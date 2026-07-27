# Claw parts — independent geometry verification report

Verifier: geometry-verifier (Sonnet). Read-only against `cad/parts/*.py`;
did not modify any part. Measurements made programmatically with CadQuery
2.8.0 by calling each part's `make()` directly — see
`tests/test_claw_geometry.py` for the reproducible pytest encoding of every
check below (42 tests). Date: 2026-07-27.

Scope: `cad/parts/{standoff, tendon_drum, electronics_cover, tentacle_hub,
tentacle_finger, effector_frame}.py`. Requirement basis: `REQUIREMENTS.md`
A1/A3, `cad/interfaces.py`.

## Check 1 — build validity, solid count, bounding box (tol ±0.3 mm)

| Part | Solids | isValid() | Expected bbox (mm) | Measured bbox (mm) | Diff (mm) | Result |
|---|---|---|---|---|---|---|
| standoff | 1 | True | 10 × 10 × 40 | 10.000 × 10.000 × 40.000 | 0,0,0 | PASS |
| tendon_drum | 1 | True | 33 × 33 × 12.4 | 33.000 × 33.000 × 12.400 | 0,0,0 | PASS |
| electronics_cover | 1 | True | 98.8 × 98.8 × 44.4 | 98.800 × 98.800 × 44.400 | 0,0,0 | PASS |
| tentacle_hub | 1 | True | 88 × 88 × 12 | 88.000 × 88.000 × 12.000 | 0,0,0 | PASS |
| tentacle_finger | 1 | True | 20 × 17 × 70 | 20.000 × 17.000 × 70.000 | 0,0,0 | PASS |
| effector_frame | 1 | True | 92 × 92 × 8 | 92.000 × 92.000 × 8.000 | 0,0,0 | PASS |

All six parts: single solid, valid BREP, bbox within tolerance (measured
diffs were sub-micron, well inside ±0.3 mm). **PASS — all parts.**

## Check 2 — interface agreement

### 2a. Frame/hub standoff-hole circle (D3/D6)

Method: Ø2 mm pin cut at `(HUB_MOUNT_R·cosθ, HUB_MOUNT_R·sinθ)` for each
θ in `STANDOFF_ANGLES_DEG = (36, 108, 252, 324)`, on both parts. Volume
removed by the cut measures whether a void was already there.

| θ (deg) | Position (mm) | Hub removed (mm³) | Frame removed (mm³) | Result |
|---|---|---|---|---|
| 36 | (21.84, 15.87) | 0.000 | 0.000 | PASS |
| 108 | (-8.34, 25.68) | 0.000 | 0.000 | PASS |
| 252 | (-8.34, -25.68) | 0.000 | 0.000 | PASS |
| 324 | (21.84, -15.87) | 0.000 | 0.000 | PASS |

Control point (θ=36°, r = HUB_MOUNT_R + 6 mm): hub removed 37.70 mm³, frame
removed 15.71 mm³ — both clearly solid there, confirming the probe
discriminates hole vs. no-hole rather than trivially passing. **PASS.**
Both parts import `HUB_MOUNT_R`/`STANDOFF_ANGLES_DEG` from
`cad/interfaces.py`, so this is a real shared-source guarantee, not
coincidence.

### 2b. Hub finger slots are through (D5)

Method: for each of the 5 slots, an 80%-of-pocket-size probe box run the
full hub height (+10 mm margin both ends) intersected with the hub.

| Slot | Center (mm) | Intersect volume (mm³) | Result |
|---|---|---|---|
| 0 (0°) | (34.30, 0.00) | 0.0000 | PASS |
| 1 (72°) | (10.60, 32.62) | 0.0000 | PASS |
| 2 (144°) | (-27.75, 20.16) | 0.0000 | PASS |
| 3 (216°) | (-27.75, -20.16) | 0.0000 | PASS |
| 4 (288°) | (10.60, -32.62) | 0.0000 | PASS |

All 5 slots open top-to-bottom, no floor. Consistent with source:
`POCKET_DEPTH = HUB_THK` and `.translate((0,0, HUB_THK - POCKET_DEPTH))` =
`translate((0,0,0))`. **PASS.**

### 2c. Finger shoulder geometry (D5)

- Shoulder-region (z ∈ [0, FINGER_SHOULDER_T]) XY footprint: measured
  20.000 × 17.000 mm vs. expected `W_BASE + 2·FINGER_SHOULDER_GROW` = 16 +
  4 = 20, `H_BASE + 2·FINGER_SHOULDER_GROW` = 13 + 4 = 17. **PASS** (exact
  match, within ±0.3 mm tol).
- Shoulder height: shoulder-region slice zmax = 2.0 mm = `FINGER_SHOULDER_T`.
  **PASS.**
- Body above the shoulder, taken across the full through-slot depth
  (z ∈ [FINGER_SHOULDER_T, HUB_THK] = [2, 12] mm — the widest point in that
  band, right above the shoulder): measured 15.800 × 12.829 mm vs. pocket
  16.4 × 13.4 mm → clearance +0.600 mm (X) / +0.571 mm (Y), both positive.
  **PASS**, fits with clearance ≈ CLEARANCE (0.2 mm/side design intent);
  the finger tapers immediately above the shoulder so this is comfortably
  inside the slot at every point along its 12 mm travel through the hub.

### 2d. Drum (C1/C2)

