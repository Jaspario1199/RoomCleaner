# Independent check: `calculations/winch_gear3.py` (D40, 3:1 spur winch stage)

Checker: calculation-checker (read-only). Date 2026-10-23. Reviewed: `calculations/winch_gear3.py`, `.json`, `.md` (including the two
rows the lead added after the review started: `drive.step_sign`, `encoder.sign`), `cad/params.py` WG3_* block,
`cad/WINCH_GEAR3_SPEC.md`, `calculations/lift_chain_weakest_link.py` (WL), `calculations/simulation_loads.py` (S),
`verification/winch_gear3_build_notes.md`, `roomcleaner/cdpr/config.py`, `roomcleaner/cdpr/station_core.py`, `firmware/winch_station/*`.
Scratch scripts: `scratchpad/check1.py` ... `check5.py` (not in the repo). Nothing in the repo was edited.

## 0. Verdict

The arithmetic is right and reproducible: `build()` reproduces the stored JSON exactly (0 mismatches), every number in the `.md` matches
the JSON, the efficiency direction is right, units are consistent, and every geometric number is read from `cad/params.py`. All
D39 pass verdicts survive my recomputation. What I disagree with is the **load cases and the margins quoted**, not the equations:

- 0 findings rated high (no PASS flips to FAIL under any recomputation I ran).
- 6 medium: capacity headline (full-step torque, speed), wall-screw row on the old load point, shaft/bearing load case and the seat
  loads handed to Jasper, tooth-check load basis and missing stress concentration, set-screw friction values, encoder tolerance budget.
- 6 low: Hertz contact, single efficiency, hard-coded/duplicated values and a wrong source tag, motor-shaft presentation,
  step_sign/encoder.sign wording, unreferenced links (spool body, tie-off).

## 1. Facts, assumptions, derived results, uncertainty

### 1.1 Supplied facts (recorded in the repo; I take them as given)

| Fact | Value | Where |
|---|---|---|
| Ratio, module, pressure angle, teeth, face | 60/20 = 3.00, m 1.0, 20 deg, 20T/60T, 10 mm | `P.WG3_*` |
| Centre distance | 40.20 (40.00 + 0.20) | `P.WG3_CD` |
| Bearing seats / spool sections (y, mm) | bearings 0-5 and 44-49 (centres 2.5, 46.5); gear 10.825-20.825; drum 20.825-36.825 | `P.WG3_BRG_*`, `WG3_Y_*` |
| Spool shaft | Ø7 steel dowel | `P.WG3_SHAFT_D` |
| Motor | 36 N.cm at 1.5 A (S), x40/36 for a 40 N.cm nameplate (USER, unverified); torque linear in current; R_phase 1.8 ohm | S, WL |
| Running fraction, skip margin | 0.7, 1.5 | `S.RUN_FRAC`, `S.SKIP_SF` |
| Spool radii | 7.5 mm core, 10 mm full | `S.R_EMPTY/R_FULL` |
| Fleet limit | 26.05 deg (factor 1.1136) | `S.fleet_limit_deg()` |
| A4988 R_sense | 0.100 ohm (red R100) | `S.R_SENSE` |
| Drive wiring | full-step, `microsteps: 1` ("Rev C wiring: MS1-3 low = full step") | `config.py:208` |
| Supply | 12 V | `docs/SHOPPING_LIST.md` |
| Rule | every link >= 1.5 x the motor's upper slip force | D39 |
| Backlash | 0.246 mm transverse at the pitch circle = 2(0.20)tan20 + 0.10 = 0.2456 (I reproduce it) | build notes |
| Max cable speed | 0.05 m/s | `config/robot.sim.json` `max_cable_speed_m_s` |
| Pinion rotates +, gear rotates -1/3 | opposite sense | build notes, "Phasing" row |

### 1.2 Assumptions made in the calc (tagged ASSUMED; none has an approval record beyond the D39/D40 text)

