# Stations and claw on Wi-Fi for good, with over-the-air updates (2026-10-26)

After **one** USB flash per board, every board joins the home Wi-Fi by itself at power-up, at a fixed address. New
firmware then goes over Wi-Fi from the Arduino IDE, with the board still in its box on the wall.

Firmware: `firmware/winch_station/winch_station.ino` (stations) and `firmware/claw_s3/claw_s3.ino` (claw). The bench-test
sketches have no Wi-Fi updates, so the first flash of the real firmware has to be over USB.

## 1. Pick the addresses (once)

On the laptop, on the home Wi-Fi, run `ipconfig` in a Command Prompt and note two lines of the Wi-Fi adapter:

- **IPv4 Address:** for example `192.168.1.23`.
- **Default Gateway:** for example `192.168.1.1`.

Give each board a fixed address with the **same first three numbers** and a **last number nobody else uses**. High numbers
are safest; most routers hand out addresses from the low end.

| Board | Example address | `config/robot.json` |
|---|---|---|
| Station A | 192.168.1.61 | `stations[A].address = "192.168.1.61:8771"` |
| Station B | 192.168.1.62 | `"192.168.1.62:8771"` |
| Station C | 192.168.1.63 | `"192.168.1.63:8771"` |
| (Station D) | 192.168.1.64 | not needed in three-station mode |
| Claw | 192.168.1.70 | `claw.address = "192.168.1.70"` (no port) |

The network must be 2.4 GHz. The stations and the laptop must be on the same network; the stations broadcast to each
other on it.

## 2. `secrets.h` for each board (stays on the laptop, never uploaded to GitHub)

Copy `secrets.example.h` to `secrets.h` in the sketch folder, or make a new tab named `secrets.h` in the IDE. For
station A:

```cpp
#pragma once
#define STATION_ID "A"
#define WIFI_SSID "your-network"
#define WIFI_PASS "your-password"
#define STATION_IP IPAddress(192, 168, 1, 61)
#define GATEWAY IPAddress(192, 168, 1, 1)        // the Default Gateway from ipconfig
#define SUBNET IPAddress(255, 255, 255, 0)
#define OTA_PASS "pick-a-password"               // asked for at every Wi-Fi upload
```

For station B, change `STATION_ID` to `"B"` and the last number of `STATION_IP` to 62, then flash. Do the same for the other
stations. The claw's `secrets.h` has `WIFI_SSID`, `WIFI_PASS`, `OTA_PASS`, and, uncommented, `CLAW_IP` / `GATEWAY` /
`SUBNET`. Without `OTA_PASS` the sketch stops compiling with a message saying what to add.

## 3. The one USB flash (each board)

1. **Board:** XIAO_ESP32C3 for the stations (ESP32 Dev Module for an ELEGOO board); XIAO_ESP32S3 with PSRAM "OPI PSRAM" for
   the claw.
2. **Power:** USB only. For a station, JP1 must be **out**.
3. **Upload.** The Serial Monitor (115200) prints `station A 192.168.1.61 boot` (the claw prints `claw 192.168.1.70 camera=1`).
4. **Check from the laptop:** `ping 192.168.1.61`, then
   `python -m tools.commission_station --config config/robot.json --station A status`
   (claw: `python -m tools.check_claw 192.168.1.70 status`).

## 4. Box it and run without a computer

- **Station:** unplug USB, then plug **JP1 in**, and power it from 12 V. At every power-up it starts by itself, joins the
  Wi-Fi at its fixed address, and keeps retrying until the router is up. The motor stays **off** until the host arms it.
- **Claw:** battery and switch on. Same behaviour, and the orange LED blinks once a second.
- **Every session:** power strip on, wait about 10 s, then on the laptop run
  `python -m roomcleaner.cdpr.service --config config/robot.json --host 0.0.0.0 --data data/hw3` and open the printed
  address on the phone.

## 5. Updating firmware over Wi-Fi

1. **Make the board safe first.** This rule is enforced in the firmware:
   - **station:** **disarmed** (Lower, then Disarm in the app, or the service not running). An armed station does not
     listen for updates, because the update ends in a reboot and a reboot releases the motor.
   - **claw:** **grip open**, resting on the floor or a support.
2. **Pick the port.** The laptop must be on the same Wi-Fi. In the Arduino IDE go to **Tools > Port**: under *Network
   ports* you see `roomcleaner-station-A at 192.168.1.61` (and B, C, `roomcleaner-claw`). It can take up to a minute to
   appear. Pick the right board.
3. **Upload,** and type the `OTA_PASS` when asked. Progress shows in the IDE. The board reboots into the new firmware and
   rejoins the Wi-Fi.
4. **After any station update,** the host sees a new boot id and requires the reference again (a normal startup). This is
   by design: the robot never resumes on its own (D25).

**If the network port does not appear:**
- check the laptop is on the same network;
- allow the Arduino IDE (and "espota" / Python) through the **Windows firewall** when Windows asks;
- power-cycle the board;
- check the board is disarmed: an armed station hides on purpose.

**If an upload fails halfway:** the board keeps running its old firmware. Updates are written to a second slot and only
switched over when complete. Try again.

**Every update changes what runs on a robot that holds a load.** Run `tools.commission_station ... status` (and the
`direction` / `jog` checks after any motion change) before lifting again.
