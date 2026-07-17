# RoomCleaner — Firmware & the Host↔Arduino Bridge

How the software brain (your computer) drives the motors (the Arduino). The
computer does all the kinematics and planning; the Arduino is a dumb, reliable
motor executor.

```
  computer (Python)                              Arduino Uno + CNC shield
  ┌───────────────────────────┐   USB serial    ┌────────────────────────┐
  │ vision -> plan -> positions│ ───────────────▶│ 4x DRV8825 steppers    │
  │ cable lengths -> steps     │  H / M / G      │ + gripper servo        │
  │ (hardware/driver.py)       │ ◀───────────────│ homing on limit switches│
  └───────────────────────────┘  HOMED/DONE/OK   └────────────────────────┘
```

## Wireless effector — the claw has no wire to it

The gripper servo does **not** run to the central Arduino. Instead the effector
carries its own **ESP32 + LiPo battery**, and the host commands it over WiFi. Only
the 4 Dyneema cables touch the claw — nothing electrical crosses the room.

```
  computer ──USB──▶ Arduino (4 winch motors, wired)
      │
      └──WiFi──▶ ESP32 on the claw ──▶ gripper servo (on battery)
```

- **Firmware:** `firmware/effector_esp32/effector_esp32.ino` — joins your WiFi,
  serves `GET /grip` / `GET /release`, drives the servo. Set your SSID/password
  and the servo pin at the top. Needs the **ESP32Servo** library.
- **Host:** `hardware/gripper.py::WiFiGripper` sends those HTTP requests. Point
  `EFFECTOR_HOST` in `hw_config.py` at the ESP32's IP or `roomcleaner-claw.local`.
- **Why this is safe to do wirelessly:** grip/release are just "close now" /
  "open now" — not the tightly-synchronized motion the winches need — so WiFi
  latency is invisible here.

Wiring it together in code (motors wired, gripper wireless):

```python
from roomcleaner.hardware.driver import SerialDriver
from roomcleaner.hardware.gripper import WiFiGripper
from roomcleaner.hardware.executor import run_on_hardware

driver = SerialDriver(robot, port="COM3", home_lengths=measured).open()
claw = WiFiGripper(host="roomcleaner-claw.local")
run_on_hardware(robot, controller, driver, gripper=claw)   # motors serial, grip WiFi
```

Power on the effector: a ~1000 mAh LiPo feeds the servo through a 5–6 V buck; a
TP4056/2S board charges it. A full session runs on one charge; optionally add
charging contacts at the rest/dock pose so it tops up whenever it parks.
(Wired fallback: `SerialGripper(driver)` keeps the servo on the Arduino instead.)

## The two pieces (winch side)

- **Firmware** — `firmware/roomcleaner_firmware/roomcleaner_firmware.ino`. Flash
  it with the Arduino IDE (install the **AccelStepper** library first). It drives
  the 4 winch steppers + the servo and homes on the limit switches.
- **Host driver** — `roomcleaner/hardware/`. `driver.py` converts effector
  positions → winch step counts and speaks the serial protocol; `executor.py`
  streams a whole plan; `hw_config.py` holds the tunables.

## The protocol (newline ASCII — debuggable in any serial monitor)

| Host → MCU | MCU → Host | Meaning |
|-----------|-----------|---------|
| `H` | `HOMED` | home all winches to their switches |
| `M a b c d` | `DONE` | move winches to absolute step counts |
| `G <deg>` | `OK` | set gripper servo angle |
| `?` | `POS a b c d` | query current step counts |

## How a position becomes steps

```
steps_i = round( (cable_length_i(P) - HOME_CABLE_LENGTHS[i]) * STEPS_PER_M )
STEPS_PER_M = STEPS_PER_REV * MICROSTEP / (pi * DRUM_DIA)   # ~50,930 with defaults
```

`HOME_CABLE_LENGTHS[i]` is the length of cable i **when its winch is homed against
the switch** (the shortest length). Every reachable position pays cable *out* from
there, so operating step targets are positive. **Calibrate this after building**
(measure each cable at home) — until you do, the dry-run uses a placeholder and
you'll see some negative step values, which is expected.

## Try it with NO hardware

```bash
python -m scripts.hardware_dryrun
```

Runs the full plan through a `MockDriver` and prints the exact `H / M / G`
commands the Arduino would receive. This is how you sanity-check the motion +
gripper stream before wiring anything.

## Drive the real robot

```python
from roomcleaner.hardware.driver import SerialDriver
from roomcleaner.hardware.executor import run_on_hardware
# ...build robot + controller as usual...
driver = SerialDriver(robot, port="/dev/ttyUSB0",           # COM3 on Windows
                      home_lengths=measured_home_lengths).open()
run_on_hardware(robot, controller, driver)                   # homes, then executes
```

`pip install pyserial` for the serial transport.

## Pin map (CNC Shield V3, GRBL layout, 4th axis on D12/D13)

| Function | Pin(s) |
|----------|--------|
| Enable | D8 (active LOW) |
| Step X/Y/Z/A | D2 / D3 / D4 / **D12** |
| Dir X/Y/Z/A | D5 / D6 / D7 / **D13** |
| Limit switches X/Y/Z/A | D9 / D10 / D11 / **A3** |
| Gripper servo | **A4** |

Because the 4th stepper uses D12/D13 (normally the spindle pins), the 4th limit
switch and the servo move to the analog pins. **Verify against your board's
silkscreen**, and set the microstepping jumpers under the DRV8825s to match
`MICROSTEP` in `hw_config.py`.

## First-power checklist (do this in order)

1. **Set the DRV8825 current limit** (Vref ≈ 0.75 V for the 1.5 A motors) with the
   motors *powered but not yet homing*. Too high = they cook.
2. **Check each motor's direction** — send a small `M` and confirm the cable reels
   the way you expect; flip `HOME_DIR[i]` / the dir wiring if not.
3. **Test each limit switch** — `?` / a serial monitor; confirm it reads triggered
   only when pressed.
4. **Home with the effector low and clear**, watching each winch; keep a hand on
   the switched power strip.
5. Only then run a full plan — and never with anyone under the workspace.
