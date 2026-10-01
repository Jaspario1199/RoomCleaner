# Clamp assembly verification

Requirements and critique recorded in docs/CLAMP_ASSEMBLY_REVIEW.md before expanding the geometry.

Final verification:
- 3,820 sampled checks: every component pair at open pose, moving jaws/pads/pinion against all other modeled components at 5° increments through closure, and cover lifted 1/5/15/30/60 mm against fixed components.
- Criterion: no unintended solid intersection over 0.01 mm³. Touching mating surfaces are permitted; no positive-volume overlap exemptions were needed.
- All component exports are single valid solids; STEP reimport volumes agree within 0.0001 mm³.
- Nominal lid cavity 0.779 L; modeled occupancy 0.153 L; residual 0.627 L. Residual space is fragmented and excludes actual unmodeled wire/connector envelopes.

Detected and fixed: logic mount conflicted with added servo ear; initial fuse shelf conflicted with servo and cover mounting tab. The shelf is now integral to the screw-mounted logic holder, with a relieved ear region. TPU pads have recessed button-head hardware seats.

Limits: sample intervals are not a continuous collision proof. Cable motion, exact fastener heads/nuts, real component connectors, horn stack, tolerance variation, force, print strength and fabric pickup are not verified by these tests. Servo reference output projection remains provisional. Physical fit/proof/functional tests are required.
