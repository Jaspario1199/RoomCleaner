# Encoder 1021 v2 (self-centring crush ribs): independent geometry verification

Verifier: geometry-verifier (Sonnet), 2026-10-22. Repo `/home/user/RoomCleaner`, branch `claude/magical-cerf-gqr7j7`, HEAD `e99d6de`.
Inputs, read only: `exports/step|stl/encoder1021_casing_v2.*`, `exports/step|stl/encoder1021_magnet_cap_v2.*`, `cad/parts/encoder1021.py`, `ENC1021_V2_*` in `cad/params.py`,
`verification/encoder1021_build_notes.md` section 11, `cad/reference/station_1021/*.step`. Baseline: `verification/encoder1021_verification.md` and `tests/test_encoder1021_verification.py` (v1).
Written by me: `tests/test_encoder1021_v2_verification.py` and this report. Nothing was repaired or changed. The v1 nominal exports and the variant exports are untouched in the working tree (git status clean for them; `git diff 70ec740 HEAD` empty).

## Verdict: PASS WITH CONDITIONS (print the first article of v2 now)

- Geometry: no geometric defect found. About 316 recorded checks PASS, 0 FAIL, 35 INFO, 5 WARN (engineering findings, listed in section 9). Every geometric claim in build notes section 11 reproduces within tolerance.
- The weakness is not the CAD, it is the self-centring premise. Two points the notes do not cover, both argued from geometry plus hand calculation (estimates, not measurements of printed parts):
  1. The board's x centring is one-sided. The -x wall is a 9.15 mm block (wall + bridge), the +x wall is a free 2.0 x 2.85 plate. Estimated result: the board is pushed onto the -x rib tips, a systematic x offset of about +0.10 mm (range 0.06 to 0.10), and a PCB width error enters at w/2 instead of cancelling (F1).
  2. A rib that centres a rigid part on a rigid support yields at a few microns of crush (PETG), so the "elastic balance of equal ribs" is really a constant-force balance. The magnet, peg and foot centring then relies on symmetric first contact and friction, and the realistic asymmetry is between 0.05 and the crush itself (0.10 to 0.12). Three-rib features also carry 4/3 of eps, not 1x (F2, F3).
- Stack-up: the implementer's numbers (0.317 worst, 0.154 RSS at eps 0.05) reproduce exactly. With the two corrections above the same method gives 0.42 worst and 0.20 RSS at eps 0.05, and 0.63 / 0.30 at eps 0.08. RSS meets the implementer's own 0.25 target only for eps up to about 0.06. The worst case does not meet the 0.25 mm AS5600 guidance at any eps above 0.03 (that guidance is from datasheet mirrors; the official PDF has still not been opened).
- Print it: it is the right fit test. Conditions (section 11): measure the first print before printing five; use the press-in procedure; do not trust eps = 0.05 until measured.

Reproduce: `PYTHONDONTWRITEBYTECODE=1 ENC_V2_VERIFY_JSON=/tmp/rec.json /usr/bin/python3 -m pytest tests/test_encoder1021_v2_verification.py -q -p no:cacheprovider -s`
(12 tests, about 145 s, 356 recorded values; all tests green, WARN records do not fail). The implementer's own `tests/test_encoder1021_v2.py` was re-run: 41 passed.

Method, same as v1 and none of the implementer's helpers: OCC ray intersections, booleans, `BRepExtrema`, face reads, binary-STL triangles. Only the v1 verification's geometry helpers are imported (no tests).
Frame: station_1021 parts shifted by (0, 0, -2.64) plus the residual (0.004243, 0.001645, 0.003854); I re-measured the residual from the spool (bore axis, flange face) instead of copying it, as v1 did.
The builder module is imported only for the STEP vs builder comparison and to reproduce `stackup()`.

## 1. Part integrity

| check | expected | measured | tol | status |
|---|---|---|---|---|
| cap v2 and casing v2: solids, BRep valid, STEP units | 1 solid each, valid, mm | 1, valid, mm, one MANIFOLD_SOLID_BREP each | - | PASS |
| cap v2 bbox | x,z +-7, y 22.6 .. 29.3 | identical | 0.01 | PASS |
| casing v2 bbox | x -22.15 .. 13.75, y 31.0 .. 57.1 (45 + 12.1, +y bumps), z +-13.75 | identical | 0.01 | PASS |
| volume / mass at 1.27 g/cc | cap 489.5, casing 3427.0 (notes) | 489.50 mm3 (0.622 g), 3426.97 mm3 (4.352 g) | 0.01 | PASS |

