# Encoder 1021: independent geometry verification (magnet cap + encoder casing)

Verifier: geometry-verifier (Sonnet), 2026-10-22. Repo `/home/user/RoomCleaner`, branch `claude/magical-cerf-gqr7j7`.
Inputs verified, unchanged since the implementer commit 70ec740 (`git diff 70ec740 HEAD` on all of them is empty):
`exports/step/encoder1021_{casing,magnet_cap}.step`, `exports/stl/encoder1021_{casing,magnet_cap}.stl`, `cad/parts/encoder1021.py`,
`cad/params.py` (`ENC1021_*`), `cad/ENCODER_1021_SPEC.md`, `cad/reference/station_1021/*.step`.
Nothing was repaired or changed. Only `tests/test_encoder1021_verification.py` and this report were written.

## Verdict: PASS WITH CONDITIONS (for printing ONE test cap and ONE test casing)

- Geometry: no geometric defect found. Every implementer claim I re-measured (about 310 recorded checks, 0 geometry FAIL) reproduces, with the
  one correction that the stack-up is worse than the notes imply (finding F1).
- Two recorded FAILs, both item 5 (lateral stack-up against the AS5600 displacement limit): worst case 0.78 mm, RSS 0.44 mm against 0.25 mm.
  This is a design-level finding, not a modelling error. It does not stop a first-article print, which is the intended fit test, but it
  must be resolved or measured before printing all five.
- Conditions before and during the first print: section 9. Release gate items (SOLIDWORKS review, physical test) are outside this report.

Reproduce everything: `PYTHONDONTWRITEBYTECODE=1 ENC_VERIFY_JSON=/tmp/rec.json /usr/bin/python3 -m pytest tests/test_encoder1021_verification.py -q -p no:cacheprovider -s`
(26 tests, about 90 s, 368 recorded values: 312 PASS, 2 FAIL, 54 INFO). The two FAIL records are encoded as a passing test that asserts the
limit IS exceeded, so the suite is green while the finding stays visible; if the design is fixed that assertion flips and must be updated.
The implementer's own suite was also re-run: `tests/test_encoder1021.py`, 54 passed.

