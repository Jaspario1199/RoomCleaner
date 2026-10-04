# Experimental local station control — 2026-10-04

This revision provides a **detached, unloaded, single-station bench controller**, not a synchronized four-cable robot. Existing central-controller firmware and encoder telemetry remain intact. Never substitute this sketch into suspended operation.

## Electrical contract

XIAO ESP32-C3: STEP GPIO3, DIR GPIO4, active-low ENABLE GPIO5, NC home GPIO10, driver nFAULT GPIO20, AS5600 SDA6/SCL7. Add an external 10k ENABLE pull-up to 3.3V so reset leaves the driver disabled. Connect NC switch between HOME and ground: rest closed, activation open. A broken wire also reads open; bounded release and reseek must succeed before homing is accepted.

DRV8825 RESET/SLEEP connect to3.3V. MODE0/1 low and MODE2 high selects1/16 (200 full steps/revolution assumed, verify motor). Current limit must be measured and set to the motor rating; firmware cannot set the potentiometer. Keep local VMOT capacitor near the driver. Power-off before motor connection changes. Isolate external5V from USB using the manufacturer-recommended Schottky arrangement. All grounds common. No mains inside the printed housing.

## Serial protocol

Select the XIAO ESP32C3 board with USB CDC On Boot enabled. The sketch rejects non-CDC configurations because UART0 RX would conflict with GPIO20 nFAULT.115200 baud, newline commands. `ARM BENCH`, `HOME`, `MOVE <signed microsteps> <microsteps/sec>`, `HOLD`, `DISARM`, `STATUS`, `HB`. MOVE requires completed homing and accepts at most32000 microsteps per command and1000 microsteps/sec. Send HB more frequently than500ms. HOLD during movement or settling invalidates homing and requires HOME before another move. Do not use DISARM on a supported load: it removes holding torque. Faults latch, stop pulses, retain ENABLE, and invalidate homing; reset requires intentional disarm/rearm. An enabled driver cannot guarantee holding torque after driver thermal/electrical failure.

Homing seeks at320 microsteps/sec, backs off256 steps, then reseeks at80. Maximum seek6400 steps. Homing edges must remain stable for10ms. After a MOVE final pulse, a settling state requires encoder error≤4 counts for50ms before accepting another move; failure to settle within500ms faults. Defaults are conservative **unmeasured bench placeholders**, not bead-position calibration or cable-length limits. Measure travel, switch stroke, direction and motor step angle before use. Positive encoder motion must match commanded positive steps; change encoderSign only after detached direction validation.

Encoder checked every5ms: magnet detected, neither weak nor strong diagnostic asserted. Encoder missing/stale30ms, driver fault, heartbeat loss, unexpected home opening, motion loop delay>10ms, and tracking error>64 counts lasting150ms stop pulses. AS5600 position is shaft rotation, not proof that the cable did not slip or that the payload moved. Video confirmation remains required.

## Verification and remaining gates

Portable C++ core:14 simulated scenarios passed with compiler warnings treated as errors and address/undefined-behavior sanitizers (leak detection disabled because the container cannot inspect process tasks). These cover homing, exact endpoint, stalled motion, invalid encoder, driver fault, heartbeat loss, delayed loop, stuck-open/stuck-closed home, unexpected switch, invalid speed/overflow, timer wrap and invalid configuration, opposite encoder direction and explicit hold.

The Arduino adapter has **not** been compiled with an ESP32 toolchain or exercised on hardware. USB command handling and I2C/pulse timings need real-board verification. Debounce duration, cable limits and spool-radius compensation remain physical commissioning requirements. Hard stops must prevent damage even if firmware fails.

Four-station network synchronization, a coordinated emergency stop, controlled startup/recovery and the host motion planner are not implemented in this experimental revision. Existing mission firmware remains the active baseline; a single power plug does not make these four independent loops a synchronized machine.
