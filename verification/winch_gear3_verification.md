# Winch 3:1 spur drive train: independent geometry verification (geometry-verifier, 10/23)

**Contract:** `cad/WINCH_GEAR3_SPEC.md`. **Subject:** `exports/step/winch_gear3_{spool_gear60,spacer_near,magnet_cap,drive_asm1021,drive_with_slipin_asm1021}.step`,
`exports/stl/winch_gear3_{spool_gear60,spacer_near,magnet_cap}.stl`, `renders/winch_gear3/*.png`, `cad/params.py` block `WG3_*`.
**Evidence file:** `tests/test_winch_gear3_verify.py` (26 tests, 341 recorded checks, **all PASS**, 5 min 43 s). It prints the full table with `-s` (see section 7).

## Verdict

**PASS: 0 failures** against spec sections 1 to 5 as requested (items 1 to 7). Nothing needs to go back to the implementer.
Section 6 lists observations and risks that are not failures; the ones that matter for Jasper's design are N1 (zero axial play in the bearing stack), N2 (line-to-line fits) and N3 (spacer land vs the real 687 inner race).
The interference list against Jasper's slide-in and wall mount reproduces the build notes to within 0.1 mm³ (3953.3 / 54.8 / 35.2 / 697.3 mm³); the notes miss nothing that involves the drive bodies.

## 0. Method and independence

- Measured the **exported STEP/STL files only**, with fresh code: CadQuery 2.8.0 / OCP under `/usr/bin/python3`; XCAF reader for the assembly names and placements. The implementer's builder, tests and measurements were not imported or run. The build notes were used only to know which numbers to look for, and each is compared in section 4.
- The only repository code loaded: the spec-mandated generator `cad/gripper_v3_fit_review_20261018/gears.py` (to rebuild the teeth independently) and, read-only, `cad/params.py` (parameter audit). Spec numbers are hard-coded in the test file from the spec text.
- **Frames.** Assembly STEPs are station_1021 + O, O = (1269.08, 738.76, 927.56), plus the deliberate 0.004 mm extraction residual (+0.004243, +0.001645, +0.003854). All assembly values below are in the spec design frame (O + residual removed). Position tolerance 0.005 mm (the residual is known to 1e-6). Part STEP/STL files are in the print frame (axis +z, gear near face on z = 0; design y = z + 10.825 for `spool_gear60`).
- **Offset O is independently confirmed:** the slide-in and wall mount in `_with_slipin_asm1021` coincide with the same parts of Jasper's original `solidworks/v4_assembly_2026-10-21/Assem_laundry_v3_step_1021.STEP` in absolute coordinates (volume 217693.1525 / 596918.86 mm³, bbox difference < 1e-3 mm, symmetric difference 0.00001 / 0.0057 mm³).
- **Independent rebuild of the spool** from spec section 3 (generator 60T gear at phase 3 deg, six Ø11 windows on R20, drum, flange, hub, land, Ø7 bore, chord hole): the exported solid lies entirely inside it (0.00000 mm³ outside) and the only difference is the 0.3 mm bed-face chamfer (16.495 mm³; perimeter x 0.3 x 0.3 / 2 = 16.60).
- Negative controls prove the tests can fail: gear turned 0.5 deg alone gives 1.95 mm³ overlap (3 deg: 40.7 mm³).

## 1. STEP files: validity, solids, names, round trip (request item 1)

