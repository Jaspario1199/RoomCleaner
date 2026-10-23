# Winch 3:1 spur drive train, revision B (18T/54T, D41): independent geometry verification (geometry-verifier, 10/23)

*Revision A (20T/60T) passed an earlier run of this verification (26 tests, 341 checks, 0 failures); this document replaces that report and covers revision B only.*

**Contract:** `cad/WINCH_GEAR3_SPEC.md` revision B, sections 2 to 5 (section 7 changed only in its quoted numbers during this work; sections 2 to 5 are unchanged since the start).
**Subject:** `exports/step/winch_gear3_{spool_gear54,spacer_near,magnet_cap,pinion18,drive_asm1021,drive_with_slipin_asm1021,gears_asm1021}.step`, `exports/stl/winch_gear3_{spool_gear54,spacer_near,magnet_cap}.stl`, `renders/winch_gear3/*.png`, `cad/params.py` block `WG3_*` (read-only audit).
**Evidence file:** `tests/test_winch_gear3_verify.py` (rewritten from the revision B spec): **29 tests, 412 recorded checks, 0 FAIL**, 6 min 54 s.

## Verdict

**PASS: 0 failures.** Nothing needs to go back to the implementer.
The interference list against Jasper's slide-in, wall mount and shell reproduces the build notes (section 5 of `verification/winch_gear3_build_notes.md`) to the notes' rounding (0.1 mm3); no discrepancy.
Observations that matter for Jasper's design are in section 8: the gear-to-pinion-hub clearance is **1.237 mm at its worst pose** (not the 1.364 mm of the reference pose), the shaft clears the slide-in by only 0.127 mm, and the bearing stack still has zero axial float.

## 0. Method and independence

- Measured the **exported STEP/STL files only**, with fresh code: CadQuery 2.8.0 / OCP under `/usr/bin/python3`; XCAF reader for assembly names and placements. `cad/parts/winch_gear3.py` and the implementer's tests were **not imported or run**. The spec numbers (18/54 teeth, tip O20/O56, root R 7.75 / 25.75, centre distance 36.20, spool axis z -33.56, windows O10 on R17.5, every unchanged axial position) are hard-coded in the test file from the spec text.
- Repository code loaded: the spec-mandated generator `cad/gripper_v3_fit_review_20261018/gears.py` (to rebuild the teeth independently) and, read-only, `cad/params.py` (parameter audit, 64 values).
- The build notes were opened only after the first full measurement run, to compare the interference list. The grep used for that also showed the notes' mesh figure (0.1168 mm), masses and volumes; those were not used as pass criteria and agree with the independent measurements.
- **Frames.** Assembly STEPs are station_1021 + O, O = (1269.08, 738.76, 927.56), plus the deliberate 0.004 mm extraction residual (+0.004243, +0.001645, +0.003854). All assembly values below are in the spec design frame (O + residual removed); position tolerance 0.005 mm. Part STEP/STL files are in the print frame (axis +z, gear near face on z = 0; design y = z + 10.825 for `spool_gear54`). The standalone `pinion18.step` has its axis on z with z = design y (hub z 5.825 to 10.825, teeth 10.825 to 20.825), centred on x = y = 0.
- **Offset O is independently confirmed**: the slide-in and wall mount in `_with_slipin_asm1021` equal the same parts of Jasper's `solidworks/v4_assembly_2026-10-21/Assem_laundry_v3_step_1021.STEP` in absolute coordinates (volume 217 693.1525 / 596 918.86 mm3, bbox difference < 1e-3 mm, fingerprint difference 7e-11 / 1e-8 relative).
- **Independent rebuild of the spool** from spec section 3 (generator 54T gear with the measured phase, six O10 windows on R17.5, drum, flange, hub, land, O7 bore, chord hole): the exported solid lies entirely inside it (0.00000 mm3 outside); the only difference is the 0.3 mm bed-face chamfer (14.85 mm3; perimeter 332.11 x 0.3 x 0.3 / 2 = 14.95).
- Part-to-assembly identity uses a fingerprint (volume, surface area, centre of mass, inertia matrix about the origin): agreement is 1e-10 relative; a 0.5 deg rotation of the spool alone gives 3e-5 mm and 9e-7 relative, so the limits (1e-5 mm, 1e-7) detect it (negative control PASS). Symmetric-difference booleans are kept for the spacer and cap.
- Other negative controls: gear turned 0.5 deg alone gives 1.34 mm3 mesh overlap, so the overlap test can fail.

