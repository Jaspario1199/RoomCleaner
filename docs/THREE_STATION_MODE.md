# Three-station mode: operator guide for the first hardware test (2026-10-21)

The product is a **four-station** robot. For the first hardware test only **three** stations are mounted, so the host
software can run with three or four active stations. Four stays the default; nothing changes unless the config
says `stations_active`. Contract: `docs/THREE_STATION_MODE_SPEC.md`. Measured results and the list of what changed:
`verification/three_station_mode_results.md`.

**What three cables mean.** A claw on three cables is held with all-positive tensions only while its floor position is
inside the triangle of the three outlets, and there is **no spare cable**: if one station stops holding, the claw falls.
Everything below follows from that.

## 1. Tonight in nine steps

1. Mount A and B in the two corners of one 11 ft wall and C in the middle of the opposite 11 ft wall (section 2), all
   three outlets at the same height. Station D is not mounted, not wired, not powered.
2. `cp config/robot.three.example.json config/robot.json` and fill in what is still `null` (section 3). The file already
   lists `"stations_active": ["A", "B", "C"]` and the three anchor priors.
3. Rehearse in the simulator first: `python -m roomcleaner.cdpr.service --sim --config config/robot.sim3.json`.
4. Start the real service: `python -m roomcleaner.cdpr.service --config config/robot.json --host 0.0.0.0`
   and open the printed address on the phone. The terminal says `THREE-STATION MODE: active cables A/B/C` at the start
   of the first startup.
5. On Setup, read the mode line and the **start point** line (section 4). Put the claw upright on the floor at that
   point, marker under the camera, marker +X pointing toward station A.
6. Tick the checklist (it names the three cables and the start point) and start. Stay out from under the robot.
7. The startup takes up slack on A, B, C one at a time, pretensions, lifts a few cm, calibrates, and ends READY.
   `LOCAL_ONLY` with the reason "slack probe was off" is the normal, safe result (section 6).
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
* `claw.mass_kg` (the budget is 0.45 kg). **The edge margin of the workspace is computed from it** (section 5): a lighter
  claw means a bigger margin and a smaller usable area.
* `marker.edge_m`, `camera.intrinsics_file`, `camera.max_frame_age_s`, and `marker.heading_prior_rad` = **-2.645** rad
  (marker +X points from the start point toward station A; the simulator profile uses the same).
* `motion` speeds and `motion.max_tension_n`, `startup.*` limits, and `authorization.suspended_motion_authorized` only
  after your own sign-off.
* `startup.max_slack_m` keeps four numbers (A, B, C, D); D's entry is ignored.

The config is refused, with a message, when `stations_active` has fewer than three or more than four stations, a
duplicate, an unknown id, a misspelt key (`active_stations` would otherwise run all four), anchors that are
collinear or span a sliver (shortest altitude under 0.25 m), or a tension floor that three cables cannot meet.
To go back to four stations delete the key (or list all four) and run with four cables.

## 4. Where to put the claw

**At the centroid of the three outlets' floor projection: (1.68, 0.93) m**, which is 5 ft 6 in along the A-B wall (the
middle of the room's width) and **3 ft 0.6 in out from that wall**. It is *not* the room centre: the room centre is
2 ft closer to C. Upright on its jaws, marker flat on the floor under the camera, marker +X toward station A.

* **Facing:** set the claw down the way it will hang, as for four cables: its A and B corner holes toward the near
  (A-B) wall and its camera side (+y) toward the far wall, within about 25 degrees. Each line then leaves its own
  corner hole toward its own station without crossing the box; the box's D corner stays empty. The marker +X points
  from the start point toward station A.
* The Setup tab shows this point (`Start point: (1.68, 0.93) m ...`) and the checklist item names it. The point follows
  the anchor entries: if you edit C's position in Setup, the start point moves with it.
* Why the centroid: the three tensions are nearly equal there (1.9-2.0 N each for a 0.45 kg claw) and it keeps the most
  margin from all three edges. The room centre is also accepted by the tension check (minimum 1.5 N, edge margin kept), so a
  start a little toward the room centre is safe too; the configured start point (`marker.position_prior_room_m`) can move it.
