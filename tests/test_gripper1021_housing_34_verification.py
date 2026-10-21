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
from OCP.Bnd import Bnd_Box                                          # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Surface                      # noqa: E402
from OCP.BRepBndLib import BRepBndLib                                # noqa: E402
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


def exact_bbox(shape):
    """Tight bounding box of the B-rep (no triangulation, no tolerance inflation: cq's BoundingBox() grows once a face has been meshed)."""
    from types import SimpleNamespace
    bb = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, bb, False, False)
    x0, y0, z0, x1, y1, z1 = bb.Get()
    return SimpleNamespace(xmin=x0, xmax=x1, ymin=y0, ymax=y1, zmin=z0, zmax=z1)


def bbox_tuple(shape):
    b = exact_bbox(shape)
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


@lru_cache(maxsize=None)
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
    # the part has 6 modified wall faces plus the new faces of the holes, chamfers and labels (91 here)
    note("02.new_faces_total_incl_slivers", len(un_p) - 6)
    assert len(un_p) - 6 > 0


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
        # material side (against the outward normal) must be baseline material; void side must be empty in the part.
        # Probes use interior points (triangle centroids of a fine tessellation), never the face boundary.
        v, t = f.tessellate(0.005, 0.2)
        vv = np.array([(q.x, q.y, q.z) for q in v], float)
        cen = vv[np.array(t, int)].mean(axis=1)
        for p in cen[:: max(1, len(cen) // 6)]:
            n = f.normalAt(cq.Vector(*p))
            nv = vec((n.x, n.y, n.z))
            mat = p - 0.04 * nv
            if base_cls(mat) not in ("I", "N"):
                bad_material.append((j, f.geomType(), tuple(np.round(p, 3)), "material side outside baseline"))
            void = p + 0.04 * nv
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


# =====================================================================================================================================
# 3. HOLE MOUTHS, BORE, TEARDROP, CHAMFER, THROUGH-WALL
# =====================================================================================================================================
def plane_hit(loc, d, hid, which):
    """Intersection of the axis line (loc + s d) with the outer / inner wall plane of hole `hid`."""
    n = vec(WALL_NORMAL[hid])
    pos = vec(OUTER[hid]) if which == "outer" else vec(INNER[hid])
    s = np.dot(pos - loc, n) / np.dot(d, n)
    return loc + s * d


@lru_cache(maxsize=None)
def measured_axis(hid):
    """Axis of the Ø2 bore, from the exact cylinder surface of the STEP B-rep (oriented outward)."""
    cyls = hole_bore_cylinder(hid)
    assert len(cyls) >= 1, f"hole {hid}: no Ø2 cylinder face found"
    r, loc, d = cylinder_params(cyls[0])
    if np.dot(d, axis_out(hid)) < 0:
        d = -d
    for f in cyls[1:]:
        r2, loc2, d2 = cylinder_params(f)
        assert abs(r2 - r) < 1e-6 and np.linalg.norm(np.cross(d, d2 if np.dot(d, d2) > 0 else -d2)) < 1e-6
    return {"radius": r, "loc": loc, "dir": d, "n_faces": len(cyls)}


@pytest.mark.parametrize("hid", IDS)
def test_03a_bore_axis_diameter_and_mouth_positions_from_brep(hid):
    ax = measured_axis(hid)
    loc, d = ax["loc"], ax["dir"]
    exp_a = axis_out(hid)
    ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(d, exp_a))))))
    radial_off = abs(loc[0] * d[2] - loc[2] * d[0]) / math.hypot(d[0], d[2])      # distance of the axis (plan view) from the tube axis
    outer = plane_hit(loc, d, hid, "outer")
    inner = plane_hit(loc, d, hid, "inner")
    e_out = np.abs(outer - vec(OUTER[hid])).max()
    e_in = np.abs(inner - vec(INNER[hid])).max()
    wall_len = float(np.linalg.norm(outer - inner))
    note(f"03.{hid}.bore_radius_mm", ax["radius"])
    note(f"03.{hid}.axis_angle_error_deg", ang)
    note(f"03.{hid}.axis_vertical_component", float(d[1]))
    note(f"03.{hid}.axis_height_y", float(loc[1]))
    note(f"03.{hid}.axis_distance_from_tube_axis_mm", float(radial_off))
    note(f"03.{hid}.outer_mouth_measured", [round(float(v), 4) for v in outer])
    note(f"03.{hid}.inner_mouth_measured", [round(float(v), 4) for v in inner])
    note(f"03.{hid}.outer_mouth_max_error_mm", float(e_out))
    note(f"03.{hid}.inner_mouth_max_error_mm", float(e_in))
    note(f"03.{hid}.wall_length_mm", wall_len)
    assert abs(2 * ax["radius"] - 2.0) < 2e-4, f"bore diameter {2 * ax['radius']}"
    assert ang < 0.1, f"axis direction off by {ang} deg"
    assert abs(d[1]) < 1e-6, "axis is not horizontal"
    assert abs(loc[1] - 42.0) < 5e-3, f"axis height {loc[1]}"
    assert radial_off < 0.01, f"axis misses the tube axis by {radial_off} mm (not radial)"
    assert e_out < 0.01 and e_in < 0.01, f"mouth centres off by {e_out} / {e_in} mm"
    assert abs(wall_len - WALL_LEN[hid]) < 0.01


@pytest.mark.parametrize("hid", IDS)
def test_03b_teardrop_tip_points_up_at_45_degrees(hid):
    ax = measured_axis(hid)
    loc, d = ax["loc"], ax["dir"]
    e1 = unit(np.cross([0.0, 1.0, 0.0], d))
    flanks = []
    for f in hole_new_faces(hid):
        if f.geomType() != "PLANE" or f.Area() < 1.0:
            continue
        n = f.normalAt()
        nv = vec((n.x, n.y, n.z))
        if abs(np.dot(nv, d)) < 1e-3 and abs(abs(nv[1]) - math.sqrt(0.5)) < 5e-3:
            c = f.Center()
            flanks.append((nv, vec((c.x, c.y, c.z))))
    note(f"03.{hid}.flank_planes", len(flanks))
    assert len(flanks) == 2, f"expected two 45 degree flank planes, found {len(flanks)}"
    # normals point out of the solid = into the void; tip up  <=>  both normals point DOWN (-y)
    assert all(n[1] < 0 for n, _ in flanks), "flank normals do not point down: the tip does not point +y"
    lat = [float(np.dot(n, e1)) for n, _ in flanks]
    assert lat[0] * lat[1] < 0
    # apex: intersection of the two flank planes in (lateral, vertical) coordinates
    A = np.array([[np.dot(n, e1), n[1]] for n, _ in flanks])
    rhs = np.array([np.dot(n, p - loc) for n, p in flanks])
    lat_apex, y_rel = np.linalg.solve(A, rhs)
    half_angle = math.degrees(math.atan2(abs(np.dot(flanks[0][0], e1)), abs(flanks[0][0][1])))
    note(f"03.{hid}.tip_apex_above_axis_mm", float(y_rel))
    note(f"03.{hid}.tip_apex_lateral_mm", float(lat_apex))
    note(f"03.{hid}.tip_flank_angle_from_vertical_deg", half_angle)
    assert abs(y_rel - 1.0 / math.sin(math.radians(45))) < 0.005, f"apex {y_rel} mm above the axis"
    assert abs(lat_apex) < 0.005
    assert abs(half_angle - TIP_HALF_DEG) < 0.1


def _frame(hid):
    ax = measured_axis(hid)
    a = ax["dir"]
    return ax["loc"], a, unit(np.cross([0.0, 1.0, 0.0], a)), np.array([0.0, 1.0, 0.0])


def _axis_point(hid, s_from_inner):
    loc, a, _, _ = _frame(hid)
    inner = plane_hit(loc, a, hid, "inner")
    return inner + a * s_from_inner


@pytest.mark.parametrize("hid", IDS)
def test_03c_through_wall_probe_lines(hid):
    """Lines along the axis (and offset lines inside the Ø2 teardrop) from 4 mm inside the pocket to 4 mm outside: nothing solid.
    Point-in-solid probes along the axis plus exact OCC edge-solid common on six lines."""
    loc, a, e1, e2 = _frame(hid)
    L = WALL_LEN[hid]
    ss = np.arange(-4.0, L + 4.0 + 1e-9, 0.25)
    solid_hits = [round(float(s), 3) for s in ss if is_solid34(_axis_point(hid, s))]
    # the baseline must have wall material on the same line (so the hole really cuts something)
    base_wall_ok = all(is_solid_base(_axis_point(hid, s)) for s in np.arange(0.15, L - 0.1, 0.25))
    offsets = [(0.0, 0.0), (0.9, 0.0), (-0.9, 0.0), (0.0, -0.9), (0.0, 0.9), (0.0, 1.3)]       # (lateral, vertical) inside the teardrop
    lens = {}
    for du, dv in offsets:
        p0 = _axis_point(hid, -4.0) + e1 * du + e2 * dv
        p1 = _axis_point(hid, L + 4.0) + e1 * du + e2 * dv
        edge = cq.Edge.makeLine(cq.Vector(*p0), cq.Vector(*p1))
        common = part().intersect(edge)
        lens[(du, dv)] = sum(e.Length() for e in common.Edges()) if common.Edges() else 0.0
        # the same line through the baseline must cut through the wall (>= 4 mm of material)
        cb = base().intersect(edge)
        lens[("base", du, dv)] = sum(e.Length() for e in cb.Edges()) if cb.Edges() else 0.0
    note(f"03.{hid}.probe_points_on_axis", len(ss))
    note(f"03.{hid}.solid_hits_on_axis", solid_hits)
    note(f"03.{hid}.baseline_has_wall_material_on_axis", bool(base_wall_ok))
    note(f"03.{hid}.occ_edge_lengths_inside_part_mm", {str(k): round(v, 6) for k, v in lens.items() if k[0] != "base"})
    note(f"03.{hid}.occ_edge_lengths_inside_baseline_mm", {str(k[1:]): round(v, 4) for k, v in lens.items() if k[0] == "base"})
    assert base_wall_ok, "baseline has no wall material along the axis: nothing to cut"
    assert not solid_hits, f"hole is blocked at {solid_hits[:5]}"
    for k, v in lens.items():
        if k[0] == "base":
            assert v > 4.0, f"baseline line {k} has only {v} mm of wall material"
        else:
            assert v < 1e-6, f"OCC: line {k} has {v} mm inside the part"


@lru_cache(maxsize=None)
def local_classifier(hid, path=STEP_34):
    """Point classifier of a solid (part or baseline) restricted to a 24 mm box around the hole's outer mouth."""
    m = vec(OUTER[hid])
    bx = cq.Solid.makeBox(24.0, 24.0, 24.0, cq.Vector(m[0] - 12.0, m[1] - 12.0, m[2] - 12.0))
    loc_solid = load_box(path).intersect(bx)
    c = BRepClass3d_SolidClassifier(loc_solid.wrapped)

    def state(p):
        c.Perform(gp_Pnt(float(p[0]), float(p[1]), float(p[2])), 1e-7)
        st = c.State()
        return "I" if st == TopAbs_IN else ("O" if st == TopAbs_OUT else "N")

    return state


