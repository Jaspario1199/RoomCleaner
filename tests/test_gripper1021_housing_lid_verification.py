"""
INDEPENDENT verification of the Gripper 1021 housing lid (exports/step/gripper1021_housing_lid.step, exports/stl/gripper1021_housing_lid.stl).

Written by the geometry-verifier, not the implementer.  The implementer's builder (cad/parts/gripper1021_housing_lid.py), its tests and its
measurement helpers are NOT used for any pass/fail decision; the only import from the repository is cad.params (CAMBAY1021_BAY_ORIGIN_WORLD, the
bay-frame origin that the housing STEP is placed with, and PETG data from cad.materials).  The one exception is the "stale export" test, which rebuilds
the part with the builder on purpose to see whether the exported file is current.

Every check is made on the exported files: B-rep face parameters, exact line/solid intersections (IntCurvesFace), booleans, BRepExtrema distances,
and a raster of the STL slice.  Frame: bay frame = world minus CAMBAY1021_BAY_ORIGIN_WORLD (x, z horizontal, +y up).

Run:  /usr/bin/python3 -m pytest tests/test_gripper1021_housing_lid_verification.py -s -q
"""

from __future__ import annotations

import math
import os
import struct
import sys

import pytest

cq = pytest.importorskip("cadquery")

import numpy as np                                              # noqa: E402
from OCP.Bnd import Bnd_Box                                      # noqa: E402
from OCP.BRepBndLib import BRepBndLib                            # noqa: E402
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector     # noqa: E402
from OCP.gp import gp_Lin, gp_Pnt, gp_Dir                         # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad import materials as M                                   # noqa: E402

STEP_DIR = os.path.join(REPO, "exports", "step")
LID_STEP = os.path.join(STEP_DIR, "gripper1021_housing_lid.step")
LID_STL = os.path.join(REPO, "exports", "stl", "gripper1021_housing_lid.stl")
HOUSING_STEP = os.path.join(STEP_DIR, "gripper1021_housing_cambay_34.step")
COVER_STEP = os.path.join(STEP_DIR, "gripper1021_housing_cambay_cover.step")
ORIGIN = P.CAMBAY1021_BAY_ORIGIN_WORLD

pytestmark = pytest.mark.skipif(not all(os.path.exists(p) for p in (LID_STEP, LID_STL, HOUSING_STEP, COVER_STEP)), reason="exports not available")

# ---- expectations (from the task statement, not from the implementer's code) -----------------------------------------------------------------
SEAT_Y, RIM_Y = 50.0, 55.0
RECESS_HALF, RECESS_R, RECESS_C = 42.5, 12.5, 30.0
POCKET_HALF, POCKET_R = 40.0, 10.0
PLATE_HALF, PLATE_R = 42.25, 12.25                 # 84.5 square, R12.25
SIDE_CLEAR, INTERF = 0.25, 0.15
BUMP_TIP_X = RECESS_HALF + INTERF                  # 42.65
MIN_FEATURE = 0.45

RESULTS: dict = {}


def note(key, value):
    RESULTS[key] = value
    print(f"[measured] {key}: {value}")


# ---- helpers ----------------------------------------------------------------------------------------------------------------------------------
def to_bay(shape):
    return shape.translate(cq.Vector(-ORIGIN[0], -ORIGIN[1], -ORIGIN[2]))


def exact_bb(shape):
    """Exact bounding box (cq's BoundingBox() grows once a face has been meshed)."""
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, b, False, False)
    x0, y0, z0, x1, y1, z1 = b.Get()
    return (x0, x1, y0, y1, z0, z1)


def hits(shape, p, d):
    """Sorted parameters t (mm, d unit) of all intersections of the line p + t d with the shape's faces, t >= 0 only."""
    d = np.array(d, float)
    d /= np.linalg.norm(d)
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(shape.wrapped, 1e-7)
    inter.Perform(gp_Lin(gp_Pnt(*[float(v) for v in p]), gp_Dir(*[float(v) for v in d])), 0.0, 1e6)
    ts = sorted(inter.WParameter(i) for i in range(1, inter.NbPnt() + 1))
    out = []
    for t in ts:
        if not out or t - out[-1] > 1e-5:
            out.append(t)
    return out


def vol(shape):
    return shape.Volume() if shape is not None else 0.0


def common(a, b):
    r = a.intersect(b)
    return r


def pieces(shape):
    return [s for s in shape.Solids()] if shape is not None else []


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0)).val()


def rotate_xz(x, z, deg):
    a = math.radians(deg)
    return (x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a))


SIDES = {"+z": ((0, 0, 1), (1, 0, 0)), "-z": ((0, 0, -1), (-1, 0, 0)), "+x": ((1, 0, 0), (0, 0, -1)), "-x": ((-1, 0, 0), (0, 0, 1))}   # outward n, tangent t


# ---- fixtures ---------------------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def lid_world():
    return cq.importers.importStep(LID_STEP).val()


@pytest.fixture(scope="module")
def lid(lid_world):
    return to_bay(lid_world)


@pytest.fixture(scope="module")
def housing():
    return to_bay(cq.importers.importStep(HOUSING_STEP).val())


@pytest.fixture(scope="module")
def hclip(housing):
    """Housing between y 30 and 60: the open top, the seat and the upper wall (plus the pocket below the seat, down to 30)."""
    r = housing.intersect(box(-60, 60, 30, 60, -60, 60))
    return r


@pytest.fixture(scope="module")
def cover():
    return to_bay(cq.importers.importStep(COVER_STEP).val())


@pytest.fixture(scope="module", autouse=True)
def _dump():
    yield
    print("\n==== MEASUREMENT SUMMARY ====")
    for k, v in RESULTS.items():
        print(f"{k}: {v}")


