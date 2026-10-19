"""Bead reference verification (sequential, one station at a time).

Each cable carries a bead near the claw end. When the cable is shortened to
``trigger_length_m`` the bead actuates the station's NC switch. Because the
beads sit near the claw, a bead can only be reached by flying the claw close
to that station's exit point, with the other three cables long. So homing is
sequential and every approach is a planned, tension-checked Cartesian move.

Rules (docs/CONTROL_SYSTEM_V1.md, "Reference verification"):

1. sigma here is the ABSOLUTE length uncertainty of that cable (L0), not the
   much smaller consistency uncertainty inside the calibrated volume: vision
   pins anchor range and L0 only together. With e the model's error:
   * the approach ends at model length trigger + window, so the bead cannot be
     reached during the (non-reference) approach if k*sigma <= window;
   * the search ends at model length trigger - overtravel + k*sigma, so even a
     failed switch cannot pull the bead more than ``overtravel`` past its
     trigger point;
   * the search is then complete (finds the bead for any |e| <= k*sigma) iff
     2*k*sigma <= overtravel.
   Otherwise BLOCKED with the numbers (do not "search harder").
2. The search is a slow coordinated line toward that anchor with the station's
   segments flagged ``ref = 1``; the station snapshots the first raw switch
   edge and holds everyone (coordinated feed-hold).
3. No capture by the search end -> stop, back off, BLOCKED. Never extend.
4. Pre-update check: the model's predicted length at the captured position
   must agree with the configured trigger length within k*sigma. Disagreement
   means the vision calibration or the bead entry is wrong, so nothing is
   updated (BLOCKED, operator decides).
5. Back-off is flagged ``ref = 2``: the switch must release during it.
6. Repeat; the spread of captured lengths must be <= repeatability_tol_m.
7. Only then is the station VERIFIED. The captures are returned as
   observations; the caller refits the whole model with them (changing L0
   alone would break the anchor/L0 consistency the vision fit established).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .kinematics import Workspace, tension_distribution
from .trajectory import PlanError, plan_line_from

IDS = ("A", "B", "C", "D")


@dataclass
class BeadCheck:
    station: str
    P_capture: float
    L_predicted: float
    trigger: float
    residual: float
    sigma: float
    k: float
    consistent: bool


@dataclass
class BeadOutcome:
    station: str
    status: str                       # VERIFIED | BLOCKED | FAULT
    reason: str = ""
    checks: list = field(default_factory=list)
    L0_old: float | None = None
    captures: list = field(default_factory=list)   # motor positions at the confirmed captures
    sigma: float | None = None
    spread_m: float | None = None
    log: list = field(default_factory=list)


def capture_sigma(bead, model_sigma: float, payout_per_ustep: float, latency_s: float = 0.001) -> float:
    """1-sigma of (predicted length at capture - trigger length)."""
    return math.sqrt(model_sigma ** 2 + bead.uncertainty_m ** 2 + payout_per_ustep ** 2 / 12
                     + (bead.approach_speed_m_s * latency_s) ** 2)


def check_capture(length_fn, i, P_cap, bead, sigma, k) -> BeadCheck:
    """``length_fn(i, P)`` is the current model's external length at position P."""
    Lp = float(length_fn(i, P_cap))
    r = Lp - bead.trigger_length_m
    return BeadCheck(IDS[i], float(P_cap), Lp, bead.trigger_length_m, r, sigma, k, abs(r) <= k * sigma)


def bead_workspace(ws: Workspace, i: int, min_len: float) -> Workspace:
    mins = ws.min_lengths.copy()
    mins[i] = min_len
    return Workspace(ws.lo, ws.hi, mins, ws.obstacles)


