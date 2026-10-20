# Per-pose slack probe: results (simulation only)

Scope: the fix proposed for the finding in `verification/floor_reference_study.md` (suspended, four cables over-constrain
the claw, one cable carries mm of slack at many excitation poses, the fit-based classifier misses sub-3 mm slack, the bias
is amplified into `L0`). Implementation: `StartupSequencer._probe_pose` / `_probe_cable` / `_sample_probed`
(`roomcleaner/cdpr/startup.py`), `hinge_analysis`, `probe_response`; estimator side `PoseSample.taut` / `taut_sigma_m`
(`calibration.py`); config `startup.slack_probe` and `probe_*` (`config.py`, both JSON profiles). Design text:
`docs/CONTROL_SYSTEM_V1.md` 6.1a. Everything here is the simulator (`sim/world.py`: linear cables, EA 20 kN, no pulley
friction, no stiction, white IMU and pixel noise); nothing is validated on hardware.

## Bottom line

* The probe **measures the slack to about 0.4 mm RMS** (315 probed readings, 4 simulated startups): 90 % of readings
  with more than 0.8 mm of true slack within 1 mm, taut cables read 0.2 mm on average; the reported 1-sigma is calibrated
  (RMS of error / sigma = 0.84). The probed cable is left within about -0.7 / +1.3 mm of just taut.
* **Vision limits what can be probed, not the method.** Onset needs the claw to move by a few sigma of the vision noise.
  With the default tension guard (`probe_overshoot_max_m` 6 mm) about half of all readings can be probed (poses below
  roughly 0.7 m with the single tag; fewer than half of the poses where only one tag of the sparse board is in view);
  the rest keep the fit's slack hypothesis selection. With 12 mm about 90 % can be probed.
* **Target (accepted runs: worst actual |L0 error| / predicted sigma <= 3; board acceptance no worse than the single
  tag):** met for the 1.0 m sparse board (worst 2.4 sigma with 6 mm, 1.3 sigma with 12 mm; accepted 5/5 against 2/5
  without the probe, single tag 5/5). **Not met for the single tag with the default 6 mm guard** (worst 3.5 sigma, one
  seed; median error 37 mm against 69 mm); met with 12 mm (1.9 sigma), but 12 mm is not a safe default (below).
