"""Cable geometry, Jacobians and static tension feasibility.

Straight-cable model (taut, negligible sag for light Dyneema):

    L_i = || a_i - (p + R b_i) ||

with ``a_i`` the cable exit point, ``p`` the claw body origin, ``R`` the body
orientation and ``b_i`` the attachment point in body coordinates. For a single
common attachment all ``b_i`` are equal. V1 operation keeps the claw
approximately upright (``R ~ I``); deliberate tilting is out of scope.

Statics: four cables give 4 tension unknowns for 3 force equations, so the
distribution is indeterminate. Planning uses the *best* feasible distribution
(min-max linear program); a path is accepted only if it exists with margin.
For spaced attachments the moment balance is not imposed by the planner (the
claw's tilt adjusts); the residual moment is reported so a stability check can
reject configurations with large expected tilt. This limitation is explicit in
docs/CONTROL_SYSTEM_V1.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares, linprog

G = 9.81


@dataclass
class Geometry:
    anchors: np.ndarray            # (4,3) cable exit points
    attach: np.ndarray             # (4,3) attachment points in body frame

    def __post_init__(self):
        self.anchors = np.asarray(self.anchors, float).reshape(4, 3)
        self.attach = np.asarray(self.attach, float).reshape(4, 3)

    def attach_world(self, p, R=None) -> np.ndarray:
        R = np.eye(3) if R is None else R
        return np.asarray(p, float) + self.attach @ R.T

    def lengths(self, p, R=None) -> np.ndarray:
        return np.linalg.norm(self.anchors - self.attach_world(p, R), axis=1)

    def unit_vectors(self, p, R=None) -> np.ndarray:
        """Unit vectors from each attachment toward its anchor (tension direction)."""
        d = self.anchors - self.attach_world(p, R)
        return d / np.linalg.norm(d, axis=1, keepdims=True)

    def jacobian(self, p, R=None) -> np.ndarray:
        """dL/dp (4x3) at fixed orientation: dL_i = -u_i . dp."""
        return -self.unit_vectors(p, R)

    def length_rates(self, p, v, R=None) -> np.ndarray:
        return self.jacobian(p, R) @ np.asarray(v, float)

    def forward(self, L, p0=None, R=None) -> tuple[np.ndarray, float]:
        """Position from four lengths (least squares, fixed orientation).
        Returns (p, rms residual)."""
        L = np.asarray(L, float)
        p0 = np.mean(self.anchors, axis=0) - [0, 0, 1.0] if p0 is None else np.asarray(p0, float)
        res = least_squares(lambda p: self.lengths(p, R) - L, p0, method="lm")
        return res.x, float(np.sqrt(np.mean(res.fun ** 2)))


@dataclass
class TensionResult:
    feasible: bool
    tensions: np.ndarray
    max_tension: float
    moment_residual: float


def tension_distribution(geo: Geometry, p, mass_kg: float, *, t_min: float, t_max: float,
                         R=None, accel=(0, 0, 0)) -> TensionResult:
    """Min-max tension distribution supporting weight (+ optional acceleration).

    Solves  min t  s.t.  sum T_i u_i = m (a - g),  t_min <= T_i <= t.
    """
    u = geo.unit_vectors(p, R)
    w = mass_kg * (np.asarray(accel, float) + [0, 0, G])     # force the cables must supply
    c = np.r_[np.zeros(4), 1.0]
    A_eq = np.hstack([u.T, np.zeros((3, 1))])
    A_ub = np.hstack([np.eye(4), -np.ones((4, 1))])
    res = linprog(c, A_ub=A_ub, b_ub=np.zeros(4), A_eq=A_eq, b_eq=w,
                  bounds=[(t_min, None)] * 4 + [(0, None)], method="highs")
    if res.status != 0:
        return TensionResult(False, np.full(4, np.nan), np.inf, np.nan)
    T = res.x[:4]
    rw = geo.attach_world(p, R) - np.asarray(p, float)
    M = np.sum(np.cross(rw, T[:, None] * u), axis=0)
    return TensionResult(bool(T.max() <= t_max + 1e-9), T, float(T.max()), float(np.linalg.norm(M)))


@dataclass
class Workspace:
    """Allowed claw-origin region (room frame) plus cable-length bounds."""
    lo: np.ndarray
    hi: np.ndarray
    min_lengths: np.ndarray          # per cable (bead minimum + margin), 0 if none
    obstacles: list

    def violations(self, geo: Geometry, p, R=None, *, allow_low: bool = False) -> list[str]:
        p = np.asarray(p, float)
        out = []
        lo = self.lo.copy()
        if allow_low:
            lo[2] = -np.inf
        for k, ax in enumerate("xyz"):
            if p[k] < lo[k] - 1e-9:
                out.append(f"{ax}={p[k]:.3f} below {lo[k]:.3f}")
            if p[k] > self.hi[k] + 1e-9:
                out.append(f"{ax}={p[k]:.3f} above {self.hi[k]:.3f}")
        L = geo.lengths(p, R)
        for i, (Li, m) in enumerate(zip(L, self.min_lengths)):
            if Li < m - 1e-9:
                out.append(f"cable {'ABCD'[i]} {Li:.3f} m shorter than minimum {m:.3f} m")
        pts = geo.attach_world(p, R)
        for ob in self.obstacles:
            for i in range(4):
                if _segment_hits_cylinder(geo.anchors[i], pts[i], ob):
                    out.append(f"cable {'ABCD'[i]} crosses obstacle {ob.get('name', '')}")
        return out


def _segment_hits_cylinder(a, b, ob, n=24) -> bool:
    for s in np.linspace(0, 1, n):
        q = a + s * (b - a)
        if ob["z_low"] <= q[2] <= ob["z_high"] and np.hypot(q[0] - ob["x"], q[1] - ob["y"]) <= ob["r"]:
            return True
    return False


def workspace_from_config(cfg, anchors_room: np.ndarray, *, lowest_point_z: float = 0.0) -> Workspace:
    """Workspace for the claw body origin in the room frame.

    ``lowest_point_z`` is the body-frame z of the lowest claw point (negative),
    so the origin must stay ``-lowest_point_z`` above the floor.
    """
    m = cfg.motion.workspace_margin_m
    W, D, H = cfg.room_m
    top = float(np.min(anchors_room[:, 2])) - cfg.motion.ceiling_margin_m
    lo = np.array([m, m, -lowest_point_z])
    hi = np.array([W - m, D - m, top])
    mins = []
    for s in cfg.stations:
        if s.bead.present and s.bead.trigger_length_m is not None:
            mins.append(s.bead.trigger_length_m + s.bead.min_length_margin_m)
        else:
            mins.append(0.0)
    return Workspace(lo, hi, np.array(mins), list(cfg.obstacles))
