"""
Gripper v6r (Jasper's v6 gears modified for the 2:1 gearbox) -- executable acceptance checks.  Every number is
MEASURED from the built solids (nothing is read back from a docstring).

Covers: his source untouched, single valid solids, pinion identical to his, 36T tooth form equals his 54T tooth form
(pitch-circle thickness), feature-by-feature diff (no unintended change), lightening-hole ligaments, relief, crank
radius / phasing, mesh interference (2D outlines + 3D booleans), backlash / tip-root / axial / swept clearances,
STEP round trip, masses, and the saved verification JSON.

Run:  /usr/bin/python3 -m pytest -q tests/test_gripper_v6r_gears.py        (about 10 minutes: builds the solids)
"""

from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

from cad import params as P                       # noqa: E402
from cad.parts import gripper_v6r_gears as G      # noqa: E402
from cad.v6_loader import V6_STEP                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PETG = P.GRIPV6R_DENSITY_PETG
SWEEP_30 = list(np.arange(-30.0, 30.0 + 1e-9, 5.0))
STROKE = list(np.arange(0.0, P.GRIPV6R_SWEEP_DEG + 1e-9, 5.0)) + [P.GRIPV6R_SWEEP_DEG]
ALL_DELTAS = sorted(set(SWEEP_30 + STROKE))
NAMES = ("pinion", "compound", "compound_norelief", "follower")


@pytest.fixture(scope="module")
def parts():
    return {n: G.part(n) for n in NAMES}


@pytest.fixture(scope="module")
def mesh():
    return G.mesh_report(ALL_DELTAS)


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bb(s):
    b = s.BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


# ---------------------------------------------------------------------------------------------------------------
def test_source_step_not_modified():
    before = sha(V6_STEP)
    G.src_solid(P.GRIPV6R_SRC_COMPOUND)
    assert sha(V6_STEP) == before
    with open(os.path.join(REPO, "verification", "gripper_v6r_gears_numbers.json")) as fh:
        j = json.load(fh)
    assert j["source"]["unchanged"] is True
    assert j["source"]["sha256_before"] == before


def test_single_valid_solids(parts):
    for n, s in parts.items():
        assert s.isValid(), n
        assert len(s.Solids()) == 1, n


def test_pinion_is_his_unchanged(parts):
    his = G.home_pinion()
    new = parts["pinion"]
    assert new.Volume() == pytest.approx(his.Volume(), rel=1e-9)
    assert len(new.Faces()) == len(his.Faces())
    assert bb(new) == pytest.approx(bb(his), abs=1e-6)
    # his geometry: 18T, D30 tip, D8.00 bore, 16 mm face, no horn pocket
    x0, x1, y0, y1, z0, z1 = bb(new)
    assert (z0, z1) == pytest.approx((0.0, 16.0), abs=1e-6)
    assert y1 - y0 == pytest.approx(30.0, abs=1e-6)
    on, off = G._surface_census(new)
    assert on[(4.0, 0.0, 16.0)][1] == pytest.approx(math.pi * 8.0 * 16.0, rel=1e-4)       # D8.00 through bore
    assert not any(k[0] > 15.0 for k in on)


def test_compound_envelope_and_layers(parts):
    x0, x1, y0, y1, z0, z1 = bb(parts["compound"])
    assert (z0, z1) == pytest.approx((0.0, 36.0), abs=1e-5)
    tip36 = G.tip_r(P.GRIPV6R_Z_MAIN)
    assert tip36 == pytest.approx(28.5)
    assert max(abs(x0), abs(x1), abs(y1)) == pytest.approx(tip36, abs=0.03)       # 36T tip circle (lug is on -y side)
    o = G.mesh_outlines()
    r = np.hypot(o["ring36"][:, 0], o["ring36"][:, 1])
    assert r.max() == pytest.approx(28.5, abs=1e-3)
    assert r.min() == pytest.approx(G.root_r(36), abs=1e-3)                          # 25.125
    r24 = np.hypot(o["sync_c"][:, 0], o["sync_c"][:, 1])
    assert (r24.max(), r24.min()) == pytest.approx((19.5, 16.125), abs=1e-3)
    xf0, xf1, yf0, yf1, zf0, zf1 = bb(parts["follower"])
    assert (zf0, zf1) == pytest.approx((16.0, 36.0), abs=1e-5)


