"""
Geometry checks for cad/parts/claw_camera_bay.py (XIAO ESP32-S3 Sense camera bay, no IMU
(D27), unioned onto the v6 electrical box).  Everything is measured on the built BRep solids with
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
    assert bb.zmin == pytest.approx(-B.OUT_R1, abs=0.05)       # cradle end wall, r = 101.3
    assert bb.xmin == pytest.approx(-bb.xmax, abs=0.05)         # symmetric: ribs reach +-34.85
    assert bb.xmax < P.CAMBAY_CORNER_HOLE_EXIT_XZ - P.CAMBAY_CORNER_HOLE_KEEPOUT
    assert bb.ymin == pytest.approx(0.0, abs=0.02)          # on the print bed plane with the box
    assert bb.ymax == pytest.approx(B.H_CAV, abs=0.05)
    cb = combined.val().BoundingBox()
    assert cb.ymin == pytest.approx(0.0, abs=0.02)           # box bottom plane unchanged
    assert cb.ymax == pytest.approx(P.CAMBAY_BOX_TOP_Y, abs=0.05)
    assert cb.zmax == pytest.approx(P.CAMBAY_BOX_FLANGE_HALF, abs=0.05)
    kb = cover.val().BoundingBox()
    assert kb.zmin == pytest.approx(-B.OUT_R1, abs=0.05)
    assert kb.ymax == pytest.approx(B.Y_TOP, abs=0.05)       # flat outer face, nothing above it
    # lowest cover feature = the XIAO hold-down pegs
    assert kb.ymin == pytest.approx(B.Y_BOARD0 + P.CAMBAY_PEG_STOP_ABOVE_SEAT, abs=0.05)


# ---------------------------------------------------------- optical geometry ----
def test_lens_window_size_and_chamfer(combined):
    p = Probe(combined)
    r0 = B.BOARD_CR + P.CAMBAY_LENS_DR
    # window along X at the USB-C end (y = 1: above the 1 mm chamfer), measured at the lens radius
    runs = p.run((-14.5, 1.0, r0), (1, 0, 0), 29.0)
    assert len(runs) == 2
    assert runs[0][1] - 14.5 == pytest.approx(B.WIN_X0, abs=2 * TOL)
    win_x = runs[1][0] - runs[0][1]
    assert win_x == pytest.approx(B.WIN_X, abs=2 * TOL)
    # radial size 16.4: lens position +-4 mm plus the 8 mm barrel
    runs = p.run((B.WIN_XC, 1.0, r0 - 10.2), (0, 0, 1), 20.4)
    assert len(runs) == 2
    win_r = runs[1][0] - runs[0][1]
    assert win_r == pytest.approx(P.CAMBAY_LENS_WINDOW_R, abs=2 * TOL)
    assert win_r >= 2 * (P.CAMBAY_LENS_POS_TOL + P.CAMBAY_LENS_BARREL_D / 2)
    # the window sits at the USB-C end: lens centre +4.75, USB end of the pocket is +11.5
    assert B.LENS_X == pytest.approx(4.75, abs=1e-9) and B.WIN_X1 < B.CAV_HALF_X
    # chamfer: bottom mouth is wider by the 1 mm chamfer each side
    wide = Probe(combined).run((-14.5, 0.15, r0), (1, 0, 0), 29.0)
    assert (wide[1][0] - wide[0][1]) > win_x + 1.2
    for y in (0.1, 1.0, 3.0, 6.0, 9.0):
        assert not p.inside(B.LENS_X, y, r0)
    # lens-position tolerance: the 8 mm barrel (module protrudes 8 mm below the seat) fits with the
    # lens 3.9 mm off in -X / +-r and up to the USB-end envelope limit (+2.25) in +X
    for dx, dr in ((2.25, 0), (-3.9, 0), (0, 3.9), (0, -3.9), (2.25, 3.9), (-3.9, -3.9)):
        barrel = (cq.Workplane("XZ").workplane(offset=-B.Y_BOARD0).center(B.LENS_X + dx, z_of(r0 + dr))
                  .circle(P.CAMBAY_LENS_BARREL_D / 2).extrude(B.Y_BOARD0 - B.LENS_FRONT_Y))
        assert combined.intersect(barrel).val().Volume() < 0.01, (dx, dr)
    # 8.5 mm square camera module body at the nominal lens position
    mod = B._rbox(B.LENS_X - 4.25, B.LENS_X + 4.25, B.LENS_FRONT_Y, B.Y_BOARD0, r0 - 4.25, r0 + 4.25)
    assert combined.intersect(mod).val().Volume() < 0.01
    # lens glass height
    assert B.LENS_FRONT_Y == pytest.approx(P.CAMBAY_LENS_FRONT_Y)
    assert B.Y_BOARD0 - B.LENS_FRONT_Y == pytest.approx(P.CAMBAY_CAM_PROTRUDE)


def test_lens_barrel_and_field_of_view_unclipped(combined):
    """The 70 deg diagonal FOV (35 deg half angle) must leave the tunnel unclipped
    even with the lens off its nominal position (lens position is an assumption)."""
    lens_y = B.LENS_FRONT_Y
    half = math.radians(P.CAMBAY_FOV_DIAG_DEG / 2)
    V, F = tessellate(combined, 0.2, 0.3)
    dirs = []
    for a in np.linspace(0, 2 * math.pi, 72, endpoint=False):
        dirs.append([math.sin(half) * math.cos(a), -math.cos(half), math.sin(half) * math.sin(a)])
    dirs = np.array(dirs)
    # 4:3 sensor pyramid edge rays (long side along X)
    tx = math.tan(half) * 4 / 5
    ty = math.tan(half) * 3 / 5
    pyr = []
    for u in np.linspace(-tx, tx, 9):
        for v in (-ty, ty):
            pyr.append([u, -1.0, v])
    for v in np.linspace(-ty, ty, 7):
        for u in (-tx, tx):
            pyr.append([u, -1.0, v])
    pyr = np.array(pyr)
    pyr /= np.linalg.norm(pyr, axis=1, keepdims=True)
    r0 = B.BOARD_CR + P.CAMBAY_LENS_DR
    for dx, dr in ((0, 0), (2.25, 0), (-3.9, 0), (0, 3.9), (0, -3.9)):
        origin = np.array([B.LENS_X + dx, lens_y, z_of(r0 + dr)])
        t = ray_mesh_first_hit(origin, pyr, V, F)
        assert not np.any(t < 15.0), f"sensor pyramid clipped for lens offset ({dx},{dr})"
    t = ray_mesh_first_hit(np.array([B.LENS_X, lens_y, z_of(r0)]), dirs, V, F)
    assert not np.any(t < 15.0), f"circular cone clipped: {np.sort(t)[:5]}"


# ----------------------------------------------------------- boards fit ----
def _env(x0, x1, y0, y1, r0, r1):
    return B._rbox(x0, x1, y0, y1, r0, r1)


def test_xiao_cradle_and_clearance(combined, cover):
    """Generous cradle: pocket 23.0 x 18.6, >= 16 mm above the seat, board 21 x 17.8 + USB-C overhang."""
    r0 = B.BOARD_CR
    bl, bw = P.CAMBAY_XIAO_BOARD_L, P.CAMBAY_XIAO_W
    top = B.Y_STACK_TOP                                          # nominal stack top (7 mm above the seat)
    # base board + expansion/camera stack above the seat, USB-C 8.94 x 3.3 overhanging +X by 1.5 mm
    board = _env(B.BOARD_X0 - bl / 2, B.BOARD_X0 + bl / 2, B.Y_BOARD0, top, r0 - bw / 2, r0 + bw / 2)
    usb = _env(B.BOARD_X0 + bl / 2, B.BOARD_X0 + bl / 2 + P.CAMBAY_XIAO_USB_OVERHANG, top - 3.3, top,
               r0 - 4.5, r0 + 4.5)
    for env in (board, usb):
        assert combined.intersect(env).val().Volume() < 0.05
        assert cover.intersect(env).val().Volume() < 0.05
    # even the whole 15 mm stack (as if nothing protruded below the seat) fits under the cover seat
    full = _env(-P.CAMBAY_XIAO_L / 2, P.CAMBAY_XIAO_L / 2, B.Y_BOARD0, B.Y_BOARD1, r0 - bw / 2, r0 + bw / 2)
    assert combined.intersect(full).val().Volume() < 0.5       # soft locating ribs only (0.4 proud)
    # (the cover's four hold-down pegs do reach into that envelope from 11 mm above the seat: by design)
    # pocket measured away from ribs / notch / vents / fence gap
    p = Probe(combined)
    ys = B.Y_BOARD0 + 3.0
    runs = p.run((-14.5, ys, r0 + 8.5), (1, 0, 0), 29.0)
    assert len(runs) == 2 and runs[1][0] - runs[0][1] == pytest.approx(P.CAMBAY_CRADLE_L, abs=2 * TOL)
    runs = p.run((3.0, ys, B.HEAD_R1 - 25.0), (0, 0, 1), 28.0)
    assert runs[-1][0] == pytest.approx(25.0, abs=2 * TOL)   # end wall inner face at HEAD_R1
    runs = p.run((9.0, ys, B.HEAD_R0 - 4.0), (0, 0, 1), 28.0)
    assert len(runs) == 2 and runs[1][0] - runs[0][1] == pytest.approx(P.CAMBAY_CRADLE_W, abs=2 * TOL)
    assert P.CAMBAY_CRADLE_L >= 23.0 and P.CAMBAY_CRADLE_W >= 18.6
    # internal height above the seat (cover seat - seat plane) >= 16
    runs = p.run((-8.0, 0.0, r0 + 2.75), (0, 1, 0), B.H_CAV + 1.0)
    assert len(runs) == 1 and runs[0][1] == pytest.approx(B.Y_BOARD0, abs=2 * TOL)
    assert B.H_CAV - B.Y_BOARD0 >= 16.0
    # soft locating ribs: 0.4 proud on both long walls, absent in the wire gap |x| < 4
    for xc in (-8.0, 7.0):
        assert p.inside(xc, B.Y_BOARD0 + 3.0, B.HEAD_R1 - P.CAMBAY_LOCATOR_RIB_T / 2)
        assert not p.inside(xc, B.Y_BOARD0 + 3.0, B.HEAD_R1 - P.CAMBAY_LOCATOR_RIB_T - 0.1)
        assert p.inside(xc, B.Y_BOARD0 + 3.0, B.HEAD_R0 + P.CAMBAY_LOCATOR_RIB_T / 2)
    # board seat: floor of the cradle block at y = Y_BOARD0
    assert p.inside(-9.0, B.Y_BOARD0 - 0.1, B.BOARD_CR + 7.0)
    assert not p.inside(-9.0, B.Y_BOARD0 + 0.1, B.BOARD_CR + 7.0)


def test_no_imu_features(body, cover):
    """D27: no IMU on the claw -> no IMU pocket, pads, pegs, ties or parameters anywhere."""
    assert not [n for n in dir(P) if "IMU" in n.upper()]
    assert not [n for n in dir(B) if "IMU" in n.upper()]
    bb = body.val().BoundingBox()
    assert bb.zmin == pytest.approx(-(B.HEAD_R1 + B.WALL), abs=0.05)     # nothing beyond the cradle end wall
    assert body.val().Volume() < 16000.0


def test_antenna_pocket_and_hold_down(cover):
    # antenna 30x10 lies against the cover underside between the corral rails
    y0 = B.H_CAV
    ant_r0 = 65.0
    env = _env(-P.CAMBAY_ANT_W / 2, P.CAMBAY_ANT_W / 2, y0 - 1.0, y0, ant_r0 + 0.1, ant_r0 + P.CAMBAY_ANT_L + 0.1)
    assert cover.intersect(env).val().Volume() < 0.05
    rail = _env(P.CAMBAY_ANT_W / 2 + 0.5, P.CAMBAY_ANT_W / 2 + 1.0, y0 - 1.2, y0 - 0.2, ant_r0 + 5, ant_r0 + 10)
    assert cover.intersect(rail).val().Volume() > 1.0
    # board hold-down pegs stop 11 mm above the seat (nominal stack top is 7 mm above it)
    p = Probe(cover)
    px = B.CAV_HALF_X - 1.4
    pr = B.BOARD_CR + B.CAV_HALF_R - 1.4
    y_stop = B.Y_BOARD0 + P.CAMBAY_PEG_STOP_ABOVE_SEAT
    assert p.inside(px, y_stop + 0.1, pr) and not p.inside(px, y_stop - 0.1, pr)
    assert y_stop > B.Y_STACK_TOP + 2.0


# --------------------------------------------------------------- openings ----
def test_usb_c_notch_open_top_closed_by_cover(combined, cover):
    p = Probe(combined)
    r0 = B.BOARD_CR
    # 13 x 8 plug overmould (outside the wall) and the plug tip inside the cavity pass
    plug = _env(B.CAV_HALF_X - 0.2, B.OUT_HALF_X + 30.0, B.USB_YC - P.CAMBAY_USB_PLUG_H / 2,
                B.USB_YC + P.CAMBAY_USB_PLUG_H / 2, r0 - P.CAMBAY_USB_PLUG_W / 2, r0 + P.CAMBAY_USB_PLUG_W / 2)
    assert combined.intersect(plug).val().Volume() < 1e-3
    assert cover.intersect(plug).val().Volume() < 1e-3
    assert P.CAMBAY_USB_PLUG_W >= 13.0 and P.CAMBAY_USB_PLUG_H >= 8.0
    # +-1 mm lateral and vertical play for the plug (cable plug can be fitted for flashing in place)
    for dr, dy in ((0.9, 0.0), (-0.9, 0.0), (0.0, 0.9), (0.0, -0.4)):
        sh = _env(B.CAV_HALF_X - 0.2, B.OUT_HALF_X + 30.0, B.USB_YC - P.CAMBAY_USB_PLUG_H / 2 + dy,
                  B.USB_YC + P.CAMBAY_USB_PLUG_H / 2 + dy, r0 - P.CAMBAY_USB_PLUG_W / 2 + dr, r0 + P.CAMBAY_USB_PLUG_W / 2 + dr)
        assert combined.intersect(sh).val().Volume() < 1e-3, (dr, dy)
        assert cover.intersect(sh).val().Volume() < 1e-3, (dr, dy)
    # open-top notch: void from the sill to the wall top (no roof / lintel), width 15.0
    xm = B.CAV_HALF_X + 1.0
    ys = p.run((xm, B.USB_SILL_Y - 3.0, r0), (0, 1, 0), 3.0 + B.H_CAV - B.USB_SILL_Y + 0.5)
    assert len(ys) == 1 and ys[0][1] == pytest.approx(3.0, abs=2 * TOL)        # solid only below the sill
    rr = p.run((xm, B.USB_SILL_Y + 3.0, r0 - 8.0), (0, 0, 1), 16.0)
    assert len(rr) == 2 and rr[1][0] - rr[0][1] == pytest.approx(B.USB_NOTCH_W, abs=2 * TOL)
    assert B.USB_NOTCH_W >= 13.0
    # the cover closes the notch from above (plate directly over the wall top)
    pc = Probe(cover)
    assert pc.inside(xm, B.H_CAV + 0.3, r0) and not pc.inside(xm, B.H_CAV - 0.1, r0)
    # connector end of the XIAO envelope is aligned with the notch (same radial centre, +X end)
    assert abs(B.BOARD_CR - (B.HEAD_R0 + B.HEAD_R1) / 2) < 1e-9
    assert B.USB_SILL_Y > B.Y_BOARD0


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


def test_box_only_modified_at_window(combined, box_bay):
    removed = box_bay.cut(combined)
    v = removed.val().Volume()
    assert 300.0 < v < 3500.0, v            # wire window + flares only
    bb = removed.val().BoundingBox()
    assert bb.xmin > -16 and bb.xmax < 16
    assert bb.ymin > 6.0 and bb.ymax < 30.0       # window + bay-side flare only
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
    ys = B.Y_BOARD0 + 5.0
    # end wall, XIAO -X wall (between vents), +X wall beside the notch, neck-side fence
    runs = p.run((3.0, 12.0, B.HEAD_R1 - 1.0), (0, 0, 1), 4.0)
    assert abs((runs[0][1] - runs[0][0]) - P.CAMBAY_WALL) < 0.1
    runs = p.run((-B.OUT_HALF_X - 1.0, ys, r0 + 2.75), (1, 0, 0), 4.0)
    assert abs((runs[0][1] - runs[0][0]) - P.CAMBAY_WALL) < 0.1
    runs = p.run((B.CAV_HALF_X - 1.0, ys, r0 + 8.5), (1, 0, 0), 4.0)
    assert runs and abs((runs[0][1] - runs[0][0]) - P.CAMBAY_WALL) < 0.1
    runs = p.run((8.0, B.Y_BOARD0 + 4.0, B.HEAD_R0 - 3.0), (0, 0, 1), 4.0)
    assert runs and abs((runs[0][1] - runs[0][0]) - P.CAMBAY_WALL) < 0.1
    # ledge between the window and the cavity on the neck side (block reaches past the chamfer foot)
    runs = p.run((B.WIN_XC, 4.0, r0 - P.CAMBAY_LENS_WINDOW_R / 2 - 3.5), (0, 0, 1), 3.5)
    assert runs and runs[0][1] - runs[0][0] >= P.CAMBAY_WALL - 0.1
    # wall left at the USB-end of the lens window after the chamfer (>= 1.2)
    assert B.OUT_HALF_X - (B.WIN_X1 + P.CAMBAY_LENS_CHAMFER) >= 1.2
    # vent ligaments between slots
    assert 5.5 - 2.0 >= P.CAMBAY_WALL - 1e-9
    # cover plate
    pc = Probe(cover)
    runs = pc.run((0.0, B.H_CAV - 0.5, B.COVER_R0 + 14.0), (0, 1, 0), 4.0)
    assert runs and (runs[0][1] - runs[0][0]) >= P.CAMBAY_COVER_T - 0.1
    # floor thickness under the neck
    runs = p.run((0.0, -0.3, 70.4), (0, 1, 0), 4.0)
    assert runs and abs((runs[0][1] - runs[0][0]) - P.CAMBAY_FLOOR_T) < 0.1


def test_min_wall_inward_normal_scan(body, cover):
    """Every wall of bay and cover >= 1.2 mm (inward-normal rays from the facets outside the box wall)."""
    for name, shp in (("body", body), ("cover", cover)):
        V, F = tessellate(shp, 0.1, 0.2)
        tri = V[F]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        area = np.linalg.norm(n, axis=1)
        keep = area > 0.05
        n[keep] /= area[keep, None]
        cen = tri.mean(axis=1)
        tmin = np.inf
        for i in np.where(keep & (-cen[:, 2] > 62.0))[0]:
            t = ray_mesh_first_hit(cen[i] - n[i] * 1e-3, (-n[i])[None, :], V, F)[0]
            tmin = min(tmin, t)
        assert tmin >= 1.2, (name, tmin)


def test_cover_fasteners_and_boss_walls(combined, cover):
    p = Probe(combined)
    # M3 heat-set insert boss: hole D4.0-4.2 x >= 5.7 (+ melt-in reserve), boss OD >= 8, wall >= 2.5
    assert 4.0 <= P.CAMBAY_INSERT_D <= 4.2 and P.CAMBAY_INSERT_DEPTH >= P.CAMBAY_INSERT_LEN + 1.0
    assert B.COL_OD >= 8.0
    assert B.COL_OD / 2 - P.CAMBAY_INSERT_D / 2 >= P.CAMBAY_BOSS_WALL - 1e-9
    runs = p.run((B.COL_X - 3.0, B.H_CAV - 2.0, B.COL_R), (1, 0, 0), 6.0)
    assert len(runs) == 2 and runs[1][0] - runs[0][1] == pytest.approx(P.CAMBAY_INSERT_D, abs=2 * TOL)
    ys = p.run((B.COL_X, -0.5, B.COL_R), (0, 1, 0), B.H_CAV + 1.0)
    assert len(ys) == 1 and ys[0][1] == pytest.approx(0.5 + B.H_CAV - P.CAMBAY_INSERT_DEPTH, abs=0.1)
    pc = Probe(cover)
    runs = pc.run((B.COL_X - 3.0, B.H_CAV + 1.0, B.COL_R), (1, 0, 0), 6.0)
    assert len(runs) == 2 and runs[1][0] - runs[0][1] == pytest.approx(P.SCREW_M3, abs=2 * TOL)


def test_gusset_ribs_stiffen_root(body):
    """Ribs are present on both sides, reach out to <= RIB_X_MAX and stay 5 mm
    clear of the corner holes (|x| = 54.1)."""
    bb = body.val().BoundingBox()
    assert bb.xmax == pytest.approx(P.CAMBAY_RIB_SPAN_X + P.CAMBAY_RIB_T / 2 * 0.9, abs=1.5)
    assert bb.xmax + P.CAMBAY_CORNER_HOLE_KEEPOUT < 54.09
    assert -bb.xmin + P.CAMBAY_CORNER_HOLE_KEEPOUT < 54.09
    p = Probe(body)
    for sx in (1, -1):
        # a point on the rib centre line half way along
        x = sx * 0.5 * ((B.OUT_HALF_X - 0.5) + P.CAMBAY_RIB_SPAN_X)
        r = 0.5 * (76.0 + 56.0)
        assert p.inside(x, P.CAMBAY_RIB_H / 2, r)


# --------------------------------------------------------------- mass ----
def test_added_mass_under_30g(combined, box_bay, cover):
    added = combined.val().Volume() - box_bay.val().Volume() + cover.val().Volume()
    mass_g = added / 1000.0 * PETG
    assert 5.0 < mass_g <= 30.0, mass_g
    assert mass_g < 22.0, mass_g          # IMU removed: was 28.7 g


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
    assert B.LENS_CENTER_BAY[0] == pytest.approx(4.75)
    assert B.OPTICAL_AXIS_BAY == (0.0, -1.0, 0.0)
    assert abs(B.LENS_CENTER_BAY[2]) == pytest.approx(P.CAMBAY_CAM_R)


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