| File | Solids | Valid BREP | Volume mm³ | BBox (print frame) | Round trip (re-export, reimport) dV / dBBox | STL: watertight, dV vs STEP | Status |
|---|---|---|---|---|---|---|---|
| `spool_gear60` | 1 (1 shell) | yes | 27345.934 | x,y +-30.9735, z 0 to 33.175 | 1.5e-9 / 4e-15 (tol 1e-3) | yes (62 076 triangles), -0.003 % (tol 0.1 %) | PASS |
| `spacer_near` | 1 | yes | 217.918 | x,y +-5.0, z 0 to 5.825 | 0 / 0 | yes, -0.041 % | PASS |
| `magnet_cap` | 1 | yes | 514.614 | x,y +-6.0, z 0 to 6.25 | 7e-15 / 0 | yes, -0.042 % | PASS |
| `drive_asm1021` | 17 bodies, 17 solids in file | all 17 valid, one shell each | total 122 947.28 | x -30.97 to 30.98, y -41.17 to 60.10, z -68.53 to 210.24 (tall fin) | worst body 1.5e-9 / 2e-13 mm; total 3e-10 | n/a | PASS |
| `drive_with_slipin_asm1021` | 19 bodies, 19 solids | all valid | total 937 559.29 | x -42.31 to 30.98, y -94.44 to 125.56, z -68.61 to 210.24 | worst body 1.5e-9; total 4e-11 | n/a | PASS |

- All STEP files declare millimetres (`SI_UNIT(.MILLI.,.METRE.)`). STEP vs STL bbox difference <= 0.002 mm.
- Named bodies, expected = spec section 5 list, measured = the 17 names found (`PRODUCT` entities and XCAF): `motor_front_cap, motor_stator, motor_winding, motor_rear_cap, motor_shaft, motor_connector, fin, pinion, spool_gear60, shaft, bearing_near, bearing_far, spacer_near, magnet_cap, magnet, as5600_chip, as5600_board`; the with-slip-in file adds `slipin_mount`, `wall_mount`. No missing, extra or duplicate names. **PASS**.
- No unintended disconnected bodies: every body is exactly one solid with one shell. **PASS**.
- Part files equal the assembly bodies: symmetric difference of the transformed part STEP and the assembly body is 0.00000 mm³ for the spool, the spacer and the cap. **PASS**.
- `fin` equals `heat_fin1021_1p8_asm1021.step` (V 26 905.8243, bbox difference 0). Motor front cap, stator, winding, rear cap and connector equal the `nema17_thermal_fin1p8_asm1021.step` bodies (volume and bbox, 0.000). `motor_shaft` differs by the D-flat only: removed 22.481 mm³ = circular segment (R 2.5, depth 0.5) x 22 mm; flat plane at z = 4.64 (axis + 2.0, +z side, as Motor_Reference), y -1.175 to 20.825. **PASS**.
- `git show --stat 609aff7`: the implementer's commit adds new files, appends 95 lines to `params.py` (0 deletions) and changes one export bullet of the spec; no existing export, reference STEP, encoder or heat-fin file is modified (see N6 for the spec edit).

## 2. Gear stage (request item 2)

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Gear teeth (disjoint tooth sections at the pitch ring) | 60 | 60 (60 tip faces, 60 root faces) | exact | PASS |
| Pinion teeth | 20 | 20 (20 tip, 20 root faces) | exact | PASS |
| Ratio | 3.000 | 3.000 | 1e-9 | PASS |
| Gear tip / root Ø | 62 / 57.5 (R 31.0 / 28.75) | 62.000 / 57.500 | 0.01 | PASS |
| Pinion tip / root Ø | 22 / 17.5 (R 11.0 / 8.75) | 22.000 / 17.500 | 0.01 | PASS |
| Pinion bore axis (x, z) | (0, 2.64) | (0.0000, 2.6400) | 0.005 | PASS |
| Spool bore axis (x, z) | (0, -37.56) | (0.0000, -37.5600) | 0.005 | PASS |
| Centre distance, bore axis to bore axis | 40.200 | 40.2000 | 0.001 | PASS |
| Pinion teeth y range / width | 10.825 to 20.825 / 10 | 10.825 to 20.825 / 10.000 | 0.005 | PASS |
| Gear teeth y range | 10.825 (bed face) to 20.825 | 10.825 to 20.825 (tip faces start at 11.125: the 0.3 chamfer) | 0.005 | PASS |
| Motor shaft end y | 20.825 | 20.825 | 0.005 | PASS |
| Tooth form (module 1, 20 deg, thinning 0.10 gear / 0 pinion, root blend 0.4) | equals the repo generator | symmetric difference with the generator rebuilt independently: 0.00000 mm³ (gear), 0.00000 mm³ (pinion) | 0.01 mm³ | PASS |
| Tooth thickness at the pitch circle | gear pi/2 - 0.10 = 1.4708; pinion pi/2 = 1.5708 | 1.4704; 1.5696 (ring-averaged) | 0.005 | PASS |
| Phasing at the reference pose | gear tooth SPACE and pinion tooth on the line of centres | gear radius there 28.750 (root); pinion radius 11.000 (tip) | 0.005 | PASS |
| Mesh overlap, 7 poses 0 to 18 deg (pinion +theta, gear -theta/3), plus 7 exploratory poses incl. negative | 0 mm³ | 0.00000 mm³ at all poses | 0.001 | PASS |
| Minimum flank-to-flank distance per pose (0 / 3 / 6 / 9 / 12 / 15 / 18 deg) | > 0 | 0.1166 / 0.1167 / 0.1167 / 0.1167 / 0.1167 / 0.1167 / 0.1166 mm | >= 0.05 | PASS |
| Tip-to-root clearance, both ways (CD - R_tip - R_root) | 0.45 | 0.450 / 0.450 | 0.002 | PASS |
| Free pinion rotation with the gear fixed (contact bisection) | 1.41 deg total (0.246 mm at R10) | +0.712 / -0.712 deg, 1.425 deg total = 0.249 mm at the pinion pitch circle = 0.475 deg and 0.062 mm of cable at the drum (R7.5) | 0.05 deg | PASS |

