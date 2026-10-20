"""Multi-sheet floor reference (D26): printable PDF, joint-PnP detector, survey.

Synthetic data only: tags are rendered into images with a known camera
(vision.board.render_board_view) or projected with Gaussian corner noise.
"""
import math
import re
import shutil
import subprocess

import cv2
import numpy as np
import pytest

from roomcleaner.cdpr import frames as F
from roomcleaner.cdpr.vision.board import (BoardDetector, BoardObservation, BoardSurvey, FloorBoardLayout,
                                           render_board_view, wrap_pi)
from roomcleaner.cdpr.vision.camera import CameraModel
from roomcleaner.cdpr.vision.marker import MarkerDetector, MarkerObservation, render_marker_view
from tools import print_floor_board as pfb

CAM = CameraModel.load("config/camera.sim.json")
EDGE = 0.150
FAM = "apriltag_36h11"


# ------------------------------------------------------------------ helpers
def cam_above(height, dx=0.0, dy=0.0, roll=0.0, pitch=0.0, yaw=0.0):
    """T_C_M for a camera looking straight down at the floor from ``height``."""
    R_M_C = F.rpy_to_matrix(roll, pitch, yaw) @ F.rot_x(np.pi)
    return F.inv_T(F.make_T(R_M_C, [dx, dy, height]))


def random_board(rng, jitter=0.1, min_gap=0.30):
    """3x3 grid at ~0.45 m with +-jitter offsets and any yaw (sheets never overlap)."""
    while True:
        true = {0: (0.0, 0.0, 0.0)}
        k = 1
        for gx in (-1, 0, 1):
            for gy in (-1, 0, 1):
                if (gx, gy) != (0, 0):
                    true[k] = (gx * 0.45 + rng.uniform(-jitter, jitter), gy * 0.45 + rng.uniform(-jitter, jitter),
                               rng.uniform(-np.pi, np.pi))
                    k += 1
        xy = np.array([p[:2] for p in true.values()])
        d = np.linalg.norm(xy[:, None] - xy[None], axis=2) + np.eye(len(xy)) * 9
        if d.min() > min_gap:
            return true


def truth_layout(true, edge=EDGE):
    lay = FloorBoardLayout(edge)
    for i, p in true.items():
        if i:
            lay.set_pose(i, *p)
    return lay


def random_cam(rng):
    return cam_above(rng.uniform(1.2, 1.7), *rng.uniform(-0.3, 0.3, 2), *rng.uniform(-0.06, 0.06, 2),
                     rng.uniform(-3, 3))


def projected(true_lay, ids, T, rng, sigma=0.3, scale=None):
    out = {}
    for i in ids:
        pts = true_lay.corners_M(i)
        if scale and i in scale:
            c = true_lay.T_M_T(i)[:3, 3]
            pts = c + (pts - c) * scale[i]
        pc = pts @ T[:3, :3].T + T[:3, 3]
        out[i] = CAM.project(pc) + rng.normal(0, sigma, (4, 2))
    return out


def pose_errors(est, true_lay, ids):
    pos, yaw = [], []
    for i in ids:
        x, y, w = est.pose(i)
        tx, ty, tw = true_lay.pose(i)
        pos.append(math.hypot(x - tx, y - ty))
        yaw.append(abs(math.degrees(float(wrap_pi(w - tw)))))
    return np.array(pos), np.array(yaw)


def cam_error(T_est, T_true):
    return (np.linalg.norm(T_est[:3, 3] - T_true[:3, 3]),
            math.degrees(np.linalg.norm(F.matrix_to_rotvec(T_est[:3, :3].T @ T_true[:3, :3]))))


# ----------------------------------------------------------------- PDF tool
@pytest.fixture(scope="module")
def pdf9(tmp_path_factory):
    pytest.importorskip("reportlab")
    out = tmp_path_factory.mktemp("board") / "floor_board_letter.pdf"
    pfb.build_pdf(out, range(9), 150.0)
    return out


