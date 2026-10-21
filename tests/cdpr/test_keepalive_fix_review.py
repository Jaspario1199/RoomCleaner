"""Independent re-check of the keep-alive fix (verification/keepalive_fix_review.md; fix: verification/keepalive_fix_results.md).

Regression tests for the defects the re-check found. Like tests/cdpr/test_board_followups_review.py they are written to PASS WHILE THE
FINDING IS TRUE and fail when it is fixed: whoever fixes a finding converts its test (rename with ``_fixed``, ``# converted after fix: <id>``).

N1  Unpumped computations remain on the command thread while the stations are armed (excitation-candidate feasibility in
    ``StartupSequencer._stage``, ``trajectory.plan_line`` -> ``_check_path``): only ``Calibrator.fit`` and the survey flush go through
    ``_pumped``. In a coupled-clock full startup (simulated time = wall time) the fixed tree still latches Fault.LEASE (4) on all four
    stations at the first calibration stage (gap 0.9-2.3 s against faults.lease_s 0.3 s).
N2  The pump gap across a large ``Calibrator.fit`` is not ~21 ms: with a sleeping ``ctx.wait`` (what RealRuntime does) the worker re-takes the
    GIL after every numpy call and the command thread is starved for 0.1-0.3 s at the default 5 ms switch interval (a 4 s fit: 0.2-0.3 s
    against a 0.3 s lease); at 0.5 ms the same fit leaves 0.04 s.
N3  ``load_config``'s noise-floor cross-check assumes startup.frame_interval_s = 0.1 s whatever the configured value is.

Timings are CPU dependent (this sandbox, ``OMP_NUM_THREADS=1``): the assertions are ratios or call counts; the times are printed.
Everything is simulation.
"""
import copy
import json
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr import startup as ST
from roomcleaner.cdpr import trajectory as TJ
from roomcleaner.cdpr.attitude import wait_until_still
from roomcleaner.cdpr.calibration import Calibrator, box_candidates
from roomcleaner.cdpr.config import ConfigError, load_config
from roomcleaner.cdpr.frames import rot_z
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.spool import CableMap
from roomcleaner.cdpr.startup import StartupAbort, StartupSequencer

from .simkit import SIM, fast_cfg
from . import test_calibration as TC


# ===================================================================== N1: other long calls on the command thread
def _armed_with_model():
    """A simulated robot whose four stations are configured, synchronised and armed, with a nominal cable model (anchors = priors)."""
    cfg = fast_cfg()
    r = SimRobot(cfg, seed=3)
    co, ctx = r.co, r.ctx
    co.wait(300000)
    co.configure()
    co.wait_synced(3.0)
    co.arm()
    co.wait(100000)
    anchors = cfg.anchor_priors()
    ctx.set_model(anchors, {s.id: 2.5 for s in cfg.stations}, np.eye(4))
    ctx.result = SimpleNamespace(anchors_M=anchors, L0=np.full(4, 2.5), psi=np.zeros(3))
    assert cfg.faults.lease_s == 0.3 and all(co.links[s].tel["st"] == 1 for s in "ABCD")
    return r, cfg


def test_n1_the_candidate_filter_of_a_calibration_stage_runs_unpumped_while_the_stations_are_armed(monkeypatch):
    """``_stage`` filters its excitation candidates with ``_feasible`` (one tension LP, a workspace check and visibility per pose): 75
    poses in the local stage, 196 in the expanded ones, on the command thread with the stations armed. Not one ``Coordinator.pump`` runs
    during the filter (here the stage stops right after it: asking for more poses than exist). 0.3 s here for 75 cheap rejections; the
    full startup measured 0.7-2.3 s for the feasible ones (stack samples at ``_stage > _feasible > tension_distribution`` /
    ``BoardGeometry.visible``), 2.3-7.7x the 0.3 s lease."""
    r, cfg = _armed_with_model()
    co, ctx = r.co, r.ctx
    S = StartupSequencer(ctx)
    n = {"lp": 0, "pump": 0}
    lp = ST.tension_distribution
    monkeypatch.setattr(ST, "tension_distribution", lambda *a, **k: (n.__setitem__("lp", n["lp"] + 1), lp(*a, **k))[1])
    pump = co.pump
    co.pump = lambda: (n.__setitem__("pump", n["pump"] + 1), pump())[1]
    zf = -float(cfg.claw.lowest_point_body_m[2])
    min_z = zf + cfg.startup.target_clearance_m
    lb = np.asarray(cfg.calibration.local_box_m)
    W, D, _H = cfg.room_m
    centre = np.array([W / 2, D / 2, max(1.2, min_z + lb[2] + 0.01)])
    t0 = time.perf_counter()
    with pytest.raises(StartupAbort, match="feasible visible poses"):
        S._stage("local", centre, lb, 10 ** 6, 0, np.eye(3), min_z, (5, 5, 3))
    dt = time.perf_counter() - t0
    co.pump = pump
    print(f"\n[n1] _stage candidate filter: {dt:.2f} s, {n['lp']} tension LPs, {n['pump']} pumps (lease 0.3 s)")
    assert n["lp"] >= 75 and n["pump"] == 0                                 # 75 LP solves in a row, the keep-alive never runs


