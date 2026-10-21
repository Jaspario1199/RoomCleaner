"""Motion planning: Cartesian or cable-space moves -> per-station segment streams.

The planner never sends "pull one cable, release the opposite one by the same
amount" or "pay out every cable equally". Every Cartesian move is converted
through the current geometric model into per-cable length histories (one per ACTIVE station: four, or three in
three-station mode), and those into motor-position histories via each station's spool map. All
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
from .station_core import MIN_SEG_US

# Segment-duration floor. The station nacks ("range") any segment shorter than MIN_SEG_US (station_core), and a
# rest-to-rest profile over a few micrometres lasts only a few milliseconds (T = 2 sqrt(d / a)), so a naive
# "max(2, ceil(T / segment_s))" grid produced 3 ms segments for a 3 um move. The planner therefore never emits a segment
# shorter than 2 x MIN_SEG_US (a 2x margin for rounding of the microsecond duration and for the station's own checks),
# and a profile that would be shorter than two such segments is slowed down (never sped up) to last exactly that long.
MIN_SEG_PLAN_S = 2 * MIN_SEG_US / 1e6        # shortest segment the planner emits (10 ms)
MIN_PLAN_S = 2 * MIN_SEG_PLAN_S              # shortest plan (two segments minimum): 20 ms

# A Cartesian move whose cable lengths all stay within this of their start values over the whole path is a no-op
# ("already there"). 20 um of cable is far below the geometry's own uncertainty (calibrated length sigma ~1 mm) and is
# 0.3 microstep on the coarsest simulated drive (~5 on the finest), so no station would move meaningfully for it.
# It is kept small on purpose: any Cartesian move of >= 60 um moves some cable by >= ~30 um (the four cables span 3-D),
# so it stays a real, slowed-down motion rather than being swallowed. The plan is returned with a single knot
# (Plan.is_noop); Coordinator.execute completes it after the usual readiness checks without sending a segment.
NOOP_CABLE_M = 20e-6


@dataclass
class RobotModel:
    """Current best geometric model in the working (room) frame."""
    geometry: Geometry
    maps: dict          # sid -> CableMap (with L0 for the current boot epoch)
    ids: tuple = ("A", "B", "C", "D")   # the ACTIVE stations (model_from sets them from the config: 3 or 4)

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
    pos: np.ndarray                         # (K, n) microsteps, n = number of active stations (3 or 4)
    vel: np.ndarray                         # (K, n) microsteps / s
    ref: np.ndarray                         # (K-1, n) segment ref flag per station
    cart: np.ndarray | None = None          # (K, 3) planned claw positions (if Cartesian)
    label: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return float(self.times[-1])

    @property
    def is_noop(self) -> bool:
        """True for a plan with a single knot: the target is where the stations already are, no segment exists."""
        return len(self.times) < 2

    @property
    def start(self) -> np.ndarray:
        return self.pos[0]

    @property
    def end(self) -> np.ndarray:
        return self.pos[-1]

    def position_at(self, tau_s: float) -> np.ndarray:
        """Planned microstep positions of all stations at path time tau (s)."""
        from .station_core import hermite
        if self.is_noop:
            return np.array(self.pos[0], float)
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


def _slowed_profile(dist: float, T: float):
    """(v, a) of a rest-to-rest triangular profile over ``dist`` lasting ``T``: slower than whatever it replaces whenever
    ``T`` exceeds that profile's own duration. ``v`` is 1 % above the peak so ``trapezoid`` takes the triangular branch."""
    return 1.01 * 2.0 * dist / T, 4.0 * dist / (T * T)


def _segment_count(T: float, segment_s: float) -> int:
    """Number of equal segments for a profile of duration ``T`` (>= MIN_PLAN_S): about ``segment_s`` each, at least two,
    and never so many that one is shorter than MIN_SEG_PLAN_S."""
    return max(2, min(int(math.ceil(T / segment_s)), int(math.floor(T / MIN_SEG_PLAN_S + 1e-9))))


def _noop_plan(start_pos, cart, label, meta) -> Plan:
    """A one-knot plan: the stations stay where they are (see NOOP_CABLE_M)."""
    start = np.asarray(start_pos, float).reshape(1, -1)
    return Plan(np.zeros(1), start, np.zeros_like(start), np.zeros((0, start.shape[1]), int),
                None if cart is None else np.asarray(cart, float).reshape(1, 3), label, {"noop": True, **meta})


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
    tension_derate: float = 0.8        # plan to 80 % of the measured pull limit
    dynamic_accel: float = 0.0         # extra vertical acceleration allowance (m/s^2)


