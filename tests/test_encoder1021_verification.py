"""
Independent geometry verification of the encoder 1021 parts (magnet cap + encoder casing).

Verifier: geometry-verifier (Sonnet), 2026-10-22.  Spec: cad/ENCODER_1021_SPEC.md.  Implementer claims:
verification/encoder1021_build_notes.md.  Report: verification/encoder1021_verification.md.

Everything here is measured with this file's OWN helpers (OCC ray intersections, booleans, BRepExtrema distances, STL triangles); the
implementer's helpers (Probe, overhang_faces, reference_parts, stiffness_estimate ...) are NOT used.  The part module is imported only
for item 7, to compare the exported STEP files with the builder's solids.

What is measured (the part is NOT assumed correct):
  1  part integrity            one valid solid, bbox, volume, mass at PETG 1.27 g/cc
  2  magnet cap                D-peg vs the spool bore measured from Spool1011, ribs, peg length / end, pocket, magnet face
  3  encoder casing            pocket, chip-face plane, board seat + hooks (board modelled as a 23 x 23 x 1.6 box), foot in the
                               divot (divot faces read from the STEP), holes vs the divot holes, screw access
  4  assembly clearances       interference with the 6 station_1021 parts in the plain (0, 0, -2.64) frame and in the implementer's
                               residual-corrected frame, whose legitimacy is tested; distances; cap swept 360 deg; line path
  5  stack-up                  worst-case lateral chip-to-magnet offset vs the AS5600 displacement limit
  6  manufacturability         overhangs, walls, crush ribs vs a 0.4 mm nozzle, snap-hook strain
  7  STEP / STL round trip
  8  renders present

Run:  PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m pytest tests/test_encoder1021_verification.py -q -p no:cacheprovider
Set ENC_VERIFY_JSON=/path/out.json to dump every recorded number (expected, measured, tolerance, status).
"""

from __future__ import annotations

import json
import math
import os
import struct
import sys
import tempfile

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

from OCP.BRepCheck import BRepCheck_Analyzer                      # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape            # noqa: E402
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt                         # noqa: E402
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
STEP_DIR = os.path.join(REPO, "exports", "step")
STL_DIR = os.path.join(REPO, "exports", "stl")
REF_DIR = os.path.join(REPO, "cad", "reference", "station_1021")
RENDER_DIR = os.path.join(REPO, "renders", "encoder1021")
CAP_STEP = os.path.join(STEP_DIR, "encoder1021_magnet_cap.step")
CAS_STEP = os.path.join(STEP_DIR, "encoder1021_casing.step")
CAP_STL = os.path.join(STL_DIR, "encoder1021_magnet_cap.stl")
CAS_STL = os.path.join(STL_DIR, "encoder1021_casing.stl")
REF_NAMES = ("Slipin_mount_piecev3", "Spool1011", "Shell_Casing", "Motor_Reference", "Heat_horn", "Wall_Mount_v3")

PETG_G_CM3 = 1.27          # task statement; cad/materials.py agrees
PETG_E_MPA = 2100.0        # cad/materials.py
PETG_YIELD_MPA = 45.0      # cad/materials.py (XY)
AS5600_DISPLACEMENT_MM = 0.25   # ams AS5600 datasheet: max displacement of the magnet axis from the package centre, 6 mm magnet
                                # (read from search-engine excerpts of datasheet mirrors; official PDF not opened: see the report)
NOZZLE_MM = 0.4

# --- design values taken from the SPEC (authoritative), not from cad/params.py
SPEC = dict(
    spool_face_y=26.0, shaft_end_y=22.0, bore_d=5.30, bore_flat=2.15, divot_rim=24.0, divot_depth=1.0, divot_yz=(45.0, 0.0),
    divot_hole_pitch=9.5, peg_d=5.10, peg_flat=2.05, peg_len=3.4, peg_end_y=22.6, head_d=14.0, head_t=3.3, pocket_d=6.2,
    pocket_depth=2.55, magnet_face_y=29.3, air_gap=1.5, chip_face_y=30.8, pcb=23.0, pcb_t=1.6, chip_h=1.45, pocket=23.4,
    foot=23.6, foot_proud=3.0, foot_key=1.0, hole_d=3.4,
)

RECORDS: list = []


# =====================================================================================================================
# recording
# =====================================================================================================================
def _rec(item, what, expected, measured, tol, status, note=""):
    RECORDS.append(dict(item=item, what=what, expected=expected, measured=measured, tol=tol, status=status, note=note))


def check(item, what, expected, measured, tol, note=""):
    """|measured - expected| <= tol."""
    ok = abs(measured - expected) <= tol
    _rec(item, what, expected, measured, f"+-{tol}", "PASS" if ok else "FAIL", note)
    assert ok, f"[{item}] {what}: expected {expected} +-{tol}, measured {measured}"


def check_min(item, what, minimum, measured, note=""):
    ok = measured >= minimum
    _rec(item, what, f">= {minimum}", measured, "min", "PASS" if ok else "FAIL", note)
    assert ok, f"[{item}] {what}: need >= {minimum}, measured {measured}"


def check_max(item, what, maximum, measured, note=""):
    ok = measured <= maximum
    _rec(item, what, f"<= {maximum}", measured, "max", "PASS" if ok else "FAIL", note)
    assert ok, f"[{item}] {what}: need <= {maximum}, measured {measured}"


def check_true(item, what, cond, measured="", note=""):
    _rec(item, what, "True", measured if measured != "" else cond, "-", "PASS" if cond else "FAIL", note)
    assert cond, f"[{item}] {what}: {measured}"


def info(item, what, measured, note=""):
    _rec(item, what, "-", measured, "-", "INFO", note)


@pytest.fixture(scope="session", autouse=True)
def _dump_records():
    yield
    out = os.environ.get("ENC_VERIFY_JSON")
    if out:
        with open(out, "w") as fh:
            json.dump(RECORDS, fh, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    for r in RECORDS:
        m = r["measured"]
        ms = f"{m:.5g}" if isinstance(m, (float, np.floating)) else str(m)
        print(f"[{r['item']}] {r['status']:5s} {r['what']} | expected {r['expected']} | measured {ms} | tol {r['tol']} {r['note']}")


# =====================================================================================================================
# own geometry helpers
# =====================================================================================================================
def load_step(path):
    return cq.importers.importStep(path).val()


def n_solids(shape):
    return len(shape.Solids())


def brep_valid(shape):
    return bool(shape.isValid()) and bool(BRepCheck_Analyzer(shape.wrapped).IsValid())


def bbox(shape):
    b = shape.BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def cyl(r, h, base, axis):
    return cq.Solid.makeCylinder(r, h, cq.Vector(*base), cq.Vector(*axis))


def vol_common(a, b):
    r = a.intersect(b)
    return r.Volume() if r is not None else 0.0


def common(a, b):
    return a.intersect(b)


def min_dist(a, b):
    e = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    e.Perform()
    return e.Value()


_ISECT = {}


def ray(shape, origin, direction, tmin=0.0, tmax=1e3):
    """Sorted distances t > tmin along the unit `direction` where the ray origin + t d crosses a face of `shape`."""
    key = id(shape)
    if key not in _ISECT:
        it = IntCurvesFace_ShapeIntersector()
        it.Load(shape.wrapped, 1e-7)
        _ISECT[key] = (it, shape)
    it = _ISECT[key][0]
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    it.Perform(gp_Lin(gp_Pnt(*[float(v) for v in origin]), gp_Dir(*[float(v) for v in d])), -1e4, tmax)
    ts = sorted(it.WParameter(i) for i in range(1, it.NbPnt() + 1))
    return [t for t in ts if t > tmin]


def plane_faces(shape, normal):
    """(coordinate of the plane along the normal's axis, area, bbox) for planar faces whose OUTWARD normal is `normal`
    (a unit axis vector, e.g. (0, -1, 0) = faces looking toward -y; the returned coordinate is y, not -y)."""
    n = np.array(normal, float)
    n /= np.linalg.norm(n)
    axis = int(np.argmax(np.abs(n)))
    out = []
    for f in shape.Faces():
        if f.geomType() != "PLANE":
            continue
        fn = f.normalAt()
        if np.dot([fn.x, fn.y, fn.z], n) > 0.9999:
            c = f.Center()
            out.append((float((c.x, c.y, c.z)[axis]), f.Area(), f.BoundingBox()))
    return out


def cyl_faces(shape, axis):
    """Cylindrical faces whose axis is parallel to `axis` (index 0/1/2): list of (radius, (x, y, z) of a point on the axis, area)."""
    out = []
    for f in shape.Faces():
        if f.geomType() != "CYLINDER":
            continue
        c = f._geomAdaptor().Cylinder()
        d = c.Axis().Direction()
        if abs(abs((d.X(), d.Y(), d.Z())[axis]) - 1.0) > 1e-6:
            continue
        loc = c.Location()
        out.append((c.Radius(), (loc.X(), loc.Y(), loc.Z()), f.Area()))
    return out


def sphere_faces(shape):
    out = []
    for f in shape.Faces():
        if f.geomType() == "SPHERE":
            s = f._geomAdaptor().Sphere()
            loc = s.Location()
            out.append((s.Radius(), (loc.X(), loc.Y(), loc.Z()), f.Area()))
    return out


def read_stl(path):
    """Binary STL -> (n, 3, 3) float array of triangles."""
    raw = open(path, "rb").read()
    n = struct.unpack("<I", raw[80:84])[0]
    assert len(raw) == 84 + 50 * n, f"{path} is not a binary STL"
    rec = np.frombuffer(raw[84:], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n)
    return rec["v"].reshape(-1, 3, 3).astype(float)


def stl_volume(tri):
    return float(np.sum(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2]))) / 6.0)


def stl_watertight(tri):
    pts = np.round(tri.reshape(-1, 3), 4)
    _, inv = np.unique(pts, axis=0, return_inverse=True)
    f = inv.reshape(-1, 3)
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, c = np.unique(e, axis=0, return_counts=True)
    return int((c != 2).sum())


