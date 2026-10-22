"""
Acceptance checks for encoder 1021 v2, the SELF-CENTRING version (answer to verification finding F1: worst-case chip-to-magnet offset 0.78 mm,
RSS 0.44 mm against about 0.25 mm; spec: the lead's task 2026-10-22; parts: cad/parts/encoder1021.py with v2=True, params ENC1021_V2_*).

v2 changes (v1, the fit-test variants and their exports are unchanged and re-checked here):
  board pocket   0.25 mm per side + 8 crush ribs (2 per wall, clear of pad rows / hook lips / tabs): rib tip 0.10 inside the board outline
  magnet pocket  Ø6.3 + 3 crush ribs: tip 0.12 inside the Ø6.0 magnet
  peg            0.20 high ribs with a 0.45 tip (the rib020 variant), crush 0.10 into the Ø5.30 bore
  foot           23.4 (0.3 per side) + 8 crush bumps that follow the measured divot dish wall, 0.10 interference at every depth they cover

Everything is measured on the built B-rep solids / exported files (ray probes, booleans, distances) against the corrected station_1021
reference parts (same frame correction as tests/test_encoder1021.py).  Run with /usr/bin/python3 -m pytest tests/test_encoder1021_v2.py
"""

from __future__ import annotations

import math
import os
import sys

import pytest

cq = pytest.importorskip("cadquery")

import numpy as np                                               # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import encoder1021 as E                           # noqa: E402
from tests.test_encoder1021 import Probe, _bb, _cyl_faces, _stl_triangles, _vol   # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(E.REF_DIR), reason="station_1021 reference parts not available")

TOL = 1e-3                                  # mm3: a true face contact leaves less than this
C2 = E.Cfg(v2=True)
EPS = P.ENC1021_V2_RIB_TOL
RIB_ANGLES = (180, 300, 60)                 # peg and magnet ribs: from +x toward +z


# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cap2():
    return E.make_magnet_cap(v2=True).val()


@pytest.fixture(scope="module")
def cas2():
    return E.make_casing(v2=True).val()


@pytest.fixture(scope="module")
def cap1():
    return E.make_magnet_cap().val()


@pytest.fixture(scope="module")
def cas1():
    return E.make_casing().val()


@pytest.fixture(scope="module")
def magnet():
    return E.make_magnet().val()


@pytest.fixture(scope="module")
def board():
    return E.make_board().val()


@pytest.fixture(scope="module")
def ref():
    return E.reference_parts(True)


@pytest.fixture(scope="module")
def pc2(cap2):
    return Probe(cap2)


@pytest.fixture(scope="module")
def pk2(cas2):
    return Probe(cas2)


def _ray(a_deg):
    a = math.radians(a_deg)
    return (math.cos(a), 0.0, math.sin(a))


def _pieces(shape):
    return [s for s in shape.Solids() if s.Volume() > 1e-9]


# =====================================================================================================================
# v1 is not broken
# =====================================================================================================================
def test_v1_master_values_are_unchanged():
    assert (P.ENC1021_PCB_CLEAR, P.ENC1021_FOOT_SIZE, P.ENC1021_CAP_RIB_H, P.ENC1021_CAP_RIB_W_TIP,
            P.ENC1021_CAP_POCKET_CLEAR_D, P.ENC1021_HOOK_OVERLAP, P.ENC1021_FLEX_WALL_T) == (0.2, 23.6, 0.15, 0.3, 0.2, 0.4, 1.2)
    c1 = E.Cfg()
    assert (c1.pocket_half, c1.foot, c1.rib_h, c1.rib_wt, c1.pocket_d) == (pytest.approx(11.7), 23.6, 0.15, 0.3, pytest.approx(6.2))


@pytest.mark.parametrize("name,key", [(E.CAP_NAME, "cap"), (E.CASING_NAME, "casing"),
                                      ("encoder1021_magnet_cap_rib020", "rib020"), ("encoder1021_magnet_cap_rib025", "rib025"),
                                      ("encoder1021_casing_foot234", "foot234")])
def test_v1_and_variant_exports_still_equal_their_builds(name, key):
    """The v1 / variant exports on disk are what the (refactored) v1 builders still produce: zero boolean difference."""
    fresh = {"cap": E.make_magnet_cap, "casing": E.make_casing}.get(key, lambda: E.build_variant(key))().val()
    disk = cq.importers.importStep(os.path.join(E.STEP_DIR, f"{name}.step")).val()
    assert disk.Volume() == pytest.approx(fresh.Volume(), rel=1e-5)
    assert fresh.cut(disk).Volume() < 0.01 and disk.cut(fresh).Volume() < 0.01


def test_building_v2_does_not_touch_the_master_values(cap2, cas2):
    assert P.ENC1021_FOOT_SIZE == 23.6 and P.ENC1021_PCB_CLEAR == 0.2 and P.ENC1021_CAP_RIB_H == 0.15


# =====================================================================================================================
# magnet cap v2
# =====================================================================================================================
def test_cap2_is_one_valid_solid_with_the_v1_envelope(cap2, cap1):
    assert cap2.isValid() and len(cap2.Solids()) == 1
    assert _bb(cap2) == pytest.approx(_bb(cap1), abs=1e-6)                 # 14 x 6.7 x 14, y 22.6 .. 29.3
    v = cap2.Volume()
    print("cap v2 volume %.1f mm3, %.2f g" % (v, v * P.ENC1021_PETG_G_CM3 / 1000))
    assert 470.0 < v < 500.0


