"""Regression: a micrometre-scale move must never reach a station as a segment it nacks.

The station rejects ("range") any segment shorter than ``MIN_SEG_US`` (5 ms). A rest-to-rest profile over d metres
lasts 2 sqrt(d / a), so ``TaskRunner.run``'s scan move of a few micrometres was planned as two 3 ms segments and the
whole pass aborted ("rejected segment 0: range"). Fix (trajectory.py / coordinator.py):

* a move whose cable lengths stay within ``NOOP_CABLE_M`` of the start over the whole path is a no-op plan
  (``Plan.is_noop``: one knot, no segments) which ``Coordinator.execute`` completes after the usual readiness checks;
* every other plan is slowed to last >= ``MIN_PLAN_S`` and gridded into segments of >= ``MIN_SEG_PLAN_S``
  (2 x ``MIN_SEG_US``), for Cartesian and cable-space moves alike.
"""
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr.homing import BeadVerifier
from roomcleaner.cdpr.kinematics import geometry_from_config, workspace_from_config
from roomcleaner.cdpr.station_core import MIN_SEG_US
from roomcleaner.cdpr.tasks import TaskRunner
from roomcleaner.cdpr.trajectory import (MIN_PLAN_S, NOOP_CABLE_M, Plan, PlanError, limits_from_config, model_from,
                                         plan_cable_move, plan_line, plan_line_from)

from .simkit import bring_up, build, fast_cfg

P0 = np.array([1.5, 1.2, 1.0])
AXES = {"z": (0, 0, 1), "x": (1, 0, 0), "diag": (1, 1, 1)}


def _rig(cfg):
    geo = geometry_from_config(cfg, cfg.anchor_priors(), yaw=0.2)
    model = model_from(geo, cfg, dict(zip("ABCD", geo.lengths(P0))))      # station position 0 == claw at P0
    return geo, model, limits_from_config(cfg)


def _profiles():
    cfg = fast_cfg()
    _, model, lim = _rig(cfg)
    # the limits of a quicker robot and a very fine segment grid: the worst case for short segments
    fast = replace(lim, cart_v=0.5, cable_v=0.5, cart_a=3.0, cable_a=3.0, segment_s=0.002)
    return cfg, model, {"config": lim, "aggressive": fast}


CFG, MODEL, PROFILES = _profiles()


def _durations_us(plan):
    return [s["d"] for j in range(4) for s in plan.segments(j, 0)]


def _unit(axis):
    v = np.asarray(AXES[axis], float)
    return v / np.linalg.norm(v)


# ===================================================================== (a) the planner
@pytest.mark.parametrize("profile", ["config", "aggressive"])
@pytest.mark.parametrize("axis", list(AXES))
@pytest.mark.parametrize("dist_um,noop", [(0, True), (1, True), (7, True), (60, False)])
def test_plan_line_never_emits_a_segment_shorter_than_min_seg_us(profile, axis, dist_um, noop):
    plan = plan_line(MODEL, P0, P0 + _unit(axis) * dist_um * 1e-6, PROFILES[profile])
    assert plan.is_noop == noop
    d = _durations_us(plan)
    if noop:
        assert d == [] and plan.duration == 0.0 and len(plan.times) == 1
        assert np.array_equal(plan.position_at(0.3), plan.pos[0]) and np.all(plan.vel == 0)
    else:
        assert len(plan.times) >= 3                                    # at least two segments
        assert min(d) >= 2 * MIN_SEG_US > MIN_SEG_US, d                # the planner's own 2x margin
        assert plan.duration >= MIN_PLAN_S - 1e-12
        # slowed down, never sped up: the limits are still respected
        lim = PROFILES[profile]
        assert plan.meta["v"] <= lim.cart_v * 1.011 + 1e-12 and plan.meta["a"] <= lim.cart_a + 1e-12


@pytest.mark.parametrize("profile", ["config", "aggressive"])
@pytest.mark.parametrize("axis", list(AXES))
def test_sweep_every_distance_gives_a_noop_or_station_legal_segments(profile, axis):
    seen_noop = seen_real = False
    for dist in np.logspace(-8, -1.5, 40):                             # 10 nm ... 3 cm
        plan = plan_line(MODEL, P0, P0 + _unit(axis) * dist, PROFILES[profile])
        if plan.is_noop:
            seen_noop = True
            assert dist < 2 * NOOP_CABLE_M / 0.3, "a >= ~70 um move must not be swallowed"
            continue
        seen_real = True
        d = _durations_us(plan)
        assert min(d) >= 2 * MIN_SEG_US, (dist, d)
        assert all(x == int(x) for x in d)
        # the knots are continuous and the plan starts and ends at rest
        assert np.all(plan.vel[0] == 0) and np.all(plan.vel[-1] == 0)
    assert seen_noop and seen_real


