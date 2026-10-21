"""Self-calibrating startup: DISARMED -> ... -> READY.

Operator preconditions: claw upright on the floor near the middle of the room,
the marker on the floor under the camera, room/anchor entries in the config,
the room cleared (nobody under the workspace), power strip within reach.

States (each step has explicit bounds and abort conditions; an abort HOLDS
motion and never removes holding torque):

SELF_CHECK
    config complete for every stage needed; suspended motion authorised;
    stations configured (hash), clock-synced, fault-free, switches closed
    (NC: open = bead at switch or broken wire), armed; claw online, battery
    >= min; camera calibration id recorded; marker visible and still; claw
    resting upright on the floor (height; the camera-to-body tilt offset is measured
    here at every startup, D27: no IMU). Vision noise measured.
SLACK_TAKEUP
    one station at a time, a slow continuous retraction (claw on the floor, so
    the stations are not coupled) bounded by ``max_slack_m``. Vision is polled
    every frame; claw motion >= max(onset_translation, k*noise) marks the taut
    onset; pulling continues to ``bearing_translation_m`` so the slide direction
    is measurable, then the station holds and pays out ``onset_backoff_m``.
    Abort: no onset within max slack (cable unattached / wrong direction /
    station order), marker lost, tilt. After all four: the slide bearings are
    checked against the anchor entries (catches swapped station wiring) and a
    first fit gives L0 per station and the marker registration.
INITIAL_LIFT
    all cables brought to just-taut, then vertical packets of ``lift_packet_m``
    computed incrementally from the model's cable directions. After each
    packet: vision height, lateral drift, tilt. Abort: drift > max, tilt > max,
    commanded - observed lift > budget, no clearance by ``max_lift_m``.
VISUAL_INITIALIZATION
    still pose while suspended -> refit (onsets + first suspended sample).
CALIBRATION
    local box (D-optimal poses + witnesses) -> fit -> expanded box -> fit ->
    acceptance (identifiability, residuals, uniqueness, witnesses, predicted
    length sigma over the work volume). Partial acceptance gives LOCAL_ONLY
    with the validated volume.
    With ``startup.slack_probe`` every suspended sample (this state and
    VISUAL_INITIALIZATION) is preceded by a per-pose slack probe: each cable in
    turn is retracted in small steps until the claw moves (taut onset), its
    slack is measured, it is left just taut, the sample is taken with all four
    taut, and the motor positions are restored afterwards (so the planner's
    model-consistent positions are unchanged).
REFERENCE_VERIFICATION
    trust decision (decision D26). Full-workspace operation (VERIFIED) is granted
    by the MARGINS, not by bead precision, if at this startup (a) the calibration
    was accepted, (b) the slack probe was on for the suspended samples and the
    witness chi-squared is consistent, and (c) k*sigma <= the ceiling / wall
    margin everywhere in the commanded workspace, sigma being the predicted
    1-sigma of the claw position relative to the boundary the margin protects
    (``assess_margin_trust``, ``Calibrator.boundary_sigma``). The bead search
    (one station at a time, homing.py) is optional (``startup.bead_search``,
    off by default); D24's gating still applies when it runs and an all-verified
    search is VERIFIED on the basis "beads". Beads are otherwise end-of-travel
    switches: one opening during normal motion faults the station.
READY
    level VERIFIED (basis "margin" or "beads") or LOCAL_ONLY (stated reasons).

Tension is NOT measured in V1 (open decision, see docs): the lift and the
calibration rely on geometric consistency checks instead, which bound but do
not measure cable load.
"""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .calibration import (IDS, BeadObs, Calibrator, OnsetSample, PoseSample, Priors, align_from_bearings,
                          box_candidates, design_excitation, marker_visible, predicted_vision_cov)
from .attitude import mount_offset_from_up
from .frames import inv_T, make_T, matrix_to_rotvec, planar_T, rotvec_to_matrix, tilt_angle
from .kinematics import Geometry, geometry_from_config, tension_distribution, workspace_from_config
from .perception import cam_displacement, floor_displacement, tilt_change, to_marker, to_room
from .spool import CableMap
from .protocol import State
from .trajectory import PlanError, limits_from_config, model_from, plan_cable_move, plan_line_from

def probe_response(geo, q_room, i, k_rel=None, R=None):
    """Claw displacement (room frame) per unit retraction of cable ``i`` beyond
    the taut point, for equal-modulus cables of stiffness ~ 1/length (the
    modulus cancels): ``x = (sum_j k_j u_j u_j^T)^-1 k_i u_i`` over all four
    cables (a slack cable not yet found is the main source of mismatch, hence the
    prior sigma ``probe_response_sigma``).

    Spaced attachments: the rigid claw also rotates. The twist (dp, dtheta) of
    the body responds with the 6x6 stiffness ``sum_j k_j w_j w_j^T`` (w_j = [u_j;
    r_j x u_j], r_j the attachment offset in the world frame); the translation part
    is returned. (The pendulum stiffness of gravity at the CoM, ~m g |c| ~ 1 N m/rad, is
    negligible against the line elasticity ~EA |b|^2 / L and is left out; yaw has no
    gravity restoring term at all.)
    A common point reduces to the 3x3 formula above exactly."""
    U = geo.unit_vectors(q_room, R)
    k = 1.0 / geo.lengths(q_room, R) if k_rel is None else np.asarray(k_rel, float)
    if not geo.spaced:
        K = sum(k[j] * np.outer(U[j], U[j]) for j in range(4))
        return np.linalg.solve(K, k[i] * U[i])
    Rm = geo.R_at(q_room, R)
    r = geo.attach @ Rm.T
    W = np.hstack([U, np.cross(r, U)])                               # (4, 6) rows w_j
    K = (W * k[:, None]).T @ W
    x = np.linalg.solve(K + 1e-12 * np.eye(6), k[i] * W[i])
    return x[:3]


def hinge_analysis(r, P, C, v, sig_w, k_noise, floor_m):
    """Taut-onset analysis of one cable's retraction series.

    Data: ``r`` (K,) cumulative retraction (m), ``P`` (K,3) vision positions
    (marker frame) and ``C`` (K,3,3) covariances of the individual measurements.
    Model: ``p_k = p0 + w * max(r_k - s, 0)``: the claw does not move until the
    slack ``s`` is taken up, then moves by ``w`` per metre of further
    retraction (``w`` has a Gaussian prior ``N(v, sig_w^2 I)`` from the cable
    geometry). ``s`` is profiled on a grid; the null model is "no response yet".

    Returns a dict: ``detected`` (the hinge beats the null by ``k_noise`` sigma
    AND the fitted claw motion at the last step is >= ``floor_m``), ``s`` (best
    slack), ``sigma_s`` (profile 1-sigma), ``sig`` (significance, sigma),
    ``disp`` (fitted motion at the last step, m)."""
    r = np.asarray(r, float)
    P = np.asarray(P, float)
    W = np.linalg.inv(np.asarray(C, float))
    rK = float(r[-1])
    n = int(min(max(round(rK / 5e-5), 20), 240))
    sg = np.linspace(0.0, rK, n + 1)                           # s = rK is the null model
    H = np.maximum(r[None, :] - sg[:, None], 0.0)               # (G, K)
    S0 = W.sum(0)
    S1 = np.einsum("gk,kab->gab", H, W)
    S2 = np.einsum("gk,kab->gab", H * H, W) + np.eye(3) / sig_w ** 2
    N = np.zeros((len(sg), 6, 6))
    N[:, :3, :3] = S0
    N[:, :3, 3:] = S1
    N[:, 3:, :3] = np.swapaxes(S1, 1, 2)
    N[:, 3:, 3:] = S2
    b0 = np.einsum("kab,kb->a", W, P)
    b1 = np.einsum("gk,kab,kb->ga", H, W, P)
    rhs = np.concatenate([np.broadcast_to(b0, (len(sg), 3)), b1 + v / sig_w ** 2], axis=1)
    th = np.linalg.solve(N, rhs[:, :, None])[:, :, 0]
    p0, w = th[:, :3], th[:, 3:]
    res = P[None] - p0[:, None, :] - H[:, :, None] * w[:, None, :]
    chi2 = np.einsum("gka,kab,gkb->g", res, W, res) + np.sum((w - v) ** 2, axis=1) / sig_w ** 2
    g = int(np.argmin(chi2))
    null = float(chi2[-1])
    sig = math.sqrt(max(null - float(chi2[g]), 0.0))
    ok = np.flatnonzero(chi2 <= chi2[g] + 1.0)
    lo, hi = sg[ok.min()], sg[ok.max()]
    step = sg[1] - sg[0] if len(sg) > 1 else 0.0
    sigma_s = max(0.5 * (hi - lo), 0.5 * step)
    disp = float(np.linalg.norm(w[g]) * max(rK - sg[g], 0.0))
    return {"detected": bool(g < len(sg) - 1 and sig >= k_noise and disp >= floor_m), "s": float(sg[g]),
            "sigma_s": float(sigma_s), "sig": float(sig), "disp": disp, "w": w[g].copy()}


STARTUP_STATES = ("DISARMED", "SELF_CHECK", "SLACK_TAKEUP", "INITIAL_LIFT", "VISUAL_INITIALIZATION",
                  "CALIBRATION", "REFERENCE_VERIFICATION", "READY")


class StartupAbort(Exception):
    def __init__(self, state, reason, *, suspended=False, paused=False):
        super().__init__(f"{state}: {reason}")
        self.state, self.reason, self.suspended, self.paused = state, reason, suspended, paused


@dataclass
class StartupReport:
    state: str = "DISARMED"
    history: list = field(default_factory=list)
    measurements: dict = field(default_factory=dict)
    outcome: str | None = None              # READY | FAULT | PAUSED
    level: str = "NONE"
    reasons: list = field(default_factory=list)


