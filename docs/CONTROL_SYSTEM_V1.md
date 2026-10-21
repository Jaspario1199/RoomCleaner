# RoomCleaner control system V1 — calibration, coordination, safety logic

Date: 2026-10-19. Code: `roomcleaner/cdpr/` (host), `firmware/winch_station/` (station
core, C++), `firmware/claw_s3/` (claw node). Simulation evidence: `tests/cdpr/`.

This document is the logic contract for the four-cable robot: what every part
does, what it is allowed to believe, and when it must stop. It answers the
calibration/control handoff of 2026-10-16 (questions in §12) and supersedes no
earlier document. The Codex startup study (`docs/STARTUP_CALIBRATION_V1_20261016.md`)
remains the research background.

**Status, plainly:** the logic is implemented and passes in simulation
(physics, network loss/jitter, faults). **None of it has run on the physical
four-station rig yet.** Every hardware-dependent number in
`config/robot.example.json` is `null` until measured, and the code refuses to
run a stage whose numbers are missing.

---

## 1. Operator experience

1. Place the claw upright on the floor near the middle of the room. Put the
   printed marker (AprilTag 36h11 id 0; print with `python -m tools.print_marker`)
   under the camera.
2. Open the setup page on a phone (`python -m roomcleaner.cdpr.service`,
   port 8100). Enter or confirm room size and anchor positions.
3. Tick the pre-start checklist (room clear, power strip in reach, claw and
   marker placed, cables on pulleys, LiPo balance-charged) and press **Start
   calibration**.
4. The page walks through SELF_CHECK → SLACK_TAKEUP → INITIAL_LIFT →
   VISUAL_INITIALIZATION → CALIBRATION → REFERENCE_VERIFICATION → READY and
   shows the trust level (VERIFIED or LOCAL_ONLY), what VERIFIED rests on
   (the margin numbers, or beads) and, if restricted, the plain reasons.
5. **PAUSE** holds position at any time. The switched power strip is the
   emergency stop and drops the claw.

---

## 2. Architecture

| Component | Runs | Responsibility |
|---|---|---|
| Host PC | `roomcleaner/cdpr` | vision, calibration, planning, coordination, supervision, logging |
| Station ×4 (XIAO ESP32-C3 + A4988 + AS5600 + NC bead switch) | `firmware/winch_station` | local step generation from Hermite segments, encoder tracking, switch capture, feed-hold, lease, faults |
| Claw (XIAO ESP32-S3 Sense + MG996R; no IMU, D27) | `firmware/claw_s3` | timestamped JPEG frames, battery, grip (obeys; the host approves grips) |
| Phone | `roomcleaner/cdpr/static/setup.html` | setup, start/pause, recovery, confirmed disarm |

Host layering (each layer only uses those below it):

```
service (HTTP API, phone page)
supervisor (DISARMED/STARTUP/READY/TASK/PAUSED/FAULT/RECOVERY_REQUIRED/PARKED)
startup sequencer · task runner · bead verifier
calibration (estimator, identifiability, excitation design) · perception (claw pose)
coordinator (synchronized segment streams, holds, completion) · trust ledger
trajectory (Cartesian/cable plans) · kinematics/statics · spool model · frames · config
station link / clock model / transport (UDP or simulated network)
```

The **Python station core** (`roomcleaner/cdpr/station_core.py`) is the
executable specification of the firmware; the C++ core is checked against it
trace-by-trace (`tests/firmware/`).

---

## 3. Models

**Frames.** R = room (anchor coordinates), M = marker (on the floor), B = claw
body (origin on the tube axis at the height of the four line attachments, +z up
the tube, +x = v6 world X, +y = −v6 Z so the camera bay is at +y; at claw yaw 0
the body axes equal the room axes), C = camera. `T_A_B` maps B→A.
Vision gives `T_C_M`; the claw pose is `T_M_B = inv(T_C_M)·inv(T_B_C)`.

**Cables (3.1, multi-attachment).** `L_i = |a_i − (p + R b_i)|`, straight and
taut, sag neglected (Dyneema, < 1 kg). The real claw ties its four lines off at
**four separate points** `b_i`: the *inner mouth* of the radial cable hole through
each corner fillet of the electrical box (user direction 10/20), taken from the CAD
by `scripts/extract_claw_body_frame.py` → `verification/claw_body_frame.json` →
`claw.attachment_points_body_m` (station order A, B, C, D = body corners (−,−),
(+,−), (+,+), (−,+); (±42.07, ±42.07, 0) mm; hole 18.2 mm long, rising 21° outward).
Lengths therefore depend on the orientation `R`, so every length, direction,
Jacobian, tension and workspace check takes `R`:
* **measured** `R` where a vision pose exists: the full vision attitude, roll/pitch against the
  floor reference's normal and yaw (`perception.VisionSource`, i.e. the marker pose `T_M_B`;
  **no IMU, D27**). The camera-to-body *tilt* offset is measured at every startup, while the
  claw rests upright on its jaws over the printout (`StartupSequencer._measure_mount`,
  `attitude.mount_offset_from_up`: the marker normal seen by the camera is body z; the
  rotation about the vertical is unobservable there and keeps its CAD value), stored, saved
  with the model and applied to every later vision pose; startup aborts if it exceeds
  `claw.mount_offset_max_rad` (5°: the claw is not resting upright or the mount is wrong).
  Honest sigma of a vision roll/pitch: `claw.vision_attitude_sigma_rad` = 10 mrad
  (not the 4 mrad of the IMU it replaced) combined with the standard error of the mount
  measurement (frame scatter/√30, about 2–3 mrad). The estimator uses each
  sample's own `R` and `b_i` in the measurement model, the slack hypotheses
  (re-solved at the sample's `R`), the slack probe (response computed with the
  rigid-body 6×6 stiffness), bead verification, witnesses and identifiability;
  the attitude error is added to the length sigma (`calibration.attitude_sigma_rad`·|b_i|);
