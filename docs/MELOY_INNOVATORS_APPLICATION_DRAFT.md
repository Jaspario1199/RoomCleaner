# Meloy Engineering Innovators ($2,500) — application draft (2026-11-20)

Form: Texas A&M Engineering Entrepreneurship, Meloy Innovators (rolling review). The form asks for seven items; the
answers below follow it. Selection criteria on the page: a well-articulated idea; a clear, detailed plan for the
award; researched costs; the team supplies skills and labor (no hiring); free/low-cost compute used first for
software; Meloy Engineering Incubator participation preferred.

Before submitting: confirm every price at the seller's page, fill in teammates (if any), and fix the incubator answer
to what is true.

---

## 1. Name and contact information

Jasper Buntinx, Mechanical Engineering (B.S. expected August 2027), [TAMU email], [phone].

## 2. Brief description of the innovation

**RoomCleaner: minimally invasive home robotics.** Home robots today either crawl across the floor, where the
clutter they are meant to clear blocks them, or they are humanoids that cost as much as a car. RoomCleaner takes a
third path: it works from the ceiling down and leaves the floor, the furniture and the walls almost untouched.

A few small winch boxes slide onto wall mounts near the ceiling and hold one claw on thin cables. Changing the cable
lengths moves the claw anywhere in the room, so it can pick up laundry and clutter and drop it in a hamper. When it
is not wanted, each box slides off its mount and unplugs; the room goes back to normal. Each box joins Wi-Fi by
itself and updates over the air, and the robot calibrates itself at startup from a printed floor mat its camera
reads, so nobody has to measure anything.

The people this helps most are the ones for whom bending down is hard: older adults, people with back injuries or
limited mobility, and the family members who care for them. Picking clothes off the floor is a small task that
becomes a real barrier to living independently; a robot that does it from above, without a machine roaming the
floor to trip over, is a quiet kind of help.

**Where it stands today (self-funded, about $640 spent, July to November 2026):**
- **Generation 1 built and retired:** one central board driving four corner motors with bead homing. It lifted a
  test weight and showed why the design had to change: bead homing leaves at most about a third of the room
  reachable, and a central box means about 250 m of wire.
- **Generation 2 built:** three winch stations printed, machined and wired, each with its own ESP32, driver, homing
  switch, spool encoder and aluminium heat fin. Both controller boards pass the bench checklist; the first station
  is on the wall on its slide-in mount.
- **Claw built:** four-bar hands, camera, its own battery. Live view, battery sensing and servo pass on the bench;
  it hangs from three cables in the room.
- **Software written and tested in simulation:** six-state startup and self-calibration, motion planning with
  tension limits, an obstacle map, a phone app, over-the-air updates.
- **Next iteration designed:** a 3:1 printed gear stage, a drafted slide-in mount that cannot bind, a lighter back
  mount, TPU grip pads, and a circuit board built for automated assembly in the Fab Lab.
- **Now experimenting with sensing beyond the camera:** fusing lidar, Bluetooth and Wi-Fi signals with video to map
  the room and detect people, training the models in simulation and refining them by trial on the real robot. The
  aim is a robot that knows when someone is underneath it and stops, without depending on a camera alone.

## 3. Team members

Jasper Buntinx: mechanical design (SolidWorks/CadQuery), printing and machining, electronics and PCB design,
firmware and control software. [Add any teammates and their roles.]

## 4. Plans for the innovation

The prototype exists. The award funds the step from "it works in my room" to "someone else can safely install it":

1. **Measure what is still calculated (weeks 1–3).** Pull test of each winch with a calibrated hanging scale, a
   90-minute hold test of motor temperature, the first three-station lift with a 1 lb load, then 100 pick-and-place
   cycles with every fault logged.
2. **Make it safe to live under (weeks 2–8).** A power cut currently drops the claw, because the motors only hold
   while powered. Power-off brakes fix that: the brake's 0.25 N·m friction torque on the 7.5 mm spool holds about
   33 N of cable tension, double the 16.8 N design limit per cable. In parallel, the lidar and radio sensing work
   becomes a person-detection layer that keeps the claw away from anyone below it.
3. **Build the next iteration (weeks 4–8).** Fit the 3:1 gear stage (2.7x the pull at the same current), print the
   drafted and lighter mounts, add TPU grip pads, and assemble the new boards on the Fab Lab's stencil printer,
   pick-and-place and reflow oven so every station is built the same way.
