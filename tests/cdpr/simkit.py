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


def fast_cfg(**overrides):
    """Simulation profile with coarser microstepping and faster moves so whole
    startups run in tens of seconds of wall time (same logic, same checks)."""
    import json
    raw = json.load(open(SIM))
    for s in raw["stations"]:
        s["drive"]["microsteps"] = 4
    raw["motion"].update(max_cable_speed_m_s=0.15, max_cable_accel_m_s2=0.3, max_cart_speed_m_s=0.15,
                         max_cart_accel_m_s2=0.3)
    for path, v in overrides.items():
        d = raw
        keys = path.split(".")
        for k in keys[:-1]:
            d = d[int(k)] if isinstance(d, list) else d[k]
        d[keys[-1]] = v
    return load_config(raw)


def assert_no_eq_failures(sim, where=""):
    """Harness hardening (review finding 6): a lifecycle / system run is only evidence if the plant's static
    equilibrium solver never failed. ``World.settle`` keeps the old state and counts ``eq_failures`` when it cannot
    converge (silently, unless ``strict``), so every system run must assert it. ``sim``: a ``SimRobot`` or a ``World``."""
    w = getattr(sim, "world", sim)
    events = [e for e in getattr(w, "events", []) if e and e[0] == "no_equilibrium"]
    assert w.eq_failures == 0 and not events, (
        f"{where or 'simulation'}: the plant's equilibrium solver failed {w.eq_failures} time(s) "
        f"(worst accepted residual {getattr(w, 'eq_worst_residual', float('nan')):.3g}); the run is not valid evidence")


def ModelFrameItemPerception(world, **kw):
    """``SimItemPerception`` reporting items the way the real perception chain does.

    ``SimItemPerception`` reports items in the TRUTH room frame, while the planner works in the calibrated model's
    frame; any registration error of the calibration (tens of mm in these simulations, the same order as the
    simulated gripper reach of 60 mm) then turns into a pick error that has nothing to do with the workflow under
    test. A real item position comes from the camera pose chain (vision/model) and therefore shares the model's
    frame: item_model = item_truth - (claw_truth - claw_model)."""
    from dataclasses import replace

    from roomcleaner.cdpr.tasks import SimItemPerception

    class _ModelFrame(SimItemPerception):
        def scan(self, ctx):
            here = ctx.model.pose_from_positions(ctx.co.positions())[0]
            bias = self.w.p[:2] - here[:2]
            return [replace(s, xy=s.xy - bias) for s in super().scan(ctx)]
    return _ModelFrame(world, **kw)
