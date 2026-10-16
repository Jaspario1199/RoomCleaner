# Motor station electrical bring-up — Rev B

## Progress addendum — 2026-10-16

The user has now identified the ALITOVE 12 V / 6 A supply and red A4988 carrier, reported motor coil pairs identified, measured buck/XIAO power rails (5.00 V / approximately 4.7 V / 3.3 V), confirmed USB serial execution on the ESP32-C3, and confirmed switch released/pressed readings. These are user-reported bench results, not suspended-motion validation. Capacitor installation, current limit, encoder operation and motor motion remain unverified in the record. WAGOs were not yet available during the last reported switch wiring; the earlier on-hand statement below was corrected in conversation.

The selected floor-start, visual calibration and bead-verification development plan is now [Startup calibration V1](STARTUP_CALIBRATION_V1_20261016.md). It is a new proposed mode; existing detached homing remains restricted to its original use.

## Inventory correction — 2026-10-14

The supplied Amazon history establishes an **A4988 four-driver kit**, three **XIAO ESP32-C3s**, three older **ELEGOO ESP-WROOM-32s**, six **DROK buck modules**, and an **ATC/ATO blade fuse holder/fuse assortment** as marked delivered. User also confirms WAGOs and holders are on hand. See [inventory reconciliation](INVENTORY_RECONCILIATION_20261014.md) for quantities, evidence and pending deliveries.

The next station is therefore based on a C3 and an actual A4988 carrier, subject to board inspection. The older DRV8825 wiring and firmware are not directly applicable: A4988 needs logic VDD, has different microstep selection, lacks the same nFAULT interface, and needs a carrier-specific current-limit calculation. No A4988 firmware or wiring has been validated by this inventory update. Purchased fuse/regulator/connector envelopes differ from the earlier CAD candidates.

The original Rev A planning text follows for provenance; generic bring-up sequencing still applies, but its component uncertainty is superseded by the inventory record. Remaining photos are for board revisions and markings, not to re-establish the known product families.

Recorded 2026-10-14. Status: assembly plan, not a hardware test report.

User reports the motor-station electrical components have shipped. Exact received models, quantities and condition are not yet verified. Do not substitute the claw XIAO ESP32-S3 camera board for an assumed station board. Earlier local station documents specify XIAO ESP32-C3 and DRV8825; the original central controller used A4988. Identify actual parts before choosing the pin map or current-limit formula.

## One-station topology

External isolated 12 V DC supply feeds a source-protected branch to the station. Inside, the positive supply splits to driver VMOT and the input of a 12-to-5 V buck regulator. The driver feeds the two motor coils through four motor wires. The regulator powers the ESP32 through the board's required external-power isolation. Driver, regulator, ESP32 and sensors share ground. The ESP32 sends STEP, DIR and ENABLE to the driver; it does not power the motor through GPIO.

An NC homing switch connects a GPIO to ground with a 3.3 V pull-up. An optional AS5600 encoder uses local 3.3 V-compatible power and I2C; verify breakout pull-ups before connection. The suspension line carries no electrical power. Network control follows single-axis commissioning, not before it.

## Sequence and acceptance criteria

1. Identify ESP32 board, driver carrier (both sides), buck regulator, supply output label and motor model/current. Confirm multimeter availability and whether encoders are included. Keep power disconnected while identifying and wiring.
2. Connect only the ESP32 to a USB data cable. Confirm board identity, upload and serial output. Leave the external 5 V feed disconnected at this stage.
3. Test the regulator separately on 12 V. Meter-check polarity and approximately 5.00 V output before connecting logic. Do not route motor current through solderless breadboard rails or thin logic jumpers.
4. Assemble driver power and local electrolytic capacitor, observing polarity. Prior candidate is 100 uF/50 V. Pololu requires at least 47 uF near VMOT for its DRV8825 carrier; long supply leads make this particularly important. Verify the actual module requirements.
5. With all power off, identify the two motor coil pairs using resistance measurements. Connect each pair to one driver bridge. Secure the motor and remove spool load for first motion.
6. Select the actual board's current-limit procedure and conservative limit at or below the motor/driver thermal limits. Do not apply the Pololu DRV8825 formula to an unidentified clone or A4988. Check RESET, SLEEP, microstep straps and startup-disabled ENABLE wiring.
7. Run short, slow, unloaded moves in both directions. Verify direction, supply stability and driver/motor temperature. Never connect or disconnect a motor while its driver is powered.
8. Test the NC switch electrically before homing. Verify normal, pressed and disconnected states; confirm bounded travel and correct stop direction with no suspended load.
9. If fitted, validate encoder magnet diagnostics, direction, counts per revolution and stationary jitter. Then compare commands with measured rotation. Encoder rotation does not establish cable traction or payload movement.
10. Repeat the verified wiring on the other stations. Coordinated four-cable motion requires a separate network timing, emergency stop and recovery qualification.

The existing `firmware/local_station/` adapter is experimental and requires an encoder and heartbeat; it is not a generic plug-and-play motor jog sketch. Its documentation reports portable core tests but no real-board compilation or hardware execution. Do not bypass those interlocks to run the suspended robot.

## Information needed before exact wiring

- Clear front/back photographs or exact product links for ESP32, driver and buck board.
- Power supply DC output voltage/current label.
- Motor part number/current rating; wire colors alone do not identify coils.
- Whether a multimeter, local capacitor, branch protection and encoder are available.

Sources: https://www.pololu.com/product/2133 ; https://www.pololu.com/product/1182 ; https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/ . Checked 2026-10-14. Existing detailed candidates: `LOCAL_STATION_HARDWARE_20261004.md` and `LOCAL_STATION_CONTROL_20261004.md`.
