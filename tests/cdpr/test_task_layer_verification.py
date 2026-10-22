"""Independent verification probes of the task-layer changes (verification/task_layer_verification.md).

The implementer's own tests are in test_task_pumping.py and test_task_reach.py. These probes were written by the verifier, who assumed
nothing from them:

* part A (fast, no startup): the order of events inside ``TaskRunner._handle`` with a stubbed planner / coordinator -- which refusals
  abort, which skip, and what the jaws are doing when they do (A1-A6). The stubs record every plan, execution and grip command.
* part B (one simulated three-station ``sim3_34`` startup, about 2 minutes, shared by the module): the PAUSED refusals through the
  Supervisor (B1), the dry run against the moves the real task makes (B2), the sensitivity of the dry run's pass/fail to the few mm by
  which the real start poses differ from the commanded ones (B3), and a whole task with a blocking claw link and a 1 s detector under
  the clock-coupled gap meter (B4).
"""
import dataclasses
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr import tasks as T
from roomcleaner.cdpr.coordinator import MotionResult
from roomcleaner.cdpr.protocol import Fault, State
from roomcleaner.cdpr.startup import StartupAbort
from roomcleaner.cdpr.trajectory import PlanError, plan_line

from .test_keepalive_pumping import PumpGapMeter, _armed_model_robot, _pump_threads
from .test_task_pumping import _verified_runner

REFUSALS = {"workspace": "workspace: floor point (0.1, 0.1) is outside the test triangle",
            "tension": "tension infeasible at [1.9 1.0 1.36] (max 12.1 N > 12.0 N incl. dynamics)"}
CARRY_LEGS = ("lift", "verify shift", "raise", "transport")


# ===================================================================== part A: the order of events in _handle (stubbed planner)
class Harness:
    """A TaskRunner on the armed four-station model robot whose planner, coordinator and claw are recording stubs. ``plan_fail(label)``
    / ``dry_fail(label)`` return a PlanError text (or None) for the planned moves / the dry run's legs. Every event is appended to
    ``ev``: ("plan", label, q, mass, allow_low), ("dry", label, a, b, mass, allow_low), ("exec", label), ("grip", close)."""

    def __init__(self, monkeypatch, *, payload=0.3, plan_fail=None, dry_fail=None, holds=(True, False), exec_fail=None,
                 scan=None, **tasks):
        self.r, self.cfg = _armed_model_robot()
        r, cfg = self.r, self.cfg
        self.runner = _verified_runner(r)
        W, D, _H = cfg.room_m
        self.runner.tc = dataclasses.replace(cfg.tasks, hamper_room_m=[W * 0.8, D * 0.5], max_payload_kg=payload, grip_settle_s=0.05,
                                             **tasks)
        self.hamper = np.asarray(self.runner.tc.hamper_room_m, float)
        self.ev, self.states = [], []
        self.pos = np.array([W / 2, D / 2, 1.2])
        self.holds = list(holds)
        self.plan_fail = plan_fail or (lambda lab: None)
        self.dry_fail = dry_fail or (lambda lab: None)
        self.exec_fail = exec_fail or (lambda lab: None)
        self.scan_results = scan
        h = self
        real_plan = T.plan_line

        def plan_from(model, P, q, lim, **kw):
            lab = kw["label"]
            h.ev.append(("plan", lab, np.array(q, float), lim.mass_kg, kw.get("allow_low")))
            msg = h.plan_fail(lab)
            if msg:
                raise PlanError(msg)
            return SimpleNamespace(label=lab, q=np.array(q, float))

        def dry(model, a, b, lim, **kw):
            lab = kw["label"]
            h.ev.append(("dry", lab, np.array(a, float), np.array(b, float), lim.mass_kg, kw.get("allow_low")))
            msg = h.dry_fail(lab)
            if msg:
                raise PlanError(msg)
            return real_plan(model, a, b, lim, **kw)

        def execute(plan, **k):
            h.ev.append(("exec", plan.label))
            why = h.exec_fail(plan.label)
            if why:
                return MotionResult(False, why)
            h.pos = plan.q.copy()
            return MotionResult(True)
        monkeypatch.setattr(T, "plan_line_from", plan_from)
        monkeypatch.setattr(T, "plan_line", dry)
        monkeypatch.setattr(r.co, "execute", execute)
        self.runner._here = lambda: h.pos.copy()
        self.runner._settle_and_approve = lambda *a, **k: (True, "")
        r.ctx.claw = SimpleNamespace(grip=lambda close: (h.ev.append(("grip", bool(close))), True)[1])
        self.runner.per = SimpleNamespace(
            holding=lambda ctx: (h.holds.pop(0) if h.holds else False, 0.9),
            scan=lambda ctx: h.scan_results(h) if h.scan_results else [],
            item_at=lambda ctx, xy, rad: True, note_target=lambda it: None)

    def item(self, dx=-0.3, dy=0.0, height=0.05, id="sock"):
        W, D, _H = self.cfg.room_m
        return T.ItemSighting(id, np.array([W / 2 + dx, D / 2 + dy]), height, 0.9)

    def handle(self, item):
        return self.runner._handle(item, self.hamper, lambda s, m="": self.states.append((s, m)))

    def of(self, kind):
        return [e for e in self.ev if e[0] == kind]

    def grips(self):
        return [e[1] for e in self.ev if e[0] == "grip"]

    def labels(self, kind):
        return [e[1] for e in self.ev if e[0] == kind]