def test_pdf_is_letter_with_exact_tags(pdf9):
    pytest.importorskip("pypdf")
    lines = pfb.verify_pdf(pdf9, range(9), 150.0)        # asserts page size, edge, bit pattern, margins
    assert len(lines) == 10 and lines[0].startswith("10 pages")


def test_pdf_options_and_limits(tmp_path):
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    out = pfb.build_pdf(tmp_path / "two.pdf", [3, 7], 140.0, instructions=False)
    pfb.verify_pdf(out, [3, 7], 140.0, instructions=False)
    with pytest.raises(AssertionError):                   # wrong expected edge is caught
        pfb.verify_pdf(out, [3, 7], 150.0, instructions=False)
    with pytest.raises(ValueError, match="does not fit"):
        pfb.build_pdf(tmp_path / "big.pdf", [0], 170.0)
    with pytest.raises(ValueError, match="outside"):
        pfb.build_pdf(tmp_path / "id.pdf", [9999], 150.0)
    pfb.main(["--out", str(tmp_path / "cli.pdf"), "--ids", "0-2", "--edge-mm", "150"])
    assert (tmp_path / "cli.pdf").exists()


@pytest.mark.skipif(shutil.which("pdftoppm") is None, reason="pdftoppm not installed")
def test_pdf_raster_tag_size_ids_and_margins(pdf9, tmp_path):
    """Independent of the PDF parser: rasterise, detect with the real detector, measure in mm."""
    stem = tmp_path / "pg"
    subprocess.run(["pdftoppm", "-r", "300", "-png", str(pdf9), str(stem)], check=True)
    pages = sorted(tmp_path.glob("pg-*.png"))
    assert len(pages) == 10
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    det = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters())
    mm_per_px = 25.4 / 300
    for k, p in enumerate(pages[1:]):
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        assert img.shape == (3300, 2550)                  # 11 x 8.5 in at 300 dpi
        corners, ids, _ = det.detectMarkers(img)
        assert ids is not None and list(ids.ravel()) == [k]
        c = corners[0].reshape(4, 2)
        edge_mm = np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]) * mm_per_px
        assert abs(edge_mm - 150.0) < 0.25, edge_mm
    # everything printed stays inside the 1/4 in printer margin (at 100 dpi: 25 px)
    for p in pages:
        small = cv2.resize(cv2.imread(str(p), cv2.IMREAD_GRAYSCALE), None, fx=1 / 3, fy=1 / 3, interpolation=cv2.INTER_AREA)
        ys, xs = np.nonzero(small < 200)
        m = int(round(pfb.PRINTER_MARGIN_MM / 25.4 * 100)) - 1
        assert xs.min() >= m and ys.min() >= m and xs.max() <= 850 - m and ys.max() <= 1100 - m, (p.name, xs.min(), ys.min())


# ------------------------------------------------------------------- layout
def test_layout_json_roundtrip_and_origin_fixed(tmp_path):
    lay = FloorBoardLayout(EDGE)
    assert lay.surveyed_ids() == [0] and lay.pose(0) == (0.0, 0.0, 0.0)
    assert np.allclose(lay.T_M_T(0), np.eye(4))
    cov = np.diag([1e-6, 2e-6, 3e-7])
    lay.set_pose(4, 0.41, -0.52, 4.0, cov, n_obs=33, note="x")
    assert abs(lay.pose(4)[2] - (4.0 - 2 * np.pi)) < 1e-12      # yaw wrapped
    with pytest.raises(ValueError):
        lay.set_pose(0, 0.1, 0, 0)
    with pytest.raises(KeyError):
        lay.set_pose(42, 0, 0, 0)
    lay.save(tmp_path / "board.json")
    back = FloorBoardLayout.load(tmp_path / "board.json")
    assert back.surveyed_ids() == [0, 4] and back.edge_m == EDGE and back.origin_id == 0
    assert np.allclose(back.tags[4].cov, cov) and back.tags[4].n_obs == 33
    assert np.allclose(back.corners_M(4), lay.corners_M(4))
    assert abs(back.tags[4].sigma_xy_m - math.sqrt(1.5e-6)) < 1e-12
    assert not back.is_surveyed(5)
    # corners follow the single-tag convention: TL, TR, BR, BL with +Y up the page
    c0 = back.corners_M(0)
    assert np.allclose(c0[0], [-EDGE / 2, EDGE / 2, 0]) and np.allclose(c0[2], [EDGE / 2, -EDGE / 2, 0])