## 2. Board pocket (item 1)

| check | expected | measured | tol | status |
|---|---|---|---|---|
| pocket wall to wall, away from ribs (x and z), y 32.9 | 23.5 (11.75 per side) | 11.750 on all four walls | 0.005 | PASS |
| rib count and centres | 8, 2 per wall at +-6.5 | 8 at +-6.500 (all four walls) | 0.01 | PASS |
| rib tip distance from the axis, 8 ribs | 11.40 | 11.400 each | 0.005 | PASS |
| clear width between opposite tips, 4 pairs (x pairs at z = +-6.5, z pairs at x = +-6.5) | 22.8 | 22.800 each | 0.01 | PASS |
| rib height above the wall face | 0.35 | 0.350 | 0.005 | PASS |
| rib tip flat width, 8 ribs | 0.45 | 0.455 (resolution 0.005) | 0.02 | PASS |
| rib width at the wall face | notes: base 0.9 | 0.695, flank 19 deg from the wall normal. The 0.9 base is defined 0.3 mm INSIDE the wall (builder trapezoid); only a documentation discrepancy | - | INFO |
| rib profile in y | full height from the bed face 31.0 to y 33.5, 45 deg ramp to the wall top 33.85 | 11.400 at y 31.05 / 33.0 / 33.45; 11.50 / 11.60 / 11.70 at y 33.6 / 33.7 / 33.8 | 0.01 | PASS |
| hook lip half-length (ribs must miss the lips) | 4.0 | 4.00; rib near edge at 6.153, clearance 2.15 | min 1.5 | PASS |
| corner tab inner edge (ribs must miss the tabs) | 8.75 | 8.75; rib far edge 6.85, clearance 1.9 | min 1.5 | PASS |
| pad rows | ribs touch only the bare PCB edge | NOT measurable: the module was not available. Assumed 4-pad header, 2.54 pitch, centred, pad envelope to |z| 4.8: clearance 1.35 | min 1.0 | PASS on the assumption, see condition C5 |
| 23 x 23 x 1.6 board box seated on y 32.25: interference | 8 pieces, each at a rib (+-6.5 on a wall) | 8 pieces, all at rib positions, none on tabs, hooks or pads | - | PASS |
| same, volume | own estimate 0.502 (8 x 0.10 x mean(0.45, 0.52) x 1.30) | 0.5045 mm3 (notes 0.504) | 6 % | PASS |
| centring window: board shifted +-0.09 in x or z | all 8 ribs in contact | 8 pieces | - | PASS |
| board shifted 0.11 | two walls' ribs lost | 6 pieces | - | PASS |
| corner stops | board 0.01 toward -y collides with the 4 tabs (3.0 x 3.0 faces at y 32.25) | collides (+ volume), 4 tab faces at 32.250 | - | PASS |
| hooks | free at +0.09 toward +y, caught at +0.11 | 8 rib pieces only at 0.00 and 0.09, catch contact at 0.11 | - | PASS |
| hook lip overlap over the board back face (2 lips x 8.0 x 0.4) | 6.4 mm2, 3.2 each | 6.40 (dz 0, +-0.05), 3.20 per lip | 0.3 | PASS |
| wall deflection the lips need for a centred board | 0.4 | 0.400 (lip tip 11.10, protrusion 0.65, flat 0.35) | 0.01 | PASS |
| chip body 6 x 4 x 1.45 vs casing | 0 | 0 mm3 | 1e-6 | PASS |

The ribs are well clear of everything geometric. What is not yet shown is that the ribs centre the board in x (finding F1).

## 3. Magnet pocket (item 2)

