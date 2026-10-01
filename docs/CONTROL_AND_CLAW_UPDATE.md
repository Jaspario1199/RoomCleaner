# Verified laundry cycle and hardware integration — 2026-09-30

## Implemented behavior

Planning previews do not remove detected items, increment delivered counts, or
change the physical pose estimate. Execution advances pose only after each
motion action has been acknowledged. The mission sequence is:

1. Acquire fresh detections and select a reachable item.
2. Approach, descend slowly, capture the selected clothing's appearance.
3. Close the claw. Lift and move up to 0.20 m toward the hamper.
4. Require matching clothing to move at least 20 image pixels into the expected
   probe region in three fresh observations. Disappearance does not pass.
5. If unconfirmed, return to the pickup point slowly, open, confirm the target
   is still there, and retry. Stop after three attempts or if identity is lost.
6. Carry to the hamper and positively identify the payload there before opening.
7. Open, move the claw clear of the hamper image region, and require the matching
   clothing to remain stable in the receiving ROI in three fresh observations.
8. Only now increment the delivered count and retire the selected item.

A failed/ambiguous delivery stops with no count increase. It does not blindly
retry another delivery or assume the floor is clear. Live execution cannot use
simulation verification. Unknown camera calibration prevents a live mission.

The first camera implementation uses label + normalized image appearance, a
calibrated expected region, temporal freshness and ambiguity rejection. It is a
conservative prototype, not validated production tracking. Clothing deformation,
untextured cloth, occlusion, look-alike items and camera perspective can prevent
confirmation. A dropped item that remains inside the pickup probe ROI is still a
potential false positive: commission raised-payload versus floor-drop tests and
add multi-view depth or a claw sensor if the single view cannot distinguish them.
Delivery requires an unobstructed view into the hamper. This is a real hardware
acceptance condition, not something the floor homography can guarantee.

## Measured placeholders

Fill `roomcleaner/hardware/hw_config.py` after assembly:

| Field | Measurement |
|---|---|
| HOME_TRIGGER_LENGTHS_M | Four cable lengths at bead switch trigger, X/Y/Z/A order; None until measured |
| HOME_POSE_M | Measured claw cable-plane pose after setup payout and attachment |
| CAMERA_PROJECTION | 3x4 matrix from calibrated world points to image, including elevated points |
| HAMPER_ROI_PX | Visible receiving area, x1/y1/x2/y2 pixels |
| DRUM_DIA_M / STEPS_PER_M | Retain nominal diameter pending payout tests |

Measured trigger lengths must use the same outlet-to-claw datums as kinematics.
The firmware keeps the final backoff as a positive step offset from trigger zero.
HOME_POSE_M is a separately measured assembly pose after the homed spools pay
out its calculated lengths. Four trigger/backoff lengths generally cannot form
a valid suspended pose. It is not implicitly the computed parking position. Measured wall outlet coordinates must
also replace the simulated anchor coordinates.

## Homing explanation and revised procedure

The bead collar establishes a length reference; it does not by itself establish
a mutually compatible four-cable claw pose. Sequentially retracting each cable
with the claw freely suspended can overload or slack other cables. Therefore
this firmware only accepts `H DETACHED`: detach the claw and acknowledge
that setup through the host (`driver.home(detached=True)`; console home request
requires `detached: true`). This is bench/assembly homing, not autonomous
suspended-claw homing. A coordinated physical initialization procedure remains
to be designed and tested before autonomous power-up.

After homing: `prepare_pose` with `detached: true` pays out lengths for measured
HOME_POSE_M. Attach the supported claw at that pose, verify all four cable
attachments/lengths, then `confirm_pose` with `attached: true`. Only then can the
console run a mission. Standalone executor requires this setup and `home=False`.
Use `driver.prepare_pose(point, detached=True)` and
`driver.confirm_pose(attached=True)` outside the console. Operator confirmation
is a setup acknowledgement, not camera/encoder proof of physical position.

For each axis: release an initially active switch; bounded seek; backoff and
verify release; slow reapproach; set zero at trigger; backoff and retain its step
count. A stuck/open contact or missing trigger faults. NC wiring cannot identify
an open wire separately from an actuated contact electrically, but the required
release/retrigger sequence catches persistent faults. Bounds are provisional;
commission travel/time limits and HOME_DIR with one unloaded station first.

## Motion and stop

Provisional cable speed caps: 0.020 m/s travel, 0.008 m/s descent/probe/retry.
The host converts these to step-rate caps. These are not guarantees of Cartesian
speed. At 16 microsteps and a 20 mm drum, the existing 1200 step/s cap is only
about 0.0236 m/s cable payout. Do not assume the simulated 0.4 m/s applies to the
Uno build. Tune microstepping, driver current, loaded torque and timing together.

