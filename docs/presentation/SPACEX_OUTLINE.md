# RoomCleaner — SpaceX panel presentation outline (v2)

**Panel:** Tue Oct 27, 11:00–12:00 CT, Bastrop · Mechanical Engineer, Insource
Manufacturing (Starlink) · 6 engineers
**Format:** ~15 slides, ~30 min of content inside 50 min with questions;
interactive like a design review. **Bring PPTX + PDF on the laptop desktop**
(no cloud). **Draft to Lushi Vatz and Cocona Nakamaru by Thu Oct 22.**

## The one-sentence story

> I took a ceiling cable robot from a full CAD design to working hardware one
> station at a time, and the biggest things I learned came from the places
> where measuring and testing overruled the CAD.

Every slide should support that sentence. The panel hires for
*concept → commissioning, failure analysis, and first-principles reasoning*,
and this role is manufacturing, so lean on fits, fixtures, print process,
inspection and bring-up, not on software.

## Rules for every slide (from the recruiter's prompt)

- One graphic per slide that you can defend line by line.
- Headline is a claim, not a topic ("Cable tension, not payload, limits the
  top of the workspace", not "Statics").
- Mark each result as **measured**, **calculated** or **planned**. Never
  present a planned number as a result.
- Spell out every acronym once (A4988 stepper driver, ESP32 microcontroller,
  FDM = fused deposition modeling, DFM = design for manufacturing).
- Say who did what. It is a solo project: say so, and name tools and purchased
  modules plainly (see slide 3).

## Time budget

| Block | Slides | Minutes |
|---|---|---|
| Who / what / why | 1–3 | 4 |
| First principles: statics, sizing, heat | 4–6 | 7.5 |
| Design decisions (mechanical + electrical) | 7–10 | 8.5 |
| Failure, debugging, verification, test plan | 11–13 | 6.5 |
| Results, lessons, close | 14–15 | 3.5 |
| **Total content** | | **30** |

---

## Slide-by-slide

### 1 · About me (1 min)
- **Headline:** Jasper Buntinx — mechanical engineering, Texas A&M; I build
  physical things end to end.
- **Graphic:** one real photo of you building (workshop, the metal sculptures,
  or EcoFil).
- **Say:** degree and expected graduation, EcoFil filament recycler (shredder,
  dehydrator, extruder), Austin Creek Show sculptures (fiber laser, welding),
  one hobby. Close with why a laundry robot.
- **Evidence to add:** graduation date; photo.

### 2 · The problem and what "done" means (1.5 min)
- **Headline:** A four-cable ceiling robot that finds laundry and drops it in a
  hamper. The first gate is a 1 lb test weight.
- **Graphic:** room sketch, 11 × 9 × 9 ft, four wall stations, cables to a
  central claw, hamper, camera.
- **Say:** why a cable robot (covers the whole floor, nothing on the floor,
  low moving mass); constraints (cheap parts, printed structure, removable
  stations, safe in a home).
- **Success criteria table:** gate 1 = one station repeatable; gate 2 = four
  stations hold and move 1 lb with no slack; gate 3 = pick and drop one
  garment. Say which gate you are at (between 1 and 2).

### 3 · Scope, ownership and timeline (1.5 min)
- **Headline:** Solo project, Aug → Oct 2026: two design generations.
- **Graphic:** timeline bar. Aug 6–Sep 2: gen 1 (parametric CAD, bench
  electronics proven on all 4 channels). Oct 7–19: gen 2 in SolidWorks (wall
  station v1→v3, spool v1→v3, clamp gripper V1→V5). Oct: one gen-2 station
  jog + homing switch on the bench.
- **Who did what (say it plainly):** you: requirements, SolidWorks redesign,
  wiring, soldering, bench bring-up and debugging, test plan, design decisions.
  Tools: an AI coding assistant for the control software, simulator,
  first-generation parametric CAD and verification scripts; purchased modules
  (NEMA 17 steppers, A4988 drivers, ESP32 boards, MG996R servo, camera). The
  panel will ask how you used AI tools; a direct answer ("I used it like a
  junior engineer whose work I checked; here is a defect I caught and one it
  caught for me") is strong. A vague answer is not.
- **Confirm:** project start date.

### 4 · First principles: cable statics (2.5 min)
- **Headline:** Cable tension, not payload, limits the top of the workspace.
- **Graphic:** free-body diagram of the claw with four cable unit vectors;
  plot of tension vs depth below the anchors.
- **Equations:** Σ Tᵢ·uᵢ + m·g = m·a, Tᵢ ≥ 0. Equal-share vertical case:
  T = W / Σ sin θᵢ.
- **Numbers (calculated, `calculations/gen2_screening.py`):** W = 1 lb + 0.45
  kg claw = 8.9 N. At 0.15 m below the anchors T = 32 N per cable; at 0.3 m,
  16 N; at 1.2 m, 4.6 N. The motor gives ~24 N of line force at the spool core (18 N at a full spool)
  → **software ceiling ≥ 0.4 m below the anchors**.
- **Say:** four cables for three translational DOF (degrees of freedom) is
  over-constrained; position control means length errors become tension.
  This sets up the electronics decision on slide 9.
- **Capacity anywhere in the room (calculated, `gen2_payload_limit.py`):**
  the total claw + load at 1.0 A is 1.0–2.3 lb, depending on how close to the
  anchors the claw may go. If one cable goes slack it is about 25 % less. The
  worst spot is high against the middle of a long wall. This is why the
  workspace ceiling is tension-aware, and why the claw's mass matters as much
  as the payload.
- **Likely question:** "What happens at a corner pick?" → far cables go
  near-horizontal and carry little; near cables take most of the load; the
  feasibility solver checks Tᵢ ≥ 0.5 N and ≤ 18 N.

### 5 · Motor and spool sizing (2.5 min)
- **Headline:** A shorter spool fits the shaft but changes the math every layer.
- **Graphic:** spool section (core radius, width, flange, shaft flat, set
  screw) + table of layers vs drum width.
- **Equations:** τ = T·r; F_available ≈ η·τ_motor(ω)/r; length/rev = 2πr.
- **Numbers (Spoolv3 measured: Ø15 core, 16 mm drum, Ø36 flanges):** the
  longest cable is 4.66 m (15.3 ft, far floor corner), and 20 ft is stored,
  leaving 1.4 m of margin. 20 ft of 0.5 mm line winds 5 layers, from 7.5 to
  10 mm radius, 8 mm inside the flanges. Line force drops from 24 N to 18 N,
  and length per rev changes by 15.7 mm, or 33 %. **Decision:** model radius vs wound length (or keep the working
  range on the base layers).
- **Measured to add:** pull force vs speed on one station (the outline's own
  ask). That plot is the strongest evidence you can bring.

### 6 · Heat, not torque, limits the winch (2.5 min)

- **Headline:** More current buys payload, but the heat ends up in printed
  plastic. A 50 g aluminium fin fixes it.
- **Graphic:** left, `docs/presentation/figures/motor_thermal.png` (motor case
  temperature vs current for open air, vented shell and sealed shell). Right,
  a section of the station showing two heat paths: motor → PETG tab (blocked,
  k ≈ 0.2 W/m·K) vs motor → aluminium fin → room air. Add the fin drawing
  (`solidworks/heat_plate/motor_heat_plate_drawing.png`) or a photo of it.
- **Equations:** F_line ∝ τ ∝ I · P = I²·R_phase · T_case ≈ T_room + P·R_th.
  Force goes up with I, heat with I². So +50 % current (1.0 → 1.5 A) gives
  +50 % payload and 2.25× the heat.
- **Numbers (calculated, `calculations/gen2_motor_thermal.py` + review R11):**

  | | 1.0 A | 1.5 A |
  |---|---|---|
  | Payload anywhere, 0.6 m ceiling limit | 1.51 lb | 2.27 lb |
  | Motor in sealed printed shell | ~67 °C | ~106 °C |
  | With 44 × 150 × 3 mm black aluminium fin | ~39 °C | ~51 °C |

  Limits: 60 °C for loaded printed parts; PETG softens at ~80 °C.
- **Say:**
  - **The insight.** In stagnant air, the motor can only conduct heat into
    the PETG it is bolted to. PETG barely conducts, so the plastic around the
    motor bolts climbs to almost motor temperature. That is exactly the joint
    carrying the cable load, so it creeps, the motor loosens, and the anchor
    drifts. It is slow and invisible in a short test. (Say plainly that this
    was your catch.)
  - **The decision.** Put an aluminium fin between the motor flange and the
    tab. It is a metal heat path out to room air, it runs vertical so warm
    air rises along it, it is painted black because emissivity roughly
    doubles heat loss, and it has thermal paste at the flange. It also
    carries the bolt load, so it fixes creep and heat in one part.
  - **Why vertical and motor-width.** It fits the station's footprint. A
    44 × 150 fin gives up only ~3 °C against a 100 × 100 plate, and past
    ~150 mm the tip is near room temperature (fin efficiency), so taller
    buys little.
  - **Alternatives considered.** A fan adds noise, power and a failure point.
    Lowering current costs payload. TMC2209 drivers cut current to ~60 %
    while holding (~65 % less heat at the same margin): the next step, not
    a replacement.
- **Evidence to add:** a 90-minute hold test at 1.0 A with and without the
  fin, logging motor case and PETG temperature every 10 min. Plot it over the
  model. Mark the fin as **planned** until it is built and tested.
- **Likely questions:** fin efficiency (why not taller); contact resistance
  (why paste, why not liquid metal: gallium attacks aluminium); why not
  copper (aluminium is cheaper and lighter, and its conductivity is enough at
  ~4 W); does holding current really need to stay on (yes, the motor
  back-drives without it; the detent torque is ~1–2 N·cm).

### 7 · Corner hardware, generation 1 → 2 (2 min)
- **Headline:** I moved from a screwed-down bracket to a removable station so
  calibration survives service.
- **Graphic:** side by side: gen-1 one-piece corner mount (motor + pulley +
  homing switch on one plate) vs gen-2 wall frame + slide-in housing + shell.
- **Say:** gen 1 put motor and pulley on one rigid plate so their alignment
  (fleet angle) was fixed by the print. Gen 2 keeps that but makes the
  assembly removable without touching the frame on the wall.
- **Load path:** line → pulley → housing → rails → frame → screws → stud.
  Show the slide direction relative to the line pull, and the positive
  retention feature. (Review R3: if the housing slides out in a direction the
  line pulls, the retention carries the full load.)

### 8 · Designed to be printed: fits, orientation, process (2 min)
- **Headline:** Every printed interface was chosen for how it prints and
  inspects, not just how it looks in CAD. *(This is the slide for this role.)*
- **Graphic:** fit-coupon photo (rail clearance, motor pilot Ø22.2, M3
  clearance Ø3.8 vs nominal 3.4) with measured insertion results; print
  orientation of the frame and housing.
- **Real example:** the v2 spool bore (Ø5.2) printed too tight on the 5 mm
  shaft, so v3 opened it to Ø5.45 (4.95 across the flat), with the set screw
  on the flat carrying the torque. Show the measured printed bore.
- **Say:** clearances tuned by coupon, not guesswork; PETG for parts under
  constant load (PLA creeps); orientation so rail loads run along layers;
  heat-set inserts where threads are reused; inspection datum for the slide.
- **Evidence to add:** a coupon print and caliper numbers, assembly time for
  one station.

### 9 · Electronics: central → distributed (2 min)
- **Headline:** Moving a controller to each winch removed four long harnesses
  and created my hardest open problem: synchronization.
- **Graphic:** before/after block diagram. Before: one Arduino + CNC shield,
  four long motor cables. After: per station XIAO ESP32 + A4988 + buck, one
  12 V pair each, Wi-Fi.
- **Say (honest trade):** a cable robot is over-constrained (slide 4), so
  50 ms of Wi-Fi skew at 50 mm/s is 2.5 mm of length error, roughly 8 N of
  unplanned tension on stiff line. Plan: time-stamped trajectories with
  synchronized clocks, or keep central step generation for the 1 lb demo.
  Safety rules: driver disabled until firmware is ready (EN pull-up), hold
  position on lost link, one kill switch for all stations.

### 10 · End effector: from five fingers to a geared clamp (2.5 min)
- **Headline:** I traded a compliant five-finger gripper for a two-jaw clamp I
  could build and test this month.
- **Graphic:** V5 section: MG996R → 18T pinion → 54T/24T compound → 24T
  follower; jaw pivots; camera housing on the extension.
- **Equations:** G = 54/18 = 3; τ_out ≈ η·G·τ_servo; θ_out = 180°/3 = 60°.
  Grip need: N ≥ W / (2μ) = 7.4 N per jaw at μ = 0.3; available ~21 N at a
  60 mm arm.
- **Say:** the 24/24 stage counter-rotates the second jaw so one servo drives
  a symmetric clamp. The camera on the claw helps the final approach, but
  keep the ceiling camera for finding laundry (review R7).
- **Gear strength (be ready):** Lewis σ = F_t/(b·m·Y). A module-1, 6 mm PETG
  pinion at servo stall is SF ≈ 0.4. Present what you changed (module ≥ 2,
  face ≥ 10 mm, or metal pinion, or torque-limited closing). **Only present it
  as fixed if it is.**

### 11 · Challenge: a motor that would not move (2.5 min)
- **Headline:** The log said it was stepping; the meter said otherwise.
- **Graphic:** annotated meter photos + the observation table.
- **Story:** command log showed pulses → EN toggled 3.3 → 0 → 3.3 V, so
  enable logic worked → measured driver logic rail ≈ 1.14 V → found a poor
  3.3 V connection → repaired → motor moved. Lesson: verify physical motion,
  not the command; measure supplies before blaming firmware.
- **Design change it caused:** crimped/soldered logic feed, VDD check in
  the bring-up procedure.
- **Evidence to add:** before/after numbers, short video.

### 12 · Verification caught a defect before I printed it (2 min)
- **Headline:** An independent check found the homing switch would never trip.
- **Graphic:** corner-mount rev C vs rev D: switch on a vertical face (roller
  5 mm off the line in X, 10.5 mm in Y) → switch on a horizontal pad (roller
  on the line, 3.75 mm overlap with a 5 mm bead).
- **Say:** moving the switch below the pulley was my idea, so the bead never
  rides over the pulley groove. The first implementation was wrong, and a
  geometric check against the real lever caught it in CAD, not in a print.
  Thorough example. Pair it with one scrappy example: beep-testing jumper
  caps instead of pulling them, or the duct-tape power splice on the bench.

### 13 · Test plan with pass/fail limits set in advance (2 min)
- **Graphic:** gate table.
  1. One station: jog repeatability, pull force vs speed, driver temperature,
     switch response.
  2. Station hardware: measured fits, retained slide under 3× line load,
     inspection after N cycles.
  3. Four stations, 1 lb: 300 mm move at 50 mm/s, no slack, ≤ 2 mm end error
     per cable, node reset under load → zero motion, Wi-Fi loss → holds.
  4. Laundry: attempts, successes, failure modes by garment type.
- **Say:** limits were written before testing.

### 14 · Results so far and the next gate (1.5 min)

- **Headline:** Hardware works one station at a time. Four-station motion is
  next.
- **Graphic:** evidence table: measured (gen-1: all 4 driver channels, 1 rev
  out/back each, Vref 0.80 V, switches fail-safe; gen-2: one station jog +
  homing), calculated (statics, spool, gears), not yet demonstrated (four
  stations, pickup).
- **Say:** no payload, accuracy or reliability rating is claimed yet.
- **Next gate:** four stations moving 1 lb repeatably, with the fault tests
  passing and the thermal test under 60 °C.
- **Photo:** latest hardware beside the evidence table.

### 15 · Decisions, lessons, and what I'd do in half the time (2 min)

- **Good:** proving the electronics on the bench before any printing; the
  removable station; setting a 1 lb gate instead of jumping to laundry;
  catching heat in the printed motor joint by analysis before building four
  stations, and fixing it with one part (the fin) that also carries the bolt
  load.
- **Poor:** designing the whole system (five-finger claw, every bracket)
  before one station worked; the spool was sized before I measured how far
  the shaft engages; I trusted a power brick's nominal 12 V until the meter
  read 18 V.
- **Half the time:** measure every purchased part first; freeze one station's
  interfaces; test that station to its limits; then copy it three times.
- **Takeaway sentence (write your own):** e.g. "Hardware tells you which
  assumptions were wrong; my job is to find out early and cheaply."

### Backups (only if asked)
- B1 Electrical: as-built station schematic (12 V, buck, XIAO, A4988, VMOT
  bulk capacitor 47–100 µF, EN pull-up, switch to GND with pull-up).
- B2 Gears: Lewis numbers table from the review (module/face vs SF).
- B3 Calibration: anchor measurement, camera mapping, bead homing, slack
  limits at startup.
- B5 Thermal network: motor case → (R_ma) → shell interior + PETG → (R_sa)
  → room, with 1.5 W of electronics inside; fin as a parallel path; all
  assumptions listed (`calculations/gen2_motor_thermal.py`).
- B4 Gen-1 corner mount stress check: ear root 5.5 MPa at 40 N (SF ≈ 5 vs
  PETG layer adhesion).

---

## Evidence to collect before Thursday (priority order)

| # | Item | Used on |
|---|---|---|
| 1 | Photos: bench station, gen-2 printed parts, gripper V5 render/section | 3, 7, 10, 14 |
| 2 | Meter photos / numbers from the 3.3 V fault | 11 |
| 3 | Pull-force-vs-speed test on one station (spring scale or luggage scale) | 5, 14 |
| 3b | 90-min thermal hold test at 1.0 A, with and without the fin (motor case + PETG temperature) | 6, 14 |
| 4 | Fit coupon + caliper readings | 8 |
| 5 | Decision on R1 (sync approach) and R5 (gear fix) | 9, 10 |
| 6 | Start date, graduation date, personal photo | 1, 3 |

## Questions to rehearse (answers in `verification/design_review_gen2.md`)

- Why four cables and not three? What does the fourth buy you, and cost you?
- How do you know each cable's length at startup?
- What happens if one node reboots mid-move? If Wi-Fi drops? If power is cut?
- What fails first on the gripper? Show the number.
- Why PETG? What about creep near the ceiling?
- Which load does the slide-in retention carry, and what is its margin?
- How did you set the clearances? What did the coupons measure?
- How did you use the AI assistant, and how did you check its work?
- If you had half the time, what would you cut?
- Why not just add a fan? Why not raise the current? How hot does the PETG
  around the motor bolts get?