eta = 0.90 each direction; warm factor 0.85 (WL); PETG allowable 22.5 MPa x 0.85 = 19.1 MPa; Lewis Y table (0.320/0.422);
C0(687) = 600 N; dowel yield 350 MPa; motor radial limit 28 N at 20 mm; friction coefficients and seating torque inside
`WL.setscrew_joint` (mu 0.20 tip, 0.25 bore, K 0.20, seating 3-4 in-lb, bite 1.15); 4 full steps per skip; tracking tolerance 20 counts.

### 1.3 Unresolved uncertainty (not resolvable on paper)

Real mesh/bearing efficiency; the motor's true torque (36 vs 40 N.cm, and the full-step 0.707 vector); steel-on-steel friction of the
pinion joint; real C0 of the purchased 687s and yield of the dowel; the radial limit of Jasper's actual motor; pull-out torque at
191 rpm on 12 V; AS5600 INL as mounted; which side of the drum the new cable leaves from (needed for step_sign).

## 2. Agree/disagree on each result

| Result | Doc | Mine | Verdict |
|---|---|---|---|
| Vref (8 I R_sense) | 0.80 / 1.20 V | 0.80 / 1.20 V | agree |
| Hold, hold x40/36 | 0.240/0.267 ; 0.360/0.400 N.m | same | agree |
| Running pull at full spool (driving, x eta) | 45.4 / 68.0 N | 45.36 / 68.04 | agree (direction right) |
| Capacity | 2.80 / 4.20 kg (1.56 direct) | 2.80 / 4.20 nominal; **1.98 / 2.97 with full-step vector** | agree arithmetic, **disagree on headline (F1)** |
| Fuse lower (eta = 1, x0.707) | 67.9 / 101.8 N | same | agree |
| Fuse upper (back-driven, /eta, x1.1136) | 131.9 / 197.9 N | same | agree (conditional on eta, F8) |
| Parts must hold (1.5 x) | 197.9 / 296.8 N | same | agree |
| Heat I^2 R | 1.80 / 4.05 W | same | agree |
| Tooth force F_t | 26.7 N (pinion side) | 26.67 pinion side; **29.63 spool side** | **disagree on basis (F4)** |
| Lewis sigma, 60T | 6.32 MPa, ratio 3.03 | 6.32 ; spool side 7.02, ratio **2.72** | arithmetic agree, basis disagree |
| Set screw torque | 0.666-0.888 N.m, 2.50 | same arithmetic | agree arithmetic; **friction values (F6)** |
| Shaft M, sigma, ratio | 1461 N.mm, 43.4 MPa, 8.06 | same at mid-plane; **worst over drum width 1537 N.mm, 45.7 MPa, 7.67** | agree, load case incomplete (F3) |
| Bearing reactions near/far | 63.9 / 82.7 N | same at mid-plane; **87.0 / 106.6 N worst** | agree, load case incomplete (F3) |
| Seat loads for Jasper | 96 / 124 N | **130 / 160 N** (envelope) | **disagree (F3)** |
| Motor shaft radial | 6.4 N run, 28.4 N slip, 42.6 N at 1.5 A | same | agree |
| Skip / backlash | 27.3 counts / 5.3 counts | same | agree |
| Steps/s, rpm, mm per step | 637 (477 full) , 191 rpm, 0.0785 mm | same | agree |
| Knot | 2.02 | 266.9 / 131.9 = 2.02 | agree |
| Wall screws, one column | 4.03 | **2.91** at the new load point | **disagree (F2)** |
| `.md` vs `.json` | | every table and prose number matches | agree |

## 3. Findings

### F1 (medium): capacity headline ignores the full-step torque factor the repo already flags, and the 0.7 running fraction is carried to 3x the motor speed

Evidence.
- `config.py:208`: `microsteps: int = 1  # Rev C wiring: MS1-3 low = full step`; `robot.example.json` has `"microsteps": 1` for all four stations.
  `docs/decisions/WINCH_CAPACITY_20261021.md` (update note) says that in full-step mode the A4988 drives both coils at about 0.71 x I_trip and
  "would cut every pull number above by up to about 30 %". WL applies the same factor (`VECTOR_LOW`) to the lower fuse bound, so the calc uses it on
  one side only.
