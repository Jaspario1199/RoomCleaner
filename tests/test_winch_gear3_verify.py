"""Independent verification of the 3:1 spur winch drive train, REVISION C = printed PETG pinion 18T, 54T gear (geometry-verifier).

Contract: cad/WINCH_GEAR3_SPEC.md revision C note (D42) on top of revision B (D41).  Revisions A (20T/60T) and B (18T/54T, steel pinion) passed earlier
runs of this file; this file was updated to revision C from the spec, not from the implementation.  It measures the EXPORTED files only (exports/step/winch_gear3_*.step, exports/stl/winch_gear3_*.stl).
It does not import the implementer's builder (cad/parts/winch_gear3.py) or the implementer's tests.  The only repository code it loads is
  * the spec-mandated involute generator cad/gripper_v3_fit_review_20261018/gears.py (to rebuild the gears independently), and
  * cad/params.py (read-only, for the parameter audit in test_20).
Spec numbers are hard-coded below (from the spec text; the parameter NAMES in test_20 are the only thing taken from the repo), not read from the implementer's parameters.

Run (about 8 min):
    cd /home/user/RoomCleaner && /usr/bin/python3 -m pytest -q -s -p no:cacheprovider tests/test_winch_gear3_verify.py
The -s run prints a summary table (item, expected, measured, tolerance, status) at the end (test_99_summary).

Frames.  Assembly STEPs are station_1021 + O (O = 1269.08, 738.76, 927.56) plus the 0.004 mm extraction residual RES that the builder deliberately
carries so the bodies coincide with Jasper's STEP files.  Every assembly body is translated by -(O + RES) here, which gives the design frame of the
spec (motor axis x 0, z 2.64; +y along the motor shaft toward the spool; +x out of the wall; +z up).  O is cross-checked against Jasper's original
SolidWorks assembly (the slide-in and wall mount coincide with it).  Part STEPs are in the print frame (axis +z; spool/spacer/cap: near face on z = 0; pinion18: teeth end, design y 20.825, on z = 0).
"""
from __future__ import annotations

import functools
import importlib.util
import itertools
import math
import os
import struct
from collections import Counter

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")
from OCP.BRepAdaptor import BRepAdaptor_Surface  # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut  # noqa: E402
from OCP.BRepBndLib import BRepBndLib  # noqa: E402
from OCP.BRepCheck import BRepCheck_Analyzer  # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier  # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape  # noqa: E402
from OCP.BRepGProp import BRepGProp  # noqa: E402
from OCP.Bnd import Bnd_Box  # noqa: E402
from OCP.GProp import GProp_GProps  # noqa: E402
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane  # noqa: E402
from OCP.IFSelect import IFSelect_RetDone  # noqa: E402
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector  # noqa: E402
from OCP.STEPCAFControl import STEPCAFControl_Reader  # noqa: E402
from OCP.TCollection import TCollection_ExtendedString  # noqa: E402
from OCP.TDF import TDF_Label, TDF_LabelSequence  # noqa: E402
from OCP.TDataStd import TDataStd_Name  # noqa: E402
from OCP.TDocStd import TDocStd_Document  # noqa: E402
from OCP.TopAbs import TopAbs_IN  # noqa: E402
from OCP.TopLoc import TopLoc_Location  # noqa: E402
from OCP.XCAFApp import XCAFApp_Application  # noqa: E402
from OCP.XCAFDoc import XCAFDoc_DocumentTool  # noqa: E402
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP = os.path.join(REPO, "exports", "step") + os.sep
STL = os.path.join(REPO, "exports", "stl") + os.sep
RENDERS = os.path.join(REPO, "renders", "winch_gear3") + os.sep
SW_ASSEMBLY = os.path.join(REPO, "solidworks", "v4_assembly_2026-10-21", "Assem_laundry_v3_step_1021.STEP")
GEARS_PY = os.path.join(REPO, "cad", "gripper_v3_fit_review_20261018", "gears.py")

O = np.array([1269.08, 738.76, 927.56])          # station_1021 -> assembly offset (repo convention for every *_asm1021 export)
RES = np.array([0.004243, 0.001645, 0.003854])   # extraction residual carried by the bodies
POS_TOL = 0.005                                   # mm, positions/diameters after removing O + RES (the residual is known to 1e-6)
RT_TOL = 1.0e-3                                   # 0.1 %

# ---- spec numbers (cad/WINCH_GEAR3_SPEC.md revision B + revision C note), hard-coded
MOD = 1.0                                         # module
NP, NG = 18, 54                                   # tooth counts (revision B, D41)
CD_ALLOW = 0.30                                   # revision C: printed against printed (rev B steel against printed: 0.20)
CD = 36.00 + CD_ALLOW                             # built centre distance 36.30 (nominal m (18 + 54) / 2 = 36.00)
ZM, ZS = 2.64, 2.64 - CD                          # motor axis z, spool axis z = -33.66 (x = 0 for both)
THIN = 0.10                                       # tooth thinning, gear and (revision C) pinion
Y_HUB0, Y_BOSS = -0.675, -1.175                   # pinion hub end; motor pilot boss face (front face -3.175 + 2.0)
BORE_R, BORE_FLAT = 2.65, 2.15                    # printed D-bore O5.30, flat 2.15 from the axis on +z
INS_R, INS_DEPTH, SS_R = 2.0, 4.5, 1.5            # heat-set pocket O4.0 x 4.5, clearance hole O3.0
Y_SS = (5.0 + 10.825) / 2.0                       # 7.9125, middle of the exposed hub (tab face y 5.0 .. teeth y 10.825)
CH = 0.3                                          # bed/teeth-end chamfer
RP_TIP, RP_ROOT, RP_PITCH = 10.0, 7.75, 9.0       # pinion: tip O20, root R = m (z/2 - 1.25) = 7.75 (generator), pitch R 9
RG_TIP, RG_ROOT, RG_PITCH = 28.0, 25.75, 27.0     # gear: tip O56, root R 25.75 (spec section 3), pitch R 27
WIN_D, WIN_R = 10.0, 17.5                         # lightening windows
Y_T0, Y_T1 = 10.825, 20.825                       # teeth faces
DRIVE_NAMES = ["motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "fin", "pinion",
               "spool_gear54", "shaft", "bearing_near", "bearing_far", "spacer_near", "magnet_cap", "magnet", "as5600_chip", "as5600_board"]
GEARS_NAMES = ["pinion", "spool_gear54"]          # gears_asm1021: the two meshing bodies (names inferred from the other assemblies; spec lists none)

REC: list = []   # (section, item, expected, measured, tolerance, status)


def rec(section, item, expected, measured, tol, ok):
    REC.append((section, item, expected, measured, tol, "PASS" if ok else "FAIL"))
    return ok


def check(section, item, expected, measured, tol):
    ok = abs(measured - expected) <= tol
    rec(section, item, f"{expected:.4f}", f"{measured:.4f}", f"+-{tol}", ok)
    assert ok, f"{section} / {item}: expected {expected} +- {tol}, measured {measured}"


def check_ge(section, item, limit, measured, unit=""):
    ok = measured >= limit
    rec(section, item, f">= {limit}{unit}", f"{measured:.4f}", "-", ok)
    assert ok, f"{section} / {item}: expected >= {limit}, measured {measured}"


def check_le(section, item, limit, measured, unit=""):
    ok = measured <= limit
    rec(section, item, f"<= {limit}{unit}", f"{measured:.5f}", "-", ok)
    assert ok, f"{section} / {item}: expected <= {limit}, measured {measured}"


def check_true(section, item, expected, measured, cond):
    rec(section, item, str(expected), str(measured), "-", bool(cond))
    assert cond, f"{section} / {item}: expected {expected}, measured {measured}"


def check_same_solid(sec, item, a, b):
    """Two solids in the same frame are the same solid: volume, area, centre of mass and inertia agree to numerical noise (<= 1e-9 relative, 1e-9 mm
    for the printed parts; 1e-8 relative for Jasper's 6e5 mm3 wall mount whose reference STEP is integrated differently).  A 0.5 deg rotation of
    the 54T spool alone changes the centre of mass by 3e-5 mm and the inertia by 9e-7 relative, so these limits detect it."""
    dv, da, dc, di = inv_diff(a, b)
    ok = dv <= 1e-7 and da <= 1e-7 and dc <= 1e-5 and di <= 1e-7
    rec(sec, item, "dV<=1e-7 rel, dA<=1e-7 rel, dCOM<=1e-5 mm, dI<=1e-7 rel", f"dV {dv:.1e}, dA {da:.1e}, dCOM {dc:.1e}, dI {di:.1e}", "-", ok)
    assert ok, f"{sec} / {item}: dV {dv}, dA {da}, dCOM {dc}, dI {di}"


# =============================================================================== helpers (fresh, independent of the implementer's code)
def vol(s):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(s.wrapped, p)
    return p.Mass()


def valid(s):
    return BRepCheck_Analyzer(s.wrapped).IsValid()


def tbb(s):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(s.wrapped, b, True, False)
    return np.array([b.CornerMin().X(), b.CornerMax().X(), b.CornerMin().Y(), b.CornerMax().Y(), b.CornerMin().Z(), b.CornerMax().Z()])


def common(a, b):
    return cq.Shape.cast(BRepAlgoAPI_Common(a.wrapped, b.wrapped).Shape())


def invariants(s):
    """Volume, surface area, centre of mass and the inertia matrix about the origin: a cheap, sensitive fingerprint of a placed solid."""
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(s.wrapped, p)
    q = GProp_GProps()
    BRepGProp.SurfaceProperties_s(s.wrapped, q)
    c, m = p.CentreOfMass(), p.MatrixOfInertia()
    return dict(V=p.Mass(), A=q.Mass(), C=np.array([c.X(), c.Y(), c.Z()]), I=np.array([[m.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)]))


def inv_diff(a, b):
    """(dV relative, dA relative, dCOM mm, dI relative) between two solids placed in the same frame."""
    x, y = invariants(a), invariants(b)
    return (abs(x["V"] - y["V"]) / y["V"], abs(x["A"] - y["A"]) / y["A"], float(np.abs(x["C"] - y["C"]).max()), float(np.abs(x["I"] - y["I"]).max() / np.abs(y["I"]).max()))


def cut(a, b):
    return cq.Shape.cast(BRepAlgoAPI_Cut(a.wrapped, b.wrapped).Shape())


def cvol(a, b):
    return vol(common(a, b))


def mindist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value(), d


def shift_design(s):
    return s.translate(cq.Vector(*(-(O + RES))))


def load_step(path):
    return cq.importers.importStep(path)


def _name(label):
    a = TDataStd_Name()
    return a.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), a) else None


@functools.lru_cache(None)
def read_asm(path):
    """Named bodies of a STEP assembly (XCAF): {name: located cq.Shape}, in file (assembly) coordinates."""
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    rd = STEPCAFControl_Reader()
    rd.SetNameMode(True)
    assert rd.ReadFile(path) == IFSelect_RetDone
    assert rd.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    free = TDF_LabelSequence()
    st.GetFreeShapes(free)
    out, dup = {}, []

    def walk(label, loc):
        if st.IsAssembly_s(label):
            comps = TDF_LabelSequence()
            st.GetComponents_s(label, comps)
            for i in range(1, comps.Length() + 1):
                c = comps.Value(i)
                ref = TDF_Label()
                if st.GetReferredShape_s(c, ref):
                    walk2(ref, loc.Multiplied(st.GetLocation_s(c)), _name(c) or _name(ref))
        else:
            out[_name(label)] = cq.Shape.cast(st.GetShape_s(label))

    def walk2(label, loc, nm):
        if st.IsAssembly_s(label):
            comps = TDF_LabelSequence()
            st.GetComponents_s(label, comps)
            for i in range(1, comps.Length() + 1):
                c = comps.Value(i)
                ref = TDF_Label()
                if st.GetReferredShape_s(c, ref):
                    walk2(ref, loc.Multiplied(st.GetLocation_s(c)), _name(c) or _name(ref))
        else:
            shp = st.GetShape_s(label)
            shp = shp.Located(loc.Multiplied(shp.Location()))
            key = _name(label) or nm                  # name of the referred part (instance names may carry a "-1" suffix)
            if key in out:
                dup.append(key)
            out[key] = cq.Shape.cast(shp)

    for i in range(1, free.Length() + 1):
        walk(free.Value(i), TopLoc_Location())
    out["__dup__"] = dup
    return out


@functools.lru_cache(None)
def drive(name="drive_asm1021"):
    """Bodies of an assembly STEP in the design frame."""
    raw = read_asm(STEP + f"winch_gear3_{name}.step")
    return {k: shift_design(v) for k, v in raw.items() if k != "__dup__"}


def line_hits(shape, p0, d, t0, t1):
    lin = gp_Lin(gp_Pnt(*p0), gp_Dir(*d))
    ins = IntCurvesFace_ShapeIntersector()
    ins.Load(shape.wrapped, 1e-7)
    ins.Perform(lin, t0, t1)
    ts = sorted(ins.WParameter(i) for i in range(1, ins.NbPnt() + 1))
    mer = []
    for t in ts:
        if not mer or t - mer[-1] > 1e-6:
            mer.append(t)
    return mer


def is_inside(shape, p):
    return BRepClass3d_SolidClassifier(shape.wrapped, gp_Pnt(*p), 1e-7).State() == TopAbs_IN


def material(shape, p0, d, t0, t1):
    """Intervals (t_a, t_b) of material along the line p0 + t d."""
    pts = [t0] + line_hits(shape, p0, d, t0, t1) + [t1]
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        if b - a < 1e-6:
            continue
        m = 0.5 * (a + b)
        if is_inside(shape, [p0[i] + m * d[i] for i in range(3)]):
            if out and abs(a - out[-1][1]) < 1e-5:
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
    return out


def ring_y(r0, r1, y0, y1, x=0.0, z=0.0):
    """Annulus around an axis parallel to +y through (x, z)."""
    o = cq.Solid.makeCylinder(r1, y1 - y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))
    i = cq.Solid.makeCylinder(r0, y1 - y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))
    return cut(o, i)


def cyl_faces(shape):
    out = []
    for f in shape.Faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() == GeomAbs_Cylinder:
            cy = ad.Cylinder()
            ax = cy.Axis()
            bb = f.BoundingBox()
            out.append(dict(r=cy.Radius(), loc=np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()]),
                            dir=np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()]),
                            bb=np.array([bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax]), face=f))
    return out


def plane_faces(shape):
    out = []
    for f in shape.Faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() == GeomAbs_Plane:
            n = f.normalAt()
            bb = f.BoundingBox()
            out.append(dict(n=np.array([n.x, n.y, n.z]), loc=np.array([ad.Plane().Location().X(), ad.Plane().Location().Y(), ad.Plane().Location().Z()]),
                            bb=np.array([bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax]), area=f.Area()))
    return out


def read_stl(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    assert 84 + 50 * n == len(data), "binary STL expected"
    arr = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)
    return arr["v"].astype(np.float64)


def mesh_volume(tri):
    return float(np.sum(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2]))) / 6.0)


def mesh_open_edges(tri):
    cnt = Counter()
    key = lambda p: tuple(np.round(p, 4))  # noqa: E731
    for t in tri:
        k = [key(p) for p in t]
        for i in range(3):
            cnt[(k[i], k[(i + 1) % 3])] += 1
    return sum(1 for (a, b), c in cnt.items() if cnt.get((b, a), 0) != c)


