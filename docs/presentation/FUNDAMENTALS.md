# Engineering fundamentals behind the design decisions

Each section ties one design decision to an undergraduate mechanical-engineering relationship: statics, mechanics of materials, heat transfer, dynamics, machine design, measurement and uncertainty, circuits. Every number below is recomputed by one script, `calculations/presentation_fundamentals.py`, from the project's own inputs. The script prints a table and writes `calculations/presentation_fundamentals.json`; re-run it after any input changes (about 20 s, or a few seconds with `--fast`, which skips the linear programs in section 1).

**Evidence tags** (use the same words on a slide):

| Tag | Meaning |
|---|---|
| CALCULATED | worked from stated inputs; the answer is only as good as its assumptions |
| SIMULATED | produced by a model or simulator run on the project's geometry or software; no physical test |
| MEASURED | a physical measurement exists in the project record |
| PLANNED | a test is defined; no result yet |

**How each section is laid out.** Supplied facts (recorded in the project: specifications, measurements, decisions) are listed apart from assumptions (values nobody has measured) and from derived results (computed here). A result built on an assumption is never called measured.

## Headline numbers

| # | Topic | Headline | Evidence |
|---|---|---|---|
| 1 | Cable statics | Tension per cable 32.1 / 16.2 / 8.3 / 4.6 N at 0.15 / 0.30 / 0.60 / 1.20 m below the anchors | CALCULATED |
| 2 | Motor torque to line tension | Vref 0.85 V → 1.06 A → 23.8 N at the 7.5 mm core, 17.9 N at a full spool; Ø10 core: +25 % design force | CALCULATED (Vref MEASURED) |
| 3 | Joule heating and the fin | Sealed shell: 64 °C without the fin, 46 °C with it; the fin carries about 50 % of the heat | CALCULATED, hold test PLANNED |
| 4 | Gear tooth bending | Module 1: safety factor 0.35–0.41 at stall; as built (module 1.5, 6 V): 2.0–2.5 | CALCULATED, jaw force SIMULATED |
| 5 | Grip by friction | 1 lb needs 8.9 N per jaw, jeans 17.7 N (μ 0.3); jaws give 13.3–25 N | CALCULATED vs SIMULATED |
| 6 | Beam bending and creep | Same tube, same load: 0.04 mm in aluminium vs 1.32 mm in PETG (33 ×) | CALCULATED, wall UNMEASURED |
| 7 | Pendulum and tilt | Period 0.89 s at the recorded CoM depth, but that depth is stale (0.12 m estimated now); statics tilt reaches 13° | CALCULATED, tilt reproduced from the cable model |
| 8 | Measurement uncertainty | Lever-arm error 6.6 mm per frame with one tag, 0.7 mm with a four-tag board | CALCULATED |
| 9 | Synchronisation | 2.5 mm length error → 7.5 N spike | CALCULATED, test PLANNED |
| 10 | Wire voltage drop | 32 ft, 2 A: 0.82 V (18 AWG) vs 0.51 V (16 AWG) | CALCULATED |
| 11 | Camera view vs tube length | Hover needed to see the grasp zone: 171 mm uncut, 140 mm after the 50 mm cut | CALCULATED, ray-cast SIMULATED |
| 12 | Press fits and printed holes | Pocket 0.075 mm over the bearing, line-to-line lip; lip stays under the allowable stress up to 0.16 mm of printer undersize | CALCULATED, coupon PLANNED |

## Where this sheet differs from earlier project statements

| Earlier statement | This sheet | Why |
|---|---|---|
| Load case: up to 40 N per cable "(motor limit)" | Running pull at the cap is 23.8 N at the core, 17.9 N full spool; hold torque over core radius is 34 N | 40 N is not reachable at 1.06 A; the shopping list already says it was never a measured limit |
| Decision D29: "claw mass budget rises to ~750 g with a 1 lb payload" (1.35 A, 0.4 m ceiling) | 183 g (full spool, 1.5 margin), 502 g (no margin), 820 g (core radius, no margin) | Not reproducible with running torque at a wound spool; 750 g appears only if the hold torque at the empty-spool radius (43 N) is used as the line force with the 1.5 margin (759 g). D30 withdrew 1.35 A, so do not quote 750 g |
| Decision D30: "cable tension returns to ~34 N" | 34 N is hold torque over the empty-spool radius (a snag worst case); the running pull is 23.8 N, the design value 11.9 N | Numbers agree; the three meanings of "tension" must not be mixed on a slide |
| Design review: "grip force margin ~2.8× for 1 lb" | 1.5× at the weakest jaw position with the +2 m/s² term (13.3 N against 8.9 N) | The 2.8× came from the earlier gearbox estimate (20.8 N); the as-built four-bar gives 13.3 N at the weakest point |
| Pendulum length 0.196 m (period 0.89 s, dwell 5.6 s) | A lumped estimate for the current head and the 50 mm tube cut is 0.09–0.14 m | 0.196 m belongs to the superseded 1044 g head on the 304.8 mm tube; re-extract the centre of mass before quoting |
| Hand calculation of the tube: 0.18 mm tip deflection, 8.5 MPa | 0.04 mm and 1.8 MPa for the 3 mm wall in the CAD | The hand calculation used 0.48 mm, which is the heat-fin sheet thickness, not the tube wall; the real wall is unmeasured |
| Outline: fit-coupon photo with measured insertion results | None exists in the record | Say PLANNED |
| Vref cap "~0.79 V" (10/21 entry) vs "~0.85 V" (D30) | 0.99 A vs 1.06 A | Two measurements of one cap; the 7 % spread applies to every tension below |

One input risk runs through sections 1, 2, 5 and 7: every capacity number uses the 0.45 kg claw budget. The project record estimates the printed claw at 1.05–1.25 kg and has not yet weighed it.

---

## 1. Cable statics: tension grows as the cable flattens

**Evidence:** CALCULATED. No tension has been measured on the rig.

**Equation.** Four cables, claw centred, weight shared equally: each cable carries W/4 vertically, so

T = W / (4 sin φ), with sin φ = d / √(d² + D_h²)

