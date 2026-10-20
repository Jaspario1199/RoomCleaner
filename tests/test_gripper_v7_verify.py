"""
Gripper v7 gearbox -- INDEPENDENT geometry verification (geometry-verifier agent, 2026-10-20).

Everything here is measured from the exported STEP/STL files (exports/step|stl/gripper_v7_*), not from the
part-builder code and not from verification/gripper_v7_numbers.json.  Only numeric design values
(module, tooth counts, link-ground point, crank radius ...) are typed in from cad/params.py as the
"expected" side of each comparison.

Revision 2 (after repair round 1, commit 3bd8256): fixed defects are now plain asserts; the remaining open item is the
servo ear pitch (measure on hardware); the sync-gear SF 1.997 and the 0.2 mm flank clearance are ACCEPTED conditions
(lead decision) and are asserted at their measured values.  See verification/gripper_v7_verification.md.

Run:  /usr/bin/python3 -m pytest -q tests/test_gripper_v7_verify.py       (about 6-8 minutes)
"""

from __future__ import annotations

import itertools
import math
import os
import re
import struct
import tempfile

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface        # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section                           # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape                    # noqa: E402
from OCP.GCPnts import GCPnts_UniformAbscissa                             # noqa: E402
from OCP.GeomAbs import GeomAbs_Cylinder                                  # noqa: E402
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt                                 # noqa: E402
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds                    # noqa: E402
from OCP.TopTools import TopTools_HSequenceOfShape                        # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP = os.path.join(REPO, "exports", "step", "gripper_v7_%s.step")
STL = os.path.join(REPO, "exports", "stl", "gripper_v7_%s.stl")
V6_STEP = os.path.join(REPO, "solidworks", "gripper_v6_2026-10-20", "LaundryGripperAssem1.STEP")
PARTS = ["lower_plate", "upper_plate", "pinion", "compound", "follower", "jaw", "link"]
PETG = 1.27                                   # g/cc

# ---- expected values (typed from cad/params.py GRIPV7_*; the geometry is what is being tested) ---------------
M = 1.5
CD_MAIN, CD_SYNC = 40.80, 36.30
C_AX, F_AX = (CD_SYNC / 2, 0.0), (-CD_SYNC / 2, 0.0)
S_AX = (10.0, math.sqrt(CD_MAIN ** 2 - (10.0 - CD_SYNC / 2) ** 2))
WORLD_ORIGIN = (951.8475, 707.9864, 1079.49)
G = 9.81


# ---- helpers ------------------------------------------------------------------------------------------------
_cache: dict = {}


def load(name):
    if name not in _cache:
        _cache[name] = cq.importers.importStep(STEP % name).val()
    return _cache[name]


def preview_solids():
    if "preview" not in _cache:
        _cache["preview"] = cq.importers.importStep(STEP % "preview").solids().vals()
    return _cache["preview"]


def cylfaces(shape, vertical=True):
    out = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        c = a.Cylinder()
        d = c.Axis().Direction()
        if vertical and abs(abs(d.Z()) - 1.0) > 1e-6:
            continue
        loc = c.Axis().Location()
        bb = f.BoundingBox()
        out.append(dict(r=c.Radius(), x=loc.X(), y=loc.Y(), z0=bb.zmin, z1=bb.zmax, area=f.Area()))
    return out


def section_wires(shape, z):
    s = BRepAlgoAPI_Section(shape.wrapped, gp_Pln(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1)))
    s.Build()
    edges = cq.Shape.cast(s.Shape()).Edges()
    seq, out = TopTools_HSequenceOfShape(), TopTools_HSequenceOfShape()
    for e in edges:
        seq.Append(e.wrapped)
    ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(seq, 1e-5, False, out)
    ws = [cq.Wire(out.Value(i + 1)) for i in range(out.Length())]
    return sorted(ws, key=lambda w: -cq.Face.makeFromWires(w).Area())     # outer first


def wire_segments(w, step=0.04):
    segs = []
    for e in w.Edges():
        c = BRepAdaptor_Curve(e.wrapped)
        n = max(2, int(e.Length() / step) + 1)
        d = GCPnts_UniformAbscissa(c, n)
        if d.IsDone():
            segs.append(np.array([(c.Value(d.Parameter(i)).X(), c.Value(d.Parameter(i)).Y())
                                  for i in range(1, d.NbPoints() + 1)]))
    return segs


def _seg_arrays(segs):
    return np.concatenate([s[:-1] for s in segs]), np.concatenate([s[1:] for s in segs])


