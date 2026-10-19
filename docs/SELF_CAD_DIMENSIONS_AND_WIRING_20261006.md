# RoomCleaner: dimensional and electrical handoff for your own CAD

Prepared 6 October 2026. Scope: four wall winches and one extended parallel clamp. All dimensions are millimeters unless noted. This is a reference and implementation specification, not an assertion of completed physical qualification. No purchases or receipts are inferred.

**Evidence labels:** U = earlier user-supplied size; S = supplier drawing/model recorded in project; C = current CAD nominal/clearance choice; M = must measure the actual component. A supplier size does not establish printed fit. A C value is changeable in your redesign. The original five-finger `cad/interfaces.py` contains historical interfaces and is not the source for the active parallel clamp.

## 1. What the assembly must do

Each station reels one mechanical Dyneema line using a NEMA17. A magnet rotates with the spool; a stationary AS5600 reads rotation. A bead on the external cable pushes a sliding annular collar, which actuates a fixed KW12 roller switch. The guide ring and motor bracket transfer their reactions into the structural base, adapter and wall dock. The removable cover carries neither cable-guide nor motor load.

The claw has four spaced cable anchors on an upper electronics deck. The battery, camera/controller, IMU and power converters remain above. A printed150mm extension carries a lower servo-driven two-rack clamp. The servo rotates a pinion and translates the two jaws symmetrically. TPU95A pads contact the cloth. Intentional cable-driven attitude maneuvers are excluded; tilt sensing is a settled pickup check, not active leveling.

## 2. Winch purchased interfaces

| Component / interface | Useful dimension | Evidence and use |
|---|---|---|
| NEMA17 motor |42.3×42.3 face;38 body length|U; confirm the actual motor/connector body, not NEMA size alone|
| Motor mounting |31×31 hole-center square; four M3 screws|U/C; screw centers15.5 either side of shaft; measure usable tapped depth|
| Motor locating boss |Ø22; CAD clearanceØ22.4|U/C; boss projection is M|
| Motor shaft |Ø5 D shaft;24 projection|U; actual projection datum and flat depth M; old CAD assumes0.5 flat depth|
| Spool shaft bore |Ø5.2 nominal with D-flat|C; fit coupon first; this is not a proven press fit|
| Spool drum |Ø20 core;26 winding width;Ø36 flanges,3 thick each;32 overall|C; larger winding radius increases torque demand and payout per revolution|
| Spool cable anchoring |Ø1.4 chord hole,6 offset from spool axis; axial position16|C; threaded with shaft installed; knot/tail clearance and retention M|
| Spool grub screw |M3×6 candidate, axial position7; recessed about2 under winding surface|C; align with shaft flat; measure actual engagement and socket access|
| Magnet |K&J D42DIA,Ø6.35×3.175, diametrically magnetized|S; do not substitute an axially magnetized disc|
| Magnet pocket |Ø6.55 nominal;3.175 depth|C; clearance permits eccentricity; centering must be controlled|
| Magnet cup pilot |Ø36.4 internal overØ36 flange;Ø38.4 external skirt|C;0.2 radial clearance is assembly space, not a locating tolerance|
| Cup attachment |Three holes on radius13 at0/120/240°;M3×5 button screws without spacers|C; shallow head relief; head height≤1.7; check printed pilot depth|
| Grove AS5600 |Seeed101020692; PCB outline nominal40×20; package reserve41×24×1.6|S/C; actual connector/components extend beyond bare board|
| AS5600 chip position |10 off PCB center on underside|S; align chip axis with magnet, not board center|
| Encoder PCB holes |Current oriented centers(Y,Z)=(20,53),(40,53),(30,23)|S/C; three M2×5 screws; verify board revision|
| Magnet/sensor gap |1.5 face-to-face nominal|C; magnet diagnostics/runout must be checked through a full revolution|
| Encoder pedestal feet |Two M3 holes at(X,Y)=(48,10),(48,50)|C;40 spacing;M3×16, rear0.5 washers and ordinary2.4 nuts|
| XIAO ESP32-C3 |21×17.8 board;6 populated height reservation|S/C; low-profile wiring; actual USB, antenna and solder joints M|
| XIAO tray |26×22 outer; two attachment centers30 apart|C; foam/tie retention; leave USB and antenna access|
| KW12-3 switch |20×10.5×6.5 body|U; lever pivot, roller, trip/overtravel, force and terminal positions are M|
| Metal outlet |Ronstan RF8090-05; aboutØ15 overall,7.5 axial; nominal5 bore, CAD proxy5.1 throat|S/C; metal flares and external capture groove must be measured|
| Homing collar |Ø28 main face;Ø18.6 central hole;4 thick;2 stroke|C; opening is in collar, not switch; test angled bead arrival|
| External stopper |Ø24×8 nominal; flat contact face|C; printed candidate, not a purchased bead; line fastening M|
| Collar guides |Two Ondrives SHS3-12; approximatelyØ4×12 shoulder, M3×4 thread,Ø6×3 head|S; guide centers36 apart; one round bore and one relieved secondary slot|
| Collar washers |Two1-thick;OD≤7,ID≥4.3|C; separate from0.5 washers elsewhere|
| Return springs |Two Century Z-2CS per station;OD6.35,ID5.33,free9.65,solid3.81,k0.65N/mm|S; installed7→5; pair spring force3.45→6.05N, excluding friction/switch force|
| Driver |Genuine Pololu2133 DRV8825;15.2×20.3 PCB;1.57 PCB,4.06 component-side profile|S; underside components and soldered wires need space; no tall header stack modeled|
| Station logic buck |Pololu2831 D24V10F5;12.7×17.8;3.5 populated reservation|S/C;5V logic branch only|
| VMOT capacitor |Panasonic EEUFR1H101;100µF50V,Ø8×11.5|S; polarity, bottom leads, insulating sleeve and vent clearance|
| Station fuse holder |Littelfuse01550100Z;Ø15.24×55.63|S;14AWG8-inch loop; fuse not included; body dimension excludes complete routed lead envelope|
| Fuse size |3AG cartridge6.35×31.75|S; exact DC-rated series/current/interrupt capacity remains unresolved|
| Prototype input connector |Molex43020-0200 panel plug /43025-0200 mate; two circuits|S; power only, not combined data; each station needs2 male and2 female terminals|
| Connector panel |1.5 thick; accepted supplier range1.40–2.54|S/C; cutout central4.20×7.11, ear region7.90×4.06, key1.98×1.59; corner geometry/snap-ear fit M|