where d is the depth below the anchors and D_h the horizontal distance from the claw to each anchor. For a shallow cable T ≈ W·D_h / (4d). A vertical acceleration a multiplies the weight by (1 + a/g).

**Supplied facts.** Room 11 × 9 × 9 ft (3.353 × 2.743 × 2.743 m); design acceleration 2 m/s²; first test load 1 lb (0.4536 kg); planner ceiling margin 0.4 m; highest task height 1.6 m (0.99 m below the anchors). Winch line force from section 2.

**Assumptions.** Anchors 0.15 m below the ceiling; claw mass 0.45 kg (a budget, not a weighed value); straight, massless cables; equal share. The real split is statically indeterminate (four cables, three force equations), so the room-wide limits below use the best possible split, found by a linear program that minimises the largest tension.

**Substitution.** D_h = √(1.676² + 1.372²) = 2.166 m. W = (0.4536 + 0.45) × 9.81 = 8.86 N; with +2 m/s², 10.67 N.

| Depth d (m) | Elevation φ | T static (N) | T with +2 m/s² (N) |
|---|---|---|---|
| 0.15 | 4.0° | 32.1 | 38.6 |
| 0.30 | 7.9° | 16.2 | 19.4 |
| 0.60 | 15.5° | 8.3 | 10.0 |
| 1.20 | 29.0° | 4.6 | 5.5 |

The earlier review quotes 32.1 / 16.1 / 8.3 / 4.6 N: the same numbers to within rounding.

**Why a ceiling margin exists.** Tension scales as 1/sin φ, so it doubles each time the depth halves, while the winch has a fixed ceiling: 17.9 N running at a full spool, 11.9 N after the 1.5 skip margin (section 2). For the centred claw the shallowest depth the winches can hold is 0.27 m (static, no margin), 0.33 m (with +2 m/s²) and 0.50 m (with the 1.5 margin). Near a wall the near cables are steep and short while the far two are almost horizontal, so the best split is worse. The worst case over the whole room (0.2 m wall margin) at 1.06 A with the 1.5 margin is:

| Ceiling limit below the anchors | Largest tension per unit weight | Total weight the four winches can hold |
|---|---|---|
| 0.4 m (planner margin) | 2.42 | 1.10 lb (0.50 kg) |
| 0.6 m | 1.67 | 1.60 lb (0.73 kg) |
| 1.0 m | 1.10 | 2.44 lb (1.11 kg) |
| 0.99 m (highest task pose) | 1.10 | 2.43 lb (1.10 kg) |

The claw (0.45 kg) plus 0.9 kg of jeans is 1.35 kg, which is 1.22 × what the Ø15 spool can hold at the highest task pose. Section 2 shows how the spool core closes that gap.

**Decision it explains.** Keep the claw at least 0.4 m below the anchors (software ceiling), never home by winching the claw up to the pulleys, and treat the motor, not the line, as the limit on lifted weight.

**Limit of the model.** Point claw and ideal cables: the 84 mm attachment spread, line sag, pulley friction and swing are ignored, and the equal-share table is a lower bound for any pose off the centre.

---

## 2. Motor torque to line tension, the current cap, and the spool core

**Evidence:** CALCULATED. Inputs: Vref MEASURED on the board; spool dimensions taken from the part's CAD model (the printed spool has not been measured); running-torque fraction ASSUMED (pull test PLANNED).

**Equations.**

- A4988 current limit: I = Vref / (8·R_s), with R_s = 0.100 Ω on the R100 boards.
- Stepper torque is taken proportional to current: τ_hold = τ_rated · I / I_rated; running torque τ_run = 0.7 τ_hold.
- Line force F = τ / r, with r the radius of line on the spool.

**Supplied facts.** Vref tops out at 0.85 V on the red R100 carrier (decision D30; an earlier entry says 0.79 V). Motor rated holding torque 0.36 N·m at 1.5 A. Spool core Ø15, drum 16 mm wide, flanges Ø36; 20 ft (6.096 m) of line. 200 full steps × 16 microsteps per revolution; the simulation profile caps the step rate at 4000 Hz; maximum cable speed 50 mm/s. Bore Ø5.45 with a 0.5 mm D-flat on the Ø5 shaft; Ø1.4 tie-off hole 6 mm off axis.

**Assumptions.** Running torque is 0.7 of holding torque (an earlier table used 0.5); a skip margin of 1.5 on line force; 0.5 mm effective line diameter; 85 % winding packing; the rule of thumb that braided high-modulus line wants a bend ratio (core diameter ÷ line diameter) of at least 20, with 8–10 as an absolute floor; an M3 thread-forming screw wants about 3 mm of engagement.

**Substitution.**

- I = 0.85 / (8 × 0.100) = 1.0625 A (0.79 V would give 0.9875 A).
- τ_hold = 0.36 × 1.0625 / 1.5 = 0.255 N·m; τ_run = 0.1785 N·m.
- Winding the 20 ft on the Ø15 core gives 5 layers and a full radius of 10.0 mm.

| Quantity | Value |
|---|---|
| Running pull at the 7.5 mm core | 23.8 N |
| Running pull at a full spool (10 mm) | 17.9 N |
| Design force (÷ 1.5): core / full spool | 15.9 N / 11.9 N |
| Snag worst case: hold torque ÷ core radius | 34 N |
| Older table (0.5 of 0.36 N·m, no current scaling) | 24.0 N core, 18.0 N full |

"Tension" therefore means three different things in the project: the running pull, the derated design value, and the snag load. The older 24 → 18 N table agrees with the new one only because 0.7 × (1.06 / 1.5) happens to be close to 0.5.

### Spool-core study (20 ft of 0.5 mm line, 16 mm drum, 85 % packing)

