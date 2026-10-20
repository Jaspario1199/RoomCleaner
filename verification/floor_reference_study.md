# Floor reference sizing study (simulation only)

Scope: how the absolute cable-length sigma after self-calibration (the quantity the bead gate uses,
docs/CONTROL_SYSTEM_V1.md 6.4 and decision D-B) and the actual absolute L0 error change when the single 6 in
AprilTag is replaced by a larger printed floor reference. Driver: `scripts/sim_floor_reference_study.py`
(`--suite main|wide|sens|all`, `--seeds N`, `--out file.json`).
All numbers come from the full simulated startup (`Supervisor.start()` on `fast_cfg()`, config
`robot.sim.json`: anchor prior 5 cm, `length_sigma_m` 1 mm, `payout_scale_sigma` 3 mm/m, bead overtravel 12 mm,
k = 3). `pytest -q tests/cdpr -x`: 92 passed after the changes.

## Bottom line

1. A bigger board lowers the PREDICTED absolute sigma from about 25 mm (single tag) to 17 mm (0.6 m board),
   12.5 mm (1.0 m) and about 11 mm (1.5 m), then saturates (9.3 to 11 mm even with a 1.0 to 1.2 m excitation box).
   No board extent got below 9 mm, so neither 5 mm nor 2 mm is reachable by the floor reference alone. Nine sparse
   sheets (3x3, 0.42 m pitch, 1.0 m span) do as well as 25 dense sheets (5x5): the extent matters, the tag count
   does not.
2. The ACTUAL |L0| error did not improve: median 62 to 117 mm (max 217 mm) with boards against median 69 mm
   (max 93 mm) with the single tag, i.e. up to 7 to 17 times the claimed sigma with a board against 3.6 times for the
   single tag. Calibration acceptance fell from 5/5 (single tag) to 1 to 3 out of 5 (startup rejects its own fit:
   witness RMS, witness chi2 or "ambiguous alignment"). With a more precise camera the pipeline exposes a
   millimetre-scale cable-length model mismatch (see "What dominates the ACTUAL error"); the board makes that
   visible rather than fixing it.
3. What limits the predicted sigma is not the camera: halving pixel noise or cutting IMU tilt noise 3 to 1 mrad changes
   it by 1 mm or less. It is set by the excitation geometry, the 5 cm anchor prior and the 1 mm per-reading cable
   length noise; all vision noise together accounts for about 40 to 45 %. Anchors placed to 1 cm would give about 8 mm,
   to 0.5 cm about 5 mm.
4. The bead-gate sigma also contains a payout-scale term (3 mm/m times the distance from the claw to the bead trigger
   length): 5 to 7 mm at the end-of-calibration pose. That term alone exceeds the 2 mm the gate needs
   (overtravel / 2k = 12 / 6). A larger overtravel is therefore still needed whatever the floor reference: about
   6 x gate sigma, i.e. about 75 to 85 mm with the best board (gate sigma 12 to 14 mm) and about 155 mm with the
   single tag, unless an independent absolute length (tape-measured line length at a known pose, D-B option 3) is added.

## Method and hooks (sim-side only, defaults unchanged)

* `roomcleaner/cdpr/sim/world.py`: new `FloorBoard` (grid of tags centred on the marker origin) and an optional
  `board=` argument of `SimCamera`. The reference counts as seen when ANY tag is fully in view and at least the
  detector minimum size. The effective span fed to the existing depth-noise model is `edge_eff` of the visible tags:
  "extent" = geometric mean of the x/y extents of the visible tags' outer corners (optimistic; the span definition in
  the brief), "rms" = sqrt(2) x RMS corner radius (conservative for a filled grid). Both reduce to the tag edge for one
  tag. Optional per-tag layout error (xy sigma, yaw sigma = error / tag edge) that the estimator does not know.
  With `board=None` the original code path runs unchanged.
* `roomcleaner/cdpr/startup.py`: class attribute `StartupSequencer.study_board = None` (marked STUDY HOOK). When set,
  `_feasible()` uses `board.visible(...)` instead of `marker_visible(...)` for the single tag and `cov_fn` uses
  `board.edge_eff(...)`. Needed because the excitation design otherwise keeps only poses where the centre tag is in
  view. No estimator math, gate, threshold or default was changed.
