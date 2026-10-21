"""Station keep-alive during the long computations of the startup (review H1, verification/board_followups_review.md section 3;
results in verification/keepalive_fix_results.md).

While a command owns the robot the idle host loop does not pump (Service.idle_tick), so a computation of seconds on the command
thread -- a board-survey flush (0.8-2.5 s) or a Calibrator.fit (0.6-7.9 s) -- outlasts faults.lease_s (0.3 s in robot.sim.json) and
latches Fault.LEASE on all four armed stations. StartupSequencer._pumped runs such a call on a one-worker thread while the command
thread keeps pumping with ctx.wait on the 20 ms grid.

The simulated clock only moves while somebody waits (SimRuntime.wait), so a stall is modelled in two ways here: as host time the
worker waits out (the clock must be taken that far by the command thread's pump), and as a real wall-clock sleep of the worker (the
command thread then takes the clock on, 20 ms per step, for as long as it lasts). Everything is simulation: the real host CPU and the real lease are
unmeasured.

Repair round 2 (verification/keepalive_fix_review.md N1-N3): the other multi-hundred-ms computations of the armed startup (candidate filter,
D-optimal design, every planned move, the acceptance report and work volume, the margin scan) go through ``_pumped`` too, ``_pumped`` lowers
the GIL switch interval while its worker runs (N2), and (section f) a test-only ``PumpGapMeter`` records the largest wall-clock gap between
two ``Coordinator.pump`` calls after arm(): one full simulated startup with the clock coupled to wall time must stay below a third of the
lease and must not latch Fault.LEASE, whichever call is slow.
"""
import collections
import inspect
import json
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr.attitude import image_motion_rad_s
from roomcleaner.cdpr.config import (ATTITUDE_BOUNDS, STILL_RATE_NOISE_K, ConfigError, load_config,
                                     still_rate_noise_floor_rad_s)
from roomcleaner.cdpr import startup as ST
from roomcleaner.cdpr.protocol import Fault, State
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.startup import StartupAbort, StartupSequencer
from roomcleaner.cdpr.supervisor import Supervisor

from .simkit import SIM, assert_no_eq_failures, fast_cfg
from .test_board_attitude import CAM, cam_pose
from .test_board_followups import _StillCamera, _errors, _survey_robot, _truth

EXAMPLE = "config/robot.example.json"


def _armed_robot(tmp_path):
    """A simulated robot with a floor-board survey whose four stations are configured, synchronised and armed (state IDLE, no fault)."""
    r, truth, _path = _survey_robot(tmp_path=tmp_path)
    co = r.co
    co.wait(300000)
    co.configure()
    co.wait_synced(3.0)
    co.arm()
    co.wait(100000)
    assert all(co.links[s].tel["st"] == 1 and co.links[s].tel["flt"] == 0 for s in "ABCD")
    assert r.cfg.faults.lease_s == 0.3 and co.lease_us == pytest.approx(0.3e6)
    return r, co, truth


def _clock_stall(r, seconds):
    """A computation that costs ``seconds`` of host time: it returns once the simulated clock has been taken that far, which only
    the command thread's pump can do while this runs on the worker. If nothing pumps (the call was made on the command thread) it
    fails after 20 s of wall time instead of hanging."""
    t0 = r.rt.now_us()

    def stall():
        deadline = time.monotonic() + 20.0
        while r.rt.now_us() < t0 + seconds * 1e6:
            assert time.monotonic() < deadline, "nothing pumps the stations while this computation runs"
            time.sleep(0.001)
    return stall


def _pump_threads():
    return [t for t in threading.enumerate() if t.name.startswith("startup-pumped")]


def _all_stations_ok(co):
    co.pump()
    return all(co.links[s].tel["st"] == 1 and co.links[s].tel["flt"] == 0 for s in "ABCD")


# ===================================================================== (a) the survey top-up through _survey_topup
def test_a_top_up_whose_flush_stalls_0_9_s_leaves_every_armed_station_fault_free(tmp_path):
    """The reviewer's test_a_top_up_that_blocks_longer_than_the_lease...: a flush of 0.9 s of host time against a 0.3 s lease, through the
    real _survey_topup. Unpumped (the code before the fix) it latched Fault.LEASE (4) on all four stations; now the command thread
    keeps the 20 ms ping going while the flush computes."""
    r, co, _ = _armed_robot(tmp_path)
    S = StartupSequencer(r.ctx)
    t0 = r.rt.now_us()
    pumps = []
    orig = co.pump
    co.pump = lambda: (pumps.append(r.rt.now_us()), orig())[1]
    r.ctx.board_survey.flush = _clock_stall(r, 0.9)
    S._survey_topup("CALIBRATION")
    assert r.rt.now_us() >= t0 + 0.9e6                                      # the clock was taken on by the command thread's pump
    assert max(np.diff(pumps)) <= 0.02e6 + 1e-6                             # never more than one ping period between two pumps (sim time)
    co.pump = orig
    assert _all_stations_ok(co)
    assert _pump_threads() == []                                            # the worker is gone


def test_the_same_stall_as_a_wall_clock_sleep_of_the_worker_also_leaves_the_stations_fault_free(tmp_path):
    r, co, _ = _armed_robot(tmp_path)
    S = StartupSequencer(r.ctx)
    t0 = r.rt.now_us()
    r.ctx.board_survey.flush = lambda: time.sleep(0.9)
    S._survey_topup("CALIBRATION")
    assert r.rt.now_us() >= t0 + 0.5e6                                      # the clock was taken on while the flush slept (20 ms per
    assert _all_stations_ok(co)                                             # step, a step costs ~27 ms of wall time in the simulator)
    assert _pump_threads() == []