Exploratory, not in the test file: with the gear moved 0.2 mm toward the pinion (CD 40.00) there is still no overlap (distance 0.047 mm): the gear's 0.10 thinning alone clears the nominal-centre-distance mesh, and the +0.20 adds the rest of the backlash; the minimum-distance points sit near the gear tip and the pinion base circle (pinion r 9.49, gear r 30.96).

## 3. `spool_gear60` (request item 3; print frame, z = y_design - 10.825)

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Part extent | y 10.825 to 44.0 (z 0 to 33.175) | z 0.000 to 33.175 | 1e-6 | PASS |
| Six windows: Ø, pitch radius | Ø11 on R20 | 6 faces R 5.5, axis offset 20.000 (+-1e-4) at 0, 60 .. 300 deg; z 0 to 10 | 1e-4 | PASS |
| Window outer / inner edge | R25.5 / R14.5 | 25.500 / 14.500 | 1e-4 | PASS |
| Rim below the root | >= 3 (3.25) | 3.250 (root R28.75 minus 25.5) | - | PASS |
| Web window to drum core | >= 2 | 7.000 | - | PASS |
| Spoke on the line of centres (270 deg print frame) | no window | solid [3.5, 28.75] along 30, 90, 150, 210, 270, 330 deg | - | PASS |
| Gear z range | 0 to 10 | 0 to 10 | 1e-4 | PASS |
| Drum | Ø15, y 20.825 to 36.825 (16 long) | R 7.500, z 10.0 to 26.0 | 1e-3 | PASS |
| Outer flange | Ø36 x 3, y 36.825 to 39.825 | R 18.000, z 26.0 to 29.0 | 1e-3 | PASS |
| Far hub | Ø12, y 39.825 to 44.0 | R 6.000, z 29.0 to 32.875 | 1e-3 | PASS |
| Ø9 land, 0.3 proud | R4.5, 0.3 | R 4.500, z 32.875 to 33.175 (0.300) | 1e-3 | PASS |
| Bore | Ø7.00 through | one face R 3.500, z 0 to 33.175, coaxial | 1e-3 | PASS |
| Tie-off hole Ø, offset, position | Ø1.4, 5.25 off axis, y 28.825 (z 18.0) | R 0.7000, axis x 5.2500, z 18.000, direction perpendicular to the axis | 1e-4 | PASS |
| Ligament to bore / to core surface | 1.05 / 1.55 | 1.050 / 1.550 (rays through the solid) | 0.002 | PASS |
| Hole open on the winding surface, both ends | open | no material along the hole axis for y -9 to +9; at y = +5.3 and y = -5.3 the section is [0, 4.55] only (broken out); control line 1.0 mm lower crosses the 10.71 mm chord | - | PASS |
| Hole side as Spool1011 | +x, along station z | Spool1011 hole at x +6.0 along z: same side and direction | - | PASS |
| Bed-face chamfer 0.3 x 45 deg on the tooth edges | 0.3 | tooth tip radius 30.701 / 30.800 / 30.900 / 31.000 at z 0.001 / 0.1 / 0.2 / 0.3; root 28.451 / 28.550 / 28.650 / 28.750 (all +-0.003 of 45 deg); window and bore edges at the bed face are not chamfered (3.5, 14.5, 25.5 unchanged); removed volume 16.495 mm³ | 0.003 / 0.4 mm³ | PASS |
| Volume | rebuild minus chamfer | 27 345.934 mm³ (34.7 g at 1.27 g/cm³, solid) | 0.01 | PASS |