* Tags are 0.16 m (fits a Letter sheet with a 28 mm border); 0.22 m pitch is one Letter sheet per tag. Quoted spans are
  outer-corner extents.
* Check of the camera model (scratch script, not in the repo): over 400 random poses the fused vision position error
  against truth had chi2/dof 0.45 (single tag) and 0.10 (7x7 board). The estimator's assumed vision covariance is
  conservative and unbiased on both paths, so the board model is not the cause of the findings below.
* Tilt sensitivity sets both the simulated IMU noise and the estimator's `tilt_sigma` (defaults: sim 2 mrad,
  estimator 3 mrad). Seeds 0 to 4 (main), 0 to 2 (wide box, sensitivity). About 1.5 to 2 min per run, four parallel
  processes.
* sigma and error columns use the final fit when the calibration was accepted and a refit of all fit samples (when at
  least 20 exist) when startup rejected it; rejected runs are not READY and have no trust level or bead status. The
  bead status of every accepted run was BLOCKED (absolute sigma above the gate) and the trust level LOCAL_ONLY.

## Results, cases 1 to 3 (default excitation box, 5 seeds)

| Case | accepted/runs | predicted σ_abs med / max (mm) | actual max\|ΔL0\| med / max (mm) | worst err/σ | trust / bead | witness RMS (mm, max of accepted) | bead-gate σ incl. payout term (mm, med) | run time (s) |
|---|---|---|---|---|---|---|---|---|
| 1 baseline single 6in tag | 5/5 | 25.1 / 30.4 | 69 / 93 | 3.6 | LOCAL_ONLY / BLOCKED | 3.46 | 25.7 | 118 |
| 2a board_span 0.30 (existing opt) | 4/5 | 24.6 / 29.8 | 50 / 92 | 3.1 | LOCAL_ONLY / BLOCKED | 2.17 | 25.2 | 119 |
| 2b board_span 0.60 (existing opt) | 4/5 | 25.1 / 30.4 | 68 / 87 | 3.1 | LOCAL_ONLY / BLOCKED | 2.13 | 26.0 | 120 |
| 3a dense 3x3 p0.22 (0.60 m, 9 sheets) | 3/5 | 17.3 / 17.4 | 83 / 117 | 7.0 | LOCAL_ONLY / BLOCKED | 4.59 | 18.1 | 89 |
| 3b dense 5x5 p0.21 (1.0 m, 25 sheets) | 2/5 | 12.4 / 13.4 | 90 / 169 | 12.7 | LOCAL_ONLY / BLOCKED | 3.91 | 13.3 | 83 |
| 3c sparse 3x3 p0.42 (1.0 m, 9 sheets) | 2/5 | 12.7 / 13.6 | 96 / 160 | 11.8 | LOCAL_ONLY / BLOCKED | 2.99 | 13.9 | 121 |
| 3d sparse 5x5 p0.34 (1.5 m, 25 sheets) | 2/5 | 11.2 / 14.8 | 62 / 79 | 6.9 | LOCAL_ONLY / BLOCKED | 4.53 | 14.2 | 108 |
| 3e very sparse 3x3 p0.67 (1.5 m, 9 sheets) | 1/5 | 12.4 / 13.0 | 117 / 217 | 17.5 | LOCAL_ONLY / BLOCKED | 3.05 | 13.6 | 128 |
| 3f dense 7x7 p0.22 (1.5 m, 49 sheets) | 2/5 | 11.1 / 15.0 | 77 / 109 | 9.9 | LOCAL_ONLY / BLOCKED | 1.37 | 12.2 | 100 |
| 3g dense 5x5 p0.21, rms span | 3/5 | 12.6 / 14.2 | 65 / 86 | 6.9 | LOCAL_ONLY / BLOCKED | 4.10 | 13.9 | 105 |
| 3h dense 7x7 p0.22, rms span | 1/5 | 10.5 / 11.7 | 93 / 128 | 10.9 | LOCAL_ONLY / BLOCKED | 3.04 | 12.1 | 109 |