def test_n1_plan_line_has_no_way_to_pump_and_solves_hundreds_of_lps_per_move(monkeypatch):
    """``plan_line`` -> ``_check_path`` checks the tension of every point of the path both ways (2 LPs per point) and is a module function
    that knows nothing of the runtime: no parameter to wait or pump. A 1.3 m calibration move is 188 LPs, 0.6 s here (the full startup
    measured 0.2-1.2 s per planned move, ``_stage > plan_line_from > plan_line > _check_path``)."""
    import inspect
    r, cfg = _armed_with_model()
    sig = inspect.signature(TJ.plan_line)
    assert not [p for p in sig.parameters if "wait" in p or "pump" in p or "ctx" in p or "yield" in p]
    n = {"lp": 0}
    lp = TJ.tension_distribution
    monkeypatch.setattr(TJ, "tension_distribution", lambda *a, **k: (n.__setitem__("lp", n["lp"] + 1), lp(*a, **k))[1])
    t0 = time.perf_counter()
    plan = TJ.plan_line(r.ctx.model, np.array([1.2, 1.0, 1.0]), np.array([2.2, 1.7, 1.5]), TJ.limits_from_config(cfg), ws=r.ctx.ws)
    dt = time.perf_counter() - t0
    print(f"\n[n1] plan_line 1.3 m: {dt:.2f} s, {n['lp']} tension LPs, {len(plan.cart)} path points (lease 0.3 s)")
    assert n["lp"] >= 150 and len(plan.cart) >= 75


# ===================================================================== N2: the pump gap across a large calibrator fit
def _sleeping_pump():
    """``ctx.wait`` as ``Coordinator.wait`` does it on a RealRuntime: ``time.sleep(1 ms)`` and a pump, until the time is up."""
    class P:
        def __init__(self):
            self.t = []

        def wait(self, s):
            end = time.perf_counter() + s
            while time.perf_counter() < end:
                time.sleep(0.001)
                self.t.append(time.perf_counter())
    return P()


def _synthetic_fit_problem(n):
    cfg = TC.point_claw_config()
    maps = {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations}
    rng = np.random.default_rng(1)
    aR = cfg.anchor_priors() + rng.normal(0, 0.05, (4, 3))
    psi = np.array([1.5, 1.45, cfg.marker.heading_prior_rad + 0.15])
    aM = (aR - [psi[0], psi[1], 0]) @ rot_z(psi[2])
    L0 = np.array([2.3, 2.5, 2.4, 2.2])
    big = box_candidates([0, 0, 1.2], (0.8, 0.8, 0.5))
    return cfg, maps, TC.make_samples(maps, aM, L0, big[rng.choice(len(big), n, replace=False)], rng)


def _max_pump_gap(cfg, maps, samples, switch_interval_s):
    old = sys.getswitchinterval()
    sys.setswitchinterval(switch_interval_s)
    try:
        p = _sleeping_pump()
        S = StartupSequencer(SimpleNamespace(cfg=cfg, wait=p.wait))
        t0 = time.perf_counter()
        S._pumped(Calibrator(cfg, maps).fit, samples)
        wall = time.perf_counter() - t0
    finally:
        sys.setswitchinterval(old)
    return float(np.diff(np.array([t0] + p.t + [t0 + wall])).max()), wall