@pytest.mark.parametrize("leg", CARRY_LEGS)
@pytest.mark.parametrize("kind", ["workspace", "tension"])
def test_a1_a_planning_refusal_after_the_jaws_closed_aborts_and_is_never_skipped(monkeypatch, leg, kind):
    """The dry run passes, then the REAL move of the carry (lift, verify shift, raise, transport) is refused with a workspace / tension
    text -- exactly what the task layer turns into ``TaskUnreachable`` before the grip. After the jaws closed it must leave ``_handle``
    (and ``run``) as an exception with the garment in the jaws: no ``(False, ...)`` return that would let ``run`` go on to the next
    item, no command to open the jaws, no later leg."""
    h = Harness(monkeypatch, plan_fail=lambda lab: REFUSALS[kind] if lab.startswith(leg) else None)
    with pytest.raises(StartupAbort) as e:
        h.handle(h.item())
    assert e.value.state == "TASK" and leg in e.value.reason and REFUSALS[kind][:12] in e.value.reason and not e.value.paused
    assert h.grips() == [False, True]                                   # opened for the approach, closed on the item, never opened again
    later = CARRY_LEGS[CARRY_LEGS.index(leg) + 1:]
    assert not any(any(lab.startswith(x) for x in later) for lab in h.labels("plan")), h.labels("plan")
    assert h.labels("exec")[-1] != leg + " sock" and ("exec", f"{leg} sock") not in h.ev     # the refused move was not executed
    # through run(): the exception comes out of the whole task, the item is not recorded as failed and the run does not go on
    h2 = Harness(monkeypatch, plan_fail=lambda lab: REFUSALS[kind] if lab.startswith(leg) else None,
                 scan=lambda hh: [hh.item()] if not hh.of("grip") else [])
    with pytest.raises(StartupAbort, match=leg):
        h2.runner.run(on_state=lambda s, m="": None)
    assert h2.grips() == [False, True]


def test_a1b_motion_faults_and_pauses_after_the_grip_abort_too(monkeypatch):
    for why, paused in (("station B reported fault 4", False), ("paused: operator", True)):
        h = Harness(monkeypatch, exec_fail=lambda lab: why if lab.startswith("verify shift") else None)
        with pytest.raises(StartupAbort) as e:
            h.handle(h.item())
        assert why in e.value.reason and e.value.paused == paused and not isinstance(e.value, T.TaskUnreachable)
        assert h.grips() == [False, True]


@pytest.mark.parametrize("leg", CARRY_LEGS)
@pytest.mark.parametrize("kind", ["workspace", "tension"])
def test_a2_a_dry_run_refusal_skips_the_item_before_any_motion_or_grip(monkeypatch, leg, kind):
    h = Harness(monkeypatch, dry_fail=lambda lab: REFUSALS[kind] if lab.startswith(leg) else None)
    ok, why = h.handle(h.item())
    assert ok is False and why.startswith(f"unreachable: {leg} sock: ") and REFUSALS[kind] in why
    assert h.of("plan") == [] and h.of("exec") == [] and h.grips() == []        # nothing planned for execution, nothing moved, jaws untouched
    assert h.runner.log and "carry not plannable" in h.runner.log[-1]


