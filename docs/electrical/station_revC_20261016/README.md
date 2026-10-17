# Motor station electrical review - Rev C

Date: October 16, 2026 (America/Chicago). Scope: one unloaded motor station, repeated four times, using a XIAO ESP32-C3, red A4988 carrier, DROK buck and KW12-3 NC switch. This is not the S3 camera-claw circuit or a DRV8825 pinout.

## Read the drawing

- [Four-page vector PDF](RoomCleaner_Station_RevC.pdf): power circuit, control circuit, complete connection ledger, audit and restart sequence.
- [Power circuit SVG](sheet_1.svg)
- [Control circuit SVG](sheet_2.svg)
- [Connection ledger SVG](sheet_3.svg)
- [Audit SVG](sheet_4.svg)
- [Reproducible drawing source](draw_schematic.py)

The drawings are module-level electrical schematics, not PCB layouts. Position within a symbol is not physical header position. U2A/U2B represent one XIAO; U3A/U3B represent one driver. Filled dots are junctions, wire hops are unconnected crossings, and identical net labels / ground symbols connect electrically across sheets. Resistor rectangles are components, not direct wire connections. JP1 is a removable positive-feed connection, drawn open. Leave it open for every ordinary USB connection; close it only for standalone operation with USB unplugged. Change connections with both sources removed.

## Findings from this session

User reported VDD, RESET and SLEEP each at 3.3V; VMOT-to-neighboring-GND at 0V; afterward the XIAO heated with USB and was not recognized. It has not been established that the XIAO was fully disconnected from every peripheral during the USB-only observation. Treat both the XIAO and external assembly as suspect. No root cause or permanently failed part has been proven. A low VMOT reading does not distinguish missing positive, missing return, fuse, supply, short or measurement error by itself.

The requested circuit is now explicit, but this is not verification of the user's perfboard. No replacement XIAO should be installed in the unchanged suspect assembly. No actual motor run, current setting, load rating or four-axis qualification is established by this document.

## Corrections and additions

1. **Power source selection:** Earlier advice made the external 1N5819 seem sufficient for simultaneous USB/external power. The Seeed schematic places the exposed 5V pin on VBUS. A diode from the buck to that net blocks reverse current into the buck, not every external-to-host current path. JP1 makes source selection explicit: open during USB use. This does not establish USB backfeed as the failure cause.
2. **Ground:** Both driver GND pins, both buck negatives, XIAO GND and source negative are one electrical net. A motor return should run directly to the incoming power return, not along a narrow controller-ground lead. The buck's internal negative connection can establish the common reference, but it should not be the main motor-current return path. An extra external ground connection is allowed, not required to make two separate grounds magically work.
3. **Defined boot states:** Retain R1 10k from ENABLE to 3.3V. R2/R3 10k to ground are proposed additions for STEP/DIR. R4 10k from HOME to 3.3V strengthens the pull-up already enabled by firmware. These additions are not evidence of installed hardware, and their omission alone does not establish why the XIAO heated. All resistors may be ordinary 1/4W parts; voltage/current here are small.
4. **Protection:** The matching DROK family explicitly lacks output overvoltage and input reverse-polarity protection. A correctly oriented 1N5819 is not a clamp against a buck failure or mistaken 12V connection. This remains a supervised prototype, not a fault-tolerant supply design. A protected regulator/eFuse/power-path design would be a separate qualified revision; do not assume protection exists because a fuse is present.
5. **Fuses:** F1-F4 belong at the distribution/source end of long positive branch wires. A fuse only at the station does not protect the upstream cable from a short before that fuse. F0=7.5A is recorded existing hardware, not a validated rating for unknown wires. A supply limited below a fuse's trip current may not clear it. Need conductor material/gauge, connector ratings, expected input current, supply fault behavior and fuse curve. Do not guess a final branch value or bypass a blown fuse.
6. **Motor/current:** A4988 VDD remains 3.3V to match C3 signals; changing it to 5V is not a repair. RESET/SLEEP high and MS1-3 low are valid for this test. Need exact motor phase rating and carrier Rsense before a Vref target. Supply current is not motor phase current. NEMA17 specifies size, not electrical rating. Carrier clone cooling/current capability is not inferred from Pololu hardware.
7. **Local decoupling:** C1 is 100uF/50V across VMOT and its return, close to the carrier, in addition to the carrier's onboard ceramic capacitors. Do not connect it in series. Confirm its actual printed rating/polarity. It reduces spikes but does not prove long-cable or regenerative-load transients stay within the buck/driver ratings. Preserve onboard decoupling; this schematic is not for a bare A4988 IC.

## What each part does

