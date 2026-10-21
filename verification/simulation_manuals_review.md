# Independent review: SolidWorks Simulation manuals (Study A static, Study B thermal)

Reviewer: calculation-checker (independent recompute). Date: 2026-10-21.
Scope: `calculations/simulation_loads.py`, `tests/test_simulation_loads.py`,
`docs/simulation/SW_STATIC_STATION_MOUNT.md`, `docs/simulation/SW_THERMAL_HEAT_FIN.md`,
`docs/simulation/img/*` (7 PNG), cross-checked against `DECISIONS.md` D29/D30 + erratum,
`docs/decisions/WINCH_CAPACITY_20261021.md`, `docs/presentation/FUNDAMENTALS.md` topics 2 and 3,
`calculations/gen2_motor_thermal.py`, `verification/design_review_gen2.md` R3/R4/R10/R11,
`docs/SIMULATION_GUIDE.md` Study 1, `docs/presentation/DECK_STORYLINE.md` slide 10, and the STEP files in
`solidworks/v3_2026-10-18/` plus the newer `solidworks/v3_assembly_2026-10-19/Assem_laundry_v3.STEP`
(the loads script reads the assembly; I compared the two).

Method: I recomputed every number without importing `simulation_loads.py` (own scripts, kept in the session
scratchpad, not in the repo): loads, directions, tab-root statics with signed corner stresses, screw group with all
six moment components, fin formulas, a 2-D finite-volume solve of the real fin outline (hole, bolt holes, R3 corners,
0.25 mm grid, 2 grid levels agree to 0.3 %), the coupled motor network, the transient, and STEP queries with
CadQuery 2.8 (face areas/normals, slab sections, booleans). I did not run SolidWorks and did not run an FEA of the
station; all click-path judgements are from knowledge of SolidWorks 2023-2025 and are marked where I am unsure.
`/usr/bin/python3 -m pytest tests/test_simulation_loads.py`: **8 passed** (no skips, so the STEP test did execute).

## Verdict: USE WITH FIXES

The load arithmetic, the thermal numbers and the STEP geometry check out. Nothing below changes a headline
number except the screw-load and deflection hand columns. But four items would produce a false alarm or block
Jasper on the first run (H1 to H4), and the pass/fail rules for P1/P3/P4/P7 are not yet measurable as written.
Estimated fix effort: 30 to 45 minutes of text edits; no calculation has to be redone except the two hand columns.

---

## 0. Facts, assumptions, derived results, unresolved (kept separate as CLAUDE.md requires)

| Class | Item |
|---|---|
| Supplied facts (repo/STEP) | Vref 0.85 V (D30); R100 sense; 36 N.cm at 1.5 A convention (shopping list, R10); spool core 7.5 mm, full 10 mm (R4); 0.7 running fraction; STEP geometry (verified below); R_phase 1.8 ohm (itself an assumption in `gen2_motor_thermal.py`); fin 44 x 250 x 0.483 mm, 7/8 in hole (DESIGN_STATE 10/20-21) |
| Approved/inherited assumptions | PETG E 1800 MPa, derated yield 25 MPa, SF 3 / 1.5, 2x dynamic, K_line 3 N/mm (guide, R1) |
| Manual-introduced assumptions | Y_drum 18 mm; shell mass 0.25 kg; hot-tab x0.7; print orientation; 25 deg dovetail flank (now measurable, see L2); h_inside 4; contact conductances; alloy k bounds; emissivities |
| Derived (all re-derived here) | tensions, directions, tab-root stresses, screw loads, fin eta/R, rises, coupled temperatures |
| Unresolved | motor torque basis (U1); line outlet/pulley absent from STEP; print orientation; real contact conductance; fin vs ceiling clearance (U3) |

---

## 1. Findings by severity

### HIGH (fix before Jasper runs anything)

**H1. The P5 equilibrium table omits the self-weight of the two meshed bodies, so every Z reaction is wrong and P5 fails on the first run.**
Evidence: section 4.3 step 1 applies gravity (`L0_gravity`) to the model, and the model contains the wall mount and
slide-in (602,284 + 217,693 = 819,977 mm3, measured from the STEP, x 1270 kg/m3 = 1.041 kg = **10.22 N**).
Section 5.1 expects "applied loads + 5.30 N weights" only.
Correct Z reactions: D1 +49.5 N (table says +39.30, off 26 %), D2 +40.0 (29.80), D3/D4/D5 +22.2 (11.96, off 85 %).
X and Y entries are right. The "within 1 %" check would send him hunting a setup error that does not exist.
Exact fix, section 5 item 1, replace the sentence and the Z column:
> "The sum must equal the negative of the applied loads plus the 5.30 N remote weights plus the self-weight of the two meshed bodies (10.2 N: read the mass from Evaluate -> Mass Properties on both parts, about 1.04 kg, times 9.81):"
> D1 0, 0, +49.5 | D2 -16.67, -16.67, +40.0 | D3 -33.34, 0, +22.2 | D4 0, +33.34, +22.2 | D5 0, -33.34, +22.2