4. **Make it plug and play (weeks 6–10).** Power each box from a standard USB-C charger and set up Wi-Fi from the
   phone instead of in code.
5. **Five-unit alpha (weeks 10–16).** Five homes, including at least one person with limited mobility, install kits
   from printed instructions; every setup problem and failure is logged.
6. **Protect and position (alongside).** File a provisional patent on the self-calibrating, slide-off winch system
   and enter Aggie PITCH with the alpha results. The closest competitor (Stringman, about $1,000) needs drilled
   corner anchors and a desktop PC; RoomCleaner's slide-off boxes, phone setup and self-calibration are the
   difference.

## 5. Goods and services to procure (researched costs; confirm before ordering)

| Item | Qty | Unit price | Total | Source / note |
|---|---|---|---|---|
| NEMA 17 stepper with 24 V power-off brake (StepperOnline 17HS19-2004D-B025, 0.59 N·m, brake 0.25 N·m) | 8 | $47.44 | $379.52 | omc-stepperonline.com list price; 4 to retrofit my robot, 4 for alpha kits (my existing motors go into further alpha kits) |
| 24 V supply / boost for the brake coils (5 W each) | 8 | ~$10 | ~$80 | estimate; brakes are 24 V, my bus is 12 V |
| Rev E station PCBs + matching stencil (board house) | 20 boards + 1 stencil | quote | ~$80 | estimate; get a JLCPCB quote with the fab zip |
| SMD/THT parts for 20 boards (resistors, SS14, headers, JST-XH, terminals, C1) | 20 sets | ~$6 | ~$120 | estimate from the Rev E BOM |
| XIAO ESP32-C3 + A4988 + 5 V buck per station | 16 | ~$12 | ~$190 | estimate from the cost breakdown |
| USB-C PD 12 V trigger boards (10-pack) | 2 | $13.99 | $27.98 | Newegg listing |
| USB-C PD chargers ≥ 36 W (12 V / 3 A) | 16 | ~$15 | ~$240 | estimate |
| Calibrated hanging scale for pull tests (PCE-HS 50N, 50 kg) | 1 | $119.00 | $119.00 | TestEquity listing |
| Claw parts for 4 alpha kits (servo, camera board, battery, charger, regulators) | 4 | ~$60 | ~$240 | estimate from the claw bill of materials |
| PETG and TPU filament, Dyneema line, fasteners, heat-set inserts | — | — | ~$250 | estimate; 0.76 kg PETG per station at ~$15/kg |
| Printed floor mats (9 sheets each, laminated) | 5 | ~$10 | ~$50 | estimate |
| Low-cost 2D lidar module for the sensing experiments | 1 | ~$90 | ~$90 | estimate; confirm model and price |
| USPTO provisional patent filing fee (micro entity) | 1 | check fee schedule | ~$65 | uspto.gov fee schedule |
| **Total** | | | **~$1,930** | remaining ~$570 covers shipping, price changes and one round of board fixes |

Already owned and not requested: the three built stations, the claw, the gen-1 parts, the printed next-iteration
pinion, tools and spares (about $640 spent so far). No hiring: all design, assembly and testing is my own labor. Software runs on my own hardware and free tools.

## 6. Involvement with the Meloy Engineering Incubator

Not yet. I have built the project on my own time and money so far, and I would welcome an assigned mentor with
consumer-hardware or product-safety experience.

## 7. Additional information

- The engineering is documented end to end: requirements, decisions, calculations, CAD, circuit boards, firmware and
  tests, all in one repository, with every number tagged by where it came from (measured, datasheet, calculated,
  assumed).
- [Optional, only if you are comfortable naming it: "I presented this project at my SpaceX onsite interview."]
- Safety is designed in, not bolted on: the motor is the deliberate weak link (it slips near 48 N before any part
  of the mount fails), the encoder turns slip into a fault, and the startup sequence never retries on its own.

Sources for prices: omc-stepperonline.com (17HS19-2004D-B025), newegg.com (12 V PD trigger 10-pack),
testequity.com (PCE-HS 50N). Competitor: Stringman coverage (eWeek, Interesting Engineering). Award page:
engineering.tamu.edu/student-life/eep/funding/meloy-innovators.html.
