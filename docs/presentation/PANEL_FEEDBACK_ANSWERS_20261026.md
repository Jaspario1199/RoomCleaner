# Panel feedback on deck v8 (SpaceX engineers, 10/26): answers from the record

Prepared 2026-10-26 from the repository record only. Each item gives the v8 slide the panel named, the matching v9 slide
(`docs/presentation/deck_v9/`, outline `DECK_V9_NOTES.md`; numbers as of 10/27 evening: slide 13 "The drive slips before the wall does" added, the gear-stage slide removed, slide 24 "What hurts now, and the next iteration" added), an answer a presenter can say, the evidence tag and the source
file, and where it went: **On slide** (a one-line statement on the v9 slide), **In notes** (the v9 "If asked" speaker notes),
or **Question for Jasper** (the record does not hold the answer; a `[[Jasper: ...]]` placeholder sits in the notes).

Evidence tags: MEASURED (an instrument reading exists), CALCULATED (worked from stated inputs), SIMULATED (a model ran),
PLANNED (a test is defined, no result), CAD (measured on a CAD solid). "NOT IN THE RECORD" means exactly that; nothing below
is invented.

| v8 slide | v9 slide | Item | Placement |
|---|---|---|---|
| 5 Timeline and Scope | 4 Five phases in fifteen weeks | Self-imposed budget and schedule limits | On slide + In notes (hours and mentors: Question for Jasper) |
| 7 Design Trade-offs | 7 July's choices (notes); 12 and 16 (margins, heat) | The idea behind each trade | In notes; "how to read the margins" On slide 12 |
| 8 Cable Tension | 6 The first physics | Layout offset to a corner | In notes |
| 9 Gen 1 | 8 Generation 1; 10 Why Gen 1 could not be final | What bead homing is | On slide 10 + In notes 8 and 10 |
| 10 One Controller per Winch | 14 One controller per winch | What happens when the motors lose power | On slide (table row) + In notes |
| 11 Camera Calibration | 10 (chart) and 15 The claw camera replaces bead homing | Floor area vs volume | On slide 10 (computed) + In notes 10 and 15 |
| 12 Claw | 18 The claw | Where the 0.3 friction coefficient came from | In notes: assumed, source named; Question for Jasper |
| 13 Final Wall Station | 16 Heat (fin); 12 One plug per station, 13 the designed fuse | What the fin does | On slide 16 + In notes |
| 14 Winch Pull | 17 Winch pull and what the four winches can lift | How the pull value was validated | In notes (it is not validated: PLANNED) |
| 15 Motor Cooling | 16 Heat | Why the 6061 is painted | In notes (model side) + Question for Jasper (the built fin) |
| 16 Weight Budget | 17 (same slide) | Where the ~25 % mass reduction came from | In notes + Question for Jasper |
| 17 Build | 20 Station electronics on the bench | How the 3.3 V fault was found; steps when the motor would not turn | In notes (recorded steps) + Question for Jasper |
| 18 Manufacturing fits | Appendix: Manufacturing fits and datums | Which feature each fit belongs to | In notes |
| 20 Results | 25 Results against targets | What narrow grabs are | On slide (table row) + In notes |
| 21 Decisions | 26 What I would do first next time | How the weaker decisions affected the deliverable | In notes |
| 22 Takeaways | 26 (same slide) | Why larger motors were not the answer | In notes |

---

## v8 slide 5, Timeline and Scope → v9 slide 4: self-imposed budget and schedule limits

**Answer.** "I set four limits on myself. Money: a hobby budget; the 10/26 breakdown puts everything ordered at about $640,
of which $220 (three stations) to $260 (four) is in the robot as parts and another $40 to $50 as filament; the rest is pack
remainders, spares and two tools. Time: fifteen weeks ending on the presentation date, so the build-and-test week ends on the
day I present. Mass: a 450 g claw, because every gram on the claw is a gram of payload. Heat: 60 °C for any loaded printed
part. Those limits picked the hardware: NEMA 17 steppers at $33 for five instead of self-locking worm-gear motors at $32
each, an A4988 kit chosen by what was in stock, printed parts everywhere except the pulleys, a prototype fin cut from sheet I
already had, and a 1 lb test weight before any jeans."