def radial_profile(shape, y, cx, cz, n=720, tmax=30.0):
    """Distance from the axis point (cx, y, cz) to the FIRST surface crossing, per angle (0 = +x, 90 = +z), plus the angles (deg)."""
    ang = np.arange(n) * 360.0 / n
    r = []
    for a in np.radians(ang):
        ts = ray(shape, (cx, y, cz), (math.cos(a), 0.0, math.sin(a)), 1e-6, tmax)
        r.append(ts[0] if ts else float("nan"))
    return ang, np.array(r)


# =====================================================================================================================
# fixtures
# =====================================================================================================================
@pytest.fixture(scope="module")
def cap():
    return load_step(CAP_STEP)


@pytest.fixture(scope="module")
def cas():
    return load_step(CAS_STEP)


@pytest.fixture(scope="module")
def ref_raw():
    """station_1021 parts exactly as stored (before any shift)."""
    return {n: load_step(os.path.join(REF_DIR, f"{n}.step")) for n in REF_NAMES}


@pytest.fixture(scope="module")
def ref_plain(ref_raw):
    """Plain frame of the spec: subtract (0, 0, 2.64) and nothing else."""
    return {n: s.translate(cq.Vector(0, 0, -2.64)) for n, s in ref_raw.items()}


@pytest.fixture(scope="module")
def offs(ref_plain):
    """Common extraction residual, measured here from the spool (bore axis x, z; outer-face y), not copied from params.py."""
    sp = ref_plain["Spool1011"]
    bore = [c for c in cyl_faces(sp, 1) if abs(c[0] - 2.65) < 0.01][0]
    face = [p for p in plane_faces(sp, (0, 1, 0)) if p[1] > 900][0]            # the plain outer flange face (area ~996.9)
    return dict(x=bore[1][0], y=face[0] - SPEC["spool_face_y"], z=bore[1][2])


@pytest.fixture(scope="module")
def ref_corr(ref_raw, offs):
    return {n: s.translate(cq.Vector(-offs["x"], -offs["y"], -(2.64 + offs["z"]))) for n, s in ref_raw.items()}


# =====================================================================================================================
# 1  part integrity
# =====================================================================================================================
def test_1_cap_integrity(cap):
    check("1", "cap: solid count", 1, n_solids(cap), 0)
    check_true("1", "cap: BRep valid (cq isValid + BRepCheck_Analyzer)", brep_valid(cap))
    b = bbox(cap)
    for nm, e, m in (("x min", -7.0, b[0]), ("x max", 7.0, b[1]), ("y min (peg end)", 22.6, b[2]), ("y max (magnet face)", 29.3, b[3]),
                     ("z min", -7.0, b[4]), ("z max", 7.0, b[5])):
        check("1", f"cap bbox {nm}", e, m, 0.01)
    v = cap.Volume()
    # independent estimate: head cylinder - chamfer ring - pocket - notch + D-peg beyond the head + ribs
    r_pk, r0, d = 3.1, 2.55, 2.05
    seg = r0 ** 2 * math.acos(d / r0) - d * math.sqrt(r0 ** 2 - d ** 2)
    est = (math.pi * 49 * 3.3 - 0.5 * 0.3 ** 2 * 2 * math.pi * 6.85 - math.pi * r_pk ** 2 * 2.55 - 3.0 * 2.0 * 0.8
           + (math.pi * r0 ** 2 - seg) * 3.4 + 3 * 0.6 * 0.15 * 2.9)
    check("1", "cap volume vs independent analytic estimate (mm3)", est, v, 0.03 * est, note=f"measured {v:.2f}, estimate {est:.2f}")
    info("1", "cap mass at PETG 1.27 g/cc (g)", v * PETG_G_CM3 / 1000.0)
    check_true("1", "cap volume > 0", v > 0)


def test_1_casing_integrity(cas):
    check("1", "casing: solid count", 1, n_solids(cas), 0)
    check_true("1", "casing: BRep valid (cq isValid + BRepCheck_Analyzer)", brep_valid(cas))
    b = bbox(cas)
    # expected from the spec: foot floor x = -22.1 (measured divot floor: -22.15, 0.05 rounding), frame +x edge = 27.4/2,
    # frame front face y = 31.0, foot far edge y = 45 + 23.6/2, frame z = +-13.7
    for nm, e, m, t in (("x min", -22.15, b[0], 0.06), ("x max", 13.7, b[1], 0.01), ("y min", 31.0, b[2], 0.01),
                        ("y max", 56.8, b[3], 0.01), ("z min", -13.7, b[4], 0.01), ("z max", 13.7, b[5], 0.01)):
        check("1", f"casing bbox {nm}", e, m, t)
    v = cas.Volume()
    check_true("1", "casing volume > 0 and inside a crude bound (box 35.85 x 25.8 x 27.4 = 25 345 mm3)", 0 < v < 25345.0, f"{v:.1f}")
    info("1", "casing mass at PETG 1.27 g/cc (g)", v * PETG_G_CM3 / 1000.0)


# =====================================================================================================================
# frame / reference sanity (feeds items 2 to 4)
# =====================================================================================================================
def test_ref_frame_residual_is_common_and_legitimate(ref_plain, offs):
    """The implementer's correction (0.004243, 0.001645, 0.003854) must be one rigid offset common to every reference part,
    below the 0.01 mm rounding of the extraction origin, and must turn the interface numbers into round design values."""
    for k in "xyz":
        check_max("4", f"residual |{k}| (mm), rounding of extract.py origin O is 0.01", 0.005, abs(offs[k]))
    check("4", "residual x vs implementer's 0.004243", 0.004243, offs["x"], 2e-5)
    check("4", "residual y vs implementer's 0.001645", 0.001645, offs["y"], 2e-5)
    check("4", "residual z vs implementer's 0.003854", 0.003854, offs["z"], 2e-5)
    ox, oy, oz = offs["x"], offs["y"], offs["z"]
    # motor shaft (Ø5, D-flat) and its end
    mo = ref_plain["Motor_Reference"]
    shaft = [c for c in cyl_faces(mo, 1) if abs(c[0] - 2.5) < 0.01][0]
    check("4", "shaft axis x after removing the residual (spool bore and shaft share it)", 0.0, shaft[1][0] - ox, 1e-4)
    check("4", "shaft axis z after removing the residual", 0.0, shaft[1][2] - oz, 1e-4)
    end = max(p[0] for p in plane_faces(mo, (0, 1, 0)) if abs((p[2].xmin + p[2].xmax) / 2) < 3 and p[0] > 20)
    check("4", "shaft end y after removing the residual (spec 22.0)", 22.0, end - oy, 1e-4)
    # slip-in divot
    sl = ref_plain["Slipin_mount_piecev3"]
    floor = [p for p in plane_faces(sl, (1, 0, 0)) if 400 < p[1] < 500 and -23 < p[0] < -22][0]
    check("4", "divot floor x after removing the residual (spec -22.1: rounded; measured design -22.15)", -22.15, floor[0] - ox, 1e-4)
    fb = floor[2]
    check("4", "divot centre y", 45.0, (fb.ymin + fb.ymax) / 2 - oy, 1e-4)
    check("4", "divot centre z", 0.0, (fb.zmin + fb.zmax) / 2 - oz, 1e-4)
    holes = sorted((round(c[1][1] - oy, 4), round(c[1][2] - oz, 4)) for c in cyl_faces(sl, 0) if abs(c[0] - 1.725) < 0.01)
    holes = sorted(set(holes))
    check("4", "divot hole axes found (4 distinct y/z)", 4, len(holes), 0)
    for (y, z), (ey, ez) in zip(holes, sorted([(40.25, -4.75), (40.25, 4.75), (49.75, -4.75), (49.75, 4.75)])):
        check("4", f"divot hole axis y at {ey}", ey, y, 1e-3)
        check("4", f"divot hole axis z at {ez}", ez, z, 1e-3)
    # other parts' bounding boxes land on round numbers with the same offset
    b = bbox(ref_plain["Motor_Reference"])
    check("4", "Motor_Reference x min after residual (round -21.15)", -21.15, b[0] - ox, 1e-3)
    check("4", "Motor_Reference x max after residual (round 21.15)", 21.15, b[1] - ox, 1e-3)
    check("4", "Motor_Reference y min after residual (round -40.0)", -40.0, b[2] - oy, 1e-3)
    b = bbox(ref_plain["Heat_horn"])
    check("4", "Heat_horn y max after residual (round 0.0)", 0.0, b[3] - oy, 1e-3)
    check("4", "Heat_horn y min after residual (round -2.0)", -2.0, b[2] - oy, 1e-3)
    b = bbox(ref_plain["Shell_Casing"])
    check("4", "Shell_Casing x min after residual (round -21.15)", -21.15, b[0] - ox, 1e-3)


