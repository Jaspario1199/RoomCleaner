# Gripper 1021 build notes (cad-implementer)

Spec: `cad/GRIPPER_1021_SPEC.md`. Sources: `cad/parts/gripper1021_hands.py`, `cad/parts/gripper1021_housing_cambay.py`
(housing: part 2), master values `GRIP1021_*` / `CAMBAY1021_*` in `cad/params.py`, build + measurement script
`scripts/build_gripper1021.py`, tests `tests/test_gripper1021.py`. Jasper's reference parts were only read.

Reproduce: `/usr/bin/python3 -m cad.parts.gripper1021_hands` (build + STEP/STL/preview, 10 s);
`/usr/bin/python3 scripts/build_gripper1021.py hands` (adds sweep, dense sweep, clearances, all renders, about 5 min);
`/usr/bin/python3 -m pytest tests/test_gripper1021.py` (hands: 24 tests, 40 s, all pass).

## PART 1: HANDS (done)

Status: built, exported, measured. One valid solid each. Everything in the acceptance list passes; the one
spec conflict is mass vs the 3 mm wall rule (see Flags).

### Design as built (right hand; the left is the mirror about x = 951.8475, A boss 1 mm taller)
- Link plate z 1090..1098: hull of R8 at A and R8.5 at B, web from B tapering to the palm top bar, one waist window
  (22 x 10) between the nut pockets. Ø8 bosses: A to 1098.99 (right) / 1099.99 (left), B to 1101.49. Ø3.2 holes through,
  hex nyloc pockets 5.7 AF x 4.2 deep in the bed face, vertices across the link.
- Finger + palm, y <= 628.4, z 1090..1118 full width: grip wall on x = 951.8475, finger 9 thick, tip y = 575.0, R3 round on
  the grip-face bottom edge, 30 deg wedge on the outer bottom edge (chamfer face 30 deg off the tip plane, reaches the
  outer face at y = 578.46). 16 V-grooves 0.8 deep, 3.0 pitch, 0.8 crest land, cut into the face (nothing proud of x = AX).
- Lightening: all through-z (prints on the bed face with no supports or bridges). Finger is a closed ladder (grip wall,
  outer skin, tip wedge) with one 3 x 46 slot; the palm is a triangle frame (grip wall, 3 mm top bar, 45 deg strut to the
  web foot, apex at B_x - 3) with one window. Plate has one window. Every window corner is rounded R1.2..1.5.
- All hand z values carry Jasper's file offset of -0.000129 mm (his crank boss underside is 1098.989871, not 1098.99) so the
  contact faces coincide exactly; otherwise every boss/crank pair shows a 0.005 mm3 sliver overlap.

### Acceptance, expected vs measured (closed pose theta = -62 unless noted)
| Item | Expected | Measured |
|---|---|---|
| Solids / validity | 1 valid solid each | right 1, left 1, both valid (also after STEP re-import) |
| A hole centre, right | (994.879, 674.617) | (994.8790, 674.6168), error 0.0000 mm |
| B hole centre, right | (986.708, 640.923) | (986.7081, 640.9234), error 0.0000 mm |
| Left A / B | mirror about x = 951.8475 | (908.8160, 674.6168) / (916.9869, 640.9234), error 0.0000 |
| Coupler A-B | 34.67 | 34.670 |
| File pose (theta = -52.1) holes in the STEP | A (1002.554, 679.592), B (994.481, 645.875) | right A (1002.554, 679.592), B (994.481, 645.875); left (901.141, 679.592), (909.214, 645.875) |
| Boss tops | 1098.99 R-A / 1099.99 L-A / 1101.49 B | 1098.9899 / 1099.9899 / 1101.4899 (the file offset, 0.00013 below nominal) |
| Grip face at closed pose | x = 951.8475, hands touch, zero overlap | right xmin 951.8475, left xmax 951.8475, R-L distance 0.000, overlap volume 0.000 mm3 |
| Bed plane / top / tip | z 1090.0 / 1118.0 / y 575.0 | z 1089.9999 / 1117.9999 / y 575.000 |
| Above the plate for y > 628.4 | only the two bosses | right 189.2 mm3, left 231.4 mm3 = bosses minus pin holes (analytic 189.2 / 231.4) |
| Mass (solid PETG 1.27) | <= 22 g | right 21.50 g (16926 mm3), left 21.55 g (16968 mm3) |
| Min wall around windows (nominal face) | >= 3.0 | 3.00 (z 1110 palm section), 3.00 (z 1092 plate section incl. pockets: 3.44 to the pockets) |
| Min wall at groove roots | information | 2.25 right, 2.30 left (0.8 grooves excluded from the 3 mm rule, see Flags) |
| STEP re-import | volume, bbox agree | volume rel. diff 1e-11, bbox diff 0.00000 mm, 1 solid |
| STL print orientation | bed face z = 0 down | z min 0.000, bbox equals the solid, >90 % of down-facing area on the bed plane (only the nut-pocket roofs are higher) |