- Numbers: $637.47 ordered (recorded $289.47 + estimated $348.00), $220.38 / $259.84 in the robot, $38.70 / $50.40 filament
  (COST_BREAKDOWN, prices partly recorded, partly typical Amazon prices: say "about"). 450 g claw budget (REQUIREMENTS R7).
  60 °C PETG limit (D37, D38). Jul 16 to Oct 27 (v8 Gantt). 1 lb first (D19).
- Evidence: receipts and recorded prices for the "recorded" lines; the rest estimated. Sources: `docs/COST_BREAKDOWN_20261026.md`,
  `DECISIONS.md` D19, D37, D38, `docs/presentation/DECISION_STORIES.md` T01, T02, T31, `verification/deck_factcheck.md` F26.
- **Question for Jasper:** hours spent, shop access or mentors, and whether a dollar ceiling was ever set in advance (the record
  only says "hobby budget"). The v9 notes keep the `[[hours spent, total cost, shop access or mentors]]` placeholder.
- Placement: **On slide 4** (one statement) and **In notes**.

## v8 slide 7, Design Trade-offs → v9 slide 7 (notes), 12 and 16: the idea behind each trade

**Why heat matters (motor current up).** "Line pull rises with current, but the heat in the coils rises with current
squared: P = I²R, 2.0 W at 1.06 A and 4.05 W at 1.5 A with the assumed 1.8 Ω phase. The motor is bolted to a printed PETG
tab that carries the whole cable load, and PETG conducts about 1/800 as well as aluminium, so the tab climbs toward the motor
temperature. Above about 60 °C loaded PETG creeps; the motor loosens and the anchor drifts, and anchor error becomes claw
position error about one to one." CALCULATED. Sources: `docs/presentation/FUNDAMENTALS.md` §3,
`calculations/fin_sizing_4w.md`, `DECISION_STORIES.md` T31, D13.

**What failure the stronger claw was built for (gear teeth).** "Yes, the gear teeth. A clamp does not stop at a position; it
stops when the servo stalls, so every grip loads the teeth with the full stall torque. The first screening, module 1 with a
6 mm face, gave a Lewis bending safety factor of 0.35 at 6 V stall: the teeth shear. The built train is module 1.5 with
16 mm and 20 mm faces, safety factor 2.05 on the pinion at 6 V, against a PETG allowable of 22.5 MPa, half the tensile
strength, to cover layer adhesion and fatigue. The cost of the stronger train is mass, and the claw came in at 0.60 kg
against a 0.45 kg budget." CALCULATED; no printed gear has been stalled. Sources: `FUNDAMENTALS.md` §4,
`verification/design_review_gen2.md` R5.

**How longer wires increase voltage drop.** "The supply sits in one corner on a stand, so the longest 12 V branch is 32 ft
one way, 64 ft of loop. Drop is current times loop resistance, R = ρ·2L/A: at 2 A, 0.82 V on 18 AWG and 0.51 V on 16 AWG,
7 % against 4 % of 12 V, and more when the wire runs warm near the ceiling. The station buck accepts down to 4.5 V so the
drop is not fatal, but it is wasted heat in the wall and less margin, so 16 AWG went in." CALCULATED (2 A is an illustrative
current; branch current not measured). Sources: `FUNDAMENTALS.md` §10, `docs/POWER_WIRE_SELECTION_20261014.md`,
`DECISION_STORIES.md` T28.

**How to read the safety margins.** "Three margins appear and they mean different things. The 1.5 on the winch pull is a
skip margin: the design force is the running pull divided by 1.5 so a snag does not skip steps. The 1.5 in the weakest-link
table is a ratio of the cable tension at which a part gives to the most the motor can pull before it slips, 59 N; at or
above 1.5 the motor is guaranteed to give first, 1.0 to 1.5 is marginal, below 1.0 the part fails before the motor. The gear
and structural SFs are allowable stress over calculated stress, with printed PETG allowed only half its tensile strength and
derated a further 15 % when warm. All of them are CALCULATED against assumed allowables; none is a tested margin." Sources:
`calculations/lift_chain_weakest_link.md`, `calculations/winch_gear3.md`, `FUNDAMENTALS.md` §2 and §4, D39.

