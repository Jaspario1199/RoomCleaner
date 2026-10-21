# Three-station mode: operator guide for the first hardware test (2026-10-21)

The product is a **four-station** robot. For the first hardware test only **three** stations are mounted, so the host
software can run with three or four active stations. Four stays the default; nothing changes unless the config
says `stations_active`. Contract: `docs/THREE_STATION_MODE_SPEC.md`. Measured results and the list of what changed:
`verification/three_station_mode_results.md`.

**What three cables mean.** A claw on three cables is held with all-positive tensions only while its floor position is
inside the triangle of the three outlets, and there is **no spare cable**: if one station stops holding, the claw falls.
Everything below follows from that.

**Review status.** The independent review (`verification/three_station_mode_review.md`) found the mode **PASS WITH
CONDITIONS** once its one blocker was fixed. The blocker (H1): on real hardware the phone's commands could not get through
("busy with 'None'"). It is fixed in commit `e42e2d4`, so **pull the latest code on the laptop first**. This guide includes the
review's conditions; the review IDs (M1, L2, ...) are given so you can look up the evidence.

## 1. Tonight, step by step

**Before anything moves:**

* **Weigh the claw** (kitchen scale, with battery and lines) and enter the weighed mass as `claw.mass_kg`, not the
  0.45 kg budget (L4). The edge margin of the workspace is computed from it. An entry heavier than the real claw lets the real
  edge tension drop below the 0.5 N floor.
* **Find the centre of mass** in x and y (balance the claw on a pencil, once along each axis, +-3 mm) and enter it as
  `claw.com_body_m` (M6). The config value is a CAD estimate without electronics. On the corner-hole claw, a CoM about 9 mm off
  toward the empty D corner is enough to trip the 8 degree tilt abort on the first lift.
* **Lay the printed floor board** (section 4.1). All the simulated three-station evidence uses it (M5).
* **Pad the floor** under the usable area (section 5): a folded blanket or mattress pad. With no spare cable, a station
  fault drops the claw from up to 1.6 m.
* **Outlets:** one person watches each outlet during the first calibration, and the first calibration box is smaller
  (section 5, outlet angle; M4).
* **Quiet laptop:** close the browser, CAD, the garment detector, anything CPU-heavy (L7). A busy laptop can stall the
  keep-alive to the stations.

**Then:**

1. Mount A and B in the two corners of one 11 ft wall and C in the middle of the opposite 11 ft wall (section 2), all
   three outlets at the same height. Station D is not mounted, not wired, not powered.
2. Pick the config for the claw you are hanging (section 3): lines through three of the **corner holes** ->
   `config/robot.three.example.json`; the **three-cable housing** (`_34`, lines through holes T_A, T_B, T_C) ->
   `config/robot.three34.example.json`. Copy it to `config/robot.json` and fill in what is still `null`. Both files already
   list `"stations_active": ["A", "B", "C"]` and the three anchor priors.
3. Rehearse in the simulator first, **with its own data directory**:
   `python -m roomcleaner.cdpr.service --sim --config config/robot.sim3.json --data data/sim3`
   (`config/robot.sim3_34.json` for the three-cable housing). Stop it with Ctrl+C when done.
4. Start the real service with a **different, new** data directory (M3):
   `python -m roomcleaner.cdpr.service --config config/robot.json --host 0.0.0.0 --data data/hw3`
   and open the printed address on the phone. Never point the real service at the rehearsal's directory: it would start in
   RECOVERY_REQUIRED ("host restarted while the claw may be suspended") and show the simulator's calibration. The terminal
   says `THREE-STATION MODE: active cables A/B/C` at the start of the first startup; **if it does not, stop**: the
   config is running four stations (section 3).
5. On Setup, read the mode line and the **start point** line (section 4). Put the claw upright on sheet 0 of the board at
   that point, camera side toward station C (section 4).
