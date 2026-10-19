"""Generate conformance traces by driving the PYTHON StationCore (the reference).

Each scenario scripts inputs (time, received datagrams, encoder counts, enc_valid,
switch level) against ``roomcleaner.cdpr.station_core.StationCore`` and records
every input and every output (steps per update, emitted messages in wire form,
i.e. exactly what ``protocol.encode`` would put on the network). The C++ port in
``firmware/winch_station`` replays the same inputs and must reproduce the
outputs (see ``conformance_main.cpp``).

Trace format (JSON, one event per line)::

    {"name":..., "boot":..., "period_us":..., "init_out":[...], "events":[
      {"op":"h","now":T,"raw":"<datagram text>","host":true,"acc":true,"out":[...]},
      {"op":"u","now":T,"enc":N|null,"ev":true,"sw":false,"steps":S,"out":[...]},
      ...]}

``out`` entries are ``{"d":"host"|"*","m":{wire message}}`` in emission order.
Run directly:  python3 tests/firmware/gen_station_traces.py [out_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from roomcleaner.cdpr.protocol import Fault, State, decode, encode, params_hash  # noqa: E402
from roomcleaner.cdpr.station_core import StationCore  # noqa: E402

TRACE_DIR = Path(__file__).resolve().parent / "traces"

PARAMS = {"sid": "A", "usteps_per_rev": 3200, "step_sign": 1, "max_rate_hz": 4000,
          "counts_per_rev": 4096, "enc_sign": 1, "enc_max_age_us": 30000, "track_tol": 60,
          "track_dwell_us": 150000, "lease_us": 300000, "sw_nc": True, "debounce_us": 10000,
          "hold_us": 250000}


# ------------------------------------------------------------------ helpers
def s5(x):
    return 10 * x ** 3 - 15 * x ** 4 + 6 * x ** 5


def ds5(x):
    return 30 * x ** 2 - 60 * x ** 3 + 30 * x ** 4


def segs(t0, p_from, p_to, dur_us, n, *, m=1, ref=0, last=True):
    """Min-jerk motion split into n cubic-Hermite segments (zero end velocity)."""
    length = p_to - p_from
    big_t = dur_us / 1e6
    d = dur_us // n
    out = []
    for k in range(n):
        a, b = k / n, (k + 1) / n
        pa = float(p_from) if k == 0 else p_from + length * s5(a)
        pb = float(p_to) if k == n - 1 else p_from + length * s5(b)
        va = length * ds5(a) / big_t
        vb = length * ds5(b) / big_t
        out.append({"t": "seg", "m": m, "i": k, "t0": t0 + k * d, "d": d, "p0": pa, "p1": pb,
                    "v0": va, "v1": vb, "last": bool(last and k == n - 1), "ref": ref})
    return out


def expect(cond, what):
    if not cond:
        raise AssertionError(f"scenario sanity check failed: {what}")


class Rec:
    """A StationCore + ideal motor/encoder + controllable switch, with recording."""

    def __init__(self, name, *, boot=0xC0FFEE, follow=True, period_us=1000):
        self.name, self.boot, self.period = name, boot, period_us
        self.core = StationCore(boot_id=boot, period_us=period_us)
        self.t = 0
        self.sw = False
        self.enc_valid = True
        self.enc_none = False
        self.follow = follow
        self.motor = 0
        self.events: list[dict] = []
        self.all_out: list[tuple[str, dict]] = []
        self.init_out = self._drain()

    def _drain(self):
        out = []
        for dest, msg in self.core.drain():
            wire = json.loads(encode(msg))
            out.append({"d": dest, "m": wire})
            self.all_out.append((dest, wire))
        return out

    def send(self, msg, from_host=True):
        self.send_raw(encode(msg).decode("ascii"), from_host)

    def send_raw(self, raw, from_host=True):
        dec = decode(raw.encode("ascii"))
        acc = dec is not None
        if acc:
            self.core.handle(dec, self.t, from_host)
        ev = {"op": "h", "now": self.t, "raw": raw, "host": from_host, "acc": acc}
        out = self._drain()
        if out:
            ev["out"] = out
        self.events.append(ev)

    def step(self, n=1, ping=True):
        for _ in range(n):
            enc = None if self.enc_none else int(self.motor * 4096 / 3200)
            s = self.core.update(self.t, enc, self.enc_valid, self.sw)
            ev = {"op": "u", "now": self.t, "enc": enc, "ev": self.enc_valid, "sw": self.sw, "steps": s}
            if self.follow:
                self.motor += s
            out = self._drain()
            if out:
                ev["out"] = out
            self.events.append(ev)
            self.t += 1000
            if ping and self.t % 100000 == 0:
                self.send({"t": "ping"})

    def step_until(self, cond, limit=5000, ping=True):
        for _ in range(limit):
            if cond():
                return
            self.step(1, ping=ping)
        raise AssertionError(f"{self.name}: condition not reached in {limit} steps")

    # --- queries over everything emitted so far
    def msgs(self, t, **kw):
        return [m for _, m in self.all_out if m["t"] == t and all(m.get(k) == v for k, v in kw.items())]

    def broadcasts(self, t="hold"):
        return [m for d, m in self.all_out if d == "*" and m["t"] == t]

    def last_ack(self, re):
        a = self.msgs("ack", re=re)
        return a[-1]

    def dump(self, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        head = {"name": self.name, "boot": self.boot, "period_us": self.period, "init_out": self.init_out}
        hs = json.dumps(head, separators=(",", ":"))
        body = ",\n".join(json.dumps(e, separators=(",", ":")) for e in self.events)
        path = out_dir / f"{self.name}.json"
        path.write_text(hs[:-1] + ',"events":[\n' + body + "\n]}\n")
        return path


def setup(r: Rec, params=PARAMS):
    r.send({"t": "cfg", "p": params})
    r.step(5)
    r.send({"t": "arm"})
    expect(r.core.state == State.IDLE, "armed")


# ---------------------------------------------------------------- scenarios
def sc_cfg_arm_gates():
    r = Rec("cfg_arm_gates")
    r.send({"t": "cfg", "p": {"sid": "A"}})
    expect(r.last_ack("cfg")["why"] == "incomplete", "incomplete")
    r.send({"t": "cfg"})
    expect(r.last_ack("cfg")["why"] == "incomplete", "no p")
    r.send({"t": "cfg", "p": dict(PARAMS, track_tol=None)})
    expect(r.last_ack("cfg")["why"] == "incomplete", "null param")
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["why"] == "no config", "no config")
    pre = segs(r.t + 20000, 0, 100, 500_000, 2)
    r.send(pre[0])
    expect(r.last_ack("seg")["why"] == "not armed", "seg before config")
    r.send({"t": "sync", "h": 123456789})
    r.send({"t": "sync", "h": 1234.5})
    r.send({"t": "sync"})
    expect(len(r.msgs("sync_r")) == 3, "sync_r x3")
    for bad in (dict(PARAMS, usteps_per_rev=0), dict(PARAMS, step_sign=2), dict(PARAMS, enc_sign=0),
                dict(PARAMS, debounce_us=-1), dict(PARAMS, hold_us=0), dict(PARAMS, max_rate_hz=-5)):
        r.send({"t": "cfg", "p": bad})
        expect(r.last_ack("cfg")["why"] == "invalid", "invalid cfg")
    params_f = dict(PARAMS, max_rate_hz=4000.0, track_tol=60.5, lease_us=300000.0, sw_nc=True, sid="B7")
    r.send({"t": "cfg", "p": params_f})
    ack = r.last_ack("cfg")
    expect(ack["ok"] and ack["hash"] == params_hash(params_f), "float cfg hash")
    r.send({"t": "cfg", "p": PARAMS})                          # replace while OFF
    expect(r.last_ack("cfg")["hash"] == params_hash(PARAMS), "int cfg hash")
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["why"] == "encoder", "arm needs encoder")
    r.step(3)
    r.sw = True
    r.step(15)                                               # debounced active
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["why"] == "switch active", "switch active")
    r.send({"t": "arm", "sw_ok": True})                        # operator accepts the active switch
    expect(r.last_ack("arm")["ok"] and r.core.state == State.IDLE, "armed with sw_ok")
    r.step(2)
    expect(r.core.fault == Fault.SWITCH and r.core.state == State.FAULT, "idle switch fault")
    r.sw = False
    r.step(15)
    r.send({"t": "arm", "sw_ok": False})
    expect(r.last_ack("arm")["why"] == "busy", "arm while faulted")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"] and r.core.state == State.IDLE, "clear")
    r.send({"t": "cfg", "p": PARAMS})                          # armed: same config is idempotent
    expect(r.last_ack("cfg")["ok"], "idempotent cfg (exact)")
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["ok"], "idempotent arm")
    r.send({"t": "cfg", "p": dict(PARAMS, max_rate_hz=4000.0)})  # same config (4000 == 4000.0)
    expect(r.last_ack("cfg")["ok"] and r.last_ack("cfg")["hash"] == params_hash(PARAMS), "idempotent cfg")
    r.send({"t": "cfg", "p": dict(PARAMS, lease_us=1)})
    expect(r.last_ack("cfg")["why"] == "armed", "cfg while armed")
    r.send({"t": "cfg", "p": {k: v for k, v in PARAMS.items() if k != "hold_us"}})
    expect(r.last_ack("cfg")["why"] == "armed", "cfg while armed, partial")
    r.send({"t": "cfg"})
    expect(r.last_ack("cfg")["why"] == "armed", "cfg while armed, no p")
    r.send({"t": "ping"})
    r.send({"t": "ping"}, from_host=False)
    r.send({"t": "sync", "h": 5}, from_host=False)              # ignored: not from host
    r.send({"t": "bogus", "x": 1})                              # unknown type still renews the lease
    r.send_raw('{"t":"ping"}')                                  # no version -> dropped
    r.send_raw("not json at all")
    r.send_raw("[1,2,3]")
    r.send_raw('{"v":2,"t":"ping"}')
    r.send_raw('{"v":1,"t":5}')
    r.send_raw('{"v":1,"t":"ping","extra":{"a":{"b":1}},"n":null,"s":"x\\"y\\\\z\\u0041"}')
    expect(len([e for e in r.events if e["op"] == "h" and not e["acc"]]) == 5, "five dropped datagrams")
    r.step(250)
    return r


def sc_normal_motion():
    r = Rec("normal_motion")
    setup(r)
    a = segs(r.t + 20000, 0, 1200, 800_000, 8, m=1)
    for s in a:
        r.send(s)
    r.send(a[2])                                              # retransmitted duplicate
    r.send({"t": "sync", "h": 1000000})
    r.step(1000)
    expect(r.core.pos == 1200 and r.core.state == State.IDLE, "motion 1 done")
    b = segs(r.t + 20000, r.core.pos, 0, 1_200_000, 12, m=2)
    for s in b[:6]:
        r.send(s)
    r.step(200)
    r.send(b[0])                                              # dup mid-motion
    for s in b[6:10]:
        r.send(s)
    r.step(400)
    for s in b[10:]:
        r.send(s)
    r.step(900)
    expect(r.core.pos == 0 and r.core.state == State.IDLE and r.core.fault == Fault.NONE, "motion 2 done")
    expect(len(r.msgs("evt", k="done")) == 2, "two done events")
    c = segs(r.t + 20000, 0, 333, 300_000, 3, m=3)           # odd length, fractional rounding
    for s in c:
        r.send(s)
    r.step(400)
    expect(r.core.pos == 333, "motion 3 done")
    return r


def sc_segments_ooo_dup():
    r = Rec("segments_ooo_dup")
    setup(r)
    t0 = r.t + 30000
    s = segs(t0, 0, 1500, 1_000_000, 6, m=1)
    r.send(dict(s[0], p0=5.0))
    expect(r.last_ack("seg")["why"] == "position", "position")
    r.send(dict(s[0], t0=r.t - 1))
    expect(r.last_ack("seg")["why"] == "late", "late")
    r.send(dict(s[0], p1=20000.0))
    expect(r.last_ack("seg")["why"] == "speed", "speed")
    r.send(dict(s[0], d=1000))
    expect(r.last_ack("seg")["why"] == "range", "range d")
    r.send(dict(s[0], ref=3))
    expect(r.last_ack("seg")["why"] == "range", "range ref")
    bad = dict(s[0])
    del bad["i"]
    r.send(bad)
    expect(r.last_ack("seg")["why"] == "malformed" and r.last_ack("seg")["i"] is None, "malformed no i")
    bad = dict(s[0])
    del bad["p1"]
    r.send(bad)
    expect(r.last_ack("seg")["why"] == "malformed", "malformed no p1")
    r.send(dict(s[0], m=None))
    expect(r.last_ack("seg")["why"] == "malformed", "malformed m null")
    r.send(s[0])
    expect(r.last_ack("seg")["ok"], "seg0")
    r.send(s[0])                                              # duplicate -> idempotent ack
    expect(r.last_ack("seg")["ok"], "dup seg0")
    r.send(dict(s[1], p0=s[1]["p0"] + 3))
    expect(r.last_ack("seg")["why"] == "continuity", "continuity")
    r.send(dict(s[1], v0=s[1]["v0"] + 1.0))
    expect(r.last_ack("seg")["why"] == "continuity", "continuity v")
    r.send(s[3])                                              # early: parked
    r.send(dict(s[3], p1=s[3]["p1"]))                         # parked twice: overwritten
    bad5 = dict(s[5])
    del bad5["p1"]
    r.send(bad5)                                              # parked, malformed at append time
    r.send(dict(s[2], t0=s[2]["t0"] + 1))                     # parked, sequence-bad at append time
    expect(len(r.core.pending) == 3, "three parked")
    r.send(s[1])                                              # appends 1, drains bad 2 (nack) and stops
    expect(r.last_ack("seg")["why"] == "sequence" and r.last_ack("seg")["i"] == 2, "drain nack sequence")
    r.send(s[2])                                              # appends 2, drains 3
    r.send(s[2])                                              # dup
    r.send(s[4])                                              # appends 4, drains malformed 5
    expect(r.last_ack("seg")["why"] == "malformed" and r.last_ack("seg")["i"] == 5, "drain nack malformed")
    r.send(s[5])
    expect(r.last_ack("seg")["ok"] and [q.i for q in r.core.queue] == [0, 1, 2, 3, 4, 5], "queue complete")
    r.send(dict(s[5], i=6, t0=s[5]["t0"] + s[5]["d"]))
    expect(r.last_ack("seg")["why"] == "after last", "after last")
    r.send({"t": "cancel", "m": 5})                            # nothing queued for m=5
    expect(r.last_ack("cancel")["ok"] and len(r.core.queue) == 6, "cancel other motion")
    r.step(1200)
    expect(r.core.pos == 1500 and r.core.state == State.IDLE, "motion done")
    # new sequence for a different motion id: first segment must be index 0
    n = segs(r.t + 30000, 1500, 1700, 300_000, 3, m=2)
    r.send(n[1])                                              # parked (m=2, i=1)
    r.send({"t": "cancel", "m": 2})
    r.send(n[0])                                              # appends 0, drains parked 1
    expect([q.i for q in r.core.queue] == [0, 1], "parked drained after first")
    r.send({"t": "cancel", "m": 2})
    expect(r.last_ack("cancel")["ok"] and not r.core.queue, "cancel queued motion")
    r.send(n[2])                                              # i=2 == expected -> sequence (queue empty, i != 0)
    expect(r.last_ack("seg")["why"] == "sequence", "sequence")
    r.send({"t": "cancel"})                                   # no m
    expect(r.last_ack("cancel")["m"] is None, "cancel echo null")
    # a motion that is running: cancel -> not idle; and a segment for an unknown future motion parks
    k = segs(r.t + 20000, 1500, 1600, 200_000, 2, m=3)
    for q in k:
        r.send(q)
    r.step(40)
    r.send({"t": "cancel", "m": 3})
    expect(r.last_ack("cancel")["why"] == "not idle", "cancel while running")
    r.send(dict(k[1], m=9, i=4))                              # parks for another motion mid-run
    r.step(400)
    expect(r.core.state == State.IDLE, "idle again")
    return r


def sc_queue_full():
    r = Rec("queue_full")
    setup(r)
    start = r.t + 400_000
    pending = segs(start, 0, 160, 32 * 5000, 32, m=1)         # 32 segments of 5 ms, all queued before start
    for s in pending:
        r.send(s)
    expect(len(r.core.queue) == 32, "queue holds 32")
    extra = dict(pending[31], i=32, t0=pending[31]["t0"] + 5000, p0=pending[31]["p1"], v0=pending[31]["v1"],
                 p1=pending[31]["p1"] + 1.0, last=True)
    pending[31]["last"] = False
    r.send(extra)
    expect(r.last_ack("seg")["why"] == "full", "queue full nack")
    r.send({"t": "cancel", "m": 1})
    expect(not r.core.queue, "cancelled")
    # park 32 distinct early segments for another motion, 33rd is refused; overwrite also refused when full
    base = segs(r.t + 400_000, 0, 10, 100_000, 3, m=2)[0]
    for i in range(1, 33):
        r.send(dict(base, i=i))
    expect(len(r.core.pending) == 32, "32 parked")
    r.send(dict(base, i=33))
    expect(r.last_ack("seg")["why"] == "full", "pending full")
    r.send(dict(base, i=5))
    expect(r.last_ack("seg")["why"] == "full", "pending full even when overwriting")
    r.step(30)
    return r


def sc_hold_feed():
    r = Rec("hold_feed")
    setup(r)
    for s in segs(r.t + 50000, 0, 3000, 1_500_000, 15, m=1):
        r.send(s)
    r.send({"t": "hold", "m": 7, "tau": 100})                   # not the queued motion: nothing
    expect(not r.msgs("evt", k="hold"), "wrong-motion idle hold ignored")
    r.send({"t": "hold", "m": 1, "tau": 0})                     # drops the queued motion
    expect(len(r.msgs("evt", k="hold")) == 1 and not r.core.queue, "idle hold drops queue")
    r.send({"t": "hold"})                                       # no m -> ignored
    r.step(100)
    expect(r.core.state == State.IDLE, "queued motion never started")
    for s in segs(r.t + 20000, 0, 3000, 1_500_000, 15, m=2):
        r.send(s)
    r.step(40)
    expect(r.core.state == State.RUN, "running")
    r.send({"t": "hold", "m": 99, "tau": 1})                    # other motion: ignored
    r.send({"t": "hold", "m": 2, "tau": 520000}, from_host=False)   # peer broadcast
    r.send({"t": "hold", "m": 2, "tau": 500000})
    r.send({"t": "hold", "m": 2, "tau": 480000})                # earlier wins
    r.send({"t": "hold", "m": 2, "tau": 700000})                # later ignored
    r.step_until(lambda: r.core.state == State.HOLD)
    tail = segs(r.t + 20000, 3000, 3100, 100_000, 1, m=2)[0]
    r.send(dict(tail, i=15))
    expect(r.last_ack("seg")["why"] == "holding", "seg while holding")
    r.send({"t": "hold", "m": 2, "tau": 1})                     # during HOLD: ignored
    r.step(400)
    expect(r.core.state == State.IDLE and r.core.fault == Fault.NONE, "stopped by feed-hold")
    expect(len(r.msgs("evt", k="hold")) == 2 and not r.broadcasts("hold"), "hold evt, no self broadcast")
    stop_pos = r.core.pos
    expect(500 < stop_pos < 1500, "stopped on path")
    for s in segs(r.t + 20000, stop_pos, stop_pos - 1000, 1_000_000, 10, m=3):
        r.send(s)
    r.step(60)
    r.send({"t": "hold", "m": 3})                               # no tau: hold from the current path time
    r.step(500)
    expect(r.core.state == State.IDLE and len(r.msgs("evt", k="hold")) == 3, "tau-less hold")
    return r


def sc_lease_expiry():
    r = Rec("lease_expiry")
    setup(r)
    for s in segs(r.t + 20000, 0, 4000, 2_000_000, 20, m=1):
        r.send(s)
    r.step(500)
    r.step(800, ping=False)                                   # host goes silent
    expect(r.core.fault == Fault.LEASE and r.core.state == State.FAULT, "lease fault")
    expect(r.broadcasts("hold"), "lease hold broadcast")
    expect(r.core.pos < 4000, "stopped early")
    r.send(segs(r.t + 20000, r.core.pos, 0, 600_000, 3, m=2)[0])
    expect(r.last_ack("seg")["why"] == "fault", "seg refused in fault")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"] and r.core.state == State.IDLE, "clear after lease fault")
    r.step(400, ping=False)                                   # lease expires again while idle
    expect(r.core.fault == Fault.LEASE and r.core.state == State.FAULT, "lease fault when idle")
    expect(len(r.broadcasts("hold")) == 1, "no extra broadcast when idle")
    r.send({"t": "clear"})
    r.step(20)
    return r


def sc_underrun():
    r = Rec("underrun")
    setup(r)
    allsegs = segs(r.t + 20000, 0, 2000, 1_000_000, 10, m=1, last=False)
    for s in allsegs[:5]:
        r.send(s)
    r.step(1200)
    expect(r.core.fault == Fault.UNDERRUN and r.core.state == State.FAULT, "underrun fault")
    expect(r.core.pos <= 1000, "within buffered path")
    expect(r.broadcasts("hold"), "underrun broadcast")
    r.send({"t": "cancel", "m": 1})
    expect(r.last_ack("cancel")["why"] == "not idle", "cancel in fault")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"], "clear")
    r.step(30)
    return r


def _ref_motion(r, p_from, p_to, dur, n, m, ref):
    for s in segs(r.t + 20000, p_from, p_to, dur, n, m=m, ref=ref):
        r.send(s)


def sc_ref_capture_backoff():
    r = Rec("ref_capture_backoff")
    setup(r)
    _ref_motion(r, 0, -1600, 2_000_000, 20, 1, 1)
    r.step_until(lambda: r.core.pos <= -700)
    r.sw = True                                               # bead reaches the switch
    r.step(700)
    cap = r.msgs("evt", k="capture")
    expect(len(cap) == 1 and cap[0]["confirmed"] is True, "capture evt")
    expect(r.core.state == State.IDLE and r.core.fault == Fault.NONE, "stopped without fault")
    expect(r.broadcasts("hold"), "capture hold broadcast")
    expect(any(m["t"] == "tel" and m["cap"] and m["cap"]["confirmed"] for _, m in r.all_out), "tel carries cap")
    p = r.core.pos
    expect(p >= cap[0]["pos"] - 60, "no shortening after capture")
    _ref_motion(r, p, p + 300, 500_000, 5, 2, 2)              # backoff with ref 2
    r.step_until(lambda: r.core.pos >= cap[0]["pos"] + 120)
    r.sw = False                                              # bead leaves the switch
    r.step(400)
    expect(len(r.msgs("evt", k="release")) == 1, "release evt")
    expect(r.core.state == State.IDLE and r.core.fault == Fault.NONE, "idle after release")
    _ref_motion(r, r.core.pos, r.core.pos + 200, 400_000, 4, 3, 0)
    r.step(600)
    expect(r.core.state == State.IDLE and r.core.fault == Fault.NONE, "normal motion after reference")
    return r


def sc_ref_started_active():
    """Switch rises during a ref=2 segment (edge ignored) and is still active when the
    motion's ref=1 segments begin: capture happens without a seen edge."""
    r = Rec("ref_started_active")
    setup(r)
    plan = segs(r.t + 20000, 0, -1600, 2_000_000, 20, m=1)
    for q in plan:
        q["ref"] = 2 if q["i"] < 8 else 1
        r.send(q)
    r.step(150)
    r.sw = True
    r.step(1000)
    cap = r.msgs("evt", k="capture")
    expect(len(cap) == 1 and r.core.state == State.IDLE and r.core.fault == Fault.NONE, "capture without a seen edge")
    expect(len(r.msgs("evt", k="release")) == 1, "release fires immediately (switch inactive at ref=2 start)")
    _ref_motion(r, r.core.pos, r.core.pos - 100, 300_000, 3, 2, 0)   # ref 0 with the switch still active
    r.step(200)
    expect(r.core.fault == Fault.SWITCH and r.core.state == State.FAULT, "switch fault at next motion")
    r.step(50)
    return r