**H2. "Peak von Mises (away from singularities)" (P1, P3, section 10 table) has no operational rule, and with this loading the global maximum is guaranteed to be singular.**
Evidence: the load is a Remote Load (Direct Transfer) on the walls of four Ø3.5 holes, the fixture is Fixed Geometry on
the bore plus shoulder of six holes, and the tab has a sharp back-side root corner. Each is a fixed/loaded-edge or
re-entrant-corner singularity. The manual names them (sections 5.2, 6.3) but gives no distance, no value to quote and
no way to decide "real vs artefact"; the FoS plot of section 8 (areas below FoS 3 in red) will also paint the singular
spots red. Hand numbers to adjudicate: average hole bearing is (34/4)/(3.5 x 5) = **0.49 MPa** (about 1 to 1.5 MPa
with the moments), and per-screw loads are 10 to 20 N, so any W2/S3 hole-edge vM of tens of MPa is an artefact.
Exact fix, add to section 6 after step 3 and point section 10 at it:
> "Rule for P1/P3. Do not quote a stress within 2 mm (about two C1 elements at M3) of (i) the edge of a fixed face (W2 bore or shoulder), (ii) the edge of a loaded face (S3 holes) or (iii) the sharp back-side root corner. The value used for P1/P3 is the larger of (a) the fillet-probe maximum of the convergence table and (b) the stress probed 1 mm inside the sharp corner. Also record the unfiltered global maximum and its location and label it 'singular, not used' if it sits on a fixed or loaded edge and changes by more than 10 % between M2 and M3 while the fillet probe changes by less. Hole-bearing stress for comparison: 0.5 MPa average (about 1.5 MPa with moments). In the FoS plot, red patches smaller than about 2 mm at a fixed or loaded edge are singular; red on the tab root fillet or on the deck away from edges is real."
> Section 10 first row: "P1 peak vM (non-singular, per the section 6 rule), D1".

**H3. P4 "displacement at the cable exit" cannot be read from the model as built, and the hand deflection column is inconsistent (so the "within a factor of 2" sanity check will misfire).**
Evidence: the spool and motor are excluded, so there is no node at the drum/cable exit (the load point is in air 13 mm
in front of the tab). Section 8 says "also report the cable-exit value" without saying how. The script's `defl_y`
counts only the y-deflection, adds the two contributions as absolute values (for D2 they partly cancel: 0.143 - 0.122
= 0.02, not 0.27) and ignores the rotation of the tab acting through the 15.5 to 18 mm lever (for D1 the twist is
14 mrad, giving 0.22 mm along the force, the manual says "<0.05"). My rigid-motor, free-cantilever (E 1800 MPa,
G = E/2(1+nu), J = 0.312 b t^3) displacement of the load point is below; it is conservative if the real motor stiffens the tab.

| Case | Manual "exit deflection" | My load-point displacement, total / along the line (mm) |
|---|---|---|
| D1 | < 0.05 | 0.22 / 0.22 |
| D2 | 0.27 | 0.19 / 0.17 |
| D3 | 0.17 | 0.28 / 0.23 |
| D4, D5 | 0.33 | **0.43** / 0.33 |
| D4f | 0.22 | 0.36 / 0.35 |

D4 at 0.43 mm is 86 % of the 0.5 mm limit, not 66 %. Also the FEA "Max URES on S3 holes" (section 6 table) will over-read
the exit: the far holes at x = +15.5 mm move about 0.69 mm in D4 by the same cantilever formula.
Exact fix: replace the section 0 deflection column with the table above (total value), and in section 8/10/11 define
P4 as: "P4 gauge = maximum URES on the four S3 hole faces. If it is 0.5 mm or less, P4 passes (the gauge over-reads the drum
point). If it exceeds 0.5 mm, estimate the exit as mean URES over the S3 faces plus tab rotation times the 15.5 mm
(x or z) / 18 mm (y) lever before calling it a failure." Rename the template column "S3 max URES (mm)" and add "exit estimate (mm)".

**H4. Section 3.3 "Insert -> Face -> Delete" is a part-level feature and the model is open as an assembly.**
(As far as I can judge; I could not test.) In an assembly the Insert menu does not offer Face -> Delete until a component is
opened for editing. A first-time Simulation user will stall at the first defeature step. The five components are
`Wall_Mount_v3`, `Slipin_mount_piecev3`, `Shell_Casing`, `Spool1011`, `Motor_Reference`; `Motor_Reference` is itself a
two-body sub-assembly (motor block 67,993 mm3 plus the Ø5 x 24 mm shaft, 447 mm3), so "Exclude from Analysis" must be
applied to both of its bodies.
Exact fix, section 3.3, add before the table:
> "These are part features. In the assembly, right-click `Slipin_mount_piecev3` (then `Wall_Mount_v3`) -> Edit Part (or Open Part), do the Delete Face there, then return to the assembly (Edit Component to close). Defeaturing is optional if the mesh controls cope; skip it rather than skip the study."
Section 3.5, add: "`Motor_Reference` contains two bodies (motor, shaft); exclude both."

### MEDIUM

