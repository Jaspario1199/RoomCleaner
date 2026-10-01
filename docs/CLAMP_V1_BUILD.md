# RoomCleaner parallel clamp V1

This supersedes the five-finger central effector for the first build. The winches and camera-verified pickup/delivery flow remain separate. This is a CAD-checked assembly prototype, not a demonstrated laundry pickup mechanism. Thin fabric lying completely flat may still require a scoop or revised TPU pad.

## Geometry and mechanism

Coordinates are millimeters. Deck underside is Z=0; servo output axis is X=Y=0. Servo body points upward; horn and pinion are underneath. Positive servo motion from 20 to 140 degrees turns the pinion clockwise viewed from above. Two opposing racks translate equal distances, keeping pad bottoms at constant height. Install the horn at 20 degrees with racks in the exported open pose; verify actual servo direction before meshing.

| Interface | Dimension / location |
|---|---|
| Main deck | 160 × 150 × 4; rounded corners R10 |
| Removable cover | 142 × 130 × 50; 2 mm wall/roof; Z4–54 |
| Servo body envelope | 40.7 × 19.7 × 37; center X=-10.5, Y=0; Z4–41 |
| Servo pocket | 43 × 22; four slotted M3 ear holes; nominal X=-34.5/+13.5, Y=±5 |
| Pinion | Module 1.5, 24 teeth, 20° pressure angle; pitch Ø36, outer Ø39; 7 thick; Z=-15 to -8 |
| Pinion/horn connection | Central Ø6.5 screw access; three Ø2.3 holes on radius 7 at 0/120/240° |
| Racks | 116 × 10 × 7 bodies; matching teeth; track centers Y=±24.875 |
| Travel per jaw | 37.699 for a 120° servo turn |
| Pad gap | 77.4 open; 2.002 closed, before pad compression |
| Jaw plates | 4 × 44 × 70; replaceable pads on inward faces |
| TPU pads | 5 × 40 × 36; rounded edges R0.7; bottom Z=-96.5 |
| Pad screw pattern | Four M3, Y=±14, Z=-88/-68; axis X |
| ESP32 tray cavity | 68 × 36 × 20 available envelope; center Y=38; foam below board |
| Battery tray cavity | 78 × 39 × 18; center Y=-36; foam below cell |
| Servo regulator | Pololu D24V50F5; 17.8 × 20.3 × 8.8; center X46; M2 holes offset ±6.731, ±8.001 |
| Logic regulator | Foam/tie mount at X=-48; reference envelope 24 × 20 × 8 |
| Cable clevises | X=±69, Y=±64; M3 pin axis Y at Z13 |
| Cable rings | Welded stainless OD12/ID8, 2 mm section; nominal tie plane Z21.5 |
| Cable plane to pad bottom | 118 mm nominal; remeasure actual tied assembly |

Cable load path: cable tied to closed metal ring → M3 clevis bolt → two deck ears → deck beams. Electronics and cover carry no cable load. Use a tested braid knot appropriate to the actual line and ring, with retained tails; do not rely on glue or an untested knot. The rotating ring gives angular freedom but its true cable attachment point moves with load direction. Calibration must use the assembled geometry.

The pinion bolts to the supplied round plastic servo horn. The factory horn screw retains the horn on the servo spline. Do not print an assumed spline. Required horn: at least Ø20, about 2 mm thick, with clearance for the three M2 attachments. Drill its three holes using the printed pinion as a template before fitting. If the supplied horn differs, revise this interface first.

## Electronics

2S battery (8.4 V fully charged) → inline 5 A fuse → two regulated branches:

- Pololu D24V50F5, regulated 5 V → servo positive; servo negative → common ground.
- Existing MP1584EN adjusted and measured at 5 V → ESP32 board's documented 5 V/VIN input; common ground.
- ESP32 GPIO13 → servo signal. Never connect raw 2S or the old 6 V servo setting to the ESP32.

Place the small inline fuse on the dedicated shelf above the logic regulator, retained with ties; holder must fit within the modeled 33 × 18 × 14 mm envelope, Z24–38. The shelf is part of the screw-mounted logic-regulator holder; it needs no glue. No panel switch is assumed: the accessible battery power connector serves as the prototype disconnect. Charging is external with a suitable 2S balance charger and the battery removed. The two cover openings are general harness access, not precisely aligned USB sockets; remove the lid for programming. Keep wires above Z0 and away from the moving rack channels. Secure both trays to the deck using ties through aligned slots; use foam against the cell and do not squeeze the LiPo pouch.