def test_ref_divot_is_a_dish_with_one_sharp_corner(ref_plain, offs):
    """Spec says 'R1.0 concave corners, 1.0 deep'.  Read the faces: quarter-round R1.0 wall, floor 22 x 22, 3 spherical corners."""
    sl = ref_plain["Slipin_mount_piecev3"]
    ox, oy, oz = offs["x"], offs["y"], offs["z"]
    floor = [p for p in plane_faces(sl, (1, 0, 0)) if 400 < p[1] < 500 and -23 < p[0] < -22][0]
    fb = floor[2]
    check("3", "divot floor size y (22 = 24 - 2 x R1.0)", 22.0, fb.ymax - fb.ymin, 1e-3)
    check("3", "divot floor size z", 22.0, fb.zmax - fb.zmin, 1e-3)
    plate = max((p for p in plane_faces(sl, (1, 0, 0)) if abs(p[0] - ox + 21.15) < 0.01), key=lambda p: p[1])
    plate_x = plate[0] - ox
    check("3", "plate face x (the face the divot is cut into; spec -21.1 rounded)", -21.15, plate_x, 2e-3)
    walls = [c for ax in (1, 2) for c in cyl_faces(sl, ax) if abs(c[0] - 1.0) < 1e-3 and abs(c[1][0] - ox - plate_x) < 2e-3
             and ((ax == 1 and abs(abs(c[1][2] - oz) - 11.0) < 2e-3) or (ax == 2 and min(abs(c[1][1] - oy - 34.0), abs(c[1][1] - oy - 56.0)) < 2e-3))]
    check("3", "divot wall cylinders R1.0 (2 per axis)", 4, len(walls), 0)
    for r, loc, _ in walls:
        check("3", "wall arc centre x equals the plate face level (arc tangent to the floor, quarter-round, no vertical part)",
              plate_x, loc[0] - ox, 2e-3)
    check("3", "divot depth = plate face - floor", 1.0, plate_x - (floor[0] - ox), 2e-3)
    sph = [s_ for s_ in sphere_faces(sl) if abs(s_[0] - 1.0) < 1e-3 and abs(s_[1][0] - ox - plate_x) < 2e-3]
    check("3", "spherical R1.0 corner patches", 3, len(sph), 0)
    centres = sorted((round(s_[1][1] - oy, 2), round(s_[1][2] - oz, 2)) for s_ in sph)
    info("3", "sphere-patch centres (y, z): the corner without one is a sharp mitre", centres)
    check_true("3", "missing sphere at the (+y, +z) corner (56.0, +11.0) -> sharp corner there",
               (56.0, 11.0) not in centres and (34.0, 11.0) in centres and (34.0, -11.0) in centres and (56.0, -11.0) in centres, centres)


# =====================================================================================================================
# 2  magnet cap
# =====================================================================================================================
def test_2_cap_peg_vs_spool_bore(cap, ref_corr, ref_plain, offs):
    sp = ref_corr["Spool1011"]
    # --- measure the bore from Spool1011 (corrected frame: axis at 0, 0)
    bore_face = [c for c in cyl_faces(sp, 1) if abs(c[0] - 2.65) < 0.01][0]
    check("2", "spool bore diameter (spec 5.30)", 5.30, 2 * bore_face[0], 0.002)
    flats = [p for p in plane_faces(sp, (-1, 0, 0)) if abs(p[0]) < 3]
    check("2", "spool bore D-flat plane count", 1, len(flats), 0)
    check("2", "spool bore D-flat x (spec +2.15, material on +x)", 2.15, flats[0][0], 0.002)
    fb = flats[0][2]
    check("2", "bore flat runs through the spool (y 7.0 .. 26.0)", 19.0, fb.ymax - fb.ymin, 0.01)
    # --- radial profiles at three y inside the peg (lead-in ends at 23.1)
    ang, rb = radial_profile(sp, 24.3, 0.0, 0.0)
    check("2", "bore round radius from the spool, probed 720 angles (spec Ø5.30)", 2.65, float(np.nanmax(rb)), 0.002)
    check("2", "bore flat distance from the spool, probed (spec 2.15)", 2.15, float(np.nanmin(rb)), 0.002)
    rib_hits = {}
    for y in (23.4, 24.3, 25.5):
        ang, rc = radial_profile(cap, y, 0.0, 0.0)
        flat = float(np.max(rc * np.cos(np.radians(ang))))
        check("2", f"peg flat position at y={y} (spec +2.05, bore flat 2.15)", 2.05, flat, 0.003)
        # round part radius: median of the non-rib, non-flat angles
        mask = (np.cos(np.radians(ang)) < 0.5)
        r_round = float(np.median(rc[mask]))
        check("2", f"peg round radius at y={y} (spec Ø5.10)", 2.55, r_round, 0.003)
        clear = rb - rc
        rib = clear < 0.0
        rib_hits[y] = (ang[rib], clear[rib])
        # clearance outside the rib sectors
        rib_ang = ang[rib]
        far = np.array([np.min(np.abs(((a - rib_ang + 180) % 360) - 180)) if len(rib_ang) else 999 for a in ang]) > 12.0
        check("2", f"peg clearance to the bore away from the ribs at y={y} (min over angles)", 0.10, float(clear[far].min()), 0.01,
              note="round part 2.65-2.55 and flat 2.15-2.05")
    ang_hit, clr = rib_hits[24.3]
    sectors = []
    for a in ang_hit:
        if not sectors or a - sectors[-1][-1] > 3:
            sectors.append([a])
        else:
            sectors[-1].append(a)
    centres = [float(np.mean(s)) for s in sectors]
    check("2", "number of crush-rib sectors (angles where the peg exceeds the bore)", 3, len(sectors), 0)
    check("2", "ribs equally spaced: spread of sector spacings (deg)", 0.0,
          float(np.ptp(np.diff(sorted(centres + [centres[0] + 360])))), 2.0, note=f"centres {np.round(centres, 1)}")
    check("2", "rib interference with the bore (radial, mm)", 0.054, float(-clr.min()), 0.01, note="tip r 2.70 vs bore 2.65")
    # --- volume of the cap inside the spool: ribs only
    v_corr = vol_common(cap, sp)
    check("2", "cap/spool interference volume, corrected frame (mm3): ribs only (analytic ~0.15-0.17)", 0.16, v_corr, 0.03)
    # same, with every rib sector removed: wedge cut-out of 24 deg around each rib (y 22 .. 26, the part of the peg inside the bore)
    keep = cap
    for c in centres:
        pts = [cq.Vector(0, 22.0, 0)] + [cq.Vector(6 * math.cos(math.radians(c + d)), 22.0, 6 * math.sin(math.radians(c + d))) for d in (-12, 12)]
        face = cq.Face.makeFromWires(cq.Wire.makePolygon(pts, close=True))
        wedge = cq.Solid.extrudeLinear(face, cq.Vector(0, 4.0, 0))
        if wedge.Volume() < 0:
            wedge = cq.Solid.extrudeLinear(cq.Face.makeFromWires(cq.Wire.makePolygon(pts[::-1], close=True)), cq.Vector(0, 4.0, 0))
        assert wedge.Volume() > 1.0, "wedge construction failed"
        keep = keep.cut(wedge)
    v_wo = vol_common(keep, sp)
    check("2", "cap/spool interference volume with the 3 rib sectors cut away (mm3)", 0.0, v_wo, 0.002,
          note="the head face contact leaves < 0.002 in the corrected frame")
    v_plain = vol_common(cap, ref_plain["Spool1011"])
    info("2", "cap/spool interference volume, plain frame (mm3)", v_plain,
         note="ribs + head embedded 0.0016 mm into the flange face (0.0016 x 134 mm2 = 0.21)")
    slab = cap.intersect(box(-10, 10, 26.0, 26.01, -10, 10))
    head_embed = vol_common(slab, ref_plain["Spool1011"]) if slab is not None else 0.0
    check("2", "plain-frame overlap at the head/flange contact is only the 0.0016 mm extraction offset (mm3 <= 0.0016 x 154)", 0.21,
          head_embed, 0.03)
    # --- head underside sits on the spool face
    sp_face = [p for p in plane_faces(sp, (0, 1, 0)) if p[1] > 900][0][0]
    under = [p for p in plane_faces(cap, (0, -1, 0)) if p[1] > 100][0][0]
    check("2", "head underside y (spool outer face y, corrected)", sp_face, under, 0.002)


def test_2_cap_peg_length_and_shaft_clearance(cap, ref_corr, ref_plain):
    b = bbox(cap)
    under = [p for p in plane_faces(cap, (0, -1, 0)) if p[1] > 100][0][0]
    check("2", "peg length = head underside - peg end (spec 3.4)", 3.4, under - b[2], 0.005)
    check("2", "peg end y (spec 22.6)", 22.6, b[2], 0.005)
    mo = ref_corr["Motor_Reference"]
    shaft_end = max(p[0] for p in plane_faces(mo, (0, 1, 0)) if abs((p[2].xmin + p[2].xmax) / 2) < 3 and p[0] > 20)
    check("2", "shaft end y measured from Motor_Reference (spec 22.0), corrected frame", 22.0, shaft_end, 0.002)
    check("2", "peg end to shaft end distance, BRepExtrema, corrected frame (spec 0.6)", 0.6, min_dist(cap, mo), 0.005)
    check("2", "peg end to shaft end distance, BRepExtrema, plain frame (0.6 - 0.0016)", 0.5984, min_dist(cap, ref_plain["Motor_Reference"]), 0.005)
    check("2", "cap vs motor: interference volume (mm3)", 0.0, vol_common(cap, mo), 1e-6)


def test_2_cap_rotational_lash_without_ribs(cap, ref_corr):
    """The D-key has 0.10 mm of clearance on the flat: how far can the cap turn in the bore if the crush ribs do not grip?"""
    sp = ref_corr["Spool1011"]
    ang, rc = radial_profile(cap, 24.3, 0.0, 0.0)
    r0 = float(np.median(rc[(np.cos(np.radians(ang)) < 0.5) & (rc < 2.6)]))
    flat = float(np.max(rc * np.cos(np.radians(ang))))
    peg = cyl(r0, 3.4, (0, 22.6, 0), (0, 1, 0)).intersect(box(-3, flat, 21, 27, -3, 3))      # clean D-peg (no ribs) from the measured profile
    check_true("2", "clean D-peg has no interference with the bore at 0 deg", vol_common(peg, sp) < 1e-9)
    lo, hi = 0.0, 20.0
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        free = all(vol_common(peg.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), sg * mid), sp) < 1e-6 for sg in (1, -1))
        lo, hi = (mid, hi) if free else (lo, mid)
    cx = math.sqrt(r0 ** 2 - flat ** 2)
    # corner (flat, cx) rotated until x' = 2.15:  flat cos(a) + cx sin(a) = 2.15
    a = 0.0
    for _ in range(60):
        a += (2.15 - (flat * math.cos(a) + cx * math.sin(a))) / (-flat * math.sin(a) + cx * math.cos(a))
    analytic = math.degrees(a)
    check("2", "angular lash of the cap in the bore if the ribs do not grip, +- deg (BRep) vs analytic corner-on-flat", analytic, lo, 0.1,
          note="the 0.10 mm flat clearance is the only key: +-4 deg = about +-0.5 mm of line at the 7.5 mm core radius per direction reversal")
    info("2", "line-length hysteresis at the Ø15 core from that lash (mm, total)", 2 * math.radians(lo) * 7.5)


