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
"""
import json
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr.attitude import image_motion_rad_s
from roomcleaner.cdpr.config import (ATTITUDE_BOUNDS, STILL_RATE_NOISE_K, ConfigError, load_config,
                                     still_rate_noise_floor_rad_s)
from roomcleaner.cdpr.startup import StartupAbort, StartupSequencer

from .simkit import SIM, fast_cfg
from .test_board_attitude import CAM, cam_pose
from .test_board_followups import _StillCamera, _errors, _survey_robot

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
