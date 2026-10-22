"""Station keep-alive during the long computations of a TASK (results in verification/task_pumping_results.md).

While a command owns the robot the idle host loop does not pump the stations (Service.idle_tick), so a computation of more than a
fraction of faults.lease_s (0.3 s in simulation) on the command thread latches Fault.LEASE on every armed station: they hold torque and
the task aborts. The startup pumps its long calls with ``StartupSequencer._pumped``; the task layer did not:

* ``ClawGarmentPerception`` called ``self.det.detect(img)`` directly. On hardware that is YOLO-World: a CPU inference takes a large
  fraction of a second or more, and the model loads lazily on the FIRST call (seconds, possibly a weights download).
* ``TaskRunner._move`` ran ``plan_line_from`` on the command thread: its path check solves the cable tensions at every path point both
  ways, with payload and dynamics (47-241 ms per task move on this machine, 3-station profile, ``verification/task_pumping_results.md``).

Both now go through ``startup.run_pumped`` (the body of ``StartupSequencer._pumped``, extracted unchanged).

Method (as tests/cdpr/test_keepalive_pumping.py): the simulated clock follows wall time through ``PumpGapMeter(couple=True)``: a host stall
between two pumps advances the stations with no ping, as on a real runtime, so a stall over the lease latches Fault.LEASE for real. The
detector is replaced by one that really sleeps (or burns CPU) for the stated time. The tests are written to FAIL on the code before the
fix (checked against ``git archive HEAD``): the stall equals the detector's time, Fault.LEASE is latched, the detector runs on the main
thread. The machine is shared: a wall-clock gap test that fails is to be rerun alone before concluding anything.
"""
import ast
import inspect
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr import garments as G
from roomcleaner.cdpr import startup as ST
from roomcleaner.cdpr import tasks as T
from roomcleaner.cdpr.frames import make_T, rot_z
from roomcleaner.cdpr.garments import ClawFloorMapper, ClawGarmentPerception
from roomcleaner.cdpr.protocol import Fault, State
from roomcleaner.cdpr.startup import StartupAbort, StartupSequencer
from roomcleaner.cdpr.trajectory import PlanError
from roomcleaner.perception.detector import Detection, Detector

from .test_keepalive_pumping import PumpGapMeter, _armed_model_robot, _pump_threads

IMG = np.full((600, 800, 3), 90, np.uint8)
DETS = [Detection(np.zeros(3), "sock", 0.9, bbox=(300.0, 250.0, 340.0, 290.0)),
        Detection(np.zeros(3), "towel", 0.1, bbox=(100.0, 100.0, 150.0, 150.0)),       # below min_confidence: dropped
        Detection(np.zeros(3), "jeans", 0.8, bbox=None),                                 # no box: dropped
        Detection(np.zeros(3), "tee", 0.7, bbox=(500.0, 300.0, 560.0, 360.0))]


class SlowDetector(Detector):
    """A detector that takes real time: ``first_s`` for the first call (the lazy model load), ``delay_s`` for the others, either
    sleeping (a torch inference releases the GIL) or burning CPU in Python (``burn``: holds the GIL, the worst case for the command
    thread). Records the thread and the duration of every call."""

    def __init__(self, dets=DETS, delay_s=1.0, first_s=None, burn=False):
        self.dets, self.delay_s, self.first_s, self.burn = dets, delay_s, first_s, burn
        self.mapper = None
        self.calls = []

    def detect(self, frame=None):
        d = self.first_s if (not self.calls and self.first_s is not None) else self.delay_s
        t0 = time.monotonic()
        if self.burn:
            while time.monotonic() - t0 < d:
                sum(i * i for i in range(500))
        else:
            time.sleep(d)
        self.calls.append((threading.current_thread().name, d, time.monotonic() - t0, self.mapper))
        return list(self.dets)


