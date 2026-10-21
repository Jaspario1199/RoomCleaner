# Independent review of the D27 IMU removal (commits 8adeb8f..HEAD)

Reviewer: calculation-checker (Sonnet 5.5), 2026-10-21. Read-only on code, configs and other tests. Files written: this report,
`tests/cdpr/test_imu_removal_review.py` (14 fast tests, all pass), `scripts/review_attitude_noise.py` (CRB + Monte Carlo),
`scripts/review_board_sim.py` (simulator study with a geometry-dependent attitude noise; monkeypatches inside its own process only).
All sim numbers are simulation numbers. Nothing was committed.

## 0. Verdict

* The implementer's numbers REPRODUCE exactly (table A below), so the work is honest. The conclusion drawn from them is not:
  "vision-only attitude costs +25 % sigma, 24 % probing, 8 xfails and a failing floor stage" is mostly produced by **how the simulator
  and the estimator model the attitude noise**, not by the physics of the floor board.
* Vision-only attitude is **workable with the floor board**, with two small changes (section 6): a per-frame attitude sigma taken from
  the tag geometry instead of the constant 10 mrad, and a board whose centre sheets are close enough that >= 2 tags are in view when the
  claw rests on the floor (about 0.5 m lens height). With the single 6-inch tag it is not workable at the stated 10 mrad in most poses.
* 11 findings (3 High, 5 Medium, 2 Low, 1 Info), section 5; F1-F3 should be fixed before the next study or any hardware attempt.

## 1. Facts, assumptions, derived results, uncertainty

**Supplied facts** (repository, implementer): `claw.vision_attitude_sigma_rad` 0.010, `calibration.attitude_sigma_rad` 0.010,
`statics_attitude_sigma_rad` 0.07, `mount_offset_max_rad` 5 deg, `grip_tilt_max_rad` 5 deg, `grip_still_rate_rad_s` 0.02, 5 frames,
5 pendulum periods (min 2 s, timeout 15 s), CoM depth L = 0.196 m (`com_body_m` z = -0.19638, attachments z = 0), camera fx = 520 px
(OV2640 guess, `config/camera.sim.json`), single tag 152.4 mm, board = 9 sheets, 36h11 ids 0-8, 150 mm tags (D26), lens ~0.51 m above the
floor when the claw rests (`lowest_point_body` -0.5173, camera z -0.0056), v7 jaw opening 91.6 mm (`verification/gripper_v7_numbers.json`),
`SimGripper` reach 60 mm radial (`sim/world.py:110`), motion limits 0.1 m/s^2 in `config/robot.sim.json`.
**What "plant attitude noise" is in the simulator**: `SimCamera.rot_sigma`, an iid rotation drawn per FRAME and applied to the measured
`R_C_M` (all three camera axes, same sigma, independent of how many tags are in view). It is camera MEASUREMENT noise. True claw motion is
`World` physics and is not touched. The estimator is told `claw.vision_attitude_sigma_rad` separately.

**Approved assumptions** (D26, D27, user): floor board of 9 Letter sheets, claw rests upright on its jaws over the printout, no IMU,
host approves grips. Camera corner noise 0.3 px is the simulator's own value; I also report 0.5 px.

**Derived by me** (independent of the implementer): CRB of the 6-DOF pose from corner reprojection (numpy) and a Monte Carlo through
`cv2.solvePnP` (`scripts/review_attitude_noise.py`, 12 s). Closed form for a fronto-parallel square tag of edge a at range z:
sigma_tilt ~ 2 sigma_px z^2 / (f a^2) (keystone term, four corners).
**Unresolved**: real corner noise of an OV2640 q10 JPEG tag (0.1-0.5 px?), its frame-to-frame correlation (static JPEG/demosaic bias does
not average), lens distortion, floor flatness, real friction on the printout, real damping of the claw swing, CoM after v7/D28/electronics.

## 2. Pose covariance (question 1)

