"""Reference implementation of the winch-station control logic.

This is the executable specification for ``firmware/winch_station``: the C++
core mirrors it function for function, and the conformance test drives both
with the same scripted inputs. It has no I/O; the caller supplies time,
encoder samples, switch level and received messages, and collects outgoing
messages plus the number of step pulses to emit during the next period.

Key behaviours
--------------
* Motion = queue of cubic Hermite segments of commanded position vs time.
  Steps are generated locally; the network never times individual pulses.
* Path time ``tau`` advances at rate ``s`` (1 nominal). A HOLD ramps ``s``
  to 0 over ``hold_us`` starting at an agreed path time, so all stations
  stop at the same point of the same geometric path (feed-hold).
* Lease: if no valid host message arrives within ``lease_us`` the station
  starts a hold itself and broadcasts it. Buffer starvation (less than half
  a hold of path left and no final segment) does the same.
* A fault never removes holding torque. Only a confirmed DISARM does.
* Reference capture (segment ``ref = 1``): the first raw switch edge is
  snapshotted (time, position, encoder); after debounce the station suppresses
  further shortening and starts a coordinated hold.
* NC switch: "active" means open = actuated *or* a broken wire. Outside a
  reference motion an active switch is a fault, never a home.
"""
from __future__ import annotations

import math

from .protocol import REQUIRED_PARAMS, Fault, State, params_hash

MAX_QUEUE = 32
MIN_SEG_US = 5_000
MAX_SEG_US = 1_000_000
MIN_LEAD_US = 2_000
TELEMETRY_US = 20_000


def hermite(p0, p1, v0, v1, d_s, u):
    """Position and velocity of a cubic Hermite segment at u in [0,1]."""
    u2, u3 = u * u, u * u * u
    h00 = 2 * u3 - 3 * u2 + 1
    h10 = u3 - 2 * u2 + u
    h01 = -2 * u3 + 3 * u2
    h11 = u3 - u2
    x = h00 * p0 + h10 * d_s * v0 + h01 * p1 + h11 * d_s * v1
    dh00 = 6 * u2 - 6 * u
    dh10 = 3 * u2 - 4 * u + 1
    dh01 = -6 * u2 + 6 * u
    dh11 = 3 * u2 - 2 * u
    v = (dh00 * p0 + dh01 * p1) / d_s + dh10 * v0 + dh11 * v1
    return x, v


class Segment:
    __slots__ = ("m", "i", "t0", "d", "p0", "p1", "v0", "v1", "last", "ref", "tau0")

    def __init__(self, m, i, t0, d, p0, p1, v0, v1, last, ref, tau0):
        self.m, self.i, self.t0, self.d = m, i, t0, d
        self.p0, self.p1, self.v0, self.v1 = p0, p1, v0, v1
        self.last, self.ref, self.tau0 = last, ref, tau0