# ----------------------------------------------------------------- detector
def test_joint_pnp_beats_single_tag_at_1p5m():
    rng = np.random.default_rng(3)
    true = random_board(rng)
    tl = truth_layout(true)
    joint, single, refused = [], [], 0
    for _ in range(12):
        T = cam_above(1.5, *rng.uniform(-0.15, 0.15, 2), *rng.uniform(-0.05, 0.05, 2), rng.uniform(-3, 3))
        img = render_board_view(CAM, FAM, EDGE, true, T, rng=rng, noise=2.0)
        o = BoardDetector(tl, CAM).detect(img, up_in_cam=T[:3, 2])
        assert isinstance(o, MarkerObservation) and isinstance(o, BoardObservation)
        assert o.ok and o.rms_px < 1.0, o.reason
        assert len(o.used_ids) >= 6
        joint.append(cam_error(o.T_C_M, T))
        o1 = BoardDetector(FloorBoardLayout(EDGE), CAM).detect(img, up_in_cam=T[:3, 2])
        if o1.ok:
            single.append(cam_error(o1.T_C_M, T))
        else:
            refused += 1
    joint, single = np.array(joint), np.array(single).reshape(-1, 2)
    assert joint[:, 0].max() < 0.002 and joint[:, 1].max() < 0.15, joint      # < 2 mm, < 0.15 deg
    # the single 52-px tag is either refused (ambiguous) or much worse
    assert refused >= 3 or np.median(single[:, 0]) > 4 * np.median(joint[:, 0])
    assert len(single) == 0 or np.median(single[:, 0]) > 4 * np.median(joint[:, 0])
    assert len(single) == 0 or np.median(single[:, 1]) > 4 * np.median(joint[:, 1])
    print(f"joint PnP @1.5 m: pos {np.median(joint[:, 0]) * 1e3:.2f} mm (max {joint[:, 0].max() * 1e3:.2f}), "
          f"rot {np.median(joint[:, 1]):.3f} deg (max {joint[:, 1].max():.3f}) | single tag: refused {refused}/12, "
          f"accepted frames {np.median(single[:, 0]) * 1e3:.1f} mm / {np.median(single[:, 1]):.2f} deg")


def test_edge_eff_is_span_of_used_tags():
    rng = np.random.default_rng(5)
    true = random_board(rng)
    tl = truth_layout(true)
    T = cam_above(1.5)
    o = BoardDetector(tl, CAM).detect(render_board_view(CAM, FAM, EDGE, true, T, rng=rng), up_in_cam=T[:3, 2])
    assert o.ok and o.edge_eff == pytest.approx(tl.extent_eff(o.used_ids)) and o.edge_eff > 0.9
    assert o.sigma_cam(CAM.fx, o.edge_eff)[2] < o.sigma_cam(CAM.fx, EDGE)[2] / 4     # depth noise model improves
    # one tag -> edge_eff None (perception falls back to edge_m)
    T1 = cam_above(0.5, 0.03, 0.0, 0.25, -0.2, 0.7)
    o1 = BoardDetector(FloorBoardLayout(EDGE), CAM).detect(render_board_view(CAM, FAM, EDGE, {0: (0, 0, 0)}, T1),
                                                           up_in_cam=T1[:3, 2])
    assert o1.ok and o1.edge_eff is None


