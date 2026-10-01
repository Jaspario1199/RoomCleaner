> Primary build changed to [EXTENDED_CLAW_V3_BUILD.md](EXTENDED_CLAW_V3_BUILD.md):printed150mm extension, lower servo/clamp, upper electronics,28degree camera pose. Compact V2 remains a historical baseline.

# Claw camera assembly V2 — bench prototype

Camera: Seeed XIAO ESP32-S3 Sense113991115, without soldered pin headers. This replaces the old claw ESP32 and its tray; the battery, servo regulator, logic regulator, tilt sensor, clamp and four cable anchors remain. No order or receipt is confirmed by this document.

## Defined geometry and retention

The camera sits in an external front pod, pitched40 degrees toward the grasp area. It bolts to the deck atX=+/-18,Y=70 using two M3 bolts. The main enclosure lid stays independent. Local camera coordinates transform byX rotation-40 degrees and translation(0,96,22)mm. Published21x17.8x15mm is not the full connector envelope: the manufacturer STEP spans24.363x17.78x13.96mm in normalized length/width/height. The housing accounts for USB and flex protrusions.

Pocket:18.4mm width x25.0mm length, length center offset+1.4mm to clear the asymmetric connector/flex. Outer shell22.4x29mm. Shell front/rear and keeper geometry are parameterized in cad/clamp_camera_v2.py. The camera lens stays uncovered; the retainers do not press on the lens or camera daughterboard. Two side rails overlap the motherboard perimeter and are removable with M3x8 button screws into2.8mm printed pilots. Head envelope assumed diameter<=6mm,height<=2mm. Validate printed pilot engagement and screw seating before tightening.

Front keeper lip:localW12.1..12.5mm; motherboard frontW12.71mm. Rear support faceW14.4mm; motherboard backW13.96mm. Use small nonconductive silicone pads, initially0.3mm front and0.5mm rear, at verified bare motherboard edge locations only. The nominal combined gap is0.65mm, so0.8mm pads compress about0.15mm. Pads are consumable fit adjustments, not certified preload. Confirm actual solder/component locations; no pressure on chips, lens, connectors or flexible ribbon. Tighten just enough to prevent board movement. If the supplier revision differs, change pad/keeper parameters and rerun checks.

The camera cradle/bracket is one connected printed part. Outer gussets preserve support around the keeper-access relief. Base is44mm wide, deck attachmentY70, side support rails extend toY113. Enlarged camera pod and USB service space extend beyond the old deck footprint: use the assembly bounding boxes in geometry.json for collision planning. Do not continue treating the claw as a zero-size point around furniture.

## Print and hardware list

Validation:5808 nominal assembly clearance checks and nine open-grasp sight lines passed; valid solids and STEP round trips passed. This is a bench release, not physical fit certification.

Print PETG:camera_cradle.stl,camera_keeper_left.stl,camera_keeper_right.stl and the revised deck.stl. Reuse existing clamp rails/jaws/pinion, battery tray, power mounts, cover and TPU pads. The old ESP32 tray is removed. Exported cradle is base-down; the angled pod requires slicer support review. Keep support scars away from board seats and optical opening. Print keepers flat in their provided orientation. No physical printer/shrinkage fit is certified.

| New hardware | Quantity | Interface |
|---|---:|---|
| XIAO ESP32-S3 Sense |1| Camera/controller; use unsoldered-header version |
| M3x16 button screws |2| Pod bracket to deck |
| M3 nyloc nuts |2| Under deck; nominal4mm height |
| M3 washers |2| Under deck; nominal0.5mm |
| M3x8 button screws |2| Removable board keepers; printed pilots |
| Insulating silicone pad stock |Small strips|0.3mm front /0.5mm rear starting fit |
| Small nonconductive cable ties |4| Harness/antenna strain relief |

M3x12 may replace the deck bolts only with ordinary2.4mm hex nuts and verified engagement; it is too short for the modeled washer/nyloc stack. Keeper bolt engagement is about5.95mm. No M2 is required by the new camera mount. Existing encoder/horn/regulator M2 interfaces elsewhere are unchanged.

## Wiring, access and assembly

1. Print and dry-fit one pod with the received board. Verify PCB revision, lens/flex/USB protrusions and board-edge seating against the included manufacturer reference. Secure the PCB using insulating edge pads and keepers; never squeeze the camera stack as a whole.
2. Use two M3x16/washer/nyloc sets to bolt the pod onto the revised deck. The bracket includes a relief for the lid's front tab and its vertical removal path. Check every fastener head and underside thread with jaws open and closed.
3. Retain the original external2S balance charger. Supply regulated5V/GND from the clean logic buck to the camera board; do not connect2S raw voltage to its3.7V BAT terminals. Servo stays on the separate5V high-current branch. Common ground. Camera/IMU branch provision at least1A available; verify supply ripple and heat with continuous streaming and loaded servo operation.
4. Low-profile soldered wires avoid pin-header height. Firmware camera variant uses servoGPIO1, MPU6050SDA5/SCL6. Confirm pin labels with Seeed documentation before soldering. Feed the harness through the pod's rear/bottom exit and the existing lid access opening; retain at the old deck tie slotsX+/-20,Y38. Tie the bundle to the bracket slots atX+/-10,Y71.5; provide a service loop so lid removal never pulls the camera connector.
5. Connect the supplied Wi-Fi antenna and retain its cable with strain relief. Place the antenna patch on plastic, away from conductive battery/servo parts and without covering the rear vents. Final patch/cable length was not supplied and is not an exact CAD fit claim. Verify radio coverage throughout the room.
6. USB opening and an18mm long plug access volume are modeled. Actual plug dimensions and cable bend radius remain a purchase-specific check. Disconnect USB before moving the claw. Routine power can use soldered5V/GND leads.
7. Power on at the bench, check tilt/servo commands and images. Calibrate lens intrinsics and camera-to-claw transform. Mark camera module reassembly as requiring recalibration. Do not claim autonomous scanning from this mechanical release alone.

## Optical and validation limits

The nominal optical axis points toward the gap between open jaws; ray checks target nine points across30x24mm atZ=-96.5mm. These only test mechanical sight lines, not actual field of view, focus or detection quality. Cloth may block the lens or obscure confirmation after gripping. Closed-jaw visibility and hamper release verification must be tested with real cloth. The40-degree mount means high scanning images look diagonally across the room; scan waypoints must account for that offset and uncertain pose.

Before printing all parts: inspect the lens image at floor approach height, confirm the jaws do not hide required grasp/verification features, check lighting, servo brownouts, frame latency, enclosure temperature, wire bends and camera retention under gentle vibration. The pod adds forward mass: weigh the completed claw, update its center-of-mass/tension assumptions and recheck settled tilt before room travel. Physical verification remains pending.

Reproduce:python -m tools.prepare_camera_model;python -m cad.clamp_camera_v2;python -m verification.check_clamp_camera;python -m verification.check_camera_sightlines. Files under cad/exports/clamp_camera_v2 are the new assembly; do not mix the old deck/ESP32 tray into it.
