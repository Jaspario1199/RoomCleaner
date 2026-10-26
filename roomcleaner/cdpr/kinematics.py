"""Cable geometry, Jacobians and static tension feasibility.

Straight-cable model (taut, negligible sag for light Dyneema):

    L_i = || a_i - (p + R b_i) ||

with ``a_i`` the cable exit point, ``p`` the claw body origin, ``R`` the body
orientation and ``b_i`` the attachment point in body coordinates. For a single
common attachment all ``b_i`` are equal. V1 operation keeps the claw
approximately upright (``R ~ I``); deliberate tilting is out of scope.

Orientation. For spaced attachments (the real claw: four lines tied off at the
inner mouths of the corner holes of the electrical box) the lengths depend on R.
``Geometry.R_at(p)`` supplies it when the caller has no measurement: the nominal
roll/pitch from the static equilibrium of the rigid claw (gravity at the claw CoM
plus the four cable tensions, :class:`Attitude`) at a *held yaw* (the last
measured one; yaw is only weakly constrained by the lines and is therefore
treated as passive, measured by vision, never predicted). Callers that hold a measurement (the full
vision attitude = the marker pose; D27: no IMU) pass ``R`` explicitly. A common
attachment point (all b_i equal) is orientation independent and ``R_at`` returns
the identity, reproducing the original point-claw model exactly.

Statics: four cables give 4 tension unknowns for 3 force equations, so the
distribution is indeterminate. Planning uses the *best* feasible distribution
(min-max linear program); a path is accepted only if it exists with margin.
For spaced attachments the moment balance about the CoM fixes the two tilt
angles in :class:`Attitude`; the residual moment about the CoM at the R used is
reported by ``tension_distribution`` so a stability check can reject large
expected tilt.
See docs/CONTROL_SYSTEM_V1.md 3.1.

Three-station mode (docs/THREE_STATION_MODE_SPEC.md). Everything here works over however many cables the geometry has
(3 or 4; ``anchors`` / ``attach`` are (n, 3)). With THREE cables and a point load the tensions are the unique solution
of a 3 x 3 system (no distribution to choose): ``tension_distribution`` solves it directly and the pose is feasible
only if every ``T_i >= t_min`` (and ``max <= t_max``). For a claw weight W at floor position p inside the triangle of the
anchors' floor projection, with barycentric coordinates lambda_i(p) (anchors at one height H, claw z below it):

    T_i = lambda_i(p) * W * L_i / (H - z),        L_i >= H - z   =>   T_i >= lambda_i * W

so ``lambda_i >= T_floor / W`` is sufficient for ``T_i >= T_floor`` at ANY height: :class:`Workspace` keeps the claw's floor
projection where every lambda_i >= ``lam_min`` = T_floor / (m g) (the edge margin, a fraction of the triangle's altitude:
distance to edge i = lambda_i * altitude_i). A point outside the triangle has a negative lambda: infeasible. The attitude
model (:class:`Attitude`) with three cables has 3 force + 2 moment equations for 3 tensions + roll + pitch (yaw held, as
before) and agrees with the rigid-body simulator's equilibrium to 0.01 deg when evaluated at its yaw; the vertical-axis
moment left at a held yaw (``yaw_moment``, 0.05-0.1 N m) is what turns the claw to its equilibrium yaw (+11 to +25 deg in
the simulator), and a three-cable claw has about a third of the four-cable yaw stiffness (verification/three_station_mode_results.md).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares, linprog

from ..geometry import (segment_intersects_box, segment_intersects_cylinder, segments_hit_box, segments_hit_cylinder,
                        xy_distance_to_box)

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
    roll: float              # tilt about world x / y (rad) relative to the held-yaw upright pose
    pitch: float
    tensions: np.ndarray     # min-norm distribution that balances the weight at this attitude
    residual: float          # max |force residual| (N) and |horizontal moment about the CoM| (N m)
    yaw_moment: float        # unbalanced moment about the vertical axis (N m): what the passive yaw would answer to
    ok: bool                 # iteration converged and the tilt is small
    taut: bool               # all tensions >= 0


class Attitude:
    """Nominal static attitude (roll/pitch) of the rigid claw hung on four lines, at a HELD yaw.

    The claw is a rigid body loaded by gravity at its CoM (``Geometry.com``; a payload acts at the jaws) and four
    line tensions ``T_i u_i`` acting at the attachment points ``R b_i`` (``u_i`` from attachment toward its anchor).
    Force balance ``sum T_i u_i = m (a + g)`` leaves a one-parameter family of tension sets (4 unknowns, 3 equations,
    the self-stress mode is the internal pretension); the minimum 2-norm set (no pretension; NOT the least-total-tension LP
    solution, and it can be slightly negative at some poses) is used. The two horizontal moment equations about the CoM then fix roll and pitch (Newton on the
    2x2 system, a handful of iterations).

    Yaw is NOT predicted: it is only weakly held by the lines (3.6 to 6 deg per mm of line-length inconsistency,
    verification/claw_camera_bay_verification.md F6) and the same mm-level inconsistencies also move the tilt, so
    this is a nominal value; the measured attitude (vision roll/pitch/yaw) replaces it wherever a measurement
    exists. The unbalanced vertical-axis moment is reported (``yaw_moment``).
    """

    def __init__(self, geo: "Geometry"):
        self.geo = geo
        self._cache: dict = {}
        self.failures = 0

    def _state(self, w, yaw, p, c, wrench):
        g = self.geo
        R = _tilt(w) @ _rot_z(yaw)
        r = g.attach @ R.T
        d = g.anchors - (p + r)
        u = d / np.linalg.norm(d, axis=1, keepdims=True)
        T = np.linalg.lstsq(u.T, wrench, rcond=None)[0]                 # minimum-norm solution of sum T_i u_i = w
        M = np.cross(r - R @ c, T[:, None] * u).sum(0)
        return R, u, T, M

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
            c = (m_claw * g.com + extra * g.payload_body) / m           # payload at the jaws
        wrench = m * (acc + np.array([0.0, 0.0, G]))
        w = np.zeros(2)                                                # tilt about world x, y
        ok = False
        for _ in range(15):
            R, u, T, M = self._state(w, yaw, p, c, wrench)
            if np.max(np.abs(M[:2])) < 1e-10:
                ok = True
                break
            J = np.empty((2, 2))
            for k in range(2):
                wk = w.copy()
                wk[k] += 1e-6
                J[:, k] = (self._state(wk, yaw, p, c, wrench)[3][:2] - M[:2]) / 1e-6
            try:
                dw = -np.linalg.solve(J, M[:2])
            except np.linalg.LinAlgError:
                break
            w = w + np.clip(dw, -0.2, 0.2)
        else:
            R, u, T, M = self._state(w, yaw, p, c, wrench)
            ok = bool(np.max(np.abs(M[:2])) < 1e-7)
        ok = bool(ok and np.max(np.abs(w)) < 0.5)
        if not ok:
            self.failures += 1
        F = float(np.max(np.abs((T[:, None] * u).sum(0) - wrench)))
        out = AttitudeSolution(R, float(w[0]), float(w[1]), T, max(F, float(np.max(np.abs(M[:2])))), float(M[2]),
                               ok, bool(np.all(T >= 0)))
        if len(self._cache) > 20000:
            self._cache.clear()
        self._cache[key] = out
        return out


def _tilt(w):
    """Rotation by the small world-frame rotation vector (wx, wy, 0)."""
    th = float(np.hypot(w[0], w[1]))
    if th < 1e-12:
        return np.eye(3)
    k = np.array([w[0], w[1], 0.0]) / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


@dataclass
class Geometry:
    anchors: np.ndarray            # (n,3) cable exit points (n = 4, or 3 in three-station mode)
    attach: np.ndarray             # (n,3) attachment points in body frame
    com: np.ndarray | None = None  # claw centre of mass in the body frame (default: body origin)
    mass_kg: float | None = None   # claw mass (for the attitude statics)
    payload_body: np.ndarray | None = None   # where a payload acts (jaws), body frame
    yaw: float = 0.0               # held yaw (room frame) used by the attitude predictor

    def __post_init__(self):
        self.anchors = np.asarray(self.anchors, float).reshape(-1, 3)
        self.attach = np.asarray(self.attach, float).reshape(-1, 3)
        if self.anchors.shape != self.attach.shape or self.anchors.shape[0] not in (3, 4):
            raise ValueError(f"Geometry needs 3 or 4 cables with one attachment point each, got anchors {self.anchors.shape} "
                             f"and attachment points {self.attach.shape}")
        self.n = self.anchors.shape[0]
        self.com = np.zeros(3) if self.com is None else np.asarray(self.com, float).reshape(3)
        if self.payload_body is not None:
            self.payload_body = np.asarray(self.payload_body, float).reshape(3)
        # spaced attachments make the lengths orientation dependent
        self.spaced = bool(np.max(np.abs(self.attach - self.attach[0])) > 1e-9)
        self._att = Attitude(self) if (self.spaced and self.mass_kg) else None
        self._ref = None

    # -- orientation ---------------------------------------------------------
    def set_yaw(self, yaw: float):
        self.yaw = float(yaw)

    def set_reference(self, p, R):
        """Anchor the attitude prediction to a MEASURED pose: ``R_at(p)`` then returns exactly ``R`` there and the
        statics-predicted change elsewhere (a constant world-frame tilt offset carries the part of the real tilt
        that statics cannot know, e.g. from mm-level line-length inconsistencies). Sets the held yaw from ``R``."""
        R = np.asarray(R, float)
        self.yaw = float(np.arctan2(R[1, 0], R[0, 0]))
        self._ref = None
        if self._att is not None:
            nominal = self.R_at(np.asarray(p, float))
            self._ref = R @ nominal.T

    def R_at(self, p, R=None) -> np.ndarray:
        """Orientation to use at claw position ``p``: the caller's ``R``, else the statics prediction at the held
        yaw (spaced attachments, anchored to the last measured pose, see :meth:`set_reference`), else identity."""
        if R is not None:
            return np.asarray(R, float)
        if self._att is None:
            return _rot_z(self.yaw) if self.spaced else np.eye(3)
        sol = self._att.solve(p)
        nominal = sol.R if sol.ok else _rot_z(self.yaw)
        return nominal if self._ref is None else self._ref @ nominal

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
    """Tension distribution supporting weight (+ optional acceleration).

    Four cables: min-max over the self-stress family,  min t  s.t.  sum T_i u_i = m (a - g),  t_min <= T_i <= t.
    Three cables: the unique solution of the 3 x 3 system sum T_i u_i = m (a + g); feasible only if every
    ``T_i >= t_min`` (and the largest <= ``t_max``). There is no distribution to choose, so a pose outside the anchors'
    triangle (a negative tension) or too close to its edge (below the floor) is infeasible.
    """
    u = geo.unit_vectors(p, R)
    w = mass_kg * (np.asarray(accel, float) + [0, 0, G])     # force the cables must supply
    n = geo.n
    if n == 3:
        try:
            T = np.linalg.solve(u.T, w)
        except np.linalg.LinAlgError:
            return TensionResult(False, np.full(3, np.nan), np.inf, np.nan)
        ok = bool(np.all(T >= t_min - 1e-9))
        Rm = geo.R_at(p, R)
        rw = geo.attach @ Rm.T - Rm @ geo.com
        M = np.sum(np.cross(rw, T[:, None] * u), axis=0)
        if not ok:
            return TensionResult(False, T, float(T.max()), float(np.linalg.norm(M)))
        return TensionResult(bool(T.max() <= t_max + 1e-9), T, float(T.max()), float(np.linalg.norm(M)))
    c = np.r_[np.zeros(n), 1.0]
    A_eq = np.hstack([u.T, np.zeros((3, 1))])
    A_ub = np.hstack([np.eye(n), -np.ones((n, 1))])
    res = linprog(c, A_ub=A_ub, b_ub=np.zeros(n), A_eq=A_eq, b_eq=w,
                  bounds=[(t_min, None)] * n + [(0, None)], method="highs")
    if res.status != 0:
        return TensionResult(False, np.full(n, np.nan), np.inf, np.nan)
    T = res.x[:n]
    Rm = geo.R_at(p, R)
    rw = geo.attach @ Rm.T - Rm @ geo.com            # lever arms about the CoM
    M = np.sum(np.cross(rw, T[:, None] * u), axis=0)
    return TensionResult(bool(T.max() <= t_max + 1e-9), T, float(T.max()), float(np.linalg.norm(M)))


def barycentric_xy(tri_xy, xy) -> np.ndarray:
    """Barycentric coordinates (3,) of the floor point ``xy`` in the triangle ``tri_xy`` ((3, 2)); all >= 0 inside it."""
    P = np.asarray(tri_xy, float).reshape(3, 2)
    d = np.asarray(xy, float)[:2] - P[2]
    T = np.array([[P[0, 0] - P[2, 0], P[1, 0] - P[2, 0]], [P[0, 1] - P[2, 1], P[1, 1] - P[2, 1]]])
    l01 = np.linalg.solve(T, d)
    return np.array([l01[0], l01[1], 1.0 - l01.sum()])


def geometry_from_config(cfg, anchors, yaw: float = 0.0) -> Geometry:
    """Geometry with the claw's attachment points, CoM, mass and payload point from the configuration."""
    low = cfg.claw.lowest_point_body_m
    return Geometry(anchors, cfg.attachment_points(), com=cfg.claw.com_body_m, mass_kg=cfg.claw.mass_kg,
                    payload_body=low, yaw=yaw)


