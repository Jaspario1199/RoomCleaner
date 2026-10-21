"""Vision-only attitude with the printed floor board (verification/imu_removal_review.md F1-F9, the minimal change set).

Fast tests (no simulated startup unless stated): per-frame covariance and LM refinement of the detector, anisotropic
lever, board / single-tag fallback, the 0.25 m layout and its printout, camera-frame displacements, the drag watch,
the simulator's tag-derived noise model, and the settle-gate / mount-offset fixes."""
import math
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from roomcleaner.cdpr import frames as F
from roomcleaner.cdpr.attitude import (loaded_pendulum_length_m, pendulum_length_m, pendulum_period_s,
                                       settle_dwell_s, wait_until_still)
from roomcleaner.cdpr.calibration import predicted_vision_cov
from roomcleaner.cdpr.config import ConfigError, load_config
from roomcleaner.cdpr.perception import VisionSource, cam_displacement, floor_displacement
from roomcleaner.cdpr.sim.world import FloorBoard
from roomcleaner.cdpr.startup import DragWatch, StartupAbort, StartupSequencer
from roomcleaner.cdpr.vision.board import DEFAULT_PITCH_M, MAX_PITCH_M, BoardDetector, FloorBoardLayout
from roomcleaner.cdpr.vision.camera import CameraModel
from roomcleaner.cdpr.vision.marker import (MarkerDetector, MarkerObservation, claw_cov_from_pose, claw_position_cov,
                                            pose_covariance, roll_pitch_sigma)

from .simkit import SIM, fast_cfg
from .test_attitude import FakeCtx, _obs

CAM = CameraModel.load("config/camera.sim.json")
EDGE_S, EDGE_B = 0.1524, 0.150
T_B_C = F.make_T(F.rpy_to_matrix(np.pi, 0, 0), [0.0, 0.09, -0.0056])     # camera 9 cm from the body origin, looking down


def cam_pose(cam_xyz, tilt=(0.03, -0.02)):
    """T_C_M of a camera at ``cam_xyz`` (marker frame) looking down, tilted slightly."""
    R_M_C = F.rot_x(tilt[0]) @ F.rot_y(tilt[1]) @ F.rot_x(np.pi)
    return F.inv_T(F.make_T(R_M_C, cam_xyz))


def tag_corners(cx, cy, edge, yaw=0.0):
    h = edge / 2
    loc = np.array([[-h, h], [h, h], [h, -h], [-h, -h]])
    c, s = math.cos(yaw), math.sin(yaw)
    xy = loc @ np.array([[c, -s], [s, c]]).T + [cx, cy]
    return np.c_[xy, np.zeros(4)]


def grid(pitch, edge=EDGE_B, n=3):
    c = (np.arange(n) - (n - 1) / 2) * pitch
    return np.vstack([tag_corners(x, y, edge) for y in c for x in c])


