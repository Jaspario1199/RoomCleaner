"""
Acceptance checks for the heat fin 1021 (cad/parts/heat_fin1021.py, spec cad/HEAT_FIN_1021_SPEC.md section 3A, parameters FIN1021_* in cad/params.py).

The fin is the y = 0 face of Jasper's Heat_horn extruded toward -y: 1/8 in (3.175 mm) production and 0.019 in (0.483 mm) prototype record.
Everything is measured on the built B-rep solids and on the exported files (STEP reimport, STL mesh, DXF, drawing), against the reference STEP
cad/reference/station_1021/Heat_horn.step and, where available, the original assembly STEP.  Run with
    /usr/bin/python3 -m pytest tests/test_heat_fin1021.py
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
from cad.parts import heat_fin1021 as H                          # noqa: E402
from cad.reference.station_1021.extract import O, SRC            # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isfile(H.HORN_STEP), reason="station_1021 reference parts not available")

KEYS = list(H.VARIANTS)
EDGE_TOL = 0.005                                                 # mm, the measured outline numbers are rounded to 0.1 in the spec
HORN_AREA = 8474.2753687                                         # mm2, y = 0 face of the Heat_horn as measured by the lead / this builder


def _bb(sh):
    b = sh.BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


def _stl_mesh(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    assert len(d) == 84 + 50 * n, "binary STL expected"
    arr = np.frombuffer(d, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)
    return arr["v"].astype(float)


def _mesh_volume(tris):
    return float(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6.0)


@pytest.fixture(scope="module")
def fins():
    return {k: H.make_fin(t) for k, t in H.VARIANTS.items()}


@pytest.fixture(scope="module")
def outline():
    return H.measure_outline()


# ---------------------------------------------------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------------------------------------------------
def test_thickness_options():
    assert P.FIN1021_T_PRODUCTION_MM == pytest.approx(0.125 * 25.4, abs=1e-9)             # 1/8 in
    assert P.FIN1021_T_PROTOTYPE_MM == pytest.approx(0.019 * 25.4, abs=0.001)             # 0.019 in = 0.4826, spec value 0.483
    assert H.VARIANTS == {"1p8": P.FIN1021_T_PRODUCTION_MM, "0p019": P.FIN1021_T_PROTOTYPE_MM}
    assert P.FIN1021_REF_T == 2.0
    assert "6061-T6" in P.FIN1021_ALLOY and "5052-H32" in P.FIN1021_ALLOY and "1/8" in P.FIN1021_ALLOY
    assert "matte black" in P.FIN1021_FINISH and "motor contact square" in P.FIN1021_FINISH
    assert P.FIN1021_Z_MAX == pytest.approx(P.FIN1021_Z_MIN + P.FIN1021_H_RIGHT)
    assert math.hypot(P.FIN1021_X_MAX - P.FIN1021_X_MIN, P.FIN1021_H_RIGHT - P.FIN1021_H_LEFT) == pytest.approx(53.413, abs=0.001)
    assert round(P.FIN1021_TOP_EDGE_MM, 1) == 53.4


def test_master_values_are_not_modified_by_this_task():
    """The new block only appends: the values this task must not touch are as before."""
    assert P.ENC1021_CAP_PEG_LEN == 3.4 and P.ENC1021_SPOOL_FACE_Y == 26.0 and P.ENC1021_SHAFT_END_Y == 22.0
    assert P.ENC1021_REF_RESIDUAL == (0.004243, 0.001645, 0.003854)


# ---------------------------------------------------------------------------------------------------------------------
# the outline equals the reference (measured on the Heat_horn face itself)
# ---------------------------------------------------------------------------------------------------------------------
def test_reference_outline_numbers(outline):
    """The lead's measured values, re-checked on the Heat_horn y = 0 face (residual removed)."""
    assert outline["area"] == pytest.approx(HORN_AREA, rel=1e-9)
    e = outline["edge_lengths"]
    assert e == pytest.approx([42.0, math.hypot(42.0, 33.0), 195.6, 228.6], abs=EDGE_TOL)       # bottom, slanted top, left, right (long) side
    assert round(e[1], 1) == P.FIN1021_TOP_EDGE_MM
    assert (outline["x_min"], outline["x_max"]) == pytest.approx((P.FIN1021_X_MIN, P.FIN1021_X_MAX), abs=EDGE_TOL)
    assert (outline["z_min"], outline["z_max"]) == pytest.approx((P.FIN1021_Z_MIN, P.FIN1021_Z_MAX), abs=EDGE_TOL)


