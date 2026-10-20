"""Cable geometry, Jacobians and static tension feasibility.

Straight-cable model (taut, negligible sag for light Dyneema):

    L_i = || a_i - (p + R b_i) ||

with ``a_i`` the cable exit point, ``p`` the claw body origin, ``R`` the body
orientation and ``b_i`` the attachment point in body coordinates. For a single
common attachment all ``b_i`` are equal. V1 operation keeps the claw
approximately upright (``R ~ I``); deliberate tilting is out of scope.

Orientation. For spaced attachments (the real claw: four lines tied off at the
inner mouths of the corner holes of the electrical box) the lengths depend on R.
``Geometry.R_at(p)`` supplies it when the caller has no measurement: roll/pitch
from the static equilibrium of the rigid claw (gravity at the claw CoM plus the
four cable tensions, :class:`Attitude`) at a *held yaw* (the last measured one;
yaw is only weakly constrained by the lines and is therefore treated as passive,
measured by vision, never predicted). Callers that hold a measurement (IMU
roll/pitch + vision yaw = the marker pose) pass ``R`` explicitly. A common
attachment point (all b_i equal) is orientation independent and ``R_at`` returns
the identity, reproducing the original point-claw model exactly.

Statics: four cables give 4 tension unknowns for 3 force equations, so the
distribution is indeterminate. Planning uses the *best* feasible distribution
(min-max linear program); a path is accepted only if it exists with margin.
For spaced attachments the 3 moment equations about the CoM fix the two tilt
angles (and, with the held yaw, the tensions) in :class:`Attitude`; the
residual moment about the CoM at the used R is reported by
``tension_distribution`` so a stability check can reject large expected tilt.
See docs/CONTROL_SYSTEM_V1.md 3.1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares, linprog

G = 9.81


def _rot_z(a):
    c, s_ = np.cos(a), np.sin(a)
    return np.array([[c, -s_, 0.0], [s_, c, 0.0], [0.0, 0.0, 1.0]])


def _rpy(roll, pitch, yaw):
    """Z-Y-X (yaw, then pitch, then roll) -> rotation matrix (same as frames.rpy_to_matrix)."""
    cr, sr, cp, sp_, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    return np.array([[cy * cp, cy * sp_ * sr - sy * cr, cy * sp_ * cr + sy * sr],
                     [sy * cp, sy * sp_ * sr + cy * cr, sy * sp_ * cr - cy * sr],
                     [-sp_, cp * sr, cp * cr]])


@dataclass
class AttitudeSolution:
    R: np.ndarray
    roll: float
    pitch: float
    tensions: np.ndarray
    residual: float          # max |wrench residual| (N, N*m) at the solution
    ok: bool                 # Newton converged (residual below tolerance)
    taut: bool               # all tensions >= 0


class Attitude:
    """Static attitude of the rigid claw hung on four lines.

    Unknowns: roll, pitch (yaw is held) and the four tensions; equations: force
    balance ``sum T_i u_i = m (a + g)`` and moment balance about the CoM
    ``sum (R b_i - R c) x T_i u_i = 0`` (6 equations, 6 unknowns, Newton with a
    finite-difference Jacobian, warm started). ``u_i`` points from attachment
    ``i`` toward its anchor. A payload (mass above the claw mass) is taken to
    act at ``payload_body`` (the jaws).
    """

    def __init__(self, geo: "Geometry"):
        self.geo = geo
        self._cache: dict = {}
        self._warm = np.zeros(2)
        self.failures = 0

    def solve(self, p, accel=(0.0, 0.0, 0.0), mass_kg=None, yaw=None) -> AttitudeSolution:
        g = self.geo
        yaw = g.yaw if yaw is None else yaw
        p = np.asarray(p, float)
        acc = np.asarray(accel, float)
        m_claw = g.mass_kg if g.mass_kg else 0.0
        m = m_claw if mass_kg is None else float(mass_kg)
        key = (p.tobytes(), acc.tobytes(), m, yaw)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        c = g.com
        extra = max(m - m_claw, 0.0) if m_claw else 0.0
        if extra > 0 and g.payload_body is not None and m > 0:
            c = (m_claw * g.com + extra * g.payload_body) / m
        w = m * (acc + np.array([0.0, 0.0, G]))
        b, a = g.attach, g.anchors

        def residual(x):
            R = _rpy(x[0], x[1], yaw)
            r = b @ R.T
            d = a - (p + r)
            u = d / np.linalg.norm(d, axis=1, keepdims=True)
            f = x[2:, None] * u
            M = np.cross(r - R @ c, f).sum(0)
            return np.r_[f.sum(0) - w, M]

        x = np.r_[self._warm, np.zeros(4)]
        # initial tensions: least squares of the wrench balance at the starting attitude
        R0 = _rpy(x[0], x[1], yaw)
        r0 = b @ R0.T
        u0 = a - (p + r0)
        u0 /= np.linalg.norm(u0, axis=1, keepdims=True)
        A = np.vstack([u0.T, np.cross(r0 - R0 @ c, u0).T])
        x[2:] = np.linalg.lstsq(A, np.r_[w, np.zeros(3)], rcond=None)[0]
        scale = max(float(np.linalg.norm(w)), 1e-3)
        res = residual(x)
        for _ in range(30):
            if np.max(np.abs(res)) < 1e-10 * scale:
                break
            J = np.empty((6, 6))
            h = 1e-7
            for k in range(6):
                xp = x.copy()
                step = h if k < 2 else h * scale
                xp[k] += step
                J[:, k] = (residual(xp) - res) / step
            try:
                dx = -np.linalg.solve(J, res)
            except np.linalg.LinAlgError:
                break
            dx[:2] = np.clip(dx[:2], -0.2, 0.2)
            t = 1.0
            for _ls in range(10):                      # backtracking on the residual norm
                xn = x + t * dx
                rn = residual(xn)
                if np.linalg.norm(rn) < np.linalg.norm(res):
                    break
                t *= 0.5
            x, res = xn, rn
        err = float(np.max(np.abs(res)))
        ok = err < 1e-7 * scale and abs(x[0]) < 1.0 and abs(x[1]) < 1.0
        if ok:
            self._warm = x[:2].copy()
        else:
            self.failures += 1
        out = AttitudeSolution(_rpy(x[0], x[1], yaw), float(x[0]), float(x[1]), x[2:].copy(), err, bool(ok),
                               bool(np.all(x[2:] >= 0)))
        if len(self._cache) > 20000:
            self._cache.clear()
        self._cache[key] = out
        return out


@dataclass
class Geometry:
    anchors: np.ndarray            # (4,3) cable exit points
    attach: np.ndarray             # (4,3) attachment points in body frame
    com: np.ndarray | None = None  # claw centre of mass in the body frame (default: body origin)
    mass_kg: float | None = None   # claw mass (for the attitude statics)
    payload_body: np.ndarray | None = None   # where a payload acts (jaws), body frame
    yaw: float = 0.0               # held yaw (room frame) used by the attitude predictor

    def __post_init__(self):
        self.anchors = np.asarray(self.anchors, float).reshape(4, 3)
        self.attach = np.asarray(self.attach, float).reshape(4, 3)
        self.com = np.zeros(3) if self.com is None else np.asarray(self.com, float).reshape(3)
        if self.payload_body is not None:
            self.payload_body = np.asarray(self.payload_body, float).reshape(3)
        # spaced attachments make the lengths orientation dependent
        self.spaced = bool(np.max(np.abs(self.attach - self.attach[0])) > 1e-9)
        self._att = Attitude(self) if (self.spaced and self.mass_kg) else None

    # -- orientation ---------------------------------------------------------
    def set_yaw(self, yaw: float):
        self.yaw = float(yaw)

    def R_at(self, p, R=None) -> np.ndarray:
        """Orientation to use at claw position ``p``: the caller's ``R``, else the
        statics prediction at the held yaw (spaced attachments), else identity."""
        if R is not None:
            return np.asarray(R, float)
        if self._att is None:
            return _rot_z(self.yaw) if self.spaced else np.eye(3)
        sol = self._att.solve(p)
        return sol.R if sol.ok else _rot_z(self.yaw)

    def attach_world(self, p, R=None) -> np.ndarray:
        R = self.R_at(p, R)
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
        """Position from four lengths (least squares; orientation ``R`` if given,
        else the statics prediction at each trial position).
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
    Rm = geo.R_at(p, R)
    rw = geo.attach @ Rm.T - Rm @ geo.com            # lever arms about the CoM
    M = np.sum(np.cross(rw, T[:, None] * u), axis=0)
    return TensionResult(bool(T.max() <= t_max + 1e-9), T, float(T.max()), float(np.linalg.norm(M)))


def geometry_from_config(cfg, anchors, yaw: float = 0.0) -> Geometry:
    """Geometry with the claw's attachment points, CoM, mass and payload point from the configuration."""
    low = cfg.claw.lowest_point_body_m
    return Geometry(anchors, cfg.attachment_points(), com=cfg.claw.com_body_m, mass_kg=cfg.claw.mass_kg,
                    payload_body=low, yaw=yaw)


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
