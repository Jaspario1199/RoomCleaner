# RoomCleaner deck — storyline v3 (story-driven)

Draft for the Tue Oct 27 panel (Mechanical Engineer, Insource Manufacturing,
Starlink; 6 engineers; ~30 min of content inside 50 min). Builds on
`SPACEX_OUTLINE.md` (v2, kept) and the trouble log in `DECISION_STORIES.md`.
Every number comes from `FUNDAMENTALS.md` / `calculations/presentation_fundamentals.py`
or the cited verification file. Style: `STYLE_GUIDE.md`.

## What the research says a panel like this rewards

Sources are prep guides and interview reports, not an official SpaceX
document. They agree with each other and with the recruiter's notes in
`SPACEX_OUTLINE.md`.

- **Your own decisions, defended.** Panels push on what *you* decided: the
  options you actually had, the evidence, the cost you accepted, and what
  happens when your choice fails. ([prachub][1], [skills guide][2])
- **Fundamentals under questioning.** Engineering panels drill shear and moment,
  structures, thermo, fluids and controls. Each slide therefore carries one
  fundamental equation you can derive at the whiteboard. ([zerogtalent][3])
- **Failures, told honestly.** A common mistake is presenting only what went
  well. ([towardsdatascience][4])
- **One message, few details.** Leave room for interruptions: answer the
  question, then return to the thread. ([towardsdatascience][4], [prachub][1])
- **Trade-study shape.** Requirement → options → criteria → choice → evidence is
  the standard design-review pattern. ([trade studies][5], [UMD PDR][6])
- **SpaceX's own design habit** (the five-step process, 2021 interview): question
  every requirement, **delete parts**, then simplify, accelerate, automate.
  Several of your decisions are deletions: the IMU, the yaw guard, five
  fingers becoming two jaws, 50 mm of tube, the open gearbox frame. Show that
  pattern in the closing slide; don't name-drop the process. ([OODA transcript][7])

[1]: https://prachub.com/interview-questions/present-a-technical-project-under-active-follow-up
[2]: https://skillselion.com/skills/erichowens/some_claude_skills/tech-presentation-interview
[3]: https://zerogtalent.com/blog/spacex-onsite-interview-2026
[4]: https://towardsdatascience.com/how-to-present-your-project-in-a-software-engineer-job-interview-d4d3fc184308/
[5]: https://microsoft.github.io/code-with-engineering-playbook/design/design-reviews/trade-studies/
[6]: https://spacecraft.ssl.umd.edu/old_site/academics/484S03/484_deliverables.html
[7]: https://oodaloop.com/analysis/archive/the-everyday-astronaut-elon-musk-and-his-five-step-engineering-process/

## The spine

> **I set out to build a ceiling robot that picks laundry off my floor. Every
> time a measurement disagreed with my plan, I changed the design, and every
> change traces back to a first-principles equation.**

Each decision slide follows your flow, shown as the five-step rail at the
bottom of the slide (rename the rail labels in the style kit):

**WANTED → REALIZED → DECIDED → RESULT → BUT**

- **BUT** is mandatory. It names the cost you accepted or what is still
  unproven. That honesty is the point.
- Each decision slide also carries one **fundamentals box**: the equation and
  the numbers substituted in.
- Each number carries an evidence pill: MEASURED / CALCULATED / SIMULATED /
  PLANNED.

## Time budget (30 min)

| Act | Slides | Minutes |
|---|---|---|
| Open: who, what, done-means | 1–3 | 3.5 |
| Act 1: physics sets the limits | 4–7 | 9 |
| Act 2: making it buildable | 8–12 | 10 |
| Act 3: electronics and debugging | 13–15 | 5 |
| Close: evidence, lessons | 16–17 | 2.5 |

---

## Slides

### 1 · Title (A)
**RoomCleaner — a four-cable ceiling robot that picks laundry off the floor**
- Hero: photo 13 (gen-1 station lifting the test weight). Name, role, date.