- `winch_gear3.py:at_current` computes capacity from the nominal `hold`, with no `VECTOR_LOW`.
- RUN_FRAC 0.7 was set for the direct-drive winch at 50 mm/s: 212 steps/s = 64 rpm. Geared it is 637 steps/s = 191 rpm on a 12 V supply.

Expected vs computed (1.0 A / 1.5 A): capacity 2.80 / 4.20 kg (doc); with the 0.707 vector 1.98 / 2.97 kg, i.e. +32 % / +98 % on 1.50 kg instead of
+87 % / +180 %. The same basis puts the direct-drive baseline at 1.10 kg, so the gain (x1.8) is unchanged. Pull-out torque at 191 rpm and 12 V is
below the low-speed figure; I did not quantify it and the repo has no curve. The conclusion (capacity > 1.50 kg at 1.0 A) survives, but the md's
"almost twice the needed capacity" becomes about 1.3x, and a speed derate of 0.8 would leave about 1.6 kg.

Fix. Add a `capacity_low_kg` column (x `WL.VECTOR_LOW`) to `at_current`, the JSON and the md table, state D40's rationale as "1.98 to 2.80 kg", and put
"pull test at 50 mm/s, 191 rpm" into the bench test in place of the 0.7 assumption.

### F2 (medium): the wall-screw row reuses the old drum's load point

Evidence. `build()` takes `WL.build()["wall"]["per_case"][worst]["f_design_one"]`. WL's load points come from `S.tangent_point`
(drum mid-plane y = 18.0, spool axis on the motor axis, z about 0). The new spool axis is 40.20 mm below the motor axis (`P.WG3_CD`) and the drum
mid-plane is y = 28.825. I re-solved the one-stud-column screw model with the point moved (`check4.py`):

| case | f_design_one old | new point | ratio old | ratio new |
|---|---|---|---|---|
| D1 straight down | 551 N | 551 | 4.18 | 4.18 |
| D2c floor diagonal | 531 | 928 | 4.03 | 7.04 |
| D3 scan straight out | 656 | **384** | 4.98 | **2.91** |
| D4f along the wall | 626 | 390 | 4.74 | 2.95 |

The governing case changes from D2c to D3 and the ratio from 4.03 to 2.91. Still PASS, but the table overstates the margin by 28 % and the lever
arm (about 40 mm lower) is exactly what Jasper is about to change by redesigning the slide-in and mount.

Also: the table lists only the knot and wall screws. The other WL links against the new 131.9 N fuse (WL "lower" / 131.9): claw eye 7.7, motor
screws 23.6, wall-plate head punch 41.7, dovetails 101: all pass and should be listed so the claim "every part must hold 198 N" is backed. The
motor tab and motor-shaft links of WL no longer carry the cable; say so.

Fix. Move the load point in the wall-screw solve (or parameterise `S.tangent_point` by spool-axis offset and drum y), list the remaining WL links,
and re-run after Jasper fixes the mount geometry.

### F3 (medium): shaft/bearing load case omits the cable's travel along the drum and the axial component; the seat loads handed to Jasper are low

Evidence (`check2.py`, `check3.py`). `spool_shaft` places the cable at the drum mid-plane (y 28.825) and takes its magnitude as 131.9 N, radial.
- The line winds across the whole 16 mm drum (y 20.825 to 36.825), so the load point moves. Scanning it over the width and over every reachable
  in-plane direction (0-84 deg from straight down, mesh sign fixed by torque balance), the worst case is the cable straight down: near bearing
  **87.0 N** (cable at the gear side), far bearing **106.6 N** (cable at the flange side), bending moment **1537 N.mm** (sigma 45.7 MPa, ratio 7.67).
  The doc has 63.9, 82.7, 1461 N.mm, 8.06.
