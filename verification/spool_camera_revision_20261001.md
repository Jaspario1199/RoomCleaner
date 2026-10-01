# Spool/outlet/camera revision checks — 2026-10-01

- Host regression: 306 tests passed. No host moving-camera localization/pickup implementation is claimed.
- Existing ESP32 clamp firmware compiled: 997107 bytes flash / 51220 bytes global RAM.
- New XIAO ESP32-S3 Sense camera + clamp firmware compiled with OPI PSRAM: 1027481 bytes flash / 62400 bytes global RAM. Camera clock and servo use separate LEDC timers. Actual simultaneous operation remains untested.
- Full clamp nominal assembly: 4037 sampled checks passed; assembly remains the existing fixed-camera-era mechanical prototype, not a completed camera pod.
- Revised winch: valid connected printable solids, STEP export/volume round trips and sampled nominal collision/stroke/cover removal checks. Latest check count is in cad/exports/winch_bench/bench_audit.json. Bead approach and full depression are included.
- 15 oriented winch STLs, including the new original-geometry V2 spool, screw-retained magnet cup and Ronstan outlet retaining plate. Metal ring, hardware, switch and electronics reference solids must not be printed as functional replacements.
- This release does not validate real hardware, screw head envelopes, printed thread strength, KW12 lever travel/force, spring SKU/rate, braid friction/wear, electronics temperatures, camera field of view, pose accuracy or printer fit. Print a single cartridge and spool/cup first.
- Order worksheet has historical purchases, new requirements, reusable inventory and unresolved specifications. It is not a claim of confirmed receipt or a fully frozen purchase BOM.
