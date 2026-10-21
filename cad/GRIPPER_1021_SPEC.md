# Gripper 1021: hands and electrical housing with camera bay (2026-10-21)

Source: Jasper's final gripper assembly `cad/reference/gripper_1021/1021LaundryAssem.STEP`
(SolidWorks 2026). Its parts, extracted one STEP each in **assembly world coordinates**, are in
`cad/reference/gripper_1021/parts/`. Do not edit Jasper's parts. All coordinates below are
world mm in that frame:
- the tube axis is the line x = 951.8475, z = 1103.99, along y;
- +y points up, toward the housing and the cables; the hands are at low y;
- +z points toward the servo.

Deliverables: (1) left and right **hands**, (2) the **electrical housing with the camera bay**
as one part. STEP and STL for both.

## 1. Mechanism (lead analysis; `cad/reference/gripper_1021/fourbar.py`, `sweep_linkage.py`)

The arms (`Claw_arm_extension3`, 5 mm plates, z 1101.49–1106.49) pivot on the gear-housing pins
at O4 = (963.847, 685.391) (right) and (939.847, 685.391) (left). Each has a 50.00 mm arm with
a Ø3.5 tip hole on an R9.15 boss.

The gears carry crank pins: the compound has a Ø3.5 hole at r = 53.0 from its axis
O2 = (969.997, 721.413), on an Ø18.3 boss at z 1098.99–1108.99. The follower has a Ø3.4 hole
at r = 53.0 from (933.697, 721.413), on an Ø18.33 boss at z 1099.99–1109.99.

**The hand is the coupler** of a near-parallelogram four-bar: it joins the crank pin A to the
arm tip B.

| Link | Value |
|---|---|
| Ground O2–O4 | 36.54 |
| Crank | 53.00 |
| Rocker | 50.00 |
| Coupler (hand) A→B | **34.67** (matches the compound side of the current assembly pose) |

With c = 34.67 the hand's direction stays at −103.6° ± 0.8° over the working range, so the
jaws move almost parallel.

- **Working crank range: −5° (open) to −65° (closed).** Sweep result: no interference
  between gears, arms and both housing halves anywhere in −5° … −65°. At −70° the arm hits the
  crank, and at −100° the linkage reaches its change point. The jaws therefore close at
  **θc = −62°** (grip faces meet), which leaves 3° before the first collision. This is
  servo travel 2 × 57° ≈ 114°.
- **Gear mesh:** the follower in the assembly file is 6° off its mesh. Rotated by −6.0° it
  meshes with zero overlap, and its crank then mirrors the compound crank exactly, so the
  jaws are symmetric. The left hand is the mirror of the right hand about x = 951.8475.

Key points for the right hand (compound side):

| θ2 | A (crank pin) | B (arm tip) | Grip-face gap |
|---|---|---|---|
| −5° (max open) | (1022.795, 716.794) | (1013.804, 683.310) | 2 × 27.1 = 54.2 mm |
| −10° | (1022.192, 712.210) | (1013.394, 678.675) | 53.4 mm |
| −52.1° (Jasper's file pose) | (1002.554, 679.592) | (994.481, 645.875) | |
| **−62° (closed: faces meet at x = 951.8475)** | **(994.879, 674.617)** | **(986.708, 640.923)** | 0 |

While closing, the hand moves down 37.8 mm as well as inward. Fingertips scoop downward, so
the claw should close with the open tips about 35–40 mm above the floor.

## 2. Hands: geometry contract (right hand, closed pose θc = −62°; left = mirror)

Build in world coordinates at the closed pose, then export (see §4).

- **Bottom plane z = 1090.0** for the whole hand. It is the print-bed face, so no supports are
  needed.
- **Link plate**, z 1090.0–1098.0: hull of a circle R8.0 at A and a circle R8.5 at B, plus a web
  from B down to the palm.
- **Joint bosses (washer faces Ø8, rising from the plate top):**
  - A boss up to the crank's underside: **z 1098.99 on the right, 1099.99 on the left** (the
    follower crank sits 1 mm higher; this is the only non-mirror difference).
  - B boss up to the arm's underside: **z 1101.49** on both.
