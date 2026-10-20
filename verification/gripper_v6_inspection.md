# Gripper v6 inspection (read-only)

Input: `solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP` (SolidWorks 2026, AP214, 7.7 MB).
Method: OCP/XCAF load with assembly transforms applied, then BREP measurement with CadQuery 2.8 / OCC.
Reproduce: `/usr/bin/python3 verification/gripper_v6_scripts/gripper_v6_measure.py` (about 2 min, writes nothing).
Renders: `renders/gripper_v6/` (iso, iso_gear_head, top_along_gear_axes, top_along_gear_axes_gears_only,
top_along_gear_axes_full, front_side, plus three section plots). Nothing was committed or pushed.

Coordinates are the assembly's world frame as exported (origin is about 950, 700, 1100 mm from the design
datum). **Gear axes are parallel to Z. The claw axis (tube) runs along +Y.** Gear housing is at low Y; the
electronics housing is at high Y. Compound-gear axis C = (969.8475, 707.9864), follower axis F =
(933.8475, 707.9864), pinion/servo axis = (961.8475, 761.3905).

## 1. Solids, bounding boxes, volume, mass

14 instances, 12 unique solids. All 14 are valid BREP and single-solid. `Claw_arm_extension` and
`Claw_arm_extension3` each appear twice (left and right, same volume).

Mass uses PETG 1.27 g/cc on the CAD volume (a 100 % solid upper bound), aluminium 2.70 g/cc.

| # | Solid | bbox size X x Y x Z (mm) | Volume (mm^3) | Mass | Status |
|---|---|---|---|---|---|
| 0 | Griper Cylinder | 127.0 x 55.0 x 127.0 | 252,523 | 321 g | printed |
| 1 | MG996R body (40x19x38 ESTIMATED) | 55.0 x 19.0 x 40.0 | 29,902 | (use 55 g) | purchased/reference |
| 2 | MG996R shaft (ESTIMATED) | 6.0 x 6.0 x 4.0 | 94 | n/a | reference |
| 3 | Gripper_gear_housing (upper half) | 140.0 x 175.0 x 42.5 | 303,333 | 385 g | printed |
| 4 | 06_compound_54T_24T | 115.3 x 90.0 x 36.0 | 90,982 | 116 g | printed |
| 5 | 24T_Follower | 93.6 x 65.9 x 20.0 | 24,942 | 32 g | printed |
| 6 | Simple_18T_Pinionvlast | 29.8 x 30.0 x 16.0 | 8,024 | 10 g | printed |
| 7 | Gripper_Electric_Housing_Base (2) | 127.0 x 81.2 x 127.0 | 392,739 | 499 g | printed |
| 8 | aluminum tubing (OD 28.54, ID 22.54, L 304.8) | 28.5 x 304.8 x 28.5 | 73,368 | 198 g | purchased stock |
| 9 | Gripper_gear_housing_Part2 (lower half) | 140.0 x 175.0 x 40.0 | 278,396 | 354 g | printed |
| 10, 11 | Claw_arm_extension (x2, jaws) | 50.0 x 95.9 x 20.0 | 30,124 each | 38 g each | printed |
| 12, 13 | Claw_arm_extension3 (x2, links) | about 78 x 54 x 5.0 | 6,276 each | 8 g each | printed |

World-frame bbox min/max per solid are printed by the script. Key ones: housing X 881.85..1021.85, Y
653.89..828.89, Z 1101.49..1143.99. Part2 Z 1063.99..1103.99. Gears Z 1080.49..1116.49. Servo body Z
1096.49..1136.49. Tube Y 786.39..1091.19.

**Mass roll-up against the 450 g budget (REQUIREMENTS R7 / A3)**

| Item | Mass |
|---|---|
| Printed parts, CAD-solid upper bound (sum of the printed rows above) | 1,808 g |
| Aluminium tube | 198 g |
| MG996R (supplied figure) | 55 g |
| **Total, upper bound** | **about 2,061 g (4.6 x the budget)** |

- The tube alone is 44 % of the budget. Electric Housing Base (499 g) plus Griper Cylinder (321 g) are 45 % of
  the printed mass. Housings plus cylinder plus base are 1,559 g.
