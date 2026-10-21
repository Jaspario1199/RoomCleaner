# Board follow-ups: config ranges, rocking check, board survey at startup (re-review round 2, conditions R2.2b / R2.2e / R2.5)

Implementer: Sonnet 5.5 agent, 2026-10-21. Independent verification pending. **All numbers are simulation numbers**; the real corner noise,
glare, curl, the real floor and a real claw's tipping behaviour are unmeasured. Inputs: `verification/imu_removal_review.md` (round 2: R2, R4,
R6), `verification/board_attitude_results.md`. Not touched: CAD, any acceptance threshold (`length_sigma_max_m`, witness / norm / bearing /
still-spread / probe / `max_lateral_drift` limits, `k_sigma`), reviewer-owned tests (`test_*_review.py`: all three files still pass, none went
stale). Nothing committed by this task (note: sibling sessions committed the working tree while this ran, `077c0e7`, `52b5d4f`, `bc2964e`
contain this task's files; those commits were not made by this task).

## 0. Result in six lines

* **Config (R4)**: every new key has a physical range with a stated reason (`config.ATTITUDE_BOUNDS`, 13 keys), and `marker.board_layout_file` must be
  `null` or an existing, parseable layout file. `pose_cov_inflate` 0.05, `grip_period_margin` 0.05, a nonexistent layout path and the integer 5 are refused
  with a message that says why.
* **Rocking (R2)**: with >= 2 floor tags the tilt change is watched in the take-up (it is the onset; the pull stops) and the pretension (abort "claw rocking on its
  jaws while tensioning"); with one tag nothing can be seen, the old behaviour stays and the log and the report say so. New simulator option `World(rock=...)`.
* **Survey (R6)**: SELF_CHECK now runs `BoardSurvey` for the sheets the resting claw sees, and every suspended still window feeds a top-up that surveys the others
  as the claw rises. With 9 sheets laid out sloppily (+-15 mm, +-0.1 rad) all nine are known by the end of calibration (<= 0.15 mm error) and the startup is as good as with the
  layout known in advance (section 3). The printed instructions and `tools/print_floor_board.py` now say what it does and what it does not do.
* **Pre-existing and unchanged**: with `startup.slack_probe` off (the shipped default) most simulated startups are rejected at calibration, with the layout known
  in advance or surveyed alike (section 3.4); the code before this change gives the identical results for the study board.
* **No numeric acceptance threshold was relaxed or changed**; the probe-on study numbers with the known board reproduce the previous report to the digit (16.1 / 13.5 / 14.1 mm).
* Full suite `OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr tests/firmware`: see section 5.

## 1. Configuration ranges (R4)

`roomcleaner/cdpr/config.py`: `ATTITUDE_BOUNDS = {key: (low, high, unit, reason)}`, applied in `load_config` AFTER the old checks (their messages are unchanged), and the
error repeats the reason: `camera.pose_cov_inflate = 0.05 is outside the physically sensible range [1, 5] x: margin on the Cramer-Rao standard deviation ...`.

| key | range | why (short; the full reason is in the table and the error) |
|---|---|---|
| `camera.corner_sigma_px` | 0.05 .. 2 px | cv2 sub-pixel refinement alone is biased ~0.15 px on a 50 px tag; every covariance scales with its square; 2 px is the detector's own reprojection limit |
| `camera.pose_cov_inflate` | 1 .. 5 | a margin on the Cramer-Rao std: below 1 claims better than the bound (0.05 = 400x smaller covariance); above 5 throws information away |
| `claw.vision_attitude_floor_rad` | 0.2 .. 20 mrad (and <= `vision_attitude_sigma_rad`) | 0.1 mm of paper curl over a 150 mm tag is 0.7 mrad; 20 mrad is twice the constant sigma it replaced |
| `tasks.grip_period_margin` | 1.2 .. 3 | compound pendulum T = 2 pi sqrt((k^2+L^2)/(gL)) is 1.2x the simple period (k = 0.13 m, L = 0.196 m, review F8c); 0.05 collapsed the dwell to its floor; 3x needs k = 0.55 m |
| `tasks.grip_still_rate_rad_s` | 0.005 .. 0.1 rad/s | still-claw rate noise 8e-3 rad/s per corner (4e-3 over a tag): under 0.005 never opens; 0.1 = 17 mrad swing, a fifth of the 5 deg limit |
| `tasks.grip_still_frames` | 3 .. 30 pairs | the quiet window must span a quarter period (0.27 s) to contain moving frames; 30 pairs = 3 s |
| `tasks.grip_settle_periods` | 3 .. 20 | the review judged 3.8 periods too short; 20 x loaded 1.25 s = 31 s |
| `tasks.grip_settle_min_s` | 1 .. 10 s | at least one full period; above the 7.8 s loaded dwell the arithmetic means nothing |
| `tasks.grip_settle_timeout_s` | 10 .. 120 s | unloaded dwell 5.6 s, loaded release 7.8 s |
| (cross-check) | periods x margin x 1.5 s <= timeout | a loaded release could never be approved |
| `startup.board_survey_frames` | 10 .. 200 | a sheet needs >= 8 views; 200 frames = 20 s |
| `startup.rocking_tilt_k` | 3 .. 10 sigma | exp(-k^2/2): 1e-2 at 3, 4e-6 at 5 |
| `startup.rocking_tilt_min_rad` | 1 .. 20 mrad | 1 mrad = systematic floor; 20 mrad = 10 mm of origin motion |
| `startup.rocking_yaw_coupling` | 0 .. 0.5 | simulator ~0.03-0.04 tilt per rad of yaw |
| `marker.board_layout_file` | `null` or an existing file | a string; a file that exists and is a floor-board layout JSON (version 1, tags, `edge_m` 0.02-0.5 m, `origin_id` among the tags); relative paths from the working directory, as the service opens them; the message says how to create the starting file |

The ranges exclude values that no camera, pendulum or print can have; they are not product thresholds. Shipped defaults and both profiles sit inside them
(tested). Tests (`test_board_followups.py`): each of the 13 keys refused below / above / NaN / inf / bool / string / None and accepted at both edges (with its
cross-check companions); the review's examples with their messages; layout file: missing, directory, not JSON, no tags, wrong version, absurd edge, origin not among the tags,
list, string edge, 0 / integer 5 / empty / list / bool; the layout version constant equals `FloorBoardLayout.VERSION`; dwell vs timeout; floor vs sigma.

## 2. Rocking check (R2.2b)

**Problem.** `floor_displacement` uses the reference tilt, so a claw that tips about a jaw edge reads (almost) nothing: for 15 mrad about a jaw edge 40 mm from the body axis the origin
moves 7.8 mm, `floor_displacement` reads 0.5-1 mm (tilt x distance pivot-to-tag-centroid; the reviewer's "exactly zero" holds only if the pivot is the anchor), `cam_displacement` 7.8 mm,
`tilt_change` 15 mrad (tested with noise-free frames).

**Change.**
* `perception.tilt_change(o, ref)`: relative rotation of the two detector poses minus the turn about the claw's own z axis (a take-up yaws the claw); returns the tilt vector,
  the per-axis noise variance of the frame and of the reference from their own covariances (systematic floor excluded), and the yaw.
* `startup.RockWatch`: with >= 2 tags in the reference AND in the frame, the mean of the last 3 frames must exceed
  `max(startup.rocking_tilt_min_rad (4 mrad), startup.rocking_tilt_k (5) x sigma) + startup.rocking_yaw_coupling (0.08) x |yaw change|`, sigma = sqrt(frame variance / 3 + reference variance + (1 mrad)^2).
  A frame with one tag restarts the window. One tag in the reference: `can_see` is False, `update` is always False.
* Take-up (`slack_takeup`): rocking counts as the taut onset and stops the pull at once (the claw is tipping); the slide direction then comes from the general `cam_displacement`
  (measured tilt, 5-sigma rule) instead of `floor_displacement`; the log says "the claw ROCKED x mrad on its jaws". Pretension (`_pretension_watch`, `initial_lift`): abort "claw rocking on its jaws while tensioning (x mrad tilt change > y mrad)".
* One tag: previous behaviour; log (once) "N floor tag in view (station A take-up): a claw rocking on its jaws cannot be seen (tilt noise of one tag ~13 mrad per frame); ...", `measurements["rocking_check"] = "blind: ..."`,
  `rocking_blind_at`. With a board: `rocking_check = "active"`, `rocking_<sid>_max_tilt_rad` per station.
* Simulator (`sim/world.py`): `World(rock={"half_width_m": 0.04, "max_rad": 0.12, "slide": True})`, i.e. `SimRobot(world_kw={"rock": {...}})`. The resting claw tips about the jaw edge on the side of the pull until the cable moment
  balances gravity (found by bisection on the angle with the plant's own force model; friction and lift judged at the rocked pose; `slide: False` isolates rocking; `tipped` event and `rock_max_rad` for studies).
  Measured: 2.8 mrad per mm of take-up, cable tension capped at the tipping moment (0.58-0.69 N for 0.6 kg; sliding friction is 2.4 N), i.e. the claw tips INSTEAD of sliding, as the review argued.

**Evidence** (seed 4, `fast_cfg`, pure rocking):

| case | outcome |
|---|---|
| board, rock | all four take-ups stop at the tilt onset: tilt change 10.2 / 11.5 / 11.1 / 10.1 mrad against a threshold of 9.9-10.0 mrad (about 5 mm of body-origin motion), plant maximum 15.8 mrad, no tipping, slide-direction RMS 0.71 sigma (limit 3), 4 onsets |
| one tag, same plant | watch inert; log says so once; nothing stops the take-up at the onset, the claw tips to the 120 mrad limit (`tipped`) and the old slide-direction check aborts (RMS 3.4 sigma). Without rock the same seed completes (RMS 0.10) |
| false alarms, board, no rock, seeds 0-3 | 1721 watch evaluations in 4 take-ups: largest tilt change / threshold 0.39 / 0.54 / 0.53 / 0.60, zero trips |
| study numbers | the six probe-on startups of section 3.2 reproduce the previous report exactly (no change from the new watch) |

Unit tests: `RockWatch` never trips in 300 frames of an unmoved claw (statistic < half the threshold), trips within 3 frames of a 15 mrad tip and reports 15 +- 2.5 mrad, ignores 4 mrad,
ignores a one-frame 4.5-sigma outlier, ignores a take-up yaw of 0.15 rad with 6 mrad of coupled tilt but not 30 mrad, its threshold equals the stated rule and grows with the corner noise, one tag is inert even for 40 mrad;
the pretension watch aborts for rocking (not "dragged"), for a 20 mm drag it still says "dragged", one tag blind.

**Limits.** The rocking physics is a quasi-static model with a circular 40 mm footprint, the pivot and axis fixed by the flat-pose pull direction, and assumed mass / CoM / half-width; whether the real claw tips before it slides on the real
floor is **unverified** (the reviewer's condition "hardware check of the take-up" stands). The thresholds come from the simulated tilt noise (1-2.6 mrad for 3-4 tags; real corner noise unmeasured) and the 0.08 yaw coupling from the simulated rigid body. The pretension never rocked in the simulator
(symmetric pull), so that path is covered by the unit test only. With one tag a rocking claw is still only caught by the old guards (here: after tipping).

## 3. Board survey at startup (R6)

**Reality check first.** `BoardSurvey` needs frames in which a camera pose from already surveyed tags exists and >= 8 views of each new tag; the resting claw sees sheet 0 and 2-3 neighbours (camera ~0.52 m up: the view is about 0.79 x 0.60 m, so with the 150 mm tags and a 4 px border the corner sheets, 0.25 m off the axis in both directions, are outside it), so a survey at SELF_CHECK alone leaves 5-6 sheets unknown for the whole startup.
That would make the printed promise false for most sheets and, as measured below, degrades the startup. So the survey has two stages (`roomcleaner/cdpr/board_startup.py`):

1. **SELF_CHECK** (`StartupSequencer._survey_board`, before the mount offset): after a stillness check, `startup.board_survey_frames` (30) frames of the resting claw -> `BoardSurvey` (`finalize()`: accept, bundle-adjust). Sheets surveyed earlier that are in view are checked: the detector / bundle adjustment flag one that moved (tested 3-80 mm); it is cleared and surveyed afresh in the same startup
   (a moved origin sheet clears all the others); smaller errors are refined away. The layout file is rewritten atomically only for a real change (sheet added/cleared, > 1 mm), the previous contents kept as `<file>.bak`; an unwritable file is reported, not fatal.
2. **Top-up while suspended**: every suspended still window offers its frames (`VisionSource.last_still_frames`, thinned to >= 0.3 s apart, <= 60 pending) that show a sheet not yet surveyed (`offer`); each calibration sample flushes them (`_survey_topup`, claw hanging still): accepted tags update the file, `ctx.floor_board` (the excitation design) and the report. Nothing is moved for the survey.

Wiring: `PoseObs.dets` / `MarkerObservation.dets` (all raw detections of a frame, set by `BoardDetector`), `RobotContext.board_survey`, `service.attach_board_survey` (hardware: when a layout file is configured and `startup.board_survey`), `service.build_marker_detector` (an unsurveyed template adopts the measured `marker.edge_m`; a surveyed layout at another tag size is refused,
SELF_CHECK also aborts: the tags are the only ruler, +-0.5 %). `SimRobot(board_truth=<true layout>, board_start=..., board_path=...)` images the TRUE layout through the real `BoardDetector` over the live layout (`SimCamera(board_detector, board_truth)`), so what the estimator knows is exactly what was surveyed.
The report: `measurements["board_survey"] = {ran, expected, surveyed_ids, newly_surveyed, cleared, unsurveyed {id: reason}, frames, max_sigma_xy_m, warnings, saved, topups[]}`.

### 3.1 Accuracy of the survey

SELF_CHECK, seed 4: sheets 4 and 8 surveyed from 30 frames, 0.07 / 0.13 mm position error, 0.02 deg yaw, sigma 0.07 mm. Synthetic still view (unit test): all visible sheets < 1 mm and < 0.2 deg. Top-up, in the simulated startups: all nine sheets, sigma <= 0.15 mm, final error <= 0.15 mm.

### 3.2 Full startups, probe on (`scripts/sim_board_survey_study.py`, seeds 0-2, 150 mm tags, jittered layout +-15 mm / +-0.1 rad, 0.3 px)

| layout | seed | outcome | trust | predicted length sigma (the 5 mm criterion) | absolute sigma max (mm) | worst true L0 error (mm) | sheets known at the end |
|---|---|---|---|---|---|---|---|
| known in advance (the "3i" case, previous report) | 0 | READY | LOCAL_ONLY | 5.0 | 16.1 | 17.2 | 9 (given) |
| | 1 | READY | VERIFIED | | 13.5 | 19.1 | 9 |
| | 2 | READY | LOCAL_ONLY | 5.7 | 14.1 | 8.3 | 9 |
| survey at SELF_CHECK only (no top-up) | 0 | READY | LOCAL_ONLY | 10.9 | 21.9 | **71.3 (3.3 sigma)** | 2 |
| | 1 | READY | LOCAL_ONLY | 6.8 | 18.2 | 11.7 | 3 |
| | 2 | READY | LOCAL_ONLY | 7.8 | 21.8 | 20.6 | 3 |
| **survey + top-up (as shipped)** | 0 | READY | LOCAL_ONLY | 5.3 | 16.4 | 12.3 | 9 (top-ups at t = 144, 178, 352 s) |
| | 1 | READY | VERIFIED | | 12.4 | 20.6 | 9 |
| | 2 | READY | LOCAL_ONLY | 5.9 | 16.7 | 6.2 | 9 |

The top-up is what makes the survey equivalent to knowing the layout: with the resting-claw survey alone the outer sheets are missing in flight and the startup is clearly worse (one seed 3.3 sigma off). No "ROCKED" event in any of these runs; no tag was cleared.

### 3.3 Probe off (the shipped default, `... survey 0 noprobe`, seeds 0-6)

| layout | READY | rejected at calibration |
|---|---|---|
| known in advance (study board) | seeds 0, 4, 5 (LOCAL_ONLY, 15.9-17.3 mm) | 1, 2, 3, 6 (witness 6.9x / 12.3x, 3 outliers, ambiguous alignment) |
| surveyed (as shipped) | seeds 0, 5 (16.0, 16.2 mm) | 1, 2, 3, 4, 6 (witness 5.0-16x, outliers, ambiguous) |

With the slack probe off most simulated startups are rejected by the calibration (the report says so: "slack probe was off: the predicted sigma is not honest"); this is the same with the layout known in advance, and the
code **before this change** (commit `180b015`, `git archive`, same script) gives the identical outcomes for study seeds 1, 2, 3, 4, 6 (6.9x, 12.3x, 3 outliers, READY 17.3 / 52.8 mm, ambiguous). The survey does not change the pattern (2 of 7 vs 3 of 7 READY, n = 7 each, different noise streams).
In the survey runs the top-ups complete within the first calibration samples (t = 105-133 s) because every sample offers a window.

### 3.4 Tests

Synthetic still view of a jittered layout: sheets in view surveyed to < 1 mm / 0.2 deg, saved, `.bak` kept, JSON-friendly report, the unseen listed with reasons; a second survey of the same view writes nothing; a sheet kicked by 3, 6, 12, 30, 80 mm (and up to 17 deg) between startups ends within 1 mm of where it is
(>= 6 mm: cleared and re-surveyed, message logged); tag-size mismatch refused, a template adopts the measured size; unwritable file not fatal; no usable frames -> nothing surveyed; service adoption / refusal / `attach_board_survey` (on, off, no layout);
top-up: unit (offers kept thinned and capped, outer sheets accepted from four poses, file and report updated) and on the simulated robot (`_survey_topup` after still windows); SELF_CHECK on the simulated robot (survey first, then the floor pose and mount offset on the board: 3 tags, attitude sigma 1 mrad; design refreshed; layout file equals the layout; error < 1 mm);
no layout / `board_survey = false`: nothing surveyed, report says so; layout at another tag size: SELF_CHECK aborts.

### 3.5 Printed instructions

`tools/print_floor_board.py` (module text, layout page, `--layout-json PATH [--no-pdf]` writes the starting layout, `write_layout_template`) and `prints/floor_board_letter.pdf` + `-01.png` regenerated (only page 1 changes; the tag pages and the 450 mm printout are byte-identical). Page 1 now says: the robot SURVEYS the layout itself during startup
(from the resting claw the sheets its camera sees, the rest while the claw hangs and calibrates); a sheet never seen clearly is NOT surveyed and NOT used; set `marker.board_layout_file` to an existing layout (how to make it), the robot rewrites it and keeps `<file>.bak`; set `marker.edge_m`; do not move a sheet during a run
(nothing re-surveys it until the next startup; between startups a sheet in view that moved by more than a few mm is found and surveyed again). The old sentence ("the robot surveys the layout itself") and "run the survey again" (there is no such tool) are gone; a test pins the new text in the built and the shipped PDF.

## 4. Limits and open items

* Simulation only; the survey, the thresholds of the rocking check and the real corner noise (`camera.corner_sigma_px` must be measured) are untested on real frames. Glare, curled sheets, carpet, a bumped sheet during a run are not simulated.
* **Hardware time**: a top-up flush costs ~1 s (bundle adjustment) while the claw hangs; the keep-alive is not pumped in that time (the stations hold on their own lease; the existing calibration fits block similarly). Measure it against `faults.lease_s` before the first suspended run; `startup.board_survey = false` switches the survey off.
* A sheet that is never seen clearly stays unsurveyed and unused. A sheet that moves during a run is not re-surveyed until the next startup (the detector's per-frame consistency check can drop it, >= 3 tags).
* One tag (no layout file): rocking cannot be seen; startup is the degraded fallback (tilt 13 mrad per frame). The shipped `config/robot.sim.json` / `robot.example.json` still have `board_layout_file = null`; R5 (announce the board as the validated reference or require a layout for hardware) is **documented** in `docs/CONTROL_SYSTEM_V1.md` 3.2, not enforced.
* Rocking physics is a model; the hardware take-up check of the review stands. The pretension rocking path is covered by a unit test only.
* Not done (outside this task): R1 (grip gate vs statics tilt over 81 % of the room, needs a decision), R7, R8.

## 5. Tests

`tests/cdpr/test_board_followups.py` (new): see sections 1-3. Existing tests edited: `test_board_attitude.py::test_service_builds_the_board_detector_only_when_a_layout_is_configured` builds its layout at the configured `marker.edge_m` (the new edge check; the test is implementer-owned).
Reviewer-owned `test_imu_removal_review.py`, `test_multi_attachment_review.py`, `test_slack_probe_review.py`: pass unchanged, none stale.

**Full suite** `OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr tests/firmware`: **328 passed, 0 failed** in 28 min 6 s (4 cores shared with the studies above; the previous report: 278 passed + 4 stale reviewer assertions that the reviewer has since flipped; this task adds 44 tests in `test_board_followups.py`, 4 of them full simulated take-ups of 30-40 s).
`test_board_followups.py` alone: 44 tests, about 4 min.

## 6. Reproduce

```
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr/test_board_followups.py        # about 4 min
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr tests/firmware                   # about 25 min
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/sim_board_survey_study.py survey 0               # 8-10 min per seed; also: study 0, survey 0 noprobe
OMP_NUM_THREADS=1 /usr/bin/python3 -m tools.print_floor_board --out prints/floor_board_letter.pdf --png-dpi 100
OMP_NUM_THREADS=1 /usr/bin/python3 -m tools.print_floor_board --layout-json data/floor_board.json --no-pdf
```
