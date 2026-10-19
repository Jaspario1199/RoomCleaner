import math
import random

import pytest

from roomcleaner.cdpr.clock import ClockModel
from roomcleaner.cdpr.protocol import Fault, State, decode, encode, params_hash
from roomcleaner.cdpr.station_core import StationCore, hermite
from roomcleaner.cdpr.transport import SimNetwork

PARAMS = {"sid": "A", "usteps_per_rev": 3200, "step_sign": 1, "max_rate_hz": 4000,
          "counts_per_rev": 4096, "enc_sign": 1, "enc_max_age_us": 30000, "track_tol": 60,
          "track_dwell_us": 150000, "lease_us": 300000, "sw_nc": True, "debounce_us": 10000,
          "hold_us": 250000}


class Bench:
    """One station core + ideal motor/encoder + controllable switch."""

    def __init__(self, sid="A", follow=True):
        self.core = StationCore(boot_id=hash(sid) & 0xFFFF)
        self.t = 0
        self.sw = False
        self.follow = follow
        self.enc_valid = True
        self.motor = 0                      # physical position (usteps)
        self.out = []
        p = dict(PARAMS, sid=sid)
        self.send({"t": "cfg", "p": p})
        self.step(5)
        self.send({"t": "arm"})
        self.out = []

    def send(self, msg, from_host=True):
        self.core.handle(decode(encode(msg)), self.t, from_host)
        self.out += self.core.drain()

    def step(self, n=1, ping=True):
        for _ in range(n):
            enc = int(self.motor * 4096 / 3200)
            s = self.core.update(self.t, enc, self.enc_valid, self.sw)
            if self.follow:
                self.motor += s
            self.t += 1000
            if ping and self.t % 100000 == 0:
                self.send({"t": "ping"})
            self.out += self.core.drain()

    def msgs(self, t, k=None):
        return [m for _, m in self.out if m["t"] == t and (k is None or m.get("k") == k)]

    def ack(self, re):
        return [m for _, m in self.out if m["t"] == "ack" and m["re"] == re]


def linear_segments(t0, p_from, p_to, dur_s, n, *, ref=0, last=True, m=1):
    """Constant-velocity segments with smooth (zero) ends handled by caller."""
    out = []
    d = int(dur_s / n * 1e6)
    v = (p_to - p_from) / dur_s
    for k in range(n):
        a = p_from + (p_to - p_from) * k / n
        b = p_from + (p_to - p_from) * (k + 1) / n
        out.append({"t": "seg", "m": m, "i": k, "t0": t0 + k * d, "d": d, "p0": a, "p1": b,
                    "v0": v, "v1": v, "last": last and k == n - 1, "ref": ref})
    return out


def test_config_hash_and_arm_gates():
    c = StationCore(1)
    c.handle({"t": "cfg", "p": {"sid": "A"}}, 0)
    assert c.drain()[-1][1]["why"] == "incomplete"
    c.handle({"t": "arm"}, 0)
    assert c.drain()[-1][1]["why"] == "no config"
    c.handle({"t": "cfg", "p": PARAMS}, 0)
    ack = c.drain()[-1][1]
    assert ack["ok"] and ack["hash"] == params_hash(PARAMS)
    c.handle({"t": "arm"}, 0)                          # encoder never sampled
    assert c.drain()[-1][1]["why"] == "encoder"
    c.update(1000, 0, True, True)                      # switch open (actuated or broken)
    c.drain()
    c.handle({"t": "arm"}, 1000)
    assert c.drain()[-1][1]["why"] == "switch active"
    c.update(2000, 0, True, False)
    c.update(14000, 0, True, False)
    c.drain()
    c.handle({"t": "arm"}, 14000)
    assert c.drain()[-1][1]["ok"] and c.state == State.IDLE


def test_executes_motion_and_reports_done():
    b = Bench()
    for s in linear_segments(b.t + 20000, 0, 1200, 0.6, 6):
        b.send(s)
    assert all(a["ok"] for a in b.ack("seg"))
    b.step(700)
    assert b.core.pos == 1200 and b.motor == 1200
    assert b.core.state == State.IDLE
    assert b.msgs("evt", "done")


