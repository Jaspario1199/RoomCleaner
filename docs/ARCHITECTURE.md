# RoomCleaner — Architecture & Design Notes

This explains *why* the code is shaped the way it is, so future-you (and any
collaborators) can extend it without surprises.

## Layers, and the one rule between them

```
        perception            control              hardware
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
   │ Detector         │  │ Controller       │  │ motor drivers│
   │ (finds laundry,  │─▶│ (state machine)  │─▶│ camera       │
   │  returns 3D pts) │  │ + trajectory     │  │ e-stop       │
   └──────────────────┘  └────────┬─────────┘  └──────────────┘
                                  │
                          ┌───────▼────────┐
                          │  kinematics    │  pure math, no I/O
                          └────────────────┘
```

**The rule:** `kinematics.py` is pure math with no I/O; `control/` never talks to
hardware directly; `perception/` and `hardware/` hide the messy real world behind
small interfaces. This is what lets the **same controller code** run against the
simulator today and real motors in Phase 3.

## Key design decisions

### Point-mass model of the effector
We model the claw as a single point with mass. That's a deliberate
simplification: it makes the kinematics and statics tractable and is accurate
enough for a small, compact end-effector. If the effector becomes large or we
need to control its *orientation*, we'd upgrade to a rigid-body (6-DOF) model —
that's a bigger change, so we defer it until hardware proves we need it.

### Cables pull, never push
Every workspace/feasibility decision flows from this. A cable can only exert
force *toward* its anchor. Holding the claw against gravity therefore requires a
set of non-negative cable tensions whose sum cancels gravity — and with 4 cables
and 3 force equations there's a 1-D family of solutions to pick from (see
`solve_tensions`). Points where no valid tension set exists are *outside* the
workspace, which is exactly the pink border in the workspace plot.

### Explicit state machine over ad-hoc logic
`Controller` is a named-state machine (`SCAN → SELECT → APPROACH → GRAB →
DELIVER → DONE`). This makes it obvious what the robot is doing at any moment,
easy to insert safety states (`VERIFY_GRAB`, `RECOVER`, `ESTOP`), and easy to log
and replay.

### Swappable perception & end-effector
`Detector` is an interface with two implementations planned:
`SimulatedDetector` (now) and a real vision detector (Phase 1). Downstream code
depends only on the interface. The end-effector is treated the same way, so the
claw-vs-suction decision stays open without code churn.

### Simulator is a monitor, not the system
`simulator.py` only *draws* positions the controller produces. It never drives
logic. In Phase 3 it becomes an optional live monitor next to the real robot.

## Coordinate frame (repeated everywhere, memorize it)

- Origin at a floor corner. `+x`, `+y` along the two walls, `+z` up.
- Ceiling anchors at `z = ROOM_HEIGHT`; the floor (laundry) at `z = 0`.
- Anchors are always ordered A, B, C, D counter-clockwise. This order is fixed
  across kinematics, control, and (eventually) the physical motor wiring — cable
  index `i` always means the same corner.

## Testing philosophy

`tests/test_kinematics.py` pins down the math we must be able to trust —
inverse↔forward round-tripping, unit-vector directions, gravity balance, and
workspace membership. As real hardware and perception land, add tests at each
seam (e.g. camera-pixel → world-point mapping) rather than end-to-end only.

## Extending it — likely next edits

- **Real detector:** subclass `Detector`, return `Detection`s with real 3D
  positions. Nothing else changes.
- **Better routing:** `Controller` picks nearest-first; swap in a TSP-style order
  for fewer/shorter trips.
- **Orientation control:** upgrade the point-mass model to a rigid body if the
  end-effector needs to be aimed, not just positioned.
- **Hardware backend:** add `hardware/motors.py` implementing "set cable length
  i to L" and have the controller call it instead of (or alongside) the sim.
