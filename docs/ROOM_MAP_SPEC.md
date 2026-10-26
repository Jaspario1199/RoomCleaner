# Room map: keep-out shapes drawn in the app (spec, 2026-10-21)

Decision D35 (Jasper, 10/21):
- **Now:** the user draws the room's obstacles in the phone app (squares, rectangles and circles, each with its size and
  height), and the robot plans around them.
- **Later:** the robot builds its own model of the room from the claw camera. It proposes shapes, and the user accepts
  them in the same editor.

Today the planner already refuses any path where a cable line or the claw would cross a keep-out cylinder
(`roomcleaner/cdpr/kinematics.py` `Workspace.violations`, `config.obstacles`). The only way to enter one is to hand-edit
the config, and only cylinders are supported. This spec makes the map a first-class, user-friendly part of setup.

## 1. What the user can do

On a new **Map** tab, the user sees a top view of the room:
- the walls;
- the anchors A-D (an unmounted station is greyed out);
- in three-station mode, the usable area (the triangle shrunk by its edge margins) and the start point;
- the hamper.

| action | how (phone first; mouse works the same) |
|---|---|
| add a shape | tap **Square**, **Rectangle** or **Circle** in the palette: the shape appears in the middle of the free floor, selected. Dragging a palette button onto the map drops it where the finger lifts. |
| move | drag the shape's body; it snaps to 1 in (2.5 cm) and flush to a wall within 5 cm |
| resize | drag a corner handle (rectangle), the side handle (square keeps its sides equal) or the rim handle (circle) |
| rotate (rectangle) | a rotate button: 90 degree steps, plus a numeric angle in the inspector |
| exact values | the inspector (bottom sheet) for the selected shape: name, L x W, side or diameter, **height**, position x / y, rotation, "hangs from the ceiling" (then a bottom height, e.g. a fan or a pendant lamp), duplicate, delete |
| name quickly | chips: Bed, Desk, Dresser, Shelf, Chair, Lamp, Ceiling fan, Other. A chip pre-fills typical sizes, which the user then edits |
| units | ft-in or metres toggle (default ft-in). Fields accept `5'6"`, `66 in`, `1.68 m`, `168 cm`. Everything is stored in metres |
| undo | the last 20 edits |
| see the effect | toggle **Where can it pick?** It shades the floor in a 10 cm grid: reachable for a grip, blocked by a shape (tap a cell: "cable B would cross the Shelf"), outside the usable area, or outside the trusted (calibrated) volume. It updates about 0.3 s after an edit, before saving |
| hamper | the hamper marker is draggable too (`tasks.hamper_room_m`); its rim height is in its inspector (`tasks.hamper_height_m`) |
| save | **Save map**. Afterwards: "Saved: the planner now avoids 3 shapes". Unsaved changes show a dot on the tab and a Revert button |

**Simple first (Jasper, 10/26: "make sure the app is easy to navigate and simple as possible").**
- **Main screen:** the room, the shapes, three big buttons (Square, Rectangle, Circle) and Save. Everything else (units,
  undo history, "Where can it pick?", hamper settings, exact angle) sits behind one "More" control.
- **Shape panel:** name chip, size and height only; the bottom height, x/y and angle go under "More".
- **Words:** plain ("keep the robot away from this"), never "keep-out", "violations" or "coverage".
- **One obvious next step at a time,** and an empty-state hint when there are no shapes.
- **Navigation:** no new top-level navigation beyond the Map tab.

PAUSE and the emergency-stop line stay visible above everything, as on every other tab (phone-app review F14).

