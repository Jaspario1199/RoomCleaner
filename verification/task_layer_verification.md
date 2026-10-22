# Task layer: independent verification (2026-10-22)

Verifier: independent agent (not the implementer). Code under test: `roomcleaner/cdpr/startup.py`, `garments.py`, `tasks.py`, `claw_link.py` as of commit
`41886dd` (unchanged since: `git diff 41886dd HEAD -- roomcleaner config tests/cdpr` shows only this verifier's new test file). The implementer's
`test_system` / `test_three_station` logs started at 00:32, after the last edit of these files (00:06), so they ran on this code.
Everything here is simulation (`config/robot.sim3_34.json`, `_34` housing, three stations, seed 3). Nothing was run on hardware; the real YOLO-World detector
and the claw's HTTP timings were not available to anyone. Files changed by the verifier: this report and `tests/cdpr/test_task_layer_verification.py`.
Scratch probes (outside the repo): `/tmp/claude-0/-home-user-RoomCleaner/c51aa926-76d6-52eb-b707-af7c5e22fd24/scratchpad/verify_task/`.

## Verdict: PASS WITH CONDITIONS (for the first real pickup tonight)

No defect was found in the changed code. Every refusal after the jaws close aborts; every skip happens with the jaws open and empty; both pre-motion refusals
pause with the robot holding and resume cleanly; the carry dry run plans the poses of the real moves (target difference 0.0000 mm); nothing slow runs unpumped
on the command thread. The full-startup flake is reproducible on the pre-refactor tree and is not linked to the refactor. Conditions:

1. **Set `tasks.max_payload_kg` to the item's real weight (about 0.3 kg) and put `tasks.hamper_room_m` inside the calibrated area.** At the 0.9 kg default the dry run
   refuses every item ("unreachable ... tension infeasible", 3 in a row pause the run) on the simulated three-cable profile. Measured on sim3_34 (15 N limit,
   0.6 kg claw): all positions pass up to 0.70 kg, none at 0.75 kg. Your real `motion.max_tension_n` moves that edge. (The three-station guide already says this.)
2. **Quiet host PC for the startup** (review L7). The startup can still end FAULT on "clock uncertainty" or a LEASE fault when the host is busy; that is the same
   on the pre-refactor tree (section 4). A FAULT at startup is a re-run, not a defect of the task layer.
3. **Stay at the first deliveries with PAUSE ready.** One pre-existing path (F2, not in the diff) lets the run go on to the next scan with the garment still in the
   closed jaws when the release approval (settle / tilt) is refused. Also unmeasured: the real detector's first-call model load and inference time, and the claw's HTTP times.

## 1. Checks

| # | Check | Expected | Measured | Result |
|---|---|---|---|---|
| 1 | `run_pumped` equals the old `StartupSequencer._pumped` body | same statements, same behaviour | AST of the 4 body statements identical to e42e2d4 after `self.ctx`->`ctx` and `self.PUMP_*`->`StartupSequencer.PUMP_*` (`c1_ast.py`); `startup.py` diff is 59 lines and only this; differential run of 17 observations (result, kwargs, exception identity, step 0.02 s, worker name `startup-pumped_0`, non-daemon, switch interval 0.5 ms inside / restored after normal, exception and abort, abort `StartupAbort(paused=True)` after 3 waits in <1 s, worker not waited for, `ctx.wait` KeyError propagates) old vs new: identical except the two instance / subclass override lines (F1) | PASS (F1 Info) |
| 2a | Nothing slow runs unpumped on the command thread: planning, detection, frame grab, grip with `blocking_io` | stations IDLE, no LEASE, largest gap < 100 ms (lease/3), slow calls on `startup-pumped` | Static: `plan_line_from`, the dry run's `plan_legs`, `det.detect`, `frame_fn`, `claw.grip` are each the argument of `run_pumped` (guards pass; five mutants that unpump one each are killed by `test_task_pumping.py`). Dynamic (B4): whole task on sim3_34 under the clock-coupled `PumpGapMeter`, `blocking_io` claw (each grip and each frame grab sleeps 0.8 s), 1.0 s detector: 5 detector calls, 3+ grips, 4+ frame grabs all on `startup-pumped_0`, largest gap 25 / 39 / 27 ms in three runs, 7-10 gaps above 12 ms, all in simulator vision / render code (`world.py`, `camera.py`, `render_claw_view`) or the task start-up; no coordinator call from a worker; stations IDLE, 0 faults. At the REAL 0.05 m/s speeds (`real_speed_gap.py`): path check 172-417 ms per move (fast3: 77-194 ms); the 4-leg dry run 1.78 s wall, largest gap 22 ms | PASS |
| 2b | An exception or a pause inside a pumped call aborts exactly as before | exception unchanged; pause held by the next `execute` | Exception: same object, same type; no worker left; robot holding (B6, 0.4 s detector raising ImportError through `run()`). Pause (B5): PAUSE pressed 0.3 s into the first 1 s detection: the dry run and the approach plan complete, `execute` returns "paused: test pause", `run_task` -> PAUSED, claw still at the scan point (movement < 1 mm), no grip, `pause_requested` consumed, resume -> READY. (A pause is not an exception of `ctx.wait`; before and after the change it is held by the next `execute`.) | PASS |
| 3a | Refusal after the jaws close (lift, verify shift, raise, transport) aborts, never skips | `StartupAbort` out of `_handle` and `run`; jaws still closed | A1: 8 cases (4 legs x workspace / tension text): all raise `StartupAbort` (`paused=False`) with grips `[open, close]`, no later leg planned, refused move not executed; the same through `run()`; A1b: motion fault and pause at the shift abort too. Mutant "lift refusal returns (False, ...)" killed | PASS |
| 3b | "Unreachable" skips only before motion toward the item or before the grip | skip with nothing planned for execution / jaws open | A2: 8 dry-run cases (4 legs x 2 texts): `unreachable: <leg> sock: ...`, 0 plans, 0 executes, 0 grips. A2b: item outside the workspace: same. A3: approach refusal -> 0 executes, 0 grips; descent refusal -> only `approach` executed, grips `[open]` (nothing was closed); "model and cables disagree" aborts (not skipped). A4: refusal on the second attempt (item outside / dry run / approach plan / descent plan) -> skip with last grip command = open. A6: tall item (hover above `task_max_height_m`) refused before any plan. A7: 3 unreachable in a row -> `pause`, only scan moves, no grip. Mutants "no dry run", "no open before back over" killed | PASS |
| 3c | PAUSED for the two pre-motion refusals leaves the robot holding; resume behaves | PAUSED, no motion, stations IDLE and fault-free, no pending pause; resume -> READY; new task works | B1 [scan] (scan_height 3.5 m) and [hamper] (outside the hull): `sup.state == PAUSED`, "nothing was moved", 0 moves, 0 plans, positions and claw unchanged to 1e-9, `pause_requested` None, item untouched, 3 s of idle ticks: stations `(IDLE, 0)` x3; with a stale `paused_from = ("STARTUP", ...)` in place `resume()` -> READY (`claw_supported` False so it cannot restart the startup); then a normal one-item task delivers. B1b: `task` refused in PAUSED (`CommandRefused`), accepted after resume | PASS |
| 3d | The carry dry run plans exactly the poses the real moves use | same targets, payload mass, low-pose flags | A5 (stubs): 4 legs equal to the real lift / verify shift / raise / transport in target (1e-9), mass (claw + `max_payload_kg`), `allow_low`, chained start poses. B2 (real two-item task on sim3_34, planner spied on both sides): 8 legs: target difference 0.0000 mm, raise xy 0.03 mm (it is where the claw is after the shift), start pose difference 0.05 mm. B3: payload sweep, 12 positions: 0.3 / 0.45 / 0.55 / 0.65 kg: 12/12 pass, 0 thin; 0.70 kg: 12/12 pass but 12/12 fail with the tension limit scaled to 0.97 (thin, position independent: the binding pose is the fixed transport pose); 0.75 / 0.8 / 0.85 kg: 0/12 pass. With 5 mm of start error in 4 directions: 0 refusals at any payload | PASS |
| 4 | Test counts | see section 3 | 0 failures in the requested files | PASS |
| 5 | Flaky full-startup result | linked to the refactor or not | not linked (section 4) | PASS |

## 2. Findings

| ID | Severity | Finding | Reproduce |
|---|---|---|---|
| F1 | Info | `run_pumped` reads `StartupSequencer.PUMP_STEP_S / PUMP_YIELD_S / PUMP_SWITCH_INTERVAL_S` from the class; `_pumped` read them through `self`. An instance or subclass override is no longer honoured. Nothing in the repo does that (tests patch the class). | `python3 c1_diff.py <tree>` on `old_e42` and `/home/user/RoomCleaner`: `instance_override_step_args` `[0.05]` vs `[0.02]`, `subclass_override_step_args` `[0.07]` vs `[0.02]` |
| F2 | **Medium** (pre-existing, unchanged lines, outside the diff) | A refused RELEASE approval (`_settle_and_approve` at the hamper: "claw would not settle" or tilt > `grip_tilt_max_rad`) returns `(False, "release not approved: ...")` with the garment in the closed jaws. `run()` records the item as failed and goes on: the claw moves to the next scan (planned without the payload mass), and the next APPROACH opens the jaws wherever it is. `item still in the claw after release` (jaws were opened, garment reported still held) also continues. The four legs the task asked about abort correctly; this is the approval step. | `pytest tests/cdpr/test_task_layer_verification.py -k "test_a8"` (`a8` = desired behaviour, strict xfail; `a8b` records the current behaviour). Suggested fix, not made: treat a refused release approval as an abort or `paused=True`. |
| F3 | Low (operational) | `tasks.max_payload_kg` default 0.9 refuses every item on three cables; the edge between "carriable" and "refused" is narrow (0.70 to 0.75 kg here). Fail-safe (refused before any motion), but the run ends in "3 consecutive failures" PAUSED without a pickup. | B3 (`pytest ... -k test_b3 -s`) |
| F4 | Low | An unset `tasks.hamper_room_m` is still a plain `StartupAbort` -> FAULT (not PAUSED); `acknowledge` returned the simulated robot to READY with stations IDLE. `Supervisor.paused_from` is never cleared (stale values are harmless here because `claw_supported` is False while suspended, B1). | `pytest ... -k test_b9 -s` ; B1 |
| F5 | Low | `TaskUnreachable` is recognised from the PlanError text prefix (`workspace:`, `tension infeasible`). A reworded PlanError becomes a plain abort, which is the safe direction. | `tasks._UNREACHABLE_PLAN` |
| F6 | Low | An abort (`ctx.wait` raising) leaves a pumped HTTP call (`grip`) running in the background; a grip command could land after the abort. Documented by the implementer; unchanged by this verification. | code reading |
| F7 | Info | `_scan_point` says "nothing was moved" also when it refuses on a later scan iteration (after items were delivered), and an exception out of `run()` discards the `done` / `failed` lists. Unlikely (the hamper is inside the hull). | code reading |
| F8 | Info | The gap before the first pump of a task (`TaskRunner()` Delaunay, `_check_hamper`, `_scan_point`, `_here`) was the worst gap of one of three B4 runs (39 ms, limit 100 ms); the old code planned the scan move there unpumped (47-241 ms measured by the implementer). | B4 |
| F9 | Low (test quality) | `test_task_pumping.py::test_a_carry_leg_outside_the_trusted_volume_or_above_the_task_height_fails_the_item_too` asserts `A and B or C`, which passes for any `raise` / `transport` text. The verifier's A2 covers each leg strictly. | test source |
| F10 | Low (environmental) | The full-startup keep-alive test fails now and then on this shared VM, on the pre-refactor tree as well (section 4). A leftover simulated service from an earlier session (PID 3788, `roomcleaner.cdpr.service --sim`, 25-40 % of a core, not started by the verifier and not killed) ran the whole time. | section 4 |
| F11 | Info (documentation) | `verification/task_pumping_results.md` still has the placeholders `SEE_SYSTEM` and `SEE_THREE`; the results are 11 passed and 6 passed (31 deselected). | below |

## 3. Test counts (each file run alone, one after the other; ambient load: PID 3788 above)

| file | result | time |
|---|---|---|
| `tests/cdpr/test_task_pumping.py` | **18 passed** | 16 s |
| `tests/cdpr/test_task_reach.py` | **17 passed** (no skip) | 280 s |
| `tests/cdpr/test_garments.py` | **8 passed** | 207 s |
| `tests/cdpr/test_keepalive_pumping.py` | **20 passed** (the full-startup test passed in this run) | 172 s |
| `tests/cdpr/test_keepalive_fix_review.py` | **4 passed** | 13 s |
| `tests/cdpr/test_system.py` | **11 passed** (implementer's run, log read; started 00:32, code unchanged since) | 362 s |
| `tests/cdpr/test_three_station.py -k "task or move"` | **6 passed, 31 deselected** (implementer's run, log read) | 300 s |
| `tests/cdpr/test_task_layer_verification.py` (new, this verifier) | **36 passed, 1 xfailed** (strict xfail = F2) | 348 s |

Requested files: 84 passed, 0 failed. Mutants: five unpump-one-call mutants against `test_task_pumping.py` (4+2+2+2+3 tests fail, 18 pass on the original) and five logic mutants
against part A of the new file (post-grip skip, no dry run, wrong raise height, no open before back over, no hamper check) were all killed, so these tests can fail.

## 4. The flaky full-startup result

`test_a_full_simulated_startup_never_leaves_the_armed_stations_unpumped_for_a_third_of_the_lease`, one test at a time, alternating HEAD (refactored) and a `git archive`
of e42e2d4 (before the refactor), ambient load as above. "retry" = the test's own second attempt was needed.

| set | HEAD (refactored) | e42e2d4 (before) |
|---|---|---|
| alone, run 1 | pass 162 s | pass 394 s (retry) |
| alone, run 2 | pass 159 s | **FAIL** 338 s: retry ended LEASE fault (4, 4) on all four stations |
| alone, run 3 | **FAIL** 277 s: `expanded: motion not ready: clock uncertainty 5074 us`, single 146 ms stall (the implementer's failure, same text) | pass 161 s |
| BLAS pinned to 1 thread, run 1 | pass 157 s | **FAIL** 30 s: `local: motion not ready: clock uncertainty 5015 us (A), 5259 us (B)` |
| BLAS pinned, run 2 | pass 174 s | pass 167 s |
| BLAS pinned, run 3 | pass 155 s | pass 158 s |
| total | 5/6 pass | 4/6 pass (+1 needing the retry) |

Judgement: **the known load sensitivity, not the refactor.** (1) `run_pumped` is AST-identical to the old `_pumped` and behaves identically in 15 of 17 observations (the two others are F1); `startup.py` differs in nothing else, and the other differences between the two trees (`chat`, `service`, static files, `claw_link` class attribute, `garments`, `tasks`)
are not on the startup path. (2) The failure reproduces on the pre-refactor tree in both modes (clock uncertainty over the 5000 us budget; LEASE on all four stations) and
at a similar rate (2 of 6 against 1 of 6, plus a retry). (3) The same text was recorded before the change: `verification/tiny_move_fix.md` (`clock uncertainty 5125 us`, 23 ms
largest pump gap) and review L7 in `verification/three_station_mode_review.md` (pump gaps depend on a quiet host, LEASE on all four stations, at HEAD and at the pre-change
commit alike). (4) The test's own retry only covers a pump-gap or station fault, not a startup FAULT, so a clock-uncertainty FAULT is reported as a failure. Pinning BLAS threads did
not remove it (blas1 e42e2d4 run 1), so do not count on that. On tonight's hardware the stations' clocks are real, but the same rule applies: nothing else CPU-heavy on the host during the startup.

## 5. How the probes were made

* `tests/cdpr/test_task_layer_verification.py`, part A (28 tests, about 1 minute, no startup): the real `TaskRunner._handle` / `run` on the armed four-station model robot with a
  recording stub planner, coordinator and claw; each refusal is injected at each leg; the order of plan / execute / grip events is asserted.
* Part B (9 tests, one shared simulated sim3_34 startup of about 90 s): B1 PAUSED refusals through the real `Supervisor`, B1b command gating, B2 dry run against the real moves,
  B3 payload sweep with 5 mm start error, B4 whole task with a blocking claw link and a 1 s detector under `PumpGapMeter`, B5 PAUSE inside a pumped detection, B6 detector exception,
  B9 unset hamper (kept last: it acknowledges a FAULT).
* Scratch: `c1_ast.py` (AST comparison), `c1_diff.py` (old/new differential trace), `plan_speed.py`, `real_speed_gap.py` (0.05 m/s speeds), `run_suites.sh`, `run_flaky.sh`, logs `suite_*.log`, `flaky_*.log`, `partB*.log`.

## Lead follow-up (10/22)

- **F2 fixed.** A refused release approval now raises `StartupAbort(paused=True)`: the task pauses over the hamper with the
  garment held and does not go on to the next scan. `test_a8` is no longer an xfail; it passes. `test_a8b` now asserts the new
  behaviour: PAUSED, jaws still closed, last move `transport`. `tests/cdpr/test_task_pumping.py` still gives 18 passed.
- **F3:** the operator sets `tasks.max_payload_kg` to the item weight (guide section 9).
- **Results file:** the two pending counts in `verification/task_pumping_results.md` are filled from the implementer's logs:
  `test_system` 11 passed; `test_three_station -k "task or move"` 6 passed.
