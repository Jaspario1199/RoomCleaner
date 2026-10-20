"""firmware/claw_s3 against host stand-ins (tests/firmware/claw_stubs): decision D27 (no IMU on the claw).

This is NOT an ESP32 build (arduino-cli / the ESP32 core are not available here); it compiles the sketch with
-Wall -Wextra -Werror against minimal stubs of the Arduino API, runs setup()/loop() and calls the HTTP handlers.
It checks what the host depends on: /status is valid JSON with no attitude fields, /grip obeys (no tilt gate) and
rejects bad parameters without moving the servo, nothing of the MPU-6050 is left."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "firmware" / "claw_s3"
STUBS = Path(__file__).parent / "claw_stubs"
SRC = (FW / "claw_s3.ino").read_text()


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    if shutil.which("g++") is None:
        pytest.skip("g++ not installed")
    d = tmp_path_factory.mktemp("claw")
    shutil.copy(FW / "claw_s3.ino", d / "claw_s3.ino")
    shutil.copy(FW / "secrets.example.h", d / "secrets.h")
    exe = d / "claw"
    r = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", f"-I{d}", f"-I{STUBS}",
                        str(STUBS / "harness_main.cpp"), "-o", str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]

    def run(*requests):
        out = subprocess.run([str(exe), *requests], capture_output=True, text=True, timeout=10, check=True)
        lines = [json.loads(line) for line in out.stdout.splitlines()]
        run.boot_servo_us = lines[0]["boot_servo_us"]          # servo pulse right after setup()/loop()
        return lines[1:]
    return run


def test_no_imu_left_in_the_sketch():
    code = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)           # the header comment may say why there is no IMU
    code = "\n".join(re.sub(r"//.*", "", ln) for ln in code.splitlines())
    for word in ("Wire", "mpu", "imu", "tilt", "roll", "pitch", "I2C", "0x68", "GRIP_TILT"):
        assert not re.search(word, code, re.I), f"{word!r} still in the sketch code"


def test_status_is_valid_json_without_attitude_fields(harness):
    (st,) = harness("/status")
    assert harness.boot_servo_us == 900                         # power-up: open
    assert st["code"] == 200
    d = st["body"]
    for k in ("online", "t_us", "battery_v", "battery_low", "grip_closed", "servo_us", "camera_ok", "camera_mode",
              "frame_id"):
        assert k in d, k
    for k in ("roll", "pitch", "tilt_rad", "imu_ok"):
        assert k not in d, f"{k} must be gone from /status (D27)"
    assert d["online"] is True and d["grip_closed"] is False and d["servo_us"] == 900
    assert d["battery_low"] is False and abs(d["battery_v"] - 7.8) < 0.01


def test_grip_obeys_with_no_tilt_gate(harness):
    a, b, c, d = harness("/grip?close=1", "/status", "/grip?close=0", "/status")
    assert a["code"] == 200 and a["body"] == {"ok": True, "grip_closed": True} and a["servo_us"] == 2000
    assert b["body"]["grip_closed"] is True and b["body"]["servo_us"] == 2000
    assert c["code"] == 200 and c["body"]["grip_closed"] is False and c["servo_us"] == 900
    assert d["body"]["grip_closed"] is False


def test_grip_with_bad_parameters_never_moves_the_servo(harness):
    out = harness("/grip?close=1", "/grip", "/grip?close=2", "/grip?close=", "/grip?x=1", "/grip?close=yes")
    assert out[0]["servo_us"] == 2000                           # closed by the first, untouched by the rest
    for r in out[1:]:
        assert r["code"] == 400 and r["body"]["ok"] is False and r["servo_us"] == 2000


def test_servo_stays_inside_its_limits_and_setup_parks_open(harness):
    out = harness("/grip?close=1", "/setup")
    assert out[0]["servo_us"] == 2000 and 600 <= out[0]["servo_us"] <= 2400
    assert out[1]["code"] == 200 and out[1]["servo_us"] == 900
