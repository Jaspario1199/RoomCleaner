"""Independent review of D27 (IMU removal), see verification/imu_removal_review.md.

These tests record the reviewer's own derivations and are written to PASS when the finding they document is true; a
test that starts failing means the code or the finding changed. Nothing here edits code or configuration.
Fast (no simulated startup): numpy / OpenCV Monte Carlo, arithmetic, and the settle gate with fake observations.
"""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr.attitude import (image_motion_rad_s, mount_offset_from_up, pendulum_length_m,
                                       pendulum_period_s, settle_dwell_s, wait_until_still)
from roomcleaner.cdpr.config import load_config
from roomcleaner.cdpr.frames import make_T, rpy_to_matrix, rotvec_to_matrix
from roomcleaner.cdpr.perception import VisionSource
from roomcleaner.cdpr.vision.marker import MarkerObservation, claw_position_cov

from .simkit import SIM, fast_cfg
from .test_attitude import FakeCtx, _obs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import review_attitude_noise as N                                    # noqa: E402  (CRB / Monte Carlo helpers)

EDGE_SINGLE, EDGE_BOARD = 0.1524, 0.150


def _crb(tags, edge, cam, px=0.3, tilt=(0.03, -0.02)):
    r = N.row("t", tags, edge, cam, px, tilt_xy=tilt, do_mc=False)
    return r


# ====================================================================== 1. pose covariance / lever term
def test_lever_term_is_physical_for_the_claw_reference_point():
    """Camera position in the marker frame = -R^T t: a tilt error of the tag's pose moves it by tilt x range (rotation
    about the marker origin).  CRB of a 152 mm tag at 0.52 m, 0.3 px: position error = tilt error x range, fully
    correlated; so rot_sigma * |p| is the right lever for the claw origin (p = claw origin in the marker frame)."""
    r = _crb([(0, 0)], EDGE_SINGLE, (0.0, 0.0, 0.52))
    assert r["n_tags"] == 1
    assert r["crb_pos_xy_mm"] == pytest.approx(r["lever_pred_mm"], rel=0.10)
    # and it is NOT small: a 13 mrad tilt noise gives ~7 mm of position noise per frame
    assert 11 < r["crb_tilt_mrad"] < 16 and 5.5 < r["crb_pos_xy_mm"] < 8.5
    # the z component of the lever error is tiny for a camera looking straight down (isotropic repo covariance overstates it)
    assert r["crb_pos_z_mm"] < 1.0


def _vision_only_cov(rot_sigma, cam_xyz=(0.1, 0.05, 0.6)):
    R_C_M, t = N.camera_pose(cam_xyz)
    T_C_M = make_T(R_C_M, t)
    T_B_C = make_T(rpy_to_matrix(np.pi, 0, 0), [0.0, 0.09, -0.0056])
    uv = N.project(N.tag_corners(0, 0, EDGE_SINGLE), R_C_M, t)
    now = 1.0e6
    src = SimpleNamespace(observe=lambda n: MarkerObservation(True, "", T_C_M, 0.3, 50.0, 100.0, uv, frame_id=1,
                                                              capture_us=now))
    v = VisionSource(src, T_B_C, 520.0, EDGE_SINGLE, max_age_s=0.5, now_us=lambda: now, rot_sigma=rot_sigma)
    o = v.observe()
    s = MarkerObservation(True, "", T_C_M).sigma_cam(520.0, EDGE_SINGLE, 0.3)
    pix = o.cov - np.eye(3) * (rot_sigma * np.linalg.norm(T_B_C[:3, 3])) ** 2 - np.eye(3) * (rot_sigma * np.linalg.norm(o.p)) ** 2
    return o, T_B_C, pix, s


def test_the_two_lever_terms_are_one_rotation_error_and_the_second_is_negligible():
    """The vision-only covariance adds sigma^2 (|camera->body|^2 + |marker->body|^2) I.  The pose error is one rotation of
    the whole estimate about the marker origin, whose lever on the body origin is |p| only: the 0.09 m camera->body
    term is a (conservative) double count worth ~1-2 % of the variance, i.e. harmless."""
    o, T_B_C, pix, s = _vision_only_cov(0.010)
    lev_cam, lev_p = float(np.linalg.norm(T_B_C[:3, 3])), float(np.linalg.norm(o.p))
    assert 0.55 < lev_p < 0.70                                         # the ~6 mm per frame of the report
    frac = lev_cam ** 2 / (lev_cam ** 2 + lev_p ** 2)
    assert 0.005 < frac < 0.03
    # |p| is within 15 % of the camera->marker range (the correct lever for the camera), the difference is the mount offset
    R_C_M, t = N.camera_pose((0.1, 0.05, 0.6))
    assert abs(lev_p / np.linalg.norm(t) - 1) < 0.15
    # the covariance is isotropic although the lever error is horizontal for a downward camera: z is overstated
    assert o.cov[2, 2] >= (0.010 * lev_p) ** 2 and abs(o.cov[2, 2] / o.cov[0, 0] - 1) < 0.5


