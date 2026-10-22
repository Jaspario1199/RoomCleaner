"""
Acceptance checks for the Gripper 1021 housing LID (cad/parts/gripper1021_housing_lid.py, params LID1021_*).

The opening and seat are MEASURED from exports/step/gripper1021_housing_cambay_34.step (bay frame = world minus CAMBAY1021_BAY_ORIGIN_WORLD;
the STEP's own 1e-5 mm placement residual is removed by the loader, the raw frame is checked too).  Everything is measured on the built B-rep
solids / exported files (ray probes, booleans, distances).  Run with /usr/bin/python3 -m pytest tests/test_gripper1021_housing_lid.py
"""

from __future__ import annotations

import math
import os
import struct
import sys

import pytest

cq = pytest.importorskip("cadquery")

import numpy as np                                               # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier          # noqa: E402
from OCP.TopAbs import TopAbs_IN                                  # noqa: E402
from OCP.gp import gp_Pnt                                         # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import gripper1021_housing_lid as L               # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(L.HOUSING_STEP), reason="housing STEP not available")

C0 = L.Cfg()
TOL = 1e-3                          # mm3: a true face contact leaves less than this


# ---------------------------------------------------------------------------------------------------------------------
class Probe:
    """Point-in-solid classifier with ray search for the first in/out change."""

    def __init__(self, shape):
        s = shape.Solids()
        self.c = BRepClass3d_SolidClassifier((s[0] if len(s) == 1 else shape).wrapped)

    def inside(self, p) -> bool:
        self.c.Perform(gp_Pnt(float(p[0]), float(p[1]), float(p[2])), 1e-7)
        return self.c.State() == TopAbs_IN

    def boundary(self, p0, d, rmax, step=0.02):
        p0, d = np.array(p0, float), np.array(d, float)
        d = d / np.linalg.norm(d)
        s0 = self.inside(p0)
        t = 0.0
        while t < rmax:
            t2 = min(t + step, rmax)
            if self.inside(p0 + d * t2) != s0:
                lo, hi = t, t2
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    if self.inside(p0 + d * mid) != s0:
                        hi = mid
                    else:
                        lo = mid
                return 0.5 * (lo + hi)
            t = t2
        return None


def rot(x, z, deg):
    """Rotate the plan point (x, z) about +y by deg (same convention as the part: x' = x cos + z sin, z' = -x sin + z cos)."""
    a = math.radians(deg)
    return (x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a))


def _vol(a, b) -> float:
    r = a.intersect(b)
    return r.Volume() if r is not None else 0.0


def _pieces(shape):
    return [s for s in shape.Solids() if s.Volume() > 1e-9]


def _bb(sh):
    b = sh.BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


@pytest.fixture(scope="module")
def lid():
    return L.make_lid().val()


@pytest.fixture(scope="module")
def bare():
    return L.make_lid(bumps=False).val()


@pytest.fixture(scope="module")
def housing():
    return L.load_housing(True)


@pytest.fixture(scope="module")
def housing_raw():
    return L.load_housing(False)


@pytest.fixture(scope="module")
def cover():
    return L.load_cover()


@pytest.fixture(scope="module")
def pl(lid):
    return Probe(lid)


@pytest.fixture(scope="module")
def ph(housing):
    return Probe(housing)


