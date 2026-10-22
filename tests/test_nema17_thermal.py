"""
Acceptance checks for the multi-body NEMA 17 thermal model (cad/parts/nema17_thermal.py, parameters NEMA17T_*, spec cad/HEAT_FIN_1021_SPEC.md section E).

Motor frame: front face at y = 0, axis +y.  Bodies front to back: front_cap, stator, winding, rear_cap, shaft, connector (each a separate named STEP component;
no rotor, the cavity inside the winding is air).  Everything is measured on the built B-rep solids and on the exported STEP files.
Run with /usr/bin/python3 -m pytest tests/test_nema17_thermal.py
"""

from __future__ import annotations

import csv
import itertools
import math
import os
import sys

import pytest

cq = pytest.importorskip("cadquery")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import nema17_thermal as N                        # noqa: E402
from cad.reference.station_1021.extract import O                 # noqa: E402

H = P.NEMA17T_SIZE / 2                                           # 21.15
FRONT_CAP_Y = (-P.NEMA17T_CAP_LEN, P.NEMA17T_PILOT_H)            # the boss is part of the front cap
TOL = 1e-6


def _bb(sh):
    b = sh.BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


@pytest.fixture(scope="module")
def bodies():
    return N.make_bodies()


def _probe(shape):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt
    c = BRepClass3d_SolidClassifier(shape.Solids()[0].wrapped)

    def inside(p):
        c.Perform(gp_Pnt(*p), 1e-7)
        return c.State() == TopAbs_IN
    return inside


# ---------------------------------------------------------------------------------------------------------------------
# parameters and the body list
# ---------------------------------------------------------------------------------------------------------------------
def test_parameters_are_the_briefed_values():
    assert (P.NEMA17T_SIZE, P.NEMA17T_LEN, P.NEMA17T_CORNER_CHAMFER) == (42.3, 38.0, 3.0)
    assert (P.NEMA17T_CAP_LEN, P.NEMA17T_STATOR_LEN) == (8.0, 22.0) and P.NEMA17T_LEN == 2 * P.NEMA17T_CAP_LEN + P.NEMA17T_STATOR_LEN
    assert (P.NEMA17T_PILOT_D, P.NEMA17T_PILOT_H, P.NEMA17T_HOLE_SQ) == (22.0, 2.0, 31.0)
    assert (P.NEMA17T_TAP_D, P.NEMA17T_TAP_DEPTH) == (3.0, 4.5)
    assert (P.NEMA17T_STATOR_BORE_D, P.NEMA17T_WINDING_ID, P.NEMA17T_SHAFT_D) == (34.0, 23.0, 5.0)
    assert (P.NEMA17T_SHAFT_PROUD, P.NEMA17T_SHAFT_REAR_INSET, P.NEMA17T_CONNECTOR) == (24.0, 1.0, (16.0, 6.0, 6.0))
    assert P.NEMA17T_BORE_D_SPEC == 5.2 and P.NEMA17T_CAP_BORE_D == 5.0       # the brief's Ø5.2 is built as Ø5.0 so the shaft touches the caps
    assert P.NEMA17T_BODIES == ("front_cap", "stator", "winding", "rear_cap", "shaft", "connector")


def test_body_list_and_one_valid_solid_each(bodies):
    assert list(bodies) == ["front_cap", "stator", "winding", "rear_cap", "shaft", "connector"]
    for n, s in bodies.items():
        assert s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0, n