- The printed mass will be below CAD-solid after slicing. I have not measured a sliced mass. If sliced
  material is about 60 % of CAD volume (an assumption, not measured), the claw is about 1.34 kg. Hitting
  450 g needs about a 4.6 x cut from the CAD-solid figure.
- Unknowns not in the STEP: 5 x 607-type 7x14x5 bearings (about 9 g), M3 hardware, ESP32, 2S LiPo, buck
  converter, camera, wiring, servo horn or adapter, glue.

## 2. Gears

Pitch data confirmed from the geometry: OD 30 / 84 / 39 mm gives **module 1.5** (m = OD/(z+2)). Root diameters
23.25 / 77.25 / 32.25 are exact m(z-2.5) full-depth values. Profile is a true 20 degree involute (measured
tooth thickness at 3 radii matches the analytic involute to 3 decimals). Tooth thinning is 0.100 mm per gear
at the pitch circle (2.256 mm against an ideal 2.356 mm).

| Gear | Axis (X, Y), dir | Teeth (counted) | OD | Module | Face width / Z range | Other |
|---|---|---|---|---|---|---|
| Pinion | (961.8475, 761.3905), Z | 18 | 30.00 | 1.5 | 16.0 mm, Z 1080.49..1096.49 | bore Ø8.00 through, no horn pocket |
| 54T of compound | (969.8475, 707.9864), Z | 54 | 84.00 | 1.5 | 16.0 mm, Z 1080.49..1096.49 | 8 x Ø12 lightening holes on R27 |
| 24T of compound | same axis | 24 | 39.00 | 1.5 | 20.0 mm, Z 1096.49..1116.49 | integral lug and fork at R75, angle -31.2 deg |
| Follower 24T | (933.8475, 707.9864), Z | 24 | 39.00 | 1.5 | 20.0 mm, Z 1096.49..1116.49 | integral lug at R75, angle 209.9 deg |

Tooth counting: a thin ring at the pitch radius cuts the solid into 18, 54, 24 and 24 pieces. The compound's
lower 10 mm of 24T face (Z 1096.49..1106.49) is partly filled by the lug and fork over about 290 to 360 deg,
so a ring there gives 22 pieces. The upper 10 mm gives 24. At the mesh position (180 deg, away from the lug)
the full 20 mm is toothed, and the follower's lug sector is likewise clear of the mesh.

**Centre distances**

| Mesh | Measured | Nominal m(z1+z2)/2 | Allowance | R5 / v3 recommendation |
|---|---|---|---|---|
| 18T to 54T | 54.0000 | 54.000 | **0.000 mm** | +0.1 to +0.3 (v3 used 54.30) |
| 24T to 24T | 36.0000 | 36.000 | **0.000 mm** | +0.1 to +0.3 (v3 used 36.30) |

Tip to root clearance is 0.375 mm (0.25 m) on both stages (54 - 15 - 38.625 and 36 - 19.5 - 16.125). Pinion
to follower tip clearance is 26.0 mm (centres 60.29 mm apart; they also sit in different Z bands, so there is
no contact between them).

**Backlash and mesh clocking (assembly pose)**
- Circumferential backlash window, measured by rotating one gear with the other fixed: pinion mesh -1.3 to
  -0.4 deg (0.9 deg, which is 0.21 mm at the pinion pitch circle); follower mesh +1.0 to +1.7 deg (0.7 deg,
  which is 0.22 mm at its pitch circle). These match the 0.1 mm per-gear thinning at exactly nominal centres.
- **As exported, both meshes overlap**: pinion to compound 2.53 mm^3, compound to follower 17.00 mm^3 (the
  pose is about 0.4 deg and about 1.0 deg outside the clearance windows). This is a clocking problem, not a
  geometry problem.
- With the pinion at -0.85 deg and the follower at +1.35 deg (window midpoints), I swept the compound from -30
  to +30 deg (pinion +90 to -90 deg) in 5 deg steps: **zero overlap at all 13 angles** for both meshes.
  Sampled angles only.
