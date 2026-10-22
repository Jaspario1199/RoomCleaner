"""Reach of the task layer, refused BEFORE any motion (lead's rehearsals with config/robot.sim3_34.json; results in
verification/task_pumping_results.md).

* the startup ends wherever its last calibration pose left the claw, which can be outside the volume it validated (the rehearsal:
  claw at (1.47, 0.674), validated hull x 0.94-2.41, y 0.79-1.96): the first scan is then planned above the claw's start point
  (``cfg.start_point_xy``), else above the centroid of the trusted volume; none allowed -> the task is refused with nothing moved;
* the hamper's transport / release pose is checked at the start (it used to fail after the grip, at TRANSPORT, with the garment in the
  jaws): refused with the hamper's position and the trusted extents;
* an item whose approach or grip pose is outside the trusted volume, or that cannot be planned to (workspace / tension), is failed
  "unreachable: ..." and the run goes on; motion faults, pauses and planning refusals after the grip closed still abort.

One simulated three-station startup (about 90 s) is shared by the whole module (and by tests/cdpr/test_task_pumping.py through
``started``); every test puts the robot back ("home") first and clears the items.
"""
import copy
import dataclasses

import numpy as np
import pytest

from scipy.spatial import ConvexHull

from roomcleaner.cdpr.coordinator import MotionResult
from roomcleaner.cdpr import tasks as T
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.sim.world import FloorBoard
from roomcleaner.cdpr.startup import StartupAbort
from roomcleaner.cdpr.supervisor import Supervisor
from roomcleaner.cdpr.tasks import TaskRunner, TrustedVolume
from roomcleaner.cdpr.trajectory import PlanError, plan_line, plan_line_from

from .simkit import ModelFrameItemPerception, assert_no_eq_failures, item_offsets_with_small_statics_tilt as _tilt_offsets
from .test_three_station import fast3

PROFILE = "config/robot.sim3_34.json"
# tonight's operator setting is the item's real weight (about 0.2-0.3 kg), not the 0.9 kg of the jeans requirement: with 0.9 kg the
# cable tension limit of this three-cable profile leaves NO position carriable at the transport height (see
# test_with_the_jeans_payload_of_0_9_kg_every_item_is_unreachable_before_any_grip and verification/task_pumping_results.md)
PAYLOAD_KG = 0.3
_RUN: dict = {}


def started(tmp_path_factory, seed=3):
    """(robot, supervisor) after a full simulated startup of the three-cable-hole three-station profile, cached per process."""
    if seed not in _RUN:
        tmp = tmp_path_factory.mktemp(f"task_reach_{seed}")
        r = SimRobot(fast3(PROFILE), seed=seed, data_dir=tmp, camera_kw={"board": FloorBoard.nominal(0.15)})
        sup = Supervisor(r.ctx, state_path=tmp / "state.json", ledger_path=tmp / "ledger.json")
        rep = sup.start()
        assert sup.state == "READY", rep.reasons
        assert_no_eq_failures(r, "task reach startup")
        r.world.hamper = (np.asarray(r.cfg.tasks.hamper_room_m), r.cfg.tasks.hamper_radius_m)
        _RUN[seed] = (r, sup)
    return _RUN[seed]


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    return started(tmp_path_factory)


# ------------------------------------------------------------------ helpers
def goto(r, q):
    """Move the claw to ``q`` (room frame) with a planned line, like a calibration move (no task layer, no trusted-volume check)."""
    ctx = r.ctx
    res = ctx.co.execute(plan_line_from(ctx.model, ctx.co.positions(), np.asarray(q, float), ctx.lim, ws=ctx.ws, label="test goto"))
    assert res.ok, res.reason


def reset(r):
    w = r.world
    w.items.clear()
    w.held = None
    w.mass = w.base_mass
    r.claw.grip(False)


def claw_xyz(r):
    return r.ctx.model.pose_from_positions(r.ctx.co.positions())[0]


