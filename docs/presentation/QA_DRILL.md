# RoomCleaner panel Q&A drill (Tue Oct 27)

Rehearsal sheet for Jasper Buntinx. Thirty likely questions in eight groups. Each answer is written to be said aloud in 20 to 30 seconds, in first person, using the deck's own numbers. Each question also carries:

- **Fundamental:** the course-level equation you should be able to write on a whiteboard and substitute into.
- **If pushed:** the honest limit, or what has not been measured yet.

Evidence words, used exactly as on the slides: **MEASURED** (an instrument reading exists), **CALCULATED** (worked from stated inputs and assumptions), **SIMULATED** (a model ran, nothing physical), **PLANNED** (a test is defined, no result). Anything in `[fill in: ...]` is a fact the written record does not contain. Supply it or say "not done yet"; do not guess in the room.

## Facts to fill in before the panel

- [fill in: project start date. The timeline strip says July 16; confirm.]
- [fill in: printer model and filament brand for the fit-critical and load-bearing parts.]
- [fill in: how many winch stations are built today.]
- [fill in: what the gen-1 station in the title photo lifted, for how long, and the result.]
- [fill in: weighed claw mass, and battery mass.]
- [fill in: results of the pull test, hold test and SolidWorks study, if any are run before Oct 27.]
- [fill in: line diameter; caliper readings for the printed v2 and v3 spool bores.]
- [fill in: VDD at the driver when Vref was read; exact meter readings and dates for the 1.14 V fault; what you tried first.]
- [fill in: supply voltage under load at the buck input, and what the brick label says.]
- [fill in: which control-software parts you personally wrote and can walk through line by line.]
- [fill in: how the slide-in station is retained and what load it was checked against.]
- [fill in: whether a bead has been run past a printed homing arm on real line.]

---

## 1. Requirements and "is it done?"

**Q1. "Give me the 30-second version. What does done mean?"**

"I'm building a four-cable ceiling robot: four wall winches hold a claw on four cables, and the claw is designed to descend onto laundry, close two jaws with one servo, carry the load, and release it over a hamper. Done means a 0.9 kg pair of jeans goes from anywhere on the floor into the hamper with nobody touching it, with 2 m/s² of acceleration allowed for. The 0.9 kg is a provisional screening figure, so my first physical test load is 1 lb. Today the design is partly built and the four-station test has not run."

Fundamental: ΣF = 0 on the claw node, with a dynamic load of W(1 + a/g). For 1 lb plus the 0.45 kg budget claw that is 8.86 N static and 10.67 N at +2 m/s².

If pushed: Nothing has lifted jeans. The four-station test (1 lb, 300 mm at 50 mm/s, within 2 mm per cable) is PLANNED. [fill in: what the title-photo station lifted and the result.] [fill in: start date.]

**Q2 (HARD 1). "Your own numbers say the winches can't lift your claw plus jeans. Does the robot work, and why is 450 g still the requirement?"**

"Not yet, and the deck says so. At 1.06 A direct drive the four winches hold about 1.1 kg total in the worst case at the highest task pose, and 0.50 kg at the 0.4 m ceiling limit. The printed claw is estimated at 1.05 to 1.25 kg and has not been weighed, so claw plus 1 lb is about 1.5 to 1.7 kg and claw plus jeans is 2.0 to 2.2 kg, which doesn't fit. The options are a Ø10 core for +25 % (1.38 kg held), a 3:1 reduction at each winch for about 2.7 times (about 3 kg held), or a 0.3 to 0.5 kg payload for the demo, and the first step is a 15-minute luggage-scale pull test."

Fundamental: ΣF = 0 on the claw node (claw mass counts exactly like payload) and F = τ/r at the spool. Need 0.45 kg + 0.9 kg = 1.35 kg against 1.10 kg held, which is 1.22 times too much.

If pushed: 450 g is the number the analysis assumed, not a weighed claw: the v6 gripper was 2.06 kg in CAD and the v7 head is 481 g in CAD. Weighing it is next. [fill in: weighed claw mass.] The pull test matters because the 0.7 running-torque factor is assumed and the true torque could be up to 1.4 times lower if the motor rating is a two-phase figure. I won't pick between the options until that test is in.

**Q3. "What did you do yourself, and what did you buy?"**

"I designed the stations and the claw in SolidWorks, printed and machined the parts, wired the bench and perfboard electronics, and wrote the test plan with pass limits before any test. I made the architecture calls: margins instead of precision, no IMU. The stepper motors, A4988 drivers, ESP32 boards, DROK buck, MG996R servo, bearings, pulleys and line are purchased."

Fundamental: ΣF = 0 on the claw node (Q4). If you can derive one result from a blank page, make it that one.

If pushed: [fill in: which control-software parts you personally wrote and can walk through line by line. Say only what is true.] [fill in: who produced the 1/8 in fin shop drawing and which dimensions you specified.] Don't say "everything else": the supply, LiPo, camera and encoders are bought too.

---

## 2. Statics and cable tension