Excitation (mean over runs): fit-pose extent in the marker frame 1.51 m (single tag), 1.98 m (0.6 m board), 2.2 m
(1.0 m and 1.5 m boards, limited by the 0.8 m half-box); mean cable-direction spread seen from the anchors 0.203,
0.231, 0.244, 0.237 rad. The board widens the excitation by about 45 % and the direction spread by about 20 %, then the
box is the limit.

Rejections: "ambiguous alignment (alternate optimum)" in the local stage in 8 of 40 board runs (seeds 1 and 2) and in 0
of 15 single-tag / span-only runs; "witness position RMS 6.3 to 17 mm > 6 mm" and "witness errors 4 to 9x predicted
variance" in the expanded stage.

## Wider excitation box and stiffer cable (3f 7x7 board, 3 seeds)

Box = `calibration.expanded_box_m` half extents (xy/z, default 0.8/0.5), overridden in memory only. EA x10 = cable
stiffness 200 kN instead of 20 kN in the plant.

| Case | accepted/runs | predicted σ_abs med / max (mm) | actual max\|ΔL0\| med / max (mm) | worst err/σ | trust / bead | witness RMS (mm, max of accepted) | bead-gate σ incl. payout term (mm, med) | run time (s) |
|---|---|---|---|---|---|---|---|---|
| 6a 3f, box 1.0/0.5 | 0/3 | 9.5 / 9.7 | 72 / 77 | 8.2 | not READY (calibration rejected) | – | – | 92 |
| 6b 3f, box 1.2/0.5 | 0/3 | 9.7 / 9.8 | 69 / 72 | 7.4 | not READY (calibration rejected) | – | – | 100 |
| 6c 3f, box 1.2/0.5, cable EA x10 | 0/3 | 9.5 / 9.6 | 80 / 89 | 9.2 | not READY (calibration rejected) | – | – | 120 |
| 6d 3f, box 0.8/0.5, cable EA x10 | 0/3 | 11.0 / 11.4 | 63 / 67 | 6.4 | not READY (calibration rejected) | – | – | 110 |
| 6e baseline tag, box 0.8/0.5, cable EA x10 | 3/3 | 26.4 / 29.8 | 80 / 104 | 3.5 | LOCAL_ONLY / BLOCKED | 4.06 | 26.9 | 131 |
| 6f 3f, box 1.2/0.8, cable EA x10 | 0/3 | 9.3 / 9.5 | 61 / 69 | 7.2 | not READY (calibration rejected) | – | – | 128 |

A wider box raises the cable-direction spread (0.24 to 0.27 at 1.0 m and 0.30 at 1.2 m) and lowers the predicted
sigma to about 9.5 mm, but no board run was accepted. A ten times stiffer cable does not change that, so cable
stretch is not the cause.

## What dominates the predicted absolute sigma

Refit of the SAME samples with the vision covariance (split into pixel, tilt and rotation parts, reconstructed to 0.2 %)
and the priors rescaled; mm, max over stations, median over runs with 30 or more fit samples:

| Group (n runs) | as run | pixel noise x0.5 | IMU tilt x1/3 | all vision noise to 0 | cable length noise x0.5 | anchor prior 2 cm | anchor prior 1 cm | anchor prior 0.5 cm | vision to 0 + length noise x0.1 | same + anchor 1 cm |
|---|---|---|---|---|---|---|---|---|---|---|
| single tag (8) | 25.5 | 24.6 | 24.2 | 14.6 | 17.6 | 17.6 | 10.4 | 5.7 | 3.0 | 2.6 |
| board 0.6 m (3) | 17.3 | 16.9 | 16.7 | 7.6 | 13.0 | 13.9 | 9.4 | 5.5 | 1.3 | 1.3 |
| board 1.0 m (12) | 12.7 | 12.5 | 12.3 | 6.4 | 9.6 | 11.2 | 8.7 | 5.4 | 1.2 | 1.1 |
| board 1.5 m (16) | 11.0 | 11.0 | 10.7 | 6.2 | 7.8 | 10.0 | 7.9 | 5.4 | 1.2 | 1.3 |
| 1.0 to 1.5 m, wide box / sensitivity (22) | 10.1 | 10.1 | 10.1 | 5.0 | 7.1 | 9.4 | 7.6 | 5.1 | 0.8 | 0.8 |