def test_a2b_an_item_outside_the_workspace_is_skipped_before_any_motion(monkeypatch):
    h = Harness(monkeypatch)
    far = T.ItemSighting("sock", np.array([h.cfg.room_m[0] + 1.5, h.cfg.room_m[1] / 2]), 0.05, 0.9)
    ok, why = h.handle(far)
    assert ok is False and why.startswith("unreachable: approach sock: target ") and "outside the trusted volume" in why
    assert h.of("plan") == [] and h.of("exec") == [] and h.grips() == []


def test_a3_a_planning_refusal_of_the_approach_or_the_descent_skips_the_item_with_the_jaws_open(monkeypatch):
    h = Harness(monkeypatch, plan_fail=lambda lab: REFUSALS["workspace"] if lab.startswith("approach") else None)
    ok, why = h.handle(h.item())
    assert ok is False and why.startswith("unreachable: approach sock: ") and h.of("exec") == [] and h.grips() == []
    h = Harness(monkeypatch, plan_fail=lambda lab: REFUSALS["tension"] if lab.startswith("descend") else None)
    ok, why = h.handle(h.item())
    assert ok is False and why.startswith("unreachable: descend sock: ") and h.labels("exec") == ["approach sock"]
    assert h.grips() == [False]                                          # opened for the approach, never closed: nothing in the jaws
    # a refusal of the other kind (the model and the cables disagree) says something about the system: abort, no skip
    h = Harness(monkeypatch, plan_fail=lambda lab: "actual positions differ from the model by [9.0, 0.0, 0.0] mm of cable: model and cables disagree"
                if lab.startswith("approach") else None)
    with pytest.raises(StartupAbort, match="model and cables disagree") as e:
        h.handle(h.item())
    assert not isinstance(e.value, T.TaskUnreachable) and h.grips() == []


@pytest.mark.parametrize("second", ["outside", "dry_run", "approach", "descent"])
def test_a4_a_refusal_on_the_second_attempt_skips_with_the_jaws_open(monkeypatch, second):
    """The first grip is not confirmed (``holding`` False): the claw opens, goes back over the item and re-locates it; the second attempt
    meets a refusal at the point named. The item is skipped, but only with the jaws open and empty (the last grip command is 'open')."""
    n = {"dry": 0}

    def dry_fail(lab):
        if lab.startswith("lift"):
            n["dry"] += 1
            if second == "dry_run" and n["dry"] == 2:
                return REFUSALS["tension"]

    def plan_fail(lab):
        calls = [e for e in h.ev if e[0] == "plan" and e[1] == lab]
        if len(calls) == 2 and ((second == "approach" and lab.startswith("approach")) or (second == "descent" and lab.startswith("descend"))):
            return REFUSALS["workspace"]

    def rescan(hh):
        if second == "outside":
            return [T.ItemSighting("sock", np.array([hh.cfg.room_m[0] + 1.5, hh.cfg.room_m[1] / 2]), 0.05, 0.9)]
        return [hh.item(dx=-0.28)]
    h = Harness(monkeypatch, holds=(False, True, False), dry_fail=dry_fail, plan_fail=plan_fail, scan=rescan)
    ok, why = h.handle(h.item())
    assert ok is False and why.startswith("unreachable: "), (ok, why)
    assert h.grips()[:3] == [False, True, False] and h.grips()[-1] is False, h.grips()   # attempt 1 closed and opened; the last command is open
    assert ("exec", "back over sock") in h.ev


def test_a5_the_dry_run_plans_the_poses_and_flags_the_real_moves_use(monkeypatch):
    """With stubs that keep the claw exactly where it was commanded, the legs the dry run plans (label, target, payload mass, low-pose
    permission) are those of the real lift, verify shift, raise and transport."""
    h = Harness(monkeypatch)
    ok, why = h.handle(h.item())
    assert (ok, why) == (True, "delivered"), (ok, why)
    dry = {e[1].split()[0] if not e[1].startswith("verify") else "verify": e for e in h.of("dry")}
    real = {(e[1].split()[0] if not e[1].startswith("verify") else "verify"): e for e in h.of("plan")}
    assert [e[1] for e in h.of("dry")] == [f"{k} sock" for k in CARRY_LEGS]
    for a, b in (("lift", "lift"), ("verify", "verify"), ("raise", "raise"), ("transport", "transport")):
        assert np.allclose(dry[a][3], real[b][2], atol=1e-9), (a, dry[a][3], real[b][2])        # target
        assert dry[a][4] == pytest.approx(real[b][3]) and dry[a][5] == real[b][4], (a, dry[a][4:], real[b][3:])   # mass, allow_low
    # the legs chain: each starts where the previous one ended, and the first at the grip pose
    d = h.of("dry")
    zf = h.runner.zf
    assert np.allclose(d[0][2], [h.item().xy[0], h.item().xy[1], zf + h.runner.tc.grip_clearance_m])
    assert all(np.allclose(d[k][2], d[k - 1][3]) for k in (1, 2, 3))
    assert d[0][4] == pytest.approx(h.cfg.claw.mass_kg + 0.3)