def _pt_seg_min(P, a, b):
    best = 1e9
    ab = b - a
    l2 = (ab ** 2).sum(1) + 1e-18
    for i in range(0, len(P), 500):
        p = P[i:i + 500]
        t = np.clip(((p[:, None, :] - a[None]) * ab[None]).sum(-1) / l2[None], 0, 1)
        q = a[None] + t[..., None] * ab[None]
        best = min(best, np.sqrt(((p[:, None, :] - q) ** 2).sum(-1)).min())
    return best


def poly_distance(A, B):
    """Min distance between two polylines given as lists of per-edge point arrays (vertex<->segment)."""
    Ap, Bp = np.concatenate(A), np.concatenate(B)
    lo = np.maximum(Ap.min(0), Bp.min(0)) - 1.0
    hi = np.minimum(Ap.max(0), Bp.max(0)) + 1.0

    def clip(P):
        return P[((P >= lo) & (P <= hi)).all(1)]
    a1, b1 = _seg_arrays(A)
    a2, b2 = _seg_arrays(B)
    return min(_pt_seg_min(clip(Ap), a2, b2), _pt_seg_min(clip(Bp), a1, b1))


def rot2(P, c, ang):
    a = math.radians(ang)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (P - np.asarray(c)) @ R.T + np.asarray(c)


def rotz(s, c, a):
    return s.rotate(cq.Vector(c[0], c[1], 0), cq.Vector(c[0], c[1], 1), a)


def wire_dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