# =====================================================================================================================
# the opening and the seat, measured from the housing STEP
# =====================================================================================================================
def test_opening_and_seat_measured_from_the_step(housing_raw):
    m = L.measure_opening(housing_raw)
    print({k: round(v, 6) for k, v in m.items()})
    assert m["seat_y"] == pytest.approx(P.LID1021_SEAT_Y, abs=1e-3) and m["rim_y"] == pytest.approx(P.LID1021_RIM_Y, abs=1e-3)
    assert m["recess_half_x"] == pytest.approx(P.LID1021_RECESS_HALF, abs=1e-3) and m["recess_half_z"] == pytest.approx(P.LID1021_RECESS_HALF, abs=1e-3)
    assert abs(m["centre_x"]) < 1e-3 and abs(m["centre_z"]) < 1e-3                  # on the tube axis
    assert m["recess_r"] == pytest.approx(P.LID1021_RECESS_R, abs=1e-3) and m["corner_c"] == pytest.approx(P.LID1021_RECESS_CORNER_C, abs=1e-3)
    assert m["pocket_half"] == pytest.approx(P.LID1021_POCKET_HALF, abs=1e-3) and m["pocket_r"] == pytest.approx(P.LID1021_POCKET_R, abs=1e-3)
    # spec text: "lid seat at y 1141.2, top at y 1146.19" = box frame 50.0 / 55.0, and CAMBAY1021_TRI_LID_RECESS_HALF = 42.5
    assert P.CAMBAY1021_BOX_LID_SEAT_Y == P.LID1021_SEAT_Y and P.CAMBAY1021_BOX_TOP_Y == P.LID1021_RIM_Y
    assert P.CAMBAY1021_TRI_LID_RECESS_HALF == P.LID1021_RECESS_HALF
    # the seat is a ring 2.5 mm wide between pocket and recess; below it the pocket is open (no floor under the middle of the lid)
    ph = Probe(housing_raw)
    assert not ph.inside((0.0, 49.9, 0.0)) and not ph.inside((39.0, 49.9, 0.0)) and ph.inside((41.0, 49.9, 0.0)) and not ph.inside((41.0, 50.05, 0.0))
    assert not ph.inside((0.0, 20.0, 0.0))


def test_nothing_else_stands_in_the_recess(housing):
    """No feature of the housing between the seat plane and the rim inside the recess outline (so the lid has the whole opening)."""
    void = (cq.Workplane(L._plane_y(50.01)).rect(2 * 42.4, 2 * 42.4).extrude(4.98).edges("|Y").fillet(12.4)).val()      # recess outline, 0.1 inside
    assert _vol(void, housing) < TOL


# =====================================================================================================================
# the lid
# =====================================================================================================================
def test_lid_is_one_valid_solid_with_the_expected_envelope(lid):
    assert lid.isValid() and len(lid.Solids()) == 1
    x0, x1, y0, y1, z0, z1 = _bb(lid)
    tip = C0.H + C0.bump_p
    assert (x0, x1, z0, z1) == pytest.approx((-tip, tip, -tip, tip), abs=1e-3)               # bump tips at +-42.65
    assert y0 == pytest.approx(50.0, abs=1e-6) and y1 == pytest.approx(51.8, abs=1e-6)
    v = lid.Volume()
    print("lid volume %.1f mm3, %.2f g PETG, bbox %.2f x %.2f x %.2f" % (v, v * P.LID1021_PETG_G_CM3 / 1000, x1 - x0, y1 - y0, z1 - z0))
    assert 11000 < v < 13500
    assert v * P.LID1021_PETG_G_CM3 / 1000 < 18.0                                            # light: about 16 g


def test_plate_thickness_seat_contact_and_outline(pl, lid, bare, housing):
    # plate: bottom on the seat plane, top 1.8 above, solid between
    assert pl.inside((20.0, 50.05, 20.0)) and pl.inside((20.0, 51.75, 20.0)) and not pl.inside((20.0, 49.95, 20.0)) and not pl.inside((20.0, 51.85, 20.0))
    # outline on a free stretch of each side (x = -8 in the side's own frame: clear of the arm at x -3 .. 10 and of the notch at -27 .. -13)
    for ang in (0, 90, 180, 270):
        x, z = rot(-8.0, 30.0, ang)
        d = rot(0.0, 1.0, ang)
        assert 30.0 + pl.boundary((x, 50.9, z), (d[0], 0, d[1]), 20.0) == pytest.approx(42.25, abs=0.005), ang        # recess wall 42.5 - 0.25
    # corners R12.25 concentric with the recess's R12.5: diagonal extent 30 sqrt2 + 12.25
    diag = pl.boundary((0.0, 50.9, 0.0), (1, 0, 1), 80.0, 0.05)
    assert diag == pytest.approx(30 * math.sqrt(2) + 12.25, abs=0.01)
    # top edge chamfer 0.3 x 45 deg: 0.05 below the top the outline is 0.25 inside the edge
    edge = pl.boundary((0.0, 51.75, 20.0), (1, 0, 0), 60.0, 0.02)
    assert edge == pytest.approx(42.25 - 0.3 + 0.05, abs=0.01)
    # face contact with the seat ring, nothing more
    assert _vol(bare, housing) < TOL
    assert bare.distance(housing) == pytest.approx(0.0, abs=1e-6)
    assert bare.translate(cq.Vector(0, 0.02, 0)).distance(housing) == pytest.approx(0.02, abs=1e-4)
    assert _vol(bare.translate(cq.Vector(0, -0.02, 0)), housing) > 1.0                        # it really rests on the ring (the seat stops it)
    # ... and the plate is over the ring on every side: 2.25 mm of its 2.5 mm width
    ring = housing.intersect(cq.Workplane("XY").box(100, 0.2, 100, centered=False).translate((-50, 49.8, -50)).val())
    covered = _vol(bare.translate(cq.Vector(0, -0.1, 0)), ring) / 0.1                       # plan area of the plate over the seat ring (ring: 776.7 mm2)
    print("plate covers %.0f of the 777 mm2 seat ring" % covered)
    assert 600.0 < covered < 777.0