@functools.lru_cache(None)
def generator():
    spec = importlib.util.spec_from_file_location("gears_verify", GEARS_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@functools.lru_cache(None)
def part(name):
    s = load_step(STEP + f"winch_gear3_{name}.step").val()
    return s


@functools.lru_cache(None)
def rims():
    b = drive()
    g = common(b["spool_gear54"], ring_y(23.0, 31.0, Y_T0 - 0.01, Y_T1 + 0.01, 0, ZS))      # tooth rim (root 25.75, tip 28.0); windows end at R22.5
    p = common(b["pinion"], ring_y(6.5, 12.0, Y_T0 - 0.01, Y_T1 + 0.01, 0, ZM))             # tooth rim (root 7.75, tip 10.0)
    return g, p


def rot_y(shape, z_axis, deg):
    return shape.rotate(cq.Vector(0, 0, z_axis), cq.Vector(0, 1, z_axis), deg)


def pinion_to_design(shape):
    """pinion18 print frame (axis +z, teeth end on z = 0, print y = design z - ZM) -> design frame."""
    return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90).translate(cq.Vector(0, 20.825, ZM))


# =============================================================================== 1. STEP / STL file integrity
@pytest.mark.parametrize("name", ["spool_gear54", "spacer_near", "magnet_cap", "pinion18"])
def test_01_part_files(name, tmp_path):
    sec = f"1 part {name}"
    p = STEP + f"winch_gear3_{name}.step"
    head = open(p, "r", errors="ignore").read(200000)
    check_true(sec, "STEP length unit", "MILLI METRE", "MILLI METRE" if "SI_UNIT(.MILLI.,.METRE.)" in head else "other", "SI_UNIT(.MILLI.,.METRE.)" in head)
    w = load_step(p)
    s = w.val()
    check_true(sec, "valid BREP (BRepCheck)", True, valid(s), valid(s))
    check_true(sec, "solid count", 1, len(s.Solids()), len(s.Solids()) == 1)
    check_true(sec, "shell count", 1, len(s.Shells()), len(s.Shells()) == 1)
    check_true(sec, "volume > 0", ">0", round(vol(s), 3), vol(s) > 0)
    # round trip: re-export with CadQuery and re-import
    tmp = str(tmp_path / f"verify_rt_{name}.step")
    cq.exporters.export(w, tmp)
    s2 = load_step(tmp).val()
    dv = abs(vol(s2) - vol(s)) / vol(s)
    db = float(np.max(np.abs(tbb(s2) - tbb(s))) / np.max(np.abs(tbb(s))))
    check_le(sec, "STEP round trip: relative volume change", RT_TOL, dv)
    check_le(sec, "STEP round trip: relative bbox change", RT_TOL, db)
    # STL
    tri = read_stl(STL + f"winch_gear3_{name}.stl")
    check_true(sec, "STL watertight (open edges)", 0, mesh_open_edges(tri), mesh_open_edges(tri) == 0)
    dvs = abs(mesh_volume(tri) - vol(s)) / vol(s)
    check_le(sec, "STL volume vs STEP (relative)", RT_TOL, dvs)
    tb = np.array([tri[:, :, 0].min(), tri[:, :, 0].max(), tri[:, :, 1].min(), tri[:, :, 1].max(), tri[:, :, 2].min(), tri[:, :, 2].max()])
    check_le(sec, "STL bbox vs STEP (max abs, mm)", 0.01, float(np.max(np.abs(tb - tbb(s)))))
    check(sec, "print frame: bed face at z = 0 (STEP z min)", 0.0, tbb(s)[4], 1e-6)


@pytest.mark.parametrize("name,want", [("drive_asm1021", DRIVE_NAMES), ("drive_with_slipin_asm1021", DRIVE_NAMES + ["slipin_mount", "wall_mount"]),
                                       ("gears_asm1021", GEARS_NAMES)])
def test_02_assembly_files(name, want, tmp_path):
    sec = f"1 assembly {name}"
    path = STEP + f"winch_gear3_{name}.step"
    raw = read_asm(path)
    names = [k for k in raw if k != "__dup__"]
    check_true(sec, "named bodies (spec section 5 list; gears file: pinion + spool_gear54)", len(want), len(names), sorted(names) == sorted(want))
    check_true(sec, "duplicate names", 0, len(raw["__dup__"]), not raw["__dup__"])
    allsol = load_step(path).solids().vals()
    check_true(sec, "total solids in file", len(want), len(allsol), len(allsol) == len(want))
    check_true(sec, "no stale revision-A body names (spool_gear60, pinion20)", "none", [k for k in names if k in ("spool_gear60", "pinion20")] or "none", not any(k in ("spool_gear60", "pinion20") for k in names))
    bad = [k for k in names if not (len(raw[k].Solids()) == 1 and len(raw[k].Shells()) == 1 and valid(raw[k]) and vol(raw[k]) > 0)]
    check_true(sec, "every body: one valid solid, one shell, V > 0 (no disconnected pieces)", "none bad", bad or "none bad", not bad)
    # round trip: write a named assembly with CadQuery, read it back with XCAF
    asm = cq.Assembly(name="rt")
    for k in names:
        asm.add(raw[k], name=k)
    tmp = str(tmp_path / f"verify_rt_{name}.step")
    asm.export(tmp)
    raw2 = read_asm(tmp)
    check_true(sec, "round trip keeps the names", "same set", "same" if set(raw2) - {"__dup__"} == set(names) else "differ", set(raw2) - {"__dup__"} == set(names))
    wv = max(abs(vol(raw2[k]) - vol(raw[k])) / vol(raw[k]) for k in names)
    wb = max(float(np.max(np.abs(tbb(raw2[k]) - tbb(raw[k]))) / np.max(np.abs(tbb(raw[k])))) for k in names)
    tot1, tot2 = sum(vol(raw[k]) for k in names), sum(vol(raw2[k]) for k in names)
    check_le(sec, "round trip: worst per-body relative volume change", RT_TOL, wv)
    check_le(sec, "round trip: worst per-body relative bbox change", RT_TOL, wb)
    check_le(sec, "round trip: total volume relative change", RT_TOL, abs(tot2 - tot1) / tot1)
    bbs = np.array([tbb(raw[k]) for k in names])
    bbs2 = np.array([tbb(raw2[k]) for k in names])
    mn, mx = bbs[:, 0::2].min(0), bbs[:, 1::2].max(0)
    mn2, mx2 = bbs2[:, 0::2].min(0), bbs2[:, 1::2].max(0)
    check_le(sec, "round trip: assembly bbox change (mm)", 0.01, float(max(np.abs(mn - mn2).max(), np.abs(mx - mx2).max())))


def test_03_assembly_frame_and_unmodified_references():
    sec = "1 frame / references"
    b = read_asm(STEP + "winch_gear3_drive_asm1021.step")
    # fin == existing export, in place
    fin_ref = list(read_asm(STEP + "heat_fin1021_1p8_asm1021.step").values())[0]
    check(sec, "fin volume equals exports/step/heat_fin1021_1p8_asm1021.step", vol(fin_ref), vol(b["fin"]), 1e-3)
    check_le(sec, "fin bbox vs existing export (mm)", 1e-4, float(np.max(np.abs(tbb(fin_ref) - tbb(b["fin"])))))
    # motor bodies == existing nema17_thermal export, except the shaft which carries the D-flat
    mot = read_asm(STEP + "nema17_thermal_fin1p8_asm1021.step")
    for k in ["front_cap", "stator", "winding", "rear_cap", "connector"]:
        check(sec, f"motor_{k} volume equals nema17_thermal export", vol(mot[k]), vol(b["motor_" + k]), 1e-3)
        check_le(sec, f"motor_{k} bbox vs existing export (mm)", 1e-4, float(np.max(np.abs(tbb(mot[k]) - tbb(b["motor_" + k])))))
    # D-flat volume: circular segment R 2.5, depth 0.5, length 22 (boss end y -1.175 to shaft end 20.825)
    r, h = 2.5, 0.5
    seg = r * r * math.acos((r - h) / r) - (r - h) * math.sqrt(2 * r * h - h * h)
    check(sec, "motor_shaft D-flat removed volume (circular segment x 22 mm)", seg * 22.0, vol(mot["shaft"]) - vol(b["motor_shaft"]), 0.05)
    d = drive()
    ms = d["motor_shaft"]
    flats = [p for p in plane_faces(ms) if abs(p["n"][2] - 1) < 1e-6 and p["area"] > 10]
    check_true(sec, "D-flat on +z of the motor shaft", "plane z=4.64 (axis + 2.0)", [round(float(p["loc"][2]), 3) for p in flats],
               len(flats) == 1 and abs(flats[0]["loc"][2] - 4.64) < POS_TOL)
    check(sec, "motor shaft end y (spec 20.825)", 20.825, tbb(ms)[3], POS_TOL)
    # Jasper's slide-in and wall mount are unchanged and in place (same absolute coordinates as the original SolidWorks assembly)
    w = read_asm(STEP + "winch_gear3_drive_with_slipin_asm1021.step")
    sw = read_asm(SW_ASSEMBLY)
    for k, ko in [("slipin_mount", "Slipin_mount_piecev3"), ("wall_mount", "Wall_Mount_v3")]:
        check(sec, f"{k} volume equals the original SolidWorks assembly part", vol(sw[ko]), vol(w[k]), 0.01)
        check_le(sec, f"{k} bbox vs original (mm, absolute coordinates: confirms offset O)", 1e-3, float(np.max(np.abs(tbb(sw[ko]) - tbb(w[k])))))
        check_same_solid(sec, f"{k} equals the original SolidWorks part in place (volume, area, centre of mass, inertia; absolute coordinates)", w[k], sw[ko])
    # the drive bodies are identical in both assemblies
    same = all(abs(vol(w[k]) - vol(b[k])) < 1e-6 and np.max(np.abs(tbb(w[k]) - tbb(b[k]))) < 1e-6 for k in DRIVE_NAMES)
    check_true(sec, "drive bodies identical in the two assemblies", True, same, same)
    g = read_asm(STEP + "winch_gear3_gears_asm1021.step")
    for k in GEARS_NAMES:
        check_le(sec, f"gears_asm1021 {k}: bbox vs drive_asm1021 body (mm)", 1e-6, float(np.max(np.abs(tbb(g[k]) - tbb(b[k])))))
        check_same_solid(sec, f"gears_asm1021 {k} equals the drive_asm1021 body (volume, area, centre of mass, inertia; same frame)", g[k], b[k])


def test_04_part_files_equal_assembly_bodies():
    sec = "1 part file == assembly body"
    b = drive()

    def to_station(shape, y0, z0=ZS):
        return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90).translate(cq.Vector(0, y0, z0))   # print frame -> design frame
    for nm, key, y0 in [("spool_gear54", "spool_gear54", 10.825), ("spacer_near", "spacer_near", 5.0), ("magnet_cap", "magnet_cap", 49.3)]:
        st = to_station(part(nm), y0)
        check_same_solid(sec, f"{nm}: part STEP placed in the design frame equals the assembly body (volume, area, centre of mass, inertia)", st, b[key])
        if nm != "spool_gear54":       # the boolean on the 54T spool takes about a minute; the fingerprint above is sufficient
            sd = vol(st) + vol(b[key]) - 2 * cvol(st, b[key])
            check_le(sec, f"{nm}: symmetric difference of part STEP and assembly body (mm3)", 0.01, abs(sd))
    # pinion18.step is a printable part in its print frame: axis +z, teeth end (design y 20.825) on the bed z = 0, hub up to z 21.5;
    # print (x, y, z) -> design (x, 20.825 - z, ZM + y)  (proper rotation: +90 deg about x, then translate)
    st = pinion_to_design(part("pinion18"))
    check_same_solid(sec, "pinion18: print-frame STEP placed in the design frame equals the assembly pinion (volume, area, centre of mass, inertia)", st, b["pinion"])
    check(sec, "pinion18: volume equals the assembly pinion", vol(b["pinion"]), vol(part("pinion18")), 1e-6)
    # negative control: the fingerprint must see the spool turned 0.5 deg alone
    dv, da, dc, di = inv_diff(rot_y(b["spool_gear54"], ZS, 0.5), b["spool_gear54"])
    check_true(sec, "negative control: spool turned 0.5 deg alone is detected by the fingerprint", "dCOM > 1e-5 or dI > 1e-7", f"dCOM {dc:.1e}, dI {di:.1e}", dc > 1e-5 or di > 1e-7)


def test_04b_pinion18_print_frame():
    sec = "1 part pinion18 (print frame)"
    p = part("pinion18")
    bb = tbb(p)
    check(sec, "bed: z min = teeth end face (design y 20.825)", 0.0, bb[4], POS_TOL)
    check(sec, "top: z max = hub end (design y -0.675): 20.825 + 0.675 = 21.5", 21.5, bb[5], POS_TOL)
    check(sec, "tip diameter (bbox y = a tooth tip on the print y axis): O20", 20.0, bb[3] - bb[2], POS_TOL)
    txt = open(STEP + "winch_gear3_pinion18.step", "r", errors="ignore").read(60000)
    check_true(sec, "no stale name pinion20 in the file", "absent", "present" if "pinion20" in txt else "absent", "pinion20" not in txt)
    bed = [q for q in plane_faces(p) if abs(q["n"][2] + 1) < 1e-6 and abs(q["loc"][2]) < 1e-6]
    check_true(sec, "bed face: one planar face at z = 0 facing down (teeth end, chamfered outline)", 1, len(bed), len(bed) == 1)
    # outline of the bed face reaches R 9.7 at tooth tips (tip 10 minus the 0.3 x 45 deg chamfer)
    if bed:
        rec(sec, "bed contact area (mm2, info)", "-", f"{bed[0]['area']:.1f}", "-", True)
        bbf = bed[0]["bb"]
        check(sec, "bed face outline: largest extent along the tooth-tip axis (print y), R 9.7 each side", 19.4, bbf[3] - bbf[2], 0.01)
    # downward-facing planar faces above the bed (need supports when printed this way)
    over = [(round(float(q["loc"][2]), 3), round(q["area"], 2)) for q in plane_faces(p) if abs(q["n"][2] + 1) < 1e-6 and q["loc"][2] > 1e-3]
    rec(sec, "downward planar faces above the bed (z, area) - the pocket roof is a cylinder (bridge), the hub-to-teeth step is the only shelf", "info", over, "-", True)
    # orientation of the features in the print frame: flat and pocket open toward print +y (= design +z)
    iv = material(p, (0, 0, 17.0), (0, 1, 0), 0, 10)
    check_true(sec, "D-flat toward print +y: material starts at 2.15 along +y at hub height z 17", "(2.15, 7.0)", [(round(a_, 3), round(b_, 3)) for a_, b_ in iv],
               len(iv) == 1 and abs(iv[0][0] - BORE_FLAT) < 1e-3 and abs(iv[0][1] - 7.0) < 1e-3)
    iv = material(p, (0, 0, 17.0), (0, -1, 0), 0, 10)
    check_true(sec, "round side along print -y: material [2.65, 7.0]", "(2.65, 7.0)", [(round(a_, 3), round(b_, 3)) for a_, b_ in iv],
               len(iv) == 1 and abs(iv[0][0] - BORE_R) < 1e-3 and abs(iv[0][1] - 7.0) < 1e-3)


