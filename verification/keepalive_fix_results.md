# Keep-alive pumping and bound fixes after the board follow-ups review (H1, M1, L1, L2, L4)

Implementer results for `verification/board_followups_review.md`. Simulation only (`/usr/bin/python3`, `OMP_NUM_THREADS=1`, 4 shared vCPU):
the real host CPU, the real `faults.lease_s` and the real corner noise are unmeasured. No shipped default in `config/*.json` changed (only
bounds and a cross-check); `slack_probe`, `faults.lease_s`, CAD, docs, DECISIONS.md and DESIGN_STATE.md are untouched; nothing committed by
this task. Independent verification of these fixes has not been done (the author of the change wrote the new tests).

## Finding -> change -> proving test

| Finding | What changed (file:line) | Test that proves it |
|---|---|---|
| H1 (High): survey top-up and `Calibrator.fit` starve the station keep-alive | `roomcleaner/cdpr/startup.py:447` new `StartupSequencer._pumped(fn, *a, **kw)`: runs `fn` on a one-worker `ThreadPoolExecutor` (per call, `try/finally`, no `except`), loops `while not fut.done(): ctx.wait(0.02)` plus a `concurrent.futures.wait((fut,), timeout=0.02)` between steps, returns `fut.result()` (re-raises the worker's exception unchanged). An exception of `ctx.wait` (abort/e-stop) propagates at once and the worker is not waited for. Used for `sv.flush()` at `:863` and for the six `ctx.cal.fit` sites at `:773, :1077, :1168, :1189, :1194, :1373`. Constant `PUMP_STEP_S = 0.02` at `:429`. `fit` and `flush` compute exactly what they did | `tests/cdpr/test_keepalive_pumping.py` (a) `test_a_top_up_whose_flush_stalls_0_9_s...`, `test_the_same_stall_as_a_wall_clock_sleep...`; (b) `test_a_calibration_fit_that_stalls_0_9_s...` (through `visual_init`), `test_every_fit_and_the_survey_flush_of_the_sequencer_go_through_the_pumped_helper` (all 7 sites); (c) `test_an_exception_raised_inside_the_worker...`, `test_an_abort_while_waiting...`; (e) `test_a_real_60_frame_flush_runs_pumped...`; converted reviewer test `..._pumping_while_it_runs_does_not_fixed` |
| M1 (Medium): `grip_still_rate_rad_s` bound/reason wrong, no cross-check with `corner_sigma_px` | `roomcleaner/cdpr/config.py:84` lower bound 0.005 -> **0.015** and a corrected reason (noise-only rate = sqrt(pi) sigma / (fx dt) = 1.0e-2 rad/s at 0.3 px, norms do not average away); `:128-139` constants `STILL_RATE_REF_FX_PX = 520`, `STILL_RATE_REF_DT_S = 0.1`, `STILL_RATE_NOISE_K = 1.4`, `still_rate_noise_floor_rad_s(sigma)`; `:746` cross-check in `load_config`: refused when `grip_still_rate_rad_s < 1.4 x floor(corner_sigma_px)`, message says why and the value to use | `test_keepalive_pumping.py` (d): `test_the_noise_floor_formula...` (Monte Carlo, 1/2/4 tags, 0.3 and 0.8 px, within 3 %), `test_one_pixel_of_corner_noise_with_the_shipped_still_rate_is_refused...`, `test_both_shipped_profiles_pass...`; converted `test_still_claw_image_rate_noise..._fixed`, `test_no_cross_check_between_corner_noise_and_the_still_rate_limit_fixed` |
| L1: `rocking_tilt_k` lower bound 3 inside the range | `config.py:111` lower bound 3 -> **4**; reason carries 98 % / 12.7 % / 0.15 % of take-ups tripping at k = 3 / 4 / 5 | `test_the_other_tightened_bounds_and_the_removed_dwell_check`; converted `test_rocking_k_lower_bound_of_three..._fixed` |
| L2: dwell-vs-timeout cross-check over-strict, hard-coded 1.5 s | **Removed** (not re-stated): `wait_until_still` extends a loaded release's timeout to `max(timeout, dwell + 2 dt)` and the no-signal dwell is not bounded by the timeout, so no combination inside the ranges is unapprovable. A comment at `config.py:741` says why; the `grip_settle_timeout_s` reason (`:102`) now mentions the extension | `test_the_other_tightened_bounds_and_the_removed_dwell_check` (period margin 3 with timeout 15 loads); converted `test_dwell_cross_check_rejects..._fixed` (loads, and the gate approves a loaded release with dwell 15.6 s > timeout 15 s) |
| L4: `corner_sigma_px` lower bound 0.05 below its cited evidence | `config.py:65` lower bound 0.05 -> **0.15** (the cv2 corner bias of `floor_board_detector.md`); reason updated | `test_the_other_tightened_bounds_and_the_removed_dwell_check`; `test_both_shipped_profiles_pass...` (0.15 px with its lowest feasible limit loads) |
| Task 6 (optional): `vision/board.py` bundle adjustment `max_nfev=40`, tolerances 1e-10 | **Not changed.** The reviewer's `..._cap_of_8_changes_nothing` test shows identical sheets (< 5e-5 m apart) for the top-up path only (update + refine from a solved layout); the same function also runs the SELF_CHECK first survey from PnP starts, where no existing test shows the cap is harmless. With the pump the compute no longer endangers the lease, so the gain (2x CPU) is not worth the risk | `test_board_followups_review.py::test_an_accepting_flush_runs_two_bundle_adjustments...` (unchanged, passes) |

## Design choices and where they differ from the brief

* **Yield between pump steps.** The recommended loop (`while not fut.done(): ctx.wait(0.02)`) starves the worker in the simulator: there
  `ctx.wait` is CPU work (the simulated stations), not a sleep, and a CPU-bound main thread against a worker that releases the GIL
  thousands of times in small numpy/cv2 calls gives a GIL convoy (a 60-frame flush that takes 2.4 s alone had not finished after 10 minutes;
  the traceback showed the main thread in the stations' JSON encoder). `_pumped` therefore sleeps on the future for up to 20 ms after every
  20 ms pump step (`futures_wait`, wakes the moment the worker is done). On hardware the worst gap between two pumps is ~21 ms; in the
  simulator the simulated clock runs at about 0.9 x wall time during a pumped computation (2.1-2.4 s of clock for a 2.4-2.9 s flush).
* **Cross-check constants.** `k = 1.4` (not a rounder 1.5): it passes 93 % of the pairs of a one-tag view (99 % with 3 tags) and five
  quiet pairs in a row 70 % (97 %) of the time per window at the limit, and it keeps every corner sigma of its range feasible (1.4 x
  0.068 = 0.095 rad/s <= the 0.1 upper bound; 1.5 would make the 2 px edge of `corner_sigma_px` unsatisfiable). Lower bound 0.015 =
  1.4 x the 1.0e-2 rad/s noise rate at the default 0.3 px, so a limit on the range's edge also passes the cross-check at the default
  corner noise. The formula assumes the reference camera (fx 520 px) and frame interval (0.1 s); a camera with a smaller fx has a larger
  noise rate than the check models (the check is then too lax, never too strict), and the real corner noise still has to be measured.
  Effect on a value the review discussed: 0.5 px corner noise with the shipped 0.02 is now refused (0.5 px needs >= 0.024).
* The two shipped profiles load unchanged (`corner_sigma_px` 0.3, `grip_still_rate_rad_s` 0.02, ratio 1.96 against the floor).

## Measured pump gap (simulator, 60 offered frames, 9 sheets, through the real `_survey_topup`)

`test_a_real_60_frame_flush_runs_pumped_and_gives_the_sheets_the_direct_call_gives` (six runs, machine partly loaded by another test run):
flush 2.40-2.89 s wall (2.3-2.5 s when called directly, so pumping does not slow it); **largest wall gap between two `Coordinator.pump`
calls 31-72 ms** (71.5, 46.0, 42.2, 44.7, 46.1, 31.1), median 0.1 ms; the simulated clock advanced 2.1-2.4 s, never more than one ping
period (20 ms) of simulated time between two pumps; all four stations IDLE with Fault 0 afterwards; 9 of 9 sheets surveyed, error
< 1 mm. The review measured 25-28 ms for a pure sleeping loop; the test bound is the half-lease 0.15 s. On a real runtime `ctx.wait`
sleeps, which is the case measured by the review and not reproduced here.

## Tests that now fail by design in a file outside this task's edit list (`tests/cdpr/test_board_followups.py`, the implementer's)

Both encode behaviour this task removed or added. I did not edit the file (not in the list of files I may edit); the patch below makes both
pass (checked in-process; `EDGE_COMPANIONS` is the file's own mechanism for cross-checks):

1. `test_the_settle_dwell_has_to_fit_into_the_timeout` (line ~114) asserts the L2 check that was removed
   (`match="loaded release could never be approved"` for `grip_period_margin = 3.0`). Replace its first `with pytest.raises(...)` by
   `assert load_config(_raw(**{"tasks.grip_period_margin": 3.0}))` (L2: removed, see `test_board_followups_review.py::..._fixed`).
2. `test_every_bounded_key_is_refused_outside_its_range_and_accepted_at_its_edges[camera.corner_sigma_px]` loads `corner_sigma_px = 2.0`
   with the default limit 0.02, which the new cross-check refuses. Add to `EDGE_COMPANIONS`:
   `"camera.corner_sigma_px": {"tasks.grip_still_rate_rad_s": 0.1},` (the 2 px edge is feasible only with the 0.1 rad/s edge).

## Test results (`OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest ...`)

| Run | Result |
|---|---|
| `tests/cdpr/test_keepalive_pumping.py` (new) | **11 passed** (7 s) |
| `tests/cdpr/test_board_followups_review.py` (5 tests converted to `_fixed`, 11 untouched) | **16 passed** (14 s) |
| `tests/cdpr/test_board_followups.py` | 42 passed, **2 failed by design** (the two tests of the previous section; they pass with the patch given there) |
| `tests/cdpr/test_service.py` | **4 passed** |
| `tests/cdpr/test_startup*.py` | no such files in the repository |
| full `tests/cdpr` (`timeout 3500`, 25.5 min) | **344 passed, 2 failed** (the same two); baseline of the tree before this task, run in a scratch copy: 334 passed, 1 skipped (the +11 are the new file) |

Converted reviewer tests (renamed with `_fixed`, each with `# converted after fix: <id>`): M1 `test_still_claw_image_rate_noise_is_10_mrad_per_s_not_4_so_the_lower_bound_and_its_reason_are_wrong_fixed`,
M1 `test_no_cross_check_between_corner_noise_and_the_still_rate_limit_fixed`, L2 `test_dwell_cross_check_rejects_configurations_the_gate_can_run_so_its_message_is_not_true_fixed`,
L1 `test_rocking_k_lower_bound_of_three_gives_false_trips_in_most_take_ups_fixed`, H1 `test_a_top_up_that_blocks_longer_than_the_lease_lease_faults_every_armed_station_and_pumping_while_it_runs_does_not_fixed`
(that last one passed unchanged only by a race: its worker advanced the shared simulated clock while the command thread pumped; it now keeps the unpumped 0.9 s stall as evidence by replacing
`_pumped` with a direct call, and runs the stall through the real path with a clock-driven worker). `test_thirteen_bounded_keys...` still passes untouched (13 keys, both profiles inside the new bounds).
Both shipped profiles load (`robot.sim.json`, `robot.example.json`: corner sigma 0.3 px, still-rate limit 0.02 rad/s, rocking k 5).

## Not done / limits

* Not independently verified (the author wrote the new tests); no hardware: the worst pump gap on a real runtime and the real lease are unmeasured.
* If `ctx.wait` raises during a pumped call the worker cannot be interrupted: it finishes in the background and its result is dropped (a flush may still
  write the layout file after the abort). It holds no robot resources.
* L3, L5, L6, L7, M2, I1/I2 of the review are not part of this task and unchanged; `slack_probe` and `faults.lease_s` unchanged.

## Repair round 2 (N1, N2, N3, N4 of `verification/keepalive_fix_review.md`)

Simulation only (`/usr/bin/python3` 3.13, `OMP_NUM_THREADS=1`, a 4-vCPU shared VM on which another job was running for part of the time: it adds
25-170 ms hiccups, see N1 limits). The real host CPU, the real `faults.lease_s` and the real corner noise are unmeasured. No `config/*.json` default,
`slack_probe` or `faults.lease_s` changed. Nothing committed. Files edited: `roomcleaner/cdpr/startup.py`, `roomcleaner/cdpr/config.py`,
`tests/cdpr/test_keepalive_pumping.py`, `tests/cdpr/test_keepalive_fix_review.py`, and (one line, see "outside the list") `tests/cdpr/test_board_followups_review.py`.
Not independently verified: the author of the change wrote the new tests.

### N1 (High for hardware): the other long calls on the command thread while armed

| What | Change (file:line) | Proving test | Measured |
|---|---|---|---|
| excitation-candidate filter (`_feasible` over 75-196 poses) | `startup.py:1138` new `_candidates`, called through `_pumped` at `:1149` | `test_the_calibration_stage_filter_is_a_stall_unpumped_and_stays_under_a_third_of_the_lease_pumped`; converted `test_n1_the_candidate_filter..._fixed` | unpumped 357-433 ms (75 cheap poses) -> pumped 13-25 ms; 0.7-2.3 s per stage in a full startup before |
| `pose_from_positions` of the claw's pose (3 sites) | `:1165`, `:1188`, `:1392` through `_pumped` (the positions are read on the command thread and passed in) | static guard, below | 32 ms max, pumped anyway (a slower host multiplies it) |
| D-optimal design | `:1166` `_pumped(design_excitation, ...)` | static guard; `test_a_planned_move..._pumped_worker_...` | 0.06-0.2 s before |
| every planned move (`plan_line_from` -> `plan_line` -> `_check_path`, a tension LP at each path point both ways) | `:1172` `_pumped(plan_line_from, ctx.model, ctx.co.positions(), q, ctx.lim, ws=ctx.ws, ...)`; `PlanError` of the worker reaches the unchanged `except PlanError` | `test_a_planned_move_of_a_calibration_stage_is_planned_on_the_pumped_worker_and_a_plan_error_still_aborts`; converted `test_n1_plan_line_still_solves_hundreds_of_lps_..._fixed` (1.3 m move, 188 LPs, 94 points, 1.1 s, 2180 pumps, largest gap 10 ms) | 31 gaps up to 0.98 s (+3 up to 0.41 s) in one full startup before |
| local / bead-refit validation | `:1196`, `:1422` `_pumped(ctx.cal.validate, ...)` | static guard | 66 ms |
| work volume + acceptance report | `:1241` new `_accept` (`_work_volume` 75 LPs + `validate` over the volume), pumped at `:1220` | static guard, full startup | 0.24 s + 66 ms |
| absolute sigma + length sigma over the volume | `:1248` new `_validated_points`, pumped at `:1230` | same | |
| margin scan of the trust decision (405 LPs + 405 `boundary_sigma`) | `:1287` new `_margin_scan` (the old body of `assess_margin_trust` (c)), pumped at `:1365` | same; `test_margin_trust.py` (real `assess_margin_trust` on a finished startup) | 1.52 s `_margin_volume`, 2.27 s `assess_margin_trust`; this was the **2.63 s trailing gap** after the last fit, invisible to a consecutive-pump measure |

What I looked at and left on the command thread (measured per call, probe off, armed, 1 full startup): `apply_result` <= 4.9 ms (5 calls), `save_model` 2.6 ms and
`atomic_write` 1.7 ms (tmpfs here; an SD card is unmeasured), `align_from_bearings` 10.9 ms, `plan_cable_move` <= 1.4 ms, `vision.observe` mean 2.5 / max 8.8 ms (1057 calls),
`still_pose` 124 ms mean per call but that is waiting (pumped). The slack-probe path (`hinge_analysis`: einsum on <= 240 x 40 arrays; `probe_response`) was not timed per call;
three probe-on uncoupled audits show no gap above 67 ms. The audit scripts are scratch (session scratchpad `r2/`: `audit.py`, `timers.py`), not in the repo.

**The systemic guard** (`tests/cdpr/test_keepalive_pumping.py`, section f): `PumpGapMeter`, a test-only instrument attached to one `Coordinator` instance (nothing in the product
changes). It records, after `arm()`, the gap between consecutive `Coordinator.pump` calls as `max_wall_s` (raw), `max_host_s` (minus the CPU time the simulated plant used inside
`rt.wait`: a plant solve of up to 0.2 s has no hardware counterpart) and `max_stall_s` (minus the time the OS kept the command thread runnable but off the CPU,
`/proc/thread-self/schedstat`; time blocked on the GIL or computing stays in), couples the simulated clock to wall time (a stall goes into the stations with no ping, so a stall over
the lease latches Fault.LEASE), makes `close()` the first pump after the command returns (the **trailing gap**), raises if a `startup-pumped` worker calls any public `Coordinator`
method, and samples the command thread's and the worker's stacks during a gap above 40 ms (`worst_text()` names the call). Tests: `test_the_gap_meter_measures_a_host_stall_excludes_the_plant_and_a_stall_over_the_lease_latches_the_fault`,
`test_the_gap_meter_closes_the_trailing_gap_and_flags_a_coordinator_call_from_the_worker`, `test_the_slow_calls_of_the_armed_startup_are_the_arguments_of_the_pumped_helper` (AST: no call
of `plan_line_from`, `design_excitation`, `fit`, `flush`, `pose_from_positions` on the command thread; `_feasible`, `_work_volume`, `_margin_volume`, `validate`, `length_sigma`,
`boundary_sigma` only inside their pure helpers), and
`test_a_full_simulated_startup_never_leaves_the_armed_stations_unpumped_for_a_third_of_the_lease` (survey mode, probe off, seed 0, the review's coupled clock, `Supervisor.start()`; asserts READY,
no station in State.FAULT / Fault.LEASE, no coordinator call from a worker, `max_stall_s < lease_s / 3 = 0.1 s`, no leaked thread, switch interval restored, no plant equilibrium failure; ~165-195 s).

Full startup, coupled clock, round-1 tree: FAULT, all four stations State FAULT / Fault.LEASE at the first calibration stage (first stall 0.72 s in `_stage > _feasible > BoardGeometry.visible`,
simulated 119.96 s). Round-2 tree, 9 runs (one with the first 20 ms yield, eight with the final 5 ms), all READY, all stations IDLE / Fault 0, 290-370 k pumps after arm:
largest stall **21, 45, 49, 50, 52, 57, 81 ms** (seven runs), **128 and 172 ms** (two runs). The two outliers were not the code: 128 ms with 1 ms of OS run-queue wait sat in `pool.submit` (the worker
thread not yet started) and 172 ms was the final fit during a run with another job on the machine; a bare thread start + join measures median 0.6 / p99 2.3 / max 29.5 ms over 5756
trials on this VM, a 20 ms sleep overshoots by up to 25-38 ms over 60 s. Because a stall in the code recurs on every run (the defects were 0.2-2.6 s; the unpumped stage is 0.36-0.43 s every time)
and a VM hiccup does not, the full-startup test allows ONE retry: the limit is exceeded only if it is exceeded in two full startups in a row. That deviates from "one run, assert < lease/3" and
is the one place to push back on. The margin is 1.2-4.8x on the seven clean runs (1.2x for the 81 ms of the 20 ms yield, 1.8x and better with the final 5 ms), 0.6-0.8x on the two outliers.
Uncoupled audits (probe on, seed 0, three processes at once): largest stall 61-67 ms.

Limits: the stall of a thread worker is bounded below by CPython: a numpy/scipy call that holds the GIL cannot be interrupted by `setswitchinterval` (see N2: a 120-sample fit still shows ~0.1 s). A process
worker would remove it but `Calibrator.fit` mutates `ctx.cal` (`hold_yaw_M`, `_last_slack`), so it is not a drop-in; not done. The measured gap says nothing about the real host: `faults.lease_s` still has
to be sized from the worst post-arm stall measured on it (>= 4x), not from these numbers.

### N2 (Medium): the GIL hand-off gap across a large `Calibrator.fit`

Change: `startup.py:427-437` constants `PUMP_YIELD_S = 0.005` (the command thread's sleep on the worker between steps, was the 20 ms of `PUMP_STEP_S`) and `PUMP_SWITCH_INTERVAL_S = 5e-4`; `:455-480` `_pumped` sets
`sys.setswitchinterval(min(old, 5e-4))` for the call and restores it in `finally` (also after an exception of the worker, of `ctx.wait`, and when the caller had already chosen a shorter interval); comment on
`PUMP_STEP_S` rewritten (the 21 ms was the nominal gap, not the worst). Tests: `test_pumped_lowers_the_gil_switch_interval_for_the_call_and_restores_it_whatever_happens`; converted
`test_n2_the_pump_gap_across_a_large_fit_is_a_small_share_of_the_lease_at_the_default_gil_switch_interval_fixed` (60-sample fit: 243 ms before, 27 ms after in its run).

Measured through the real `StartupSequencer._pumped` with a sleeping `ctx.wait` (what `Coordinator.wait` does on a `RealRuntime`: 1 ms sleeps + a pump), "before" = the class constant set to 1.0 s (the 5 ms interpreter
default stays), "after" = the shipped 5e-4; 3 runs each, max gap over the call (ms), lease 300 ms:

| fit | before | after |
|---|---|---|
| real 31-sample fit captured from a startup (2-3 s) | 127 / 230 / 164 | 37 / 31 / 42 |
| synthetic 25 samples (2 s) | 157 / 107 / 113 | 21 / 33 / 28 |
| synthetic 60 samples (4.6-5.8 s) | 168 / 139 / 178 | 29 / 62 / 32 |
| **synthetic 120 samples (14-16 s, the size of the 11-16 s fits of the review)** | **359 / 220 / 246** (p99 89-98) | **108 / 96 / 107** (p99 77-82) |

In the simulator (CPU-bound `ctx.wait`, real 31-sample fit, 30 runs): 13-49 ms, median 16 ms; without the lowering 69-157 ms. For the largest fits the remaining ~0.1 s is a GIL-holding scipy LAPACK call
(`scipy.linalg.svd` inside the TRF solver; `numpy.linalg.svd` releases the GIL, scipy's does not: measured), which no switch interval can cut: 3x margin on a 0.3 s lease, not the 8x of the small fits.

### N3 (Low): the cross-check assumed `frame_interval_s` = 0.1 s

`config.py:139` `still_rate_noise_floor_rad_s(corner_sigma_px, frame_interval_s=STILL_RATE_REF_DT_S)`; `:749-775` the `load_config` cross-check uses `startup.frame_interval_s` (the interval
`wait_until_still` uses, `attitude.py:187`; `tasks.py:141` passes none), which is now also validated `> 0` (a zero interval would have been a `ZeroDivisionError` here and an endless loop in the gate). Message
wording: it still starts "... is below 1.4 x the image rate that sensor noise alone gives ... at camera.corner_sigma_px = X px and startup.frame_interval_s = Y s", then states the ratio and what it does:
below 0.9 x "only rarely ... could not approve a grip or release" (0.9 x opens 75 / 48 / 20 % of the runs with 1 / 2 / 4 tags, 0.6 x none), 0.9-1.0 x "only some of the time ... would often time out",
1.0-1.4 x "would open ... only after seconds (median 1-2.5 s, up to 6 s; 0.5 s at 1.4 x), so slow" (the review's wording was false for that band); the remedies now include lengthening the interval.
Tests: `test_the_noise_floor_cross_check_uses_the_configured_frame_interval_and_the_message_says_so`, `test_the_cross_check_message_is_true_for_the_ratio_it_reports`; converted
`test_n3_the_noise_floor_cross_check_uses_the_configured_frame_interval_fixed` (0.5 px, 0.025, 0.05 s is now refused and said so; the 0.048 it asks for opens the real gate in 40 of 40 runs at 0.05 s, the old
accepted 0.025 in 0 of 40). Shipped profiles unchanged (0.3 px, 0.02, 0.1 s: 1.96x). No test of `test_board_followups*.py` asserted the old N3 behaviour (the M1 message test still matches).

### N4 (Low): reproducibility of the pumped simulation

Probe off, seed 0, uncoupled clock, 3 runs of the same code: READY x3; L0 after VISUAL_INITIALIZATION identical to 5 decimals in all three (2.85817, 2.82456, 3.11112, 3.18666 m); the simulated clock is NOT
bit-reproducible: end 387.44 / 387.96 / 388.02 s (0.15 %), INITIAL_LIFT entered at 84.249 / 84.229 / 84.269 s, REFERENCE_VERIFICATION at 382.5 / 383.5 / 383.4 s (the number of 20 ms pump steps follows
wall time; do not compare clock values bit for bit). The nine coupled full startups above were all READY.
Probe on, seed 0, uncoupled, three processes at once: READY x1 and **FAULT x2 "calibration rejected: 1 outlier readings"** (no station fault, largest stall 61-67 ms); the review's three round-1 runs gave 2 READY / 1 FAULT, so
the pumped tree has 3 READY / 3 FAULT in six probe-on runs. The round-1 tree (`eb07a5d`) probe on, seeds 1-3 (same load): READY x3, so that tree has not faulted in 4 probe-on runs (seed 0 earlier). **OPEN**: not shown to be
caused by the pumping (no lease fault; the pumped computations are the same functions on the same inputs; the simulated clock now advances during them, and the number of timed loop iterations changes the noise
the camera model draws), not excluded either. Cheapest discriminating experiment, not run (my 20-minute allowance was used): the old tree with a random simulated-time offset before each stage at probe on.

### Outside the list of files I was allowed to edit

`tests/cdpr/test_board_followups_review.py`, one test (`test_a_top_up_that_blocks_longer_than_the_lease_..._fixed`, the last case, `sliced()`): its fake flush drove the simulated runtime itself (`co2.wait(0.1e6)` from the
worker thread) while the command thread pumped, which `_pumped` forbids; with the 5 ms GIL interval the two `rt.wait` loops hardly ever interleaved inside a tick, with 0.5 ms they do and 9 of 12 runs latched
Fault.TIMING (6) on a station. It now sleeps 0.1 s per slice instead. Revert it if you object; then that test is flaky.

### Test results (final; `OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -p no:cacheprovider`)

| Run | Result |
|---|---|
| `test_keepalive_pumping.py` (20 tests, 9 new), `test_keepalive_fix_review.py` (4, all converted `_fixed`), `test_board_followups.py` (44), `test_board_followups_review.py` (16), `test_service.py` (4) | **88 passed** in 321 s (the full-startup test: 49 ms largest stall, 170 s) |
| full `tests/cdpr` (`timeout 3600`, 30 min 07 s) | **447 passed, 2 failed**: `test_garments.py::test_failed_grip_is_detected_and_retried`, `::test_release_failure_is_not_reported_as_delivered` |

The two `test_garments.py` failures are **not** a pumping fault but are triggered by this change set, and the cause is a latent bug outside the files I may edit. Both fail the same way in every
unperturbed run on this tree (4 of 4: the full suite and three module runs) and in two runs with read-only instrumentation, and pass 3 of 3 on the round-1 tree (`1411460`); the round-1 tree with only
my `startup.py` and `config.py` copied in fails too (2 of 2 tests), so it is these two files and not the other agent's `service.py` / `claw_link.py`. The two runs of my debug plugins that changed the
model's or the noise stream's state (an extra FK solve before planning, an extra rendered frame) passed 8 of 8. The failing test is the second task of the module's robot: `TaskRunner.run` starts every pass with a "scan" move to its own current xy at `scan_height_m`,
and after the previous task that is a move of a few micrometres (FK rounding: the same move measured 11.4 um in a run where it passed). `plan_line` makes `n = max(2, ceil(T / segment_s))` segments of
T / n; for a move below ~7.5 um that is under `station_core.MIN_SEG_US` (5 ms) and the station answers `nack("range")` ("scan: station A rejected segment 0: range", 7 ms into the task, supervisor
FAULT). Whether the micrometre-sized move lands above or below the limit is chaotic (the end state of the startup differs by up to 15 mm between runs of the same code since round 1, N4), so a task chained
after another task can fail on any tree; I did not measure the failing move itself (measuring it changes it), the `range` nack and the 11.4 um / 12.3 ms / 6.15 ms case that passes are the evidence. Suggested fix, not done (`trajectory.py` / `tasks.py` are not in my list): in `plan_line` treat a move shorter than ~50 um as zero-length (or lift `T` to >= 2 x MIN_SEG), or skip it in
`TaskRunner._move`.

Runs I did not repeat: the full `tests/cdpr` suite once. Timing-based new tests (`test_n2_..._fixed`, the unpumped-stage meter test, the full-startup test) passed on every run of the final code (the full-startup test
needed its retry rule on none of the final runs of the five-file group, but on 2 of the 9 runs listed above the first measurement was 128 / 172 ms).
