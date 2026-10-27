# Deck v9: the build, in the order it happened (outline, lead, 2026-10-26)

**Jasper's brief (10/26):** restructure as a **chronological build story**, for a **20-30 minute class or design-review
audience**, "heavier on the new photos". v8 (20 slides for a 10-minute panel) is kept unchanged.

**Build:** `docs/presentation/deck_v9/build_deck_v9.js`, started from `deck_v8/build_deck_v8.js` (same theme, helpers,
equation boxes, evidence tags, footer). Outputs `RoomCleaner_Buntinx_v9.pptx`, `.pdf`, `contact_sheet.png`.

**Rules that carry over:** every number from v8 / `FUNDAMENTALS.md` / `DECISION_STORIES.md`, unchanged unless this file
says so; evidence tags MEASURED / CALCULATED / SIMULATED / PLANNED; titles are claims; no tool names or repo paths on
slides; `[[...]]` for anything not in the record. Speaker notes: a 40-60 second talk track per slide, plus "If asked".

**Pace:** 25 main slides + 1 closing = about 1 minute each, 26 minutes, leaving time for questions. Photos are large
(half a slide or more); text stays at 3-4 statements.

**What is new since v8 (10/22 to 10/26), all in the record:**
- gears: 3:1 spur stage, 18T/54T, printed PETG pinion (D40-D42, 10/23), **next iteration, not fitted** (Jasper 10/27); the encoder magnet measured Ø4.0 (D43, 10/26);
- station Rev D electronics bench-tested on the ELEGOO ESP32 and the XIAO: driver off at boot, homing switch, encoder at
  0x36, one spool turn within 60 counts (10/25-10/26);
- claw Rev B electronics built and bench-tested: camera live view, battery 7.2 V read through the divider, servo moves (10/26);
  the servo needed its own hardware timer (the camera owned the first one), found on the bench;
- first station mounted on the wall (photos 32, 33); shells printed in blue and red PETG (34-37); the claw assembled (38, 40);
- over-the-air firmware updates so boxed stations never need a USB cable again (10/26);
- the phone app's Map tab (drawn obstacles) built and under independent verification (10/26): two findings being fixed,
  so it is PLANNED on the slide, not done.

## Slides

