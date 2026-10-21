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


def test_legacy_frame_covariance_is_isotropic_and_has_the_marker_lever_only():
    """(Round 2: the premise of the round-1 test, two lever terms, is gone; what is left is the LEGACY path, a frame without
    pose_cov, e.g. a fixed-noise source.)  Round 1 text: the vision-only covariance added sigma^2 (|camera->body|^2 + |marker->body|^2) I.  The pose error is one rotation of
    the whole estimate about the marker origin, whose lever on the body origin is |p| only: the 0.09 m camera->body
    term is a (conservative) double count worth ~1-2 % of the variance, i.e. harmless."""
    o, T_B_C, pix, s = _vision_only_cov(0.010)
    lev_cam, lev_p = float(np.linalg.norm(T_B_C[:3, 3])), float(np.linalg.norm(o.p))
    assert 0.55 < lev_p < 0.70                                         # the ~6 mm per frame of the report
    # |p| is within 15 % of the camera->marker range (the correct lever for the camera), the difference is the mount offset
    R_C_M, t = N.camera_pose((0.1, 0.05, 0.6))
    assert abs(lev_p / np.linalg.norm(t) - 1) < 0.15
    # the covariance is isotropic although the lever error is horizontal for a downward camera: z is overstated
    assert o.cov[2, 2] >= (0.010 * lev_p) ** 2 and abs(o.cov[2, 2] / o.cov[0, 0] - 1) < 0.5


def test_round2_claw_position_cov_no_longer_double_counts_and_the_legacy_frame_gets_one_lever():
    """Round 2 (F9 fixed): claw_position_cov ignores rot_sigma_rad (no camera->body term); a legacy frame (no pose_cov) gets exactly
    (sigma |p|)^2 from VisionSource.  Measured here: the covariance difference between rot_sigma 0 and 0.010 is sigma^2 |p|^2 I."""
    o10, T_B_C, _, _ = _vision_only_cov(0.010)
    o0, _, _, _ = _vision_only_cov(0.0)
    c0 = claw_position_cov(MarkerObservation(True, "", make_T(np.eye(3), [0, 0, 0.6])), T_B_C, 520.0, EDGE_SINGLE, rot_sigma_rad=0.0)
    c1 = claw_position_cov(MarkerObservation(True, "", make_T(np.eye(3), [0, 0, 0.6])), T_B_C, 520.0, EDGE_SINGLE, rot_sigma_rad=0.010)
    assert np.allclose(c0, c1)
    lever = float(np.linalg.norm(o10.p))
    assert np.allclose(o10.cov - o0.cov, np.eye(3) * (0.010 * lever) ** 2, rtol=1e-6, atol=1e-12)


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
def test_dwell_arithmetic_round2():
    """Round 2 (F8c fixed): dwell = 5 x 1.25 x T with T = 0.8887 s -> 5.55 s; loaded release: L = (0.6 x 0.196 + 0.9 x 0.5173)/1.5 =
    0.389 m, T = 1.251 s, dwell 7.82 s.  My own compound-pendulum estimate (ASSUMED radius of gyration k = 0.13 m about the CoM):
    unloaded T = 1.065 s -> 5.55 s is 5.2 periods (was 4.2); loaded T = 1.35 s -> 7.82 s is 5.8 periods (was 3.3)."""
    from roomcleaner.cdpr.attitude import loaded_pendulum_length_m
    cfg = load_config(SIM)
    L = pendulum_length_m(cfg.claw)
    T = pendulum_period_s(L)
    assert L == pytest.approx(0.196, abs=1e-3) and T == pytest.approx(0.8887, abs=1e-3)
    d0 = settle_dwell_s(cfg.claw, cfg.tasks)
    assert d0 == pytest.approx(5 * 1.25 * T, abs=1e-6) and 5.5 < d0 < 5.6
    Lp = loaded_pendulum_length_m(cfg.claw, 0.9)
    assert Lp == pytest.approx((0.6 * L + 0.9 * 0.5173) / 1.5, abs=2e-3) and 0.38 < Lp < 0.40
    d1 = settle_dwell_s(cfg.claw, cfg.tasks, 0.9)
    assert d1 == pytest.approx(5 * 1.25 * pendulum_period_s(Lp), abs=1e-6) and 7.7 < d1 < 7.9
    g, k, m, mp, lp = 9.81, 0.13, 0.6, 0.9, 0.5173
    T_comp = 2 * math.pi * math.sqrt((L ** 2 + k ** 2) / (g * L))
    T_load = 2 * math.pi * math.sqrt((m * (L ** 2 + k ** 2) + mp * lp ** 2) / ((m * L + mp * lp) * g))
    assert d0 / T_comp > 5.0 and d1 / T_load > 5.5                     # at least the 5 periods the config promises, by my numbers
    # a payload on a claw without mass / lowest point falls back to the unloaded length (no crash)
    assert loaded_pendulum_length_m(SimpleNamespace(com_body_m=cfg.claw.com_body_m, attachment_points_body_m=cfg.claw.attachment_points_body_m), 0.9) == pytest.approx(L)