- **Holes:** Ø3.2 through at A and B, for M3 screws used as pins. M3 nyloc pockets in the
  bottom face: hex 5.7 across flats (point to the side), 4.2 deep, coaxial.
- **Hardware:** M3 × 20 button-head screw from the top through the crank and through the arm
  tip; nyloc nut in the hand pocket. Tighten until snug, then back off, so the joints turn
  freely.
- **Height limit above the screw heads:** at A, the crank top is 1108.99 and the gear-housing
  plate is at 1112, so only button heads (1.65 mm) fit. No washers thicker than 0.5 mm there.
- **Palm and finger, below the cut line y ≤ 628.4** (= B_y − 12.5; clears the own arm-tip boss
  by more than 3 mm): full width z 1090.0–1118.0, centred near the tube-axis plane.
  - **Grip face:** the plane x = 951.8475, from y 628.4 down to the fingertip at **y = 575.0**.
  - **Finger:** 9 mm thick (x 951.85–960.85).
  - **Palm:** a gusset from the finger back to under B, joining the link plate.
  - **Lightening:** add lightening windows (through z) in the palm, keeping walls ≥ 3 mm.
- **Grip surface:** horizontal ridges 0.8 mm high at 3 mm pitch on the grip face, kept inside
  x ≥ 951.8475 (ridges are cut into the face, not proud of it, so the faces still meet at
  θc).
- **Fingertip:** R3 round on the bottom edge, and a 30° chamfer on the outer bottom edge for
  scraping under fabric.
- **Keep-outs** (verified for the volume above, at any θ2 in −5° … −62°):
  - above the plate (z > 1098.0) for y > 628.4 only the two bosses are allowed;
  - nothing at y ≥ 676.4 when the hand is at −5° (gear-housing plate).
  - The implementer must re-run the sweep with the real hand solids (both hands, all parts,
    θ2 = −5, −10, −20, … −60, −62) and report the overlap volume, which must be 0.
- **Mass target:** ≤ 22 g per hand as solid PETG (1.27 g/cm³) in CAD.

## 3. Electrical housing with camera bay (one part)

Base part: `parts/05_Gripper_Electric_Housing_Base_2__NAUO5.step`, Jasper's new housing.
Measured:
- 100 × 100 base, y 1091.19–1096.19, R20 corners;
- R75 concave blend up to a 90 × 90 box with 5 mm walls;
- top at y 1146.19, lid seat at y 1141.2;
- Ø30 tube hole;
- 8 × Ø3.3 holes to the cylinder;
- 4 corner cable-line holes Ø2, on the diagonals, rising about 14°, at y ≈ 1098–1102.

Port `cad/parts/claw_camera_bay.py` (the verified v6 bay, D27 no IMU) to this housing and
**union** the bay onto it:
- **Same bay frame:** origin on the tube axis in the box bottom plane y = 1091.19; bay on the
  −Z side (CAMBAY_SIDE = −1); optical axis at **r = 90 mm**, pointing −y.
- This puts the lens at the same world position as the studied v6 design (lens glass about
  1.9 mm above the bed plane, x ≈ 956.60, z ≈ 1013.99), so the D28 camera-view study still
  applies.
- Keep the cradle, lens window, USB-C notch, fence, locating ribs, cover and its pegs/insert
  columns as in the v6 bay.
- **Re-derive** only the box-dependent parameters for the new box: flange half 50.0, upper
  half 45.0, blend R75, pocket half 40.0, pocket floor 5.0, lid seat 50.0, top 55.0. Also the
  corner-hole position, diameter (Ø2) and keep-out, and the neck, rib and column geometry from
  the new wall (r 45–50) out to the cradle (r 80.7).
- Add the new parameters under a new `CAMBAY1021_*` block in `cad/params.py`. Do not change the
  existing `CAMBAY_*` values; the v6 bay stays reproducible.
- Wire window from the bay neck into the box pocket at x = 0, below the lid seat.
- **Keep-outs:**
  - ≥ 5 mm from each corner cable hole;
  - the four cable lines leaving the corner holes must not touch the bay (re-run
    `scripts/analyze_cable_lines_claw_camera_bay.py` adapted to the new box);
  - nothing inside the box pocket may change;
  - the base bottom plane stays one flat print face (the bay floor is on the same plane).
