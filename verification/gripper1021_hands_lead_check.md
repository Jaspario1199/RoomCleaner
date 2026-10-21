# Gripper 1021 hands: lead's independent collision sweep (2026-10-21)

Independent of the implementer's sweep: `scripts/verify_gripper1021_hands_sweep.py` loads the exported hand STEPs
(`exports/step/gripper1021_hand_{right,left}.step`, file pose θ2 = −52.1°) and moves them rigidly with the four-bar
(`cad/reference/gripper_1021/fourbar.py`, coupler 34.67). Jasper's parts move with them: the compound about its axis,
the follower meshed (−6°) and mirrored, both arms to the solved rocker angle (tip-hole angles measured from the STEPs),
and both housing halves and the pinion fixed.

| θ2 (deg) | Overlap > 0.01 mm³, hands vs compound / follower / both arms / housing 1 / housing 2 / pinion / each other |
|---|---|
| −5, −10, −20, −30, −40, −50, −52.1, −60, −62 | none (clear) |

Result: **PASS**. This agrees with the implementer's sweep and clearance table in `gripper1021_build_notes.md`.

Lead decisions on the implementer's flags:
1. **Mass vs the 3 mm wall rule:** keep the 21.5 g layout. The wall is 2.25 mm at the groove roots. Finger bending at a 20 N grip is about 3 MPa against roughly 50 MPa for PETG, and 2.25 mm is 5 or more perimeters with a 0.4 mm nozzle.
2. **Screws:** M3 × 20 at the crank pin; M3 × 18 at the arm tip (× 20 also fits).
3. **Spec typo:** the spec's 994.19 tip x was a bounding-box estimate. The STEP hole is at 994.531, and the hands follow the four-bar numbers. The 0.15 mm M3 play absorbs the 0.06 mm.