def plan_line(model: RobotModel, p_from, p_to, lim: Limits, *, R=None, ws: Workspace | None = None,
              allow_low: bool = False, ref=None, label="line", check_tension=True) -> Plan:
    """Straight Cartesian move. A move whose cable lengths all stay within NOOP_CABLE_M of their start values over the
    whole path (this includes a zero-length move) returns a no-op plan (``Plan.is_noop``): the target is already reached
    and nothing is sent. Every other plan has >= 2 segments, each >= MIN_SEG_PLAN_S (> the station's MIN_SEG_US)."""
    p_from, p_to = np.asarray(p_from, float), np.asarray(p_to, float)
    delta = p_to - p_from
    dist = float(np.linalg.norm(delta))
    # lengths along the whole path, not only at its ends: a chord between two poses on a common sphere about every anchor
    # would otherwise look like "no cable change"
    L_from = model.lengths(p_from, R)
    probe_pts = [p_from + delta * f for f in np.linspace(0, 1, 21)]
    dL_max = max(float(np.max(np.abs(model.lengths(q, R) - L_from))) for q in probe_pts)
    if dL_max < NOOP_CABLE_M:
        if ref is not None and np.any(np.asarray(ref, int) != 0):
            raise PlanError(f"reference-capture move of {dL_max * 1e6:.0f} um of cable is below the planner minimum "
                            f"({NOOP_CABLE_M * 1e6:.0f} um): nothing could be captured")
        _check_path(model, np.array([p_from, p_to]), ws, lim, R, allow_low, check_tension)
        return _noop_plan(model.positions_for(p_from, R), p_to, label, {"dist": dist, "dL_max_m": dL_max})
    direction = delta / dist
    # worst cable-rate factor along the path: |dL/ds| = |u . dir|
    kmax = max(float(np.max(np.abs(model.geometry.unit_vectors(q, R) @ direction))) for q in probe_pts)
    v = min(lim.cart_v, lim.cable_v / max(kmax, 1e-6))
    a = min(lim.cart_a, lim.cable_a / max(kmax, 1e-6))
    T, s, sd = trapezoid(dist, v, a)
    if T < MIN_PLAN_S:                       # too short for two station-legal segments: slow it down, never speed up
        v, a = _slowed_profile(dist, MIN_PLAN_S)
        T, s, sd = trapezoid(dist, v, a)
    n = _segment_count(T, lim.segment_s)
    times = np.linspace(0, T, n + 1)
    cart = np.array([p_from + direction * s(t) for t in times])
    _check_path(model, cart, ws, lim, R, allow_low, check_tension, accels=(a * direction, -a * direction))
    pos = np.array([model.positions_for(q, R) for q in cart])
    vel = np.zeros_like(pos)
    for k, (q, t) in enumerate(zip(cart, times)):
        dLdt = _length_rates(model.geometry, q, direction, sd(t), R)
        L = model.lengths(q, R)
        vel[k] = [dl / model.maps[sid].payout_per_ustep(Li) for sid, dl, Li in zip(model.ids, dLdt, L)]
    vel[0] = vel[-1] = 0.0
    refs = np.zeros((n, pos.shape[1]), int) if ref is None else np.tile(np.asarray(ref, int), (n, 1))
    return Plan(times, pos, vel, refs, cart, label, {"v": v, "a": a, "dist": dist})


def _length_rates(geo: Geometry, q, direction, speed, R, h: float = 1e-4):
    """dL/dt along the path. With a predicted attitude R(p) the lengths also change through the tilt
    that follows the position, so the rate is a central difference along the path; otherwise the
    analytic -u . v (identical to the original point-claw model)."""
    if R is not None or geo._att is None:
        return geo.length_rates(q, direction * speed, R)
    return (geo.lengths(q + h * direction) - geo.lengths(q - h * direction)) / (2 * h) * speed


