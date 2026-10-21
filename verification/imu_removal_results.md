# D27 implementation: no IMU on the claw (results)

Implementer: Sonnet 5.5 agent, 2026-10-20/21. Independent verification pending. All numbers are simulation numbers.
Inputs: DECISIONS.md D27/D26, `verification/multi_attachment_review.md` findings 1, 6, 7, `docs/CONTROL_SYSTEM_V1.md` 3 and 6.2.

## 1. What changed

| Area | Change |
|---|---|
| Firmware `firmware/claw_s3/claw_s3.ino` | MPU-6050 removed: `Wire`, I2C pins, `mpuInit/imuUpdate`, roll/pitch filter, `imu_ok`, `tilt_rad`, `GRIP_TILT_MAX_RAD`, the 10 Hz attitude task, the pin notes. `/status` no longer has `roll`, `pitch`, `tilt_rad`, `imu_ok` (dropped, not null); it reads the battery ADC once so voltage and flag agree. `/grip` obeys (no 409 tilt gate, no `force`). Safety on bad parameters is stricter than before: `close` must be exactly `0` or `1`, otherwise 400 and the servo does not move (before, anything but `1` meant OPEN, which could drop a held item). Servo limits, power-up open, WiFi-loss behaviour unchanged. |
| Host link `claw_link.py` | `roll_pitch()`, `tilt()`, `force=` and the 409 branch removed; `DetectorFrameSource` no longer reads attitude (detector prior = "claw upright" from the nominal mount). |
| Attitude `attitude.py` (new) | Camera-mount tilt offset from an upright claw; pendulum period and dwell; vision-or-statics attitude estimate with a sigma; camera motion signal and `wait_until_still`. |
| Startup `startup.py` | `_measure_mount` in SELF_CHECK, every startup: 30 averaged frames over the printout with the claw resting on its jaws; stores the offset (`ctx.mount_angle_rad/sigma`, `vision.mount_Q`), saves it with `model.json` (restored by `load_model`), aborts if it exceeds `claw.mount_offset_max_rad` (5 deg). All `claw.tilt()` uses (startup, supervisor) now read the vision tilt. `ctx.T_B_C` is the corrected mount. |
| `perception.py` | `VisionSource.T_B_C` = nominal rotation x measured offset; `PoseObs` carries corners and the marker normal; `StillPose` carries the mean normal and its standard error. Gravity fusion (`imu=`) remains as an optional path, default off. |
| Grip gating `tasks.py` | `_wait_upright` replaced by `_settle_and_approve`: wait until still (image motion of the floor reference below `tasks.grip_still_rate_rad_s` for `grip_still_frames` frames; no camera signal: dwell of `grip_settle_periods` pendulum periods, T = 2 pi sqrt(L/g), L = CoM depth below the attachment plane = 0.196 m, T = 0.89 s, dwell 4.4 s); then the tilt (vision when the reference is in view, else `R_at`) and the predicted `R_at` tilt at the hover and at the grip pose must be <= `claw.grip_tilt_max_rad`. Also before a release. Records in `TaskRunner.approvals`. |
| Config | `claw.imu` false in `config/robot.sim.json` (example was already false). New validated fields: `claw.vision_attitude_sigma_rad` 0.010, `claw.statics_attitude_sigma_rad` 0.07, `claw.mount_offset_max_rad` 5 deg; `calibration.attitude_sigma_rad` 0.004 -> 0.010 (validation refuses a value below the vision sigma while `claw.imu` is false); `tasks.grip_still_rate_rad_s` 0.02, `grip_still_frames` 5, `grip_settle_periods` 5, `grip_settle_min_s` 2, `grip_settle_timeout_s` 15. `service.py` refuses `claw.imu = true` on hardware (no provider exists). |
| Simulator | `SimClaw`: no `tilt()` and no `tilt_rad` in `status()`; `roll_pitch()` kept only as the optional gravity sensor. `SimCamera(mount_rotvec=)` = true camera tilt error; `SimRobot(mount_err_rad=0.02)` draws one per seed, so the startup measurement is exercised in every simulated run. Plant attitude noise unchanged (2 mrad/axis, the level of the IMU simulation); the estimator is told 10 mrad. |
| Harness (review finding 6) | `tests/cdpr/simkit.assert_no_eq_failures(sim)` (fails on `World.eq_failures > 0` or a `no_equilibrium` event). Used in `test_system.py` (lifecycle at five points, crash test, `run_startup`, bead tests), `test_margin_trust.py`, `test_garments.py`. 0 failures everywhere it runs. |
| Docs | `CONTROL_SYSTEM_V1.md`: component table, 3.1 (vision attitude, mount offset, "minimum 2-norm", floor rest), SELF_CHECK row, estimator observations, historic IMU note, the GRIP rule. |

