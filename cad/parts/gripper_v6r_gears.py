"""
Gripper v6r -- Jasper's own v6 gears, modified for the 2:1 gearbox.  NOT new gears: every solid below is his
v6 solid (solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP, read-only, via cad/v6_loader.py) with
exactly these changes and nothing else:

  pinion  Simple_18T_Pinionvlast   unchanged (only re-homed to its own axis).
  compound 06_compound_54T_24T     54T ring (Z 0..16) -> 36T ring of the SAME tooth form; his hub, pocket, lips
                                   and web kept inside R = GRIPV6R_CORE_R; lightening holes re-laid for the
                                   smaller ring (same style: round holes in the web); 24T layer untouched;
                                   lug / fork shortened from R75 to R53 (same cross-section, boss, fork) and
                                   re-phased to the v7 closed-pose crank angle.
  follower 24T_Follower            lug R75 -> R53, re-phased.  Nothing else.
  FUNCTIONAL FIX (flagged, only change beyond tooth count / crank length): a 0.30 mm annular relief on the top
  face of the 36T layer (his follower bottom sits ON the big-gear top face and the parts counter-rotate).
  make_compound(relief=False) is the _norelief variant.

Tooth form.  The 36T ring is produced by the v3/v6 involute generator (cad/gripper_v3_fit_review_20261018/
gears.py) with the parameters measured on his 54T (20 deg, addendum 1.0 m, dedendum 1.25 m, R0.4 root blend,
0.10 mm thinning at the pitch circle).  The generator reproduces his 54T section to 1e-5 mm
(verification/gripper_v6r_gears_numbers.json, "tooth_form").

Frames.  PART frame: gear axis = z axis through the origin, z = 0 at the bottom of his gear stack
(his world z GRIPV6R_SRC_Z0).  Compound and follower are exported in the v7 CLOSED-POSE orientation
(lug angle GRIPV6R_ARM_DEG_C / _F, CCW from +x, same convention as cad/parts/gripper_v7_kin.py); the pinion keeps
his orientation.  Placement: translate to GRIPV6R_C_XY / F_XY / S_XY (the v7 local frame = his world - origin).
Rotation with the crank: compound +d, follower -d, pinion -2 d (d = crank angle - closed angle).

Mesh phasing is built into the 36T ring (its tooth phase is solved numerically so that the pinion, in his
orientation, sits in the middle of the clearance window at the closed pose); the 24T pair has no free phase
and falls at the window centre because the two lugs are exact mirror images (see mesh_report()).
"""

from __future__ import annotations

import math
import os
from functools import lru_cache

import numpy as np
import cadquery as cq
from matplotlib.path import Path as MplPath
from scipy.optimize import brentq
from scipy.spatial import cKDTree

from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

from cad import params as P
from cad.gripper_v3_fit_review_20261018.gears import gear as _involute_gear
from cad.v6_loader import find, load_v6

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M = P.GRIPV6R_MODULE
Z_PIN, Z_MAIN, Z_SYNC = P.GRIPV6R_Z_PINION, P.GRIPV6R_Z_MAIN, P.GRIPV6R_Z_SYNC


def pitch_r(n: int) -> float:
    return M * n / 2.0


def tip_r(n: int) -> float:
    return M * n / 2.0 + P.GRIPV6R_ADDENDUM_K * M


def root_r(n: int) -> float:
    return M * n / 2.0 - P.GRIPV6R_DEDENDUM_K * M


# =============================================================================================================
# his solids
# =============================================================================================================
@lru_cache(maxsize=1)
def _v6_parts():
    return load_v6()


def _cyl_axis(shape: cq.Shape, radius: float, tol: float = 1e-3):
    """(x, y) of the first cylindrical face of the given radius (his gear axes are read from his tooth tip / root
    cylinders, never typed in)."""
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - radius) < tol:
            loc = a.Cylinder().Axis().Location()
            return loc.X(), loc.Y()
    raise RuntimeError("no cylinder of radius %.3f" % radius)


def src_solid(name: str) -> cq.Shape:
    """His solid in his world frame (fresh copy of the loaded shape)."""
    return find(_v6_parts(), name)


def _home(shape: cq.Shape, axis_xy, expect_xy) -> cq.Shape:
    """Re-home to the part frame (axis on z, stack bottom at z = 0).  Asserts his axis against params."""
    if math.hypot(axis_xy[0] - expect_xy[0], axis_xy[1] - expect_xy[1]) > P.GRIPV6R_SRC_TOL:
        raise AssertionError("source axis %s differs from params %s" % (axis_xy, expect_xy))
    return shape.moved(cq.Location(cq.Vector(-axis_xy[0], -axis_xy[1], -P.GRIPV6R_SRC_Z0)))


def home_pinion() -> cq.Shape:
    s = src_solid(P.GRIPV6R_SRC_PINION)
    return _home(s, _cyl_axis(s, tip_r(Z_PIN)), P.GRIPV6R_SRC_S_XY)


def home_compound() -> cq.Shape:
    s = src_solid(P.GRIPV6R_SRC_COMPOUND)
    return _home(s, _cyl_axis(s, tip_r(Z_SYNC)), P.GRIPV6R_SRC_C_XY)


def home_follower() -> cq.Shape:
    s = src_solid(P.GRIPV6R_SRC_FOLLOWER)
    return _home(s, _cyl_axis(s, tip_r(Z_SYNC)), P.GRIPV6R_SRC_F_XY)


# =============================================================================================================
# helpers
# =============================================================================================================
def _wp(shape) -> cq.Workplane:
    return shape if isinstance(shape, cq.Workplane) else cq.Workplane(obj=shape)


