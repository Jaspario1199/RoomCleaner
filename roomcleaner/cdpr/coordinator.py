"""Synchronized execution of a Plan on all ACTIVE stations (four; three in three-station mode: ``ids`` defaults to
``cfg.ids``, an inactive station has no link and is never addressed).

Readiness gate (all must hold before a motion starts):
  * every station: fresh telemetry, no fault, IDLE (armed, holding), same boot
    epoch as when it was configured, config hash = what the host pushed,
    encoder valid, commanded position == the plan's start position;
  * every station's clock uncertainty within ``faults.clock_uncertainty_max_s``.

Execution:
  * one shared start time T0 (host clock) = now + start_lead, converted to each
    station's clock; segments carry station-local times;
  * segments streamed so each station always holds ``lookahead_s`` of path;
    the first window must be acknowledged by every station before T0 or the
    motion is cancelled before anyone moves;
  * any NACK, fault, stale/rebooted station, peer-originated hold, or operator
    pause -> the host broadcasts HOLD at the current path time + a small lead
    so every station decelerates along the same path; the result reports why;
  * a reference capture (bead) is collected from station events.

The coordinator never replays missed steps and never pays out a cable to
"recover" from a fault; recovery is a separate, explicit operator/sequencer
decision (see supervisor.py).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .protocol import Fault, State
from .station_link import StationLink
from .trajectory import Plan
from .trust import tracking_fault_detail


class RealRuntime:
    def now_us(self) -> float:
        return time.monotonic() * 1e6

    def wait(self, dt_us: float) -> None:
        time.sleep(dt_us / 1e6)


@dataclass
class MotionResult:
    ok: bool
    reason: str = ""
    motion_id: int = -1
    final_pos: dict = field(default_factory=dict)
    captures: dict = field(default_factory=dict)
    releases: dict = field(default_factory=dict)
    held_by: str | None = None
    stopped_tau_us: float | None = None


class CoordinatorError(RuntimeError):
    pass


class Coordinator:
    def __init__(self, cfg, transport, runtime, ids=None):
        self.cfg = cfg
        self.tx = transport
        self.rt = runtime
        self.ids = tuple(cfg.ids if ids is None else ids)
        self.links = {s: StationLink(s) for s in self.ids}
        self.motion_id = int(runtime.now_us()) % 100000 * 10
        self.next_sync = 0.0
        self.next_ping = 0.0
        self.pause_requested: str | None = None
        self.last_sent = {s: -1e18 for s in self.ids}   # host time of the last datagram to each station
        self.log: list[str] = []
        f = cfg.faults
        self.tel_max_age = f.telemetry_max_age_s * 1e6
        self.clock_budget = f.clock_uncertainty_max_s * 1e6
        self.lease_us = f.lease_s * 1e6

    # ----------------------------------------------------------- plumbing
    def _log(self, s):
        self.log.append(f"{self.rt.now_us() / 1e6:10.3f} {s}")

    def pump(self) -> None:
        now = self.rt.now_us()
        for src, msg in self.tx.recv():
            if src in self.links:
                self.links[src].ingest(msg, now)
        if now >= self.next_sync:
            self.next_sync = now + self.cfg.faults.sync_interval_s * 1e6
            for s in self.ids:
                h = int(self.rt.now_us())
                self.links[s].sync_pending[h] = True
                if len(self.links[s].sync_pending) > 20:
                    self.links[s].sync_pending.pop(next(iter(self.links[s].sync_pending)))
                self._send(s, {"t": "sync", "h": h})
        if now >= self.next_ping:
            self.next_ping = now + min(self.lease_us / 4, 20000)
            self._send("*", {"t": "ping"})

    def _send(self, dest, msg):
        self.tx.send(dest, msg)
        now = self.rt.now_us()
        for s in (self.ids if dest == "*" else [dest]):
            self.last_sent[s] = now

    def wait(self, us: float) -> None:
        end = self.rt.now_us() + us
        while self.rt.now_us() < end:
            self.rt.wait(1000)
            self.pump()

    def wait_for(self, pred, timeout_s: float, what: str):
        end = self.rt.now_us() + timeout_s * 1e6
        while True:
            self.pump()
            r = pred()
            if r:
                return r
            if self.rt.now_us() > end:
                raise CoordinatorError(f"timeout waiting for {what}")
            self.rt.wait(1000)

    def request(self, sid, msg, re, timeout_s=1.0, retry_s=0.1):
        """Send an idempotent command, resending until acknowledged."""
        self.links[sid].take_acks(re)
        end = self.rt.now_us() + timeout_s * 1e6
        while self.rt.now_us() < end:
            self._send(sid, msg)
            try:
                return self.wait_for(lambda: self.links[sid].take_acks(re), retry_s, f"{re} ack {sid}")[0]
            except CoordinatorError:
                continue
        raise CoordinatorError(f"no {re} acknowledgement from station {sid}")

    # ------------------------------------------------------- bring-up
    def configure(self, sids=None) -> None:
        from .protocol import params_hash
        for s in sids or self.ids:
            p = self.cfg.station_firmware_params(s)
            missing = [k for k, v in p.items() if v is None]
            if missing:
                raise CoordinatorError(f"station {s}: unmeasured firmware params {missing}")
            ack = self.request(s, {"t": "cfg", "p": p}, "cfg")
            if not ack["ok"] or ack.get("hash") != params_hash(p):
                raise CoordinatorError(f"station {s} rejected config: {ack.get('why')}")
            self.links[s].expected_hash = ack["hash"]
            self.links[s].boot_changed = False
            self._log(f"{s} configured hash={ack['hash']:08x} boot={self.links[s].boot}")

    def arm(self, sids=None, *, sw_ok=False) -> None:
        for s in sids or self.ids:
            ack = self.request(s, {"t": "arm", "sw_ok": sw_ok}, "arm")
            if not ack["ok"]:
                raise CoordinatorError(f"station {s} refused ARM: {ack.get('why')}")
            self._log(f"{s} armed")

    def wait_synced(self, timeout_s=3.0):
        self.wait_for(lambda: all(self.links[s].clock.uncertainty(self.rt.now_us()) <= self.clock_budget
                                  and self.links[s].fresh(self.rt.now_us(), self.tel_max_age)
                                  for s in self.ids), timeout_s, "clock sync + telemetry")

    def clear(self, sid) -> bool:
        ack = self.request(sid, {"t": "clear"}, "clear")
        return bool(ack["ok"])

    def disarm(self, sid, confirm: str) -> bool:
        key = (self.links[sid].tel or {}).get("dk")
        if key is None:
            raise CoordinatorError(f"station {sid}: no telemetry yet (disarm key unknown)")
        ack = self.request(sid, {"t": "disarm", "confirm": confirm, "k": key}, "disarm")
        return bool(ack["ok"])

    # ---------------------------------------------------------- queries
    def readiness(self) -> dict:
        now = self.rt.now_us()
        out = {}
        for s in self.ids:
            r = self.links[s].health(now, self.tel_max_age, self.clock_budget)
            st = self.links[s].state
            if st is not None and st != State.IDLE:
                r.append(f"state {State.NAMES.get(st, st)}")
            out[s] = r
        return out

    def positions(self) -> np.ndarray:
        return np.array([self.links[s].pos for s in self.ids], float)

    def faults(self) -> dict:
        return {s: (self.links[s].tel or {}).get("flt") for s in self.ids}

    def request_pause(self, reason="operator pause"):
        self.pause_requested = reason

    # ---------------------------------------------------------- motion
    def execute(self, plan: Plan, *, stop_on_capture=True, timeout_s=None, monitor=None) -> MotionResult:
        """Run one synchronized motion. ``monitor(tau_s)`` (optional) is polled
        while moving; returning a string stops every station with a coordinated
        feed-hold at the same path point (e.g. vision saw the claw move).

        Any exception on the host side still stops the stations (hold, resent
        until every station reports stopped) before it propagates."""
        if self.pause_requested:                 # a pause pressed between motions holds the next one
            why = f"paused: {self.pause_requested}"
            self.pause_requested = None
            return MotionResult(False, why)
        self._active = None
        try:
            return self._execute(plan, stop_on_capture=stop_on_capture, timeout_s=timeout_s, monitor=monitor)
        except BaseException:
            if self._active is not None:
                mid, T0 = self._active
                tau = max(self.rt.now_us() - T0, 0) + 20000
                self._abort(mid, tau, "host exception")
                end = self.rt.now_us() + 300000
                while self.rt.now_us() < end and not self._all_stopped(mid):
                    self.rt.wait(1000)
                    try:
                        self.pump()
                    except Exception:
                        pass
                    self._resend_holds(mid)
            raise
        finally:
            self._active = None

    def _all_stopped(self, mid):
        return all(self.links[s].tel is not None and self.links[s].tel["st"] not in (State.RUN, State.HOLD)
                   for s in self.ids)

    def _resend_holds(self, mid):
        """H1: a hold is a datagram that can be lost. While any station still
        reports RUN for this motion, resend it every 20 ms (escalation logged
        after 300 ms)."""
        h = getattr(self, "_hold", None)
        if h is None or h[0] != mid:
            return
        now = self.rt.now_us()
        for s in self.ids:
            tel = self.links[s].tel or {}
            if tel.get("m") == mid and tel.get("st") == State.RUN and now - h[2].get(s, -1e18) >= 20000:
                self._send(s, {"t": "hold", "m": mid, "tau": int(h[1])})
                h[2][s] = now
                if now - h[3] > 300000 and s not in h[4]:
                    h[4].add(s)
                    self._log(f"station {s} still running {(now - h[3]) / 1e3:.0f} ms after hold")

    def _execute(self, plan, *, stop_on_capture, timeout_s, monitor):
        rd = self.readiness()
        bad = {s: r for s, r in rd.items() if r}
        if bad:
            return MotionResult(False, f"not ready: {bad}")
        start = self.positions()
        if np.any(np.abs(start - np.round(plan.start)) > 0.5):
            return MotionResult(False, f"start mismatch: stations at {start.tolist()}, plan {np.round(plan.start).tolist()}")
        if plan.is_noop:
            # "already there" (trajectory.NOOP_CABLE_M): the same readiness and start checks as a real motion, but nothing
            # to send, so no motion id is consumed and no station leaves IDLE. A pause request was already honoured above.
            self._log(f"motion '{plan.label}': already at the target, nothing sent")
            return MotionResult(True, "completed: already at the target (no motion)",
                                final_pos={s: self.links[s].pos for s in self.ids})
        self.motion_id += 1
        mid = self.motion_id
        lead = self.cfg.motion.start_lead_s * 1e6
        T0 = self.rt.now_us() + lead
        self._active = (mid, T0)
        segs = {}
        for j, s in enumerate(self.ids):
            t0l = self.links[s].clock.to_local(T0)
            segs[s] = [dict(m, m=mid) for m in plan.segments(j, t0l)]
            self.links[s].take_acks("seg", m=mid)
            self.links[s].take_events()
        sent = {s: 0 for s in self.ids}
        acked = {s: set() for s in self.ids}
        sent_at = {s: {} for s in self.ids}
        look = self.cfg.motion.lookahead_s * 1e6
        res = MotionResult(False, motion_id=mid)
        self._log(f"motion {mid} '{plan.label}' {plan.duration:.2f}s start in {lead / 1e3:.0f} ms")

        def feed():
            tau_now = self.rt.now_us() - T0
            for s in self.ids:
                while sent[s] < len(segs[s]):
                    seg = segs[s][sent[s]]
                    seg_tau = sum(x["d"] for x in segs[s][: sent[s]])
                    if seg_tau > tau_now + look:
                        break
                    self._send(s, seg)
                    sent_at[s][sent[s]] = self.rt.now_us()
                    sent[s] += 1
            # retransmit anything not acknowledged within 40 ms (lost datagram)
            now_ = self.rt.now_us()
            for s in self.ids:
                for k, t_sent in list(sent_at[s].items()):
                    if k not in acked[s] and now_ - t_sent > 40000:
                        self._send(s, segs[s][k])
                        sent_at[s][k] = now_

        def collect_acks():
            for s in self.ids:
                for a in self.links[s].take_acks("seg", m=mid):
                    if not a["ok"]:
                        return f"station {s} rejected segment {a.get('i')}: {a.get('why')}"
                    acked[s].add(a.get("i"))
            return None

        feed()
        # all first-window segments must be acknowledged before T0
        while self.rt.now_us() < T0 - 20000:
            self.rt.wait(1000)
            self.pump()
            why = collect_acks()
            if why:
                self._abort(mid, 0, why)
                res.reason = why
                return self._finish(res, mid)
            feed()
            if all(len(acked[s]) >= sent[s] for s in self.ids):
                break
        if not all(len(acked[s]) >= sent[s] for s in self.ids):
            why = f"start window not acknowledged: { {s: (len(acked[s]), sent[s]) for s in self.ids} }"
            self._abort(mid, 0, why)
            res.reason = why
            return self._finish(res, mid)

        done = set()
        deadline = T0 + (plan.duration + 2.0 + (timeout_s or 0)) * 1e6
        holding_reason = None
        while True:
            self.rt.wait(1000)
            self.pump()
            now = self.rt.now_us()
            tau = now - T0
            if holding_reason is None:
                feed()
                why = collect_acks()
                hold_at = max(tau, 0) + 20000
                if why is None:
                    why, lost = self._check_running(now)
                    if lost is not None:
                        # the unreachable station will stop itself when its lease
                        # expires; stop everyone else at that same path time
                        # The link broke about when its last telemetry was sent; it last
                        # heard us at most one keep-alive interval earlier.
                        lat = self.links[lost].clock.unc_base if self.links[lost].clock.ready else 2000
                        broke = self.links[lost].tel_host_t - lat
                        hold_at = max(hold_at, broke - 10000 + self.lease_us - T0)
                if why is None and self.pause_requested:
                    why = f"paused: {self.pause_requested}"
                    self.pause_requested = None
                peer = self._peer_holds(mid)
                if why is None and peer:
                    why = f"hold originated by station {peer}"
                    res.held_by = peer
                if why is None and monitor is not None and tau > 0:
                    try:
                        why = monitor(tau / 1e6)
                    except Exception as e:            # a failing check is a reason to stop
                        why = f"monitor error: {type(e).__name__}: {e}"
                    if why:
                        res.held_by = "monitor"
                caps = self._collect_events(mid, res)
                if why is None and caps and stop_on_capture:
                    why = "reference captured"
                if why:
                    holding_reason = why
                    self._abort(mid, hold_at, why)
            else:
                self._collect_events(mid, res)
                self._resend_holds(mid)
            for s in self.ids:
                for e in self.links[s].take_events():
                    if e.get("m") == mid and e.get("k") in ("done", "hold"):
                        done.add(s)
                        res.final_pos[s] = e.get("pos")
                        if e.get("k") == "hold":
                            res.stopped_tau_us = e.get("tau")
                    elif e.get("k") == "fault":
                        self._log(f"{s} fault event {self._fault_name(s, e.get('f'))}")
                        if holding_reason is None:
                            holding_reason = f"station {s} fault {self._fault_name(s, e.get('f'))}"
                            self._abort(mid, max(tau, 0) + 20000, holding_reason)
                        done.add(s)
                        res.final_pos[s] = e.get("pos")
                    elif e.get("k") in ("capture", "release"):
                        (res.captures if e["k"] == "capture" else res.releases)[s] = e
            # Telemetry is repeated every 20 ms, so it is the authoritative
            # (loss-tolerant) source for completion, final position and captures.
            for s in self.ids:
                tel = self.links[s].tel
                if tel and tel.get("m") == mid and tau > 0 and tel["st"] in (State.IDLE, State.FAULT, State.OFF):
                    done.add(s)
                    res.final_pos[s] = tel["pos"]
                    cap = tel.get("cap")
                    if cap and cap.get("m") == mid and cap.get("confirmed") and s not in res.captures:
                        res.captures[s] = dict(cap, k="capture")
                        if holding_reason is None and stop_on_capture:
                            holding_reason = "reference captured"
                            self._abort(mid, tau + 20000, holding_reason)
            if len(done) == len(self.ids):
                break
            if now > deadline:
                holding_reason = holding_reason or "motion timeout"
                self._abort(mid, tau + 20000, holding_reason)
                break
        res.ok = holding_reason is None or (holding_reason == "reference captured" and res.captures)
        res.reason = holding_reason or "completed"
        return self._finish(res, mid)

    def _finish(self, res, mid):
        # settle: wait for fresh telemetry reflecting the stop (re-sending a hold
        # to any station that has not acted on it)
        try:
            self.wait_for(lambda: (self._resend_holds(mid), all(
                self.links[s].tel and self.links[s].tel["st"] in (State.IDLE, State.FAULT, State.OFF)
                for s in self.ids))[1], 2.0, "stop")
        except CoordinatorError:
            res.ok = False
            res.reason += " | stations did not report stopped"
        for s in self.ids:
            res.final_pos.setdefault(s, self.links[s].pos)
        if res.held_by in self.ids:
            res.reason += self._held_by_tracking_text(res.held_by)
        self._log(f"motion {mid} -> {'OK' if res.ok else 'STOPPED'}: {res.reason}")
        return res

    def _abort(self, mid, tau_us, why):
        self._log(f"motion {mid} HOLD at tau={tau_us / 1e3:.0f} ms: {why}")
        now = self.rt.now_us()
        self._hold = (mid, tau_us, {s: now for s in self.ids}, now, set())
        for _ in range(2):                     # redundancy against a lost datagram (+ resend loop)
            self._send("*", {"t": "hold", "m": mid, "tau": int(tau_us)})

    def _fault_name(self, sid, code):
        """Fault name for a log line or stop reason. A TRACKING fault is followed by what the station's latest tracking
        error says (``trust.tracking_fault_detail``; the spool is taken at its core radius, so the line length is the
        minimum) when its telemetry carries one. Message text only."""
        name = Fault.NAMES.get(code)
        if code == Fault.TRACKING:
            st = self.cfg.station(sid)
            detail = tracking_fault_detail(self.links[sid].tel, st.encoder.counts_per_rev, st.spool.core_radius_m)
            if detail:
                return f"{name}: {detail}"
        return name

    def _held_by_tracking_text(self, sid):
        """`` (fault TRACKING: ...)`` when the station that originated a hold now reports a latched TRACKING fault, so the
        stop reason says why that station held (its fault event can arrive after its hold, so this is read once the
        stations have settled). Otherwise empty. Message text only."""
        if (self.links[sid].tel or {}).get("flt") == Fault.TRACKING:
            return f" (fault {self._fault_name(sid, Fault.TRACKING)})"
        return ""

    def _check_running(self, now):
        """(reason, lost_station) — lost_station set when only telemetry stopped."""
        tracking = f"fault {Fault.NAMES[Fault.TRACKING]}"
        for s in self.ids:
            h = self.links[s].health(now, self.tel_max_age, float("inf"))
            if h:
                lost = s if h == ["telemetry stale"] else None
                text = [f"fault {self._fault_name(s, Fault.TRACKING)}" if x == tracking else x for x in h]
                return f"station {s}: {', '.join(text)}", lost
        return None, None

    def _peer_holds(self, mid):
        for s in self.ids:
            for e in self.links[s].events:
                if e.get("k") == "peer_hold" and e.get("m") == mid:
                    return s
        return None

    def _collect_events(self, mid, res):
        for s in self.ids:
            for e in self.links[s].events:
                if e.get("m") == mid and e.get("k") == "capture" and s not in res.captures:
                    res.captures[s] = e
        return res.captures
