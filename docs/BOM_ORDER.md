# RoomCleaner — Final BOM (the "shirts & jeans" build)

The locked-in parts list, sized for the real job: picking up **shirts, pants, and
jeans** (heaviest item ≈ average Levi's, ~2 lb / 0.9 kg) off the floor and
dropping them in a hamper. Reuses a computer you own; the 12 V motor supply is
killed by a **switched power strip you already have** (no e-stop button needed).

Prices are 2026 US estimates (±20%); Amazon blocks automated price checks, so
confirm at checkout. Why these sizes: see "Sizing" at the bottom.

---

## §0 — Print these (free)

STEP + STL in `cad/`. Print settings & assembly in `cad/README.md`.
The `motor_mount` is the **NEMA 17** L-bracket; `winch_spool` bore is 5 mm.

| Part | Qty | Material |
|------|-----|----------|
| `winch_spool` | 4 | PLA/PETG |
| `motor_mount` (NEMA 17 bracket) | 4 | **PETG** |
| `corner_guide` | 4 | PETG |
| `effector_frame` | 1 | PETG |
| `tentacle_hub` | 1 | PETG |
| `tentacle_finger` | 5 | **TPU 95A** |
| `camera_mount` | 1 | PLA/PETG |

---

## §1 — Buy this

| ✓ | Item | Spec / search term | Qty | ~$ |
|---|------|--------------------|-----|----|
| ☐ | **Winch motor** | NEMA 17 stepper, **≥50 N·cm** (high-torque) — "NEMA 17 stepper 59Ncm 4 pack" | 4 | 50 |
| ☐ | **Controller + drivers** | Arduino Uno (or CNC-shield clone) + **CNC shield** + 4× A4988/DRV8825 — "Arduino CNC shield kit A4988" | 1 kit | 18 |
| ☐ | **Line** | Braided Dyneema 100 lb — "hollow braid dyneema 100lb" | 1 | 10 |
| ☐ | **Home switches** | KW12-3 micro limit switch (10-pk) — "KW12-3 limit switch" | 1 pk | 8 |
| ☐ | **Power supply** | 12V **5A** 60W — "12V 5A power supply barrel" | 1 | 12 |
| ☐ | **Inline fuse + holder** | 5–10 A automotive — "inline blade fuse holder 5A" | 1 | 3 |
| ☐ | **Overhead camera** | 1080p USB webcam — "1080p USB webcam" (or Logitech C920 ~$55 for autofocus) | 1 | 22 |
| ☐ | **Gripper servo** | MG996R metal-gear — "MG996R servo" | 1 | 6 |
| ☐ | **Ceiling anchors** ⚠️ | 304 stainless eye/lag screws **into joists** — "304 stainless lag eye screw" | 1 pk | 8 |
| ☐ | **M3 screw/nut kit** | Assorted M3 — "M3 screw nut assortment kit" | 1 | 12 |
| ☐ | **TPU filament** | TPU 95A (for the fingers) — "TPU 95A filament 1kg" | 1 | 20 |
| ☐ | **Wiring** | Dupont jumpers + 22 AWG hookup + zip ties | — | 15 |

**Total ≈ $184** (≈ **$164** if you already own some PLA/PETG/TPU filament).

### Reused / not needed (why)
| Item | Why it's out |
|------|--------------|
| Raspberry Pi + PSU + SD (~$101) | You're reusing a computer for vision. |
| E-stop button + contactor (~$22) | Your **switched power strip** cuts the 12 V motor supply — same job. |
| Corner pulleys (~$12) | Printed `corner_guide` handles 15 N tension fine. |
| Buck converter (~$8) | Reuse a **5 V phone charger** to power the servo. |
| Effector close-up camera (~$25) | Deferred to Phase 4; the overhead camera gets you picking up. |
| Worm-gear DC + encoders (~$128) | Overkill for 2 lb; steppers are cheaper, faster, plenty strong. |

---

## §2 — Optional upgrades (only if you want to spend more)

| Upgrade | +$ | Why |
|---------|----|----|
| **M3 brass heat-set inserts** + iron tip | 12 | **Best reliability upgrade** — real metal threads in printed parts instead of self-tapping into plastic. |
| Ceramic-bearing corner pulleys (×4) | 12 | Lower friction → better position accuracy over time. |
| Logitech C920 webcam | +33 | Autofocus + better optics vs. a generic cam. |
| Coated 200 lb Dyneema | +7 | Less stretch = position holds accurate longer. |
| TMC2209 drivers (quiet) | +10 | Near-silent steppers vs. A4988 whine. |

---

## Sizing (why these numbers)

Computed from our own kinematics for the loaded effector (0.45 kg assembly +
0.9 kg jeans = 1.35 kg):

- **Peak cable tension across the whole workspace: 15 N.** → ~3 kg·cm drum torque
  with a 2× dynamic margin. A ≥50 N·cm NEMA 17 (~5 kg·cm) gives ~2× on top of
  that — comfortable.
- **Line:** 15 N ≈ 3.4 lb → 100 lb Dyneema has ~30× margin.
- **Power:** ~12 W mechanical total → a 12 V 5 A (60 W) supply is ample.

If you later want a **heavier** capacity (e.g. wet towels or bedding), you'd step
back up to higher-torque motors, a bigger supply, and stronger line — and, for
horizontal pulling tasks like straightening bedding, a different cable geometry
(the current one can't apply much sideways force near the floor).

## The one thing that stays regardless of budget
The **metal ceiling anchors** (into joists) and the **switched power strip** kill
path. Everything else can flex; those two keep the rig up and stoppable.