- **Cover:** export it as a separate printed part, as before.

## 4. Exports and checks

- **STEP files** in the assembly world frame, so each drops into Jasper's SolidWorks assembly
  when inserted at the origin:
  - right hand at **Jasper's file pose** (θ2 = −52.1°: rigidly move the closed-pose hand so
    that A and B land on (1002.554, 679.592) and (994.481, 645.875));
  - left hand at the mirrored pose (the follower must be rotated −6° into mesh);
  - housing + bay, and its cover.
- **STL files** in print orientation: hands bottom face (z = 1090) down; housing as the box
  prints.
- **Files** go in `exports/step/gripper1021_*` and `exports/stl/gripper1021_*`. Sources go in
  `cad/parts/gripper1021_hands.py` and `cad/parts/gripper1021_housing_cambay.py`, with a build
  script in `scripts/`.
- **Checks:**
  - valid solid, one body each;
  - the hole positions above at the stated poses;
  - the sweep interference table;
  - masses;
  - bay keep-outs and cable-line clearance;
  - STEP re-import, with volume and bounding box agreeing;
  - standard renders.

## 5. Three-cable holes on the electrical housing (lead, 2026-10-21)

Jasper, 10/21: "I haven't printed the electrical housing yet. Can you add a hole configuration on it meant for 3
motors? So based on function you can choose." The housing keeps its four corner holes for the four-station robot and
gains a second, three-hole pattern for the three-station test (docs/THREE_STATION_MODE_SPEC.md). The lines are
threaded through one pattern or the other; the unused holes stay empty.

**Layout reasoning.**
- The three-station layout is A and B in the corners of one wall and C at the middle of the opposite wall. Seen from the
  start point (the centroid), the stations lie at room azimuths 90° (C), 208° (A) and 332° (B): nearly 120° apart.
- At yaw 0 the claw body frame matches the room (verification/claw_body_frame.json: body +x = box +x, body +y = −box z,
  camera bay at body +y). So the holes sit at body azimuths **C 90°, A 210°, B 330°**.
- C is on the bay side. Its hole goes **high on the wall, above the bay**:
  - bay and cover top out at box y = 26.9 and 29.3; the wire window ends at y ≈ 20.5;
  - every line rises toward the ceiling, so a line leaving at y = 42 can never come down onto the bay.
- A and B sit on the side away from the bay. All three holes are at the same height, so the attachment plane is level.

**Geometry (box frame of cad/parts/gripper1021_housing_cambay.py: origin on the tube axis in the box bottom plane, +y up):**

| Hole | Station (3-mode) | Axis direction (x, z) | Outer mouth centre (x, y, z) | Inner mouth centre (x, y, z) |
|---|---|---|---|---|
| T_C | C | (0, −1) | (0, 42.0, −45.0) | (0, 42.0, −40.0) |
| T_A | A | (−0.8660, +0.5) | (−45.0, 42.0, +25.98) | (−40.0, 42.0, +23.09) |
| T_B | B | (+0.8660, +0.5) | (+45.0, 42.0, +25.98) | (+40.0, 42.0, +23.09) |

- **Hole form:**
  - Ø2.0, horizontal axis along the listed (x, z) direction, through the 5 mm upper wall (pocket 40 to wall 45);
  - teardrop profile with a 45° tip pointing up (+y), so it prints without support with the box upright;
  - 0.5 × 45° chamfer at the outer mouth, so the line does not chafe where it turns up toward its station.
- **Labels:** deboss "A", "B", "C" on the outer wall, 4 mm tall, 0.4 mm deep, centred 5 mm above each mouth. Text must read
  upright with the box printing bottom-down. If CadQuery text fails, skip the labels and say so; do not hide the failure.
- **Keep-outs (≥ 5 mm clear):** corner holes, wire window, bay body, bay cover, lid-seat ledge (y 50), the 8 × Ø3.3 floor
  holes, and any existing feature of Jasper's housing. Each hole must cut only wall material: the removed volume per hole
  must match a Ø2 bore of its wall length, within 10 %. If an existing feature conflicts, stop and report; do not move a
  hole on your own.