| claim | my result | verdict |
|---|---|---|
| lever term rot_sigma*|p| is physical | The pose error is one rotation of the whole estimate about the marker origin. Camera position in M is -R^T t, so a tilt error moves it by tilt x range. MC (1.2k trials, 152 mm tag, 0.52 m, 0.3 px): position error = tilt error x range within 1-3 %, correlation -1.00. Lever for the claw origin = |p| (marker to claw origin), which is what the code uses; it differs from the camera range by < 15 %. | AGREE |
| 6 mm per frame at 0.6 m | 10 mrad x 0.6 m = 6 mm. The tilt noise itself: 10.5 / 17.9 / 31.8 / 49.6 mrad at 0.46 / 0.60 / 0.80 / 1.0 m on axis (0.3 px, LM-quality), 4.4 / 7.6 / 13.6 / 21.3 mrad when the tag is 0.2 m off axis. So 10 mrad is right only at ~0.46 m on axis and is optimistic above that. | AGREE for 0.46 m, optimistic above |
| double counted? | `claw_position_cov` adds (sigma x 0.09 m camera-to-body)^2 and `VisionSource.observe` adds (sigma x |p|)^2. They are the same rotation error; the lever on the body origin is |p| only, so the 0.09 m term is a double count worth 1-2 % of the variance. Attitude as an explicit input (`calibration.attitude_sigma_rad x |attach|` = 0.6 mm) is the same rotation error treated as independent of the position error (true correlation -1); effect < 20 % of 0.6 mm. | negligible double count |
| isotropy | The code adds the lever as sigma^2 |p|^2 I. For a camera looking down the lever error is horizontal: CRB/MC z = 0.7 mm vs xy = 6.7 mm at 0.52 m. The probe projects onto a cable response that is mostly vertical, so its sigma is overstated. | DISAGREE (conservative, Low/Medium) |
| averaging N frames | MC, 0.6 m on axis: N = 4 / 10 / 30 give 9.3 / 5.9 / 3.5 mrad against 18.4 / sqrt(N) = 9.2 / 5.8 / 3.4. Holds for independent frame noise only. | AGREE (iid), static bias NOT averaged (uncertainty) |
| detector quality | `MarkerDetector.pose_from_corners` uses IPPE_SQUARE without LM refinement (`board.py` refines). At 0.46 m on axis I measure rms tilt 55 mrad (IPPE only) vs 10 mrad (IPPE+LM) with 0.3 px noise; near fronto-parallel the two IPPE solutions are within ~70 mrad and `select_pose` rejects or guesses (`floor_board_detector.md`: refused 8 of 12 frames at 1.5 m). | DISAGREE with "10 mrad" for the code as written (Medium) |

## 3. The 8 strict xfails (question 2)

They are **not** clean consequences of "a 10 mrad attitude". Three separate causes, none of them the floor board:

1. **Estimator told 10 mrad, plant is 2 mrad (6 margin tests, and the sigma +25 %).** The rig draws 2 mrad (`harness.py`) but
   `VisionSource.rot_sigma` is 10 mrad, so the probe believes 6 mm of noise per frame, skips 75 % of readings ("over-retraction > 6 mm even
   with 40 frames") and the witness fit of seed 1 fails. Control run F (plant 2 mrad, estimator told 2 mrad, same board, probe on,
   seeds 0-2): **3/3 startups READY, trust VERIFIED 3/3, 80 / 84 / 81 % of readings probed, sigma 14.8 / 11.1 / 11.2 mm.** That is better
   than the IMU-on figures in the implementer's table (LOCAL_ONLY, 68-75 %, 15.6-16.2 mm). A constant sigma that ignores the number of
   tags is wrong in both directions: 10 mrad is 3-15x too pessimistic for the board at suspended poses (CRB 0.6-3 mrad) and too optimistic
   for the single tag above 0.46 m. The six `board_probe` tests use the board fixture, so their xfail premise is internally inconsistent.
2. **The probe statistic is a differential position built from absolute poses (all 8).** Each still pose carries its own tilt-lever noise,
   which does not cancel between poses. But the unmoved-claw displacement can be measured in the camera frame with ONE reference rotation,
   `-R_ref^T (t_k - t_ref)`, where only the lateral/depth noise of the marker origin remains. MC, single tag, 0.52 m, 0.3 px, 0.3 mm
   z-noise either way: xy noise **3.1 mm -> 0.10 mm (n = 10) and 1.55 -> 0.05 mm (n = 40)**. So even the 2 `test_slack_probe.py`
   tests (single 6-inch tag, first suspended pose at ~0.59 m, where the absolute tilt noise really is ~18 mrad) fail for the wrong reason.
   (A rotation of the claw during the probe is neglected by this estimator; the existing model already neglects it.)
