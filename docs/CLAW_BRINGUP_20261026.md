# Claw bring-up: bench test → claw firmware → host → phone app (2026-10-26)

Status on 10/26: the Rev B claw breadboard passes the bench test (`firmware/claw_bench_test`) on Jasper's bench. Camera
live view works, the battery reads 7.2 V, and the servo moves. This page is the order from here to the phone app.

## 1. Flash the claw firmware (`firmware/claw_s3/claw_s3.ino`)

- **Board and libraries:** board XIAO_ESP32S3, PSRAM OPI PSRAM, USB CDC On Boot Enabled. No extra libraries: as in the
  bench test, the servo now runs on LEDC timer 1, so ESP32Servo is gone.
- **`secrets.h`:** copy `secrets.example.h` to `secrets.h` in that folder, with the same Wi-Fi as the bench test.
- **Fixed address, recommended:** the host config must know the claw's address. Uncomment `CLAW_IP` / `GATEWAY` /
  `SUBNET` in `secrets.h`, with an IP outside the router's DHCP range and the same first three numbers as your laptop.
  The alternative is to reserve the claw's address in the router.
- **Boot:** the Serial Monitor prints `claw <ip> camera=1`. The orange LED blinks once a second. The servo goes to OPEN
  (900 µs) at power-up: **take the horn off the drum, or check the claw can be fully open, before the first boot.**

## 2. Check it from the laptop (no stations needed)

```
python -m tools.check_claw <claw-ip> status          # online, battery, camera, grip
python -m tools.check_claw <claw-ip> frames --n 5    # JPEGs in data/claw_check/ (exactly what the host receives)
python -m tools.check_claw <claw-ip> all             # status + frames + open / close / open (asks first)
```

- **Records:** every run appends to `data/commissioning/claw.jsonl`.
- **Camera calibration photos:** `frames --n 40`, moving the ChArUco board around, captures them in the right mode
  (SVGA 800×600, the mode the firmware is fixed to). Calibrate with
  `python -m tools.calibrate_camera calibrate --images data/claw_check --square-mm <measured> --out config/camera.json`.
  Use only the board photos for this.
- **Servo end points:** `SERVO_OPEN_US = 900` / `SERVO_CLOSED_US = 2000` are not measured yet. Measure them with the
  bench test's `+` / `-` on the assembled claw (fingers fully open; curled with no stall), write them into
  `claw_s3.ino` and flash again.

## 3. Practise with the phone app in simulation (nothing connected)

```
pip install -r requirements-app.txt
python -m roomcleaner.cdpr.service --sim --host 0.0.0.0 --port 8100
```

Open the printed `http://<laptop-ip>:8100/?token=...` on the phone, on the same Wi-Fi. It shows the same tabs as the
real robot: Home, Camera, Setup, Chat. See `docs/APP.md`.

## 4. The real app (`--config config/robot.json`): what still has to exist

The hardware service (`service.build_hardware_context`) builds a context only if every piece below is in place. It
refuses to start otherwise.

| Needed | Where | Status 10/26 |
|---|---|---|
| Every active station's `address` = `"<STATION_IP>:8771"` | `config/robot.json` `stations[].address` | Bench tests pass; stations not yet flashed with `winch_station.ino` / on the network |
| `claw.address` = `"<CLAW_IP>"` (no port) | `config/robot.json` `claw.address` | After step 1 |
| `camera.intrinsics_file` | `config/camera.json` from step 2 | Not done |
| `marker.edge_m` (printed tag, measured) | `config/robot.json` | Not done |
| `claw.mass_kg` (weighed, with battery) | `config/robot.json` | Not done |
| Per-station commissioning (`tools.commission_station`) | `data/commissioning/<id>.jsonl` | Not done |

`config/robot.json` is a copy of `config/robot.example.json`, or of `robot.three.example.json` for three stations. Then:

```
python -m roomcleaner.cdpr.service --config config/robot.json --host 0.0.0.0 --data data/hw1
```

Next bounded task: flash `winch_station.ino` on station A, put it on the same network, and run `commission_station`
`status` / `direction` / `jog`. Then do the same for the other stations.
