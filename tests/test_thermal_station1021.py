"""
Acceptance checks for the thermal station geometry (cad/thermal_station1021.py, spec cad/HEAT_FIN_1021_SPEC.md sections 3B and E; parameters THERMAL_*).

One STEP per variant, assembly coordinates, every solid a named component:
    fin1p8           1/8 in fin, Motor_Reference block (no shaft) moved by 2.0 - t with 4 x Ø3.0 x 4.0 holes, screws whose Ø3.0 shank fills them
    fin0p019         the same stack with the 0.019 in prototype fin
    detailed_fin1p8  the multi-body NEMA 17 (cad/parts/nema17_thermal.py) with real M3 x 12 screws (3.825 mm into the front cap)
The fin is exported as two named solids, fin_in / fin_out, split at the shell top where it leaves the shell.  Everything is MEASURED on the built solids,
on the exported files (named-component STEP read-back) and on the reference STEPs.  Run with /usr/bin/python3 -m pytest tests/test_thermal_station1021.py
"""

from __future__ import annotations

import math
import os
import sys

import pytest

cq = pytest.importorskip("cadquery")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad import thermal_station1021 as T                         # noqa: E402
from cad.parts import heat_fin1021 as H                          # noqa: E402
from cad.parts import nema17_thermal as N                        # noqa: E402
from cad.reference.station_1021.extract import O                 # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(T.REF_DIR), reason="station_1021 reference parts not available")

KEYS = [k for k, _, _ in P.THERMAL_VARIANTS]
BLOCK_KEYS = [k for k, _, m in P.THERMAL_VARIANTS if m == "block"]
VOL_TOL = 1e-3                                                   # mm3, analytic volumes / areas
HOLE_AREA_TOL = 0.02                                             # mm2, contact areas against analytic values

ENC_NAMES = ["insert_enc_1", "insert_enc_2", "insert_enc_3", "insert_enc_4"]
SCREW_NAMES = ["screw_1", "screw_2", "screw_3", "screw_4"]
EXPECTED_NAMES = {
    "fin1p8": ["motor_block", "fin_in", "fin_out", "slipin_mount"] + SCREW_NAMES + ["insert_deck"] + ENC_NAMES,
    "fin0p019": ["motor_block", "fin_in", "fin_out", "slipin_mount"] + SCREW_NAMES + ["insert_deck"] + ENC_NAMES,
    "detailed_fin1p8": list(P.NEMA17T_BODIES) + ["fin_in", "fin_out", "slipin_mount"] + SCREW_NAMES + ["insert_deck"] + ENC_NAMES,
}


def _bb(sh):
    b = sh.BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


@pytest.fixture(scope="module")
def stations():
    return {k: T.build_station(k) for k in KEYS}


@pytest.fixture(scope="module")
def reports(stations):
    return {k: T.interference_report(stations[k]) for k in KEYS}


@pytest.fixture(scope="module")
def meas():
    return T.measure_slipin()


def _contact(rep, a, b):
    return next((c for c in rep["contacts"] if {c["a"], c["b"]} == {a, b}), None)


def _area(rep, a, b):
    c = _contact(rep, a, b)
    return 0.0 if c is None else c["area"]


# ---------------------------------------------------------------------------------------------------------------------
# bodies and names
# ---------------------------------------------------------------------------------------------------------------------
def test_variant_table():
    assert KEYS == ["fin1p8", "fin0p019", "detailed_fin1p8"]
    assert dict((k, t) for k, t, _ in P.THERMAL_VARIANTS) == {"fin1p8": 3.175, "fin0p019": 0.483, "detailed_fin1p8": 3.175}
    assert P.THERMAL_INSERTS == ("deck", "enc")


@pytest.mark.parametrize("key", KEYS)
def test_body_names_and_one_valid_solid_each(stations, key):
    bodies = stations[key]
    assert list(bodies) == EXPECTED_NAMES[key]
    for n, s in bodies.items():
        assert s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0, n


@pytest.mark.parametrize("which,expect", [((), []), (("deck",), ["insert_deck"]), (("enc",), ENC_NAMES), (("deck", "enc"), ["insert_deck"] + ENC_NAMES)])
def test_inserts_are_optional_by_parameter(monkeypatch, which, expect):
    monkeypatch.setattr(P, "THERMAL_INSERTS", which)
    names = [n for n in T.build_station("fin1p8") if n.startswith("insert")]
    assert names == expect