**Q4. "Walk me through the tension in one cable."**

"With the claw centred and the weight shared equally, each cable carries W over four vertically, so T = W/(4 sin φ), with φ the cable's elevation angle. For 1 lb plus the 0.45 kg budget claw, W is 8.86 N, and the tension is 32.1 N per cable at 0.15 m below the anchors, 16.2 N at 0.30 m, 8.3 N at 0.60 m and 4.6 N at 1.20 m. With +2 m/s² those become 38.6, 19.4, 10.0 and 5.5 N. It doubles each time the depth halves, so cable angle, not payload, sets the limits."

Fundamental: Vertical ΣF = 0: 4T sin φ = W(1 + a/g), with sin φ = d/√(d² + D_h²) and D_h = 2.17 m (centre to corner of the 11 × 9 ft room).

If pushed: CALCULATED only; no tension has been measured on the rig. It assumes a point claw and massless straight cables, and ignores the 84 mm attachment spread, sag, pulley friction and swing.

**Q5. "The claw won't always be centred. How do you know the worst case?"**

"Off-centre there are four cables and three force equations, so the problem is statically indeterminate, and I find the best split with a linear program that minimises the largest tension. The worst spot is high against the middle of a long wall. With a 0.2 m wall margin and +2 m/s², the largest tension there is about 1.10 times the total weight at the highest task pose and 2.42 times at the 0.4 m ceiling limit. The equal-share table is a lower bound for any pose off the centre."

Fundamental: Three equations (ΣFx = ΣFy = ΣFz = 0), four unknown tensions, one redundancy. Minimise max Tᵢ subject to Tᵢ ≥ 0, which is a linear program.

If pushed: Straight lines, no sag, no pretension, best possible split, so a real split will be no better. CALCULATED; nothing is measured. [fill in: whether you have seen the real tension split on the rig.]

**Q6. "Why a 0.4 m ceiling margin, and where do the limits actually bind?"**

"Tension scales as 1/sin φ, so near the anchors the cables go flat and the winch's fixed pull runs out, and I keep the claw at least 0.4 m below the anchors. At that limit the four winches hold only 0.50 kg total in the worst case, against 1.10 kg at the highest task pose, so shallow cables bind hardest and 0.4 m is a floor, not a comfortable margin. Every one of those numbers uses the 0.45 kg claw budget; a printed claw of 1.05 to 1.25 kg raises the centred tension at 0.6 m from 8.3 N to 13.8 to 15.7 N."

Fundamental: T = W/(4 sin φ) ∝ 1/sin φ against a winch limit of 17.9 N running at a full spool, or 11.9 N after the 1.5 skip margin.

If pushed: For the centred 1 lb test load the winches need about 0.50 m of depth with the 1.5 margin (0.33 m with +2 m/s² and no margin), so 0.4 m is below even that. That is why I call the margin a floor.

---

## 3. Drive, motor, driver current, torque

**Q7. "Walk me from Vref to newtons of pull."**

"The A4988 sets coil current by I = Vref/(8·Rs); on my red boards Rs is 0.100 Ω and the trim pot tops out at 0.85 V, so the board caps me at 1.06 A (MEASURED Vref). Scaling the motor's 0.36 N·m rating at 1.5 A gives 0.255 N·m holding at 1.06 A, and I take running torque as 0.7 of that, 0.179 N·m. Then T = τ/r gives 23.8 N at the 7.5 mm core and 17.9 N at a full 10 mm spool, or 11.9 N after a 1.5 skip margin (CALCULATED)."

Fundamental: I = Vref/(8·Rs) = 0.85/0.8; τ ∝ I; F = τ/r.

If pushed: "Tension" means three things in my project: the running pull, the 11.9 N design value, and a 34 N snag worst case (holding torque over the core radius). The 40 N per cable I once quoted is not reachable at 1.06 A and was never a measured limit.

**Q8. "How much do you trust that pull number?"**

"As an upper bound, not much yet. The 0.7 running-torque factor is assumed, and the Vref pot read 0.85 V on one reading and about 0.79 V on another, which is 0.99 A and 7 % less pull. The bigger risk is the torque basis: if the 0.36 N·m rating is a two-phase figure, 1.06 A gives about 0.18 N·m holding, so 16.8 N at the core, 12.6 N at a full spool and an 8.4 N design force. That's why a luggage-scale pull test on one station, empty and full spool, comes first: it replaces the assumed 0.7 with a real number."

Fundamental: τ_run = 0.7·τ_hold (assumed). The A4988 drives both coils at about 0.71 × I_trip, so a two-phase rating scales with 0.71 × 1.06 A, not 1.06 A.

If pushed: Line diameter is assumed 0.5 mm and unmeasured; 0.6 mm gives 17.0 N and 1.0 mm gives 12.3 N at a full spool. I have no recorded VDD at the driver when Vref was read, and a low VDD would also cap Vref. The test sheet runs full-step while the winches run 1/16 microstep. [fill in: pull-test result.]

