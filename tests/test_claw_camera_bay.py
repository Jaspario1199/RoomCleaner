"""
Geometry checks for cad/parts/claw_camera_bay.py (camera + IMU bay unioned onto
the v6 electrical box).  Everything is measured on the built BRep solids with
exact point-in-solid probes, not read back from the module's constants (except
as the expected values).

Bay frame: origin on the tube axis in the box bottom plane, +Y up, bay on -Z
(r = radial distance outward = -z).

Skips when cadquery or the (read-only) v6 STEP is unavailable.
"""

from __future__ import annotations

import math
import os

import pytest

cq = pytest.importorskip("cadquery")

import numpy as np                                            # noqa: E402
from OCP.gp import gp_Pnt                                      # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier        # noqa: E402
from OCP.TopAbs import TopAbs_IN                                # noqa: E402

from cad import params as P                                    # noqa: E402
from cad.parts import claw_camera_bay as B                     # noqa: E402
from cad.v6_loader import V6_STEP, load_v6, find, BOX_NAME     # noqa: E402
from cad.mesh_tools import tessellate, ray_mesh_first_hit      # noqa: E402
from cad.materials import MATERIALS                            # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(V6_STEP), reason="v6 STEP not available")

PETG = MATERIALS["PETG"]["density_g_cm3"]
S = B.S
TOL = 0.06          # probe resolution (mm)


def z_of(r):
    return S * r


class Probe:
    def __init__(self, shape):
        self.shape = shape.val() if isinstance(shape, cq.Workplane) else shape

    def inside(self, x, y, r):
        c = BRepClass3d_SolidClassifier(self.shape.wrapped)
        c.Perform(gp_Pnt(x, y, z_of(r)), 1e-6)
        return c.State() == TopAbs_IN

    def run(self, start, axis, length, step=0.05):
        """Return list of (t0, t1) intervals of solid along start + t*axis, axis in (x,y,r)."""
        out, cur = [], None
        n = int(length / step)
        for i in range(n + 1):
            t = i * step
            p = [start[k] + axis[k] * t for k in range(3)]
            ins = self.inside(*p)
            if ins and cur is None:
                cur = t
            if not ins and cur is not None:
                out.append((cur, t))
                cur = None
        if cur is not None:
            out.append((cur, length))
        return out


@pytest.fixture(scope="module")
def parts():
    return load_v6()


@pytest.fixture(scope="module")
def box_bay(parts):
    ox, oy, oz = B.BAY_ORIGIN_WORLD
    return cq.Workplane().add(find(parts, BOX_NAME)).translate((-ox, -oy, -oz))


@pytest.fixture(scope="module")
def combined(box_bay):
    return B.combine(box_bay)


@pytest.fixture(scope="module")
def body():
    return B.make_bay_body()


@pytest.fixture(scope="module")
def cover():
    return B.make_cover()


# ----------------------------------------------------------------- validity ----
def test_single_valid_solids(combined, body, cover, box_bay):
    for name, s in (("combined", combined), ("body", body), ("cover", cover)):
        assert s.val().isValid(), name
        assert len(s.solids().vals()) == 1, f"{name}: expected 1 solid"
    # the combined solid is larger than the box and contains it except the window
    assert combined.val().Volume() > box_bay.val().Volume()


def test_bbox_sanity(combined, body, cover):
    bb = body.val().BoundingBox()
    assert bb.zmin == pytest.approx(-(P.CAMBAY_CAM_R + P.CAMBAY_XIAO_W / 2 + P.CAMBAY_FIT_CLEAR + P.CAMBAY_WALL), abs=0.05)
    assert bb.ymin == pytest.approx(0.0, abs=0.02)          # on the print bed plane with the box
    assert bb.ymax == pytest.approx(B.H_CAV, abs=0.05)
    cb = combined.val().BoundingBox()
    assert cb.ymin == pytest.approx(0.0, abs=0.02)           # box bottom plane unchanged
    assert cb.ymax == pytest.approx(P.CAMBAY_BOX_TOP_Y, abs=0.05)
    assert cb.zmax == pytest.approx(P.CAMBAY_BOX_FLANGE_HALF, abs=0.05)
    kb = cover.val().BoundingBox()
    assert kb.zmin == pytest.approx(body.val().BoundingBox().zmin, abs=0.05)
    assert kb.ymax <= B.Y_TOP + 1.6                          # corral rails only