def test_cap2_magnet_pocket_and_levels_unchanged(pc2):
    y_top = 31.0 - pc2.boundary((5.0, 31.0, 0.0), (0, -1, 0), 8.0)
    y_floor = 31.0 - pc2.boundary((0.0, 31.0, 0.0), (0, -1, 0), 8.0)
    assert y_top == pytest.approx(29.3, abs=0.01)                          # magnet face level
    assert y_floor == pytest.approx(26.75, abs=0.01) and y_top - y_floor == pytest.approx(2.55, abs=0.01)
    assert 20.0 + pc2.boundary((0.0, 20.0, 0.0), (0, 1, 0), 5.0) == pytest.approx(22.6, abs=0.01)     # peg end
    assert 20.0 + pc2.boundary((5.0, 20.0, 0.0), (0, 1, 0), 9.0) == pytest.approx(26.0, abs=0.01)     # head underside
    for a in (0, 120, 240):                                                # between the ribs: pocket Ø6.3
        assert pc2.boundary((0.0, 28.0, 0.0), _ray(a), 5.0, 0.01) == pytest.approx(3.15, abs=0.005), a


def test_cap2_three_magnet_ribs_centre_the_magnet(pc2, magnet):
    """3 ribs at 60 / 180 / 300 deg: tip radius 2.88 = magnet r 3.0 - 0.12 crush, tip at least 0.45 wide, full pocket depth."""
    for y in (26.9, 27.5, 28.2, 29.0):
        for a in RIB_ANGLES:
            r = pc2.boundary((0.0, y, 0.0), _ray(a), 5.0, 0.005)
            assert r == pytest.approx(2.88, abs=0.005), (y, a, r)
            assert 3.0 - r == pytest.approx(0.12, abs=0.005)                # crush on the Ø6.0 magnet
            ca, sa = _ray(a)[0], _ray(a)[2]
            tang = (-sa, 0.0, ca)
            p0 = ((r + 0.01) * ca, y, (r + 0.01) * sa)                      # just outside the tip, inside the rib
            half = min(pc2.boundary(p0, tang, 1.0, 0.005), pc2.boundary(p0, tuple(-t for t in tang), 1.0, 0.005))
            assert half >= 0.45 / 2 - 0.003, (y, a, half)
    # exactly three ribs (angular scan), equally spaced, nothing else narrows the pocket
    prev, starts = False, []
    for a in np.arange(0.0, 360.0, 0.5):
        inrib = pc2.boundary((0.0, 28.0, 0.0), _ray(a), 5.0, 0.01) < 3.1
        if inrib and not prev:
            starts.append(a)
        prev = inrib
    assert len(starts) == 3 and np.allclose(np.diff(starts), 120.0, atol=1.0)
    # lead-in at the mouth: the rib ramps down to the wall over its height (45 deg), so the magnet enters
    assert pc2.boundary((0.0, 29.29, 0.0), _ray(60), 5.0, 0.005) > 3.0 + 0.1
    assert pc2.boundary((0.0, 29.3 - 0.27 - 0.02, 0.0), _ray(60), 5.0, 0.005) == pytest.approx(2.88, abs=0.005)


def test_cap2_magnet_crush_is_the_three_ribs_only(cap2, magnet):
    common = cap2.intersect(magnet)
    pieces = _pieces(common)
    print("magnet / rib crush: %d pieces, %.3f mm3" % (len(pieces), common.Volume()))
    assert len(pieces) == 3
    assert 0.3 < common.Volume() < 0.55
    assert max(p.Volume() for p in pieces) < 1.3 * min(p.Volume() for p in pieces)          # equal ribs
    # without the ribs the magnet only has the 0.15 mm clearance
    bare = E.make_magnet_cap(ribs=False, v2=True).val()
    assert _vol(bare, magnet) == 0.0
    assert magnet.distance(bare) == pytest.approx(0.05, abs=0.01)                          # glue film below, 0.15 radial


def test_cap2_magnet_ribs_hold_it_centred(cap2, magnet):
    """Geometric play of the ribbed pocket: shifted by up to the 0.12 mm crush the magnet still touches all three ribs; beyond that the
    rib on the far side loses contact.  (The centring itself is the equal elastic crush of the three equal ribs.)"""
    for a in RIB_ANGLES:
        ca, sa = _ray(a)[0], _ray(a)[2]
        away = lambda d: magnet.translate(cq.Vector(-d * ca, 0, -d * sa))                  # move the magnet away from the rib at angle a
        assert len(_pieces(cap2.intersect(away(0.10)))) == 3, a
        assert len(_pieces(cap2.intersect(away(0.14)))) == 2, a


def test_cap2_peg_is_the_rib020_variant(cap2, ref, pc2):
    """Peg ribs 0.20 high, tip 0.45: tip radius 2.75, crush 0.10 into the bore; the peg itself equals the fit-test variant."""
    sp = Probe(ref["Spool1011"])
    y = 24.3
    for a in RIB_ANGLES:
        r = pc2.boundary((0.0, y, 0.0), _ray(a), 4.0, 0.005)
        assert r == pytest.approx(2.75, abs=0.005)
        assert r - sp.boundary((0.0, y, 0.0), _ray(a), 4.0, 0.005) == pytest.approx(0.10, abs=0.006)
        ca, sa = _ray(a)[0], _ray(a)[2]
        p0 = ((r - 0.01) * ca, y, (r - 0.01) * sa)
        half = min(pc2.boundary(p0, (-sa, 0, ca), 1.0, 0.005), pc2.boundary(p0, (sa, 0, -ca), 1.0, 0.005))
        assert half >= 0.45 / 2 - 0.003
    assert pc2.boundary((0.0, y, 0.0), _ray(90), 4.0, 0.005) == pytest.approx(2.55, abs=0.005)       # round part, flat
    assert pc2.boundary((0.0, y, 0.0), _ray(0), 4.0, 0.005) == pytest.approx(2.05, abs=0.005)
    v2peg = E.make_peg(v2=True).val()
    with E.params_override(ENC1021_CAP_RIB_H=0.20, ENC1021_CAP_RIB_W_TIP=0.45):
        v1_rib020 = E.make_peg().val()
    assert v2peg.Volume() == pytest.approx(v1_rib020.Volume(), rel=1e-9)
    assert v2peg.cut(v1_rib020).Volume() < 1e-6 and v1_rib020.cut(v2peg).Volume() < 1e-6


