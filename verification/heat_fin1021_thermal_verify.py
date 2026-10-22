"""Independent verification harness for the 10/22 heat fin, thermal station, detailed NEMA 17 and the Ø4 magnet caps.

Run (read-only, nothing under cad/ or exports/ is written):
    PYTHONPATH=. /usr/bin/python3 verification/heat_fin1021_thermal_verify.py            # prints the table, writes verification/heat_fin1021_thermal_results.json
    PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_heat_fin1021_thermal_verification.py

Everything is measured from the files on disk (STEP / STL / DXF) and from the reference STEPs in cad/reference/station_1021 and
solidworks/v4_assembly_2026-10-21; the builders' own measurement helpers are NOT used for any pass/fail decision.
Frames: station_1021 = reference STEP frame; assembly = station_1021 + O (O from cad/reference/station_1021/extract.py).
The reference files carry a common extraction residual RES (cad/params.py ENC1021_REF_RESIDUAL), so "design" values are file values minus RES.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import struct
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad import params as P  # noqa: E402  (master values are used only as the expected-value source, never to build geometry)
from cad.reference.station_1021.extract import O as O_TUPLE, SRC as ASM_SRC  # noqa: E402

REF = ROOT / "cad" / "reference" / "station_1021"
STEP = ROOT / "exports" / "step"
STL = ROOT / "exports" / "stl"
DXF = ROOT / "exports" / "dxf"
O = cq.Vector(*O_TUPLE)
RES = cq.Vector(*P.ENC1021_REF_RESIDUAL)
T_PROD, T_PROTO = 3.175, 0.483          # spec values typed here on purpose (independent of the params block)

RESULTS: list[dict] = []


def chk(cid: str, item: str, expected, measured, tol, ok: bool | None = None, note: str = "") -> bool:
    """Record one check. expected/measured are numbers (|m - e| <= tol decides) or strings (ok given explicitly)."""
    if ok is None:
        ok = abs(float(measured) - float(expected)) <= tol
    RESULTS.append(dict(id=cid, item=item, expected=expected, measured=measured, tol=tol, status="PASS" if ok else "FAIL", note=note))
    return ok


# ---------------------------------------------------------------- helpers
def load(path) -> cq.Shape:
    return cq.importers.importStep(str(path)).val()


def is_valid(shape: cq.Shape) -> bool:
    return BRepCheck_Analyzer(shape.wrapped).IsValid()


def bbox6(s: cq.Shape):
    b = s.BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def named(path) -> dict:
    """{component name: shape} read with OpenCascade XCAF (component names = the STEP product / instance names)."""
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    r.ReadFile(str(path))
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = TDF_LabelSequence()
    st.GetFreeShapes(roots)
    out: dict = {}
    dup: list = []

    def nm(lab):
        a = TDataStd_Name()
        return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else None
    for i in range(roots.Length()):
        root = roots.Value(i + 1)
        if st.IsAssembly_s(root):
            comps = TDF_LabelSequence()
            st.GetComponents_s(root, comps)
            for j in range(comps.Length()):
                c = comps.Value(j + 1)
                n = nm(c)
                if n in out:
                    dup.append(n)
                out[n] = cq.Shape.cast(st.GetShape_s(c))
        else:
            out[nm(root)] = cq.Shape.cast(st.GetShape_s(root))
    out["__duplicates__"] = dup
    return out


def cylinders(shape: cq.Shape):
    """All cylindrical faces: dict(r, p (point on axis), d (unit axis), area, bb, face)."""
    res = []
    for f in shape.Faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() == GeomAbs_Cylinder:
            c = ad.Cylinder()
            ax = c.Axis()
            res.append(dict(r=c.Radius(), p=np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()]),
                            d=np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()]), area=f.Area(), bb=bbox6(f), face=f))
    return res


def axis_xy(c, drop: int):
    """(a, b) = the two coordinates of the axis point after dropping the axis coordinate index `drop`."""
    idx = [i for i in range(3) if i != drop]
    return tuple(c["p"][idx])


def merged_cyl(shape, drop: int):
    """Group cylindrical faces by (rounded radius, rounded axis position): list of (r, a, b, lo, hi, total area) with the axis extent lo..hi."""
    groups: dict = {}
    for c in cylinders(shape):
        if abs(abs(c["d"][drop]) - 1) > 1e-6:
            continue
        a, b = axis_xy(c, drop)
        key = (round(c["r"], 4), round(a, 3), round(b, 3))
        bb = c["bb"]
        lo, hi = bb[2 * drop], bb[2 * drop + 1]
        g = groups.setdefault(key, [lo, hi, 0.0])
        g[0], g[1], g[2] = min(g[0], lo), max(g[1], hi), g[2] + c["area"]
    return [(k[0], k[1], k[2], v[0], v[1], v[2]) for k, v in sorted(groups.items())]


def probe_inside(shape, pt) -> bool:
    return shape.isInside(cq.Vector(*pt), 1e-6)


def read_stl(path):
    with open(path, "rb") as fh:
        data = fh.read()
    n = struct.unpack("<I", data[80:84])[0]
    assert len(data) == 84 + 50 * n, "not a binary STL of the stated triangle count"
    arr = np.frombuffer(data[84:], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n)
    return arr["v"].astype(float), arr["n"].astype(float)


def stl_volume_area(tri):
    v0, v1, v2 = tri[:, 0], tri[:, 1], tri[:, 2]
    vol = np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0
    area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum()
    return vol, area


def stl_watertight(tri) -> tuple:
    """(closed manifold?, number of edges not shared by exactly two triangles) from the vertex-welded triangle list."""
    key = np.round(tri.reshape(-1, 3), 4)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    idx = inv.reshape(-1, 3)
    edges: dict = {}
    for a, b, c in idx:
        for e in ((a, b), (b, c), (c, a)):
            k = (min(e), max(e))
            edges[k] = edges.get(k, 0) + 1
    bad = sum(1 for v in edges.values() if v != 2)
    return bad == 0, bad


# ================================================================ SECTION 1: FIN
def section1():
    horn_ref = load(REF / "Heat_horn.step")
    asm_solids = cq.importers.importStep(str(ASM_SRC)).val().Solids()
    horn_asm = [s for s in asm_solids if abs(s.Volume() - 16948.551) < 0.05 and abs(bbox6(s)[3] - bbox6(s)[2] - 2.0) < 0.01][0]
    # reference face at y = 0
    y0 = [f for f in horn_ref.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y) > 0.999 and abs(f.Center().y - RES.y) < 1e-3 and f.Area() > 5000][0]
    area_ref = y0.Area()
    # -- reference outline (sanity of the expected numbers themselves)
    verts = sorted({(round(v.X - RES.x, 3), round(v.Z - RES.z, 3)) for v in y0.outerWire().Vertices()})
    vx = {(-20.0, -18.36), (22.0, -18.36), (-20.0, 177.24), (22.0, 210.24)}
    chk("1.0a", "Heat_horn y=0 outline vertices (x,z), design frame", sorted(vx), verts, 0.005, ok=all(abs(a[0] - b[0]) < 0.005 and abs(a[1] - b[1]) < 0.005 for a, b in zip(sorted(vx), verts)) and len(verts) == 4)
    edges = {"bottom": 42.0, "left": 195.6, "right": 228.6, "top (slanted)": 53.4}
    meas = {"bottom": 22.0 - -20.0, "left": 177.24 - -18.36, "right": 210.24 - -18.36, "top (slanted)": math.hypot(42.0, 210.24 - 177.24)}
    for k, e in edges.items():
        chk("1.0b", f"reference outline edge: {k} (mm)", e, round(meas[k], 3), 0.02 if k != "top (slanted)" else 0.02)
    # -- fin files
    flat = load(STEP / "heat_fin1021_1p8.step")
    a18 = load(STEP / "heat_fin1021_1p8_asm1021.step")
    a019 = load(STEP / "heat_fin1021_0p019_asm1021.step")
    for nm, s in (("flat 1p8", flat), ("asm 1p8", a18), ("asm 0p019", a019)):
        chk("1.1", f"{nm}: single valid solid", "1 solid, valid", f"{len(s.Solids())} solid(s), valid={is_valid(s)}", 0, ok=len(s.Solids()) == 1 and is_valid(s))
    # thickness
    bb = bbox6(a18)
    chk("1.2a", "asm 1p8 thickness (y extent, mm)", T_PROD, bb[3] - bb[2], 0.001)
    chk("1.2b", "asm 0p019 thickness (y extent, mm)", T_PROTO, bbox6(a019)[3] - bbox6(a019)[2], 0.001)
    chk("1.2c", "flat 1p8 thickness (z extent, mm)", T_PROD, bbox6(flat)[5] - bbox6(flat)[4], 0.001)
    # flat bbox and origin
    fb = bbox6(flat)
    chk("1.3a", "flat bbox X extent", 42.0, fb[1] - fb[0], 0.001)
    chk("1.3b", "flat bbox Y extent", 228.6, fb[3] - fb[2], 0.001)
    chk("1.3c", "flat bbox Z extent", 3.175, fb[5] - fb[4], 0.001)
    chk("1.3d", "flat bbox min corner (origin at bottom-left of the 42 mm edge)", (0, 0, 0), tuple(round(v, 5) for v in (fb[0], fb[2], fb[4])), 0.001,
        ok=max(abs(fb[0]), abs(fb[2]), abs(fb[4])) < 0.001)
    # orientation: the long (228.6) side must be on the X = 42 side, the shorter (195.6) on X = 0; the slanted edge between
    probe = lambda x, y: flat.isInside(cq.Vector(x, y, 1.0), 1e-6)  # noqa: E731
    chk("1.3e", "flat orientation: material at (41,220), none at (1,220); material at (1,190)", "True/False/True", f"{probe(41, 220)}/{probe(1, 220)}/{probe(1, 190)}", 0,
        ok=probe(41, 220) and not probe(1, 220) and probe(1, 190))
    # holes on the flat file
    cy = merged_cyl(flat, 2)
    exp_h = [(22.5 / 2, 20.0, 21.0)] + [(1.7, 20.0 + sx * 15.5, 21.0 + sz * 15.5) for sx in (-1, 1) for sz in (-1, 1)]
    ok_all = len(cy) == 5
    detail = []
    for r, a, b, lo, hi, _ in cy:
        m = [e for e in exp_h if abs(e[0] - r) < 0.005 and abs(e[1] - a) < 0.01 and abs(e[2] - b) < 0.01]
        detail.append((round(2 * r, 3), round(a, 3), round(b, 3), round(lo, 3), round(hi, 3)))
        ok_all &= len(m) == 1 and abs(lo - 0.0) < 1e-3 and abs(hi - 3.175) < 1e-3
    chk("1.4", "flat fin holes: Ø22.5 at (20.0, 21.0) and 4 x Ø3.4 at (20+-15.5, 21+-15.5), all through 0..3.175 (tol 0.01)",
        [(2 * e[0], e[1], e[2]) for e in exp_h], detail, 0.01, ok=ok_all)
    # hole in the fin vs the reference Heat_horn holes, measured on the reference file (relative to the outline corner, residual-free)
    ref_cy = merged_cyl(horn_ref, 1)
    dev = []
    for r, a, b, lo, hi, _ in ref_cy:
        # reference axis is (x, z); flat is (X = x + 20 - RES.x, Y = z + 18.36 - RES.z)
        X, Y = a - RES.x + 20.0, b - RES.z + 18.36
        m = [c for c in cy if abs(c[0] - r) < 0.005 and abs(c[1] - X) < 0.01 and abs(c[2] - Y) < 0.01]
        dev.append(len(m) == 1)
    chk("1.4b", "every Heat_horn reference hole has a matching hole (same Ø, centre within 0.01) in the flat fin", "5/5", f"{sum(dev)}/{len(ref_cy)}", 0, ok=all(dev) and len(ref_cy) == 5)
    # holes on the asm copies (centre vs motor axis x 0, z 2.64 design frame)
    for nm, s in (("asm 1p8", a18), ("asm 0p019", a019)):
        cyy = merged_cyl(s, 1)
        okh = len(cyy) == 5
        lst = []
        for r, a, b, lo, hi, _ in cyy:
            xd, zd = a - O.x - RES.x, b - O.z - RES.z
            lst.append((round(2 * r, 3), round(xd, 3), round(zd, 3)))
            okh &= (abs(r - 11.25) < 0.005 and abs(xd) < 0.01 and abs(zd - 2.64) < 0.01) or (abs(r - 1.7) < 0.005 and abs(abs(xd) - 15.5) < 0.01 and abs(abs(zd - 2.64) - 15.5) < 0.01)
        chk("1.4c", f"{nm}: hole centres in the station frame (Ø22.5 on x 0 / z 2.64; Ø3.4 on 31 mm square)", "5 holes", lst, 0.01, ok=okh)
    # asm copy coincident with the original assembly's Heat_horn on y = 0
    f_asm = [f for f in a18.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y) > 0.999 and f.Center().y > bbox6(a18)[2] + 1 and f.Area() > 5000][0]
    f_orig = [f for f in horn_asm.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y) > 0.999 and f.Center().y > bbox6(horn_asm)[2] + 1 and f.Area() > 5000][0]
    common = f_asm.intersect(f_orig)
    chk("1.5a", "asm 1p8 y=0 face plane y vs original assembly Heat_horn y=0 face (mm)", f_orig.Center().y, f_asm.Center().y, 1e-4)
    chk("1.5b", "asm 1p8 y=0 face area (mm2) vs original face", f_orig.Area(), f_asm.Area(), 0.01)
    chk("1.5c", "common area of the two faces (mm2) = full original face", f_orig.Area(), common.Area(), 0.05)
    s019 = [f for f in a019.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y) > 0.999 and f.Center().y > bbox6(a019)[2] + 0.2 and f.Area() > 5000][0]
    chk("1.5d", "asm 0p019 y=0 face plane y vs original assembly Heat_horn y=0 face (mm)", f_orig.Center().y, s019.Center().y, 1e-4)
    chk("1.5e", "asm 0p019 common face area with original y=0 face (mm2)", f_orig.Area(), s019.intersect(f_orig).Area(), 0.05)
    # the fin must not stick through the original Heat_horn in x/z beyond its outline (outline coincident): symmetric difference of the y = 0 faces
    chk("1.5f", "asm 1p8: fin y=0 face minus original face, and original minus fin (mm2)", 0.0, f_asm.cut(f_orig).Area() + f_orig.cut(f_asm).Area(), 0.05)
    # volume = area x t
    for nm, s, t in (("flat 1p8", flat, T_PROD), ("asm 1p8", a18, T_PROD), ("asm 0p019", a019, T_PROTO)):
        chk("1.6", f"{nm}: volume = reference face area x t (mm3)", area_ref * t, s.Volume(), 0.01)
    # --- STL
    tri, nrm = read_stl(STL / "heat_fin1021_1p8.stl")
    vol, area = stl_volume_area(tri)
    mb = (tri[:, :, 0].min(), tri[:, :, 0].max(), tri[:, :, 1].min(), tri[:, :, 1].max(), tri[:, :, 2].min(), tri[:, :, 2].max())
    chk("1.7a", "STL bbox == flat STEP bbox (max abs diff, mm)", 0.0, max(abs(a - b) for a, b in zip(mb, fb)), 0.002)
    chk("1.7b", "STL (mesh) volume vs STEP volume (relative; tessellated holes, tol 0.3 %)", 0.0, abs(vol - flat.Volume()) / flat.Volume(), 0.003)
    wt, bad = stl_watertight(tri)
    chk("1.7c", "STL closed manifold (edges not shared by exactly 2 triangles)", 0, bad, 0)
    flat_area = sum(f.Area() for f in flat.Faces())
    chk("1.7d", "STL surface area vs STEP surface area (relative, tol 0.3 %)", 0.0, abs(area - flat_area) / flat_area, 0.003)
    # sample STL vertices -> distance to the STEP solid
    rng = np.random.default_rng(1)
    verts = np.unique(np.round(tri.reshape(-1, 3), 5), axis=0)
    pick = verts[rng.choice(len(verts), size=min(250, len(verts)), replace=False)]
    dmax = max(cq.Vertex.makeVertex(*p).distance(flat) for p in pick)
    chk("1.7e", "STL vertices lie on the STEP surface (max distance of 250 sampled vertices, mm)", 0.0, dmax, 0.002)
    outward = all(np.dot(np.cross(t[1] - t[0], t[2] - t[0]), n) >= -1e-6 for t, n in zip(tri, nrm))
    chk("1.7f", "STL facet normals agree with the winding", True, outward, 0, ok=bool(outward))
    # --- DXF
    import ezdxf
    doc = ezdxf.readfile(str(DXF / "heat_fin1021_1p8_profile.dxf"))
    msp = doc.modelspace()
    kinds = {}
    for e in msp:
        kinds[e.dxftype()] = kinds.get(e.dxftype(), 0) + 1
    insunits = doc.header.get("$INSUNITS", 0)
    chk("1.8a", "DXF units ($INSUNITS 4 = mm)", 4, insunits, 0)
    polys = [e for e in msp if e.dxftype() in ("LWPOLYLINE", "POLYLINE")]
    circles = [e for e in msp if e.dxftype() == "CIRCLE"]
    chk("1.8b", "DXF entities: 1 closed outline polyline + 5 circles", "1 poly + 5 circles", f"{len(polys)} poly + {len(circles)} circles {kinds}", 0, ok=len(polys) == 1 and len(circles) == 5)
    pts = [(round(p[0], 4), round(p[1], 4)) for p in polys[0].get_points("xy")] if polys else []
    outline = {(0.0, 0.0), (42.0, 0.0), (42.0, 228.6), (0.0, 195.6)}
    chk("1.8c", "DXF outline vertices == flat-frame outline", sorted(outline), sorted(pts), 0.005,
        ok=len(pts) == 4 and all(any(abs(p[0] - q[0]) < 0.005 and abs(p[1] - q[1]) < 0.005 for q in outline) for p in pts) and bool(polys[0].closed))
    dc = sorted((round(2 * c.dxf.radius, 3), round(c.dxf.center.x, 3), round(c.dxf.center.y, 3)) for c in circles)
    fc = sorted((round(2 * r, 3), round(a, 3), round(b, 3)) for r, a, b, *_ in cy)
    chk("1.8d", "DXF circles (Ø, X, Y) == flat STEP holes (tol 0.005)", fc, dc, 0.005, ok=len(dc) == len(fc) and all(all(abs(u - v) < 0.005 for u, v in zip(p, q)) for p, q in zip(dc, fc)))
    poly_area = 0.5 * abs(sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))) if len(pts) == 4 else -1
    net = poly_area - sum(math.pi * c.dxf.radius ** 2 for c in circles)
    chk("1.8e", "DXF net area (outline - holes) vs STEP face area (mm2)", area_ref, net, 0.05)
    return dict(area_ref=area_ref)



# ================================================================ shared pieces for the station checks
Y0 = O.y + RES.y                 # tab face (design y = 0) in assembly coordinates, incl. the extraction residual
X0 = O.x + RES.x                 # motor axis x
Z0 = O.z + P.ENC1021_REF_SHIFT_Z + RES.z   # motor axis z (design 2.64)
BLOCK_NAMES = ["motor_block", "fin_in", "fin_out", "slipin_mount", "screw_1", "screw_2", "screw_3", "screw_4",
               "insert_deck", "insert_enc_1", "insert_enc_2", "insert_enc_3", "insert_enc_4"]
DETAIL_NAMES = ["front_cap", "stator", "winding", "rear_cap", "shaft", "connector"] + BLOCK_NAMES[1:]
VARIANTS = (("fin1p8", T_PROD, BLOCK_NAMES), ("fin0p019", T_PROTO, BLOCK_NAMES), ("detailed_fin1p8", T_PROD, DETAIL_NAMES))


def contact_area(a: cq.Shape, b: cq.Shape) -> float:
    """Face-to-face contact area from the surface-area bookkeeping of a fuse: (A_a + A_b - A_fused) / 2 (valid for touching, non-overlapping solids)."""
    fa = lambda s: sum(f.Area() for f in s.Faces())  # noqa: E731
    return (fa(a) + fa(b) - fa(a.fuse(b))) / 2.0


def overlap_vol(a: cq.Shape, b: cq.Shape) -> float:
    return a.intersect(b).Volume()


def bb_near(a: cq.Shape, b: cq.Shape, tol=0.01) -> bool:
    A, B = bbox6(a), bbox6(b)
    return all(A[2 * i] <= B[2 * i + 1] + tol and B[2 * i] <= A[2 * i + 1] + tol for i in range(3))


_STATION_CACHE: dict = {}


def station(key: str) -> dict:
    if key not in _STATION_CACHE:
        n = named(STEP / f"thermal_station1021_{key}.step")
        n.pop("__duplicates__", None)
        _STATION_CACHE[key] = n
    return _STATION_CACHE[key]


def section2():
    ref_motor = [s for s in load(REF / "Motor_Reference.step").Solids() if s.Volume() > 60000][0].translate(O)
    ref_slip = load(REF / "Slipin_mount_piecev3.step").translate(O)
    fin_asm = {"fin1p8": load(STEP / "heat_fin1021_1p8_asm1021.step"), "fin0p019": load(STEP / "heat_fin1021_0p019_asm1021.step")}
    fin_asm["detailed_fin1p8"] = fin_asm["fin1p8"]
    area_ref = fin_asm["fin1p8"].Volume() / T_PROD
    for key, t, names in VARIANTS:
        tag = f"[{key}]"
        path = STEP / f"thermal_station1021_{key}.step"
        raw = named(path)
        dup = raw.pop("__duplicates__")
        b = raw
        chk("2.1a", f"{tag} component names == spec list ({len(names)} bodies)", sorted(names), sorted(b), 0, ok=sorted(b) == sorted(names) and not dup)
        chk("2.1b", f"{tag} component count / duplicate names", f"{len(names)} / none", f"{len(b)} / {dup or 'none'}", 0, ok=len(b) == len(names) and not dup)
        whole = load(path)
        chk("2.1c", f"{tag} every component = one valid solid; whole file solid count = component count", f"{len(names)} solids, all valid",
            f"{len(whole.Solids())} solids; valid={all(is_valid(s) for s in b.values())}; solids per component={sorted({len(s.Solids()) for s in b.values()})}", 0,
            ok=len(whole.Solids()) == len(names) and all(len(s.Solids()) == 1 and is_valid(s) for s in b.values()))
        # ---- overlaps (all pairs)
        worst, worst_pair, npairs, touching = 0.0, None, 0, []
        items = sorted(b.items())
        for (na, sa), (nb, sb) in itertools.combinations(items, 2):
            if not bb_near(sa, sb):
                continue
            npairs += 1
            v = overlap_vol(sa, sb)
            if v > worst:
                worst, worst_pair = v, (na, nb)
            if sa.distance(sb) < 1e-6:
                touching.append((na, nb))
        chk("2.2", f"{tag} max pairwise overlap volume over {len(items) * (len(items) - 1) // 2} pairs ({npairs} bbox-near) (mm3, limit 0.01)", 0.0, worst, 0.01, note=f"worst pair {worst_pair}")
        # ---- slip-in unchanged vs the reference
        chk("2.3a", f"{tag} slipin_mount == reference Slipin_mount_piecev3 (+O): volume and symmetric difference (mm3)", 0.0,
            abs(b["slipin_mount"].Volume() - ref_slip.Volume()) + b["slipin_mount"].cut(ref_slip).Volume() + ref_slip.cut(b["slipin_mount"]).Volume(), 0.01)
        # ---- fin halves
        fi, fo = b["fin_in"], b["fin_out"]
        whole_fin = fin_asm[key]
        chk("2.4a", f"{tag} fin_in + fin_out volume == whole fin (mm3)", whole_fin.Volume(), fi.Volume() + fo.Volume(), 0.01)
        chk("2.4b", f"{tag} fin_in U fin_out == exported whole fin: symmetric difference (mm3)", 0.0, fi.fuse(fo).cut(whole_fin).Volume() + whole_fin.cut(fi.fuse(fo)).Volume(), 0.01)
        zsplit = bbox6(fi)[5] - O.z
        chk("2.4c", f"{tag} split plane z, from fin_in top (station frame, spec 31.16 +- 0.05)", 31.16, zsplit, 0.05)
        chk("2.4d", f"{tag} fin_out bottom == fin_in top (mm)", 0.0, abs(bbox6(fo)[4] - bbox6(fi)[5]), 1e-4)
        chk("2.4e", f"{tag} split contact area fin_in/fin_out = 42 x t (mm2)", 42.0 * t, contact_area(fi, fo), 0.01)
        cyfi = merged_cyl(fi, 1)
        chk("2.4f", f"{tag} fin_in holds all 5 holes, fin_out none", "5 / 0", f"{len(cyfi)} / {len(merged_cyl(fo, 1))}", 0, ok=len(cyfi) == 5 and len(merged_cyl(fo, 1)) == 0)
        # ---- motor placement
        if key != "detailed_fin1p8":
            mb = b["motor_block"]
            shift = bbox6(mb)[3] - bbox6(ref_motor)[3]
            chk("2.5a", f"{tag} motor_block shift along y vs Motor_Reference block (mm; expected 2.0 - t)", 2.0 - t, shift, 0.002)
            chk("2.5b", f"{tag} motor_block shifts only in y (x, z extents and y length unchanged)", 0.0,
                max(abs(bbox6(mb)[i] - bbox6(ref_motor)[i]) for i in (0, 1, 4, 5)) + abs((bbox6(mb)[3] - bbox6(mb)[2]) - (bbox6(ref_motor)[3] - bbox6(ref_motor)[2])), 0.002)
            moved = ref_motor.translate(cq.Vector(0, shift, 0))
            chk("2.5c", f"{tag} motor_block == shifted reference block minus 4 holes: reference-minus-built volume (mm3; 4 x pi x 1.5^2 x 4 = 113.097) and built-minus-reference (0)",
                "113.097 / 0.000", f"{moved.cut(mb).Volume():.3f} / {mb.cut(moved).Volume():.3f}", 0.01, ok=abs(moved.cut(mb).Volume() - 113.097) < 0.01 and mb.cut(moved).Volume() < 0.01)
            mh = [c for c in merged_cyl(mb, 1)]
            exp = sorted((1.5, X0 + sx * 15.5, Z0 + sz * 15.5) for sx in (-1, 1) for sz in (-1, 1))
            okm = len(mh) == 4 and all(abs(r - 1.5) < 0.005 and abs(hi - lo - 4.0) < 1e-3 and abs(hi - bbox6(mb)[3]) < 1e-3 for r, a, bz, lo, hi, _ in mh) \
                and all(abs(m[1] - e[1]) < 0.01 and abs(m[2] - e[2]) < 0.01 for m, e in zip(sorted((r, a, bz) for r, a, bz, *_ in mh), exp))
            chk("2.5d", f"{tag} motor_block: 4 x Ø3.0 x 4.0 deep holes in the front face on the 31 mm square about the axis", "4 holes Ø3.0 depth 4.0", [(round(2 * r, 3), round(a - X0, 3), round(bz - Z0, 3), round(hi - lo, 3)) for r, a, bz, lo, hi, _ in mh], 0.01, ok=okm)
            front_y = bbox6(mb)[3]
        else:
            front_y = bbox6(b["front_cap"])[3] - 2.0     # boss is 2.0 proud of the front face
            ref_front = bbox6(ref_motor)[3]
            chk("2.5a", f"{tag} motor front face moves by 2.0 - t relative to Motor_Reference (mm)", 2.0 - t, front_y - ref_front, 0.002)
        chk("2.5e", f"{tag} motor front face y == fin motor-side face (-t from the tab face) (mm)", Y0 - t, front_y, 0.002)
        # ---- screws
        tab_hole = {(round(a - X0, 1), round(bz - Z0, 1)): (r, lo, hi) for r, a, bz, lo, hi, _ in merged_cyl(b["slipin_mount"], 1) if abs(r - 1.75) < 0.01}
        fin_hole = {(round(a - X0, 1), round(bz - Z0, 1)): r for r, a, bz, lo, hi, _ in cyfi if abs(r - 1.7) < 0.01}
        tab_face_y = max(v[2] for v in tab_hole.values())
        chk("2.6a", f"{tag} tab spool-side face y == 5.0 (design), from the 4 tab holes (Ø3.5) (mm)", Y0 + 5.0, tab_face_y, 0.002, ok=None)
        order = {1: (-1, -1), 2: (1, -1), 3: (-1, 1), 4: (1, 1)}
        okpos = okhead = oktip = okcoax = okshare = True
        info = []
        eng = []
        for n in (1, 2, 3, 4):
            s = b[f"screw_{n}"]
            sx, sz = order[n]
            cs = merged_cyl(s, 1)
            head = [c for c in cs if abs(c[0] - 2.75) < 0.005]
            shank = [c for c in cs if abs(c[0] - 1.5) < 0.005]
            okpos &= len(head) == 1 and len(shank) == 1
            h, k = head[0], shank[0]
            ex, ez = X0 + sx * 15.5, Z0 + sz * 15.5
            okpos &= abs(h[1] - ex) < 0.01 and abs(h[2] - ez) < 0.01 and abs(k[1] - ex) < 0.01 and abs(k[2] - ez) < 0.01
            okhead &= abs(h[3] - (Y0 + 5.0)) < 2e-3 and abs(h[4] - (Y0 + 8.0)) < 2e-3 and abs(h[3] - tab_face_y) < 1e-4
            tip_exp = (Y0 - t - 4.0) if key != "detailed_fin1p8" else (Y0 - 7.0)
            oktip &= abs(k[3] - tip_exp) < 2e-3 and abs(k[4] - (Y0 + 5.0)) < 2e-3
            okcoax &= max(abs(h[1] - k[1]), abs(h[2] - k[2])) < 1e-6
            eng.append(round((Y0 - t) - k[3], 4))
            info.append((n, round(h[3] - Y0, 4), round(h[4] - Y0, 4), round(k[3] - Y0, 4)))
        chk("2.6b", f"{tag} screws 1..4 at (+-15.5, 2.64+-15.5) in the order 1(-x,-z) 2(+x,-z) 3(-x,+z) 4(+x,+z); head Ø5.5 + shank Ø3.0", "all 4", info, 0.01, ok=okpos)
        chk("2.6c", f"{tag} screw heads on the tab spool-side face: head y 5.0 .. 8.0 and head underside == tab face (mm)", "5.0..8.0", [(i[0], i[1], i[2]) for i in info], 0.002, ok=okhead)
        tip_note = "block variant: shank 4.0 mm into the Ø3.0 x 4.0 holes" if key != "detailed_fin1p8" else "detailed: M3 x 12, shank tip y = -7.0"
        chk("2.6d", f"{tag} shank tip y (design): {tip_note}", (-t - 4.0) if key != "detailed_fin1p8" else -7.0, [i[3] for i in info], 0.002, ok=oktip)
        chk("2.6e", f"{tag} shank and head coaxial (mm)", 0.0, 0.0, 1e-6, ok=okcoax)
        chk("2.7a", f"{tag} thread/shank engagement behind the fin motor face = tip depth below -t (mm)", 3.825 if key == "detailed_fin1p8" else 4.0, eng, 0.002, ok=all(abs(e - (3.825 if key == "detailed_fin1p8" else 4.0)) < 0.002 for e in eng))
        if key == "detailed_fin1p8":
            under_head = [(Y0 + 5.0) - min(c[3] for c in merged_cyl(b[f"screw_{n}"], 1) if abs(c[0] - 1.5) < 0.005) for n in (1, 2, 3, 4)]
            chk("2.7b", f"{tag} screw length under the head = M3 x 12 (mm) -> 5 (tab) + 3.175 (fin) + 3.825 (engagement)", 12.0, under_head, 0.002, ok=all(abs(u - 12.0) < 0.002 for u in under_head))
        # screw/hole radial relations and no overlap with fin/tab/motor
        gaps_fin, gaps_tab, ovl, share = [], [], [], []
        for n in (1, 2, 3, 4):
            s = b[f"screw_{n}"]
            sx, sz = order[n]
            key_xz = (sx * 15.5, sz * 15.5)
            kk = (round(key_xz[0], 1), round(key_xz[1], 1))
            shank_faces = [c["face"] for c in cylinders(s) if abs(c["r"] - 1.5) < 0.005]
            tab_f = [c["face"] for c in cylinders(b["slipin_mount"]) if abs(c["r"] - 1.75) < 0.01 and abs(c["p"][0] - (X0 + sx * 15.5)) < 0.01 and abs(c["p"][2] - (Z0 + sz * 15.5)) < 0.01]
            fin_f = [c["face"] for c in cylinders(fi) if abs(c["r"] - 1.7) < 0.01 and abs(c["p"][0] - (X0 + sx * 15.5)) < 0.01 and abs(c["p"][2] - (Z0 + sz * 15.5)) < 0.01]
            gaps_tab.append(round(min(sf.distance(tf) for sf in shank_faces for tf in tab_f), 4))
            gaps_fin.append(round(min(sf.distance(ff) for sf in shank_faces for ff in fin_f), 4))
            ovl.append(max(overlap_vol(s, fi), overlap_vol(s, b["slipin_mount"]), overlap_vol(s, b["fin_out"])))
        chk("2.8a", f"{tag} shank-to-fin-hole radial gap (Ø3.4 vs Ø3.0 -> 0.200) (mm)", 0.2, gaps_fin, 0.002, ok=all(abs(g - 0.2) < 0.002 for g in gaps_fin))
        chk("2.8b", f"{tag} shank-to-tab-hole radial gap (Ø3.5 vs Ø3.0 -> 0.250) (mm)", 0.25, gaps_tab, 0.002, ok=all(abs(g - 0.25) < 0.002 for g in gaps_tab))
        chk("2.8c", f"{tag} screw overlap with fin_in / fin_out / slipin_mount (mm3, limit 0.01)", 0.0, max(ovl), 0.01)
        chk("2.8d", f"{tag} screw to fin_in minimum distance (mm; 0.2 radial gap, no contact)", 0.2, [round(b[f'screw_{n}'].distance(fi), 4) for n in (1, 2, 3, 4)], 0.002,
            ok=all(abs(b[f"screw_{n}"].distance(fi) - 0.2) < 0.002 for n in (1, 2, 3, 4)))
        # shank vs motor holes
        mot = b["motor_block"] if key != "detailed_fin1p8" else b["front_cap"]
        mo = [overlap_vol(b[f"screw_{n}"], mot) for n in (1, 2, 3, 4)]
        chk("2.8e", f"{tag} screw / motor-hole overlap volume (mm3, limit 0.01)", 0.0, max(mo), 0.01)
        ca = [contact_area(b[f"screw_{n}"], mot) for n in (1, 2, 3, 4)]
        cexp = (math.pi * 3.0 * 4.0 + math.pi * 1.5 ** 2) if key != "detailed_fin1p8" else (math.pi * 3.0 * 3.825)
        chk("2.8f", f"{tag} screw-to-motor contact area (mm2): " + ("cylinder Ø3 x 4 + end face (shared)" if key != "detailed_fin1p8" else "cylinder Ø3 x 3.825, 0.675 air under the tip"), cexp, [round(c, 3) for c in ca], 0.05, ok=all(abs(c - cexp) < 0.05 for c in ca))
        if key == "detailed_fin1p8":
            hs = [(r, lo, hi) for r, a, bz, lo, hi, _ in merged_cyl(b["front_cap"], 1) if abs(r - 1.5) < 0.005]
            chk("2.8g", f"{tag} front_cap tapped holes: 4 x Ø3.0, depth 4.5 (so the M3 x 12 tip stops 0.675 short of the bottom)", "4 x depth 4.5", [(round(2 * r, 3), round(hi - lo, 3)) for r, lo, hi in hs], 0.002,
                ok=len(hs) == 4 and all(abs(hi - lo - 4.5) < 0.002 for r, lo, hi in hs))
        # ---- inserts
        sl = b["slipin_mount"]
        dk = b["insert_deck"]
        pk = [c for c in merged_cyl(sl, 2) if abs(c[0] - 2.05) < 0.005]
        sk = merged_cyl(dk, 2)
        okd = len(pk) == 1 and len(sk) == 2
        top_probe_out = not probe_inside(sl, (pk[0][1], pk[0][2] + 2.9, pk[0][4] + 0.2))      # air above the deck face next to the pocket ... (point 2.9 mm off-axis in +y)
        deck_in = probe_inside(sl, (pk[0][1], pk[0][2] + 2.9, pk[0][4] - 0.3))                 # material below the deck face next to the pocket
        osl = [c for c in sk if abs(c[0] - 2.05) < 0.005][0]
        bor = [c for c in sk if abs(c[0] - 1.25) < 0.005][0]
        okd &= abs(osl[1] - pk[0][1]) < 1e-3 and abs(osl[2] - pk[0][2]) < 1e-3
        chk("2.9a", f"{tag} insert_deck: OD 4.1 / ID 2.5 / length 5.7 (mm)", (4.1, 2.5, 5.7), (round(2 * osl[0], 3), round(2 * bor[0], 3), round(osl[4] - osl[3], 3)), 0.005, ok=okd and abs(osl[4] - osl[3] - 5.7) < 0.005 and abs(bor[4] - bor[3] - 5.7) < 0.005)
        chk("2.9b", f"{tag} insert_deck coaxial with the slip-in pocket Ø4.1 (axis offset, mm)", 0.0, round(max(abs(osl[1] - pk[0][1]), abs(osl[2] - pk[0][2])), 5), 1e-3)
        chk("2.9c", f"{tag} insert_deck top flush with the deck face (pocket opening) (mm); deck face is at the pocket top: air above, material beside", pk[0][4], osl[4], 1e-3, ok=abs(osl[4] - pk[0][4]) < 1e-3 and top_probe_out and deck_in)
        chk("2.9d", f"{tag} insert_deck inside the pocket depth (sleeve bottom above pocket floor by 7.0 - 5.7 = 1.3 mm)", 1.3, osl[3] - pk[0][3], 1e-3)
        ca = contact_area(dk, sl)
        chk("2.9e", f"{tag} insert_deck / slipin contact = outer cylinder pi x 4.1 x 5.7 (mm2); distance 0", math.pi * 4.1 * 5.7, ca, 0.05, ok=abs(ca - math.pi * 4.1 * 5.7) < 0.05 and dk.distance(sl) < 1e-6)
        chk("2.9f", f"{tag} insert_deck overlap with slipin_mount (mm3)", 0.0, overlap_vol(dk, sl), 0.01)
        divots = sorted((a, bz, lo, hi) for r, a, bz, lo, hi, _ in merged_cyl(sl, 0) if abs(r - 1.725) < 0.005)
        okE, listE = len(divots) == 4, []
        for i in (1, 2, 3, 4):
            ins = b[f"insert_enc_{i}"]
            mc = merged_cyl(ins, 0)
            o1 = [c for c in mc if abs(c[0] - 1.725) < 0.005]
            o2 = [c for c in mc if abs(c[0] - 1.05) < 0.005]
            okE &= len(o1) == 1 and len(o2) == 1
            m = [d for d in divots if abs(d[0] - o1[0][1]) < 1e-3 and abs(d[1] - o1[0][2]) < 1e-3]
            okE &= len(m) == 1 and abs(m[0][2] - o1[0][3]) < 1e-3 and abs(m[0][3] - o1[0][4]) < 1e-3 and abs(o1[0][4] - o1[0][3] - 4.0) < 1e-3
            listE.append((i, round(2 * o1[0][0], 3), round(2 * o2[0][0], 3), round(o1[0][4] - o1[0][3], 3), round(o1[0][1] - Y0, 3), round(o1[0][2] - Z0, 3)))
            okE &= overlap_vol(ins, sl) < 0.01 and ins.distance(sl) < 1e-6
        chk("2.9g", f"{tag} insert_enc_1..4: OD 3.45 / ID 2.1 / length 4.0, coaxial with the 4 divot holes (same x range, flush with the divot floor), no overlap", "4 sleeves in 4 holes", listE, 0.001, ok=okE)
        # probe: divot floor is the open end
        d0 = divots[0]
        floor_air = not probe_inside(sl, (d0[3] + 0.2, d0[0], d0[1]))
        floor_mat = probe_inside(sl, (d0[3] - 0.2, d0[0] + 2.4, d0[1]))
        chk("2.9h", f"{tag} divot hole open at the divot floor (air at +0.2, material beside the hole at -0.2)", True, floor_air and floor_mat, 0, ok=floor_air and floor_mat)
        # ---- touching pairs vs builder CSV (informational comparison)
        out_pairs = sorted({tuple(sorted(p)) for p in touching})
        chk("2.10", f"{tag} touching pairs (distance < 1e-6) are listed", "list", out_pairs, 0, ok=True)
        STATION_TOUCH[key] = out_pairs
    return {}


STATION_TOUCH: dict = {}




def section2b():
    """Cross-checks of the thermal STEPs against the builder's contact CSV and against the shell / spool references."""
    import csv
    shell = load(REF / "Shell_Casing.step").translate(O)
    spool = load(REF / "Spool1011.step").translate(O)
    wall = [s for s in cq.importers.importStep(str(REF / "Wall_Mount_v3.step")).vals()][0].translate(O)
    # shell slot walls, measured on the shell file
    slot = sorted(f.Center().y for f in load(REF / "Shell_Casing.step").Faces()
                  if f.geomType() == "PLANE" and abs(f.normalAt().y) > 0.999 and 27 < f.BoundingBox().zmin < 28 and 31 < f.BoundingBox().zmax < 32 and f.BoundingBox().xmin < -20)
    top_z = max(f.BoundingBox().zmax for f in load(REF / "Shell_Casing.step").Faces()
                if f.geomType() == "PLANE" and abs(f.normalAt().y) > 0.999 and 27 < f.BoundingBox().zmin < 28 and 31 < f.BoundingBox().zmax < 32 and f.BoundingBox().xmin < -20)
    chk("2.11a", "shell fin-slot walls measured on Shell_Casing.step: y (file frame) and roof-plate top z", "y -2.690 / +2.310; top z 31.16 +- 0.05 (design)",
        f"y {slot[0]:.3f} / {slot[-1]:.3f}; top z {top_z - RES.z:.3f} (file {top_z:.4f})", 0.05, ok=len(slot) == 2 and abs(top_z - RES.z - 31.16) < 0.05 and abs(slot[0] + 2.69) < 0.01 and abs(slot[1] - 2.31) < 0.01,
        note="split plane z 31.16 agrees with the shell roof at the slot")
    chk("2.11b", "split plane (fin_in top, file frame) vs shell roof top at the slot (mm)", 0.0, (bbox6(station("fin1p8")["fin_in"])[5] - O.z) - top_z, 0.05)
    f18, f019 = station("fin1p8"), station("fin0p019")
    ov18 = sum(overlap_vol(f18[k], shell) for k in ("fin_in", "fin_out"))
    ov019 = sum(overlap_vol(f019[k], shell) for k in ("fin_in", "fin_out"))
    chk("2.11c", "1/8 in fin vs shell (finding F1: motor-side slot wall overlaps the fin) (mm3; builder 68.94)", 68.94, ov18, 1.0)
    chk("2.11d", "0.019 in fin vs shell (mm3)", 0.0, ov019, 0.01)
    # motor / slipin vs shell, spool
    for key in ("fin1p8", "fin0p019", "detailed_fin1p8"):
        b = station(key)
        mot = [n for n in b if n in ("motor_block", "front_cap", "stator", "winding", "rear_cap", "shaft", "connector")]
        dist = min(b[n].distance(shell) for n in mot if n != "shaft")
        chk("2.11e", f"[{key}] motor bodies (excl. shaft) minimum distance to the shell (mm; builder: 1.9)", 1.9, round(dist, 4), 0.05)
        chk("2.11f", f"[{key}] overlap of slipin_mount / inserts / screws / motor bodies with the shell (mm3)", 0.0, max(overlap_vol(b[n], shell) for n in b if not n.startswith("fin")), 0.01)
    # shaft vs spool bore in the detailed station
    d = station("detailed_fin1p8")
    chk("2.11g", "[detailed_fin1p8] shaft / spool overlap and shaft end y (design; expected 20.825) (mm3 / mm)", "0 / 20.825",
        f"{overlap_vol(d['shaft'], spool):.5f} / {bbox6(d['shaft'])[3] - Y0:.4f}", 0.01, ok=overlap_vol(d["shaft"], spool) < 0.01 and abs(bbox6(d["shaft"])[3] - Y0 - 20.825) < 0.005)
    shaft_in_bore = bbox6(d["shaft"])[3] - Y0 - 7.0
    chk("2.11h", "[detailed_fin1p8] shaft engagement in the spool bore (y 7 .. shaft end) (mm; spec 13.8)", 13.8, round(shaft_in_bore, 3), 0.05)
    # contact CSV (builder) vs my fuse-area measurement
    for key in ("fin1p8", "fin0p019", "detailed_fin1p8"):
        rows = {}
        with open(ROOT / "renders" / "thermal_station1021" / f"thermal_station1021_{key}_contacts.csv") as fh:
            for line in csv.reader(fh):
                if not line or line[0].startswith("near gaps") or line[0] == "body A":
                    continue
                if len(line) >= 3 and line[2].replace(".", "", 1).isdigit():
                    rows[tuple(sorted(line[:2]))] = float(line[2])
        b = station(key)
        pairs = set(STATION_TOUCH.get(key, []))
        okc = pairs == set(rows)
        worst = 0.0
        worst_pair = None
        for pr in sorted(pairs & set(rows)):
            a = contact_area(b[pr[0]], b[pr[1]])
            dd = abs(a - rows[pr])
            if dd > worst:
                worst, worst_pair = dd, pr
        chk("2.12", f"[{key}] touching pairs and contact areas: my {len(pairs)} touching pairs vs the builder's {len(rows)}-row contact CSV (set equality; worst area difference mm2)",
            "same pairs, areas within 0.01", f"same set={okc}; extra mine={sorted(pairs - set(rows))}; missing={sorted(set(rows) - pairs)}; worst |dA|={worst:.4f} {worst_pair}", 0.01, ok=okc and worst < 0.01)
    # body-table CSV volumes
    for key in ("fin1p8", "fin0p019", "detailed_fin1p8"):
        b = station(key)
        with open(ROOT / "renders" / "thermal_station1021" / f"thermal_station1021_{key}_bodies.csv") as fh:
            rd = [r for r in csv.reader(fh)]
        tab = {r[0]: float(r[4]) for r in rd[1:] if r and r[0] not in ("total", "") and r[4]}
        dev = max(abs(tab[k] - b[k].Volume()) for k in tab if k in b)
        chk("2.13", f"[{key}] body table volumes vs measured (max |dV| mm3, over {len(tab)} rows; every body listed={set(tab) == set(b)})", 0.0, dev, 0.01, ok=dev < 0.01 and set(tab) == set(b))
    # engagement arithmetic of the claims (screw length - tab - fin)
    for L, t, label in ((12, 3.175, "M3x12 + 1/8 in"), (8, 0.483, "M3x8 + 0.019 in"), (10, 0.483, "M3x10 + 0.019 in")):
        eng = L - 5.0 - t
        chk("2.14", f"engagement arithmetic {label} = L - 5 (tab) - t (mm)", {"M3x12 + 1/8 in": 3.825, "M3x8 + 0.019 in": 2.517, "M3x10 + 0.019 in": 4.517}[label], round(eng, 3), 0.001)
    return {}


