"""Top-level supervisor: operator commands, safety states, persistence.

States
------
DISARMED           stations not holding (or not yet armed). Entry state after a
                   host start unless the claw may be hanging.
STARTUP            the startup sequencer is running (sub-state in ``detail``).
READY              calibrated; trust level VERIFIED or LOCAL_ONLY.
TASK               a pickup/delivery task is running (sub-state in ``detail``).
PAUSED             motion held by the operator or a transient condition.
FAULT              motion stopped with references still trusted (e.g. a
                   lease/underrun coordinated stop) or a failure on the floor.
                   ``acknowledge`` clears station faults and re-checks.
RECOVERY_REQUIRED  the claw may be suspended and some reference is not trusted
                   (station reboot, tracking fault, host restart while
                   suspended). ``recover`` or ``lower``.
PARKED             claw verified on the floor by vision, cables slack, stations
                   still holding until a confirmed disarm.

Rules
-----
* Nothing auto-resumes after any reboot (host, station, claw).
* Stop != disable: stops are coordinated holds with torque kept. ``disarm``
  needs the typed confirmation AND a fresh vision check that the claw rests on
  the floor -- always; no stored flag can substitute for it.
* ``claw_supported`` fails closed: unknown = may be hanging. It is written
  durably (atomic + fsync) False before the first lift command and True only
  after a vision floor check.
* ``pause`` is accepted in every state and stops any motion in progress,
  including lowering and recovery moves.
* The calibrated model is persisted, so after a host restart with the claw
  hanging, stations whose boot epoch is unchanged keep their references and
  the claw can be recovered or lowered by software.
* The power strip is the emergency stop (IEC 60204-1 category 0): it drops the
  claw. Nobody stands under the workspace.
* Everything here runs over the ACTIVE stations (``ctx.ids``: four, or three in
  three-station mode). A station that is not active is not polled, configured,
  armed or disarmed, is not in the ledger, and its absence is not a fault.
"""
from __future__ import annotations

import json
import math
import threading
from pathlib import Path

import numpy as np

from .perception import cam_displacement, to_marker, to_room
from .protocol import Fault, State
from .startup import StartupAbort, StartupSequencer
from .trajectory import PlanError, plan_cable_move, plan_line_from
from .trust import TrustLedger, atomic_write

STATES = ("DISARMED", "STARTUP", "READY", "TASK", "PAUSED", "FAULT", "RECOVERY_REQUIRED", "PARKED")
COORDINATED_STOPS = (Fault.LEASE, Fault.UNDERRUN)

ALLOWED = {
    "start": ("DISARMED", "PARKED"),
    "pause": STATES,
    "resume": ("PAUSED",),
    "acknowledge": ("FAULT",),
    "recover": ("RECOVERY_REQUIRED", "FAULT"),
    "lower": ("READY", "PAUSED", "RECOVERY_REQUIRED", "FAULT"),
    "disarm": ("PARKED", "DISARMED", "FAULT", "RECOVERY_REQUIRED", "PAUSED"),
    "task": ("READY",),
}


class CommandRefused(Exception):
    pass