- Placement: **In notes** on v9 slide 7; the margin rule **On slide 12** (one statement) and in its notes; heat on slide 15.

## v8 slide 8, Cable Tension → v9 slide 6: a layout offset to a corner of the room

**Answer.** "Cables only pull, so the claw can only hang where the horizontal pulls cancel: its floor position has to stay
inside the polygon under the anchors. A layout pushed into one corner of a room does not make the rest of the room harder,
it makes it unreachable, and the floor it does cover shrinks further by the tension-floor margin at each edge. Near an edge
the far cable goes slack and the near ones run flat, so the largest tension per unit of weight climbs from 1.10 at task height
to 2.42 at the 0.4 m ceiling line in the worst spot, the middle of a long wall. The three-station layout is the measured
example of an offset: anchors A and B in two corners and C mid-wall span a triangle of 47 % of the floor, and after a
0.23 to 0.31 m edge margin only 20 to 27 % of the floor is usable, with the start point 0.44 m off the room centre. For
four stations the same statics says: put the anchors in the corners, as high and as symmetric as the studs allow." CALCULATED
(linear-program statics and the three-cable solve); nothing measured on the rig. Sources: `FUNDAMENTALS.md` §1,
`docs/THREE_STATION_MODE.md` §5, `verification/three_station_mode_results.md` §3.

- Placement: **In notes** on v9 slide 6 (and the 3-station numbers already on slide 23).

## v8 slide 9, Gen 1 → v9 slides 8 and 10: what bead homing is

**Answer.** "Bead homing is how Generation 1 found zero for each cable. A stopper bead is crimped onto each cable; at the
outlet a lever switch sits in the bead's path. To home, every winch reels in until its bead trips the switch; that pose is the
reference and each cable's zero length. Because the bead cannot pass the outlet, a cable can never be shorter than it was at
home, so the home pose caps how high and how far the claw can go. The homing switch had to move below the pulley onto a drop
arm, so the bead never has to ride over the pulley groove; the first arm design missed the line by 5 mm in X and 10.5 mm in Y
in a CAD check, and rev D overlaps a 5 mm bead by 3.75 mm. The beads stay on the final robot as end-of-travel switches."
CAD-verified; no bead has tripped a printed arm on real line. Sources: `DECISION_STORIES.md` T16, D14, D26,
`calculations/bead_reach.py`.

- Placement: **On slide 10** (definition in the first statement) and **In notes** on slides 8 and 10.

## v8 slide 10, One Controller per Winch → v9 slide 14: what happens when the motors lose power

**Answer.** "A stepper holds only while it is powered; there is no brake and no self-locking stage. If the 12 V goes, from
the power strip, a blown fuse or a pulled plug, all four motors lose holding torque and the claw falls, up to 1.5 kg from
about 2 m. That is deliberate: the power strip is the one category-0 stop that software cannot override, and the accepted
mitigation is that nobody stands under the robot. Each station's controller runs from the same 12 V pair, so a power loss is
also a reboot: the driver's enable line is pulled high at boot so a reset can never move a motor, and nothing resumes by
itself, the host comes back disarmed or in recovery and waits for a person. A lost Wi-Fi link is different: the stations
stop and hold on their own clocks with torque on. A brake or a non-backdrivable stage is on the next-steps list." Designed and
SIMULATED; not run on four stations. Sources: `DECISIONS.md` D21, D25, `docs/electrical/station_revC_20261016/README.md`,
`DECISION_STORIES.md` T04, T27, v8 safe-state table.

- Placement: **On slide 14** (the Faults row of the table) and **In notes**.

## v8 slide 11, Camera Calibration → v9 slides 10 and 15: floor area instead of volume

**Computed here** from the same model as the volume chart (`calculations/bead_reach.py`: room 11 × 9 ft, anchors 0.05 m in
from the corners at 2.59 m, 0.2 m wall margin, heights 0.3 to 2.19 m, home at the room centre). A floor point counts as
reachable when the claw can reach it at the model's lowest working height, 0.3 m, where clothes would be grabbed:

| Home height above the floor | Reachable share of the working volume (the chart) | Reachable share of the floor at grab height |
|---|---|---|
| 0.6 m | 0.4 % | 7 % |
| 0.8 m | 1.8 % | 23 % |
| 1.0 m | 4.8 % | 45 % |
| 1.2 m | 9.2 % | 67 % |
| 1.5 m | 17.3 % | 93 % |
| 1.8 m | 25.2 % | 100 % |
| 2.0 m | 29.3 % | 100 % |

Script: scratch `bead_floor.py` (same anchors, margins and reach test as `bead_reach.py`, 120 × 100 floor grid, 50 heights).

**Answer.** "The panel is right that floor area is the honest measure of where clothes can be picked, and it reads very
differently: with the beads set 1 m up, 45 % of the floor is reachable at grab height, not 5 %; at 1.5 m, 93 %; from 1.8 m
up, all of it. Bead homing does not lose floor, it loses height: a cable can never be shorter than at home, so the claw cannot
rise above the home pose anywhere, and near the walls much less. The robot needs that height to scan the floor from 1.6 m,
to lift a garment over the hamper and to keep the cables off furniture, and a high home pose sits in the high-tension zone
next to the anchors. So the volume chart is the right figure for the robot's job, but the slide now says both, and I would
present the floor number first." CALCULATED. Sources: `calculations/bead_reach.py` and `.json`, the table above,
`FUNDAMENTALS.md` §1.

- Placement: **On slide 10** (one statement with the floor numbers) and **In notes** on slides 10 and 14.

## v8 slide 12, Claw → v9 slide 18: where the 0.3 friction coefficient came from

**NOT IN THE RECORD as a measurement.** The 0.3 is an assumption: `calculations/gen2_screening.py` line 49,
`MU_CLOTH = 0.3  # ASSUMED cloth-on-printed-jaw friction`, carried into the design review R5, `FUNDAMENTALS.md` §5
("μ = 0.3, cloth on a printed pad; 0.6 for TPU pads; the pad-to-cloth μ has never been measured") and the grip equation on
the slide. No source (handbook, test or datasheet) is cited anywhere in the record.

**What the presenter can say.** "The 0.3 is an assumed value for cloth on a bare printed PETG pad, chosen low on purpose; I
also run the numbers at 0.6 for TPU pads. It has not been measured, which is why the jeans case is marked short and why a
pull test with a force gauge on the real pads is first on the list." CALCULATED on an ASSUMED input.

- **Question for Jasper:** where did 0.3 come from (a handbook value for cotton on plastic, a class note, a guess, or a quick
  test with a scale)? If a test, what pad, what cloth, what reading? Placeholder `[[Jasper: ...]]` in the slide 18 notes.
- Placement: **In notes** + **Question for Jasper**.

## v8 slide 13, Final Wall Station → v9 slide 16 (and 12): what the aluminium fin does

**Answer.** "The motor's only way out of a closed printed box is conduction into the PETG it is bolted to, and PETG is a
thermal insulator: 0.2 W/m·K against 160 for aluminium, so the 5 mm tab is 14 K/W and a 3 mm aluminium plate 0.011 K/W,
1260 times less. The fin is that aluminium plate: it sits between the motor flange and the tab, takes heat from the flange by
conduction, carries it along the sheet and out through the slot in the shell top, and sheds it to room air by convection and
radiation over both faces, 200 mm by 44 mm. In the model it carries 35 to 50 % of the motor's 4.05 W, cuts the sealed-shell
motor temperature from about 99 to 64 °C and the vented from 77 to 56–59 °C, and it keeps the loaded PETG tab under the
motor cooler, which is the creep concern. It also spreads the bolt load over the tab. The thin 0.019 in prototype stops
gaining by 136 mm because the sheet cannot conduct more; the 1/8 in design plate would carry all 4.05 W alone at 56–59 °C."
CALCULATED; no temperature has been measured; the hold test is PLANNED. Sources: `FUNDAMENTALS.md` §3,
`calculations/fin_sizing_4w.md`, `DECISIONS.md` D37, D38, `verification/thermal_assembly_1p5a_check.md`.

- Placement: **On slide 16** (one statement) and **In notes** on slides 16 and 12.

## v8 slide 14, Winch Pull → v9 slide 17: how the pull-test value was validated