@pytest.mark.parametrize("hid", IDS)
def test_03d_probed_bore_size_and_teardrop_shape(hid):
    """Diameter / tip / bottom from point-in-solid bisection at mid-wall, on the part itself."""
    loc, a, e1, e2 = _frame(hid)
    L = WALL_LEN[hid]
    s_mid = L / 2.0
    c0 = _axis_point(hid, s_mid)

    def edge_of(direction, start, far):
        t = bisect_boundary(is_empty34, start, start + direction * far, tol=2e-4)
        return t * far

    right = edge_of(e1, c0, 1.8)
    left = edge_of(-e1, c0, 1.8)
    down = edge_of(-e2, c0, 1.8)
    up = edge_of(e2, c0, 2.5)                 # along the vertical through the axis: ends at the tip apex
    note(f"03.{hid}.probed_halfwidth_right_left_mm", [right, left])
    note(f"03.{hid}.probed_bottom_below_axis_mm", down)
    note(f"03.{hid}.probed_apex_above_axis_mm", up)
    assert abs(right - 1.0) < 0.01 and abs(left - 1.0) < 0.01, f"half widths {right}, {left}"
    assert abs(down - 1.0) < 0.01, f"bottom {down}"
    assert abs(up - math.sqrt(2.0)) < 0.01, f"tip apex {up}"
    # 45 degree flank: half width as a function of height above the axis, w = sqrt(2) - h
    for h in (0.9, 1.1, 1.25):
        base_pt = c0 + e2 * h
        assert is_empty34(base_pt)
        w = edge_of(e1, base_pt, 1.5)
        note(f"03.{hid}.flank_halfwidth_at_h{h}", w)
        assert abs(w - (math.sqrt(2.0) - h)) < 0.012, f"flank half width at h={h}: {w} (expected {math.sqrt(2.0) - h:.4f})"
    # below the axis the section is the plain circle: half width at height -0.6 is sqrt(1 - 0.36) = 0.8
    w = edge_of(e1, c0 - e2 * 0.6, 1.5)
    assert abs(w - 0.8) < 0.01
    # cross-section area on a 0.05 mm probe grid (local copy of the part around the hole: same solid, far fewer faces, fast probes)
    loc_cls = local_classifier(hid)
    rng = np.random.default_rng(3)
    for _ in range(40):                                              # the local copy must classify exactly like the full part
        q = c0 + e1 * rng.uniform(-1.8, 1.8) + e2 * rng.uniform(-1.4, 1.9)
        assert loc_cls(q) == classifier(STEP_34)(q) or "N" in (loc_cls(q), classifier(STEP_34)(q))
    n_in = 0
    step = 0.05
    for u in np.arange(-1.6, 1.6 + 1e-9, step):
        for v in np.arange(-1.3, 1.9 + 1e-9, step):
            if loc_cls(c0 + e1 * u + e2 * v) == "O":
                n_in += 1
    area = n_in * step * step
    exp_area = 1.0 * (math.pi / 2 + math.radians(45) + 1.0 / math.tan(math.radians(45)))
    note(f"03.{hid}.probed_section_area_mm2", area)
    note(f"03.{hid}.expected_section_area_mm2", exp_area)
    assert abs(area - exp_area) / exp_area < 0.02


def _chamfer_profile_points(hid, side):
    """Equal-distance 0.5 x 0.5 chamfer of the outer mouth edge, measured in the plane PERPENDICULAR to the edge tangent:
      bottom : edge tangent horizontal along the wall trace -> section plane (wall normal, vertical); F = E - 0.5 y (down the wall face),
               G = E - 0.5 n (into the wall, in the horizontal tangent plane of the bore bottom);
      left / right : edge tangent vertical -> horizontal section through the axis; F = E + 0.5 t (along the wall trace, away from the hole),
               G = E - 0.5 a (back along the bore generatrix).
    Returns E, F, G, normal of the section plane, unit vector from the bore surface towards the axis at G."""
    loc, a, e1, e2 = _frame(hid)
    n = vec(WALL_NORMAL[hid])
    O = plane_hit(loc, a, hid, "outer")
    if side == "bottom":
        E = O - e2 * 1.0
        F = E - e2 * CHAMFER
        G = E - n * CHAMFER
        plane_n = unit(np.cross([0.0, 1.0, 0.0], n))
        toward = e2.copy()
    else:
        sgn = 1.0 if side == "right" else -1.0
        lam = -(sgn * np.dot(e1, n)) / np.dot(a, n)
        E = O + sgn * e1 * 1.0 + lam * a
        t = unit(np.cross([0.0, 1.0, 0.0], n))
        if np.dot(t, sgn * e1) < 0:
            t = -t
        F = E + t * CHAMFER
        G = E - a * CHAMFER
        plane_n = np.array([0.0, 1.0, 0.0])
        toward = -sgn * e1
    return E, F, G, plane_n, toward


@pytest.mark.parametrize("side", ["bottom", "right", "left"])
@pytest.mark.parametrize("hid", IDS)
def test_03e_chamfer_is_a_half_by_half_chamfer_on_the_outer_mouth(hid, side):
    loc, a, e1, e2 = _frame(hid)
    n = vec(WALL_NORMAL[hid])
    E, F, G, plane_n, toward = _chamfer_profile_points(hid, side)
    fg = G - F
    nrm = unit(np.cross(plane_n, fg))                       # in-section normal of the chamfer line
    mid = (F + G) / 2.0
    to_axis = (loc + a * np.dot(mid - loc, a)) - mid
    if np.dot(nrm, to_axis) < 0:
        nrm = -nrm
    failures = []
    off = 0.03 if side != "bottom" or hid == "C" else 0.06      # oblique bottom: the bore bottom curves away from G (lateral 0.25 mm)
    for lam in (0.12, 0.5, 0.88):
        H = F + fg * lam
        if not is_empty34(H + nrm * off):
            failures.append(("void side solid", lam))
        if not is_solid34(H - nrm * off):
            failures.append(("material side empty", lam))
    # the chamfer ends 0.5 mm inside the wall (along the bore): just past G the surface is the plain bore
    past = G - (n if side == "bottom" else a) * 0.06
    if side == "bottom":
        lat = float(np.dot(past - loc, e1))
        yb = 42.0 - math.sqrt(max(1.0 - lat * lat, 0.0))
        probe_empty, probe_solid = np.array([past[0], yb + off, past[2]]), np.array([past[0], yb - off, past[2]])
    else:
        probe_empty, probe_solid = past + toward * off, past - toward * off
    if not is_empty34(probe_empty):
        failures.append(("bore side past G solid", 0))
    if not is_solid34(probe_solid):
        failures.append(("past G material empty (chamfer deeper than 0.5)", 0))
    # just before the start F on the wall face (outside the chamfer width) the face is intact
    start = F + unit(F - G) * 0.0 + (F - E) * 0.12
    if not is_solid34(start - n * 0.02):
        failures.append(("wall face beyond the 0.5 chamfer width is cut", 0))
    ang_axis = math.degrees(math.acos(abs(np.dot(unit(fg), a))))
    ang_face = math.degrees(math.acos(abs(np.dot(unit(fg), unit(F - E)))))
    note(f"03.{hid}.chamfer_{side}_profile_angle_to_axis_deg", ang_axis)
    note(f"03.{hid}.chamfer_{side}_profile_angle_to_wall_face_deg", ang_face)
    note(f"03.{hid}.chamfer_{side}_failures", failures)
    assert not failures, f"chamfer profile ({side}) deviates from the 0.5 x 0.5 chamfer: {failures}"


def test_03f_cone_chamfer_of_the_perpendicular_hole_C_is_45_degrees():
    pf, _, _, un_p = face_diff()
    cones = []
    for f in hole_new_faces("C"):
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() == GeomAbs_Cone:
            co = ad.Cone()
            ap = co.Apex()
            d = co.Axis().Direction()
            cones.append((math.degrees(co.SemiAngle()), vec((ap.X(), ap.Y(), ap.Z())), vec((d.X(), d.Y(), d.Z()))))
    assert len(cones) == 1
    semi, apex, d = cones[0]
    if d[2] > 0:
        d = -d
    r_at_outer = abs(apex[2] - (-45.0))                     # cone radius = distance from apex along the axis (45 deg)
    r_at_half = abs(apex[2] - (-44.5))
    note("03.C.cone_semi_angle_deg", semi)
    note("03.C.cone_apex", [float(v) for v in apex])
    note("03.C.cone_radius_at_outer_plane_mm", r_at_outer)
    note("03.C.cone_radius_0.5_inside_mm", r_at_half)
    assert abs(semi - 45.0) < 0.01
    assert abs(r_at_outer - 1.5) < 0.005 and abs(r_at_half - 1.0) < 0.005
    assert abs(apex[0]) < 1e-6 and abs(apex[1] - 42.0) < 1e-6


# =====================================================================================================================================
# 4. REMOVED VOLUME PER HOLE vs THE DESIGNED CUTTER (bore + teardrop + chamfer), spec 5.1 item 1: within 10 %
# =====================================================================================================================================
def teardrop_polygon(sx=1.0, n_arc=2400, r=1.0, k_deg=45.0):
    """Teardrop outline (circle + 45 degree tangent tip up), counter-clockwise, lateral axis stretched by sx (oblique section)."""
    k = math.radians(k_deg)
    tip = r / math.sin(k)
    a0 = math.pi / 2 + (math.pi / 2 - k)                           # polar angle of the left tangent point (135 deg)
    a1 = a0 + (2 * math.pi - 2 * (math.pi / 2 - k))                # right tangent point after going round the bottom (405 deg)
    ang = np.linspace(a0, a1, n_arc)
    arc = np.stack([r * np.cos(ang), r * np.sin(ang)], axis=1)
    poly = np.vstack([[0.0, tip], arc])
    poly[:, 0] *= sx
    return poly