def carry_plannable(r, xy, height=0.05, margin=0.9, payload=PAYLOAD_KG):
    """Can an item at ``xy`` be carried to the hamper with ``payload`` kg? The same legs as ``TaskRunner._handle`` (lift, verify shift,
    raise, transport) planned with the real path check and the tension limit scaled by ``margin``. The tests that deliver items choose
    items where it can, so that they test reach and not the tension limit."""
    ctx, tc = r.ctx, r.cfg.tasks
    zf = -float(r.cfg.claw.lowest_point_body_m[2])
    hamper = np.asarray(tc.hamper_room_m, float)
    above = np.array([xy[0], xy[1], zf + height + tc.approach_clearance_m])
    grip = np.array([xy[0], xy[1], zf + tc.grip_clearance_m])
    d = hamper - above[:2]
    shift = above.copy()
    shift[:2] += d / np.linalg.norm(d) * min(tc.verify_shift_m, float(np.linalg.norm(d)))
    z_t = max(above[2], zf + tc.hamper_height_m + tc.release_clearance_m)
    legs = [(grip, above), (above, shift), (shift, np.array([shift[0], shift[1], z_t])),
            (np.array([shift[0], shift[1], z_t]), np.array([hamper[0], hamper[1], z_t]))]
    lim = dataclasses.replace(ctx.lim, mass_kg=r.cfg.claw.mass_kg + payload, t_max=ctx.lim.t_max * margin)
    try:
        for a, b in legs:
            plan_line(ctx.model, a, b, lim, ws=ctx.ws, allow_low=True)
    except PlanError:
        return False
    return True


def item_offsets(r, n=2, pool=14):
    """Offsets (from the claw, as ``item_offsets_with_small_statics_tilt``) of ``n`` items that can be served AND carried."""
    c = claw_xyz(r)[:2]
    served = []
    for k in range(pool, 0, -1):                      # the helper wants exactly k offsets: take as many as it finds (a prefix, nearest first)
        try:
            served = _tilt_offsets(r.ctx, None, n=k)
            break
        except AssertionError:
            continue
    out = [o for o in served if carry_plannable(r, c + o)]
    if len(out) < (n or 1):
        pytest.skip(f"fewer than {n or 1} items that can be carried with the full payload from here for this startup")
    return out if n is None else out[:n]


def hull_extents(vol):
    """(lo, hi) of the validated points (computed here, independently of TrustedVolume.extents)."""
    pts = np.asarray(vol.hull.points)
    return pts.min(0), pts.max(0)


def hull_centroid_xy(vol):
    """xy of the volume centroid of the convex hull (independent of TrustedVolume.centroid_xy: cones from the vertex mean to the facets)."""
    pts = np.asarray(vol.hull.points)
    o = pts.mean(0)
    num, tot = np.zeros(3), 0.0
    for tri in pts[ConvexHull(pts).simplices]:
        v = abs(np.linalg.det(tri - o)) / 6.0
        num += v * (tri.sum(0) + o) / 4.0
        tot += v
    return (num / tot)[:2]


def scan_candidates(r):
    """The contract of the first scan point: the start point, then the centroid of the trusted volume, at the scan height."""
    vol = TrustedVolume(r.ctx)
    z = r.cfg.tasks.scan_height_m
    cands = [np.r_[r.cfg.start_point_xy(), z], np.r_[hull_centroid_xy(vol), z]]
    return vol, cands


def home(r):
    """The claw above the first allowed scan candidate (the start point, else the centroid) at 1.0 m; items are chosen from here."""
    reset(r)
    vol, cands = scan_candidates(r)
    ok = [c for c in cands if vol.allows(c)]
    assert ok, f"neither the start point nor the centroid of the trusted volume is allowed at the scan height: {hull_extents(vol)}"
    goto(r, np.r_[ok[0][:2], 1.0])
    return ok[0]


def outside_point(r, vol, z=1.0):
    """A point just outside the validated hull (0.12-0.3 m) that is inside the workspace: where a startup could have left the claw."""
    lo, hi = hull_extents(vol)
    c = hull_centroid_xy(vol)
    geo = r.ctx.model.geometry
    for d in (0.12, 0.2, 0.3):
        for xy in ((c[0], lo[1] - d), (c[0], hi[1] + d), (lo[0] - d, c[1]), (hi[0] + d, c[1])):
            q = np.array([xy[0], xy[1], z])
            if vol.hull.find_simplex(q) < 0 and not r.ctx.ws.violations(geo, q):
                return q
    pytest.skip("no point just outside the hull is inside the workspace for this startup")


def make_runner(r, perception=None, **tasks_changes):
    """A TaskRunner whose task configuration is a copy with ``tasks_changes`` (the shared config is never modified)."""
    runner = TaskRunner(r.ctx, perception or ModelFrameItemPerception(r.world))
    runner.tc = dataclasses.replace(r.cfg.tasks, **{"max_payload_kg": PAYLOAD_KG, **tasks_changes})
    return runner