**Q9. "What does a smaller spool core buy you, and what does it cost?"**

"Since T = τ/r, a Ø10 core instead of Ø15 raises the full-spool design force by 25 %, so the winches hold 1.38 kg against the 1.35 kg needed for the budget claw plus jeans. The cost is a spool redesign: the hub annulus drops to 2.3 mm, so the M3 set screw needs its own boss and the tie-off moves to the flange; the bend ratio sits at the 20:1 floor; and the line paid out per revolution grows from 31.4 to 50.3 mm, so the controller must keep modelling radius against wound length. And it only helps a 0.45 kg claw."

Fundamental: F = τ/r; line per revolution = 2πr; bend ratio = core diameter / line diameter ≥ 20.

If pushed: Ø15 is what's drawn today (5 layers, 10.0 mm full radius). Ø10 builds 6 layers and needs 5093 Hz for 50 mm/s on the core layer, above the 4000 Hz cap in the simulation profile, or a 39 mm/s limit. Line bend life is a rule of thumb; no bend-cycle test exists. Ø8 adds only 8 more points of force and breaks the bend ratio. The choice between core, gearing and payload is open until the pull test.

---

## 4. Heat transfer and the fin

**Q10 (HARD 2). "At 1.06 A in a vented shell your chart shows 51 °C with no fin, under your 60 °C limit. Why a fin, and what have you measured?"**

"The fin was sized when the plan was 1.35 A in a sealed shell, where an earlier review model gave 67 °C sealed with no fin at 1.0 A and 106 °C at 1.5 A. At the 1.06 A driver cap the margin is large, so the fin now buys margin, vented 51 to 41 °C and sealed 64 to 46 °C, and it keeps the loaded PETG tab cooler, which is the creep concern. Every temperature is CALCULATED: coil resistance of 1.8 Ω is assumed, h is 5 to 9 W/m²·K, the alloy and finish are unconfirmed, and no thermometer reading exists yet. The planned test is a 60-minute hold on the vented shell with thermocouples on the motor case, fin and PETG tab, read against 0.94 times the 41 °C prediction, pass below 60 °C."

Fundamental: P = I²R = 1.0625² × 1.8 Ω = 2.0 W; steady state T_motor = T_room + P·R_total from a thermal resistance network.

If pushed: If the bare motor is already fine, the test says the fin is not earning its place. A coil resistance of 1.5 Ω would give 0.83 times the rise. [fill in: hold-test result and thermometer type.] [fill in: alloy check, magnet or file test.]

**Q11. "You drew a 1/8 in fin and built it from 0.019 in sheet. What changed?"**

"A thinner fin conducts less along its length, so I re-ran the fin equation before accepting the sheet. With m = √(2h/(k·t)), efficiency η = tanh(mL)/(mL) falls from 74 % to 37 % and R_fin roughly doubles from 10.9 to 22.1 K/W. The exposed area is the same, so the fin still carries about half the motor's heat and the sealed case runs about 6 K hotter, 46 °C against 40 °C. Then I checked the fit: the 7/8 in centre hole clears the 22.0 mm motor pilot boss by about 0.1 mm per side, and the screws now reach 2.7 mm deeper into the motor."

Fundamental: m = √(2h/(k·t)); η = tanh(mL)/(mL); R_fin = 1/(η·h·A_fin). With h = 7 W/m²·K, k = 160 W/m·K, L = 200 mm: mL = 2.69 as built, 1.05 as drawn.

If pushed: k = 160 assumes an alloy I haven't confirmed, and h = 7 assumes a black fin while the as-built fin is bare metal, which runs hotter: about 41 to 43 °C vented, 46 to 50 °C sealed. The fit is a visual test-fit. Thin sheet can bow and buzz, so I'll flatten it and listen in the hold test. The drawing asks for ±0.1 mm between holes in one setup. [fill in: caliper readings on the finished fin.]

**Q12. "Why can't the printed mount just carry the heat away?"**

"PETG conducts about 1/800 as well as aluminium, 0.2 against 160 W/m·K. Through the 42.3 mm square flange contact, the 5 mm PETG path is 14.0 K/W while 3.2 mm of aluminium is 0.011 K/W, which is 1260 times worse: 800 from conductivity and about 1.6 from thickness. Heat in PETG dies out within a few millimetres of the motor, so the PETG around the motor bolts climbs toward motor temperature while it carries the cable load and creeps."

Fundamental: Conduction R = L/(k·A); convection R = 1/(h·A). For a long fin at equal geometry the conductance ratio is √(160/0.2) = 28.

If pushed: The 1260 times is a flange-slab comparison; the 28 times is the long-fin comparison. PETG at 0.2 W/m·K is an assumed value, not measured on my filament. [fill in: filament brand.]

**Q13. "Why a 60-minute hold test, and what result changes your design?"**