def test_matches_the_station_motor_reference_envelope(bodies):
    """42.3 x 42.3 x 38 like Motor_Reference (y -40 .. -2 in the station frame: 38 long, 42.3 square), shaft 24 proud of the front face."""
    import cad.parts.encoder1021 as E
    ref = max(E.reference_parts(True)["Motor_Reference"].Solids(), key=lambda s: s.Volume()).BoundingBox()
    assert (ref.xlen, ref.ylen, ref.zlen) == pytest.approx((P.NEMA17T_SIZE, P.NEMA17T_LEN, P.NEMA17T_SIZE), abs=1e-6)
    body_boxes = [_bb(bodies[n]) for n in ("front_cap", "stator", "rear_cap")]
    assert (min(b[0] for b in body_boxes), max(b[1] for b in body_boxes)) == pytest.approx((-H, H), abs=TOL)
    assert (min(b[4] for b in body_boxes), max(b[5] for b in body_boxes)) == pytest.approx((-H, H), abs=TOL)
    assert min(b[2] for b in body_boxes) == pytest.approx(-P.NEMA17T_LEN, abs=TOL)
    shaft = _bb(bodies["shaft"])
    ref_shaft = min(E.reference_parts(True)["Motor_Reference"].Solids(), key=lambda s: s.Volume()).BoundingBox()
    assert shaft[3] - 0.0 == pytest.approx(P.NEMA17T_SHAFT_PROUD, abs=TOL)                                   # 24 mm proud of the front face
    assert ref_shaft.ymax - (-2.0) == pytest.approx(P.NEMA17T_SHAFT_PROUD, abs=1e-6)                         # as in the reference (y -2 .. 22)


# ---------------------------------------------------------------------------------------------------------------------
# dimensions of each body
# ---------------------------------------------------------------------------------------------------------------------
def test_front_cap(bodies):
    cap = bodies["front_cap"]
    x0, x1, y0, y1, z0, z1 = _bb(cap)
    assert (x0, x1, z0, z1) == pytest.approx((-H, H, -H, H), abs=TOL)
    assert (y0, y1) == pytest.approx(FRONT_CAP_Y, abs=TOL)                                                  # y -8 .. 0 plus the 2 mm boss
    inside = _probe(cap)
    r_boss = P.NEMA17T_PILOT_D / 2
    assert inside((r_boss - 0.1, 1.0, 0.0)) and not inside((r_boss + 0.1, 1.0, 0.0))                       # Ø22 x 2 boss on the front face
    assert not inside((0.0, 1.0, 2.0)) and inside((0.0, 1.0, 3.0))                                          # Ø5.0 bore through the boss (r 2.5), boss material around it
    assert inside((8.0, 1.0, 0.0)) and not inside((8.0, 2.01, 0.0))                                         # the boss ends 2 mm in front of the face
    assert inside((10.0, -0.01, 10.0)) and not inside((10.0, 0.01, 10.0))                                   # outside r 11 nothing stands in front of y = 0
    from cad.thermal_station1021 import cylinders
    taps = cylinders(cap, P.NEMA17T_TAP_D / 2, "y")
    assert len(taps) == 4
    h = P.NEMA17T_HOLE_SQ / 2
    assert sorted(t["c"] for t in taps) == pytest.approx(sorted((sx * h, sz * h) for sx in (-1, 1) for sz in (-1, 1)), abs=TOL)
    for t in taps:
        assert (t["lo"], t["hi"]) == pytest.approx((-P.NEMA17T_TAP_DEPTH, 0.0), abs=TOL)                    # Ø3.0 x 4.5 deep from the front face
    bore = cylinders(cap, P.NEMA17T_CAP_BORE_D / 2, "y")
    assert len(bore) == 1 and bore[0]["c"] == pytest.approx((0.0, 0.0), abs=TOL) and (bore[0]["lo"], bore[0]["hi"]) == pytest.approx(FRONT_CAP_Y, abs=TOL)


def test_stator(bodies):
    s = bodies["stator"]
    assert _bb(s) == pytest.approx((-H, H, -P.NEMA17T_CAP_LEN - P.NEMA17T_STATOR_LEN, -P.NEMA17T_CAP_LEN, -H, H), abs=TOL)                 # 22 long behind the front cap
    from cad.thermal_station1021 import cylinders
    bore = cylinders(s, P.NEMA17T_STATOR_BORE_D / 2, "y")
    assert len(bore) == 1 and bore[0]["c"] == pytest.approx((0.0, 0.0), abs=TOL) and bore[0]["hi"] - bore[0]["lo"] == pytest.approx(22.0, abs=TOL)      # bore Ø34
    area = P.NEMA17T_SIZE ** 2 - 4 * P.NEMA17T_CORNER_CHAMFER ** 2 / 2 - math.pi * 17.0 ** 2
    assert s.Volume() == pytest.approx(area * P.NEMA17T_STATOR_LEN, rel=1e-9)