| Core Ø (mm) | Layers | Full radius (mm) | Running pull core / full (N) | Design force, full spool (N) | Gain vs Ø15 | Weight held at the highest task pose (kg) | Largest claw that still lifts 0.9 kg jeans (g) |
|---|---|---|---|---|---|---|---|
| 15 | 5 | 10.0 | 23.8 / 17.9 | 11.9 | – | 1.10 | 202 |
| 12 | 5 | 8.5 | 29.8 / 21.0 | 14.0 | +18 % | 1.30 | 397 |
| 10 | 6 | 8.0 | 35.7 / 22.3 | 14.9 | +25 % | 1.38 | 478 |
| 8 | 7 | 7.5 | 44.6 / 23.8 | 15.9 | +33 % | 1.47 | 570 |

| Core Ø (mm) | Bend ratio | Line per rev, core → full (mm) | Step rate for 50 mm/s on the core layer (Hz) | Line speed at the 4000 Hz cap, core (mm/s) | Wall around the Ø5.45 bore, round side / flat side (mm) | Axial Ø1.4 tie-off hole fits | M3 set-screw engagement ≥ 3 mm |
|---|---|---|---|---|---|---|---|
| 15 | 30:1 | 47.1 → 62.8 | 3395 | 58.9 | 4.775 / 5.275 | yes | yes |
| 12 | 24:1 | 37.7 → 53.4 | 4244 | 47.1 | 3.275 / 3.775 | yes | yes |
| 10 | 20:1 | 31.4 → 50.3 | 5093 | 39.3 | 2.275 / 2.775 | no | no |
| 8 | 16:1 | 25.1 → 47.1 | 6366 | 31.4 | 1.275 / 1.775 | no | no |

The wall column is the material left around the Ø5.45 D-bore: radius minus 2.725 mm on the round side, radius minus 2.225 mm on the flat side (where the Ø2.8 set-screw hole runs). The axial tie-off hole needs the annulus between bore and core surface to be at least the hole diameter plus two 0.8 mm walls (3.0 mm), the wall the drawn Ø15 part has today. Replacing the layer pitch by the hexagonal value 0.866 d changes the full radius by at most 0.5 mm, so the winding convention does not drive the conclusions.

**Recommended core: Ø10 mm.** It is the largest core that both keeps the 20:1 bend ratio and lets the winches hold the 0.45 kg claw plus 0.9 kg jeans with the 1.5 margin at the highest task pose (1.38 kg held against 1.35 kg needed). Ø15 can carry a claw of only 202 g with that payload and Ø12 397 g. Going to Ø8 buys only 8 more points of force and breaks the bend ratio. Caveats before committing:

1. The margin is thin (1.38 kg against 1.35 kg) and rests on the 0.45 kg claw budget; no core in the study carries a 1.05–1.25 kg printed claw plus jeans.
2. Line wound on a Ø10 core bends at 20:1 and builds six layers (five on Ø15): bend fatigue of the braid is a rule of thumb here; a bend-cycle test is needed. Line paid out per revolution then grows from 31.4 to 50.3 mm (+60 %), so the controller must keep modelling radius against wound length.
3. A Ø10 core leaves a 2.3 mm hub annulus: the set screw needs a separate boss (flat-side wall 2.8 mm is under 3 mm) and the line tie-off has to move to the flange.
4. 50 mm/s on the core layer needs 5093 Hz at 16 microsteps, above the 4000 Hz cap in the simulation profile (the hardware example profile has no cap and full steps). Raise the cap after confirming the step generator and the motor's torque at about 1.6 rev/s, or limit speed to 39 mm/s near the core.
5. The thin walls of Ø8 (1.275 mm round side) are barely above a three-perimeter wall; that option also fails on bend ratio and tie-off.

**Decision it explains.** The driver board caps the winch current at about 1.06 A, so extra lift has to come from the spool radius, the claw mass or the ceiling margin; the Ø10 core is the cheapest of these.

**Limit of the model.** Torque is linear in current with a flat 0.7 running fraction and no speed roll-off; packing ignores cross-overs; line bend life is a rule of thumb.

---

## 3. Joule heating and the aluminium fin

**Evidence:** CALCULATED. Fin dimensions MEASURED (as built); all temperatures are model outputs and the 90-minute hold test is PLANNED.

**Equations.**

- Joule heat in the coils: P = I²R.
- Fin parameter for a thin plate with both faces exposed: m = √(2h / (k t)); fin efficiency η = tanh(mL) / (mL); fin resistance R_fin = 1 / (η h A_fin), A_fin = 2 w L.
- A two-node network: motor case → shell interior → room, with the fin as a second path from the motor case straight to the room. Heat balance: P_m = (T_m − T_room)/R_fin,total + (T_m − T_shell)/R_ma, and the shell interior also receives the electronics heat.

**Supplied facts.** Fin sheet as built 0.019 in (0.483 mm); designed plate 1/8 in (3.175 mm); fin 44 mm wide with about 200 mm exposed in room air; current 1.0625 A from section 2; shell network values (motor→interior 12 K/W, interior→room 0 / 1 / 3.5 K/W for open / vented / sealed) and 1.5 W of electronics from the earlier thermal model.

**Assumptions.** Coil resistance 1.8 Ω per phase (to be measured with a meter); room 23 °C near the ceiling; aluminium conductivity 160 W/m·K (138–167 over common alloys); film coefficient h = 5–9 W/m²·K (7 as the central value, still air plus radiation from a black fin); 1 K/W contact resistance at the motor flange; PETG conductivity 0.2 W/m·K.

**Substitution at 1.0625 A.** P = 1.0625² × 1.8 = 2.03 W. Fin area, both faces: 2 × 0.044 × 0.200 = 0.0176 m².

| Fin | m (1/m) | mL | Efficiency η (h = 9 / 7 / 5) | R_fin (K/W) (h = 9 / 7 / 5) |
|---|---|---|---|---|
| As built, 0.019 in | 13.5 | 2.69 | 33 / 37 / 43 % | 19.4 / 22.1 / 26.4 |
| Designed, 1/8 in | 5.25 | 1.05 | 70 / 74 / 80 % | 9.0 / 10.9 / 14.2 |

Motor case temperature and the share of the heat the fin carries (h = 7, 23 °C room):