### Sweep: overlap volume (mm3), both hands vs every Jasper part moved by the four-bar
Compound at theta; follower rotated -6 deg into mesh then mirrored motion; both arms at the four-bar angle; pinion turned
2 x the gear angle; both housing halves, electrical housing, tube, cylinder, servo body and shaft fixed. The table value is
the larger of the two hands.

| theta | compound | follower | arm_R | arm_L | pinion | housing1 | housing2 | elec. housing, tube, cylinder, servo | R vs L |
|---|---|---|---|---|---|---|---|---|---|
| -5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| -10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| -20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| -30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| -40 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| -50 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| -60 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| -62 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

A denser sweep (theta = -5, -8, ... -62 plus -62, 21 poses) is also 0.0000 mm3. The test is not vacuous: a hand pushed
5 mm up in z shows > 10 mm3 against the crank and the arm (`test_sweep_control_detects_a_collision`).

Minimum clearance, hand with the two bosses removed (their seats are the intended contact), mm:

| theta | compound | follower | arm_R / arm_L | housing1 | housing2 |
|---|---|---|---|---|---|
| -62 | 0.99 | 1.99 | 3.49 | 13.99 | 28.43 |
| -45 | 0.99 | 1.99 | 3.49 | 13.99 | 18.44 |
| -30 | 0.99 | 1.99 | 3.49 | 13.99 | 9.91 |
| -15 | 0.99 | 1.99 | 3.49 | 13.99 | 6.54 |
| -5 | 0.99 | 1.99 | 3.42 | 4.75 | 5.59 |

The 0.99 / 1.99 are the intended z gaps between the plate top (1098.0) and the crank / follower undersides (1098.99,
1099.99); the arm gap is 3.49 (z) and the tightest in-plane approach is 3.42 (palm to arm boss at -5 deg).

### Flags for the lead
1. **Mass vs wall rule (spec conflict).** The same outline without windows is 33.9 g; with through-windows and walls >= 3.0 mm from
   the NOMINAL grip face the best layout I found is 21.5 g, and it relies on measuring walls from the nominal face, so the
   spine is 2.2 mm at the 0.8 mm groove roots. Measured from the groove root (true 3.0 mm everywhere) the same layout is 22.66 g
   (misses 22 g by 0.7 g). Walls 2.5 mm: 18.96 g; 2.0 mm: 16.22 g. Switch with `GRIP1021_WALL_MIN` and
   `GRIP1021_WALL_FROM_RIDGE_ROOT` in `cad/params.py`, then rerun the build.
2. **Palm layout.** The strut apex sits at B_x - 3 (inside the spec's palm region, under the web foot); extending the strut apex to
   B_x + 8.5 (the old tangent-to-B-circle foot width) with the same walls is 23.3 g, over the 22 g target.
3. **Jasper's file is not exactly four-bar consistent**: his crank hole (1002.522, 679.566) and arm tip hole (994.531, 645.912)
   sit 0.04 and 0.06 mm from the spec's file-pose points (1002.554, 679.592), (994.481, 645.875). The hand holes follow the
   spec numbers; the 0.15 mm radial play of M3 in Ø3.2 absorbs it.
4. **`sweep_linkage.py` typo**: `t40` uses x = 994.19 but the right arm's tip hole in the STEP is at x = 994.531. That rotates
   the right arm 0.28 deg (0.24 mm at the tip) off the four-bar. My sweep measures the hole angles from the STEP instead.
5. **Screw length.** With M3 x 20 from the crank top the tip is 1.0 mm below the bed face at A and 3.5 mm below it at B
   (arm top 1106.49). Nothing is below the hands in the sweep; M3 x 16 at B would end 0.5 mm above the bed face if that matters.
6. Interpretations I made: "30 deg chamfer on the outer bottom edge" = a wedge whose face is 30 deg off the tip plane (a shallow
   scraping lip), not 30 deg off the outer face; "point to the side" = hex vertices point across the link.

### Files (hands)
- `/home/user/RoomCleaner/cad/parts/gripper1021_hands.py`, `/home/user/RoomCleaner/cad/params.py` (GRIP1021_* block appended)
- `/home/user/RoomCleaner/exports/step/gripper1021_hand_right.step`, `gripper1021_hand_left.step` (file pose, world frame)
- `/home/user/RoomCleaner/exports/stl/gripper1021_hand_right.stl`, `gripper1021_hand_left.stl` (print orientation, z min 0)
- `/home/user/RoomCleaner/renders/gripper1021/gripper1021_hand_{right,left}_{front,rear,left,right,top,bottom,iso}.png`,
  `preview_hand_{right,left}.png`, `hands_on_mechanism_poses.png` (open -5, mid -30, closed -62 on the mechanism)
- `/home/user/RoomCleaner/scripts/build_gripper1021.py`, `/home/user/RoomCleaner/tests/test_gripper1021.py`