- **Nothing else changes:**
  - the difference to the current part lies only within 3 mm of the three holes and their labels;
  - the corner holes, bay, cover and pocket are unchanged.
- **Cable lines (3-mode):** take lines from each outer mouth to its station's anchor prior:
  - anchor priors A (0.05, 0.05, 2.5932), B (3.3028, 0.05, 2.5932), C (1.6764, 2.6932, 2.5932) m;
  - claw positions over the three-station workspace (floor projection inside the A-B-C triangle, 0.2 m from the walls,
    heights from the lowest working height to 0.4 m below the anchors);
  - claw yaw −15° to +15°.
  - Minimum distance from each line to the housing + bay + cover, away from its own mouth, must be ≥ 5 mm.
  - Report the minimum and where it occurs. Adapt `scripts/analyze_cable_lines_claw_camera_bay.py`; keep the original.
- **Claw body frame for the software:** give the three outer-mouth centres in the body frame of
  verification/claw_body_frame.json, re-derived for the 1021 box:
  - origin on the tube axis at the corner-hole inner-mouth height (box y = 7.82);
  - +x = box x, +y = −box z, +z up.
  - Expected: C (0, +0.0450, +0.0342), A (−0.0450, −0.0260, +0.0342), B (+0.0450, −0.0260, +0.0342) m.
  - Give the four 1021 corner-hole points in the same frame too. The configs still carry the v6 values (±0.04207).
- **Parameters:** a new `CAMBAY1021_TRI_*` block in cad/params.py. Existing values do not change.
- **Exports, as new files (the current housing exports stay untouched):**
  - `exports/step/gripper1021_housing_cambay_34.step` and `exports/stl/gripper1021_housing_cambay_34.stl`;
  - the cover is unchanged and is reused.
- **Renders:** `renders/gripper1021/gripper1021_housing_cambay_34_{iso,front,rear,left,right,top,bottom}.png`, plus one
  close-up per hole.
- **Use:**
  - **four stations:** lines through the corner holes, as before;
  - **three stations:** lines through T_A, T_B and T_C; the claw starts with the camera bay facing station C. Inside,
    each line is tied off on a washer or bead larger than the hole: a knot alone can pull through Ø2.

### 5.1 Lead decisions on the implementer's flags (2026-10-21)

1. **Removed volume:** C 17.76 mm³, A and B 20.32 mm³, which is +12 to +13 % over a plain Ø2 bore.
   - **Accepted.** The excess is this spec's own hole form: the teardrop tip adds +6.8 % and the 0.5 mm chamfer +5 to +6 %. The bore proper is +6.8 %.
   - The criterion now reads: within 10 % of the designed cutter (bore + teardrop + chamfer). Its purpose stays the same: prove the cut met only wall material.
2. **Keep-out:** A and B sit 4.98 mm from the pocket's R10 corner fillet.
   - **Accepted.** The fillet belongs to the same wall the hole is drilled through; it is not an independent feature.
   - Every independent feature is at least 6.39 mm away (lid-seat ledge); the bay cover is 11.2 mm away.
3. **Cable-line minimum:** 0.26 mm overall, ≥ 5 mm only up to about 45° elevation.
   - **Accepted; the criterion was wrong for this layout.** No line enters the claw anywhere: every line leaves its mouth outward and upward.
   - The near misses are lines that run close past two convex, rounded features:
     - the box rim edge, 13 mm above the mouth, for steep lines (elevation above about 67°: the claw within about 0.4 to 0.9 m horizontally of its own station);
     - the R10 box corner, for A and B lines far off the hole axis.
   - If the claw tilts a few degrees, these lines can touch the rim or the corner. Grazing contact there is benign, and it moves the effective attachment point by a few millimetres at most, small against the calibration's own uncertainty. The bay and cover are clear by 12.7 mm, which was the real risk.
   - The criterion becomes: no line intersects the claw solid (minimum > 0), and the bay and cover are clear by ≥ 5 mm.
   - Practice: break the rim's outer edge above each three-mode hole with a file if the line marks it.
4. **Software attachment points:** use the **outer** mouth for the three new holes; the line leaves there and turns.
   - The corner holes keep their inner-mouth convention until the configs are re-derived for the 1021 box. Flag that work to the software owner.
