"""The XIAO-C3 station sketch must at least build and run setup/loop on the host
against minimal Arduino stubs (catches API drift between the sketch, the
hardware headers and station_core.h). This is NOT an ESP32 build."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "firmware" / "winch_station"
STUBS = Path(__file__).parent / "arduino_stubs"


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not installed")
def test_station_sketch_builds_against_stubs(tmp_path):
    shutil.copy(FW / "winch_station.ino", tmp_path / "winch_station.ino")
    shutil.copy(FW / "secrets.example.h", tmp_path / "secrets.h")
    (tmp_path / "main.cpp").write_text(
        '#include "winch_station.ino"\nint main(){ setup(); for (int i = 0; i < 5; i++) loop(); return 0; }\n')
    exe = tmp_path / "station"
    r = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-DCONFIG_IDF_TARGET_ESP32C3", f"-I{tmp_path}", f"-I{STUBS}",
                        f"-I{FW}", str(tmp_path / "main.cpp"), "-o", str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    assert subprocess.run([str(exe)], timeout=10).returncode == 0