**M1. D4/D5 are unreachable and D2 is beyond the manual's own fleet limit; D4 is listed "required" and is predicted to fail.**
Evidence: the tangent point (7.5, 18, 0) for a line along -y lies inside the spool flange (r = 7.5 < 18 mm at y = 10..7) and
directly in front of the motor tab and motor (|x| < 21.15, |z| < 21.15): physically blocked (the `station_assembly_loads.png` D4
arrow passes through the motor). The in-plane share is only 0.196 x 34 = 6.7 N, so the motor torque in D4/D5 is 0.050 N.m,
not 0.255 N.m. D2 has u_y = 0.490, i.e. 29.4 deg of fleet, more than the 26.05 deg (my recompute) the manual uses for D4f.
At a fleet angle a the line tension at the same shaft torque is 34/cos(a), not 34 N (D2 +15 %, D4f +11 %). D4f is the
reachable motor-side case (line passes x = +27.5 mm at y = 5, clear of the tab at x = 21.15).
Tension-face analysis (my signed corner stresses): D4 and D4f put tension on the **filleted +y face**; D5 puts it on the
**sharp -y corner** (5.55 MPa nominal, no fillet). With fleet-limited directions the D4f case governs (4.9 MPa nominal);
D5f gives about 0.9 MPa on the +y face and roughly 0 on the sharp face.
Exact fix, section 2.2 table "Required?" column and verdict rule:
> D4, D5: "unreachable bounds (the line would pass through a spool flange; D4 also through the tab and motor); optional". D4f: "**yes** (reachable motor-side case, u = (0.8810, -0.4392, -0.1760))". D2: "recommended; as written it needs an outlet that turns the line (29.4 deg of fleet exceeds the 26.1 deg limit); clipped version u = (0.5054, 0.4392, -0.7429), F = 34/cos(26.05 deg) = 37.8 N along u".
> Verdict rule: replace "D1, D2, D3 and D4" by "D1, D3 and D4f (and D2)", and keep the D4/D5 bound only as information. If D5 is kept as a bound, note it is the only one that tensions the sharp back-side corner.

**M2. The "wall-present variant: Roller/Slider on the back face W1" is a two-sided constraint and gives a false answer for the pull-away cases.**
A Roller/Slider holds the face against moving away from the wall as well as into it. For D2/D3/D4f (Fx > 0, pulling away) it would
carry the pull through the whole back face and report almost no screw tension, the opposite of what the variant is meant to show.
(The existing `SIMULATION_GUIDE.md` Study 1 says the same thing, "it can press the wall but not pass through it"; that is not what the
restraint does.) Exact fix, section 4.1:
> "...run the optional wall-present variant with a one-sided wall: Connections -> Virtual Wall (rigid, No Penetration, friction 0.3) on the back face W1 (check that your Simulation tier offers it), not Roller/Slider, which also resists pull-away."

**M3. Screw hand estimate omits the moment about z (and x), so the per-screw tension quoted for P7 and used for the "sanity check" is too low for the along-wall cases; P7 has no capacity number.**
Evidence: `screw_group_estimate` uses only `M[1]` (and Fy, Fz for shear). My rigid-plate, six-screw, wall-bearing-ignored solution
with all components (same convention, same C = screw centroid):

| Case | Manual/script top-row tension, shear (N) | Mine, max tension / max shear (N) |
|---|---|---|
| D1 | 11 / 6.5 | 11.2 / 6.6 |
| D2 | 11 / 5.7 | **17.5** / 6.2 |
| D3 | 8 / 2.0 | 9.1 / 2.2 |
| D4, D5 | 4 / 5.9 | **18.6** / 7.1 and 7.9 |
| D4f | not printed | 14.2 / 3.3 |

The manual quotes the D1 numbers (11 N / 6.5 N) as "the hand estimate" for P7 and in section 5.4; the worst case is 18.6 N (1.7x).
P7 says "rated withdrawal / 3" but names no screw, no wood and no number, so it cannot be evaluated.
Install note (unresolved, not a manual error): the hole pattern has two columns 37.0 mm apart; a nominal 1.5 in stud is 38.1 mm wide,
leaving about 0.5 mm edge distance per screw if perfectly centred. Both columns cannot sit in one stud. Confirm how the six screws will
actually land (stud, plate, or one column only); if one column only, rerun F1 with three fixed holes.
Exact fix: section 0 P7 and section 5.4: replace "hand estimate ~11 N tension, 6.5 N shear" by "hand estimate, rigid plate on six screws, wall bearing ignored: D1 11 N / 6.6 N; D2 17.5 / 6.2; D3 9.1 / 2.2; D4 and D5 18.6 / 7.9 (governing); D4f 14.2 / 3.3". Add to P7: "limit = rated withdrawal of the actual screw in the actual wood / 3; fill in: screw ______, wood ______, rated ______ N". In the script add the `M[2]` (column) term to `t_top` and the `M[0]` torsion term to `shear`.

**M4. Thermal: the manual compares the formula and the FEA at the wrong station.**
Evidence: `R_fin = 1/(h eta A)` with A = 2 x 44 x 200 mm and a tip at z = 250 mm references the fin **base at the shell exit z = 50 mm**,
not the patch top at z = 42.15 mm. The manual labels the formula's 37.3 K "rise at the top of the contact patch (z = 42 mm)" and
explains the FEA being 2 to 7 % above it by the hole and spreading. My 2-D solve (same loads, same h, 0.25 mm grid): z = 50 mm 35.7 K
(manual quasi-1D 35.6; formula 37.3, -4 %), z = 42.15 mm **40.1 K** (manual 39.9), patch average 51.6 K (50.2), y = 100 mm 16.5 K (16.6), tip 3.2 K.
The +4.4 K between z = 50 and 42.15 is plain conduction along the 7.85 mm neck (R = L/(k t w) = 2.2 K/W x 2.03 W), not mainly the hole.
All numbers agree; the labels and the explanation do not. Exact fix:
> Section 0 table header: "Formula rise at the fin base, shell exit z = 50 mm" (values unchanged); add a column "FEA/quasi-1D rise at the top of the patch, z = 42 mm: 39.9 K (paint), 52.1 K (bare), 17.7 K (1/8 paint)".
> Section 4 first bullet: replace "assumes a clean 44 mm wide fin starting at the patch top" by "is referenced to the shell exit (z = 50 mm, exposed length 200 mm). Compare it with the FEA at y = 50 (expect 4 to 5 % below the formula) and note the rise at y = 42.15 is about 4 K higher because of conduction along the 7.85 mm neck; the hole and spreading mainly raise the patch average."