def spy(r, runner):
    """Record every planned task move (label, target) and every executed plan."""
    moves, executed = [], []
    orig_move, orig_exec = runner._move, r.co.execute

    def move(q, **kw):
        moves.append((kw.get("label"), np.array(q, float)))
        return orig_move(q, **kw)

    def execute(plan, *a, **k):
        executed.append(plan)
        return orig_exec(plan, *a, **k)
    runner._move = move
    r.co.execute = execute
    return moves, executed, lambda: setattr(r.co, "execute", orig_exec) or delattr(r.co, "execute")


# ============================================================ 1. the first scan
def test_the_first_scan_is_planned_above_the_start_point_when_the_claw_ended_outside_the_trusted_volume(rig):
    r, sup = rig
    scan_xy = home(r)[:2]
    c = r.world.p[:2].copy()
    offs = item_offsets(r)
    for k, off in enumerate(offs):
        r.world.add_item(f"item{k}", c + off, mass=0.5)
    vol, cands = scan_candidates(r)
    outside = outside_point(r, vol)
    goto(r, outside)                                                    # where the last calibration pose could have left it
    here = claw_xyz(r)
    assert vol.hull.find_simplex(here) < 0 and not vol.allows(np.r_[here[:2], r.cfg.tasks.scan_height_m])
    expected = next(c_ for c_ in cands if vol.allows(c_))
    runner = make_runner(r)
    moves, executed, unspy = spy(r, runner)
    try:
        out = sup.run_task(runner)
    finally:
        unspy()
    assert out is not None, (sup.state, sup.reasons[-2:])             # old code: "scan: target [...] outside the trusted volume", FAULT
    assert sorted(out["done"]) == ["item0", "item1"] and not out["failed"] and sup.state == "READY", (out, sup.reasons[-2:])
    assert moves[0][0] == "scan" and np.allclose(moves[0][1], expected), (moves[0], expected)
    assert np.allclose(moves[0][1][:2], scan_xy) and runner.log and "outside the trusted volume" in runner.log[0]
    assert any(e[1] == "TASK/SCAN" and ("start point" in e[2] or "centre of the calibrated volume" in e[2]) for e in sup.events)
    assert_no_eq_failures(r, "scan fallback task")


def test_a_scan_above_the_claw_is_unchanged_when_the_claw_is_inside_the_trusted_volume(rig):
    r, sup = rig
    home(r)
    runner = make_runner(r)
    here = runner._here()
    q, note = runner._scan_point(here)
    assert note == "" and np.allclose(q, [here[0], here[1], r.cfg.tasks.scan_height_m])


def test_the_centroid_of_the_hull_is_the_volume_weighted_centre_and_lies_inside_it(rig):
    r, _ = rig
    vol = TrustedVolume(r.ctx)
    c = vol.centroid_xy()
    lo, hi = vol.extents()
    assert np.allclose(lo, hull_extents(vol)[0]) and np.allclose(hi, hull_extents(vol)[1]) and np.all(c > lo[:2]) and np.all(c < hi[:2])
    assert np.allclose(c, hull_centroid_xy(vol), atol=1e-6)
    # a unit cube: 8 corners, centroid (0.5, 0.5)
    cube = copy.copy(vol)
    from scipy.spatial import Delaunay
    cube.hull = Delaunay(np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float))
    assert np.allclose(cube.centroid_xy(), [0.5, 0.5])
    cube.hull = None
    assert cube.centroid_xy() is None and cube.extents() is None


def test_no_allowed_scan_point_refuses_the_task_before_any_motion(rig):
    r, sup = rig
    home(r)
    runner = make_runner(r, scan_height_m=3.5)                          # above the whole validated volume: no candidate is allowed
    moves, executed, unspy = spy(r, runner)
    p0 = r.world.p.copy()
    try:
        with pytest.raises(StartupAbort) as e:
            runner.run()
    finally:
        unspy()
    assert e.value.paused and "scan: no point at the scan height 3.50 m" in e.value.reason and "nothing was moved" in e.value.reason
    assert "above the claw's start point" in e.value.reason and "x " in e.value.reason       # what was tried, and the trusted extents
    assert moves == [] and executed == [] and np.allclose(r.world.p, p0)