**Answer.** "It has not been validated; the slide's pull is calculated and the test is planned. The chain is: the driver
sets the coil current from its reference voltage, I = Vref/(8 × 0.1 Ω), 1.5 A at 1.2 V; holding torque is taken proportional
to current from the motor's 0.36 N·m rating; running torque is assumed to be 0.7 of holding; and line pull is torque over
spool radius, 34 N on the empty 7.5 mm core and 25 N at the full 10 mm. The two weak links are the 0.7 factor, which is a
convention, and the torque basis: if the 0.36 N·m rating is a two-phase figure the pull could be about 1.4 times lower. The
validation is a 15-minute luggage-scale test on one station, reeling in against the scale at the empty and the full spool
until the motor skips; its result replaces the 0.7 and goes into the planner as the tension limit." CALCULATED; pull test
PLANNED; how 1.5 A was reached is not recorded (D37). Sources: `FUNDAMENTALS.md` §2, `DECISIONS.md` D37,
`docs/decisions/WINCH_CAPACITY_20261021.md`, `verification/deck_factcheck.md` F01.

- Placement: **In notes**.

## v8 slide 15, Motor Cooling → v9 slide 16: why the 6061 is painted

**What the record holds.** The paint is in the design, not confirmed on the built fin. The fin drawing calls for "matte
black paint except the motor contact square" and the sizing model assumes a black fin, emissivity 0.9, because a thin plate
in still air sheds a large share of its heat by radiation: the effective film coefficient is 10.6 W/m²·K painted against
6.2 bare, the fin resistance changes by 37 %, and bare aluminium would need a 1/4 in plate about 300 mm long to carry 4.05 W
alone where painted 1/8 in does it at 145–185 mm. The motor temperature itself moves less (about 1.5 K vented, 2 to 3 K
sealed) because the motor also sheds heat into the shell air. Photos 15 to 18 show the built prototype fin bare, and the
alloy is unconfirmed (the sheet may not be 6061).

**What the presenter can say.** "Paint is for radiation. Bare aluminium has an emissivity near 0.1 and radiates almost
nothing; matte black is about 0.9, and for a thin plate in still air that nearly doubles the heat it sheds per degree. In the
sizing table that is the difference between a 1/8 in fin that works at 145 to 185 mm and a bare one that needs 1/4 in and
300 mm. The contact square under the motor stays bare, with thermal paste, so paint never sits in the conduction path."
CALCULATED. Sources: `calculations/fin_sizing_4w.md` (results and raw output), `cad/HEAT_FIN_1021_SPEC.md`,
`docs/simulation/SW_THERMAL_HEAT_FIN.md` item 4, `verification/deck_factcheck.md` F13.

- **Question for Jasper:** is the built prototype fin painted (the photos show bare metal), and if so with what and when? Is
  the sheet 6061, and how do you know (a magnet or file test, a label)? Placeholder `[[Jasper: ...]]` in the slide 16 notes.
- Placement: **In notes** + **Question for Jasper**.

## v8 slide 16, Weight Budget → v9 slide 17: where the ~25 % mass reduction from the estimate came from

**What the record holds.** The 0.86 kg is a CAD-based estimate with the battery (DESIGN_STATE 10/22; Lift budget sheet row
19); the claw weighed 0.60 kg with the battery on 10/22. The record itemizes the weighed claw as: aluminium tube 198 g (CAD),
servo 55 g, battery 99 g, leaving about 250 g of printed parts as built against 677 cm³ of solid CAD volume (860 g at 100 %
solid PETG). The gap between the estimate and the scale is therefore the printed parts: the CAD-based estimate priced them as
solid plastic, and the printed parts have walls and infill. The exact assumptions behind the 0.86 figure (which parts, what
density or infill) are **NOT IN THE RECORD** beyond "CAD-based".

**What the presenter can say** (the attribution to infill is derived here from those numbers, not stated in the record).
"It is the same claw on the scale as in the estimate; the difference is that the estimate came from CAD solids and printed
parts are not solid. The tube, servo and battery are 350 g and were never in doubt;
the printed parts came to about 250 g on the scale against 860 g if they were solid plastic. The lesson I took is that a CAD
mass is an upper bound, and the budget is checked on the scale, not in CAD." MEASURED (0.60 kg) against CALCULATED (0.86 kg).
Sources: `DESIGN_STATE.md` "Claw weighed (10/22)", `docs/decisions/WEIGHT_REDESIGN_PROPOSAL_20261022.md`,
`docs/presentation/DECK_V8_NOTES.md`.