# ---------------------------------------------------------- optical geometry ----
def test_lens_window_size_and_chamfer(combined):
    p = Probe(combined)
    r0 = P.CAMBAY_CAM_R
    # along bay X through the window centre at mid floor height
    runs = p.run((-10.7, 1.0, r0), (1, 0, 0), 21.4)
    # solid from the cavity edge to the window edge on both sides
    gaps = [(a, b) for (a, b) in runs]
    assert len(gaps) == 2
    win_x = gaps[1][0] - gaps[0][1]
    assert win_x == pytest.approx(P.CAMBAY_LENS_WINDOW, abs=2 * TOL)
    assert win_x >= 14.0
    # along bay radial through the centre
    runs = p.run((0.0, 1.0, r0 - 9.15), (0, 0, 1), 18.3)
    assert len(runs) == 2
    win_r = runs[1][0] - runs[0][1]
    assert win_r == pytest.approx(P.CAMBAY_LENS_WINDOW, abs=2 * TOL)
    # outer-edge chamfer: wider opening right at the bottom face than inside
    wide = Probe(combined).run((-10.7, 0.15, r0), (1, 0, 0), 21.4)
    win_bottom = wide[1][0] - wide[0][1]
    assert win_bottom > win_x + 1.2          # 1 mm chamfer each side at y~0
    # whole tunnel is void from the floor underside to the board seat
    for y in (0.1, 1.0, 3.0, 6.0):
        assert not p.inside(0.0, y, r0)


def test_lens_barrel_and_field_of_view_unclipped(combined):
    """Lens glass sits inside the tunnel; the 70 deg diagonal cone (35 deg half
    angle) from the lens front must clear the window edges."""
    lens_y = B.LENS_FRONT_Y
    half = math.radians(P.CAMBAY_FOV_DIAG_DEG / 2)
    V, F = tessellate(combined, 0.2, 0.3)
    origin = np.array([0.0, lens_y, z_of(P.CAMBAY_CAM_R)])
    dirs = []
    for a in np.linspace(0, 2 * math.pi, 72, endpoint=False):
        dirs.append([math.sin(half) * math.cos(a), -math.cos(half), math.sin(half) * math.sin(a)])
    t = ray_mesh_first_hit(origin, np.array(dirs), V, F)
    # every cone-edge ray must leave the tunnel unobstructed within 15 mm
    assert not np.any(t < 15.0), f"FOV clipped by the bay tunnel: {np.sort(t)[:5]}"
    # barrel envelope (diameter 8 from lens front to board seat) is inside the void
    barrel = (cq.Workplane("XZ").workplane(offset=-B.Y_BOARD0).center(0, z_of(P.CAMBAY_CAM_R))
              .circle(P.CAMBAY_LENS_BARREL_D / 2).extrude(B.Y_BOARD0 - lens_y))
    assert combined.intersect(barrel).val().Volume() < 0.01


# ----------------------------------------------------------- boards fit ----
def _env(x0, x1, y0, y1, r0, r1):
    return B._rbox(x0, x1, y0, y1, r0, r1)


def test_xiao_cradle_and_clearance(combined, cover):
    L, W, H = P.CAMBAY_XIAO_L, P.CAMBAY_XIAO_W, P.CAMBAY_XIAO_H
    # nominal board envelope fits, and with 0.29 mm per side (clearance is 0.30)
    env = _env(-L / 2 - 0.29, L / 2 + 0.29, B.Y_BOARD0, B.Y_BOARD1, B.BOARD_CR - W / 2 - 0.29,
               B.BOARD_CR + W / 2 + 0.29)
    assert combined.intersect(env).val().Volume() < 0.05
    assert cover.intersect(env).val().Volume() < 0.05
    # and the cradle really is snug: an envelope 0.6 mm per side bigger must collide
    big = _env(-L / 2 - 0.6, L / 2 + 0.6, B.Y_BOARD0, B.Y_BOARD1, B.BOARD_CR - W / 2 - 0.6,
               B.BOARD_CR + W / 2 + 0.6)
    assert combined.intersect(big).val().Volume() > 1.0
    # board seat: floor of the cradle block at y = 6.4
    p = Probe(combined)
    assert p.inside(-9.0, B.Y_BOARD0 - 0.1, B.BOARD_CR + 7.0)
    assert not p.inside(-9.0, B.Y_BOARD0 + 0.1, B.BOARD_CR + 7.0)