3. **Genuine part:** the absolute pose with one tag at the rest height has 10-13 mrad and 5-7 mm per axis (CRB and MC agree), and a
   measurement scheme that depends on it fails (section 4).

`strict` xfail also removes the regression guard of the probe MECHANICS (a broken probe still "xfails"). Recommended: keep one
single-tag test documenting the outcome, and run the mechanics tests with a board-quality attitude (2-3 mrad) so they guard the code.

## 4. Stress test and the floor board (question 3)

Replication (A, `review_board_sim.py --mode fixed`, board 3x3 p0.42 + probe, seeds 0-2): plant 2 mrad: seed 0 accepted 19.4 mm / 24 %,
seed 1 rejected (witness 9.3 mm, 21.0 mm, 20 %), seed 2 accepted 20.3 mm / 25 %; plant 5 mrad: 0/3 ("claw dragged while tensioning 0.0113",
"slide directions disagree" 3.7 / 3.5 sigma); plant 10 mrad: 0/3. **Identical to the implementer's table.** Giving yaw 1/10 of the tilt
sigma (what a tag really does: CRB yaw 1.4 mrad) changes nothing (E: tilt 5 and 10 mrad, 0/6).

**Is 5-10 mrad realistic for a single 6-inch tag at ~0.5 m, OV2640?** Yes for the floor stage: sigma_tilt = 2 x 0.3 x 0.51^2 / (520 x 0.1524^2)
= 13 mrad (CRB 12.9, MC 13.4), i.e. 6.6 mm per axis of claw-position noise per frame; 22 mrad at 0.5 px; 6 mrad at 0.15 px. It is not
realistic as a general constant (section 2). Also, the failures are not random: the floor stage scales its thresholds with the measured
frame scatter, `noise_m`: `thr = max(2 mm, 4 noise_m)`, `bearing_d = max(.., 2 thr)`. With one tag at rest noise_m ~ 10 mm, so the take-up
continues until the claw has slid ~80 mm (I log slides of 83-85 mm and 131 mm of payout; baseline 25 mm). A long slide on carpet/paper
bends away from the straight line to the anchor, and the bearing check then fails at 3.4-3.8 sigma. The pretension drag-watch uses a FIXED
10 mm single-frame threshold (`max(3 onset, 0.01)`), which a 7 mm/axis noise exceeds in ~36 % of frames. So the failure is real for
that measurement scheme, not a seed artefact.

**Board estimate and runs.** CRB (0.3 px; the 150 mm tags of D26), n = tags fully in view with the 4 px margin:

| camera | single 152 mm tag | board 3x3 pitch 0.42 |
|---|---|---|
| 0.46-0.6 m, over a tag (floor-rest view) | 10.5-17.9 mrad | **1 tag: 10.8-18.4 mrad (no gain)** |
| 0.5 m, 0.1-0.2 m off a tag | 4-8 mrad | 2 tags: 1.9-3.2 mrad |
| 0.8 m | 31.8 mrad (13.6 off axis) | 3-4 tags: 1.5-2.9 mrad |
| 1.0-1.3 m | 50-84 mrad (21-36 off axis) | 6-9 tags: 0.6-1.1 mrad |

so the board's gain is real but it needs >= 2 tags in view. At the rest height, pitch 0.42 gives ONE tag in 8 of 8 seeds (11.8-13.4 mrad);
pitch 0.30: 2-3 tags in 7 of 8 seeds (1.7-2.8 mrad); 0.25: 3-4 tags (1.0-2.0 mrad); 0.22: 3-6 tags (0.8-2.1 mrad). Simulator runs
(`review_board_sim.py --mode crb`: rotation noise drawn from the CRB of the tags in view, estimator told the same sigma per frame, probe on):