* **predicted** `R` for a target not yet visited (`Geometry.R_at`, `kinematics.Attitude`):
  rigid-body statics of gravity at the CoM (`claw.com_body_m`, payload at the jaws)
  plus the four tensions, the minimum 2-norm tension distribution (no pretension; it is not the
  least-total-tension LP solution and can be slightly negative at some poses, which `.taut`
  reports), roll/pitch from the horizontal moment balance, **yaw held at the last measured
  value** (`RobotContext.room_pose` updates it). Away from the floor reference this is the
  claw's attitude (D27), valid once the pendulum has settled, with a 1-sigma of
  `claw.statics_attitude_sigma_rad` (4°: it moves with the CoM height and the payload).
  Assumption (VERIFY): the CoM is a CAD estimate without electronics.
* **Yaw is passive.** The four lines leave nearly radially from the corners, so
  yaw is only weakly held: 3.6–6° per mm of line-length inconsistency (linear tilt-free
  model, `verification/claw_camera_bay_verification.md` F6; the elastic simulator gives
  2.4–3.7°/mm). It is measured, never predicted; the same mm-level inconsistencies also
  move the tilt by a few degrees, so the predicted attitude is *nominal* and vision
  closes the loop wherever the floor reference is in view. Backward compatibility: one common point (`attachment: "common"`, b = 0)
  is orientation independent, `R_at` is the identity and the original point-claw
  model is reproduced exactly (`tests/cdpr/test_rigid_body.py`).
* **Known simplification.** The line is a straight chord from the inner mouth to the
  anchor. A line steeper than the 21° hole axis actually bears on the outer-mouth rim, so
  the true path is up to 18.2·(1 − cos θ) ≈ 6 mm longer for θ ≈ 50° and varies a few mm over
  the workspace; the constant part is absorbed by `L0`, the pose-dependent part is a
  model error of mm level. Open item D-G.

**Spool.** Layered winding (Spoolv3: 7.5 → 10 mm radius over the line). With
`line_total = W + L`, one constant per station per boot epoch, `L0` (external
length at motor position 0), maps motor microsteps to length exactly. A
measured payout table can replace the layered model.

**Statics.** Four cables, three force equations: tension is indeterminate.
Planning requires a feasible min-max distribution within
`[min_tension_n, max_tension_n]` at every knot (`kinematics.tension_distribution`);
the residual moment about the CoM at the attitude used is reported.

**Simulated plant (`sim/world.py`).** With spaced attachments the claw hangs as a
**rigid body (6 DOF)**: minimum of gravity (at the CoM) + elastic line energy
(`k_i = EA/ℓ_i`, no compression), found by a Levenberg–Marquardt Newton with the exact
analytic Hessian and an Armijo line search, warm-started. Non-convergence is reported
(`World.eq_failures`, event `no_equilibrium`, `strict` raises) and the previous state is
kept: a non-equilibrium state is never returned. This replaced an undamped 3-DOF
Newton that limit-cycled at some poses and produced spurious 14–25 N tensions
(`verification/slack_probe_review.md` M1). Passive yaw drift under length errors
emerges from the model. On the floor the claw rests on its jaws with the equilibrium attitude of its lines
(upright when they are slack or vertical, slightly tilted when loaded) and yaw is held by friction.

**Overconstraint — measured in simulation, important.** With stiff cables and
any length error, the claw hangs on **three** cables and the fourth goes
slack (up to 48 mm in an early run). Consequences built into the logic:
the estimator decides per sample whether one cable was slack and drops that
reading (§6.2). Excitation grows in stages so model errors stay small. All
position checks solve the pose slack-aware.

---

## 4. Synchronized motion (stations)

Protocol v1: JSON over UDP, one message per datagram, ≤ 512 bytes. Full
message list in `roomcleaner/cdpr/protocol.py`.

* **Segments, not steps.** The host converts a Cartesian path into four
  cable-length histories (never "pull one, release the opposite"). Those
  become motor positions through each spool map, sent as cubic Hermite
  segments `(t0, d, p0, p1, v0, v1)`, all on one shared timeline. Stations
  generate their own steps (DDA timer).
* **Clocks.** The host estimates each station's offset (minimum-RTT SYNC, drift
  term) and sends `t0` in that station's own clock. Motion is refused unless
  every clock uncertainty is ≤ `clock_uncertainty_max_s`.
* **Start.** `T0 = now + start_lead`. Every first-window segment must be
  acknowledged before `T0`, or the motion is aborted before it starts.
  Out-of-order segments are parked. Duplicates are re-acknowledged. Lost
  ones are resent after 40 ms.
* **Coordinated stop = feed-hold in path time.** A hold names a path time τ.
  The host resends it every 20 ms to any station still reporting RUN, so a
  lost datagram cannot leave one winch running while three hold. Any host-side
  exception during a motion also sends the hold before propagating.
  Each station ramps its path-rate to 0 over `hold_us`, so all four
  decelerate **along the same geometric path**.
* **Lease.** No valid host message within `lease_s` → the station holds
  itself and broadcasts the hold to its peers. If a station goes silent, the
  host holds everyone else at the path time where that station's lease will
  stop it (lease-aligned). Measured stop spread in simulation: about 18 ms.
* **Underrun.** If less than half a hold of path remains buffered → self-hold.
* **Completion** is read from repeated telemetry (loss-tolerant): 10/10 lossy
  motions completed in simulation at 2–5 % packet loss.