# ===================================================================== (b) one cal.fit site (visual_init) and all of them
def test_a_calibration_fit_that_stalls_0_9_s_leaves_every_armed_station_fault_free(tmp_path):
    """The same through a ``ctx.cal.fit`` site (visual_init): ``fit`` is replaced by a call that sleeps 0.9 s (wall) and then returns the
    result; the sequencer gets it unchanged, the call ran off the command thread, the clock was pumped throughout."""
    r, co, _ = _armed_robot(tmp_path)
    ctx = r.ctx
    S = StartupSequencer(ctx)
    sample = SimpleNamespace(kind="fit")
    S._sample_probed = lambda kind, state: sample                           # (no probe, no moves: only the fit is under test)
    ctx.result = SimpleNamespace(L0=np.zeros(4), psi=np.array([0.1, 0.2, 0.3]))
    ctx.onsets = []
    result = SimpleNamespace(L0=np.array([1.0, 2.0, 3.0, 4.0]))
    applied, seen = [], {}

    def slow_fit(samples, onsets, **kw):
        seen["thread"] = threading.current_thread()
        seen["args"] = (list(samples), list(onsets), kw)
        time.sleep(0.9)
        return result
    ctx.cal = SimpleNamespace(fit=slow_fit)
    ctx.apply_result = lambda res, tag: applied.append((res, tag))
    t0 = r.rt.now_us()
    S.visual_init()
    assert r.rt.now_us() >= t0 + 0.5e6                                      # pumped throughout (a pump step is 20 ms of the clock)
    assert seen["thread"] is not threading.main_thread() and seen["thread"].name.startswith("startup-pumped")
    assert seen["args"][0] == [sample] and seen["args"][1] == [] and seen["args"][2]["L0_init"] is ctx.result.L0
    assert applied == [(result, "visual")] and S.rep.measurements["L0_visual"] == [1.0, 2.0, 3.0, 4.0]
    assert _all_stations_ok(co)
    assert _pump_threads() == []


def test_every_fit_and_the_survey_flush_of_the_sequencer_go_through_the_pumped_helper():
    """Static guard: the six ``Calibrator.fit`` sites and the survey flush of startup.py are the arguments of ``_pumped``, none is called
    directly on the command thread."""
    import inspect
    src = inspect.getsource(StartupSequencer)
    assert src.count("ctx.cal.fit") == 6 and src.count("self._pumped(ctx.cal.fit,") == 6
    assert "sv.flush()" not in src.replace("``sv.flush()``", "") and src.count("self._pumped(sv.flush)") == 1


# ===================================================================== (c) exceptions
class _Boom(RuntimeError):
    pass


def test_an_exception_raised_inside_the_worker_propagates_with_its_original_type_and_instance(tmp_path):
    r, co, _ = _armed_robot(tmp_path)
    S = StartupSequencer(r.ctx)
    err = _Boom("calibration failed from every initialisation")

    def fn():
        time.sleep(0.05)
        raise err
    with pytest.raises(_Boom) as e:
        S._pumped(fn)
    assert e.value is err and _pump_threads() == []
    # through a real site: a ValueError of Calibrator.fit ("no observation of cable A") reaches the caller of visual_init unchanged
    ctx = r.ctx
    S._sample_probed = lambda kind, state: SimpleNamespace(kind="fit")
    ctx.result = SimpleNamespace(L0=np.zeros(4), psi=np.zeros(3))
    ctx.onsets = []
    ctx.cal = SimpleNamespace(fit=lambda *a, **k: (_ for _ in ()).throw(ValueError("no observation of cable A: its L0 is undetermined")))
    with pytest.raises(ValueError, match="no observation of cable A"):
        S.visual_init()
    assert _pump_threads() == [] and _all_stations_ok(co)
    # the worker's return value and arguments pass through
    assert S._pumped(lambda a, b=0: a + b, 1, b=2) == 3


def test_an_abort_while_waiting_propagates_at_once_and_the_worker_does_not_leak():
    """ctx.wait raises (abort / e-stop): the exception comes out of _pumped immediately, without waiting for a computation that
    cannot be interrupted; the worker thread ends when the computation does."""
    release = threading.Event()
    calls = []

    def wait(s):
        calls.append(s)
        if len(calls) == 3:
            raise StartupAbort("CALIBRATION", "operator abort")
        time.sleep(0.001)
    S = StartupSequencer(SimpleNamespace(cfg=None, wait=wait))
    t0 = time.monotonic()
    with pytest.raises(StartupAbort, match="operator abort"):
        S._pumped(release.wait, 30.0)
    assert time.monotonic() - t0 < 2.0 and calls == [StartupSequencer.PUMP_STEP_S] * 3
    release.set()
    deadline = time.monotonic() + 5.0
    while _pump_threads() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert _pump_threads() == []


# ===================================================================== (d) the noise-floor cross-check and the tightened bounds
def _raw(**changes):
    raw = json.load(open(SIM))
    for path, v in changes.items():
        sec, key = path.split(".")
        raw[sec][key] = v
    return raw