* Tolerance: within about 20 cm is fine. If the claw is outside the usable triangle the startup **stops in INITIAL_LIFT
  before it lifts**, with the floor point it measured and the point to use instead. It never lifts a claw that three cables
  cannot hold.

## 5. Expected workspace

The floor position of the claw has to stay inside the triangle A-B-C **and** keep a margin from each edge. The margin is
sized from the tension floor: cable `i` carries `T_i >= lambda_i * m g` (lambda = the claw's barycentric coordinates in the
triangle), so `lambda_i >= T_floor / (m g)` keeps every cable at or above `motion.min_tension_n` (0.5 N) at any height.
For the 0.45 kg budget that is `lambda >= 0.113`: **0.31 m from the A-B wall side and 0.30 m from each diagonal side**
(0.235 m / 0.225 m for the simulator's 0.6 kg claw). The other margins are as before: 0.2 m from the walls, 0.4 m under the
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
  is the known open outlet-cone item, not something the software can fix. Check the outlet before the claw lifts.

## 6. What the app shows

* **Home:** three station tiles (A, B, C): online, state, fault, reference. There is no tile for D and D is not a fault.
  The trust line, claw and camera cards are as before.
* **Setup:** (a) anchors for A, B, C only; the note says "THREE-STATION MODE: cables A, B, C only ... No spare cable, about
  a third of the four-cable yaw stiffness, and only the middle of the room is usable"; the start point line; (c) the checklist:
  *Claw upright on the floor at the start point (1.68, 0.93) m, the centroid of anchors A, B, C (NOT the room centre), marker
  under the camera* and *All active cables (A, B, C) attached and routed over their pulleys*; (e) the calibration result with
  anchors A, B, C and the identifiability condition number.
* **Trust level:** with `startup.slack_probe` off (the default) the startup ends **READY, `LOCAL_ONLY`**, reason "slack probe
  was off ...": the same as the four-station simulator. With `startup.slack_probe: true` the simulated three-station startup
  reached **VERIFIED (basis: margin)**: k x sigma was 60 mm of 400 mm at the ceiling and 102 mm of 200 mm at the walls. The
  probe retracts each cable in turn, so it takes about twice as long. Tonight `LOCAL_ONLY` is enough.
* `GET /api/status` adds `stations_active`, `stations_inactive`, `start_point_m`, `start_point_text`, `mode_text`, `workspace`
  (triangle area, edge margins); `stations` lists A, B, C only.

## 7. Safety notes

* **Nobody under the robot.** Not for the lift, the calibration moves, or a stop. The power strip drops the claw.
* **No redundancy.** With four cables a failed station leaves three that still hold the claw inside their triangle. Here
  every cable is needed: a station that loses power, trips a fault or slips lets the claw fall. The startup lifts only
  8 cm first; the calibration then moves the claw up to 1.6 m. Keep the floor under it clear.
* **The claw sits further from the room centre** than the four-cable claw does (it starts 0.44 m toward the near wall and the
  usable area reaches about 0.6 m from the start point). Keep the cables clear of furniture and the hamper in that area.
* **Less yaw stiffness.** Measured in the rigid-body simulator the yaw stiffness is 0.31 N m/rad (z 0.7 m) against 0.98 for
  four cables, about a third; roll and pitch are the same (1.3 N m/rad, gravity pendulum). The claw settles to a yaw of
  about +11 to +25 degrees on its own, whatever it started at, and a three-cable claw turns more easily if a cable
  drags. The camera still sees the marker over the usable area (the startup checks visibility at its poses).
* **Tilt.** Hanging from three of the box's four corners tilts the claw: the cable model predicts 5.5 degrees at the start
  point and 1 to 13 degrees over the workspace (median 7; the rigid-body simulator agrees to 0.01 degree). That is the CAD
  centre of mass (`claw.com_body_m` says VERIFY); the lift aborts, holding, if the measured tilt exceeds `startup.max_tilt_rad`
  (8 degrees), a 2.5 degree margin at the start. The grip tilt limit (5 degrees) would refuse most grips: do not run pickup
  tasks tonight. Movement and calibration are the test.
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
