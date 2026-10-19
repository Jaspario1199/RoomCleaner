"""Shared builders for simulation tests (not a test module)."""
import numpy as np

from roomcleaner.cdpr.config import load_config
from roomcleaner.cdpr.coordinator import Coordinator
from roomcleaner.cdpr.sim.runtime import SimRuntime
from roomcleaner.cdpr.sim.station import SimStation
from roomcleaner.cdpr.transport import SimHostTransport, SimNetwork

SIM = "config/robot.sim.json"


def build(seed=0, *, latency_us=2000, jitter_us=1500, loss=0.0, world=None, cfg=None):
    cfg = cfg or load_config(SIM)
    net = SimNetwork(cfg.ids, latency_us=latency_us, jitter_us=jitter_us, loss=loss, seed=seed)
    rng = np.random.default_rng(seed)
    stations = {}
    for k, s in enumerate(cfg.stations):
        stations[s.id] = SimStation(s.id, usteps_per_rev=s.drive.usteps_per_rev,
                                    counts_per_rev=s.encoder.counts_per_rev, enc_sign=s.encoder.sign,
                                    clock_offset_us=float(rng.uniform(1e6, 9e7)),
                                    drift_ppm=float(rng.uniform(-40, 40)), seed=seed * 10 + k)
    rt = SimRuntime(net, stations, world)
    co = Coordinator(cfg, SimHostTransport(net, rt.now_us), rt)
    return cfg, net, stations, rt, co


def bring_up(co, *, sw_ok=False):
    co.wait(300000)
    co.configure()
    co.wait_synced(3.0)
    co.arm(sw_ok=sw_ok)
    co.wait(100000)