## 1. STEP/STL files: validity, solids, names, round trip

| File | Solids | Valid BREP | Volume mm3 | BBox | Round trip dV / dBBox (tol 1e-3) | STL watertight, dV vs STEP | Status |
|---|---|---|---|---|---|---|---|
| `spool_gear54` (print frame) | 1 (1 shell) | yes | 22 987.903 | x +-28.0000, y +-27.9702, z 0 to 33.175 | < 5e-6 / < 5e-6 | yes (56 862 triangles), 0.005 % (tol 0.1 %) | PASS |
| `spacer_near` | 1 | yes | 217.918 | x,y +-5.0, z 0 to 5.825 | 0 / 0 | yes, 0.041 % | PASS |
| `magnet_cap` | 1 | yes | 514.614 | x,y +-6.0, z 0 to 6.25 | 0 / 0 | yes, 0.042 % | PASS |
| `pinion18` (axis z, design y) | 1 | yes | 2 928.064 | x +-9.9015, y +-10.0, z 5.825 to 20.825 | 0 / 0 | no STL in the spec | PASS |
| `drive_asm1021` | 17 bodies, 17 solids | all 17 valid, one shell each | total 117 996.44 | x -28.00 to 28.00, y -41.17 to 60.10, z -61.53 to 210.24 (tall fin) | worst body < 5e-6; total < 5e-6 | n/a | PASS |
| `drive_with_slipin_asm1021` | 19 bodies, 19 solids | all valid | total 932 608.45 | x -42.32 to 28.00, y -94.44 to 125.56, z -68.61 to 210.24 | same | n/a | PASS |
| `gears_asm1021` | 2 bodies (`pinion`, `spool_gear54`) | valid | total 25 915.97 | x +-28.0, y 5.82 to 44.0, z -61.53 to 12.64 | same | n/a | PASS |

- All STEP files declare millimetres. STL bbox vs STEP bbox difference <= 0.002 mm.
- **Named bodies**, expected = spec section 5 list; measured: `motor_front_cap, motor_stator, motor_winding, motor_rear_cap, motor_shaft, motor_connector, fin, pinion, spool_gear54, shaft, bearing_near, bearing_far, spacer_near, magnet_cap, magnet, as5600_chip, as5600_board` (17); the with-slip-in file adds `slipin_mount`, `wall_mount`; the gears file holds `pinion`, `spool_gear54` (names inferred from the other assemblies; the spec lists no gears file). No missing, extra, duplicate or stale (`spool_gear60`, `pinion20`) names. **PASS**.
- **Stale revision A files are gone**: no file named `*gear60*` or `*pinion20*` anywhere in the repository (git index and working tree); `exports/step/winch_gear3_*` is exactly the 7 files above, `exports/stl/winch_gear3_*` exactly the 3 above, `renders/winch_gear3/` exactly the 8 expected PNGs, none older than the regenerated STEP. **PASS**.
- Every body is exactly one solid with one shell, V > 0 (no disconnected pieces). **PASS**.
- Part files equal the assembly bodies: fingerprint agreement 1e-10 or better for the spool, spacer, cap and the standalone pinion; symmetric difference 0.00000 mm3 for spacer and cap. **The standalone `pinion18` equals the assembly pinion** (volume 2928.0637 both). `gears_asm1021` bodies equal the `drive_asm1021` bodies exactly. **PASS**.
- `fin` equals `heat_fin1021_1p8_asm1021.step` (V 26 905.8243, bbox difference 0). Motor front cap, stator, winding, rear cap and connector equal the `nema17_thermal_fin1p8_asm1021.step` bodies. `motor_shaft` differs by the D-flat only: removed 22.481 mm3 = circular segment (R 2.5, depth 0.5) x 22 mm; flat plane at z = 4.64. **PASS**.