"The hold runs at 1.06 A on the vented shell for 60 minutes, which covers about 94 % of the vented rise, since its time constant is about 21 minutes. A sealed shell is slower, 35 minutes, so 60 minutes reaches only about 82 % of its rise. I read the motor case, fin and PETG tab against 0.94 times the 41 °C prediction, and the pass limit is below 60 °C. If the bare motor is already fine, the fin is not earning its place."

Fundamental: First-order lumped response T(t) = T_room + ΔT∞(1 − e^(−t/τ)); 1 − e^(−60/21) ≈ 94 %, 1 − e^(−60/35) ≈ 82 %.

If pushed: PLANNED; nothing is measured. The limits are written before the test. A 90-minute hold would reach 92 % of the sealed rise. [fill in: confirm 60 or 90 minutes, and the result if run.]

---

## 5. Machine design: gears, tube, PETG, the SolidWorks study, fasteners

**Q14. "Walk me through the Lewis check on your gear teeth."**

"A clamp doesn't stop at a position, it stops when the servo stalls, so every grip loads the teeth at full stall torque, and that is my design case. The pinion force is F_t = 2τ/(m·z) and Lewis bending is σ = F_t/(b·m·Y). Module 1 with a 6 mm face at 6 V stall gave 120 N and 65 MPa, a safety factor of 0.35 against my 22.5 MPa allowable. Module 1.5 with a 16 mm face gives the pinion 2.4 at 4.8 V and 2.05 at 6 V, and the 36-tooth gear 2.9 and 2.5."

Fundamental: σ = F_t/(b·m·Y), F_t = 2τ/(m·z), SF = σ_allow/σ. Y = 0.309 for the 18-tooth pinion; stall torque 0.922 N·m at 4.8 V, 1.079 N·m at 6.0 V.

If pushed: Static Lewis only, with textbook form factors and no dynamic or stress-concentration factor. The 22.5 MPa is half of 45 MPa to cover layer adhesion and fatigue. The 24-tooth sync gear at 6 V is 1.997, just under 2.0; I accepted it as inside the precision of the assumed stall torque. No printed gear has been stalled, and jaw force is SIMULATED. [fill in: the servo supply voltage actually on the claw.]

**Q15. "Why a 2:1 first stage and not 3:1?"**

"The pinion force doesn't depend on the ratio, but everything downstream does. A 3:1 train gives more jaw torque, 1.25 N·m against 0.83 N·m, but loads the 24-tooth sync gear to a safety factor of 1.56 at 4.8 V (1.33 at 6 V) and cuts the jaw stroke from 76.5° to 51°. The v6 inspection also showed the claw about 4.6 times over its mass budget, so the train was rebuilt at 2:1, and that gear set went from 157 g to 96 g in CAD."

Fundamental: τ_out = N·τ_in, per jaw τ_jaw = N·τ_in·η²/2 with η = 0.95 per mesh: 2 × 0.922 × 0.95² / 2 = 0.83 N·m.

If pushed: The 157 g to 96 g comparison is original against rebuilt v6 gears in CAD; the safety factors are for the v7 open-frame train. [fill in: say "rebuilt from my v6 gears" only if you specified the 36-tooth gear and the 53 mm crank radius yourself.]

**Q16. "Will it hold a pair of jeans?"**

"On friction alone, not with margin. Each jaw needs N ≥ m(g + a)/(2μ), which for 0.9 kg of jeans is 17.7 N per jaw at μ = 0.3 and 8.9 N at μ = 0.6. The jaws give 13.3 N at the weakest position, rising to 25 N near a 70 mm grab at 4.8 V. So 1 lb is covered with a margin of about 1.5 at μ = 0.3, but jeans at μ = 0.3 are 0.75 times what's needed at the weakest position, which is why grippy pads and a wider grab matter."

Fundamental: Friction on two pads, 2μN ≥ m(g + a), so N ≥ m(g + a)/(2μ) = 0.9 × 11.81 / 0.6 = 17.7 N.

If pushed: Jaw force is SIMULATED from the four-bar model, with no force-gauge reading, and pad-to-cloth friction has never been measured. TPU pads are PLANNED; the pull test is the first thing to run. Jeans at μ = 0.3 need a grab of at least 43 mm at 4.8 V (22 mm at 6 V). Cloth bunches and interlocks, which may help, but that is an expectation, not data. [fill in: whether any pad has been printed.]

**Q17. "Why an aluminium tube instead of a printed arm?"**

"A long printed arm under constant load creeps, and the camera would slowly shift against the jaws. For the same tube and a 10 N tip load, δ = FL³/(3EI) gives 0.04 mm in aluminium and 1.32 mm in PETG, 33 times more. Creep is the arm's problem; stress relaxation is what loosens the printed collars that grip the tube, so those joints get a cross-bolt, not friction."

Fundamental: δ = F·L³/(3EI) with I = π(D⁴ − d⁴)/64; σ = Mc/I = 1.83 MPa for both materials. Creep ε(t) = σ₀J(t); relaxation σ(t) = ε₀E_r(t).