def test_the_noise_floor_formula_is_the_image_rate_of_a_still_claw_for_1_to_4_tags():
    """still_rate_noise_floor_rad_s = sqrt(pi) x sigma / (520 px x 0.1 s) is the mean of attitude.image_motion_rad_s over frame pairs of a
    claw that does not move (1.0e-2 rad/s at 0.3 px), whatever the number of corners."""
    rng = np.random.default_rng(5)
    for sigma in (0.3, 0.8):
        for n_tags in (1, 2, 4):
            base = np.vstack([np.array([[100, 100], [150, 100], [150, 150], [100, 150]], float) + 60 * k for k in range(n_tags)])
            r = [image_motion_rad_s(SimpleNamespace(corners=base + rng.normal(0, sigma, base.shape), t_us=0.0),
                                    SimpleNamespace(corners=base + rng.normal(0, sigma, base.shape), t_us=1e5), CAM.fx)
                 for _ in range(2500)]
            assert np.mean(r) == pytest.approx(still_rate_noise_floor_rad_s(sigma), rel=0.03), (sigma, n_tags)
    assert still_rate_noise_floor_rad_s(0.3) == pytest.approx(1.0e-2, rel=0.03)
    assert CAM.fx == 520.0


def test_one_pixel_of_corner_noise_with_the_shipped_still_rate_is_refused_and_the_message_says_why():
    with pytest.raises(ConfigError) as e:
        load_config(_raw(**{"camera.corner_sigma_px": 1.0}))
    msg = str(e.value)
    assert "tasks.grip_still_rate_rad_s = 0.02" in msg and "camera.corner_sigma_px = 1 px" in msg
    assert "do not average to zero" in msg and "could not approve a grip or release" in msg and "at least 0.048" in msg
    # the remedy named in the message works, and so does the other way round
    assert load_config(_raw(**{"camera.corner_sigma_px": 1.0, "tasks.grip_still_rate_rad_s": 0.048})).camera.corner_sigma_px == 1.0
    with pytest.raises(ConfigError, match="camera.corner_sigma_px = 1 px"):
        load_config(_raw(**{"camera.corner_sigma_px": 1.0, "tasks.grip_still_rate_rad_s": 0.047}))


def test_both_shipped_profiles_pass_the_cross_check_with_margin_and_the_widest_corner_noise_has_a_feasible_limit():
    for prof in (SIM, EXAMPLE):
        cfg = load_config(prof)
        floor = still_rate_noise_floor_rad_s(cfg.camera.corner_sigma_px)
        assert (cfg.camera.corner_sigma_px, cfg.tasks.grip_still_rate_rad_s) == (0.3, 0.02)
        assert cfg.tasks.grip_still_rate_rad_s >= 1.9 * floor                       # 0.02 against a floor of 0.0102
    lo_rate, hi_rate = ATTITUDE_BOUNDS["tasks.grip_still_rate_rad_s"][:2]
    lo_sig, hi_sig = ATTITUDE_BOUNDS["camera.corner_sigma_px"][:2]
    assert lo_rate >= STILL_RATE_NOISE_K * still_rate_noise_floor_rad_s(0.3)        # the range's lower bound clears the default noise
    assert load_config(_raw(**{"camera.corner_sigma_px": hi_sig, "tasks.grip_still_rate_rad_s": hi_rate}))
    assert load_config(_raw(**{"camera.corner_sigma_px": lo_sig, "tasks.grip_still_rate_rad_s": lo_rate}))


def test_the_other_tightened_bounds_and_the_removed_dwell_check():
    assert ATTITUDE_BOUNDS["startup.rocking_tilt_k"][0] == 4.0 and ATTITUDE_BOUNDS["camera.corner_sigma_px"][0] == 0.15
    for key, bad, good in (("startup.rocking_tilt_k", 3.9, 4.0), ("camera.corner_sigma_px", 0.14, 0.15)):
        with pytest.raises(ConfigError, match="physically sensible range"):
            load_config(_raw(**{key: bad}))
        assert load_config(_raw(**{key: good}))
    assert "98 %" in ATTITUDE_BOUNDS["startup.rocking_tilt_k"][3] and "12.7 %" in ATTITUDE_BOUNDS["startup.rocking_tilt_k"][3]
    assert "0.15 px" in ATTITUDE_BOUNDS["camera.corner_sigma_px"][3]
    # L2: no dwell-against-timeout check any more (periods x margin x 1.5 s = 22.5 s > 15 s loads, and the gate runs it)
    assert load_config(_raw(**{"tasks.grip_period_margin": 3.0})).tasks.grip_period_margin == 3.0