| Enclosure | No fin | As-built fin (share) | 1/8 in fin (share) |
|---|---|---|---|
| Open air | 47 °C | 39 °C (34 %) | 35 °C (50 %) |
| Vented shell | 51 °C | 41 °C (38 %) | 36 °C (55 %) |
| Sealed shell | 64 °C | 46 °C (50 %) | 40 °C (68 %) |

Across the h and conductivity ranges the sealed, as-built case spans 45–49 °C and the fin share 43–54 %. The fin buys 18 K in the sealed case. Its efficiency is about half that of the designed plate, but the exposed area is the same, so the as-built fin still carries about half of the heat in the sealed shell. A 90-minute hold covers 92 % of the final rise (the sealed shell time constant is 35 min), which is why the planned test is 90 minutes.

**Why a printed mount cannot sink motor heat.**

| | Aluminium | PETG |
|---|---|---|
| Conductivity | 160 W/m·K | 0.2 W/m·K |
| Conduction resistance through the flange contact (42.3 mm square, 3.175 mm Al / 5 mm PETG) | 0.011 K/W | 14.0 K/W (1260 × more) |
| Distance heat spreads along the plate, 1/m, 0.48 mm sheet | 74 mm | 2.6 mm |
| Long-fin resistance 1/√(h P k A_c), 44 mm wide | 0.48 mm Al: 22 K/W | 5 mm PETG: 182 K/W |

At the same geometry the conductance ratio is √(160 / 0.2) = 28 ×. Heat in PETG dies out within a few millimetres of the motor, so the PETG around the motor bolts climbs to nearly the motor's temperature while it carries the cable load.

**Decision it explains.** An aluminium fin through the shell into room air (and vented shell openings) instead of relying on the printed mount; the thin sheet is accepted because, in this model, it still keeps the sealed case well below the 60 °C target for loaded printed parts.

**Limit of the model.** Lumped, steady-state numbers with assumed coil resistance, film coefficient and shell resistances; the hold test with thermometers replaces it.

---

## 4. Gear tooth bending (Lewis) and the gear ratio

**Evidence:** CALCULATED. Jaw force from the four-bar is SIMULATED (computed from the model, no force gauge). No printed gear has been stalled.

**Equations.** Tooth bending (Lewis): σ = F_t / (b · m · Y), with F_t = 2τ / (m z) the tangential force at the pinion, b the face width, m the module, Y the form factor; safety factor SF = σ_allow / σ. Torque through the train: τ_jaw = N · τ_in · η² / 2 (two jaws share the output; η per mesh).

**Supplied facts.** MG996R stall torque 9.4 kg·cm at 4.8 V (0.922 N·m) and 11.0 kg·cm at 6.0 V (1.079 N·m); tooth counts 18 / 36 / 24 / 24 (ratio N = 2), module 1.5 mm, face widths 16 mm (15.7 mm effective after the 0.3 mm relief) and 20 mm; form factors Y = 0.309 (18T), 0.3775 (36T), 0.337 (24T) from the standard 20° full-depth table.

**Assumptions.** η = 0.95 per printed mesh; PETG allowable stress 22.5 MPa (half of a 45 MPa tensile strength, to cover layer adhesion and fatigue); the first screening assumed module 1 with a 6 mm face.

**Substitution (pinion, 6.0 V stall).** Module 1: F_t = 2 × 1.079 / 0.018 = 119.9 N, σ = 119.9 / (6 × 1 × 0.309) = 64.7 MPa, SF = 22.5 / 64.7 = 0.35.

| Case (pinion, then big gear and sync gear where relevant) | F_t at 4.8 / 6.0 V (N) | Root stress at 4.8 / 6.0 V (MPa) | SF at 4.8 V | SF at 6.0 V |
|---|---|---|---|---|
| Module 1, 6 mm face (first screening) | 102 / 120 | 55 / 65 | 0.41 | 0.35 |
| Module 1.5, 8 mm face | – | – | 1.22 | 1.04 |
| Module 2, 10 mm face | – | – | 2.71 | 2.32 |
| As built, pinion (module 1.5, 15.7 mm) | 68 / 80 | 9.4 / 11.0 | 2.40 | 2.05 |
| As built, 36-tooth gear | same F_t | – | 2.93 | 2.50 |
| As built, 24-tooth sync gear, one jaw takes all | – | – | 2.34 | 2.00 |

The 24-tooth sync gear at 6 V is 1.997, just under 2.0 and accepted as inside the precision of the assumed stall torque.

**Why stall is the design case.** A clamp closing on cloth does not stop at a position; it stops when the servo stalls. Every grip therefore loads the gears with the full stall torque, repeatedly, for as long as the load is held. A strength check at "typical" torque would miss the load the gears actually see.

**Effect of the gear ratio on jaw force.** The pinion force F_t depends only on servo torque and pinion radius, not on N. Raising N multiplies everything downstream:

| Ratio N | Jaw torque at 4.8 V | Jaw stroke from a 153° servo | Sync-gear SF (one jaw, 4.8 V) |
|---|---|---|---|
| 2 (as built) | 0.83 N·m | 76.5° | 2.34 |
| 3 (earlier gearbox) | 1.25 N·m | 51° | 1.56 (1.33 at 6 V) |

Jaw force at the tips is jaw torque divided by an effective lever arm that shrinks as the jaws close on a wider object: 59 mm at a 10 mm gap, 48 mm at 40 mm, 33 mm at 70 mm. That is why the as-built jaws give 13.3 N at the weakest position and 25 N near a 70 mm grab at 4.8 V.

**Decision it explains.** Module 1.5 with 16 mm and 20 mm faces and a 2:1 first stage: strong enough at stall, with a jaw stroke of 76.5°, instead of the module 1 train that fails and the 3:1 train that loads the sync gear to a margin of 1.3.

**Limit of the model.** Static Lewis bending only, with textbook form factors, no dynamic or stress-concentration factor, and a 50 % rule of thumb for printed PETG.

---

## 5. Grip by friction

**Evidence:** CALCULATED requirement against SIMULATED jaw force (computed from the four-bar model, not a force gauge). A hardware pull test is PLANNED.

