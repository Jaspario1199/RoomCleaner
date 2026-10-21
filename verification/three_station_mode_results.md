# Three-station mode: implementation and results (2026-10-21)

Scope: host software and simulator (`roomcleaner/cdpr`), config profiles, the phone app, and the operator guide
`docs/THREE_STATION_MODE.md`, exactly per `docs/THREE_STATION_MODE_SPEC.md`. Firmware, CAD, `docs/presentation`,
`DECISIONS.md`, `DESIGN_STATE.md` and the four-station default values are untouched. This work committed nothing (a WIP snapshot commit,
`ec2cf6d`, was made of the tree by another process during the session; the commit before this work is `9480887`).
Simulation evidence only: nothing here is hardware evidence, and the hardware claw is not measured (`claw.com_body_m` says VERIFY).

## 1. Summary

* `stations_active` (spec: `stations.active`; the same key, also accepted as `"stations.active"`) selects 3 or 4 of A-D;
  absent = all four. `cfg.stations` / `cfg.ids` are the ACTIVE stations in A-D order, so every loop over them in the
  coordinator, supervisor, trust ledger, startup, calibration, planner, simulator and phone app runs over the active set;
  `cfg.inactive_stations` keeps the other records (never configured, armed, addressed, simulated or polled; not a fault).
* Three cables: unique 3 x 3 tension solve, all `T_i >= min_tension_n` or infeasible; workspace = triangle of the active
  anchors with a tension-floor edge margin; attitude model, calibration, trust and startup run over three attachment points;
  the start point is the centroid of the active anchors' floor projection.
* Simulated full startups with `config/robot.sim3.json`, seeds 0, 1, 2 (and 0.45 / 0.375 kg claws): READY, trust `LOCAL_ONLY`
  with the single reason "slack probe was off" (the same as the four-station simulator), no station faults, every active
  reference valid. With `startup.slack_probe: true`: READY, **VERIFIED (basis margin)**.
* A 300 mm move inside completes (3 seeds); moves toward the missing corner are refused before any motion (3 seeds); a claw put
  outside the triangle is refused in INITIAL_LIFT before it lifts.
