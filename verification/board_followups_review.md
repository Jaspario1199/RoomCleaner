# Independent review: board-attitude follow-ups (config ranges, rocking watch, board survey at startup)

Reviewer: independent calculation-checker (did not write the code). Under review: `verification/board_followups_results.md` and the code of
the commits after `180b015` (`077c0e7`, `52b5d4f`, `bc2964e`, `eddf04a`; the task's own files are in them). Everything below is **simulation**
(`/usr/bin/python3`, `OMP_NUM_THREADS=1`, 4 shared vCPU): the real corner noise, the real host CPU, the real `faults.lease_s` and the real
claw/floor are unmeasured. Nothing was committed; no code, config or default was changed. Review tests:
`tests/cdpr/test_board_followups_review.py` (16 tests, 15 s, all pass; written to PASS while the finding is true). Scratch scripts and
raw outputs: session scratchpad `.../scratchpad/rev/` (`mc_rock.py`, `time_survey.py`, `bench_*.py`, `stall_run.py`, `run_study_tree.py`).

## Verdict: ACCEPT WITH CONDITIONS

The three deliverables do what the write-up says and no acceptance threshold was relaxed (proved by a diff of every default, section 6).
Conditions, in order of importance:

1. **Before the first suspended run on hardware**, stop the survey top-up (and, as the same defect, the calibration fits) from starving
   the station keep-alive (H1). Not a drop hazard (torque is kept), but it aborts the startup with the claw hanging.
2. Fix the wrong noise-floor claim behind `tasks.grip_still_rate_rad_s` and add the missing cross-check with `camera.corner_sigma_px` (M1).
3. Document and report the rocking watch's real sensitivity per tag count, and measure `camera.corner_sigma_px` on the real camera before
   relying on a 5-sigma threshold (M2); raise `rocking_tilt_k`'s lower bound to 4 (L1).
4. Do **not** flip `startup.slack_probe` to true yet (section 4).

## Supplied facts, assumptions, derived results, uncertainty

* Supplied: the implementer's report; `config/robot.sim.json` (`faults.lease_s` 0.3 s, `motion.hold_time_s` 0.25 s, camera `fx` 520 px);
  `config/robot.example.json` (hardware profile, `lease_s` null = unmeasured); D26/D27; `verification/slack_probe_review.md` (H1/M2/M3).
* Assumptions used: i.i.d. Gaussian corner noise (the model the whole design uses; correlated/biased corner errors, IPPE flips, glare, curl
  are not modelled by anyone); host CPU = this sandbox.
* Derived (own runs): sections 1-4. Uncertain: every absolute time (CPU of the real host), the real lease, the real corner noise.

## Findings by severity

| # | Sev. | Finding | Evidence |
|---|---|---|---|
| H1 | High (hardware availability; not a drop hazard) | The survey top-up (`StartupSequencer._survey_topup`, `startup.py:838` `out = sv.flush()`) blocks the command thread for 0.8-2.5 s CPU per accepting flush with no keep-alive pumped; `faults.lease_s` is 0.3 s and the ping period 20 ms. Any stall > lease latches Fault.LEASE (state FAULT) on all four armed stations. The same is already true of every `Calibrator.fit` (0.6-7.9 s CPU) | section 3 |
| M1 | Medium | `tasks.grip_still_rate_rad_s` lower bound 0.005 and its stated reason are wrong: a still claw's noise-only image rate is **1.0e-2 rad/s** at 0.3 px, not 4e-3 (the mean of corner-shift *norms* does not average away). Any limit below ~0.009 never opens; no cross-check ties the limit to `camera.corner_sigma_px` (1 px passes `load_config` and makes the shipped 0.02 unreachable). Fails closed | `test_still_claw_image_rate_noise...`, `test_no_cross_check...` |
| M2 | Medium | The rocking watch's sensitivity depends on the tag count far more than the write-up/doc suggest. Real-detector Monte Carlo: threshold (5 sigma) median **15.3 / 9.1 / 7.5 / 5.9 mrad for 2 / 3 / 4 / 5 tags at 0.3 px** (8.0 / 4.7 / 3.9 / 3.1 mm of body-origin motion) and **24.7 / 13.6 / 10.6 / 7.2 mrad at 0.5 px** (12.8 / 7.1 / 5.5 / 3.7 mm). The doc's "5-10 mrad, 3-5 mm" holds for >= 3 tags only. With a corner noise 2x the configured one, false stops occur in about half the take-ups (analytic) | section 2 |
| L1 | Low | `startup.rocking_tilt_k` lower bound 3 is inside the range although its own reason says "several false alarms per take-up": simulated, **98 %** of 430-evaluation take-ups trip at k = 3, 12.7 % at k = 4, 0.15 % at k = 5 | `test_rocking_k_lower_bound...` |
| L2 | Low | The dwell-vs-timeout cross-check refuses a configuration the gate handles: `wait_until_still` extends a loaded release's timeout to `max(timeout, dwell + 2 dt)` and the no-signal dwell is not bounded by the timeout, so "a loaded release could never be approved" is not true. Over-strict, harmless. It also hard-codes a 1.5 s period (the real loaded simple period is 1.25 s at 0.9 kg) | `test_dwell_cross_check...` |
| L3 | Low | `grip_period_margin` lower bound 1.2 is exactly `sqrt(1 + (k/L)^2)` for the assumed (unmeasured) gyration radius k = 0.13 m: zero allowance. A uniform rod of the claw's length (k = 0.149 m) gives 1.26 > the shipped 1.25 (unloaded). The loaded ratio is only 1.10, so the loaded dwell is conservative | `test_compound_pendulum...` |
| L4 | Low | `camera.corner_sigma_px` lower bound 0.05 px is below the only evidence cited for it (cv2 corner bias 0.15 px, `floor_board_detector.md`), and no cross-check with `pose_cov_inflate` (1..5): 0.05 px x 1.0 is a covariance 40x smaller than the validated 0.3 x 1.3 | reading |
| L5 | Low | `rocking_yaw_coupling` upper bound 0.5 lets a 10 deg take-up yaw hide 5 deg of tilt (= `grip_tilt_max_rad`); default 0.08 is fine | reading |
| L6 | Low | `load_config` now depends on the working directory (relative `marker.board_layout_file`); a profile cannot be validated off the robot. Documented in the message | `test_board_layout_file_check_depends_on...` |
| L7 | Low | `FloorBoardSurveyor.save` does `fsync` + a `.bak` copy inside the same stall (SD-card latency adds to H1); the layout object is mutated on the command thread while the `claw-frames` thread runs the detector on it (per-tag replacement is atomic, a cleared tag could give one frame with a (0, 0, 0) tag pose that the 2 px consistency check should drop) | reading |
| I1 | Info | The 4 mrad floor of the rocking threshold never binds: 5 sigma is >= 5.9 mrad even with 5 tags. The effective rule is `5 sigma + 0.08 x yaw` | section 2 |
| I2 | Info | The SELF_CHECK survey (1 s of unpumped compute) is harmless: it runs before `co.configure()` and `co.arm()` (stations unarmed, no lease check) | `test_self_check_survey_runs_before...` |

## 1. `config.ATTITUDE_BOUNDS` (13 ranges) and the cross-checks

Own checks: read all 13 reasons against the code and the repo's numbers; recomputed the quoted figures; loaded both shipped profiles;
pinned every existing default against a `git archive` of `180b015`.

| key | range | verdict |
|---|---|---|
| `camera.corner_sigma_px` | 0.05-2 px | upper OK (= detector reprojection limit); lower below its cited evidence (L4) |
| `camera.pose_cov_inflate` | 1-5 | OK; at 1.3 the detector covariance is calibrated (E z^2 = 1.21 measured against 1.18 predicted, section 2) |
| `claw.vision_attitude_floor_rad` | 0.2-20 mrad (and <= `vision_attitude_sigma_rad`) | OK |
| `tasks.grip_period_margin` | 1.2-3 | lower bound has no allowance for the assumed k (L3) |
| `tasks.grip_still_rate_rad_s` | 0.005-0.1 | lower bound and reason wrong (M1); upper OK (0.1 rad/s = 17 mrad swing) |
| `tasks.grip_still_frames` | 3-30 pairs | OK (3 pairs = 0.3 s detects a swing amplitude > 4.4 mrad at the 0.02 limit); units assume `frame_interval_s` = 0.1 |
| `tasks.grip_settle_periods` / `_min_s` / `_timeout_s` | 3-20 / 1-10 s / 10-120 s | OK; the timeout reason ignores the loaded-release extension (L2) |
| `startup.board_survey_frames` | 10-200 | OK |
| `startup.rocking_tilt_k` | 3-10 | lower bound contradicts its reason (L1) |
| `startup.rocking_tilt_min_rad` | 1-20 mrad | OK (but never binds, I1) |
| `startup.rocking_yaw_coupling` | 0-0.5 | upper bound loose (L5) |
| `marker.board_layout_file` | null or an existing, parseable layout | works; cwd-dependent (L6) |

Cross-checks:
* **floor <= vision sigma**: catches what it claims (0.012 > 0.010 refused, equality accepted). Weak in meaning (it equates two different
  things) but not wrong.
* **periods x margin x 1.5 s <= timeout**: catches nothing real (L2); the message states a failure the gate prevents itself.
* **Shipped configs still pass**: `robot.sim.json` and `robot.example.json` load and sit inside all 13 ranges; **no existing default changed**
  in either profile (the only config diff is five new `startup` keys), see section 6.

## 2. Rocking watch (`perception.tilt_change`, `startup.RockWatch`)

The implementer's unit tests draw the frame noise from the same covariance model the watch uses, so they cannot show that the covariance is
right. I pushed i.i.d. corner pixel noise through the **real `BoardDetector`** (solvePnP, Cramer-Rao covariance, `VisionSource`) and fed
`RockWatch`: 48 random resting poses with 2-5 tags in the reference, 150 frames each (7,200 frames), then rocks of 4-30 mrad about a floor
line 40 mm from the body axis (`scratchpad/rev/mc_rock.py`).

| true / configured corner noise | false trips (48 take-up windows) | E z^2 = E\|mean tilt\|^2 / model variance (exact 1.18) | threshold by tags in the reference (median, mrad) |
|---|---|---|---|
| 0.3 / 0.3 px | **0** | 1.21 | 15.3 (2), 9.1 (3), 7.5 (4), 5.9 (5) |
| 0.5 / 0.5 px | **0** | 1.21 | 24.7, 13.6, 10.6, 7.2 |
| 0.5 / 0.3 px (corner noise under-set) | 1 | **3.35** | 15.4, 9.1, 7.5, 5.9 (unchanged: the threshold follows the configured value) |

* **The 5-sigma-of-a-3-frame-mean rule is sound.** The reported tilt covariance is calibrated against the real detector (1.21 against 1.18),
  so the matched-noise trip probability per evaluation is about exp(-25 / 1.21) = 1e-9; zero trips in 14,400 frames at both 0.3 and 0.5 px
  agree. The write-up's "0.39-0.60 of threshold" in its 1,721 evaluations is consistent.
* **It is not robust to an under-set `camera.corner_sigma_px`.** The threshold scales with the configured value, the noise with the true one.
  At 1.67x (0.5 vs 0.3 px) the effective rule is 3 sigma (E z^2 = 3.35); analytically exp(-25 / z^2) per evaluation, i.e. about 2 % of
  150-frame windows and about 8 % of 430-evaluation take-ups; at 2x about 55 % of take-ups. A false trip in the take-up declares the onset
  early; in the pretension it aborts the startup. The write-up says the corner noise must be measured; this is why.
* **Detection of a real rock (>= 2 tags).** Detected within 30 frames, median latency 3 frames once above threshold:

  | rock (mrad) | 0.3 px: 2 tags | 3 tags | 4 tags | 0.5 px: 2 tags | 3 tags | 4 tags |
  |---|---|---|---|---|---|---|
  | 6 | 0/17 | 7/13 | 7/17 | 0/17 | 0/13 | 0/17 |
  | 8 | 0/17 | 12/12 | 18/18 | 0/17 | 1/12 | 9/18 |
  | 10 | 3/17 | 12/12 | 18/18 | 0/17 | 7/12 | 17/18 |
  | 15 | 17/17 | 12/12 | 18/18 | 2/17 | 12/12 | 18/18 |
  | 20 | 17/17 | 13/13 | 17/17 | 15/17 | 12/12 | 18/18 |

  At exactly two tags (the gate for "active") the watch is blind below 15 mrad (0.3 px) or 25 mrad (0.5 px), 8-13 mm of body-origin motion;
  with 4 tags it sees 8-10 mrad (4-5 mm). The doc's "5-10 mrad, 3-5 mm" is the >= 3-tag case (M2). The 4 mrad floor never binds (I1).
* **One-tag fallback logs and nothing else** (own test): `can_see` False, 50 frames at 200 mrad never fire, the log line appears once for
  two take-ups, `rocking_check` = "blind...", `rocking_blind_at` lists both. In `slack_takeup` the onset test is `disp >= thr or rocked`
  and the slide direction `(cam_displacement if mon["rocked"] else floor_displacement)`; with `rocked` always False both are the previous code.
* **No acceptance threshold relaxed**: the watch only adds ways to stop (earlier onset, a new pretension abort).
  Plant-level evidence (the implementer's four full take-ups with `World(rock=...)`) re-ran and passes.

Recommendations (not done): store `rw.last_thr_rad` next to `rocking_<sid>_max_tilt_rad` and log a warning when it exceeds ~10 mrad
("rocking sensitivity weak: N tags"); require >= 3 tags for "active" on hardware, or state 2 tags as degraded.

## 3. Board survey at startup: blocking time versus the lease (the implementer's hardware risk)

**Facts.** `faults.lease_s` = 0.3 s (`robot.sim.json`; null in the hardware example = unmeasured), keep-alive ping every
`min(lease/4, 20 ms)` = 20 ms (`Coordinator.pump`), `motion.hold_time_s` 0.25 s, `telemetry_max_age_s` 0.15 s. While `Service` runs a command
(`start`) the idle host loop is skipped (`Service.idle_tick` returns at the lock), so only the command thread's `ctx.wait` keeps the stations
alive. A station whose host is silent for `lease_us` sets Fault.LEASE and enters State.FAULT (queue cleared, torque kept; `station_core.py`
`_set_fault`). `tests/cdpr/test_service.py::test_idle_host_loop_keeps_stations_alive` already shows a 1 s stall gives flt = 4 on all stations.

**Measured blocking time** (CPU/wall seconds of the calling thread; this sandbox, 4 vCPU, partly shared with other jobs; the 60-frame flush
takes the same 2.3-2.5 s on an idle machine, so contention is not the cause; the real host is unknown and a small single-board computer
would more likely be slower than this sandbox):

| call | measured | against lease 0.3 s / ping 20 ms |
|---|---|---|
| accepting `flush()` with 3 offered windows (synthetic, `bench_flush.py`, 3 seeds) | 0.77-0.95 s; its two bundle adjustments 0.23-0.41 s each | 3x / 40x |
| accepting `flush()` with 60 frames (as the startup offers; `bench_flush60.py`) | 2.3-2.4 s | 8x / 120x |
| the three accepting flushes of a full simulated startup (`time_survey.py`, probe on, seed 0, top-ups at t = 144, 178, 352 s) | 1.9, 2.1, 2.5 s | 6-8x |
| non-accepting flush | 0.01-0.08 s | harmless |
| SELF_CHECK `run()` (30 frames + `finalize`) | 0.4-1.0 s | harmless: stations not yet configured/armed (I2) |
| `Calibrator.fit` (existing, 5 calls in the same run) | mean 2.4 s, max 7.9 s | already 8-26x |

Largest gaps between consecutive `Coordinator.pump()` calls in that startup: 4.3, 3.6, 2.6, 2.5, 2.1 s (24 gaps > 0.3 s); three of the top five
contain a survey flush, the others a calibration fit. About 90 % of a flush is `BoardSurvey._bundle` (cProfile): `update()` runs one
bundle adjustment and `refine()` another, each `max_nfev = 40` with `ftol = xtol = gtol = 1e-10`, which is never met (nfev reaches 40 in
several runs); the result is identical at a cap of 4 (same sheets, <= 0.33 mm).

**Is it a real fault risk on hardware? Yes, conditionally and reproducibly.** If `faults.lease_s` on the real machine is of the order of the
sim value (0.3 s), every accepting top-up latches Fault.LEASE on all four stations while the claw hangs. Consequences, from the code and the
docs (`Stop != disable`): torque is kept, the claw does not drop; but the next `co.execute` refuses ("not ready: telemetry stale", then "state FAULT" once the telemetry arrives), the startup aborts suspended
(`StartupAbort(suspended=True)` -> `claw_supported = False` -> RECOVERY_REQUIRED, D25), the latched fault needs `acknowledge`, and the startup
(5 min, or ~30 min with the probe) is lost. It happens on the **first startups with a new or moved board** only: once all sheets are in the
layout file nothing is offered and `flush()` returns None. The risk is not new in kind: the existing calibration fits stall the pump for
longer (table), so a hardware lease of 0.3 s would already fault at the first refit. The implementer's statement "the existing calibration
fits already block similarly" is therefore **correct**, and it means the lease/pumping design has an open problem independent of this change.
Test: `test_a_top_up_that_blocks_longer_than_the_lease...` (a 0.9 s unpumped stall inside `_survey_topup` -> flt = 4 on A-D; the same compute
in 0.1 s slices that pump -> flt = 0). Full-startup demonstration: section 3.1.

### 3.1 End-to-end: a stalled versus a pumped top-up in a full simulated startup (`stall_run.py`, survey mode, probe off, seed 0)

Each accepting `flush()` was made to cost an extra 0.9 s of host time (the measured CPU of a small accepting flush; real ones are 2x that), with
the simulator's clock running but the keep-alive either not pumped (`rt.wait`, what the code does) or pumped (`co.wait`, what the fix does).

| variant | accepting top-ups | outcome | stations at the end | claw |
|---|---|---|---|---|
| not pumped | 1 (t = 116 s, VISUAL_INITIALIZATION) | **FAULT / RECOVERY_REQUIRED**: "motion not ready: telemetry stale" on A-D at the next move | all four **State FAULT, Fault.LEASE (4)**, latched | suspended (`claw_supported` False) |
| pumped | 4 (t = 116, 123, 132, 136 s) | **READY** (LOCAL_ONLY, probe off, predicted length sigma 5.3 mm) | all IDLE, no fault | -- |

So on a machine whose lease is the sim value, the stall costs the whole startup at the first top-up and leaves the claw hanging on four
held (torque-kept) stations that need `acknowledge` and a recovery; pumping removes it completely.

**Minimal fix (recommended; not applied).**
1. `roomcleaner/cdpr/startup.py:838`, in `StartupSequencer._survey_topup`: replace `out = sv.flush()` by `out = self._pumped(sv.flush)`, with a
   small helper on `StartupSequencer` (or `RobotContext`): submit `fn` to a one-worker `concurrent.futures.ThreadPoolExecutor`, then
   `while not fut.done(): self.ctx.wait(0.02)` (the 20 ms keep-alive grid), and return `fut.result()` (re-raises). The worker touches only the
   survey and the layout; the command thread only pumps. The `claw-frames` thread already reads the same layout (L7). This is 8 lines and
   covers both bundle adjustments, the PnP solves and the `fsync`. Checked (`bench_thread.py`, 60-frame flush, 9 sheets): flush in a worker
   thread takes 2.3-2.5 s wall while the main thread's 20 ms loop keeps running with a **maximum gap of 25-28 ms** (GIL contention is not an
   issue: numpy/scipy release it), against 2.3-2.5 s unpumped.
2. Use the same helper at the existing `ctx.cal.fit(` sites (`startup.py` 748, 1052, 1143, 1164, 1169, 1348): they are the larger stall.
3. As a complement, not a substitute: `vision/board.py:909`, `least_squares(..., max_nfev=40, ftol=xtol=gtol=1e-10)` -> loosen to ~1e-8 or
   cap the top-up at `max_nfev` 8. Measured (`bench_cap.py`, `bench_flush60.py`): identical sheets and errors (0.18 mm) at caps 3-40; a 60-frame
   flush drops from 2.3-2.4 s to 1.0-1.4 s CPU, still 3-4x the lease, so the cap alone is not enough.
Rejected: "pump inside the survey loop" can only pump between PnP solves, not inside `scipy.optimize.least_squares`, and would need `flush`
restructured into slices; "cap iterations" alone leaves ~1 s.
Also: set `faults.lease_s` for the real machine only after the longest unpumped host stall is known, and document it next to the value.

## 4. "With `slack_probe` off most simulated startups are rejected, and this predates the follow-ups"

**Verified.** Scratch copy of `180b015` (`git archive`, working tree untouched), `fast_cfg(startup.slack_probe=False, marker.edge_m=0.150)`,
the nominal 9-sheet study board (`FloorBoard.nominal`), seeds 0-9 (`run_study_tree.py`):

| seed | probe off: outcome | trust | reason / witness | worst true L0 error / predicted abs. sigma (mm) |
|---|---|---|---|---|
| 0 | READY | LOCAL_ONLY | predicted length sigma 5.2 mm > 5.0; "probe off: sigma not honest" | 37.7 / 15.9 (2.4 sigma) |
| 1 | **rejected** | -- | witness 6.9x predicted variance | -- |
| 2 | **rejected** | -- | witness 12.3x | -- |
| 3 | **rejected** | -- | 3 outlier readings | -- |
| 4 | READY | LOCAL_ONLY | 6.2 mm > 5.0; not honest | **52.8 / 17.3 (3.05 sigma)** |
| 5 | READY | LOCAL_ONLY | 5.5 mm > 5.0; not honest | 17.1 / 16.2 (1.05 sigma) |
| 6 | **rejected** | -- | ambiguous alignment (alternate optimum) | -- |
| 7 | **rejected** | -- | witness 5.7x | -- |
| 8 | **rejected** | -- | witness 6.5x + 1 outlier | -- |
| 9 | READY | LOCAL_ONLY | not honest | 28.9 / 14.8 (1.95 sigma) |

**6 of 10 rejected at calibration, 4 of 10 READY, none VERIFIED** (every READY says the sigma is not honest). The claim is correct, and the
code before the follow-ups already behaves this way. The implementer's seeds 1, 2, 3, 6 and the READY seeds agree with mine.

The four rejected seeds (1, 2, 3, 6) and, for the timing, READY seed 5, with `slack_probe = True` on the same tree (`run_study_tree.py ... probe`):

| seed | probe on: outcome | trust | predicted length sigma | worst true L0 error / abs. sigma (mm) | simulated startup time |
|---|---|---|---|---|---|
| 1 | READY | **VERIFIED** | -- | 19.1 / 13.5 (1.4 sigma) | -- |
| 2 | READY | LOCAL_ONLY | 5.7 mm | 8.3 / 14.1 (0.6 sigma) | -- |
| 3 | READY | LOCAL_ONLY | 5.6 mm | 11.3 / 16.2 (0.7 sigma) | 1565 s |
| 5 | READY | LOCAL_ONLY | 5.6 mm | 12.8 / 16.4 (0.8 sigma) | 1564 s (probe off, same seed: **316 s**) |
| 6 | READY | LOCAL_ONLY | 6.2 mm | 15.7 / 14.2 (1.1 sigma) | 1616 s |

The probe rescues **4 of 4** rejected seeds and every true error is within 1.4 sigma (probe off: up to 3.05); but only seed 1 reaches
VERIFIED (the predicted length sigma stays above the 5.0 mm gate in the others). Added time on the matched seed 5: **+1,248 s (21 min)**,
simulated clock, against the write-up's +1,480 s (38 poses; mine is within 16 %). Total startup about 26 min instead of 5 min.

**Does the follow-up change this?** No. HEAD, same script, seeds 1, 2, 3, 7 (study board, no layout file, i.e. the old single code path): **6.9x, 12.3x,
3 outliers, 5.7x** rejections, identical to `180b015`. The follow-ups leave the 60 % rejection rate untouched; the survey runs (implementer,
seeds 0-6) show the same pattern with a surveyed layout.

**Recommendation on the default (not changed): keep `startup.slack_probe = false` for now; make flipping it a gated decision.**
* Case for true: D26 requires the probe for an honest sigma and for VERIFIED. With it off the best outcome is LOCAL_ONLY (enforced: every
  READY above carries "slack probe was off: the predicted sigma is not honest", and
  `test_margin_trust.py::test_without_the_probe_the_robot_stays_local_only` passes), 6 of 10 simulated startups are rejected, and READY runs
  include errors at 2.4 and 3.05 sigma. With the probe: 5 of 5 READY (it rescued 4 of 4 rejected seeds) and every error <= 1.4 sigma.
* Case against, today: (1) `verification/slack_probe_review.md` said the probe stays opt-in until **H1** (no tension bound on any probe
  motion; High before hardware) and **M2** (slack sigma under-reported 1.4-2.2x with white noise) are fixed; neither is (no tension code in
  the probe path of `startup.py`, no change since); (2) it is simulation-only (linear cables, no friction or stiction); (3) cost +1,248 s
  measured on a matched seed (+1,480 s in the write-up): a 26-minute startup instead of 5 minutes at every cold start (D25: no automatic resume);
  (4) it buys VERIFIED in only 1 of 5 probe-on runs (the other four stay LOCAL_ONLY at a predicted sigma of 5.6-6.2 mm against the 5.0 mm gate),
  so the cost is mostly paid for acceptance and honest error bars, not for the larger workspace; (5) default-off is fail-safe (an availability
  loss, not a safety loss), and the follow-up's top-up stall (H1 above) is a second reason not to lengthen the suspended phase on hardware yet.
* So: keep the hardware default `false`; close probe-review H1/M2 and the keep-alive stall (this review's H1); validate the probe on the restrained
  bench (ladder steps 5-6); then decide on a measured hardware startup time. Option for the lead (not implemented): when the cheap probe-off
  calibration is rejected for witness/outliers/ambiguity, offer a retry with the probe on instead of ending in RECOVERY_REQUIRED, so the 21
  extra minutes are paid only in the roughly 60 % of cases that need them. Study and test profiles keep their explicit `slack_probe` overrides.

## 5. Tests run

| file | result |
|---|---|
| `tests/cdpr/test_board_followups.py` | 44 passed (139 s) |
| `tests/cdpr/test_board_attitude.py`, `test_slack_probe.py`, `test_margin_trust.py` | 50 passed (753 s) |
| `tests/cdpr/test_board_followups_review.py` (new, reviewer-owned) | 16 passed (15 s) |

I did not re-run the full 328-test suite.

## 6. What I could not or did not check

* Real-camera corner noise, glare, curl, carpet, a real claw's tipping vs sliding (the rocking plant is a quasi-static model), the real host
  CPU and the real `lease_s`. All timings are this sandbox's.
* `Calibrator.fit` timings come from one probe-on run under CPU contention (5 calls); the order of magnitude, not the number, is the finding.
* No existing default changed: every numeric default of `calibration`, `startup`, `tasks`, `claw`, `camera` in both profiles equals `180b015`
  (`test_no_existing_default_changed...`; the diff is exactly `board_survey`, `board_survey_frames`, `rocking_tilt_k`, `rocking_tilt_min_rad`,
  `rocking_yaw_coupling`). `perception.py` / `vision/*` changes are additions of `dets`, `tilt_change`, `last_still_frames` only.

## 7. Reproduce

```
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr/test_board_followups_review.py            # 15 s
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr/test_board_followups.py                  # 2.3 min
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr/test_board_attitude.py tests/cdpr/test_slack_probe.py tests/cdpr/test_margin_trust.py   # 12.5 min
git archive 180b015 | tar -x -C <scratch>; OMP_NUM_THREADS=1 /usr/bin/python3 -I run_study_tree.py <scratch> <seed> noprobe|probe   # ~2.5 / ~10 min
```
