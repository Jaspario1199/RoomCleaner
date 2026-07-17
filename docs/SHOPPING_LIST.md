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
| ☐ | Controller + drivers (kit) | **DAOKI CNC Shield V3.0 kit**: Arduino Uno + CNC Shield V3 + **4× DRV8825** + heatsinks + USB + DC power cable + jumpers | https://www.amazon.com/s?k=DAOKI+CNC+Shield+V3.0+kit+DRV8825+Arduino | 17 |
| ☐ | Home switches | HiLetgo KW12-3 micro limit switch, 1NO 1NC roller lever (10-pack) — wire Common + NC for fail-safe homing | https://www.amazon.com/HiLetgo-KW12-3-Roller-Switch-Normally/dp/B07X142VGC | 6 |

*Driver note: this kit ships **DRV8825** drivers — cooler-running, finer microstepping, and they drive the 1.5 A motors at full torque. Set each driver's current limit (Vref ≈ 0.75 V for ~1.5 A) before running. **4-axis caveat (any CNC shield):** the stock 4th "A" slot clones another axis; our custom firmware drives all 4 independently via the step/dir pins (incl. D12/D13), so this is fine for us.*

## Power + protection

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | 12 V power supply | ALITOVE 12V **6A** 72W barrel adapter (4.6★, extra headroom) — *or Chanzon 12V 5A if you want a UL-listed unit (~$20)* | https://www.amazon.com/s?k=ALITOVE+12V+6A+72W+power+supply | 16 |
| ✅ | Barrel → screw-terminal | **Covered by the DAOKI kit's DC power cable.** (The ALITOVE 6A ships only a power cord, so rely on the kit cable; if its plug doesn't fit the shield, a $2 barrel→terminal adapter closes the gap.) | — | 0 |
| ☐ | Inline fuse + fuses | SIM&NAT inline holder + 50 blade fuses (4.7★) — install a **7.5 A** fuse (matches the 6 A supply) | https://www.amazon.com/SIM-NAT-Automotive-Standard-Replacement/dp/B07FQCBSJ5 | 12 |
| ⚙️ | Kill switch | **Your switched power strip** — plug the 12 V PSU into it | — | 0 |

*Wiring order: PSU → barrel adapter → **fuse on the + lead** → CNC-shield power terminal. (You can also just cut the PSU barrel off and skip the adapter → save $8.)*

## Perception + gripper

| ✓ | Item | Product | Link | ~$ |
|---|------|---------|------|----|
| ☐ | Overhead webcam | innomaker 1080P **130° wide** USB UVC (OpenCV plug-and-play). Bare 32×32 board — needs a ceiling bracket (print one) + a one-time lens-undistort calibration | https://www.amazon.com/innomaker-Computer-Raspberry-Support-Windows/dp/B0CNCSFQC1 | 19 |
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
| **Everything above (primary picks, single-servo, incl. structural PLA)** | **~$213** |
| If you already own PLA/PETG filament | **~$193** |
| Trimmed (reuse some wire; barrel adapter already free) | **~$178** |

*(Running savings: the 42-38 5-pack ($33) beat the $54 4-pack (−$21, +spare); the DAOKI DRV8825 kit ($17) beat the A4988 kit (−$7, better drivers) and bundles the DC power cable that likely makes the $8 barrel adapter redundant.)*

Honest note: this is **above the earlier ~$184 estimate**. The estimate was rough;
itemizing real products added up — the control *kit* is $24 (not $18), plus a
barrel adapter, a fuse **assortment**, real wiring, and structural filament I
hadn't line-itemed. Nothing changed in scope; the parts just cost what they cost.

## ⬆️ Optional upgrades (only if you want to spend more)

| Upgrade | Product | Link | +$ |
|---------|---------|------|----|
| Heat-set inserts (best reliability upgrade) | INCLY 130-pc M3 inserts + iron tip | https://www.amazon.com/INCLY-Threaded-Insert-Set/dp/B0GXV9XTXC | 12 |
| ~~DRV8825 drivers~~ | **Already included** in the DAOKI kit above | — | 0 |
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
