# RoomCleaner — Shopping List (exact products + links)

The "shirts & jeans" build, with a specific product and direct link for every
line. **Links are real listings, but Amazon blocks automated price/stock checks —
confirm the live price and that you've picked the right variant at checkout.**
Where a link rotates, use the search fallback.

Legend: 🟢 buy · ⚙️ reuse/own · ⬆️ optional upgrade

---

## Motion

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | NEMA 17 stepper ×4 (+1 spare) | SIMAX3D NEMA 17 **42-38** size, ~36 N·cm, 1.5 A, 5 mm shaft (**5-pack**) — select the **42-38** option | https://www.amazon.com/s?k=SIMAX3D+Nema+17+42-38+5pcs | 33 |
| ☐ | Cable/line | 9KM DWLIFE X8 braided Dyneema, **50 lb**, 150 m (select 50 lb, not 8 lb) | https://www.amazon.com/9KM-DWLIFE-Anti-Bite-Freshwater-Saltwater/dp/B0DLNQFQKK | 8 |

*Note: at 0.8–1.2 mm, UHMWPE line naturally rates ~200–350 lb (not 100) — that's a bonus: more abrasion life, still low-stretch.*

## Control electronics

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Arduino Uno **+ project stock** | **ELEGOO UNO R3 Super Starter Kit** — genuine-quality Uno clone + 200+ components (breadboard, jumpers, sensors, LCD, power module, resistors, LEDs). The Uno runs the winches; the rest is your parts bin for future projects | https://www.amazon.com/ELEGOO-Project-Tutorial-Controller-Projects/dp/B01D8KOZF4 | 45 |
| ☐ | CNC shield + drivers | **ACEIRMC CNC Shield V3 + 4× A4988** (heatsinks incl.) — plugs onto the Uno above | https://www.amazon.com/s?k=ACEIRMC+CNC+shield+V3+A4988 | 10 |
| ☐ | Home switches | HiLetgo KW12-3 micro limit switch, 1NO 1NC roller lever (10-pack) — wire Common + NC for fail-safe homing | https://www.amazon.com/HiLetgo-KW12-3-Roller-Switch-Normally/dp/B07X142VGC | 6 |

*Why this replaced the sold-out DAOKI kit: you plan an array of projects, so the extra ~$28 buys a whole component library instead of a bare no-name Uno clone. **Budget alternative** if you'd rather match the old price: Sevenmore CNC Shield + UNO R3 + 4× DRV8825 kit (~$23–27, the closest 1:1 DAOKI substitute): https://www.amazon.com/Arduino-Printer-Sevenmore-Shield-DRV8825/dp/B07PXWBQTQ*

