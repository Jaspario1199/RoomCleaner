# Extended laundry claw — SolidWorks design brief

Date: 2026-10-12. Units: mm unless stated otherwise.

**Status: proposed complete assembly architecture, with an audit of the previous CAD. Not a print release or a verified payload rating.** This brief supports the user's own SolidWorks design. No existing CAD was modified for this review. Historical interference reports were read, not rerun.

## 1. Design intent

- Keep the battery, controller, camera and regulators in an upper assembly with a removable lid.
- Use a printed rigid extension first, with the servo and a simple two-jaw clamp below it. Consider aluminum and flexible fingers after this mechanism works.
- Use replaceable TPU contact pads. Aim to collect fabric close to the floor without exposed fastener heads touching the floor or clothing.
- Move slowly with the body nominally level; do not plan intentional orientation maneuvers.
- Verify pickup by observing the garment move with the claw during a short transfer. Verify release/delivery before counting an item as delivered.
- Prefer M3 hardware, with exceptions for the purchased servo horn or boards when necessary.

The previous one-pound suspended test weight is a winch-system milestone, not proof that this claw can grip one pound of clothing. Proposed claw milestones: grip a small folded cloth, then a representative garment, then a measured one-pound garment load. A five-pound grip rating remains unestablished.

## 2. Assembly skeleton and load path

| Assembly | Function and proposed attachment |
|---|---|
| Structural upper deck | Carries cable anchors, extension and component trays. The removable lid carries no suspended load. |
| Cable anchors | Retain four spaced structural attachment points from the full-claw baseline provisionally. Use captive metal rings and positively retained pins/bolts; no corner bearings. |
| Electronics enclosure | Lid removes without disconnecting suspension or removing the extension. Trays/keepers restrain components in all directions; wires do not act as restraints. |
| Camera outrigger | Attaches to the structural deck independently of the lid. Adjustable aim; accessible lens, USB and antenna connection. |
| Two extension uprights | Bolted flanges join upper deck to lower carrier. One upright routes and strain-relieves the servo harness. |
| Lower carrier | Holds servo, rack guides and clamp loads together, so gear engagement does not depend on a flexible enclosure lid. |
| Servo horn and pinion | Supplied matching servo horn transfers torque into a bolted printed pinion. Retain the manufacturer's center screw; do not print an assumed spline. |
| Opposed racks and jaws | One pinion translates two guided racks in opposite directions. Guide rails resist jaw bending and prevent rack lift/disengagement. |
| TPU pads | Replaceable, backed by rigid jaws. Prefer fastening from behind; keep hard hardware recessed from the contact surface. |

Load path: garment → pads/jaws → rack guides/lower carrier → extension flanges → upper deck → cable attachments. Grip torque travels through servo horn → pinion → racks. Review both paths independently.

**Suspension decision:** four cables meeting at one point was specified for the suspended test weight. It is not automatically the full-claw configuration. Four spaced anchors can resist some body rotation but do not provide arbitrary orientation control or guaranteed leveling. A common-point suspension simplifies the cable junction but leaves the body free to swing/yaw and depends on its center of mass to hang appropriately. Freeze this choice before drilling anchor holes or implementing the full-claw kinematics.

## 3. Dimensions available from the previous CAD

These are source-code dimensions, not measurements of purchased hardware or approved structural sizes. They provide a starting envelope for a master SolidWorks layout.

Reference frame: upper structural deck underside Z=0; downward is negative Z; camera projects toward +Y; jaws move along X.

| Parameter | Previous value | Disposition |
|---|---:|---|
| Upper deck | 160 × 150 × 4 | Starting envelope; verify bending, anchor roots and component fit. |
| Cover external envelope | 142 × 130 × 50 | Starting envelope; chamfered corners reduce usable space. |
| Lower carrier | 140 × 90 × 4 | Starting envelope; check servo pocket and guide fastener ligaments. |
| Lower carrier underside | Z = −150 | Proposed extension length reference. |
| Upright centers | X = ±43, Y = 0 | Starting spacing. |
| Upright outer/inner sections | 14 × 18 / 8 × 12 | Nominal 3 mm walls; strength not qualified. |
| Upright flanges | 24 × 82 × 6 | Review fillets, fastener access and print direction. |
| Lowest pad surface | Z = −246.5 | Check ground reach against every other component. |
| Cable attachment reference plane | Z = +21.5 | Total nominal attachment-to-pad reach: 268. |
| Cable clevis centers | X = ±69, Y = ±64 | Provisional four-point option. |
| Camera lens reference position | (0, 136, 22) | Outboard position; vulnerable to collision unless protected. |
| Camera axis | 28° inward from downward | Starting aim; measure real image coverage. |
| MG996R body envelope | 40.7 × 19.7 × 37 | Measure actual servo, mounting ears, shaft and cable exit. |
| Servo body pocket | 43 × 22 | Historical clearance only. |
| Pinion | Module 1.5, 24 teeth, 20° pressure angle | Pitch Ø36; tip Ø39; 7 thick. |
| Rack body | 116 × 10 × 7 | Review tooth engagement and guide overlap at both limits. |
| Rack track centers | Y = ±24.875 | Includes old jaw/rack geometry; not simply pitch radius. |
| Jaw plate | 4 × 44 × 70 | Check bending at neck and rail connection under grip force. |
| TPU pad | 5 × 40 × 36 | Requires closure correction; see below. |
| Nominal jaw opening | 77.4 | Useful opening at old starting angle. |
| Servo nominal sweep | 20° to 140° | Calibration placeholders, not safe physical limits. |
| Battery reference tray | 78 × 39 × 18 | Old pack allowance 76 × 37 × 14; actual battery unknown. |
| Old ESP-WROOM tray | 68 × 36 × 20 | Only relevant if retaining that board; measure actual variant. |