def test_slipin_is_the_reference_part_unchanged(stations):
    ref = T.reference("Slipin_mount_piecev3")
    for k in KEYS:
        s = stations[k]["slipin_mount"]
        assert s.Volume() == pytest.approx(ref.Volume(), rel=1e-12) and _bb(s) == pytest.approx(_bb(ref), abs=1e-9)


# ---------------------------------------------------------------------------------------------------------------------
# no overlaps, contact list
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_no_pair_overlaps_above_the_limit(reports, key):
    rep = reports[key]
    assert P.THERMAL_OVERLAP_LIMIT_MM3 == 0.01
    assert rep["max_overlap"] <= P.THERMAL_OVERLAP_LIMIT_MM3, rep["overlaps"]
    assert all(v <= P.THERMAL_OVERLAP_LIMIT_MM3 for v in rep["overlaps"].values())


@pytest.mark.parametrize("key", KEYS)
def test_every_body_touches_something(reports, stations, key):
    touched = {n for c in reports[key]["contacts"] for n in (c["a"], c["b"])}
    missing = [n for n in stations[key] if n not in touched]
    assert missing == [], missing                                                  # every body carries a conduction path


@pytest.mark.parametrize("key", BLOCK_KEYS)
def test_contact_list_block_variants(reports, stations, key):
    rep = reports[key]
    t = dict((k, tt) for k, tt, _ in P.THERMAL_VARIANTS)[key]
    # the motor block's whole -x face is on the slip-in's back plate; the fin's tab face is on the tab; motor face on the fin
    assert _area(rep, "motor_block", "slipin_mount") == pytest.approx(P.NEMA17T_LEN * P.NEMA17T_SIZE, abs=HOLE_AREA_TOL)       # 38 x 42.3 = 1607.4
    assert _area(rep, "motor_block", "fin_in") == pytest.approx(1300.548, abs=0.05) and _contact(rep, "motor_block", "fin_out") is None
    assert _area(rep, "fin_in", "slipin_mount") == pytest.approx(1298.552, abs=0.05) and _contact(rep, "fin_out", "slipin_mount") is None
    assert _area(rep, "fin_in", "fin_out") == pytest.approx(42.0 * t, abs=HOLE_AREA_TOL)
    for i in (1, 2, 3, 4):
        s = f"screw_{i}"
        # shank in the Ø3.0 x 4.0 motor hole: shared cylinder + end face; head annulus on the tab face
        c = _contact(rep, "motor_block", s)
        assert c["kinds"]["cyl"] == pytest.approx(math.pi * P.THERMAL_SCREW_D * P.THERMAL_MOTOR_HOLE_DEPTH, abs=HOLE_AREA_TOL)
        assert c["kinds"]["plane"] == pytest.approx(math.pi * (P.THERMAL_SCREW_D / 2) ** 2, abs=HOLE_AREA_TOL)
        assert _area(rep, "slipin_mount", s) == pytest.approx(math.pi / 4 * (P.THERMAL_SCREW_HEAD_D ** 2 - P.THERMAL_TAB_HOLE_D ** 2), abs=HOLE_AREA_TOL)
        assert _contact(rep, "fin_in", s) is None and _contact(rep, "fin_out", s) is None          # radial gap through the fin hole
    assert _area(rep, "slipin_mount", "insert_deck") == pytest.approx(math.pi * P.THERMAL_DECK_INSERT_OD * P.THERMAL_DECK_INSERT_LEN, abs=HOLE_AREA_TOL)
    for n in ENC_NAMES:
        c = _contact(rep, "slipin_mount", n)
        assert c["kinds"]["cyl"] == pytest.approx(math.pi * P.THERMAL_ENC_INSERT_OD * P.THERMAL_ENC_INSERT_LEN, abs=HOLE_AREA_TOL)
        assert c["kinds"]["plane"] == pytest.approx(math.pi / 4 * (P.THERMAL_ENC_INSERT_OD ** 2 - P.THERMAL_ENC_INSERT_ID ** 2), abs=HOLE_AREA_TOL)   # bottom of the hole
    # the screw shank to the fin hole wall: a 0.2 mm radial gap listed as a near gap
    near = {(c["a"], c["b"]): c["gap"] for c in rep["near"]}
    assert all(near[("fin_in", f"screw_{i}")] == pytest.approx((P.FIN1021_HOLE_D - P.THERMAL_SCREW_D) / 2, abs=1e-6) for i in (1, 2, 3, 4))


