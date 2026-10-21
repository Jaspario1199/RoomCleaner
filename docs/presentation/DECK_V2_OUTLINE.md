# Deck v2: outline (Jasper's narrative, 2026-10-21)

Jasper's direction (10/21):
- More professional, less stylised. He talks through everything, so every slide is bullet points on its subject.
- The content is design principles, the choices made, and how everything works.
- Order: position vectors → first idea → why it failed (wiring) → controller per unit → real modularity (housing)
  → slide-in mount → self-calibration → plug-in power → cooling → bead homing and why it failed → new calibration
  → then the rest.

v1 (`docs/presentation/deck/`) is kept unchanged as history.

## Style (professional, plain)

- **Canvas:** 16:9, white content slides, navy section dividers. One accent colour (navy 1F3A5F); text charcoal
  1A1A1A; light grey F2F2F4 behind images.
- **Removed from v1:** the decision rail, evidence pills, fundamentals boxes and orange highlights.
- **Titles:** short topic names (2–6 words: "Position vectors", "First architecture: one central controller"),
  not sentences. A small section label above the title, in navy.
- **Body:**
  - 4–6 bullets of about 18 pt, sub-bullets 15–16 pt, left column ~55 %.
  - One image or diagram on the right ~40 %, with a one-line caption.
  - Equations as plain inline text in a bullet (e.g. "L_i = ‖a_i − p‖").
- **Fonts and footer:** Calibri everywhere (Arial fallback). Footer: "RoomCleaner | Jasper Buntinx" left, slide number
  right, 10 pt grey.
- **Never:** AI mentions, SpaceX names/logos, repo paths, file names, decision IDs.
- **Numbers:** only from `docs/presentation/FUNDAMENTALS.md` / `calculations/presentation_fundamentals.json`, the
  items below, or the cited verification files. Anything not tested is worded as "planned" or "calculated" inside
  the bullet text, not as a tag.
- **Speaker notes:** 2–4 lines per slide (the numbers to quote, one likely question), no paths.

## Slides

**1. Title.** RoomCleaner: a four-cable ceiling robot that picks laundry off the floor. Jasper Buntinx · Technical
presentation · Oct 27, 2026. Hero photo: gen-1 station lifting its test weight (photo 13).

**2. Goal and constraints.**
- Pick clothes off the floor and drop them in a hamper, from anywhere in the room.
- Room 11 × 9 ft, 9 ft ceiling; four winches near the ceiling corners hold one claw.
- Working load: a pair of jeans (0.9 kg) plus 2 m/s² of acceleration; first test load 1 lb.
- 3D-printed (PETG), hobby budget, parts I can buy and fix myself.
- Safety: anchors in studs, one hard stop (the switched power strip), nobody under the robot.

**3. Outline.** How a cable robot works · Architecture: from one box to modular stations · Homing and calibration ·
The claw · Electronics and software · Status and next steps.

### Section 1: How a cable robot works

**4. Position vectors.**
- Room frame at a floor corner; anchor (pulley exit) i at position vector a_i, claw at p.
- Cable vector l_i = a_i − p; cable length L_i = ‖a_i − p‖; direction u_i = l_i / L_i.
- To move the claw: for each point p(t) on the path, compute the four lengths L_i(t).
- The spool turns by Δθ_i = ΔL_i / r (r = spool radius including the wound line).
- Inverse kinematics is closed form, so no iteration is needed to command a move.
- Diagram: 3D room with four anchors, the claw and the four l_i arrows (new figure).

**5. Statics: why cable angle matters.**
- Force balance on the claw: Σ T_i u_i + m(g + a) = 0. Cables can only pull, so every T_i > 0.
- Centred claw, equal share: T = W / (4 sin φ), where φ is the cable's angle above horizontal.
- 1 lb + 0.45 kg claw: 32.1 N per cable 0.15 m below the anchors, 8.3 N at 0.6 m, 4.6 N at 1.2 m.
- Flat cables near the ceiling or a wall need large tension, so the robot keeps margins: 0.4 m below the anchors
  and 0.2 m from the walls.
- Chart: per-cable tension vs depth below the anchors, with the winch design force band (native chart; reuse the v1
  slide 4 data).

**6. The winch.**
- NEMA 17 stepper + printed spool + bearing pulley at the outlet, in each corner.
- Torque to pull: τ = T · r. A smaller spool radius gives more pull per amp, but more turns per metre.
- Spool v1 → v3: Ø20 → Ø15 core and a 16 mm drum; the bore was opened from Ø5.2 to Ø5.45 after the first print
  was too tight.
- Open-loop steps with an encoder watching for lost steps.
- Image: spool v1/v2/v3 renders.

### Section 2: Architecture: from one box to modular stations

**7. First idea: one central controller.**
- One Arduino Uno + CNC shield with four A4988 drivers in a single box.
- The computer sends moves; the shield steps all four motors from one clock, so sync is free.
- Each motor gets a long 4-wire cable from the box to its corner.
- It worked on the bench: a gen-1 station lifted a test weight (photo).
- Photo 14 (gen-1 shield) + photo 05 (gen-1 spool plate).