def approach_pose(model, i, L_target, ws: Workspace, *, mass_kg, t_min, t_max, R=None, prefer=None,
                  n_az=72, n_el=40):
    """Claw pose with cable i at L_target, inside the workspace (cable i exempt
    from its normal minimum), with a feasible tension distribution. Chooses the
    lowest max-tension pose, tie-broken by distance from ``prefer``."""
    geo = model.geometry
    a = geo.anchors[i]
    attach = geo.attach[i]
    R = np.eye(3) if R is None else R
    ws_i = bead_workspace(ws, i, L_target - 1e-3)
    best, why = None, {}
    for el in np.linspace(math.radians(3), math.radians(87), n_el):
        for az in np.linspace(-math.pi, math.pi, n_az, endpoint=False):
            d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el)])
            p = a + L_target * d - R @ attach
            v = ws_i.violations(geo, p, R)
            if v:
                why[v[0].split(" ")[0]] = why.get(v[0].split(" ")[0], 0) + 1
                continue
            t = tension_distribution(geo, p, mass_kg, t_min=t_min, t_max=t_max, R=R)
            if not t.feasible:
                why["tension"] = why.get("tension", 0) + 1
                continue
            key = (round(t.max_tension, 1), 0.0 if prefer is None else float(np.linalg.norm(p - prefer)))
            if best is None or key < best[0]:
                best = (key, p, t)
    if best is None:
        return None, f"no feasible approach pose for cable {IDS[i]} at {L_target:.3f} m (rejections: {why})"
    return best[1], best[2]


