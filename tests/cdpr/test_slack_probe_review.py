"""Independent review checks of the per-pose slack probe (verification/slack_probe_review.md).

Written by the verifier, not the author: station faults mid-probe, bounds, restore quality (slack and tension,
not only positions), hinge false-onset / calibration statistics, probe-off equivalence of the estimator, and the
simulator's contact solver limit cycle that produced the unexplained >15 N "peak tensions"."""
import math

import numpy as np
import pytest

from roomcleaner.cdpr.calibration import IDS, PoseSample
from roomcleaner.cdpr.protocol import Fault, State
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.startup import StartupAbort, StartupSequencer, hinge_analysis
from roomcleaner.cdpr.trajectory import plan_cable_move

from .simkit import fast_cfg

STATE = "CALIBRATION"


@pytest.fixture()
def rig():
    cfg = fast_cfg(**{"startup.slack_probe": True})
    r = SimRobot(cfg, seed=3)
    S = StartupSequencer(r.ctx)
    S.self_check()
    S.slack_takeup()
    S.initial_lift()
    S.visual_init()
    return r, S


def slack_mm(w):
    return (w.ell() - w.dist()) * 1e3


def pay_out(r, i, m):
    d = np.zeros(4)
    d[i] = m / r.ctx.ppu(i)
    res = r.co.execute(plan_cable_move(r.co.positions(), d, 0.005 / r.ctx.ppu(i), 0.005 / r.ctx.ppu(i) / 0.2,
                                       segment_s=r.cfg.motion.segment_s, label="inject"))
    assert res.ok, res.reason
    r.ctx.wait(1.0)


# ---------------------------------------------------------------- 1. safety: faults and bounds
def test_stalled_station_mid_probe_aborts_with_hold_and_keeps_torque(rig):
    r, S = rig
    pay_out(r, 2, 0.006)                                     # make the probe need several steps
    armed = {"n": 0}

    def hook(t):
        if r.co._active is not None and not armed["n"]:
            armed["n"] = 1
            r.stations["C"].stalled = True                   # the probed station stops following its path
    r.rt.hooks.append(hook)
    ref = S._still(n=10, state=STATE, suspended=True)
    with pytest.raises(StartupAbort) as e:
        S._probe_cable(2, ref, 10, STATE)
    assert e.value.suspended and not e.value.paused, e.value.reason
    assert "probe motion" in e.value.reason
    assert all(r.co.links[s].tel["en"] for s in IDS)         # holding torque kept everywhere (never disabled)
    assert not r.world.on_floor
    assert r.co.links["C"].tel["flt"] == Fault.TRACKING


def test_link_outage_mid_probe_aborts_suspended_and_station_self_holds(rig):
    r, S = rig
    pay_out(r, 1, 0.006)
    armed = {"n": 0}

    def hook(t):
        if r.co._active is not None and not armed["n"]:
            armed["n"] = 1
            r.net.down.add("D")
    r.rt.hooks.append(hook)
    ref = S._still(n=10, state=STATE, suspended=True)
    with pytest.raises(StartupAbort) as e:
        S._probe_cable(1, ref, 10, STATE)
    assert e.value.suspended and not e.value.paused
    r.co.wait(800000)
    assert r.stations["D"].core.fault == Fault.LEASE
    assert r.stations["D"].core.state != State.OFF           # LEASE stop must not drop the cable (torque kept)
    assert not r.world.on_floor


def test_no_onset_retraction_never_exceeds_probe_max(rig):
    r, S = rig
    st = r.cfg.startup
    saved = st.probe_max_m
    pay_out(r, 0, 0.012)                                     # 12 mm slack against a 5 mm bound
    P0 = r.co.positions().copy()
    st.probe_max_m = 0.005
    try:
        ref = S._still(n=10, state=STATE, suspended=True)
        with pytest.raises(StartupAbort) as e:
            S._probe_cable(0, ref, 10, STATE)
    finally:
        st.probe_max_m = saved
    retracted = (P0[0] - r.co.positions()[0]) * r.ctx.ppu(0)
    assert "no taut onset" in e.value.reason
    assert retracted <= 0.005 + r.ctx.ppu(0), retracted      # never more than one microstep over the bound


# ---------------------------------------------------------------- 2. restore leaves slack and tension as before
def test_restore_returns_slack_and_tension_not_only_positions(rig):
    r, S = rig
    pay_out(r, 2, 0.003)
    s_before, T_before = slack_mm(r.world), r.world.tension.copy()
    P_before = r.co.positions().copy()
    smp = S._sample_probed("fit", STATE)
    r.ctx.wait(0.5)
    s_after, T_after = slack_mm(r.world), r.world.tension.copy()
    assert np.all(np.abs(r.co.positions() - P_before) <= 1.0)
    assert np.all(np.abs(s_after - s_before) < 0.5), (s_before, s_after)       # no cable ends slacker or tighter
    assert np.all(np.abs(T_after - T_before) < 1.0), (T_before, T_after)
    assert smp.taut is not None