**Cable-diameter correction:** selected line is9KM DWLIFE120lb,150m,8 strands. No measured diameter is recorded. Guide checks use0.6mm while `cad/params.py` uses1.0mm and produces the1.4mm spool anchor hole. Do not carry either assumption into your new CAD as a fact. Measure the real braid under representative tension and size holes, knots, guide clearance and winding accordingly. The120lb marketing rating is not assembled system capacity.

**Encoder centering:** current assembly clearances can accumulate beyond the sensor's documented centering conditions. A larger pocket does not solve this. Datum the sensor and magnet from the actual shaft axis; design adjustment or a repeatable locating feature. Magnet field health, centering and gap all matter.

## 3. Winch structure and motion envelope

Use A=shaft axis, B=motor mounting face, C=structural base back face. The motor/spool axis is perpendicular to B. Give the outlet its own bore-axis datum. Dimension these functional relationships directly instead of chaining exterior case sizes.

Current station coordinates: XY wall plane, +Y upward, +Z away from wall, shaft along X. Shaft axisY30/Z33; motor faceX−2; spool beginsX4.5. These are convenient CAD placements, not required room coordinates.

| Current printed geometry | Nominal definition |
|---|---|
| Structural base |112×150 footprint;6 back plate; integral motor/outlet towers|
| Motor bracket |6 thick;52 alongY and54 alongZ; locating-boss clearanceØ22.4|
| Main enclosure |112×150; approximately68-depth cover;3 wall|
| Revised fuse bulge |36×53 footprint; outer depth reachesZ124; inner roofZ121|
| Wall dock |160×190×12 back plate; current wall planeZ−30|
| Dock rails |Side walls7; lips6; current nominal gaps0.2 side and0.6 face|
| Slide-in adapter |135.6×119.6 main tongue,7.8 thick; protruding lock bridge changes overall height|
| Dock wood-screw clearances |ThreeØ6 holes atY−78,0,68;Ø13×3 head recess; screw type/embedment unresolved|
| Base/adapter bolts |Four M3×20 atX±25,Y±48|
| Positive dock lock |M3×20 plus two0.5 washers and ordinary nut; lock centerY84|
| Cover screws |Four M3×10 atX±51.5,Y±66; driver/head passagesØ6.4|
| Service clearance |Allow at least125 upward slide travel plus forward withdrawal; disconnect/unload first|
| Outlet carrier |52 wide,6 mounting-plate thickness,26 main depth; fixed to base towers|
| Outlet carrier attachment |Two M3 through-bolts, M3×25/M3×30 current stacks; verify actual washers/nuts and grip|
| Outlet upper split jaw |Two M3×10 low button screws, head≤5.7×1.7|
| Switch cradle |Fixed plate and shelf; retained switch and slotted fastening; actual lever alignment determines trip|