# ===================================================================== (e) a real 60-frame flush through _survey_topup
def test_a_real_60_frame_flush_runs_pumped_and_gives_the_sheets_the_direct_call_gives(tmp_path):
    """The review's worst case (60 offered frames, 9 sheets, 2.3-2.5 s of compute on this machine) through the real _survey_topup on
    an armed robot: no fault, the keep-alive pumped throughout (largest wall-clock gap between two pump calls well inside the 0.3 s
    lease; it is printed), the survey, layout file and report updated as before."""
    r, co, truth = _armed_robot(tmp_path)
    ctx, sv = r.ctx, r.ctx.board_survey
    edge = r.cfg.marker.edge_m
    sv.run(_StillCamera(truth, cam_pose((0.03, -0.02, 0.52)), seed=1), lambda s: None, n_frames=30, interval_s=0.1, edge_m=edge)
    rr = np.random.default_rng(1)
    for k in range(24):
        cam = _StillCamera(truth, cam_pose((rr.uniform(-0.15, 0.15), rr.uniform(-0.15, 0.15), rr.uniform(0.6, 1.1))), seed=100 + k)
        cam.t = 100.0 * k
        sv.offer([cam.observe() for _ in range(10)])
    assert len(sv._pending) == 60
    S = StartupSequencer(ctx)
    S.rep.measurements["board_survey"] = sv.report()
    stamps, sim_stamps = [], []
    orig = co.pump
    co.pump = lambda: (stamps.append(time.perf_counter()), sim_stamps.append(r.rt.now_us()), orig())[2]
    t0, wall0 = r.rt.now_us(), time.perf_counter()
    S._survey_topup("CALIBRATION")
    wall = time.perf_counter() - wall0
    co.pump = orig
    gaps = np.diff(stamps)
    print(f"\n[keepalive] 60-frame flush: {wall:.2f} s wall, {len(stamps)} pumps, largest wall gap between pumps {gaps.max() * 1e3:.1f} ms, "
          f"median {np.median(gaps) * 1e3:.2f} ms, simulated clock advanced {(r.rt.now_us() - t0) / 1e6:.1f} s")
    assert len(stamps) > 20 and gaps.max() < 0.15                           # half the 0.3 s lease; 25-28 ms were measured for a pure sleep loop
    assert max(np.diff(sim_stamps)) <= 0.02e6 + 1e-6
    assert _all_stations_ok(co)
    rep = S.rep.measurements["board_survey"]
    assert len(sv._pending) == 0 and len(r.board_layout.surveyed_ids()) == 9 and rep["topups"] and len(rep["surveyed_ids"]) == 9
    assert len(ctx.floor_board.corners) == 9
    assert max(e[0] for e in _errors(r.board_layout, truth).values()) < 1.0e-3
    assert _pump_threads() == []


# ===================================================================== (d, round 2) N3: the cross-check uses startup.frame_interval_s
def test_the_noise_floor_cross_check_uses_the_configured_frame_interval_and_the_message_says_so():
    """The noise-only image rate is sqrt(pi) sigma / (fx dt) with the dt ``wait_until_still`` really uses (startup.frame_interval_s), not a
    hard-coded 0.1 s: halving the interval doubles the floor, so 0.5 px with a 0.025 limit (1.47x the floor at 0.1 s) is refused at 0.05 s."""
    assert still_rate_noise_floor_rad_s(0.3, 0.05) == pytest.approx(2 * still_rate_noise_floor_rad_s(0.3))
    assert still_rate_noise_floor_rad_s(0.3, 0.1) == still_rate_noise_floor_rad_s(0.3)
    base = {"camera.corner_sigma_px": 0.5, "tasks.grip_still_rate_rad_s": 0.025}
    assert load_config(_raw(**base)).startup.frame_interval_s == 0.1
    with pytest.raises(ConfigError) as e:
        load_config(_raw(**base, **{"startup.frame_interval_s": 0.05}))
    msg = str(e.value)
    assert "startup.frame_interval_s = 0.05 s" in msg and "0.73 x" in msg and "520 px x 0.05 s" in msg and "at least 0.048" in msg
    # the remedies named in the message work: the limit it asks for, or the interval of the check that passed
    assert load_config(_raw(**dict(base, **{"startup.frame_interval_s": 0.05, "tasks.grip_still_rate_rad_s": 0.048})))
    assert load_config(_raw(**{"camera.corner_sigma_px": 0.25, "tasks.grip_still_rate_rad_s": 0.025, "startup.frame_interval_s": 0.05}))
    # a longer interval LOWERS the noise rate: 0.5 px with the shipped 0.02 is refused at 0.1 s and accepted at 0.2 s
    with pytest.raises(ConfigError, match="camera.corner_sigma_px = 0.5 px"):
        load_config(_raw(**{"camera.corner_sigma_px": 0.5}))
    assert load_config(_raw(**{"camera.corner_sigma_px": 0.5, "startup.frame_interval_s": 0.2})).startup.frame_interval_s == 0.2
    # and an interval that cannot be divided by is a configuration error of its own, not a ZeroDivisionError
    for bad in (0.0, -0.1):
        with pytest.raises(ConfigError, match="startup.frame_interval_s must be > 0"):
            load_config(_raw(**{"startup.frame_interval_s": bad}))


def test_the_cross_check_message_is_true_for_the_ratio_it_reports():
    """Review N3 wording: 'rarely ... could not approve' is true below ~0.9x the noise rate (the real gate on a still claw: 0.9x opens in
    75 / 48 / 20 % of the runs with 1 / 2 / 4 tags, 0.6x never) and false for 0.9-1.4x, where the gate opens (slowly)."""
    floor = still_rate_noise_floor_rad_s(1.0)                                            # 0.0341 rad/s at 1 px
    texts = {}
    for ratio in (0.59, 0.85, 0.95, 1.2, 1.38):
        with pytest.raises(ConfigError) as e:
            load_config(_raw(**{"camera.corner_sigma_px": 1.0, "tasks.grip_still_rate_rad_s": round(ratio * floor, 5)}))
        texts[ratio] = str(e.value)
        assert f"is {ratio:.2f} x the image rate" in texts[ratio] and "requires at least 1.4 x" in texts[ratio]
    for ratio in (0.59, 0.85):
        assert "only rarely and could not approve a grip or release" in texts[ratio]
    for ratio in (0.95,):
        assert "only some of the time" in texts[ratio] and "could not approve" not in texts[ratio] and "rarely" not in texts[ratio]
    for ratio in (1.2, 1.38):
        assert "only after seconds of waiting" in texts[ratio] and "could not approve" not in texts[ratio] and "rarely" not in texts[ratio]
    assert load_config(_raw(**{"camera.corner_sigma_px": 1.0, "tasks.grip_still_rate_rad_s": round(1.4 * floor + 1e-4, 5)}))