**M5. Study B-2 is "optional" but every motor temperature on the slide depends on it; there is no thermal results template; TC1 location.**
B-1 puts all 2.03 W through the fin by construction, so it validates only the fin curve. The motor temperatures (41.6, 47.3, 43.2, 49.7,
35.1, 37.7 C; fin heat 0.72 / 1.21 W) come from the lumped network plus the quasi-1D resistance and are CALCULATED unless B-2 is built. The
static manual has a section 11 template; the thermal manual has none. The predicted TC1 (18.6 K) is the lumped motor node, which equals the
patch mean; a thermocouple "on the flange rim at the top edge next to the fin" sits near the patch top (14.9 K for the coupled case).
Exact fix:
> Section 0/5: "Build B-2 if a slide quotes a motor temperature as SIMULATED. Without B-2 those figures are CALCULATED (network plus quasi-1D) and only the fin curve is FEA-validated."
> Section 8 TC1 row: "predicted 18.6 K at the motor case mid-length; a thermocouple on the flange rim next to the fin reads between 14.9 K and 18.6 K".
> Add a section 11 template: `Study B run by __ date __ release __; model B-1/B-2; k __, h __ (finish), t __; energy balance F3 __ W, F2 __ W, total __ W (2.03); rise at y=42.15 __ K (39.9), y=50 __ (35.6), y=100 __ (16.6), tip __ (3.2), patch avg __ (50.2); within +/-20 %? __; B-2: motor block mean __ C (41.6), fin heat __ W (0.72), TC2/TC1 __ (0.35); 1/8 in repeat: __ ; saved plots: B_temp_fin_0p019.png, B_temp_fin_1over8.png, B_heatflux_0p019.png`.

**M6. Slide 10 text and the manual's safety-factor rule disagree by a factor of 2.**
`DECK_STORYLINE.md` slide 10 says "sized for the slip-limit tension x dynamic factor, with SF >= 3". The manual requires SF >= 3 at 34 N and
SF >= 1.5 at 68 N (algebraically the same check). Read literally the slide claims SF 3 at 68 N. Exact fix (slide line, not the manual):
> "sized for the 34 N slip limit with SF >= 3 on derated PETG (equivalently SF >= 1.5 at twice that load)".
Also, in section 2.1/section 13 say once why SF 3 at the snag load is the right pairing: it is equivalent to SF 5.7 at the 17.85 N sustained load
(8.33 MPa x 17.85/34 = 4.4 MPa, about 10 % of bulk UTS), which is the creep-driven requirement. That is a sound reading, but the manual only implies it.

**M7. FUNDAMENTALS reconciliation is correct in the numbers and misleading in the wording.**
I reproduced FUNDAMENTALS topic 3 (h = 7, R_c = 1 K/W, formula R_fin, no hole): as-built 40.7 C vented / 46.0 C sealed, fin share 39 % / 50 %;
1/8 in 36.3 / 39.4 C. The manual (and my independent 2-D version): 41.6 / 47.3 C, share 35 % / 46 %; 1/8 in 35.1 / 37.7 C.
Why they differ: the fin path is 26.0 K/W here (patch-average from the hole/neck/spreading model, +6 K/W) against 22.6 K/W there (21.6 + 1.0);
the higher converged h (8.5 to 8.7 vs 7) and the 0.07 vs 1 K/W contact resistance offset most of it. Net +0.6 K vented, +1.3 K sealed as-built, -2 K sealed for 1/8 in.
The manual's "agree to within 1.5 K" is true only for the three figures it picks; it does not mention 1/8 in sealed (-2 K) and its "about a third"
(vented) will collide with FUNDAMENTALS' headline "the fin carries about 50 %" (sealed). Exact fix, section 0 cross-check paragraph:
> "Fin share of the motor heat: 35 % vented and 46 % sealed here, 38 % and 50 % in FUNDAMENTALS (h 7, 1 K/W contact, no hole). The fin path is 26.0 K/W here (quasi-1D, includes neck and hole spreading) against 22.6 K/W there; higher h and lower contact resistance cancel most of it. Sealed 1/8 in: 37.7 C here, 39.4 to 40 C there."
> Finding (1): "about a third of the motor heat when vented (46 % when sealed)".

**M8. Units statement (low confidence).** Section 3 step 1 says "Metric (G) (temperature in C)". I am not sure Metric (G) defaults to Celsius
(it may default to Kelvin) and its pressure default is not N/mm2. Study A uses SI with mm and N/mm2 selected by hand; the two manuals should say the
same thing. Fix: "choose the unit system, then set Length/Displacement = mm, Temperature = Celsius and (Study A) Pressure/Stress = N/mm2 (MPa) explicitly in the drop-downs, and confirm the Thermal legend reads Celsius."

