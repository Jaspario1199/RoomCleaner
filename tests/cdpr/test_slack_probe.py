"""Per-pose slack probe (startup.slack_probe): taut-onset probing of every cable at each suspended pose.

Synthetic tests of the onset analysis are fast; the rest run the real sequencer / coordinator / station logic
against the physics simulator on a claw hanging a few centimetres above the floor (good vision there), built once
for the module (about 15 s). The tests run in file order and each leaves the rig as it found it."""
import math

import numpy as np
import pytest

from roomcleaner.cdpr.calibration import IDS, Calibrator, Layout, PoseSample
from roomcleaner.cdpr.config import ConfigError, load_config
from roomcleaner.cdpr.protocol import State
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.startup import StartupAbort, StartupSequencer, hinge_analysis, probe_response
from roomcleaner.cdpr.trajectory import plan_cable_move

from .simkit import fast_cfg

STATE = "CALIBRATION"


# ------------------------------------------------------------------ synthetic: the onset analysis
def _series(s, rng, *, sigma=0.0005, step=0.0005, n=14, w=(0.0, 0.0, 0.8), start=0.0):
    r = np.arange(0, n + 1) * step + start
    w = np.asarray(w, float)
    P = np.array([[0.0, 0.0, 0.5] + w * max(x - s, 0.0) + rng.normal(0, sigma, 3) for x in r])
    return r, P, np.tile(np.eye(3) * sigma ** 2, (len(r), 1, 1))


def test_hinge_analysis_measures_the_slack_and_does_not_fire_on_noise():
    rng = np.random.default_rng(0)
    v = np.array([0.0, 0.0, 0.8])
    errs = []
    for s in (0.0, 0.0008, 0.002, 0.004):
        for _ in range(10):
            r, P, C = _series(s, rng)
            for k in range(2, len(r) + 1):                     # sequential use, as the probe does
                a = hinge_analysis(r[:k], P[:k], C[:k], v, 0.4, 4.0, 0.001)
                if a["detected"]:
                    break
            assert a["detected"], (s, k)
            errs.append(a["s"] - s)
            assert r[k - 1] - s <= 0.006                       # bounded over-retraction at this noise
    assert abs(np.mean(errs)) < 0.0004 and np.sqrt(np.mean(np.square(errs))) < 0.0008
    for _ in range(20):                                        # a cable that is far from taut: no response
        r, P, C = _series(1.0, rng, n=10)
        assert not hinge_analysis(r, P, C, v, 0.4, 4.0, 0.001)["detected"]


def test_probe_response_points_at_the_anchor_and_is_scale_free():
    cfg = load_config("config/robot.sim.json")
    from roomcleaner.cdpr.kinematics import Geometry
    geo = Geometry(cfg.anchor_priors(), cfg.attachment_points())
    q = np.array([cfg.room_m[0] / 2, cfg.room_m[1] / 2, 0.8])
    U = geo.unit_vectors(q)
    for i in range(4):
        x = probe_response(geo, q, i)
        assert 0.3 < np.linalg.norm(x) < 1.2 and x @ U[i] > 0.3 * np.linalg.norm(x)