# ===================================================================== (b, round 2) _pumped: the GIL switch interval (N2)
def test_pumped_lowers_the_gil_switch_interval_for_the_call_and_restores_it_whatever_happens():
    """N2: a worker whose numpy calls release and re-take the GIL starves the sleeping command thread for 0.10-0.30 s at the default
    5 ms switch interval; _pumped runs the call at PUMP_SWITCH_INTERVAL_S and puts the old value back (also on an exception of the
    worker, of ctx.wait, and when the caller had already chosen a shorter interval)."""
    seen = []
    S = StartupSequencer(SimpleNamespace(cfg=None, wait=lambda s: time.sleep(0.001)))
    old = sys.getswitchinterval()
    try:
        sys.setswitchinterval(0.005)
        assert S._pumped(lambda: (time.sleep(0.03), sys.getswitchinterval())[1]) == pytest.approx(StartupSequencer.PUMP_SWITCH_INTERVAL_S)
        assert sys.getswitchinterval() == pytest.approx(0.005)
        with pytest.raises(_Boom):
            S._pumped(lambda: (seen.append(sys.getswitchinterval()), (_ for _ in ()).throw(_Boom("x")))[1])
        assert seen == [pytest.approx(StartupSequencer.PUMP_SWITCH_INTERVAL_S)] and sys.getswitchinterval() == pytest.approx(0.005)
        # ctx.wait raising (abort): the interval is restored before the exception leaves, the worker is left to finish
        release = threading.Event()
        calls = []

        def wait(s):
            calls.append(s)
            if len(calls) == 2:
                raise StartupAbort("CALIBRATION", "operator abort")
        with pytest.raises(StartupAbort):
            StartupSequencer(SimpleNamespace(cfg=None, wait=wait))._pumped(release.wait, 30.0)
        assert sys.getswitchinterval() == pytest.approx(0.005)
        release.set()
        # a caller that already uses a shorter interval keeps it (the lowering never raises the interval)
        sys.setswitchinterval(1e-4)
        assert S._pumped(sys.getswitchinterval) == pytest.approx(1e-4, rel=0.05) and sys.getswitchinterval() == pytest.approx(1e-4, rel=0.05)
    finally:
        sys.setswitchinterval(old)
    deadline = time.monotonic() + 5.0
    while _pump_threads() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert _pump_threads() == []


