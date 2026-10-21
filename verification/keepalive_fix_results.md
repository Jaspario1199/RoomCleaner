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