def test_tooth_form_equals_his_54T():
    """New 36T teeth are the same involute form: pitch-circle thickness equals his 54T (2.256 = 2.356 - 0.10)."""
    rr = G.radii_report()
    th = rr["tooth_thickness_pitch_mm"]
    assert th["ideal_pitch_circle"] - th["his_54T"] == pytest.approx(P.GRIPV6R_TOOTH_THIN, abs=0.003)
    assert th["new_36T"] == pytest.approx(th["his_54T"], abs=0.003)
    assert th["his_pinion_18T"] == pytest.approx(th["his_54T"], abs=0.003)
    assert th["his_24T_follower"] == pytest.approx(th["his_54T"], abs=0.003)


def test_tooth_counts_by_pitch_circle_crossings():
    o = G.mesh_outlines()
    for key, n in (("ring36", 36), ("sync_c", 24), ("sync_f", 24), ("pinion", 18)):
        t, s = G.pitch_tooth_thickness(o[key], n)          # raises unless the pitch circle is crossed 2 n times
        assert t < s


def test_feature_diff_has_no_unintended_change():
    for k in ("pinion", "compound", "compound_norelief", "follower"):
        rows = G.feature_diff(k)
        bad = [r for r in rows if "UNINTENDED" in r["status"]]
        assert not bad, (k, bad)


def test_feature_diff_keeps_pockets_lips_bore(parts):
    """His bearing pockets (D14.075, D14.000 x 1.95 lips), shoulders and bore: identical axis-cylinder census."""
    for k, shoulder in (("compound", 4.15), ("follower", 4.165)):
        on_o, _ = G._surface_census(G.home_compound() if k == "compound" else G.home_follower())
        on_n, _ = G._surface_census(parts[k])
        keep = lambda c: {key: round(v[1], 1) for key, v in c.items() if key[0] in (7.0, 7.0375, shoulder, 16.125, 19.5)}
        assert keep(on_o) == keep(on_n), k
        assert any(key[0] == 7.0375 for key in on_n) and any(key[0] == 7.0 for key in on_n)
    pr = G.pocket_ranges(parts["compound"])
    assert pr[0][1] - pr[0][0] == pytest.approx(5.05, abs=2e-3)         # lower: one 5 mm bearing
    assert pr[-1][1] - pr[-1][0] == pytest.approx(10.05, abs=2e-3)      # upper: two bearings


def test_lightening_pattern(parts):
    lig = G.lightening_ligaments()
    for k, v in lig.items():
        assert v >= P.GRIPV6R_LIGHT_MIN_LIG, (k, v)
    # measured on the solid: N holes of D12 through layer 1
    assert len(G.hole_centres(parts["compound"], 6.0)) == P.GRIPV6R_LIGHT_N
    assert len(G.hole_centres(G.home_compound(), 6.0)) == 8              # his
    assert P.GRIPV6R_LIGHT_D == 12.0
    # 8 holes of his size cannot fit: needs R >= 18.3 > root - 6 - 2
    assert 14.0 / (2 * math.sin(math.pi / 8)) > G.root_r(36) - 6.0 - 2.0


def test_relief_and_norelief(parts):
    ax = G.axial_gaps()
    assert ax["big_gear_top_z_norelief"] == pytest.approx(16.0, abs=1e-6)
    assert ax["big_gear_top_z_relief"] == pytest.approx(16.0 - P.GRIPV6R_RELIEF_DEPTH, abs=1e-6)
    assert ax["follower_to_36T_relief"] >= P.GRIPV6R_AXIAL_GAP_MIN - 1e-9
    assert ax["follower_to_36T_norelief"] == pytest.approx(0.0, abs=1e-6)       # as his: flush, counter-rotating
    assert ax["pinion_to_boss"] >= P.GRIPV6R_PINION_BOSS_GAP - 1e-9
    dv = parts["compound_norelief"].Volume() - parts["compound"].Volume()
    assert dv > 0
    # relief volume = annulus (R16.5..tip) x 0.30 minus holes / tooth gaps -> well below the full annulus
    full = math.pi * (28.5 ** 2 - P.GRIPV6R_RELIEF_R_IN ** 2) * P.GRIPV6R_RELIEF_DEPTH
    assert 0.3 * full < dv < full