The spool is currently supported by the motor shaft, with no outboard bearing. You must evaluate motor bearing capacity, shaft bending and running torque for the actual load. Moving the exit upward does not automatically reduce these loads. The fixed ring is a direction guide, not a2:1 pulley.

The existing outlet clearance is limited to a nominal40° angle from its bore axis, with360° direction around that axis. That is not unrestricted room movement. A bent cable must clear the collar at the spool side and claw side; the bead must still push the collar without wedging.

Normal moving groups: shaft/spool/cup/magnet rotate together; collar translates2; switch lever pivots. Board, metal eyelet, base and cover stay fixed. Do not constrain the collar with two exact round bores if printing error can bind it. Stops carry overtravel, not the switch body. Target switch trip at least0.5 before the2mm stop, including stopping distance.

## 4. Extended claw dimensions

Claw coordinates differ from the old finger assembly: upper deck undersideZ0, +Z toward ceiling. Lower carrier undersideZ−150. Servo output axisX0/Y0. Do not reuse the old tendon drum/hub interfaces.

| Interface | Useful dimension | Evidence |
|---|---|---|
| Upper deck |160×150×4, cornerR10|C|
| Upper removable lid |142×130×50; nominal2 wall/roof|C|
| Lower carrier |140×90×4; bottomZ−150|C|
| Servo body |User earlier41×20.2×38; CAD surrogate40.7×19.7×37|U/C; use actual MG996R clone measurements|
| Servo pocket |43×22 centeredX−10.5,Y0|C|
| Servo ear slots |CentersX−34.5/+13.5,Y±5;5-long×3.4-wide slots|C; actual shaft offset/ear pattern M|
| Horn |Compatible stock round horn≥Ø20, about2 thick|C/M; retain factory spline and center screw; do not print an assumed spline|
| Horn/pinion screws |ThreeØ2.3 holes on radius7 at0/120/240°;M2 attachments|C; actual horn thickness/shaft projection determines axial stack|
| Pinion |Module1.5,24 teeth,20° pressure angle; pitchØ36,tipØ39,7 thick|C|
| Pinion center access |Ø6.5|C; factory horn screw access|
| Racks |116×10×7 bodies; track centersY±24.875|C|
| Rail/sliding clearance |0.3 per side and about0.3 below rack|C; tune via printed coupon|
| Jaw travel |37.699 per jaw for120° servo rotation|C;18×2.094 radians|
| Opening |77.4 open;2.002 closed before pad deformation|C; these are mechanism endpoints, not grip-force guarantees|
| Servo command |20° release /140° closed nominal|C; index horn unloaded; calibrate actual pulse/angle range|
| Jaw plates |4×44×70|C|
| TPU pads |5×40×36; edgeR0.7;TPU95A|C|
| Pad bolts |Four per pad;Y±14, localZ−88/−68 before150 extension;M3×16|C; head≤Ø6×2; keep below cloth contact face|
| Rail bolts |Four atX±53,Y±35;M3×30 with0.5 washers and ordinary2.4 nuts|C; nut/socket relief in lower uprights required|
| Printed uprights |CentersX±43; outer14×18,inner8×12; nominal3 walls|C|
| Upright flanges |24×82×6|C|
| Upper flange holes |X±49,Y±24;M3×20|C|
| Lower flange holes |X±43,Y±36;M3×20|C|
| Lower rail tool reliefs |Ø8 open-edge pockets atX±53,Y±35|C; install rails before upright bolts|
| Extension |150 upper/lower underside separation|C|
| Cable anchors |X±69,Y±64; four M3 clevis pins alongY at upperZ13|C; fixed spacing138×128|
| Cable rings |Welded stainlessOD12/ID8,2 section|C/M; exact supplier/strength pending; no split key rings|
| Cable tie plane |NominalZ21.5|C; actual tied line contact changes with direction|
| Pad bottoms |Z−246.5; nominal cable-plane-to-pad reach268|C; measure actual assembled reach before descent|
| Battery |2S1000mAh candidate; maximum modeled76×37×14|C/listing reservation; connector/wires and actual battery M|
| Battery tray cavity |78×39×18|C; insulation/foam and soft restraint, not pouch compression|
| Servo buck |Pololu D24V50F5;17.8×20.3×8.8 reservation|S/C; two mounting points offset±6.731/±8.001 from board center|
| Logic buck |MP1584EN module;24×20×8 reservation|C; purchased module dimensions vary|
| Claw fuse space |33×18×14; no exact holder selected|C; old5A value is provisional, not final fuse coordination|
| IMU |Adafruit3886 MPU6050;26×17.8×4.6 reservation|S/C; foam/tie shelf28×24|
| Camera/controller |XIAO ESP32-S3 Sense113991115; recorded OEM model24.363×17.78×13.96 overall normalized bounds|S; actual board/camera revision M|
| Camera retention |Two M3×16 deck bolts; two M3×8 keepers; edge pads0.3 front/0.5 rear starting values|C; retain motherboard bare edges, avoid lens/ribbon/components|
| Camera pose |28° toward grip; origin(0,136,22)|C; calibration must follow your redesigned pose|
| Servo lead |Three conductors down right upright;350 allowance,20–22AWG power starting candidate|C; actual path, plugs, bend radius, current and voltage drop determine design|