def test_segment_validation():
    b = Bench()
    t0 = b.t + 20000
    segs = linear_segments(t0, 0, 800, 0.4, 4, last=True)
    b.send(dict(segs[0], p0=5.0))
    assert b.ack("seg")[-1]["why"] == "position"
    b.send(dict(segs[0], t0=b.t - 1))
    assert b.ack("seg")[-1]["why"] == "late"
    b.send(dict(segs[0], p1=20000.0))
    assert b.ack("seg")[-1]["why"] == "speed"
    b.send(segs[0])
    assert b.ack("seg")[-1]["ok"]
    b.send(dict(segs[1], p0=segs[1]["p0"] + 3))
    assert b.ack("seg")[-1]["why"] == "continuity"
    b.send(dict(segs[2]))
    assert b.ack("seg")[-1]["why"] == "sequence"
    for s in segs[1:]:
        b.send(s)
    b.send(dict(segs[3], i=4, t0=segs[3]["t0"] + segs[3]["d"]))
    assert b.ack("seg")[-1]["why"] == "after last"


def test_coordinated_hold_stops_all_stations_at_same_path_point():
    """Hold at path time 0.5 s: each station decelerates over hold_us (0.25 s),
    covering hold_us/2 more path time, so all stop at tau = 0.625 s."""
    a, b = Bench("A"), Bench("B")
    t0 = a.t + 20000
    for s_ in linear_segments(t0, 0, 3000, 1.5, 15):
        a.send(s_)
    for s_ in linear_segments(t0, 0, -2400, 1.5, 15):
        b.send(s_)
    a.step(300)
    b.step(300)
    a.send({"t": "hold", "m": 1, "tau": 500000})
    b.send({"t": "hold", "m": 1, "tau": 500000})
    a.step(900)
    b.step(900)
    assert a.core.state == b.core.state == State.IDLE
    assert abs(a.core.pos - 3000 * 0.625 / 1.5) <= 2
    assert abs(b.core.pos - (-2400) * 0.625 / 1.5) <= 2


def test_late_hold_overshoot_is_bounded_by_lateness():
    a = Bench("A")
    for s_ in linear_segments(a.t + 20000, 0, 3000, 1.5, 15):
        a.send(s_)
    while a.core.tau < 530000:                 # hold arrives 30 ms of path time late
        a.step()
    a.send({"t": "hold", "m": 1, "tau": 500000})
    a.step(600)
    late_stop = 3000 * (0.531 + 0.125) / 1.5
    assert abs(a.core.pos - late_stop) <= 3   # overshoot = speed x lateness, no more


def test_station_originated_hold_reaches_peers():
    a, b = Bench("A"), Bench("B")
    t0 = a.t + 20000
    for s_ in linear_segments(t0, 0, 3000, 1.5, 15):
        a.send(s_)
        b.send(dict(s_))
    a.step(400)
    b.step(400)
    a.enc_valid = False                         # A loses its encoder -> stop + broadcast
    for _ in range(900):
        a.step()
        b.step()
        for d, m in a.out:
            if d == "*" and m["t"] == "hold":
                b.send(m, from_host=False)
        a.out = [x for x in a.out if not (x[0] == "*" and x[1]["t"] == "hold")]
    assert a.core.fault == Fault.ENCODER
    assert b.core.state == State.IDLE and b.core.fault == Fault.NONE
    # B decelerated from A's fault point instead of finishing the motion
    assert b.core.pos < 3000 and abs(b.core.pos - a.core.pos) < 3000 * 0.13 / 1.5 + 3


def test_lease_expiry_holds_and_broadcasts():
    b = Bench()
    for s in linear_segments(b.t + 20000, 0, 4000, 2.0, 20):
        b.send(s)
    b.step(500, ping=True)
    b.step(800, ping=False)                 # host goes silent
    assert b.core.fault == Fault.LEASE
    assert b.core.state == State.FAULT
    holds = [m for d, m in b.out if m["t"] == "hold" and d == "*"]
    assert holds, "station must broadcast its own hold"
    assert b.core.pos < 4000


def test_underrun_holds_inside_buffered_path():
    b = Bench()
    segs = linear_segments(b.t + 20000, 0, 2000, 1.0, 10, last=False)
    for s in segs[:5]:                       # only half the motion ever arrives
        b.send(s)
    b.step(1200)
    assert b.core.fault == Fault.UNDERRUN
    assert b.core.pos <= 1000                # never beyond the buffered end
    assert b.core.state == State.FAULT


