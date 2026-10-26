# Room map (Map tab, planner, API): independent verification, 2026-10-26

Scope: `docs/ROOM_MAP_SPEC.md` sections 1-5 (incl. "Simple first"), branch `claude/magical-cerf-gqr7j7`, commits
`8b933e2..9be3fbb`. The verifier did not write the feature. The builder's note (`verification/room_map_build_notes.md`) was read
for orientation only. Product code was not changed.

## Verdict: FAIL (not ready for hardware)

The core of the feature is sound. Two High findings must be fixed before the robot runs on hardware with a map:

- the exact segment tests, the margin, the claw-body check, validation, the API state rules, persistence, coverage and the
  Map tab's basic editing all pass;
- **H-2:** lowering descends into a shape that the map has just refused;
- **H-1:** the builder's new calibration detour strands the claw at the top of the workspace and ends the startup in
  RECOVERY_REQUIRED.

Once H-1 and H-2 are fixed and re-verified, the expected verdict is PASS WITH CONDITIONS (the Medium findings).

## Findings

| id | severity | finding | expected | measured | reproduce |
|---|---|---|---|---|---|
| H-2 | **High** | `Supervisor.lower` refuses the planned descent because of a shape, then falls back to equal cable pay-out packets at the same place. The claw is lowered into the shape the map just refused. `PUT` in READY checks the straight lowering from the claw's current xy only, not the descent over the floor marker, where `lower()` actually goes down. | Spec 3.4: lowering uses the map; the claw never enters a shape | Log: `lower: descend refused (workspace: the claw would enter the Ottoman); using cable packets`, then 95 `lower packet` moves at the marker. The true claw body was 0.070 m inside the 0.30 m ottoman, its axis inside the footprint. In the sim the virtual box is passed through and the robot reports PARKED. On hardware the claw lands on the furniture. | `pytest tests/cdpr/test_room_map_verify.py -k lowering` (xfail strict). Setup: READY, claw at 1.25 m beside the marker, `PUT` a 0.5 x 0.5 x 0.30 m box centred on the marker (accepted), then `sup.lower()` |
| H-1 | **High** | The calibration detour ("up, across, down", `startup._around_the_map`) ends its "up" leg at exactly `ws.hi[2]`. The stations then hold positions whose forward kinematics can lie micrometres above the limit. The "across" leg, and then the next calibration move, are refused with `workspace: z=2.148 above 2.148`. That second refusal is not a map refusal, so the startup aborts. In three-station mode the "up" leg to the top is also often tension-infeasible (12.3 N > 12.0 N). | Spec 5 (startup): a startup with a shape near the start point reaches READY, and the detour works | sim3 with one 5 cm pole near the start point: RECOVERY_REQUIRED `expanded: workspace: z=2.148 above 2.148`, claw left suspended at the ceiling margin (about 2.15 m). Four-station sim (dresser 0.55 m + pole, earlier run): RECOVERY_REQUIRED `local: workspace: z=2.193 above 2.193`. Deterministic: of the 81 station positions within ±1 microstep of a pose at exactly `ws.hi[z]`, 31 refuse every next move. | `pytest tests/cdpr/test_room_map_verify.py -k "pole_0_25 or up_leg"` (both xfail strict) |
| M-1 | Medium | `POST /api/room` (Setup) changes the room size without re-validating the saved map. In hardware mode the file is rewritten with shapes that are now outside the room or above the ceiling, and `load_config` refuses it at the next start. | Refuse the room change with a reason, or keep the file loadable | Shrink to 3.0 x 2.4 x 2.4 m with a shelf at (3.1, 2.5), 2.6 m tall: the room edit is accepted and `load_config(robot.json)` raises ConfigError | `pytest tests/cdpr/test_room_map_verify.py -k room_size` (xfail strict) |
| M-2 | Medium | The user sees refusals with internal key names, metres in ft-in mode, and ids (spec 1: plain words) | Plain words, the shape's name, the user's units | `Not saved: shape 2: bottom height z_low_m 0.00 m must be below its top height_m 0.00 m`; `Not saved: shape 2: length_m 6.10 m is larger than the room (3.35 x 2.74 m)`; cell tap: `cable A would cross shape o1` | `pytest tests/cdpr/test_room_map_app_verify.py -k plain` (xfail strict) |
| M-3 | Medium | The hamper reacts only to its 3 px ring (`fill: none`). A finger on the middle of the hamper deselects instead of dragging it, and its panel says "Drag the green circle" | The hamper body can be grabbed (44 px target) | Drag from the ring moved it 0.35 m; drag from the centre moved it 0.00 m (all 4 configurations) | `pytest tests/cdpr/test_room_map_app_verify.py -k middle` (xfail strict) |
| M-4 | Medium | Labels are centred on their shape with no collision handling, and shapes are drawn in list order. A hanging shape's opaque fill hides the floor shapes under it. | Labels readable, not overlapping | Tapping Square, Rectangle and Circle (the first thing a user does) already overlaps "Square 2'6"" and "Circle 2'6"" by 14 x 15 px at 360 px. A circle moved onto the hamper overlaps "Hamper" by 48 x 13 px; this is the lead's screenshot, reproduced in `08_circle_on_hamper_*`. "Ceiling fan (hangs, from 7'6")" (about 190 px wide) covers "Chair" and hides the lamp under the fan. "Dresser 2'10"" is clipped at the wall. `freeSpot` ignores the hamper, so new shapes are placed touching it. | `pytest tests/cdpr/test_room_map_app_verify.py -k overlap` (xfail strict); screenshots `03_*`, `07_*`, `08_*` |
| M-5 | Medium | One tall shelf with its side 0.19 m from the resting claw blocks every local calibration pose and the way over them. The startup ends in RECOVERY_REQUIRED (claw suspended) with `expanded: only 13 feasible visible poses (need 15)`, which names neither the map nor the shelf. Nothing warns before Start. | A pre-start warning ("the Shelf is too close to the start point"), or a refusal that names the shape | 22 poses skipped (`up: workspace: cable C would cross the Shelf`), then RECOVERY_REQUIRED | `pytest tests/cdpr/test_room_map_verify.py -k plain_words` (xfail strict) |
| L-1 | Low | Changing units alone cannot be saved: `draftKey()` holds only shapes and the hamper, so Save stays disabled. The choice lives in `localStorage` and overrides the server's `map_units`. | Spec 2: units preference saved with the map | Code inspection (`app.js` `draftKey`, `mapLoad`) | none |
| L-2 | Low | A thin shape is drawn smaller than a finger, and its body is the only way to select it | 44 px targets | 5 cm pole 4.6 px, 40 cm lamp 36.6 px, at 360 px | `-k grabbed` (xfail strict) |
| L-3 | Low | The green "Hamper" label falls below 4.5:1 when it sits on a shape or on the overlay tint | >= 4.5:1 | light 3.98 on a shape, 3.43 on the overlay; dark 4.45 / 3.96. All other text passes, HTML and SVG. | `-k hamper_label` (xfail strict) |
| L-4 | Low | The height field accepts 0. Save is then refused with the jargon of M-2. | Refused in the field | `0` -> `height_m = 0` | `-k zero_height` (xfail strict) |
| L-5 | Low | The default height 0.75 m already displays as 2'6", so typing `2'6"` changes nothing: the user gets 0.750 m, not 0.762 m | Exact value typed | Walkthrough: height 0.750 m stored (all 4 configurations) | walkthrough evidence |
| L-6 | Low | While a command runs, the preview (the "Where can it pick?" overlay) takes 1.5-2.5 s instead of < 150 ms. The coverage computation itself is slowed (GIL contention with the pumping command thread, which lowers the switch interval). It never blocks on the robot lock. | Spec 3.5: < 150 ms (holds when idle) | Coverage compute 1.8-2.5 s while busy, 136-600 ms at start or end; idle 13 ms | evidence `preview_while_busy_*` |
| L-7 | Low | A hamper placed inside a shape (e.g. under a desk) is accepted | Refused or warned | `PUT` 200 | inline check in this report |
| L-8 | Low (pre-existing) | A task whose remaining items are all "unreachable" (now often because of a shape) ends with "0 delivered, room clear" | "2 items could not be reached" | `tasks.py:349` | evidence `sim4_task` |
| I-1 | Info | The true (simulated) cables used up to 38 mm of the 100 mm margin while no planned pose came closer than 2-8 mm to the inflated shape (model error before and around calibration, priors off by 4 cm). The real shape was never touched. The margin is doing its job; keep it at 0.10 m or more. | | sim3 shelf 0.55 m: true cable 65 mm from the real shelf; sim3 pole: 62 mm | evidence `sim3_startup_*` |

## 1. Geometry (own reference)

Reference: a separate max-of-slabs signed function. It is convex along any line, so it is minimised exactly per segment
(dense scan plus golden section), and a plain 20 001-point sampler is also run.

- **Random cases:** 12 000 shape/segment pairs. Boxes at any yaw (0, 45, 90, 180, 359.999 and random), cylinders, 40 % hanging
  (`z_low > 0`), margins 0 / 0.05 / 0.10 / 0.15 m. Segment modes: endpoints inside, both inside, vertical, horizontal at the
  top / bottom face ±3 mm, cable-like from a corner, zero length, and tangent lines shifted ±2 mm (grazing). Result: **0 false
  negatives, 0 false positives**. The dense sampler never invented a hit. The vectorised form (coverage) agrees on all 12 000.
- **Hand cases:**
  - box corner ±1 mm, at 5 yaws;
  - vertical through or 1 mm above the top;
  - hanging box passed under;
  - tangent ±1 mm on the cylinder;
  - vertical under a hanging cylinder.
- **Margin:** for 300 random shapes and margins of 0.02-0.2 m, a hit at margin - 1 mm and none at margin + 1 mm, sideways (any
  direction, corners included), above the top, and below a hanging bottom.
- **5 cm pole:** on a random cable's line at random places, offset up to 24 mm: always caught (693 cases), and 166 of them are
  missed by the old 24-sample test. Offset by 26 mm with margin 0: not refused. With the default margin it is caught up to
  124 mm.
- **Claw body:** checked against a brute-force footprint distance (boundary sampling) at ±2 mm of margin + radius (0.17 m), over
  the shape's height band, at margin ±2 mm above the top, and below hanging bottoms. All agree. Messages: "the claw would enter
  the Shelf".

## 2. Configuration

Every rule is refused with a message, by `validate_obstacles` and by `load_config` (26 parametrised cases):

- unknown or missing shape;
- size exactly 2 cm, or negative;
- larger than the room;
- `z_low == height`, and `z_low < 0`;
- a top above the ceiling + 5.1 cm (+5.0 cm is accepted);
- a centre 1 mm outside the room (a centre on the wall line is accepted);
- NaN, inf, a bool or text where a number belongs;
- a foreign key, a name over 40 characters, an empty id;
- 51 shapes (50 accepted), and duplicate ids.

Old `{x, y, r, z_low, z_high}` entries load as cylinders, are still validated, can be mixed with new entries, and give identical
`violations()` on 500 poses.

**Without obstacles nothing changed.** In a subprocess against a `git worktree` of `8b933e2`:
- `violations()` for 3000 random points per profile (sim, sim3), and with `allow_low`;
- two planned line moves (times and positions).

All identical to HEAD.

## 3. Planner safety (simulated, actual executed plans)

`MotionRecorder` wraps `co.execute` (every executed plan, with the model geometry and the map in force) and `world.step` (the
TRUE plant every step). Each executed Cartesian plan is densified to 5 mm and checked against every shape inflated by the margin:
each cable segment (exact minimum) and the claw body. The true cables and claw are checked against the real shapes. Maps are
saved through `PUT /api/room_map` while DISARMED; the startup runs through `POST /api/command`.

**Planned and true clearance:**

| scenario | outcome | planned min clearance to inflated shape | true min clearance to real shape |
|---|---|---|---|
| sim3, 1.8 m shelf 0.55 m from the start | READY | +3.7 mm | cable 65 mm, body 98 mm |
| sim3, 5 cm pole near the start | RECOVERY_REQUIRED (H-1: `intermediate: workspace: z=2.154 above 2.154`; another run `expanded: ... 2.148`) | +8 to +17 mm (incl. the detour's "up" leg) | cable 62 mm, body 80 mm |
| sim3, shelf side 0.19 m from the claw | RECOVERY_REQUIRED (M-5), 22 poses skipped | no Cartesian move | cable 112 mm |
| sim4, dresser + pole saved while DISARMED | READY | +50 mm | 163 mm |
| sim4 task: 2 items, a 5 cm floor lamp 0.12 m from item 0 | both "unreachable: ... the claw would enter the Floor lamp", no move toward them | (scan moves only) | no contact |
| sim4 task: an ottoman 0.30 m from item 0 | **2 delivered** (approach, descend, lift, verify shift, raise, transport) | +5 mm (another run +47 mm) | no contact |
| sim4 lowering, ottoman over the marker | **claw lowered into it (H-2)** | descent refused, then unplanned packets | **-70 mm (inside)** |

**Results:**
- Every planned pose of every executed plan was clear of every inflated shape (the lowering packets are not planned poses: H-2).
- The lift check refuses a resting claw whose straight lift meets a shape, with a plain message, before any lifting packet.
  Its own map and the claw's resting pose were also exercised.

**State rules in READY and in PAUSED** (`PUT`):
- a cabinet 0.15 m from the claw axis (inside margin + body): refused, "current pose";
- a hanging lamp 5 cm above the attachment plane: refused, "current pose";
- a table 0.11 m under the claw's lowest point: refused, "lowering ... at 0.93 m";
- a chair 1.4 m away: accepted. The live `ctx.ws` gets it at once: a line through the chair is refused.

**While the startup runs:** 5 out of 5 `PUT`s were refused with "busy with 'start'", and `preview` answered (see L-6 for the
timing).

## 4. API

- **Token:** all three endpoints refuse no token, an empty token, a wrong token, a truncated token and the token in the URL
  (401). A `PUT` without a JSON body gets 415.
- **GET** returns the room, anchors (an inactive D is marked), usable box, a three-station triangle that is inside the anchors'
  triangle and contains the start point, the hamper and the units.
- **Preview never saves:** valid, invalid, non-list and empty bodies leave the hardware config file byte-identical and leave
  `cfg` and `GET` unchanged. An invalid `PUT` gets 400 and leaves the file byte-identical.
- **`PUT` in hardware mode** writes `obstacles`, `map_units` and `tasks.hamper_*`, keeps every other key, and the file reloads
  through `load_config`. An empty map is saved and reloads.
- **`PUT` in `--sim`** writes nothing (`robot.sim*.json` unchanged); memory only.
- **States:**
  - allowed in DISARMED and PARKED;
  - refused (409) in every other supervisor state: STARTUP, TASK, FAULT and RECOVERY_REQUIRED (the startup's steps all run
    inside STARTUP);
  - READY and PAUSED: see section 3.

## 5. Coverage

- **Full grid:** all 952 cells (34 x 28) were recomputed with the verifier's own geometry for 4 shapes: a shelf, a lamp, an
  unnamed turned box and a hanging fan. The reason per cell matches on every cell (cable / claw text exact; area; trust).
- **Hand checks:**
  - cell (1.75, 1.35): cable A from (0.05, 0.05, 2.593) to (1.708, 1.308, 0.527) is inside the shelf's inflated footprint for
    s = 0.262-0.739 and below its inflated top (2.0 m) for s >= 0.287, so "cable A would cross the Shelf";
  - lamp-only cell (2.85, 1.85): cable A's line passes 0.225 m from the lamp axis at 0.68 m height, so "cable A would cross the
    Lamp";
  - a wall cell: "area";
  - the unnamed box: "shape o4" (M-2);
  - under the fan: no fan reason at grip height.
- **Timing** (10 random shapes through `POST /api/room_map/preview`, idle): **server 13.0 ms median (max 13.7 ms), HTTP round
  trip 14.1 ms** (limit 150 ms). Busy: L-6.

## 6. App (Playwright, Chromium)

Configurations: 360 x 740 with real touch events (CDP) and 1280 x 800 with the mouse, each in light and dark, plus 320 px.
Results: 60 passed, 24 xfailed (the Low/Medium findings above, 6 per configuration).

**Simple first:**
- the first screen shows exactly: the empty-state hint, Square, Rectangle, Circle, Save map (disabled) and one "More";
- tabs are Home, Camera, Setup, Map and Chat only;
- the rectangle panel shows Length, Width and Height; the square panel shows Side and Height;
- Name, x, y, angle and "Hangs from the ceiling" are under the panel's "More";
- Undo, overlay, hamper and units are under the page "More".

**Editing:**
- add by tap;
- palette drag and drop with a real finger (dropped within 1 cm);
- move: the finger delta is reproduced within 1 in, snaps to the 1 in grid, and goes flush to the wall within 5 cm;
- resize: square by its side (stays square), rectangle by a corner, circle by its rim;
- Turn 90° (rectangles only), and the exact angle under More;
- undo to the start, capped at 20 steps;
- Save shows "Saved: the planner now avoids 4 shapes."; the dot clears, Revert restores, and a reload brings the map back;
- hamper: moved by its ring, rim height saved to `tasks` (M-3 for its middle);
- overlay: the reason of a tapped cell is shown, and it updates about 0.31-0.32 s after an edit.

**Parsing, ft-in mode** (all exact):
- `5'6"`, `66 in`, `5 ft 6 in`, `5' 6"`, `5'6`, `66"`, `66` and `5’6”` all give 1.6764 m;
- `1.68 m`, `168 cm`, `1,68 m` and `1680 mm` give 1.68 m;
- `5'` and `2 ft` are also correct;
- `abc` and `-1 m` are refused with a hint;
- `0` is accepted (L-4).

**Parsing, metre mode:** a bare `1.68` is metres. Labels switch to "0.75 m".

**PAUSE and the e-stop line:** visible and topmost (elementFromPoint at 3 points) after every step, with the panel open and
scrolled to the bottom, and at 320 px. No horizontal scroll at 320, 360 or 1280 px.

**Contrast:** every HTML text on the tab, light and dark, incl. the panel, chips, overlay legend and placeholders, is >= 4.5:1.
SVG labels were measured from screenshot pixels; only "Hamper" fails, on shapes and on the tint (L-3).

**Touch targets:** all buttons, fields, summaries, chips, checkbox rows, tabs and handles (44.0 px) are >= 44 px, also at 320
px. Thin shapes are not (L-2).

**Words:** no "keep-out", "violation(s)", "coverage" or "obstacle" anywhere in the normal screens or the overlay. The refusal
messages fail (M-2).

**Render:** one drag frame (`mapRender`) with 50 shapes takes 3.4-3.8 ms.

**Label overlap, characterised (M-4):**
- `03_three_by_tap_*`: the first three taps already collide.
- `08_circle_on_hamper_*`: the lead's case. The label is centred on its shape, the "Hamper" label is centred on the hamper, and
  nothing moves either one. The hamper ring is also drawn over the shape.
- `07_crowded_labels_*`:
  - the hanging fan's label (190 px) overlaps "Chair";
  - the fan's fill hides the lamp under it (draw order);
  - "Dresser 2'10"" is clipped at the left wall.

**First-time-user walkthrough:** "Desk 4 ft x 2 ft, 2'6" tall", then save, at 360 x 740.
- **Typed route: 5 taps** (Rectangle, Length, Width, Height, Save map), typing 3 values, and about 430 px of scrolling to reach
  Save. The panel appears below the map at y = 396 px, on screen above the dock at 578 px. Tapping Save straight after typing,
  with no Enter, saves the typed values: 4'0" x 2'0", height see L-5. The page still shifts after Save; the message line
  changes.
- **Chip route: 3 taps** (Rectangle, "Desk", Save map). The Desk chip is exactly 4'0" x 2'0" x 2'6" (1.22 x 0.61 x 0.76 m).
- **What confused me:**
  - after the tap, the message says "set its size and height below", but on a phone the panel is below the map and Save is
    further down still: two screens of scrolling;
  - the unexplained blue dashed rectangle (usable area) and the small blue circle (start point) have no legend on the main
    screen;
  - the new rectangle lands touching the hamper;
  - "Turned (degrees)" and "Position x (from wall A-D)" use the anchor letters, which a first-time user has to look up on the
    map;
  - the toast "Saved: …" covers the chips for about 3 s.

## 7. Suite

Full affected suite on HEAD:
`/usr/bin/python3 -m pytest -q -p no:logging tests/cdpr tests/test_app.py tests/test_geometry.py tests/test_kinematics.py`.
Result: **801 passed, 5 failed, 1 skipped** (44 min). It ran while the verifier's own simulations and browser runs loaded the
CPU.

- **3 failures are timing-only:**
  - `test_keepalive_fix_review::test_n2_...`;
  - `test_keepalive_pumping::test_a_full_simulated_startup_...`;
  - `test_task_reach::test_a_whole_task_with_a_one_second_detector_...`.

  Re-run alone: **3 passed**.
- **2 failures pre-exist:** `test_tiny_moves.py::test_task_runner_move_handles_a_tiny_or_zero_move[offset0/1]`. **Confirmed on
  the base:** a `git worktree add /tmp/base 8b933e2` gives the same 2 failures (`2 failed, 50 passed`; `AttributeError` at
  `startup.py:445`, the fake context has no `wait`). The builder's note names the base as 17f3730; the stated base 8b933e2 also
  has them.

**Verifier's files:** `tests/cdpr/test_room_map_verify.py` and `tests/cdpr/test_room_map_app_verify.py` (+ the Playwright
script `tests/cdpr/map_app_verify.js`).
- Final run: `/usr/bin/python3 -m pytest -q tests/cdpr/test_room_map_verify.py tests/cdpr/test_room_map_app_verify.py`.
  Result: **118 passed, 7 skipped, 33 xfailed** (10 min).
- The 33 xfails are the strict markers of the findings above: H-1, H-2, M-1 to M-5 and L-2 to L-4. Some appear once per
  scenario or per browser configuration.
- 5 of the skips were placeholder states that do not exist in the supervisor. That test was then reparametrised over the real
  states (4 passed), so the file now gives 118 passed, 2 skipped, 33 xfailed.
- The other 2 skips: "reaches READY" is asserted only for the case expected to reach it.

## Evidence

- `verification/room_map_verify_evidence.json`: measured numbers per test.
- `verification/room_map_verify_screens/`: screenshots per configuration:
  - `01_first`, `03_three_by_tap`, `04_inspector`, `05_reloaded`, `06_overlay`, `07_crowded_labels`, `08_circle_on_hamper`,
    `09_320px`;
  - each at `_360x740_light`, `_360x740_dark`, `_1280x800_light` and `_1280x800_dark`.
- The base worktree for the compatibility test: `ROOM_MAP_BASE=/tmp/base` (the test is skipped without it).
