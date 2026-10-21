# Three-station profiles for the housing with three-cable holes ("_34"), lead, 2026-10-21

New files, copies of the three-station profiles with one change: the claw attachment points.
- `config/robot.sim3_34.json` is a copy of `robot.sim3.json`.
- `config/robot.three34.example.json` is a copy of `robot.three.example.json`.

The reviewed profiles `robot.sim3.json` and `robot.three.example.json` are unchanged.

| station | point (body frame, m) | source |
|---|---|---|
| A | (−0.0450, −0.0260, +0.0342) | outer mouth of T_A (verification/gripper1021_housing_34_verification.md, item 11) |
| B | (+0.0450, −0.0260, +0.0342) | outer mouth of T_B |
| C | (0, +0.0450, +0.0342) | outer mouth of T_C |
| D | (−0.03707, +0.03707, 0) | 1021 corner hole D, inner mouth (unused in three-station mode) |

Use this profile only when the lines go through T_A, T_B and T_C. Start the claw with the camera bay toward station C.
The centre of mass, camera and lowest point are unchanged from the other profiles (CAD, VERIFY).

## Predicted claw tilt (cable statics model, yaw 0, `attitude.py` / `Geometry._att`)

| profile | start point (1.676, 0.931), z 0.59 m | usable workspace (0.1 m grid, z 0.6-2.1 m): min / median / max | share under the 5° grip limit |
|---|---|---|---|
| corner holes A, B, C (`robot.sim3.json`) | 5.5° | 1.4 / 7.2 / 13.2° | 22 % |
| three-cable holes (`robot.sim3_34.json`) | 0.8° | 0.2 / 3.6 / 9.2° | 78 % |

Why: three of the four corner holes have their centroid 14 mm off the centre of mass, which tilts the claw. The 120°
pattern's centroid is 2.3 mm off, and 34 mm higher.

Status:
- Tilt computed with the cable model only.
- Not measured on hardware.

## Simulated startups (lead, 2026-10-21, after the independent review)

Fast profile (`tests/cdpr/test_three_station.py::fast3`), 3 x 3 floor board (`FloorBoard.nominal(0.15)`), full
`Supervisor.start()`, scratch script (not in the repo). Each startup took 85 to 115 s of wall time.

| profile | calibration box | seed | outcome | trust level and reasons | station faults |
|---|---|---|---|---|---|
| `robot.sim3_34.json` | default [0.8, 0.8, 0.5] | 3 | READY | LOCAL_ONLY, "slack probe was off" | none |
| `robot.sim3_34.json` | default | 5 | READY | LOCAL_ONLY, "slack probe was off" | none |
| `robot.sim3_34.json` | default | 7 | READY | LOCAL_ONLY, "slack probe was off" | none |
| `robot.sim3_34.json` | default | 0 | READY | LOCAL_ONLY, "slack probe was off" | none |
| `robot.sim3.json` (corner holes) | [0.4, 0.4, 0.3] | 0 | READY | LOCAL_ONLY, "predicted length sigma 5.3 mm > 5.0 mm in the requested volume", "slack probe was off"; 14/15 points validated | none |
| `robot.sim3.json` (corner holes) | [0.4, 0.4, 0.3] | 6 | READY | LOCAL_ONLY, "predicted length sigma 5.6 mm > 5.0 mm ...", "slack probe was off"; 12/15 points validated | none |

- **Review finding M1** (false "pretension: claw dragged while tensioning") hit seeds 3, 5 and 7 with the corner-hole
  profile. It did not occur with the `_34` profile on the same seeds. The likely reason, inferred from the review's mechanism
  and not logged in these runs: with the 120 degree pattern the claw lifts off its jaws almost level (0.8 degrees predicted
  against 5.5), so the drag watch sees no tilt change to misread as drag. This removes the symptom for the `_34` claw in
  simulation. The corner-hole profile still
  has it; the underlying fix (pretension short of lift-off, or a tilt-aware drag watch) is still open.
- **M4** (outlet cone): the smaller first-run calibration box recommended in `docs/THREE_STATION_MODE.md` section 5 still
  reaches READY on the corner-hole profile.