def test_reference_capture_snapshots_and_suppresses_shortening():
    b = Bench()
    segs = linear_segments(b.t + 20000, 0, -1600, 2.0, 20, ref=1)
    for s in segs:
        b.send(s)
    while b.core.pos > -700:
        b.step()
    b.sw = True                              # bead reaches the switch
    edge_pos = b.core.pos
    b.step(700)
    cap = b.msgs("evt", "capture")
    assert cap and abs(cap[0]["pos"] - edge_pos) <= 4
    after = b.core.pos
    assert after >= cap[0]["pos"] - 40      # debounce allowance, then no more shortening
    assert b.core.state == State.IDLE and b.core.fault == Fault.NONE
    assert [m for d, m in b.out if m["t"] == "hold" and d == "*"]


def test_unexpected_switch_is_a_fault_not_a_home():
    b = Bench()
    for s in linear_segments(b.t + 20000, 0, -1600, 2.0, 20, ref=0):
        b.send(s)
    b.step(400)
    b.sw = True
    b.step(30)
    p = b.core.pos
    b.step(200)
    assert b.core.fault == Fault.SWITCH and b.core.state == State.FAULT
    assert b.core.pos == p                   # pulses stopped immediately
    assert b.core.armed                      # holding torque retained


def test_tracking_fault_when_motor_does_not_follow():
    b = Bench(follow=False)
    for s in linear_segments(b.t + 20000, 0, 2000, 1.0, 10):
        b.send(s)
    b.step(600)
    assert b.core.fault == Fault.TRACKING
    assert b.core.state == State.FAULT and b.core.armed


def test_encoder_stale_fault_and_clear_reorigins():
    b = Bench()
    b.enc_valid = False
    b.step(60)
    assert b.core.fault == Fault.ENCODER
    b.enc_valid = True
    b.step(5)
    b.send({"t": "clear"})
    assert b.ack("clear")[-1]["ok"] and b.core.state == State.IDLE


def test_disarm_requires_confirmation_and_stillness():
    b = Bench()
    b.send({"t": "disarm"})
    assert not b.ack("disarm")[-1]["ok"]
    for s in linear_segments(b.t + 20000, 0, 2000, 1.0, 10):
        b.send(s)
    b.step(200)
    b.send({"t": "disarm", "confirm": "claw_supported"})
    assert b.ack("disarm")[-1]["why"] == "moving"
    b.step(900)
    b.send({"t": "disarm", "confirm": "claw_supported"})
    assert b.ack("disarm")[-1]["ok"] and b.core.state == State.OFF


def test_hermite_endpoints():
    x0, v0 = hermite(0, 10, 2, 3, 2.0, 0.0)
    x1, v1 = hermite(0, 10, 2, 3, 2.0, 1.0)
    assert (x0, x1) == (0, 10) and math.isclose(v0, 2) and math.isclose(v1, 3)


def test_clock_model_tracks_offset_and_drift():
    rng = random.Random(3)
    cm = ClockModel()
    true_off, drift = 7_000_000.0, 40e-6
    h = 1_000_000.0
    for _ in range(80):
        up, down = 800 + rng.expovariate(1 / 3000), 800 + rng.expovariate(1 / 3000)
        rx = h + up + true_off + drift * h
        tx = rx + 50
        h1 = h + up + 50 + down
        cm.add(h, rx, tx, h1)
        h = h1 + 200_000
    err = abs(cm.offset(h) - (true_off + drift * h))
    assert err < cm.uncertainty(h) and cm.uncertainty(h) < 3000


def test_sim_network_broadcast_and_outage():
    net = SimNetwork(["A", "B", "C", "D"], latency_us=1000, jitter_us=0)
    net.send("A", "*", {"t": "hold", "m": 1, "tau": 5}, now=0)
    net.deliver(2000)
    assert [len(net.take(n)) for n in ("host", "A", "B", "C", "D")] == [1, 0, 1, 1, 1]
    net.down.add("C")
    net.send("host", "*", {"t": "ping"}, now=0)
    net.deliver(5000)
    assert len(net.take("C")) == 0 and len(net.take("D")) == 1
    with pytest.raises(ValueError):
        net.send("host", "A", {"t": "x", "pad": "y" * 600}, now=0)