def test_cap2_interference_is_the_peg_ribs_only(cap2, ref):
    v = _vol(cap2, ref["Spool1011"])
    assert 0.3 < v < 0.7                                                   # 0.477 mm3 = three 0.20 ribs (v1: 0.163)
    for n in ("Motor_Reference", "Heat_horn", "Shell_Casing", "Slipin_mount_piecev3", "Wall_Mount_v3"):
        assert _vol(cap2, ref[n]) == 0.0, n
    assert cap2.distance(ref["Motor_Reference"]) == pytest.approx(0.6, abs=0.01)
    bare = E.make_magnet_cap(ribs=False, v2=True).val()
    assert _vol(bare, ref["Spool1011"]) < TOL                              # head on the face only


def test_cap2_pry_notch_and_head_unchanged(pc2):
    assert not pc2.inside((0.0, 26.4, 6.0)) and pc2.inside((0.0, 27.0, 6.0)) and pc2.inside((6.0, 26.4, 0.0))


# =====================================================================================================================
# encoder casing v2
# =====================================================================================================================
def test_cas2_is_one_valid_solid_and_bbox(cas2):
    assert cas2.isValid() and len(cas2.Solids()) == 1
    x0, x1, y0, y1, z0, z1 = _bb(cas2)
    assert x0 == pytest.approx(-22.15, abs=2e-3) and x1 == pytest.approx(13.75, abs=2e-3)        # frame outer 27.5 (0.25 clearance)
    assert y0 == pytest.approx(31.0, abs=2e-3) and y1 == pytest.approx(45.0 + 11.7 + 0.4, abs=2e-3)   # +y foot bumps 0.4 beyond the 23.4 foot
    assert z0 == pytest.approx(-13.75, abs=2e-3) and z1 == pytest.approx(13.75, abs=2e-3)
    v = cas2.Volume()
    print("casing v2 volume %.1f mm3, %.2f g" % (v, v * P.ENC1021_PETG_G_CM3 / 1000))
    assert 3300.0 < v < 3600.0


def test_cas2_pocket_clearance_and_centre(pk2):
    y = 32.9
    xp = pk2.boundary((0.0, y, 0.0), (1, 0, 0), 14.0)                      # at z = 0: between the ribs
    xn = pk2.boundary((0.0, y, 0.0), (-1, 0, 0), 14.0)
    zp = pk2.boundary((0.0, y, 0.0), (0, 0, 1), 14.0)
    zn = pk2.boundary((0.0, y, 0.0), (0, 0, -1), 14.0)
    assert xp + xn == pytest.approx(23.5, abs=0.02) and zp + zn == pytest.approx(23.5, abs=0.02)      # 0.25 mm per side
    assert abs(xp - xn) / 2 < 0.01 and abs(zp - zn) / 2 < 0.01


def test_cas2_eight_board_ribs_centre_the_board(pk2):
    """Two ribs per wall at +-6.5 from the wall centre, tip 11.40 = board edge 11.50 - 0.10 crush, tip >= 0.45 wide, symmetric."""
    y = 33.0
    for pos in (6.5, -6.5):
        for d in ((1, 0, 0), (-1, 0, 0)):                                    # +-x walls (pad edges): ribs at z = +-6.5
            assert pk2.boundary((0.0, y, pos), d, 14.0, 0.005) == pytest.approx(11.4, abs=0.006), (pos, d)
        for d in ((0, 0, 1), (0, 0, -1)):                                    # +-z walls (hook edges): ribs at x = +-6.5
            assert pk2.boundary((pos, y, 0.0), d, 14.0, 0.005) == pytest.approx(11.4, abs=0.006), (pos, d)
    # no ribs elsewhere: the pad rows (+-x edges, |z| < 4.5), the hook lips (+-z edges, |x| < 4.5), the corners stay at the wall, 11.75
    for pos in (0.0, 2.0, -2.0, 4.0, -4.0, 8.0, -8.0):
        for d in ((1, 0, 0), (-1, 0, 0)):
            assert pk2.boundary((0.0, y, pos), d, 14.0, 0.005) == pytest.approx(11.75, abs=0.006), (pos, d)
        for d in ((0, 0, 1), (0, 0, -1)):
            assert pk2.boundary((pos, y, 0.0), d, 14.0, 0.005) == pytest.approx(11.75, abs=0.006), (pos, d)
    # rib tip width (tangential) at least 0.45, just inside the tip
    for (p0, tang) in (((6.5, y, 11.41), (1, 0, 0)), ((-6.5, y, -11.41), (1, 0, 0)), ((11.41, y, 6.5), (0, 0, 1)), ((-11.41, y, -6.5), (0, 0, 1))):
        half = min(pk2.boundary(p0, tang, 1.0, 0.005), pk2.boundary(p0, tuple(-t for t in tang), 1.0, 0.005))
        assert half >= 0.45 / 2 - 0.003, (p0, half)