def test_a6_a_tall_item_or_a_carry_above_the_task_height_is_refused_not_discovered_after_the_grip(monkeypatch):
    h = Harness(monkeypatch)
    zmax = h.cfg.motion.task_max_height_m
    tall = h.item(height=zmax - h.runner.zf - h.runner.tc.approach_clearance_m + 0.1)       # the hover point is above the task height
    ok, why = h.handle(tall)
    assert ok is False and why.startswith("unreachable: ") and "task_max_height_m" in why
    assert h.of("plan") == [] and h.of("exec") == [] and h.grips() == []
    h = Harness(monkeypatch, hamper_height_m=zmax)                      # the hamper itself needs a carry above the task height
    with pytest.raises(StartupAbort) as e:
        h.runner.run(on_state=lambda s, m="": None)
    assert e.value.paused and "task_max_height_m" in e.value.reason and "nothing was moved" in e.value.reason
    assert h.of("plan") == [] and h.of("exec") == [] and h.grips() == []


def test_a7_three_unreachable_items_in_a_row_pause_the_run_with_the_robot_untouched(monkeypatch):
    items = lambda hh: [hh.item(dx=-0.3 + 0.1 * k, id=f"i{k}") for k in range(5)]
    h = Harness(monkeypatch, dry_fail=lambda lab: REFUSALS["tension"] if lab.startswith("raise") else None, scan=items)
    out = h.runner.run(on_state=lambda s, m="": None)
    assert out["done"] == [] and len(out["failed"]) == 3 and out["pause"].startswith("3 consecutive failures")
    assert h.grips() == [] and set(h.labels("exec")) == {"scan"}                              # only the scan moves


def _release_refused(h):
    h.runner._settle_and_approve = lambda what, *a, **k: (False, "predicted tilt 6.0 deg (cable model) > 5.0 deg") if what.startswith("release") else (True, "")


@pytest.mark.xfail(strict=True, reason="PRE-EXISTING, not in the diff (verifier finding F2): a refused RELEASE approval returns (False, ...) with the garment "
                   "still in the closed jaws, and run() goes on to the next scan with it")
def test_a8_a_refused_release_approval_does_not_carry_the_garment_on_to_the_next_scan(monkeypatch):
    h = Harness(monkeypatch, scan=lambda hh: [hh.item()] if not hh.of("grip") else [])
    _release_refused(h)
    try:
        h.runner.run(on_state=lambda s, m="": None)
    except StartupAbort:
        return                                                          # aborting would be fine
    evs = [e[0] if e[0] != "exec" else e[1] for e in h.ev]
    last_grip = max(i for i, e in enumerate(h.ev) if e[0] == "grip")
    moved_after = any(e[0] == "exec" for e in h.ev[last_grip + 1:])
    assert not (h.grips()[-1] is True and moved_after), evs[-6:]


def test_a8b_the_current_behaviour_of_a_refused_release_approval_is_recorded(monkeypatch):
    h = Harness(monkeypatch, scan=lambda hh: [hh.item()] if not hh.of("grip") else [])
    _release_refused(h)
    out = h.runner.run(on_state=lambda s, m="": None)
    assert out["failed"] == [("sock", "release not approved: predicted tilt 6.0 deg (cable model) > 5.0 deg")]
    assert h.grips() == [False, True]                                   # closed on the garment and never opened
    assert h.labels("exec")[-1] == "scan"                               # ... and the claw then moved on to the next scan


# ===================================================================== part B: the sim3_34 profile (one simulated startup)
from .test_task_reach import (PAYLOAD_KG, _outside_hamper, carry_plannable, claw_xyz, garment_perception,  # noqa: E402
                              goto, home, hull_extents, item_offsets, make_runner, outside_point, reset, spy, started)
from roomcleaner.cdpr.tasks import TrustedVolume  # noqa: E402


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    return started(tmp_path_factory)