def _shp(x) -> cq.Shape:
    return x.val() if isinstance(x, cq.Workplane) else x


def _cyl(r: float, z0: float, z1: float, x: float = 0.0, y: float = 0.0) -> cq.Solid:
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0))


def _box(x0, x1, y0, y1, z0, z1) -> cq.Solid:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def rotate_z(shape: cq.Shape, deg: float, about=(0.0, 0.0)) -> cq.Shape:
    return shape.rotate(cq.Vector(about[0], about[1], 0), cq.Vector(about[0], about[1], 1), deg)


def _single_solid(shape: cq.Shape, what: str) -> cq.Solid:
    BRepTools.Clean_s(shape.wrapped)      # drop stale triangulations inherited from his faces (they corrupt bounding boxes / STL)
    solids = shape.Solids()
    if len(solids) != 1 or not shape.isValid():
        raise RuntimeError("%s: %d solids, valid=%s" % (what, len(solids), shape.isValid()))
    return solids[0]


def involute_ring(n: int, width: float, phase_deg: float) -> cq.Solid:
    """Full gear blank (no bore) with his tooth form; tooth k centred at phase + 360 k / n."""
    g = _involute_gear(n, M, width, phase=phase_deg, reduction=P.GRIPV6R_TOOTH_THIN,
                       root_radius=P.GRIPV6R_ROOT_FILLET_R)
    return g.val()


