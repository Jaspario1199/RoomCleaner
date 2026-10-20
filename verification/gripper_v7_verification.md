# Gripper v7 gearbox -- independent geometry verification

Verifier: geometry-verifier (read-only except tests/ and verification/). Date 2026-10-20.
Reproduce: `/usr/bin/python3 -m pytest -q tests/test_gripper_v7_verify.py` (about 3-4 min: 59 pass, 8 strict-xfail
= known defects below). Implementer's suite: `/usr/bin/python3 -m pytest -q tests/test_gripper_v7.py` -> **28 passed** (230 s).

Method: every number below was measured from `exports/step/gripper_v7_*.step` (and `exports/stl`, `gripper_v7_preview.step`,
v6 `solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP`), using my own section / distance / four-bar code in
`tests/test_gripper_v7_verify.py`. Nothing was read back from `gripper_v7_numbers.json`. Design values (module, tooth
counts, link ground point ...) were typed from `cad/params.py` only as the "expected" side. The mesh/sweep code in the
part modules was not imported. xfail(strict) tests turn RED when a defect is repaired -- remove the marker then.

## Verdict: PASS WITH CONDITIONS

Geometry is valid, meshes, sweeps without interference and matches the stated kinematics, forces, masses and v6 interfaces.
Two stated claims are NOT met (5: sync-gear SF 1.997 < 2.0; 9: minimum wall >= 1.2 mm) and one real design defect was found
that the claims do not cover (follower rests with zero axial clearance on the 36T gear). Conditions are listed at the end.

## Claim-by-claim

