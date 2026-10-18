# Claw compact power proposal — 2026-10-18

> Current direction: See the final section, Revised component-built design. The user rejected a finished power bank; the preferred proposal is now a protected 2S battery, embedded USB charger and 5 V buck. Earlier options remain as design history.

Status: RESEARCHED PROPOSAL, not purchased, assembled, load-tested, or a released wiring/CAD revision. User requested detailed research after rejecting the cost and mass of earlier arrangements. This proposal supersedes earlier shopping recommendations only if adopted; preserve the previous decision history.

## Recommendation

For the working moving prototype with one MG996R, XIAO ESP32-S3 Sense camera and FSR, propose:
- One XTAR 3.6 V 18650 3500 mAh USB-C protected 10 A battery.
- One Pololu U3V70F5 (#2891) fixed 5 V boost regulator.
- A secured extended-cell holder, fused power wiring, accessible disconnect, servo decoupling and battery-voltage sensing.
- Charge with the robot electrically switched off through the battery's built-in USB-C charger. Reuse a suitable 5 V / 2 A USB adapter and cable.

This is the best documented compact compromise found in this review, not proof of a globally optimal system. It moves charging and cell protection inside the battery, avoiding a separate RC balance charger, external display/cutoff box and large USB power bank. The converter is retained because the existing servo cannot run reliably directly from a 1S cell over its discharge range.

Important boundary: the exact high-current holder/contact assembly is not yet qualified, and the robot's real peak/average loads remain unmeasured. Do not describe this as a completely verified last-order BOM. Automatic charge-while-awake and self-undocking are not implemented by these two components alone.

## Requirements and evidence

Existing camera board and servo are retained. No new ESP32, servo or FSR is required by this power architecture. XIAO C3 station pin mappings must not be copied to the S3 claw.

TowerPro's current MG996R page quotes 1.4 A stall current, but the owned unit is Deegoo-branded; that figure does not qualify the user's servo. Older circulated MG996R sheets also conflict. Use a provisional 2.5 A servo pulse allowance, not an asserted measured maximum.

Seeed documents approximately 140 mA average and 347 mA capture peak for one webcam example, while its camera comparison lists peaks around 0.6–0.65 A for other configurations. Reserve 0.7 A for camera/MCU/sensors for initial sizing, and measure the actual camera version and firmware.

Provisional design scenario:
- Servo pulse: 2.5 A at 5 V.
- Camera/MCU/FSR: 0.7 A allowance.
- Combined short peak: 3.2 A = 16 W.
- At 3.2 V battery and assumed 88% efficiency, battery current = 16/(3.2*0.88) = 5.68 A.
- This is an engineering allowance, not a worst-case certified servo specification. Higher measured demand requires requalification.
- Stop normal operation before the battery protection cutoff. Do not use over-discharge shutdown as the normal parking signal.

The XTAR battery is specified for 10 A continuous discharge. Pololu specifies thermally dependent input capability, approximately 6 A for many minutes and 8 A for several seconds in the overview; these are INPUT currents, not 5 V output ratings. Its output capability varies with voltage, efficiency and enclosure temperature. The proposal is credible for the above intermittent load, subject to thermal/transient tests.

## Candidate BOM and procurement

| Item | Exact choice | Published data / price | Status |
|---|---|---|---|
| Battery | XTAR 18650 3500mAh USB-C, protected button-top, 3.6 V, 10 A | IMR listing $12.99; manufacturer mass <=53 g; 18.5 +/-0.3 mm diameter, 70.3 +/-0.5 mm long | Proposed, not ordered |
| Boost converter | Pololu U3V70F5 #2891 | Manufacturer $25.95; 40.6 x 15.2 x 4.6 mm; 3.5 g; supply marked rationed/backorders | Proposed; delivery not confirmed |
| Converter alternative supplier | Same exact #2891 from ABRA | Listed in stock at USD $37.38 at review; shipping/checkout unverified | Procurement option, not electrical substitute |
| Holder | Extended protected-18650 holder/contact assembly | MPD BH-18650-PC-E is a mechanical candidate for 70 mm cells; current rating and upper length tolerance not qualified | OPEN, do not release |
| Fuse / disconnect / wire | Reuse appropriate owned parts where rated | Battery branch carries about 5.7 A in the planning peak. Do not copy a 5 V-side fuse value to the battery side. Exact fuse selected against wire/contact ratings and time-current curve | OPEN integration detail |
| Servo capacitor | Initial 470–1000 uF, >=10 V, near servo connector | Starting design value, verify converter startup stability and actual voltage transient; not a substitute for source current | Use suitable owned stock if available |
| Voltage sensing | 100k / 47k divider plus 100nF filter, if available | From switched protected battery terminal to suitable S3 ADC, nominal 1.34 V at 4.2 V; reconcile older 100k/33k schematic before implementation | Proposal, firmware not changed |
| USB adapter/cable | Reuse quality 5 V / 2 A adapter and compatible USB-C cable | Adapter powers the battery's charger, not bare battery terminals | Verify owned adapter |

Costs:
- Battery + converter at manufacturer/reference prices: $38.94 before tax/shipping.
- Using the verified listed in-stock ABRA price: $50.37 before holder, wiring, tax/shipping.
- Allocate roughly $5–15 for holder/switch/passives only as a planning allowance, not a quoted cart.
- Indicative system budget: about $45–65 before shipping/tax, assuming reuse of an appropriate USB adapter and some wiring.
- No exact matching Amazon stock/price was verified. Do not invent Amazon product IDs or delivery dates.
- Battery+converter mass <=56.5 g from published specifications. About 70–90 g installed electrical-power-package target is an estimate excluding printed enclosure, servo and ESP32. Weigh the assembled parts.

A protected USB-C cell is longer than a bare 65 mm 18650. Allocate for maximum 70.8 x 18.8 mm cell dimensions plus holder, retention, USB plug access and bend radius. Do not force it into a standard holder or solder directly to the cell. MPD's candidate holder is not fully approved just because nominal length matches. Verify >=6 A continuous suitability with headroom (prefer documented 10 A path), low contact resistance and vibration retention.

## Electrical topology

Operating:
protected battery terminals -> near-battery fuse -> master disconnect -> boost VIN/GND -> regulated 5 V distribution.
Separate power-and-return branches from the converter:
1. MG996R power, with local bulk capacitance.
2. XIAO 5 V/GND, with camera attached normally.
FSR uses the XIAO 3.3 V sensing circuit. Servo control is a GPIO signal with common ground; preserve/validate the existing signal buffer if used. Motor current must not pass through XIAO traces, GPIO or its regulator.

Charge:
5 V USB supply -> battery USB-C socket -> integrated charger -> cell.
Switch the robot load off first and support the claw mechanically. Leave the XIAO BAT pads unused with this topology. Do not connect another charger across the same battery. Do not feed 5 V into the battery's raw +/- contacts.

For programming, isolate the external 5 V feed to XIAO before connecting PC USB unless an explicitly verified source-selection circuit is installed. Switching the battery alone may leave the shared output rail reachable from PC USB; disconnect the XIAO external 5 V branch for this prototype procedure. Never let PC USB inadvertently power the servo through XIAO.

The boost regulator's ENABLE pull-up is to battery VIN, which can be 4.2 V. Do not connect it directly to a non-5-V-tolerant ESP32 GPIO as an input; use a properly designed transistor interface if implementing software shutdown. An ordinary master disconnect requires no such interface.

## Runtime and charging

Nominal battery energy: 3.6 V * 3.5 Ah = 12.6 Wh.
Assuming 80% usable energy before reserve/voltage sag and 88% conversion efficiency gives 8.87 Wh delivered at 5 V.

| Average total load | Estimated duration |
|---|---|
| 2.5 W / 0.5 A | 3.55 hours |
| 5 W / 1.0 A | 1.77 hours |
| 7.5 W / 1.5 A | 1.18 hours |

These are calculated scenarios, not predicted measured duty-cycle performance. A reasonable initial planning expectation is roughly 1–3 hours active operation, revised after testing. Holding a heavily loaded gripper can dominate consumption; avoid a design that holds the servo stalled.

XTAR specifies 1.35 +/-0.15 A charge current and approximately 2.9 hours USB charging with a suitable 5 V / 2 A adapter. Budget about 3 hours rather than assuming the adapter's 2 A is the cell charge current.

Compared with prior 2S 2200 mAh battery (16.28 Wh), this 12.6 Wh cell has about 23% less nominal energy. Weight reduction partly comes from reduced stored energy, not just integration. Like-for-like runtime is not promised.

## Alternatives examined

- DFRobot DFR0446 MP2636: $8, 35 x 30 mm, 12 g, integrated charge/boost, maximum 2.5 A output. Attractive cheap option but below the provisional 3.2 A combined transient allowance. Do not qualify from charger-current rating.
- Adafruit bq25185+boost #6106: documented power-path but 1 A 5 V output; insufficient for this servo budget.
- Waveshare Solar Power Manager (D): $11.99–12.99 reference, 5 V / 3 A, 45 x 40 x 16.1 mm. Too close/below present transient allowance, larger, and uninterrupted charging/output behavior not established here. Solar input is not needed.
- Generic MT3608/TPS61088 listings: switch-current or headline ratings do not establish continuous 5 V output, thermal limits, low-battery behavior or protection. Existing MT3608 not selected for this combined load.
- 2S LiPo + UBEC + balance charger: good transient headroom but more separate charging/protection parts and higher battery mass for the discussed pack; retain as a fallback if actual measured load exceeds compact 1S capability.
- Large USB-C power bank: integrates management but previous Anker example was 215 g/$49.99 before accessories. Not preferred for minimum airborne mass.
- Direct 1S to MG996R: insufficient voltage over discharge.
- XIAO battery charger alone: does not provide a servo-rated regulated 5 V rail; do not route servo current through the tiny board.

## Hook/contact charging roadmap

Manual USB charging while switched off is the released usage concept for evaluation, not an autonomous dock.

Future dock can feed the EXISTING battery USB-C charger through a mechanically secured short USB-C pigtail and compliant 5 V input interface. Dock contacts carry charging supply, never connect directly to the cell. Hook carries the mechanical load.

Automatic sequence to design:
1. Robot parks and verifies hook support.
2. Hardware disconnects robot load.
3. Dock applies current-limited 5 V to charger input.
4. Charging completes under battery charger control.
5. Separate designed wake/load-switch mechanism restarts robot, with outputs disarmed until release command.

The central winch controller can stay powered while the claw is off. If the claw must remain Wi-Fi-connected during charging, a true power-path/source-selection circuit is needed; built-in USB charging does not demonstrate simultaneous charge/load support. Auto-wake, charge-done sensing, docking contacts and power-path hardware remain an additional revision, not claimed included in today's price.

## Qualification before suspended use

1. Qualify holder/current path: exact cell fit incl USB access, no exposed conductors, firm retained contacts, current rating, voltage drop and temperature.
2. Power converter first with a current-limited source and dummy load; sweep battery-equivalent input from 4.2 to 3.2 V, test normal and planned transient loads. Confirm converter tolerance/wire drop keeps servo supply >=4.8 V and XIAO supply in its allowed range.
3. Run actual camera streaming plus representative gripping/release load; capture fast voltage dips/current with scope or suitable logging instrument. A handheld DMM can miss surges.
4. Verify temperatures over representative repeated use inside the intended enclosure. Stop if thermal shutdown, brownouts, contact heating, or greater current than budget occurs.
5. Verify software low-battery park reserve before hardware cutoff, boot with servo disarmed, loss-of-power grip behavior, and no motion after reconnect until commanded.
6. Verify charging with load switched off and absence of USB backfeed. No deliberate prolonged servo stall needed to establish normal operating behavior.
7. Log average energy use, recharge time and measured mass. Only then freeze final BOM and runtime claims.

## Sources checked

- XTAR manufacturer: https://www.xtar.cc/product/xtar-18650-3500mah-usb-c-10a-lithium-battery.html
- XTAR official shop: https://xtardirect.com/products/xtar-36v-18650-3500mah-usb-c-10a-li-ion-rechargeable-li-ion-battery
- Battery retailer: https://imrbatteries.com/products/xtar-18650-3500mah-usb-c-protected-button-top
- Regulator manufacturer: https://www.pololu.com/product/2891
- Regulator retailer: https://abra-electronics.com/voltage-regulator-modules/dc-dc-step-up-converters/2891-pololu-5v-step-up-voltage-regulator-u3v70f5.html
- Candidate holder: https://www.batteryholders.com/part.php?original=li-ion+18650&override=li-ion+18650&pn=BH-18650-PC-E
- Seeed camera/board documentation: https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/
- TowerPro reference (not Deegoo unit qualification): https://towerpro.com.tw/product/mg996R/
- DFRobot MP2636: https://www.dfrobot.com/product-1613.html
- Adafruit integrated option: https://www.adafruit.com/product/6106
- Waveshare option: https://www.waveshare.com/product/modules/solar-power-manager-d.htm
- Waveshare manual: https://m.media-amazon.com/images/I/A1ieAi-DS7L.pdf

No hardware, firmware, CAD or purchase status changed. This research is stored on the design-history branch, not a claim that the repository default branch or every historical CAD file was updated.

## Later recommendation — prioritize simplicity and low assembly cost (15:15 CDT)

Status: proposed architecture, not purchased or hardware validated. User requested the simplest/cheapest practical overall setup after asking for MG996R running-current averages. This recommendation takes precedence over the earlier XTAR+Pololu preference for the current prototype when ease of assembly and charging are prioritized. The XTAR path remains a lower-mass alternative, not an additional purchase.

Recommend Anker Nano A1653 5000mAh plus Adafruit HUSB238 breakout #5807:
- Manufacturer price $29.99 for A1653; 100 g; 3.03 x 1.45 x 0.98 in (about 77 x 37 x 25 mm).
- Manufacturer lists 5 V / 3 A per USB-C output and 5 V / 3.6 A total (18 W) when shared. This is not 6 A combined.
- One output powers XIAO S3 Sense through a USB-C cable.
- Other output feeds HUSB238 set to 5 V / 3 A, then appropriate servo branch wiring, branch protection and local bulk capacitor to MG996R.
- HUSB238 $5.95; keep 5 V jumper closed, cut 1 A jumper, leave 2 A jumper open for 3 A selection. It requests power, not generates extra current or independently charges a battery. Verify 5 V before connecting electronics.
- All signal grounds referenced together. Do not parallel the positive outputs or add the earlier external 5 V feed to XIAO. Servo current returns directly through its own power branch.
- Secure the bank body and adapter independently in the housing; do not use folding USB plug as a structural support.
- FSR remains on XIAO's existing 3.3 V sensing circuit. Existing camera/servo retained. Wall-mount electronics remain separate on the ALITOVE 12 V system.
- Two core new parts total $35.94 before cables/passives/tax/shipping. Approximate budget $40–45 if cables and small suitable components are partly reused; not a confirmed complete checkout price.
- Manufacturer stock page lists 3–7 business day delivery estimate, not address-specific guaranteed delivery. Exact Amazon price/stock not established.

Load reasoning:
Published current references do not establish actual Deegoo clone draw: TowerPro lists 10 mA idle, 170 mA no-load running and 1.4 A stall; circulated datasheet hosted by DigiKey specifies 0.5–0.9 A running and 2.5 A stall at 6 V. Do not mix these into one measured data set or transfer 6 V values exactly to 5 V.
Keep provisional servo 2.5 A pulse and camera/electronics 0.7 A allowance = 3.2 A combined. Separate outputs with published 3.6 A shared limit make this a more plausible simple option than splitting a single 3 A output. Margin is modest; actual dual-port limits, voltage drops, transients and thermal behavior must pass testing.

Charging/operation:
Support claw, stop motion, disconnect both robot outputs, charge bank through its intended input. No separate RC balance charger, raw-cell holder, display cutoff box, external buck or boost is required by this candidate arrangement.
Anker advertises pass-through, but this does not establish uninterrupted source changes, 3.6 A availability while charging, automatic wake or a complete robotic docking implementation. Keep automatic contact charging as a separate integration stage with hook support, charger input interface and source-transition tests.

Validation required:
- Simultaneous camera streaming and representative loaded gripping at full and low bank state of charge, without reset/output cutoff.
- Servo supply >=4.8 V under the tested load; capture transients if possible.
- Bank wake, low-load timeout, port reallocation when connecting second load and motion-disarmed boot.
- Charging/reconnect causes no uncommanded motion.
- Do not claim software grip-force limiting or capacitance alone makes an undersized source adequate.

Sources:
- https://www.anker.com/products/a1653-usb-c-portable-charger-5000mah
- https://www.adafruit.com/product/5807
- https://learn.adafruit.com/adafruit-husb238-usb-type-c-power-delivery-breakout/pinouts
- https://towerpro.com.tw/product/mg996R/
- https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/204/MG996R.pdf

No firmware/CAD/hardware or purchase status changed.

## Revised component-built design — user rejects finished power bank (2026-10-18)

CURRENT PREFERRED PROPOSAL. User explicitly wants an engineering build from components/modules, not a finished power bank. The A1653 recommendation above is rejected for this project's design goals. Preserve all preceding alternatives as history; do not buy them in addition to this system.

Architecture: factory-assembled protected 2S Li-ion battery + embedded 2S USB charger + fixed 5 V buck regulator. Existing XIAO ESP32-S3 Sense, camera, MG996R and FSR remain. Four wall stations remain on their separate 12 V supply.

### Core parts

| Part | Proposed component | Checked price | Key specification |
|---|---|---|---|
| Battery | Tenergy 31003 protected 7.4 V 2200 mAh 2S1P pack | $18.49 | Treat as 3 A continuous per detailed specs, despite legacy URL/metadata saying 4 A; 1 A maximum rapid charging; 72 x 38 x 19 mm; 99 g |
| Charger | DFRobot DFR0564 | $5.00 | 5 V USB input; 8.4 V +/-1% CC/CV charge; up to 1 A; 28 x 37 mm; micro-USB and input solder pads; supplied heatsink |
| Regulator | DFRobot DFR0753 | $8.50 | 6–14 V input; fixed 5 V output; manufacturer advertises up to 8 A |

Core subtotal $31.99 before tax/shipping. Allow roughly $5–10 for any missing suitable fuse, switch, connectors, voltage-divider passives and bulk capacitor; reuse owned parts where appropriate. This is not a complete verified cart. USB 5 V / 2 A adapter and micro-USB cable assumed reusable. No purchases confirmed.

DFR0753 is selected for input range and inexpensive current headroom, not an assertion that an enclosed module delivers 8 A under every condition. Its >93% efficiency figure is specified at 12 V/full load; use an assumed 90% only for preliminary 2S calculations. Verify thermal behavior and regulation at 6.8–8.4 V and actual load. Exact board mounting dimensions/clearance must be measured or obtained before freezing CAD.

Battery protection is not a charger. Charger is not cell balancing. No balancing capability is established for the selected pack or charger; do not describe it as a balance charger or substitute unmatched loose cells. Pairing is based on published chemistry/voltage/current specifications, not manufacturer certification of the entire robot. Use the pack's protected external leads only.

### Power topology

Charging:
5 V USB adapter -> DFR0564 USB/input pads -> protected battery terminals, through appropriately protected wiring.
Battery positive -> near-battery fuse -> junction.
One junction branch connects charger BAT+; the other connects master RUN switch -> DFR0753 VIN.
Battery protected negative connects charger BAT-, regulator ground and system ground.
DFR0753 5 V output -> separate servo and XIAO power branches.
Servo return -> regulator ground directly.
XIAO return -> regulator ground separately.
FSR remains on the existing XIAO 3.3 V sensor circuit.
Servo PWM remains a common-ground GPIO signal; retain/validate any existing signal buffer.

The charger is connected on the battery side of the RUN switch, so the switch can remove robot loads while allowing charging. Do not connect 8.4 V battery/charger output to XIAO 5 V, XIAO BAT or servo. Leave XIAO BAT unused in this architecture. This single regulated rail is 5 V, not 6 V. Confirm servo voltage stays >=4.8 V at its connector during intended operation.

Initial local servo bulk capacitance: 470–1000 uF, >=10 V, plus existing board decoupling; final choice subject to startup/transient tests. Capacitance is not a substitute for sufficient source capability. Fuse and switch must be selected against actual wiring, battery-current budget and surge behavior; do not copy the winch supply's 7.5 A fuse. No specific fuse value is released here.

For PC USB programming, disconnect the external XIAO 5 V branch and leave the servo unpowered unless a verified source-selection circuit is fitted. Avoid powering the servo through XIAO/PC USB.

### Why 2S and expected performance

Provisional allowance retained: servo 2.5 A short pulse plus camera/electronics 0.7 A = 3.2 A at 5 V, or 16 W. This is not measured Deegoo servo demand.
At 6.8 V battery and assumed 90% conversion efficiency, battery current is 16/(6.8*0.90) = 2.61 A. This fits a 3 A battery rating with modest margin. The 8 A regulator rating does not change the battery's 3 A limit.
A single cell at 3.2 V would need about 5.7 A at 88% efficiency for the same load. Two cells reduce upstream current and permit a cheaper buck converter, at the cost of more battery mass.

Battery-voltage monitoring should request parking before protection cutoff. Provisional threshold: 6.8 V, to be tuned for sag, reserve and actual pack behavior. One proposed divider is 100k upper / 33k lower with 100nF filtering at a suitable free S3 ADC, giving about 2.08 V at 8.4 V. This supersedes earlier 1S divider calculations ONLY for this candidate architecture. Pin assignment, calibration, filtering and firmware are not implemented. Total-pack measurement cannot detect individual-cell imbalance; the pack protection remains essential.

Nominal stored energy about 16.3 Wh. With 80% usable allowance and 90% converter efficiency, usable output energy approximately 11.7 Wh:
- 2.5 W average: 4.7 hours.
- 5 W average: 2.3 hours.
- 7.5 W average: 1.6 hours.
These are conditional calculations, not measured runtime.
Charging at up to 1 A: 2.2 hours ideal constant-current equivalent plus taper/other losses; budget approximately 3–4 hours with adequate USB input and cooling, then measure.

### Charging/docking scope

Initial implementation: support claw, switch RUN off, plug USB into charger, charge, unplug, switch RUN on. No battery removal or large RC balance charger required.
Future hook contacts can deliver regulated 5 V to this SAME charger's input pads. Contacts do not touch raw cells and do not carry the claw mechanically.
Do not promise fully autonomous charge/wake from these three parts alone. Keeping the ESP32 awake while charging requires a designed power-path/load-sharing arrangement; otherwise implement a separate hardware load-disconnect/wake mechanism. Initial manual switch does not complete that roadmap.

### Validation and rejected shortcut

Check regulator output unloaded, then actual camera streaming plus representative gripping, at full and near-reserve input voltage. Capture transient voltage/current and check enclosure temperatures. Stop normal motion before battery protection trips. Measure actual average load/runtime. Do not deliberately sustain a servo stall.

SparkFun BabyBuck AP63357 was examined but not selected: its 3.5 A headline is not its practical no-heatsink continuous output; manufacturer guidance recommends <=1.5 A without heatsink, <=2.5 A with heatsink, and added airflow around 3 A. It would add cooling complications to this compact combined rail.

Sources:
- https://power.tenergy.com/tenergy-li-ion-7-4v-2200mah-rechargeable-battery-w-pcb-2s1p-16-25wh-4a-rate/
- https://www.dfrobot.com/product-1713.html
- https://www.dfrobot.com/product-2162.html
- https://docs.sparkfun.com/SparkFun_Buck_Regulator_AP63357DV-7/single_page/

Only design documentation changed. No hardware, CAD, firmware, inventory or procurement status is claimed changed. This is the preferred component-level proposal pending user adoption and load qualification.