def test_four_crush_bumps_interference_is_the_press_fit_only(lid, housing, bare):
    common = lid.intersect(housing)
    pieces = _pieces(common)
    print("lid / housing interference: %d pieces, %.3f mm3 total" % (len(pieces), common.Volume()))
    assert len(pieces) == 4
    for k, ang in enumerate((0, 90, 180, 270)):
        x, z = rot(C0.x_bump, C0.rh + 0.07, ang)                                              # the crush sliver sits 0.07 beyond the wall line
        assert sum(1 for p in pieces if math.hypot(p.Center().x - x, p.Center().z - z) < 0.3) == 1, ang
    assert all(p.Volume() == pytest.approx(0.157, abs=0.01) for p in pieces)                  # 0.15 deep, ~0.8 wide, 1.4 high (after the lead-in)
    assert common.Volume() < 1.0
    # the housing is otherwise untouched: without the bumps nothing overlaps, and no other station part is anywhere near the lid
    assert _vol(bare, housing) < TOL


def test_bump_tips_are_beyond_the_wall_by_the_interference_and_at_least_0_45_wide(pl, ph):
    for ang in (0, 90, 180, 270):
        x0, z0 = rot(C0.x_bump, 41.0, ang)                                                    # start inside the arm (z 40.25 .. 42.25)
        d = rot(0.0, 1.0, ang)
        for y in (50.5, 51.0, 51.7):                                                           # above the lead-in
            tip = 41.0 + pl.boundary((x0, y, z0), (d[0], 0, d[1]), 20.0, 0.01)
            wall = 41.0 + ph.boundary((x0, y, z0), (d[0], 0, d[1]), 20.0, 0.01)
            assert tip == pytest.approx(C0.H + C0.bump_p, abs=0.005) and wall == pytest.approx(42.5, abs=0.005), (ang, y)
            assert tip - wall == pytest.approx(P.LID1021_INTERF, abs=0.006)                    # 0.15 mm of press-fit
        # tip width along the edge, just inside the tip
        p0 = rot(C0.x_bump, C0.H + C0.bump_p - 0.01, ang)
        t = rot(1.0, 0.0, ang)                                                                 # along the edge
        half = min(pl.boundary((p0[0], 51.0, p0[1]), (t[0], 0, t[1]), 2.0, 0.005), pl.boundary((p0[0], 51.0, p0[1]), (-t[0], 0, -t[1]), 2.0, 0.005))
        assert 2 * half >= 0.45 and 2 * half == pytest.approx(P.LID1021_BUMP_TIP, abs=0.03), (ang, half)


def test_bump_lead_in_on_the_underside(pl):
    """The lid goes in underside first: the bump grows from the plate edge to its full tip over 0.40 mm of height at 45 deg."""
    x0 = C0.x_bump
    for dy, expect in ((0.05, 0.05), (0.2, 0.2), (0.35, 0.35), (0.45, 0.40), (1.0, 0.40)):
        tip = pl.boundary((x0, 50.0 + dy, 41.0), (0, 0, 1), 20.0, 0.005) + 41.0
        assert tip - C0.H == pytest.approx(expect, abs=0.01), dy