def test_cas2_ribs_run_from_the_bed_face_and_have_a_lead_in(pk2):
    for xc in (6.5, -6.5):
        for y in (31.05, 32.0, 33.0, 33.6):
            assert pk2.inside((xc, y, 11.55)), (xc, y)                       # rib material (between tip 11.4 and wall 11.75) along the depth
    tip_mid = pk2.boundary((6.5, 33.0, 0.0), (0, 0, 1), 14.0, 0.005)
    tip_top = pk2.boundary((6.5, 33.84, 0.0), (0, 0, 1), 14.0, 0.005)        # board enters from +y: the rib ramps 45 deg to the wall at the top
    assert tip_mid == pytest.approx(11.4, abs=0.006) and tip_top > 11.65


def test_cas2_board_crush_is_the_eight_ribs_only(cas2, board):
    common = board.intersect(cas2)
    pieces = _pieces(common)
    print("board / rib crush: %d pieces, %.3f mm3" % (len(pieces), common.Volume()))
    assert len(pieces) == 8
    assert 0.35 < common.Volume() < 0.7
    cents = sorted((round(p.Center().x, 1), round(p.Center().z, 1)) for p in pieces)
    exp = sorted({(round(a, 1), round(b, 1)) for a, b in
                  [(6.5, 11.45), (-6.5, 11.45), (6.5, -11.45), (-6.5, -11.45), (11.45, 6.5), (11.45, -6.5), (-11.45, 6.5), (-11.45, -6.5)]})
    assert cents == exp
    assert board.distance(cas2) == pytest.approx(0.0, abs=1e-6)


def test_cas2_board_play_is_the_rib_crush(cas2, board):
    """Geometric play of the ribbed pocket: a 0.09 mm shift in x or z keeps all ribs in contact (0.10 crush), 0.11 loses the far-side ones;
    even shifted 0.2 mm the board only ever touches ribs, never a wall (walls are 0.25 away)."""
    for dx, dz in ((0.09, 0), (-0.09, 0), (0, 0.09), (0, -0.09)):
        assert len(_pieces(board.translate(cq.Vector(dx, 0, dz)).intersect(cas2))) == 8, (dx, dz)
    for dx, dz in ((0.11, 0), (-0.11, 0), (0, 0.11), (0, -0.11)):
        assert len(_pieces(board.translate(cq.Vector(dx, 0, dz)).intersect(cas2))) == 6, (dx, dz)
    for dx, dz in ((0.2, 0), (0, 0.2), (-0.2, 0), (0, -0.2)):
        for piece in _pieces(board.translate(cq.Vector(dx, 0, dz)).intersect(cas2)):
            bb = piece.BoundingBox()
            assert max(abs(bb.xmin), abs(bb.xmax), abs(bb.zmin), abs(bb.zmax)) < 11.72, (dx, dz)     # rib region only, wall face is at 11.75


def test_cas2_chip_plane_tabs_hooks_unchanged(pk2):
    for sx in (-1, 1):
        for sz in (-1, 1):
            c = (sx * 10.2, 0.0, sz * 10.2)
            assert 30.0 + pk2.boundary((c[0], 30.0, c[2]), (0, 1, 0), 3.0) == pytest.approx(31.0, abs=0.01)           # tab front
            y_back = 33.0 - pk2.boundary((c[0], 33.0, c[2]), (0, -1, 0), 3.0)
            assert y_back == pytest.approx(32.25, abs=0.01) and y_back - P.ENC1021_CHIP_H == pytest.approx(30.8, abs=0.1)   # chip face plane
            assert 11.75 - pk2.boundary((0.0, 31.6, c[2]), (sx, 0, 0), 14.0) == pytest.approx(3.0, abs=0.02)         # 3 x 3 tab
    for s_ in (1, -1):
        assert 33.85 + pk2.boundary((0.0, 33.85, s_ * 11.4), (0, 1, 0), 2.0) == pytest.approx(33.95, abs=0.01)         # hook catch face
        assert pk2.boundary((0.0, 34.2, 0.0), (0, 0, s_), 13.0) == pytest.approx(11.5 - P.ENC1021_HOOK_OVERLAP, abs=0.01)  # lip overlap 0.4
        assert not pk2.inside((6.0, 34.2, s_ * 11.3))                                                              # lips only over 8 mm
    for s_ in (1, -1):
        assert pk2.inside((s_ * 13.0, 32.5, 0.0)) and not pk2.inside((s_ * 13.0, 34.5, 0.0))                        # pad edges open at the back


def test_cas2_board_is_retained_by_the_hooks(cas2, board):
    hooks = cas2.intersect(cq.Workplane("XY").box(60, 4, 60, centered=False).translate((-30, 33.9, -30)).val())      # everything at y >= 33.9
    assert _vol(board.translate(cq.Vector(0, 0.09, 0)), hooks) == 0.0
    assert _vol(board.translate(cq.Vector(0, 0.30, 0)), hooks) > 0.5


def test_cas2_foot_23_4_with_eight_bumps(pk2):
    ey = pk2.boundary((-19.5, 45.0, 0.0), (0, 1, 0), 15.0)
    ez = pk2.boundary((-19.5, 45.0, 0.0), (0, 0, 1), 15.0) + pk2.boundary((-19.5, 45.0, 0.0), (0, 0, -1), 15.0)
    assert ey == pytest.approx(11.7, abs=0.01) and ez == pytest.approx(23.4, abs=0.02)             # between the bumps
    x_bot = -25.0 + pk2.boundary((-25.0, 45.0, 0.0), (1, 0, 0), 8.0)
    x_top = -15.0 - pk2.boundary((-15.0, 45.0, 0.0), (-1, 0, 0), 8.0)
    assert x_bot == pytest.approx(-22.15, abs=0.01) and x_top == pytest.approx(-18.15, abs=0.01)  # floor datum, 3.0 proud


