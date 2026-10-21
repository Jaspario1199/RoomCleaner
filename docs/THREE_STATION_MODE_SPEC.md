# Three-station mode: specification (2026-10-21)

Jasper, 10/21: for the first hardware test (tonight and tomorrow) he will mount only **three** stations. This is a
test configuration, not a design change: the product is four stations. The software must run with either three or
four, chosen in the settings, with four as the default. The work tonight is about getting three to run.

## Settings

- New config key `stations.active` (list of station ids). Default: all four, so existing profiles are unchanged.
  Allowed: any 3 or 4 of A, B, C, D. Validated: no duplicates; 3 ≤ n ≤ 4; the active anchors must span a triangle
  with positive area, with an error message otherwise.
- Keep all four station records in the config. Inactive stations get no address requirement and no transport; the
  host never configures or arms them.
- New hardware profile `config/robot.three.example.json`: copy of the hardware example with `stations.active` set to
  three ids. The default trio and layout are in the section below.
- New sim profile `config/robot.sim3.json`: copy of the sim profile with three active.

## Physics that changes with three cables

- **Kinematics:** unchanged per cable (L_i = ‖a_i − p‖), over the active set only.
- **Statics:**
  - With three cables and a point load, the tensions are the unique solution of a 3×3 system. There is no tension
    distribution to choose. Every T_i ≥ T_min is required, or the pose is infeasible.
  - With four, keep the existing method.
  - The rigid-body (four-point attachment) attitude model must handle three attachment points: only the active
    corners' cables pull. Check that it still converges; report the predicted claw tilt across the three-station
    workspace.
- **Workspace:** a point mass is held with all-positive tensions only when its floor projection lies inside the
  active anchors' triangle.
  - Planner, ceiling cap and task workspace must use the feasible region with the same margins as today: tension
    floor, 0.2 m walls, 0.4 m ceiling, plus a margin from the triangle's open edge. Size that margin from the
    tension floor and state it.
  - Expect roughly half the room.
- **Start position:** "claw upright near the middle" becomes **near the centroid of the active anchors' floor
  projection**. For three room corners the room centre sits on the triangle's edge, where one cable goes slack, so the recommended layout below is used instead.
  - The startup must use this point; the phone app's Setup step and the start checklist must say where it is.

## Layout for the first test (Jasper, 10/21: "rearrange the position to a triangular shape")

Three stations do not have to sit in three room corners. The robot calibrates its anchors itself, so any good
triangle works.
- **Recommended:** A and B in the two corners of one 11 ft wall, and the third station (id C) in the **middle of the
  opposite 11 ft wall**, on the stud nearest the midpoint, at the same height.
- **Anchor priors:** A (0.05, 0.05, 2.5932), B (3.3028, 0.05, 2.5932), C (1.6764, 2.6932, 2.5932) m.
- **Shape:** sides about 3.25 / 3.10 / 3.10 m, nearly equilateral. The margins cut least from a balanced triangle,
  and the room centre (1.676, 1.372) lies inside it.
- **Start point:** the centroid (1.676, 0.931), or the room centre if the startup's tension check accepts it. The
  implementer reports both minimum tensions.
- **Priors only:** the anchor priors only seed the calibration. A stud a few inches off the midpoint is fine. The
  priors must be within the calibration's prior range; report that range.
- **Outlet angle:** a mid-wall station's line leaves square to the wall rather than along a corner diagonal. Check the
  outlet angle range over the three-station workspace and report it (the outlet cone limit is a known open item).
- **Power run to C:** 3 ft down, along the floor to the far wall's middle, 9 ft up: about 27 ft. The 35 ft pair covers
  it with slack.
- **Config:** `config/robot.three.example.json` and `config/robot.sim3.json` use active = [A, B, C] with C's anchor
  prior at the opposite wall's middle. This replaces the "A, B, D" default above. Layout and id choice stay
  configurable.

## Startup and calibration

- Slack take-up one cable at a time, pretension, initial lift, visual initialisation and calibration all run over
  the active set.
- Calibration poses are chosen inside the three-station feasible region.
- Fit: anchors and zero lengths of the active stations only. Check identifiability (condition number / covariance)
  and report it. Accept and trust rules are unchanged: VERIFIED only if k·σ fits the margins, otherwise LOCAL_ONLY.
- Beads stay end-of-travel switches (D26).
- Board survey and rocking watch: unchanged, over the active stations.

## Software surfaces

- **Supervisor, coordinator, leases, trust ledger:** active stations only. A missing inactive station is not a
  fault.
- **Service and phone app:** station tiles only for active stations.
  - The checklist item "All four cables attached…" becomes "All active cables (A, B, D) attached…".
  - Setup shows the start point.
- **Firmware:** unchanged; each station is independent.
- **Simulator:** the world model is built with the active cables only.

## Tests and acceptance

1. Config: the default (four) is unchanged; three is accepted; two, duplicates, an unknown id and a degenerate
   triangle are refused with clear messages.
2. Statics: for three cables, unique tensions match a direct solve. A point outside the triangle is infeasible.
3. Simulation: a full startup with `robot.sim3.json` (seed 0 and two more seeds) reaches READY, or a clearly
   reported LOCAL_ONLY, with no station faults. Then:
   - a 300 mm move inside the triangle completes;
   - a move toward the missing corner is refused before motion.
4. Regression: the full `tests/cdpr` suite passes unchanged for four stations.
5. Doc `docs/THREE_STATION_MODE.md` covers, for tonight's test:
   - which config to use and how to pick the corners;
   - where to put the claw;
   - what workspace to expect;
   - what the app shows;
   - the safety notes: nobody under the robot; the claw sits further from the room centre; a three-cable claw has
     less tilt and yaw stiffness.