# ================================================================ SECTION 3: detailed NEMA 17
def section3():
    nm = named(STEP / "nema17_thermal.step")
    dup = nm.pop("__duplicates__")
    want = ["front_cap", "stator", "winding", "rear_cap", "shaft", "connector"]
    chk("3.1a", "nema17_thermal.step components", sorted(want), sorted(nm), 0, ok=sorted(nm) == sorted(want) and not dup)
    chk("3.1b", "each part: one valid solid, one shell", "6 x (1 solid, 1 shell, valid)", [(k, len(v.Solids()), len(v.Shells()), is_valid(v)) for k, v in nm.items()], 0,
        ok=all(len(v.Solids()) == 1 and len(v.Shells()) == 1 and is_valid(v) for v in nm.values()))
    fc, st, wd, rc, sh, cn = (nm[k] for k in want)
    for k in ("front_cap", "stator", "rear_cap"):
        bb = bbox6(nm[k])
        chk("3.2a", f"{k}: body 42.3 mm square (x and z extent) (mm)", (42.3, 42.3), (round(bb[1] - bb[0], 4), round(bb[5] - bb[4], 4)), 0.01, ok=abs(bb[1] - bb[0] - 42.3) < 0.01 and abs(bb[5] - bb[4] - 42.3) < 0.01)
    chk("3.2b", "body length: rear cap back face y -38; front cap boss end y +2 (front face y 0) (mm)", (-38.0, 2.0), (round(bbox6(rc)[2], 4), round(bbox6(fc)[3], 4)), 0.005,
        ok=abs(bbox6(rc)[2] + 38) < 0.005 and abs(bbox6(fc)[3] - 2.0) < 0.005)
    front_face = [f for f in fc.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y - 1) < 1e-6 and abs(f.Center().y) < 1e-6]
    chk("3.2c", "front face is at y = 0 (one planar face, boss and 4 holes cut out of it)", "1 face at y 0", len(front_face), 0, ok=len(front_face) == 1)
    # chamfers on the four long edges: probe a corner
    cham = all(not st.isInside(cq.Vector(sx * 20.5, -19, sz * 20.5), 1e-6) and st.isInside(cq.Vector(sx * 19.0, -19, sz * 19.0), 1e-6) for sx in (-1, 1) for sz in (-1, 1))
    chk("3.2d", "stator long edges chamfered 3 mm (corner point (20.5,20.5) outside, (19,19) inside, all 4 corners)", True, cham, 0, ok=cham)
    cf = [f.Area() for f in st.Faces() if f.geomType() == "PLANE" and abs(abs(f.normalAt().x) - math.sqrt(0.5)) < 1e-3 and abs(abs(f.normalAt().z) - math.sqrt(0.5)) < 1e-3]
    chk("3.2e", "stator chamfer faces: 4 x 3 sqrt2 x 22 (mm2)", 3 * math.sqrt(2) * 22, [round(a, 3) for a in cf], 0.05, ok=len(cf) == 4 and all(abs(a - 3 * math.sqrt(2) * 22) < 0.05 for a in cf))
    # tapped holes
    th = merged_cyl(fc, 1)
    taps = sorted((round(a, 3), round(b, 3), round(r, 3), round(hi - lo, 3)) for r, a, b, lo, hi, _ in th if abs(r - 1.5) < 0.005)
    exp = sorted((sx * 15.5, sz * 15.5, 1.5, 4.5) for sx in (-1, 1) for sz in (-1, 1))
    chk("3.3a", "front_cap: 4 tapped holes Ø3.0 x 4.5 deep on the 31 mm square (x, z, r, depth)", exp, taps, 0.005,
        ok=len(taps) == 4 and all(all(abs(u - v) < 0.005 for u, v in zip(p, q)) for p, q in zip(taps, exp)))
    chk("3.3b", "tap holes open at the front face (hole top y = 0, bottom y = -4.5)", (0.0, -4.5), sorted({(round(hi, 3), round(lo, 3)) for r, a, b, lo, hi, _ in th if abs(r - 1.5) < 0.005}), 0.005,
        ok=sorted({(round(hi, 3), round(lo, 3)) for r, a, b, lo, hi, _ in th if abs(r - 1.5) < 0.005}) == [(0.0, -4.5)])
    boss = [c for c in th if abs(c[0] - 11.0) < 0.005]
    chk("3.4", "front_cap pilot boss Ø22 on the axis, y 0 .. +2", "Ø22, y 0..2", [(round(2 * c[0], 3), round(c[1], 3), round(c[2], 3), round(c[3], 3), round(c[4], 3)) for c in boss], 0.005,
        ok=len(boss) == 1 and abs(boss[0][3]) < 0.005 and abs(boss[0][4] - 2.0) < 0.005 and abs(boss[0][1]) < 0.005 and abs(boss[0][2]) < 0.005)
    shf = merged_cyl(sh, 1)
    chk("3.5", "shaft Ø5.0, y -37 .. +24 (24 proud of the front face)", "Ø5, -37..24", [(round(2 * c[0], 3), round(c[3], 3), round(c[4], 3)) for c in shf], 0.005,
        ok=len(shf) == 1 and abs(shf[0][0] - 2.5) < 0.005 and abs(shf[0][3] + 37) < 0.005 and abs(shf[0][4] - 24) < 0.005 and abs(shf[0][1]) < 0.005 and abs(shf[0][2]) < 0.005)
    bores = [(round(2 * r, 3), round(lo, 2), round(hi, 2)) for r, a, b, lo, hi, _ in merged_cyl(fc, 1) if abs(r - 2.5) < 0.005] + [(round(2 * r, 3), round(lo, 2), round(hi, 2)) for r, a, b, lo, hi, _ in merged_cyl(rc, 1) if abs(r - 2.5) < 0.005]
    chk("3.6", "bores that carry the shaft: front cap Ø5.0 through (y -8..2), rear cap Ø5.0 blind seat y -37..-30", [(5.0, -8.0, 2.0), (5.0, -37.0, -30.0)], bores, 0.01,
        ok=sorted(bores) == sorted([(5.0, -8.0, 2.0), (5.0, -37.0, -30.0)]))
    cbb = bbox6(cn)
    chk("3.7", "connector 16 (z) x 6 (y) x 6 (x), x 21.15..27.15, y -38..-32, flush with the back face", ((21.15, 27.15), (-38, -32), (-8, 8)), (tuple(round(v, 3) for v in cbb[0:2]), tuple(round(v, 3) for v in cbb[2:4]), tuple(round(v, 3) for v in cbb[4:6])), 0.005,
        ok=all(abs(a - b) < 0.005 for a, b in zip(cbb, (21.15, 27.15, -38, -32, -8, 8))))
    stator_bore = [c for c in merged_cyl(st, 1) if abs(c[0] - 17.0) < 0.005]
    wi = merged_cyl(wd, 1)
    chk("3.8", "stator bore Ø34, winding annulus Ø23..Ø34 x 22 inside it", "bore Ø34; winding Ø23/Ø34, y -30..-8", (len(stator_bore), sorted((round(2 * c[0], 2), round(c[3], 2), round(c[4], 2)) for c in wi)), 0.005,
        ok=len(stator_bore) == 1 and sorted((round(2 * c[0], 2), round(c[3], 2), round(c[4], 2)) for c in wi) == [(23.0, -30.0, -8.0), (34.0, -30.0, -8.0)])
    # overlaps and contacts
    items = sorted(nm.items())
    worst, wp, contacts = 0.0, None, []
    for (na, sa), (nb, sb) in itertools.combinations(items, 2):
        v = overlap_vol(sa, sb)
        if v > worst:
            worst, wp = v, (na, nb)
        if sa.distance(sb) < 1e-6:
            contacts.append((na, nb, round(contact_area(sa, sb), 2)))
    chk("3.9a", "max pairwise overlap, 15 pairs, incl. the shaft-to-cap contact pairs (mm3, limit 0.01)", 0.0, worst, 0.01, note=f"worst {wp}")
    sc = {(a, b): c for a, b, c in contacts}
    chk("3.9b", "shaft-to-cap contact is surface contact: front_cap-shaft pi x 5 x 10 = 157.08, rear_cap-shaft pi x 5 x 7 + pi x 2.5^2 = 129.59 (mm2)", (157.08, 129.59),
        (sc.get(("front_cap", "shaft")), sc.get(("rear_cap", "shaft"))), 0.05, ok=abs(sc.get(("front_cap", "shaft"), 0) - 157.08) < 0.05 and abs(sc.get(("rear_cap", "shaft"), 0) - 129.59) < 0.05)
    chk("3.9c", "contact list (touching pairs, mm2)", "list", contacts, 0, ok=True)
    chk("3.9d", "shaft to winding distance (air around the shaft inside the stator; 17 - ... = 11.5 - 2.5 = 9.0 mm)", 9.0, round(sh.distance(wd), 4), 0.01)
    # mass / volume
    dens = {"front_cap": 2.74, "stator": 7.65, "winding": 5.0, "rear_cap": 2.74, "shaft": 7.85, "connector": 1.40}
    tot = sum(nm[k].Volume() * dens[k] / 1000 for k in nm)
    chk("3.10", "total mass with the table densities (g) vs 0.28 kg reference motor (builder: 288.15, +2.9 %)", 288.15, round(tot, 2), 0.1)
    # --- placement
    for key, t in (("fin1p8", T_PROD), ("fin0p019", T_PROTO)):
        asm = named(STEP / f"nema17_thermal_{key}_asm1021.step")
        asm.pop("__duplicates__")
        okp = sorted(asm) == sorted(want)
        mx = 0.0
        for k in want:
            a, m = bbox6(asm[k]), bbox6(nm[k])
            sh_ = (X0, Y0 - t, Z0)
            ex = (m[0] + sh_[0], m[1] + sh_[0], m[2] + sh_[1], m[3] + sh_[1], m[4] + sh_[2], m[5] + sh_[2])
            mx = max(mx, max(abs(u - v) for u, v in zip(a, ex)))
            okp &= abs(asm[k].Volume() - nm[k].Volume()) < 1e-3
        chk("3.11a", f"[{key}] nema17 asm1021 file = motor-frame model translated by (X0, Y0 - t, Z0) = front face on the fin motor face, axis on x 0 / z 2.64 (max bbox deviation mm)", 0.0, round(mx, 5), 0.01, ok=okp and mx < 0.01)
        chk("3.11b", f"[{key}] front face y (design) == -t; shaft end y (design) == 24 - t (mm)", (-t, 24 - t), (round(bbox6(asm['front_cap'])[3] - 2.0 - Y0, 4), round(bbox6(asm['shaft'])[3] - Y0, 4)), 0.003,
            ok=abs(bbox6(asm["front_cap"])[3] - 2.0 - Y0 + t) < 0.003 and abs(bbox6(asm["shaft"])[3] - Y0 - (24 - t)) < 0.003)
    # 1/8 in asm file == the motor bodies in the detailed station
    d = station("detailed_fin1p8")
    asm18 = named(STEP / "nema17_thermal_fin1p8_asm1021.step")
    asm18.pop("__duplicates__")
    dv = max(max(abs(u - v) for u, v in zip(bbox6(asm18[k]), bbox6(d[k]))) for k in want)
    chk("3.11c", "nema17_thermal_fin1p8_asm1021 == the six motor bodies of thermal_station1021_detailed_fin1p8 (max bbox deviation, mm)", 0.0, round(dv, 5), 0.002,
        ok=dv < 0.002 and all(abs(asm18[k].Volume() - d[k].Volume()) < 1e-3 for k in want))
    # the pilot boss against the fin and tab pilot holes, for both fin thicknesses
    slip = load(REF / "Slipin_mount_piecev3.step").translate(O)
    for key, t in (("fin1p8", T_PROD), ("fin0p019", T_PROTO)):
        asm = named(STEP / f"nema17_thermal_{key}_asm1021.step")
        asm.pop("__duplicates__")
        fin = load(STEP / ("heat_fin1021_1p8_asm1021.step" if key == "fin1p8" else "heat_fin1021_0p019_asm1021.step"))
        ovs = {"fin": overlap_vol(asm["front_cap"], fin), "slipin": max(overlap_vol(v, slip) for v in asm.values()), "boss end vs tab face (mm)": None}
        boss_end = bbox6(asm["front_cap"])[3] - Y0
        chk("3.12", f"[{key}] nema17 front cap boss in the fin pilot (Ø22.5) / tab pilot (Ø22.4): overlap with fin and slip-in (mm3); boss end y (design)", "0 / 0",
            f"fin {ovs['fin']:.5f} / slipin {ovs['slipin']:.5f}; boss end y {boss_end:.3f} (fin tab-side face at y 0, tab pilot r 11.2 vs boss r 11)", 0.01, ok=ovs["fin"] < 0.01 and ovs["slipin"] < 0.01)
    # rebuild check: files current with the builder
    from cad.parts import nema17_thermal as N
    nb = N.make_bodies()
    chk("3.13", "nema17_thermal.step volumes == fresh build_bodies() (max |dV| mm3; the builder's own code, only a currency check)", 0.0, max(abs(nb[k].Volume() - nm[k].Volume()) for k in want), 0.01)
    return {}