def test_ref_spool_vs_shaft_interference_is_a_reference_model_matter(ref_corr):
    """Observation only: spool bore flat (x = +2.15) and shaft flat (z = +2.0) are 90 deg apart in the reference assembly."""
    v = vol_common(ref_corr["Spool1011"], ref_corr["Motor_Reference"])
    info("2", "reference spool vs Motor_Reference shaft interference (mm3): bore flat and shaft flat are 90 deg apart in the 10/21 assembly", v,
         note="not caused by the new parts; the spool must be turned 90 deg or driven by something other than the D-flat; the cap keys on the bore only")


def test_2_cap_magnet_pocket_and_face(cap, ref_plain, ref_corr, offs):
    pockets = [c for c in cyl_faces(cap, 1) if abs(c[0] - 3.1) < 0.01]
    check("2", "magnet pocket cylinder faces (Ø6.2)", 1, len(pockets), 0)
    r, loc, _ = pockets[0]
    check("2", "pocket diameter (spec Ø6.2 = Ø6 + 0.2)", 6.2, 2 * r, 0.002)
    check("2", "pocket axis x (design frame, the shaft axis)", 0.0, loc[0], 1e-4)
    check("2", "pocket axis z", 0.0, loc[2], 1e-4)
    shaft_p = [c for c in cyl_faces(ref_plain["Motor_Reference"], 1) if abs(c[0] - 2.5) < 0.01][0]
    ecc = math.hypot(shaft_p[1][0] - loc[0], shaft_p[1][2] - loc[2])
    info("2", "pocket axis to motor shaft axis, plain frame (mm)", ecc, note="= the 0.0057 mm residual, not a design offset")
    shaft_c = [c for c in cyl_faces(ref_corr["Motor_Reference"], 1) if abs(c[0] - 2.5) < 0.01][0]
    check("2", "pocket axis to motor shaft axis, corrected frame (mm)", 0.0, math.hypot(shaft_c[1][0] - loc[0], shaft_c[1][2] - loc[2]), 1e-4)
    # pocket depth from the top plane and the pocket floor
    tops = sorted(p[0] for p in plane_faces(cap, (0, 1, 0)))
    check("2", "magnet-face plane (head top annulus) y (spec 29.3)", 29.3, tops[-1], 0.002)
    floor = [p for p in plane_faces(cap, (0, 1, 0)) if abs(p[1] - math.pi * 3.1 ** 2) < 0.3][0]
    check("2", "pocket floor area = Ø6.2 disc", math.pi * 3.1 ** 2, floor[1], 0.3)
    check("2", "pocket depth (spec 2.55 = 2.5 + 0.05 glue film)", 2.55, tops[-1] - floor[0], 0.003)
    check("2", "head diameter (spec Ø14)", 14.0, 2 * max(c[0] for c in cyl_faces(cap, 1)), 0.003)
    # a Ø6 x 2.5 magnet with a 0.05 glue film is flush at 29.3; bottomed it is at 29.25 (inside +-0.05)
    magnet_glued = floor[0] + 0.05 + 2.5
    magnet_bottomed = floor[0] + 2.5
    check("2", "magnet face y, glued with a 0.05 film (spec 29.3)", 29.3, magnet_glued, 0.002)
    check("2", "magnet face y, bottomed without glue (spec 29.3 +- 0.05)", 29.3, magnet_bottomed, 0.0501)
    mag = cyl(3.0, 2.5, (0, floor[0] + 0.05, 0), (0, 1, 0))
    check("2", "magnet in the pocket: no interference with the cap (mm3)", 0.0, vol_common(cap, mag), 1e-6)
    info("2", "magnet radial play in the pocket (mm)", 3.1 - 3.0)


# =====================================================================================================================
# 3  encoder casing
# =====================================================================================================================
def test_3_pocket_and_chip_plane(cas, cap):
    for y in (31.6, 32.0, 33.0, 33.5):
        d = {nm: ray(cas, (0, y, 0), v, 0, 40)[0] for nm, v in (("+x", (1, 0, 0)), ("-x", (-1, 0, 0)), ("+z", (0, 0, 1)), ("-z", (0, 0, -1)))}
        check("3", f"board pocket width in x at y={y} (spec 23.4)", 23.4, d["+x"] + d["-x"], 0.005)
        check("3", f"board pocket width in z at y={y} (spec 23.4)", 23.4, d["+z"] + d["-z"], 0.005)
        check("3", f"pocket centre offset x at y={y}", 0.0, (d["+x"] - d["-x"]) / 2, 0.01)
        check("3", f"pocket centre offset z at y={y}", 0.0, (d["+z"] - d["-z"]) / 2, 0.01)
    stops = [p for p in plane_faces(cas, (0, 1, 0)) if abs(p[0] - 32.25) < 0.01 and abs(p[1] - 9.0) < 0.05]
    check("3", "front stops: four tab faces on the PCB front plane", 4, len(stops), 0)
    check("3", "PCB front plane y = tab back face (chip face 30.8 + 1.45)", 32.25, stops[0][0], 0.005)
    chip_face = stops[0][0] - SPEC["chip_h"]
    check("3", "chip-face plane y = PCB front - chip height (spec 30.8)", 30.8, chip_face, 0.01)
    magnet_face = max(p[0] for p in plane_faces(cap, (0, 1, 0)))
    check("3", "air gap magnet face to chip face (spec 1.5)", 1.5, chip_face - magnet_face, 0.01)
    front = max((p for p in plane_faces(cas, (0, -1, 0))), key=lambda p: p[1])
    check("3", "frame front face y (spec >= 31.0)", 31.0, front[0], 0.002)
    check("3", "chip protrudes beyond the frame front (mm)", 0.2, front[0] - chip_face, 0.01)
    # the four tabs are 3 x 3 and at the board corners
    xs = sorted((round((p[2].xmin + p[2].xmax) / 2, 2), round((p[2].zmin + p[2].zmax) / 2, 2)) for p in stops)
    check_true("3", "tab centres at (+-10.2, +-10.2): the pocket corners", xs == [(-10.2, -10.2), (-10.2, 10.2), (10.2, -10.2), (10.2, 10.2)], xs)
    check("3", "tab size x", 3.0, stops[0][2].xmax - stops[0][2].xmin, 0.01)


def _board(dx=0.0, dy=0.0, dz=0.0):
    """23 x 23 x 1.6 PCB as a box, seated: front face on the tab plane y = 32.25, centred on the axis; (dx, dy, dz) = offset."""
    return box(-11.5 + dx, 11.5 + dx, 32.25 + dy, 33.85 + dy, -11.5 + dz, 11.5 + dz)


def test_3_board_seat_and_capture(cas):
    check("3", "23 x 23 x 1.6 board seated on the stops: interference (mm3)", 0.0, vol_common(cas, _board()), 1e-6)
    # lateral play: all 8 extreme positions fit, +0.01 more does not
    worst = []
    for dx, dz in ((0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2), (0.2, 0.2), (-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2)):
        v = vol_common(cas, _board(dx, 0, dz))
        worst.append(v)
    check("3", "board at the 8 extreme lateral positions (+-0.2): max interference (mm3)", 0.0, max(worst), 1e-6)
    check_true("3", "board 0.01 mm beyond the pocket walls interferes (the pocket really is 23.4)", all(
        vol_common(cas, _board(dx, 0, dz)) > 0.05 for dx, dz in ((0.21, 0), (-0.21, 0), (0, 0.21), (0, -0.21))))
    # stops: the board cannot move toward -y
    check_true("3", "front stops: board moved 0.01 toward -y collides with the tabs", vol_common(cas, _board(0, -0.01, 0)) > 0.1)
    # hooks: free to move 0.1 toward +y (hook gap), then captured
    check("3", "hooks: board raised 0.09 mm toward +y is still free (mm3)", 0.0, vol_common(cas, _board(0, 0.09, 0)), 1e-6)
    check_true("3", "hooks: board raised 0.11 mm toward +y hits the catch faces", vol_common(cas, _board(0, 0.11, 0)) > 0.01)
    # lip overlap over the board footprint, for the centred board and the two extreme z positions
    for dz in (0.0, 0.2, -0.2):
        slab = box(-11.5, 11.5, 33.96, 34.0, -11.5 + dz, 11.5 + dz)
        area = vol_common(cas, slab) / 0.04
        check("3", f"hook lip overlap with the board back face, total area, board dz={dz} (2 lips x 8.0 x overlap)", 6.4, area, 0.3,
              note="sum of both lips is constant; one lip overlaps 0.6 and the other 0.2 mm at dz=+-0.2")
    for side in (1, -1):
        z0, z1 = sorted((side * 11.1, side * 11.5))
        ov = vol_common(cas, box(-11.5, 11.5, 33.96, 34.0, z0, z1)) / 0.04
        check("3", f"lip on z side {side:+d}: overlap area over the centred board edge strip (8.0 x 0.4)", 3.2, ov, 0.2)
    # insertion: penetration of the centred board into the lip while it passes (the wall has to flex by this much)
    pen = common(cas, box(-11.5, 11.5, 33.96, 35.2, -11.5, 11.5))
    zb = pen.BoundingBox()
    check("3", "board passes the lips: required wall deflection for a centred board (mm)", 0.4, zb.zmax - 11.1, 0.01)
    pen2 = common(cas, box(-11.5, 11.5, 33.96, 35.2, -11.5 + 0.2, 11.5 + 0.2)).BoundingBox()
    check("3", "board passes the lips: required deflection if inserted against one wall (mm)", 0.6, pen2.zmax - 11.1, 0.01,
          note="1.5x the centred value; the strain check in item 6 uses both")
    # chip body (6 x 4 SOIC with leads) between the tabs
    chip = box(-3, 3, 30.8, 32.26, -2, 2)
    check("3", "chip body (6 x 4 x 1.45) vs casing (mm3)", 0.0, vol_common(cas, chip), 1e-6)
    # pad edges (+-x) are open above the PCB back plane for wires
    for sx in (-1, 1):
        ts = ray(cas, (sx * 12.7, 25, 0), (0, 1, 0), 0, 40)
        check("3", f"+-x wall (pad edge x={sx * 12.7}) top y: flush with the PCB back face 33.85", 33.85, 25 + ts[-1], 0.01)