# =============================================================================================================
# 2D outlines (for the mesh analysis) and measurements on the real solids
# =============================================================================================================
def _chain(edges_pts):
    """Chain unordered edge polylines into closed loops (end-point matching with a KD tree)."""
    tol = 2e-4
    ends = np.vstack([np.vstack([p[0], p[-1]]) for p in edges_pts])        # row 2 i = start, 2 i + 1 = end of edge i
    tree = cKDTree(ends)
    used = np.zeros(len(edges_pts), bool)
    loops = []
    for i0 in range(len(edges_pts)):
        if used[i0]:
            continue
        used[i0] = True
        loop = [edges_pts[i0]]
        start, end = edges_pts[i0][0], edges_pts[i0][-1]
        while np.hypot(*(end - start)) > tol:
            nxt = None
            for j in tree.query_ball_point(end, tol):
                if not used[j // 2]:
                    nxt = j
                    break
            if nxt is None:
                break
            used[nxt // 2] = True
            e = edges_pts[nxt // 2]
            e = e if nxt % 2 == 0 else e[::-1]
            loop.append(e)
            end = e[-1]
        loops.append(np.vstack(loop))
    return loops


def outlines(shape: cq.Shape, z: float, step: float = 0.02):
    """Closed section loops of the solid at height z (part frame), each densified to `step`."""
    pl = cq.Face.makePlane(600, 600, basePnt=(0, 0, z), dir=(0, 0, 1))
    sec = BRepAlgoAPI_Section(shape.wrapped, pl.wrapped)
    sec.Build()
    polys = []
    for e in cq.Shape.cast(sec.Shape()).Edges():
        n = max(2, int(math.ceil(e.Length() / step)) + 1)
        c = BRepAdaptor_Curve(e.wrapped)
        a, b = c.FirstParameter(), c.LastParameter()
        pts = [c.Value(a + (b - a) * u) for u in np.linspace(0.0, 1.0, n)]
        polys.append(np.array([[p.X(), p.Y()] for p in pts]))
    return _chain(polys)


def _area(poly) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def outer_outline(shape: cq.Shape, z: float, step: float = 0.02) -> np.ndarray:
    loops = outlines(shape, z, step)
    return max(loops, key=lambda p: abs(_area(p)))


def _rot2(poly: np.ndarray, deg: float, about=(0.0, 0.0)) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    q = poly - np.array(about)
    return np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c], axis=1) + np.array(about)


class Outline:
    """Closed polygon with fast signed-distance queries (KD tree and containment path are built on first use)."""

    def __init__(self, pts: np.ndarray):
        self.pts = pts
        self._tree = None
        self._path = None

    @property
    def tree(self):
        if self._tree is None:
            self._tree = cKDTree(self.pts)
        return self._tree

    @property
    def path(self):
        if self._path is None:
            self._path = MplPath(self.pts)
        return self._path

    def placed(self, deg: float, xy) -> "Outline":
        return Outline(_rot2(self.pts, deg) + np.array(xy))


NEAR_MM = 1.0       # only vertices this close to the other outline can be (or become) the first to penetrate it


def signed_gap(A: Outline, B: Outline) -> float:
    """> 0: minimum distance between the two outlines (no overlap).  < 0: -(maximum penetration depth).
    Vertices are sampled every 0.02 mm; a crossing always leaves vertices of one outline inside the other within
    NEAR_MM of its boundary, so only those are containment-tested."""
    dA = B.tree.query(A.pts)[0]
    dB = A.tree.query(B.pts)[0]
    depth = 0.0
    for pts, d, other in ((A.pts, dA, B), (B.pts, dB, A)):
        near = np.where(d < NEAR_MM)[0]
        if near.size:
            ins = other.path.contains_points(pts[near])
            if ins.any():
                depth = max(depth, float(d[near[ins]].max()))
    if depth > 0.0:
        return -max(depth, 1e-9)
    return float(min(dA.min(), dB.min()))


def tooth_phase_deg(pts: np.ndarray, n: int, r_tip_val: float) -> float:
    """Angle (deg, in [-180/n, 180/n)) of the centre of the tooth nearest to +x, from the tip-circle points."""
    r = np.hypot(pts[:, 0], pts[:, 1])
    tip = pts[r > r_tip_val - 2e-3]
    a = np.arctan2(tip[:, 1], tip[:, 0])
    ph = np.angle(np.exp(1j * n * a).sum()) / n
    return math.degrees(ph)


def pitch_tooth_thickness(pts: np.ndarray, n: int):
    """(tooth thickness, space width) as arcs (mm) on the nominal pitch circle, from an outline."""
    rp = pitch_r(n)
    r = np.hypot(pts[:, 0], pts[:, 1])
    a = np.unwrap(np.arctan2(pts[:, 1], pts[:, 0]))
    s = r - rp
    cross = np.where(np.sign(s[:-1]) * np.sign(s[1:]) < 0)[0]
    ang = []
    for i in cross:
        t = s[i] / (s[i] - s[i + 1])
        ang.append(float(a[i] + t * (a[i + 1] - a[i])))
    ang = np.array(sorted(a_ % (2 * math.pi) for a_ in ang))
    if len(ang) != 2 * n:
        raise RuntimeError("pitch circle crossed %d times, expected %d" % (len(ang), 2 * n))
    # crossings alternate rising/falling; tooth = rising -> falling pairs
    pitch = 2 * math.pi / n
    widths = np.diff(np.append(ang, ang[0] + 2 * math.pi))
    w_even, w_odd = widths[0::2].mean(), widths[1::2].mean()
    thick = min(w_even, w_odd)                     # the smaller of the two arc families is the tooth
    return float(thick * rp), float((pitch - thick) * rp)


# =============================================================================================================
# the three parts
# =============================================================================================================
def lightening_holes_xy():
    n, rr, ph = P.GRIPV6R_LIGHT_N, P.GRIPV6R_LIGHT_R, P.GRIPV6R_LIGHT_PHASE_DEG
    return [(rr * math.cos(math.radians(ph + 360.0 * k / n)), rr * math.sin(math.radians(ph + 360.0 * k / n)))
            for k in range(n)]


def lightening_ligaments() -> dict:
    """Ligaments (mm) of the Ø12 hole pattern: to the pocket wall, to the 36T root circle, hole to hole."""
    d, n, rr = P.GRIPV6R_LIGHT_D, P.GRIPV6R_LIGHT_N, P.GRIPV6R_LIGHT_R
    return dict(to_pocket_wall=rr - d / 2 - P.GRIPV6R_POCKET_R,
                to_root_circle=root_r(Z_MAIN) - (rr + d / 2),
                hole_to_hole=2 * rr * math.sin(math.pi / n) - d)


def make_pinion() -> cq.Workplane:
    """His 18T pinion, unchanged (re-homed to its axis, z 0..16)."""
    return _wp(_single_solid(home_pinion(), "pinion"))


def _arm_frame_shorten(solid: cq.Shape, arm_deg: float, delta: float, x_cut: float) -> cq.Shape:
    """Shorten the lug / fork by `delta` along its axis: remove the constant-section slab x in [x_cut, x_cut+delta]
    (arm frame: axis along +x) and slide the outer piece (pivot boss) inward by delta.  Cross-section, thickness,
    boss and fork shape are his."""
    s = rotate_z(solid, -arm_deg)
    big = 400.0
    zlo, zhi = -5.0, 60.0
    inner = s.cut(_box(x_cut, big, -big, big, zlo, zhi))
    outer = s.intersect(_box(x_cut + delta, big, -big, big, zlo, zhi)).moved(cq.Location(cq.Vector(-delta, 0, 0)))
    both = inner.fuse(outer).clean()
    return rotate_z(both, arm_deg)


def _compound_big_gear_replaced(phase_his_deg: float, relief: bool) -> cq.Shape:
    """His compound (his orientation, part frame) with the 54T ring replaced by the 36T ring."""
    h = home_compound()
    zb, zt = P.GRIPV6R_L1_Z0, P.GRIPV6R_L1_Z1
    # 1. remove his 54T ring + web outside the kept core (everything of layer 1 outside R_core)
    cutter = _cyl(60.0, zb - 2.0, zt).cut(_cyl(P.GRIPV6R_CORE_R, zb - 3.0, zt + 1.0))
    core_and_upper = h.cut(cutter)
    # 2. the new 36T ring: his tooth form, bore-less blank minus core, lightening holes, relief
    ring = involute_ring(Z_MAIN, zt - zb, phase_his_deg).moved(cq.Location(cq.Vector(0, 0, zb)))
    ring = ring.cut(_cyl(P.GRIPV6R_CORE_R, zb - 1.0, zt + 1.0))
    for hx, hy in lightening_holes_xy():
        ring = ring.cut(_cyl(P.GRIPV6R_LIGHT_D / 2.0, zb - 1.0, zt + 1.0, hx, hy))
    if relief:
        rel = _cyl(80.0, zt - P.GRIPV6R_RELIEF_DEPTH, zt + 1.0).cut(
            _cyl(P.GRIPV6R_RELIEF_R_IN, zt - P.GRIPV6R_RELIEF_DEPTH - 1.0, zt + 2.0))
        ring = ring.cut(rel)
    return core_and_upper.fuse(ring).clean()




# -------------------------------------------------------------------------------------------------------------
# crank re-phasing (his -> v7 closed pose).  Angles are CCW from +x about the gear axis, the same convention as
# gripper_v7_kin (theta) and his world frame (v6 world = v7 local + (951.8475, 707.9864)); no sign flip needed.
# -------------------------------------------------------------------------------------------------------------
def delta_c() -> float:
    return P.GRIPV6R_ARM_DEG_C - P.GRIPV6R_SRC_ARM_DEG_C        # his compound lug -> v7 closed (-78.589)


def delta_f() -> float:
    return P.GRIPV6R_ARM_DEG_F - P.GRIPV6R_SRC_ARM_DEG_F        # his follower lug -> mirror of it (258.589)


# -------------------------------------------------------------------------------------------------------------
# mesh phasing of the 36T ring
# -------------------------------------------------------------------------------------------------------------
def pinion_outline() -> np.ndarray:
    """His pinion tooth outline (part frame, his orientation) at mid face."""
    return _cached_outline("pinion", lambda: outer_outline(home_pinion(), 8.0))


_OUTLINE_CACHE: dict = {}


def _cached_outline(key, fn):
    if key not in _OUTLINE_CACHE:
        _OUTLINE_CACHE[key] = fn()
    return _OUTLINE_CACHE[key]


def pinion_phase_deg() -> float:
    return tooth_phase_deg(pinion_outline(), Z_PIN, tip_r(Z_PIN))


def pose_outline(pts: np.ndarray, axis_xy, rot_deg: float) -> Outline:
    """Part-frame outline rotated about its own axis by rot_deg, then placed at axis_xy."""
    return Outline(_rot2(pts, rot_deg) + np.array(axis_xy))


def rotation_window(fixed: Outline, moving_pts: np.ndarray, axis_xy, rot_deg: float, step: float = 0.1,
                    limit: float = 8.0):
    """Rotation interval [lo, hi] (deg, about the pose rot_deg) over which the moving outline does not touch the
    fixed one.  (0, 0) if it already overlaps."""
    def f(psi):
        return signed_gap(fixed, pose_outline(moving_pts, axis_xy, rot_deg + psi))
    if f(0.0) <= 0.0:
        return (0.0, 0.0)
    out = []
    for sgn in (+1.0, -1.0):
        a = 0.0
        while a < limit and f(sgn * (a + step)) > 0.0:
            a += step
        if a >= limit:
            out.append(sgn * limit)
            continue
        out.append(sgn * brentq(lambda t: f(sgn * t), a, a + step, xtol=1e-5))
    return (min(out), max(out))


def _main_phase_guess_deg() -> float:
    """Analytic phase of the 36T teeth (closed-pose orientation) that puts his unrotated pinion mid-window.
    The pinion tooth centre nearest the line of centres is eps off it; the big gear is then rotated -eps/2
    (ratio 2) from the 'gap on the line of centres' position."""
    sx, sy = P.GRIPV6R_S_XY
    cx, cy = P.GRIPV6R_C_XY
    ang_sc = math.degrees(math.atan2(cy - sy, cx - sx))
    ang_cs = ang_sc + 180.0
    eps = (pinion_phase_deg() - ang_sc + 180.0 / Z_PIN) % (360.0 / Z_PIN) - 180.0 / Z_PIN
    return ang_cs - eps / 2.0 + 180.0 / Z_MAIN


def main_phase_deg() -> float:
    """36T tooth phase (closed-pose orientation), refined on the 2D outlines until the pinion window is centred
    to 1e-3 deg."""
    def solve():
        ph = _main_phase_guess_deg()
        pin = outer_outline(home_pinion(), 8.0, 0.05)          # coarse outlines: this only centres the window
        for _ in range(5):
            ring = Outline(outer_outline(involute_ring(Z_MAIN, 1.0, ph), 0.5, 0.05)).placed(0.0, P.GRIPV6R_C_XY)
            lo, hi = rotation_window(ring, pin, P.GRIPV6R_S_XY, 0.0)
            centre = 0.5 * (lo + hi)                  # pinion rotation that would centre it
            if abs(centre) < 1e-3:
                break
            ph += centre / P.GRIPV6R_SWEEP_PINION_RATIO
        return ph
    return _cached_outline("main_phase", solve)


# -------------------------------------------------------------------------------------------------------------
# the three parts, final (closed-pose) frame
# -------------------------------------------------------------------------------------------------------------
def make_pinion() -> cq.Workplane:
    """His 18T pinion, unchanged (re-homed to its own axis, z 0..16, his orientation)."""
    return _wp(_single_solid(home_pinion(), "pinion"))


def make_compound(relief: bool = True) -> cq.Workplane:
    ph_his = main_phase_deg() - delta_c()
    s = _compound_big_gear_replaced(ph_his, relief)
    s = _arm_frame_shorten(s, P.GRIPV6R_SRC_ARM_DEG_C, P.GRIPV6R_ARM_SHORTEN, P.GRIPV6R_ARM_CUT_X)
    s = rotate_z(s, delta_c())
    return _wp(_single_solid(s, "compound" + ("" if relief else "_norelief")))


def make_follower() -> cq.Workplane:
    s = _arm_frame_shorten(home_follower(), P.GRIPV6R_SRC_ARM_DEG_F, P.GRIPV6R_ARM_SHORTEN, P.GRIPV6R_ARM_CUT_X)
    s = rotate_z(s, delta_f())
    return _wp(_single_solid(s, "follower"))


@lru_cache(maxsize=None)
def part(name: str) -> cq.Shape:
    """Cached final parts: pinion, compound, compound_norelief, follower (closed-pose frame)."""
    mk = {"pinion": make_pinion, "compound": lambda: make_compound(True),
          "compound_norelief": lambda: make_compound(False), "follower": make_follower}[name]
    return mk().val()


def deep_copy(shape: cq.Shape) -> cq.Shape:
    """Independent copy (meshing / STL export attaches triangulations to the shared faces and makes isValid() report
    False on the original -- always mesh a copy)."""
    return cq.Shape.cast(BRepBuilderAPI_Copy(shape.wrapped, True).Shape())


def print_pose(name: str, shape: cq.Shape) -> cq.Shape:
    """Print orientation (independent copy): gear axis vertical, lowest face on the bed (z min = 0)."""
    z0 = shape.BoundingBox().zmin
    return deep_copy(shape).moved(cq.Location(cq.Vector(0, 0, -z0)))


def place(shape: cq.Shape, axis_xy, rot_deg: float = 0.0) -> cq.Shape:
    """Rotate about the part axis, then translate to the placement-frame axis position."""
    return rotate_z(shape, rot_deg).moved(cq.Location(cq.Vector(axis_xy[0], axis_xy[1], 0.0)))


def pose_shapes(delta_deg: float, compound: str = "compound") -> dict:
    """The three gears placed at crank offset delta (deg from the closed pose, positive = opening)."""
    return dict(pinion=place(part("pinion"), P.GRIPV6R_S_XY, -P.GRIPV6R_SWEEP_PINION_RATIO * delta_deg),
                compound=place(part(compound), P.GRIPV6R_C_XY, delta_deg),
                follower=place(part("follower"), P.GRIPV6R_F_XY, -delta_deg))


# =============================================================================================================
# mesh analysis (2D outlines of the real solids)
# =============================================================================================================
def mesh_outlines() -> dict:
    """Mid-face outlines (part frame, closed-pose orientation) of the meshing layers of the FINAL parts."""
    comp, fol = part("compound"), part("follower")
    return dict(
        pinion=pinion_outline(),
        ring36=_cached_outline("ring36", lambda: outer_outline(comp, 8.0)),
        sync_c=_cached_outline("sync_c", lambda: outer_outline(comp, 31.0)),    # above the lug band: full 24T teeth
        sync_f=_cached_outline("sync_f", lambda: outer_outline(fol, 31.0)))


def mesh_report(deltas) -> dict:
    """For every crank offset: circumferential backlash at the pitch circle (rotation window x pitch radius of the
    moving gear) and the neutral-pose minimum gap, for pinion/36T and 24T/24T.  Gear 1 fixed, gear 2 = pinion or
    follower."""
    o = mesh_outlines()
    cxy, fxy, sxy = P.GRIPV6R_C_XY, P.GRIPV6R_F_XY, P.GRIPV6R_S_XY
    rows = []
    for d in deltas:
        ring = pose_outline(o["ring36"], cxy, d)
        pin_w = rotation_window(ring, o["pinion"], sxy, -P.GRIPV6R_SWEEP_PINION_RATIO * d)
        pin_gap = signed_gap(ring, pose_outline(o["pinion"], sxy, -P.GRIPV6R_SWEEP_PINION_RATIO * d))
        sc = pose_outline(o["sync_c"], cxy, d)
        sync_w = rotation_window(sc, o["sync_f"], fxy, -d)
        sync_gap = signed_gap(sc, pose_outline(o["sync_f"], fxy, -d))
        rows.append(dict(
            delta_deg=float(d),
            pinion36=dict(window_deg=[pin_w[0], pin_w[1]], centre_deg=0.5 * (pin_w[0] + pin_w[1]),
                          backlash_mm=(pin_w[1] - pin_w[0]) * math.pi / 180.0 * pitch_r(Z_PIN), gap_mm=pin_gap),
            sync24=dict(window_deg=[sync_w[0], sync_w[1]], centre_deg=0.5 * (sync_w[0] + sync_w[1]),
                        backlash_mm=(sync_w[1] - sync_w[0]) * math.pi / 180.0 * pitch_r(Z_SYNC), gap_mm=sync_gap)))
    return dict(rows=rows)


def radii_report() -> dict:
    """Measured tip / root radii (from the outlines of the final parts) and the tip-to-root clearances at the v7
    centres, plus the pitch-circle tooth thickness of his 54T and the new 36T."""
    o = mesh_outlines()
    rr = {k: (float(np.hypot(v[:, 0], v[:, 1]).max()), float(np.hypot(v[:, 0], v[:, 1]).min())) for k, v in o.items()}
    cd_main, cd_sync = P.GRIPV6R_CD_MAIN, P.GRIPV6R_CD_SYNC
    tip, root = {k: v[0] for k, v in rr.items()}, {k: v[1] for k, v in rr.items()}
    his54 = outer_outline(home_compound(), 8.0)
    return dict(
        tip_radius=tip, root_radius=root,
        pinion_tip_to_36T_root=cd_main - tip["pinion"] - root["ring36"],
        ring36_tip_to_pinion_root=cd_main - tip["ring36"] - root["pinion"],
        sync_c_tip_to_f_root=cd_sync - tip["sync_c"] - root["sync_f"],
        sync_f_tip_to_c_root=cd_sync - tip["sync_f"] - root["sync_c"],
        tooth_thickness_pitch_mm={"his_54T": pitch_tooth_thickness(_cached_outline("his54", lambda: his54), 54)[0],
                                  "new_36T": pitch_tooth_thickness(o["ring36"], Z_MAIN)[0],
                                  "his_pinion_18T": pitch_tooth_thickness(o["pinion"], Z_PIN)[0],
                                  "his_24T_follower": pitch_tooth_thickness(o["sync_f"], Z_SYNC)[0],
                                  "ideal_pitch_circle": math.pi * M / 2.0},
        nominal_cd=dict(main=M * (Z_PIN + Z_MAIN) / 2.0, sync=M * Z_SYNC))


# =============================================================================================================
# 3D checks on the real solids
# =============================================================================================================
def common_volume(a: cq.Shape, b: cq.Shape) -> float:
    r = a.intersect(b)
    return float(r.Volume()) if r.Solids() else 0.0


def interference_3d(deltas, compound: str = "compound") -> list:
    """Boolean common volume (mm3) of each gear pair at each crank offset (all three gears, full solids)."""
    rows = []
    for d in deltas:
        s = pose_shapes(d, compound)
        rows.append(dict(delta_deg=float(d),
                         pinion_compound=common_volume(s["pinion"], s["compound"]),
                         compound_follower=common_volume(s["compound"], s["follower"]),
                         pinion_follower=common_volume(s["pinion"], s["follower"])))
    return rows


def interference_control(extra_deg: float = 3.0) -> dict:
    """Positive control for the boolean check: the same pairs with the second gear turned `extra_deg` off the clearance
    window (backlash window is only about +-0.7 deg) MUST show a real overlap volume."""
    s = pose_shapes(0.0)
    fol = place(part("follower"), P.GRIPV6R_F_XY, extra_deg)
    pin = place(part("pinion"), P.GRIPV6R_S_XY, extra_deg)
    return dict(extra_deg=extra_deg, compound_follower=common_volume(s["compound"], fol),
                pinion_compound=common_volume(pin, s["compound"]))


LUG_X0 = P.GRIPV6R_ARM_R - 32.0          # arm-frame x where the lug / fork piece starts (R21, 1.5 mm outside the 24T tips)


def lug_piece(shape: cq.Shape, arm_deg: float) -> cq.Shape:
    """The lug / fork of a closed-pose part: everything beyond arm-frame x = LUG_X0 and above the pinion / 36T layer."""
    s = rotate_z(shape, -arm_deg)
    piece = s.intersect(_box(LUG_X0, 400.0, -400.0, 400.0, P.GRIPV6R_L1_Z1 - 0.001, 60.0))
    return rotate_z(piece, arm_deg)


def pocket_ranges(shape: cq.Shape, r_pocket: float = P.GRIPV6R_POCKET_R):
    """z ranges of the on-axis bearing-pocket cylinders (his Ø14.075), merged."""
    zs = set()
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - r_pocket) < 1e-3:
            bb = f.BoundingBox()
            zs.add((round(bb.zmin, 3), round(bb.zmax, 3)))
    return sorted(zs)


