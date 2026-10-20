# Independent review: per-pose slack probe (commit 3208bf5)

Reviewer: independent verifier (did not write the code). Scope: `docs/CONTROL_SYSTEM_V1.md` 6.1a,
`roomcleaner/cdpr/startup.py` (probe), `calibration.py` (taut flag), `config.py` (probe fields),
`tests/cdpr/test_slack_probe.py`, `verification/slack_probe_results.md`, `scripts/sim_floor_reference_study.py --probe`.
Everything below is the **simulator** (EA 20 kN, no friction); nothing is hardware evidence. All runs were made on detached
worktrees of 3208bf5 (and 2665065 for the comparison), so the other workstream's in-progress edits could not interfere.
Review test file: `tests/cdpr/test_slack_probe_review.py` (9 tests, 73 s, all pass on 3208bf5 and on the current working tree).
Instrumentation scripts (not committed) are in the session scratchpad `.../scratchpad/rv/`: `tens.py` runs one startup and logs
every plant settle, `eq.py` recomputes the true equilibrium, `an*.py` and `hinge_mc*.py` are the analyses.

## Verdict

No Critical finding. The change can stay **as an opt-in, default-off, simulation-validated feature**, with the documentation
corrections below. Two items should be fixed before anyone enables it on hardware (H1, M2). The 17.5 to 24.8 N "whole-startup
tension peaks" are **not real**: they are a limit cycle of the simulator's contact solver, they also occur with the probe off, and
the true equilibrium tension is at most 6.5 N in every run (section 4, the most important result).

| # | Severity | Finding |
|---|---|---|
| H1 | High (for hardware; not for default-off sim) | No tension bound on any probe motion; the only protection is a vision-predicted over-retraction, and the blind-detector abort allows 10 mm of claw motion |
| M1 | Medium | `World._hang` Newton limit cycle reports 14 to 28 N "tensions" and a 7 mm claw flicker; contaminates the study's peak-tension column and the vision samples at those poses (simulator artefact, probe-independent) |
| M2 | Medium | Reported slack sigma looks calibrated only because the sim's vision covariance is conservative; with white noise of the stated size it is under-reported 1.4 to 2.2 times; false onset about 1 % per probe on a never-responding cable, no backstop |
| M3 | Medium | Headline "worst err/sigma 2.4 (board)" does not hold on seeds 5 to 7: 3.05 sigma (target 3); tag 2.5 sigma; 1 of 3 tag seeds rejected (identically to probe off) |
| L1 | Low | Retraction not checked against the bead minimum-length margin; no tilt monitor during probe steps; no progress check in the step loop |
| L2 | Low | Response direction/magnitude not validated (opposite or orthogonal response is accepted as onset) |
| L3 | Low | Vision loss or pause between sample and restore leaves cables un-restored (hold semantics kept; untested) |

## 1. Safety logic

Verified by code reading, the author's 12 tests (pass) and my own tests:

* **Every probe motion** is a `plan_cable_move` packet executed by `StartupSequencer._execute` -> `Coordinator.execute` (readiness,
  start-position match, lease, tracking fault, pause, peer hold), `stop_on_capture=False`. **There is no host- or station-side
  tension check on that path**: the planner's `_check_path` / `tension_derate` apply to `plan_line` only and the coordinator has no
  tension input. The doc text is accurate ("readiness, lease, tracking, station faults, pause, hold") but easy to read as including a
  tension check; see H1.
