> Historical V2 decisions. For current mount printing and fasteners, use [MOUNT_PRINT_RELEASE_20261002.md](MOUNT_PRINT_RELEASE_20261002.md). Its M3×5 spacer-free cap,0.5mm recess and fastener stacks supersede the old ordering worksheet and recipes below.

> Primary build changed to [EXTENDED_CLAW_V3_BUILD.md](EXTENDED_CLAW_V3_BUILD.md):printed150mm extension, lower servo/clamp, upper electronics,28degree camera pose. Compact V2 remains a historical baseline.

> Camera pod now designed: see [CLAW_CAMERA_V2_BUILD.md](CLAW_CAMERA_V2_BUILD.md). Earlier notes about an unfrozen camera pod describe the prior revision; physical/optical validation remains pending.

# Spool, outlet and moving-camera revision — 2026-10-01

This revision is a bench prototype. No order has been placed, no physical receipt confirmed, and no hardware fit, encoder response or camera pickup cycle verified. Existing motor dimensions are retained; do not reorder motors to match a new assumption.

## Spool and encoder

The original printed spool has a 20 mm core, 26 mm winding width, two 36 mm diameter x 3 mm flanges and 32 mm overall length. V2 preserves its winding geometry, cable tie-off, 5.3 mm shaft bore and original 0.5 mm D-flat assumption. Confirm the actual flat against the printed original; this is not a new measured motor specification.

A separate cup locates on the outer flange: 36.4 mm internal / 38.4 mm external diameter, 3 mm skirt. Three M3 x 6 screws, each with a measured 1 mm nonmagnetic head spacer, on a 26 mm pitch circle retain it. Cup screw recess diameter is 6.4 mm, depth 1 mm; choose button heads and spacers no larger than 6.4 mm; head height must be <=2 mm. Blind flange pilots are 2.8 mm diameter, 2.85 mm deep. Nominal screw engagement is 2.825 mm. Printed thread strength and screw-head/cover clearance require a fit test. Do not substitute long screws that penetrate the winding area.

The cup accepts K&J D42DIA, a **diametrically magnetized** 6.35 x 3.175 mm magnet, in a 6.55 mm through pocket. Retain the magnet with suitable adhesive, flush with the cup face. Adhesive must not protrude into the encoder gap. The cup itself is screw retained. Spacer thickness is mandatory for M3 x 6; without it the screw can protrude through the flange. M3 x 5 without spacers gives the same nominal engagement, if available. Nominal magnet-face to AS5600-chip-face gap is 1.5 mm; check magnet centering and measured signal health across a full rotation before trusting counts.

Grove AS5600 101020692 is mounted using three M2 x 5 screws in printed bosses. Mount-hole locations follow the manufacturer's Eagle board drawing; the reference PCB envelope is conservatively 41 x 24 x 1.6 mm. Hardware revision, chip projection, screw heads, connector and cable bends still require physical confirmation. Do not drill based on an arbitrary board 'volume'. A different board needs hole-center spacing, hole diameters, PCB thickness, chip center relative to holes, chip-face height and connector projection.

Motor packaging remains 42.3 x 42.3 x 38 mm, 31 mm mounting pitch, 22 mm locating boss, 5 mm shaft and 24 mm shaft projection. These are inherited project dimensions, not newly measured claims. Encoder firmware compares measured spool rotation with commanded motor motion. It does not detect line slipping on the drum or compensate multilayer drum diameter.

## Metal outlet and homing collar

Selected supplier: Ronstan US, **RF8090-05 RopeGlide ring**, $17.07 each / $68.28 for four before tax and shipping.
https://www.ronstan.com/us/ropeglide-ring15mm-x-5mm-x-7mmblack-1.html
Metric manufacturer drawing: https://www.ronstan.com/au/ropeglide-ring15mm-x-5mm-x-7mmblack-1.html

The hard-anodized aluminium ring has 5 mm bore, 15 mm outside diameter and 7.5 mm axial width; mass 1.5 g. Its rounded rope surfaces support cable deflection in any azimuth without a pulley axle restricting the plane. This is a low-friction fixed guide, not a friction-free bearing. Price is higher than generic eyelets, but the supplier specifies rope use and publishes dimensions. Thin Dyneema wear and friction at the intended loads and angles must be tested. The ring's published load rating does not rate our printed carrier.

