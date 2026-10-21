# Tiny-move fix: planner emitted segments the station nacks

Date: 2026-10-21. Scope: simulation / host software only (`roomcleaner/cdpr`). Station firmware semantics and
`MIN_SEG_US` (5 ms, `station_core.py:33`) are unchanged.

## Finding (reproduced independently)

`TaskRunner.run` opens every pass with `_move(scan)`; the scan target differs from the claw's pose by a few micrometres.
`plan_line` built a rest-to-rest trapezoid whose duration is `T = 2 sqrt(d / a)` and cut it into `max(2, ceil(T / segment_s))`
equal segments. With the fast test profile (`a = 0.3 m/s^2`):

| move | segments | each | station |
|---|---|---|---|
| 3 um | 2 | 3162 us | `nack("range")` -> "station A rejected segment 0: range" |
| 7 um | 2 | 4830 us | nack |
| 7.6 um | 2 | 5033 us | accepted (threshold is ~7.5 um, as diagnosed) |

Two more defects of the same family were found on the way:

* 0 and 1 um moves raised `PlanError("zero-length move")`, which `TaskRunner._move` turns into `StartupAbort` (a pass
  that starts exactly at scan height would have aborted the task).
* `plan_cable_move` had the identical grid, so a cable move of a fraction of a microstep produced sub-5 ms segments too.
* `plan_line_from` would have divided by `dist = 0` for a zero-length move had `plan_line` not raised first.

## Changes

| # | change | where |
|---|---|---|
| 1 | Planner segment floor: every segment >= `MIN_SEG_PLAN_S` = 2 x `MIN_SEG_US` (10 ms), every plan >= `MIN_PLAN_S` (20 ms, two segments). A profile that would be shorter is slowed (triangular profile of exactly that duration: lower peak speed and acceleration, never higher). Segment count is `_segment_count` (>= 2, never so many that one falls below the floor, also for a very fine `segment_s`). | `trajectory.py:29-30,152-161,213-216` |
| 2 | No-op threshold `NOOP_CABLE_M = 20e-6`: a Cartesian move whose four cable lengths stay within 20 um of their start over the whole path (21 probe points, so a chord on a common sphere is not mistaken for "no change") returns a one-knot plan, `Plan.is_noop`. A zero-length move is now such a plan instead of an error. The workspace and tension checks still run on both end points. A no-op that carries a reference-capture flag (`ref != 0`) raises `PlanError` (nothing could be captured; it must not look like a completed search). | `trajectory.py:38,76-80,164-170,188-211` |
| 3 | `plan_line_from`: the model-vs-cable offset check runs before the no-op return, so a tiny move cannot bypass the "model and cables disagree" refusal; the no-op plan holds exactly at the stations' actual positions. | `trajectory.py:259-264` |
| 4 | `plan_cable_move` gets the same floor and segment count. | `trajectory.py:295-298` |
| 5 | `Plan.position_at` returns the single position of a no-op plan (it would have indexed `times[-1]`). | `trajectory.py:91-92` |
| 6 | `Coordinator._execute`: after the readiness gate and the start-position check (unchanged), a no-op plan completes `ok` ("completed: already at the target (no motion)") without consuming a motion id or sending a segment. A pause request is still honoured first (existing code above it). | `coordinator.py:254-259` |

Threshold choice: 20 um, not 50 um. It is far below the geometry's own uncertainty (calibrated length sigma ~1 mm) and is
0.3 microstep on the coarsest simulated drive (~5 on the finest), yet small enough that any Cartesian move of >= 60 um
(some cable then moves >= ~30 um, since four cables span 3-D) stays a real, slowed-down motion that exercises the floor
rather than being swallowed. The floor alone already makes every plan station-legal, so the threshold only removes
pointless motions; it is not what guarantees legality.

Callers (no edits needed, all go through `Coordinator.execute` and read only `r.ok` / `r.reason` / `r.captures` /
`r.releases`; none reads `plan.cart`, `plan.times` or `plan.meta` of a `plan_line_from` plan):

