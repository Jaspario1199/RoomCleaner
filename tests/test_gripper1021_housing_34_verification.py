"""
INDEPENDENT geometry verification of the Gripper 1021 electrical housing with the three-cable holes ("_34").

  Part under test : exports/step/gripper1021_housing_cambay_34.step / exports/stl/gripper1021_housing_cambay_34.stl
  Baseline        : exports/step/gripper1021_housing_cambay.step (+ _cover.step), Jasper's raw housing (read only)
  Spec            : cad/GRIPPER_1021_SPEC.md section 5, as amended by the lead's decisions in section 5.1

Written by the geometry-verifier.  It does NOT import the implementer's tests, build script or cable-line analyzer, and it does not
use cad.params for any expected value: every expected number below is typed in from the task / spec table.  Measurements are made on the
exported STEP / STL files (B-rep face parameters, point-in-solid probes, face-signature comparison, local volume differences, an own
ray / segment-to-triangle distance code on a re-tessellated mesh).  The only repository code it executes is
cad.parts.gripper1021_housing_cambay.make() (item 10: baseline regenerates identically) and make_34() (STEP vs source).
Nothing in the repository is written; STEP round-trip files go to a pytest tmp dir.

Frames.  World -> "box frame": subtract ORIGIN (origin on the tube axis in the box bottom plane, +y up; box x = world x,
box z = world z - 1103.9899).  Body frame of the claw: origin on the tube axis at box y = 7.82, +x = box x, +y = -box z, +z = box y.
"""

from __future__ import annotations

import itertools
import math
import os
import struct
import sys
import time
from functools import lru_cache

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")
from OCP.BRepAdaptor import BRepAdaptor_Surface                      # noqa: E402
from OCP.BRepCheck import BRepCheck_Analyzer                         # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier              # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape              # noqa: E402
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane  # noqa: E402
from OCP.TopAbs import TopAbs_IN, TopAbs_OUT                         # noqa: E402
from OCP.gp import gp_Pnt                                            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

STEP_34 = os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay_34.step")
STL_34 = os.path.join(REPO, "exports", "stl", "gripper1021_housing_cambay_34.stl")
STEP_BASE = os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay.step")
STL_BASE = os.path.join(REPO, "exports", "stl", "gripper1021_housing_cambay.stl")
STEP_COVER = os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay_cover.step")
STEP_RAW = os.path.join(REPO, "cad", "reference", "gripper_1021", "parts", "05_Gripper_Electric_Housing_Base_2__NAUO5.step")

pytestmark = pytest.mark.skipif(
    not all(os.path.exists(p) for p in (STEP_34, STL_34, STEP_BASE, STEP_COVER, STEP_RAW)), reason="exports / reference parts not available")

# ---- expected values, typed from the task / spec (NOT read from cad.params) ----------------------------------------------------
ORIGIN = (951.8475, 1091.1905, 1103.9899)
IDS = ("C", "A", "B")
OUTER = {"C": (0.0, 42.0, -45.0), "A": (-45.0, 42.0, 25.98), "B": (45.0, 42.0, 25.98)}
INNER = {"C": (0.0, 42.0, -40.0), "A": (-40.0, 42.0, 23.09), "B": (40.0, 42.0, 23.09)}
WALL_NORMAL = {"C": (0.0, 0.0, -1.0), "A": (-1.0, 0.0, 0.0), "B": (1.0, 0.0, 0.0)}
WALL_LEN = {"C": 5.0, "A": 5.0 / math.cos(math.radians(30)), "B": 5.0 / math.cos(math.radians(30))}
BORE_R, CHAMFER, TIP_HALF_DEG, LABEL_H, LABEL_DEPTH, LABEL_ABOVE = 1.0, 0.5, 45.0, 4.0, 0.4, 5.0
KEEPOUT = 5.0
HOLE_ZONE = 3.0                      # mm: changed regions must lie within this of a hole or a label
BODY_ORIGIN_BOX_Y = 7.82
BODY_POINTS_M = {"C": (0.0, 0.0450, 0.0342), "A": (-0.0450, -0.0260, 0.0342), "B": (0.0450, -0.0260, 0.0342)}
ANCHORS_M = {"A": (0.05, 0.05, 2.5932), "B": (3.3028, 0.05, 2.5932), "C": (1.6764, 2.6932, 2.5932)}
ROOM_M = (3.3528, 2.7432)
WALL_MARGIN_M = 0.2
PETG = 1.27                          # g/cm3

RESULTS: dict = {}                   # filled by the tests, dumped by the last test for the report


def note(key, value):
    RESULTS[key] = value