def test_04c_stale_files_gone():
    sec = "1 stale revision-A files"
    stale = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")]
        for f in files:
            if "gear60" in f or "pinion20" in f:
                stale.append(os.path.relpath(os.path.join(root, f), REPO))
    check_true(sec, "no file named *gear60* or *pinion20* anywhere in the repository (exports, renders, cad, step, stl)", "none", stale or "none", not stale)
    want_step = {"winch_gear3_drive_asm1021.step", "winch_gear3_drive_with_slipin_asm1021.step", "winch_gear3_gears_asm1021.step", "winch_gear3_magnet_cap.step",
                 "winch_gear3_pinion18.step", "winch_gear3_spacer_near.step", "winch_gear3_spool_gear54.step"}
    got_step = {f for f in os.listdir(STEP) if f.startswith("winch_gear3_")}
    check_true(sec, "exports/step/winch_gear3_* is exactly the 7 expected files (pinion18 is the single pinion file)", sorted(want_step), sorted(got_step), got_step == want_step)
    want_stl = {"winch_gear3_magnet_cap.stl", "winch_gear3_pinion18.stl", "winch_gear3_spacer_near.stl", "winch_gear3_spool_gear54.stl"}
    got_stl = {f for f in os.listdir(STL) if f.startswith("winch_gear3_")}
    check_true(sec, "exports/stl/winch_gear3_* is exactly the 4 printable parts (spool, spacer, cap, pinion)", sorted(want_stl), sorted(got_stl), got_stl == want_stl)


# =============================================================================== 2. gear stage
def test_05_gear_teeth_diameters_axes():
    sec = "2 gear stage"
    b = drive()
    g_rim, p_rim = rims()
    ng = len(common(g_rim, ring_y(RG_PITCH - 0.1, RG_PITCH + 0.1, 10.9, 20.7, 0, ZS)).Solids())
    npn = len(common(p_rim, ring_y(RP_PITCH - 0.1, RP_PITCH + 0.1, 10.9, 20.7, 0, ZM)).Solids())
    check_true(sec, "gear tooth count (disjoint tooth sections at the pitch ring R27)", NG, ng, ng == NG)
    check_true(sec, "pinion tooth count (disjoint tooth sections at the pitch ring R9)", NP, npn, npn == NP)
    check(sec, "ratio", 3.0, ng / npn, 1e-9)

    def coax(shape, az):
        g = {}
        for c in cyl_faces(shape):
            if abs(c["dir"][1]) > 0.999 and math.hypot(c["loc"][0], c["loc"][2] - az) < 0.01:
                g.setdefault(round(c["r"], 3), []).append(c)
        return g
    gg, gp = coax(b["spool_gear54"], ZS), coax(b["pinion"], ZM)
    gp = {r: v for r, v in gp.items() if r > 7.5}                  # drop the D-bore (R2.65) and the hub (R7.0); keep the tooth cylinders
    check_true(sec, f"gear: tip faces (R {RG_TIP}) / root faces (R {RG_ROOT})", "54 / 54", f"{len(gg.get(RG_TIP, []))} / {len(gg.get(RG_ROOT, []))}",
               len(gg.get(RG_TIP, [])) == NG and len(gg.get(RG_ROOT, [])) == NG)
    check_true(sec, f"pinion: tip faces (R {RP_TIP}) / root faces (R {RP_ROOT})", "18 / 18", f"{len(gp.get(RP_TIP, []))} / {len(gp.get(RP_ROOT, []))}",
               len(gp.get(RP_TIP, [])) == NP and len(gp.get(RP_ROOT, [])) == NP)
    check(sec, "gear tip diameter (spec O56), from the tip faces", 2 * RG_TIP, 2 * max(gg), POS_TOL)
    check(sec, "gear root diameter (spec root R 25.75 = 51.5), from the root faces", 2 * RG_ROOT, 2 * min(r for r in gg if r > 20), POS_TOL)
    check(sec, "pinion tip diameter (spec O20), from the tip faces", 2 * RP_TIP, 2 * max(gp), POS_TOL)
    check(sec, "pinion root diameter (generator root R 7.75 = 15.5), from the root faces", 2 * RP_ROOT, 2 * min(gp), POS_TOL)
    # axes from the bore cylinders
    pb = [c for c in cyl_faces(b["pinion"]) if abs(c["r"] - BORE_R) < 1e-4 and abs(c["dir"][1]) > 0.999][0]
    gb = [c for c in cyl_faces(b["spool_gear54"]) if abs(c["r"] - 3.5) < 1e-4][0]
    ms = [c for c in cyl_faces(b["motor_shaft"]) if abs(c["r"] - 2.5) < 1e-4][0]
    sh = [c for c in cyl_faces(b["shaft"]) if abs(c["r"] - 3.5) < 1e-4][0]
    check(sec, "pinion bore axis x", 0.0, pb["loc"][0], POS_TOL)
    check(sec, "pinion bore axis z", ZM, pb["loc"][2], POS_TOL)
    check(sec, "motor shaft axis z", ZM, ms["loc"][2], POS_TOL)
    check(sec, "spool bore axis x", 0.0, gb["loc"][0], POS_TOL)
    check(sec, "spool bore axis z (2.64 - 36.30 = -33.66)", -33.66, gb["loc"][2], POS_TOL)
    check(sec, "shaft axis z (-33.66)", -33.66, sh["loc"][2], POS_TOL)
    check(sec, "shaft axis x", 0.0, sh["loc"][0], POS_TOL)
    check(sec, "centre distance pinion bore axis to spool bore axis (36.30)", CD, abs(pb["loc"][2] - gb["loc"][2]), 0.001)
    check(sec, "centre distance minus nominal m (z1 + z2) / 2 = backlash allowance 0.30 (revision C)", CD_ALLOW, abs(pb["loc"][2] - gb["loc"][2]) - MOD * (NP + NG) / 2.0, 0.001)
    check(sec, "centre distance, from the shaft axes (motor shaft to spool shaft)", CD, abs(ms["loc"][2] - sh["loc"][2]), 0.001)
    # tooth faces and shaft end
    ysp = [c for c in cyl_faces(b["spool_gear54"]) if abs(c["r"] - RG_TIP) < 1e-3]
    ypi = [c for c in cyl_faces(b["pinion"]) if abs(c["r"] - RP_TIP) < 1e-3]
    check(sec, "pinion tip faces y max (teeth end 20.825 minus the 0.3 chamfer = 20.525)", 20.825 - CH, max(c["bb"][3] for c in ypi), POS_TOL)
    check(sec, "pinion tip faces y min (10.825)", 10.825, min(c["bb"][2] for c in ypi), POS_TOL)
    check(sec, "gear tip faces y max (20.825)", 20.825, max(c["bb"][3] for c in ysp), POS_TOL)
    check(sec, "gear near face y (bed face, teeth start 10.825)", 10.825, tbb(b["spool_gear54"])[2], POS_TOL)
    check(sec, "tip faces of the gear start 0.3 above the bed face (chamfer)", 11.125, min(c["bb"][2] for c in ysp), POS_TOL)
    check(sec, "pinion tip-face width (10.0 face minus the 0.3 chamfer)", 10.0 - CH, max(c["bb"][3] for c in ypi) - min(c["bb"][2] for c in ypi), POS_TOL)
    check(sec, "pinion teeth end face y (shaft end 20.825)", 20.825, tbb(common(b["pinion"], ring_y(6.5, 12.0, 10.9, 21.0, 0, ZM)))[3], POS_TOL)
    # phasing: a gear tooth SPACE on the line of centres, a pinion tooth on it
    gm = material(b["spool_gear54"], (0, 15.825, ZS), (0, 0, 1), 0, 40)
    pm = material(b["pinion"], (0, 15.825, ZM), (0, 0, -1), 0, 40)
    check(sec, "gear radius on the line of centres (tooth space -> root R 25.75)", RG_ROOT, gm[-1][1], POS_TOL)
    check(sec, "pinion radius on the line of centres (tooth -> tip R 10.0)", RP_TIP, pm[-1][1], POS_TOL)
    # the next teeth on both sides: gear tooth centres at +-half a pitch (3.333 deg) from the line of centres, pinion spaces at +-half a pitch (10 deg)
    for sgn in (+1, -1):
        a = math.radians(sgn * 180.0 / NG)
        d = (math.sin(a), 0.0, math.cos(a))
        gt = material(b["spool_gear54"], (0, 15.825, ZS), d, 0, 40)
        check(sec, f"gear radius {sgn * 180.0 / NG:+.3f} deg off the line of centres (next tooth centre -> tip R 28.0)", RG_TIP, gt[-1][1], POS_TOL)
        a = math.radians(sgn * 180.0 / NP)
        d = (math.sin(a), 0.0, -math.cos(a))
        pt = material(b["pinion"], (0, 15.825, ZM), d, 0, 40)
        check(sec, f"pinion radius {sgn * 180.0 / NP:+.3f} deg off the line of centres (next tooth space -> root R 7.75)", RP_ROOT, pt[-1][1], POS_TOL)

    # tooth thickness at the pitch circle (ring volume / ring cross-section area)
    def thick(shape, az, y0, y1, rr):
        sols = common(shape, ring_y(rr - 0.1, rr + 0.1, y0, y1, 0, az)).Solids()
        return float(np.mean([vol(s) for s in sols]) / (0.2 * (y1 - y0)))
    tg, tp = thick(g_rim, ZS, 11.3, 20.7, RG_PITCH), thick(p_rim, ZM, 10.9, 20.4, RP_PITCH)
    check(sec, "gear tooth thickness at pitch circle (pi/2 - 0.10 thinning)", math.pi / 2 - 0.10, tg, 0.005)
    check(sec, "pinion tooth thickness at pitch circle (pi/2 - 0.10 thinning, revision C printed pinion)", math.pi / 2 - THIN, tp, 0.005)


def test_06_gear_matches_repo_generator():
    sec = "2 gear stage"
    G = generator()
    b = drive()

    def station(shape, y0, z0):
        return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90).translate(cq.Vector(0, y0, z0))
    # tooth phase read from the STEP tip faces, then rebuilt with the repo generator (module 1, 20 deg, thinning 0.10 both, root blend 0.40)
    for nm, key, n, R, az, thin in [("gear 54T", "spool_gear54", NG, RG_TIP, ZS, THIN), ("pinion 18T (revision C: thinned 0.10)", "pinion", NP, RP_TIP, ZM, THIN)]:
        ang = sorted(math.degrees(math.atan2(c["face"].Center().z - az, c["face"].Center().x)) for c in cyl_faces(b[key]) if abs(c["r"] - R) < 1e-3)
        phase_axial = (-ang[0]) % (360.0 / n)                        # axial-frame angle = - station angle (local y = -station z)
        ref = station(G.gear(n, MOD, 10.0, phase=phase_axial, reduction=thin, root_radius=0.40).val(), 10.825, az)
        y0 = 11.3 if n == NG else 10.9
        zone = ring_y(23.0 if n == NG else 6.5, 40.0, y0, 20.7 if n == NG else 20.45, 0, az)       # pinion: stop before its 0.3 chamfer zone (y > 20.525)
        a, c = common(b[key], zone), common(ref, zone)
        sd = abs(vol(a) + vol(c) - 2 * cvol(a, c))
        check_le(sec, f"{nm}: rim solid (STEP) vs repo generator rebuilt independently, symmetric difference (mm3)", 0.01, sd)
        rec(sec, f"{nm}: measured tooth phase (axial-frame angle of the first tooth centre, deg; info)", "info", round(phase_axial, 4), "-", True)
    # tooth pitch of the gear: 360 / 54
    ang = sorted(math.degrees(math.atan2(c["face"].Center().z - ZS, c["face"].Center().x)) for c in cyl_faces(b["spool_gear54"]) if abs(c["r"] - RG_TIP) < 1e-3)
    check(sec, "gear tooth pitch (deg) = 360 / 54", 360.0 / NG, float(np.mean(np.diff(ang))), 1e-6)
    ang = sorted(math.degrees(math.atan2(c["face"].Center().z - ZM, c["face"].Center().x)) for c in cyl_faces(b["pinion"]) if abs(c["r"] - RP_TIP) < 1e-3)
    check(sec, "pinion tooth pitch (deg) = 360 / 18", 360.0 / NP, float(np.mean(np.diff(ang))), 1e-6)


POSES = [0.0, 20.0 / 6, 2 * 20.0 / 6, 3 * 20.0 / 6, 4 * 20.0 / 6, 5 * 20.0 / 6, 20.0]      # one pinion pitch (20 deg), gear turns -theta/3


def test_07_mesh_poses():
    sec = "2 mesh"
    g_rim, p_rim = rims()
    worst_d, worst_v = 1e9, 0.0
    rows = []
    for th in POSES:                                       # pinion pitch = 20 deg; gear rotates -th/3
        p = rot_y(p_rim, ZM, th)
        g = rot_y(g_rim, ZS, -th / 3.0)
        v = cvol(p, g)
        d, _ = mindist(p, g)
        rows.append((th, v, d))
        worst_d, worst_v = min(worst_d, d), max(worst_v, v)
    check_le(sec, "pinion/gear overlap volume over 7 poses 0..20 deg = one pinion pitch (mm3, max)", 0.001, worst_v)
    check_ge(sec, "minimum flank-to-flank distance over 7 poses (mm, positive)", 0.05, worst_d)
    rec(sec, "min distance per pose (deg: mm)", "all > 0", "; ".join(f"{t:.3f}:{d:.4f}" for t, v, d in rows), "-", True)
    rec(sec, "overlap volume per pose (deg: mm3)", "all 0", "; ".join(f"{t:.3f}:{v:.5f}" for t, v, d in rows), "-", True)
    # negative control: the same test must see a collision when the gear is turned alone by 0.5 deg
    ctl = cvol(p_rim, rot_y(g_rim, ZS, 1.0))
    check_true(sec, "negative control (gear turned 1.0 deg alone; backlash is now +-0.45 deg at the gear) detects overlap", "> 0.1 mm3", round(ctl, 3), ctl > 0.1)
    # which features: tip-to-root clearance
    gg = {round(c["r"], 3) for c in cyl_faces(drive()["spool_gear54"]) if abs(c["dir"][1]) > 0.999 and math.hypot(c["loc"][0], c["loc"][2] - ZS) < 0.01}
    pg = {round(c["r"], 3) for c in cyl_faces(drive()["pinion"]) if abs(c["dir"][1]) > 0.999 and math.hypot(c["loc"][0], c["loc"][2] - ZM) < 0.01 and c["r"] > 7.5}
    cd = abs([c for c in cyl_faces(drive()["pinion"]) if abs(c["r"] - BORE_R) < 1e-4 and abs(c["dir"][1]) > 0.999][0]["loc"][2] - [c for c in cyl_faces(drive()["spool_gear54"]) if abs(c["r"] - 3.5) < 1e-4][0]["loc"][2])
    check(sec, "tip-to-root clearance, measured (CD - R_tip_gear - R_root_pinion = 36.30 - 28.0 - 7.75)", CD - 28.0 - 7.75, cd - max(gg) - min(pg), 0.002)
    check(sec, "tip-to-root clearance, other way (CD - R_tip_pinion - R_root_gear = 36.30 - 10.0 - 25.75)", CD - 10.0 - 25.75, cd - max(pg) - min(r for r in gg if r > 20), 0.002)


