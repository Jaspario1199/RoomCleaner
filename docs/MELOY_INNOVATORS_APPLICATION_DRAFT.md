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

RoomCleaner is a ceiling cable robot that picks laundry and clutter off the floor and drops it in a hamper. Four
small winch boxes mount high on the walls and hold one claw on four cables; changing the cable lengths moves the
claw anywhere in the room, with nothing on the floor. Each box is self-contained: it slides off its wall mount and
unplugs, joins Wi-Fi by itself and updates over the air. The robot calibrates itself at startup from a printed
floor mat that its claw camera reads, so a buyer never measures anchor positions. A spool encoder in every box
confirms each step and detects slip, so a snag stops the robot instead of pulling a mount out of the wall.

I have built and bench-tested working winch stations and the claw (camera, battery, servo), and written the
control software, simulator and phone app. The goal is a self-calibrating, plug-and-play kit for home automation.

## 3. Team members

Jasper Buntinx: mechanical design (SolidWorks/CadQuery), printing and machining, electronics and PCB design,
firmware and control software. [Add any teammates and their roles.]

## 4. Plans for the innovation

The next milestone is turning the prototype into a kit a stranger can install. The award funds that milestone:

1. **Prove it with measurements (weeks 1–3).** Pull test of each winch with a calibrated hanging scale, a 90-minute
   hold test for motor temperature, the first three-station lift, then 100 pick-and-place cycles with every fault
   logged.
2. **Fix the one safety blocker (weeks 2–6).** Today a power cut drops the claw, because the motors only hold while
   powered. I will switch to steppers with power-off brakes: the brake's 0.25 N·m friction torque on the 7.5 mm
   spool holds about 33 N of cable tension, double the 16.8 N design limit per cable.
3. **Make it plug and play (weeks 4–8).** Order my Rev E circuit board (already designed: socketed modules, keyed
   connectors, DRC clean) and assemble it on the Fab Lab's stencil printer, pick-and-place and reflow oven, so
   every station is built the same way instead of hand-wired. Power each box from a standard USB-C charger through
   a 12 V PD trigger, and replace hard-coded Wi-Fi with setup from the phone.
4. **Five-unit alpha (weeks 8–14).** Build kits for five people who are not me to install from printed
   instructions, and log every setup problem and failure.
5. **Protect and position (alongside).** File a provisional patent on the self-calibrating, modular winch system,
   and enter Aggie PITCH with the alpha results. The closest competitor (Stringman, about $1,000) needs drilled
   anchors and an external PC; RoomCleaner's slide-off boxes, phone setup and self-calibration are the difference.

## 5. Goods and services to procure (researched costs; confirm before ordering)

| Item | Qty | Unit price | Total | Source / note |
|---|---|---|---|---|
| NEMA 17 stepper with 24 V power-off brake (StepperOnline 17HS19-2004D-B025, 0.59 N·m, brake 0.25 N·m) | 8 | $47.44 | $379.52 | omc-stepperonline.com list price; 4 for my robot, 4 for alpha kits |
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
| USPTO provisional patent filing fee (micro entity) | 1 | check fee schedule | ~$65 | uspto.gov fee schedule |
| **Total** | | | **~$1,840** | remaining ~$660 covers shipping, price changes and one round of board fixes |

No hiring: all design, assembly and testing is my own labor. Software runs on my own hardware and free tools.

## 6. Involvement with the Meloy Engineering Incubator

[Be accurate. If not yet involved: "I am joining the Meloy Engineering Incubator this semester to get mentorship on
customer discovery and the path from a developer kit to a consumer product, and I would welcome an assigned mentor
with consumer-hardware or product-safety experience."]

## 7. Additional information

- The engineering is documented end to end: requirements, decisions, calculations, CAD, circuit boards, firmware and
  tests, all in one repository, with every number tagged by where it came from (measured, datasheet, calculated,
  assumed).
- [Optional, only if you are comfortable citing it: "I presented this project's engineering (homing method,
  self-calibration math, manufacturing approach) in a technical interview presentation for an engineering role."]
- Safety is designed in, not bolted on: the motor is the deliberate weak link (it slips near 48 N before any part
  of the mount fails), the encoder turns slip into a fault, and the startup sequence never retries on its own.

Sources for prices: omc-stepperonline.com (17HS19-2004D-B025), newegg.com (12 V PD trigger 10-pack),
testequity.com (PCE-HS 50N). Competitor: Stringman coverage (eWeek, Interesting Engineering). Award page:
engineering.tamu.edu/student-life/eep/funding/meloy-innovators.html.