class StillClawPerception(ClawGarmentPerception):
    """The real perception with the view of a settled claw: ``_view`` (marker still pose, frame grab) is unchanged by the fix and not
    under test here; everything after it -- scan / holding / item_at, the detector call, the mapping -- is the real code."""

    def _view(self, ctx):
        p = ctx.model.pose_from_positions(ctx.co.positions())[0]
        T_R_B = make_T(rot_z(0.0), p)
        return IMG, ClawFloorMapper(self.cam, T_R_B @ ctx.T_B_C), T_R_B


def _perception(r, detector):
    return StillClawPerception(detector, r.camera, lambda: IMG)


def _stations(co):
    return [(co.links[s].tel["st"], co.links[s].tel["flt"]) for s in co.ids]


def _run_metered(r, fn):
    """``fn()`` under the clock-coupled pump-gap meter; returns (result, meter). The stations get 0.2 s of simulated time afterwards so
    that a latched fault shows in their telemetry."""
    m = PumpGapMeter(r.co, couple=True, armed=True)
    try:
        out = fn()
    finally:
        m.close()
    r.co.wait(200000)
    return out, m


def _alive(co):
    return _stations(co) == [(State.IDLE, 0)] * len(co.ids)


# ===================================================================== (a) a detector of one second inside a task scan
@pytest.mark.parametrize("burn", [False, True], ids=["inference-sleeps", "inference-burns-cpu"])
def test_a_task_scan_with_a_detector_that_takes_one_second_keeps_every_station_alive(burn):
    """The detector takes 1.0 s (burn: 0.6 s of pure-Python CPU, which holds the GIL), the lease is 0.3 s. Before the fix the command
    thread sat in ``detect`` for the whole time: one gap of 1.0 s between two pumps and Fault.LEASE on every armed station. Now the
    detector runs on the pumped worker and the largest gap between two pumps stays under a third of the lease."""
    r, cfg = _armed_model_robot()
    lease = cfg.faults.lease_s
    det = SlowDetector(delay_s=0.6 if burn else 1.0, burn=burn)
    per = _perception(r, det)
    found, m = _run_metered(r, lambda: per.scan(r.ctx))
    print(f"\n[task scan, detector {det.calls[0][2]:.2f} s{' (burns CPU)' if burn else ''}] {m.n_pumps} pumps, largest gap between pumps "
          f"{m.max_stall_s * 1e3:.0f} ms (wall {m.max_wall_s * 1e3:.0f} ms), lease {lease * 1e3:.0f} ms; stations {_stations(r.co)}")
    assert [s.id for s in found] == ["sock-1", "tee-2"]
    assert det.calls[0][2] >= det.delay_s - 0.01                                  # the detector really took its time
    assert all(f != Fault.LEASE for _st, f in _stations(r.co)) and _alive(r.co), _stations(r.co)
    assert m.max_stall_s < lease / 3, m.worst_text()
    assert det.calls[0][0].startswith("startup-pumped")                           # off the command thread
    assert m.n_pumps > 20 and m.violations == [] and _pump_threads() == []


def test_the_unpumped_one_second_detector_would_latch_the_lease_the_meter_sees_it():
    """The control for the test above: the same detector called directly on the command thread (what the code did) is a gap of its
    own length and latches Fault.LEASE on all four stations in the clock-coupled simulation."""
    r, cfg = _armed_model_robot()
    det = SlowDetector(delay_s=1.0)
    _out, m = _run_metered(r, lambda: det.detect(IMG))
    assert m.max_stall_s > 0.9 and [f for _st, f in _stations(r.co)] == [Fault.LEASE] * 4
    assert [st for st, _f in _stations(r.co)] == [State.FAULT] * 4