**Equation.** Each of the two jaws presses with normal force N and friction μN, so 2μN ≥ m(g + a), giving N ≥ m(g + a) / (2μ) per jaw.

**Supplied facts.** 1 lb test load; 0.9 kg jeans as the provisional screening reference; a = 2 m/s²; as-built jaw force at 4.8 V from the model: 13.34 N at the weakest position (gap 0.6 mm) rising to 25.0 N at a 70 mm gap; at 6.0 V the figures are 17 % higher.

**Assumptions.** μ = 0.3 (cloth on a printed pad) and 0.6 (TPU pads); Coulomb friction between flat pads and the load. "Grab width" below is the jaw tip gap when the pads meet the cloth.

| Load | μ | Required N per jaw, static | Required N per jaw, with +2 m/s² | Margin at the weakest jaw position | Narrowest grab where 4.8 V force suffices |
|---|---|---|---|---|---|
| 1 lb | 0.3 | 7.4 N | 8.9 N | 1.49 × | any |
| 1 lb | 0.6 | 3.7 N | 4.5 N | 2.99 × | any |
| 0.9 kg jeans | 0.3 | 14.7 N | 17.7 N | 0.75 × (short) | 43 mm (22 mm at 6 V) |
| 0.9 kg jeans | 0.6 | 7.4 N | 8.9 N | 1.51 × | any |

The earlier 7.4 N per jaw for 1 lb is the static value; adding the dynamic term gives 8.9 N.

**Decision it explains.** The 1 lb target is covered everywhere in the stroke; the jeans target at μ = 0.3 depends on the gripping width and the pad friction, which is why TPU pads are on the claw and why the friction coefficient is the first thing to measure with a pull test.

**Limit of the model.** Two flat pads on a rigid object; cloth bunches and interlocks (often better than μ alone) but the pad-to-cloth μ has never been measured.

---

## 6. Beam bending and creep: why an aluminium tube

**Evidence:** CALCULATED. The as-built tube wall is UNMEASURED (the 0.019 in figure in the record is the fin sheet, not the tube). The creep numbers are ILLUSTRATIVE: no creep test has been run.

**Equations.** Second moment of area I = π(D⁴ − d⁴)/64. Cantilever with an end load F: tip deflection δ = F L³ / (3 E I); bending stress σ = M c / I with M = F L, c = D/2. Bearing stress at a cross-bolt through two tube walls: σ_b = F / (2 d t).

**Supplied facts.** Tube OD 28.54 mm, wall 3 mm in the CAD (ID 22.54 mm); length 254.8 mm after the 50 mm cut; M3 cross-bolt (Ø3 shank in a Ø3.4 hole); head mass 0.48 kg.

**Assumptions.** E = 69 GPa for the aluminium (alloy unknown, 6061 assumed) and 2.1 GPa for printed PETG in the plane of the layers; side load 10 N at the tube tip; cross-bolt design load 100 N; bearing allowable 360 MPa (1.5 × 240 MPa yield).

**Substitution.** I(3 mm wall) = 19897 mm⁴. Aluminium: δ = 10 × 0.2548³ / (3 × 69×10⁹ × 19897×10⁻¹² ) = 0.040 mm; σ = 10 × 0.2548 × 0.01427 / I = 1.83 MPa.

| Tube | Tip deflection (10 N at 254.8 mm) | Bending stress | Mass |
|---|---|---|---|
| Aluminium, 3 mm wall (CAD) | 0.040 mm | 1.83 MPa | 166 g |
| Aluminium, 1 mm wall | 0.097 mm | 4.43 MPa | 60 g |
| Aluminium, 0.48 mm wall (retired figure) | 0.192 mm | 8.73 MPa | 29 g |
| PETG, same size as the CAD tube | 1.32 mm | 1.83 MPa (identical: stress depends on geometry only) | – |

Stiffness ratio E_Al / E_PETG = 32.9. A 1 mm aluminium wall keeps 41 % of the 3 mm wall's stiffness at 36 % of its mass and is still 14 × stiffer than a 3 mm PETG tube. With the 156.2 mm of free tube between hub and head the 3 mm aluminium tube deflects 0.009 mm and reaches 1.12 MPa.

**Creep versus stress relaxation.** Creep is strain growing with time at constant stress, ε(t) = σ₀ J(t): a long arm under steady load sags a little more every day, and the camera-to-jaw geometry drifts. Stress relaxation is stress decaying with time at constant strain, σ(t) = ε₀ E_r(t): a press fit or clamp that was tight when assembled loses grip. The long arm is a creep problem; the printed collars and press fits that grip the tube are a relaxation problem, so the tube joints need a positive lock (a cross-bolt) rather than friction alone. With an illustrative modulus decay E(t) = E₁ t^−0.07 (an assumed exponent, not data), a PETG tube keeps 72 % of its stiffness after 100 h and 62 % after 1000 h, so the 10 N tip deflection grows from 1.32 mm to 2.14 mm. The aluminium tube works at 0.8 % of its yield strength and shows no measurable creep at room temperature. PETG works at only 4 % of its tensile strength, but a polymer about 57 K below its softening point creeps at any stress.

**Bearing at the cross-bolt.** σ_b = 100 / (2 × 3 × 3) = 5.6 MPa on the 3 mm wall (safety factor 65 against 360 MPa; capacity 6480 N). The actual axial load is (head + 0.9 kg)(g + 2) = 16.3 N, so the 100 N design load is 6.1 × the real one. A thin wall would raise the bearing stress to 16.7 MPa (1 mm) or 34.7 MPa (0.48 mm): still fine, but thin tubes dent, so the printed saddle must carry the clamp and the bolt must not be over-tightened.

**Decision it explains.** An aluminium tube for the long arm so the camera stays registered to the jaws; the wall thickness can drop if mass matters, once measured.

**Limit of the model.** Linear-elastic cantilever with an assumed 10 N load; thin-wall dents, local buckling and the alloy are not modelled; the creep exponent is illustrative.

---

## 7. Pendulum dynamics and tilt

