# RoomCleaner cost breakdown — 2026-10-26

Requested by Jasper (10/26): price the parts actually in the robot, prorated to what was used out of each pack; wiring
estimated; filament kept separate; and, separately, everything ordered versus what was used.

**Definition of the build (10/26):** three wall stations mounted or being mounted (A, B, C; station D's parts exist and
count as spare, `docs/THREE_STATION_MODE.md`), each with a NEMA 17, an A4988 carrier, a controller (two XIAO ESP32-C3 and
one ELEGOO ESP32 DevKit on the station that lost its XIAO, `docs/electrical/station_revD_20261021/BREADBOARD_LAYOUT_ESP32.md`),
a DROK buck, an AS5600 board with a Ø4 magnet (D43), a KW12-3 switch, a direct-drive spool on the motor shaft (the D40–D42 3:1
stage is the next iteration: designed, pinion printed, not fitted; Jasper 10/27), a fuse, WAGOs, C1, R1–R4 and a board; the Rev B claw (D31, `docs/electrical/claw_revB_20261021/`); shared line, power,
hardware and wire. Both a **3-station** and a **4-station** column are given.

**Prices:** 'recorded' = a price written in this repo (SHOPPING_LIST.md 2026 estimates, the 10/18 cost review, D31 sources);
'est.' = typical Amazon price assumed here because none is recorded. Nothing was browsed. Tax and shipping are excluded.
Prorating = pack price × (quantity used ÷ pack quantity); composite kits are valued by hand and say so in the note.

## Headline numbers

| | 3 stations | 4 stations |
|---|---:|---:|
| **Parts in the robot, prorated, without filament** | **$210.78** | **$248.04** |
| Filament in the robot (estimate, §2) | $37.74 | $49.17 |
| **Everything ordered** (incl. filament and tools; recorded $289.47 + est. $348.00) | **$637.47** | $637.47 |
| Spares, gen-1 parts, next-iteration parts and tools on the shelf (ordered − used − filament) | $388.95 | $340.26 |
| of which tools (meter, soldering iron) | $35.00 | $35.00 |

Roughly: of about $637.47 spent, $210.78 (three stations) to $248.04 (four) is in the robot as
parts, $37.74–$49.17 as filament, and the rest ($388.95 / $340.26) is pack remainders, gen-1 parts,
the next-iteration gear-stage parts and tools. (Revised 10/27: the 3:1 gear stage, its 687 bearings and Ø7 shafts are not fitted.) The biggest in-robot lines are the motors, the 16 AWG power run, the claw battery, the 12 V supply, the UBEC,
the XIAO S3 Sense and the station controllers.

## 1. Parts in the robot, prorated (no filament)

