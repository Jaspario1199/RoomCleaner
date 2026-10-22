"""
Acceptance checks for the v2 magnet caps made for the MEASURED Ø4.0 magnet (Jasper, 10/22; ENC1021_MAGNET_D, was the supplied-magnet assumption Ø6.0):

    encoder1021_magnet_cap_v2_m4          standard peg 3.4  (stations with the 1/8 in fin)
    encoder1021_magnet_cap_v2_m4_peg1p9   short peg 1.9     (stations with the 0.019 in prototype fin; tests/test_encoder1021_peg1p9.py)

Built through the parameters (cad.parts.encoder1021.V2_VARIANTS); the Ø6 v2 files stay on disk as the superseded record.  Every number below that
scales with the magnet is derived from cad/params.py, not typed.  Run with /usr/bin/python3 -m pytest tests/test_encoder1021_m4.py
"""

from __future__ import annotations

import math
import os
import struct
import sys

import pytest

cq = pytest.importorskip("cadquery")

import numpy as np                                               # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import encoder1021 as E                           # noqa: E402
from tests.test_encoder1021 import Probe, _bb                    # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(E.REF_DIR), reason="station_1021 reference parts not available")

KEYS = ["m4", "m4_peg1p9"]
MAG_R = P.ENC1021_MAGNET_D / 2
POCKET_R = MAG_R + P.ENC1021_V2_CAP_POCKET_CLEAR_D / 2
RIB_TIP_R = MAG_R - P.ENC1021_V2_MAGNET_RIB_CRUSH
RIB_ANGLES = (60, 180, 300)                                      # deg from +x toward +z, as in the v2 cap
PEG_LEN = {"m4": P.ENC1021_CAP_PEG_LEN, "m4_peg1p9": P.FIN1021_PROTO_CAP_PEG_LEN}


def _ray(a):
    return (math.cos(math.radians(a)), 0.0, math.sin(math.radians(a)))


@pytest.fixture(scope="module")
def caps():
    return {k: E.build_v2_variant(k).val() for k in KEYS}


@pytest.fixture(scope="module")
def probes(caps):
    return {k: Probe(v) for k, v in caps.items()}


@pytest.fixture(scope="module")
def ref():
    return E.reference_parts(True)


# ---------------------------------------------------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------------------------------------------------
def test_magnet_parameter_and_nothing_else_changed():
    assert P.ENC1021_MAGNET_D == 4.0 and P.ENC1021_MAGNET_T == 2.5
    assert (P.ENC1021_CAP_PEG_LEN, P.ENC1021_CAP_HEAD_D, P.ENC1021_CAP_HEAD_T, P.ENC1021_CAP_FLOOR_MIN) == (3.4, 14.0, 3.3, 0.75)
    assert (P.ENC1021_V2_CAP_POCKET_CLEAR_D, P.ENC1021_V2_MAGNET_RIB_CRUSH, P.ENC1021_V2_MAGNET_RIB_TIP, P.ENC1021_V2_MAGNET_RIB_BASE) == (0.30, 0.12, 0.45, 0.9)
    assert (P.ENC1021_AIR_GAP, P.ENC1021_CAP_NOTCH, P.ENC1021_CAP_POCKET_EXTRA_DEPTH) == (1.5, (3.0, 2.0, 0.8), 0.05)


def test_variant_table_and_master_values_restored(caps):
    assert set(E.V2_VARIANTS) == set(KEYS)
    assert [E.V2_VARIANTS[k][2] for k in KEYS] == ["encoder1021_magnet_cap_v2_m4", "encoder1021_magnet_cap_v2_m4_peg1p9"]
    assert P.ENC1021_CAP_PEG_LEN == 3.4                                    # the short-peg override did not leak