**M9. Option A contact text is internally inconsistent; add a one-run sensitivity.**
Section 3.6 says the bonded slide-in "rests on the shelf by the load pressing it down". The shelf gap is 0.881 mm (verified) and the ignore-clearance is
0.25 mm, so the shelf is not bonded and, once everything else is glued, not in the load path either; vertical load goes through the glued flanks
and lips. For the tab-root objective this is acceptable and the manual's reasoning (0.13 to 0.21 mm gaps, 36.75 mm3 / 0.02 mm centre-flank overlap, both verified) is sound. Fix:
> "In Option A the 0.88 mm shelf gap is larger than the ignore-clearance, so the shelf carries nothing; the vertical load goes through the bonded flanks and lips. Run the governing case once in Option B (No Penetration + soft springs); if the tab-root vM changes by less than 10 % keep the Option A numbers, otherwise quote Option B."
The existence and exact label of "Ignore clearance for surface contact" in your release is unverified by me; the manual's fallback (Option B) covers it.

**M10. "Working tension" label contradicts the capacity memo.**
Section 2.1 calls 17.85 N "the largest the winch can pull while moving (full spool)". The memo's range is 17.9 N (full spool) to 23.8 N (core), and
23.8 N is larger. The numbers are right (my 17.850 / 23.80 / 11.90 / 34.00 / 68.0); only the label is wrong.
Fix: "Running pull at a full spool (r = 10 mm), 17.85 N (the memo's 17.9). The running pull at the empty core is higher (23.8 N) but is not demanded by the claw; both are well below the 34 N slip limit that governs the checks."

**M11. Motor-basis uncertainty that the manual should state (U1 below).** Not an arithmetic error; it changes slide wording and the "x1.111 sensitivity".

### LOW

- **L1.** Section 1.3 S1 "Deck 13.47 thick (x -34.62 to -21.15)". Measured: rib tips x = -34.62, **deck underside x = -29.62**, deck top -21.15: the deck is 8.47 mm thick plus 5.0 mm ribs. Fix the S1 row.
- **L2.** Dovetail flank angle "assumed 25 deg" is measurable: five of six groove flanks have normals (-0.500, +/-0.866), i.e. 30 deg from the pull axis; the centre rib's +y flank is 25 deg; flank area 420 mm2 (script uses 401.6 for the rib side). Bearing becomes 0.055 MPa (not 0.065); conclusion unchanged.
- **L3.** Hot-tab "about 55 C" (x0.7, 5.8 MPa) vs the thermal manual's motor case 41.6 C (vented) / 47.3 C (sealed) / 50.9 C (no fin). 55 C is pessimistic; say so, or use 47 C.
- **L4.** Figures: `heat_fin_zones.png` says B-2 air "27 C", the text says 26 C vented / 32 C sealed; `line_directions.png` title says "working 17.8 N" (17.85 elsewhere) and the D1 label overlaps the legend text. `station_assembly_loads.png` correctly shows the D4 arrow through the motor, which supports M1.
- **L5.** Tests pin the load arithmetic and fin formulas but not the numbers Jasper will paste: coupled temperatures (41.6, 47.3, 43.2, 49.7, 35.1, 37.7), fin heat 0.72/1.21 W, the quasi-1D column (50.2, 62.4, 19.3, 28.7), TC ratios 0.35/0.49, the section 0 tab-root table, the screw table, or the P5 reaction constants. `test_fin_hand_calc_targets` hard-codes h = 9.6 rather than calling `converge_h`. `test_step_measurements_if_available` skips silently if CadQuery is missing (it did run here). Suggested additions: `assert coupled_converged(167,0.483,0.9,Rc_paste,'vented')['r']['T_motor'] == approx(41.6, abs=0.1)` (and the other five), `assert SL.screw_group_estimate(...)` for D4 after the M_z fix, and a constant `SELF_WEIGHT_N = 10.2` used by the P5 table.
- **L6.** The STEP files were written by "SolidWorks 2026", so Jasper's release is probably 2026, not 2023-2025. Click paths below are unlikely to change but say "2023 to 2026".
- **L7.** Thermal studies need SOLIDWORKS Simulation Professional or higher (Standard has no thermal; I am fairly but not fully sure). Neither manual states the licence tier; add "confirm tonight that Thermal appears in New Study".
- **L8.** The assembly carries the older 19 mm spool at y = 7 to 26 (mid-plane 16.5), the loads use the 22 mm Spoolv3 (mid-plane 18). The manual flags this; effect on lever is 1.5 mm.
- **L9.** Time estimates ("about 1 hour") are optimistic for a first Simulation run (model 25 + loads 15 + checks 5 + convergence 12 + cases 10 = about 70 min of clicking before solver time); say 2 to 3 hours.
- **L10.** Pull test (section 13.1): 68 N is a 7 kg dead weight on printed parts; add "keep everyone clear of the load path; hang the weight on a catch rope".
- **L11.** Section 8 "A_fos" instructions say "Areas below factor of safety: 3". Add the H2 rule so the red patches are not misread.

---

## 2. Unresolved uncertainty (not defects; the manuals should say so)