If pushed: The tube wall is unmeasured: 3 mm and OD 28.54 mm in the CAD, 254.8 mm long after the 50 mm cut, alloy unknown (6061 assumed). The creep figures (62 % stiffness left after 1000 h, 2.1 mm tip deflection) use an assumed exponent; no creep test has been run. A 1 mm wall would keep 41 % of the stiffness at 36 % of the mass. The cross-bolt bearing stress is 5.6 MPa at a 100 N design load against a real load of 16.3 N. [fill in: measured wall and alloy.]

**Q18. "How did you decide how strong printed PETG is?"**

"I haven't tested it, so I derate. For the gear teeth I use 22.5 MPa, half of a 45 MPa tensile figure, to cover layer adhesion and fatigue, and for the station study I use a 25 MPa derated yield with a 2 times dynamic factor. Printed parts are weakest between layers, so I also check the first principal stress across the layers, at most 7.5 MPa. Heat and creep matter as much as strength: my limit for loaded printed parts is 60 °C."

Fundamental: SF = σ_allow/σ_applied; σ = Mc/I. FDM is anisotropic, so the allowable depends on the load direction relative to the layers.

If pushed: Both allowables are assumptions. No printed gear has been stalled and no creep test has been run; a polymer about 57 K below its softening point creeps at any stress. [fill in: print orientation and infill on the load-bearing parts; any pull-test data on printed PETG.]

**Q19. "What does your SolidWorks station study check, and what do you expect?"**

"It's a linear static study of the slide-in station mount at the 34 N slip-limit line tension, on derated PETG: peak von Mises at most 8.33 MPa, which is SF 3 on 25 MPa; first principal stress across layers at most 7.5 MPa; and cable-exit deflection at most 0.5 mm, because anchor error turns one-to-one into claw position error. My hand estimate puts the motor-tab root at about 8 to 14 MPa with stress concentration, so I expect the study to find a design issue rather than confirm one. It's PLANNED and there is no result yet."

Fundamental: σ = Mc/I at the rail root; δ = FL³/(3EI) for the cable-exit lever; SF = σ_allow/σ.

If pushed: "SF 3 at 34 N" and "SF 1.5 at 68 N" are one check in a linear model, not two. 34 N is the direct-drive slip limit; a 3:1 reduction raises the line load about 2.7 times, to about 92 N, and I would repeat the study. Linear statics can't see creep or layer adhesion; the physical pull test closes that gap. [fill in: peak stress, SF and deflection once run.]

**Q20. "How is the station fastened and retained, and where can it fail?"**

"The stations are designed to screw into wall studs. The line pulls the station away from the wall, so the screws see mostly pull-out and prying, plus some shear from the vertical component of the line. Today the slide-in is held by three dovetail ribs and J-lips, and a positive lock is still an open item. The 34 N check is a stress check on the motor tab, not a retention check."

Fundamental: Moment balance about the station's lower edge gives upper-screw pull-out; cross-bolt bearing stress σ_b = F/(2·d·t); about 3 mm of engagement for an M3 thread-forming screw.

If pushed: The two screw columns are 37.0 mm apart against a 38.1 mm stud, so how the six screws are fixed is not settled. The thinner fin sheet puts the motor screws 2.7 mm deeper into the motor, so I check thread depth. The station pull test is PLANNED; nothing is tested. [fill in: retention feature and the load it was checked against.]

---

## 6. Controls and calibration

**Q21. "Why no PID? How do you know where the claw is?"**

"Each winch runs open loop. A stepper commanded to a step count is already a position actuator as long as it doesn't skip, and at 3200 microsteps per revolution one microstep is about 15 µm of line on the core layer. The feedback's job is to catch a skip, not to regulate position, so the station has an encoder port with 4096 counts per spool revolution as a watchdog, and a mismatch is a fault, and every fault holds torque. That is designed and simulated, not run on four stations."

Fundamental: Δℓ = N_steps · 2πr/3200 = 14.7 µm per microstep at r = 7.5 mm; open loop holds while required torque stays below the motor's available torque with the 1.5 margin; encoder resolution 2πr/4096 = 11.5 µm per count.

If pushed: Steppers lose steps silently on a snag or shock; that is the failure I design against, and the four-station test requires no step loss and at most 2 mm per cable. SIMULATED only. 50 mm/s on the Ø15 core layer needs 3395 Hz, below the 4000 Hz cap. [fill in: the watchdog mismatch threshold in mm, and whether an encoder is fitted on a built station.]

**Q22. "Why one controller per winch, and what does timing error cost?"**

"In July I kept one controller so synchronised motion was free; in October 32 ft harness runs and a one-plug station argued for one controller per winch. The cost is that four cables are over-constrained: at 50 mm/s a 50 ms skew is 2.5 mm of length error, and with an assumed 3 N/mm line stiffness that is a 7.5 N spike, about 90 % of the static tension at 0.6 m depth. So the host plans and each station executes timed segments on its own clock with feed-hold and leases, and a stop never disables."

Fundamental: Δℓ = v·Δt; F = k·Δℓ with k = EA/L; wire drop V = I·ρ·2L/A.