Current camera models may differ from newly supplied boards: Seeed now documents OV3660 after OV2640 discontinuation. Measure the received unit and check firmware compatibility rather than reproducing the old lens/module envelope blindly.

The parallel clamp may not pick up thin fabric lying flat; TPU friction and closing motion are not proof of that. Test cloth capture, grasp holding current and slip before freezing the jaw geometry. Four anchors do not guarantee level equilibrium across a room; encoder rotation is not pose feedback.

## 5. Electrical architecture: keep the two station profiles distinct

**Profile A: existing centralized motor control.** External12V supply → central CNC shield with four drivers → four motors. Uno receives coordinated host motion. One C3/AS5600 per spool provides feedback over local Wi-Fi to the computer, which bridges it to the central controller. This uses the historically ordered Uno/shield/A4988 hardware. It requires motor/switch runs back to that controller. Exact purchased shield fourth-axis routing and A4988 current-limit resistors need verification. Do not use the local DRV8825 pin/current formula for an A4988 board.

**Profile B: self-contained wall-station housing.** Each station contains C3,DRV8825,AS5600,logic buck,capacitor,fuse and home switch. The pin map below is the implemented detached single-axis USB bench profile. Four-station synchronized transport and machine-level fault recovery are not implemented. The two-pin connector is power only. A final combined power/data plug, data protocol and connector allocation remain undecided. You cannot build a fully specified one-plug synchronized room robot from the present files.

Your current housing references Profile B. Do not connect two motor drivers to the same motor or reuse Uno shield pin assignments on the C3. The hanging Dyneema cables are mechanical only. The battery claw is electrically independent of station supply; Wi-Fi links them through the host computer.

