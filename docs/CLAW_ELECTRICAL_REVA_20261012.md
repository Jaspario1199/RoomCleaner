# Claw electrical design — Rev A, 2026-10-12

Printable drawing: `output/pdf/Claw_Electrical_RevA.pdf`. Generator: `tools/build_claw_electrical_schematic.py`.

Status: complete proposed module-level wiring topology and discrete sensor/servo interfaces. This is **not a hardware-validated final release**. The actual battery/protection/connector, regulator qualification, fuse coordination and confirmation of the Sense camera attachment remain release gates. Existing firmware has not been changed by this schematic task.

## Purchase update — 2026-10-12, 17:19 America/Chicago

User confirmed purchase of the force sensors discussed above and supplied product image `51LqLcEn6oL._AC_SL1001_.jpg`. Record FSR1 as **purchased, receipt and physical measurements unverified**. The linked listing advertises a two-piece pack; received quantity has not been counted. The PDF is the earlier review issue and its sensor procurement status is superseded by this update; its circuit is unchanged.

Dimensions labeled in the supplied image:

- Sensor head outside diameter: 10 mm.
- Inner sensing region indicated: 8 mm diameter; confirm the actual active boundary before sizing the actuator.
- Film body length indicated: 19 mm, excluding the projecting metal pins shown below it.
- Pin pitch: 2.54 mm.
- Film thickness, full length including pins, tail width and bend limits: not specified in this image.

Mechanical proposal: locate the head in a shallow approximately 10.4 mm diameter pocket, with depth set only after measuring film thickness. Use an approximately 6 mm diameter flat actuator as a prototype starting point, centered within the indicated 8 mm sensing region. Keep retention off the sensing face, provide tail/connection clearance, and calibrate the complete pad stack. The 10.4 mm pocket and 6 mm actuator are proposed CAD dimensions, not supplier dimensions or a validated force-transfer design.

## Architecture

### New requirement — automatic wall-hook charging (2026-10-12, 17:33 America/Chicago)

User wants the claw to park on a custom wall hook and automatically make charging contact. This supersedes removable-pack-only charging as the end-state requirement. Rev A PDF remains a manual-charge bench circuit and does NOT implement this dock; its battery-removal instructions apply until the revised charging hardware is built and qualified.

Proposed dock behavior: approach slowly, align through tapered guides, lower a structural hanger onto a load-bearing hook/cradle, verify seating, disable the unloaded servo, confirm stable correctly polarized contacts, then enable charging. Maintain slight controlled cable tension to avoid loose line and preserve a defined departure sequence. The hook and anti-rotation guide carry the weight and moments, not the electrical contacts.

Use recessed compliant contacts (spring pins against pads, with alignment features), not an unsupported USB plug insertion. Ensure misalignment cannot bridge battery/cell-tap contacts; exposed battery-side conductors require fault-current protection and guarded geometry. Contact force, travel, current rating and mechanical retention are pending part selection.

Electrical revision must provide correct 2S CC/CV charging, per-cell balancing and protection, temperature supervision, charge/status reporting, and dock presence detection. Do not substitute an 8.4 V boost converter for a verified charger or assume a protection board is itself a charger. Keep the controller available during rest using a qualified charger power-path arrangement or a separate dock-powered logic path with battery-load isolation; servo off while parked. If charging electronics are on the wall, balance/cell connections may require extra dock contacts. If onboard, fewer dock contacts are possible at the cost of onboard mass and volume. Final contact count is not frozen.

Prefer investigating wall-side charging electronics first to minimize suspended mass. Do not purchase a charger solely because it says '2S': verify unattended automatic start after battery connection, termination, balance behavior, protection interaction and status detection. Prototype manual seating/contact alignment before autonomous docking. Departure sequence must terminate charging, transfer logic power safely, confirm battery readiness, take up the suspended load and only then clear the hook. Dead-battery recovery cannot depend solely on running ESP32 firmware.

Existing records show the B3 Pro-style balance charger as not ordered; an ACEIRMC 2S USB boost board was reported purchased, but its exact variant and charge/balance behavior are not qualified for this dock. Battery purchase remains unconfirmed. No new charging parts were ordered in this update.

Use one 2S lithium battery for the claw, with separate 5 V servo and logic regulators. The XIAO remains on the horizontal camera bracket; distribution, passives and the servo buffer are in the main housing. The servo and force sensor are at the lower claw. All grounds are common, but servo load current returns directly to the servo regulator rather than through the XIAO or sensor return wiring.

The user photo identifies a XIAO ESP32-S3 main board. The matching Sense camera expansion board is assumed in this design; the underside photo alone does not establish that it was included. The older USB UVC camera is not used in this circuit.