# =====================================================================================================================================================
# 1. the lid itself
# =====================================================================================================================================================
def test_01_single_valid_solid_bbox_volume(lid):
    assert lid.isValid()
    assert len(lid.Solids()) == 1, "expected exactly one solid"
    v = lid.Volume()
    x0, x1, y0, y1, z0, z1 = exact_bb(lid)
    note("lid.volume_mm3", round(v, 2))
    note("lid.mass_g_PETG_1.27", round(v * 1.27e-3, 3))
    note("lid.bbox_bay", [round(c, 4) for c in (x0, x1, y0, y1, z0, z1)])
    assert v > 0
    # claim: bbox 85.3 x 1.8 x 85.3 (84.5 plate + 2 x 0.4 bump protrusion), y 50.0 .. 51.8
    assert x1 - x0 == pytest.approx(85.3, abs=0.01) and z1 - z0 == pytest.approx(85.3, abs=0.01) and y1 - y0 == pytest.approx(1.8, abs=0.005)
    assert y0 == pytest.approx(SEAT_Y, abs=0.002) and y1 == pytest.approx(51.8, abs=0.002)
    assert abs(x0 + x1) < 0.002 and abs(z0 + z1) < 0.002, "lid centred on the tube axis"
    # independent analytic volume: plate - 4 L-slots - notch - top chamfer + 4 bump tips
    c4 = 4 - math.pi
    plate_a = (2 * PLATE_HALF) ** 2 - c4 * PLATE_R ** 2
    slot_a = 13.0 * 1.0 + 3.0 * 1.0 - 1.0                      # inboard slot -3..10 x 1.0, end slot 1.0 x 3.0 (inside the plate), overlap 1.0
    notch_a = 14.0 * 4.5 - 2 * (1 - math.pi / 4) * 2.0 ** 2     # two inner corners R2 stay material
    chamfer_v = 0.5 * 0.3 * 0.3 * (4 * (2 * PLATE_HALF - 2 * PLATE_R) + 2 * math.pi * PLATE_R)
    bump_v = 4 * 0.64                                           # rough: 4 teeth beyond the edge (0.4 x ~0.89 x 1.8 less the lead-in)
    v_exp = (plate_a - 4 * slot_a - notch_a) * 1.8 - chamfer_v + bump_v
    note("lid.volume_analytic_mm3", round(v_exp, 1))
    assert v == pytest.approx(v_exp, rel=0.003)
    assert v == pytest.approx(12391.0, rel=0.002)               # builder's claim


# =====================================================================================================================================================
# 2. the housing's recess and seat, measured from the housing STEP
# =====================================================================================================================================================
def test_02a_recess_walls_and_corners(hclip):
    y = 52.5
    # straight walls: first hit going outward from the middle
    pos = {}
    for name, (n, t) in SIDES.items():
        vals = []
        for u in (-20.0, -10.0, 0.0, 10.0, 20.0):
            p = np.array(n) * 0 + np.array(t) * u + np.array((0, y, 0))
            h = hits(hclip, p, n)
            vals.append(h[0])
        pos[name] = vals
        assert max(vals) - min(vals) < 1e-3
        assert vals[0] == pytest.approx(RECESS_HALF, abs=1e-3), f"recess wall {name}"
    note("recess.wall_positions_from_axis_at_y52.5", {k: round(v[0], 5) for k, v in pos.items()})
    # width 85 x 85 and centring
    assert pos["+x"][0] + pos["-x"][0] == pytest.approx(85.0, abs=2e-3) and pos["+z"][0] + pos["-z"][0] == pytest.approx(85.0, abs=2e-3)
    # R12.5 corners about (+-30, +-30): radial ray from the corner centre
    worst = 0.0
    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        for ang in range(10, 81, 10):
            a = math.radians(ang)
            d = (sx * math.cos(a), 0, sz * math.sin(a))
            h = hits(hclip, (sx * RECESS_C, y, sz * RECESS_C), d)
            r = h[0]
            worst = max(worst, abs(r - RECESS_R))
    note("recess.corner_radius_max_dev_from_R12.5_mm", round(worst, 5))
    assert worst < 2e-3
    # rim and seat heights, vertical rays
    h_rim = hits(hclip, (44.0, 40.0, 0.0), (0, 1, 0))
    h_seat = hits(hclip, (41.5, 40.0, 0.0), (0, 1, 0))
    h_pocket = hits(hclip, (0.0, 40.0, 0.0), (0, 1, 0))
    note("recess.rim_y", round(40.0 + h_rim[-1], 5))
    note("recess.seat_y", round(40.0 + h_seat[0], 5))
    assert 40.0 + h_rim[-1] == pytest.approx(RIM_Y, abs=1e-3)
    assert 40.0 + h_seat[0] == pytest.approx(SEAT_Y, abs=1e-3)
    assert len(h_pocket) == 0, "pocket must be open under the middle of the lid (no floor between y 40 and 60)"


def test_02b_seat_ring_2p5mm_around_80_pocket(hclip, housing):
    # horizontal rays at y = 49.9 (below the seat) from the middle: pocket edge, then solid
    for name, (n, t) in SIDES.items():
        h = hits(hclip, (0, 49.9, 0), n)
        assert h[0] == pytest.approx(POCKET_HALF, abs=1e-3), f"pocket half {name}"
    # pocket corners R10 about (+-30, +-30)
    worst = 0.0
    for sx, sz in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
        for ang in range(10, 81, 10):
            a = math.radians(ang)
            h = hits(hclip, (sx * 30.0, 49.9, sz * 30.0), (sx * math.cos(a), 0, sz * math.sin(a)))
            worst = max(worst, abs(h[0] - POCKET_R))
    note("pocket.corner_radius_max_dev_from_R10_mm", round(worst, 5))
    assert worst < 2e-3
    # ring area: the +y planar face at the seat (any normal +y planar face near y = 50)
    ring = [f for f in housing.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y - 1) < 1e-6 and abs(f.Center().y - SEAT_Y) < 1e-3]
    assert len(ring) == 1
    area = ring[0].Area()
    exp = (85.0 ** 2 - (4 - math.pi) * RECESS_R ** 2) - (80.0 ** 2 - (4 - math.pi) * POCKET_R ** 2)
    note("ring.area_mm2 (measured / analytic)", (round(area, 3), round(exp, 3)))
    assert area == pytest.approx(exp, abs=0.1)
    assert (RECESS_HALF - POCKET_HALF) == pytest.approx(2.5)
    # nothing else standing in the recess between y 50 and 55: the housing's overlap with the recess prism (85 x 85, R12.5, shrunk by 1 um) is zero
    prism = (cq.Workplane("XZ").rect(2 * RECESS_HALF - 0.002, 2 * RECESS_HALF - 0.002).extrude(-(RIM_Y + 1.0 - SEAT_Y - 0.001))
             .edges("|Y").fillet(RECESS_R - 0.001).translate((0, SEAT_Y + 0.001, 0)).val())
    pb = prism.BoundingBox()
    assert pb.ymin == pytest.approx(SEAT_Y + 0.001, abs=1e-6) and pb.ymax > RIM_Y
    ov = vol(hclip.intersect(prism))
    note("recess.foreign_material_inside_recess_prism_mm3", round(ov, 6))
    assert ov < 1e-4