- Added kinematic check (4-bar jaw linkage, see section 5): with the re-clocked pose the compound and
  follower jaws mirror each other to within 0.01 mm. The as-exported jaw 2 is rotated about 1.3 deg from the
  mirror of jaw 1 (arm Y 626.61 against 625.10, and jaw 2 link and arm pivot holes miss each other by 0.12
  mm; jaw 1's are exact).

**Tooth strength (R5 method, `calculations/gen2_screening.py` constants: Lewis Y18 = 0.309, Y24 = 0.337, Y54
= 0.416, PETG allowable 22.5 MPa, MG996R stall 9.4 / 11.0 kg cm).** I reproduced R5's table first (55.3 MPa
for m1, b6, 4.8 V).

| Case at servo stall | Ft | Lewis stress | SF |
|---|---|---|---|
| Pinion m1.5, b16, 4.8 V | 68 N | 9.2 MPa | 2.44 |
| Pinion m1.5, b16, 6.0 V | 80 N | 10.8 MPa | 2.09 |
| 54T, 6.0 V | 80 N | 8.0 MPa | 2.81 |
| Sync 24T, b20, jaws balanced, 6.0 V | 85 N | 8.4 MPa | 2.66 |
| Sync 24T, b20, one jaw takes all torque, 6.0 V | 171 N | 16.9 MPa | 1.33 |

The measured m1.5 with 16 mm face is about R5's "module 2.0, 10 mm face" case (10 MPa, SF 2.3), so R5's
pinion recommendation is met on a Lewis basis. This is a screening number only: no contact stress, printed
layer orientation, creep or fatigue.

## 3. Interfaces

**Pins and bearing pockets (the 7x14 question)**
- Pocket diameter measured **Ø14.075** (R 7.0375). Both ends have a **Ø14.000** entry lip, 1.95 mm long.
  The step is 0.0375 mm radial. In practice this is a straight bore: a Ø14.0 bearing has to be pressed
  through the lip, and a vertical FDM hole usually prints undersize.
- Against the recommendation (Ø14.05 for vertical holes, or crush ribs), the pocket is 0.025 mm larger and the
  lip is 0.05 mm smaller. There are no crush ribs.
- Pockets: compound lower 5.05 mm deep (Z 1082.44..1087.49, one 5 mm bearing); compound upper 10.05 mm
  (Z 1104.49..1114.54, two 5 mm bearings); follower upper 10.075 mm (Z 1104.49..1114.565, two bearings). Total
  5 bearings. The shoulder inside each pocket steps to Ø8.30 (compound) or Ø8.33 (follower).
- Housing pins are **integral printed Ø7.000** (R 3.5000). That is zero clearance on a 7 mm bearing bore.
- Upper housing: Ø7 pins on both gear axes, Z 1105.99..1120.94, boss Ø17.5 above.
- Lower housing (Part2): a Ø7 pin on the compound axis only, Z up to 1083.49. **There is no lower pin on the
  follower axis.**

**Servo (MG996R reference, marked ESTIMATED in the file)**
- The shaft axis (961.8475, 761.3905) coincides with the pinion axis to 0.0001 mm. Pinion alignment is exact.
- The shaft is Ø6.0 x 4 mm, entering the pinion's Ø8.0 bore from above (Z 1092.49..1096.49). There is 1.0 mm
  radial gap, no spline, no horn, no horn pocket and no screw holes in the pinion.
- The pinion is 4.9 mm clear of the Part2 floor and is otherwise unsupported. Its top face is flush
  (0 mm gap) against the servo boss at Z 1096.49.
- Ear-hole pattern in the servo model: 47 mm x 10 mm, Ø4.0. The upper housing has four integral Ø4.0 pegs
  (35 mm long, Z 1101.49..1136.49) at exactly those positions (0.00 mm offset). Peg diameter equals hole
  diameter, so clearance is zero, and there is no head or retention. The servo top face touches the housing
  roof (Z 1136.49).

**Tube and mounting**
- Tube OD Ø28.54 against the housing neck bore Ø28.54 (R 14.27) and against the cylinder collar Ø28.54 for
  10 mm: line-to-line, zero measured interference. Behind the collar the cylinder bore is Ø30.0 (1.46 mm
  diametral gap). The collar has a Ø3.5 cross-hole along X at Y 1048.19; the tube has no matching hole.
- Cylinder to Electric Base: the 8 x Ø3.5/Ø3.3 holes match exactly. The 4 x Ø3.4 holes are offset 0.31 mm
  (pitch 57.01 against 56.57 mm), which leaves 0.09 mm of margin for an M3.

