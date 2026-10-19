# Detached bench motion configuration resolution

Report date: 2026-10-05. Filename follows the assigned 20261004 resolution series.

## Change and preserved defaults

The portable single-axis `Config` now explicitly owns the formerly hardcoded arrival and home/tick timing values:

| Parameter | Default | Unit / purpose |
|---|---:|---|
| arrivalTolerance | 4 | Encoder counts allowed for settled arrival |
| arrivalDwellUs | 50000 | Continuous in-tolerance arrival dwell, microseconds |
| settleTimeoutUs | 500000 | Time allowed after the final MOVE pulse, microseconds |
| switchDebounceUs | 10000 | Stable home-switch edge window, microseconds |
| maxTickIntervalUs | 10000 | Maximum active-motion tick interval, microseconds |

All defaults and comparison boundaries remain unchanged. The existing tracking, heartbeat and encoder timeout defaults are also unchanged. No adapter, network, CAD, or hardware settings were changed.

`arm()` rejects zero timing intervals and intervals at or above 2^31 microseconds, across all seven timing fields. The half-range bound keeps configured intervals within the conventional unambiguous range of wrapping 32-bit timestamp comparisons. It additionally requires arrival dwell strictly less than settle timeout, and arrival tolerance positive and no larger than tracking tolerance. These are configuration acceptance rules, not measured commissioning values. Configuration is validated at arm; public configuration mutation while armed is not newly guarded.

## Verification

Command:

```sh
PYTHONPATH=/workspace/scratch/9aff26cb6121/task_dependencies python -m pytest tests/test_local_station_core.py -q
```

Actual result: **2 passed in 0.67s**. Both actual C++ executables compiled with C++11, `-Wall -Wextra -Werror`, and undefined-behavior sanitizer, then executed successfully.

Coverage retains the 14 existing motion scenarios and four fresh debounce/arrival regressions. Seven added configuration regression groups check all seven timing fields at zero, 2^31 and UINT32_MAX; invalid arrival ordering and tolerance; configured debounce boundary; configured arrival tolerance and dwell boundary; configured settle timeout boundary; and configured maximum active tick interval boundary. The existing Python-consumed regression output remains compatible; a second output line identifies the new groups.

## Limits

This verifies portable software behavior only. Defaults remain unmeasured detached-bench placeholders. No ESP32 adapter compilation, physical switch/encoder calibration, pulse timing measurement, suspended four-axis qualification, or hardware safety qualification was performed. Parameter calibration and real-board commissioning remain required.