class Supervisor:
    def __init__(self, ctx, *, state_path=None, ledger_path=None):
        self.ctx = ctx
        self.state_path = Path(state_path) if state_path else None
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self.lock = threading.RLock()
        self.detail = ""
        self.reasons: list = []
        self.events: list = []
        self.paused_from = None
        self.state = "DISARMED"
        self._boots_seen = {}
        self._needs_restore = False
        ctx.persist = self._save
        prev = self._load()
        if prev is not None and not self.ctx.ledger.claw_supported:
            self._set("RECOVERY_REQUIRED", "host restarted while the claw may be suspended; "
                                          "verify the scene, then recover or lower")
        else:
            self._set("DISARMED", "host start (no automatic resume)")

    # ------------------------------------------------------------ plumbing
    def _set(self, state, why=""):
        assert state in STATES
        with self.lock:
            self.state = state
            self.events.append((round(self.ctx.now_s(), 3), state, why))
            self.ctx.log(f"[supervisor] -> {state} {why}")
            self._save()

    def _save(self):
        with self.lock:
            if self.state_path:
                atomic_write(self.state_path, json.dumps({
                    "state": self.state, "detail": self.detail, "claw_supported": self.ctx.ledger.claw_supported,
                    "level": self.ctx.ledger.level, "reasons": self.reasons[-10:]}, indent=2))
            if self.ledger_path:
                self.ctx.ledger.save(self.ledger_path)

    def _load(self):
        prev = None
        if self.ledger_path and self.ledger_path.exists():
            self.ctx.ledger = TrustLedger.load(self.ledger_path)
            self.ctx.ledger.restrict_to(self.ctx.ids)         # a ledger saved with another active set
        if self.state_path and self.state_path.exists():
            try:
                prev = json.loads(self.state_path.read_text())
            except ValueError:                       # unreadable -> treat as "may be hanging"
                prev = {"claw_supported": False}
                self.ctx.ledger.claw_supported = False
        if prev is not None and self.ctx.load_model():
            self._needs_restore = True
        return prev

    def _require(self, cmd):
        if self.state not in ALLOWED[cmd]:
            raise CommandRefused(f"'{cmd}' not allowed in {self.state}")

    def status(self) -> dict:
        lg = self.ctx.ledger
        return {"state": self.state, "detail": self.detail, "level": lg.level,
                "claw_supported": lg.claw_supported, "recovery_required": lg.recovery_required,
                "stations": {s: {"valid": st.valid, "bead_verified": st.bead_verified, "note": st.note,
                                 "state": State.NAMES.get((self.ctx.co.links[s].tel or {}).get("st")),
                                 "fault": Fault.NAMES.get((self.ctx.co.links[s].tel or {}).get("flt"))}
                             for s, st in lg.stations.items()},
                "reasons": self.reasons[-5:], "events": self.events[-20:]}

    # ------------------------------------------------------------ monitoring
    def poll(self):
        """Run continuously (service idle loop) and after every command: turns
        station reboots and latched faults into trust events and states."""
        co = self.ctx.co
        co.pump()
        self._restore_if_needed()
        invalidated, stopped = False, []
        for s in self.ctx.ids:
            ln = co.links[s]
            if ln.boot is not None and self._boots_seen.get(s) not in (None, ln.boot):
                self.ctx.ledger.on_boot_change(s, ln.boot)
                invalidated = True
            if ln.boot is not None:
                self._boots_seen[s] = ln.boot
            f = (ln.tel or {}).get("flt")
            if f in (None, Fault.NONE):
                continue
            if f in COORDINATED_STOPS:
                stopped.append(f"{s}: {Fault.NAMES[f]}")
            elif self.ctx.ledger.stations[s].valid:
                self.ctx.ledger.on_fault(s, f)
                invalidated = True
        if self.state in ("READY", "PAUSED", "TASK", "PARKED"):
            if invalidated:
                why = "station reference lost: " + "; ".join(
                    f"{s}: {st.note}" for s, st in self.ctx.ledger.stations.items() if not st.valid)
                self.reasons.append(why)
                self._set("FAULT" if self.ctx.ledger.claw_supported else "RECOVERY_REQUIRED", why)
            elif stopped:
                why = "coordinated stop latched (" + ", ".join(stopped) + "): acknowledge to clear"
                self.reasons.append(why)
                self._set("FAULT", why)

    def _restore_if_needed(self):
        """After a host restart: keep each persisted reference whose station
        still runs the same boot epoch (lease stops are benign)."""
        if not self._needs_restore:
            return
        links = self.ctx.co.links
        ids = self.ctx.ids
        if not all(links[s].boot is not None and links[s].tel is not None for s in ids):
            return
        boots = {s: links[s].boot for s in ids}
        faults = {s: (None if (links[s].tel or {}).get("flt") in COORDINATED_STOPS else links[s].tel.get("flt"))
                  for s in ids}
        self.ctx.ledger.restore_after_host_restart(boots, faults)
        self._boots_seen = dict(boots)
        self._needs_restore = False
        self._save()

    def _restore_stations(self):
        """Bring stations back to IDLE holding after stops/reboots: reconfigure
        rebooted ones, clear latched faults (positions are kept; the trust
        ledger has already invalidated what a fault made untrustworthy)."""
        co = self.ctx.co
        co.wait(300000)
        self.poll()
        for s in self.ctx.ids:
            ln = co.links[s]
            st = (ln.tel or {}).get("st")
            if st == State.FAULT:
                co.clear(s)
            if ln.boot_changed or st == State.OFF:
                co.configure([s])
                co.wait(100000)
                co.arm([s], sw_ok=False)
        co.wait(300000)
        return {s: r for s, r in co.readiness().items() if r}

    # ------------------------------------------------------------ commands
    def start(self):
        with self.lock:
            self._require("start")
            self._set("STARTUP", "operator start")
        seq = StartupSequencer(self.ctx)
        seq._enter = self._wrap_enter(seq._enter)
        rep = seq.run()
        self._boots_seen = {s: self.ctx.co.links[s].boot for s in self.ctx.ids}
        self.reasons.extend(rep.reasons)
        if rep.outcome == "READY":
            self.detail = ""
            if self.state != "PAUSED":                      # a pause pressed at the very end wins
                self._set("READY", f"level {self.ctx.ledger.level}")
        elif rep.outcome == "PAUSED":
            self.paused_from = ("STARTUP", rep.state)
            self._set("PAUSED", rep.reasons[-1] if rep.reasons else "")
        else:
            self._set("RECOVERY_REQUIRED" if not self.ctx.ledger.claw_supported else "FAULT",
                      rep.reasons[-1] if rep.reasons else "")
        return rep

    def _wrap_enter(self, fn):
        def enter(state, msg=""):
            self.detail = state
            fn(state, msg)
        return enter

    def pause(self, why="operator pause"):
        """Always accepted: holds whatever is moving (including lowering and
        recovery). Moving states become PAUSED; others keep their state."""
        self.ctx.co.request_pause(why)
        with self.lock:
            if self.state in ("STARTUP", "TASK", "READY"):
                self.paused_from = (self.state, self.detail)
                self._set("PAUSED", why)
            else:
                self.events.append((round(self.ctx.now_s(), 3), f"pause in {self.state}", why))

    def resume(self):
        """Nothing restarts by itself: a paused startup restarts from the
        safest valid step (floor -> SELF_CHECK; suspended -> visual model
        check), a paused task returns to READY."""
        self._require("resume")
        self.ctx.co.pause_requested = None
        bad = {s: r for s, r in self.ctx.co.readiness().items() if r}
        if bad:
            raise CommandRefused(f"stations not ready: {bad}")
        o = self.ctx.vision.observe()
        if not o.ok:
            raise CommandRefused(f"marker not visible: {o.reason}")
        src = (self.paused_from or ("READY", ""))[0]
        if src == "STARTUP" and self.ctx.ledger.claw_supported:
            self._set("DISARMED", "startup will restart from SELF_CHECK")
            return self.start()
        ok, why = self.visual_check()
        if not ok or self.ctx.ledger.level == "NONE" or self.ctx.result is None:
            self._set("RECOVERY_REQUIRED", why if not ok else "no validated model")
            return None
        self._set("READY", f"resumed ({why})")
        return None

    def acknowledge(self):
        self._require("acknowledge")
        bad = self._restore_stations()
        lg = self.ctx.ledger
        if lg.claw_supported:
            self._set("PARKED" if not bad else "DISARMED", "fault acknowledged")
            return
        ok, why = self.visual_check() if lg.all_valid() and not bad else (False, f"stations: {bad or 'invalid'}")
        if ok and lg.level != "NONE":
            self._set("READY", f"acknowledged ({why})")
        else:
            self._set("RECOVERY_REQUIRED", why)

    # ----------------------------------------------------------- recovery
    def visual_check(self, k=4.0):
        """Is the model consistent with what the camera sees right now? The
        model pose is solved slack-aware; the difference to vision is judged
        against the combined 1-sigma of both."""
        ctx = self.ctx
        if ctx.model is None:
            return False, "no model"
        sp, why = ctx.vision.still_pose(5, ctx.wait, max_wait_s=10.0)
        if sp is None:
            return False, why
        p_vis = ctx.room_pose(sp)
        try:
            p_mod = self._fk_slack_aware(ctx.co.positions(), p_vis, ctx.room_R(sp))
        except Exception as e:                      # spool range etc.
            return False, f"model evaluation failed: {e}"
        err = p_mod - p_vis
        R = ctx.T_R_M[:3, :3]
        C = R @ (sp.cov * sp.n) @ R.T + np.eye(3) * (ctx.cfg.calibration.length_sigma_m * 2) ** 2
        if ctx.result is not None:
            C += np.eye(3) * ctx.cal.position_sigma(ctx.result, to_marker(ctx.T_R_M, p_vis)) ** 2
        d = float(np.sqrt(err @ np.linalg.solve(C, err) / 3))
        return d <= k, f"model vs vision {np.linalg.norm(err) * 1e3:.1f} mm ({d:.1f} sigma)"

    def _fk_slack_aware(self, P, p0, R=None):
        """Model pose from the motor positions; ``R`` = the measured claw orientation (room frame) when known
        (spaced attachments: the lengths depend on it)."""
        from scipy.optimize import least_squares
        m = self.ctx.model
        L = m.lengths_from_positions(P)
        geo = m.geometry
        f = lambda q, keep: (geo.lengths(q, R) - L)[keep]
        n = len(L)
        sol = least_squares(f, p0, args=(list(range(n)),), method="lm")
        r = L - geo.lengths(sol.x, R)                    # + = model longer than span (slack)
        j = int(np.argmax(r))
        if n >= 4 and r[j] > 3 * self.ctx.cfg.calibration.length_sigma_m:      # three cables: no spare to drop
            keep = [i for i in range(n) if i != j]
            sol = least_squares(f, sol.x, args=(keep,), method="lm")
        return sol.x

    def _visual_rereference(self, bad, *, tauten=True):
        """New L0 for each station in ``bad`` from the camera. The claw hangs
        on the other three, so the recovered cable may be slack: it is then
        retracted slowly under vision until the claw starts to move (taut),
        bounded by 3 sigma + 10 mm, and referenced again (review M6)."""
        ctx, co, lg = self.ctx, self.ctx.co, self.ctx.ledger
        st = ctx.cfg.startup
        for s in bad:
            i = ctx.ids.index(s)
            sp, why = ctx.vision.still_pose(ctx.cfg.calibration.noise_capture_frames, ctx.wait, max_wait_s=20.0)
            if sp is None:
                raise CommandRefused(f"cannot see the marker: {why}")
            L0, sig = ctx.cal.visual_reference(ctx.result, i, co.positions()[i], sp.p, sp.R, sp.cov)
            ctx.model.maps[s] = ctx.model.maps[s].with_reference(L0)
            if tauten:
                # onset = camera-frame displacement from this still pose (one reference tilt), against the camera-frame noise
                thr = max(st.onset_translation_m, 4 * max(sp.spread_cam_m, 2e-4), 3 * math.sqrt(np.trace(sp.cov_cam * sp.n)))
                mon = {"next": 0.0}

                def moved(tau, ref=sp, mon=mon):
                    if ctx.now_s() < mon["next"]:
                        return None
                    mon["next"] = ctx.now_s() + st.frame_interval_s
                    o = ctx.vision.observe()
                    return "taut" if o.ok and np.linalg.norm(cam_displacement(o, ref)[0]) >= thr else None
                ppu = ctx.ppu(i)
                delta = np.zeros(len(ctx.ids))
                delta[i] = -(3 * sig + 0.010) / ppu
                rate = st.probe_speed_m_s / ppu
                r = co.execute(plan_cable_move(co.positions(), delta, rate, rate / 0.2,
                                               segment_s=ctx.cfg.motion.segment_s, label=f"tauten {s}"), monitor=moved)
                if r.reason != "taut":
                    raise CommandRefused(f"station {s}: no tension within {(3 * sig + 0.01) * 1e3:.0f} mm "
                                         f"({r.reason}); lower the claw")
                ctx.wait(st.settle_s)
                sp, why = ctx.vision.still_pose(ctx.cfg.calibration.noise_capture_frames, ctx.wait, max_wait_s=20.0)
                if sp is None:
                    raise CommandRefused(f"cannot see the marker: {why}")
                L0, sig = ctx.cal.visual_reference(ctx.result, i, co.positions()[i], sp.p, sp.R, sp.cov)
                ctx.model.maps[s] = ctx.model.maps[s].with_reference(L0)
            lg.set_reference(s, co.links[s].boot, L0, sig, "visual-recovery")
        if bad:
            lg.set_level("LOCAL_ONLY")
            ctx.save_model()

    def recover(self):
        """Re-establish trust while suspended: stations reconfigured/cleared/
        re-armed; at most one invalid station is re-referenced from the camera
        (LOCAL_ONLY until bead verification); then every station must be ready
        and the model must agree with vision. Otherwise only ``lower``."""
        self._require("recover")
        ctx, lg = self.ctx, self.ctx.ledger
        if ctx.result is None or ctx.model is None:
            raise CommandRefused("no calibrated model: use 'lower'")
        not_ready = self._restore_stations()
        if not_ready:
            raise CommandRefused(f"stations not ready: {not_ready}")
        bad = [s for s in ctx.ids if not lg.stations[s].valid]
        if len(bad) > 1:
            raise CommandRefused(f"{len(bad)} stations invalid ({bad}): use 'lower'")
        self._visual_rereference(bad)
        not_ready = {s: r for s, r in ctx.co.readiness().items() if r}
        ok, why = self.visual_check()
        if not ok or not_ready:
            why = why if not ok else f"stations not ready: {not_ready}"
            self.reasons.append(why)
            self._set("RECOVERY_REQUIRED", why)
            return False
        lg.recovery_required = False
        self._set("READY", f"recovered ({why}); level {lg.level}")
        return True

    def lower(self, speed=None):
        """Controlled descent to the floor, then slacken -> PARKED. Works with
        any number of invalid references (the final descent is equal-payout
        packets, which need no absolute lengths). Bounded: lateral drift and
        tilt are checked every packet, the packet count is limited, and PARKED
        is entered only if vision confirms the claw rests on the floor."""
        self._require("lower")
        ctx, cfg = self.ctx, self.ctx.cfg
        st = cfg.startup
        zf = -float(cfg.claw.lowest_point_body_m[2])
        not_ready = self._restore_stations()
        if not_ready:
            raise CommandRefused(f"stations not ready: {not_ready}")
        sp, why = ctx.vision.still_pose(3, ctx.wait, max_wait_s=20.0)
        if sp is None:
            raise CommandRefused(f"cannot see the marker: {why}")
        p = ctx.room_pose(sp)
        bad = [s for s in ctx.ids if not ctx.ledger.stations[s].valid]
        if ctx.model is not None and ctx.result is not None and len(bad) <= 1:
            if bad:
                ctx.log(f"[supervisor] lowering: provisional visual reference for {bad}")
                self._visual_rereference(bad)
            # back over the marker (the camera sees only ~0.2 m around it near
            # the floor), then down to 5 cm above the floor
            off = (sp.R @ ctx.T_B_C[:3, 3])[:2]
            mk = to_room(ctx.T_R_M, [0, 0, 0])[:2]
            xy = mk - ctx.T_R_M[:2, :2] @ off
            for tgt, lbl in ((np.array([xy[0], xy[1], max(p[2], zf + 0.30)]), "lower: over marker"),
                             (np.array([xy[0], xy[1], zf + 0.05]), "lower: descend")):
                try:
                    # recovery move: after a re-reference the claw often hangs on three
                    # cables, so allow a larger start offset (faded out over the move)
                    plan = plan_line_from(ctx.model, ctx.co.positions(), tgt, ctx.lim, ws=ctx.ws, allow_low=True,
                                          label=lbl, max_offset_m=0.02)
                except PlanError as e:
                    ctx.log(f"[supervisor] {lbl} refused ({e}); using cable packets")
                    break
                r = ctx.co.execute(plan)
                if not r.ok:
                    raise CommandRefused(f"{lbl} stopped: {r.reason}")
        # final part: equal payout packets until the camera sees no further descent
        sp0, why = ctx.vision.still_pose(3, ctx.wait, max_wait_s=20.0)
        if sp0 is None:
            raise CommandRefused(f"cannot see the marker: {why}")
        last, n_max = None, int(math.ceil((sp0.p[2] - zf + 0.05) / st.lift_packet_m)) + 10
        on_floor = False
        for _ in range(n_max):
            sp, why = ctx.vision.still_pose(3, ctx.wait, max_wait_s=20.0)
            if sp is None:
                raise CommandRefused(f"lost the marker while lowering: {why}")
            if np.linalg.norm(sp.p[:2] - sp0.p[:2]) > 2 * st.max_lateral_drift_m:
                raise CommandRefused("lateral drift while lowering: stopped (lower by another method)")
            if sp.tilt_rad > st.max_tilt_rad:
                raise CommandRefused("claw tilted while lowering: stopped")
            z = sp.p[2]
            if last is not None and last - z < 0.3 * st.lift_packet_m and z - zf < st.floor_height_tol_m:
                on_floor = True
                break
            last = z
            dP = np.array([st.lift_packet_m / ctx.ppu(i) for i in range(len(ctx.ids))])
            rate = st.probe_speed_m_s * 2 / min(ctx.ppu(i) for i in range(len(ctx.ids)))
            r = ctx.co.execute(plan_cable_move(ctx.co.positions(), dP, rate, rate / 0.2,
                                               segment_s=cfg.motion.segment_s, label="lower packet"))
            if not r.ok:
                raise CommandRefused(f"lowering stopped: {r.reason}")
        if not on_floor:
            self._set("RECOVERY_REQUIRED", "lowering ended without vision confirming the floor "
                                           "(resting on an object?)")
            raise CommandRefused(self.events[-1][2])
        dP = np.array([0.03 / ctx.ppu(i) for i in range(len(ctx.ids))])
        rate = st.probe_speed_m_s * 4 / min(ctx.ppu(i) for i in range(len(ctx.ids)))
        ctx.co.execute(plan_cable_move(ctx.co.positions(), dP, rate, rate / 0.2, segment_s=cfg.motion.segment_s,
                                       label="slacken"))
        ctx.ledger.claw_supported = True
        self._set("PARKED", "claw on the floor (vision), cables slack")

    def _floor_confirmed(self):
        sp, why = self.ctx.vision.still_pose(3, self.ctx.wait, max_wait_s=10.0)
        zf = -float(self.ctx.cfg.claw.lowest_point_body_m[2])
        return sp is not None and abs(sp.p[2] - zf) < self.ctx.cfg.startup.floor_height_tol_m

    def disarm(self, confirm: str):
        """Remove holding torque: the literal confirmation 'claw_supported'
        AND a fresh vision check that the claw rests on the floor. If the
        camera cannot confirm it, the answer is no (use 'lower' first; with a
        failed camera and the claw verifiably on the floor, the power strip is
        safe)."""
        self._require("disarm")
        if confirm != "claw_supported":
            raise CommandRefused("type 'claw_supported' to confirm the claw is resting on a support")
        if not self._floor_confirmed():
            raise CommandRefused("vision does not confirm the claw is on the floor: lower first")
        for s in self.ctx.ids:
            self.ctx.co.disarm(s, confirm)
        self.ctx.ledger.claw_supported = True
        self._set("DISARMED", "operator disarm (floor confirmed by vision)")

    # ------------------------------------------------------------- tasks
    def run_task(self, runner, *args, **kw):
        with self.lock:
            self._require("task")
            self._set("TASK", "task start")
        try:
            out = runner.run(*args, on_state=self._task_state, **kw)
        except StartupAbort as e:
            self.reasons.append(e.reason)
            self._set("PAUSED" if e.paused else "FAULT", e.reason)
            self.poll()
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