* Edge margin: `lambda_i >= T_floor / (m g)`; for the budget claw (0.45 kg) **0.31 m / 0.30 m** from the sides of the
  recommended triangle (0.235 / 0.225 m for the simulator's 0.6 kg). Usable floor area 1.9 m2 (20 % of the room) for 0.45 kg,
  2.4 m2 (27 %) for 0.6 kg; the triangle itself is 4.3 m2 (47 %). The spec expected "roughly half the room": that is the
  triangle; the tension floor takes the rest.
* Findings that need a decision (section 9): the 40 degree bench outlet does not cover even the start point (41-43 degrees);
  the three-corner attachment tilts the claw 5.5 degrees at the start (2.5 degrees under the 8 degree lift limit).

## 2. What changed (file:line, final tree)

| area | change | where |
|---|---|---|
| config | `STATION_IDS` (all four records are still required, in order) / active-set parse and validation (type, duplicates, unknown ids, 3-4, misspelt-key guard, both spellings) | `config.py:39`, `_parse_active` 656 |
| config | triangle check: collinear / coincident / sliver (shortest altitude < 0.25 m) / tension floor >= 1/3 of the weight | `triangle_geometry` 685, `_check_triangle` 695, called at 908 |
| config | `SystemConfig.stations` = active, `.inactive_stations`, `.record()`, `.all_stations`, `.station_index()`, `.max_slack_for()`, `.start_point_xy()`, `.tension_floor_fraction()`, `attachment_points()` per active station; `config_to_jsonable` adds `stations_active` | `config.py:479-560`, 750, 799 |
| statics | `Geometry` over n = 3 or 4 cables; `tension_distribution`: unique 3 x 3 solve for n = 3, LP unchanged for n = 4 | `kinematics.py:173-190`, `259-300` |
| workspace | `Workspace` carries `ids`, `tri_xy`, `lam_min`; `triangle_violation`; `workspace_from_config` builds it for 3 stations; `barycentric_xy` | `kinematics.py:297-330`, `388-411` |
| planner | `RobotModel.ids` from the config; `Plan` columns = active stations; no-op / `plan_line_from` / `plan_cable_move` reshape by column count (the NOOP_CABLE_M and segment-floor code is untouched) | `trajectory.py:166, 228, 261, 304, 342` |
| calibration | `Layout(n_st)`, `CableLengthModel(ids)`, `Calibrator.ids/.n`, no slack hypothesis and no slack-drop witness / boundary solutions for n = 3, identifiability condition number, `CalibrationResult.ids` (+ persistence, JSON), start-point marker prior | `calibration.py:136, 178, 222, 241, 268, 327, 543, 829, 932` |
| startup | `RobotContext.ids`, `StartupSequencer.ids/.n`; `max_slack_for`; three-station log line and measurements; start-point check in INITIAL_LIFT; work/margin volumes skip points outside the triangle; saved model of another mode ignored; ledger restricted to the active set | `startup.py:265-268, 362, 722, 771, 843, 1303, 1315` |
| supervisor / trust | polls, restores, disarms, recovers, lowers over `ctx.ids`; `_fk_slack_aware` drops no cable with 3; `TrustLedger.for_ids`, `.restrict_to` (a ledger saved by the other mode is reconciled) | `supervisor.py:117, 150, 200, 336, 492`, `trust.py:104-130` |
| homing / coordinator | station labels and `ref` vectors from the model ids; `bead_workspace` keeps the triangle (`replace`); `Coordinator.ids` default = `cfg.ids` | `homing.py:97, 241`, `coordinator.py:66` |
| simulator | `World` built with the active cables (all `4`s are `n`), `default_world` starts the claw at the centroid, `SimRobot` ledger over the active ids | `sim/world.py:59, 742, 748`, `sim/harness.py:72` |
| service / app | `checklist_for`, `start_point_text`, `workspace_summary`, new status keys, `station_addresses` (active only), `set_room` accepts any record and refuses a degenerate triangle, `TrustLedger.for_ids` | `service.py:70-120, 266-278, 298, 839-860, 872` |
| app | tiles from `status.stations` (columns = count), mode note, start-point line, anchor labels from `res.ids`, condition number | `static/app.js:215, 253-254, 337-339`, `static/index.html:97-98` |
| configs | `config/robot.sim3.json`, `config/robot.three.example.json` (active = A, B, C; C prior `[1.6764, 2.6932, 2.5932]`; sim heading prior -2.6451 rad) | new |
| docs / tests | operator guide, this report, `tests/cdpr/test_three_station.py` (37 tests) | new |

Unchanged by design: all four-station default values, `NOOP_CABLE_M` / tiny-move code in `trajectory.py` and `coordinator.py`,
firmware, trust and accept rules (VERIFIED only if k x sigma fits the margins).

## 3. Edge margin from the tension floor (derivation)

Point claw of weight W = m g, outlets at one height H, claw z below them, floor position p in the triangle of the outlets with
barycentric coordinates lambda_i(p). Force balance (3 x 3) gives `T_i = lambda_i W L_i / (H - z)` (verified to 1e-9 against the
direct solve in `test_three_cable_tensions_follow_the_barycentric_formula`). Since `L_i >= H - z`, `T_i >= lambda_i W`, so
**`lambda_i >= T_floor / (m g)` guarantees `T_i >= T_floor` at any height** (`test_the_edge_margin_is_sized_...`, 400 random
poses). The distance from edge i is `lambda_i x altitude_i`. `Workspace.lam_min = motion.min_tension_n / (claw.mass_kg g)`; the
exact tension solve (`T_i >= t_min`, including +2 m/s2 and the path acceleration) still runs on top of it at every point of every plan.

| claw mass | lambda_min | margin from the A-B side / A-C, B-C sides | usable triangle area | usable footprint on a 0.1 m grid |
|---|---|---|---|---|
| 0.60 kg (simulator) | 0.085 | 0.235 m / 0.225 m | 2.39 m2 | 2.45 m2 = 27 % of the room, x 0.5-2.8, y 0.3-2.2 |
| 0.45 kg (budget) | 0.113 | 0.314 m / 0.299 m | 1.87 m2 | 1.87 m2 = 20 %, x 0.7-2.7, y 0.4-2.0 |
| 0.375 kg (estimate) | 0.136 | 0.377 m / 0.359 m | 1.51 m2 | not gridded |

Triangle A (0.05, 0.05), B (3.3028, 0.05), C (1.6764, 2.6932): sides 3.253 / 3.103 / 3.103 m, altitudes 2.643 / 2.770 / 2.770 m,
area 4.299 m2 (46.7 % of the 9.197 m2 floor). The bound uses `sin(elevation) <= 1`, so it is 15-25 % larger than the exact
height-dependent boundary; the other margins are as today (0.2 m walls, 0.4 m ceiling -> z <= 2.19 m, floor clearance, task cap 1.6 m).
Anchors at unequal heights change the formula slightly (the exact tension solve covers that).

## 4. Tensions at the start point (recommended layout, claw on the floor, z = 0.517 m; static / with +2 m/s2)

| claw mass | centroid (1.676, 0.931): min-max | room centre (1.676, 1.372): min-max | both accepted by the startup's check |
|---|---|---|---|
| 0.60 kg | 2.51-2.65 N / 3.02-3.19 N | 2.01-3.46 N / 2.42-4.16 N | yes |
| 0.45 kg | 1.88-1.98 N / 2.27-2.39 N | 1.51-2.59 N / 1.82-3.12 N | yes |
| 0.375 kg | 1.57-1.65 N / 1.89-1.99 N | 1.26-2.16 N / 1.51-2.60 N | yes |

(`motion.min_tension_n` 0.5 N, 0.75 x `max_tension_n` 15 N.) Both points are inside the margin-shrunk triangle (barycentric
1/3 each, and 0.25 / 0.25 / 0.50). The centroid was chosen, as the spec says; the room centre would also be accepted
(`marker.position_prior_room_m` moves it).

## 5. Tests

`tests/cdpr/test_three_station.py`, 37 tests, TBD_TESTS_NEW. They cover the spec's acceptance list:

1. Config: default four unchanged (also the checklist and start point), three accepted for both profiles with D kept as a
   record and no address requirement, sorted order, the spec spelling, null, two / one / zero ids, duplicates, unknown ids,
   bad types, misspelt key, collinear / coincident / sliver anchors, an impossible tension floor, four stations exempt.
2. Statics: tensions equal `np.linalg.solve(u.T, w)` (7 poses x 3 accelerations), independent of the bounds; barycentric formula;
   outside the triangle (5 points x 3 heights) and too close to an edge infeasible; margin guarantee; the rigid-body attitude model
   converges at every usable grid pose and yaw (3 yaws) and flags a pose outside the triangle.
3. Simulation (`robot.sim3.json`, fast variant of simkit.fast_cfg: 4 microsteps, 0.15 m/s): the world, network, coordinator, ledger
   and calibrator contain A, B, C only; startups for seeds 0, 1, 2: READY, LOCAL_ONLY with a reason, no faults, all valid, D nowhere,
   fit over A, B, C with the identifiability report and the persisted `calibration.json`; 300 mm move completes (3 seeds, the real
   claw moves 0.30 +- 0.02 m); a move toward D is refused before motion (3 seeds; no motion id, positions untouched, all IDLE); a claw
   placed outside the triangle is refused in INITIAL_LIFT with the start point in the message and never lifts.
4. Wiring: with three cables the slide-direction check has no spare bearing; swapping the cables of A and B, or A and C, is still caught in
   SLACK_TAKEUP (RMS 8.0 / 8.1 sigma against the limit 3; four stations 7.8), test `test_swapped_station_wiring_is_still_caught_with_three_cables`.
5. Service and app: `/api/status` lists A, B, C only, the checklist names the active cables and the start point, the Setup note and
   start-point line exist in the page and the script, four stations keep the old checklist and keys; `set_room` edits any record.
6. Hardware wiring: `station_addresses` and the UDP transport cover the active stations only; modes switching over a saved
   ledger / model / state do not crash and reconcile.

Full `tests/cdpr` suite (background, 7200 s timeout): TBD_SUITE

## 6. Simulated startups (config/robot.sim3.json, fast variant, FloorBoard 3x3 floor reference, claw 0.6 kg)

| seed | outcome | level (reason) | take-up A / B / C (mm) | bearing RMS (sigma) | lift cmd / seen (mm) | witness chi2/dof, n | max length sigma | station faults | eq failures |
|---|---|---|---|---|---|---|---|---|---|
| 0 | READY | LOCAL_ONLY (slack probe off) | 89.5 / 68.2 / 43.0 | 0.14 | 85 / 76.4 | 0.23, 7 | 3.0 mm | none | 0 |
| 1 | READY | LOCAL_ONLY (slack probe off) | 45.8 / 57.1 / 39.0 | 0.14 | 80 / 78.2 | 0.34, 7 | 2.3 mm | none | 0 |
| 2 | READY | LOCAL_ONLY (slack probe off) | 89.5 / 44.0 / 28.9 | 0.07 | 85 / 79.2 | 0.26, 7 | 2.6 mm | none | 0 |

Each ran 92-99 s wall, 38 calibration samples (31 fit, 7 witness), 15 / 15 validated work-volume points, calibration accepted
with no reasons. The four-station simulator (seed 0, same fast profile) is LOCAL_ONLY for the same "slack probe was off" reason
(and, for that seed, a predicted length sigma of 5.1 mm against the 5.0 mm limit; the three-station runs are 2.3-3.0 mm).

* **Slack probe on** (`startup.slack_probe: true`, seed 0, 237 s wall): READY, **VERIFIED, basis "margin"**; k x sigma = 60 mm of the
  400 mm ceiling margin and 102 mm of the 200 mm wall margin over 100 commanded-workspace poses; 114 probed readings, 0 skipped, median slack 0 mm,
  max 0.9 mm (with three cables every cable of a hanging claw is taut, so the probe finds nothing to correct; it costs time).
* **Light claws** (0.45 kg, 0.375 kg; seed 0): READY, LOCAL_ONLY (same reason), calibration accepted, 15 / 15 validated points,
  38 samples, poses 0.59-1.61 m high: the bigger margin (lambda 0.113 / 0.136) still leaves enough feasible visible poses.
* Take-up sequence runs A, B, C one at a time; D is never touched.

### Identifiability (calibration fit over A, B, C, 9 anchor + 3 zero-length unknowns)

| run | params | smallest / largest singular value (prior-normalised) | condition number | weak directions | sigma anchor x, y, z (mm) | sigma L0 (mm) |
|---|---|---|---|---|---|---|
| 3 stations, seed 0 | 12 | 1.96 / 479 | 244 | none | A 16.4, 4.5, 12.9; B 7.0, 8.5, 8.1; C 2.5, 9.3, 7.6 | A 20.7, B 13.0, C 11.6 |
| 3 stations, seed 1 | 12 | 3.11 / 475 | 153 | none | worst 10.9 | 11.4 / 13.1 / 13.1 |
| 3 stations, seed 2 | 12 | 2.90 / 468 | 161 | none | worst 9.3 | 9.8 / 12.0 / 13.9 |
| 4 stations, seed 0 | 16 | 2.44 / 531 | 218 | none | worst 14.5 | 12.7 / 11.2 / 14.9 / 16.3 |

"Weak" is a singular value under `calibration.data_sv_min` = 1 (data information below the prior's). Three cables are as
identifiable as four in these runs. The anchors' posterior covariance and the singular values are in `calibration.json`
(`result.identifiability.condition_number`, `singular_value_min`, `sigma`). The room-frame anchor error against the simulator's
truth after the fit is 1.4-6.3 cm (3 stations; 2.3-6.2 cm for 4): the data fix the geometry relative to the marker, the room alignment
comes from the entered anchor positions.

## 7. Calibration prior range (anchor C, seed 0)

`anchor_sigma_m` (1 sigma of the entry): 0.10 m hardware, 0.05 m simulator; `marker.position_sigma_m` 0.5 m; heading 20 degrees; the
slide-direction check in SLACK_TAKEUP refuses at an RMS of `startup.bearing_rms_max` = 3 sigma of `bearing_sigma_rad` 0.15 rad (0.45 rad).
Simulated truth with C's ENTRY off by the amount shown (the world's C stays at the middle of the wall):

| C entry off by | startup | trust level | bearing RMS (limit 3 sigma) | C anchor error in the room frame after the fit | calibration |
|---|---|---|---|---|---|
| 0 (reference, seed 0) | READY | LOCAL_ONLY (slack probe off) | 0.14 | 0.014 m (1.4 cm) | accepted |
| +0.2 m along the wall | READY | LOCAL_ONLY | 0.17 | 0.12 m | accepted |
| -0.4 m along the wall | READY | LOCAL_ONLY | 0.09 | 0.28 m | accepted |
| -0.3 m toward the wall (y) | READY | LOCAL_ONLY | 0.14 | 0.11 m | accepted |
| +0.8 m along the wall | READY | LOCAL_ONLY | 0.27 | 0.51 m | accepted |
| +1.2 m along the wall | READY | LOCAL_ONLY | 0.35 | 0.77 m | accepted |

So a stud a few inches or even 0.4 m off the midpoint does not stop the startup (it still completes at 1.2 m): the cable geometry relative to the marker is
fitted from the data. What the entry does decide is the ROOM-FRAME registration: the fitted C keeps about 0.6-0.7 of the entry error here (simulator prior
sigma 0.05 m; the hardware example uses 0.10 m), because the room alignment (marker position and heading) comes from the entered anchors, and the
acceptance criteria do not test the priors. The 0.2 m wall margin and the triangle edges are protected only as well as the entry is right, so enter C's
measured stud position (+-5 cm). Range in the sense of the spec: the entry may be anywhere within about 1.2 m along the wall for the startup to complete;
it should be within about 0.1 m for the wall margins to mean what they say.

## 8. Geometry of the recommended layout over the usable workspace

### Outlet angle (angle between the line and the vertical at the station; 0.6 kg / 0.45 kg claw; grid of the usable region, z 0.59-2.19 m)

| station | over the whole region | z <= 1.6 m (task cap) | at the start point, claw on the floor / lifted 7.5 cm | within 0.3 m of the start, z <= 1.0 m |
|---|---|---|---|---|
| A | 13.0-78.5 / 18.9-78.4 deg | 13.0-68.0 / 18.9-67.3 deg | 41.7 / 42.7 deg | 36.9-53.3 deg |
| B | 14.3-78.7 / 17.9-78.3 deg | 14.3-67.7 / 17.9-67.0 deg | 41.7 / 42.7 deg | 36.9-53.3 deg |
| C (mid-wall) | 12.9-78.1 / 18.2-77.6 deg | 12.9-66.9 / 18.2-66.1 deg | 40.3 / 41.3 deg | 35.2-52.3 deg |

C's line leaves nearly square to the wall: its horizontal direction is within -25.8 .. +27.4 degrees (0.6 kg; -23.5 .. +25.3 for 0.45 kg) of the
wall's normal; A and B leave along the diagonals (A 4-53 deg, B 127-176 deg in the room frame). At the room centre on the floor the angles would be
A, B 45.3 and C 32.5 degrees. **The 40 degree bench outlet cone does not cover the start point** (all three stations exceed 40 degrees there:
the known open outlet-cone item; the earlier review gave 43.9 degrees for the four-station floor centre). No pose has all three stations inside 40 degrees:
that needs a point within H tan 40 of all three outlets, H the drop below them (2.08 m for the claw on the floor: 1.74 m), and the smallest circle through
A, B, C has a radius of 1.82 m (circumradius of the 3.25 / 3.10 / 3.10 m triangle).

### Predicted claw tilt (cable model, held yaw; usable region at 0.15 m height steps)

| case | tilt min / median / max | share above the 5 degree grip limit |
|---|---|---|
| 3 stations, 0.6 kg, yaw 0 | 1.4 / 7.2 / 13.2 deg | 78 % |
| 3 stations, 0.6 kg, yaw 90 | 1.3 / 7.7 / 13.5 deg | 82 % |
| 3 stations, 0.45 kg, yaw 0 | 1.9 / 6.8 / 12.2 deg | 76 % |
| 4 stations, 0.6 kg, yaw 0 (reference, 0.2 m grid) | 0.4 / 6.8 / 13.2 deg | n/a |

At the start point (centroid, claw lifted 7.5 cm): roll -4.25, pitch -3.47 = **5.49 degrees**, vertical-axis moment 0.07 N m at yaw 0. The
tilt comes from hanging a box whose centre of mass sits under the centre of FOUR corner holes from THREE of them (the centroid of
the three holes is 14 mm off the centre of mass in x and in y: 19.8 mm / 0.196 m = 5.8 degrees). It cannot be changed in software. The lift aborts
(holding) if the measured tilt exceeds `startup.max_tilt_rad` = 8 degrees.

### Rigid-body simulator against the attitude model (42 suspended poses x 3 initial yaws, EA = 20 kN)

* Equilibrium tilt 3.5-9.7 degrees; the statics model evaluated at the equilibrium yaw agrees to < 0.01 degree everywhere (max |difference| 0.00).
* The equilibrium yaw does not depend on the initial yaw (0, +34, -52 degrees all settle within 0.8 degree of each other): +11.1 to +25.4 degrees over the poses (+15 at the
  start point). The held-yaw statics leaves a vertical moment of 0.05-0.1 N m; the claw turns until it vanishes.
* Stiffness (Schur complement of the 6 x 6 energy Hessian, claw at the start point, z = 0.7 / 1.3 m):

| (z = 0.7 m / z = 1.3 m) | roll N m/rad | pitch N m/rad | **yaw N m/rad** | lateral x N/m | lateral y N/m | vertical N/m |
|---|---|---|---|---|---|---|
| 4 stations, room centre | 1.34 / 1.42 | 1.38 / 1.48 | **0.98 / 1.48** | 531 / 1196 | 342 / 762 | 12 886 / 9 097 |
| 3 stations, centroid | 1.34 / 1.42 | 1.31 / 1.37 | **0.31 / 0.46** | 329 / 606 | 147 / 264 | 3 125 / 3 174 |

Roll and pitch stiffness are gravity-dominated and about the same; the **yaw stiffness is about a third** and the lateral and vertical stiffness 0.3-0.5 x.
The spec's "less tilt stiffness" is therefore not what was measured; the operator guide says "yaw stiffness a third" and "tilt from the corner pattern".

## 9. Limits, assumptions and open items

* **Outlet cone** (section 8): 41-43 degrees at the start for all three stations, 13-78 degrees over the workspace. Needs a station / outlet that allows it before the lift.
* **No redundancy**: any station that stops holding drops the claw. The coordinated stops (lease, underrun, pause) still hold with torque; a station reboot makes recovery
  `lower`; `recover` re-references at most one station from the camera, as before.
* **Tilt**: 5.5 degrees at the start on the CAD centre of mass; 2.5 degrees under the lift abort limit. Grips (5 degree limit) are refused over most of the workspace; no pickup tasks tonight.
* **Margin is conservative** by sin(elevation) (15-25 %) and uses the static weight (not a downward acceleration); the workspace is 20-27 % of the floor, not half.
* Slack probe is needed for VERIFIED (rule unchanged); without it the trust level is LOCAL_ONLY with that reason. With three cables the probe cannot find slack (all cables are taut), so it only costs time; the rule was not changed because the spec says the trust rules are unchanged.
* `bead_search` (optional, off): smoke run seed 0, `startup.bead_search: true`: READY, LOCAL_ONLY; each bead is BLOCKED by its gate ("absolute length sigma 20.7 / 13.5 / 12.1 mm exceeds 10.0 mm"), exactly as in the four-station lifecycle test, with no exception (the approach-pose search and `bead_workspace` ran over three cables). A full bead capture over three cables was not exercised.
* The simulator's camera is the 3 x 3 floor board (as in the four-station lifecycle test); a single 6 inch tag cannot meet the witness criterion at suspended poses in either mode.
* `geometric_reference` (new L0 from "the other three cables") raises for three active stations; nothing calls it.
* Two small four-station behaviour notes: `set_room` now answers 400 "unknown station" for an unknown id (it raised KeyError -> 500), and `Coordinator` / `Plan` accept any column count.
* Not done: firmware (unchanged by spec), hardware validation, a real claw tilt / yaw measurement, outlet angle limits in the planner.