# ============================================================ 2. the hamper
def _outside_hamper(r, vol):
    lo, hi = hull_extents(vol)
    c = hull_centroid_xy(vol)
    z_t = -float(r.cfg.claw.lowest_point_body_m[2]) + r.cfg.tasks.hamper_height_m + r.cfg.tasks.release_clearance_m
    for xy in ((lo[0] - 0.3, c[1]), (hi[0] + 0.3, c[1]), (c[0], lo[1] - 0.3), (c[0], hi[1] + 0.3)):
        if not vol.allows(np.array([xy[0], xy[1], z_t])):
            return [float(xy[0]), float(xy[1])]
    raise AssertionError("every hamper position around the hull is allowed?")


def test_a_hamper_outside_the_trusted_volume_is_refused_before_any_motion_with_its_position_and_the_trusted_extents(rig):
    r, sup = rig
    home(r)
    vol = TrustedVolume(r.ctx)
    ham = _outside_hamper(r, vol)
    r.world.add_item("sock", r.world.p[:2] + [0.1, 0.1])               # there is work to do: the old code would pick it up first
    runner = make_runner(r, hamper_room_m=ham)
    moves, executed, unspy = spy(r, runner)
    p0 = r.world.p.copy()
    try:
        with pytest.raises(StartupAbort) as e:
            runner.run()
    finally:
        unspy()
    lo, hi = hull_extents(vol)
    msg = e.value.reason
    assert e.value.paused and f"hamper at ({ham[0]:.2f}, {ham[1]:.2f}) is outside the calibrated volume" in msg, msg
    assert f"x {lo[0]:.2f}-{hi[0]:.2f}, y {lo[1]:.2f}-{hi[1]:.2f}" in msg and "move it toward the middle of the calibrated area" in msg
    assert "nothing was moved" in msg
    assert moves == [] and executed == [] and np.allclose(r.world.p, p0) and r.world.items[0]["state"] == "floor"
    reset(r)


def test_the_supervisor_pauses_on_a_refused_hamper_and_resume_returns_to_ready(rig):
    r, sup = rig
    home(r)
    ham = _outside_hamper(r, TrustedVolume(r.ctx))
    out = sup.run_task(make_runner(r, hamper_room_m=ham))
    assert out is None and sup.state == "PAUSED" and "outside the calibrated volume" in sup.reasons[-1]
    sup.resume()
    assert sup.state == "READY", sup.reasons[-2:]


def test_with_trust_verified_the_hamper_is_judged_against_the_workspace_and_says_so(rig):
    r, sup = rig
    home(r)
    lg = r.ctx.ledger
    level, basis, reasons = lg.level, lg.verified_basis, list(lg.trust_reasons)
    lg.set_level("VERIFIED", basis="margin")
    try:
        runner = make_runner(r, hamper_room_m=[-3.0, 0.5])
        with pytest.raises(StartupAbort, match=r"hamper at \(-3\.00, 0\.50\) is outside the workspace \(") as e:
            runner.run()
        assert e.value.paused
        assert runner.vol.hull is None                                  # (VERIFIED: no hull, the workspace decides)
    finally:
        lg.set_level(level, basis=basis, reasons=reasons)
    assert lg.level == level and lg.trust_reasons == reasons


# ============================================================ 3. an unreachable item
def _item_outside(r, vol, scan_xy, min_clear=0.08):
    """A floor point inside the scan footprint whose approach and grip poses are outside the trusted volume (by ``min_clear``)."""
    tc = r.cfg.tasks
    zf = -float(r.cfg.claw.lowest_point_body_m[2])
    lo, hi = hull_extents(vol)
    for d in (0.15, 0.2, 0.3, 0.4):
        for xy in ((scan_xy[0], lo[1] - d), (scan_xy[0], hi[1] + d), (lo[0] - d, scan_xy[1]), (hi[0] + d, scan_xy[1])):
            hover = np.array([xy[0], xy[1], zf + 0.05 + tc.approach_clearance_m])
            grip = np.array([xy[0], xy[1], zf + tc.grip_clearance_m])
            if (not vol.allows(hover) and not vol.allows(grip, below_ok=True)
                    and np.max(np.abs(np.asarray(xy) - scan_xy)) < 0.6):
                return np.asarray(xy, float)
    pytest.skip("no point inside the scan footprint is outside the trusted volume for this startup")