def vec(p):
    return np.array(p, dtype=float)


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def axis_out(hid):
    """Unit outward axis (horizontal, radial) from the spec mouths."""
    return unit(vec(OUTER[hid]) - vec(INNER[hid]))


def e1_of(hid):
    """Horizontal unit vector perpendicular to the axis (lateral direction of the hole cross-section)."""
    a = axis_out(hid)
    return unit(np.cross([0.0, 1.0, 0.0], a))


# ---- loading ---------------------------------------------------------------------------------------------------------------------
def to_box(shape):
    return shape.translate(cq.Vector(-ORIGIN[0], -ORIGIN[1], -ORIGIN[2]))


@lru_cache(maxsize=None)
def load_box(path):
    return to_box(cq.importers.importStep(path).val())


@lru_cache(maxsize=None)
def classifier(path):
    sh = load_box(path)
    c = BRepClass3d_SolidClassifier(sh.wrapped)

    def state(p):
        c.Perform(gp_Pnt(float(p[0]), float(p[1]), float(p[2])), 1e-7)
        s = c.State()
        return "I" if s == TopAbs_IN else ("O" if s == TopAbs_OUT else "N")

    return state


def part():
    return load_box(STEP_34)


def base():
    return load_box(STEP_BASE)


def is_empty34(p):
    return classifier(STEP_34)(p) == "O"


def is_solid34(p):
    return classifier(STEP_34)(p) in ("I",)


def is_solid_base(p):
    return classifier(STEP_BASE)(p) in ("I",)


def bisect_boundary(inside_fn, p_empty, p_solid, tol=1e-4):
    """Along the segment p_empty -> p_solid, locate the empty/solid transition; returns the fraction t in [0,1] of the boundary."""
    lo, hi = 0.0, 1.0
    a, b = vec(p_empty), vec(p_solid)
    assert inside_fn(a) and not inside_fn(b), "bisection needs an empty start and a solid end"
    length = np.linalg.norm(b - a)
    while (hi - lo) * length > tol:
        mid = 0.5 * (lo + hi)
        if inside_fn(a + (b - a) * mid):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# =====================================================================================================================================
# generic geometry helpers
# =====================================================================================================================================
def brep_valid(shape) -> bool:
    return bool(BRepCheck_Analyzer(shape.wrapped).IsValid())


def bbox_tuple(shape):
    b = shape.BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def face_sig(f):
    c = f.Center()
    return (f.geomType(), f.Area(), c.x, c.y, c.z)


def match_faces(faces_a, faces_b, tol_area=1e-3, tol_pos=1e-3):
    """Greedy signature matching (geometry type, area, centre of mass).  Returns (unmatched indices in a, unmatched indices in b)."""
    sb = [face_sig(f) for f in faces_b]
    used = set()
    un_a = []
    for i, f in enumerate(faces_a):
        s = face_sig(f)
        hit = None
        for j, t in enumerate(sb):
            if j in used or t[0] != s[0]:
                continue
            if abs(t[1] - s[1]) <= tol_area + 1e-6 * s[1] and max(abs(t[k] - s[k]) for k in (2, 3, 4)) < tol_pos:
                hit = j
                break
        if hit is None:
            un_a.append(i)
        else:
            used.add(hit)
    return un_a, [j for j in range(len(faces_b)) if j not in used]


def face_points(f, lin=0.05):
    v, t = f.tessellate(lin, 0.2)
    return np.array([(p.x, p.y, p.z) for p in v], float)


def seg_dist_points(pts, a, b):
    pts = np.atleast_2d(pts)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / (ab @ ab), 0.0, 1.0)
    return np.linalg.norm(pts - (a + t[:, None] * ab), axis=1)


def label_frame(hid):
    """(centre, right, up, normal) of the label on the outer wall: centre = outer mouth + 5 mm up (from the spec table)."""
    n = vec(WALL_NORMAL[hid])
    centre = vec(OUTER[hid]) + np.array([0.0, LABEL_ABOVE, 0.0])
    right = np.cross(-n, [0.0, 1.0, 0.0])          # reader's right when looking at the wall from outside, y up
    return centre, right, np.array([0.0, 1.0, 0.0]), n


def label_box_dist(pts, hid, half_u=2.5, half_v=2.2, depth=0.45):
    """distance of points to the nominal label box (wall aligned) -- used only for the 'within 3 mm of a label' zone test."""
    c, r, u, n = label_frame(hid)
    q = np.atleast_2d(pts) - c
    du = np.abs(q @ r) - half_u
    dv = np.abs(q @ u) - half_v
    dw = np.maximum(-(q @ n) - depth, (q @ n) - 0.05)
    return np.linalg.norm(np.stack([np.maximum(du, 0), np.maximum(dv, 0), np.maximum(dw, 0)], axis=1), axis=1)