def test_cas2_foot_bumps_follow_the_measured_dish_wall(pk2, ref):
    """At every depth the bump covers, on all eight bumps, the bump tip is 0.10 mm beyond the REFERENCE slip-in's dish wall
    (lateral interference), while the foot between the bumps is 0.3 mm clear."""
    sl = Probe(ref["Slipin_mount_piecev3"])
    sides = {"+z": ((0, 0, 1), lambda u, x: (x, 45.0 + u, 0.0)), "-z": ((0, 0, -1), lambda u, x: (x, 45.0 + u, 0.0)),
             "+y": ((0, 1, 0), lambda u, x: (x, 45.0, u)), "-y": ((0, -1, 0), lambda u, x: (x, 45.0, u))}
    for name, (d, start) in sides.items():
        for u in (-9.0, 9.0):
            for x in (-21.85, -21.65, -21.45, -21.25, -21.17):                 # depth 0.70 .. 0.02 below the plate-face plane
                p0 = start(u, x)
                dish = sl.boundary(p0, d, 15.0, 0.02)
                tip = pk2.boundary(p0, d, 15.0, 0.02)
                assert dish - tip == pytest.approx(-0.10, abs=0.006), (name, u, x, dish, tip)
        for u in (0.0, 4.5, -4.5):                                              # between the bumps: 0.3 clear
            for x in (-22.14, -21.9, -21.5, -21.2):
                p0 = start(u, x)
                assert sl.boundary(p0, d, 15.0, 0.02) - pk2.boundary(p0, d, 15.0, 0.02) == pytest.approx(0.3, abs=0.006), (name, u, x)
    # bump width along the side: 0.6 (>= 0.45 required), measured just inside the tip on one bump of each side
    for (p0, tang) in (((-21.5, 36.0, 12.0), (0, 1, 0)), ((-21.5, 54.0, -12.0), (0, 1, 0)), ((-21.5, 57.0, 9.0), (0, 0, 1)), ((-21.5, 33.0, -9.0), (0, 0, 1))):
        half = min(pk2.boundary(p0, tang, 1.0, 0.005), pk2.boundary(p0, tuple(-t for t in tang), 1.0, 0.005))
        assert 2 * half == pytest.approx(0.6, abs=0.02), (p0, half)


def test_cas2_divot_crush_is_the_eight_bumps_only(cas2, ref):
    sl = ref["Slipin_mount_piecev3"]
    common = cas2.intersect(sl)
    pieces = _pieces(common)
    print("foot bumps / divot wall crush: %d pieces, %.3f mm3 (each %.4f)" % (len(pieces), common.Volume(), pieces[0].Volume()))
    assert len(pieces) == 8
    assert common.Volume() == pytest.approx(8 * 0.042, abs=0.01)             # 0.6 wide x 0.7 deep x 0.10 lateral each
    cents = sorted((round(p.Center().y - 45.0, 0), round(p.Center().z, 0)) for p in pieces)
    assert cents == sorted([(-9.0, 12.0), (9.0, 12.0), (-9.0, -12.0), (9.0, -12.0), (-12.0, 9.0), (-12.0, -9.0), (12.0, 9.0), (12.0, -9.0)])
    for n, r in ref.items():
        if n != "Slipin_mount_piecev3":
            assert _vol(cas2, r) < TOL, n
    assert cas2.distance(sl) == pytest.approx(0.0, abs=1e-6)                 # floor contact


def test_cas2_foot_floor_contact_and_normal_gap(cas2, ref):
    bottom = [f for f in cas2.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().x + 1.0) < 1e-6 and abs(f.BoundingBox().xmin + 22.15) < 1e-3]
    assert len(bottom) == 1
    r = 1.7
    expect = 21.4 ** 2 - (4 - math.pi) * 0.2 ** 2 - 4 * (math.pi * r * r + (1 - math.pi / 4) * r * r)
    assert bottom[0].Area() == pytest.approx(expect, abs=0.5)
    # normal gap between the foot's bottom round (the big faces, bumps excluded) and the divot wall faces: 0.044 as in the 23.4 variant
    wall_faces = [f for f in ref["Slipin_mount_piecev3"].Faces() if f.geomType() in ("CYLINDER", "SPHERE") and f.BoundingBox().xmin > -22.2
                  and f.BoundingBox().xmax < -21.1 and 32.9 < f.BoundingBox().ymin and f.BoundingBox().ymax < 57.1
                  and abs(f.BoundingBox().zmin) < 12.1 and abs(f.BoundingBox().zmax) < 12.1]
    assert len(wall_faces) == 7
    round_faces = [f for f in cas2.Faces() if f.geomType() != "PLANE" and f.BoundingBox().xmin > -22.16 and f.BoundingBox().xmax < -21.14
                   and 33 < f.BoundingBox().ymin and f.BoundingBox().ymax < 57.2
                   and max(f.BoundingBox().ylen, f.BoundingBox().zlen) > 3.0]
    assert round_faces
    gap = cq.Compound.makeCompound(round_faces).distance(cq.Compound.makeCompound(wall_faces))
    print("normal gap foot round -> divot wall (bumps excluded): %.4f mm" % gap)
    assert gap == pytest.approx(0.044, abs=0.004)