@pytest.mark.parametrize("seed", range(10))
def test_only_tag0_matches_single_tag_detector(seed):
    rng = np.random.default_rng(seed)
    h = rng.uniform(0.25, 1.4)
    T = cam_above(h, *rng.uniform(-0.15, 0.15, 2) * h, *rng.uniform(-0.15, 0.15, 2), rng.uniform(-3, 3))
    img = render_marker_view(CAM, FAM, 0, EDGE, T, rng=rng, noise=2.0)
    ref = MarkerDetector(FAM, 0, EDGE, CAM).detect(img)
    got = BoardDetector(FloorBoardLayout(EDGE), CAM).detect(img)
    assert got.ok == ref.ok and got.reason == ref.reason
    assert got.edge_eff is None and got.used_ids == ([0] if got.ok or ref.corners is not None else [])
    if ref.ok:
        assert np.allclose(got.T_C_M, ref.T_C_M, atol=1e-9)
        assert got.rms_px == pytest.approx(ref.rms_px) and got.ambiguity_ratio == pytest.approx(ref.ambiguity_ratio)


def test_unsurveyed_neighbours_do_not_change_tag0_result():
    rng = np.random.default_rng(11)
    true = random_board(rng)
    T = cam_above(0.9, 0.05, -0.03, 0.04, -0.02, 0.5)
    img = render_board_view(CAM, FAM, EDGE, true, T, rng=rng, noise=1.0)
    ref = MarkerDetector(FAM, 0, EDGE, CAM).detect(img, up_in_cam=T[:3, 2])
    got = BoardDetector(FloorBoardLayout(EDGE), CAM).detect(img, up_in_cam=T[:3, 2])
    assert ref.ok and got.ok and np.allclose(got.T_C_M, ref.T_C_M, atol=1e-9)
    assert len(got.unsurveyed_ids) >= 2 and got.used_ids == [0]


def test_single_non_origin_tag_is_expressed_in_M():
    rng = np.random.default_rng(2)
    true = random_board(rng)
    lay = FloorBoardLayout(EDGE)
    lay.set_pose(5, *true[5])
    n_ok = 0
    for _ in range(30):
        h = rng.uniform(0.35, 0.6)
        T = cam_above(h, *(np.array(true[5][:2]) + rng.uniform(-0.04, 0.04, 2)), *rng.uniform(-0.3, 0.3, 2), 0.3)
        uv = CAM.project(lay.corners_M(5) @ T[:3, :3].T + T[:3, 3])
        if not np.all(CAM.in_image(uv, margin=10)):
            continue                                  # tag not fully in view
        img = render_board_view(CAM, FAM, EDGE, {5: true[5]}, T, rng=rng, noise=1.0)
        o = BoardDetector(lay, CAM).detect(img, up_in_cam=T[:3, 2])
        if not o.ok:                                  # near-frontal single tags are genuinely ambiguous: refusal is correct
            assert "ambiguous" in o.reason, o.reason
            continue
        n_ok += 1
        assert o.used_ids == [5] and o.edge_eff is None
        pos, rot = cam_error(o.T_C_M, T)
        assert pos < 0.004 + 0.01 * h and rot < 3.0, (pos, rot)
    assert n_ok >= 4


def test_small_and_border_tags_are_skipped_not_fatal():
    rng = np.random.default_rng(4)
    true = random_board(rng)
    tl = truth_layout(true)
    T = cam_above(1.5, 0.45, 0.2)                                    # part of the board runs out of the image
    img = render_board_view(CAM, FAM, EDGE, true, T, rng=rng)
    o = BoardDetector(tl, CAM).detect(img, up_in_cam=T[:3, 2])
    assert o.ok and 2 <= len(o.used_ids) < 9
    assert cam_error(o.T_C_M, T)[0] < 0.004
    far = cam_above(3.8)
    o = BoardDetector(tl, CAM).detect(render_board_view(CAM, FAM, EDGE, true, far), up_in_cam=far[:3, 2])
    assert not o.ok and o.reason