## 6. Local station power connections

1. Isolated external12V DC source → source-side protection/distribution → branch cable → station panel connector. Keep mains entirely outside the station.
2. Prototype connector cavity assignment:1=+12V,2=GND, after verifying actual cavity numbering and both mates. Source side uses recessed female contacts. Exact wire size/fuse/source rating must be coordinated; input motor current is not coil current.
3. Station +12V → local DC-rated fuse → junction feeding DRV8825 VMOT and D24V10F5 VIN.
4. Supply GND → DRV8825 GND and regulator GND, with restrained low-resistance power return wiring.
5.100µF50V electrolytic across VMOT/GND near driver: positive to VMOT, negative stripe toGND. Keep leads short.
6. D24V10F5 VOUT5V → suitable series diode → C3 5V input. Diode anode toward converter, cathode/banded end toward C3. Select diode rating/drop and verify voltage during radio activity; exact diode SKU is not selected.
7. C3 regulated3V3 → AS5600 VCC; C3GND → AS5600GND. Driver/regulator/controller/sensor share a common ground within the station.
8. Disconnect external power when USB programming. The series diode is not a complete validated USB/external power-selection circuit. Do not assume automatic isolation or tie two unqualified5V supplies together.

DRV8825 motor outputs: coilA ends → A1/A2; coilB ends → B1/B2. Identify the two real coil pairs by resistance with power off. Wire colors are not definitive. The shaft changes direction if one pair is reversed; calibrate direction rather than guessing. Do not connect/disconnect the motor while powered.

No separate5V logic supply pin is required on this DRV8825 carrier. Do not put5V into an assumed VDD location taken from an A4988 pinout. VMOT is motor supply; all GPIO remain3.3V logic.

## 7. Local station signal map (XIAO ESP32-C3)

| C3 GPIO / board label | Destination | Function |
|---|---|---|
|GPIO3 /D1|DRV8825 STEP|One pulse commands one microstep|
|GPIO4 /D2|DRV8825 DIR|Direction; setup time before STEP|
|GPIO5 /D3|DRV8825 nENABLE|LOW enabled,HIGH disabled; external10k pull-up to3V3|
|GPIO10 /D10|KW12 COM|Input with pull-up; KW12 NC →GND, NO unused/insulated|
|GPIO20 /D7|DRV8825 nFAULT|LOW fault; firmware pull-up; native USB-CDC required to avoid UART RX conflict|
|GPIO6 /D4|AS5600 SDA|I2C data|
|GPIO7 /D5|AS5600 SCL|I2C clock|
|3V3|DRV8825 nRESET and nSLEEP|Both held high in this bench profile|
|GND|DRV8825 MODE0 and MODE1|Both low|
|3V3|DRV8825 MODE2|High; with above selects1/16 microsteps|

With200-full-step motor,1/16 gives3200microsteps/revolution. Verify your motor step angle. AS5600 gives4096 raw counts/revolution. Set sensor switch to I2C/SDA position; do not program OTP. Address0x36. Keep sensor I2C local, target≤150 harness; existing firmware sets400kHz. Verify pull-ups are to3.3V, not5V, and avoid unintentionally adding many parallel pull-ups.

Home NC wiring: rest closes input toGND; bead activation opens contact and input rises. A broken wire also reads open. A high reading alone does not prove home: release and reapproach must succeed within bounded travel. AC125–250V/5A switch markings do not mean we apply mains; this is a3.3V logic input.

For genuine Pololu2133, current-limit relation I_limit=2×VREF with its documented sense resistors; example1A corresponds0.5VREF, not a prescribed operating current. Set to actual motor and enclosed thermal capability. Clone resistors can change the formula. Holding torque is not available running torque, and a thermal fault can release tension.

## 8. Claw power: battery, two branches and common ground

Use2S LiPo:7.4V nominal,8.4V fully charged. Battery positive → appropriately selected near-battery fuse → accessible disconnect/switch → split into two converter VIN connections. Old5A fuse is a candidate only. Battery negative is the common return.

