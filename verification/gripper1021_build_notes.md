# Gripper 1021 build notes (cad-implementer)

Spec: `cad/GRIPPER_1021_SPEC.md`. Sources: `cad/parts/gripper1021_hands.py`, `cad/parts/gripper1021_housing_cambay.py`
(housing: part 2), master values `GRIP1021_*` / `CAMBAY1021_*` in `cad/params.py`, build + measurement script
`scripts/build_gripper1021.py`, tests `tests/test_gripper1021.py`. Jasper's reference parts were only read.

Status: hands SHIPPED and FROZEN by the lead (c95c3bb; do not change `gripper1021_hands.py`, the GRIP1021_* block or the
`gripper1021_hand_*` exports; a regeneration check on 2026-10-21 17:3x gave byte-identical STL and identical STEP volume/bbox).
Housing + camera bay: done, see part 2.

Reproduce: `/usr/bin/python3 -m cad.parts.gripper1021_hands` (build + STEP/STL/preview, 10 s);
`/usr/bin/python3 scripts/build_gripper1021.py hands` (adds sweep, dense sweep, clearances, all renders, about 5 min);
`/usr/bin/python3 -m cad.parts.gripper1021_housing_cambay` (housing + bay + cover, exports, 8 s);
`/usr/bin/python3 scripts/build_gripper1021.py housing` (all housing measurements, cable lines, renders, about 5 min);
`/usr/bin/python3 -m pytest tests/test_gripper1021.py` (hands 24 + housing 16 tests, 2.2 min, all 40 pass).

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
1. **Mass vs wall rule (spec conflict; lead decision: keep the 21.5 g layout, 2.25 mm at the groove roots accepted).** The same outline without windows is 33.9 g; with through-windows and walls >= 3.0 mm from
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
5. **Screw length (lead decision: M3 x 20 at A, M3 x 18 at B).** From the crank top (1108.99) an M3 x 20 tip is 1.0 mm below the bed
   face at A; from the arm top (1106.49) an M3 x 18 tip is 1.5 mm below it at B. Nothing is below the hands in the sweep.
6. Interpretations I made: "30 deg chamfer on the outer bottom edge" = a wedge whose face is 30 deg off the tip plane (a shallow
   scraping lip), not 30 deg off the outer face; "point to the side" = hex vertices point across the link.

### Files (hands)
- `/home/user/RoomCleaner/cad/parts/gripper1021_hands.py`, `/home/user/RoomCleaner/cad/params.py` (GRIP1021_* block appended)
- `/home/user/RoomCleaner/exports/step/gripper1021_hand_right.step`, `gripper1021_hand_left.step` (file pose, world frame)
- `/home/user/RoomCleaner/exports/stl/gripper1021_hand_right.stl`, `gripper1021_hand_left.stl` (print orientation, z min 0)
- `/home/user/RoomCleaner/renders/gripper1021/gripper1021_hand_{right,left}_{front,rear,left,right,top,bottom,iso}.png`,
  `preview_hand_{right,left}.png`, `hands_on_mechanism_poses.png` (open -5, mid -30, closed -62 on the mechanism)
- `/home/user/RoomCleaner/scripts/build_gripper1021.py`, `/home/user/RoomCleaner/tests/test_gripper1021.py`


## PART 2: HOUSING + CAMERA BAY (done)

Status: built, exported, measured. One valid solid (housing + bay) and one valid solid (cover). Jasper's housing is
unchanged except the wire window. Sources `cad/parts/gripper1021_housing_cambay.py`, parameters `CAMBAY1021_*` (appended
to `cad/params.py`; existing `CAMBAY_*` values are untouched, `git diff` of params.py is additions only).

### What was ported and what was re-derived
- Bay frame, cradle, lens window and chamfer, USB-C notch, fence, locating ribs, cover pegs / lips / antenna corral, insert
  columns, ties, vents: unchanged, read from `CAMBAY_*`. Origin (951.8475, 1091.1905, 1103.9899), bay on -Z, optical axis at
  r = 90 pointing -y.