**Printability on the gear's near face (z 0 on the bed):** bed contact 2083.6 mm² (one planar face). Overhangs steeper than 45 deg (STL): only the **flange inner face z 26.0, 840.8 mm²** (annulus R7.5 to R18, overhang 10.5 mm: needs supports, as the spec expects) and the **tie-off hole roof, 11.2 mm²** (horizontal Ø1.4 hole: a 1.4 mm bridge, or drill it out). The 0.3 mm bed chamfer sits at exactly 45 deg (58 mm², facets nz -0.707 to -0.713), at the limit but only 0.3 mm tall. Windows, bore, drum, hub and land are vertical or upward-facing: no supports.

## 4. Spacer, shaft, bearings, magnet cap, magnet, AS5600 (request item 4)

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Spacer length / OD / bore | y 5.0 to 10.825 (5.825) / Ø10 / Ø7.10 | 5.825 / 10.000 / 7.100 | 1e-4 | PASS |
| Spacer lands | Ø9 at both ends | R 4.5 lands, 0.3 proud, z 0 to 0.3 and 5.525 to 5.825 (flat ends, prints either way) | 1e-4 | PASS |
| Spacer volume | analytic pi(25 x 5.225 + 20.25 x 0.6 - 12.6025 x 5.825) | 217.918 (217.918) | 0.01 | PASS |
| Spacer in the assembly | y 5.0 to 10.825, axis z -37.56 | 5.000 to 10.825; -37.560 | 0.005 | PASS |
| Shaft | Ø7 x 55, y -3.0 to 52.0, axis (0, -37.56) | Ø7.000, y -3.000 to 52.000, axis (0.000, -37.560) | 0.005 | PASS |
| Bearing near / far | 687, 7 x 14 x 5, y 0 to 5 / 44 to 49 | R 3.5 / R 7.0, width 5.000, y 0.000 / 44.000, axis (0, -37.56) | 0.005 | PASS |
| Cap Ø / thickness | Ø12 / 6.25 (y 49.3 to 55.55) | 12.000 / 6.250; y 49.300 to 55.550 | 1e-4 / 0.005 | PASS |
| Cap bore | Ø7, 3.0 deep (y 49.3 to 52.3) | R 3.500, depth 3.000; floor y 52.300; shaft end 52.0 leaves 0.300 | 1e-4 / 0.005 | PASS |
| Web | >= 0.75 (0.75) | 0.750 (material z 3.0 to 3.75 on the axis) | 1e-6 | PASS |
| Magnet pocket | Ø6.3 x 2.5 (y 53.05 to 55.55) | R 3.150, depth 2.500, floor y 53.050 | 1e-4 | PASS |
| Crush ribs | 3 ribs, 0.15 per side + 0.12 crush | 3 ribs at 90, 210, 330 deg; tip R 2.880 (protrusion 0.270 = 0.15 + 0.12); wall R 3.150 between; width 0.463 mm at R2.9 (tip 0.45) | 0.002 | PASS |
| Cap volume | cylinder - bore - pocket + ribs | 514.614 (513.47 + ribs 1.1) | within 0..3 | PASS |
| Cap to far bearing | 0.3 | 0.300 | 1e-3 | PASS |
| Magnet | Ø6 x 2.5, y 53.05 to 55.55, flush with the cap face | Ø6.000 x 2.500, y 53.050 to 55.550 (cap face 55.550), axis z -37.560 | 0.005 | PASS |
| Magnet-rib interference | by design, 3 ribs x 0.12 | 0.4125 mm³ | 0.2 to 0.6 | PASS |
| AS5600 chip | face y 57.05 (1.5 from the magnet face), 1.45 tall, 6 x 4 | face 57.050, air gap 1.500, height 1.450, 6.000 x 4.000, centred on the axis | 0.005 | PASS |
| AS5600 PCB | 23 x 23 x 1.6 at y 58.5 to 60.1, centred | 23.000 x 23.000, y 58.500 to 60.100, centre (0.000, -37.560) | 0.005 | PASS |
| Pinion hub / bore | Ø14 x 5 (y 5.825 to 10.825) / Ø5 through | R 7.000, 5.825 to 10.825 (5.000; 0.825 clear of the tab face y 5.0) / R 2.500, y 5.825 to 20.825 | 0.005 | PASS |
| Pinion set-screw hole | Ø3.0 radial toward the D-flat (+z), hub mid-plane | one R 1.5 hole, direction z, y 8.325; open from bore to outside on +z, wall intact on -z | 0.005 | PASS |
| Pinion mass (steel 7.85) | informative | 27.64 g | - | PASS |