@dataclass
class Workspace:
    """Allowed claw-origin region (room frame) plus cable-length bounds.

    Three-station mode adds the triangle of the active anchors' floor projection (``tri_xy``, (3, 2)): the claw's floor
    projection must keep every barycentric coordinate >= ``lam_min`` (= T_floor / (m g): the edge margin derived from the
    tension floor, see the module docstring); ``lam_min`` = 0 means "inside the triangle" only. ``None`` = four cables, no
    triangle (the box and the tension check are the whole region, exactly as before).

    Room map (docs/ROOM_MAP_SPEC.md 3): ``obstacles`` are the canonical keep-out shapes of ``config.parse_obstacles``. Each is
    inflated by ``obstacle_margin_m`` (sideways and in height; a box keeps square corners, which is conservative) and tested
    EXACTLY against every cable segment (anchor to attachment point: ``roomcleaner.geometry``) and against the claw body, the
    vertical segment from its lowest point (``claw_low_z``, body frame) to its attachment plane widened by ``claw_radius_m``.
    No obstacles: nothing below runs, the region is exactly as before."""
    lo: np.ndarray
    hi: np.ndarray
    min_lengths: np.ndarray          # per cable (bead minimum + margin), 0 if none
    obstacles: list
    ids: tuple = ("A", "B", "C", "D")
    tri_xy: np.ndarray | None = None
    lam_min: float = 0.0
    obstacle_margin_m: float = 0.0
    claw_low_z: float = 0.0          # body-frame z of the claw's lowest point (<= 0)
    claw_radius_m: float = 0.0

    def triangle_violation(self, p) -> str | None:
        """None if the floor projection of ``p`` is inside the (margin-shrunk) triangle, else why not (three cables only)."""
        if self.tri_xy is None:
            return None
        lam = barycentric_xy(self.tri_xy, p)
        if lam.min() >= self.lam_min - 1e-9:
            return None
        j = int(np.argmin(lam))
        alt = _altitude(self.tri_xy, j)
        dist = lam[j] * alt                                  # signed distance inside edge j (opposite vertex j), m
        need = self.lam_min * alt
        side = "outside" if lam[j] < 0 else "inside"
        return (f"floor point ({p[0]:.3f}, {p[1]:.3f}) is {abs(dist):.3f} m {side} the edge opposite station {self.ids[j]} "
                f"of the {'/'.join(self.ids)} triangle; it must be at least {need:.3f} m inside (cable {self.ids[j]} would "
                f"carry under {self.lam_min * 100:.0f} % of the weight)")

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
        tv = self.triangle_violation(p)
        if tv:
            out.append(tv)
        L = geo.lengths(p, R)
        for i, (Li, m) in enumerate(zip(L, self.min_lengths)):
            if Li < m - 1e-9:
                out.append(f"cable {self.ids[i]} {Li:.3f} m shorter than minimum {m:.3f} m")
        out += self.obstacle_violations(geo, p, R)
        return out

    def obstacle_violations(self, geo: Geometry, p, R=None) -> list[str]:
        """Why the cables or the claw body at ``p`` meet a keep-out shape (inflated by the margin); [] if they do not."""
        if not self.obstacles:
            return []
        p = np.asarray(p, float)
        pts = geo.attach_world(p, R)
        z_top = max(float(np.max(pts[:, 2])), float(p[2]))
        z_bot = min(float(p[2]) + self.claw_low_z, z_top)
        out = []
        for ob in self.obstacles:
            name = obstacle_label(ob)
            for i in range(len(pts)):
                if segment_hits_obstacle(geo.anchors[i], pts[i], ob, self.obstacle_margin_m):
                    out.append(f"cable {self.ids[i]} would cross {name}")
            if claw_hits_obstacle(p[:2], z_bot, z_top, ob, self.obstacle_margin_m, self.claw_radius_m):
                out.append(f"the claw would enter {name}")
        return out