## 2. Gear stage

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Gear teeth (disjoint sections at the pitch ring R27) | 54 | 54 (54 tip faces, 54 root faces) | exact | PASS |
| Pinion teeth (pitch ring R9) | 18 | 18 (18 tip, 18 root faces) | exact | PASS |
| Ratio | 3.000 | 3.000 | 1e-9 | PASS |
| Gear tip / root diameter | 56 / 51.5 (R 28.0 / 25.75) | 56.000 / 51.500 | 0.005 | PASS |
| Pinion tip / root diameter | 20 / 15.5 (R 10.0 / 7.75, generator root m (z/2 - 1.25)) | 20.000 / 15.500 | 0.005 | PASS |
| Centre distance, bore axis to bore axis | 36.200 (nominal 36.00 + 0.20) | 36.2000; minus nominal 0.2000 | 0.001 | PASS |
| Pinion axis / motor shaft axis (x, z) | (0, 2.64) | (0.0000, 2.6400) both | 0.005 | PASS |
| Spool axis, bore and shaft (x, z) | (0, -33.56) | (0.0000, -33.5600) | 0.005 | PASS |
| Pinion teeth y range / width | 10.825 to 20.825 / 10 | 10.825 to 20.825 / 10.000 | 0.005 | PASS |
| Gear teeth y range | 10.825 (bed face) to 20.825 | 10.825 to 20.825 (tip faces start at 11.125: the 0.3 chamfer) | 0.005 | PASS |
| Tooth form (module 1, 20 deg, thinning 0.10 gear / 0 pinion, root blend 0.4) | equals the repo generator | symmetric difference with the generator rebuilt independently: 0.00000 mm3 (gear), 0.00000 mm3 (pinion) | 0.01 mm3 | PASS |
| Tooth pitch | 6.6667 deg / 20.0 deg | 6.6667 / 20.0000 (all tip-face centres uniform within 1e-6 deg) | 1e-6 | PASS |
| Tooth thickness at the pitch circle | gear pi/2 - 0.10 = 1.4708; pinion pi/2 = 1.5708 | 1.4704; 1.5695 (ring-averaged) | 0.005 | PASS |
| **Phasing** at the reference pose | gear tooth SPACE and pinion tooth on the line of centres | gear radius there 25.750 (root); pinion radius 10.000 (tip); neighbours +-3.333 deg on the gear: tip R 28.000; neighbours +-10 deg on the pinion: root R 7.750 | 0.005 | PASS |
| **Mesh overlap**, 7 poses 0 to 20 deg (one pinion pitch; pinion +theta, gear -theta/3) | 0 mm3 | 0.00000 mm3 at every pose | 0.001 | PASS |
| **Minimum flank-to-flank distance** per pose (0, 3.33, 6.67, 10, 13.33, 16.67, 20 deg) | > 0 | 0.1168 mm at every pose | >= 0.05 | PASS |
| Tip-to-root clearance, both ways | 0.45 (36.20 - 28.0 - 7.75 and 36.20 - 10.0 - 25.75) | 0.450 / 0.450 | 0.002 | PASS |
| **Backlash**, free pinion rotation with the gear fixed (contact bisection) | analytic (2 x 0.20 tan 20 + 0.10) / 9 = 0.2456 mm / R9 = 1.563 deg | +0.792 / -0.792 deg, 1.584 deg total = 0.249 mm at the pinion pitch circle = 0.528 deg and 0.069 mm of cable at the drum (R7.5) | 0.06 deg | PASS |