# ===================================================================== (f) the systemic guard: the largest gap between pumps after arm()
class PumpGapMeter:
    """Test-only instrument (review N1: stop chasing slow call sites one by one): the largest wall-clock gap between two consecutive
    ``Coordinator.pump`` calls after ``arm()``, on the instance it is attached to (nothing in the product changes).

    * ``max_wall_s``: the wall time between two consecutive pump calls, whatever ran in between.
    * ``max_stall_s``: the same minus the CPU time the simulated plant used inside ``rt.wait`` in that interval. The plant is CPU work in
      the simulator (an equilibrium solve of up to 0.2 s) and a physical machine on hardware, so its CPU time is no host stall; time the
      command thread spends waiting for the GIL, sleeping or computing is. This is the number the lease has to be sized against.
    * ``couple=True`` couples the simulated clock to wall time: a host stall between two pumps advances the stations by the stall with no
      ping, as on a real runtime, so a stall over ``faults.lease_s`` latches Fault.LEASE for real.
    * ``close()`` makes the first pump after the command returns (``Service.idle_tick``) and so closes the TRAILING gap (the work after the
      last pump of a command, which no consecutive-pump measure sees otherwise: the margin scan after the last calibration fit was 2.6 s).
    * every public ``Coordinator`` method raises (and is recorded in ``violations``) when called from a ``startup-pumped`` worker: a
      pumped computation may touch only its own inputs.
    * a watchdog thread samples the command thread's stack during a gap above ``sample_above_s``; ``worst_text()`` names the call.
    """

    def __init__(self, co, *, couple=False, armed=False, worker_prefix="startup-pumped", sample_above_s=0.04, poll_s=0.01):
        self.co, self.rt, self.couple, self.armed = co, co.rt, couple, armed
        self.worker_prefix, self.sample_above_s, self.poll_s = worker_prefix, sample_above_s, poll_s
        self.n_pumps = 0
        self.max_wall_s = self.max_stall_s = 0.0
        self.long_stalls = []                       # stall_s of every gap above sample_above_s
        self.violations = []
        self._worst = None
        self._samples = {}
        self._last_end = time.perf_counter()        # the moment of attaching counts as the last pump (a command that never pumps is a gap)
        self._plant_cpu = 0.0
        self._coupling = False
        self._main_tid = threading.get_ident()
        names = [n for n, _fn in inspect.getmembers(type(co), inspect.isfunction) if not n.startswith("_") and n not in ("pump", "arm")]
        self._patched = [(co, n, n in vars(co), getattr(co, n)) for n in names + ["pump", "arm"]] + \
                        [(co.rt, "wait", "wait" in vars(co.rt), co.rt.wait)]
        self._orig = {"pump": co.pump, "arm": co.arm, "rt_wait": co.rt.wait}
        for n in names:
            setattr(co, n, self._guard(n, getattr(co, n)))
        co.pump, co.arm, co.rt.wait = self._pump, self._arm, self._rt_wait
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, name="pump-gap-watchdog", daemon=True)
        self._thread.start()

    # -- wrappers
    def _in_worker(self):
        return threading.current_thread().name.startswith(self.worker_prefix)

    def _guard(self, name, fn):
        def guarded(*a, **k):
            if self._in_worker():
                self.violations.append(name)
                raise AssertionError(f"Coordinator.{name} called from a pumped worker thread")
            return fn(*a, **k)
        return guarded

    def _rt_wait(self, dt_us):
        c0 = time.thread_time()
        try:
            return self._orig["rt_wait"](dt_us)
        finally:
            self._plant_cpu += time.thread_time() - c0

    def _arm(self, *a, **k):
        out = self._orig["arm"](*a, **k)
        self.armed = True                           # the stations are armed: from here a pump gap longer than the lease latches Fault.LEASE
        return out

    def _pump(self):
        if self._in_worker():
            self.violations.append("pump")
            raise AssertionError("Coordinator.pump called from a pumped worker thread")
        t = time.perf_counter()
        if self.armed and self._last_end is not None:
            wall = t - self._last_end
            stall = max(wall - self._plant_cpu, 0.0)
            self.n_pumps += 1
            self.max_wall_s = max(self.max_wall_s, wall)
            if stall > self.sample_above_s:
                self.long_stalls.append(stall)
            if stall > self.max_stall_s:
                self.max_stall_s = stall
                self._worst = (stall, wall, self._last_end)
            if self.couple and stall > 0.002:
                self._coupling = True               # (the watchdog does not sample the plant steps that stand for the stall)
                try:
                    self._orig["rt_wait"](stall * 1e6)      # the stations live on while the host computes: no ping goes out
                finally:
                    self._coupling = False
        self._plant_cpu = 0.0
        out = self._orig["pump"]()
        self._last_end = time.perf_counter()
        return out

    def _watch(self):
        while not self._stop.wait(self.poll_s):
            t0 = self._last_end
            if self.armed and t0 is not None and not self._coupling and time.perf_counter() - t0 > self.sample_above_s:
                fr = sys._current_frames().get(self._main_tid)
                if fr is not None:
                    import traceback
                    stack = tuple(f"{f.filename.rsplit('/', 1)[-1]}:{f.name}:{f.lineno}" for f in traceback.extract_stack(fr)
                                  if "roomcleaner" in f.filename or "test_" in f.filename)
                    self._samples.setdefault(t0, []).append(stack[-6:])

    # -- use
    def close(self):
        """The first pump after the command returns, then detach (restore the coordinator's own methods)."""
        self.co.pump()
        self._stop.set()
        self._thread.join(2.0)
        for obj, name, was_instance_attr, orig in self._patched:
            if was_instance_attr:
                setattr(obj, name, orig)
            else:
                delattr(obj, name)                  # back to the class's own method
        return self

    def worst_text(self):
        if self._worst is None:
            return "no gap recorded"
        stall, wall, t0 = self._worst
        common = collections.Counter(self._samples.get(t0, [])).most_common(1)
        where = " > ".join(common[0][0]) if common else "(no stack sample: shorter than the polling interval)"
        return f"worst gap {stall * 1e3:.0f} ms of host stall ({wall * 1e3:.0f} ms wall) in: {where}"


def _armed_model_robot():
    """A simulated robot whose four stations are armed and that has a nominal cable model (anchors = priors), seed 3."""
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


def test_the_gap_meter_measures_a_host_stall_excludes_the_plant_and_a_stall_over_the_lease_latches_the_fault(tmp_path):
    r, co, _ = _armed_robot(tmp_path)
    m = PumpGapMeter(co, couple=True, armed=True)
    try:
        co.wait(300000)                                             # 0.3 s of simulated plant time: no host stall
        assert m.n_pumps > 100 and m.max_stall_s < 0.05, m.worst_text()
        assert m.max_wall_s >= m.max_stall_s                       # the plant's CPU time is in the wall gap, not in the stall
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 0.15:                      # 0.15 s of host compute between two pumps (half the lease)
            pass
        co.pump()
        assert 0.14 < m.max_stall_s < 0.25 and "worst gap" in m.worst_text()
        assert all(co.links[s].tel["flt"] == 0 for s in "ABCD")     # under the lease: the clock-coupled stations are still fine
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 0.45:                      # 0.45 s: longer than the 0.3 s lease, no ping went out
            pass
        co.pump()
        co.wait(100000)
        assert m.max_stall_s > 0.4
        assert [co.links[s].tel["flt"] for s in "ABCD"] == [Fault.LEASE] * 4 and [co.links[s].tel["st"] for s in "ABCD"] == [State.FAULT] * 4
    finally:
        m.close()
    assert not {"pump", "arm", "wait", "positions"} & set(vars(co)) and "wait" not in vars(co.rt)     # detached: the class's methods again
    assert m.violations == []


