# Winch 3:1 spur drive train, revision C (printed PETG pinion 18T, D42): independent geometry verification (geometry-verifier, 10/23)

*Revisions A (20T/60T; 26 tests, 341 checks) and B (18T/54T, steel pinion; 29 tests, 412 checks) passed earlier runs of this verification with 0 failures; this document replaces the revision B report and covers revision C.*

**Contract:** `cad/WINCH_GEAR3_SPEC.md`, "Revision C" note (D42) on top of revision B (D41); the lead's hand-over list for revision C.
**Subject:** `exports/step/winch_gear3_{spool_gear54,spacer_near,magnet_cap,pinion18,drive_asm1021,drive_with_slipin_asm1021,gears_asm1021}.step`, `exports/stl/winch_gear3_{spool_gear54,spacer_near,magnet_cap,pinion18}.stl`, `renders/winch_gear3/*.png`, `cad/params.py` block `WG3_*` (read-only name/value audit).
**Evidence file:** `tests/test_winch_gear3_verify.py` (updated from the revision C spec): **32 tests, 503 recorded checks, 0 FAIL**. Run as three parallel pytest processes (82 s, 107 s, 249 s; about 4 min wall; a single process needs about 8 min).

## Verdict

**PASS: 0 failures.** Nothing goes back to the implementer. Two observations (section 7: flank chamfer on the pinion about 4 % shallower than an exact 0.3 offset; measured backlash 0.428 vs 0.418 analytic) are not failures. The interference list reproduces `verification/winch_gear3_build_notes.md` section C4 to its rounding.

## 0. Method and independence

- Measured the **exported STEP/STL files only** (CadQuery 2.8 / OCP, `/usr/bin/python3`; XCAF reader for named assembly bodies). The implementer's builder `cad/parts/winch_gear3.py` and its tests were not imported or run. Spec numbers are hard-coded in the test file. Repository code loaded: the spec-mandated generator `cad/gripper_v3_fit_review_20261018/gears.py` (to rebuild teeth) and `cad/params.py` (read-only, 72 name/value audit).
- The build notes were opened by the verifier before the run: the lead's hand-over cited their revision C figures, and the interference comparison needs them. The volumes below are measured here; the notes figures are only the comparison column.
- Frames: assembly STEPs are station_1021 + O (1269.08, 738.76, 927.56) plus the 0.004 mm residual; all values below have both removed (position tolerance 0.005). Part STEPs are in the print frame: spool, spacer, cap with the near face on z = 0; **pinion18 with the teeth end (design y 20.825) on z = 0, axis +z**, mapping print (x, y, z) to design (x, 20.825 - z, 2.64 + y).
- The pinion was rebuilt independently from the spec (generator 18T with 0.10 thinning, Ø14 hub to y -0.675, D-bore Ø5.30 flat 2.15, pocket Ø4.0 x 4.5, hole Ø3.0): the exported solid lies entirely inside the rebuild (0.000 mm3 outside); the only difference is the teeth-end chamfer (4.76 mm3).

## 1. Files: validity, solids, names, round trip

| File | Solids / valid | Volume mm3 | Round trip dV / dBBox (tol 1e-3) | STL watertight, dV, dBBox | Status |
|---|---|---|---|---|---|
| `spool_gear54` | 1 / yes | 22 987.903 | 0 / 0 | yes, 0.005 %, 0.0016 mm | PASS |
| `spacer_near` | 1 / yes | 217.918 | 0 / 0 | yes, 0.04 % | PASS |
| `magnet_cap` | 1 / yes | 514.614 | 0 / 0 | yes, 0.04 % | PASS |
| **`pinion18` (print frame)** | 1 solid, 1 shell / yes | 3 701.129 | 0 / 0 | yes, 0.03 %, 0.002 mm | PASS |
| `drive_asm1021`, `drive_with_slipin_asm1021`, `gears_asm1021` | 17 / 19 / 2 bodies, each one valid solid | pinion 3 701.129 in all | worst body < 5e-6 | n/a | PASS |

- Names: the 17 spec names (+ `slipin_mount`, `wall_mount`; gears file `pinion`, `spool_gear54`); none missing, duplicate or stale. `exports/step/winch_gear3_*` is exactly 7 files, `exports/stl/winch_gear3_*` exactly 4 (the pinion STL is new), no `*gear60*` / `*pinion20*` file anywhere. PASS.
- Part files equal assembly bodies by fingerprint (volume, area, centre of mass, inertia, 1e-10 relative): spool, spacer, cap, **and pinion18 turned from its print frame into the design frame**; `gears_asm1021` bodies equal the drive bodies; negative control (spool turned 0.5 deg) is detected. Fin, motor bodies and motor shaft (D-flat 22.481 mm3 removed, flat at z 4.64) unchanged; slide-in and wall mount equal Jasper's SolidWorks assembly parts in place. PASS.