def hardware_cylinders(axis_xy, ranges):
    """Ø7 pin (z -3 .. 39) and Ø14 bearing envelopes in his pockets, at a placed axis."""
    out = [("pin", _cyl(P.GRIPV6R_PIN_D / 2.0, -3.0, 39.0, axis_xy[0], axis_xy[1]))]
    for z0, z1 in ranges:
        out.append(("bearing %.2f..%.2f" % (z0, z1), _cyl(P.GRIPV6R_BRG_OD / 2.0, z0, z1, axis_xy[0], axis_xy[1])))
    return out


def swept_clearance(deltas) -> dict:
    """Minimum 3D distance of each crank lug / fork to the other gear, the other lug, the pins and bearings and the
    pinion over the stroke."""
    comp, fol = part("compound"), part("follower")
    lug_c0, lug_f0 = lug_piece(comp, P.GRIPV6R_ARM_DEG_C), lug_piece(fol, P.GRIPV6R_ARM_DEG_F)
    rc, rf = pocket_ranges(comp), pocket_ranges(fol)
    rows = []
    for d in deltas:
        s = pose_shapes(d)
        lug_c = place(lug_c0, P.GRIPV6R_C_XY, d)
        lug_f = place(lug_f0, P.GRIPV6R_F_XY, -d)
        t_c = [("follower gear", s["follower"]), ("follower lug", lug_f), ("pinion", s["pinion"])] \
            + [("F " + n, c) for n, c in hardware_cylinders(P.GRIPV6R_F_XY, rf)]
        t_f = [("compound gear", s["compound"]), ("compound lug", lug_c), ("pinion", s["pinion"])] \
            + [("C " + n, c) for n, c in hardware_cylinders(P.GRIPV6R_C_XY, rc)]
        for who, lug, targets in (("compound lug", lug_c, t_c), ("follower lug", lug_f, t_f)):
            for name, tgt in targets:
                rows.append(dict(delta_deg=float(d), lug=who, target=name, distance_mm=float(lug.distance(tgt))))
    best = min(rows, key=lambda r: r["distance_mm"])
    return dict(rows=rows, min=best)