* **Monitor hook.** A host predicate (e.g. "vision saw the claw move") can
  trigger the same coordinated hold mid-motion. Slack take-up uses it. If the
  monitor raises, that is a stop reason.
* **Path time** on each station integrates the *measured* elapsed time, so
  loop jitter cannot make one winch lag the others.
* **Host loop.** While no command runs, the service keeps pumping (keep-alive
  pings at ≤ lease/4, clock sync) and polls the supervisor every 100 ms. Real
  camera frames are fetched on their own thread so the control loop never
  waits on the network.

### Station fault reactions

| Fault | Meaning | Reaction | Holding torque |
|---|---|---|---|
| TRACKING | encoder vs commanded steps beyond tol for dwell | stop pulses now | kept |
| ENCODER | stale/unreadable/bad magnet | stop | kept |
| SWITCH | bead switch open outside a reference move (bead or broken wire) | stop | kept |
| TIMING / CONFIG | loop overrun / no valid config | stop | kept |
| LEASE / UNDERRUN | coordination at risk, motion itself fine | coordinated hold | kept |

**Stop ≠ disable.** No fault removes torque. Only `disarm` with
`confirm:"claw_supported"` **and the station's per-boot disarm key** (`dk`,
reported only in unicast telemetry) does. A stray or replayed datagram
cannot drop the claw. The supervisor sends it only after a **fresh vision
check** shows the claw on the floor; no stored flag substitutes for that check.

### Encoder role (AS5600 on the spool)

The encoder confirms the motor turned as commanded (missed steps, jam,
wrong direction, magnet loss). It does **not** measure tension, cable slip on
the spool, or absolute multi-turn length: a reboot starts a new epoch and
`L0` is lost. On mismatch the station stops; the host never auto-unwinds.

---

## 5. Trust ledger (what survives what)

`roomcleaner/cdpr/trust.py`. Levels: **NONE < LOCAL_ONLY < VERIFIED**, plus
`recovery_required` and `claw_supported`.

| Event | Station references | Room geometry | Result |
|---|---|---|---|
| coordinated stop (pause, lease, underrun, peer hold) | kept | kept | unchanged; a latched lease/underrun shows FAULT until `acknowledge` |
| tracking / encoder / timing fault | that station invalid | kept | RECOVERY |
| unexpected bead switch | that station suspect | kept | RECOVERY |
| station reboot | that station's epoch lost | kept | RECOVERY |
| host restart | kept only if every boot id matches and no latched fault | kept | restored or RECOVERY |
| power loss (strip) | all lost; claw may have dropped | kept | NONE, floor restart |
| marker moved / missing | kept | marker registration invalid | LOCAL_ONLY until re-registered |
| camera calibration changed | kept | visual products invalid | NONE for vision |

**Basis of VERIFIED (D26).** VERIFIED means "the whole commanded workspace may
be used" and is never granted silently. The ledger records
`verified_basis` (`"margin"` or `"beads"`), `margin_check` (k, sigma, margin,
k·sigma and worst pose for the ceiling and for the walls, the probe coverage,
the witness chi-squared, the bead notes) and, below VERIFIED, `trust_reasons`
in plain words. It is re-decided at every startup (§6.5); any event in the
table above that lowers the level also clears the basis and states which
station or registration was lost. `/api/status` carries it as
`trust: {level, basis, full_workspace, reasons, margin}` and the setup page
prints it under the level. Ledgers written before D26 load with the new
fields empty.

A reboot of anything never resumes a task or a startup. `claw_supported`
fails closed:
* unknown means "may be hanging";
* it is written durably (atomic, fsync) False before the first lift command;
* it is written True only after a vision floor check.

The calibrated model (`data/cdpr/model.json`) is persisted. After a host
restart, stations with unchanged boot ids keep their references, so a hanging
claw can still be recovered or lowered by software.

---

## 6. Startup and self-calibration

Implementation: `startup.py` (states), `calibration.py` (estimator),
`homing.py` (beads), `perception.py` (claw pose). Every step has bounds and
abort conditions. Aborts **hold**; they never disable.

### 6.1 States

| State | Does | Aborts (→ FAULT / PAUSED / RECOVERY_REQUIRED) |
|---|---|---|
| SELF_CHECK | config complete for the stage, suspended motion authorised; stations configured (param hash), synced, fault-free, switches closed, armed; claw online, battery ≥ min; camera calibration id recorded; marker visible and still; **camera-to-body tilt offset measured** (30 frames, claw resting upright on its jaws over the printout, D27) and stored; claw on the floor at the expected height (±3 cm) | any check fails, or the measured mount offset > `claw.mount_offset_max_rad` |
| SLACK_TAKEUP | one station at a time, a slow continuous retraction (claw on the floor = stations uncoupled), bounded by `max_slack_m`. Each vision frame is checked; claw motion ≥ max(onset_translation, k·noise) marks taut onset. Pulling continues to `bearing_translation_m` so the **slide direction** is measured, then a hold and a pay-out of `onset_backoff_m` | no onset within max slack (cable unattached, wrong winding direction, station order); marker lost > 1 s; tilt |
| — after all four | slide bearings vs anchor entries (catches **swapped station wiring**); first fit → L0 per station + marker registration | bearing RMS > limit |
| INITIAL_LIFT | all cables to just-taut, then vertical packets computed from the model's cable directions; vision after each | lateral drift > max, tilt > max, commanded − observed lift > budget, no clearance by `max_lift_m` |
| VISUAL_INITIALIZATION | still pose while suspended → refit (with `startup.slack_probe`: probed first, §6.1a) | marker lost |
| CALIBRATION | staged excitation: local box → intermediate → expanded, D-optimal poses + held-out witnesses, refit between stages (with `startup.slack_probe`: every pose probed first, §6.1a) | witness, residual, ambiguity or outlier failure; probe: no taut onset within `probe_max_m`, claw moved > 10 mm without onset |
| REFERENCE_VERIFICATION | the trust decision (§6.5): margin check `assess_margin_trust`; the bead search per station (§6.4) only if `startup.bead_search` (default off), verified captures refit jointly | bead fault; refit rejected |
| READY | trust level VERIFIED (basis `margin`, or `beads` if every bead was verified) or LOCAL_ONLY with stated reasons | — |

