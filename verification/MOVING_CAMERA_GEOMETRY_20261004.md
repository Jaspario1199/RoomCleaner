# Moving-camera plane geometry — bounded V01 contribution

Verified 5 October 2026; filename follows the design-plan revision of 4 October.

## Scope and contract

New `roomcleaner/perception/moving_camera.py` exposes
`pixel_to_world_plane(u, v, K, T_WC, plane_normal, plane_offset, *, image_size=None)`.
All calibration, image-specific pose and plane inputs are supplied explicitly.
There is no default room, calibration, inferred camera position or live integration.
The existing fixed-camera localization implementation remains unchanged.

Camera axes are +X right, +Y down, +Z forward. `T_WC` maps camera points to the
world frame (metres, +Z up); its translation is the optical centre. The world
plane equation is `n · X + d = 0`. The pixel must already be undistorted into the
pixel coordinate system of the supplied canonical pinhole K; distortion handling
is external. Width/height, if provided, describe that undistorted image.

The ray is obtained by solving `K r_C = [u, v, 1]`, normalizing it and rotating it
with `R_WC`. For optical centre `c_W`, intersection distance is
`t = -(n_unit · c_W + d_unit)/(n_unit · r_W)` and `X_W = c_W + t r_W`.
Only finite intersections with strictly positive t are returned.

## Acceptance evidence

Reproduction command from repository root:

```sh
PYTHONPATH=/workspace/scratch/9aff26cb6121/task_dependencies python -m pytest -q tests/test_moving_camera.py tests/test_localization.py
```

Result: **62 passed** (56 new moving-camera cases, six existing localization cases).

| Check | Expected | Measured result / tolerance | Status |
|---|---|---|---|
| Downward camera principal point | Floor point [1, 2, 0] m | Matches; NumPy allclose | Pass |
| Noncentral pixels with unequal focal lengths and skew | Independently forward-projected known point | Recovered within 1e-12 m absolute tolerance | Pass |
| Three translated/yawed/tilted poses, horizontal and tilted planes, three points each | Recover known world coordinates | All 18 points within 1e-11 m absolute tolerance | Pass |
| Same world point observed from two different camera positions | Pose-specific rays return same point | Both within 1e-12 m absolute tolerance | Pass |
| Positive/negative plane scaling (1e-200, -3, 1e200) | Equivalent plane returns same point | Within 1e-12 m absolute tolerance | Pass |
| Invalid/absent/nonfinite/singular/noncanonical intrinsics | ValueError | All assigned negative cases rejected | Pass |
| Invalid/absent/nonfinite/reflected/scaled/sheared/projective pose | ValueError | All assigned negative cases rejected | Pass |
| Missing required pose | TypeError | Rejected by required argument contract | Pass |
| Bad plane or pixel inputs | ValueError | Shape, zero normal, nonfinite and absent inputs rejected | Pass |
| Parallel / nearly parallel ray | ValueError | Exact and 1e-14 angular-dot cases rejected | Pass |
| Intersection behind or at camera centre | ValueError | Both rejected | Pass |
| Image bounds | 0 <= u < width, 0 <= v < height | Lower/upper outside points rejected; inside edges accepted | Pass |
| Invalid dimensions | ValueError | Nonpositive, noninteger, boolean, wrong length rejected | Pass |
| No dimensions supplied | No unsupported bounds inference | Finite off-frame pixel remains geometrically usable | Pass |
| Input arrays | Unchanged | Exact array equality after call | Pass |
| Existing localization tests | Unchanged behavior | Six cases pass | Pass |

An initial synthetic fixture put one tilted-plane point behind its tilted
camera. Raising that fixture camera from z=2 m to z=4 m made the positive
forward-projection case valid; the implementation was unchanged by that repair.

## Limits and remaining evidence

This is mathematical/synthetic verification, not independent hardware validation.
No real camera is claimed calibrated and V01 is not closed. Physical intrinsics,
distortion, assembled transforms, image-specific observed pose, surveyed planes,
timestamp association, uncertainty and acceptable grazing-angle/workspace bounds
remain required. Rigid rotation checks use absolute tolerance 1e-8; angular
parallel rejection uses a unit-vector dot threshold 1e-12. These numerical
thresholds do not establish an application error budget.

This utility assumes the selected observed point lies on the selected plane;
cloth height, occlusion and identity cannot be resolved by ray/plane geometry.
Camera-only motion, empty grabs, wrong-cloth pickup and failed-release evidence
remain mission-verification tasks. No success evidence or delivered-count logic
has been changed. Lead review is required before integration.
