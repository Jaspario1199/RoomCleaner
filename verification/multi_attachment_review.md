# Independent review: four-point claw attachment (b9bc5d0..1c2e968)

Reviewer: calculation-checker (independent of the implementer). Executable evidence:
`tests/cdpr/test_multi_attachment_review.py` (15 tests, all pass; tests named `finding_*` document a defect and are
meant to flip when it is fixed). Scratch derivations were run with `/usr/bin/python3` (CadQuery 2.8 available there).
Code, configs and other tests were not modified.

## 0. Status of the inputs
* **Supplied facts** (user/CAD records): inner mouths of the corner cable holes are the tie-offs (user direction 10/20);
  D27 no IMU on the claw; D28 tube cut by 50 mm; claw budget 450 g; <= 40 N per cable; payload <= 0.9 kg.
* **Approved assumptions in the code**: straight chord from inner mouth to anchor; least-total-tension (no pretension)
  distribution; yaw held, not predicted; EA = 20 kN, mu = 0.4 in the plant; attitude error 4 mrad; visibility cone 4 deg.
* **Derived results** are in section 1-4 below. **Unresolved uncertainty** in section 5.

## 1. Results: agree / disagree

| # | Result | Verdict | My number |
|---|---|---|---|
| 1 | L_i = abs(a_i - (p + R b_i)); dL/dp = -u, dL/dw = -(r x u) | AGREE | central FD vs closed form, 40 random poses, max error 4.6e-10 (both blocks). Existing test only checks dL/dp; rotation block was untested before. |
| 2a | World equilibrium = force and moment balance | AGREE | independent recomputation (own energy, tensions, moment about CoM): residual <= 1e-6 N / N m at 12 random states; Hessian PD at every solution |
| 2b | Analytic Hessian | AGREE | second differences of an independently written energy: rel. error <= 2e-8 away from slack/taut kinks. FD of the *gradient* differs (up to 10 %) at non-equilibrium points: expected, the twist chart is not commutative; it matches at equilibria. A test pinning only gradient-FD at generic points would be wrong. |
| 2c | Non-convergence never silently accepted | AGREE with caveat | `max_iter=2` from a far start returns ok=False, resid > 1e-4; `settle()` keeps the old state, counts `eq_failures`, logs `no_equilibrium`, `strict` raises (my test uses a real failure, not only the existing monkeypatch). Caveat: `strict` defaults False and nothing in simkit or the study scripts asserts `eq_failures == 0` (only 2 tests do). Accept threshold is 1e-4 (tol_f is 1e-6), documented. |
| 3a | Roll/pitch from moment balance | AGREE | scipy `root` on my own moment function reproduces roll/pitch to 1e-6 deg and tensions to 1e-6 N at 4 poses |
| 3b | "Least-total-tension" distribution is valid and nonnegative | DISAGREE (wording and validity) | code is the minimum 2-norm solution, not min sum(T). The LP minimum is a vertex with 1-2 lines at zero and gives a tilt 0.5-1.2 deg different. Min-norm tension is negative in 51 of 2000 sampled work-volume poses (down to -0.4 N); `solve` still returns ok=True and `R_at` uses it (only `.taut` is False). |
| 3c | Single [0,0,0] point = old model | AGREE | against the pre-change module from `git show 14d5981`: lengths, unit vectors, Jacobian, `R_at`, `tension_distribution` (tensions, max, feasibility) and `forward` are bit-for-bit equal over 25 random poses, with and without R. |
| 4 | Body-frame numbers vs CAD | AGREE (v6 head) | line/surface intersection from the STEP: inner mouths +-42.071 mm, z = 0, hole elevation 20.97 deg; outer mouth radial +-54.14 (edge extent; 54.09 stated) and z +6.54 (6.52 stated); A-D corner order and room-corner order consistent; camera (0, 90, -5.63) mm from CAMBAY_CAM_R and LENS_FRONT_Y = 1.9 over a bay origin 7.53 mm below the mouth plane; rpy [pi,0,0] is a proper rotation (optical axis -z, image x = body x). Re-running the v6 loader gives tip (-0.00045, 0.0025, -0.5173) exactly, CoM (0.0008, 0.00084, -0.1969) and 2059 g vs JSON (0.0008, 0.0012, -0.1964) and 2065 g (0.4-0.6 mm, benign; coincides with the camera-bay STEP being regenerated at 23:07 by someone else). |
| 5a | Limit-cycle fix | AGREE (mechanism), peak 20.3 -> 6.3 N not re-run (50 min study) | at the recorded state the solver's energy is <= an independent 6-DOF BFGS minimum and T_max < 7 N; the old algorithm is reproduced cycling by the implementer's test |
| 5b | Yaw sensitivity 2.4-3.7 deg/mm | AGREE | elastic plant, 9 poses, worst 1 mm direction: 2.8-3.6 deg/mm. Tilt-free linear model at 9 poses: 5.5-6.1 deg/mm (their 4.7-6.5). |
| 5c | Sigma 12.8 -> 15.4 mm | NOT EXPLAINED (see 3) | |