### 6.1a Per-pose slack probe (`startup.slack_probe`, opt-in, simulation-validated only)

**Why.** Suspended, four cables over-constrain the claw: with any length-model error the claw hangs on three cables and
one (which one changes with the pose) carries a few mm to 20 mm of slack. The fit-based slack classifier only drops a
reading more than `slack_k` (3 mm) beyond its span, so slack of 0.5 to 3 mm enters the fit as an ordinary length. That
bias is amplified into `L0` by the weak absolute-length geometry (`verification/floor_reference_study.md`).

**What.** Before every suspended sample (the VISUAL_INITIALIZATION pose and every CALIBRATION fit/witness pose), after
the claw has settled, each station in turn is probed (`StartupSequencer._probe_pose` / `_probe_cable`):

1. A still reference pose (`probe_frames` frames; more, up to `probe_frames_max`, where vision is noisy).
2. Cable `i` is retracted in steps of `probe_step_m` (0.5 mm; the step grows x1.5 up to `probe_max_step_m` while no
   response is seen), `probe_settle_s`, then a still pose after every step. All motion is `plan_cable_move` packets through
   `Coordinator.execute` (readiness, lease, tracking, station faults, pause, hold unchanged).
3. Onset analysis (`hinge_analysis`): the claw does not move until the slack `s` is taken up, then moves by
   `w * (r - s)` per metre of further retraction; `w` has a Gaussian prior (relative sigma `probe_response_sigma`) from the
   cable geometry (`probe_response`: `x = (sum k_j u_j u_j^T)^-1 k_i u_i`, `k_j ~ 1/L_j`, the modulus cancels). `s` is
   profiled on a grid with the full per-measurement vision covariance. Onset is declared when the hinge beats "no response
   yet" by `onset_noise_k` sigma (the take-up's k) AND the fitted claw motion is at least `probe_onset_translation_m`
   (1 mm, half of the take-up's absolute 2 mm: this is a differential measurement at one pose, no systematic offsets).
   A cable that is already taut gives `s` = 0 within its sigma ("onset on the first step": the retraction is paid back).
4. The measured slack `s` (profile minimum, 1-sigma from the profile) fixes the stopping point: the cable is paid out by
   `(peak retraction - s)` and left just taut (no safety margin, see the results report). The detection overshoot is not
   guessed from a fixed number: it comes out of the fit, which uses every step beyond the onset.
5. After all four cables: optional extra rounds (`probe_rounds`, default 1): a cable is re-probed only if the claw has since
   moved toward its anchor by a detectable amount (a later probe loosened it).
6. The sample is taken with all probed cables just taut and carries `PoseSample.taut` (per cable) and `taut_sigma_m`
   (the probe's sigma, added in quadrature to `length_sigma_m` for that reading); the per-pose record (slack per station,
   steps, peak retraction, time, skipped cables) goes to `StartupSequencer.probe_log`, `calibration.json` and
   `measurements["slack_probe"]`.
7. The motor positions are then restored to the model-consistent values the planner started from (a pay-out only), so the
   next `plan_line_from` sees exactly the state it would have seen without the probe.

**Estimator.** A probed reading is never a slack-hypothesis candidate (`_assign_slack`, witness check) and gets the
extra sigma; unprobed readings (skipped cables or `slack_probe` off) keep the hypothesis selection described in §6.2 as a
backstop. No gate or threshold changed.

**Bounds and aborts (hold, never disable).** Total retraction per cable per pose <= `probe_max_m` (40 mm): beyond that
without onset the startup aborts to FAULT with "no taut onset within ... mm of probe retraction ... (cable detached or
slipping on its spool, or the model is badly wrong)"; the claw stays on the cables. The claw moving > 10 mm without a
significant onset also aborts. A pause (between steps or mid-step) holds and returns PAUSED. **Vision decides what can be
probed:** from the reference pose the over-retraction at which onset becomes detectable
`rho = max(floor, k * sigma_proj) / |response|` is predicted; if it exceeds `probe_overshoot_max_m` (6 mm) with
`probe_frames_max` frames, the cable is skipped at that pose (not probed blind), which bounds the tension excursion on a
taut cable.

**Limits.** Simulation only. See `verification/slack_probe_results.md` for numbers, the coverage by pose height and the
hardware caveats (tension rise when probing a taut cable on real Dyneema; recommended step; quantisation).

### 6.2 Estimator

* **Attachment points:** every row uses the sample's measured `R` and the
  per-cable `b_i` (`q_i = p + R b_i`); `p` is the body origin (tube axis at the
  attachment height), so the camera offset `T_B_C` is the CAD lens position.
* **Unknowns:**
  * anchors in the **marker** frame (12);
  * `L0` per station (4);
  * optional payout scale (4, off by default);
  * the marker's room pose (x, y, yaw);
  * one nuisance position per vision sample.
* **Observations:**
  * vision poses with covariance (full vision attitude; the claw has no IMU, D27; the optional gravity fusion `claw.imu` is off and unused);
  * motor positions;
  * taut-onset lengths and slide bearings;
  * bead captures.
