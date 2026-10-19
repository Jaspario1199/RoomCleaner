# RoomCleaner startup calibration V1

**Revision:** research and implementation specification, 2026-10-16. **Status:** proposed; not implemented or qualified for suspended operation. Authoritative user intent: the conversation on 2026-10-16, approximately 02:24–02:58 America/Chicago.

## 1. The startup we are building

Place the claw upright on the floor near the middle of the room, with correctly routed cables and a small, bounded amount of slack. Enter approximate room and mount dimensions in a phone interface. The robot makes a short controlled pickup, holds while the user places a printed marker under/near its camera, estimates geometry from camera observations and coordinated spool movements, then checks its cable references against the bead-operated homing devices before normal operation.

The marker may already be present before pickup. Seeing it early is useful but is not a substitute for developing the requested lift-before-calibration stage. There is no required parking cradle, surveyed marker location, ceiling camera, or room-wide marker search in the intended startup flow. A temporary support/catch arrangement during engineering tests does not become a product docking requirement.

This specification retains **physical bead verification** as a distinct phase. It does not silently replace that requirement with vision alone. The full startup is incomplete if required bead references cannot be checked.

Supported initial-condition envelope to establish in testing: upright, empty claw, near-center starting region, unobstructed cables, limited slack, no tangled loops, known motor identity and routing. Recovery from a fallen, snagged, or arbitrarily slack robot is outside this version. The starting region is a measured area with tolerance, not an exact docking pose.

## 2. What is established and what is not

| Evidence | Current state |
|---|---|
| Supply | User identified ALITOVE 12 V, 6 A, 72 W adapter |
| One logic-power chain | User measured buck 5.00 V, XIAO input about 4.7 V after diode, regulated output 3.3 V; soldered connection subsequently reported good |
| Controller | Upload log identifies ESP32-C3; user subsequently confirmed repeating USB serial test |
| One KW12-3 switch | User confirmed released/pressed software states; disconnected-wire fault test not separately confirmed |
| Motor coil pairs | User reported identified; pair colors/resistances not recorded |
| Driver | User photos show red A4988 carrier with heatsink; sense resistor values and motor rated current unresolved |
| Encoders | Required by this proposed startup; installed four-axis encoder feedback not demonstrated |
| Camera | XIAO ESP32-S3 Sense is the selected claw platform; streaming, lens, intrinsic calibration and pose accuracy not demonstrated |
| Power distribution and capacitors | Earlier delivery estimates do not prove current arrival/installation; verify physically |
| Suspended motion, bead approach, camera calibration | No hardware results yet |

The local repository contains detached-bench homing and experimental encoder guards. `firmware/local_station/local_station.ino` assumes a DRV8825-style fault input and `motion_core.h` assumes a detached home sequence. `roomcleaner/hardware/driver.py` explicitly requires detached homing; `hw_config.py` has unmeasured home lengths and historical drum constants. None implements this startup. Do not remove those existing interlocks and call the result V1.

## 3. Research findings and engineering interpretation

The closest primary reference is Tremblay et al., *Eye-on-Hand Calibration Method for Cable-Driven Parallel Robots* (2019). It estimates outlet locations and initial cable lengths using an onboard camera and fiducial markers. Its experiment uses eight winches and a different drive/control system, with multiple floor markers. It does **not** establish blind floor pickup, A4988 operation, or four-cable self-righting. Its useful precedent is visual geometric calibration and testing predictions at separate witness poses. [R1]

AprilTag supplies identification and metric pose estimation from a measured tag and calibrated camera. OpenCV provides planar pose solvers; IPPE explicitly returns alternative planar solutions. Therefore V1 must retain ambiguity and quality checks rather than trusting whichever pose is returned first. [R2–R4]

An AS5600 measures angle within a turn. Software can unwrap successive measurements while running, but rebooting does not recover complete spool turns. Encoder feedback is movement evidence, not an absolute cable-length or tension sensor. [R5]

The following design is our adaptation to this robot, not a claim that a paper has already validated it.

## 4. Coordinates, inputs and geometry

Use the fixed marker as frame **M**: origin at its defined center, X/Y along its printed axes, Z normal to its flat face. Enter measured tag edge length, not paper size. Six inches means 152.4 mm only if the detector's specified tag boundary actually measures that length. The white margin is additional. Tape or mount the sheet flat so it cannot slide during the run.

