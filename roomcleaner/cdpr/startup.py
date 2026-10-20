"""Self-calibrating startup: DISARMED -> ... -> READY.

Operator preconditions: claw upright on the floor near the middle of the room,
the marker on the floor under the camera, room/anchor entries in the config,
the room cleared (nobody under the workspace), power strip within reach.

States (each step has explicit bounds and abort conditions; an abort HOLDS
motion and never removes holding torque):

SELF_CHECK
    config complete for every stage needed; suspended motion authorised;
    stations configured (hash), clock-synced, fault-free, switches closed
    (NC: open = bead at switch or broken wire), armed; claw online, battery
    >= min; camera calibration id recorded; marker visible and still; claw
    resting upright on the floor (height and tilt). Vision noise measured.
SLACK_TAKEUP
    one station at a time, a slow continuous retraction (claw on the floor, so
    the stations are not coupled) bounded by ``max_slack_m``. Vision is polled
    every frame; claw motion >= max(onset_translation, k*noise) marks the taut
    onset; pulling continues to ``bearing_translation_m`` so the slide direction
    is measurable, then the station holds and pays out ``onset_backoff_m``.
    Abort: no onset within max slack (cable unattached / wrong direction /
    station order), marker lost, tilt. After all four: the slide bearings are
    checked against the anchor entries (catches swapped station wiring) and a
    first fit gives L0 per station and the marker registration.
INITIAL_LIFT
    all cables brought to just-taut, then vertical packets of ``lift_packet_m``
    computed incrementally from the model's cable directions. After each
    packet: vision height, lateral drift, tilt. Abort: drift > max, tilt > max,
    commanded - observed lift > budget, no clearance by ``max_lift_m``.
VISUAL_INITIALIZATION
    still pose while suspended -> refit (onsets + first suspended sample).
CALIBRATION
    local box (D-optimal poses + witnesses) -> fit -> expanded box -> fit ->
    acceptance (identifiability, residuals, uniqueness, witnesses, predicted
    length sigma over the work volume). Partial acceptance gives LOCAL_ONLY
    with the validated volume.
    With ``startup.slack_probe`` every suspended sample (this state and
    VISUAL_INITIALIZATION) is preceded by a per-pose slack probe: each cable in
    turn is retracted in small steps until the claw moves (taut onset), its
    slack is measured, it is left just taut, the sample is taken with all four
    taut, and the motor positions are restored afterwards (so the planner's
    model-consistent positions are unchanged).
REFERENCE_VERIFICATION
    bead verification, one station at a time (homing.py).
READY
    level VERIFIED (all beads verified) or LOCAL_ONLY (stated reasons).

Tension is NOT measured in V1 (open decision, see docs): the lift and the
calibration rely on geometric consistency checks instead, which bound but do
not measure cable load.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .calibration import (IDS, BeadObs, Calibrator, OnsetSample, PoseSample, Priors, align_from_bearings,
                          box_candidates, design_excitation, marker_visible, predicted_vision_cov)
from .frames import inv_T, make_T, planar_T
from .kinematics import Geometry, tension_distribution, workspace_from_config
from .perception import to_marker, to_room
from .spool import CableMap
from .protocol import State
from .trajectory import PlanError, limits_from_config, model_from, plan_cable_move, plan_line_from

def probe_response(geo, q_room, i, k_rel=None):
    """Claw displacement (room frame) per unit retraction of cable ``i`` beyond
    the taut point, for equal-modulus cables of stiffness ~ 1/length (the
    modulus cancels): ``x = (sum_j k_j u_j u_j^T)^-1 k_i u_i`` over all four
    cables (a slack cable not yet found is the main source of mismatch, hence the
    prior sigma ``probe_response_sigma``)."""
    U = geo.unit_vectors(q_room)
    k = 1.0 / geo.lengths(q_room) if k_rel is None else np.asarray(k_rel, float)
    K = sum(k[j] * np.outer(U[j], U[j]) for j in range(4))
    return np.linalg.solve(K, k[i] * U[i])


def hinge_analysis(r, P, C, v, sig_w, k_noise, floor_m):
    """Taut-onset analysis of one cable's retraction series.

    Data: ``r`` (K,) cumulative retraction (m), ``P`` (K,3) vision positions
    (marker frame) and ``C`` (K,3,3) covariances of the individual measurements.
    Model: ``p_k = p0 + w * max(r_k - s, 0)``: the claw does not move until the
    slack ``s`` is taken up, then moves by ``w`` per metre of further
    retraction (``w`` has a Gaussian prior ``N(v, sig_w^2 I)`` from the cable
    geometry). ``s`` is profiled on a grid; the null model is "no response yet".

    Returns a dict: ``detected`` (the hinge beats the null by ``k_noise`` sigma
    AND the fitted claw motion at the last step is >= ``floor_m``), ``s`` (best
    slack), ``sigma_s`` (profile 1-sigma), ``sig`` (significance, sigma),
    ``disp`` (fitted motion at the last step, m)."""
    r = np.asarray(r, float)
    P = np.asarray(P, float)
    W = np.linalg.inv(np.asarray(C, float))
    rK = float(r[-1])
    n = int(min(max(round(rK / 5e-5), 20), 240))
    sg = np.linspace(0.0, rK, n + 1)                           # s = rK is the null model
    H = np.maximum(r[None, :] - sg[:, None], 0.0)               # (G, K)
    S0 = W.sum(0)
    S1 = np.einsum("gk,kab->gab", H, W)
    S2 = np.einsum("gk,kab->gab", H * H, W) + np.eye(3) / sig_w ** 2
    N = np.zeros((len(sg), 6, 6))
    N[:, :3, :3] = S0
    N[:, :3, 3:] = S1
    N[:, 3:, :3] = np.swapaxes(S1, 1, 2)
    N[:, 3:, 3:] = S2
    b0 = np.einsum("kab,kb->a", W, P)
    b1 = np.einsum("gk,kab,kb->ga", H, W, P)
    rhs = np.concatenate([np.broadcast_to(b0, (len(sg), 3)), b1 + v / sig_w ** 2], axis=1)
    th = np.linalg.solve(N, rhs[:, :, None])[:, :, 0]
    p0, w = th[:, :3], th[:, 3:]
    res = P[None] - p0[:, None, :] - H[:, :, None] * w[:, None, :]
    chi2 = np.einsum("gka,kab,gkb->g", res, W, res) + np.sum((w - v) ** 2, axis=1) / sig_w ** 2
    g = int(np.argmin(chi2))
    null = float(chi2[-1])
    sig = math.sqrt(max(null - float(chi2[g]), 0.0))
    ok = np.flatnonzero(chi2 <= chi2[g] + 1.0)
    lo, hi = sg[ok.min()], sg[ok.max()]
    step = sg[1] - sg[0] if len(sg) > 1 else 0.0
    sigma_s = max(0.5 * (hi - lo), 0.5 * step)
    disp = float(np.linalg.norm(w[g]) * max(rK - sg[g], 0.0))
    return {"detected": bool(g < len(sg) - 1 and sig >= k_noise and disp >= floor_m), "s": float(sg[g]),
            "sigma_s": float(sigma_s), "sig": float(sig), "disp": disp, "w": w[g].copy()}


STARTUP_STATES = ("DISARMED", "SELF_CHECK", "SLACK_TAKEUP", "INITIAL_LIFT", "VISUAL_INITIALIZATION",
                  "CALIBRATION", "REFERENCE_VERIFICATION", "READY")


class StartupAbort(Exception):
    def __init__(self, state, reason, *, suspended=False, paused=False):
        super().__init__(f"{state}: {reason}")
        self.state, self.reason, self.suspended, self.paused = state, reason, suspended, paused


@dataclass
class StartupReport:
    state: str = "DISARMED"
    history: list = field(default_factory=list)
    measurements: dict = field(default_factory=dict)
    outcome: str | None = None              # READY | FAULT | PAUSED
    level: str = "NONE"
    reasons: list = field(default_factory=list)


class RobotContext:
    """Everything the procedures share. Working frame for motion: the room."""

    def __init__(self, cfg, co, claw, vision, camera, ledger, *, log=print, data_dir=None):
        self.cfg, self.co, self.claw, self.vision, self.camera, self.ledger = cfg, co, claw, vision, camera, ledger
        self.log = log
        self.data_dir = Path(data_dir) if data_dir else None
        self.cal = Calibrator(cfg, {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations})
        self.priors = self.cal.priors
        self.T_R_M = planar_T(self.priors.position[0], self.priors.position[1], self.priors.heading)
        self.model = None
        self.result = None
        self.onsets: list = []
        self.samples: list = []
        self.lim = limits_from_config(cfg)
        self.ws = None
        self.validated_volume = None        # room-frame points where the model is validated
        self.T_B_C = cfg.claw.T_body_cam
        self.persist = lambda: None         # supervisor installs its durable save here

    # -- time ------------------------------------------------------------
    def wait(self, s):
        self.co.wait(s * 1e6)

    def now_s(self):
        return self.co.rt.now_us() / 1e6

    # -- model -----------------------------------------------------------
    def set_model(self, anchors_room, L0: dict, T_R_M=None):
        if T_R_M is not None:
            self.T_R_M = np.asarray(T_R_M, float)
        geo = Geometry(anchors_room, self.cfg.attachment_points())
        self.model = model_from(geo, self.cfg, L0)
        self.ws = workspace_from_config(self.cfg, np.asarray(anchors_room),
                                        lowest_point_z=float(self.cfg.claw.lowest_point_body_m[2]))
        self._bead_margin()

    def _bead_margin(self):
        """Until the beads are verified the absolute length can be off by
        k*sigma_abs: widen the normal-motion keep-out from each bead so an
        ordinary move cannot pull a bead onto its switch (review M2)."""
        if self.result is None or self.ws is None or self.ledger.level == "VERIFIED":
            return
        k = self.cfg.calibration.bead_k_sigma
        sig = self.cal.absolute_sigma(self.result)
        for i, s in enumerate(self.cfg.stations):
            if s.bead.present and s.bead.trigger_length_m is not None and not self.ledger.stations[s.id].bead_verified:
                self.ws.min_lengths[i] = s.bead.trigger_length_m + s.bead.min_length_margin_m + k * float(sig[i])

    def apply_result(self, res, source):
        self.result = res
        self.ledger.anchors_room = res.anchors_room.tolist()
        self.set_model(res.anchors_room, dict(zip(IDS, res.L0)), res.T_R_M)
        sig = res.sigma()
        boots = {s: self.co.links[s].boot for s in IDS}
        for i, s in enumerate(IDS):
            self.ledger.set_reference(s, boots[s], res.L0[i], float(sig[f"L0 {s}"]), source)
        self.ledger.T_R_M = res.T_R_M.tolist()
        self.ledger.marker_valid = True
        self.save_model()

    # -- persistence (host restart while suspended) ----------------------------
    def save_model(self):
        if self.data_dir is None or self.result is None or self.model is None:
            return
        from .trust import atomic_write
        st = {"result": self.result.to_state(), "T_R_M": self.T_R_M.tolist(),
              "L0": {s: self.model.maps[s].L0 for s in IDS},
              "boots": {s: self.co.links[s].boot for s in IDS},
              "validated_volume": None if self.validated_volume is None else np.asarray(self.validated_volume).tolist(),
              "beads": [[b.i, b.P, b.trigger, b.sigma] for b in self.cal.beads]}
        atomic_write(self.data_dir / "model.json", json.dumps(st))

    def load_model(self) -> bool:
        if self.data_dir is None or not (self.data_dir / "model.json").exists():
            return False
        from .calibration import CalibrationResult
        d = json.loads((self.data_dir / "model.json").read_text())
        self.result = CalibrationResult.from_state(d["result"])
        self.set_model(self.result.anchors_room, d["L0"], d["T_R_M"])
        vv = d.get("validated_volume")
        self.validated_volume = None if vv is None else np.asarray(vv)
        self.cal.beads = [BeadObs(int(i), P, t, sg) for i, P, t, sg in d.get("beads", [])]
        self.saved_boots = d.get("boots", {})
        return True

    def room_pose(self, sp):
        return to_room(self.T_R_M, sp.p)

    def length_sigma_room(self, q_R):
        if self.result is None:
            return np.full(4, np.inf)
        return self.cal.length_sigma(self.result, to_marker(self.T_R_M, q_R))

    def ppu(self, i):
        sid = IDS[i]
        P = self.co.positions()[i]
        m = self.model.maps[sid] if self.model is not None and self.model.maps[sid].L0 is not None else None
        if m is None:
            return 2 * math.pi * self.cfg.stations[i].spool.core_radius_m / self.cfg.stations[i].drive.usteps_per_rev
        return m.payout_per_ustep(m.length(P))

    def save(self, name, obj):
        if self.data_dir is None:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / name).write_text(json.dumps(obj, indent=2, default=lambda o: np.asarray(o).tolist()))


class StartupSequencer:
    # STUDY HOOK (floor-reference study; None = off, behaviour unchanged): an
    # object with visible(camera, T_B_C, T_M_B, min_side_px=, margin_px=) -> bool
    # and edge_eff(camera, T_B_C, T_M_B, min_side_px=, margin_px=) -> float
    # (e.g. sim.world.FloorBoard). When set, the excitation design treats a pose
    # as visible if ANY tag of the board is in view, and predicts the vision
    # covariance with the board's effective span instead of the single tag edge.
    study_board = None

    def __init__(self, ctx: RobotContext):
        self.ctx = ctx
        self.cfg = ctx.cfg
        self.rep = StartupReport()
        self.noise_m = 0.001
        self.p_floor = None
        self.probe_log: list = []               # one record per probed pose (slack_probe)

    # -------------------------------------------------------------- helpers
    def _enter(self, state, msg=""):
        self.rep.state = state
        self.rep.history.append((round(self.ctx.now_s(), 3), state, msg))
        self.ctx.log(f"[startup] {state} {msg}")

    def _still(self, n=None, state="?", suspended=False):
        st = self.cfg.startup
        sp, why = self.ctx.vision.still_pose(n or st.still_samples, self.ctx.wait, interval_s=st.frame_interval_s,
                                             max_wait_s=max(10.0, st.max_marker_wait_s if n is None else 10.0),
                                             spread_max_m=st.still_spread_max_m)
        if sp is None:
            raise StartupAbort(state, why, suspended=suspended, paused=True)
        return sp

    def _execute(self, plan, state, *, suspended, monitor=None, stop_on_capture=False):
        r = self.ctx.co.execute(plan, monitor=monitor, stop_on_capture=stop_on_capture)
        if not r.ok and r.reason.startswith("paused"):
            raise StartupAbort(state, r.reason, suspended=suspended, paused=True)
        return r

    def _cable_rate(self, speed, i=None):
        ppus = [self.ctx.ppu(j) for j in (range(4) if i is None else [i])]
        return speed / min(ppus)

    # -------------------------------------------------------------- run
    def run(self) -> StartupReport:
        steps = [("SELF_CHECK", self.self_check), ("SLACK_TAKEUP", self.slack_takeup),
                 ("INITIAL_LIFT", self.initial_lift), ("VISUAL_INITIALIZATION", self.visual_init),
                 ("CALIBRATION", self.calibrate), ("REFERENCE_VERIFICATION", self.verify_references)]
        try:
            for name, fn in steps:
                self._enter(name)
                fn()
        except StartupAbort as e:
            self.rep.outcome = "PAUSED" if e.paused else "FAULT"
            self.rep.reasons.append(e.reason)
            self.rep.measurements["suspended"] = e.suspended
            if e.suspended:                             # never set True from an abort (fail closed)
                self.ctx.ledger.claw_supported = False
            self.rep.measurements["suspended"] = not self.ctx.ledger.claw_supported
            self.ctx.persist()
            self._enter(self.rep.outcome, f"in {e.state}: {e.reason}")
            return self.rep
        self.rep.outcome = "READY"
        self.rep.level = self.ctx.ledger.level
        self._enter("READY", f"level {self.ctx.ledger.level}")
        return self.rep

    # ------------------------------------------------------------ SELF_CHECK
    def self_check(self):
        cfg, ctx, S = self.cfg, self.ctx, "SELF_CHECK"
        missing = cfg.missing("calibration")
        if missing:
            raise StartupAbort(S, f"configuration incomplete: {missing}")
        if not cfg.authorization.suspended_motion_authorized:
            raise StartupAbort(S, "suspended motion not authorised in the configuration")
        ctx.ledger.on_camera_calibration(ctx.camera.calibration_id)
        st = ctx.claw.status()
        if not st.get("online"):
            raise StartupAbort(S, "claw offline")
        if st.get("battery_v") is not None and st["battery_v"] < cfg.startup.battery_min_v:
            raise StartupAbort(S, f"claw battery {st['battery_v']:.2f} V < {cfg.startup.battery_min_v} V")
        # 1) the claw must demonstrably rest upright on the floor BEFORE any
        #    station is touched; only then is clearing latched faults safe
        sp = self._still(state=S)
        self.noise_m = max(sp.spread_m, 2e-4)
        zf = -float(cfg.claw.lowest_point_body_m[2])
        if abs(sp.p[2] - zf) > cfg.startup.floor_height_tol_m:
            raise StartupAbort(S, f"claw origin {sp.p[2]:.3f} m above the marker, expected {zf:.3f} m: "
                                  "not resting upright on the floor (or marker edge / camera mount wrong)")
        tilt = max(sp.tilt_rad, ctx.claw.tilt())
        if tilt > cfg.startup.max_tilt_rad:
            raise StartupAbort(S, f"claw tilted {math.degrees(tilt):.1f} deg")
        ctx.ledger.claw_supported = True
        ctx.persist()
        # 2) stations
        co = ctx.co
        try:
            co.wait(300000)
            for s_ in IDS:                           # e.g. LEASE latched while parked: safe on the floor
                if (co.links[s_].tel or {}).get("st") == State.FAULT:
                    co.clear(s_)
            co.configure()
            co.wait_synced(5.0)
            co.wait(200000)                          # telemetry reflecting the new configuration
        except Exception as e:                      # CoordinatorError: station unreachable / config
            raise StartupAbort(S, f"stations: {e}")
        bad = {s: [x for x in r if x not in ("state OFF", "state IDLE")] for s, r in co.readiness().items()}
        bad = {s: r for s, r in bad.items() if r}
        if bad:
            raise StartupAbort(S, f"stations not healthy: {bad}")
        sw = {s: (co.links[s].tel or {}).get("sw") for s in IDS}
        if any(sw.values()):
            raise StartupAbort(S, f"switch open at {[s for s, v in sw.items() if v]}: bead at switch or broken wire")
        try:
            co.arm(sw_ok=False)
        except Exception as e:
            raise StartupAbort(S, f"arm refused: {e}")
        co.wait(100000)
        bad = {s: r for s, r in co.readiness().items() if r}
        if bad:
            raise StartupAbort(S, f"stations not ready after arming: {bad}")
        self.p_floor = sp
        self.rep.measurements["vision_noise_m"] = self.noise_m
        self.rep.measurements["claw_on_floor_M"] = sp.p.tolist()

    # ---------------------------------------------------------- SLACK_TAKEUP
    def slack_takeup(self):
        cfg, ctx, S = self.cfg, self.ctx, "SLACK_TAKEUP"
        st = cfg.startup
        thr = max(st.onset_translation_m, st.onset_noise_k * self.noise_m)
        bearing_d = max(st.bearing_translation_m, 2 * thr)
        ctx.onsets = []
        for i, sid in enumerate(IDS):
            ref = self._still(state=S)
            mon = {"next": 0.0, "onset": None, "lost": 0.0, "max_disp": 0.0}

            def monitor(tau, i=i, ref=ref, mon=mon):
                now = ctx.now_s()
                if now < mon["next"]:
                    return None
                mon["next"] = now + st.frame_interval_s
                o = ctx.vision.observe()
                if not o.ok:
                    mon["lost"] += st.frame_interval_s
                    return f"marker lost ({o.reason})" if mon["lost"] > 1.0 else None
                mon["lost"] = 0.0
                disp = float(np.linalg.norm(o.p - ref.p))
                mon["max_disp"] = max(mon["max_disp"], disp)
                if mon["onset"] is None and disp >= thr:
                    mon["onset"] = float(ctx.co.positions()[i])
                if disp >= bearing_d:
                    return "onset"
                if ctx.claw.tilt() > st.max_tilt_rad:
                    return "tilt"
                return None

            ppu = ctx.ppu(i)
            delta = np.zeros(4)
            delta[i] = -st.max_slack_m[i] / ppu
            rate = st.probe_speed_m_s / ppu
            plan = plan_cable_move(ctx.co.positions(), delta, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                   label=f"slack {sid}")
            r = self._execute(plan, S, suspended=False, monitor=monitor)
            if r.reason != "onset":
                if r.ok:
                    raise StartupAbort(S, f"station {sid}: no taut onset within {st.max_slack_m[i] * 1e3:.0f} mm "
                                          "(cable unattached, wrong winding direction, or station order)")
                raise StartupAbort(S, f"station {sid}: {r.reason}")
            ctx.wait(st.settle_s)
            end = self._still(state=S)
            d = end.p - ref.p
            o = OnsetSample(i, float(ctx.co.positions()[i]), end.p, end.R, end.cov,
                            bearing=math.atan2(d[1], d[0]), bearing_from=ref.p.copy(),
                            bearing_sigma=st.bearing_sigma_rad)
            ctx.onsets.append(o)
            taken = -(o.P - plan.start[i]) * ppu
            self.rep.measurements[f"slack_{sid}_m"] = taken
            ctx.log(f"[startup] {sid} taut after {taken * 1e3:.1f} mm, slide {np.linalg.norm(d) * 1e3:.1f} mm "
                    f"toward {math.degrees(o.bearing):.0f} deg (marker frame)")
            back = np.zeros(4)
            back[i] = st.onset_backoff_m / ppu
            rb = self._execute(plan_cable_move(ctx.co.positions(), back, rate * 2, rate * 10,
                                               segment_s=cfg.motion.segment_s, label=f"backoff {sid}"),
                               S, suspended=False)
            if not rb.ok:
                raise StartupAbort(S, f"station {sid}: backoff {rb.reason}")
        # bearings vs anchor entries, then the first fit
        claw = np.array([0.5 * (o.p + o.bearing_from) for o in ctx.onsets])
        psi, cov, rms = align_from_bearings(ctx.priors, claw, [o.bearing for o in ctx.onsets],
                                            st.bearing_sigma_rad)
        self.rep.measurements["bearing_rms"] = rms
        if rms > st.bearing_rms_max:
            raise StartupAbort(S, f"slide directions disagree with the anchor entries (RMS {rms:.1f} sigma): "
                                  "check station order/wiring A-D and anchor coordinates")
        res = ctx.cal.fit([], ctx.onsets, psi_inits=[psi])
        ctx.apply_result(res, "onset")
        self.rep.measurements["L0_onset"] = res.L0.tolist()

    # ---------------------------------------------------------- INITIAL_LIFT
    def _packet(self, p_from_R, p_to_R, speed, label, state, monitor=None):
        ctx = self.ctx
        geo = ctx.model.geometry
        dL = geo.lengths(p_to_R) - geo.lengths(p_from_R)
        P = ctx.co.positions()
        newP = []
        for i, sid in enumerate(IDS):
            m = ctx.model.maps[sid]
            newP.append(m.position(m.length(P[i]) + dL[i]))
        delta = np.array(newP) - P
        if np.max(np.abs(delta)) < 0.5:
            return None
        rate = self._cable_rate(speed)
        plan = plan_cable_move(P, delta, rate, rate / 0.2, segment_s=self.cfg.motion.segment_s, label=label)
        return self._execute(plan, state, suspended=True, monitor=monitor)

    def initial_lift(self):
        cfg, ctx, S = self.cfg, self.ctx, "INITIAL_LIFT"
        st = cfg.startup
        sp = self._still(state=S)
        p0 = ctx.room_pose(sp)
        ctx.ledger.claw_supported = False          # durable BEFORE the first command that can lift
        ctx.persist()
        # bring all four to just-taut at the current pose (they were backed off)
        P = ctx.co.positions()
        target = ctx.model.positions_for(p0)
        rate = self._cable_rate(st.probe_speed_m_s * 2)
        drag = {"bad": None, "next": 0.0}

        def watch(tau):
            if ctx.now_s() < drag["next"]:
                return None
            drag["next"] = ctx.now_s() + st.frame_interval_s
            o = ctx.vision.observe()
            if o.ok and np.linalg.norm(o.p - sp.p) > max(3 * st.onset_translation_m, 0.01):
                drag["bad"] = float(np.linalg.norm(o.p - sp.p))
                return "claw dragged while tensioning"
            return None
        r = self._execute(plan_cable_move(P, target - P, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                          label="pretension"), S, suspended=False, monitor=watch)
        if not r.ok:
            raise StartupAbort(S, f"pretension: {r.reason} ({drag['bad']})")
        zf = -float(cfg.claw.lowest_point_body_m[2])
        lifted = 0.0
        cur = p0.copy()
        while True:
            if lifted >= st.max_lift_m:
                raise StartupAbort(S, f"no {st.target_clearance_m * 1e3:.0f} mm clearance after "
                                      f"{st.max_lift_m * 1e3:.0f} mm commanded lift", suspended=True)
            nxt = cur + [0, 0, st.lift_packet_m]
            r = self._packet(cur, nxt, st.probe_speed_m_s * 2, "lift", S)
            if r is not None and not r.ok:
                raise StartupAbort(S, f"lift packet stopped: {r.reason}", suspended=True)
            lifted += st.lift_packet_m
            cur = nxt
            ctx.wait(st.settle_s)
            sp2 = self._still(n=3, state=S, suspended=True)
            obs = ctx.room_pose(sp2)
            rise = obs[2] - p0[2]
            drift = float(np.linalg.norm(obs[:2] - p0[:2]))
            tilt = max(sp2.tilt_rad, ctx.claw.tilt())
            if drift > st.max_lateral_drift_m:
                raise StartupAbort(S, f"lateral drift {drift * 1e3:.0f} mm during lift", suspended=True)
            if tilt > st.max_tilt_rad:
                raise StartupAbort(S, f"tilt {math.degrees(tilt):.1f} deg during lift", suspended=True)
            if lifted - rise > st.lift_slack_budget_m:
                raise StartupAbort(S, f"claw rose {rise * 1e3:.0f} mm for {lifted * 1e3:.0f} mm commanded: "
                                      "a cable is slack/unattached or the model is badly wrong", suspended=True)
            if sp2.p[2] - zf >= st.target_clearance_m:
                self.rep.measurements["lift_commanded_m"] = lifted
                self.rep.measurements["lift_observed_m"] = float(rise)
                ctx.persist()
                return

    # ---------------------------------------------------- VISUAL_INITIALIZATION
    def _sample(self, kind, state):
        ctx = self.ctx
        ctx.wait(self.cfg.startup.settle_s)
        sp = self._still(n=self.cfg.calibration.noise_capture_frames, state=state, suspended=True)
        return PoseSample(ctx.co.positions().copy(), sp.p, sp.R, sp.cov, kind, ctx.now_s())

    # ------------------------------------------------------------ slack probe
    # Fraction of the measured slack's 1-sigma by which a probed cable is left on the slack side of its onset (so it
    # cannot pull the claw toward itself and loosen a neighbour). 0 = leave it just taut. Simulation showed no
    # difference (seeds 1, 2, single tag: residual truth slack of probed readings mean -0.28 mm, max 1.34 mm at 0
    # against max 0.78 / 1.20 mm at 0.5; verification/slack_probe_results.md), so the simplest choice stays.
    PROBE_MARGIN_SIGMA = 0.0
    # The claw moving this far from the reference during one cable's probe without a significant onset means the
    # vision or the response model cannot be trusted: abort (hold) rather than keep retracting.
    PROBE_MAX_DISP_M = 0.010

    def _probe_geometry(self, i, ref):
        """Predicted claw response to retracting cable ``i`` at the pose of ``ref`` and what the vision noise
        allows: (v, |v|, sigma_proj, rho) with ``v`` the response (marker frame, per metre of retraction),
        ``sigma_proj`` the 1-sigma of a differential position measurement along it (reference + one
        measurement, both averaged over the frames of ``ref``) and ``rho`` the over-retraction beyond the
        taut point at which the onset becomes detectable (max(floor, k sigma) / |v|)."""
        ctx, st = self.ctx, self.cfg.startup
        v = ctx.T_R_M[:3, :3].T @ probe_response(ctx.model.geometry, ctx.room_pose(ref), i)
        vn = float(np.linalg.norm(v))
        vhat = v / vn
        sig_proj = math.sqrt(float(vhat @ (2.0 * ref.cov) @ vhat))
        rho = max(st.probe_onset_translation_m, st.onset_noise_k * sig_proj) / vn
        return v, vn, sig_proj, rho

    def _probe_cable(self, i, ref, n_frames, state):
        """Retract cable ``i`` in small steps until the claw moves (taut onset), measure the slack, leave
        the cable just taut. ``ref`` is a still pose (``n_frames`` frames) with the cable as it is. Returns a
        record dict. Aborts (hold) when the cable never goes taut within ``probe_max_m``."""
        ctx, cfg = self.ctx, self.cfg
        st, sid = cfg.startup, IDS[i]
        q_room = ctx.room_pose(ref)
        v, vn, sig_proj, rho = self._probe_geometry(i, ref)
        rec = {"station": sid, "status": "ok", "response_per_m": vn, "detect_overshoot_m": rho,
               "sigma_proj_m": sig_proj, "frames": n_frames}
        rate = st.probe_speed_m_s
        r_arr, P_arr, C_arr = [0.0], [ref.p], [ref.cov]
        r, step, n_steps, a = 0.0, st.probe_step_m, 0, None
        while True:
            if r >= st.probe_max_m - 1e-9:
                raise StartupAbort(state, f"station {sid}: no taut onset within {st.probe_max_m * 1e3:.0f} mm of probe "
                                          f"retraction at claw {np.round(q_room, 3).tolist()} (cable detached or "
                                          "slipping on its spool, or the model is badly wrong)", suspended=True)
            h = min(step, st.probe_max_m - r)
            ppu = ctx.ppu(i)
            P_b = float(ctx.co.positions()[i])
            delta = np.zeros(4)
            delta[i] = -h / ppu
            plan = plan_cable_move(ctx.co.positions(), delta, rate / ppu, rate / ppu / 0.2,
                                   segment_s=cfg.motion.segment_s, label=f"probe {sid}")
            res = self._execute(plan, state, suspended=True)
            if not res.ok:
                raise StartupAbort(state, f"station {sid}: probe motion {res.reason}", suspended=True)
            r += (P_b - float(ctx.co.positions()[i])) * ppu
            n_steps += 1
            ctx.wait(st.probe_settle_s)
            sp = self._still(n=n_frames, state=state, suspended=True)
            r_arr.append(r)
            P_arr.append(sp.p)
            C_arr.append(sp.cov)
            a = hinge_analysis(r_arr, P_arr, C_arr, v, st.probe_response_sigma * vn, st.onset_noise_k,
                               st.probe_onset_translation_m)
            if a["detected"]:
                break
            moved = float(np.linalg.norm(sp.p - ref.p))
            if moved > self.PROBE_MAX_DISP_M:
                raise StartupAbort(state, f"station {sid}: claw moved {moved * 1e3:.1f} mm during the probe without a "
                                          "significant onset (vision or response model unreliable)", suspended=True)
            step = min(max(st.probe_step_m, 0.5 * r), st.probe_max_step_m)
        s_hat, sig_s = a["s"], a["sigma_s"]
        r_final = min(max(s_hat - self.PROBE_MARGIN_SIGMA * sig_s, 0.0), r)
        back = r - r_final
        if back > 0.5 * ctx.ppu(i):
            pb = np.zeros(4)
            pb[i] = back / ctx.ppu(i)
            rb = self._execute(plan_cable_move(ctx.co.positions(), pb, rate / ctx.ppu(i), rate / ctx.ppu(i) / 0.2,
                                               segment_s=cfg.motion.segment_s, label=f"probe back {sid}"),
                               state, suspended=True)
            if not rb.ok:
                raise StartupAbort(state, f"station {sid}: probe pay-out {rb.reason}", suspended=True)
        rec.update(slack_m=float(s_hat), sigma_m=float(sig_s), peak_m=float(r), final_m=float(r_final),
                   steps=n_steps, significance=float(a["sig"]), response_fit_per_m=float(np.linalg.norm(a["w"])))
        return rec

    def _probe_pose(self, state):
        """Probe the cables at the current (suspended) pose, one at a time, leaving each just taut.

        Vision decides what is possible: from a reference still pose, each cable's detection over-retraction
        ``rho`` is predicted; the frames per measurement are raised (up to ``probe_frames_max``) until ``rho`` is
        within ``probe_overshoot_max_m`` (this bounds the tension excursion on a taut cable); a cable that still
        does not make it is skipped (its reading keeps the fit's slack hypothesis selection). Up to
        ``probe_rounds`` rounds: later rounds re-probe a cable only when the claw has since moved toward its
        anchor by a detectable amount (a later probe loosened it). The caller restores the positions."""
        ctx, st = self.ctx, self.cfg.startup
        t0 = ctx.now_s()
        k = st.onset_noise_k
        recs = {}
        n_base = st.probe_frames
        ref = self._still(n=n_base, state=state, suspended=True)
        need = {}
        for i in range(4):
            _, _, _, rho = self._probe_geometry(i, ref)
            n_i = n_base if rho <= st.probe_overshoot_max_m else int(math.ceil(n_base * (rho / st.probe_overshoot_max_m) ** 2))
            if n_i <= st.probe_frames_max:
                need[i] = n_i
            else:
                recs[i] = {"station": IDS[i], "status": "skipped", "detect_overshoot_m": rho,
                           "reason": f"vision too noisy: detecting onset needs {rho * 1e3:.1f} mm of over-retraction "
                                     f"(> {st.probe_overshoot_max_m * 1e3:.1f} mm) even with {st.probe_frames_max} frames"}
        todo = sorted(need)
        n_pose = max(need.values(), default=n_base)
        n_rounds = 0
        if todo and n_pose > n_base:
            ref = self._still(n=n_pose, state=state, suspended=True)
        for rnd in range(st.probe_rounds if todo else 0):
            if not todo:
                break
            n_rounds += 1
            done_pose = {}                                        # cable -> still pose right after it was finished
            for i in todo:
                rec = self._probe_cable(i, ref, n_pose, state)
                rec["round"] = rnd
                if i in recs and recs[i].get("status") == "ok":
                    rec["slack_first_round_m"] = recs[i].get("slack_m")
                recs[i] = rec
                ref = self._still(n=n_pose, state=state, suspended=True)
                done_pose[i] = ref
            todo = []
            if rnd + 1 < st.probe_rounds:
                U = ctx.model.geometry.unit_vectors(ctx.room_pose(ref))
                Rm = ctx.T_R_M[:3, :3].T
                for i, pose in done_pose.items():
                    u = Rm @ U[i]
                    dist = float(u @ (ref.p - pose.p))            # motion toward anchor i since it was finished
                    thr = max(st.probe_onset_translation_m, k * math.sqrt(float(u @ (pose.cov + ref.cov) @ u)))
                    if dist >= thr:
                        todo.append(i)
        taut = np.array([recs[i]["status"] == "ok" for i in range(4)])
        sigma = np.array([recs[i].get("sigma_m", 0.0) * (1.0 + self.PROBE_MARGIN_SIGMA) if taut[i] else 0.0
                          for i in range(4)])
        slack = [recs[i].get("slack_m", float("nan")) for i in range(4)]
        return {"taut": taut, "sigma_m": sigma, "slack_m": slack, "rounds": n_rounds, "t_s": ctx.now_s() - t0,
                "frames": n_pose, "cables": {IDS[i]: recs[i] for i in range(4)}}

    def _restore_positions(self, P_target, state):
        """Back to the model-consistent motor positions the planner started from (pay-out only)."""
        ctx, cfg, st = self.ctx, self.cfg, self.cfg.startup
        delta = np.asarray(P_target, float) - ctx.co.positions()
        if np.max(np.abs(delta)) < 0.5:
            return
        ppus = np.array([ctx.ppu(j) for j in range(4)])
        rate = st.probe_speed_m_s / float(np.min(ppus))
        r = self._execute(plan_cable_move(ctx.co.positions(), delta, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                          label="probe restore"), state, suspended=True)
        if not r.ok:
            raise StartupAbort(state, f"probe restore: {r.reason}", suspended=True)

    def _sample_probed(self, kind, state):
        """A calibration sample, preceded by the slack probe when enabled (all cables just taut)."""
        if not self.cfg.startup.slack_probe:
            return self._sample(kind, state)
        ctx = self.ctx
        P_before = ctx.co.positions().copy()
        ctx.wait(self.cfg.startup.settle_s)
        rec = self._probe_pose(state)
        smp = self._sample(kind, state)
        smp.taut, smp.taut_sigma_m = rec["taut"], rec["sigma_m"]
        smp.probe = {k_: v for k_, v in rec.items() if k_ != "sigma_m"}
        smp.probe["sigma_m"] = rec["sigma_m"].tolist()
        smp.probe["taut"] = rec["taut"].tolist()
        self._restore_positions(P_before, state)
        self.probe_log.append(dict(smp.probe, kind=kind, state=state, z_m=float(smp.p[2])))
        return smp

    def visual_init(self):
        ctx, S = self.ctx, "VISUAL_INITIALIZATION"
        s = self._sample_probed("fit", S)
        ctx.samples = [s]
        res = ctx.cal.fit(ctx.samples, ctx.onsets, L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
        ctx.apply_result(res, "visual")
        self.rep.measurements["L0_visual"] = res.L0.tolist()

    # ------------------------------------------------------------ CALIBRATION
    def _feasible(self, q_R, R_M, min_z):
        ctx, cfg = self.ctx, self.cfg
        if q_R[2] < min_z:
            return False
        if ctx.ws.violations(ctx.model.geometry, q_R):
            return False
        t = tension_distribution(ctx.model.geometry, q_R, cfg.claw.mass_kg, t_min=cfg.motion.min_tension_n,
                                 t_max=cfg.motion.max_tension_n * 0.75,
                                 accel=(0.0, 0.0, cfg.motion.dynamic_accel_m_s2))
        if not t.feasible:
            return False
        T_M_B = make_T(R_M, to_marker(ctx.T_R_M, q_R))
        if self.study_board is not None:
            return self.study_board.visible(ctx.camera, ctx.T_B_C, T_M_B,
                                            min_side_px=cfg.camera.min_marker_pixels * 1.2, margin_px=30)
        return marker_visible(ctx.camera, ctx.T_B_C, T_M_B, cfg.marker.edge_m,
                              min_side_px=cfg.camera.min_marker_pixels * 1.2, margin_px=30)

    def _stage(self, name, center_R, half, n_fit, n_wit, R_M, min_z, grid):
        ctx, cfg = self.ctx, self.cfg
        cands = [q for q in box_candidates(center_R, half, grid) if self._feasible(q, R_M, min_z)]
        if len(cands) < n_fit + n_wit:
            raise StartupAbort("CALIBRATION", f"{name}: only {len(cands)} feasible visible poses "
                                              f"(need {n_fit + n_wit})", suspended=True)

        def cov_fn(qM):
            edge = cfg.marker.edge_m
            if self.study_board is not None:
                edge = self.study_board.edge_eff(ctx.camera, ctx.T_B_C, make_T(R_M, qM),
                                                 min_side_px=cfg.camera.min_marker_pixels * 1.2, margin_px=30)
            return predicted_vision_cov(ctx.camera, ctx.T_B_C, make_T(R_M, qM), edge)
        candM = [to_marker(ctx.T_R_M, q) for q in cands]
        here = to_marker(ctx.T_R_M, ctx.model.pose_from_positions(ctx.co.positions())[0])
        fitM, witM = design_excitation(ctx.cal, ctx.result, candM, n_fit, cov_fn=cov_fn,
                                       existing_M=[s.p for s in ctx.samples], start_M=here, n_witness=n_wit)
        for kind, pts in (("fit", fitM), ("witness", witM)):
            for qM in pts:
                q = to_room(ctx.T_R_M, qM)
                try:
                    plan = plan_line_from(ctx.model, ctx.co.positions(), q, ctx.lim, ws=ctx.ws,
                                          label=f"{name} {kind}")
                except PlanError as e:
                    raise StartupAbort("CALIBRATION", f"{name}: {e}", suspended=True)
                r = self._execute(plan, "CALIBRATION", suspended=True)
                if not r.ok:
                    raise StartupAbort("CALIBRATION", f"{name}: motion {r.reason}", suspended=True)
                ctx.samples.append(self._sample_probed(kind, "CALIBRATION"))

    def calibrate(self):
        ctx, cfg, S = self.ctx, self.cfg, "CALIBRATION"
        cc = cfg.calibration
        st = cfg.startup
        zf = -float(cfg.claw.lowest_point_body_m[2])
        min_z = zf + st.target_clearance_m
        R_M = ctx.samples[-1].R
        here = ctx.model.pose_from_positions(ctx.co.positions())[0]
        lb = np.asarray(cc.local_box_m)
        c_local = np.array([here[0], here[1], max(here[2], min_z + lb[2] + 0.01)])
        self._stage("local", c_local, lb, max(8, cc.min_samples // 2), max(2, cc.witness_samples // 2),
                    R_M, min_z, (5, 5, 3))
        res = ctx.cal.fit([s for s in ctx.samples if s.kind == "fit"], ctx.onsets, L0_init=ctx.result.L0,
                          psi_inits=[ctx.result.psi])
        wit = [s for s in ctx.samples if s.kind == "witness"]
        rep_local = ctx.cal.validate(res, wit)
        hard = [r for r in rep_local["reasons"] if not r.startswith(("prior-dominated", "only"))]
        if hard:
            raise StartupAbort(S, "local calibration rejected: " + "; ".join(hard), suspended=True)
        ctx.apply_result(res, "visual")
        self.rep.measurements["local"] = {"weak": [d for _, d in res.identifiability.weak],
                                          "witness_rms_m": rep_local["witness_rms_m"]}
        # Grow the excitation volume in steps, refitting between them, so the
        # model never extrapolates far: a model error at a commanded pose makes
        # the claw hang on three cables (the fourth goes slack).
        eb = np.asarray(cc.expanded_box_m)
        mk = to_room(ctx.T_R_M, [0, 0, 0])
        for name, scale, frac in (("intermediate", 0.45, 0.4), ("expanded", 1.0, 0.6)):
            half = np.maximum(eb * scale, lb)
            c = np.array([mk[0], mk[1], min_z + half[2] + 0.02])
            self._stage(name, c, half, max(6, int(cc.min_samples * frac)),
                        max(2, int(round(cc.witness_samples * frac))), R_M, min_z, (7, 7, 4))
            if name != "expanded":
                res = ctx.cal.fit([s for s in ctx.samples if s.kind == "fit"], ctx.onsets,
                                  L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
                ctx.apply_result(res, "visual")
        fit = [s for s in ctx.samples if s.kind == "fit"]
        wit = [s for s in ctx.samples if s.kind == "witness"]
        res = ctx.cal.fit(fit, ctx.onsets, L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
        vol = self._work_volume(res)
        report = ctx.cal.validate(res, wit, [to_marker(res.T_R_M, q) for q in vol])
        self.rep.measurements["calibration"] = {k: v for k, v in report.items()}
        ctx.save("calibration.json", {"result": res.to_jsonable(), "validation": report, "slack_probe": self.probe_log})
        if self.probe_log:
            self.rep.measurements["slack_probe"] = self._probe_summary()
        hard = [r for r in report["reasons"] if not r.startswith(("prior-dominated", "predicted length sigma"))]
        if hard:
            raise StartupAbort(S, "calibration rejected: " + "; ".join(hard), suspended=True)
        ctx.apply_result(res, "visual")
        self.rep.measurements["absolute_sigma_m"] = ctx.cal.absolute_sigma(res).tolist()
        ok_pts = [q for q in vol if np.max(ctx.cal.length_sigma(res, to_marker(res.T_R_M, q))) <= cc.length_sigma_max_m]
        ctx.validated_volume = np.array(ok_pts)
        ctx.save_model()
        if report["accepted"]:
            ctx.ledger.set_level("LOCAL_ONLY")      # VERIFIED only after the beads
        else:
            ctx.ledger.set_level("LOCAL_ONLY")
            self.rep.reasons.extend(report["reasons"])
        self.rep.measurements["validated_points"] = f"{len(ok_pts)}/{len(vol)}"

    def _probe_summary(self):
        L = self.probe_log
        ok = [(i, r) for r in L for i, c in enumerate(r["taut"]) if c]
        sl = np.array([r["slack_m"][i] for i, r in ok]) if ok else np.zeros(0)
        return {"poses": len(L), "time_s": float(sum(r["t_s"] for r in L)),
                "readings_probed": len(ok), "readings_skipped": 4 * len(L) - len(ok),
                "slack_median_m": float(np.median(sl)) if len(sl) else None,
                "slack_max_m": float(sl.max()) if len(sl) else None,
                "peak_retraction_max_m": float(max((c.get("peak_m", 0.0) for r in L for c in r["cables"].values()),
                                                   default=0.0))}

    def _work_volume(self, res, n=(5, 5, 3)):
        ctx, cfg = self.ctx, self.cfg
        lo, hi = ctx.ws.lo.copy(), ctx.ws.hi.copy()
        lo[2] += cfg.startup.target_clearance_m
        pts = box_candidates((lo + hi) / 2, (hi - lo) / 2, n)
        geo = Geometry(res.anchors_room, cfg.attachment_points())
        return [q for q in pts if tension_distribution(geo, q, cfg.claw.mass_kg, t_min=cfg.motion.min_tension_n,
                                                       t_max=cfg.motion.max_tension_n).feasible]

    # ------------------------------------------------- REFERENCE_VERIFICATION
    def verify_references(self):
        from .homing import BeadVerifier
        ctx, S = self.ctx, "REFERENCE_VERIFICATION"
        missing = self.cfg.missing("bead_verification")
        home = ctx.model.pose_from_positions(ctx.co.positions())[0]
        outcomes = {}
        if missing:
            self.rep.reasons.append(f"bead verification blocked: unmeasured {missing}")
        else:
            # absolute sigma + spool-model (payout scale) error over the distance
            # between the calibrated region and the bead (review M3)
            Lh = ctx.model.geometry.lengths(home)
            sig_abs = np.hypot(ctx.cal.absolute_sigma(ctx.result),
                               self.cfg.calibration.payout_scale_sigma * np.abs(Lh - np.array(
                                   [s.bead.trigger_length_m for s in self.cfg.stations])))
            bv = BeadVerifier(self.cfg, ctx.co, ctx.model, ctx.lim, ctx.ws, lambda q: sig_abs, log=ctx.log)
            for i, sid in enumerate(IDS):
                out = bv.run(i, p_home=home)
                outcomes[sid] = out
                if out.status == "FAULT":
                    ctx.ledger.invalidate(sid, f"bead verification fault: {out.reason}")
                    raise StartupAbort(S, f"station {sid}: {out.reason}", suspended=True)
                if out.status != "VERIFIED":
                    self.rep.reasons.append(f"bead {sid}: {out.reason}")
                    continue
                bead = self.cfg.stations[i].bead
                for P in out.captures:
                    ctx.cal.beads.append(BeadObs(i, P, bead.trigger_length_m,
                                                 math.hypot(bead.uncertainty_m, 1e-4)))
            if ctx.cal.beads:
                fit = [s for s in ctx.samples if s.kind == "fit"]
                res = ctx.cal.fit(fit, ctx.onsets, L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
                rep = ctx.cal.validate(res, [s for s in ctx.samples if s.kind == "witness"])
                hard = [r for r in rep["reasons"] if not r.startswith("prior-dominated")]
                if hard or res.norm_rms > self.cfg.calibration.norm_rms_max:
                    raise StartupAbort(S, "refit with bead references rejected: " + "; ".join(hard), suspended=True)
                ctx.apply_result(res, "visual+bead")
                for sid, o in outcomes.items():
                    if o.status == "VERIFIED":
                        i = IDS.index(sid)
                        ctx.ledger.set_reference(sid, ctx.co.links[sid].boot, res.L0[i],
                                                 float(ctx.cal.absolute_sigma(res)[i]), "bead", bead=True)
                self.rep.measurements["absolute_sigma_after_beads_m"] = ctx.cal.absolute_sigma(res).tolist()
        self.rep.measurements["beads"] = {s: {"status": o.status, "reason": o.reason, "sigma_m": o.sigma,
                                              "spread_m": o.spread_m,
                                              "residuals_m": [c.residual for c in o.checks]}
                                          for s, o in outcomes.items()}
        if outcomes and all(o.status == "VERIFIED" for o in outcomes.values()) and not self.rep.reasons:
            ctx.ledger.set_level("VERIFIED")
        else:
            ctx.ledger.set_level("LOCAL_ONLY")
        ctx.save("trust.json", {"level": ctx.ledger.level, "history": ctx.ledger.history})
