# Independent check: `calculations/lift_chain_weakest_link.py` (weakest link of one winch station's lifting chain, 1.5 A)

Checker: calculation-checker (Sonnet 5.5), 2026-10-22. Scope: arithmetic, units, inputs, boundary conditions, margins, and whether the
ranking and the four recommendations follow from the numbers. No CAD, parameter, or calculation file was edited. The script was run as
instructed; it regenerated `calculations/lift_chain_weakest_link.json` byte-identically (`git status` clean afterwards).

Independent arithmetic (written fresh, not importing the script's functions) is in the session scratchpad, outside the repo:
`/tmp/claude-0/-home-user-RoomCleaner/c51aa926-76d6-52eb-b707-af7c5e22fd24/scratchpad/check1.py` (fuse, line, set screw, D-flat, shaft, encoder),
`.../check2.py` (tab root with signed face stresses and a direction scan), `.../check3.py` (wall screws, drywall, stud, motor screws, sensitivities).

## 1. Verdict

**Arithmetic: agree.** Every number the script prints reproduces to within 0.3 % (table in section 3). No unit error found.

**Modelling: two errors, one stale input, several missing inputs.** None changes the order of the ranking; one changes a printed ratio
(tab "as drawn": 1.05 becomes 1.38, still MARGINAL), and three PASS rows are fragile (insert 1.66, tab with fillet 1.74, and anything
that depends on the unverified 1.5 A setting).

| ID | Severity | Finding | Effect on ranking |
|---|---|---|---|
| F1 | **Medium** | The tab's "sharp back corner" row applies Kt 2.5 to case D4f, but D4f puts the **back** face in compression (-6.6 to -7.3 MPa) and tensions the **spool-side** face, which already has the R2.5 fillet. The manual itself says only D5 tensions the back corner (`SW_STATIC_STATION_MOUNT.md` lines 209, 474). | "Tab, sharp back corner" 62 N / 1.05 becomes **82 N / 1.38** (governing case is a straight-down pull fleeted toward the spool, not D4f). Still MARGINAL, order unchanged. The "2 mm fillet" row (103 N / 1.74) is in fact the existing front fillet at D4f, i.e. what the tab already has on that face. `calculations/lift_chain_weakest_link.md` item 2 ("gives just above the motor when the cable pulls along the wall") is wrong as worded. |
| F2 | **Medium** | PETG strength is taken at room temperature. The repo defines `HOT_DERATE = 0.7` (simulation_loads.py) and the manual carries a hot-tab sensitivity; the chain script ignores both. Motor case is 57.6 C (0.019 in fin, D37) or about 45 C (1/8 in fin, D38). | Tab with fillet 1.74 becomes **1.47 (x0.85) or 1.21 (x0.70)**: PASS flips to MARGINAL. Set-screw clamp relaxation in warm PETG also lowers the printed-thread range. |
| F3 | **Medium** | The brass-insert row (PASS 1.66) assumes the screw can be seated to the steel-thread rating, but never checks the **insert's own pull-out** in PETG (the set-screw reaction pulls the insert outward with 565 to 753 N) or whether an insert fits: the hub wall from OD to bore flat is 5.275 mm, the repo's standard M3 insert is 5.7 mm long (`THERMAL_DECK_INSERT_LEN`). | 1.66 flips to MARGINAL for K = 0.25 (1.33), mu 25 % lower (1.30), no cup bite (1.45), or an insert pull-out below 500 N (1.47). The recommendation (insert beats printed thread) follows; the "1.66 x" figure does not. |
| F4 | **Medium** | The printed-thread set-screw verdict "GIVES FIRST" (0.48) is the pessimistic end of a range that straddles the fuse (0.19 to 0.55 N.m against 0.255 to 0.40). It rests on the thread-strip area factor (0.5 pi d L; a tooth-base area gives x1.75) and the friction values, all `[ASSUMED]`. | Honest label is "may give first". Monte Carlo over plausible inputs: P(slip below 0.36 N.m) = 0.35 to 0.82. Direction supported, magnitude not. Needs the bench test the .md already proposes. |
| F5 | **Medium** | Stale bore: script uses bore 5.45 / flat 2.225 mm from the axis (R4, Spoolv3 10/18); `cad/params.py` (`ENC1021_BORE_D = 5.30`, `ENC1021_BORE_FLAT_X = 2.15`) is the 10/21 reference spool the encoder cap and D38 are built on. The .md design change 2 (print bore 5.15, flat 4.62 across) contradicts the repo's own print history (a 5.2 bore was "too tight", DECISION_STORIES T24, hence 5.45) and the cap's 5.10 peg. | D-flat backup is 13.8 deg / 0.98 mm lever / 367 N at 0.36 N.m (408 N at 0.40), not 25.4 deg / 0.50 mm / 724 N. The D-flat contact is never compared with a capacity (Hertz line contact of steel on PETG is 113 to 155 MPa against PETG yield 25 to 50 MPa). Not in the ranking, so no order change. |
| F6 | **Low-Medium** | The whole table scales with the real driver current. D37 says how 1.5 A was reached is "not yet recorded" (Vref/VDD/Rs). 60 counts is a simulation value; `robot.example.json` has `tracking_tol_counts: null`. | At 1.7 A the fuse upper is 67.3 N: insert 1.47, tab-with-fillet 1.53. Detection needs a hardware tolerance below 82 counts (margin 1.37 only). |
| F7 | **Low** | Shaft and motor-screw levers measure from the tab back face and omit the heat fin: the motor front face is 2.0 mm (reference CAD) to 3.175 mm (D38 fin) behind it. | Shaft lever 21 becomes 23.0 to 24.2 mm: yield 171 N becomes 149 to 157 N (ratio 2.89 becomes 2.5 to 2.6); front-bearing factor 1.70 becomes 1.81; screw prying 0.29 becomes 0.34 per N (4.3 kN becomes 3.7 kN). All still PASS. |
| F8 | **Low** | Presentation: (a) set-screw line-tension equivalents multiply by 1/cos(fleet) for the lower end too, so "29 N" should be 25.7 N unfleeted (the ratio uses torque and is right); (b) dovetail row lower = 1000 is a hard-coded placeholder printed with a ratio of 16.84 (computed value 15.7 kN); (c) `MOTOR_SENS` is tagged `[REPO]` but is `[USER, unverified]` in simulation_loads.py; (d) the wall-screw lower bound is an NDS design value (safety factor 5.5 built in) while other rows are yield or ultimate; (e) .md says the top screw sees 34 N "at the motor's upper slip force": that is at 53.4 N; at 59.4 N it is 38 N. | None. |
| F9 | **Low** | Duplicated constants not imported from `cad/params.py` (shaft 5.0 / flat 0.5, pattern 31, head 5.5, hole 3.5, tab 5.0); values agree today. `DYNEEMA_DIA = 1.0` in params.py contradicts the 0.5 mm used in R4 and simulation_loads (script is insensitive to it). | None. |

## 2. Supplied facts, assumptions, derived results, unresolved uncertainty

**Supplied facts (recorded in the repo, file named):**
- Motor: SIMAX3D 42-38, about 36 N.cm at 1.5 A (`docs/SHOPPING_LIST.md` line 22, marked "unverified" at line 37). Driver current 1.5 A (D37, Vref 1.2 V on R100).
- Spool: core r = 7.5 mm, full r = 10 mm, flanges r = 18, drum 16 mm wide (R4, STEP Spoolv3); shaft Ø5 with a 0.5 mm flat (`cad/params.py`); hub Ø15, radial Ø2.8 set-screw hole on the flat's axis 7 mm from the base (R4).
- Motor screws M3 x 12, 3.8 mm thread (D38); tab 5.0 mm, holes Ø3.5, pattern 31 mm (`cad/params.py`).
- PETG 25 MPa derated yield, 45 MPa UTS, 22.5 MPa across layers (SIMULATION_GUIDE, R5).
- Line: 9KM DWLIFE X8, 120 lb, diameter "requires measurement" (`SHOPPING_LIST.md` line 23).
- Wall plate y -94.44 to 125.56, screw columns y -2.78 / 34.22, rows z -34.75 / 10.25 / 55.25, counterbore floor 10.53 mm of PETG (manual 1.3).
- Tracking fault 60 counts, 0.15 s (`config/robot.sim.json`, simulation profile only); AS5600 4096 counts per rev; spool encoder confirmed by `ENC1021_*` (magnet cap head on the spool face, D-peg in the spool bore).

**Assumptions in the script (all tagged `[ASSUMED]` or `[SRC]`; none is recorded as approved in DECISIONS.md, so treat all as unapproved):**
mu_tip 0.20, mu_bore 0.25, cup bite 1.15, K 0.20, seat fraction 0.5 to 0.8, PETG thread shear 0.58 x (25 to 45), 3 to 4 in-lb seat torque, Kt 2.5 / 1.5, shaft yield 350 to 600 MPa, bearing C0 380 N and 3 mm / 30 mm geometry, 120 MPa aluminium shear, knot efficiency 50 to 90 %, capstan mu 0.05 to 0.10, 1 in of thread in the stud, 1/2 in drywall, drywall-only ratings, Y_DRUM = 18 mm (assumes the 22 mm Spoolv3), shell 0.25 kg, print orientation (tab loaded across layers).

**Derived results (reproduced independently):** section 3.

**Unresolved uncertainty (largest first):** actual driver current and motor torque (0.255 to 0.40 N.m span, plus D37's unrecorded setting); set-screw friction, strip area, creep; hot PETG strength; insert pull-out; which spool (5.45 or 5.30 bore) is built; real line strength; whether the screws land in a stud; dynamic back-driving torque of a stepper (regeneration through the driver) is not in any holding-torque figure; fault reaction after TRACKING is outside this calculation.

## 3. Item-by-item check (script value / my value / agree)

### 3.1 Units and arithmetic, every link

| Quantity | Script | Mine | Result |
|---|---|---|---|
| hold 1.5 A; slip empty / full; run core / full | 0.36; 48.0 / 36.0; 33.6 / 25.2 N | 0.36; 48.0 / 36.0; 33.6 / 25.2 | agree |
| fleet limit; 1/cos | 26.1 deg; 1.1131 | 26.054 deg; 1.11312 | agree |
| fuse low / fleeted / upper | 33.9 / 53.4 / 59.4 N | 33.94 / 53.43 / 59.37 | agree |
| jeans peak; holding and moving ratio | 16.2 N; 2.96 / 1.56 | 16.20; 2.963 / 1.555 | agree |
| line 120 lb; knot 50 to 90 % | 534; 267 to 480 N | 533.8; 266.9 to 480.4 | agree |
| capstan, 3 wraps | 15 to 39 % | 15.2 to 39.0 % | agree |
| set-screw lever; thread length; strip area | 1.025 mm; 4.8 mm; 22.5 mm2 | 1.025; 4.775; 22.50 | agree |
| strip / seated / torque, printed | 326 to 587 N; 163 to 470 N; 0.19 to 0.55 N.m | 326.3 to 587.3; 163.1 to 469.8; 0.192 to 0.554 | agree |
| insert seat force / torque | 565 to 753 N; 0.67 to 0.89 N.m | 565.0 to 753.3; 0.666 to 0.888 | agree |
| D-flat (5.45): turn / lever / force | 25.4 deg; 0.50 mm; 724 N | 25.39; 0.497; 723.6 | agree (input stale, F5) |
| D-flat (5.15, 0.525): turn / lever / force | 5.1 deg; 1.32 mm; 273 N | 5.08; 1.317; 273.4 | agree |
| shaft Z (D-section); yield 350 / 600 MPa | 10.29 mm3; 171 / 294 N | 10.31 (general bending, 3000 grid); 172 / 295 | agree |
| bearing static; load at fuse | 224 N; 101 N | 223.5; 100.9 | agree |
| motor screw strip / punch / per N / line | 2579 / 1253 N; 0.29; 4315 N | 2578.6 / 1252.7; 0.2903; 4315 | agree |
| tab sharp, D1 / D2c / D3 / D4f | 105 / 112 / 91 / 62 N | 105 / 112 / 91 / 62 | agree |
| tab fillet, D1 / D2c / D3 / D4f | 174 / 187 / 152 / 103 N | 174 / 187 / 152 / 103 | agree |
| dovetail bearing at fuse; yield line force | 0.094 MPa; 15,708 N | 0.094; 15,750 | agree |
| NDS #6 SPF 1 in: design / ultimate | 309 / 1700 N | 308.6 / 1700.1 | agree |
| screw lateral; head punch | 271 N; 3166 N | 270.9; 3165.8 | agree |
| one-column top screw D1 / D2c / D3 / D4f | 30.1 / 34.2 / 25.9 / 29.6 N | 30.1 / 34.2 / 25.9 / 29.6 | agree |
| line force at design value D1 / D2c / D3 / D4f | 551 / 531 / 656 / 626 N | 551 / 531 / 656 / 626 | agree |
| six-screw top screw | 15.1 / 25.8 / 12.1 / 21.4 N | same | agree |
| bare drywall 5 lbf (six screws) | 74 / 46 / 95 / 56 N | 74 / 46 / 95 / 56 | agree |
| stud bending | 0.72 vs 6.0 MPa | 0.722 vs 6.03 | agree |
| detection | 5.3 deg; 7.2 deg = 82 counts; 0.94 mm | 5.27; 7.2 = 81.9; 0.942 | agree |

Parameter provenance: all values that the script reads from `simulation_loads` are used consistently (R_EMPTY, R_FULL, Y_DRUM, PETG, Z_STRENGTH, screw rows/columns, weights). Hard-coded duplicates agree with `cad/params.py` except the bore (F5) and the line diameter note (F9).

### 3.2 The fuse: **agree**, with caveats
- 0.36 N.m x 1.111 / 7.5 mm / cos 26.05 deg = 59.37 N. Using the line centre (r = 7.75 mm for a 0.5 mm line) gives 57.5 N, so r = 7.5 mm is the conservative choice. Fleet limit is smallest at the empty core, so the empty spool is the true upper end (full spool with its wider limit: 45 N).
- 1/sqrt2 is correct physics (A4988 holds I_a^2 + I_b^2 = I_trip^2; the datasheet figure is both phases at rated current), but it is the **expected value**, not a remote lower bound: the "central" 48 N is the optimistic reading. This does not hurt the ranking, because the ranking uses the upper bound. It matters for lifting margin (moving pull at a full spool becomes 17.8 N against the 16.2 N jeans demand).
- The 40 N.cm sensitivity is a one-sided conservative bound (a 17HS4401 rated 1.7 A would give about 35 N.cm at 1.5 A; that datasheet is not in the repo, so unverified).
- Current is the largest hidden dependence (F6): fuse upper = 59.4 x (I / 1.5 A).
- Rotor-inertia allowance: J/r^2 for a NEMA 17 rotor is about 0.15 kg of equivalent line mass, so 10 m/s^2 adds about 1.5 N; the 1.5 factor is therefore almost all scatter allowance, which is reasonable.

### 3.3 Set-screw joint and D-flat geometry (item 3): **model agrees; conclusion supported in direction, over-stated in label**
- Friction lever 0.2 x 2.0 + 0.25 x 2.5 = 1.025 mm per newton: correct geometry (flat at 2.0 mm from the axis, bore contact at the shaft radius).
- Insert seat force F = T/(K d): 0.339 / (0.2 x 3e-3) = 565 N; correct. The step from seat force to joint torque is a single multiplication, so the ratio is directly proportional to K, mu and cup bite (sensitivity table below).
- `dflat_engagement` is correct: it puts the shaft against the round side, finds the corner contact when the corner's extent along the bore-flat normal reaches 2.45 mm, and takes the lever as r sin(a1). My independent derivation gives the same 25.39 deg / 0.497 mm. Correct input for the current reference spool (5.30 / 2.15): 13.8 deg, 0.98 mm, 367 N.
- The "can slip below the motor's holding torque" conclusion: supported as a possibility. The lower end (0.19 N.m) is 53 % of the nominal and 75 % of the 1/sqrt2 torque; unmodelled creep and heat only lower it. But the range is a stack of unmeasured factors, and two plausible reading choices move it a lot (strip area x1.75: range becomes 0.34 to 0.97 N.m; mu_tip 0.4 / mu_bore 0.35 for clean dry steel: x1.6).
- Monte Carlo (200,000 draws, uniform inputs): median printed-thread capacity 0.28 N.m (script-like mu) ; P(capacity < 0.255 / 0.36 / 0.40) = 0.36 / 0.82 / 0.91 with the script's mu ranges, 0.05 / 0.35 / 0.49 with wider mu ranges (tip 0.15 to 0.40, bore 0.20 to 0.40).
- Not covered: PETG creep/relaxation of the clamp; the screw's 1.5 mm hex key limiting seat torque; a 0.1 mm partial thread depth in a Ø2.8 hole (strip area is not a clean 0.5 pi d L).
- Honest wording: "the printed-thread set screw may give before the motor; its range straddles the fuse; measure". Consequence of a slip is benign in itself: the spool encoder (cap in the spool bore) sees the spool move 25 deg (289 counts) or 13.8 deg (157 counts) before the flat catches it, so TRACKING trips either way; the real risk is the unrated D-flat contact (F5).

Sensitivity of the **insert** row (ratio to 0.40 N.m; script 1.66):

| Change | Torque N.m | Ratio | Verdict |
|---|---|---|---|
| none | 0.666 | 1.66 | PASS |
| K = 0.25 | 0.533 | 1.33 | MARGINAL |
| K = 0.30 | 0.444 | 1.11 | MARGINAL |
| mu_tip 0.15 | 0.601 | 1.50 | borderline |
| mu_bore 0.20 | 0.585 | 1.46 | MARGINAL |
| both mu lower | 0.520 | 1.30 | MARGINAL |
| no cup bite | 0.579 | 1.45 | MARGINAL |
| seat force capped by insert pull-out 300 / 400 / 500 / 600 N | 0.354 / 0.471 / 0.589 / 0.707 | 0.88 / 1.18 / 1.47 / 1.77 | |
| mu_tip 0.4, mu_bore 0.35 | 1.088 | 2.72 | PASS |

### 3.4 Tab scaling and the worst reachable case (item 4): **arithmetic agrees; face/Kt pairing disagrees (F1)**
- Linearity: confirmed. Every term of `tab_root_estimate` (axial, both bending moments, torsion, shear) is homogeneous of degree one in F, and the load point depends only on the direction, so `per_N` scaling is exact. (Weights of the motor and spool, 2.9 N, are left out of the hand model; effect is under 6 % on D1 only.)
- Hand-model nominal stresses at 1.5 A reproduce the manual's 34 N figures x 1.412 (D4f 5.5 x 1.412 = 7.77 MPa).
- Signed stresses (sigma_x = Fx/A + My z/Iy - Mz y/Iz, M = r x F about the root centroid; front = spool side y = +2.5 with the R2.5 fillet, back = y = -2.5 sharp corner), 1.5 A, MPa, tension positive, range over the section corners/centre:

| Case | T (N) | Front (fillet) face | Back (sharp) face | Shear | Line force that gives, front Kt 1.5 | back Kt 2.5 |
|---|---|---|---|---|---|---|
| D1 | 48.0 | +0.9 / -0.9 | +0.9 / -0.9 | 2.60 | 174 | 105 |
| D2c | 53.4 | -0.3 / -1.9 | **+2.2 / +0.6** | 2.45 | 210 | 112 |
| D3 | 48.0 | +4.7 / +4.0 | -3.5 / -4.3 | 0.51 | 152 | no tension |
| **D4f (-y)** | 53.4 | **+7.7 / +7.0** | **-6.6 / -7.3** | 0.25 | **103** | no tension |
| D5f (+y, 78.7 deg) | 53.4 | +1.7 / +1.0 | -0.5 / -1.3 | 1.13 | 341 | no tension |
| D1 fleeted +y (theta 0) | 53.4 | negligible | **+4.7** | | | **82** |
| D5 pure sideways (unreachable) | 48.0 | -7.5 / -7.8 | +7.8 / +7.5 | 0.78 | 595 | 55 |

  The script's rows are the sum-of-absolute-values nominal (which my abs-sum reproduces exactly: D4f 7.75 MPa), then one Kt for the whole section.
- Physical check of the sign: the line pulls at y = +18, 15.5 mm toward the spool from the tab mid-plane, so a pull away from the wall (+x) is an eccentric tension that stretches the **spool-side** face. A pull toward -y adds to it. The back face is stretched only by a +y pull with little +x pull (D5, D2c, D1 fleeted +y).
- Scan over every direction (theta 0 to 88 deg, both fleet signs, all fleet fractions): worst **front-face** case is theta = 69 to 79 deg fleeted toward -y: 102.6 N, so D4f is the worst reachable case for the filleted face (agree). Worst **back-face** case is theta = 0 fleeted toward +y: 81.8 N (85 N at theta = 6 deg, which is what the 0.2 m wall margin allows at a 2.2 m line). Neither is D4f for the sharp corner.
- Corrected tab rows (Kt 2.5 sharp / 1.5 fillet as in the script, 59.37 N fuse): as drawn = min(front 103, back 82) = **82 N, ratio 1.38 MARGINAL**; with a 2 mm back fillet = min(103, back 136) = **103 N, ratio 1.73 PASS**, limited by the existing front fillet at D4f. So the 2 mm back fillet still moves the row from MARGINAL to PASS (recommendation 3 follows), for a different reason than stated.
- The across-layer criterion (22.5 MPa) governs D4f, not the 25 MPa yield. It is 50 % of UTS and the print orientation is assumed. At 40 % (18 MPa) the fillet row is 83 N (1.39); at 30 % it is 62 N (1.04). With the hot derate: x0.85 gives 87 N (1.47), x0.70 gives 72 N (1.21) (F2).
- Kt values: 2.5 for a printed sharp corner and 1.5 for r/t = 0.4 to 0.5 are consistent with published stepped-bar charts (my recollection, not repo evidence); a true sharp corner has no finite Kt, so 2.5 is a modelling choice.
- The .md's SF = 2.15 (5 mm tab) and 3.04 (6 mm tab) at 1.5 A reproduce with the repo's own `tab_root_estimate` (2.15; 3.10 with y_c = 3.0), deflection 0.53 mm reproduces exactly, 6 mm gives 0.30 mm.

### 3.5 Wood screws, stud, drywall (item 5): **agree**
- NDS W = 2850 G^2 D per inch (lb, in): 2850 x 0.1764 x 0.138 = 69.4 lb/in = 308.6 N. G = 0.42 is the NDS value for spruce-pine-fir; #6 D = 0.138 in. Ultimate 15,700 G^2 D L = 1700 N (ratio 5.51, consistent with the ICC-ES AC233 divide-by-5 the .md cites). I could not re-derive the 15,700 constant offline; it only feeds the "upper" column, not the verdict.
- Thread in stud: 1.0 in assumed; a #6 x 2.5 in through 10.53 mm PETG and 12.7 mm drywall leaves 40 mm (1.59 in), so the assumption is conservative if the thread is long enough.
- `screws_one_column` treatment: conservative in four ways, optimistic in one.
  Conservative: nearer plate edge chosen (91.3 to 91.7 mm instead of 128 mm); My uses the group centroid with no bearing (about 2x more tension than a bottom-edge pivot would give); other column given zero credit; weights included.
  Optimistic: the Mz pivot is taken at the plate edge on a rigid wall, but the drywall between studs is soft, so the effective lever is shorter. Test with e = 37 mm (the spacing to the drywall-only column): line force to reach the design value falls from 626 to 443 N (D4f), 531 to 439 N (fleeted straight down). Also evaluated both columns and both fleet signs (the script evaluates only y = -2.78): minimum 439 N, ratio 7.4. Verdict (PASS) is robust.
- Not in the ranking but checked: shear per screw 4.5 to 36 N against the 271 N bent-across-drywall lateral value (7.5x or more); head punch 3166 N per screw.
- Drywall only (six screws, published ratings): bare 5 to 10 lbf = 46 to 95 N (ratio 0.77 GIVES FIRST); plastic anchors 10 to 25 lbf = 95 to 244 N (lower end 1.6, within a rating tolerance of MARGINAL); self-drilling zinc 60 lbf is fine. The recommendation "screws into the stud only" is strongly supported. The drywall ratings are web-sourced, not analysed.
- Stud bending 0.72 MPa against 6.03 MPa reference (875 psi): agree, and not limiting.

### 3.6 Shaft modulus, lever, bearing (item 6): **arithmetic agrees; lever input incomplete (F7)**
- D-section (Ø5, 0.5 mm flat): area 18.61 mm2, centroid 0.12 mm off-centre, Iyy 25.44, Izz 30.21 mm4, minimum Z over all bending directions with the full unsymmetric-bending formula = 10.31 mm3 (script 10.29; round shaft 12.27 mm3). Agree.
- Lever 21 mm = Y_DRUM 18 + bearing 3, measured from the tab back face. The motor's front face is 2.0 mm (reference CAD, Heat_horn) or 3.175 mm (D38 fin) behind that face, so the lever is 23.0 to 24.2 mm. With 24.2 mm: yield 149 N (350 MPa) to 256 N (600 MPa), ratio 2.5; front-bearing reaction 1.81 F; static bearing limit 210 N.
- The flat does not extend to the bearing, so using the D-section modulus at the bearing moment is conservative (round section there: 204 N). Run-out Kt at the flat end is not applied; at the flat start the moment is 9 to 12 of 21 to 24 mm, so even Kt 2.5 does not bring it near 89 N.
- Torsion at 0.40 N.m: 16 MPa; negligible.
- C0 = 380 N is `[ASSUMED]`; the datasheet is not in the repo. The 28 N radial figure is a life rating; running pull at the empty core (33.6 N) is 1.2x it with the load 20 mm from the motor face and about 1.3x with the fin offset (load 21.2 mm from the face, rating equivalent 26.4 N): bearing life, not strength, as the script says.

### 3.7 Encoder detection (item 7): **agree, margin thin**
- 60 counts x 360 / 4096 = 5.27 deg. A stepper that loses sync falls to the next equilibrium of the fixed field, one electrical cycle = 4 full steps = 7.2 deg = 81.9 counts. 81.9 > 60: a single skip trips the 0.15 s dwell because the lost cycle is permanent. Agree.
- Margin is only 1.37x; a two-full-step lag (41 counts) alone would not trip. The 60 counts and 0.15 s are simulation-profile values; hardware example configs have null (required for the `station_bench` stage, `config.py` line 556). Any hardware tolerance of 82 counts or more removes single-skip detection.
- The encoder measures the spool (`ENC1021` magnet cap head against the spool face, D-peg in the spool bore), so a set-screw slip is also caught: the spool runs 289 counts before the flat stop (current reference spool 157 counts).
- TRACKING has reaction "stop" (`protocol.py`); what that does to the claw is outside this calculation.

### 3.8 Chain gaps, flips, recommendations (item 8)

**Missing or thin links:**
1. Insert pull-out and fit in the hub (F3).
2. Claw tie-off (Ø3.2 hole, Palomar knot, corner boss) and the spool-side Ø1.4 tie-off hole (0.8 mm ligament to the hub OD) are represented only by the line-knot row. A shear-out bound of 2 x 6.4 mm x 5 mm x 14.5 MPa = 0.93 kN for the claw eye (edge distance assumed 8 mm minus the hole radius) says it is not limiting; the geometry should be confirmed.
3. D-flat backup capacity (F5).
4. Hot and creep derating of PETG (F2).
5. Fin offset in the levers (F7).
6. A line outlet or pulley does not exist in the v3 files (manual 1.4 item 3). If added, it adds up to 1.41 T on whatever holds it.
7. Dynamic back-driving torque of a stepper: regeneration through the driver can brake harder than the static holding figure. The 1.5 factor is the only allowance; this needs a bench pull test, not a calculation.
8. Prototype fin (0.019 in): M3 x 12 would engage 6.5 mm against a tapped depth of 4.0 to 4.5 mm (`THERMAL_MOTOR_HOLE_DEPTH`), so the screws bottom out about 2 mm before clamping; prototype stations need shorter screws. Hardware note, not a strength result.

**Verdict flips under a reasonable change of an assumed input:**

| Row (script verdict) | Change | New ratio / verdict |
|---|---|---|
| Printed-thread set screw (GIVES FIRST 0.48) | strip area x1.75, or higher friction | range 0.34 to 0.97 N.m: straddles, "may give first" |
| Brass insert (PASS 1.66) | K 0.25; pull-out below 500 N; mu -25 % | 1.33 to 1.47 MARGINAL |
| Tab with fillet (PASS 1.74) | hot derate 0.85 / 0.70; across-layer 40 % of UTS | 1.47 / 1.21; 1.39 MARGINAL |
| Tab as drawn (MARGINAL 1.05) | correct face pairing | 1.38 MARGINAL |
| Any row | actual driver current 1.7 A | fuse upper 67.3 N: insert 1.47, tab 1.53 |
| Shaft (PASS 2.89) | lever 24.2 mm | 2.5 PASS. Only an unrealistic combination (weakest steel, Kt 2 on the full bearing-level moment with the flat section, lever 24.2 mm) reaches 1.26 |
| Line knot (PASS 4.5) | label strength x0.6 | 2.7 PASS |
| Wall screws (PASS 8.9) | e = 37 mm; second column; either fleet sign | 7.4 PASS |
| Wall screws in drywall (GIVES FIRST 0.77) | plastic anchors | 1.6 PASS at the 10 lbf rating, 1.28 at 8 lbf |
| Motor screws, plate head, dovetail | any reasonable change | far above 1.5 |

**Do the ranking and recommendations follow?**

| Statement | Follows? |
|---|---|
| Order: printed set screw, fuse, tab as drawn, insert, tab with fillet, shaft, knot, wall screws, others | **Yes.** My corrected values keep this order (set screw 29, fuse 34 to 59, tab as drawn 82, insert 99, tab with fillet 103, shaft 149 to 172, knot 267, wall screws 439 to 531). Above the shaft the exact order is immaterial; the dovetail row's 1000 N is a placeholder (computed 15.7 kN would put it last). |
| "As drawn, the motor is not the weakest link" | **Partly.** The set screw may give first (straddling range); with the tab's corrected 1.38 the tab is also within 1.5x of the fuse. Hot PETG makes the tab the second concern. |
| Use a heat-set insert for the set screw | **Yes in direction** (printed thread is the weaker option on every plausible reading). The "1.66 x" figure is not established (F3); check pull-out and fit first. |
| 2 mm fillet on the tab's back-side root | **Yes**, it lifts the back-corner limit from 82 to 136 N. The stated case (D4f) is the wrong one; D4f is limited by the existing front fillet at 103 N, which the back fillet does not change, so the tab stays at 1.73 and falls to MARGINAL under a modest thermal derate (F2). |
| Screws into the stud only | **Yes**, strongly (bare drywall 46 N gives first; plastic anchors are marginal). |
| Keep dead wraps on the spool | **Qualitatively yes, not required by the numbers.** The line knot at 267 N (4.5x) does not need the 15 to 39 % capstan relief; the benefit is protecting an untested knot and a Ø1.4 hole with a 0.8 mm ligament. Capstan mu is assumed. |
| (from the .md) print the bore at 5.15 mm with a 4.62 mm flat | **Not supported.** Contradicts the repo's print history and the Ø5.30 reference; a 0.12 mm clearance is beyond what an FDM hole holds. If a backup is wanted, size it for the 5.30 reference (13.8 deg) and rate the contact. |

## 4. Corrected ranking (my values; line tension at which each link gives, N; fuse upper 59.37 N)

| Link | Script low / high | My low / high | My ratio | Verdict |
|---|---|---|---|---|
| Spool set screw, printed thread | 29 / 82 | 26 / 74 unfleeted (0.19 / 0.55 N.m) | 0.48 | may give first (straddles) |
| Motor torque (fuse) | 34 / 59 | 34 / 59 | | fuse |
| Tab root as drawn | 62 / 172 | 82 (back, D1 fleeted +y) / 172 | 1.38 | MARGINAL |
| Spool set screw, brass insert | 99 / 132 | 99 / 132 unfleeted 89 / 119, subject to F3 | 1.66 | PASS, thin |
| Tab root with fillet | 103 / 172 | 103 / 172 | 1.73 | PASS, thermal-sensitive |
| Motor shaft | 171 / 294 | 149 to 157 / 256 to 269 | 2.5 to 2.6 | PASS |
| Line knot | 267 / 480 | 267 / 480 | 4.5 | PASS |
| Wall screws, one column | 531 / 2954 | 439 / 2954 | 7.4 | PASS |
| Slide-in dovetails | 1000 / 15,708 | 15,750 (computed) | 265 | PASS |
| Motor screws | 4315 / 8882 | 3668 (fin lever) / 7600 | 62 | PASS |
| Wall plate head pull-through | 5507 / 9913 | 5507 | 93 | PASS |
| Six screws in bare drywall (comparison) | 46 / 95 | 46 / 95 | 0.77 | GIVES FIRST |

## 5. What to measure or decide next (cheapest first)

1. Pull-test the spool joint on the bench with a spring scale or torque wrench: printed thread, then insert, both with a pull-out test of the insert; compare with 0.255 to 0.40 N.m.
2. Record the real driver setting (Vref, VDD, sense resistor) and the motor nameplate; scale the table by I / 1.5 A.
3. Decide which spool is built (5.45 or 5.30 bore) and make `lift_chain_weakest_link.py` read it from `cad/params.py`.
4. Correct the tab pairing (front fillet at D4f, back corner at fleeted straight-down and D2c), add the hot derate, add the fin offset to the levers.
5. Set the hardware tracking tolerance below 82 counts and confirm in the pull test that a single skip raises TRACKING.
6. Relabel the set-screw row "may give first" and replace the hard-coded dovetail 1000 N with the computed value.