**Jaw linkage hardware**
- Pivot holes are Ø3.5 (lug, arm and link). Housing blind holes for the link pins are Ø3.5, Z 1106.49..1121.81.
- Pin and arm axes are coaxial: lug to arm 0.00 mm (jaw 1), 0.12 mm (jaw 2 link hole).

**Other alignment defect**
- **Part2's compound pin axis is at Y = 708.39, but the upper pin, the compound axis and the compound
  bearings are at Y = 707.9864: a 0.40 mm offset** (X agrees). The two bearing seats are 0.40 mm out of line.

## 4. Static interference (pairs with intersection > 0.5 mm^3)

| Pair | Volume | Note |
|---|---|---|
| 06_compound_54T_24T and 24T_Follower | 17.00 mm^3 | tooth overlap, phase only (section 2) |
| 06_compound_54T_24T and Simple_18T_Pinion | 2.53 mm^3 | tooth overlap, phase only |

The other 32 pairs whose bounding boxes overlap (34 tested in total) all intersect at 0.00 mm^3. No press-fit
interferences exist: the bearings, pins, screws and steel hardware are not in the STEP.

Zero-volume face contacts (touching, no clearance):
- Follower bottom face (Z 1096.49) sits on the 54T top face over about 740 mm^2 of overlap. The parts counter-rotate.
- Pinion top face (Z 1096.49) sits against the servo boss.
- Servo top (Z 1136.49) against the housing roof.
- Tube line-to-line in the neck and the cylinder collar.
- Upper housing against Part2.

Minimum gear to housing wall distance is 1.5 mm (compound and follower to each housing half).

## 5. Changes against v5 and against the V3 fit review

**Against v5** (only names and structure can be inferred; the v5 SLDPRTs and SLDASM have no readable
strings). The same seven parts exist (the 18T pinion, the compound 54T/24T, the 24T follower, the gear
housing, the Griper Cylinder, the electric housing base, and the servo as a reference). New in v6:
- `Gripper_gear_housing_Part2`: the housing is now split into upper and lower halves.
- `Claw_arm_extension` and `Claw_arm_extension3` (x2 each): the jaws are now modelled as a parallelogram-type
  4-bar linkage. The compound/follower lug at R75 is the crank, the arm is the coupler (41.3 mm between
  pivots), and the link is pinned to the housing at (963.85, 665.39) and (939.85, 665.39) with a 70.0 mm
  length. The ground link is 43.0 mm.
- `aluminum tubing` (12 in, Ø28.54 x 3 mm wall) joins the housing to the Cylinder and the Electric Base.
- A servo reference body (MG996R) replaces any placeholder.

**Against the V3 fit review (`docs/history/gripper_v3_fit_review_20261018.md`)**

| Item | V3 | v6 |
|---|---|---|
| Module, teeth, OD, face widths | m1.5, 18/54/24/24, 30/84/39, 16/20 | unchanged |
| Tooth thinning | 0.10 per gear | unchanged (0.100) |
| Centre distances | 54.30 / 36.30 | **54.00 / 36.00** (the +0.30 allowance is gone) |
| Backlash per mesh | about 0.42 mm | about 0.21 to 0.22 mm |
| Lightening | 8 x Ø12 on R27 | unchanged |
| Pivot | Ø8 steel pins, Ø8.3 gear bore | Ø7 printed integral pins plus 7x14 bearings (Ø14.075 pockets); Ø8.3 retained between |
| Servo and pinion | horn pocket Ø25.3, Ø12 journal | plain Ø8 bore, servo shaft pointing in from above, no horn or journal |
| Thrust and flanges | thrust washers, Ø34 flange | none; follower sits directly on the 54T face |
| Housing | 112 x 112 x 96 case | two-piece, 140 x 175 x about 82 plus tube neck |
| Jaws | not defined | 4-bar linkage, Ø3.5 pivots |