| check | expected | measured | tol | status |
|---|---|---|---|---|
| pocket wall radius (probed 720 angles at y 28) | 3.15 (Ø6.3) | 3.150 | 0.005 | PASS |
| ribs | 3 at 60 / 180 / 300 deg | 3, centres 60 / 180 / 300 deg | 1.5 deg | PASS |
| rib tip radius / tip flat width | 2.88 / 0.45 | 2.880 / 0.455 for each | 0.005 / 0.02 | PASS |
| inscribed circle of the tips | Ø5.76 | Ø5.760 (three flats tangent) | 0.01 | PASS |
| crush on a Ø6.0 magnet | 0.12 per rib | 0.120 | 0.01 | PASS |
| play of the Ø6.0 magnet to the wall away from the ribs | 0.15 per side | 0.150 | 0.005 | PASS |
| Ø6.0 x 2.5 magnet, glued, face at 29.3: interference | 3 rib pieces, own estimate 0.439 | 3 pieces, 0.4125 mm3 (notes 0.413) | 7 % | PASS |
| centring window | 3 ribs at 0.10 shift; the 180 deg rib lost at 0.13 | 3 / 2 | - | PASS |
| head top plane (magnet face) | 29.3 | 29.300 | 0.002 | PASS |
| pocket floor / glue film | y 26.75 / face 26.75 + 0.05 + 2.5 = 29.30 | one floor plane at 26.75 | 0.002 | PASS |
| air gap magnet face to chip face | 1.5 (29.3 to 30.8) | 1.500 | - | PASS |

The magnet stays on the axis as long as the three tip radii are equal; the ribs stand on the pocket floor and do not cover the pocket centre column.

## 4. Peg ribs vs the spool bore (item 3)

| check | expected | measured | tol | status |
|---|---|---|---|---|
| spool bore Ø (from the spool faces) | 5.30 | 5.300 | 0.002 | PASS |
| peg round radius / flat, y 23.4 / 24.3 / 25.5 | 2.55 / 2.05 | 2.550 / 2.050 | 0.003 | PASS |
| 3 ribs: tip radius, tip width, crush into the bore | 2.75, 0.45, 0.10 | 2.750, 0.455, 0.100 at 60 / 180 / 300 deg | 0.004 / 0.02 / 0.005 | PASS |
| ribs clear of the bore flat (+-36 deg about +x) | >= 45 deg from +x | 60 / 180 / 60 deg | - | PASS |
| cap vs spool interference, corrected frame | 3 pieces; own estimate 0.477 | 3 pieces, 0.4766 mm3 (v1 0.163) | 8 % | PASS |
| peg (y < 26) vs the rib020 variant peg | identical | boolean difference 0 mm3 | 1e-4 | PASS |
| peg clearance to the bore away from the ribs | 0.10 | 0.100 | 0.01 | PASS |
| peg end to shaft end | 0.60 | 0.600 | 0.005 | PASS |

## 5. Foot with 8 crush bumps (item 4)

All against the slip-in divot read from the STEP, corrected frame.

| check | expected | measured | tol | status |
|---|---|---|---|---|
| foot half-width at the side centre, 4 sides, x -21.02 | 11.70 (23.4) | 11.700 each | 0.005 | PASS |
| casing vs slip-in interference | 8 pieces, 0.336 mm3 (own: 8 x 0.10 x 0.6 x 0.7) | 8 pieces of 0.042, total 0.336 | 0.01 | PASS |
| bump positions along the side (all 8) | +-9.0 | 9.000, spread 0.000 | 0.02 | PASS |
| bump width | 0.6 | 0.600 | 0.02 | PASS |
| contact depth | x -21.85 .. -21.15 (0.7 below the plate face, nothing above) | -21.85 .. -21.15 | 0.01 | PASS |
| tip minus measured divot wall, lateral, 8 bumps x 5 depths | +0.100 | 0.100 min and max | 0.006 | PASS |
| foot to wall away from the bumps, 4 sides x 5 positions x 4 depths | 0.30 | 0.300 min and max | 0.01 | PASS |
| normal gap to the 7 wall faces with the bump zones removed | 0.044 | 0.0440 | 0.012 | PASS |
| bumps are the only contact | no other interference | 8 pieces, all at bump positions; closest piece to a hole axis 8.3 | - | PASS |
| foot seats on the floor | foot bottom plane = divot floor plane -22.15 | -22.150 / -22.150; 0.01 further down adds 4.28 mm3 | 0.002 | PASS |
| foot bottom flat area | 419.1 ((21.4)^2 - 4 x 3.356 r^2) | 419.13 | 1.0 | PASS |
| foot holes Ø3.4, coaxial with the divot holes | offset 0 | 0.000 (corrected frame), pitch 9.500 | 0.001 | PASS |
| holes clear along the axis | no casing material | clear (4 holes) | - | PASS |
| centring window: foot translated 0.09 / 0.11 (z, y) | 8 / 6 bumps | 8 / 6 | - | PASS |
| foot rotated 0.5 / 0.8 deg | 8 / fewer | 8 / 4 | - | PASS |
| entry, interference volume vs foot raised 0 / .1 / .2 / .3 / .4 / .5 mm | decreasing to 0 | 0.336 / 0.173 / 0.070 / 0.021 / 0.0015 / 0.000 | - | PASS |