| board (0.3 px) | tags / tilt sigma median | startups complete | probed | sigma max (mm) | trust |
|---|---|---|---|---|---|
| p0.42, as D26 (B) | 1 / 9-11 mrad | 0/3 (floor stage: 2x slide-direction 3.4-3.5 sigma, 1x drag 11.5 mm) | - | - | - |
| p0.30 (H) | 3-4 / 1.5-3.0 mrad | 2/3 (seed 0 starts with 1 tag in view: slide directions) | 68, 72 % | 17.7, 18.2 | LOCAL_ONLY |
| p0.25 (I) | 4-5 / 2.5-3.0 mrad | 3/3 | 70, 72, 76 % | 18.3, 19.9, 19.2 | LOCAL_ONLY |
| p0.22, study case 3a, 0.16 tags (J) | 5 / 2.7-2.8 mrad | 2/3 (seed 0: calibration rejected, 1 outlier reading, witness 3.8 mm) | 76, 72, 77 % | 22.2, 20.7 (refit), 20.1 | LOCAL_ONLY |
| matched-sigma control (F): p0.42, plant 2 / estimator 2 mrad | - | 3/3 | 80-84 % | 11.1-14.8 | **VERIFIED 3/3** |
| implementer, vision only, estimator 10 mrad (A) | - | 2/3 | 20-25 % | 19.4-21.0 | LOCAL_ONLY |
| implementer, IMU on (supplied, not re-run) | - | 3/3 | 68-75 % | 15.6-16.2 | LOCAL_ONLY |

Conclusion: with a board that shows >= 2 tags at the rest pose and a per-frame sigma, the slack probe is back (68-76 % probed, equal to the
IMU-on 68-75 %) and the floor stage completes in 8 of 9 runs (p0.30: 2/3, p0.25: 3/3, p0.22: 3/3) and 7 of 9 end READY. They stay LOCAL_ONLY because the predicted work-volume sigma is 6.6-7.6 mm
against the 5 mm criterion (the same reason as IMU-on). Absolute-length sigma 18-20 mm is still above the IMU-on 16 mm: the dense-core boards have a
smaller span and a worse scale/depth term; the p0.42 board (span 1.0 m) gives 11-15 mm and VERIFIED only if the estimator is told the true
low noise (F) AND the floor stage works, which needs the rest pose to see >= 2 tags. A hybrid (4-5 sheets near the rest position at
<= 0.28 m pitch plus an outer ring at ~0.45 m) is the layout I would try; it is not simulated here (`FloorBoard` is a regular grid).
Sensitivity: at 0.5 px corner noise (pitch 0.25, seed 1, 3 tags, 3.3 mrad) the floor stage already faults again (slide directions 3.6 sigma; one seed run
only, the second was stopped), so the floor stage is marginal against corner noise and the real OV2640 corner noise must be measured (F2 would remove this
dependence).
Shifting the p0.42 grid by half a pitch gave 2 tags in 6 of 8 seeds in a static check but "marker not found" in the real runs (fragile:
a +-1 cm margin separates 2 tags from none), so I do not recommend relying on placement alone.

## 5. Findings (severity, action)