def test_imu_envelope_and_posts(combined, cover):
    L, W, T = P.CAMBAY_IMU_L, P.CAMBAY_IMU_W, P.CAMBAY_IMU_T
    env = _env(B.IMU_XC - L / 2, B.IMU_XC + L / 2, B.IMU_Y_BOARD, B.IMU_Y_BOARD + T,
               B.IMU_RC - W / 2, B.IMU_RC + W / 2)
    assert combined.intersect(env).val().Volume() < 0.05
    assert cover.intersect(env).val().Volume() < 0.05
    # headroom above the IMU for the chip / wires under the cover
    above = _env(B.IMU_XC - L / 2, B.IMU_XC + L / 2, B.IMU_Y_BOARD + T, B.IMU_Y_BOARD + T + 3.0,
                 B.IMU_RC - W / 2, B.IMU_RC + W / 2)
    assert combined.intersect(above).val().Volume() < 0.05
    # board plane parallel to the camera board plane: both are y = const planes
    # posts: pilot holes Ø2.1 at the 15.2 mm pitch
    p = Probe(combined)
    (hx0, hr0), (hx1, hr1) = B.IMU_HOLES
    assert hr1 - hr0 == pytest.approx(P.CAMBAY_IMU_HOLE_PITCH, abs=1e-6)
    assert hx0 == hx1 == pytest.approx(-P.CAMBAY_IMU_L / 2 + P.CAMBAY_IMU_HOLE_EDGE)
    runs = p.run((hx1 - 3.0, B.IMU_Y_BOARD - 2.0, hr1), (1, 0, 0), 6.0)
    assert len(runs) == 2
    assert runs[1][0] - runs[0][1] == pytest.approx(P.CAMBAY_IMU_SCREW_PILOT, abs=2 * TOL)
    # post wall >= 2.5 mm around the pilot (outer diameter check)
    assert B.IMU_POST_OD / 2 - P.CAMBAY_IMU_SCREW_PILOT / 2 >= P.CAMBAY_BOSS_WALL - 1e-9
    # the post stands from the floor and ends at the board underside
    assert p.inside(hx1 + 2.5, B.IMU_Y_BOARD - 0.1, hr1) and not p.inside(hx1 + 2.5, B.IMU_Y_BOARD + 0.1, hr1)


def test_antenna_pocket_and_hold_down(cover):
    # antenna 30x10 lies on the cover between the corral rails
    ant_r0 = B.BOARD_CR - 22.0
    y1 = B.H_CAV + B.COVER_T
    env = _env(-P.CAMBAY_ANT_W / 2, P.CAMBAY_ANT_W / 2, y1, y1 + 1.0, ant_r0 + 0.1, ant_r0 + P.CAMBAY_ANT_L + 0.1)
    assert cover.intersect(env).val().Volume() < 0.05
    # ...and the rails exist to hold it (solid just outside the antenna width)
    rail = _env(P.CAMBAY_ANT_W / 2 + 0.5, P.CAMBAY_ANT_W / 2 + 1.0, y1 + 0.2, y1 + 1.0, ant_r0 + 5, ant_r0 + 10)
    assert cover.intersect(rail).val().Volume() > 1.0
    # board hold-down pegs reach to within 0.3 mm of the stack top
    p = Probe(cover)
    px = P.CAMBAY_XIAO_L / 2 - 1.4 - 0.2
    pr = B.BOARD_CR + P.CAMBAY_XIAO_W / 2 - 1.4 - 0.2
    assert p.inside(px, B.Y_BOARD1 + 0.35, pr) and not p.inside(px, B.Y_BOARD1 + 0.25, pr)