def polygon_area(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def mitred_offset_area(poly, d):
    """Area of a convex CCW polygon offset outward by d with mitred corners."""
    e = np.roll(poly, -1, axis=0) - poly
    ln = np.linalg.norm(e, axis=1)
    keep = ln > 1e-12
    poly, e, ln = poly[keep], e[keep], ln[keep]
    nrm = np.stack([e[:, 1], -e[:, 0]], axis=1) / ln[:, None]       # outward normal of a CCW polygon
    nprev = np.roll(nrm, 1, axis=0)
    new = poly + d * (nrm + nprev) / (1.0 + np.sum(nrm * nprev, axis=1))[:, None]
    return polygon_area(new)


def designed_cutter_volume(hid):
    """Independent model of the designed cutter: Ø2 teardrop prism through the wall plus a 0.5 x 0.5 chamfer at the outer mouth.
    Chamfer modelled as the wall-normal 45 degree mitred offset of the mouth section (area integrated over the depth)."""
    cos_t = abs(np.dot(axis_out(hid), vec(WALL_NORMAL[hid])))
    sx = 1.0 / cos_t
    poly = teardrop_polygon(1.0)
    a_perp = polygon_area(poly)
    bore = a_perp * WALL_LEN[hid]
    pm = teardrop_polygon(sx)
    a_b = polygon_area(pm)
    ds = np.linspace(0.0, CHAMFER, 201)
    extra_curve = np.array([mitred_offset_area(pm, CHAMFER - d) - a_b for d in ds])
    extra = float(np.trapezoid(extra_curve, ds))
    plain = math.pi * BORE_R ** 2 * WALL_LEN[hid]
    return {"plain_bore": plain, "teardrop_bore": bore, "chamfer_extra": extra, "designed": bore + extra, "a_perp": a_perp, "mouth_area_at_wall_plane": mitred_offset_area(pm, CHAMFER)}


@pytest.mark.parametrize("hid", IDS)
def test_04_removed_volume_within_10_percent_of_designed_cutter(hid):
    dv = local_dv(hid, "hole")
    des = designed_cutter_volume(hid)
    rel = dv / des["designed"] - 1.0
    rel_plain = dv / des["plain_bore"] - 1.0
    # second, independent estimate: Monte Carlo over a box around the hole (baseline solid & part empty)
    loc, a, e1, e2 = _frame(hid)
    inner = plane_hit(loc, a, hid, "inner")
    rng = np.random.default_rng(7 + IDS.index(hid))
    n = 3500
    s0, s1, u0, u1, v0, v1 = -0.6, WALL_LEN[hid] + 0.8, -1.9, 1.9, -1.9, 2.0
    smp = rng.random((n, 3)) * np.array([s1 - s0, u1 - u0, v1 - v0]) + np.array([s0, u0, v0])
    cnt = 0
    cb, cp = local_classifier(hid, STEP_BASE), local_classifier(hid, STEP_34)
    for s, u, v in smp:
        p = inner + a * s + e1 * u + e2 * v
        if cb(p) == "I" and cp(p) == "O":
            cnt += 1
    mc = cnt / n * (s1 - s0) * (u1 - u0) * (v1 - v0)
    mc_err = mc / math.sqrt(max(cnt, 1))
    note(f"04.{hid}.removed_volume_mm3", dv)
    note(f"04.{hid}.designed_cutter_mm3", des["designed"])
    note(f"04.{hid}.plain_d2_bore_mm3", des["plain_bore"])
    note(f"04.{hid}.teardrop_bore_mm3", des["teardrop_bore"])
    note(f"04.{hid}.model_chamfer_extra_mm3", des["chamfer_extra"])
    note(f"04.{hid}.measured_chamfer_extra_mm3", dv - des["teardrop_bore"])
    note(f"04.{hid}.removed_vs_designed_percent", 100 * rel)
    note(f"04.{hid}.removed_vs_plain_bore_percent", 100 * rel_plain)
    note(f"04.{hid}.monte_carlo_volume_mm3", [mc, mc_err])
    assert abs(rel) <= 0.10, f"removed {dv:.3f} mm3 vs designed cutter {des['designed']:.3f} mm3 ({100 * rel:+.2f} %)"
    assert abs(mc - dv) <= max(3 * mc_err, 0.06 * dv), f"Monte Carlo {mc:.2f} +- {mc_err:.2f} vs boolean volume difference {dv:.3f}"
    # the removed material must be only the hole: no part of it may lie outside the wall slab 40 .. 45 (checked via face positions)
    for f in hole_new_faces(hid):
        pts = face_points(f)
        along = (pts - vec(OUTER[hid])) @ vec(WALL_NORMAL[hid])
        assert along.max() < 1e-3 and along.min() > -5.0 - 1e-3, "hole face leaves the 5 mm wall slab"


# =====================================================================================================================================
# 5. KEEP-OUTS >= 5 mm
# =====================================================================================================================================
@lru_cache(maxsize=None)
def _raw_classifier():
    return BRepClass3d_SolidClassifier(load_box(STEP_RAW).wrapped)


def classify_face(f):
    """Feature category of a face of the housing (baseline or part)."""
    t = f.geomType()
    c = f.Center()
    b = exact_bbox(f)
    if t == "CYLINDER":
        r, loc, d = cylinder_params(f)
        if abs(r - 1.0) < 0.02 and b.ymax < 30.0:
            return "corner cable hole (Ø2)"
        if abs(r - 1.65) < 0.02:
            return "floor hole (Ø3.3)"
        if abs(r - 15.0) < 0.02:
            return "tube hole (Ø30)"
        if abs(r - 10.0) < 0.02 and abs(d[1]) > 0.99:
            return "pocket R10 fillet" if abs(abs(loc[0]) - 30.0) < 0.05 else "box corner R10"
    if t == "PLANE":
        n = f.normalAt()
        if abs(abs(n.y) - 1.0) < 1e-6 and abs(c.y - 50.0) < 1e-3:
            return "lid-seat ledge (y=50)"
        if abs(abs(n.y) - 1.0) < 1e-6 and abs(c.y - 55.0) < 1e-3:
            return "rim top (y=55)"
        if abs(n.y) < 1e-6 and b.ymin >= 49.99 and 42.4 < max(abs(c.x), abs(c.z)) < 42.6:
            return "lid-recess wall"
    # relation to Jasper's raw housing solid (1e-4 tolerance): faces lying OUTSIDE it are the bay, faces INSIDE its material are the cuts
    # (wire window), faces ON its surface are housing faces
    cls = _raw_classifier()
    pts = face_points(f, 0.2)
    states = set()
    for p in pts[:: max(1, len(pts) // 8)]:
        cls.Perform(gp_Pnt(float(p[0]), float(p[1]), float(p[2])), 1e-4)
        st = cls.State()
        states.add("IN" if st == TopAbs_IN else ("ON" if _on_boundary(cls) else "OUT"))
    if "OUT" in states:
        return "bay body"
    if "IN" in states:
        return "wire window / cut inside the raw wall"
    return "other housing face"


@lru_cache(maxsize=None)
def baseline_face_categories():
    """Category of every baseline face.  The 6 hole-bearing wall faces are 'own wall (excluded)'."""
    pf, bf, un_b, un_p = face_diff()
    return {i: ("own wall (excluded)" if i in un_b else classify_face(f)) for i, f in enumerate(bf)}


def _on_boundary(cls):
    from OCP.TopAbs import TopAbs_ON
    return cls.State() == TopAbs_ON


@lru_cache(maxsize=None)
def keepout_table():
    """Per hole and per feature category: minimum distance (OCC BRepExtrema) between the hole's new faces (bore, flanks, chamfer; the whole
    boundary of the removed volume except its two open caps) and every baseline face of that category."""
    pf, bf, un_b, un_p = face_diff()
    cats = baseline_face_categories()
    out = {}
    for hid in IDS:
        hole = cq.Compound.makeCompound(hole_new_faces(hid))
        hb = exact_bbox(hole)
        shp = {}
        for i, f in enumerate(bf):
            if cats[i].startswith("own wall"):
                continue
            b = exact_bbox(f)
            gap = max(b.xmin - hb.xmax, hb.xmin - b.xmax, b.ymin - hb.ymax, hb.ymin - b.ymax, b.zmin - hb.zmax, hb.zmin - b.zmax, 0.0)
            c = cats[i]
            if gap > 40.0:
                best = gap                                  # bounding boxes are > 40 mm apart: the distance is at least that (lower bound)
            else:
                dss = BRepExtrema_DistShapeShape(hole.wrapped, f.wrapped)
                dss.Perform()
                best = dss.Value() if dss.IsDone() else 1e9
            if c not in shp or best < shp[c][0]:
                shp[c] = (best, i)
        cover = load_box(STEP_COVER)
        cb_ = exact_bbox(cover)
        gap = max(cb_.xmin - hb.xmax, hb.xmin - cb_.xmax, cb_.ymin - hb.ymax, hb.ymin - cb_.ymax, cb_.zmin - hb.zmax, hb.zmin - cb_.zmax, 0.0)
        if gap > 40.0:
            shp["bay cover (separate part)"] = (gap, -1)
        else:
            dss = BRepExtrema_DistShapeShape(hole.wrapped, cover.wrapped)
            dss.Perform()
            shp["bay cover (separate part)"] = (dss.Value(), -1)
        out[hid] = shp
    return out


@pytest.mark.parametrize("hid", IDS)
def test_05_keepouts_at_least_5mm(hid):
    tab = keepout_table()[hid]
    cats = baseline_face_categories()
    note(f"05.{hid}.min_distance_by_feature_mm", {k: round(v[0], 3) for k, v in sorted(tab.items())})
    note(f"05.{hid}.note", "values >= 40 are bounding-box lower bounds, not exact distances")
    pf, bf, un_b, un_p = face_diff()
    nearest_overall = min((v[0], k) for k, v in tab.items() if k != "pocket R10 fillet")
    note(f"05.{hid}.nearest_non_exempt_feature", [nearest_overall[1], nearest_overall[0]])
    required = ["corner cable hole (Ø2)", "floor hole (Ø3.3)", "lid-seat ledge (y=50)", "bay body", "wire window / cut inside the raw wall",
                "bay cover (separate part)"]
    for k in required:
        assert k in tab, f"{hid}: no '{k}' faces found; the feature classification is incomplete"
    for k, (dist, idx) in tab.items():
        if k == "pocket R10 fillet":
            continue
        assert dist >= KEEPOUT - 1e-3, f"{hid}: {dist:.3f} mm to '{k}' (face {idx})"
    if "pocket R10 fillet" in tab:
        d = tab["pocket R10 fillet"][0]
        note(f"05.{hid}.pocket_R10_fillet_mm_exempt_per_5_1", d)
        assert d >= 4.95, f"{hid}: pocket fillet distance {d:.3f} mm is below the accepted 4.98 mm"


# =====================================================================================================================================
# 6. LABELS  "C" above T_C, "A" above T_A, "B" above T_B
# =====================================================================================================================================
PPMM = 100            # raster resolution for the glyph masks (pixels per mm)
HALF_FIELD = 3.2      # mm, half size of the raster window around the label centre


def read_stl(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    assert 84 + 50 * n == len(d), "not a binary STL of the expected size"
    arr = np.frombuffer(d, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)
    return arr["v"].astype(float), arr["n"].astype(float)


def box_to_print(p):
    """Print orientation: bay frame rotated +90 deg about X, (x, y, z) -> (x, -z, y), bottom plane y=0 on the bed z=0."""
    p = np.asarray(p, float)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], axis=-1)


def rasterize(tris_uv, field=HALF_FIELD, ppmm=PPMM):
    from PIL import Image, ImageDraw
    n = int(2 * field * ppmm)
    img = Image.new("L", (n, n), 0)
    dr = ImageDraw.Draw(img)
    for t in tris_uv:
        pts = [((u + field) * ppmm, (field - v) * ppmm) for u, v in t]            # row 0 = top (+v)
        dr.polygon(pts, fill=255)
    return np.array(img) > 127


def mask_axes(field=HALF_FIELD, ppmm=PPMM):
    n = int(2 * field * ppmm)
    u = (np.arange(n) + 0.5) / ppmm - field
    v = field - (np.arange(n) + 0.5) / ppmm
    return u, v


@lru_cache(maxsize=None)
def label_floor_mask(hid):
    """Mask of the debossed glyph (reader's frame: columns = reader's right, rows = up) from the exact floor faces of the STEP."""
    pf, _, _, un_p = face_diff()
    c, right, up, n = label_frame(hid)
    O = vec(OUTER[hid])
    tris, depths = [], []
    for j in un_p:
        f = pf[j]
        if f.geomType() != "PLANE" or f.Area() > 50:
            continue
        nn = f.normalAt()
        nv = vec((nn.x, nn.y, nn.z))
        ctr = f.Center()
        cv = vec((ctr.x, ctr.y, ctr.z))
        if np.dot(nv, n) > 0.999 and abs(np.dot(cv - O, n) + LABEL_DEPTH) < 0.02 and abs(np.dot(cv - c, right)) < 4 and abs(cv[1] - c[1]) < 3.2:
            v, t = f.tessellate(0.002, 0.1)
            vv = np.array([(q.x, q.y, q.z) for q in v], float)
            for tri in np.array(t, int):
                p3 = vv[tri]
                tris.append([((p - c) @ right, (p - c) @ up) for p in p3])
            depths.append(float(np.dot(cv - O, n)))
    assert tris, f"label {hid}: no recess floor faces found at depth {LABEL_DEPTH}"
    return rasterize(tris), depths


def glyph_stats(mask):
    u, v = mask_axes()
    rows, cols = np.nonzero(mask)
    half = 0.5 / PPMM
    umin, umax = u[cols.min()] - half, u[cols.max()] + half
    vmax, vmin = v[rows.min()] + half, v[rows.max()] - half
    area = mask.sum() / PPMM ** 2
    cu = float(u[cols].mean())
    cv_ = float(v[rows].mean())
    return {"u_min": umin, "u_max": umax, "v_min": vmin, "v_max": vmax, "width": umax - umin, "height": vmax - vmin,
            "centre_u": 0.5 * (umin + umax), "centre_v": 0.5 * (vmin + vmax), "area_mm2": area, "centroid_u": cu, "centroid_v": cv_}


def ascii_glyph(mask, cols=44):
    """Down-sampled ASCII picture of the glyph as the reader sees it (up = up, right = reader's right)."""
    ys, xs = np.nonzero(mask)
    sub = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    step_x = max(1, sub.shape[1] // cols)
    step_y = step_x * 2
    lines = []
    for r in range(0, sub.shape[0], step_y):
        row = ""
        for c in range(0, sub.shape[1], step_x):
            blk = sub[r:r + step_y, c:c + step_x]
            row += "#" if blk.mean() > 0.5 else "."
        lines.append(row)
    return "\n".join(lines)


def thin_stroke_residual(mask, d_mm):
    """Area (mm2) of the largest connected piece of the glyph that a disk of diameter d_mm cannot reach (opening residual)."""
    from scipy import ndimage as ndi
    r = d_mm / 2.0 * PPMM
    pad = np.pad(mask, 2)
    er = ndi.distance_transform_edt(pad) >= r
    opened = ndi.distance_transform_edt(~er) <= r
    res = pad & ~opened
    lab, nlab = ndi.label(res)
    if nlab == 0:
        return 0.0, 0.0
    sizes = ndi.sum(res, lab, index=np.arange(1, nlab + 1)) / PPMM ** 2
    return float(sizes.max()), float(res.sum() / max(pad.sum(), 1))


def thinnest_stroke_width(mask, piece_mm2=0.03):
    """Largest disk diameter (0.01 mm steps) whose opening leaves no connected glyph piece bigger than piece_mm2 (corner rounding only)."""
    best = 0.0
    for d in np.arange(0.20, 0.80, 0.01):
        big, _ = thin_stroke_residual(mask, float(d))
        if big > piece_mm2:
            break
        best = float(d)
    return best


def median_stroke_width(mask):
    from scipy import ndimage as ndi
    edt = ndi.distance_transform_edt(np.pad(mask, 2))
    mx = ndi.maximum_filter(edt, size=3)
    ridge = (edt >= mx - 1e-9) & (edt > 1.0)
    return float(2.0 * np.median(edt[ridge]) / PPMM), float(2.0 * np.percentile(edt[ridge], 10) / PPMM)


def reading_checks(hid, mask):
    """Orientation of the glyph in the reader's frame.  Returns {check: bool}."""
    u, v = mask_axes()
    st = glyph_stats(mask)
    rows, cols = np.nonzero(mask)
    out = {}
    h = st["height"]

    def row_extent(vc, half=0.15):
        sel = (np.abs(v[:, None] - vc) < half) & mask
        cc = np.nonzero(sel.any(axis=0))[0]
        return (u[cc.min()], u[cc.max()]) if len(cc) else (None, None)

    if hid == "C":
        mid = row_extent(st["centre_v"])
        top = row_extent(st["v_max"] - 0.45)
        bot = row_extent(st["v_min"] + 0.45)
        # a C is open to the right: at mid height the glyph ends well left of where the top / bottom arms end
        out["opening_on_reader_right"] = mid[1] < top[1] - 0.25 and mid[1] < bot[1] - 0.25
        out["mass_left_of_bbox_centre"] = st["centroid_u"] < st["centre_u"] - 0.05
    elif hid == "B":
        stem = mask[:, np.searchsorted(u, st["u_min"] + 0.05):np.searchsorted(u, st["u_min"] + 0.30)]
        rows_span = np.nonzero(mask.any(axis=1))[0]
        frac_left = stem[rows_span.min():rows_span.max() + 1].any(axis=1).mean()
        right_edge = mask[:, np.searchsorted(u, st["u_max"] - 0.30):np.searchsorted(u, st["u_max"] - 0.05)]
        frac_right = right_edge[rows_span.min():rows_span.max() + 1].any(axis=1).mean()
        out["stem_on_reader_left"] = frac_left > 0.97 and frac_right < 0.9
        out["mass_left_of_bbox_centre"] = st["centroid_u"] < st["centre_u"] - 0.05
    elif hid == "A":
        top = row_extent(st["v_max"] - 0.4)
        bot = row_extent(st["v_min"] + 0.4)
        out["apex_up_narrow_top_wide_bottom"] = (top[1] - top[0]) < 0.6 * (bot[1] - bot[0])
        out["left_right_symmetric"] = abs(st["centroid_u"] - st["centre_u"]) < 0.06
        out["bottom_heavy"] = st["centroid_v"] < st["centre_v"] - 0.05
    return out


@pytest.mark.parametrize("hid", IDS)
def test_06a_label_size_depth_position_and_reading_direction_from_step(hid):
    mask, depths = label_floor_mask(hid)
    st = glyph_stats(mask)
    vol_label = local_dv(hid, "label")
    chk = reading_checks(hid, mask)
    big, frac = thin_stroke_residual(mask, 0.40)
    big45, frac45 = thin_stroke_residual(mask, 0.45)
    big50, _ = thin_stroke_residual(mask, 0.50)
    med_w, p10_w = median_stroke_width(mask)
    note(f"06.{hid}.thinnest_stroke_width_mm", thinnest_stroke_width(mask))
    c, right, up, n = label_frame(hid)
    note(f"06.{hid}.glyph_height_mm", st["height"])
    note(f"06.{hid}.glyph_width_mm", st["width"])
    note(f"06.{hid}.glyph_centre_above_mouth_mm", 5.0 + st["centre_v"])
    note(f"06.{hid}.glyph_centre_lateral_offset_mm", st["centre_u"])
    note(f"06.{hid}.depth_mm", [round(d, 4) for d in depths])
    note(f"06.{hid}.glyph_area_mm2", st["area_mm2"])
    note(f"06.{hid}.area_x_depth_vs_removed_volume_mm3", [st["area_mm2"] * LABEL_DEPTH, vol_label])
    note(f"06.{hid}.reading_checks", chk)
    note(f"06.{hid}.largest_piece_not_reached_by_0.40_disk_mm2", big)
    note(f"06.{hid}.largest_piece_not_reached_by_0.45_disk_mm2", big45)
    note(f"06.{hid}.largest_piece_not_reached_by_0.50_disk_mm2", big50)
    note(f"06.{hid}.stroke_width_median_p10_mm", [med_w, p10_w])
    note(f"06.{hid}.ascii_as_read_from_outside", ascii_glyph(mask))
    assert abs(st["height"] - LABEL_H) < 0.05, f"glyph height {st['height']:.3f}"
    assert all(abs(d + LABEL_DEPTH) < 0.01 for d in depths), f"depth {depths}"
    assert abs(st["centre_v"]) < 0.1, f"glyph centre is {5.0 + st['centre_v']:.3f} mm above the mouth (expected 5)"
    assert abs(st["centre_u"]) < 0.2, f"glyph centre is {st['centre_u']:.3f} mm off the mouth axis laterally"
    assert abs(st["area_mm2"] * LABEL_DEPTH - vol_label) / vol_label < 0.03
    assert chk and all(chk.values()), f"reading-direction checks failed: {chk}"
    # all of the glyph lies on the flat part of the wall, below the rim and above the hole's chamfer
    lat_ok = abs(np.dot(c - vec(OUTER[hid]), right) + st["u_max"]) < 35.0 and abs(np.dot(c - vec(OUTER[hid]), right) + st["u_min"]) < 35.0
    assert lat_ok
    y_bottom, y_top = 42.0 + 5.0 + st["v_min"], 42.0 + 5.0 + st["v_max"]
    note(f"06.{hid}.glyph_y_range_box", [y_bottom, y_top])
    assert y_bottom - 44.2 > 0.5, f"glyph bottom {y_bottom:.2f} is less than 0.5 mm above the hole's chamfer top (y 44.12)"
    assert 50.0 - y_top > 0.5, f"glyph top {y_top:.2f} is less than 0.5 mm below the lid-seat ledge (y 50)"


@pytest.mark.parametrize("hid", IDS)
def test_06b_label_strokes_at_least_0p4mm_wide(hid):
    mask, _ = label_floor_mask(hid)
    big, frac = thin_stroke_residual(mask, 0.40)
    w = thinnest_stroke_width(mask)
    # corner rounding of the opening leaves small pieces (< ~0.02 mm2 each); a thinner stroke would leave a long piece
    assert big < 0.03, f"a piece of {big:.3f} mm2 of the glyph is thinner than 0.40 mm"
    assert w >= 0.40, f"thinnest stroke {w:.2f} mm"


@pytest.mark.parametrize("hid", IDS)
def test_06c_label_reads_correctly_in_the_stl_in_print_orientation(hid):
    """Independent of the STEP faces and of the label_frame formula: ray-cast a depth image of the wall from OUTSIDE the STL
    (print orientation) with the camera 'right' computed as forward x up, and compare to the STEP-derived glyph mask."""
    tris, _ = read_stl(STL_34)                                      # already in print orientation
    n_box = vec(WALL_NORMAL[hid])
    n = box_to_print(n_box)
    centre = box_to_print(vec(OUTER[hid]) + np.array([0.0, LABEL_ABOVE, 0.0]))
    up = np.array([0.0, 0.0, 1.0])
    fwd = -n
    right = np.cross(fwd, up)
    # local triangles
    lo, hi = centre - 8.0, centre + 8.0
    sel = np.all(tris.max(axis=1) >= lo, axis=1) & np.all(tris.min(axis=1) <= hi, axis=1)
    loc_tris = tris[sel]
    ppmm = 25
    field = 3.2
    nn = int(2 * field * ppmm)
    uu = (np.arange(nn) + 0.5) / ppmm - field
    vv = field - (np.arange(nn) + 0.5) / ppmm
    U, V = np.meshgrid(uu, vv)
    origins = centre[None, None, :] + right[None, None, :] * U[..., None] + up[None, None, :] * V[..., None] + n[None, None, :] * 2.0
    O = origins.reshape(-1, 3)
    depth = np.full(len(O), np.inf)
    A, B, C = loc_tris[:, 0], loc_tris[:, 1], loc_tris[:, 2]
    e1, e2 = B - A, C - A
    for k in range(len(loc_tris)):
        pv = np.cross(fwd, e2[k])
        det = float(pv @ e1[k])
        if abs(det) < 1e-12:
            continue
        tv = O - A[k]
        u_ = (tv @ pv) / det
        qv = np.cross(tv, e1[k])
        v_ = (qv @ fwd) / det
        t_ = (qv @ e2[k]) / det
        ok = (u_ >= 0) & (v_ >= 0) & (u_ + v_ <= 1) & (t_ > 0)
        depth = np.where(ok & (t_ < depth), t_, depth)
    d_wall = depth.reshape(nn, nn) - 2.0                        # 0 on the wall plane, 0.4 on the pit floor
    pit = d_wall > 0.2
    # compare with the STEP-derived mask resampled to the same grid
    step_mask, _ = label_floor_mask(hid)
    f = PPMM // ppmm
    step_small = step_mask.reshape(nn, f, nn, f).mean(axis=(1, 3)) > 0.5
    inter = (pit & step_small).sum()
    union = (pit | step_small).sum()
    iou = inter / union
    chk = reading_checks(hid, np.kron(pit, np.ones((f, f), bool)))
    note(f"06.{hid}.stl_vs_step_mask_IoU", float(iou))
    note(f"06.{hid}.stl_reading_checks", chk)
    note(f"06.{hid}.stl_pit_depth_max_mm", float(np.nanmax(np.where(np.isfinite(d_wall), d_wall, np.nan))))
    assert iou > 0.85, f"STL glyph differs from the STEP glyph (IoU {iou:.2f})"
    assert all(chk.values()), f"STL reading checks failed {chk}"
    assert abs(np.nanmax(np.where(np.isfinite(d_wall), d_wall, np.nan)) - LABEL_DEPTH) < 0.03


# =====================================================================================================================================
# 7. CABLE LINES, THREE-STATION MODE  (own mesh / line-to-triangle distance code; cross-checked against OCC BRepExtrema)
# =====================================================================================================================================


def tessellate_faces(faces, lin=0.01, ang=0.1):
    """list of (verts (n,3), tris (m,3) int) per face, in the shape's own frame."""
    out = []
    for f in faces:
        v, t = f.tessellate(lin, ang)
        out.append((np.array([(p.x, p.y, p.z) for p in v], float), np.array(t, int)))
    return out


def stack_tris(parts):
    tris = []
    for v, t in parts:
        if len(t):
            tris.append(v[t])
    return np.concatenate(tris, axis=0) if tris else np.zeros((0, 3, 3))


def subdivide(tris, max_edge):
    """split triangles at the midpoint of their longest edge until every edge <= max_edge. tris (n,3,3)."""
    tris = np.asarray(tris, float)
    while True:
        e = np.stack([np.linalg.norm(tris[:, 1] - tris[:, 0], axis=1),
                      np.linalg.norm(tris[:, 2] - tris[:, 1], axis=1),
                      np.linalg.norm(tris[:, 0] - tris[:, 2], axis=1)], axis=1)
        longest = e.argmax(axis=1)
        big = e.max(axis=1) > max_edge
        if not big.any():
            return tris
        keep = tris[~big]
        tb = tris[big]; lb = longest[big]
        # rotate so that the longest edge is (0,1)
        idx = np.arange(len(tb))
        a = np.where(lb[:, None] == 0, tb[:, 0], np.where(lb[:, None] == 1, tb[:, 1], tb[:, 2]))
        b = np.where(lb[:, None] == 0, tb[:, 1], np.where(lb[:, None] == 1, tb[:, 2], tb[:, 0]))
        c = np.where(lb[:, None] == 0, tb[:, 2], np.where(lb[:, None] == 1, tb[:, 0], tb[:, 1]))
        m = 0.5 * (a + b)
        t1 = np.stack([a, m, c], axis=1)
        t2 = np.stack([m, b, c], axis=1)
        tris = np.concatenate([keep, t1, t2], axis=0)


def _dot(a, b):
    return np.einsum('ij,ij->i', a, b)


def seg_seg_dist(p1, q1, p2, q2):
    d1 = q1 - p1; d2 = q2 - p2; r = p1 - p2
    a = _dot(d1, d1); e = _dot(d2, d2); f = _dot(d2, r); c = _dot(d1, r); b = _dot(d1, d2)
    denom = a * e - b * b
    with np.errstate(divide='ignore', invalid='ignore'):
        s = np.where(denom > 1e-12 * np.maximum(a * e, 1e-30), np.clip((b * f - c * e) / denom, 0, 1), 0.0)
        t = (b * s + f) / e
        s2 = np.where(t < 0, np.clip(-c / a, 0, 1), np.where(t > 1, np.clip((b - c) / a, 0, 1), s))
    t = np.clip(t, 0, 1)
    return np.linalg.norm((p1 + d1 * s2[:, None]) - (p2 + d2 * t[:, None]), axis=1)


def pt_seg_dist(p, a, b):
    ab = b - a
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.clip(_dot(p - a, ab) / _dot(ab, ab), 0, 1)
    return np.linalg.norm(p - (a + ab * t[:, None]), axis=1)


def pt_tri_dist(p, A, B, C):
    n = np.cross(B - A, C - A)
    nn = np.linalg.norm(n, axis=1)
    nhat = n / np.maximum(nn, 1e-30)[:, None]
    h = _dot(p - A, nhat)
    q = p - nhat * h[:, None]
    # barycentric inside test
    v0 = C - A; v1 = B - A; v2 = q - A
    d00 = _dot(v0, v0); d01 = _dot(v0, v1); d11 = _dot(v1, v1); d20 = _dot(v2, v0); d21 = _dot(v2, v1)
    den = d00 * d11 - d01 * d01
    with np.errstate(divide='ignore', invalid='ignore'):
        u = (d11 * d20 - d01 * d21) / den
        v = (d00 * d21 - d01 * d20) / den
    inside = (u >= 0) & (v >= 0) & (u + v <= 1)
    de = np.minimum(np.minimum(pt_seg_dist(p, A, B), pt_seg_dist(p, B, C)), pt_seg_dist(p, C, A))
    return np.where(inside, np.abs(h), de)


def seg_tri_intersect(P, Q, A, B, C):
    """True where segment P->Q crosses triangle ABC (Moller-Trumbore, t in [0,1])."""
    d = Q - P
    e1 = B - A; e2 = C - A
    pv = np.cross(d, e2)
    det = _dot(e1, pv)
    ok = np.abs(det) > 1e-14
    with np.errstate(divide='ignore', invalid='ignore'):
        inv = 1.0 / det
        tv = P - A
        u = _dot(tv, pv) * inv
        qv = np.cross(tv, e1)
        v = _dot(d, qv) * inv
        t = _dot(e2, qv) * inv
    return ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)


def seg_tri_dist(P, Q, A, B, C):
    """exact distance between segments P->Q and triangles ABC (all (n,3)); 0 on crossing."""
    d = np.minimum(np.minimum(seg_seg_dist(P, Q, A, B), seg_seg_dist(P, Q, B, C)), seg_seg_dist(P, Q, C, A))
    d = np.minimum(d, np.minimum(pt_tri_dist(P, A, B, C), pt_tri_dist(Q, A, B, C)))
    hit = seg_tri_intersect(P, Q, A, B, C)
    return np.where(hit, 0.0, d), hit

# ------------------------------------------------------------------ cable-line model


def clip_polygon(poly, xmin, xmax, ymin, ymax):
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia: out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out
    def ix(x0):
        return lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))
    def iy(y0):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)
    pts = list(poly)
    pts = clip(pts, lambda p: p[0] >= xmin, ix(xmin))
    pts = clip(pts, lambda p: p[0] <= xmax, ix(xmax))
    pts = clip(pts, lambda p: p[1] >= ymin, iy(ymin))
    pts = clip(pts, lambda p: p[1] <= ymax, iy(ymax))
    return pts