# =====================================================================================================================================================
# 3. fit of the lid in the housing
# =====================================================================================================================================================
def outer_profile(shape, y, n, t, us):
    """Outermost boundary distance from the axis along outward n at tangential offsets us (ray from outside, first hit)."""
    out = []
    for u in us:
        p = np.array(n) * 70.0 + np.array(t) * u + np.array((0, y, 0))
        h = hits(shape, p, -np.array(n))
        out.append(70.0 - h[0] if h else None)
    return np.array([np.nan if v is None else v for v in out])


@pytest.fixture(scope="module")
def profiles(lid, hclip):
    us = np.arange(-38.0, 38.001, 0.05)
    lidp, wallp = {}, {}
    for name, (n, t) in SIDES.items():
        lidp[name] = outer_profile(lid, 51.0, n, t, us)
        wallp[name] = np.array([hits(hclip, np.array(t) * u + np.array((0, 52.5, 0)), n)[0] for u in us])
    return us, lidp, wallp


def test_03a_plate_square_and_corner_radius(lid, profiles):
    us, lidp, wallp = profiles
    # plate straight edge = the most common outermost position (excluding bumps and the arm slots)
    edge = {}
    for name in SIDES:
        vals = lidp[name]
        sel = vals[(np.abs(vals - PLATE_HALF) < 0.05)]
        edge[name] = float(np.median(sel))
        assert len(sel) > 400
    note("plate.edge_position_per_side", {k: round(v, 4) for k, v in edge.items()})
    for name, v in edge.items():
        assert v == pytest.approx(PLATE_HALF, abs=0.005), name
    assert edge["+x"] + edge["-x"] == pytest.approx(84.5, abs=0.01) and edge["+z"] + edge["-z"] == pytest.approx(84.5, abs=0.01)
    # corner radius: from the corner centre (30, 30), the lid's outermost boundary at angles 10..80 deg, mid-height y = 51
    worst = 0.0
    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        for ang in range(10, 81, 10):
            a = math.radians(ang)
            h = hits(lid, (sx * 30.0, 51.0, sz * 30.0), (sx * math.cos(a), 0, sz * math.sin(a)))
            worst = max(worst, abs(h[-1] - PLATE_R))
    note("plate.corner_radius_max_dev_from_R12.25_mm", round(worst, 5))
    assert worst < 3e-3


def test_03b_side_clearance_and_four_bumps(lid, hclip, profiles):
    us, lidp, wallp = profiles
    gaps_plate, bumps = {}, {}
    for name in SIDES:
        gap = wallp[name] - lidp[name]
        plate = np.abs(lidp[name] - PLATE_HALF) < 0.02
        gaps_plate[name] = (float(gap[plate].min()), float(gap[plate].max()))
        mask = lidp[name] > PLATE_HALF + 0.1
        assert mask.sum() > 3, f"no bump on side {name}"
        idx = np.where(mask)[0]
        assert idx[-1] - idx[0] + 1 == len(idx), f"more than one bump on side {name}"
        bumps[name] = {"u_centre": round(float(us[idx].mean()), 3), "tip_pos": round(float(lidp[name][idx].max()), 4),
                       "interference_mm": round(float((-gap[idx]).max()), 4), "width_at_0.1_above_edge": round(float(len(idx) * 0.05), 2)}
        assert (-gap[idx]).max() == pytest.approx(INTERF, abs=0.01), f"bump interference on {name}"
        assert lidp[name][idx].max() == pytest.approx(BUMP_TIP_X, abs=0.005)
    note("side_clearance_plate_edge (min,max) per side", {k: (round(a, 4), round(b, 4)) for k, (a, b) in gaps_plate.items()})
    note("bumps", bumps)
    for name, (a, b) in gaps_plate.items():
        assert a == pytest.approx(SIDE_CLEAR, abs=0.006) and b == pytest.approx(SIDE_CLEAR, abs=0.006), name
    # corner gap: recess R12.5 vs plate R12.25 about the same centre, along the four diagonals and at 20 / 70 deg
    cg = []
    for sx, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        for ang in (20, 45, 70):
            a = math.radians(ang)
            d = (sx * math.cos(a), 0, sz * math.sin(a))
            rl = hits(lid, (sx * 30.0, 51.0, sz * 30.0), d)[-1]
            rw = hits(hclip, (sx * 30.0, 52.5, sz * 30.0), d)[0]
            cg.append(rw - rl)
    note("side_clearance_corners (min, max) mm", (round(min(cg), 4), round(max(cg), 4)))
    assert min(cg) == pytest.approx(SIDE_CLEAR, abs=0.006) and max(cg) == pytest.approx(SIDE_CLEAR, abs=0.006)
    # bump tip width (flat tip) at the tip position, measured along the tangent at 0.01 below the tip
    for name, (n, t) in SIDES.items():
        idx = np.where(lidp[name] > BUMP_TIP_X - 0.01)[0]
        w = len(idx) * 0.05
        note(f"bump.tip_flat_width_{name}", round(w, 2))
        assert 0.4 <= w <= 0.8