def test_four_arms_are_free_cantilevers(pl):
    """Each arm: 2.0 wide, freed by an L-shaped 1.0 slot (inboard side + free end), solid at its root."""
    y = 50.9
    for ang in (0, 90, 180, 270):
        def at(x, z):
            px, pz = rot(x, z, ang)
            return pl.inside((px, y, pz))
        assert at(4.0, 41.25) and at(11.0, 41.0) and at(11.0, 38.0)                           # arm, root region, plate beyond the root
        assert not at(4.0, 39.75) and not at(0.0, 39.75) and not at(9.5, 39.75)               # inboard slot
        assert not at(-2.5, 41.0) and not at(-2.5, 39.5) and at(-3.5, 41.0) and at(-3.5, 39.5)  # free-end slot, plate beyond it
        assert at(-1.0, 41.0) and at(0.0, 40.5)                                               # arm free end is the arm
    assert Probe(L.make_lid().val()).inside((0.0, 50.9, 0.0))


def test_arm_hand_calculation():
    e = L.arm_estimate()
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items()})
    assert e["L_mm"] == pytest.approx(8.0) and e["I_mm4"] == pytest.approx(1.2)
    assert 1.5 < e["F_nominal_N"] < 3.0 and e["F_max_N"] < 7.0                                  # about 2 N per bump, 5.9 N if the lid is pushed to one side
    assert e["strain_nominal_pct"] < 1.0 and e["strain_max_pct"] < 2.0                          # in the layer plane, PETG
    assert e["retention_over_weight"] > 10 and e["retention_N"] < 10.0                          # holds the lid, still pulls off by hand
    lo, hi = e["F_at_interference_range_N"]
    assert lo > 1.0                                                                             # still gripped if the printed interference is 0.05 short
    # a rigid plate could not be pressed in: why the bumps sit on arms (Euler buckling of the strip between two opposite bumps)
    E_, I_plate = P.LID1021_PETG_E_MPA, 84.5 * 1.8 ** 3 / 12
    f_buckle = math.pi ** 2 * E_ * I_plate / 84.5 ** 2
    f_rigid = E_ * (84.5 * 1.8) / 84.5 * 2 * P.LID1021_INTERF                                   # axial force for 2 x 0.15 mm of shortening
    assert f_rigid > 5 * f_buckle


def test_pry_notch_reaches_under_the_plate(pl, ph, lid, housing):
    """14 x 4.5 mm notch on the +z side; 2.25 mm of it is past the seat ring (z < 40), over the open pocket, so a blade gets under the plate edge."""
    y = 50.9
    z_in = C0.H - C0.notch_d
    assert not pl.inside((-20.0, y, 41.0)) and not pl.inside((-20.0, y, z_in + 0.3)) and pl.inside((-20.0, y, z_in - 0.3))
    for dx in (-6.5, 6.5):
        assert not pl.inside((-20.0 + dx, y, 41.5)) and pl.inside((-20.0 + dx * 1.1, y, 41.5))
    assert pl.boundary((-20.0, y, 30.0), (0, 0, 1), 20.0, 0.01) + 30.0 == pytest.approx(z_in, abs=0.01)
    assert z_in < P.LID1021_POCKET_HALF - 2.0 + 1e-9                                           # 37.75: 2.25 mm past the ring's inner edge at 40
    assert not ph.inside((-20.0, 49.9, 38.5)) and ph.inside((-20.0, 49.9, 41.0))                # void under the notch's inner part, ring under its outer part
    # a 8 x 1 mm blade can be pushed straight down through the notch into the pocket: no contact with lid or housing
    blade = cq.Workplane("XY").box(8.0, 14.0, 1.0, centered=False).translate((-24.0, 42.0, 38.2)).val()
    assert _vol(blade, lid) < TOL and _vol(blade, housing) < TOL
    # the notch is clear of the arms and of the corner
    assert abs(C0.notch_x) + C0.notch_w / 2 <= 30.0 - 1.0


