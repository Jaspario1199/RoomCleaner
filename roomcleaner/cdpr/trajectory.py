"""Motion planning: Cartesian or cable-space moves -> per-station segment streams.

The planner never sends "pull one cable, release the opposite one by the same
amount" or "pay out every cable equally". Every Cartesian move is converted
through the current geometric model into four cable-length histories, and
those into four motor-position histories via each station's spool map. All
stations share one timeline (same knot times), so a feed-hold in path time
keeps the geometry consistent.

Profiles are time-optimal trapezoids in path length, scaled down until the
worst cable speed/acceleration along the path is within limits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .kinematics import Geometry, Workspace, tension_distribution
from .spool import CableMap


@dataclass
class RobotModel:
    """Current best geometric model in the working (room) frame."""
    geometry: Geometry
    maps: dict          # sid -> CableMap (with L0 for the current boot epoch)
    ids: tuple = ("A", "B", "C", "D")

    def lengths(self, p, R=None):
        return self.geometry.lengths(p, R)

    def positions_for(self, p, R=None) -> np.ndarray:
        L = self.lengths(p, R)
        return np.array([self.maps[s].position(Li) for s, Li in zip(self.ids, L)])

    def lengths_from_positions(self, P) -> np.ndarray:
        return np.array([self.maps[s].length(Pi) for s, Pi in zip(self.ids, P)])

    def pose_from_positions(self, P, p0=None, R=None):
        return self.geometry.forward(self.lengths_from_positions(P), p0, R)


@dataclass
class Plan:
    """A synchronized motion: knot times shared by all stations."""
    times: np.ndarray                       # (K,) seconds from motion start
    pos: np.ndarray                         # (K, 4) microsteps
    vel: np.ndarray                         # (K, 4) microsteps / s
    ref: np.ndarray                         # (K-1, 4) segment ref flag per station
    cart: np.ndarray | None = None          # (K, 3) planned claw positions (if Cartesian)
    label: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return float(self.times[-1])

    @property
    def start(self) -> np.ndarray:
        return self.pos[0]

    @property
    def end(self) -> np.ndarray:
        return self.pos[-1]

    def position_at(self, tau_s: float) -> np.ndarray:
        """Planned microstep positions of all stations at path time tau (s)."""
        from .station_core import hermite
        tau = min(max(tau_s, 0.0), self.duration)
        k = int(min(np.searchsorted(self.times, tau, side="right") - 1, len(self.times) - 2))
        d = self.times[k + 1] - self.times[k]
        u = (tau - self.times[k]) / d
        return np.array([hermite(self.pos[k, j], self.pos[k + 1, j], self.vel[k, j], self.vel[k + 1, j], d, u)[0]
                         for j in range(self.pos.shape[1])])

    def segments(self, j: int, t0_local: int) -> list[dict]:
        """Segment messages for station column j, starting at local time t0."""
        out, t = [], t0_local
        K = len(self.times)
        for k in range(K - 1):
            d = int(round((self.times[k + 1] - self.times[k]) * 1e6))
            out.append({"t": "seg", "i": k, "t0": t, "d": d,
                        "p0": round(float(self.pos[k, j]), 4), "p1": round(float(self.pos[k + 1, j]), 4),
                        "v0": round(float(self.vel[k, j]), 4), "v1": round(float(self.vel[k + 1, j]), 4),
                        "last": k == K - 2, "ref": int(self.ref[k, j])})
            t += d
        # make the rounded values continuous
        for a, b in zip(out, out[1:]):
            b["p0"], b["v0"] = a["p1"], a["v1"]
        return out


def trapezoid(dist: float, vmax: float, amax: float):
    """Return (T, s(t), sdot(t)) for a rest-to-rest trapezoid over ``dist``."""
    if dist <= 0:
        return 0.0, (lambda t: 0.0), (lambda t: 0.0)
    ta = vmax / amax
    if amax * ta * ta >= dist:              # triangular
        ta = math.sqrt(dist / amax)
        vpk = amax * ta
        tc = 0.0
    else:
        vpk = vmax
        tc = (dist - amax * ta * ta) / vmax
    T = 2 * ta + tc

    def s(t):
        t = min(max(t, 0.0), T)
        if t < ta:
            return 0.5 * amax * t * t
        if t < ta + tc:
            return 0.5 * amax * ta * ta + vpk * (t - ta)
        r = T - t
        return dist - 0.5 * amax * r * r

    def sd(t):
        t = min(max(t, 0.0), T)
        if t < ta:
            return amax * t
        if t < ta + tc:
            return vpk
        return amax * (T - t)
    return T, s, sd


class PlanError(ValueError):
    pass


@dataclass
class Limits:
    cart_v: float
    cart_a: float
    cable_v: float
    cable_a: float
    segment_s: float = 0.1
    t_min: float = 0.5
    t_max: float = math.inf
    mass_kg: float | None = None


def plan_line(model: RobotModel, p_from, p_to, lim: Limits, *, R=None, ws: Workspace | None = None,
              allow_low: bool = False, ref=None, label="line", check_tension=True) -> Plan:
    p_from, p_to = np.asarray(p_from, float), np.asarray(p_to, float)
    delta = p_to - p_from
    dist = float(np.linalg.norm(delta))
    if dist < 1e-6:
        raise PlanError("zero-length move")
    direction = delta / dist
    # worst cable-rate factor along the path: |dL/ds| = |u . dir|
    probe = [p_from + direction * dist * f for f in np.linspace(0, 1, 21)]
    kmax = max(float(np.max(np.abs(model.geometry.unit_vectors(q, R) @ direction))) for q in probe)
    v = min(lim.cart_v, lim.cable_v / max(kmax, 1e-6))
    a = min(lim.cart_a, lim.cable_a / max(kmax, 1e-6))
    T, s, sd = trapezoid(dist, v, a)
    n = max(2, int(math.ceil(T / lim.segment_s)))
    times = np.linspace(0, T, n + 1)
    cart = np.array([p_from + direction * s(t) for t in times])
    _check_path(model, cart, ws, lim, R, allow_low, check_tension)
    pos = np.array([model.positions_for(q, R) for q in cart])
    vel = np.zeros_like(pos)
    for k, (q, t) in enumerate(zip(cart, times)):
        dLdt = model.geometry.length_rates(q, direction * sd(t), R)
        L = model.lengths(q, R)
        vel[k] = [dl / model.maps[sid].payout_per_ustep(Li) for sid, dl, Li in zip(model.ids, dLdt, L)]
    vel[0] = vel[-1] = 0.0
    refs = np.zeros((n, 4), int) if ref is None else np.tile(np.asarray(ref, int), (n, 1))
    return Plan(times, pos, vel, refs, cart, label, {"v": v, "a": a, "dist": dist})


def plan_waypoints(model, points, lim, **kw) -> list[Plan]:
    return [plan_line(model, a, b, lim, **kw) for a, b in zip(points, points[1:])]


def plan_cable_move(start_pos, delta_usteps, max_rate, max_acc, *, segment_s=0.1, ref=None,
                    label="cable") -> Plan:
    """Independent per-station position changes on one shared timeline.

    Only for situations where the stations are *not* mechanically coupled
    (e.g. slack take-up with the claw resting on the floor), or for tiny
    probe packets. The duration is set by the largest change.
    """
    start = np.asarray(start_pos, float)
    delta = np.asarray(delta_usteps, float)
    big = float(np.max(np.abs(delta)))
    if big < 1e-9:
        raise PlanError("zero cable move")
    T, s, sd = trapezoid(1.0, max_rate / big, max_acc / big)
    n = max(2, int(math.ceil(T / segment_s)))
    times = np.linspace(0, T, n + 1)
    pos = np.array([start + delta * s(t) for t in times])
    vel = np.array([delta * sd(t) for t in times])
    vel[0] = vel[-1] = 0.0
    refs = np.zeros((n, 4), int) if ref is None else np.tile(np.asarray(ref, int), (n, 1))
    return Plan(times, pos, vel, refs, None, label, {})


def _check_path(model, cart, ws, lim, R, allow_low, check_tension):
    if ws is not None:
        for q in cart:
            v = ws.violations(model.geometry, q, R, allow_low=allow_low)
            if v:
                raise PlanError("workspace: " + "; ".join(v))
    if check_tension and lim.mass_kg is not None:
        for q in cart:
            r = tension_distribution(model.geometry, q, lim.mass_kg, t_min=lim.t_min, t_max=lim.t_max, R=R)
            if not r.feasible:
                raise PlanError(f"tension infeasible at {np.round(q, 3)} (max {r.max_tension:.1f} N)")


def limits_from_config(cfg, *, scale: float = 1.0, mass_kg=None) -> Limits:
    m = cfg.motion
    return Limits(cart_v=m.max_cart_speed_m_s * scale, cart_a=m.max_cart_accel_m_s2 * scale,
                  cable_v=m.max_cable_speed_m_s * scale, cable_a=m.max_cable_accel_m_s2 * scale,
                  segment_s=m.segment_s, t_min=m.min_tension_n, t_max=m.max_tension_n,
                  mass_kg=cfg.claw.mass_kg if mass_kg is None else mass_kg)


def model_from(geometry: Geometry, cfg, L0: dict) -> RobotModel:
    maps = {}
    for s in cfg.stations:
        m = CableMap(s.spool, s.drive.usteps_per_rev)
        maps[s.id] = m.with_reference(L0[s.id]) if L0.get(s.id) is not None else m
    return RobotModel(geometry, maps)