# ------------------------------------------------------------------ the estimator consumes the all-taut flag
def test_sample_flags_set_length_sigma_and_block_slack_candidates():
    s = PoseSample(np.zeros(4), np.zeros(3), np.eye(3), np.eye(3) * 1e-6)
    assert np.allclose(s.length_sigma(0.001), 0.001)
    s = PoseSample(np.zeros(4), np.zeros(3), np.eye(3), np.eye(3) * 1e-6, taut=[True, False, True, True],
                   taut_sigma_m=[0.001, 9.0, 0.0, 0.002])
    assert np.allclose(s.length_sigma(0.001), [math.sqrt(2) * 1e-3, 1e-3, 1e-3, math.hypot(1e-3, 2e-3)])
    cfg = load_config("config/robot.sim.json")
    from roomcleaner.cdpr.frames import rot_z
    from roomcleaner.cdpr.spool import CableMap
    from .test_calibration import make_samples
    maps = {st.id: CableMap(st.spool, st.drive.usteps_per_rev) for st in cfg.stations}
    rng = np.random.default_rng(1)
    aR = cfg.anchor_priors() + rng.normal(0, 0.03, (4, 3))
    aM = (aR - [1.5, 1.45, 0]) @ rot_z(cfg.marker.heading_prior_rad)
    L0 = np.array([2.3, 2.5, 2.4, 2.2])
    cal = Calibrator(cfg, maps)
    pts = [np.array([0.0, 0.0, 1.0]), np.array([0.3, -0.2, 0.9]), np.array([-0.4, 0.3, 1.1])]
    smp = make_samples(maps, aM, L0, pts, rng, slack=[(2, 0.02)] * 3)
    lay = Layout(3, False)
    x = cal._init_x(lay, smp, [], np.array([1.5, 1.45, cfg.marker.heading_prior_rad]), L0)
    x[lay.psi] = [1.5, 1.45, cfg.marker.heading_prior_rad]
    x[:12] = aM.ravel()
    for k in range(3):
        x[lay.p(k)] = smp[k].p
    assert cal._assign_slack(x, lay, smp)[:, 2].all()          # unflagged: the 20 mm slack is found
    for t in smp:
        t.taut = np.array([False, False, True, False])         # probed taut: never a slack candidate
        t.taut_sigma_m = np.zeros(4)
    assert not cal._assign_slack(x, lay, smp)[:, 2].any()


def test_probe_config_is_validated_and_off_by_default():
    assert load_config("config/robot.sim.json").startup.slack_probe is False
    assert load_config("config/robot.example.json").startup.slack_probe is False
    base = {k: v for k, v in __import__("json").load(open("config/robot.sim.json")).items()}
    for key, bad in (("probe_step_m", 0.0), ("probe_rounds", 0), ("probe_rounds", 4), ("probe_frames", 2),
                     ("probe_max_step_m", 0.0001), ("probe_max_m", 0.001), ("probe_frames_max", 5),
                     ("slack_probe", 1)):
        raw = __import__("copy").deepcopy(base)
        raw["startup"][key] = bad
        with pytest.raises(ConfigError):
            load_config(raw)


# ------------------------------------------------------------------ simulated rig: suspended claw
@pytest.fixture(scope="module")
def rig():
    cfg = fast_cfg(**{"startup.slack_probe": True})
    r = SimRobot(cfg, seed=0)
    S = StartupSequencer(r.ctx)
    S.self_check()
    S.slack_takeup()
    S.initial_lift()
    S.visual_init()                                            # first suspended sample, itself probed
    return r, S


def truth_slack_mm(w):
    return (w.ell() - w.dist()) * 1e3                          # > 0: cable longer than its span


def pay_out(r, S, i, m):
    """Lengthen cable ``i`` by ``m`` metres (a physical slack injection through the real coordinator)."""
    d = np.zeros(4)
    d[i] = m / r.ctx.ppu(i)
    res = r.co.execute(plan_cable_move(r.co.positions(), d, 0.005 / r.ctx.ppu(i), 0.005 / r.ctx.ppu(i) / 0.2,
                                       segment_s=r.cfg.motion.segment_s, label="inject"))
    assert res.ok, res.reason
    r.ctx.wait(1.0)


def pay_out_until_slack(r, S, i, target_mm, step_m=0.003, cap_m=0.05):
    """Lengthen cable ``i`` in steps until some cable has ``target_mm`` of true slack; return (cable index, total payout).
    A rigid claw on four spaced lines absorbs the first millimetres by swinging in yaw (about 2 deg/mm) before any
    cable goes slack, so the amount needed (and which cable slackens) depends on the pose."""
    total = 0.0
    while total < cap_m:
        pay_out(r, S, i, step_m)
        total += step_m
        sl = truth_slack_mm(r.world)
        if sl.max() >= target_mm:
            return int(np.argmax(sl)), total
    raise AssertionError(f"no slack after {total * 1e3:.0f} mm of payout: {truth_slack_mm(r.world)}")