def test_an_unreachable_item_is_failed_with_its_reason_and_the_run_goes_on_to_the_next_item(rig):
    r, sup = rig
    scan_xy = home(r)[:2]
    c = r.world.p[:2].copy()
    vol = TrustedVolume(r.ctx)
    a = _item_outside(r, vol, scan_xy)
    d_a = np.linalg.norm(a - scan_xy)
    offs = item_offsets(r, n=None)
    b_off = next((o for o in offs if np.linalg.norm(c + o - scan_xy) > d_a + 0.03), None)
    if b_off is None:
        pytest.skip("no reachable item farther from the scan point than the unreachable one")
    r.world.add_item("lost", a)                                         # nearer to the scan point: handled first
    r.world.add_item("sock", c + b_off)
    runner = make_runner(r)
    moves, executed, unspy = spy(r, runner)
    try:
        out = sup.run_task(runner)
    finally:
        unspy()
    assert out is not None, (sup.state, sup.reasons[-2:])
    assert out["done"] == ["sock"] and sup.state == "READY", (out, sup.reasons[-2:])
    assert [f[0] for f in out["failed"]] == ["lost"] and out["failed"][0][1].startswith("unreachable: approach lost: target ")
    assert "outside the trusted volume" in out["failed"][0][1]
    assert not [m for m in moves if m[0] and "lost" in m[0]]            # not one move was planned towards it
    lost = next(it for it in r.world.items if it["id"] == "lost")
    sock = next(it for it in r.world.items if it["id"] == "sock")
    assert lost["state"] == "floor" and sock["state"] == "hamper"
    reset(r)


def _two_reachable_items(r):
    scan_xy = home(r)[:2]
    c = r.world.p[:2].copy()
    offs = item_offsets(r)
    for name, off in zip(("first", "second"), offs):
        r.world.add_item(name, c + off)
    return scan_xy


def test_a_workspace_refusal_while_planning_the_approach_fails_that_item_and_the_run_goes_on(rig, monkeypatch):
    r, sup = rig
    _two_reachable_items(r)
    real = T.plan_line_from
    seen = {"n": 0}

    def plan(model, P, q, lim, **kw):
        if str(kw.get("label", "")).startswith("approach") and seen["n"] == 0:
            seen["n"] = 1
            raise PlanError("workspace: floor point (0.1, 0.1) is outside the test triangle")
        return real(model, P, q, lim, **kw)
    monkeypatch.setattr(T, "plan_line_from", plan)
    runner = make_runner(r)
    out = runner.run()
    assert len(out["done"]) == 1 and len(out["failed"]) == 1, out
    assert out["failed"][0][1].startswith("unreachable: approach ") and "workspace: floor point" in out["failed"][0][1]
    reset(r)


def test_a_tension_refusal_while_planning_the_descent_fails_that_item_with_the_jaws_open_and_empty(rig, monkeypatch):
    r, sup = rig
    _two_reachable_items(r)
    real = T.plan_line_from
    seen = {"n": 0}

    def plan(model, P, q, lim, **kw):
        if str(kw.get("label", "")).startswith("descend") and seen["n"] == 0:
            seen["n"] = 1
            raise PlanError("tension infeasible at [1. 1. 0.1] (max 41.0 N against 40.0 N)")
        return real(model, P, q, lim, **kw)
    monkeypatch.setattr(T, "plan_line_from", plan)
    out = make_runner(r).run()
    assert len(out["done"]) == 1 and len(out["failed"]) == 1, out
    assert out["failed"][0][1].startswith("unreachable: descend ") and "tension infeasible" in out["failed"][0][1]
    assert r.world.held is None
    reset(r)


def test_with_the_jeans_payload_of_0_9_kg_every_item_is_unreachable_before_any_grip(rig):
    """The default ``tasks.max_payload_kg`` is 0.9 kg (jeans). On this three-cable profile the cable tension limit (15 N, 12 N with the
    planner's margin) leaves no position carriable at the transport height with that mass, so the carry dry run refuses every item
    BEFORE the claw moves towards it; with the item's real weight (0.3 kg) the same item is delivered. Without the dry run the task
    picked the item up and aborted in the air at 'raise' (rehearsal: tension infeasible, 12.1 N > 12.0 N)."""
    r, sup = rig
    home(r)
    off = item_offsets(r, n=1)[0]                                       # carriable with 0.3 kg
    r.world.add_item("sock", r.world.p[:2] + off)
    runner = make_runner(r, max_payload_kg=0.9)
    moves, executed, unspy = spy(r, runner)
    grips = []
    orig_grip = r.claw.grip
    r.claw.grip = lambda close: (grips.append(close), orig_grip(close))[1]
    try:
        out = runner.run()
    finally:
        unspy()
        r.claw.grip = orig_grip
    assert out["done"] == [] and [f[0] for f in out["failed"]] == ["sock"], out
    assert out["failed"][0][1].startswith("unreachable: ") and "tension infeasible" in out["failed"][0][1], out["failed"]
    assert grips == [] and not [m for m in moves if m[0] and "sock" in m[0]]       # nothing gripped, nothing moved towards the item
    assert r.world.items[0]["state"] == "floor"
    reset(r)