def point_in_tri(p, a, b, c, eps=1e-12):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    neg = (d1 < -eps) or (d2 < -eps) or (d3 < -eps)
    pos = (d1 > eps) or (d2 > eps) or (d3 > eps)
    return not (neg and pos)


def claw_positions(anchors_xy, room, margin, step):
    a, b, c = anchors_xy
    poly = clip_polygon([a, b, c], margin, room[0] - margin, margin, room[1] - margin)
    pts = [tuple(p) for p in poly]
    pts.append((sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)))
    xs = np.arange(margin, room[0] - margin + 1e-9, step)
    ys = np.arange(margin, room[1] - margin + 1e-9, step)
    for x in xs:
        for y in ys:
            if point_in_tri((x, y), a, b, c):
                pts.append((float(x), float(y)))
    return np.array(pts), poly


def make_lines(mouth_box, anchor_m, positions, zcs, yaws_deg, origin_y=7.82):
    """returns dict arrays: dir_box (n,3) unit, pos_idx, zc, yaw, elev_deg (room), length_mm."""
    bx, by, bz = mouth_box
    body = np.array([bx, -bz, by - origin_y])         # mm, body frame
    Q = np.array(anchor_m) * 1000.0
    n = len(positions) * len(zcs) * len(yaws_deg)
    P = np.repeat(positions, len(zcs) * len(yaws_deg), axis=0)
    Z = np.tile(np.repeat(zcs, len(yaws_deg)), len(positions))
    Y = np.tile(np.array(yaws_deg), len(positions) * len(zcs))
    psi = np.radians(Y)
    c, s = np.cos(psi), np.sin(psi)
    Rm = np.stack([P[:, 0] * 1000 + c * body[0] - s * body[1], P[:, 1] * 1000 + s * body[0] + c * body[1], Z * 1000 + body[2]], axis=1)
    d_room = Q[None, :] - Rm
    L = np.linalg.norm(d_room, axis=1)
    dr = d_room / L[:, None]
    # room -> body: rotate by -psi about z
    bxd = c * dr[:, 0] + s * dr[:, 1]
    byd = -s * dr[:, 0] + c * dr[:, 1]
    bzd = dr[:, 2]
    dbox = np.stack([bxd, bzd, -byd], axis=1)          # box = (body x, body z -> box y, -body y -> box z)
    elev = np.degrees(np.arcsin(dr[:, 2]))
    return dict(dir=dbox, pos=P, zc=Z, yaw=Y, elev=elev, length=L, room_mouth=Rm)