**Evidence:** CALCULATED. The static-equilibrium tilt was reproduced independently from the cable model (SIMULATED in the project). Damping is UNMEASURED.

**Equations.** Simple pendulum T = 2π√(L/g); rigid body (compound pendulum) T = 2π√((k² + L²)/(gL)), k the radius of gyration about the centre of mass. The claw hangs on four lines attached to a square of ±42.07 mm above its centre of mass. In static equilibrium the cable forces and gravity must balance in force and in moment about the centre of mass: Σ (r_i − r_c) × T_i u_i = 0. To first order the horizontal force components cancel and what remains is the moment M_v of the vertical components about the centre of mass, which the pendulum stiffness W·L turns into a tilt: θ ≈ M_v / (W L).

**Supplied facts.** Recorded centre-of-mass depth L = 0.196 m below the attachment plane (CAD of the old claw: 2065 g, 1044 g head, 304.8 mm tube); jaw tips 0.517 m below the plane; attachment square ±42.07 mm; anchors from the simulation profile (not surveyed); head mass 481 g (CAD).

**Assumptions.** Radius of gyration k = 0.13 m; settle rule of 5 periods × 1.25; unknown damping; for the lumped estimate, centroid depths for the box (31 mm above the plane), the hub, the tube and the head (321 mm below), all from CAD-solid masses with no electronics.

| Case | L (m) | T simple (s) | T compound (s) | Settle dwell 5 × 1.25 × T (s) |
|---|---|---|---|---|
| Recorded (stale) | 0.196 | 0.89 | 1.07 | 5.6 |
| Lumped estimate, current head and 50 mm cut | 0.116 (0.09–0.14) | 0.68 | – | – |
| Loaded release (0.6 kg claw + 0.9 kg at the tips) | 0.389 | 1.25 | – | 7.8 |

The compound-pendulum period is 20 % longer than the simple one, which is why the gate multiplies by 1.25.

**Note on the stale depth.** The 0.196 m comes from the superseded v6 head; the estimate for the current head with the 50 mm tube cut is 0.116 m (range 0.09–0.14 m). Re-extract it from the CAD, then re-run this section. A shorter L shortens the period but raises the tilt (below).

**Settle-before-grip.** Waiting n periods shrinks the amplitude by e^(−2πζn). With the assumed damping ratios 0.01 / 0.02 / 0.05, 73 % / 53 % / 21 % of the swing is left after 5 periods; 90 % reduction needs ζ ≥ 0.073. The dwell alone cannot be relied on; the camera "still" test and the small motion limit (0.1 m/s²) are what keep the swing small, and the real damping must be measured by a free-decay test.

**Where tilt comes from.** Solving the force and moment balance for a claw on four straight lines (minimum-norm tension set, no pretension) at the grip height on the 9 × 7 grid used in the project's review agrees with the repository's own attitude predictor to numerical precision (largest difference 3e-14 degrees) at the five poses checked. Results:

| Centre-of-mass depth | Tilt at the room centre | Median tilt | Largest tilt (corners) | Grid points above 5° |
|---|---|---|---|---|
| 0.196 m (recorded) | 0.0° | 8.7° | 12.9° | 83 % |
| 0.116 m (lumped estimate) | – | 13.8° | 20.7° | 92 % |

The corner tilt grows by 1.61 × when L drops from 0.196 to 0.116 m, against 1.70 × from the 1/L law: tilt is the vertical-force moment divided by W·L.

**Decision it explains.** Grips wait for a settle dwell and a tilt check; the tilt prediction must not gate grips across the whole room until the centre-of-mass depth is re-measured, because 83 % of grid points already exceed 5° with the recorded value.

**Limit of the model.** Small-angle rigid pendulum with no damping; the centre-of-mass depth is a CAD-solid estimate (and the lumped bracket is rough); the tilt model assumes straight lines and no pretension.

---

## 8. Measurement uncertainty

**Evidence:** CALCULATED (Cramer-Rao bound for the tag corners). The matching Monte Carlo runs in the project are SIMULATED. Real corner noise on the camera is UNMEASURED.

**Equations.**

- Lever-arm error: δx = σ_θ · L (a small rotation error of the marker pose moves a point at distance L by σ_θ L).
- Averaging N independent frames: σ_N = σ / √N.
- One square tag of edge a at range z, corner noise σ_px, focal length f (pixels): σ_θ ≈ 2σ_px z² / (f a²). For several tags, the bound comes from the 6-degree-of-freedom Jacobian: C = σ_px² (JᵀJ)⁻¹.
- Weighted least squares: θ̂ minimises Σ r²/σ²; the covariance is (JᵀWJ)⁻¹; the reduced χ² is rᵀWr / (m − n).

**Supplied facts.** Focal length 520 px (camera guess); tag edge 152.4 mm (single) and 150 mm (board); board pitch 0.25 m; lens 0.51 m above the floor with the claw at rest.

**Assumptions.** Corner noise 0.3 px, independent between frames; lever arm equal to the range (0.51 m); in the least-squares toy, 6 mm vision noise per axis.

| Quantity | Result |
|---|---|
| One tag, tilt noise at 0.51 m (closed form / numerical bound) | 12.9 / 12.9 mrad |
| Lever-arm error, one frame, one tag | 6.6 mm |
| Tilt noise vs range, 0.46 / 0.6 / 0.8 / 1.0 m | 10.5 / 17.9 / 31.8 / 49.7 mrad |
| Board, four tags in view, camera centred over them (pitch 0.25 m) | 1.3 mrad → 0.68 mm |
| Mean of 1 / 4 / 10 / 30 frames (one tag) | 12.9 / 6.5 / 4.1 / 2.4 mrad |

The single-tag figures reproduce the project's Monte Carlo (10.5 / 17.9 / 31.8 / 49.6 mrad). A constant 10 mrad is right only near 0.46 m on axis. Averaging helps only for independent noise: a static bias of 1 mrad still leaves 0.5 mm. The board's gain comes from many corners spread over a wide area, but only when at least two tags are in view at the rest height (the 0.25 m pitch is chosen for that). The four-tag figure is the best placement; the project's simulator reports 1.0–3.0 mrad for 3–5 tags in realistic positions.