def test_contact_list_detailed(reports):
    rep = reports["detailed_fin1p8"]
    flat = P.NEMA17T_SIZE - 2 * P.NEMA17T_CORNER_CHAMFER                           # flat part of a side: 36.3
    assert _area(rep, "stator", "winding") == pytest.approx(math.pi * P.NEMA17T_STATOR_BORE_D * P.NEMA17T_STATOR_LEN, abs=HOLE_AREA_TOL)
    assert _area(rep, "front_cap", "shaft") == pytest.approx(math.pi * P.NEMA17T_SHAFT_D * (P.NEMA17T_CAP_LEN + P.NEMA17T_PILOT_H), abs=HOLE_AREA_TOL)
    assert _area(rep, "rear_cap", "shaft") == pytest.approx(math.pi * P.NEMA17T_SHAFT_D * (P.NEMA17T_CAP_LEN - P.NEMA17T_SHAFT_REAR_INSET)
                                                           + math.pi * (P.NEMA17T_SHAFT_D / 2) ** 2, abs=HOLE_AREA_TOL)
    assert _area(rep, "rear_cap", "connector") == pytest.approx(P.NEMA17T_CONNECTOR[0] * P.NEMA17T_CONNECTOR[1], abs=HOLE_AREA_TOL)
    assert _area(rep, "front_cap", "slipin_mount") == pytest.approx(P.NEMA17T_CAP_LEN * flat, abs=HOLE_AREA_TOL)      # the -x side of each cap / the stator on the back plate
    assert _area(rep, "stator", "slipin_mount") == pytest.approx(P.NEMA17T_STATOR_LEN * flat, abs=HOLE_AREA_TOL)
    assert _contact(rep, "stator", "shaft") is None and _contact(rep, "winding", "shaft") is None             # air around the shaft inside the stator
    assert _contact(rep, "front_cap", "fin_out") is None and _contact(rep, "stator", "fin_in") is None
    for i in (1, 2, 3, 4):
        c = _contact(rep, "front_cap", f"screw_{i}")
        assert c["kinds"]["cyl"] == pytest.approx(math.pi * P.THERMAL_SCREW_D * (P.THERMAL_SCREW_LEN_DETAILED - P.THERMAL_TAB_T - P.FIN1021_T_PRODUCTION_MM), abs=HOLE_AREA_TOL)
        assert "plane" not in c["kinds"]                                          # the screw tip does not reach the bottom of the 4.5 mm hole


# ---------------------------------------------------------------------------------------------------------------------
# screws
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_screw_heads_on_the_tab_face(stations, meas, key):
    tab_back = meas["tab_back_y"]
    assert tab_back - meas["tab_front_y"] == pytest.approx(P.THERMAL_TAB_T, abs=1e-6)
    for i, xz in enumerate(meas["tab_holes"], start=1):
        s = stations[key][f"screw_{i}"]
        x0, x1, y0, y1, z0, z1 = _bb(s)
        assert y1 == pytest.approx(tab_back + P.THERMAL_SCREW_HEAD_H, abs=1e-6)             # head top y 8
        assert (x1 - x0, z1 - z0) == pytest.approx((P.THERMAL_SCREW_HEAD_D, P.THERMAL_SCREW_HEAD_D), abs=1e-6)
        assert ((x0 + x1) / 2, (z0 + z1) / 2) == pytest.approx(xz, abs=1e-6)                 # on the tab hole axis
        head = s.intersect(cq.Workplane("XY").box(20, P.THERMAL_SCREW_HEAD_H, 20).translate((xz[0], tab_back + P.THERMAL_SCREW_HEAD_H / 2, xz[1])).val())
        assert head.Volume() == pytest.approx(math.pi * (P.THERMAL_SCREW_HEAD_D / 2) ** 2 * P.THERMAL_SCREW_HEAD_H, abs=VOL_TOL)
        # the head sits on the tab face: closest distance of the head to the slip-in is 0, and the head is above it
        assert s.distance(stations[key]["slipin_mount"]) < 1e-9