def test_visual_init_sample_was_probed_and_positions_restored(rig):
    r, S = rig
    smp = r.ctx.samples[0]
    assert smp.taut is not None and smp.taut.all()             # near the floor the vision resolves every cable
    assert smp.probe["rounds"] == 1 and len(S.probe_log) == 1
    assert np.all(np.asarray(smp.taut_sigma_m) < 0.003)
    assert not r.world.on_floor and np.isfinite(smp.probe["slack_m"]).all()


def test_injected_slack_is_measured_and_the_cable_left_taut(rig):
    r, S = rig
    j, total = pay_out_until_slack(r, S, 2, 2.6)               # a rigid claw on four spaced lines absorbs the first mm in yaw
    t0 = truth_slack_mm(r.world)
    assert t0[j] > 2.5
    P_before = r.co.positions().copy()
    n0 = len(S.probe_log)
    smp = S._sample_probed("fit", STATE)
    rec = smp.probe
    assert smp.taut.all() and len(S.probe_log) == n0 + 1
    slack = np.array(rec["slack_m"]) * 1e3
    assert abs(slack[j] - t0[j]) < 1.0, (slack, t0)            # within 1 mm of the truth
    for k in range(4):                                         # the cables that were taut read ~0
        if k != j:
            assert slack[k] < 1.0
    # the sample was taken with every cable taut (positions of the probed state) ...
    assert smp.P[j] < P_before[j] - 0.8 * (t0[j] * 1e-3) / r.ctx.ppu(j)
    # ... and the motor positions were restored afterwards (the planner's model-consistent state)
    assert np.all(np.abs(r.co.positions() - P_before) <= 1.0)
    assert rec["cables"][IDS[j]]["peak_m"] < 0.012             # bounded over-retraction
    pay_out(r, S, 2, -total)                                   # undo the injection


def test_already_taut_cable_is_detected_on_the_first_step_and_restored(rig):
    r, S = rig
    st = r.cfg.startup
    saved = (st.probe_onset_translation_m, r.claw.tilt_noise, r.vision.tilt_sigma, r.vision.rot_sigma,
             r.simcam.pixel_sigma, r.vision.pixel_sigma)
    try:                                                       # a quiet camera: one 0.5 mm step is resolvable
        st.probe_onset_translation_m = 0.0002
        r.claw.tilt_noise, r.vision.tilt_sigma, r.vision.rot_sigma = 0.0, 1e-5, 1e-5
        r.simcam.pixel_sigma = r.vision.pixel_sigma = 0.01
        r.simcam.rot_sigma = 1e-6
        i = 1
        assert truth_slack_mm(r.world)[i] < 0.0                # B is taut (pre-tensioned)
        P0 = r.co.positions().copy()
        ref = S._still(n=10, state=STATE, suspended=True)
        rec = S._probe_cable(i, ref, 10, STATE)
        assert rec["steps"] == 1, rec                          # onset on the first step ...
        assert rec["slack_m"] < st.probe_step_m                # ... so the cable was already taut
        assert abs(r.co.positions()[i] - P0[i]) * r.ctx.ppu(i) < 0.0004    # ... and that step was paid back out
    finally:
        (st.probe_onset_translation_m, r.claw.tilt_noise, r.vision.tilt_sigma, r.vision.rot_sigma,
         r.simcam.pixel_sigma, r.vision.pixel_sigma) = saved
        r.simcam.rot_sigma = 0.002


def test_cable_that_never_goes_taut_aborts_with_a_hold_not_a_disable(rig):
    r, S = rig
    st = r.cfg.startup
    saved = st.probe_max_m
    j, total = pay_out_until_slack(r, S, 2, 3.0)               # a cable slack by >= 3 mm ...
    assert truth_slack_mm(r.world)[j] > 3.0                    # ... against a bound of 1 mm set below
    P_before = r.co.positions().copy()
    st.probe_max_m = 0.001
    try:
        ref = S._still(n=10, state=STATE, suspended=True)
        with pytest.raises(StartupAbort) as e:
            S._probe_cable(j, ref, 10, STATE)
    finally:
        st.probe_max_m = saved
    assert "no taut onset" in e.value.reason and f"station {IDS[j]}" in e.value.reason
    assert e.value.suspended and not e.value.paused            # fault path, claw still supported by the cables
    assert all(r.co.links[s].tel["st"] != State.OFF for s in IDS)       # holding torque stays on
    assert not r.world.on_floor
    S._restore_positions(P_before, STATE)
    pay_out(r, S, 2, -total)