def test_moved_sheet_is_dropped_from_the_joint_solution():
    rng = np.random.default_rng(6)
    true = random_board(rng)
    tl = truth_layout(true)
    moved = dict(true)
    x, y, w = true[5]
    moved[5] = (x + 0.03, y - 0.02, w + 0.1)                         # the sheet was kicked
    T = cam_above(1.5, 0.05, 0.05, 0.02, -0.02, 1.0)
    img = render_board_view(CAM, FAM, EDGE, moved, T, rng=rng)
    o = BoardDetector(tl, CAM).detect(img, up_in_cam=T[:3, 2])
    assert o.ok and 5 not in o.used_ids and "inconsistent" in o.dropped.get(5, ""), (o.used_ids, o.dropped)
    assert cam_error(o.T_C_M, T)[0] < 0.002
    # a tag excluded by the survey is not used either
    o = BoardDetector(tl, CAM).detect(img, up_in_cam=T[:3, 2], exclude=[3])
    assert 3 not in o.used_ids and 3 in o.dropped


def test_duplicate_and_unexpected_ids_are_reported():
    rng = np.random.default_rng(7)
    true = random_board(rng)
    tl = truth_layout(true)
    T = cam_above(1.4)
    a = render_board_view(CAM, FAM, EDGE, {i: p for i, p in true.items() if i != 4}, T, rng=rng, noise=0)
    # a second sheet printed with id 6 (also on the floor) -> id 6 appears twice
    b = render_board_view(CAM, FAM, EDGE, {6: (true[4][0], true[4][1], true[4][2])}, T, rng=rng, noise=0)
    img = np.minimum(a, b)
    bd = BoardDetector(tl, CAM)
    dets, dups, unexpected = bd.detect_tags(img)
    assert dups == [6] and 6 not in dets
    o = bd.detect(img, up_in_cam=T[:3, 2])
    assert o.ok and 6 not in o.used_ids and "duplicate" in o.dropped[6] and o.duplicate_ids == [6]
    # an id outside the board (e.g. a stray tag) is ignored but reported
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    stray = cv2.aruco.generateImageMarker(d, 37, 80, borderBits=1)
    img2 = a.copy()
    img2[20:100, 20:100] = stray
    dets, dups, unexpected = bd.detect_tags(img2)
    assert unexpected == [37] and 37 not in dets


# ------------------------------------------------------------------- survey
@pytest.mark.parametrize("seed,gravity", [(100, False), (101, True)])
def test_survey_recovers_random_placements_from_noisy_corners(seed, gravity, tmp_path):
    rng = np.random.default_rng(seed)
    true = random_board(rng)
    tl = truth_layout(true)
    lay = FloorBoardLayout(EDGE)
    sv = BoardSurvey(lay, CAM)
    for _ in range(60):
        T = random_cam(rng)
        up = T[:3, 2] + rng.normal(0, 0.003, 3) if gravity else None      # IMU gravity, 3 mrad noise
        sv.add_detections(projected(tl, true, T, rng, sigma=0.3), up_in_cam=up)
    sv.finalize()
    assert lay.surveyed_ids() == list(range(9)), sv.problems()
    pos, yaw = pose_errors(lay, tl, range(1, 9))
    assert pos.max() < 1e-3 and yaw.max() < 0.2, (pos.max() * 1e3, yaw.max())
    for i in range(1, 9):                       # the reported sigma is honest (error within 4 sigma) and small
        t = lay.tags[i]
        assert t.sigma_xy_m < 1e-3 and pos[i - 1] < 4 * max(t.sigma_xy_m, 1e-4) * 1.5
        assert t.n_obs >= 15
    print(f"survey (corner noise 0.3 px, 60 frames, gravity={gravity}): max pos {pos.max() * 1e3:.2f} mm, "
          f"mean {pos.mean() * 1e3:.2f} mm, max yaw {yaw.max():.3f} deg")
    # the survey result drives the joint detector at the same accuracy
    T = random_cam(rng)
    o = BoardDetector(lay, CAM).pose_from_detections(projected(tl, true, T, rng), up_in_cam=T[:3, 2])
    assert o.ok and cam_error(o.T_C_M, T)[0] < 0.002
    lay.save(tmp_path / "b.json")
    assert FloorBoardLayout.load(tmp_path / "b.json").surveyed_ids() == list(range(9))