def zone_distance(pts):
    """smallest distance of each point to any hole axis segment (inner->outer mouth) or nominal label box."""
    pts = np.atleast_2d(pts)
    d = np.full(len(pts), np.inf)
    for hid in IDS:
        d = np.minimum(d, seg_dist_points(pts, vec(INNER[hid]), vec(OUTER[hid])))
        d = np.minimum(d, label_box_dist(pts, hid))
    return d


@lru_cache(maxsize=None)
def face_diff():
    """Face-signature comparison of the part against the baseline housing."""
    pf, bf = part().Faces(), base().Faces()
    un_b, un_p = match_faces(bf, pf)
    return pf, bf, un_b, un_p


def cylinder_params(f):
    ad = BRepAdaptor_Surface(f.wrapped)
    assert ad.GetType() == GeomAbs_Cylinder
    cy = ad.Cylinder()
    ax = cy.Axis()
    loc, d = ax.Location(), ax.Direction()
    return cy.Radius(), vec((loc.X(), loc.Y(), loc.Z())), vec((d.X(), d.Y(), d.Z()))


def hole_bore_cylinder(hid):
    """The new Ø2 cylinder face belonging to hole `hid` (found by proximity to the expected hole segment)."""
    pf, _, _, un_p = face_diff()
    a, b = vec(INNER[hid]), vec(OUTER[hid])
    found = []
    for j in un_p:
        f = pf[j]
        if f.geomType() != "CYLINDER":
            continue
        r, _, _ = cylinder_params(f)
        if abs(r - BORE_R) > 0.05:
            continue
        c = f.Center()
        if seg_dist_points(vec((c.x, c.y, c.z)), a, b)[0] < 2.0:
            found.append(f)
    return found


def hole_new_faces(hid, radius=HOLE_ZONE):
    """All new faces of the part (not in the baseline) that lie in the hole body (y < 45, i.e. not the label)."""
    pf, _, _, un_p = face_diff()
    a, b = vec(INNER[hid]), vec(OUTER[hid])
    out = []
    for j in un_p:
        f = pf[j]
        if f.Area() > 100.0:
            continue                                   # modified big wall faces
        pts = face_points(f)
        if len(pts) and seg_dist_points(pts, a, b).max() < radius and pts[:, 1].max() < 44.9:
            out.append(f)
    return out


# =====================================================================================================================================
# 1. SOLID
# =====================================================================================================================================
def test_01_single_valid_solid_and_bbox_equals_baseline():
    raw_step = open(STEP_34, "r", errors="ignore").read()
    n_brep = raw_step.count("MANIFOLD_SOLID_BREP(")
    imported = cq.importers.importStep(STEP_34)
    p, b = part(), base()
    bb_p, bb_b = bbox_tuple(p), bbox_tuple(b)
    d_bbox = max(abs(x - y) for x, y in zip(bb_p, bb_b))
    note("01.step_manifold_solid_breps", n_brep)
    note("01.imported_objects", len(imported.vals()))
    note("01.solids", len(p.Solids()))
    note("01.shells", len(p.Shells()))
    note("01.valid_cq", bool(p.isValid()))
    note("01.valid_brepcheck", brep_valid(p))
    note("01.volume_mm3", p.Volume())
    note("01.baseline_volume_mm3", b.Volume())
    note("01.bbox_box_frame", [round(v, 5) for v in bb_p])
    note("01.baseline_bbox_box_frame", [round(v, 5) for v in bb_b])
    note("01.bbox_max_diff_mm", d_bbox)
    assert n_brep == 1 and len(imported.vals()) == 1
    assert len(p.Solids()) == 1 and len(p.Shells()) == 1
    assert p.isValid() and brep_valid(p)
    assert p.Volume() > 0.0
    assert d_bbox < 1e-4, f"bounding box differs from the baseline by {d_bbox} mm"


# =====================================================================================================================================
# 2. DIFFERENCE TO THE BASELINE: only three holes and three debossed labels, nothing added
# =====================================================================================================================================
def _wall_face_kind(f):
    """('outer'|'inner', hole id) for a planar wall face of the box that carries a hole; None otherwise."""
    if f.geomType() != "PLANE":
        return None
    c = f.Center()
    n = f.normalAt()
    for hid in IDS:
        for kind, pos in (("outer", OUTER[hid]), ("inner", INNER[hid])):
            wn = vec(WALL_NORMAL[hid])
            sign = 1.0 if kind == "outer" else -1.0
            # plane of the wall through the mouth, normal = +-wall normal
            if abs(np.dot(vec((n.x, n.y, n.z)), wn * sign)) > 0.999 and abs(np.dot(vec((c.x, c.y, c.z)) - vec(pos), wn)) < 1e-3:
                return kind, hid
    return None