The current ESP32 firmware uses GPIO13 and 20/140 degree release/grip commands. These are geometry limits, not measured position or force feedback. Establish pulse calibration unloaded. A smaller command angle can be used for a thicker object. A blocked servo can stall while commanded closed: measure holding current and temperature before prolonged operation; do not treat stall torque as continuous grip capability. Battery undervoltage shutdown is not implemented yet; monitor pack/cell voltages during bench tests and stop before the pack manufacturer's discharge limit.

## Print and assembly

1. Measure the actual servo shaft offset, ear-hole pattern, supplied horn, ESP32 including connectors, and battery. Reference cuboids are envelopes, not exact vendor models. The servo slots permit only about ±0.8 mm alignment adjustment. If dimensions exceed the listed envelopes or slots, change parameters before printing the complete deck.
2. Print one pinion and rail pair first. Use PETG for structural parts, pinion and racks; TPU 95A for pads. Suggested starting settings: 0.2 mm layers, five perimeters, 40% infill, reinforced/solid clevis regions. These are initial settings, not strength certification. Orient rack/jaw parts on a broad side with support under overhangs; orient rails with channel accessible; cover inverted/open side up; pad on broad flat face. Inspect and deburr sliding/gear faces. Actual printer clearance may require tuning.
3. Fit servo in deck, horn pointing downward. Fit factory horn and screw, then pinion with three M2 bolts/nuts. Ensure fasteners clear the servo body and deck. Pinion axial position must match Z=-15 to -8; stock horn stack height is a fit-check hold.
4. Fit racks and two rails. Set open rack/jaw positions as exported. Attach rails with four M3×30 bolts, washers and nuts. Move by hand through full travel before servo power. Retaining bridges keep racks seated; channel nominal running clearance is 0.3 mm per side and 0.3 mm below.
5. Attach each TPU pad with four M3×16 bolts, washers and nuts. Use M3 button heads no larger than Ø6.0 × 2.0 mm in the modeled Ø6.4 × 2.6 mm counterbores. Seat heads below the TPU contact face; do not crush the pad. Standard tall socket heads do not fit this recess.
6. Install foam, board, battery, regulators, fuse, and tied wiring. Fit cover with four M3×8 bolts into appropriately sized M3 heat-set inserts. Pilot Ø4 is provisional: change to the insert manufacturer's recommended hole size.
7. Fit four rings using M3×20 bolts, washers and nyloc nuts. Confirm rings articulate without pinching. Proof-test the complete deck/clevis/ring/knot load path on a bench before suspension; existing control tension limit is 40 N per cable, so a provisional proof target is 120 N per anchor without permanent deformation. This does not establish fatigue life.
8. Bench-test unloaded opening/closing, then a folded cloth, then representative flat laundry. Measure actual gap, servo current, temperature, slippage and assembly mass. Confirm electrical stability while the servo reverses under load. Check both ESP32 logic power and servo rail.
9. Suspend only after load-path testing. Existing software pickup height gives 20 mm nominal pad clearance. Reduce it in small measured steps for near-ground pickup; a 3 mm target corresponds to cable-plane Z=121 mm, but do not use it until floor height and actual reach are calibrated. Camera must verify payload motion after a partial lift and delivery after release. A commanded closure alone proves neither.

## Latest bench audit

See `BENCH_PRINT_AUDIT.md` before suspended use. The point-mass planner does not currently account for the four separated clamp attachments. Adafruit3886 MPU6050 packaging26×17.8×4.6mm and a tied shelf sit above the servo regulator. Tilt telemetry and a calibrated settled pickup gate are implemented; active leveling and finite-anchor pose control are not. See ENCODER_AND_TILT_COMMISSIONING.md.

## Remaining release gates

Actual component fit and horn stack; print sliding clearance; measured grip force/current/thermal behavior; low-battery handling; braid knot and clevis proof test; real assembly mass/center of gravity; cable attachment calibration; near-floor pickup test; camera calibration. Encoder boards/nodes/magnets are selected in BOM_ENCODER_TILT.csv; winch eyelet/spring physical checks remain outstanding. Encoder mounts are in cad/winch_bench.py.

See `CLAMP_ASSEMBLY_REVIEW.md` for the requirements-first review and complete-assembly checks. Generate STEP/STL: `python -m cad.clamp_v1`. Run sampled rigid clearance checks: `python -m verification.check_clamp_v1`. STEP reference parts represent purchased components and foam, and should not be printed. Metal rings should not be printed. Open and closed assemblies include reference envelopes. Sampled collision tests are not a continuous motion or physical validation.