**U1. Motor torque basis.**
(a) *Microstepping:* the repo scales the datasheet 36 N.cm linearly with I_trip / 1.5 A. The datasheet figure is for two phases each at 1.5 A
(vector 2.12 A). The A4988 holds I_a^2 + I_b^2 = I_trip^2 (the manual uses this correctly for heat), so the torque vector at I_trip = 1.0625 A is about
1/sqrt2 of the linear estimate: about 18 N.cm, slip about 24 N, not 34 N. That would make the structural loads conservative by up to 1.41x and the memo's
running pulls (23.8 / 17.9 N) optimistic by up to 1.41x. This is outside the manuals' scope but it strengthens the memo's "pull test first".
(b) *Which motor:* DESIGN_STATE says the D-flat was seen on "17HS4401s"; the shopping list says SIMAX3D 42-38 (36 N.cm, 1.5 A). From memory (not in the repo; check the nameplate) the 17HS4401 is usually sold at 1.7 A, about 1.5 ohm, about 40 N.cm. If so, 40 N.cm at 1.7 A scales to 25.0 N.cm at 1.0625 A (slip 33.3 N, -2 %), the manual's "x1.111, require SF 3.33" sensitivity does not apply, and motor heat is 1.0625^2 x 1.5 = 1.69 W (not 2.03 W). A meter reading of R_phase (planned anyway) and the nameplate settle both.

**U2. Line entry.** The STEP has no pulley or outlet. The drum stand-in is the right load path only for a line that leaves the drum and passes freely
through an opening. If an outlet or pulley is fixed to the shell/slide-in, the motor tab sees T along the drum-to-pulley leg (still magnitude T), and the pulley bracket
sees an extra reaction up to T x |u_out - u_leg| (up to 1.41 T for a 90 deg turn) that this study does not load. Section 1.4(1) flags this; keep it on the slide.
Also: at y = 18 mm the 34 N line load exceeds the roughly 25 to 30 N at 20 mm typical NEMA 17 front-bearing radial rating quoted in R4. The motor bearing is outside this study.

**U3. Fin versus ceiling.** The fin top is 229 mm above the shaft axis (250 mm plate, axis 21 mm above its bottom edge). `config/robot.sim.json` puts the anchor
0.15 m below the ceiling (z 2.5932 vs 2.7432 m). If the shaft axis is near anchor height the fin reaches about 80 mm into the ceiling, and a ceiling hot-air layer would cut h below the free-plate value used. Confirm the station height; the hold test with a thermocouple at 100 mm will show it.

---

## 3. Agree / disagree by result (my numbers beside the manual's)

### Study A, loads and geometry