6. Tick the checklist (it names the three cables and the start point) and start. Stay out from under the robot.
7. The startup takes up slack on A, B, C one at a time, pretensions, lifts a few cm, calibrates, and ends READY.
   `LOCAL_ONLY` with the reason "slack probe was off" is the normal, safe result (section 6).
   **Expect that some starts stop in PRETENSION with `claw dragged while tensioning`** (M1, a known false alarm,
   section 8): the claw is still on the floor. Disarm (type `claw_supported`), check the claw sits at the start point, Start again.
8. Move only inside the usable area (section 5). A move toward the missing corner is refused before any motion.
9. When done: **Lower** from Setup, wait for PARKED, then Disarm. The power strip is the emergency stop and it drops the claw.

## 2. Placing the stations

```
        far 11 ft wall (y = 2.74 m)                       x runs along the 11 ft walls (3.35 m), y along the 9 ft walls (2.74 m)
 +----------------------------- C ----------------------------+    C: on the stud nearest the MIDDLE of this wall
 |                          (1.68, 2.69)                       |       (5 ft 6 in from either corner), same height as A and B
 |                                                             |    The corner at its left end would be D: not mounted.
 |                                                             |
 |                                                             |
 |                          claw start +                       |    + start point (1.68, 0.93) m = the centroid of A, B, C
 |                         (1.68, 0.93)                        |      = 5 ft 6 in along the wall, 3 ft 0.6 in out from the A-B wall
 |                                                             |
 A ----------------------------------------------------------- B
 (0.05, 0.05)       near 11 ft wall (the one with A and B)     (3.30, 0.05)
```

* **A and B:** the two corners of one 11 ft (3.35 m) wall, outlets 5 cm in from each corner. These are the same places
  the four-station layout uses for A and B.
* **C:** the **middle of the opposite 11 ft wall**, on the stud nearest the midpoint, at the **same height** as A and B
  (the priors say 2.59 m = 8 ft 6 in, 6 in under the 9 ft ceiling). Sides of the triangle: about 3.25 m (A to B) and
  3.10 m (A to C, B to C): nearly equilateral, which keeps the usable area as large as it can be.
* **Priors only, but enter the real position.** The three anchor entries seed the calibration, which fits the cable
  geometry itself, so a stud a few inches off the midpoint does not stop the startup (in simulation it completed with C's
  entry off by 0.2, 0.4, 0.8 and even 1.2 m). What the entry does decide is where the room is: the fitted C keeps about two
  thirds of an entry error (0.2 m off -> 0.12 m off after the fit), and the 0.2 m wall margin is only as good as that.
  Measure the stud (tape measure, +-5 cm) and type it into Setup (a) or the config
  (`verification/three_station_mode_results.md`, section 7).
* **Station ids.** The host tells each station its id when it configures it, and the id belongs to the address in the
  config: put the IP:port of the unit on the middle of the far wall under `C`, the corners' units under `A` and `B`.
  Leave `D`'s address `null`. No firmware change.
* **Power run to C:** 3 ft down, along the floor to the middle of the far wall, 9 ft up: about 27 ft. The 35 ft pair covers it.

Anchor positions in feet from the A corner: A (0.2, 0.2), B (10.8, 0.2), C (5.5, 8.8). Room 11 x 9 x 9 ft.

## 3. The config to use

Two hardware configs, one per claw. They differ **only** in `claw.attachment_points_body_m`, the points where the lines leave
the claw:

| claw on the rig tonight | config | simulator rehearsal | predicted tilt at the start point |
|---|---|---|---|
| lines through three of the four **corner holes** (A, B, C; D empty) | `config/robot.three.example.json` | `config/robot.sim3.json` | 5.5 degrees (abort at 8) |
| **three-cable housing** `_34`, lines through T_A, T_B, T_C | `config/robot.three34.example.json` | `config/robot.sim3_34.json` | 0.8 degrees |