def in_view(P, T, margin=4, min_side=40.0):
    """Corner sets (4, 3) of the tags fully in view."""
    out = []
    for k in range(len(P) // 4):
        pc = P[4 * k:4 * k + 4] @ T[:3, :3].T + T[:3, 3]
        if np.any(pc[:, 2] < 0.05):
            continue
        uv = CAM.project(pc)
        side = np.mean([np.linalg.norm(uv[i] - uv[(i + 1) % 4]) for i in range(4)])
        if np.all(CAM.in_image(uv, margin)) and side >= min_side:
            out.append(P[4 * k:4 * k + 4])
    return np.vstack(out) if out else None


def tilt_sigma(P, T, px=0.3, inflate=1.0):
    C = pose_covariance(P, T, CAM.K, px, inflate)
    Rm = T[:3, :3].T
    return roll_pitch_sigma(Rm @ C[:3, :3] @ Rm.T)


def mc_pose(P, T, px, n, refine, seed=0):
    """Pose of M from noisy corners of the tags in P through cv2 (IPPE, optionally LM-polished): (tilt errors (n, 2), pos)."""
    rng = np.random.default_rng(seed)
    uv0 = CAM.project(P @ T[:3, :3].T + T[:3, 3])
    flag = cv2.SOLVEPNP_IPPE_SQUARE if len(P) == 4 else cv2.SOLVEPNP_IPPE
    out = []
    for _ in range(n):
        uv = uv0 + rng.normal(0, px, uv0.shape)
        k, rvs, tvs, _ = cv2.solvePnPGeneric(P, uv, CAM.K, None, flags=flag)
        best = None
        for rv, tv in zip(rvs, tvs):
            if refine:
                rv, tv = cv2.solvePnPRefineLM(P, uv, CAM.K, None, rv.copy(), tv.copy())
            e = float(np.sum((cv2.projectPoints(P, rv, tv, CAM.K, None)[0].reshape(-1, 2) - uv) ** 2))
            if best is None or e < best[0]:
                best = (e, rv, tv)
        R = cv2.Rodrigues(best[1])[0]
        out.append(T[:3, :3].T @ cv2.Rodrigues(R @ T[:3, :3].T)[0].ravel())
    out = np.array(out)
    return out[:, :2]


# ===================================================================== 1. detector: LM refinement, per-frame covariance
def test_lm_refinement_removes_the_ippe_tilt_noise_of_the_single_tag_detector():
    """IPPE alone is several times noisier in tilt than the ML pose when the tag is seen face-on (review F4: 55 vs 10 mrad
    at 0.46 m); the detector now polishes every IPPE candidate with LM. Through MarkerDetector.pose_from_corners, on the
    best candidate of each frame."""
    T = cam_pose((0.0, 0.0, 0.52))
    P = tag_corners(0, 0, EDGE_S)
    uv0 = CAM.project(P @ T[:3, :3].T + T[:3, 3])
    rng = np.random.default_rng(1)
    errs, accepted = {True: [], False: []}, {True: 0, False: 0}
    for refine in (True, False):
        det = MarkerDetector("apriltag_36h11", 0, EDGE_S, CAM, refine=refine, min_side_px=20.0)
        for _ in range(250):
            obs = det.pose_from_corners(uv0 + rng.normal(0, 0.3, (4, 2)), up_in_cam=(0, 0, -1), up_sigma_rad=0.5)
            accepted[refine] += bool(obs.ok)
            Tb = obs.candidates[0][1]
            errs[refine].append((T[:3, :3].T @ cv2.Rodrigues(Tb[:3, :3] @ T[:3, :3].T)[0].ravel())[:2])
    lm, ippe = (np.sqrt(np.mean(np.square(errs[k]))) for k in (True, False))
    assert lm < 0.025 and ippe > 3 * lm
    # and the refined frames are accepted (one ML pose, not a pair of near-equal IPPE solutions to guess between)
    assert accepted[True] > 240 and accepted[False] < 200


def test_reported_covariance_matches_monte_carlo_through_cv2():
    """The Cramer-Rao covariance (inflate 1) is the ML pose's noise: LM Monte Carlo agrees within ~25 % for one tag at two
    ranges and for the board at the resting height."""
    for cam, P in (((0, 0, 0.52), tag_corners(0, 0, EDGE_S)), ((0, 0, 0.8), tag_corners(0, 0, EDGE_S)),
                   ((0, 0, 0.51), grid(DEFAULT_PITCH_M))):
        T = cam_pose(cam)
        P = in_view(P, T)
        pred = tilt_sigma(P, T)
        emp = float(np.sqrt(np.mean(mc_pose(P, T, 0.3, 500, True) ** 2)))
        assert emp == pytest.approx(pred, rel=0.25), (cam, len(P) // 4, emp, pred)


def test_covariance_follows_range_tag_size_focal_length_corner_noise_and_tag_count():
    P1 = tag_corners(0, 0, EDGE_S)
    s = {z: tilt_sigma(P1, cam_pose((0, 0, z))) for z in (0.5, 1.0)}
    assert s[1.0] == pytest.approx(4 * s[0.5], rel=0.15)                  # tilt sigma ~ z^2
    big = tilt_sigma(tag_corners(0, 0, 2 * EDGE_S), cam_pose((0, 0, 1.0)))
    assert big == pytest.approx(s[1.0] / 4, rel=0.15)                     # ~ 1 / a^2
    assert tilt_sigma(P1, cam_pose((0, 0, 0.5)), px=0.6) == pytest.approx(2 * s[0.5], rel=1e-6)   # ~ corner noise
    K2 = CAM.K.copy()
    K2[0, 0] *= 2
    K2[1, 1] *= 2
    T = cam_pose((0, 0, 0.5))
    Rm = T[:3, :3].T
    f2 = roll_pitch_sigma(Rm @ pose_covariance(P1, T, K2, 0.3)[:3, :3] @ Rm.T)
    assert f2 == pytest.approx(s[0.5] / 2, rel=0.15)                      # ~ 1 / f
    # tags in view: the board at the resting height (3+ tags) against one tag, and more tags -> less noise
    Tb = cam_pose((0.0, 0.0, 0.51))
    n_tags = lambda P: len(in_view(P, Tb)) // 4
    P9 = grid(DEFAULT_PITCH_M)
    assert n_tags(P9) >= 3
    assert tilt_sigma(in_view(P9, Tb), Tb) < tilt_sigma(P1, Tb) / 4
    two = in_view(P9, Tb)[:8]
    assert tilt_sigma(in_view(P9, Tb), Tb) < tilt_sigma(two, Tb)
    # the quoted figures of the review (0.3 px, 152 mm tag): 13 mrad at 0.52 m on axis, 1-3 mrad for the board
    assert 11e-3 < tilt_sigma(P1, cam_pose((0, 0, 0.52))) < 16e-3
    assert 0.8e-3 < tilt_sigma(in_view(P9, Tb), Tb) < 3.5e-3


def test_claw_position_covariance_is_anisotropic_mostly_horizontal_for_a_downward_camera():
    T = cam_pose((0.1, 0.05, 0.6), (0.0, 0.0))
    P = tag_corners(0, 0, EDGE_S)
    C = pose_covariance(P, T, CAM.K, 0.3, 1.0)
    cov_p, cov_att = claw_cov_from_pose(C, T, T_B_C)
    assert np.all(np.linalg.eigvalsh(cov_p) > 0)
    # z (marker normal) only sees the tilt through the HORIZONTAL part of the marker-to-claw vector (~0.2 m here), xy through
    # the vertical one (~0.6 m): 2 mm against 7.5 mm (review: 0.7 mm against 6.7 mm with the marker under the camera)
    assert cov_p[0, 0] > 8 * cov_p[2, 2] and cov_p[1, 1] > 8 * cov_p[2, 2]
    assert 0.005 < math.sqrt(cov_p[0, 0]) < 0.010
    Con = claw_cov_from_pose(pose_covariance(P, cam_pose((0, 0, 0.6), (0.0, 0.0)), CAM.K, 0.3, 1.0),
                             cam_pose((0, 0, 0.6), (0.0, 0.0)), T_B_C)[0]
    assert Con[0, 0] > 15 * Con[2, 2]                                              # marker under the camera: z is ~5x better
    assert roll_pitch_sigma(cov_att) > 5 * math.sqrt(cov_att[2, 2])                # yaw ~10x better than tilt
    # and the old isotropic model it replaces would have put the same sigma on z
    iso = (0.010 * np.linalg.norm(F.inv_T(T)[:3, 3])) ** 2
    assert cov_p[2, 2] < iso / 5


def test_no_double_counted_camera_to_body_lever_in_the_legacy_covariance():
    """claw_position_cov (frames WITHOUT a covariance of their own) no longer adds sigma^2 |camera -> body|^2; the one
    lever (marker -> body) is VisionSource's."""
    T = cam_pose((0.1, 0.05, 0.6))
    o = MarkerObservation(True, "", T)
    c0 = claw_position_cov(o, T_B_C, 520.0, EDGE_S, rot_sigma_rad=0.0)
    c1 = claw_position_cov(o, T_B_C, 520.0, EDGE_S, rot_sigma_rad=0.010)
    assert np.array_equal(c0, c1)
    now = 1.0e6
    v = VisionSource(SimpleNamespace(observe=lambda n: MarkerObservation(True, "", T, 0.3, 50.0, 100.0,
                                                                          np.zeros((4, 2)), frame_id=1, capture_us=now)),
                     T_B_C, 520.0, EDGE_S, max_age_s=0.5, now_us=lambda: now, rot_sigma=0.010)
    p = v.observe()
    assert np.allclose(p.cov - c0, np.eye(3) * (0.010 * np.linalg.norm(p.p)) ** 2)      # exactly one marker -> body lever


def test_vision_source_takes_the_frames_own_covariance_and_adds_nothing_else():
    P = tag_corners(0, 0, EDGE_S)
    T = cam_pose((0.1, 0.05, 0.6))
    C6 = pose_covariance(P, T, CAM.K, 0.3, 1.3)
    now = 1.0e6
    obs = MarkerObservation(True, "", T, 0.3, 50.0, 100.0, np.zeros((4, 2)), frame_id=1, capture_us=now, pose_cov=C6,
                            anchor_M=P.mean(0), n_tags=1)
    outs = []
    for rot_sigma in (0.010, 0.050):                      # the configured constant is NOT used for a frame with a covariance
        v = VisionSource(SimpleNamespace(observe=lambda n: obs), T_B_C, 520.0, EDGE_S, max_age_s=0.5, now_us=lambda: now,
                         rot_sigma=rot_sigma, rot_floor=0.001)
        outs.append(v.observe())
    assert np.allclose(outs[0].cov, outs[1].cov)
    want = claw_cov_from_pose(C6, T, T_B_C, floor_rad=0.001)
    assert np.allclose(outs[0].cov, want[0]) and outs[0].att_sigma_rad == pytest.approx(roll_pitch_sigma(want[1]))
    assert outs[0].att_sigma_rad > 0.012                                               # a single tag at 0.6 m is NOT 10 mrad
    assert np.allclose(outs[0].pose_cov, C6)                       # displacements use the random part only: the floor cancels
    assert outs[0].att_sigma_rad ** 2 > roll_pitch_sigma(want[1]) ** 2 - 1e-12 and outs[0].cov[0, 0] > claw_cov_from_pose(
        C6, T, T_B_C)[0][0, 0]                                                           # ... the absolute pose has it
    # the design-time prediction (excitation design) is the same model
    T_M_B = F.inv_T(T) @ F.inv_T(T_B_C)
    pred = predicted_vision_cov(CAM, T_B_C, T_M_B, EDGE_S, pixel_sigma=0.3, inflate=1.3, floor_rad=0.001)
    assert np.allclose(pred, want[0])


# ===================================================================== 3. board detector in use, single-tag fallback
def _dets(lay, ids, T, rng, px=0.3):
    out = {}
    for i in ids:
        out[i] = CAM.project(lay.corners_M(i) @ T[:3, :3].T + T[:3, 3]) + rng.normal(0, px, (4, 2))
    return out


def test_board_pose_is_used_when_two_tags_are_in_view_and_single_tag_otherwise_with_its_honest_covariance():
    lay = FloorBoardLayout.nominal(EDGE_B)
    det = BoardDetector(lay, CAM, corner_sigma_px=0.3, cov_inflate=1.3)
    T = cam_pose((0.02, -0.01, 0.51))
    rng = np.random.default_rng(0)
    vis = [i for i in lay.expected_ids if in_view(lay.corners_M(i), T) is not None]
    assert len(vis) >= 3
    o_board = det.pose_from_detections(_dets(lay, vis, T, rng), up_in_cam=(0, 0, -1))
    assert o_board.ok and len(o_board.used_ids) == len(vis) >= 3 and o_board.n_tags == len(vis)
    o_one = det.pose_from_detections(_dets(lay, vis[:1], T, rng), up_in_cam=(0, 0, -1))
    assert o_one.ok and o_one.used_ids == vis[:1] and o_one.n_tags == 1
    t_b, t_1 = (math.sqrt(np.trace(o.pose_cov[:2, :2]) / 2) for o in (o_board, o_one))
    assert t_1 > 4 * t_b                                                       # one tag: honest, much larger tilt sigma
    # a non-origin single tag is re-expressed in M with ITS corners' covariance (lever from the tag to M included)
    k = next(i for i in vis if i != lay.origin_id)
    o_k = det.pose_from_detections(_dets(lay, [k], T, rng), up_in_cam=(0, 0, -1))
    assert o_k.ok and o_k.used_ids == [k] and np.allclose(o_k.anchor_M, lay.corners_M(k).mean(0), atol=1e-9)
    # only an unsurveyed second tag: single-tag fallback, never a guess
    lay2 = FloorBoardLayout(EDGE_B)
    det2 = BoardDetector(lay2, CAM)
    o2 = det2.pose_from_detections(_dets(lay, vis, T, rng), up_in_cam=(0, 0, -1))
    assert o2.ok and o2.used_ids == [0] and o2.unsurveyed_ids


def test_service_builds_the_board_detector_only_when_a_layout_is_configured(tmp_path):
    import json
    from roomcleaner.cdpr.service import build_marker_detector
    cfg = load_config(SIM)
    assert isinstance(build_marker_detector(cfg, CAM), MarkerDetector)
    FloorBoardLayout.nominal(EDGE_B).save(tmp_path / "layout.json")
    raw = json.load(open(SIM))
    raw["marker"]["board_layout_file"] = str(tmp_path / "layout.json")
    det = build_marker_detector(load_config(raw), CAM)
    assert isinstance(det, BoardDetector) and len(det.layout.surveyed_ids()) == 9
    assert det._sel.corner_sigma_px == cfg.camera.corner_sigma_px and det._sel.cov_inflate == cfg.camera.pose_cov_inflate


# ===================================================================== 2. layout: pitch 0.25 m
def test_default_pitch_is_0p25_and_the_validated_maximum_is_enforced():
    assert DEFAULT_PITCH_M == 0.25 and MAX_PITCH_M == 0.28
    pos = FloorBoardLayout.nominal_positions()
    assert pos[0] == (0.0, 0.0) and sorted(pos) == list(range(9))
    xs = sorted({round(p[0], 6) for p in pos.values()})
    assert xs == [-0.25, 0.0, 0.25]
    lay = FloorBoardLayout.nominal(EDGE_B)
    assert math.hypot(*lay.pose(1)[:2]) == pytest.approx(0.25 * math.sqrt(2))        # id 1: the top-left corner of the ring
    with pytest.raises(ValueError, match="validated maximum"):
        FloorBoardLayout.nominal(EDGE_B, pitch_m=0.30)
    assert FloorBoard.nominal().corners.shape == (9, 4, 3)
    assert float(np.ptp(FloorBoard.nominal().centres[:, 0])) == pytest.approx(0.5)


def test_resting_claw_sees_at_least_two_tags_at_the_default_pitch_but_only_one_at_the_old_pitch():
    """review F3: pitch 0.42 gives ONE tag at the 0.5 m resting height in 8 of 8 seeds, 0.25 gives 3-4."""
    rng = np.random.default_rng(0)
    new, old = FloorBoard.nominal(EDGE_B), FloorBoard(3, 3, 0.42, EDGE_B)
    n_new, n_old = [], []
    for _ in range(40):
        T_M_B = F.make_T(F.rot_z(rng.uniform(-np.pi, np.pi)), [*rng.uniform(-0.06, 0.06, 2), 0.5])
        for b, out in ((new, n_new), (old, n_old)):
            out.append(len(b.visible_tags(CAM, np.asarray(T_B_C), T_M_B, min_side_px=40.0)))
    assert min(n_new) >= 2 and np.median(n_new) >= 3
    assert np.median(n_old) <= 2 and min(n_old) <= 1


def test_print_tool_states_the_new_pitch_and_the_overlap_and_the_old_printout_is_kept(tmp_path):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    from pathlib import Path
    from tools import print_floor_board as pfb
    assert pfb.DEFAULT_PITCH_MM == 250.0 and pfb.MAX_PITCH_MM == 280.0
    out = pfb.build_pdf(tmp_path / "b.pdf")
    txt = pypdf.PdfReader(str(out)).pages[0].extract_text()
    flat = " ".join(txt.split())
    assert "250 mm centre to centre" in flat and "OVERLAP" in flat and "280 mm" in flat
    assert "margins" in flat and "NEVER cover" in flat
    with pytest.raises(ValueError, match="280"):
        pfb.build_pdf(tmp_path / "far.pdf", pitch_mm=300.0)
    root = Path(__file__).resolve().parents[2] / "prints"
    new_txt = " ".join(pypdf.PdfReader(str(root / "floor_board_letter.pdf")).pages[0].extract_text().split())
    old_txt = " ".join(pypdf.PdfReader(str(root / "floor_board_letter_450mm.pdf")).pages[0].extract_text().split())
    assert "250 mm" in new_txt and "450 mm" in old_txt and "450 mm" not in new_txt
    # a layout page for a pitch the sheets do not overlap at says so
    far = pfb.build_pdf(tmp_path / "p28.pdf", pitch_mm=280.0)
    assert "do not overlap" in " ".join(pypdf.PdfReader(str(far)).pages[0].extract_text().split())


# ===================================================================== 4. camera-frame displacement
def _frames(lay_corners, T_true_list, rng, px=0.3, inflate=1.3, floor=0.001):
    """PoseObs of a claw at the given true T_M_B poses, noise from the pose covariance of ``lay_corners`` (one tag or a board)."""
    cfg = load_config(SIM)
    now = {"us": 1.0e6}
    seq = iter(T_true_list)
    cur = {}

    def observe(n):
        T_M_B = next(seq)
        T_C_M = F.inv_T(T_M_B @ T_B_C)
        P = lay_corners
        C = pose_covariance(P, T_C_M, CAM.K, px, 1.0)
        e = np.linalg.cholesky(C) @ rng.normal(0, 1, 6)
        T = T_C_M.copy()
        T[:3, :3] = F.rotvec_to_matrix(e[:3]) @ T[:3, :3]
        T[:3, 3] += e[3:]
        o = MarkerObservation(True, "", T, 0.3, 50.0, 100.0, CAM.project(P @ T[:3, :3].T + T[:3, 3])[:4], frame_id=1,
                              capture_us=now["us"], pose_cov=pose_covariance(P, T, CAM.K, px, inflate),
                              anchor_M=P.mean(0), n_tags=len(P) // 4)
        return o
    v = VisionSource(SimpleNamespace(observe=observe), T_B_C, CAM.fx, EDGE_S, max_age_s=10.0, now_us=lambda: now["us"],
                     rot_floor=floor)
    return v


def _claw(x, y, z=0.5, yaw=0.0):
    return F.make_T(F.rot_z(yaw), [x, y, z])


def test_camera_frame_displacement_cancels_the_tilt_lever_noise_of_the_absolute_pose():
    """One tag, 0.5 m, 0.3 px: the absolute claw position of an UNMOVED claw scatters ~7 mm per axis (tilt x lever); the
    camera-frame displacement from a reference only ~0.3 mm, so a 3 mm slide is measured to ~0.5 mm."""
    rng = np.random.default_rng(2)
    P = tag_corners(0, 0, EDGE_S)
    n = 60
    v = _frames(P, [_claw(0.0, 0.0)] * (n + 1), rng)
    ref_frames = [v.observe() for _ in range(1)]
    ref = ref_frames[0]
    absp = np.array([v.observe().p for _ in range(n)])
    assert absp[:, :2].std(0).mean() > 4e-3
    v2 = _frames(P, [_claw(0.0, 0.0)] + [_claw(0.003, -0.002)] * n, rng)
    ref = v2.observe()
    d = np.array([cam_displacement(v2.observe(), ref)[0] for _ in range(n)])
    assert np.abs(d.mean(0) - [0.003, -0.002, 0.0]).max() < 1.0e-3
    assert d[:, :2].std(0).max() < 1.0e-3                                      # against > 4 mm for the absolute pose
    # unmoved: the same statistic is ~zero and its noise is the camera-frame one
    v3 = _frames(P, [_claw(0.0, 0.0)] * (n + 1), rng)
    ref = v3.observe()
    d0 = np.array([cam_displacement(v3.observe(), ref)[0] for _ in range(n)])
    assert np.linalg.norm(d0.mean(0)) < 1e-3 and np.sqrt(np.mean(np.sum(d0 ** 2, axis=1))) < 2e-3


def test_camera_frame_displacement_is_not_fooled_by_the_claw_yawing():
    """A cable take-up yaws the claw by degrees about its own axis; the camera 9 cm to the side and the tag off to the side
    make that look like a lateral shift of the whole claw unless the frame's own yaw is used. Noise-free frames, with the
    claw hanging level and tilted 3 deg (the CAD claw hangs a few degrees off: it yaws about its tilted body axis)."""
    rng = np.random.default_rng(3)
    P = tag_corners(0.0, 0.0, EDGE_S)
    for tilt in (0.0, math.radians(3.0)):
        R0 = F.rot_z(0.3) @ F.rot_x(tilt) @ F.rot_y(-0.4 * tilt)
        for yaw in (0.0, math.radians(2), math.radians(6)):
            poses = [F.make_T(R0, [0.25, 0.1, 0.55]), F.make_T(R0 @ F.rot_z(yaw), [0.25, 0.1, 0.55])]   # about the BODY z
            v = _frames(P, poses, rng, px=1e-9)
            ref, o = v.observe(), v.observe()
            d = cam_displacement(o, ref)[0]
            assert np.linalg.norm(d) < 1e-6, (tilt, yaw, d)                    # the body origin did not move
            if yaw > 0:    # a fixed reference rotation (plain -R_ref^T (t - t_ref)) would read many mm
                naive = -(ref.T_C_M[:3, :3].T @ (o.T_C_M[:3, 3] - ref.T_C_M[:3, 3]))
                assert np.linalg.norm(naive) > 5e-3
    # a real tilt of the claw (beyond the noise) is taken from the frame's own rotation: the origin did not move
    v = _frames(P, [_claw(0.0, 0.0), F.make_T(F.rot_x(0.12), [0.0, 0.0, 0.5])], rng, px=1e-9)
    ref, o = v.observe(), v.observe()
    assert np.linalg.norm(cam_displacement(o, ref)[0]) == pytest.approx(0.0, abs=1e-6)
    # a tilt change that accompanies a yaw (3 % of it, as in the rigid-body simulator) is used when the view is good (board:
    # tilt noise ~1 mrad) and ignored when it is not (one tag: 13 mrad), so the displacement is right to ~0.5 mm vs ~1.5 mm
    Pb = grid(DEFAULT_PITCH_M)
    for P_, expect_small in ((Pb, True), (P, False)):
        errs = []
        for k in range(30):
            ra = F.make_T(R0, [0.0, 0.0, 0.5])
            R1 = R0 @ F.rot_z(0.08) @ F.rot_y(0.0027)                          # 0.08 rad of yaw with a 2.7 mrad tilt change
            v = _frames(P_, [ra, F.make_T(R1, [0.0, 0.0, 0.5])], np.random.default_rng(100 + k))
            ref, o = v.observe(), v.observe()
            errs.append(cam_displacement(o, ref)[0])
        e = np.sqrt(np.mean(np.sum(np.square(errs), axis=1)))
        if expect_small:
            assert e < 1.0e-3, e
        else:
            assert e < 4.0e-3, e                                                # honest: not better than ~1.5 mm


def test_a_tilt_spike_of_one_frame_is_not_motion_for_a_claw_on_the_floor():
    """A resting claw cannot tilt: the floor displacement uses the reference tilt only, so a 16 mrad tilt outlier of ONE frame (a
    4-5 sigma event for the board at 0.5 px; 8 mm through the 0.5 m lever) does not read as a slide, which would end a take-up early
    (review F2; found in the 0.5 px study). The general displacement takes a tilt beyond 5 sigma as real and uses it."""
    P = grid(DEFAULT_PITCH_M)
    rng = np.random.default_rng(8)
    v = _frames(P, [_claw(0.0, 0.0, 0.5)] * 11 + [_claw(0.0, 0.0, 0.5)], rng, px=1e-9)
    ref = v._summarise([v.observe() for _ in range(10)])
    o = v.observe()
    spike = F.rot_x(0.016)                                         # 16 mrad about the camera x axis, one frame
    T = o.T_C_M.copy()
    T[:3, :3] = spike @ T[:3, :3]
    o.T_C_M = T
    assert np.linalg.norm(floor_displacement(o, ref)[0]) < 0.5e-3
    assert np.linalg.norm(cam_displacement(o, ref)[0]) > 4e-3        # (own rotation: the lever carries the spike into the position)
    # yaw of the resting claw as it slides and turns is still the frame's own
    v = _frames(P, [_claw(0.0, 0.0, 0.5, 0.3)] * 10 + [_claw(0.0, 0.0, 0.5, 0.3 + 0.1)], rng, px=1e-9)
    ref = v._summarise([v.observe() for _ in range(10)])
    assert np.linalg.norm(floor_displacement(v.observe(), ref)[0]) < 1e-6


def test_still_pose_rejects_a_30mm_swing_on_the_raw_motion_not_the_inflated_covariance():
    """review F6: the absolute-pose covariance of one tag is inflated ~10x by the tilt lever, and a scatter threshold built
    on it accepted a 30 mm swing as 'still'. The test is now on the camera-frame scatter."""
    P = tag_corners(0, 0, EDGE_S)
    for rot_sigma in (0.010, 0.004):
        t = {"s": 0.0}
        poses = lambda: _claw(0.030 * math.sin(2 * math.pi * t["s"] / 2.8), 0.0)
        rng = np.random.default_rng(4)
        now = {"us": 1.0e6}

        def observe(n, rng=rng, now=now):
            T_C_M = F.inv_T(poses() @ T_B_C)
            C = pose_covariance(P, T_C_M, CAM.K, 0.3, 1.0)
            e = np.linalg.cholesky(C) @ rng.normal(0, 1, 6)
            T = T_C_M.copy()
            T[:3, :3] = F.rotvec_to_matrix(e[:3]) @ T[:3, :3]
            T[:3, 3] += e[3:]
            return MarkerObservation(True, "", T, 0.3, 50.0, 100.0, np.zeros((4, 2)), frame_id=1, capture_us=now["us"],
                                     pose_cov=pose_covariance(P, T, CAM.K, 0.3, 1.3), anchor_M=P.mean(0))
        v = VisionSource(SimpleNamespace(observe=observe), T_B_C, CAM.fx, EDGE_S, max_age_s=10.0, now_us=lambda: now["us"],
                         rot_sigma=rot_sigma)

        def wait(s):
            t["s"] += s
            now["us"] += s * 1e6
        sp, why = v.still_pose(10, wait, interval_s=0.1, max_wait_s=0.95, spread_max_m=0.003)
        assert sp is None, (rot_sigma, "a 30 mm swing was accepted as still")
    # the same noisy view of an UNMOVED claw is accepted at the first window
    t = {"s": 0.0}
    poses = lambda: _claw(0.0, 0.0)
    rng = np.random.default_rng(5)
    now = {"us": 1.0e6}

    def observe(n):
        T_C_M = F.inv_T(poses() @ T_B_C)
        C = pose_covariance(P, T_C_M, CAM.K, 0.3, 1.0)
        e = np.linalg.cholesky(C) @ rng.normal(0, 1, 6)
        T = T_C_M.copy()
        T[:3, :3] = F.rotvec_to_matrix(e[:3]) @ T[:3, :3]
        T[:3, 3] += e[3:]
        return MarkerObservation(True, "", T, 0.3, 50.0, 100.0, np.zeros((4, 2)), frame_id=1, capture_us=now["us"],
                                 pose_cov=pose_covariance(P, T, CAM.K, 0.3, 1.3), anchor_M=P.mean(0))
    v = VisionSource(SimpleNamespace(observe=observe), T_B_C, CAM.fx, EDGE_S, max_age_s=10.0, now_us=lambda: now["us"])
    sp, why = v.still_pose(10, lambda s: now.__setitem__("us", now["us"] + s * 1e6), interval_s=0.1, max_wait_s=1.5)
    assert sp is not None and sp.spread_cam_m < 2e-3 and sp.spread_m > 2e-3     # absolute scatter is large, raw one small
    assert sp.n_tags == 1 and sp.att_sigma_rad > 0.003      # 13 mrad per frame / sqrt(10), x1.3 margin


def test_drag_watch_is_filtered_and_scales_with_the_covariance_instead_of_a_fixed_single_frame_threshold():
    P = tag_corners(0, 0, EDGE_S)
    rng = np.random.default_rng(6)
    v = _frames(P, [_claw(0.0, 0.0)] * 11, rng)
    ref = v._summarise([v.observe() for _ in range(10)])

    def watch(shifts, px=0.3):
        w = DragWatch(ref, floor_m=0.010, k=4.0, n=3)
        vv = _frames(P, [_claw(s, 0.0) for s in shifts], np.random.default_rng(7), px=px)
        return [w.update(vv.observe()) for _ in shifts], w
    # a single 14 mm frame in a still series never trips it (the old test: one frame above a fixed 10 mm)
    tripped, w = watch([0, 0, 0.014, 0, 0, 0])
    assert not any(tripped)
    # a sustained 14 mm drag does, after N frames
    tripped, w = watch([0, 0, 0.014, 0.014, 0.014, 0.014])
    assert tripped[-1] and not tripped[1] and w.last_disp_m == pytest.approx(0.014, abs=1.5e-3)
    # below the 10 mm floor nothing trips, however many frames
    assert not any(watch([0.006] * 8)[0])
    # the threshold follows the noise: with a 40x noisier corner detector (12 px!) the same 14 mm drag is within the noise
    tripped, w = watch([0.014] * 8, px=12.0)
    assert w.last_thr_m > 0.014 and not any(tripped)
    assert watch([0.0] * 8)[1].last_thr_m == pytest.approx(0.010)               # quiet view: the floor only


# ===================================================================== 5. simulator realism
def _sim(**kw):
    from roomcleaner.cdpr.sim.harness import SimRobot
    return SimRobot(fast_cfg(), seed=1, mount_err_rad=0.0, **kw)


def _tilt_noise(r, n=300):
    """Std of the true-vs-measured roll/pitch error of the simulator's frames for the claw where it is (marker frame)."""
    errs, sig = [], []
    T_true = F.inv_T(r.world.T_M_B() @ r.simcam.T_B_C)
    for _ in range(n):
        o = r.simcam.observe(0.0)
        assert o.ok
        e = F.matrix_to_rotvec(o.T_C_M[:3, :3] @ T_true[:3, :3].T)
        errs.append((T_true[:3, :3].T @ e))
        sig.append(roll_pitch_sigma(o.T_C_M[:3, :3].T @ o.pose_cov[:3, :3] @ o.T_C_M[:3, :3]))
    errs = np.array(errs)
    return errs[:, :2].std(), errs[:, 2].std(), float(np.mean(sig)), o


def test_sim_camera_noise_comes_from_the_tags_actually_in_view():
    single = _sim()
    s_t, s_y, rep, o = _tilt_noise(single)
    assert o.n_tags == 1 and 0.010 < s_t < 0.017                               # one 152 mm tag at the 0.5 m rest height
    assert s_y < 0.4 * s_t                                                     # anisotropic: yaw much better than tilt
    assert rep == pytest.approx(1.3 * s_t, rel=0.25)                           # the frame reports (inflated) what it has
    board = _sim(camera_kw={"board": FloorBoard.nominal(EDGE_B)})
    b_t, b_y, rep_b, o = _tilt_noise(board)
    assert o.n_tags >= 3 and b_t < 0.004 and b_t < s_t / 4
    # corner noise is configurable (plant), and the estimator keeps what it was told unless changed too
    noisy = _sim(camera_kw={"pixel_sigma": 0.5, "est_pixel_sigma": 0.3})
    n_t, _, rep_n, _ = _tilt_noise(noisy)
    assert n_t == pytest.approx(s_t * 0.5 / 0.3, rel=0.2) and rep_n == pytest.approx(rep, rel=0.1)


def test_sim_camera_fixed_noise_mode_is_the_old_regression_mode():
    r = _sim(camera_kw={"noise_model": "fixed"})
    o = r.simcam.observe(0.0)
    assert o.ok and o.pose_cov is None                                         # no covariance of its own: the estimator uses
    p = r.vision.observe()                                                     # its configured attitude sigma
    assert p.att_sigma_rad == r.cfg.claw.vision_attitude_sigma_rad
    s_t, s_y, *_ = _fixed_noise(r)
    assert s_t == pytest.approx(0.002, rel=0.25) and s_y == pytest.approx(0.002, rel=0.25)      # iid 2 mrad on every axis
    rb = _sim(camera_kw={"noise_model": "fixed", "board": FloorBoard.nominal(EDGE_B)})
    assert _fixed_noise(rb)[0] == pytest.approx(s_t, rel=0.25)                 # independent of the tags in view
    from roomcleaner.cdpr.sim.world import SimCamera
    with pytest.raises(ValueError, match="noise_model"):
        SimCamera(r.world, CAM, T_B_C, EDGE_S, noise_model="bogus")


def _fixed_noise(r, n=300):
    T_true = F.inv_T(r.world.T_M_B() @ r.simcam.T_B_C)
    e = np.array([T_true[:3, :3].T @ F.matrix_to_rotvec(r.simcam.observe(0.0).T_C_M[:3, :3] @ T_true[:3, :3].T)
                  for _ in range(n)])
    return e[:, :2].std(), e[:, 2].std()


# ===================================================================== 6. settle gate
def test_dwell_is_counted_from_the_last_observed_motion():
    """review F8a: a claw seen swinging until 3 s and then lost used to be approved ~1.4 s later."""
    cfg = fast_cfg()
    swing = lambda t: 6.0 * math.sin(2 * math.pi * t / 0.9)
    ctx = FakeCtx(cfg, lambda t: _obs(t, shift_px=swing(t)) if t < 3.0 else _obs(t, ok=False))
    res = wait_until_still(ctx)
    dwell = settle_dwell_s(cfg.claw, cfg.tasks)
    assert res.ok and res.method == "dwell"
    last_motion = 2.9                                                           # last frame pair above the rate limit
    assert res.waited_s >= last_motion + dwell - 0.3 and res.waited_s <= 3.0 + dwell + 0.6
    # never observed: counted from the start of waiting, as before
    ctx = FakeCtx(cfg, lambda t: _obs(t, ok=False))
    res = wait_until_still(ctx)
    assert res.waited_s == pytest.approx(dwell, abs=1e-6)
    # a claw observed to be still (no motion ever seen) and then lost: the dwell counts from the start of waiting
    ctx = FakeCtx(cfg, lambda t: _obs(t) if t < 0.3 else _obs(t, ok=False))
    assert wait_until_still(ctx).waited_s == pytest.approx(dwell, abs=1e-6)


def test_period_margin_covers_the_compound_pendulum():
    cfg = load_config(SIM)
    assert cfg.tasks.grip_period_margin == 1.25
    L = pendulum_length_m(cfg.claw)
    T = pendulum_period_s(L)
    k = 0.13                                                                    # assumed gyration radius about the CoM (review)
    T_compound = 2 * math.pi * math.sqrt((L ** 2 + k ** 2) / (9.81 * L))
    assert T < T_compound < 1.25 * T
    assert settle_dwell_s(cfg.claw, cfg.tasks) == pytest.approx(max(cfg.tasks.grip_settle_min_s, 5 * 1.25 * T))
    raw = __import__("json").load(open(SIM))
    raw["tasks"]["grip_period_margin"] = 0.0
    with pytest.raises(ConfigError, match="grip_period_margin"):
        load_config(raw)


def test_loaded_release_uses_the_longer_loaded_pendulum_and_always_the_full_dwell():
    cfg = fast_cfg()
    L = pendulum_length_m(cfg.claw)
    Lp = loaded_pendulum_length_m(cfg.claw, 0.9)
    assert Lp > 1.7 * L and loaded_pendulum_length_m(cfg.claw, 0.0) == L
    d0, d1 = settle_dwell_s(cfg.claw, cfg.tasks), settle_dwell_s(cfg.claw, cfg.tasks, 0.9)
    assert d1 > 1.3 * d0 and d1 < cfg.tasks.grip_settle_timeout_s
    # camera sees the claw still from the start: unloaded, approved after the N still frames; loaded, only after the dwell
    ctx = FakeCtx(cfg, lambda t: _obs(t))
    r0 = wait_until_still(ctx)
    assert r0.ok and r0.method == "camera" and r0.waited_s < 1.0
    ctx = FakeCtx(cfg, lambda t: _obs(t))
    r1 = wait_until_still(ctx, payload_kg=0.9)
    assert r1.ok and r1.method == "camera" and r1.waited_s >= d1 - 1e-6
    # ... and the full dwell counts from the last motion seen
    ctx = FakeCtx(cfg, lambda t: _obs(t, shift_px=(8.0 if abs(t - 1.0) < 0.05 else 0.0)))
    assert wait_until_still(ctx, payload_kg=0.9).waited_s >= 1.0 + d1 - 0.2
    # the task layer asks for it at a release (payload = tasks.max_payload_kg) and not at a grip
    from roomcleaner.cdpr.tasks import TaskRunner
    ctx = FakeCtx(cfg, lambda t: _obs(t))
    ctx.validated_volume, ctx.ledger, ctx.ws, ctx.lim = None, SimpleNamespace(level="LOCAL_ONLY"), None, None
    runner = TaskRunner(ctx, None)
    runner._here = lambda: np.array([1.0, 1.0, 0.5])
    ok, _ = runner._settle_and_approve("release x", payload_kg=cfg.tasks.max_payload_kg)
    assert ok and runner.approvals[-1]["payload_kg"] == 0.9 and runner.approvals[-1]["waited_s"] >= d1 - 0.2
    import inspect
    src = inspect.getsource(TaskRunner._handle)
    assert 'self._settle_and_approve(f"release {item.id}", payload_kg=tc.max_payload_kg)' in src
    assert 'self._settle_and_approve(f"grip {item.id}", grip_pose)' in src


# ---- mount offset: the post-correction check tests something real (held-out frames)
def test_mount_offset_holdout_passes_for_a_resting_claw_and_fails_when_the_claw_moves_between_the_sets():
    from roomcleaner.cdpr.sim.harness import SimRobot
    # board fixture, resting claw: recovered to ~1 mrad and the held-out residual is far inside the limit
    r = SimRobot(fast_cfg(), seed=2, mount_err_rad=0.02, camera_kw={"board": FloorBoard.nominal(EDGE_B)})
    S = StartupSequencer(r.ctx)
    Q_true = np.linalg.inv(r.simcam.T_B_C_nominal[:3, :3]) @ r.simcam.T_B_C[:3, :3]
    held = S._measure_mount(S._still(state="SELF_CHECK", min_frames=30), "SELF_CHECK")
    m = S.rep.measurements
    err = np.linalg.norm(F.matrix_to_rotvec(r.vision.mount_Q @ Q_true.T))
    assert err < 0.003 and m["camera_mount_holdout_residual_rad"] < m["camera_mount_holdout_limit_rad"]
    assert held.n_tags >= 2 and held.att_sigma_rad < 0.004                      # the board pose, not the single tag
    # a claw that tilts between the two sets (rocking on its jaws, a jaw on the paper edge): refused, mount not kept
    r = SimRobot(fast_cfg(), seed=2, mount_err_rad=0.02, camera_kw={"board": FloorBoard.nominal(EDGE_B)})
    S = StartupSequencer(r.ctx)
    first = S._still(state="SELF_CHECK", min_frames=30)
    r.simcam.T_B_C[:3, :3] = r.simcam.T_B_C[:3, :3] @ F.rot_x(math.radians(1.5))      # 1.5 deg: far above the 3 mrad floor
    with pytest.raises(StartupAbort, match="not reproducible"):
        S._measure_mount(first, "SELF_CHECK")
    assert r.ctx.mount_angle_rad is None and np.allclose(r.vision.mount_Q, np.eye(3))


def test_startup_floor_stage_and_mount_use_the_board_pose_when_two_tags_are_in_view():
    from roomcleaner.cdpr.sim.harness import SimRobot
    r = SimRobot(fast_cfg(), seed=4, mount_err_rad=0.02, camera_kw={"board": FloorBoard.nominal(EDGE_B)})
    S = StartupSequencer(r.ctx)
    S.self_check()
    m = S.rep.measurements
    assert m["floor_tags_in_view"] >= 2 and m["floor_attitude_sigma_rad"] < 0.004
    assert m["vision_noise_m"] < 0.002 < m["vision_noise_absolute_m"] * 4          # camera-frame noise drives the thresholds
    single = SimRobot(fast_cfg(), seed=4, mount_err_rad=0.02)
    S1 = StartupSequencer(single.ctx)
    S1.self_check()
    assert S1.rep.measurements["floor_tags_in_view"] == 1
    assert S1.rep.measurements["floor_attitude_sigma_rad"] > 3 * m["floor_attitude_sigma_rad"]


# ===================================================================== calibration uses the pose's own attitude sigma
def test_calibration_length_noise_uses_the_poses_own_attitude_sigma_with_the_configured_value_as_floor():
    from roomcleaner.cdpr.calibration import Calibrator, PoseSample
    from roomcleaner.cdpr.spool import CableMap
    cfg = load_config(SIM)
    maps = {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations}
    cal = Calibrator(cfg, maps)
    assert cal.spaced
    mk = lambda att: PoseSample(np.zeros(4), np.zeros(3), np.eye(3), np.eye(3) * 1e-6, att_sigma_rad=att)
    sg = cal._len_sigmas([mk(None), mk(0.002), mk(0.010), mk(0.060)])
    assert np.allclose(sg[0], sg[1]) and np.allclose(sg[0], sg[2])                # a good view is not credited below the config
    lever = np.linalg.norm(cal.attach, axis=1)
    assert np.allclose(sg[3], np.hypot(cfg.calibration.length_sigma_m, 0.060 * lever))      # a poor one (1 tag far away) is not
    assert np.all(sg[3] > sg[0])