def test_3_foot_in_divot(cas, ref_corr, ref_plain):
    sl = ref_corr["Slipin_mount_piecev3"]
    local = common(sl, box(-34, -15, 25, 66, -20, 20))
    # foot top, floor contact plane
    floor_pl = [p for p in plane_faces(cas, (-1, 0, 0)) if p[1] > 400][0]
    check("3", "foot bottom plane x (divot floor, design -22.15)", -22.15, floor_pl[0], 0.002)
    top_pl = [p for p in plane_faces(cas, (1, 0, 0)) if abs(p[1] - 446.7) < 1.0][0]
    check("3", "foot +x face x (3.0 proud of the plate face -21.15)", -18.15, top_pl[0], 0.002)
    check("3", "foot stands proud of the plate face by (spec 3.0)", 3.0, top_pl[0] - (-21.15), 0.002)
    check("3", "foot keyed into the divot by (spec 1.0)", 1.0, -21.15 - floor_pl[0], 0.002)
    # lateral gaps measured by rays from the divot centre at depths between the floor and the rim
    gaps = []
    for xl in (-22.10, -21.95, -21.80, -21.60, -21.40, -21.20, -21.16):
        for nm, d in (("+y", (0, 1, 0)), ("-y", (0, -1, 0)), ("+z", (0, 0, 1)), ("-z", (0, 0, -1))):
            o = (xl, 45.0, 0.0)
            tc = ray(cas, o, d, 0, 40)
            tw = ray(local, o, d, 0, 40)
            gaps.append(tw[0] - tc[0])
    check("3", "foot side clearance to the divot wall, 7 depths x 4 sides: min", 0.2, min(gaps), 0.01)
    check("3", "foot side clearance, max (uniform 0.2)", 0.2, max(gaps), 0.01)
    # diagonals: foot corner vs divot corner (R1.2 foot vs R1.0 divot; sharp mitre at +y/+z)
    diag = {}
    for nm, d in (("-y-z", (0, -1, -1)), ("-y+z", (0, -1, 1)), ("+y-z", (0, 1, -1)), ("+y+z", (0, 1, 1))):
        g = []
        for xl in (-22.10, -21.80, -21.40, -21.16):
            o = (xl, 45.0, 0.0)
            tc = ray(cas, o, d, 0, 40)           # the diagonal passes through a screw hole: the foot edge is the LAST crossing
            tw = ray(local, o, d, 0, 40)
            g.append(tw[0] - tc[-1])
        diag[nm] = min(g)
    info("3", "corner (diagonal) gaps, min over depth: -y-z, -y+z, +y-z, +y+z", {k: round(v, 3) for k, v in diag.items()})
    check_min("3", "foot corners clear the divot corners (min diagonal gap, mm)", 0.3, min(diag.values()))
    # no interference in the corrected frame; contact only on the floor
    v_corr = vol_common(cas, sl)
    check("3", "casing/slip-in interference volume, corrected frame (mm3)", 0.0, v_corr, 1e-3)
    ov = vol_common(cas, ref_plain["Slipin_mount_piecev3"])
    info("3", "casing/slip-in interference volume, plain frame (mm3)", ov)
    ovs = common(cas, ref_plain["Slipin_mount_piecev3"]).BoundingBox()
    check_max("3", "plain-frame overlap is a sheet: x thickness (mm) <= the 0.0042 mm residual", 0.0045, ovs.xmax - ovs.xmin,
              note=f"overlap x [{ovs.xmin:.4f}, {ovs.xmax:.4f}] on the floor plane, y [{ovs.ymin:.1f},{ovs.ymax:.1f}]")
    # floor contact area
    check("3", "foot bottom flat area (mm2)", 427.7, floor_pl[1], 1.0, note="21.6 x 21.6 less four holes")
    # distance of the foot to the divot WALL faces only (excludes the floor contact)
    def _in_divot(f):
        b = f.BoundingBox()
        return b.xmin > -22.2 and b.xmax < -21.1 and b.ymin > 32.9 and b.ymax < 57.1 and b.zmin > -12.1 and b.zmax < 12.1
    wall_faces = [f for f in sl.Faces() if _in_divot(f) and (f.geomType() == "SPHERE" or (f.geomType() == "CYLINDER" and abs(f._geomAdaptor().Cylinder().Radius() - 1.0) < 1e-3))]
    dmin = min(min_dist(cas, f) for f in wall_faces)
    check_true("3", "divot wall faces found (4 cylinders + 3 spheres)", len(wall_faces) == 7, len(wall_faces))
    check("3", f"normal gap foot-to-divot-wall ({len(wall_faces)} wall faces), min (mm): the R1.0 foot round follows the dish", 0.02, dmin, 0.01,
          note="~0.02 near the wall/floor tangent edge: the foot only has its 0.2 lateral play, no margin in the normal direction")
    # a plain straight-sided foot would not seat (check of the implementer's reason for the R1.0 round)
    plain_foot = box(-22.15, -18.15, 45 - 11.8, 45 + 11.8, -11.8, 11.8)
    check_true("3", "a plain square 23.6 foot does NOT seat (interferes with the dish wall)", vol_common(plain_foot, local) > 1.0,
               f"{vol_common(plain_foot, local):.2f} mm3")


def test_3_holes_coaxial_with_divot_holes(cas, ref_corr, ref_plain, offs):
    sl_c = ref_corr["Slipin_mount_piecev3"]
    sl_p = ref_plain["Slipin_mount_piecev3"]
    foot_holes = sorted(set((round(c[1][1], 4), round(c[1][2], 4)) for c in cyl_faces(cas, 0) if abs(c[0] - 1.7) < 0.01))
    check("3", "foot holes found", 4, len(foot_holes), 0)
    for r, _, _ in [c for c in cyl_faces(cas, 0) if abs(c[0] - 1.7) < 0.05]:
        check("3", "foot hole diameter (spec Ø3.4)", 3.4, 2 * r, 0.002)
    for frame_name, sl in (("corrected", sl_c), ("plain", sl_p)):
        dh = sorted(set((round(c[1][1], 4), round(c[1][2], 4)) for c in cyl_faces(sl, 0) if abs(c[0] - 1.725) < 0.01))
        dev = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(foot_holes, dh))
        if frame_name == "corrected":
            check_max("3", "foot hole axis to divot hole axis, max offset (mm), corrected frame", 0.001, dev)
        else:
            check_max("3", "foot hole axis to divot hole axis, max offset (mm), plain frame", 0.005, dev,
                      note="0.0042 = the extraction residual")
    check("3", "divot hole diameter measured (Ø3.45); foot hole is smaller by 0.05 (mm)", 3.45, 2 * [c for c in cyl_faces(sl_c, 0) if abs(c[0] - 1.725) < 0.01][0][0], 0.002)
    # pitch
    ys = sorted(set(h[0] for h in foot_holes))
    zs = sorted(set(h[1] for h in foot_holes))
    check("3", "foot hole pitch y (spec 9.5)", 9.5, ys[1] - ys[0], 0.002)
    check("3", "foot hole pitch z (spec 9.5)", 9.5, zs[1] - zs[0], 0.002)
    # holes go through the foot only (4.0 thick) and the divot hole bores are not blocked by anything else
    for (yh, zh) in foot_holes:
        ts = ray(cas, (-40, yh, zh), (1, 0, 0), 0, 80)
        check_true("3", f"ray along the hole axis y={yh} z={zh}: no casing material between x=-22.15 and -18.15",
                   not any(-22.15 + 1e-4 < -40 + t < -18.15 - 1e-4 for t in ts), [round(-40 + t, 3) for t in ts])


def test_3_screw_head_access(cas, ref_corr):
    holes = [(40.25, 4.75), (40.25, -4.75), (49.75, 4.75), (49.75, -4.75)]
    names = list(ref_corr)
    worst_cas = 0.0
    dist_cas = 1e9
    cas_no_foot = cas.cut(box(-23, -18.15, 30, 60, -14, 14))       # the foot itself touches the cylinders at x = -18.15
    hits = {n: 0.0 for n in names}
    for (yh, zh) in holes:
        # Ø7 (M3 pan head Ø6 + 0.5 tool clearance), from the foot +x face outward 55 mm
        access = cyl(3.5, 55.0, (-18.15, yh, zh), (1, 0, 0))
        worst_cas = max(worst_cas, vol_common(cas, access))
        dist_cas = min(dist_cas, min_dist(cas_no_foot, access))
        for n in names:
            hits[n] = max(hits[n], vol_common(access, ref_corr[n]))
    check("3", "screw access cylinders Ø7 x 55 mm from the foot face: interference with casing (mm3)", 0.0, worst_cas, 1e-6)
    for n in names:
        check("3", f"screw access cylinders vs {n} (mm3)", 0.0, hits[n], 1e-6)
    check("3", "screw-head access: closest casing feature to the Ø7 access cylinders (bridge top at y 36.2 vs 36.75) (mm)", 0.55, dist_cas, 0.02)


def test_3_wire_slots(cas):
    for s in (-1, 1):
        zc = s * 6.2
        tx = ray(cas, (-19.0, 33.0, zc), (1, 0, 0), 0, 8.0)
        tzz = ray(cas, (-16.0, 33.0, zc - 3.0), (0, 0, 1), 0, 6.0)
        width_x = tx[1] - tx[0]
        width_z = tzz[1] - tzz[0]
        check("3", f"zip-tie slot at z={zc:+.1f}: length in x (3.0)", 3.0, width_x, 0.01)
        check("3", f"zip-tie slot at z={zc:+.1f}: width in z (1.6)", 1.6, width_z, 0.01)
        thru = ray(cas, (-16.0, 25.0, zc), (0, 1, 0), 0, 20.0)
        check_true("3", f"slot at z={zc:+.1f} is open through the bridge in y (no material between y=31 and y=36.2)",
                   not any(31.001 < 25 + t < 36.199 for t in thru), [round(25 + t, 3) for t in thru])


