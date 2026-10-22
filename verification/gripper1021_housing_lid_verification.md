# Independent verification: Gripper 1021 housing lid (press-fit)

Verifier: geometry-verifier (Sonnet), 2026-10-22. Nothing in the repository was repaired, edited or committed; the only files written are this report and
`tests/test_gripper1021_housing_lid_verification.py`.

- Part under test: `exports/step/gripper1021_housing_lid.step` and `exports/stl/gripper1021_housing_lid.stl` (the files on disk, not a rebuild).
- Fit partners: `exports/step/gripper1021_housing_cambay_34.step` (recess, seat, bores), `exports/step/gripper1021_housing_cambay_cover.step`.
- Claims checked: `verification/gripper1021_housing_lid_build_notes.md`. The implementer's builder, tests and measurement helpers are NOT used for any decision. The only exception
  is `test_07b` (stale-export check), which rebuilds with the builder on purpose.
- Run: `/usr/bin/python3 -m pytest tests/test_gripper1021_housing_lid_verification.py -s -q -rxX` (about 2.5 min). Frame: bay frame = world minus `CAMBAY1021_BAY_ORIGIN_WORLD`, +y up.
- Method: exact line/solid intersections (OCC `IntCurvesFace`), booleans, `BRepExtrema` distances, exact bounding boxes (`BRepBndLib.AddOptimal`), STL parsed by hand
  (edge manifold test, normals, slice raster with opening/closing morphology; the detector is self-checked on synthetic 0.30 mm wall/gap vs 0.60 mm wall).

## 1. Verdict

**Geometry: PASS.** **Print verdict: PASS WITH CONDITIONS.** 20 tests pass, 1 strict xfail documents finding F1 (below). No measurement contradicts a build-notes claim.

Conditions for printing: (C1) compensate first-layer elephant foot at the bump tips or add a chamfer to the bump top edge (F1); (C2) control warp and check flatness before fitting
(F4); (C3) keep the strip under the notch empty inside the housing (F3).

## 2. Expected vs measured