def test_reference_holes(outline):
    holes = outline["holes"]
    assert len(holes) == 5
    ax, az = P.FIN1021_AXIS_XZ
    pilot = [h for h in holes if h[2] > 10]
    small = [h for h in holes if h[2] < 10]
    assert len(pilot) == 1 and len(small) == 4
    assert pilot[0] == pytest.approx((ax, az, P.FIN1021_PILOT_D), abs=EDGE_TOL)
    h = P.FIN1021_HOLE_SQ / 2
    expect = sorted((ax + sx * h, az + sz * h) for sx in (-1, 1) for sz in (-1, 1))
    assert [v for p in sorted((x, z) for x, z, _ in small) for v in p] == pytest.approx([v for p in expect for v in p], abs=EDGE_TOL)
    assert all(d == pytest.approx(P.FIN1021_HOLE_D, abs=EDGE_TOL) for _, _, d in small)
    # axis 21.0 above the bottom edge, 20.0 from the left edge, 22.0 from the right edge
    assert az - P.FIN1021_Z_MIN == pytest.approx(21.0, abs=EDGE_TOL)
    assert ax - P.FIN1021_X_MIN == pytest.approx(20.0, abs=EDGE_TOL) and P.FIN1021_X_MAX - ax == pytest.approx(22.0, abs=EDGE_TOL)


@pytest.mark.parametrize("key", KEYS)
def test_fin_face_is_the_reference_face(fins, key):
    """The y = 0 face of the fin coincides with the Heat_horn's: same area, zero symmetric difference."""
    fin = fins[key]
    face = [f for f in fin.Faces() if f.geomType() == "PLANE" and f.normalAt().y > 0.999][0]
    ref = H.reference_face()
    assert len(face.innerWires()) == 5
    assert face.Area() == pytest.approx(ref.Area(), rel=1e-9)
    assert face.BoundingBox().ymax == pytest.approx(ref.BoundingBox().ymax, abs=1e-9)
    assert face.intersect(ref).Area() == pytest.approx(ref.Area(), rel=1e-6)
    assert sum(f.Area() for f in face.cut(ref).Faces()) < 1e-6 and sum(f.Area() for f in ref.cut(face).Faces()) < 1e-6