# =====================================================================================================================
# 4  assembly clearances
# =====================================================================================================================
def test_4_interference_matrix(cap, cas, ref_corr, ref_plain):
    vols = {}
    for fr, refs in (("plain", ref_plain), ("corrected", ref_corr)):
        for pn, part in (("casing", cas), ("cap", cap)):
            for n in REF_NAMES:
                vols[(fr, pn, n)] = vol_common(part, refs[n])
                info("4", f"interference {pn} vs {n} [{fr} frame] (mm3)", vols[(fr, pn, n)])
    # statements: no interference in the corrected frame except the cap ribs
    for n in REF_NAMES:
        check("4", f"casing vs {n}, corrected frame: interference (mm3)", 0.0, vols[("corrected", "casing", n)], 1e-3)
    for n in REF_NAMES:
        v = vols[("corrected", "cap", n)]
        if n == "Spool1011":
            check("4", "cap vs Spool1011, corrected frame: interference (mm3) = crush ribs only", 0.163, v, 0.03)
        else:
            check("4", f"cap vs {n}, corrected frame: interference (mm3)", 0.0, v, 1e-3)
    # plain frame: legitimate contact artefacts only
    for n in REF_NAMES:
        v = vols[("plain", "casing", n)]
        if n == "Slipin_mount_piecev3":
            check("4", "casing vs Slipin, plain frame: 1.83 mm3 contact artefact (<= 0.0042 x 428 mm2 + rim = 2.0)", 1.83, v, 0.2)
        else:
            check("4", f"casing vs {n}, plain frame: interference (mm3)", 0.0, v, 1e-3)


def test_4_minimum_distances(cap, cas, ref_corr, ref_plain):
    for fr, refs in (("corrected", ref_corr), ("plain", ref_plain)):
        d = min_dist(cas, refs["Shell_Casing"])
        check_min("4", f"casing to Shell_Casing min distance [{fr}] (spec >= 1.0)", 1.0, d)
        for n in ("Spool1011", "Motor_Reference", "Heat_horn", "Wall_Mount_v3"):
            info("4", f"casing to {n} min distance [{fr}] (mm)", min_dist(cas, refs[n]))
    # cap swept 360 deg (5 deg steps) vs casing and vs a board model, plus the exact envelope of revolution
    dmin = 1e9
    for a in range(0, 360, 5):
        dmin = min(dmin, min_dist(cap.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), a), cas))
    check_min("4", "cap swept 360 deg (5 deg steps) vs casing: min distance (spec >= 1.0)", 1.0, dmin)
    env = cyl(7.0, 3.3, (0, 26.0, 0), (0, 1, 0))                      # exact envelope of the head for every rotation
    d_env = min_dist(env, cas)
    check("4", "envelope of revolution (Ø14 x y26..29.3) vs casing: min distance (mm), exact lower bound for any rotation", 5.0, d_env, 0.05,
          note="rim (r 7, y 29.3) to the pocket edge (r 11.7, y 31.0) = sqrt(4.7^2 + 1.7^2)")
    board = box(-11.5, 11.5, 32.25, 33.85, -11.5, 11.5).fuse(box(-3, 3, 30.8, 32.26, -2, 2))
    check("4", "cap envelope vs board + chip body: min distance (the chip is the only thing within 1.5) (mm)", 1.5, min_dist(env, board), 0.01)
    # nothing at y < 26 within r 19 of the axis
    check_min("4", "casing: lowest y (line-path zone y < 26 must stay empty)", 26.0, bbox(cas)[2])
    zone = cq.Solid.makeCylinder(19.0, 26.0 - 7.0, cq.Vector(0, 7.0, 0), cq.Vector(0, 1, 0))
    check("4", "casing vs the y 7..26, r 19 line-path zone (mm3)", 0.0, vol_common(cas, zone), 1e-9)
    # the cap's own part below y = 26 is the peg inside the bore
    low = common(cap, box(-20, 20, 0, 25.999, -20, 20))
    ang, rr = radial_profile(cap, 24.3, 0.0, 0.0)
    check_max("4", "cap below y = 26: max radius (inside the Ø5.3 bore, mm)", 2.71, float(np.max(rr)))
    outer = low.cut(cyl(2.9, 40.0, (0, 0, 0), (0, 1, 0)))
    check("4", "cap below y = 26 outside r 2.9 (the line-path zone, r 7.5 .. 19) (mm3)", 0.0, outer.Volume(), 1e-9)


def test_4_cap_vs_casing_foot_sequence_free_travel(cap, cas):
    """Assembly path: with the cap on the spool the casing is slid in along -x with its front at y >= 31 - nothing at y < 30.8."""
    check_min("4", "casing keeps y >= 31.0, cap top is 29.3: axial margin during a -x slide-in (mm)", 1.69, bbox(cas)[2] - bbox(cap)[3])


# =====================================================================================================================
# 5  stack-up
# =====================================================================================================================
def _foot_rotation_limit(cas, local_slip, dz_shift, sign):
    """Largest rotation (deg) of the casing about the x axis through the divot centre such that the foot still clears the divot,
    after the foot has been translated by dz_shift in z.  Bisection on the interference volume (< 1e-3 mm3 = free)."""
    foot = common(cas, box(-22.2, -18.0, 32, 58, -13, 13)).translate(cq.Vector(0, 0, dz_shift))
    lo, hi = 0.0, 3.0
    for _ in range(9):
        mid = 0.5 * (lo + hi)
        f = foot.rotate(cq.Vector(0, 45.0, 0), cq.Vector(1, 45.0, 0), sign * mid)
        if vol_common(f, local_slip) < 1e-3:
            lo = mid
        else:
            hi = mid
    return lo


def test_5_stackup_vs_as5600_limit(cas, cap, ref_corr):
    local = common(ref_corr["Slipin_mount_piecev3"], box(-30, -17, 25, 65, -20, 20))
    lever = 45.0 - 30.8                                                   # divot centre y - chip face y
    # foot: translation play (measured above: 0.2 per side) and rotation limit measured by BRep
    th0 = _foot_rotation_limit(cas, local, 0.0, +1)
    th0n = _foot_rotation_limit(cas, local, 0.0, -1)
    info("5", "foot rotation limit in the divot about x, deg (+, -)", (round(th0, 3), round(th0n, 3)))
    check_true("5", "foot can rotate by about +-1 deg in the divot (0.2 mm per side on a 23.6 foot)", 0.9 < th0 < 1.3 and 0.9 < th0n < 1.3)
    chip_dz_rot = lever * math.radians(max(th0, th0n))
    # combined translation + rotation: maximise |dz + lever*theta| on the feasible boundary
    best = chip_dz_rot
    combo = []
    for d in (0.05, 0.10, 0.15, 0.20):
        t = _foot_rotation_limit(cas, local, d, -1)                       # rotate so that the chip moves the same way as dz
        combo.append((d, round(t, 3), round(d + lever * math.radians(t), 3)))
        best = max(best, d + lever * math.radians(t))
    info("5", "foot translation d (mm), rotation limit at that d (deg), chip z shift (mm)", combo)
    foot_z = best
    # board in pocket: measured pocket width minus the nominal 23.0 board
    dd = [ray(cas, (0, 33.0, 0), v, 0, 40)[0] for v in ((1, 0, 0), (-1, 0, 0))]
    board_clear = (dd[0] + dd[1] - SPEC["pcb"]) / 2                       # 0.2 per axis
    # cap peg in the bore (round part, measured from the spool and the cap); flat clearance is the same 0.10 (item 2)
    a_, rb = radial_profile(ref_corr["Spool1011"], 24.3, 0.0, 0.0)
    a_, rc = radial_profile(cap, 24.3, 0.0, 0.0)
    rmask = np.cos(np.radians(a_)) < 0.5
    peg = float(np.median(rb[rmask])) - float(np.median(rc[rmask & (rc < 2.6)]))
    # magnet in its pocket: pocket radius from the cap minus the nominal Ø6 magnet
    mag = [c for c in cyl_faces(cap, 1) if abs(c[0] - 3.1) < 0.01][0][0] - 3.0
    z_wc = foot_z + board_clear + peg + mag
    x_wc = 0.0 + board_clear + peg + mag                                  # x is datum-ed by the divot floor: no foot play in x
    wc = math.hypot(x_wc, z_wc)
    z_rss = math.sqrt(foot_z ** 2 + board_clear ** 2 + peg ** 2 + mag ** 2)
    x_rss = math.sqrt(board_clear ** 2 + peg ** 2 + mag ** 2)
    rss = math.hypot(x_rss, z_rss)
    info("5", "lateral budget per source (mm): foot z (rotation-dominated), board, cap peg, magnet in pocket",
         (round(foot_z, 3), board_clear, peg, mag))
    info("5", "worst-case chip-to-magnet axis offset: x, z, radial (mm)", (round(x_wc, 3), round(z_wc, 3), round(wc, 3)))
    info("5", "RSS chip-to-magnet axis offset: x, z, radial (mm)", (round(x_rss, 3), round(z_rss, 3), round(rss, 3)))
    # recommended tightening (not built): board 0.1, foot 0.1/side (rotation halves), peg 0.05, magnet pocket 0.05
    foot_z2 = foot_z / 2
    z2 = foot_z2 + 0.1 + 0.05 + 0.05
    x2 = 0.1 + 0.05 + 0.05
    rss2 = math.hypot(math.sqrt(foot_z2 ** 2 + 0.1 ** 2 + 0.05 ** 2 + 0.05 ** 2), math.sqrt(0.1 ** 2 + 0.05 ** 2 + 0.05 ** 2))
    info("5", "with PCB_CLEAR 0.1, foot clearance 0.1/side, peg clearance 0.05, magnet pocket Ø6.1: worst-case radial, RSS (mm)",
         (round(math.hypot(x2, z2), 3), round(rss2, 3)))
    # axial: air gap range from the measured foot y play at the rim level
    gy = [ray(local, (-21.2, 45.0, 0.0), d, 0, 40)[0] - ray(cas, (-21.2, 45.0, 0.0), d, 0, 40)[0] for d in ((0, 1, 0), (0, -1, 0))]
    info("5", "foot y play each side (mm)", gy)
    lo_gap, hi_gap = 1.5 - min(gy), 1.5 + min(gy)
    check_true("5", "air gap range from the foot y play stays inside the AS5600 0.5 .. 3 mm window", 0.5 < lo_gap and hi_gap < 3.0,
               f"{lo_gap:.2f} .. {hi_gap:.2f}")
    RECORDS.append(dict(item="5", what="stack-up worst-case radial offset vs AS5600 limit 0.25 mm", expected=f"<= {AS5600_DISPLACEMENT_MM}",
                        measured=wc, tol="max", status="FAIL" if wc > AS5600_DISPLACEMENT_MM else "PASS",
                        note="datasheet figure from search-engine excerpts of mirror copies; official ams PDF not opened"))
    RECORDS.append(dict(item="5", what="stack-up RSS radial offset vs AS5600 limit 0.25 mm", expected=f"<= {AS5600_DISPLACEMENT_MM}",
                        measured=rss, tol="max", status="FAIL" if rss > AS5600_DISPLACEMENT_MM else "PASS", note=""))
    # finding is encoded rather than hidden: the stack-up exceeds the limit
    assert wc > AS5600_DISPLACEMENT_MM and rss > AS5600_DISPLACEMENT_MM, "stack-up now within the AS5600 limit: update the report"


