# Room map (Map tab): build note, 2026-10-26

Scope: `docs/ROOM_MAP_SPEC.md` sections 1-5 (decision D35, "now" half). Section 6 (camera-built map) not started.
Built by the implementer; **independent verification (spec 5, last bullet) is still to be done** by an agent that did not write it.

## What was built

| area | where | what |
|---|---|---|
| data model | `roomcleaner/cdpr/config.py` | `validate_obstacles` / `parse_obstacles`: boxes (`length_m`, `width_m`, `yaw_deg`) and cylinders (`diameter_m`), `z_low_m` = bottom, `height_m` = top; old `{x,y,r,z_low,z_high,name}` loads as a cylinder; ids `o1..` given when missing. Refusals with a message: unknown shape or key, size <= 2 cm or larger than the room, `z_low_m >= height_m` (or below the floor), top above ceiling + 5 cm, centre outside the room, > 50 shapes, duplicate id, non-numbers. New keys `motion.obstacle_margin_m` (0.10), `claw.body_radius_m` (0.07), top-level `map_units` ("ft-in" / "m"). `load_config` validates at every start. |
| exact tests | `roomcleaner/geometry.py` | `segment_intersects_box` (slab test in the box frame) beside the existing `segment_intersects_cylinder` (reused, unchanged); vectorised `segments_hit_cylinder`, `segments_hit_box`, `xy_distance_to_box` for the coverage grid. |
| planner | `roomcleaner/cdpr/kinematics.py` | `Workspace.violations` -> `obstacle_violations`: every cable segment and the claw body (lowest point to attachment plane, widened by `claw.body_radius_m`) against every shape inflated by the margin (box corners stay square: conservative). The 24-point sampler is gone. Messages: "cable B would cross the Shelf", "the claw would enter the Shelf". No shapes: nothing runs, behaviour unchanged. `coverage()`: 10 cm grid, first reason per cell (shape + cable, usable area, trusted volume). |
| tasks (spec 3.6) | `roomcleaner/cdpr/tasks.py` | Skipping unreachable items was already in place (task-pumping fix). Small addition: an item refused by the map now says which shape and cable ("unreachable: approach sock: target [...]: cable B would cross the Shelf") instead of "outside the trusted volume". |
| startup | `roomcleaner/cdpr/startup.py` | (found by the startup test) the D-optimal calibration poses were already filtered, but the straight move between two allowed poses can pass a shape: such a move now goes over it (up to the workspace top, across, down) and a pose not reachable that way is skipped and logged instead of a fault. INITIAL_LIFT refuses to lift a claw resting where the straight-up column meets a shape (with the margin), with a plain message. Only refusals caused by map shapes take these paths; without shapes nothing changes. |
| API | `roomcleaner/cdpr/service.py` | `GET /api/room_map`, `POST /api/room_map/preview` (errors + coverage, saves nothing, no robot lock), `PUT /api/room_map` (DISARMED/PARKED; READY/PAUSED only if the claw pose and its straight-down lowering to the floor stay clear; refused while busy and in STARTUP/TASK/FAULT/RECOVERY_REQUIRED; written to the config file in hardware mode, memory only in `--sim`; also updates the live `ctx.ws`). Token guard as every /api call; PUT also needs a JSON body. |
| app | `roomcleaner/cdpr/static/index.html`, `app.js`, `app.css` | Map tab (fifth tab, between Setup and Chat). |
| docs | `docs/APP.md` | Map row in the tab table, endpoints, tests. |