## Point-to-point net schedule

The dots in the PDF indicate junctions. Every ground symbol refers to GND. Component pin numbers below refer to the IC's manufacturer numbering; adapter/header numbering must be checked separately. J1/J2/J3 cavity numbers are proposed assignments, not universal connector conventions.

| Net | Connected terminals |
|---|---|
| BAT_PROTECTED_POS | J1.1, F1 input |
| BAT_FUSED | F1 output, S1 input |
| VBAT_SW | S1 output, U1 VIN, U2 IN+, C1 positive, R4 top |
| GND | J1.2, U1 ground(s), U2 IN-/OUT-, U4 GND, U3.1 (/OE), U3.3, J2.1, R2 bottom, R5 bottom, R7 bottom, all capacitor negative/ground terminals |
| SERVO_BUCK_OUT | U1 VOUT, F2 input |
| +5V_SERVO | F2 output, J2.2, U3.5, C2 positive, C4 supply terminal, C7 supply terminal |
| LOGIC_BUCK_OUT | U2 OUT+, F3 input |
| LOGIC_FUSED | F3 output, D1 anode |
| +5V_XIAO | D1 cathode/banded end, U4 5V/VBUS pad, C3 positive, C8 supply terminal |
| +3V3_SENSOR | U4 3V3 output, R1 input |
| FSR_EXC | R1 output, J3.1 |
| FSR_RETURN | J3.2, R2 top, R3 input |
| FSR_ADC | R3 output, C5 signal terminal, U4 D1 / GPIO2 / ADC1_CH1 |
| VBAT_ADC | R4 bottom, R5 top, C6 signal terminal, U4 D3 / GPIO4 / ADC1_CH3 |
| SERVO_PWM_3V3 | U4 D0 / GPIO1, R6 input |
| BUFFER_IN | R6 output, R7 top, U3.2 (A) |
| BUFFER_OUT | U3.4 (Y), R8 input |
| PWM_5V | R8 output, J2.3 |
| FSR1 sensing element | Between J3.1 and J3.2; no external supply terminal on the passive sensor itself |
| CAM1 | Factory Sense camera assembly connection to XIAO; see manufacturer pin map |
| No connection | XIAO BAT pads; U1 EN left floating as permitted by its internal pull-up |

### Values

- R1 2.2 kΩ, R2 10 kΩ, R3 1 kΩ, R4 100 kΩ, R5 33 kΩ, R6 1 kΩ, R7 47 kΩ, R8 220 Ω. All 1%, at least 0.125 W.
- C1 220 µF / 16 V at switched battery input; C2 1000 µF / 10 V at the lower servo; C3 100 µF / 10 V at XIAO power input.
- C4–C8 100 nF ceramic / at least 16 V: buffer bypass, FSR ADC filter, battery ADC filter, lower servo bypass, XIAO input bypass respectively.
- D1 1N5819, anode toward regulator, cathode/band toward XIAO. External supply path follows Seeed's diode guidance. Account for diode drop in the measured board input voltage. Do not connect raw 2S voltage to the board's 5V or BAT pads.
- U1 Pololu D24V50F5 at 5 V, previous candidate. It is not assumed on hand. Manufacturer dropout varies with load; qualification must include low battery and high servo current.
- U2 existing MP1584EN module, adjusted to 5.00 V and qualified for at least 1 A output over the working input range. A module's advertised peak rating is not evidence of sustained performance.
- U3 TI SN74AHCT1G125DBVR with a suitable SOT-23-5 breakout. Pins: 1 /OE, 2 A, 3 GND, 4 Y, 5 VCC. Fixed 5 V servo supply is within its 4.5–5.5 V range; 3.3 V logic exceeds its 2 V minimum HIGH input. Do not substitute a generic HC buffer without checking input thresholds.
- F1 5 A, F2 3 A, F3 1 A are **provisional** starting values, with suitable DC-rated holders. Confirm inrush, time-current behavior, connector ratings, pack capability and wire protection before release.
- S1 SPST main disconnect, at least 10 A DC at 12 V. An AC rating alone is not the required rating.

The 1N5819 was reported delivered for VELOX; remaining stock is not verified. New buffer, breakout, exact fuses/switch and capacitors are proposed parts, not confirmed purchases.

## Harnesses and physical placement

**Six conductors between housing and camera board:** +5V_XIAO, GND, 3V3, SERVO_PWM_3V3, FSR_ADC, VBAT_ADC. Use 24 AWG power/ground and 26 AWG signals for this short prototype harness. Place C3/C8 at the XIAO end. Place C5/C6 near the analog pins, even if the divider resistors are on the housing distribution board. Tie grounds together electrically while keeping the servo return path separate physically.