| Reference | Component | Role/status |
|---|---|---|
| U1 | DROK adjustable buck | Set 5.00V at its disconnected output; exact revision still needs inspection |
| U2 | XIAO ESP32-C3 | Reads switch, sends STEP/DIR/ENABLE; suspect board quarantined |
| U3 | A4988 carrier | Switches motor coil current from the 12V supply |
| C1 | 100uF 50V electrolytic | Local VMOT bulk decoupling; stripe to ground |
| D1 | 1N5819 | Anode to buck OUT+, striped cathode toward JP1/XIAO |
| JP1 | Removable positive-feed link | Proposed new means to disconnect buck output from XIAO 5V during USB use |
| R1 | 10k | ENABLE default HIGH/disabled; previously specified, installation unconfirmed |
| R2 / R3 | 10k each | Proposed STEP/DIR default LOW |
| R4 | 10k | Proposed external switch pull-up; retain INPUT_PULLUP |
| S1 | KW12-3 | COM/NC used; NO unused. Test actual terminal identity with meter |
| J1 | Two-wire station power inlet | Source-fused positive and return; choose rating to match wiring |
| J2 | Four motor connections | One coil across 1A/1B, other across 2A/2B |
| J3 | Two switch connections | NC signal and COM ground |
| F0 | Existing 7.5A main fuse | Recorded only, suitability unresolved |
| F1-F4 | Branch fuses | Values unresolved; at source before long cables |

JP1 can be a suitable removable connector rather than a literal PCB jumper. Use sockets for replaceable modules, insulated connections, strain relief, and test points that can be probed without bridging adjacent pins. Exact perfboard pad-to-pad routing cannot be certified until the copper pattern and assembly are inspected. Stripboard rows and isolated-pad perfboard behave differently. Keep the 12V paths clear of logic wiring and use a conductor suitable for current rather than relying on a long thin solder bridge. All unused XIAO pins and battery pads remain unconnected in this revision. Buck EN remains externally unconnected as in the tested/default-on module; verify the exact module before changing it.

## Controlled testing and operational limits

Follow sheet 4, progressing with electronics removed before adding known-good modules. On an unpowered assembly, check both intended continuity and unintended connections between distinct rails. A persistent near-zero resistance deserves investigation, but capacitors/semiconductors can make a continuity buzzer misleading; a brief beep or polarity-dependent reading is not proof of a short. Confirm capacitor voltage near zero before resistance measurement. Do not discharge by shorting it with a screwdriver.

Keep the meter leads in COM and V/ohms for voltage measurements. Use black on a verified return and red on named test points. Never put a meter in current mode directly across a supply. Use a current-limited bench supply for fault finding where available; no universal current-limit setting is specified without knowing which stage is under test. Stop immediately if an isolated board heats unexpectedly.

The existing bench sketch sends 20 steps at 50Hz, then disables motor outputs. Its completion message is not feedback. Enable is active low; a multimeter may miss its 0.4-second active window. STEP pulses are only 5us high. Use a scope or logic analyzer to inspect pulses; a near-zero average STEP voltage is not evidence that no pulses were sent. Do not use this sketch with suspended loads: it deliberately releases holding torque. Pressing/opening the NC switch stops both test directions; a fresh command after release is needed. This is a software stop, not a rated safety circuit, and a switch wire short to ground can hide a hit. Supply removal also releases the load; no brake or independently qualified emergency-stop behavior has been implemented here.

The one-source, four-parallel-station arrangement remains feasible as an architecture. The actual 12V/6A total capacity has not been validated with all four motors at their intended phase currents, speeds and accelerations. Evaluate station heating, voltage drop, source behavior and transients before room installation.

## Still open before release

- Full isolation/assessment of damaged-looking XIAO, A4988 and wiring; identify original fault.
- Exact motor model, phase rating, winding resistance, and both sense-resistor values; calculated/measured Vref.
- Main/branch wire material and gauge, connector/pad capability, fuse ratings and fault-clearing behavior.
- Actual buck revision and stable 5V output under intended load; do not assume a pot setting persists after a fault.
- Four-station current/temperature/transient validation, supported parking and safe stop behavior.
- Encoders: reserve D4/GPIO6 (SDA) and D5/GPIO7 (SCL), but do not connect a generic AS5600 board until its supply configuration and pull-up voltage are confirmed. No 5V pull-ups on ESP32 GPIO. Encoder/magnet integration is part of the later calibration build, not tested by this circuit.

## Primary references

- Seeed C3 pin map / external power guidance: https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/
- Seeed C3 schematic inspected visually: https://files.seeedstudio.com/wiki/XIAO_WiFi/Resources/Seeeduino-XIAO-ESP32C3-SCH.pdf
- Allegro A4988 IC datasheet: https://www.pololu.com/file/0J450/A4988.pdf
- Pololu carrier reference (not proof of clone component values): https://www.pololu.com/product/1182
- DROK matching family: https://www.droking.com/10pcs-dc-buck-converter-5v-voltage-regulator

Validation performed: module-pin and net review against these references, four-page rendering inspection, artifact/link checks. No circuit simulator, PCB electrical-rule checker, physical inspection, or hardware measurements performed by the assistant. New sketch testing has not been compiled or run by this drawing workflow.

Reproduce with Python plus reportlab and DejaVu fonts: `python draw_schematic.py`.
