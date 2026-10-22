# Task layer: station keep-alive, reach, carry dry run, claw I/O (implementer results, 2026-10-22)

Scope: `roomcleaner/cdpr/startup.py` (helper extraction only), `garments.py`, `tasks.py`, `claw_link.py` (one class attribute),
`tests/cdpr/test_task_pumping.py`, `tests/cdpr/test_task_reach.py`. Everything is simulation; nothing was run on hardware and the
real YOLO-World detector was not available here (ultralytics and torch are not installed).

## 1. Problem

While a command owns the robot, the idle host loop does not pump the stations (`Service.idle_tick`), so the command thread must keep the
keep-alive going itself. A stall longer than `faults.lease_s` (0.3 s) latches Fault.LEASE on every armed station. The startup does this
with `StartupSequencer._pumped`; the task layer did not. Unpumped on the command thread:

- the garment detector (`ClawGarmentPerception._detections` -> `det.detect`; YOLO-World loads its model lazily on the first call);
- the path check of every planned task move (`plan_line_from`: a tension solve at every path point, both ways, with payload);
- on hardware, the claw's blocking HTTP calls: `frame_bgr` (GET) and `claw.grip` (POST), both with a 1 s timeout.

## 2. What changed

| file | change |
|---|---|
| `startup.py` | `run_pumped(ctx, fn, *a, **k)` at module level is the body of `_pumped`, unchanged (one worker thread named `startup-pumped`, `ctx.wait` on the 20 ms grid, lowered GIL switch interval restored in `finally`, worker exception re-raised unchanged, `ctx.wait` exception propagates at once, worker not waited for). It reads `PUMP_STEP_S / PUMP_YIELD_S / PUMP_SWITCH_INTERVAL_S` from `StartupSequencer` at call time. `_pumped` calls it. Nothing else in the file changed. |
| `garments.py` | `_detections(ctx, img, mapper, core)` calls the detector through `run_pumped`; `scan`, `holding`, `item_at` pass `ctx`. `_frame(ctx)` runs `frame_fn` through `run_pumped` only if `getattr(ctx.claw, "blocking_io", False)`. Results and order of the detections are those of the detector. |
| `claw_link.py` | `HttpClawClient.blocking_io = True`. The simulator's `SimClaw` has no such attribute, so the sim stays unpumped (its calls go into the world that `ctx.wait` steps on the command thread). |
| `tasks.py` | `_move` plans through `run_pumped` (positions read on the command thread). `_grip` runs `claw.grip` through `run_pumped` when `blocking_io`. New `TaskUnreachable(StartupAbort)` for a target outside the trusted volume or a PlanError starting `workspace:` / `tension infeasible` (other PlanErrors, motion faults and pauses stay plain `StartupAbort`). `_scan_point`, `_check_hamper`, `_dry_run_carry` as below. `TrustedVolume` gains `extents()`, `extent_text()`, `centroid_xy()`. |

Behaviour added to `TaskRunner`:

1. First scan: above the claw if that point is allowed; else above `cfg.start_point_xy()`; else above the volume-weighted centroid of the hull
   at the scan height; none allowed -> `StartupAbort(paused=True)` before any motion. The note is logged and sent to `on_state("SCAN", ...)`.
2. Hamper: at the start of `run()` the transport/release pose `[hamper, z_t]` must be allowed (and below `motion.task_max_height_m`), else
   `StartupAbort(paused=True)` with the hamper position and the trusted extents (x, y, z), before any motion.
3. Unreachable item: approach and grip poses are checked before the claw moves; a `TaskUnreachable` from the approach or the descend move also
   fails the item ("unreachable: <reason>"), it is added to `skip`, the run goes on. It counts toward `max_consecutive_failures`.
4. Carry dry run: before the claw moves towards an item, lift, verify shift, raise and transport are planned (not executed) with the payload
   mass (`tasks.max_payload_kg`) through the same height / trusted-volume / workspace / tension checks, on one pumped worker. Any refusal ->
   "unreachable: <leg>: <reason>", nothing moved, nothing gripped. Planning refusals after the grip closed, motion faults and pauses still abort.