def test_survey_from_rendered_images_and_detector_corner_bias():
    """Full image path. cv2's sub-pixel refinement shrinks small tags by ~0.15 px per
    corner, which scales the layout by ~0.4 %: ~2-3 mm at 0.5 m with the default
    detector, removed by corner_inflate_px (a calibration constant)."""
    results = {}
    for inflate in (0.0, 0.155):
        rng = np.random.default_rng(0)
        true = random_board(rng)
        tl = truth_layout(true)
        lay = FloorBoardLayout(EDGE)
        sv = BoardSurvey(lay, CAM, detector=BoardDetector(lay, CAM, corner_inflate_px=inflate))
        for _ in range(40):
            T = random_cam(rng)
            sv.add_image(render_board_view(CAM, FAM, EDGE, true, T, rng=rng, noise=2.0))
        sv.finalize()
        assert lay.surveyed_ids() == list(range(9)), sv.problems()
        results[inflate] = pose_errors(lay, tl, range(1, 9))
    pos0, yaw0 = results[0.0]
    pos1, yaw1 = results[0.155]
    assert pos0.max() < 0.005 and yaw0.max() < 0.2          # default detector: scale bias only
    assert pos1.max() < 0.001 and yaw1.max() < 0.2          # bias removed
    assert np.mean(pos0) > 2 * np.mean(pos1)
    print(f"image survey, 40 frames: default detector max {pos0.max() * 1e3:.2f} mm / {yaw0.max():.3f} deg; "
          f"with corner_inflate_px=0.155 max {pos1.max() * 1e3:.2f} mm / {yaw1.max():.3f} deg")


def _survey(true, frames=30, *, seed=0, scale=None, move=None, dup_at=None, dup_id=None):
    rng = np.random.default_rng(seed)
    tl = truth_layout(true)
    lay = FloorBoardLayout(EDGE)
    sv = BoardSurvey(lay, CAM)
    for f in range(frames):
        if move and f == move[1]:
            x, y, w = true[move[0]]
            tl.set_pose(move[0], x + move[2], y, w)
        T = random_cam(rng)
        sv.add_detections(projected(tl, true, T, rng, scale=scale),
                          duplicate_ids=[dup_id] if dup_at == f else ())
    sv.finalize()
    return lay, sv


def test_survey_rejects_misscaled_sheet():
    true = random_board(np.random.default_rng(21))
    lay, sv = _survey(true, scale={3: 0.97})
    st = sv.status()
    assert not lay.is_surveyed(3) and st[3].state == "rejected" and "printed size" in st[3].reason
    assert abs(st[3].edge_ratio - 0.97) < 0.006, st[3].edge_ratio             # measured within 0.6 %
    assert sorted(set(lay.surveyed_ids()) | {3}) == list(range(9)), sv.problems()      # the rest is unaffected
    pos, _ = pose_errors(lay, truth_layout(true), [i for i in range(1, 9) if i != 3])
    assert pos.max() < 1.5e-3
    # 1 % is inside the tolerance; 2 % is not
    assert _survey(true, scale={3: 0.99})[0].is_surveyed(3)
    assert _survey(true, scale={3: 0.98})[1].status()[3].state == "rejected"


def test_survey_flags_origin_sheet_with_a_different_print_scale():
    true = random_board(np.random.default_rng(22))
    lay, sv = _survey(true, scale={0: 0.96})
    assert any("origin" in w for w in sv.warnings), sv.warnings
    assert abs(sv.status()[0].edge_ratio - 0.96) < 0.01


