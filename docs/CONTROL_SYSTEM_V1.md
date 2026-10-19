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
   shows the trust level (VERIFIED or LOCAL_ONLY) with plain reasons.
5. **PAUSE** holds position at any time. The switched power strip is the
   emergency stop and drops the claw.

---

## 2. Architecture

| Component | Runs | Responsibility |
|---|---|---|
| Host PC | `roomcleaner/cdpr` | vision, calibration, planning, coordination, supervision, logging |
| Station ×4 (XIAO ESP32-C3 + A4988 + AS5600 + NC bead switch) | `firmware/winch_station` | local step generation from Hermite segments, encoder tracking, switch capture, feed-hold, lease, faults |
| Claw (XIAO ESP32-S3 Sense + MPU6050 + MG996R) | `firmware/claw_s3` | timestamped JPEG frames, roll/pitch, battery, grip with tilt gate |
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
body (origin at the common cable attachment), C = camera. `T_A_B` maps B→A.
Vision gives `T_C_M`; the claw pose is `T_M_B = inv(T_C_M)·inv(T_B_C)`.

**Cables.** `L_i = |a_i − (p + R b_i)|`, straight and taut, sag neglected
(Dyneema, < 1 kg). The claw uses one **common attachment point** (b_i = 0), so
its orientation does not enter the lengths. It hangs plumb; yaw is free.
Deliberate tilting is out of scope.

**Spool.** Layered winding (Spoolv3: 7.5 → 10 mm radius over the line). With
`line_total = W + L`, one constant per station per boot epoch, `L0` (external
length at motor position 0), maps motor microsteps to length exactly. A
measured payout table can replace the layered model.

**Statics.** Four cables, three force equations: tension is indeterminate.
Planning requires a feasible min-max distribution within
`[min_tension_n, max_tension_n]` at every knot (`kinematics.tension_distribution`).

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
  trigger the same coordinated hold mid-motion. Slack take-up uses it.

### Station fault reactions

| Fault | Meaning | Reaction | Holding torque |
|---|---|---|---|
| TRACKING | encoder vs commanded steps beyond tol for dwell | stop pulses now | kept |
| ENCODER | stale/unreadable/bad magnet | stop | kept |
| SWITCH | bead switch open outside a reference move (bead or broken wire) | stop | kept |
| TIMING / CONFIG | loop overrun / no valid config | stop | kept |
| LEASE / UNDERRUN | coordination at risk, motion itself fine | coordinated hold | kept |

**Stop ≠ disable.** No fault removes torque. Only `disarm` with
`confirm:"claw_supported"` does. The supervisor sends it only when vision
shows the claw on the floor, or the state already records it as supported.

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
| coordinated stop (pause, lease, underrun, peer hold) | kept | kept | unchanged |
| tracking / encoder / timing fault | that station invalid | kept | RECOVERY |
| unexpected bead switch | that station suspect | kept | RECOVERY |
| station reboot | that station's epoch lost | kept | RECOVERY |
| host restart | kept only if every boot id matches and no latched fault | kept | restored or RECOVERY |
| power loss (strip) | all lost; claw may have dropped | kept | NONE, floor restart |
| marker moved / missing | kept | marker registration invalid | LOCAL_ONLY until re-registered |
| camera calibration changed | kept | visual products invalid | NONE for vision |

A reboot of anything never resumes a task or a startup.

---

## 6. Startup and self-calibration

Implementation: `startup.py` (states), `calibration.py` (estimator),
`homing.py` (beads), `perception.py` (claw pose). Every step has bounds and
abort conditions. Aborts **hold**; they never disable.

### 6.1 States

| State | Does | Aborts (→ FAULT / PAUSED / RECOVERY_REQUIRED) |
|---|---|---|
| SELF_CHECK | config complete for the stage, suspended motion authorised; stations configured (param hash), synced, fault-free, switches closed, armed; claw online, battery ≥ min; camera calibration id recorded; marker visible and still; claw resting upright on the floor (height ±3 cm, tilt) | any check fails |
| SLACK_TAKEUP | one station at a time, a slow continuous retraction (claw on the floor = stations uncoupled), bounded by `max_slack_m`. Each vision frame is checked; claw motion ≥ max(onset_translation, k·noise) marks taut onset. Pulling continues to `bearing_translation_m` so the **slide direction** is measured, then a hold and a pay-out of `onset_backoff_m` | no onset within max slack (cable unattached, wrong winding direction, station order); marker lost > 1 s; tilt |
| — after all four | slide bearings vs anchor entries (catches **swapped station wiring**); first fit → L0 per station + marker registration | bearing RMS > limit |
| INITIAL_LIFT | all cables to just-taut, then vertical packets computed from the model's cable directions; vision after each | lateral drift > max, tilt > max, commanded − observed lift > budget, no clearance by `max_lift_m` |
| VISUAL_INITIALIZATION | still pose while suspended → refit | marker lost |
| CALIBRATION | staged excitation: local box → intermediate → expanded, D-optimal poses + held-out witnesses, refit between stages | witness, residual, ambiguity or outlier failure |
| REFERENCE_VERIFICATION | bead per station, sequentially (§6.4); verified captures refit jointly | bead fault; refit rejected |
| READY | trust level VERIFIED (all beads verified) or LOCAL_ONLY with stated reasons | — |