def test_noop_threshold_is_in_cable_length_over_the_whole_path_not_in_cartesian_distance():
    """A 60 um move along a cable moves that cable by 60 um (> threshold): not a no-op; the same move at right angles to
    every cable is not possible (the four cables span 3-D), which is why the threshold is on the cable lengths."""
    u = MODEL.geometry.unit_vectors(P0)[0]
    plan = plan_line(MODEL, P0, P0 + u * 60e-6, PROFILES["config"])
    assert not plan.is_noop and min(_durations_us(plan)) >= 2 * MIN_SEG_US
    just_below = plan_line(MODEL, P0, P0 + u * 0.9 * NOOP_CABLE_M, PROFILES["config"])
    assert just_below.is_noop


def test_a_reference_capture_move_that_would_be_a_noop_is_refused_not_silently_skipped():
    with pytest.raises(PlanError, match="reference-capture move"):
        plan_line(MODEL, P0, P0 + [0, 0, 3e-6], PROFILES["config"], ref=[1, 0, 0, 0])
    assert plan_line(MODEL, P0, P0 + [0, 0, 3e-6], PROFILES["config"], ref=[0, 0, 0, 0]).is_noop


def test_noop_plan_still_validates_the_target_against_the_workspace():
    ws = workspace_from_config(CFG, CFG.anchor_priors(), lowest_point_z=float(CFG.claw.lowest_point_body_m[2]))
    out = np.array([ws.hi[0] + 0.5, P0[1], P0[2]])                      # outside the room
    with pytest.raises(PlanError, match="workspace"):
        plan_line(MODEL, out, out + [0, 0, 3e-6], PROFILES["config"], ws=ws)


@pytest.mark.parametrize("big", [1e-6, 0.05, 0.3, 1.0, 5.0])
def test_plan_cable_move_of_a_fraction_of_a_microstep_is_station_legal(big):
    plan = plan_cable_move(np.zeros(4), [big, -big / 2, 0, big / 4], max_rate=2500, max_acc=12500, segment_s=0.1)
    assert min(_durations_us(plan)) >= 2 * MIN_SEG_US and plan.duration >= MIN_PLAN_S - 1e-12
    plan = plan_cable_move(np.zeros(4), [big, 0, 0, 0], max_rate=2500, max_acc=12500, segment_s=0.001)
    assert min(_durations_us(plan)) >= 2 * MIN_SEG_US


def test_plan_line_from_noop_holds_exactly_where_the_stations_are_and_keeps_the_model_check():
    P = np.array([0.0, 0.0, 0.0, 0.0])
    plan = plan_line_from(MODEL, P, P0 + [0, 0, 3e-6], PROFILES["config"])
    assert plan.is_noop and np.array_equal(plan.start, P) and np.array_equal(plan.end, P)
    # a zero-length move used to raise PlanError("zero-length move") (and abort a task); it is "already there" now
    assert plan_line_from(MODEL, P, P0, PROFILES["config"]).is_noop
    # the model-vs-cables sanity check is not bypassed for a tiny move
    with pytest.raises(PlanError, match="model and cables disagree"):
        plan_line_from(MODEL, P + [0, 0, 0, 400.0], P0 + [0, 0, 3e-6], PROFILES["config"])


# ===================================================================== (b) the simulated coordinator
def test_3um_move_through_the_sim_coordinator_does_not_produce_a_nack():
    cfg, net, st, rt, co = build(1, cfg=CFG)
    bring_up(co)
    assert np.array_equal(co.positions(), np.zeros(4))
    plan = plan_line_from(MODEL, co.positions(), P0 + [0, 0, 3e-6], PROFILES["config"])
    res = co.execute(plan)
    assert res.ok, res.reason
    assert "range" not in res.reason and not any("rejected" in line for line in co.log), co.log
    assert np.array_equal(co.positions(), np.zeros(4))                  # nothing moved
    assert all(not r for r in co.readiness().values())                  # every station still IDLE and healthy
    assert res.final_pos == {s: 0.0 for s in "ABCD"}
    nxt = co.motion_id
    assert co.execute(plan).ok and co.motion_id == nxt                  # a no-op consumes no motion id