**8. Why it did not scale: the wiring.**
- I wanted more safety: a homing switch and an encoder at every winch, plus fault detection.
- Per corner that is motor 4 + switch 2 + encoder 4 = 10 conductors, not 4.
- The real cable routes are 6, 21, 23 and 32 ft (82 ft) → about 820 ft of conductor, against 164 ft for power only.
- The encoder's I²C bus is meant for centimetres, not 10 m runs, and motor phase currents in long cables add noise.
- Diagram: central box with four thick 10-wire bundles vs four stations on 2-wire power (new figure).

**9. Decision: a controller in every winch.**
- Each station has its own XIAO ESP32-C3 + A4988 driver + 5 V buck; only 12 V power travels (2 wires).
- The switch and encoder wires stay inside the station (a few cm).
- A host computer plans the path and sends each station timed segments over Wi-Fi; each station runs them on its own clock.
- Cost of the change: Wi-Fi timing. A 50 ms skew at 50 mm/s is 2.5 mm of cable mismatch, so segments are
  time-stamped and every station holds on a lost link.
- Benefit: about 5× less wire, and each station can be built and tested alone.

**10. Making the units truly modular.**
- Gen 1 was a plate screwed into the wall. That is fine for a bare motor.
- Now each corner carries a controller, driver, buck, switch and encoder: they need protection, a clean look and a
  place for heat to go.
- So each station became a housing: motor, spool, pulley and electronics in one unit.
- Photos: 04 (gen-2 station shells), 11 (gen-2 station assembled); render station_v3_assembly.

**11. Slide-in mount.**
- I take stations down often: to test, rework, repair or modify them.
- Drilling in and out every time damages the wall and moves the anchor point.
- A fixed wall frame is screwed into a stud once; the station housing slides in and locks.
- Pull it out, rework it, slide it back: the frame keeps the anchor position.
- Load case: the line pulls the station away from the wall (pull-out and prying). Design target: safety factor 3
  at 34 N; the SolidWorks static study is planned.
- Renders: wall_mount_v3 + slipin_v3.

**12. Self-calibration: set it up anywhere.**
- Every time stations go back up, the robot measures its own geometry. There is no tape measure and no user input
  to get wrong.
- The claw camera sees a printed floor board (a grid of tags) and reports the claw's pose.
- The robot moves through a set of poses and fits the anchor positions and cable lengths by least squares.
- So it works in any room shape the cables can reach, which is what makes it a consumer product.
- Image: floor board printout (render or photo) + a calibration-loop diagram (new figure: move → see board → fit →
  check → ready).

**13. Plug-in power.**
- Each station has one power cable: a 16 AWG pair from a fused supply. Nothing else plugs in.
- Plug in to use; unplug and store the cables when the robot is not needed; slide the stations off if wanted.
- Cut lengths 9, 24, 26 and 35 ft (94 ft of a 100 ft roll); a fuse per branch at the supply end.
- The motor stays wired inside the station, so a motor is never unplugged under power.
- The switched power strip is the one hard stop.

**14. Cooling.**
- In a sealed printed housing the motor's heat has nowhere to go; PETG next to the loaded motor mount softens and
  creeps.
- Fin efficiency: η = tanh(mL) / (mL) with m = √(2h / (k t)).
- Fix: an aluminium fin from the motor face up through the shell, plus vents.
- Calculated at 1.06 A, 23 °C: sealed 64 °C; vented with the fin about 41 °C.
- Built from 0.019 in sheet (fin efficiency 37 % vs 74 % for the 1/8 in drawn part); a 60-min hold test is planned.
- Photos 01/02 (milling), 15 (finished fin), 16 (fin on the motor).

### Section 3: Homing and calibration

**15. First plan: bead homing.**
- A bead on each cable trips a switch at the outlet, giving a known cable length, so the robot zeroes itself.
- I expected that to be enough to set up anywhere, maybe even without encoders.
- Detail fixed early: the switch moved below the pulley so the bead never rides over the pulley groove.
- Photo 09 (homing switch on the bench) + a small diagram of the bead and switch arm.

**16. The problem: beads limit the motion.**
- A bead cannot pass the outlet, so a cable can never be shorter than its homing length.
- To home all four at one point, each bead sits at that point's length, and then the claw can never move closer
  to any anchor than that.
- Homing at the room centre 1 m up leaves about 5 % of the working volume reachable; 2 m up, about 29 %. Calculated:
  0.2 m wall margin, 0.4 m ceiling margin.
- Second problem: vision alone knows cable length to ~20–25 mm, but a bead allows ~12 mm of overtravel, so a bead
  search was not safe.
- Figure: side view of the room with the reachable region shaded for a centre homing point (new figure).

**17. New calibration: camera + floor board + margins.**
- Startup: take up slack one cable at a time, lift, then look at the floor board from several poses.
- Least-squares fit of the anchor positions and cable zero lengths; a held-out pose checks the fit.
- Safety comes from margins, not precision: the robot stays 0.4 m below the anchors and 0.2 m inside the walls
  unless the error bars allow more.
