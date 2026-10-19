# Plug-in station architecture — proposal, not implemented

User goal: install stud dock, slide on fully assembled station, connect one external plug; no internal wiring during installation. The old four-conductor motor extension does not achieve this by itself.

## Current bench wiring

12V supply feeds the central Uno/CNC shield/A4988 drivers. Four phase conductors run from each driver to its NEMA17. Each NC home switch has a separate signal/return to the central controller. The local XIAO reads its AS5600 via short3.3V/I2C wiring, uses separate5V USB power and sends encoder telemetry over WiFi. A mechanical switch is a contact, not an independently powered load. Motor phase wiring must not be used as an electronics DC supply.

## Alternatives

| Architecture | One external connection | Station changes | Main consequence |
|---|---|---|---|
| Existing central drivers with combined harness | Keyed hybrid connector:4motor+2home+2DC-power conductors | Panel connector, strain relief and optional12V→5V local regulator | Keeps existing motion firmware; eight-contact custom cable still carries chopped phase current. Connector/cable/current/voltage-drop qualification required |
| Fully self-contained station | DC input with WiFi, or one combinedDC+differential-data cable | Local motor driver, XIAO/controller, regulated logic supply, protective components and mounts | Short motor/switch/encoder leads; coordinated local motion, fault handling and central synchronization must be developed |

Recommended product direction: fully self-contained stations, one central external low-voltage PSU/distribution hub with protected branches, one accessible keyed retained plug per station. Start from12V compatibility with existing hardware; validate actual supply demand and line voltage drop before fixing PSU/cable/connector ratings. Four wall adapters are optional but add outlets/cables and complicate collective power control. Local controllers should execute coordinated buffered trajectories; WiFi should not directly determine individual step pulse timing. Wired data is an option for a combined power/data connector; its protocol/transceivers/topology remain to select.

Existing four XIAO encoder nodes may be reused as station controllers if GPIO, boot pins, real-time firmware and timing analysis support it. They currently only report encoder data; local motor control is not implemented. The current CAD has no released local driver/regulator/connector brackets or validated thermal clearance. Do not infer that the new electronics fit because the case has empty volume.

## Before CAD/BOM freeze

Select exact driver carrier, regulator and connector/cable. Measure peak/continuous input current, actual motor running torque, driver temperature, supply transients and branch voltage drop at room-length wiring. Add input protection/decoupling and service/programming power isolation. XIAO's5V input is not a12V input; follow Seeed's external-power/backfeed guidance. Define axis IDs, synchronized trajectory start, encoder comparison, local NC homing, timeouts and all-axis coordinated fault response. Retest sensor field with powered driver/motor, EMC and enclosure heat.

Connecting/disconnecting motor phases with an energized A4988 can damage it. The removable station is serviced unloaded and with motor power off; a locking connector alone does not make it hot-swappable. DC-only local stations also lose motor holding torque on unplugging.

The proposed architecture is not in the current bench print release. Hold the motor-only extension purchase decision until this architecture is chosen. Existing extensions can still serve the central-driver bench setup if connector pinout and wire/current rating are verified.

Primary references:
- [Pololu A4988 power/logic/current/decoupling and powered motor-disconnection guidance](https://www.pololu.com/product/1182)
- [Seeed XIAO ESP32C3 supply, GPIO and external-power isolation guidance](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/)