*Driver note (A4988 path): the ACEIRMC A4988s drive our motors fine **derated to ~1.0–1.2 A** — still >2× torque margin at our ≤40 N cable loads, and their 1/16 microstep max exactly matches firmware `MICROSTEP=16`. Set Vref ≈ **0.8 V per amp** (typical 0.1 Ω sense resistors → 0.8 V for 1.0 A, 0.96 V for 1.2 A) — this differs from DRV8825 (0.75 V ≈ 1.5 A). ⬆️ Optional: HiLetgo **DRV8825 5-pack** (~$12, https://www.amazon.com/dp/B01NCE3ZW1) for full 1.5 A + cooler running + a spare. **4-axis caveat (any CNC shield):** the stock 4th "A" slot clones another axis; our custom firmware drives all 4 independently via the step/dir pins (incl. D12/D13), so this is fine for us.*

## Power + protection

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | 12 V power supply | ALITOVE 12V **6A** 72W barrel adapter (4.6★, extra headroom) — *or Chanzon 12V 5A if you want a UL-listed unit (~$20)* | https://www.amazon.com/s?k=ALITOVE+12V+6A+72W+power+supply | 16 |
| ⚙️ | Barrel → screw-terminal | **Cut the barrel plug off the ALITOVE and land the bare leads in the shield's screw terminal (free).** Prefer not to cut? Female barrel-jack→screw-terminal adapter, ~$7/pack: https://www.amazon.com/s?k=female+DC+barrel+jack+screw+terminal+adapter | — | 0 |
| ☐ | Inline fuse + fuses | SIM&NAT inline holder + 50 blade fuses (4.7★) — install a **7.5 A** fuse (matches the 6 A supply) | https://www.amazon.com/SIM-NAT-Automotive-Standard-Replacement/dp/B07FQCBSJ5 | 12 |
| ⚙️ | Kill switch | **Your switched power strip** — plug the 12 V PSU into it | — | 0 |

*Wiring order: PSU → barrel adapter → **fuse on the + lead** → CNC-shield power terminal. (You can also just cut the PSU barrel off and skip the adapter → save $8.)*

## Perception + gripper

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Overhead webcam | innomaker 1080P **130° wide** USB UVC (OpenCV plug-and-play). Bare 32×32 board — print `cad/camera_mount_overhead` (no $14 case needed) + one-time lens-undistort calibration | https://www.amazon.com/innomaker-Computer-Raspberry-Support-Windows/dp/B0CNCSFQC1 | 19 |
| ☐ | Gripper servo | **STANDARD 180° MG996R, 4-pack** (best value, 3 spares — servo is the most wear-prone part). ⚠️ NOT "360°"/continuous. On the **wireless effector**, powered from its onboard battery via a buck | https://www.amazon.com/s?k=Deegoo-FPV+MG996R+4+pack | 18 |

### Wireless effector (the claw is a self-contained WiFi node — no wire to it)
The gripper servo lives on the effector with an ESP32 + battery, commanded over
WiFi. Only the 4 Dyneema cables touch the claw. See `docs/FIRMWARE.md`.

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Effector brain | MELIFE ESP32-DevKitC (2-pack: one for the claw + a spare) | https://www.amazon.com/MELIFE-ESP32-DevKitC-Development-ESP32-WROOM-32U-Arduino/dp/B0811KLGDD | 13 |
| ☐ | Battery | OVONIC 2S 7.4V 1000 mAh LiPo, JST (2-pack) | https://www.amazon.com/OVONIC-1000mAh-Battery-Truck-Truggy/dp/B07CVBJ3SL | 16 |
| ☐ | Servo 5–6V buck | EBOOT MP1584EN buck (6-pack) — set output to 6.0 V for the servo | https://www.amazon.com/MP1584EN-DC-DC-Converter-Adjustable-Module/dp/B01MQGMOKI | 9 |
| ☐ | LiPo charger | Simple **2S USB LiPo charge board** (8.4 V) — search; ~$8. *(Or, if you get a hobby balance charger like an iMax B6, a parallel board works.)* | https://www.amazon.com/s?k=2S+lipo+USB+charger+board+8.4V | 8 |
| ☐ | Power switch | Small SPST slide/rocker switch (multipack) — flip the effector on per session | https://www.amazon.com/s?k=mini+SPST+slide+switch | 5 |

> **Power strategy:** start with the switch above (on for a session, off when
> idle). The long-run end-state is a **charging dock at the rest pose** so the
> claw tops up whenever it parks — build that in Phase 4 once your layout is set.
> This solves the ESP32's ~100 mA always-on WiFi drain by charging while idle.

### Full-room-rig wiring additions (measure your room first!)
| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Cord raceway (hide the wires) | D-Line paintable self-adhesive raceway, 157" — buy enough for your ceiling perimeter | https://www.amazon.com/D-Line-Self-Adhesive-Channels-Accessories-Management/dp/B08563XMS5 | 25 |
| ☐ | Stepper extension | R REIFENG 4× 2 M NEMA 17 extension cables — *verify the connector matches your SIMAX motor cable; for runs > 3 m use bulk 20–22 AWG 4-conductor wire instead* | https://www.amazon.com/REIFENG-Setpper-Motor-Cable-Connectors/dp/B07SHK9YZ5 | 12 |
| ☐ | Limit-switch wire | EvZ 24 AWG 2-conductor, 33 ft (thin, low-current; get more if your runs are long) | https://www.amazon.com/EvZ-Conductor-Temperature-Resistant-Extension/dp/B07GGJDPPJ | 8 |
| ⚙️ | Structural filament | **You have PLA — skip.** (PLA is fine for all the structural parts at ~15 N indoors.) | — | 0 |
| ⚙️ | Vision computer | **Reuse your laptop/PC** | — | 0 |
| ⚙️ | 5 V for servo | **Reuse a 5 V phone charger** | — | 0 |

## Fasteners + structure

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Ceiling anchors ⚠️ | QXSKSLH 5" M10 **stainless, fully-closed-eye** self-tapping hooks, 700 lb, 4-pack (screw into JOISTS, no nut; pilot-drill first) | https://www.amazon.com/s?k=QXSKSLH+5+inch+eye+hooks+M10+stainless | 14 |
| ☐ | M3 screw/nut kit | MroMax 640-pc M3 button-head, 304 stainless (6–30 mm + nuts + washers) — also provides the NEMA 17 mount screws | https://www.amazon.com/MroMax-Stainless-Button-Socket-Screws/dp/B0BZP89FQT | 10 |

## Wiring

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ⚙️ | Dupont jumpers | **Skip — the ELEGOO starter kit above includes jumper wires.** (If you took the Sevenmore budget path instead, add the ELEGOO 120-pc back: https://www.amazon.com/Elegoo-EL-CP-004-Multicolored-Breadboard-arduino/dp/B01EV70C78, $7) | — | 0 |
| ☐ | Hookup wire | 22 AWG silicone stranded, red + black | https://www.amazon.com/Silicone-Electrical-Conductor-Parallel-Flexible/dp/B07K9R9LBV | 9 |
| ☐ | Zip ties | ALBO 500-pk assorted | https://www.amazon.com/Assorted-Sizes-Plastic-Resistant-Colors/dp/B08LNRH2TG | 8 |

## Filament

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | TPU 95A (fingers) | OVERTURE TPU 95A, 1.75 mm, 1 kg | https://www.amazon.com/OVERTURE-Flexible-Printer-Filament-1-75mm/dp/B0991X92K8 | 22 |
| ☐/⚙️ | Structural (if needed) | HATCHBOX PLA 1 kg (PLA is fine at ~15 N indoors) *or SUNLU PETG* | https://www.amazon.com/HATCHBOX-3D-Filament-Dimensional-Accuracy/dp/B00J0ECR5I | 20 |

---

## Totals

| Scenario | ~$ |
|----------|----|
| **Everything above (ELEGOO starter-kit controller path, incl. wireless-effector parts + structural PLA)** | **~$274** |
| If you already own PLA/PETG filament | **~$254** |
| Budget controller path (Sevenmore kit instead of starter kit, dupont jumpers back in) | **−$31** |

*(The wireless claw adds ~$30 — ESP32 + LiPo + charger + buck — to keep any wire from crossing the room to the effector.)*

*(Running savings: the 42-38 5-pack ($33) beat the $54 4-pack (−$21, +spare). Controller history: the $17 DAOKI DRV8825 kit went **sold out** at order time; replaced with ELEGOO starter kit + ACEIRMC shield (~$55, −$7 dupont line) because extra components serve future projects — the Sevenmore DRV8825 kit (~$24) remains the like-for-like budget swap.)*

Honest note: this is **above the earlier ~$184 estimate**. The estimate was rough;
itemizing real products added up — the control *kit* is $24 (not $18), plus a
barrel adapter, a fuse **assortment**, real wiring, and structural filament I
hadn't line-itemed. Nothing changed in scope; the parts just cost what they cost.

## ⬆️ Optional upgrades (only if you want to spend more)

| Upgrade | Product | Link | +$ |
|---------|---------|------|----|
| Heat-set inserts (best reliability upgrade) | INCLY 130-pc M3 inserts + iron tip | https://www.amazon.com/INCLY-Threaded-Insert-Set/dp/B0GXV9XTXC | 12 |
| DRV8825 drivers (full 1.5 A, cooler, +1 spare) | HiLetgo DRV8825 5-pack — drop-in for the ACEIRMC A4988s | https://www.amazon.com/dp/B01NCE3ZW1 | 12 |
| Autofocus webcam | Logitech C920x | *search "Logitech C920x"* | +30 |
| Higher-torque servo | ANNIMOS DS3218 20 kg | https://www.amazon.com/ANNIMOS-Digital-Waterproof-DS3218MG-Control/dp/B076CNKQX4 | +5 |
| Ceramic-bearing corner pulleys ×4 | *search "ceramic bearing pulley 3mm bore"* | — | +12 |

## ⚠️ Safety — the two non-negotiables
- **Ceiling anchors into joists**, metal, derated hard (treat "breaking strength"
  as several× your safe load). Pilot-drill into a real joist, not drywall.
- **The switched power strip is your kill switch** — the 12 V motor supply must
  plug into it so you can cut all motor power instantly.

*Compiled from 6 parallel product-research passes. Prices are 2026 estimates;
verify each at checkout.*
