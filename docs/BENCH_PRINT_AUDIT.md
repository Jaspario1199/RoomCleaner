> Latest spool/outlet/camera decisions and consolidated order status: [REVISION_V2_DECISIONS.md](REVISION_V2_DECISIONS.md) and [ORDER_STATUS_V2.csv](ORDER_STATUS_V2.csv). Earlier generic outlet, friction-fit magnet cup, servo power and fixed-camera assumptions below are superseded where they conflict.

> Feedback revision2026-10-01: [encoder/tilt commissioning](../docs/ENCODER_AND_TILT_COMMISSIONING.md) supersedes older optional/unimplemented encoder and tilt descriptions. Use current cad/winch_bench.py and cad/clamp_v1.py exports. Physical commissioning remains required.

# Bench print audit: winch first, clamp second

This is the active print guide. Use `cad/winch_bench.py`, not the old standalone winch_v2 or legacy corner_mount files. Changes were driven by full component-pair and cover-removal checks. These files are prepared for **one instrumented bench prototype**, not four installed stations or unattended room operation.

## Winch review and fixes

| Issue found | Revision / remaining limitation |
|---|---|
| Stationary switch plate embedded in structural tower | Tower face moved back 1 mm; plate seats against it |
| Switch shelf and schematic lever/roller intruded into cartridge | Cartridge relieved locally; keep the actual roller checked against this reference |
| Lower switch slot collided with guide tower | Corner relief added; use three switch-plate screws, omit lower-left slot |
| Original roof screws needed approximately 60 mm reach | Low internal screw seats; short M3×10 screws accessed through roof openings; posts moved to X=±51.5, Y=±66 |
| Cover could not slide past the homing collar | Full-depth outlet opening; removal checked with fixed mechanism |
| Spool flange touched motor bracket nominally | Spool positioned 0.5 mm forward for running clearance; measure actual shaft engagement |
| No encoder accommodation | Integral front-of-spool support, generic board envelope and separate magnetic cup; no rear shaft assumed |
| Encoder support initially disconnected in draft | Connected to base; valid single-solid export required |

Coordinates: wall is XY; +Y upward; +Z into room. Base 112×150×6 mm; cover overall extends to Z74.4. Motor face X=-2; shaft axis Y30/Z33; 38 mm motor body extends toward negative X. Motor pocket accepts the given 42.3 mm face, Ø22 boss and 31 mm screw pattern. Nominal shaft projection 24 mm; spool extends X4.5–36.5 and engages only 17.5 mm of shaft. Its outer section is cantilevered: inspect runout and bearing load during testing. This enclosure does **not** provide an outboard spool bearing. Do not force a hot press fit or rely on friction alone; use the existing D-flat/set-screw spool retention and inspect for slip.

Spool reference: Ø20 core, 26 mm winding length, Ø36 flanges, 3 mm flange thickness, total 32 mm. Existing spool may be reused only if it meets these dimensions. No level-wind is included. Line pile-up changes effective payout radius and may foul the flange; watch winding across the full usable travel. A polished fixed guide gives azimuth freedom; it is not a bearing. The ±55° analytical line cone concerns collar clearance only, not wear or housing/load approval at every cable angle.

The line passes through the fixed metal eyelet, then the moving annular collar. A Ø20×8 flat-faced stopper on the external line presses the Ø12-bore collar. Two 4 mm shoulder guides keep the collar aligned; two compression springs restore it. The collar fork pushes the stationary KW12 roller. Nominal collar stroke 2 mm, initial pad/roller gap 0.7 mm, schematic roller motion 1.3 mm. Actual switch travel and roller pivot are unmeasured. **The reference is not proof that a real KW12 will actuate or survive overtravel.** Verify electrical trip before the sleeve hard stop, leaving at least 0.5 mm mechanical margin as an initial bench acceptance target; change fork/shims if needed. The slotted plate adjusts lateral alignment, not arbitrary switch depth.

At oblique cable angles the stopper approaches off-axis and may side-load/jam the collar. Start with a straight detached cable; then test intended exit angles and repeated returns. Do not home the suspended assembly by trying to bring every bead against its station. Each detached winch is homed and then paid out to measured attachment lengths.

## Print sequence