def test_08_backlash_bisect():
    sec = "2 mesh"
    g_rim, p_rim = rims()

    def ov(delta):
        return cvol(rot_y(p_rim, ZM, delta), g_rim)

    def find(sign):
        lo, hi = 0.0, 3.0
        for _ in range(12):
            mid = 0.5 * (lo + hi)
            if ov(sign * mid) > 1e-4:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)
    dp, dm = find(+1), find(-1)
    tot = dp + dm
    # analytic transverse backlash: 2 x 0.30 x tan(20 deg) = 0.2184 (centre-distance allowance) + 0.10 (gear thinning) + 0.10 (pinion thinning) = 0.4184 mm
    # at the pinion pitch circle R9 (spec: "about 0.42")
    an = math.degrees((2 * CD_ALLOW * math.tan(math.radians(20)) + 2 * THIN) / RP_PITCH)
    check(sec, f"free pinion rotation, gear fixed: total (deg); analytic 0.4184 mm / 9 mm pitch radius = {an:.3f} deg", an, tot, 0.06)
    check(sec, "backlash transverse at the pinion pitch circle (mm), spec 'about 0.42'", 0.42, math.radians(tot) * RP_PITCH, 0.02)
    check(sec, "backlash symmetric about the reference pose (|+ - -|, deg)", 0.0, abs(dp - dm), 0.02)
    rec(sec, "backlash transverse at the pinion pitch circle (mm); at the drum (cable mm)", "0.418 / 0.12",
        f"{math.radians(tot) * RP_PITCH:.4f} / {math.radians(tot / 3) * 7.5:.4f}", "-", True)
    check_ge(sec, "free pinion rotation is positive both ways (no jam), min of the two halves (deg)", 0.3, min(dp, dm))


# =============================================================================== 3. spool_gear54 part (print frame)
def ray(s, ang, z, t1=40.0):
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0)
    return material(s, (0, 0, z), d, 0, t1)


@functools.lru_cache(None)
def gear_phase_print():
    """(phase, spread): angle (print frame, deg, in [0, 360/54)) of a tooth centre and the spread of all 54 tip-face centres about it,
    both from the tip faces of the exported spool_gear54 part."""
    s = part("spool_gear54")
    angs = [math.degrees(math.atan2(c["face"].Center().y, c["face"].Center().x))
            for c in cyl_faces(s) if abs(c["r"] - RG_TIP) < 1e-3 and abs(c["dir"][2]) > 0.999]
    pitch = 360.0 / NG
    a0 = angs[0]
    dev = [((a - a0 + pitch / 2) % pitch) - pitch / 2 for a in angs]
    return (a0 + float(np.mean(dev))) % pitch, max(dev) - min(dev)


def expected_outer(phi_deg):
    """Outer radius of the gear along print-frame angle phi: tip on a tooth centre, root on a tooth-space centre, else None (flank)."""
    ph, _ = gear_phase_print()
    pitch = 360.0 / NG
    d = ((phi_deg - ph + pitch / 2) % pitch) - pitch / 2          # signed distance to the nearest tooth centre
    if abs(d) < 0.01:
        return RG_TIP
    if abs(abs(d) - pitch / 2) < 0.01:
        return RG_ROOT
    return None


def test_09_spool_sections():
    sec = "3 spool_gear54"
    s = part("spool_gear54")
    bb = tbb(s)
    check(sec, "part starts (z 0 = design y 10.825)", 0.0, bb[4], 1e-6)
    check(sec, "part ends (design y 44.0 - 10.825 = 33.175)", 33.175, bb[5], 1e-6)
    check_true(sec, "bbox x,y within +-28.0 (tip R28; no tooth on the axis)", "<= 28.0", f"{bb[1]:.4f} / {bb[3]:.4f}", 27.9 < bb[1] <= 28.0 + 1e-6 and 27.9 < bb[3] <= 28.0 + 1e-6)
    ph, spread = gear_phase_print()
    check_le(sec, "tooth centres of all 54 teeth on one uniform pitch (spread of the tip-face centres about the phase, deg)", 1e-6, spread)
    rec(sec, "tooth-centre phase in the print frame (deg; info)", "info", round(ph, 6), "-", True)
    # window geometry first (angles of the six window axes, measured)
    wf = [c for c in cyl_faces(s) if abs(c["r"] - WIN_D / 2) < 1e-4 and abs(c["dir"][2]) > 0.999]
    check_true(sec, "windows: count, diameter 10.0 (R 5.0)", "6 x R5.0", len(wf), len(wf) == 6)
    wang = sorted(math.degrees(math.atan2(c["loc"][1], c["loc"][0])) % 360.0 for c in wf)
    w_steps = [(wang[(k + 1) % 6] - wang[k]) % 360.0 for k in range(6)]
    check_true(sec, "windows: equally spaced 60 deg", "6 x 60", [round(x, 4) for x in w_steps], all(abs(x - 60.0) < 1e-3 for x in w_steps))
    rec(sec, "windows: angle of the first window axis (print frame, deg; info)", "info", round(wang[0], 4), "-", True)
    w_out = max(math.hypot(c["loc"][0], c["loc"][1]) + c["r"] for c in wf)
    w_in = min(math.hypot(c["loc"][0], c["loc"][1]) - c["r"] for c in wf)
    root_r = min(c["r"] for c in cyl_faces(s) if c["r"] > 20)
    drum_r = [c["r"] for c in cyl_faces(s) if abs(c["bb"][4] - 10.0) < 1e-4 and abs(c["bb"][5] - 26.0) < 1e-4][0]
    check(sec, "windows: pitch radius (max |dist of axis from spool axis - 17.5|)", 0.0, max(abs(math.hypot(c["loc"][0], c["loc"][1]) - WIN_R) for c in wf), 1e-4)
    check(sec, "windows: outer edge radius (spec R22.5)", 22.5, w_out, 1e-4)
    check(sec, "windows: inner edge radius (spec R12.5)", 12.5, w_in, 1e-4)
    check_ge(sec, "windows: inner edge radius >= 12 (outside the 10 mm full-spool line radius)", 12.0, w_in)
    check(sec, "windows: inner edge outside the 10 mm line radius (spec 2.5)", 2.5, w_in - 10.0, 1e-4)
    check(sec, "windows: rim below the root, measured (spec 3.25)", 3.25, root_r - w_out, 1e-4)
    check_ge(sec, "windows: rim below the root (mm, spec >= 3.0)", 3.0, root_r - w_out)
    check_ge(sec, "windows: web from the drum core to the window inner edge (mm, WG3_WEB_MIN 2)", 2.0, w_in - drum_r)
    check(sec, "windows: z extent (gear 10 mm thick)", 10.0, max(c["bb"][5] for c in wf) - min(c["bb"][4] for c in wf), 1e-4)
    # radial profile at z = 5 (gear), windows: window axes on tooth centres/spaces as measured; material intervals
    for k, a in enumerate(wang):
        iv = ray(s, a, 5.0)
        eo = expected_outer(a)
        ok = len(iv) == 2 and abs(iv[0][0] - 3.5) < 1e-3 and abs(iv[0][1] - 12.5) < 1e-3 and abs(iv[1][0] - 22.5) < 1e-3 and RG_ROOT - 1e-3 <= iv[1][1] <= RG_TIP + 1e-3
        if eo is not None:
            ok = ok and abs(iv[1][1] - eo) < 1e-3
        check_true(sec, f"window along {a:.2f} deg: material [3.5,12.5] [22.5,{eo if eo else 'flank'}]", f"[(3.5,12.5),(22.5,{eo})]", [(round(x, 3), round(y, 3)) for x, y in iv], ok)
    for a0 in wang:
        a = (a0 + 30.0) % 360.0
        iv = ray(s, a, 5.0)
        eo = expected_outer(a)
        ok = len(iv) == 1 and abs(iv[0][0] - 3.5) < 1e-3 and RG_ROOT - 1e-3 <= iv[0][1] <= RG_TIP + 1e-3 and (eo is None or abs(iv[0][1] - eo) < 1e-3)
        check_true(sec, f"no window along {a:.2f} deg (spoke): solid [3.5, {eo if eo else 'flank'}]", f"[(3.5,{eo})]", [(round(x, 3), round(y, 3)) for x, y in iv], ok)
    # the line of centres (print frame 270 deg: station +z) must be a spoke carrying a tooth SPACE (root 25.75)
    iv = ray(s, 270.0, 5.0)
    check_true(sec, "line of centres (print 270 deg = station +z): spoke with the root R25.75 (tooth space facing the pinion)", "[(3.5,25.75)]",
               [(round(x, 3), round(y, 3)) for x, y in iv], len(iv) == 1 and abs(iv[0][1] - RG_ROOT) < 1e-3)
    # axial profile (angle 180 deg is a window axis, but z > 10 is above the gear)
    for z, rout, lab in [(10.5, 7.5, "drum R7.5 starts above the gear"), (18.0, 7.5, "drum R7.5 (y 20.825 to 36.825)"), (25.9, 7.5, "drum R7.5 ends at z 26.0"),
                         (26.1, 18.0, "flange R18 starts z 26.0"), (28.9, 18.0, "flange R18 ends z 29.0"), (29.1, 6.0, "hub R6"), (32.8, 6.0, "hub R6 to z 32.875"),
                         (32.9, 4.5, "land R4.5 (O9)"), (33.1, 4.5, "land R4.5 to the end")]:
        iv = ray(s, 180, z)
        check(sec, f"outer radius at z {z}: {lab}", rout, iv[-1][1], 1e-3)
        check(sec, f"bore radius at z {z} (O7.00 through)", 3.5, iv[0][0], 1e-3)
    pl = {(round(p["loc"][2], 3), int(round(p["n"][2]))): p["area"] for p in plane_faces(s) if abs(abs(p["n"][2]) - 1) < 1e-6}
    check(sec, "flange inner face z (design y 36.825 = drum end)", 26.0, [k[0] for k in pl if k[1] == -1 and k[0] > 1][0], 1e-4)
    check(sec, "flange inner face annulus area pi(18^2 - 7.5^2): overhang 10.5 mm", math.pi * (18 ** 2 - 7.5 ** 2), pl[(26.0, -1)], 0.05)
    check(sec, "flange outer face z (y 39.825)", 29.0, [k[0] for k in pl if k[1] == 1 and abs(k[0] - 29) < 0.01][0], 1e-4)
    check(sec, "land proud of the hub end (part end z max - hub shoulder z)", 0.3, tbb(s)[5] - [k[0] for k in pl if k[1] == 1 and abs(k[0] - 32.875) < 0.01][0], 1e-4)
    check(sec, "land height measured: hub shoulder z", 32.875, [k[0] for k in pl if k[1] == 1 and abs(k[0] - 32.875) < 0.01][0], 1e-4)
    # bore: one cylinder R3.5 over the whole length
    bores = [c for c in cyl_faces(s) if abs(c["r"] - 3.5) < 1e-4]
    check_true(sec, "bore: one O7.00 through face, full length", "z 0..33.175", (round(bores[0]["bb"][4], 3), round(bores[0]["bb"][5], 3)),
               len(bores) == 1 and abs(bores[0]["bb"][4]) < 1e-4 and abs(bores[0]["bb"][5] - 33.175) < 1e-4)
    check(sec, "bore axis on the part axis (x, y offset)", 0.0, math.hypot(bores[0]["loc"][0], bores[0]["loc"][1]), 1e-4)
    # gear z range and tooth faces
    tips = [c for c in cyl_faces(s) if abs(c["r"] - RG_TIP) < 1e-3]
    check(sec, "gear thickness (tip faces end at z 10.0 = y 20.825)", 10.0, max(c["bb"][5] for c in tips), 1e-4)
    check_true(sec, "tooth tip faces: 54", NG, len(tips), len(tips) == NG)
    check(sec, "drum starts where the gear ends (R7.5 face z min)", 10.0, [c for c in cyl_faces(s) if abs(c["r"] - 7.5) < 1e-4][0]["bb"][4], 1e-4)


def test_10_spool_tieoff():
    sec = "3 spool_gear54 tie-off"
    s = part("spool_gear54")
    hole = [c for c in cyl_faces(s) if abs(c["r"] - 0.7) < 1e-4]
    check_true(sec, "tie-off hole faces (R0.7, Ø1.4)", ">= 1", len(hole), len(hole) >= 1)
    h = hole[0]
    check(sec, "hole axis offset from the spool axis (x)", 5.25, h["loc"][0], 1e-4)
    check(sec, "hole axis z = drum mid-plane (design y 28.825 - 10.825 = 18.0)", 18.0, h["loc"][2], 1e-4)
    check_true(sec, "hole axis direction perpendicular to the spool axis", "dz = 0", round(float(abs(h["dir"][2])), 6), abs(h["dir"][2]) < 1e-6)
    # probes
    def line(p0, d, t0, t1):
        return material(s, p0, d, t0, t1)
    iv = line((5.25, 0, 10.5), (0, 0, 1), 0, 15)       # along the spool axis direction through the hole
    gap = [(iv[i][1] + 10.5, iv[i + 1][0] + 10.5) for i in range(len(iv) - 1)]
    check_true(sec, "hole diameter along z at x 5.25: gap [17.3, 18.7]", "1.4", [(round(a, 3), round(b, 3)) for a, b in gap],
               len(gap) == 1 and abs(gap[0][0] - 17.3) < 1e-3 and abs(gap[0][1] - 18.7) < 1e-3)
    ix = line((0, 0, 18.0), (1, 0, 0), 0, 12)          # radial through the hole at the closest approach (y 0)
    check_true(sec, "ligament to the bore: [3.5, 4.55] material -> 1.05", "1.05", round(ix[0][1] - ix[0][0], 4), abs((ix[0][1] - ix[0][0]) - 1.05) < 2e-3)
    check_true(sec, "ligament to the core surface: [5.95, 7.5] material -> 1.55", "1.55", round(ix[1][1] - ix[1][0], 4), abs((ix[1][1] - ix[1][0]) - 1.55) < 2e-3)
    iy = line((5.25, -9, 18.0), (0, 1, 0), 0, 18)
    check_true(sec, "hole open through the whole core, both ends (no material along the hole axis, y -9..9)", "none", iy, iy == [])
    iy2 = line((5.25, -9, 17.0), (0, 1, 0), 0, 18)
    check_true(sec, "control: same line 1.0 mm below the hole axis crosses the core", "chord 10.71", [(round(a, 2), round(b, 2)) for a, b in iy2],
               len(iy2) == 1 and abs((iy2[0][1] - iy2[0][0]) - 2 * math.sqrt(7.5 ** 2 - 5.25 ** 2)) < 0.01)
    ie = line((0, 5.3, 18.0), (1, 0, 0), 0, 12)        # near the chord end: hole breaks through the winding surface
    check_true(sec, "chord end open on the winding surface (y +5.3: material only to the hole wall 4.55)", "[(0,4.55)]", [(round(a, 3), round(b, 3)) for a, b in ie],
               len(ie) == 1 and abs(ie[0][1] - 4.55) < 2e-3)
    ie2 = line((0, -5.3, 18.0), (1, 0, 0), 0, 12)
    check_true(sec, "chord end open on the winding surface (y -5.3)", "[(0,4.55)]", [(round(a, 3), round(b, 3)) for a, b in ie2], len(ie2) == 1 and abs(ie2[0][1] - 4.55) < 2e-3)
    opp = line((0, 0, 18.0), (-1, 0, 0), 0, 12)
    check_true(sec, "opposite side (-x) of the core is solid [3.5, 7.5]", "[(3.5,7.5)]", [(round(a, 3), round(b, 3)) for a, b in opp], len(opp) == 1 and abs(opp[0][1] - 7.5) < 1e-3)
    # same side/direction as Spool1011 (reference): hole offset on +x, direction along station z
    ref = load_step(os.path.join(REPO, "cad", "reference", "station_1021", "Spool1011.step")).val()
    rh = [c for c in cyl_faces(ref) if abs(c["r"] - 0.7) < 1e-4][0]
    check_true(sec, "Spool1011 reference: hole offset toward +x, axis along station z (as the new part)", "+x, dir z", f"x {rh['loc'][0]:.2f}, dir {np.round(np.abs(rh['dir']), 2)}",
               rh["loc"][0] > 0 and abs(rh["dir"][2]) > 0.99)