# ===================================================================== (b) the lazy model load of the first call
def test_the_model_load_of_the_first_detector_call_takes_three_seconds_and_scan_holding_item_at_all_stay_pumped():
    """YoloWorldDetector loads its weights on the first ``detect`` (seconds, possibly a download). scan -> holding -> item_at reach the
    detector one after the other here (the first one takes 3.0 s, the others 0.15 s)."""
    r, cfg = _armed_model_robot()
    lease = cfg.faults.lease_s
    det = SlowDetector(delay_s=0.15, first_s=3.0)
    per = _perception(r, det)

    def task_perception_calls():
        found = per.scan(r.ctx)
        per.note_target(found[0])
        held = per.holding(r.ctx)
        delivered = per.item_at(r.ctx, found[0].xy, 0.2)
        return found, held, delivered
    (found, held, delivered), m = _run_metered(r, task_perception_calls)
    print(f"\n[first-call model load 3.0 s, then 0.15 s] {m.n_pumps} pumps, largest gap between pumps {m.max_stall_s * 1e3:.0f} ms, "
          f"lease {lease * 1e3:.0f} ms; stations {_stations(r.co)}")
    assert len(det.calls) == 3 and det.calls[0][2] >= 2.99 and all(c[0].startswith("startup-pumped") for c in det.calls)
    assert all(c[3] is not None for c in det.calls)                              # the pose-aware mapper was set before each call
    assert held[0] is False and delivered is True and len(found) == 2
    assert all(f != Fault.LEASE for _st, f in _stations(r.co)) and _alive(r.co), _stations(r.co)
    assert m.max_stall_s < lease / 3, m.worst_text()
    assert m.violations == [] and _pump_threads() == []


# ===================================================================== (c) the detector's results are unchanged
def _outputs(per, ctx):
    found = per.scan(ctx)
    per.note_target(found[0])
    held = per.holding(ctx)
    delivered = per.item_at(ctx, found[0].xy, 0.2)
    return ([(s.id, np.round(s.xy, 9).tolist(), s.height_m, s.confidence) for s in found], held, delivered, list(per.log),
            [(t.id, np.round(t.xy, 9).tolist(), t.label, t.seen) for t in per.tracks])


def test_detections_come_back_in_the_detectors_order_and_the_outputs_equal_those_of_the_direct_call(monkeypatch):
    r, cfg = _armed_model_robot()
    ctx = r.ctx
    pumped = _outputs(_perception(r, SlowDetector(delay_s=0.0)), ctx)
    monkeypatch.setattr(G, "run_pumped", lambda ctx_, fn, *a, **k: fn(*a, **k))        # the code before the fix: a direct call
    direct = _outputs(_perception(r, SlowDetector(delay_s=0.0)), ctx)
    assert pumped == direct
    assert [f[0] for f in pumped[0]] == ["sock-1", "tee-2"]                              # the detector's order, filters applied
    # and the sightings are the mapped box centres of those two detections
    per = _perception(r, SlowDetector(delay_s=0.0))
    _img, mapper, _T = per._view(ctx)
    assert np.allclose(pumped[0][0][1], mapper.pixel_to_floor(320.0, 270.0)) and np.allclose(pumped[0][1][1], mapper.pixel_to_floor(530.0, 330.0))


def test_an_exception_of_the_detector_reaches_the_caller_unchanged_and_no_worker_is_left():
    r, cfg = _armed_model_robot()
    err = ImportError("The real detector needs Ultralytics")

    class Missing(Detector):
        def detect(self, frame=None):
            time.sleep(0.05)
            raise err
    per = _perception(r, Missing())
    with pytest.raises(ImportError) as e:
        per.scan(r.ctx)
    assert e.value is err and _pump_threads() == [] and _alive(r.co)