1. **Fit coupon** (`fit_coupon.stl`): 2.8 mm M3 pilot, 3.4 mm M3 clearance, 4.3 mm shoulder clearance, 8.3 mm eyelet seat. Measure printed holes. Tune fit before printing the mechanism; nominal CAD clearance is not printer compensation.
2. **Cartridge bench fixture**, guide_carrier, homing_collar, switch_mount, homing_stopper: one each. Fixture replaces the large base for a manual button test. Attach it to a board through its three Ø4.5 holes. Fit real hardware, check free return and switch continuity; use the metal eyelet for line-motion tests.
The optional `eyelet_fit_dummy.stl` is a non-threaded plastic fit surrogate for manual alignment only; it does not substitute for the metal eyelet in line/load tests. No sleeves, eyelet surrogate or hardware references are load-approved printed replacements.

3. **One complete base and cover**: fit motor/spool, cartridge, switch and wiring. Print encoder_magnet_cup only if its flange fit and actual sensor/magnet are being tested. Do not print four stations yet.
4. Stop sleeves may be printed for geometry checks only; use metal Ø5.8 OD / Ø4.2 ID / 5 mm length for final mechanical stops.

PETG starting settings: 0.2 mm layers, 5–6 walls, 40–50% infill, reinforced bracket/cartridge regions. These are initial settings, not a load qualification. Base wall-facing flat surface on bed; support underside of encoder tie holes and horizontal bosses as needed. Cover front face on bed, support low internal screw shelves and inspect support removal. Cartridge broad plate face on bed; collar flat ring face on bed, supporting fork bridge; switch plate broad face on bed with shelf supported; stopper flat face on bed; magnet cup bore vertical/open side upward. Critical holes may need drilling/reaming. Print the fixture/collar first and check direction-dependent strength, finish and binding before loading.

## Hardware for ONE bench station

| Hardware | Qty | Interface / hold |
|---|---:|---|
| Existing NEMA17 and spool | 1 each | Given single-shaft dimensions; actual mounting threads/shaft fit must be measured |
| KW12-3 roller switch | 1 | Body 20×10.5×6.5; roller geometry/travel unmeasured |
| Polished metal eyelet + capture nut | 1 | Reference Ø8 body, Ø3 bore, Ø10 lip, 14.5 mm body; actual thread/supplier not selected |
| Shoulder guides | 2 | Ø4 shoulder, 12 mm shoulder length, M3×6 thread; actual head geometry must fit |
| Return springs | 2 | Reference OD7.4/ID6.4; installed length 7 mm at rest, 5 mm pressed; coil-bind height <5 mm and force must be selected/tested |
| Metal stop sleeves | 2 | OD5.8/ID4.2×5; deburred |
| Guide washers | 2 | ID ≥4.2, approximately OD7–8×1; check actual stack |
| Motor bolts | 4 | M3×10 + washers through 6 mm bracket; measure permissible motor thread engagement before tightening |
| Cartridge bolts | 2 | M3×25, washers and nuts; plate6 + tower12 + washers/nut |
| Switch plate screws | 3 | M3×12 into printed pilots; upper pair and lower-right; omit relieved lower-left |
| Cover screws | 4 | M3×10 low heads; direct printed pilots, heads on low shelves, screwdriver through roof holes |
| Switch ties | 2 | 2 mm wide; keep roller/lever unobstructed |
| Braid + stopper | 1 set | User's 120 lb eight-strand line; retain stopper with a tested knot seated in its pocket; no adhesive-only retention |
| Bench board/fasteners | 1 set | Existing scrap board and appropriate bolts; no wall installation needed |

Wall-mount screw heads are not modeled. The three stud holes have Ø11×3 mm counterbores; actual heads must seat without intruding into the motor/guide bracket. Driver access near the center/lower holes is narrow: dry-fit a slim long bit, and install the motor/cartridge after fixing the base if needed. Wall screw type, embedment and stud attachment remain installation choices, outside this detached bench release.

The winch houses motor, spool, switch, encoder and restrained leads. Uno/CNC shield/power supply stay in the base station, not inside each winch. Remove strain from switch terminals; use boots/heat shrink and tie motor/encoder leads above and away from spool. Rear notches are harness exits, not a validated connector model. Wire switch Common + NC to GND/limit input as documented in firmware; confirm HIGH on trip/disconnection. Do not use AC on these switches.

## Encoder accommodation and integration hold