def test_n2_the_pump_gap_across_a_large_fit_is_a_large_share_of_the_lease_at_the_default_gil_switch_interval():
    """A real 60-sample fit (4-5 s) run through ``_pumped`` with a sleeping ``ctx.wait``: 0.2-0.3 s between two pumps at the default 5 ms
    switch interval (0.7-1.0x the lease), 0.04 s at 0.5 ms. (A 25-sample 1.8 s fit: 0.11-0.15 s against 0.035 s.) The 20 ms in the
    comment of ``PUMP_STEP_S`` is the sleep between steps, not the worst gap."""
    cfg, maps, samples = _synthetic_fit_problem(60)
    default_gap, default_wall = _max_pump_gap(cfg, maps, samples, sys.getswitchinterval())
    fast_gap, fast_wall = _max_pump_gap(cfg, maps, samples, 0.0005)
    print(f"\n[n2] 60-sample fit: max pump gap {default_gap * 1e3:.0f} ms at the default switch interval ({default_wall:.1f} s wall), "
          f"{fast_gap * 1e3:.0f} ms at 0.5 ms ({fast_wall:.1f} s wall); lease 300 ms")
    assert default_gap > 0.10                                               # a third of the lease or more
    assert default_gap > 2.0 * fast_gap                                     # and it is the GIL hand-off: 4-7x smaller at 0.5 ms
    assert not [t for t in threading.enumerate() if t.name.startswith("startup-pumped")]


# ===================================================================== N3: the cross-check ignores startup.frame_interval_s
def _raw(**changes):
    raw = json.load(open(SIM))
    for path, v in changes.items():
        sec, key = path.split(".")
        raw[sec][key] = v
    return raw


def _noise_only_gate(cfg0, sigma, limit, dt, seed, n_tags=4):
    tk, su = copy.copy(cfg0.tasks), copy.copy(cfg0.startup)
    object.__setattr__(tk, "grip_still_rate_rad_s", limit)
    object.__setattr__(su, "frame_interval_s", dt)
    base = np.vstack([np.array([[100, 100], [150, 100], [150, 150], [100, 150]], float) + 60 * k for k in range(n_tags)])
    g = np.random.default_rng(seed)
    clk = {"t": 0.0}

    class V:
        def observe(self):
            return SimpleNamespace(ok=True, corners=base + g.normal(0, sigma, base.shape), t_us=clk["t"] * 1e6)
    ctx = SimpleNamespace(cfg=SimpleNamespace(tasks=tk, startup=su, claw=cfg0.claw), camera=SimpleNamespace(fx=520.0), vision=V(),
                          wait=lambda s: clk.__setitem__("t", clk["t"] + s))
    return wait_until_still(ctx).ok


def test_n3_the_noise_floor_cross_check_assumes_a_frame_interval_of_0_1_s_whatever_is_configured():
    """sigma 0.5 px with a still-rate limit of 0.025 passes the cross-check (1.4 x 0.0170 = 0.0239 <= 0.025), and with frame_interval_s =
    0.1 the settle gate opens. With frame_interval_s = 0.05 (in the config, unbounded) the noise-only rate doubles to 0.034 rad/s, the
    limit is 0.73x of it, load_config still accepts and the gate never opens on a claw that does not move."""
    ok = load_config(_raw(**{"camera.corner_sigma_px": 0.5, "tasks.grip_still_rate_rad_s": 0.025, "startup.frame_interval_s": 0.05}))
    assert ok.startup.frame_interval_s == 0.05                              # accepted: the check uses 0.1 s, not this
    cfg0 = load_config(SIM)
    at_0_1 = [_noise_only_gate(cfg0, 0.5, 0.025, 0.1, s) for s in range(40)]
    at_0_05 = [_noise_only_gate(cfg0, 0.5, 0.025, 0.05, s) for s in range(40)]
    assert all(at_0_1)                                                      # the interval the check models: opens every time
    assert not any(at_0_05)                                                 # the accepted configuration: never (0 of 40, 4 tags)
    with pytest.raises(ConfigError, match="grip_still_rate_rad_s"):                 # sanity: the check itself works at 0.1 s
        load_config(_raw(**{"camera.corner_sigma_px": 0.5, "tasks.grip_still_rate_rad_s": 0.02}))