## 2. Stale after v7 / D28 (reported, not fixed)
* `lowest_point_body_m` z = -0.5173 (v6 jaw tips): D28 says the tie-off box is 474 mm above the jaw tips when gripping, so z_floor, the workspace floor limit and the task heights are off by about 43 mm (8 %) or more.
* `com_body_m` and the whole mass basis: from a 2.06 kg v6 CAD solid set (head 1044 g); the v7 head is 481 g CAD / 376 g printed, tube is 50 mm shorter. `claw.mass_kg` = 0.6 matches neither the 450 g budget nor the 1.05-1.25 kg printed estimate in DESIGN_STATE. Tilt is homogeneous in mass but strongly CoM-height dependent: corner-pose tilt 7 deg at z_c = -0.196 m, 9.8 deg at -0.146, 13 deg at -0.10 (CoM at the mouth plane is not pendulum-stable: tens of degrees at the corners, ok=False).
* `camera_in_body.translation_m` x = 0: the working tree (uncommitted D27 camera-bay rework) now puts the lens at bay x = +4.75 mm. Camera y, z and rpy unchanged. `claw.imu: true` contradicts D27.
* b_i (box-relative) and the camera y, z, rpy stay valid; the body frame stays valid because it is box-based.
* Docs: CONTROL_SYSTEM_V1 3.1 still says "IMU roll/pitch + vision yaw", "least-total-tension", and 3 (simulated plant) says "rests upright" while the code now keeps the equilibrium tilt on the floor.