@pytest.mark.parametrize("name", ["front_cap", "stator", "rear_cap"])
def test_corner_chamfers_45_deg_3_mm(bodies, name):
    """Four chamfers 3 x 3 on the long edges: the corner is cut along x + z = 2H - 3 (inside just before it, outside just after it)."""
    s = bodies[name]
    inside = _probe(s)
    y = {"front_cap": -4.0, "stator": -19.0, "rear_cap": -34.0}[name]
    c = P.NEMA17T_CORNER_CHAMFER
    edge = 2 * H - c                                                       # x + z = 39.3 on the +x +z corner
    for sx, sz in itertools.product((-1, 1), (-1, 1)):
        d = 0.05
        assert inside((sx * (edge / 2 - d), y, sz * (edge / 2 - d)))
        assert not inside((sx * (edge / 2 + d), y, sz * (edge / 2 + d)))
    chamfers = [f for f in s.Faces() if f.geomType() == "PLANE" and abs(abs(f.normalAt().x) - math.sqrt(0.5)) < 1e-6 and abs(abs(f.normalAt().z) - math.sqrt(0.5)) < 1e-6]
    assert len(chamfers) == 4
    length = {"front_cap": P.NEMA17T_CAP_LEN, "stator": P.NEMA17T_STATOR_LEN, "rear_cap": P.NEMA17T_CAP_LEN}[name]
    assert all(f.Area() == pytest.approx(c * math.sqrt(2) * length, rel=1e-9) for f in chamfers)         # 45 degrees, leg 3 mm


def test_winding_is_inside_the_stator(bodies):
    w, s = bodies["winding"], bodies["stator"]
    from cad.thermal_station1021 import cylinders
    assert _bb(w) == pytest.approx((-17.0, 17.0, -30.0, -8.0, -17.0, 17.0), abs=TOL)                    # annulus Ø34 outside, 22 long, same y span as the stator
    wb, sb = _bb(w), _bb(s)
    assert wb[0] >= sb[0] and wb[1] <= sb[1] and wb[2] == pytest.approx(sb[2], abs=TOL) and wb[3] == pytest.approx(sb[3], abs=TOL) and wb[4] >= sb[4] and wb[5] <= sb[5]
    assert w.Volume() == pytest.approx(math.pi / 4 * (34.0 ** 2 - 23.0 ** 2) * 22.0, rel=1e-9)         # annulus Ø23 .. Ø34 x 22
    outer = cylinders(w, 17.0, "y")
    inner = cylinders(w, 11.5, "y")
    assert len(outer) == 1 and len(inner) == 1 and outer[0]["c"] == pytest.approx((0.0, 0.0), abs=TOL)
    # the winding's outer face is the stator's bore (shared cylindrical face, no overlap)
    assert w.intersect(s).Volume() < 1e-6 and w.distance(s) < 1e-9
    inside = _probe(s)
    assert not inside((16.9, -19.0, 0.0)) and inside((17.1, -19.0, 0.0))                              # the stator's wall starts at r 17
    inside_w = _probe(w)
    assert inside_w((14.0, -19.0, 0.0)) and not inside_w((10.0, -19.0, 0.0)) and not inside_w((0.0, -19.0, 0.0))     # air inside the winding


def test_rear_cap_shaft_and_connector(bodies):
    rc, sh, cn = bodies["rear_cap"], bodies["shaft"], bodies["connector"]
    assert _bb(rc) == pytest.approx((-H, H, -P.NEMA17T_LEN, -P.NEMA17T_CAP_LEN - P.NEMA17T_STATOR_LEN, -H, H), abs=TOL)
    from cad.thermal_station1021 import cylinders
    seat = cylinders(rc, P.NEMA17T_CAP_BORE_D / 2, "y")
    assert len(seat) == 1 and seat[0]["hi"] - seat[0]["lo"] == pytest.approx(P.NEMA17T_CAP_LEN - P.NEMA17T_SHAFT_REAR_INSET, abs=TOL)       # blind seat, 7 deep
    assert _bb(sh) == pytest.approx((-2.5, 2.5, -P.NEMA17T_LEN + P.NEMA17T_SHAFT_REAR_INSET, P.NEMA17T_SHAFT_PROUD, -2.5, 2.5), abs=TOL)  # y -37 .. 24
    assert sh.Volume() == pytest.approx(math.pi * 2.5 ** 2 * 61.0, rel=1e-9)
    assert _bb(cn) == pytest.approx((H, H + 6.0, -P.NEMA17T_LEN, -P.NEMA17T_LEN + 6.0, -8.0, 8.0), abs=TOL)       # 16 (z) x 6 (y) x 6 (x), flush with the back face on the +x side face
    assert cn.Volume() == pytest.approx(16 * 6 * 6, abs=1e-9)
    assert cn.BoundingBox().ymin == pytest.approx(rc.BoundingBox().ymin, abs=TOL)