def test_03c_interference_volume_is_four_bump_tips(lid, hclip):
    r = lid.intersect(hclip)
    ps = [(s.Volume(), exact_bb(s)) for s in pieces(r) if s.Volume() > 1e-12]
    big = [(v, b) for v, b in ps if v > 0.05]
    small = [(v, b) for v, b in ps if v <= 0.05]
    note("interference.pieces_total / tips(>0.05mm3) / slivers", (len(ps), len(big), len(small)))
    note("interference.tip_volumes_mm3", [round(v, 4) for v, _ in big])
    note("interference.sliver_volume_total_mm3", round(sum(v for v, _ in small), 5))
    note("interference.total_volume_mm3", round(sum(v for v, _ in ps), 4))
    assert len(big) == 4, "exactly four interference pieces expected (one per bump tip)"
    # analytic tip volume: wall -> tip, 0.15 deep, width 0.6 -> 0.81 (side slope 0.714), full height 1.4 + lead-in triangle
    slope = (0.8 - 0.3) / 0.7
    w_wall = 0.6 + 2 * slope * INTERF
    area = INTERF * 0.5 * (0.6 + w_wall)
    v_exp = area * 1.4 + 0.5 * INTERF * 0.15 * 0.5 * (0.6 + w_wall) * 0 + (0.5 * INTERF * INTERF * 0.5 * (0.6 + w_wall))
    note("interference.tip_volume_analytic_mm3 (approx)", round(v_exp, 4))
    for v, b in big:
        assert v == pytest.approx(v_exp, rel=0.15)
        x0, x1, y0, y1, z0, z1 = b
        depth = max(abs(x0), abs(x1), abs(z0), abs(z1)) - RECESS_HALF
        assert depth == pytest.approx(INTERF, abs=0.003)
        assert y0 >= SEAT_Y - 0.001 and y1 <= 51.8 + 0.001
    assert sum(v for v, _ in small) < 0.05, "residual contact slivers should be negligible"
    # distinct sides
    sides = set()
    for _, b in big:
        x0, x1, y0, y1, z0, z1 = b
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        sides.add("x" + ("+" if cx > 0 else "-") if abs(cx) > abs(cz) else "z" + ("+" if cz > 0 else "-"))
    note("interference.sides", sorted(sides))
    assert len(sides) == 4


def test_03d_plate_rests_on_the_ring_and_nothing_else_touches(lid, hclip):
    # the lid bottom plane vs the housing seat plane
    seat = hits(hclip, (41.5, 40.0, 0.0), (0, 1, 0))[0] + 40.0
    lid_y0 = exact_bb(lid)[2]
    note("seat_y(housing) / lid_bottom_y", (round(seat, 6), round(lid_y0, 6)))
    assert abs(seat - lid_y0) < 5e-5, "lid bottom plane must sit on the ring plane to within 0.05 um"
    v0 = vol(lid.intersect(hclip))
    # contact area: lower the lid by 0.02 mm -> the extra overlap is the seat contact area x 0.02 (bump-tip change is < 0.003 mm3)
    dl = 0.02
    v_down = vol(lid.translate(cq.Vector(0, -dl, 0)).intersect(hclip))
    area = (v_down - v0) / dl
    # analytic: ring under the plate = plate outline area - pocket area - ring covered by slots and notch
    c4 = 4 - math.pi
    covered = ((84.5 ** 2 - c4 * 12.25 ** 2) - (80.0 ** 2 - c4 * 10.0 ** 2))
    slots = 4 * (0.25 * 13.0 + 2.25 * 1.0 - 0.25 * 1.0)           # slot parts on the ring (z 40..42.25)
    notch = 14.0 * 2.25
    exp = covered - slots - notch
    note("seat_contact_area_mm2 (by 0.02 mm lowering / analytic)", (round(area, 1), round(exp, 1)))
    assert area == pytest.approx(exp, rel=0.02)
    # lift by 0.05: only the four tips remain
    r_up = lid.translate(cq.Vector(0, 0.05, 0)).intersect(hclip)
    ps = [s for s in pieces(r_up) if s.Volume() > 1e-9]
    note("pieces_after_lifting_0.05mm (count, total vol)", (len(ps), round(sum(s.Volume() for s in ps), 4)))
    assert len(ps) == 4 and sum(s.Volume() for s in ps) < 0.7


def test_03e_insertion_only_tips_touch(lid, hclip):
    """Lowering the lid from 4 mm above the seat: no contact above the rim plane; below it only the four tips."""
    worst_nontip = 0.0
    for dy in (4.0, 3.0, 2.0, 1.0, 0.5):
        r = lid.translate(cq.Vector(0, dy, 0)).intersect(hclip)
        ps = [s for s in pieces(r) if s.Volume() > 1e-9]
        note(f"insertion.dy={dy}", (len(ps), round(sum(s.Volume() for s in ps), 4)))
        assert len(ps) == 4, f"unexpected contact at lift {dy}"


# =====================================================================================================================================================
# 3b. arm / press-force estimate
# =====================================================================================================================================================
def _arm_geometry(lid):
    y = 51.0
    h = hits(lid, (5.0, y, 0.0), (0, 0, 1))
    assert len(h) == 3, f"expected slot start, arm start, edge at x=5; got {h}"
    z_slot0, z_arm0, z_edge = h
    t_arm = z_edge - z_arm0
    w_slot = z_arm0 - z_slot0
    # root: along x at the middle of the slot z, the slot ends at the root
    zc = 0.5 * (z_slot0 + z_arm0)
    hx = hits(lid, (0.0, y, zc), (1, 0, 0))
    hxm = hits(lid, (0.0, y, zc), (-1, 0, 0))
    x_root = hx[0]
    x_free_slot = -hxm[0]
    # bump centre: along x at z = 42.5 (between the plate edge and the tip)
    hb = hits(lid, (-20.0, y, 42.5), (1, 0, 0))
    assert len(hb) == 2, hb
    x_bump = -20.0 + 0.5 * (hb[0] + hb[1])
    # plate thickness at the arm
    hy = hits(lid, (5.0, 40.0, 41.2), (0, 1, 0))
    thick = hy[1] - hy[0]
    return dict(t_arm=t_arm, w_slot=w_slot, x_root=x_root, x_slot_end=x_free_slot, x_bump=x_bump, thick=thick, z_slot0=z_slot0)