The cartridge now captures the ring between an integral front lip and a removable two-screw rear plate. The pocket is 15.3 mm diameter. The CAD ring is a conservative dimensional envelope, not the exact manufacturer's flared/grooved CAD. Confirm that the real ring seats without rocking; do not print a plastic substitute as the working outlet. Backplate requires two M3 screws per station; confirm length against assembled pilot depth and head clearance before tightening.

A stationary ring carries cable load; the separate sliding collar actuates the stationary KW12-3 roller switch. The collar bore is 18.6 mm; flat-faced printed stopper is 24 mm diameter x 8 mm. The enlarged bore clears the ring neck during the 2 mm stroke. Switch body assumes the user's 20 x 10.5 x 6.5 mm dimensions. Lever, roller, operating force and overtravel are schematic; adjust and hand-test the switch before powered homing. This is not an exact validated switch drawing.

**Springs are only button return springs.** Two per mount return the sliding collar when the bead moves away. They do not suspend the claw or set cable tension. Packaging assumes spring OD <=7.4 mm, ID >=6.4 mm, installed length 7 mm at rest / 5 mm pressed, solid height below 5 mm and a free length above 7 mm. Eight are needed for four stations. Exact spring SKU/rate remains open until sliding friction and switch force are measured; choosing a rate without those would be false precision. Printed stop sleeves provide the travel stop; do not use spring coil bind as the stop.

## Camera on the claw

**Feasible and recommended for a bench evaluation**, not a drop-in replacement for fixed-camera calibration. Selected candidate: Seeed XIAO ESP32-S3 Sense, SKU113991115, $13.99.
https://www.seeedstudio.com/XIAO-ESP32S3-Sense-p-5639.html
https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/
https://wiki.seeedstudio.com/xiao_esp32s3_camera_usage/

It combines ESP32-S3, camera, Wi-Fi, 8 MB PSRAM and 8 MB flash. Manufacturer assembled envelope is 21 x 17.8 x 15 mm. It can eventually replace the existing clamp ESP32, controlling the servo and tilt sensor and sending JPEG images to the existing computer for recognition. The purchased USB webcam cannot simply plug into the original ESP32's USB programming connector. Keep it for bench comparison while evaluating the replacement.

Prototype firmware: firmware/effector_camera_s3. Compile for XIAO_ESP32S3 with OPI PSRAM enabled. Browser / provides diagnostic live JPEG refresh; /capture sends JPEG; existing /grip, /release and tilt endpoints remain. Servo GPIO1, tilt SDA5/SCL6. Servo PWM is restricted to timer0; camera clock uses timer3/channel7. Compile success does not verify concurrent camera/servo operation, thermal behavior, latency or power stability. Images are explicitly marked diagnostic-unlocalized. Capture milliseconds are approximate device timing, not synchronized exposure timestamps. No host autonomous camera substitution is implemented.

Power from the 2S battery through a clean regulated **5 V logic branch** (design for at least 1 A available). Manufacturer camera workloads report varying peaks, including roughly 0.65 A. Measure the actual combined camera/IMU current and regulator heating; do not infer battery runtime from one typical figure. Keep the servo on its separate 5 V high-current regulator; share ground. Never connect a 2S battery, up to 8.4 V, to this board's 3.7 V battery input. Use an external 2S balance charger. Provide strain relief, accessible switch/fuse and decoupling near the logic board. Run camera and full loaded servo simultaneously to check brownouts before hanging the assembly.

A rigid downward-looking camera with a clear view of the grasp area is the starting choice. Board size fits the old tray envelope, but that does **not** establish optical clearance: the lens needs a window or external pod, jaws and cloth must not block it, and field of view must be measured before finalizing its mounting angle. Final camera pod CAD is deliberately not frozen before this optical test.

Required software work before removing the ceiling camera:
1. Calibrate lens intrinsics, distortion and rigid camera-to-claw transform.
2. Establish camera pose for each image. Encoder angles plus roll/pitch are insufficient: cable radius errors remain and yaw is unknown. Use known floor/hamper fiducials (AprilTags/ArUco) and calibrated room geometry; reject images with uncertain pose.
3. Map detections onto a known floor plane; use multiple high scan positions to cover the room. A single low camera view cannot see the whole room or through furniture. Four cables do not provide arbitrary six-degree-of-freedom orientation.
4. Use small, slow final approach movements and image feedback; stop to capture sharp images. Never reuse the fixed-camera pixel-to-room homography.
5. Verify pickup by tracking cloth relative to scene geometry during the partial test move. Mere whole-image motion proves only that the camera moved. If cloth is occluded, verification is uncertain and pickup must not be accepted.
6. Verify delivery by observing the item in the hamper after release and retreat. If no confirming view is available, retain an unverified status; never increment delivered count.

