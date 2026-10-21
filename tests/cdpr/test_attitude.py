"""D27, no IMU on the claw: vision/statics attitude, the startup camera-mount tilt offset, settle-then-approve grip
gating and the new configuration fields. Everything except the two simulated-startup tests is deterministic and fast."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr.attitude import (SettleResult, estimate_attitude, image_motion_rad_s, mount_offset_from_up,
                                       pendulum_length_m, pendulum_period_s, predicted_tilt_rad, settle_dwell_s,
                                       wait_until_still)
from roomcleaner.cdpr.config import ConfigError, load_config
from roomcleaner.cdpr.frames import (inv_T, make_T, matrix_to_rotvec, planar_T, rot_x, rot_y, rpy_to_matrix,
                                     rotvec_to_matrix, tilt_angle)
from roomcleaner.cdpr.kinematics import geometry_from_config
from roomcleaner.cdpr.perception import PoseObs, VisionSource
from roomcleaner.cdpr.tasks import TaskRunner
from roomcleaner.cdpr.vision.marker import MarkerObservation

from .simkit import SIM, fast_cfg

R_B_C_NOM = rpy_to_matrix(np.pi, 0, 0)                  # camera looks down, image x = body x
T_B_C_NOM = make_T(R_B_C_NOM, [0.0, 0.09, -0.0056])


# ============================================================ camera mount offset
def _up_for(Q_true):
    """Marker normal in camera coordinates for an upright claw whose true mount is nominal @ Q_true."""
    return (R_B_C_NOM @ Q_true).T @ np.array([0.0, 0.0, 1.0])


@pytest.mark.parametrize("seed", range(5))
def test_mount_offset_recovers_the_tilt_error_of_the_mount(seed):
    rng = np.random.default_rng(seed)
    Q_true = rotvec_to_matrix([*rng.normal(0, 0.03, 2), 0.0])           # tilt-only error, a couple of degrees
    off = mount_offset_from_up(R_B_C_NOM, _up_for(Q_true))
    R_corr = R_B_C_NOM @ off.Q
    assert np.allclose(R_corr.T @ np.array([0, 0, 1.0]), _up_for(Q_true), atol=1e-12)    # body z = marker normal
    assert np.isclose(off.angle_rad, np.linalg.norm(matrix_to_rotvec(Q_true)), atol=1e-9)
    # a pure tilt error is recovered completely (both tilt components), and the correction adds no yaw about up
    assert np.allclose(R_corr, R_B_C_NOM @ Q_true, atol=1e-9)
    assert abs(np.linalg.det(off.Q) - 1) < 1e-12 and np.allclose(off.Q @ off.Q.T, np.eye(3), atol=1e-12)


def test_mount_offset_is_identity_for_the_nominal_mount_and_cannot_see_yaw():
    off = mount_offset_from_up(R_B_C_NOM, _up_for(np.eye(3)))
    assert off.angle_rad < 1e-12 and np.allclose(off.Q, np.eye(3))
    # a rotation about the vertical leaves the up vector untouched: unobservable, so left at the nominal value
    yaw_only = rotvec_to_matrix([0, 0, 0.2])
    off2 = mount_offset_from_up(R_B_C_NOM, _up_for(yaw_only))
    assert off2.angle_rad < 1e-9


class FakeFrames:
    """Frame source for a claw with a known true camera mount, pose and per-frame jitter."""

    def __init__(self, T_M_B, Q_true, *, jitter=0.0, seed=0):
        self.T_B_C_true = T_B_C_NOM.copy()
        self.T_B_C_true[:3, :3] = R_B_C_NOM @ Q_true
        self.T_M_B = T_M_B
        self.jitter = jitter
        self.rng = np.random.default_rng(seed)
        self.corners = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float) + 300

    def observe(self, now_us):
        T_C_M = inv_T(self.T_M_B @ self.T_B_C_true)
        if self.jitter:
            T_C_M = T_C_M.copy()
            T_C_M[:3, :3] = rotvec_to_matrix(self.rng.normal(0, self.jitter, 3)) @ T_C_M[:3, :3]
        return MarkerObservation(True, "", T_C_M, 0.3, 50.0, 100.0, self.corners, frame_id=1, capture_us=now_us)


def _vision(frames):
    t = {"us": 0.0}

    def now():
        t["us"] += 100_000
        return t["us"]
    return VisionSource(frames, T_B_C_NOM, 520.0, 0.1524, max_age_s=1.0, now_us=now), t


def _still(v, n=30):
    sp, why = v.still_pose(n, lambda s: None, interval_s=0.0, spread_max_m=1.0)
    assert sp is not None, why
    return sp


def test_vision_tilt_is_read_against_the_corrected_mount():
    Q_true = rotvec_to_matrix([0.025, -0.018, 0.0])
    T_M_B = planar_T(0.1, -0.05, 0.7, 0.52)                                   # upright on the floor, yawed
    v, _ = _vision(FakeFrames(T_M_B, Q_true))
    sp = _still(v, 3)
    assert abs(sp.tilt_rad - 0.0308) < 2e-3                                   # the mount error shows up as a tilt
    off = mount_offset_from_up(v.T_B_C_nominal[:3, :3], sp.up_cam)
    v.set_mount_offset(off.Q)
    sp2 = _still(v, 3)
    assert sp2.tilt_rad < 1e-9 and np.allclose(sp2.p, T_M_B[:3, 3], atol=1e-9)       # exact with noise-free frames
    # the claw later hangs tilted by 3 deg about x: the corrected mount reads it
    tilted = FakeFrames(T_M_B @ make_T(rot_x(math.radians(3)), None), Q_true)
    v.src = tilted
    assert abs(_still(v, 3).tilt_rad - math.radians(3)) < 1e-9
    # without the correction the same claw would read ~1.8 deg too much or too little
    v0, _ = _vision(tilted)
    assert abs(_still(v0, 3).tilt_rad - math.radians(3)) > math.radians(0.5)


def test_mount_offset_measurement_averages_down_the_frame_noise():
    Q_true = rotvec_to_matrix([-0.02, 0.015, 0.0])
    T_M_B = planar_T(0.0, 0.0, 0.3, 0.52)
    errs = []
    for seed in range(6):
        v, _ = _vision(FakeFrames(T_M_B, Q_true, jitter=0.01, seed=seed))        # honest 10 mrad per axis
        sp = _still(v, 30)
        off = mount_offset_from_up(v.T_B_C_nominal[:3, :3], sp.up_cam, sigma_rad=sp.up_sigma_rad, n=sp.n)
        errs.append(np.linalg.norm(matrix_to_rotvec(off.Q @ Q_true.T)))
        assert 0.001 < off.sigma_rad < 0.005                                      # ~14 mrad / sqrt(30)
    assert np.median(errs) < 6e-3 and max(errs) < 12e-3


def test_set_mount_offset_rejects_non_rotations():
    v, _ = _vision(FakeFrames(planar_T(0, 0, 0, 0.5), np.eye(3)))
    with pytest.raises(ValueError):
        v.set_mount_offset(np.diag([1.0, 1.0, 2.0]))


def test_gravity_fusion_is_optional_and_off_by_default():
    """claw.imu = false: no roll/pitch provider is wired anywhere; the optional path still works when one is given."""
    Q_true = np.eye(3)
    T_M_B = planar_T(0.1, -0.05, 0.7, 0.52)
    v, _ = _vision(FakeFrames(T_M_B, Q_true))
    assert v.imu is None
    roll, pitch = 0.02, -0.01
    t = {"us": 0.0}

    def now():
        t["us"] += 1e5
        return t["us"]
    fused = VisionSource(FakeFrames(T_M_B, Q_true), T_B_C_NOM, 520.0, 0.1524, max_age_s=1.0, now_us=now,
                         imu=SimpleNamespace(roll_pitch=lambda: (roll, pitch)))
    o = fused.observe()
    assert o.ok and tilt_angle(o.R) == pytest.approx(math.hypot(roll, pitch), rel=0.02)
    from roomcleaner.cdpr.sim.harness import SimRobot
    r = SimRobot(fast_cfg(), seed=0)
    assert r.vision.imu is None and r.cfg.claw.imu is False
    assert not hasattr(r.claw, "tilt") and not {"roll", "pitch", "tilt_rad", "imu_ok"} & set(r.claw.status())


# ============================================================ pendulum dwell
def test_pendulum_period_from_the_claw_geometry():
    assert pendulum_period_s(0.2) == pytest.approx(2 * math.pi * math.sqrt(0.2 / 9.81))
    cfg = load_config(SIM)
    L = pendulum_length_m(cfg.claw)
    assert L == pytest.approx(0.19638, abs=1e-4)          # attachment plane z = 0, CoM z = -0.196 m
    T = pendulum_period_s(L)
    assert 0.85 < T < 0.95
    # each period carries the margin that covers the compound-pendulum lengthening (tasks.grip_period_margin, 1.25)
    assert settle_dwell_s(cfg.claw, cfg.tasks) == pytest.approx(max(cfg.tasks.grip_settle_min_s,
                                                                   cfg.tasks.grip_settle_periods
                                                                   * cfg.tasks.grip_period_margin * T))


def test_dwell_falls_back_to_the_minimum_when_there_is_no_valid_pendulum():
    cfg = load_config(SIM)
    claw = SimpleNamespace(com_body_m=np.array([0, 0, 0.05]), attachment_points_body_m=np.zeros((4, 3)))
    assert pendulum_length_m(claw) is None                # CoM above the attachment plane: not hanging below it
    assert settle_dwell_s(claw, cfg.tasks) == cfg.tasks.grip_settle_min_s
    assert pendulum_length_m(SimpleNamespace(com_body_m=None, attachment_points_body_m=np.zeros((4, 3)))) is None
    tk = SimpleNamespace(grip_settle_min_s=2.0, grip_settle_periods=5.0, grip_period_margin=1.0)
    short = SimpleNamespace(com_body_m=np.array([0, 0, -0.02]), attachment_points_body_m=np.zeros((4, 3)))
    assert settle_dwell_s(short, tk) == 2.0                # 5 x 0.28 s < the floor
    long = SimpleNamespace(com_body_m=np.array([0, 0, -0.5]), attachment_points_body_m=np.zeros((4, 3)))
    assert settle_dwell_s(long, tk) == pytest.approx(5 * pendulum_period_s(0.5))


# ============================================================ settle gate
class FakeCtx:
    """Just enough context for wait_until_still / estimate_attitude / the grip approval."""

    def __init__(self, cfg, observations, *, R_vision=None):
        self.cfg = cfg
        self.camera = SimpleNamespace(fx=520.0)
        self.t = 0.0
        self.obs = observations                   # callable(t_s) -> PoseObs
        self.waits = []
        self.vision = SimpleNamespace(observe=lambda: self.obs(self.t))
        self.T_R_M = np.eye(4)
        self.mount_sigma_rad = 0.003
        self.model = SimpleNamespace(geometry=SimpleNamespace(R_at=lambda p: np.eye(3)))

    def wait(self, s):
        self.waits.append(s)
        self.t += s


def _obs(t, shift_px=0.0, ok=True, R=None, corners=True):
    if not ok:
        return PoseObs(False, "marker not found", t_us=t * 1e6)
    c = np.array([[100, 100], [200, 100], [200, 200], [100, 200]], float) + shift_px
    return PoseObs(True, "", make_T(np.eye(3) if R is None else R, [0, 0, 0.5]), np.eye(3) * 1e-6, t * 1e6,
                   corners=c if corners else None, up_cam=np.array([0, 0, -1.0]))


def test_image_motion_is_pixel_shift_over_focal_length_and_dt():
    a, b = _obs(0.0), _obs(0.2, shift_px=1.04)
    assert image_motion_rad_s(a, b, 520.0) == pytest.approx(np.hypot(1.04, 1.04) / (520 * 0.2))
    assert image_motion_rad_s(a, a, 520.0) is None                       # same frame
    assert image_motion_rad_s(a, _obs(0.2, corners=False), 520.0) is None


def test_gate_waits_for_camera_stillness_then_approves():
    cfg = fast_cfg()
    tk = cfg.tasks
    swing = lambda t: 8.0 * math.exp(-t / 1.0) * math.sin(2 * math.pi * t / 0.9)      # px, decaying pendulum
    ctx = FakeCtx(cfg, lambda t: _obs(t, shift_px=swing(t)))
    res = wait_until_still(ctx)
    assert res.ok and res.method == "camera" and res.frames >= tk.grip_still_frames
    assert res.waited_s > 1.0                                 # it really waited for the swing to die down
    assert res.waited_s < tk.grip_settle_timeout_s


def test_gate_does_not_approve_a_claw_that_keeps_moving():
    cfg = fast_cfg()
    ctx = FakeCtx(cfg, lambda t: _obs(t, shift_px=6.0 * math.sin(2 * math.pi * t / 0.9)))
    res = wait_until_still(ctx)
    assert not res.ok and res.method == "camera" and "still moving" in res.reason
    assert res.waited_s >= cfg.tasks.grip_settle_timeout_s


def test_gate_requires_n_consecutive_still_frames():
    cfg = fast_cfg()
    n = cfg.tasks.grip_still_frames
    # still except for a jolt every (n - 1) frames: never n consecutive quiet pairs
    ctx = FakeCtx(cfg, lambda t: _obs(t, shift_px=(5.0 if int(round(t / 0.1)) % (n - 1) == 0 else 0.0)))
    assert not wait_until_still(ctx).ok


def test_gate_dwells_k_pendulum_periods_without_a_camera_motion_signal():
    cfg = fast_cfg()
    for obs in (lambda t: _obs(t, ok=False), lambda t: _obs(t, corners=False)):
        ctx = FakeCtx(cfg, obs)
        res = wait_until_still(ctx)
        assert res.ok and res.method == "dwell" and res.max_rate_rad_s is None
        assert res.waited_s == pytest.approx(settle_dwell_s(cfg.claw, cfg.tasks), abs=1e-6)
        assert sum(ctx.waits) == pytest.approx(res.waited_s, abs=1e-6)


# ============================================================ attitude estimate + grip approval
def test_attitude_estimate_prefers_vision_and_reports_an_honest_sigma():
    cfg = fast_cfg()
    R = rot_x(math.radians(2.0))
    est = estimate_attitude(FakeCtx(cfg, lambda t: _obs(t, R=R)), [0, 0, 1])
    assert est.source == "vision" and est.tilt_rad == pytest.approx(math.radians(2.0))
    assert est.sigma_rad >= 0.010 > 0.004                       # not the 4 mrad IMU figure
    est2 = estimate_attitude(FakeCtx(cfg, lambda t: _obs(t, ok=False)), [0, 0, 1])
    assert est2.source == "statics" and est2.sigma_rad == cfg.claw.statics_attitude_sigma_rad


def _runner(cfg, obs, *, R_at=None, tilt_limit=None):
    ctx = FakeCtx(cfg, obs)
    if tilt_limit is not None:
        cfg.claw.grip_tilt_max_rad = tilt_limit
    if R_at is not None:
        ctx.model.geometry.R_at = R_at
    ctx.validated_volume = None
    ctx.ledger = SimpleNamespace(level="LOCAL_ONLY")
    ctx.ws, ctx.lim = None, None
    runner = TaskRunner(ctx, None)
    runner._here = lambda: np.array([1.0, 1.0, 0.5])
    return runner, ctx


def test_grip_is_approved_only_after_settling_and_within_the_tilt_limit():
    cfg = fast_cfg()
    runner, ctx = _runner(cfg, lambda t: _obs(t, R=rot_x(math.radians(1.0))))
    ok, why = runner._settle_and_approve("grip x", np.array([1.0, 1.0, 0.06]))
    assert ok, why
    rec = runner.approvals[-1]
    assert rec["approved"] and rec["method"] == "camera" and rec["source"] == "vision" and rec["tilt_deg"] == 1.0


def test_grip_refused_when_the_measured_tilt_exceeds_the_limit():
    cfg = fast_cfg()
    runner, _ = _runner(cfg, lambda t: _obs(t, R=rot_y(math.radians(7.0))))
    ok, why = runner._settle_and_approve("grip x")
    assert not ok and "vision tilt 7.0 deg" in why and not runner.approvals[-1].get("approved")


def test_grip_refused_when_the_cable_model_predicts_too_much_tilt_at_the_grip_pose():
    cfg = fast_cfg()
    bad = rot_x(math.radians(6.0))
    # floor reference not in view: the dwell path; statics fine at the hover but 6 deg at the grip pose
    R_at = lambda p: bad if p[2] < 0.1 else np.eye(3)
    runner, _ = _runner(cfg, lambda t: _obs(t, ok=False), R_at=R_at)
    assert runner._settle_and_approve("hover only")[0]
    ok, why = runner._settle_and_approve("grip x", np.array([1.0, 1.0, 0.06]))
    assert not ok and "predicted tilt 6.0 deg" in why
    assert runner.approvals[-1]["method"] == "dwell"


def test_grip_refused_when_the_claw_will_not_settle():
    cfg = fast_cfg()
    runner, _ = _runner(cfg, lambda t: _obs(t, shift_px=6.0 * math.sin(2 * math.pi * t / 0.9)))
    ok, why = runner._settle_and_approve("grip x")
    assert not ok and "would not settle" in why


def test_predicted_tilt_of_a_point_claw_is_zero_and_of_the_cad_claw_is_a_few_degrees():
    cfg = fast_cfg()
    anchors = cfg.anchor_priors()
    geo = geometry_from_config(cfg, anchors)
    assert predicted_tilt_rad(geo, [1.68, 1.37, 1.0]) < math.radians(3)
    assert predicted_tilt_rad(geo, [0.6, 0.5, 1.0]) > 0.0


# ============================================================ configuration fields
def test_new_config_fields_have_validated_defaults():
    cfg = load_config(SIM)
    assert cfg.claw.imu is False and cfg.calibration.attitude_sigma_rad >= 0.010
    assert cfg.claw.vision_attitude_sigma_rad == 0.010 and cfg.claw.statics_attitude_sigma_rad > 0.03
    assert math.degrees(cfg.claw.mount_offset_max_rad) == pytest.approx(5.0)
    tk = cfg.tasks
    assert (tk.grip_still_rate_rad_s, tk.grip_still_frames, tk.grip_settle_periods) == (0.02, 5, 5.0)
    assert tk.grip_settle_min_s <= tk.grip_settle_timeout_s and tk.grip_period_margin == 1.25
    # per-frame covariance of the detectors: corner noise, margin, least attitude sigma
    assert cfg.camera.corner_sigma_px == 0.3 and cfg.camera.pose_cov_inflate == 1.3
    assert cfg.claw.vision_attitude_floor_rad == 0.001 and cfg.marker.board_layout_file is None


@pytest.mark.parametrize("change,msg", [
    ({"tasks.grip_still_frames": 1}, "grip_still_frames"),
    ({"tasks.grip_still_frames": 2.5}, "grip_still_frames"),
    ({"tasks.grip_still_rate_rad_s": 0.0}, "grip_still_rate_rad_s"),
    ({"tasks.grip_settle_periods": -1.0}, "grip_settle_periods"),
    ({"tasks.grip_settle_timeout_s": 1.0, "tasks.grip_settle_min_s": 2.0}, "grip_settle_min_s"),
    ({"tasks.grip_settle_min_s": -0.5}, "grip_settle_min_s"),
    ({"claw.vision_attitude_sigma_rad": 0.0}, "vision_attitude_sigma_rad"),
    ({"claw.mount_offset_max_rad": float("nan")}, "mount_offset_max_rad"),
    ({"claw.grip_tilt_max_rad": 0.9}, "sane limit"),
    ({"calibration.attitude_sigma_rad": 0.004}, "no IMU"),
    ({"claw.vision_attitude_floor_rad": 0.0}, "vision_attitude_floor_rad"),
    ({"camera.corner_sigma_px": -0.3}, "corner_sigma_px"),
    ({"tasks.grip_period_margin": 0.0}, "grip_period_margin"),
])
def test_config_validation_rejects_bad_attitude_and_grip_fields(change, msg):
    import json
    raw = json.load(open(SIM))
    for path, v in change.items():
        sec, key = path.split(".")
        raw[sec][key] = v
    with pytest.raises(ConfigError, match=msg):
        load_config(raw)


def test_a_lower_calibration_attitude_sigma_is_allowed_only_with_the_optional_gravity_sensor():
    import json
    raw = json.load(open(SIM))
    raw["calibration"]["attitude_sigma_rad"] = 0.004
    raw["claw"]["imu"] = True
    assert load_config(raw).calibration.attitude_sigma_rad == 0.004


def test_no_imu_in_the_shipped_configs():
    for path in ("config/robot.sim.json", "config/robot.example.json"):
        assert load_config(path).claw.imu is False


# ============================================================ simulated startup: the offset is measured and used
def test_startup_measures_the_camera_mount_offset_while_the_claw_rests_on_the_floor():
    from roomcleaner.cdpr.sim.harness import SimRobot
    from roomcleaner.cdpr.startup import StartupSequencer
    r = SimRobot(fast_cfg(), seed=3, world_kw={"swap_stations": (0, 1)}, mount_err_rad=0.02)
    Q_true = np.linalg.inv(r.simcam.T_B_C_nominal[:3, :3]) @ r.simcam.T_B_C[:3, :3]
    assert np.linalg.norm(matrix_to_rotvec(Q_true)) > 0.005               # the sim camera really is mounted off-nominal
    rep = StartupSequencer(r.ctx).run()
    assert "slide directions disagree" in rep.reasons[-1]                  # stops at the (injected) wiring error, later
    m = rep.measurements
    assert 0.0 < m["camera_mount_offset_rad"] < r.cfg.claw.mount_offset_max_rad
    err = np.linalg.norm(matrix_to_rotvec(r.vision.mount_Q @ Q_true.T))
    assert err < 4 * max(m["camera_mount_offset_sigma_rad"], 1e-3) and err < 0.01
    assert r.ctx.mount_angle_rad == m["camera_mount_offset_rad"]
    assert np.allclose(r.ctx.T_B_C, r.vision.T_B_C)                        # everything downstream uses the corrected mount


def test_startup_aborts_when_the_claw_is_not_resting_upright():
    from roomcleaner.cdpr.sim.harness import SimRobot
    from roomcleaner.cdpr.startup import StartupSequencer
    r = SimRobot(fast_cfg(), seed=3, mount_err_rad=0.0)
    # the camera is really mounted 9 deg off (or the claw lies tilted): beyond claw.mount_offset_max_rad (5 deg)
    r.simcam.T_B_C[:3, :3] = r.simcam.T_B_C_nominal[:3, :3] @ rot_x(math.radians(9))
    rep = StartupSequencer(r.ctx).run()
    assert rep.outcome == "FAULT" and "not resting upright" in rep.reasons[-1]
    assert r.world.on_floor and r.ctx.ledger.claw_supported is False      # nothing touched, support never confirmed
    assert r.ctx.mount_angle_rad is None                                  # an implausible offset is not stored