def test_claw_position_cov_uses_only_the_camera_to_body_lever_and_perception_adds_the_marker_lever():
    o, T_B_C, _, _ = _vision_only_cov(0.010)
    c0 = claw_position_cov(MarkerObservation(True, "", make_T(np.eye(3), [0, 0, 0.6])), T_B_C, 520.0, EDGE_SINGLE,
                           rot_sigma_rad=0.0)
    c1 = claw_position_cov(MarkerObservation(True, "", make_T(np.eye(3), [0, 0, 0.6])), T_B_C, 520.0, EDGE_SINGLE,
                           rot_sigma_rad=0.010)
    assert (c1 - c0)[0, 0] == pytest.approx((0.010 * np.linalg.norm(T_B_C[:3, 3])) ** 2, rel=1e-6)


def test_averaging_n_frames_reduces_tilt_and_position_noise_as_one_over_sqrt_n_for_independent_noise():
    """Monte Carlo (IPPE + LM refinement, 0.3 px corner noise, 152 mm tag at 0.6 m).  Holds for independent frame noise
    only; static sub-pixel / JPEG-block / lens bias is NOT reduced (unresolved uncertainty)."""
    R, t = N.camera_pose((0.0, 0.0, 0.6), (0.03, -0.02))
    P = N.tag_corners(0, 0, EDGE_SINGLE)
    T, Pp, _ = N.mc(P, R, t, 0.3, n=1200, seed=11, refine=True)
    s1 = float(np.sqrt(np.mean(T ** 2)))
    for n in (4, 10):
        m = len(T) // n
        sn = float(np.sqrt(np.mean(T[:m * n].reshape(m, n, 2).mean(1) ** 2)))
        assert sn == pytest.approx(s1 / math.sqrt(n), rel=0.2)
    assert 0.012 < s1 < 0.025                                          # ~18 mrad single frame at 0.6 m on axis, not 10


def test_the_repo_single_tag_detector_without_refinement_is_much_noisier_than_the_estimator_is_told():
    """vision/marker.py uses IPPE_SQUARE only (board.py refines with LM).  Nearly fronto-parallel (the claw hangs level
    and the camera looks straight down at the tag) the two IPPE solutions are close and the analytic one is far from
    the ML estimate: tilt rms several times the CRB.  (Frames with ambiguity ratio < 3 are then rejected by
    select_pose or resolved by an upright prior of +-0.6 rad that cannot separate them.)"""
    R, t = N.camera_pose((0.0, 0.0, 0.52), (0.03, -0.02))
    P = N.tag_corners(0, 0, EDGE_SINGLE)
    Ti, _, _ = N.mc(P, R, t, 0.3, n=400, seed=3, refine=False)
    Tl, _, _ = N.mc(P, R, t, 0.3, n=400, seed=3, refine=True)
    assert np.sqrt(np.mean(Ti ** 2)) > 3 * np.sqrt(np.mean(Tl ** 2))


# ====================================================================== 3. attitude noise: single tag vs board
def test_single_tag_attitude_noise_grows_with_range_squared_and_10_mrad_is_right_only_near_0p46_m_on_axis():
    on = {h: _crb([(0, 0)], EDGE_SINGLE, (0.0, 0.0, h))["crb_tilt_mrad"] for h in (0.46, 0.6, 0.8, 1.0)}
    assert 8 < on[0.46] < 13 and 14 < on[0.6] < 22 and 28 < on[0.8] < 38 and on[1.0] > 45
    off = _crb([(0, 0)], EDGE_SINGLE, (0.2, 0.1, 0.6))["crb_tilt_mrad"]      # oblique view helps ~2.4x
    assert 5 < off < 10