def test_clear_of_every_cable_hole_and_line_and_the_camera_bay_cover(lid, cover, housing):
    d_min = {}
    for name, sol in L.keepout_solids().items():
        d_min[name] = lid.distance(sol)
    worst = min(d_min, key=d_min.get)
    print("closest cable keep-out to the lid: %s at %.2f mm (limit %.1f)" % (worst, d_min[worst], P.LID1021_KEEPOUT))
    assert len(d_min) == 4 + 3 + 3 * 6                                                           # corner holes, T_A/T_B/T_C bores, 6 rising lines each
    steep = {k: v for k, v in d_min.items() if k.endswith(("_line75", "_line90"))}
    normal = {k: v for k, v in d_min.items() if k not in steep}
    # the bores and the lines up to 60 deg elevation keep the 5 mm keep-out
    assert all(v >= P.LID1021_KEEPOUT for v in normal.values()), {k: round(v, 2) for k, v in normal.items() if v < P.LID1021_KEEPOUT}
    # a line leaving a T hole steeper than that (75 deg, or straight up along the wall plane) cannot get over the lid, which stays inside the
    # 45 mm wall plane (lid tips at 42.65): at least 45 - 42.65 - 0.5 (line radius) = 1.85 mm even for a vertical line
    assert min(steep.values()) > 1.8
    print("steepest-line worst case: %.2f mm" % min(steep.values()))
    d_cover = lid.distance(cover)
    print("lid -> camera-bay cover: %.1f mm" % d_cover)
    assert d_cover >= P.LID1021_KEEPOUT and _vol(lid, cover) == 0.0
    # the lid does not touch the bay body either: the housing is touched only at the seat ring and by the four bumps (tests above)
    bay_zone = cq.Workplane("XY").box(200, 50.0, 200, centered=False).translate((-100, 0.0, -150)).val()          # everything below y = 50
    assert _vol(lid, housing.intersect(bay_zone)) < TOL


def test_lid_goes_in_underside_first_touching_only_the_bumps(lid, housing):
    """Lower the lid onto the seat from 6 mm above: at every height the only contact with the housing is the four bump tips on the recess walls."""
    for dy in (6.0, 5.2, 4.8, 4.0, 2.5, 1.0, 0.3, 0.0):
        moved = lid.translate(cq.Vector(0, dy, 0))
        pieces = _pieces(moved.intersect(housing))
        if dy >= 5.0:
            assert not pieces, dy                                                              # still above the rim
        for p in pieces:
            c = p.Center()
            assert any(math.hypot(c.x - rot(C0.x_bump, C0.rh + 0.07, a)[0], c.z - rot(C0.x_bump, C0.rh + 0.07, a)[1]) < 0.3 for a in (0, 90, 180, 270)), (dy, c)
        assert len(pieces) <= 4


# =====================================================================================================================
# printability: top face down
# =====================================================================================================================
def test_prints_top_face_down_without_supports(lid):
    pp = L.to_print_pose(lid).BoundingBox()
    assert (pp.xmin, pp.ymin, pp.zmin) == pytest.approx((0, 0, 0), abs=1e-6)
    assert (pp.xlen, pp.ylen, pp.zlen) == pytest.approx((85.3, 85.3, 1.8), abs=2e-3)
    assert L.bed_contact_area(lid) > 5500.0                                                    # the flat top face (minus chamfer, slots, notch) is the bed face
    assert L.overhang_faces(lid) == []                                                          # nothing steeper than 45 deg faces down: slots / notch vertical, lead-ins face up
    # minimum features for a 0.4 mm nozzle
    assert C0.bump_tip >= 0.45 and C0.slot >= 1.0 and C0.arm_t >= 1.2 and C0.t >= 1.2


