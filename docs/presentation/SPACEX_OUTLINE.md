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
| First principles | 4–5 | 6 |
| Design decisions (mechanical + electrical) | 6–9 | 9 |
| Failure, debugging, verification | 10–12 | 7 |
| Results, lessons, close | 13–15 | 4 |
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

### 4 · First principles: cable statics (3 min)
- **Headline:** Cable tension, not payload, limits the top of the workspace.
- **Graphic:** free-body diagram of the claw with four cable unit vectors;
  plot of tension vs depth below the anchors.
- **Equations:** Σ Tᵢ·uᵢ + m·g = m·a, Tᵢ ≥ 0. Equal-share vertical case:
  T = W / Σ sin θᵢ.
- **Numbers (calculated, `calculations/gen2_screening.py`):** W = 1 lb + 0.45
  kg claw = 8.9 N. At 0.15 m below the anchors T = 32 N per cable; at 0.3 m,
  16 N; at 1.2 m, 4.6 N. The motor gives ~18 N of line force at the spool core
  → **software ceiling ≥ 0.4 m below the anchors**.
- **Say:** four cables for three translational DOF (degrees of freedom) is
  over-constrained; position control means length errors become tension.
  This sets up the electronics decision on slide 8.
- **Likely question:** "What happens at a corner pick?" → far cables go
  near-horizontal and carry little; near cables take most of the load; the
  feasibility solver checks Tᵢ ≥ 0.5 N and ≤ 18 N.

### 5 · Motor and spool sizing (3 min)
- **Headline:** A shorter spool fits the shaft but changes the math every layer.
- **Graphic:** spool section (core radius, width, flange, shaft flat, set
  screw) + table of layers vs drum width.
- **Equations:** τ = T·r; F_available ≈ η·τ_motor(ω)/r; length/rev = 2πr.
- **Numbers:** longest cable 4.66 m (15.3 ft, far floor corner) vs 20 ft
  stored → 1.4 m margin. 0.5 mm line on a 10 mm core: 3–6 layers depending on
  width; radius grows 1.5–3 mm → force drops 13–23 %, length per rev changes
  9–19 mm. **Decision:** model radius vs wound length (or keep the working
  range on the base layers).
- **Measured to add:** pull force vs speed on one station (the outline's own
  ask). That plot is the strongest evidence you can bring.

### 6 · Corner hardware, generation 1 → 2 (2.5 min)
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

### 7 · Designed to be printed: fits, orientation, process (2 min)
- **Headline:** Every printed interface was chosen for how it prints and
  inspects, not just how it looks in CAD. *(This is the slide for this role.)*
- **Graphic:** fit-coupon photo (rail clearance, motor pilot Ø22.2, M3
  clearance Ø3.8 vs nominal 3.4) with measured insertion results; print
  orientation of the frame and housing.
- **Say:** clearances tuned by coupon, not guesswork; PETG for parts under
  constant load (PLA creeps); orientation so rail loads run along layers;
  heat-set inserts where threads are reused; inspection datum for the slide.
- **Evidence to add:** a coupon print and caliper numbers, assembly time for
  one station.

### 8 · Electronics: central → distributed (2 min)
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

### 9 · End effector: from five fingers to a geared clamp (2.5 min)
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

### 10 · Challenge: a motor that would not move (3 min)
- **Headline:** The log said it was stepping; the meter said otherwise.
- **Graphic:** annotated meter photos + the observation table.
- **Story:** command log showed pulses → EN toggled 3.3 → 0 → 3.3 V, so
  enable logic worked → measured driver logic rail ≈ 1.14 V → found a poor
  3.3 V connection → repaired → motor moved. Lesson: verify physical motion,
  not the command; measure supplies before blaming firmware.
- **Design change it caused:** crimped/soldered logic feed, VDD check in
  the bring-up procedure.
- **Evidence to add:** before/after numbers, short video.

### 11 · Verification caught a defect before I printed it (2 min)
- **Headline:** An independent check found the homing switch would never trip.
- **Graphic:** corner-mount rev C vs rev D: switch on a vertical face (roller
  5 mm off the line in X, 10.5 mm in Y) → switch on a horizontal pad (roller
  on the line, 3.75 mm overlap with a 5 mm bead).
- **Say:** moving the switch below the pulley was my idea, so the bead never
  rides over the pulley groove. The first implementation was wrong, and a
  geometric check against the real lever caught it in CAD, not in a print.
  Thorough example. Pair it with one scrappy example: beep-testing jumper
  caps instead of pulling them, or the duct-tape power splice on the bench.

### 12 · Test plan with pass/fail limits set in advance (2 min)
- **Graphic:** gate table.
  1. One station: jog repeatability, pull force vs speed, driver temperature,
     switch response.
  2. Station hardware: measured fits, retained slide under 3× line load,
     inspection after N cycles.
  3. Four stations, 1 lb: 300 mm move at 50 mm/s, no slack, ≤ 2 mm end error
     per cable, node reset under load → zero motion, Wi-Fi loss → holds.
  4. Laundry: attempts, successes, failure modes by garment type.
- **Say:** limits were written before testing.

### 13 · Results so far, and what is not proven (1.5 min)
- **Headline:** Hardware works one station at a time. Four-station motion is
  next.
- **Graphic:** evidence table: measured (gen-1: all 4 driver channels, 1 rev
  out/back each, Vref 0.80 V, switches fail-safe; gen-2: one station jog +
  homing), calculated (statics, spool, gears), not yet demonstrated (four
  stations, pickup).
- **Say:** no payload, accuracy or reliability rating is claimed yet.

### 14 · Decisions: good, poor, and half the time (1.5 min)
- **Good:** proving the electronics on the bench before any printing; the
  removable station; setting a 1 lb gate instead of jumping to laundry.
- **Poor:** designing the whole system (five-finger claw, every bracket)
  before one station worked; the spool was sized before I measured how far
  the shaft engages; I trusted a power brick's nominal 12 V until the meter
  read 18 V.
- **Half the time:** measure every purchased part first; freeze one station's
  interfaces; test that station to its limits; then copy it three times.

### 15 · Close (0.5 min)
- **Headline:** Next gate: four stations moving 1 lb repeatably, with fault
  tests passing.
- **Graphic:** latest hardware photo.
- **Takeaway sentence (write your own):** e.g. "Hardware tells you which
  assumptions were wrong; my job is to find out early and cheaply."

### Backups (only if asked)
- B1 Electrical: as-built station schematic (12 V, buck, XIAO, A4988, VMOT
  bulk capacitor 47–100 µF, EN pull-up, switch to GND with pull-up).
- B2 Gears: Lewis numbers table from the review (module/face vs SF).
- B3 Calibration: anchor measurement, camera mapping, bead homing, slack
  limits at startup.
- B4 Gen-1 corner mount stress check: ear root 5.5 MPa at 40 N (SF ≈ 5 vs
  PETG layer adhesion).

---

## Evidence to collect before Thursday (priority order)

| # | Item | Used on |
|---|---|---|
| 1 | Photos: bench station, gen-2 printed parts, gripper V5 render/section | 3, 6, 9, 13, 15 |
| 2 | Meter photos / numbers from the 3.3 V fault | 10 |
| 3 | Pull-force-vs-speed test on one station (spring scale or luggage scale) | 5, 13 |
| 4 | Fit coupon + caliper readings | 7 |
| 5 | Decision on R1 (sync approach) and R5 (gear fix) | 8, 9 |
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
