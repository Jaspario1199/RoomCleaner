# Independent check: SolidWorks thermal Study C (motor + fin + PETG slip-in at 1.5 A) and the 4 W fin sizing

Checker: calculation-checker (independent recomputation). Date: 2026-10-22.
Files reviewed (not edited): `docs/simulation/SW_THERMAL_MOTOR_ASSEMBLY.md`, `calculations/thermal_assembly_1p5a.py`,
`calculations/simulation_loads.py` section 6, `docs/simulation/SW_THERMAL_HEAT_FIN.md`, `calculations/fin_sizing_4w.py`,
`calculations/fin_sizing_4w.md`, `cad/reference/station_1021/*.step`, `DECISIONS.md` D37.

## Verdicts

| Item | Verdict |
|---|---|
| Study C answer sheet values (section 0, section 7) versus the script | **PASS** (every number reproduced; script calls the model correctly at 1.5 A) |
| Study C manual as a set of expectations for the SolidWorks run | **PASS WITH CONDITIONS**: 3 errors must be fixed before the user runs it (F1 to F3), 4 more should be (F4 to F7) |
| `fin_sizing_4w` (script and .md) | **PASS WITH CONDITIONS**: headline claims hold; one model artefact, one wrong sentence and one traceability gap to fix (section 8) |

Evidence labels used below: SUPPLIED (given by the repo or the user), ASSUMED (flagged assumption in the repo), DERIVED (calculated from those),
MEASURED-STEP (measured by me from the STEP files), CHECK (my own recomputation), UNRESOLVED.

## 1. What I did

1. Ran `calculations.thermal_assembly_1p5a` and compared its output with every number in the manual (section 3 below).
2. Re-implemented the network and the quasi-1D fin with my own code and solver (no import from `calculations/`): it matches the repo to 0.1 to 0.2 K.
3. Measured the STEP parts (areas, gaps, contact faces, fin and shell geometry) with CadQuery / OCC.
4. Built an independent **3-D steady conduction model** from the STEP geometry (1 mm voxels, about 314 000 cells: motor block, fin, PETG slip-in), with the manual's
   boundary conditions exactly as written, to test the energy split and the PETG temperatures that the hand model cannot give. Validation: with the PETG insulated and
   R_ma = 12 K/W preserved the 3-D model gives motor 57.7 C and fin heat 1.50 W, inside the 1-D range for the CAD fin (56.6 to 59.4 C, 1.36 to 1.58 W). Voxel volumes are
   within 0.3 % (fin), 0.9 % (motor) and 5 % (slip-in) of the STEP; PETG heat is therefore good to about +/-20 %, not better.
5. Checked the transient claim with the repo's two-node transient and with a fixed-air lumped model of what the SolidWorks study actually contains.
6. Reviewed `fin_sizing_4w` (script, override, convergence, infinite-fin limit, headline claims, trends).

Scratch scripts (session scratchpad, not in the repo): `.../scratchpad/indep1d.py`, `cadgeom*.py`, `fin4w_check*.py`, `transient.py`, `vox/{voxelize,fea,runv}.py`.
They can be moved to `verification/` on request.

## 2. Separation of facts, assumptions, derived results, uncertainty

**Supplied facts (SUPPLIED):** 1.5 A (D37); room 23 C; motor block 42.3 mm square, 38 mm; fin as built 0.019 in (0.483 mm), 6061, 44 x 250 mm; PETG limit 60 C;
R_ma 12 / 14 K/W and R_sa 1.0 / 3.5 K/W and P_elec 1.5 W (repo `gen2_motor_thermal.py`); Study B conventions.

**Approved/flagged assumptions (ASSUMED):** R_phase = 1.8 ohm (heat scales with R: 1.5 ohm gives 3.38 W, 2.1 ohm gives 4.73 W); h of the fin inside the shell 4 W/m2K;
PETG free-face h 5 W/m2K; PETG k 0.20; contact 1e-4 K.m2/W; 6061 k 167; emissivity 0.90 / 0.10; still air; how 1.5 A was reached is **not recorded** (D37).

