"""C++ winch-station core vs. the Python reference, by recorded-trace replay.

1. gen_station_traces.py drives roomcleaner.cdpr.station_core.StationCore through
   scripted scenarios and records every input and output.
2. conformance_main.cpp (compiled with g++ -std=c++17 -Wall -Wextra -Werror) replays
   the traces through firmware/winch_station/station_core.h and compares exactly.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gen_station_traces as gen  # noqa: E402

FW = ROOT / "firmware" / "winch_station"
CXX = shutil.which("g++")
# -ffp-contract=off: no fused multiply-add, so doubles round exactly as in CPython.
WARN = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-ffp-contract=off"]

REQUIRED_SCENARIOS = {
    "cfg_arm_gates", "normal_motion", "segments_ooo_dup", "queue_full", "hold_feed", "lease_expiry",
    "underrun", "ref_capture_backoff", "ref_started_active", "ref_capture_glitch", "tracking_fault",
    "switch_fault", "disarm_clear", "encoder_invalid_motion", "encoder_stale_none", "timing_fault",
}


@pytest.fixture(scope="module")
def traces():
    paths = gen.generate(gen.TRACE_DIR)
    return paths


def test_generated_traces_cover_scenarios(traces):
    assert {p.stem for p in traces} == REQUIRED_SCENARIOS
    kinds, acks, faults = set(), set(), set()
    for p in traces:
        data = json.loads(p.read_text())
        kinds.update(o["m"]["k"] for o in data["init_out"])
        for ev in data["events"]:
            for o in ev.get("out", []):
                m = o["m"]
                if m["t"] == "evt":
                    kinds.add(m["k"])
                    if m["k"] == "fault":
                        faults.add(m["f"])
                if m["t"] == "ack" and not m["ok"]:
                    acks.add((m["re"], m["why"]))
    assert {"boot", "fault", "hold", "done", "capture", "release"} <= kinds
    assert faults == {1, 2, 3, 4, 5, 6}                       # every reachable fault code
    for why in ("position", "late", "speed", "range", "malformed", "continuity", "sequence", "after last",
                "full", "holding", "fault", "not armed"):
        assert ("seg", why) in acks, why
    for key in (("disarm", "confirm"), ("disarm", "moving"), ("arm", "encoder"), ("arm", "switch active"),
                ("cfg", "incomplete"), ("cfg", "invalid"), ("cfg", "armed"), ("cancel", "not idle")):
        assert key in acks, key


@pytest.mark.skipif(CXX is None, reason="g++ not available")
def test_cpp_core_matches_python_traces(traces, tmp_path):
    exe = tmp_path / "conformance"
    cmd = [CXX, *WARN, "-I", str(FW), str(HERE / "conformance_main.cpp"), "-o", str(exe)]
    comp = subprocess.run(cmd, capture_output=True, text=True)
    assert comp.returncode == 0, comp.stderr
    run = subprocess.run([str(exe), str(gen.TRACE_DIR)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert f"{len(traces)} trace(s), 0 failed" in run.stdout


@pytest.mark.skipif(CXX is None, reason="g++ not available")
def test_core_header_builds_without_exceptions_or_rtti(tmp_path):
    """The firmware build disables exceptions and RTTI; the core must not need them."""
    tu = tmp_path / "embedded_tu.cpp"
    tu.write_text(
        '#include "station_core.h"\n'
        "int main() {\n"
        "  static roomcleaner::winch::StationCore core(1);\n"
        '  static const char kPing[] = "{\\"v\\":1,\\"t\\":\\"ping\\"}";\n'
        "  core.handleDatagram(kPing, sizeof kPing - 1, 0);\n"
        "  roomcleaner::winch::OutMsg m;\n"
        "  while (core.drain(m)) {}\n"
        "  return core.update(0, 0, true, false) + (core.configured() ? 1 : 0) + (core.params() ? 1 : 0);\n"
        "}\n")
    exe = tmp_path / "embedded_tu"
    cmd = [CXX, *WARN, "-fno-exceptions", "-fno-rtti", "-Wshadow", "-I", str(FW), str(tu), "-o", str(exe)]
    comp = subprocess.run(cmd, capture_output=True, text=True)
    assert comp.returncode == 0, comp.stderr
    assert subprocess.run([str(exe)]).returncode == 0