# ================================================================ SECTION 4: Ø4 caps
def section4():
    names = {"std": "encoder1021_magnet_cap_v2_m4", "short": "encoder1021_magnet_cap_v2_m4_peg1p9"}
    exp_end = {"std": 22.6, "short": 24.1}
    exp_vol = {"std": 531.94, "short": 502.31}
    caps = {k: load(STEP / f"{v}.step") for k, v in names.items()}
    caps_asm = {k: load(STEP / f"{v}_asm1021.step") for k, v in names.items()}
    off = cq.Vector(X0, Y0, Z0)          # station-frame cap file -> assembly
    for k in ("std", "short"):
        c, a = caps[k], caps_asm[k]
        chk("4.1", f"[{k}] station-frame cap: one valid solid", "1 solid, valid", f"{len(c.Solids())} solid, valid={is_valid(c)}, shells={len(c.Shells())}", 0, ok=len(c.Solids()) == 1 and is_valid(c) and len(c.Shells()) == 1)
        chk("4.2", f"[{k}] cap volume (mm3; build notes)", exp_vol[k], round(c.Volume(), 3), 0.05)
        bb = bbox6(c)
        chk("4.3a", f"[{k}] peg end y (mm; station frame)", exp_end[k], bb[2], 0.01)
        chk("4.3b", f"[{k}] head: Ø14 x ... magnet face at y 29.3 (bbox x, z = +-7; y max 29.3)", (14.0, 14.0, 29.3), (round(bb[1] - bb[0], 3), round(bb[5] - bb[4], 3), round(bb[3], 3)), 0.005,
            ok=abs(bb[1] - bb[0] - 14) < 0.005 and abs(bb[5] - bb[4] - 14) < 0.005 and abs(bb[3] - 29.3) < 0.005)
        pk = [x for x in merged_cyl(c, 1) if abs(x[0] - 2.15) < 0.005]
        chk("4.4a", f"[{k}] magnet pocket Ø4.3 on the shaft axis, y 26.75 .. 29.3 (Ø, axis x/z, floor y, rim y)", (4.3, 0.0, 0.0, 26.75, 29.3), [(round(2 * x[0], 3), round(x[1], 3), round(x[2], 3), round(x[3], 3), round(x[4], 3)) for x in pk], 0.005,
            ok=len(pk) == 1 and abs(pk[0][3] - 26.75) < 0.005 and abs(pk[0][4] - 29.3) < 0.005 and abs(pk[0][1]) < 0.005 and abs(pk[0][2]) < 0.005)
        # the pocket really is Ø4.3 over its full depth: probe at three angles at r 2.14 inside / 2.16 outside (outside only where no rib: angle 0 is the +x flat side = open... use 90/270)
        mid_y = 28.0
        air = [not c.isInside(cq.Vector(2.1 * math.cos(math.radians(an)), mid_y, 2.1 * math.sin(math.radians(an))), 1e-6) for an in (0, 30, 90, 270)]
        wall = [c.isInside(cq.Vector(2.2 * math.cos(math.radians(an)), mid_y, 2.2 * math.sin(math.radians(an))), 1e-6) for an in (0, 30, 90, 270)]
        chk("4.4b", f"[{k}] pocket probe at y 28: air at r 2.1 and wall at r 2.2 at 0/30/90/270 deg (the Ø4.0 magnet + 0.15 per side)", True, all(air) and all(wall), 0, ok=all(air) and all(wall))
        # magnet Ø4.0 x 2.5 fits: only the 3 crush ribs touch it
        mag = cq.Workplane("XZ").circle(2.0).extrude(-2.5).val().translate(cq.Vector(0, 26.8, 0))   # y 26.8 .. 29.3
        mb = bbox6(mag)
        crush = overlap_vol(mag, c)
        chk("4.4c", f"[{k}] Ø4.0 x 2.5 magnet (y 26.8..29.3, flush with the face) vs the cap: only crush-rib overlap (mm3; builder 0.403, limit < 1)", 0.403, round(crush, 3), 0.15, ok=0.0 <= crush < 1.0)
        # asm copy == station copy + offset
        d = max(abs(a_ - (b_ + o_)) for a_, b_, o_ in zip(bbox6(a), bb, (off.x, off.x, off.y, off.y, off.z, off.z)))
        chk("4.5a", f"[{k}] asm1021 copy = station copy translated by (O + RES + (0, 0, 2.64)) (max bbox deviation mm); volume equal", 0.0, round(d, 5), 0.001, ok=d < 0.001 and abs(a.Volume() - c.Volume()) < 1e-4)
    # peg ends in the assembly frame
    for k in ("std", "short"):
        chk("4.5b", f"[{k}] asm1021 peg end y (design, from the tab face y 0 of the assembly) (mm)", exp_end[k], round(bbox6(caps_asm[k])[2] - Y0, 4), 0.01)
    # shaft clearance
    n019 = named(STEP / "nema17_thermal_fin0p019_asm1021.step")
    n019.pop("__duplicates__")
    n18 = named(STEP / "nema17_thermal_fin1p8_asm1021.step")
    n18.pop("__duplicates__")
    sh019, sh18 = n019["shaft"], n18["shaft"]
    chk("4.6a", "0.019 in motor shaft end y (design) from nema17_thermal_fin0p019_asm1021 (mm; 22.0 + 1.517 = 23.517)", 23.517, round(bbox6(sh019)[3] - Y0, 4), 0.003)
    chk("4.6b", "1/8 in motor shaft end y (design) from nema17_thermal_fin1p8_asm1021 (mm; 20.825)", 20.825, round(bbox6(sh18)[3] - Y0, 4), 0.003)
    # ideal Ø5 shaft ending at design y 23.517 on the station-frame cap axis (axis at x 0, z 0 in the station-frame cap files)
    shaft_ideal = cq.Solid.makeCylinder(2.5, 60.0, cq.Vector(0, 23.517 - 60.0, 0), cq.Vector(0, 1, 0))
    for k, label in (("short", "peg1p9"), ("std", "standard")):
        dist = caps[k].distance(shaft_ideal)
        ov = overlap_vol(caps[k], shaft_ideal)
        if k == "short":
            chk("4.6c", f"[{label}] clearance to an ideal Ø5 shaft ending at y 23.517 (mm; required >= 0.5; builder 0.583)", ">= 0.5", f"{dist:.4f} (overlap {ov:.5f})", 0.0, ok=dist >= 0.5 and ov < 1e-6)
        else:
            chk("4.6d", f"[{label}] vs the same 23.517 shaft: INTERFERENCE expected (why the short peg exists): overlap (mm3; builder ~18)", "> 0 (collides)", f"{ov:.3f} mm3, distance {dist:.4f}", 0.0, ok=ov > 5.0)
    dd = caps_asm["short"].distance(sh019)
    chk("4.6e", "[peg1p9 asm1021] clearance to the nema17 0.019 in asm shaft (mm; required >= 0.5)", ">= 0.5", round(dd, 4), 0.0, ok=dd >= 0.5)
    dd_std = caps_asm["std"].distance(sh18)
    chk("4.6f", "[standard asm1021] clearance to the nema17 1/8 in asm shaft (mm; builder 1.775)", 1.775, round(dd_std, 4), 0.005)
    ov_std019 = overlap_vol(caps_asm["std"], sh019)
    chk("4.6g", "[standard asm1021] vs the 0.019 in motor shaft: overlap (mm3, expected collision ~18, builder note)", "> 0", round(ov_std019, 3), 0.0, ok=ov_std019 > 5.0)
    # touching check against Jasper's assembly STEP (method of tools/export_encoder1021_asm.py)
    asm_solids = cq.importers.importStep(str(ASM_SRC)).val().Solids()
    refs = {p.stem: load(p).translate(O) for p in REF.glob("*.step")}
    nmap = {}
    for i, s_ in enumerate(asm_solids):
        for n_, r_ in refs.items():
            if abs(r_.Volume() - s_.Volume()) < 0.01 and (r_.Center() - s_.Center()).Length < 0.01:
                nmap[i] = n_
    for k, vol in (("std", 0.477), ("short", 0.234)):
        a = caps_asm[k]
        cont = {nmap.get(i, f"solid {i}"): round(a.intersect(s_).Volume(), 4) for i, s_ in enumerate(asm_solids) if a.distance(s_) < 1e-6}
        chk("4.7", f"[{k} asm1021] touches only Spool1011 in Jasper's assembly STEP (distance < 1e-6), contact volume (mm3; builder {vol})", {"Spool1011": vol}, cont, 0.005,
            ok=set(cont) == {"Spool1011"} and abs(cont["Spool1011"] - vol) < 0.005)
        near = sorted((round(a.distance(s_), 3), nmap.get(i, f"solid {i}")) for i, s_ in enumerate(asm_solids) if a.distance(s_) >= 1e-6)
        chk("4.7b", f"[{k} asm1021] nearest other solids in the original assembly (shaft ends at y 22.0 there)", "info", near[:3], 0, ok=True)
    # STL
    for k in ("std", "short"):
        tri, nrm = read_stl(STL / f"{names[k]}.stl")
        vol, area = stl_volume_area(tri)
        mb_ = (tri[:, :, 0].min(), tri[:, :, 0].max(), tri[:, :, 1].min(), tri[:, :, 1].max(), tri[:, :, 2].min(), tri[:, :, 2].max())
        wt, bad = stl_watertight(tri)
        zlen = {"std": 6.7, "short": 5.2}[k]
        chk("4.8a", f"[{k}] STL bbox 14 x 14 x {zlen} with the magnet face on the bed (z min 0)", (14.0, 14.0, zlen, 0.0),
            (round(mb_[1] - mb_[0], 3), round(mb_[3] - mb_[2], 3), round(mb_[5] - mb_[4], 3), round(mb_[4], 4)), 0.01,
            ok=abs(mb_[1] - mb_[0] - 14) < 0.01 and abs(mb_[3] - mb_[2] - 14) < 0.01 and abs(mb_[5] - mb_[4] - zlen) < 0.01 and abs(mb_[4]) < 0.01)
        chk("4.8b", f"[{k}] STL volume vs STEP (relative; tessellated, tol 1 %)", 0.0, abs(vol - caps[k].Volume()) / caps[k].Volume(), 0.01)
        chk("4.8c", f"[{k}] STL closed manifold (bad edges)", 0, bad, 0)
        # peg up: the highest vertices are the peg (radius <= 2.6 about the axis); pocket opens at z=0: vertices at r=2.15 exist at z in 0..2.55
        top = tri[:, :, 2] > mb_[5] - 0.01
        rr = np.hypot(tri[:, :, 0][top], tri[:, :, 1][top])
        pocket_v = tri.reshape(-1, 3)
        pr = np.hypot(pocket_v[:, 0], pocket_v[:, 1])
        sel = (np.abs(pr - 2.15) < 0.02) & (pocket_v[:, 2] < 0.05)
        chk("4.8d", f"[{k}] STL orientation: peg end at top (z max, radius <= 2.6), pocket rim (r 2.15) on the bed (z 0)", True, bool(rr.max() < 2.6 and sel.sum() > 6), 0, ok=bool(rr.max() < 2.6 and sel.sum() > 6))
    # rebuild currency check
    from cad.parts import encoder1021 as E
    for k, key in (("std", "m4"), ("short", "m4_peg1p9")):
        v = E.build_v2_variant(key).val()
        chk("4.9", f"[{k}] cap file == fresh builder output (volume difference mm3; currency check)", 0.0, abs(v.Volume() - caps[k].Volume()), 0.01)
    return {}