**Derived results (CHECKED here):** P = 1.5^2 x 1.8 = 4.05 W; k_eq = 167 x 0.483 / 2.0 = 40.33 W/m.K; h_motor = 1/(12 x 8219 mm2) = 10.14 W/m2K;
shell air 27.1 C vented, 36.2 C sealed; motor, fin heat and fin rises of the answer sheet.

**Unresolved uncertainty:** R_phase; R_ma and R_sa (whether R_ma includes the PETG housing, see F2); fin h inside the shell roof funnel (F6); ceiling hot layer and draughts;
PETG k and contact quality; driver (A4988) heat; PETG creep at 55 to 60 C under load.

## 3. Check 1: answer sheet versus script output, and the model call

`P = S.motor_heat(1.5) = 1.5^2 x 1.8 = 4.05 W` is passed as `P=` to `coupled_converged` for every case (and as `p` for the 1.06 A and 1.35 A comparisons). Correct.

| Manual value | Script output | My recomputation | Agree |
|---|---|---|---|
| Motor painted vented 55.9 to 58.8 | 58.8 -> 55.9 | 58.7 -> 55.8 | yes |
| Fin heat painted 1.41 to 1.63 W (35 to 40 %) | 1.41 -> 1.63 (34.8 to 40.2 %) | 1.42 -> 1.64 | yes |
| 50 mm above exit 12.1 to 13.7 K; tip 2.5 to 2.8 K | 12.1 -> 13.7; 2.5 -> 2.8 | 12.1 -> 13.8; 2.5 -> 2.8 | yes (as-built 44 x 200 fin) |
| Bare: 59.5 to 61.6 C, 1.20 to 1.36 W, 17.8 to 19.7 K, 6.7 to 7.2 K | same | 59.4 to 61.5, 1.21 to 1.37, 17.9 to 19.8, 6.7 to 7.3 | yes |
| Sealed painted 63.5 to 67.8 C (air 36 C) | 63.5 -> 67.8, 36.2 C | 63.3 -> 67.6, 36.1 C | yes |
| No fin vented 77.1 C; sealed 99.1 C | 77.1; 99.1 | 77.15; 99.1 | yes |
| 1.35 A (3.28 W) 49.9 to 52.2; 1.06 A (2.02 W) 40.1 to 41.5 | same | 49.8 to 52.2; 40.0 to 41.5 | yes |
| h_motor 10.1 vented, 8.7 sealed over 8,219 mm2 | 10.14; 8.69 | same | yes |
| Fin h 9.2 painted, 4.8 bare | 9.2 (9.3 iso end); 4.8 (4.9) | 9.17/9.33; 4.79/4.91 | yes |
| k_eq 40.3; density 652 | 40.3 | 40.33; 2700 x 0.483/2 = 652.05 | yes |
| Block 4100 kg/m3 for about 280 g | n/a | 68,440 mm3 (block + shaft) x 4100 = 280.6 g; block only 278.8 g | yes |
| 0.04 K/W through the 2 mm fin | n/a | 0.002 / (40.3 x 1300.5e-6) = 0.038 K/W | yes |

Sections 6 and 8 (targets repeated in the table and the hold-test table) are consistent with section 0 (35 to 37 C = 23 + 12.1 to 13.7; rise 33 to 36 K = 55.9 to 58.8 minus 23).

**Caveat on what these values describe.** The sheet quotes the **as-built 44 x 200 mm fin**. The model the user will run has the **CAD fin, 42 x 228.6 mm** (see F4).

## 4. Check 2: the equivalent-conductivity trick (k_eq = 40.3, density 652)

Valid, and I confirmed it numerically (the CAD fin mass is 16,949 mm3 x 652 = 11.05 g; the real sheet 8,474 mm2 x 0.483 x 2700 = 11.05 g):