def test_04b_cantilever_numbers(lid):
    g = _arm_geometry(lid)
    note("arm.geometry", {k: round(v, 4) for k, v in g.items()})
    assert g["t_arm"] == pytest.approx(2.0, abs=0.01) and g["w_slot"] == pytest.approx(1.0, abs=0.01) and g["thick"] == pytest.approx(1.8, abs=0.01)
    L = g["x_root"] - g["x_bump"]
    assert L == pytest.approx(8.0, abs=0.05)
    E = M.MATERIALS["PETG"]["youngs_modulus_GPa"] * 1000.0
    sy = M.MATERIALS["PETG"]["yield_MPa"]
    h, t, d = g["thick"], g["t_arm"], INTERF
    I = h * t ** 3 / 12.0
    k = 3 * E * I / L ** 3
    F = k * d
    eps = 3 * t * d / (2 * L ** 2)
    # Timoshenko shear flexibility (rectangular section kappa 5/6, G = E / 2(1+nu), nu 0.38)
    G = E / (2 * 1.38)
    flex = L ** 3 / (3 * E * I) + L / ((5.0 / 6.0) * G * h * t)
    F_sh = d / flex
    note("arm.k_N_per_mm / F_at_0.15 / strain_%", (round(k, 3), round(F, 3), round(100 * eps, 3)))
    note("arm.F_with_shear_flexibility_N", round(F_sh, 3))
    assert F == pytest.approx(2.2, abs=0.1) and 100 * eps == pytest.approx(0.70, abs=0.03)
    assert F_sh > 0.9 * F, "shear flexibility should be a few percent"
    # +-20 % on E (materials.py) and +-0.05 mm of printed size error
    lo, hi = 0.8 * k * (d - 0.05), 1.2 * k * (d + 0.05)
    note("arm.force_range_N (E +-20 %, interference 0.10..0.20)", (round(lo, 2), round(hi, 2)))
    # worst case: lid pushed to one wall, whole protrusion 0.40; sharp root corner (print rounds it to ~0.2 mm; Kt ~ 2 for this shoulder in bending)
    d_max = SIDE_CLEAR + INTERF
    eps_max = 3 * t * d_max / (2 * L ** 2)
    sig_nom_max = E * eps_max
    note("arm.worst_case_(0.40 mm)_force_N / nominal strain_% / nominal stress_MPa / yield_MPa", (round(k * d_max, 2), round(100 * eps_max, 2), round(sig_nom_max, 1), sy))
    note("arm.centred_nominal_stress_MPa / with Kt=2", (round(E * eps, 1), round(2 * E * eps, 1)))
    assert E * eps < 0.5 * sy                          # centred, nominal: below 50 % of yield
    assert E * eps * 2.0 < sy                          # centred, with a Kt=2 root corner: below yield
    # the PETG strain claim (0.7 %) is far below the yield strain sy/E = 2.1 %
    assert eps < 0.4 * sy / E


# =====================================================================================================================================================
# 4. clearances
# =====================================================================================================================================================
def _cyl(r, length, p, d):
    return cq.Solid.makeCylinder(r, length, cq.Vector(*p), cq.Vector(*d))


def _bores(housing):
    """Corner and T bores from the housing STEP's R1.0 cylinder faces: (name, point on axis, outward unit direction)."""
    out = {}
    for f in housing.Faces():
        if f.geomType() != "CYLINDER":
            continue
        c = f._geomAdaptor().Cylinder()
        if abs(c.Radius() - 1.0) > 1e-3:
            continue
        a = c.Axis()
        d = np.array([a.Direction().X(), a.Direction().Y(), a.Direction().Z()])
        p = np.array([a.Location().X(), a.Location().Y(), a.Location().Z()])
        if abs(p[1] - 42.0) < 0.1:                                 # T hole (horizontal, y = 42): outward = away from the tube axis
            if np.dot(d, np.array([p[0], 0, p[2]])) < 0:
                d = -d
            key = "T@(%+.0f,%+.0f)" % (round(d[0] * 100) / 100 * 100, round(d[2] * 100))
        else:                                                      # corner hole: outward in x, z
            if d[0] * p[0] < 0:
                d = -d
            key = "corner(%+d,%+d)" % (np.sign(p[0]), np.sign(p[2]))
        out[key] = (p, d)
    return out


def test_05a_corner_and_T_bores_and_lines(lid, housing):
    bores = _bores(housing)
    note("bores_found", sorted(bores))
    assert sum(1 for k in bores if k.startswith("corner")) == 4 and sum(1 for k in bores if k.startswith("T@")) == 3
    res = {}
    for k, (p, d) in bores.items():
        cyl = _cyl(1.0, 400.0, p, d)
        res[k + " bore"] = round(lid.distance(cyl), 2)
    note("clearance.bores_to_lid_mm", res)
    assert min(res.values()) >= 5.0
    # T lines: from the outer mouth (axis meets the 45 mm wall plane) rising 15..90 deg in the vertical plane of the axis, radius 0.5
    lines = {}
    for k, (p, d) in bores.items():
        if not k.startswith("T@"):
            continue
        nrm = np.array([np.sign(d[0]), 0, 0]) if abs(d[0]) > abs(d[2]) else np.array([0, 0, np.sign(d[2])])
        t_out = (45.0 - np.dot(p, nrm)) / np.dot(d, nrm)
        mouth = p + d * t_out
        for el in (0, 15, 30, 45, 60, 75, 90):
            e = math.radians(el)
            dd = d * math.cos(e) + np.array([0, 1, 0]) * math.sin(e)
            cyl = _cyl(0.5, 400.0, mouth, dd)
            lines[(k, el)] = round(lid.distance(cyl), 2)
    byel = {el: min(v for (k, e), v in lines.items() if e == el) for el in (0, 15, 30, 45, 60, 75, 90)}
    note("clearance.T_lines_min_over_3_holes_by_elevation_deg_(surface to lid, mm)", byel)
    for el in (0, 15, 30, 45, 60):
        assert byel[el] >= 5.0, f"line at {el} deg closer than 5 mm to the lid"
    # steep lines (75, 90 deg) are inside 5 mm of the lid by construction: the lid stays inside the 45 mm wall plane
    note("clearance.steep_lines_(75, 90 deg)_below_5mm_literal_keepout", (byel[75] < 5.0, byel[90] < 5.0))
    bb = exact_bb(lid)
    assert max(abs(bb[0]), abs(bb[1]), abs(bb[4]), abs(bb[5])) < 45.0 - 2.0, "lid must stay well inside the 45 mm outer wall plane"


