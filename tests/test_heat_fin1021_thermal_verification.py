"""Independent verification of the 10/22 heat fin, thermal station STEPs, detailed NEMA 17 and the Ø4 magnet caps.

All measuring code lives in verification/heat_fin1021_thermal_verify.py (read-only on cad/ and exports/).  The harness takes about 3 minutes; it runs once
per session and each test asserts that no check of its group failed (the message lists the failing rows with expected and measured values).
Report: verification/heat_fin1021_thermal_verification.md.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def V():
    spec = importlib.util.spec_from_file_location("heat_fin1021_thermal_verify", ROOT / "verification" / "heat_fin1021_thermal_verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.RESULTS.clear()
    mod.run_all()
    return mod


def _group(V, prefix):
    rows = [r for r in V.RESULTS if r["id"].startswith(prefix)]
    assert rows, f"no checks recorded for {prefix}"
    bad = [r for r in rows if r["status"] == "FAIL"]
    assert not bad, "\n".join(f"{r['id']} {r['item']}: expected {r['expected']} measured {r['measured']} (tol {r['tol']})" for r in bad)


@pytest.mark.parametrize("prefix", ["1.", "2.", "3.", "4.", "5.", "9."])
def test_group(V, prefix):
    _group(V, prefix)
