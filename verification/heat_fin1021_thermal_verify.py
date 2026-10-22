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


if __name__ == "__main__":
    section1()
    for r in RESULTS:
        print(r["status"], r["id"], r["item"], "| exp", r["expected"], "| meas", r["measured"], "| tol", r["tol"])