Contacts (distance 0.0000 mm, all PASS): motor front cap/fin, spacer/spool, spacer/near bearing, spool/far bearing, magnet/cap, chip/PCB, shaft with spool, both bearings and cap, pinion/motor shaft, motor shaft/front cap.
Radial fits, bore R minus shaft R (CAD nominal): spool 0.000, both bearings 0.000, cap 0.000, spacer +0.050 (7.10 slip), pinion bore on the Ø5 motor shaft 0.000. All as the spec states.

## 5. Clearances and overlaps inside the drive (request item 5)

| Item | Expected | Measured | Status |
|---|---|---|---|
| Overlap of any two of the 17 drive bodies (24 pairs with overlapping bounding boxes, all computed; 136 pairs in total) | <= 0.01 mm³ except cap ribs into the magnet | only `magnet_cap` / `magnet`: **0.4125 mm³** (by design). All others 0.000000 | PASS |
| Gear tip to pinion hub | >= 1.5 mm | **2.3345 mm** (closest points at y 11.125 on a gear tooth, hub top edge) | PASS |
| `spool_gear60` to `motor_front_cap` / `stator` / `winding` / `rear_cap` / `shaft` / `connector` | >= 1.5 mm | 12.000 / 22.000 / 22.000 / 44.000 / 6.815 / 46.661 mm | PASS |
| `spool_gear60` to `fin` | >= 1.5 mm | 10.825 mm | PASS |
| Pinion to fin; pinion hub to tab face | info | 7.211 mm; 0.825 mm | PASS |

## 6. Interference with Jasper's current slide-in and wall mount (request item 6; redesign inputs, not failures)

All 17 drive bodies against `slipin_mount` and `wall_mount` (volume of the boolean common, design-frame coordinates):

| Mount | Drive body | Measured mm³ | Build notes | Location / detail |
|---|---|---|---|---|
| `slipin_mount` | `spool_gear60` | **3953.304** | 3953.3 | one connected intersection, x -30.97 to 13.85, y 10.82 to 25.56, z -52.38 to -15.40; by region: back plate x < -21.15: 2003.43 (notes 2003.4); deck block z < -42.4: 1860.56 (1860.6), of which under the gear 1760.32 (1760.3), under the drum 58.75, in the far cheek 41.49; far cheek above the deck: 89.31 (89.3), of which 83.52 in the cheek y 23.6 to 25.6 and 5.79 gear and drum |
| `slipin_mount` | `shaft` | **54.808** | 54.8 | 2 x 27.404, x -3.50 to 1.85, z -41.06 to -35.71, at y 5.56 to 7.56 and 23.56 to 25.56 (both lug cheeks) |
| `slipin_mount` | `spacer_near` | **35.247** | 35.3 | x -5.00 to 2.93, y 5.56 to 10.52, z -42.56 to -34.63 |
| `wall_mount` | `spool_gear60` | **697.297** (13 pieces) | 697.3 | main piece 686.093 (x -24.3 to -8.45, y 10.82 to 20.83, z -66.6 to -55.91; notes 686.1); 12 slivers 11.205 in total (0.08 to 1.88 each, x -30.97 to -29.79, z -45.9 to -29.2; notes 11.2) |