The marker may lie anywhere within the usable camera view. Its unknown room location is absorbed by estimating the mounts in frame M. Relative wall orientation and motor identities still need initialization: the app shows an A/B/C/D diagram and asks the user to align a printed arrow approximately toward station A or enter a rough heading. The arrow need not be precision-surveyed. If the marker moves later, room/hamper coordinates cannot simply be reused unchanged; re-register the frame or recalibrate. A single moving marker cannot distinguish its own motion from camera motion reliably in every case.

A marker on a tilted floor defines floor-normal, not gravity-vertical. Measure/qualify floor level for the initial experiment. An optional IMU provides a gravity reference after settling. It is not required to prove basic visual calibration, but reserve its mounting and electrical interface.

Let `a_i` be outlet i in M, `p_k,R_k` the claw rigid-body pose at sample k, and `b_i` the cable attachment point in claw coordinates. The straight external cable span is:

`L_i,k = ||a_i - (p_k + R_k b_i)||`.

For a single common attachment use one measured point. For four spaced attachments retain all four `b_i`; do not pretend a four-cable platform can independently command arbitrary six-axis poses. Keep motion predominantly translational and monitor actual orientation and stability.

Measure the fixed camera-to-claw transform before estimating room geometry. Marker PnP returns marker-to-camera; invert and compose transforms correctly to obtain claw pose in M. Keep a unit test fixture with known translations and rotations for these conventions. Camera optical height is not jaw clearance: transform the lowest claw points to the marker plane.

App inputs for first setup:

- Approximate width, depth and outlet heights; the reported 11 × 9 × 9 ft values are priors, not surveyed geometry.
- Station IDs, approximate positions/corner offsets, marker heading and approximate central starting area. Height refers to cable outlets, not necessarily the ceiling.
- Claw configuration, mass including battery, attachment coordinates, camera mounting transform and camera-calibration ID.
- Spool/encoder signs, gear ratio if any, measured payout curves, marker ID/family/size.
- Measured bead trigger lengths, their repeatability and angle range; no invented zero values.
- Qualified bounds on initial slack, tilt, translation, lift travel, force capability, stop latency and available camera coverage.

Rough dimensions help choose initial estimates. They are not precise collision boundaries. Keep a generous interior motion envelope until walls and obstacles are measured.

## 5. Architecture

**Phone:** setup fields, preview, current phase, stop/recover prompts and calibration report. The phone does not generate step timing.

**PC coordinator:** image processing, pose quality, geometric fitting, path generation, all-station synchronization and calibration persistence.

**Claw S3 camera:** timestamped images with sequence/boot IDs; optionally tilt telemetry. Start with JPEG capture and host processing, then measure stream age and detection rate. Espressif documents JPEG and buffering options, but no assumed frame rate or latency is accepted without measurement. [R7]

**Each station C3 + A4988 + encoder + switch:** local pulse scheduling, encoder tracking, home-edge timestamp/count capture, bounded command segments, command lease/watchdog, local stop and fault broadcast. The A4988 cannot report tension or missed steps; its current limit is separate. [R6]

Use one coordinated trajectory generation ID and explicit acknowledgements before movement. Queue short segments with a common start time and expiry; refuse late/stale/duplicate commands and avoid accumulating a long unchecked motion queue. Measure clock uncertainty and convert it into a cable mismatch budget. A Wi-Fi stop packet alone is insufficient: every station has a local expiry mechanism. No transport changes are required by this document, and CAN is not declared implemented.

## 6. State machine