### 6.2 Estimator

* **Unknowns:**
  * anchors in the **marker** frame (12);
  * `L0` per station (4);
  * optional payout scale (4, off by default);
  * the marker's room pose (x, y, yaw);
  * one nuisance position per vision sample.
* **Observations:**
  * vision poses with covariance, **gravity-fused**: roll/pitch from the claw IMU, only yaw and position from the image;
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
  7.2 mm to 0.9 mm.

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

### 6.4 Bead verification — why it is gated on *absolute* length

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

**Simulation finding (6-inch marker, 3 mrad IMU tilt σ):** absolute σ came out
at 20–25 mm, with actual errors of −38 to +21 mm, so the 3σ claims held. With
`overtravel = 12 mm` the gate requires σ ≤ 2 mm, so all four beads were
**BLOCKED** and the robot finished at **LOCAL_ONLY**. This is the honest
outcome, not a bug. Options are in §9 (open decision D-B).

---

## 7. Supervisor

| Command | Allowed in | Effect |
|---|---|---|
| start | DISARMED, PARKED | runs the startup (page requires the checklist) |
| pause | STARTUP, TASK, READY | coordinated hold → PAUSED |
| resume | PAUSED | on floor: restart from SELF_CHECK; suspended: visual model check first |
| acknowledge | FAULT | clears station faults → DISARMED/PARKED (on floor) or RECOVERY_REQUIRED (hanging) |
| recover | RECOVERY_REQUIRED | ≤ 1 invalid station: reconfigure, clear, re-arm, re-reference its L0 from vision (LOCAL_ONLY), then a slack-aware model-vs-vision check |
| lower | READY, PAUSED, RECOVERY_REQUIRED, FAULT | move over the marker, descend, final packets until vision sees no further descent, slacken → PARKED |
| disarm | PARKED, DISARMED, FAULT, RECOVERY_REQUIRED | needs `claw_supported` **and** vision/state confirming support |

**Host restart:**
* claw known supported → DISARMED;
* otherwise → RECOVERY_REQUIRED.

Nothing auto-resumes.

---

## 8. Tasks

`tasks.py`: SCAN → APPROACH → GRIP → PICKUP_VERIFICATION → TRANSPORT →
RELEASE → DELIVERY_VERIFICATION.
* Moves stay in the trusted volume: the workspace if VERIFIED, the validated
  hull if LOCAL_ONLY, plus vertical descents below it to the floor.
* The claw must settle upright (IMU) before closing. The claw firmware also
  refuses a tilted close.
* The final descent is at 30 % speed. Transport is planned with claw mass
  plus the maximum payload (0.9 kg).
* A servo command proves nothing: pickup and delivery are both checked by
  perception.
* Limits: `max_grip_attempts` per item, `max_consecutive_failures` before
  pausing for the operator.
* **Garment detection on hardware is not implemented** (`ItemPerception`
  raises): an open item. The simulator's perception exercises the workflow.

---

## 9. Open decisions (not silently solved)

* **D-A Tension sensing.** V1 has none. Startup and calibration bound load by
  geometric consistency: onset detection, lift-lag budget, drift, statics
  feasibility, slack-aware fitting. These bound the load but do not measure
  it. A series spring or load cell per cable would turn overconstraint into
  a measured, benign quantity.
  *Recommendation:* add a calibrated series spring (≈ 200–500 N/m) at each
  claw attachment before suspended operation above the 1 lb test weight.
* **D-B Absolute length reference.** Beads need σ ≤ overtravel/(2k). Vision
  alone gave ~20 mm. Options (combinable):
  1. design more bead-to-pulley clearance (a larger `max_overtravel_m`);
  2. a calibrated IMU and a multi-tag marker board;
  3. a tape-measured line length at setup as one absolute observation;
  4. accept switch + stall-tracking as the over-travel backstop (a risk decision).
* **D-C Power-loss holding.** An unpowered NEMA 17 with A4988 disabled may
  back-drive under the claw's weight. Measure detent holding on the real
  spool before any suspended run. Until then, nobody under the workspace,
  and the 1 lb test weight first.
* **D-D Garment perception** for hardware (see §8).
* **D-E Station address assignment / discovery.** Static IPs in the config.

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
| 10 | Sequential bead verification | `homing.py` | capture residuals, spread, or BLOCKED reasons |
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
3. **Common or spaced attachment?** Common point (one ring). The code supports
   spaced points (`claw.attachment: spaced`), but V1 statics and tests assume
   common.
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
   σ_abs ≤ `bead_length_sigma_max_m`.
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

## 13. Evidence (simulation, `pytest tests/cdpr`)

* Station core: 16 tests (segments, parking, holds, lease, underrun, capture,
  faults).
* Coordinator: synchronized motion, pause on the same path point (< 10 ms
  path time), stalled motor → tracking fault + holds, lossy network 10/10,
  link outage stop spread ≈ 18 ms.
* Vision: marker detection and pose ambiguity handling (12 cases), marker
  sheet scale, ChArUco calibration recovery.
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