class DragWatch:
    """Pretension drag-watch: is the claw being dragged while the cables are tensioned?

    Camera-frame displacement (``perception.floor_displacement``: one reference tilt, so the absolute pose's tilt-lever
    noise cancels) from the still pose ``ref`` taken at the start of the step, FILTERED over the last ``n`` frames: the
    mean displacement must exceed ``max(floor_m, k x the mean's own 1-sigma)``, the sigma coming from the per-frame
    covariances (largest principal axis of the mean's covariance plus the reference's). A single frame never trips it,
    and the threshold follows the noise: a noisier view (one tag) raises it instead of producing false alarms, and the
    old fixed 10 mm single-frame threshold is only the floor of the threshold."""

    def __init__(self, ref, *, floor_m: float, k: float, n: int = 3):
        self.ref, self.floor_m, self.k, self.n = ref, float(floor_m), float(k), int(n)
        self.win: list = []
        self.last_disp_m = 0.0
        self.last_thr_m = float(floor_m)

    def update(self, o) -> bool:
        """Feed one good frame (``PoseObs``); True = dragged."""
        d, c_o, c_r = floor_displacement(o, self.ref)         # the claw rests on the floor: its tilt is the reference's
        self.win = (self.win + [(d, c_o)])[-self.n:]
        if len(self.win) < self.n:
            return False
        m = np.mean([w[0] for w in self.win], axis=0)
        C = np.mean([w[1] for w in self.win], axis=0) / self.n + c_r
        self.last_disp_m = float(np.linalg.norm(m))
        self.last_thr_m = max(self.floor_m, self.k * math.sqrt(float(np.linalg.eigvalsh(C)[-1])))
        return self.last_disp_m > self.last_thr_m


class RockWatch:
    """Is the claw rocking on its jaws? The tilt-change channel of the floor stage (take-up, pretension).

    ``perception.floor_displacement`` takes the reference tilt, so a claw that tips about a jaw edge (a tall claw on a small
    footprint pulled at ~0.5 m tips at ~0.5 N, before it slides at ~1.8 N; verification/imu_removal_review.md R2.2b) reads
    almost no displacement. With the board in view (>= 2 tags in the reference AND in the frame: tilt noise 1-3 mrad) the
    tilt change itself is measured (``perception.tilt_change``): the mean of the last ``n`` frames must exceed
    ``max(min_rad, k x its own sigma)`` plus ``yaw_coupling x |yaw change|`` (a take-up yaws the claw and a little tilt comes
    with it). The sigma is the frames' covariance (the mean of ``n`` frames against the reference's own noise) plus the
    systematic floor ``floor_rad`` (a change of the tag set between the two views). A single noise spike cannot trip the
    3-frame mean (a 5-sigma frame is 2.9 sigma of the mean). With ONE tag in view the tilt noise is ~13 mrad per frame:
    nothing can be seen, ``can_see`` is False, ``update`` always returns False and the caller says so in the log."""

    def __init__(self, ref, *, k: float, min_rad: float, yaw_coupling: float, floor_rad: float = 0.0, n: int = 3):
        self.ref, self.k, self.min_rad, self.yaw_coupling, self.floor_rad, self.n = ref, float(k), float(min_rad), \
            float(yaw_coupling), float(floor_rad), int(n)
        self.win: list = []
        self.last_tilt_rad = 0.0
        self.last_thr_rad = float(min_rad)
        self.max_tilt_rad = 0.0
        self.n_tags_ref = int(getattr(ref, "n_tags", 1))

    @property
    def can_see(self) -> bool:
        return self.n_tags_ref >= 2 and getattr(self.ref, "pose_cov", None) is not None

    def update(self, o) -> bool:
        """Feed one good frame (``PoseObs``); True = the claw has rocked."""
        if not self.can_see or int(getattr(o, "n_tags", 1)) < 2 or o.pose_cov is None:
            self.win = []                                    # a one-tag frame carries no tilt information
            return False
        eps, s_o2, s_r2, psi = tilt_change(o, self.ref)
        self.win = (self.win + [(eps, s_o2, abs(psi))])[-self.n:]
        if len(self.win) < self.n:
            return False
        m = np.mean([w[0] for w in self.win], axis=0)
        sig = math.sqrt(float(np.mean([w[1] for w in self.win])) / self.n + s_r2 + self.floor_rad ** 2)
        self.last_tilt_rad = float(np.linalg.norm(m))
        self.last_thr_rad = max(self.min_rad, self.k * sig) + self.yaw_coupling * float(np.mean([w[2] for w in self.win]))
        self.max_tilt_rad = max(self.max_tilt_rad, self.last_tilt_rad)
        return self.last_tilt_rad > self.last_thr_rad


class RobotContext:
    """Everything the procedures share. Working frame for motion: the room."""

    def __init__(self, cfg, co, claw, vision, camera, ledger, *, log=print, data_dir=None):
        self.cfg, self.co, self.claw, self.vision, self.camera, self.ledger = cfg, co, claw, vision, camera, ledger
        self.log = log
        self.data_dir = Path(data_dir) if data_dir else None
        self.cal = Calibrator(cfg, {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations})
        self.priors = self.cal.priors
        self.T_R_M = planar_T(self.priors.position[0], self.priors.position[1], self.priors.heading)
        self.model = None
        self.result = None
        self.onsets: list = []
        self.samples: list = []
        self.lim = limits_from_config(cfg)
        self.ws = None
        self.validated_volume = None        # room-frame points where the model is validated
        self.mount_angle_rad = None         # camera-to-body tilt offset measured at startup (D27); None = not measured
        self.mount_sigma_rad = 0.0          # its standard error
        self.persist = lambda: None         # supervisor installs its durable save here
        self.claw_yaw_room = 0.0            # last measured claw yaw (room frame): the yaw the attitude statics hold
        self.claw_ref_room = None           # (p, R) of the last measured claw pose (room frame)
        self.floor_board = None             # vision.board.BoardGeometry of the surveyed floor-reference layout (None = single tag)
        self.board_survey = None            # board_startup.FloorBoardSurveyor over the live layout (None = no survey: single tag / off)

    @property
    def T_B_C(self):
        """Camera pose in the body frame: nominal CAD rotation corrected by the mount tilt measured at startup."""
        v = getattr(self.vision, "T_B_C", None)
        return self.cfg.claw.T_body_cam if v is None else v

    def set_mount_offset(self, off):
        """Store the measured camera-to-body tilt offset (attitude.MountOffset) and use it for all later vision poses."""
        self.vision.set_mount_offset(off.Q)
        self.mount_angle_rad, self.mount_sigma_rad = float(off.angle_rad), float(off.sigma_rad)

    # -- time ------------------------------------------------------------
    def wait(self, s):
        self.co.wait(s * 1e6)

    def now_s(self):
        return self.co.rt.now_us() / 1e6

    # -- model -----------------------------------------------------------
    def set_model(self, anchors_room, L0: dict, T_R_M=None):
        if T_R_M is not None:
            self.T_R_M = np.asarray(T_R_M, float)
        geo = geometry_from_config(self.cfg, anchors_room, self.claw_yaw_room)
        if self.claw_ref_room is not None:
            geo.set_reference(*self.claw_ref_room)
        self.model = model_from(geo, self.cfg, L0)
        self.ws = workspace_from_config(self.cfg, np.asarray(anchors_room),
                                        lowest_point_z=float(self.cfg.claw.lowest_point_body_m[2]))
        self._bead_margin()

    def _bead_margin(self):
        """Until a station's bead is verified (D26: also when VERIFIED by margin, where the bead is only an
        end-of-travel switch) the absolute length can be off by k*sigma_abs: widen the normal-motion
        keep-out from each bead so an ordinary move cannot pull a bead onto its switch (review M2)."""
        if self.result is None or self.ws is None:
            return
        k = self.cfg.calibration.bead_k_sigma
        sig = self.cal.absolute_sigma(self.result)
        for i, s in enumerate(self.cfg.stations):
            if s.bead.present and s.bead.trigger_length_m is not None and not self.ledger.stations[s.id].bead_verified:
                self.ws.min_lengths[i] = s.bead.trigger_length_m + s.bead.min_length_margin_m + k * float(sig[i])

    def apply_result(self, res, source):
        self.result = res
        self.ledger.anchors_room = res.anchors_room.tolist()
        self.set_model(res.anchors_room, dict(zip(IDS, res.L0)), res.T_R_M)
        sig = res.sigma()
        boots = {s: self.co.links[s].boot for s in IDS}
        for i, s in enumerate(IDS):
            self.ledger.set_reference(s, boots[s], res.L0[i], float(sig[f"L0 {s}"]), source)
        self.ledger.T_R_M = res.T_R_M.tolist()
        self.ledger.marker_valid = True
        self.save_model()

    # -- persistence (host restart while suspended) ----------------------------
    def save_model(self):
        if self.data_dir is None or self.result is None or self.model is None:
            return
        from .trust import atomic_write
        st = {"result": self.result.to_state(), "T_R_M": self.T_R_M.tolist(),
              "L0": {s: self.model.maps[s].L0 for s in IDS},
              "boots": {s: self.co.links[s].boot for s in IDS},
              "validated_volume": None if self.validated_volume is None else np.asarray(self.validated_volume).tolist(),
              "mount": {"rotvec": matrix_to_rotvec(self.vision.mount_Q).tolist(), "angle_rad": self.mount_angle_rad,
                        "sigma_rad": self.mount_sigma_rad},
              "beads": [[b.i, b.P, b.trigger, b.sigma] for b in self.cal.beads]}
        atomic_write(self.data_dir / "model.json", json.dumps(st))

    def load_model(self) -> bool:
        if self.data_dir is None or not (self.data_dir / "model.json").exists():
            return False
        from .calibration import CalibrationResult
        d = json.loads((self.data_dir / "model.json").read_text())
        self.result = CalibrationResult.from_state(d["result"])
        self.set_model(self.result.anchors_room, d["L0"], d["T_R_M"])
        mt = d.get("mount")
        if mt:                                        # the offset measured at the last startup (the claw is hanging now)
            self.vision.set_mount_offset(rotvec_to_matrix(mt["rotvec"]))
            self.mount_angle_rad, self.mount_sigma_rad = mt["angle_rad"], mt["sigma_rad"]
        vv = d.get("validated_volume")
        self.validated_volume = None if vv is None else np.asarray(vv)
        self.cal.beads = [BeadObs(int(i), P, t, sg) for i, P, t, sg in d.get("beads", [])]
        self.saved_boots = d.get("boots", {})
        return True

    def room_pose(self, sp):
        """Claw origin (room frame) of a vision pose. Side effect: the measured yaw becomes the held yaw of the
        attitude model (planning predicts roll/pitch from statics at this yaw; yaw itself is only measured)."""
        self.note_attitude(sp.R, sp.p)
        return to_room(self.T_R_M, sp.p)

    def room_R(self, sp):
        """Claw orientation (room frame) of a vision pose (full vision attitude; D27: no IMU)."""
        return self.T_R_M[:3, :3] @ np.asarray(sp.R, float)

    def note_attitude(self, R_M, p_M=None):
        """Anchor the attitude prediction to a measured claw pose (marker frame)."""
        R_room = self.T_R_M[:3, :3] @ np.asarray(R_M, float)
        self.claw_yaw_room = float(math.atan2(R_room[1, 0], R_room[0, 0]))
        self.cal.note_yaw_M(R_M, p_M)
        self.claw_ref_room = None if p_M is None else (to_room(self.T_R_M, p_M), R_room)
        if self.model is not None:
            self.model.geometry.set_yaw(self.claw_yaw_room)
            if self.claw_ref_room is not None:
                self.model.geometry.set_reference(*self.claw_ref_room)

    def length_sigma_room(self, q_R):
        if self.result is None:
            return np.full(4, np.inf)
        return self.cal.length_sigma(self.result, to_marker(self.T_R_M, q_R))

    def ppu(self, i):
        sid = IDS[i]
        P = self.co.positions()[i]
        m = self.model.maps[sid] if self.model is not None and self.model.maps[sid].L0 is not None else None
        if m is None:
            return 2 * math.pi * self.cfg.stations[i].spool.core_radius_m / self.cfg.stations[i].drive.usteps_per_rev
        return m.payout_per_ustep(m.length(P))

    def save(self, name, obj):
        if self.data_dir is None:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / name).write_text(json.dumps(obj, indent=2, default=lambda o: np.asarray(o).tolist()))