def test_cas2_foot_rotation_and_translation_play_before_a_bump_loses_contact(cas2, ref, cas1):
    """v1: the foot turns +-1.10 deg and moves +-0.2 mm in the divot before it touches (the F1 foot term).  v2: all eight bumps keep
    contact up to 0.10 mm / 0.5 deg and the centring is the elastic balance of the equal bumps, not a clearance."""
    sl = ref["Slipin_mount_piecev3"]
    axis = ((0, 45.0, 0.0), (1, 45.0, 0.0))
    # v1 rotation limit by bisection (volume of interference > 0.05 mm3 means a corner / wall touches)
    lo, hi = 0.0, 3.0
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        if _vol(cas1.rotate(*axis, mid), sl) > 0.05:
            hi = mid
        else:
            lo = mid
    print("v1 foot rotation play: +-%.3f deg" % lo)
    assert lo == pytest.approx(E.V1_FOOT_ROTATION_DEG, abs=0.06)
    for dz in (0.19, -0.19):
        assert _vol(cas1.translate(cq.Vector(0, 0, dz)), sl) < TOL
    for dz in (0.21, -0.21):
        assert _vol(cas1.translate(cq.Vector(0, 0, dz)), sl) > 0.05
    # v2 translation: 0.09 keeps 8 bumps, 0.11 loses the two on the far side
    for (dy, dz, n) in ((0, 0.09, 8), (0, -0.09, 8), (0.09, 0, 8), (-0.09, 0, 8), (0, 0.11, 6), (0, -0.11, 6), (0.11, 0, 6), (-0.11, 0, 6)):
        assert len(_pieces(cas2.translate(cq.Vector(0, dy, dz)).intersect(sl))) == n, (dy, dz)
    # v2 rotation: contact loss at crush / lever = 0.10 / 9.0 rad = 0.64 deg
    assert len(_pieces(cas2.rotate(*axis, 0.5).intersect(sl))) == 8
    assert len(_pieces(cas2.rotate(*axis, -0.5).intersect(sl))) == 8
    assert len(_pieces(cas2.rotate(*axis, 0.8).intersect(sl))) < 8
    assert len(_pieces(cas2.rotate(*axis, -0.8).intersect(sl))) < 8


def test_cas2_holes_screw_access_and_clearances(cas2, ref, cap2, board):
    mine = _cyl_faces(cas2, 0, 1.7, tol=0.01)
    theirs = {(round(l[1], 3), round(l[2], 3)) for _, l in _cyl_faces(ref["Slipin_mount_piecev3"], 0, 1.725, tol=0.01)}
    assert len({(round(l[1], 3), round(l[2], 3)) for _, l in mine}) == 4 and len(theirs) == 4
    for _, l in mine:
        assert min(math.hypot(l[1] - ty, l[2] - tz) for ty, tz in theirs) < 0.05
    r = C2.screw_access_r
    for (y, z) in C2.hole_pts:
        cyl = cq.Workplane("YZ", origin=(C2.foot_top_x, 0, 0)).center(y, z).circle(r).extrude(40.0).val()
        assert _vol(cas2, cyl) == 0.0
        above = cas2.intersect(cq.Workplane("XY").box(60, 80, 60, centered=False).translate((C2.foot_top_x + 0.05, 0, -30)).val())
        assert above.distance(cyl) >= 0.5
    assert cas2.distance(ref["Shell_Casing"]) >= 1.0
    assert cas2.BoundingBox().ymin >= 26.0                                                 # line path: nothing at y < 26
    assert _vol(cas2, cq.Workplane(E._plane_y(0.0)).circle(19.0).extrude(26.0).val()) == 0.0
    # rotating cap (360 deg sweep) clear of the v2 casing, chip is the only thing within 1.5 mm
    dmin = min(cap2.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), a).distance(cas2) for a in range(0, 360, 10))
    head = cq.Workplane(E._plane_y(26.0)).circle(7.0).extrude(3.3).val()
    d_env = head.distance(cas2)
    print("v2 swept cap -> casing: %.3f mm (envelope %.3f)" % (dmin, d_env))
    assert dmin >= 1.0 and d_env >= 1.0
    assert _vol(cap2, cas2) == 0.0
    d_chip = min(cap2.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), a).distance(board) for a in range(0, 360, 30))
    assert d_chip == pytest.approx(1.5, abs=0.01)


# =====================================================================================================================
# printability (same orientations as v1)
# =====================================================================================================================
def test_cas2_prints_without_supports(cas2):
    """Frame front face on the bed, +y up.  Overhangs steeper than 45 deg: the two hook ledges (0.65 x 8 mm), the foot's key-edge ledge
    (about 1 mm, as v1) and the undersides of the foot bumps (0.4 mm ledges, 0.6 wide).  Nothing over the pocket except the hooks: the
    board ribs run from the bed face and ramp 45 deg at the top."""
    over = E.overhang_faces(cas2, "casing")
    hooks, edge, bumps, other = [], [], [], []
    for o in over:
        lo, hi = o["bbox"]
        if abs(lo[0]) <= 11.76 and abs(hi[0]) <= 11.76 and abs(lo[2]) <= 11.76 and abs(hi[2]) <= 11.76:
            hooks.append(o)
        elif hi[0] <= -20.9 + 1e-6 and lo[1] >= 33.25 and hi[1] <= 33.75 and abs(hi[2]) > 9.4:
            edge.append(o)
        elif (hi[0] <= -20.8 and lo[0] >= -21.9 and ((lo[1] >= 32.85 and hi[1] <= 33.25) or abs(lo[1] - 35.7) < 0.05 or abs(lo[1] - 53.7) < 0.05)
              and abs(hi[2]) <= 12.2):
            bumps.append(o)
        else:
            other.append(o)
    assert not other, other
    assert len(hooks) == 1 and hooks[0]["bbox"][0][1] == pytest.approx(33.95, abs=0.01)
    assert hooks[0]["area"] == pytest.approx(2 * C2.hook_w * C2.lip_protrusion, rel=0.02)
    edge_w = max(o["bbox"][1][0] - o["bbox"][0][0] for o in edge)
    bump_area = sum(o["area"] for o in bumps)
    print("v2 casing overhangs > 45 deg: hooks %.1f mm2, foot edge %.1f mm2 (%.2f mm wide), bump undersides %.2f mm2"
          % (hooks[0]["area"], sum(o["area"] for o in edge), edge_w, bump_area))
    assert edge_w <= 1.3 and bump_area < 3.5