Phase detail: tooth centres sit at multiples of 6.6667 deg in the print frame (a tooth tip on the print x axis), the line of centres is print 270 deg (station +z), which falls on a tooth space (270 / 6.6667 = 40.5). The pinion has a tooth tip on the line of centres (standalone bbox y +-10.0, x +-9.9015).

## 3. `spool_gear54` (print frame, z = y_design - 10.825)

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Part extent | y 10.825 to 44.0 (z 0 to 33.175) | z 0.000 to 33.175 | 1e-6 | PASS |
| Six windows: Ø, pitch radius | O10 (R5.0) on R17.5 | 6 faces R 5.000, axis radius 17.500 (+-1e-4), 60.00 deg apart (first at 0 deg), z 0 to 10 | 1e-4 | PASS |
| Window outer / inner edge | R22.5 / R12.5 | 22.500 / 12.500 | 1e-4 | PASS |
| **Rim below the root** | >= 3.0 (3.25) | 3.250 (root R25.75 minus 22.5) | - | PASS |
| **Window inner edge** | >= 12 (2.5 outside the 10 mm full-spool line radius) | 12.500 (2.500 outside R10) | - | PASS |
| Web window to drum core | >= 2 | 5.000 | - | PASS |
| Radial section at z = 5 along the six window axes | material [3.5, 12.5] [22.5, 28.0] (window axes fall on tooth centres) | as expected at 0, 60 .. 300 deg | 1e-3 | PASS |
| Radial section along the six spokes (30 .. 330 deg incl. the line of centres at 270 deg) | solid [3.5, 25.75] (tooth spaces) | as expected | 1e-3 | PASS |
| Gear z range | 0 to 10 | 0 to 10; 54 tip faces end at z 10.0 | 1e-4 | PASS |
| Drum | O15, y 20.825 to 36.825 | R 7.500, z 10.0 to 26.0 | 1e-3 | PASS |
| Outer flange | O36 x 3, y 36.825 to 39.825 | R 18.000, z 26.0 to 29.0; inner face annulus 841.16 mm2 (overhang 10.5) | 1e-3 | PASS |
| Far hub | O12, y 39.825 to 44.0 | R 6.000, z 29.0 to 32.875 | 1e-3 | PASS |
| O9 land, 0.3 proud | R4.5, 0.3 | R 4.500, z 32.875 to 33.175 (0.300) | 1e-3 | PASS |
| Bore | O7.00 through | one face R 3.500, z 0 to 33.175, coaxial | 1e-3 | PASS |
| Tie-off hole | O1.4, 5.25 off axis (+x), y 28.825 (z 18.0), perpendicular | R 0.7000, x 5.2500, z 18.000, direction perpendicular | 1e-4 | PASS |
| Ligament to bore / to core surface | 1.05 / 1.55 | 1.050 / 1.550 | 0.002 | PASS |
| Hole open on the winding surface, both ends | open | no material along the hole axis; at y = +5.3 and -5.3 the section is [0, 4.55] only | - | PASS |
| Hole side as Spool1011 | +x, along station z | Spool1011 hole at x +6.0 along z: same side and direction | - | PASS |
| Bed-face chamfer 0.3 x 45 deg on the tooth edges | 0.3 | tooth tip radius 27.701 / 27.800 / 27.900 / 28.000 at z 0.001 / 0.1 / 0.2 / 0.3; root 25.451 / 25.550 / 25.650 / 25.750 (all +-0.003); window and bore edges at the bed face not chamfered (3.5, 12.5, 22.5 unchanged); removed volume 14.85 mm3 | 0.003 / 0.4 mm3 | PASS |
| Volume | rebuild minus chamfer | 22 987.903 mm3 (29.2 g PETG at 1.27 g/cm3, solid) | 0.01 | PASS |

