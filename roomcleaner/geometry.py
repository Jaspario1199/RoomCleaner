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