def test_cap2_prints_without_supports_one_bridge(cap2):
    over = E.overhang_faces(cap2, "cap")
    assert len(over) == 1
    o = over[0]
    assert o["print_z"] == pytest.approx(2.55, abs=0.06)
    assert 28.0 < o["area"] < math.pi * 3.15 ** 2
    assert o["bbox"][1][0] - o["bbox"][0][0] == pytest.approx(6.3, abs=0.06)           # bridge span: the Ø6.3 pocket floor (ribs lie on it)


def test_print_pose_bboxes_v2(cap2, cas2):
    pk = E.to_print_pose(cap2, "cap").BoundingBox()
    assert (pk.xlen, pk.ylen, pk.zlen) == (pytest.approx(14.0, abs=1e-3), pytest.approx(14.0, abs=1e-3), pytest.approx(6.7, abs=1e-3))
    pc = E.to_print_pose(cas2, "casing").BoundingBox()
    assert (pc.xmin, pc.ymin, pc.zmin) == (pytest.approx(0, abs=1e-6),) * 3
    assert (pc.xlen, pc.ylen, pc.zlen) == (pytest.approx(35.9, abs=2e-3), pytest.approx(27.5, abs=2e-3), pytest.approx(26.1, abs=2e-3))


# =====================================================================================================================
# the stack-up (verification item 5 method)
# =====================================================================================================================
def test_stackup_v1_reproduces_the_verifiers_numbers():
    r = E.stackup(1)
    assert r["worst_radial"] == pytest.approx(0.783, abs=0.002) and r["rss_radial"] == pytest.approx(0.441, abs=0.002)
    assert r["worst_x"] == pytest.approx(0.40, abs=1e-6) and r["worst_z"] == pytest.approx(0.673, abs=0.002)
    assert r["arm"] == pytest.approx(14.2)


def test_stackup_v2_meets_the_targets():
    r = E.stackup(2)
    print({k: round(v, 4) for k, v in r.items() if isinstance(v, float)})
    assert r["rss_radial"] <= P.ENC1021_V2_TARGET_RSS and r["worst_radial"] <= P.ENC1021_V2_TARGET_WORST
    assert r["worst_radial"] == pytest.approx(0.317, abs=0.002) and r["rss_radial"] == pytest.approx(0.154, abs=0.002)
    # it holds for an asymmetry up to about 0.063 mm (worst case) / 0.081 mm (RSS); at 0.10 it does not (stated limit, to be measured)
    assert r["eps_max_worst"] == pytest.approx(0.0632, abs=0.001) and r["eps_max_rss"] == pytest.approx(0.0812, abs=0.001)
    assert E.stackup(2, eps=0.06)["worst_radial"] <= 0.4 and E.stackup(2, eps=0.10)["worst_radial"] > 0.4


def test_stackup_inputs_are_the_measured_geometry(cas2, pk2, cap2, pc2):
    """The levers, arm and crushes that the stack-up uses are what the solids have."""
    r = E.stackup(2)
    assert r["arm"] == pytest.approx(45.0 - 30.8)                                           # divot centre - chip face plane
    # bump lever: bump centres at +-9.0 from the side centre (centroids of the divot interference pieces measured above)
    assert C2.bump_pos == 9.0
    # every crush is at least 2 x eps, so contact is kept for any systematic over/undersize up to 2 x crush - ... of the modelled asymmetry
    for name, crush in (("board", C2.brd_rib_crush), ("peg", 0.10), ("magnet", C2.mag_rib_crush), ("foot", C2.bump_crush)):
        assert crush >= 2 * EPS - 1e-9, name
    # and the measured ones equal the design ones
    assert 11.5 - pk2.boundary((6.5, 33.0, 0.0), (0, 0, 1), 14.0, 0.005) == pytest.approx(0.10, abs=0.006)
    assert 3.0 - pc2.boundary((0.0, 28.0, 0.0), _ray(60), 5.0, 0.005) == pytest.approx(0.12, abs=0.006)


def test_pins_would_be_slightly_worse_and_cost_two_screws():
    b, pins = E.stackup(2, foot="bumps"), E.stackup(2, foot="pins")
    print("foot bumps worst %.3f / RSS %.3f ; two pins worst %.3f / RSS %.3f" % (b["worst_radial"], b["rss_radial"], pins["worst_radial"], pins["rss_radial"]))
    assert pins["worst_radial"] > b["worst_radial"] and pins["rss_radial"] > b["rss_radial"]
    assert pins["worst_radial"] == pytest.approx(0.341, abs=0.003) and pins["rss_radial"] == pytest.approx(0.169, abs=0.003)
    assert len(C2.hole_pts) - 2 == 2                                                       # pins use two of the four divot holes: two screws left
    # with the same asymmetry a pin pair still meets the targets; it loses first if the 4 mm blind hole prints worse than the 24 mm rim
    assert E.stackup(2, eps=0.07, foot="pins")["worst_radial"] > 0.4 > E.stackup(2, eps=0.07, foot="bumps")["worst_radial"] - 0.05