# ---------------------------------------------------------------- 3. estimator: probe off = unchanged, flags consistent
def test_probe_off_estimator_inputs_are_bitwise_unchanged():
    s = PoseSample(np.zeros(4), np.zeros(3), np.eye(3), np.eye(3) * 1e-6)
    sl = 0.00137
    assert np.array_equal(s.length_sigma(sl), np.full(4, sl))


def test_taut_sigma_only_widens_probed_readings():
    s = PoseSample(np.zeros(4), np.zeros(3), np.eye(3), np.eye(3) * 1e-6, taut=[1, 0, 1, 0], taut_sigma_m=[2e-3, 5e-3, 0, 5e-3])
    out = s.length_sigma(1e-3)
    assert np.allclose(out, [math.hypot(1e-3, 2e-3), 1e-3, 1e-3, 1e-3])


# ---------------------------------------------------------------- 4. onset statistics (own noise model, own seeds)
def _probe_series(rng, s_true, w_true, v_model, C, step0=5e-4, step_max=2e-3, r_max=0.04, k=4.0, floor=1e-3):
    L = np.linalg.cholesky(C)
    vn = np.linalg.norm(v_model)
    r_arr, P_arr, C_arr = [0.0], [rng.normal(size=3) @ L.T], [C]
    r, step = 0.0, step0
    while r < r_max - 1e-9:
        r += min(step, r_max - r)
        r_arr.append(r)
        P_arr.append(w_true * max(r - s_true, 0.0) + rng.normal(size=3) @ L.T)
        C_arr.append(C)
        a = hinge_analysis(r_arr, P_arr, C_arr, v_model, 0.5 * vn, k, floor)
        if a["detected"]:
            return a, r
        step = min(max(step0, 0.5 * r), step_max)
    return None, r


def test_hinge_false_onset_rate_on_a_far_slack_cable_is_low():
    rng = np.random.default_rng(2024)
    v = np.array([0.35, -0.2, 0.45])
    C = np.diag([0.5e-3 ** 2, 0.5e-3 ** 2, 1.0e-3 ** 2])
    n = 150
    false = sum(1 for _ in range(n) if _probe_series(rng, 1.0, v * 0, v, C)[0] is not None)
    assert false / n <= 0.03, false                          # measured ~1 % (see report): not zero


def test_hinge_taut_cable_detected_within_a_few_mm_and_bias_small():
    rng = np.random.default_rng(77)
    v = np.array([0.35, -0.2, 0.45])
    C = np.diag([0.5e-3 ** 2, 0.5e-3 ** 2, 1.0e-3 ** 2])
    errs, over = [], []
    for s in (0.0, 0.002, 0.006):
        for _ in range(60):
            a, r = _probe_series(rng, s, v, v, C)
            assert a is not None
            errs.append(a["s"] - s)
            over.append(r - s)
    assert abs(np.mean(errs)) < 0.0006 and np.sqrt(np.mean(np.square(errs))) < 0.0015
    assert np.percentile(over, 90) < 0.009


# ---------------------------------------------------------------- 5. the >15 N "peaks" are a simulator solver artefact
def test_world_hang_newton_limit_cycle_is_not_a_physical_tension():
    """Recorded state (probe, board case, seed 6, t = 1806.70 s, claw at z = 1.446 m): World._hang (undamped Newton, 30
    iterations) returns an iterate of a 2-cycle with 14 / 24 N; the convex energy minimum has at most 5.5 N."""
    from scipy.optimize import minimize
    r = SimRobot(fast_cfg(), seed=6)
    w = r.world
    w.anchors = np.array([[0.09675902233802439, -0.029915812897558028, 2.6281711972113406],
                          [3.3747790902804558, 0.07576337591173413, 2.651577270580651],
                          [3.285081543284766, 2.6212090451906946, 2.5782608973984664],
                          [0.10697483709598357, 2.7489196468982477, 2.5799438462946576]])
    ell = np.array([3.4021554010805435, 2.8125584623644526, 1.5682327696229539, 2.446110875293816])
    p0 = np.array([2.2359623584770616, 2.3368087288241846, 1.4463272851120872])
    G = 9.81

    def U(p):
        d = np.linalg.norm(w.anchors - w.attach_world(p), axis=1)
        return w.mass * G * p[2] + 0.5 * np.sum(w.EA / ell * np.maximum(0, d - ell) ** 2)
    pe = minimize(U, p0, method="Nelder-Mead", options=dict(xatol=1e-9, fatol=1e-12, maxiter=4000)).x
    T_eq = w._forces(pe, ell)[0]
    seen = []
    for _ in range(6):                                       # successive settles of an unchanged state
        p0 = w._hang(p0, ell)
        seen.append(float(np.max(w._forces(p0, ell)[0])))
    assert T_eq.max() < 7.0, T_eq
    assert max(seen) > 3.0 * T_eq.max(), (seen, T_eq)        # the simulator reports a non-equilibrium state
