# Task layer: independent verification (2026-10-22)

Verifier: independent agent (not the implementer). Tree: branch `claude/magical-cerf-gqr7j7`, HEAD `41886dd`; the four source files under test
(`roomcleaner/cdpr/startup.py`, `garments.py`, `tasks.py`, `claw_link.py`) are unchanged since 00:06 and the implementer's `test_system` /
`test_three_station` logs started at 00:32, so they ran on this code. Nothing was run on hardware; everything is simulation (`config/robot.sim3_34.json`,
seed 3, three stations, housing `_34`). No repository file other than this report and `tests/cdpr/test_task_layer_verification.py` was changed.
Scratch probes: `scratchpad/verify_task/` (outside the repo).

__VERDICT__

## 1. Checks

| # | Check | Expected | Measured | Result |
|---|---|---|---|---|
__CHECKS__

## 2. Findings

__FINDINGS__

## 3. Test counts (each file run ALONE, one after the other, on an otherwise idle 4-core VM)

__COUNTS__

## 4. The flaky full-startup result

__FLAKY__

## 5. How the probes were made (and that they can fail)

* `tests/cdpr/test_task_layer_verification.py`, part A (28 tests, about 1 minute, no startup): a recording stub planner / coordinator / claw under the real
  `TaskRunner._handle` and `run`. Every refusal is injected at every leg and the order of plan, execute and grip events is checked.
  Five mutants of a copy of the tree (`scratchpad/verify_task/mut`) were killed by it: a post-grip `lift` refusal turned into a skip (A1), the dry run removed
  (A2), a dry-run raise height 5 cm off (A5), the jaw-open before `back over` removed (A4), the hamper pre-check removed (A6).
* Part B (9 tests, one shared simulated startup of about 85 s): the PAUSED refusals through the real `Supervisor` (B1), dry run against the real moves (B2),
  sensitivity of the dry run to 5 mm of start error over a payload sweep (B3), a whole task with a blocking claw link and a 1 s detector under the clock-coupled
  `PumpGapMeter` (B4), a PAUSE pressed inside a pumped detection (B5), a detector exception (B6), an unset hamper (B9).
* Differential probe of `_pumped` against the e42e2d4 archive: `scratchpad/verify_task/c1_diff.py` (trace of 20 observations, old versus new).