Decision recorded: the two pre-motion refusals are `paused=True` (supervisor PAUSED, `resume` returns to READY); the lead accepted this.

## 3. Measured timings (HEAD tree, before the change)

`config/robot.sim3_34.json` (`fast3`), seed 3, LOCAL_ONLY, 15 validated points, lowest point z -0.5173 (the profile was changed to -0.4854 in
commit 3f2ece7 afterwards). One task of three items, `PumpGapMeter(couple=True)`, 0.3 s lease. Machine shared (load average 2-5).

| call | time |
|---|---|
| `plan_line_from` per task move (path check), 7-67 path points | 47-241 ms, median about 110 ms (scan 114-164, approach 47-202, descend 213-241, lift 106-159, verify shift 82-123, back over 99-107) |
| largest gap between two pumps over the whole task | 264 ms (0.9x the lease; worst stack in `kinematics.solve` called from the plan check) |
| `TrustedVolume` (Delaunay) | 0.1-0.2 ms for 15 points, 0.8-1.3 ms for 100, 3.9-4.3 ms for 400, 12 ms for 1000; `TaskRunner()` 0.4 ms |
| `pose_from_positions` | 1.3-1.8 ms |
| `vol.allows` / `ws.violations` / `predicted_tilt_rad` / `estimate_attitude` (sim) | up to 2.2 / 0.4 / 0.05 / 1.0 ms |
| `BlobDetector.detect` | 3-6 ms |
| YOLO-World inference and first-call model load | NOT measured (not installed). The tests use 1.0 s and 3.0 s sleeping detectors. |
| claw `/grip` POST and `/frame` GET | NOT measured (no hardware). The HTTP timeout is 1 s; the tests use 0.8 s. |

Every planned move is above the 60 ms (20 % of the lease) threshold, so all of them are pumped. Nothing else measured needs pumping.