def test_board_attitude_noise_depends_on_how_many_tags_are_in_view_not_on_the_board_span():
    tags42 = N.board_tags(0.42, EDGE_BOARD)
    tags30 = N.board_tags(0.30, EDGE_BOARD)
    # suspended poses (>= 0.8 m): 3-9 tags, 0.6-3 mrad (below the 4 mrad IMU figure)
    for h, lim in ((0.8, 3.5), (1.0, 1.5), (1.3, 1.5)):
        r = _crb(tags42, EDGE_BOARD, (0.0, 0.0, h))
        assert r["n_tags"] >= 3 and r["crb_tilt_mrad"] < lim, r
    # floor stage: camera ~0.51 m above the floor.  Over a tag centre at pitch 0.42 only ONE tag is in view -> no gain
    r = _crb(tags42, EDGE_BOARD, (0.0, 0.0, 0.51))
    assert r["n_tags"] == 1 and r["crb_tilt_mrad"] > 11
    # two tags (camera >= 0.11 m off the tag centre toward a neighbour) or pitch 0.30: 2-3 mrad; a cell centre: ~1 mrad
    assert _crb(tags42, EDGE_BOARD, (0.21, 0.0, 0.51))["crb_tilt_mrad"] < 3.5
    assert _crb(tags30, EDGE_BOARD, (0.0, 0.0, 0.51))["crb_tilt_mrad"] < 3.5
    assert _crb(tags30, EDGE_BOARD, (0.15, 0.15, 0.51))["n_tags"] == 4


# ====================================================================== 4. settle-then-approve
def test_dwell_arithmetic_and_its_assumptions():
    cfg = load_config(SIM)
    L = pendulum_length_m(cfg.claw)
    assert L == pytest.approx(0.196, abs=1e-3)
    T = pendulum_period_s(L)
    assert T == pytest.approx(0.8887, abs=1e-3)
    assert settle_dwell_s(cfg.claw, cfg.tasks) == pytest.approx(5 * T, abs=1e-6) and 4.4 < 5 * T < 4.5
    # reviewer's estimates (ASSUMED gyration radius k = 0.13 m about the CoM; payload 0.9 kg at 0.5 m below the plane):
    g, k = 9.81, 0.13
    T_compound = 2 * math.pi * math.sqrt((L ** 2 + k ** 2) / (g * L))
    assert 1.0 < T_compound < 1.15                                   # the simple-pendulum period is ~20 % short
    m, mp, lp = 0.6, 0.9, 0.5
    I = m * (L ** 2 + k ** 2) + mp * lp ** 2
    T_loaded = 2 * math.pi * math.sqrt(I / ((m * L + mp * lp) * g))
    assert 1.2 < T_loaded < 1.5 and 5 * T / T_loaded < 3.8          # a release with the jeans gets < 4 loaded periods
    # D28: the box and everything above the tube moved 50 mm down relative to the head; with ~60 % of the mass above
    # the cut the CoM depth below the attachment plane shrinks by ~0.4 x 50 mm -> shorter period, the stale L is conservative
    L28 = L - 0.4 * 0.050
    assert pendulum_period_s(L28) < T


def test_dwell_is_counted_from_the_start_of_waiting_so_a_claw_seen_moving_then_lost_is_approved_early():
    """Finding: the dwell used when the floor reference leaves the image is max(dwell - waited, 0) where ``waited``
    includes time during which the camera SAW the claw moving; the claw is approved ~1.4 s after the last observed motion."""
    cfg = fast_cfg()
    swing = lambda t: 6.0 * math.sin(2 * math.pi * t / 0.9)
    seen_until = 3.0
    ctx = FakeCtx(cfg, lambda t: _obs(t, shift_px=swing(t)) if t < seen_until else _obs(t, ok=False))
    res = wait_until_still(ctx)
    dwell = settle_dwell_s(cfg.claw, cfg.tasks)
    assert res.ok and res.method == "dwell"
    since_last_motion = res.waited_s - seen_until
    assert res.waited_s == pytest.approx(dwell, abs=0.3)
    assert since_last_motion < dwell / 2.5                         # < 2 s of quiet after the last observed swing


def test_still_threshold_vs_image_corner_noise():
    """grip_still_rate 0.02 rad/s, 5 consecutive frames at 0.1 s: a still claw passes 99.9 % of frames at 0.3 px corner noise,
    ~74 % at 0.5 px (settles within seconds), ~4 % at 1 px (effectively never: fails closed after 15 s)."""
    cfg = fast_cfg()
    tk = cfg.tasks
    rng = np.random.default_rng(0)
    base = np.array([[100, 100], [200, 100], [200, 200], [100, 200]], float)

    def p_pass(px, n=4000):
        ok = 0
        prev = SimpleNamespace(corners=base + rng.normal(0, px, (4, 2)), t_us=0.0)
        for k in range(n):
            cur = SimpleNamespace(corners=base + rng.normal(0, px, (4, 2)), t_us=(k + 1) * 1e5)
            ok += image_motion_rad_s(prev, cur, 520.0) <= tk.grip_still_rate_rad_s
            prev = cur
        return ok / n
    assert p_pass(0.3) > 0.99 and 0.6 < p_pass(0.5) < 0.9 and p_pass(1.0) < 0.1


