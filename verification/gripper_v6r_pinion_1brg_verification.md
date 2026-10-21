# Verification: gripper_v6r_pinion_1brg (Jasper's 18T pinion + one 687 pocket)

Verifier: geometry-verifier (independent).  Date 2026-10-21.
Part under test: `exports/step/gripper_v6r_pinion_1brg.step` and `exports/stl/gripper_v6r_pinion_1brg.stl` (the files themselves, imported).
Source script (not used for any measurement): `cad/parts/gripper_v6r_pinion_bearing.py`.
Reference solids: `Simple_18T_Pinionvlast` and `06_compound_54T_24T` from `solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP`, loaded read-only with `cad/v6_loader.py` and homed by translation only (bore axis on z, stack bottom z = 0; origins read from the bore cylinders, not typed).
`verification/gripper_v6r_pinion_1brg_numbers.json` was NOT read.  The implementer's modules (`gripper_v6r_pinion_bearing.py`, `gripper_v6r_gears.py`) were NOT imported by the verification test.

Test: `tests/test_gripper_v6r_pinion_1brg_verify.py`, run `/usr/bin/python3 -m pytest -q tests/test_gripper_v6r_pinion_1brg_verify.py` (about 2.3 min): 15 passed, 1 failed (the 3.83 notch wall, item 3).
Implementer suite `/usr/bin/python3 -m pytest -q tests/test_gripper_v6r_gears.py -k 1brg`: 10 passed, 21 deselected (44 s).

## Verdict

**FAIL on one requirement number (notch wall >= 3.83 mm; measured 3.709 mm).  Everything else PASS.**
The geometry itself is a faithful copy of his pocket (all booleans against his solids are 0.000 mm3).  The 3.83 mm claim comes from a wrong notch extent (R7.80 is the X/Y bounding-box extent; the true largest notch radius is R7.916).  The pocket is Jasper's own, so the notch wall of 3.709 mm is inherent to his pocket unless the requirement is relaxed; the part does not need to be repaired to match the donor.  Decision for the lead: either correct the requirement to 3.71 mm or change the notch design; I did not repair anything.

## 1. Pocket vs donor (tolerance 0.001 mm / 0.001 mm3)

| Item | Expected | Measured | Result |
|---|---|---|---|
| Lip cylinders R7.000 (D14.000), z 0..1.95 | 8 arc faces | 8 faces, R 7.0000, z 0.000..1.950 | PASS |
| Lip arc area, new vs donor | equal within 0.001 | 79.52463015 vs 79.52463015 mm2 | PASS |
| Lip arc mid-angle vs donor | < 0.001 mm | 1.1e-10 deg | PASS |
| R0.25 relief fillets | 16 faces = 8 notches | 16 on 16 distinct axes, 8 notches (axis pairs 0.9997 mm apart) | PASS |
| Fillet axes vs donor | < 0.001 mm | 0.0000 mm max deviation; area deviation 4.6e-13 mm2 | PASS |
| Fillet axis radius | n/a | 7.6663 mm (all 16) | info |
| Pocket bore R7.0375 (D14.075), z 1.95..7.00 (5.05 deep) | 7.0375, 5.05 | R 7.0375, z 1.950..7.000 | PASS |
| Floor | flat plane z = 7.000, annulus R4.15..R7.0375 | one planar face at z 7.000, area 101.48571 vs analytic 101.48571 mm2, 2 wires | PASS |
| Floor opening D8.30 (R4.15), z 7..12 | R4.150 | R 4.1500, z 7.000..12.000 | PASS |
| Faces in the pocket zone | planes and cylinders only | no cone, torus or spline | PASS |
| Extra on-axis cylinders | none | none (only lip, pocket, D8.30, D8.00) | PASS |
| Pocket cavity z -1..7 inside R9, symmetric difference with donor | < 0.001 mm3 | 0.000 mm3 (1353.7517 vs 1353.7518 mm3) | PASS |
| Empty space z 7..12 inside R9 vs cylinder R4.15 | < 0.001 mm3 | 0.000 mm3 | PASS |
| Donor lower pocket is the 5.05 deep one (upper is 10.05 deep) | yes | lower 5.05, upper 10.05 | PASS |