def test_tab_hole_clearances(meas):
    """Shank Ø3.0 through the Ø3.5 tab holes and the Ø3.4 fin holes: radial gaps 0.25 / 0.20, never touching."""
    assert meas["tab_hole_r"] - P.THERMAL_SCREW_D / 2 == pytest.approx(0.25, abs=1e-6)
    assert P.FIN1021_HOLE_D / 2 - P.THERMAL_SCREW_D / 2 == pytest.approx(0.20, abs=1e-9)


@pytest.mark.parametrize("key", BLOCK_KEYS)
def test_shanks_fill_the_motor_holes(stations, meas, key):
    """Each Ø3.0 shank exactly fills a Ø3.0 x 4.0 hole of the motor block: shank inside the solid (hole-less) block = pi r^2 x 4, no overlap with the real block."""
    block = stations[key]["motor_block"]
    solid = max(T.reference("Motor_Reference").Solids(), key=lambda s: s.Volume())
    solid = solid.translate(cq.Vector(0, block.BoundingBox().ymax - solid.BoundingBox().ymax, 0))              # same motor, no holes
    hole_vol = math.pi * (P.THERMAL_MOTOR_HOLE_D / 2) ** 2 * P.THERMAL_MOTOR_HOLE_DEPTH
    assert solid.Volume() - block.Volume() == pytest.approx(4 * hole_vol, abs=VOL_TOL)                     # 4 holes cut
    for i in (1, 2, 3, 4):
        s = stations[key][f"screw_{i}"]
        assert s.intersect(block).Volume() < VOL_TOL                                                       # no overlap
        assert s.intersect(solid).Volume() == pytest.approx(hole_vol, abs=VOL_TOL)                         # the shank occupies exactly the hole
        assert s.BoundingBox().ymin == pytest.approx(block.BoundingBox().ymax - P.THERMAL_MOTOR_HOLE_DEPTH, abs=1e-6)     # tip on the hole bottom


def test_detailed_screws_are_m3x12_into_the_front_cap(stations, meas):
    t = P.FIN1021_T_PRODUCTION_MM
    cap = stations["detailed_fin1p8"]["front_cap"]
    engaged = P.THERMAL_SCREW_LEN_DETAILED - P.THERMAL_TAB_T - t
    assert engaged == pytest.approx(3.825, abs=1e-9)                                                        # "3.8 mm into the front cap's holes"
    hole_depth = P.NEMA17T_TAP_DEPTH
    for i in (1, 2, 3, 4):
        s = stations["detailed_fin1p8"][f"screw_{i}"]
        assert s.BoundingBox().ymin == pytest.approx(meas["tab_back_y"] - P.THERMAL_SCREW_LEN_DETAILED, abs=1e-6)
        front = cap.BoundingBox().ymax - P.NEMA17T_PILOT_H                                                  # the cap's front face
        assert front == pytest.approx(meas["tab_front_y"] - t, abs=1e-6)                                   # on the fin's motor face
        assert front - s.BoundingBox().ymin == pytest.approx(engaged, abs=1e-6)
        assert s.intersect(cap).Volume() < VOL_TOL
        assert s.distance(cap) < 1e-9 and hole_depth - engaged == pytest.approx(0.675, abs=1e-9)           # tip stands 0.675 above the hole bottom