**Servo branch:** Pololu D24V50F5 VOUT5V → MG996R positive. ConverterGND → servo negative. This converter is a5V/5A class product; actual continuous capability depends on conditions. Servo stall/transient current and temperature must be measured. Never power servo from XIAO3V3 or its small logic regulator.

**Logic branch:** MP1584EN adjusted and verified5V before connection → suitable series diode → S3 Sense5V input. Add and account for the diode here too: current Seeed documentation requires it for external5V input, as on C3. S3GND → logic return; S3 regulated3V3 → IMU VIN, IMU GND →S3GND.

Servo high-current return should run directly back to the designated common power junction rather than through the IMU/controller ground wiring. All three still share reference ground. Route5V servo power/GND together down the extension; add the signal wire and strain relief at both ends. Reserve actual connector boots, wire bend radius and service loops outside rack/pinion motion.

Do not connect raw2S to S3 5V,3V3 or its BAT terminals. Its onboard charging/battery arrangement is for a single cell, not this2S pack. Charge the2S externally with an appropriate balance charger, disconnecting it from the robot. Battery protection, cell-voltage monitoring/undervoltage cutoff and a final rated switch are not implemented/selected. A battery plug disconnect is the existing prototype method.

USB programming: disconnect battery-fed board power; do not assume the diode alone qualifies simultaneous supplies. Servo power must remain controlled so an upload/reset does not move a loaded clamp unexpectedly.

## 9. Claw signal map (XIAO ESP32-S3 Sense)

| S3 GPIO / board label | Destination | Notes |
|---|---|---|
|GPIO1 /D0|MG996R signal|Servo PWM; GPIO13 belongs to the camera in this profile|
|GPIO5 /D4|MPU6050 SDA|3.3V I2C; address0x68 withAD0 low/default|
|GPIO6 /D5|MPU6050 SCL|Verify pad labels; harness colors alone are insufficient|
|3V3|Adafruit3886 VIN|Selected module's power input; confirm actual module revision|
|GND|IMU GND and servo reference ground|Common reference, separate high-current return routing|
|Onboard camera connector|Supplied camera daughterboard/ribbon|Not connected to those external IMU pins|

Use positional MG996R, not continuous-rotation version. Factory spline/horn screw couples servo to round horn; three M2 bolts couple horn to pinion. Signal angle is a requested position, not measured force or verified servo angle. Confirm3.3V PWM recognition by the actual servo and establish pulse endpoints unloaded; level shifting, if necessary for a variant, is not yet selected.

Current firmware reserves separate PWM resources for servo and camera and has a camera build option. Simultaneous streaming/servo/IMU stability still needs hardware tests. Wi-Fi antenna must be retained clear of motor, metal rings and battery; lid removal must not pull its connector.

## 10. What happens during operation

Local station sequence: reset leaves driver disabled through enable pull-up → ARM BENCH → bounded home seek/backoff/slow reseek with stable switch edges and valid encoder → accept limited MOVE → check spool angle while issuing steps → settle against measured angle → accept completion. Home lengths remain measured placeholders, not0. Lost encoder/heartbeat, driver fault, unexpected home opening or persistent mismatch latches a pulse-stop fault and invalidates home. Holding remains enabled where the fault policy allows; this is not a mechanical brake and cannot hold through power/driver failure.

Existing local bench defaults: home seek320microsteps/s, backoff256steps, latch80; seek bound6400. Encoder polls5ms, stale30ms; heartbeat500ms; tracking64counts/150ms; settle within4counts for50ms, timeout500ms. These are software settings, not cable travel accuracy. Maximum commanded1000microsteps/s. Do not combine these with different limits in the central Uno profile.

ForØ20 core, ideal bare-core payout/revolution=π×20=62.832;3200microsteps gives0.019635 per microstep;4096encoder counts gives0.01534 per count. Real payout is2πr_effective; layered winding changesr_effective. Encoder angle therefore does not prove payload travel, no-slip cable traction or successful pickup. Measure payout under tension.