## 2. Removed material (boolean against his pinion)

| Item | Expected | Measured | Result |
|---|---|---|---|
| New minus his (added material) | 0 | 0.000 mm3 | PASS |
| His minus new (removed) | pocket + D8.30 counterbore only | 766.627 mm3, bbox x,y +-7.799, z 0.000..12.000; his 8024.154 - new 7257.527 = 766.627 | PASS |
| Removed vs independently built expectation (donor cavity U cylinder R4.15 z 0..12, intersected with his pinion) | symdiff < 0.001 | 0.000 mm3 | PASS |
| Whole part rebuilt independently (his pinion minus that region) vs the exported STEP | symdiff < 0.001 | 0.000 mm3 | PASS |
| Teeth and everything outside R9 x z -1..12 | identical | symdiff 0.000 mm3 | PASS |
| R9 x z 12..17 (D8.00 servo bore z 12..16, face) | identical | symdiff 0.000 mm3 | PASS |
| D8.00 bore | R4.000, z 12..16, area 100.531 | R 4.0000, z 12.000..16.000, area 100.531 mm2, no R4.00 below z 12 | PASS |
| Tooth surface area (non-planar, beyond R9.5) | equal to his | 2254.76096 vs 2254.76096 mm2 | PASS |

## 3. Walls (dense wire sampling of z-sections, 0.004 mm spacing; BRepExtrema vertex-to-wire was unreliable here and was not used)

| Item | Expected | Measured | Tolerance | Result |
|---|---|---|---|---|
| Root circle radius (18T, m1.5) | 11.625 | 11.6250 | 0.002 | PASS |
| Pocket radius R7.0375 | 7.0375 | 7.0375 | 0.002 | PASS |
| Wall, pocket to root circle | about 4.59 (4.5875) | 4.5875 mm | 0.005 | PASS |
| Largest notch radius | stated R7.80 | **7.916** (fillet axis 7.6663 + 0.25); R7.799 is only the axis-aligned x/y extent | - | info |
| **Wall at the notches** | **>= 3.83** | **3.709 mm** (= 11.625 - 7.916) | 0.005 | **FAIL** |

Reproduce: `/usr/bin/python3 -m pytest -q tests/test_gripper_v6r_pinion_1brg_verify.py -k at_least_3p83`.
The implementer's own test uses `notch_wall > 3.5`, which passes at 3.709, so it did not catch the number.  The donor has the identical notch (same fillet axes to 0.000 mm), so this is inherent to his pocket.

## 4. Single solid, STEP round trip, STL

| Item | Expected | Measured | Result |
|---|---|---|---|
| Valid BREP, solid / shell count | valid, 1 / 1 | valid, 1 / 1 | PASS |
| Bounding box z | 0..16 | -1e-7..16.0000001 | PASS |
| Bounding box vs his pinion | equal (1e-4) | equal | PASS |
| STEP file volume / area | n/a | 7257.527 mm3 / 4344.176 mm2 | info |
| Re-export + re-import | volume, bbox agree | volume delta -6e-11 mm3, bbox equal 1e-6, symdiff 0.000 mm3 | PASS |
| STL binary, closed | every edge used once per direction with an opposite partner; 1 component | 13502 triangles, 6751 vertices, 20253 edges, no open or non-manifold edge, 1 component | PASS |
| STL Euler characteristic V-E+F | 0 (through-bore torus) | 0 | PASS |
| STL volume / area vs STEP | within 0.5 % | 7256.99 vs 7257.53 mm3 (-0.007 %); 4343.83 vs 4344.18 mm2 | PASS |
| STL print pose | z 0..16, pocket UP | z 0.000..16.000; top plane area 390.97 mm2 (STEP pocket-face 391.00), bed plane area 501.46 mm2 (STEP servo face 501.53); floor face at z 9.0 (normal +z), area within 1 % of analytic | PASS |

## 5. Mass at 1.27 g/cc

| Expected | Measured | Result |
|---|---|---|
| about 9.22 g (+-0.01) | 9.217 g from STEP; 9.216 g from STL; his pinion 10.191 g (-0.974 g) | PASS |