def test_survey_rejects_sheet_kicked_during_survey():
    true = random_board(np.random.default_rng(23))
    lay, sv = _survey(true, move=(5, 8, 0.03))
    st = sv.status()[5]
    assert not lay.is_surveyed(5) and st.state == "rejected" and "moved" in st.reason, st
    mm = float(re.search(r"moved ~(\d+) mm", st.reason).group(1))
    assert 20 <= mm <= 35, st.reason                       # true displacement: 30 mm
    assert sorted(set(lay.surveyed_ids()) | {5}) == list(range(9))
    # the user re-places it and the survey starts over for that tag
    sv.reset_tag(5)
    assert sv.status()[5].state == "unseen" and not lay.is_surveyed(5)


def test_survey_flags_sheet_kicked_after_it_was_surveyed():
    true = random_board(np.random.default_rng(24))
    lay, sv = _survey(true, frames=36, move=(5, 20, 0.02))
    st = sv.status()[5]
    assert st.state == "suspect" and "moved" in st.reason, st
    assert lay.is_surveyed(5)                          # old pose kept, but flagged and no longer trusted
    others = [i for i in range(1, 9) if i != 5]
    assert all(sv.status()[i].state == "surveyed" for i in others)
    # a flagged sheet is not used by later joint solves
    rng = np.random.default_rng(1)
    tl = truth_layout(true)
    T = random_cam(rng)
    o = BoardDetector(lay, CAM).pose_from_detections(projected(tl, true, T, rng), up_in_cam=T[:3, 2], exclude=[5])
    assert o.ok and 5 not in o.used_ids and cam_error(o.T_C_M, T)[0] < 0.002


def test_survey_rejects_duplicate_id():
    true = random_board(np.random.default_rng(25))
    lay, sv = _survey(true, frames=24, dup_at=4, dup_id=4)
    st = sv.status()[4]
    assert st.state == "rejected" and "duplicate" in st.reason and not lay.is_surveyed(4)
    assert sorted(set(lay.surveyed_ids()) | {4}) == list(range(9))


def test_survey_waits_for_enough_views_and_chains_through_surveyed_tags():
    """Tags only seen together with other (not yet surveyed) tags get placed once a
    neighbour is surveyed; a tag with too few views stays pending with the reason."""
    rng = np.random.default_rng(31)
    true = random_board(rng)
    tl = truth_layout(true)
    lay = FloorBoardLayout(EDGE)
    sv = BoardSurvey(lay, CAM)
    # near views: only the four axis neighbours (ids 2, 4, 5, 7) and tag 0 are in view
    for _ in range(22):
        T = cam_above(1.0, *rng.uniform(-0.1, 0.1, 2), *rng.uniform(-0.03, 0.03, 2), rng.uniform(-3, 3))
        sv.add_detections(projected(tl, [0, 2, 4, 5, 7], T, rng))
    assert {2, 4, 5, 7} <= set(lay.surveyed_ids()), sv.problems() or sv.status()
    # tag 8 appears only in 3 views: pending, with an explanation
    for _ in range(3):
        T = random_cam(rng)
        sv.add_detections(projected(tl, [0, 8], T, rng))
    st = sv.status()[8]
    assert st.state == "pending" and "views" in st.reason and not lay.is_surveyed(8)
    for _ in range(25):
        T = random_cam(rng)
        sv.add_detections(projected(tl, true, T, rng))
    sv.finalize()
    assert lay.surveyed_ids() == list(range(9)), sv.problems()
    pos, yaw = pose_errors(lay, tl, range(1, 9))
    assert pos.max() < 1.5e-3 and yaw.max() < 0.3


def test_survey_flags_origin_sheet_that_moved():
    """Tag 0 defines M; if it is kicked the others disagree with it and the frame is suspect."""
    rng = np.random.default_rng(5)
    true = random_board(rng)
    tl = truth_layout(true)
    lay = FloorBoardLayout(EDGE)
    sv = BoardSurvey(lay, CAM)
    for f in range(40):
        if f == 24:
            tl.tags[0].x = 0.03
        sv.add_detections(projected(tl, true, random_cam(rng), rng))
    sv.finalize()
    st = sv.status()[0]
    assert st.state == "suspect" and "origin" in st.reason, st