**Five conductors down the tube:** +5V_SERVO, servo GND, PWM_5V, FSR_EXC, FSR_RETURN. Use 20 AWG copper for the servo power pair and 26 AWG for signal/sensor wiring. Twist the two sensor wires together, keep away from the servo power pair where possible, and provide a service loop at the moving jaw. Do not use the sensor tail as the flexible harness.

Use 18 AWG copper for the main battery harness. The connector system must be selected for the actual wire gauges and verified current, not merely physical compatibility. The main battery connector type remains open until the actual pack is identified. J2 uses the actual servo lead order, commonly ground/power/signal; verify rather than relying on colors. Secure soldered/crimped connectors; no loose breadboard joints in the suspended unit.

The upper housing must reserve space for U1/U2, fuse holders, the disconnect body, buffer/breakout, passive components, wiring bends and the battery. These are additional to the tiny XIAO dimensions. Exact tray dimensions cannot be frozen without the selected modules/connectors.

## Analog checks

At nominal resistor values:

`V_FSR_ADC = 3.3 × 10000 / (R_FSR + 2200 + 10000)`.

An open sensor reads near zero; a shorted sensor produces 2.705 V maximum nominally. R1 limits sensor current and leaves ADC headroom. This is a nonlinear measurement; mount geometry, material creep, contact area and temperature affect calibration. A disconnected sensor looks like no contact, so a closure timeout and position/travel limit are required.

`V_BAT_ADC = V_BAT_SW × 33000 / 133000`.

An 8.4 V pack produces 2.084 V nominally. Use ADC1, appropriate attenuation and calibrated millivolts, then compare to a meter. With 1% resistor extremes at 8.4 V the maximum remains below 2.12 V; the FSR short-circuit maximum remains below 2.75 V at 3.3 V excitation. Actual rail tolerance and ADC calibration still matter.

## Power, charging and recovery

The drawing assumes a **verified protected 2S pack or an appropriately matched per-cell protection assembly**. Its exact implementation is not frozen. A bare RC pack is not automatically protected. The regulator's own undervoltage lockout is not a lithium battery protection system. Pack-voltage monitoring cannot identify one weak/imbalanced cell.

Use the pack's matched external 2S balance/protected-pack charger as applicable, with the pack removed/disconnected from the robot. No charging circuit is designed here. Leave XIAO BAT pads unused.

Provisional software thresholds: warning at 7.0 V, stop starting new tasks at 6.8 V, filtered under load. Select final thresholds from the actual pack discharge limits, cell protection and regulator dropout. Begin recovery before a hard cutoff; loss of power may release a servo-held garment. No automatic release just because communication disappears. S1 OFF removes battery power but USB can still run the controller; unplug USB for full isolation.

U3 follows the servo rail. In USB-only service, keep servo PWM disabled/LOW and disconnect the servo initially. Check startup, USB insertion/removal, shutdown and rail-fault sequencing on the bench. This design does not claim a guaranteed glitch-free servo startup.

## Firmware integration requirements

The camera's XCLK generator and servo PWM must use distinct timer resources, not merely different pins. Begin with 50 Hz servo control, calibrated pulse endpoints and explicit arm/close/open commands. Do not use a library that silently reconfigures the camera timer. Sample/average the two ADC1 channels while streaming and test power-supply noise.

Force control: record unloaded baseline, approach slowly, stop increasing closure at a calibrated threshold, and cap travel/time. Do not continually increase closure to chase FSR drift. Detect saturation and implausible readings, but acknowledge that open-circuit and no-force states are indistinguishable with this simple divider. Camera verification remains necessary for pickup and delivery.

## Release evidence required

1. Identify the actual battery/protection/connector/charger and camera kit.
2. Meter-check both rails before plugging in XIAO or servo; load-test U2 and qualify U1 over battery range.
3. Verify pinout, capacitor polarity, diode direction and common-ground continuity.
4. Measure servo current/inrush and choose final branch/main fuse ratings.
5. Scope PWM and rails during startup, camera capture, servo motion/hold and USB service.
6. Check FSR open/short tests, force calibration, motion limits, low battery and communications recovery before suspended trials.

Sources: Seeed XIAO S3 getting-started and pin-multiplexing documentation; TI SN74AHCT1G125 datasheet; Pololu product 2851; TowerPro MG996R product page; user-selected Amazon ASIN B07T1CHY58; Interlink FSR integration guide. Full URLs are in the PDF. Interlink guidance supports general FSR integration; its product specifications are not substituted for the DF9-16 seller's specifications.