@pytest.mark.parametrize("key", KEYS)
def test_fin_holes_equal_reference_holes(fins, key):
    """Cylinder faces of the fin: the Ø22.5 axis and 4 x Ø3.4 axes equal the Heat_horn's, through the whole thickness."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    t = H.VARIANTS[key]
    axes = {}
    for f in fins[key].Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder:
            cy = a.Cylinder()
            loc = cy.Axis().Location()
            bb = f.BoundingBox()
            e = axes.setdefault((round(loc.X(), 4), round(loc.Z(), 4)), [cy.Radius(), 1e9, -1e9])
            e[1], e[2] = min(e[1], bb.ymin), max(e[2], bb.ymax)
    assert len(axes) == 5
    for (x, z), (r, y0, y1) in axes.items():
        assert y1 - y0 == pytest.approx(t, abs=1e-6)                                    # a through hole
    ref = {}
    for f in H.reference_horn().Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder:
            loc = a.Cylinder().Axis().Location()
            ref[(round(loc.X(), 4), round(loc.Z(), 4))] = a.Cylinder().Radius()
    assert {k: v[0] for k, v in axes.items()} == pytest.approx(ref)


@pytest.mark.parametrize("key", KEYS)
def test_fin_shares_the_reference_volume_on_the_common_thickness(fins, key):
    """Heat_horn (2.0 thick, y -2 .. 0) and the fin overlap exactly over min(t, 2.0) x area: the outlines are identical, nothing sticks out."""
    t = H.VARIANTS[key]
    common = fins[key].intersect(H.reference_horn()).Volume()
    assert common == pytest.approx(min(t, P.FIN1021_REF_T) * HORN_AREA, rel=1e-6)


# ---------------------------------------------------------------------------------------------------------------------
# thickness, volume, mass
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_thickness_and_position(fins, key):
    fin = fins[key]
    t = H.VARIANTS[key]
    x0, x1, y0, y1, z0, z1 = _bb(fin)
    assert fin.isValid() and len(fin.Solids()) == 1
    assert y1 - y0 == pytest.approx(t, abs=1e-9)
    assert y1 == pytest.approx(P.ENC1021_REF_RESIDUAL[1], abs=1e-6)                     # the tab face, y = 0 (+ the file's 0.0016 residual)
    assert (x1 - x0, z1 - z0) == pytest.approx((42.0, 228.6), abs=EDGE_TOL)


@pytest.mark.parametrize("key", KEYS)
def test_volume_equals_area_times_thickness(fins, key):
    t = H.VARIANTS[key]
    assert fins[key].Volume() == pytest.approx(HORN_AREA * t, rel=1e-9)


def test_mass():
    fin = H.make_fin(P.FIN1021_T_PRODUCTION_MM)
    assert H.fin_mass_g(fin) == pytest.approx(HORN_AREA * 3.175 * 2.70e-3, rel=1e-9)
    assert 72.0 < H.fin_mass_g(fin) < 73.5                                              # 72.65 g
    assert H.fin_mass_g(H.make_fin(P.FIN1021_T_PROTOTYPE_MM)) == pytest.approx(11.05, abs=0.02)


# ---------------------------------------------------------------------------------------------------------------------
# frames: flat part frame and assembly coordinates
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_flat_frame_bounding_box(key):
    t = H.VARIANTS[key]
    flat = H.make_fin_flat(t)
    x0, x1, y0, y1, z0, z1 = _bb(flat)
    assert (x0, y0, z0) == pytest.approx((0.0, 0.0, 0.0), abs=2e-6)                    # origin at the bottom-left corner of the 42 mm edge, plate in XY, thickness +Z
    assert (x1, y1, z1) == pytest.approx((42.0, 228.6, t), abs=2e-6)
    assert flat.Volume() == pytest.approx(HORN_AREA * t, rel=1e-9)


def test_flat_frame_mapping_and_holes():
    """(x, y, z) station -> (x + 20, z + 18.36, -y), residual removed; the hole table is the same holes in the flat frame."""
    t = P.FIN1021_T_PRODUCTION_MM
    fin, flat = H.make_fin(t), H.make_fin_flat(t)
    dx, dy, dz = P.ENC1021_REF_RESIDUAL
    c, f = fin.Center(), flat.Center()
    assert (f.x, f.y, f.z) == pytest.approx((c.x - dx - P.FIN1021_X_MIN, c.z - dz - P.FIN1021_Z_MIN, -(c.y - dy)), abs=1e-6)
    rows = H.hole_table()
    assert len(rows) == 5 and rows[0][0] == 1 and rows[0][1] == pytest.approx(22.5, abs=EDGE_TOL)
    assert rows[0][2:] == pytest.approx((20.0, 22.0, 21.0), abs=EDGE_TOL)                # pilot: 20 from the left edge, 22 from the long side, 21 above the bottom
    small = sorted((r[2], r[4]) for r in rows[1:])
    assert [v for p in small for v in p] == pytest.approx([v for p in sorted((x, y) for x in (4.5, 35.5) for y in (5.5, 36.5)) for v in p], abs=EDGE_TOL)
    for r in rows:
        assert r[2] + r[3] == pytest.approx(42.0, abs=1e-9)                              # X from the left + X from the right edge = the width


@pytest.mark.parametrize("key", KEYS)
def test_assembly_copy_is_the_station_copy_plus_O(fins, key):
    asm = H.make_fin_asm(H.VARIANTS[key])
    a, s = _bb(asm), _bb(fins[key])
    assert a == pytest.approx((s[0] + O[0], s[1] + O[0], s[2] + O[1], s[3] + O[1], s[4] + O[2], s[5] + O[2]), abs=1e-9)
    assert asm.Volume() == pytest.approx(fins[key].Volume(), rel=1e-12)


@pytest.mark.skipif(not os.path.isfile(str(SRC)), reason="assembly STEP not available")
@pytest.mark.parametrize("key", KEYS)
def test_assembly_copy_coincides_with_the_heat_horn_of_the_original_assembly(key):
    """In Jasper's Assem_laundry_v3_step_1021 the Heat_horn is the solid of volume 16948.55; its y = 0 face coincides with the fin's."""
    horn = [s for s in cq.importers.importStep(str(SRC)).val().Solids() if abs(s.Volume() - 16948.55) < 0.5]
    assert len(horn) == 1
    horn_face = [f for f in horn[0].Faces() if f.geomType() == "PLANE" and f.normalAt().y > 0.999][0]
    fin = H.make_fin_asm(H.VARIANTS[key])
    fin_face = [f for f in fin.Faces() if f.geomType() == "PLANE" and f.normalAt().y > 0.999][0]
    assert fin_face.BoundingBox().ymax == pytest.approx(horn_face.BoundingBox().ymax, abs=1e-6)
    assert fin_face.Area() == pytest.approx(horn_face.Area(), rel=1e-9)
    assert fin_face.intersect(horn_face).Area() == pytest.approx(horn_face.Area(), rel=1e-6)
    assert (fin_face.Center() - horn_face.Center()).Length < 1e-6


# ---------------------------------------------------------------------------------------------------------------------
# exported files
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_asm1021_step_reimports_with_equal_volume(key):
    path = os.path.join(H.STEP_DIR, f"heat_fin1021_{key}_asm1021.step")
    assert os.path.isfile(path)
    back = cq.importers.importStep(path).val()
    ref = H.make_fin_asm(H.VARIANTS[key])
    assert len(back.Solids()) == 1 and back.isValid()
    assert back.Volume() == pytest.approx(ref.Volume(), rel=1e-6)
    assert _bb(back) == pytest.approx(_bb(ref), abs=1e-4)


def test_flat_step_and_stl():
    t = P.FIN1021_T_PRODUCTION_MM
    step = os.path.join(H.STEP_DIR, "heat_fin1021_1p8.step")
    stl = os.path.join(H.STL_DIR, "heat_fin1021_1p8.stl")
    back = cq.importers.importStep(step).val()
    assert back.Volume() == pytest.approx(HORN_AREA * t, rel=1e-6)
    assert _bb(back) == pytest.approx((0.0, 42.0, 0.0, 228.6, 0.0, t), abs=1e-4)
    tris = _stl_mesh(stl)
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    assert tuple(lo) == pytest.approx((0, 0, 0), abs=1e-3) and tuple(hi) == pytest.approx((42.0, 228.6, t), abs=1e-3)
    assert _mesh_volume(tris) == pytest.approx(HORN_AREA * t, rel=2e-3)                 # tessellated holes: slightly under


def test_dxf_profile():
    import ezdxf
    doc = ezdxf.readfile(os.path.join(H.DXF_DIR, "heat_fin1021_1p8_profile.dxf"))
    assert doc.units == ezdxf.units.MM
    msp = doc.modelspace()
    polys = list(msp.query("LWPOLYLINE"))
    circles = list(msp.query("CIRCLE"))
    assert len(polys) == 1 and polys[0].closed and len(polys[0]) == 4
    pts = [(p[0], p[1]) for p in polys[0].get_points()]
    area = 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])))
    holes_area = sum(math.pi * c.dxf.radius ** 2 for c in circles)
    assert area - holes_area == pytest.approx(HORN_AREA, abs=0.05)                       # outline minus holes = the face area
    assert (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)) == pytest.approx((0, 42.0, 0, 228.6), abs=1e-3)
    assert len(circles) == 5
    got = sorted((round(c.dxf.center.x, 3), round(c.dxf.center.y, 3), round(2 * c.dxf.radius, 3)) for c in circles)
    want = sorted((round(r[2], 3), round(r[4], 3), round(r[1], 3)) for r in H.hole_table())
    assert [v for p in got for v in p] == pytest.approx([v for p in want for v in p], abs=2e-3)


def test_shop_drawing_files():
    png = os.path.join(H.RENDER_DIR, "heat_fin1021_1p8_drawing.png")
    pdf = os.path.join(H.RENDER_DIR, "heat_fin1021_1p8_drawing.pdf")
    assert os.path.getsize(png) > 50_000 and os.path.getsize(pdf) > 10_000
    import matplotlib.image as mpimg
    img = mpimg.imread(png)
    assert img.shape[1] == pytest.approx(SHEET_PX(297.0), abs=3) and img.shape[0] == pytest.approx(SHEET_PX(420.0), abs=3)     # A3 portrait at 150 dpi
    assert open(pdf, "rb").read(5) == b"%PDF-"
    assert H.SHEET_W == 297.0 and H.SHEET_H == 420.0


def SHEET_PX(mm: float, dpi: float = 150.0) -> float:
    return mm / 25.4 * dpi


def test_drawing_function_runs_and_writes_both_files(tmp_path):
    png, pdf = H.shop_drawing(str(tmp_path / "d.png"), str(tmp_path / "d.pdf"))
    assert os.path.getsize(png) > 50_000 and os.path.getsize(pdf) > 10_000


def test_standard_renders_exist():
    for view in ("front", "rear", "left", "right", "top", "bottom", "iso"):
        assert os.path.getsize(os.path.join(H.RENDER_DIR, f"heat_fin1021_1p8_{view}.png")) > 2_000, view