At the existing camera position, its axis intersects the pad-bottom plane at approximately Y=136−268.5 tan(28°)=−6.8 mm. This points near the grasp center, but does not prove unobstructed vision of bulky clothing or adequate field of view.

## 4. Mechanism correction required before detailed CAD

The existing pinion pitch radius is 18 mm. With 120° rotation:

- Rack travel per jaw = 18 × 120π/180 = **37.699 mm**.
- Remaining pad gap = 77.4 − 2 × 37.699 = **2.002 mm**.

Therefore the old nominal closed position cannot pinch thin fabric between the modeled pad faces.

Proposed correction: make pad projection adjustable with replaceable pads/shims, then set the commanded closing endpoint from real contact tests. Adding approximately 1.001 mm projection per pad would only bring the nominal faces into contact; additional compliant travel is needed to develop grip force. Do not just extend servo travel: another 3.186° closes that geometric gap, but gear engagement, rack overlap, servo limits and collision clearances must be checked first.

Required features and checks:

1. Capture each rack against lift and sideways movement while maintaining printable running clearance.
2. Include mechanical travel stops beyond the calibrated operating range; a stop must not be the normal continuously powered closing position.
3. Leave access to the servo center screw, horn-to-pinion fasteners and rack-guide fasteners after assembly.
4. Check gear mesh, guide overlap, bolt tips and jaw collisions throughout travel, not just at endpoints.
5. Pad mounts must withstand shear without relying only on glue or TPU friction against a screw head.
6. Keep lower pad edges close enough to the floor to collect cloth; add a rounded, non-snagging contact edge. Flat-cloth pickup still requires testing.
7. Use an initial fit coupon for sliding clearance (for example 0.15, 0.25 and 0.35 mm per side), printed in the final material and orientation.

### Grip-force screening

For a friction-only two-jaw pinch, with normal force N at each pad:

`2 μ N ≥ S m g`, and `required servo torque ≥ 2 N r / η = S m g r / (μ η)`.

Illustration only: pad/fabric friction μ=0.5, reserve multiplier S=2, transmission efficiency η=0.8, pitch radius r=0.018 m.

| Garment mass | Required force per jaw | Required servo torque |
|---|---:|---:|
| 1 lb (0.454 kg) | 8.90 N | 0.400 N·m |
| 5 lb (2.268 kg) | 44.48 N | 2.002 N·m |

TowerPro lists MG996R stall torque of 9.4 kg·cm at 4.8 V (~0.922 N·m) and 11 kg·cm at 6 V (~1.079 N·m). Stall torque is not a continuous holding rating, and the actual purchased servo may differ. Under the illustrative assumptions, five pounds exceeds even the listed stall torque. One pound remains a test target, not a certified capacity.

If testing shows insufficient force, options include a smaller pinion/longer servo sweep within verified travel, a linkage with higher mechanical advantage near closure, or geometry that gathers/supports fabric instead of depending only on friction. Each changes travel or packaging; do not order a stronger servo before measuring the shortfall.

## 5. Electronics architecture and packaging

Recommended wireless camera path, conditional on purchase: **XIAO ESP32-S3 Sense with its matching camera**, plus the existing positional servo. The existing ESP-WROOM board's USB programming connector does not directly host the ordered USB UVC camera. Retaining that camera would require another suitable host and a different power/volume budget.

Manufacturer documentation now lists OV3660 on newer S3 Sense units; earlier units used OV2640. Match the enclosure to the actual delivered board/camera revision. The old CAD used an OEM model with an overall envelope approximately 24.363 × 17.78 × 13.96, including protrusions; the advertised board size alone is insufficient.

Power branches:

| From | To | Requirements |
|---|---|---|
| Protected/appropriately monitored 2S battery | Fuse near battery, then accessible disconnect | Size fuse and wiring from measured loads, wire ratings and inrush. Old 5 A value is provisional. |
| Switched battery bus | Dedicated servo regulator → servo power/ground | Start with a regulated 5 V rail; choose verified peak-current capability and thermal margin. |
| Switched battery bus | Separate logic regulator → board-approved 5 V input | Follow exact board power/USB isolation instructions; include voltage drop if using a series Schottky diode. |
| Controller GPIO | Servo signal | Common ground reference; verify reliable 3.3 V signal recognition with the actual servo. |
| Camera module | Matching controller camera connector | Use the supplied compatible interface, not arbitrary pin wiring. |

- A fully charged 2S pack is 8.4 V. Do not connect it to the XIAO's single-cell battery input or directly to a 5 V rail.
- Route servo return current directly to the power split, not through controller ground traces. Use strain relief at the lower servo and both ends of the upright channel.
- Provide space for plugs and wire bends, not only PCB rectangles. Target an initial ~350 mm servo harness, then measure the routed assembly before cutting.
- Use captive trays/edge keepers for boards without suitable mounting holes. Avoid squeezing connectors or components.
- Keep battery retention broad and non-puncturing. Make removal and external balance charging possible without dismantling the structural assembly.
- Preserve antenna clearance, regulator ventilation and access to the disconnect with the lid installed.
- Implement battery undervoltage handling before unattended use; wireless loss must not trigger an automatic release of a carried item. Stopping motion does not make a non-braked winch fail-safe.

Pololu D24V50F5 (5 V, nominal 5 A) is a previous servo-regulator candidate, not a confirmed purchase or an automatically sufficient solution. Check dropout at low battery voltage, actual servo peak current and enclosure temperature. Reported MP1584EN stock also requires testing; a listing's current headline is not proof of enclosed continuous capability.

## 6. Logic skeleton

1. **Boot/check:** outputs enter a defined state; check battery, camera and communication. Confirm empty gripper before any automatic open/close calibration.
2. **Ready:** PC identifies the claw and stations; explicit arm command permits motion. Claw reports command acknowledgments and available health data.
3. **Scan:** PC processes streamed images using calibrated camera intrinsics, camera-to-body transform and time-associated body pose. A moving camera cannot use an unchanged ceiling-camera floor mapping.
4. **Approach:** slow down near the garment and floor; observe before final descent. Include the full extended body and camera outrigger in collision clearance.
5. **Close:** command a calibrated position/rate. Servo command acknowledgment proves command receipt, not fabric contact or grip force.
6. **Lift/verify:** lift or move a short controlled distance. Verify garment motion relative to the scene while accounting for camera motion; retry within a limited count if pickup failed.
7. **Carry:** use conservative acceleration and monitor visibility/health. A blocked image is uncertainty, not pickup confirmation.
8. **Release/verify:** release at the target; confirm separation/delivery before incrementing completed count. If the onboard view cannot establish delivery, retain an unverified state.
9. **Fault:** stop coordinated travel and require recovery appropriate to the load and fault. Define low-battery and communication-loss behavior before room trials.

This is the required behavior specification. This review does not claim all behaviors are implemented in firmware or perception code.

## 7. BOM status and design consequences

Purchase states below come from project records/user statements, not a current physical inventory. Quantities are for one claw unless noted.

| Item | Qty | Recorded status / action |
|---|---:|---|
| MG996R positional servo | 1 | Reported bought/ordered; confirm actual unit and horn. |
| ELEGOO ESP-WROOM-32 board | 1 | Reported bought/ordered; reusable for control, but not direct USB-camera hosting. |
| Innomaker USB UVC camera | 1 | Reported ordered; not directly compatible with the proposed XIAO camera connector. |
| XIAO ESP32-S3 Sense camera kit | 1 | Candidate, purchase not confirmed. Freeze board/camera choice first. |
| 2S battery + compatible balance charger | 1 each | Exact purchased model/status unknown. Old OVONIC 1000 mAh envelope is provisional. |
| Servo buck regulator | 1 | Candidate D24V50F5; not confirmed bought. Verify requirements. |
| Logic regulator | 1 | MP1584EN stock reported ordered; qualify voltage/current behavior. |
| Power-isolation diode if required | 1 | 1N5819 stock reported delivered in another project; confirm available quantity and board wiring. |
| Battery fuse/holder and disconnect | 1 each | Exact ratings, connector type and receipt unresolved. |
| Servo extension, power wires, connectors, strain relief | 1 set | Select after power and routing measurements. |
| Closed metal cable rings and retained anchor pins | 4 sets provisionally | Exact supplier/section and retention unresolved. |
| M3 screws, nuts/inserts and washers | Stack-dependent | M3 kit reported bought; inventory lengths before final counterbores. |
| OEM horn fasteners / small board fasteners | As needed | Measure; do not assume all can become M3. |
| PETG upper deck/lid/trays, uprights and lower carrier | 1 set | Redesign/verify against actual components. |
| Pinion, racks, guide rails and rigid jaws | 1 set | Resolve pad gap, horn fit, guide capture and travel first. |
| TPU pads | 2 | Replaceable design, hardness/material availability to confirm. |
| Tilt sensor | Optional later | Not needed for the first standalone grip test; sensing alone does not provide leveling control. |