* **Pause**: honoured between steps (next `execute` returns "paused") and mid-step (author's two tests pass).
* **Aborts hold, never disable**: stalled station C mid-probe -> `StartupAbort(suspended=True, paused=False)`, C `Fault.TRACKING`,
  `tel["en"]` true on all four, claw not on the floor (`test_stalled_station_mid_probe_aborts_with_hold_and_keeps_torque`). Link
  outage of D mid-probe -> abort suspended, D `Fault.LEASE`, D state != OFF, claw supported
  (`test_link_outage_mid_probe_aborts_suspended_and_station_self_holds`). The probe code has no disarm/OFF path.
* **Bounds**: with `probe_max_m` = 5 mm and 12 mm of injected slack the retraction stopped at <= bound + 1 microstep and aborted with
  "no taut onset" (`test_no_onset_retraction_never_exceeds_probe_max`); `h = min(step, probe_max_m - r)` makes this structural. The
  runaway abort (claw moved > max(10 mm, 2 rho |v|) without significance) passes the author's test.
* **Restore**: positions restored within 1 microstep, and, which the author did not test, **slack and tension are restored too**:
  after `_sample_probed` with 3 mm injected slack, per-cable true slack differs from before by < 0.5 mm and plant tension by < 1 N
  (`test_restore_returns_slack_and_tension_not_only_positions`). In the runs, the cable was left within -0.8 / +1.0 mm of just taut
  (240 board probes) and the flagged readings had true slack **at sample time** of mean -0.26, p95 +0.36, max +1.04 mm (209 tag
  readings): later probes in the same pose did not measurably loosen earlier ones.
* **Probe off = identical behaviour**: board seeds 0 and 1 with `startup.slack_probe=false` at 3208bf5 against commit 2665065 give
  identical L0 error vectors (seed 0: [-12.708661, -9.064931, -95.707693, 15.503757] mm in both), identical numbers of plant settles
  (60724 and 60466) and max claw position difference over all settles of 0.0 m. In the diff, with `taut=None` `length_sigma` returns
  `np.full(4, sl)` and every changed expression reduces to the old one; the only addition is a `slack_probe: []` key in
  `calibration.json`. No existing test was edited; `pytest tests/cdpr` all pass at 3208bf5 (135 tests).

### H1. No tension bound on probe motions (High before hardware enable)

Evidence: `plan_cable_move` has no tension argument, and `_probe_cable` / `_probe_pose` never use `motion.max_tension_n`,
`tension_derate`, an EA, or `ws.min_lengths`. The guard `probe_overshoot_max_m` (6 mm) is a *prediction* from vision noise. Actual
over-retraction beyond the true onset: board median 3.5, p90 4.9, max 6.9 mm (2 of 240 above 6 mm); tag median 3.3, p90 4.9, max 6.9
mm (3 of 209 above 6 mm). The blind-detector abort allows the claw to move up to `PROBE_MAX_DISP_M` = 10 mm, about 20 mm of
over-retraction at |response| about 0.5; with the author's own `k_eff` = 0.23 EA/L (1.5 N/mm at sim EA) that is about 30 N at EA 20 kN
and about 75 N at EA 50 kN against a 15 N motor limit (my estimate from the author's constant, not measured). The sim never got
there: true plant tension after any probe cable was at most 6.3 N.
Fix: add `startup.probe_ea_n` (measured), compute the allowed over-retraction `(0.8*max_tension_n - static)/(0.25*EA/L)` per cable, and
(a) skip a cable whose predicted `rho` exceeds it, (b) abort when cumulative retraction beyond the fitted onset exceeds it,
(c) derive `PROBE_MAX_DISP_M` from it. Keep `slack_probe` false until EA is measured.

### L1. Smaller gaps
* Retraction is not checked against the bead margin (`ws.min_lengths` = trigger + 20 mm + k sigma) although it can reach 40 mm; poses
  are mid-volume so unlikely, but a pose near the limit could trip a bead switch (capture events are ignored with
  `stop_on_capture=False`). Fix: cap retraction at `L_now - min_length`.
* Probe steps pass `monitor=None` (the take-up monitors tilt and drag). Steps are <= 2 mm so the risk is low; add an IMU tilt check.
* If a "successful" step does not move the cable, `r` does not advance and the loop never ends (or `plan_cable_move` raises an
  uncaught `PlanError`). Not reachable with a healthy coordinator (tracking fault first). Fix: abort if `r` gains less than half a step.

### L3. Vision loss / pause between sample and restore
`_sample_probed` calls `_sample` (which can raise `StartupAbort(paused=True)` on vision loss) before `_restore_positions`; the abort
leaves the cables in the probed state (a few N of preload, positions off the model by the slack). Hold semantics are preserved and
`Supervisor.resume` -> `visual_check` is the existing path for a suspended pause, but the combination is untested. Add a test and a
sentence in 6.1a.

## 2. Statistics

**Real simulated probes (my seeds 5 to 7, 6 mm guard; 240 board probes, 209 tag probes; truth from the plant: slack =
`world.ell() - world.dist()` immediately before each probe).**

| | board (240 probes) | tag (209 probes) |
|---|---|---|
| error `s_hat - max(true,0)`, mean / RMS / 90 % / max (mm) | +0.11 / 0.32 / 0.59 / 1.35 | +0.12 / 0.35 / 0.66 / 1.25 |
| z = error / reported sigma, RMS | 0.59 | 0.71 |
| P(abs z > 2) | 1.3 % | 2.9 % |
| probes with abs error > 3 mm (false or missed onset) | 0 | 0 |
| true slack > 1 mm / > 3 mm / max (mm) | 37 / 30 / 11.5 | 38 / 25 / 11.5 |
| over-retraction beyond true onset, median / p90 / max (mm) | 3.5 / 4.9 / 6.9 | 3.3 / 4.9 / 6.9 |
| cable left at (true slack after the probe), min / mean / max (mm) | -0.79 / -0.30 / +1.01 | -0.66 / -0.28 / +1.04 |

This agrees with the author (RMS 0.4 mm, z RMS 0.84, left within -0.7 / +1.3 mm); in the sim the reported sigma is conservative
(z RMS 0.6 to 0.7). Coverage: 53 % of board readings (240 of 456) and 59 % of tag readings (209 of 356) probed. **Of the tag readings
the probe skipped, 13.6 % (20 of 147) carry more than 3 mm of true slack (max 13.7 mm)** and fall back to the old classifier, as
the author states.

**Estimator side is correct.** `_assign_slack` skips `drop` for flagged cables, the witness `rf` is set to -inf for flagged cables
(`calibration.py:487,703`), and the taut sigma enters `hypot(sl, taut_sigma)` in `_rows`, the `_assign_slack` residuals, `norm_rms`,
`residuals_m`, the outlier test and hence the Jacobian and posterior (so the predicted absolute sigma includes it). The remaining
uses of the plain `length_sigma_m` (witness `rf` for unflagged cables, `length_sigma()`, recovery) are about unprobed quantities.
Consequence: with no hypothesis backstop, a *wrong* flag (false onset, or a cable slackened afterwards) enters as a hard outlier with
sigma about 1 mm. In the sim only 0.5 % of flagged readings had more than 1 mm of slack at sample time and none more than 2 mm.

### M2. Sigma calibration and false onsets (synthetic, my noise model; `hinge_mc.py`, `hinge_mc2.py`, 300 trials per cell)
Independent white noise per measurement (lateral 0.4 to 1.5 mm, depth 2x), response |v| = 0.6, model response correct, stopping rule
and step schedule copied from `_probe_cable`:
* Responding cable (slack 0 to 10 mm): detected 100 % (no missed onsets within 40 mm).
* **False onset** (cable never responds): 3/300 (sigma 0.4 mm), 2/300 (0.8), 0/300 (1.5), about 1 % per probe, at r = 7 to 33 mm.
  With 150 probes per startup that would be about 1.5 false onsets per startup; in the real simulator 0 of 449. A false onset flags a
  slack cable "taut" with sigma about 1 mm: a 7 to 25 mm outlier with no backstop.
* **Sigma under-reported** when the covariance equals the actual noise: z RMS 1.4 to 2.2, P(abs z > 2) = 9 to 18 % (expected 4.6 %);
  the s = 0 case is biased +0.5 to +1.0 mm (positive hinge bias, clipping, optional stopping). The simulator's `still_pose` covariance
  is larger than the actual frame-to-frame noise, which hides this (real z RMS 0.6 to 0.7). On hardware the covariance will be closer
  to the noise and noise will not be independent, so the reported sigma should not be trusted at its 1-sigma meaning.
* Response-model mismatch (true response 0.4 / 0.6 / 1.5 x the model, 30 / 60 deg off, orthogonal, opposite sign): onset detected
  100 %, slack error RMS 1.2 to 4.2 mm, z RMS 1.8 to 2.8 (L2: nothing checks that the fitted `w` agrees with `v`). A zero-response
  cable (slipping on its spool) is detected 1 % of the time, i.e. aborts at `probe_max_m` as intended.

Recommended: (1) require a confirming step (two consecutive detections) before declaring onset; (2) reject the onset and abort
if the fitted `w` departs from `v` by more than about 2 prior sigma; (3) inflate `taut_sigma_m` by 2 (or add a 0.5 mm floor) until the
noise model is validated on hardware; (4) treat flagged readings robustly (Huber) in the fit.

## 3. Reproduction of study rows (seeds 5 to 7; the author used 0 to 4)

Same cases (`case_table()`), `fast_cfg` with `startup.slack_probe` (6 mm default), run through `Supervisor.start` by my instrumented
driver (`tens.py`; same calls as the author's `run_one`). "worst" = max over cables of abs(dL0) / predicted absolute sigma of the
final fit.

| Case | probe | seed | outcome | worst abs(dL0)/sigma (max abs dL0, mm) | witness RMS (mm) | sim startup time (s) | readings probed/skipped |
|---|---|---|---|---|---|---|---|
| board 3x3 p0.42 (1.0 m) | 6 mm | 5 | accepted | 1.99 (23.3) | 0.00 | 1897 | 80/72 |
| board | 6 mm | 6 | accepted | 1.30 (15.9) | 0.00 | 2107 | 83/69 |
| board | 6 mm | 7 | accepted | **3.05** (34.4) | 0.00 | 1901 | 77/75 |
| board | off | 5 | accepted | 2.66 (29.3) | 1.93 | 314 | - |
| board | off | 6 | rejected (local: ambiguous alignment) | - | - | - | - |
| board | off | 7 | accepted | 8.39 (113.1) | 4.78 | 298 | - |
| single 6 in tag | 6 mm | 5 | accepted | 1.28 (34.5) | 0.49 | 1781 | - |
| single tag | 6 mm | 6 | rejected (local: ambiguous alignment) | - | - | 991 | - |
| single tag | 6 mm | 7 | accepted | 2.52 (53.5) | 0.00 | 1760 | - |
| single tag | off | 5 | accepted | 1.48 (31.1) | 2.09 | 278 | - |
| single tag | off | 6 | rejected (same reason) | - | - | - | - |
| single tag | off | 7 | rejected (witness 5.5x predicted variance) | - | - | - | - |

The benefit is reproduced (board: 3/3 accepted vs 2/3, worst 3.05 vs 8.39 sigma, witness RMS 0 vs 1.9 to 4.8 mm; tag: 2/3 vs 1/3) and
the probe is not what rejects tag seed 6 (rejected identically with the probe off). But, **M3**: over the 8 board seeds (author 0 to 4,
mine 5 to 7) the worst is 3.05 sigma (seed 7, cables B and D: 31.7 and 34.4 mm against a sigma of 13), above the stated 3 sigma target
and the "worst 2.4 sigma" headline; the tag figures are 3.5 and 2.5 sigma. Restate the claim ("worst 3.05 sigma over 8 seeds; the probe
shortens the tail, it does not remove it"). Added simulated startup time is 1500 to 1750 s (25 to 29 min) per run.

## 4. The whole-startup tension peaks of 17.5 to 24.8 N (most important)

**Answer: a simulator artefact (limit cycle of `World._hang`), not a violation of the planner's tension limit and not a probe side
effect.** It occurs with the probe off, on the unprobed board baseline, and was also seen at the 2665065 behaviour.

Method: every plant settle (5 ms) was logged (time, label of the executing plan, `world.tension`, claw p, cable free lengths `ell`). For
each settle with reported tension > 6.5 N, and every 50th settle, the **true static equilibrium** for the same `ell` was recomputed
independently by minimising the convex potential `m g z + sum k_i max(0, d_i - ell_i)^2 / 2` (BFGS; residual gradient < 1e-9 N;
`rv/eq.py`). Every settle above 6.5 N in every run was a non-equilibrium state.

| Run (case, probe, seed) | time, plan | reported T (N) | claw p (m) | true equilibrium T (N) | planner's min-max distribution at that pose (N) |
|---|---|---|---|---|---|
| board, **off**, seed 5 | 238.6 s, "expanded fit", (0.815,0.535,1.445)->(0.815,0.269,1.445) | [22.65, 0, 28.08, 0] | z = 1.442 | [5.64, 1.78, 2.23, 0] | [4.96, 3.08, 0.5, 1.26] |
| board, **off**, seed 1 (identical on 2665065) | 300.235 s, "expanded witness" | [0, 13.55, 0, 15.50] | z = 0.821 | [2.35, 3.99, 0, 2.45] | [3.17, 3.17, 1.06, 1.38] |
| board, probe, seed 6 | 1806.705 s, "expanded fit", (1.923,2.345,1.445)->(2.19,2.345,1.445) | [23.70, 0, 22.04, 0] | z = 1.445 | [2.06, 0, 5.44, 2.69] | [0.5, 1.37, 4.63, 3.84] |

* Signature: tension and claw position **alternate every 5 ms between two states** (seed 6: [23.5, 0, 22, 0] <-> [0, 0, 14.0, 6.8] and
  y = 2.3435 <-> 2.3368 m, a 7 mm flicker), for 19 s (seed 6, including the pose at rest, label None), 14 s (seed 5) and 422 settles
  (seed 1). Neither state is an equilibrium.
* Root cause: `World._hang` (`sim/world.py:158`) is an undamped Newton iteration whose Hessian contains only currently taut cables, with
  a 5 cm step cap, 30 iterations and no line search. With nearly horizontal cables (z about 1.44 to 1.45 m, the top of the excitation
  box) and a cable at the taut/slack boundary it limit-cycles: the iterates swing through 14, 250, 24 and 313 N and 400 iterations from
  the recorded state do not converge; `settle()` stores whichever iterate it stops on. Pinned by
  `tests/cdpr/test_slack_probe_review.py::test_world_hang_newton_limit_cycle_is_not_a_physical_tension` (recorded state, anchors and
  `ell` embedded).
* Frequency in my 16 instrumented runs: artefact in board-off 2 of 5 (seeds 1, 5), board-probe 1 of 3 (seed 6), tag-off 0 of 3,
  tag-probe 0 of 3 (the author: 4 of 10 probe runs, 1 of 5 baseline). Nothing shows the probe changes the rate; the sample is too small
  to show it does not.
* True peaks are 4.4 to 6.5 N in all 16 runs (max 6.5 N at z = 1.45, "expanded fit"), under the planner's derated limit (0.8 x 15 = 12 N
  including dynamics) and the 15 N motor limit. Planned min-max tensions at the artefact poses are 4.6 to 5.0 N; the stiff-cable
  equilibrium is 5.4 to 6.1 N, so the planner's check is not contradicted. The author's probe-motion peaks (5.1 / 6.2 N) are valid
  (mine: at most 6.3 N after any probe cable).
* Side effect of the artefact: a vision sample taken while the plant is in the limit cycle carries up to 3.5 mm of unmodelled claw
  flicker (seed 6: samples between 1799 and 1819 s). This affects probed and unprobed runs alike and is a plausible contributor to
  some "witness 4.5x predicted variance" rejections; I did not isolate it.
* Caveat on the planner (independent of the probe): `_check_path` verifies that a bounded min-max tension distribution exists (static,
  rigid cables). It does not model cable compatibility, so tension in the over-constrained four-cable suspension equals length errors
  times EA/L (6 to 14 N/mm here). At EA 20 kN and the present model accuracy the true peaks are 6.5 N, but this scales with a stiffer
  real cable and belongs in the hardware plan.

Fix: make `_hang` a damped, line-searched Newton (the energy is convex, so backtracking on U converges), assert the gradient residual in
`settle()`, and have the study's peak-tension tracker ignore non-converged states. Correct `verification/slack_probe_results.md`: the
"peak cable tension: whole startup" column (17.5 / 24.8 / 19.2 N) and item 4 of "What remains" should read "simulator solver artefact;
true peak <= 6.5 N".

## 5. Other points for the lead

* 6.1a: add "no tension limit applies to probe motions" and the H1 caveat next to the coordinator sentence.
* Cost: 25 to 29 min of added real time per startup and about 3x test wall time if switched on in `robot.sim.json`; default off keeps
  all existing tests at the previous speed (confirmed).
* The study script's tension tracker for "probe motions" covers only plans labelled `probe*`, not the still measurements between steps;
  my full-run equilibrium check covers those and agrees (<= 6.3 N).
* Hardware unknowns the sim cannot answer (the author lists them): EA, line friction/stiction (delays onset, increasing the real
  over-retraction), correlated vision noise, 0.5 mm step = 2 microsteps only at 1 microstep full-step drive.
* Not reviewed: `board.py` / the floor-board detector (other workstream) and real-camera behaviour.

## Commands to reproduce
    /usr/bin/python3 -m pytest -q tests/cdpr/test_slack_probe_review.py        # 9 passed, 73 s
    /usr/bin/python3 -m pytest -q tests/cdpr                                    # all pass at 3208bf5
    # instrumented startup (scratchpad rv/tens.py): args  case seed probe(0/1) out.pkl ; WT=<worktree> selects the commit
    /usr/bin/python3 tens.py "3c sparse 3x3 p0.42 (1.0 m, 9 sheets)" 5 0 base_board_5.pkl   # probe off: sim peak 28.1 N, true 6.1 N
    /usr/bin/python3 tens.py "3c sparse 3x3 p0.42 (1.0 m, 9 sheets)" 6 1 probe_board_6.pkl  # probe on:  sim peak 23.7 N, true 6.2 N
