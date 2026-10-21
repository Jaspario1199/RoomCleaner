"""
Acceptance checks for the Gripper 1021 printable parts (spec: cad/GRIPPER_1021_SPEC.md).

  HANDS    cad/parts/gripper1021_hands.py     (left + right coupler links of Jasper's four-bar)
  HOUSING  cad/parts/gripper1021_housing_cambay.py  (Jasper's electrical housing + the v6 camera bay, one part)

Everything is measured on the built BRep solids / exported files (probes, booleans, section rasters), with the
spec numbers as the expected values.  Jasper's reference parts are read-only (cad/reference/gripper_1021/parts).
"""

from __future__ import annotations

import importlib.util
import math
import os
import struct
import sys

import pytest

cq = pytest.importorskip("cadquery")

import numpy as np                                               # noqa: E402
from OCP.gp import gp_Pnt                                        # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier          # noqa: E402
from OCP.TopAbs import TopAbs_IN                                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import gripper1021_hands as H                     # noqa: E402

REF = os.path.join(REPO, "cad", "reference", "gripper_1021", "parts")
pytestmark = pytest.mark.skipif(not os.path.isdir(REF), reason="gripper_1021 reference parts not available")


def _load_build_module():
    spec = importlib.util.spec_from_file_location("build_gripper1021", os.path.join(REPO, "scripts", "build_gripper1021.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B = _load_build_module()
PETG = P.GRIP1021_PETG_G_CM3
SPEC_A_CLOSED = (994.879, 674.617)       # spec table, right hand, theta = -62
SPEC_B_CLOSED = (986.708, 640.923)
SPEC_A_FILE = (1002.554, 679.592)        # theta = -52.1 (Jasper's file pose)
SPEC_B_FILE = (994.481, 645.875)
AXIS_X = 951.8475


def inside(shape, x, y, z):
    c = BRepClass3d_SolidClassifier(shape.wrapped)
    c.Perform(gp_Pnt(x, y, z), 1e-7)
    return c.State() == TopAbs_IN


def mirror_pt(p):
    return (2 * AXIS_X - p[0], p[1])


@pytest.fixture(scope="module")
def hands():
    return H.make_hand_right(), H.make_hand_left()


@pytest.fixture(scope="module")
def jasper():
    parts = B.load_jasper()
    return parts, B.file_pose_angles(parts)


# ---------------------------------------------------------------------------------------------------------------
# hands
# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("side", ["R", "L"])
def test_hand_is_one_valid_solid(hands, side):
    wp = hands[0] if side == "R" else hands[1]
    assert wp.val().isValid()
    assert len(wp.solids().vals()) == 1
    assert len(wp.val().Solids()) == 1


@pytest.mark.parametrize("side", ["R", "L"])
def test_closed_pose_pin_hole_centres(hands, side):
    sh = (hands[0] if side == "R" else hands[1]).val()
    a, b = SPEC_A_CLOSED, SPEC_B_CLOSED
    if side == "L":
        a, b = mirror_pt(a), mirror_pt(b)
    axes = B.pin_hole_axes(sh)
    assert len(axes) == 2
    ha = min(axes, key=lambda c: math.dist(c, a))
    hb = min(axes, key=lambda c: math.dist(c, b))
    assert math.dist(ha, a) < 0.02, (ha, a)
    assert math.dist(hb, b) < 0.02, (hb, b)
    # coupler length
    assert abs(math.dist(ha, hb) - P.GRIP1021_COUPLER) < 0.02


@pytest.mark.parametrize("side", ["R", "L"])
def test_file_pose_pin_hole_centres(hands, side):
    wp = hands[0] if side == "R" else hands[1]
    sh = H.place_hand(wp, side, P.GRIP1021_THETA_FILE_DEG).val()
    a, b = SPEC_A_FILE, SPEC_B_FILE
    if side == "L":
        a, b = mirror_pt(a), mirror_pt(b)
    axes = B.pin_hole_axes(sh)
    assert math.dist(min(axes, key=lambda c: math.dist(c, a)), a) < 0.02
    assert math.dist(min(axes, key=lambda c: math.dist(c, b)), b) < 0.02


def test_exported_step_is_at_the_file_pose():
    for nm, side in (("right", "R"), ("left", "L")):
        path = os.path.join(REPO, "exports", "step", f"gripper1021_hand_{nm}.step")
        assert os.path.exists(path), "run scripts/build_gripper1021.py hands"
        sh = cq.importers.importStep(path).val()
        a, b = SPEC_A_FILE, SPEC_B_FILE
        if side == "L":
            a, b = mirror_pt(a), mirror_pt(b)
        axes = B.pin_hole_axes(sh)
        assert math.dist(min(axes, key=lambda c: math.dist(c, a)), a) < 0.02
        assert math.dist(min(axes, key=lambda c: math.dist(c, b)), b) < 0.02


def test_boss_tops(hands):
    for side, wp, a_top in (("R", hands[0], 1098.99), ("L", hands[1], 1099.99)):
        sh = wp.val()
        a, b = H.A_C, H.B_C
        if side == "L":
            a, b = mirror_pt(a), mirror_pt(b)
        ta, tb = B.boss_tops(sh, [a, b])
        assert abs(ta - a_top) < 0.001, (side, ta)
        assert abs(tb - 1101.49) < 0.001, (side, tb)


def test_z_planes_and_extents(hands):
    for side, wp in (("R", hands[0]), ("L", hands[1])):
        bb = wp.val().BoundingBox()
        assert abs(bb.zmin - 1090.0) < 0.001                  # bed face
        assert abs(bb.zmax - 1118.0) < 0.001                  # palm / finger top
        assert abs(bb.ymin - 575.0) < 1e-6                    # fingertip
        # plate top: probe just below / above 1098 over the plate between the pockets' ring (a point on the A ring)
        a = H.A_C if side == "R" else mirror_pt(H.A_C)
        px, py = a[0] + 6.0 * math.cos(H.HAND_DIR + math.pi / 2) * (1 if side == "R" else -1), a[1] + 6.0 * math.sin(H.HAND_DIR + math.pi / 2)
        assert inside(wp.val(), px, py, 1097.9) and not inside(wp.val(), px, py, 1098.1)


def test_grip_faces_meet_and_do_not_overlap(hands):
    hr = H.place_hand(hands[0], "R", P.GRIP1021_THETA_CLOSED_DEG).val()
    hl = H.place_hand(hands[1], "L", P.GRIP1021_THETA_CLOSED_DEG).val()
    # closed pose is the build pose: the placement must be the identity
    assert abs(hr.BoundingBox().xmin - AXIS_X) < 1e-6
    assert abs(hl.BoundingBox().xmax - AXIS_X) < 1e-6
    assert hr.intersect(hl).Volume() < 1e-6
    assert hr.distance(hl) < 1e-6                              # the crests touch


def test_keepout_above_the_plate_only_bosses(hands):
    """For y > 628.4, above the plate (z > 1098) only the two joint bosses (minus their pin holes) exist."""
    for side, wp, a_top in (("R", hands[0], 1098.99), ("L", hands[1], 1099.99)):
        box = cq.Workplane("XY").box(400, 400, 60, centered=False).translate((800, 628.4 + 1e-6, H.Z_PLATE + 1e-6))
        v = wp.val().intersect(box.val()).Volume()
        ring = lambda top: math.pi * (4.0 ** 2 - 1.6 ** 2) * (top - 1098.0)
        expect = ring(a_top) + ring(1101.49)
        assert abs(v - expect) < 1.0, (side, v, expect)
        # and the palm / finger never rise above y = 628.4 at z > 1098
        assert abs(wp.val().intersect(box.val()).BoundingBox().ymax - max(H.B_C[1], H.A_C[1])) < 5.0


@pytest.mark.parametrize("side", ["R", "L"])
def test_mass_within_spec(hands, side):
    sh = (hands[0] if side == "R" else hands[1]).val()
    mass = sh.Volume() * PETG / 1000.0
    assert mass <= P.GRIP1021_MASS_MAX_G, mass


@pytest.mark.parametrize("side", ["R", "L"])
def test_nut_pockets_hex_57_af_42_deep(hands, side):
    sh = (hands[0] if side == "R" else hands[1]).val()
    for c in ((H.A_C, H.B_C) if side == "R" else (mirror_pt(H.A_C), mirror_pt(H.B_C))):
        # direction across the link (vertices) and along it (flats)
        ux, uy = math.cos(H.HAND_DIR + math.pi / 2), math.sin(H.HAND_DIR + math.pi / 2)
        if side == "L":
            ux = -ux
        vx, vy = math.cos(H.HAND_DIR), math.sin(H.HAND_DIR)
        if side == "L":
            vx = -vx
        rc = 5.7 / math.sqrt(3.0)
        z_in, z_out = 1090.0 + 4.0, 1090.0 + 4.4
        # vertex direction: pocket reaches circumradius, just past it is solid
        assert not inside(sh, c[0] + (rc - 0.1) * ux, c[1] + (rc - 0.1) * uy, z_in)
        assert inside(sh, c[0] + (rc + 0.1) * ux, c[1] + (rc + 0.1) * uy, z_in)
        # flat direction: pocket reaches AF/2
        assert not inside(sh, c[0] + (2.85 - 0.05) * vx, c[1] + (2.85 - 0.05) * vy, z_in)
        assert inside(sh, c[0] + (2.85 + 0.05) * vx, c[1] + (2.85 + 0.05) * vy, z_in)
        # depth: void up to 4.2, solid above (take a point inside the hex but off the Ø3.2 hole)
        px, py = c[0] + 2.4 * ux, c[1] + 2.4 * uy
        assert not inside(sh, px, py, 1090.0 + 4.1)
        assert inside(sh, px, py, 1090.0 + 4.3)
        # Ø3.2 through hole
        assert not inside(sh, c[0] + 1.55 * vx, c[1] + 1.55 * vy, 1096.0)
        assert inside(sh, c[0] + 1.65 * vx, c[1] + 1.65 * vy, 1096.0)


def test_grip_ridges_cut_into_the_face(hands):
    """16 grooves, 0.8 deep, 3.0 pitch; no material proud of the plane x = AX (right hand)."""
    sh = hands[0].val()
    mid_z = 1110.0
    y0 = P.GRIP1021_RIDGE_Y0
    assert not inside(sh, AXIS_X - 0.01, 600.0, mid_z)              # nothing proud of the face
    for k in range(P.GRIP1021_RIDGE_N):
        y_groove = y0 + k * 3.0 + 1.1                              # groove centre line
        y_crest = y_groove + 1.5
        assert not inside(sh, AXIS_X + 0.75, y_groove, mid_z)      # groove open at 0.75 depth
        assert inside(sh, AXIS_X + 0.85, y_groove, mid_z)          # root at 0.8
        assert inside(sh, AXIS_X + 0.02, y_crest, mid_z)           # crest land is at the face
    left = hands[1].val()
    assert not inside(left, AXIS_X + 0.01, 600.0, mid_z)
    assert not inside(left, AXIS_X - 0.75, y0 + 1.1, mid_z)


def test_fingertip_round_and_wedge(hands):
    sh = hands[0].val()
    z = 1110.0
    # R3 round on the grip-face bottom edge: the corner (AX, 575) is cut away, the arc point is on the surface
    assert not inside(sh, AXIS_X + 0.2, 575.2, z)
    c = (AXIS_X + 3.0, 578.0)
    on_arc = (c[0] - 3.0 * math.cos(math.radians(45)), c[1] - 3.0 * math.sin(math.radians(45)))
    assert inside(sh, on_arc[0] + 0.05, on_arc[1] + 0.05, z) and not inside(sh, on_arc[0] - 0.05, on_arc[1] - 0.05, z)
    # 30 deg wedge on the outer bottom edge: outer-bottom corner is removed, the chamfer line passes (AX+3, 575) -> (AX+9, 578.46)
    assert not inside(sh, AXIS_X + 8.8, 575.5, z)
    y_line = 575.0 + (AXIS_X + 8.0 - (AXIS_X + 3.0)) * math.tan(math.radians(30.0))
    assert inside(sh, AXIS_X + 8.0, y_line + 0.05, z) and not inside(sh, AXIS_X + 8.0, y_line - 0.05, z)


@pytest.mark.parametrize("side", ["R", "L"])
def test_wall_thickness_at_least_3mm(hands, side):
    """Every through-window keeps >= 3.0 mm to the outside (measured from the nominal grip face, ridge grooves
    excluded) and to the other windows / nut pockets; the true minimum (groove root) is >= 2.2."""
    sh = (hands[0] if side == "R" else hands[1]).val()
    tol = 0.06
    for z, fill in ((1110.0, True), (1092.0, True), (1096.0, True)):
        for w in B.wall_report(sh, z, fill_ridges=fill, side=side):
            assert w["min_wall_to_outside"] >= P.GRIP1021_WALL_MIN - tol, (z, w)
            if w["min_wall_to_other_void"] is not None:
                assert w["min_wall_to_other_void"] >= P.GRIP1021_WALL_MIN - tol, (z, w)
    for w in B.wall_report(sh, 1110.0, fill_ridges=False, side=side):
        assert w["min_wall_to_outside"] >= P.GRIP1021_WALL_MIN - P.GRIP1021_RIDGE_DEPTH - tol, w


def test_step_reimport_agrees(hands):
    for nm, wp, side in (("right", hands[0], "R"), ("left", hands[1], "L")):
        path = os.path.join(REPO, "exports", "step", f"gripper1021_hand_{nm}.step")
        ref = H.place_hand(wp, side, P.GRIP1021_THETA_FILE_DEG).val()
        d = B.reimport_check(path, ref)
        assert d["solids"] == 1 and d["valid"]
        assert d["vol_rel_diff"] < 1e-6
        assert d["bbox_max_diff_mm"] < 1e-3


def _read_stl(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    assert 84 + 50 * n == len(data), "binary STL expected"
    arr = np.frombuffer(data[84:], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n)
    return arr["v"].reshape(-1, 3)


def test_stl_in_print_orientation(hands):
    for nm, wp in (("right", hands[0]), ("left", hands[1])):
        path = os.path.join(REPO, "exports", "stl", f"gripper1021_hand_{nm}.stl")
        assert os.path.exists(path), "run scripts/build_gripper1021.py hands"
        v = _read_stl(path)
        lo, hi = v.min(axis=0), v.max(axis=0)
        bb = wp.val().BoundingBox()
        assert abs(lo[2]) < 1e-3                                   # bed face on z = 0
        assert np.allclose(hi - lo, [bb.xlen, bb.ylen, bb.zlen], atol=0.02)
        # almost all downward-facing area lies on the bed plane (flat bed face; only the nut-pocket roofs are higher)
        tri = v.reshape(-1, 3, 3)
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        area = 0.5 * np.linalg.norm(nrm, axis=1)
        down = nrm[:, 2] < -0.5 * np.linalg.norm(nrm, axis=1)     # genuinely downward-facing (not vertical walls)
        on_bed = down & (np.abs(tri[:, :, 2] - lo[2]).max(axis=1) < 1e-3)
        assert area[on_bed].sum() > 0.9 * area[down].sum(), (area[on_bed].sum(), area[down].sum())


def test_pin_axes_coincide_with_jasper_holes_at_the_file_pose(hands, jasper):
    """At the file pose the hand pin holes sit within 0.1 mm of Jasper's holes (his file is not exactly
    four-bar-consistent: 0.04 / 0.06 mm); the M3 clearance is 0.15 mm per side."""
    parts, fp = jasper
    r = H.place_hand(hands[0], "R", P.GRIP1021_THETA_FILE_DEG).val()
    axes = B.pin_hole_axes(r)
    assert min(math.dist(a, fp["crank_xy"]) for a in axes) < 0.1
    assert min(math.dist(a, fp["armR_xy"]) for a in axes) < 0.1


def test_sweep_has_zero_overlap(hands, jasper):
    """Both hands vs every Jasper part moved by the four-bar, theta = -5, -10, -20 ... -60, -62, plus each other."""
    parts, fp = jasper
    rows = B.sweep(hands[0], hands[1], P.GRIP1021_SWEEP_DEG, parts, fp)
    assert [r["theta_deg"] for r in rows] == list(P.GRIP1021_SWEEP_DEG)
    worst = 0.0
    for r in rows:
        worst = max(worst, r["R_vs_L"], *r["R"].values(), *r["L"].values())
    assert worst < 1e-3, B.sweep_summary(rows)


def test_sweep_control_detects_a_collision(hands, jasper):
    """Control: the same check must flag a hand pushed 5 mm up in z into the crank and arm (so 0 is not vacuous)."""
    parts, fp = jasper
    moved = B.jasper_at(parts, fp, -30.0)
    hr = H.place_hand(hands[0], "R", -30.0).val().translate(cq.Vector(0, 0, 5.0))
    assert B.overlap_volume(hr, moved["compound"]) > 10.0
    assert B.overlap_volume(hr, moved["arm_R"]) > 10.0


# ---------------------------------------------------------------------------------------------------------------
# housing + camera bay
# ---------------------------------------------------------------------------------------------------------------
from cad.parts import gripper1021_housing_cambay as G          # noqa: E402
from cad.parts import claw_camera_bay as V6                    # noqa: E402

BAY_ORIGIN = (951.8475, 1091.1905, 1103.9899)


@pytest.fixture(scope="module")
def housing():
    orig = G.load_housing_bay_frame()
    hb, cv = G.make()
    return orig, hb, cv


def test_existing_cambay_values_unchanged():
    """The v6 bay stays reproducible: spot-check the CAMBAY_* values that the 1021 block must not touch."""
    assert P.CAMBAY_BOX_FLANGE_HALF == 63.5 and P.CAMBAY_BOX_BLEND_TOP_Y == 39.68 and P.CAMBAY_BOX_TOP_Y == 81.2
    assert P.CAMBAY_CAM_R == 90.0 and P.CAMBAY_SIDE == -1 and P.CAMBAY_CORNER_HOLE_D == 1.5
    assert P.CAMBAY_WALL == 2.0 and P.CAMBAY_FLOOR_T == 2.4 and P.CAMBAY_RIB_SPAN_X == 34.0


def test_housing_is_one_valid_solid(housing):
    orig, hb, cv = housing
    for wp in (hb, cv):
        assert wp.val().isValid() and len(wp.solids().vals()) == 1


def test_only_the_wire_window_is_removed_and_the_pocket_is_untouched(housing):
    orig, hb, cv = housing
    o, c = orig.val(), hb.val()
    removed = o.cut(c)
    win = G.wire_window_cutter().val()
    assert removed.cut(win).Volume() < 1e-3                          # nothing removed outside the wire window
    assert 300.0 < removed.Volume() < 800.0                          # and the window is there (526.6 mm3)
    pocket = cq.Solid.makeBox(80, 50, 80, cq.Vector(-40, 5, -40))
    assert c.cut(o).intersect(pocket).Volume() < 1e-3                # nothing added in the pocket
    assert removed.intersect(pocket).Volume() < 1e-3                 # nothing removed in the pocket
    # the wire window is the only region of the original wall that changed: probes in the pocket, floor, lid seat
    for (x, y, z, want) in ((0.0, 30.0, 0.0, False), (10.0, 4.0, -20.0, True), (0.0, 2.0, 0.0, False),
                            (43.0, 52.0, 0.0, True), (0.0, 20.0, -42.0, True), (0.0, 15.5, -43.0, False)):
        assert inside(c, x, y, z) == want, (x, y, z)


def test_bottom_plane_is_flat_and_nothing_below(housing):
    orig, hb, cv = housing
    c = hb.val()
    assert abs(c.BoundingBox().ymin) < 1e-5
    faces = [f for f in c.Faces() if f.geomType() == "PLANE" and f.normalAt().y < -0.999 and abs(f.BoundingBox().ymin) < 1e-5]
    assert len(faces) >= 1
    # the bay floor (x +-31, r 42.5..101.3) lies in the same plane as the housing base: both at y = 0
    assert sum(f.Area() for f in faces) > 0.95 * (8881.35 + 1500.0 - 232.5)      # housing base + bay floor, one plane
    for f in c.Faces():
        if f.geomType() == "PLANE" and f.normalAt().y < -0.999:
            assert abs(f.BoundingBox().ymin) < 1e-5 or f.BoundingBox().ymin > 4.9      # y = 0 or the 5 mm pocket-floor level


def test_lens_position_matches_the_spec_and_v6():
    lens = G.LENS_CENTER_WORLD
    assert lens == tuple(a + b for a, b in zip(V6.LENS_CENTER_BAY, V6.BAY_ORIGIN_WORLD))
    assert abs(lens[0] - 956.60) < 0.01 and abs(lens[2] - 1013.99) < 0.01
    assert abs(lens[1] - 1091.19 - 1.9) < 0.01                       # glass 1.9 mm above the bed plane
    assert abs(math.hypot(0.0, lens[2] - 1103.9899) - 90.0) < 1e-6   # optical axis at r = 90 from the tube axis


def test_lens_window_is_open_at_the_lens_and_closed_around_it(housing):
    orig, hb, cv = housing
    c = hb.val()
    zc = -90.0
    assert not inside(c, G.LENS_X, 1.0, zc) and not inside(c, G.LENS_X, 8.0, zc)       # tunnel through floor + block
    assert not inside(c, G.WIN_X0 + 0.1, 1.0, zc) and not inside(c, G.WIN_X1 - 0.1, 1.0, zc)
    assert inside(c, G.WIN_X0 - 1.6, 1.0, zc) and inside(c, G.LENS_X, 1.0, zc - 8.2 - 1.6)  # wall outside the chamfer
    assert inside(c, -8.0, 1.0, zc)                                                        # solid on the -X side of the window


def test_bay_head_and_cover_are_identical_to_the_verified_v6_bay():
    far = cq.Solid.makeBox(60, 40, 32, cq.Vector(-30, -1, -110))          # r >= 78
    a, b = G.make_bay_body().val().intersect(far), V6.make_bay_body().val().intersect(far)
    assert a.Volume() > 5000.0
    assert a.cut(b).Volume() + b.cut(a).Volume() < 1e-3
    far2 = cq.Solid.makeBox(60, 40, 45, cq.Vector(-30, -1, -110))         # r >= 65
    a, b = G.make_cover().val().intersect(far2), V6.make_cover().val().intersect(far2)
    assert a.cut(b).Volume() + b.cut(a).Volume() < 1e-3


def test_bay_is_five_mm_from_the_corner_cable_holes(housing):
    orig, hb, cv = housing
    c, o = hb.val(), orig.val()
    holes = B.hole_cylinders(G)
    added = c.cut(o)
    for h in holes:
        assert added.distance(h) >= P.CAMBAY1021_CORNER_HOLE_KEEPOUT + 5.0     # >= 10 mm measured (11.7)
        assert cv.val().distance(h) >= P.CAMBAY1021_CORNER_HOLE_KEEPOUT
    # the four Ø2 holes are still open through the wall (Jasper's geometry untouched)
    el = math.radians(P.CAMBAY1021_CORNER_HOLE_ELEV_DEG)
    for sx in (1, -1):
        for sz in (1, -1):
            for t in (2.0, 5.0, 8.0):
                x = P.CAMBAY1021_CORNER_HOLE_INNER_XZ + t * math.cos(el) / math.sqrt(2)
                y = P.CAMBAY1021_CORNER_HOLE_INNER_Y + t * math.sin(el)
                assert not inside(c, sx * x, y, sz * x), (sx, sz, t)
    # the keep-out numbers the module asserts
    assert G.BAY_MAX_X + P.CAMBAY1021_CORNER_HOLE_KEEPOUT < P.CAMBAY1021_CORNER_HOLE_EXIT_XZ


def test_bay_starts_inside_the_wall_and_walls_are_at_least_2mm(housing):
    orig, hb, cv = housing
    hp = G.housing_to_print(hb).val()
    cp = G.cover_to_print(cv).val()
    for z in (2.6, 9.8, 12.0, 17.9, 24.0):
        assert B.thin_features(hp, z, region=(-25, 25, 47, 110)) == [], z
    assert B.thin_features(cp, 2.9, region=(-30, 30, -10, 120)) == []
    assert B.thin_features(cp, 1.2, region=(-30, 30, -10, 120)) == []


def test_wire_window_gives_a_straight_wire_path_from_the_pocket_to_the_cradle(housing):
    orig, hb, cv = housing
    c = hb.val()
    for r in range(38, 96, 2):                                   # x = 0, window height: pocket -> wall -> neck -> fence gap -> cradle
        assert not inside(c, 0.0, G.WIN_Y, -r), r
    assert inside(c, 0.0, G.WIN_Y, -101.0)                       # end wall closes it


def test_cover_seats_flush_and_is_a_separate_part(housing):
    orig, hb, cv = housing
    assert cv.val().intersect(hb.val()).Volume() < 1e-3
    cb = cv.val().BoundingBox()
    assert abs(cb.ymax - G.Y_TOP) < 1e-6 and abs(cb.ymin - (G.Y_BOARD0 + P.CAMBAY_PEG_STOP_ABOVE_SEAT)) < 1e-6
    assert abs(cb.zmax + G.COVER_R0) < 1e-6                      # inner edge 0.8 mm off the box wall
    assert 0.5 < G.COVER_R0 - G.box_wall_r(G.Y_TOP) < 1.0
    for nm in ("gripper1021_housing_cambay", "gripper1021_housing_cambay_cover"):
        for sub, ext in (("step", "step"), ("stl", "stl")):
            assert os.path.exists(os.path.join(REPO, "exports", sub, f"{nm}.{ext}")), nm


def test_housing_step_reimport_agrees(housing):
    orig, hb, cv = housing
    for nm, wp in (("gripper1021_housing_cambay", hb), ("gripper1021_housing_cambay_cover", cv)):
        d = B.reimport_check(os.path.join(REPO, "exports", "step", nm + ".step"), G.to_world(wp.val()))
        assert d["solids"] == 1 and d["valid"]
        assert d["vol_rel_diff"] < 1e-6 and d["bbox_max_diff_mm"] < 1e-3
    # world frame: the housing STEP drops into Jasper's assembly at the origin (same bbox as his housing + the bay)
    re = cq.importers.importStep(os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay.step")).val().BoundingBox()
    jb = cq.importers.importStep(os.path.join(REF, "05_Gripper_Electric_Housing_Base_2__NAUO5.step")).val().BoundingBox()
    assert abs(re.xmin - jb.xmin) < 1e-3 and abs(re.xmax - jb.xmax) < 1e-3 and abs(re.ymin - jb.ymin) < 1e-3
    assert abs(re.ymax - jb.ymax) < 1e-3 and abs(re.zmax - jb.zmax) < 1e-3 and re.zmin < jb.zmin - 40.0   # bay sticks out on -Z


def test_housing_stl_in_print_orientation():
    v = _read_stl(os.path.join(REPO, "exports", "stl", "gripper1021_housing_cambay.stl"))
    lo, hi = v.min(axis=0), v.max(axis=0)
    assert abs(lo[2]) < 1e-3 and abs(hi[2] - 55.0) < 1e-2                         # bottom plane on the bed, top at 55
    assert abs(lo[0] + 50.0) < 1e-2 and abs(hi[0] - 50.0) < 1e-2
    assert abs(lo[1] + 50.0) < 1e-2 and abs(hi[1] - 101.3) < 1e-2                 # bay toward +y, 101.3 from the tube axis
    vc = _read_stl(os.path.join(REPO, "exports", "stl", "gripper1021_housing_cambay_cover.stl"))
    assert abs(vc[:, 2].min()) < 1e-3
    tri = vc.reshape(-1, 3, 3)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    on_bed = (nrm[:, 2] < 0) & (np.abs(tri[:, :, 2]).max(axis=1) < 1e-3)
    assert area[on_bed].sum() > 0.9 * area[nrm[:, 2] < -0.5 * np.linalg.norm(nrm, axis=1)].sum()   # flat outer face down


def test_housing_and_cover_do_not_touch_jasper_parts(housing, jasper):
    orig, hb, cv = housing
    parts, fp = jasper
    hw, cw = G.to_world(hb.val()), G.to_world(cv.val())
    for k, shp in parts.items():
        if k == "elec_housing":
            continue
        assert B.overlap_volume(hw, shp) < 0.01, k      # (0.0024 mm3 with the cylinder = 12 nm mating offset in Jasper's file)
        assert B.overlap_volume(cw, shp) < 0.01, k


def test_masses(housing):
    orig, hb, cv = housing
    bay_g = (hb.val().Volume() - orig.val().Volume()) * PETG / 1000.0
    cover_g = cv.val().Volume() * PETG / 1000.0
    assert bay_g + cover_g <= 30.0                      # the v6 bay + cover target
    assert 150.0 < hb.val().Volume() * PETG / 1000.0 < 250.0


def test_cable_lines_clear_the_bay_within_15_deg_yaw():
    r = B.cable_line_analysis(verbose=False, yaws_deg=[0.0, 15.0, -15.0])
    assert r["hits_pm15deg"] == 0 and r["total_lines_hitting_bay"] == 0
    assert r["nominal_yaw0_min_clearance_mm"] > 10.0 and r["yaw_pm15_min_clearance_mm"] > 10.0
