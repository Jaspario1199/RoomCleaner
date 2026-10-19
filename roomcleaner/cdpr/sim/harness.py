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
                 loss=0.0, world_kw=None, camera_kw=None, log=None, data_dir=None):
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
        self.simcam = SimCamera(self.world, self.camera, cfg.claw.T_body_cam, cfg.marker.edge_m,
                                min_side_px=cfg.camera.min_marker_pixels, seed=seed, **ck)
        self.claw = SimClaw(self.world, self.simcam, seed=seed)
        self.vision = VisionSource(self.simcam, cfg.claw.T_body_cam, self.camera.fx, cfg.marker.edge_m,
                                   max_age_s=cfg.camera.max_frame_age_s, now_us=self.rt.now_us,
                                   pixel_sigma=ck.get("pixel_sigma", 0.3), imu=self.claw if cfg.claw.imu else None)
        self.ledger = TrustLedger()
        self.ctx = RobotContext(cfg, self.co, self.claw, self.vision, self.camera, self.ledger, log=log,
                                data_dir=data_dir)