def test_dwell_is_counted_from_the_last_observed_motion_round2():
    """Round 2 (F8a fixed): a claw seen moving until t = 3 s and then lost is approved only a full dwell after the last motion.
    Also: a loaded release applies the full loaded dwell even when the camera reports stillness from the start."""
    cfg = fast_cfg()
    swing = lambda t: 6.0 * math.sin(2 * math.pi * t / 0.9)
    seen_until = 3.0
    ctx = FakeCtx(cfg, lambda t: _obs(t, shift_px=swing(t)) if t < seen_until else _obs(t, ok=False))
    res = wait_until_still(ctx)
    dwell = settle_dwell_s(cfg.claw, cfg.tasks)
    assert res.ok and res.method == "dwell"
    assert res.waited_s - seen_until >= dwell - 0.5                    # quiet time since the last observed motion ~ the dwell
    ctx2 = FakeCtx(cfg, lambda t: _obs(t))                             # camera: perfectly still
    res2 = wait_until_still(ctx2, payload_kg=0.9)
    assert res2.ok and res2.waited_s >= settle_dwell_s(cfg.claw, cfg.tasks, 0.9) - 0.2
    assert wait_until_still(FakeCtx(cfg, lambda t: _obs(t))).waited_s < 1.0       # unloaded and still: quick


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


def test_still_pose_gate_rejects_a_swing_at_any_covariance_round2():
    """Round 2 (F6 fixed): the gate judges the raw camera-frame scatter.  Same one-window experiment as round 1 (fastest part of a
    2.8 s swing): 30 mm AND 25 mm amplitude are rejected (the tolerance for one tag at 0.6 m is hypot(3 mm, 3 x ~2.7 mm camera-frame depth noise) = ~8.7 mm RMS scatter, i.e. a swing of ~15 mm amplitude is still accepted: depth noise inflates the LATERAL tolerance because the gate uses the trace; round 1 measured 32 mm) at rot_sigma 0.004 and 0.010; a still claw is accepted; a 1 mm swing
    (inside the 3 mm motion budget) is accepted."""
    def accepts(rot_sigma, amp_m):
        now = {"t": 1.0e6}
        T_B_C = make_T(rpy_to_matrix(np.pi, 0, 0), [0.0, 0.09, -0.0056])
        R_C_M, t = N.camera_pose((0.0, 0.0, 0.6))

        def obs(n):
            x = amp_m * math.sin(2 * math.pi * (n / 1e6) / 2.8)
            tt = t + R_C_M @ np.array([x, 0, 0]) * -1.0
            return MarkerObservation(True, "", make_T(R_C_M, tt), 0.3, 50.0, 100.0,
                                     N.project(N.tag_corners(0, 0, EDGE_SINGLE), R_C_M, tt), frame_id=1, capture_us=n)
        v = VisionSource(SimpleNamespace(observe=obs), T_B_C, 520.0, EDGE_SINGLE, max_age_s=0.5,
                         now_us=lambda: now["t"], rot_sigma=rot_sigma)

        def wait(s):
            now["t"] += s * 1e6
        sp, _ = v.still_pose(10, wait, interval_s=0.1, max_wait_s=0.95, spread_max_m=0.003)       # ONE window
        return sp is not None
    for rs in (0.004, 0.010):
        assert not accepts(rs, 0.030) and not accepts(rs, 0.025)
        assert accepts(rs, 0.0) and accepts(rs, 0.001)