MOUNT_FRAMES = 30            # frames averaged for the camera-mount tilt offset (standard error = scatter / sqrt(30))


class StartupSequencer:
    # STUDY HOOK (floor-reference study; None = off, behaviour unchanged): an
    # object with visible(camera, T_B_C, T_M_B, min_side_px=, margin_px=) -> bool
    # and edge_eff(camera, T_B_C, T_M_B, min_side_px=, margin_px=) -> float
    # (e.g. sim.world.FloorBoard). When set, the excitation design treats a pose
    # as visible if ANY tag of the board is in view, and predicts the vision
    # covariance with the board's effective span instead of the single tag edge.
    study_board = None

    # The pretension drag-watch (INITIAL_LIFT, class DragWatch) judges the camera-frame displacement of the claw with a
    # filter over this many frames: the mean of the last N displacements against max(3 x onset_translation, 10 mm, k x the
    # mean's own sigma).
    DRAG_WATCH_FRAMES = 3
    DRAG_WATCH_FLOOR_M = 0.010
    # The rocking watch (class RockWatch) filters the tilt change over this many frames (take-up and pretension, >= 2 floor tags).
    ROCK_WATCH_FRAMES = 3
    # Mount-offset hold-out check (SELF_CHECK): the residual tilt of a fresh set of frames against the corrected mount
    # may not exceed MOUNT_RECHECK_K sigma of the two measurements (and at least MOUNT_RECHECK_FLOOR_RAD).
    MOUNT_RECHECK_K = 4.0
    MOUNT_RECHECK_FLOOR_RAD = 0.003
    # Keep-alive grid while a long computation runs on a worker thread (_pumped): Coordinator.pump pings every
    # min(faults.lease_s / 4, 20 ms), so ctx.wait is called in steps of one ping period.
    PUMP_STEP_S = 0.02

    def __init__(self, ctx: RobotContext):
        self.ctx = ctx
        self.cfg = ctx.cfg
        self.rep = StartupReport()
        self.noise_m = 0.001
        self.p_floor = None
        self.probe_log: list = []               # one record per probed pose (slack_probe)
        self.cal_report: dict | None = None     # last acceptance report of the final calibration

    # -------------------------------------------------------------- helpers
    @property
    def board(self):
        """Visibility / span queries of the multi-tag floor reference (sim.world.FloorBoard or vision.board.BoardGeometry
        of a surveyed layout), or None for the single tag. ``study_board`` (class attribute) wins over the context's."""
        return self.study_board if self.study_board is not None else getattr(self.ctx, "floor_board", None)

    def _pumped(self, fn, *args, **kwargs):
        """Run the long computation ``fn(*args, **kwargs)`` (a ``Calibrator.fit``, the survey top-up's ``flush``) on a one-worker
        thread while this (the command) thread keeps the station keep-alive going with ``ctx.wait`` on the 20 ms grid. While a
        command owns the robot the idle host loop does not pump (``Service.idle_tick``), so a computation of seconds on this
        thread would outlast ``faults.lease_s`` and latch Fault.LEASE on all four armed stations (review H1). ``fn`` must touch
        only its own objects (the calibrator, the survey and its layout), never the coordinator; its result is returned and an
        exception it raises is re-raised unchanged. An exception of ``ctx.wait`` (abort, e-stop) propagates at once: the worker
        is not waited for (it cannot be interrupted and its result is dropped)."""
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="startup-pumped")
        fut = None
        try:
            fut = pool.submit(fn, *args, **kwargs)
            while not fut.done():
                self.ctx.wait(self.PUMP_STEP_S)
            return fut.result()
        finally:
            pool.shutdown(wait=fut is not None and fut.done(), cancel_futures=True)

    def _enter(self, state, msg=""):
        self.rep.state = state
        self.rep.history.append((round(self.ctx.now_s(), 3), state, msg))
        self.ctx.log(f"[startup] {state} {msg}")

    def _still(self, n=None, state="?", suspended=False, min_frames=None):
        st = self.cfg.startup
        sp, why = self.ctx.vision.still_pose(max(n or st.still_samples, min_frames or 0), self.ctx.wait, interval_s=st.frame_interval_s,
                                             max_wait_s=max(10.0, st.max_marker_wait_s if n is None else 10.0),
                                             spread_max_m=st.still_spread_max_m)
        if sp is None:
            raise StartupAbort(state, why, suspended=suspended, paused=True)
        if suspended and getattr(self.ctx, "board_survey", None) is not None and st.board_survey:
            self.ctx.board_survey.offer(getattr(self.ctx.vision, "last_still_frames", ()))     # sheets the hanging claw sees now
        return sp

    def _measure_mount(self, sp, S):
        """Camera-to-body tilt offset (D27), measured at EVERY startup while the claw rests upright on its jaws over
        the printout: the marker normal seen by the camera is body z. Stored in the context (and the saved model) and
        applied to every later vision pose. Aborts if the offset is implausibly large (claw not resting upright, or the
        camera mount is wrong).

        The correction is then CHECKED against a held-out set of frames: a fresh, independent set of ``MOUNT_FRAMES``
        frames is taken (the claw is not touched in between) and its mean marker normal, read through the corrected
        mount, must agree with body z within ``MOUNT_RECHECK_K`` x the combined standard error of the two sets (at
        least ``MOUNT_RECHECK_FLOOR_RAD``). A claw that is rocking, a rest tilt that changed, or a measurement that is not
        reproducible fails here; the old 'tilt after correction' test on the same data was zero by construction.
        Returns the held-out still pose (corrected mount) used by the rest of SELF_CHECK."""
        ctx, cfg = self.ctx, self.cfg
        off = mount_offset_from_up(ctx.vision.T_B_C_nominal[:3, :3], sp.up_cam, sigma_rad=sp.up_sigma_rad, n=sp.n)
        if off.angle_rad > cfg.claw.mount_offset_max_rad:
            raise StartupAbort(S, f"camera-to-body tilt offset {math.degrees(off.angle_rad):.1f} deg exceeds "
                                  f"{math.degrees(cfg.claw.mount_offset_max_rad):.1f} deg: the claw is not resting upright "
                                  "on its jaws, or the camera mount differs from the CAD")
        ctx.set_mount_offset(off)
        held = self._still(state=S, min_frames=MOUNT_FRAMES)
        R_B_C = ctx.vision.T_B_C[:3, :3]
        u_pred = R_B_C.T @ np.array([0.0, 0.0, 1.0])                 # body z in camera axes, through the corrected mount
        u_meas = np.asarray(held.up_cam, float)
        resid = float(math.acos(float(np.clip(u_pred @ u_meas, -1.0, 1.0))))
        sig = math.hypot(sp.up_sigma_rad, held.up_sigma_rad)
        limit = max(self.MOUNT_RECHECK_K * sig, self.MOUNT_RECHECK_FLOOR_RAD)
        self.rep.measurements["camera_mount_offset_rad"] = off.angle_rad
        self.rep.measurements["camera_mount_offset_sigma_rad"] = off.sigma_rad
        self.rep.measurements["camera_mount_holdout_residual_rad"] = resid
        self.rep.measurements["camera_mount_holdout_limit_rad"] = limit
        if resid > limit:
            ctx.mount_angle_rad, ctx.mount_sigma_rad = None, 0.0
            ctx.vision.set_mount_offset(np.eye(3))
            raise StartupAbort(S, f"camera-mount offset not reproducible: a held-out set of {held.n} frames disagrees with the "
                                  f"corrected mount by {math.degrees(resid):.2f} deg (limit {math.degrees(limit):.2f} deg = "
                                  f"{self.MOUNT_RECHECK_K:g} sigma): the claw is moving or was disturbed between the sets")
        ctx.log(f"camera mount tilt offset {math.degrees(off.angle_rad):.2f} deg "
                f"(+-{math.degrees(off.sigma_rad):.2f}, {off.n} frames); held-out check {math.degrees(resid):.2f} deg "
                f"(limit {math.degrees(limit):.2f})")
        return held

    def _pretension_watch(self, dw: DragWatch, rw: RockWatch, drag: dict):
        """Monitor of the pretension move: the claw must neither be dragged (``DragWatch``, translation) nor rock on its jaws
        (``RockWatch``, tilt change; >= 2 floor tags). ``drag`` carries the frame clock (``next``) and the detail of a trip (``bad``)."""
        ctx, st = self.ctx, self.cfg.startup

        def watch(tau):
            if ctx.now_s() < drag["next"]:
                return None
            drag["next"] = ctx.now_s() + st.frame_interval_s
            o = ctx.vision.observe()
            if o.ok and dw.update(o):
                drag["bad"] = dw.last_disp_m
                return "claw dragged while tensioning"
            if o.ok and rw.update(o):                  # tilt-change channel: the cables tip the claw about a jaw edge
                drag["bad"] = f"{rw.last_tilt_rad * 1e3:.1f} mrad tilt change > {rw.last_thr_rad * 1e3:.1f} mrad"
                return "claw rocking on its jaws while tensioning"
            return None
        return watch

    def _survey_board(self, S):
        """Survey the floor board with the resting claw (``board_startup.FloorBoardSurveyor``; only when the context has one,
        i.e. ``marker.board_layout_file`` is set and ``startup.board_survey`` is on). Needs a still claw, so a stillness check
        comes first. Never moves anything; aborts only when the layout cannot be the printed board (tag size)."""
        ctx, st = self.ctx, self.cfg.startup
        sv = getattr(ctx, "board_survey", None)
        if sv is None:
            return
        if not st.board_survey:
            self.rep.measurements["board_survey"] = {"ran": False, "why": "startup.board_survey = false"}
            ctx.log("[startup] floor board survey is switched off (startup.board_survey = false): the layout file is used as it is")
            return
        self._still(state=S)                                   # the claw and the sheets must be still before they are surveyed
        try:
            out = sv.run(ctx.vision, ctx.wait, n_frames=st.board_survey_frames, interval_s=st.frame_interval_s,
                         edge_m=self.cfg.marker.edge_m)
        except ValueError as e:
            raise StartupAbort(S, str(e))
        ctx.floor_board = sv.geometry()
        self.rep.measurements["board_survey"] = {"ran": True, **out}
        n = len(out["surveyed_ids"])
        ctx.log(f"[startup] floor board survey: {n} of {out['expected']} sheets surveyed ({out['frames']} frames"
                + (f", new: {out['newly_surveyed']}" if out["newly_surveyed"] else "")
                + (f", sigma <= {out['max_sigma_xy_m'] * 1e3:.2f} mm" if out["max_sigma_xy_m"] is not None else "") + ")"
                + (f"; saved to {out['saved']}" if out["saved"] else ""))
        for i, why in out["cleared"].items():
            ctx.log(f"[startup] floor board: sheet {i} was cleared: {why}")
        if out["unsurveyed"]:
            ctx.log("[startup] floor board: not surveyed and so not used: "
                    + "; ".join(f"{i} ({why})" for i, why in sorted(out["unsurveyed"].items())))
        for w in out["warnings"]:
            ctx.log(f"[startup] floor board WARNING: {w}")

    def _execute(self, plan, state, *, suspended, monitor=None, stop_on_capture=False):
        r = self.ctx.co.execute(plan, monitor=monitor, stop_on_capture=stop_on_capture)
        if not r.ok and r.reason.startswith("paused"):
            raise StartupAbort(state, r.reason, suspended=suspended, paused=True)
        return r

    def _cable_rate(self, speed, i=None):
        ppus = [self.ctx.ppu(j) for j in (range(4) if i is None else [i])]
        return speed / min(ppus)

    def _rock_watch(self, ref, where: str) -> RockWatch:
        """The tilt-change watch for a floor-stage step whose reference is ``ref``. With one floor tag the tilt of the claw
        cannot be measured (13 mrad per frame): the watch is inert, the behaviour is the previous one (translation, slide
        direction, the absolute tilt limit) and the report and the log say that a rocking claw cannot be seen."""
        st, rep = self.cfg.startup, self.rep.measurements
        rw = RockWatch(ref, k=st.rocking_tilt_k, min_rad=st.rocking_tilt_min_rad, yaw_coupling=st.rocking_yaw_coupling,
                       floor_rad=self.cfg.claw.vision_attitude_floor_rad, n=self.ROCK_WATCH_FRAMES)
        if rw.can_see:
            rep.setdefault("rocking_check", "active")
        else:
            blind = rep.setdefault("rocking_blind_at", [])
            if not blind:
                self.ctx.log(f"[startup] {int(getattr(ref, 'n_tags', 1))} floor tag in view ({where}): a claw rocking on its jaws "
                             "cannot be seen (tilt noise of one tag ~13 mrad per frame); the take-up and the pretension use "
                             "the reference tilt and the absolute tilt limit only (a board with >= 2 tags in view removes this)")
            blind.append(where)
            rep["rocking_check"] = "blind: fewer than 2 floor tags in view"
        return rw

    # -------------------------------------------------------------- run
    def run(self) -> StartupReport:
        steps = [("SELF_CHECK", self.self_check), ("SLACK_TAKEUP", self.slack_takeup),
                 ("INITIAL_LIFT", self.initial_lift), ("VISUAL_INITIALIZATION", self.visual_init),
                 ("CALIBRATION", self.calibrate), ("REFERENCE_VERIFICATION", self.verify_references)]
        try:
            for name, fn in steps:
                self._enter(name)
                fn()
        except StartupAbort as e:
            self.rep.outcome = "PAUSED" if e.paused else "FAULT"
            self.rep.reasons.append(e.reason)
            self.rep.measurements["suspended"] = e.suspended
            if e.suspended:                             # never set True from an abort (fail closed)
                self.ctx.ledger.claw_supported = False
            self.rep.measurements["suspended"] = not self.ctx.ledger.claw_supported
            self.ctx.persist()
            self._enter(self.rep.outcome, f"in {e.state}: {e.reason}")
            return self.rep
        self.rep.outcome = "READY"
        self.rep.level = self.ctx.ledger.level
        self._enter("READY", f"level {self.ctx.ledger.level}")
        return self.rep

    # ------------------------------------------------------------ SELF_CHECK
    def self_check(self):
        cfg, ctx, S = self.cfg, self.ctx, "SELF_CHECK"
        missing = cfg.missing("calibration")
        if missing:
            raise StartupAbort(S, f"configuration incomplete: {missing}")
        if not cfg.authorization.suspended_motion_authorized:
            raise StartupAbort(S, "suspended motion not authorised in the configuration")
        ctx.ledger.on_camera_calibration(ctx.camera.calibration_id)
        st = ctx.claw.status()
        if not st.get("online"):
            raise StartupAbort(S, "claw offline")
        if st.get("battery_v") is not None and st["battery_v"] < cfg.startup.battery_min_v:
            raise StartupAbort(S, f"claw battery {st['battery_v']:.2f} V < {cfg.startup.battery_min_v} V")
        # 1) the claw must demonstrably rest upright on the floor BEFORE any
        #    station is touched; only then is clearing latched faults safe
        self._survey_board(S)                      # the sheets in view are surveyed BEFORE the mount offset and the floor poses use them
        sp = self._measure_mount(self._still(state=S, min_frames=MOUNT_FRAMES), S)
        # vision noise for the onset thresholds: the RAW camera-frame scatter of the frames (not the absolute-pose
        # scatter, whose tilt-lever part cancels in every displacement the take-up and the probe use)
        self.noise_m = max(sp.spread_cam_m, 2e-4)
        zf = -float(cfg.claw.lowest_point_body_m[2])
        if abs(sp.p[2] - zf) > cfg.startup.floor_height_tol_m:
            raise StartupAbort(S, f"claw origin {sp.p[2]:.3f} m above the marker, expected {zf:.3f} m: "
                                  "not resting upright on the floor (or marker edge / camera mount wrong)")
        if sp.tilt_rad > cfg.startup.max_tilt_rad:      # ~0 by construction after the mount correction; a consistency check
            raise StartupAbort(S, f"claw tilted {math.degrees(sp.tilt_rad):.1f} deg after the mount correction")
        ctx.ledger.claw_supported = True
        ctx.persist()
        # 2) stations
        co = ctx.co
        try:
            co.wait(300000)
            for s_ in IDS:                           # e.g. LEASE latched while parked: safe on the floor
                if (co.links[s_].tel or {}).get("st") == State.FAULT:
                    co.clear(s_)
            co.configure()
            co.wait_synced(5.0)
            co.wait(200000)                          # telemetry reflecting the new configuration
        except Exception as e:                      # CoordinatorError: station unreachable / config
            raise StartupAbort(S, f"stations: {e}")
        bad = {s: [x for x in r if x not in ("state OFF", "state IDLE")] for s, r in co.readiness().items()}
        bad = {s: r for s, r in bad.items() if r}
        if bad:
            raise StartupAbort(S, f"stations not healthy: {bad}")
        sw = {s: (co.links[s].tel or {}).get("sw") for s in IDS}
        if any(sw.values()):
            raise StartupAbort(S, f"switch open at {[s for s, v in sw.items() if v]}: bead at switch or broken wire")
        try:
            co.arm(sw_ok=False)
        except Exception as e:
            raise StartupAbort(S, f"arm refused: {e}")
        co.wait(100000)
        bad = {s: r for s, r in co.readiness().items() if r}
        if bad:
            raise StartupAbort(S, f"stations not ready after arming: {bad}")
        self.p_floor = sp
        self.rep.measurements["vision_noise_m"] = self.noise_m
        self.rep.measurements["vision_noise_absolute_m"] = sp.spread_m
        self.rep.measurements["floor_tags_in_view"] = sp.n_tags
        self.rep.measurements["floor_attitude_sigma_rad"] = sp.att_sigma_rad
        self.rep.measurements["claw_on_floor_M"] = sp.p.tolist()

    # ---------------------------------------------------------- SLACK_TAKEUP
    def slack_takeup(self):
        cfg, ctx, S = self.cfg, self.ctx, "SLACK_TAKEUP"
        st = cfg.startup
        thr = max(st.onset_translation_m, st.onset_noise_k * self.noise_m)
        bearing_d = max(st.bearing_translation_m, 2 * thr)
        ctx.onsets = []
        for i, sid in enumerate(IDS):
            ref = self._still(state=S)
            rw = self._rock_watch(ref, f"station {sid} take-up")
            mon = {"next": 0.0, "onset": None, "lost": 0.0, "max_disp": 0.0, "rocked": False}

            def monitor(tau, i=i, ref=ref, mon=mon):
                now = ctx.now_s()
                if now < mon["next"]:
                    return None
                mon["next"] = now + st.frame_interval_s
                o = ctx.vision.observe()
                if not o.ok:
                    mon["lost"] += st.frame_interval_s
                    return f"marker lost ({o.reason})" if mon["lost"] > 1.0 else None
                mon["lost"] = 0.0
                # camera-frame displacement from the reference captured at the start of this station's take-up
                # (one reference tilt: the per-frame tilt-lever noise of the absolute pose cancels)
                disp = float(np.linalg.norm(floor_displacement(o, ref)[0]))
                mon["max_disp"] = max(mon["max_disp"], disp)
                # tilt-change channel (>= 2 floor tags): a claw tipping about a jaw edge reads almost no displacement above
                rocked = rw.update(o)
                if mon["onset"] is None and (disp >= thr or rocked):
                    mon["onset"] = float(ctx.co.positions()[i])
                if rocked:
                    mon["rocked"] = True
                    return "onset"                    # the cable is taut and the claw tips: stop pulling at once
                if disp >= bearing_d:
                    return "onset"
                if tilt_angle(o.R) > st.max_tilt_rad:
                    return "tilt"
                return None

            ppu = ctx.ppu(i)
            delta = np.zeros(4)
            delta[i] = -st.max_slack_m[i] / ppu
            rate = st.probe_speed_m_s / ppu
            plan = plan_cable_move(ctx.co.positions(), delta, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                   label=f"slack {sid}")
            r = self._execute(plan, S, suspended=False, monitor=monitor)
            if r.reason != "onset":
                if r.ok:
                    raise StartupAbort(S, f"station {sid}: no taut onset within {st.max_slack_m[i] * 1e3:.0f} mm "
                                          "(cable unattached, wrong winding direction, or station order)")
                raise StartupAbort(S, f"station {sid}: {r.reason}")
            ctx.wait(st.settle_s)
            end = self._still(state=S)
            # slide direction from the camera-frame displacement; a rocking claw moved its body origin by tilt x lever with the
            # tags (almost) not moving, so its displacement is the general one (the measured tilt change is used: 5-sigma rule)
            d = (cam_displacement if mon["rocked"] else floor_displacement)(end, ref)[0]
            o = OnsetSample(i, float(ctx.co.positions()[i]), end.p, end.R, end.cov,
                            bearing=math.atan2(d[1], d[0]), bearing_from=ref.p.copy(),
                            bearing_sigma=st.bearing_sigma_rad)
            ctx.onsets.append(o)
            taken = -(o.P - plan.start[i]) * ppu
            self.rep.measurements[f"slack_{sid}_m"] = taken
            self.rep.measurements[f"rocking_{sid}_max_tilt_rad"] = rw.max_tilt_rad
            ctx.log(f"[startup] {sid} taut after {taken * 1e3:.1f} mm, slide {np.linalg.norm(d) * 1e3:.1f} mm "
                    f"toward {math.degrees(o.bearing):.0f} deg (marker frame)"
                    + (f"; the claw ROCKED {rw.last_tilt_rad * 1e3:.1f} mrad on its jaws (limit {rw.last_thr_rad * 1e3:.1f}), "
                       "stopped at the tilt onset" if mon["rocked"] else ""))
            back = np.zeros(4)
            back[i] = st.onset_backoff_m / ppu
            rb = self._execute(plan_cable_move(ctx.co.positions(), back, rate * 2, rate * 10,
                                               segment_s=cfg.motion.segment_s, label=f"backoff {sid}"),
                               S, suspended=False)
            if not rb.ok:
                raise StartupAbort(S, f"station {sid}: backoff {rb.reason}")
        # bearings vs anchor entries, then the first fit
        claw = np.array([0.5 * (o.p + o.bearing_from) for o in ctx.onsets])
        psi, cov, rms = align_from_bearings(ctx.priors, claw, [o.bearing for o in ctx.onsets],
                                            st.bearing_sigma_rad)
        self.rep.measurements["bearing_rms"] = rms
        if rms > st.bearing_rms_max:
            raise StartupAbort(S, f"slide directions disagree with the anchor entries (RMS {rms:.1f} sigma): "
                                  "check station order/wiring A-D and anchor coordinates")
        res = self._pumped(ctx.cal.fit, [], ctx.onsets, psi_inits=[psi])
        ctx.apply_result(res, "onset")
        self.rep.measurements["L0_onset"] = res.L0.tolist()

    # ---------------------------------------------------------- INITIAL_LIFT
    def _packet(self, p_from_R, p_to_R, speed, label, state, monitor=None):
        ctx = self.ctx
        geo = ctx.model.geometry
        dL = geo.lengths(p_to_R) - geo.lengths(p_from_R)
        P = ctx.co.positions()
        newP = []
        for i, sid in enumerate(IDS):
            m = ctx.model.maps[sid]
            newP.append(m.position(m.length(P[i]) + dL[i]))
        delta = np.array(newP) - P
        if np.max(np.abs(delta)) < 0.5:
            return None
        rate = self._cable_rate(speed)
        plan = plan_cable_move(P, delta, rate, rate / 0.2, segment_s=self.cfg.motion.segment_s, label=label)
        return self._execute(plan, state, suspended=True, monitor=monitor)

    def initial_lift(self):
        cfg, ctx, S = self.cfg, self.ctx, "INITIAL_LIFT"
        st = cfg.startup
        sp = self._still(state=S)
        p0 = ctx.room_pose(sp)
        ctx.ledger.claw_supported = False          # durable BEFORE the first command that can lift
        ctx.persist()
        # bring all four to just-taut at the current pose (they were backed off)
        P = ctx.co.positions()
        target = ctx.model.positions_for(p0)
        rate = self._cable_rate(st.probe_speed_m_s * 2)
        drag = {"bad": None, "next": 0.0}
        dw = DragWatch(sp, floor_m=max(3 * st.onset_translation_m, self.DRAG_WATCH_FLOOR_M), k=st.onset_noise_k,
                       n=self.DRAG_WATCH_FRAMES)
        watch = self._pretension_watch(dw, self._rock_watch(sp, "pretension"), drag)
        r = self._execute(plan_cable_move(P, target - P, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                          label="pretension"), S, suspended=False, monitor=watch)
        if not r.ok:
            raise StartupAbort(S, f"pretension: {r.reason} ({drag['bad']})")
        zf = -float(cfg.claw.lowest_point_body_m[2])
        lifted = 0.0
        cur = p0.copy()
        while True:
            if lifted >= st.max_lift_m:
                raise StartupAbort(S, f"no {st.target_clearance_m * 1e3:.0f} mm clearance after "
                                      f"{st.max_lift_m * 1e3:.0f} mm commanded lift", suspended=True)
            nxt = cur + [0, 0, st.lift_packet_m]
            r = self._packet(cur, nxt, st.probe_speed_m_s * 2, "lift", S)
            if r is not None and not r.ok:
                raise StartupAbort(S, f"lift packet stopped: {r.reason}", suspended=True)
            lifted += st.lift_packet_m
            cur = nxt
            ctx.wait(st.settle_s)
            sp2 = self._still(n=3, state=S, suspended=True)
            obs = ctx.room_pose(sp2)
            rise = obs[2] - p0[2]
            drift = float(np.linalg.norm(obs[:2] - p0[:2]))
            tilt = sp2.tilt_rad
            if drift > st.max_lateral_drift_m:
                raise StartupAbort(S, f"lateral drift {drift * 1e3:.0f} mm during lift", suspended=True)
            if tilt > st.max_tilt_rad:
                raise StartupAbort(S, f"tilt {math.degrees(tilt):.1f} deg during lift", suspended=True)
            if lifted - rise > st.lift_slack_budget_m:
                raise StartupAbort(S, f"claw rose {rise * 1e3:.0f} mm for {lifted * 1e3:.0f} mm commanded: "
                                      "a cable is slack/unattached or the model is badly wrong", suspended=True)
            if sp2.p[2] - zf >= st.target_clearance_m:
                self.rep.measurements["lift_commanded_m"] = lifted
                self.rep.measurements["lift_observed_m"] = float(rise)
                ctx.persist()
                return

    # ---------------------------------------------------- VISUAL_INITIALIZATION
    def _sample(self, kind, state):
        ctx = self.ctx
        ctx.wait(self.cfg.startup.settle_s)
        sp = self._still(n=self.cfg.calibration.noise_capture_frames, state=state, suspended=True)
        self._survey_topup(state)                  # the claw hangs still: sheets seen from this pose may now be surveyed
        return PoseSample(ctx.co.positions().copy(), sp.p, sp.R, sp.cov, kind, ctx.now_s(), att_sigma_rad=sp.att_sigma_rad)

    def _survey_topup(self, state):
        """Survey top-up while suspended: the still frames offered since the last call (``FloorBoardSurveyor.offer``) are given to the
        survey; sheets that the resting claw could not see but this pose does, and that now have enough views, are surveyed, the
        layout file is updated and the excitation design sees them. Nothing moves; the cost is a few PnP solves and, when a
        sheet is ready, one bundle adjustment (~1 s) -- so the flush runs on a worker thread while this thread keeps pumping the
        station keep-alive (``_pumped``); an unpumped stall of that length would outlast ``faults.lease_s``."""
        ctx = self.ctx
        sv = getattr(ctx, "board_survey", None)
        if sv is None or not self.cfg.startup.board_survey:
            return
        out = self._pumped(sv.flush)
        rep = self.rep.measurements.get("board_survey")
        if out is None or rep is None or not (out["new"] or out["cleared"]):
            return
        ctx.floor_board = sv.geometry()
        rep.update(sv.report())
        rep.setdefault("topups", []).append({"state": state, "t_s": round(ctx.now_s(), 1), **{k: v for k, v in out.items() if k != "cleared"},
                                              "cleared": {int(k): v for k, v in out["cleared"].items()}})
        ctx.log(f"[startup] floor board survey top-up in {state}: sheets {out['new']} surveyed from {out['frames']} frames of the hanging claw"
                + (f"; cleared {sorted(out['cleared'])}" if out["cleared"] else "") + f" ({len(rep['surveyed_ids'])} of {rep['expected']} known)")

    # ------------------------------------------------------------ slack probe
    # Fraction of the measured slack's 1-sigma by which a probed cable is left on the slack side of its onset (so it
    # cannot pull the claw toward itself and loosen a neighbour). 0 = leave it just taut. Simulation showed no
    # difference (seeds 1, 2, single tag: residual truth slack of probed readings mean -0.28 mm, max 1.34 mm at 0
    # against max 0.78 / 1.20 mm at 0.5; verification/slack_probe_results.md), so the simplest choice stays.
    PROBE_MARGIN_SIGMA = 0.0
    # The claw moving this far from the reference during one cable's probe without a significant onset means the
    # vision or the response model cannot be trusted: abort (hold) rather than keep retracting. The limit is the
    # larger of this value and twice the motion at which the onset is expected to become significant.
    PROBE_MAX_DISP_M = 0.010

    def _probe_geometry(self, i, ref):
        """Predicted claw response to retracting cable ``i`` at the pose of ``ref`` and what the vision noise
        allows: (v, |v|, sigma_proj, rho) with ``v`` the response (marker frame, per metre of retraction),
        ``sigma_proj`` the 1-sigma of a differential position measurement along it (reference + one
        measurement, both averaged over the frames of ``ref``) and ``rho`` the over-retraction beyond the
        taut point at which the onset becomes detectable (max(floor, k sigma) / |v|)."""
        ctx, st = self.ctx, self.cfg.startup
        v = ctx.T_R_M[:3, :3].T @ probe_response(ctx.model.geometry, ctx.room_pose(ref), i, R=ctx.room_R(ref))
        vn = float(np.linalg.norm(v))
        vhat = v / vn
        sig_proj = math.sqrt(float(vhat @ (2.0 * ref.cov_cam) @ vhat))       # camera-frame noise: reference + one measurement
        rho = max(st.probe_onset_translation_m, st.onset_noise_k * sig_proj) / vn
        return v, vn, sig_proj, rho

    def _probe_payout(self, i, back, state):
        """Pay out ``back`` metres of cable ``i`` (undo part or all of a probe retraction; below half a microstep nothing)."""
        ctx, cfg, st = self.ctx, self.cfg, self.cfg.startup
        if back > 0.5 * ctx.ppu(i):
            pb = np.zeros(4)
            pb[i] = back / ctx.ppu(i)
            rate = st.probe_speed_m_s
            rb = self._execute(plan_cable_move(ctx.co.positions(), pb, rate / ctx.ppu(i), rate / ctx.ppu(i) / 0.2,
                                               segment_s=cfg.motion.segment_s, label=f"probe back {IDS[i]}"),
                               state, suspended=True)
            if not rb.ok:
                raise StartupAbort(state, f"station {IDS[i]}: probe pay-out {rb.reason}", suspended=True)

    def _probe_cable(self, i, ref, n_frames, state):
        """Retract cable ``i`` in small steps until the claw moves (taut onset), measure the slack, leave
        the cable just taut. ``ref`` is a still pose (``n_frames`` frames) with the cable as it is. Returns a
        record dict. Aborts (hold) when the cable never goes taut within ``probe_max_m``."""
        ctx, cfg = self.ctx, self.cfg
        st, sid = cfg.startup, IDS[i]
        q_room = ctx.room_pose(ref)
        v, vn, sig_proj, rho = self._probe_geometry(i, ref)
        rec = {"station": sid, "status": "ok", "response_per_m": vn, "detect_overshoot_m": rho,
               "sigma_proj_m": sig_proj, "frames": n_frames}
        rate = st.probe_speed_m_s
        # The series is a DIFFERENTIAL one: displacements relative to ``ref`` measured in the camera frame under one
        # reference tilt (perception.cam_displacement), so the absolute pose's tilt-lever noise does not enter. The
        # reference is the first point (its own camera-frame noise); the offset to the absolute position is a constant
        # that the hinge fit's free ``p0`` absorbs.
        r_arr, P_arr, C_arr = [0.0], [ref.p], [ref.cov_cam]
        vhat = v / vn
        r, step, n_steps, a = 0.0, st.probe_step_m, 0, None
        while True:
            if r >= st.probe_max_m - 1e-9:
                raise StartupAbort(state, f"station {sid}: no taut onset within {st.probe_max_m * 1e3:.0f} mm of probe "
                                          f"retraction at claw {np.round(q_room, 3).tolist()} (cable detached or "
                                          "slipping on its spool, or the model is badly wrong)", suspended=True)
            h = min(step, st.probe_max_m - r)
            ppu = ctx.ppu(i)
            P_b = float(ctx.co.positions()[i])
            delta = np.zeros(4)
            delta[i] = -h / ppu
            plan = plan_cable_move(ctx.co.positions(), delta, rate / ppu, rate / ppu / 0.2,
                                   segment_s=cfg.motion.segment_s, label=f"probe {sid}")
            res = self._execute(plan, state, suspended=True)
            if not res.ok:
                raise StartupAbort(state, f"station {sid}: probe motion {res.reason}", suspended=True)
            r += (P_b - float(ctx.co.positions()[i])) * ppu
            n_steps += 1
            ctx.wait(st.probe_settle_s)
            sp = self._still(n=n_frames, state=state, suspended=True)
            d_k, c_k, _ = cam_displacement(sp, ref)
            r_arr.append(r)
            P_arr.append(ref.p + d_k)
            C_arr.append(c_k)
            a = hinge_analysis(r_arr, P_arr, C_arr, v, st.probe_response_sigma * vn, st.onset_noise_k,
                               st.probe_onset_translation_m)
            if a["detected"]:
                break
            # The noise of THIS measurement (the board may have lost tags since the reference: fewer tags, more noise) decides
            # whether the onset can still be resolved within the allowed over-retraction; if not, back out and skip the
            # cable at this pose (as the pre-probe check does) instead of retracting blind or aborting on noise.
            sig_k = math.sqrt(float(vhat @ (c_k + ref.cov_cam) @ vhat))
            rho_k = max(st.probe_onset_translation_m, st.onset_noise_k * sig_k) / vn
            if rho_k > st.probe_overshoot_max_m:
                self._probe_payout(i, r, state)
                rec.update(status="skipped", slack_m=float("nan"), peak_m=float(r), final_m=0.0, steps=n_steps,
                           detect_overshoot_m=float(rho_k),
                           reason=f"vision too noisy during the probe ({int(sp.n_tags)} tag(s) in view): detecting onset needs "
                                  f"{rho_k * 1e3:.1f} mm of over-retraction (> {st.probe_overshoot_max_m * 1e3:.1f} mm); "
                                  f"{r * 1e3:.1f} mm paid back")
                return rec
            moved = float(np.linalg.norm(d_k))
            if moved > max(self.PROBE_MAX_DISP_M, 2.0 * rho * vn):
                raise StartupAbort(state, f"station {sid}: claw moved {moved * 1e3:.1f} mm during the probe without a "
                                          "significant onset (vision or response model unreliable)", suspended=True)
            step = min(max(st.probe_step_m, 0.5 * r), st.probe_max_step_m)
        s_hat, sig_s = a["s"], a["sigma_s"]
        r_final = min(max(s_hat - self.PROBE_MARGIN_SIGMA * sig_s, 0.0), r)
        self._probe_payout(i, r - r_final, state)
        rec.update(slack_m=float(s_hat), sigma_m=float(sig_s), peak_m=float(r), final_m=float(r_final),
                   steps=n_steps, significance=float(a["sig"]), response_fit_per_m=float(np.linalg.norm(a["w"])))
        return rec

    def _probe_pose(self, state):
        """Probe the cables at the current (suspended) pose, one at a time, leaving each just taut.

        Vision decides what is possible: from a reference still pose, each cable's detection over-retraction
        ``rho`` is predicted; the frames per measurement are raised (up to ``probe_frames_max``) until ``rho`` is
        within ``probe_overshoot_max_m`` (this bounds the tension excursion on a taut cable); a cable that still
        does not make it is skipped (its reading keeps the fit's slack hypothesis selection). Up to
        ``probe_rounds`` rounds: later rounds re-probe a cable only when the claw has since moved toward its
        anchor by a detectable amount (a later probe loosened it). The caller restores the positions."""
        ctx, st = self.ctx, self.cfg.startup
        t0 = ctx.now_s()
        k = st.onset_noise_k
        recs = {}
        n_base = st.probe_frames
        ref = self._still(n=n_base, state=state, suspended=True)
        need = {}
        for i in range(4):
            _, _, _, rho = self._probe_geometry(i, ref)
            n_i = n_base if rho <= st.probe_overshoot_max_m else int(math.ceil(n_base * (rho / st.probe_overshoot_max_m) ** 2))
            if n_i <= st.probe_frames_max:
                need[i] = n_i
            else:
                recs[i] = {"station": IDS[i], "status": "skipped", "detect_overshoot_m": rho,
                           "reason": f"vision too noisy: detecting onset needs {rho * 1e3:.1f} mm of over-retraction "
                                     f"(> {st.probe_overshoot_max_m * 1e3:.1f} mm) even with {st.probe_frames_max} frames"}
        todo = sorted(need)
        n_pose = max(need.values(), default=n_base)
        n_rounds = 0
        if todo and n_pose > n_base:
            ref = self._still(n=n_pose, state=state, suspended=True)
        for rnd in range(st.probe_rounds if todo else 0):
            if not todo:
                break
            n_rounds += 1
            done_pose = {}                                        # cable -> still pose right after it was finished
            for i in todo:
                rec = self._probe_cable(i, ref, n_pose, state)
                rec["round"] = rnd
                if i in recs and recs[i].get("status") == "ok":
                    rec["slack_first_round_m"] = recs[i].get("slack_m")
                recs[i] = rec
                ref = self._still(n=n_pose, state=state, suspended=True)
                done_pose[i] = ref
            todo = []
            if rnd + 1 < st.probe_rounds:
                U = ctx.model.geometry.unit_vectors(ctx.room_pose(ref))
                Rm = ctx.T_R_M[:3, :3].T
                for i, pose in done_pose.items():
                    u = Rm @ U[i]
                    d_m, c_a, c_b = cam_displacement(ref, pose)   # camera-frame motion since cable i was finished
                    dist = float(u @ d_m)                         # ... toward anchor i
                    thr = max(st.probe_onset_translation_m, k * math.sqrt(float(u @ (c_a + c_b) @ u)))
                    if dist >= thr:
                        todo.append(i)
        taut = np.array([recs[i]["status"] == "ok" for i in range(4)])
        sigma = np.array([recs[i].get("sigma_m", 0.0) * (1.0 + self.PROBE_MARGIN_SIGMA) if taut[i] else 0.0
                          for i in range(4)])
        slack = [recs[i].get("slack_m", float("nan")) for i in range(4)]
        return {"taut": taut, "sigma_m": sigma, "slack_m": slack, "rounds": n_rounds, "t_s": ctx.now_s() - t0,
                "frames": n_pose, "cables": {IDS[i]: recs[i] for i in range(4)}}

    def _restore_positions(self, P_target, state):
        """Back to the model-consistent motor positions the planner started from (pay-out only)."""
        ctx, cfg, st = self.ctx, self.cfg, self.cfg.startup
        delta = np.asarray(P_target, float) - ctx.co.positions()
        if np.max(np.abs(delta)) < 0.5:
            return
        ppus = np.array([ctx.ppu(j) for j in range(4)])
        rate = st.probe_speed_m_s / float(np.min(ppus))
        r = self._execute(plan_cable_move(ctx.co.positions(), delta, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                          label="probe restore"), state, suspended=True)
        if not r.ok:
            raise StartupAbort(state, f"probe restore: {r.reason}", suspended=True)

    def _sample_probed(self, kind, state):
        """A calibration sample, preceded by the slack probe when enabled (all cables just taut)."""
        if not self.cfg.startup.slack_probe:
            return self._sample(kind, state)
        ctx = self.ctx
        P_before = ctx.co.positions().copy()
        ctx.wait(self.cfg.startup.settle_s)
        rec = self._probe_pose(state)
        smp = self._sample(kind, state)
        smp.taut, smp.taut_sigma_m = rec["taut"], rec["sigma_m"]
        smp.probe = {k_: v for k_, v in rec.items() if k_ != "sigma_m"}
        smp.probe["sigma_m"] = rec["sigma_m"].tolist()
        smp.probe["taut"] = rec["taut"].tolist()
        self._restore_positions(P_before, state)
        self.probe_log.append(dict(smp.probe, kind=kind, state=state, z_m=float(smp.p[2])))
        return smp

    def visual_init(self):
        ctx, S = self.ctx, "VISUAL_INITIALIZATION"
        s = self._sample_probed("fit", S)
        ctx.samples = [s]
        res = self._pumped(ctx.cal.fit, ctx.samples, ctx.onsets, L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
        ctx.apply_result(res, "visual")
        self.rep.measurements["L0_visual"] = res.L0.tolist()

    # ------------------------------------------------------------ CALIBRATION
    def _feasible(self, q_R, R_M, min_z):
        ctx, cfg = self.ctx, self.cfg
        if q_R[2] < min_z:
            return False
        if ctx.ws.violations(ctx.model.geometry, q_R):
            return False
        t = tension_distribution(ctx.model.geometry, q_R, cfg.claw.mass_kg, t_min=cfg.motion.min_tension_n,
                                 t_max=cfg.motion.max_tension_n * 0.75,
                                 accel=(0.0, 0.0, cfg.motion.dynamic_accel_m_s2))
        if not t.feasible:
            return False
        qM = to_marker(ctx.T_R_M, q_R)
        for R_try in self._attitudes_at(qM, R_M):
            T_M_B = make_T(R_try, qM)
            if self.board is not None:
                ok = self.board.visible(ctx.camera, ctx.T_B_C, T_M_B,
                                        min_side_px=cfg.camera.min_marker_pixels * 1.2, margin_px=30)
            else:
                ok = marker_visible(ctx.camera, ctx.T_B_C, T_M_B, cfg.marker.edge_m,
                                    min_side_px=cfg.camera.min_marker_pixels * 1.2, margin_px=30)
            if not ok:
                return False
        return True

    # tilt the claw may differ from its prediction by when it gets there (mm-level length inconsistencies tilt a
    # rigid claw on four spaced lines by a few degrees; verified in the rigid-body simulator): visibility is required
    # over this cone, not only at the nominal attitude.
    VISIBILITY_TILT_RAD = math.radians(4.0)

    def _attitudes_at(self, qM, R_M):
        """Attitudes (marker frame) at which the marker must be visible from pose ``qM``: the held one for a common
        point claw (unchanged), else the statics prediction at the held yaw and its +-tilt neighbours."""
        ctx = self.ctx
        if not ctx.model.geometry.spaced:
            return [R_M]
        R0 = ctx.cal.predicted_R(ctx.result.anchors_M, qM)
        from .frames import rot_x, rot_y
        t = self.VISIBILITY_TILT_RAD
        return [R0] + [rot(sg * t) @ R0 for rot in (rot_x, rot_y) for sg in (1, -1)]

    def _stage(self, name, center_R, half, n_fit, n_wit, R_M, min_z, grid):
        ctx, cfg = self.ctx, self.cfg
        cands = [q for q in box_candidates(center_R, half, grid) if self._feasible(q, R_M, min_z)]
        if len(cands) < n_fit + n_wit:
            raise StartupAbort("CALIBRATION", f"{name}: only {len(cands)} feasible visible poses "
                                              f"(need {n_fit + n_wit})", suspended=True)

        def cov_fn(qM):
            # the same model as the detector: Cramer-Rao covariance of the corners that would be in view (one tag, or every
            # tag of the board in the image), propagated to the claw
            corners = None
            if self.board is not None:
                corners = self.board.visible_corners(ctx.camera, ctx.T_B_C, make_T(R_M, qM),
                                                     min_side_px=cfg.camera.min_marker_pixels * 1.2, margin_px=30)
            return predicted_vision_cov(ctx.camera, ctx.T_B_C, make_T(R_M, qM), cfg.marker.edge_m, corners_M=corners,
                                        pixel_sigma=cfg.camera.corner_sigma_px, inflate=cfg.camera.pose_cov_inflate,
                                        floor_rad=cfg.claw.vision_attitude_floor_rad)
        candM = [to_marker(ctx.T_R_M, q) for q in cands]
        here = to_marker(ctx.T_R_M, ctx.model.pose_from_positions(ctx.co.positions())[0])
        fitM, witM = design_excitation(ctx.cal, ctx.result, candM, n_fit, cov_fn=cov_fn,
                                       existing_M=[s.p for s in ctx.samples], start_M=here, n_witness=n_wit)
        for kind, pts in (("fit", fitM), ("witness", witM)):
            for qM in pts:
                q = to_room(ctx.T_R_M, qM)
                try:
                    plan = plan_line_from(ctx.model, ctx.co.positions(), q, ctx.lim, ws=ctx.ws,
                                          label=f"{name} {kind}")
                except PlanError as e:
                    raise StartupAbort("CALIBRATION", f"{name}: {e}", suspended=True)
                r = self._execute(plan, "CALIBRATION", suspended=True)
                if not r.ok:
                    raise StartupAbort("CALIBRATION", f"{name}: motion {r.reason}", suspended=True)
                ctx.samples.append(self._sample_probed(kind, "CALIBRATION"))

    def calibrate(self):
        ctx, cfg, S = self.ctx, self.cfg, "CALIBRATION"
        cc = cfg.calibration
        st = cfg.startup
        zf = -float(cfg.claw.lowest_point_body_m[2])
        min_z = zf + st.target_clearance_m
        R_M = ctx.samples[-1].R
        here = ctx.model.pose_from_positions(ctx.co.positions())[0]
        lb = np.asarray(cc.local_box_m)
        c_local = np.array([here[0], here[1], max(here[2], min_z + lb[2] + 0.01)])
        self._stage("local", c_local, lb, max(8, cc.min_samples // 2), max(2, cc.witness_samples // 2),
                    R_M, min_z, (5, 5, 3))
        res = self._pumped(ctx.cal.fit, [s for s in ctx.samples if s.kind == "fit"], ctx.onsets, L0_init=ctx.result.L0,
                          psi_inits=[ctx.result.psi])
        wit = [s for s in ctx.samples if s.kind == "witness"]
        rep_local = ctx.cal.validate(res, wit)
        hard = [r for r in rep_local["reasons"] if not r.startswith(("prior-dominated", "only"))]
        if hard:
            raise StartupAbort(S, "local calibration rejected: " + "; ".join(hard), suspended=True)
        ctx.apply_result(res, "visual")
        self.rep.measurements["local"] = {"weak": [d for _, d in res.identifiability.weak],
                                          "witness_rms_m": rep_local["witness_rms_m"]}
        # Grow the excitation volume in steps, refitting between them, so the
        # model never extrapolates far: a model error at a commanded pose makes
        # the claw hang on three cables (the fourth goes slack).
        eb = np.asarray(cc.expanded_box_m)
        mk = to_room(ctx.T_R_M, [0, 0, 0])
        for name, scale, frac in (("intermediate", 0.45, 0.4), ("expanded", 1.0, 0.6)):
            half = np.maximum(eb * scale, lb)
            c = np.array([mk[0], mk[1], min_z + half[2] + 0.02])
            self._stage(name, c, half, max(6, int(cc.min_samples * frac)),
                        max(2, int(round(cc.witness_samples * frac))), R_M, min_z, (7, 7, 4))
            if name != "expanded":
                res = self._pumped(ctx.cal.fit, [s for s in ctx.samples if s.kind == "fit"], ctx.onsets,
                                  L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
                ctx.apply_result(res, "visual")
        fit = [s for s in ctx.samples if s.kind == "fit"]
        wit = [s for s in ctx.samples if s.kind == "witness"]
        res = self._pumped(ctx.cal.fit, fit, ctx.onsets, L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
        vol = self._work_volume(res)
        report = ctx.cal.validate(res, wit, [to_marker(res.T_R_M, q) for q in vol])
        self.cal_report = report
        self.rep.measurements["calibration"] = {k: v for k, v in report.items()}
        ctx.save("calibration.json", {"result": res.to_jsonable(), "validation": report, "slack_probe": self.probe_log})
        if self.probe_log:
            self.rep.measurements["slack_probe"] = self._probe_summary()
        hard = [r for r in report["reasons"] if not r.startswith(("prior-dominated", "predicted length sigma"))]
        if hard:
            raise StartupAbort(S, "calibration rejected: " + "; ".join(hard), suspended=True)
        ctx.apply_result(res, "visual")
        self.rep.measurements["absolute_sigma_m"] = ctx.cal.absolute_sigma(res).tolist()
        ok_pts = [q for q in vol if np.max(ctx.cal.length_sigma(res, to_marker(res.T_R_M, q))) <= cc.length_sigma_max_m]
        ctx.validated_volume = np.array(ok_pts)
        ctx.save_model()
        if report["accepted"]:
            ctx.ledger.set_level("LOCAL_ONLY")      # VERIFIED is decided in REFERENCE_VERIFICATION (D26)
        else:
            ctx.ledger.set_level("LOCAL_ONLY", reasons=report["reasons"])
            self.rep.reasons.extend(report["reasons"])
        self.rep.measurements["validated_points"] = f"{len(ok_pts)}/{len(vol)}"

    def _probe_summary(self):
        L = self.probe_log
        ok = [(i, r) for r in L for i, c in enumerate(r["taut"]) if c]
        sl = np.array([r["slack_m"][i] for i, r in ok]) if ok else np.zeros(0)
        return {"poses": len(L), "time_s": float(sum(r["t_s"] for r in L)),
                "readings_probed": len(ok), "readings_skipped": 4 * len(L) - len(ok),
                "slack_median_m": float(np.median(sl)) if len(sl) else None,
                "slack_max_m": float(sl.max()) if len(sl) else None,
                "peak_retraction_max_m": float(max((c.get("peak_m", 0.0) for r in L for c in r["cables"].values()),
                                                   default=0.0))}

    def _work_volume(self, res, n=(5, 5, 3)):
        ctx, cfg = self.ctx, self.cfg
        lo, hi = ctx.ws.lo.copy(), ctx.ws.hi.copy()
        lo[2] += cfg.startup.target_clearance_m
        pts = box_candidates((lo + hi) / 2, (hi - lo) / 2, n)
        geo = geometry_from_config(cfg, res.anchors_room, ctx.claw_yaw_room)
        return [q for q in pts if tension_distribution(geo, q, cfg.claw.mass_kg, t_min=cfg.motion.min_tension_n,
                                                       t_max=cfg.motion.max_tension_n).feasible]

    # ------------------------------------------------- REFERENCE_VERIFICATION
    def _margin_volume(self, res, n=(9, 9, 5)):
        """Commanded-workspace poses (room frame, tension-feasible, top plane and all four walls included)."""
        ctx, cfg = self.ctx, self.cfg
        lo, hi = ctx.ws.lo.copy(), ctx.ws.hi.copy()
        lo[2] = min(lo[2] + cfg.startup.target_clearance_m, hi[2])
        pts = box_candidates((lo + hi) / 2, (hi - lo) / 2, n)
        geo = geometry_from_config(cfg, res.anchors_room, ctx.claw_yaw_room)
        return [q for q in pts if tension_distribution(geo, q, cfg.claw.mass_kg, t_min=cfg.motion.min_tension_n,
                                                       t_max=cfg.motion.max_tension_n).feasible]

    def assess_margin_trust(self, res=None) -> dict:
        """Decision D26: may the robot use the whole workspace without beads? Evaluated at every startup.

        (a) the final calibration was accepted (the five criteria of ``Calibrator.validate``);
        (b) ``startup.slack_probe`` was on for every suspended sample and the witness chi-squared is consistent
            (otherwise the predicted sigma is not honest: slack reads as length error);
        (c) ``k * sigma <= margin`` for both margins, ``k = calibration.bead_k_sigma``, over the whole commanded
            workspace, with sigma from ``Calibrator.boundary_sigma``, the 1-sigma of the claw's position relative
            to the boundary the margin protects:
              ceiling margin (below the fitted anchors): claw-to-anchor vertical and distance error, which does
                not involve the room registration;
              workspace margin (inside the walls, a room-frame boundary): the room x / y error, which adds the
                marker registration (x, y, yaw x lever arm) to the claw position error.
            The payout-scale uncertainty (``calibration.payout_scale_sigma`` x the cable-length change from the
            nearest fitted sample) is added to every pose as an independent per-cable length error.

        Returns a JSON-able dict (also stored in the ledger); ``ok`` only if (a), (b), (c) hold and every station
        reference and the marker registration are valid.
        """
        ctx, cfg = self.ctx, self.cfg
        cc, mo, su = cfg.calibration, cfg.motion, cfg.startup
        res = ctx.result if res is None else res
        k = float(cc.bead_k_sigma)
        out = {"k": k, "ceiling_margin_m": float(mo.ceiling_margin_m), "workspace_margin_m": float(mo.workspace_margin_m),
               "ok": False, "reasons": []}
        why = out["reasons"]
        rep = self.cal_report
        # (a)
        out["calibration_accepted"] = bool(rep and rep["accepted"])
        if rep is None:
            why.append("no calibration acceptance report (calibration did not complete)")
        elif not rep["accepted"]:
            why.append("calibration not accepted: " + "; ".join(rep["reasons"]))
        # (b)
        smp = list(ctx.samples)
        n_probed = sum(1 for x in smp if x.probe is not None)
        out["slack_probe"] = bool(su.slack_probe)
        out["probed_samples"] = f"{n_probed}/{len(smp)}"
        out["readings_probed"] = (self._probe_summary()["readings_probed"] if self.probe_log else 0)
        chi2 = None if rep is None else rep.get("witness_chi2_dof")
        out["witness_chi2_dof"] = None if chi2 is None or not math.isfinite(chi2) else float(chi2)
        out["witness_chi2_max"] = float(cc.norm_rms_max) ** 2
        if not su.slack_probe:
            why.append("slack probe was off: the predicted sigma is not honest (slack reads as length error); "
                       "enable startup.slack_probe")
        elif not smp or n_probed != len(smp):
            why.append(f"the slack probe did not cover every suspended sample ({n_probed}/{len(smp)})")
        if out["witness_chi2_dof"] is None:
            why.append("no witness chi-squared (no held-out witness poses)")
        elif out["witness_chi2_dof"] > out["witness_chi2_max"]:
            why.append(f"witness chi-squared {out['witness_chi2_dof']:.2f} > {out['witness_chi2_max']:.1f}: "
                       "errors at held-out poses exceed their predicted sigma")
        # (c)
        if res is not None and ctx.ws is not None:
            fit = [x for x in smp if x.kind == "fit"]
            geo = geometry_from_config(cfg, res.anchors_M, ctx.cal.hold_yaw_M)
            Ls = np.array([geo.lengths(x.p, x.R) for x in fit]) if fit else None
            pts = self._margin_volume(res)
            worst = {"ceiling": (-1.0, None, ""), "wall": (-1.0, None, "")}
            for q in pts:
                qM = to_marker(res.T_R_M, q)
                extra = None
                if Ls is not None:
                    extra = cc.payout_scale_sigma * np.min(np.abs(Ls - geo.lengths(qM, ctx.cal.predicted_R(res.anchors_M, qM))[None, :]), axis=0)
                b = ctx.cal.boundary_sigma(res, qM, extra_len_sigma=extra)
                comps = {"ceiling": (("vertical", b["ceiling_z"]), ("distance", b["ceiling_dist"])),
                         "wall": (("x", b["wall_x"]), ("y", b["wall_y"]))}
                for key in worst:
                    if b[key] > worst[key][0]:
                        worst[key] = (b[key], np.asarray(q, float), max(comps[key], key=lambda c: c[1])[0])
            out["n_poses"] = len(pts)
            for key, margin in (("ceiling", mo.ceiling_margin_m), ("wall", mo.workspace_margin_m)):
                sg, q, comp = worst[key]
                out[f"sigma_{key}_m"] = float(sg)
                out[f"k_sigma_{key}_m"] = float(k * sg)
                out[f"worst_pose_{key}_room_m"] = None if q is None else [round(float(v), 4) for v in q]
                out[f"worst_component_{key}"] = comp
                if q is None:
                    why.append(f"{key}: no feasible pose in the workspace to evaluate")
                elif k * sg > margin:
                    name = "ceiling margin" if key == "ceiling" else "workspace (wall) margin"
                    what = ("claw-to-anchor " + comp) if key == "ceiling" else ("room-" + comp)
                    why.append(f"{k:g} x sigma = {k * sg * 1e3:.0f} mm ({what} error, sigma {sg * 1e3:.1f} mm) exceeds the "
                               f"{margin * 1e3:.0f} mm {name} at pose {np.round(q, 2).tolist()}")
        else:
            why.append("no calibrated model to evaluate the margins")
        if not ctx.ledger.all_valid() or not ctx.ledger.marker_valid:
            why.append("a station reference or the marker registration is not valid")
        out["ok"] = not why
        return out

    def verify_references(self):
        from .homing import BeadVerifier
        ctx, S = self.ctx, "REFERENCE_VERIFICATION"
        cal_reasons = list(self.rep.reasons)                 # why the calibration itself was not accepted
        outcomes, bead_notes = {}, []
        home = ctx.model.pose_from_positions(ctx.co.positions())[0]
        missing = self.cfg.missing("bead_verification") if self.cfg.startup.bead_search else []
        if not self.cfg.startup.bead_search:
            bead_notes.append("bead search off (startup.bead_search): beads are end-of-travel switches only")
        elif missing:
            bead_notes.append(f"bead verification blocked: unmeasured {missing}")
        else:
            # absolute sigma + spool-model (payout scale) error over the distance
            # between the calibrated region and the bead (review M3)
            Lh = ctx.model.geometry.lengths(home)
            sig_abs = np.hypot(ctx.cal.absolute_sigma(ctx.result),
                               self.cfg.calibration.payout_scale_sigma * np.abs(Lh - np.array(
                                   [s.bead.trigger_length_m for s in self.cfg.stations])))
            bv = BeadVerifier(self.cfg, ctx.co, ctx.model, ctx.lim, ctx.ws, lambda q: sig_abs, log=ctx.log)
            for i, sid in enumerate(IDS):
                out = bv.run(i, p_home=home)
                outcomes[sid] = out
                if out.status == "FAULT":
                    ctx.ledger.invalidate(sid, f"bead verification fault: {out.reason}")
                    raise StartupAbort(S, f"station {sid}: {out.reason}", suspended=True)
                if out.status != "VERIFIED":
                    bead_notes.append(f"bead {sid}: {out.reason}")
                    continue
                bead = self.cfg.stations[i].bead
                for P in out.captures:
                    ctx.cal.beads.append(BeadObs(i, P, bead.trigger_length_m,
                                                 math.hypot(bead.uncertainty_m, 1e-4)))
            if ctx.cal.beads:
                fit = [s for s in ctx.samples if s.kind == "fit"]
                res = self._pumped(ctx.cal.fit, fit, ctx.onsets, L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
                rep = ctx.cal.validate(res, [s for s in ctx.samples if s.kind == "witness"])
                hard = [r for r in rep["reasons"] if not r.startswith("prior-dominated")]
                if hard or res.norm_rms > self.cfg.calibration.norm_rms_max:
                    raise StartupAbort(S, "refit with bead references rejected: " + "; ".join(hard), suspended=True)
                ctx.apply_result(res, "visual+bead")
                for sid, o in outcomes.items():
                    if o.status == "VERIFIED":
                        i = IDS.index(sid)
                        ctx.ledger.set_reference(sid, ctx.co.links[sid].boot, res.L0[i],
                                                 float(ctx.cal.absolute_sigma(res)[i]), "bead", bead=True)
                self.rep.measurements["absolute_sigma_after_beads_m"] = ctx.cal.absolute_sigma(res).tolist()
        self.rep.measurements["beads"] = {s: {"status": o.status, "reason": o.reason, "sigma_m": o.sigma,
                                              "spread_m": o.spread_m,
                                              "residuals_m": [c.residual for c in o.checks]}
                                          for s, o in outcomes.items()}
        # ---- the trust decision (D26)
        margin = self.assess_margin_trust()
        margin["bead_notes"] = bead_notes
        self.rep.measurements["margin_trust"] = margin
        beads_all = bool(outcomes) and all(o.status == "VERIFIED" for o in outcomes.values())
        if beads_all and not cal_reasons:
            basis, reasons = "beads", []
        elif margin["ok"]:
            basis, reasons = "margin", []                    # a BLOCKED bead does not prevent this (D26)
        else:
            basis = None
            reasons = margin["reasons"] + [n for n in bead_notes if not n.startswith("bead search off")]
            # (the calibration's own rejection reasons were already reported by calibrate())
            self.rep.reasons.extend(r for r in reasons if r not in self.rep.reasons
                                    and not (cal_reasons and r.startswith("calibration not accepted")))
        if basis:
            ctx.ledger.set_level("VERIFIED", basis=basis, margin_check=margin)
        else:
            ctx.ledger.set_level("LOCAL_ONLY", reasons=reasons, margin_check=margin)
        ctx.save("trust.json", {"level": ctx.ledger.level, "basis": ctx.ledger.verified_basis,
                                "margin_check": margin, "reasons": ctx.ledger.trust_reasons,
                                "history": ctx.ledger.history})