| State | Action | Exit evidence / failure behavior |
|---|---|---|
| SETUP | Confirm upright empty claw, bounded slack, clear central region, hardware/config identities | Every configured bound available; missing measurements keep system unarmed |
| PREFLIGHT | Check encoders, switch idle states, camera heartbeat, local stop paths, network timing, step direction | Stale/bad encoder, open switch at startup, reboot or wrong config prevents pickup |
| PICKUP_PROBE | Short synchronized retraction packets using a commissioned central-start profile | Stop after bounded travel/time; following error stops motion, not automatic unwinding |
| WAIT_FOR_MARKER | Hold at the provisional pickup position while user places marker; no searching | Stable marker pose; finite hold time and thermal limits; require manual recovery on timeout initially |
| CONFIRM_CLEARANCE | Estimate body pose and lowest-point clearance; reject ambiguous/noisy pose | If too low, continue short camera-observed lift; if unexpected height/tilt/lateral displacement, stop |
| LOCAL_CALIBRATION | Collect small coordinated moves with settled camera/encoder observations | Fit a local model and test unused witness moves |
| EXPAND_CALIBRATION | Expand sample region only within demonstrated visibility, motion and force bounds | Geometry becomes sufficiently identifiable for the proposed next route |
| PLAN_BEAD_CHECKS | Solve accessible trigger poses and complete paths for each bead | All required approaches and retreats feasible with uncertainty allowance |
| VERIFY_BEADS | Check one bead at a time with all cables coordinated; record contact, retreat, repeat | Independent pre-update residual and repeatability pass; broken-wire/open input not accepted as home |
| FINAL_VALIDATE | Refit accepted references; repeat witness poses and initial-area return | All required checks pass; save scoped calibration with uncertainty and IDs |
| READY | Permit operation only within validated envelope | New faults invalidate appropriate calibration state |
| FAULT_HOLD | Cancel new movement, request coordinated stop, preserve appropriate energized support | No unattended restart or blind payout; support/recovery procedure required |

Retaining motor current is not guaranteed load holding. Power loss or overload requires physical support/catch provisions during qualification. A software stop is not a brake.

### 6.1 Pickup before the marker is acquired

This is a bounded engineering mode, not yet a solved general estimator. The camera stream may run throughout, but no marker observation is assumed until `WAIT_FOR_MARKER`. Spool rotation alone cannot prove floor clearance because some winding removes slack.

Commission the pickup profile from a grid of allowed near-center start positions and deliberately varied bounded slack. Use a supervisor and temporary external measurement/catch arrangement to determine whether synchronized low-speed winding reliably creates a small clearance without excessive tilt, displacement, tension or missed steps. Log failed trials too. The product's routine stays automatic; engineering supervision establishes its operating envelope.

Use a rough geometry-based upward cable-rate pattern, rather than assuming equal rates for every possible start. Equal retraction is only an approximation near a symmetric central configuration. Keep each packet and cumulative take-up bounded; no instruction to retract an arbitrary two feet. After the probe, wait for the marker and verify actual clearance. If the marker was present at the outset, use its feedback immediately.

The initial reference encoder counts for **geometric fitting are taken after the cables are confirmed taut and the claw is suspended**, not at the original slack-floor state. Slack take-up samples do not satisfy the straight-length model. Do not reset the diagnostic motor-following-error history when assigning the new geometric origin.

Encoder-only pickup is a supervised prototype track until tests establish adequate margins. A mechanically caught cable can overload something before a motor loses steps. If testing cannot establish a reliable bounded startup using camera/encoder feedback, add per-cable tension sensing; that improves this same pickup sequence rather than changing it to a dock-first workflow. No tension-sensor purchase is asserted here.

### 6.2 Preliminary test numbers, not released settings

For test planning, begin with roughly 50–100 mm jaw clearance after visual confirmation, not a multi-foot blind rise. Consider nominal 1–2 mm payout-equivalent probe packets and low single-digit mm/s cable speeds for the first supported experiments. These values are hypotheses; effective spool radius, full-step resolution, stopping response, slack envelope and actual force capability may require different values.

`parameters.example.json` deliberately leaves machine limits null. This is a research template, not a configuration consumed by existing firmware. No example value authorizes movement.

## 7. Marker and camera implementation

Choose one AprilTag family/ID for V1 and record it. Use a 152.4 mm detected-edge target as a first print experiment, with the correct white border. A rigid backing is preferable to a curled loose sheet. Calibrate intrinsics/distortion at the actual image resolution, crop and lens setting; changing these invalidates the calibration unless the transform is correctly adjusted.

Before motorized use, place the camera at known heights and lateral positions on a fixture. Check metric position, pitch/roll estimates, minimum focus, edge-of-image distortion, lighting and tag visibility. A larger marker improves distant imaging but may not fit the close floor-start view. The correct size comes from these tests.

For a roughly frontal tag, projected width is approximately `pixels = fx * tag_edge_m / camera_distance_m`. Actual off-axis projection must be computed with calibrated intrinsics and extrinsics. Do not use this formula as a fixed field-of-view specification for the purchased camera.

Estimate both planar pose candidates, check positive depth, corner reprojection, temporal continuity and known upright/floor constraints. Ambiguous orientation cannot be made trustworthy merely by averaging whichever solution arrives first. Reject bad frames; record why. A board with multiple markers can improve robustness if one square proves inadequate; it is a proposed upgrade, not a hidden initial requirement. [R2–R4]