### 2 · What I built, and how I worked (C-variant, no rail)
**Claim: "A solo build: four winch stations, a camera claw and the software, July to October."**
- Timeline strip (H): Jul 16 concept, then Aug gen-1 bench, then Oct 7 SolidWorks gen-2, then Oct 20 gripper v6, then Oct 27.
- Say plainly: purchased modules (A4988 driver, ESP32, DROK buck, MG996R servo); everything else designed, printed, machined and wired by me.
- Evidence legend: what MEASURED / CALCULATED / SIMULATED / PLANNED mean.
- **Need from Jasper:** confirm start date (git says Jul 16), printer and filament.

### 3 · The problem and what "done" means (D, requirements cards)
**Claim: "Done means: a 0.9 kg pair of jeans from anywhere on the floor into the hamper, with nobody touching it."**
- Cards with the requirements:
  - payload 0.9 kg plus 2 m/s²;
  - claw mass target;
  - four stations into studs;
  - kill switch = the switched strip;
  - nobody under the robot.
- Visual: station render (`renders/station_v3_assembly.png`) plus claw render (`claw_v6_camera_bay.png`).
- Rail: none. Set up the acts.

---

## Act 1 — Physics sets the limits

### 4 · Cable statics (F, chart)
**Claim: "Cable tension, not payload, sets how high the claw can go."**
- **WANTED:** use the whole room height.
- **REALIZED:** as the claw rises toward the anchors the cables flatten and tension explodes: T ≈ W / (4 sin φ).
- **DECIDED:** keep the claw 0.4 m below the anchors; plan with a tension-aware ceiling.
- **RESULT:** for 1 lb plus a 0.45 kg claw, about 32 N per cable at 0.15 m below the anchors versus about 8 N at 0.6 m. [FUND §1]
- **BUT:** the claw's own mass matters as much as the payload; every 0.1 kg of claw costs about 0.22 lb of lift.
- Fundamentals box: ΣF = 0 on the claw; four-cable equal share.
- Chart: tension vs depth below anchors (native line chart, focus series orange).
- Likely question: *"What about off-centre?"* Least-norm tension distribution; worst spot is high against a long wall (R10).

