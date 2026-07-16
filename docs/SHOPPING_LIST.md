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
| ☐ | NEMA 17 stepper ×4 | STEPPERONLINE 17HS19-2004S1, 59 N·cm, 2 A, 5 mm shaft (**4-pack**) | https://www.amazon.com/Stepper-Bipolar-Printer-Machine-Robotics/dp/B07BKRWK1Q | 54 |
| ☐ | Cable/line | 9KM-DWLIFE UHMWPE braid (or emma kites 1 mm, ~350 lb) | https://www.amazon.com/9KM-DWLIFE-Anti-Bite-Freshwater-Saltwater/dp/B0DLNQFQKK | 13 |

*Note: at 0.8–1.2 mm, UHMWPE line naturally rates ~200–350 lb (not 100) — that's a bonus: more abrasion life, still low-stretch.*

## Control electronics

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Controller + drivers (kit) | **kuman K75**: Arduino Uno + CNC Shield V3 + 4× A4988 + heatsinks | https://www.amazon.com/kuman-Expansion-Stepper-Heatsink-Arduino/dp/B06XHKSVTG | 24 |
| ☐ | Home switches | HiLetgo KW12-3 micro limit switch (10-pack) | https://www.amazon.com/HiLetgo-KW12-3-Roller-Switch-Normally/dp/B07X142VGC | 8 |

*Driver note: your motors are 2 A; A4988 (in the kit) practically tops out ~1.2–1.4 A, which still gives ~4 kg·cm — above the ~3 kg·cm this build needs, so the cheap kit is fine. For full torque/quieter motion, see the DRV8825 upgrade below.*

## Power + protection

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | 12 V power supply | Chanzon 12V 5A 60W (UL) — *or Signcomplex 12V 6A for headroom (~$16)* | https://www.amazon.com/110V-220V-Converter-Lighting-Transformer-Flexible/dp/B073QTNF9F | 13 |
| ☐ | Barrel → screw-terminal | Cctv4Less 5.5×2.1 mm female → terminal (multipack) | https://www.amazon.com/Cctv4Less-Connectors-Terminal-Adapter-Security/dp/B077QD4G3Q | 8 |
| ☐ | Inline fuse + fuses | SIM&NAT inline holder + 50 blade fuses (use a **5 A** fuse) | https://www.amazon.com/SIM-NAT-Automotive-Standard-Replacement/dp/B07FQCBSJ5 | 9 |
| ⚙️ | Kill switch | **Your switched power strip** — plug the 12 V PSU into it | — | 0 |

*Wiring order: PSU → barrel adapter → **fuse on the + lead** → CNC-shield power terminal. (You can also just cut the PSU barrel off and skip the adapter → save $8.)*

## Perception + gripper

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Overhead webcam | innomaker 1080P **130° wide** USB UVC (great ceiling FOV, OpenCV plug-and-play) | https://www.amazon.com/innomaker-Computer-Raspberry-Support-Windows/dp/B0CNCSFQC1 | 25 |
| ☐ | Gripper servo | MG996R metal-gear — Treedix 2-pack (spare) *(or Deegoo 4-pack ~$25)* | https://www.amazon.com/Treedix-MG996R-Servo-High-Torque-Helicopter/dp/B08743N181 | 10 |
| ⚙️ | Vision computer | **Reuse your laptop/PC** | — | 0 |
| ⚙️ | 5 V for servo | **Reuse a 5 V phone charger** | — | 0 |

## Fasteners + structure

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Ceiling anchors ⚠️ | 304 stainless lag **eye** screws (into joists) ×4 — National Hardware lag eye (confirm stainless SKU) | https://www.amazon.com/National-Hardware-N220-806-Lag-Screw/dp/B01E60C2X2 | 12 |
| ☐ | M3 screw/nut kit | MroMax 640-pc M3 button-head, 304 stainless (6–30 mm + nuts + washers) | https://www.amazon.com/MroMax-Stainless-Button-Socket-Screws/dp/B0BZP89FQT | 14 |

## Wiring

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Dupont jumpers | ELEGOO 120-pc (M-M/M-F/F-F) | https://www.amazon.com/Elegoo-EL-CP-004-Multicolored-Breadboard-arduino/dp/B01EV70C78 | 7 |
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
| **Everything above (primary picks, single-servo, incl. structural PLA)** | **~$256** |
| If you already own PLA/PETG filament | **~$236** |
| Trimmed (cut PSU barrel instead of adapter −$8, reuse some wire −$15) | **~$215** |

Honest note: this is **above the earlier ~$184 estimate**. The estimate was rough;
itemizing real products added up — the control *kit* is $24 (not $18), plus a
barrel adapter, a fuse **assortment**, real wiring, and structural filament I
hadn't line-itemed. Nothing changed in scope; the parts just cost what they cost.

## ⬆️ Optional upgrades (only if you want to spend more)

| Upgrade | Product | Link | +$ |
|---------|---------|------|----|
| Heat-set inserts (best reliability upgrade) | INCLY 130-pc M3 inserts + iron tip | https://www.amazon.com/INCLY-Threaded-Insert-Set/dp/B0GXV9XTXC | 12 |
| DRV8825 drivers (full 2 A torque, quieter) | HiLetgo DRV8825 5-pack (swap into the CNC shield) | https://www.amazon.com/HiLetgo-DRV8825-Stepper-RAMPS1-4-StepStick/dp/B0FRCQN1P9 | 11 |
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