def test_05b_steep_lines_are_limited_by_the_housing_rim_not_the_lid(lid, housing):
    """For the 75 and 90 degree lines (the literal 5 mm keep-out cannot hold against the lid), the housing's own rim top edge is closer, so the lid
    is never the limiting object (a line that leaves the wall plane cannot enter the 2.35 mm gap behind the wall)."""
    bores = _bores(housing)
    rim_band = housing.intersect(box(-60, 60, 54.9, 55.1, -60, 60))
    out = {}
    for k, (p, d) in bores.items():
        if not k.startswith("T@"):
            continue
        nrm = np.array([np.sign(d[0]), 0, 0]) if abs(d[0]) > abs(d[2]) else np.array([0, 0, np.sign(d[2])])
        mouth = p + d * ((45.0 - np.dot(p, nrm)) / np.dot(d, nrm))
        for el in (75, 83, 90):
            e = math.radians(el)
            dd = d * math.cos(e) + np.array([0, 1, 0]) * math.sin(e)
            cyl = _cyl(0.5, 400.0, mouth, dd)
            out[(k, el)] = (round(lid.distance(cyl), 2), round(rim_band.distance(cyl), 2))
    note("clearance.steep_lines (lid, housing rim) mm", {f"{k}/{e}": v for (k, e), v in out.items()})
    for key, (dl, dr) in out.items():
        assert dr <= dl + 1e-6, f"{key}: the lid would be closer to the cable than the rim"


def test_05c_camera_bay_cover(lid, cover):
    d = lid.distance(cover)
    ov = vol(lid.intersect(cover))
    note("clearance.lid_to_cover_mm / overlap_mm3", (round(d, 3), round(ov, 6)))
    assert ov < 1e-9 and d >= 5.0


def test_05d_pry_notch_reaches_open_space(lid, hclip, housing):
    # notch geometry from the lid: along x at z = 41 and y = 51, the void between the notch walls; then depth along z at x = -20
    h = hits(lid, (-35.0, 51.0, 41.0), (1, 0, 0))
    note("notch.hits_along_x_at_z=41", [round(-35.0 + v, 3) for v in h])
    x_a, x_b = -35.0 + h[0], -35.0 + h[1]
    assert x_b - x_a == pytest.approx(14.0, abs=0.05) and 0.5 * (x_a + x_b) == pytest.approx(-20.0, abs=0.05)
    hz = hits(lid, (-20.0, 51.0, 30.0), (0, 0, 1))
    z_in = 30.0 + hz[0]
    note("notch.inner_wall_z / depth_from_plate_edge_(42.25)", (round(z_in, 3), round(PLATE_HALF - z_in, 3)))
    assert PLATE_HALF - z_in == pytest.approx(4.5, abs=0.02)
    # the part of the notch that lies over the open pocket (z < 40): the lid is absent and so is the housing, all the way down to the pocket floor
    free = []
    floors = set()
    for x in np.linspace(x_a + 2.1, x_b - 2.1, 5):
        for z in np.linspace(z_in + 0.15, 39.85, 4):
            up = hits(lid, (x, 40.0, z), (0, 1, 0))                         # lid above the pocket here? (none expected: that is the notch)
            down = hits(housing, (x, 49.9, z), (0, -1, 0))                  # whole housing below: only the pocket floor (y = 5) may be hit
            free.append((len(up), len(down)))
            if down:
                floors.add(round(49.9 - down[0], 3))
    note("notch.open_columns: (lid hits above, housing hits below) all (0, 2) = pocket floor top y=5 and bottom y=0; first housing hit y", (sorted(set(free)), sorted(floors)))
    assert all(a == 0 and b == 2 for a, b in free) and floors == {5.0}, "column under the notch must be empty down to the pocket floor at y = 5"
    width_over_void = 40.0 - z_in
    note("notch.width_over_the_open_pocket_mm", round(width_over_void, 3))
    assert width_over_void >= 2.0
    # a 8 x 1 mm blade pushed straight down through that part of the notch touches nothing (lid or housing) down to y = 8
    blade = box(-20 - 4, -20 + 4, 8.0, 56.0, 38.2, 39.2)
    assert vol(lid.intersect(blade)) < 1e-9 and vol(hclip.intersect(blade)) < 1e-9
    # the notch stays clear of the +z arm slot (x from -3): notch right edge at -13, 10 mm of plate between them
    assert x_b < -3.0 - 5.0 and x_a > -30.0 + 1.0, "notch vs arm slot / corner start"


# =====================================================================================================================================================
# 5. printability (STL, print pose)
# =====================================================================================================================================================
def read_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[80:84])[0]
    assert len(data) == 84 + 50 * n, "binary STL expected"
    arr = np.frombuffer(data[84:], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n)
    return arr["v"].astype(float), arr["n"].astype(float)


def mesh_stats(tri):
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    cr = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0
    return cr, area, vol


@pytest.fixture(scope="module")
def stl():
    tri, nrm = read_stl(LID_STL)
    return tri, nrm