**Why "the optimiser converged" is not acceptance.** In a one-cable toy (unknown anchor position and length offset, 30 vision poses, exact motor length, 300 random trials):

| Excitation box | Whitened residual RMS | Predicted σ along the weak direction | Actual error along it | Error at a held-out far pose |
|---|---|---|---|---|
| 0.6 m | 1.00 | 351 mm | 392 mm | 14 mm |
| 1.8 m | 0.99 | 39 mm | 39 mm | 2 mm |

Both fits "converge" with a residual near 1, so the residual says only that the data agree with the model. The information matrix says that in the small box the anchor range and the length offset trade off almost perfectly (9 × larger uncertainty), and even a held-out far pose sees only a small part of that error. This is why acceptance requires identifiability, residual adequacy, no alternate optimum, witness agreement and a predicted σ over the work volume, not a converged solver.

**Decision it explains.** A multi-tag floor board with at least two tags in view replaces the single 6-inch tag; calibration is accepted only on the five conditions, otherwise the robot stays inside the validated region.

**Limit of the model.** Independent Gaussian noise, fronto-parallel tags; the toy is one cable in two dimensions, not the four-cable estimator.

---

## 9. Synchronisation error becomes force

**Evidence:** CALCULATED. The four-node synchronisation test is PLANNED.

**Equations.** Length mismatch Δℓ = v · Δt; force F = k · Δℓ with line stiffness k = E A / L.

**Supplied facts.** Maximum cable speed 50 mm/s; line diameter 0.5 mm (A = 0.196 mm²).

**Assumptions.** Wi-Fi skew Δt = 50 ms; line stiffness k = 3 N/mm over a 3 m run (this implies an effective braid modulus of 46 GPa, plausible for a braid made of 100 GPa fibre).

**Substitution.** Δℓ = 50 mm/s × 0.05 s = 2.5 mm; F = 3 N/mm × 2.5 mm = 7.5 N (the earlier review rounds this to 8 N). That is 90 % of the static tension at 0.6 m depth (8.3 N). The pass criterion of 2 mm error gives 6 N, and a skew of 40 ms at full speed produces that 2 mm. Stiffness scales as 1/L: the same line over 1.5 m is twice as stiff (k = 5.9 N/mm at E = 45 GPa), over 4.5 m 2.0 N/mm.

**Decision it explains.** Time-stamped trajectories on a shared clock (or a coordinator node) so that skew becomes clock error instead of network jitter.

**Limit of the model.** Linear spring with an assumed modulus; one lagging cable would really redistribute its error over the other three.

---

## 10. Wire voltage drop

**Evidence:** CALCULATED. The wiring is not electrically qualified (PLANNED).

**Equation.** R = ρ · 2L / A (out and back); V_drop = I R; P_loss = I² R.

**Supplied facts.** Longest branch 32 ft (9.75 m) one way, from the room layout; supply 12 V on the label. AWG areas from the standard formula: 18 AWG 0.823 mm², 16 AWG 1.309 mm².

**Assumptions.** Copper at 20 °C, ρ = 1.724×10⁻⁸ Ω·m; 50 °C for a warm ceiling run (+0.0039 per K); stranding lay and connector resistance ignored.

| Wire | Loop resistance | Drop at 1 A (% of 12 V) | Drop at 2 A (% of 12 V) | Drop at 2 A, 50 °C | Wire loss at 2 A |
|---|---|---|---|---|---|
| 18 AWG | 0.409 Ω | 0.41 V (3.4 %) | 0.82 V (6.8 %) | 0.91 V | 1.63 W |
| 16 AWG | 0.257 Ω | 0.26 V (2.1 %) | 0.51 V (4.3 %) | 0.57 V | 1.03 W |

16 AWG drops 1.59 × less than 18 AWG (area ratio). Check: 18 AWG resistance per 1000 ft computes to 6.39 Ω, matching the standard table.

**Decision it explains.** 16 AWG on the long branch: lower drop and less heat at the same current; the 18 AWG candidate was chosen for a 14 ft run.

**Limit of the model.** DC resistance only; the supply label, meter reading and driver minimum voltage still need an electrical qualification.

---

## 11. Camera field of view versus tube length

**Evidence:** CALCULATED closed form (similar triangles). The ray-cast over the CAD model that it summarises is SIMULATED.

**Equation.** A ray from the lens (height H above the floor, 90 mm to the side of the tube) to the far edge of the grasp zone (97 mm from the lens) passes the camera-side face of the lower plate (59.5 mm from the lens) at a height k·H, where k = 1 − 59.5/97. The ray clears the plate's bottom edge (93 mm above the closed jaw tips, plus the hover D) when k (H₀ − c + D) ≤ 93 + D, so the minimum hover is

D\* = (k (H₀ − c) − 93) / (1 − k)

where c is the tube cut and H₀ the lens height with the jaw tips on the floor.

**Supplied facts.** Lens offset 90 mm; plate face 30.5 mm from the tube axis; grasp zone far edge 7 mm; lens height 512.06 mm at c = 0.

**Substitution.** k = 0.3866, 1 − k = 0.6134.

| Cut c (mm) | D\* closed form (mm) | With the rounded constants 0.387 / 0.613 (mm) | Ray-cast scan from the project's study (mm) | Mass saved (g) |
|---|---|---|---|---|
| 0 | 171.1 | 171.5 | 172 | 0 |
| 50 | 139.6 | 140.0 | 140 | 32.5 |
| 100 | 108.1 | 108.4 | 109 | 65 |
| 150 | 76.6 | 76.8 | 77 | 97 |
| 200 | 45.1 | 45.3 | 46 | 130 |

The closed form sits 0.4–0.9 mm below the one-millimetre ray-cast scan, which reports the first whole millimetre. Each millimetre of cut lowers D\* by k/(1−k) = 0.630 mm, about 6.3 mm per 10 mm cut. The field of view is never the limit for the grasp zone; the lower plate's edge is.