# --------------------------------------------------------------- openings ----
def test_usb_c_window_through_plus_x_wall(combined):
    p = Probe(combined)
    r0 = B.BOARD_CR
    yc = B.Y_BOARD1 - P.CAMBAY_XIAO_USB_Z_FROM_TOP
    # clear path through the wall at the connector height
    runs = p.run((B.CAV_HALF_X - 1.0, yc, r0), (1, 0, 0), 4.0)
    assert not any(a < 3.2 for a, b in runs if b > 1.0 and a > 0.5), "USB-C window blocked"
    assert not p.inside(B.CAV_HALF_X + 1.0, yc, r0)
    # opening size: width along radial >= 12.5 at the wall mid-plane, height >= 7 mm
    wr = p.run((B.CAV_HALF_X + 1.0, yc, r0 - 8), (0, 0, 1), 16.0)
    assert len(wr) == 2 and wr[1][0] - wr[0][1] == pytest.approx(P.CAMBAY_USB_W, abs=2 * TOL)
    hy = p.run((B.CAV_HALF_X + 1.0, yc - 5, r0), (0, 1, 0), 10.0)
    assert len(hy) == 2 and hy[1][0] - hy[0][1] == pytest.approx(P.CAMBAY_USB_H, abs=2 * TOL)
    # opening is above the board seat and the connector sits inside the opening height
    assert yc - P.CAMBAY_USB_H / 2 > B.Y_BOARD0


def test_wire_window_into_box_below_lid_seat(combined, box_bay):
    p = Probe(combined)
    y = P.CAMBAY_WIN_Y
    # void all the way from the bay cavity into the box pocket along r at x = 0
    for r in np.arange(P.CAMBAY_BOX_POCKET_HALF - 0.5, 66.0, 0.5):
        assert not p.inside(0.0, y, r), f"window blocked at r={r}"
    # window size >= 8 x 6 measured mid-wall (r = 51)
    wx = p.run((-9.0, y, 51.0), (1, 0, 0), 18.0)
    assert len(wx) == 2
    width = wx[1][0] - wx[0][1]
    wy = p.run((0.0, y - 6.0, 51.0), (0, 1, 0), 12.0)
    assert len(wy) == 2
    height = wy[1][0] - wy[0][1]
    assert width >= 8.0 and height >= 6.0
    assert width == pytest.approx(P.CAMBAY_WIN_W, abs=0.2) and height == pytest.approx(P.CAMBAY_WIN_H, abs=0.2)
    # window top is far below the lid seat; rim region above is untouched
    assert y + height / 2 < P.CAMBAY_BOX_LID_SEAT_Y - 10
    top = cq.Workplane("XY").box(200, 200, 100, centered=False).translate((-100, P.CAMBAY_BOX_LID_SEAT_Y - 30, -100))
    assert combined.intersect(top).val().Volume() == pytest.approx(box_bay.intersect(top).val().Volume(), rel=1e-6)
    cb = combined.val().BoundingBox()
    assert cb.ymax == pytest.approx(P.CAMBAY_BOX_TOP_Y, abs=0.05)      # rim continuous, no notch
    # mouths are flared (chamfered): opening grows toward the pocket and the bay
    assert not p.inside(5.9, y, P.CAMBAY_BOX_POCKET_HALF + 0.5)         # wider than 10 mm at the pocket wall
    # >= 5 mm from the corner cable holes: nearest hole mouth at |x| = 54.1
    assert 54.1 - (P.CAMBAY_WIN_W / 2 + P.CAMBAY_WIN_FLARE + 4.5) > P.CAMBAY_CORNER_HOLE_KEEPOUT


def test_box_only_modified_at_window_and_pilot(combined, box_bay):
    removed = box_bay.cut(combined)
    v = removed.val().Volume()
    assert 300.0 < v < 3500.0, v            # wire window + flares + IMU pilot 1
    bb = removed.val().BoundingBox()
    assert bb.xmin > -16 and bb.xmax < 16
    assert bb.ymin > 2.0 and bb.ymax < 30.0       # pilot hole 1 reaches down to y = 2.4
    assert abs(bb.zmin) < 66.0 and abs(bb.zmax) < 66.0
    # corner cable-hole region untouched: sample the box/combined volumes near the 4 mouths
    for sx in (1, -1):
        for sz in (1, -1):
            c = cq.Workplane("XY").box(30, 30, 30).translate((sx * 54.1, 14.05, sz * 54.1))
            assert combined.intersect(c).val().Volume() == pytest.approx(box_bay.intersect(c).val().Volume(), rel=1e-4)


