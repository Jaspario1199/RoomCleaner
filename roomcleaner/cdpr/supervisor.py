"""Top-level supervisor: operator commands, safety states, persistence.

States
------
DISARMED           stations unpowered/disabled (or not yet armed). Claw must be
                   supported (on the floor). Entry state after ANY host start
                   when the claw is known to be supported.
STARTUP            the startup sequencer is running (sub-state in ``detail``).
READY              calibrated; trust level VERIFIED or LOCAL_ONLY.
TASK               a pickup/delivery task is running (sub-state in ``detail``).
PAUSED             motion held by the operator or a transient condition
                   (marker lost, claw silent). Holding torque on.
FAULT              something failed; motion held, holding torque on. Needs
                   ``acknowledge``.
RECOVERY_REQUIRED  the claw may be suspended and some reference is no longer
                   trusted (station reboot, tracking fault, host restart while
                   suspended). Only recovery commands are accepted.
PARKED             claw lowered onto the floor, cables slackened, stations
                   still armed (holding) until a confirmed disarm.

Rules
-----
* A reboot (host, station or claw) never auto-resumes a task or a startup.
* Stop != disable: every stop is a coordinated feed-hold with torque kept.
  Only ``disarm(confirm="claw_supported")`` removes torque, and only when the
  vision confirms the claw rests on the floor (or the operator explicitly
  confirms it is supported by other means).
* The power strip is the emergency stop (IEC 60204-1 category 0). It drops
  the claw: it is for emergencies, and nobody stands under the workspace.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .calibration import IDS
from .perception import to_room
from .protocol import Fault, State
from .startup import StartupAbort, StartupSequencer
from .trajectory import PlanError, plan_cable_move, plan_line_from

STATES = ("DISARMED", "STARTUP", "READY", "TASK", "PAUSED", "FAULT", "RECOVERY_REQUIRED", "PARKED")

ALLOWED = {
    "start": ("DISARMED", "PARKED"),
    "pause": ("STARTUP", "TASK", "READY"),
    "resume": ("PAUSED",),
    "acknowledge": ("FAULT",),
    "recover": ("RECOVERY_REQUIRED",),
    "lower": ("READY", "PAUSED", "RECOVERY_REQUIRED", "FAULT"),
    "disarm": ("PARKED", "DISARMED", "FAULT", "RECOVERY_REQUIRED"),
    "task": ("READY",),
}


class CommandRefused(Exception):
    pass


class Supervisor:
    def __init__(self, ctx, *, state_path=None, ledger_path=None):
        self.ctx = ctx
        self.state_path = Path(state_path) if state_path else None
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self.detail = ""
        self.reasons: list = []
        self.events: list = []
        self.paused_from = None
        self.state = "DISARMED"
        self._boots_seen = {}
        prev = self._load()
        if prev and not prev.get("claw_supported", True):
            # host restarted while the claw may hang: references are suspect
            self._set("RECOVERY_REQUIRED", "host restarted while the claw may be suspended; "
                                          "verify the scene, then recover or lower")
        else:
            self._set("DISARMED", "host start (no automatic resume)")

    # ------------------------------------------------------------ plumbing
    def _set(self, state, why=""):
        assert state in STATES
        self.state = state
        self.events.append((round(self.ctx.now_s(), 3), state, why))
        self.ctx.log(f"[supervisor] -> {state} {why}")
        self._save()

    def _save(self):
        if self.state_path:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({
                "state": self.state, "detail": self.detail, "claw_supported": self.ctx.ledger.claw_supported,
                "level": self.ctx.ledger.level, "reasons": self.reasons[-10:]}, indent=2))
        if self.ledger_path:
            self.ctx.ledger.save(self.ledger_path)

    def _load(self):
        if self.ledger_path and self.ledger_path.exists():
            from .trust import TrustLedger
            self.ctx.ledger = TrustLedger.load(self.ledger_path)
        if self.state_path and self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return None

    def _require(self, cmd):
        if self.state not in ALLOWED[cmd]:
            raise CommandRefused(f"'{cmd}' not allowed in {self.state}")

    def status(self) -> dict:
        lg = self.ctx.ledger
        return {"state": self.state, "detail": self.detail, "level": lg.level,
                "claw_supported": lg.claw_supported, "recovery_required": lg.recovery_required,
                "stations": {s: {"valid": st.valid, "bead_verified": st.bead_verified, "note": st.note}
                             for s, st in lg.stations.items()},
                "reasons": self.reasons[-5:], "events": self.events[-20:]}

    # ------------------------------------------------------------ monitoring
    def poll(self):
        """Call periodically while idle (READY/PAUSED/PARKED): turns station
        reboots and latched faults into trust events."""
        co = self.ctx.co
        co.pump()
        changed = False
        for s in IDS:
            ln = co.links[s]
            if ln.boot is not None and self._boots_seen.get(s) not in (None, ln.boot):
                self.ctx.ledger.on_boot_change(s, ln.boot)
                changed = True
            if ln.boot is not None:
                self._boots_seen[s] = ln.boot
            f = (ln.tel or {}).get("flt")
            if f not in (None, Fault.NONE) and self.ctx.ledger.stations[s].valid:
                self.ctx.ledger.on_fault(s, f)
                changed = True
        if changed and self.state in ("READY", "PAUSED", "TASK"):
            self.reasons.append("station reference lost: " + "; ".join(
                f"{s}: {st.note}" for s, st in self.ctx.ledger.stations.items() if not st.valid))
            self._set("RECOVERY_REQUIRED" if not self.ctx.ledger.claw_supported else "FAULT", self.reasons[-1])

    def _remember_boots(self):
        self._boots_seen = {s: self.ctx.co.links[s].boot for s in IDS}

    # ------------------------------------------------------------ commands
    def start(self):
        self._require("start")
        self._set("STARTUP", "operator start")
        seq = StartupSequencer(self.ctx)
        seq._enter = self._wrap_enter(seq._enter)
        rep = seq.run()
        self._remember_boots()
        self.reasons.extend(rep.reasons)
        if rep.outcome == "READY":
            self.detail = ""
            self._set("READY", f"level {self.ctx.ledger.level}")
        elif rep.outcome == "PAUSED":
            self.paused_from = ("STARTUP", rep.state)
            self._set("PAUSED", rep.reasons[-1] if rep.reasons else "")
        else:
            self._set("RECOVERY_REQUIRED" if rep.measurements.get("suspended") else "FAULT",
                      rep.reasons[-1] if rep.reasons else "")
        return rep

    def _wrap_enter(self, fn):
        def enter(state, msg=""):
            self.detail = state
            fn(state, msg)
        return enter

    def pause(self, why="operator pause"):
        self._require("pause")
        self.ctx.co.request_pause(why)
        self.paused_from = (self.state, self.detail)
        self._set("PAUSED", why)

    def resume(self):
        """Resume after a pause. Nothing restarts by itself: a paused startup
        restarts from the safest valid step (floor -> SELF_CHECK; suspended ->
        a visual re-check of the model), a paused task returns to READY."""
        self._require("resume")
        bad = {s: r for s, r in self.ctx.co.readiness().items() if r}
        if bad:
            raise CommandRefused(f"stations not ready: {bad}")
        o = self.ctx.vision.observe()
        if not o.ok:
            raise CommandRefused(f"marker not visible: {o.reason}")
        src = (self.paused_from or ("READY", ""))[0]
        if src == "STARTUP":
            if self.ctx.ledger.claw_supported:
                self._set("DISARMED", "startup will restart from SELF_CHECK")
                return self.start()
            ok, why = self.visual_check()
            if not ok:
                self._set("RECOVERY_REQUIRED", why)
                return None
            self._set("READY" if self.ctx.result is not None else "RECOVERY_REQUIRED", "resumed")
            return None
        self._set("READY", "resumed")
        return None

    def acknowledge(self):
        self._require("acknowledge")
        for s in IDS:
            if (self.ctx.co.links[s].tel or {}).get("st") == State.FAULT:
                self.ctx.co.clear(s)
        if self.ctx.ledger.claw_supported:
            self._set("PARKED" if any((self.ctx.co.links[s].tel or {}).get("st") == State.IDLE for s in IDS)
                      else "DISARMED", "fault acknowledged")
        else:
            self._set("RECOVERY_REQUIRED", "fault acknowledged while suspended")

    # ----------------------------------------------------------- recovery
    def visual_check(self, k=4.0):
        """Is the model consistent with what the camera sees right now?

        The model pose is solved from the cable lengths, dropping one clearly
        slack cable (the claw hangs on three whenever lengths are not exactly
        consistent); the difference to vision is judged against the combined
        1-sigma of both."""
        ctx = self.ctx
        if ctx.model is None:
            return False, "no model"
        sp, why = ctx.vision.still_pose(5, ctx.wait, max_wait_s=10.0)
        if sp is None:
            return False, why
        p_vis = ctx.room_pose(sp)
        try:
            p_mod = self._fk_slack_aware(ctx.co.positions(), p_vis)
        except Exception as e:                      # spool range etc.
            return False, f"model evaluation failed: {e}"
        err = p_mod - p_vis
        R = ctx.T_R_M[:3, :3]
        C = R @ (sp.cov * sp.n) @ R.T + np.eye(3) * (ctx.cfg.calibration.length_sigma_m * 2) ** 2
        if ctx.result is not None:
            from .perception import to_marker
            C += np.eye(3) * ctx.cal.position_sigma(ctx.result, to_marker(ctx.T_R_M, p_vis)) ** 2
        d = float(np.sqrt(err @ np.linalg.solve(C, err) / 3))
        msg = f"model vs vision {np.linalg.norm(err) * 1e3:.1f} mm ({d:.1f} sigma)"
        return d <= k, msg

    def _fk_slack_aware(self, P, p0):
        from scipy.optimize import least_squares
        m = self.ctx.model
        L = m.lengths_from_positions(P)
        geo = m.geometry
        f = lambda q, keep: (geo.lengths(q) - L)[keep]
        sol = least_squares(f, p0, args=(list(range(4)),), method="lm")
        r = L - geo.lengths(sol.x)                       # + = model longer than span (slack)
        j = int(np.argmax(r))
        if r[j] > 3 * self.ctx.cfg.calibration.length_sigma_m:
            keep = [i for i in range(4) if i != j]
            sol = least_squares(f, sol.x, args=(keep,), method="lm")
        return sol.x

    def _visual_rereference(self, bad):
        ctx, co, lg = self.ctx, self.ctx.co, self.ctx.ledger
        for s in bad:
            if co.links[s].boot_changed or (co.links[s].tel or {}).get("st") == State.OFF:
                co.configure([s])
            if (co.links[s].tel or {}).get("st") == State.FAULT:
                co.clear(s)
            co.wait(100000)
            co.arm([s], sw_ok=False)
        co.wait(200000)
        for s in bad:
            i = IDS.index(s)
            sp, why = ctx.vision.still_pose(ctx.cfg.calibration.noise_capture_frames, ctx.wait, max_wait_s=20.0)
            if sp is None:
                raise CommandRefused(f"cannot see the marker: {why}")
            L0, sig = ctx.cal.visual_reference(ctx.result, i, co.positions()[i], sp.p, sp.R, sp.cov)
            ctx.model.maps[s] = ctx.model.maps[s].with_reference(L0)
            lg.set_reference(s, co.links[s].boot, L0, sig, "visual-recovery")
        if bad:
            lg.set_level("LOCAL_ONLY")

    def recover(self):
        """Re-establish invalid station references while suspended.

        Rebooted/faulted stations are reconfigured, cleared and re-armed, then
        their L0 is re-derived from the camera (the other cables must still be
        trusted). Recovered stations are LOCAL_ONLY until bead verification.
        If more than one station is invalid, or the model disagrees with
        vision, the only offered path is ``lower``."""
        self._require("recover")
        ctx, co, lg = self.ctx, self.ctx.co, self.ctx.ledger
        bad = [s for s in IDS if not lg.stations[s].valid]
        if ctx.result is None or ctx.model is None:
            raise CommandRefused("no calibrated model: lower the claw by hand-guided procedure, then start")
        if len(bad) > 1:
            raise CommandRefused(f"{len(bad)} stations invalid ({bad}): use 'lower'")
        self._visual_rereference(bad)
        ok, why = self.visual_check()
        if not ok:
            self.reasons.append(why)
            self._set("RECOVERY_REQUIRED", why)
            return False
        lg.recovery_required = False
        self._remember_boots()
        self._set("READY", f"recovered ({why}); level {lg.level}")
        return True

    def lower(self, speed=None):
        """Controlled descent to the floor, then slacken all cables -> PARKED.
        Vertical packets with vision; stops when the claw stops descending."""
        self._require("lower")
        ctx, cfg = self.ctx, self.ctx.cfg
        st = cfg.startup
        zf = -float(cfg.claw.lowest_point_body_m[2])
        speed = speed or st.probe_speed_m_s * 4
        sp, why = ctx.vision.still_pose(3, ctx.wait, max_wait_s=20.0)
        if sp is None:
            raise CommandRefused(f"cannot see the marker: {why}")
        p = ctx.room_pose(sp)
        bad = [s for s in IDS if not ctx.ledger.stations[s].valid]
        if bad and ctx.result is not None:
            ctx.log(f"[supervisor] lowering: provisional visual reference for {bad}")
            self._visual_rereference(bad)
        if ctx.model is not None and ctx.result is not None:
            # back over the marker (the camera sees only ~0.2 m around it near the
            # floor), then down to 5 cm above the floor
            off = (sp.R @ ctx.T_B_C[:3, 3])[:2]
            mk = to_room(ctx.T_R_M, [0, 0, 0])[:2]
            R2 = ctx.T_R_M[:2, :2]
            xy = mk - R2 @ off
            for tgt, lbl in ((np.array([xy[0], xy[1], max(p[2], zf + 0.30)]), "lower: over marker"),
                             (np.array([xy[0], xy[1], zf + 0.05]), "lower: descend")):
                try:
                    plan = plan_line_from(ctx.model, ctx.co.positions(), tgt, ctx.lim, ws=ctx.ws, allow_low=True,
                                          check_tension=False, label=lbl)
                except PlanError as e:
                    ctx.log(f"[supervisor] {lbl} refused ({e}); using cable packets")
                    break
                r = ctx.co.execute(plan)
                if not r.ok:
                    raise CommandRefused(f"{lbl} stopped: {r.reason}")
        # final part: equal payout packets until the camera sees no further descent
        last = None
        for _ in range(400):
            sp, why = ctx.vision.still_pose(3, ctx.wait, max_wait_s=20.0)
            if sp is None:
                raise CommandRefused(f"lost the marker while lowering: {why}")
            z = sp.p[2]
            if last is not None and last - z < 0.3 * st.lift_packet_m and z - zf < st.floor_height_tol_m:
                break
            last = z
            dP = np.array([st.lift_packet_m / ctx.ppu(i) for i in range(4)])
            rate = st.probe_speed_m_s * 2 / min(ctx.ppu(i) for i in range(4))
            r = ctx.co.execute(plan_cable_move(ctx.co.positions(), dP, rate, rate / 0.2,
                                               segment_s=cfg.motion.segment_s, label="lower packet"))
            if not r.ok:
                raise CommandRefused(f"lowering stopped: {r.reason}")
        # slacken
        dP = np.array([0.03 / ctx.ppu(i) for i in range(4)])
        rate = st.probe_speed_m_s * 4 / min(ctx.ppu(i) for i in range(4))
        ctx.co.execute(plan_cable_move(ctx.co.positions(), dP, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                       label="slacken"))
        ctx.ledger.claw_supported = True
        self._set("PARKED", "claw on the floor, cables slack")

    def disarm(self, confirm: str):
        """Remove holding torque. Requires the literal confirmation
        'claw_supported' AND (vision shows the claw on the floor OR the state
        already records it as supported)."""
        self._require("disarm")
        if confirm != "claw_supported":
            raise CommandRefused("type 'claw_supported' to confirm the claw is resting on a support")
        if not self.ctx.ledger.claw_supported:
            o = self.ctx.vision.observe()
            zf = -float(self.ctx.cfg.claw.lowest_point_body_m[2])
            if not (o.ok and abs(o.p[2] - zf) < self.ctx.cfg.startup.floor_height_tol_m):
                raise CommandRefused("vision does not confirm the claw is on the floor: lower first")
        for s in IDS:
            self.ctx.co.disarm(s, confirm)
        self._set("DISARMED", "operator disarm")

    # ------------------------------------------------------------- tasks
    def run_task(self, runner, *args, **kw):
        self._require("task")
        self._set("TASK", "task start")
        try:
            out = runner.run(*args, on_state=self._task_state, **kw)
        except StartupAbort as e:
            self.reasons.append(e.reason)
            self._set("PAUSED" if e.paused else "FAULT", e.reason)
            return None
        self.poll()
        if self.state == "TASK":
            self.detail = ""
            if out.get("pause"):
                self.paused_from = ("TASK", "")
                self._set("PAUSED", out["pause"])
            else:
                self._set("READY", f"task finished: {out.get('summary', '')}")
        return out

    def _task_state(self, s, msg=""):
        self.detail = s
        self.events.append((round(self.ctx.now_s(), 3), f"TASK/{s}", msg))