| # | Title (claim) | Visual | Text (3-4 statements) | Tag |
|---|---|---|---|---|
| 1 | **RoomCleaner: a four-cable ceiling robot that picks laundry off the floor** | photo 42 (claw hanging from three cables, 10/27; was photo 38) full-bleed right | name, Mechanical Engineering, Texas A&M; "built July to October 2026" | |
| 2 | **About me** | v8 About Me collage (unchanged) | unchanged from v8 | |
| 3 | **The goal: jeans from anywhere on the floor into the hamper, nobody touching it** | v8 room elevation (anchors 0.15 m below the 2.74 m ceiling, margins) | payload 0.9 kg + 2 m/s²; four winches in the studs; PAUSE holds, the switched strip is the emergency stop and drops the claw; I approve each move on the phone | |
| 4 | **Five phases in fourteen weeks** | v8 Gantt (Concept Jul 16-Aug 5, Gen 1 Aug 6-Sep 2, Redesign Sep 3-Oct 6, Final design Oct 7-21, Build and test Oct 22-27) | "mine: requirements, decisions, SolidWorks, printing, machining, wiring, bring-up; with Claude Code under my direction: control software, calculations, CAD checks; purchased: steppers, drivers, boards, servo, camera, battery, encoders" | |
| **Act 1: Concept (July)** | | | | |
| 5 | **Why a cable robot: four winches cover the whole floor with nothing in the room** | v8 cable sketch + the floor/gantry/cable table | chosen: four ceiling winches, one claw; cost: cables only pull, so tension sets the working space | |
| 6 | **The first physics: cable tension climbs toward the ceiling** | v8 tension-vs-depth chart (0.60 kg claw) | 1 lb test at 0.4 m: 14.3 N static, 17.2 N with 2 m/s²; limit 16.8 N; jeans must stay 0.6 m below the anchors | CALCULATED |
| 7 | **July's choices, and what each one cost later** | three cards | NEMA 17 steppers (cheap, one shield drives four; no brake, holds only while powered, runs hot); five tendon fingers (CAD only, 419 g of 450 g, never built); the power strip as the kill switch (guaranteed stop, drops the claw) | |
| **Act 2: Generation 1 (August)** | | | | |
| 8 | **Generation 1: one Uno, one shield, four corner mounts** | photos 05 (gen-1 plate), 13 (station lifting a test weight) | a printed corner plate screwed into a joist replaced hanging hooks (a hook is a pivot: ~1:1 anchor error to position error); bench: the station lifted a test weight and the cable math held | MEASURED (lift) |
| 9 | **Bench week found what the drawings could not** | photo 13 or bench photos from the v8 Gen-1 slide | 18 V on the meter from a supply labelled 12 V; a homing switch that would have zeroed without moving (NC wiring, inverted logic); a switch that had to move below the pulley | MEASURED |
| 10 | **Why Gen 1 could not be the final design** | v8 bead-homing chart (reachable share vs homing height) | bead homing left 5-29 % of the room reachable; one central board would need 10 wires to every corner, 250 m (820 ft) of wire; a central board skews 2.5 mm per 50 ms | CALCULATED |
| **Act 3: Redesign (September to early October)** | | | | |
| 11 | **The clamp that could not close on thin cloth (Sep 30)** | v8 claw-versions figure (fingers, v6 clamp, four-bar) | rack-and-pinion jaws could not pinch thin fabric; v6 clamp came out at 4.6× its mass budget in CAD (Oct 20); lesson: mass tracked through every version from now on | CAD |
| 12 | **One plug per station: the station lifts off while the anchor stays in the stud** | v8 Final Wall Station render + photo 24 | slide-in wall mount; load path cable → spool → set screw → motor → tab → mount → screws → stud; the motor is the weakest link: it slips at 34-59 N before anything breaks | CALCULATED |
| 13 | **The drive slips before the wall does: a designed fuse** (added 10/27, Jasper's story) | v8 weakest-link chart (cable tension at which each part gives, one station at 1.5 A) | four cables can pull against each other; the motor's rotor skips at 34-59 N, the designed fuse, below every other link (wall screws in a stud 9×, dovetails 225×); the spool encoder sees the spool fall behind the commanded steps: TRACKING fault, stations hold; the same catches an overweight pickup; the as-drawn printed set screw (22-64 N) moves into a metal insert | CALCULATED |
| 14 | **One controller per winch** | v8 "One Controller per Winch" photos + table | Gen 1's central box worked in about a day and a half but had to go (wire, skew, storage, no modularity); a board in each station on one 12 V pair: 50 m of wire instead of 250 m; each station is built and tested on its own; timing moves into software | |
| 15 | **The claw camera replaces bead homing** | v8 camera-calibration content | the claw reads a printed floor board and fits anchors and cable lengths; whole room reachable; camera pose best case 0.7 mm per frame; cable lengths after the fit about 12-16 mm (simulated) | SIMULATED |
| **Act 4: Final design (October 7-21)** | | | | |
| 16 | **Heat: a sealed PETG box would cook its own motor mount** | v8 Motor Cooling chart + fin table | 1.5 A = 4.05 W; vented shell + fin: 56-59 °C with the 0.019 in prototype fin, 45-49 °C with 1/8 in; the thin sheet stops gaining at 136 mm | CALCULATED |
| 17 | **Winch pull and what the four winches can lift** | v8 winch-pull chart + weight-budget bars | 34 N on an empty spool at 1.5 A, 25 N full; claw with battery weighed 0.60 kg (0.86 estimated); jeans 1.50 kg against 1.56 kg capacity, a 4 % margin, inside the uncertainty; the pull test decides | MEASURED / CALCULATED |
| 18 | **The claw: geared four-bar hands, camera bay, one 2S pack** | photo 25 (assembled claw 10/22) + photo 40 (housing open) | hands stay within 1° of parallel over 53 mm; grip 13.3-25 N per jaw vs 17.7 N for jeans; 7.4 V pack, UBEC 6 V for the servo, buck 5 V for the board, 200k/100k battery sense | CALCULATED |
| **Act 5: Build and bring-up (October 22-26)** | | | | |
| 19 | **Printing and machining: fits came from coupons, not guesses** | photo 26 (slicer) + v8 fits/datums snapshots (dovetail, gear lip, insert pocket) + photo 35 (failed layer kept) | spool bore Ø5.2 printed too tight, opened to Ø5.45; fin holes drilled in one setup; one shell kept a failed layer: it is a shell, not a load path | MEASURED |
| 20 | **Station electronics on the bench: every check before the motor turns** | photos 29, 37 (ELEGOO bench, red shell with fuse), 31 (XIAO breadboard) | driver off at boot; homing switch LOW at rest, HIGH pressed or broken; encoder at 0x36; one spool turn within 60 counts: PASS on both boards; a short found by the LED going out, traced to the switch pull-up | MEASURED |
| 21 | **Claw electronics on the bench: camera, battery, servo** | photo 40 (housing lit) + a camera-page screenshot `[[Jasper: screenshot of the live view]]` | live video on the phone; battery 7.2 V through the divider, matching the meter; the servo only moved after it got its own hardware timer (the camera owned the first one) | MEASURED |
| 22 | **On the wall** | photos 32, 33 (mounted station), 34/36 (shell vents and fin tab) | first station in a stud on the TV wall, 12 V down the wall, fin out the top; boxed stations boot and join Wi-Fi on their own, firmware updates over Wi-Fi, motor off until the phone arms it | |
| 23 | **Three stations first: the triangle, the tilt, and no spare cable** | three-station room diagram (from `docs/THREE_STATION_MODE.md` §2, drawn) | A, B in two corners, C mid-wall opposite; claw on three corner holes hangs 5.5° (limit 8°); grips refused over 78 % of the floor until the three-hole housing (0.8°); a station fault drops the claw, so the floor is padded | SIMULATED |
| 24 | **What hurts now, and the next iteration** (added 10/27; replaces the gear-stage slide) | three cards + `[[Jasper: photos or CAD of the next iteration]]` box | 3:1 printed gear stage (18T/54T, PETG pinion; designed, CAD-verified, pinion printed, not fitted; slip fuse moves to ~130 N); 1° draft on the slide-in dovetail so it does not bind; lighter back mount (holds ~200× the motor's pull, 597 cm³ → ~200 cm³) for open-source builders | CAD / PLANNED |
| 25 | **Results against targets, and what is still planned** | v8 results table, updated: Wiring = Built (bench PASS); add rows "Station bench test: PASS both boards (MEASURED)", "Claw bench test: PASS (MEASURED)", "Map of obstacles in the app: built, under verification (PLANNED)", "First three-station lift: PLANNED" | | mixed |
| 26 | **What I would do first next time, and what happens next** | v8 Good/Poor decisions condensed to 3 + 3, and next steps | good: one controller per winch; camera calibration; mass budget per part. Poor: mass not tracked through four claw versions; scrap-sheet fin; build week ending on presentation day. Next: flash and commission the three stations, pull test at 1.5 A, first lift, then the robot scans its own room | |

**Appendix (behind a divider, kept from v8):** fundamentals, safe state and failure modes, the manufacturing fits table,
the Rev D station schematic, the claw Rev B schematic, the station breadboard layout.

## Notes for the builder

- Photos: `docs/presentation/photos/NN_*.jpg` (README has the captions and dates); use the `imgSize` helper for aspect.
- Keep the v8 figures where the slide says "v8"; only the text changes. Charts in `deck_v8/fig` and `deck_v3/fig`.
- Slide 24 diagram: draw it in pptxgenjs (rectangles, three dots A/B/C, the triangle, the start point) from the numbers in
  `docs/THREE_STATION_MODE.md` section 2; no new dependency.
- Slide 22: the live-view screenshot is a `[[...]]` placeholder box unless `docs/app_screenshots/` has one.
- Footer: "Act N of 5: <name>" as v8 did with phases.
- Validate the pptx with the pptx skill's validate script; render the contact sheet; LibreOffice via the skill's soffice.py.

## Update 10/27 (Jasper's stories folded in)

New slide 13 "The drive slips before the wall does: a designed fuse" (the weakest-link chart; slides after it move up one).
Title photo is now 42 (the claw hanging from three cables in the room corner); the title notes carry the 30-second pitch. Slide 14
opens with Gen 1's central box (worked in about a day and a half; wire, skew, storage, modularity). Slide 18 states the encoder's two
jobs. Slide 26 adds the pole-clamp wall mount and the open-source release. Photos 43 (bench overview) on slide 21, 45 and 46 (wall
mount alone, with XT60) on slide 12, 44 (station from below, line down) on slide 23 replacing 33. Numbers unchanged from the record.

## Update 10/27 (correction, Jasper): the 3:1 gear stage is the next iteration

The mounted stations are direct-drive spools on the motor shaft. The gear-stage slide (old 18) is removed from Act 4; the encoder's
two jobs moved to the station-bench slide (20); a new slide 24 "What hurts now, and the next iteration" sits in Act 5 before the
results (gear stage, 1° draft on the slide-in dovetail, lighter back mount; placeholder box for Jasper's photos). Still 26 main slides.
Slides 19-24 of the 10/27 morning numbering are now 18-23.

## v9.1 (10/27): limits strip, one-line results, requirement origins

Slide 24 gains a "Limits today" strip (relative positioning only; three-station corner-hole tilt 5.5°/8°, grips refused on 78 % of the
floor, 0.8° with the three-hole housing; no person or pet detection). Slide 25 opens with one statement: 1.56 kg lift (calculated,
direct drive at 1.5 A), cable lengths to about 12–16 mm after calibration (simulated), $210.78 of parts in the robot for three
stations plus $37.74 of filament. Slide 3's four requirements each carry a grey origin line (room as reported; 0.9 kg screening value,
CR6; 2 m/s² and the 450 g claw budget assumed, R1/R7; 40 N per cable the motor limit, R17; studs from D13; stop rule D21; 1 lb gate D19).

## v9.2 (10/27): the architecture story first (Jasper's account, `DESIGN_INTENT_20261027.md`)

The early story is the system around the claw, not the gripper. Slide 7's gripper card becomes "Iteration 1 architecture: one central
unit" (Uno + shield driving four corner motors over wires to each corner; overhead ceiling camera). The clamp slide (old 11) is removed
from Act 3; slides 11-17 move up one; a new slide 18 sits next to the claw in Act 4. Still 26 main slides.

| # | Title (claim) | Visual | Text (3-4 statements) | Tag |
|---|---|---|---|---|
| 7 | **July's choices, and what each one cost later** | three cards | NEMA 17 steppers; **one central unit** (Uno + shield, wires to each corner, overhead camera; cost: everything wired back to one place, 250 m once each corner had a switch and an encoder); the power strip | |
| 10 | **A motor on a wall needs a switch and an encoder** | v8 bead-homing chart (secondary) | things go wrong (camera, overwind, tension, stall) so each winch gets a switch and a spool encoder; the encoder measures discrepancies while testing, data first; one central box over thin wire then fails: 10 conductors per corner, 250 m, 0.82 V lost on the 32 ft run (18 AWG, 2 A, calculated), 2.5 mm skew per 50 ms; bead homing capped the room 5-29 % | CALCULATED |
| 13 | **Iteration 2: a box with its own brain, and only power going in** | photos 14 (central board), 33 (box on the wall) + the Gen 1 vs Final table | ESP32 in each box, one thicker 12 V pair (50 m, 0.51 V drop calculated); any position and orientation; slides off and unplugs for guests or storage, one plug and it joins Wi-Fi; a product, not a tangle; the mount is separate (pole clamp later) | |
| 17 | **The claw: geared four-bar hands, camera bay, one 2S pack** | unchanged | described as it is today | CALCULATED |
| 18 | **The gripper is a modular attachment, on purpose** | claw_v6 render, gripper1021_head render, photo 22 (small) | attaches modularly at the tube, a test bed for shirts; a hard pinch was expected to be better, testing showed alignment problems (the Sep 30 rack-and-pinion 2 mm gap); TPU and other pad materials being tried (μ 0.6 vs 0.3 halves the force jeans need); the v6 clamp at 4.6× its mass budget is why mass is tracked per part | MEASURED (pinch test, Jasper; no reading logged) / CAD |
| 26 | **What I would do first next time** | unchanged | poor decision reworded: "mass not tracked per part until Oct 20" | |

Not supported by the record and therefore worded carefully: the 0.51 V drop is calculated, not measured (the slide says so); the
pinch-test result is Jasper's account plus the geometry audit's 2 mm gap, no cloth-test reading is logged (said in the notes).