def top_face_z_36T_layer(shape: cq.Shape) -> float:
    """z of the (largest) upward planar face of the 36T layer below the 24T layer: 16.0 as built by him, 15.7 with the relief."""
    best = None
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Plane:
            pl = a.Plane()
            nz = pl.Axis().Direction().Z()
            z = pl.Location().Z()
            if nz > 0.999 and 10.0 < z < P.GRIPV6R_L1_Z1 + 1e-6 and (best is None or f.Area() > best[0]):
                best = (f.Area(), z)
    return best[1]


def axial_gaps() -> dict:
    comp, compn, fol, pin = part("compound"), part("compound_norelief"), part("follower"), part("pinion")
    fol_zmin = min(z for z in (pl_z for pl_z in _plane_levels(fol)) if z > 0)
    boss_plane = pin.BoundingBox().zmax + P.GRIPV6R_PINION_BOSS_GAP
    return dict(follower_bottom_z=fol_zmin,
                big_gear_top_z_relief=top_face_z_36T_layer(comp),
                big_gear_top_z_norelief=top_face_z_36T_layer(compn),
                follower_to_36T_relief=fol_zmin - top_face_z_36T_layer(comp),
                follower_to_36T_norelief=fol_zmin - top_face_z_36T_layer(compn),
                pinion_top_z=pin.BoundingBox().zmax, servo_boss_plane_z=boss_plane,
                pinion_to_boss=boss_plane - pin.BoundingBox().zmax)


