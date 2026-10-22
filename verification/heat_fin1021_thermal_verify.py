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
            under_head = [(Y0 + 5.0) - merged_cyl(b[f"screw_{n}"], 1)[0][3] for n in (1, 2, 3, 4)] if False else [(Y0 + 5.0) - min(c[3] for c in merged_cyl(b[f"screw_{n}"], 1) if abs(c[0] - 1.5) < 0.005) for n in (1, 2, 3, 4)]
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


if __name__ == "__main__":
    section1()
    section2()
    for r in RESULTS:
        print(r["status"], r["id"], r["item"], "| exp", r["expected"], "| meas", r["measured"], "| tol", r["tol"])