def sc_ref_capture_glitch():
    r = Rec("ref_capture_glitch")
    setup(r)
    _ref_motion(r, 0, -1600, 2_000_000, 20, 1, 1)
    r.step_until(lambda: r.core.pos <= -300)
    r.sw = True
    r.step(5)                                                 # glitch shorter than the debounce
    r.sw = False
    r.step(60)
    expect(r.core.capture is None, "glitch snapshot discarded")
    expect(not r.msgs("evt", k="capture"), "no capture yet")
    r.step_until(lambda: r.core.pos <= -700)
    p_contact = r.core.pos
    r.sw = True
    r.step(700)
    cap = r.msgs("evt", k="capture")
    expect(len(cap) == 1, "capture")
    expect(abs(cap[0]["pos"] - p_contact) <= 2, "capture at the real contact, not the glitch")
    return r


def sc_tracking_fault():
    r = Rec("tracking_fault", follow=False)
    setup(r)
    for s in segs(r.t + 20000, 0, 2000, 1_000_000, 10, m=1):
        r.send(s)
    r.step(600)
    expect(r.core.fault == Fault.TRACKING and r.core.state == State.FAULT and r.core.armed, "tracking fault")
    expect(r.broadcasts("hold"), "tracking broadcast")
    r.send({"t": "cancel", "m": 1})
    expect(r.last_ack("cancel")["why"] == "not idle", "cancel in fault")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"] and r.core.state == State.IDLE, "clear re-origins")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"], "clear idempotent")
    r.follow = True
    for s in segs(r.t + 20000, r.core.pos, r.core.pos + 500, 500_000, 5, m=2):
        r.send(s)
    r.step(700)
    expect(r.core.fault == Fault.NONE and r.core.state == State.IDLE, "healthy after clear")
    return r