**Printability on the gear's near face (z 0 on the bed):** bed contact 1658.6 mm2 (one planar face). Overhangs steeper than 45 deg (STL): only the **flange inner face z 26.0, 840.8 mm2** (annulus R7.5 to R18, overhang 10.5 mm: supports, as the spec expects) and the **tie-off hole roof, 11.2 mm2** (horizontal O1.4 hole). The 0.3 mm bed chamfer sits at exactly 45 deg. Windows, bore, drum, hub and land are vertical or upward-facing: no supports.

## 4. Spacer, shaft, bearings, magnet cap, magnet, AS5600, pinion (all unchanged axial positions; only the axis z moved)

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Spacer length / OD / bore | y 5.0 to 10.825 (5.825) / O10 / O7.10 | 5.825 / 10.000 / 7.100 | 1e-4 | PASS |
| Spacer lands | O9 at both ends, 0.3 proud | R 4.5 lands at z 0 to 0.3 and 5.525 to 5.825 | 1e-4 | PASS |
| Spacer volume | analytic pi(25 x 5.225 + 20.25 x 0.6 - 12.6025 x 5.825) | 217.918 (217.918) | 0.01 | PASS |
| Spacer in the assembly | y 5.0 to 10.825, axis z -33.56 | 5.000 to 10.825; -33.560 | 0.005 | PASS |
| Shaft | O7 x 55, y -3.0 to 52.0, axis (0, -33.56) | O7.000, y -3.000 to 52.000, axis (0.000, -33.560) | 0.005 | PASS |
| Bearing near / far | 687, 7 x 14 x 5, y 0 to 5 / 44 to 49 | R 3.5 / R 7.0, width 5.000, y 0.000 / 44.000, axis (0, -33.56) | 0.005 | PASS |
| Stack | near bearing face 5.0, spacer + spool = 39.000, far bearing face 44.0 | touching at both lands (distance 0.0000) | 1e-4 | PASS |
| Cap Ø / thickness | O12 / 6.25 (y 49.3 to 55.55) | 12.000 / 6.250; y 49.300 to 55.550 | 1e-4 | PASS |
| Cap bore, web, pocket | O7 x 3.0 deep; 0.75; O6.3 x 2.5 (floor y 53.05) | R 3.500, 3.000; 0.750 (z 3.0 to 3.75 on the axis); R 3.150, 2.500; shaft end 52.0 leaves 0.300 | 1e-4 | PASS |
| Crush ribs | 3, 0.15 per side + 0.12 crush | at 90, 210, 330 deg; tip R 2.880 (protrusion 0.270); width 0.463 at R2.9 (tip 0.45) | 0.002 | PASS |
| Cap to far bearing | 0.3 | 0.300 | 1e-3 | PASS |
| Magnet | O6 x 2.5, y 53.05 to 55.55 | O6.000 x 2.500, y 53.050 to 55.550, axis z -33.56 | 0.005 | PASS |
| AS5600 chip | face y 57.05, 1.45 tall, 6 x 4, centred | face 57.050, air gap 1.500, height 1.450, 6.000 x 4.000, centred | 0.005 | PASS |
| AS5600 PCB | 23 x 23 x 1.6 at y 58.5 to 60.1, centred | 23.000 x 23.000, y 58.500 to 60.100, centre (0.000, -33.560) | 0.005 | PASS |
| Pinion hub / bore | O14 x 5 (y 5.825 to 10.825) / O5 through | R 7.000, 5.825 to 10.825 (0.825 clear of the tab face y 5.0) / R 2.500, y 5.825 to 20.825 | 0.005 | PASS |
| Pinion set-screw hole | O3.0 radial toward the D-flat (+z), hub mid-plane | one R 1.5 hole, direction z, y 8.325; open on +z, wall intact on -z | 0.005 | PASS |
| Pinion volume / mass | independent estimate (generator rim + hub - bore - set screw) 2928.62 | 2928.064 (diff 0.55); 22.985 g steel at 7.85 | 3.0 | PASS |

