# RoomCleaner — Hardware Guide (BOM + Gripper)

You don't need any of this for Phases 0–2 (all software). This is your shopping
and design reference for going physical. Prices are 2026 US estimates (±20%) —
Amazon doesn't expose live prices to automated lookups, so treat them as
realistic ballparks, not quotes.

> **Build a tabletop prototype first** (≈1 m × 1 m, small motors). It's cheap,
> safe, and every line of code transfers to the full-size room build.

---

## The two decisions that make or break the build

### 1. Motor choice — use self-locking **worm-gear DC + encoder**, not bare steppers
This is a *lifting* job: a dropped end-effector = a camera smashing on the floor.

- **NEMA 17 steppers** — cheap and simple (one RAMPS board drives all four), but
  they hold load *only while powered*, run hot doing it, and **silently lose
  steps under shock/overload** — exactly what happens when the gripper snags a
  heavy towel. Position is then wrong with no feedback. OK only if kept energized
  100% of the time and re-homed often.
- **Worm-gear geared DC + encoder** — the worm gear is **mechanically
  self-locking (won't back-drive)**, so the load holds with *zero* current, no
  heat, no drop if power blips. The encoder gives true closed-loop position. You
  write a small PID loop per motor and they're slow (~10–30 RPM), which is fine
  for a winch. **This is the reliable pick.**

### 2. Split the brain: Raspberry Pi (vision) + a microcontroller (motors)
Vision (webcam + detection) wants Linux horsepower → **Raspberry Pi 5**.
Real-time motor timing/PID wants bare metal → **ESP32** (or Arduino Mega+RAMPS
for steppers). The Pi says "go to XYZ"; the ESP32 runs the four control loops.
Motor timing in Linux userspace gives jitter and missed edges.

---

## Recommended "reliable" BOM (~$515)

| # | Item | Spec | Qty | ~$ea | ~$sub | Why |
|---|------|------|-----|------|-------|-----|
| 1 | Winch motor | 12 V worm-gear DC, **self-locking**, ~20–30 RPM, ~30 kg·cm, **w/ quadrature encoder** | 4 | 32 | 128 | Holds load with no power, closed-loop — the safe lifting choice |
| 2 | Motor driver | **BTS7960 / IBT-2** dual half-bridge (43 A) | 4 | 10 | 40 | Handles stall current with margin; cheap, robust |
| 3 | Vision brain | **Raspberry Pi 5, 4 GB** + 27 W PSU + 32 GB microSD | 1 | 101 | 101 | Runs the webcam detector; 4 GB is plenty and avoids 8 GB price spike |
| 4 | Motor MCU | **ESP32 DevKit** (keep a spare) | 1 | 13 | 13 | Deterministic PID/PWM for 4 motors; talks to Pi over USB/UART |
| 5 | Power supply | **12 V 30 A 360 W** enclosed SMPS | 1 | 28 | 28 | Feeds 4 motors + servo with headroom for simultaneous stalls |
| 6 | Cable | **Hollow/braided Dyneema (UHMWPE) 100–200 lb**, low-stretch | 1 | 13 | 13 | Near-zero stretch keeps position accurate |
| 7 | Spools/drums | **3D-printed** winch drums | 4 | 0 | 0 | Print for free; keep diameter small for torque |
| 8 | Corner guides | **Micro pulleys w/ bearings** | 4 | 3 | 12 | Bearings cut friction/wear vs. a bare screw eye |
| 9 | Anchor eyes | 304 stainless **screw eyes** (into joists) | 1 pk | 8 | 8 | Structural mount for corner pulleys |
| 10 | Camera | **Logitech C920/C920x** 1080p USB | 1 | 55 | 55 | Plug-and-play on Pi, autofocus, works with OpenCV out of box |
| 11 | Gripper servo | **MG996R** metal-gear (~11 kg·cm) | 1 | 11 | 11 | Metal gears survive gripping; SG90 plastic gears strip |
| 12 | **E-STOP** | 22 mm **latching mushroom, NC** | 1 | 10 | 10 | Mandatory. Latches off until twisted to reset |
| 13 | E-stop contactor | 30–40 A relay / DC contactor | 1 | 12 | 12 | E-stop NC coil drops this to **cut the 12 V motor rail** |
| 14 | Home switches | **KW12-3** micro limit switches (10-pk) | 1 | 8 | 8 | One per winch for cable homing/zeroing |
| 15 | 5 V buck | MP1584/LM2596 | 1 | 8 | 8 | Clean 5–6 V for servo + logic off the 12 V rail |
| 16 | Fuse + holder | Inline 30 A automotive fuse | 1 | 8 | 8 | Protects the motor rail |
| 17–20 | Wiring, dupont, project box, mounting | — | — | ~44 | 44 | Signal/power wiring, enclosure, ceiling brackets |

**Reliable total: ~$515** (3D-printed spools).

### "Budget" swaps (~$250 total) — accept the flagged risks
- 4× NEMA 17 steppers ($50) + TMC2209 drivers ($20) + Arduino Mega/RAMPS ($32) —
  **but loses steps under shock and only holds while powered; no vision on RAMPS.**
- Reuse a laptop/PC for the webcam vision ($0) instead of buying a Pi.
- SG90 servo ($2) — **plastic gears strip under load; expect replacements.**

### Where going too cheap *will* bite you
- **Bare steppers for lifting** — no feedback + step loss + power-off = dropped
  effector. If you must, add homing switches and never de-energize under load.
- **Cheap PE/monofilament line** — stretches; your XYZ solution drifts and sags.
  Use true **low-stretch Dyneema ≥100 lb**.
- **SG90 gripper servo** — shears the first time it grips a heavy wet item. Use MG996R.
- **E-stop wired to logic only** — the button must physically **cut the motor
  power rail** via the contactor, not just signal the MCU. Software can hang; the
  latch cannot.
- **L298N as the DC driver** — ~2 A max, drops ~2 V; stalls/overheats on a real
  winch. Use BTS7960.
- **Drywall anchoring** — screw corner pulleys into **joists/solid blocking**.
  Cable tension multiplies the load and will rip out a drywall anchor.

*Sourced product links live in `docs/RESEARCH.md`.*

---

## The gripper — how to grab flat cloth off a hard floor

Cloth lying flat on tile is the worst case: nothing to close fingers around, and
the hard floor gives nothing to dig into. Every solution that works does one of:
**(a) pierce the fabric**, **(b) pinch it against the floor / a rigid anvil**, or
**(c) slide a thin leading edge under it and scoop.** Because our effector is
lowered straight down on cables, the motion is **press down → capture → lift**,
which favors piercing pins or a pinch/scoop.

### The single most important trick
**Don't try to close in mid-air — pinch or scoop against the floor.** Give the
gripper a rigid "anvil" (a thin spatula/leading edge) that presses the cloth flat
against the floor, then a finger/flap/pins trap the cloth against that anvil. A
shallow (~10–20°) ramped leading edge driven forward-and-down scoops a crumpled
pile far more reliably than any symmetric squeeze.

### Recommendation (mechanical, no vacuum)

1. **Primary — Spatula-scoop + Fin Ray flap (all 3D-printable).**
   A thin spring-steel/PLA leading edge wedges under the cloth (or pins it to the
   floor); a servo-driven **Fin Ray Effect** finger folds the cloth up onto the
   spatula. The spatula does the *capturing* (the hard part), the soft flap does
   the *holding* (the easy part). Forgiving of crumpled vs. flat. One MG996R servo.
2. **Fallback — Needle/pin gripper.** Two opposed sets of thin angled pins
   (0.8–1.5 mm) that drive a few mm into the fabric and lock it mechanically —
   the best pure "straight-down onto a flat sock" grabber. Add a stripper plate to
   push cloth off on release. Tiny pinholes are irrelevant on laundry about to be
   washed; watch for lint/grit buildup.

**Skip:** plain parallel jaws alone and plain Fin Ray alone (nothing to grab on
flat cloth), and jamming/granular grippers (they need the vacuum pump you ruled
out).

**Payload is not the constraint** — a wet towel/jeans is ~300–700 g, well within
an MG996R (~9–11 kg·cm) or an off-the-shelf metal claw (~500 g). *Capturing the
flat sheet* is the whole challenge.

---

## Homing, calibration & safety (before the first powered move)

- **Cable homing:** the robot must know each cable's length at startup — drive to
  a home fixture or use the limit switches on the spools.
- **Anchor calibration:** measure the four ceiling anchor positions precisely and
  put them in `config.py`; small anchor errors → large position errors.
- **Camera calibration:** see `docs/VISION.md` — zero-calibration works for a
  centered overhead camera; a 4-point homography corrects a tilted one.
- **Safety checklist:** hardware e-stop cuts motor power (tested with software
  off) · software tension limits enforced · geofence rejects points outside the
  verified workspace **and the fan keep-out** · nobody/no pets in the room · never
  unattended until it's earned trust over many supervised runs.