# ====================================================================== mount offset and hardware refusal
def test_mount_offset_still_absorbs_a_CONSTANT_rest_tilt_round2():
    """Round 2: the startup now has a held-out check (re-measure 30 frames against the corrected mount), which catches a rest tilt that
    CHANGES between the sets, not a constant one (the residual below is ~0 by construction for a constant tilt): F7 first half only."""
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


# ====================================================================== 2. the slack probe is a DIFFERENTIAL measurement
def test_probe_onset_noise_is_dominated_by_per_pose_tilt_lever_that_a_fixed_reference_rotation_removes():
    """The probe compares the claw position of two still poses of a (nearly) unmoved claw.  With each pose's own noisy
    rotation the tilt lever does not cancel (repo: ~3 mm per axis at n = 10, 0.52 m, single tag, 0.3 px); using ONE
    reference rotation and the camera-frame displacement of the marker origin it does: ~0.1 mm (xy), 0.3 mm (z)."""
    d = N.differential_probe_noise(n=10, trials=40, seed=5)
    assert d["repo_xy_mm"] > 2.0
    assert d["fixedR_xy_mm"] < d["repo_xy_mm"] / 10
    assert d["repo_z_mm"] < 1.0 < d["repo_xy_mm"] / 2          # and the repo's isotropic covariance puts the same sigma on z


# ====================================================================== round 2: new covariance and camera-frame displacement
def _detect(tags, edge, T_M_B, T_B_C, rng, px=0.3):
    """A detector-like observation with noisy corners (cv2 IPPE + LM, lowest reprojection error) carrying the repo's pose_cov."""
    import cv2
    from roomcleaner.cdpr.frames import inv_T
    from roomcleaner.cdpr.vision.marker import pose_covariance
    T = inv_T(T_M_B @ T_B_C)
    R, t = T[:3, :3], T[:3, 3]
    vis = N.visible(tags, edge, R, t)
    P = np.vstack([N.tag_corners(x, y, edge) for x, y in vis])
    uv = N.project(P, R, t) + rng.normal(0, px, (4 * len(vis), 2))
    flag = cv2.SOLVEPNP_IPPE if len(P) > 4 else cv2.SOLVEPNP_IPPE_SQUARE
    _, rvs, tvs, _ = cv2.solvePnPGeneric(P, uv, N.K, None, flags=flag)
    best = None
    for rv, tv in zip(rvs, tvs):
        rv, tv = cv2.solvePnPRefineLM(P, uv, N.K, None, rv.copy(), tv.copy())
        e = float(np.sum((cv2.projectPoints(P, rv, tv, N.K, None)[0].reshape(-1, 2) - uv) ** 2))
        if best is None or e < best[0]:
            best = (e, rv, tv)
    Tn = make_T(cv2.Rodrigues(best[1])[0], best[2].ravel())
    return MarkerObservation(True, "", Tn, 0.3, 50.0, 100.0, uv[:4], frame_id=1, capture_us=1e6,
                             pose_cov=pose_covariance(P, Tn, N.K, 0.3, 1.3), anchor_M=P.mean(0), n_tags=len(vis))