## 2. Revision C pinion (design frame, on the assembly body)

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Hub | Ø14, y -0.675 to 10.825 (11.5 long) | R 7.000; y -0.675 to 10.825 | 0.005 | PASS |
| Total extent | y -0.675 to 20.825 (21.5), 0.5 from the boss face y -1.175 | -0.675 to 20.825 | 0.005 | PASS |
| D-bore | Ø5.30 through, flat 2.15 from the axis on +z | R 2.650, y -0.675 to 20.825; flat plane z = axis + 2.15 (normal -z) over the full length; no flat on -z. Probes: +z material from 2.15, -z, +x, -x from 2.65, in hub and teeth sections | 1e-3 | PASS |
| Fit on the motor shaft | no overlap | round 0.150, flat 2.15 vs 2.0 = 0.150, min distance 0.1500, overlap 0 | 0.002 | PASS |
| Heat-set pocket | Ø4.0 x 4.5 deep, radial from +z, bottom 2.5 from the axis | R 2.000; top 7.0, bottom 2.500 (depth 4.500); flat floor plane at axis + 2.5 facing +z; opens only toward +z (-z wall solid 2.65 to 7.0) | 0.005 | PASS |
| Hole to the bore | Ø3.0, on to the bore | R 1.500, concentric; open from the bore to the outside at x 0 and x 1.0; floor beside it 0.35 (flat 2.15 to 2.5) | - | PASS |
| Set-screw y | about 7.91 (middle of tab face 5.0 and teeth 10.825) | pocket and hole axis y 7.9125 (x 0); pocket spans 5.9125 to 9.9125: 0.9125 from the tab-face plane and from the teeth | 0.02 | PASS |
| Teeth | 18, tip Ø20, root Ø15.5, y 10.825 to 20.825, thinned 0.10 | 18 / 18 tip and root faces; 20.000 / 15.500; tooth thickness on R9 1.4695 (pi/2 - 0.10 = 1.4708) | 0.005 | PASS |
| Tooth form | equals the repo generator, thinning 0.10 | symmetric difference 0.00000 mm3 (zone y 10.9 to 20.45) | 0.01 | PASS |
| Teeth-end chamfer 0.3 x 45 deg at y 20.825 | tip and root radii reduced by 0.3 at the end | tip 9.701 / 9.800 / 9.900 / 10.000 and root 7.451 / 7.550 / 7.650 / 7.750 at 0.001 / 0.1 / 0.2 / 0.3 mm from the end (all +-0.003); end face outline R 9.7 (19.400); hub side of the teeth unchamfered; removed volume 4.76 mm3 (corner-free estimate 5.05) | 0.003 | PASS (see observation O1) |
| Hub volume (O14 x 11.5 - D-bore - pocket - hole) | 1470.59 analytic | 1470.63 | 1.0 | PASS |
| Whole pinion | 4.70 g PETG at 1.27 g/cm3 | 3 701.13 mm3, 4.700 g | info | - |

### pinion18 print frame

Axis +z; bed face one planar face at z 0 (area 191.7 mm2, teeth end, outline reaches R 9.7); z 0 to 21.5; tip Ø20 across the bbox (tooth tip on the print y axis); D-flat toward print +y (material from 2.15 along +y at hub height, round side 2.65 along -y); pocket and hole horizontal toward print +y (bridges over their roofs); no downward planar shelf above the bed. PASS.