- The "Limits" line "the real cable angle lowers it" is true for angle (straight down is the worst direction), but not for position.
- Seat loads quoted to Jasper (1.5 x reactions): 96 N near, 124 N far. With the envelope: **130 N near, 160 N far**. If only the in-plane share
  (cos 26 deg) is counted as radial, the far seat is about 144 N: still above 124 N.
- Bearing static ratio becomes 600 / 106.6 = 5.6 (still PASS).
- The fleeted line also pulls axially: T sin(26.05 deg) = **57.9 N** at 1.0 A (87 N at 1.5 A). The calc does not mention it. It goes through a
  bearing outer race into Jasper's seat shoulder, so the cheeks need axial retention. P0 = 0.6 Fr + 0.5 Fa stays small against C0, so the bearing is
  not at risk.

Fix. Scan `y_cable` over [P.WG3_Y_TEETH1, P.WG3_Y_DRUM1] in `spool_shaft`, report the envelope reactions, give Jasper 130 / 160 N radial and
>= 58 N axial (1.5 x = 87 N), and delete or correct the "angle lowers it" sentence. The search at the load points only is sufficient inside any single
load case (moment is piecewise linear per plane and the norm of a linear function is convex; dense scan: 1460.8 vs 1461.4 N.mm), so no change there.

### F4 (medium): the printed-tooth check uses a different (lower) load than the shaft check and has no stress-concentration allowance

Evidence.
- `gear_teeth` uses `f_t = hold_hi / r_p` = 26.67 N (pinion side). `spool_shaft` uses `hold_hi * N / eta / r_gear` = 29.63 N (spool side, from torque
  balance on the spool). The gear teeth see the larger one in the back-driven slip case: sigma = 29.63 / (10 x 1.0 x 0.422) = 7.02 MPa, ratio
  **2.72** (not 3.03); at 1.5 A 1.82 (not 2.02).
- The Lewis Y values are right (Shigley 0.322 / 0.421), the formula sigma = F_t / (b m Y) is dimensionally right (N/mm^2 = MPa) and the face (10 mm) is
  read from params. Lewis excludes root stress concentration (Kf 1.5-2), the 0.10 mm tooth thinning (about 10-12 % less root section), misalignment
  and dynamic factors. With Kf = 1.8 on the spool-side load the ratio is 1.51 at 1.0 A and 1.01 at 1.5 A; with thinning also, 1.33 at 1.0 A.
- Mitigating: the allowable (22.5 x 0.85) is already half the UTS, and the teeth are printed with layers in the gear plane (bending along the
  layers, the strong direction). Against the warm UTS (45 x 0.85) even Kf = 1.8 gives about 3. So this is not a likely failure, but the "3.03"
  reads as a margin to failure and is not.
- Which member is critical: the printed 60T gear is. The steel pinion is not checked in the calc; I confirm it need not be (Lewis stress 8.3 MPa
  pinion side / 9.3 MPa spool side against a steel allowable of order 100+ MPa, under 10 % utilised), but the calc should say so and the purchase spec must
  say steel (sintered or brass 20T M1 pinions are sold in the same sizes).

Fix. Use the spool-side tangential force for the printed gear, include Kf (1.5-2.0) and the thinning in the stress, state the allowable basis
(half UTS, warm) in the md, and add one sentence on the pinion. Because the margin to the 1.5 rule is sensitive to Kf, a printed-tooth static
test belongs in the pull test.

### F5 (low): Hertz contact stress is not computed

Estimate (`check1.py`): spool-side F_t 29.6 N, normal 31.5 N, pitch-point radius of relative curvature 2.565 mm, b = 10 mm, E* about 2.1 GPa (steel on
PETG E 1800 MPa): p_max = 28.6 MPa at the 1.0 A slip, 35 MPa at 1.5 A. Against a warm compressive strength of about 42 MPa (50 MPa x 0.85, typical value,
not verified in the repo) the force ratio is (42.5/28.6)^2 = 2.2 at 1.0 A and 1.5 at 1.5 A. Passes at 1.0 A, marginal at 1.5 A. The md's Limits mention wear and
creep but not this number.

Fix. Add the Hertz line (a three-line formula) and the stated compressive allowable.