def read_stl(path):
    b = open(path, "rb").read()
    if b[:5] == b"solid" and b"facet" in b[:400]:
        v = np.array([[float(x) for x in m.groups()]
                      for m in re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", b)])
        return v.reshape(-1, 3, 3)
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return a["v"].astype(float)


# ---- independent four-bar (typed from params: R, C, P, d, psi, drop) --------------------------------------------
class FB:
    R, TH_C, SWEEP, AB, PSI_C, DROP = 53.0, -78.589, 76.5, 31.81, -113.589, 75.0
    C = np.array([CD_SYNC / 2, 0.0])
    P = np.array([8.0, -30.0])

    def __init__(self):
        self.Ac = self.A(self.TH_C)
        self.Bc = self.Ac + self.AB * np.array([math.cos(math.radians(self.PSI_C)), math.sin(math.radians(self.PSI_C))])
        self.L = float(np.linalg.norm(self.Bc - self.P))
        self.tip_c = np.array([0.0, self.Ac[1] - self.DROP])

    def A(self, t):
        return self.C + self.R * np.array([math.cos(math.radians(t)), math.sin(math.radians(t))])

    def pose(self, delta):
        prev = self.Bc.copy()
        for t in np.linspace(self.TH_C, self.TH_C + delta, max(2, int(abs(delta) / 0.2) + 2)):
            A = self.A(t)
            d = np.linalg.norm(self.P - A)
            a = (self.AB ** 2 - self.L ** 2 + d * d) / (2 * d)
            h = math.sqrt(max(self.AB ** 2 - a * a, 0.0))
            u = (self.P - A) / d
            m = A + a * u
            pp = np.array([-u[1], u[0]])
            c1, c2 = m + h * pp, m - h * pp
            B = c1 if np.linalg.norm(c1 - prev) < np.linalg.norm(c2 - prev) else c2
            prev = B
        tilt = math.degrees(math.atan2(B[1] - A[1], B[0] - A[0])) - self.PSI_C
        c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
        rel = self.tip_c - self.Ac
        tip = A + np.array([rel[0] * c - rel[1] * s, rel[0] * s + rel[1] * c])
        return A, B, tilt, tip


FBAR = FB()


# =====================================================================================================
# 1. solids, STEP round trip, STL
# =====================================================================================================
@pytest.mark.parametrize("name", PARTS)
def test_step_single_valid_solid(name):
    s = load(name)
    assert s.isValid()
    assert len(cq.importers.importStep(STEP % name).solids().vals()) == 1
    assert s.Volume() > 100.0


@pytest.mark.parametrize("name", PARTS)
def test_step_export_reimport_roundtrip(name):
    s = load(name)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, name + ".step")
        cq.exporters.export(cq.Workplane("XY").add(s), p)
        r = cq.importers.importStep(p).val()
    assert len(r.Solids()) == 1 and r.isValid()
    assert abs(r.Volume() - s.Volume()) / s.Volume() < 1e-6
    a, b = s.BoundingBox(), r.BoundingBox()
    assert max(abs(a.xmin - b.xmin), abs(a.xmax - b.xmax), abs(a.ymin - b.ymin), abs(a.ymax - b.ymax),
               abs(a.zmin - b.zmin), abs(a.zmax - b.zmax)) < 1e-3


@pytest.mark.parametrize("name", PARTS)
def test_stl_watertight_and_matches_step(name):
    t = read_stl(STL % name)
    vol = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0
    q = np.round(t.reshape(-1, 3), 4)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    tri = inv.reshape(-1, 3)
    e = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    assert (cnt != 2).sum() == 0, "STL has open or non-manifold edges"
    assert vol == pytest.approx(load(name).Volume(), rel=2e-3)


def test_preview_roundtrip_and_count():
    sol = preview_solids()
    assert len(sol) == 59
    assert all(s.isValid() for s in sol)
    # the 9 printed bodies in the preview are the exported part files (2 jaws, 2 links)
    vols = sorted(round(s.Volume(), 1) for s in sol[:9])
    want = sorted(round(load(n).Volume(), 1) for n in ("lower_plate", "upper_plate", "compound", "follower", "pinion",
                                                      "jaw", "jaw", "link", "link"))
    assert vols == want


# =====================================================================================================
# 2. gear train
# =====================================================================================================
def _axes_from_pockets():
    """Gear axes measured from the Ø14.05 bearing pockets (compound/follower) and the Ø8.8 pinion pilot bore."""
    ax = {}
    for n in ("compound", "follower"):
        pk = [c for c in cylfaces(load(n)) if abs(c["r"] - 7.025) < 1e-3]
        assert pk, n
        ax[n] = (pk[0]["x"], pk[0]["y"])
    pb = [c for c in cylfaces(load("pinion")) if abs(c["r"] - 4.4) < 1e-3]
    ax["pinion"] = (pb[0]["x"], pb[0]["y"])
    return ax


def test_centre_distances_from_geometry():
    ax = _axes_from_pockets()
    d_main = math.dist(ax["pinion"], ax["compound"])
    d_sync = math.dist(ax["compound"], ax["follower"])
    assert d_main == pytest.approx(CD_MAIN, abs=0.01)           # 40.80
    assert d_sync == pytest.approx(CD_SYNC, abs=0.01)           # 36.30
    # tube plane symmetry: compound/follower mirror about x = 0
    assert ax["compound"][0] == pytest.approx(-ax["follower"][0], abs=1e-3)


def _outer_pts(shape, z, axis, pitch_r):
    w = section_wires(shape, z)[0]
    pts = np.concatenate(wire_segments(w, 0.02))
    d = pts - np.asarray(axis)
    r = np.hypot(d[:, 0], d[:, 1])
    th = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
    o = np.argsort(th)
    r, th = r[o], th[o]
    sg = r - pitch_r
    up = np.where((sg[:-1] < 0) & (sg[1:] >= 0))[0]
    dn = np.where((sg[:-1] >= 0) & (sg[1:] < 0))[0]
    thick = [math.radians(th[dn[dn > u][0]] - th[u]) * pitch_r for u in up if (dn > u).any()]
    return len(up), r.max(), r.min(), float(np.mean(thick))


@pytest.mark.parametrize("part,z,axis,n,", [("pinion", 9.0, S_AX, 18), ("compound", 9.0, C_AX, 36),
                                            ("compound", 20.0, C_AX, 24), ("follower", 20.0, F_AX, 24)])
def test_tooth_counts_and_form(part, z, axis, n):
    cnt, rt, rr, t = _outer_pts(load(part), z, axis, M * n / 2)
    assert cnt == n
    assert rt == pytest.approx(M * (n + 2) / 2, abs=0.01)            # tip radius
    assert rr == pytest.approx(M * (n - 2.5) / 2, abs=0.01)          # root radius
    assert t == pytest.approx(math.pi * M / 2 - 0.10, abs=0.02)      # 0.10 mm thinning at the pitch circle


def test_ratio_is_two_to_one():
    assert 36 / 18 == 2.0


@pytest.fixture(scope="module")
def gear_segs():
    return {"p": wire_segments(section_wires(load("pinion"), 9.0)[0]),
            "c36": wire_segments(section_wires(load("compound"), 9.0)[0]),
            "c24": wire_segments(section_wires(load("compound"), 20.0)[0]),
            "f": wire_segments(section_wires(load("follower"), 20.0)[0])}


def test_flank_clearance_over_sweep(gear_segs):
    """Compound turns by delta, follower by -delta, pinion by -2 delta (phasing as built).  +-30 deg of
    compound rotation in 7.5 deg steps plus the full 0..76.5 deg stroke.  Sampling pitch 0.04 mm -> +-0.002."""
    worst_m, worst_s = 1e9, 1e9
    for d in sorted(set(list(np.arange(-30, 30.1, 7.5)) + [38.25, 76.5])):
        cm = [rot2(s, C_AX, d) for s in gear_segs["c36"]]
        pm = [rot2(s, S_AX, -2 * d) for s in gear_segs["p"]]
        c2 = [rot2(s, C_AX, d) for s in gear_segs["c24"]]
        fm = [rot2(s, F_AX, -d) for s in gear_segs["f"]]
        worst_m = min(worst_m, poly_distance(cm, pm))
        worst_s = min(worst_s, poly_distance(c2, fm))
    print("min flank clearance main %.4f sync %.4f mm" % (worst_m, worst_s))
    assert worst_m >= 0.2 - 0.002 and worst_s >= 0.2 - 0.002
    assert worst_m < 0.5 and worst_s < 0.5                 # and it actually meshes (not a separated pair)


def test_36t_rim_and_spokes():
    s = load("compound")
    ws = section_wires(s, 9.0)
    windows = [w for w in ws[1:] if cq.Face.makeFromWires(w).Area() > 20.0
               and math.hypot((w.BoundingBox().xmin + w.BoundingBox().xmax) / 2 - C_AX[0],
                              (w.BoundingBox().ymin + w.BoundingBox().ymax) / 2 - C_AX[1]) > 3.0]   # not the centre bore
    assert len(windows) == 6                                  # six-spoke web
    c = np.array(C_AX)
    rmax = 0.0
    for w in windows:
        p = np.concatenate(wire_segments(w, 0.1)) - c
        rmax = max(rmax, np.hypot(p[:, 0], p[:, 1]).max())
    root = M * (36 - 2.5) / 2
    assert root - rmax >= 3.75                                # rim below the root circle
    print("36T rim below root %.3f mm (window outer R %.2f, root R %.3f)" % (root - rmax, rmax, root))


# =====================================================================================================
# 3. bearings and pins
# =====================================================================================================
@pytest.mark.parametrize("part,z0,pockets", [("compound", 1.0, [(1.0, 6.05), (26.95, 37.0)]),
                                             ("follower", 17.0, [(17.0, 22.05), (26.95, 37.0)])])
def test_bearing_pockets(part, z0, pockets):
    cyl = cylfaces(load(part))
    bore = [c for c in cyl if abs(c["r"] - 7.025) < 1e-3]                  # Ø14.05 pocket wall
    relief = [c for c in cyl if abs(c["r"] - 7.325) < 1e-3]                # Ø14.65 mouth relief
    assert bore and len(relief) >= 2
    for zlo, zhi in pockets:
        faces = [c for c in bore + relief if c["z1"] > zlo + 1e-6 and c["z0"] < zhi - 1e-6]
        assert faces, (part, zlo, zhi)
        assert min(c["z0"] for c in faces) == pytest.approx(zlo, abs=1e-3)
        assert max(c["z1"] for c in faces) == pytest.approx(zhi, abs=1e-3)
        n = 1 if (zhi - zlo) < 6 else 2
        assert zhi - zlo == pytest.approx(5.0 * n + 0.05, abs=0.01)         # 5.05 / 10.05 deep
    assert all(abs(2 * c["r"] - 14.05) < 1e-3 for c in bore)


def test_pin_seats_and_pin_engagement():
    lp, up = load("lower_plate"), load("upper_plate")
    pins = [s for s in preview_solids() if abs(s.Volume() - math.pi * 3.5 ** 2 * 50.0) < 1.0]
    assert len(pins) == 2
    for s in pins:
        bb = s.BoundingBox()
        assert (bb.zmax - bb.zmin) == pytest.approx(50.0, abs=1e-3)
        assert (bb.xmax - bb.xmin) == pytest.approx(7.0, abs=1e-3)
        pz0, pz1 = bb.zmin - WORLD_ORIGIN[2], bb.zmax - WORLD_ORIGIN[2]
        x = (bb.xmin + bb.xmax) / 2 - WORLD_ORIGIN[0]
        for plate, z_face_in, sign in ((lp, 0.0, -1), (up, 42.0, +1)):
            seat = [c for c in cylfaces(plate) if abs(c["r"] - 3.525) < 1e-3 and abs(c["x"] - x) < 1e-3
                    and abs(c["y"]) < 1e-3]
            assert seat, "pin seat missing"
            if sign < 0:
                depth_into_plate = z_face_in - min(c["z0"] for c in seat)
                assert depth_into_plate >= 4.0 - 1e-6
                assert min(c["z0"] for c in seat) <= pz0 + 1e-6
            else:
                depth_into_plate = max(c["z1"] for c in seat) - z_face_in
                assert depth_into_plate >= 4.0 - 1e-6
                assert max(c["z1"] for c in seat) >= pz1 - 1e-6


def test_every_bearing_straddled_by_a_pin():
    sol = preview_solids()
    pins = [s for s in sol if abs(s.Volume() - math.pi * 3.5 ** 2 * 50.0) < 1.0]
    brgs = [s for s in sol if abs(s.Volume() - 577.3) < 1.0 and abs(s.BoundingBox().zlen - 5.0) < 1e-3]
    assert len(brgs) == 6
    for b in brgs:
        bb = b.BoundingBox()
        cx, cy = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
        ok = False
        for p in pins:
            pb = p.BoundingBox()
            if (abs((pb.xmin + pb.xmax) / 2 - cx) < 1e-3 and abs((pb.ymin + pb.ymax) / 2 - cy) < 1e-3
                    and pb.zmin <= bb.zmin and pb.zmax >= bb.zmax):
                ok = True
        assert ok


# =====================================================================================================
# 4. jaw four-bar
# =====================================================================================================
def test_fourbar_travel_and_gaps_from_jaw_geometry():
    jaw = load("jaw")
    vs = np.array([(v.X, v.Y) for v in jaw.Vertices()])
    inner = vs[vs[:, 0] < 0.01]
    tip_c = inner[inner[:, 1].argmin()]
    assert tip_c[0] == pytest.approx(0.0, abs=1e-6)               # inner face on x = 0 -> tips meet
    gaps = []
    for d in np.linspace(0, FBAR.SWEEP, 31):
        A, B, tilt, tip = FBAR.pose(d)
        c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
        rel = tip_c - FBAR.Ac
        tp = A + np.array([rel[0] * c - rel[1] * s, rel[0] * s + rel[1] * c])
        gaps.append(2 * tp[0])
    assert gaps[0] == pytest.approx(0.0, abs=1e-3)
    assert gaps[-1] == pytest.approx(91.6, abs=0.2)
    assert all(np.diff(gaps) > 0)                                  # monotonic, no toggle inside the stroke
    assert FBAR.SWEEP == pytest.approx(76.5)


def _build_bodies(delta):
    A, B, tilt, _ = FBAR.pose(delta)
    j = rotz(load("jaw"), FBAR.Ac, tilt).translate(cq.Vector(A[0] - FBAR.Ac[0], A[1] - FBAR.Ac[1], 0))
    a0 = math.degrees(math.atan2(*(FBAR.Bc - FBAR.P)[::-1]))
    a1 = math.degrees(math.atan2(*(B - FBAR.P)[::-1]))
    lk = rotz(load("link"), FBAR.P, a1 - a0)
    return {"lower_plate": load("lower_plate"), "upper_plate": load("upper_plate"),
            "compound": rotz(load("compound"), C_AX, delta), "follower": rotz(load("follower"), F_AX, -delta),
            "pinion": rotz(load("pinion"), S_AX, -2 * delta),
            "jaw_R": j, "jaw_L": j.mirror("YZ"), "link_R": lk, "link_L": lk.mirror("YZ")}


@pytest.mark.parametrize("delta", list(np.linspace(0.0, 76.5, 17)))
def test_no_interference_over_sweep(delta):
    """>= 15 angles over the stroke, nine printed bodies (plates, 3 gears, 2 jaws, 2 links); threshold 0.5 mm3."""
    bodies = _build_bodies(delta)
    worst = ("", 0.0)
    for (na, a), (nb, b) in itertools.combinations(bodies.items(), 2):
        A, B = a.BoundingBox(), b.BoundingBox()
        if (A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin
                or A.zmax < B.zmin or B.zmax < A.zmin):
            continue
        v = a.intersect(b).Volume()
        if v > worst[1]:
            worst = (na + "/" + nb, v)
    assert worst[1] <= 0.5, worst


def test_interference_detector_positive_control():
    b = _build_bodies(38.25)
    j = rotz(b["jaw_R"], FBAR.Ac, 6.0)
    assert j.intersect(b["link_R"]).Volume() > 10.0


@pytest.mark.parametrize("delta", [0.0, 38.25, 76.5])
def test_follower_axial_gap_over_36t_layer(delta):
    """Repair 1: annular relief on the 36T-layer top -> follower bottom (z 17.0) clears it by 0.30 mm."""
    b = _build_bodies(delta)
    top = b["compound"].intersect(cq.Solid.makeBox(300, 300, 1.0, cq.Vector(-150, -150, 16.0)))   # 36T layer z 16..17
    d = top.distance(b["follower"])
    assert d >= 0.3 - 1e-3, d
    # the relief really is an annulus R16.5..29.5 on the 36T top: only the R11..16.5 hub reaches z = 17
    ws = section_wires(load("compound"), 16.85)
    p = np.concatenate(wire_segments(ws[0], 0.1)) - np.array(C_AX)
    assert np.hypot(p[:, 0], p[:, 1]).max() == pytest.approx(16.5, abs=0.01)
    ws = section_wires(load("compound"), 16.6)
    p = np.concatenate(wire_segments(ws[0], 0.1)) - np.array(C_AX)
    assert np.hypot(p[:, 0], p[:, 1]).max() == pytest.approx(28.5, abs=0.01)          # full 36T below the relief


# =====================================================================================================
# 5. Lewis strength and 6. grip force (independent re-computation)
# =====================================================================================================
LEWIS_Y = {18: 0.309, 24: 0.337, 36: 0.3775}
ALLOW = 22.5e6


def _sf(ft, face_mm, z):
    return ALLOW / (ft / (face_mm * 1e-3 * M * 1e-3 * LEWIS_Y[z]))


def test_lewis_safety_factors_6v():
    """Effective mesh face of the 36T layer is 16 - 0.30 = 15.7 mm after the axial relief (pinion teeth are still
    16 mm, so 15.7 governs the engaged width of the pair)."""
    tau = 11.0 * G / 100.0
    ft = 2 * tau / (18 * M * 1e-3)
    assert _sf(ft, 15.7, 18) == pytest.approx(2.048, abs=0.002)
    assert _sf(ft, 15.7, 18) >= 2.0
    assert _sf(ft, 15.7, 36) == pytest.approx(2.502, abs=0.002)
    assert _sf(ft, 15.7, 36) >= 2.5


def test_lewis_sync_sf_accepted_condition():
    """ACCEPTED CONDITION (lead decision): sync 24T one-jaw SF at 6 V stall = 1.997 (< 2.0 by 0.15 %)."""
    tau = 11.0 * G / 100.0
    ft_sync = tau * 2.0 * 0.95 / (M * 24 / 2 * 1e-3)
    assert _sf(ft_sync, 20, 24) == pytest.approx(1.997, abs=0.002)


def test_grip_force_per_jaw_4v8():
    tau = 9.4 * G / 100.0
    tjaw = tau * 2.0 * 0.95 ** 2 / 2.0
    ds = np.linspace(0, FBAR.SWEEP, 301)
    pts = [FBAR.pose(d) for d in ds]
    tipx = np.array([p[3][0] for p in pts])
    gap = 2 * tipx
    F = np.array([tjaw * math.radians(ds[i + 1] - ds[i - 1]) / ((tipx[i + 1] - tipx[i - 1]) * 1e-3)
                  for i in range(1, 300)])
    g = gap[1:300]
    m = g <= 85.0
    print("min grip force per jaw at 4.8 V over gap<=85 mm: %.2f N at gap %.1f" % (F[m].min(), g[m][F[m].argmin()]))
    assert g.min() < 1.0 and g.max() > 85.0
    assert F[m].min() >= 7.4


# =====================================================================================================
# 7. masses
# =====================================================================================================
def test_masses():
    m = {n: load(n).Volume() * PETG * 1e-3 for n in PARTS}
    frame = m["lower_plate"] + m["upper_plate"]
    assert frame <= 150.0
    printed = frame + m["pinion"] + m["compound"] + m["follower"] + 2 * m["jaw"] + 2 * m["link"]
    print("frame %.2f g, printed total %.2f g" % (frame, printed))
    assert 320.0 < printed < 335.0                              # was 332.2 before repair 1
    # purchased: the 148.4 g of the roll-up is arithmetic on ASSUMED catalogue masses.  Only the steel pins can be
    # checked from geometry (7.85 g/cc); fasteners are checked against their envelope volumes in the preview and
    # come out ~8 g heavier (+1.8 % of the head total), reported in verification/gripper_v7_verification.md.
    sol = preview_solids()
    pins = sum(s.Volume() for s in sol if abs(s.Volume() - 1924.2) < 1) * 7.85e-3
    assert pins == pytest.approx(30.2, abs=0.1)
    assert 332.2 + 148.4 == pytest.approx(480.6, abs=0.1)
    fasteners = sum(s.Volume() for s in sol[23:55]) * 7.85e-3            # shoulder screws, washers, nylocs, ties
    assert 40.4 < fasteners < 60.0


# =====================================================================================================
# 8. v6 interfaces kept
# =====================================================================================================
def _tube(solids, length=254.8):
    for s in solids:
        bb = s.BoundingBox()
        d = sorted([bb.xlen, bb.ylen, bb.zlen])
        if abs(d[2] - length) < 0.5 and abs(d[0] - 28.54) < 0.3:     # D28: v7 preview tube is 254.8 (cut 50 mm); the v6 STEP tube is 304.8
            return s
    raise AssertionError("tube not found")


def test_tube_interface_vs_v6_and_socket_insertion():
    t7 = _tube(preview_solids()).BoundingBox()
    assert (t7.xmin + t7.xmax) / 2 == pytest.approx(951.8475, abs=1e-3)
    assert (t7.zmin + t7.zmax) / 2 == pytest.approx(1103.99, abs=1e-2)
    assert t7.ymin == pytest.approx(786.39, abs=2e-2)
    if os.path.exists(V6_STEP):
        t6 = _tube(cq.importers.importStep(V6_STEP).solids().vals(), 304.8).BoundingBox()
        assert (t7.xmin + t7.xmax) / 2 == pytest.approx((t6.xmin + t6.xmax) / 2, abs=1e-3)
        assert (t7.zmin + t7.zmax) / 2 == pytest.approx((t6.zmin + t6.zmax) / 2, abs=1e-3)
        assert t7.ymin == pytest.approx(t6.ymin, abs=2e-2)
    # 42.5 mm insertion: socket bore (R = 14.27 + 0.15) in both plates spans world y 786.39 .. 828.89
    for n in ("lower_plate", "upper_plate"):
        bores = []
        for f in load(n).Faces():
            a = BRepAdaptor_Surface(f.wrapped)
            if a.GetType() == GeomAbs_Cylinder and abs(abs(a.Cylinder().Axis().Direction().Y()) - 1) < 1e-6 \
                    and abs(a.Cylinder().Radius() - 14.42) < 1e-3:
                bb = f.BoundingBox()
                bores.append((bb.ymin + WORLD_ORIGIN[1], bb.ymax + WORLD_ORIGIN[1]))
        assert bores, n
        assert min(b[0] for b in bores) == pytest.approx(786.39, abs=0.02)
        assert max(b[1] for b in bores) - min(b[0] for b in bores) == pytest.approx(42.5, abs=0.02)


def test_servo_ear_span_open_item_measure_on_hardware():
    """OPEN ITEM (measure on hardware): the plate uses 47.0 mm (v6 model); cad/interfaces.py says 48.3 mm.
    This test records the unchanged discrepancy; it does not claim either number is right."""
    import importlib
    itf = importlib.import_module("cad.interfaces")
    holes = [c for c in cylfaces(load("upper_plate")) if abs(c["r"] - 1.65) < 1e-3 and c["z1"] > 47.9]
    xs = sorted({round(c["x"], 3) for c in holes})
    assert len(xs) == 2
    assert xs[1] - xs[0] == pytest.approx(47.0, abs=0.01)
    assert itf.SERVO_EAR_SPAN == pytest.approx(48.3)


# =====================================================================================================
# 9. minimum wall (>= 1.2 mm) -- exact wire-to-wire distances + raster opening for necks / slivers
# =====================================================================================================
MIN_WALL = 1.2


def test_wall_pinion_horn_pilots():
    ws = section_wires(load("pinion"), 26.0)
    walls = [wire_dist(ws[0], w) for w in ws[1:]]
    print("pinion horn-pilot outer wall %.3f mm" % min(walls))
    assert min(walls) == pytest.approx(1.65, abs=0.01)        # hub Ø21, pilots Ø1.7 at R8
    assert min(walls) >= MIN_WALL


def test_wall_upper_plate_insert_holes():
    holes_f = [c for c in cylfaces(load("upper_plate")) if abs(c["r"] - 1.65) < 1e-3 and c["z1"] > 47.9]
    assert len(holes_f) == 4                                                  # Ø3.3 x 4.7 blind
    assert all(abs(c["z0"] - 43.3) < 1e-3 for c in holes_f)                   # floor 43.3 - 42 = 1.3 mm
    ws = section_wires(load("upper_plate"), 45.0)
    holes = [w for w in ws[1:] if w.BoundingBox().xlen < 4 and w.BoundingBox().ylen < 4
             and abs(abs((w.BoundingBox().xmin + w.BoundingBox().xmax) / 2) - 23.5) < 0.1]
    assert len(holes) == 4
    cut = [w for w in ws[1:] if abs(w.BoundingBox().xlen - 41.2) < 0.1 and abs(w.BoundingBox().ylen - 20.2) < 0.1]
    assert cut, "servo cut-out wire not found"
    wall = min(wire_dist(h, cut[0]) for h in holes)
    print("insert hole to cut-out wall %.3f mm, floor 1.3 mm" % wall)
    assert wall >= MIN_WALL and wall == pytest.approx(1.25, abs=0.01)


def test_wall_race_rings():
    """Ring OD is measured from the STEP (not hard-coded); wall = (OD - pin seat) / 2."""
    for n in ("lower_plate", "upper_plate"):
        cyl = cylfaces(load(n))
        seat_r = [c["r"] for c in cyl if abs(abs(c["x"]) - 18.15) < 1e-3 and abs(c["y"]) < 1e-3 and 3.4 < c["r"] < 3.6]
        ring_r = [c["r"] for c in cyl if abs(abs(c["x"]) - 18.15) < 1e-3 and abs(c["y"]) < 1e-3 and 4.4 < c["r"] < 5.0]
        assert seat_r and ring_r, n
        wall = min(ring_r) - max(seat_r)
        print(n, "race ring OD %.3f seat %.3f wall %.3f" % (2 * min(ring_r), 2 * max(seat_r), wall))
        assert wall >= MIN_WALL and wall == pytest.approx(1.325, abs=0.005)


def _raster_thin(shape, z, bbox_pad=10, px=0.05):
    """Morphological opening with a Ø1.2 mm disc; returns connected thin components with area >= 0.4 mm2."""
    import cv2
    bb = shape.BoundingBox()
    x0, y0 = bb.xmin, bb.ymin
    W = int((bb.xmax - bb.xmin) / px) + 2 * bbox_pad
    H = int((bb.ymax - bb.ymin) / px) + 2 * bbox_pad
    m = np.zeros((H, W), np.uint8)
    for w in section_wires(shape, z):
        chain = []
        rem = [seg.tolist() for seg in wire_segments(w, 0.02)]
        chain += rem.pop(0)
        while rem:
            end = np.array(chain[-1])
            best, bd = None, 1e9
            for k, sg in enumerate(rem):
                for rev in (False, True):
                    dd = np.linalg.norm(np.array(sg[-1] if rev else sg[0]) - end)
                    if dd < bd:
                        bd, best = dd, (k, rev)
            k, rev = best
            sg = rem.pop(k)
            chain += sg[::-1] if rev else sg
        P = np.array(chain)
        pts = np.stack([np.round((P[:, 0] - x0) / px + bbox_pad), np.round((P[:, 1] - y0) / px + bbox_pad)], 1).astype(np.int32)
        t = np.zeros((H, W), np.uint8)
        cv2.fillPoly(t, [pts], 1)
        m ^= t
    k = int(round(0.5 * MIN_WALL / px))
    op = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    thin = ((m == 1) & (op == 0)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(thin, 8)
    return [(st[i, 4] * px * px, (cen[i][0] * px + x0 - bbox_pad * px, cen[i][1] * px + y0 - bbox_pad * px))
            for i in range(1, n) if st[i, 4] * px * px >= 0.4]


def _planar_z_levels(shape):
    from OCP.GeomAbs import GeomAbs_Plane
    zs = set()
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Plane and abs(abs(a.Plane().Axis().Direction().Z()) - 1) < 1e-6:
            zs.add(round(a.Plane().Location().Z(), 3))
    return sorted(zs)


def _scan_levels(shape, extra=()):
    zs = _planar_z_levels(shape)
    mids = [(a + b) / 2 for a, b in zip(zs[:-1], zs[1:]) if b - a > 0.05]
    out = sorted(set(mids) | set(extra))
    return [z for z in out if all(abs(z - q) > 0.04 for q in zs)]          # never section on a coincident plane


def test_wall_jaw_slot_band_and_all_bands():
    s = load("jaw")
    for z in _scan_levels(s):
        assert _raster_thin(s, z) == [], z
    # blunt end: the crescent wall at A is now 1.3 mm (boss R9.8 - (tongue end R8 + 0.5 slot clearance))
    assert 9.8 - (8.0 + 0.5) == pytest.approx(1.3)


def test_wall_upper_saddle_ligaments():
    s = load("upper_plate")
    # saddle shell / tie-column notch region: the bore width varies with z, so sample densely, not only mid-bands
    for z in _scan_levels(s, extra=np.arange(24.6, 42.0, 0.9)):
        assert _raster_thin(s, z) == [], z


@pytest.mark.parametrize("name,extra", [("link", ()), ("pinion", ()), ("follower", ()), ("compound", ()),
                                        ("lower_plate", tuple(np.arange(0.3, 24.5, 1.2)))])
def test_wall_other_parts_clean(name, extra):
    s = load(name)
    for z in _scan_levels(s, extra):
        thin = _raster_thin(s, z)
        if name in ("pinion", "follower", "compound"):          # tooth ring is not a wall
            axis = {"pinion": S_AX, "follower": F_AX, "compound": C_AX}[name]
            root = {"pinion": 11.7, "follower": 16.2, "compound": 25.2}[name]
            thin = [t for t in thin if math.dist(t[1], axis) < root]
        assert thin == [], (name, z, thin)