def tri_spheres(tris):
    cen = tris.mean(axis=1)
    rad = np.linalg.norm(tris - cen[:, None, :], axis=2).max(axis=1)
    return cen, rad


def _line_dist_matrix(rel, R2, D, T):
    """distance (n_points, n_lines) from points (rel = point - mouth) to segments mouth -> mouth + T*d, d = rows of D."""
    p = rel @ D.T
    d2 = np.where(p < 0, R2[:, None], np.where(p > T, R2[:, None] - 2.0 * T * p + T * T, R2[:, None] - p * p))
    return np.sqrt(np.maximum(d2, 0.0))


def min_dist_lines(tris, mouth, dirs, T=250.0, line_chunk=100, pair_chunk=400000):
    """Exact min distance (mm) segment(mouth, mouth+T*dir) -> triangles, per line; also crossing flag and argmin triangle."""
    M = np.asarray(mouth, float)
    cen, rad = tri_spheres(tris)
    relc = cen - M; R2c = np.einsum('ij,ij->i', relc, relc)
    V = np.unique(np.round(tris.reshape(-1, 3), 6), axis=0)
    relv = V - M; R2v = np.einsum('ij,ij->i', relv, relv)
    n = len(dirs)
    dmin = np.full(n, np.inf); hit = np.zeros(n, bool); arg = np.full(n, -1)
    npairs = 0
    for i0 in range(0, n, line_chunk):
        d = dirs[i0:i0 + line_chunk]
        U = _line_dist_matrix(relv, R2v, d, T).min(axis=0)                 # (c,) upper bound on the true min
        lb = _line_dist_matrix(relc, R2c, d, T) - rad[:, None]            # (nt,c) lower bound per triangle
        ti, li = np.nonzero(lb <= U[None, :] + 1e-9)
        npairs += len(ti)
        for j0 in range(0, len(ti), pair_chunk):
            tj = ti[j0:j0 + pair_chunk]; lj = li[j0:j0 + pair_chunk]
            tr = tris[tj]
            P = np.broadcast_to(M, (len(tj), 3)).copy()
            Q = M[None, :] + d[lj] * T
            dd, hh = seg_tri_dist(P, Q, tr[:, 0], tr[:, 1], tr[:, 2])
            gl = i0 + lj
            order = np.lexsort((dd, gl))
            gl_s, dd_s, tj_s, hh_s = gl[order], dd[order], tj[order], hh[order]
            first = np.r_[True, gl_s[1:] != gl_s[:-1]]
            ug = gl_s[first]; ud = dd_s[first]; ut = tj_s[first]
            better = ud < dmin[ug]
            dmin[ug[better]] = ud[better]; arg[ug[better]] = ut[better]
            if hh_s.any():
                hit[np.unique(gl_s[hh_s])] = True
    return dmin, hit, arg, npairs


def subdivide_faces(parts, max_edge):
    """parts = list of (verts, tris) per face -> (tris (n,3,3), face_id (n,))"""
    allt, ids = [], []
    for k, (v, t) in enumerate(parts):
        if len(t) == 0: continue
        s = subdivide(v[t], max_edge)
        allt.append(s); ids.append(np.full(len(s), k))
    return np.concatenate(allt), np.concatenate(ids)


CABLE_HEIGHTS_M = np.linspace(0.52, 2.20, 11)         # claw reference (body origin = tube axis at box y 7.82) heights; mouths are 34 mm higher
CABLE_YAWS_DEG = (-15.0, -10.0, -5.0, 0.0, 5.0, 10.0, 15.0)
CABLE_GRID_STEP_M = 0.15
CABLE_REACH_MM = 250.0        # beyond 250 mm along a line every point of the 170 mm-radius part is > 80 mm away: the rest cannot matter


def own_face_ids(hid, faces):
    """Faces that belong to the line's own mouth: everything within 2.5 mm of the mouth centre (wall face, bore, chamfer) and the
    debossed label of the same wall (its edges lie IN the wall plane, so the line's distance to them is just its standoff from the wall)."""
    m = plane_hit(measured_axis(hid)["loc"], measured_axis(hid)["dir"], hid, "outer")
    vtx = cq.Vertex.makeVertex(*[float(v) for v in m])
    n = vec(WALL_NORMAL[hid])
    ids = set()
    inner = plane_hit(measured_axis(hid)["loc"], measured_axis(hid)["dir"], hid, "inner")
    for i, f in enumerate(faces):
        dss = BRepExtrema_DistShapeShape(vtx.wrapped, f.wrapped)
        dss.Perform()
        dist = dss.Value()
        # the pocket-side face of the same 5 mm wall (the line starts 5 mm in front of it and moves away: not an obstacle)
        if f.geomType() == "PLANE" and f.Area() > 100.0:
            nn = f.normalAt()
            cc = f.Center()
            if abs(abs(np.dot(vec((nn.x, nn.y, nn.z)), n)) - 1.0) < 1e-6 and abs(np.dot(vec((cc.x, cc.y, cc.z)) - inner, n)) < 1e-3:
                ids.add(i)
                continue
        if dist < 2.5:
            ids.add(i)
        elif dist < 8.0:
            pts = face_points(f, 0.05)
            if len(pts) and np.abs((pts - m) @ n).max() <= LABEL_DEPTH + 0.05:
                ids.add(i)
    return ids