Use settled observations first: stop, wait until measured motion is small, then associate camera frames with stationary encoder values. This avoids pretending Wi-Fi receive time equals image capture time. Continuous control later needs synchronized capture timestamps, measured latency/jitter and an error bound such as `speed × age` within the allowed pose error.

## 8. Geometry estimation and calibration motion

Define `d_i,k` as measured **paid-out** cable change from the taut reference; retraction is negative. Estimate outlet positions `a_i` and reference lengths `L_i,0` by minimizing metric residuals:

`r_i,k = ||a_i - (p_k + R_k b_i)|| - (L_i,0 + d_i,k)`.

Use uncertainty weights, robust loss and physically justified priors/bounds. With fixed camera and payout calibration, there are four principal unknowns per cable: three outlet coordinates and one initial length. Having enough equations is necessary but not sufficient; near-identical poses make those unknowns hard to separate. Solve with multiple plausible initializations, inspect the scaled Jacobian, and report sensitivity to measurement perturbations. SciPy's bounded nonlinear least-squares implementation is an appropriate offline prototype tool. [R8]

Do not initially estimate every unknown at once. Measure camera extrinsics, attachment points and payout scale separately. For a multilayer spool, payout is a function of accumulated wraps, not a universal circumference. Keep first samples within a characterized layer region; qualify a piecewise payout model before long bead approaches. Guide friction, wrap changes, stretch and sag are model errors to measure, not errors to conceal by shifting mount coordinates.

Proposed sample progression:

1. A settled reference and repeated observations without motion to measure noise.
2. Small translations in +X, −X, +Y, −Y and +Z, returning to reference where feasible. Do not intentionally rotate the claw for this version.
3. Fit a local model, then test distinct withheld points.
4. Add diagonals and another height; expand horizontal baseline only after the local tests and visibility/path checks pass.
5. Refit on a rolling accepted dataset, not continuously on slack or faulted observations. Keep the last accepted model available for comparison.

All four cables participate in each Cartesian move. For a point attachment, a desired upward velocity maps approximately as `dL_i/dt = -(a_i - p)/L_i dot v`. A common attachment with three other taut, fixed cable lengths is generally already position-constrained; pulling the fourth alone is not a clean way to measure its direction. With spaced attachments include measured orientation and wrench/stability constraints.

The camera can validate local pose without accurate distant anchor estimates. Label that state `LOCAL_ONLY`. It must not automatically authorize a several-metre corner approach. Prefer geometric priors over wildly moving anchors to explain noise. Holdout motion tests, independent ruler checks and uncertainty propagation are stronger evidence than low training residual alone.

### 8.1 Offline sensitivity check completed with this document

`research/startup_calibration_20261016/observability_study.py` is a reproducible synthetic study, not firmware. It uses ideal corners in the reported room, a point attachment at 0.6 m nominal height, known payout scale, 2 mm independent position noise, 0.3 mm payout noise, 60 poses and 30 trials per case. Fits use rough-anchor bounds but no prior penalty. It does not model field of view, forces, dynamics or actual camera errors.

| Sample box width X/Y/Z | Median anchor error | Median fitting residual | Median withheld cable-change RMS |
|---|---:|---:|---:|
| 0.05 / 0.05 / 0.05 m | 398 mm | 1.98 mm | 8.27 mm |
| 0.30 / 0.30 / 0.20 m | 296 mm | 1.95 mm | 3.63 mm |
| 0.80 / 0.80 / 0.50 m | 55 mm | 1.96 mm | 0.83 mm |

The independent witness box is 1.2 × 1.2 × 0.6 m, still not the full room. The lesson is that a low residual can coexist with poor anchor recovery, and small motion does not establish room-wide geometry. The larger synthetic box is not a released trajectory or an expected hardware accuracy. Biased vision and payout errors can be worse. A noiseless fitting check recovered the synthetic anchor within 1 micrometre; this checks the algebra, not the machine.

## 9. Physical bead verification — retained as a required stage

### 9.1 What each bead establishes

A bead-switch event supplies one scalar cable-length reference, not the full claw pose. Let `h_i` be independently measured exposed span at first repeatable switch actuation, with a specified approach direction, outlet angle and low contact force. If that event occurs at payout change `d_i,event`, then `L_i,0 = h_i - d_i,event` in the simplified span model. Add/calibrate known routing corrections consistently.