# ---------------------------------------------------------------------------------------------------------------------
# inserts
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_insert_sleeves_sit_in_their_pockets(stations, meas, key):
    sl = stations[key]["slipin_mount"]
    d = meas["deck"]
    s = stations[key]["insert_deck"]
    x0, x1, y0, y1, z0, z1 = _bb(s)
    assert 2 * d["r"] == pytest.approx(P.THERMAL_DECK_INSERT_OD, abs=1e-6)                                  # the pocket is the Ø4.1 of the spec
    assert d["z_top"] - d["z_bottom"] == pytest.approx(7.0, abs=1e-6)                                      # 7 deep
    assert z1 == pytest.approx(d["z_top"], abs=1e-6)                                                       # flush with the deck face
    assert z1 - z0 == pytest.approx(P.THERMAL_DECK_INSERT_LEN, abs=1e-6) and z0 > d["z_bottom"]            # 5.7 long, 1.3 above the pocket bottom
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx(d["xy"], abs=1e-6)
    assert s.Volume() == pytest.approx(math.pi / 4 * (P.THERMAL_DECK_INSERT_OD ** 2 - P.THERMAL_DECK_INSERT_ID ** 2) * P.THERMAL_DECK_INSERT_LEN, abs=VOL_TOL)
    assert s.intersect(sl).Volume() < VOL_TOL
    for i, e in enumerate(meas["enc"], start=1):
        s = stations[key][f"insert_enc_{i}"]
        x0, x1, y0, y1, z0, z1 = _bb(s)
        assert 2 * e["r"] == pytest.approx(P.THERMAL_ENC_INSERT_OD, abs=1e-6)
        assert e["x_open"] - e["x_bottom"] == pytest.approx(4.0, abs=1e-6)                                  # 4 deep, open at the divot floor
        assert (x0, x1) == pytest.approx((e["x_bottom"], e["x_open"]), abs=1e-6)                           # flush with the floor, on the hole bottom
        assert ((y0 + y1) / 2, (z0 + z1) / 2) == pytest.approx(e["yz"], abs=1e-6)
        assert s.Volume() == pytest.approx(math.pi / 4 * (P.THERMAL_ENC_INSERT_OD ** 2 - P.THERMAL_ENC_INSERT_ID ** 2) * P.THERMAL_ENC_INSERT_LEN, abs=VOL_TOL)
        assert s.intersect(sl).Volume() < VOL_TOL
    pitch = sorted({round(e["yz"][0], 3) for e in meas["enc"]}), sorted({round(e["yz"][1], 3) for e in meas["enc"]})
    assert pitch[0][1] - pitch[0][0] == pytest.approx(P.THERMAL_ENC_HOLE_PITCH, abs=1e-3) and pitch[1][1] - pitch[1][0] == pytest.approx(P.THERMAL_ENC_HOLE_PITCH, abs=1e-3)


# ---------------------------------------------------------------------------------------------------------------------
# motor shift per variant
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,shift,shaft_end", [("fin1p8", -1.175, 20.825), ("fin0p019", 1.517, 23.517)])
def test_motor_shift_per_variant(stations, key, shift, shaft_end):
    t = dict((k, tt) for k, tt, _ in P.THERMAL_VARIANTS)[key]
    ref_block = max(T.reference("Motor_Reference").Solids(), key=lambda s: s.Volume())
    block = stations[key]["motor_block"]
    dy = block.BoundingBox().ymax - ref_block.BoundingBox().ymax
    assert dy == pytest.approx(P.FIN1021_REF_T - t, abs=1e-9) and dy == pytest.approx(shift, abs=1e-3)       # 2.0 - t
    assert block.BoundingBox().ymax == pytest.approx(stations[key]["fin_in"].BoundingBox().ymin, abs=1e-9)  # front face on the fin's motor face
    assert (block.BoundingBox().xmin, block.BoundingBox().xmax, block.BoundingBox().zmin, block.BoundingBox().zmax) == pytest.approx(
        (ref_block.BoundingBox().xmin, ref_block.BoundingBox().xmax, ref_block.BoundingBox().zmin, ref_block.BoundingBox().zmax), abs=1e-9)
    shaft = min(T.reference("Motor_Reference").Solids(), key=lambda s: s.Volume())
    assert shaft.BoundingBox().ymax + dy == pytest.approx(shaft_end, abs=1e-3 + P.ENC1021_REF_RESIDUAL[1])   # shaft end y 20.83 / 23.52 (+ the file's 0.0016)
    assert block.Volume() == pytest.approx(ref_block.Volume() - 4 * math.pi * (P.THERMAL_MOTOR_HOLE_D / 2) ** 2 * P.THERMAL_MOTOR_HOLE_DEPTH, abs=VOL_TOL)


def test_motor_block_is_the_block_without_the_shaft(stations):
    solids = T.reference("Motor_Reference").Solids()
    assert len(solids) == 2
    block = max(solids, key=lambda s: s.Volume())
    assert block.BoundingBox().ylen == pytest.approx(38.0, abs=1e-6) and block.BoundingBox().xlen == pytest.approx(42.3, abs=1e-6)
    assert max(b.BoundingBox().ymax for b in (stations["fin1p8"]["motor_block"],)) < 0.0                  # nothing of the shaft: it stays behind the tab face