def test_still_pose_gate_is_blind_to_swing_when_the_covariance_is_large():
    """perception.still_pose allows scatter hypot(spread_max, 3 sqrt(trace cov)) among n frames: the vision-only lever term
    inflates cov ~10x, so a ~20 mm swing that the old gate (rot_sigma 4 mrad IMU-like) rejected is now accepted as 'still'."""
    def accepts(rot_sigma, amp_m):
        now = {"t": 1.0e6}
        T_B_C = make_T(rpy_to_matrix(np.pi, 0, 0), [0.0, 0.09, -0.0056])
        R_C_M, t = N.camera_pose((0.0, 0.0, 0.6))

        def obs(n):
            x = amp_m * math.sin(2 * math.pi * (n / 1e6) / 2.8)          # long-cable swing, 2.8 s period
            tt = t + R_C_M @ np.array([x, 0, 0]) * -1.0
            return MarkerObservation(True, "", make_T(R_C_M, tt), 0.3, 50.0, 100.0,
                                     N.project(N.tag_corners(0, 0, EDGE_SINGLE), R_C_M, tt), frame_id=1, capture_us=n)
        v = VisionSource(SimpleNamespace(observe=obs), T_B_C, 520.0, EDGE_SINGLE, max_age_s=0.5,
                         now_us=lambda: now["t"], rot_sigma=rot_sigma)

        def wait(s):
            now["t"] += s * 1e6
        sp, _ = v.still_pose(10, wait, interval_s=0.1, max_wait_s=0.95, spread_max_m=0.003)       # ONE window, at the fastest part of the swing
        return sp is not None
    assert not accepts(0.004, 0.030)                                   # IMU-era covariance: 30 mm swing rejected
    assert accepts(0.010, 0.030)                                       # vision-only covariance: accepted (finding)


# ====================================================================== mount offset and hardware refusal
def test_mount_offset_absorbs_any_rest_tilt_of_the_claw_and_the_post_correction_check_is_vacuous():
    R_nom = rpy_to_matrix(np.pi, 0, 0)
    rest = rotvec_to_matrix([math.radians(3.0), 0.0, 0.0])             # claw standing 3 deg off vertical, camera mount exact
    up_cam = (R_nom @ np.eye(3)).T @ (rest.T @ np.array([0, 0, 1.0]))  # marker normal in camera coordinates
    off = mount_offset_from_up(R_nom, up_cam)
    assert off.angle_rad == pytest.approx(math.radians(3.0), abs=1e-6)  # the rest tilt is read as a mount error ...
    # ... and a claw that hangs level afterwards then reads a 3 deg tilt (the vision tilt gate loses 3 of its 5 deg)
    u_level = R_nom.T @ np.array([0, 0, 1.0])
    u_corr = (R_nom @ off.Q).T @ np.array([0, 0, 1.0])
    assert math.acos(np.clip(u_level @ u_corr, -1, 1)) == pytest.approx(math.radians(3.0), abs=1e-6)
    # by construction the corrected resting pose is exactly upright: startup's 'tilt after correction' check cannot fire
    assert np.allclose((R_nom @ off.Q).T @ np.array([0, 0, 1.0]), up_cam, atol=1e-12)


def test_service_refuses_claw_imu_true_on_hardware(tmp_path, monkeypatch):
    from roomcleaner.cdpr import claw_link, service
    raw = json.load(open(ROOT / SIM))
    for i, s in enumerate(raw["stations"]):
        s["address"] = f"127.0.0.1:{9100 + i}"
    raw["claw"]["address"] = "127.0.0.1:9199"
    raw["claw"]["imu"] = True
    path = tmp_path / "robot.json"
    path.write_text(json.dumps(raw))
    monkeypatch.setattr(claw_link, "ThreadedFrameSource", lambda src: SimpleNamespace(observe=lambda now: None))
    with pytest.raises(SystemExit) as e:
        service.build_hardware_context(str(path), tmp_path)
    msg = str(e.value)
    del e
    import gc
    gc.collect()                                                       # release the bound UDP socket
    assert "IMU" in msg and "D27" in msg
    # (the refusal comes AFTER the UDP transport has been bound and the claw client created: a second build in this
    # process would hit 'Address already in use'; harmless because the process exits on SystemExit)