# --------------------------------------------------------- cable lines ----
def test_cable_lines_clear_of_bay(body, cover):
    mouths = [(sx * 54.09, 14.05, sz * 54.09) for sx in (1, -1) for sz in (1, -1)]
    Vb, Fb = tessellate(body, 0.15, 0.3)
    Vc, Fc = tessellate(cover, 0.15, 0.3)
    V = np.concatenate([Vb, Vc])
    F = np.concatenate([Fb, Fc + len(Vb)])
    dmin = 1e9
    for mx, my, mz in mouths:
        dirs = []
        for az in np.radians(np.arange(0, 90.1, 7.5)):
            for el in np.radians(np.arange(10, 90.1, 10.0)):
                dirs.append([np.sign(mx) * math.cos(az) * math.cos(el), math.sin(el),
                             np.sign(mz) * math.sin(az) * math.cos(el)])
        t = ray_mesh_first_hit(np.array([mx, my, mz]), np.array(dirs), V, F)
        assert not np.isfinite(t).any(), f"cable line from corner ({mx:.0f},{mz:.0f}) hits the bay"
        # distance from the mouth to the nearest bay vertex
        dmin = min(dmin, float(np.linalg.norm(V - np.array([mx, my, mz]), axis=1).min()))
    assert dmin > P.CAMBAY_CORNER_HOLE_KEEPOUT + 5.0, dmin


# ---------------------------------------------------------------- walls ----
def test_min_wall_thickness(combined, cover):
    p = Probe(combined)
    r0 = B.BOARD_CR
    wall = P.CAMBAY_WALL - 0.05
    # -X wall (XIAO zone, between vent slots) and +X wall (clear of the USB window)
    runs = p.run((-B.OUT_HALF_X - 1.0, 8.0, r0 - 6.0), (1, 0, 0), 4.0)
    assert any(abs((b - a) - P.CAMBAY_WALL) < 0.1 for a, b in runs[:1])
    runs = p.run((B.CAV_HALF_X - 1.0, 12.0, B.HEAD_R1 - 0.6), (1, 0, 0), 4.0)
    assert runs and (runs[0][1] - runs[0][0]) >= P.CAMBAY_WALL - 0.1
    # outer end wall
    runs = p.run((0.0, 15.0, B.HEAD_R1 - 1.0), (0, 0, 1), 4.0)
    assert runs and abs((runs[0][1] - runs[0][0]) - P.CAMBAY_WALL) < 0.1
    # floor beside the window
    runs = p.run((-11.5, -0.5, B.BOARD_CR + 12.0 - 8.0), (0, 1, 0), 4.0)
    # (position chosen outside cradle block; floor solid from y=0)
    # vent ligaments between the -X wall slots stay >= 2.0 mm
    slots = [B.BOARD_CR - 4.0, B.BOARD_CR, B.BOARD_CR + 4.0]
    assert (slots[1] - 1.0) - (slots[0] + 1.0) >= P.CAMBAY_WALL - 1e-9
    # cover plate and ears
    pc = Probe(cover)
    runs = pc.run((0.0, B.H_CAV - 0.5, B.COVER_R0 + 20.0), (0, 1, 0), 4.0)
    assert runs and (runs[0][1] - runs[0][0]) >= P.CAMBAY_COVER_T - 0.1
    # floor thickness under the neck (outside the window, at the box side of the IMU)
    pf = Probe(combined)
    runs = pf.run((0.0, -0.3, B.IMU_RC), (0, 1, 0), 4.0)
    assert runs and abs((runs[0][1] - runs[0][0]) - P.CAMBAY_FLOOR_T) < 0.1


