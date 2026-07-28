# Winch-side / camera parts -- independent verification report

Scope: `winch_spool`, `motor_mount`, `corner_guide`, `camera_mount`,
`camera_mount_overhead`. These five parts predate the Gate-4/5 workflow and
`cad/interfaces.py`; they had never been independently verified. This report
covers Gate 5 (geometry-verifier role) only.

Verifier: geometry-verifier (Sonnet). Permanent tests:
`tests/test_winch_geometry.py`. All measurements below were produced by
independently building each part's `make()` function and probing the actual
BRep solid (OCCT `BRepClass3d_SolidClassifier` point-in-solid tests and
boolean pin-cut volume differencing) -- not by reading source and trusting
comments.

Authority for expected values: `cad/params.py`
(`MOTOR_SHAFT_DIA=5.0, MOTOR_SHAFT_FLAT=0.5, CLEARANCE=0.2,
NEMA17_FACE=42.3, NEMA17_HOLES=31.0, NEMA17_BOSS_DIA=22.0, SCREW_M3=3.4,
SCREW_M3_TAP=2.8, SPOOL_*`) plus purchased-part facts given in the assignment
(NEMA 17: 5 mm round shaft, 31 mm M3 square, Ø22 pilot boss; Pi Camera:
21x12.5 mm M2 pattern; innomaker board: 32x32 mm, ASSUMED 28 mm M2 pattern).

All five parts execute cleanly via `python -m cad.parts.<name>` and export
STEP/STL/PNG with no exceptions.

## Summary

| Part | Build | BBox | Interfaces | STEP round-trip | Verdict |
|---|---|---|---|---|---|
| winch_spool | PASS | PASS | Bore dia PASS; **D-flat FAIL** | PASS | **FAIL** (D-flat non-functional) |
| motor_mount | PASS | PASS | PASS | PASS | **PASS** |
| corner_guide | PASS | PASS | Hole dia + coax PASS; **wall FAIL** | PASS | **FAIL** (0.15 mm wall) |
| camera_mount | PASS | PASS | PASS | PASS | **PASS** (see assumption note) |
| camera_mount_overhead | PASS | PASS | PASS | PASS | **PASS** (28 mm pitch is an unverified assumption -- flagged in source) |

Reproduce all of the below: `python -m pytest tests/test_winch_geometry.py -v`

---

## 1. winch_spool

**Build / BREP**: `winch_spool.make()` builds a single valid solid.
`solids()` count = 1, `isValid()` = True, `Volume()` = 13307.34 mm^3 > 0.

**Bounding box** (expected 36 x 36 x 32 mm, tol 0.3 mm):
measured **36.000 x 36.000 x 32.000 mm** -- PASS.

**CRITICAL CHECK -- bore derives from MOTOR_SHAFT_DIA (not stale 6 mm)**:
`bore = MOTOR_SHAFT_DIA + CLEARANCE = 5.0 + 0.2 = 5.2 mm` (radius 2.6 mm) is
computed directly from `cad/params.py` in `winch_spool.py` line 24 --
`bore = MOTOR_SHAFT_DIA + CLEARANCE`. This is a live parameter reference, not
a hardcoded literal, so it cannot silently go stale on a future motor swap.
Measured (round side of the bore, -X, away from the flat, at mid-drum height
z=16 mm): binary-search void->solid transition radius = **2.6000 mm**,
expected 2.600 mm (tol 0.02 mm). **PASS** -- confirms the bore is sized for
the current 5 mm NEMA 17 shaft, not the old 6 mm motor.