If pushed: SIMULATED only: lease-aligned stop spread about 18 ms and 10 of 10 lossy motions completed at 2 to 5 % packet loss. The 50 ms skew and 3 N/mm stiffness are assumptions, and 7.5 N is an upper bound because the error redistributes over the other three cables. On the 32 ft run at 2 A (illustrative) the drop is 0.82 V on 18 AWG against 0.51 V on 16 AWG, so 16 AWG is preferred; it is not purchased yet.

**Q23. "How accurate is the camera? Where does 6.6 mm come from?"**

"A small rotation error in the tag pose moves a point at lever arm L by δx = σθ·L. One 152.4 mm tag at 0.51 m with 0.3 px corner noise gives about 12.9 mrad of tilt noise, which is 6.6 mm per frame. A floor board of 150 mm tags on a 0.25 m pitch cuts that to about 1.3 mrad, 0.7 mm, with four tags in view; with only two in view it is 4.9 mrad, 2.5 mm."

Fundamental: δx = σθ·L; averaging N independent frames, σ_N = σ/√N (30 frames takes 12.9 to 2.4 mrad); single tag σθ ≈ 2σ_px·z²/(f·a²).

If pushed: CALCULATED bound with independent Gaussian noise; the 520 px focal length is a camera guess and real corner noise is unmeasured. A static bias isn't averaged: 1 mrad still leaves 0.5 mm. The 0.7 mm is per-frame attitude error; absolute cable-length uncertainty is a different quantity, predicted at 12 to 16 mm in simulation, above the 12 mm bead overtravel, which is why safety rides on ceiling and wall margins. The claw also hangs tilted up to about 13° near the corners (20.7° with the current-head estimate), so the grip-tilt rule needs a decision.

**Q24. "The optimiser converged. Why isn't that enough to accept a calibration?"**

"Because a converged weighted least-squares fit only says the data agree with the model. In my one-cable toy, the 0.6 m and 1.8 m excitation boxes both gave a whitened residual near 1.0, yet in the small box the anchor range and length offset were nine times less identifiable: predicted weak-direction σ of 351 mm against 39 mm. So I accept a calibration only on identifiability, residual adequacy, no alternate optimum, witness agreement and a predicted σ over the work volume; otherwise the robot stays inside the validated region."

Fundamental: θ̂ = argmin Σ r²/σ²; covariance (JᵀWJ)⁻¹; reduced χ² = rᵀWr/(m − n).

If pushed: The toy is one cable in two dimensions, not the four-cable estimator. In simulation: 6 of 6 startups, 91 to 97 % of slack readings resolved, predicted σ of 12 to 16 mm, and 3 of 6 runs reach full-room trust. All SIMULATED, nothing on hardware, and those counts have not had an independent check yet. The slack probe reels one cable at a time: no motion means slack. [fill in: any hardware test of the probe.]

---

## 7. Safety

**Q25 (HARD 3). "Your only stop is a power strip and cutting power drops the claw. What is the safety case, and what happens if a stepper skips?"**

"It is a deliberate category-0 stop with no brake: cutting 12 V removes holding torque and the claw falls. The accepted mitigation is that nobody stands under the robot while it moves, with a 1 lb first gate and a slow final approach. In software a stop never disables: every fault and pause holds torque, only a disarm confirmed with the claw supported releases it, and nothing resumes after a reboot. No safety-rated function is claimed; a controlled stop or self-locking drive is a next-generation item. Steppers can lose steps silently on a snag, so the four-station test requires no step loss and at most 2 mm per cable."

Fundamental: Stop category 0 is uncontrolled removal of power. With no brake or self-locking element the only holding effort is motor torque, τ_hold ≈ 0.255 N·m at 1.06 A (CALCULATED), which goes to zero with the power.

If pushed: None of this has run on four stations, and the control behaviour is SIMULATED. ISO 13849 and IEC 61508 are not claimed. This is a hobby prototype; load-bearing, high-speed or energy-storage parts need qualified supervision and controlled testing before use.

**Q26. "What else could go wrong in the room: the swinging claw, the wall, the battery?"**

"Three things. A hanging claw swings, so grips wait for a settle dwell and a tilt check. The stations are designed to screw into studs, but the screw pattern and slide-in lock are still open, which is why the pull test matters. And the claw's 2S LiPo is charged on the claw only with the main switch off, attended, at 8.4 V CC/CV and at most 1 A (decision D31), and no mains goes inside printed housings. Above all, nobody stands under the robot."

Fundamental: Pendulum period T = 2π√(L/g), compound pendulum T = 2π√((k² + L²)/(gL)); tilt θ ≈ M_v/(W·L); swing amplitude decays as e^(−2πζn).

If pushed: The recorded centre-of-mass depth of 0.196 m (T = 0.89 s) is stale; the estimate for the current head is 0.116 m (0.09 to 0.14 m), about 0.68 s, and a loaded release at 0.389 m is about 1.25 s. Damping is unmeasured: at ζ = 0.02, 53 % of the swing remains after 5 periods, so the dwell alone can't be relied on. [fill in: free-decay test result.]