- Measured on Jasper's housing (probes + faces, bay frame): flange half 50.0 (y 0..5, R20 corners), R75 blend 5.0 -> 31.926,
  upper half 45.0 (R10 corners), pocket half 40.0 (R10), pocket floor 5.0, lid seat 50.0 (ledge half 42.5), top 55.0, Ø30 tube hole,
  8 x Ø3.3 holes (y 0..5), four Ø2 corner cable holes on the diagonals rising 13.76 deg: outer mouth centre |x| = |z| = 43.22 at
  y = 9.95 (world 1101.14), pocket-side exit |x| = |z| = 37.07 at y = 7.82.
- New for the 5 mm wall: bay solid starts at r = 42.5 (inside the wall: pocket wall at 40, outer wall 45..50); cover inner edge
  r = 45.85 (0.8 mm off the wall at the cover height, v6 was 56.5); root gusset ribs run from (12.9, 76) on the neck side wall to
  (30.0, 44.5) inside the wall (x <= 30 keeps them 13 mm from the corner mouths); wire window 10 x 7 at y = 15.5 through the
  5 mm wall (v6: 10 mm), funnel out to r = 66 (22 x 19), pocket-side flare r 39..41.5. The neck is now 31..36 mm long (v6: 17..25),
  so the wires run 12 mm further before the cradle; the tie slots stay 10.3 mm inboard of the cradle (r 66.4 / 74.4).
- Asserts in the module: bay solid starts between the pocket wall and the outer wall; ribs end inside the wall and outside the
  pocket; bay max |x| (31.05) + 5 < corner mouth 43.22; window funnel + 6 + 5 < pocket-side exit 37.07.