@lru_cache(maxsize=None)
def cable_study():
    p = part()
    faces = p.Faces()
    parts = tessellate_faces(faces)
    pf, bf, un_b, un_p = face_diff()
    # bay faces: outside the box envelope and not on Jasper's raw surface
    bay_ids = [i for i, f in enumerate(faces) if exact_bbox(f).zmin < -45.01 and classify_face(f) == "bay body"]
    cover = load_box(STEP_COVER)
    cover_faces = cover.Faces()
    cover_parts = tessellate_faces(cover_faces)
    bc_parts = [parts[i] for i in bay_ids] + cover_parts
    tris_bc, fid_bc = subdivide_faces(bc_parts, 12.0)
    pos, poly = claw_positions([ANCHORS_M[k][:2] for k in ("A", "B", "C")], ROOM_M, WALL_MARGIN_M, CABLE_GRID_STEP_M)
    study = {"n_positions": len(pos), "clipped_polygon": [tuple(map(float, q)) for q in poly], "bay_faces": len(bay_ids), "cover_faces": len(cover_faces),
             "holes": {}}
    for hid in IDS:
        ax = measured_axis(hid)
        M = plane_hit(ax["loc"], ax["dir"], hid, "outer")
        own = own_face_ids(hid, faces)
        keep = [parts[i] if i not in own else (parts[i][0], parts[i][1][:0]) for i in range(len(parts))]
        tris_h, fid_h = subdivide_faces(keep, 12.0)
        ln = make_lines(M, ANCHORS_M[hid], pos, CABLE_HEIGHTS_M, CABLE_YAWS_DEG, BODY_ORIGIN_BOX_Y)
        t0 = time.time()
        dmin, hit, arg, npairs = min_dist_lines(tris_h, M, ln["dir"], T=CABLE_REACH_MM)
        t1 = time.time()
        dbc, hbc, abc, _ = min_dist_lines(tris_bc, M, ln["dir"], T=CABLE_REACH_MM)
        study["holes"][hid] = {"mouth": M, "own_faces": sorted(own), "lines": ln, "dmin": dmin, "hit": hit, "arg": arg, "fid": fid_h,
                               "dbc": dbc, "hbc": hbc, "abc": abc, "fid_bc": fid_bc, "bay_ids": bay_ids, "seconds": (t1 - t0, time.time() - t1),
                               "d_dot_n": ln["dir"] @ vec(WALL_NORMAL[hid]), "n_tris": len(tris_h)}
    study["faces"] = faces
    study["cover_faces_list"] = cover_faces
    return study


def _room_point(pt_box, pos_xy, zc, yaw_deg):
    body = np.array([pt_box[0], -pt_box[2], pt_box[1] - BODY_ORIGIN_BOX_Y]) / 1000.0
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    return (pos_xy[0] + c * body[0] - s * body[1], pos_xy[1] + s * body[0] + c * body[1], zc + body[2])


def _line_record(study, hid, idx, which):
    h = study["holes"][hid]
    ln = h["lines"]
    d = h["dmin"][idx] if which == "all" else h["dbc"][idx]
    return {"hole": hid, "claw_xy_m": [round(float(v), 4) for v in ln["pos"][idx]], "claw_ref_height_m": round(float(ln["zc"][idx]), 4),
            "yaw_deg": float(ln["yaw"][idx]), "elevation_deg": round(float(ln["elev"][idx]), 2), "line_length_m": round(float(ln["length"][idx]) / 1000, 3),
            "mesh_distance_mm": float(d), "dir_box": [round(float(v), 5) for v in ln["dir"][idx]]}


def occ_line_distance(study, hid, idx, which):
    """Exact B-rep distance (OCC) from the line segment to the faces counted for `which` ('all' = housing + bay minus the own mouth faces,
    'bay' = bay faces + cover faces).  Returns (distance, nearest point on the solid (box frame), category of the nearest face)."""
    h = study["holes"][hid]
    M, d = h["mouth"], h["lines"]["dir"][idx]
    edge = cq.Edge.makeLine(cq.Vector(*[float(v) for v in M]), cq.Vector(*[float(v) for v in (M + d * CABLE_REACH_MM)]))
    faces = study["faces"]
    if which == "all":
        use = [f for i, f in enumerate(faces) if i not in set(h["own_faces"])]
    else:
        use = [faces[i] for i in h["bay_ids"]] + list(study["cover_faces_list"])
    best = (1e9, None, None)
    for f in use:
        dss = BRepExtrema_DistShapeShape(edge.wrapped, f.wrapped)
        dss.Perform()
        if dss.IsDone() and dss.Value() < best[0]:
            q = dss.PointOnShape2(1)
            best = (dss.Value(), vec((q.X(), q.Y(), q.Z())), f)
    return best[0], best[1], classify_face(best[2]) if best[2] is not None else None


def test_07a_distance_kernels_agree_with_brute_force():
    rng = np.random.default_rng(1)
    n = 400
    A = rng.normal(size=(n, 3)); B = A + rng.normal(size=(n, 3)); C = A + rng.normal(size=(n, 3))
    P = rng.normal(size=(n, 3)) * 2; Q = P + rng.normal(size=(n, 3)) * 3
    d, hit = seg_tri_dist(P, Q, A, B, C)
    ts = np.linspace(0, 1, 401)
    u = np.linspace(0, 1, 81)
    uv = np.array([(a, b) for a in u for b in u if a + b <= 1.0 + 1e-12])
    worst_over = -1.0
    for i in range(60):
        seg = P[i] + (Q[i] - P[i]) * ts[:, None]
        pts = A[i] + uv[:, :1] * (B[i] - A[i]) + uv[:, 1:] * (C[i] - A[i])
        brute = np.sqrt(((seg[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)).min()
        worst_over = max(worst_over, d[i] - brute)
        assert d[i] <= brute + 1e-9, f"exact distance {d[i]} exceeds a sampled distance {brute}"
        assert brute - d[i] < 0.02
    # a segment through a triangle is reported as a hit with distance 0
    d0, h0 = seg_tri_dist(np.array([[0.2, 0.2, -1.0]]), np.array([[0.2, 0.2, 1.0]]), np.array([[0.0, 0.0, 0.0]]),
                          np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 1.0, 0.0]]))
    assert h0[0] and d0[0] == 0.0
    note("07.kernel_selfcheck_max_exact_minus_brute", worst_over)


@pytest.mark.parametrize("hid", IDS)
def test_07b_lines_leave_outward_and_never_intersect_the_claw(hid):
    st = cable_study()
    h = st["holes"][hid]
    ln = h["lines"]
    dn = h["d_dot_n"]
    dmin, hit = h["dmin"], h["hit"]
    i = int(np.argmin(dmin))
    rec = _line_record(st, hid, i, "all")
    f = st["faces"][h["fid"][h["arg"][i]]]
    rec["nearest_face"] = classify_face(f)
    rec["nearest_face_type"] = f.geomType()
    rec["nearest_face_centre_box"] = [round(c, 2) for c in (f.Center().x, f.Center().y, f.Center().z)]
    rec["min_d_dot_wall_normal"] = float(dn.min())
    srt = np.sort(dmin)
    note(f"07.{hid}.n_lines", len(dmin))
    note(f"07.{hid}.elevation_range_deg", [float(ln["elev"].min()), float(ln["elev"].max())])
    note(f"07.{hid}.min_overall", rec)
    note(f"07.{hid}.count_lt_5mm_includes_interior_lid_recess_faces", int((dmin < 5.0).sum()))
    note(f"07.{hid}.count_lt_1mm", int((dmin < 1.0).sum()))
    note(f"07.{hid}.count_lt_0.5mm", int((dmin < 0.5).sum()))
    note(f"07.{hid}.count_intersecting", int(hit.sum()))
    note(f"07.{hid}.timing_s", [round(x, 1) for x in h["seconds"]])
    for lo, hi in ((0, 30), (30, 45), (45, 60), (60, 70), (70, 80), (80, 90)):
        sel = (ln["elev"] >= lo) & (ln["elev"] < hi)
        if sel.any():
            note(f"07.{hid}.min_by_elevation_{lo}_{hi}_deg", float(dmin[sel].min()))
    assert (dn > 0).all(), f"{hid}: a line runs back into its own wall (min d.n = {dn.min():.4f})"
    assert not hit.any(), f"{hid}: {int(hit.sum())} lines intersect the claw solid"
    assert dmin.min() > 0.05, f"{hid}: closest approach {dmin.min():.4f} mm"


@pytest.mark.parametrize("hid", IDS)
def test_07c_lines_clear_bay_and_cover_by_5mm(hid):
    st = cable_study()
    h = st["holes"][hid]
    dbc = h["dbc"]
    i = int(np.argmin(dbc))
    rec = _line_record(st, hid, i, "bay")
    note(f"07.{hid}.min_bay_and_cover", rec)
    note(f"07.{hid}.bay_cover_count_lt_12mm", int((dbc < 12.0).sum()))
    assert not h["hbc"].any()
    assert dbc.min() >= 5.0, f"{hid}: bay / cover distance {dbc.min():.3f} mm"


def test_07d_global_minimums_and_occ_cross_check():
    st = cable_study()
    # global minimum over everything / over bay + cover only
    best_all = min(((st["holes"][h]["dmin"].min(), h, int(np.argmin(st["holes"][h]["dmin"]))) for h in IDS))
    best_bc = min(((st["holes"][h]["dbc"].min(), h, int(np.argmin(st["holes"][h]["dbc"]))) for h in IDS))
    rec_all = _line_record(st, best_all[1], best_all[2], "all")
    rec_bc = _line_record(st, best_bc[1], best_bc[2], "bay")
    # exact B-rep distances for those two lines and for the closest line of every hole
    checks = []
    for hid in IDS:
        i = int(np.argmin(st["holes"][hid]["dmin"]))
        d_occ, pt, cat = occ_line_distance(st, hid, i, "all")
        checks.append((hid, "all", st["holes"][hid]["dmin"][i], d_occ, pt, cat, i))
        j = int(np.argmin(st["holes"][hid]["dbc"]))
        d_occ2, pt2, cat2 = occ_line_distance(st, hid, j, "bay")
        checks.append((hid, "bay", st["holes"][hid]["dbc"][j], d_occ2, pt2, cat2, j))
    for hid, which, dm, do, pt, cat, i in checks:
        note(f"07.occ.{hid}.{which}", {"mesh_mm": float(dm), "occ_mm": float(do), "nearest_point_box": [round(float(v), 3) for v in pt], "nearest_face": cat})
    # location of the global minimum in room coordinates (nearest point and mouth)
    h = best_all[1]
    i = best_all[2]
    ln = st["holes"][h]["lines"]
    d_occ, pt, cat = occ_line_distance(st, h, i, "all")
    rec_all["occ_distance_mm"] = float(d_occ)
    rec_all["nearest_point_box_mm"] = [round(float(v), 3) for v in pt]
    rec_all["nearest_point_room_m"] = [round(v, 4) for v in _room_point(pt, ln["pos"][i], ln["zc"][i], ln["yaw"][i])]
    rec_all["nearest_feature"] = cat
    d2, pt2, cat2 = occ_line_distance(st, best_bc[1], best_bc[2], "bay")
    rec_bc["occ_distance_mm"] = float(d2)
    rec_bc["nearest_point_box_mm"] = [round(float(v), 3) for v in pt2]
    rec_bc["nearest_feature"] = cat2
    note("07.GLOBAL_MIN_ALL", rec_all)
    note("07.GLOBAL_MIN_BAY_COVER", rec_bc)
    note("07.n_claw_positions", st["n_positions"])
    note("07.clipped_triangle_polygon_m", st["clipped_polygon"])
    note("07.n_lines_total", int(sum(len(st["holes"][k]["dmin"]) for k in IDS)))
    for hid, which, dm, do, pt, cat, i in checks:
        assert abs(dm - do) < 0.03, f"{hid} {which}: mesh {dm:.4f} mm vs OCC {do:.4f} mm"
    assert rec_all["mesh_distance_mm"] > 0.0 and d_occ > 0.0
    # random lines (not only the extremes): mesh distance vs exact B-rep distance
    rng = np.random.default_rng(11)
    diffs = []
    for hid in IDS:
        dm = st["holes"][hid]["dmin"]
        cand = np.nonzero(dm < 40.0)[0]
        for i in rng.choice(cand, 8, replace=False):
            d_occ_r, _, _ = occ_line_distance(st, hid, int(i), "all")
            diffs.append((hid, int(i), float(dm[i]), float(d_occ_r)))
    worst = max(abs(a - b) for _, _, a, b in diffs)
    note("07.random_line_mesh_vs_occ", {"n": len(diffs), "max_abs_diff_mm": worst, "distance_range_mm": [min(d[2] for d in diffs), max(d[2] for d in diffs)]})
    assert worst < 0.03, f"mesh vs OCC distance differ by up to {worst:.4f} mm on random lines"
    assert rec_bc["mesh_distance_mm"] >= 5.0