After the change (new code, tube geometry z -0.4854, 0.3 kg payload): a whole task of two items, 81,997 pumps, largest gap 28 ms; the
same task with ClawGarmentPerception and a 1.0 s detector (5 calls on the pumped worker): 50,921 pumps, largest gap 53 ms (that gap was the
simulator's own `render_claw_view` on the command thread, not the detector).

## 4. Tests

New tests were checked against `git archive HEAD` (the unmodified tree): `test_task_pumping.py`, first 11 tests: 9 failed, 2 passed on HEAD
(the 2 are the intended controls: the unpumped detector latches LEASE, and exception propagation is unchanged). Evidence on HEAD: a 1.0 s detector gave a 1027 ms gap and
all four stations at (FAULT, LEASE); a 0.6 s CPU-burning detector 608 ms; the 3 s first-call load 3340 ms. New code: 26 ms, 31 ms, 22 ms, stations IDLE.

| file | result |
|---|---|
| `tests/cdpr/test_task_pumping.py` | 18 passed (16.6 s) |
| `tests/cdpr/test_task_reach.py` | 17 tests; 16 passed in 356 s (loaded), the 17th failed on a missing `import time/threading` of the test file (fixed); the two whole-task tests re-run alone: 2 passed (142 s). All 7 tests that were skipped in the earlier runs now execute. |
| `tests/cdpr/test_keepalive_fix_review.py` + `test_task_pumping.py` | 22 passed (4 + 18) in 28.6 s |
| `tests/cdpr/test_keepalive_pumping.py` | 19 passed, 1 failed in 99.9 s; the failure `test_a_full_simulated_startup_never_leaves_the_armed_stations_unpumped_for_a_third_of_the_lease` ended FAULT at the "expanded" stage ("motion not ready: clock uncertainty 5604 us"), with the largest pump gap 42 ms and no LEASE. Re-run alone: passed (READY, 171 s, largest gap 48 ms stall, limit 100 ms). Not reproduced; not investigated on HEAD (the startup is not bit-reproducible, `phone_app_review.md` F17). |
| `tests/cdpr/test_garments.py` | 8 passed in 284 s (210 s before my changes) |
| `tests/cdpr/test_system.py` | 11 passed |
| `tests/cdpr/test_three_station.py -k "task or move"` | 6 passed (31 deselected) |

Geometry used by each reported result: measurements in section 3 and reach runs 1-4 used the old lowest point (z -0.5173); reach runs 5-6, the
garments run and everything after commit 3f2ece7 used -0.4854. `test_three_station.py` uses `robot.sim3.json` (corner holes), not `_34`.

## 5. Why the 49 mm item error appeared (sim3_34, scan at 1.2 m): a test-rig artifact

`tests/cdpr/test_garments.py` renders the garment image with `render_claw_view(world, camera, cfg.claw.T_body_cam)`, the NOMINAL mount. The simulated
marker vision, and the camera-to-body correction the startup measures, belong to the TRUE mount (`SimCamera.T_B_C`: nominal rotated by a random 0.02 rad per axis).
Image and pose disagree by the mount tilt times the scan height. Item error against the exact model-frame position (probe `diag3.py`, item 0.12/0.10 m from the claw):

| claw height | sim3_34 seed 3, nominal render | true render | four-station seed 0, nominal | true render |
|---|---|---|---|---|
| 0.6 m | 26.8 mm | 11.9 | 15.6 | 11.9 |
| 0.8 m | 34.4 | 9.8 | 17.1 | 10.2 |
| 1.0 m | 43.6 | 9.3 | 19.2 | 7.1 |
| 1.2 m | 55.3 | 10.3 | 23.6 | 7.7 |
| 1.4 m | 58.5 | 8.4 | 28.5 | 5.9 |

Estimated mount vs true: 0.029 deg (three-station, the nominal mount is 2.609 deg off) and 0.006 deg (four-station, 0.974 deg off). Vision pose error: at most 3.5 mm in the
marker frame, tilt 0.02-0.31 deg, yaw at most 0.03 deg. The correction is applied once, with the right sign and frame. The true-render residual (6-12 mm, falling with height)
matches the parallax of the item's top face (5 cm above the z = 0 plane the pixel is mapped onto) plus 3-5 mm of noise. The simulated gripper reaches 60 mm, so the nominal render
left almost nothing for the grip on the three-station seed, and test_garments passes only because its mount error is smaller. Remedy (not done: not my file): pass `r.simcam.T_B_C`
in `test_garments._perception`. `test_task_reach.py` renders with the true mount and delivers two items through `ClawGarmentPerception` + `BlobDetector` on sim3_34.
The second-look refinement was NOT implemented: the true-render residual is below the 15 mm threshold you set.

## 6. Payload: set `tasks.max_payload_kg` to the item weight

With the default 0.9 kg the carry legs are planned at 1.35 kg total. On sim3_34 (old tube, transport height 1.467 m, `max_tension_n` 15 N) no grid position of the trusted volume was carriable even
at the full 15 N, so the dry run refuses every item as "unreachable ... tension infeasible" before any grip (before the dry run the same task picked the item up and aborted in the air at
`raise`, "12.1 N > 12.0 N"). With 0.3 kg the items are delivered. This was not recomputed for the 10.48 in tube.

## 7. Open items and limits

- The real detector load/inference times and the claw HTTP times are unmeasured; pumping them is based on the 1 s timeouts and the measured plan checks.
- `run_pumped` advances the simulated clock (a 20 ms `ctx.wait` step per pump) while the worker computes, so simulated time passes during a detection; harmless in the tests so far.
- An abort (`ctx.wait` raising) leaves the worker running until its call returns; if the operator starts a new task immediately, two threads could call the same detector at once (Ultralytics serialises predict internally in recent versions; not checked here).
- `TaskUnreachable` is recognised from the PlanError text prefix (`workspace:`, `tension infeasible`); a reworded PlanError would become a plain abort.
- `tasks.max_consecutive_failures` counts unreachable items; with three in a row the task pauses for the operator.
- Parallax of the item top could be removed by mapping box centres at `plane_z = item_h`; not done (shifts every perceived position by up to 10 mm).
- The unmodified `test_garments.py` rig has the nominal-mount render artifact; `test_system.py` uses `ModelFrameItemPerception` and is not affected.