### Map tab, kept simple (Jasper's request via the lead)
- First screen: three big palette buttons (Square, Rectangle, Circle), the room, an empty-state line ("Tap Square, Rectangle or Circle to
  add furniture the robot must avoid."), **Save map** (Revert only appears when there are unsaved changes; a dot on the Map tab too).
- One folded **"More: undo, units, hamper, where it can pick"**: Undo last change (20 steps), Show where it can pick things up (overlay
  + legend; tap a cell for the reason), Hamper: place and height, Units (feet and inches / metres).
- Selected shape: a card under the map (never over it, so the shape stays draggable) with the name chips (Bed, Desk, Dresser, Shelf,
  Chair, Lamp, Ceiling fan, Other: they pre-fill sizes), size (Length/Width, Side or Across) and Height, Turn 90 deg (rectangles) and
  Delete. Its own "More: exact place, angle, hanging" holds name text, x/y, angle, "Hangs from the ceiling" + bottom height, Make a copy.
- Drag to move (1 in snap, flush to a wall within 5 cm), corner / side / rim handles (44 px hit areas), palette drag-and-drop,
  pointer events with one update per animation frame. Lengths accept `5'6"`, `5 ft 6 in`, `66 in`, `66"`, `1.68 m`, `168 cm` (smart
  quotes too); a bare number is inches in ft-in mode, metres in metre mode. Labels "Shelf 6'5"". Light and dark via the system theme.

## Tests (all with `/usr/bin/python3 -m pytest -q`)

- `tests/cdpr/test_room_map.py`: 26 tests, ~2.5 min (two full simulated startups). Data model and every refusal; exact tests vs dense
  sampling on 10 000 random segment/shape pairs (sampling may only miss grazing hits, never invent one; vectorised = scalar on 2000);
  5 cm pole missed by the old 24-sample test and caught now; deck shelf example; margin and claw body; old format = new cylinder and no
  shapes = unchanged; coverage < 150 ms for 10 shapes and the shelf's shadow; API round trip, every refusal (+ token / JSON), busy and
  state refusals, READY refusals for the pose and for the lowering, persistence (file) vs memory (sim); three-station startup
  (`robot.sim3.json`, fast profile) with a lamp 0.45 m from the resting claw reaches READY, the TRUE cables and claw never meet the lamp at
  any simulated step, and no calibration sample pose meets it.
- `tests/cdpr/test_room_map_app.py` + `tests/cdpr/map_app_check.js`: Playwright (Node package + preinstalled Chromium, as
  `test_phone_app_review.py`), 360 x 740 and 1280 x 800, 10 tests: circle by tap, rectangle by drag-and-drop, move, resize (rim and
  corner), height typed as `6'5"`, overlay, save ("Saved: the planner now avoids 2 shapes"), reload brings both back, PAUSE and the
  e-stop line in view and topmost after every step, no horizontal scroll, text contrast >= 4.5:1 light and dark (shape labels, map
  text, inspector, palette, More, e-stop line). `MAP_SCREENSHOTS=<dir>` also writes the screenshots.
- Timings: coverage 8-26 ms for 10 shapes on the 3.35 x 2.74 m room (34 x 28 cells, grip + approach heights); preview round trip in
  the test client < 30 ms.
- Full affected suite (tests/cdpr, tests/test_app.py, tests/test_geometry.py, tests/test_kinematics.py): see "Suite result" below.

## Suite result

Command: `/usr/bin/python3 -m pytest -q -p no:logging tests/cdpr tests/test_app.py tests/test_geometry.py tests/test_kinematics.py`,
run as four parallel groups (no pytest-xdist here): 798 passed, 8 failed, 1 skipped (807 tests, ~26 min wall).
- 2 failures pre-exist on the base commit 17f3730 (`test_tiny_moves.py::test_task_runner_move_handles_a_tiny_or_zero_move[offset0/1]`).
- 5 were pump-gap timing tests (`test_keepalive_pumping.py`, `test_keepalive_fix_review.py`, `test_task_reach.py`) that fail only under
  the 4x parallel CPU load; run alone they pass.
- 1 was real and is fixed: the static guard `test_the_slow_calls_of_the_armed_startup_are_the_arguments_of_the_pumped_helper` (the
  room-map detour had added a second pumped `plan_line_from` / `pose_from_positions` call site; it now reuses one `_plan_to` helper and
  the stage's own pose).
- After the fix, serially: `test_room_map.py`, `test_room_map_app.py`, `test_keepalive_pumping.py`, `test_keepalive_fix_review.py`,
  `test_task_reach.py`: 77 passed (11 min).
Net: everything passes except the 2 pre-existing `test_tiny_moves` cases.

## Deviations and decisions to confirm

1. **Margin vs the deck example.** The deck's shelf example (claw at the room centre refused at 0.8 m, clear at 1.5 m) holds with no
   margin. With the spec's 0.10 m margin (sideways and in height) 1.5 m is refused too; the claw clears from about 1.65 m. The test checks
   both.
2. **"Old cylinder entries give the same answers"** is read as: an old entry gives exactly the answers of the equivalent new cylinder.
   Old entries now get the margin and the claw-body check like every shape, so they are stricter than the old 24-sample test (which
   also missed thin poles). No shipped config had obstacles.
3. **Coverage model.** A cell is the claw upright at the held yaw at the grip height and at the approach height over a 0.10 m item
   (every 0.1 m between), cables to the attachment points, the claw body over that whole descent. No tension LP per cell (too slow
   for 150 ms); the usable area (wall margin box, three-station triangle) stands in for it. Before the first calibration every free
   cell shows "not calibrated there".
4. **Units preference** is stored with the map (`map_units`, sent with Save) and the phone also remembers the last choice for the session.
5. **Inspector** is a card under the map rather than a sheet over it: on a 360 x 740 phone a sheet covered the map and the selected
   shape could not be dragged (found by the browser test).
6. **Bare numbers** in ft-in mode are inches.

## Not done / open

- Independent verification (spec 5) by another agent.
- The other startup motions (visual initialisation moves, reference verification, lowering, recovery) use the same planner check, so
  they refuse a move through a shape, but only the calibration stage routes around one; a refusal elsewhere still stops the startup with
  the reason. The supervisor's "lower" refuses the planned descent and falls back to cable packets (existing behaviour); a shape under
  the claw is what `PUT` refuses in READY/PAUSED, but a map saved while DISARMED is not checked against where the claw will be lowered.
- No browser test of the hamper card, units switch or undo (they are exercised manually through the screenshots run only).
- Pre-existing failures unrelated to this work: `tests/cdpr/test_tiny_moves.py::test_task_runner_move_handles_a_tiny_or_zero_move`
  (2 cases) fail on the base commit 17f3730 too (the fake context has no `wait` for `run_pumped`).

## Suggestions for the other tabs (not changed)

- "Trust" on Home and "Calibration result and trust" on Setup: plain words would help ("How sure the robot is of its position").
- Setup mixes room entry (a), configuration status (b), the checklist and Start (c, d) and results (e) in one long page; Start could sit
  at the top with the checklist, the rest folded.
- The anchors' x/y/z inputs on Setup have no units hint beyond the card title; the room size could reuse the Map tab's ft-in parser.
- "Acknowledge fault" / "Recover (re-reference from camera)" are jargon; a one-line "what happens" under each would help.

## Round 1 fixes after the independent verification (`verification/room_map_verification.md`, FAIL)

| finding | fix |
|---|---|
| H-2 lowering into a shape | `Supervisor.lower`: with a map, the landing is chosen first (`_landing_spot`, on the pumped worker): over the marker if the move there and the straight descent plan; else the start point, then the nearest point of a 10 cm grid of the usable area whose claw-body descent column is clear and whose moves plan; none: `CommandRefused("Can't lower: the Ottoman is under the landing spot. Move it on the Map, or lower by hand.")`, still holding. A map-caused refusal of a planned leg never falls back to packets (the fallback stays for its other reasons). Without a usable model, packets straight down are refused if a shape is under the claw. `PUT /api/room_map` refuses, in every state, a map whose shapes cover the landing column (claw body, floor up to `motion.task_max_height_m`) over the floor marker or the start point, naming the shape; `GET` returns `landing_m` and the app never places a new shape there. |
| H-1 detour strands the claw | `plan_line_from` puts a start pose less than 1 mm outside the workspace box on the bound (`START_BOUND_TOL_M`); the detour goes over the shape at the lowest height (0.1 m steps) at which up/across/down all plan, never above the top less `motion.waypoint_inset_m` (0.03 m, new config key). |
| M-1 room edit | `POST /api/room` re-validates the saved map and hamper against the new room and refuses with the shapes named ("Move or resize those shapes on the Map first"). |
| M-2 plain words | Service messages name keys in words ("its bottom", "its length") and unnamed shapes by kind and place ("the 4th shape on the map (a rectangle)", "the unnamed square at 1.20, 0.80 m"); the app checks sizes and heights in the user's units before saving and turns the coverage grid's "shape o3" into the shape's label. The coverage text itself keeps the id (the verifier's per-cell reference matches it). |
| M-3 hamper | The whole hamper marker (at least 48 px) takes the drag; the ring is drawn separately. |
| M-4 labels | Greedy placement: each label (hamper first) takes the first free spot near its centre (lines above/below, a little to the side), inside the drawing; hanging shapes are drawn first; new shapes avoid the hamper. |
| M-5 blocked startup | Calibration aborts after map refusals name the shapes and say "Edit the Map"; the lift refusal says so too. |
| L-1 units | Units are part of the saved map (dirty, undo); the server's value wins on load. |
| L-2 thin shapes | Every shape has a grab area at least 44 px wide (transparent, over its body). |
| L-3 Hamper label | Opaque pill behind it. |
| L-4 zero height | Refused in the field ("is not a height"). |
| L-5 typed value | A typed value is always applied, even when it reads like the shown one. |
| L-7 hamper in a shape | Refused ("the hamper is inside the Desk"). |
| L-8 task summary | "N delivered, M could not be picked up (...)" when items were skipped. |
| L-6 preview while busy | Not changed: coverage competes for the GIL with the pumping command thread (the switch interval is lowered on purpose); idle it is 13 ms. Option: refuse or cache the preview while a command runs. |

Verifier tests that now XPASS (strict): H-1 (`test_three_station_startup_with_a_pole_0_25_m_from_the_start_reaches_ready`,
`test_after_the_detours_up_leg_the_next_move_can_be_planned`), M-1, and in the browser file L-2, L-3, L-4, M-2, M-3, M-4 (each per
configuration). H-2's verifier test cannot flip: it saves an ottoman over the marker and expects 200, which the lead's rule now refuses.
The same rule refuses some maps the verifier's other scenarios save (three-station shelves 0.33 / 0.55 m from the resting claw, and the
app script's "save and reload" desk turned 30 degrees near the room centre): those setups now get 409 "covers the claw's landing spot".

New own tests (`tests/cdpr/test_room_map.py`): plain messages, room edit refused, hamper in a shape and landing spot refused, moves from
one microstep past the top and from every detour apex, lowering never enters a shape (refuses with the name or lands elsewhere).