# =====================================================================================================================================
# 8. STEP ROUND TRIP, STL
# =====================================================================================================================================
def test_08a_step_reimport_roundtrip(tmp_path):
    shp = cq.importers.importStep(STEP_34).val()
    out = str(tmp_path / "roundtrip_34.step")
    cq.exporters.export(cq.Workplane("XY").add(shp), out)
    re1 = cq.importers.importStep(out).val()
    out2 = str(tmp_path / "roundtrip_34_b.step")
    cq.exporters.export(cq.Workplane("XY").add(re1), out2)
    re2 = cq.importers.importStep(out2).val()
    d1 = max(abs(a - b) for a, b in zip(bbox_tuple(shp), bbox_tuple(re1)))
    d2 = max(abs(a - b) for a, b in zip(bbox_tuple(re1), bbox_tuple(re2)))
    rv1 = abs(re1.Volume() - shp.Volume()) / shp.Volume()
    rv2 = abs(re2.Volume() - re1.Volume()) / re1.Volume()
    note("08.step_roundtrip", {"solids": len(re1.Solids()), "valid": bool(re1.isValid()), "volume_shipped": shp.Volume(), "volume_reimport": re1.Volume(),
                               "volume_rel_diff": rv1, "bbox_max_diff_mm": d1, "second_pass_volume_rel_diff": rv2, "second_pass_bbox_diff_mm": d2,
                               "faces_shipped": len(shp.Faces()), "faces_reimport": len(re1.Faces())})
    assert len(re1.Solids()) == 1 and re1.isValid() and brep_valid(re1)
    assert rv1 < 1e-6 and d1 < 1e-4
    assert rv2 < 1e-6 and d2 < 1e-4
    assert len(re1.Faces()) == len(shp.Faces())


def test_08b_shipped_step_matches_the_source_script():
    from cad.parts import gripper1021_housing_cambay as G
    housing, _cover = G.make_34()
    src = G.to_world(housing.val())
    shp = cq.importers.importStep(STEP_34).val()
    rv = abs(src.Volume() - shp.Volume()) / shp.Volume()
    d = max(abs(a - b) for a, b in zip(bbox_tuple(src), bbox_tuple(shp)))
    note("08.source_vs_shipped_step", {"volume_source": src.Volume(), "volume_shipped": shp.Volume(), "rel_diff": rv, "bbox_max_diff_mm": d,
                                       "solids": len(src.Solids()), "valid": bool(src.isValid())})
    assert len(src.Solids()) == 1 and src.isValid()
    assert rv < 1e-4, f"shipped STEP and make_34() differ in volume by {100 * rv:.4f} %"
    assert d < 1e-3


def stl_edges_and_volume(tris):
    """Merge vertices at 1e-4 mm, drop triangles that collapse (degenerate micro-triangles from the tessellation of sliver faces),
    then count edges that are not shared by exactly one triangle in each direction.  Returns (bad edges, signed volume, vertices,
    collapsed triangles, largest collapsed area)."""
    area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    v = np.round(tris.reshape(-1, 3), 4)
    keys, inv = np.unique(v, axis=0, return_inverse=True)
    idx = inv.reshape(-1, 3)
    ok = np.array([len(set(t)) == 3 for t in idx])
    collapsed = int((~ok).sum())
    max_collapsed_area = float(area[~ok].max()) if collapsed else 0.0
    idx = idx[ok]
    e = np.concatenate([idx[:, [0, 1]], idx[:, [1, 2]], idx[:, [2, 0]]], axis=0)
    directed = {}
    for a, b in e:
        directed[(a, b)] = directed.get((a, b), 0) + 1
    bad = 0
    for (a, b), c in directed.items():
        if c != 1 or directed.get((b, a), 0) != 1:
            bad += 1
    vol = float(np.einsum("ij,ij->", tris[ok][:, 0], np.cross(tris[ok][:, 1], tris[ok][:, 2])) / 6.0)
    return bad, vol, len(keys), collapsed, max_collapsed_area


def test_08c_stl_print_orientation_volume_and_watertight():
    tris, nrm = read_stl(STL_34)
    bad, vol, nv, collapsed, collapsed_area = stl_edges_and_volume(tris)
    bad_b, _, _, collapsed_b, _ = stl_edges_and_volume(read_stl(STL_BASE)[0])
    shp = part()
    vstep = shp.Volume()
    bb = tris.reshape(-1, 3)
    mn, mx = bb.min(axis=0), bb.max(axis=0)
    # print frame = box frame rotated +90 deg about X:  (x, y, z) -> (x, -z, y)
    bs = bbox_tuple(shp)
    exp_min = np.array([bs[0], -bs[5], bs[2]])
    exp_max = np.array([bs[1], -bs[4], bs[3]])
    # bottom face on the bed: triangles lying on z = 0 and facing down (computed normals; micro slivers have noisy normals but no area)
    z0 = np.isclose(tris[:, :, 2], 0.0, atol=1e-3).all(axis=1)
    cr = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ar = 0.5 * np.linalg.norm(cr, axis=1)
    nzc = cr[:, 2] / np.maximum(2 * ar, 1e-30)
    bottom_area = float(ar[z0].sum())
    down_area = float(ar[z0 & (nzc < -0.99)].sum())
    up_area = float(ar[z0 & (nzc > 0.99)].sum())
    facing_down = down_area >= 0.999 * bottom_area and up_area == 0.0
    rv = abs(vol - vstep) / vstep
    # the existing (baseline) STL carries the same tessellation offset: the NEW features must add only their own volume change
    tb_, _ = read_stl(STL_BASE)
    _bb, vol_b, _nv, _c, _ca = stl_edges_and_volume(tb_)
    d_stl = vol - vol_b
    d_step = vstep - base().Volume()
    note("08.stl_volume_change_vs_baseline", {"stl_34_minus_stl_base_mm3": d_stl, "step_34_minus_step_base_mm3": d_step,
                                              "baseline_stl_rel_offset_to_step": (vol_b - base().Volume()) / base().Volume()})
    note("08.stl", {"triangles": len(tris), "unique_vertices": nv, "non_manifold_or_open_edges": bad, "collapsed_micro_triangles": collapsed,
                    "largest_collapsed_triangle_area_mm2": collapsed_area, "baseline_stl_collapsed_micro_triangles": collapsed_b,
                    "baseline_stl_open_edges": bad_b, "signed_volume_mm3": vol, "step_volume_mm3": vstep,
                    "volume_rel_diff": rv, "bbox_min": [round(float(v), 4) for v in mn], "bbox_max": [round(float(v), 4) for v in mx],
                    "expected_bbox_min": [round(float(v), 4) for v in exp_min], "expected_bbox_max": [round(float(v), 4) for v in exp_max],
                    "bottom_face_area_on_bed_mm2": bottom_area, "bottom_triangles_face_down": bool(facing_down)})
    assert bad == 0, f"{bad} open / non-manifold / inconsistently oriented edges in the STL"
    assert collapsed_area < 1e-3, "a collapsed triangle is large enough to matter"
    assert vol > 0
    assert rv < 0.0025, f"STL volume {vol:.1f} vs STEP {vstep:.1f} ({100 * rv:.3f} %)"
    assert abs(d_stl - d_step) < 1.0, f"STL volume change {d_stl:.2f} mm3 vs STEP volume change {d_step:.2f} mm3"
    assert np.abs(mn - exp_min).max() < 0.02 and np.abs(mx - exp_max).max() < 0.02, "STL bounding box is not the STEP box rotated to print orientation"
    assert abs(mn[2]) < 1e-3, "STL does not sit on z = 0"
    assert bottom_area > 8000.0 and facing_down, "the box bottom is not one flat face on the bed"


def test_08d_stl_vertices_lie_on_the_step_surface():
    tris, _ = read_stl(STL_34)
    verts = np.unique(np.round(tris.reshape(-1, 3), 5), axis=0)
    rng = np.random.default_rng(5)
    sel = verts[rng.choice(len(verts), 200, replace=False)]
    box = np.stack([sel[:, 0], sel[:, 2], -sel[:, 1]], axis=1)          # inverse of (x, y, z) -> (x, -z, y)
    shell = part().Shells()[0]
    worst = 0.0
    for p in box:
        dss = BRepExtrema_DistShapeShape(cq.Vertex.makeVertex(*[float(v) for v in p]).wrapped, shell.wrapped)
        dss.Perform()
        worst = max(worst, dss.Value())
    note("08.stl_vertex_to_step_surface_max_mm", worst)
    assert worst < 0.01, f"STL vertex {worst:.4f} mm off the STEP surface"


@pytest.mark.parametrize("hid", IDS)
def test_08e_stl_has_the_through_holes_and_the_baseline_stl_does_not(hid):
    def hits(tris, p0, p1):
        d = p1 - p0
        A, B, C = tris[:, 0], tris[:, 1], tris[:, 2]
        e1, e2 = B - A, C - A
        pv = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, pv)
        ok = np.abs(det) > 1e-12
        tv = p0 - A
        u = np.einsum("ij,ij->i", tv, pv) / np.where(ok, det, 1.0)
        qv = np.cross(tv, e1)
        v = (qv @ d) / np.where(ok, det, 1.0)
        t = np.einsum("ij,ij->i", e2, qv) / np.where(ok, det, 1.0)
        return int((ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)).sum())

    t34, _ = read_stl(STL_34)
    tb, _ = read_stl(STL_BASE)
    loc, a, e1, e2 = _frame(hid)
    L = WALL_LEN[hid]
    n34, nbase = [], []
    for du, dv in ((0.0, 0.0), (0.7, 0.0), (-0.7, 0.0), (0.0, -0.7)):
        p0 = box_to_print(_axis_point(hid, -4.0) + e1 * du + e2 * dv)
        p1 = box_to_print(_axis_point(hid, L + 4.0) + e1 * du + e2 * dv)
        n34.append(hits(t34, p0, p1))                       # the STL is already in print orientation
        nbase.append(hits(tb, p0, p1))
    note(f"08.{hid}.stl_ray_crossings_through_wall_part_vs_baseline", [n34, nbase])
    assert all(n == 0 for n in n34), f"the STL wall is closed along the hole axis (crossings {n34})"
    assert all(n >= 2 for n in nbase), f"the baseline STL has no wall on these lines ({nbase}): the probe is meaningless"


# =====================================================================================================================================
# 9. PRINTABILITY
# =====================================================================================================================================
def overhang_triangles(path, limit_deg=47.0):
    tris, nrm = read_stl(path)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    nz = n[:, 2] / np.maximum(2 * area, 1e-30)
    thr = -math.sin(math.radians(limit_deg))
    sel = nz < thr
    cen = tris.mean(axis=1)
    return cen[sel], area[sel], nz[sel]


def test_09_no_new_unsupported_overhang_beyond_the_teardrop_tips_and_label_ceilings():
    c34, a34, _ = overhang_triangles(STL_34)
    cb, ab, _ = overhang_triangles(STL_BASE)
    # to box frame for the zone tests: (x, -z, y) inverse -> (x, z_print, -y_print)
    def to_box_frame(p):
        return np.stack([p[:, 0], p[:, 2], -p[:, 1]], axis=1)
    b34, bb_ = to_box_frame(c34), to_box_frame(cb)
    def in_hole_body(p):
        d = np.full(len(p), np.inf)
        for hid in IDS:
            d = np.minimum(d, seg_dist_points(p, vec(INNER[hid]), vec(OUTER[hid])))
        return d <= 3.0
    def in_label(p):
        d = np.full(len(p), np.inf)
        for hid in IDS:
            d = np.minimum(d, label_box_dist(p, hid))
        return d <= 1.0
    hole34, lab34 = in_hole_body(b34), in_label(b34)
    holeb, labb = in_hole_body(bb_), in_label(bb_)
    outside34 = ~(hole34 | lab34)
    outsideb = ~(holeb | labb)
    a_out34, a_outb = a34[outside34].sum(), ab[outsideb].sum()
    a_hole34, a_lab34 = a34[hole34].sum(), a34[lab34 & ~hole34].sum()
    # label pits: every steep overhang triangle there must lie within the pit (<= 0.4 mm below the wall plane): an unsupported span of one
    # extrusion width, i.e. the tops of the debossed strokes
    depth_max = 0.0
    for hid in IDS:
        sel = label_box_dist(b34, hid) <= 1.0
        if sel.any():
            dpt = (b34[sel] - vec(OUTER[hid])) @ vec(WALL_NORMAL[hid])
            depth_max = max(depth_max, float(-dpt.min()))
            assert dpt.max() < 0.02, f"label {hid}: an overhang triangle outside the wall plane"
    note("09.overhang_area_steeper_than_47deg_mm2", {"baseline_total": float(ab.sum()), "part_total": float(a34.sum()), "part_outside_zones": float(a_out34),
                                                      "baseline_outside_zones": float(a_outb), "part_in_hole_bodies": float(a_hole34),
                                                      "part_in_label_pits": float(a_lab34), "baseline_in_zones": float(ab[~outsideb].sum()),
                                                      "label_pit_overhang_max_depth_mm": depth_max})
    assert abs(a_out34 - a_outb) < 0.5, f"overhang area changed outside the hole / label zones: {a_out34:.2f} vs {a_outb:.2f} mm2"
    assert a_hole34 < 1e-3, f"{a_hole34:.4f} mm2 of >47 degree overhang inside the hole bodies"
    assert depth_max <= LABEL_DEPTH + 0.03, f"label overhangs reach {depth_max:.3f} mm into the wall"