# ---------------------------------------------------------------------------------------------------------------------
# fin split
# ---------------------------------------------------------------------------------------------------------------------
def test_split_plane_is_the_roof_plate_top_at_the_slot():
    """z = 31.16: the roof plate (z 27.84 .. 31.16) of the Shell_Casing at the fin slot, re-measured on the slot walls (F6 of verification/thermal_assembly_1p5a_check.md)."""
    assert P.THERMAL_FIN_SPLIT_Z == 31.16
    z = T.measure_shell_top_z()
    assert z == pytest.approx(P.THERMAL_FIN_SPLIT_Z, abs=P.THERMAL_FIN_SPLIT_TOL)
    slot = T.measure_shell_slot()
    assert slot["z_lo"] == pytest.approx(27.84, abs=0.01) and slot["z_hi"] == pytest.approx(31.16, abs=0.01)    # roof plate 3.32 thick
    assert slot["z_hi"] - slot["z_lo"] == pytest.approx(3.32, abs=0.01)
    assert z == pytest.approx(slot["z_hi"], abs=1e-12)
    # the funnel above the roof plate (z 33 .. 37) is outside air: the split is below it
    assert z < 33.0


@pytest.mark.parametrize("key", KEYS)
def test_fin_split_in_two_named_solids(stations, key):
    t = dict((k, tt) for k, tt, _ in P.THERMAL_VARIANTS)[key]
    fin = H.make_fin(t)
    fi, fo = stations[key]["fin_in"], stations[key]["fin_out"]
    assert fi.Volume() + fo.Volume() == pytest.approx(fin.Volume(), abs=0.01)
    assert _bb(fi)[5] == pytest.approx(P.THERMAL_FIN_SPLIT_Z, abs=1e-9) and _bb(fo)[4] == pytest.approx(P.THERMAL_FIN_SPLIT_Z, abs=1e-9)
    assert _bb(fi)[4] == pytest.approx(_bb(fin)[4], abs=1e-9) and _bb(fo)[5] == pytest.approx(_bb(fin)[5], abs=1e-9)
    # the bottom part holds all 5 holes; the top part is the plain plate
    assert len([f for f in fi.Faces() if f.geomType() == "CYLINDER"]) >= 5 and not [f for f in fo.Faces() if f.geomType() == "CYLINDER"]
    assert fi.intersect(fo).Volume() < 1e-9
    height = P.THERMAL_FIN_SPLIT_Z - _bb(fin)[4]
    assert height == pytest.approx(49.5, abs=0.1)                                                           # split height above the fin's bottom edge: 49.52 mm


@pytest.mark.parametrize("key", KEYS)
def test_fin_halves_touch_on_the_split_plane(reports, key):
    t = dict((k, tt) for k, tt, _ in P.THERMAL_VARIANTS)[key]
    c = _contact(reports[key], "fin_in", "fin_out")
    assert c is not None and c["distance"] < 1e-9 and c["overlap"] < 1e-9
    assert c["area"] == pytest.approx((P.FIN1021_X_MAX - P.FIN1021_X_MIN) * t, abs=HOLE_AREA_TOL)         # the plate cross-section, 42 x t


# ---------------------------------------------------------------------------------------------------------------------
# exports: named components, assembly coordinates
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_step_has_every_solid_named_in_assembly_coordinates(stations, key):
    path = os.path.join(T.STEP_DIR, f"thermal_station1021_{key}.step")
    assert os.path.isfile(path), "run /usr/bin/python3 -m cad.thermal_station1021"
    named = N.read_named_step(path)
    assert sorted(named) == sorted(EXPECTED_NAMES[key])
    for n, shape in named.items():
        built = stations[key][n]
        assert len(shape.Solids()) == 1 and shape.isValid(), n
        assert shape.Volume() == pytest.approx(built.Volume(), rel=1e-6), n
        b, s = _bb(built), _bb(shape)
        assert s == pytest.approx((b[0] + O[0], b[1] + O[0], b[2] + O[1], b[3] + O[1], b[4] + O[2], b[5] + O[2]), abs=5e-3), n   # assembly coordinates = station + O


def test_step_reimport_is_a_single_compound_of_all_bodies():
    for key in KEYS:
        shape = cq.importers.importStep(os.path.join(T.STEP_DIR, f"thermal_station1021_{key}.step")).val()
        assert len(shape.Solids()) == len(EXPECTED_NAMES[key])