* Geometry and excitation extent: this is what the board buys (25 to 11 mm). The absolute length is the anchor-range
  component along each cable. It is seen only through the second-order change of the cable direction over the poses
  (direction spread 0.2 to 0.3 rad, gain roughly with its square) and is otherwise held by the 5 cm anchor prior. The
  gain saturates when the excitation box, not the board, is the limit.
* Pose noise: pixel noise and IMU tilt are minor (pixel x0.5 plus tilt x1/3 together move the sigma by 1 mm or less).
  IMU noise 3 / 1 / 0.3 mrad gave 10.8 / 10.2 / 10.1 mm predicted on the 3f board. All vision noise to 0 explains
  roughly 40 to 45 % (25 to 14.6 mm single tag, 11 to 6 mm board).
* The rest is the 1 mm per-reading cable length noise and the anchor prior. About 1 mm needs vision at 0 and 10 times
  lower length noise; anchors placed to 0.5 to 1 cm already give 5 to 8 mm on their own.
* The length-noise x0.1 refits jump between local optima on some seeds; use the medians, not single runs.

## What dominates the ACTUAL error (why the board does not help in practice)

Oracle check: each calibration sample evaluated at the TRUE anchors and TRUE L0, so that only sample noise and
unmodelled physics remain (runs `1 baseline`, `3a`, `3f`, `6e`, seeds 0 to 2; residual = span minus modelled length, mm):

* seed 0, single tag: mean residual per cable A..D [-1.8, 0.5, -6.2, 0.7], RMS [5.1, 1.9, 9.4, 1.8]. Cable C is slack
  (longer than its span) by more than 3 mm in 22 of 38 samples, growing with height: mean -0.7 mm below 0.45 m,
  -3.3 mm at 0.45 to 0.8 m, -8.9 mm above 0.8 m.
* The same pattern in the 3x3 and 7x7 board runs (cable C mean -8.1 and -6.9 mm, 22 and 21 samples beyond 3 mm) and with
  a 10 times stiffer cable (cable C mean -6.1 mm, 23 samples). So it is the commanded-pose / hang mismatch (the claw
  hangs on three cables and the fourth carries mm of slack because the model is off by centimetres), not stretch.
* The slack classifier drops a cable only if it is more than `slack_k` = 3 sigma = 3 mm beyond its span, and at most one
  per sample; up to 14 samples per cable sit at 0.5 to 3 mm slack and enter the fit as ordinary length readings. A common
  bias of a few mm over this pose range is amplified into L0 by the same weak second-order geometry that makes the
  sigma large (order of magnitude 30 to 50 times, estimated from direction spread 0.2 rad, not measured). That
  reproduces the 50 to 120 mm L0 errors. A precise board removes the vision noise that used to mask it: the fit then
  claims 10 to 13 mm, is wrong by 7 to 17 sigma, and the witness and alignment-ambiguity checks reject the calibration
  more often.
* A diagnostic refit with `slack_k` = 1 mm cut the actual error from 57 to 11 mm and from 72 to 15 mm on two runs and
  did little on others; it is not a validated fix. This is an estimator/excitation matter for the lead to decide
  (sub-3 mm slack classification, a tension margin on the excitation poses, or inflating length noise for poses
  above about 0.5 m); nothing was changed here.

## Sensitivity (cases 4 and 5: 3f 7x7 board = best predicted sigma, 3 seeds)

Predicted sigma is flat in IMU tilt noise (3 / 1 / 0.3 mrad: 10.8 / 10.2 / 10.1 mm) and in pixel sigma (0.6 px: 10.6 mm;
0.15 px: 16.5 mm from the single run with 20 or more fit samples, confounded by a different pose design), in line with
the table above. Acceptance and actual errors are dominated by the model mismatch, not by these noises.