The tilt is from the cable model with the CAD centre of mass (`verification/three_station_34_profile.md`). The corner-hole
pattern tilts the claw because three of four corners have their centroid 14 mm off the centre of mass; the 120 degree
pattern is 2.3 mm off. The independent review covered the corner-hole profile; the `_34` profile was added afterwards.

`config/robot.three.example.json` is `config/robot.example.json` plus:

| key | value |
|---|---|
| `stations_active` | `["A", "B", "C"]` (also accepted: the spelling `"stations.active"`). Three or four distinct ids from A-D, in any order. Absent = all four. |
| `stations[C].anchor_room_m` | `[1.6764, 2.6932, 2.5932]` (middle of the far wall); A and B are `[0.05, 0.05, 2.5932]` and `[3.3028, 0.05, 2.5932]` |

Everything else is `null` until measured, exactly as in the four-station example, and the code refuses a stage whose
fields are `null` (Setup (b) lists them; `GET /api/checks` the same). For tonight fill in at least:

* `stations[A|B|C].address` ("ip:port"), `claw.address`, the drive and encoder values you measured (`drive.max_step_rate_hz`,
  `encoder.sign`, `encoder.max_age_s`, `spool.line_diameter_m`, `spool.line_total_m`), and the timing limits under `faults`.
  Station D needs **nothing**: no address, no measured values.
* `claw.mass_kg`: **the weighed mass**, not the 0.45 kg budget (L4). **The edge margin of the workspace is computed from
  it** (section 5): a lighter claw means a bigger margin and a smaller usable area.