The selected sensor is Seeed GroveAS5600 SKU101020692, with a41×21×1.6mm packaging envelope and sensor10mm off-center. Use the revised fixed support and K&J D42DIA6.35×3.175mm cup in cad/winch_bench.py. Chip faceX41.175 and magnet faceX39.675 give1.5mm nominal gap. The node tray fits XIAO ESP32-C3 and includes a USB exit. Exact positions, assembly and field checks are in ENCODER_AND_TILT_COMMISSIONING.md; older20×20/6×2generic packaging is superseded.


## Bench acceptance log

Record actual switch trigger/release strokes; return from every tested angle; spring coil-bind margin; sleeve/washer stacks; 20 slow manual stopper cycles with zero missed trips or binding; line wear under representative load; unloaded and modest-load winding/runout; flange retention; motor bracket temperature; encoder gap/field/readings if installed. Use low motor current and a detached line for first powered homing, verifying switch action by hand first. The 40 N control limit is a model value, not load sensing. Using the shopping list’s 36 N·cm motor holding-torque figure gives only 36 N theoretical static cable force at a 10 mm radius, and 20 N at an 18 mm winding radius, before losses; moving torque is lower. The current 40 N feasibility bound is therefore not a demonstrated actuator capability. Calibrate torque/payout limits before relying on the workspace calculation. Do not drive continuously into the mechanical stop. Proof-test guide/bracket/fasteners separately before any suspended payload; provisional 120 N per-anchor proof target follows the existing 40 N operating assumption but does not qualify fatigue or impact performance.

## Clamp review: the user's tilt concern is real

The four corner pieces are welded metal rings and clevis pins, **not bearings**. The rings allow the tied line to align; there are no rolling elements. They need actual articulation, knot and pin-clearance tests. Keep them on the structural deck, not the removable cover.

Four spaced points can provide passive rotational restraint, but unequal cable lengths/tensions can tilt the deck. A single common junction cannot directly transmit cable-generated moments about that junction, so it permits freer yaw and pendulum motion. Joining all four is not a simple cure for a direction-sensitive two-jaw clamp. Keep the four-point prototype for low-height tests and measure attitude before deciding on a different suspension.

**Important integration gap found:** the current planner models a point-mass effector with all cables ending at one point. It does not use the clamp's actual ±69/±64 mm attachment offsets or solve rotational equilibrium. For a rigid body, each length is `norm(anchor_i - (position + rotation @ offset_i))`; force balance must include moments from attachment offsets and measured center of gravity. Four independently controlled cable tensions cannot independently command all six rigid-body degrees of freedom. Accurate encoders do not change that actuator count.

Offline diagnostic (`python -m verification.clamp_pose_diagnostic`) illustrates the mismatch using the default room, an assumed level deck and matched corner ordering: at the room center, actual corner lengths are about 71 mm shorter than point-model lengths; near [0.3,0.3,0.5] m, corrections vary about 17–85 mm. A one-point calibration cannot remove that position-dependent error. These examples are model diagnostics, not measured room results. Do not run near-floor autonomous pickup with the spaced-anchor assembly until attachment-aware kinematics and attitude/stability checks are integrated and calibrated.

Simple scale intuition, not a robot pose prediction: a 1 mm differential vertical displacement across a 138 mm span corresponds to about 0.42°; 5 mm to about 2.1°. The actual response depends on cable directions, compliance, slack and load. At a 3 mm intended ground gap even small tilt matters. Start higher, measure level/tilt and payload shifts, then reduce ground clearance.

Adafruit3886 MPU6050 packaging26×17.8×4.6mm and a tied shelf are above the servo regulator. Tilt telemetry and a calibrated settled pickup gate are implemented; no sensor purchase or physical validation has been performed, and no attitude controller is claimed. A tilt sensor can detect a problem and support a stop/adjustment strategy; it does not by itself eliminate it. Current ESP32 low-voltage shutdown, force feedback and position feedback remain absent; current startup commands the servo open. Test brownout/reboot behavior with a cloth on a bench before suspended use.

The clamp otherwise retains the reviewed electronics slots, fuse shelf, removable lid and recessed TPU pad screws. Actual servo horn stack, PCB connectors, wiring bend radius, threaded fasteners and print distortion are still physical fit gates. Every modeled envelope is checked again after the optional shelf change. Measure total mass and center of gravity; the old 0.45 kg assembly constant has not been validated for this new print.