Do not issue a final fastener order from the old screw list: changed pad thickness, servo horn, nut type and flange stack change the needed lengths. Use screw length = clamped stack + nut/thread engagement + intentional protrusion, with clearance checked on the far side.

## 8. Assembly sequence to design around

1. Bench-test controller, camera, regulators and servo electrically before enclosing them.
2. Assemble servo/horn/pinion on the lower carrier with the shaft and center screw accessible.
3. Install racks/jaws and capture rails; check full travel by controlled low-force operation.
4. Install pads and calibrate contact, useful opening and allowed compression using fabric samples.
5. Bolt uprights to lower carrier; route and retain the servo harness.
6. Install upper deck and cable-anchor hardware; verify tool access and bolt-tip clearances.
7. Secure battery, regulators and controller in separate retained positions; connect and strain-relieve wiring.
8. Fit and aim camera with the clamp open, closed and carrying representative fabric.
9. Close lid, then confirm battery/disconnect access and all external cables remain clear of moving parts.

## 9. Release gates and immediate work order

**First print:** servo/horn fit coupon, rack-guide fit coupon and one jaw/pad fastening sample. Use these to resolve fit before printing the enclosure and long uprights.

**Then test the lower mechanism on a bench:** verify mesh throughout travel, pad contact, measured pull-out force, flat/folded fabric behavior, servo current and heating during repeated cycles/hold. Check controller brownouts while streaming and closing together.

**Then complete upper packaging:** actual component models, connector/tool access, lid extraction, wiring route, battery retention, camera coverage and weighed center of mass.

**Then supported suspension:** verify structural anchors and extension with a controlled load test close to a support surface. Choose proof loads from the actual service tension/geometry and reserve requirement; do not reuse the old 120 N anchor target merely because an earlier model assumed a 40 N motor limit. Record deflection, cracks, slip and permanent set.

Only after these pass: low-height pickup trials, four-station integration, and gradually wider travel. Printed PETG thicknesses and infill settings alone do not establish structural capacity.

## 10. Measurements needed from the user

Highest priority, before the first detailed mechanism revision:

1. **Servo and horn:** photo of label; front/side horn photos with calipers; body L/W/H; ear-hole spacing and diameter; mounting-ear thickness; shaft-axis offset from body end; shaft/horn height above mounting plane; horn diameter/thickness; usable horn-hole spacing; supplied center screw. Confirm positional, not continuous-rotation, servo.
2. **Camera/controller actually being used:** exact product link or label/photo. Is it the existing ESP-WROOM plus USB camera, or has the XIAO S3 Sense kit been purchased? Include camera revision and whether headers are installed.
3. **Battery:** exact model, cell count, capacity, measured L/W/H, lead exit and connector type; identify the charger. If not bought, say so before sizing its tray.

Before final upper-deck CAD: choose spaced cable anchors versus a common-point junction, confirm pad material, and measure the actual regulator/connector envelopes. The camera choice changes the controller bay; the battery choice changes both volume and suspended mass.

## References and evidence boundaries

Local design sources: `cad/clamp_v1.py`, `cad/clamp_extended_v3.py`, `cad/extended_camera_pod.py`, `docs/CLAMP_V1_BUILD.md`, `docs/EXTENDED_CLAW_V3_BUILD.md`, `docs/CLAW_CAMERA_V2_BUILD.md`, `docs/BOM_CLAMP_V1.csv`, `docs/CLAMP_ASSEMBLY_REVIEW.md`.

Historical reports under `verification/` establish only what their modeled/sample checks covered. They do not validate actual hardware fit, continuous grip torque, fabric friction or printed-part strength. The older tentacle mass/torque calculations in `calculations/claw_integration.md` do not qualify this extended rack-and-pinion claw.

Manufacturer sources checked for this review:

- Seeed XIAO ESP32-S3/Sense hardware and power guidance: https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/
- TowerPro MG996R specifications: https://towerpro.com.tw/product/mg996R/
- Pololu D24V50F5 regulator: https://www.pololu.com/product/2851
- Pololu mechanical drawing: https://www.pololu.com/file/0J1436/d24v50f5-step-down-voltage-regulator-dimensions.pdf