| Use | Valid? | Why |
|---|---|---|
| Steady in-plane conduction (along z and across x) | **Yes** | conductance is k t w / L; k t is preserved (40.33 x 2.0 = 167 x 0.483 = 80.7 W.mm/K) |
| Heat capacity (transient mass) | **Yes** | rho c V preserved (9.9 J/K) |
| In-plane transient diffusion | **Yes** | k_eq/(rho' c) = 6.9e-5 m2/s, identical to 167/(2700 x 896) |
| Convection area (faces) | **Yes** | face area is the same planform; edges are unloaded in both |
| Contact area, contact resistance (K.m2/W) | **Yes** | per-area quantities, planform identical |
| Through-thickness resistance | **No, but negligible** | CAD 0.038 K/W against the real 0.0022 K/W (17x too high), still under 0.05 K on the motor face at 1.4 W |
| Heat-flux plot (`C_heatflux.png`) | **No** | flux density k_eq x gradient is 4.1x lower than the real fin's; the integrated heat is right. Say so in the manual |
| Edge convection/radiation if the user adds it | **No** | CAD edge area is 4.1x the real edge area (not used by the manual) |

## 5. Check 3: boundary conditions and units

| Item | Finding |
|---|---|
| Motor-face h (10.14) | Arithmetic correct for 8,219 mm2, **but the area is wrong for the CAD** (F2) |
| Shell air 27 / 36 C | Correct from the network (27.1 / 36.2). It is also consistent with the 3-D check: heat to the air is 1.90 + 0.76 + 0.10 = 2.76 W, so 23 + (2.76 + 1.5) x 1.0 = 27.3 C |
| Electronics 1.5 W | Not double counted: it enters only through the shell-air temperature, as intended |
| Radiation | Correct: h_rad (about 5.4 to 5.8 W/m2K at eps 0.9) is already inside 9.2; do not add a radiation load |
| Contact 1e-4 K.m2/W and 0.074 K/W total | 1e-4 is right. **0.074 K/W uses the model patch (1,359 mm2); the CAD contact is 1,300.5 mm2 (measured), giving 0.077 K/W** (F7, negligible effect) |
| PETG k 0.20, rho 1270, cp 1200 | In the usual range (ASSUMED). Sensitivity: k 0.12 raises the motor by 1.1 K (F5) |
| Heat into the PETG | **Missing from the manual's expectations and partly double counted** (F1, F2) |
| Units | Consistent: W, m2K, K.m2/W. The manual's contact "Distributed" entry is per-area, the "Total" entry K/W |

## 6. Check 4: the PETG face estimate "1 to 3 K below the motor block, about 53 to 58 C"

**Not defensible as written.** Nothing in the script computes a PETG temperature; the range is the motor range minus 1 to 3 K by assertion. The 3-D check, with the
manual's boundary conditions:

| Quantity (painted, vented, literal manual BCs, V1) | Value |
|---|---|
| Motor block mean | 55.27 C (min 54.23, max 55.42) |
| PETG hottest cell | **55.28 C (equal to the motor mean)**, on the bonded motor face |
| PETG touching the motor, mean | 54.68 C |
| PETG touching the fin (the "face against the fin"), max / mean | 54.79 / 54.07 C (0.5 to 1.2 K below the motor mean) |
| Motor face against the fin | 0.43 K below the block mean (manual: "less than 1 K": agrees) |

The bonded interface cannot drop much temperature because the heat flux across it is small and the steel block is nearly isothermal. Across all my variants the PETG
maximum minus the motor mean is -0.0 to +0.2 K; PETG against the fin is 0.5 to 1.2 K lower (0 to 0.4 K lower when the PETG is insulated and passes no heat). So a defensible statement is: **PETG maximum equals the motor block mean (within
0.2 K); the face against the fin is 0.5 to 1.2 K lower**. Applied to the answer sheet that is about 55 to 59 C painted (CAD fin 56 to 60) and about 59 to 62 C bare, i.e.
the 60 C limit is **not** met "with margin" and is exceeded with a bare fin. The statement "PETG 10 mm from the motor plate: well below the maximum" is also wrong for this
geometry: the bonded deck is 13.5 mm thick, and at 10 to 15 mm from the motor surface the PETG still reaches 52 C (mean 40 C), at 15 to 25 mm 43.5 C; about 20 cm3 of PETG is above
50 C (x -35 to 20, y -64 to 8, z -29 to 33 mm in the station frame). That matters for the hot-tab creep check, not only for the 60 C face limit.

## 7. Check 5: energy-balance split and the transient claim

**Energy balance.** The total closes (4.050 W in all my runs), but the manual's split "2.4 to 2.6 W from the motor faces, 1.4 to 1.6 W from the fin, a few hundredths of a watt
from the PETG" is **wrong for the CAD assembly**. The 2.4 to 2.6 W is the network's total non-fin heat (P minus q_fin), which in the FEA is shared between the motor faces and the
PETG. A hand check agrees with the 3-D result: the 13.45 mm PETG deck behaves as an annular fin (r0 22.6 mm, m 43 /m, G 0.024 W/K), 0.66 W at a 28 K rise; the 3-D model gives 0.76 W.

**Transient (C7).** The repo's two-node transient reproduces "about 94 %" at 1.5 A (94.1 % uniform-flux end, 95.3 % isothermal end at 60 min; 95 % to 96 % at 65 min). That network
has the 600 J/K shell warming up. The SolidWorks study fixes the shell air at 27 C and includes the PETG mass, so the C7 prediction differs: a fixed-air lumped model gives
tau 17 to 19 min and **96 to 97 %** at 60 min with no PETG mass, and **90 to 92 %** if about 15 % of the PETG mass takes part (tau 24 to 26 min). The 0.94 factor is correct for the
hold test (real shell), but is not a prediction for C7.

## 8. Findings (Study C)

| # | Severity | Finding | Expected (manual) | Found | Fix |
|---|---|---|---|---|---|
| F1 | **High** | Energy-balance expectation (section 5) ignores the PETG heat path. The motor's -x face (1,607 mm2, measured) is bonded to the PETG deck, and the fin patch is bonded to the PETG tab (1,299 mm2) | motor faces 2.4 to 2.6 W, fin 1.4 to 1.6, PETG a few hundredths | 3-D: motor faces 1.90, fin 1.39 (1.29 out + 0.10 in), **PETG 0.76** (0.74 with h only within 30 mm; 0.64 at k 0.12) | Change the expected split to about 1.9 / 1.4 / 0.75 W (or restate the BCs) and remove the "check for a double load" advice that would send the user hunting for a non-existent fault |
| F2 | **High** | h_motor 10.1 is R_ma spread over 8,219 mm2 = 4 sides + back. In the CAD one side (1,607 mm2, 20 %) is covered by PETG and the manual tells the user to leave it out, so the free area is **6,612 mm2** and G_air = 0.067 W/K (14.9 K/W, not 12). The PETG then adds a second path, although `gen2_motor_thermal.py` defines R_ma as motor to "shell interior: air + PETG housing", i.e. the PETG path is already inside R_ma (partial double count). Result: the motor temperature depends on how the user selects faces | motor 55.9 to 58.8 within +/-3 K | **52.3** (h raised to 12.57 to keep R_ma, PETG on) / **55.3** (literal manual) / 55.5 (PETG h only near the motor) / 56.4 (PETG k 0.12) / **57.7** (R_ma kept, PETG insulated: matches the network) / **62.1** (literal, H_petg omitted). Spread 9.8 K against a +/-3 K pass window | State one consistent BC set and its expected result (recommended: literal set, expect 55 to 56.5 C and PETG 0.7 to 0.8 W), say that omitting `H_petg` gives about 62 C, and note that the PETG path is not in R_ma's 12 K/W if it is kept |
| F3 | **High** | PETG face estimate, see section 6; "with margin" is not justified; bare fin is above 60 C | 53 to 58 C, 1 to 3 K below the motor | PETG max = motor mean (-0.0 to +0.2 K); against the fin 0.5 to 1.2 K below (0 to 0.4 K if the PETG is insulated) | State "PETG maximum about equal to the motor mean; 55 to 59 C painted (56 to 60 with the CAD fin), 59 to 62 bare". Replace "with margin" by "0.4 to 4.7 K margin painted; none bare". Fix "PETG 10 mm away" |
| F4 | Medium | Fin targets are for the as-built 44 x 200 fin but the study runs the CAD fin 42 x 228.6 mm (176 to 179 mm exposed). Motor shift is **+0.8 K, not about 0.5 K**; the tip target is off by 1 K or more | tip 2.5 to 2.8 K painted, 6.7 to 7.2 bare | CAD fin (1-D): motor 56.6 to 59.4 C painted, 59.9 to 62.0 bare; fin 1.36 to 1.58 W; 50 mm above exit 11.9 to 13.5 K; **tip 3.4 to 3.8 K painted, 8.2 to 8.9 bare**. 3-D: tip 4.4 K painted, 9.9 K bare | Give the CAD-fin tip targets (3.4 to 4.5 K painted, 8 to 10 K bare) or flag the sheet as as-built only |
| F5 | Medium / Low | Variants: C5 "about 77 C" is the network; with the real PETG path the motor is **69.4 C** (PETG 1.20 W, PETG max 69 C). C6 "almost no change in the motor": +1.1 K (56.4 vs 55.3 C). C7 94 %: see section 7. C2 sealed 63.5 to 67.8: 3-D gives 63.5 C (low end, PETG 63.5 C, so "PETG above 60" holds); C3 bare 59.5 to 61.6: 3-D gives 57.9 C | as listed | as listed | Quote the 3-D-consistent values or say the sheet is the network without the PETG path |
| F6 | Low | Shell exit height. STEP: the roof plate at the fin slot is z 27.84 to 31.16 (3.3 mm); slot walls y -2.69 and +2.31 (gap 0.69 mm on the motor side, **2.31 mm** on the spool side). The fin leaves the plate at **z = 31.16, 49.5 mm above the fin bottom edge** (matches the brief's 50 mm), not z 34.6 / 53 mm. The two options in 2.4 (draw at 53 mm, or Convert Entities on the slot edge) disagree by 3.5 mm. Effect on results: under 0.4 K, under 0.05 W. Also: the roof rises in a funnel around the slot (z 33 at 6 mm off the fin, 36 to 37 at 9 mm, 70.8 beyond 10 mm), so the hottest 40 mm of the exposed fin sits in a V-notch, where the assumed unconfined h 9.2 may be too high (UNRESOLVED; the hold test decides) | 34.6 / 53 mm | 31.16 / 49.5 mm | Correct the number; mention the funnel |
| F7 | Low | Contact area 1,300.5 mm2 (motor face to fin back, measured) against the 1,359 mm2 in the script, so the "Total" entry is 0.077 K/W | 0.074 K/W | 0.077 K/W | Update the number (effect under 0.01 K) |
| F8 | Info | The station-frame origin is 2.64 mm below the real shaft axis (shaft centre z 2.64; motor block z -18.51 to 23.79). The manual's "axis 21 mm above the bottom edge" is right for the true axis | | | Optional note |
| F9 | Info | The claim that the steel block puts the result at the isothermal (lower-motor) end is only partly right: 3-D validation lands mid-range (57.7 C in 56.6 to 59.4; fin 1.50 W in 1.36 to 1.58) | | | Optional wording |

What agrees: the motor-to-fin drop (0.35 to 0.5 K against the "less than 1 K" target), TC2 rise (12.5 to 13.5 K in the 3-D runs against 12.1 to 13.7), the fin heat (1.39 to 1.50 W against
1.41 to 1.63 W, inside +/-20 %), the sealed-shell PETG above 60 C, and the energy balance closing to 1 %.

### Voxel 3-D check, all variants (painted fin unless stated; heat in W)

| Variant | Motor mean (C) | Motor faces | Fin (out+in) | PETG | PETG max (C) | PETG at fin, max / mean |
|---|---|---|---|---|---|---|
| V1 literal manual BCs | 55.27 | 1.90 | 1.39 | 0.76 | 55.28 | 54.79 / 54.07 |
| V3 PETG h only within 30 mm | 55.49 | 1.91 | 1.40 | 0.74 | 55.50 | 55.00 / 54.28 |
| V8 PETG k 0.12 | 56.40 | 1.97 | 1.44 | 0.64 | 56.39 | 55.65 / 54.80 |
| V2 PETG insulated (no H_petg) | 62.10 | 2.36 | 1.69 | 0.00 | 62.28 | 62.25 / 61.68 |
| V4 h 12.57 (R_ma kept) + PETG | 52.32 | 2.11 | 1.27 | 0.68 | 52.34 | 51.89 / 51.25 |
| V10 h 12.57 + PETG insulated (validation) | 57.66 | 2.55 | 1.50 | 0.00 | 57.83 | 57.81 / 57.31 |
| V5 bare fin (h 4.8) | 57.94 | 2.08 | 1.14 | 0.83 | 57.93 | 57.40 / 56.72 |
| V6 sealed (36 C air, h 8.69) | 63.46 | 1.58 | 1.73 | 0.74 | 63.48 | 63.01 / 62.19 |
| V9 no fin, motor mated to the plate | 69.41 | 2.85 | 0.00 | 1.20 | 69.33 | n/a |

All with the CAD geometry, 4.05 W, shell exit at z 34.64 (as the manual), 1 mm voxels, bonded PETG, contact 1e-4 K.m2/W motor to fin.

## 9. Fin sizing for 4.05 W (`fin_sizing_4w.py` and `.md`)

Run: reproduces the `.md` raw output exactly (only blank lines differ). 22 s.

| Check | Result |
|---|---|
| (1) Temporary override of `S.FIN['h']` | **PASS.** Set to `z_exit + L` (50 + L), used inside `fin_quasi_1d`, restored in `finally` (250 before and after). z grid ends at 250 mm for L = 200, as intended. `dz = 0.5` versus 0.25 changes the 0.019 in patch rise by 0.14 K |
| (2) `converge_h` consistency | **PASS.** Mean rise = Q/(hA) (the eta cancels), Churchill-Chu uses the exposed length, radiation at the mean fin temperature, 44 mm width matches `FIN['w']`. My independent code reproduces every 200 mm temperature to 0.2 K (0.019 in painted 99.5 / 119.7 vs 99.7 / 119.8; 1/8 in 56.2 / 59.3; 1/4 in 50.7 / 52.3). The same h for every thickness is correct (mean rise Q/(hA) does not depend on t) |
| (3) Infinite-fin limit | Formula `w sqrt(2 h k t) theta_b` is right for two faces. The approximate h (mean rise theta/3, L 0.4 m) is **conservative**: the exact first integral with a local h(theta) gives 2.11 to 2.17 W for 0.019 in painted (script 1.99), 1.47 to 1.55 bare (1.35), 5.41 to 5.56 for 1/8 in painted (5.11), 5.34 to 5.63 for 1/4 in bare (4.90): the script is 6 to 15 % low. It is an indicator, not a strict upper bound, so "the most heat any length can carry" should read "about" |
| (4a) 0.019 in cannot carry 4.05 W, about 2.0 W max painted | **AGREE.** 1.99 W (2.1 to 2.2 W with the local-h method); needs 1.9x. Past about 140 mm it adds under 5 %: tanh(m L) = 0.979 at 140 mm, 0.925 at 100 mm (m = 16.2 /m) |
| (4b) 1/8 in painted at 200 mm: 56 to 59 C alone | **AGREE.** 56.2 to 59.3 (independent 56.2 / 59.3) |
| (4b) coupled with the vented shell: 44.7 to 45.8 C (sealed 48.0 to 49.5) | **AGREE** by `S.coupled_converged` (44.7 to 45.8; 48.0 to 49.5) and my independent code (44.5 to 45.7; 47.8 to 49.3), **but these numbers are not printed by the script or in the .md raw output** (traceability gap) |
| (4c) bare needs 1/4 in x 285 to 330 mm | **AGREE** with the script. 3/16 in x 395 mm also passes at the isothermal end (not at the uniform end), so "needs 1/4 in" holds for both ends only |
| (5) Unphysical trends | **One.** Temperature versus exposed length is **not monotonic**. Churchill-Chu with L = exposed length makes h fall as L^-0.25 even though the added length is far from the hot base. T(L) passes a minimum and then rises: 0.090 in painted 59.07 C at 320 mm, 60.1 at 600; 1/8 in painted 54.0 at 380 mm, 54.5 at 600; 3/16 in bare 59.04 at 580 mm. All other trends (thickness, finish, limit, q_inf) are monotonic |

Consequences of the artefact: lengths on the falling branch (most of the table) are right and slightly conservative; **"0.090 in painted 210 mm" is marginal** (the flange stays within 1 K of 60 C at any length: 60.2 at 200 mm, 59.1 at 300, 60.1 at 600), and "nothing up to 600 mm reaches 55 C" for the bare 1/4 in is borderline (55.02 C at 600 mm). The headline claims are unaffected.

Wording errors in the `.md`: "the motor's own path to the shell air is ignored, which is conservative and **close to a sealed shell**" is wrong: in a sealed shell the fin carries only 1.79 to 2.04 W (44 to 50 %) of the 4.05 W; the 100 % case is an adiabatic-motor bound. The mass column is for a 250 mm plate, so the 285 to 330 mm bare 1/4 in fin is about 250 to 290 g, not 189 g.

Unresolved for the fin sizing: edge and tip area ignored (conservative, up to 14 % extra area at 1/4 in); the roof funnel and ceiling limit on length; shear and flatness of thick plate (the .md already notes shear capacity).

## 10. Conditions for PASS (what to fix in the manual)

Must fix before the user runs Study C:
1. Section 5 (energy balance) and section 10: replace the expected split with about 1.9 W motor faces, 1.4 W fin, 0.75 W PETG, and fix the "no PETG heat" assumption (F1).
2. Sections 1 and 3.3: state one consistent set of motor-face and PETG loads and its expected motor temperature (55 to 56.5 C literal, 62 C if `H_petg` is omitted); say that h 10.1 over 8,219 mm2 no longer applies once the -x face is covered; address the R_ma double count (F2).
3. Sections 0 and 6: PETG maximum about equals the motor mean, 0.5 to 1.2 K lower against the fin; remove "with margin" and "well below at 10 mm" (F3).

Should fix:
4. Give CAD-fin targets for the tip (3.4 to 4.5 K painted, 8 to 10 K bare) and motor +0.8 K (F4).
5. C5 about 69 C, C6 about +1 K, C7 qualifier (F5). 6. Shell exit 31.16 mm / 49.5 mm above the bottom edge, 2.31 mm gap on the spool side, funnel note (F6); contact 1,300.5 mm2 and 0.077 K/W (F7).

For `fin_sizing_4w`: note or remove the L-dependence of h for L above about 250 mm; delete "close to a sealed shell"; print the coupled 1/8 in numbers in the script; say the infinite-fin limit is approximate (about 10 % low).