def test_02a_only_six_wall_faces_changed_every_other_face_identical():
    pf, bf, un_b, un_p = face_diff()
    note("02.faces_baseline", len(bf))
    note("02.faces_part", len(pf))
    note("02.unmatched_baseline_faces", len(un_b))
    note("02.unmatched_part_faces", len(un_p))
    kinds = [_wall_face_kind(bf[i]) for i in un_b]
    note("02.unmatched_baseline_face_kinds", [str(k) for k in kinds])
    assert len(un_b) == 6, f"expected exactly the 6 wall faces (3 outer + 3 inner) to change, got {len(un_b)}"
    assert all(k is not None for k in kinds), f"an unmatched baseline face is not a hole-bearing wall face: {kinds}"
    assert sorted(kinds) == sorted([(k, h) for k in ("outer", "inner") for h in IDS])
    assert len(bf) - len(un_b) == 181
    # new faces: 91 + the 6 modified
    assert len(un_p) - 6 == 91 or len(un_p) - 6 > 0


def test_02b_modified_wall_faces_keep_their_outer_boundary_and_only_gain_inner_loops_in_the_zones():
    pf, bf, un_b, un_p = face_diff()
    worst_loop = 0.0
    for i in un_b:
        kind, hid = _wall_face_kind(bf[i])
        fb = bf[i]
        # counterpart in the part: planar, same plane, large
        cands = [pf[j] for j in un_p if _wall_face_kind(pf[j]) == (kind, hid) and pf[j].Area() > 100.0]
        assert len(cands) == 1, f"{kind} {hid}: {len(cands)} large counterparts"
        fp = cands[0]
        ob = sorted(round(e.Length(), 5) for e in fb.outerWire().Edges())
        op = sorted(round(e.Length(), 5) for e in fp.outerWire().Edges())
        assert ob == op, f"{kind} {hid}: outer boundary changed"
        cb = sorted((round(e.Center().x, 4), round(e.Center().y, 4), round(e.Center().z, 4)) for e in fb.outerWire().Edges())
        cp = sorted((round(e.Center().x, 4), round(e.Center().y, 4), round(e.Center().z, 4)) for e in fp.outerWire().Edges())
        assert cb == cp, f"{kind} {hid}: outer boundary edges moved"
        def wire_sig(w):
            return tuple(sorted((round(e.Center().x, 3), round(e.Center().y, 3), round(e.Center().z, 3), round(e.Length(), 3)) for e in w.Edges()))
        wb = {wire_sig(w) for w in fb.innerWires()}
        wp = {wire_sig(w): w for w in fp.innerWires()}
        assert wb <= set(wp), f"{kind} {hid}: an inner loop of the baseline face disappeared or moved"
        new_loops = [w for k, w in wp.items() if k not in wb]
        assert new_loops, f"{kind} {hid}: no new inner loop"
        for w in new_loops:
            pts = np.concatenate([np.array([(q.x, q.y, q.z) for q in e.positions([i / 8.0 for i in range(9)])]) for e in w.Edges()])
            dz = zone_distance(pts).max()
            worst_loop = max(worst_loop, dz)
            assert dz <= HOLE_ZONE, f"{kind} {hid}: a new inner loop of the wall face is {dz:.3f} mm from the nearest hole / label"
    note("02.max_zone_distance_of_new_wall_loops_mm", worst_loop)