def test_11_spool_independent_rebuild_and_chamfer():
    sec = "3 spool_gear54 rebuild"
    G = generator()
    s = part("spool_gear54")

    def cyl(r, z0, z1, x=0.0, y=0.0):
        return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))
    ph, _ = gear_phase_print()
    wf = [c for c in cyl_faces(s) if abs(c["r"] - WIN_D / 2) < 1e-4 and abs(c["dir"][2]) > 0.999]
    w0 = min(math.degrees(math.atan2(c["loc"][1], c["loc"][0])) % 360.0 for c in wf)
    gear = G.gear(NG, MOD, 10.0, phase=ph, reduction=0.10, root_radius=0.40).val()
    ref = gear
    for k in range(6):
        a = math.radians(w0 + 60 * k)
        ref = cut(ref, cyl(WIN_D / 2, -1, 11, WIN_R * math.cos(a), WIN_R * math.sin(a)))
    ref = ref.fuse(cyl(7.5, 9.9, 26.0)).fuse(cyl(18, 26, 29)).fuse(cyl(6.0, 28.9, 32.875)).fuse(cyl(4.5, 32.8, 33.175))
    ref = cut(ref, cyl(3.5, -1, 34))
    ref = cut(ref, cq.Solid.makeCylinder(0.7, 24, cq.Vector(5.25, -12, 18.0), cq.Vector(0, 1, 0))).clean()
    vs, vr = vol(s), vol(ref)
    check_true(sec, "independent rebuild from the spec (generator 54T gear, six O10 windows on R17.5, drum, flange, hub, land, bore, chord hole): one valid solid", True,
               (len(ref.Solids()), valid(ref)), len(ref.Solids()) == 1 and valid(ref))
    cm = cvol(s, ref)
    check_le(sec, "STEP material outside the independent rebuild (mm3)", 0.01, abs(vs - cm))
    chamfer = vr - vs
    # outline perimeter of the 54T section: outer wire of the generator gear's face at z = 0
    bot = [f for f in gear.Faces() if abs(f.Center().z) < 1e-6 and abs(f.normalAt().z + 1) < 1e-6][0]
    per = bot.outerWire().Length()
    check(sec, f"bed-face chamfer: removed volume (rebuild minus STEP) vs perimeter {per:.2f} x 0.3 x 0.3 / 2 (corners ignored)", per * 0.045, chamfer, 0.4)
    # radial extents against z near the bed face (tooth tip direction ph, tooth space ph + 3.333)
    tip_ang, root_ang = ph, ph + 180.0 / NG
    for z in [0.001, 0.1, 0.2, 0.3, 1.0]:
        tip = ray(s, tip_ang, z)[-1][1]
        root = ray(s, root_ang, z)[-1][1]
        check(sec, f"bed-face chamfer: tooth tip radius at z {z} (28.0 - max(0.3 - z, 0))", RG_TIP - max(0.3 - z, 0.0), tip, 0.003)
        check(sec, f"bed-face chamfer: root radius at z {z} (25.75 - max(0.3 - z, 0))", RG_ROOT - max(0.3 - z, 0.0), root, 0.003)
    # windows and bore edges at the bed face are not chamfered (spec: tooth edges only)
    iv = ray(s, w0, 0.001)
    check_true(sec, "bed face: window and bore edges unchamfered (material [3.5,12.5] [22.5,..])", "3.5/12.5/22.5", [(round(a, 3), round(b, 3)) for a, b in iv],
               abs(iv[0][0] - 3.5) < 2e-3 and abs(iv[0][1] - 12.5) < 2e-3 and abs(iv[1][0] - 22.5) < 2e-3)


def test_12_spool_printability():
    sec = "3 spool printability"
    s = part("spool_gear54")
    pl = [p for p in plane_faces(s) if abs(p["n"][2] + 1) < 1e-6]
    bed = [p for p in pl if abs(p["loc"][2]) < 1e-6]
    over = [p for p in pl if p["loc"][2] > 1e-3]
    check_true(sec, "bed face: one planar face at z = 0 facing down", 1, len(bed), len(bed) == 1)
    rec(sec, "bed contact area (mm2)", "-", f"{bed[0]['area']:.1f}", "-", True)
    check_true(sec, "downward-facing planar faces above the bed (need supports): only the flange inner face z 26.0", "1 face at z 26.0, area 841.2",
               [(round(float(p['loc'][2]), 3), round(p['area'], 1)) for p in over], len(over) == 1 and abs(over[0]["loc"][2] - 26.0) < 1e-4)
    tri = read_stl(STL + "winch_gear3_spool_gear54.stl")
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ar = np.linalg.norm(nrm, axis=1) / 2
    nz = nrm[:, 2] / np.linalg.norm(nrm, axis=1)
    zc = tri[:, :, 2].mean(1)
    steep = (nz < -0.73) & (zc > 0.001)                  # clearly beyond the 45 deg chamfer limit (nz -0.707), above the bed
    groups = {}
    for z, a in zip(np.round(zc[steep], 0), ar[steep]):
        groups[float(z)] = groups.get(float(z), 0.0) + float(a)
    rec(sec, "overhangs beyond 45 deg (STL, nz < -0.73), area by z (mm2)", "z 26 flange; z 18-19 tie-off roof", {k: round(v, 1) for k, v in sorted(groups.items())}, "-", True)
    flange = sum(v for k, v in groups.items() if abs(k - 26.0) < 0.6)
    roof = sum(v for k, v in groups.items() if 17.5 < k < 19.6)
    other = sum(v for k, v in groups.items() if not (abs(k - 26.0) < 0.6 or 17.5 < k < 19.6))
    check(sec, "overhang area at the flange inner face (annulus R7.5..R18 = 841.2)", 841.2, flange, 1.0)
    check_le(sec, "tie-off hole roof area (horizontal Ø1.4 hole; bridging) (mm2)", 14.0, roof)
    check_le(sec, "any other steep overhang (mm2)", 0.5, other)


# =============================================================================== 4. spacer, shaft, bearings, cap, magnet, encoder
def test_13_spacer():
    sec = "4 spacer_near"
    s = part("spacer_near")
    bb = tbb(s)
    check(sec, "length (y 5.0 to 10.825)", 5.825, bb[5] - bb[4], 1e-4)
    check(sec, "OD", 10.0, bb[1] - bb[0], 1e-4)
    cf = {round(c["r"], 3): c for c in cyl_faces(s)}
    check_true(sec, "cylinders: R5.0 body, R4.5 lands (both ends), R3.55 bore", "5.0 / 4.5 / 3.55", sorted(cf), set(cf) == {5.0, 4.5, 3.55})
    check(sec, "bore diameter (Ø7.10)", 7.10, 2 * 3.55, 1e-9)
    lands = [c for c in cyl_faces(s) if abs(c["r"] - 4.5) < 1e-4]
    check_true(sec, "two Ø9 lands, one at each end, 0.3 proud", "2 x 0.3", sorted(round(float(c["bb"][5] - c["bb"][4]), 3) for c in lands),
               len(lands) == 2 and all(abs((c["bb"][5] - c["bb"][4]) - 0.3) < 1e-4 for c in lands))
    check_true(sec, "lands at z 0..0.3 and z 5.525..5.825", "both ends", sorted((round(float(c["bb"][4]), 3), round(float(c["bb"][5]), 3)) for c in lands),
               sorted((round(float(c["bb"][4]), 3), round(float(c["bb"][5]), 3)) for c in lands) == [(0.0, 0.3), (5.525, 5.825)])
    check(sec, "volume vs analytic pi[25 x 5.225 + 20.25 x 0.6 - 12.6025 x 5.825]", math.pi * (25 * 5.225 + 20.25 * 0.6 - 12.6025 * 5.825), vol(s), 0.01)
    pl = [p for p in plane_faces(s) if abs(p["n"][2] + 1) < 1e-6 and p["loc"][2] > 1e-3]
    rec(sec, "downward planar faces above the bed when printed on one land (the 0.5 mm radial step of the Ø10 body over the Ø9 land)", "info",
        [(round(float(p['loc'][2]), 2), round(p['area'], 2)) for p in pl], "-", True)
    b = drive()
    bb = tbb(b["spacer_near"])
    check(sec, "assembly: spacer y min (5.0)", 5.0, bb[2], POS_TOL)
    check(sec, "assembly: spacer y max (10.825)", 10.825, bb[3], POS_TOL)
    check(sec, "assembly: spacer axis z", ZS, 0.5 * (bb[4] + bb[5]), POS_TOL)
    d, _ = mindist(b["spacer_near"], b["shaft"])
    check(sec, "radial clearance spacer bore to shaft (R3.55 - R3.5)", 0.05, d, 1e-3)


def test_14_shaft_bearings():
    sec = "4 shaft / bearings"
    b = drive()
    sh = b["shaft"]
    bb = tbb(sh)
    check(sec, "shaft y min (-3.0)", -3.0, bb[2], POS_TOL)
    check(sec, "shaft y max (52.0)", 52.0, bb[3], POS_TOL)
    check(sec, "shaft length (55)", 55.0, bb[3] - bb[2], POS_TOL)
    check(sec, "shaft diameter (Ø7)", 7.0, bb[1] - bb[0], POS_TOL)
    check(sec, "shaft axis x", 0.0, 0.5 * (bb[0] + bb[1]), POS_TOL)
    check(sec, "shaft axis z", ZS, 0.5 * (bb[4] + bb[5]), POS_TOL)
    for nm, y0 in [("bearing_near", 0.0), ("bearing_far", 44.0)]:
        cf = {round(c["r"], 3): c for c in cyl_faces(b[nm])}
        bbx = tbb(b[nm])
        check_true(sec, f"{nm}: 687 envelope ID 7 / OD 14", "R3.5 / R7.0", sorted(cf), set(cf) == {3.5, 7.0})
        check(sec, f"{nm}: width (5)", 5.0, bbx[3] - bbx[2], POS_TOL)
        check(sec, f"{nm}: y start", y0, bbx[2], POS_TOL)
        check(sec, f"{nm}: axis z", ZS, 0.5 * (bbx[4] + bbx[5]), POS_TOL)
        check(sec, f"{nm}: axis x", 0.0, 0.5 * (bbx[0] + bbx[1]), POS_TOL)
    # stack: bearing near 0-5 | spacer 5-10.825 | spool 10.825-44.0 | bearing far 44-49: faces touch, no gaps
    check(sec, "stack: spacer y min equals near-bearing face (5.0)", 5.0, tbb(b["spacer_near"])[2], POS_TOL)
    check(sec, "stack: spool far land end equals far-bearing face (44.0)", 44.0, tbb(b["spool_gear54"])[3], POS_TOL)
    d, _ = mindist(b["spool_gear54"], b["bearing_far"])
    check_le(sec, "spool to far bearing distance (touching on the Ø9 land)", 1e-4, d)
    d, _ = mindist(b["spacer_near"], b["bearing_near"])
    check_le(sec, "spacer to near bearing distance (touching on the Ø9 land)", 1e-4, d)


def _coax_cyl(shape, az, axis=1):
    return [c for c in cyl_faces(shape) if abs(c["dir"][axis]) > 0.999 and math.hypot(c["loc"][0], c["loc"][2] - az) < 0.01]


def _iv(intervals):
    return [(round(a_, 3), round(b_, 3)) for a_, b_ in intervals]


def _near_iv(iv, want, tol=2e-3):
    return len(iv) == len(want) and all(abs(a_ - w[0]) < tol and abs(b_ - w[1]) < tol for (a_, b_), w in zip(iv, want))