| # | Item | Expected | Measured | Tol | Result |
|---|---|---|---|---|---|
| 1 | Solids / validity | 1, valid | 1, valid | exact | PASS |
| 1 | Volume | 12391 mm3 (claim); analytic 12390.6 | 12391.38 mm3 (15.74 g PETG 1.27) | 0.2 % | PASS |
| 1 | Bbox (bay) | x, z +-42.65 (85.3), y 50.0 .. 51.8 | x, z -42.650 .. 42.650, y 50.000 .. 51.800 | 0.01 | PASS |
| 2 | Recess walls | 85 x 85, centred | 42.49997 / 42.50003 / 42.5 / 42.5 from the tube axis (centred to 3e-5) | 2e-3 | PASS |
| 2 | Recess corners | R12.5 about (+-30, +-30) | max deviation 3e-5 mm (8 angles x 4 corners) | 2e-3 | PASS |
| 2 | Seat / rim heights | y 50 / 55 | 50.00001 / 55.00001 | 1e-3 | PASS |
| 2 | Seat ring | 2.5 wide around 80 x 80 pocket (R10) | pocket half 40.000, R10 dev 3e-5; ring face 776.715 mm2 = analytic 776.715 | 0.1 mm2 | PASS |
| 2 | Pocket under lid | open (no floor between y 40 and 60) | no hit | exact | PASS |
| 2 | Other material in the recess (y 50 .. 55) | none | 0.000 mm3 | 1e-4 | PASS |
| 3 | Plate | 84.5 square | edges 42.250 on all 4 sides (84.500 x 84.500) | 0.005 | PASS |
| 3 | Plate corner | R12.25 | max deviation 0.000 | 3e-3 | PASS |
| 3 | Side clearance | 0.25 | straight edges 0.2500 .. 0.2504 (all four sides, 1520 probes each); corners 0.250 (12 probes) | 0.006 | PASS |
| 3 | Bumps | one per side, tip 0.15 into the wall | four, one per side in a pinwheel (centre +2 mm in each side's tangent frame), tip 42.650, interference 0.150, flat tip 0.65 wide (0.05 scan) | 0.01 | PASS |
| 3 | Interference volume | the 4 bump tips only | 9 pieces: 4 tips of 0.1568 .. 0.1569 mm3 (analytic 0.1565), total 0.627 mm3; 5 slivers totalling 0.0076 mm3 (the 1.2e-5 mm placement residual of the housing STEP at the seat). Tip depth 0.150 +- 0.003 on every tip, all within y 50 .. 51.8 | 15 % on volume | PASS |
| 3 | Plate rests on the ring | bottom plane = seat plane | lid bottom 50.000000, seat 50.000012 (1.2e-5 mm); contact area by 0.02 mm lowering 644.8 mm2 = analytic 644.8; lifted by 0.05 mm only the four tips remain (0.627 mm3) | 5e-5 mm | PASS |
| 3 | Insertion | only tips touch | lid raised 0.5 .. 4 mm: always exactly the four tips, nothing else | | PASS |
| 4 | Arm geometry | 2.0 wide, 1.0 slot, 8 mm free length, 1.8 high | 2.000, 1.000, 8.000 (root x 10.0, bump x 2.0, slot end x -3.0), 1.800 | 0.05 | PASS |
| 4 | Press force per bump | about 2.2 N | k = 3EI/L^3 = 14.77 N/mm, F(0.15) = 2.215 N; with shear flexibility 2.11 N; E +-20 % and interference 0.10 .. 0.20: 1.2 .. 3.5 N | +-0.1 N | PASS |
| 4 | Strain | about 0.7 % | 3 t d / 2 L^2 = 0.703 %; yield strain 45 MPa / 2100 MPa = 2.14 % | 0.03 | PASS |
| 4 | Worst case, lid shoved to one wall (d = 0.40) | claim 5.9 N, 1.9 % | 5.91 N, 1.88 % nominal, 39.4 MPa vs 45 MPa yield (88 %) | | see F2 |
| 5 | Corner bores / lines (13.76 deg, 400 mm) | >= 5 mm | 39.43 mm (all four) | 5.0 | PASS |
| 5 | T_A / T_B / T_C bores | >= 5 mm | 7.00 mm (all three) | 5.0 | PASS |
| 5 | Lines leaving T holes, elevation 0 / 15 / 30 / 45 / 60 deg, surface to lid | >= 5 mm | 7.98 / 7.96 / 7.68 / 6.82 / 5.54 mm | 5.0 | PASS |
| 5 | Steep lines 75 / 90 deg | literal 5 mm not reachable | lid 3.99 (T_C 4.23) / 2.25 mm; the housing rim is closer: 2.42 (T_C 2.84) / 0.00 mm. At 83 deg (the worst elevation of the housing cable study): lid 3.20 (T_C) / 3.08, rim 1.07 / 0.86 mm. Lid stays inside the 45 mm wall plane (max 42.65) | | PASS (lid never limiting) |
| 5 | Camera-bay cover | clear | 21.01 mm, overlap 0.000 mm3 | 5.0 | PASS |
| 5 | Pry notch | opens into free space | notch x -27 .. -13, inner wall z 37.75 (4.5 deep); 2.25 mm of it (z 37.75 .. 40) is over the open pocket; 20 columns under it are empty down to the pocket floor (y 5.0); an 8 x 1 mm blade pushed down to y 8 touches neither lid nor housing; 10 mm of plate to the arm slot, 3 mm of straight edge to the corner start | | PASS |
| 6 | STL watertight | every edge shared by 2 triangles | 1256 triangles, 0 bad edges | exact | PASS |
| 6 | STL vs STEP | volume, bbox | 12391.0 vs 12391.4 mm3 (0.99997); bbox 85.3 x 85.3 x 1.8, bed plane z = 0 | 0.5 % | PASS |
| 6 | Orientation | top face down | bed face z = 0, area 6803.6 mm2, facing down; the seat face is the z = 1.8 top | | PASS |
| 6 | Overhangs | none steeper than 45 deg | downward faces (124 mm2) exist only at z 0 .. 0.3 (the 0.3 x 45 deg top-edge chamfer, exactly 45.0 deg); nothing steeper than 45.5 deg; no downward face above z 0.31 | 45.5 deg | PASS |
| 6 | Minimum feature widths | >= 0.45 mm | none in solid or void at z = 0.1, 0.5, 0.9, 1.3, 1.45, 1.6, 1.75 (opening/closing with a 0.42 mm disc; 16-18 sharp-corner clips of about 0.01 mm2 ignored). Bump tip flat 0.6 .. 0.65, slot 1.0, arm 2.0, plate 1.8 | 0.45 | PASS |
| 7 | STEP round trip | volume and bbox agree | volume 12391.3829 -> 12391.3829, bbox deviation 0, area and 77 faces equal, 1 valid solid | 1e-6 | PASS |
| 7 | Export current with the builder | equal | fresh build equals the export (volume, area, bbox, faces) | 1e-6 | PASS |

## 3. Findings

- **F1 (medium for fit, strict xfail `test_06e`): the bump tips have no relief on the bed edge.** The plate edge has the 0.3 x 45 deg top chamfer, but the bump tip runs full height at 42.650
  right up to the top face (42.650 at y = 51.78, the layer that sits on the bed). Elephant foot (typically 0.1 .. 0.2 mm in PETG) therefore adds directly to the 0.15 mm interference in the first
  layers, and the arm deflection is set by the largest protrusion over the bump height: 0.25 .. 0.35 mm gives 3.7 .. 5.2 N and 1.2 .. 1.6 % strain per bump instead of 2.2 N / 0.7 %.
  Condition: elephant-foot compensation of at least 0.15 mm in the slicer, or the implementer adds a chamfer to the bump top edge (not done here, no repairs).
- **F2 (low): the arm root is a sharp internal corner.** The lid has only 4 x R12.25 and 2 x R2 cylindrical faces; the slot ends are square. Nominal 14.8 MPa (33 % of yield) is fine, Kt about 2 at a
  printed corner gives about 30 MPa (66 %). If the lid is shoved against one wall (0.40 mm), nominal stress is 39.4 MPa (88 % of yield) and the root corner yields locally, so expect creep or
  set (the grip loosens, the lid does not break). The lid centres itself (restoring stiffness 2 k = 29.5 N/mm), so this is a transient state, but it is also the state after a careless
  insertion. A fillet of at least 0.5 mm at the slot ends would remove it (suggestion only).
- **F3 (info): the notch needs free space inside the housing that this STEP cannot show.** The housing STEP itself is empty under the notch down to the pocket floor (45 mm). The ESP32, LiPo and
  wiring are not in the STEP: keep the strip x -27 .. -13, z 37.75 .. 40 (2.25 mm wide) clear to at least 8 mm below the lid.
- **F4 (print, as asked): an 85.3 x 85.3 x 1.8 mm PETG plate warps.** The big face (6804 mm2) is on the bed, which is the best orientation, and the slots relieve in-plane stress. Even so, corner lift of 0.2 .. 0.5 mm
  is typical when the plate comes off warm; the lid sits on a 2.5 mm ring over an open pocket, so a bowed lid rocks on the ring and presses unevenly. Condition: heated bed at the filament's
  setting, little or no part cooling on the first layers, 3 .. 5 mm brim or mouse ears if the corners lift, remove only below about 40 deg C, accept if flat within 0.2 mm on a surface plate.
  The lid and the housing should be the same material and slicer scaling: both shrink about 0.3 %, which scales the 0.25 mm gap and the 0.15 mm interference by the same factor.
- **F5 (info): pinwheel couple.** The four bump forces act 2 mm off the side centres, all in the same sense: a net yaw couple of about 4 x 2.2 N x 2 mm = 17.7 N.mm. The arms alone would
  yaw the lid several degrees, but the plate corners meet the wall after about 0.5 deg (0.25 mm over a 30 mm lever), so about 0.3 N of wall reaction at the corners carries it. Harmless.
- **F6 (info): coarse lead-in.** The 45 deg lead-in is 0.4 mm high: two layers at 0.2 mm. It is printed as two steps; insertion will work, the lead-in is not smooth.
- Agreement with the notes: every number in section 3 of the build notes was reproduced (interference pieces 4 x 0.157 mm3, 39.4 / 7.0 mm bores, line clearances 8.0 / 7.7 / 6.8 / 5.54 / 3.99 / 2.25 mm,
  21.0 mm to the cover, 644.8 mm2 contact, 2.2 N, 0.70 %, bed area 6804 mm2, STL volume within 1 %).

## 4. Not covered

- Friction coefficient, creep over time, actual FDM size error of the printed recess (the arms tolerate about +-0.1 mm; a recess printed more than 0.15 mm oversize leaves the lid loose).
- Cable lines leaving the T holes outside the vertical plane of the bore axis: handled by the geometric argument (the lid stays 2.35 mm behind the outer wall plane, so a line that leaves
  the wall cannot reach it), not by a full azimuth scan.
- Plate bending under a press in the middle (notes: 0.65 mm under 10 N; rough check with simply supported square plate theory, a = 80 mm, h = 1.8 mm, E = 2.1 GPa: 0.62 mm). Not simulated.
- Insertion force (estimated about 20 N for the four wedges at mu 0.4, not measured).
- No standardized renders were reviewed; the build notes list the 7 views in `renders/gripper1021_lid/`.

## 5. Files

`tests/test_gripper1021_housing_lid_verification.py` (21 tests, 1 expected failure), this report. Scratch scripts only in the session scratchpad.