How it was measured (my own code, none of the implementer's helpers): OCC ray intersections (`IntCurvesFace_ShapeIntersector`),
booleans (`intersect`/`cut`), `BRepExtrema_DistShapeShape` distances, face-geometry reads (planes, cylinders, spheres), and binary-STL triangle
analysis in numpy. The builder module is imported only in item 7 to compare the exports with its solids.

## 0. Frame correction: is the implementer's residual legitimate? YES

The implementer subtracts (0, 0, 2.64) and also a residual (0.004243, 0.001645, 0.003854). I measured the residual myself, from the spool
(bore axis x, z; outer flange face y), and tested whether it is one rigid offset common to the reference parts:

| feature after removing the residual | expected (design) | measured | tol | status |
|---|---|---|---|---|
| residual x / y / z (mm) | each below 0.005 (extract.py origin is rounded to 0.01) | 0.004243 / 0.001645 / 0.003854 | 0.005 | PASS |
| motor shaft axis x, z (independent part) | 0, 0 | within 1e-4 | 1e-4 | PASS |
| shaft end y | 22.0 | 22.0000 | 1e-4 | PASS |
| divot floor x | -22.15 | -22.1500 | 1e-4 | PASS |
| divot centre y, z | 45.0, 0.0 | within 1e-4 | 1e-4 | PASS |
| divot hole axes (4) | y 40.25 / 49.75, z +-4.75 | within 1e-3 | 1e-3 | PASS |
| Motor_Reference x min / max, y min | -21.15 / 21.15 / -40.0 | round to 1e-3 | 1e-3 | PASS |
| Heat_horn y min / max | -2.0 / 0.0 | round to 1e-3 | 1e-3 | PASS |
| Shell_Casing x min | -21.15 | round to 1e-3 | 1e-3 | PASS |

Reading: the same vector lands the spool, motor, slip-in, heat horn and shell on round design numbers, so it is a rigid re-origin on the true
shaft axis, caused by the 0.01 rounding of the extraction origin, not a design feature and not a hidden clash. In the plain frame the only
overlaps are contact sheets: casing/slip-in 1.8338 mm3 with x thickness 0.0042 mm (foot bottom 0.0042 below the floor over 428 mm2), and
cap/spool 0.372 mm3 = 0.163 ribs + 0.209 head embedded 0.0016 mm into the flange face. All other plain-frame pairs are 0. Correction accepted.
(Spec rounds the plate/floor to -21.1/-22.1; the STEP says -21.15/-22.15, so the implementer is right to follow the STEP.)

## 1. Part integrity

| check | expected | measured | tol | status |
|---|---|---|---|---|
| cap: solids / BRep valid | 1 / valid | 1 / valid (isValid and BRepCheck_Analyzer) | - | PASS |
| cap bbox x, y, z | [-7, 7], [22.6, 29.3], [-7, 7] | identical | 0.01 | PASS |
| cap volume | 491.0 (my analytic estimate: head, chamfer, pocket, notch, D-peg, ribs) | 490.20 mm3 | 3 % | PASS |
| cap mass at 1.27 g/cc | - | 0.623 g | - | INFO |
| casing: solids / BRep valid | 1 / valid | 1 / valid | - | PASS |
| casing bbox x | -22.15 .. 13.7 (spec -22.1: rounded) | -22.150 .. 13.700 | 0.06 / 0.01 | PASS |
| casing bbox y | 31.0 .. 56.8 (45 + 23.6/2) | 31.000 .. 56.800 | 0.01 | PASS |
| casing bbox z | +-13.7 | +-13.700 | 0.01 | PASS |
| casing volume, mass | > 0 | 3454.85 mm3, 4.388 g | - | PASS / INFO |
| STEP file: units, solid count | mm, 1 MANIFOLD_SOLID_BREP | mm, 1 each | - | PASS |

## 2. Magnet cap

Measured against Spool1011 (bore read from its faces, then 720-angle ray probes at y = 23.4, 24.3, 25.5) and Motor_Reference.

| check | expected | measured | tol | status |
|---|---|---|---|---|
| spool bore diameter (from the spool faces) | 5.30 | 5.300 | 0.002 | PASS |
| spool bore D-flat x, material on +x | +2.15 | +2.150 (one plane, through y 7..26) | 0.002 | PASS |
| peg round radius (3 levels) | 2.55 (Ø5.10) | 2.550 | 0.003 | PASS |
| peg flat x (3 levels) | +2.05 | +2.050 | 0.003 | PASS |
| peg-to-bore clearance away from the ribs | 0.10 (round and flat) | 0.100 (min over angles) | 0.01 | PASS |
| crush ribs | 3, equally spaced | 3 at 60 / 180 / 300 deg | exact | PASS |
| rib interference with the bore (radial) | 0.054 (tip 2.70 vs 2.65) | 0.0537 | 0.01 | PASS |
| cap/spool interference volume, corrected frame | ribs only, about 0.16 (my estimate 0.15..0.17) | 0.1630 mm3 | 0.03 | PASS |
| same with the 3 rib sectors cut away | 0 | 0 | 0.002 | PASS |
| head underside y vs spool face y | 26.000 | 26.000 | 0.002 | PASS |
| peg length | 3.4 | 3.400 | 0.005 | PASS |
| peg end y | 22.6 | 22.600 | 0.005 | PASS |
| shaft end y, measured from Motor_Reference | 22.0 | 22.000 | 0.002 | PASS |
| peg end to shaft end (BRepExtrema) | 0.60 | 0.6000 (plain frame 0.5984) | 0.005 | PASS |
| cap vs motor interference | 0 | 0 | 1e-6 | PASS |
| magnet pocket diameter / axis | Ø6.2, on the shaft axis | Ø6.200, axis offset 4.6e-10 mm (corrected frame), 0.0057 mm in the plain frame = the residual | 0.002 / 1e-4 | PASS |
| pocket depth, floor under magnet | 2.55, 0.75 | 2.550, 0.750 | 0.003 | PASS |
| magnet-face plane (head top) | 29.3 | 29.300 | 0.002 | PASS |
| magnet face glued (0.05 film) / bottomed | 29.30 / 29.25 (spec 29.3 +-0.05) | 29.300 / 29.250 | 0.002 / 0.05 | PASS |
| Ø6 x 2.5 magnet model in the pocket | no interference | 0 mm3, 0.10 mm radial play | - | PASS |
| head diameter | Ø14 | 14.000 | 0.003 | PASS |

Additional measurement (not in the notes), risk F2:
- Angular lash of the cap in the bore if the ribs do not grip: +-3.97 deg (BRep rotation of a clean D-peg vs the spool; analytic corner-on-flat 3.97 deg).
  At the Ø15 core that is 1.04 mm of line total per direction reversal. The 0.10 mm flat clearance is the only key.

## 3. Encoder casing

| check | expected | measured | tol | status |
|---|---|---|---|---|
| board pocket 23.4 x 23.4, at y 31.6 / 32 / 33 / 33.5 | 23.4 | 23.400 in x and z at all four levels | 0.005 | PASS |
| pocket centre offset from the axis (x, z) | 0 | 0.000 | 0.01 | PASS |
| front stops | 4 tab faces on the PCB front plane | 4, 3.0 x 3.0, centres (+-10.2, +-10.2), plane y 32.250 | 0.005 | PASS |
| chip-face plane = PCB front - 1.45 | 30.8 | 30.800 | 0.01 | PASS |
| air gap, chip face to cap magnet face | 1.5 | 1.500 | 0.01 | PASS |
| frame front y; chip protrusion | >= 31.0; 0.2 | 31.000; 0.200 | 0.002 / 0.01 | PASS |
| 23 x 23 x 1.6 board box seated on the stops | no interference | 0 mm3 | 1e-6 | PASS |
| board at 8 extreme lateral positions (+-0.2) | free | 0 mm3 | 1e-6 | PASS |
| board 0.01 mm beyond the pocket walls (+-x, +-z) | collides | collides (0.37 mm3 each) | - | PASS |
| board 0.01 mm toward -y | stopped by the tabs | collides | - | PASS |
| board lifted 0.09 / 0.11 toward +y | free / caught by the hooks | free / caught | - | PASS |
| hook lip overlap over the board back face | 2 lips x 8.0 x 0.4 = 6.4 mm2 (0.6 + 0.2 at +-0.2 shift) | 6.40 mm2 (centred and +-0.2) | 0.3 | PASS |
| deflection the walls need as the board passes the lips | 0.4 centred | 0.40 centred; 0.60 if the board is pushed against one wall | 0.01 | PASS |
| chip body 6 x 4 x 1.45 vs casing | none | 0 mm3 | 1e-6 | PASS |
| +-x pad-edge walls end flush with the PCB back | 33.85 | 33.850 | 0.01 | PASS |
| zip-tie slots at z = +-6.2 | 3.0 x 1.6, open through y | 3.000 x 1.600, open | 0.01 | PASS |

Foot and divot (divot faces read from the slip-in STEP):

| check | expected | measured | tol | status |
|---|---|---|---|---|
| divot is a dish: floor 22 x 22, R1.0 quarter-round walls, arc centres at the plate-face level, depth 1.0 | notes claim | floor 22.000 x 22.000, 4 wall cylinders R1.000 centred at x = -21.150, depth 1.000 | 0.002 | PASS |
| corner patches | 3 spherical R1.0, one sharp mitre at (+y, +z) | spheres at (34,-11) (34,+11) (56,-11) only: sharp corner at (56,+11) | exact | PASS |
| foot bottom plane / top plane / keyed / proud | -22.15 / -18.15 / 1.0 / 3.0 | -22.150 / -18.150 / 1.000 / 3.000 | 0.002 | PASS |
| foot side clearance to the divot wall, 7 depths x 4 sides | 0.2 uniform | min 0.200, max 0.200 | 0.01 | PASS |
| foot corners vs divot corners (diagonals) | > 0 | 0.366 (3 corners), 0.495 at the sharp corner | min 0.3 | PASS |
| casing vs slip-in interference, corrected frame | 0 | 0 mm3 | 1e-3 | PASS |
| normal gap foot to divot walls (7 wall faces) | positive | 0.0198 mm (see F4) | 0.01 | PASS |
| plain straight 23.6 foot | would NOT seat | 9.12 mm3 of interference: the implementer's R1.0 bottom round is justified | - | PASS |
| foot bottom flat area | 427.7 | 427.73 mm2 | 1.0 | PASS |
| 4 foot holes Ø | 3.4 | 3.400 | 0.002 | PASS |
| foot-hole to divot-hole axis offset | 0 | 0.000 corrected, 0.0042 plain (the residual) | 0.001 / 0.005 | PASS |
| hole pitch y, z | 9.5 | 9.500, 9.500 | 0.002 | PASS |
| divot hole Ø (measured; foot hole is 0.05 smaller) | 3.45 | 3.450 | 0.002 | INFO/PASS |
| screw access: Ø7 x 55 mm cylinders from the foot face, 4 holes | no casing, no station part | 0 mm3 vs casing and all 6 reference parts | 1e-6 | PASS |
| closest casing feature to the access cylinders | 0.55 (bridge top 36.2 vs 36.75) | 0.550 mm | 0.02 | PASS |

Screw access along the hole axes is clear to x = 36.9 (first shell feature at x 38.85 for the -z holes; the shell end wall is at x 93.85).

## 4. Assembly clearances

Interference volumes (mm3). Full 2 x 6 x 2 matrix is in the test output; summary:

| pair | plain frame (-2.64 only) | corrected frame | judgement |
|---|---|---|---|
| casing vs Slipin_mount_piecev3 | 1.8338 | 0 | contact sheet of 0.0042 mm on the floor: legitimate (section 0) |
| cap vs Spool1011 | 0.372 | 0.1630 | corrected value = the 3 crush ribs only; plain adds a 0.0016 mm head contact sheet |
| casing vs Spool, Shell, Motor, Heat_horn, Wall_Mount | 0 | 0 | PASS |
| cap vs Slipin, Shell, Motor, Heat_horn, Wall_Mount | 0 | 0 | PASS |

Minimum distances:

| check | expected | measured (corrected / plain) | status |
|---|---|---|---|
| casing to Shell_Casing | >= 1.0 | 17.410 / 17.412 | PASS |
| casing to Spool / Motor / Heat_horn / Wall_Mount | info | 5.000 / 12.870 / 31.000 / 7.642 | INFO |
| cap swept 360 deg (5 deg steps) to casing | >= 1.0 | 5.108 | PASS |
| exact envelope of revolution of the head (Ø14, y 26..29.3) to casing | 5.0 = sqrt(4.7^2 + 1.7^2) | 4.998 | PASS |
| cap envelope to board + chip body | 1.5 (chip is the only thing within 1.5) | 1.500 | PASS |
| nothing at y < 26 within r 19 | casing y min >= 26 | casing y min 31.0; casing vs the y 7..26, r 19 zone 0 mm3 | PASS |
| cap below y = 26 | only inside the bore | max radius 2.704, nothing outside r 2.9 | PASS |
| axial margin during the -x slide-in of the casing | >= 1.7 | 1.700 | PASS |

Order of assembly implied by the geometry: cap on the spool first, casing second (the cap cannot pass the board or the frame afterwards).

## 5. Stack-up against the AS5600 placement limit

Limit: ams AS5600 datasheet, maximum displacement of the magnet axis from the package centre 0.25 mm for a Ø6 magnet; air gap typically 0.5 to 3 mm.
Caveat: I could only reach search-engine excerpts of datasheet mirror copies (alldatasheet.net); the direct fetch failed (no DNS). The official ams-OSRAM
PDF was NOT opened. Confirm 0.25 mm there.

Lateral offset of the chip from the magnet axis (x = across the divot floor normal, z = across the divot), nominal dimensions, nominal 23.0 board:

| source | x (mm) | z (mm) | how obtained |
|---|---|---|---|
| foot in the divot | 0 (floor is the x datum) | 0.273 | rim clearance 0.2/side allows the foot to turn +-1.10 deg (BRep bisection); the chip is 14.2 mm from the divot centre, so rotation moves it 14.2 x 0.0192 = 0.273, more than the 0.2 translation. The notes counted only 0.2 |
| board in the pocket | 0.20 | 0.20 | pocket 23.400 - board 23.0, halved |
| cap peg in the bore | 0.10 | 0.10 | measured clearance, round part and flat |
| magnet in its pocket | 0.10 | 0.10 | Ø6.2 - Ø6.0, halved |
| worst case (sum) | 0.40 | 0.673 | radial 0.783 |
| RSS | 0.245 | 0.367 | radial 0.441 |

Axial: foot y play +-0.2 gives an air gap of 1.30 to 1.70, inside 0.5 to 3. PASS.

| check | expected | measured | status |
|---|---|---|---|
| worst-case radial offset | <= 0.25 | 0.783 (3.1x the limit) | FAIL |
| RSS radial offset | <= 0.25 | 0.441 (1.8x) | FAIL |

Not in these numbers, all of which make it worse: spool-on-shaft eccentricity (Ø5.3 bore on a Ø5 shaft, up to 0.15 mm, not controlled by these
parts), divot-to-shaft-axis tolerance of the printed slip-in and the motor seat, PCB outline tolerance (commonly +-0.1 to 0.2), chip placement on the
board, FDM size error on the pocket, foot and peg (about +-0.1 each). Functional consequence: extra INL and angle error, not loss of function.
For a line-length winch encoder this may be acceptable; it is the implementer's own flagged risk, now quantified.

Recommended tightening (not built), computed with the same method:

| change | worst case radial | RSS radial |
|---|---|---|
| as built | 0.783 | 0.441 |
| PCB_CLEAR 0.2 to 0.1 (after measuring the board), FOOT_SIZE 23.6 to 23.8 (halves the rotation, but raises the bind risk of F4), peg clearance 0.05, magnet pocket Ø6.1 | 0.391 | 0.221 |
| the above, plus two close-fit foot locators (two of the four holes at Ø3.1 for an M3 shank, or dowels) so the foot is located by the screws instead of the rim, foot term about 0.08 | about 0.34 | about 0.19 |

The 0.10 to 0.05 peg clearance is at the limit of FDM repeatability, so do it only after the first print shows what the printer holds.

## 6. Manufacturability

| check | expected | measured | status |
|---|---|---|---|
| casing STL print pose | frame front (y = 31) on the bed, +y up | min z 0, bed contact 389.44 mm2 = the front face; bbox 35.85 x 27.4 x 25.8 | PASS |
| cap STL print pose | magnet face on the bed, peg up | min z 0, bed contact 110.79 mm2 (Ø13.4 less Ø6.2) | PASS |
| casing overhangs > 45 deg | only the hook catch ledges and the foot key edge | catch ledges 9.60 mm2 (2 x 0.6 x 8.0); foot key edge 23.5 mm2 over 0.96 mm width; none over the pocket plan | PASS |
| cap overhangs | the pocket floor only | 30.18 mm2 = Ø6.2 disc, a 6.2 mm bridge | PASS with condition (F2 notes) |
| ceiling over any unsupported span | <= about 1 mm for the casing | 0.6 mm (catch) and 0.96 mm (foot edge) | PASS |
| thin walls | +-z flex walls 1.2; +x wall 2.0; tabs 1.25 | 1.200 each at z = +-; +x wall 2.000; -x side is wall + bridge 9.2; hook wall 1.8 through the lip tip | PASS |
| sampled local thickness, casing (6000 surface rays) | nothing below 1.15 except the hook lips | min 0.419, all 34 samples below 1.15 at the hook lips; 0 elsewhere | PASS |
| hook lip tip thickness along y | - | 0.401 mm (2 layers) | INFO: thin, will string |
| cap floor under the magnet / ring wall | 0.75 / 3.9 | 0.750 / 3.900 | PASS |
| crush rib vs 0.4 mm nozzle | - | height 0.154, width 0.61 at the base, 0.47 at half height, 0.34 at 90 % height (nozzle 0.4); nominal crush 0.054 | CONDITION (F2) |
| bridge stiffness, 1 N on the far wall | < 0.1 mm | my ray-sampled section at x = -16, y >= 33.2: A 72.6 mm2, I 54.45 mm4 (matches notes), cantilever L 31.85, a 18.15: 0.0372 mm | PASS (clamp assumed rigid) |
| snap-hook strain, wall span 23.4, t 1.2, h 4.05, E 2100 | notes 27.6 MPa at 0.5 mm | 27.6 MPa, 1.31 % (61 % of 45 MPa yield) | PASS |

Snap-hook cases (sigma = 12 E t d / L^2): centred board 0.4 mm needs 22 MPa (1.05 %, 49 % of yield); the notes' 0.5 mm including margin, 27.6 MPa, 1.31 %;
board pushed against one wall, 0.6 mm: 33.1 MPa, 1.58 % (74 %); same with 0.1 margin: 38.7 MPa, 1.84 % (86 %). I used a 2 % one-shot strain allowance
for printed PETG as my own assumption, not a datasheet value. Fine for one insertion, no margin for repeated service.

## 7. STEP round trip and STL

| check | expected | measured | tol | status |
|---|---|---|---|---|
| STEP file vs builder bbox (6 numbers each) | equal | equal to 1e-3 (cap and casing) | 1e-3 | PASS |
| STEP file vs builder volume | equal | cap 490.2038 vs 490.2039; casing 3454.8487 vs 3454.8487 | 0.01 | PASS |
| boolean difference file vs builder (both directions) | 0 | 0.000 mm3 each | 0.01 | PASS |
| STEP, reimport, re-export, reimport: bbox, volume, solid count, validity | unchanged | unchanged, 1 solid, valid | 1e-3 / 0.01 | PASS |
| STL watertight (every edge shared by 2 triangles) | 0 open edges | 0 / 0 | - | PASS |
| STL volume vs STEP volume | within 0.3 % | cap 490.03 vs 490.20 (0.03 %); casing 3454.86 vs 3454.85 | 0.3 % | PASS |
| STL print-pose extents vs STEP extents | equal | equal to 0.005 mm (cap 14.0 x 14.0 x 6.7; casing 35.85 x 27.4 x 25.8) | 0.005 | PASS |

## 8. Renders

All 14 standard views (front, rear, left, right, top, bottom, iso for each part), 3 assembly views and 4 section views exist (21 files, all above 5 kB).
I looked at: casing iso, front, rear, sections z0, x0 and hole row; cap iso and section z0; assembly iso and section z0. Nothing contradicts the numbers:
chip protrudes 0.2 past the frame front, magnet face level with the cap head top, 1.5 mm gap to the chip, D-peg with ribs and lead-in 0.6 mm short of the
shaft end, teardrop holes pointing +y, foot with its bottom round against the divot, 0.25 mm gap under the bridge, hooks behind the board at +-z, tie slots through the bridge.

## 9. Findings, severity, conditions, recommendations

| id | severity | finding | evidence |
|---|---|---|---|
| F1 | medium (design) | Lateral stack-up exceeds the AS5600 0.25 mm limit: 0.78 worst case, 0.44 RSS. The notes omitted foot rotation (0.27 mm, not 0.2) and the magnet-in-pocket play (0.10) | section 5 |
| F2 | medium | Cap fit is not controlled: 0.054 mm crush from a rib 0.154 high and 0.34 wide at its tip (below the nozzle) is inside FDM accuracy. If the ribs do not grip the cap can turn +-3.97 deg (1.04 mm of line) and has no axial retention other than rib friction. Pocket floor bridge 6.2 mm in PETG may sag | sections 2, 6 |
| F3 | low-medium | Snap hooks: 61 % of yield at the notes' case, up to 86 % if the board is pushed against one wall while snapping in; lip tip only 0.4 mm. One insertion only | section 6 |
| F4 | low | Foot-to-divot normal gap is 0.020 mm near the wall/floor tangent edge (notes say about 0.03). The 0.2 lateral play is real, but a print oversize of about 0.1 to 0.2 mm binds. Notes already give the fallback FOOT_SIZE 23.4 | section 3 |
| F5 | info | All purchased-part numbers are nominal. If the chip stands 1.75 mm (SOIC-8 maximum) the chip face is at 30.5 and the air gap 1.2, still inside 0.5 to 3. PCB thickness, chip centring, pad positions vs the 3 x 3 tabs, hole pitch are unmeasured | spec section 6 |
| F6 | info | Reference model, not these parts: spool bore flat (x = +2.15) and shaft flat (z = +2.0) are 90 deg apart, and Spool1011 overlaps Motor_Reference by 9.06 mm3 in the 10/21 assembly. Ask Jasper how the spool is driven. The cap keys on the bore only, so it is unaffected | test output |
| F7 | info | `cad/interfaces.py` has no encoder interface, so there is no interface record to agree with. `ENC1021_*` in `cad/params.py` is the only authority; the values I cross-checked agree (MOTOR_SHAFT_DIA 5.0 and FLAT 0.5 match Motor_Reference, SPOOL_FLANGE_DIA 36 matches). Legacy `SPOOL_DRUM_DIA = 20.0` disagrees with the 10/21 spool core of Ø15, but ENC1021 does not use it | grep, STEP |
| F8 | info | Deviation from spec section 4 ("2 mm walls"): the +-z walls are 1.2 mm so they can flex as hooks. Outer size is still 27.4. Justified, and it is what F3 stresses | section 6 |

Conditions for printing one cap and one casing:
1. Before printing, measure with calipers or pin gauges: board outline, PCB thickness, chip height, chip centring, pad positions relative to the corner tabs, hole pitch; magnet Ø and thickness; the real spool bore (a printed bore is usually under nominal, and Ø5.10 plus 0.15 ribs may not enter); the real divot size. Update `ENC1021_*` if they differ, then regenerate.
2. Print the cap three times with `ENC1021_CAP_RIB_H` 0.15, 0.20, 0.25 (and `ENC1021_CAP_RIB_W_TIP` at least 0.45 for the taller ones). A cap is 0.62 g. Pick by hand: presses in, no rotation by hand, removable with the notch.
3. Snap the board in once, gently, centred; do not stand the casing face down with a board in it (the chip protrudes 0.2 mm).
4. Treat the print as the fit test of the spec (section 6.4): cap in the spool, board in the pocket, foot in the divot. Then read the AS5600 status bits (MD set, ML and MH clear) over a full turn, and decide on the F1 tightening from the measured offset.
5. Do not print all five before F1 is decided.

Recommendations (nothing applied):
- F1: apply the tightening table in section 5, preferably the two close-fit foot locators, after the part measurements in condition 1.
- F2: peg flat 2.10 (clearance 0.05) cuts the lash to about +-2.0 deg; or put crush ribs on the flat as well. If the pocket-floor bridge sags, print a sacrificial bridging layer or accept scraping the pocket flat before gluing.
- F3: if the casing must be opened often, `ENC1021_HOOK_OVERLAP` 0.3 (worst deflection 0.5, about 27.6 MPa, but the capture overlap at a board shifted 0.2 falls to 0.1 mm) or a screwed retainer.
- F7: add an encoder interface record (datums, divot, spool bore, board and magnet stack) to `cad/interfaces.py`, and a DECISIONS entry for the foot-bottom round and the 1.2 mm flex walls.
- F4 and the datasheet value: confirm 0.25 mm in the official ams PDF.

## 10. Not verified

Real purchased-part dimensions; PETG shrinkage and printer accuracy; foot-clamp and slip-in flexibility in the stiffness number; the divot hardware (insert vs screw, still an open question for Jasper);
wire routing beyond the presence of the tie slots and open pad edges; magnet strength and AGC with the real parts; any FEA or physical test; SOLIDWORKS mates and drawings.
