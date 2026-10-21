# Vision-only attitude with the printed floor board: implementation and floor-reference study (D27 follow-up)

Implementer: Sonnet 5.5 agent, 2026-10-21. Independent verification pending. **All numbers are simulation numbers**; the real
corner noise, its frame-to-frame correlation, lens distortion, IPPE face-on flips and printed-sheet flatness are unmeasured.
Inputs: `verification/imu_removal_review.md` (F1-F11, section 6 "minimal change set"), `verification/imu_removal_results.md`.
Not touched: CAD, `claw_body_frame.json`, the four-point kinematics, the tension distribution, any acceptance threshold
(`length_sigma_max_m`, witness RMS, `k_sigma`, `still_spread_max_m`, probe thresholds, ...). Nothing committed.

## 0. Result in six lines

* Probing is back: **91-97 % of the probe readings resolved** (D27 vision-only: 20-25 %, IMU on: 68-75 %), because the probe, the
  take-up and the drag-watch now work on camera-frame displacements (noise 0.1-1 mm per frame) instead of absolute poses (7-15 mm).
* **All six startups complete at 0.3 px** (3c old layout and 3i printed 0.25 m layout, seeds 0-2; D27: 2 of 3); three end **VERIFIED by margin** (3c seeds 0, 1; 3i seed 1),
  the other three miss only the unchanged 5 mm predicted-length-sigma criterion (5.0 / 5.1 / 5.7 mm; D27: 8.8-9.1 mm, review runs 6.6-7.6 mm).