### Acceptance, expected vs measured
| Item | Expected | Measured |
|---|---|---|
| Solids / validity | one valid solid; cover separate | housing + bay: 1 solid, valid; cover: 1 solid, valid |
| Material removed from Jasper's housing | only the wire window | removed volume 526.6 mm3; 0.000 mm3 of it outside the window cutter; 0.000 mm3 in the pocket |
| Inside the box pocket | unchanged | added in pocket 0.000 mm3, removed in pocket 0.000 mm3 (pocket box 80 x 50 x 80 above the 5 mm floor) |
| Bottom face | one flat print face, bay floor on the same plane | housing y min = 0.0000 (-4e-7); two coplanar faces on y = 0 (housing base 8648.8 mm2, bay floor 1500.1 mm2); nothing below y = 0 |
| Lens centre, world | x ~ 956.60, z ~ 1013.99, glass 1.9 above bed | (956.5975, 1093.0905, 1013.9899), identical to the v6 value; glass 1.9000 above y = 1091.19 |
| Bay head vs the verified v6 bay | same | symmetric difference of the bay bodies for r >= 78: 0.000 mm3 of 5819 mm3; cover for r >= 65: 0.000 mm3 |
| Distance to the corner cable holes | >= 5 mm | bay body (added solid) 11.69 mm to the nearest Ø2 hole (the -Z side pair; the +Z pair is 79.6), cover 30.28 mm |
| Cable lines leaving the corner holes (model of the v6 script, 8 x 7 x 6 claw positions, 24 yaws) | clear of the bay | no line touches the bay within +-15 deg yaw; min line-to-bay distance 13.23 mm at yaw 0, 11.96 mm within +-15 deg (v6: 20.76 / 19.14). Details below |
| Wall thickness | >= 2.0 | opening test with a 1.9 mm disc on 18 print-frame sections (housing y 1.0 ... 26.5 above the bed incl. each face-coincident level +-0.1, cover 4 levels): no thin spot anywhere in the bay (resolution 0.05 mm), so min wall >= 2.0; designed walls 2.0 (neck sides, fence, lips, rails), ribs 2.4, floor 2.4, cover plate 2.4 |
| Cover | exported separately | `gripper1021_housing_cambay_cover.step/.stl`; cover vs housing overlap 0.000 mm3; sits at y 26.9..29.3, pegs down to 20.9 |
| STEP re-import | volume, bbox agree | housing: volume rel. diff 4.9e-10, bbox diff 0.00000; cover: 3.4e-12, 0.00000; 1 solid each |
| World frame | drops in at the origin | housing + bay bbox x 901.8475..1001.8475, y 1091.19..1146.19, z 1002.69..1153.99; same x, y and +z extent as Jasper's housing, bay sticks 51.3 mm out on -Z |
| Interference with Jasper's parts at the file pose | none | 0.000 mm3 against every part; 0.0024 mm3 against the cylinder = a 12 nm offset (the cylinder top in his file is 1.2e-5 mm above his housing bottom) |
| Masses (solid PETG 1.27) | report | housing + bay 196.0 g (Jasper's housing alone 177.2 g); bay net +18.8 g; cover 5.5 g; bay + cover 24.3 g (v6 target <= 30 g) |
| Wire path | pocket -> cradle | x = 0, y = 15.5 is open from r = 38 to r = 99.3 (window, neck, fence gap), closed by the end wall at 101.3 |

### Cable lines (port of `scripts/analyze_cable_lines_claw_camera_bay.py`, now `cable_line_analysis()` in `scripts/build_gripper1021.py`)
Same model as v6 (mouth -> anchor lines, feasible lines only, claw reference sampled over the workspace, lowest claw point
= closed fingertip y = 575.0 i.e. 0.526 m below the mouth plane), new mouth (43.22, 9.95):
- yaw 0: 0 hits of 1344 lines, min clearance 13.23 mm; yaw +-15: 0 hits, 11.96 mm.
- yaw +-30: 4 hits each side, elevation 5.8..16.4 deg, claw height 1.98..2.34 m (near the ceiling), all on the far end of the
  bay (side wall at x = -13.5, r = 99..100, height 16..29 mm). v6 had 4 hits within +-30 deg, also at elevation <= 13.5 deg and height >= 1.98 m.
- yaw 45 and beyond: up to 56 hits per yaw (402 over all 24 yaws), elevation up to 30 deg, claw height down to 0.53 m, on the
  columns and the neck. v6 had 170 over all yaws with elevation <= 13.5 deg. The corner mouths are now 43.2 mm out instead of
  54.4, so steeper lines reach the bay before they clear its 29.3 mm height. If the claw may yaw beyond +-30 deg at low
  heights, lower the cover columns or shorten the bay; I did not change the bay geometry.

### Flags for the lead
1. Cable-line clearance is smaller than v6 (13.2 vs 20.8 mm at yaw 0) and hits appear at yaw >= 30 deg with elevation up to 30 deg.
   Within +-15 deg there is none. This follows from the smaller housing (mouths 43.2 mm out), not from the bay.
2. The bottom plane is two coplanar faces (housing base and bay floor), not one merged face; the plane itself is one flat y = 0.
3. The bay solid overlaps the housing flange (r 42.5..50) at y = 0, so it touches the cylinder top in Jasper's file by 12 nm
   (0.0024 mm3). Harmless; it is the same offset his own housing has.
4. Jasper's housing alone is 177 g as a solid PETG volume (139.5k mm3); with the bay 196 g. Not changed here.
5. Nothing in the pocket changed, but the window removes 0.53 cm3 of the 5 mm wall: check the lid-screw / board layout that
   nothing mounts on the -Z wall at x = 0, y 12..19.

### Files (housing)
- `/home/user/RoomCleaner/cad/parts/gripper1021_housing_cambay.py`, `/home/user/RoomCleaner/cad/params.py` (CAMBAY1021_* block appended)
- `/home/user/RoomCleaner/exports/step/gripper1021_housing_cambay.step`, `gripper1021_housing_cambay_cover.step` (assembly world frame)
- `/home/user/RoomCleaner/exports/stl/gripper1021_housing_cambay.stl` (bottom plane on the bed, bay toward +y), `gripper1021_housing_cambay_cover.stl` (flat outer face down)
- `/home/user/RoomCleaner/renders/gripper1021/gripper1021_housing_cambay_{front,rear,left,right,top,bottom,iso}.png`, the same for `..._cover_*`,
  `bay_iso.png`, `bay_iso_no_cover.png`, `bay_underside_lens.png`, `bay_section_front.png`, `assembly_iso.png`, `assembly_bay_side.png`
- `/home/user/RoomCleaner/scripts/build_gripper1021.py`, `/home/user/RoomCleaner/tests/test_gripper1021.py`