Claw: host checks settled tilt → issues close → servo moves requested angle → camera checks garment movement after a partial lift → retry if absent → transport → release over hamper → camera confirms deposition before incrementing delivered count. Existing IMU gate rejects unsettled/tilted pickup; it does not actively balance the four winches or supply absolute yaw.

Current camera firmware exposes /capture JPEG and a browser page that requests repeated images with approximately300ms pause after each completed image. It is not a proven continuous video stream or validated autonomous scanning pipeline. Moving-camera pose, calibrated intrinsics, detection latency, occlusion and payload/delivery verification need integration/bench validation.

The local four-controller network motion layer is absent. Do not interpret this sequence as an already-working synchronized four-axis machine. Keep each local controller detached for its current bench test. Room safety/coordination, collision envelope, tension feasibility and start/stop recovery remain system-design work.

## 11. CAD assembly and service requirements

- Keep motor locating datum, shaft center, magnet center and encoder chip aligned. Measure rotating runout, not just static centering. Preserve spool screw access and cable threading with motor installed.
- Capture the ring's groove with removable split jaws; expose its metal flares. Ring and jaw install before the collar and switch cradle. Provide actual driver access after those are removed. No printed ring for loaded cable contact.
- Guide collar without overconstraint; design hard stops and spring margins. Keep switch terminals outside moving envelope. Verify free return under angled bead force.
- Place rear nuts before the adapter blocks access. Lock retention washer/fastener must be installable with the station assembled. Provide room for upward removal.
- Attach populated boards to accessible supports at known bare PCB edges; no pressure on chips, solder joints, capacitor vent or lens. Low-profile soldered wires were assumed; headers change height.
- Fuse support removal in old revision requires disconnecting/releasing both leads, deflecting them to access twoM3×10 screws, and lifting support plus holder together. Lower lead is threaded through its seat off-case. For your CAD, prefer a service layout that does not require passing a permanently terminated lead through a small closed hole.
- Reserve full motor connector, crimp contacts, diode, joint insulation, harness bends and hand/tool volume. Existing nominal body-fit checks do not provide those envelopes.
- Claw rails fit before upright fasteners; allow tools through open pockets. Confirm horn/gear axial stack, full jaw travel, lower servo ear access and right-upright wire threading before closing the upper box.
- Printed material and tolerances: structural PETG,TPU95A pads; local hole/pocket corrections based on test coupons, not universal shrinkage or global scaling. M3 clearance3.4 and pilot2.8 are old CAD starting values. Inserts require supplier-specific holes. No final mechanical load rating exists.

## 12. Order/inventory snapshot and remaining selections

Reported ordered in historical records, receipt/count not verified: NEMA17 pack;120lb line;KW12 switch pack;12V supply;Uno kit/CNC shield/A4988 kit;USB overhead webcam;MG996R pack;ELEGOO ESP32 pack;MP1584EN buck pack;M3 assortment;automotive blade fuse kit;USB boost charger. Existing M3 preference/first printed spool do not establish all required hardware quantities. The older webcam/large ESP32/central shield are legacy options for this active local-station/S3-camera layout.

Not recorded ordered:4 Grove AS5600,4 XIAO ESP32-C3,4 D42DIA magnets,4 Ronstan rings,8 SHS3-12 guides,8 Century Z-2CS springs,12 M2×5 encoder screws,1 S3 Sense camera/controller,1 Adafruit3886 IMU,1 battery/2S balance charger,1 D24V50F5 servo buck. For local packaging additionally4 genuineDRV8825,4 D24V10F5,4 capacitors,4 Littelfuse holders and selectedDC fuses,4 panel plugs/4mates and their contacts. Both controller-power isolation diodes and complete harnesses need selection. Purchase approval is not an order confirmation.

Check actual M3 stock for each station:4×20 base/adapter;1×20 lock;4×10 motor;1×25+1×30 outlet carrier;2×12 switch cradle;4×10 cover;2×12 node;3×5 cup;2×16 encoder feet;2×10 outlet jaw;4×16 electronics carrier;4×8 board keepers;2×10 input panel;2×10 revised fuse support. Specialized shoulder screws are additional. Capacitor keeper adds2M2×10; encoder adds3M2×5. Washer/nut thickness and low button-head limits are interface requirements; consult fresh build notes rather than substituting tall heads/nylocs indiscriminately. Counts are per installed station, not including spares or optional tooling.