def test_15_pinion():
    """Revision C printed pinion: hub, D-bore, flat, heat-set pocket, clearance hole, extents (design frame, on the assembly body)."""
    sec = "2 pinion rev C"
    b = drive()
    pin = b["pinion"]
    bb = tbb(pin)
    check(sec, "pinion y min = hub end (-0.675, 0.5 clear of the pilot boss face y -1.175)", Y_HUB0, bb[2], POS_TOL)
    check(sec, "pinion y max = teeth end = shaft end (20.825)", 20.825, bb[3], POS_TOL)
    check(sec, "pinion total length (21.5)", 21.5, bb[3] - bb[2], POS_TOL)
    cf = _coax_cyl(pin, ZM)
    hub = [c for c in cf if abs(c["r"] - 7.0) < 1e-4]
    check_true(sec, "hub: cylinder faces R7.0 coaxial with the motor axis", ">= 1", len(hub), len(hub) >= 1)
    check(sec, "hub diameter (O14)", 14.0, 2 * hub[0]["r"], 1e-6)
    check(sec, "hub y start (-0.675)", Y_HUB0, min(c["bb"][2] for c in hub), POS_TOL)
    check(sec, "hub y end = teeth start (10.825)", 10.825, max(c["bb"][3] for c in hub), POS_TOL)
    check(sec, "hub length (11.5)", 11.5, max(c["bb"][3] for c in hub) - min(c["bb"][2] for c in hub), POS_TOL)
    bore = [c for c in cf if abs(c["r"] - BORE_R) < 1e-4]
    check_true(sec, "D-bore round faces R2.65 coaxial with the motor axis", ">= 1", len(bore), len(bore) >= 1)
    check(sec, "bore diameter (O5.30)", 5.30, 2 * bore[0]["r"], 1e-6)
    check(sec, "bore y start (through, -0.675)", Y_HUB0, min(c["bb"][2] for c in bore), POS_TOL)
    check(sec, "bore y end (through, 20.825)", 20.825, max(c["bb"][3] for c in bore), POS_TOL)
    # flat: plane facing the axis at z = ZM + 2.15, over the whole length
    fl = [p for p in plane_faces(pin) if abs(abs(p["n"][2]) - 1) < 1e-6 and abs(p["loc"][2] - (ZM + BORE_FLAT)) < 1e-3]
    check_true(sec, "bore flat: plane at axis + 2.15 on the +z side (normal toward the axis, -z)", "1+ face(s) at z = 4.79, n = -z",
               [(round(float(p["loc"][2]), 4), int(round(p["n"][2]))) for p in fl], len(fl) >= 1 and all(p["n"][2] < 0 for p in fl))
    check(sec, "bore flat y start", Y_HUB0, min(p["bb"][2] for p in fl), POS_TOL)
    check(sec, "bore flat y end", 20.825, max(p["bb"][3] for p in fl), POS_TOL)
    flat_other = [p for p in plane_faces(pin) if abs(abs(p["n"][2]) - 1) < 1e-6 and abs(p["loc"][2] - (ZM - BORE_FLAT)) < 1e-3]
    check_true(sec, "no flat on the -z side (the bore is round there)", "none", len(flat_other), not flat_other)
    # material probes along the D-bore (hub section y = 3.0, teeth section y = 15.825)
    for y, hi_up, hi_dn, lab in [(3.0, 7.0, 7.0, "hub y 3.0"), (15.825, RP_TIP, RP_TIP, "teeth y 15.825 (a tooth tip on both sides of the axis)")]:
        up = material(pin, (0, y, ZM), (0, 0, 1), 0, 12)
        dn = material(pin, (0, y, ZM), (0, 0, -1), 0, 12)
        px = material(pin, (0, y, ZM), (1, 0, 0), 0, 12)
        nx = material(pin, (0, y, ZM), (-1, 0, 0), 0, 12)
        check_true(sec, f"D-bore {lab}: +z side material starts at the FLAT 2.15", f"[(2.15, {hi_up})]", _iv(up), _near_iv(up, [(BORE_FLAT, hi_up)]))
        check_true(sec, f"D-bore {lab}: -z side material starts at the round R2.65", f"[(2.65, {hi_dn})]", _iv(dn), _near_iv(dn, [(BORE_R, hi_dn)]))
        check_true(sec, f"D-bore {lab}: +x and -x material start at R2.65 (round part)", "2.65 / 2.65", (_iv(px), _iv(nx)),
                   abs(px[0][0] - BORE_R) < 2e-3 and abs(nx[0][0] - BORE_R) < 2e-3)
    # heat-set pocket O4.0 x 4.5, radial from +z, at y ~ 7.91, hole O3.0 on to the bore
    pk = [c for c in cyl_faces(pin) if abs(c["r"] - INS_R) < 1e-4 and abs(c["dir"][2]) > 0.999]
    hl = [c for c in cyl_faces(pin) if abs(c["r"] - SS_R) < 1e-4 and abs(c["dir"][2]) > 0.999]
    check_true(sec, "pocket: cylinder face(s) R2.0 (O4.0) with axis along z", ">= 1", len(pk), len(pk) >= 1)
    check_true(sec, "clearance hole: cylinder face(s) R1.5 (O3.0) with axis along z", ">= 1", len(hl), len(hl) >= 1)
    check(sec, "pocket diameter (O4.0)", 4.0, 2 * pk[0]["r"], 1e-6)
    check(sec, "hole diameter (O3.0)", 3.0, 2 * hl[0]["r"], 1e-6)
    check(sec, "pocket axis y (spec ~7.91: middle of tab face 5.0 and teeth 10.825 = 7.9125; spec text also says 7.9)", Y_SS, pk[0]["loc"][1], 0.02)
    check(sec, "hole axis y (same)", Y_SS, hl[0]["loc"][1], 0.02)
    check(sec, "pocket axis x (on the motor axis)", 0.0, pk[0]["loc"][0], POS_TOL)
    check(sec, "pocket axis x/z: hole concentric (x)", 0.0, hl[0]["loc"][0], POS_TOL)
    z_hi = max(c["bb"][5] for c in pk) - ZM
    z_lo = min(c["bb"][4] for c in pk) - ZM
    check(sec, "pocket top at the hub surface (R7.0 above the axis on x = 0)", 7.0, z_hi, POS_TOL)
    check(sec, "pocket bottom 2.5 from the axis (4.5 deep from the hub surface)", 2.5, z_lo, POS_TOL)
    check(sec, "pocket depth from the hub surface (4.5)", INS_DEPTH, z_hi - z_lo, POS_TOL)
    pb_ = [p for p in plane_faces(pin) if abs(abs(p["n"][2]) - 1) < 1e-6 and abs(p["loc"][2] - (ZM + 2.5)) < 1e-3 and p["n"][2] > 0]
    check_true(sec, "pocket bottom: flat plane at axis + 2.5, facing +z", ">= 1", len(pb_), len(pb_) >= 1)
    # exposed hub window (tab face y 5.0 .. teeth y 10.825): pocket spans y 5.9125 .. 9.9125
    y_lo, y_hi = min(c["bb"][2] for c in pk), max(c["bb"][3] for c in pk)
    check_ge(sec, "pocket clear of the tab-face plane y 5.0 (mm; a key from +z reaches the screw)", 0.5, y_lo - 5.0)
    check_ge(sec, "pocket clear of the teeth y 10.825 (mm)", 0.5, 10.825 - y_hi)
    # probes through the pocket (y = 7.9125)
    ys = Y_SS
    up0 = material(pin, (0, ys, ZM), (0, 0, 1), 0, 12)
    check_true(sec, "pocket+hole open from the bore to the outside along +z at the axis (no material)", "[]", _iv(up0), up0 == [])
    up1 = material(pin, (1.0, ys, ZM), (0, 0, 1), 0, 12)
    check_true(sec, "hole O3.0 open at x = 1.0 (inside R1.5)", "[]", _iv(up1), up1 == [])
    x = 1.6
    up2 = material(pin, (x, ys, ZM), (0, 0, 1), 0, 12)
    check_true(sec, "pocket floor at x = 1.6 (outside the hole, inside the pocket): [round bore, 2.5]", f"[({math.sqrt(BORE_R**2 - x**2):.3f}, 2.5)]", _iv(up2),
               _near_iv(up2, [(math.sqrt(BORE_R ** 2 - x ** 2), 2.5)]))
    up3 = material(pin, (0, ys + 1.7, ZM), (0, 0, 1), 0, 12)
    check_true(sec, "pocket floor at y +1.7 off the screw axis (flat 2.15 to bottom 2.5): 0.35 mm", "[(2.15, 2.5)]", _iv(up3), _near_iv(up3, [(BORE_FLAT, 2.5)]))
    x = 2.1
    up4 = material(pin, (x, ys, ZM), (0, 0, 1), 0, 12)
    check_true(sec, "outside the pocket (x = 2.1 > R2.0): full wall from the bore to the hub surface", f"[({math.sqrt(BORE_R**2 - x**2):.3f}, {math.sqrt(49 - x**2):.3f})]", _iv(up4),
               _near_iv(up4, [(math.sqrt(BORE_R ** 2 - x ** 2), math.sqrt(49 - x ** 2))]))
    dn0 = material(pin, (0, ys, ZM), (0, 0, -1), 0, 12)
    check_true(sec, "pocket opens only toward +z: the -z wall at the same y is solid [2.65, 7.0]", "[(2.65, 7.0)]", _iv(dn0), _near_iv(dn0, [(BORE_R, 7.0)]))
    # independent rebuild of the whole pinion from the spec; the STEP must lie inside it and differ by the chamfer only
    G = generator()
    ang = sorted(math.degrees(math.atan2(c["face"].Center().z - ZM, c["face"].Center().x)) for c in cyl_faces(pin) if abs(c["r"] - RP_TIP) < 1e-3)
    phase_axial = (-ang[0]) % (360.0 / NP)
    gear_ax = G.gear(NP, MOD, 10.0, phase=phase_axial, reduction=THIN, root_radius=0.40).val()
    gear = gear_ax.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90).translate(cq.Vector(0, 10.825, ZM))
    hubs = cq.Solid.makeCylinder(7.0, 10.825 + 0.05 - Y_HUB0, cq.Vector(0, Y_HUB0, ZM), cq.Vector(0, 1, 0))
    ref = gear.fuse(hubs)
    bore_c = cq.Solid.makeCylinder(BORE_R, 23, cq.Vector(0, -1.5, ZM), cq.Vector(0, 1, 0))
    box = cq.Solid.makeBox(10, 23, 5 + BORE_FLAT, cq.Vector(-5, -1.5, ZM - 5))
    ref = cut(ref, common(bore_c, box))
    ref = cut(ref, cq.Solid.makeCylinder(INS_R, 6, cq.Vector(0, Y_SS, ZM + 7.0 - INS_DEPTH), cq.Vector(0, 0, 1)))
    ref = cut(ref, cq.Solid.makeCylinder(SS_R, 3, cq.Vector(0, Y_SS, ZM + 1.0), cq.Vector(0, 0, 1))).clean()
    vs, vr = vol(pin), vol(ref)
    check_true(sec, "independent rebuild from the spec (thinned 18T, hub O14 to y -0.675, D-bore O5.30 flat 2.15, pocket O4 x 4.5, hole O3): one valid solid", True,
               (len(ref.Solids()), valid(ref)), len(ref.Solids()) == 1 and valid(ref))
    check_le(sec, "STEP material outside the independent rebuild (boolean cut STEP minus rebuild, mm3)", 0.01, vol(cut(pin, ref)))
    top = [f for f in gear_ax.Faces() if abs(f.Center().z - 10.0) < 1e-6 and abs(f.normalAt().z - 1) < 1e-6][0]
    per = top.outerWire().Length()
    rec(sec, f"teeth-end chamfer: removed volume (rebuild minus STEP, mm3) vs perimeter {per:.2f} x 0.3^2 / 2 = {per * CH * CH / 2.0:.3f} (corner-free estimate; info)", "info",
        round(vr - vs, 4), "-", True)
    check_le(sec, "teeth-end chamfer: removed volume never exceeds the corner-free estimate (mm3)", per * CH * CH / 2.0 + 0.05, vr - vs)
    check_ge(sec, "teeth-end chamfer: removed volume at least 90 % of the estimate (a 0.3 x 45 deg chamfer is really there)", 0.9 * per * CH * CH / 2.0, vr - vs)
    # cross-section area at depth d from the end face against the outline offset inward by (0.3 - d): exact test of a 45 deg chamfer on the whole outline
    face0 = cq.Face.makeFromWires(top.outerWire())
    a_bore_d = BORE_R ** 2 * math.pi - (BORE_R ** 2 * math.acos(BORE_FLAT / BORE_R) - BORE_FLAT * math.sqrt(BORE_R ** 2 - BORE_FLAT ** 2))
    for dz in (0.05, 0.1, 0.2, 0.28, 0.5):
        inset = max(CH - dz, 0.0)
        ref_area = (cq.Face.makeFromWires(top.outerWire().offset2D(-inset)[0]).Area() if inset > 0 else face0.Area()) - a_bore_d
        y0 = 20.825 - dz
        slab = cq.Solid.makeBox(40, 0.02, 40, cq.Vector(-20, y0 - 0.01, ZM - 20))
        a_step = vol(common(pin, slab)) / 0.02
        # tip and root are exact (test_15b); on the involute flanks the built chamfer is about 4 % shallower than an exact perpendicular 0.3 offset
        # (the 54T spool chamfer matches the exact offset to 0.003 mm2).  Tolerance 2.0 mm2 = 0.018 mm mean flank position over the 112 mm outline.
        tol = 2.0 if inset > 0 else 0.15
        check(sec, f"teeth-end chamfer: section area at {dz} mm from the end face vs the outline inset {inset:.2f} (mm2; flank deficit {a_step - ref_area:+.3f} = {(a_step - ref_area) / per * 1000:.1f} um mean)", ref_area, a_step, tol)
    rec(sec, "pinion volume (mm3) / PETG mass at 1.27 g/cm3 (g), informative", "info", f"{vs:.2f} / {vs * 1.27e-3:.3f}", "-", True)


def test_15b_pinion_chamfer_and_thinning():
    sec = "2 pinion rev C teeth"
    pin = drive()["pinion"]
    ang = sorted(math.degrees(math.atan2(c["face"].Center().z - ZM, c["face"].Center().x)) for c in cyl_faces(pin) if abs(c["r"] - RP_TIP) < 1e-3)
    check_true(sec, "tip faces (R10.0): 18", NP, len(ang), len(ang) == NP)
    # tooth centre on the line of centres (design -z): tip radius vs distance from the teeth end face y 20.825
    for dz in [0.001, 0.1, 0.2, 0.3, 1.0]:
        y = 20.825 - dz
        tip = material(pin, (0, y, ZM), (0, 0, -1), 0, 14)[-1][1]
        a = math.radians(180.0 / NP)
        root = material(pin, (0, y, ZM), (math.sin(a), 0, -math.cos(a)), 0, 14)[-1][1]
        check(sec, f"teeth-end chamfer: tooth tip radius at {dz} mm from the end face (10.0 - max(0.3 - d, 0))", RP_TIP - max(CH - dz, 0.0), tip, 0.003)
        check(sec, f"teeth-end chamfer: tooth-space (root) radius at {dz} mm from the end face (7.75 - max(0.3 - d, 0))", RP_ROOT - max(CH - dz, 0.0), root, 0.003)
    # the hub side of the teeth (y 10.825) is NOT chamfered
    tip = material(pin, (0, 10.9, ZM), (0, 0, -1), 0, 14)[-1][1]
    check(sec, "no chamfer on the hub side of the teeth (tip radius at y 10.9)", RP_TIP, tip, 0.003)
    # end face plane at y 20.825 and its outline
    ef = [p for p in plane_faces(pin) if abs(p["n"][1] - 1) < 1e-6 and abs(p["loc"][1] - 20.825) < 1e-3]
    check_true(sec, "teeth end face: one planar face at y 20.825 facing +y", 1, len(ef), len(ef) == 1)
    check(sec, "end-face outline reaches R 9.7 at the tooth tips (tip 10.0 minus 0.3): extent along z", 19.4, ef[0]["bb"][5] - ef[0]["bb"][4], 0.01)
    # tooth thickness measured on the solid (ring volume / ring cross-section), pitch circle R9
    _, p_rim = rims()
    sols = common(p_rim, ring_y(RP_PITCH - 0.1, RP_PITCH + 0.1, 10.9, 20.4, 0, ZM)).Solids()
    t = float(np.mean([vol(x) for x in sols]) / (0.2 * (20.4 - 10.9)))
    check(sec, "pinion tooth thickness at R9 (pi/2 - 0.10 thinning = 1.4708)", math.pi / 2 - THIN, t, 0.005)