* `claw.com_body_m`: the measured centre of mass (x, y from the balance test; keep the CAD z).
* `marker.edge_m` (the measured black square of sheet 0, in metres), `marker.board_layout_file` (section 4.1),
  `camera.intrinsics_file`, `camera.max_frame_age_s`, and `marker.heading_prior_rad` = **-2.645** rad
  (sheet 0's +X points from the start point toward station A; the simulator profile uses the same).
* `calibration.expanded_box_m`: **[0.4, 0.4, 0.3]** for the first run instead of the default [0.8, 0.8, 0.5]
  (section 5, outlet angle).
* `motion` speeds and `motion.max_tension_n`, `startup.*` limits, and `authorization.suspended_motion_authorized` only
  after your own sign-off.
* `startup.max_slack_m` keeps four numbers (A, B, C, D); D's entry is ignored.

The config is refused, with a message, when `stations_active` has fewer than three or more than four stations, a
duplicate, an unknown id, anchors that are collinear or span a sliver (shortest altitude under 0.25 m), or a tension floor
that three cables cannot meet.

**Misspelt key: only partly caught (M2).** A stray key containing both "active" and "station" (`active_stations`,
`Stations_Active`) is refused. Other typos are **not**: `stations_actve`, `stations_enabled`, `three_station` and the like load
as **four** active stations without a word. So copy the key from the example file, and check that the terminal prints
`THREE-STATION MODE: active cables A/B/C` and the Home tab shows three tiles. Tonight D has no address, so a four-station
load stops at launch for the missing address; it never arms a station without a cable.

To go back to four stations delete the key (or list all four) and run with four cables.

## 4. Where to put the claw

**At the centroid of the three outlets' floor projection: (1.68, 0.93) m**, which is 5 ft 6 in along the A-B wall (the
middle of the room's width) and **3 ft 0.6 in out from that wall**. It is *not* the room centre: the room centre is
0.44 m (1 ft 5 in) closer to C (L2). Upright on its jaws, on sheet 0 of the floor board, sheet 0's +X toward station A.

* **Facing (both claws):** set the claw down the way it will hang, camera side (+y) toward the far wall and station C,
  within about 25 degrees.
  * Corner holes: the A and B corner holes face the near (A-B) wall. Each line then leaves its own corner hole toward its
    own station without crossing the box; the box's D corner stays empty.
  * Three-cable housing (`_34`): the camera bay faces station C, so T_C is the hole on the camera side and T_A, T_B face
    the near wall.
* The Setup tab shows this point (`Start point: (1.68, 0.93) m ...`) and the checklist item names it. The point follows
  the anchor entries: if you edit C's position in Setup, the start point moves with it.
* Why the centroid: the three tensions are nearly equal there (1.9-2.0 N each for a 0.45 kg claw) and it keeps the most
  margin from all three edges. The room centre is also accepted by the tension check (minimum 1.5 N, edge margin kept), so a
  start a little toward the room centre is safe too; the configured start point (`marker.position_prior_room_m`) can move it.
* Tolerance: within about 20 cm is fine. If the claw is outside the usable triangle the startup **stops in INITIAL_LIFT
  before it lifts**, with the floor point it measured and the point to use instead. It never lifts a claw that three cables
  cannot hold.

### 4.1 The floor board (use it tonight)

The printed 3 x 3 board is the validated floor reference, and every simulated three-station startup in the results and the
review used it (M5). It is described in `docs/CONTROL_SYSTEM_V1.md` section 3.2; page 1 of the PDF repeats these steps.

1. Print `prints/floor_board_letter.pdf` on US Letter at **100 % (Actual size, not "fit to page")**: one instruction page
   and nine tag sheets (AprilTag 36h11, ids 0-8, 150 mm black squares). To regenerate it:
   `python -m tools.print_floor_board --out prints/floor_board_letter.pdf`.
2. Measure sheet 0's black square with a ruler and enter it in metres as `marker.edge_m`. Reprint any sheet that differs
   from sheet 0 by more than 1 mm.
3. Put **sheet 0 in the middle, at the start point**, with its +X (to the right as printed) pointing toward station A.
4. Lay the other eight around it as a 3 x 3 grid, **0.25 m tag centre to tag centre**. Above and below, the sheets overlap
   by about 30 mm: overlap only the blank paper margins, never a tag or its white border. Exact spacing does not matter,
   because the robot surveys the sheets during startup.
5. Tape every corner flat: no curl, no rug that slides, no glare, nothing lying across a tag. Pad under the board is fine
   if it lies flat; do not put the blanket on top of the board.
6. Write the starting layout file once:
   `python -m tools.print_floor_board --layout-json data/floor_board.json --no-pdf`, then set
   `"marker": {"board_layout_file": "data/floor_board.json", ...}`. The robot rewrites it after surveying (and keeps a `.bak`).
7. Do not move or bump a sheet during a run.

**Without the board** (one tag only), the simulated three-station startup still ended READY / `LOCAL_ONLY` in 4 of 5 seeds,
but with a different reason ("calibration not accepted: prior-dominated ...; predicted length sigma 7.3 to 8.1 mm > 5.0 mm"),
and in the fifth it stopped in INITIAL_LIFT ("claw rose 59 mm for 75 mm commanded"), claw hanging, `lower` to recover.

## 5. Expected workspace

The floor position of the claw has to stay inside the triangle A-B-C **and** keep a margin from each edge. The margin is
sized from the tension floor: cable `i` carries `T_i >= lambda_i * m g` (lambda = the claw's barycentric coordinates in the
triangle), so `lambda_i >= T_floor / (m g)` keeps every cable at or above `motion.min_tension_n` (0.5 N) at any height.
For the 0.45 kg budget that is `lambda >= 0.113`: **0.30 m (0.299) from the A-B wall side and 0.31 m (0.314) from each
diagonal side** (0.225 m / 0.235 m for the simulator's 0.6 kg claw; L1). The margin is `lambda x altitude`, and the
triangle's altitude over A-B (2.64 m) is shorter than over the diagonals (2.77 m). A lighter claw needs a bigger margin:
for a weighed 0.375 kg, `lambda >= 0.136`, about 0.36 m and 0.38 m. The app shows the values it uses under
`workspace.edge_margin_m` in `GET /api/status`. The other margins are as before: 0.2 m from the walls, 0.4 m under the
outlets (`z <= 2.19 m`), the claw's own height above the floor (`z >= 0.59 m`, origin height), and the task layer's 1.6 m.

```
   +----------------------------------+    . = usable (0.45 kg claw)      + = start point (centroid)
   |                 C                |    , = inside the triangle but too close to an edge
   |               ,,,,               |    o = room centre (usable)
   |              ,,,,,,              |
   |             ,,,,,,,,             |    Usable floor area: about 1.9 m2 = 20 % of the room
   |            ,,,,..,,,,            |    (2.4 m2 = 27 % for the 0.6 kg simulator claw).
   |           ,,,......,,,           |    The whole triangle is 4.3 m2 = 47 % of the room: the margins cost
   |         ,,,,........,,,,         |    the rest. x 0.7 .. 2.7 m, y 0.4 .. 2.0 m, z 0.59 .. 2.19 m.
   |        ,,,,.....o....,,,,        |
   |       ,,,,............,,,,       |
   |      ,,,........+.......,,,      |
   |    ,,,,..................,,,,    |
   |   ,,,,....................,,,,   |
   |  ,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,  |
   |A,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,B|
   +----------------------------------+
```

* The planner, the calibration poses, the start-up work volume, the ceiling cap and the task layer all use this region.
  A target outside it is refused **before any motion**: `workspace: floor point (...) is 0.53 m outside the edge opposite
  station B of the A/B/C triangle; it must be at least 0.23 m inside`.
* A 300 mm move from the start point to another point inside the area runs normally (simulated, all three seeds).
* The room corner near D is outside. Do not ask for it.
* Outlet angle: the cable leaves each station at **41-43 degrees from vertical** at the start point (A and B 41.7, C 40.3
  with the claw on the floor), 37-53 degrees within 0.3 m of it, and 13 to 78 degrees over the whole usable volume (13-68 up to
  1.6 m). C's line leaves nearly square to the wall (within 26 degrees of the wall's normal); A and B leave along the
  diagonals. **If your outlets are the 40 degree bench outlet, the start point itself is 1-3 degrees outside its cone**; that
  is the known open outlet-cone item, not something the software can fix.
* **The calibration is what drives the cables far outside 40 degrees (M4).** The claw climbs to about 1.6 m in a box
  +-0.8 m around the start point, so each cable leaves its station at up to 66-68 degrees from vertical, and 84-88 % of the
  calibration poses are above 40 degrees. Height raises the angle most. The planner has no outlet-angle limit. Point-claw
  estimate of the worst angle per calibration box (`calibration.expanded_box_m`, half-widths x, y, z):

  | box (m) | claw height range | worst angle A / B / C | poses above 50 degrees |
  |---|---|---|---|
  | [0.8, 0.8, 0.5] (default) | 0.61-1.60 m | 66 / 66 / 65 | 47-55 % |
  | [0.4, 0.4, 0.3] (first run) | 0.61-1.21 m | 60 / 60 / 58 | 26-35 % |
  | [0.3, 0.3, 0.2] | 0.61-1.01 m | 55 / 55 / 53 | 8-14 % |

  No box keeps every cable inside 40 degrees, because the start point is already at 41-43. For the first run:
  1. Set `calibration.expanded_box_m` to [0.4, 0.4, 0.3].
  2. One person watches each outlet where the line leaves the collar (three people, nobody under the claw).
  3. **Pause** at the first sign of the line rubbing the collar edge, scraping noise or fuzz on the line, then Lower.
  4. After the run, look at the lines and the outlet edges for wear before running the full box.
  The decision on the outlets themselves (keep the bench outlet, open its cone, or add an outlet-angle limit to the
  planner) is still open.

## 6. What the app shows

* **Home:** three station tiles (A, B, C): online, state, fault, reference. There is no tile for D and D is not a fault.
  The trust line, claw and camera cards are as before.
* **Setup:** (a) anchors for A, B, C only; the note says "THREE-STATION MODE: cables A, B, C only ... No spare cable, about
  a third of the four-cable yaw stiffness, and only the middle of the room is usable"; the start point line; (c) the checklist:
  *Claw upright on the floor at the start point (1.68, 0.93) m, the centroid of anchors A, B, C (NOT the room centre), marker
  under the camera* and *All active cables (A, B, C) attached and routed over their pulleys*; (e) the calibration result with
  anchors A, B, C and the identifiability condition number.
* **Trust level:** with `startup.slack_probe` off (the default) the startup ends **READY, `LOCAL_ONLY`**, reason "slack probe
  was off ...": the same as the four-station simulator. With a single tag instead of the board the reason is
  "calibration not accepted: prior-dominated ..." (section 4.1); also `LOCAL_ONLY`, also fine for moving tonight. With `startup.slack_probe: true` the simulated three-station startup
  reached **VERIFIED (basis: margin)**: k x sigma was 60 mm of 400 mm at the ceiling and 102 mm of 200 mm at the walls. The
  probe retracts each cable in turn, so it takes about twice as long. Tonight `LOCAL_ONLY` is enough.
* `GET /api/status` adds `stations_active`, `stations_inactive`, `start_point_m`, `start_point_text`, `mode_text`, `workspace`
  (triangle area, edge margins); `stations` lists A, B, C only.

## 7. Safety notes

* **Nobody under the robot.** Not for the lift, the calibration moves, or a stop. The power strip drops the claw.
* **No redundancy.** With four cables a failed station leaves three that still hold the claw inside their triangle. Here
  every cable is needed: a station that loses power, trips a fault or slips lets the claw fall. The startup lifts only
  8 cm first; the calibration then moves the claw up to 1.6 m (1.2 m with the first-run box). Keep the floor under it clear
  and **padded**.
* **The claw sits further from the room centre** than the four-cable claw does. It starts 0.44 m toward the near wall, and
  the usable area reaches 0.5 m from the start point toward the near wall, 1.0 m to each side and 1.07 m toward C (L2).
  Keep the cables clear of furniture and the hamper in that area.
* **Quiet laptop (L7).** In a simulated four-station startup with another CPU-heavy program running, the calibration fit
  stalled the keep-alive for 200-435 ms against the 300 ms lease, and once all four stations latched a LEASE fault. On a
  quiet machine the worst gap was 28 ms. Close everything else during the startup (optional: start the service with
  `OPENBLAS_NUM_THREADS=1`).
* **Less yaw stiffness.** Measured in the rigid-body simulator the yaw stiffness is 0.31 N m/rad (z 0.7 m) against 0.98 for
  four cables, about a third; roll and pitch are the same (1.3 N m/rad, gravity pendulum). The claw settles to a yaw of
  about +11 to +25 degrees on its own, whatever it started at, and a three-cable claw turns more easily if a cable
  drags. The camera still sees the marker over the usable area (the startup checks visibility at its poses).
* **Tilt.** Hanging from three of the box's four corners tilts the claw: the cable model predicts 5.5 degrees at the start
  point and 1 to 13 degrees over the workspace (median 7; the rigid-body simulator agrees to 0.01 degree). That is the CAD
  centre of mass (`claw.com_body_m` says VERIFY); the lift aborts, holding, if the measured tilt exceeds `startup.max_tilt_rad`
  (8 degrees), a 2.5 degree margin at the start. A centre of mass 9 mm off toward the empty D corner uses up that margin, and
  15 mm off gives 9.4 degrees (M6), so **measure it** (section 1). If the first lift stops with `tilt ... deg during lift`,
  check which side the battery sits on. The grip tilt limit (5 degrees) would refuse most grips: do not run pickup
  tasks tonight. Movement and calibration are the test.
* **Tilt with the three-cable housing (`_34`).** The 120 degree hole pattern predicts 0.8 degrees at the start point and
  0.2 to 9.2 degrees over the workspace (median 3.6; 78 % of it under the 5 degree grip limit). Model only, not yet measured.
* **Corner-hole exit angle (L3).** With the corner holes, the A and C lines leave their 18 mm holes 30-46 degrees off the hole
  axis. Nobody has checked that the Dyneema takes that bend without wear: look at the C and A holes after the first lift.
* **Tensions** are about 2 N per cable at the start point (0.45 kg claw) and fall toward the 0.5 N floor at the edge of the
  usable area; the margin keeps them above it. Do not ask for more than the planner allows, and not with a loaded claw.
* **Station D is not part of this run.** Nothing in the host talks to it, configures it or arms it. If it is on the network
  it is not a fault and not checked.
* The recovery commands work over A, B, C. After a station reboot, **lower**; the recover command re-references at most one
  station from the camera and lowering needs the claw inside the usable area.

## 8. If something is refused

| message | meaning / what to do |
|---|---|
| `stations_active [...]: 2 station(s); ... needs 3 or 4 distinct ids` | the config lists too few stations |
| `... collinear or coincide` / `... degenerate triangle (area ..., shortest altitude ...)` | the three anchor entries do not span a triangle; check the coordinates, especially C's |
| `unknown config key ['active_stations']` | the key is `stations_active` |
| `the claw rests where three cables cannot lift it: floor point (x, y) is ... outside the edge opposite station B ...` | the claw is not near the start point; move it to (1.68, 0.93) m and start again |
| `workspace: floor point (...) is ... outside the edge opposite station ...` | a move target outside the usable area; refused before any motion |
| `slide directions disagree with the anchor entries ... check station order/wiring A-B-C` | a cable is on the wrong station (a swap of A and B, or A and C, is caught in simulation, RMS 8 sigma against a limit of 3) or an anchor entry is far off |
| `pretension: claw dragged while tensioning` (or `claw rocking on its jaws while tensioning`) | **known false alarm (M1)**, seen on 3 of 8 simulated corner-hole starts. The "just taut" pretension overshoots by 0.3-0.6 mm, the three cables take the whole weight, the claw lifts off its jaws and tilts about 6 degrees, and the drag watch (which assumes the resting claw cannot tilt) reads that as 15-18 mm of drag. The claw is still on the floor and the stations hold. **Disarm** (type `claw_supported`), check the claw sits upright at the start point, **Start** again (in simulation the second start reached READY). |
| `busy with 'None'` on every command | the laptop runs code from before the H1 fix: `git pull` (commit `e42e2d4` or later) and restart the service |
| `busy with 'start'` (or another command) | a command is really running; wait for it, or press PAUSE |
| state RECOVERY_REQUIRED right after launch: `host restarted while the claw may be suspended ...` | the data directory holds an earlier run, often the rehearsal's (M3). If the claw may be hanging: **Lower**. If it is certainly on the floor: stop the service and start it again with a new `--data` directory (section 1, step 4) |
| `tilt ... deg during lift` | the claw hangs tilted more than 8 degrees; the stations hold it a few cm up. **Lower**, then check the centre of mass and the battery position (section 7, M6) |
| `claw rose ... mm for ... mm commanded: a cable is slack/unattached or the model is badly wrong` | a line is not attached or not over its pulley, or (with one tag instead of the board) a poor floor reference. **Lower**, check the three lines, use the board |
| READY / `LOCAL_ONLY`, `calibration not accepted: prior-dominated ...` | the calibration ran on a single tag (no board): usable for moving tonight; use the board next time (section 4.1) |
| a station shows a LEASE fault during calibration | the keep-alive stalled, usually a busy laptop (L7). The stations stop together and keep holding (a fault never removes holding torque), so the claw stays where it is. Stay clear and **Lower**. Close other programs before the next start. The power strip is only for an emergency: it drops the claw |