def _stations(co):
    return [(co.links[s].tel["st"], co.links[s].tel["flt"]) for s in co.ids]


def _holding_still(r, sup, seconds=3.0):
    """The robot is held where it was: stations IDLE and fault-free, positions unchanged, nothing pumped wrongly, over ``seconds`` of
    simulated time with the idle host loop's keep-alive (``co.wait`` is what ``Service.idle_tick`` does)."""
    co = r.ctx.co
    pos0, p0 = co.positions().copy(), r.world.p.copy()
    co.wait(seconds * 1e6)
    assert _stations(co) == [(State.IDLE, 0)] * len(co.ids), _stations(co)
    assert np.allclose(co.positions(), pos0, atol=1e-9) and np.allclose(r.world.p, p0, atol=1e-6)


@pytest.mark.parametrize("which", ["scan", "hamper"])
def test_b1_the_two_pre_motion_refusals_pause_with_the_robot_holding_and_resume_works(rig, which):
    r, sup = rig
    reset(r)
    home(r)
    r.world.add_item("sock", r.world.p[:2] + [0.1, 0.1])
    sup.paused_from = ("STARTUP", "SELF_CHECK")                         # stale value of an earlier paused startup (never cleared by anything)
    runner = make_runner(r, scan_height_m=3.5) if which == "scan" else make_runner(r, hamper_room_m=_outside_hamper(r, TrustedVolume(r.ctx)))
    moves, executed, unspy = spy(r, runner)
    p0, pos0 = r.world.p.copy(), r.ctx.co.positions().copy()
    try:
        out = sup.run_task(runner)
    finally:
        unspy()
    assert out is None and sup.state == "PAUSED", (sup.state, sup.reasons[-2:])
    assert "nothing was moved" in sup.reasons[-1] and moves == [] and executed == []
    assert np.allclose(r.world.p, p0) and np.allclose(r.ctx.co.positions(), pos0, atol=1e-9)
    assert r.ctx.co.pause_requested is None                              # no pending pause that would refuse the next motion
    assert r.world.items[0]["state"] == "floor" and r.world.held is None
    _holding_still(r, sup)
    assert not r.ctx.ledger.claw_supported                               # (so the stale STARTUP paused_from cannot restart the startup)
    sup.resume()
    assert sup.state == "READY", (sup.state, sup.reasons[-2:])
    # after the resume the same robot does a normal task
    runner2 = make_runner(r)
    off = item_offsets(r, n=1)[0]
    r.world.items.clear()
    r.world.add_item("sock", r.world.p[:2] + off)
    out = sup.run_task(runner2)
    assert out is not None and out["done"] == ["sock"] and sup.state == "READY", (out, sup.state, sup.reasons[-2:])
    reset(r)


def test_b1b_a_new_task_command_is_refused_while_paused_and_accepted_after_the_resume(rig):
    from roomcleaner.cdpr.supervisor import CommandRefused
    r, sup = rig
    reset(r)
    home(r)
    out = sup.run_task(make_runner(r, scan_height_m=3.5))
    assert out is None and sup.state == "PAUSED"
    with pytest.raises(CommandRefused):
        sup.run_task(make_runner(r))
    assert sup.state == "PAUSED"
    sup.resume()
    assert sup.state == "READY"
    reset(r)