def _altitude(tri_xy, j) -> float:
    """Altitude (m) of vertex j of the triangle over its opposite side."""
    P = np.asarray(tri_xy, float).reshape(3, 2)
    a, b = P[(j + 1) % 3], P[(j + 2) % 3]
    side = b - a
    d = P[j] - a
    return float(abs(side[0] * d[1] - side[1] * d[0]) / np.linalg.norm(side))


# ------------------------------------------------------------------------------------------------- room map shapes
def obstacle_label(ob) -> str:
    """How a shape is named in a refusal: "the Shelf", or "shape o3" when it has no name."""
    return f"the {ob['name']}" if ob.get("name") else f"shape {ob.get('id', '?')}"


def segment_hits_obstacle(a, b, ob, margin=0.0) -> bool:
    """Exact: does the segment a -> b pass through the shape ``ob`` (canonical, config.parse_obstacles) inflated by ``margin``?"""
    zl, zh = ob["z_low_m"] - margin, ob["height_m"] + margin
    if ob["shape"] == "cylinder":
        return segment_intersects_cylinder(a, b, (ob["x"], ob["y"]), ob["diameter_m"] / 2 + margin, zl, zh)
    return segment_intersects_box(a, b, (ob["x"], ob["y"]), ob["length_m"] / 2 + margin, ob["width_m"] / 2 + margin,
                                  np.radians(ob["yaw_deg"]), zl, zh)


