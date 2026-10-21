"""One-call construction of a complete simulated robot (stations, network,
world, camera, claw, coordinator, vision, context) for tests and the app."""
from __future__ import annotations

import numpy as np

from ..config import load_config
from ..coordinator import Coordinator
from ..perception import VisionSource
from ..startup import RobotContext
from ..transport import SimHostTransport, SimNetwork
from ..trust import TrustLedger
from ..vision.camera import CameraModel
from .runtime import SimRuntime
from .station import SimStation
from .world import SimCamera, SimClaw, default_world


class SimRobot:
    def __init__(self, cfg_or_path="config/robot.sim.json", *, seed=0, latency_us=2000, jitter_us=1500,
                 loss=0.0, world_kw=None, camera_kw=None, log=None, data_dir=None, mount_err_rad=0.02,
                 board_truth=None, board_start=None, board_path=None):
        cfg = load_config(cfg_or_path) if isinstance(cfg_or_path, str) else cfg_or_path
        self.cfg = cfg
        self.log_lines = []
        log = log or self.log_lines.append
        self.net = SimNetwork(cfg.ids, latency_us=latency_us, jitter_us=jitter_us, loss=loss, seed=seed)
        rng = np.random.default_rng(seed)
        self.stations = {}
        for k, s in enumerate(cfg.stations):
            self.stations[s.id] = SimStation(s.id, usteps_per_rev=s.drive.usteps_per_rev,
                                             counts_per_rev=s.encoder.counts_per_rev, enc_sign=s.encoder.sign,
                                             clock_offset_us=float(rng.uniform(1e6, 9e7)),
                                             drift_ppm=float(rng.uniform(-40, 40)), seed=seed * 10 + k)
        self.world = default_world(cfg, self.stations, seed=seed, **(world_kw or {}))
        self.rt = SimRuntime(self.net, self.stations, self.world)
        self.co = Coordinator(cfg, SimHostTransport(self.net, self.rt.now_us), self.rt)
        self.camera = CameraModel.load(cfg.camera.intrinsics_file)
        ck = dict(camera_kw or {})
        # D27: the true camera mount differs from the configured one by a random tilt (``mount_err_rad`` per axis,
        # about the camera's horizontal axes) that the startup has to measure.
        # Measurement noise (SimCamera.noise_model, default "tags"): drawn from the tags actually in view with corner noise
        # ``camera.corner_sigma_px`` (0.3 px, configurable; ``camera_kw={"pixel_sigma": ...}`` changes the PLANT only, add
        # ``est_pixel_sigma`` to change what the estimator is told); every frame carries its own covariance. The old
        # fixed iid attitude noise (2 mrad plant, estimator told claw.vision_attitude_sigma_rad) is
        # ``camera_kw={"noise_model": "fixed"}`` (regression).
        mrng = np.random.default_rng(seed + 777)
        ck.setdefault("mount_rotvec", (*mrng.normal(0.0, mount_err_rad, 2), 0.0))
        ck.setdefault("pixel_sigma", cfg.camera.corner_sigma_px)
        ck.setdefault("cov_inflate", cfg.camera.pose_cov_inflate)
        # Board SURVEY mode: ``board_truth`` (vision.board.FloorBoardLayout, the TRUE planar poses of the sheets, tag 0 at the
        # identity) is imaged through the real BoardDetector over the live layout the startup surveys. The robot starts from
        # ``board_start`` (a layout, e.g. one surveyed earlier or a template) or, by default, knowing only tag 0; ``board_path``
        # is the layout file the survey saves to (marker.board_layout_file).
        self.board_layout = None
        if board_truth is not None:
            from ..vision.board import BoardDetector, FloorBoardLayout
            self.board_layout = board_start.copy() if board_start is not None else FloorBoardLayout(board_truth.edge_m)
            ck["board_truth"] = board_truth
            ck["board_detector"] = BoardDetector(
                self.board_layout, self.camera, min_side_px=cfg.camera.min_marker_pixels,
                max_reprojection_px=cfg.camera.max_reprojection_px, ambiguity_ratio_min=cfg.camera.ambiguity_ratio_min,
                corner_sigma_px=cfg.camera.corner_sigma_px, cov_inflate=cfg.camera.pose_cov_inflate)
        self.simcam = SimCamera(self.world, self.camera, cfg.claw.T_body_cam, cfg.marker.edge_m,
                                min_side_px=cfg.camera.min_marker_pixels, seed=seed, **ck)
        self.claw = SimClaw(self.world, self.simcam, seed=seed)
        self.vision = VisionSource(self.simcam, cfg.claw.T_body_cam, self.camera.fx, cfg.marker.edge_m,
                                   max_age_s=cfg.camera.max_frame_age_s, now_us=self.rt.now_us,
                                   pixel_sigma=ck.get("est_pixel_sigma") or ck["pixel_sigma"],
                                   imu=self.claw if cfg.claw.imu else None,
                                   rot_sigma=cfg.claw.vision_attitude_sigma_rad, rot_floor=cfg.claw.vision_attitude_floor_rad)
        self.ledger = TrustLedger()
        self.ctx = RobotContext(cfg, self.co, self.claw, self.vision, self.camera, self.ledger, log=log,
                                data_dir=data_dir)
        # a board floor reference: the excitation design (visibility, predicted covariance) knows its layout, as it would
        # from the surveyed layout file on the hardware (marker.board_layout_file)
        self.ctx.floor_board = ck.get("board")
        if self.board_layout is not None:
            from ..board_startup import FloorBoardSurveyor
            from ..vision.board import BoardGeometry
            self.ctx.floor_board = BoardGeometry.from_layout(self.board_layout)
            self.ctx.board_survey = FloorBoardSurveyor(self.board_layout, self.camera, path=board_path,
                                                       corner_sigma_px=cfg.camera.corner_sigma_px,
                                                       min_side_px=cfg.camera.min_marker_pixels, log=log)