# ============================================================ 4. what still aborts
def test_other_planning_errors_motion_faults_and_pauses_still_abort_the_task(rig, monkeypatch):
    r, sup = rig
    _two_reachable_items(r)
    real = T.plan_line_from
    # a model that disagrees with the cables is about the system, not about the item
    monkeypatch.setattr(T, "plan_line_from", lambda *a, **k: (_ for _ in ()).throw(
        PlanError("actual positions differ from the model by [9.0, 0.0, 0.0] mm of cable: model and cables disagree")))
    with pytest.raises(StartupAbort, match="model and cables disagree") as e:
        make_runner(r).run()
    assert not isinstance(e.value, T.TaskUnreachable)
    monkeypatch.setattr(T, "plan_line_from", real)
    # a motion that fails (station fault) and a pause
    orig_exec = r.co.execute
    for reason, paused in (("station B reported fault 4", False), ("paused: operator", True)):
        monkeypatch.setattr(r.co, "execute", lambda plan, *a, _reason=reason, **k: MotionResult(False, _reason))
        with pytest.raises(StartupAbort) as e:
            make_runner(r).run()
        assert reason in e.value.reason and e.value.paused == paused and not isinstance(e.value, T.TaskUnreachable)
    monkeypatch.setattr(r.co, "execute", orig_exec)
    reset(r)


def test_a_workspace_refusal_after_the_grip_closed_aborts_the_task_it_is_not_an_unreachable_item(rig, monkeypatch):
    r, sup = rig
    _two_reachable_items(r)
    real = T.plan_line_from

    def plan(model, P, q, lim, **kw):
        if str(kw.get("label", "")).startswith("lift"):                 # the garment is in the jaws by now
            raise PlanError("workspace: floor point (0.1, 0.1) is outside the test triangle")
        return real(model, P, q, lim, **kw)
    monkeypatch.setattr(T, "plan_line_from", plan)
    with pytest.raises(StartupAbort, match="lift .*workspace: floor point") as e:
        make_runner(r).run()
    assert e.value.state == "TASK"                                       # (run() lets it out after the grip: the item is not skipped)
    assert r.world.held is not None                                      # the item really is in the jaws: skipping to the next one would be wrong
    reset(r)


# ============================================================ 5. keep-alive over a whole task
def test_a_whole_task_never_leaves_the_armed_stations_unpumped_for_a_third_of_the_lease(rig):
    """Two items delivered with the clock-coupled pump-gap meter attached (tests/cdpr/test_keepalive_pumping.py::PumpGapMeter): the
    planned moves of the task layer are the longest computations on the command thread (47-241 ms each, 264 ms the largest gap of
    the whole task before the change, which is 0.9 x the lease); now no gap exceeds a third of the lease and no pumped computation
    touches the coordinator. The machine is shared: rerun alone before concluding anything from a failure."""
    from roomcleaner.cdpr.protocol import Fault

    from .test_keepalive_pumping import PumpGapMeter
    r, sup = rig
    _two_reachable_items(r)
    lease = r.cfg.faults.lease_s
    runner = make_runner(r)
    m = PumpGapMeter(r.co, couple=True, armed=True)
    try:
        out = sup.run_task(runner)
    finally:
        m.close()
    r.co.wait(200000)
    print(f"\n[whole task] {m.n_pumps} pumps, largest gap between pumps {m.max_stall_s * 1e3:.0f} ms stall / {m.max_wall_s * 1e3:.0f} ms wall; "
          f"{len(m.long_stalls)} gaps above 40 ms; lease {lease * 1e3:.0f} ms; {m.worst_text()}")
    assert out is not None and sorted(out["done"]) == ["first", "second"] and not out["failed"], (out, sup.reasons[-2:])
    assert all(r.co.links[s].tel["flt"] != Fault.LEASE for s in r.co.ids)
    assert m.violations == []
    assert m.max_stall_s < lease / 3, m.worst_text()
    reset(r)