If `h_i` is unknown and is defined using the same camera model being checked, the event is repeatability evidence but not an independent absolute-length verification. Measure bead-to-attachment length and trigger geometry beforehand, then bench-characterize trigger angle, hysteresis and repeatability. Do not set every cable's current length to zero when one bead triggers.

Nonpassing beads still impose `L_i >= h_i` approximately. Put them as near the claw as needed for workspace **only after** finding a reachable trigger configuration and allowable stopping travel. More accessible trigger lengths consume short-cable workspace; this tradeoff is physical and cannot be removed by calibration software.

### 9.2 Plan the entire four-cable approach

For each i, find a pose satisfying `L_i(p,R) = h_i`, other cable-length bounds, motor torque/speed limits, positive feasible tension, outlet-angle limits, wall/ceiling/claw clearance and camera/position uncertainty. For spaced attachments include torque equilibrium and passive orientation stability, not just three force equations. Test the complete approach and retreat, not just the endpoint.

Use measured torque at the operating speed and actual wound radius; do not reuse the website's unverified 40 N cable limit. Even a tension-feasible nominal path needs an uncertainty margin. The waypoint is below/inboard of the outlet where possible, not automatically the ceiling corner.

Start from the validated central region. Move toward one bead while commanding all four stations. Slow within a bounded search window. The target station captures the first switch edge and encoder count locally and suppresses further shortening; all stations execute a bounded stop. Validate the electrical open state, then perform a coordinated retreat until the switch releases and repeat at low speed. A broken NC wire also reads open: an unexplained open signal or failure to release is a fault, not successful home.

Allow for contact travel and total response distance: `v * worst_detection_and_stop_delay + v^2/(2*deceleration)` plus mechanical compliance and uncertainty. Local immediate pulse suppression and the other stations' stop lag need separate testing. Do not drive the bead hard against the ring or use switch bodies as sustained load stops. The refinement approach must be slow enough that debounce does not consume available stroke.

Record the **pre-update** mismatch between predicted and measured event. Only after it passes the uncertainty-based acceptance test may that event refine the reference. Repeat contact checks, then withhold at least one repeat/witness pose from the final refit. Return through a checked route before the next bead. Keep A/B/C/D identities intact.

### 9.3 Visibility during corner checks

A single six-inch floor marker near the center is not assumed visible from all four near-outlet poses. Project its corners along each path with the actual camera and claw geometry. If vision is lost, an encoder-only continuation is permitted only within a separately validated pose-uncertainty bound; extrapolation from a tiny calibration patch does not qualify.

Possible remedies, to evaluate in order: choose a feasible bead pose still seeing the original tag; adjust camera placement/angle or marker size; extend the local map using additional uniquely identified markers with overlapping observations; or use another qualified position reference. A moved sole marker requires re-registration. These are alternatives, not evidence that the single-sheet full route already works.

If a mandatory bead has no qualified route, report `BEAD_VERIFICATION_BLOCKED` and retain `LOCAL_ONLY`, rather than reporting READY or silently deleting that check. A passable optical cable mark or revised outlet mechanism is a future hardware alternative if the bead travel restriction proves incompatible; it is not adopted by this revision.

## 10. Encoder fault handling and tension

Compare unwrapped measured spool angle against commanded angle, accounting for direction and gearing. Set following-error tolerance and dwell from measured normal lag/noise and the maximum acceptable lost motion. Use local freshness checks, magnet diagnostics, boot IDs and sequence numbers. A missed sample must not be treated as a valid half-turn wrap; maximum speed and sample interval must preserve unwrapping observability. [R5]

If a sensor is on the motor shaft it cannot see spool-to-shaft slip. A spool-mounted sensor covers that interface but still cannot prove line traction. Image pose residuals supply a different check. No encoder-only rule directly measures tension. Do not deliberately use weak-motor stalling as the tension-control strategy.

Any tracking fault cancels pending coordinated movement, latches fault and requests all-station stop; each other station also has a bounded local lease. Do not automatically replay missed steps or release the stalled cable. Initial recovery is supervised with support; automatic relief needs its own measured feedback and test sequence. Maintaining holding current is conditional on available torque and temperature, not a guarantee against a fall.

## 11. Acceptance tests and release evidence

Complete in this order. Items are proposed tests; none is marked passed by this document.