* **Priors:** the user's anchor entries (σ per station), the marker heading
  guess (σ), and the marker position (σ). The room frame enters only through
  these priors. This makes the gauge explicit: the data constrain the anchors
  relative to the marker; the priors place the marker in the room.
* **Solver:** bounded trust-region least squares with Huber IRLS on
  measurement rows only (priors are never down-weighted). It is started from
  several marker headings to expose alternate optima.
* **Slack hypothesis selection:** per sample, the claw position is re-solved
  under "all taut" and "cable i slack" (θ held). Cable i may be declared slack
  only if its model length then exceeds its span by > `slack_k` σ, and a
  penalty prefers "all taut". In simulation this cut witness error from
  7.2 mm to 0.9 mm. Samples whose cables were probed taut by motion onset
  (§6.1a) skip this selection for those readings; it stays the backstop for
  everything the probe could not resolve.

**Acceptance is never "the optimiser converged".** All five must hold:
1. Identifiability: data information ≥ prior information in every direction,
   or the weak direction is named (e.g. "anchor C range + L0 C").
2. Whitened residual RMS ≤ `norm_rms_max`.
3. No alternate optimum within `ambiguity_dchi2`.
4. Witness error beyond camera noise ≤ `witness_rms_max_m`, and witness χ² consistent.
5. Predicted length σ over the work volume ≤ `length_sigma_max_m`.

If only (5) fails, the validated sub-volume is kept and the level is
LOCAL_ONLY. Tasks then stay inside that hull.

### 6.3 Excitation design

Candidate poses on a grid are filtered for:
* workspace;
* tension feasibility (80 % of max);
* marker visibility with ≥ 1.2× the minimum pixel size.

Greedy D-optimal selection maximises log det of the information on θ, with
sample positions marginalised and the predicted vision covariance at each pose.
Witnesses are the farthest-apart remaining poses. Poses are toured
nearest-neighbour.

### 6.4 Bead verification — optional since D26; why it is gated on *absolute* length

Since D26 the bead search is **optional** (`startup.bead_search`, default
false) and the beads are end-of-travel switches: a switch that opens during
normal motion faults the station (SWITCH, §4, `station_core._check_switch`)
and the ledger drops to LOCAL_ONLY/RECOVERY. Absolute-length safety comes from
the margins (§6.5). If the search is enabled the gating below is unchanged, a
verified bead is extra evidence, an all-verified search is VERIFIED on the
basis `beads`, and a BLOCKED bead no longer prevents VERIFIED by itself when
the margin rule holds. The normal-motion keep-out from each unverified bead
still carries `k·σ_abs` (`RobotContext._bead_margin`), now also while
VERIFIED by margin.

A bead checks the **absolute** length of one cable. Vision determines
absolute length poorly: anchor range and `L0` trade off along each cable.
In-volume consistency can be ~2 mm while absolute σ is ~20 mm.

With e the model's error, k = `bead_k_sigma`:
* The approach ends at model length `trigger + window`. The bead cannot be
  hit during that (non-reference) move if **k·σ ≤ window**.
* The search ends at model length `trigger − overtravel + k·σ`. Even with a
  failed switch, the bead cannot be pulled more than `overtravel` past its
  true trigger point.
* The search is complete (finds the bead for any |e| ≤ k·σ) iff
  **2·k·σ ≤ overtravel**.

If these fail, the bead is **BLOCKED** with the numbers. The robot does not
"search harder". When a bead is found:
1. The capture residual must agree with the model (pre-update check).
2. Back-off (`ref=2`) must release the switch.
3. Repeated captures must agree within `repeatability_tol_m`.

Then the captures are added as observations and **the whole model is refit**.
Changing L0 alone would break the anchor/L0 consistency the vision fit
established.

**Simulation finding (6-inch marker, 3 mrad IMU tilt σ; historic, before D27 removed the IMU, see `verification/imu_removal_results.md`):** absolute σ came out
at 20–25 mm, with actual errors of −38 to +21 mm, so the 3σ claims held. With
`overtravel = 12 mm` the gate requires σ ≤ 2 mm, so all four beads were
**BLOCKED** and the robot finished at **LOCAL_ONLY**. This is the honest
outcome, not a bug. Decision D-B is resolved by D26 (§6.5, §9).

### 6.5 Margin trust (D26): full-workspace operation without beads

**Rule.** The workspace is the room inset by `workspace_margin_m` (0.2 m) from
the walls, and `ceiling_margin_m` (0.4 m) below the fitted anchors
(`kinematics.workspace_from_config`). The robot starts near the room centre
on the floor reference, so gross slack is caught on the floor by the bounded
take-up. VERIFIED (basis `margin`) is granted by `StartupSequencer.assess_margin_trust`,
at every startup, only if all hold:

* (a) the final calibration was **accepted** (`Calibrator.validate`: witnesses,
  identifiability, residual adequacy, uniqueness, outliers, and predicted
  length sigma ≤ `length_sigma_max_m` over the work volume);
* (b) `startup.slack_probe` was on for **every** suspended sample (otherwise
  sub-3 mm slack reads as length error and the predicted sigma is not
  honest, §6.1a) and the witness chi-squared is ≤ `norm_rms_max`²;
* (c) `k·σ ≤ margin` for **both** margins at every pose of the commanded
  workspace (9×9×5 grid of the workspace box, tension-feasible poses, all four
  walls and the top plane included), `k = calibration.bead_k_sigma`, with σ
  below. The same station references and marker registration must still be
  valid.

Otherwise the level is LOCAL_ONLY (tasks stay in the validated hull) and the
failed items are listed in plain words.