def test_derived_levels_and_pocket():
    c = E.Cfg(v2=True)
    assert c.pocket_d == pytest.approx(P.ENC1021_MAGNET_D + P.ENC1021_V2_CAP_POCKET_CLEAR_D) and c.pocket_d == pytest.approx(4.3)
    assert c.magnet_face_y == pytest.approx(29.3, abs=1e-9)                # flush: head 3.3 on the 26.0 spool face
    assert c.pocket_floor_y - c.spool_face_y >= P.ENC1021_CAP_FLOOR_MIN - 1e-9      # solid material under the magnet
    assert c.head_t == pytest.approx(3.3) and c.head_d == 14.0
    assert c.mag_rib_tip >= 0.45 - 1e-9 and c.rib_wt >= 0.45 - 1e-9        # printable with a 0.4 mm nozzle
    assert c.mag_rib_h == pytest.approx(0.27)                              # 0.15 clearance + 0.12 crush
    assert 0.5 * c.mag_rib_base * c.mag_rib_n < math.pi * c.pocket_d / 2   # the three rib bases fit around the pocket wall


# ---------------------------------------------------------------------------------------------------------------------
# the built caps
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_cap_is_one_valid_solid_with_the_head_unchanged(caps, key):
    cap = caps[key]
    assert cap.isValid() and len(cap.Solids()) == 1
    x0, x1, y0, y1, z0, z1 = _bb(cap)
    assert (x0, x1, z0, z1) == pytest.approx((-7.0, 7.0, -7.0, 7.0), abs=1e-3)       # head Ø14
    assert y1 == pytest.approx(29.3, abs=1e-3)
    assert y0 == pytest.approx(P.ENC1021_SPOOL_FACE_Y - PEG_LEN[key], abs=1e-3)


@pytest.mark.parametrize("key", KEYS)
def test_pocket_floor_magnet_face_and_notch(probes, key):
    pc = probes[key]
    y_top = 31.0 - pc.boundary((5.0, 31.0, 0.0), (0, -1, 0), 8.0)
    y_floor = 31.0 - pc.boundary((0.0, 31.0, 0.0), (0, -1, 0), 8.0)
    assert y_top == pytest.approx(29.3, abs=0.01)                                    # magnet face level
    assert y_floor == pytest.approx(29.3 - (P.ENC1021_MAGNET_T + P.ENC1021_CAP_POCKET_EXTRA_DEPTH), abs=0.01)
    assert y_floor - P.ENC1021_SPOOL_FACE_Y >= P.ENC1021_CAP_FLOOR_MIN - 0.01
    for a in (0, 120, 240):                                                          # between the ribs: pocket Ø4.3
        assert pc.boundary((0.0, 28.0, 0.0), _ray(a), 5.0, 0.01) == pytest.approx(POCKET_R, abs=0.005), a
    # head radius 7 at the middle of the head, pry notch under the rim at +z unchanged (3 wide, 0.8 high)
    assert 4.0 + pc.boundary((4.0, 27.5, 0.0), (1, 0, 0), 5.0, 0.01) == pytest.approx(7.0, abs=0.01)
    assert not pc.inside((0.0, 26.4, 6.0)) and pc.inside((0.0, 27.0, 6.0))
    assert pc.inside((3.0, 26.4, 6.0)) and pc.inside((6.0, 26.4, 0.0))