def test_06a_stl_watertight_volume_orientation(stl, lid):
    tri, _ = stl
    cr, area, v = mesh_stats(tri)
    # watertight: every undirected edge shared by exactly two triangles (vertices merged at 1e-4)
    keys = np.round(tri.reshape(-1, 3) / 1e-4).astype(np.int64)
    uniq, inv = np.unique(keys, axis=0, return_inverse=True)
    f = inv.reshape(-1, 3)
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    note("stl.triangles / unique_vertices / edges_with_count!=2", (len(tri), len(uniq), int((cnt != 2).sum())))
    assert (cnt != 2).sum() == 0, "STL not watertight (every edge must have exactly two triangles)"
    note("stl.volume_mm3 / step_volume_mm3 / ratio", (round(v, 1), round(lid.Volume(), 1), round(v / lid.Volume(), 5)))
    assert v == pytest.approx(lid.Volume(), rel=0.005)
    mn, mx = tri.reshape(-1, 3).min(axis=0), tri.reshape(-1, 3).max(axis=0)
    note("stl.bbox", [round(float(x), 3) for x in (*mn, *mx)])
    assert np.allclose(mn, 0.0, atol=1e-3) and mx[0] == pytest.approx(85.3, abs=0.01) and mx[1] == pytest.approx(85.3, abs=0.01) and mx[2] == pytest.approx(1.8, abs=0.005)
    # bed face (z = 0) area: top face minus slots, notch and chamfer
    nz = cr[:, 2] / np.maximum(2 * area, 1e-18)
    bed = (np.abs(tri[:, :, 2]).max(axis=1) < 1e-4) & (nz < -0.999)
    note("stl.bed_face_area_mm2 (z=0, facing down)", round(float(area[bed].sum()), 1))
    assert area[bed].sum() > 6000.0
    # the underside (seat face) is the z = 1.8 plane, facing up
    top = (np.abs(tri[:, :, 2] - 1.8).min(axis=1) < 1e-4) & (np.abs(tri[:, :, 2] - 1.8).max(axis=1) < 1e-4) & (nz > 0.999)
    assert area[top].sum() > 600.0
    # the STL is the same part as the STEP: compare the print pose to the STEP by a few vertex-in-solid probes (x -> x, y -> -z', z -> y' mapping)
    # print pose = rotate about +x by -90 deg then shift: (x, y, z)_bay -> (x - xmin, ?, ?) ; check volume and bbox only (done above) plus the bed-face count


def test_06b_overhangs(stl):
    tri, _ = stl
    cr, area, _ = mesh_stats(tri)
    nz = cr[:, 2] / np.maximum(2 * area, 1e-18)
    z = tri[:, :, 2]
    on_bed = z.max(axis=1) < 1e-4
    down = (nz < -1e-6) & ~on_bed & (area > 1e-9)
    ang = np.degrees(np.arcsin(np.clip(-nz[down], 0, 1)))               # overhang angle measured from vertical: 0 = vertical wall, 90 = horizontal ceiling
    note("overhang.downward_facing_area_mm2 (not on bed)", round(float(area[down].sum()), 3))
    if down.any():
        note("overhang.max_angle_from_vertical_deg", round(float(ang.max()), 2))
        note("overhang.area_steeper_than_45.5_deg", round(float(area[down][ang > 45.5].sum()), 4))
        # the only downward faces are the 0.3 x 45 deg top-edge chamfer on the bed edge (z 0 .. 0.3)
        zz = z[down]
        note("overhang.downward_faces_z_range", (round(float(zz.min()), 3), round(float(zz.max()), 3)))
        assert area[down][ang > 45.5].sum() < 1e-3
    # no downward-facing face above z = 0.31 at all
    assert not (down & (z.min(axis=1) > 0.31)).any()


def _slice_mask(tri, zc, res):
    """Rasterise the solid cross-section at height zc (mm) at res mm/pixel by even-odd filling of the slice polylines."""
    import cv2
    t = tri
    z = t[:, :, 2]
    sel = (z.min(axis=1) < zc) & (z.max(axis=1) > zc)
    segs = []
    for tr in t[sel]:
        pts = []
        for i in range(3):
            a, b = tr[i], tr[(i + 1) % 3]
            if (a[2] - zc) * (b[2] - zc) < 0:
                s = (zc - a[2]) / (b[2] - a[2])
                pts.append(a[:2] + s * (b[:2] - a[:2]))
        if len(pts) == 2:
            segs.append(pts)
    # chain segments into loops
    from collections import defaultdict
    key = lambda p: (round(p[0] / 1e-4), round(p[1] / 1e-4))
    adj = defaultdict(list)
    for a, b in segs:
        adj[key(a)].append((key(b), b))
        adj[key(b)].append((key(a), a))
    loops, used = [], set()
    pt = {}
    for a, b in segs:
        pt[key(a)] = a
        pt[key(b)] = b
    for start in list(adj):
        if start in used:
            continue
        loop, cur, prev = [start], start, None
        used.add(start)
        while True:
            nxt = [k for k, _ in adj[cur] if k != prev and k not in used]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            used.add(cur)
            loop.append(cur)
        loops.append(np.array([pt[k] for k in loop]))
    h = int(math.ceil(88.0 / res))                                   # 1 mm margin all round: the morphology must not see the image border
    img = np.zeros((h, h), np.uint8)
    # even-odd: XOR each loop's filled polygon
    for lp in loops:
        m = np.zeros_like(img)
        cv2.fillPoly(m, [np.round((lp + 1.0) / res).astype(np.int32).reshape(-1, 1, 2)], 1)
        img ^= m
    return img


THIN_AREA = 0.05      # mm2: opening a sharp 90 deg corner with a 0.2 mm radius disc removes ~0.011 mm2 (corner clipping, not a thin feature); a thin wall removes far more


def _max_component_area(mask, res):
    import cv2
    n, _, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    return max([st[i, cv2.CC_STAT_AREA] * res * res for i in range(1, n)] or [0.0])


def test_06c0_thin_feature_detector_self_check():
    """The opening/closing detector must flag a 0.30 mm wall and a 0.30 mm gap and must not flag a 0.60 mm wall (sharp-corner clips stay below THIN_AREA)."""
    import cv2
    res = 0.02
    k = int(round(MIN_FEATURE / res)) | 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k - 2, k - 2))
    for w, expect in ((0.30, True), (0.60, False)):
        img = np.zeros((600, 600), np.uint8)
        img[100:100 + int(round(5.0 / res)), 100:100 + int(round(w / res))] = 1
        img[300:340, 300:500] = 1
        opened = cv2.morphologyEx(img, cv2.MORPH_OPEN, ker)
        removed = (img.astype(np.int16) - opened.astype(np.int16)) > 0
        assert (_max_component_area(removed, res) > THIN_AREA) == expect, (w, _max_component_area(removed, res))
    img = np.ones((400, 400), np.uint8)
    img[100:300, 150:150 + int(round(0.30 / res))] = 0              # a 0.30 mm gap
    closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, ker)
    assert _max_component_area((closed.astype(np.int16) - img.astype(np.int16)) > 0, res) > THIN_AREA