The bump envelope follows the measured dish wall, so the crush is 0.10 lateral at every depth. It is a wedge (a lead-in) that starts to bite at about 0.4 mm of raise. Plain-frame (-2.64 only) casing vs slip-in is 2.14 mm3: the 0.336 of bumps plus the 0.0042 mm floor contact sheet that v1 accepted.

## 6. Unchanged from v1 (item 6)

| check | expected | measured | status |
|---|---|---|---|
| casing to Shell_Casing | >= 1.0 | 17.11 (plain 17.11) | PASS |
| casing to Spool / Motor / Heat_horn / Wall_Mount | info | 5.00 / 12.91 / 31.00 / 7.64 | INFO |
| casing vs the 6 station parts, corrected frame | 0 except the slip-in (bumps, 0.336) | 0 for five parts, 0.336 for the slip-in | PASS |
| cap vs the 6 station parts | 0 except the spool (peg ribs, 0.477) | 0 for five parts, 0.4766 for the spool | PASS |
| cap swept 360 deg, 5 deg steps, vs casing | >= 1.0 | 5.154 | PASS |
| envelope of revolution of the head vs casing | sqrt(4.75^2 + 1.7^2) = 5.045 | 5.045 | PASS |
| cap envelope to board + chip body | 1.5 (chip only) | 1.500 | PASS |
| nothing below y 26 | casing y min >= 26, line zone empty | 31.0, 0 mm3 in the y 7..26, r 19 zone | PASS |
| cap below y 26 | inside the bore | max radius 2.7585, 0 mm3 beyond r 2.9 | PASS |
| zip-tie slots (z = +-6.2), bridge top | open through y, 36.2 | open, 36.200 | PASS |
| screw-access cylinders Ø7 x 55, 4 holes | no casing or station part; closest feature 0.55 | 0 mm3 against all 7; 0.55 (bridge) | PASS |
| STEP vs builder (bbox 6 numbers, volume), both parts | equal | equal to 1e-3 / 0.01; boolean difference 0.000 mm3 (exports are current) | PASS |
| STEP, reimport, re-export, reimport | unchanged, 1 solid, valid | unchanged | PASS |
| STL watertight, volume vs STEP, print-pose extents | 0 open edges, 0.3 %, 0.005 | 0 / 489.32 vs 489.50 and 3427.0 vs 3427.0 / equal | PASS |
| v1 exports and rib/foot variants untouched | unmodified | git clean for them | PASS |
| v2 renders | 14 standard views | all present (24 v2 files) | PASS |

Note on a coincidence, not a defect: the zip-tie slots at z = +-6.2 sit directly behind the two -x board ribs (rib base z 6.15 to 6.85, slot 5.4 to 7.0). Behind each rib is 2.75 mm of solid (wall + 0.75 strut), then the 3.0 mm slot. It stays rigid, because the span is only 1.6 mm.

## 7. Printability of the new features (item 7)