def test_every_detector_call_of_the_garment_perception_is_the_argument_of_run_pumped():
    """Static guard: no ``<detector>.detect(...)`` call is left in garments.py; its one use is ``run_pumped(ctx, self.det.detect, img)``
    (the other ``run_pumped`` is the claw's frame grab, gated on ``claw.blocking_io``) and scan / holding / item_at pass their ``ctx``
    on to ``_detections``."""
    tree = ast.parse(inspect.getsource(G))
    direct = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "detect"]
    assert direct == []
    pumped = [[ast.unparse(a) for a in n.args[:3]] for n in ast.walk(tree)
              if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "run_pumped"]
    assert sorted(pumped) == [["ctx", "self.det.detect", "img"], ["ctx", "self.frame_fn"]]       # the detector, and the claw's frame grab
    users = {}
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_detections":
                users.setdefault(fn.name, []).append(ast.unparse(n.args[0]))
    assert users == {"scan": ["ctx"], "holding": ["ctx"], "item_at": ["ctx"]}


# ===================================================================== (d) a planned task move
def _verified_runner(r):
    """A TaskRunner on the armed robot with the workspace as its trusted volume (trust VERIFIED), no calibration needed to plan a stub."""
    r.ctx.ledger.set_level("VERIFIED", basis="margin")
    return T.TaskRunner(r.ctx, SimpleNamespace())


def test_the_path_check_of_a_task_move_runs_on_the_pumped_worker_and_keeps_the_stations_alive(monkeypatch):
    """``_move`` plans with ``plan_line_from`` (a stub that takes 1.0 s stands for hundreds of ms of tension solves: 47-241 ms measured per
    move); the stations' positions are read on the command thread and passed in, the stub's PlanError reaches ``_move``'s handler
    unchanged and becomes ``TaskUnreachable`` (a workspace refusal)."""
    r, cfg = _armed_model_robot()
    runner = _verified_runner(r)
    seen = {}

    def slow_plan(model, P, q, lim, **kw):
        seen.update(thread=threading.current_thread().name, P=P, model=model, ws=kw.get("ws"), label=kw.get("label"), mass=lim.mass_kg)
        time.sleep(1.0)
        raise PlanError("workspace: floor point (0.1, 0.1) is outside the test triangle")
    monkeypatch.setattr(T, "plan_line_from", slow_plan)
    q = np.array([cfg.room_m[0] / 2, cfg.room_m[1] / 2, 1.2])

    def move():
        with pytest.raises(StartupAbort) as e:
            runner._move(q, label="approach sock", payload=0.9)
        return e.value
    err, m = _run_metered(r, move)
    print(f"\n[task move, 1.0 s plan stub] {m.n_pumps} pumps, largest gap between pumps {m.max_stall_s * 1e3:.0f} ms, lease 300 ms")
    assert type(err).__name__ == "TaskUnreachable" and "approach sock: workspace: floor point" in err.reason and err.state == "TASK"
    assert seen["thread"].startswith("startup-pumped") and isinstance(seen["P"], np.ndarray) and seen["P"].shape == (4,)
    assert seen["model"] is r.ctx.model and seen["ws"] is r.ctx.ws and seen["label"] == "approach sock"
    assert seen["mass"] == pytest.approx(cfg.claw.mass_kg + 0.9)
    assert all(f != Fault.LEASE for _st, f in _stations(r.co)) and _alive(r.co)
    assert m.max_stall_s < cfg.faults.lease_s / 3, m.worst_text()
    assert m.violations == [] and _pump_threads() == []


def test_the_task_layer_runs_nothing_else_slow_on_the_command_thread_static_guard():
    """tasks.py: ``plan_line_from`` is only ever the argument of ``run_pumped``; the other calls of the runner are cheap by
    measurement (TrustedVolume 0.2 ms for 15 points, 12 ms for 1000; pose_from_positions 1-2 ms; Workspace.violations < 1 ms)."""
    tree = ast.parse(inspect.getsource(T))
    direct = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "plan_line_from"]
    assert direct == []
    pumped = [ast.unparse(n.args[1]) for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "run_pumped"]
    assert pumped == ["plan_line_from"]