| # | sev | finding | action |
|---|---|---|---|
| F1 | High | One constant attitude sigma (10 mrad, also enforced by config validation: `calibration.attitude_sigma_rad >= claw.vision_attitude_sigma_rad` when no IMU) is wrong for every geometry: 3-15x pessimistic for the board, optimistic above 0.46 m for one tag. It produced the 6 margin xfails, the 24 % probing and the +25 % sigma. | Detector reports a per-frame tilt sigma (board: from the joint-PnP J^T J it already forms; single tag: 2 sigma_px z^2/(f a^2) x 1.3); `VisionSource` uses it; config values become floor/ceiling. ~30 lines. |
| F2 | High | Floor stage: thresholds scale with measured scatter (slides 80+ mm with 1 tag), the pretension drag-watch is a fixed 10 mm single-frame test; both are driven by absolute-pose lever noise. | Measure onset/drag in the camera frame with a reference rotation (noise 0.1 mm vs 3 mm); at least scale the drag threshold with `noise_m`. |
| F3 | High | Board pitch 0.42 gives ONE tag at the rest height in 8/8 seeds, so the board adds nothing exactly where the floor stage needs it. | Layout change (pitch <= 0.30 for the sheets around the rest position, hybrid with outer ring); state it in the print instructions and `print_floor_board.py`. |
| F4 | Medium | Single-tag detector uses IPPE without LM refinement: 55 mrad rms vs 10 mrad refined at 0.46 m on axis. | Refine with `solvePnPRefineLM` as `board.py` does. |
| F5 | Medium | The 2 `test_slack_probe.py` xfails test probe mechanics; strict xfail hides regressions of that code. | Re-run them with a board-quality attitude; keep a documented single-tag expectation. |
| F6 | Medium | `still_pose` accepts scatter up to hypot(spread_max, 3 sqrt(trace cov)): with the inflated covariance a 30 mm swing (2.8 s period) passes as "still" (rot_sigma 0.010) where the 0.004 covariance rejects it (test). Startup samples may be taken on a swinging claw. | Gate stillness on image motion (as `wait_until_still`) not on noise-scaled position scatter. |
| F7 | Medium | Mount offset: a rest tilt of the claw on its jaws is absorbed as a mount error (test: 3 deg rest tilt -> a level hanging claw reads 3 deg, leaving 2 of the 5 deg gate). The startup "tilt after correction" check is vacuous by construction; the only guard is the 5 deg abort. The standard error (scatter/sqrt(30), 2-3 mrad) ignores static bias. | Compare the vision tilt at the first suspended pose with `R_at` (sigma 4 deg) and flag/refresh the offset; log it in the report. |
| F8 | Medium | Grip gate: (a) the dwell is counted from the start of waiting, so a claw seen moving at t = 3 s and then lost is approved 1.4 s later (test); (b) the grip site is usually outside the floor-reference view, so the gate is a blind 4.4 s dwell plus `R_at` with sigma 4 deg against a 5 deg limit, nearly uninformative; (c) the simple-pendulum period is ~20 % short (compound pendulum with an assumed k = 0.13 m: T = 1.06 s, 4.2 periods in 4.44 s), and with 0.9 kg at the jaws a release has T = 1.3-1.5 s, i.e. < 3.8 periods; (d) D28 shortens L to ~0.16 m (conservative). With the 0.1 m/s^2 limit the rocking amplitude is ~10 mrad (0.6 deg) so the margin is large today. | Restart the dwell at the last observed motion; use loaded L at release; gate on tilt + 2 sigma; measure real damping. |
| F9 | Low | Covariance is isotropic; z overstated ~10x. 0.09 m term is a 1-2 % double count. | Use sigma^2(|p|^2 I - p p^T) restricted to roll/pitch. |
| F10 | Low | Firmware: see 7. The claw now closes for any LAN client with `close=1`; the local interlock is gone and the host ignores the `grip()` return value. | Accept and note, or add a shared secret. |
| F11 | Info | Validated hull area fell 20 % with vision only (1.73 vs 2.16 m^2, seeds 0-1; the IMU-on seed 2 failed its startup in this single-tag run). Not recorded in the results report. | Record. |

## 6. Recommendation

**Is vision-only attitude workable with the floor board? Yes, conditionally.** Evidence: board runs with a per-frame sigma recover
68-76 % probing and 8/9 startups with pitch 0.25-0.30; with the estimator told the true noise the p0.42 board reaches VERIFIED 3/3
at 11-15 mm. The 10 mrad constant and the single-tag floor stage are what failed.

**Minimal change set** (code and print layout, no CAD):
1. Per-frame attitude sigma from the detection geometry into `VisionSource` (F1) and LM refinement in the single-tag path (F4).
2. Floor board: >= 2 tags in view at the 0.5 m rest height, i.e. the sheets around the rest position at <= 0.28 m pitch (F3).
3. Take-up onset, drag-watch and probe use camera-frame displacement with a reference rotation (F2); this also makes the single-tag fallback
   usable. Not tested in the simulator; MC says 30x lower noise.
