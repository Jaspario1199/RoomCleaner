# Claw bench test (Rev B breadboard, XIAO ESP32-S3 Sense)

`claw_bench_test.ino` checks the claw circuit one part at a time from the Serial Monitor, and serves the camera as a
live web page. It is not the claw firmware: flash `firmware/claw_s3/claw_s3.ino` again when everything passes.
**Not compiled in this workspace** (no Arduino toolchain), so compile it on your laptop first.

**Setup (Arduino IDE):**
- **Board:** esp32 > **XIAO_ESP32S3**. Under Tools, set **PSRAM: "OPI PSRAM"**; the camera fails without it.
- **USB CDC On Boot: Enabled**, so the Serial Monitor works over USB.
- **Libraries:** none beyond the esp32 core.
- **Wi-Fi:** copy `secrets.example.h` to `secrets.h` in this folder and fill in your **2.4 GHz** network.
  `secrets.h` is git-ignored.
- **Serial Monitor:** 115200 baud, line ending "Newline". Type a letter and press Enter.

## Order

| Step | Power | Type | Pass |
|---|---|---|---|
| 1. Boot | USB only, battery off | (reset) | menu prints; the orange LED blinks once a second |
| 2. Camera | USB | `k` | "captured 640x480 JPEG"; the boot message names the sensor |
| 3. Wi-Fi + live view | USB | `n` | prints `http://<ip>/`; open it on your phone or laptop (same network): live video |
| 4. Battery | USB + battery ON | `b` | 6.8-8.4 V, within about 0.1 V of a meter on the pack |
| 5. Servo center | USB + battery, horn OFF the claw drum | `m` | servo moves to the middle and holds |
| 6. Servo travel | same | `+` / `-` | moves in 50 us steps; note the open and closed values for your claw |
| 7. Servo off | | `x` | the servo goes limp |
| 8. Battery only | unplug USB | | LED keeps blinking; the camera page still works at the same address |

The servo gets no signal at boot, so it does not jump when the board starts. Test `o` / `c` (900 / 2000 us) only after
`+` / `-` show the claw can travel that far. Write your measured open and closed values into
`SERVO_OPEN_US` / `SERVO_CLOSED_US` in `claw_s3.ino`.

**If anything gets hot or the servo buzzes against a stop: type `x` and switch the battery off.**