### F6 (medium): pinion set screw: right structure, wrong friction values for a steel hub, and no sensitivity

Is `WL.setscrew_joint` the right model for a purchased steel hub? The structure is: screw force from seating torque, times a friction lever
(r_flat = 2.0 mm at the screw tip on the flat, r_bore = 2.5 mm opposite). The calc reads only `lever_mm` and `f_seat_steel`, so the PETG hub-wall and
strip terms are correctly unused. But:
- `MU_BORE = 0.25` is tagged in WL as "steel shaft on the PETG bore". For a steel bore it is steel on steel, dry or with the motor's anticorrosion oil:
  0.10-0.20. `MU_TIP = 0.20` (steel cup on steel flat, dry) is also optimistic for an oiled shaft.
- Sensitivity (1.0 A / 1.5 A ratio to the motor's upper torque): mu 0.20/0.25 gives 2.50 / 1.66 (doc); 0.20/0.20 gives 2.19 / 1.46; 0.15/0.15 gives
  **1.64 / 1.10**; 0.10/0.10 gives 1.10 / 0.73. The 1.5 A ratio already falls below 1.5 at mu 0.2/0.2.
- Offsetting conservatism, none quantified: `K_NUT = 0.20` is a cap-screw value, a headless set screw has no under-head friction (K about 0.12-0.15
  gives 1.3-1.7 x the seat force); the 3-4 in-lb seating torque is on the low side for an M3 set screw (catalogues give roughly 0.6-1 N.m, from
  memory, not verified); and the model ignores the positive engagement of the flat: its half-width is 1.5 mm and the ramp at the flat edge is
  36.9 deg, so a slipping screw tip must climb the edge. The real joint is probably stronger, but this is unmeasured.

Fix. Give the steel-hub mu a range (0.10-0.20) and report the ratio range, not 2.50; mark 2.50 as an upper case. Put a torque-slip test of the
pinion on the shaft (torque wrench, motor shaft locked) into the pull test, specify retaining compound on the screw, and state the 1.5 A ratio as
marginal at low friction.

### F7 (medium): encoder tolerance of 20 counts has no error budget and only 7 counts of detection margin

Evidence. Skip 27.3 counts, tolerance 20, so detection margin 7.3 counts = 0.64 deg at the spool. Error sources that are not in the md number:
command quantisation 4096/600 = 6.83 counts per full step (firmware `checkTracking` compares against `pos x cpr / usteps_per_rev`, so a step is a
6.8-count jump); rotor lag up to one full step before pull-out (6.8 counts); gear backlash 5.3 counts after a reversal; AS5600 INL about 0.5 deg
or more as mounted (5.7-11 counts, datasheet from memory, check; the repo's `encoder1021_verification.md` only says "extra INL"). A worst-case
persistent sum is in the range 18-29 counts, which spans the 20-count tolerance. The old scheme had the same tolerance-to-step ratio (60 / 20.5 = 2.93
and 20 / 6.83 = 2.93), but the sensor INL did not scale down with the gear: it was 10-18 % of the old tolerance and is 28-55 % of the new one.
The tracking dwell (`tracking_dwell_s`) helps with transients but not with a persistent offset.

Fix. Add a budget table; log `terr` on the bench at rated pull in both directions before fixing the number; consider 22-24 counts if the false-trip
side dominates, and verify the skip is still detected (27.3 +/- sensor error).

### F8 (low): one efficiency for both roles; the sensitivity is not shown

Direction check. Capacity uses `x eta` (driving), fuse upper uses `/ eta` (back-driven) and fuse lower uses eta = 1. All correct, and a lower eta
is conservative for both (lower capacity, higher fuse). The value is the issue: eta 0.9 is a single assumed number. Fuse upper: 118.7 N at eta 1.0,
125.0 at 0.95, 131.9 at 0.90, 148.4 at 0.80, 169.6 at 0.70 N (1.0 A); capacity 3.11 / 2.96 / 2.80 / 2.49 / 2.18 kg. The knot (lower bound 266.9 N) is
the weakest listed link and passes 1.5 x only while eta >= 0.67 (ratio 2.02 now, 1.80 at 0.80, 1.57 at 0.70). Plain bearings and meshes in
printed gear sets are often 0.93-0.97, so 0.9 is reasonable but unmeasured.

Fix. Print the 0.7-1.0 sensitivity in the md next to the assumed value; the pull test (D39) replaces eta.

### F9 (low): hard-coded and duplicated values, and one wrong source tag

The calc does take its geometry from `cad/params.py` (ratio, module, teeth, face, pressure angle, bearing y, drum/gear y, shaft diameter) and its motor,
radii, skip margin, running fraction, fleet factor, warm factor, vector factor, cup bite and pass ratio from S and WL. Exceptions:
- `direct = dict(capacity_kg=1.56, ...)` is a typed number; the computed value is 1.5555. Use `S.tension_cases(1.5)["work_margin"] / (K_TENSION * G)`.
- `K_TENSION = 1.101` and `NEEDED_KG = 1.50` duplicate the inline literals in WL (`JEANS_PEAK = 1.50 * 1.101 * G`); neither is exported, so there are
  two independent definitions of the repo's most-used loading number. Export one constant from WL or S.
- `G = 9.81` (S.G, WL.G exist); `PETG_ALLOW = 22.5 * ...` duplicates `S.Z_STRENGTH` / `WL.PETG_LAYER`; `MOTOR_RADIAL_N = 28.0` duplicates
  `WL.RADIAL_RATING`; `SHAFT_SY = 350` equals `WL.SHAFT_SY[0]` (different part, same value, label it); `CPR = 4096` duplicates
  `EncoderConfig.counts_per_rev`; `200` full steps per revolution is typed four times; `tol = 20` is typed.
- `backlash_mm = 0.246` is copied from the build notes. It is derivable from params: `2 * P.WG3_CD_ALLOW * tan(P.WG3_PRESSURE_ANGLE_DEG) +
  P.WG3_GEAR_TOOTH_THIN - P.WG3_PINION_TOOTH_THIN` = 0.2456.
- `LINE_SPEED = 0.050  # [REPO REQUIREMENTS]`: `REQUIREMENTS.md` has no 50 mm/s. The repo value is `config/robot.sim.json`
  `max_cable_speed_m_s: 0.05` (also quoted in `verification/design_review_gen2.md`). Re-tag it.
- `build()` calls `WL.build()` twice for one number (cost only).

### F10 (low): motor-shaft radial load

Numbers agree (28.38 N at 1.0 A slip, 6.39 N running, 42.57 N at 1.5 A; 19.0 mm arm from `P.WG3_*`). Presentation: the md says "about the
catalogue life limit"; the ratio is 1.01 at 1.0 A and 1.52 at 1.5 A against 28 N at 20 mm (the 19 mm arm is slightly kinder). The statement that
short peaks at a slip do no harm is a judgement with no source in the repo; it is reasonable (life rating, rare event), but a motor that is
retried against a hung claw would see the peak repeatedly. The calc does not re-check the motor shaft's strength under the new load. Using
WL's section modulus (10.3 mm3) and a 22 mm lever to the front bearing: sigma = 28.4 x 22 / 10.3 = 60.7 MPa against 350 (5.8 x), front bearing
reaction 49 N against C0 380 N (7.7 x). Both pass.

Fix. Quote the ratio to the catalogue limit (1.01 and 1.52), add the two static lines above, and confirm the limit on Jasper's actual motor.

### F11 (low): `drive.step_sign` and `encoder.sign` rows: the claims check out; two qualifications

`step_sign`. Verified. A single external spur pair reverses the sense of rotation (build notes: "pinion rotates +, gear -1/3"). `DriveConfig.step_sign`:
"+1: positive logical step = DIR high = payout"; the firmware applies it as `sign = step_sign < 0 ? -1 : 1` in `stepgen::load`. So at the same DIR the spool now
turns the other way, and the sign flips (every committed config has +1, so the new value is -1), or one coil pair is swapped; both are equivalent.
Qualifications:
(a) the flip is right only if payout is still the same rotation sense about +y as before, i.e. the cable leaves the drum on the same tangent
side (room side, +x, hanging down). The spec says only "the cable still leaves downward"; add the exit side to the spec and the bench step;
(b) "flip" is relative to the sign the real station had when direct-driven, which is not the example configs; the bench measurement decides it.
Wrong sign shows up as an immediate TRACKING fault at the first move, which is a safe failure.

`encoder.sign`. Measuring it again is correct practice but the stated reason does not decide the sign. The old magnet cap sat beyond the +y shaft end
(shaft end y 20.825) and the new one sits beyond the +y spool-shaft end (y 55.55), so the sensor looks from the same side; if payout is the same
rotation sense, the sign should be unchanged, and it depends on the AS5600 board orientation and DIR pin. Re-measure anyway.

`full_steps_per_rev` 600. Verified: the firmware and host use it per spool revolution (`station_core.h:838`, `station_core.py:513`, `spool.py:89,161`,
`startup.py:408`), so only the config changes; `max_step_rate_hz` is in full steps because `microsteps` is 1 (637 steps/s needed, about 800 allowed).

### F12 (low): links the calc does not cover

- Torque path through the printed spool body (gear teeth to hub to drum core) at the spool-side torque 0.889 N.m: drum core shear
  1.4 MPa (J = 4734 mm^4), spokes about 7 N each, inner ring 0.07 MPa. Trivial, but the sentence "gear and drum are one part, the shaft carries no torque" rests on
  it; say so with the number.
- Spool tie-off (Ø1.4 chord hole, ligaments 1.05 mm to the bore and 1.55 mm to the core surface): load is 20-51 N with 3 dead wraps (WL capstan range 15-39 %
  of 131.9 N) and 131.9 N without. WL has no tie-off strength number and the new ligament is thin. Add one, or require the dead wraps.
- Dowel yield 350 MPa and C0 600 N are assumed. Robust: the shaft ratio stays 5.8 at 250 MPa and the bearing ratio 3.8 at C0 = 400 N (worst-case
  reaction 106.6 N). Leave tagged ASSUMED.

## 4. Direct answers to the seven questions

1. **Units and equations.** Right. Capacity (driving, x eta), fuse lower (eta = 1, x0.707), fuse upper (back-driven, /eta, x40/36, x1/cos fleet), Vref = 8 I R_sense
   = 0.8 I for R100, heat = I^2 R (full-step: 2(0.707 I)^2 R = I^2 R). Issues are only F1 and F8.
2. **Lewis.** Printed 60T is the critical member; the steel pinion need not be checked (state it). Y values and face right; load basis inconsistent with
   the shaft check, no Kf (F4); warm derate applied to a gear that may be cooler than the tab, which is conservative.
3. **Set screw.** Right structure, steel-hub friction values wrong (PETG-bore mu), so the 2.50 is an upper case (F6).
4. **Shaft.** Reaction/moment code is right (I reproduced every number; the load-point-only search is sufficient per load case, dense scan agrees);
   bearing positions come from params. The load case is incomplete in cable position along the drum and axial thrust (F3).
5. **Motor shaft radial.** Numbers right; presentation should give 1.01 / 1.52 and the static checks (F10).
6. **Encoder.** Skip 27.3, backlash 5.3, speed numbers right; tolerance 20 has no budget (F7); step_sign claim verified (F11).
7. **Provenance and md/json.** md = json on every number; geometry comes from params; typed duplicates and a wrong tag in F9; wall-screw row on the
   old geometry (F2).

## 5. What I did not do

No hardware data (no motor datasheet, no bearing datasheet, no AS5600 measurement) is in the repo, so those are flagged, not resolved. I did not run the
repo's pytest suite and did not re-derive the WL chain beyond the links this calc reuses. Typical values quoted from memory (AS5600 INL, M3 set-screw
catalogue torque, PETG compressive strength) are labelled and should be confirmed.