Contacts (distance 0.0000 mm, all PASS): motor front cap/fin, spacer/spool, spacer/near bearing, spool/far bearing, magnet/cap, chip/PCB, shaft with spool, both bearings and cap, pinion/motor shaft, motor shaft/front cap.
Radial fits, bore R minus shaft R (CAD nominal): spool 0.000, both bearings 0.000, cap 0.000, spacer +0.050 (7.10 slip), pinion bore on the O5 motor shaft 0.000.

## 5. Clearances and overlaps inside the drive

| Item | Expected | Measured | Status |
|---|---|---|---|
| Overlap of any two of the 17 drive bodies (24 pairs with overlapping bounding boxes examined, all computed; 136 pairs in total) | <= 0.01 mm3 except cap ribs into the magnet | only `magnet_cap` / `magnet`: **0.4125 mm3** (by design). All others 0.000000 | PASS |
| **Gear tip to pinion hub, reference pose** (gear space on the line of centres) | >= 1.0 mm (revision B) | **1.3637 mm** (closest points: gear tooth tip corner at y 11.125, hub top edge at y 10.825) | PASS |
| **Gear tip to pinion hub, worst pose over one gear pitch of spool rotation** (0 / 1.67 / 3.33 / 5.0 deg) | >= 1.0 mm; geometric bound sqrt((36.20 - 28.0 - 7.0)^2 + 0.3^2) = 1.2369 | 1.3637 / 1.2543 / **1.2370** / 1.2543 mm | PASS |
| `spool_gear54` to `motor_front_cap` / `stator` / `winding` / `rear_cap` / `shaft` / `connector` | >= 1.5 mm | 12.000 / 22.000 / 22.000 / 44.000 / 5.830 / 46.616 mm | PASS |
| `spool_gear54` to `fin` | >= 1.5 mm | 10.825 mm | PASS |
| Pinion to fin; pinion hub to tab face | info | 7.211 mm; 0.825 mm | PASS |

## 6. Interference with Jasper's current slide-in, wall mount and shell (redesign inputs, not failures; compared with the build notes)

All 17 drive bodies against `slipin_mount` and `wall_mount` (25 pairs with overlapping bounding boxes, boolean common, design-frame coordinates):

| Mount | Drive body | Measured mm3 | Build notes | Location / detail |
|---|---|---|---|---|
| `slipin_mount` | `spool_gear54` | **2451.584** | 2451.6 | three pieces (2375.25, 72.31, 4.02); by region: back plate x < -21.15: 1233.29 (notes 1233.3), deck block z < -42.4: 1133.19 (1133.2, all under the gear face y 10.825 to 20.825), above the deck top: 85.11 (85.1 = 72.3 drum through the far cheek wall y 23.56 to 25.56, x -7.50 to 2.08, z -41.06 to -31.48, plus 12.8 gear teeth); overall x -28.00 to 13.85, y 10.82 to 25.56, z -52.38 to -15.30 |
| `slipin_mount` | `spacer_near` | **12.995** | 13.0 | x -5.00 to -0.13, y 5.56 to 7.56, z -38.56 to -33.69 (near cheek only) |
| `slipin_mount` | `shaft` | **0** | 0 (closest 0.127) | no overlap; closest approach 0.1269 mm (revision A: 54.8 mm3 at the old axis) |
| `wall_mount` | `spool_gear54` | **27.291** (2 pieces) | 27.3 | 25.834 (x -14.29 to -8.48, y 10.82 to 20.83, z -59.40 to -55.91; notes 25.8) + 1.457 (x -16.87 to -15.92, z -56.22 to -55.91; notes 1.5) |