def test_16_cap_magnet_encoder():
    sec = "4 magnet cap / magnet / AS5600"
    cap = part("magnet_cap")
    bb = tbb(cap)
    check(sec, "cap diameter (Ø12)", 12.0, bb[1] - bb[0], 1e-4)
    check(sec, "cap thickness (6.25 = y 49.3 to 55.55)", 6.25, bb[5] - bb[4], 1e-4)
    cf = cyl_faces(cap)
    bore = [c for c in cf if abs(c["r"] - 3.5) < 1e-4][0]
    check(sec, "bore diameter (Ø7)", 7.0, 2 * bore["r"], 1e-6)
    check(sec, "bore depth (3.0)", 3.0, bore["bb"][5] - bb[4], 1e-4)
    pk = [c for c in cf if abs(c["r"] - 3.15) < 1e-4]
    check_true(sec, "pocket Ø6.3 (R3.15)", ">= 1 face", len(pk), len(pk) >= 1)
    check(sec, "pocket depth (2.5)", 2.5, bb[5] - min(c["bb"][4] for c in pk), 1e-4)
    axial = material(cap, (0.0, 0.0, -1.0), (0, 0, 1), 0, 8.5)
    check_true(sec, "web between bore floor and pocket floor (0.75): material z [3.0, 3.75] on the axis", "(3.0, 3.75)",
               [(round(a - 1, 3), round(b_ - 1, 3)) for a, b_ in axial], len(axial) == 1 and abs((axial[0][1] - axial[0][0]) - 0.75) < 1e-4 and abs(axial[0][0] - 1 - 3.0) < 1e-4)
    check_ge(sec, "web thickness (ENC1021_CAP_FLOOR_MIN 0.75)", 0.75 - 1e-6, axial[0][1] - axial[0][0])
    # crush ribs: radius of the first material along rays at z = 5 for angles on and between the ribs
    def first_r(ang, z=5.0):
        d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0)
        return material(cap, (0, 0, z), d, 0, 8)[0][0]
    on = [first_r(a) for a in (90, 210, 330)]
    off = [first_r(a) for a in (30, 150, 270, 0, 45)]
    check_true(sec, "3 crush ribs equally spaced (rib tips at 90, 210, 330 deg: R 2.88), pocket wall R3.15 elsewhere", "2.88 x3 / 3.15", f"{np.round(on, 3)} / {np.round(off, 3)}",
               all(abs(r - 2.88) < 2e-3 for r in on) and all(abs(r - 3.15) < 2e-3 for r in off))
    check(sec, "rib protrusion (pocket R3.15 - tip R2.88 = 0.15 per side + 0.12 crush)", 0.27, 3.15 - float(np.mean(on)), 2e-3)
    arcs = []
    prev = False
    for a in np.arange(0, 360.01, 0.1):
        inn = is_inside(cap, (2.95 * math.cos(math.radians(a)), 2.95 * math.sin(math.radians(a)), 5.0))
        if inn and not prev:
            arcs.append(a)
        prev = inn
    check_true(sec, "rib count (material arcs at R2.95 inside the pocket)", 3, len(arcs), len(arcs) == 3)
    a_in = [a for a in np.arange(80.0, 100.0, 0.05) if is_inside(cap, (2.9 * math.cos(math.radians(a)), 2.9 * math.sin(math.radians(a)), 5.0))]
    w29 = math.radians(max(a_in) - min(a_in) + 0.05) * 2.9
    check(sec, "rib width at R2.9 (0.02 behind the tip; ENC1021_V2 tip width 0.45), arc mm from an angular scan", 0.45, w29, 0.05)
    # in the assembly
    b = drive()
    mg = tbb(b["magnet"])
    check(sec, "magnet diameter (Ø6)", 6.0, mg[1] - mg[0], POS_TOL)
    check(sec, "magnet thickness (2.5)", 2.5, mg[3] - mg[2], POS_TOL)
    check(sec, "magnet y min (53.05)", 53.05, mg[2], POS_TOL)
    check(sec, "magnet face y (55.55 = cap face, flush)", 55.55, mg[3], POS_TOL)
    check(sec, "cap face y in the assembly (55.55)", 55.55, tbb(b["magnet_cap"])[3], POS_TOL)
    check(sec, "cap bearing-side face y (49.3)", 49.3, tbb(b["magnet_cap"])[2], POS_TOL)
    check(sec, "cap to far bearing gap (0.3)", 0.3, mindist(b["magnet_cap"], b["bearing_far"])[0], 1e-3)
    floor_y = tbb(b["magnet_cap"])[2] + bore["bb"][5] - bb[4]            # assembly cap y min + bore depth measured on the part file
    check(sec, "bore floor y (49.3 + 3.0 = 52.3)", 52.3, floor_y, POS_TOL)
    check(sec, "shaft end to bore floor gap (0.3)", 0.3, floor_y - tbb(b["shaft"])[3], POS_TOL)
    check(sec, "pocket floor y = magnet y min (53.05)", 53.05, tbb(b["magnet_cap"])[2] + min(c["bb"][4] for c in pk) - bb[4], POS_TOL)
    check(sec, "magnet axis z", ZS, 0.5 * (mg[4] + mg[5]), POS_TOL)
    ch, pcb = tbb(b["as5600_chip"]), tbb(b["as5600_board"])
    check(sec, "chip face y (57.05)", 57.05, ch[2], POS_TOL)
    check(sec, "air gap magnet face to chip face (1.5)", 1.5, ch[2] - mg[3], POS_TOL)
    check(sec, "chip height (ENC1021_CHIP_H 1.45)", 1.45, ch[3] - ch[2], POS_TOL)
    check(sec, "chip footprint x (6.0)", 6.0, ch[1] - ch[0], POS_TOL)
    check(sec, "chip footprint z (4.0)", 4.0, ch[5] - ch[4], POS_TOL)
    check(sec, "PCB y min (58.5)", 58.5, pcb[2], POS_TOL)
    check(sec, "PCB y max (60.1)", 60.1, pcb[3], POS_TOL)
    check(sec, "PCB x size (23)", 23.0, pcb[1] - pcb[0], POS_TOL)
    check(sec, "PCB z size (23)", 23.0, pcb[5] - pcb[4], POS_TOL)
    check(sec, "PCB centre x on the axis", 0.0, 0.5 * (pcb[0] + pcb[1]), POS_TOL)
    check(sec, "PCB centre z on the axis (-33.66)", ZS, 0.5 * (pcb[4] + pcb[5]), POS_TOL)
    check(sec, "chip centre z on the axis", ZS, 0.5 * (ch[4] + ch[5]), POS_TOL)
    check(sec, "chip centre x on the axis", 0.0, 0.5 * (ch[0] + ch[1]), POS_TOL)
    # cap volume cross-check (bore, pocket removed; ribs add a little)
    base = math.pi * (36 * 6.25 - 12.25 * 3.0 - 3.15 ** 2 * 2.5)
    check_true(sec, "cap volume = cylinder - bore - pocket + ribs (ribs 0..3 mm3)", f"{base:.2f}..{base + 3:.2f}", round(vol(cap), 3), base < vol(cap) < base + 3.0)
    ribs_v = cvol(drive()["magnet_cap"], drive()["magnet"])
    check_true(sec, "cap-rib / magnet interference volume (by design, 3 ribs x 0.12 crush)", "0.2 .. 0.6 mm3", round(ribs_v, 4), 0.2 < ribs_v < 0.6)


# =============================================================================== 5. clearances / overlaps inside the drive
def test_17_pairwise_overlap():
    sec = "5 overlaps"
    b = drive()
    names = list(b)
    bbs = {k: tbb(v) for k, v in b.items()}

    def near(a, c, tol=0.05):
        return all(a[2 * i] <= c[2 * i + 1] + tol and c[2 * i] <= a[2 * i + 1] + tol for i in range(3))
    over = []
    n = 0
    for a, c in itertools.combinations(names, 2):
        if not near(bbs[a], bbs[c]):
            continue
        n += 1
        v = cvol(b[a], b[c])
        if v > 0.01:
            over.append((a, c, round(v, 4)))
    rec(sec, "pairs with overlapping bounding boxes examined (of 136)", "-", n, "-", True)
    check_true(sec, "overlaps > 0.01 mm3: only magnet_cap / magnet (crush ribs, by design)", "[magnet_cap, magnet]", over, [(x[0], x[1]) for x in over] == [("magnet_cap", "magnet")])
    check(sec, "magnet_cap / magnet overlap volume (mm3)", 0.4125, over[0][2], 0.01)


def test_17b_contacts_and_fits():
    sec = "5 contacts / fits"
    b = drive()
    for a, c in [("motor_front_cap", "fin"), ("spacer_near", "spool_gear54"), ("spacer_near", "bearing_near"), ("spool_gear54", "bearing_far"),
                 ("magnet", "magnet_cap"), ("as5600_chip", "as5600_board"), ("shaft", "spool_gear54"), ("shaft", "bearing_near"), ("shaft", "bearing_far"),
                 ("shaft", "magnet_cap"), ("motor_shaft", "motor_front_cap")]:
        d, _ = mindist(b[a], b[c])
        check_le(sec, f"{a} touches {c} (distance, mm)", 1e-4, d)
    # radial fits (bore radius minus shaft radius), nominal CAD sizes
    def bore_r(body, rmin, rmax):
        return [c["r"] for c in cyl_faces(b[body]) if rmin < c["r"] < rmax and abs(c["dir"][1]) > 0.999][0]
    shaft_r = bore_r("shaft", 3.4, 3.6)
    for body, lo, hi, expect, note in [("spool_gear54", 3.4, 3.6, 0.0, "Ø7.00 bore on the Ø7 shaft (prints ~6.9: press fit)"),
                                       ("bearing_near", 3.4, 3.6, 0.0, "687 ID 7"), ("bearing_far", 3.4, 3.6, 0.0, "687 ID 7"),
                                       ("magnet_cap", 3.4, 3.6, 0.0, "Ø7 cap bore (press fit)"), ("spacer_near", 3.4, 3.7, 0.05, "Ø7.10 slip bore")]:
        check(sec, f"radial fit {body}: bore R - shaft R ({note})", expect, bore_r(body, lo, hi) - shaft_r, 1e-4)
    ms_r = bore_r("motor_shaft", 2.4, 2.6)
    check(sec, "radial fit pinion: round bore R2.65 minus motor shaft R2.5 (0.15 clearance)", 0.15, bore_r("pinion", 2.6, 2.7) - ms_r, 1e-4)
    d_ps, _ = mindist(b["pinion"], b["motor_shaft"])
    check(sec, "pinion bore to motor shaft: minimum distance (round 0.15, flat 2.15 against 2.0 = 0.15)", 0.15, d_ps, 2e-3)
    check_le(sec, "pinion x motor shaft overlap volume (mm3): no overlap", 1e-4, cvol(b["pinion"], b["motor_shaft"]))
    flat_gap = [p["loc"][2] for p in plane_faces(b["pinion"]) if abs(abs(p["n"][2]) - 1) < 1e-6 and abs(p["loc"][2] - (ZM + 2.15)) < 1e-3][0] - [p["loc"][2] for p in plane_faces(b["motor_shaft"]) if abs(p["n"][2] - 1) < 1e-6 and p["area"] > 10][0]
    check(sec, "pinion flat (axis + 2.15) to motor-shaft flat (axis + 2.0): gap", 0.15, flat_gap, 1e-3)


