# RoomCleaner — Hardware Guide

You don't need any of this to work on Phases 0–2 (it's all software). This is
your shopping and wiring reference for when you go physical in Phase 3.

**Build a tabletop prototype first** (≈1 m × 1 m). It costs little, is safe, and
every bit of code transfers to the full-size room build.

---

## System block diagram

```
                 ┌──────────────────────────┐
                 │   Compute (Raspberry Pi   │
                 │   5 or a mini-PC)         │
                 │   - perception (camera)   │
                 │   - control loop          │
                 │   - state machine         │
                 └────────────┬─────────────┘
                              │ USB / GPIO / serial
        ┌─────────────┬───────┼────────┬─────────────┐
        │             │       │        │             │
   ┌────▼───┐   ┌─────▼──┐ ┌──▼───┐ ┌──▼─────┐  ┌────▼────┐
   │ Motor  │   │ Motor  │ │Motor │ │ Motor  │  │ Camera  │
   │ driver │   │ driver │ │driver│ │ driver │  │ (USB /  │
   │  + A   │   │  + B   │ │ + C  │ │  + D   │  │  Pi cam)│
   └────┬───┘   └────┬───┘ └──┬───┘ └───┬────┘  └─────────┘
     winch A      winch B   winch C   winch D
        └───────────┴──cables──┴─────────┘
                     end-effector
                   (claw / suction)
                              │
                     ┌────────▼────────┐
                     │  HARDWARE E-STOP │  ← cuts motor power directly
                     └──────────────────┘
```

---

## Parts list (full-size, one sensible option)

| Part | Suggestion | Notes |
|------|-----------|-------|
| Compute | Raspberry Pi 5 (or any mini-PC) | Runs perception + control. A Pi is fine; a mini-PC eases the vision model. |
| Motors ×4 | NEMA-17 stepper **or** DC gearmotor w/ encoder | Steppers = simple open-loop position but can lose steps under load; geared DC + encoder = true closed-loop. For lifting, closed-loop is safer. |
| Motor drivers ×4 | Stepper: TMC2209 / DRV8825. DC: a driver like a BTS7960 | Match to your motor choice. |
| Winch spools ×4 | 3D-printed drum on the motor shaft | Keep the diameter consistent — it sets the length-per-revolution. |
| Cable | Braided fishing line (high test) or thin Dyneema | Low stretch matters a lot; stretch = position error. |
| Pulleys | Small ceiling-corner pulleys | Route the cable cleanly from spool to the room volume. |
| End-effector | **Suction:** small 12 V vacuum pump + solenoid valve. **Claw:** a servo gripper | Suction grabs flat cloth far better. See below. |
| Z-stage (optional) | Small spring or micro-servo on the claw | For the final "reach down and touch the floor" few cm. |
| Camera | USB webcam or Pi Camera | One fixed overhead to find laundry; optionally one on the claw to confirm. |
| Power supply | 12 V / 24 V, amply rated | Size for 4 motors + pump at once, with headroom. |
| **E-STOP** | A real latching e-stop button that cuts motor power | **Non-negotiable.** Must work even if the software hangs. |
| Sensors | Limit/home switches; suction pressure sensor | Homing + grab confirmation. |

Exact models depend on your room size and payload — pick after the tabletop
prototype tells you how much force you actually need.

---

## The end-effector decision

This is the make-or-break mechanical choice.

- **Suction / vacuum (recommended to try first).** A vacuum cup pressed onto flat
  fabric lifts it reliably — cloth on a hard floor is close to the ideal case for
  suction. You need a vacuum source (a small pump or a repurposed handheld vac), a
  valve to switch it, and a pressure sensor to confirm the grab.
- **Mechanical claw / gripper.** Intuitive, but flat crumpled cloth gives a rigid
  claw nothing to close around, and it tends to just push the item along the
  floor. Thin, floor-scraping fingers help but add complexity.

The software treats the end-effector as a swappable module (`hardware/` in
Phase 3), so you can prototype both without touching the control loop.

---

## Homing & calibration (the unglamorous but essential part)

- **Cable homing:** the robot must know each cable's length at startup. Options:
  drive the claw to a known home fixture, or use limit switches on the spools.
- **Anchor calibration:** measure the four ceiling anchor positions precisely and
  put them in `config.py`. Small anchor errors → large position errors.
- **Camera calibration:** compute the homography (or full extrinsics) that maps
  camera pixels to room coordinates. Redo it if the camera ever moves.

---

## Safety checklist (before the first powered move)

- [ ] Hardware e-stop wired to cut **motor power**, tested to work with software off.
- [ ] Software force/tension limits enforced (`MAX_CABLE_TENSION` in `config.py`).
- [ ] Geofence: reject any commanded point outside the verified safe workspace.
- [ ] Nobody and no pets in the room during operation.
- [ ] Nothing fragile or valuable under the workspace.
- [ ] Never run unattended until it has earned trust over many supervised runs.