| check | expected | measured | status |
|---|---|---|---|
| rib tips >= 0.45 | board, magnet, peg tips 0.45; bump 0.6 | 0.455 / 0.455 / 0.455 / 0.600 | PASS |
| board ribs: undersides | none; they start on the bed face | zero overhang clusters over the pocket plan other than the 2 hook ledges (10.4 mm2 = 2 x 0.65 x 8.0); bed contact 390.31 mm2 = frame front + rib footprints | PASS |
| lead-in ramp is a top face | 45 deg | ramp faces +y (printable) | PASS |
| bump undersides | about 2 mm2 (notes) | 0.76 mm2 (the four +-z bumps, 0.4 protrusion x 0.95) + 1.23 mm2 (the +-y bumps, curved) = about 2.0 mm2, each a 0.4 mm ledge. The total non-ledge overhang is 24.7 mm2 against 23.5 for v1 (+1.15), because the foot key-edge clusters shrank with the 23.4 foot | PASS |
| cap: pocket-floor bridge | Ø6.3, ribs stand on it | 30.68 mm2 (disc 31.17 less rib footprints), span 6.28 mm | PASS (with the v1 caveat on 6 mm PETG bridges) |
| magnet-rib lead-in at the mouth (printed upward from the bed) | not steeper than 45 deg | d(radius)/d(y) = 0.990, exactly 45 deg | PASS, no margin |
| peg-rib lead-in | at the top of the print, a top chamfer | PASS | PASS |

Limits worth knowing: a 0.45 mm tip is one bead with a 0.4 nozzle and 0.45 line width; the flanks (0.695 base at the wall) will be rounded; the 0.6 wide x 0.4 proud bump is 1.5 beads and will print slightly rounded. A slicer with "thin wall detection" off or a coarse line-width will drop or fatten them. Print the first article at 0.12 to 0.16 mm layers as the notes say.

## 8. Stack-up (item 5)

x is the floor normal, z across the divot, arm of the foot rotation 14.2 mm (divot centre y 45.0 minus chip face 30.8), bump lever 9.0 (measured). Worst case is the linear sum of the term bounds, RSS the quadrature of the bounds, as in v1.

Reproduction of the implementer's model with my own code: worst 0.31667 (claim 0.317), RSS 0.15402 (claim 0.154), `encoder1021.stackup(2)` agrees. Break-even eps for its own targets: 0.0632 (worst 0.40) and 0.0812 (RSS 0.25), as claimed. So the arithmetic is right. Its inputs need two corrections.

Correction A, three-rib features (peg and magnet). A rigid circle in three equal springs at 120 deg moves by c = (2/3) Sum e_i n_i. With tip errors bounded by eps this is 4/3 eps at most (e = +eps, +eps, -eps gives a 2 eps vector). The notes use 1 eps. Effect at eps 0.05: x 0.150 to 0.183, z 0.279 to 0.312.

Correction B, the board's x centring. Equal stiffness on both sides is the assumption of the elastic balance. It does not hold in x. The numbers are beam estimates (Euler-Bernoulli, E 2100, clamped ends which is optimistic for the +x wall), see `test_8_stackup`:

| | stiffness at one rib |
|---|---|
| +x wall (free 2.0 x 2.85 plate, span 27.5, two ribs) | about 50 N/mm |
| -x wall (rib on the 9.15 mm wall + bridge block, rib alone) | about 4400 N/mm |
| z flex walls (two identical 1.2 mm walls) | about 38 N/mm each side: symmetric, real centring stiffness 151 N/mm |

The balance F+ = 50 (0.10 + c) = F- = 4400 (0.10 - c) gives c = +0.098 mm, forces about 10 N per rib, still elastic (rib yield about 26 N). Even with a rib 5 times softer or a wall 5 times stiffer c stays +0.056. So the board sits on the -x rib tips: the x centre is set by one side. A PCB outline of 23.0 +-0.15 then moves the chip by +-0.075 in x, which with working two-sided centring would cancel.

Results, radial (mm), same bounds method; "+B" adds the 0.098 x offset:

| eps | implementer worst / RSS | with A worst / RSS | with A and B worst / RSS |
|---|---|---|---|
| 0.03 | 0.190 / 0.092 | 0.217 / 0.106 | 0.280 / 0.145 |
| 0.05 | 0.317 / 0.154 | 0.362 / 0.177 | 0.420 / 0.203 |
| 0.08 | 0.507 / 0.246 | 0.579 / 0.284 | 0.634 / 0.300 |
| 0.10 | 0.633 / 0.308 | 0.724 / 0.355 | 0.778 / 0.368 |