**Jaw travel measured (not in v3).** I solved the 4-bar closure and swept for collisions. Compound rotation
(clockwise viewed from +Z closes the jaws) is free from **-34 to +17 deg, about 51 deg** (pinion about 153
deg). Closed limit: arm touches link at -35 deg (1.1 mm^3) and the arms hit each other by -40 deg. Open
limit: arm and link touch at +18 deg (3.4 mm^3); the compound lug hits Part2 by +25 deg. R5 assumed 60 deg of
jaw travel for 180 deg of servo, so the real range is shorter. Jaw gap (arm bbox): 20 mm at -30 deg, 81 mm at
0, about 97 mm at +17 deg. The arms stay within 1.5 deg of parallel, so the jaws translate.

## 6. Ranked issues

**High**
1. **Mass.** CAD-solid claw is about 2,061 g against the 450 g budget. The tube (198 g), Electric Base (499 g)
   and Cylinder (321 g) alone are 1,018 g. Not fixable by infill alone.
2. **No torque path from the servo to the pinion.** Ø8.0 bore against Ø6.0 shaft (4 mm engagement, 1.0 mm radial
   gap), no horn, no screws, nothing in the pinion. R5 says to bolt to the metal horn. At stall the pinion
   sees 68 to 80 N tangential. The pinion is also unsupported (4.9 mm from Part2, only 4 mm of shaft in it).
3. **Compound shaft support is not a valid two-bearing shaft.** The lower pin ends at Z 1083.49 and the lower
   bearing seat starts at 1082.44, so the pin enters the bearing by only 1.05 mm of its 5 mm width. The lower
   pin axis is also 0.40 mm off the upper pin axis (Y 708.39 against 707.9864).

**Medium**
4. **Zero centre-distance allowance** (54.000 / 36.000). R5 asks for +0.1 to +0.2; v3 used +0.30. Backlash is
   only 0.21 / 0.22 mm and printed teeth swell, so a 0.1 mm flank growth would remove it. Each +0.10 mm of
   centre distance adds 0.073 mm of backlash.
5. **Mesh clocking** in the exported pose is outside the clearance windows (2.5 and 17.0 mm^3 of overlap). The
   windows are only 0.9 deg and 0.7 deg wide, so assembly clocking must be controlled. The follower jaw sits
   1.3 deg off mirror, with a 0.12 mm link-hole mismatch.
6. **Follower is cantilevered.** It rides on the upper housing's Ø7 integral pin only (no lower pin). The jaw
   loads act at the lug, Z 1096.49..1106.49, partly below the bearing stack (1104.49..1114.565).
7. **Axial rubbing and no thrust control.** The follower bottom is on the 54T top face (about 740 mm^2, 0 gap),
   and the pinion is on the servo boss. No axial retention exists: the compound can float about 6 mm
   toward the upper boss.
8. **Sync stage under one-jaw load.** SF 1.33 at 6 V stall if one jaw carries all the torque (16.9 MPa
   against 22.5). Torque limiting in firmware (R5 option 3) is advised.
9. **Jaw travel** is about 51 deg (not 60 deg): link and arm collide at +18 deg.
10. **Tube fit:** line-to-line at Ø28.54 in the neck and collar. The tube will not enter as printed on FDM
    without +0.2 to +0.3 mm; the Ø30 bore elsewhere is loose.
11. **Servo pegs:** integral Ø4.0 pegs in Ø4.0 ear holes (zero clearance), with no retention; the 47 mm x 10 mm
    pattern is from an ESTIMATED reference body and must be checked on the real servo.

**Low**
12. **Bearing pockets:** Ø14.075 pocket with a Ø14.000 lip and Ø7.000 printed pins (zero clearance on the
    bearing bore). Use Ø14.05 and crush ribs or a lip relief. Ø6.9 to 6.95 pins are safer for printed pins.
13. Cylinder to Electric Base 4 x M3 holes offset 0.31 mm (0.09 mm margin).
14. Collar cross-hole has no counterpart in the tube.
15. Bearings, pins, M3 hardware and the horn are not modelled, so no fastener or press-fit interference can be
    checked.
16. The mass model is CAD-solid only; a sliced mass and the electronics mass are needed.

## Limits of this inspection
- Reference bodies (servo, shaft) are ESTIMATED dimensions inside the STEP.
- Mesh and linkage sweeps are sampled (5 deg steps, finer near contacts); not continuous.
- Strength is Lewis screening, same method as R5; no contact stress or fatigue.
- v5 comparison is by name only.