def test_claw_running_away_without_a_significant_onset_aborts(rig, monkeypatch):
    r, S = rig
    from roomcleaner.cdpr import startup as startup_mod
    P0 = r.co.positions().copy()
    monkeypatch.setattr(startup_mod, "hinge_analysis", lambda *a, **k: {"detected": False})   # a blind onset detector
    monkeypatch.setattr(S, "PROBE_MAX_DISP_M", 0.0005)
    ref = S._still(n=10, state=STATE, suspended=True)
    with pytest.raises(StartupAbort) as e:
        S._probe_cable(0, ref, 10, STATE)                      # A is taut: the claw moves as soon as it retracts
    assert "claw moved" in e.value.reason and e.value.suspended and not e.value.paused
    assert all(r.co.links[s].tel["st"] != State.OFF for s in IDS)
    monkeypatch.undo()
    S._restore_positions(P0, STATE)
    assert np.all(np.abs(r.co.positions() - P0) <= 1.0)


def test_pause_during_a_probe_holds_between_and_during_motions(rig):
    r, S = rig
    P0 = r.co.positions().copy()
    # (1) a pause pressed after the first step is honoured at the next motion
    orig = S._execute
    count = {"n": 0}

    def execute(plan, state, **kw):
        if plan.label.startswith("probe"):
            count["n"] += 1
            if count["n"] == 2:
                r.co.request_pause("test pause")
        return orig(plan, state, **kw)
    S._execute = execute
    try:
        ref = S._still(n=10, state=STATE, suspended=True)
        with pytest.raises(StartupAbort) as e:
            S._probe_cable(0, ref, 10, STATE)
    finally:
        S._execute = orig
    assert e.value.paused and "paused" in e.value.reason and e.value.suspended
    held = r.co.positions().copy()
    r.ctx.wait(1.0)
    assert np.array_equal(r.co.positions(), held)              # nothing moved after the pause
    assert all(r.co.links[s].tel["st"] != State.OFF for s in IDS) and not r.world.on_floor
    # (2) a pause pressed while a probe step is moving stops that motion
    pump, state = r.co.pump, {"done": False}

    def pump_with_pause():
        if r.co._active is not None and not state["done"]:
            state["done"] = True
            r.co.request_pause("mid-motion pause")
        return pump()
    r.co.pump = pump_with_pause
    try:
        ref = S._still(n=10, state=STATE, suspended=True)
        with pytest.raises(StartupAbort) as e2:
            S._probe_cable(3, ref, 10, STATE)
    finally:
        r.co.pump = pump
    assert e2.value.paused and "paused" in e2.value.reason
    assert all(r.co.links[s].tel["st"] != State.OFF for s in IDS) and not r.world.on_floor
    S._restore_positions(P0, STATE)
    assert np.all(np.abs(r.co.positions() - P0) <= 1.0)


def test_noisy_vision_skips_the_cable_instead_of_tensioning_blind(rig):
    r, S = rig
    st = r.cfg.startup
    saved = (st.probe_overshoot_max_m, st.probe_frames_max)
    P0 = r.co.positions().copy()
    st.probe_overshoot_max_m, st.probe_frames_max = 0.0005, st.probe_frames      # impossible to resolve
    try:
        rec = S._probe_pose(STATE)
    finally:
        st.probe_overshoot_max_m, st.probe_frames_max = saved
    assert not rec["taut"].any() and all(c["status"] == "skipped" for c in rec["cables"].values())
    assert np.array_equal(r.co.positions(), P0)                # not a single cable moved
    assert "vision too noisy" in rec["cables"]["A"]["reason"]


def test_probe_disabled_leaves_the_sample_untouched(rig):
    r, S = rig
    S.cfg.startup.slack_probe = False
    try:
        n0, P0 = len(S.probe_log), r.co.positions().copy()
        smp = S._sample_probed("fit", STATE)
    finally:
        S.cfg.startup.slack_probe = True
    assert smp.taut is None and len(S.probe_log) == n0 and np.array_equal(r.co.positions(), P0)
