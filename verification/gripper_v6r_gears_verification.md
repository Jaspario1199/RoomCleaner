# Verification report: gripper v6r gears (Jasper's v6 gears, 2:1 gearbox)

Verifier: geometry-verifier (independent of the implementer). Date 2026-10-21. Nothing repaired, committed or pushed.
Scope: `exports/step/gripper_v6r_{pinion,compound_36T_24T,compound_36T_24T_norelief,follower}.step` and the matching STLs,
against his originals in `solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP` (via `cad/v6_loader.py`), the `GRIPV6R_*`
block of `cad/params.py`, `verification/gripper_v6_inspection.md` and the claims in `verification/gripper_v6r_gears_numbers.json`.
Method: every number below is measured by `tests/test_gripper_v6r_gears_verify.py` (own section/outline/boolean code; the
implementer's builder is used only in check 8.13 to prove the delivered files are current). The json was not trusted.

Reproduce: `/usr/bin/python3 -m pytest -q -s tests/test_gripper_v6r_gears_verify.py` (about 9 min, prints the table below).
Existing implementer test: `/usr/bin/python3 -m pytest -q tests/test_gripper_v6r_gears.py` -> **21 passed, 0 failed, 0 skipped (328.65 s)**.
This verification test: **22 passed, 0 failed, 257 checks, 0 FAIL (546 s)**.

## Verdict: PASS WITH CONDITIONS

No geometry or fidelity failure was found. The conditions are advisory, not defects (section 7).

## 1. Feature fidelity against his solids

Method: position-free census of every cylinder (R, z range, face count, area) and horizontal plane on both sides; booleans
(his solid translated to its axis, rotated by the applied lug angle, versus the delivered part) in two regions
(gear body + 24T layer + hub, and the lug beyond the removed 22 mm slab); section y-crossings of the lug at 5 stations;
outline Hausdorff of the 24T teeth.

| Part | Result |
|---|---|
| Pinion | IDENTICAL to his apart from placement: boolean his-new = new-his = 0.000 mm3, census identical, area and volume equal, tooth phase 8.6117 deg unchanged, Ø8.00 bore, Ø30 tip, Ø23.25 root, face 16. |
| Compound, kept | Pocket Ø14.075 at z 1.95..7.0 (5.05 deep) and z 24.0..34.05 (10.05 deep); Ø14.000 entry lips z 0..1.95 and 34.05..36 (1.95 each); Ø8.30 shoulder z 7..24; planar layers 0/7/16/24/26/36; 24T layer 16..36 (face 20); lug band 16..26 (10 thick); fork Ø18.30 outer, 8.30 slot; Ø3.5 pivot hole; no other chamfer or fillet exists except the R0.4 root blends and R0.25 lip features, all unchanged. Body + hub + 24T boolean difference 0.0002 / 0.0003 mm3 of 20 924. |
| Follower, kept | Cylinder census identical to his (zero differences). Pocket Ø14.075 z 24..34.075, lip Ø14.000 z 34.075..36 (single top lip, as his), shoulder Ø8.33 z 16..24, fork Ø18.33 / slot 8.33, Ø8.33 pivot hole, lug band 16..26. Body boolean 0.0000 / 0.0000 mm3 of 18 931. |
| 24T teeth (both) | Outline Hausdorff distance new-rotated-back vs his = 0.000000 mm; 24 teeth, thickness 2.25619 mm both; so the tooth form is identical and the re-phasing is a pure rotation (phase-independent). |
| Lug section | Identical y-crossings at the 5 compared stations (constant section 18.3 / 8.3 over arm x 30..60, boss end 15.3 wide); lug end = his end - 22.000 mm; the slab removed was constant-section, so the join is continuous. Lug beyond-cut boolean difference 0.001 mm3 (compound) and 0.27 mm3 (follower, an artefact of the 1 micron shift needed to avoid a coincident-face boolean failure); a deliberate 0.05 mm shift gives 10.9 / 13.3 mm3, so the test would detect a real difference. |

Every difference found, classified:

| Difference | Class |
|---|---|
| 54T ring -> 36T ring: tip R42 -> R28.5, root R38.625 -> R25.125, 54 -> 36 teeth, 108 -> 72 R0.4 root-fillet faces; the flank faces change representation (BSpline -> surface of extrusion) | intended |
| Lightening 8 x Ø12 on R27 -> 7 x Ø12 on R16.7 (hole Ø unchanged; phase arbitrary) | intended |
| Lug / fork radius R75 -> R53 (compound R75.0002 -> R52.9997, follower R74.9996 -> R52.9997; shift 22.000 +- 0.0005) | intended |
| Lug angle: compound -31.2259 -> -78.5887 deg, follower 209.8829 -> 258.5890 deg (whole part rotated by -47.363 and +48.706 deg, so 24T phase moves with it) | intended |
| 0.30 mm relief, R >= 16.5, z 15.7..16.0 on the compound (not in the _norelief variant) | intended (flagged functional change) |
| Lug end faces / planar areas at z 16 and 26 shortened by the 22 mm slab | consequence of the above |
| His lugs were 1.343 deg off exact mirror; the new pair is exact mirror | consequence (puts the 24T mesh at the window centre, verified in 3) |
| UNINTENDED differences | none found (check 3.1 lists zero) |

Observation (his geometry, kept): the compound pivot hole is Ø3.5 but the follower pivot hole is Ø8.33 (and the inspection note says
Ø3.5 for both). Not a v6r change; worth a look when the jaw links are designed.

## 2. New 36T teeth

Tip R28.5000, root R25.1250, 36 teeth. Tooth thickness at the R27 pitch circle 2.25619 mm; his 54T at R40.5: 2.25619 mm (difference
6e-7 mm); ideal pi m/2 = 2.35619, so thinning 0.100001 mm. Involute test: phi_b = |angle from tooth centre| + inv(alpha) is
constant over the flank to 3.4e-7 mm for the new 36T, 6.0e-7 mm for his 54T, 3.4e-7 mm for his 24T and his 18T, with implied
thinning 0.1000 mm in all four, i.e. a true 20 deg involute consistent with his. Independent of the tooth count: the repo's v3
generator, run for 18T, 54T and 24T, reproduces his section outlines with Hausdorff distance 0.00000 mm (root blend included),
so the 36T made by the same generator has his tooth form.

## 3. Clearances (pinion-compound 40.80, compound-follower 36.30, his Z layers)

Mesh windows were found by rotating one gear until the section outlines touch (own 2D implementation, bisection 2e-4 deg),
every 1 deg over -30..+76.5 deg of compound rotation (pinion -2 d, follower -d), 108 poses, both meshes.

| Item | Required / claimed | Measured |
|---|---|---|
| Circumferential backlash pinion/36T, +-30 deg sweep and 0..76.5 stroke | >= 0.42 | 0.4244 mm min (0.4244 max), constant |
| Circumferential backlash 24T/24T, both ranges | >= 0.42 | 0.4251 mm min |
| Tighter flank, circumferential, as-built pose | - | 0.2121 (pinion/36T), 0.2125 (24T) mm |
| Normal clearance per flank (x cos 20) | about 0.20 | 0.1994 / 0.1997 mm |
| As-built pose within the window | centred | offset <= 0.0001 deg (window +-0.90 deg pinion, +-0.68 deg 24T) |
| Tip-to-root, four directions | >= 0.375 (claim 0.675) | 0.6750 each; swept minimum 0.6712 (0.01 mm root band) |
| Tooth overlap, 3D booleans, 21 poses -20..76.5 deg, 8 pairs (gears and lugs) | 0 | 0 mm3 everywhere; positive controls (2.5 / 3 deg off window) give 33.6 / 23.2 mm3 |
| Follower to 36T axial gap, relief / no relief | 0.300 / 0 | 0.3000 / 0.0000 mm at d = 0, 30, 76.5 (3D distance); relief floor z 15.7, follower bottom z 16.0, follower material below z 16 = 0 |
| Relief radial margin to the follower tip circle | 0.30 | 36.30 - 19.5 - 16.5 = 0.30 mm; removed volume 287.62 mm3 equals the annulus volume |
| Swept lug / fork clearance (gears, other lug, pinion, pins, bearings), 0..76.5 deg | >= 1.0 (claim >= 10.17) | 10.166 mm (follower lug to compound gear at d = 0); claim holds to rounding (0.004 mm) |
| Lug-to-lug first contact | from -21.5 deg | first contact at -21.5 deg (0.33 mm apart at -21); overlap 833.7 mm3 at -25; none inside the stroke |

## 4. Crank phasing

Compound lug -78.5887 deg, follower 258.5890 deg (targets -78.589 / 258.589, tolerance 0.002); angle_c + angle_f = 180 deg exactly,
placed pivots mirror about x = 0 to < 0.001 mm; crank radius 52.9997 mm; the placed compound pivot is 0.0004 mm from the
GRIPV7 four-bar crank pin (`gripper_v7_kin.default().Ac`); R = 53.0 and theta_closed = -78.589 match GRIPV7 exactly.

## 5. Structure

Section measurement (z = 3 and z = 10, both compound variants): 7 holes of Ø12 on R16.7; ligaments hole -> pocket wall 3.6625,
hole -> 36T root circle 2.4250, hole -> hole 2.4917 mm (claims 3.66 / 2.43 / 2.49); hole -> Ø8.30 shoulder 6.55 mm. All >= 2.0.

Spoke check at 6 V stall (11.0 kg cm): tangential force 79.9 N at the pinion and the 36T pitch circle (T = 2.16 N m on the 36T).
Equal share on the spokes, load at the hole-circle radius, 16 mm thick, PETG allowable 22.5 MPa. Spoke bending is bounded as a
cantilever of length 12 mm (conservative) and as fixed-guided (M = F L / 2); the rim is checked as a simply supported bridge over a hole.

| Layout | Spoke width | Load / spoke | Bending (cantilever / guided) | Shear | Rim bridge | SF (cantilever) |
|---|---|---|---|---|---|---|
| 7 x Ø12 on R16.7 (delivered) | 2.49 mm | 18.5 N | 13.4 / 6.7 MPa | 0.69 MPa | 5.6 MPa | 1.68 (rim 4.0) |
| 6 x Ø12 on R16.08 (balanced ligaments 3.04) | 4.08 mm | 22.4 N | 6.0 / 3.0 MPa | 0.51 MPa | 3.5 MPa | 3.75 |
| 6 x Ø12 on R16.7 | 4.70 mm | 21.5 N | 4.4 / 2.2 MPa | 0.43 MPa | 5.6 MPa | 5.1 |

The 7-hole web passes at SF 1.68 on the conservative bound (3.4 on the guided bound) and the rim is not governing. The 6-hole
alternative has about 2.2 times lower spoke stress and a thicker rim (3.04 mm) for 2.3 g more PETG. Screening only: no stress
concentration at the hole edges, no layer-orientation derating, no fatigue.

## 6. Exports

All four STEP files: valid, exactly one solid, re-export + reimport volume difference <= 2e-12 (relative) and bbox difference
<= 1e-14 mm. A fresh build of the implementer's code equals the delivered STEP files (0.0000 mm3 both ways), so the exports are
current. All four STLs: closed 2-manifold (0 edges not shared by exactly two triangles), positive signed volume, z-min on the bed
(0.0000), gear axis vertical, height equals the STEP z-extent (follower printed z 0..20), x/y extents within 0.003 mm, mesh volume
within 0.022 % of STEP.

Masses (PETG 1.27 g/cc, recomputed): pinion 10.19 g, compound 56.77 g, compound_norelief 57.14 g, follower 28.88 g; gear set
95.84 g against 157.41 g for his three originals.

## 7. Conditions and observations (none is a failure)

1. Spoke margin is modest (SF 1.68 conservative). If the 6 V stall load is expected, the 6 x Ø12 layout doubles it for 2.3 g.
   Print a first article and test the 2.4 mm rim ligament (hole -> root circle).
2. The as-built mesh window is only +-0.90 deg on the pinion and +-0.68 deg on the 24T pair (0.21 mm per flank). The pinion keeps
   his orientation (phase 8.61 deg), so the pinion-to-servo angular fit decides whether the pinion sits at the window centre.
   Hardware clocking is not modelled (no horn pocket, as his).
3. The compound prints with the 36T ring on the bed; the lug band (z 16..26, out to R62) overhangs 16 mm above the bed and needs
   supports (as his R75 part did).
4. Bearing pockets Ø14.075 with Ø14.000 lips and the Ø7 pins are his, unchanged (inspection items 3 and 12 still apply).
5. The closed stop must be mechanical, at the jaw tips; the gear lugs themselves collide 21.5 deg beyond it.
6. Tooling note: the first run of the verification test had one failure (check 3.9, compound) caused by an OCC boolean returning an empty
   result on exactly coincident faces, not by the geometry; the test now retries with a micron shift and requires >= 99 % common
   volume, and the control with a 0.05 mm shift shows it still detects real differences.

## 8. Full check table (257 checks, tolerance column is the pass band; blank means a threshold test)

| ID | Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|---|
| 0.1 | his STEP sha256 equals the git HEAD blob | c57a2c9f9ee65231 | c57a2c9f9ee65231 | exact | PASS |
| 0.2 | file exists gripper_v6r_pinion.step | exists | exists |  | PASS |
| 0.2 | file exists gripper_v6r_pinion.stl | exists | exists |  | PASS |
| 0.2 | file exists gripper_v6r_compound_36T_24T.step | exists | exists |  | PASS |
| 0.2 | file exists gripper_v6r_compound_36T_24T.stl | exists | exists |  | PASS |
| 0.2 | file exists gripper_v6r_compound_36T_24T_norelief.step | exists | exists |  | PASS |
| 0.2 | file exists gripper_v6r_compound_36T_24T_norelief.stl | exists | exists |  | PASS |
| 0.2 | file exists gripper_v6r_follower.step | exists | exists |  | PASS |
| 0.2 | file exists gripper_v6r_follower.stl | exists | exists |  | PASS |
| 1.1 | pinion valid BREP | True | True |  | PASS |
| 1.2 | pinion solid count | 1 | 1 |  | PASS |
| 1.3 | pinion volume > 0 (mm3) | >= 1 | 8024.15 |  | PASS |
| 1.4 | pinion bbox x-size = his pinion (mm) | 29.7845 | 29.7845 | +-0.001 | PASS |
| 1.5 | pinion bbox y-size (derived from lug R53 / tip envelope) (mm) | 30 | 30 | +-0.02 | PASS |
| 1.6 | pinion bbox z-size (stack height) (mm) | 16 | 16 | +-0.001 | PASS |
| 1.7 | pinion bbox z-min (mm) | 0 | -9.96617e-08 | +-0.001 | PASS |
| 1.1 | compound valid BREP | True | True |  | PASS |
| 1.2 | compound solid count | 1 | 1 |  | PASS |
| 1.3 | compound volume > 0 (mm3) | >= 1 | 44700.8 |  | PASS |
| 1.5 | compound bbox y-size (derived from lug R53 / tip envelope) (mm) | 89.5859 | 89.5859 | +-0.02 | PASS |
| 1.6 | compound bbox z-size (stack height) (mm) | 36 | 36 | +-0.001 | PASS |
| 1.7 | compound bbox z-min (mm) | 0 | -1e-07 | +-0.001 | PASS |
| 1.1 | compound_norelief valid BREP | True | True |  | PASS |
| 1.2 | compound_norelief solid count | 1 | 1 |  | PASS |
| 1.3 | compound_norelief volume > 0 (mm3) | >= 1 | 44988.4 |  | PASS |
| 1.5 | compound_norelief bbox y-size (derived from lug R53 / tip envelope) (mm) | 89.5859 | 89.5859 | +-0.02 | PASS |
| 1.6 | compound_norelief bbox z-size (stack height) (mm) | 36 | 36 | +-0.001 | PASS |
| 1.7 | compound_norelief bbox z-min (mm) | 0 | -1e-07 | +-0.001 | PASS |
| 1.1 | follower valid BREP | True | True |  | PASS |
| 1.2 | follower solid count | 1 | 1 |  | PASS |
| 1.3 | follower volume > 0 (mm3) | >= 1 | 22741.5 |  | PASS |
| 1.5 | follower bbox y-size (derived from lug R53 / tip envelope) (mm) | 80.5989 | 80.5989 | +-0.02 | PASS |
| 1.6 | follower bbox z-size (stack height) (mm) | 20 | 20 | +-0.001 | PASS |
| 1.7 | follower bbox z-min (mm) | 16 | 16 | +-0.001 | PASS |
| 1.8 | compound x-size = 36T tooth envelope <= 57.0 (mm) | 57 | 56.967 | +-0.05 | PASS |
| 2.1 | pinion volume vs his (mm3) | 8024.15 | 8024.15 | +-0.001 | PASS |
| 2.2 | pinion area vs his (mm2) | 4147.47 | 4147.47 | +-0.01 | PASS |
| 2.3 | pinion boolean his minus new (mm3) | 0 | -0.00000 | +-0.01 | PASS |
| 2.4 | pinion boolean new minus his (mm3) | 0 | 0.00000 | +-0.01 | PASS |
| 2.5 | pinion cylinder census (R, z range, faces, area) vs his | identical | identical |  | PASS |
| 2.6 | pinion bore diameter (mm) | 8 | 8 | +-0.0001 | PASS |
| 2.7 | pinion tip diameter (mm) | 30 | 30 | +-0.0001 | PASS |
| 2.8 | pinion root diameter (mm) | 23.25 | 23.25 | +-0.0001 | PASS |
| 2.9 | pinion face width (mm) | 16 | 16 | +-0.0001 | PASS |
| 2.10 | pinion tooth phase deg (his orientation kept) | 8.61167 | 8.61167 | +-0.0001 | PASS |
| 3.1 | compound: UNINTENDED cylinder-census differences vs his (all others: 8 intended) | none | none |  | PASS |
| 3.2 | compound: lower bearing pocket Ø14.075 (5.05 deep) present and equal to his | R7.0375 z1.950..7.000 | [(7.0375, 1.95, 7.0)] |  | PASS |
| 3.2 | compound: upper bearing pocket Ø14.075 (10.05 deep) present and equal to his | R7.0375 z24.000..34.050 | [(7.0375, 24.0, 34.05)] |  | PASS |
| 3.2 | compound: lower entry lip Ø14.000 x 1.95 present and equal to his | R7.0000 z0.000..1.950 | [(7.0, 0.0, 1.95)] |  | PASS |
| 3.2 | compound: upper entry lip Ø14.000 x 1.95 present and equal to his | R7.0000 z34.050..36.000 | [(7.0, 34.05, 36.0)] |  | PASS |
| 3.2 | compound: centre shoulder Ø8.30 present and equal to his | R4.1500 z7.000..24.000 | [(4.15, 7.0, 24.0)] |  | PASS |
| 3.3 | compound: lightening holes (7 x Ø12) | 7 | 7 |  | PASS |
| 3.4 | compound: lightening circle radius (mm) | [16.7] | [16.7] | +-0.005 | PASS |
| 3.5 | compound: Z layers (ring top / relief floor, 24T layer 16..36, lug band 16..26, pockets) | [0.0, 1.95, 7.0, 15.7, 16.0, 24.0, 26.0, 34.05, 36.0] | [0.0, 1.95, 7.0, 15.7, 16.0, 24.0, 26.0, 34.05, 36.0] |  | PASS |
| 3.1 | compound_norelief: UNINTENDED cylinder-census differences vs his (all others: 6 intended) | none | none |  | PASS |
| 3.2 | compound_norelief: lower bearing pocket Ø14.075 (5.05 deep) present and equal to his | R7.0375 z1.950..7.000 | [(7.0375, 1.95, 7.0)] |  | PASS |
| 3.2 | compound_norelief: upper bearing pocket Ø14.075 (10.05 deep) present and equal to his | R7.0375 z24.000..34.050 | [(7.0375, 24.0, 34.05)] |  | PASS |
| 3.2 | compound_norelief: lower entry lip Ø14.000 x 1.95 present and equal to his | R7.0000 z0.000..1.950 | [(7.0, 0.0, 1.95)] |  | PASS |
| 3.2 | compound_norelief: upper entry lip Ø14.000 x 1.95 present and equal to his | R7.0000 z34.050..36.000 | [(7.0, 34.05, 36.0)] |  | PASS |
| 3.2 | compound_norelief: centre shoulder Ø8.30 present and equal to his | R4.1500 z7.000..24.000 | [(4.15, 7.0, 24.0)] |  | PASS |
| 3.3 | compound_norelief: lightening holes (7 x Ø12) | 7 | 7 |  | PASS |
| 3.4 | compound_norelief: lightening circle radius (mm) | [16.7] | [16.7] | +-0.005 | PASS |
| 3.5 | compound_norelief: Z layers (ring top / relief floor, 24T layer 16..36, lug band 16..26, pockets) | [0.0, 1.95, 7.0, 16.0, 24.0, 26.0, 34.05, 36.0] | [0.0, 1.95, 7.0, 16.0, 24.0, 26.0, 34.05, 36.0] |  | PASS |
| 3.6 | follower: cylinder census differences vs his | none | none |  | PASS |
| 3.7 | follower: upper bearing pocket Ø14.075 (10.075 deep) present | R7.0375 z24.000..34.075 | [(7.0375, 24.0, 34.075)] |  | PASS |
| 3.7 | follower: upper lip Ø14.000 present | R7.0000 z34.075..36.000 | [(7.0, 34.075, 36.0)] |  | PASS |
| 3.7 | follower: centre shoulder Ø8.33 present | R4.1650 z16.000..24.000 | [(4.165, 16.0, 24.0)] |  | PASS |
| 3.8 | compound: gear body + 24T layer + hub (arm-frame x<30, z>=16, his rotated by -47.3631 deg): his-new, new-his (mm3) | 0, 0 | 0.0002, 0.0003 of 20924 | +-0.05 | PASS |
| 3.9 | compound: lug beyond the cut, his shifted -22 mm: his-new, new-his (mm3; a few-um shift to dodge coincident faces adds <= 0.3) | 0, 0 | 0.0009, 0.0009 of 4251 | +-1.0 | PASS |
| 3.10 | compound: sensitivity control, same comparison with a 0.05 mm shift (mm3) | > 3 (detects) | 10.90 |  | PASS |
| 3.10b | compound: 24T tooth outline at z=31, new rotated back vs his, Hausdorff (mm) | < 0.001 | 0.000000 |  | PASS |
| 3.10c | compound: 24T count / pitch-circle tooth thickness new vs his (mm) | 24 / equal | 24 / 2.25619 vs 2.25619 | +-1e-5 | PASS |
| 3.8 | follower: gear body + 24T layer + hub (arm-frame x<30, z>=16, his rotated by 48.7061 deg): his-new, new-his (mm3) | 0, 0 | 0.0000, -0.0000 of 18931 | +-0.05 | PASS |
| 3.9 | follower: lug beyond the cut, his shifted -22 mm: his-new, new-his (mm3; a few-um shift to dodge coincident faces adds <= 0.3) | 0, 0 | 0.2686, 0.2686 of 3811 | +-1.0 | PASS |
| 3.10 | follower: sensitivity control, same comparison with a 0.05 mm shift (mm3) | > 3 (detects) | 13.33 |  | PASS |
| 3.10b | follower: 24T tooth outline at z=31, new rotated back vs his, Hausdorff (mm) | < 0.001 | 0.000000 |  | PASS |
| 3.10c | follower: 24T count / pitch-circle tooth thickness new vs his (mm) | 24 / equal | 24 / 2.25619 vs 2.25619 | +-1e-5 | PASS |
| 3.11 | compound: lug section y-crossings at arm x=29.9 (his) / 29.9 (new) | equal | his [-9.15, -4.15, 4.15, 9.15] / new [-9.15, -4.15, 4.15, 9.15] | exact 1e-3 | PASS |
| 3.11 | compound: lug section y-crossings at arm x=40 (his) / 40 (new) | equal | his [-9.15, -4.15, 4.15, 9.15] / new [-9.15, -4.15, 4.15, 9.15] | exact 1e-3 | PASS |
| 3.11 | compound: lug section y-crossings at arm x=60 (his) / 38 (new) | equal | his [-9.15, -4.15, 4.15, 9.15] / new [-9.15, -4.15, 4.15, 9.15] | exact 1e-3 | PASS |
| 3.11 | compound: lug section y-crossings at arm x=70 (his) / 48 (new) | equal | his [-9.15, 9.15] / new [-9.15, 9.15] | exact 1e-3 | PASS |
| 3.11 | compound: lug section y-crossings at arm x=80 (his) / 58 (new) | equal | his [-7.663, 7.663] / new [-7.663, 7.663] | exact 1e-3 | PASS |
| 3.11b | compound: fork section Ø18.30 outer, slot 8.30 (arm x=40) | [-9.15, -4.15, 4.15, 9.15] | [-9.15, -4.15, 4.15, 9.15] |  | PASS |
| 3.12 | compound: lug end x in arm frame, his - 22 (mm) | 62.15 | 62.15 | +-0.01 | PASS |
| 3.13 | compound: lug band z 16..26 (10 mm thick) | {16.0, 26.0} | {16.0, 26.0} |  | PASS |
| 3.14 | compound his: pivot hole Ø3.50 at crank radius 75 | 1 hole | 1 |  | PASS |
| 3.15 | compound his: pivot radius from the gear axis (mm) | 75 | 75.0002 | +-0.002 | PASS |
| 3.14 | compound new: pivot hole Ø3.50 at crank radius 53 | 1 hole | 1 |  | PASS |
| 3.15 | compound new: pivot radius from the gear axis (mm) | 53 | 52.9997 | +-0.002 | PASS |
| 3.11 | follower: lug section y-crossings at arm x=29.9 (his) / 29.9 (new) | equal | his [-9.165, -4.165, 4.165, 9.165] / new [-9.165, -4.165, 4.165, 9.165] | exact 1e-3 | PASS |
| 3.11 | follower: lug section y-crossings at arm x=40 (his) / 40 (new) | equal | his [-9.165, -4.165, 4.165, 9.165] / new [-9.165, -4.165, 4.165, 9.165] | exact 1e-3 | PASS |
| 3.11 | follower: lug section y-crossings at arm x=60 (his) / 38 (new) | equal | his [-9.165, -4.165, 4.165, 9.165] / new [-9.165, -4.165, 4.165, 9.165] | exact 1e-3 | PASS |
| 3.11 | follower: lug section y-crossings at arm x=70 (his) / 48 (new) | equal | his [-9.165, 9.165] / new [-9.165, 9.165] | exact 1e-3 | PASS |
| 3.11 | follower: lug section y-crossings at arm x=80 (his) / 58 (new) | equal | his [-7.681, 7.681] / new [-7.681, 7.681] | exact 1e-3 | PASS |
| 3.11b | follower: fork section Ø18.33 outer, slot 8.33 (arm x=40) | [-9.165, -4.165, 4.165, 9.165] | [-9.165, -4.165, 4.165, 9.165] |  | PASS |
| 3.12 | follower: lug end x in arm frame, his - 22 (mm) | 62.165 | 62.165 | +-0.01 | PASS |
| 3.13 | follower: lug band z 16..26 (10 mm thick) | {16.0, 26.0} | {16.0, 26.0} |  | PASS |
| 3.14 | follower his: pivot hole Ø8.33 at crank radius 75 | 1 hole | 1 |  | PASS |
| 3.15 | follower his: pivot radius from the gear axis (mm) | 75 | 74.9996 | +-0.002 | PASS |
| 3.14 | follower new: pivot hole Ø8.33 at crank radius 53 | 1 hole | 1 |  | PASS |
| 3.15 | follower new: pivot radius from the gear axis (mm) | 53 | 52.9997 | +-0.002 | PASS |
| 3.16 | observation: his compound pivot hole Ø3.5 but his follower pivot hole Ø8.33 (kept, as his) | info | info |  | PASS |
| 4.1 | 36T tip radius (mm) [m1.5: 27 + 1.5] | 28.5 | 28.5 | +-0.0001 | PASS |
| 4.2 | 36T root radius (mm) [27 - 1.875] | 25.125 | 25.125 | +-0.0001 | PASS |
| 4.3 | 36T teeth counted (pitch-circle crossings / 2) | 36 | 36 |  | PASS |
| 4.4 | 36T tooth thickness at the R27 pitch circle (mm) [claim 2.2562] | 2.2562 | 2.25619 | +-0.0005 | PASS |
| 4.5 | 36T thickness minus his 54T thickness at its R40.5 pitch circle (mm) | 0 | 6.36705e-07 | +-0.0001 | PASS |
| 4.6 | thinning against ideal pi*m/2 = 2.35619 (mm) | 0.1 | 0.100001 | +-0.0005 | PASS |
| 4.7 | new 36T: flank is a 20 deg involute (max deviation mm), implied thinning (mm) | dev < 0.002, thinning 0.100 | dev 3.4e-07 (16128 pts), thinning 0.1000 |  | PASS |
| 4.7 | his 54T: flank is a 20 deg involute (max deviation mm), implied thinning (mm) | dev < 0.002, thinning 0.100 | dev 6.0e-07 (24408 pts), thinning 0.1000 |  | PASS |
| 4.7 | his 24T (compound above the lug band): flank is a 20 deg involute (max deviation mm), implied thinning (mm) | dev < 0.002, thinning 0.100 | dev 3.4e-07 (8064 pts), thinning 0.1000 |  | PASS |
| 4.7 | his 18T pinion: flank is a 20 deg involute (max deviation mm), implied thinning (mm) | dev < 0.002, thinning 0.100 | dev 3.4e-07 (5076 pts), thinning 0.1000 |  | PASS |
| 4.8 | 36T R0.4 root fillet faces (2 per tooth) | 72 | 72 |  | PASS |
| 4.9 | generator 18T pinion vs his outline, Hausdorff distance (mm) | < 0.002 | 0.00000 |  | PASS |
| 4.9 | generator 54T ring vs his outline, Hausdorff distance (mm) | < 0.002 | 0.00000 |  | PASS |
| 4.9 | generator 24T (compound) vs his outline, Hausdorff distance (mm) | < 0.002 | 0.00000 |  | PASS |
| 5.1 | pinion-compound centre distance (mm) | 40.8 | 40.8 | +-1e-06 | PASS |
| 5.2 | compound-follower centre distance (mm) | 36.3 | 36.3 | +-1e-09 | PASS |
| 5.3 | GRIPV7 CD_MAIN (m1.5*(18+36)/2 + 0.30) | 40.8 | 40.8 | +-1e-09 | PASS |
| 5.4 | GRIPV7 CD_SYNC (m1.5*24 + 0.30) | 36.3 | 36.3 | +-1e-09 | PASS |
| 5.5 | pinion/36T +-30 deg sweep (61 poses): total circumferential backlash, min (mm) [claim >= 0.42] | >= 0.42 | 0.424357 |  | PASS |
| 5.6 | pinion/36T +-30 deg sweep: circumferential clearance on the TIGHTER flank at the as-built pose (mm) | >= 0.2 | 0.212144 |  | PASS |
| 5.7 | pinion/36T +-30 deg sweep: normal clearance per flank = that x cos20 (mm) [claim ~0.20] | >= 0.19 | 0.19935 |  | PASS |
| 5.8 | pinion/36T +-30 deg sweep: window-centre offset of the as-built pose (deg) | /./ < 0.02 | -0.0001 .. 0.0000 |  | PASS |
| 5.5 | pinion/36T 0..76.5 stroke (78 poses): total circumferential backlash, min (mm) [claim >= 0.42] | >= 0.42 | 0.424357 |  | PASS |
| 5.6 | pinion/36T 0..76.5 stroke: circumferential clearance on the TIGHTER flank at the as-built pose (mm) | >= 0.2 | 0.212144 |  | PASS |
| 5.7 | pinion/36T 0..76.5 stroke: normal clearance per flank = that x cos20 (mm) [claim ~0.20] | >= 0.19 | 0.19935 |  | PASS |
| 5.8 | pinion/36T 0..76.5 stroke: window-centre offset of the as-built pose (deg) | /./ < 0.02 | -0.0001 .. 0.0000 |  | PASS |
| 5.5 | 24T/24T +-30 deg sweep (61 poses): total circumferential backlash, min (mm) [claim >= 0.42] | >= 0.42 | 0.425081 |  | PASS |
| 5.6 | 24T/24T +-30 deg sweep: circumferential clearance on the TIGHTER flank at the as-built pose (mm) | >= 0.2 | 0.212541 |  | PASS |
| 5.7 | 24T/24T +-30 deg sweep: normal clearance per flank = that x cos20 (mm) [claim ~0.20] | >= 0.19 | 0.199723 |  | PASS |
| 5.8 | 24T/24T +-30 deg sweep: window-centre offset of the as-built pose (deg) | /./ < 0.02 | -0.0001 .. 0.0001 |  | PASS |
| 5.5 | 24T/24T 0..76.5 stroke (78 poses): total circumferential backlash, min (mm) [claim >= 0.42] | >= 0.42 | 0.425081 |  | PASS |
| 5.6 | 24T/24T 0..76.5 stroke: circumferential clearance on the TIGHTER flank at the as-built pose (mm) | >= 0.2 | 0.212541 |  | PASS |
| 5.7 | 24T/24T 0..76.5 stroke: normal clearance per flank = that x cos20 (mm) [claim ~0.20] | >= 0.19 | 0.199723 |  | PASS |
| 5.8 | 24T/24T 0..76.5 stroke: window-centre offset of the as-built pose (deg) | /./ < 0.02 | -0.0001 .. 0.0001 |  | PASS |
| 5.9 | no tooth overlap: min outline gap at the as-built pose, pinion/36T, all poses (mm) | >= 0.15 | 0.199369 |  | PASS |
| 5.10 | no tooth overlap: min outline gap at the as-built pose, 24T/24T, all poses (mm) | >= 0.15 | 0.199719 |  | PASS |
| 5.11 | tip-to-root clearance, pinion tip -> 36T root (mm) [claim 0.675] | >= 0.375 (0.675) | 0.6750 |  | PASS |
| 5.11 | tip-to-root clearance, 36T tip -> pinion root (mm) [claim 0.675] | >= 0.375 (0.675) | 0.6750 |  | PASS |
| 5.11 | tip-to-root clearance, compound 24T tip -> follower root (mm) [claim 0.675] | >= 0.375 (0.675) | 0.6750 |  | PASS |
| 5.11 | tip-to-root clearance, follower tip -> compound 24T root (mm) [claim 0.675] | >= 0.375 (0.675) | 0.6750 |  | PASS |
| 5.12 | swept min distance tip land -> root land, 4 pairs, -30..76.5 deg (mm; root band 0.01 mm) | >= 0.375 | 0.6712 |  | PASS |
| 5.13 | 3D common volume pinion x compound, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.13 | 3D common volume compound x follower, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.13 | 3D common volume pinion x follower, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.13 | 3D common volume compound lug x follower, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.13 | 3D common volume follower lug x compound, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.13 | 3D common volume lug x lug, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.13 | 3D common volume compound lug x pinion, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.13 | 3D common volume follower lug x pinion, max over 21 poses -20..76.5 deg (mm3) | 0 | 0 | +-1e-3 | PASS |
| 5.14 | positive control: follower turned 2.5 deg off its window overlaps (mm3) | > 0.5 | 33.571 |  | PASS |
| 5.15 | positive control: pinion turned 3 deg off its window overlaps (mm3) | > 0.5 | 23.246 |  | PASS |
| 5.15b | positive control: lug x lug at d=-25 deg (past the stop) (mm3) | > 1 | 833.7 |  | PASS |
| 5.16 | follower bottom z (mm) | 16 | 16 | +-0.0001 | PASS |
| 5.17 | compound: follower to 36T layer, 3D distance at d=0/30/76.5 (mm) | 0.3 | 0.3 | +-0.0001 | PASS |
| 5.17b | compound: spread over the three poses (mm) | 0 | 7.10543e-15 | +-0.0001 | PASS |
| 5.17 | compound_norelief: follower to 36T layer, 3D distance at d=0/30/76.5 (mm) | 0 | 0 | +-0.0001 | PASS |
| 5.17b | compound_norelief: spread over the three poses (mm) | 0 | 0 | +-0.0001 | PASS |
| 5.18 | relief floor z = 36T top face (mm) | 15.7 | 15.7 | +-0.0001 | PASS |
| 5.19 | volume removed by the relief = no-relief solid inside annulus R>=16.5, z15.7..16 (mm3) | 287.622 | 287.622 | +-0.5 | PASS |
| 5.19b | relief solid inside that annulus (mm3) | 0 | 0.0000 |  | PASS |
| 5.20 | relief inner R16.5 margin to the follower tip circle (36.30 - 19.5 - 16.5) (mm) | 0.3 | 0.3 | +-1e-06 | PASS |
| 5.21 | follower material below z=16 (mm3) | 0 | 0 |  | PASS |
| 5.22 | pinion top face z (mm) | 16 | 16 | +-0.0001 | PASS |
| 5.23 | swept lug/fork clearance to gears, other lug, pinion, pins, bearings; min over 0..76.5 deg (mm) [need >= 1.0] | >= 1 | 10.166 |  | PASS |
| 5.24 | same minimum against the claim (>= 10.17; at d=0: follower lug -> compound gear) (mm) | 10.17 | 10.166 | +-0.01 | PASS |
| 5.26 | lug-to-lug first contact going past the closed stop (deg) [claim -21.5] | -21.5 | -21.5 | +-0.5 | PASS |
| 5.27 | lug-to-lug distance at d=0 / -10 / -20 deg, min (mm) | >= 0.1 | 2.15439 |  | PASS |
| 6.1 | compound lug angle (deg, CCW from +x) | -78.589 | -78.5887 | +-0.002 | PASS |
| 6.2 | follower lug angle (deg) | 258.589 | 258.589 | +-0.002 | PASS |
| 6.3 | mirror symmetry: angle_c + angle_f = 180 mod 360 (deg) | 180 | 180 | +-0.002 | PASS |
| 6.4 | crank radius compound (mm) | 53 | 52.9997 | +-0.001 | PASS |
| 6.5 | crank radius follower (mm) | 53 | 52.9997 | +-0.001 | PASS |
| 6.6 | placed pivots mirror about x=0: x_c + x_f (mm) | 0 | 0 | +-0.002 | PASS |
| 6.7 | placed pivots mirror about x=0: y_c - y_f (mm) | 0 | 0 | +-0.002 | PASS |
| 6.8 | placed compound pivot vs GRIPV7 four-bar crank pin, distance (mm) | 0 | 0.000405572 | +-0.002 | PASS |
| 6.9 | GRIPV7 crank radius R (mm) | 53 | 53 | +-1e-09 | PASS |
| 6.10 | GRIPV7 closed crank angle (deg) | -78.589 | -78.589 | +-1e-09 | PASS |
| 6.11 | info: his lugs compound -31.2258, follower 209.8829 (mirror error -1.3428 deg) | info | info |  | PASS |
| 7.1 | compound z=3 (bearing pocket level): section loops (7 holes + 1 core) | 7 + 1 | 7 + 1 |  | PASS |
| 7.2 | compound: ligament hole -> Ø14.075 pocket wall (mm) [claim 3.66] | 3.6625 | 3.6625 | +-0.01 | PASS |
| 7.3 | compound z=3 (bearing pocket level): ligament hole -> 36T root circle (mm) [claim 2.43] | 2.425 | 2.42501 | +-0.01 | PASS |
| 7.4 | compound z=3 (bearing pocket level): ligament hole -> hole (mm) [claim 2.49] | 2.4917 | 2.49172 | +-0.01 | PASS |
| 7.5 | compound z=3 (bearing pocket level): minimum ligament vs 2.0 (mm) | >= 2 | 2.42501 |  | PASS |
| 7.1 | compound z=10: section loops (7 holes + 1 core) | 7 + 1 | 7 + 1 |  | PASS |
| 7.2b | compound: ligament hole -> Ø8.30 shoulder (mm) | >= 6 | 6.55 |  | PASS |
| 7.3 | compound z=10: ligament hole -> 36T root circle (mm) [claim 2.43] | 2.425 | 2.42501 | +-0.01 | PASS |
| 7.4 | compound z=10: ligament hole -> hole (mm) [claim 2.49] | 2.4917 | 2.49172 | +-0.01 | PASS |
| 7.5 | compound z=10: minimum ligament vs 2.0 (mm) | >= 2 | 2.42501 |  | PASS |
| 7.1 | compound_norelief z=3 (bearing pocket level): section loops (7 holes + 1 core) | 7 + 1 | 7 + 1 |  | PASS |
| 7.2 | compound_norelief: ligament hole -> Ø14.075 pocket wall (mm) [claim 3.66] | 3.6625 | 3.6625 | +-0.01 | PASS |
| 7.3 | compound_norelief z=3 (bearing pocket level): ligament hole -> 36T root circle (mm) [claim 2.43] | 2.425 | 2.42501 | +-0.01 | PASS |
| 7.4 | compound_norelief z=3 (bearing pocket level): ligament hole -> hole (mm) [claim 2.49] | 2.4917 | 2.49172 | +-0.01 | PASS |
| 7.5 | compound_norelief z=3 (bearing pocket level): minimum ligament vs 2.0 (mm) | >= 2 | 2.42501 |  | PASS |
| 7.1 | compound_norelief z=10: section loops (7 holes + 1 core) | 7 + 1 | 7 + 1 |  | PASS |
| 7.2b | compound_norelief: ligament hole -> Ø8.30 shoulder (mm) | >= 6 | 6.55 |  | PASS |
| 7.3 | compound_norelief z=10: ligament hole -> 36T root circle (mm) [claim 2.43] | 2.425 | 2.42501 | +-0.01 | PASS |
| 7.4 | compound_norelief z=10: ligament hole -> hole (mm) [claim 2.49] | 2.4917 | 2.49172 | +-0.01 | PASS |
| 7.5 | compound_norelief z=10: minimum ligament vs 2.0 (mm) | >= 2 | 2.42501 |  | PASS |
| 7.7 | tangential tooth force at 6 V stall, 11.0 kg cm (N) [claim ~80] | 80 | 79.9333 | +-1.5 | PASS |
| 7.8 | 7 x Ø12 @ R16.7: spoke w 2.49 mm, 18.5 N/spoke; bending cantilever / fixed-guided, shear, rim-bridge (MPa) | < 22.5 | 13.4 / 6.7 / 0.69 / 5.6 |  | PASS |
| 7.8 | 6 x Ø12 @ R16.08 (balanced): spoke w 4.08 mm, 22.4 N/spoke; bending cantilever / fixed-guided, shear, rim-bridge (MPa) | < 22.5 | 6.0 / 3.0 / 0.51 / 3.5 |  | PASS |
| 7.8 | 6 x Ø12 @ R16.7: spoke w 4.70 mm, 21.5 N/spoke; bending cantilever / fixed-guided, shear, rim-bridge (MPa) | < 22.5 | 4.4 / 2.2 / 0.43 / 5.6 |  | PASS |
| 7.9 | 7 x Ø12 safety factor, conservative cantilever bound (allowable 22.5 MPa) | >= 1.5 | 1.68147 |  | PASS |
| 7.10 | 7 x Ø12 safety factor, rim bridge over a hole | >= 1.5 | 4.04259 |  | PASS |
| 7.11 | 6 x Ø12 (balanced) spoke bending stress lower than 7 x Ø12 | lower | 6.0 vs 13.4 MPa |  | PASS |
| 7.12 | info: mass cost of 6 holes instead of 7 (g, 16 mm PETG) | info | 2.30 g more |  | PASS |
| 8.1 | pinion STEP re-export + reimport: valid, 1 solid | True, 1 | True, 1 |  | PASS |
| 8.2 | pinion round-trip volume relative difference | 0 | 6.3473e-15 | +-1e-06 | PASS |
| 8.3 | pinion round-trip bbox max difference (mm) | 0 | 0 | +-0.0001 | PASS |
| 8.1 | compound STEP re-export + reimport: valid, 1 solid | True, 1 | True, 1 |  | PASS |
| 8.2 | compound round-trip volume relative difference | 0 | 1.8323e-12 | +-1e-06 | PASS |
| 8.3 | compound round-trip bbox max difference (mm) | 0 | 7.10543e-15 | +-0.0001 | PASS |
| 8.1 | compound_norelief STEP re-export + reimport: valid, 1 solid | True, 1 | True, 1 |  | PASS |
| 8.2 | compound_norelief round-trip volume relative difference | 0 | 1.83806e-12 | +-1e-06 | PASS |
| 8.3 | compound_norelief round-trip bbox max difference (mm) | 0 | 7.10543e-15 | +-0.0001 | PASS |
| 8.1 | follower STEP re-export + reimport: valid, 1 solid | True, 1 | True, 1 |  | PASS |
| 8.2 | follower round-trip volume relative difference | 0 | 3.19941e-16 | +-1e-06 | PASS |
| 8.3 | follower round-trip bbox max difference (mm) | 0 | 0 | +-0.0001 | PASS |
| 8.4 | pinion STL closed 2-manifold: edges not shared by exactly 2 triangles | 0 | 0 |  | PASS |
| 8.5 | pinion STL signed volume positive (outward normals) | > 0 | 8023.4 |  | PASS |
| 8.6 | pinion STL volume vs STEP volume (relative) | 0 | 9.50574e-05 | +-0.001 | PASS |
| 8.7 | pinion STL z-min on the bed (mm) | 0 | 1e-07 | +-0.001 | PASS |
| 8.8 | pinion STL height = STEP z-extent, gear axis vertical (mm) | 16 | 16 | +-0.05 | PASS |
| 8.9 | pinion STL x-extent vs STEP (mm) | 29.7845 | 29.7845 | +-0.05 | PASS |
| 8.10 | pinion STL y-extent vs STEP (mm) | 30 | 29.9994 | +-0.05 | PASS |
| 8.4 | compound STL closed 2-manifold: edges not shared by exactly 2 triangles | 0 | 0 |  | PASS |
| 8.5 | compound STL signed volume positive (outward normals) | > 0 | 44692.8 |  | PASS |
| 8.6 | compound STL volume vs STEP volume (relative) | 0 | 0.00017852 | +-0.001 | PASS |
| 8.7 | compound STL z-min on the bed (mm) | 0 | 1e-07 | +-0.001 | PASS |
| 8.8 | compound STL height = STEP z-extent, gear axis vertical (mm) | 36 | 36 | +-0.05 | PASS |
| 8.9 | compound STL x-extent vs STEP (mm) | 56.967 | 56.967 | +-0.05 | PASS |
| 8.10 | compound STL y-extent vs STEP (mm) | 89.5859 | 89.5831 | +-0.05 | PASS |
| 8.4 | compound_norelief STL closed 2-manifold: edges not shared by exactly 2 triangles | 0 | 0 |  | PASS |
| 8.5 | compound_norelief STL signed volume positive (outward normals) | > 0 | 44978.6 |  | PASS |
| 8.6 | compound_norelief STL volume vs STEP volume (relative) | 0 | 0.000218629 | +-0.001 | PASS |
| 8.7 | compound_norelief STL z-min on the bed (mm) | 0 | 1e-07 | +-0.001 | PASS |
| 8.8 | compound_norelief STL height = STEP z-extent, gear axis vertical (mm) | 36 | 36 | +-0.05 | PASS |
| 8.9 | compound_norelief STL x-extent vs STEP (mm) | 56.967 | 56.967 | +-0.05 | PASS |
| 8.10 | compound_norelief STL y-extent vs STEP (mm) | 89.5859 | 89.5831 | +-0.05 | PASS |
| 8.4 | follower STL closed 2-manifold: edges not shared by exactly 2 triangles | 0 | 0 |  | PASS |
| 8.5 | follower STL signed volume positive (outward normals) | > 0 | 22739.8 |  | PASS |
| 8.6 | follower STL volume vs STEP volume (relative) | 0 | 7.58699e-05 | +-0.001 | PASS |
| 8.7 | follower STL z-min on the bed (mm) | 0 | 1e-07 | +-0.001 | PASS |
| 8.8 | follower STL height = STEP z-extent, gear axis vertical (mm) | 20 | 20 | +-0.05 | PASS |
| 8.9 | follower STL x-extent vs STEP (mm) | 39.1324 | 39.1324 | +-0.05 | PASS |
| 8.10 | follower STL y-extent vs STEP (mm) | 80.5989 | 80.5961 | +-0.05 | PASS |
| 8.11 | pinion mass, PETG 1.27 g/cc (g) [json] | 10.19 | 10.1907 | +-0.02 | PASS |
| 8.11 | compound mass, PETG 1.27 g/cc (g) [json] | 56.77 | 56.77 | +-0.02 | PASS |
| 8.11 | compound_norelief mass, PETG 1.27 g/cc (g) [json] | 57.14 | 57.1353 | +-0.02 | PASS |
| 8.11 | follower mass, PETG 1.27 g/cc (g) [json] | 28.88 | 28.8818 | +-0.02 | PASS |
| 8.12 | gear set mass, new vs his (g) | new < his | new 95.84, his 157.41 |  | PASS |
| 8.13 | pinion: fresh build vs delivered STEP, volume difference both ways (mm3) | 0, 0 | -0.0000, 0.0000 | +-0.05 | PASS |
| 8.13 | compound: fresh build vs delivered STEP, volume difference both ways (mm3) | 0, 0 | 0.0000, 0.0000 | +-0.05 | PASS |
| 8.13 | compound_norelief: fresh build vs delivered STEP, volume difference both ways (mm3) | 0, 0 | 0.0000, 0.0000 | +-0.05 | PASS |
| 8.13 | follower: fresh build vs delivered STEP, volume difference both ways (mm3) | 0, 0 | -0.0000, 0.0000 | +-0.05 | PASS |