| Item | Product | Pack bought (qty, price) | Qty used (3 st / 4 st) | Prorated (3 st) | Prorated (4 st) | Subsystem | Evidence |
|---|---|---|---|---:|---:|---|---|
| NEMA 17 stepper | SIMAX3D NEMA 17 42-38, 36 N·cm, 1.5 A (5-pack) | 5 motor, $33.00 | 3 / 4 | $19.80 | $26.40 | Stations (×3 / ×4) | recorded |
| A4988 driver carrier | ACEIRMC CNC Shield V3 + 4× A4988 with heatsinks | 4 A4988 carrier, $10.00 | 3 / 4 | $6.00 | $8.00 | Stations (×3 / ×4) | recorded |
| Station controller: XIAO ESP32-C3 | Seeed XIAO ESP32-C3 (3 boards, Amazon) | 3 board, $18.00 | 2 / 2 | $12.00 | $12.00 | Stations (×3 / ×4) | est. |
| Station controller: ELEGOO ESP32 DevKit | ELEGOO ESP-WROOM-32 USB-C dev board (3-pack) | 3 board, $16.00 | 1 / 2 | $5.33 | $10.67 | Stations (×3 / ×4) | recorded |
| Station 5 V buck | DROK adjustable buck converter, 4.5–20 V in (6-pack) | 6 module, $16.00 | 3 / 4 | $8.00 | $10.67 | Stations (×3 / ×4) | est. |
| AS5600 encoder board | UMLIFE AS5600 magnetic encoder boards (5-pack, 10/19 cart) | 5 board, $12.00 | 3 / 4 | $7.20 | $9.60 | Stations (×3 / ×4) | est. |
| Ø4 encoder magnet (diametric) | Ø4 × ~2.5 mm diametric magnets (pack of 10, order not recorded) | 10 magnet, $7.00 | 3 / 4 | $2.10 | $2.80 | Stations (×3 / ×4) | est. |
| Homing / end-stop switch | HiLetgo KW12-3 roller micro switch (10-pack) | 10 switch, $6.00 | 3 / 4 | $1.80 | $2.40 | Stations (×3 / ×4) | recorded |
| 100 µF / 50 V capacitor (C1 at VMOT) | JCCON 100 µF 50 V electrolytic (10) | 10 cap, $6.00 | 3 / 4 | $1.80 | $2.40 | Stations (×3 / ×4) | est. |
| FR4 perfboard 5×7 cm | FR4 perfboards (pack of 34, 10/19 cart) | 34 board, $10.00 | 1 / 2 | $0.29 | $0.59 | Stations (×3 / ×4) | est. |
| Breadboard jumper kit | solid jumper kit, 840 pcs (10/19 cart) | 840 jumper, $8.00 | 75 / 100 | $0.71 | $0.95 | Stations (×3 / ×4) | est. |
| Dupont jumper wires | female-male Dupont jumpers, 120 pcs (10/19 cart) | 120 jumper, $7.00 | 20 / 30 | $1.17 | $1.75 | Stations (×3 / ×4) | est. |
| #10 × 3 in wood screws | #10 × 3 in exterior wood screws (box of ~50) | 50 screw, $8.00 | 18 / 24 | $2.88 | $3.84 | Stations (×3 / ×4) | recorded |
| Aluminium heat fin, 0.019 in | 0.019 in aluminium sheet, sheared and milled (stock on hand, D38) | 1 sheet, owned/none | 1 / 1 | $2.00 | $2.50 | Stations (×3 / ×4) | est. |
| **Subtotal Stations (×3 / ×4)** | | | | **$71.09** | **$94.56** | | |
| Claw controller + camera | Seeed XIAO ESP32-S3 Sense | 1 board, $13.99 | 1 / 1 | $13.99 | $13.99 | Claw | recorded |
| Gripper servo | Deegoo-FPV MG996R 180° (4-pack) | 4 servo, $18.00 | 1 / 1 | $4.50 | $4.50 | Claw | recorded |
| Claw battery | Tenergy 7.4 V 2200 mAh 2S1P Li-ion with protection PCB (31003) | 1 pack, $18.49 | 1 / 1 | $18.49 | $18.49 | Claw | recorded |
| Servo 6 V regulator | ZTW 6 A UBEC, screenless, set to 6.0 V | 1 module, $14.99 | 1 / 1 | $14.99 | $14.99 | Claw | recorded |
| XIAO 5 V buck | EBOOT MP1584EN buck (6-pack) | 6 module, $9.00 | 1 / 1 | $1.50 | $1.50 | Claw | recorded |
| USB-C 2S charger (U4) | Type-C 2S 8.4 V 1 A charging module, 2S1A (pack of 2, 10/19 cart) | 2 module, $8.00 | 1 / 1 | $4.00 | $4.00 | Claw | est. |
| 1000 µF / 16 V capacitor (C1) | 1000 µF 16 V electrolytic (pack of 15, 10/19 cart) | 15 cap, $7.00 | 2 / 2 | $0.93 | $0.93 | Claw | est. |
| 100 nF ceramic (C2–C4) | 100 nF '104' ceramic (pack of 100, 10/19 cart) | 100 cap, $6.00 | 3 / 3 | $0.18 | $0.18 | Claw | est. |
| Divider resistors 200 kΩ / 100 kΩ | 200 kΩ + 100 kΩ 1 % metal film (ELEGOO kit or two 100 k in series) | 1 set, owned/none | 1 / 1 | $0.20 | $0.20 | Claw | est. |
| Main switch SW1 | SPST rocker/toggle ≥ 5 A DC (multipack, order not recorded) | 5 switch, $6.00 | 1 / 1 | $1.20 | $1.20 | Claw | est. |
| Aluminium tube | 1-1/8 in OD aluminium tube, 12 in, cut to 10.48 in (D36; order not recorded) | 1 tube, $12.00 | 1 / 1 | $12.00 | $12.00 | Claw | est. |
| **Subtotal Claw** | | | | **$71.98** | **$71.98** | | |
| 687 bearing (7×14×5) | 687ZZ bearings, 7×14×5 mm (pack of 20, order not recorded) | 20 bearing, $12.00 | 4 / 4 (claw gear train) | $2.40 | $2.40 | Shared | est. |
| Blade fuse holder + fuse | SIM&NAT inline ATC/ATO holders (10) + 50 blade fuses | 10 holder+fuse, $12.00 | 5 / 6 | $6.00 | $7.20 | Shared | recorded |
| WAGO 221 lever nuts | WAGO 221 assortment 2401/412/413/415 (12 pcs) | 12 connector, $12.00 | 8 / 9 | $8.00 | $9.00 | Shared | est. |
| 1N5819 Schottky diode (D1) | EEEEE 1N5819 DO-41 (150) | 150 diode, $6.00 | 4 / 5 | $0.16 | $0.20 | Shared | est. |
| 10 kΩ pull resistors ×4, 100 nF, 100 kΩ, breadboard, jumpers | from the ELEGOO UNO R3 Super Starter Kit | 1 kit, $45.00 | 1 / 1 | $8.00 | $9.00 | Shared | recorded |
| 12 V power supply | ALITOVE 12 V 6 A 72 W (barrel plug cut off 8/28) | 1 PSU, $16.00 | 1 / 1 | $16.00 | $16.00 | Shared | recorded |
| 16 AWG 12 V distribution wire | 16 AWG red/black pure-copper paired cable, 100 ft (10/19 cart) | 100 ft, $30.00 | 65 / 94 | $19.50 | $28.20 | Shared | est. |
| 22–24 AWG hookup / signal wire | station 12 V leads from the WAGO, motor and switch tails, encoder leads (hookup wire; order not recorded) | 30 m, $9.00 | 14 / 18 | $4.20 | $5.40 | Shared | est. |
| M3 hardware | MroMax 640-pc M3 button-head kit, 304 SS | 640 pc, $10.00 | 60 / 72 | $0.94 | $1.12 | Shared | recorded |
| M3 heat-set inserts | INCLY heat-set insert kit, M2–M6, 580 pcs + tool | 580 insert, $12.00 | 26 / 32 | $0.54 | $0.66 | Shared | recorded |
| Dyneema line | 9KM DWLIFE X8 braided Dyneema 120 lb, 150 m | 150 m, $8.00 | 18.3 / 24.4 | $0.98 | $1.30 | Shared | recorded |
| Floor board (AprilTag sheets) | 9 Letter sheets, home-printed (prints/) | 1 board, owned/none | 1 / 1 | $1.00 | $1.00 | Shared | est. |
| **Subtotal Shared** | | | | **$67.71** | **$81.49** | | |
| **TOTAL without filament** | | | | **$210.78** | **$248.04** | | |
| *Next iteration, bought or printed, not fitted (not counted above)* | 687 bearings 2 per station, Ø7 dowel 1 per station, printed 18T pinion and 54T spool-gear (D40–D42) | | 6 / 8 bearings, 3 / 4 pins | *$6.60* | *$8.80* | Next iteration | est. |

