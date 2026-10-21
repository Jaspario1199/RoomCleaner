# Three-station mode: independent review (2026-10-21)

Reviewer: independent of the implementer. Scope: `git diff 9480887 HEAD -- roomcleaner/ config/ tests/cdpr/test_three_station.py`
(HEAD `d37e572`, which includes the lead's `start_background` change), `docs/THREE_STATION_MODE_SPEC.md`,
`docs/THREE_STATION_MODE.md`, `verification/three_station_mode_results.md`. Nothing under `roomcleaner/`, `config/`, `docs/`, `cad/` or the
implementer's tests was edited and nothing was committed. New files: `tests/cdpr/test_three_station_review.py` (tests that pin each
finding, plus checks that pass) and this report. All simulation evidence below is simulation, not hardware.

Simulation profile used for every full startup: the implementer's own fast helper (`tests/cdpr/test_three_station.py::fast3`, the
`robot.sim3.json` plant with 4 microsteps and 0.15 m/s moves, the 3 x 3 floor board), because a full-speed startup is 5 to 10 times slower. The four-station
comparison uses `simkit.fast_cfg()` (the same recipe for `robot.sim.json`).

## 0. Verdict for tonight's hardware test

**FAIL as shipped. PASS WITH CONDITIONS once H1 is fixed** (a one-line change in `Service._run`, section 2) and the conditions in section 5 are accepted.

* **H1 is a blocker, not caused by three-station mode and not fixed by the F3 change:** with the hardware loop setting the idle host loop owns the
  robot lock almost all the time, so `start`, `lower`, `disarm`, `recover` and `acknowledge` from the phone are refused with
  "busy with 'None'". Reproduced on this PC with a runtime that really sleeps (0 of 589 acquisitions); it is a model of the hardware path, not a hardware measurement.
* `pause` takes no lock, so the stop-in-place command still works while H1 is present; the power strip is still the emergency stop.
* The three-station physics, statics, workspace, start-point check, refusal-before-motion paths and the config guards are correct in everything I could check, and the
  F3 change does not starve the keep-alive in any state. Nothing I found lifts or moves a claw where three cables cannot hold it.
* What will probably happen tonight even after H1 is fixed: the startup can stop at PRETENSION with "claw dragged while tensioning" (M1: 3 of 8 simulated seeds,
  claw safe on the floor; Disarm then Start worked in the one case I tried), and the calibration drives every cable far outside the 40 degree outlet cone (M4).

## 1. What I ran

