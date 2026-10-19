# Measurement and commissioning worksheet

Fill only after the referenced part/assembly exists. A blank is unknown. Record units, instrument/method, uncertainty, date and hardware/process revision. Nominal supplier dimensions and actual measurements are separate records. This sheet is for the current extended clamp and candidate local stations; it does not request measurements already supplied unless a fit/variant needs confirmation.

## A. First inputs: before final outlet and casing geometry

| ID | Quantity and datum | Existing evidence | Actual / uncertainty / revision |
|---|---|---|---|
| M01/C01 | Four metal throat positions XYZ in one floor-based room frame [m]; station orientations [deg] |4×3×2.6m ideal room is a code example | pending |
| M01/M20 | Real room dimensions, studs/wall finish thickness and offsets [mm]; furniture/fan volumes | Wall mounting into studs selected; physical wall stack unknown | pending |
| M03 | Real braid outside diameter at several locations [mm], measurement/load method |120lb,8-strand,150m user selection;0.6mm CAD reference | pending |
| M05 | Received ring OD, throat, groove and axial width [mm] | RF8090-05 selected; supplier model proxy exists | pending receipt / measurement |
| M06 | KW12 actual body/holes, roller/lever envelope, terminals; electrical trip/release/overtravel [mm] and operating force [N] |20×10.5×6.5mm body supplied; lever/trip/force not supplied | pending |
| M07/M08 | Received spring free/solid lengths/rate; shoulder diameter/length; guide friction with print | Z-2CS andSHS3-12 selected nominal candidates | pending receipt / tests |
| M13/M14 | Motor shaft flat/projection, thread depth and hub fit | Supplied42.3face/38body/31pitch/22boss/5shaft/24projection retained | only confirm actual differences or failed fit; thread depth pending |
| M25 | Actual matching horn OD/thickness, underside-to-shaft/body stack, center-screw head and mounting pattern [mm] | PositionalMG996R-class servo; printed spline is not assumed | pending |
| M31/E03 | Battery label/cell count/capacity, actual body/lead/connector envelope [mm] |2S pack is a candidate; supplier maximum envelope in CAD | pending receipt / identification |
| M29/M32 | Exact populated boards, sockets/solder tails, connector/boot profiles and wire bend route [mm] | OEM camera/encoder and driver board references exist; harness not controlled | pending receipt / route |
| M16/C02 | Weighed upper assembly, lower clamp, completed effector, each station and representative maximum payload [kg] |0.45kg old effector assumption is not a new measurement | pending |
| M16/C01 | Complete effector COM relative to cable plane in X/Y/Z [m]; payload CG range | Four attachments at nominalX±69/Y±64mm; actual COM absent | pending |
| M35/M36/O01 | Actual filament/profile and M3/M2 screw lengths/head/nut/washer/insert envelopes [mm] | M3 stock reported; exactM3×5 cup screws not confirmed | pending inventory / coupons |

## B. Detached station commissioning records

| ID | Test and outputs | Record |
|---|---|---|
| C06/M15 | Controlled forward/reverse revolutions: microstep strap, sign, counts, AGC/magnitude/status, actual eccentricity/gap/runout | pending |
| C03/M04–M08 | Repeated home return at each allowed angle: bead displacement, switch position, trip/reset distribution, maximum force, collar overtravel and binding | pending |
| C04/M11 | Independent payout length versus spool angle/layer/tension, both directions; actual retained wraps and capacity | pending |
| M12/E01 | Current/VREF, useful torque/speed, input current/inrush and temperatures with actual cover and duty | pending |
| M10/M14 | Braid/termination/stopper/hub retention and wear; warmed reverse/axial loading on restrained fixture | pending |
| C07/C09 | Actual encoder/driver/link fault latency, stopping travel and holding/backdrive behavior | pending |
| E02/M32 | Actual fuse/connector/wire route, DC protection coordination, voltage drop and service loop | pending |

## C. Supported claw and machine records

| ID | Test and outputs | Record |
|---|---|---|
| M23/M25–M28 | Horn/rack/rail/stops, TPU cloth pullout, extension deflection and full body envelope | pending |
| C12/C01 | IMU mounted alignment and known-angle fixture; observed settled roll/pitch/yaw across supported poses, empty/loaded | pending |
| E03 | Camera+loaded servo current, voltage drop, runtime, cutoff and heating | pending |
| C08/C09 | Common four-axis segment timing, readiness/abort and all-axis fault/boot recovery under injected failures | pending |
| M17–M22/M35 | Printed process coupons, wall stack/seat, dock/outlet/shaft/clevis directional proof and warm creep, with predeclared deformation limits | pending |
| V01/V02 | Calibration images/intrinsics, assembled extrinsics, fiducial survey, localization error and frame/pose ages | pending |
| V03/V04 | True/false pickup and delivery videos, payload occlusions and moving-camera negative cases | pending |

A photo of a purchased item establishes identity/receipt evidence, not performance. Camera-confirmed laundry delivery and supplier-part receipt are different verification events. Do not convert receipt into a motion or load qualification.

Store each test result with the relevant group ID and exact revision. Update the JSON closure ledger with the measurement/evidence metadata; update runtime calibration only after the required group dependencies pass. No unknown trigger length or setup pose is replaced with zero to enable motion.