# =====================================================================================================================
# 6  manufacturability
# =====================================================================================================================
def _overhangs(tri, limit_deg=45.0, tol_deg=0.5):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    a = 0.5 * np.linalg.norm(n, axis=1)
    nz = np.where(a > 0, n[:, 2] / (2 * np.maximum(a, 1e-18)), 0.0)
    zmin = tri[:, :, 2].min()
    bed = np.all(np.abs(tri[:, :, 2] - zmin) < 1e-4, axis=1)
    bad = (nz < -math.sin(math.radians(limit_deg + tol_deg))) & ~bed & (a > 1e-9)
    clusters = []
    if bad.any():
        zc = np.round(tri[bad][:, :, 2].mean(axis=1) / 0.1) * 0.1
        for lv in np.unique(zc):
            sel = zc == lv
            pts = tri[bad][sel].reshape(-1, 3)
            clusters.append(dict(z=float(lv), area=float(a[bad][sel].sum()), nz_min=float(nz[bad][sel].min()),
                                 lo=pts.min(axis=0).round(2).tolist(), hi=pts.max(axis=0).round(2).tolist()))
    return clusters, float(a[bed].sum())


def test_6_print_orientation_and_overhangs(cas, cap):
    tc = read_stl(CAS_STL)
    pc = read_stl(CAP_STL)
    for nm, tri, step in (("casing", tc, cas), ("cap", pc, cap)):
        p = tri.reshape(-1, 3)
        check_max("6", f"{nm} STL lowest z (on the bed)", 1e-3, abs(float(p[:, 2].min())))
    bed_cas = _overhangs(tc)[1]
    front = max((p for p in plane_faces(cas, (0, -1, 0))), key=lambda p: p[1])[1]
    check("6", "casing bed contact area (mm2) = the y = 31.0 front face", front, bed_cas, 0.5, note="frame front on the bed, +y up")
    bed_cap = _overhangs(pc)[1]
    expected_cap_bed = math.pi * (6.7 ** 2 - 3.1 ** 2)                       # Ø13.4 after the 0.3 chamfer, minus the pocket
    check("6", "cap bed contact area (mm2): magnet face on the bed", expected_cap_bed, bed_cap, 1.0)
    check("6", "casing STL print bbox (35.85 x 27.4 x 25.8)", 35.85 + 27.4 + 25.8, float(sum(tc.reshape(-1, 3).max(0))), 0.01)
    # overhangs steeper than 45 deg (not on the bed)
    oc, _ = _overhangs(tc)
    info("6", "casing overhang clusters (z, area, bbox)", [(c["z"], round(c["area"], 2), c["lo"], c["hi"]) for c in oc])
    catch = [c for c in oc if abs(c["z"] - 2.95) < 0.06 and c["area"] > 5]
    check("6", "casing: hook catch ledges, total area (2 x 0.6 x 8.0 mm2)", 9.6, sum(c["area"] for c in catch), 0.2)
    others = [c for c in oc if c not in catch]
    ledge_w = max((c["hi"][0] - c["lo"][0]) for c in others) if others else 0.0
    check_max("6", "casing: widest other overhang (foot key edge) in x (mm) <= 1.0 (bridging < 2.5 line widths)", 1.0, ledge_w)
    check_max("6", "casing: total overhang area outside the catch ledges (mm2)", 30.0, sum(c["area"] for c in others))
    pk = _overhangs(pc)[0]
    check("6", "cap: overhang is only the pocket floor seen as a ceiling (mm2)", math.pi * 3.1 ** 2, sum(c["area"] for c in pk), 0.5)
    check("6", "cap: pocket-floor bridge span (mm)", 6.2, pk[0]["hi"][0] - pk[0]["lo"][0], 0.05,
          note="PETG bridges ~6 mm with good cooling; sag raises the floor into the pocket")
    # pocket plan in print coordinates: x_print = x + 22.15 -> 10.45 .. 33.85 ; y_print = 13.7 - z -> 2.0 .. 25.4
    check("6", "casing overhangs over the board pocket plan other than the 2 catch ledges (count)", 0,
          len([c for c in oc if c not in catch and c["lo"][0] >= 10.4 and c["hi"][0] <= 33.9 and c["lo"][1] >= 1.9 and c["hi"][1] <= 25.5]), 0)


def _thickness_samples(tri, n, seed):
    rng = np.random.default_rng(seed)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    idx = rng.choice(len(tri), size=n, p=area / area.sum())
    u, v = rng.random((n, 1)), rng.random((n, 1))
    flip = (u + v) > 1
    u, v = np.where(flip, 1 - u, u), np.where(flip, 1 - v, v)
    p = tri[idx, 0] + u * (tri[idx, 1] - tri[idx, 0]) + v * (tri[idx, 2] - tri[idx, 0])
    nn = nrm[idx] / np.linalg.norm(nrm[idx], axis=1)[:, None]
    e1, e2, v0 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0], tri[:, 0]
    out = np.full(n, np.inf)
    for i in range(n):
        d = -nn[i]
        o = p[i] + d * 1e-4
        h = np.cross(d, e2)
        a = np.einsum("ij,ij->i", e1, h)
        ok = np.abs(a) > 1e-12
        f = np.where(ok, 1.0 / np.where(ok, a, 1.0), 0.0)
        s = o - v0
        uu = f * np.einsum("ij,ij->i", s, h)
        q = np.cross(s, e1)
        vv = f * (q @ d)
        t = f * np.einsum("ij,ij->i", e2, q)
        m = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (t > 1e-4)
        m[idx[i]] = False
        if m.any():
            out[i] = t[m].min()
    return p, nn, out


def test_6_minimum_walls(cas, cap):
    # designed walls, measured on the STEP by rays
    for s in (-1, 1):
        ts = ray(cas, (0, 33.0, s * 11.0), (0, 0, s), 0, 4.0)
        check("6", f"flex wall at z{s:+d}: thickness at y=33 (notes: 1.2)", 1.2, ts[1] - ts[0], 0.005)
        ts = ray(cas, (0, 34.2, s * 11.0), (0, 0, s), 0, 4.0)
        check("6", f"hook wall at z{s:+d}: thickness at y=34.2 through the lip tip flat (wall 1.2 + lip 0.6)", 1.8, ts[1] - ts[0], 0.005,
              note="lip protrudes 0.6 from the 1.2 wall")
    ts = ray(cas, (11.0, 32.5, 0), (1, 0, 0), 0, 4.0)
    check("6", "+x wall (pad edge): thickness (spec 2.0)", 2.0, ts[1] - ts[0], 0.005)
    ts = ray(cas, (-11.0, 32.5, 0), (-1, 0, 0), 0, 12.0)
    check("6", "-x side: wall + bridge block, solid from the pocket to the bridge end (x -11.7 .. -20.9)", 9.2, ts[1] - ts[0], 0.01)
    # lip tip thickness (along y) at its end: the 45 deg ramp leaves 0.4 mm
    ts = ray(cas, (0, 33.0, 11.101), (0, 1, 0), 0, 4.0)
    check("6", "hook lip thickness along y at its tip (catch face to ramp start)", 0.4, ts[1] - ts[0], 0.01,
          note="2 layers at 0.2; thin feature, expect stringing / weak tip")
    # global sampling for anything thinner than 1.15 mm that is not a hook lip
    tri = read_stl(CAS_STL)
    p, nn, t = _thickness_samples(tri, 6000, 11)
    thin = np.where(t < 1.15)[0]
    def _lip(q):       # print coordinates of the two hook lips: x 18.15 .. 26.15 (station x -4 .. 4), y 1.9 .. 2.7 / 24.7 .. 25.5, z 2.9 .. 4.0
        return 18.1 <= q[0] <= 26.2 and (1.9 <= q[1] <= 2.7 or 24.7 <= q[1] <= 25.5) and 2.9 <= q[2] <= 4.0
    not_lip = [i for i in thin if not _lip(p[i])]
    info("6", "casing sampled local thickness (6000 surface rays): min, count < 1.15 (all at the hook lips)", (float(t.min()), len(thin)))
    check("6", "casing: samples thinner than 1.15 mm away from the hook lips (count)", 0, len(not_lip), 0)
    # cap
    ts = ray(cap, (2.9, 28.0, 0), (0, -1, 0), 0, 5.0)                      # beside the peg, under the pocket floor
    check("6", "cap: solid under the magnet pocket (pocket floor to head underside)", 0.75, ts[1] - ts[0], 0.005)
    ts = ray(cap, (0, 28.0, 0), (1, 0, 0), 0, 10.0)
    check("6", "cap: ring wall around the pocket (r 3.1 to r 7.0, before the chamfer)", 3.9, ts[1] - ts[0], 0.01)


