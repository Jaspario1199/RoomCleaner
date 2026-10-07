# Independent local-station firmware review — 4 October 2026

Scope: `firmware/local_station/motion_core.h`, `local_station.ino`, selected electrical contract and existing portable C++ scenarios. Detached single-axis controller only; this review does not qualify coordinated suspended operation.

## Concrete defects found and corrected by the implementation owner

| ID | Original problem | Corrective behavior reviewed |
|---|---|---|
| LS-01 | `sscanf` converted a delta to platform `long` before checking its range; oversized decimal input could overflow before rejection. | Explicit `MOVE ` prefix, `strtol`/`strtod`, conversion-error checks, range bounds and complete trailing-input validation. Numeric parsing no longer relies on overflowing scanf conversions. |
| LS-02 | Single sampled NC openings could advance Seek/Refine; a transient Refine edge immediately set zero and accepted homing. | Homing transitions require a stable 10ms edge. Raw unexpected openings still stop ordinary motion immediately. |
| LS-03 | Final commanded pulse immediately returned Idle, permitting another move without measured arrival. | Settle mode requires encoder error within four counts for 50ms and faults after 500ms without confirmation. MOVE rejects while settling. |
| LS-04 | GPIO20 nFAULT is also UART0 RX; a non-USB Serial build could conflict with fault input. | Compile guard requires `ARDUINO_USB_CDC_ON_BOOT`. An actual supported XIAO ESP32-C3 USB build remains required. |
| LS-05 | HOLD could cancel Settle while preserving homed status, bypassing arrival verification. | HOLD during Move/Settle invalidates homing. Rehoming is required before another move. Owner added a regression scenario. |

## Independently executed checks

Compiled and ran the actual core with `g++ -std=c++11 -Wall -Wextra -Werror -fsanitize=undefined`. The baseline reported **14 scenarios passed**. The additional reproducible source `tests/local_station/test_review.cpp` reported **four fresh debounce/arrival scenarios passed**:

1. A one-tick Seek opening does not initiate Backoff or establish home.
2. A one-tick Refine opening followed by a closed switch does not establish home, including subsequent closed samples.
3. A stalled ten-step move enters Settle, rejects another move and eventually faults Tracking with homing invalidated.
4. A physically followed move enters Settle and reaches Idle only after the encoder confirmation interval.

These are executable probes against the C++ implementation, not a second mathematical model. They do not compile the Arduino/Wire/USB adapter or emulate its hardware. `pytest` was unavailable in this review agent's default Python runtime, so the portable tests were invoked directly; the implementation owner ran its configured pytest suite separately.

## Electrical and adapter assessment

AS5600 addresses and raw-angle/status interpretation are consistent: register0x0B, magnet-detected bit0x20, invalid weak/strong bits0x18, raw-angle registers0x0C/0x0D and 12-bit masking. Modular unwrapping assumes less than half a revolution between valid samples. At the stated bench speed and 5ms nominal polling that assumption is reasonable; disconnected/unreliable I2C faults rather than supplying trusted motion.

Heartbeat and encoder-age checks use unsigned timer subtraction. Motion emits at most one pulse per tick, faults instead of burst-catching-up, and bounds homing travel. Faults retain ENABLE and invalidate home, matching the documented holding policy; this is not a brake and cannot maintain tension after driver/power failure. NC disconnection reads open, so bounded release/reseek is important; wiring cannot distinguish an actual pressed switch from a broken wire from its instantaneous level alone.

GPIO mapping, DRV8825 1/16 mode strap, external enable pull-up, common grounds, nearby bulk capacitor and external5V/USB isolation are specified. The document appropriately leaves fuse coordination, thermal capacity, soldered harness geometry, lead bend clearance and purchased-board restraints unqualified. Do not convert manufacturer open-air current capability into an enclosure rating.

## Remaining qualification gates

- Compile the actual sketch for the supported XIAO ESP32-C3 USB-CDC target; verify I2C API overloads, USB startup and final pin configuration.
- Measure GPIO pulse widths/direction setup, polling jitter and USB/I2C stall behavior on the powered board. Inject lost heartbeats, driver faults, encoder disconnects and switch-wire breaks.
- Include 10ms debounce travel and real stopping behavior in the measured bead/collar switch margin. Bench defaults are not calibrated cable positions.
- Verify stable actual magnet diagnostics, encoder polarity and motor microstep ratio; four-count endpoint tolerance is a declared angular tolerance, not exact cable displacement.
- Qualify power isolation, current limit, fuse/source protection, transient behavior and enclosed prolonged holding temperature.
- Keep this profile detached: no four-axis synchronization, machine-wide emergency stop, load-holding brake or recovery after power loss has been established.

No further implementation edits were made by this review agent. This report describes corrected nominal behavior and specific hardware tests still required; it does not certify the station for overhead use.
