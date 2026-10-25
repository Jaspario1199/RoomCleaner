# Station bench test (Rev D breadboard, ELEGOO ESP32 or XIAO)

`station_bench_test.ino` checks one part at a time from the Serial Monitor before the station firmware goes on. It does not
use Wi-Fi or the host. Not compiled in this workspace (no Arduino toolchain): compile on your laptop first.

**Upload:** Arduino IDE, board "ESP32 Dev Module" (ELEGOO) or "XIAO_ESP32C3"; Serial Monitor 115200 baud, line ending "Newline".
Power from USB with **JP1 out** the whole time. Type a letter and press Enter.

## Order

| Step | Power | Type | Pass |
|---|---|---|---|
| 1. Boot | USB only, 12 V off | (reset) | ESP32 LED on, board cool; the menu prints |
| 2. Homing switch | USB only | `w`, press the switch | reads `rest` (LOW) at rest, `PRESSED` (HIGH) when pressed |
| 3. Encoder | USB only | `i`, then `s` | device at 0x36; `magnet DETECTED`, not too weak or strong |
| 4. Encoder turns | USB only | `w`, turn the spool by hand | angle changes smoothly 0-4095 and wraps |
| 5. Driver off at boot | USB + 12 V on (Vref set to 0.80 V first) | (reset) | the motor does not move or hold |
| 6. Enable | USB + 12 V | `e` | the motor holds (hard to turn by hand) |
| 7. Jog | USB + 12 V | `f`, `b` | a quarter turn each way; encoder moves about 1024 counts direct (about 341 with `g` = 3:1) |
| 8. One spool turn | USB + 12 V | `t` | encoder within 60 counts of 4096: `PASS`; note the sign it prints |
| 9. Disable | | `d` | the motor turns freely again |

The sign from step 8 is what `drive.step_sign` / `encoder.sign` must agree on in `config/robot.json`.

**If anything gets hot or the ESP32 LED goes out: unplug at once.** That is a 3.3 V short (see the rail bridges, R4 and the
homing-switch wires).