### 5 · Motor, driver, spool (E, big number) — **new, measured**
**Claim: "The driver board, not the motor, capped my pull — so I'm buying it back with geometry."**
- **WANTED:** raise drive current from 1.0 to 1.35 A for about 43 N per cable, once the heat fin made the extra heat OK.
- **REALIZED:** on my red A4988 boards (R100 sense resistors, 3.3 V logic), the Vref trim pot tops out at **0.85 V**. Since I = Vref / (8·Rs), that caps current at **1.06 A** (MEASURED).
- **DECIDED:** don't hack the driver and don't run 5 V logic (a 3.3 V GPIO can't guarantee a HIGH). Run at the board maximum and recover pull mechanically: T = τ / r, so a smaller spool core gives more tension.
- **RESULT:** about 34 N per cable at 1.06 A; spool-core options are in [FUND §2].
- **BUT:** a smaller core means slower lift and more layers. Lift capacity now depends on claw mass and the ceiling margin.
- Big number: **0.85 V → 1.06 A**. Equation strip: I = Vref / (8 Rs); T = τ / r; τ ∝ I.

### 6 · Heat (C)
**Claim: "Sealing the station turned the motor mount into its hottest, most-loaded joint."**
- **WANTED:** a clean, closed printed shell around each winch.
- **REALIZED** (Jasper raised this): a stepper holding the claw dissipates P = I²R continuously. Its only way out was conduction into PETG, which conducts about 1/800 as well as aluminium (k ≈ 0.2 vs ≈ 160 W/m·K). The joint carrying the cable load heads toward 70–100 °C and creeps.
- **DECIDED:** among seven options (vent, aluminium fin, clip-on sink, TMC2209 drivers, ASA shell, thermistor park, lower current), take vents plus an aluminium fin through the shell. It is the biggest gain for no new electronics.
- **RESULT:** two-node model: sealed shell at 1.0 A is 67 °C without the fin and about 50 °C with it (CALCULATED, 30 °C ambient; ambient-corrected numbers in [FUND §3]).
- **BUT:** no thermometer number yet; the 60-minute hold test is planned.
- Fundamentals box: thermal resistance network, R = L/(kA) and R_conv = 1/(hA); Joule heating.

### 7 · Building the fin (G, photo spread) — **manufacturing story**
**Claim: "I drew a 1/8-inch plate and built a 0.019-inch fin — then re-checked the physics."**
- **WANTED:** the drawn 1/8 in plate (fin efficiency about 75 %).
- **REALIZED:** the sheet I could shear and drill on the bench was 0.019 in. Thinner fins conduct less: η = tanh(mL)/(mL), with m = √(2h/kt).
- **DECIDED:** re-run the fin equation before accepting it. η falls to about 38 %, but the fin still carries about half the motor's heat and keeps the motor near 50–55 °C at 1.06 A in a vented shell.
- **RESULT:**
  - Sheared and drilled myself on the mill from my own Letter-size drawing.
  - The 7/8 in centre hole still clears the 22.0 mm motor pilot boss, by about 0.1 mm per side.
  - All four M3 holes line up (photos 16–18).
- **BUT:** thin sheet bows and can buzz, so flatten it and listen in the hold test. Screws now reach 2.7 mm deeper into the motor, so check thread depth.
- Photos: 06 shear, 03 mill set-up with drawing, 01 drilling, 16 fitted on motor.
- Strong for a manufacturing panel: drawing, then process, then deviation, then re-analysis, then fit check.

---

## Act 2 — Making it buildable

### 8 · Spool (C)
**Claim: "My first spool was longer than the motor shaft it sat on — and the fix changed the math."**
- **WANTED:** a 32 mm winding drum on a Ø20 core.
- **REALIZED:** the spool extended about 14.5 mm past the 24 mm shaft. Shortening it (Ø15 core, 16 mm drum) changes:
  - layers: 5 for 20 ft of line;
  - line force: 24 to 18 N as it fills;
  - length per rev: changes by 33 %.
- **DECIDED:** the controller uses radius as a function of wound length.
- **RESULT** of the v2 print: the bore printed too tight on the 5 mm shaft, so I opened it from Ø5.2 to Ø5.45.
- **BUT:** printed holes shrink. Next time, print a fit coupon first. The printed bore was never measured with calipers.
- Fundamentals box: r(n) = r₀ + n·d·packing; T = τ / r(n); ℓ per rev = 2πr.
- **Need:** v2/v3 printed bore caliper readings; line diameter.

### 9 · Homing switch (C, render plus callouts)
**Claim: "The bead must never cross the pulley — my first fix still missed the line by 5 mm."**
- **WANTED:** a bead on the line trips a switch at the home position.
- **REALIZED** (Jasper's find): with the switch mid-span, the bead had to ride over the pulley groove every cycle.
- **DECIDED:** a drop arm under the pulley.
- **RESULT:**
  - Rev C failed a geometric check: the roller was 5 mm off the line in X and 10.5 mm off in Y, so the ±5 mm slot couldn't fix it.
  - Rev D lands the roller on the line with 3.75 mm overlap on a 5 mm bead.
- **BUT:** never trip-tested on real line yet.
- Fundamentals box: tolerance stack across the 18–22 mm pulley range.

### 10 · The removable station and its stress test (C) — **SolidWorks study tomorrow**
**Claim: "Making the station removable moved the anchor from a screw to a slide — so I stress-tested the slide."**
- **WANTED:** to swap a station without re-calibrating the room.
- **REALIZED:** anchor error turns 1:1 into claw position error, so the slide-in must not move. The line pulls the station *away* from the wall, so the stud screws see pull-out, not shear.
- **DECIDED:** a fixed wall frame plus a slide-in housing with positive retention, sized for the slip-limit tension × dynamic factor, with SF ≥ 3 on derated PETG.
- **RESULT:** SolidWorks linear static study (PLANNED → fill in): peak stress, safety factor, deflection at the cable exit against a ≤ 0.5 mm limit. See `docs/simulation/SW_STATIC_STATION_MOUNT.md`.
- **BUT:** linear statics can't see creep or layer weakness, so a physical pull test closes the gap.
- Fundamentals box: σ = Mc/I at the rail root; screw pull-out; δ = FL³/(3EI) for the exit lever.

### 11 · Gripper (D, options) — **evolution**
**Claim: "Stall is the design case for a printed gear — so I sized the teeth for the moment the claw squeezes cloth."**
- **WANTED:** five soft tendon fingers that gather cloth.
- **REALIZED:** I chose a clamp because it is simpler to build and test. The clamp stalls the servo on *every* grip, so teeth see stall torque every cycle. Lewis bending: module 1 would run SF 0.35–0.41; module 1.5 with a 16 mm face runs about 2.0–2.5.
- **DECIDED:**
  - Module 1.5.
  - Then the v6 inspection showed the claw was about 4.6× its mass budget.
  - So 2:1 instead of 3:1: my own gears with 36T instead of 54T and an R53 crank instead of R75.
  - Kept my press-fit bearing pockets (Ø14.075 with a Ø14.000 lead-in lip), and added clearances: 0.42 mm backlash, a 0.3 mm axial relief.
- **RESULT:** gear set 157 g → 96 g (CAD); all features identical to my originals except the intended changes, verified at 257 checks.
- **BUT:** grip on jeans is marginal on friction alone. At μ = 0.3 it needs about 18 N per jaw versus 13–25 N available, so pad grip matters. The 7-hole web is SF about 1.7, so 6 holes would give 3.75.
- Fundamentals box: σ = F_t / (b·m·Y); τ_out = N·τ_in; N ≥ m(g+a)/(2μ).

### 12 · Claw camera and tube (C, render + view diagram)
**Claim: "I wanted the camera to see everything — the geometry says it can't at the moment of contact, and that's fine."**
- **WANTED:** a long arm so the camera sees the jaws and floor. Aluminium tube rather than PETG, because a long printed arm under constant load creeps and would slowly misalign camera and jaws. That's Jasper's reason.
- **REALIZED:**
  - At contact the gearbox plate hides the grasp spot.
  - By similar triangles the spot reappears above a hover height D* that *drops* when the tube is shorter.
  - A shorter tube also shrinks the view and lowers the cable tie-offs toward furniture.
- **DECIDED:** cut 50 mm, not the 100 mm I was offered: "we can always cut more".
- **RESULT:** the spot is visible from 140 mm of hover (was 172 mm); saves 33 g. SIMULATED (ray-cast).
- **BUT:** the last ~14 cm of descent is blind, so add a short visual correction step at the hover.
- Fundamentals box: similar triangles D* = (0.387(512−c) − 93)/0.613; δ = FL³/(3EI) for the tube; creep vs stress relaxation.

---

## Act 3 — Electronics and debugging

### 13 · Central → distributed electronics (D)
**Claim: "Moving to one controller per winch fixed the wiring — and priced every millisecond of sync error."**
- **WANTED (July):** one controller so synchronised motion was free.
- **REALIZED (October):** 32 ft harness runs and a one-plug station. But four cables are over-constrained: Δℓ = v·Δt is 2.5 mm per 50 ms at 50 mm/s, and F = k·Δℓ is about 8 N, the size of the static load.
- **DECIDED:** the host plans; each station executes timed segments in its own clock with feed-hold and leases. Stop never disables.
- **RESULT:** SIMULATED only.
- **BUT:** not yet run on four stations; the pass criteria are written first.
- Fundamentals box: Δℓ = vΔt; F = kΔℓ; wire drop V = I·ρ·2L/A (16 AWG chosen for the 32 ft run).

### 14 · "The log said stepping; the meter said 1.14 V" (C) — **failure story**
**Claim: "A motor that wouldn't move taught me to measure the supply before touching the code."**
- **WANTED:** a first motion on the new station board.
- **REALIZED:** pulses were being sent but the shaft didn't move. ENABLE toggled correctly; the 3.3 V logic rail read 1.14 V. Then on Oct 21 the same habit caught a second limit: the Vref pot maxed at 0.85 V.
- **DECIDED:**
  - 3.3 V soldered, not jumpered;
  - pull resistors so the driver boots disabled;
  - a JP1 link so USB and the buck never fight;
  - a measure-VDD step in the bring-up procedure.
- **RESULT:** Rev D schematic plus a net-checked perfboard layout; motion after the repair.
- **BUT:** the as-built board still needs its meter checklist.
- Photos 07, 08, 12, plus the perfboard once built.
- **Need:** exact readings and dates, and what you tried first.

### 15 · Calibration: margins, not precision (C)
**Claim: "I stopped trying to buy precision and moved the safety into margins."**
- **WANTED:** absolute cable lengths from vision alone.
- **REALIZED:**
  - Lever-arm error is δx = σ_θ·L, so a single tag gives about 6 mm per frame at 0.6 m.
  - Calibration σ stayed above the 12 mm bead overtravel.
  - Without the IMU, a single tag wasn't enough.
- **DECIDED (Jasper's ideas):**
  - ceiling and wall margins carry the safety (D26);
  - probe slack by reeling one cable at a time: "no motion = slack";
  - drop the IMU;
  - lay a printed floor board at 250 mm pitch.
- **RESULT (SIMULATED):**
  - 6/6 startups;
  - 91–97 % of slack readings resolved;
  - predicted σ 12–16 mm;
  - 3 of 6 runs reach full-room trust.
- **BUT:**
  - the claw hangs tilted up to about 13° near the corners, so the grip-tilt rule needs a decision;
  - all of it is simulation.
- Fundamentals box: δx = σθL; σ/√N; least squares acceptance ≠ "converged".

---

## Close

### 16 · Evidence so far, and the next gate (table)
**Claim: "What I've measured, what I've calculated, and the test that decides the rest."**

| Measured | Calculated | Simulated | Planned (with pass limits) |
|---|---|---|---|
| Vref 0.75–0.85 V; one motor turned on all four driver channels; 18 V on the meter; buck 5.00 V; fin fit; logic rail 1.14 V fault | statics, Lewis, fin, wire drop | control system, calibration, camera view | 60-min hold test (< 60 °C); station pull test; 1 lb four-station 300 mm at 50 mm/s, ≤ 2 mm per cable |

### 17 · What I deleted, and what I learned (I, dark)
**Claim: "My best decisions were deletions."**
- **Deleted:**
  - IMU;
  - yaw guard;
  - three of five fingers' worth of complexity (5 fingers → 2 jaws);
  - 50 mm of tube;
  - the housing block, replaced by an open frame (−600 g);
  - a contactor e-stop, replaced by the switched strip as the only stop.
- **Three lessons:**
  - measure before you trust a margin;
  - print the coupon before the part;
  - stall and steady-state are the design cases, not the average.
- **Half the time again:** buy pulleys and couplers sooner; build one station to test before four.

### Backups
- B1 four-bar jaw kinematics and the toggle near full open
- B2 control architecture (segments, leases, stop never disables)
- B3 Rev D station schematic + perfboard layout
- B4 floor-board attitude study numbers
- B5 thermal network details + fin FEA (after the study)
- B6 v7 open-frame gearbox (alternative, verified)
- B7 safety: power strip, studs only, nobody under, balance charging

## Evidence still needed from Jasper (priority)
1. Hold test: motor case, fin and PETG tab at 1.06 A, 60 min (slides 6, 7).
2. SolidWorks station study results (slide 10).
3. Photos: perfboard built, fin installed in the station (slides 7, 14).
4. Weighed claw parts and battery (slides 4, 11).
5. Readings and dates for the 1.14 V fault (slide 14).
6. Answers to the open questions in `DECISION_STORIES.md` §3.