# ================================================================ SECTION 5: every STEP file
STEP_FILES = [
    ("heat_fin1021_1p8", 1, 26905.824), ("heat_fin1021_1p8_asm1021", 1, 26905.824), ("heat_fin1021_0p019_asm1021", 1, 4093.075),
    ("thermal_station1021_fin1p8", 13, 313249.667), ("thermal_station1021_fin0p019", 13, None), ("thermal_station1021_detailed_fin1p8", 18, None),
    ("nema17_thermal", 6, 60241.53), ("nema17_thermal_fin1p8_asm1021", 6, 60241.53), ("nema17_thermal_fin0p019_asm1021", 6, 60241.53),
    ("encoder1021_magnet_cap_v2_m4", 1, 531.941), ("encoder1021_magnet_cap_v2_m4_asm1021", 1, 531.941),
    ("encoder1021_magnet_cap_v2_m4_peg1p9", 1, 502.312), ("encoder1021_magnet_cap_v2_m4_peg1p9_asm1021", 1, 502.312),
]


def section5():
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="verify_step_"))
    for stem, nsol, vol_exp in STEP_FILES:
        path = STEP / f"{stem}.step"
        if not path.exists():
            chk("5.0", f"{stem}.step exists", True, False, 0, ok=False)
            continue
        s = load(path)
        bb = bbox6(s)
        shapes_ok = is_valid(s) and all(is_valid(x) for x in s.Solids())
        shells_ok = all(len(x.Shells()) == 1 for x in s.Solids())
        out = tmp / f"{stem}_rt.step"
        cq.exporters.export(cq.Workplane().add(s), str(out))
        r = load(out)
        rb = bbox6(r)
        dv = abs(r.Volume() - s.Volume()) / s.Volume()
        db = max(abs(a - b) for a, b in zip(bb, rb))
        chk("5.1", f"{stem}: valid BREP, {nsol} solid(s), one shell each (no stray bodies)", f"{nsol} solids, valid", f"{len(s.Solids())} solids, valid={shapes_ok}, 1 shell each={shells_ok}", 0, ok=len(s.Solids()) == nsol and shapes_ok and shells_ok)
        chk("5.2", f"{stem}: re-export + reimport: volume (relative) and bbox (mm), solid count", "dV/V <= 1e-6, dbbox <= 1e-4", f"dV/V {dv:.2e}, dbbox {db:.2e}, solids {len(r.Solids())}", 0, ok=dv <= 1e-6 and db <= 1e-4 and len(r.Solids()) == len(s.Solids()))
        if vol_exp is not None:
            chk("5.3", f"{stem}: total volume vs build-notes value (mm3)", vol_exp, round(s.Volume(), 3), max(0.01, vol_exp * 2e-6))
        if nsol > 1:
            n = named(path)
            n.pop("__duplicates__")
            sv = sum(x.Volume() for x in n.values())
            chk("5.4", f"{stem}: every component named (none empty/None), volumes sum to file total", "all named", f"{len(n)} names, none None={None not in n}, sum V {sv:.3f}", 0, ok=None not in n and abs(sv - s.Volume()) < 1e-3 and all(k for k in n))
    return {}