No other drive body overlaps the slide-in or the wall mount (`pinion`, all `motor_*`, `shaft`, both bearings, cap, magnet, chip, board: 0.000 mm3). Nearest non-overlapping: slide-in to `shaft` 0.127 mm, to `bearing_near` 0.56 mm, to `pinion` 4.28 mm.
Informative, from the original SolidWorks assembly: `Shell_Casing` x `spool_gear54` **730.418** (notes 730.4), x `as5600_board` **32.914** (32.9), x bearings **0 / 0** (notes 0); `Spool1011` (the part being replaced) x `pinion` 2012.939 (2012.9), x `motor_shaft` 8.353 (8.4). Shell distance to the magnet cap 4.61 mm, spacer 5.61 mm, near/far bearing 3.61 mm. **All reproduced; the notes miss no overlap that involves a drive body.**
**Not in the notes** (pre-existing, not caused by the gears): `Shell_Casing` x `fin` = **68.943 mm3** (x -20.0 to 22.0, y -3.17 to -2.69, z 27.8 to 31.3): the 1/8 in fin is 1.175 mm thicker than the Heat_horn it replaces. Unchanged from the revision A verification.

## 7. Renders (each opened and looked at)

| Render | Caption / name | What it shows | Matches its name |
|---|---|---|---|
| `winch_gear3_front.png` | front, from +x, +y right | Motor (left), clipped fin plate, pinion hub and 18T pinion over the 54T gear, drum with two tie-off hole openings, flange, hub, far bearing, cap, chip and board; near shaft end, near bearing and the blue spacer at left. Pinion and gear heights are consistent with O20 / O56 at CD 36.20 | yes |
| `winch_gear3_side.png` | side, end view from +y, +x left | Fin and motor face behind, 18T pinion with the shaft end, the 54T gear with six windows (two at the sides, spokes top and bottom), the shaft end, flange (faceted circle), the 23 x 23 board in front, motor connector at the left | yes |
| `winch_gear3_top.png` | top, from +z, +y left | Same stack from above; set-screw hole visible on the pinion hub, the see-through tie-off hole on the drum | yes |
| `winch_gear3_iso.png` | iso from +x, +y, +z | Whole drive: motor and fin, 18T pinion engaging the 54T gear, windows, drum, flange, far bearing, cap, board | yes |
| `winch_gear3_mesh.png` | mesh close-up, section y = 15.827 from +y | 18T pinion above, 54T gear below; one pinion tooth centred in a gear space on the line of centres, visible flank gaps, O5 shaft with the D-flat on top, two windows at the bottom | yes |
| `winch_gear3_section_axis.png` | section through the spool axis, x = 0.004 | Motor and pinion section (set-screw hole in the hub), spool section (gear slab, drum, flange, hub), shaft, bearings, spacer, cap, magnet, chip, PCB | yes |
| `winch_gear3_section_cap.png` | section through the encoder end | Far bearing, shaft end 0.3 short of the bore floor, 0.75 web, magnet in its pocket (crush rib at -z), chip 1.5 from the magnet face, PCB | yes |
| `winch_gear3_section_tieoff.png` | section at the drum mid-plane y = 28.827 from +y | 54T gear section with six windows, core R7.5, the chord hole as a vertical strip at x +5.25 (left in this view), open to the surface at both ends, O7 bore with the shaft | yes |

No render shows 20T/60T geometry or captions. CLAUDE.md's generic set also lists rear, left, right and bottom views; the spec asks only for front, side, top, iso, mesh and an axis section (plus the two extra sections), which are all present.

## 8. Observations and risks (not failures)