- Beads stay as end-of-travel safety switches; encoders watch for lost steps.
- Simulated: the board makes calibration accepted reliably; not yet run on hardware.

**18. Why a floor board.**
- Angle error turns into position error through the lever arm: δx = σθ · L.
- One tag: 12.9 mrad × 0.51 m ≈ 6.6 mm per frame. Four tags in view: about 0.7 mm.
- The board is a printed grid at 250 mm pitch: cheap, and it can go in any room.
- Chart: tilt noise vs camera range, one tag vs board (reuse v1 backup B4 data).

### Section 4: The claw

**19. Claw evolution.**
- Five tendon-driven TPU fingers → a geared clamp → a lighter open frame → the final parallel-jaw gripper.
- Each step fixed a found problem: the first clamp's jaws could not pinch thin fabric; the v6 clamp was about 4.6× its mass budget; v7 cut the gearbox frame to 143 g.
- Images: gen1_tentacle_claw, claw_v6, gripper_v7, final gripper render (1021).

**20. Final gripper: gears and four-bar hands.**
- MG996R servo → 18T pinion → 36T/24T compound (2:1) → 24T sync gear, so the two jaws move as mirror images.
- Each hand joins a gear crank (53 mm) to a swing arm (50 mm): a near-parallelogram four-bar, so the jaws stay
  parallel within ~1°.
- 53 mm opening; the jaws close with a downward scoop of ~38 mm that lifts fabric off the floor.
- Gear strength checked with the Lewis equation: safety factor about 2 at servo stall.
- Image: renders/gripper1021/hands_on_mechanism_poses.png (open / mid / closed).

**21. Camera on the claw.**
- XIAO ESP32-S3 Sense camera in a bay built into the electronics housing, looking straight down the tube.
- It sees the grasp spot from about 17 cm above it; at contact the jaw hides it, so the final approach uses the last
  good view.
- The same camera reads the floor board for calibration.
- Image: claw_v6_camera_bay render (or a 1021 housing render).

**22. Weight vs lift: where it stands.**
- The A4988 boards top out at Vref 0.85 V → about 1.06 A per motor.
- Running pull is about 18–24 N per winch (full vs empty spool), so about 1.1 kg total lift at the worst point in
  the room.
- Claw plus jeans is above that today, so this is the open problem.
- Options: lighten the claw; a 3:1 winch reduction (~2.7× pull); a lighter demo load.
- Next step: a luggage-scale pull test on one station decides between them.

### Section 5: Electronics and software

**23. Station board.**
- The driver boots disabled (EN pull-up), so a reset never steps the motor.
- USB and the buck cannot back-feed each other (a link jumper plus a Schottky diode).
- 100 µF at the driver's motor supply; connectors for the motor, switch, encoder and 12 V.
- The KiCad schematic is generated from the soldered board's net list, so the two cannot disagree.
- Image: kicad_station_revD.png (or perfboard_layout.png).

**24. A motor that would not move.**
- The log said it was stepping; the shaft did not turn.
- The meter said the logic rail was at 1.14 V instead of 3.3 V: a bad connection.
- After the fix it moved. Since then: a meter checklist (VDD, SLEEP, ENABLE, buck output) before any code.
- Photos 07/08 (bench wiring), 12 (bring-up).

**25. Control software and phone app.**
- The host plans paths; the stations execute timed segments; a lost link means hold.
- Stop never disables: there is no brake, so faults and pause keep holding torque.
- Phone app: robot status, live claw camera, guided setup, and chat. Anything that moves the robot asks
  "yes" first.
- Image: the four app screenshots (docs/app_screenshots/01..04).

### Section 6: Status

**26. Status and next steps.**
- Built: stations, boards, fins, gripper parts. Designed and checked: hands, camera housing, calibration (simulated).
- Next tests, with pass limits written first:
  - winch pull test;
  - 60-min hold test (motor under 60 °C);
  - SolidWorks static and thermal studies;
  - first four-station lift: 1 lb, 300 mm at 50 mm/s, within 2 mm per cable.

**27. What I learned.**
- Measure before trusting a margin (the driver limit, the logic rail).
- Print the test coupon before the part (the spool bore).
- Design for the worst case: stall, the corner of the room, the hottest hour.
- Modularity paid for itself: every station can be pulled, fixed and put back.

**28. Questions.** Name, email.

### Backups

- **B1 Station schematic:** kicad_station_revD.png.
- **B2 Claw electrical:** kicad_claw_revB.png. One 2S pack, a 6 V servo rail and a 5 V logic rail.
- **B3 Gear strength:** Lewis SF table, reuse v1 B6.
- **B4 Thermal network:** reuse v1 B5.
- **B5 Statics worst case:** linear program, walls vs ceiling (reuse v1 slide 4 numbers).
- **B6 Safety:** one hard stop, studs, nobody under, charging rule.