def test_6_ribs_vs_nozzle(cap, ref_corr):
    ang, rc = radial_profile(cap, 24.3, 0.0, 0.0, n=1440)
    mask = np.cos(np.radians(ang)) < 0.5
    r0 = float(np.median(rc[mask & (rc < 2.6)]))
    rib = rc > r0 + 0.01
    sectors = []
    for a in ang[rib]:
        if not sectors or a - sectors[-1][-1] > 1.0:
            sectors.append([a])
        else:
            sectors[-1].append(a)
    check("6", "crush ribs found at y = 24.3", 3, len(sectors), 0)
    tip = float(rc[rib].max())
    height = tip - r0
    check("6", "rib height above the round peg surface (mm)", 0.15, height, 0.01)
    # width at half height (arc length) from the angular extent of samples above r0 + height / 2
    def _width(frac):
        lvl = r0 + frac * height
        out = []
        for s in sectors:
            in_s = [a for a in ang[rc > lvl] if s[0] - 5 <= a <= s[-1] + 5]
            out.append(math.radians(max(in_s) - min(in_s) + 0.25) * lvl)
        return float(np.mean(out))
    w_base, w_half, w_tip = _width(0.05), _width(0.5), _width(0.9)
    info("6", "rib width at 5 % / 50 % / 90 % of its height (mm)", (round(w_base, 2), round(w_half, 2), round(w_tip, 2)))
    check_true("6", f"rib tip (90 % height) narrower than the {NOZZLE_MM} mm nozzle and rib height < 0.2: not printable as a separate line",
               w_tip < NOZZLE_MM and height < 0.2, f"tip width {w_tip:.2f}, height {height:.2f}",
               note="the bump rides on the contour; a 0.4 mm nozzle rounds a 0.3 mm tip, so the real crush is 0 to 0.1 mm and not repeatable")
    # crush relative to the bore
    bore_r = 2.65
    info("6", "nominal radial crush (rib tip - bore radius) (mm)", tip - bore_r)


def test_6_snap_hook_strain(cas):
    """Independent hand calculation (clamped-clamped beam, central load): sigma = 12 E t d / L^2, strain = 12 t d / L^2."""
    L = 23.4
    t = 1.2
    ys = ray(cas, (0, 25, 11.9), (0, 1, 0), 0, 20)
    h = (25 + ys[-1]) - 31.0
    check("6", "hook wall height (y 31.0 .. top)", 4.05, h, 0.01)
    rows = []
    for label, d in (("centred board, 0.4 overlap + 0.1 margin", 0.5), ("centred board, no margin", 0.4),
                     ("board against one wall (+0.2 play), no margin", 0.6), ("same, with 0.1 margin", 0.7)):
        sig = 12 * PETG_E_MPA * t * d / L ** 2
        eps = 12 * t * d / L ** 2
        F = 192 * PETG_E_MPA * (h * t ** 3 / 12) * d / L ** 3
        rows.append((label, d, round(F, 1), round(sig, 1), round(100 * eps, 2), round(100 * sig / PETG_YIELD_MPA)))
    info("6", "snap hook (label, deflection mm, force N per wall, stress MPa, strain %, % of PETG yield 45 MPa)", rows)
    check("6", "hook stress, implementer's case (0.5 mm) (MPa), reproduces notes 27.6", 27.6, rows[0][3], 0.2)
    check_max("6", "hook strain for the centred board (%) <= 2 (assumed one-shot limit for printed PETG)", 2.0, rows[0][4])
    check_max("6", "hook stress for the worst insertion (board against one wall + margin) (% of yield)", 100, rows[3][5],
              note="86 % of yield: no margin for a second insertion")
    _rec("6", "hook strain for the worst insertion (%) vs 2 % one-shot allowance", "<= 2.0", rows[3][4], "max",
         "PASS" if rows[3][4] <= 2.0 else "FAIL", "1.84 %: inside, with <10 % margin")


def test_6_bridge_stiffness_hand_calc_reproduced(cas):
    """Spec: a 1 N push on the frame must move the chip < 0.1 mm.  Reproduce the cantilever hand calculation with the section
    measured here (ray-sampled cross-section of the bridge neck at x = -16, only the part against the foot, y >= 33.2)."""
    x_mid, y_lo = -16.0, 33.2
    dz = 0.05
    zs = np.arange(-13.7 + dz / 2, 13.7, dz)
    area = 0.0
    sy = 0.0
    syy = 0.0
    for z in zs:
        ts = ray(cas, (x_mid, 25.0, z), (0, 1, 0), 0, 20.0)
        ys = [25.0 + t for t in ts]
        for a, b in zip(ys[0::2], ys[1::2]):
            a = max(a, y_lo)
            if b <= a:
                continue
            area += (b - a) * dz
            sy += 0.5 * (b * b - a * a) * dz
            syy += (b ** 3 - a ** 3) / 3.0 * dz
    yc = sy / area
    I = syy - area * yc * yc
    check("6", "bridge neck section at x=-16, y 33.2..36.2: area (mm2) = (27.4 - 2 x 1.6) x 3.0", 24.2 * 3.0, area, 0.3)
    check("6", "bridge neck second moment for y-deflection (mm4) = 24.2 x 3.0^3 / 12", 54.45, I, 1.0)
    F, E, L, a = 1.0, PETG_E_MPA, 13.7 + 18.15, 18.15
    d_y = F * a * a * (3 * L - a) / (6 * E * I)
    check("6", "chip motion in y for 1 N on the far wall (mm), cantilever model, reproduces the notes' 0.037", 0.037, d_y, 0.004)
    check_max("6", "chip motion for 1 N (mm) < 0.1 (spec)", 0.1, d_y,
              note="clamp at the foot face assumed rigid: foot screws, floor contact and slip-in flexibility are NOT in this number")


# =====================================================================================================================
# 7  STEP / STL round trip
# =====================================================================================================================
def test_7_step_roundtrip_and_stl(cap, cas, tmp_path):
    from cad.parts import encoder1021 as E            # builder's solids (only here)
    with E.params_override(ENC1021_MAGNET_D=6.0):     # the cap on disk was exported for the Ø6 magnet (before Jasper's 10/22 measurement, Ø4.0): superseded record
        cap_builder = E.make_magnet_cap().val()
    for nm, step_shape, builder, stl_path in (("cap", cap, cap_builder, CAP_STL), ("casing", cas, E.make_casing().val(), CAS_STL)):
        bs, ss = builder.BoundingBox(), step_shape.BoundingBox()
        for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            check("7", f"{nm}: STEP file vs builder bbox {k}", getattr(bs, k), getattr(ss, k), 1e-3)
        check("7", f"{nm}: STEP file vs builder volume (mm3)", builder.Volume(), step_shape.Volume(), 0.01)
        # real round trip: write the re-imported solid again and read it back
        p = str(tmp_path / f"{nm}_rt.step")
        cq.exporters.export(cq.Workplane("XY").add(step_shape), p)
        rt = load_step(p)
        rb = rt.BoundingBox()
        for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            check("7", f"{nm}: STEP -> reimport -> re-export -> reimport bbox {k}", getattr(ss, k), getattr(rb, k), 1e-3)
        check("7", f"{nm}: re-exported volume (mm3)", step_shape.Volume(), rt.Volume(), 0.01)
        check("7", f"{nm}: re-imported solid count", 1, n_solids(rt), 0)
        check_true("7", f"{nm}: re-imported solid valid", brep_valid(rt))
        # symmetric difference between the file and the builder solid
        x = builder.cut(step_shape).Volume() + step_shape.cut(builder).Volume()
        check("7", f"{nm}: volume of the boolean difference file vs builder (mm3)", 0.0, x, 0.01)
        # file-level: millimetre units and exactly one MANIFOLD_SOLID_BREP in the STEP text
        txt = open(CAP_STEP if nm == "cap" else CAS_STEP).read()
        check_true("7", f"{nm}: STEP units are millimetres", "SI_UNIT(.MILLI.,.METRE.)" in txt)
        check("7", f"{nm}: MANIFOLD_SOLID_BREP entities in the STEP file", 1, txt.count("MANIFOLD_SOLID_BREP("), 0)
        # STL
        tri = read_stl(stl_path)
        check("7", f"{nm}: STL is watertight (edges not shared by exactly 2 triangles)", 0, stl_watertight(tri), 0)
        check("7", f"{nm}: STL volume vs STEP volume (mm3, tessellation 0.02 mm)", step_shape.Volume(), stl_volume(tri),
              0.003 * step_shape.Volume())
        p3 = tri.reshape(-1, 3)
        ext = p3.max(0) - p3.min(0)
        sext = sorted((ss.xlen, ss.ylen, ss.zlen))
        for a, b in zip(sorted(ext), sext):
            check("7", f"{nm}: STL print-pose extent vs STEP extent (sorted)", b, a, 0.005)


# =====================================================================================================================
# 8  renders
# =====================================================================================================================
def test_8_renders_present():
    views = ("front", "rear", "left", "right", "top", "bottom", "iso")
    for part in ("encoder1021_casing", "encoder1021_magnet_cap"):
        for v in views:
            f = os.path.join(RENDER_DIR, f"{part}_{v}.png")
            check_true("8", f"render present: {part}_{v}.png", os.path.isfile(f) and os.path.getsize(f) > 5000, os.path.getsize(f) if os.path.isfile(f) else 0)
    for f in ("encoder1021_assembly_iso.png", "encoder1021_assembly_iso_front.png", "encoder1021_assembly_section_z0.png",
              "encoder1021_casing_section_z0.png", "encoder1021_casing_section_x0.png", "encoder1021_casing_section_hole_row.png",
              "encoder1021_magnet_cap_section_z0.png"):
        p = os.path.join(RENDER_DIR, f)
        check_true("8", f"render present: {f}", os.path.isfile(p) and os.path.getsize(p) > 5000)