| check | expected | measured | status |
|---|---|---|---|
| implementer's worst and RSS reproduced | 0.317 / 0.154 | 0.3167 / 0.1540 | PASS |
| verifier model (A+B) at eps 0.05, RSS vs the implementer's own 0.25 target | <= 0.25 | 0.203 | PASS |
| same, worst vs the implementer's own 0.40 target | <= 0.40 | 0.420 | WARN |
| worst case vs the AS5600 0.25 mm guidance | <= 0.25 | 0.317 (implementer) / 0.420 (A+B) at eps 0.05 | WARN |
| eps at which the A+B RSS reaches 0.25 | - | 0.062 | INFO |

Is eps = 0.05 reasonable for FDM PETG? It is a plausible best case for a tuned printer when opposing features come from the same layers, with beads of nominal 0.45 mm repeating to 0.03 to 0.05. It is not a safe design value:
- opposing ribs sit on opposite XY motions, so backlash, belt skew, bead start/stop and seam effects commonly add 0.05 to 0.10;
- the rib tip is 1 bead and its position error equals the bead error;
- ribs on rigid supports yield at 5 microns of crush (magnet rib 9576 N/mm and 49 N yield, peg rib 11571 N/mm and 59 N, foot bump 3906 N/mm and 21 N). Their centring is then bounded by the crush (0.10 to 0.12), not by eps; only the symmetric first contact and friction decide where the part ends up.
Budget eps 0.08 for planning: A+B gives 0.30 RSS and 0.63 worst. v1 was 0.44 / 0.78, so v2 is still better, by 1.2 to 1.5 times at eps 0.08 and 1.9 to 2.2 times at eps 0.05, not the 2.5 to 2.9 times the notes imply (0.783 / 0.317 and 0.441 / 0.154). Measure eps on the first print (condition C3).

## 9. Findings

| id | severity | finding | evidence |
|---|---|---|---|
| F1 | medium (design) | The board's x centring is one-sided: -x ribs are on a 9.15 mm block, +x ribs on a free 2.0 mm plate (50 vs 4400 N/mm per rib). Estimated x offset +0.10 mm (0.06 to 0.10), PCB width error enters at w/2. Not in the claimed stack-up. Fix options (not applied): put the -x ribs on a compliant wall too (relief slots or a thinner -x wall), or stiffen the +x wall (rib or thicker wall), or accept a one-sided datum on purpose and shift the pocket centre by the offset | section 8, `test_8_stackup` |
| F2 | medium | Three-rib features (peg, magnet) move by up to 4/3 eps, not eps | section 8 |
| F3 | medium | Ribs on rigid supports (magnet pocket, peg vs spool bore, foot bumps vs slip-in) yield at about 5 microns, so the equal-rib "elastic balance" is a constant-force balance. eps 0.05 is optimistic for these; the real bound is the crush (0.10 to 0.12) | section 8 |
| F4 | low-medium | Worst case does not meet 0.25 mm at eps 0.05 even in the implementer's model (0.317). The 0.40 worst-case target is relaxed, not the datasheet figure | section 8 |
| F5 | low-medium | Press-in forces were not estimated by the implementer. My rough values (factor 2 to 3 uncertainty): board 9 to 20 N sliding, brief 60 to 120 N peak at the 45 deg ramp; magnet 40 to 130 N sliding if the ribs yield rather than shave; foot 100 to 330 N total, drawn in by four M3 screws (25 to 80 N each). The magnet is the tight one and cannot be eased by a smaller crush, because a yield-limited rib's force depends on its contact area, not its crush | section 10 |
| F6 | info | Rib base width at the wall face is 0.695, not 0.9 (the 0.9 base is 0.3 mm inside the wall). No effect on the interference, tip width and heights are right | section 2 |
| F7 | info | Real module not available: pad rows and board edge features at +-6.5 are assumed clear (1.35 mm from an assumed pad envelope), PCB outline and chip placement tolerance are not controlled by the ribs | condition C5 |
| F8 | info | Magnet rib lead-in is exactly 45 deg (0.990), no margin against a stricter overhang setting | section 7 |
| F9 | info | Carried from v1, not these parts: AS5600 0.25 mm figure from datasheet mirrors only; spool-on-shaft eccentricity (up to 0.15), slip-in/motor seat, divot-to-shaft tolerance are not in any stack-up here; `cad/interfaces.py` has no encoder record | v1 report |