class StationCore:
    def __init__(self, boot_id: int, period_us: int = 1000, disarm_key: int | None = None):
        self.boot = boot_id & 0xFFFFFFFF
        self.period_us = period_us
        # disarm must echo this per-boot random key (reported only in unicast
        # telemetry to the host), so a stray or replayed datagram cannot drop
        # a hanging claw. Firmware passes a hardware random number.
        self.disarm_key = (disarm_key if disarm_key is not None else (self.boot * 2654435761) >> 7) & 0xFFFFFF
        self.dt = period_us
        self.params: dict | None = None
        self.hash = 0
        self.state = State.OFF
        self.fault = Fault.NONE
        self.pos = 0                      # issued microsteps (+ = payout)
        self.pos0 = 0
        self.enc = 0
        self.enc0 = 0
        self.enc_valid = False
        self.enc_t = -10**18
        self.queue: list[Segment] = []
        self.pending: dict = {}            # early-arriving segments, by index
        self.pending_m = None              # motion the parked segments belong to
        self.motion = -1
        self.last_appended = (-1, -1)      # (motion, index) of the newest accepted segment
        self.motion_t0 = 0                # local time of tau = 0
        self.tau = 0.0                    # path time (us)
        self.rate = 0.0                   # path-time rate s
        self.hold_tau = None              # path time at which a hold begins (pending)
        self.holding = False
        self.hold_t = 0
        self.post_capture = False
        self.last_host = None
        self.sw_raw = False
        self.sw_cand = False
        self.sw_since = 0
        self.sw = False
        self.sw_initialized = False
        self.track_bad_since = None
        self.terr = 0.0
        self.capture: dict | None = None
        self.release: dict | None = None
        self.seq = 0
        self.evt = 0
        self.next_tel = 0
        self.last_update = None
        self.outbox: list[tuple[str, dict]] = []   # ("host" | "*", message)
        self._emit("host", {"t": "evt", "k": "boot"})

    # ----------------------------------------------------------- utilities
    def _emit(self, dest, msg):
        self.seq += 1
        msg = dict(msg)
        msg["sid"] = self.params["sid"] if self.params else "?"
        msg["boot"] = self.boot
        msg["seq"] = self.seq
        if msg["t"] == "evt":
            self.evt += 1
            msg["e"] = self.evt
        self.outbox.append((dest, msg))

    def _ack(self, re, ok, why="", **kw):
        m = {"t": "ack", "re": re, "ok": bool(ok), "why": why}
        m.update(kw)
        self._emit("host", m)

    def drain(self) -> list[tuple[str, dict]]:
        out, self.outbox = self.outbox, []
        return out

    @property
    def armed(self) -> bool:
        return self.state != State.OFF

    def _max_steps(self) -> int:
        return int(math.ceil(self.params["max_rate_hz"] * self.period_us / 1e6))

    # ------------------------------------------------------------- messages
    def handle(self, msg: dict, now: int, from_host: bool = True) -> None:
        t = msg.get("t")
        if t == "hold":
            self._on_hold(msg, now)
            if from_host:
                self.last_host = now
            return
        if not from_host:
            return
        self.last_host = now
        if t == "ping":
            return
        if t == "sync":
            self._emit("host", {"t": "sync_r", "h": msg.get("h"), "rx": now, "tx": now})
        elif t == "cfg":
            self._on_cfg(msg)
        elif t == "arm":
            self._on_arm(msg, now)
        elif t == "disarm":
            if msg.get("confirm") != "claw_supported":
                self._ack("disarm", False, "confirm")
            elif msg.get("k") != self.disarm_key:
                self._ack("disarm", False, "key")
            elif self.state in (State.RUN, State.HOLD):
                self._ack("disarm", False, "moving")
            elif self.state == State.OFF:
                self._ack("disarm", True)
            else:
                self.state = State.OFF
                self.queue.clear()
                self._ack("disarm", True)
        elif t == "seg":
            self._on_seg(msg, now)
        elif t == "cancel":
            if self.state == State.IDLE:
                self.queue = [s for s in self.queue if s.m != msg.get("m")]
                self._ack("cancel", True, m=msg.get("m"))
            else:
                self._ack("cancel", False, "not idle", m=msg.get("m"))
        elif t == "clear":
            if self.state == State.FAULT:
                self.fault = Fault.NONE
                self.state = State.IDLE
                self.pos0, self.enc0 = self.pos, self.enc     # re-origin tracking
                self.track_bad_since = None
                self.capture = self.release = None
                self._ack("clear", True)
            elif self.state == State.OFF and self.fault != Fault.NONE:
                # disarmed with a latched fault: clearing is safe (no torque, no motion)
                self.fault = Fault.NONE
                self.track_bad_since = None
                self.capture = self.release = None
                self._ack("clear", True)
            elif self.state in (State.IDLE, State.OFF) and self.fault == Fault.NONE:
                self._ack("clear", True)                  # idempotent
            else:
                self._ack("clear", False, "moving")

    def _on_cfg(self, msg):
        p = msg.get("p")
        if self.state != State.OFF:
            if isinstance(p, dict) and self.params is not None and all(p.get(k) == self.params.get(k) for k in REQUIRED_PARAMS):
                self._ack("cfg", True, hash=self.hash)   # same config re-sent: idempotent
            else:
                self._ack("cfg", False, "armed")
            return
        if not isinstance(p, dict) or any(k not in p or p[k] is None for k in REQUIRED_PARAMS):
            self._ack("cfg", False, "incomplete")
            return
        ok = (p["usteps_per_rev"] > 0 and p["counts_per_rev"] > 0 and p["max_rate_hz"] > 0
              and p["step_sign"] in (1, -1) and p["enc_sign"] in (1, -1) and p["track_tol"] > 0
              and p["lease_us"] > 0 and p["hold_us"] > 0 and p["debounce_us"] >= 0
              and p["enc_max_age_us"] > 0 and p["track_dwell_us"] > 0)
        if not ok:
            self._ack("cfg", False, "invalid")
            return
        self.params = dict(p)
        self.hash = params_hash(self.params)
        self._ack("cfg", True, hash=self.hash)

    def _on_arm(self, msg, now):
        why = ""
        if self.params is None:
            why = "no config"
        elif self.state == State.IDLE and self.fault == Fault.NONE:
            self._ack("arm", True, hash=self.hash)      # idempotent (lost ack retried)
            return
        elif self.state != State.OFF:
            why = "busy"
        elif self.fault != Fault.NONE:
            why = "fault latched"
        elif not self._encoder_fresh(now):
            why = "encoder"
        elif self.sw and not msg.get("sw_ok", False):
            why = "switch active"
        if why:
            self._ack("arm", False, why)
            return
        self.state = State.IDLE
        self.pos0, self.enc0 = self.pos, self.enc
        self.track_bad_since = None
        self._ack("arm", True, hash=self.hash)

    def _on_seg(self, msg, now):
        m, i = msg.get("m"), msg.get("i")
        def nack(why):
            self._ack("seg", False, why, m=m, i=i)
        if not isinstance(i, int) or not isinstance(m, int):
            return nack("malformed")
        expected = self.last_appended[1] + 1 if self.last_appended[0] == m else 0
        if i < expected:                                  # retransmitted duplicate
            self._ack("seg", True, m=m, i=i)
            return
        if i > expected:                                  # arrived early: park it
            if self.pending_m != m:
                self.pending, self.pending_m = {}, m
            if len(self.pending) >= MAX_QUEUE:
                return nack("full")
            self.pending[i] = msg
            self._ack("seg", True, m=m, i=i)
            return
        self._append_seg(msg, now, nack)
        while self.pending_m == m and self.last_appended == (m, expected) and (expected + 1) in self.pending:
            expected += 1
            nxt = self.pending.pop(expected)
            self._append_seg(nxt, now, lambda why, k=expected: self._ack("seg", False, why, m=m, i=k))

    def _append_seg(self, msg, now, nack):
        m, i = msg.get("m"), msg.get("i")
        try:
            t0, d = int(msg["t0"]), int(msg["d"])
            p0, p1, v0, v1 = (float(msg[k]) for k in ("p0", "p1", "v0", "v1"))
            last, ref = bool(msg.get("last", False)), int(msg.get("ref", 0))
        except (KeyError, TypeError, ValueError):
            return nack("malformed")
        if self.params is None or not self.armed:
            return nack("not armed")
        if self.fault != Fault.NONE:
            return nack("fault")
        if self.holding or self.state == State.HOLD:
            return nack("holding")
        if not (MIN_SEG_US <= d <= MAX_SEG_US) or ref not in (0, 1, 2):
            return nack("range")
        if not all(math.isfinite(x) for x in (p0, p1, v0, v1)):
            return nack("range")
        if len(self.queue) >= MAX_QUEUE:
            return nack("full")
        vmax = self.params["max_rate_hz"] * 1.02
        for u in (0.0, 0.25, 0.5, 0.75, 1.0):
            if abs(hermite(p0, p1, v0, v1, d / 1e6, u)[1]) > vmax:
                return nack("speed")
        tail = self.queue[-1] if self.queue else None
        if tail is None and self.state == State.RUN and self.motion == m:
            return nack("starved")                      # queue drained mid-motion
        if tail is None or tail.m != m:
            # first segment of a new motion
            if self.state != State.IDLE or i != 0:
                return nack("sequence")
            if abs(p0 - self.pos) > 0.5:
                return nack("position")
            if t0 < now + MIN_LEAD_US:
                return nack("late")
            tau0 = 0.0
        else:
            if tail.last:
                return nack("after last")
            if i != tail.i + 1 or t0 != tail.t0 + tail.d:
                return nack("sequence")
            if abs(p0 - tail.p1) > 1e-6 or abs(v0 - tail.v1) > 1e-6:
                return nack("continuity")
            if t0 + d < now:
                return nack("late")
            tau0 = tail.tau0 + tail.d
        self.queue.append(Segment(m, i, t0, d, p0, p1, v0, v1, last, ref, tau0))
        self.last_appended = (m, i)
        self._ack("seg", True, m=m, i=i)

    def _on_hold(self, msg, now):
        m = msg.get("m")
        if self.state not in (State.RUN, State.IDLE) or m is None:
            return
        if self.state == State.IDLE:
            # not started yet: drop the queued motion so it never starts
            if self.queue and self.queue[0].m == m:
                self.queue.clear()
                self._emit("host", {"t": "evt", "k": "hold", "m": m, "pos": self.pos, "tau": 0})
            return
        if m != self.motion or self.holding:
            return
        tau = float(msg.get("tau", self.tau))
        if self.hold_tau is None or tau < self.hold_tau:
            self.hold_tau = tau

    # --------------------------------------------------------------- faults
    def _begin_hold(self, now, broadcast=True):
        if self.state != State.RUN or self.holding:
            return
        self.holding = True
        self.hold_t = now
        self.state = State.HOLD
        if broadcast:
            self._emit("*", {"t": "hold", "m": self.motion, "tau": int(self.tau)})

    def _set_fault(self, code, now):
        if self.fault != Fault.NONE:
            return
        self.fault = code
        running = self.state in (State.RUN, State.HOLD)
        self._emit("host", {"t": "evt", "k": "fault", "f": code, "pos": self.pos,
                            "m": self.motion, "tau": int(self.tau)})
        if Fault.REACTION[code] == "hold" and running:
            self._begin_hold(now)
            return
        if running:
            # stop pulses now, and ask everyone else to stop at this path point
            self._emit("*", {"t": "hold", "m": self.motion, "tau": int(self.tau)})
        if self.state != State.OFF:
            self.state = State.FAULT
        self.queue.clear()
        self.rate = 0.0
        self.holding = False

    # --------------------------------------------------------------- inputs
    def _encoder_fresh(self, now):
        return self.enc_valid and self.params is not None and now - self.enc_t <= self.params["enc_max_age_us"]

    def _debounce(self, raw, now):
        if not self.sw_initialized:
            self.sw_raw = self.sw_cand = self.sw = raw
            self.sw_since = now
            self.sw_initialized = True
            return False
        edge = raw != self.sw_raw
        self.sw_raw = raw
        if raw != self.sw_cand:
            self.sw_cand = raw
            self.sw_since = now
        deb = self.params["debounce_us"] if self.params else 10_000
        if self.sw != self.sw_cand and now - self.sw_since >= deb:
            self.sw = self.sw_cand
        return edge

    # --------------------------------------------------------------- update
    def update(self, now: int, enc_counts: int | None, enc_valid: bool, sw_active: bool) -> int:
        """Advance one control period. Returns signed steps to emit evenly over
        the next period (the firmware's pulse timer spreads them)."""
        if enc_valid and enc_counts is not None:
            self.enc, self.enc_valid, self.enc_t = int(enc_counts), True, now
        elif not enc_valid:
            self.enc_valid = False
        edge = self._debounce(bool(sw_active), now)
        # path time integrates the MEASURED elapsed time (loop jitter must not
        # make one winch lag the others); a gap > 3 periods is a TIMING fault
        self.dt = self.period_us if self.last_update is None else min(max(now - self.last_update, 0),
                                                                      3 * self.period_us)
        if self.last_update is not None and self.armed and now - self.last_update > 3 * self.period_us:
            self._set_fault(Fault.TIMING, now)
        self.last_update = now
        if self.params is None:
            self._telemetry(now)
            return 0
        if self.armed:
            if not self._encoder_fresh(now):
                self._set_fault(Fault.ENCODER, now)
            if self.last_host is not None and now - self.last_host > self.params["lease_us"]:
                self._set_fault(Fault.LEASE, now)
        steps = 0
        if self.state == State.IDLE and self.queue and now >= self.queue[0].t0:
            self.motion = self.queue[0].m
            self.motion_t0 = self.queue[0].t0
            self.tau = float(now - self.motion_t0)
            self.rate = 1.0
            self.hold_tau = None
            self.holding = False
            self.post_capture = False
            self.capture = None
            self.release = None
            self.state = State.RUN
        if self.state in (State.RUN, State.HOLD):
            steps = self._run(now, edge)
        self._check_switch(now, edge)
        self._check_tracking(now)
        self._telemetry(now)
        return steps

    def _segment_at(self, tau):
        for s in self.queue:
            if tau < s.tau0 + s.d:
                return s
        return None

    def _run(self, now, edge):
        dt = self.dt
        if not self.holding and self.hold_tau is not None and self.tau >= self.hold_tau:
            self._begin_hold(now, broadcast=False)
        if self.holding:
            self.rate = max(0.0, 1.0 - (now - self.hold_t) / self.params["hold_us"])
        if self.state == State.RUN:
            end = self.queue[-1].tau0 + self.queue[-1].d
            if not self.queue[-1].last and end - self.tau < self.params["hold_us"] / 2 + 2 * dt:
                self._set_fault(Fault.UNDERRUN, now)
                if self.state != State.HOLD:
                    return 0
        tau_next = self.tau + self.rate * dt
        end = self.queue[-1].tau0 + self.queue[-1].d
        finished = False
        if tau_next >= end:
            tau_next = end
            finished = True
        self.tau = tau_next
        seg = self._segment_at(self.tau - 1e-9) or self.queue[-1]
        u = min(max((self.tau - seg.tau0) / seg.d, 0.0), 1.0)
        x, _ = hermite(seg.p0, seg.p1, seg.v0, seg.v1, seg.d / 1e6, u)
        want = int(round(x)) - self.pos
        if self.post_capture and want < 0:
            want = 0
        lim = self._max_steps()
        steps = max(-lim, min(lim, want))
        self.pos += steps
        while self.queue and self.queue[0].tau0 + self.queue[0].d <= self.tau and len(self.queue) > 1:
            self.queue.pop(0)
        stopped = self.holding and self.rate <= 0.0
        if finished or stopped:
            m = self.motion
            self.queue.clear()
            self.holding = False
            self.hold_tau = None
            self.rate = 0.0
            if self.fault != Fault.NONE:
                self.state = State.FAULT
            else:
                self.state = State.IDLE
            self._emit("host", {"t": "evt", "k": "done" if finished and not stopped else "hold",
                                "m": m, "pos": self.pos, "tau": int(self.tau)})
        return steps

    def _active_ref(self):
        if self.state in (State.RUN, State.HOLD) and self.queue:
            seg = self._segment_at(self.tau - 1e-9) or self.queue[-1]
            return seg.ref
        return 0

    def _check_switch(self, now, edge):
        ref = self._active_ref()
        if edge and self.sw_raw and ref == 1 and self.capture is None:
            self.capture = {"ts": now, "pos": self.pos, "enc": self.enc, "tau": int(self.tau),
                            "m": self.motion, "confirmed": False}
        if self.capture is not None and not self.capture["confirmed"] and not self.sw_raw and not self.sw:
            self.capture = None           # contact shorter than the debounce: a glitch, not the bead
        if self.sw and ref == 1:
            if self.capture is None:      # debounced without a seen edge (started active)
                self.capture = {"ts": now, "pos": self.pos, "enc": self.enc, "tau": int(self.tau),
                                "m": self.motion, "confirmed": False}
            if not self.capture["confirmed"]:
                self.capture["confirmed"] = True
                self.post_capture = True
                self._emit("host", dict({"t": "evt", "k": "capture"}, **self.capture))
                self._begin_hold(now)
            return
        if ref == 2:
            if not self.sw and self.release is None:
                self.release = {"ts": now, "pos": self.pos, "enc": self.enc, "tau": int(self.tau),
                                "m": self.motion}
                self._emit("host", dict({"t": "evt", "k": "release"}, **self.release))
            return
        if self.sw and self.armed and not self.post_capture:
            self._set_fault(Fault.SWITCH, now)

    def _check_tracking(self, now):
        if not self.armed or not self.enc_valid or self.params is None:
            return
        p = self.params
        expected = (self.pos - self.pos0) * p["counts_per_rev"] / p["usteps_per_rev"]
        measured = p["enc_sign"] * (self.enc - self.enc0)
        self.terr = measured - expected
        if abs(self.terr) > p["track_tol"]:
            if self.track_bad_since is None:
                self.track_bad_since = now
            elif now - self.track_bad_since >= p["track_dwell_us"]:
                self._set_fault(Fault.TRACKING, now)
        else:
            self.track_bad_since = None

    def _telemetry(self, now):
        if now < self.next_tel:
            return
        self.next_tel = now + TELEMETRY_US
        self._emit("host", {
            "t": "tel", "now": now, "st": self.state, "flt": self.fault, "pos": self.pos,
            "enc": self.enc, "encv": self._encoder_fresh(now), "sw": self.sw, "swr": self.sw_raw,
            "m": self.motion, "i": self.queue[0].i if self.queue else -1, "tau": int(self.tau),
            "buf": len(self.queue), "terr": round(self.terr, 1), "cap": self.capture,
            "rate": round(self.rate, 4), "hash": self.hash, "en": self.armed, "dk": self.disarm_key,
        })
