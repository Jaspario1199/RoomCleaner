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

## Housing + camera bay: lead's spot check (2026-10-21)

Done independently of the implementer, on the exported STEPs:
- One valid solid each, for the housing + bay and for the cover.
- Volume: 139,511 mm³ for Jasper's housing, 154,311 mm³ for the new one. Only 526.6 mm³ was removed (Jasper's minus new), which is the wire window.
- Overlap with Jasper's cylinder is 0.0024 mm³: a 12 nm offset that is already in his file. Overlap with the tube is 0. Housing and cover do not overlap.
- The bottom plane is unchanged at y = 1091.19.

Lead decision on the cable lines: **accepted for printing.**
- Within ±15° claw yaw, no line touches the bay, and the closest line passes 11.96 mm away. This is the normal hanging orientation, set by the four-corner attachment.
- Contact is possible only at ±30° yaw or more, near the ceiling limit. The v6 bay had the same class of contact.
- Jasper was told to start the claw roughly square to the room and to look for cable rub on the first lifts.