- Winding capacity: `DRUM_CORE_R (13.5) · radians(SERVO_THROW_DEG (120))` =
  **28.274 mm ≥ 27 mm**. **PASS.** Note `SERVO_THROW_DEG` is derived
  (`SERVO_GRIP_DEG − SERVO_RELEASE_DEG` = 140 − 20 = 120) — consistent with
  the corrected 140° grip angle (see hardware-test fix below).
- 5 tie-off holes through the bottom flange at r = DRUM_CORE_R, 72° pitch:
  Ø1 mm probe pin removed ≈0.04 mm³ at all 5 positions (numerical/mesh
  residual on a 6913 mm³ part, i.e. effectively 0 — hole present).
  **PASS, all 5.**
- Horn pocket in the TOP face: Ø HORN_POCKET_DIA(21.6)×0.9, depth
  HORN_POCKET_T(2.4) probe (inset 0.1 mm each side) intersects 0.0000 mm³
  of material at top_z = 2·DRUM_FLANGE_T + DRUM_CORE_H = 12.4 mm.
  **PASS.**

### 2e. Cover ↔ frame tab-hole alignment (D7)

Ø2 mm pin probe at `(±COVER_SCREW_POS, 0)`, `(0, ±COVER_SCREW_POS)` =
`(±40, 0)`, `(0, ±40)` on both parts:

| Position | Cover removed (mm³) | Frame removed (mm³) | Result |
|---|---|---|---|
| (40, 0) | 0.0000 | 0.0000 | PASS |
| (-40, 0) | 0.0000 | 0.0000 | PASS |
| (0, 40) | 0.0000 | 0.0000 | PASS |
| (0, -40) | 0.0000 | 0.0000 | PASS |

Both parts import `COVER_SCREW_POS` from `cad/interfaces.py`; holes coincide
exactly. **PASS, all 4.**

## Check 3 — STEP round trip (bbox ≤0.1 mm, volume ≤1%)

| Part | Orig volume (mm³) | Reimport volume (mm³) | Vol diff | Bbox diff (mm) | Result |
|---|---|---|---|---|---|
| standoff | 2978.23 | 2978.23 | 0.0000% | 0.0000 | PASS |
| tendon_drum | 6913.87 | 6913.87 | 0.0000% | 0.0000 | PASS |
| electronics_cover | 40639.02 | 40639.02 | 0.0000% | 0.0000 | PASS |
| tentacle_hub | 50714.39 | 50714.39 | 0.0000% | 0.0000 | PASS |
| tentacle_finger | 7762.50 | 7762.50 | 0.0000% | 0.0000 | PASS |
| effector_frame | 37248.79 | 37248.79 | 0.0000% | 0.0000 | PASS |

All six reimport as exactly 1 solid with matching bbox/volume.
**PASS — all parts.**

## Check 4 — mass rollup (A3)

Printed volumes × `cad/materials.py` densities (PETG structural, TPU95A
finger ×5), plus `PURCHASED_MASS_G`:

| Item | Unit vol (cm³) | Qty | Material | Density (g/cm³) | Mass (g) |
|---|---|---|---|---|---|
| standoff | 2.98 | 4 | PETG | 1.27 | 15.13 |
| tendon_drum | 6.91 | 1 | PETG | 1.27 | 8.78 |
| electronics_cover | 40.64 | 1 | PETG | 1.27 | 51.61 |
| tentacle_hub | 50.71 | 1 | PETG | 1.27 | 64.41 |
| tentacle_finger | 7.76 | 5 | TPU95A | 1.21 | 46.96 |
| effector_frame | 37.25 | 1 | PETG | 1.27 | 47.31 |
| **Printed subtotal** | | | | | **234.20** |
| Purchased (MG996R 55 + ESP32 10 + LiPo2S 90 + buck 5 + switch/wiring 25) | | | | | **185.00** |
| **TOTAL** | | | | | **419.20 g** |

Budget: 450 g (R7/A3). **PASS — 419.20 g, 30.8 g (6.8%) of margin
remaining.** This is above the 375 g "estimated" figure in `CLAUDE.md`'s
project summary — worth flagging to the Fable lead as a shrinking margin,
though it still clears the hard budget.

Six parts NOT scoped to this review (`camera_mount*.py`, `corner_guide.py`,
`motor_mount.py`, `winch_spool.py`) are excluded from this rollup by
assignment scope; if they are also part of the claw's carried mass, the
419.2 g figure understates the true total and should be reconciled
separately.

## Owned test fix — grip-angle contract drift

`tests/test_hardware.py::test_full_plan_streams_expected_commands` asserted
`"G 120"` for the grip command. The contracted grip angle
(`cad/interfaces.py SERVO_GRIP_DEG` and
`roomcleaner/hardware/hw_config.py GRIP_ANGLE`) is **140°**, not 120° — the
test was stale relative to the interface contract. Updated the assertion to
`"G 140"`. The release assertion (`"G 20"`) already matched
`SERVO_RELEASE_DEG`/`RELEASE_ANGLE` = 20 and was left unchanged.

## pytest results

```
python -m pytest tests/ -q
71 passed in 12.45s
```

(42 of the 71 are the new `tests/test_claw_geometry.py`; the rest are
pre-existing suites, including the corrected `test_hardware.py`.)

## Summary

All six claw parts and all interface-agreement checks in scope **PASS** with
no repairs needed. No geometry defects found. Mass rollup passes with
~7% margin against the 450 g budget — flagged as a margin-shrinkage risk
for the Fable lead's awareness, not a failure.