## 3. Gear stage and mesh (centre distance 36.30)

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| Centre distance (bore axis to bore axis; also shaft to shaft) | 36.300 = 36.00 + 0.30 | 36.3000 / 36.3000 | 0.001 | PASS |
| Axes | motor (0, 2.64); spool, shaft, bore, bearings, magnet, chip, PCB (0, -33.66) | 0.000 / 2.640; 0.000 / -33.660 | 0.005 | PASS |
| Tip-to-root clearance, both ways | 0.55 | 0.550 / 0.550 | 0.002 | PASS |
| Phasing at the reference pose | gear tooth space and pinion tooth on the line of centres | gear R 25.75, pinion R 10.0 there; neighbours as expected | 0.005 | PASS |
| **Mesh overlap, 7 poses over one pinion pitch (20 deg)** | 0 mm3 | 0.00000 at every pose; negative control (gear turned 1.0 deg alone) 4.18 mm3 | 0.001 | PASS |
| **Flank gap** | > 0 | 0.1997 mm at all 7 poses (min over poses 0.1997) | >= 0.05 | PASS |
| **Backlash** (gear fixed, pinion turned to contact each way) | about 0.42; analytic (2 x 0.30 tan 20 + 0.10 + 0.10) = 0.418 mm at R9 | +1.35 / -1.35 deg, 0.428 mm at the pitch circle, 0.119 mm of cable at the Ø15 drum; asymmetry 0.014 deg | 0.02 mm | PASS (O2) |
| **Gear tip to pinion hub** | >= 1.0 | reference pose 1.4603; worst over one gear pitch 1.3342 = sqrt(1.3^2 + 0.3^2) | 1.0 | PASS |
| Gear to motor bodies | >= 1.5 | front cap 12.000, stator 22.0, winding 22.0, rear cap 44.0, shaft 5.929, connector 46.63 | 1.5 | PASS |
| Gear to fin | >= 1.5 | 10.825 | 1.5 | PASS |

## 4. Pinion clearances (new in revision C)

| Item | Expected | Measured | Status |
|---|---|---|---|
| Pinion hub end to the motor pilot boss face (front cap bbox y max -1.175 confirmed) | axial >= 0.4 | **0.500** | PASS |
| Pinion to front cap / stator / winding / rear cap / connector | >= 0.4 | 0.500 / 14.50 / 11.42 / 32.50 / 37.29 | PASS |
| Pinion to fin: fin motor hole R 11.25 minus hub R 7.0; whole solid distance; overlap | >= 1.5 radial | 4.250; 4.250; 0.000 mm3 | PASS |
| Pinion to slide-in: tab motor hole Ø22.4 (measured 22.400) minus hub R 7.0; distance; overlap | >= 1.5 radial | 4.200; 4.200; 0.000 mm3 | PASS |
| Pinion to wall mount | >= 1.5 | 19.90 | PASS |
| Pinion bore against the motor shaft | no overlap | 0.150 gap, 0.000 mm3 | PASS |

## 5. Everything else (unchanged from revision B, re-measured at the new axis z -33.66)

Spool (windows, rim 3.25, drum, flange, hub, land, Ø7.00 bore, chord hole, 0.3 bed chamfer 14.85 mm3, printability: supports only at the flange inner face 840.8 mm2 and the 11.2 mm2 tie-off roof), spacer (217.918 mm3), shaft Ø7 x 55 (y -3.0 to 52.0), bearings (y 0 to 5, 44 to 49), cap (Ø12 x 6.25, web 0.75, Ø6.3 x 2.5 pocket, 3 ribs), magnet, AS5600 chip and board: all values equal revision B; 0 FAIL. Stack touching at both lands (distance 0.0000). Pairwise overlap of the 17 drive bodies (25 near pairs computed): only `magnet_cap` / `magnet`, **0.4125 mm3 (by design)**; nothing else above 0.01 mm3 (pinion included).
`WG3_*` audit: 72 values equal the revision C numbers (CD 36.30, CD_ALLOW 0.30, bore 5.30, flat 2.15, hub L 11.5, hub y -0.675, boss face -1.175, insert 4.0 x 4.5, set screw 3.0, y 7.9125, motor clearance 0.4, spool axis (0, -33.66)).

## 6. Interference with Jasper's slide-in, wall mount and shell (redesign inputs, not failures; reproduced)

| Mount | Drive body | Measured mm3 | Notes C4 | Status |
|---|---|---|---|---|
| `slipin_mount` | `spool_gear54` | 2463.473 (pieces 2385.28 + 74.18 + 4.02; plate x < -21.15 1233.285, deck block z < -42.4 1143.214, above the deck 86.972) | 2463.5 (1233.3 / 1143.2 / 87.0) | agree |
| `slipin_mount` | `spacer_near` | 13.979 | 14.0 | agree |
| `slipin_mount` | `shaft` | 0; closest 0.0561 | 0; 0.056 | agree |
| `slipin_mount` | `pinion` | 0; closest 4.200 (hub R 7.0 in the tab hole R 11.2) | 0; 4.20 | agree |
| `wall_mount` | `spool_gear54` | 30.950 (2 pieces) | 31.0 (28.4 + 2.5) | agree |
| `Shell_Casing` (info) | `spool_gear54` / `as5600_board` / bearings | 736.187 / 36.594 / 0, 0 | 736.2 / 36.6 / 0 | agree |
| `Spool1011` (being replaced) | `pinion` / `motor_shaft` | 1994.127 / 8.353 | 1994.1 / 8.35 | agree |