def controls():
    """Negative controls: the detectors used above must fire on a deliberately broken input (nothing on disk is touched)."""
    b = station("fin1p8")
    sc = b["screw_1"].translate(cq.Vector(0, 0.1, 0))             # head pushed 0.1 mm into the tab
    v = overlap_vol(sc, b["slipin_mount"])
    chk("9.1", "control: screw_1 moved +0.1 mm in y must show overlap with the slip-in (head annulus 14.137 x 0.1 = 1.41 mm3)", 1.414, round(v, 3), 0.05)
    sc2 = b["screw_1"].translate(cq.Vector(0.15, 0, 0))           # shank off-axis by 0.15 mm toward the fin hole wall (gap 0.2 -> 0.05)
    chk("9.2", "control: screw_1 shifted 0.15 mm in x: shank-to-fin distance must drop to ~0.05", 0.05, round(sc2.distance(b["fin_in"]), 3), 0.01)
    cap = load(STEP / "encoder1021_magnet_cap_v2_m4.step")
    ideal = cq.Solid.makeCylinder(2.5, 60.0, cq.Vector(0, 23.517 - 60.0, 0), cq.Vector(0, 1, 0))
    chk("9.3", "control: standard cap (end 22.6) vs the 23.517 shaft must collide (>5 mm3)", "> 5", round(overlap_vol(cap, ideal), 2), 0, ok=overlap_vol(cap, ideal) > 5)
    chk("9.4", "control: contact_area() of two bodies 1 mm apart is 0", 0.0, round(contact_area(b["fin_out"], b["motor_block"].translate(cq.Vector(0, 0, 100))), 6), 1e-6)
    return {}


def run_all():
    section1()
    section2()
    section2b()
    section3()
    section4()
    section5()
    controls()


def _clean(x):
    if isinstance(x, (np.floating, np.integer)):
        return float(x)
    if isinstance(x, (list, tuple)):
        return [_clean(i) for i in x]
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def write_results():
    out = ROOT / "verification" / "heat_fin1021_thermal_results.json"
    out.write_text(json.dumps(_clean(RESULTS), indent=1, default=str))
    return out


if __name__ == "__main__":
    import time
    t0 = time.time()
    run_all()
    for r in RESULTS:
        print(r["status"], r["id"], r["item"], "| exp", _clean(r["expected"]), "| meas", _clean(r["measured"]), "| tol", r["tol"], r["note"])
    nf = sum(r["status"] == "FAIL" for r in RESULTS)
    print(f"{len(RESULTS)} checks, {nf} FAIL, {time.time() - t0:.0f} s; results -> {write_results()}")
    sys.exit(1 if nf else 0)