# ---------------------------------------------------------------------------------------------------------------------
# no overlaps; the shaft touches the bores
# ---------------------------------------------------------------------------------------------------------------------
def test_no_two_bodies_overlap(bodies):
    for a, b in itertools.combinations(bodies, 2):
        assert bodies[a].intersect(bodies[b]).Volume() < 1e-6, (a, b)


def test_shaft_surface_is_coincident_with_the_bores(bodies):
    from cad.thermal_station1021 import contact_area
    cyl = lambda a, b: contact_area(bodies[a], bodies[b])[2].get("cyl", 0.0)
    assert cyl("shaft", "front_cap") == pytest.approx(math.pi * 5.0 * (P.NEMA17T_CAP_LEN + P.NEMA17T_PILOT_H), abs=0.01)     # 10 mm: the cap and its boss
    assert cyl("shaft", "rear_cap") == pytest.approx(math.pi * 5.0 * 7.0, abs=0.01)
    assert bodies["shaft"].distance(bodies["stator"]) > 0.0 and bodies["shaft"].distance(bodies["winding"]) > 5.0     # air around the shaft inside the stator
    assert bodies["shaft"].distance(bodies["winding"]) == pytest.approx(11.5 - 2.5, abs=1e-6)


# ---------------------------------------------------------------------------------------------------------------------
# screws in the front cap, station placement
# ---------------------------------------------------------------------------------------------------------------------
def test_screws_reach_3p8_mm_into_the_front_cap_holes():
    from cad import thermal_station1021 as T
    st = T.build_station("detailed_fin1p8")
    t = P.FIN1021_T_PRODUCTION_MM
    cap = st["front_cap"]
    front = _bb(cap)[3] - P.NEMA17T_PILOT_H
    holes = T.cylinders(cap, P.NEMA17T_TAP_D / 2, "y")
    assert len(holes) == 4
    for i in (1, 2, 3, 4):
        s = st[f"screw_{i}"]
        sb = _bb(s)
        h = next(h for h in holes if h["c"] == pytest.approx(((sb[0] + sb[1]) / 2, (sb[4] + sb[5]) / 2), abs=1e-6))      # on a hole axis
        assert front - sb[2] == pytest.approx(3.825, abs=1e-6)                                                            # 3.8 mm in
        assert h["hi"] - h["lo"] == pytest.approx(P.NEMA17T_TAP_DEPTH, abs=1e-6) and sb[2] > h["lo"]                      # not bottomed
        assert s.intersect(cap).Volume() < 1e-6
        # shank fills the hole to that depth: shank volume inside the hole cylinder = pi r^2 x 3.825
        inner = T._cyl(P.NEMA17T_TAP_D / 2, (h["c"][0], h["lo"], h["c"][1]), "y", P.NEMA17T_TAP_DEPTH)
        assert s.intersect(inner).Volume() == pytest.approx(math.pi * 1.5 ** 2 * 3.825, abs=1e-3)
    assert front == pytest.approx(T.motor_front_face_y(t), abs=1e-9)                                                      # the cap's front face is the fin's motor face


def test_placement_in_the_station_frame(bodies):
    t = P.FIN1021_T_PRODUCTION_MM
    dx, dy, dz = P.ENC1021_REF_RESIDUAL
    placed = N.to_station(bodies["front_cap"], t)
    b = _bb(placed)
    assert b[3] - P.NEMA17T_PILOT_H == pytest.approx(dy - t, abs=1e-9)                                  # front face y = -t (+ the file residual)
    assert ((b[0] + b[1]) / 2, (b[4] + b[5]) / 2) == pytest.approx((dx, P.ENC1021_REF_SHIFT_Z + dz), abs=1e-9)          # axis x 0, z 2.64 (+ residual)
    asm = N.to_station(bodies["front_cap"], t, assembly=True)
    assert _bb(asm) == pytest.approx((b[0] + O[0], b[1] + O[0], b[2] + O[1], b[3] + O[1], b[4] + O[2], b[5] + O[2]), abs=1e-9)
    shaft = _bb(N.to_station(bodies["shaft"], t))
    assert shaft[3] == pytest.approx(22.0 + (P.FIN1021_REF_T - t) + dy, abs=1e-6)                       # shaft end 20.825 (+ residual 0.0016) with the 1/8 in fin