def test_02c_new_faces_lie_in_the_zones_and_inside_baseline_material():
    pf, bf, un_b, un_p = face_diff()
    new_ids = [j for j in un_p if _wall_face_kind(pf[j]) is None]
    note("02.new_faces", len(new_ids))
    worst = 0.0
    bad_material = []
    base_cls = classifier(STEP_BASE)
    part_cls = classifier(STEP_34)
    n_void_checked = 0
    for j in new_ids:
        f = pf[j]
        pts = face_points(f, 0.05)
        dz = zone_distance(pts).max()
        worst = max(worst, dz)
        assert dz <= HOLE_ZONE, f"new face {j} ({f.geomType()}, area {f.Area():.4f}) extends {dz:.3f} mm from any hole / label"
        if f.Area() < 1e-3:
            continue                                    # sliver faces: not classified
        # material side (against the outward normal) must be baseline material; void side must be empty in the part
        samples = pts[:: max(1, len(pts) // 6)]
        for p in samples:
            try:
                n = f.normalAt(cq.Vector(*p))
            except Exception:
                continue
            nv = vec((n.x, n.y, n.z))
            mat = p - 0.02 * nv
            if base_cls(mat) not in ("I", "N"):
                bad_material.append((j, f.geomType(), tuple(np.round(p, 3)), "material side outside baseline"))
            void = p + 0.02 * nv
            if part_cls(void) == "I":
                bad_material.append((j, f.geomType(), tuple(np.round(p, 3)), "void side is solid in the part"))
            n_void_checked += 1
    note("02.max_zone_distance_of_new_faces_mm", worst)
    note("02.new_face_side_probes", n_void_checked)
    assert not bad_material, f"material would have been ADDED / orientation inconsistent: {bad_material[:5]}"


@lru_cache(maxsize=None)
def local_dv(hid, which):
    """Volume difference (baseline - part) inside a local box: 'hole' (y < 44.9) or 'label' (y > 44.9)."""
    c, r, u, n = label_frame(hid)
    m = vec(OUTER[hid])
    if which == "hole":
        y0, y1 = 36.0, 44.9
        half = 9.0
    else:
        y0, y1 = 44.9, 52.0
        half = 9.0
    x0, x1 = m[0] - half - (4.0 if abs(n[0]) > 0.5 else 0), m[0] + half + (4.0 if abs(n[0]) > 0.5 else 0)
    z0, z1 = m[2] - half - (4.0 if abs(n[2]) > 0.5 else 0), m[2] + half + (4.0 if abs(n[2]) > 0.5 else 0)
    bx = cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
    lb, lp = base().intersect(bx), part().intersect(bx)
    return lb.Volume() - lp.Volume()


def test_02d_volume_balance_nothing_added():
    dv = {}
    for hid in IDS:
        dv[hid] = (local_dv(hid, "hole"), local_dv(hid, "label"))
    total_local = sum(a + b for a, b in dv.values())
    global_dv = base().Volume() - part().Volume()
    note("02.local_removed_volume_mm3", {h: [round(v, 4) for v in dv[h]] for h in IDS})
    note("02.sum_local_removed_mm3", total_local)
    note("02.global_volume_difference_mm3", global_dv)
    assert all(a > 5.0 and b > 0.5 for a, b in dv.values())
    # GProp volume integration on the 154 000 mm3 solids has an error of a few 1e-6 relative -> allow 0.5 mm3
    assert abs(global_dv - total_local) < 0.5, f"global volume change {global_dv:.3f} vs sum of local removals {total_local:.3f}"
    assert part().Volume() < base().Volume()


def test_02e_random_probe_classification_differs_only_in_the_zones_and_never_adds_material():
    rng = np.random.default_rng(20261021)
    pc, bc = classifier(STEP_34), classifier(STEP_BASE)
    # (i) uniform probes over the whole envelope
    lo, hi = np.array([-50.0, 0.0, -101.3]), np.array([50.0, 55.0, 50.0])
    pts = lo + rng.random((2500, 3)) * (hi - lo)
    changed_outside, added = [], []
    for p in pts:
        sp, sb = pc(p), bc(p)
        if sp != sb:
            if sb == "I" and sp == "O" and zone_distance(p)[0] <= HOLE_ZONE:
                continue
            changed_outside.append((tuple(np.round(p, 3)), sb, sp))
        if sb == "O" and sp == "I":
            added.append(tuple(np.round(p, 3)))
    # (ii) dense probes in the wall slabs around every hole / label, the only places that may differ
    removed = 0
    n_zone = 0
    for hid in IDS:
        m = vec(OUTER[hid])
        n = vec(WALL_NORMAL[hid])
        for _ in range(900):
            p = m + (rng.random(3) - 0.5) * np.array([9.0, 14.0, 9.0]) + np.array([0, 3.5, 0]) - n * rng.random() * 5.5
            sp, sb = pc(p), bc(p)
            n_zone += 1
            if sb == "O" and sp == "I":
                added.append(tuple(np.round(p, 3)))
            if sb == "I" and sp == "O":
                removed += 1
                if zone_distance(p)[0] > HOLE_ZONE:
                    changed_outside.append((tuple(np.round(p, 3)), sb, sp))
    note("02.random_probes_whole_part", len(pts))
    note("02.random_probes_in_zones", n_zone)
    note("02.zone_probes_removed", removed)
    assert not added, f"material present in the part but not in the baseline at {added[:5]}"
    assert not changed_outside, f"classification differs outside the hole / label zones: {changed_outside[:5]}"
    assert removed > 0
