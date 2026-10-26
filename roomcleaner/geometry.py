"""
Geometric safety tests -- most importantly: does a cable pass through the fan?

The ceiling fan is modelled as a vertical no-go CYLINDER (see config.FanZone).
Each cable is a straight line segment from a ceiling corner (the winch anchor)
to the end-effector. We must guarantee that NO cable segment ever passes through
that cylinder, and that the effector itself never enters it.

The core routine here, `segment_intersects_cylinder`, is exact (no sampling):
it solves for the exact range of the segment that lies inside the cylinder's
infinite radius, then checks whether that range also lies within the cylinder's
height band. If both overlap, the segment pierces the cylinder.
"""

from __future__ import annotations

import numpy as np


def segment_intersects_cylinder(
    a: np.ndarray,
    b: np.ndarray,
    center_xy: tuple[float, float],
    radius: float,
    z_low: float,
    z_high: float,
    eps: float = 1e-9,
) -> bool:
    """Return True if segment A->B passes through the vertical finite cylinder.

    The cylinder is axis-aligned with +z: infinite-radius `radius` around the
    vertical line (center_xy), clipped to z in [z_low, z_high].

    Method:
      1. Horizontal test. Project the segment to the xy-plane and solve the
         quadratic |a_xy + t*d_xy - c|^2 = radius^2 for t. The two roots bound
         the sub-interval [t_r0, t_r1] of the segment that is within `radius`.
      2. Vertical test. z(t) = a_z + t*d_z is linear; find the t-interval
         [t_z0, t_z1] where z(t) is within [z_low, z_high].
      3. The segment pierces the cylinder iff [t_r0,t_r1], [t_z0,t_z1] and the
         segment's own [0,1] all share a common sub-interval.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.array([center_xy[0], center_xy[1]], dtype=float)
    d = b - a

    # ---- 1. horizontal (radius) interval in t ----
    a_xy = a[:2] - c
    d_xy = d[:2]
    dd = float(d_xy @ d_xy)
    if dd < eps:
        # Segment is vertical (or a point): inside-radius for all t iff a_xy in disk.
        if float(a_xy @ a_xy) > radius * radius:
            return False
        t_r0, t_r1 = 0.0, 1.0
    else:
        b_coef = 2.0 * float(a_xy @ d_xy)
        c_coef = float(a_xy @ a_xy) - radius * radius
        disc = b_coef * b_coef - 4.0 * dd * c_coef
        if disc < 0:
            return False  # horizontal projection never reaches within radius
        sq = np.sqrt(disc)
        t_r0 = (-b_coef - sq) / (2.0 * dd)
        t_r1 = (-b_coef + sq) / (2.0 * dd)
        if t_r0 > t_r1:
            t_r0, t_r1 = t_r1, t_r0

    # ---- 2. vertical (height band) interval in t ----
    dz = d[2]
    if abs(dz) < eps:
        # Constant height: inside band for all t iff a_z within [z_low, z_high].
        if not (z_low - eps <= a[2] <= z_high + eps):
            return False
        t_z0, t_z1 = 0.0, 1.0
    else:
        tz_a = (z_low - a[2]) / dz
        tz_b = (z_high - a[2]) / dz
        t_z0, t_z1 = (tz_a, tz_b) if tz_a <= tz_b else (tz_b, tz_a)

    # ---- 3. common overlap with the segment's own [0, 1] ----
    lo = max(t_r0, t_z0, 0.0)
    hi = min(t_r1, t_z1, 1.0)
    return bool(lo <= hi + eps)


def point_in_cylinder(
    p: np.ndarray,
    center_xy: tuple[float, float],
    radius: float,
    z_low: float,
    z_high: float,
    eps: float = 1e-9,
) -> bool:
    """True if point p is inside the vertical finite cylinder."""
    p = np.asarray(p, dtype=float)
    if not (z_low - eps <= p[2] <= z_high + eps):
        return False
    dx = p[0] - center_xy[0]
    dy = p[1] - center_xy[1]
    return bool((dx * dx + dy * dy) <= radius * radius + eps)


def cables_clear_of_fan(anchors: np.ndarray, effector: np.ndarray, fan) -> bool:
    """True if EVERY cable (anchor_i -> effector) avoids the fan cylinder,
    and the effector itself is outside it.

    `fan` is a config.FanZone. If the fan is disabled, always True.
    """
    if fan is None or not getattr(fan, "enabled", False):
        return True

    center = (fan.cx, fan.cy)
    if point_in_cylinder(effector, center, fan.radius, fan.z_low, fan.z_high):
        return False
    for anchor in anchors:
        if segment_intersects_cylinder(
            anchor, effector, center, fan.radius, fan.z_low, fan.z_high
        ):
            return False
    return True


# ---------------------------------------------------------------------------------------------------------------------
# Gen-2 room map (docs/ROOM_MAP_SPEC.md 3): the same exact tests for an oriented box (a vertical prism over a rectangle
# turned by ``yaw`` about +z), and vectorised forms of both for the app's coverage grid (many segments, one shape).

def _clip_slab(p0, d, lo, hi, t0, t1, eps):
    """Clip [t0, t1] to the t where p0 + t d lies in [lo, hi] (one slab). Returns (t0, t1); empty when t0 > t1."""
    if abs(d) < eps:
        if p0 < lo - eps or p0 > hi + eps:
            return 1.0, 0.0
        return t0, t1
    ta, tb = (lo - p0) / d, (hi - p0) / d
    if ta > tb:
        ta, tb = tb, ta
    return max(t0, ta), min(t1, tb)


def segment_intersects_box(
    a: np.ndarray,
    b: np.ndarray,
    center_xy: tuple[float, float],
    half_length: float,
    half_width: float,
    yaw_rad: float,
    z_low: float,
    z_high: float,
    eps: float = 1e-9,
) -> bool:
    """Return True if segment A->B passes through the oriented box.

    The box is the rectangle |u| <= half_length, |v| <= half_width in its own frame (u along the length, turned by
    ``yaw_rad`` from room +x), extruded over z in [z_low, z_high]. Slab test: the segment is moved into the box frame
    and its parameter interval [0, 1] is clipped by the u, v and z slabs in turn; it pierces the box iff something is left.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c, s = np.cos(yaw_rad), np.sin(yaw_rad)
    ax, ay = a[0] - center_xy[0], a[1] - center_xy[1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p0, d, h in ((c * ax + s * ay, c * dx + s * dy, half_length), (-s * ax + c * ay, -s * dx + c * dy, half_width)):
        t0, t1 = _clip_slab(p0, d, -h, h, t0, t1, eps)
        if t0 > t1 + eps:
            return False
    t0, t1 = _clip_slab(a[2], b[2] - a[2], z_low, z_high, t0, t1, eps)
    return bool(t0 <= t1 + eps)


def xy_distance_to_box(xy, center_xy, half_length, half_width, yaw_rad) -> np.ndarray:
    """Floor distance (m) from the point(s) ``xy`` (..., 2) to the box's rectangle; 0 inside it."""
    xy = np.asarray(xy, dtype=float)
    c, s = np.cos(yaw_rad), np.sin(yaw_rad)
    px, py = xy[..., 0] - center_xy[0], xy[..., 1] - center_xy[1]
    u, v = np.abs(c * px + s * py) - half_length, np.abs(-s * px + c * py) - half_width
    return np.hypot(np.maximum(u, 0.0), np.maximum(v, 0.0))


def segments_hit_cylinder(a, b, center_xy, radius, z_low, z_high, eps: float = 1e-9) -> np.ndarray:
    """Vectorised ``segment_intersects_cylinder``: ``a``, ``b`` are (..., 3); returns a bool array of shape (...)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    d = b - a
    px, py = a[..., 0] - center_xy[0], a[..., 1] - center_xy[1]
    dx, dy = d[..., 0], d[..., 1]
    dd = dx * dx + dy * dy
    bq = 2.0 * (px * dx + py * dy)
    cq = px * px + py * py - radius * radius
    flat = dd < eps
    with np.errstate(divide="ignore", invalid="ignore"):
        disc = bq * bq - 4.0 * dd * cq
        sq = np.sqrt(np.maximum(disc, 0.0))
        tr0 = np.where(flat, 0.0, (-bq - sq) / (2.0 * np.where(flat, 1.0, dd)))
        tr1 = np.where(flat, 1.0, (-bq + sq) / (2.0 * np.where(flat, 1.0, dd)))
    ok = np.where(flat, cq <= 0.0, disc >= 0.0)
    t0, t1 = np.maximum(tr0, 0.0), np.minimum(tr1, 1.0)
    t0, t1, okz = _clip_slabs(a[..., 2], d[..., 2], z_low, z_high, t0, t1, eps)
    return ok & okz & (t0 <= t1 + eps)


def segments_hit_box(a, b, center_xy, half_length, half_width, yaw_rad, z_low, z_high, eps: float = 1e-9) -> np.ndarray:
    """Vectorised ``segment_intersects_box``: ``a``, ``b`` are (..., 3); returns a bool array of shape (...)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c, s = np.cos(yaw_rad), np.sin(yaw_rad)
    ax, ay = a[..., 0] - center_xy[0], a[..., 1] - center_xy[1]
    dx, dy = b[..., 0] - a[..., 0], b[..., 1] - a[..., 1]
    t0, t1 = np.zeros(ax.shape), np.ones(ax.shape)
    ok = np.ones(ax.shape, dtype=bool)
    for p0, d, lo, hi in ((c * ax + s * ay, c * dx + s * dy, -half_length, half_length),
                          (-s * ax + c * ay, -s * dx + c * dy, -half_width, half_width),
                          (a[..., 2], b[..., 2] - a[..., 2], z_low, z_high)):
        t0, t1, o = _clip_slabs(p0, d, lo, hi, t0, t1, eps)
        ok &= o
    return ok & (t0 <= t1 + eps)


def _clip_slabs(p0, d, lo, hi, t0, t1, eps):
    """Vectorised ``_clip_slab``: returns (t0, t1, inside) where ``inside`` is False for a parallel segment outside the slab."""
    par = np.abs(d) < eps
    with np.errstate(divide="ignore", invalid="ignore"):
        dsafe = np.where(par, 1.0, d)
        ta, tb = (lo - p0) / dsafe, (hi - p0) / dsafe
    tmin, tmax = np.minimum(ta, tb), np.maximum(ta, tb)
    inside = ~par | ((p0 >= lo - eps) & (p0 <= hi + eps))
    return np.where(par, t0, np.maximum(t0, tmin)), np.where(par, t1, np.minimum(t1, tmax)), inside