def test_crank_radius_and_phasing(parts):
    for k, ang in (("compound", P.GRIPV6R_ARM_DEG_C), ("follower", P.GRIPV6R_ARM_DEG_F)):
        d, r, a = G.pivot_hole(parts[k])
        assert r == pytest.approx(P.GRIPV6R_ARM_R, abs=0.01)
        assert (a - ang + 180.0) % 360.0 - 180.0 == pytest.approx(0.0, abs=0.01)
    assert P.GRIPV6R_ARM_R == P.GRIPV7_CRANK_R == 53.0
    assert P.GRIPV6R_ARM_DEG_F == pytest.approx(180.0 - P.GRIPV6R_ARM_DEG_C)         # mirror about the tube plane
    # his pivot holes kept: compound D3.5, follower D8.33
    assert G.pivot_hole(parts["compound"])[0] == pytest.approx(3.5, abs=1e-3)
    assert G.pivot_hole(parts["follower"])[0] == pytest.approx(8.33, abs=1e-3)


def test_lug_section_identical_to_his(parts):
    """Arm cross-section (outer width 18.3, slot 8.3, band z 16..26) before the cut and beyond it (boss side)."""
    for k, a_o, a_n, his in (("compound", P.GRIPV6R_SRC_ARM_DEG_C, P.GRIPV6R_ARM_DEG_C, G.home_compound()),
                             ("follower", P.GRIPV6R_SRC_ARM_DEG_F, P.GRIPV6R_ARM_DEG_F, G.home_follower())):
        z = 1101.0 - P.GRIPV6R_SRC_Z0
        sh = P.GRIPV6R_ARM_SHORTEN
        so = G.arm_section(his, a_o, z, [25.0, 60.0])
        sn = G.arm_section(parts[k], a_n, z, [25.0, 60.0 - sh])
        assert so[25.0] == pytest.approx(sn[25.0], abs=2e-3)
        assert so[60.0] == pytest.approx(sn[60.0 - sh], abs=2e-3)
        assert so[60.0] == pytest.approx([-9.15, -4.15, 4.15, 9.15], abs=0.02) or k == "follower"


def test_mesh_no_overlap_and_backlash(mesh):
    """No tooth overlap at any pose of the +-30 deg sweep and the full 76.5 deg stroke; backlash >= 0.20 mm."""
    for r in mesh["rows"]:
        for k in ("pinion36", "sync24"):
            assert r[k]["gap_mm"] > 0.0, (r["delta_deg"], k)
            assert r[k]["backlash_mm"] >= P.GRIPV6R_BACKLASH_MIN, (r["delta_deg"], k, r[k]["backlash_mm"])
    # phasing: windows centred at the closed pose
    r0 = [r for r in mesh["rows"] if r["delta_deg"] == 0.0][0]
    assert abs(r0["pinion36"]["centre_deg"]) < 0.02
    assert abs(r0["sync24"]["centre_deg"]) < 0.05


def test_tip_root_clearance():
    rr = G.radii_report()
    for k in ("pinion_tip_to_36T_root", "ring36_tip_to_pinion_root", "sync_c_tip_to_f_root", "sync_f_tip_to_c_root"):
        assert rr[k] >= P.GRIPV6R_TIP_ROOT_MIN - 1e-6, (k, rr[k])
    assert P.GRIPV6R_CD_MAIN == pytest.approx(40.80) and P.GRIPV6R_CD_SYNC == pytest.approx(36.30)


def test_interference_3d_zero(parts):
    """Gear bodies: zero at every pose of the +-30 deg sweep and the stroke.  Past the closed stop (negative offsets,
    not an operating pose) the two lugs eventually touch each other; that margin is asserted separately."""
    rows = G.interference_3d([-30.0, 0.0, 30.0, P.GRIPV6R_SWEEP_DEG])
    for r in rows:
        assert r["gear_bodies_compound_follower"] <= 0.5 and r["pinion_compound"] <= 0.5 and r["pinion_follower"] <= 0.5, r
        if r["delta_deg"] >= -20.0:
            assert r["compound_follower"] <= 0.5, r
        else:
            assert r["compound_follower"] == pytest.approx(r["lug_vs_lug"], rel=1e-3), r      # all of it is lug vs lug
    rows = G.interference_3d([0.0, 30.0], "compound_norelief")
    for r in rows:
        assert r["pinion_compound"] <= 0.5 and r["compound_follower"] <= 0.5, r
    assert G.lug_overtravel_limit() <= -15.0          # at least 15 deg of over-travel past the closed stop