* **Cost:** about 40 s per pose (6 mm) or 96 s per pose (12 mm), i.e. +1480 s / +3700 s on a simulated startup of
  275 to 304 s (about 25 min / 1 h of added real time at the simulator's 10 frames per second); wall time of the simulator
  rises from about 60 s to 190 s (6 mm) or 400 s (12 mm) per run.
* **Tension:** with 6 mm the plant tension during probe motions peaked at 5.1 / 6.2 N (tag / board), inside the
  ordinary 3.5 to 6.4 N of the unprobed startup (EA 20 kN). With 12 mm one board run reached 19.1 N during a probe
  motion (above the configured 15 N limit): the default stays at 6 mm.

## Study results

Same driver, seeds 0 to 4, `fast_cfg()` (`robot.sim.json`, 5 cm anchor prior, k = 3, `slack_k` 3 mm), cases
"1 baseline single 6in tag" and "3c sparse 3x3 p0.42 (1.0 m, 9 sheets)". "off" reproduces the numbers of the earlier
report (accepted 5/5 and 2/5, medians 69 / 96 mm). Sigma and error come from the final fit of accepted runs and from a
refit of all samples for rejected ones (as in the earlier report); "worst err/sigma" uses accepted runs only.
Rejected runs are not READY (no trust level). All accepted runs end LOCAL_ONLY with beads BLOCKED (absolute sigma above
the gate), as before.

| Case | slack probe | accepted/runs | predicted sigma med / max (mm) | actual max abs dL0 med / max (mm) | worst err/sigma (accepted) | witness RMS, max of accepted (mm) | readings probed | extra time per pose (s) | startup time, simulated (s) | peak cable tension: whole startup / probe motions (N) |
|---|---|---|---|---|---|---|---|---|---|---|
| single 6 in tag | off | 5/5 | 25.1 / 30.4 | 69 / 93 | 3.6 | 3.46 | - | - | 275 | 6.4 / - |
| single 6 in tag | on, overshoot 6 mm (default) | 5/5 | 23.7 / 25.1 | 37 / 83 | 3.5 | 2.11 | 51 % | 38 | 1752 | 17.5 / 5.1 |
| single 6 in tag | on, overshoot 12 mm, 60 frames | 5/5 | 26.4 / 27.9 | 37 / 52 | 1.9 | 2.37 | 91 % | 96 | 3995 | 6.4 / 6.4 |
| sparse board 3x3, 1.0 m | off | 2/5 | 12.7 / 13.6 | 96 / 160 | 7.5 | 2.99 | - | - | 304 | 15.5 / - |
| sparse board 3x3, 1.0 m | on, overshoot 6 mm (default) | 5/5 | 12.0 / 12.9 | 23 / 28 | 2.4 | 0.79 | 53 % | 41 | 1914 | 24.8 / 6.2 |
| sparse board 3x3, 1.0 m | on, overshoot 12 mm, 60 frames | 5/5 | 13.2 / 13.8 | 13 / 17 | 1.3 | 0.00 | 90 % | 96 | 4015 | 19.2 / 19.1 |

Per seed (6 mm default, actual error / predicted sigma, worst cable): tag 2.1, 3.5, 1.3, 1.5, 1.6; board 1.8, 1.6, 1.9, 2.4, 1.5.
Per seed without the probe: tag 1.7, 2.9, 2.8, 3.6, 1.6; board 7.5 (seed 0), rejected (1, 2, 4), 5.2 (seed 3).
"witness RMS 0.00" means no excess beyond the camera's own noise. "Extra time per pose" is the mean over all 38 poses
(including poses where nothing could be probed, which cost one reference measurement); a pose where all four cables
are probed costs roughly 70 to 80 s (inferred from the averages). "Peak tension, whole startup" includes ordinary
'expanded fit/witness' transits near z = 1.44 m that are not probe motions: the unprobed board baseline already shows
15.5 N in that kind of move, the probe runs 17.5 to 24.8 N in four of ten runs (not attributed; see "What remains").

Oracle check of the samples (mean / RMS true-anchor residual per cable, seed 0 tag): RMS per cable 5.1 / 1.9 / 9.4 / 1.8 mm
without the probe, 4.9 / 1.5 / 4.7 / 1.5 mm with it; seeds 2 to 4: 1.0 to 2.8 mm with the probe against 1.3 to 19.5 mm
without. What remains is almost entirely unprobed readings: 1 to 11 readings per cable beyond 3 mm (the hypothesis
selection backstop) and 2 to 12 per cable between 0.5 and 3 mm.

## Choices and the evidence behind them

* **Onset statistic.** A hinge model profiled over the slack with the full per-measurement vision covariance
  (`hinge_analysis`); detection = significance >= `onset_noise_k` (4) sigma and fitted motion >= `probe_onset_translation_m`
  (1 mm). The take-up's rule (motion >= max(2 mm, k * noise)) applied to a norm of the 3-D displacement would have
  needed 20 to 40 mm of claw motion at 1.4 m height (single tag), so the test is on the response direction and the 1 mm
  floor is half the take-up's, justified because the measurement is differential at one pose.
* **Detection overshoot.** Not guessed: the slack is the fit's hinge position using every step beyond onset. Over-retraction
  before detection: median 3.3 mm, 90th percentile 4.9 mm, maximum 6.9 mm (315 readings). Taut cables read slack
  0.00 to 2.0 mm (mean 0.2 mm) and are paid back.
* **Final position and margin.** The cable is paid out to the fitted onset (margin 0). Margin 0.5 sigma (leave it that
  much slack) was run on seeds 1 and 2 (single tag): residual true slack of probed readings mean -0.28 mm in both cases,
  max 1.34 / 1.30 mm at 0 against 0.78 / 1.20 mm at 0.5, final L0 errors alike. No benefit shown, so margin 0
  (`StartupSequencer.PROBE_MARGIN_SIGMA`).
* **Rounds.** `probe_rounds` 2 was run on the board, seed 0: no pose triggered a second-round re-probe (24 probed poses,
  the criterion needs a detectable claw motion toward a finished cable's anchor), result identical to one round. Default 1.
* **Overshoot guard.** `probe_overshoot_max_m` bounds the tension excursion on a taut cable by refusing to probe where the
  predicted detection overshoot exceeds it, after raising the frames per measurement (<= `probe_frames_max`). 6 mm:
  probe-motion tension 5.1 to 6.2 N. 12 mm: 6.4 N (tag) and 19.1 N (board): not safe against the 15 N limit of the sim
  profile. This is the main trade-off for the lead to set per hardware (below).
* **Restore.** After the sample the motor positions are paid back to the pre-probe values. Without it the next
  `plan_line_from` would refuse (actual positions differ from the model's by the slack, > 5 mm) or run from a state the
  planner did not choose.
* **Safety.** Probe moves are `plan_cable_move` packets through `Coordinator.execute`; the `_execute` wrapper turns a
  pause into PAUSED and every other stop into FAULT with `suspended=True` (hold, torque kept, claw marked supported).
  Extra aborts: no onset within `probe_max_m` (40 mm; the largest true slack seen was 21.6 mm); claw moved more than
  max(10 mm, 2 x expected onset motion) without significance.

## What remains

1. **Single tag, default guard:** worst 3.5 sigma on one seed (target 3). Cause: at heights above about 0.7 m a single 16 cm
   tag has depth noise of several mm per frame, onset cannot be resolved within 6 mm of over-retraction, so those
   readings (49 % of all, the ones with the largest slack) keep the old 3 mm classifier. Fix options for the lead:
   a larger guard where the hardware tension margin allows (12 mm: 1.9 sigma), a bigger or multi-tag reference (the board:
   2.4 sigma with the same guard), or treating unprobed readings at noisy poses as weaker (estimator change, not made).
2. **Remaining error is not zero:** predicted sigma is unchanged (12 to 27 mm), and actual errors are 3 to 28 mm for the
   board (6 mm guard). The probe removes the slack bias; the geometry still sets the sigma.
3. **Time.** About 25 min (6 mm) to 1 h (12 mm) of added startup. Most of it is vision dwell (up to 37 frames per
   measurement at noisy poses, 6 measurements per cable). Possible reductions not done: probe only the cable predicted to
   be slack, fewer frames before the first plausible onset.
4. **Peak tension in ordinary transits** of 17 to 25 N in 4 of 10 probe runs (not during probe steps; unprobed board baseline
   15.5 N). Unattributed; check against the planner's tension derating before hardware.
5. **Probe vs. tension when slack is the common case:** the slack cable is pulled up to its onset (about 0 N rise), but
   every taut cable is over-retracted by 1 to 5 mm to be sure it is taut.

## Assumptions and limitations (for hardware)

* Simulation only. Sim vision noise is white per frame, so averaging n frames helps as 1/sqrt(n); a real IMU/camera has bias
  and correlated errors: the differential before/after measurement cancels a constant bias but not drift, and averaging
  helps less than assumed (`still_pose` covariance is divided by n).
* **Onset resolution** is vision-limited: sigma of a differential measurement along the response direction was 0.5 mm
  (z about 0.45 m) to 1.2 mm (z about 0.6 to 0.75 m) with 10 frames; onset needs about 4 sigma of response (about 1 mm floor),
  so 3 to 7 mm of over-retraction. Slack below about 1 mm cannot be resolved (it reads 0 +- 0.3 mm).
* **Tension rise** when probing a taut cable is k_eff * overshoot. Measured on the simulator (EA 20 kN, L about 3 m, claw
  75 mm above the floor, 0.5 mm steps): a lightly loaded cable gains 1.5 N per mm (0.23 EA / L) until the claw
  re-equilibrates; a cable that carries the claw almost alone gains nothing (the claw simply moves). Use
  k_eff = 0.25 EA / L as the design bound: 5 mm of over-retraction is then 8 N at EA 20 kN and 20 N at EA 50 kN. Real Dyneema
  EA is probably 2 to 5 times the simulator's. Set `probe_overshoot_max_m` from the measured EA so that
  overshoot * 0.25 * EA / L stays below the allowed excursion (the planner's derated limit minus the static tension), and
  leave `slack_probe` off until `motion.max_tension_n` is measured. The model has no friction: line friction in guide
  pulleys or stiction would delay the onset, increasing the real overshoot.
* **Step size.** `probe_step_m` 0.5 mm is about 2 microsteps at full-step drive (0.236 mm per microstep with the Spoolv3
  15 mm core, `microsteps` 1) and about 8 at the simulator's 4 microsteps; do not go below 2 microsteps. The step grows x1.5
  up to `probe_max_step_m` (2 mm) while no response is seen. Recommended hardware start: 0.5 mm, 6 mm guard, rounds 1.
* The response model assumes equal-modulus cables of stiffness proportional to 1/length and all four taut; the 50 %
  relative prior on the response magnitude covers a slack cable not yet found. Common-point attachment only (spaced
  attachments change the response and add tilt).
* The `taut_sigma_m` of a probed reading is the probe's profile sigma (0.1 to 1.6 mm), added to the 1 mm length noise.
* Defaults: `slack_probe` false in code and both JSON profiles (it deliberately tensions taut cables; sim tests are
  unchanged and take the same time). Turning it on in `robot.sim.json` roughly triples the wall time of every startup test.

## Reproduce

    /usr/bin/python3 scripts/sim_floor_reference_study.py --suite main --only "1 baseline,3c sparse" --seeds 5 \
        --probe --no-whatif --tag probe --out probe.json
    /usr/bin/python3 scripts/sim_floor_reference_study.py --suite main --only "1 baseline,3c sparse" --seeds 5 \
        --probe --no-whatif --tag probe-guard12 --set startup.probe_overshoot_max_m=0.012 \
        --set startup.probe_frames_max=60 --out probe12.json
    /usr/bin/python3 scripts/sim_floor_reference_study.py --suite main --only "1 baseline,3c sparse" --seeds 5 \
        --no-whatif --tag base --out base.json

About 190 s (6 mm), 400 s (12 mm) or 60 s (off) per run on one core. Tests: `tests/cdpr/test_slack_probe.py` (12 tests,
27 s): onset analysis (synthetic), response model, estimator flag consumption, config validation, and on the simulator:
injected slack measured within 1 mm and the cable left taut with positions restored, an already-taut cable detected on
the first step and paid back, a cable that never goes taut aborting with a hold, a runaway claw aborting, pause between
and during a probe step holding, a noisy pose skipping instead of tensioning blind, and the probe disabled leaving the
sample untouched. `/usr/bin/python3 -m pytest -q tests/cdpr tests/firmware`: 139 passed in 279 s (96 passed in 296 s before
the change; the difference is these 12 tests and the 31 of `tests/cdpr/test_floor_board.py`, which belongs to another
workstream).