Per station (3-station build): about $23.70 of station-only parts plus a share of the shared rows.

Wiring estimate inside the totals: 16 AWG 12 V pairs 65 ft (3 st) / 94 ft (4 st) of the 100 ft roll (cut list
`docs/POWER_WIRE_CUT_LIST_20261021.md`: 9 + 26 + 24 + 35 ft; the mid-wall C in three-station mode is taken as ~30 ft);
22–24 AWG hookup ~4 m per station and ~2 m in the claw; Dupont and breadboard jumpers as counted above.

## 2. Filament (separate)

Solid CAD volumes come from `exports/stl` (computed here) and `docs/decisions/WEIGHT_REDESIGN_PROPOSAL_20261022.md`
(Jasper's SolidWorks station parts). Printed mass = solid volume × 1.27 g/cm³ × a fill factor guessed per part type
(0.20 mm layers, 3 walls, ~20 % infill, supports at 30°). No slicer output is recorded, so these are estimates.

| Part | Solid volume | Solid PETG | Fill factor | Printed (est.) | Per build |
|---|---:|---:|---:|---:|---|
| Wall mount (SolidWorks) | 597 cm³ | 758 g | 0.35 | 265 g | per station |
| Slide-in motor mount (SolidWorks) | 218 cm³ | 277 g | 0.45 | 125 g | per station |
| Shell (SolidWorks) | 352 cm³ | 447 g | 0.80 | 358 g | per station |
| Spool, direct drive (Spoolv3: Ø36 × 22, Ø15 core; estimated here) | 9 cm³ | 11 g | 0.85 | 10 g | per station |
| Magnet cap | ~1 cm³ | 1 g | 1.00 | 1 g | per station |
| *Next iteration, printed, not fitted: spool-gear54 (23 cm³, 25 g) and pinion18 (4 cm³, 5 g)* | | | | *30 g per station* | not counted |
| Encoder casing + cap (`encoder1021_*`) | 3.9 cm³ | 5 g | 1.00 | 5 g | per station |
| **Station total** | about 1,180 cm³ | | | **762 g** | ×3 = 2.29 kg, ×4 = 3.05 kg |
| Claw printed parts (gear housing ×2, electrical housing + bay + cover + lid, hands, cylinder); STL check: housing_cambay_34 154.6 cm³, hands 17.0 ×2, lid 12.4, cover 4.3, gears 44.7 + 22.7 + 8.0 | 677 cm³ (weight proposal) | 860 g | ~0.27 | **230 g** | once (Jasper weighed the claw at 0.60 kg with battery: minus tube 198 g, servo 55 g, battery 99 g, electronics ~20 g) |
| **In the robot** | | | | **2.52 kg (3 st) / 3.28 kg (4 st)** | |

| Filament cost | 3 stations | 4 stations |
|---|---:|---:|
| At $15/kg (SUNLU 4 kg pack, est. $60) | $37.74 | $49.17 |
| At $20/kg (SHOPPING_LIST PETG price) | $50.32 | $65.56 |

Everything printed, including prototypes, is more: gen-1 `corner_mount` plates (89 g each, one built), the gen-2 shells in
clear, grey, red and blue (photos 04, 27, 35), the v6/v7 gripper iterations, test coupons, a kept failed layer (photo 35),
and supports. A fair guess is 2× the in-robot mass, i.e. the whole 4 kg SUNLU pack plus some of Jasper's PLA. TPU 95A was
never recorded as ordered; the gen-2 hands are PETG (D32), so no TPU is in the build.

## 3. Everything ordered, versus what is used

One row per order line (the same rows as `docs/cost_breakdown_20261026.csv`). 'Used in final build' is for the 3-station
build; the 4-station usage and value are in the CSV. Items whose order is not recorded but which are physically in the
build (bearings, shaft, magnets, tube, wood screws, switch, hookup wire) are included with estimated prices and say so.

| Item | Product | Pack | Price | Evidence | Used in final build? | Prorated used (3 st) |
|---|---|---|---:|---|---|---:|
| NEMA 17 stepper | SIMAX3D NEMA 17 42-38, 36 N·cm, 1.5 A (5-pack) | 5 motor | $33.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly 3 of 5 motor | $19.80 |
| A4988 driver carrier | ACEIRMC CNC Shield V3 + 4× A4988 with heatsinks | 4 A4988 carrier | $10.00 | recorded; delivered Aug 7 | partly 3 of 4 A4988 carrier | $6.00 |
| Station controller: XIAO ESP32-C3 | Seeed XIAO ESP32-C3 (3 boards, Amazon) | 3 board | $18.00 | est.; delivered Oct 12 | partly 2 of 3 (1 fried, T29) | $12.00 |
| Station controller: ELEGOO ESP32 DevKit | ELEGOO ESP-WROOM-32 USB-C dev board (3-pack) | 3 board | $16.00 | recorded; SHOPPING_LIST ✅, delivered Aug 13 | partly 1 of 3 (station replacing the fried XIAO) | $5.33 |
| Station 5 V buck | DROK adjustable buck converter, 4.5–20 V in (6-pack) | 6 module | $16.00 | est.; delivered Oct 13 | partly 3 of 6 module | $8.00 |
| AS5600 encoder board | UMLIFE AS5600 magnetic encoder boards (5-pack, 10/19 cart) | 5 board | $12.00 | est.; 10/19 cart; in use on the bench 10/22 | partly 3 of 5 board | $7.20 |
| Ø4 encoder magnet (diametric) | Ø4 × ~2.5 mm diametric magnets (pack of 10, order not recorded) | 10 magnet | $7.00 | est.; order not recorded (D43: measured Ø4.0 on 10/22) | partly 3 of 10 magnet | $2.10 |
| Homing / end-stop switch | HiLetgo KW12-3 roller micro switch (10-pack) | 10 switch | $6.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly 3 of 10 switch | $1.80 |
| 687 bearing (7×14×5) | 687ZZ bearings, 7×14×5 mm (pack of 20, order not recorded) | 20 bearing | $12.00 | est.; order not recorded (4 in the claw gear housing 10/22; 2 per station in the next-iteration gear stage) | partly 4 of 20 bearing | $2.40 |
| Ø7 steel shaft / dowel pin | Ø7 h6 steel dowel pins ~50–55 mm (pack of 10, order not recorded) | 10 pin | $10.00 | est.; order not recorded | no: next iteration (gear-stage spool shaft) | $0.00 |
| Blade fuse holder + fuse | SIM&NAT inline ATC/ATO holders (10) + 50 blade fuses | 10 holder+fuse | $12.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly 5 of 10 holder+fuse | $6.00 |
| WAGO 221 lever nuts | WAGO 221 assortment 2401/412/413/415 (12 pcs) | 12 connector | $12.00 | est.; delivered Oct 15 | partly 8 of 12 connector | $8.00 |
| 100 µF / 50 V capacitor (C1 at VMOT) | JCCON 100 µF 50 V electrolytic (10) | 10 cap | $6.00 | est.; delivered Oct 15 | partly 3 of 10 cap | $1.80 |
| 1N5819 Schottky diode (D1) | EEEEE 1N5819 DO-41 (150) | 150 diode | $6.00 | est.; delivered Sep 4 | partly 4 of 150 diode | $0.16 |
| 10 kΩ pull resistors ×4, 100 nF, 100 kΩ, breadboard, jumpers | from the ELEGOO UNO R3 Super Starter Kit | 1 kit | $45.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly (breadboard, jumpers, resistors; the Uno itself is gen 1, unused) | $8.00 |
| FR4 perfboard 5×7 cm | FR4 perfboards (pack of 34, 10/19 cart) | 34 board | $10.00 | est.; 10/19 cart; soldered board in photo 19 | partly 1 of 34 board | $0.29 |
| Breadboard jumper kit | solid jumper kit, 840 pcs (10/19 cart) | 840 jumper | $8.00 | est.; 10/19 cart | partly 75 of 840 jumper | $0.71 |
| Dupont jumper wires | female-male Dupont jumpers, 120 pcs (10/19 cart) | 120 jumper | $7.00 | est.; 10/19 cart | partly 20 of 120 jumper | $1.17 |
| 12 V power supply | ALITOVE 12 V 6 A 72 W (barrel plug cut off 8/28) | 1 PSU | $16.00 | recorded; SHOPPING_LIST ✅ | fully | $16.00 |
| 16 AWG 12 V distribution wire | 16 AWG red/black pure-copper paired cable, 100 ft (10/19 cart) | 100 ft | $30.00 | est.; 10/19 cart; cut list 10/21 assumes it on hand | partly 65 of 100 ft | $19.50 |
| 22–24 AWG hookup / signal wire | station 12 V leads from the WAGO, motor and switch tails, encoder leads (hookup wire; order not recorded) | 30 m | $9.00 | est.; order not recorded (SHOPPING_LIST ☐ 22 AWG silicone $9) | partly 14 of 30 m | $4.20 |
| #10 × 3 in wood screws | #10 × 3 in exterior wood screws (box of ~50) | 50 screw | $8.00 | recorded; order not recorded (SHOPPING_LIST ☐, ~$8) | partly 18 of 50 screw | $2.88 |
| M3 hardware | MroMax 640-pc M3 button-head kit, 304 SS | 640 pc | $10.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly 60 of 640 pc | $0.94 |
| M3 heat-set inserts | INCLY heat-set insert kit, M2–M6, 580 pcs + tool | 580 insert | $12.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly 26 of 580 insert | $0.54 |
| Aluminium heat fin, 0.019 in | 0.019 in aluminium sheet, sheared and milled (stock on hand, D38) | 1 sheet | $0.00 | est.; material already on hand (D38) | fully | $2.00 |
| Claw controller + camera | Seeed XIAO ESP32-S3 Sense | 1 board | $13.99 | recorded; delivered Oct 13 (Seeed list price; Amazon price not recorded) | fully | $13.99 |
| Gripper servo | Deegoo-FPV MG996R 180° (4-pack) | 4 servo | $18.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly 1 of 4 servo | $4.50 |
| Claw battery | Tenergy 7.4 V 2200 mAh 2S1P Li-ion with protection PCB (31003) | 1 pack | $18.49 | recorded; 10/19 cart; in the claw housing (photo 40) | fully | $18.49 |
| Servo 6 V regulator | ZTW 6 A UBEC, screenless, set to 6.0 V | 1 module | $14.99 | recorded; 10/19 cart; in the claw housing (photo 40); reference price $14.99 | fully | $14.99 |
| XIAO 5 V buck | EBOOT MP1584EN buck (6-pack) | 6 module | $9.00 | recorded; SHOPPING_LIST ✅, delivered Aug 13 | partly 1 of 6 module | $1.50 |
| USB-C 2S charger (U4) | Type-C 2S 8.4 V 1 A charging module, 2S1A (pack of 2, 10/19 cart) | 2 module | $8.00 | est.; 10/19 cart; receipt not recorded | partly 1 of 2 module | $4.00 |
| 1000 µF / 16 V capacitor (C1) | 1000 µF 16 V electrolytic (pack of 15, 10/19 cart) | 15 cap | $7.00 | est.; 10/19 cart; one visible on a station breadboard (photo 31) | partly 2 of 15 cap | $0.93 |
| 100 nF ceramic (C2–C4) | 100 nF '104' ceramic (pack of 100, 10/19 cart) | 100 cap | $6.00 | est.; 10/19 cart | partly 3 of 100 cap | $0.18 |
| Divider resistors 200 kΩ / 100 kΩ | 200 kΩ + 100 kΩ 1 % metal film (ELEGOO kit or two 100 k in series) | 1 set | $0.00 | est.; from the ELEGOO kit | fully | $0.20 |
| Main switch SW1 | SPST rocker/toggle ≥ 5 A DC (multipack, order not recorded) | 5 switch | $6.00 | est.; order not recorded (BREADBOARD_PARTS: 'search') | partly 1 of 5 switch | $1.20 |
| Aluminium tube | 1-1/8 in OD aluminium tube, 12 in, cut to 10.48 in (D36; order not recorded) | 1 tube | $12.00 | est.; order not recorded | fully | $12.00 |
| Dyneema line | 9KM DWLIFE X8 braided Dyneema 120 lb, 150 m | 150 m | $8.00 | recorded; SHOPPING_LIST ✅, delivered Aug 7 | partly 18.3 of 150 m | $0.98 |
| Floor board (AprilTag sheets) | 9 Letter sheets, home-printed (prints/) | 1 board | $0.00 | est.; home printer | fully | $1.00 |
| PETG filament | SUNLU grey PETG, 4 kg pack | 4000 g | $60.00 | est.; delivered Oct 15 | filament, see §2 | $38.70 |
| Overhead webcam (gen 1) | innomaker 1080p 130° USB UVC board | 1 cam | $19.00 | recorded; SHOPPING_LIST ✅ | no: gen 1 (retired by D33) | $0.00 |
| CNC Shield V3 board (gen 1) | (the shield from the ACEIRMC kit; valued in the A4988 row) | 1 shield | $0.00 | recorded; delivered Aug 7 | no: gen 1 (central Uno architecture superseded by D17) | $0.00 |
| Arduino Uno (gen 1) | (the Uno from the ELEGOO starter kit; kit valued above) | 1 board | $0.00 | recorded; delivered Aug 7 | no: gen 1 (D17) | $0.00 |
| ACEIRMC Type-C 2S 2A boost/charger boards | ACEIRMC USB 2S boost/charging boards (2) | 2 module | $9.00 | est.; delivered Aug 13 | no: spare (CN3302 board charges ~1.2 A, over the Tenergy 1 A limit; not approved) | $0.00 |
| DF9-16 force sensors | DF9-16 20 g–2 kg FSR (2) | 2 sensor | $12.00 | est.; delivered Oct 13 | no: spare (Rev B dropped the FSR) | $0.00 |
| XT60H connectors | XT60H male/female pairs (10) | 10 pair | $9.00 | est.; delivered Oct 15 | no: spare (Rev B uses WAGOs; could become the battery disconnect) | $0.00 |
| 1S LiPo | JLJLUP protected 3.7 V 2000 mAh, PH2.0 | 1 pack | $10.00 | est.; delivered Sep 3 | no: other project (1S cannot feed the 2S claw) | $0.00 |
| MT3608 boost modules | MT3608 (5) | 5 module | $7.00 | est.; delivered Sep 3 | no: spare | $0.00 |
| IRLZ44N MOSFETs | IRLZ44N N-channel (10) | 10 pc | $8.00 | est.; delivered Sep 3 | no: spare | $0.00 |
| IRF4905 MOSFETs | IRF4905 P-channel (10) | 10 pc | $8.00 | est.; delivered Sep 4 | no: spare | $0.00 |
| 6 V solenoid | Hechen HS-0730B | 1 pc | $8.00 | est.; delivered Sep 3 | no: other project | $0.00 |
| Digital multimeter | DMM with leads | 1 tool | $15.00 | est.; delivered Aug 13 | no: tool | $0.00 |
| Soldering iron kit | 80 W adjustable soldering iron kit | 1 tool | $20.00 | recorded; SHOPPING_LIST ☐ ($20); delivered Aug 12 | no: tool | $0.00 |
| **TOTAL ORDERED** | | | **$637.47** | recorded $289.47 + est. $348.00 | | |
| **TOTAL USED (prorated, no filament)** | | | | | | **$210.78** (4 st: $248.04) |
| Filament used (prorated) | | | | | | $37.74 (4 st: $49.17) |
| **Spares, gen-1 parts, next-iteration parts and tools on the shelf** | | | | | | **$388.95** (4 st: $340.26) |

Biggest shelf items: the ELEGOO starter kit remainder (~$37), SUNLU PETG not in the robot (~$23), the two spare ELEGOO ESP32s
and the spare MG996Rs (~$24), the tools ($35), the webcam ($19), the spare motor (~$7), and the 10/19 cart passives.

**Ordered per the record but not listed above because the record says they were never bought:** eye hooks (removed from the
BOM before ordering, D13), the Adafruit MPU-6050 IMU ('not recorded ordered'), the U-groove corner pulleys, the Ronstan
rings, OVONIC LiPo, B3 charger, raceway, stepper extensions, limit-switch wire, zip ties, M2 screws, stopper beads and the
Grove AS5600 / Seeed-store XIAO C3 lines of the Oct-1 encoder BOM (SHOPPING_LIST ☐ rows; `BOM_ENCODER_TILT.csv` 'Not ordered').
If any of those were in fact bought, add the row to the CSV; they would all be 'no: gen 1 / spare'.

## 4. Assumptions and unknowns (for Jasper)

Prices not recorded anywhere in the repo (estimated here, marked est.): XIAO ESP32-C3 3 boards ($18), DROK 6-pack ($16),
WAGO 221 12-pc ($12), XT60H ($9), JCCON 100 µF ($6), 1N5819 150 ($6), DF9-16 ($12), SUNLU PETG 4 kg ($60), 1S LiPo ($10),
ACEIRMC 2S boards ($9), MT3608 ($7), MOSFETs ($8 + $8), solenoid ($8), multimeter ($15), the whole 10/19 cart except the
Tenergy pack and UBEC (AS5600 5-pack $12, 1000 µF $7, 100 nF $6, 16 AWG 100 ft $30, perfboards $10, Dupont $7, jumper kit $8,
USB-C 2S1A charger 2-pack $8), 687 bearings ($12/20), Ø7 pins ($10/10), Ø4 magnets ($7/10), aluminium tube ($12), SW1 ($6/5).
Recorded prices are themselves the shopping list's 2026 estimates (±20 %), not receipts. Replace both from the Amazon order
history and the totals update by editing the CSV.

1. **Orders not in the record:** 687 bearings, Ø7 shaft/pins, Ø4 magnets, the aluminium tube, wood screws, hookup wire and
   the claw switch are in the build (10/22–10/26 notes and photos) but no order line exists. Pack sizes are guesses.
2. **10/19 cart receipt:** the UBEC, Tenergy pack, 1000 µF, 16 AWG and UMLIFE AS5600s are seen in later notes or photos, so
   the cart is treated as ordered. The USB-C 2S1A charger, 100 nF, perfboards, Dupont and jumper kits are assumed to have
   come with it; `BREADBOARD_PARTS.md` (10/25) still links the charger and 1000 µF as 'search', so confirm.
3. **Station count and controllers:** three stations with 2 × XIAO C3 + 1 × ELEGOO (one XIAO fried, T29). A fourth station
   would use the second ELEGOO. If station D is in fact mounted, use the 4-station column.
4. **Winch 3:1 stage (resolved 10/27, Jasper):** the gear stage is the next iteration; the mounted stations are direct-drive
   spools on the motor shaft (photos 28, 39, 44). Its 687s (2 per station), Ø7 shafts and printed gears are listed as
   "next iteration, not fitted" and are not in the robot totals; the claw's 4 bearings are.
5. **Dyneema:** 6.1 m per run (5.1 m room diagonal + dead wraps + slack) → 18.3 m / 24.4 m of 150 m. Actual cut lengths not
   recorded.
6. **Wire:** 16 AWG from the cut list (94 ft for four; ~65 ft for A, B and a mid-wall C); 22–24 AWG hookup ~4 m per station
   and 2 m in the claw, and the ELEGOO kit's jumpers, are guesses. The cut list says 6 ft of the 100 ft roll is spare.
7. **Counts of M3 screws, inserts, WAGOs, wood screws and jumpers** are estimates from the CAD and layouts (notes in the CSV).
8. **Filament:** no slicer weights are recorded. Fill factors 0.35 (wall mount block), 0.45 (slide-in), 0.80 (shell) and the
   230 g claw figure (from the 0.60 kg weighing) could each be ±30 %. Read the slicer's filament estimate for one station and
   scale.
9. **Fuse count:** one 7.5 A main + one 3 A branch per station + the claw 5 A, all in SIM&NAT holders (5 of 10 holders).
10. **ELEGOO starter kit:** valued at $8–9 used (breadboards, resistors, 104 caps, jumpers); the Uno is unused. The CNC shield
    board is valued at $2 of its $10 kit and unused; the A4988 carriers at $2 each.
11. **XIAO S3 Sense** price is the Seeed list price ($13.99); the Amazon price paid is not recorded.
12. **Seeed-store items of the Oct-1 encoder BOM** (Grove AS5600 at $6.50, XIAO C3 at $4.90, D42DIA magnets) were never
    ordered; the Amazon UMLIFE boards, Amazon XIAO C3s and Ø4 magnets replaced them.
13. The 1N5819 pack (150), 100 nF (100), jumper kits and M3 kit are so large that their prorated values are cents; they are
    kept for completeness.

Sources: `docs/SHOPPING_LIST.md`, `docs/BOM_ORDER.md`, `docs/INVENTORY_RECONCILIATION_20261014.md`, `docs/REVISION_V2_DECISIONS.md`,
`docs/ORDER_STATUS_V2.csv` and `docs/BOM_ENCODER_TILT.csv` (deleted in 4375d26, read from git history), `docs/history/claw_cost_review_20261018.md`,
`docs/history/claw_compact_power_proposal_20261018.md`, `docs/history/REVIEW_HANDOFF_20261019.md` (10/19 cart), `docs/electrical/station_revD_20261021/*.md`,
`docs/electrical/claw_revB_20261021/CLAW_REVB_SPEC.md` and `BREADBOARD_PARTS.md`, `docs/POWER_WIRE_CUT_LIST_20261021.md`, `docs/POWER_WIRE_SELECTION_20261014.md`,
`docs/presentation/DECISION_STORIES.md` (T28, T29, T37), `docs/presentation/photos/README.md`, `DECISIONS.md` (D17, D31–D33, D36–D43), `DESIGN_STATE.md` (10/21–10/26),
`docs/decisions/WEIGHT_REDESIGN_PROPOSAL_20261022.md`, `verification/gripper1021_build_notes.md`, `verification/winch_gear3_verification.md`, `exports/stl/*`.
`docs/FRESH_PARTS_DELTA_20261002.md` is referenced by other docs but never existed in git history.