def test_interference_check_is_sensitive(parts):
    c = G.interference_control(3.0)
    assert c["compound_follower"] > 5.0 and c["pinion_compound"] > 5.0, c


def test_swept_clearance_lugs(parts):
    sw = G.swept_clearance(np.linspace(0.0, P.GRIPV6R_SWEEP_DEG, 5))
    assert sw["min"]["distance_mm"] >= P.GRIPV6R_SWEEP_CLEAR_MIN, sw["min"]


def test_radial_36T_to_follower(parts):
    r = G.radial_36T_to_follower()
    assert r["follower_material_below_z16_mm3"] < 0.5          # nothing of his follower in the 36T layer
    assert r["radial_to_follower_pin_r3p5"] >= P.GRIPV6R_RADIAL_36T_FOLLOWER_MIN


def test_step_round_trip_and_masses(parts, tmp_path):
    for n, s in parts.items():
        p = str(tmp_path / (n + ".step"))
        cq.exporters.export(cq.Workplane(obj=s), p)
        re = cq.importers.importStep(p).val()
        assert re.isValid() and len(re.Solids()) == 1
        assert re.Volume() == pytest.approx(s.Volume(), rel=1e-5)
        assert bb(re) == pytest.approx(bb(s), abs=1e-3)
    m = {n: s.Volume() * PETG / 1000.0 for n, s in parts.items()}
    assert m["pinion"] == pytest.approx(10.2, abs=0.3)                      # his 10 g
    assert 30.0 < m["compound"] < m["compound_norelief"] < 80.0
    assert m["follower"] < 32.0 + 1.0                                        # his 32 g, shorter arm


def _read_stl(path):
    raw = np.fromfile(path, dtype=np.uint8)
    n = int(np.frombuffer(raw[80:84].tobytes(), dtype="<u4")[0])
    rec = np.frombuffer(raw[84:84 + 50 * n].tobytes(), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return rec["v"].astype(float)


def test_stl_print_orientation_watertight_and_volume(parts):
    names = {"pinion": "gripper_v6r_pinion", "compound": "gripper_v6r_compound_36T_24T",
             "compound_norelief": "gripper_v6r_compound_36T_24T_norelief", "follower": "gripper_v6r_follower"}
    for k, base in names.items():
        tri = _read_stl(os.path.join(REPO, "exports", "stl", base + ".stl"))
        assert tri[:, :, 2].min() == pytest.approx(0.0, abs=1e-3), k                 # on the bed
        vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0
        assert vol == pytest.approx(parts[k].Volume(), rel=3e-3), k
        key = np.round(tri.reshape(-1, 3), 3)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        idx = inv.reshape(-1, 3)
        edges = np.sort(np.concatenate([idx[:, [0, 1]], idx[:, [1, 2]], idx[:, [2, 0]]]), axis=1)
        _, cnt = np.unique(edges, axis=0, return_counts=True)
        assert (cnt == 2).all(), (k, np.bincount(cnt))                               # closed 2-manifold mesh


def test_saved_outputs_exist_and_consistent():
    for base in ("gripper_v6r_pinion", "gripper_v6r_compound_36T_24T", "gripper_v6r_compound_36T_24T_norelief",
                 "gripper_v6r_follower"):
        assert os.path.getsize(os.path.join(REPO, "exports", "step", base + ".step")) > 1000
        assert os.path.getsize(os.path.join(REPO, "exports", "stl", base + ".stl")) > 1000
    with open(os.path.join(REPO, "verification", "gripper_v6r_gears_numbers.json")) as fh:
        j = json.load(fh)
    assert j["feature_diff_unintended"] == []
    assert j["mesh"]["summary"]["pinion36"]["min_backlash_mm"] >= P.GRIPV6R_BACKLASH_MIN
    assert j["mesh"]["summary"]["sync24"]["min_backlash_mm"] >= P.GRIPV6R_BACKLASH_MIN
    for k, v in j["parts"].items():
        assert v["valid"] and v["solids"] == 1
        assert v["roundtrip"]["volume_rel_diff"] < 1e-5