def _plane_levels(shape: cq.Shape):
    out = set()
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Plane:
            pl = a.Plane()
            if abs(abs(pl.Axis().Direction().Z()) - 1.0) < 1e-9 and f.Area() > 20.0:
                out.add(round(pl.Location().Z(), 4))
    return sorted(out)


def radial_36T_to_follower() -> dict:
    """36T tip circle against the follower in the 36T layer (z < 16).  His follower has no material below z = 16;
    the radial numbers are to its axis hardware and to a bearing-sized hub, with the axial separation."""
    tip36 = tip_r(Z_MAIN)
    cd = P.GRIPV6R_CD_SYNC
    fol = part("follower")
    return dict(
        follower_material_below_z16_mm3=float(common_volume(fol, _box(-200, 200, -200, 200, -5.0, P.GRIPV6R_L1_Z1 - 1e-4))),
        tip36_radius=tip36,
        radial_to_follower_pin_r3p5=cd - tip36 - P.GRIPV6R_PIN_D / 2.0,
        radial_to_follower_bearing_envelope_r7=cd - tip36 - P.GRIPV6R_BRG_OD / 2.0,
        radial_to_follower_pocket_wall_r7p0375=cd - tip36 - P.GRIPV6R_POCKET_R,
        max_bearing_od_for_1mm=2.0 * (cd - tip36 - P.GRIPV6R_RADIAL_36T_FOLLOWER_MIN))