Exactly three drive-body pairs interfere with the mounts (spool and spacer with the slide-in, spool with the wall mount); no other drive body, the pinion included, touches the slide-in or wall mount. Not in the notes and not caused by the gears: `Shell_Casing` x `fin` 68.943 mm3 (unchanged since revision A). **No discrepancy** with the notes.

## 7. Observations (not failures)

- **O1 (LOW, geometry).** The pinion's teeth-end chamfer is exactly 0.3 at tooth tips and roots, but on the involute flanks it is about 4 % shallower than a perpendicular 0.3 offset: cross-section area at 0.05 / 0.1 / 0.2 mm from the end is 1.23 / 1.06 / 0.65 mm2 larger than the exact offset (mean 11 / 10 / 6 um over the 112 mm outline; the spool's chamfer matches an exact offset to 0.003 mm2). Irrelevant for FDM; recorded for the SolidWorks handoff.
- **O2 (INFO).** Measured backlash 0.428 mm at the pinion pitch circle (build notes 0.423, analytic 0.418); all agree with "about 0.42" within bisection resolution; 0.119 mm of cable at the drum.
- **O3 (INFO, consistent with notes C5.1).** `calculations/winch_gear3.py` is the implementer's/checker's file and was not examined here; the notes say its backlash formula subtracts the pinion thinning (0.218 mm), which would be wrong against the measured 0.428 mm.
- **O4 (INFO).** The worst-pose gear-to-hub distance is 1.334 mm (tip on the line of centres, 0.3 chamfer adds the axial part), 0.12 mm less than the reference pose 1.460 mm; margin to the 1.0 criterion 0.33 mm.
- **O5 (INFO).** The shaft clears the slide-in by only 0.056 mm (0.127 mm in revision B); not a design clearance, the cheeks are being redesigned. Pocket and hole are modelled without insert or screw; the floor between pocket and bore flat is 0.35 mm; the Ø3.0 hole leaves a 0.05 mm sliver of flat each side (notes C3).
- **O6 (INFO).** Revision B observations N2 to N4 (zero axial float in the bearing stack, line-to-line CAD fits, Ø9 lands versus the real 687 inner ring) still apply unchanged.

## 8. Renders (each opened and looked at; timestamps 16:03, after the 16:02 STEP files)

| Render | Shows | Matches name |
|---|---|---|
| `front` | from +x, +y right: motor, fin plate, purple printed pinion with its long hub toward the fin and 18T teeth over the 54T gear, drum, flange, bearings, cap, board | yes |
| `side` | end view from +y: 18T pinion with the D-bore (flat on top, +z) over the 54T gear with six windows; board, flange | yes |
| `top` | from +z: set-screw pocket visible as a circle on the pinion hub; drum tie-off hole | yes |
| `iso` | whole drive, hub through the fin hole, pinion meshing with the gear | yes |
| `mesh` | section y = 15.827: pinion tooth centred in a gear space, D-bore with the flat on top and the O5 shaft inside, flank gaps visible | yes |
| `section_axis` | section through the spool axis: pinion hub on the motor shaft with the radial pocket/hole at the top, spool, shaft, bearings, cap, magnet, chip | yes |
| `section_cap` | encoder end: bearing, shaft 0.3 short of the floor, web, magnet with crush rib, chip, PCB | yes |
| `section_tieoff` | drum mid-plane: six windows, core, chord hole at x +5.25 | yes |

Exactly the 8 expected files; the rear, left, right and bottom views of the generic CLAUDE.md set are not part of this spec's list.

## 9. Reproduction

```
cd /home/user/RoomCleaner
/usr/bin/python3 -m pytest -q -s -p no:cacheprovider tests/test_winch_gear3_verify.py     # about 8 min in one process; prints the table in test_99_summary
# or in three parts (about 4 min): -k "test_01 or test_02 or test_03 or test_04", -k "test_05 or test_06 or test_07 or test_08", -k "test_09 or test_1 or test_20 or test_21"
```
Final result: 12 + 5 + 17 passed (the summary test runs in each part), 121 + 52 + 330 = 503 recorded checks, 0 FAIL. Two earlier runs of this update failed on my own test errors, both fixed in the test file: (a) a boolean-noise measure (0.066 mm3 from a common of coincident surfaces) replaced by a cut volume (0.000 mm3); (b) a corner-free chamfer volume estimate that is 5 % too high for an 18T outline, replaced by exact cross-section areas against the inset outline (observation O1). No part failure was found.
The test file writes nothing into the repository.