- **N1 (design, LOW, new in revision B).** The tightest gear-to-pinion-hub distance occurs when a gear tooth tip passes the line of centres: **1.237 mm** (sqrt(1.2^2 + 0.3^2), the 0.3 mm chamfer adds the axial part), not the 1.364 mm of the phased reference pose. The spec's 1.2 mm (36.20 - 28.0 - 7.0) is the exact radial lower bound. It passes the revision B criterion (>= 1.0) with 0.24 mm margin; the 0.2 mm axial end play does not reduce it (the hub ends at the gear's face plane).
- **N2 (design, MEDIUM, unchanged).** The bearing stack has zero axial clearance by construction: near bearing face y 5.0, spacer 5.825 + spool 33.175 = 39.000 mm, far bearing face y 44.0. Any error in Jasper's seat spacing becomes preload or play (the spec section 7 asks for 49.2 mm shoulder spacing).
- **N3 (INFO).** Five interfaces are line-to-line in CAD (spool bore, both 687 IDs, cap bore on the O7 shaft; pinion O5 bore on the O5 shaft). A real 687 inner race and dowel tolerance decide the actual fit.
- **N4 (INFO, unverifiable here).** The spacer and the spool far land (O9, 0.3 proud) are meant to touch only the inner race; if the real 687 inner-ring shoulder is under O9 they touch the shield (`params.py` itself notes "VERIFY race OD about 9").
- **N5 (INFO).** Backlash is symmetric (+-0.792 deg), 0.249 mm transverse at the pinion pitch circle, 0.069 mm of cable at the drum. The 0.1168 mm flank gap is the same at all 7 poses (revision A: 0.1166 to 0.1167). Pinion tooth thinning 0 is the implementer's assumption (spec gives thinning for the gear only).
- **N6 (INFO).** The shaft now clears the slide-in by 0.127 mm only; that is not a design clearance (the cheeks are being redesigned). The slide-in/spacer overlap (13.0 mm3) is the near cheek.
- **N7 (DOCS, LOW).** Stale revision A text outside the geometry: `cad/WINCH_GEAR3_SPEC.md` line 11 still says "printed 60-tooth gear" (intro paragraph) and section 7 quotes "26 tests" for the verification (now 29 tests); `DESIGN_STATE.md` lines 625 and 643-644 still name `spool_gear60` and `pinion20`.
- **N8 (PROCESS).** `winch_gear3_gears_asm1021.step` and `winch_gear3_pinion18.step` are not in the spec's section 5 deliverable list (the implementer added them after the spec); verified here as requested (valid, named, identical to the drive assembly bodies). Recommend adding them to the spec.
- **N9 (PROCESS).** The session environment committed this verifier's work-in-progress test file as WIP commits (from `b7f337b` on); the verifier made no commits.
- **N10 (INFO).** The test file runs in about 7 minutes (413 s), the longest items being the shell/mount booleans (85 s) and the hub sweep (57 s). Identity checks use a fingerprint instead of a boolean on the 54T spool to stay under the 10 minute limit.
- Physical items that CAD cannot confirm: real bearing seat tolerances, press-fit force on the printed bore, diametric magnet orientation (modelled as a plain cylinder), cable-path friction at the tie-off exits, and mesh behaviour under load.

## 9. Reproduction

```
cd /home/user/RoomCleaner
/usr/bin/python3 -m pytest -q -s -p no:cacheprovider tests/test_winch_gear3_verify.py    # about 7 min, prints the 412-row table (test_99_summary)
```
Result of the final run: `29 passed in 413.74s`, `412 recorded checks, 0 FAIL`. No failures, so there is no failure detail to reproduce.
History of this revision's runs: the first full run had one failing check, a stale revision A figure in my own test (pinion mass hard-coded for the 20T pinion: expected 27.64 g, measured 22.985 g for the 18T pinion); it was a test error, not a part error, and was replaced by an independent volume estimate. A second run had one failing check from an over-tight absolute tolerance on the 6e5 mm3 wall-mount fingerprint (dV 5.7e-3 mm3, 1e-8 relative; the same 0.006 mm3 noise as the revision A symmetric difference); the tolerance is now relative.
The test file writes nothing into the repository (temporary STEP re-exports go to pytest's tmp path).