# =====================================================================================================================
# exports, round trip, parameters
# =====================================================================================================================
def test_step_round_trip_in_the_world_frame_and_exports_are_current(lid, housing_raw, tmp_path):
    path = str(tmp_path / "lid.step")
    cq.exporters.export(cq.Workplane("XY").add(L.to_world(lid)), path)
    back = cq.importers.importStep(path).val()
    assert back.isValid() and len(back.Solids()) == 1 and back.Volume() == pytest.approx(lid.Volume(), rel=1e-6)
    # the exported file is the current build, in the world frame of Jasper's assembly
    step, stl = os.path.join(L.STEP_DIR, f"{L.LID_NAME}.step"), os.path.join(L.STL_DIR, f"{L.LID_NAME}.stl")
    assert os.path.exists(step) and os.path.exists(stl), "run /usr/bin/python3 -m cad.parts.gripper1021_housing_lid"
    disk = cq.importers.importStep(step).val()
    assert disk.Volume() == pytest.approx(lid.Volume(), rel=1e-5)
    bb = disk.BoundingBox()
    o = P.CAMBAY1021_BAY_ORIGIN_WORLD
    assert (bb.xmin, bb.xmax) == pytest.approx((o[0] - 42.65, o[0] + 42.65), abs=2e-3) and (bb.ymin, bb.ymax) == pytest.approx((o[1] + 50.0, o[1] + 51.8), abs=2e-3)
    # in the world frame against the housing STEP as exported (no residual correction): the four bump tips, plus contact slivers below 0.01 mm3
    world_housing = cq.importers.importStep(L.HOUSING_STEP).val()
    pieces = _pieces(disk.intersect(world_housing))
    assert sorted(p.Volume() for p in pieces)[-4:] == pytest.approx([0.157] * 4, abs=0.01)
    assert sum(p.Volume() for p in pieces) - sum(sorted(p.Volume() for p in pieces)[-4:]) < 0.02
    # STL: watertight, volume, print pose
    d = open(stl, "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    assert len(d) == 84 + 50 * n
    tris = np.frombuffer(d, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)["v"].astype(float)
    key = np.round(tris.reshape(-1, 3) * 1e4).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    edges = np.sort(np.concatenate([inv[:, [0, 1]], inv[:, [1, 2]], inv[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2), "STL not watertight"
    vol = abs(np.sum(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2]))) / 6.0)
    assert vol == pytest.approx(lid.Volume(), rel=0.01)
    pp = L.to_print_pose(lid).BoundingBox()
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    assert lo == pytest.approx([0, 0, 0], abs=0.02) and lo[2] == pytest.approx(0.0, abs=1e-4)
    assert hi == pytest.approx([pp.xlen, pp.ylen, pp.zlen], abs=0.02)


def test_renders_exist():
    names = [f"{L.LID_NAME}_{v}.png" for v in ("front", "rear", "left", "right", "top", "bottom", "iso")]
    names += [f"{L.LID_NAME}_on_housing_{k}.png" for k in ("iso", "section_y", "section_arm", "section_x0")]
    for n in names:
        path = os.path.join(L.RENDER_DIR, n)
        assert os.path.exists(path), f"missing {path}: run /usr/bin/python3 -m cad.parts.gripper1021_housing_lid"
        assert open(path, "rb").read(8) == b"\x89PNG\r\n\x1a\n" and os.path.getsize(path) > 5000


def test_parameter_edit_regenerates_the_lid(monkeypatch, housing):
    for k, v in (("LID1021_THICK", 2.2), ("LID1021_INTERF", 0.20), ("LID1021_SIDE_CLEAR", 0.30), ("LID1021_BUMP_TIP", 0.8)):
        monkeypatch.setattr(P, k, v)
    lid2 = L.make_lid().val()
    assert lid2.isValid() and len(lid2.Solids()) == 1
    bb = lid2.BoundingBox()
    assert bb.ymax - bb.ymin == pytest.approx(2.2, abs=1e-6) and bb.xmax == pytest.approx(42.5 - 0.30 + 0.50, abs=1e-3)
    pieces = _pieces(lid2.intersect(housing))
    assert len(pieces) == 4
    assert L.arm_estimate()["F_nominal_N"] > 2.2                                                # thicker plate, more interference: stiffer grip


def test_bump_tips_below_0_45_are_refused(monkeypatch):
    monkeypatch.setattr(P, "LID1021_BUMP_TIP", 0.3)
    with pytest.raises(AssertionError):
        L.Cfg()
