# Bench assembly — the printer-free electronics build

Everything you can assemble and prove **before the 3D printer is available**,
using parts in hand (Uno kit, CNC shield + A4988s, 5× NEMA 17, 12 V PSU, fuse
kit, KW12-3 switches, MG996R servos, ESP32 boards, MP1584 bucks, camera, M3
kit, line). Work top-to-bottom; every phase ends in a **checkpoint** — don't
continue past a failed one. Cross-reference: `docs/FIRMWARE.md` (pinout +
first-power detail), `docs/APP.md` (consoles).

**Tools needed:** multimeter (required), soldering iron (switches + later the
effector), small screwdriver, wire strippers, tape.

**Safety standing orders**
- The 12 V PSU plugs into the **switched power strip** — that switch is the
  kill switch for every test below.
- Never plug/unplug a motor or a driver while 12 V is on.
- No LiPo is involved anywhere in this document (yours isn't ordered yet);
  the effector benches on USB + phone-charger power.

---

## Phase 1 — Flash the winch controller (USB only)

1. Install the Arduino IDE; Library Manager → **AccelStepper**.
2. `git pull` the repo first (a limit-switch polarity bug was fixed — you need
   the current firmware), open
   `firmware/roomcleaner_firmware/roomcleaner_firmware.ino`, board
   "Arduino Uno", upload.
3. Serial Monitor @ **115200**, line ending "Newline".

**Checkpoint:** boot prints `READY`; `?` → `POS 0 0 0 0`; `S` → `SW 1 1 1 1`
(all four report "pressed" because nothing is wired yet — that is the
fail-safe reading, and it's correct).

## Phase 2 — Dress the CNC shield (USB unplugged)

1. Under each of the 4 driver sockets install **all three** microstep jumpers
   (1/16 — must match `MICROSTEP = 16` in `roomcleaner/hardware/hw_config.py`).
2. Seat the 4 A4988s — **orientation kills**: match each driver's EN pin
   corner to the shield silkscreen; all four face the same way. The trimpot
   ends up toward the shield's power terminal on a standard V3 — verify by
   silkscreen, not by this sentence.
3. Press heatsinks onto the black driver chips (centered; touching no pins).
4. Seat the shield on the Uno (no overhung pins).

## Phase 3 — Power chain (multimeter from here on)

1. Cut the barrel plug off the ALITOVE 12 V lead; strip both wires.
2. Strip ON, meter across the wires on DC volts → find and TAPE-MARK the
   **+12 V** lead. Strip OFF.
3. Wire: **+ lead → inline fuse holder (7.5 A blade fuse) → shield power
   terminal "+"**; − lead → terminal "−". Triple-check against the shield's
   silkscreen: reversed polarity is instant death for the board.

**Checkpoint:** strip ON with USB unplugged → shield power LED lights; meter
reads ~12 V across the shield's VMOT terminal. Strip OFF.

## Phase 4 — Set driver current (Vref), motors still unplugged

Strip ON, USB in. For each driver: black probe on shield GND, red probe on
the driver's trimpot top. Adjust gently to **0.80 V** (that's ~1.0 A on
standard R100-sense A4988s — the correct derate for our 1.5 A motors; see
`docs/SHOPPING_LIST.md` driver note).

**Checkpoint:** all four read 0.80 ± 0.05 V. Strip OFF.

## Phase 5 — First motion, one motor at a time

1. Strip OFF → plug one SIMAX motor into the **X** header.
2. Strip ON → serial: `M 3200 0 0 0` = exactly one revolution (200 steps ×
   16 microsteps). `M 0 0 0 0` returns it.
3. Feel/listen: smooth, quiet holding hiss at rest, motor warm-not-hot after
   minutes. If it stutters or squeals, re-check that axis's jumpers + Vref.
4. Strip OFF, move the motor to Y; repeat with `M 0 3200 0 0`; then Z, then A
   (`M 0 0 0 3200` — the A axis is our custom D12/D13 mapping, so this
   specifically proves the 4th channel).
5. Optional but useful: label each motor 1–4 with tape and write down its
   spin direction for `+` steps (you'll set `HOME_DIR` signs per axis at rig
   assembly).

**Checkpoint:** all four shield channels each spin a motor one clean
revolution and return.

## Phase 6 — Limit switches (soldering)

1. For each of 4 switches: solder a wire tail to **C** (common) and **NC**
   (normally closed). Slip-proof with a zip tie around the pair if you like.
2. Connect: X-switch → shield X endstop pins (D9 + GND side), Y → Y (D10),
   Z → Z (D11); the 4th switch → **A3 + GND** on the aux header (check
   silkscreen; see `docs/FIRMWARE.md` pin table).
3. Serial: `S` → now `SW 0 0 0 0`. Hold each lever → its digit flips to 1,
   releases back to 0.

**Checkpoint:** four switches, each toggling only its own digit. A digit
stuck at 1 = broken wire or cold joint — the fail-safe is telling you now
instead of during a homing run.

## Phase 7 — Servo bench test (5 V tethered — no LiPo, no buck yet)

1. Sacrifice a USB cable on a 5 V phone charger: red = 5 V, black = GND.
2. MG996R: red → 5 V, brown → GND **and** a jumper from that GND to an Uno
   GND pin (common ground is mandatory); orange (signal) → Uno **A4**.
3. Serial: `G 20` then `G 140` — the horn sweeps the claw's release↔grip
   throw. `G 90` to park it mid-range. At 5 V the torque is reduced — fine
   for no-load bench proof; the real effector feeds it 6.0 V from the buck.

**Checkpoint:** clean sweeps, no chatter at rest.

## Phase 8 — Pre-set ALL the bucks to 6.0 V (do this once, now)

The MP1584 trimpots arrive at random voltages — often high enough to kill a
servo. With the 12 V bench supply available (temporarily land buck IN+ / IN−
on the shield's powered terminal or the PSU leads):

For each of the 6 bucks: power its input, meter on OUT, turn the trimpot
(often many turns) until **6.00 V**, then mark the board with a dot of
marker. Store them labeled.

**Checkpoint:** six bucks all reading 6.0 V under the same input. Never
connect a servo to an unverified buck.

## Phase 9 — Effector electronics, breadboard edition (USB-powered)

The claw's brain, benched without the claw (and without the LiPo, which is
still on the shopping list):

1. In `firmware/effector_esp32/effector_esp32.ino`, set `WIFI_SSID` /
   `WIFI_PASS` to your home 2.4 GHz network. Arduino IDE: install ESP32 board
   support (Boards Manager → "esp32"), board "ESP32 Dev Module", plus the
   `ESP32Servo` library if the sketch asks for it.
2. Flash over USB-C. Serial monitor shows dots then `WiFi: <ip-address>` —
   write that IP down.
3. Wire the servo: signal → **GPIO 13**, servo power from the phone-charger
   5 V (later: buck 6.0 V from the LiPo), grounds common with the ESP32.
4. From your laptop's browser or curl:
   - `http://<ip>/status` → JSON state
   - `http://<ip>/setup` → parks the servo at the release angle (this is the
     drum-mounting zero — you'll use it during claw assembly)
   - `http://<ip>/grip` and `/release` → the servo sweeps.

**Checkpoint:** grip/release over WiFi with nothing but a USB cable powering
the board. This is the entire wireless-claw control path proven; the LiPo +
buck + switch just make it cordless later.

## Phase 10 — Camera (already verified live)

The innomaker is **index 1** (`python -m scripts.camera_view --list` to
re-check). `python -m scripts.live_app --camera 1` → http://localhost:8000
for the live perception console; `python -m roomcleaner.app --sim` →
http://localhost:8010 to fly simulated missions.

---

## What this bench phase deliberately leaves out

| Waiting on | Item |
|---|---|
| 3D printer access | corner mounts, spools, claw frame/hub/standoffs, controller case, camera bracket |
| TPU (unordered) | the five fingers |
| LiPo + balance charger + slide switch (unordered) | cordless effector |
| Servo horn measurement (calipers) | tendon drum print |
| Room measurement | real coordinates in `config.py`, raceway quantity |

When the printer is back: print the fit-test pair first (one spool, one
corner mount), then it's rig-assembly time — that sequence is
`cad/README.md` + `docs/FIRMWARE.md`.
