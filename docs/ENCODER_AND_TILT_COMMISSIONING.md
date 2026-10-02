# Four-winch encoder and clamp tilt bench build — 2026-10-01

This revision adds real feedback code and specific board packaging. It is a detached bench prototype. No motor, magnet, camera, assembled housing, radio timing, or suspended-load validation has been performed here. Four spaced anchors remain in the clamp CAD. The live planner still models a point effector, so encoders and tilt sensing do not make its suspended four-anchor pose model correct.

## What to buy

See `BOM_ENCODER_TILT.csv` for exact supplier links and counts. Boards cost $58.55: four $6.50 Grove AS5600 boards, four $4.90 XIAO ESP32-C3 nodes, one $12.95 Adafruit MPU6050. With four D42DIA magnets, four USB adapters/cables, one Grove cable five-pack and one QT cable, listed parts total $108.44 before shipping/tax, printing, foam, ties and existing fasteners. Reusing suitable USB supplies/cables saves $43.60. Prices checked 2026-10-01.

No IMU is recorded in the existing shopping list. A checked shopping-list row is a historical order flag, not proof of receipt; inspect the kit before assuming an item is on hand. None of these new parts has been purchased by this change. Existing ELEGOO ESP32 boards are larger; the selected small XIAO boards fit the new winch trays. The primary extended claw uses the selected XIAO ESP32-S3 Sense; old ESP32 boards remain spare/historical hardware.

Choose **K&J D42DIA**, not D42 or D42-N52. It is diametrically magnetized, 6.35 x 3.175 mm. Other candidate listings had conflicting magnetization/dimensions, so they were not selected. Magnetic field suitability must still be checked with the AS5600 status bits at assembly.

## Mechanical changes and assembly

Each universal winch base now has an integral encoder support for Seeed SKU101020692. Its manufacturer Eagle board layout is nominal40x20, with sensor10mm off center on the underside; packaging reserves41x24mm for edge protrusions. Board long dimension is vertical in the housing. Chip center aligns with spool axisY30/Z33. PCB occupiesX43.175..44.775, Z22.5..63.5; chip faceX41.175. Board underside faces the spool. Fasten the PCB to its three designed bosses with three M2×5 screws. No extra PCB spacer is included in the1.5mm gap calculation. If insulation or a different board needs a spacer, revise the sensor gap and screw engagement before assembly. Do not substitute a20x20generic AS5600 board without changing the CAD.

The magnet cup fits the unused outer spool flange with nominal0.2mm radial clearance. Its bore is6.55mm and disk3.175mm thick. Retain the cup with three M3×5 button-head screws (head height≤1.7mm), without spacers; glue only the magnet into its through-pocket after checking runout and field status; keep adhesive out of the line winding and shaft. Magnet faceX39.675 leaves1.5mm nominal gap to the chip. Actual chip package, magnet tolerance, print shrinkage and adhesive thickness require measurement. The cup is not a validated press-fit or load-bearing spool attachment. Magnet rotates with the spool, never with the stationary carrier.

A removable26x22mm XIAO tray sits above the motor atX-22/Y61. It has two M3 clearance mounting holes atX-37/-7,Y61; use two M3×12 button screws (headheight≤1.7mm), ordinary2.4mm nuts and0.5mm rear washers per station; no front washers near the USB connector. Foam and ties retain the21x17.8mm node. The USB end faces-X; the cover has a side cable opening. Reserve15x10x8mm plug space. Measure the actual cable plug before closing the cover. Solder low-profile leads; tall upright headers are not included in the six-mm board envelope. Route the included antenna/coax through the upper wiring notch and attach the antenna outside the plastic cover, clear of the metal motor and cable motion. No metal antenna bracket is required. Strain-relieve the cable at the housing.

The clamp regulator holder has a28x24 shelf atZ28..30 for Adafruit3886's26x17.8x4.6 board. Place it atX46/Y0,Z31..35.6 on insulating foam, component side up, board axes aligned with the clamp. Retain with nonconductive ties through shelf slots, avoiding connectors/components; solder no tall headers under this packaging. Lay the QT cable along the shelf edge into the electronics bay with slack for unplugging before removing the holder. Shelf, wiring and ties must not transmit servo vibration or twist the board. Board mount is fixed relative to the deck, not the lid.