**Decision it explains.** D28: cut the tube by 50 mm: the grasp zone is fully visible from a hover of about 140 mm instead of 172 mm, 32.5 g is saved (0.65 g per mm), and the tube can still be cut up to 206 mm before the hub meets the head plates.

**Limit of the model.** Straight rays from a point lens over a flat, bare floor with the claw hanging still; a pile of laundry raises the floor and the required hover by its height; focus, lighting and swing are not modelled.

---

## 12. Press fits and printed holes

**Evidence:** CALCULATED. A fit coupon is PLANNED; none has been printed or measured.

**Equations.** Diametral interference u = D_part − D_hole. For a rigid bearing pressed into a ring of inner radius b and outer radius c: contact pressure p = (u/2) E / (b [(c² + b²)/(c² − b²) + ν]); hoop stress at the bore σ_θ = p (c² + b²)/(c² − b²); insertion force F ≈ μ p π D l.

**Supplied facts.** 687 bearing, outer diameter 14.000 mm (7 × 14 × 5). Pocket Ø14.075 mm with a Ø14.000 mm entry lip 1.95 mm long, ring of printed material out to radius 8.5 mm. Spool bore Ø5.2 mm (v2, printed too tight on the Ø5.0 shaft) opened to Ø5.45 mm (v3). Gear parts exported to mesh files with a 0.02 mm chord tolerance and 0.1 rad angular tolerance (plates: 0.05 mm, 0.2 rad).

**Assumptions.** E = 2100 MPa, ν = 0.38 for printed PETG; μ = 0.3; bearing outer diameter tolerance 0 / −0.008 mm; the printer undersizes holes by an unknown amount u (swept below); PETG allowable 22.5 MPa.

**Nominal fit.** Pocket clearance = 14.075 − 14.000 = 0.075 mm; lip interference = 14.000 − 14.000 = 0.000 mm (line to line). On paper the pocket is a clearance fit and the lip a transition.

**Why printed holes print undersize.** The extruded bead is rounded and slightly over-filled, so the inner wall sits inside the nominal circle; plastic shrinks as it cools (an assumed 0.4 % would take 0.056 mm off a Ø14 hole); the squashed first layers (elephant foot) intrude into holes; and the mesh file approximates a circle by straight chords, so a Ø14 hole in a 63-segment mesh (gear parts) loses 0.017 mm across flats and in a 32-segment mesh (plates) 0.067 mm. The project's own bore story points the same way: Ø5.2 too tight on a Ø5.0 shaft means the printed hole lost at least 0.2 mm; at that undersize the Ø5.45 bore leaves 0.25 mm of clearance (0.15 mm at 0.3 mm), not the 0.45 mm on paper.

**Effect of printer undersize u on the lip (b = 7 mm, c = 8.5 mm, ring factor 5.22).**

| Undersize u (mm) | Lip interference | Contact pressure | Hoop stress (SF vs 22.5 MPa) | Insertion force | Pocket Ø14.075 against the bearing |
|---|---|---|---|---|---|
| 0.05 | 0.05 mm | 1.3 MPa | 7.0 MPa (3.2) | 34 N | -0.025 mm (clearance) |
| 0.075 | 0.075 mm | 2.0 MPa | 10.5 MPa (2.1) | 52 N | 0.000 mm (line to line) |
| 0.10 | 0.10 mm | 2.7 MPa | 14.0 MPa (1.6) | 69 N | +0.025 mm (squeezes the race) |
| 0.15 | 0.15 mm | 4.0 MPa | 21.0 MPa (1.1) | 103 N | +0.075 mm |
| 0.20 | 0.20 mm | 5.4 MPa | 28.0 MPa (0.8) | 138 N | +0.125 mm |
| 0.30 | 0.30 mm | 8.0 MPa | 41.9 MPa (0.5) | 207 N | +0.225 mm |

So the design works if the printer undersizes the holes by roughly 0.03 to 0.075 mm: the lip grips the bearing (about 21 N to push it through at 0.03 mm, taken here as the least useful retention) and the pocket leaves it free. Up to u = 0.16 mm the lip stays under the allowable stress, but beyond 0.075 mm the pocket itself starts to squeeze the outer race, and a squeezed race loses its small internal clearance. If the printer is accurate (u near 0) the lip does nothing and the bearing is held only by the pocket; if the printer undersizes by 0.2 mm or more the lip is overloaded and, because PETG relaxes, would loosen with time.

**Fit-coupon logic.** Print a coupon with the same material, orientation and settings as the part: holes from the nominal size −0.10 to +0.30 mm in 0.05 mm steps at Ø5, Ø7 and Ø14, with the hole axis vertical and horizontal (54 holes). Measure each printed hole with pin gauges, fit u(D) = u₀ + s·D (offset plus proportional shrink), then set every drawn hole to its target plus u. Test-insert the bearing and shaft in the hole that should be "line to line". One coupon replaces guessing on every future part and on the spool bore.

**Decision it explains.** Pocket drawn 0.075 mm oversize with a line-to-line entry lip, and a bore opened from Ø5.2 to Ø5.45: both compensate for undersized printed holes; the coupon turns that compensation from a guess into a measurement.

**Limit of the model.** Elastic thick ring with a rigid bearing; printed PETG relaxes with time and temperature, so the interference pressure is a short-term value; the undersize values are illustrative until a coupon is measured.

---

## What must still be measured before a slide can say "measured"

- Vref cap and driver current (a second reading), pull test for the running-torque fraction (section 2).
- Coil resistance, and a 90-minute hold test with thermometers on the motor case and the PETG interface (section 3).
- Stall test of a printed pinion and sync gear (section 4); pad-to-cloth friction and the jaw force with a gauge (section 5).
- Tube wall thickness and alloy; a sustained-load deflection test of a printed arm (section 6).
- Weighed claw mass and a re-extracted centre-of-mass depth; free-decay damping of the hanging claw (sections 1, 2, 5, 7).
- Camera corner noise on real images (section 8); the four-node synchronisation test (section 9); electrical qualification of the 32 ft branch (section 10).
- A fit coupon (section 12).