def segments_hit_obstacle(a, b, ob, margin=0.0) -> np.ndarray:
    """Vectorised ``segment_hits_obstacle`` over segments a, b of shape (..., 3)."""
    zl, zh = ob["z_low_m"] - margin, ob["height_m"] + margin
    if ob["shape"] == "cylinder":
        return segments_hit_cylinder(a, b, (ob["x"], ob["y"]), ob["diameter_m"] / 2 + margin, zl, zh)
    return segments_hit_box(a, b, (ob["x"], ob["y"]), ob["length_m"] / 2 + margin, ob["width_m"] / 2 + margin,
                            np.radians(ob["yaw_deg"]), zl, zh)


def obstacle_xy_distance(xy, ob, margin=0.0) -> np.ndarray:
    """Floor distance (m) from the point(s) xy (..., 2) to the footprint of ``ob`` inflated by ``margin``; 0 inside it."""
    xy = np.asarray(xy, float)
    if ob["shape"] == "cylinder":
        return np.maximum(np.hypot(xy[..., 0] - ob["x"], xy[..., 1] - ob["y"]) - ob["diameter_m"] / 2 - margin, 0.0)
    return xy_distance_to_box(xy, (ob["x"], ob["y"]), ob["length_m"] / 2 + margin, ob["width_m"] / 2 + margin,
                              np.radians(ob["yaw_deg"]))