class BeadVerifier:
    """Runs the procedure for one station through a Coordinator."""

    def __init__(self, cfg, co, model, lim, ws: Workspace, sigma_fn, *, log=print, latency_s=0.001):
        self.cfg, self.co, self.model, self.lim, self.ws = cfg, co, model, lim, ws
        self.sigma_fn = sigma_fn            # q_room -> (4,) predicted length sigma
        self.log = log
        self.latency_s = latency_s

    def _length(self, i, P):
        return self.model.maps[IDS[i]].length(P)

    def _unit(self, i, p):
        return self.model.geometry.unit_vectors(p)[i]

    def _pose(self):
        p, _ = self.model.pose_from_positions(self.co.positions())
        return p

    def _move(self, p_to, *, ref=None, lim=None, ws=None, stop_on_capture=False, label="move"):
        try:
            plan = plan_line_from(self.model, self.co.positions(), p_to, lim or self.lim, ws=ws or self.ws,
                                  ref=ref, label=label)
        except PlanError as e:
            return None, str(e)
        r = self.co.execute(plan, stop_on_capture=stop_on_capture)
        return r, None

    def run(self, i: int, *, p_home, repeats: int = 2) -> BeadOutcome:
        sid = IDS[i]
        bead = self.cfg.stations[i].bead
        k = self.cfg.calibration.bead_k_sigma
        out = BeadOutcome(sid, "BLOCKED", L0_old=self.model.maps[sid].L0)
        lg = lambda s: (out.log.append(s), self.log(f"[bead {sid}] {s}"))
        if not bead.present:
            out.reason = "no bead configured"
            return out
        miss = [n for n in ("trigger_length_m", "uncertainty_m", "approach_speed_m_s", "search_window_m",
                            "max_overtravel_m", "backoff_m", "repeatability_tol_m") if getattr(bead, n) is None]
        if miss:
            out.reason = f"bead parameters not measured: {miss}"
            return out
        L_target = bead.trigger_length_m + bead.search_window_m
        m = self.cfg.motion
        pa = approach_pose(self.model, i, L_target, self.ws, mass_kg=self.cfg.claw.mass_kg,
                           t_min=m.min_tension_n, t_max=m.max_tension_n, prefer=np.asarray(p_home))
        if pa[0] is None:
            out.reason = pa[1]
            return out
        pa = pa[0]
        sig_model = float(self.sigma_fn(pa)[i])
        ppu = self.model.maps[sid].payout_per_ustep(L_target)
        sig = capture_sigma(bead, sig_model, ppu, self.latency_s)
        out.sigma = sig
        if sig_model > self.cfg.calibration.bead_length_sigma_max_m:
            out.reason = (f"absolute length sigma {sig_model * 1e3:.1f} mm exceeds "
                          f"{self.cfg.calibration.bead_length_sigma_max_m * 1e3:.1f} mm: calibrate further first")
            return out
        if k * sig > bead.search_window_m or 2 * k * sig > bead.max_overtravel_m:
            out.reason = (f"k*sigma = {k * sig * 1e3:.1f} mm: a safe, complete search needs <= window "
                          f"({bead.search_window_m * 1e3:.0f} mm) and <= half the overtravel "
                          f"({bead.max_overtravel_m * 1e3:.0f} mm)")
            return out
        L_floor = bead.trigger_length_m - bead.max_overtravel_m + k * sig
        ws_appr = bead_workspace(self.ws, i, L_target - 1e-3)
        ws_search = bead_workspace(self.ws, i, L_floor - 1e-3)
        lg(f"approach pose {np.round(pa, 3).tolist()}, sigma {sig * 1e3:.2f} mm")
        r, err = self._move(pa, ws=ws_appr, label=f"bead {sid} approach")
        if r is None or not r.ok:
            out.status, out.reason = "FAULT", f"approach failed: {err or r.reason}"
            return out
        slow = replace(self.lim, cart_v=bead.approach_speed_m_s, cable_v=bead.approach_speed_m_s,
                       cart_a=min(self.lim.cart_a, bead.approach_speed_m_s / 0.2),
                       cable_a=min(self.lim.cable_a, bead.approach_speed_m_s / 0.2))
        ref_search = [1 if j == i else 0 for j in range(4)]
        ref_back = [2 if j == i else 0 for j in range(4)]
        caps = []
        for rep in range(repeats):
            p0 = self._pose()
            L_now = float(self.model.geometry.lengths(p0)[i])
            travel = L_now - L_floor
            if travel <= 0:
                out.status, out.reason = "FAULT", "already at the overtravel limit"
                return out
            target = p0 + self._unit(i, p0) * travel
            r, err = self._move(target, ref=ref_search, lim=slow, ws=ws_search, stop_on_capture=True,
                                label=f"bead {sid} search {rep + 1}")
            if r is None:
                out.status, out.reason = "FAULT", f"search plan refused: {err}"
                return out
            others = [s for s in r.captures if s != sid]
            if others:
                out.status, out.reason = "FAULT", f"unexpected capture on {others}"
                return out
            if sid not in r.captures:
                self._move(pa, ws=ws_search, label=f"bead {sid} retreat")
                out.reason = (r.reason if not r.ok else
                              f"bead not found within window + overtravel ({travel * 1e3:.0f} mm): bead moved, "
                              "trigger length wrong, or switch/wiring fault")
                return out
            P_cap = float(r.captures[sid]["pos"])
            chk = check_capture(self._length, i, P_cap, bead, sig, k)
            out.checks.append(chk)
            lg(f"capture {rep + 1}: predicted {chk.L_predicted:.4f} m vs trigger {chk.trigger:.4f} m "
               f"(residual {chk.residual * 1e3:+.2f} mm, limit {k * sig * 1e3:.2f} mm)")
            # back off with the switch allowed to be active; it must release
            p1 = self._pose()
            r, err = self._move(p1 - self._unit(i, p1) * bead.backoff_m, ref=ref_back, lim=slow, ws=ws_search,
                                label=f"bead {sid} backoff {rep + 1}")
            if r is None or not r.ok:
                out.status, out.reason = "FAULT", f"backoff failed: {err or r.reason}"
                return out
            if sid not in r.releases:
                out.status, out.reason = "FAULT", "switch did not release during backoff (bead stuck or wiring)"
                return out
            if not chk.consistent:
                self._move(pa, ws=ws_search, label=f"bead {sid} retreat")
                out.reason = (f"pre-update check failed: model predicts {chk.L_predicted:.4f} m at the bead, "
                              f"configured trigger {chk.trigger:.4f} m ({chk.residual * 1e3:+.1f} mm > "
                              f"{k * sig * 1e3:.1f} mm). Nothing updated.")
                return out
            caps.append(P_cap)
        Ls = [self._length(i, P) for P in caps]
        out.spread_m = float(max(Ls) - min(Ls))
        if out.spread_m > bead.repeatability_tol_m:
            out.reason = f"capture spread {out.spread_m * 1e3:.2f} mm > {bead.repeatability_tol_m * 1e3:.2f} mm"
            self._move(pa, ws=ws_search, label=f"bead {sid} retreat")
            return out
        out.captures = caps
        lg(f"captures consistent: residual {np.mean([c.residual for c in out.checks]) * 1e3:+.2f} mm, "
           f"spread {out.spread_m * 1e3:.2f} mm")
        r, err = self._move(pa, ws=ws_search, label=f"bead {sid} retreat")
        if r is None or not r.ok:
            out.status, out.reason = "FAULT", f"retreat failed: {err or r.reason}"
            return out
        r, err = self._move(np.asarray(p_home, float), ws=ws_appr, label=f"bead {sid} return")
        if r is None or not r.ok:
            out.status, out.reason = "FAULT", f"return failed: {err or r.reason}"
            return out
        out.status, out.reason = "VERIFIED", "bead captures consistent"
        return out
