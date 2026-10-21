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
- Computed with the model only. A simulated startup with `robot.sim3_34.json` has not been run yet; it is next, after the
  independent three-station review finishes.
- Not measured on hardware.