- **Question for Jasper:** what infill and wall count were the claw parts printed with, and did the 0.86 kg estimate assume
  solid parts or a slicer mass?
- Placement: **In notes** + **Question for Jasper**.

## v8 slide 17, Build → v9 slide 20: how the bad 3.3 V connection was found, and the steps when the motor would not turn

**What the record holds (reported by Jasper, not logged or photographed).** The command output showed step pulses while the
shaft did not move; the homing switch worked. The recorded approach was to separate the command from the motion and check
the driver's supply, reference and wake pins before touching code: ENABLE read about 3.3 V idle, 0 V during the run command
and 3.3 V after; SLEEP read about 1 V; the 3.3 V logic rail read about 1.14 V. Jasper identified a bad 3.3 V connection, and
after the correction the motor moved (described as loud and slow). The design change it caused: the driver's VDD comes from
the same regulated rail as the controller, soldered or crimped rather than jumpered, with a measure-VDD step before enabling.
**NOT IN THE RECORD:** what was tried before the meter, what the bad connection physically was, and the exact dates.

**What the presenter can say.** "The log said it was stepping and the shaft said it was not, so I stopped changing code and
put the meter on the driver. Enable toggled correctly with the command, 3.3 to 0 and back, which cleared the firmware; the
sleep pin read about 1 V and the logic rail about 1.14 V instead of 3.3, which pointed at the supply to the driver, and it
was a bad 3.3 V connection. After the fix the motor turned. The habit that came out of it is on the bench slide: a meter on
every rail before code, and the driver's logic supply now comes off the same regulated rail, soldered, with a VDD check
before enable." REPORTED readings (no saved log); design change recorded. Sources: `DECISION_STORIES.md` T30,
`docs/history/REVIEW_HANDOFF_20261019.md` "Electrical debugging record", `verification/design_review_gen2.md` R9,
`DESIGN_STATE.md` "Generation 2".

- **Question for Jasper:** what did you try before reaching for the meter, how did you narrow it to the 3.3 V feed (which
  pin or wire, and what was physically wrong: a loose jumper, a cold joint, a breadboard contact), and what did VDD read after
  the repair? Placeholder `[[Jasper: ...]]` in the slide 20 notes.
- Placement: **In notes** + **Question for Jasper**.

## v8 slide 18, Manufacturing fits → v9 appendix "Manufacturing: fits and datums": which feature each fit belongs to

**Answer (row by row).** "Gear bearings: the 687 ball bearings in the claw's gear housing, a Ø14.075 pocket behind a Ø14.000
entry lip with eight T-slots so the lip flexes as the bearing snaps past. Gear pins: the printed Ø7 pins the claw gears turn
on, into Ø7.05 sockets. Slide-in mount: the station housing's dovetail ribs in the wall-mount grooves, 0.175 mm a side on 30°
flanks. Spool on the D-shaft: the winch spool's bore on the motor's 5 mm D-flat shaft, Ø5.45 after Ø5.2 printed too tight.
End-stop switch: the KW12-3 homing switch pressed into a pocket in the station slide-in. Heat-set inserts: M3 in the claw gear
housing, M2.5 at the station encoder board. Screw clearance: M3 holes in the printed parts and the drilled fin, and the #6
wall-screw holes in the wall mount. Motor pilot: the NEMA 17's Ø22 boss through the printed motor tab and the drilled fin. Fin
hole zero: the datum scheme for drilling the fin, the first hole located from the sheared edges and the other four from it."
MEASURED from Jasper's STEP files (CAD) and his fin method. Sources: v8 slide 18 table, `DESIGN_STATE.md` "Manufacturing
facts measured from Jasper's parts", `cad/HEAT_FIN_1021_SPEC.md`.

- Placement: **In notes** (appendix slide).

## v8 slide 20, Results → v9 slide 25: what narrow grabs are