# ===================================================================== (e) the helper itself
def test_pumped_of_the_sequencer_is_the_module_function_with_its_context(monkeypatch):
    calls = []
    monkeypatch.setattr(ST, "run_pumped", lambda ctx, fn, *a, **k: calls.append((ctx, fn, a, k)) or "result")
    ctx = SimpleNamespace(cfg=None, wait=lambda s: None)
    fn = lambda *a, **k: None
    assert StartupSequencer(ctx)._pumped(fn, 1, 2, x=3) == "result" and calls == [(ctx, fn, (1, 2), {"x": 3})]


def test_run_pumped_keeps_the_rules_of_pumped_results_exceptions_abort_switch_interval_and_constants(monkeypatch):
    steps = []
    ctx = SimpleNamespace(cfg=None, wait=lambda s: (steps.append(s), time.sleep(0.001)))
    assert ST.run_pumped(ctx, lambda a, b=0: a + b, 1, b=2) == 3
    err = RuntimeError("boom")
    with pytest.raises(RuntimeError) as e:
        ST.run_pumped(ctx, lambda: (_ for _ in ()).throw(err))
    assert e.value is err
    # the interval is lowered for the call and restored whatever happens; a shorter caller interval is kept
    old = sys.getswitchinterval()
    try:
        sys.setswitchinterval(0.005)
        assert ST.run_pumped(ctx, lambda: (time.sleep(0.03), sys.getswitchinterval())[1]) == pytest.approx(StartupSequencer.PUMP_SWITCH_INTERVAL_S)
        assert sys.getswitchinterval() == pytest.approx(0.005)
        # the constants are read from StartupSequencer at call time (the tests of the sequencer patch them there)
        steps.clear()
        monkeypatch.setattr(StartupSequencer, "PUMP_STEP_S", 0.05)
        ST.run_pumped(ctx, time.sleep, 0.03)
        assert steps and set(steps) == {0.05}
        # ctx.wait raising (abort, e-stop): at once, the worker is not waited for, the interval is back
        release = threading.Event()
        n = []

        def wait(s):
            n.append(s)
            if len(n) == 3:
                raise StartupAbort("TASK", "operator abort")
        t0 = time.monotonic()
        with pytest.raises(StartupAbort, match="operator abort"):
            ST.run_pumped(SimpleNamespace(cfg=None, wait=wait), release.wait, 30.0)
        assert time.monotonic() - t0 < 2.0 and sys.getswitchinterval() == pytest.approx(0.005)
        release.set()
    finally:
        sys.setswitchinterval(old)
    deadline = time.monotonic() + 5.0
    while _pump_threads() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert _pump_threads() == []


# ===================================================================== (f) the claw's blocking HTTP calls
class BlockingClaw:
    """A claw link like claw_link.HttpClawClient (``blocking_io``): grip() and the frame grab take 0.8 s of wall time (a 1 s urlopen
    timeout against a 0.3 s lease). Records the thread of every call."""
    blocking_io = True

    def __init__(self, delay_s=0.8):
        self.delay_s = delay_s
        self.calls = []

    def grip(self, close):
        time.sleep(self.delay_s)
        self.calls.append(("grip", bool(close), threading.current_thread().name))
        return True

    def frame(self):
        time.sleep(self.delay_s)
        self.calls.append(("frame", None, threading.current_thread().name))
        return IMG


class DirectClaw(BlockingClaw):
    """The simulator's kind of claw: no ``blocking_io`` attribute, so it is called directly on the command thread."""
    blocking_io = False


def test_the_real_http_claw_link_declares_blocking_io_and_the_simulators_claw_does_not():
    from roomcleaner.cdpr.claw_link import HttpClawClient
    from roomcleaner.cdpr.sim.world import SimClaw
    assert HttpClawClient.blocking_io is True and not hasattr(SimClaw, "blocking_io")