**Which sigma.** The margin protects a *physical clearance*, so σ is the
1-sigma of the claw's true position relative to the boundary, not the
cable-length consistency of §6.2 and not simply the bead's `σ_abs` (the
posterior of `L0`). `Calibrator.boundary_sigma` derives it from the full
posterior covariance of (anchors in the marker frame, `L0`, marker pose
x, y, yaw). Motor positions are computed from the estimate, so with model
error `ε` (true − estimated) the true claw sits at the commanded pose plus
`dq`, from the cable equations `u_i·dq = u_i·da_i − dL0_i − e_i`
(`u_i` unit claw-to-anchor vectors, `e_i` the payout-scale error). Four
cables over-constrain a point claw, so with any mismatch it hangs on
three; which one is slack depends on pose and realisation. `dq` is therefore
evaluated for the four-cable least-squares solution and for each of the four
three-cable solutions, and every σ is the largest of the five. Then:

| Margin | Boundary | Defined in | σ used (maximum over the workspace) |
|---|---|---|---|
| `ceiling_margin_m` | claw vs the **anchors / pulleys** | the fitted anchors (the workspace top is `min(anchor z) − margin`) | claw position **relative to the true anchors**, `r_i = da_i − dq`: the larger of the vertical component of `r_i` (clearance under the anchor plane) and the claw-to-anchor distance error (= the cable-length error of a taut cable), over the four anchors. The marker registration does not enter: the ceiling moves with the anchors. |
| `workspace_margin_m` | claw vs the **walls** | the **room frame** (`room_m`), which is related to the fitted geometry only through the marker pose | room x and y error of the claw: `Rz(yaw) dq + dyaw·(ẑ × Rz q_M) + (dx, dy)`. This adds the marker registration (x, y and yaw × the lever arm from the marker), whose posterior comes from the anchor entries (`anchor_sigma_m`) and the marker prior, to the claw position error. Each wall sees only its own axis; the larger of x and y is used. |

`payout_scale_sigma` × (cable-length change from the nearest fitted sample)
is added per cable as an independent length error, because the spool scale is
not fitted by default and an extrapolated pose accumulates it. Not covered:
the cylinder obstacles (`cfg.obstacles`, room frame, their own clearances) and
the floor; the bead keep-out is handled by `_bead_margin`.

**What it does and does not claim.** σ is the model's own posterior: it is only
as honest as the estimator, which is why (b) requires the probe and a
consistent witness chi-squared. In simulation the worst true error stayed
within about 1·σ of the bound (see `verification/`), but simulation is the
only evidence: hardware (pulley friction, cable stretch, sag, a floor reference
that is not perfectly flat) can add errors the posterior does not see. The
margins are 0.2 and 0.4 m against k·σ of 0.1 to 0.2 m (sim), so the rule rests
on the margin being large compared with the model error, not on precision.

---

## 7. Supervisor

| Command | Allowed in | Effect |
|---|---|---|
| start | DISARMED, PARKED | runs the startup (page requires the checklist) |
| pause | any state | coordinated hold of whatever is moving (incl. lowering/recovery); moving states → PAUSED |
| resume | PAUSED | on floor: restart from SELF_CHECK; suspended: visual model check first |
| acknowledge | FAULT | clears station faults; on the floor → PARKED/DISARMED; hanging with all references valid and the model agreeing with vision → READY; else RECOVERY_REQUIRED |
| recover | RECOVERY_REQUIRED, FAULT | reconfigure/clear/re-arm stations; ≤ 1 invalid station is re-referenced from vision, then tautened slowly under vision (bounded) and re-referenced (LOCAL_ONLY); READY only if every station is ready and model and vision agree |
| lower | READY, PAUSED, RECOVERY_REQUIRED, FAULT | restore stations; move over the marker (model, tension-checked), descend, then equal-payout packets (bounded count, drift and tilt checked) until vision sees the floor; slacken → PARKED. Without a vision floor confirmation → RECOVERY_REQUIRED |
| disarm | PARKED, DISARMED, FAULT, RECOVERY_REQUIRED, PAUSED | typed `claw_supported` **and** a fresh vision floor check, always |

**Host restart:**
* claw known supported → DISARMED;
* otherwise → RECOVERY_REQUIRED.

Nothing auto-resumes.

---

## 8. Tasks

`tasks.py`: SCAN → APPROACH → GRIP → PICKUP_VERIFICATION → TRANSPORT →
RELEASE → DELIVERY_VERIFICATION.
* Moves stay in the trusted volume: the configured workspace (with its
  wall and ceiling margins) if VERIFIED (basis `margin` or `beads`, §6.5),
  the validated hull if LOCAL_ONLY, plus vertical descents below it to the
  floor.
* **Height limit.** `motion.task_max_height_m` (default 1.6 m, claw origin above the
  floor) is the highest the task layer ever plans (`TaskRunner._move` refuses a
  target above it with a clear reason). Near the ceiling the lines are shallow
  and the weakly held yaw can swing the camera bay into a line (camera-bay
  verification F6: hits only above ~1.6 m at |yaw| ≥ 30°). Calibration excitation and
  recovery keep their own bounds. (A yaw-measurement guard was considered and
  dropped in favour of this single limit.)
* **Settle, then approve (D27).** The claw has no IMU and no tilt gate: `/grip` obeys.
  Before descending the host waits until the claw is *still* (`attitude.wait_until_still`):
  camera-observed motion of the floor reference below `tasks.grip_still_rate_rad_s` (corner
  shift / (fx·dt)) for `tasks.grip_still_frames` consecutive frames; with no camera motion
  signal (reference not in view) a dwell of `tasks.grip_settle_periods` pendulum periods
  `T = 2π√(L/g)`, L = depth of the CoM below the attachment plane (never less than
  `tasks.grip_settle_min_s`). It then approves only if the tilt (vision when the reference is
  in view, else the cable model) and the predicted `R_at` tilt at the hover and at the grip
  pose are within `claw.grip_tilt_max_rad`. Each approval is recorded
  (`TaskRunner.approvals`). The same settle gate precedes a release.