| what | result |
|---|---|
| `tests/cdpr/test_three_station.py` (implementer's 37 tests) | 37 passed, 467.8 s |
| `tests/cdpr/test_service.py`, `test_phone_app.py`, `test_phone_app_review.py` (includes the flipped F3 test) | 119 passed, 16 s |
| keepalive: `test_keepalive_pumping.py`, `test_keepalive_fix_review.py` | 23 passed, 1 failed on the first run: `test_a_full_simulated_startup_never_leaves_the_armed_stations_unpumped_for_a_third_of_the_lease` (a four-station, wall-clock-coupled full startup) saw pump gaps of 265 to 435 ms (limit 100 ms, lease 300 ms; one attempt ended with LEASE faults on all four stations) inside an SVD of the calibration fit's worker thread, **while another agent's multi-threaded pytest was using 1.4 cores of this 4-vCPU box**. Run alone on the quiet box it passes: HEAD largest gap 28 ms, 0 gaps above 40 ms (170.7 s); the pre-change commit 9480887 (git archive, same box) 33 ms, 0 gaps above 40 ms. So: environmental, but see L7. |
| `tests/cdpr/test_three_station_review.py` (this review) | 35 tests, all pass: 32 passed in 318.7 s on the first full run, then the 3 pins added afterwards (M4, M5 / L4, L5) passed on their own run |
| three-station startups, fast profile, 3 x 3 floor board, `robot.sim3.json` plant | seeds 0, 1, 2 (the implementer's tests, which I re-ran) and 4, 6 (mine): READY, LOCAL_ONLY ("slack probe was off"), no station fault. **Seeds 3, 5, 7: FAULT at PRETENSION** (M1). |
| four-station startups (`robot.sim.json`, fast profile, same board) | seed 0: READY (a test in the review file). Seed 5: READY (LOCAL_ONLY). Seeds 3 and 7: FAULT later, in CALIBRATION ("witness position RMS 8.4 mm > 6.0 mm", "witness errors 5.7x their predicted variance"), claw suspended: the simulated startup is not seed-proof in either mode. |
| move / refusal / lowering on a READY robot (seed 6) | 300 mm move completes (claw moved 0.30 +- 0.02 m); four targets toward D refused by the planner before any motion; `TrustedVolume` refuses them too; `lower` from a displaced pose (1.68, 1.5, 1.3 m) and from the end of calibration (1.07, 0.64, 1.61 m): PARKED, vision-confirmed on the floor, no fault, then `disarm` -> DISARMED |
| single-tag floor reference (no board), fast profile | three stations: seeds 0, 1, 2, 4 READY / LOCAL_ONLY with the reason "calibration not accepted: prior-dominated ...; predicted length sigma 7.3 to 8.1 mm > 5.0 mm" (not "slack probe was off"); seed 6 FAULT in INITIAL_LIFT ("claw rose 59 mm for 75 mm commanded", claw hanging). Four stations: seed 0 READY / LOCAL_ONLY (sigma 14.5 mm), seed 6 FAULT in CALIBRATION (witness RMS 11.3 mm). Pre-existing behaviour of the single tag, not specific to three cables. |
| own numerics (scratch scripts, results quoted below) | 3 x 3 solve vs `np.linalg.solve` and a hand calculation; margin guarantee on 3000 random poses per mass; grid of the usable region; outlet angles; hole exit angles; stiffness (Schur complement) |

## 2. Findings

| ID | Sev | What | Evidence | Suggested fix |
|---|---|---|---|---|
| **H1** | **High** (tonight) | **Operator commands cannot get the robot lock on the hardware loop.** `main()` runs the hardware loop with `real_sleep_s=0.0`. `idle_tick` holds `Service.lock` for 20 ms (twenty real 1 ms sleeps) and takes it again microseconds after releasing it. `_run` (start, lower, disarm, recover, acknowledge, resume, task) takes the same lock with `acquire(blocking=False)` on the HTTP thread, so it essentially never wins and the phone shows "busy with 'None'". Pre-existing; the F3 back-off only affects the opposite case (lock held by a command) and does not help. `--sim` uses `real_sleep_s=0.01` and hides it. | Scratch probe (not in the repo; the pin test is the same measurement over real HTTP): a runtime with real 1 ms sleeps, `start_background(real_sleep_s=0.0)`: **0 of 589** non-blocking acquires in 6 s; 23 of 590 with `real_sleep_s=0.001`; 48/590 with 0.002; 165/589 with 0.01. Blocking `lock.acquire(timeout=2)`: 20 of 20 succeeded within 4 to 25 ms. Pin: `test_h1_pin_...` posts `disarm` 100 times to the real threaded HTTP server: none accepted. | In `Service._run`: `if self.busy or not self.lock.acquire(timeout=0.3): raise CommandRefused(f"busy with '{self.busy}'")` (the refusal for a real running command stays immediate). Flip `test_h1_pin_...` to assert acceptance. Add a hardware-setting test that posts a command. |
| **M1** | Medium | **Three-station startups abort in PRETENSION with a false "claw dragged while tensioning" on 3 of 8 seeds (3, 5, 7 failed; 0, 1, 2, 4, 6 READY).** Mechanism, measured in the simulator: the pretension target ("just taut", from the take-up fit) overshoots the true lengths by 0.3 to 0.6 mm; at 7 N/mm that is already 2.5 N per cable, i.e. the whole weight (sum 7.7 N against 5.9 N), so the claw lifts off its jaws and tilts about 6 degrees (three of the box's four corners; the predicted 5.5 degrees). `floor_displacement` assumes "the claw rests on the floor: its tilt cannot change" (`perception.py:160`), so the tilt change reads as 15 to 18 mm of drag (limit 10 mm) while the claw moved 5 mm. Fail-safe (claw on the floor, RECOVERY_REQUIRED, stations holding), but the startup does not finish. The guide says the startup "ends READY" and has no row for this message. | Scratch diagnostic (seed 3): before pretension slack 17.9 / 20.8 / 23.0 mm, planned retraction 18.4 / 21.1 / 23.6 mm, after: stretch 0.34 / 0.38 / 0.34 mm, tension 2.47 / 2.81 / 2.46 N, truth displacement (-5.1, 1.2, -2.2) mm, tilt 5.97 degrees, reported drag 17.3 mm. The same seeds with four cables complete PRETENSION (seed 3: claw moved 4.3 mm, tilt 0.0 degrees; seed 5: 0.2 mm, 0.0 degrees; tensions 2.5 N on one cable / 2.2, 2.1, 0.8, 1.0 N), although those seeds fail later in CALIBRATION (seed 3, 7) or are READY (seed 5). After the abort `disarm` then `start` reached READY (seed 3). Pins: `test_m1_pin_*` (seeds 3, 5, 7: deterministic, 10 s each). | Either stop the pretension short (pay out 1 to 2 mm, let the lift packets take the weight), or make the drag watch tilt-aware in three-station mode (the lift-off tilt is predictable: `Attitude.solve`). Add to guide section 8: `pretension: claw dragged while tensioning` -> Disarm (type claw_supported), then Start again. |
| **M2** | Medium | **The misspelt-key guard is a heuristic and misses most misspellings.** `_parse_active` refuses a stray top-level key only if it contains both "active" and "station" (any case). `stations_actve`, `stations_activ`, `active`, `stations_enabled`, `enabled_stations`, `three_station`, `stations.actve` all load as FOUR active stations, silently. On hardware this is stopped only because D has no address (SystemExit); with a fourth address filled in, D would be configured and armed with no cable. The guide says "a misspelt key" is refused. | `test_m2_pin_*` (7 keys). `load_config` has no unknown-top-level-key check at all. | Refuse every top-level key that `load_config` does not read (keys starting with `_` excepted). Then the heuristic is unnecessary. |
| **M3** | Medium | **Guide steps 3 and 4 share `data/cdpr`.** The simulator rehearsal and the real service both default to `--data data/cdpr`; the guide never mentions `--data`. A rehearsal that ends READY (or any aborted start) persists `claw_supported = false`; the next launch enters RECOVERY_REQUIRED ("host restarted while the claw may be suspended"), where `start` is refused, and it also loads the simulator's `model.json` (same A/B/C ids). `recover` then refuses for lack of valid references and the operator is sent to `lower`; the Setup calibration card shows the simulator's `calibration.json` until a real startup overwrites it. In this working copy `data/cdpr/state.json` is already RECOVERY_REQUIRED (a stale four-station simulator run, gitignored). Mode switches themselves are reconciled safely (checked both ways, no crash, no stale four-cable model used: below). | `test_d1_pin_*`. Manual: 4-station READY directory opened by a 3-station host: "saved model is for stations A/B/C/D ... ignored", state RECOVERY_REQUIRED, ledger A/B/C, `recover` refuses "no calibrated model: use 'lower'". | Guide: give the rehearsal `--data data/sim` and the real run `--data data/hw` (or delete `data/cdpr` before the real run). Optional: refuse a data directory whose `state.json` was written by `--sim`. |
| **M4** | Medium (known open item) | **The calibration drives every cable far outside the 40 degree outlet cone.** Start point 40.3 to 41.7 degrees (A, B 41.7; C 40.3: the guide's point-claw numbers; 39.6 to 40.9 with the real attachment points and tilt). Over the poses of the calibration box (start +-0.8 m, z 0.59 to 1.6 m, 0.45 kg) the cable leaves at up to **68 degrees**, and **84 to 87 %** of the poses are above 40 degrees at each station (usable volume: up to 78). The planner has no outlet limit (stated in the results as not done); the guide says "check the outlet before the claw lifts" but not what to look for or when to stop. | `e11` grid: 1848 feasible calibration-box poses, max 67.9 / 68.0 / 67.1 degrees, share above 40 degrees 0.86 / 0.87 / 0.84. | Decision for Jasper before tonight (outlet type). If the outlets are the 40 degree bench ones: run the first calibration with one person watching each outlet's line at the collar, Pause on any rubbing, and shrink `calibration.expanded_box_m` for the first run (the box is what sends the cables to 68 degrees). |
| **M5** | Medium | **The guide says nothing about the floor reference.** All the simulated three-station evidence uses the printed 3 x 3 board; the guide only says "marker flat on the floor under the camera". With the single tag the simulated startup ends READY / LOCAL_ONLY with a different reason ("calibration not accepted: prior-dominated ...; predicted length sigma 7.3 to 8.1 mm > 5.0 mm", not "slack probe was off") in 4 of 5 three-station seeds and aborts the lift in the fifth (section 1). Existing project documents already call the board "the validated floor reference". | single-tag runs in section 1; the guide's step 7 and section 6 name only the slack-probe reason. | Say in the guide whether tonight uses the board (`marker.board_layout_file`, `tools/print_floor_board`) or one tag, and what outcome to expect with one tag. |
| **M6** | Medium | **The first lift may abort on tilt, and nobody has measured the centre of mass.** Three of the box's four corners carry the claw, so it hangs tilted by CoM-offset / 0.196 m: 5.5 degrees at the start point on the CAD CoM, against the 8 degree abort (`startup.max_tilt_rad`). `claw.com_body_m` is a CAD estimate "without electronics (VERIFY)". A CoM error of about 9 mm in the worst direction (toward the empty D corner) reaches 8 degrees; 15 mm gives 9.4 degrees. The abort is safe (stations hold, the claw hangs a few centimetres up, `lower` brings it down) but it stops the test. | `e12` scratch run, `Attitude.solve` at the start point, 0.45 kg: shift 4 mm -> 4.4 to 6.5 degrees; 8 mm -> 3.4 to 7.6; 10 mm -> 2.8 to 8.1; 15 mm -> 1.5 to 9.4. The guide mentions VERIFY and the 2.5 degree margin but does not ask for a measurement. | Measure the CoM in x and y (hang or balance test, +-3 mm) before tonight and enter it in `claw.com_body_m`; if the tilt is high, check which side the battery is on. |
| L1 | Low | **The guide and the results attribute the two edge margins to the wrong sides.** Guide section 5: "0.31 m from the A-B wall side and 0.30 m from each diagonal side (0.235 / 0.225 m for 0.6 kg)". The code gives the A-B wall side the smaller margin: 0.299 m (0.225 m for 0.6 kg) and each diagonal 0.314 m (0.235 m): margin = lambda_min x altitude, the altitude over A-B is 2.643 m, over the diagonals 2.771 m. The implementer's own test asserts `edge_margin_m["A"] == 0.235`. Sizes are right, sides swapped. | `test_the_margins_are_031_...`, `test_l1_pin_*`; same swap in results section 3. | Swap the two numbers in the guide and results. |
| L2 | Low | Guide numbers that do not match the code: "the room centre is 2 ft closer to C" is 0.44 m = 1 ft 5 in (section 7 of the same guide says 0.44 m); "the usable area reaches about 0.6 m from the start point" is 0.5 m toward the near wall, 1.0 m sideways and 1.07 m toward C (the calibration box is +-0.8 m). | `test_l2_pin_*`; grid x 0.7 to 2.7, y 0.4 to 2.0 around (1.68, 0.93). | Correct both sentences. |
| L3 | Low (mechanical, unverified) | The C and A lines leave the box's corner holes far off the hole axis. With the hole rising 21 degrees outward and the claw at yaw 0 / +20 / +25 degrees at the start point: A 30 / 40 / 43 degrees, B 30 / 27 / 28, C 46 / 35 / 33 (four stations: about 24 degrees each). The claw settles to yaw +11 to +25 degrees by itself. No line crosses the box, as the guide says, but nobody has shown the 18 mm holes accept a 40 to 46 degree bend of the Dyneema without abrasion. | computed from `attachment_points_body_m` and the CONTROL_SYSTEM_V1 hole description. | Look at the C and A holes after the first lift; no software change. |
| L4 | Low | The guide says "`claw.mass_kg` (the budget is 0.45 kg)" and that the edge margin is computed from it. A mass entered above the real one lowers the real tension at the edge below the 0.5 N floor (0.45 entered for a real 0.375 kg: 0.42 N at the margin; still positive). | arithmetic: T_min >= lambda_min m_real g. | Say "enter the weighed mass". |
| L5 | Low | The start-point check in INITIAL_LIFT is skipped without a word when `ctx.ws is None` (`startup.py:847`). Not reachable after the take-up fit (`apply_result` always sets it), so no hole today. | code reading. | Treat `None` as a refusal. |
| L6 | Low | A deleted `anchor_room_m` entry for an active station silently becomes the room corner of that id (C -> (3.35, 2.74)); the start point moves 0.5 m+ and nothing is reported. The shipped example sets all three. | `test_a_station_left_without_an_anchor_entry_...`. | Refuse a null anchor for an active station in three-station mode. |
| L7 | Low (operations) | **The pump gaps depend on the host PC being quiet.** With a second CPU-heavy process on a 4-core machine the calibration fit's SVD (BLAS threads) stalled the keep-alive pump for 200 to 435 ms against a 300 ms lease, in 4 of 4 full four-station startups, and in one of them all four stations latched a LEASE fault; with nothing else running the same test shows 28 ms and 0 gaps above 40 ms, at HEAD and at the pre-change commit alike. A three-cable fit is smaller (12 + 3 unknowns instead of 16) but this is not measured on hardware. | keepalive runs above. | Close everything else on the host PC (browser, CAD, detectors) during the startup; optionally `OPENBLAS_NUM_THREADS=1`. |

No other High or Medium finding.

## 3. The seven checks

### 3.1 Safety (highest priority)

* **Never lifted or moved where three cables cannot hold it.** Every route goes through `Workspace.violations` (which now contains the margin-shrunk triangle) and/or the exact
  `tension_distribution` (3 x 3, every `T_i >= 0.5 N`): planner `trajectory._check_path` (also with +-path acceleration and the 2 m/s2 allowance), task layer
  (`TrustedVolume.allows` and `plan_line_from(ws=...)`, `tasks.py:83,121`), calibration poses (`_feasible`, `startup.py:1139`, plus `plan_line_from(ws=ctx.ws)` for each move),
  work and margin volumes (`startup.py:1310,1322`), the bead approach (`homing.py:123,127`), lowering (`supervisor.py:432`, planned with `ws`), and the INITIAL_LIFT start-point check
  (`startup.py:847`, before any pretension or lift). Run: four targets toward D refused by the planner with the "workspace: floor point ... edge opposite station" message, positions and motion id untouched; the task layer's volume refuses them too.
* **Not covered by a feasibility check:** the final equal-payout lowering packets and the `lower` fallback "refused ... using cable packets" (`supervisor.py:435`, packets at `:455-470`) (unchanged
  design; planned lowering is used in the normal case, and in three runs of `lower` from READY (end of calibration, displaced pose) it parked correctly), the lift packets themselves (vertical from an inside point:
  lambda is constant, so T_i >= lambda_i W holds), and the take-up (claw on the floor).
* **3 x 3 solve.** `tension_distribution` n = 3: `np.linalg.solve(u.T, m(a+g))`, feasible iff every `T_i >= t_min`. Matches my own `np.linalg.solve` for 120 random poses and accelerations
  (0, +2, -2 m/s2) to 1e-9 (`test_three_cable_tensions_match_...`). Hand calculation at the centroid, 0.45 kg, z = 0.517 m: T_i = (W/3) L_i/(H - z) = 1.9708 / 1.9708 / 1.9300 N
  (L = 2.780 / 2.780 / 2.723 m, H - z = 2.0762 m), identical to the code and to the guide's "1.9 to 2.0 N". Room centre: 1.51 / 1.59 / 2.59 N (guide: 1.5 N minimum).
* **No hidden four-cable fallback.** AST scan of `roomcleaner/cdpr` (`test_no_loop_or_array_over_stations_...`): the only `range(4)` left are the four corners of a marker tag; the `(4, 3)` literals
  are the config's attachment array of the file (the active rows are picked by id) and a render quad; no `[:4]`, `zeros(4)`, `reshape(4`. `IDS` / `STATION_IDS` / `"ABCD"` appear only in
  config (applied on top of the active set), `homing` (a label default; the caller passes the id), `calibration` / `startup` (ids of old saved files) and the default ledger of
  `TrustLedger()`, which no production path constructs (`for_ids` everywhere). The literal `"D"` appears only in those constants, in the default anchor corners, in the dataclass defaults `Workspace.ids` / `RobotModel.ids` (production constructors pass the active ids: `kinematics.py:412`, `trajectory.py:342`) and in the app's JavaScript fallback for a status without `stations_active`.
* **D is never configured, armed, addressed or polled.** Simulator: bring-up plus 1 s of pumping sends nothing to or from D, D has no node, link, ledger entry or firmware parameters
  (`test_station_d_is_never_addressed_...`). UDP: `station_addresses` returns three entries even if D has an address in the file; a `*` send reaches exactly those three sockets and
  `send("D")` raises `KeyError`.

### 3.2 Four-station behaviour unchanged

* No `stations_active` key -> `_parse_active` returns all four; `start_point_xy` returns `room/2` (as before); `checklist_for` returns `CHECKLIST`; `Coordinator(ids=None)` -> `cfg.ids`; `World` defaults are `(0.08,)*4` and `(1.0,)*4` as before.
  Every changed four-station branch I found is behaviour-neutral: `tension_distribution` (n = 4 is the old LP with `n` for 4), `Calibrator` (`for drop in (None, *range(4))`; `if self.n >= 4` branches), `supervisor._fk_slack_aware` (`n >= 4`), `check_capture(sid=None)`,
  `bead_workspace` (`dataclasses.replace`), `Plan` / `_noop_plan` reshape by column count, ledger `restrict_to` (a ledger that already covers the ids is left untouched).
  Intended differences only: additive status keys, additive calibration JSON keys, and `set_room` with an unknown station id now answers 400 instead of a KeyError / 500.
  No default value changed (`git diff` of `config/` is two new files; `robot.example.json` and `robot.sim.json` are untouched).
* A four-station simulated startup (`robot.sim.json` fast profile, seed 0): READY, all four stations valid, no fault, `active_stations == ABCD`, no `inactive_stations` key
  (`test_four_station_startup_still_reaches_ready_...`, plus seed 5 READY by script). The implementer's full suite (563 passed) was not re-run.

### 3.3 Config validation

Refused with a clear message (`test_config_checks_...`, scripted run of 40 variants): two ids, one id, none, duplicates (also with five entries), an unknown id, lowercase ids, a string / dict / ints instead of a list,
`active_stations` / `station_active` / `stationsActive` / `stations-active` and 8 other close spellings, both spellings that differ, collinear, coincident, vertically stacked, a sliver (shortest altitude 0.24 m refused, 0.26 m accepted), a
tension floor of 1/3 of the weight or more. Accepted: all four, null, any order (sorted A-D). **Not refused: misspellings the heuristic does not recognise (M2), a null anchor for an active station (L6).**
Other-mode state: a four-station or other-trio `model.json` is ignored with a logged reason (ids compared), the ledger is reconciled (`restrict_to`), `recover` refuses without a model, nothing crashes (checked here with a four-station READY directory opened by a three-station host, and by the implementer's test the other way). The stale-data trap is M3.

### 3.4 Edge margin

`T_i = lambda_i W L_i/(H - z)` with `L_i >= H - z`, hence `T_i >= lambda_i W`: `lambda_i >= T_floor/(m g)` guarantees `T_i >= T_floor` at any height for anchors at one height. 3000 random poses per mass, half exactly on the boundary
(`test_the_edge_margin_keeps_every_tension_...`): smallest point-claw tension 0.77 N (0.45 kg; floor 0.5 N), with +2 m/s2 0.93 N, with -2 m/s2 0.62 N (the theoretical floor for -2 m/s2 is 0.40 N,
only reached under an anchor); the real spaced claw (84 mm square attachment, CoM, predicted tilt) smallest 0.68 / 0.82 / 0.54 N for 0, +2, -2 m/s2. Same for 0.375 and 0.6 kg. The stated margins are right in size:
0.45 kg -> lambda 0.1133 -> **0.314 m from each diagonal side, 0.299 m from the A-B wall side**; 0.6 kg -> 0.235 / 0.225 m (the sides are swapped in the documents, L1). Usable floor area 1.87 m2 = 20.3 % (0.45 kg) and 2.45 m2 (0.6 kg) on my own 0.1 m grid,
x 0.7 to 2.7, y 0.4 to 2.0: as stated.

### 3.5 Simulation

READY on seeds 0, 1, 2 (implementer's tests, re-run) and 4, 6 (mine) (LOCAL_ONLY, reason "slack probe was off", no station fault, D nowhere), FAULT at PRETENSION on seeds 3, 5 and 7 (M1). **Seed 7, the one you asked for, does not reach READY**; the 300 mm move
and the refusal toward D were therefore checked on seed 6 (a READY robot): completed / refused before any motion, as in section 1. Fast profile throughout.

### 3.6 Operator guide

Verified against the code: the nine-step flow and CLI flags (`--sim --config`, `--config --host`); the terminal line "THREE-STATION MODE: active cables A/B/C" (printed by the startup); the checklist texts and the Setup note (verbatim); the start point (1.68, 0.93) m = 5 ft 6 in along the wall and 3 ft 0.65 in out; the facing
(camera bay at +y, A and B holes at -y: `CONTROL_SYSTEM_V1` section 3 and `camera_in_body`); `marker.heading_prior_rad` -2.645 rad = atan2 from the start point to A (1e-3; the sim3 profile has -2.6451; the hardware example leaves it null, as the guide says to enter it); the config keys of section 3;
all six refusal messages of section 8; `startup.max_tilt_rad` 8 degrees; z 0.59 to 2.19 m; the tensions 1.9 to 2.0 N / 1.5 N; the start angles 41.7 / 41.7 / 40.3; the yaw stiffness ratio (my Schur complement: 0.30 / 0.43 N m/rad against 1.0 / 1.5 for four cables at z 0.7 / 1.3 m); the tilt 5.5 degrees; the usable area.
Wrong or misleading: L1, L2, L4, M3, M5, the missing row for M1, and "ends READY" (step 7) which holds for 5 of 8 simulated seeds.

### 3.7 Tests

Section 1. The implementer's 37 and the 119 service / phone-app tests pass. My file adds the pins and checks listed in section 4.

## 4. What the review tests do

`tests/cdpr/test_three_station_review.py`. PINS pass today and say how to flip them: H1 (`test_h1_pin_*`), M1 (`test_m1_pin_*`), M2 (`test_m2_pin_*`), M3 (`test_d1_pin_*`), M4 (`test_m4_pin_*`), M5 / L4 (`test_m5_l4_pin_*`), L1, L2, L5. M6 has a check, L3 / L7 no test.
`test_h1_the_suggested_fix_is_sufficient_*` re-compiles `Service._run` in memory with the suggested one-line fix and shows the first post is accepted (it skips itself once the real code no longer has the non-blocking acquire).
CHECKS (must keep passing): F3 keep-alive (idle / long command / hand-over / persistent error), config guards, 3 x 3 vs `np.linalg.solve` and hand calculation, edge margin at 0 / +2 / -2 m/s2 for the point and the real claw, margin sides,
the guide's start point and heading prior, guide refusal texts and keys, AST scan for four-cable literals, D never addressed (sim and UDP), READY robot 300 mm move + refusal + `lower` + `disarm`, four-station startup READY, the 9 mm centre-of-mass margin of the first lift (M6).

## 5. Conditions for PASS WITH CONDITIONS (tonight)

1. Fix H1 and re-test on the hardware loop setting (post `lower`/`start` from the phone while idle).
2. Use the printed floor board (M5) or accept that a single tag may abort the lift; expect `pretension: claw dragged while tensioning` on some starts (M1): Disarm, check the claw sits on the floor, Start again.
3. Decide the outlet question (M4) before the first calibration; one person at each outlet; keep the first calibration box small.
4. Nobody under the robot; with no spare cable any station fault drops the claw from up to 1.6 m: pad the floor under the calibration volume.
5. Separate `--data` directories for rehearsal and hardware (M3); enter the weighed claw mass (L4); correct the margin sides (L1) so the figures Jasper reads match the app (`workspace.edge_margin_m`).
6. Nothing else CPU-heavy on the host PC during the startup (L7); measure the claw's centre of mass first (M6).

## 6. F3 change (`start_background`)

`idle_tick` returns False without touching the stations when a command holds the lock; the loop now sleeps `BUSY_BACKOFF_S` = 5 ms and retries, and also backs off after an exception.
Starvation check (`test_f3_fix_*`, hardware setting, runtime with real 1 ms sleeps, lease 0.3 s, ping every 20 ms): longest silence to the stations 28 ms idle, 27 ms across a 1.2 s command, 26 ms at the hand-over (31 / 36 / 95 ms in an earlier run on a loaded PC); 232 `idle_tick` calls in 1.2 s while the lock was held. The longest silence to the stations is far below the lease in all three states, the loop does not spin
(about 1 call per 5 ms while the lock is held; before: millions per second), the 5 ms is at most one ping period at the hand-over, and an exception in `idle_tick` every time is reported in `last_error` and retried every 5 ms rather than spinning or dying.
The one thing the change does not do is let a command in (H1).

## 7. Not reviewed / limits

Firmware and the Python station core (unchanged by spec), CAD, hardware behaviour of anything, Wi-Fi / UDP loss, a real claw tilt and yaw (the CoM is a CAD estimate: `claw.com_body_m` says VERIFY), the full 563-test suite
(not re-run; I ran the files named in section 1), and the full-speed startup profile (fast profile only).