| ID | Test | Evidence and exit criterion |
|---|---|---|
| T01 | One driver, motor, encoder and switch on supported bench | Coil map, current limit, direction, encoder ratio/wrap, switch release/press/unplug behavior, measured stop latency; no suspended load |
| T02 | Camera on fixed fixture | Known-pose errors over intended heights/angles, tag size/focus, ambiguity handling, timestamp age; preserve images and calibration file |
| T03 | Payout and bead bench metrology | Payout over operating layers in both directions, retained wraps, 10 repeated trigger/release cycles at relevant approach angles, measured h_i and uncertainty |
| T04 | Four-station communication without suspension | Shared segment starts, expiry, dropped/stale/duplicate commands, one-node reboot and injected encoder faults; measured worst other-axis stopping distance |
| T05 | Supervised central floor pickup | Grid of allowed starts/slack patterns, upright empty claw, slow lift, external observation; no uncontrolled tip/drag, overload or following-error events in accepted trials |
| T06 | Local visual calibration | Multiple directions/heights, actual encoder movement and settled images; held-out motion and measured reference checks meet allocated error budget |
| T07 | Expanded calibration | Uncertainty acceptable along proposed verification routes, not only near tag; payout model and orientation assumptions remain valid |
| T08 | One bead approach, then four | Path clear/feasible, bounded search, first edge captured, repeatable release/retrigger, pre-fit reference residual accepted; vision-loss handling tested |
| T09 | Full repeated startup | Upright floor → short lift → marker → fit → physical verification → READY; repeat with realistic lighting/slack/start variation and record successes/failures |

For early screening, consider a camera static pose-error target of 5–10 mm and roll/pitch error within 2 degrees over the local calibration region, with roughly 20–40 distinct settled sample poses and separate witness poses. These are proposed experiment targets, not demonstrated specifications. If the camera cannot meet them, adjust optics, marker size, lighting or sampling before interpreting mount fits.

Final tolerances must follow the available mechanical clearance, pickup accuracy, bead repeatability and stopping distance. Accept a bead residual against the combined camera, geometry, payout and trigger uncertainty, not a guessed universal millimetre threshold. Reject a fit whose uncertainty reaches an operational boundary even when average residual is small. Expand sample baselines when needed; do not simply repeat 40 nearly identical poses.

Multiple successful trials do not establish a certified fault probability. Retain failure logs, use holdout starting conditions, and scope the release to the tested envelope. Sensorless automatic slack handling remains provisional until T05/T09 establish a sufficient margin, or until tension feedback is added and tested.

## 12. Open parameters and how to close them

| Parameter | Resolution method | Owner/input |
|---|---|---|
| Common vs spaced attachment geometry | Photograph/current CAD and measure b_i | User provides current build; model supports either |
| Upright camera height/offset/angle | Measure optical center and camera-to-body transform | User measurement + camera fixture experiment |
| Camera sensor/lens and stream mode | Read sensor identity; calibrate actual captured mode | Bench capture |
| Motor model, current, effective torque | Label/sense resistors, supported current-limit and load tests | User hardware evidence + bench tests |
| Actual spool payout | Encoder/length measurement across wraps and reversals | Bench metrology |
| Encoder model/mount | Confirm purchased board, rigid magnet coupling, diagnostics | User inventory + bench tests |
| Initial slack and allowed central region | Deliberate measured perturbation matrix | T05 |
| Pickup packet/speed/cumulative cap | Worst-case response under the approved start envelope | T01/T04/T05 |
| Ground clearance and tilt bounds | Actual claw envelope and camera uncertainty | CAD/fixture + T02 |
| h_i, bead diameter, switch stroke and repeatability | Direct length/angle/trigger measurements | T03 |
| Marker coverage at bead targets | Calibrated projection along candidate trajectories | T02/T07 |
| Maximum allowed tension/minimum tautness | Actual mechanics and force/thermal capability | Bench test; model predictions are not measurements |
| Need for permanent tension sensors | Decide from pickup and calibration performance; provision mounting space | T05/T09 decision |
| Gravity direction | Level-floor verification initially; optional mounted IMU | Measured setup |
| Network/camera age and clock error | Log timestamps and worst observed latency plus margin | T04/T02 |

## 13. Implementation backlog and record format

