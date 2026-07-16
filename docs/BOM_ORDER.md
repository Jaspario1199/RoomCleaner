# RoomCleaner — Complete Orderable Checklist (Amazon US)

A single cart-ready list. Prices are 2026 estimates (±20%) — **Amazon blocks
automated price/stock checks, so confirm specs and price at checkout.** Links are
representative products from research; if one is dead, use the search term next to
it.

> **3D printing:** the winch spools and the recommended gripper are ideally
> printed. If you have no printer, use the **"no-printer swap"** noted on those
> lines — then the whole list is Amazon-orderable.

## A. Motion (motors + winches)

| ✓ | Item | Spec / search term | Qty | ~$ea | Link |
|---|------|--------------------|-----|------|------|
| ☐ | Winch motor | 12V worm-gear DC, self-locking, ~20-30 RPM, encoder — "uxcell self-locking gear motor encoder" | 4 | 32 | https://www.amazon.com/uxcell-50Kg-cm-Self-Locking-Encoder-Reduction/dp/B078J521TG |
| ☐ | Motor driver | BTS7960 / IBT-2 — "BTS7960 motor driver" | 4 | 10 | https://www.amazon.com/HiLetgo-BTS7960-Driver-Arduino-Current/dp/B00WSN98DC |
| ☐ | Cable (line) | Braided Dyneema/UHMWPE 100-200 lb — "hollow braid dyneema 100lb" | 1 spool | 13 | https://www.amazon.com/9KM-DWLIFE-Anti-Bite-Freshwater-Saltwater/dp/B0DLNQFQKK |
| ☐ | **Winch spool** | *Print it.* **No-printer swap:** aluminum shaft hub/drum matched to your motor shaft — "aluminum motor shaft coupling hub 6mm" | 4 | 3 | search |
| ☐ | Corner pulleys | Micro pulley w/ bearing — "small pulley wheel bearing 3mm bore" | 4 | 3 | search |
| ☐ | Ceiling anchors | 304 stainless screw eyes (into joists) — "304 stainless screw eye" | 1 pk | 8 | https://www.amazon.com/Stainless-Steel-Screws-Heavy-Inches/dp/B08SVMJ6NZ |

## B. Compute + control

| ✓ | Item | Spec / search term | Qty | ~$ea | Link |
|---|------|--------------------|-----|------|------|
| ☐ | Vision brain | Raspberry Pi 5 **4 GB** — "Raspberry Pi 5 4GB" | 1 | 80 | https://www.amazon.com/Raspberry-Pi-8GB-SC1112-Quad-core/dp/B0CK2FCG1K |
| ☐ | Pi power supply | Official 27 W USB-C — "Raspberry Pi 5 27W USB-C power supply" | 1 | 12 | search |
| ☐ | microSD | 32 GB A2 — "SanDisk 32GB A2 microSD" | 1 | 9 | search |
| ☐ | Motor MCU | ESP32 DevKit (2-pk, use 1) — "ESP32 DevKitC 2 pack" | 1 | 13 | https://www.amazon.com/MELIFE-ESP32-DevKitC-Development-ESP32-WROOM-32U-Arduino/dp/B0811KLGDD |
| ☐ | Home switches | KW12-3 micro limit switch (10-pk) — "KW12-3 limit switch" | 1 pk | 8 | https://www.amazon.com/HiLetgo-KW12-3-Roller-Switch-Normally/dp/B07X142VGC |

## C. Power + safety (do not skimp)

| ✓ | Item | Spec / search term | Qty | ~$ea | Link |
|---|------|--------------------|-----|------|------|
| ☐ | Power supply | 12V 30A 360W enclosed SMPS — "12V 30A power supply" | 1 | 28 | https://www.amazon.com/SUPERNIGHT-Universal-Transformer-Industrial-Automation/dp/B007MWNF5Q |
| ☐ | **E-STOP button** | 22 mm latching mushroom, **NC** — "22mm emergency stop latching NC" | 1 | 10 | https://www.amazon.com/Uxcell-a14122300ux0109-Emergency-Latching-Mushroo/dp/B00W947PS0 |
| ☐ | Power contactor | 30-40A relay/contactor the e-stop drops to cut motor rail — "40A DC contactor" or "Bosch 30A relay" | 1 | 12 | search |
| ☐ | Fuse + holder | Inline 30A automotive — "inline 30A fuse holder" | 1 | 8 | search |
| ☐ | 5V buck converter | MP1584 or LM2596 (3-pk) for servo/logic — "LM2596 buck converter 3 pack" | 1 pk | 8 | search |

## D. Perception + gripper

| ✓ | Item | Spec / search term | Qty | ~$ea | Link |
|---|------|--------------------|-----|------|------|
| ☐ | Camera | Logitech C920/C920x 1080p USB — "Logitech C920x" | 1 | 55 | https://www.amazon.com/Logitech-C920x-Pro-HD-Webcam/dp/B085TFF7M1 |
| ☐ | Gripper servo | MG996R metal-gear (4-pk) — "MG996R servo 4 pack" | 1 pk | 11 | https://www.amazon.com/4-Pack-MG996R-Torque-Digital-Helicopter/dp/B07MFK266B |
| ☐ | **Gripper body** | *Print the spatula-scoop + Fin Ray flap.* **No-printer swap (starter):** off-the-shelf MG996R metal claw — "MG996R robot metal claw gripper" | 1 | 15 | https://www.amazon.com/Mechanical-Robotic-Gripper-MG996R-Steering/dp/B099W5R2NP |
| ☐ | TPU filament | *(only if printing the Fin Ray flap)* — "TPU 95A filament 1kg" | 1 | 20 | search |

## E. Wiring + enclosure

| ✓ | Item | Spec / search term | Qty | ~$ea | Link |
|---|------|--------------------|-----|------|------|
| ☐ | Dupont jumpers | M-M/M-F/F-F assortment — "dupont jumper wire kit" | 1 | 7 | search |
| ☐ | Hookup wire | 18 AWG silicone, 2-color — "18AWG silicone wire red black" | 1 | 10 | search |
| ☐ | Project box | ABS enclosure — "ABS project box electronics" | 1 | 12 | search |
| ☐ | Mounting hardware | Corner brackets, screws, zip ties — "L bracket screw assortment" | 1 | 15 | search |

---

## Totals

- **Reliable build (this list): ~$515** with printed spools/gripper; **~$540** with
  the no-printer swaps.
- **Budget build (~$250):** swap the 4 worm-gear motors → NEMA 17 steppers + a
  RAMPS board, reuse a laptop for vision, SG90 servo. **Accept:** steppers lose
  steps under shock, no vision on RAMPS, SG90 gears strip. See `HARDWARE.md`.

## Do NOT skimp here (repeat, because it matters)
- **Motor rail must be cut by the e-stop through the contactor** — not just a
  signal to the MCU. Software hangs; the latch doesn't.
- **Anchor into joists/solid blocking, never drywall** — cable tension multiplies
  the load and rips out drywall anchors.
- **Real low-stretch Dyneema** — cheap PE/mono line stretches and your position
  drifts.
- **MG996R, not SG90** for the gripper — plastic gears shear on a wet towel.

## The two things this list can't fully solve for you
1. **Spool/gripper printing.** The no-printer swaps work but are compromises (the
   off-the-shelf claw is a starter you'll want to add a scoop edge to). A cheap 3D
   printer or a print service closes this properly.
2. **Exact motor-shaft fit** for the spool hub — measure your chosen motor's shaft
   diameter before ordering the hub.
