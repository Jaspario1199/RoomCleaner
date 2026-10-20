# Four-point claw attachment: model, simulator, calibration impact

Scope: control stack (`roomcleaner/cdpr/`) moved from a common-point claw to the real claw, which ties its four lines off at the
INNER mouths of the radial cable holes through the corner fillets of the electrical box (user direction 10/20). Everything below is
simulation or CAD arithmetic; nothing is measured on hardware. Author: implementation agent (not an independent verification).

## 1. Geometry from the CAD (`scripts/extract_claw_body_frame.py` -> `verification/claw_body_frame.json`)

Input: `exports/step/gripper_electric_housing_with_camera_bay.step` (box + camera bay, v6 world mm) and the v6 assembly for the jaws,
tube axis and CoM. A hole is a cylindrical face of radius 0.75 mm; its axis is intersected with the surface the hole's two boundary edges lie
on (inner = the pocket's corner-fillet cylinder, outer = the outer fillet/blend surface).

* Body frame: origin on the tube axis at the height of the inner mouths (v6 Y = 1098.724 mm); +z up the tube (v6 +Y); +x = v6 +X;
  +y = -v6 Z (camera bay on v6 -Z is at body +y). Right-handed. At claw yaw 0 the body axes equal the room axes.
* Inner mouths = attachment points b_i (m), station order A, B, C, D:

| station | corner (v6 X, Z) | body corner | b_i (m) | outer mouth (m) |
|---|---|---|---|---|
| A | (-X, +Z) | (-,-) | (-0.04207, -0.04207, 0) | (-0.05410, -0.05410, +0.00652) |
| B | (+X, +Z) | (+,-) | (+0.04207, -0.04207, 0) | (+0.05410, -0.05410, +0.00652) |
| C | (+X, -Z) | (+,+) | (+0.04207, +0.04207, 0) | (+0.05410, +0.05410, +0.00652) |
| D | (-X, -Z) | (-,+) | (-0.04207, +0.04207, 0) | (-0.05410, +0.05410, +0.00652) |

  Holes: 18.2 mm long, axis rising 21.0 deg outward on the corner diagonal. The mapping is the one of
  `scripts/analyze_cable_lines_claw_camera_bay.py` and it matches the config: at yaw 0 the body corners (-,-), (+,-), (+,+), (-,+) are the room
  corners of the anchors A (0.05, 0.05), B (3.30, 0.05), C (3.30, 2.69), D (0.05, 2.69), i.e. the config's station order. No fix was needed
  (asserted in `tests/cdpr/test_rigid_body.py::test_config_holds_the_cad_attachment_points`).
* Camera (camera-bay build, `LENS_CENTER_BAY`): lens centre (0, +0.0900, -0.00563) m, optical axis (0, 0, -1) (straight down); OpenCV frame
  with image x = body +x, i.e. `camera_in_body.rpy_rad = [pi, 0, 0]`. VERIFY: sensor rotation about the optical axis and lens height (assumed, CAMBAY_LENS_*).
* Lowest point (v6 jaw tips, midpoint of the two): (-0.0004, +0.0025, -0.5173) m. VERIFY: v7 jaws are being redesigned.
* CoM (CAD-solid estimate: PETG 1.27 g/cc, tube 2.70 g/cc, servo 55 g, 2065 g total; no electronics, no infill): (+0.0008, +0.0012, -0.1964) m. VERIFY.
  The real claw will weigh ~0.45 kg and have a higher CoM; only the pendulum restoring torque depends on it.
* Written to `config/robot.sim.json` and `config/robot.example.json` (`claw.attachment: "spaced"`, `attachment_points_body_m`, `camera_in_body`,
  `lowest_point_body_m`, `com_body_m`, free-text `_provenance`). `python scripts/extract_claw_body_frame.py --check` compares JSON and configs.

## 2. What changed in the stack

* `kinematics.py`: `Geometry` carries b_i, CoM, mass, payload point and a held yaw. `R_at(p)` = the caller's R, else the statics prediction
  (`Attitude`: gravity at the CoM + 4 tensions; least-total-tension distribution; roll/pitch from the horizontal moment balance; yaw held),
  anchored to the last measured pose (`set_reference`). A common point returns the identity: the old model exactly.
* `calibration.py`: measurement model, slack hypotheses, witnesses, `visual_reference`/`geometric_reference`, identifiability use each sample's measured R and b_i;
  attitude error (`calibration.attitude_sigma_rad` = 4 mrad x |b_i|) is added to the length sigma; excitation design and predicted sigmas use the predicted R;
  an alternate optimum with the same marker heading and no chi-squared barrier is a flat valley of one optimum, not an alignment ambiguity.
* `startup.py`: `RobotContext.room_pose` records the measured attitude (held yaw + anchor); slack-probe response uses the 6x6 rigid-body stiffness;
  marker visibility for excitation poses is required over a +-4 deg tilt cone around the predicted attitude (spaced attachments only).
* `trajectory.py`, `homing.py`, `supervisor.py`: per-knot R, feed-forward rates by central difference (tilt follows position), `approach_pose` solves the pose for the cable length at the predicted R, slack-aware FK at the measured R.
* `sim/world.py`: rigid-body hang (see 3). `config.py`: `claw.com_body_m`, `motion.task_max_height_m` (1.6 m), `calibration.attitude_sigma_rad`.
* `tasks.py`: `TaskRunner._move` refuses a target above `motion.task_max_height_m` with a clear reason (the yaw guard of the brief was dropped by the lead in favour of this single limit).

## 3. Rigid-body simulator

State (p, R); energy = m g z_CoM + sum 1/2 (EA/l_i) max(0, d_i - l_i)^2; exact analytic gradient and Hessian (checked against second differences);
Levenberg-Marquardt Newton with Armijo backtracking (round-off floor in the sufficient-decrease test), warm start from the previous state, step caps 5 cm / 0.1 rad.
Non-convergence is reported (`World.eq_failures`, event `no_equilibrium`, `strict` raises) and the previous state is kept. On the floor the claw rests on
the equilibrium attitude, lifted by the penetration (the old "snap upright" produced tens of newtons that are not physical). A single common point at the CoM stays 3-DOF.

* Limit-cycle bug (`slack_probe_review.md` M1): the recorded state (seed 6, z = 1.446 m): old Newton cycles 14 / 24 N, new solver is a fixed point at the energy minimum
  (T max < 7 N); regression in `test_rigid_body.py::test_world_hang_converges_at_the_recorded_limit_cycle_state` (common and spaced; the test also re-runs the old algorithm to show the failure).
  Whole-startup peak plant tension in the study: 20.3 N (old, solver artefact) -> 6.3 N (new solver, same common-point claw) -> 7.0 N (four-point claw).
* Passive yaw: for a worst-direction length error of 1 mm (vector norm) the review's linear tilt-free model gives 4.7-6.5 deg/mm at 9 room poses;
  the elastic simulator gives 2.4-3.7 deg/mm (tilt coupling and elasticity share the error), position unchanged within 3 mm. A single line moved 1 mm gives 1.2-1.9 deg.
  Paying out one line by 3 mm swings the claw by ~6 deg in yaw before any line goes slack; 6 mm of payout then slackens the opposite-diagonal line (e.g. pay A -> C slack).
* Planner/plant consistency: free lengths d_i - T_i/k_i from the predicted statics put the simulated claw at the predicted position (< 0.5 mm) and tilt (< 0.3 deg).

## 4. Tests

Added `tests/cdpr/test_rigid_body.py` (20 tests): four-point lengths/unit vectors/Jacobian/forward vs a brute-force loop; predicted-attitude wrench balance; anchoring to a measured pose;
single-point exactness (geometry, tensions, planned line bit-for-bit, world equilibrium vs the original 3-DOF Newton); energy-minimum, Hessian PSD and wrench balance at random states;
Hessian vs second differences; yaw drift vs the review; motor-driven settles; limit-cycle regression; idempotence over random states; non-convergence reporting; plan_line consistency;
estimator on rotated four-point data (slack hypotheses, witnesses, honest posterior) and a point-claw negative control; floor rest; `task_max_height_m` refusal and validation.
Existing tests adjusted for physics that legitimately changed (listed so they are not mistaken for weakened checks):
* `test_calibration.py`: its synthetic data are point-claw lengths, so it runs with the common-point profile (four-point data are in `test_rigid_body.py`).
* `test_slack_probe.py`, `test_slack_probe_review.py`: a rigid claw on spaced lines absorbs the first mm of a payout in yaw, so the injections pay out until a cable has the required true slack and probe the cable that actually slackened;
  the old limit-cycle test now asserts the fixed point.
* `test_margin_trust.py`: the board+probe fixture relaxes `calibration.length_sigma_max_m` to 7.5 mm (predicted sigma of its seed 1 is 6.0 mm with the four-point claw; see 5). Default unchanged.

Suite: `OMP_NUM_THREADS=1 python3 -m pytest -q tests/cdpr tests/firmware` -> **180 passed in 1423 s (23:43)**. Same command at HEAD 14d5981: 160 passed in 820 s (13:40);
the 20 added tests account for the count, the longer run for the 4-point plant, the probe's longer poses and the margin fixture (580 s setup).

## 5. Calibration accuracy before / after (`scripts/sim_floor_reference_study.py --suite main --only "3c" --seeds 3 --probe --no-whatif`; board 3x3 p0.42 + slack probe, seeds 0-2)

| variant | pred. abs sigma med/max (mm) | abs L0 error med/max (mm) | err/sigma max | trust (3 seeds) | peak plant T (N) | sim time (s) |
|---|---|---|---|---|---|---|
| before: HEAD 14d5981 (common point, old CAD numbers, old solver) | 12.8 / 12.9 | 22.9 / 23.9 | 1.9 | LOCAL_ONLY, VERIFIED (mixed) | 20.3 (artefact) | 1895 |
| D: new code, common point, old numbers (backward-compat check) | 12.8 / 12.9 | 23.4 / 27.6 | 2.2 | LOCAL_ONLY, VERIFIED | 6.3 | 1899 |
| C: new code, common point, new CAD camera/jaws | 11.6 / 11.8 | 34.2 / 56.3 | 5.3 | LOCAL_ONLY, VERIFIED | 7.0 | 1894 |
| **after: four-point claw, new CAD camera/jaws, rigid-body plant** | **15.4 / 16.8** | **24.6 / 49.8** | **3.2** | LOCAL_ONLY (all) | 7.0 | 2986 |

Reading: D vs before shows the point-claw behaviour is preserved (sigma identical to 0.02 mm; tiny differences are the solver's). C shows the new camera height/jaw length alone do not hurt the predicted sigma
(errors in absolute L0 are larger, 34 / 56 mm, with the estimator under-reporting, err/sigma 5.3). The four-point model raises the predicted absolute sigma by ~4 mm (11.6 -> 15.4) and the probe takes 69 s per pose instead of 41 s
(probed readings 68 % vs 54 %), so the startup is 1.6x longer. The predicted length sigma over the work volume rises from < 5 mm to 5.7-6.0 mm for seed 1, so the D26 margin rule's criterion (5) (5 mm) is missed:
no seed reaches VERIFIED with the unchanged threshold. The absolute-length numbers remain far from what beads need (as before). These are simulation numbers.

## 6. Open issues / assumptions

1. Yaw and tilt are passive and respond to mm-level length inconsistencies; the predicted attitude is nominal. The planner's lengths are exact only where R is measured; elsewhere an error of a few degrees of tilt is about 1 mm of length (10 N at EA/L ~ 10 kN/m in the simulator).
2. Straight chord from the inner mouth: a steep line bears on the hole's outer rim; path error up to 18.2 (1 - cos theta) mm (~6 mm at 50 deg), the constant part is absorbed by L0. Measure on hardware; decision D-G in the docs.
3. `Calibrator.boundary_sigma` (D26) keeps its 3-DOF position-only solution and now evaluates it at the predicted R; the rigid claw's orientation freedom is not in the margin sigma.
4. CoM, jaw tips, camera sensor rotation are CAD estimates (VERIFY). D27 (no IMU on the claw): the stack already takes the measured R from the vision pose and the statics prediction away from the reference; `claw.imu` is still true in the simulation profile.
5. On the floor the claw yaw is held by friction and the lines' yaw/tilt torque is not modelled; the predicted visibility cone (+-4 deg) is a margin chosen from the simulated tilt range, not measured.
6. The HEAD commits before this work (`14d5981`) pass 160/160 in this environment; intermediate WIP commits of this work were red (ambiguous local alignment, marker not visible) until the fixes in section 2.