def test_09b_teardrop_flanks_are_45_degrees_in_print_orientation():
    """Every hole-body face that faces downward in print orientation is at most 45 degrees off vertical (+0.1 deg)."""
    worst, worst_sliver, n_sliver = 0.0, 0.0, 0
    for hid in IDS:
        for f in hole_new_faces(hid):
            sliver = f.Area() < 1e-3                     # zero-area faces left at the mouths by the chamfer operation
            n_sliver += int(sliver)
            v, t = f.tessellate(0.01, 0.1)
            vv = np.array([(q.x, q.y, q.z) for q in v], float)
            for tri in np.array(t, int):
                p3 = vv[tri]
                n = np.cross(p3[1] - p3[0], p3[2] - p3[0])
                ln = np.linalg.norm(n)
                if ln < 1e-12:
                    continue
                n = n / ln
                fn = f.normalAt(cq.Vector(*p3.mean(axis=0)))                       # orient n out of the SOLID using the B-rep face normal
                if np.dot(n, vec((fn.x, fn.y, fn.z))) < 0:
                    n = -n
                if n[1] < 0:                                                       # box +y is print "up": downward-facing => overhang
                    ang = math.degrees(math.asin(min(1.0, -n[1])))
                    if sliver:
                        worst_sliver = max(worst_sliver, ang)
                    else:
                        worst = max(worst, ang)
    note("09.max_overhang_angle_in_hole_bodies_deg", worst)
    note("09.sliver_faces_area_lt_1e-3_mm2", {"count": n_sliver, "max_overhang_angle_deg": worst_sliver})
    assert worst <= 45.1, f"a hole face overhangs by {worst:.2f} deg"


# =====================================================================================================================================
# 10. BASELINE UNTOUCHED
# =====================================================================================================================================
def test_10a_baseline_regenerates_identically_from_make():
    from cad.parts import gripper1021_housing_cambay as G
    housing, cover = G.make()
    h = G.to_world(housing.val())
    c = G.to_world(cover.val())
    h_ref = cq.importers.importStep(STEP_BASE).val()
    c_ref = cq.importers.importStep(STEP_COVER).val()
    rows = {}
    for name, a, b in (("housing", h, h_ref), ("cover", c, c_ref)):
        rows[name] = {"volume_regenerated": a.Volume(), "volume_export": b.Volume(), "rel_diff": abs(a.Volume() - b.Volume()) / b.Volume(),
                      "bbox_max_diff_mm": max(abs(x - y) for x, y in zip(bbox_tuple(a), bbox_tuple(b))), "solids": len(a.Solids()), "valid": bool(a.isValid())}
    note("10.baseline_regeneration", rows)
    for name, r in rows.items():
        assert r["solids"] == 1 and r["valid"]
        assert r["rel_diff"] < 1e-6, f"{name}: volume {r['volume_regenerated']} vs export {r['volume_export']}"
        assert r["bbox_max_diff_mm"] < 1e-3


def test_10b_baseline_export_files_are_unmodified_in_git():
    import shutil
    import subprocess
    if shutil.which("git") is None:
        pytest.skip("git not available")
    files = ["exports/step/gripper1021_housing_cambay.step", "exports/step/gripper1021_housing_cambay_cover.step",
             "exports/stl/gripper1021_housing_cambay.stl", "exports/stl/gripper1021_housing_cambay_cover.stl"]
    res = {}
    for f in files:
        wt = subprocess.run(["git", "-C", REPO, "hash-object", f], capture_output=True, text=True).stdout.strip()
        head = subprocess.run(["git", "-C", REPO, "rev-parse", f"HEAD:{f}"], capture_output=True, text=True)
        if head.returncode != 0:
            pytest.skip(f"{f} is not tracked in HEAD")
        res[f] = (wt == head.stdout.strip())
    note("10.baseline_files_equal_to_HEAD", res)
    assert all(res.values()), res


@pytest.mark.skipif(os.environ.get("HOUSING34_RUN_BASELINE_SUITE") != "1", reason="set HOUSING34_RUN_BASELINE_SUITE=1 to run tests/test_gripper1021.py (about 2 min)")
def test_10c_existing_gripper1021_suite_still_passes():
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", os.path.join(REPO, "tests", "test_gripper1021.py")],
                       capture_output=True, text=True, cwd=REPO)
    note("10.tests_gripper1021_summary", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])
    assert r.returncode == 0, r.stdout[-2000:]


# =====================================================================================================================================
# 11. BODY-FRAME POINTS FOR THE SOFTWARE
# =====================================================================================================================================
def box_to_body_m(p):
    return (float(p[0]) / 1000.0, float(-p[2]) / 1000.0, float(p[1] - BODY_ORIGIN_BOX_Y) / 1000.0)


@pytest.mark.parametrize("hid", IDS)
def test_11a_outer_mouth_points_in_the_body_frame(hid):
    ax = measured_axis(hid)
    m = plane_hit(ax["loc"], ax["dir"], hid, "outer")
    body = box_to_body_m(m)
    exp = BODY_POINTS_M[hid]
    err = max(abs(a - b) for a, b in zip(body, exp))
    note(f"11.{hid}.outer_mouth_body_m", [round(v, 5) for v in body])
    note(f"11.{hid}.expected_body_m", list(exp))
    note(f"11.{hid}.max_error_m", err)
    assert err <= 6e-5, f"{hid}: body-frame point {body} vs {exp}"      # the notes round to 0.1 mm (half unit 5e-5 m)


def test_11b_frame_origin_is_on_the_tube_axis_at_box_y_7p82():
    # tube axis: the Ø30 cylinder of the baseline
    axes = []
    for f in base().Faces():
        if f.geomType() == "CYLINDER":
            r, loc, d = cylinder_params(f)
            if abs(r - 15.0) < 0.01:
                axes.append((loc, d))
    assert axes
    off = max(math.hypot(*(loc[[0, 2]] - d[[0, 2]] / d[1] * loc[1])) for loc, d in axes)
    # corner holes (Ø2, rising 13.8 deg): inner mouth = where the axis leaves the pocket corner (R10 about (+-30, +-30)); its height is the
    # body-frame origin height.  (The outer mouth sits in the R75 blend where no simple surface model applies: not needed by the spec table.)
    inner_y, rows = [], []
    for f in base().Faces():
        if f.geomType() != "CYLINDER":
            continue
        r, loc, d = cylinder_params(f)
        if abs(r - 1.0) > 0.02 or exact_bbox(f).ymax > 30.0:
            continue
        if d[1] < 0:
            d = -d                                                       # point up and outward along the rise
        sx, sz = math.copysign(1.0, loc[0] + d[0] * 40), math.copysign(1.0, loc[2] + d[2] * 40)
        ts = np.linspace(-80.0, 80.0, 160001)
        P = loc[None, :] + ts[:, None] * d[None, :]
        g = np.hypot(P[:, 0] - sx * 30.0, P[:, 2] - sz * 30.0) - 10.0
        k = np.nonzero(np.sign(g[:-1]) != np.sign(g[1:]))[0]
        cand = [P[i] for i in k if abs(P[i][0]) > 30.0 and abs(P[i][2]) > 30.0]
        assert cand, "axis does not meet the pocket corner fillet"
        qi = cand[0]
        rows.append({"corner_signs_xz": (sx, sz), "elevation_deg": round(math.degrees(math.asin(abs(d[1]))), 3),
                     "inner_box": [round(float(v), 4) for v in qi], "inner_body_m": [round(v, 5) for v in box_to_body_m(qi)]})
        inner_y.append(qi[1])
    note("11.tube_axis_offset_from_box_origin_mm", float(off))
    note("11.corner_hole_inner_mouth_heights_box_y", [round(float(v), 4) for v in inner_y])
    note("11.corner_holes_body_frame", rows)
    assert off < 0.01, f"tube axis is {off} mm from the box-frame y axis"
    assert len(inner_y) == 4, f"found {len(inner_y)} corner holes"
    assert max(abs(v - BODY_ORIGIN_BOX_Y) for v in inner_y) < 0.02, f"inner-mouth heights {inner_y}"
    for rw in rows:
        assert abs(abs(rw["inner_body_m"][0]) - 0.03707) < 1e-4 and abs(abs(rw["inner_body_m"][1]) - 0.03707) < 1e-4 and abs(rw["inner_body_m"][2]) < 3e-5
    # frame handedness: the camera bay is at box -z, i.e. body +y
    assert bbox_tuple(base())[4] < -100.0 and bbox_tuple(base())[5] < 51.0


# =====================================================================================================================================
# 12. PARAMETER AND DELIVERABLE AGREEMENT
# =====================================================================================================================================
def test_12a_params_agree_with_the_measured_geometry():
    """cad/params.py CAMBAY1021_TRI_* (read only) against what was measured on the STEP, and the interfaces file has no conflicting entry."""
    from cad import params as P
    assert tuple(P.CAMBAY1021_TRI_IDS) == IDS
    assert tuple(P.CAMBAY1021_TRI_AZ_BODY_DEG) == (90.0, 210.0, 330.0)
    assert P.CAMBAY1021_TRI_Y == 42.0 and P.CAMBAY1021_TRI_HOLE_D == 2.0 and P.CAMBAY1021_TRI_CHAMFER == 0.5
    assert P.CAMBAY1021_TRI_LABEL_H == 4.0 and P.CAMBAY1021_TRI_LABEL_DEPTH == 0.4 and P.CAMBAY1021_TRI_LABEL_ABOVE == 5.0
    assert tuple(P.CAMBAY1021_BAY_ORIGIN_WORLD) == ORIGIN
    for k, hid in enumerate(IDS):
        assert tuple(P.CAMBAY1021_TRI_ANCHORS_ROOM_M[k]) == ANCHORS_M[hid], f"anchor prior of {hid} differs from the task value"
    assert abs(P.CAMBAY1021_TRI_BODY_ORIGIN_Y - BODY_ORIGIN_BOX_Y) < 1e-9
    # measured axis heights equal the parameter
    for hid in IDS:
        assert abs(measured_axis(hid)["loc"][1] - P.CAMBAY1021_TRI_Y) < 5e-3
    src = open(os.path.join(REPO, "cad", "interfaces.py"), errors="ignore").read()
    note("12.interfaces_py_mentions_1021_or_tri", bool(("1021" in src) or ("CAMBAY1021" in src) or ("TRI_" in src)))


def test_12b_standard_renders_exist():
    from PIL import Image
    names = [f"gripper1021_housing_cambay_34_{v}.png" for v in ("iso", "front", "rear", "left", "right", "top", "bottom", "closeup_C", "closeup_A", "closeup_B")]
    sizes = {}
    for n in names:
        path = os.path.join(REPO, "renders", "gripper1021", n)
        assert os.path.exists(path), f"missing render {n}"
        with Image.open(path) as im:
            sizes[n] = im.size
            assert im.size[0] >= 400 and im.size[1] >= 400
    note("12.renders_found", sizes)


# =====================================================================================================================================
# results dump (for the report): set HOUSING34_VERIFY_JSON=/path/out.json
# =====================================================================================================================================
def test_99_dump_results():
    path = os.environ.get("HOUSING34_VERIFY_JSON")
    if not path:
        pytest.skip("set HOUSING34_VERIFY_JSON to write the measurements")
    import json

    def default(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    with open(path, "w") as fh:
        json.dump(RESULTS, fh, indent=1, default=default, sort_keys=True)