---

## 8. Process and judgement

**Q27. "What would you do differently?"**

"I'd buy standard pulleys and couplers instead of designing them, and build and test one complete station before building four. I'd also print a fit coupon before the part: my first spool bore, Ø5.2, printed too tight on the 5 mm shaft, so I opened it to Ø5.45. I have no caliper reading for the printed bore yet, and a 54-hole coupon is planned but none has been printed. The lesson is that the printed hole, not the drawn one, is the dimension."

Fundamental: Diametral interference u = D_part − D_hole; fit the printer's undersize as u(D) = u₀ + s·D from a coupon, then draw each hole at target plus u.

If pushed: A Ø5.2 hole too tight on a Ø5.0 shaft means the printed hole lost at least 0.2 mm, so the Ø5.45 bore really leaves about 0.25 mm of clearance, not 0.45 mm. The bearing pocket (Ø14.075 with a line-to-line Ø14.000 lip) only works if the printer undersizes holes by roughly 0.03 to 0.075 mm, which is a calculation, not a measurement. [fill in: printer model, filament, and the v2 and v3 bore readings.]

**Q28. "What did you delete, and why?"**

"My best decisions were deletions: the IMU; five fingers became two jaws; 50 mm of tube, which saves about 33 g; the housing block, replaced by an open frame, taking the head from 1,044 g to 481 g in CAD; and the 5 lb reserve target, with a 1 lb gate first. I also dropped the contactor e-stop and use the switched power strip as the only stop, and I've priced what that costs: the claw drops when power is cut. I cut 50 mm of tube, not the 100 mm I was offered, because we can always cut more."

Fundamental: T = W/(4 sin φ): claw mass counts exactly like payload, so every gram removed is a gram of payload. Mass roll-up Σmᵢ against the 450 g budget.

If pushed: The 33 g assumes the 3 mm CAD tube wall (a 1 mm wall would save about 12 g), and the 560 g is a CAD figure. The five fingers were never built. [fill in: which of these deletions you decided yourself.]

**Q29. "How did you check your own work?"**

"Three ways. Every number on a slide is recomputed from one calculation set built from the project's own inputs, with supplied facts kept apart from assumptions, and each number is tagged MEASURED, CALCULATED, SIMULATED or PLANNED. CAD geometry gets independent checks: the first drop-arm revision of the homing switch missed the line by 5 mm in X and 10.5 mm in Y, a check caught it, and rev D overlaps the 5 mm bead by 3.75 mm. And I write pass limits before tests, and I've withdrawn numbers that didn't reproduce, like the 750 g claw budget."

Fundamental: Independent recomputation and unit checks, for example I = 0.85/0.8 = 1.0625 A; a second solution of the worst-case tension problem agrees with the first to about 0.01 kg (0.51, 0.74 and 1.10 kg against 0.50, 0.73 and 1.10 kg).

If pushed: Checking is not testing. CALCULATED and SIMULATED are not MEASURED, and sampling a CAD solid is not a continuous proof. The rev D arm is a CAD check; no bead has tripped a printed arm on real line. [fill in: whether a trip test has been run.]

**Q30. "What is the biggest mistake you made on this project?"**

"I carried a 450 g claw budget through my capacity calculations while the printed design grew to an estimated 1.05 to 1.25 kg that I hadn't weighed. My own numbers then told me the claw outgrew my winches: the driver caps current at 1.06 A, the winches hold about 1.1 kg in the worst case at task height, and claw plus jeans is 2.0 to 2.2 kg. I'm telling you because the fix is a measurement: weigh the claw, run the pull test, then pick between the Ø10 core, 3:1 gearing and a lighter payload."

Fundamental: A budget is not a measurement. ΣF = 0 on the claw node with W = m·g·(1 + a/g); the capacity check is Σm_claw + m_payload ≤ m_held.

If pushed: A second one: I trusted a nominal logic rail until the meter read 1.14 V on a motor that would not move, and since then I measure the supply before I touch code. That reading was on my meter and was not logged or photographed. The as-built board still needs its meter checklist, and the 18 V read at the supply against a 12 V label is still to re-measure under load. [fill in: exact readings, dates, and what you tried first.]

---

## 9. Control logic and obstacles (deck section 7, added 10/21)

**Q31. "What is the difference between your first control logic and the one that runs now?"**

"The first logic was written against a simulator, so it trusted its model: the claw was wherever the cables were told to put it, the anchors came from a tape measure, one central board stepped all four motors, a ceiling camera found the laundry, and a grab was assumed to work once the claw closed. The final logic measures before it trusts and checks after it acts. The claw camera reads a floor board and the robot refits its own anchors and cable lengths at every startup. Each station runs time-stamped segments and holds if the host goes quiet. The camera confirms every pickup and delivery, and the robot moves only where the calibration earned trust."

