# Meloy Engineering Innovators: final answers as submitted text (2026-11-20)

Supersedes the structure in MELOY_INNOVATORS_APPLICATION_DRAFT.md for the three long form fields. Platform framing:
home automation from the ceiling, laundry first, fetch-and-carry second; affordable alternative to humanoid robots.

## Brief description of the innovation

RoomCleaner is home automation that comes down from the ceiling: a small cable robot that can reach anywhere in a
room, sets up in minutes, calibrates itself, and does the physical chores that today only an expensive humanoid robot
promises to do. Picking laundry off the floor is the first job it's learning. It won't be the last.

(Full text as given in chat on 2026-11-20: humanoid contrast; reach from above; minimally invasive; platform
features: easy setup, self-calibrating, safe by design, modular, affordable; beyond laundry: fetch to a person,
clear clutter, high shelves, garages/workshops, light pick-and-place in labs/classrooms/back rooms; accessibility
mission; build status since July, self-funded about $640; team: Muhammet Alsaka (EE), Diego Prozzi (Business).)

## Milestones

1. Prove the platform with real measurements (weeks 1-3): pull test, 90-minute hold test, first three-station lift
   with 1 lb, 100 cycles.
2. Make it safe to live under (weeks 2-8): power-off brakes (0.25 N·m on the 7.5 mm spool, about 33 N, vs 16.8 N
   design limit per cable); lidar/radio person detection.
3. Build the next iteration (weeks 4-8): 3:1 gearbox (2.7x pull), jam-proof and lighter mounts, grip pads,
   double-sided boards milled on the Fab Lab Carvera and assembled on its stencil / pick-and-place / reflow line;
   sensor and motor comparisons.
4. Swappable tool and a second task (weeks 6-10): quick-change tool mount; fetch-and-carry tool.
5. Plug and play (weeks 6-10): USB-C power, Wi-Fi setup from the phone.
6. Five-home alpha (weeks 10-16): includes a person with limited mobility; laundry and fetch-and-carry; log failures
   and which tasks people use.
7. Protect and pitch (ongoing): provisional patent (self-calibrating slide-off winch system, swappable tool
   interface); Aggie PITCH; competitor Stringman (~$1,000, drilled corner anchors, desktop PC).

## Budget (total about $1,980; about $520 contingency)

| Item | Cost |
|---|---|
| 8 brake steppers, StepperOnline 17HS19-2004D-B025 at $47.44 | $379.52 |
| 8 x 24 V brake supplies | ~$80 |
| 2 x 12 V USB-C PD trigger 10-packs (Newegg) at $13.99 | $27.98 |
| 16 x USB-C chargers ≥ 36 W | ~$240 |
| 20 double-sided copper-clad blanks | ~$40 |
| PCB milling bits and drills | ~$50 |
| Board components for 20 boards | ~$120 |
| 16 x XIAO ESP32-C3 + A4988 + 5 V buck | ~$190 |
| PCE-HS 50N 50 kg hanging scale (TestEquity) | $119.00 |
| 2D lidar module | ~$90 |
| Fetch-and-carry tool parts (servo, quick-change hardware, TPU, fasteners) | ~$40 |
| Claw parts for 4 alpha kits | ~$240 |
| Filament, Dyneema, fasteners, inserts | ~$250 |
| Floor mats for 5 kits | ~$50 |
| USPTO provisional, micro entity | ~$65 |
| **Total** | **$1,981.50** |

Already owned, not requested: three stations, claw, Gen 1 hardware, printed pinion, tools and spares (about $640).
No labor costs; software on own hardware and free tools.
