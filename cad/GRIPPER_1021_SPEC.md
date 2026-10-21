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