Fundamental: Same inverse kinematics in both, L_i = ‖a_i − p‖. What changed is where a_i and the cable zero lengths come from: a weighted least-squares fit, min Σ (L_{i0} + d_{ik} − ‖a_i − p_k‖)², accepted only if the held-out poses agree.

If pushed: Five layers, top to bottom: phone, supervisor (one robot state), startup and tasks, planner and coordinator, stations. Only the stations turn motors, and no fault removes holding torque. All of it is SIMULATED end to end; the first hardware test runs the startup and a short move, not a pickup.

**Q32. "How does it deal with obstacles? Can it see them?"**

"Known obstacles, like a tall shelf, a lamp or a ceiling fan, are entered as keep-out cylinders. Before any motion the planner checks every point of the path: each cable line from its pulley to the claw against each cylinder, plus the wall and ceiling margins, the 1.6 m task height and the cable tensions. A path that fails is refused before anything moves. What it cannot do yet is see an obstacle it was not told about. The claw camera looks down at the floor and has no depth, so a person, a pet or a moved chair under a cable is not detected. That is why the rule is nobody under the robot, with PAUSE and the power strip."

Fundamental: Cable i is the segment q(s) = a_i + s(b_i − a_i), 0 ≤ s ≤ 1. It hits a cylinder if, for some s, z_low ≤ q_z ≤ z_high and (q_x − x_c)² + (q_y − y_c)² ≤ r². Example on the slide: a 1.9 m shelf 1 m out from corner A; the claw at the room centre is clear at 1.5 m and refused at 0.8 m, because cable A would pass through the shelf.

If pushed: While moving, the encoder catches a cable that jams or stalls its motor (TRACKING fault: stop, holding torque kept), and the camera catches a failed grip. A snag that does not stall the motor is not detected. The planner refuses rather than re-routes. One gap I found writing this: an item it cannot reach stops the whole task instead of being skipped; that is a small fix. Next: keep-out zones drawn in the app, and furniture footprints mapped from the claw camera's scans. No obstacle list is configured for my room yet.

---

## If you only rehearse ten

1. Q2: the claw-versus-winch capacity question; know 1.1 kg, 0.50 kg, 1.05 to 1.25 kg and the three options cold.
2. Q10: why a fin when 51 °C is already under 60 °C; say "assumed" and "no thermometer reading yet".
3. Q25: the power-strip stop and a skipping stepper; say "category-0", "stop never disables", "not safety-rated".
4. Q8: how much you trust the pull number; the 0.7 factor and the two-phase torque basis.
5. Q6: where the limits actually bind; the ceiling is the harder case at 0.50 kg.
6. Q11: the 1/8 in to 0.019 in fin; derive η = tanh(mL)/(mL) at the whiteboard.
7. Q14: Lewis at stall, from F_t = 2τ/(m·z) to the safety factors.
8. Q16: jeans on friction alone; N ≥ m(g + a)/(2μ), 17.7 N against 13.3 N.
9. Q3: what you did yourself and what you bought; fill in the software line first.
10. Q30: biggest mistake; the 450 g budget, told plainly.

## Phrases to avoid

- "Proven", "validated", "verified" for anything physical. Say CALCULATED, SIMULATED or PLANNED.
- "It works", "it holds", "it lifts" for the four-station test, hold test, pull test, station study or homing trip test. None has a result on record.
- Never say or imply the robot has lifted jeans. The title photo is "a gen-1 station lifting a test weight" [fill in: weight and result].
- "The robot picks laundry off the floor" in present tense. Say "is designed to".
- "The winches can lift the claw plus jeans." At 1.06 A direct drive they cannot.
- "40 N per cable", "about 43 N", "a 750 g claw budget", or "34 N tension" without saying it is the snag case.
- "Walls bind before the ceiling." At the 0.4 m ceiling limit the ceiling is the harder case.
- "Geometry buys it back" or "the Ø10 core solves it." It is +25 % and the decision is open.
- Temperatures as facts ("it runs at 46 °C"), or "sealed station" as if one were built. Say "the model predicts".
- "0.7 mm accuracy" without "per frame, four tags in view" (two tags: 2.5 mm), or "calibrated" or "converged" as acceptance.
- "I wrote the software", "I rebuilt my own gears", "everything else I made", or "four stations" as built, unless true.
- "Safety-rated", "fail-safe" or "e-stop" for the power strip.
- "SF 3 and SF 1.5" as two separate checks; "MEASURED" for the 1.14 V fault, the fin fit or the 18 V reading without saying how it was taken.
- "Never measured" or "always" claims about the record. Say "I have no reading yet."

---

Sources read for this sheet: docs/presentation/DECK_STORYLINE.md, docs/presentation/FUNDAMENTALS.md, calculations/presentation_fundamentals.json, docs/presentation/deck/deck_notes.js, verification/deck_factcheck.md (hard questions and findings table), docs/decisions/WINCH_CAPACITY_20261021.md, docs/presentation/DECISION_STORIES.md (open questions).