1. Add a separate A4988 station hardware profile; retain the experimental detached controller as historical bench code.
2. Implement encoder-aware short segments, homing edge snapshots, command expiry and coordinated stop protocol. Keep motor-reference validity separate from diagnostic encoder counts.
3. Implement camera capture metadata, intrinsic/extrinsic calibration, marker pose ambiguity filtering and replayable logs on PC.
4. Implement an offline estimator and replay tool first; then add the bounded startup state machine behind an explicit experimental feature flag.
5. Implement path feasibility/uncertainty checks and the per-bead verifier; replace the current detached-only integration only after the new mode is tested.
6. Add the phone setup flow and results view; save versioned calibration artifacts rather than silently modifying constants in source files.

Log: run ID, revision/firmware IDs, hardware identities, station boot/sequence IDs, timestamp clock domains, encoder raw/unwrapped readings, commanded steps, direction, switch state and edge snapshots, actual tensions if fitted, camera frame ID/capture age, corners, candidate poses, accepted pose/covariance, fit parameters, scaled-Jacobian diagnostics, residuals, witness results, bead pre-update residuals, fault/stop times and operator interventions.

Store calibration validity scope: marker frame, payout interval/layers, motion envelope, mass/configuration, verified bead IDs, camera calibration checksum and expiry conditions. Reboot with lost turn counts, shifted marker, moved mount, changed camera bracket, spool slip/rewind or significant configuration changes triggers re-referencing as appropriate. Room dimensions do not locate the laundry hamper; register it separately in the accepted frame.

## 14. Sources and scope

Sources accessed 2026-10-16. References establish component/method behavior; all proposed RoomCleaner limits and sequences above remain engineering decisions requiring testing.

- **R1:** Tremblay et al. (2019), *Eye-on-Hand Calibration Method for Cable-Driven Parallel Robots*, DOI https://doi.org/10.1007/978-3-030-20751-9_29 . [Institutional abstract](https://constellation.uqac.ca/id/eprint/6613/). Full author manuscript inspected through an accessible [mirror](https://artefacts-discovery.researcher.life/full_text/DA-2/c2/c27b38d928fd3e0db89c852c2a314115/full_text/414fde7113c7ff62dceab78a3a97dc4c.pdf); its title/author/DOI agree with the institutional record. This is method precedent, not a four-stepper floor-start demonstration.
- **R2:** [AprilRobotics AprilTag](https://github.com/AprilRobotics/apriltag). Marker generation, size convention and pose estimation inputs. Does not guarantee accuracy of our printed sheet/camera.
- **R3:** [OpenCV PnP documentation](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html). Intrinsics, distortion, transform conventions and multiple-solution planar solvers.
- **R4:** [IPPE authors' implementation](https://github.com/tobycollins/IPPE). Two-solution planar ambiguity, especially with small/distant projected targets.
- **R5:** [ams OSRAM AS5600 datasheet](https://look.ams-osram.com/m/7059eac7531a86fd/original/AS5600-DS000365.pdf). Single-turn magnetic angle sensing and sensor diagnostics. Exact purchased breakout remains to be confirmed.
- **R6:** [Pololu A4988 carrier documentation](https://www.pololu.com/product/1182). Logic/motor supply separation, current regulation, capacitor and hot-plug precautions. Clone sense resistors must be identified separately.
- **R7:** [Espressif ESP32 camera driver](https://github.com/espressif/esp32-camera). Supported platforms/sensors, JPEG and buffering guidance; no measured end-to-end performance for this project.
- **R8:** [SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html). Bounded robust nonlinear optimization. The saved study used installed SciPy 1.17.0; retrieved current docs may describe a later release.
- **R9:** Lau (2018), [Initial length and pose calibration for cable-driven parallel robots with relative length feedback](https://research.cuhk.edu.hk/en/publications/initial-length-and-pose-calibration-for-cable-driven-parallel-rob-2/). Initial-length uncertainty is a distinct calibration problem; abstract reviewed.

Additional leads: Mai et al. (2026), DOI https://doi.org/10.3390/s26072204 , and Guo et al. (2024) [preprint](https://www.researchsquare.com/article/rs-4016435/v1). Same/similar titles appeared with different author/version metadata. Full text was not reliably accessible this session, so no quantitative result or hardware assumption from those sources is used here.

## 15. Decision

Adopt **central upright floor pickup → nearby arbitrary-position marker → visual/encoder geometry calibration → sequential coordinated bead verification → operation** as the startup development direction. Preserve the current hardware bring-up work. Do not equate this design document, the synthetic fitting study, or one successful switch test with a completed automatic robot startup.