## 6. Meshing with exports/step/gripper_v6r_compound_36T_24T.step (and follower), centre distance 40.80 mm

Placement: `P.GRIPV6R_S_XY` / `C_XY` / `F_XY` from `cad/params.py`, rotation about the part axis then translation, pinion -2 d, compound +d, follower -d (the v6r convention in `cad/parts/gripper_v6r_gears.py`).  Exported compound bore axis checked on the origin (< 0.001 mm).

| Item | Expected | Measured | Result |
|---|---|---|---|
| Centre distance S to C | 40.80 | 40.800000 | PASS |
| Boolean common volume, pinion x compound and pinion x follower, crank offset d = -30, -15, 0, 7.5, 15, 30, 45, 60, 76.5 deg | 0 | 0.000 mm3 at all 9 poses, both gears | PASS |
| Positive control (pinion turned 3 deg off at d = 0) | overlap > 1 mm3 | 23.25 mm3 | PASS |
| Minimum distance pinion-compound at d = 0, 30, 60 | > 0 | 0.1994 mm at all three | PASS |

Poses between the sampled ones were not swept; the existing 5 deg 2D outline sweep in the implementer's suite covers those.

## 7. Engineering note: 687 floor opening vs inner ring (ASSUMPTIONS, not fit items)

Repo evidence: there is NO source for 687 inner-ring land or outer-ring shoulder dimensions.  Only comments exist: `cad/params.py:200` ("clears the inner race (VERIFY race OD ~9)", `GRIPV7_BRG_SEAT_BORE = 10.0`) and `verification/gripper_v7_verification.md` I3 (assumes land >= 9.2 mm, flagged VERIFY).  Assumed values used here: inner-ring land OD 8.5..9.0 mm; outer-ring shoulder ID 11.5..12.5 mm; bearing seated flat on the floor.

| Quantity | 8.5 land | 9.0 land |
|---|---|---|
| Floor opening D8.30 vs land | land larger by 0.10 mm radially | land larger by 0.35 mm radially |
| Floor annulus lying under the inner ring (area) | 2.64 mm2 | 9.51 mm2 |

Answer: **yes, the D8.30 opening is smaller than any plausible land (8.5..9.0, and the repo's own 9.2 guess), so the rotating pinion floor (R4.15 out to R7.0375) overlaps the stationary inner ring face by 0.10..0.35 mm (up to 0.5 mm if the land is 9.2) and would rub it** if the bearing is pushed against the floor (the pocket is 5.05 deep for a 5.00 bearing, so there is only 0.05 mm axial float).
A floor opening that contacts only the outer ring needs D >= land OD and D <= outer-ring shoulder ID: **D 9.0..11.5 mm** under these assumptions, so about **D10.0** (centre of the window; also equals the repo's `GRIPV7_BRG_SEAT_BORE`).  D10 keeps the whole outer-ring face (R5.75..R7.0) supported by the floor.  Confirm on the real bearing before choosing.
His compound has the same opening at both of its floors: the R4.15 bore runs z 7.000..24.000, i.e. the lower one-bearing floor (z 7) and the upper two-bearing floor (z 24) both have D8.30, so the same rub applies to his compound (assuming the same bearing orientation).  Reported only; not a fit/fail item.

## Notes

- `verification/imu_removal_review.md` shows as modified in `git status`; it was not touched by this verification.
- Files written by the verifier: `tests/test_gripper_v6r_pinion_1brg_verify.py`, `verification/gripper_v6r_pinion_1brg_verification.md`.  No source, export or parameter file was changed; nothing committed or pushed.

## Lead disposition (10/21)
- The notch-wall FAIL is a mis-stated claim (3.83 mm), not a defect: the true
  wall is 3.709 mm, far above the 1.2 mm minimum. Claim corrected; test now
  pins 3.709 and asserts >= 1.2. Verdict: PASS.
- Floor opening Ø8.30 (his, also in the compound at z=7 and z=24) likely
  rubs the 687 inner ring (land ~8.5–9.0, unsourced). Kept as his; Jasper to
  check by spin test or calipers; Ø10 is the outer-ring-only option.