4. Replace the 8 xfails by board-quality fixtures (F5); fix the dwell-restart and rest-tilt checks (F7, F8).
Then re-run the study; a Fable audit is not needed before that.

## 7. Items 4 and 5

**Firmware** (`firmware/claw_s3/claw_s3.ino`, `tests/firmware/test_claw_sketch.py`: 5 pass): no `Wire`/MPU/roll/pitch/tilt/GRIP_TILT in code (grep test);
`/status` has no attitude and is valid JSON (one ADC read); `/grip` obeys `close=1|0`, answers 400 and does not move the servo for missing,
empty or other values; servo limited to 600-2400 us, power-up open, WiFi loss does not open. The test compiles the REAL source with
`-Wall -Wextra -Werror` against minimal stubs and calls the handlers: meaningful for logic and regressions, not for the ESP32 core
(`arduino-cli` is not installed, stub semantics of `WebServer::arg/hasArg`, ADC and `snprintf` buffer width are assumptions). An
`arduino-cli compile` for `esp32:esp32:XIAO_ESP32S3` is still needed.

**Settle-then-approve**: T = 2 pi sqrt(0.196/9.81) = 0.8887 s, dwell 4.44 s (arithmetic AGREE). Rate threshold 0.02 rad/s: a still claw passes
99.9 % of frame pairs at 0.3 px, 74 % at 0.5 px, 4 % at 1 px (fails closed after 15 s), and it is equivalent to ~3 mrad of rocking
amplitude; refusal paths (still moving, vision tilt > 5 deg, predicted `R_at` tilt at hover or grip pose > 5 deg) are covered by the
implementer's tests and behave as described. Open points: F8.

**Mount offset**: 30 frames, abort at 5 deg: correct arithmetic; recovery in the simulator is near the standard error (one board run with a single tag in view at rest: 0.57 deg measured against
0.97 deg true, 1.9 sigma). Open points: F7.

**`service.py`**: `build_hardware_context` raises SystemExit with the D27 message when `claw.imu = true` (my test, with fake addresses). The
refusal comes after the UDP transport is bound and the claw client created (harmless: the process exits).

**Fixture changes** (`test_system.py`, `test_garments.py`): legitimate isolations, with two caveats. I measured the model-minus-truth claw
position after a single-tag startup, seeds 0-2: IMU off 62 / 52 / 49 mm, IMU on 62 / 45 / 64 mm (seed 2 IMU-on startup was
RECOVERY_REQUIRED); so the 60-65 mm room-registration error is **not** a D27 effect, it comes from the operator anchor entries (4 cm
per axis in `default_world`) and is common-mode to everything the camera measures, which is what `ModelFrameItemPerception` reproduces.
Caveats: (1) it cancels the error exactly at the scan pose only, so the position-dependent calibration error between scan and grip pose is not
exercised (predicted 8.8-9.1 mm against 5 mm); (2) the simulated reach (60 mm) is larger than the v7 jaw half-opening (91.6/2 = 45.8 mm), so
a pick that passes at 50-60 mm miss would not close on the hardware; set `reach_xy` to ~0.046 in a follow-up. Moving the items to the claw's
position does not hide a loss of the validated volume (the room centre is inside the hull in all runs), but the hull is 20 % smaller (F11).
Full-suite run: not done (21 min); `test_attitude`, `test_claw_sketch`, `test_slack_probe`, `test_margin_trust` (16 passed, 8 xfailed, 526 s),
and the 14 review tests were run; `test_system` + `test_garments` (the fixture files): 19 passed in 448 s.

## 8. Reproduce

```
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr/test_imu_removal_review.py        # 2 s
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_attitude_noise.py [--probe]                 # CRB + MC tables, 15 s
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_board_sim.py --mode fixed --sigma 0.002 0.005 0.010 --seeds 3   # A, ~10 min
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_board_sim.py --mode crb --pitch 0.30 --seeds 3                  # H
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_board_sim.py --mode fixed --sigma 0.002 --seeds 3 \
    --cfg claw.vision_attitude_sigma_rad=0.002 --cfg calibration.attitude_sigma_rad=0.002                          # F
OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_board_sim.py --registration                  # item 5
```
