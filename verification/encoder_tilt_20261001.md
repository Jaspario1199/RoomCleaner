# Encoder and tilt revision validation — 2026-10-01

- Host regression:306tests passed, including real UDP relay stop on stale samples, reboot/identity/field/sequence handling, C++ encoder ratio/tolerance/unwrapping functions, and tilt pickup gates.
- Uno compiled/linked:Arduino AVR1.8.8,AccelStepper1.64,Servo1.3;21188bytes flash,844bytes static RAM. Diagnostics moved to flash to leave1204bytes for runtime.
- XIAO ESP32-C3 compiled/linked:ESP32core3.3.12;968585bytes flash,37908bytes static RAM.
- Clamp ESP32 compiled/linked:ESP32core3.3.12,ESP32Servo3.2.1;997107bytes flash,51220bytes static RAM.
- Winch nominal collision audit:2682sampled checks;clamp:4037. Cover extraction, spool/cup envelopes, homing stroke and clamp mechanism included. Actual wires/ties and magnetic field quality are not modeled.
- CAD export:valid solids and STEP volume round trips;13oriented winchSTLs;actual mesh previews inspected.
- No hardware connected or commissioned. No physical stop timing, magnetic runout/field, IMU accuracy, electrical/thermal/load, print-fit or suspended orientation test performed.
- Live planner retains point geometry. Tilt is a calibrated settled pickup gate, not active leveling or continuous motion monitoring. Encoder watchdogs inhibit/stop, not automatic corrective servo control.
