# winch_station core

`station_core.h` is a portable, allocation-free C++17 port of the reference
winch-station logic in `roomcleaner/cdpr/station_core.py` (plus the protocol
constants and `params_hash` from `roomcleaner/cdpr/protocol.py`). `json_lite.h`
is the minimal JSON codec it uses (flat objects, nested `p` / `cap` objects,
fixed buffers, `MAX_DATAGRAM` = 512).

The core does no I/O. The caller feeds it time, encoder samples, switch level and
received datagrams, and drains the outbox:

```cpp
roomcleaner::winch::StationCore core(boot_id);            // 1 ms period by default
core.handleDatagram(buf, len, now_us, /*from_host=*/true); // false if invalid (dropped)
int steps = core.update(now_us, enc_counts, enc_valid, sw_active);  // signed steps for next period
roomcleaner::winch::OutMsg m;
while (core.drain(m)) send(m.broadcast ? "*" : "host", m.data, m.len);
```

`core.params()` / `core.configured()` expose the accepted host configuration
(`step_sign`, `sw_nc`, ...) once a valid `cfg` has been acked.

Only `<math.h> <stdio.h> <stdint.h> <string.h>` are used (no heap, exceptions,
RTTI or STL), so it builds natively and in an ESP32-C3 Arduino sketch
(`#include "station_core.h"`). Time is a 64-bit microsecond count.

## Conformance

`tests/firmware/gen_station_traces.py` drives the Python `StationCore` through 16
scripted scenarios (config/arm gates, normal synchronized motion, out-of-order and
duplicate segments, queue full, hold / feed-hold, lease expiry, underrun, reference
capture + backoff release, capture without edge, capture glitch, tracking fault,
switch fault, disarm/clear, encoder faults, timing fault) and records every input
and output to `tests/firmware/traces/*.json`. `tests/firmware/conformance_main.cpp`
replays the inputs through the C++ core and requires exact step counts and
field-by-field message equality (floats within 1e-6 relative; int/float type must
also agree).

```
/usr/bin/python3 -m pytest tests/firmware -q
# or by hand:
python3 tests/firmware/gen_station_traces.py
g++ -std=c++17 -O2 -Wall -Wextra -Werror -ffp-contract=off -I firmware/winch_station \
    tests/firmware/conformance_main.cpp -o /tmp/conformance && /tmp/conformance tests/firmware/traces
```

`-ffp-contract=off` keeps doubles rounding exactly like CPython (no fused
multiply-add).

## Known limits versus the Python reference

* Integers are int64 (Python is unbounded); JSON arrays and numeric strings in
  numeric fields are not supported (Python would accept numeric strings and raise
  on some bad types). `sid` is limited to 15 characters, keys to 23.
* A datagram with more than 32 fields or nesting deeper than 3 is dropped.
* Outbox holds 16 datagrams; drain after every `handle`/`update`. Overflow drops
  the message (counter: `droppedMessages()`), but `seq` still advances so the host sees a gap.

## Hardware sketch (`winch_station.ino`)

`winch_station.ino` + `as5600.h` + `stepgen.h` are the XIAO ESP32-C3 glue
(Rev C pins, UDP port 8771, host port 8770, 1 kHz control loop, 40 kHz step
timer). `tests/firmware/test_sketch_builds.py` builds and runs it on the host
against Arduino stubs; it has **not** yet been compiled with the ESP32 core.
Copy `secrets.example.h` to `secrets.h` per station.

## Reference fixes found by the port (2026-10-19)

Applied to both `roomcleaner/cdpr/station_core.py` and `station_core.h`:
- `clear` after a disarm-in-fault now clears the latched fault (stays OFF);
  previously only a power cycle recovered.
- A switch contact shorter than the debounce no longer leaves a stale
  capture snapshot that would later be reported as the bead position.
Motion ids must be unique per boot (the coordinator increments them).