def test_the_grip_and_the_frame_grab_of_a_blocking_claw_are_pumped_and_no_station_latches_the_lease():
    """grip (HTTP POST) and the colour frame grab (HTTP GET) of the real claw link take up to their 1 s timeout; here 0.8 s each, with
    the clock-coupled meter attached. Unpumped each is a gap of 0.8 s (2.7x the lease)."""
    r, cfg = _armed_model_robot()
    claw = BlockingClaw()
    r.ctx.claw = claw
    runner = _verified_runner(r)
    per = _perception(r, SlowDetector(delay_s=0.0))
    per.frame_fn = claw.frame

    def work():
        ok = runner._grip(True)
        img = per._frame(r.ctx)
        runner._grip(False)
        return ok, img
    (ok, img), m = _run_metered(r, work)
    print(f"\n[claw I/O, grip + frame + grip at 0.8 s each] {m.n_pumps} pumps, largest gap between pumps {m.max_stall_s * 1e3:.0f} ms, "
          f"lease {cfg.faults.lease_s * 1e3:.0f} ms; stations {_stations(r.co)}")
    assert ok is True and img is IMG                                                # results pass through
    assert [c[:2] for c in claw.calls] == [("grip", True), ("frame", None), ("grip", False)]
    assert all(c[2].startswith("startup-pumped") for c in claw.calls)
    assert all(f != Fault.LEASE for _st, f in _stations(r.co)) and _alive(r.co), _stations(r.co)
    assert m.max_stall_s < cfg.faults.lease_s / 3, m.worst_text()
    assert m.violations == [] and _pump_threads() == []


def test_a_claw_without_blocking_io_is_called_directly_on_the_command_thread():
    """The simulator's claw stays unpumped (its calls go into the shared world that ctx.wait steps on this thread)."""
    r, cfg = _armed_model_robot()
    claw = DirectClaw(delay_s=0.0)
    r.ctx.claw = claw
    runner = _verified_runner(r)
    per = _perception(r, SlowDetector(delay_s=0.0))
    per.frame_fn = claw.frame
    runner._grip(True)
    per._frame(r.ctx)
    assert [c[2] for c in claw.calls] == ["MainThread", "MainThread"] and _pump_threads() == []


# ===================================================================== (g) the pre-grip dry run of the carry
def _item(r, dx=0.0, dy=0.0):
    c = np.array(r.cfg.room_m[:2], float) / 2 + [dx, dy]
    return T.ItemSighting("sock", c, 0.05, 0.9)


def test_the_dry_run_plans_lift_shift_raise_and_transport_with_the_payload_on_the_pumped_worker(monkeypatch):
    r, cfg = _armed_model_robot()
    runner = _verified_runner(r)
    runner.tc = __import__("dataclasses").replace(cfg.tasks, hamper_room_m=[cfg.room_m[0] * 0.8, cfg.room_m[1] * 0.5])
    hamper = np.asarray(runner.tc.hamper_room_m, float)
    item = _item(r, -0.3, 0.0)
    above = np.array([item.xy[0], item.xy[1], runner.zf + 0.05 + cfg.tasks.approach_clearance_m])
    grip = np.array([item.xy[0], item.xy[1], runner.zf + cfg.tasks.grip_clearance_m])
    seen = []
    real = T.plan_line

    def spy_plan(model, a, b, lim, **kw):
        seen.append((kw["label"], np.array(a), np.array(b), lim.mass_kg, kw.get("allow_low"), threading.current_thread().name))
        return real(model, a, b, lim, **kw)
    monkeypatch.setattr(T, "plan_line", spy_plan)
    assert runner._dry_run_carry("sock", above, grip, hamper) is None
    assert [s[0] for s in seen] == ["lift sock", "verify shift sock", "raise sock", "transport sock"]
    assert all(s[3] == pytest.approx(cfg.claw.mass_kg + cfg.tasks.max_payload_kg) for s in seen)
    assert [s[4] for s in seen] == [True, False, False, False] and all(s[5].startswith("startup-pumped") for s in seen)
    shift, z_t = runner._carry_poses(above, hamper)
    assert np.allclose(seen[0][1], grip) and np.allclose(seen[0][2], above) and np.allclose(seen[1][2], shift)
    assert np.allclose(seen[2][2], [shift[0], shift[1], z_t]) and np.allclose(seen[3][2], [hamper[0], hamper[1], z_t])
    assert np.linalg.norm(shift[:2] - above[:2]) == pytest.approx(cfg.tasks.verify_shift_m)