Everything else: 0.000 mm³. The notes miss no overlap that involves a drive body. Informative, from the original SolidWorks assembly: `Shell_Casing` x `spool_gear60` 1164.596 (notes 1164.6), x `as5600_board` 180.114 (180.1), x each bearing 6.126 (6.1); `Spool1011` (the part being replaced) x `pinion` 2012.939 (2012.9), x `motor_shaft` 8.353 (8.4). All reproduced.

**Not in the notes** (near misses and one pre-existing item, for Jasper):
- `Shell_Casing` x `fin` = **68.943 mm³** (x -20.0 to 22.0, y -3.17 to -2.69, z 27.8 to 31.3). Not caused by the drive: the 1/8 in fin is 1.175 mm thicker than the Heat_horn it replaces (`Shell_Casing` x `Heat_horn` = 0). It is in the `heat_fin1021_1p8` work, not here.
- `slipin_mount` to `bearing_near`: 0.56 mm (the lug's near cheek face at y 5.56 against the bearing face at y 5.0): no overlap, but the seat the notes say Jasper extends must clear this cheek.
- `Shell_Casing` to `magnet_cap`: 0.61 mm; to `spacer_near`: 1.61 mm.
- `slipin_mount` touches (distance 0) `motor_front_cap`, `stator`, `rear_cap` and `fin`: Jasper's existing contacts, unchanged.

## 7. Renders (request item 7), each opened and looked at

| Render | Caption / name | What it shows | Matches its name |
|---|---|---|---|
| `winch_gear3_front.png` | front, from +x, +y right | Motor (left), fin plate (clipped at the top), pinion hub and teeth, 60T gear, drum with the two tie-off hole openings, flange, hub, far bearing, cap, chip and board; near shaft end, near bearing and the blue spacer at left | yes |
| `winch_gear3_side.png` | side, end view from +y, +x left | Fin and motor face behind, 20T pinion with the shaft end above, 60T gear with six windows, flange (faceted circle), the 23 x 23 board in front, motor connector at the left | yes |
| `winch_gear3_top.png` | top, from +z, +y left | Same stack seen from above; the set-screw hole is visible on the pinion hub and the see-through tie-off hole on the drum | yes |
| `winch_gear3_iso.png` | iso from +x, +y, +z | Whole drive: motor and fin, pinion engaging the gear, windows, drum, flange, far bearing, cap, board | yes |
| `winch_gear3_mesh.png` | mesh close-up, section y = 15.827 from +y | Pinion above, gear below, one pinion tooth centred in a gear space on the line of centres, visible flank gaps, Ø5 shaft with the D-flat on top, two windows at the bottom | yes |
| `winch_gear3_section_axis.png` | section through the spool axis, x = 0.004 | Motor and pinion section (set-screw hole), spool section (gear slab, drum, flange, hub), shaft, bearings, spacer, cap, magnet, chip, PCB | yes |
| `winch_gear3_section_cap.png` | section through the encoder end | Far bearing, shaft end 0.3 short of the bore floor, 0.75 web, magnet in its pocket (crush rib at -z), chip 1.5 from the magnet face, PCB | yes |
| `winch_gear3_section_tieoff.png` | section at the drum mid-plane y = 28.827 from +y | Gear section with six windows, core R7.5, the chord hole as a vertical strip at x +5.25 (left in this view) open to the surface at both ends, Ø7 bore with the shaft | yes |

Notes on renders: the front, side and top views are labelled (fin clipped); the section planes carry the 0.004 mm residual in the caption (x = 0.004, y = 15.827, 28.827). CLAUDE.md's generic set also lists rear, left, right and bottom views; the spec asks only for front, side, top, iso, mesh and an axis section, which are all present.

## 8. Observations and risks (not failures; for the lead and Jasper)

- **N1 (design risk, MEDIUM).** The bearing stack has zero axial clearance by construction: near bearing face y 5.0, spacer 5.825 + spool 33.175 = 39.000 mm, far bearing face y 44.0 (all faces touching; the Ø7 shaft is free to slide). Any error in the distance between Jasper's two 687 seats becomes axial preload or play. No axial float is designed in; Jasper should size the seats (or one seat depth) for it.
- **N2 (INFO).** Five interfaces are line-to-line in CAD (spool bore, both 687 IDs and the cap bore on the Ø7 shaft; the pinion Ø5 bore on the Ø5 shaft). The spool bore and cap bore are meant to press at about 6.9 printed. A real 687 inner race and dowel tolerance decide the actual fit.
- **N3 (INFO, unverifiable here).** The spacer and the spool far land (both Ø9, 0.3 proud) are meant to touch only the inner race, but the bearings are plain 7 x 14 x 5 rings. `params.py` itself notes "VERIFY race OD about 9" for the 687; if the real inner-race shoulder is below Ø9 the land touches the shield. Check the datasheet.
- **N4 (INFO).** Printability: spacer printed on a land has a 0.5 mm radial step (14.9 mm² at z 0.3); cap web bridges a 7 mm bore (38.5 mm²); spool flange inner face 840.8 mm² needs supports and sanding (as stated); chord hole roof is a 1.4 mm bridge; bed chamfer is exactly at the 45 deg limit.
- **N5 (INFO).** Pinion tooth thinning is 0 (an implementer assumption). Measured backlash is symmetric, 0.249 mm at the pinion pitch circle, 0.062 mm of cable at the drum, so the +0.20 centre-distance allowance plus the gear's 0.10 thinning gives the 0.117 mm flank gap on each side.
- **N6 (PROCESS).** Commit 609aff7 edited the spec (one export bullet, "far flange face down" to "the gear's near face on the bed, section 3"). It agrees with the lead's section 3, but the contract file was changed by the implementer; the lead should confirm.
- **N7 (LOW).** `WG3_FLANGE_T = 3.0` and `WG3_PINION_SETSCREW_D = 3.0` are literals although equal values exist (`SPOOL_FLANGE_THK`, `NEMA17T_TAP_D`); the spec asks to import where a definition exists. No geometric effect. All 65 numeric `WG3_*` values checked equal the spec numbers; `cad/interfaces.py` holds no contract for this station (corner-mount items only), so the spec and `WG3_*` are the interface authority.
- **N8 (INFO).** In the assembly copy the motor shaft D-flat starts at the pilot end (y -1.175); Motor_Reference's flat runs from the front face. No interface is affected (nothing else touches the shaft before y 5.825).
- **N9 (PROCESS).** My test file was committed as `182c1c2` ("WIP: geometry-verifier tests...") by the session environment, not by me; I made no commits.
- Physical items that CAD cannot confirm: real bearing seat tolerances, press-fit force on the printed bore, diametric magnet orientation (modelled as a plain cylinder), cable-path friction at the tie-off exits, and mesh behaviour under load.

## 9. Reproduction

```
cd /home/user/RoomCleaner
/usr/bin/python3 -m pytest -q -s -p no:cacheprovider tests/test_winch_gear3_verify.py    # about 6 min, prints the full 341-row table (test_99_summary)
```
Result of the final run: `26 passed in 343.38s`, `341 recorded checks, 0 FAIL`. No failures, so there is no failure detail to reproduce.
The test file writes nothing into the repository (temporary STEP re-exports go to pytest's tmp path). Exploratory scripts (pose sweep with negative angles, centre-distance control, closest-point location, render review) were run from a scratch directory outside the repository and are described above, not saved.