## 3. The calibration-sigma rise and the test fixture
* R is **not** an unknown in the estimator: it is a fixed per-sample input; only a per-reading noise term |b_i| * 4 mrad (0.24 mm) is added to the 1 mm length sigma. "Attitude unknowns added" is not what the code does.
* Controlled experiment (same 25 poses, same noise, point-claw estimator vs four-point estimator, 6 seeds): mean absolute sigma 13.54 mm (point) vs 13.42 (spaced, no attitude noise) vs 13.66 (4 mrad) vs 14.76 (10 mrad). The measurement model explains +1 % to +9 %, not the +33 % (11.6 -> 15.4 mm) reported. Predicted length sigma is identical to 0.02 mm. So the rise comes from something else in the protocol (the +-4 deg visibility cone shrinking the usable pose set, longer probing / different probed fraction, tilted-claw geometry, or seed effects) and has not been isolated by the implementer. It is not a purely physical result and not proven to be an artefact.
* Consequence: with the default threshold (5 mm) no seed reaches VERIFIED any more (implementer's own table). Relaxing `calibration.length_sigma_max_m` to 7.5 mm in `test_margin_trust.py` is acceptable only as an isolating fixture (that test is about k*sigma vs margins), and it is documented honestly. It does mask a real functional regression of the default startup. A test that pins the default behaviour (xfail until diagnosed) is missing.

## 4. Other judgements
* **+-4 deg visibility cone**: conservative (adds a requirement), not loosening, so not test-fitting in a dangerous direction. Evidence: 6 mm worst-direction length error tilts the stiff-line claw by only 0.1-1.1 deg. But the dominant tilt uncertainty is CoM height and payload (3-6 deg, section 2; a 0.9 kg payload changes a corner tilt by about 3.5 deg and `R_at` plans with the unloaded mass), which the cone does not cover.
* **`_same_valley` ambiguity relaxation**: logically sound (same heading, no chi-squared barrier on a 3-point line scan), but has no direct unit test either way and a 3-point scan can step over a narrow barrier. Alternates it swallows are no longer logged. The evidence that it is not test-fitting is only the red WIP history.
* **Known gaps**:
  * `claw.imu` still true: **High**. All sigma/trust numbers assume IMU-grade roll/pitch (3 mrad); under D27 they come from a small-marker pose (10 mrad rot_sigma, 'tilt is its least accurate quantity') or from CoM-sensitive statics. At 30 mrad the attitude contribution (1.8 mm) exceeds the 1 mm length noise. The non-IMU branch exists but the study was not re-run with it.
  * Rim-bearing path error: **Medium** (hardware-only, invisible to the simulator because plant and controller share the model). Angle between line and hole axis: median 25, p95 45, max 64 deg; only 0.8 % of lines are within the 2.4 deg that a 1.5 mm x 18.2 mm hole passes freely. Pose-dependent path error 18.2(1 - cos): std about 1.2 mm, p95 5.4, max 10.3 mm. Not mentioned: the force line of action passes the rim, a lateral shift 18.2 sin: median 7.8, p95 12.9 mm, which moves the predicted tilt by median 1.3 deg (max 2.5) between inner- and outer-mouth models. With 3-6 deg/mm yaw sensitivity this matters.
  * `boundary_sigma` 3-DOF: **Low**. For 5 mm length errors the elastic plant moves the origin 7.9-9.2 mm rms vs 7.5-8.2 mm from the 3-DOF pinv (<= 15 % low); jaw tip moves 8.1-12.2 mm; yaw swings 3.4-5.5 deg.

## 5. Findings (severity, evidence, action)
1. **High** attitude knowledge is IMU-grade in sim, D27 removed the IMU: set `claw.imu=false` in the sim profile, use a vision-only attitude sigma (>= 10 mrad), rerun the floor-reference study; until then treat 12.8/15.4 mm and trust outcomes as optimistic.
2. **Medium** sigma rise unexplained, default config cannot reach VERIFIED: isolate (cone on/off, probe on/off, same pose list); add an xfail test for the default threshold; keep the 7.5 mm fixture only with that test.
3. **Medium** config inputs stale/inconsistent after v7+D28 (lowest point, CoM, mass 0.6 vs 0.45 vs ~1.1 kg, camera x +4.75 mm): regenerate `claw_body_frame.json` from the v7 assembly after the CAD settles; tilt prediction is CoM-height sensitive, so measure the real CoM.
4. **Medium** rim-bearing model (path and line of action): measure on hardware (decision D-G), or model outer-mouth contact with a bearing-angle rule; do not rely on mm-level lengths before.
5. **Low** distribution is min 2-norm, not least total tension, and can be negative: fix the wording or add a nonnegativity fallback; make `R_at` fall back (or flag) when `taut` is False.
6. **Low** `eq_failures` never asserted by the harness: assert it in `simkit`/study teardown.
7. **Low** `_same_valley` untested; `R_at` ignores payload mass; docs stale (3.1, plant paragraph).

## 6. Test counts
* `OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr/test_rigid_body.py tests/cdpr/test_core_models.py tests/cdpr/test_multi_attachment_review.py`: 43 passed (28 + 15). `tests/cdpr/test_kinematics*.py` does not exist.
* Full `tests/cdpr tests/firmware` (incl. my 15): 195 tests, all passed, no failure or skip marker (-q -q run, 195 dots to 100 %). That is the implementer's 180 plus my 15.

## 7. Verdict
CONDITIONALLY ACCEPTED as a model and simulator (kinematics, Jacobians, equilibrium, Hessian, point-claw reduction and CAD mouth numbers all verified independently). NOT ACCEPTED as evidence for calibration accuracy or trust: those numbers rest on an IMU that D27 removed, on pre-v7 CAD inputs, and on a sigma increase nobody has explained. Before hardware: findings 1-4.