def test_a_carry_that_cannot_be_planned_fails_the_item_as_unreachable_before_the_claw_moves_or_grips(monkeypatch):
    r, cfg = _armed_model_robot()
    runner = _verified_runner(r)
    runner.tc = __import__("dataclasses").replace(cfg.tasks, hamper_room_m=[cfg.room_m[0] * 0.8, cfg.room_m[1] * 0.5])
    hamper = np.asarray(runner.tc.hamper_room_m, float)
    real = T.plan_line

    def plan(model, a, b, lim, **kw):
        if kw["label"].startswith("raise"):
            raise PlanError("tension infeasible at [1.9 1.0 1.36] (max 12.1 N > 12.0 N incl. dynamics)")
        return real(model, a, b, lim, **kw)
    monkeypatch.setattr(T, "plan_line", plan)
    moved, gripped = [], []
    runner._move = lambda *a, **k: moved.append(k.get("label"))
    r.ctx.claw = SimpleNamespace(grip=lambda close: gripped.append(close))
    ok, why = runner._handle(_item(r, -0.3, 0.0), hamper, lambda *a, **k: None)
    assert ok is False and why.startswith("unreachable: raise sock: tension infeasible at") and "12.1 N" in why
    assert moved == [] and gripped == []                                              # nothing moved, nothing gripped
    assert runner.log and "carry not plannable" in runner.log[0]


def test_a_carry_leg_outside_the_trusted_volume_or_above_the_task_height_fails_the_item_too():
    r, cfg = _armed_model_robot()
    runner = _verified_runner(r)
    W, D, _H = cfg.room_m
    above = np.array([W / 2, D / 2, 0.7])
    grip = np.array([W / 2, D / 2, 0.42])
    # the hamper beyond the room: the transport leg's target is outside the workspace
    why = runner._dry_run_carry("sock", above, grip, np.array([W + 2.0, D / 2]))
    assert why.startswith("verify shift sock: target") and "outside the trusted volume" in why or why.startswith(("raise", "transport"))
    # a carry height above motion.task_max_height_m
    runner.tc = __import__("dataclasses").replace(cfg.tasks, hamper_height_m=cfg.motion.task_max_height_m + 0.1)
    why = runner._dry_run_carry("sock", above, grip, np.array([W / 2 + 0.3, D / 2]))
    assert "above motion.task_max_height_m" in why


def test_the_dry_run_planning_is_pumped_while_it_takes_seconds(monkeypatch):
    """Four legs of 0.8 s each (a slow host planning a long carry): the stations stay alive, the coordinator is never touched."""
    r, cfg = _armed_model_robot()
    runner = _verified_runner(r)
    runner.tc = __import__("dataclasses").replace(cfg.tasks, hamper_room_m=[cfg.room_m[0] * 0.8, cfg.room_m[1] * 0.5])
    hamper = np.asarray(runner.tc.hamper_room_m, float)
    monkeypatch.setattr(T, "plan_line", lambda *a, **k: time.sleep(0.8))
    item = _item(r, -0.3, 0.0)
    above = np.array([item.xy[0], item.xy[1], 0.7])
    grip = np.array([item.xy[0], item.xy[1], 0.42])
    why, m = _run_metered(r, lambda: runner._dry_run_carry("sock", above, grip, hamper))
    assert why is None
    assert all(f != Fault.LEASE for _st, f in _stations(r.co)) and _alive(r.co), _stations(r.co)
    assert m.max_stall_s < cfg.faults.lease_s / 3, m.worst_text()
    assert m.violations == [] and _pump_threads() == []