* The final descent is at 30 % speed. Transport is planned with claw mass
  plus the maximum payload (0.9 kg).
* A servo command proves nothing: pickup and delivery are both checked by
  perception.
* Limits: `max_grip_attempts` per item, `max_consecutive_failures` before
  pausing for the operator.
* **Garment detection** reuses the gen-1 YOLO-World open-vocabulary detector
  (`roomcleaner/perception/vision_detector.py`) on the claw camera
  (`roomcleaner/cdpr/garments.py`):
  * Each box centre is mapped to the floor with the claw's current pose (an
    exact ray/plane intersection; cable-kinematics position plus the last
    marker yaw when the marker is out of view).
  * **Pickup verification** needs two independent cues: the jaw region of the
    image differs from its surrounding floor (the item hangs in the jaws), and
    after the short shift toward the hamper nothing is seen at the old spot.
  * **Delivery verification**: the jaw region looks empty again and the item is
    inside the hamper radius.
  * Delivered items are excluded from later scans.
  * Tested in simulation with rendered camera images and a colour-blob
    stand-in detector: two items delivered, a failed grip detected and
    retried, a failed release reported. The YOLO path, the 30-unit
    jaw-region threshold and the 0.25 m shift must be tuned on real frames.

---

## 9. Open decisions (not silently solved)

* **D-A Tension sensing.** V1 has none. Startup and calibration bound load by
  geometric consistency: onset detection, lift-lag budget, drift, statics
  feasibility, slack-aware fitting. These bound the load but do not measure
  it. A series spring or load cell per cable would turn overconstraint into
  a measured, benign quantity.
  *Recommendation:* add a calibrated series spring (≈ 200–500 N/m) at each
  claw attachment before suspended operation above the 1 lb test weight.
* **D-B Absolute length reference. RESOLVED by D26 (2026-10-20).** Beads
  need σ ≤ overtravel/(2k), which vision alone does not give (~20 mm). Instead
  of pinning the absolute length, the ceiling and wall margins absorb it: full
  workspace if a, b and c of §6.5 hold at the startup, else LOCAL_ONLY. Beads
  are end-of-travel switches; the search is optional. Remaining risks: the
  rule is simulation-validated only, the slack probe is opt-in (and without it
  the robot is always LOCAL_ONLY), and calibration criterion "predicted length
  sigma ≤ 5 mm over the whole workspace" is what most simulated runs miss.
* **D-C Power-loss holding.** An unpowered NEMA 17 with A4988 disabled may
  back-drive under the claw's weight. Measure detent holding on the real
  spool before any suspended run. Until then, nobody under the workspace,
  and the 1 lb test weight first.
* **D-D Garment perception thresholds** on real claw images (see §8).
* **D-E Station address assignment / discovery.** Static IPs in the config.
* **D-F Station-enforced travel floor for bead searches** (review M3). Today
  the over-travel bound comes from the host's model. A station-side absolute
  floor per `ref=1` segment (protocol and both cores) is required before any
  bead search on hardware.
* **D-G Passive claw yaw / outer-rim path.** Yaw is only weakly held by the four
  lines (§3); there is no yaw actuator or guard in V1 (see the height limit in §8).
  The straight inner-mouth model ignores that a steep line bears on the outer rim of
  the 18 mm hole (mm-level, pose-dependent). Measure on the real claw: attachment
  points, CoM, tilt vs. length error, and a line-rim contact test, before relying on
  mm-level lengths.
* **Operator page access.** A session token printed at start, plus JSON-only
  requests. Use it on a trusted home network only; it is not hardened for
  hostile networks.

---

## 10. Commissioning order (from the handoff), with the evidence each step needs

| # | Step | Code / tool | Pass evidence to record |
|---|---|---|---|
| 1 | Preserve the working one-station sketch and wiring | `firmware/roomcleaner_firmware` (Uno bench), `firmware/local_station` (bench C3) kept | photo + commit |
| 2 | Encoder readings alone | `firmware/winch_station` telemetry `enc`, `encv` | direction sign, counts/rev, magnet status |
| 3 | Units, signs, spool conversion, config | `config/robot.json`, `cdpr/spool.py` | measured payout vs commanded over 1 m |
| 4 | Bounded local motion + telemetry | station core (`cfg`, `arm`, `seg`) on one station | segment tracking error, fault injection (unplug encoder → ENCODER) |
| 5 | Two stations, restrained bench | coordinator | pause spread, lease stop with Wi-Fi off |
| 6 | Four stations, 1 lb test weight | coordinator + trajectory | tension-feasible moves, hold behaviour |
| 7 | Camera calibration + marker pose alone | `tools/calibrate_camera.py`, `vision/marker.py` | RMS ≤ 1 px, pose vs tape measure |
| 8 | Bounded slack take-up and lift | `startup.py` SELF_CHECK → INITIAL_LIFT | onset lengths, bearing RMS, lift lag |
| 9 | Parameter fitting + independent validation | CALIBRATION | witness RMS, identifiability report |
| 10 | Margin trust decision (§6.5); optional sequential bead verification | `startup.py` `assess_margin_trust`, `homing.py` | k·σ vs both margins and the worst pose; if enabled, capture residuals, spread, or BLOCKED reasons |
| 11 | Grip, pickup and delivery verification | `tasks.py` | attempt logs |
| 12 | Larger envelopes only after measured validation | validated volume | coverage map |

At each stage save the firmware commit, configuration, test setup,
measurements and failures (`data/cdpr/` holds calibration and trust JSON).

---

## 11. Standards mapping (what is and is not claimed)

