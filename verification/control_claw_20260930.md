# Verified cycle and claw packaging validation — 2026-09-30

- Software regression suite: 64 passed, no skips after installing Flask.
  Covers camera positive motion, disappearance/stationary/ambiguous rejection,
  stale frames, retry bounds, failed release accounting, live console accounting,
  STOP during manual lock ownership, home/setup separation and corner retention.
- Existing claw geometry suite: 42 passed.
- New electronics prototype generator: valid single solids for two bays and three
  reference envelopes; five STEP round trips; all new-versus-assembly pairwise
  nominal interference checks pass. See cad/exports/claw_electronics/verification.json.
- Python compileall and git diff whitespace checks pass.
- Firmware: compiled sketch and linked Arduino AVR core 1.8.8, actual
  AccelStepper and Servo libraries with AVR GCC 7.3.0, ATmega328P, F_CPU=16 MHz.
  Program 18,396 bytes (56.1%); static data 1,173 bytes (57.3%).
- No motor/camera/fabric/printed-part physical tests or encoder integration run.
  Firmware compile/link is not timing, load, electrical or mechanical validation.

Commands:

```
python -m pytest tests/test_verification_cycle.py tests/test_app.py tests/test_hardware.py tests/test_live.py tests/test_kinematics.py tests/test_geometry.py tests/test_localization.py -q
python -m pytest tests/test_claw_geometry.py -q
python -m cad.claw_electronics
```

See docs/CONTROL_AND_CLAW_UPDATE.md for placeholders, commissioning steps,
encoder research and unresolved hardware interfaces. New bays are packaging
prototypes; use purchased board/pack dimensions and complete regulator mounts,
connector access and wire paths before manufacturing.