def test_b2_the_dry_run_legs_are_the_moves_the_real_task_makes_on_the_sim3_34_robot(rig, monkeypatch):
    """A real two-item task with the planner spied on both sides: the legs the dry run plans (grip pose -> hover -> shift -> raise ->
    hamper) against the moves ``_move`` then plans from the stations' actual positions. Targets, payload masses and low-pose flags
    must be equal; the starting poses differ by the few mm of the real positioning."""
    r, sup = rig
    reset(r)
    home(r)
    c = r.world.p[:2].copy()
    for name, off in zip(("first", "second"), item_offsets(r)):
        r.world.add_item(name, c + off)
    dry, real = [], []
    pf, pl = T.plan_line_from, T.plan_line

    def spy_from(model, P, q, lim, **kw):
        p0 = model.pose_from_positions(P)[0]
        real.append((kw.get("label"), np.array(p0), np.array(q, float), lim.mass_kg, kw.get("allow_low")))
        return pf(model, P, q, lim, **kw)

    def spy_line(model, a, b, lim, **kw):
        dry.append((kw.get("label"), np.array(a, float), np.array(b, float), lim.mass_kg, kw.get("allow_low")))
        return pl(model, a, b, lim, **kw)
    monkeypatch.setattr(T, "plan_line_from", spy_from)
    monkeypatch.setattr(T, "plan_line", spy_line)
    out = sup.run_task(make_runner(r))
    assert out is not None and sorted(out["done"]) == ["first", "second"], (out, sup.reasons[-2:])
    d_target_exact, d_raise_xy, d_start, n = 0.0, 0.0, 0.0, 0
    seen_base = {"raise": 0, "transport": 0}
    for lab, a, b, mass, low in dry:
        base = lab.split()[0]
        if base in seen_base:                                              # the real moves are labelled "raise" / "transport" (no item id)
            found = [y for y in real if y[0] == base][seen_base[base]:seen_base[base] + 1]
            seen_base[base] += 1
        else:
            found = [y for y in real if y[0] == lab]
        assert found, (lab, [y[0] for y in real], [d[0] for d in dry])
        x = found[0]
        assert x[3] == pytest.approx(mass) and x[4] == low, (lab, x[3:], mass, low)
        if base == "raise":
            d_raise_xy = max(d_raise_xy, float(np.linalg.norm(x[2][:2] - b[:2])))     # xy: where the claw really is after the shift
            d_target_exact = max(d_target_exact, abs(float(x[2][2] - b[2])))          # z: the transport height, exactly
        else:
            d_target_exact = max(d_target_exact, float(np.linalg.norm(x[2] - b)))
        d_start = max(d_start, float(np.linalg.norm(x[1] - a)))
        n += 1
    print(f"\n[B2] {n} dry-run legs against the real moves of the same label: target difference {d_target_exact * 1e3:.4f} mm (raise xy "
          f"{d_raise_xy * 1e3:.2f} mm), start-pose difference {d_start * 1e3:.2f} mm")
    assert n == 8 and d_target_exact < 1e-9 and d_raise_xy < 0.01 and d_start < 0.01
    reset(r)


def _legs_for(r, xy, payload, height=0.05):
    """The four carry legs planned by the dry run for an item at ``xy``: [(label, a, b, below)]."""
    runner = make_runner(r, max_payload_kg=payload)
    above = np.array([xy[0], xy[1], runner.zf + height + runner.tc.approach_clearance_m])
    grip = np.array([xy[0], xy[1], runner.zf + runner.tc.grip_clearance_m])
    hamper = np.asarray(runner.tc.hamper_room_m, float)
    shift, z_t = runner._carry_poses(above, hamper)
    raise_to = np.array([shift[0], shift[1], z_t])
    transport = np.array([hamper[0], hamper[1], z_t])
    return runner, [("lift", grip, above, True), ("shift", above, shift, False), ("raise", shift, raise_to, False),
                    ("transport", raise_to, transport, False)]


def _legs_ok(r, legs, runner, *, scale=1.0, d_start=None, payload=PAYLOAD_KG):
    """Plan the legs with the tension limit scaled by ``scale``; ``d_start`` (xy, m) is added to the START of the lift and to the XY of the
    pose the claw really reaches after each leg, as the real positioning error would (a real leg starts where the last one ended)."""
    ctx = r.ctx
    lim = dataclasses.replace(ctx.lim, mass_kg=r.cfg.claw.mass_kg + payload, t_max=ctx.lim.t_max * scale)
    off = np.zeros(3) if d_start is None else np.array([d_start[0], d_start[1], 0.0])
    for lab, a, b, below in legs:
        try:
            plan_line(ctx.model, a + off, b + off if lab == "raise" else b, lim, ws=ctx.ws, allow_low=below)
        except PlanError:
            return False
    return True