# =============================================================================================================
# feature-by-feature diff against his originals
# =============================================================================================================
def _surface_census(shape: cq.Shape):
    """(on-axis cylinders, off-axis cylinders): {(R, z0, z1): (face count, total area mm2)}.  Areas are compared, not
    face counts: a boolean or a rotation may split / merge the seam of a periodic cylinder face."""
    on, off = {}, {}
    BRepTools.Clean_s(shape.wrapped)      # a stale / foreign mesh would inflate the face bounding boxes
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        c = a.Cylinder()
        loc = c.Axis().Location()
        bb = f.BoundingBox()
        key = (round(c.Radius(), 4), round(bb.zmin, 3), round(bb.zmax, 3))
        d = on if math.hypot(loc.X(), loc.Y()) < 0.01 else off
        n0, a0 = d.get(key, (0, 0.0))
        d[key] = (n0 + 1, a0 + f.Area())
    return on, off


def arm_section(shape: cq.Shape, arm_deg: float, z: float, xs):
    """y crossings (sorted) of the section loops with the lines x = const in the arm frame (axis along +x)."""
    res = {}
    loops = [_rot2(p, -arm_deg) for p in outlines(shape, z, 0.05)]
    for x in xs:
        ys = []
        for p in loops:
            a, b = p[:-1], p[1:]
            m = (a[:, 0] - x) * (b[:, 0] - x) < 0
            t = (x - a[m, 0]) / (b[m, 0] - a[m, 0])
            ys += list(a[m, 1] + t * (b[m, 1] - a[m, 1]))
        res[x] = [round(float(v), 3) for v in sorted(ys)]
    return res


def pivot_hole(shape: cq.Shape):
    """(diameter, distance from the axis, angle deg) of the off-axis hole of the lug / fork band."""
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder:
            c = a.Cylinder()
            loc = c.Axis().Location()
            d = math.hypot(loc.X(), loc.Y())
            bb = f.BoundingBox()
            if d > 30.0 and bb.zlen < 10.5 and c.Radius() < 5.0:
                return (2 * c.Radius(), d, math.degrees(math.atan2(loc.Y(), loc.X())))
    raise RuntimeError("no pivot hole")


def hole_centres(shape: cq.Shape, radius: float):
    """Distinct (x, y) axes of the off-axis cylinders of the given radius (counts holes, immune to face splitting)."""
    out = set()
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - radius) < 1e-3:
            loc = a.Cylinder().Axis().Location()
            if math.hypot(loc.X(), loc.Y()) > 0.01:
                out.add((round(loc.X(), 3), round(loc.Y(), 3)))
    return out