## 2. Tests (`OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr tests/firmware`)

Final run: **230 passed, 8 xfailed, 1 failed** in 20 min 39 s (was 195 passed; +38 `test_attitude.py`, +5 `test_claw_sketch.py`).
* New: `tests/cdpr/test_attitude.py` (mount offset recovery incl. noise averaging, vision tilt read against the corrected mount, optional gravity fusion, pendulum dwell, settle gate with camera / dwell / never-still / N consecutive frames, approval and refusals, config validation, startup measures and aborts), `tests/firmware/test_claw_sketch.py` + `tests/firmware/claw_stubs/` (the claw sketch compiled with `-Wall -Wextra -Werror` against host stubs, handlers called: `/status` is valid JSON without attitude, `/grip` obeys and rejects bad parameters). Not an ESP32 build: `arduino-cli` is not installed here.
* **1 failed (reviewer-owned, cannot be edited by this task):** `tests/cdpr/test_multi_attachment_review.py::test_finding_config_numbers_that_the_cad_has_since_moved_away_from` asserts `claw.imu is True`. It is the documented "flips when fixed" assertion; the one line `assert claw.imu is True` must become `is False`.
* **8 xfailed, `strict=True`, conditions and thresholds untouched (genuine D27 consequence, section 4):** `test_slack_probe.py` 2 tests, `test_margin_trust.py` 6 tests (the board + probe fixture). They fail (XPASS) the day the problem is solved, which forces removing the mark.
* Fixture changes that are not threshold changes: `test_system.py` and `test_garments.py` put the items around where the startup left the claw (the old room-centre layout fell outside the scan footprint / validated volume once the noise stream changed); `test_system.py` uses `simkit.ModelFrameItemPerception` (items reported in the planner's frame, like a real camera chain), because `SimItemPerception` reports truth coordinates and a 60-65 mm room-registration error of the calibration (also present with the IMU on: the same seed gives 65 mm with `claw.imu=true`) exceeded the simulated gripper reach of 60 mm and failed the pick for a reason unrelated to the workflow.

## 3. Floor-reference study with `claw.imu=false`

Command (unchanged script, defaults of the simulator): `scripts/sim_floor_reference_study.py --suite main --only "3c" --seeds 3 --probe --no-whatif`
(board 3x3 p0.42 + slack probe, seeds 0-2). "sigma" = predicted absolute cable-length sigma, max over the four cables (the quantity of the D26 rule). Raw output was kept outside the repo.

| run | seed | accepted | predicted sigma (mm) | worst true L0 error (mm) | trust | readings probed |
|---|---|---|---|---|---|---|
| **vision only** (`imu=false`, estimator 10 mrad, plant 2 mrad/axis, mount error 1 deg/axis measured at startup) | 0 | yes | **19.4** | 68.6 | LOCAL_ONLY | 37/152 (24 %) |
| | 1 | **no**: witness RMS 9.3 mm > 6 mm (RECOVERY_REQUIRED) | 21.0 (refit of the rejected run) | 52.1 | NONE | 31/152 (20 %) |
| | 2 | yes | **20.3** | 20.9 | LOCAL_ONLY | 38/152 (25 %) |
| same code, **IMU on** (`claw.imu=true`, `attitude_sigma_rad=0.004`, plant as above) | 0 | yes | 16.2 | 27.1 | LOCAL_ONLY | 104/152 (68 %) |
| | 1 | yes | 16.2 | 19.3 | LOCAL_ONLY | 106/152 (70 %) |
| | 2 | yes | 15.6 | 15.4 | LOCAL_ONLY | 114/152 (75 %) |
| recorded before (`multi_attachment_results.md`) | 0-2 | 3/3 | 15.4 median / 16.8 max (12.8 / 12.9 for the old point claw) | 24.6 / 49.8 | LOCAL_ONLY | 68 % |

* Vision-only predicted sigma is 19.4 / (21.0) / 20.3 mm: about +25 % over the IMU-on 15.6-16.2 mm (and +26-30 % over the recorded 15.4); the predicted length sigma over the work volume rises from 5.9-6.6 mm to 8.8-9.1 mm against the 5 mm criterion. The recorded 12.8 -> 15.4 mm figures were optimistic, as review finding 1 said.
* Trust: LOCAL_ONLY or no startup in all three vision-only seeds (IMU on: LOCAL_ONLY in all three, never VERIFIED either, as in the recorded run). err/sigma max 3.5 (vision) vs 1.7 (IMU on, same code); the vision-only estimator under-reports its error, as the recorded run did (3.2).
* Cause of the loss: the pose covariance the code derives for a vision-only pose includes the lever term `rot_sigma * |p|` (10 mrad x 0.6 m = 6 mm per frame at the first suspended pose, diagonal 37 mm^2 against 3.7 mm^2 with gravity fusion), so the per-pose slack probe cannot resolve onsets and skips most readings (24 % probed instead of 70 %), which also leaves slack in the data (seed 1 witness).
* Stress test, plant attitude noise raised to the figure the estimator assumes (`STUDY_ROT_SIGMA` wrapper around the same script, `--tag`): **5 mrad/axis: 0/3 startups complete** (seed 0 "claw dragged while tensioning (0.0113)", seeds 1-2 "slide directions disagree with the anchor entries (RMS 3.7 / 3.5 sigma)"); **10 mrad/axis: 0/3** (3.7 / 3.2 sigma slide-direction disagreement, "claw dragged (0.0115)"). The floor-stage checks (taut-onset and slide-bearing detection from the single-marker pose) fail at the figure D27 is told to assume; a better-conditioned floor reference or a lower-noise attitude path is needed before relying on vision-only attitude with the single 6-inch marker. At the 2 mrad plant used for the table above the startup completes.
* Startup measurement of the mount: with a true mount error of about 1 deg per axis the measured offset is within the reported standard error (2-3 mrad) of the truth (`test_startup_measures_the_camera_mount_offset_while_the_claw_rests_on_the_floor`; a 10 mrad-plant seed-0 startup measured 0.0201 rad against a true 0.017 rad, error 3.4 mrad).

## 4. Genuine changes caused by the noisier attitude (reported, not relaxed)

1. **Slack probe (D26's honest-sigma path)** resolves only 20-25 % of readings with vision-only attitude; at the first suspended pose cables A and D are unresolved ("over-retraction > 6 mm even with 40 frames"). Two `test_slack_probe.py` tests xfail.
2. **VERIFIED-by-margin is not reached**: the board + probe fixture (seed 1) is rejected on its witness RMS (9.3 mm), so the six margin tests that depend on it xfail. The margin rule itself is unchanged and its no-simulation tests pass.
3. **Calibration sigma** +25 %, predicted work-volume sigma 8.8-9.1 mm vs the 5 mm criterion (finding 2 of the review still open: nobody has isolated the earlier +33 % rise).
4. **Floor-stage detection** needs plant attitude noise <= about 2-3 mrad/axis in the simulator (section 3).

## 5. Remaining references to the IMU (`grep -rn -i "mpu\|imu" firmware/claw_s3 roomcleaner/cdpr`, minus the words "minimum/simulat/maximum/...")

All intentional: `claw_s3.ino` header comment (no IMU, D27); `perception.py` optional gravity fusion (`imu=` argument, "IMU unavailable" branch, `imu.roll_pitch()` call and comments); `vision/marker.py` field `imu_rp` (optional) and a docstring; `attitude.py` module docstring; `config.py` the `claw.imu` flag with its comment, its validation, the `calibration.attitude_sigma_rad` note and the "no IMU" validation message; `service.py` refusing `claw.imu=true` on hardware; `claw_link.py` / `startup.py` / `tasks.py` / `sim/world.py` / `sim/harness.py` D27 comments and docstrings; `garments.py`, `kinematics.py` no longer mention it as a source.

Not edited (outside the allowed list): `docs/design_resolution/quick_resolutions.json` still says "Existing IMU gate"; `research/startup_calibration_20261016/parameters.example.json` has `imu_fitted`.

## 6. Limits and open items

* The camera-mount tilt is only as good as "the claw rests exactly upright on its jaws": a rest tilt of the claw on the printout (floor flatness, a jaw standing on the paper edge) is absorbed into the offset. The rotation about the vertical is unobservable there and keeps the CAD value. Bound: `claw.mount_offset_max_rad` 5 deg; standard error 2-3 mrad (30 frames at 10 mrad).
* `claw.statics_attitude_sigma_rad` (0.07 rad) is a documented estimate from the review (CoM height and payload, 3-6 deg), not a measurement; `R_at` plans with the unloaded mass.
* The settle rate (0.02 rad/s) and 5 frames are defaults chosen from the simulated 0.1 s frame interval and 0.3 px corner noise; the real corner noise and WiFi frame jitter are unmeasured. The camera signal exists only where the corners of the floor reference are in the image; elsewhere the pendulum dwell (4.4 s) is used, and it only covers the rocking mode, not the slow swing of the whole claw on long cables.
* `claw_body_frame` numbers, CAD and `cad/params.py` untouched (a later task regenerates them).