Print `cad/exports/winch_bench/print_oriented/` parts; it includes the new `encoder_node_holder.stl`. Hardware reference STEP envelopes are not printable substitutes. First print the fit coupon, magnet cup and node holder; measure actual parts. Print the full encoder-equipped base only after those checks. Existing homing collar, stationary KW12 switch and metal eyelet remain part of this revision. Use MOUNT_PRINT_RELEASE_20261002.md for the current winch hardware and print sequence; actual springs, guides and switch travel remain physical fit gates.

## Wiring

One AS5600 and one XIAO per winch avoid fixed-address conflicts and room-length I2C wires. Keep each I2C harness under150mm, away from motor leads. Configure all nodes to join the same2.4GHz LAN and send to the Python computer's reserved IPv4 address, UDP8765. Ensure the host firewall permits that port. Local sampling200Hz; telemetry and host-to-Uno updates50Hz. USB power is separate from12V motor power.

| Endpoint | Connect to |
|---|---|
| XIAO3V3 | Grove VCC/red |
| XIAOGND | Grove GND/black |
| XIAOD4/GPIO6 | Grove SDA/white |
| XIAOD5/GPIO7 | Grove SCL/yellow |
| XIAOUSB-C | Regulated USB supply through A-to-C cable |
| Clamp ESP32 GPIO21 | MPU6050 SDA; QTblue |
| Clamp ESP32 GPIO22 | MPU6050 SCL; QTyellow |
| Clamp ESP32 3V3 | MPU6050 VIN; QTred |
| Clamp ESP32 GND | MPU6050 GND; QTblack |

Verify silkscreen/pin names rather than relying only on colors. Set AS5600 switch to the I2C/SDA position per Seeed guide; do not program OTP. Sensor address0x36; IMU address0x68 with AD0low/default. Do not connect12V to either board. XIAO power viaUSB avoids external5V-pad backfeeding/diode requirements. USB supplies listed use US plugs. Room installation needs suitable power routing; the listed1m cables are for bench tests.

## Flash and commission, in order