For claw: MG996R and round horn;S3Sense;IMU;2S battery;separate servo/logic bucks;DC fuse/holder/switch;four welded cable rings;signal/power extension;M3/M2 hardware;selected inserts;foam/silicone pads/ties;PETG/TPU95A. Extension adds8M3×20/8nyloc/8washers;camera adds2M3×16/2nyloc/2washers and2M3×8 keeper screws. Remaining clamp hardware is in `BOM_CLAMP_V1.csv`, but omit its old ESP32 tray and use current camera assembly.

No final recommendation is made for exact wall screws, combined power/data connector/transport, diode SKU, DC fuse ratings, battery low-voltage protection, actual servo horn, terminated harness connectors, separate spool bearings/brake or exact cable knot. These must be selected against real dimensions and operating demands. Old generic spring specifications and cupM3×6-plus-spacer recipe are superseded by the values above.

## 13. Measurements before your new CAD is frozen

1. Actual motor body, boss height, shaft projection/flat and tapped depth; actual bracket orientation.
2. Actual braid diameter, knot/stopper fastening and cable approach directions.
3. Actual KW12 lever/roller/pivot, terminal geometry, trip/release/force; actual spring/guide dimensions.
4. Magnet dimensions, sensor revision/chip location, connector height and all intended solder/header profiles.
5. Servo body/ear/shaft offset, factory horn and screw, horn/gear axial stack; output travel and loaded current.
6. Battery dimensions plus leads/connectors; actual camera/lens/USB/ribbon/antenna envelope; actual regulators and IMU.
7. Full harness layout and retained bend/service loops; board-power diode/drop; matched connectors and DC protection.
8. Actual claw mass/COM, intended payload/dynamics, motor running torque, shaft/bearing limits, directional guide/dock loads and actual wall backing. Five pounds is reserve demand to investigate, not verified capacity.

## 14. Primary references and project evidence

Electrical sources checked6October2026:
- Seeed C3 power/pinout: https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/
- Seeed S3 Sense power and current camera revision: https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/
- S3 pin multiplexing: https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/
- Genuine Pololu2133 DRV8825: https://www.pololu.com/product/2133
- Station buck2831: https://www.pololu.com/product/2831
- Servo buck2851: https://www.pololu.com/product/2851

Recorded dimensional sources (recheck purchased revision):
- Grove AS5600: https://wiki.seeedstudio.com/Grove-12-bit-Magnetic-Rotary-Position-Sensor-AS5600/
- Magnet: https://www.kjmagnetics.com/d42dia-neodymium-diametric-disc-magnet
- Ring: https://www.ronstan.com/us/ropeglide-ring15mm-x-5mm-x-7mmblack-1.html
- Guide: https://ondrives.com/shoulder-screws/shs3-12
- Spring: https://www.centuryspring.com/shop/z-2cs
- IMU: https://www.adafruit.com/product/3886
- Fuse holder: https://www.littelfuse.com/assetdocs/littelfuse-fuse-holder-155-100-datasheetpdf?assetguid=feb34c70-4b5c-48a2-88f9-895c15c5efcc

Project evidence: `cad/winch_bench.py`, `cad/parts/winch_spool_v2.py`, `cad/winch_slide_mount.py`, `cad/winch_local_electronics.py`, `cad/winch_fuse_service.py`, `cad/clamp_v1.py`, `cad/clamp_extended_v3.py`, `docs/MOUNT_INTERFACE_CONTROL_20261002.md`, `docs/FRESH_MOUNT_RELEASE_20261002.md`, `docs/EXTENDED_CLAW_V3_BUILD.md`, `docs/LOCAL_STATION_HARDWARE_20261004.md`, `docs/LOCAL_STATION_CONTROL_20261004.md`, `firmware/local_station/local_station.ino`, `firmware/effector_esp32/effector_esp32.ino`.