@pytest.mark.parametrize("key", KEYS)
def test_three_magnet_ribs_centre_the_magnet(caps, probes, key):
    pc = probes[key]
    for y in (26.9, 27.5, 28.2, 29.0):
        for a in RIB_ANGLES:
            r = pc.boundary((0.0, y, 0.0), _ray(a), 5.0, 0.005)
            assert r == pytest.approx(RIB_TIP_R, abs=0.005), (y, a, r)              # tip = magnet r - 0.12 = 1.88
            ca, sa = _ray(a)[0], _ray(a)[2]
            tang = (-sa, 0.0, ca)
            p0 = ((r + 0.01) * ca, y, (r + 0.01) * sa)
            half = min(pc.boundary(p0, tang, 1.0, 0.005), pc.boundary(p0, tuple(-t for t in tang), 1.0, 0.005))
            assert half >= 0.45 / 2 - 0.003, (y, a, half)                            # tip at least 0.45 wide
    prev, starts = False, []                                                        # exactly three ribs, 120 deg apart
    for a in np.arange(0.0, 360.0, 0.5):
        inrib = pc.boundary((0.0, 28.0, 0.0), _ray(a), 5.0, 0.01) < (POCKET_R + RIB_TIP_R) / 2
        if inrib and not prev:
            starts.append(a)
        prev = inrib
    assert len(starts) == 3 and np.allclose(np.diff(starts), 120.0, atol=1.0)
    mag = E.make_magnet().val()
    mb = mag.BoundingBox()
    assert (mb.xlen, mb.zlen) == pytest.approx((P.ENC1021_MAGNET_D,) * 2, abs=1e-6) and mb.ymax == pytest.approx(29.3, abs=1e-6)
    common = caps[key].intersect(mag)
    assert len(common.Solids()) == 3 and common.Volume() == pytest.approx(0.403, abs=0.01)     # the crush of the three ribs only
    assert caps[key].distance(mag) < 1e-6


@pytest.mark.parametrize("key", KEYS)
def test_print_pose_and_one_bridge(caps, key):
    over = E.overhang_faces(caps[key], "cap")
    assert len(over) == 1 and over[0]["print_z"] == pytest.approx(2.55, abs=0.06)
    assert over[0]["bbox"][1][0] - over[0]["bbox"][0][0] == pytest.approx(2 * POCKET_R, abs=0.06)      # the Ø4.3 pocket floor disc
    pk = E.to_print_pose(caps[key], "cap").BoundingBox()
    assert (pk.xmin, pk.ymin, pk.zmin) == pytest.approx((0, 0, 0), abs=1e-6)
    assert (pk.xlen, pk.ylen, pk.zlen) == pytest.approx((14.0, 14.0, 29.3 - (P.ENC1021_SPOOL_FACE_Y - PEG_LEN[key])), abs=1e-3)


def test_contact_with_the_spool_is_the_peg_ribs_only(caps, ref):
    for key in KEYS:
        cap = caps[key]
        sp = ref["Spool1011"].intersect(cap)
        assert len(sp.Solids()) == 3 and 0.1 < sp.Volume() < 0.6                        # three crush ribs
        for name in ("Motor_Reference", "Shell_Casing", "Slipin_mount_piecev3", "Wall_Mount_v3", "Heat_horn"):
            assert cap.distance(ref[name]) > 0.1 and cap.intersect(ref[name]).Volume() < 1e-6, (key, name)
    assert caps["m4_peg1p9"].intersect(ref["Spool1011"]).Volume() < caps["m4"].intersect(ref["Spool1011"]).Volume()


def test_the_o6_record_files_are_untouched_and_still_o6():
    """Superseded record: the v2 cap on disk still has the Ø6.3 pocket (r 3.15) and its asm1021 copy is there."""
    for name in ("encoder1021_magnet_cap_v2.step", "encoder1021_magnet_cap_v2_asm1021.step"):
        assert os.path.isfile(os.path.join(E.STEP_DIR, name)), name
    old = cq.importers.importStep(os.path.join(E.STEP_DIR, "encoder1021_magnet_cap_v2.step")).val()
    assert Probe(old).boundary((0.0, 28.0, 0.0), _ray(0), 5.0, 0.01) == pytest.approx(3.15, abs=0.005)