def test_the_gap_meter_closes_the_trailing_gap_and_flags_a_coordinator_call_from_the_worker(tmp_path):
    r, co, _ = _armed_robot(tmp_path)
    m = PumpGapMeter(co, armed=True)
    S = StartupSequencer(r.ctx)
    co.wait(100000)
    time.sleep(0.12)                                                # work after the last pump of a "command": nothing pumps it
    m.close()                                                       # the first pump after the command returns
    assert m.max_stall_s >= 0.12
    m2 = PumpGapMeter(co, armed=True)
    try:
        with pytest.raises(AssertionError, match="Coordinator.positions called from a pumped worker"):
            S._pumped(co.positions)
        with pytest.raises(AssertionError, match="Coordinator.pump called from a pumped worker"):
            S._pumped(co.pump)
    finally:
        m2.close()
    assert m2.violations == ["positions", "pump"] and _pump_threads() == []


# ---------------------------------------------------------------- the calibration stage through the guard (before / after)
def _stage_gap(unpumped, monkeypatch):
    r, cfg = _armed_model_robot()
    co, ctx = r.co, r.ctx
    S = StartupSequencer(ctx)
    if unpumped:                                                    # the code before round 2: the filter runs on the command thread
        monkeypatch.setattr(S, "_pumped", lambda fn, *a, **k: fn(*a, **k))
    zf = -float(cfg.claw.lowest_point_body_m[2])
    min_z = zf + cfg.startup.target_clearance_m
    lb = np.asarray(cfg.calibration.local_box_m)
    W, D, _H = cfg.room_m
    centre = np.array([W / 2, D / 2, max(1.2, min_z + lb[2] + 0.01)])
    m = PumpGapMeter(co, armed=True)
    try:
        with pytest.raises(StartupAbort, match="feasible visible poses"):
            S._stage("local", centre, lb, 10 ** 6, 0, np.eye(3), min_z, (5, 5, 3))
    finally:
        m.close()
    return m, r


def test_the_calibration_stage_filter_is_a_stall_unpumped_and_stays_under_a_third_of_the_lease_pumped(monkeypatch):
    """The stage's candidate filter (75 poses here, 0.3 s; 0.7-2.3 s with the feasible poses of a full startup) on the command thread
    is a stall of 3x the allowed third of the 0.3 s lease; through ``_pumped`` the same stage leaves the gap at the keep-alive step."""
    bad, _ = _stage_gap(True, monkeypatch)
    good, r = _stage_gap(False, monkeypatch)
    print(f"\n[meter] _stage candidate filter, 75 poses: unpumped {bad.max_stall_s * 1e3:.0f} ms, pumped {good.max_stall_s * 1e3:.0f} ms "
          f"({good.n_pumps} pumps); lease 300 ms")
    assert bad.max_stall_s > 0.1                                    # the guard fails on the old behaviour
    assert good.max_stall_s < 0.1 and good.n_pumps > 5, good.worst_text()
    assert good.violations == []


def test_a_planned_move_of_a_calibration_stage_is_planned_on_the_pumped_worker_and_a_plan_error_still_aborts(monkeypatch):
    """_stage: plan_line_from (a tension LP at each of ~90 path points, both ways, 0.2-1.2 s per move in a full startup) runs on the pumped
    worker with the stations' positions read on the command thread and passed in; the keep-alive runs meanwhile; a PlanError of the worker
    reaches ``except PlanError`` unchanged (the stage aborts with its text). A stub with a 0.1 s sleep stands for the LPs here."""
    r, cfg = _armed_model_robot()
    ctx, co = r.ctx, r.co
    S = StartupSequencer(ctx)
    seen = {"raise": False}

    def plan(model, P_actual, p_to, lim, **kw):
        seen.update(thread=threading.current_thread().name, P_is_array=isinstance(P_actual, np.ndarray) and P_actual.shape == (4,),
                    model_is_ctx_model=model is ctx.model, ws_is_ctx_ws=kw.get("ws") is ctx.ws, label=kw.get("label"))
        time.sleep(0.1)
        if seen["raise"]:
            raise ST.PlanError("workspace: test refusal")
        return SimpleNamespace()
    monkeypatch.setattr(ST, "plan_line_from", plan)
    m = PumpGapMeter(co, armed=True)
    far = np.array([1.2, 1.0, 1.0])
    monkeypatch.setattr(S, "_candidates", lambda *a: [far, far + 0.1, far + 0.2, far + 0.3])
    monkeypatch.setattr(ST, "design_excitation", lambda *a, **k: ([np.array([2.2, 1.7, 1.5])], []))
    monkeypatch.setattr(S, "_execute", lambda plan, state, **kw: SimpleNamespace(ok=False, reason="stop here"))
    ctx.samples = []
    try:
        n0 = m.n_pumps
        with pytest.raises(StartupAbort, match="motion stop here"):
            S._stage("local", far, np.array([0.1, 0.1, 0.1]), 1, 0, np.eye(3), 0.0, (2, 2, 2))
        assert seen["thread"].startswith("startup-pumped") and seen["P_is_array"] and seen["model_is_ctx_model"] and seen["ws_is_ctx_ws"]
        assert seen["label"] == "local fit" and m.n_pumps - n0 >= 3
        seen["raise"] = True
        with pytest.raises(StartupAbort, match="workspace: test refusal") as e:
            S._stage("local", far, np.array([0.1, 0.1, 0.1]), 1, 0, np.eye(3), 0.0, (2, 2, 2))
        assert e.value.suspended and e.value.state == "CALIBRATION"
    finally:
        m.close()
    assert m.violations == [] and m.max_stall_s < 0.1, m.worst_text()
    assert _pump_threads() == []