def sc_switch_fault():
    r = Rec("switch_fault")
    setup(r)
    for s in segs(r.t + 20000, 0, -1600, 2_000_000, 20, m=1, ref=0):
        r.send(s)
    r.step(400)
    r.sw = True
    r.step(30)
    p = r.core.pos
    r.step(200)
    expect(r.core.fault == Fault.SWITCH and r.core.state == State.FAULT and r.core.pos == p, "switch fault")
    expect(r.broadcasts("hold"), "switch broadcast")
    r.sw = False
    r.step(30)
    r.send({"t": "cancel", "m": 1})
    expect(r.last_ack("cancel")["why"] == "not idle", "cancel in fault")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"] and r.core.fault == Fault.NONE, "clear")
    for s in segs(r.t + 20000, r.core.pos, r.core.pos + 300, 400_000, 4, m=2):
        r.send(s)
    r.step(600)
    expect(r.core.state == State.IDLE and r.core.fault == Fault.NONE, "ok after clear")
    return r


def sc_disarm_clear():
    r = Rec("disarm_clear")
    setup(r)
    r.send({"t": "disarm"})
    expect(r.last_ack("disarm")["why"] == "confirm", "disarm needs confirm")
    r.send({"t": "disarm", "confirm": "yes"})
    expect(r.last_ack("disarm")["why"] == "confirm", "wrong confirm")
    r.send({"t": "disarm", "confirm": "claw_supported", "k": r.core.disarm_key ^ 1})
    expect(r.last_ack("disarm")["why"] == "key", "wrong key")
    for s in segs(r.t + 20000, 0, 2000, 1_000_000, 10, m=1):
        r.send(s)
    r.step(200)
    r.send({"t": "disarm", "confirm": "claw_supported", "k": r.core.disarm_key})
    expect(r.last_ack("disarm")["why"] == "moving", "disarm while moving")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["why"] == "moving", "clear while moving")
    r.step(900)
    r.send({"t": "disarm", "confirm": "claw_supported", "k": r.core.disarm_key})
    expect(r.last_ack("disarm")["ok"] and r.core.state == State.OFF, "disarmed")
    r.send({"t": "disarm", "confirm": "claw_supported", "k": r.core.disarm_key})
    expect(r.last_ack("disarm")["ok"], "disarm idempotent")
    r.send(segs(r.t + 20000, r.core.pos, 0, 500_000, 2, m=2)[0])
    expect(r.last_ack("seg")["why"] == "not armed", "seg while off")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"], "clear while off")
    r.send({"t": "hold", "m": 2, "tau": 5})                   # hold while OFF: ignored
    r.send({"t": "cfg", "p": dict(PARAMS, sid="C")})           # reconfigure while OFF
    r.step(5)
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["ok"] and r.core.state == State.IDLE, "re-armed")
    r.enc_valid = False
    r.step(60)
    expect(r.core.fault == Fault.ENCODER and r.core.state == State.FAULT, "encoder fault")
    r.enc_valid = True
    r.step(5)
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["why"] == "busy", "arm while in fault")
    r.send({"t": "disarm", "confirm": "claw_supported", "k": r.core.disarm_key})      # disarm from FAULT latches the fault
    expect(r.last_ack("disarm")["ok"] and r.core.state == State.OFF and r.core.fault == Fault.ENCODER,
           "disarm from fault")
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["why"] == "fault latched", "fault latched")
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"] and r.core.fault == Fault.NONE and r.core.state == State.OFF,
           "clear after disarm-in-fault (stays OFF)")
    r.send({"t": "arm"})
    expect(r.last_ack("arm")["ok"] and r.core.state == State.IDLE, "re-arm after clear")
    r.step(30)
    return r