def test_b3_how_close_to_the_limits_does_the_dry_run_pass_and_do_5_mm_of_positioning_error_flip_it(rig):
    """The dry run plans from the commanded poses; the real moves start from where the stations actually are (a few mm off) and the
    raise goes straight up from wherever the shift ended. A dry run that passes with a hair of margin could still be refused in the air.
    For several payloads (0.3 kg is tonight's; the payload where about half the positions pass is the worst case), item positions drawn
    inside the trusted volume: how many pass the dry run, how many of those fail with the tension limit scaled to 0.97, and how many are
    refused when every leg starts 5 mm off in the four axis directions (the raise target moving with it)."""
    r, sup = rig
    reset(r)
    vol = TrustedVolume(r.ctx)
    lo, hi = hull_extents(vol)
    zf = -float(r.cfg.claw.lowest_point_body_m[2])
    rng = np.random.default_rng(11)
    pts = []
    while len(pts) < 12:
        xy = rng.uniform(lo[:2], hi[:2])
        if vol.allows(np.array([xy[0], xy[1], zf + 0.30])) and vol.allows(np.array([xy[0], xy[1], zf + 0.01]), below_ok=True):
            pts.append(xy)
    dirs = [np.array(d) * 0.005 for d in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    rows, total_flips = [], 0
    for payload in (0.3, 0.7, 0.75, 0.8, 0.85):
        passing, thin, flips = 0, 0, 0
        for xy in pts:
            runner, legs = _legs_for(r, xy, payload)
            if runner._dry_run_carry("t", legs[0][2], legs[0][1], np.asarray(runner.tc.hamper_room_m, float)) is not None:
                continue
            passing += 1
            thin += not _legs_ok(r, legs, runner, scale=0.97, payload=payload)
            flips += any(not _legs_ok(r, legs, runner, d_start=d, payload=payload) for d in dirs)
        rows.append((payload, passing, thin, flips))
        total_flips += flips
    print("\n[B3] 12 item positions in the trusted volume; payload kg -> (pass the dry run, of those fail at 0.97 of the tension limit, "
          "of those refused with 5 mm of start error): " + "; ".join(f"{p}: ({a}, {b}, {c})" for p, a, b, c in rows))
    assert rows[0][1] >= 5
    assert total_flips == 0, rows
    reset(r)


def test_b4_a_whole_task_with_a_blocking_claw_link_and_a_one_second_detector_never_stalls_the_keep_alive(rig):
    """The hardware shape on the sim3_34 robot: ``blocking_io`` claw (every grip and colour-frame grab sleeps 0.8 s, as an HTTP call
    against a 1 s timeout), a 1.0 s detector, the whole task under the clock-coupled gap meter, stack samples from 12 ms of gap."""
    r, sup = rig
    reset(r)
    home(r)
    r.world.add_item("sock", r.world.p[:2] + item_offsets(r, n=1)[0])
    threads = {"grip": [], "frame": [], "detect": []}
    inner_claw = r.ctx.claw

    class BlockingSimClaw:
        blocking_io = True

        def grip(self, close):
            time.sleep(0.8)
            threads["grip"].append(threading.current_thread().name)
            return inner_claw.grip(close)

        def __getattr__(self, name):
            return getattr(inner_claw, name)
    from .test_task_reach import SlowBlob
    det = SlowBlob(1.0)
    per = garment_perception(r, detector=det)
    inner_frame = per.frame_fn

    def slow_frame():
        time.sleep(0.8)
        threads["frame"].append(threading.current_thread().name)
        return inner_frame()
    per.frame_fn = slow_frame
    r.ctx.claw = BlockingSimClaw()
    lease = r.cfg.faults.lease_s
    m = PumpGapMeter(r.co, couple=True, armed=True, sample_above_s=0.012)
    try:
        out = sup.run_task(make_runner(r, per))
    finally:
        m.close()
        r.ctx.claw = inner_claw
    r.co.wait(200000)
    import collections
    where = collections.Counter(st[-1] if st else "?" for v in m._samples.values() for st in [max(v, key=len)] if v)
    long_gaps = sorted(m.long_stalls, reverse=True)[:5]
    print(f"\n[B4] {m.n_pumps} pumps, largest gap {m.max_stall_s * 1e3:.0f} ms (wall {m.max_wall_s * 1e3:.0f} ms), lease {lease * 1e3:.0f} ms, "
          f"gaps above 12 ms: {len(m.long_stalls)} (largest {[round(x * 1e3) for x in long_gaps]} ms); grips on {sorted(set(threads['grip']))}, "
          f"frames on {sorted(set(threads['frame']))}, detector calls {len(det.threads)}; {m.worst_text()}\n[B4] where the command thread was in the gaps above 12 ms: {dict(where)}")
    assert out is not None and len(out["done"]) == 1 and not out["failed"], (out, per.log, sup.reasons[-2:])
    assert len(threads["grip"]) >= 3 and all(t.startswith("startup-pumped") for t in threads["grip"])
    assert len(threads["frame"]) >= 4 and all(t.startswith("startup-pumped") for t in threads["frame"])
    assert len(det.threads) >= 4 and all(t.startswith("startup-pumped") for t in det.threads)
    assert all(r.co.links[s].tel["flt"] != Fault.LEASE for s in r.co.ids) and _stations(r.co) == [(State.IDLE, 0)] * 3
    assert m.violations == [] and _pump_threads() == []
    assert m.max_stall_s < lease / 3, m.worst_text()
    reset(r)


def test_b5_a_pause_pressed_during_a_pumped_detection_holds_the_next_motion_exactly_as_before(rig):
    """The operator presses PAUSE 0.3 s into the first 1 s detection (the command thread is in ``run_pumped``). The pause is not an
    exception of the pumped call: it is held by the next ``execute`` -- the approach of the first item -- which returns "paused: ...",
    the task aborts with ``paused=True`` and the supervisor goes to PAUSED. Nothing is moved towards the item, nothing gripped."""
    from .test_task_reach import SlowBlob
    r, sup = rig
    reset(r)
    home(r)
    r.world.add_item("sock", r.world.p[:2] + item_offsets(r, n=1)[0])

    snap = []

    class PausingBlob(SlowBlob):
        """A 1 s detector that presses PAUSE 0.3 s into its first call."""
        def detect(self, frame=None):
            if not self.threads:
                snap.append(r.world.p.copy())                           # where the claw is at the scan point
                threading.Timer(0.3, sup.pause, args=("test pause",)).start()
            return super().detect(frame)
    det = PausingBlob(1.0)
    per = garment_perception(r, detector=det)
    runner = make_runner(r, per)
    moves, executed, unspy = spy(r, runner)
    grips = []
    orig_grip = r.claw.grip
    r.claw.grip = lambda close: (grips.append(close), orig_grip(close))[1]
    try:
        out = sup.run_task(runner)
    finally:
        unspy()
        r.claw.grip = orig_grip
    assert out is None and sup.state == "PAUSED", (sup.state, sup.reasons[-2:])
    assert det.threads and det.threads[0].startswith("startup-pumped")           # the detection ran to its end on the pumped worker
    assert [m[0] for m in moves] == ["scan", "approach item-1"], moves     # the approach was planned (after the pumped dry run) ...
    assert np.linalg.norm(r.world.p - snap[0]) < 1e-3, (r.world.p, snap)      # ... and held by the pause: the claw is still at the scan point
    assert grips == [] and r.world.items[0]["state"] == "floor" and r.ctx.co.pause_requested is None
    _holding_still(r, sup, 1.0)
    sup.resume()
    assert sup.state == "READY"
    reset(r)


def test_b6_an_exception_of_the_pumped_detector_reaches_run_unchanged_with_the_robot_holding(rig):
    r, sup = rig
    reset(r)
    home(r)
    err = ImportError("The real detector needs Ultralytics")

    class Missing:
        mapper = None

        def detect(self, frame=None):
            time.sleep(0.4)
            raise err
    per = garment_perception(r, detector=Missing())
    runner = make_runner(r, per)
    m = PumpGapMeter(r.co, couple=True, armed=True)
    try:
        with pytest.raises(ImportError) as e:
            runner.run()
    finally:
        m.close()
    assert e.value is err and _pump_threads() == [] and m.violations == []
    assert m.max_stall_s < r.cfg.faults.lease_s / 3, m.worst_text()
    _holding_still(r, sup, 1.0)
    reset(r)


def test_b9_an_unset_hamper_is_a_fault_not_a_pause_current_behaviour_recorded(rig):
    """Characterisation (pre-existing, not in the diff): ``tasks.hamper_room_m`` null raises a plain StartupAbort, so the supervisor goes to
    FAULT (not PAUSED) with nothing moved. Recorded here with what ``acknowledge`` makes of it. Kept last: it may leave the shared rig in a
    state other than READY."""
    r, sup = rig
    reset(r)
    home(r)
    pos0 = r.ctx.co.positions().copy()
    out = sup.run_task(make_runner(r, hamper_room_m=None))
    state = sup.state
    assert out is None and np.allclose(r.ctx.co.positions(), pos0, atol=1e-9) and "hamper_room_m not configured" in sup.reasons[-1]
    sup.acknowledge()
    print(f"\n[B9] unset hamper: supervisor {state} after the task, {sup.state} after acknowledge; stations {_stations(r.ctx.co)}")
    assert state == "FAULT"