The user experience must be good on a phone (Jasper's request):
- touch targets of at least 44 px;
- drag at 60 fps (pointer events, no layout thrash);
- no horizontal page scroll at 320 px;
- light and dark themes, 4.5:1 text contrast;
- the map fills the width and keeps the room's aspect ratio;
- shapes are labelled with their name and height ("Shelf 6'3"").

## 2. Data model (room frame, metres; origin at the floor corner under anchor A, x along the A-B wall, z up)

```json
{"obstacles": [
  {"id": "o1", "name": "Shelf", "shape": "box", "x": 0.83, "y": 0.68, "length_m": 0.80, "width_m": 0.40, "yaw_deg": 0,
   "z_low_m": 0.0, "height_m": 1.90},
  {"id": "o2", "name": "Ceiling fan", "shape": "cylinder", "x": 1.68, "y": 1.37, "diameter_m": 1.10,
   "z_low_m": 2.25, "height_m": 2.74}
]}
```

- `height_m` is the **top** of the shape above the floor. `z_low_m` is its bottom (0 = stands on the floor).
- A square is a box with `length_m == width_m`; the app keeps them equal.
- The existing format `{x, y, r, z_low, z_high, name}` still loads; it is a cylinder.
- Stored in the config's existing `obstacles` key, exactly as `Service.set_room` stores the room and anchors (the config
  file is rewritten; in `--sim` the change lives in memory only). One source of truth: `load_config` validates it at every start.
- Validation (refused with a message):
  - unknown shape;
  - a size of 2 cm or less, or larger than the room;
  - `z_low_m >= height_m`;
  - a height above the ceiling (+ 0.05 m);
  - a centre outside the room;
  - more than 50 shapes.

## 3. Planner (what "operate with that info" means)

1. **Exact tests, not samples.** Today's cylinder test samples 24 points per cable (12 cm apart on a 3 m line), so a pole
   thinner than about 12 cm can slip between samples.
   - Replace it with exact segment tests: cylinder (circle interval intersected with the z interval) and oriented box (slab
     test in the box frame), as gen 1 did for its fan (`roomcleaner/geometry.py` `segment_intersects_cylinder`).
2. **Safety margin.** Every shape is inflated by `motion.obstacle_margin_m` (default 0.10 m), sideways and in height.
3. **The claw body too.** The claw must not enter a shape. Its vertical extent (lowest point to attachment plane), widened
   by `claw.body_radius_m` (default 0.07 m), is checked against each inflated shape. The cables are already checked.
4. Everything that plans uses it unchanged: moves, tasks, lowering, recovery, and the startup's calibration poses
   (`startup.py` already filters excitation poses through `ws.violations`).
5. **Coverage** for the app: `coverage(draft_map, heights)` returns the 10 cm floor grid with, per cell, the first reason a
   grip there is impossible (shape name and cable, usable area, trusted volume). It must run in under 150 ms for 10 shapes:
   vectorised numpy, on the HTTP thread, never holding the robot lock.
6. **Unreachable items are skipped, not fatal.** Today a refused approach stops the whole task (FAULT). It should mark the
   item "unreachable: cable B would cross the Shelf", skip it and go on. This is in `tasks.py`; do it after the task-pumping
   fix lands.

## 4. API

| endpoint | does |
|---|---|
| `GET /api/room_map` | the saved shapes, hamper and units preference, plus the room, anchors, active stations, usable-area polygon and start point for drawing |
| `POST /api/room_map/preview` | body = a draft map; returns validation errors and the coverage grid. Saves nothing |
| `PUT /api/room_map` | validate and save |

`PUT` is allowed:
- in DISARMED and PARKED;
- in READY and PAUSED only if the claw's current pose, and the vertical lowering from it, stay valid with the new map;
  otherwise it is refused, with the reason.

`PUT` is never allowed while a command runs (STARTUP, TASK, lowering): "busy". All three endpoints use the session token,
like every other `/api` call.

## 5. Tests and acceptance

- **Geometry:** the exact tests agree with dense brute-force sampling on 10 000 random segment/shape pairs. A 5 cm pole that
  the old 24-sample test misses is caught. The deck's shelf example holds: claw at the room centre refused at 0.8 m, clear
  at 1.5 m.
- **Compatibility:** old cylinder entries load and give the same answers. A config without `obstacles` behaves exactly as before.
- **API:**
  - round trip;
  - each validation refusal;
  - refused while busy;
  - refused in READY when the claw's pose would become invalid;
  - persisted to the config file; in memory in `--sim`.
- **Coverage:** under 150 ms for 10 shapes; a shelf casts the expected "shadow".
- **Startup:** a simulated three-station startup with one shape near the start point still reaches READY, and no
  calibration pose violates the shape.
- **App (Playwright, Chromium at `/opt/pw-browsers`; 360 x 740 and 1280 x 800):**
  - add a circle by tap and a rectangle by drag;
  - move and resize them;
  - type a height in ft-in;
  - save;
  - reload: the shapes come back;
  - PAUSE stays visible and on top throughout;
  - no horizontal scroll;
  - dark-mode contrast at least 4.5:1.
- **Independent verification** by an agent that did not write it, before it is used on hardware.

## 6. Phase 2: the robot builds its own model (later)

- **Method.** The claw camera's pose is known at every scan (cable model plus floor board), so the robot can triangulate
  what it sees from two poses: depth Z = f·b/d, and δZ = Z²·δd/(f·b). With f ≈ 520 px, a baseline b = 0.3 m and Z = 1 m,
  δZ ≈ 3 mm per 0.5 px of disparity. The claw's own pose error (5-10 mm) dominates.
- **Output.** The scans are fused into a 2.5D height map of the floor: per cell, the highest thing in it.
- **User in the loop.** Detected objects appear in the editor as dashed "proposed" shapes that the user accepts, edits or
  rejects.
- **Limits.**
  - The camera looks down, so it sees what is below the claw, not tall furniture tops or a fan above it. Those stay
    user-drawn.
  - Textureless surfaces match poorly.
  - A map is static: people and pets are still not detected, so the rule "nobody under the robot" stays.
- **Optional import.** A phone room scan (photogrammetry, or a LiDAR room scanner that exports furniture as boxes) can be
  imported as proposed shapes, registered to the room frame by floor-board sheet 0.