1. With all cables/clamp detached and motor power off, assemble the cup, sensor and node. Hand-rotate each spool slowly several turns both ways. Nothing should rub. The field must remain valid around360degrees; confirm weak/strong/missing status causes a failure rather than trusting raw angle alone.
2. Flash `firmware/encoder_node/encoder_node.ino` to four XIAO ESP32-C3 boards. Set `AXIS` uniquely0/1/2/3, WiFi credentials and hostIP in each. Record UID from serial115200. Flash `firmware/roomcleaner_firmware` to the Uno using AccelStepper1.64/Servo1.3,200-step motors and all three A4988 microstep jumpers for1/16. Firmware ratio is3200microsteps/rev to4096encoder counts/rev. A4988 current setting, fourth-axis independent jumpers and NC switch wiring must be verified separately against the existing bench guide.
3. Run from repo root `python -m tools.commission_encoders` to observe all four node identities without commanding motion. Restart a node after any field/read/sample-tracking fault. Close this tool before opening SerialDriver; both use UDP8765.
4. Energize unloaded motors on the bench only. Run `python -m tools.commission_encoders --port /dev/ttyACM0 --detached` (use your actual port). The tool makes bounded100-microstep forward/back tests at100steps/s per axis, measures sign and checks approximate ratio and return error, then writes `encoder_calibration.json`. No manual guessed signs/IDs are accepted. Mark and verify a full revolution produces3200commanded steps and4096ticks before approving motor accuracy; the small jog is a first screen, not an accuracy calibration.
5. Power-cycle/reconnect and repeat the small test if anything changes. Calibration file must stay in the working directory or update `ENCODER_CALIBRATION_FILE`. Do not commit personal MAC IDs or WiFi passwords. New node epochs are accepted when opening a new session; a reboot inside a session latches a fault. Reconnect and rehome after faults.
6. Open SerialDriver only once all nodes are healthy. Use detached homing; `H DETACHED` is the only accepted homing command. Encoder feedback is required during seeking/backoff. Sequential homing of a freely suspended clamp is still prohibited. Enter the actual bead-trigger cable lengths in the existing homing calibration; they remain unmeasured placeholders. After each datum reset, the feedback baseline is rebased without zeroing the node's multi-turn counter.
7. Test short unloaded moves. In this revision max500microsteps/s (~9.8mm/s with a20mm core), home300, slow latch100. Choose slower speeds for approach; higher travel speed waits for latency/radius/load tests. Threshold48microsteps sustained100ms and final48microsteps is provisional. It is ~0.94mm of drum surface travel, not true payload accuracy. Do not loosen it merely to silence a fault; inspect timing and mechanics.
8. Flash `firmware/effector_esp32` onto the existing clamp ESP32 with ESP32Servo3.2.1. ServoGPIO13, IMUGPIO21/22. Place unloaded clamp stationary on a physically level surface with board+Zup. Request `http://roomcleaner-claw.local/calibrate?stationary=1`; this averages gyro bias for2seconds and rejects visibly moving samples. Recalibrate each boot; bias is not saved. Then inspect `/tilt`: roll/pitch near0, `valid:true`, `level:true` after500ms quiet. Physically tilt known5/10degree angles in both axes and compare measured values before accepting threshold.
9. `/grip` and WiFiGripper refuse pickup if unsettled, unhealthy or either angle exceeds5degrees. Firmware checks immediately before closing as well as the host check. Release is allowed to let go after a fault. This is a settled pickup gate; it does not continuously stop winch travel on tilt, does not implement active leveling, and does not measure absolute yaw. Acceleration can corrupt gravity-based tilt; use stationary readings. Four cables cannot independently command all six rigid-body DOFs or guarantee horizontal grasp throughout a room.

## Required physical fault tests before payload tests

On the detached bench, record commanded steps, encoder counts, switch state, stop latency and camera video. Unplug one encoder; block UDP; turn one node off/on during a move; deliberately shift/loosen its magnet with motor off; simulate host exit/disconnected serial; verify no new move is accepted and rehoming is required. Simulate tracking error at low current/no payload using a controlled test fixture, not fingers on the energized spool. A healthy frame must not recover a latched tracking fault mid-run.

Host rejects missing samples older150ms, nonincreasing sequence IDs, changed node boot IDs and unhealthy field/tracking status. Uno independently rejects stream age over250ms, including while idle. Stops halt new pulses and retain driver holding torque; they do not provide a mechanical brake. Test real radio/serial latency against these limits. Firmware DONE is sent only after the final rotation check.

Keep all electrical commissioning detached. Next, measure winding radius under tension and verify cable attachment/knot/stopper loads; then develop the finite-anchor pose/tension model and validate the permitted suspension workspace with small supported loads. The current point model is not cleared for room-wide orientation claims.

## What feedback does and does not prove

AS5600 is single-turn absolute; each continuously sampling local node unwraps it into multi-turn counts. A power loss loses that tracking epoch. Never reconstruct turns from the first raw angle after reboot. Spool-mounted magnet catches lost steps and motor-to-spool slip if actual spool rotation fails to match commands. It cannot prove cable traction, winding diameter, cable stretch, attachment security, payload position or successful grip. Existing camera pickup-motion confirmation/retry and delivery verification remain necessary; do not count an item delivered based on encoder DONE.

This adds error detection and movement inhibition, not a PID servo that automatically adds steps. Automatic motor corrections near a snag could worsen the snag; corrections require measured dynamics, load/pose constraints and physical tests. Pickup retries still depend on camera observations, not encoder disagreement alone.

Primary references: Seeed AS5600 wiki and Eagle files, Seeed XIAO ESP32-C3 getting-started/pinout; Adafruit3886 product/MPU6050 guide; K&J D42DIA specification. Exact links are in the BOM and supplier pages. Geometry audits check nominal solid collisions, not wiring flex, electromagnetic field quality, printed tolerances or strength.