def test_the_slow_calls_of_the_armed_startup_are_the_arguments_of_the_pumped_helper():
    """Static guard (the dynamic one is the full-startup test below): every call of calibrate / _stage / verify_references /
    assess_margin_trust that costs more than a few tens of ms is the ARGUMENT of ``_pumped`` (an attribute or name passed on, not a call
    on the command thread); the calls that remain are inside the pure helpers that run on the worker."""
    import ast
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(StartupSequencer)))
    direct = collections.defaultdict(set)                    # called name -> methods that call it
    pumped_args = collections.Counter()                      # first argument of _pumped(...) -> count
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if name == "_pumped" and node.args:
                a = node.args[0]
                pumped_args[ast.unparse(a)] += 1
            elif name:
                direct[name].add(fn.name)
    allowed = {"plan_line_from": set(), "design_excitation": set(), "fit": set(), "flush": set(), "pose_from_positions": set(),
               "_feasible": {"_candidates"}, "_work_volume": {"_accept"}, "_margin_volume": {"_margin_scan"}, "validate": {"_accept"},
               "length_sigma": {"_validated_points"}, "boundary_sigma": {"_margin_scan"}}
    for name, methods in allowed.items():
        assert direct.get(name, set()) <= methods, (name, sorted(direct[name]), "called on the command thread")
    assert pumped_args["plan_line_from"] == 1 and pumped_args["design_excitation"] == 1 and pumped_args["ctx.cal.fit"] == 6
    assert pumped_args["self._candidates"] == 1 and pumped_args["self._accept"] == 1 and pumped_args["self._validated_points"] == 1
    assert pumped_args["self._margin_scan"] == 1 and pumped_args["sv.flush"] == 1
    assert pumped_args["ctx.model.pose_from_positions"] == 3 and pumped_args["ctx.cal.validate"] >= 2


# ---------------------------------------------------------------- the full startup (survey mode, probe off, seed 0)
def test_a_full_simulated_startup_never_leaves_the_armed_stations_unpumped_for_a_third_of_the_lease(tmp_path):
    """The review's wall-coupled full startup (section 8 of verification/keepalive_fix_review.md: ``COUPLE=1 gap_run2.py 0 noprobe``): the
    simulated clock follows wall time, so a host stall between two pumps goes into the stations with no ping. Before round 2 this ended
    FAULT / Fault.LEASE on all four stations at the first calibration stage (a 0.9-2.3 s stall in the candidate filter, then 0.2-1.2 s
    in every planned move, and a 2.6 s tail after the last fit: work volume, acceptance report, 405-pose margin scan).

    Whatever call is slow, the largest gap between two consecutive Coordinator.pump calls after arm() (the first pump after the command
    returns included) has to stay below a third of faults.lease_s (0.1 s with the sim lease), and the startup must be READY with no station
    in State.FAULT / Fault.LEASE. The simulated plant's own CPU time inside rt.wait is not counted as a stall (see PumpGapMeter)."""
    cfg = fast_cfg(**{"startup.slack_probe": False, "marker.edge_m": 0.150})
    seed = 0
    r = SimRobot(cfg, seed=seed, data_dir=tmp_path, board_truth=_truth(0.150, seed), board_path=tmp_path / "layout.json")
    lease = cfg.faults.lease_s
    assert lease == 0.3
    switch0 = sys.getswitchinterval()
    sup = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    m = PumpGapMeter(r.co, couple=True)
    wall0 = time.perf_counter()
    try:
        rep = sup.start()
    finally:
        m.close()
    wall = time.perf_counter() - wall0
    stations = {s: (r.co.links[s].tel.get("st"), r.co.links[s].tel.get("flt")) for s in "ABCD"}
    stalls = np.array(m.long_stalls) if m.long_stalls else np.zeros(1)
    print(f"\n[meter] full startup (survey, probe off, seed {seed}, coupled clock): {rep.outcome}, {wall:.0f} s wall, {m.n_pumps} pumps after arm; "
          f"largest gap between pumps {m.max_stall_s * 1e3:.0f} ms host stall / {m.max_wall_s * 1e3:.0f} ms wall (plant CPU included); "
          f"{len(m.long_stalls)} gaps above 40 ms (largest 3: {np.round(np.sort(stalls)[-3:] * 1e3).tolist()} ms); lease {lease * 1e3:.0f} ms; "
          f"{m.worst_text()}; stations {stations}")
    assert m.armed and m.n_pumps > 1000                              # the measure ran over the armed part of the startup
    assert all(flt != Fault.LEASE and st != State.FAULT for st, flt in stations.values()), stations
    assert rep.outcome == "READY", (rep.outcome, rep.reasons[:3], m.worst_text())
    assert m.max_stall_s < lease / 3, m.worst_text()
    assert m.violations == []                                        # no pumped computation touched the coordinator
    assert _pump_threads() == [] and sys.getswitchinterval() == switch0
    assert_no_eq_failures(r, "full startup under the gap meter")