* **ISO 12100** (risk assessment): §9 and the hazard notes here are the
  start of the record. A formal risk assessment is still to be written
  (suspended load, cable whip, pinch at pulleys, LiPo).
* **IEC 60204-1** stop categories: the power strip is **category 0** (it drops
  the load). Pause/fault holds are **category 2** (controlled stop, power
  maintained). There is no category 1 path, and no safety-rated stop is claimed.
* **ISO 13849 / IEC 61508:** **not claimed.** No function here is safety-rated.
  The mitigation is procedural: nobody under the workspace, a light payload,
  and the kill switch.
* **Electrical:** fused 12 V supply, balance-charged LiPo, motors and drivers
  never hot-plugged.

---

## 12. Answers to the handoff questions

1. **Which firmware runs on the working station?** The bench rig that moved
   motors is the Uno + CNC-shield firmware (`firmware/roomcleaner_firmware`).
   The XIAO-C3 station has only the USB connection check
   (`firmware/station_usb_check`; no physical pass recorded) and the Codex
   single-axis bench controller (`firmware/local_station`, which assumes a
   DRV8825 nFAULT pin the A4988 does not have). The coordinated station
   firmware is `firmware/winch_station` (new, not yet flashed).
2. **Encoders installed? Magnets?** Designed in (AS5600 per station, magnet
   on the spool axis per the Rev C electrical package). No physical encoder
   reading has been recorded yet. Commissioning step 2.
3. **Common or spaced attachment?** Spaced (updated 10/20): four lines tied off at the
   inner mouths of the corner cable holes of the electrical box (§3). The model,
   estimator, planner and simulator use the four points; a single common point is
   still supported and reproduces the old model exactly.
4. **Spool dimensions / winding?** Spoolv3: Ø36 × 22 mm, Ø15 core, 16 mm drum,
   Ø5.45 D-bore, layered 7.5 → 10 mm radius. Modelled exactly (`spool.py`).
   Payout scale and line total still to be measured (step 3).
5. **How does startup know each cable is taut?** Vision-detected claw motion
   onset while it rests on the floor, one cable at a time, bounded by max
   slack. Continued pulling gives the slide direction. With no tension sensor,
   this is the bounded, observable substitute (D-A).
6. **Known vs estimated parameters?**
   * Known/measured: spool geometry, marker edge, camera intrinsics,
     camera-in-claw transform, claw mass, bead trigger lengths.
   * Estimated: anchors (marker frame), `L0` per boot epoch, marker room pose.
   * Optional: payout scale (only when identifiable).
   * Not estimated: camera extrinsics, attachment geometry (CAD).
7. **Marker ↔ room relationship?** Estimated, not assumed. The slide bearings
   and the anchor-entry priors register it (x, y, yaw). Its uncertainty is
   reported. Changing anchor entries changes only the room alignment, not
   the internal consistency.
8. **Acceptable uncertainty before a bead approach?** Derived, not chosen:
   k·σ_abs ≤ search window and 2·k·σ_abs ≤ overtravel (§6.4), plus
   σ_abs ≤ `bead_length_sigma_max_m`. Since D26 the bead search is optional;
   full-workspace trust needs k·σ of the claw position relative to each
   boundary ≤ its margin (§6.5).
9. **How are trajectories synchronized?** Hermite segments in each station's
   own clock (offset-estimated), first-window acknowledgements before T0,
   path-time feed-hold, leases, peer-broadcast holds, telemetry completion (§4).
10. **Network loss / reset / power loss, mechanically?**
    * Network loss: lease → coordinated hold on all stations, torque kept.
    * Station reset: that motor is unpowered while the others hold. The claw
      shifts onto three cables, the station's epoch is lost, and the state is
      RECOVERY_REQUIRED.
    * Host reset: stations hold at lease expiry; on restart → RECOVERY_REQUIRED
      if hanging.
    * Power loss: everything de-energises and the claw may drop (D-C).

---

## 13. Evidence (simulation, `pytest tests/cdpr tests/firmware`)

* Firmware: the C++ station core replays 16 Python-generated traces (21.6k
  events, 1,527 messages) with identical steps and field-identical messages;
  the XIAO-C3 sketch builds warning-free and runs against Arduino stubs (not
  yet built for the ESP32).

* Station core: 16 tests (segments, parking, holds, lease, underrun, capture,
  faults).
* Coordinator: synchronized motion, pause on the same path point (< 10 ms
  path time), stalled motor → tracking fault + holds, lossy network 10/10,
  link outage stop spread ≈ 18 ms.
* Vision: marker detection and pose ambiguity handling (12 cases), marker
  sheet scale, ChArUco calibration recovery.
* Margin trust (D26, `tests/cdpr/test_margin_trust.py`): boundary sigma
  against analytic cases and a Monte-Carlo of the nonlinear physics; one full
  board + probe startup VERIFIED by margin, re-decided with the probe off,
  shrunken margins, a failed witness chi-squared and the bead search on;
  tasks confined to the hull unless VERIFIED; basis and numbers in the API;
  no probe → LOCAL_ONLY.
* Calibration: small box flagged prior-dominated; large box accepted with
  honest σ; slack identification; swapped-wiring detection; bead
  observations shrink absolute σ by > 3×.
* System:
  * full lifecycle — startup → READY(LOCAL_ONLY) → 2 items delivered → station
    reboot → RECOVERY_REQUIRED → visual recovery → lower → PARKED → confirmed
    disarm;
  * unattached cable caught on the floor;
  * swapped wiring caught before lifting;
  * covered marker → PAUSED;
  * unsafe config refused; low battery refused;
  * bead VERIFIED with a good model; bead disagreement → BLOCKED with no update.