@pytest.mark.parametrize("profile", ["config", "aggressive"])
@pytest.mark.parametrize("dist_um", [25, 60, 400])
def test_a_just_above_threshold_move_runs_on_the_stations_without_a_nack(profile, dist_um):
    """Small but real motions (slowed to >= 20 ms by the floor) are accepted by the unmodified station logic."""
    cfg, net, st, rt, co = build(2, cfg=CFG)
    bring_up(co)
    plan = plan_line_from(MODEL, co.positions(), P0 + _unit("diag") * dist_um * 1e-6, PROFILES[profile])
    assert not plan.is_noop
    res = co.execute(plan)
    assert res.ok, res.reason
    assert not any("rejected" in line for line in co.log), co.log
    assert np.all(np.abs(co.positions() - plan.end) <= 1.0), (co.positions(), plan.end)


def test_tiny_cable_move_runs_on_the_stations_without_a_nack():
    cfg, net, st, rt, co = build(3, cfg=CFG)
    bring_up(co)
    res = co.execute(plan_cable_move(co.positions(), [0.2, 0, 0, 0], max_rate=2500, max_acc=12500, segment_s=0.1))
    assert res.ok, res.reason
    assert not any("rejected" in line for line in co.log), co.log


def test_control_the_stations_still_nack_a_segment_below_min_seg_us():
    """Firmware semantics are unchanged: a hand-built plan with the old 3 ms segments is still refused ("range")."""
    cfg, net, st, rt, co = build(4, cfg=CFG)
    bring_up(co)
    t = np.array([0.0, 0.0031, 0.0062])
    plan = Plan(t, np.zeros((3, 4)), np.zeros((3, 4)), np.zeros((2, 4), int), None, "old-style 3 ms segments")
    res = co.execute(plan)
    assert not res.ok and "range" in res.reason, res.reason


def test_noop_keeps_the_readiness_and_pause_semantics_of_a_real_motion():
    cfg, net, st, rt, co = build(5, cfg=CFG)
    bring_up(co)
    plan = plan_line_from(MODEL, co.positions(), P0 + [0, 0, 3e-6], PROFILES["config"])
    co.request_pause("operator")
    res = co.execute(plan)
    assert not res.ok and res.reason.startswith("paused")              # a pause pressed between motions is honoured
    assert co.execute(plan).ok                                          # ... and consumed, not sticky
    st["C"].enc_broken = True
    co.wait(200000)
    res = co.execute(plan)
    assert not res.ok and "not ready" in res.reason and "C" in res.reason
    st["C"].enc_broken = False


# ===================================================================== (c) the callers
def _ctx(co):
    ws = workspace_from_config(CFG, CFG.anchor_priors(), lowest_point_z=float(CFG.claw.lowest_point_body_m[2]))
    return SimpleNamespace(cfg=CFG, model=MODEL, co=co, lim=PROFILES["config"], ws=ws,
                           ledger=SimpleNamespace(level="VERIFIED"), validated_volume=None)


@pytest.mark.parametrize("offset", [[0, 0, 3e-6], [0, 0, 0]])
def test_task_runner_move_handles_a_tiny_or_zero_move(offset):
    """The scan move that opens every TaskRunner.run pass (and the bug): was a nack for 3 um, StartupAbort for 0."""
    cfg, net, st, rt, co = build(6, cfg=CFG)
    bring_up(co)
    r = TaskRunner(_ctx(co), None)._move(P0 + offset, label="scan")
    assert r.ok, r.reason
    assert np.array_equal(co.positions(), np.zeros(4))


def test_bead_verifier_move_handles_a_tiny_move_and_refuses_a_tiny_capture_move():
    cfg, net, st, rt, co = build(7, cfg=CFG)
    bring_up(co)
    c = _ctx(co)
    bv = BeadVerifier(cfg, co, MODEL, c.lim, c.ws, lambda p: np.zeros(4), log=lambda s: None)
    r, err = bv._move(P0 + [0, 0, 3e-6], label="retreat")
    assert err is None and r.ok, (err, r and r.reason)
    r, err = bv._move(P0 + [0, 0, 3e-6], ref=[1, 0, 0, 0], label="search")
    assert r is None and "reference-capture move" in err