**Answer.** "A narrow grab is a grip where the jaw tips are close together when the pads meet the cloth: a thin fold rather
than a bunched handful. The jaws are four-bar hands on a gear crank, so the effective lever arm from the crank to the pad is
longest when the jaws are nearly closed, 59 mm at a 10 mm gap, and shortest at a wide grab, 33 mm at 70 mm; the servo's stall
torque is fixed, so the pad force is lowest at a narrow grab, 13.3 N, and rises to 25 N at 70 mm. Jeans at a friction of 0.3
need 17.7 N per jaw with the 2 m/s² allowance, so the force is short until the grab is at least 43 mm wide at 4.8 V, or 22 mm
at the 6 V the claw's servo rail actually runs. The fixes are grippy TPU pads, which halve the force needed, and grabbing a
bunch rather than an edge." CALCULATED requirement against SIMULATED jaw force (four-bar model, no force gauge). Sources:
`FUNDAMENTALS.md` §4 and §5, `verification/gripper_v7_verification.md` row 6, `DECISIONS.md` D31, D32.

- Placement: **On slide 25** (the "Grip for jeans" row) and **In notes**.

## v8 slide 21, Decisions → v9 slide 26: how the weaker decisions affected the overall deliverable

**Answer.** "Each one shows up in the results table. Not tracking mass through four claw versions put the claw at 0.60 kg
against 0.45, which turned the jeans lift margin into 4 % and made the gear stage necessary before any jeans pickup, and it
is why the demo load is 1 lb. Cutting the prototype fin from scrap sheet left 1 to 4 K of thermal margin at 1.5 A, so the
stations cannot run at full current until a hold test passes, with 1.35 A as the fallback. Ending the build week on
presentation day means the first three-station lift, the pull test and the hold test have no result on the slides: everything
on the robot that moves a load is still planned. And building parts far stronger than any load needed cost about 1.2 L of
PETG and days of printing per station for no benefit, which the lighter redesign takes back." MEASURED (claw mass), CALCULATED
(margins), PLANNED (the tests). Sources: v9 slide 25 results table, `DESIGN_STATE.md` "Claw weighed",
`calculations/fin_sizing_4w.md`, `docs/decisions/WEIGHT_REDESIGN_PROPOSAL_20261022.md`.

- Placement: **In notes**.

## v8 slide 22, Takeaways → v9 slide 26: why larger motors were not the answer if mass was the constraint

**Answer.** "Because the mass that matters is on the claw, and the motors are on the wall; a bigger motor adds nothing to the
claw and does not remove a gram from it. What limits the lift is not the motor's size but the current I can put through it
and the heat that makes: pull goes up with current and heat with current squared, so going from 1.0 to 1.5 A bought 50 %
more pull for 2.25 times the heat, and at 1.5 A the printed mount is already at its 60 °C limit. A larger motor would need
more current, a bigger driver than the 2 A A4988, a bigger supply than the 12 V 6 A brick, thicker wire for the 32 ft run and
a new station. The 3:1 gear stage gives 2.7 times the pull at 1.0 A, with half the heat, for two printed gears and two
bearings I already use, and it keeps the motor as the fuse of the lifting chain. The right lever was the ratio, not the motor,
and the other one is taking mass off the claw." CALCULATED (gear stage verified in CAD, not pull-tested). A larger motor is
not among the options in the record; the options recorded were the Ø10 core, the 3:1 reduction, a lighter claw and a lighter
payload. Sources: `docs/decisions/WINCH_CAPACITY_20261021.md`, `calculations/winch_gear3.md`, `DECISIONS.md` D37, D40,
`FUNDAMENTALS.md` §2 and §3, `calculations/fin_sizing_4w.md` ("mass is not the constraint" for the station).

- Placement: **In notes**.

---

## Questions for Jasper (collected)

1. Slide 4: hours spent, mentors or shop access, and whether a dollar ceiling was set in advance.
2. Slide 18: the source of the 0.3 friction coefficient (handbook, class note, guess or a scale test; pad and cloth if tested).
3. Slide 16: is the built prototype fin painted, with what, and is the sheet 6061 (how checked)?
4. Slide 17: infill and walls on the claw parts; what the 0.86 kg estimate assumed.
5. Slide 20: what you tried before the meter; which wire or pin was the bad 3.3 V connection and what was physically wrong;
   VDD after the repair; dates.