| Result | Manual | Mine | Verdict |
|---|---|---|---|
| Driver current | 1.0625 A | 0.85/(8 x 0.1) = 1.0625 A | AGREE |
| Holding torque at 1.0625 A | 0.2550 N.m | 0.2550 | AGREE (basis: U1) |
| Slip-limit, empty core 7.5 mm | 34.0 N; 32.0 @1.0 A; 48.0 @1.5 A | 34.00; 32.0; 48.0 | AGREE; consistent with D30 "~34 N" and the erratum's "holding/snag, not running" |
| Running pull core / full spool / design | 23.8 / 17.85 / 11.9 N | 23.80 / 17.85 / 11.90 | AGREE with memo; label M10 |
| Dynamic 2x | 68.0 N (SF 1.5 identical to SF 3 at 34 N) | 68.0; identity holds (linear) | AGREE; slide wording M6 |
| 40 N.cm sensitivity | 37.8 N | 37.8 | AGREE arithmetic; basis U1(b) |
| Allowables 8.33 / 16.7 / 7.5 / 5.83 MPa | as stated | 25/3, 25/1.5, 22.5/3, 0.7x25/3 | AGREE arithmetic |
| Is 25 MPa derated yield, SF 3 justified? | stated from guide/R5 | 25 MPa is a design allowable, not a measured PETG yield (printed Z strength about 20 to 30 MPa, bulk yield higher); with SF 3 on a motor-limited snag load and a load bound that ignores the flange seat it is conservative for a short event. It is the right size for the sustained case: 8.33 MPa x 17.85/34 = 4.4 MPa = SF 5.7 on 25 MPa, about 10 % of UTS, a usual creep screen. | AGREE as a design rule; say so (M6); hot case L3 |
| Deflection limit 0.5 mm @34 N | 68 N/mm, 22.7x line, 4.2 % added compliance, 2.5 % of 20 mm | same | AGREE (proposed criterion, matches guide Study 1's 0.5 mm at 32 N); measurement H3 |
| Room angles 38.9 / 79.2 / 84.3 deg | as stated | 38.9 / 79.2 / 84.3 | AGREE |
| Direction vectors D1 to D5, D4f | six unit vectors and force components | all match to 1e-4 (e.g. D2 (16.67, 16.67, -24.50), D3 (33.34, 0, -6.66), D4f (29.95, -14.93, -5.99)) | AGREE; reachability M1 |
| Fleet limit | 26.1 deg | atan(8/sqrt(18^2-7.5^2)) = 26.05 deg | AGREE |
| Tangent points | e.g. D2 (6.20, 18, 4.22), D3 (1.47, 18, 7.35) | same; torque sign identical for D1/D2/D3 (+0.255, +0.222, +0.255 N.m) | AGREE |
| Motor-tab hand estimate (nominal sigma / vM, MPa) | D1 0.65/3.25, D2 1.70/3.16, D3 3.36/3.41, D4=D5 5.55/5.63, D4f 4.93/4.94 | identical (signed-corner calc; tab 42.3 x 5.0 verified in the STEP: area 211.5 mm2, Iy 31,536, Iz 440.6 mm4) | AGREE |
| Stress x1.5 to x2.5 root band | 4.9 to 14.1 MPa | judgement, not derivable; band straddles the 8.33 / 7.5 limits for D1, D3, D4f | NOTE: the manual should say plainly that this study is expected to be a design-finding study (limits likely exceeded at the sharp corner/D4f) |
| Exit deflection column | table in section 0 | see H3 | DISAGREE |
| Screw tension / shear | 11 N / 6.5 N (D1) | see M3 | AGREE D1, D3; DISAGREE D2, D4, D5 |
| Dovetail/J-lip bearing | 0.065 / 0.024 MPa | 0.055 (30 deg measured) / 0.024 | AGREE; L2 |
| Weights | 2.845 N motor, 2.453 N shell (0.25 kg assumed) | same | AGREE |
| P5 reaction table | 39.30 / 29.80 / 11.96 N (Z) | 49.5 / 40.0 / 22.2 N (Z) | DISAGREE (H1) |
| STEP geometry | wall 33.9 x 220 x 145, back face -42.32, 6 holes (y -2.78/34.22, z -34.75/10.25/55.25), Ø3.97/Ø7.94, J-lip faces x -20.97 (2,755 mm2), grooves y -34.40/15.56/65.60, shelf z -55.90, tab y 0 to 5, pilot R11.2, holes (+/-15.5, +/-15.5), shell screws, 36.7 mm3 overlap, 0.88 / 0.18 mm gaps | all re-measured: match (overlap 36.75 mm3, one solid, x -32.43 to -29.84, y 11.25 to 12.17, full height). Part files vs assembly: wall identical in topology and within 0.03 mm (917 mm3), slide-in differs by the encoder recess (703 mm3 at x -26.1..-21.2, y 33..57, z +/-12) plus noise | AGREE; L1 |

### Study B, thermal

| Result | Manual | Mine | Verdict |
|---|---|---|---|
| Motor heat | 2.03 W | 1.0625^2 x 1.8 = 2.032 | AGREE (R_phase assumed; U1) |
| Churchill-Chu / simple h at 3, 5, 10, 15, 20 K | 2.69/3.09/3.75/4.21/4.57; 2.79/3.18/3.78/4.18/4.49 | 2.69/3.09/3.76/4.21/4.57; same | AGREE (vertical-plate correlation, L = 0.2 m, 300 K film, correct form) |
| Radiation h_r | 0.60 (bare), 5.4 to 5.8 (paint) | 0.60 to 0.64; 5.44 to 5.78 | AGREE (linearised to room at 23 C, view factor 1) |
| Converged combined h | 9.6 paint, 5.3 bare | 9.59 (3.96 + 5.63), 5.33 (4.68 + 0.66) | AGREE |
| eta, m, R_fin, painted 0.019 in | 0.32, (15.4), 18.3 K/W | 0.3227, 15.43 1/m, 18.34 | AGREE |
| bare 0.019 in | 0.43, 25.1 | 0.4274, 11.46, 25.09 | AGREE |
| 1/8 in painted | 0.69, 8.5 | 0.6936, 6.02, 8.53 | AGREE |
| 1/8 in bare | 0.80, 13.4 | 0.7979, 4.47, 13.44 | AGREE |
| Alloys (3003 / 5052 / 6061) | eta .315/.294/.323, R 18.8/20.1/18.3 | .3151/.2939/.3227, 18.78/20.14/18.34 | AGREE |
| Formula rises (base, tip) | 37.3/3.4 (paint), 51.0/10.2 (bare), 17.3/9.6 (1/8) | 37.3/3.40, 51.0/10.19, 17.3/9.55 | AGREE; station label M4 |
| Quasi-1D patch average | 50.2 / 62.4 / 19.3 / 28.7 K | 2-D solve 51.6 / 63.8 / 19.5 / 28.9 (+2.8 %, +2.2 %, +1 %, +0.7 %) | AGREE (well inside the +/-20 % band) |
| Rises at y = 42, 50, 100, tip (paint) | 39.9, 35.6, 16.6, 3.2 | 40.1, 35.7, 16.5, 3.2; bare 52.3, 47.9, 27.4, 9.6 vs manual 52.1/47.8/27.5/9.5 | AGREE |
| Energy balance F3 / F2 | 1.94 / 0.095 W | total 2.032 W closes; with the 0.85 mm side strips convecting (as section 3.3 asks) F2+strips take about 0.12 W and the balance shifts by about 1 % | AGREE (note: the quasi-1D used for the target leaves the side strips adiabatic; difference about 1 %) |
| Contact R_c | 0.07 / 0.25 / 1.00 K/W (A = 1,359 mm2) | 0.074 / 0.245 / 1.000 (A = 1,358.7) | AGREE |
| Coupled motor temperature, vented (none / bare / paint / 1/8 paint) | 50.9 / 43.2 / 41.6 / 35.1 C | 50.9 / 43.3 / 41.8 / 35.2 | AGREE (within 0.3 K, 2-D vs quasi-1D) |
| Sealed (none / bare / paint / 1/8 paint) | 63.8 / 49.7 / 47.3 / 37.7 C | 63.8 / 50.0 / 47.6 / 37.9 | AGREE |
| Heat through the fin, vented, paint / 1/8 | 0.72 / 1.21 W | 0.70 / 1.21 | AGREE |
| B-2 block convection h | 10.1 (vented), 8.7 (sealed) | 1/(12 x 8219 mm2) = 10.14; 1/(14 x ...) = 8.69 | AGREE |
| Time to steady, 60 min fraction | 94 % at 60 min vented, 95 % at 65 min, sealed 104 min | 94 %, 65 min, 105 min (sealed 84 % at 60 min) | AGREE (consistent with FUNDAMENTALS' 35 min sealed time constant) |
| Model B-1 corresponds to the hand calc? | "same exposed length, h on both faces" | same L = 200 mm above z = 50, 2h on two faces, adiabatic tip, heat over the patch; differences: formula base is z = 50 not 42 (M4), side strips (about 1 %), uniform patch flux (an isothermal flange would give a slightly lower patch mean, conservative) | AGREE with M4 relabel |
| FUNDAMENTALS topic 3 reconciliation | within 1.5 K | reproduced FUNDAMENTALS (40.7/46.0 C, 39 %/50 %, 36.3/39.4 C for 1/8 in) | AGREE on numbers; wording M7 |

---

## 4. Usability (can a first-time Simulation user follow it?)

Overall the structure is good (answer sheet first, named faces with coordinates, annotated figures, explicit limits, convergence and equilibrium checks,
troubleshooting table, fallbacks flagged "if your release differs"). Specific points:

| Step | Judgement |
|---|---|
| Add-in, MMGS, custom PETG, Apply Material to All, Exclude from Analysis, New Study -> Static / Thermal, Fixtures/External Loads Advisor, Remote Load (Direct Transfer) with reference coordinate system, Gravity, Curvature-based mesh with Apply Control, List Resultant Force, Probe -> On selected entities, Define Factor of Safety Plot (including "Areas below factor of safety", user-defined limit), Duplicate study, Select Tangency | Paths and names look right for 2023-2026 as far as I can judge |
| 3.1 import "as an assembly" | The STEP does carry assembly structure (8 usage occurrences, 5 components), so it should open as an assembly; the exact import option wording may differ |
| 3.2 Point -> Arc center -> Coordinate System | Fine; the check value (1269.08, 738.76, 927.56) matches `O_ASM` and the pilot centre in the STEP |
| 3.3 Delete Face | H4 |
| 3.6 Option A "Ignore clearance for surface contact" | Plausible (Component Contact -> Bonded -> options) but I cannot confirm the label or that it applies to Bonded in your release; the Option B fallback is described and adequate |
| 4.1 Roller/Slider variant | M2 |
| 4.2 Remote Load location and reference coordinate system | Correct approach. Add: "Force sign: pull on the station = +T u (u points toward the claw)" and "the same four S3 faces carry L1 and L2; this is allowed, check both appear under External Loads" |
| 8 FoS plot "criterion Max von Mises -> Yield strength" and the 1st-principal plot via Edit Definition -> P1 | Right; the first-principal limit is a user-defined 22.5 MPa |
| Thermal 3: "Heat Power", "Convection", "Radiation", "Define Shell by Selected Faces", "List Net Heat Power" | Names look right; the manual already hedges for release wording. If the radiation option is used, also set the Stefan-Boltzmann constant in the study properties and check absolute-temperature units |
| Thermal contact resistance in B-2 | Hedged by the manual ("may be labelled thermal resistance or contact resistance"); fine |
| Pass/fail explicitness | Static: P1/P3/P4/P7 are not yet explicit (H2, H3, M3); P2, P5, P6 are. Thermal: only a prose "Passing means"; add the section 11-style template (M5) |
| Results template vs slide 10 ("peak stress, safety factor, deflection at the cable exit against 0.5 mm", fundamentals box sigma = Mc/I, screw pull-out, delta = FL^3/3EI) | Template captures peak vM, location, p1, min FoS, exit URES, SF at 17.85 and 68 N, convergence, screw reactions. Missing: hand-versus-FEA column (the "within a factor of 2" check), the evidence label SIMULATED, the per-case `STATION` load-point entry, and the screw capacity number (M3). Thermal slide (backup B5) needs the template of M5 |

---

## 5. Items that do not need to change (checked and sound)

- Equal torque sign and tangent-point construction for D1/D2/D3 (the line always rotates the drum the same way).
- The factor-of-safety identity (SF 3 at 34 N = SF 1.5 at 68 N) and the single-run-then-scale approach (linear model).
- The status note quoting the erratum and the capacity memo (34 N is the holding/snag load; 23.8/17.9/11.9 N the running/design values; 3:1 option gives about 2.7x, roughly 92 N).
- Hand-estimate structure for the tab root: the cantilever with a rigid motor and the root section 42.3 x 5.0 mm is the right first-order model; the lower-lug gussets (y 5.56 to 13.06 and 18.06 to 25.56, z below -31) do not connect to the tab in z, so ignoring them is correct and mildly conservative.
- Natural-convection and radiation treatment, using the combined h in a linear study, holding h fixed across alloy/thickness, the isothermal-plate correlation applied with the mean fin rise (an approximation the +/-20 % band covers).
- The bonded-contact decision for the tab-root objective (with the corrections in M9).
- The statement that nothing holds the slide-in up, and that this is acceptable only because the line never has a +z component (R3's insertion-direction advice is respected: the load seats the housing downward).

## 6. Files

Written: `/home/user/RoomCleaner/verification/simulation_manuals_review.md` (this file). No manual, script, test, CAD or parameter file was edited. Nothing was committed or pushed.