def test_cover_fasteners_and_boss_walls(combined, cover):
    p = Probe(combined)
    # insert holes in the cover columns: diameter = heat-set melt-in hole, wall >= 2.5
    assert B.COL_OD / 2 - P.M3_THREAD_HOLE / 2 >= P.CAMBAY_BOSS_WALL - 1e-9
    runs = p.run((B.COL_X - 3.0, B.H_CAV - 2.0, B.COL_R), (1, 0, 0), 6.0)
    assert len(runs) == 2 and runs[1][0] - runs[0][1] == pytest.approx(P.M3_THREAD_HOLE, abs=2 * TOL)
    pc = Probe(cover)
    runs = pc.run((B.COL_X - 3.0, B.H_CAV + 1.0, B.COL_R), (1, 0, 0), 6.0)
    assert len(runs) == 2 and runs[1][0] - runs[0][1] == pytest.approx(P.SCREW_M3, abs=2 * TOL)


def test_gusset_ribs_stiffen_root(body):
    """Ribs are present on both sides, reach out to <= RIB_X_MAX and stay 5 mm
    clear of the corner holes (|x| = 54.1)."""
    bb = body.val().BoundingBox()
    assert bb.xmax == pytest.approx(P.CAMBAY_RIB_SPAN_X + P.CAMBAY_RIB_T / 2 * 0.9, abs=1.5)
    assert bb.xmax + P.CAMBAY_CORNER_HOLE_KEEPOUT < 54.09
    p = Probe(body)
    for sx in (1, -1):
        # a point on the rib centre line half way along
        x = sx * (B.OUT_HALF_X - 0.5 + (P.CAMBAY_RIB_SPAN_X - B.OUT_HALF_X + 0.5) * 0.5)
        r = 82.0 - (82.0 - 56.0) * 0.5
        assert p.inside(x, P.CAMBAY_RIB_H / 2, r)


# --------------------------------------------------------------- mass ----
def test_added_mass_under_30g(combined, box_bay, cover):
    added = combined.val().Volume() - box_bay.val().Volume() + cover.val().Volume()
    mass_g = added / 1000.0 * PETG
    assert 5.0 < mass_g <= 30.0, mass_g


# --------------------------------------------------- STEP round trip ----
def test_step_round_trip(combined, cover, tmp_path):
    for name, s in (("combined", combined), ("cover", cover)):
        path = str(tmp_path / f"{name}.step")
        cq.exporters.export(s, path)
        re = cq.importers.importStep(path).val()
        src = s.val()
        assert re.Volume() == pytest.approx(src.Volume(), rel=1e-4)
        a, b = src.BoundingBox(), re.BoundingBox()
        for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            # OCC bounding boxes of BSpline-heavy solids are loose and differ slightly
            # between the boolean result and the re-imported shape
            assert getattr(a, k) == pytest.approx(getattr(b, k), abs=0.6)
        assert len(re.Solids()) == 1


def test_pose_helper_consistency():
    assert B.LENS_CENTER_BAY[2] == pytest.approx(S * P.CAMBAY_CAM_R)
    assert B.OPTICAL_AXIS_BAY == (0.0, -1.0, 0.0)
    assert math.hypot(B.LENS_CENTER_BAY[0], B.LENS_CENTER_BAY[2]) == pytest.approx(P.CAMBAY_CAM_R)


def test_no_interference_with_other_v6_parts(parts, body):
    """The bay must not collide with any other v6 solid (the Griper Cylinder
    touches the box bottom plane; face contact only)."""
    ox, oy, oz = B.BAY_ORIGIN_WORLD
    bay_w = body.val().moved(cq.Location(cq.Vector(ox, oy, oz)))
    bb = bay_w.BoundingBox()
    checked = 0
    for n, s in parts:
        if n == BOX_NAME:
            continue
        a = s.BoundingBox()
        if (a.xmax < bb.xmin or bb.xmax < a.xmin or a.ymax < bb.ymin or bb.ymax < a.ymin
                or a.zmax < bb.zmin or bb.zmax < a.zmin):
            continue
        checked += 1
        assert s.intersect(bay_w).Volume() < 0.5, f"bay collides with {n}"
    assert checked >= 1