# ---------------------------------------------------------------------------------------------------------------------
# files
# ---------------------------------------------------------------------------------------------------------------------
def _stl(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    assert len(d) == 84 + 50 * n
    arr = np.frombuffer(d, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)
    return arr["v"].astype(float)


@pytest.mark.parametrize("key", KEYS)
def test_exports_match_the_build(caps, key):
    part, _, stem = E.V2_VARIANTS[key]
    step, stl = os.path.join(E.STEP_DIR, f"{stem}.step"), os.path.join(E.STL_DIR, f"{stem}.stl")
    assert os.path.isfile(step) and os.path.isfile(stl), "run /usr/bin/python3 -m cad.parts.encoder1021 m4"
    cap = caps[key]
    disk = cq.importers.importStep(step).val()
    assert disk.isValid() and len(disk.Solids()) == 1
    assert disk.Volume() == pytest.approx(cap.Volume(), rel=1e-5)
    assert cap.cut(disk).Volume() < 0.01 and disk.cut(cap).Volume() < 0.01
    for u, v in zip(_bb(cap), _bb(disk)):
        assert u == pytest.approx(v, abs=1e-2)                                       # OCC boxes of curved faces are loose (more so once tessellated)
    tris = _stl(stl)
    keyq = np.round(tris.reshape(-1, 3) * 1e4).astype(np.int64)
    _, inv = np.unique(keyq, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    edges = np.sort(np.concatenate([inv[:, [0, 1]], inv[:, [1, 2]], inv[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2), "STL is not watertight"
    vol = abs(np.sum(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2]))) / 6.0)
    assert vol == pytest.approx(cap.Volume(), rel=0.01)
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)       # same print orientation as the v2 cap: magnet face on the bed (z = 0), peg up
    assert tuple(lo) == pytest.approx((0, 0, 0), abs=1e-2)
    assert tuple(hi - lo) == pytest.approx((14.0, 14.0, 29.3 - (P.ENC1021_SPOOL_FACE_Y - PEG_LEN[key])), abs=1e-2)


@pytest.mark.parametrize("key", KEYS)
def test_asm1021_copy_is_the_station_file_plus_the_offset(key):
    """asm1021 = station frame + O + (0, 0, 2.64) + residual; same volume; the contact with the original assembly is the spool's ribs only."""
    from tools.export_encoder1021_asm import offset
    stem = E.V2_VARIANTS[key][2]
    st = cq.importers.importStep(os.path.join(E.STEP_DIR, f"{stem}.step")).val()
    path = os.path.join(E.STEP_DIR, f"{stem}_asm1021.step")
    assert os.path.isfile(path), "run PYTHONPATH=. /usr/bin/python3 tools/export_encoder1021_asm.py"
    asm = cq.importers.importStep(path).val()
    off = offset()
    s, a = _bb(st), _bb(asm)
    assert a == pytest.approx((s[0] + off.x, s[1] + off.x, s[2] + off.y, s[3] + off.y, s[4] + off.z, s[5] + off.z), abs=2e-3)
    assert asm.Volume() == pytest.approx(st.Volume(), rel=1e-6)


def test_asm1021_contact_check_against_the_original_assembly():
    from cad.reference.station_1021.extract import O, SRC
    from tools.export_encoder1021_asm import offset
    if not os.path.isfile(str(SRC)):
        pytest.skip("assembly STEP not available")
    solids = cq.importers.importStep(str(SRC)).val().Solids()
    refs = {n: cq.importers.importStep(os.path.join(E.REF_DIR, f"{n}.step")).val().translate(cq.Vector(*O)) for n in E.REF_NAMES}
    for key in KEYS:
        asm = cq.importers.importStep(os.path.join(E.STEP_DIR, f"{E.V2_VARIANTS[key][2]}_asm1021.step")).val()
        touching = []
        for s in solids:
            if asm.distance(s) < 1e-6:
                name = next(n for n, r in refs.items() if abs(r.Volume() - s.Volume()) < 0.01 and (r.Center() - s.Center()).Length < 0.01)
                touching.append((name, asm.intersect(s).Volume()))
        assert [t[0] for t in touching] == ["Spool1011"], (key, touching)
        assert 0.1 < touching[0][1] < 0.6