def feature_diff(which: str) -> list:
    """Rows {feature, original, modified, status} comparing the final part against his homed original."""
    if which == "pinion":
        o, n = home_pinion(), part("pinion")
    elif which in ("compound", "compound_norelief"):
        o, n = home_compound(), part(which)
    elif which == "follower":
        o, n = home_follower(), part("follower")
    else:
        raise KeyError(which)
    rows = []

    def add(feature, a, b, intended=None):
        same = (a == b) or (isinstance(a, float) and isinstance(b, float) and abs(a - b) < 1e-3)
        status = "identical" if same else (intended or "CHANGED (UNINTENDED)")
        rows.append(dict(feature=feature, original=a, modified=b, status=status))

    on_o, off_o = _surface_census(o)
    on_n, off_n = _surface_census(n)
    area = lambda d, k: round(d[k][1], 2) if k in d else 0.0
    tooth_r = {round(tip_r(Z_MAIN), 4), round(root_r(Z_MAIN), 4), round(tip_r(54), 4), round(root_r(54), 4)}

    def add_area(label, k, do, dn, intended=None):
        a, b = area(do, k), area(dn, k)
        rows.append(dict(feature=label, original=a, modified=b,
                         status="identical" if abs(a - b) < 0.05 else (intended or "CHANGED (UNINTENDED)")))

    if which.startswith("compound"):
        for k in sorted(set(on_o) | set(on_n)):
            if k[0] in tooth_r and k[1] == 0.0:
                continue
            relief_wall = (k[0] == round(P.GRIPV6R_RELIEF_R_IN, 4) and k[1] == round(P.GRIPV6R_L1_Z1 - P.GRIPV6R_RELIEF_DEPTH, 3))
            add_area("axis cylinder R%.4f z %.3f..%.3f, area mm2 (pocket / lip / shoulder / bore / 24T tip + root)" % k, k,
                     on_o, on_n, "intended: 0.30 mm relief wall (flagged functional change)" if relief_wall else None)
        tip_o = [k for k in on_o if k[0] == round(tip_r(54), 4)][0]
        tip_n = [k for k in on_n if k[0] == round(tip_r(Z_MAIN), 4)][0]
        add("big gear tip radius (mm)", tip_o[0], tip_n[0], "intended: 54T -> 36T tooth count")
        rt_o = [k for k in on_o if k[0] == round(root_r(54), 4)][0]
        rt_n = [k for k in on_n if k[0] == round(root_r(Z_MAIN), 4)][0]
        add("big gear root radius (mm)", rt_o[0], rt_n[0], "intended: 54T -> 36T tooth count")
        add("big gear teeth (tip faces)", on_o[tip_o][0], on_n[tip_n][0], "intended: 54T -> 36T tooth count")
        k04 = lambda off: sum(v[0] for k, v in off.items() if k[0] == 0.4 and k[1] == 0.0)
        add("big gear root fillets R0.4 (faces, 2 per tooth)", k04(off_o), k04(off_n), "intended: 54T -> 36T tooth count")
        add("lightening hole radius (mm)", 6.0, 6.0)
        add("lightening holes (count)", len(hole_centres(o, 6.0)), len(hole_centres(n, 6.0)),
            "intended: holes re-laid for the 36T ring")
        for k in sorted(set(off_o) | set(off_n)):
            if (k[0] == 0.4 and k[1] == 0.0) or k[0] == 6.0:
                continue
            add_area("off-axis cylinder R%.4f z %.3f..%.3f, area mm2" % k, k, off_o, off_n)
    else:
        for k in sorted(set(on_o) | set(on_n)):
            add_area("axis cylinder R%.4f z %.3f..%.3f, area mm2" % k, k, on_o, on_n)
        for k in sorted(set(off_o) | set(off_n)):
            add_area("off-axis cylinder R%.4f z %.3f..%.3f, area mm2" % k, k, off_o, off_n)
    lv_o, lv_n = _plane_levels(o), _plane_levels(n)
    extra = [z for z in lv_n if z not in lv_o]
    if which == "compound" and extra:
        add("planar levels (z) with area > 20 mm2 (face widths 16 / 20, pocket floors, lug band 16..26)",
            [z for z in lv_o], [z for z in lv_n if z not in extra],
            None)
        add("planar level added by the relief", None, extra, "intended: 0.30 mm relief (flagged functional change)")
    else:
        add("planar levels (z) with area > 20 mm2 (face widths, pocket floors, lug band)", lv_o, lv_n)
    if which in ("compound", "compound_norelief", "follower"):
        a_o = P.GRIPV6R_SRC_ARM_DEG_C if which.startswith("compound") else P.GRIPV6R_SRC_ARM_DEG_F
        a_n = P.GRIPV6R_ARM_DEG_C if which.startswith("compound") else P.GRIPV6R_ARM_DEG_F
        ho, hn = pivot_hole(o), pivot_hole(n)
        add("pivot hole diameter (mm)", round(ho[0], 3), round(hn[0], 3))
        add("pivot radius from the axis (mm)", round(ho[1], 3), round(hn[1], 3), "intended: crank R75 -> R53")
        add("lug angle (deg, CCW from +x)", round(ho[2], 3), round(hn[2], 3),
            "intended: re-phased to the v7 closed pose")
        sh = P.GRIPV6R_ARM_SHORTEN
        xs_o = [25.0, 60.0, 70.0]
        so = arm_section(o, a_o, 1101.0 - P.GRIPV6R_SRC_Z0, xs_o)
        sn = arm_section(n, a_n, 1101.0 - P.GRIPV6R_SRC_Z0, [x - (sh if x > P.GRIPV6R_ARM_CUT_X + sh else 0.0) for x in xs_o])
        for x, xn in zip(xs_o, sn):
            add("lug / fork section y crossings at arm x = %.0f (orig) / %.0f (new)" % (x, xn), so[x], sn[xn])
        zl_o = sorted({z for z in _plane_levels(o) if 15.9 < z < 26.1})
        zl_n = sorted({z for z in _plane_levels(n) if 15.9 < z < 26.1})
        add("lug / fork thickness band z (mm)", [z for z in zl_o if z in (16.0, 26.0)], [z for z in zl_n if z in (16.0, 26.0)])
    ob, nb = o.Volume(), n.Volume()
    rows.append(dict(feature="volume (mm3)", original=round(ob, 1), modified=round(nb, 1), status="info"))
    return rows
