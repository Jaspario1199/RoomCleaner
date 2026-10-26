# Room scan: the robot builds its own model of its workspace (spec, lead, 2026-10-26)

Decision D35, "later" half; D44 (Jasper, 10/26: "using the vision to actually create a real-time model that's stored and
edited to update, so that the robot knows the sandbox it's playing in"). This expands section 6 of
`docs/ROOM_MAP_SPEC.md`. It builds on the Map tab (sections 1 to 5 there), which must exist first: the scan writes its
results into the same map and the same editor.

## 0. What it is and what it is not

The claw camera photographs the room below it from many **known** poses. The poses come from the cable model and the
floor-board calibration, and the trust ledger says how good they are. Two photos of the same spot from known positions
give depth by triangulation. The robot fuses that depth into a stored **2.5D height map**: per floor cell, the top of
whatever stands there. From it the robot:
- plans around obstacles it found itself;
- proposes shapes for the user to accept;
- shows a real photo of the room in the Map tab;
- notices later when something moved.

| In scope | Not in scope |
|---|---|
| Obstacles **below** the claw: furniture tops, boxes, piles, anything on the floor | Things above the claw (ceiling fan, lamp, shelf tops above the scan height): they stay user-drawn |
| A stored, versioned map that updates by re-scanning | Live detection of people or pets: "nobody under the robot" stays the rule |
| A photo mosaic of the floor | Full SLAM: the pose comes from the robot, never from the images |
| Optional offline 3D mesh export (OBJ/STL) | Using the mesh for planning: planning uses the height map |

**Safety principle.** A scan only ever **adds** keep-out. Every map change takes effect only when the user accepts it, or
by an automatic rule that can only make the robot more cautious (section 5). Nothing the camera sees can open space that
the user's own shapes close.

## 1. Inputs and preconditions

**Claw camera.** The fixed mode `SVGA-800x600-q10` (`claw_s3.ino`), with the intrinsics in `camera.intrinsics_file`
(`tools/calibrate_camera.py`). The camera-to-body transform is `claw.T_body_cam`.

**Pose per frame.**
- **Source:** the host's claw pose at the frame's capture time (`X-Capture-Us` mapped to host time, as `claw_link` already
  does), with its covariance from the trust ledger.
- **Settled frames only.** A frame is used only if the claw had settled: commanded speed 0 for at least
  `scan.settle_s` (default 0.8 s), and the attitude estimate is steady. A swinging claw blurs the pose.

**When a scan may run.**
- State READY, inside the **trusted volume**: the calibration says where the pose is good.
- Never with an item in the grip.
- Never over the hamper.

## 2. The survey flight (scan mode)

- **Pattern.** A boustrophedon (lawn-mower) grid over the usable floor area at a fixed scan height `scan.height_m`.
  - **Height:** default 1.2 m above the floor, clamped so the claw clears every known shape by its margin.
  - **Spacing:** chosen so each floor point is seen from at least three poses. Overlap ≥ 60 % along a line and ≥ 40 %
    between lines, from the camera's footprint at that height.
- **At each waypoint:** settle, grab 2 frames, keep the sharper (variance of the Laplacian), and store the frame with its
  pose and covariance.
- **Planning.** The waypoints go through the planner like any move. Every leg is checked against the current map,
  cables included; a waypoint that would violate it is skipped and reported, not forced.
- **Duration.** About 4 to 8 minutes for a 3.35 × 2.74 m room at 1.2 m. The app shows progress and an ETA, and **PAUSE**
  works as everywhere else.
- **Partial scan.** The user can draw a rectangle in the Map tab: "scan this area". The same pattern runs over that area
  only, which is what updates use (section 5).
- **Storage.** `data/<run>/scans/<scan_id>/` holds `frames/NNNN.jpg` and one `poses.jsonl` line per frame:
  pose, covariance, capture time, sharpness, and the calibration id it was taken under.

## 3. Building the height map

**Grid.**
- Room frame (`ROOM_MAP_SPEC.md` section 2), cell size `scan.cell_m` (default 0.05 m).
- Per cell: height `h` (top surface, m), confidence `c` (0 to 1), observation count, last-seen scan id, and a "free floor"
  flag.

**Method: plane-sweep stereo** (robust, no learned model, works with known poses):
1. **Undistort** each frame with the intrinsics.
2. **Pick neighbours.** For each frame, choose the 2 to 4 neighbours with the best baseline-to-depth ratio (target
   b/Z ≈ 0.2 to 0.4).
3. **Sweep candidate heights** z from the floor to `scan.max_obstacle_h_m` (default 1.0 m below the scan height) in 1 cm
   steps. For each z, warp the neighbours onto the horizontal plane at z through the reference frame. Score with zero-mean
   normalised cross-correlation over 7×7 patches.
4. **Accept a cell's height** only if the best score ≥ `scan.ncc_min` (default 0.6) and the best is clearly better than the
   second-best peak (ratio ≥ `scan.peak_ratio` 1.15). Otherwise the cell is "unknown", never "free".
5. **Fuse all frames** into the grid. Per cell, take the **highest** consistent surface over observations, weighted by
   score and by the pose covariance projected to that cell. A pose with large uncertainty counts less.

**Accuracy budget** (`ROOM_MAP_SPEC.md` §6):
- f ≈ 520 px, b = 0.3 m, Z = 1 m: δZ ≈ 3 mm per 0.5 px of matching error.
- The claw's pose error (5 to 10 mm) dominates. Expect about 1 to 3 cm in height and 2 to 5 cm in position.
- That sits inside the 0.10 m planner margin.

**Floor reference.** The floor-board sheets give a known z = 0 check. A scan whose floor cells deviate from 0 by more than
`scan.floor_tol_m` (default 0.02 m) is flagged "calibration suspect" and not merged.

**Weak surfaces.** Textureless, shiny or very dark areas come out "unknown". In the planner, unknown cells are treated as
obstacles up to `scan.unknown_assume_h_m` (default: the height of the tallest known shape nearby, at least 0.3 m) until
seen properly or until the user marks them free.

**Speed.** This runs on the laptop, in a background process, never on the control loop or the HTTP thread. Target under
2 minutes for a full-room scan on a normal laptop (numpy/OpenCV, downsampled 2×). `opencv-python` is already a dependency.

## 4. What the user sees (Map tab)

- **Layers** (toggles):
  - Photo: the stitched top-down mosaic, orthorectified onto z = 0 from the same frames and poses;
  - Height: a colour ramp, unknown cells hatched;
  - Shapes: the user's and the accepted ones;
  - Proposals: dashed outlines.
- **Proposals.**
  - The height map is segmented into connected regions above `scan.min_obstacle_h_m` (default 0.05 m). Each region is
    fitted with a rotated rectangle or a circle, whichever covers it tighter.
  - Each is offered as a dashed shape: "Proposed: box 1.18 × 0.61 m, 0.76 m tall (desk?)".
  - **Accept** turns it into a normal shape the user can edit. **Reject** hides it and remembers the rejection for that
    region.
  - Height is the region's 95th-percentile height, rounded up to 1 cm.
- **Keep-out.** Accepted shapes are planner keep-outs like any drawn shape. The raw height map is also a keep-out, but only
  where it is above the floor (section 5), so even unaccepted obstacles are avoided.
- **History.** Each scan is a version. "Compare to the previous scan" shows changed cells in colour, and the previous map
  can be restored.

## 5. Updates and change detection ("the sandbox stays current")

- **Before a task in an area,** if that area's last scan is older than `scan.max_age_h` (default 24 h) or the area was never
  scanned, run a **partial scan** of that area first. The app shows "checking the area".
- **During normal work,** every settled frame the robot takes anyway (task approaches, garment detection) is matched
  against the map at no extra flight. Cells whose height now differs by more than `scan.change_tol_m` (default 0.05 m)
  are marked "changed".
- **Rules for applying a change:**
  - **Taller or new:** applied to the planner keep-out at once, because it is more cautious. The user is told: "A new
    object about 0.4 m tall appeared near (1.2, 0.8)."
  - **Lower or gone:** shown as a proposal. It frees space only after the user accepts it.
- **Settings:** in Map → Scan settings, the user can turn the automatic rules off. Then only manual scans run.

## 6. Optional: 3D export

**"Export 3D model"** runs an offline reconstruction on the laptop. The stored frames with their **known** poses go to
COLMAP (`point_triangulator` with fixed poses, then dense MVS), when COLMAP is installed. That gives a mesh as OBJ/STL in
the room frame, in metres.

It is for looking at, importing into CAD, or measuring. It is never used for planning, and it is optional: the app says so
when COLMAP is not installed. It takes several minutes or more.

## 7. Phone-scan import (alternative input)

A phone room scan (iPhone LiDAR "room plan" boxes, or a photogrammetry mesh) can be imported as **proposals**. It is
registered to the room frame by floor-board sheet 0: the user taps its four corners in the scan's top view. The same
accept/reject flow applies.

## 8. Config keys (new `scan` block, every value with a default, documented in `docs/APP.md`)

`settle_s 0.8`, `height_m 1.2`, `cell_m 0.05`, `max_obstacle_h_m`, `ncc_min 0.6`, `peak_ratio 1.15`,
`floor_tol_m 0.02`, `min_obstacle_h_m 0.05`, `unknown_assume_h_m`, `change_tol_m 0.05`, `max_age_h 24`,
`auto_partial_scan true`, `auto_apply_taller true`.

## 9. API (all token-protected; scan commands are supervisor commands like Lower, refused when not allowed)

| endpoint | does |
|---|---|
| `POST /api/scan {area?}` | start a full or partial scan; answers with the plan (waypoints, ETA) or the refusal reason |
| `GET /api/scan/status` | progress, current waypoint, frames kept, ETA |
| `GET /api/scan/heightmap?id=` | the grid (PNG height ramp + JSON metadata) |
| `GET /api/scan/mosaic?id=` | the photo mosaic PNG |
| `GET /api/scan/proposals` / `POST /api/scan/proposals/{id} {accept|reject}` | the proposal flow |
| `POST /api/scan/export3d` | start the optional mesh export |

## 10. Phasing (each phase verified before the next)

| Phase | Delivers | Acceptance |
|---|---|---|
| S0 | Map tab (`ROOM_MAP_SPEC.md` §1 to 5) | its own section 5, independent verification |
| S1 | Scan mode: survey planner, settled-frame capture, storage | sim: a full-room plan with every leg valid; frames and poses stored; PAUSE mid-scan holds; refused outside READY or with a grip |
| S2 | Height-map builder + mosaic | **simulator**: render the sim room with known boxes from the sim camera, then run the builder. Box heights within 2 cm and footprints within 5 cm with the sim's pose noise; unknown cells never reported free; floor cells within 1 cm. **Bench**: a box of known size on the floor-board, measured with calipers, within 3 cm |
| S3 | Proposals in the editor; height-map keep-out in the planner | accept or reject round trip; a raw obstacle blocks a path before acceptance; the planner refuses a cable over an unaccepted 0.5 m box |
| S4 | Partial scans, change detection, auto rules | moving a box in the sim gives a "changed" region; taller applies at once, lower waits for acceptance; history restore |
| S5 | 3D export, phone-scan import | the export runs when COLMAP is present, with a clear message when absent; the import is registered within 3 cm on the board |

Every phase uses the usual roles: implementation by a builder agent, then an independent verification report in
`verification/` by an agent that did not write it, then a lead review before hardware use.

## 11. Risks

| Risk | Mitigation |
|---|---|
| The pose error is larger than predicted on hardware | The floor-reference check (§3) refuses the merge, and the trust ledger already bounds where scans may run |
| Cable shadows and the claw's own shadow in the images | Mask the predicted cable lines and the jaw silhouette in each frame before matching |
| Laundry piles are soft and change all the time | Small piles are below or near `min_obstacle_h_m`. The garment detector handles laundry; the map handles furniture. Piles are not proposed as shapes unless taller than 0.25 m |
| Lighting changes between scans | NCC is gain-invariant. The mosaic shows the newest frame per cell |
| Compute time on an older laptop | Downsample further; partial scans keep the routine updates small |
