# Design history

RoomCleaner has gone through two design generations. Both are kept in this
repo: generation 1 is the record of what was tried, measured and learned;
generation 2 is the current direction. Nothing from generation 1 is deleted.

| | Generation 1 (Aug 6 – Sep 2, 2026) | Generation 2 (Oct 7 – present) |
|---|---|---|
| CAD tool | CadQuery (Python), `cad/` | SolidWorks, `solidworks/` |
| Winch mounting | One-piece printed `corner_mount` screwed to a joist (revs A–D.1) | Fixed **wall frame** + **removable slide-in motor housing** + shell (v1–v3) |
| Spool | `winch_spool`, Ø20 core × 26 mm, 32 mm long | **Shortened** to fit the motor shaft's real engagement; ~20 ft of line target (v1–v3) |
| Electronics | One Arduino Uno + CNC Shield V3 (4× A4988) at a base station, long motor cables to each corner | **One node per winch**: XIAO ESP32 + A4988 + step-down regulator at each station, one 12 V pair per station, Wi-Fi coordination |
| Gripper | Five tendon-driven TPU fingers on a hub, MG996R pulling a tendon drum | **Two-jaw clamp**: MG996R → 18T pinion → 54T/24T compound → 24T follower (3:1, jaws counter-rotate), electronics + camera housing on a rigid extension |
| First target | 0.9 kg (jeans) payload, full room | **1 lb test weight** on four stations; laundry later |
| Homing | KW12-3 + bead, switch below the pulley (D14) | Kept: KW12-3 + bead (Bead part, KW12 reference in v1) |

## What carried over from generation 1

- The bench bring-up (Phases 1–5): wiring discipline, Vref setting, fail-safe
  NC limit-switch wiring, `S` switch test, polarity-by-meter. The `firmware/`
  sketches remain the working reference for the protocol.
- Cable kinematics, tension model and the sim/live console (`roomcleaner/`).
- The homing concept and D14 (bead never crosses the pulley).
- Lessons from verification: rev C of the corner mount failed independent
  review (switch roller missed the line) before anything was printed.

## What generation 2 changes, and the stated reasons

Recorded from Jasper's SolidWorks files and Outline v1 (Oct 19). See
DECISIONS.md D15–D19.

1. **Removable wall station** — service and replacement without unscrewing a
   frame from the wall; the frame stays installed and calibrated.
2. **Short spool** — the original spool was longer than the motor shaft can
   engage; shorter spool holds ~20 ft, enough for an 11 × 9 × 9 ft room.
3. **Per-station electronics** — eliminates four long motor harnesses; the cost
   is that synchronized motion and communication faults move into firmware.
4. **Clamp gripper** — simpler to build and test than five TPU fingers and a
   tendon drum; 3:1 reduction trades jaw speed and travel for torque.
5. **1 lb first target** — prove four stations hold and move a known load
   before the laundry task.

The engineering review of these changes is `verification/design_review_gen2.md`.
