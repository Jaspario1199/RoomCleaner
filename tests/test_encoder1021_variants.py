"""
Acceptance checks for the encoder 1021 FIT-TEST VARIANTS (lead request 2026-10-22, after the independent verification):

  magnet caps with crush-rib height 0.20 and 0.25 mm   encoder1021_magnet_cap_rib020 / _rib025   (nominal 0.15 is the normal export)
  casing with a 23.4 mm foot (fallback if 23.6 binds)  encoder1021_casing_foot234

They are built THROUGH the parameters (`cad.parts.encoder1021.build_variant`, `params_override`): the master ENC1021_* values in
cad/params.py are untouched and the nominal exports stay as they are.  Each variant is one valid solid with the changed dimension
measured on the solid, everything else equal to nominal, and zero interference with the station parts (cap: the ribs only).
Run with /usr/bin/python3 -m pytest tests/test_encoder1021_variants.py
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
from tests.test_encoder1021 import RECORD_MAGNET_D, Probe, _bb, _cyl_faces, _stl_triangles, _vol   # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(E.REF_DIR), reason="station_1021 reference parts not available")

TOL_MM3 = 1e-3
RIB_ANGLES = (180, 300, 60)                                       # deg from +x toward +z, as in the nominal cap
BORE_R = 2.65


# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def nominal_cap():
    return E.make_magnet_cap().val()


@pytest.fixture(scope="module")
def nominal_casing():
    return E.make_casing().val()


@pytest.fixture(scope="module")
def ref():
    return E.reference_parts(True)


@pytest.fixture(scope="module")
def variants():
    return {k: E.build_variant(k).val() for k in E.VARIANTS}


def _radius(probe, y, phi_deg, rmax=4.0):
    a = math.radians(phi_deg)
    return probe.boundary((0.0, y, 0.0), (math.cos(a), 0.0, math.sin(a)), rmax, 0.01)


# ---------------------------------------------------------------------------------------------------------------------
# the helper itself
# ---------------------------------------------------------------------------------------------------------------------
def test_variant_table_is_exactly_the_requested_three():
    assert set(E.VARIANTS) == {"rib020", "rib025", "foot234"}
    assert E.VARIANTS["rib020"][1]["ENC1021_CAP_RIB_H"] == 0.20 and E.VARIANTS["rib025"][1]["ENC1021_CAP_RIB_H"] == 0.25
    assert E.VARIANTS["foot234"][1] == {"ENC1021_FOOT_SIZE": 23.4}
    assert [E.VARIANTS[k][2] for k in E.VARIANTS] == ["encoder1021_magnet_cap_rib020", "encoder1021_magnet_cap_rib025",
                                                      "encoder1021_casing_foot234"]


def test_master_values_are_untouched_by_building_variants(variants):
    """Built through parameters: the master values are restored (also after an error inside the override)."""
    assert P.ENC1021_CAP_RIB_H == 0.15 and P.ENC1021_CAP_RIB_W_TIP == 0.3 and P.ENC1021_FOOT_SIZE == 23.6
    with pytest.raises(AttributeError):
        with E.params_override(ENC1021_FOOT_SIZE=23.4, ENC1021_NO_SUCH_VALUE=1):
            pass
    assert P.ENC1021_FOOT_SIZE == 23.6
    with pytest.raises(RuntimeError):
        with E.params_override(ENC1021_FOOT_SIZE=23.4):
            raise RuntimeError
    assert P.ENC1021_FOOT_SIZE == 23.6


@pytest.mark.parametrize("key", list(E.VARIANTS))
def test_variant_is_one_valid_solid(variants, key):
    v = variants[key]
    assert v.isValid() and len(v.Solids()) == 1
    assert v.Volume() > 0


def test_nominal_parts_are_still_the_nominal_exports(nominal_cap, nominal_casing):
    """After the variants were built the nominal builders still give the nominal parts, equal to the exports on disk."""
    with E.params_override(ENC1021_MAGNET_D=RECORD_MAGNET_D):                          # the nominal cap on disk is for the Ø6 magnet (superseded record)
        nominal_cap = E.make_magnet_cap().val()
    for name, fresh in ((E.CAP_NAME, nominal_cap), (E.CASING_NAME, nominal_casing)):
        on_disk = cq.importers.importStep(os.path.join(E.STEP_DIR, f"{name}.step")).val()
        assert on_disk.Volume() == pytest.approx(fresh.Volume(), rel=1e-5)
        for u, v in zip(_bb(fresh), _bb(on_disk)):
            assert u == pytest.approx(v, abs=1e-3)


# ---------------------------------------------------------------------------------------------------------------------
# magnet caps: crush-rib height 0.20 / 0.25
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,h,w_tip", [("rib020", 0.20, 0.45), ("rib025", 0.25, 0.45)])
def test_rib_variant_changed_dimension_is_measured(variants, nominal_cap, ref, key, h, w_tip):
    cap = variants[key]
    pc, pn = Probe(cap), Probe(nominal_cap)
    y = 24.3
    sp = Probe(ref["Spool1011"])
    for a in RIB_ANGLES:
        r = _radius(pc, y, a)
        assert r == pytest.approx(2.55 + h, abs=0.005), (a, r)                      # rib tip radius
        bore = sp.boundary((0.0, y, 0.0), (math.cos(math.radians(a)), 0.0, math.sin(math.radians(a))), 4.0, 0.01)
        assert r - bore == pytest.approx(h - 0.10, abs=0.006), (a, r - bore)       # radial crush into the Ø5.30 bore: 0.10 / 0.15
        # tip width: tangential half-width just below the tip is at least w_tip / 2 (the verifier asked for >= 0.45)
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        tangent = (-sa, 0.0, ca)
        p0 = ((r - 0.01) * ca, y, (r - 0.01) * sa)
        half = min(pc.boundary(p0, tangent, 1.0, 0.005), pc.boundary(p0, tuple(-t for t in tangent), 1.0, 0.005))
        assert half >= w_tip / 2 - 0.002, (a, half)
    # the nominal rib is narrower than 0.45 at the tip (0.3), so the variants really changed it
    pn_half = min(pn.boundary(((2.70 - 0.01) * math.cos(math.radians(180)), y, 0.0), (0, 0, 1), 1.0, 0.005),
                  pn.boundary(((2.70 - 0.01) * math.cos(math.radians(180)), y, 0.0), (0, 0, -1), 1.0, 0.005))
    assert pn_half < 0.17 < w_tip / 2
    # still three ribs: radius profile has exactly three peaks above the round part
    prof = [_radius(pc, y, a) for a in range(0, 360, 5)]
    peaks = sum(1 for i, r in enumerate(prof) if r > 2.65 and prof[i - 1] <= 2.65)
    assert peaks == 3


@pytest.mark.parametrize("key,h", [("rib020", 0.20), ("rib025", 0.25)])
def test_rib_variant_everything_else_equals_nominal(variants, nominal_cap, key, h):
    cap = variants[key]
    assert _bb(cap) == pytest.approx(_bb(nominal_cap), abs=1e-6)                     # same bbox (14 x 6.7 x 14)
    dv = cap.Volume() - nominal_cap.Volume()
    assert 0.0 < dv < 4.0                                                           # only the taller ribs
    # away from the ribs the peg is the nominal one: round 2.55, flat 2.05
    pc = Probe(cap)
    assert _radius(pc, 24.3, 90) == pytest.approx(2.55, abs=0.005) and _radius(pc, 24.3, 0) == pytest.approx(2.05, abs=0.005)
    # head, pocket, magnet face, peg end unchanged
    assert 31.0 - pc.boundary((5.0, 31.0, 0.0), (0, -1, 0), 8.0) == pytest.approx(29.3, abs=0.01)
    assert 31.0 - pc.boundary((0.0, 31.0, 0.0), (0, -1, 0), 8.0) == pytest.approx(26.75, abs=0.01)
    assert 20.0 + pc.boundary((0.0, 20.0, 0.0), (0, 1, 0), 5.0) == pytest.approx(22.6, abs=0.01)


@pytest.mark.parametrize("key", ["rib020", "rib025"])
def test_rib_variant_interference_is_the_ribs_only(variants, nominal_cap, ref, key):
    cap = variants[key]
    v_nom = _vol(nominal_cap, ref["Spool1011"])
    v = _vol(cap, ref["Spool1011"])
    print(f"{key}: crush-rib interference with the bore {v:.3f} mm3 (nominal {v_nom:.3f})")
    assert v > v_nom                                                                  # more crush
    assert v < 1.5
    for n in ("Motor_Reference", "Heat_horn", "Shell_Casing", "Slipin_mount_piecev3", "Wall_Mount_v3"):
        assert _vol(cap, ref[n]) == 0.0, n
    assert cap.distance(ref["Motor_Reference"]) == pytest.approx(0.6, abs=0.01)
    # without the ribs (cut the three rib sectors away) there is no interference at all: the peg core is the nominal D-peg
    core = E.make_peg(ribs=False).val()
    assert _vol(core, ref["Spool1011"]) == 0.0


def test_taller_ribs_give_more_crush_volume(variants, nominal_cap, ref):
    v = [_vol(c, ref["Spool1011"]) for c in (nominal_cap, variants["rib020"], variants["rib025"])]
    assert v[0] < v[1] < v[2]


# ---------------------------------------------------------------------------------------------------------------------
# casing with a 23.4 foot
# ---------------------------------------------------------------------------------------------------------------------
def test_foot234_changed_dimension_is_measured(variants):
    cas = variants["foot234"]
    pr = Probe(cas)
    ey = pr.boundary((-19.5, 45.0, 0.0), (0, 1, 0), 15.0)
    ez_p = pr.boundary((-19.5, 45.0, 0.0), (0, 0, 1), 15.0)
    ez_n = pr.boundary((-19.5, 45.0, 0.0), (0, 0, -1), 15.0)
    assert ey == pytest.approx(11.7, abs=0.01)                                       # +y edge at 45 + 11.7
    assert ez_p + ez_n == pytest.approx(23.4, abs=0.02)
    assert _bb(cas)[3] == pytest.approx(56.7, abs=1e-3)                              # y max
    # corner radius still >= 1.2 and the key depth / proud height unchanged
    corners = {(round(loc[1], 2), round(loc[2], 2)) for _, loc in _cyl_faces(cas, 0, 1.2, tol=0.05)}
    assert corners == {(round(45.0 + sy * 10.5, 2), round(sz * 10.5, 2)) for sy in (-1, 1) for sz in (-1, 1)}, corners
    x_bot = -25.0 + pr.boundary((-25.0, 45.0, 0.0), (1, 0, 0), 8.0)
    x_top = -15.0 - pr.boundary((-15.0, 45.0, 0.0), (-1, 0, 0), 8.0)
    assert x_bot == pytest.approx(-22.15, abs=0.01) and x_top == pytest.approx(-18.15, abs=0.01)


def test_foot234_has_0_3_mm_side_play_and_a_larger_normal_gap(variants, nominal_casing, ref):
    cas = variants["foot234"]
    pr, sl = Probe(cas), Probe(ref["Slipin_mount_piecev3"])
    for x in (-22.14, -22.05, -21.9, -21.7, -21.5, -21.3, -21.2):
        for d in ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            p0 = (x, 45.0, 0.0)
            assert sl.boundary(p0, d, 14.0, 0.05) - pr.boundary(p0, d, 14.0, 0.05) == pytest.approx(0.3, abs=0.006), (x, d)
    # normal gap between the foot's bottom round and the divot's seven wall faces (the verifier's 0.020 mm at the 23.6 foot)
    def walls(shape):
        out = []
        for f in shape.Faces():
            bb = f.BoundingBox()
            if f.geomType() in ("CYLINDER", "SPHERE") and bb.xmin > -22.2 and bb.xmax < -21.1 and 32.9 < bb.ymin \
                    and bb.ymax < 57.1 and abs(bb.zmin) < 12.1 and abs(bb.zmax) < 12.1:
                out.append(f)
        return cq.Compound.makeCompound(out)

    def key_round(shape):
        return cq.Compound.makeCompound([f for f in shape.Faces() if f.geomType() != "PLANE" and f.BoundingBox().xmin > -22.16
                                         and f.BoundingBox().xmax < -21.14 and 33 < f.BoundingBox().ymin and f.BoundingBox().ymax < 57])

    w = walls(ref["Slipin_mount_piecev3"])
    assert len(w.Faces()) == 7
    g_nom = key_round(nominal_casing).distance(w)
    g_var = key_round(cas).distance(w)
    print(f"normal gap foot round -> divot wall: nominal {g_nom:.4f} mm, foot234 {g_var:.4f} mm")
    assert g_nom == pytest.approx(0.0198, abs=0.002)
    assert g_var == pytest.approx(0.0440, abs=0.003) and g_var > 2.0 * g_nom


def test_foot234_zero_interference_and_only_floor_contact(variants, ref):
    cas = variants["foot234"]
    for n, r in ref.items():
        assert _vol(cas, r) < TOL_MM3, n
    assert cas.distance(ref["Slipin_mount_piecev3"]) == pytest.approx(0.0, abs=1e-6)       # foot on the divot floor
    assert cas.distance(ref["Shell_Casing"]) >= 1.0
    bottom = [f for f in cas.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().x + 1.0) < 1e-6
              and abs(f.BoundingBox().xmin + 22.15) < 1e-3]
    assert len(bottom) == 1
    r = 1.7
    teardrop = math.pi * r * r + (1 - math.pi / 4) * r * r
    expect = 21.4 ** 2 - (4 - math.pi) * 0.2 ** 2 - 4 * teardrop                            # 21.4 flat, R0.2 corners
    assert bottom[0].Area() == pytest.approx(expect, abs=0.5)


def test_foot234_holes_and_screw_access_unchanged(variants, ref):
    cas = variants["foot234"]
    mine = _cyl_faces(cas, 0, 1.7, tol=0.01)
    theirs = {(round(l[1], 3), round(l[2], 3)) for _, l in _cyl_faces(ref["Slipin_mount_piecev3"], 0, 1.725, tol=0.01)}
    assert len({(round(l[1], 3), round(l[2], 3)) for _, l in mine}) == 4 and len(theirs) == 4
    for _, l in mine:
        assert min(math.hypot(l[1] - ty, l[2] - tz) for ty, tz in theirs) < 0.05
    r = E.Cfg().screw_access_r
    for (y, z) in E.Cfg().hole_pts:
        cyl = cq.Workplane("YZ", origin=(-18.15, 0, 0)).center(y, z).circle(r).extrude(40.0).val()
        assert _vol(cas, cyl) == 0.0


def test_foot234_board_pocket_chip_plane_and_hooks_equal_nominal(variants, nominal_casing):
    cas = variants["foot234"]
    pv, pn = Probe(cas), Probe(nominal_casing)
    for probe in (pv, pn):
        assert probe.boundary((0.0, 32.9, 0.0), (1, 0, 0), 14.0) == pytest.approx(11.7, abs=0.005)
        assert 33.0 - probe.boundary((10.2, 33.0, 10.2), (0, -1, 0), 3.0) == pytest.approx(32.25, abs=0.005)    # tab back = chip face + 1.45
        assert 33.85 + probe.boundary((0.0, 33.85, 11.3), (0, 1, 0), 2.0) == pytest.approx(33.95, abs=0.005)    # hook catch face
    # volume differs only by the thinner foot slab: (23.6^2 - 23.4^2) x 4 mm, less the rounded corners
    dv = nominal_casing.Volume() - cas.Volume()
    assert dv == pytest.approx((23.6 ** 2 - 23.4 ** 2) * 4.0, rel=0.25)


def test_foot234_print_overhangs_same_character_as_nominal(variants):
    over = E.overhang_faces(variants["foot234"], "casing")
    pocket_plan, edge, other = [], [], []
    for o in over:
        lo, hi = o["bbox"]
        if abs(lo[0]) <= 11.71 and abs(hi[0]) <= 11.71 and abs(lo[2]) <= 11.71 and abs(hi[2]) <= 11.71:
            pocket_plan.append(o)
        elif hi[0] <= -20.9 + 1e-6 and lo[1] >= 33.2 and hi[1] <= 33.8:                  # foot -y edge now at y = 33.3
            edge.append(o)
        else:
            other.append(o)
    assert not other, other
    assert len(pocket_plan) == 1 and pocket_plan[0]["area"] == pytest.approx(2 * 8.0 * 0.6, rel=0.02)     # the two hook ledges
    assert edge and max(o["bbox"][1][0] - o["bbox"][0][0] for o in edge) <= 1.3


# ---------------------------------------------------------------------------------------------------------------------
# exports of the variants
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", list(E.VARIANTS))
def test_variant_exports_exist_and_match_the_build(variants, key):
    part, _, stem = E.VARIANTS[key]
    step = os.path.join(E.STEP_DIR, f"{stem}.step")
    stl = os.path.join(E.STL_DIR, f"{stem}.stl")
    assert os.path.exists(step) and os.path.exists(stl), "run /usr/bin/python3 -m cad.parts.encoder1021 variants"
    fresh = variants[key]
    if part == "cap":                                                                # the cap variant files on disk are for the Ø6 magnet (superseded record)
        with E.params_override(ENC1021_MAGNET_D=RECORD_MAGNET_D):
            fresh = E.build_variant(key).val()
    back = cq.importers.importStep(step).val()
    assert back.isValid() and len(back.Solids()) == 1
    assert back.Volume() == pytest.approx(fresh.Volume(), rel=1e-5)
    for u, v in zip(_bb(fresh), _bb(back)):
        assert u == pytest.approx(v, abs=5e-3)                                       # OCC boxes of curved faces are loose by ~0.002
    tris = _stl_triangles(stl)
    key_ = np.round(tris.reshape(-1, 3) * 1e4).astype(np.int64)
    _, inv = np.unique(key_, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    edges = np.sort(np.concatenate([inv[:, [0, 1]], inv[:, [1, 2]], inv[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2), "STL is not watertight"
    vol = abs(np.sum(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2]))) / 6.0)
    assert vol == pytest.approx(fresh.Volume(), rel=0.01)
    pp = E.to_print_pose(fresh, part).BoundingBox()
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    assert lo == pytest.approx([0, 0, 0], abs=0.02) and lo[2] == pytest.approx(0.0, abs=1e-4)
    assert hi == pytest.approx([pp.xlen, pp.ylen, pp.zlen], abs=0.02)