def test_repo_pose_covariance_matches_my_independent_monte_carlo():
    """Their Cramer-Rao pose covariance (inflate 1) against my own cv2 Monte Carlo (IPPE+LM, 0.3 px): roll/pitch of the claw for one
    tag at 0.52 m and for the 3x3 / 0.25 m board at 1.0 m; and the repo default (inflate 1.3) is 1.3x that."""
    from roomcleaner.cdpr.vision.marker import claw_cov_from_pose, pose_covariance, roll_pitch_sigma
    T_B_C = make_T(rpy_to_matrix(np.pi, 0, 0), [0.0, 0.09, -0.0056])
    for tags, edge, cam, lo, hi in (([(0, 0)], EDGE_SINGLE, (0.0, 0.0, 0.52), 11.5, 15.5),
                                    (N.board_tags(0.25, 0.15), 0.15, (0.0, 0.0, 1.0), 1.0, 2.0)):
        R, t = N.camera_pose(cam, (0.03, -0.02))
        vis = N.visible(tags, edge, R, t)
        P = np.vstack([N.tag_corners(x, y, edge) for x, y in vis])
        T_mc, _, _ = N.mc(P, R, t, 0.3, n=800, seed=4, refine=True)
        mc = 1e3 * float(np.sqrt(np.mean(T_mc ** 2)))
        T_C_M = make_T(R, t)
        # claw attitude: use a camera-over-origin claw whose camera is the claw camera (mount offset only changes the lever)
        s1 = 1e3 * roll_pitch_sigma(claw_cov_from_pose(pose_covariance(P, T_C_M, N.K, 0.3, 1.0), T_C_M, T_B_C)[1])
        s13 = 1e3 * roll_pitch_sigma(claw_cov_from_pose(pose_covariance(P, T_C_M, N.K, 0.3, 1.3), T_C_M, T_B_C)[1])
        assert lo < mc < hi, (mc, len(vis))
        assert s1 == pytest.approx(mc, rel=0.2), (s1, mc, len(vis))
        assert s13 == pytest.approx(1.3 * s1, rel=1e-6)


def test_cam_displacement_round2_noise_and_its_blind_spot():
    """(a) cam_displacement of a claw that moves 3.6 mm (rigid, tilt about the body origin), 150 trials of single frames at 0.51 m
    height, 0.3 px: error rms in mm.  tilt change 0: single tag ~1.3 (absolute pose 8.8), board ~0.3 (0.8).  A REAL tilt change of
    15 mrad: board sees it (0.8 mm), one tag does not (7.8 mm = tilt x 0.5 m lever, as documented).  (b) floor_displacement uses the
    reference tilt only: blind to a real tilt change even with the board (7.8 mm): sound only for a claw that cannot tilt."""
    from roomcleaner.cdpr.perception import cam_displacement, floor_displacement
    from roomcleaner.cdpr.frames import rotvec_to_matrix
    T_B_C = make_T(rpy_to_matrix(np.pi, 0, 0), [0.0, 0.09, -0.0056])
    rng = np.random.default_rng(0)

    def po(mo):
        return VisionSource(SimpleNamespace(observe=lambda n: mo), T_B_C, 520.0, 0.15, max_age_s=0.5, now_us=lambda: 1e6).observe()

    def rms(tags, edge, eps, n=100):
        p0, d = np.array([0.05, 0.02, 0.51]), np.array([0.003, -0.002, 0.0])
        E = []
        for _ in range(n):
            ref = po(_detect(tags, edge, make_T(np.eye(3), p0), T_B_C, rng))
            o = po(_detect(tags, edge, make_T(rotvec_to_matrix([eps, 0, 0]), p0 + d), T_B_C, rng))
            E.append([np.linalg.norm(cam_displacement(o, ref)[0] - d), np.linalg.norm(floor_displacement(o, ref)[0] - d),
                      np.linalg.norm((o.p - ref.p) - d)])
        return 1e3 * np.sqrt(np.mean(np.square(E), axis=0))
    one, board = [(0, 0)], N.board_tags(0.25, 0.15)
    a0, b0 = rms(one, EDGE_SINGLE, 0.0), rms(board, 0.15, 0.0)
    a1, b1 = rms(one, EDGE_SINGLE, 0.015), rms(board, 0.15, 0.015)
    assert a0[0] < 2.0 < a0[2] and b0[0] < 0.6 and a0[2] > 5 * b0[0]            # displacement beats the absolute pose
    assert a1[0] > 5.0 and a1[1] > 5.0                                          # one tag: a real tilt change is NOT seen
    assert b1[0] < 1.5 and b1[1] > 5.0                                          # board: cam_displacement sees it, floor_displacement does not