## 10. Insertion and cracking risk (item 8), rough hand calculation

Assumptions (mine): PETG E 2100, yield 45 MPa (cad/materials.py), friction 0.25 to 0.45, 45 deg lead-ins (measured), board ribs contact length 1.30, ribs on beam walls clamped at the ends (optimistic stiffness), confined-yield factor 1 to 2 on rigid supports. Wedge factor (sin45 + mu cos45) / (cos45 - mu sin45) is 1.67 to 2.64.

| operation | lateral squeeze | sliding force | brief peak at the ramp |
|---|---|---|---|
| board past 8 ribs | 35 to 45 N total (z ribs 3.8 N each, x ribs 5 to 10 N) | 9 to 20 N | 60 to 120 N |
| magnet past 3 ribs | 150 to 300 N | 40 to 130 N | high; the ribs will shave rather than yield fully, treat as 2 to 3 times the sliding value |
| foot past 8 bumps | 170 to 335 N normal on the divot wall | 100 to 330 N axial, by 4 screws | the bump wedge engages after about 0.4 mm raise |

What could crack:
- Hooks and z walls: central force to pass a lip at 0.4 deflection is 7.2 N per lip, wall stress 22 MPa; a rib at 0.10 crush adds 12 MPa; summed (conservative, they do not coincide) 34 MPa = 76 % of yield. No crack at a normal push; no margin for a skewed board or levering. The lip tip flat is only 0.35 mm and 2 layers thick: never lever the board out with a screwdriver on the hooks.
- Tabs, ring, bridge: lateral loads only a few N to 10 N; no risk.
- Cap: the magnet pocket ring is 3.85 mm thick, the 0.75 mm pocket floor carries 5 MPa under 150 N; no crack risk. The risk is chipping the nickel coat on the magnet if it is hammered; use a flat plate.
- Slip-in: the foot bumps load the divot wall; the slip-in is a massive part. The real risk is the four M3 holes: threads in printed PETG hold a few tens of N. Draw the foot with a diagonal sequence, and prefer heat-set inserts, which is still the open question for Jasper.

## 11. Conditions for printing and the first fit test

C1. Print one casing and one cap per variant, not five. Use 0.12 to 0.16 mm layers, 0.4 nozzle, 0.45 line width. Keep the v1 cap-rib variants as a fallback.
C2. Measure before inserting anything: board outline (both axes), PCB thickness, chip height; magnet Ø and thickness; real spool bore; real divot width; and the printed ribs, tips and bumps with calipers or pin gauges.
C3. Measure eps: caliper the clear width between opposite rib tips (expected 22.80), the foot over the bumps in both axes (expected 24.20), the magnet pocket over the ribs (expected 5.76 inscribed). The difference between opposite sides is eps. Also record the board position in the pocket at +x and -x after insertion (F1: expect the board to touch the -x ribs and show about 0.2 of crush on the +x side).
C4. Press-in procedure: board square, push on the back face with a flat tool, never on the hooks; magnet in a drop of CA with a flat plate; foot by the screws in a diagonal sequence, a few turns each. If the magnet will not go in with thumb pressure, ask for a cap variant with shorter rib pads (for example 1.0 mm instead of the full 2.5 mm); a smaller crush alone will not lower a yield-limited force.
C5. Check the real board at the rib positions (+-6.5 along each edge, 0.45 wide): no pad, solder, or SMD part within that zone. Move `ENC1021_V2_BOARD_RIB_POS` if there is one.
C6. After the first print, read the AS5600 status bits (MD set, ML and MH clear) and the angle error over a full turn; decide F1 and the eps budget from the measurement, and open the official ams datasheet to confirm the 0.25 mm figure.
C7. Record F1 to F3 in DESIGN_STATE. A Fable audit is not needed for printing; it would be needed if the first article shows an x offset beyond about 0.1.

## 12. Not verified

Real board and magnet dimensions, PETG shrinkage and printer accuracy, actual rib yield and insertion forces (no physical test, beam estimates only), the official AS5600 datasheet figure, slip-in hardware (insert or screw), wire routing, magnet strength and AGC with the real parts, SOLIDWORKS mates and drawings.
