"""Bench commissioning tool against one simulated station."""
from roomcleaner.cdpr.sim.runtime import SimRuntime
from roomcleaner.cdpr.sim.station import SimStation
from roomcleaner.cdpr.transport import SimHostTransport, SimNetwork
from tools.commission_station import Bench

from .simkit import fast_cfg


def bench(enc_sign=1, seed=0):
    cfg = fast_cfg()
    s = cfg.station("A")
    net = SimNetwork(["A"], latency_us=2000, jitter_us=1000, seed=seed)
    st = {"A": SimStation("A", usteps_per_rev=s.drive.usteps_per_rev, counts_per_rev=s.encoder.counts_per_rev,
                          enc_sign=enc_sign, clock_offset_us=3e6, drift_ppm=20, seed=seed)}
    rt = SimRuntime(net, st)
    return Bench(cfg, "A", SimHostTransport(net, rt.now_us), rt, log=lambda m: None), st


def test_direction_jog_and_lease_pass_on_a_correct_station():
    b, st = bench()
    d = b.direction()
    assert d["ok"], d
    assert abs(d["ratio"] - 1) < 0.02
    j = b.jog(50)
    assert j["ok"], j
    lz = b.lease()
    assert lz["ok"], lz


def test_reversed_encoder_is_reported_not_ignored():
    b, st = bench(enc_sign=-1, seed=1)
    d = b.direction()
    assert not d["ok"]
    assert "TRACKING" in d["why"] or "flip encoder.sign" in d["why"]
