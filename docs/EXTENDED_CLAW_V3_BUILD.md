# Primary extended claw V3 — printed bench design

This is the selected first build, replacing the compact V2 baseline. Upper battery, ESP32-S3 Sense camera/controller, tilt sensor, clean logic regulator and servo regulator; lower MG996R servo and parallel-jaw clamp. Four cables attach to the upper housing. No intentional cable-driven rotation or angled grasping. Tilt sensing remains a settled pickup gate, not active leveling.

## Mechanical definition

Upper deck bottomZ0, lower carrier bottomZ-150mm. Pad bottomZ-246.5mm. Upper cable planeZ21.5mm:nominal floor reach268mm. Camera pose is fixed28degrees toward the grasp area, origin(0,136,22)mm. Its longer front bracket keeps the lower carrier/rails out of the main sight lines; a40x14mm forward notch in the lower carrier clears the corner rays. Camera remains attached to the upper electronics housing.

Two removable hollow PETG uprights atX+/-43,Y0 connect the plates. Outer section14x18mm, inner8x12mm:3mm nominal walls. Upper and lower flanges24x82x6mm. Left lower relief clears the servo ear/screw region. Right upright routes the servo's three wires:lower side exit, vertical channel and upper elbow to deck openingX43,Y34. This is a printed fork frame, not a central pole through the servo. Its split arrangement keeps the existing servo/gear mechanism intact and resists twisting better than an unsecured round connector.

The lower carrier is140x90x4mm with servo ear slots, rail holes atX+/-53,Y+/-35 and upright holes atX+/-43,Y+/-36. Upper upright holesX+/-49,Y+/-24 clear battery and regulator mounts. Upper deck preserves the four cable clevises and removable enclosure lid; the old servo opening is filled. The compact ESP32 tray is removed because the camera/controller is in the upper pod.

Later aluminium uprights can replace these printed parts after matching the end-flange pattern and keeping the wiring/servo clearances. No aluminium stock or joint design is frozen in this release. Changing extension length requires regenerated CAD and camera calibration; it is not a telescoping mechanism.

## Parts and fastening

Print PETG:upper deck(deck.stl),lower_carrier,upright_left,upright_right,camera_cradle,two camera_keepers,battery_tray,logic_mount,regulator_mount,cover,rails,jaws,pinion. Print the two yellow pads in TPU95A. Reference hardware/electronics/cable rings are not working printed substitutes.

| Interface | Required hardware |
|---|---|
| Uprights to upper/lower plates |8 M3x20 button bolts,8 M3 nyloc nuts,8 M3 washers |
| Camera bracket to upper deck |2 M3x16,2 M3 nyloc nuts,2 washers |
| Camera PCB keepers |2 M3x8 into printed2.8mm pilots |
| Lower servo/rails/horn |Existing hardware from clamp BOM; horn dimensions still need physical confirmation |
| Servo wiring |3-conductor extension,20–22AWG power conductors; matching3-pin servo connectors; strain relief |

Extension head envelopes<=6mm diameter,<=2mm height; nut envelope6.4mm across corners x4mm high; washer0.5mm. Upper bolts have10mm plate/flange grip; lower likewise. With washer and4mm nyloc, M3x20 leaves about5.5mm beyond the nut; verify the actual stack and choose the shortest length that fully engages the nylon. Hardware shanks/threads and exact purchased fasteners still need physical fit inspection.

Upper camera retention uses the manufacturer STEP and the edge-pad arrangement from CLAW_CAMERA_V2_BUILD.md, with the new28degree pose. Neither the keeper nor foam presses on the lens/daughterboard. Use low-profile soldered leads, not unmodeled tall pin headers. Manufacturer revision must match the received board.

## Print and wire route

Print uprights in the supplied side orientation, about150x82mm on the bed and24mm high. The slimmer midsection sits5mm above the flange faces, so supports beneath it are required; inspect internal-channel bridging and remove/deburr support remnants before threading wire. Avoid printing tall upright columns as the default. PETG orientation, shell count, infill and threaded fit require the actual printer profile; no certified load rating is asserted. Print one upright/connector fit first.

Both regulators stay above. Battery2S feeds separately regulated5V logic/camera and5V high-current servo branches. Keep common ground. Run servo power, ground and GPIO1 signal down the right upright. Choose extension length after routing:350mm is a starting lead allowance, not an exact connector SKU. Check conductor voltage drop, connector pin order and loaded servo current. The clean logic branch must not share the servo's high-current return path before their designated common-ground point.

Protect every channel edge, tie the lead at the upper deck's wire opening and at lower carrier slotsX22/31,Y0. Leave a small service loop near the servo; no lead can enter the pinion/racks at any pose. Select connectors from the actual MG996R lead; do not assume all3-pin housings have identical geometry. For first bench power-up, move jaws by hand and inspect the entire travel before enabling torque.

Camera USB/antenna access, upper lid service and optical calibration follow the prior camera build guide, but use the new V3 geometry and extrinsic pose. The front camera arm enlarges the collision footprint; geometry.json supplies complete part bounds. Empty-space sight-line checks do not guarantee view with a large garment hanging from the jaws.

## Control and commissioning

Nominal EFFECTOR_REACH is now0.268m and GRAB_Z0.288m. Normal minimum cable-plane height is0.418m, allowing150mm nominal pad clearance. These refer to the upper cable plane, not the lower servo carrier. Measure actual assembled floor reach and update before powered descent. Camera localizer/zone scans and continuous stream are still pending; extending the mechanics does not implement them.

Use gentle acceleration and allow images to settle near pickup. A long assembly can swing; no promise of perfectly level motion or unrestricted equilibrium is made. Weigh the assembly, test loaded strut flex/joints and update mass/center-of-mass/tension assumptions before suspension. The point-effector planner does not yet check the full extended body against furniture; room operation requires that collision-envelope integration and moving-camera pose verification. Bench prints and clearance checks are not authorization to treat the room trajectory as validated.

Reproduce:python -m tools.prepare_camera_model;python -m cad.clamp_extended_v3;python -m verification.check_extended_claw;python -m verification.check_extended_sightlines. Use cad/exports/clamp_extended_v3 for the primary build. Do not combine the previous compact deck/camera angle with this version.