# ---------------------------------------------------------------------------------------------------------------------
# exports and the body table
# ---------------------------------------------------------------------------------------------------------------------
def test_motor_frame_step_has_six_named_components(bodies):
    path = os.path.join(N.STEP_DIR, "nema17_thermal.step")
    assert os.path.isfile(path), "run /usr/bin/python3 -m cad.parts.nema17_thermal"
    named = N.read_named_step(path)
    assert list(named) == list(P.NEMA17T_BODIES)
    for n, shape in named.items():
        assert len(shape.Solids()) == 1 and shape.isValid()
        assert shape.Volume() == pytest.approx(bodies[n].Volume(), rel=1e-6), n
        assert _bb(shape) == pytest.approx(_bb(bodies[n]), abs=5e-3), n                                   # motor frame: front face y = 0, shaft to y = 24
    assert _bb(named["front_cap"])[3] - P.NEMA17T_PILOT_H == pytest.approx(0.0, abs=5e-3) and _bb(named["shaft"])[3] == pytest.approx(24.0, abs=5e-3)


@pytest.mark.parametrize("key,t", [("fin1p8", P.FIN1021_T_PRODUCTION_MM), ("fin0p019", P.FIN1021_T_PROTOTYPE_MM)])
def test_asm1021_copies_have_the_front_face_on_the_fin(bodies, key, t):
    path = os.path.join(N.STEP_DIR, f"nema17_thermal_{key}_asm1021.step")
    assert os.path.isfile(path)
    named = N.read_named_step(path)
    assert list(named) == list(P.NEMA17T_BODIES)
    dx, dy, dz = P.ENC1021_REF_RESIDUAL
    front = _bb(named["front_cap"])[3] - P.NEMA17T_PILOT_H
    assert front == pytest.approx(O[1] + dy - t, abs=5e-3)                                                # fin motor face y = -t, in asm1021 coordinates
    for n, shape in named.items():
        assert shape.Volume() == pytest.approx(bodies[n].Volume(), rel=1e-6)
        b0, b1 = _bb(bodies[n]), _bb(shape)
        assert b1[2] - b0[2] == pytest.approx(O[1] + dy - t, abs=5e-3), n


def test_body_table():
    rows = N.body_table()
    assert [r["name"] for r in rows] == list(P.NEMA17T_BODIES)
    surf = {r["name"]: r["surface"] for r in rows}
    assert surf["stator"] == "black painted steel" and surf["front_cap"] == "aluminium end cap" and surf["rear_cap"] == "aluminium end cap"
    assert surf["connector"] == "plastic connector"
    assert all(r["k"] > 0 and r["volume"] > 0 and r["material"] and r["mass_g"] > 0 for r in rows)
    assert {r["name"]: r["k"] for r in rows}["connector"] < 1.0 < {r["name"]: r["k"] for r in rows}["front_cap"]
    assert sum(r["mass_g"] for r in rows) == pytest.approx(P.THERMAL_MOTOR_MASS_G, rel=0.06)                # about the 0.28 kg motor
    path = os.path.join(N.RENDER_DIR, "nema17_thermal_bodies.csv")
    got = list(csv.reader(open(path)))
    assert got[0][:6] == ["name", "suggested material", "k W/m.K", "density g/cm3", "volume mm3", "mass g"]
    assert [r[0] for r in got[1:-1]] == list(P.NEMA17T_BODIES) and got[-1][0] == "total"


def test_renders_exist():
    for tag in ("front_iso", "rear_iso", "section_z0"):
        assert os.path.getsize(os.path.join(N.RENDER_DIR, f"nema17_thermal_{tag}.png")) > 5_000