def sc_encoder_invalid_motion():
    r = Rec("encoder_invalid_motion")
    setup(r)
    for s in segs(r.t + 20000, 0, 3000, 1_500_000, 15, m=1):
        r.send(s)
    r.step(400)
    r.enc_valid = False
    r.step(900)
    expect(r.core.fault == Fault.ENCODER and r.core.state == State.FAULT, "encoder fault")
    expect(r.broadcasts("hold"), "encoder broadcast")
    r.enc_valid = True
    r.step(5)
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"] and r.core.state == State.IDLE, "clear")
    r.step(40)
    return r


def sc_encoder_stale_none():
    r = Rec("encoder_stale_none")
    setup(r)
    r.step(10)
    r.enc_none = True                                         # valid flag but no new sample: goes stale
    r.step(60)
    expect(r.core.fault == Fault.ENCODER, "stale encoder fault")
    r.enc_none = False
    r.step(5)
    r.send({"t": "clear"})
    expect(r.last_ack("clear")["ok"], "clear")
    r.step(40)
    return r


def sc_timing_fault():
    r = Rec("timing_fault")
    setup(r)
    for s in segs(r.t + 20000, 0, 1500, 1_000_000, 10, m=1):
        r.send(s)
    r.step(300)
    r.t += 5000                                               # control loop overran its period
    r.step(30)
    expect(r.core.fault == Fault.TIMING and r.core.state == State.FAULT, "timing fault")
    expect(r.broadcasts("hold"), "timing broadcast")
    r.step(20)
    return r


SCENARIOS = [sc_cfg_arm_gates, sc_normal_motion, sc_segments_ooo_dup, sc_queue_full, sc_hold_feed,
             sc_lease_expiry, sc_underrun, sc_ref_capture_backoff, sc_ref_started_active,
             sc_ref_capture_glitch, sc_tracking_fault, sc_switch_fault, sc_disarm_clear,
             sc_encoder_invalid_motion, sc_encoder_stale_none, sc_timing_fault]


def generate(out_dir: Path = TRACE_DIR) -> list[Path]:
    out_dir = Path(out_dir)
    if out_dir.exists():
        for old in out_dir.glob("*.json"):
            old.unlink()
    return [sc().dump(out_dir) for sc in SCENARIOS]


if __name__ == "__main__":
    paths = generate(Path(sys.argv[1]) if len(sys.argv) > 1 else TRACE_DIR)
    for p in paths:
        print(f"{p}  {p.stat().st_size // 1024} KiB")