# =====================================================================================================================
# exports and parameters
# =====================================================================================================================
@pytest.mark.parametrize("name,part,mk", [(E.CAP_NAME_V2, "cap", E.make_magnet_cap), (E.CASING_NAME_V2, "casing", E.make_casing)])
def test_v2_step_round_trip_and_stl(name, part, mk, tmp_path):
    fresh = mk(v2=True).val()
    path = str(tmp_path / f"{name}.step")
    cq.exporters.export(cq.Workplane("XY").add(fresh), path)
    back = cq.importers.importStep(path).val()
    assert back.isValid() and len(back.Solids()) == 1
    assert back.Volume() == pytest.approx(fresh.Volume(), rel=1e-6)
    for u, v in zip(_bb(fresh), _bb(back)):
        assert u == pytest.approx(v, abs=5e-3)
    # the files on disk are the current build
    step, stl = os.path.join(E.STEP_DIR, f"{name}.step"), os.path.join(E.STL_DIR, f"{name}.stl")
    assert os.path.exists(step) and os.path.exists(stl), "run /usr/bin/python3 -m cad.parts.encoder1021 v2"
    disk = cq.importers.importStep(step).val()
    assert disk.Volume() == pytest.approx(fresh.Volume(), rel=1e-5) and fresh.cut(disk).Volume() < 0.01 and disk.cut(fresh).Volume() < 0.01
    tris = _stl_triangles(stl)
    key = np.round(tris.reshape(-1, 3) * 1e4).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    edges = np.sort(np.concatenate([inv[:, [0, 1]], inv[:, [1, 2]], inv[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2), "STL not watertight"
    vol = abs(np.sum(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2]))) / 6.0)
    assert vol == pytest.approx(fresh.Volume(), rel=0.01)
    pp = E.to_print_pose(fresh, part).BoundingBox()
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    assert lo == pytest.approx([0, 0, 0], abs=0.02) and lo[2] == pytest.approx(0.0, abs=1e-4)
    assert hi == pytest.approx([pp.xlen, pp.ylen, pp.zlen], abs=0.02)


def test_v2_renders_exist():
    names = []
    for part in (E.CAP_NAME, E.CASING_NAME):
        names += [f"v2_{part}_{v}.png" for v in ("front", "rear", "left", "right", "top", "bottom", "iso")]
    names += ["v2_encoder1021_assembly_iso.png", "v2_encoder1021_assembly_iso_front.png", "v2_encoder1021_assembly_section_z0.png",
              f"v2_{E.CAP_NAME}_section_z0.png", f"v2_{E.CAP_NAME}_section_magnet_ribs.png", f"v2_{E.CASING_NAME}_section_z0.png",
              f"v2_{E.CASING_NAME}_section_x0.png", f"v2_{E.CASING_NAME}_section_board_ribs.png", f"v2_{E.CASING_NAME}_section_foot_bumps.png"]
    for n in names:
        path = os.path.join(E.RENDER_DIR, n)
        assert os.path.exists(path), f"missing {path}: run /usr/bin/python3 -m cad.parts.encoder1021 v2"
        assert open(path, "rb").read(8) == b"\x89PNG\r\n\x1a\n" and os.path.getsize(path) > 5000


def test_v2_parameter_edit_regenerates_both_parts(monkeypatch):
    """One edit of the ENC1021_V2_* (and shared purchased-part) values regenerates both parts consistently."""
    for k, v in (("ENC1021_V2_PCB_CLEAR", 0.30), ("ENC1021_V2_BOARD_RIB_CRUSH", 0.12), ("ENC1021_V2_FOOT_BUMP_CRUSH", 0.15),
                 ("ENC1021_V2_MAGNET_RIB_CRUSH", 0.15), ("ENC1021_V2_CAP_POCKET_CLEAR_D", 0.40), ("ENC1021_MAGNET_D", 6.2)):
        monkeypatch.setattr(P, k, v)
    cap = E.make_magnet_cap(v2=True).val()
    cas = E.make_casing(v2=True).val()
    assert cap.isValid() and len(cap.Solids()) == 1 and cas.isValid() and len(cas.Solids()) == 1
    pc, pk = Probe(cap), Probe(cas)
    assert pc.boundary((0.0, 28.0, 0.0), _ray(0), 5.0, 0.005) == pytest.approx(3.3, abs=0.006)          # pocket Ø6.6 = 6.2 + 0.4
    assert pc.boundary((0.0, 28.0, 0.0), _ray(60), 5.0, 0.005) == pytest.approx(3.1 - 0.15, abs=0.006)   # tip = magnet r - 0.15
    assert pk.boundary((0.0, 33.0, 0.0), (1, 0, 0), 14.0, 0.005) == pytest.approx(11.8, abs=0.006)       # pocket half 11.5 + 0.30
    assert pk.boundary((6.5, 33.0, 0.0), (0, 0, 1), 14.0, 0.005) == pytest.approx(11.5 - 0.12, abs=0.006)
    sl = E.reference_parts(True)["Slipin_mount_piecev3"]
    assert len(_pieces(cas.intersect(sl))) == 8
    dish = Probe(sl)
    p0 = (-21.45, 45.0 + 9.0, 0.0)
    assert dish.boundary(p0, (0, 0, 1), 15.0, 0.02) - pk.boundary(p0, (0, 0, 1), 15.0, 0.02) == pytest.approx(-0.15, abs=0.006)
    assert E.stackup(2)["worst_radial"] > 0                                                              # still computable


def test_v2_rib_tips_below_0_45_are_refused(monkeypatch):
    monkeypatch.setattr(P, "ENC1021_V2_BOARD_RIB_TIP", 0.30)
    with pytest.raises(AssertionError):
        E.Cfg(v2=True)