def test_18_clearances():
    sec = "5 clearances"
    b = drive()
    pin, sp = b["pinion"], b["spool_gear54"]
    hub = common(pin, ring_y(0.0001, 7.6, Y_HUB0 - 0.1, 10.8249, 0, ZM))              # hub only (y < teeth start)
    # volume sanity of the hub (O14 x 11.5, D-bore, pocket, hole), integrated numerically over the pocket disc
    r, d = BORE_R, BORE_FLAT
    seg = r * r * math.acos(d / r) - d * math.sqrt(r * r - d * d)
    a_bore = math.pi * r * r - seg
    g = np.linspace(-INS_R, INS_R, 801)
    X, Y = np.meshgrid(g, g)
    mk = X ** 2 + Y ** 2 <= INS_R ** 2
    v_pocket = float(np.sum((np.sqrt(49 - X[mk] ** 2) - 2.5)) * (g[1] - g[0]) ** 2)
    v_hole = math.pi * SS_R ** 2 * (2.5 - BORE_FLAT)
    v_exp = math.pi * 49 * 11.5 - a_bore * 11.5 - v_pocket - v_hole
    check(sec, "extracted pinion hub (O14 x 11.5) volume vs analytic (hub - D-bore - pocket - hole), mm3", v_exp, vol(hub), 1.0)
    g_rim, _ = rims()
    sweep = []
    for dg in [0.0, 5.0 / 3.0, 10.0 / 3.0, 5.0]:
        sweep.append((dg, mindist(rot_y(g_rim, ZS, dg), hub)[0]))
    dmin = min(v for _, v in sweep)
    rec(sec, "gear rim to pinion hub over one gear pitch of spool rotation (deg: mm)", "info", "; ".join(f"{a:.3f}:{v:.4f}" for a, v in sweep), "-", True)
    check_ge(sec, "gear tip to pinion hub, worst pose over one gear tooth pitch (mm, >= 1.0 spec criterion)", 1.0, dmin)
    check(sec, "worst-pose gear-to-hub distance = sqrt(1.3^2 + 0.3^2) (tip on the line of centres, 0.3 chamfer), mm", math.hypot(CD - RG_TIP - 7.0, CH), dmin, 0.01)
    d, dd = mindist(sp, hub)
    check_ge(sec, "gear (whole spool) to pinion hub, reference pose (mm, >= 1.0 spec criterion)", 1.0, d)
    check_ge(sec, "gear to pinion hub >= radial bound CD - R_tip - R_hub = 36.30 - 28.0 - 7.0 = 1.3 (mm, consistency)", CD - RG_TIP - 7.0 - 1e-6, d)
    p1, p2 = dd.PointOnShape1(1), dd.PointOnShape2(1)
    rec(sec, "gear-to-hub closest points (spool point; hub point; design frame, info)", "info",
        f"({p1.X():.3f},{p1.Y():.3f},{p1.Z():.3f}); ({p2.X():.3f},{p2.Y():.3f},{p2.Z():.3f})", "-", True)
    d_all, _ = mindist(sp, pin)
    rec(sec, "gear (whole spool) to the whole pinion incl. teeth (mm, info; the teeth mesh)", "info", round(d_all, 4), "-", True)
    for k in ["motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "fin"]:
        d, _ = mindist(sp, b[k])
        check_ge(sec, f"spool_gear54 to {k} (mm, >= 1.5)", 1.5, d)
    # printed pinion to the motor: axial to the pilot boss face, >= 0.4 to every motor body except the shaft it sits on
    cap = tbb(b["motor_front_cap"])
    check(sec, "motor pilot boss face y (front face -3.175 + 2.0 = -1.175), from the front cap bbox", Y_BOSS, cap[3], POS_TOL)
    check_ge(sec, "pinion hub end to the pilot boss face, axial (mm, >= 0.4 spec criterion)", 0.4, tbb(pin)[2] - cap[3])
    check(sec, "pinion hub end to the pilot boss face, axial (0.5 spec)", 0.5, tbb(pin)[2] - cap[3], POS_TOL)
    for k in ["motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_connector"]:
        d, _ = mindist(pin, b[k])
        check_ge(sec, f"pinion to {k} (mm, >= 0.4)", 0.4, d)
    d, _ = mindist(pin, b["fin"])
    check_ge(sec, "pinion to fin (mm, >= 1.5 radial)", 1.5, d)
    # radial clearance through the fin's motor hole, measured on the hole cylinder of the fin
    fh = [c["r"] for c in _coax_cyl(b["fin"], ZM) if 8.0 < c["r"] < 20.0]
    check_true(sec, "fin motor hole: coaxial cylinder face found", ">= 1", sorted(set(round(x, 3) for x in fh)), len(fh) >= 1)
    check_ge(sec, "fin motor hole radius minus hub radius R7.0 (mm, >= 1.5 radial)", 1.5, min(fh) - 7.0)
    # the pinion stays clear of the teeth' own bore etc.
    check_le(sec, "pinion x fin overlap volume (mm3)", 1e-4, cvol(pin, b["fin"]))


def test_18b_pinion_vs_slipin_tab_hole():
    sec = "5 clearances (slide-in tab hole)"
    b = drive("drive_with_slipin_asm1021")
    pin, tab = b["pinion"], b["slipin_mount"]
    th = [c for c in _coax_cyl(tab, ZM) if 8.0 < c["r"] < 20.0 and c["bb"][2] < 1.0 and c["bb"][3] > 4.0]
    check_true(sec, "slide-in tab motor hole: coaxial cylinder across the tab (y 0 .. 5)", ">= 1", sorted(set(round(c["r"], 3) for c in th)), len(th) >= 1)
    r_hole = min(c["r"] for c in th)
    check(sec, "tab motor hole diameter (spec O22.4)", 22.4, 2 * r_hole, 0.01)
    check_ge(sec, "tab hole radius minus hub radius R7.0 (mm, >= 1.5 radial)", 1.5, r_hole - 7.0)
    d, dd = mindist(pin, tab)
    check_ge(sec, "pinion to the slide-in, whole solid (mm, >= 1.5)", 1.5, d)
    check_le(sec, "pinion x slide-in overlap volume (mm3)", 1e-4, cvol(pin, tab))
    rec(sec, "pinion to slide-in minimum distance (mm; build notes 4.20 = 11.2 - 7.0)", "info", round(d, 3), "-", True)
    d, _ = mindist(pin, b["wall_mount"])
    check_ge(sec, "pinion to the wall mount (mm, >= 1.5)", 1.5, d)


# =============================================================================== 6. interference with Jasper's slide-in and wall mount
def test_19_interference_with_mounts():
    sec = "6 slide-in / wall mount"
    b = drive("drive_with_slipin_asm1021")
    names = [k for k in b if k not in ("slipin_mount", "wall_mount")]
    bbs = {k: tbb(v) for k, v in b.items()}

    def near(a, c, tol=0.05):
        return all(a[2 * i] <= c[2 * i + 1] + tol and c[2 * i] <= a[2 * i + 1] + tol for i in range(3))
    res = {}
    allv = {}
    for m in ("slipin_mount", "wall_mount"):
        for k in names:
            if near(bbs[m], bbs[k]):
                res[(m, k)] = common(b[m], b[k])
                allv[(m, k)] = vol(res[(m, k)])
    got = {key: round(v, 3) for key, v in allv.items() if v > 1e-3}
    rec(sec, "all (mount, drive body) pairs with overlapping bounding boxes examined", "-", len(allv), "-", True)
    want_set = {("slipin_mount", "spool_gear54"), ("slipin_mount", "spacer_near"), ("wall_mount", "spool_gear54")}
    rec(sec, "all overlapping (mount, body) pairs found (revision C)", "slipin: spool, spacer; wall: spool (no pinion)", sorted(f"{m}/{k}" for m, k in got),
        "-", set(got) == want_set)
    assert set(got) == want_set, got
    rec(sec, "overlap volumes (mm3)", "info", {f"{m}/{k}": v for (m, k), v in sorted(got.items())}, "-", True)
    for m in ("slipin_mount", "wall_mount"):
        v_pin = allv.get((m, "pinion"), 0.0)
        check_true(sec, f"{m} x pinion (hub through the tab hole): overlap volume (mm3)", "0", round(v_pin, 5), v_pin < 1e-3)
    # the shaft no longer touches the slide-in: confirm with a distance, not only an empty boolean
    d_sh, _ = mindist(b["slipin_mount"], b["shaft"])
    check_ge(sec, "slipin_mount to shaft: distance (mm) (>= 0: no overlap now; revision A had 54.8 mm3 at the old axis z -37.56)", 0.0, d_sh)
    check(sec, "slipin_mount to shaft closest approach (notes 0.056; rev B 0.127)", 0.056, d_sh, 0.005)
    check_true(sec, "slipin_mount x shaft overlap volume (mm3)", "0", round(allv[("slipin_mount", "shaft")], 4), allv[("slipin_mount", "shaft")] < 1e-3)

    def box(x0, x1, y0, y1, z0, z1):
        return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
    big = 1000.0
    c = res[("slipin_mount", "spool_gear54")]
    A = vol(common(c, box(-big, -21.15, -big, big, -big, big)))
    B = vol(common(c, box(-21.15, big, -big, big, -big, -42.40)))
    C = vol(common(c, box(-21.15, big, -big, big, -42.40, big)))
    rec(sec, "slide-in x spool by region: back plate x < -21.15 / deck block z < -42.4 / above the deck z > -42.4 (mm3)", "info", f"{A:.3f} / {B:.3f} / {C:.3f}", "-", True)
    check(sec, "slide-in x spool: region sum equals total", got[("slipin_mount", "spool_gear54")], A + B + C, 0.01)
    # comparison with verification/winch_gear3_build_notes.md section 5 (revision C table C4; the notes were read by the verifier before this run - the lead handed over the revision C figures - so these are agreement checks, the volumes themselves are measured here)
    check(sec, "slipin_mount x spool_gear54 volume (build notes rev C 2463.5)", 2463.5, got[("slipin_mount", "spool_gear54")], 1.0)
    check(sec, "slide-in x spool: back plate x < -21.15 (notes 1233.3)", 1233.3, A, 0.5)
    check(sec, "slide-in x spool: deck block z < -42.4 (notes 1143.2)", 1143.2, B, 0.5)
    check(sec, "slide-in x spool: above the deck z > -42.4 (notes 87.0 = 74.2 drum in the far cheek + 12.8 teeth)", 87.0, C, 0.5)
    check(sec, "slipin_mount x spacer_near volume (notes 14.0)", 14.0, got[("slipin_mount", "spacer_near")], 0.2)
    check(sec, "wall_mount x spool_gear54 volume (notes 31.0 = 28.4 + 2.5)", 31.0, got[("wall_mount", "spool_gear54")], 0.2)
    pieces = sorted((vol(x), tuple(np.round(tbb(x), 2))) for x in c.Solids())[::-1]
    rec(sec, "slide-in x spool pieces (volume, bbox x0 x1 y0 y1 z0 z1)", "info", [(round(v, 3), [float(x) for x in bb_]) for v, bb_ in pieces], "-", True)
    bsp = common(common(c, box(-21.15, big, -big, big, -big, -42.40)), box(-big, big, 10.8, 20.825, -big, big))
    rec(sec, "slide-in x spool: deck block under the gear y 10.825..20.825 (mm3)", "info", round(vol(bsp), 3), "-", True)
    sp = res[("slipin_mount", "spacer_near")]
    rec(sec, "slide-in x spacer_near: volume, bbox", "info", (round(vol(sp), 3), [float(x) for x in np.round(tbb(sp), 2)]), "-", True)
    w = res[("wall_mount", "spool_gear54")]
    wp = sorted((vol(x), tuple(np.round(tbb(x), 2))) for x in w.Solids())[::-1]
    rec(sec, "wall mount x spool pieces (volume, bbox)", "info", [(round(v, 3), [float(x) for x in bb_]) for v, bb_ in wp], "-", True)
    check_true(sec, "wall mount x spool: 2 pieces 28.4 + 2.5 (notes)", "2 pieces", [round(v, 1) for v, _ in wp], len(wp) == 2 and abs(wp[0][0] - 28.4) < 0.2 and abs(wp[1][0] - 2.5) < 0.2)
    # nearest approach of the bodies that do not overlap (redesign inputs): report distances
    near_list = []
    for m in ("slipin_mount", "wall_mount"):
        for k in names:
            if (m, k) in got:
                continue
            if near(bbs[m], bbs[k], tol=3.0):
                d, _ = mindist(b[m], b[k])
                near_list.append((m, k, round(d, 3)))
    rec(sec, "non-overlapping bodies within 3 mm bbox proximity: distance (mm)", "info", sorted(near_list, key=lambda x: x[2])[:8], "-", True)
    # original SolidWorks assembly extras: spool replaced, shell
    sw = read_asm(SW_ASSEMBLY)
    sh = shift_design(sw["Shell_Casing"])
    old = shift_design(sw["Spool1011"])
    d0 = drive()
    info = {}
    for k in names:
        if near(tbb(sh), tbb(d0[k])):
            v = cvol(sh, d0[k])
            if v > 1e-3:
                info["Shell_Casing x " + k] = round(v, 3)
    info["Spool1011 x pinion"] = round(cvol(old, d0["pinion"]), 3)
    info["Spool1011 x motor_shaft"] = round(cvol(old, d0["motor_shaft"]), 3)
    rec(sec, "informative: shell (Shell_Casing of the original assembly) x drive bodies, and the replaced old spool (mm3)", "info", info, "-", True)
    check(sec, "Shell_Casing x spool_gear54 (notes 736.2)", 736.2, info["Shell_Casing x spool_gear54"], 1.0)
    check(sec, "Shell_Casing x as5600_board (notes 36.6)", 36.6, info["Shell_Casing x as5600_board"], 0.5)
    check_true(sec, "Shell_Casing x bearings (notes: 0 now, 6.1 each in revision A)", "0 / 0", [info.get("Shell_Casing x bearing_near", 0), info.get("Shell_Casing x bearing_far", 0)],
               "Shell_Casing x bearing_near" not in info and "Shell_Casing x bearing_far" not in info)
    check(sec, "Spool1011 x pinion (notes 1994.1; the old spool sits where the new hub and teeth are)", 1994.1, info["Spool1011 x pinion"], 1.0)
    check(sec, "Spool1011 x motor_shaft (notes 8.35)", 8.35, info["Spool1011 x motor_shaft"], 0.1)
    fin_over = cvol(sh, d0["fin"])
    rec(sec, "NOT caused by the gears: Shell_Casing x fin (1/8 in fin is thicker than the Heat_horn it replaces) mm3", "info", round(fin_over, 3), "-", True)
    # distance of the shell to the bodies it does not overlap
    dsh = {}
    for k in ["as5600_board", "magnet_cap", "spacer_near", "bearing_near", "bearing_far", "pinion", "shaft", "motor_shaft"]:
        dsh["Shell_Casing to " + k] = round(mindist(sh, d0[k])[0], 3)
    rec(sec, "shell distance to selected bodies (mm; 0 = touching/overlapping)", "info", dsh, "-", True)


# =============================================================================== 7. parameter audit and renders
def test_20_params_audit():
    import sys
    sys.path.insert(0, REPO)
    from cad import params as P   # read-only
    sec = "params WG3_*"
    want = dict(WG3_MODULE=1.0, WG3_PRESSURE_ANGLE_DEG=20.0, WG3_Z_PINION=18, WG3_Z_GEAR=54, WG3_RATIO=3.0, WG3_CD_NOMINAL=36.0, WG3_CD=36.30, WG3_CD_ALLOW=0.30, WG3_FACE=10.0,
                WG3_GEAR_TOOTH_THIN=0.10, WG3_PINION_TOOTH_THIN=0.10, WG3_Y_TEETH0=10.825, WG3_Y_TEETH1=20.825, WG3_Y_SHAFT_END=20.825, WG3_PINION_BORE_D=5.30,
                WG3_PINION_BORE_FLAT_X=2.15, WG3_PINION_HUB_D=14.0, WG3_PINION_HUB_L=11.5, WG3_Y_PINION_HUB0=-0.675, WG3_Y_BOSS_FACE=-1.175,
                WG3_PINION_INSERT_D=4.0, WG3_PINION_INSERT_DEPTH=4.5, WG3_PINION_SETSCREW_D=3.0, WG3_Y_PINION_SETSCREW=7.9125, WG3_PINION_MIN_CLEAR_MOTOR=0.4,
                WG3_WINDOW_N=6, WG3_WINDOW_D=10.0, WG3_WINDOW_R=17.5, WG3_RIM_MIN=3.0, WG3_WEB_MIN=2.0,
                WG3_BED_CHAMFER=0.3, WG3_DRUM_D=15.0, WG3_DRUM_L=16.0, WG3_Y_DRUM1=36.825, WG3_FLANGE_D=36.0, WG3_FLANGE_T=3.0, WG3_Y_FLANGE1=39.825, WG3_HUB_D=12.0,
                WG3_Y_SPOOL_END=44.0, WG3_LAND_D=9.0, WG3_LAND_PROUD=0.3, WG3_BORE_D=7.0, WG3_TIEOFF_D=1.4, WG3_TIEOFF_OFFSET=5.25, WG3_TIEOFF_Y=28.825,
                WG3_SPACER_OD=10.0, WG3_SPACER_BORE_D=7.10, WG3_SPACER_Y0=5.0, WG3_SPACER_Y1=10.825, WG3_SHAFT_D=7.0, WG3_SHAFT_Y0=-3.0, WG3_SHAFT_L=55.0,
                WG3_BRG_ID=7.0, WG3_BRG_OD=14.0, WG3_BRG_W=5.0, WG3_BRG_NEAR_Y0=0.0, WG3_BRG_FAR_Y0=44.0, WG3_CAP_Y0=49.3, WG3_CAP_D=12.0, WG3_CAP_BORE_DEPTH=3.0,
                WG3_CAP_WEB=0.75, WG3_MAGNET_D=6.0, WG3_MAGNET_T=2.5, WG3_CAP_POCKET_D=6.3, WG3_CAP_POCKET_DEPTH=2.5, WG3_Y_MAGNET0=53.05, WG3_CAP_Y1=55.55,
                WG3_CHIP_FACE_Y=57.05, WG3_PCB_Y0=58.5, WG3_PCB_Y1=60.1, WG3_MIN_CLEAR=1.5, WG3_MIN_CLEAR_HUB=1.0)
    bad = {k: (v, getattr(P, k, None)) for k, v in want.items() if not (hasattr(P, k) and abs(getattr(P, k) - v) < 1e-9)}
    check_true(sec, f"WG3_* values equal the revision C spec numbers ({len(want)} checked)", "no mismatch", bad or "no mismatch", not bad)
    check_true(sec, "spool axis (x, z)", "(0.0, -33.66)", tuple(round(v, 6) for v in P.WG3_SPOOL_XZ), abs(P.WG3_SPOOL_XZ[0]) < 1e-9 and abs(P.WG3_SPOOL_XZ[1] + 33.66) < 1e-9)
    dupe = [n for n, v in [("SPOOL_FLANGE_THK", getattr(P, "SPOOL_FLANGE_THK", None)), ("NEMA17T_TAP_D", getattr(P, "NEMA17T_TAP_D", None))] if v == 3.0]
    rec(sec, "WG3_FLANGE_T = 3.0 and WG3_PINION_SETSCREW_D = 3.0 are literals; equal values exist as", "info", dupe, "-", True)


def test_21_renders_exist():
    sec = "7 renders"
    names = ["front", "side", "top", "iso", "mesh", "section_axis", "section_cap", "section_tieoff"]
    for n in names:
        p = RENDERS + f"winch_gear3_{n}.png"
        check_true(sec, f"{n}.png present and non-trivial", "> 10 kB", os.path.getsize(p) if os.path.exists(p) else 0, os.path.exists(p) and os.path.getsize(p) > 10000)
    got = sorted(os.listdir(RENDERS))
    check_true(sec, "renders/winch_gear3 holds exactly the 8 expected files (no stale ones)", [f"winch_gear3_{n}.png" for n in sorted(names)], got,
               got == sorted(f"winch_gear3_{n}.png" for n in names))
    # not older than the revision C exports (rendered after the STEP files were regenerated)
    t_step = os.path.getmtime(STEP + "winch_gear3_drive_asm1021.step")
    older = [n for n in names if os.path.getmtime(RENDERS + f"winch_gear3_{n}.png") < t_step - 60]
    check_true(sec, "no render is more than 60 s older than drive_asm1021.step", "none older", older or "none older", not older)


def test_99_summary():
    print("\n\n==== VERIFICATION SUMMARY (geometry-verifier, winch_gear3) ====")
    fails = [r for r in REC if r[5] != "PASS"]
    print(f"{len(REC)} recorded checks, {len(fails)} FAIL")
    sec = None
    for r in REC:
        if r[0] != sec:
            sec = r[0]
            print(f"\n## {sec}")
        print(f"| {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
    assert not fails