def plan_line_from(model: RobotModel, P_actual, p_to, lim: Limits, *, R=None, p_guess=None,
                   max_offset_m: float = 0.005, **kw) -> Plan:
    """Line move that starts exactly at the stations' actual positions.

    After a hold or a capture the four positions are no longer exactly on the
    model's geometry (feed-hold ramps, post-capture shortening suppression,
    rounding). The start pose is solved from the actual positions and the
    small per-station offset is faded out linearly along the path. A large
    offset means the model and the cables disagree, which is refused.
    """
    P_actual = np.asarray(P_actual, float)
    p_from, rms = model.pose_from_positions(P_actual, p_guess, R)
    plan = plan_line(model, p_from, p_to, lim, R=R, **kw)
    off = P_actual - plan.pos[0]
    L = model.lengths(p_from, R)
    off_m = np.array([o * model.maps[s].payout_per_ustep(Li) for o, s, Li in zip(off, model.ids, L)])
    if np.max(np.abs(off_m)) > max_offset_m:
        raise PlanError(f"actual positions differ from the model by {np.round(off_m * 1e3, 1).tolist()} mm "
                        "of cable: model and cables disagree")
    if plan.is_noop:                         # already at the target: hold exactly where the stations are
        plan.pos = P_actual.reshape(1, -1).copy()
        plan.cart = np.asarray(p_from, float).reshape(1, 3)
        plan.meta["start_offset_usteps"] = off.tolist()
        plan.meta["start_fk_rms_m"] = rms
        return plan
    dist = plan.meta["dist"]
    _, sf, sdf = trapezoid(dist, plan.meta["v"], plan.meta["a"])
    s = np.array([sf(t) for t in plan.times]) / dist
    sd = np.array([sdf(t) for t in plan.times]) / dist
    plan.pos = plan.pos + off[None, :] * (1.0 - s)[:, None]
    plan.vel = plan.vel - off[None, :] * sd[:, None]
    plan.vel[0] = plan.vel[-1] = 0.0
    plan.meta["start_offset_usteps"] = off.tolist()
    plan.meta["start_fk_rms_m"] = rms
    return plan


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
    if T < MIN_PLAN_S:                       # a few-microstep move: slow it down to two station-legal segments
        v, a = _slowed_profile(1.0, MIN_PLAN_S)
        T, s, sd = trapezoid(1.0, v, a)
    n = _segment_count(T, segment_s)
    times = np.linspace(0, T, n + 1)
    pos = np.array([start + delta * s(t) for t in times])
    vel = np.array([delta * sd(t) for t in times])
    vel[0] = vel[-1] = 0.0
    refs = np.zeros((n, len(start)), int) if ref is None else np.tile(np.asarray(ref, int), (n, 1))
    return Plan(times, pos, vel, refs, None, label, {})


def _check_path(model, cart, ws, lim, R, allow_low, check_tension, accels=((0.0, 0.0, 0.0),)):
    if ws is not None:
        for q in cart:
            v = ws.violations(model.geometry, q, R, allow_low=allow_low)
            if v:
                raise PlanError("workspace: " + "; ".join(v))
    if check_tension and lim.mass_kg is not None:
        # review M8: include the path acceleration both ways plus the specified
        # dynamic load, and keep a derating margin under the motor limit
        t_max = lim.t_max * lim.tension_derate
        dyn = np.array([0.0, 0.0, lim.dynamic_accel])
        for q in cart:
            for acc in accels:
                r = tension_distribution(model.geometry, q, lim.mass_kg, t_min=lim.t_min, t_max=t_max, R=R,
                                         accel=np.asarray(acc, float) + dyn)
                if not r.feasible:
                    raise PlanError(f"tension infeasible at {np.round(q, 3)} (max {r.max_tension:.1f} N "
                                    f"> {t_max:.1f} N incl. dynamics)")


def limits_from_config(cfg, *, scale: float = 1.0, mass_kg=None) -> Limits:
    m = cfg.motion
    return Limits(cart_v=m.max_cart_speed_m_s * scale, cart_a=m.max_cart_accel_m_s2 * scale,
                  cable_v=m.max_cable_speed_m_s * scale, cable_a=m.max_cable_accel_m_s2 * scale,
                  segment_s=m.segment_s, t_min=m.min_tension_n, t_max=m.max_tension_n,
                  mass_kg=cfg.claw.mass_kg if mass_kg is None else mass_kg,
                  dynamic_accel=m.dynamic_accel_m_s2)


def model_from(geometry: Geometry, cfg, L0: dict) -> RobotModel:
    maps = {}
    for s in cfg.stations:
        m = CableMap(s.spool, s.drive.usteps_per_rev)
        maps[s.id] = m.with_reference(L0[s.id]) if L0.get(s.id) is not None else m
    return RobotModel(geometry, maps, tuple(s.id for s in cfg.stations))