def test_06c_minimum_feature_widths(stl):
    import cv2
    tri, _ = stl
    res = 0.02
    k_solid = int(round(MIN_FEATURE / res)) | 1                       # odd kernel ~0.45 mm
    out = {}
    for zc in (0.1, 0.5, 0.9, 1.3, 1.45, 1.6, 1.75):
        img = _slice_mask(tri, zc, res)
        area0 = img.sum() * res * res
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_solid - 2, k_solid - 2))        # slightly under 0.45 to avoid pixel-quantisation false alarms
        opened = cv2.morphologyEx(img, cv2.MORPH_OPEN, ker)
        removed = (img.astype(np.int16) - opened.astype(np.int16)) > 0
        n, labels, stats, cent = cv2.connectedComponentsWithStats(removed.astype(np.uint8), connectivity=8)
        big = [(stats[i, cv2.CC_STAT_AREA] * res * res, cent[i] * res) for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] * res * res > THIN_AREA]
        n_corner = sum(1 for i in range(1, n) if 0.003 < stats[i, cv2.CC_STAT_AREA] * res * res <= THIN_AREA)
        # voids (slots, gaps): close the solid and see what disappears -> a void thinner than 0.45
        closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, ker)
        added = (closed.astype(np.int16) - img.astype(np.int16)) > 0
        n2, l2, s2, c2 = cv2.connectedComponentsWithStats(added.astype(np.uint8), connectivity=8)
        bigv = [(s2[i, cv2.CC_STAT_AREA] * res * res, c2[i] * res) for i in range(1, n2) if s2[i, cv2.CC_STAT_AREA] * res * res > THIN_AREA]
        out[zc] = {"section_area_mm2": round(float(area0), 1), "thin_solid_regions": len(big), "thin_void_regions": len(bigv), "sharp_corner_clips_(ignored)": n_corner,
                   "thin_solid_xy": [(round(float(a), 3), tuple(round(float(v), 2) for v in c)) for a, c in big[:4]]}
    note("minfeature.by_print_height_z_mm", out)
    for zc, r in out.items():
        assert r["thin_solid_regions"] == 0, f"solid feature thinner than 0.45 mm at z={zc}: {r}"
        assert r["thin_void_regions"] == 0, f"void thinner than 0.45 mm at z={zc}"


def test_06d_bump_geometry_for_printing(lid):
    """Tip width, protrusion by height (lead-in), and whether the bump tip has the same top-edge relief as the plate (elephant foot on the bed)."""
    n, t = SIDES["+z"]
    rows = {}
    for y in (50.05, 50.1, 50.2, 50.3, 50.4, 50.6, 51.0, 51.5, 51.7, 51.78):
        h = hits(lid, (2.0, y, 60.0), (0, 0, -1))
        rows[y] = round(60.0 - h[0], 4)
    note("bump.protrusion_position_vs_y_(+z side, x=2)", rows)
    # lead-in 45 deg: tip position grows 1:1 with y from 50 to 50.4 beyond the plate edge 42.25
    assert rows[50.2] - PLATE_HALF == pytest.approx(0.2, abs=0.01) and rows[50.4] == pytest.approx(BUMP_TIP_X, abs=0.01)
    # full height up to the top face: no chamfer / relief on the bump tip (elephant-foot relief only on the plate edge)
    note("bump.tip_position_at_y=51.78 (top face, the bed face when printed)", rows[51.78])
    top_relieved = rows[51.78] < BUMP_TIP_X - 0.02
    note("bump.tip_has_top_edge_relief", top_relieved)
    # plate edge at the same height (at x = -20, away from bumps)
    hp = hits(lid, (-8.0, 51.78, 60.0), (0, 0, -1))
    note("plate.edge_position_at_y=51.78 (0.3 x 45 deg chamfer: expect 42.25 - 0.28)", round(60.0 - hp[0], 4))
    assert 60.0 - hp[0] == pytest.approx(PLATE_HALF - 0.28, abs=0.01), "plate top-edge chamfer 0.3 x 45 deg present"



@pytest.mark.xfail(strict=True, reason="FINDING F1: the bump tips run full height to the top (bed) face with no top-edge relief, so first-layer elephant foot "
                   "adds to the 0.15 mm interference there; only the plate edge has the 0.3 x 45 deg chamfer")
def test_06e_bump_tip_has_bed_edge_relief(lid):
    h = hits(lid, (2.0, 51.78, 60.0), (0, 0, -1))
    assert 60.0 - h[0] < BUMP_TIP_X - 0.1


# =====================================================================================================================================================
# 6. STEP round trip and export currency
# =====================================================================================================================================================
def test_07a_step_round_trip(lid_world, tmp_path):
    p = str(tmp_path / "rt.step")
    cq.exporters.export(cq.Workplane("XY").add(lid_world), p)
    back = cq.importers.importStep(p).val()
    b0, b1 = exact_bb(lid_world), exact_bb(back)
    note("roundtrip.volume (orig, back)", (round(lid_world.Volume(), 4), round(back.Volume(), 4)))
    note("roundtrip.bbox_max_dev_mm", float(max(abs(a - b) for a, b in zip(b0, b1))))
    assert len(back.Solids()) == 1 and back.isValid()
    assert back.Volume() == pytest.approx(lid_world.Volume(), rel=1e-6)
    assert max(abs(a - b) for a, b in zip(b0, b1)) < 1e-5
    assert len(back.Faces()) == len(lid_world.Faces())
    assert back.Area() == pytest.approx(lid_world.Area(), rel=1e-6)


def test_07b_export_is_current_with_builder(lid_world):
    """Stale-export check: rebuild with the builder (intentional exception to the independence rule) and compare volume, area, bbox and face count."""
    from cad.parts import gripper1021_housing_lid as B
    fresh = B.to_world(B.make_lid().val())
    note("stale_check.volume (export, fresh)", (round(lid_world.Volume(), 4), round(fresh.Volume(), 4)))
    assert fresh.Volume() == pytest.approx(lid_world.Volume(), rel=1e-6)
    assert fresh.Area() == pytest.approx(lid_world.Area(), rel=1e-6)
    assert max(abs(a - b) for a, b in zip(exact_bb(fresh), exact_bb(lid_world))) < 1e-4
    assert len(fresh.Faces()) == len(lid_world.Faces())
