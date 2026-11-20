# RoomCleaner as a product: from prototype to a plug-and-play kit (plan, 2026-11-20)

Goal (Jasper, 11/20): sell a self-calibrating, plug-and-play ceiling cable robot that a buyer can set up at home or
for other automation.

## 1. The market already has one competitor

**Stringman** (Neufangled Robotics): four ceiling-corner anchors, one gripper, autonomous laundry pickup, drop-off
points marked with clip-on fiducials, compute on an external PC (Ryzen 7 class recommended), reported around $965
assembled or about $1,000 as a DIY/pilot kit. Reported weak points: drilling into four ceiling corners (bad for
renters), flat items defeat the gripper, cables descend into the room while it works.

So the category is proven enough to sell to enthusiasts, and the price point is set. RoomCleaner has to win on
something specific. What it already has that the reports do not credit Stringman with:

| RoomCleaner feature | Status | Why a buyer cares |
|---|---|---|
| Self-contained winch boxes that slide off a wall mount and unplug | built (slide-in dovetail, D-series) | take it down for guests, fix a box without tools, renter-friendlier |
| Each box has its own brain, joins Wi-Fi itself, updates over the air | built (ESP32 per station, OTA) | no wiring between corners, no laptop cable |
| Self-calibration from a printed floor board, no tape-measured anchors | built in software, simulated | "self-centering" setup in minutes, no measuring |
| Encoder per spool: confirms steps, catches slip as a tension sensor | built, bench PASS | detects a snag or overload instead of ripping a mount |
| Three-station mode | built in software | cheaper starter kit, fewer holes |
| Modular end effector | designed for it | laundry first, other tools later ("other automation") |

## 2. What "plug and play" means, and the gap from today

| A buyer expects | Today | Needed |
|---|---|---|
| Power: plug each box into any outlet | 12 V run along the wall from one supply | one USB-C PD charger per box at 12 V (a PD trigger on the board), or a UL-listed 12 V adapter per box |
| Wi-Fi: join from the phone | `secrets.h` compiled into firmware | BLE or soft-AP provisioning from the app; no recompiling |
| Setup: no measuring, no config files | `config/robot.json`, IPs set by hand | auto-discovery (mDNS), boxes identify themselves, app walks through placement |
| Runs without a laptop | host service + perception run on a laptop | a small hub (single-board computer) or a phone/cloud split; perception budget decides which |
| Mounting without a contractor | screws into studs | stud mount stays the reference; add a rated no-drill option (pole / tension-rod clamp, the D-series mount is already separate) |
| Survives power loss safely | a power cut drops the claw (no brake, D21) | **must fix before any sale**, see section 3 |
| Picks up what people drop | 1 lb test load planned, jeans 1.70 kg capacity calculated, first lift not yet run | measured pull test, hold test, first lift, then reliability cycles |

## 3. Safety items that block selling anything

These are not polish. A consumer product hangs a moving load over people, pets and furniture.

1. **Power loss must not drop the claw.** Today the stepper holds only while powered and the spur stage (3:1) is
   back-drivable. Options: a power-off brake on each motor, a self-locking worm stage, or a spool ratchet that engages
   on power loss. Decide by calc plus a drop test.
2. **Nobody under the robot is a rule, not a feature.** For a product it has to be enforced: person/pet detection in
   the claw camera before and during motion, a speed and height envelope, and a load limit that is checked (the
   encoder slip detection is a start).
3. **Anchor pull-out.** The motor is the designed fuse (slips at about 48 N, calc). That has to be shown by test on
   the real mount, in a stud and in the no-drill option, with a published rating.
4. **Cable hazards.** Entanglement and strangulation risk for children; cable visibility; behavior when a cable
   catches on furniture.
5. **Electrical.** Use a certified external power supply (UL 62368-1 listed adapter or PD charger) so the robot
   itself stays low-voltage.

## 4. Certification and legal (US first)

- **FCC Part 15.** The ESP32 modules carry their own radio approval, which covers the intentional radiator, but the
  finished product still needs unintentional-emissions testing (Part 15 Subpart B) at a test lab. Get quotes before
  committing to a launch date.
- **UL 3300** (Outline of Investigation for service, communication, information, education and entertainment robots)
  sits on top of the base product standard and covers mobility, manipulation, user classes and surroundings. Not
  legally required to sell, but retailers and insurers ask for it, and it is the checklist to design against now.
  Contact: UL's consumer technology group.
- **Product liability insurance** before the first unit leaves the bench.
- **Patents:** search the cable-robot and consumer cable-robot space before disclosing more publicly; a provisional
  application is cheap and buys a year. Texas A&M's McFerrin Center for Entrepreneurship and the university's tech
  commercialization office are the first stops (also check who owns IP developed with university resources).

## 5. Phased plan with gates

| Phase | Deliverable | Gate to pass before the next phase |
|---|---|---|
| **0. Prove the prototype** | pull test at 1.5 A, 90-minute hold test, first three-station lift, 100 pick-and-place cycles | measured numbers replace every "calc/assumed" on the critical path; no unrecovered fault in 100 cycles |
| **1. Fix the product blockers** | power-loss hold (brake or worm), Rev E boards, PD power, phone provisioning, auto-discovery | drop test passes; a new box joins and calibrates with no laptop and no config edits |
| **2. Five-unit alpha** | 5 kits installed by people who are not you, in different rooms | each installs in under an hour from printed instructions; log every failure |
| **3. Developer / maker kit** | sell to enthusiasts, open firmware and app, clear "developer kit" labelling | FCC Part 15B passed; insurance in place; support plan |
| **4. Consumer product** | hub, no-drill mount, injection-molded shells, UL 3300 evaluation | certification, unit cost at target, return rate measured in phase 3 |

Selling a developer kit first is how the competitor entered, and it fits: the buyers forgive rough edges, and their
installs generate the reliability data phase 4 needs.

## 6. Cost picture today

Parts in the robot for three stations: $210.78 plus $37.74 of filament (COST_BREAKDOWN_20261026.md, partly estimated).
That excludes the hub, brakes, PD chargers, packaging, the floor board, support and certification. A kit price near
the competitor's needs a full landed-cost sheet after phase 1.

## 7. Decisions only Jasper can make

1. First customer: makers and developers (kit, phase 3) or households (phase 4)?
2. Time and money: solo side project, or a funded team (pitch competitions, McFerrin programs)?
3. Open source or closed? The competitor is open; RoomCleaner's differentiators are hardware and setup.
4. Power-loss fix: brake, worm stage, or ratchet? (calc and drop test first; recommendation follows those results)

Sources: Stringman coverage (eWeek, Interesting Engineering, gagadget, Hackaday.io project 205264, Neufangled site);
UL 3300 announcement (ul.com) and listings (ANSI webstore, GlobalSpec). Internal numbers: DECISIONS.md D21, D45,
deck v10 slide 12 (48 N slip), COST_BREAKDOWN_20261026.md.