def claw_hits_obstacle(xy, z_bot, z_top, ob, margin=0.0, radius=0.0):
    """Does the claw body (vertical axis at ``xy`` from ``z_bot`` to ``z_top``, widened by ``radius``) enter ``ob`` inflated
    by ``margin``? Vectorised over xy (..., 2) and z_bot / z_top (broadcast)."""
    over = (np.asarray(z_bot) <= ob["height_m"] + margin) & (np.asarray(z_top) >= ob["z_low_m"] - margin)
    hit = over & (obstacle_xy_distance(xy, ob, margin) <= radius + 1e-9)
    return bool(hit) if np.ndim(hit) == 0 else hit


def workspace_from_config(cfg, anchors_room: np.ndarray, *, lowest_point_z: float = 0.0) -> Workspace:
    """Workspace for the claw body origin in the room frame.

    ``lowest_point_z`` is the body-frame z of the lowest claw point (negative),
    so the origin must stay ``-lowest_point_z`` above the floor.

    Three active stations: the triangle of their anchors (floor projection, ``anchors_room``) with the tension-floor edge
    margin ``lam_min`` = ``cfg.tension_floor_fraction()`` (0 if the claw mass is not set yet) is part of the region.
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
    tri, lam = None, 0.0
    if len(cfg.stations) == 3:
        tri = np.asarray(anchors_room, float)[:, :2].copy()
        lam = cfg.tension_floor_fraction() or 0.0
    return Workspace(lo, hi, np.array(mins), list(cfg.obstacles), tuple(cfg.ids), tri, float(lam),
                     obstacle_margin_m=float(cfg.motion.obstacle_margin_m), claw_low_z=min(float(lowest_point_z), 0.0),
                     claw_radius_m=float(cfg.claw.body_radius_m))


def coverage(ws: Workspace, anchors, attach, shapes, heights, room_xy, *, yaw: float = 0.0, trusted=None,
             trust_text: str = "outside the trusted (calibrated) volume", cell_m: float = 0.1) -> dict:
    """The app's "Where can it pick?" grid (docs/ROOM_MAP_SPEC.md 3.5): per ``cell_m`` floor cell, the first reason a grip
    there is impossible, or 0 = reachable.

    A grip at a cell is the claw origin at every height in ``heights`` (the grip and approach heights; heights in between are
    added every 0.1 m so the descent is covered) above the cell centre, upright at the held ``yaw``. Reasons, in this order:
    a cable (``anchors`` to the attachment points ``attach``, body frame) or the claw body (its vertical span over the whole
    descent, widened by ``ws.claw_radius_m``) meets one of ``shapes`` (the DRAFT map, inflated by ``ws.obstacle_margin_m``;
    the first shape in map order and its first cable); outside the usable area (the workspace box in xy, and in three-station
    mode the margin-shrunk triangle); outside the trusted volume (``trusted``: a function (N, 2) -> bool, None = all).

    Pure numpy over all cells at once (no LP, no lock): ~10 ms for 10 shapes on a 3.4 x 2.7 m room. Returns
    ``{cell_m, nx, ny, x0, y0, cells, reasons, counts}``: ``cells`` is row-major (y rows, then x), each an index into
    ``reasons`` (``reasons[0]`` = reachable)."""
    W, D = float(room_xy[0]), float(room_xy[1])
    nx, ny = max(1, int(np.ceil(W / cell_m - 1e-9))), max(1, int(np.ceil(D / cell_m - 1e-9)))
    gx, gy = np.meshgrid((np.arange(nx) + 0.5) * cell_m, (np.arange(ny) + 0.5) * cell_m)
    xy = np.stack([gx.ravel(), gy.ravel()], axis=1)                                     # (N, 2), row-major in y
    n = len(xy)
    hs = np.asarray(sorted(set(float(h) for h in heights)), float)
    if len(hs) > 1:
        hs = np.unique(np.r_[hs, np.arange(hs[0], hs[-1], 0.1)])
    A = np.asarray(anchors, float).reshape(-1, 3)
    b = np.asarray(attach, float).reshape(-1, 3) @ _rot_z(yaw).T                         # attachment offsets (upright, held yaw)
    ids = ws.ids
    reasons = [{"kind": "ok", "text": "reachable for a grip"}]
    index: dict = {}
    code = np.zeros(n, int)

    def mark(mask, kind, text, **extra):
        mask = mask & (code == 0)
        if not np.any(mask):
            return
        if text not in index:
            index[text] = len(reasons)
            reasons.append({"kind": kind, "text": text, **extra})
        code[mask] = index[text]

    m = ws.obstacle_margin_m
    top_off = float(np.max(b[:, 2]))
    z_bot, z_top = hs[0] + ws.claw_low_z, hs[-1] + max(top_off, 0.0)
    P = np.empty((n, len(hs), 3))
    P[:, :, :2], P[:, :, 2] = xy[:, None, :], hs[None, :]
    for ob in shapes:
        name = obstacle_label(ob)
        for i in range(len(A)):
            hit = segments_hit_obstacle(np.broadcast_to(A[i], P.shape), P + b[i], ob, m).any(axis=1)
            mark(hit, "shape", f"cable {ids[i]} would cross {name}", shape=ob.get("id"), cable=ids[i])
        mark(claw_hits_obstacle(xy, z_bot, z_top, ob, m, ws.claw_radius_m), "shape", f"the claw would enter {name}",
             shape=ob.get("id"))
    out_box = np.any(xy < ws.lo[:2] - 1e-9, axis=1) | np.any(xy > ws.hi[:2] + 1e-9, axis=1)
    mark(out_box, "area", f"outside the usable area (closer than {ws.lo[0]:.2f} m to a wall)")
    if ws.tri_xy is not None:
        P3 = np.asarray(ws.tri_xy, float)
        T = np.array([[P3[0, 0] - P3[2, 0], P3[1, 0] - P3[2, 0]], [P3[0, 1] - P3[2, 1], P3[1, 1] - P3[2, 1]]])
        l01 = np.linalg.solve(T, (xy - P3[2]).T).T
        lam = np.c_[l01, 1.0 - l01.sum(axis=1)]
        mark(lam.min(axis=1) < ws.lam_min - 1e-9, "area",
             f"outside the usable area (too close to an edge of the {'/'.join(ids)} triangle)")
    if trusted is not None:
        mark(~np.asarray(trusted(xy), bool), "trust", trust_text)
    kinds = np.array([r["kind"] for r in reasons])[code]
    counts = {k: int(np.sum(kinds == k)) for k in ("ok", "shape", "area", "trust")}
    return {"cell_m": cell_m, "nx": nx, "ny": ny, "x0": 0.0, "y0": 0.0, "cells": code.tolist(), "reasons": reasons,
            "counts": counts}
