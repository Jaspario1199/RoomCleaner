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

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.GeomAbs import GeomAbs_Cylinder

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
    """Chain unordered edge polylines into closed loops."""
    pts = [e for e in edges_pts]
    loops = []
    tol = 2e-4
    used = [False] * len(pts)
    for i in range(len(pts)):
        if used[i]:
            continue
        used[i] = True
        loop = [pts[i]]
        end = pts[i][-1]
        start = pts[i][0]
        for _ in range(len(pts)):
            if np.hypot(*(end - start)) < tol and len(loop) > 1:
                break
            nxt = None
            for j in range(len(pts)):
                if used[j]:
                    continue
                if np.hypot(*(pts[j][0] - end)) < tol:
                    nxt = (j, pts[j])
                    break
                if np.hypot(*(pts[j][-1] - end)) < tol:
                    nxt = (j, pts[j][::-1])
                    break
            if nxt is None:
                break
            used[nxt[0]] = True
            loop.append(nxt[1])
            end = nxt[1][-1]
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
        pp = [e.positionAt(t) for t in np.linspace(0.0, 1.0, n)]
        polys.append(np.array([[p.x, p.y] for p in pp]))
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
    """Closed polygon with fast signed-distance queries."""

    def __init__(self, pts: np.ndarray):
        self.pts = pts
        self.path = MplPath(pts)
        self.tree = cKDTree(pts)

    def placed(self, deg: float, xy) -> "Outline":
        return Outline(_rot2(self.pts, deg) + np.array(xy))


def signed_gap(A: Outline, B: Outline) -> float:
    """> 0: minimum distance between the two outlines (no overlap).  < 0: -(maximum penetration depth)."""
    inA = B.path.contains_points(A.pts)
    inB = A.path.contains_points(B.pts)
    if inA.any() or inB.any():
        d = 0.0
        if inA.any():
            d = max(d, float(B.tree.query(A.pts[inA])[0].max()))
        if inB.any():
            d = max(d, float(A.tree.query(B.pts[inB])[0].max()))
        return -max(d, 1e-9)
    return float(min(B.tree.query(A.pts)[0].min(), A.tree.query(B.pts)[0].min()))


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
        pin = pinion_outline()
        for _ in range(5):
            ring = Outline(outer_outline(involute_ring(Z_MAIN, 1.0, ph), 0.5)).placed(0.0, P.GRIPV6R_C_XY)
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


def print_pose(name: str, shape: cq.Shape) -> cq.Shape:
    """Print orientation: gear axis vertical, lowest face on the bed (z min = 0)."""
    return shape.moved(cq.Location(cq.Vector(0, 0, -shape.BoundingBox().zmin)))


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