@pytest.mark.parametrize("key", KEYS)
def test_body_table_and_contact_files(stations, key):
    import csv
    rows = list(csv.reader(open(os.path.join(T.RENDER_DIR, f"thermal_station1021_{key}_bodies.csv"))))
    assert rows[0][:6] == ["name", "material to assign", "k W/m.K", "density g/cm3", "volume mm3", "mass g"]
    body_rows = [r for r in rows[1:] if r and r[0] != "total"]
    assert [r[0] for r in body_rows] == EXPECTED_NAMES[key]
    for r in body_rows:
        assert float(r[4]) == pytest.approx(stations[key][r[0]].Volume(), abs=1e-3) and float(r[5]) > 0 and r[1] and float(r[2]) > 0
    assert os.path.isfile(os.path.join(T.RENDER_DIR, f"thermal_station1021_{key}_contacts.csv"))


def test_masses_in_the_table(stations):
    tab = {r["name"]: r for r in T.body_table(stations["fin1p8"], "block")}
    assert tab["motor_block"]["mass_g"] == pytest.approx(P.THERMAL_MOTOR_MASS_G, abs=1.0)            # effective density: the block weighs the motor
    assert tab["fin_in"]["mass_g"] + tab["fin_out"]["mass_g"] == pytest.approx(72.65, abs=0.05)       # 1/8 in 6061
    assert tab["slipin_mount"]["material"] == "PETG" and tab["slipin_mount"]["density"] == 1.27
    assert tab["screw_1"]["density"] == 7.85 and tab["insert_deck"]["density"] == 8.5
    det = {r["name"]: r for r in T.body_table(stations["detailed_fin1p8"], "detailed")}
    assert sum(det[n]["mass_g"] for n in P.NEMA17T_BODIES) == pytest.approx(P.THERMAL_MOTOR_MASS_G, rel=0.06)   # the multi-body motor weighs about the same


def test_section_renders_exist():
    for key in KEYS:
        assert os.path.getsize(os.path.join(T.RENDER_DIR, f"thermal_station1021_{key}_section_screws.png")) > 5_000


# ---------------------------------------------------------------------------------------------------------------------
# findings the export does not contain: shell slot, screw lengths
# ---------------------------------------------------------------------------------------------------------------------
def test_shell_slot_finding():
    f = T.shell_findings()
    y_motor, y_spool = f["slot_y"]
    assert y_spool - y_motor == pytest.approx(5.0, abs=0.01)                                            # measured slot: 5.0 wide
    thick, thin = f["variants"]["fin1p8"], f["variants"]["fin0p019"]
    assert thick["fin_shell_overlap"] == pytest.approx(69.0, abs=5.0)                                   # spec: about 69 mm3
    assert thick["overlap_y"][0] == pytest.approx(-P.FIN1021_T_PRODUCTION_MM, abs=1e-3) and thick["overlap_y"][1] == pytest.approx(y_motor, abs=1e-3)
    assert thin["fin_shell_overlap"] == pytest.approx(0.0, abs=1e-6)                                    # the 0.019 in fin clears the wall
    assert thick["slot_open_to_y"] == pytest.approx(-3.675, abs=1e-9) and round(thick["slot_open_to_y"], 1) == -3.7
    for key in KEYS:                                                                                      # the motor (block or the multi-body one) stays inside the shell
        assert f["variants"][key]["motor_shell_overlap"] == pytest.approx(0.0, abs=1e-6) and f["variants"][key]["motor_shell_gap"] > 1.5, key


def test_screw_length_finding():
    f = T.screw_findings()
    assert f["fin1p8"]["engagement"] == pytest.approx(3.825, abs=1e-9)                                  # M3 x 12 behind the 1/8 in fin
    assert f["fin0p019 (M3 x 8)"]["engagement"] == pytest.approx(2.517, abs=1e-9)
    assert f["fin0p019 (M3 x 10)"]["engagement"] == pytest.approx(4.517, abs=1e-9)
    assert 3.0 <= f["fin1p8"]["engagement"] <= 4.5 and f["fin0p019 (M3 x 10)"]["engagement"] > P.THERMAL_MOTOR_HOLE_DEPTH       # M3 x 10 > the 4.0 mm hole of the model