**D-flat anti-rotation feature -- FAIL (real defect)**:
`cad/parts/winch_spool.py` (lines 43-49) cuts the D-flat with:
```python
flat = (
    cq.Workplane("XY")
    .center(bore / 2 - MOTOR_SHAFT_FLAT, 0)
    .box(MOTOR_SHAFT_FLAT * 2, bore, total_len * 2, centered=(True, True, True))
)
```
This box is centered at `x = bore/2 - MOTOR_SHAFT_FLAT = 2.1 mm` with a
1.0 mm X-extent (`MOTOR_SHAFT_FLAT*2`), giving global X range **[1.6, 2.6]
mm**, and a Y-extent (`width=bore=5.2`) of **[-2.6, 2.6] mm** -- exactly the
bore's own diameter. Because the circular bore cut already voids the entire
X range [-2.6, 2.6] at y=0 (the bore's equator), the flat box is a complete
no-op there: it only removes *additional* material near the Y-extremes of
the bore (|y| > ~2.05 mm, where the round bore's own X-extent has already
narrowed below the box's fixed 1.6 mm inner edge). At y=0 -- the flat's
intended center, i.e. where a mating NEMA 17 D-shaft's flat face would
actually contact -- there is **no flattening at all**.

Measured (probe: sweep +X at y=0, z=16 mm, using an exact BRep point
classifier, 50-iteration bisection):
- Wall (void->solid transition) at **x = 2.6000 mm**
- Expected per spec: `bore_r - MOTOR_SHAFT_FLAT = 2.6 - 0.5 = 2.100 mm`
- Error: **0.500 mm** (i.e. the flat is entirely absent at its design
  center; the bore is a plain round hole there)

Confirmed z-invariant (same result at z = 0.5, 8, 16, 24, 31.5 mm -- the
defect is present along the full bore length, not just near one end).

Secondary artifact: at the Y-extremes where the box cut *does* engage (e.g.
y=2.2 mm), it creates a disconnected sliver of solid material between the
circular-bore boundary (x=1.386 mm) and the box's inner edge (x=1.6 mm)
rather than a clean flat -- confirmed present but not the primary defect.

**Consequence**: with `MOTOR_SHAFT_FLAT=0.5` set in params, a NEMA 17
D-shaft inserted into this bore sees an effectively round hole at the
5.2 mm slip-fit clearance; the only anti-rotation feature actually present
is the radial M3 grub screw (confirmed present and correctly located, not
re-verified in detail here since it was not asked). The flat cut must be
reconstructed (e.g. centering the box further outward so its inner face
lands at `bore/2 - MOTOR_SHAFT_FLAT` with the cut extending outward past the
bore radius, not straddling that plane) -- **not attempted here; this is a
report, not a repair**, per instructions.

**STEP round-trip**: reimport 1 solid, bbox diff 0.0000 mm (tol 0.1),
volume diff 0.0000 % (tol 1 %). PASS.

Permanent tests: `test_spool_bore_round_radius_matches_motor_shaft_dia`
(PASS), `test_spool_dflat_has_zero_effect_at_flat_center` (FAILS by design,
documents the defect with the exact numbers above).

---

## 2. motor_mount

**Build / BREP**: 1 solid, valid, Volume = 27964.44 mm^3.

**Bounding box** (expected 56 x 52 x 54 mm): measured **56.000 x 52.000 x
54.000 mm** -- PASS.

**4x M3 clearance holes on the NEMA17_HOLES=31 mm square**: face plate holes
at (dx, dz) = (±15.5, 30±15.5) relative to the vertical face
(`half = NEMA17_HOLES/2 = 15.5`, `PATTERN_Z = 30`). Probed all 4 by sweeping
along X through the face thickness at each hole center:

| hole (x, z) | measured diameter | expected (SCREW_M3 + 0.4) |
|---|---|---|
| (-15.5, 14.5) | 3.8000 mm | 3.8 mm |
| (-15.5, 45.5) | 3.8000 mm | 3.8 mm |
| (15.5, 14.5) | 3.8000 mm | 3.8 mm |
| (15.5, 45.5) | 3.8000 mm | 3.8 mm |

All 4 PASS (tol 0.05 mm).

**Boss clearance (NEMA17_BOSS_DIA=22.0 mm)**: measured diameter **22.2000
mm**, i.e. `NEMA17_BOSS_DIA + CLEARANCE = 22.0 + 0.2`. Requirement (>= 22 mm)
and exact-value check both PASS.

**STEP round-trip**: 1 solid, bbox diff 0.0000 mm, volume diff 0.0000 %.
PASS.

Verdict: **PASS**, no defects found.

---

## 3. corner_guide

**Build / BREP**: 1 solid, valid, Volume = 10982.29 mm^3.

**Bounding box** (expected 55 x 34 x 26 mm): measured **55.000 x 34.000 x
26.000 mm** -- PASS.

**Ear axle holes -- diameter and coaxiality**: `EAR_HOLE = SCREW_M3 = 3.4
mm`, hole cut at `EAR_HOLE + 0.3 = 3.7 mm` diameter, axis along Y (drilled
from the `>Y` ear face). Measured diameter by sweeping Z (perpendicular to
both the hole axis and the thin X wall, so this isolates the true bore size)
at both ears: **3.7000 mm** on both (expected 3.7 mm) -- PASS. Both ears use
the identical `(ear_cx, z)` formula (differ only in `sy`), so the two axle
holes are exactly coaxial by construction -- PASS.

**Wall thickness around the axle hole -- FAIL (real defect)**: the ear is
only `EAR_T = 4.0 mm` thick in X, and the hole through it is 3.7 mm in
diameter, centered in that thickness. Remaining wall on each side =
`(4.0 - 3.7) / 2 = 0.15 mm`. Direct point-classifier probing along X at the
hole confirms this: solid was found only in a razor-thin sliver between
x-offset -2.0 and -1.9 mm from the ear center (about 0.1 mm), with void on
both sides of it -- i.e. the "hole" leaves essentially no usable wall and,
at typical FDM dimensional tolerances (+/-0.1-0.2 mm is common), is likely
to breach the ear's outer face entirely, turning the bore into an open-sided
slot. This is well below any practical FDM minimum wall (commonly cited as
>= 0.4-0.8 mm, i.e. at least one nozzle width at 0.4 mm nozzle).

Measured/nominal: **0.15 mm** wall vs. **0.4 mm** minimum-printable
threshold used in the test -- FAIL.

**STEP round-trip**: 1 solid, bbox diff 0.0000 mm, volume diff 0.0000 %.
PASS.

Permanent tests: `test_corner_guide_ear_axle_hole_diameter` (PASS, both
ears), `test_corner_guide_ear_axle_holes_are_coaxial` (PASS),
`test_corner_guide_ear_wall_thickness_around_axle_hole` (FAILS by design,
documents the 0.15 mm wall).

---

## 4. camera_mount

**Build / BREP**: 1 solid, valid, Volume = 3953.98 mm^3.

**Bounding box** (expected 31 x 35 x 16 mm): measured **31.000 x 35.000 x
16.000 mm** -- PASS.

**Pi Camera M2 hole pattern (21 x 12.5 mm, purchased-part fact)**: all 4
corners probed (`(±10.5, ±6.25)`), measured diameter **2.4000 mm** at each,
expected `M2 = 2.4 mm` (matches the local `M2` constant in
`camera_mount.py`) -- PASS at all 4.

**Assumption flag**: the 21 x 12.5 mm / M2 pattern is hardcoded locally in
`camera_mount.py` (not in `cad/params.py` or `cad/interfaces.py`), sourced
from the docstring's claim about the Pi Camera Module PCB. This matches the
commonly cited Pi Camera v1/v2 mounting-hole spec, but it is not centralized
or traced to a measurement in this repository -- flagging per the
assignment's authority note, not a geometry failure.

**STEP round-trip**: 1 solid, bbox diff 0.0000 mm, volume diff 0.0000 %.
PASS.

Verdict: **PASS**, no geometry defects found; hole-pattern source is an
external assumption (flagged, not a defect).

---

## 5. camera_mount_overhead

**Build / BREP**: 1 solid, valid, Volume = 10465.41 mm^3.

**Bounding box** (expected 50 x 50 x 14 mm): measured **50.000 x 50.000 x
14.000 mm** -- PASS.

**4 posts on the CAM_HOLE_PITCH=28 mm square, M2 tap holes**: all 4 posts
probed at `(±14, ±14)`, mid-post height (z = -5 mm):

| post (x, y) | tap hole dia | expected (M2_TAP) | post OD | expected (POST_DIA) |
|---|---|---|---|---|
| (14, 14) | 1.7000 mm | 1.7 mm | 6.0000 mm | 6.0 mm |
| (-14, 14) | 1.7000 mm | 1.7 mm | 6.0000 mm | 6.0 mm |
| (14, -14) | 1.7000 mm | 1.7 mm | 6.0000 mm | 6.0 mm |
| (-14, -14) | 1.7000 mm | 1.7 mm | 6.0000 mm | 6.0 mm |

All 4 posts PASS on both dimensions (tol 0.05 mm).

**Assumption flag (explicit in source)**: `camera_mount_overhead.py` itself
states `CAM_HOLE_PITCH = 28.0` is unverified against the real innomaker
board and instructs the user to measure before printing. Geometry is
internally consistent with that assumed value; this is a documented
open risk, not a geometry defect.

**STEP round-trip**: 1 solid, bbox diff 0.0000 mm, volume diff 0.0000 %.
PASS.

Verdict: **PASS**, no geometry defects found; 28 mm hole pitch remains an
unverified assumption (already flagged in the part's own docstring).

---

## Test run

```
python -m pytest tests/test_winch_geometry.py -q
...
2 failed, 32 passed in ~7s
FAILED tests/test_winch_geometry.py::test_spool_dflat_has_zero_effect_at_flat_center
FAILED tests/test_winch_geometry.py::test_corner_guide_ear_wall_thickness_around_axle_hole
```
Both failures are intentional -- they encode the two real defects found
above and will fail until the parts are repaired. All other 32 checks
(build validity, bbox, interface dimensions, STEP round-trip) pass.

```
python -m pytest tests/ -q
...
2 failed, 103 passed in ~19s
```
The pre-existing claw suite (`tests/test_claw_geometry.py`, part of the
103 passing) remains fully green; the only failures are the two new,
intentional defect-documentation tests above. No repairs were made to any
part file -- per instructions, this pass reports failures rather than
fixing them.

## Findings requiring a decision

1. **winch_spool D-flat is non-functional** (FAIL). The bore behaves as a
   plain round 5.2 mm hole; `MOTOR_SHAFT_FLAT=0.5` has no geometric effect.
   Recommend routing to `cad-implementer` for a bounded fix to the `flat`
   cut construction in `cad/parts/winch_spool.py`, then re-verification.
2. **corner_guide ear axle hole leaves ~0.15 mm wall** (FAIL), below
   printable minimum. Recommend either increasing `EAR_T` or reducing the
   axle hole clearance (`EAR_HOLE + 0.3`) in `cad/parts/corner_guide.py`,
   then re-verification.
3. **camera_mount_overhead CAM_HOLE_PITCH=28 mm** and **camera_mount's
   21x12.5 mm Pi Camera pattern** are both real-hardware assumptions not
   centralized in `cad/params.py`/`cad/interfaces.py`. Recommend the user
   confirm against the actual purchased boards before printing; no geometry
   defect found against the assumed values.