| Case | accepted/runs | predicted σ_abs med / max (mm) | actual max\|ΔL0\| med / max (mm) | worst err/σ | trust / bead | witness RMS (mm, max of accepted) | bead-gate σ incl. payout term (mm, med) | run time (s) |
|---|---|---|---|---|---|---|---|---|
| 4 pixel_sigma 0.15 | 0/3 | 16.5 / 16.5 | 57 / 57 | 3.5 | not READY (calibration rejected) | – | – | 60 |
| 4 pixel_sigma 0.6 | 1/3 | 10.6 / 10.6 | 60 / 71 | 6.7 | LOCAL_ONLY / BLOCKED | 1.63 | 12.5 | 79 |
| 4 tilt 0.3 mrad | 1/3 | 10.1 / 10.1 | 69 / 72 | 7.2 | LOCAL_ONLY / BLOCKED | 1.41 | 11.6 | 77 |
| 4 tilt 1 mrad | 1/3 | 10.2 / 10.3 | 93 / 118 | 11.5 | LOCAL_ONLY / BLOCKED | 3.43 | 12.1 | 85 |
| 4 tilt 1 mrad + pixel 0.15 | 0/3 | 10.0 / 10.2 | 85 / 97 | 9.5 | not READY (calibration rejected) | – | – | 87 |
| 4 tilt 3 mrad | 2/3 | 10.7 / 10.8 | 43 / 53 | 5.0 | LOCAL_ONLY / BLOCKED | 2.34 | 12.2 | 91 |
| 5 layout err 0 mm (ref) | 1/3 | 11.1 / 11.1 | 109 / 109 | 9.9 | LOCAL_ONLY / BLOCKED | 1.07 | 12.2 | 78 |
| 5 layout err 1 mm | 0/3 | 11.4 / 11.4 | 142 / 142 | 12.4 | not READY (calibration rejected) | – | – | 74 |
| 5 layout err 2 mm | 0/3 | n/a (rejected before 20 fit samples) | n/a | | not READY | | | 41 |

Case 5 (layout error): with 0, 1 and 2 mm random tag offset (unknown to the estimator) 1/3, 0/3 and 0/3 runs were
accepted. The 0 mm reference itself is rejected in 2 of 3 runs, so the experiment cannot isolate the layout effect. The
layout error enters as a pose-dependent bias of 1 to 2 mm, the same size as the vision noise and the slack bias, so a
layout accurate to about 1 mm should be treated as a requirement. No usable accuracy figure for this case.

## Answers to the acceptance questions

* Dominant term: (1) excitation geometry plus the 5 cm anchor prior and the 1 mm cable length noise set the predicted
  sigma (the board improves the geometry and the vision half only); (2) a pose-dependent slack mismatch of a few mm
  dominates the actual error and is amplified by the weak absolute-length geometry; (3) pose noise (pixel, tilt) is
  secondary.
* Minimum board extent for sigma under 5 mm: none found. Under 2 mm: none. Predicted sigma plateaus at about 10 to
  11 mm from about 1.0 m extent upward (9.3 to 9.8 mm with a 1.0 to 1.2 m excitation box). Under 5 mm needs the anchors
  known to 0.5 cm in addition; under 2 mm also needs vision noise near 0 and 10 times lower length noise.
* Overtravel: still needed. The bead-gate sigma with the best boards is 12 to 14 mm (absolute sigma plus a 5 to 7 mm
  payout-scale term), so 2 k sigma needs about 70 to 85 mm of overtravel against 12 mm available; the single tag needs
  about 155 mm. The early gate (`bead_length_sigma_max_m` 10 mm) would also still fail.

## Assumptions and limitations

* Simulation only. Noise models are the project's own (pixel sigma 0.3 px, rotation sigma, white IMU tilt noise); a real
  IMU has bias and mounting error that white noise does not capture, which would make tilt matter more.
* The multi-tag model combines tags through an effective span in the existing depth-noise formula. It does not run a
  real multi-tag PnP, and does not model print scale error, paper curl, floor unevenness or sheet gaps beyond the
  optional random layout error; tags are assumed detected whenever fully in view (no glare, no laundry on tags).
* Small samples: 3 to 5 seeds per case; acceptance rates and ratios carry large uncertainty. Seeds 1 and 2 fail most board
  cases in the local stage, so board statistics lean on seeds 0, 3 and 4.
* Anchor prior (5 cm), `length_sigma_m`, `payout_scale_sigma` and the excitation box are the sim config values.
* The what-if refits reuse the same samples and are not independent runs. The slack finding comes from simulated oracle
  residuals; whether the real cable behaves the same (tension margin, friction, sag) must be measured on hardware.