One accelerated scalar AccelStepper clocks a Bresenham pulse distributor, so all
four axes share the same progress/ramp. It stops at each waypoint; throughput and
swing need bench tuning. Corner waypoints are retained when thinning paths. Full
sampled paths check cable/fan/tension feasibility; pickup descent has its own
minimum height because GRAB_Z is below normal travel clearance. Furniture maps,
dynamic payload tensions and exact continuous segment proofs remain outstanding.

`X` interrupts an active move/home, retains driver power/holding torque, invalidates
homing, and requires rehoming. Limit inputs are checked during moves. This is a
software stop, not mechanical load retention during loss of electrical power.

## Encoder recommendation and mount concept

Start with one AS5600 sensor and diametrically magnetized magnet to validate the
mechanical interface before buying all four. Seeed's Grove module was listed at
USD 6.50 each on review (four = USD 26, excluding magnets, wiring, shipping and
controller hardware). It offers 12-bit angle data (4096 counts/revolution).

Attach the magnet concentrically to the spool's outer end face, with the sensor
on a stationary removable bracket facing it. This avoids needing a rear motor
shaft and observes spool-to-shaft slip as well as motor rotation. In the v2 winch,
spool end is approximately X=36 mm and the inside side wall approximately X=53 mm:
17 mm nominal packaging space before tolerances/connectors. Measure the actual
sensor board, magnet and motor magnetic interference before revising the cover.
No encoder mount CAD or sensor firmware is claimed complete in this update.

AS5600 returns one-turn angle, not cable length or stored multi-turn position.
Firmware must unwrap angle, detect missing/invalid magnet readings, enforce a
sampling limit, compare measured versus commanded rotation, and rehome after
lost state. It will not correct winding radius, cable stretch or cable sliding.
The fixed I2C address is 0x36; four units require separate buses/a multiplexer or
local controllers. Do not route an unvalidated long I2C bus around the room.
Choose local acquisition/wired communication before committing to wiring or a
new motion controller. The Uno's pin and processing budget needs review.

References: https://wiki.seeedstudio.com/Grove-12-bit-Magnetic-Rotary-Position-Sensor-AS5600/
https://www.seeedstudio.com/Grove-12-bit-Magnetic-Rotary-Position-Sensor-AS5600-p-4192.html

## Central claw packaging started

`python -m cad.claw_electronics` retains the existing frame, five TPU fingers,
hub, servo drum, standoffs and cover. It adds two removable strap-mounted bays
and reference electronics envelopes, with STEP/STL and an assembly export.

| Feature | Prototype value |
|---|---|
| Frame | Existing 92 mm square x 5 mm plate |
| Servo body reference | 41 x 20.2 x 38 mm, inverted |
| Hub / fingers | Existing Ø88 x 12 mm hub; five 70 mm fingers |
| Board envelope | 55 x 26 x 13 mm, provisional including connectors |
| Battery envelope | 55 x 25 x 18 mm, provisional |
| Bays | Centers Y=+31/-31 mm; floor starts Z=8.5 mm; 2 mm floor; 1.8 mm walls |
| Bay attachment | Strap passages align with existing frame slots; feet rest on frame |

Printed-bay validity, STEP round-trip and pairwise interference checks pass for
these envelopes. This does not verify battery fit, straps, wiring access, strength,
thermal behavior or loaded grasping. The cover's USB cutout/switch cutout are still
references, not aligned to a selected board/panel switch. Regulator mounting and
wire routes are not complete. Assembly STEP uses separate parts for inspection.

Electrical architecture: removable 2S pack -> fuse/power switch -> regulated
servo rail and regulated 5 V logic rail -> ESP32; common ground. Do not feed the
servo rail into an unspecified ESP32 board input. Select converters against
measured servo current transients; add suitable bulk capacitance and strain
relief. Use a charger/protection arrangement matched to the selected pack.
Low-battery telemetry, brownout behavior and charging/docking remain design work.

Need exact board, pack, regulator, switch and connector dimensions; actual servo
horn/spline dimensions; loaded servo current and required tendon force/travel;
and a weighed assembled claw. Target claw mass remains <=450 g; holding 0.9 kg
is a requirement awaiting testing, not a demonstrated capability.

## Validation

Python: controller/vision evidence regressions plus hardware, live, app, kinematic,
geometry and localization checks. AVR: sketch, actual AccelStepper/Servo and
Arduino AVR core compiled and linked for ATmega328P. Physical hardware tests have
not been run. Camera synthetic tests demonstrate gating logic, not real fabric
recognition. Geometry checks demonstrate nominal clearance, not manufactured fit.