* Predicted absolute sigma 12.0-16.1 mm (D27 vision only 19.4-21.0 mm, IMU on 15.6-16.2 mm); the worst true error was **1.4 sigma** (D27: 3.5 sigma, IMU on 1.7).
* At **0.5 px** (estimator told 0.5) the printed layout still completes 3 of 3 (VERIFIED 1 of 3, worst error 2.3 sigma); the old layout 2 of 3: one seed faults in the pretension
  (claw dragged 11.0 mm against the unchanged 10 mm limit; at 0.3 px the same seed drags 9.7 mm: the old layout's single-tag floor view is marginal). With the plant at 0.5 px and the estimator
  told 0.3 px the printed layout completes 2 of 3 (the third is rejected: witness errors 4.4x their predicted variance, i.e. the mis-told noise shows up as an honest rejection).
* One tag is still poor for the ABSOLUTE pose (13 mrad per frame at the 0.5 m rest height, 18 mrad at 0.6 m); only the displacement measurements are
  fixed by this change. Documented by a test (`test_single_tag_probe_limitation_is_documented`).
* Full suite `pytest -q tests/cdpr tests/firmware`: **278 passed, 4 failed** in 22 min; the 4 failures are reviewer-owned assertions (`test_imu_removal_review.py`) that document
  findings that were fixed here (section 5). They cannot be edited by this task.

## 1. What was implemented (review item -> change)

| Item | Change | Files |
|---|---|---|
| 1 single-tag detector (F1, F4, F9) | LM refinement (`cv2.solvePnPRefineLM`) of every IPPE candidate; when both candidates converge to one pose there is one ML solution (reason "unambiguous"), a real flip keeps its own pose and the prior rules decide. Every accepted frame carries a **6x6 pose covariance** = Cramer-Rao bound of the corner reprojection Jacobian for the corners actually used (range, tag size, focal length, corner noise `camera.corner_sigma_px` 0.3 px, x `camera.pose_cov_inflate` 1.3, number of tags), reproducing the review's Monte Carlo (one tag 0.52 m: 13.4 vs 13.5 mrad; nine tags 1.0 m: 0.61 vs 0.61 mrad). `claw_cov_from_pose` propagates it to the claw through the true marker-to-claw lever: **anisotropic** (z 3-5x smaller than x, y; correlated with the position as the physics is). The double-counted `(sigma*0.09 m)^2` term is gone from `claw_position_cov`; a frame without a covariance (legacy) gets the single `(sigma*\|p\|)^2` lever. `claw.vision_attitude_sigma_rad` (10 mrad) is now only the fallback for such frames, `claw.vision_attitude_floor_rad` (1 mrad) the least sigma added to a frame's own. The calibration's attachment-lever length noise uses max(`calibration.attitude_sigma_rad`, the pose's own sigma). | `vision/marker.py`, `vision/board.py`, `perception.py`, `calibration.py`, `config.py` |
| 2 layout | `DEFAULT_PITCH_M = 0.25` (max 0.28, enforced) in `FloorBoardLayout.nominal(...)`, `FloorBoard.nominal(...)` and `tools/print_floor_board.py` (`--pitch-mm`); layout page rewritten: 250 mm centre to centre, Letter sheets overlap by ~29 mm along the page height, "overlap only the blank paper margins, NEVER cover any part of a tag or its white border"; `prints/floor_board_letter.pdf` regenerated (verified by the tool's own check), the 450 mm version kept as `prints/floor_board_letter_450mm.pdf` (+ PNGs). | `vision/board.py`, `sim/world.py`, `tools/print_floor_board.py`, `prints/` |
| 3 startup uses the board | `marker.board_layout_file` -> `service.build_marker_detector` builds the `BoardDetector` (>= 2 usable tags: joint pose; one: single-tag pose with its own covariance) and `RobotContext.floor_board` (`BoardGeometry`) so the excitation design sees the same tags and predicts the same covariance. Floor stage, mount-offset measurement and every suspended pose consume whichever the frame gave. The study / tests use the simulator's equivalent (`SimCamera(board=...)`). | `service.py`, `startup.py`, `vision/board.py`, `sim/harness.py` |
| 4 camera-frame displacement | `perception.cam_displacement`: displacement of the corner centroid in the camera frame relative to a reference captured at the start of each take-up / tension step / probe, one reference rotation (+ the frame's own turn about the claw's z axis, + a Gauss-Markov weight on the measured tilt change; a 5-sigma tilt change falls back to the frame's own rotation; for the resting claw of the floor stage `floor_displacement` uses the reference tilt only). Used by the take-up onset and slide direction, the **`DragWatch`** (mean of the last 3 frames against max(3 x onset, 10 mm, k sigma of the mean), replacing one frame against a fixed 10 mm), the per-pose probe (series, `sigma_proj`, round-2 re-probe), the recovery tauten and `still_pose`. Mid-probe, if the noise of the current measurement makes the onset unresolvable within `probe_overshoot_max_m`, the cable is paid back and skipped (never blind, never an abort on noise). | `perception.py`, `startup.py`, `supervisor.py` |
| 5 simulator | `SimCamera.noise_model = "tags"` (default): pose error drawn from the same Cramer-Rao covariance of the tags in view (corner noise `pixel_sigma`, estimator told `est_pixel_sigma`), frame carries its covariance; `"fixed"` = the previous iid 2 mrad regression mode (`camera_kw={"noise_model": "fixed"}`, study flag `--noise-model`). | `sim/world.py`, `sim/harness.py`, `scripts/sim_floor_reference_study.py` |
| 6 settle gate | dwell counted from the **last observed motion**; period x `tasks.grip_period_margin` 1.25 (compound pendulum); **loaded release** uses the loaded pendulum (payload `tasks.max_payload_kg` at the jaw tips: L 0.196 -> 0.39 m, dwell 5.6 -> 7.8 s) and always the full dwell, also when the camera reports stillness; `still_pose` judges the **raw camera-frame scatter** (a 30 mm swing is rejected at any covariance); the mount-offset check re-measures a **held-out set** of 30 frames against the corrected mount (limit max(4 sigma, 3 mrad)) and aborts "not reproducible". | `attitude.py`, `tasks.py`, `perception.py`, `startup.py`, `config.py` |
| 7 tests | see section 4 | `tests/cdpr/` |

## 2. What integration showed (and was fixed)

1. **A fixed reference rotation is not enough.** A cable take-up yaws the claw by 1.3 deg per 0.7 mm about its own (tilted) axis; read through one
   reference rotation that is a lateral shift of the whole claw (tens of mm at a 0.3 m lever) and aborted the probe ("claw moved 11-17 mm without a significant onset",
   RECOVERY_REQUIRED in the first board runs). `cam_displacement` therefore takes the frame's own turn about the body z axis, plus the tilt change weighted by its precision
   (the simulated claw tilts ~3.5 % of its yaw): residual error 0.2-0.9 mm for the board at any yaw up to 1.5 rad, 2-12 mm for one tag once the yaw exceeds ~6 deg (the tilt change is then not measurable; `test_camera_frame_displacement_is_not_fooled_by_the_claw_yawing`).
2. **The board loses tags while the claw moves** (2 tags at the reference, 1 later at 1.6 m height): the measurement noise rises 3x above what the reference promised.
   The probe now re-checks resolvability at every step and backs out (`test_view_that_gets_noisy_mid_probe_skips_the_cable_and_pays_the_retraction_back`).
3. **A noise spike must not read as motion.** One 0.5 px frame with a 15.8 mrad tilt outlier (3-sigma limit 13.7 mrad) triggered the "tilt really changed" fallback (absolute pose, 8 mm of
   lever error) and ended a take-up early (a false onset: that cable's L0 28-38 mm too short, then 14.7 mm of drag in the pretension, startup fault). The fallback threshold is now 5 sigma, and the floor stage (take-up, pretension) uses `floor_displacement`, which never uses the frame's tilt (a resting claw cannot tilt; also made the run with the estimator told 0.3 px instead of 0.5 survive that seed).
4. **LM makes the ambiguity rule see one pose**, not two near-equal candidates; `test_vision.py` bound is now max(3 deg, 2 x the frame's own reported rotation sigma).
5. **Fixtures**: with honest single-tag noise the lifecycle / garment / no-probe fixtures need the printed board (witness RMS 24.8 mm with one tag); they use `FloorBoard.nominal(0.15)`.
   The item positions of the task fixtures are now chosen from candidates whose predicted STATICS tilt at the grip pose is <= 4 deg and that lie in the scan footprint of the claw and the hamper
   (the cable model's floor tilt ranges 2-9 deg over the room; a fixed offset was refused for another noise stream: "grip not approved: statics tilt 5.5 deg > 5.0 deg", unrelated to this change).
6. **Calibration**: a pose's own attitude sigma enters the length noise (max with the configured 10 mrad). In the run before it was added the old-layout seed 0 (single tag at the floor) was rejected ("witness errors 4.1x their predicted variance"); it is accepted in the final runs (the effect of this change alone was not isolated).

## 3. Floor-reference study

Commands (simulation, `startup.slack_probe` on, seeds 0-2, `--no-whatif`; the "3i" case was added to `scripts/sim_floor_reference_study.py`; plant and estimator corner noise agree unless stated):

```
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/sim_floor_reference_study.py --suite main --only "3c,3i" --seeds 3 --probe --no-whatif --out board_px03.json
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/sim_floor_reference_study.py --suite main --only "3c,3i" --seeds 3 --probe --no-whatif --pix 0.5 --tag px0.5 --out board_px05.json
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/sim_floor_reference_study.py --suite main --only "3i" --seeds 3 --probe --no-whatif --pix 0.5 --est-pix 0.3 --tag plant0.5-est0.3 --out board_mismatch.json
```

"3c" = the case of the D27 report (board 3x3, pitch 0.42 m, 160 mm tags), the **unchanged** command asked for; "3i" = the printed layout (3x3, pitch 0.25 m, 150 mm tags, `DEFAULT_PITCH_M`).
"probed" = readings of the per-pose probe that resolved their cable's taut onset / all readings; "predicted sigma" = predicted absolute cable-length sigma, max over the four cables
(the quantity of the D26 rule); "worst true L0 error" is against the simulator's truth; "tags / sigma" = tags in view at the resting claw and the 1-sigma of its roll/pitch (mean of the 30 mount frames).

### Per seed

| layout | corner px | seed | startup complete | readings probed | predicted sigma, max over 4 cables (mm) | worst true L0 error (mm) | trust | floor stage: tags / attitude sigma (mrad) | if not complete |
|---|---|---|---|---|---|---|---|---|---|
| 3c old layout 3x3 p0.42, 160 mm tags | 0.3 | 0 | yes | 94 % | 13.5 | 17.5 | VERIFIED | 1 / 2.8 |  |
| 3c old layout 3x3 p0.42, 160 mm tags | 0.3 | 1 | yes | 96 % | 12.0 | 16.9 | VERIFIED | 1 / 2.8 |  |
| 3c old layout 3x3 p0.42, 160 mm tags | 0.3 | 2 | yes | 97 % | 14.4 | 11.8 | LOCAL_ONLY | 1 / 2.8 |  |
| 3c old layout 3x3 p0.42, 160 mm tags | 0.5 | 0 | yes | 93 % | 14.3 | 29.4 | LOCAL_ONLY | 1 / 4.6 |  |
| 3c old layout 3x3 p0.42, 160 mm tags | 0.5 | 1 | **no** | - | - | - | NONE | 1 / 4.6 | pretension: claw dragged while tensioning (0.011021674777370942) |
| 3c old layout 3x3 p0.42, 160 mm tags | 0.5 | 2 | yes | 96 % | 14.4 | 5.6 | LOCAL_ONLY | 1 / 4.6 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.3 | 0 | yes | 91 % | 16.1 | 17.2 | LOCAL_ONLY | 4 / 1.0 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.3 | 1 | yes | 95 % | 13.5 | 19.1 | VERIFIED | 3 / 1.0 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.3 | 2 | yes | 96 % | 14.1 | 8.3 | LOCAL_ONLY | 3 / 1.0 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.5 | 0 | yes | 94 % | 18.7 | 42.5 | LOCAL_ONLY | 4 / 1.0 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.5 | 1 | yes | 92 % | 15.3 | 11.3 | VERIFIED | 3 / 1.0 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.5 | 2 | yes | 93 % | 18.6 | 18.2 | LOCAL_ONLY | 3 / 1.0 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.5 (estimator told 0.3) | 0 | yes | 96 % | 16.2 | 25.4 | LOCAL_ONLY | 4 / 1.0 |  |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.5 (estimator told 0.3) | 1 | **no** | 95 % | 14.6 (refit of the rejected run) | 11.3 | NONE | 3 / 1.0 | calibration rejected: witness errors 4.4x their predicted variance; 1 outlier readings |
| 3i printed layout 3x3 p0.25, 150 mm tags | 0.5 (estimator told 0.3) | 2 | yes | 97 % | 13.9 | 26.6 | LOCAL_ONLY | 3 / 1.0 |  |

(Seeds are single runs; "VERIFIED" = by margin (D26) at this startup, "LOCAL_ONLY" rows missed only the predicted-length-sigma criterion unless a reason is given. Worst true error / predicted sigma over the seeds: 1.4 (0.3 px, both layouts),
2.1 (3c) and 2.3 (3i) at 0.5 px, 1.9 with the mis-told estimator.)

### Against the earlier numbers (same case 3c unless stated)

| run | startups complete | readings probed | predicted sigma (mm) | trust | source |
|---|---|---|---|---|---|
| D27 vision only (estimator 10 mrad, plant 2 mrad) | 2 / 3 | 20-25 % | 19.4-21.0 | LOCAL_ONLY, one none | `imu_removal_results.md` |
| same code, IMU on | 3 / 3 | 68-75 % | 15.6-16.2 | LOCAL_ONLY | `imu_removal_results.md` |
| review control F (estimator told the plant's 2 mrad), 3c | 3 / 3 | 80-84 % | 11.1-14.8 | VERIFIED 3 / 3 | `imu_removal_review.md` s.4 |
| review crb mode, printed pitch 0.25 (absolute-pose probe) | 3 / 3 | 70-76 % | 18.3-19.9 | LOCAL_ONLY | `imu_removal_review.md` s.4 |
| **this change, 3c, 0.3 px** | 3 / 3 | 94-97 % | 12.0-14.4 | VERIFIED 2 / 3 | here |
| **this change, 3i printed layout, 0.3 px** | 3 / 3 | 91-96 % | 13.5-16.1 | VERIFIED 1 / 3 | here |
| this change, 3i, 0.5 px | 3 / 3 | 92-94 % | 15.3-18.7 | VERIFIED 1 / 3 | here |

Reading: the old layout's floor view has ONE tag (2.8 mrad attitude sigma on the mean of 30 frames), the printed layout 3-4 (1.0 mrad = the floor). That is invisible in the probe now (camera-frame displacements) and
shows in the floor stage margin (drag 9.7-11 mm against 0.4-2 mm) and at 0.5 px. The absolute sigma is about the same for both layouts (13.5-16.1 against 12.0-14.4 mm; the review expected the
dense one to be worse because of its smaller span; not decomposed here, `--no-whatif`); the 5 mm work-volume criterion is missed by the printed layout in two seeds by 0.0-0.7 mm and by the old one in one seed by 0.1 mm.

## 4. Tests

`OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr tests/firmware` (about 22 min): **278 passed, 4 failed** in 22 min (the 4 are the reviewer-owned stale assertions of section 5; full output kept outside the repo)

* **New**: `tests/cdpr/test_board_attitude.py` (24 tests, 5 s): LM vs IPPE tilt noise through the detector; covariance against a cv2 Monte Carlo (one tag at two ranges, the board); scaling with range, tag size, focal length,
  corner noise and tag count; anisotropy; no double-counted lever (legacy frames); a frame's own covariance replaces the constant; board pose with >= 2 tags and single-tag fallback with a larger honest covariance;
  `service.build_marker_detector`; default pitch 0.25 / maximum 0.28 / >= 2 tags at the resting height (and one at 0.42 m); the print tool's text (250 mm, OVERLAP, margins, pitch limit) and the kept 450 mm printout;
  camera-frame displacement (tilt-lever noise cancels, claw yaw incl. a tilted claw, tilt-change weighting, floor tilt spike); `still_pose` rejects a 30 mm swing at both covariances and accepts a still claw;
  `DragWatch` (single frame cannot trip it, sustained drag does, threshold follows the noise, floor 10 mm); simulator tag-derived noise (single tag 10-17 mrad, board < 4 mrad, yaw < 0.4 tilt, configurable corner noise, `fixed` regression mode);
  dwell from the last motion, period margin, loaded release (loaded length, full dwell with a camera signal, `TaskRunner` passes the payload), held-out mount check (passes for a resting claw, aborts when the claw tilts between the sets), startup floor stage on the board;
  calibration length noise with the pose's own attitude sigma.
* **The 8 strict xfails are gone**: `test_slack_probe.py` (2) and `test_margin_trust.py` (6) run on the board fixture (3x3 at the default 0.25 m pitch, 150 mm tags, tag-derived noise, 0.3 px). Their assertions and the thresholds are unchanged
  (the margin fixture's pre-existing `length_sigma_max_m = 0.0075` for THAT fixture only was not touched, default 5 mm unchanged; seed 1 as before). All 8 pass.
* **One documented single-tag test**: `test_slack_probe.py::test_single_tag_probe_limitation_is_documented` (single-tag absolute pose: > 10 mrad and several times the board's sample covariance; the differential probe still resolves all four cables).
  New there: `test_view_that_gets_noisy_mid_probe_skips_the_cable_and_pays_the_retraction_back`.
* **Other test-file changes (not thresholds)**: `test_vision.py` (rotation bound = max(3 deg, 2 x the frame's own reported sigma), LM-refined); `test_attitude.py` (dwell with the 1.25 margin; new config fields and their validation);
  `test_system.py`, `test_garments.py`, `test_margin_trust.py::test_without_the_probe...` (printed-board fixture; item positions chosen from the statics tilt / trusted volume / scan footprint via `simkit.item_offsets_with_small_statics_tilt`;
  `done` order not asserted: nearest first; the "far pose" of the task-confinement test must be <= `motion.task_max_height_m`).

## 5. Reviewer-owned assertions that became stale (`tests/cdpr/test_imu_removal_review.py`, not edited)

Each documents a finding that this change fixes; they fail by design and should be flipped by the reviewer:

| Test | Stale assertion | Now |
|---|---|---|
| `test_claw_position_cov_uses_only_the_camera_to_body_lever_and_perception_adds_the_marker_lever` | `(c1 - c0)[0,0] == (0.010 * \|camera->body\|)^2` (F9) | `claw_position_cov` ignores `rot_sigma_rad`: `c1 == c0`; VisionSource adds exactly `(sigma*\|p\|)^2` (pinned in `test_no_double_counted_camera_to_body_lever_in_the_legacy_covariance`) |
| `test_dwell_arithmetic_and_its_assumptions` | `settle_dwell_s == 5 T` (4.44 s) | `5 x 1.25 x T` = 5.56 s (`tasks.grip_period_margin`); loaded release 7.8 s |
| `test_dwell_is_counted_from_the_start_of_waiting_so_a_claw_seen_moving_then_lost_is_approved_early` | `waited == dwell` with the claw seen moving until 3 s (F8a) | `waited >= 3 s + dwell` |
| `test_still_pose_gate_is_blind_to_swing_when_the_covariance_is_large` | `assert accepts(0.010, 0.030)` (F6) | a 30 mm swing is rejected at every covariance |

Two more still pass but their wording is outdated: `test_mount_offset_absorbs_any_rest_tilt_..._and_the_post_correction_check_is_vacuous` (true of `mount_offset_from_up` alone; the startup now has the held-out check, which catches a CHANGE of the rest tilt between the sets, not a constant one),
and `test_the_two_lever_terms_are_one_rotation_error_...` (its premise is the legacy-frame model).

## 6. Limits and open items

* Simulation only. Real OV2640 corner noise (0.1-0.5 px?), its correlation between frames (static JPEG / demosaic bias does not average), lens distortion beyond the 5-parameter model, rolling shutter and print flatness are unmeasured; `camera.corner_sigma_px` must be measured.
  The IPPE face-on flip is not modelled by the simulator (the real detector refuses or resolves those frames: fewer usable frames than simulated).
* The tilt-change weight (the claw tilts ~3.5 % of its yaw, `kappa` 0.04) comes from the simulated rigid body; unverified on hardware. With ONE tag and a yaw > ~6 deg during a probe the displacement is wrong by 2-12 mm (the tilt change is not measurable); the board is fine.
* The old layout's single-tag floor view is marginal for the pretension: the claw slides 9-11 mm in INITIAL_LIFT against the unchanged 10 mm drag limit (3c seed 1: 9.7 mm at 0.3 px, 11.0 mm at 0.5 px). The printed 0.25 m layout slides 0.4-2 mm (3-4 tags at rest).
* A mismatch between the corner noise the estimator is told and the plant's (0.3 vs 0.5 px) is survivable here (section 3) but spikes of one frame's tilt are then 1.7x more likely to exceed the claimed sigma: the floor stage uses `floor_displacement` (no tilt) for exactly that reason.
* `BoardSurvey` is not run by the startup: the layout JSON for `marker.board_layout_file` comes from an offline survey. (Superseded: SELF_CHECK now surveys the sheets in view of the resting claw, `verification/board_followups_results.md` section 3.)
* Review items not done: F7 second half (compare the first suspended vision tilt with `R_at`, flag a rest-tilt absorbed into the mount offset), F8b/d (the grip gate away from the floor reference is still a dwell + `R_at`, nothing new), F10 (firmware `/grip` interlock),
  F11 (hull area not recorded; the study reports the validated work-volume points instead: 41-43 of 43 at 0.3 px, 35-43 at 0.5 px).
* `calibration.attitude_sigma_rad` keeps its validation (>= `claw.vision_attitude_sigma_rad` without IMU) and now acts as a floor.