| # | Claim | Expected | Measured | Tol. | Result |
|---|---|---|---|---|---|
| 1a | 7 printed parts, valid single solids | 7 x (valid, 1 solid, V>0) | all 7 valid, 1 solid each | - | PASS |
| 1b | STEP re-export + reimport | dV, dbbox | dV <= 1e-6 (<= 3.4e-8 vs rebuilt source); dbbox < 1e-3 | 1e-6 / 1e-3 | PASS |
| 1c | STL | watertight, V = STEP | 0 open edges all 7; dV <= 9.1e-4 (pinion) | 2e-3 | PASS |
| 1d | preview STEP | 59 solids, V_sum | 59 valid solids, sum 1,047,982.24 mm3 | 1e-6 | PASS |
| 2a | m1.5, 18T->36T, 24T/24T | tooth counts 18/36/24/24; tip R 15/28.5/19.5; root R 11.625/25.125/16.125 | 18/36/24/24; tips 15.000/28.500/(24T tip R 19.5); roots match; pitch-circle chordal tooth 2.256 (=pi m/2 - 0.10) | 0.01 / 0.02 | PASS |
| 2b | centre distances | 40.80 / 36.30 (from pocket axes) | 40.8000 / 36.3000 | 0.01 | PASS |
| 2c | min flank clearance, +-30 deg | >= 0.20 | main 0.1994, sync 0.1997 (constant for +-30 deg, the full 0..76.5 deg stroke and a 0..10 / 0..15 deg phase scan; phasing correct at all angles) | +-0.002 | PASS (zero margin: 0.6 um under 0.200 nominal) |
| 2d | 36T spoked web, rim >= 3.75 | 6 spokes, rim >= 3.75 | 6 windows, hub R11.0, window outer R19.40, rim below root 5.725 | - | PASS |
| 3a | bearing pockets | Ø14.05; depth 5.05 / 10.05 | Ø14.05 (+ Ø14.65 x 0.6 mouth relief, Ø10 seat bore); compound 1.00-6.05 and 26.95-37.00; follower 17.00-22.05 and 26.95-37.00 | 0.01 | PASS (note: 4 pockets hold the 6 bearings, 1+2 per gear) |
| 3b | 2 x Ø7 x 50 pins, >= 4 mm in each plate | 4.0 | pin vol 1924.2 (Ø7.000 x 50.000), z -4..46; seats Ø7.05 depth 4.00 in both plates; 2.0 mm blind floor in lower plate | 1e-6 | PASS |
| 3c | every bearing straddled | 6 / 6 | 6 / 6 coaxial (<1e-3) and inside the pin span | - | PASS |
| 4a | jaw travel / tips / open gap | 76.5 deg; 0; ~91.6 | 76.5 deg; closed gap 0.000 (jaw inner-face vertex x = 0.000000); open 91.648; gap monotonic (no toggle in stroke); max jaw tilt 2.59 deg | 0.2 mm | PASS |
| 4b | no interference > 0.5 mm3, >= 15 angles | <= 0.5 | 17 angles (0..76.5 step 4.78), 9 printed bodies, 36 pairs: max overlap 0.000 mm3. Positive control (jaw +6 deg) detects 50 mm3 | 0.5 | PASS (but see D1 for a zero-gap contact) |
| 4c | static check incl. hardware (closed pose) | none | only 4 x horn screw / pinion pilot 5.23 mm3 each (intended self-tap) | - | PASS |
| 5a | Lewis SF pinion 6 V | >= 2.0 | 2.087 (Ft 79.93 N, 10.78 MPa) | - | PASS |
| 5b | Lewis SF 36T 6 V | >= 2.5 | 2.550 (8.82 MPa) | - | PASS |
| 5c | Lewis SF sync 24T one-jaw 6 V | >= 2.0 | **1.997** (Ft 113.91 N, 11.27 MPa; the implementer's own json also holds 1.99706). Without the 0.95 mesh efficiency it is 1.90. Balanced-jaw case 3.99. | - | **FAIL** (by 0.15 %) |
| 6 | grip force per jaw, 4.8 V, gap 0..85 | >= 7.4 N | min 13.34 N at gap 0.6 mm; 14.1 @10, 15.0 @20, 17.2 @40, 21.1 @60, 33.4 @80, 43.6 @85 (matches the implementer's table to 0.01 N) | - | PASS (margin 1.8x; efficiency 0.95^2 and no pivot friction assumed) |
| 7a | frame <= 150 g (CAD, 1.27 g/cc) | <= 150 | lower 78.24 + upper 65.28 = **143.51 g** | - | PASS |
| 7b | printed total 332 g | 332 | 332.16 g (lower 78.24, upper 65.28, pinion 15.86, compound 63.01, follower 29.90, 2 jaw 63.73, 2 link 16.15) | 1 g | PASS |
| 7c | head 481 g incl. 148 g purchased | 480.6 | arithmetic reproduced (332.16 + 148.41 = 480.57). Pins reproduce (30.21 g). Purchased fasteners are ASSUMED figures: preview envelope volumes x 7.85 give shoulder-screw sets 21.6 g (claimed 16.6) and M3x50 ties 27.5 g (claimed 23.8), so the bottom-up head total is about 489 g (+1.8 %) | 2 % | PASS (note) |
| 8 | v6 interfaces kept | x 951.8475, z 1103.99, lower end y 786.39, insertion 42.5 | v7 preview tube axis x 951.8475, z 1103.9900 (v6 STEP 951.8475 / 1103.9899); lower end y 786.3903 (v6 786.3905); both plate sockets Ø28.84 over y 786.39..828.89 = 42.50; tube vol 73313 vs v6 73368 (cross hole) | 0.02 | PASS |
| 9 | min wall >= 1.2 mm, printability notes plausible | >= 1.2 | see W1-W5: 5 features below 1.2 mm | - | **FAIL** (walls); notes mostly plausible |

## Defects and condition items (reproducible)

**D1 (functional, not in the claims) -- follower rubs on the 36T gear.** Follower bottom face z = 17.000 sits exactly on the
36T top face z = 17.000: zero axial gap, 136 mm2 of face contact (134 mm2 at the open stop), and the two parts counter-rotate
(relative speed up to 2x). Volumetric overlap is 0, so the 0.5 mm3 interference test cannot see it. Repro:
`b=_build_bodies(0.0); b["compound"].distance(b["follower"])` -> 0.0000 (z = 17 contact points); intersect after a
0.01 mm z-shift gives 1.36 mm3 (= 136 mm2). Test: `test_follower_clears_36t_axially` (xfail). Required: an axial gap
(>= 0.3 mm) between L1 top and the follower bottom, or lower the follower race column accordingly.
All other moving pairs have clearance (min distances over 5 poses): jaw-link 0.50, jaw-compound 0.50, link-compound 0.91
(closed), link-upper plate 0.50, compound-upper 0.50, compound-lower 1.00, pinion-lower 0.15, pinion-upper 2.63,
follower-lower 0.50, follower-upper 0.50, link R-link L 4.00. The two jaw faces touch (0.00) at the closed pose by design.

**D2 (claim 5c) -- sync 24T one-jaw SF 1.997 < 2.0.** Repro: tau = 11.0*9.81/100 = 1.0791 N m; Ft = tau*2*0.95/0.018 =
113.91 N; sigma = Ft/(0.020*0.0015*0.337) = 11.267 MPa; SF = 22.5/11.267 = 1.9971. Test: `test_lewis_sync_sf_claim_ge_2` (xfail).

**Minimum wall (claim 9)** -- exact wire-to-wire distances and a morphological opening (Ø1.2 mm disc) on every horizontal band
of every part (tooth ring excluded). Link, jaw (except W4), follower, compound, lower plate (except W3) are clean.
- W1 pinion hub: the 4 x Ø1.7 horn-screw pilots at R8.0 leave **1.15 mm** to the Ø20 hub (z 22..31). `test_wall_pinion_horn_pilots*`.
- W2 upper plate: the 4 x Ø3.6 M2.5 insert holes at x = +-23.5 are **1.10 mm** from the servo cut-out wall (z 42..48); the blind
  holes also leave a 1.0 mm floor (z 42..43).
- W3 race rings / follower race column Ø9 around the Ø7.05 pin seat: **0.975 mm** radial (24.5 mm2 annulus, 0.85 mm and 16.85 mm tall).
- W4 jaw clevis boss, slot band z 22..33 (jaw z 5..15): boss R9.5 vs swept-tongue slot R8.8 leaves a **0.7 mm crescent**
  tapering to a knife edge at the A pivot (+x outer side, near (37.2, -53.2) in the closed pose). The neck between the two slots was not flagged (>= 1.2 mm).
- W5 upper-plate saddle: the Ø9.4 tie-column clearance bores cut the Ø36.8 shell, leaving **0.8-1.1 mm** ligaments next to the
  tube bore at (+-14.7, 88), (+-14.7, 112) (z 25..41) and 0.8 mm slivers at (+-23.7, 90.5) (z 25..41).
Repro: `_raster_thin(load("jaw"), 27.0)` and `_raster_thin(load("upper_plate"), 28.32)` return non-empty lists. The raster step is
0.05 mm, so 1.15-1.2 mm walls need the exact-distance tests (W1, W2). The implementer's own wall test only covers the guard strips.

**Interface / purchasing items**
- I1 Servo ear-hole pitch is 47.0 mm (copies the v6 model) but `cad/interfaces.py` SERVO_EAR_SPAN = 48.3 (delta 1.3 mm). Cut-out
  float is only +-0.6 mm, so one of the two numbers must be verified on the servo. `test_servo_ear_span_matches_interfaces_py` (xfail).
- I2 The bearing is called "607" in params, tests and the mass roll-up. 7 x 14 x 5 is a **687**; a 607 is 7 x 19 x 6 and does not fit the pockets.
- I3 The Ø9.0 race rings assume an inner-race land >= 9.2 mm (flagged VERIFY by the implementer); not checkable from CAD.

**Printability review** (plausible overall): both plates flat on their outer face, upper plate flipped in the STL (checked: z 0..30.5),
columns/guards/stubs point up -- fine. Gears with axis vertical and the lug band needing supports (compound: 21.5 mm of support under a
R61 lug) is correct. The 36T windows are bridged by the 24T underside; the span reaches about 15 mm at R19.4 (arc 20.3 minus 5 mm spoke), not "about 10 mm". The jaw
upper clevis ear (4.5 mm) bridges a slot of very roughly 16 x 20 mm over a 10 mm cavity -- not mentioned in the notes; plan supports. Jaw and link are
z-symmetric, so one printed part serves both sides (verified: mirror vs 180 deg flip, symmetric difference 0.000 mm3).

## Conditions to clear (return to implementer, then re-run this suite)
1. D1: add axial clearance between the follower bottom and the 36T top face.
2. D2: raise the sync 24T SF to >= 2.0 (e.g. face width or a documented basis) or restate the claim as 2.0 (1.997).
3. W1-W5: bring walls to >= 1.2 mm (or document an accepted exception for the non-structural W4/W5 slivers).
4. I1/I2: confirm the servo ear pitch and correct the bearing designation to 687.
5. Replace ASSUMED purchased-mass figures (shoulder screws, ties) with weighed values; head total is about 489 g, not 481 g.