Camera adds a cheaper compact viewpoint, but also moving-pose estimation, scan coverage, occlusion and Wi-Fi latency requirements. It has no intrinsic depth measurement. Fixed workspace/obstacle geometry remains necessary for collision planning. No promise of horizontal grasp orientation is justified by the current point-effector planner.

## Release and measurements

Print one fit coupon, spool/cup and outlet cartridge first. PETG for structural parts; TPU95A for clamp pads. Measure printed fits and tune hole compensation before printing all four. No printer make/bed/material shrinkage was supplied, so a universal production fit is not certified. Check slicer supports, screw access, cable bends and lid removal with real hardware. Nominal CAD collision checks do not verify stiffness, spring force or braid wear.

Needed from user: assembled servo horn diameter/thickness and shaft-to-horn underside height, horn center-screw head clearance; actual ESP32 length/width/maximum height including headers and USB plug if retaining that board; battery length/width/height plus lead exit and connector. Supplier drawings cover the selected encoder; send revision/measurements only if the received board differs. Confirm original motor D-flat assumption only if the printed spool does not match. Do not provide a generic 'volume' measurement.

Use ORDER_STATUS_V2.csv as the consolidated purchasing worksheet. Historical ordered flags are separated from confirmed receipt. Unqualified springs, cable attachment rings, inserts and connector variants remain blockers for final procurement/production, even though nominal spaces exist in CAD.

## User-selected direction: scan, then pick, from the claw

Prefer the claw camera as the intended primary viewpoint. The ceiling camera remains a useful bench reference during validation, not a required final installation. Phone/app commands should select a named floor zone and start/pause/stop a job on the existing computer. Store zone polygons, validated scan waypoints and the hamper's room coordinate. Scan from a high feasible plane below the anchors, stitch detections into a room-coordinate target list, then approach/verify/pick/deliver. The highest possible position is not necessarily feasible: nearly horizontal cables demand large tension, so scan-height selection belongs to the validated workspace model.

The preferred image transport is continuous JPEG/MJPEG over local Wi-Fi, supported by the camera platform. It avoids a separate cloud round trip for each photo. Run cloth detection/tracking on the computer; the ESP32 handles capture, transmission, servo and tilt. Forward a preview from the computer to the phone so multiple viewers do not require multiple camera uplinks. Current prototype uses repeated /capture requests, not a continuous MJPEG endpoint. A future MJPEG server must run independently from the command server and tilt sampling; an infinite stream handler inside the existing synchronous WebServer would block grip/release requests.

For smooth motion, the local motor controller executes acceleration-limited segments independently of inference. A separate vision loop always processes the newest image and discards queued old frames. Plan long travel from the mapped targets and room obstacles, then make small visual corrections near the item. Stop briefly when sharp images or uncertain pose require it. The robot must not treat a late image as a current pose, or follow every noisy detection with a new abrupt motor command. Loss of fresh pose/vision near the floor should pause motion.

Initial engineering targets, not measured performance: 640x480 JPEG at5–10 useful frames/sec and end-to-end image age around100–250ms on local Wi-Fi. Benchmark with the actual lens, lighting, computer, radio coverage and loaded servo. A smooth preview alone does not prove timely detection. If these goals fail, reduce resolution/quality, improve lighting/network, optimize the local detector, or select stronger camera hardware before promising fluid autonomous pickup.

Compared with a ceiling camera, the claw camera offers close-up grasp views, scans from several positions and removes a separate mounted camera. It costs extra versus the already purchased USB webcam, consumes claw battery power, moves with cable sway, can be blocked by cloth/jaws and needs image-specific camera pose. The fixed ceiling viewpoint is simpler for persistent room mapping, target coordinates and observing a payload independently of the moving robot, but can miss small details and hidden items. For this project, the user's scan-then-pick workflow makes the claw camera a reasonable primary design, conditional on pose and pickup/delivery verification passing bench tests.

A known hamper coordinate is sufficient for initial routing. The camera should confirm that the destination area is clear and verify the deposited cloth; it need not continuously recognize or relocate the hamper. Future actions can share scan/map/move/inspect primitives, but every new manipulation action needs its own gripper and success checks. No general-purpose manipulation capability is implied by adding video.
