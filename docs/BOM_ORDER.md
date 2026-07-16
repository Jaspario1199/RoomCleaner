# RoomCleaner — BOM: what to print, what to buy (base vs. upgrade)

Structure:
- **§0 Printed parts** — free (you have a printer). Files in `cad/`.
- **§1–5 Bought parts** — each line has a **Base** (the minimum that does the job
  well) and, where it's worth it, an **Upgrade → why**.

Prices are 2026 US estimates (±20%); Amazon blocks automated price checks, so
confirm at checkout. Product links + search terms are in `docs/RESEARCH.md` and
`docs/HARDWARE.md`.

---

## §0 — Print these (free)

Everything mechanical that can be printed, is. STEP + STL are in `cad/`. See
`cad/README.md` for materials and print settings.

| Part | Qty | Material | Replaces buying |
|------|-----|----------|-----------------|
| `winch_spool` | 4 | PLA/PETG | winch drums |
| `motor_mount` | 4 | PETG | motor brackets |
| `corner_guide` | 4 | PETG | pulley brackets |
| `effector_frame` | 1 | PETG | end-effector body |
| `tentacle_hub` | 1 | PETG | gripper base |
| `tentacle_finger` | 5 | **TPU 95A** | the whole gripper |
| `camera_mount` | 1 | PLA/PETG | camera bracket |

**Still buy even though you print:** the *pulley wheels* (printed pulleys add
friction — buy bearing pulleys), all *fasteners*, and — critically — the *metal
ceiling anchors* (never printed, see §3).

---

## §1 — Motion (motors + winches)

| Item | Base pick | ~$ (×qty) | Upgrade → why |
|------|-----------|-----------|---------------|
| **Winch motor ×4** | 12V worm-gear **self-locking** DC, ~30 kg·cm, w/ encoder | 32 (×4=128) | **50 kg·cm** version (~$45) → more payload margin, holds heavier/wet loads without straining. *Cheaper-but-risky alt:* NEMA 17 stepper ($12) — **loses steps & drops the load**, only for a bench test. |
| **Motor driver ×4** | BTS7960 / IBT-2 | 10 (×4=40) | Base is genuinely enough. Only upgrade to a closed-loop controller (ODrive/SimpleFOC ~$50) if you later want silky velocity control. |
| **Cable (line)** | Braided Dyneema 100 lb | 13 | **200 lb coated Dyneema** (~$20) → less stretch & abrasion = position stays accurate longer. Line stretch is a top accuracy killer, so this upgrade earns its keep. |
| **Corner pulley ×4** | Small bearing pulley (steel) | 3 (×4=12) | **Ceramic-bearing pulley** (~$8) → lower friction at the redirect point directly improves position accuracy and lasts longer. Worth it. |

## §2 — Compute + control

| Item | Base pick | ~$ | Upgrade → why |
|------|-----------|----|----|
| **Vision brain** | Raspberry Pi 5 **4 GB** + PSU + 32 GB SD | 101 | **Pi 5 8 GB** (~$120+) or a mini-PC → run a bigger/faster detector, more headroom for the hybrid two-camera setup. Only if the 4 GB feels tight. |
| **Motor MCU** | ESP32 DevKit | 13 | **Teensy 4.1** (~$32) → far faster, hardware quadrature decoders for all 4 encoders, rock-solid timing. Worth it if you run high-rate closed-loop on all four motors. |
| **Home switches ×4** | KW12-3 microswitches (10-pk) | 8 | Optical/Hall endstops (~$10) → no mechanical wear, more repeatable homing. Minor; base is fine. |

## §3 — Power + safety (do not skimp — mandatory)

| Item | Base pick | ~$ | Upgrade → why |
|------|-----------|----|----|
| **Power supply** | 12V 30A 360W enclosed SMPS | 28 | **Mean Well 12V 30A** (~$55) → trusted regulation & protection, quieter, safer for an always-on system. Recommended upgrade — cheap PSUs are a fire/reliability risk running 24/7. |
| **E-STOP button** ⚠️ | 22 mm latching mushroom, NC | 10 | Industrial-rated (~$18) → more reliable contacts. Base is acceptable **if** it drives the contactor below. |
| **Power contactor** ⚠️ | 40A relay/DC contactor (e-stop cuts motor rail through this) | 12 | Proper safety contactor (~$25) → rated for many cycles, positive-guided contacts. |
| **Fuse + holder** | Inline 30A automotive | 8 | — (base is correct) |
| **5V buck converter** | LM2596 / MP1584 | 8 | Higher-current buck (5V 5A, ~$10) → headroom if the gripper servo stalls. |

> The e-stop **must physically cut the motor power rail through the contactor** —
> not just signal the MCU. This is non-negotiable regardless of tier.

## §4 — Perception + gripper

| Item | Base pick | ~$ | Upgrade → why |
|------|-----------|----|----|
| **Overhead "find" camera** | Logitech C920 1080p USB | 55 | Wider-FOV / C922 (~$70) → see the whole floor from a lower ceiling; better low-light. *Cheaper alt:* generic 1080p USB ($22) — poorer optics/autofocus. |
| **Effector "confirm" camera** | Raspberry Pi Camera Module 3 | 25 | **Camera Module 3 Wide** (~$35) → wider close-up view so laundry doesn't fall outside frame as the claw descends. Worth it. |
| **Gripper servo** | MG996R metal-gear | 3–11 | **DS3218 20 kg digital** (~$15) → much more grip force to curl the tentacles through a wet towel, metal gears, better centering. Recommended if grip feels weak. |

## §5 — Fasteners, filament, misc

| Item | Base pick | ~$ | Upgrade → why |
|------|-----------|----|----|
| **Threaded inserts** | *(skip — self-tap M3 into plastic)* | 0 | **M3 brass heat-set inserts + soldering-iron tip** (~$12) → **the single best reliability upgrade for printed parts.** Screwing repeatedly into plastic strips out; heat-set inserts give real metal threads. Strongly recommended. |
| **Metal ceiling anchors** ⚠️ | 304 stainless eye screws into joists | 8 | Rated lag eye-bolts (~$15) → higher load rating & safety margin. Always metal, into solid wood — **never printed.** |
| **M3 screw/nut kit** | Assorted M3 bolts/nuts/washers | 12 | Stainless kit (~$18) → won't rust, cleaner. |
| **Filament** | PETG (structural) + TPU 95A (fingers) + a little PLA | ~40 | Brand-name TPU (e.g., 95A) → more consistent flexible prints; the fingers depend on good TPU. |
| **Zip ties, wire, dupont, project box** | Assortment (box can be printed) | ~25 | — |

---

## Totals

| Tier | Rough cost | Notes |
|------|-----------|-------|
| **Base build** (print everything printable, base bought parts) | **~$430** | Fully functional; safe (worm-gear motors, real e-stop). |
| **+ Worthwhile upgrades** (heat-set inserts, Mean Well PSU, ceramic pulleys, coated line, DS3218 servo, wide effector cam) | **+~$90** | Best bang-for-buck reliability/accuracy gains. |
| **Cheapest bench prototype** (1 motor, reuse a laptop, stepper) | **~$90** | Prove one winch + the gripper before committing. |

## The three upgrades I'd actually pay for first
1. **M3 heat-set inserts (~$12)** — printed threads strip; this fixes it everywhere.
2. **Mean Well PSU (~+$27)** — it runs 24/7; don't cheap out on the power.
3. **Coated 200 lb Dyneema (~+$7)** — line stretch is the #1 accuracy killer.

Everything else, the base pick is genuinely fine to start.