* `tasks.py:121-127` (`_move`): `r.ok` -> continues; zero-length no longer aborts. Covered by `test_task_runner_move_handles_a_tiny_or_zero_move`.
* `startup.py:1172-1182` (`_stage`, via `_execute`): `r.ok` then samples at the pose the claw already holds.
* `supervisor.py:427-434` (lower / recover): `if not r.ok` only.
* `homing.py:157-165` (`BeadVerifier._move`): a plain move completes; a capture move (`ref`) that is too short is refused with a
  `PlanError` text that the existing `except PlanError` returns as `(None, err)`. Covered by `test_bead_verifier_move_...`.
* `startup.py` / `supervisor.py` `plan_cable_move` callers: unchanged semantics (zero move still raises), tiny moves now legal.

`tasks.py` was not edited: its handling is already generic.

## Proving tests (`tests/cdpr/test_tiny_moves.py`, 52 cases)

| requirement | test |
|---|---|
| (a) 0 / 1 / 7 / 60 um never < `MIN_SEG_US`; 0/1/7 are no-ops, 60 is a real plan (3 directions x 2 limit profiles incl. a quick robot with 2 ms `segment_s`) | `test_plan_line_never_emits_a_segment_shorter_than_min_seg_us` |
| every distance 10 nm .. 3 cm | `test_sweep_every_distance_gives_a_noop_or_station_legal_segments` |
| threshold semantics, `ref` refusal, workspace still enforced, cable moves, offset check kept | `test_noop_threshold_...`, `test_a_reference_capture_move_...`, `test_noop_plan_still_validates_...`, `test_plan_cable_move_of_a_fraction_...`, `test_plan_line_from_noop_...` |
| (b) 3 um move through the simulated coordinator: `ok`, no nack, nothing moved, no motion id used | `test_3um_move_through_the_sim_coordinator_does_not_produce_a_nack` |
| small real moves (25 / 60 / 400 um) and a 0.2-microstep cable move run on the stations with no nack | `test_a_just_above_threshold_move_...`, `test_tiny_cable_move_...` |
| firmware unchanged: old-style 3 ms segments are still refused ("range") | `test_control_the_stations_still_nack_a_segment_below_min_seg_us` |
| no-op keeps readiness and pause semantics | `test_noop_keeps_the_readiness_and_pause_semantics_of_a_real_motion` |
| callers | `test_task_runner_move_handles_a_tiny_or_zero_move`, `test_bead_verifier_move_handles_...` |
| (c) the two garments tests | `tests/cdpr/test_garments.py::test_failed_grip_is_detected_and_retried`, `::test_release_failure_is_not_reported_as_delivered` |

Evidence the tests discriminate: against the unfixed HEAD code (constants stubbed so the module imports) 44 of the 52
fail, including the coordinator test with `rejected segment 0: range`; with the fix all 52 pass.

Results:

* `tests/cdpr/test_tiny_moves.py`: 52 passed (9 s).
* `tests/cdpr/test_garments.py`: 8 passed (216 s), including the two that failed since commit 8fa242a.
* Full `tests/cdpr` suite: **527 passed in 1889 s (31 min), exit 0** (`OMP_NUM_THREADS=1 python3 -m pytest tests/cdpr -q`).
  Caveat: the working tree was being edited concurrently by another session (three-station generalisation of
  `trajectory.py` / `coordinator.py` / `homing.py` / `startup.py` / `tasks.py` / `supervisor.py` etc., plus new tests), so the
  suite ran on that moving tree (501 tests at the first run, 527 at the second). An earlier full run (501 tests) gave
  500 passed, 1 failed: `test_keepalive_pumping.py::test_a_full_simulated_startup_never_leaves_the_armed_stations_unpumped_for_a_third_of_the_lease`,
  `expanded: motion not ready: clock uncertainty 5125 us` (budget 5000 us) on a wall-coupled startup with a 23 ms largest pump gap.
  Diagnosis: wall-clock sensitivity of the clock-sync estimate on a shared VM, not this fix: the same test passes alone (twice)
  and in the second full run, and an instrumented full startup executed 62 plans of which 0 were no-op, 0 floored, 0 shorter than
  100 ms, so none of the new code paths ran in it.

## Remaining risk

* A move below `NOOP_CABLE_M` is skipped by design; no caller needs micrometre repositioning (the smallest intentional
  moves are the millimetre-scale bead backoff and slack packets).
* The firmware mirrors the limit (`firmware/winch_station/station_core.h:27`, `kMinSegUs = 5000`, nack "range" at
  line 613); the planner now never emits < 10 ms, a 2x margin. No firmware file was changed or re-tested here.
