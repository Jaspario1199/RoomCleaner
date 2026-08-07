# corner_mount -- independent verification report

> **STATUS UPDATE (2026-08-07, commit `a9c1a51`)**: the gusset/motor-body
> interference defect documented in the original Section 7 below has been
> repaired and independently re-verified. See **"Re-verification --
> 2026-08-07 (commit a9c1a51)"** at the end of this report for the full
> delta re-check (new measurements, interference re-probes, test audit, and
> the lead-requested FACE_TO_SPOOL/rub-gap assessment). The sections below
> this point are the **original, first-pass report and are kept as history**
> -- do not treat their now-superseded FAIL as the current state.

Scope: `cad/parts/corner_mount.py` (new; supersedes the eye-hook hanging
anchors per D13 in `DECISIONS.md`; unifies `motor_mount.py` +
`corner_guide.py` into one ceiling/joist bracket). This report covers Gate 5
(geometry-verifier role) only.

Verifier: geometry-verifier (Sonnet). Read-only against
`cad/parts/corner_mount.py`. Permanent tests exercised:
`tests/test_winch_geometry.py::test_corner_mount_*` (pre-existing, 19 tests).
All numbers below were reproduced independently by building `corner_mount.
make()` directly and probing the actual BRep solid (OCCT
`BRepClass3d_SolidClassifier` point-in-solid tests, void/solid bisection, and
boolean intersection volumes) -- not by reading source and trusting
docstrings/comments. Probe scripts used are described inline per section so
each result is reproducible.

Authority for expected values: `cad/interfaces.py` ("corner mount" block,
`CORNER_MOUNT_*`) and `cad/params.py` (`NEMA17_*`, `SPOOL_*`, `SCREW_M3`,
`CLEARANCE`), plus the lead ruling embedded in `corner_mount.py`'s module
docstring and the assignment's "INTENDED DESIGN" spec.

## Summary

| Area | Verdict |
|---|---|
| 1. Build / single valid solid | PASS |
| 2. Bounding box | PASS |
| 3. Countersink holes (position, dia, material under cone) | PASS |
| 4. NEMA17 pattern + boss + wall thickness | PASS |
| 5. Pulley ears (gap, thickness, axle dia, coaxiality, height) | PASS |
| 6. Fleet alignment (coplanarity, separation, height, spool-plate clearance, angle) | PASS |
| 7. Interference vs virtual spool cylinder | PASS (0 mm³) |
| 7. Interference vs NEMA17 motor-body envelope (42.3×42.3×38) | **FAIL at time of this report** (70.42 mm³, both gussets) -- **REPAIRED, see re-verification section at end** |
| 8. Wood-screw driver access from above | PASS |
| 9. STEP round-trip | PASS |
| Mass budget (≤90 g PETG) | PASS (83.14 g measured, 7.6 g margin) |
| Printability (downward-overhang scan) | PASS |

**Overall: FAIL** -- one real geometric defect (gusset/motor-envelope
interference), documented in Section 7. Not repaired, per instructions.

Reproduce the pre-existing suite:
`python -m pytest tests/test_winch_geometry.py -k corner_mount -v`
(19 passed -- none of them cover the Section 7 motor-envelope check, see
Section 10).

---

## 1. Build / BREP validity

`corner_mount.make()` executes with no exceptions.

- `solids()` count = **1**
- `isValid()` = **True**
- `Volume()` = **65463.50 mm³** (> 0)

PASS.

## 2. Bounding box

Expected envelope (assignment): plate ~148 × 58 × 6 mm base, with wall/ears
raising the Z extent above the plate. Repo test envelope:
X ∈ [130, 150], Y ∈ [55, 65].

Measured (`BoundingBox()` on the built solid):
**148.000 × 58.000 × 50.000 mm** (X × Y × Z), origin
X:[-74,74] Y:[-29,29] Z:[0,50].

- X: 148.0 mm, within [130,150] -- PASS
- Y: 58.0 mm, within [55,65] -- PASS
- Z: 50.0 mm = `PLATE_T(6) + WALL_H(44)` (wall taller than the ears, which top
  out at `PLATE_T + EAR_H = 34.5`) -- consistent with source, PASS

## 3. Countersink wood-screw holes

Expected (interfaces.py): shank ⌀5.2, csk ⌀10.5, 90° included angle, ≥45 mm
adjacent spacing, ≥2.5 mm material under each cone. 3 holes on Y=0 at
X = -55, -5, 45 (spacing 50/50 mm).

Probed on the built solid (point classifier at each hole's nominal
position):

| hole X | void at top (z=5.5) | void at bottom (z=0.5) | material 3 mm off-axis is solid | adjacent spacing |
|---|---|---|---|---|
| -55.0 | void -- PASS | void -- PASS | solid -- PASS | 50.0 mm (≥45) -- PASS |
| -5.0 | void -- PASS | void -- PASS | solid -- PASS | 50.0 mm (≥45) -- PASS |
| 45.0 | void -- PASS | void -- PASS | solid -- PASS | -- |

Countersink cone floor depth, direct probe (bisected on the built solid,
hole at x=-55): `depth = (csk_r - shank_r)/tan(45°) = (5.25-2.6) = 2.65 mm`,
so cone floor at `z = 6.0 - 2.65 = 3.35 mm`. Material remaining under the
floor down to the joist face (z=0) = **3.35 mm**, required ≥2.5 mm -- PASS.
Confirmed solid just below the theoretical floor and void just above it at
the same radius, at all 3 holes (parametrized test in the repo suite covers
hole 0 explicitly; I additionally confirmed via face inspection that all
three countersink faces are `CONE` type with `z ∈ [3.35, 6.00]` -- i.e. they
widen going up toward the plate top, the self-supporting print orientation
claimed in the module docstring).

All PASS.

## 4. NEMA17 motor bracket wall

Expected: 4× ⌀(SCREW_M3+0.4)=3.8 mm through-holes on a 31.0 mm square about
the boss center, boss clearance ⌀(NEMA17_BOSS_DIA+CLEARANCE)=22.2 mm, wall
≥6 mm thick, wall at negative Y clear of the Y=0 screw line.

Probed on the built solid (bisection along X through the wall thickness, at
the wall's mid-Y):

| feature | measured | expected | tol | verdict |
|---|---|---|---|---|
| 4× NEMA M3 hole ⌀ (all 4 corners) | 3.8000 mm | 3.8 mm | 0.05 | PASS |
| boss clearance ⌀ | 22.2000 mm | 22.2 mm | 0.05 | PASS |
| wall front (+Y) face | Y = -19.0000 | -19.0 (WALL_FRONT_Y) | -- | PASS |
| wall back (-Y) face | Y = -25.0000 | -25.0 (WALL_BACK_Y) | -- | PASS |
| **wall thickness (direct, not read off the constant)** | **6.0000 mm** | 6.0 (WALL_THK) | -- | PASS |

Wall thickness was probed independently (not present in the repo's own test
suite -- see Section 10): binary-searched the solid→void transition outward
from mid-wall in both +Y and -Y at a Z height clear of the hole pattern
(z = PLATE_T + 5), giving the wall's true built front/back faces, which
matched `WALL_FRONT_Y`/`WALL_BACK_Y` to 4 decimal places.

All PASS.

## 5. Pulley ears

Expected: 10.0 mm clear gap between ears, 7.0 mm ear thickness through the
axle hole, axle ⌀(SCREW_M3+0.3)=3.7 mm along Y, both ears symmetric about
Y=0, axle height = `CORNER_MOUNT_AXIS_Z`.

Probed on the built solid:

| feature | measured | expected | tol | verdict |
|---|---|---|---|---|
| axle hole ⌀ (both ears) | 3.7000 mm | 3.7 mm | 0.05 | PASS |
| **gap between ears (direct void span at z=PLATE_T+1)** | **10.0000 mm** | 10.0 (PULLEY_GAP) | -- | PASS |
| **ear thickness at axle hole (7.0 - hole 3.7 = 1.65 mm wall each side)** | open width 3.7000 mm, remaining wall 1.65 mm/side | ≥0.4 mm printable min | -- | PASS (well clear; contrast with the corner_guide 0.15 mm defect found in a prior verification pass) |
| **axle hole center X, Z, both ears (true coaxiality, not `len(set(EAR_SY))==2`)** | ear+10: x=60.0000, z=28.5000; ear-10: x=60.0000, z=28.5000 | x=EAR_CX=60.0, z=28.5 | -- | PASS -- identical to 4 decimal places, confirms a straight axle passes through both on the built geometry |
| axle height above plate top | 22.500 mm (from height-match test, motor/spool axis z agrees within tol) | CORNER_MOUNT_AXIS_Z=22.5 | ±3 mm | PASS |

The gap and ear-thickness probes were run independently (see Section 10 --
neither is in the repo's own suite). The gap probe swept Y outward from the
Y=0 centerline at the ear's base height (clear of the axle hole) and found
the void→solid transition at exactly ±5.0 mm, i.e. a 10.0 mm gap, matching
`PULLEY_GAP` exactly.

All PASS.

## 6. Fleet alignment

Expected: spool drum mid-length (XZ plane) coplanar with the pulley groove
mid-plane within ±2.0 mm; shaft-to-axle separation ≥60 mm along X; axle/boss
height match within ±3 mm; spool-flange-to-plate clearance ≥4 mm.

| check | measured | expected | tol | verdict |
|---|---|---|---|---|
| coplanarity (pulley mid-Y vs. spool drum mid-Y, both probed on built solid) | diff = 0.000 mm (both land at Y=0.000 by construction and by probe) | 0 | ±2.0 | PASS |
| separation (X, boss vs. axle) | 100.00 mm | ≥60.0 | -- | PASS |
| height match (motor/spool axis z vs. pulley axle z, both bisected on solid) | diff = 0.000 mm | -- | ±3.0 | PASS |
| **spool-flange-to-plate clearance** | `AXIS_Z(22.5) - SPOOL_FLANGE_DIA/2(18.0) = 4.500 mm` | ≥4.0 mm | -- | PASS (matches `CORNER_MOUNT_SPOOL_PLATE_CLEARANCE=4.5` in interfaces.py) |
| max fleet angle | `atan((SPOOL_LEN/2)/separation) = atan(13/100) = 7.41°` | ≤15° (repo test threshold) | -- | PASS |

The spool-plate clearance check has no dedicated test in the repo suite
(only a module-level `assert` at import time comparing two constants for
equality -- see Section 10); I additionally probed it by computing the
built axle height directly against `SPOOL_FLANGE_DIA` from `params.py`, both
of which independently agree with `interfaces.CORNER_MOUNT_SPOOL_PLATE_
CLEARANCE = 4.5`.

All PASS.

## 7. Interference sanity checks (new probes, not in repo suite)

**7a. Virtual spool cylinder vs. bracket.** Built a cylinder per the part's
own constants: axis along Y at (`WALL_CX`, `CORNER_MOUNT_AXIS_Z` above plate
top), diameter `SPOOL_FLANGE_DIA` = 36.0 mm (the widest part of the spool),
spanning `SPOOL_NEAR_Y`(-16.0) to `SPOOL_FAR_Y`(+16.0) (length
`2*SPOOL_FLANGE_THK + SPOOL_LEN` = 32.0 mm). Boolean-intersected with the
built `corner_mount` solid.

Measured intersection volume: **0.000000 mm³**. **PASS** -- the spool
envelope clears the bracket entirely (plate, wall, gussets, ears).

**7b. NEMA17 motor-body envelope vs. bracket -- FAIL (real defect).**
Built a 42.3 × 42.3 × 38 mm box (per the assignment's stated envelope:
`NEMA17_FACE` square cross-section × 38 mm body depth), positioned flush
against the wall's -Y (motor-bolting) face and extending further -Y (motor
hangs off the plate edge, which is accepted per the module docstring),
centered on the shaft axis (`WALL_CX`, `CORNER_MOUNT_AXIS_Z` above plate
top). Box Y-range: [-63.0, -25.0] (touching the wall's back face at
Y=-25.0). Boolean-intersected with the built solid, and separately with
just the plate, just the wall, and just the gussets to isolate the cause.

| body | intersection volume with motor envelope |
|---|---|
| plate alone | 0.000000 mm³ |
| wall alone | 0.000000 mm³ |
| **gussets (both)** | **70.423008 mm³** |

Interference bounding box (both gussets combined):
`X ∈ [-61.150, -18.850]` (spanning both gusset X-positions, symmetric about
`WALL_CX`), `Y ∈ [-27.747, -25.000]`, `Z ∈ [7.350, 22.000]`.

**Cause**: the two triangular gussets brace the wall's back face and run
`GUSSET_RUN = 3.0 mm` further in -Y (from Y=-25 to Y=-28, into the ~4 mm of
plate margin behind the wall -- see the module docstring's own account of
this constraint). But the -Y direction is exactly where the real NEMA17
motor body sits once bolted to that same wall face (Y ≤ -25). Because the
gusset X-offsets (`GUSSET_X_OFFSET = 21.4 mm` from `WALL_CX`) put the
gussets just inside the 42.3 mm motor-body half-width (21.15 mm from
`WALL_CX`), a ~1.75 mm-wide (X) sliver of each gusset, over its first ~3 mm
of -Y run and up to its full 16 mm height (tapering per the gusset's
triangular profile), lands inside the square motor-body envelope near two
of its corners.

**Caveat for engineering judgment**: this measures against a squared-corner
42.3×42.3 envelope, per the assignment's stated check. Real NEMA17 motors
commonly have small chamfered or rounded corners, which could clear this
sliver in practice depending on the specific motor SKU -- but that is a
fact about the purchased part, not something this bracket's geometry can
rely on without a spec. As modeled, and against the literal envelope this
assignment specifies, **this is a genuine, reproducible interference and
should be treated as a FAIL** pending either (a) a purchased-part corner
clearance confirmation, or (b) tightening `GUSSET_X_OFFSET` / `GUSSET_RUN`
in `cad/parts/corner_mount.py` so the gussets clear the full square
envelope.

**Reproduction** (probe script logic, standalone):
```python
import cadquery as cq
from cad.parts import corner_mount as cm
from cad import params as P

part = cm.make()
axis_z_world = cm.PLATE_T + cm.CORNER_MOUNT_AXIS_Z
NEMA_SQ, MOTOR_DEPTH = P.NEMA17_FACE, 38.0
y_near, y_far = cm.WALL_BACK_Y, cm.WALL_BACK_Y - MOTOR_DEPTH
motor_box = (
    cq.Workplane("XY").center(cm.WALL_CX, 0).rect(NEMA_SQ, MOTOR_DEPTH)
    .extrude(NEMA_SQ)
    .translate((0, 0, axis_z_world - NEMA_SQ / 2))
    .translate((0, (y_near + y_far) / 2, 0))
)
gussets = cm._gussets().translate((0, 0, cm.PLATE_T))
inter = motor_box.intersect(gussets)
print(inter.val().Volume())   # -> 70.423008 mm^3, nonzero => FAIL
```

## 8. Wood-screw driver access

Expected: a screwdriver approaching from +Z above each countersink must have
a clear column up to the bbox top (no wall/gusset/ear material in the way).

Probed (point classifier at each hole's `(x, 0.0, z)` for
`z ∈ {plate top+0.5, 25.0, 37.5, bbox_top-0.1}`):

| hole X | column clear |
|---|---|
| -55.0 | clear -- PASS |
| -5.0 | clear -- PASS |
| 45.0 | clear -- PASS |

All 3 holes sit on Y=0; the wall/gusset material lives entirely at
Y ∈ [-28, -19] and the ears at |Y| ≥ 5, so none intrude on the Y=0 driver
line even though hole x=-55 falls inside the wall's X-footprint
([-65, -15]) -- the wall doesn't extend to Y=0. PASS, all 3.

## 9. STEP round-trip

Exported `corner_mount` to STEP and reimported, independently of the repo
test (same method):

- reimport solids = **1**
- bbox: orig **148.0000 × 58.0000 × 50.0000**, reimport **148.0000 × 58.0000
  × 50.0000**, diff **0.000000 mm** (tol 0.1) -- PASS
- volume: orig **65463.5014 mm³**, reimport **65463.5014 mm³**, diff
  **0.000000 %** (tol 1%) -- PASS

## Mass budget

`Volume() = 65463.50 mm³` → `65.4635 cm³` × PETG 1.27 g/cm³ = **83.14 g**,
budget ≤90 g -- **PASS**, 7.6 g / 8.5% margin.

## Printability (downward-overhang scan, new probe)

Scanned all 40 faces of the built solid for planar faces with a
downward-facing normal whose overhang angle from vertical exceeds 45°.
Result: exactly **1** such face -- the plate's own bottom face at Z=0
(normal (0,0,-1), the print-bed contact face itself, not an overhang).
No other planar face qualifies. Separately confirmed all 3 countersink
faces are `CONE` type spanning `Z ∈ [3.35, 6.00]` (narrow at the bottom,
widening toward the plate top) -- the self-supporting orientation the
module docstring claims. Matches the design intent: PASS, no unexpected
overhangs found.

---

## 10. Audit of `tests/test_winch_geometry.py` corner_mount tests

19 tests exist (`test_corner_mount_*`), all currently passing. Per the
assignment's specific instruction to watch for tests that assert only
nominal arithmetic without probing the built solid:

**Tests that DO properly probe the built solid** (no defect in test
methodology): `test_corner_mount_builds_valid_single_solid`,
`test_corner_mount_bounding_box_within_declared_envelope`,
`test_corner_mount_countersink_hole_is_through_on_centerline` (parametrized,
uses `_inside_fn`/point classifier),
`test_corner_mount_countersink_depth_leaves_min_material` (bisects the cone
floor), `test_corner_mount_nema17_bolt_square_through_holes` (parametrized,
`_bisect_wall`), `test_corner_mount_nema17_boss_clearance` (`_bisect_wall`),
`test_corner_mount_pulley_axle_holes_present_and_coaxial` (diameter probed
via `_bisect_wall`), `test_corner_mount_fleet_alignment_height` (bisects
both axis heights on the solid), `test_corner_mount_fleet_alignment_
coplanarity` (bisects the wall's true front face and both ears' true Y
centers on the solid -- this is the test written specifically to replace the
first draft's defective, non-probing coplanarity check; it is done
correctly), `test_corner_mount_step_round_trip`.

**Tests that assert only nominal arithmetic on Python constants, without
probing the built solid** (the exact failure mode this assignment warned
about; flagged, not necessarily wrong, but weak):

1. `test_corner_mount_countersink_spacing_meets_declared_minimum` --
   computes gaps from `sorted(corner_mount.MOUNT_HOLE_X)` directly; never
   builds or measures the solid. Low risk here because `MOUNT_HOLE_X` is the
   same constant list the `pushPoints` call in `make()` consumes verbatim,
   so it can't silently diverge from the built geometry -- but it would not
   catch a bug in how `pushPoints`/`cskHole` place the holes.
2. `test_corner_mount_pulley_axle_holes_present_and_coaxial` -- the diameter
   half of this test *does* probe the solid (via `_bisect_wall`), but its
   coaxiality assertion is `assert len(set(corner_mount.EAR_SY)) == 2`, i.e.
   "the two Y source values are distinct" -- pure Python-object arithmetic,
   not a measurement that both axle holes actually share the same X and Z on
   the built solid. I independently probed true coaxiality (Section 5
   above) and it holds (both centers land at x=60.0000, z=28.5000 exactly),
   so there is no live defect, but the *test* would not catch one if a
   future edit gave the two ears different `EAR_CX` or hole-height formulas.
3. `test_corner_mount_fleet_separation_minimum` -- `distance = abs(
   corner_mount.EAR_CX - corner_mount.WALL_CX)`, pure constant arithmetic;
   never confirms `EAR_CX`/`WALL_CX` are where the actual axle/boss holes
   sit on the built solid (though the diameter-probe tests above do
   incidentally confirm holes exist at those exact coordinates, so in
   combination the suite is sound -- but this specific test alone is
   non-probing).
4. `test_corner_mount_max_fleet_angle_reasonable` -- same pattern,
   `math.degrees(math.atan((P.SPOOL_LEN/2)/separation))` computed from
   constants only.

**Acceptance criteria in the assignment with NO test coverage at all** (not
even a nominal-arithmetic one) in `tests/test_winch_geometry.py`:

- Wall thickness (`WALL_THK` ≥ 6 mm) as a directly measured built-solid
  dimension -- I added this probe in Section 4; not present in the repo
  suite.
- Pulley gap (`PULLEY_GAP` = 10.0 mm) as a directly measured built-solid
  span -- Section 5; not present.
- Ear thickness through the axle hole (`EAR_PLATE_T` = 7.0 mm, remaining
  wall) -- Section 5; not present. (This is exactly the defect class found
  in `corner_guide`'s 0.15 mm wall during the prior verification pass --
  worth a permanent regression test here given the history.)
- Spool-flange-to-plate clearance (`CORNER_MOUNT_SPOOL_PLATE_CLEARANCE` ≥
  4 mm) -- only a module-level `assert` at import time in
  `corner_mount.py` comparing `SPOOL_AXIS_Z == CORNER_MOUNT_AXIS_Z` (a
  tautology check, not an independent pytest assertion, and not in
  `tests/`) -- Section 6; not present in the test suite.
- Interference vs. a virtual spool envelope -- Section 7a; not present.
  This is the one check I ran that came back clean (0 mm³).
  **Recommend adding as a permanent regression test given it's cheap and
  currently passes.**
- Interference vs. the NEMA17 motor-body envelope vs. plate/gussets --
  Section 7b; not present. **This is where the real defect was found; had
  this check existed as a permanent test, it would already be red.**
  Strongly recommend adding it as a permanent regression test (it will
  correctly FAIL until the gusset geometry is fixed).
- Wood-screw driver access clearance from above -- Section 8; not present.
- Printability / downward-overhang scan -- Section 8 is 8, printability is
  its own item; not present as an automated check anywhere (only asserted
  informally in the module docstring's narrative).

---

## Test run

```
python -m pytest tests/test_winch_geometry.py -k corner_mount -v
...
19 passed in 7.07s
```

```
python -m pytest tests/ -q
...
124 passed in 41.85s
```

The full repository suite is currently green (124/124). None of the
existing tests cover the Section 7b motor-envelope interference -- that
defect is real but has zero automated coverage today, which is why the
suite shows all-green while the bracket, as built, has a genuine (if small)
clash between the bracing gussets and the space a real NEMA17 motor body
occupies once bolted to the wall.

## Findings requiring a decision

1. **Gusset/NEMA17-motor-envelope interference (FAIL, Section 7)** --
   70.42 mm³ overlap between the two bracing gussets and a 42.3×42.3×38 mm
   squared NEMA17 motor-body envelope, concentrated in a ~1.75 mm × ≤3 mm ×
   ≤14.65 mm sliver near two of the envelope's corners. Recommend routing to
   `cad-implementer` for a bounded fix (reduce `GUSSET_RUN` and/or increase
   `GUSSET_X_OFFSET`/widen the motor-corner clearance margin in
   `cad/parts/corner_mount.py`), OR a lead decision to accept it pending
   confirmation that the specific purchased NEMA17 SKU has corner chamfers
   large enough to clear this sliver. Not repaired here, per instructions.
2. **Test-coverage gaps** (Section 10) -- recommend adding permanent
   regression tests for: wall thickness, pulley gap, ear wall thickness at
   the axle hole, spool-plate clearance, the virtual-spool interference
   check (passes today), and especially the motor-envelope interference
   check (currently failing -- would catch finding #1 automatically going
   forward). Also recommend strengthening the two nominal-arithmetic-only
   fleet tests (`test_corner_mount_fleet_separation_minimum`,
   `test_corner_mount_max_fleet_angle_reasonable`) to probe the built solid
   directly, matching the pattern already used correctly in
   `test_corner_mount_fleet_alignment_coplanarity`.

---

# Re-verification -- 2026-08-07 (commit `a9c1a51`)

Verifier: geometry-verifier (Sonnet), independent of the implementer.
Read-only against `cad/parts/corner_mount.py`; no part files modified.
Scope: focused delta re-check of the implementer's claimed repair (commit
`a9c1a51`, "Fix corner_mount gusset/motor-body interference; harden
tests") against Finding #1 and the test-coverage gaps from the original
report above. All numbers below are from fresh, independent probe scripts
(new boolean intersections, new bisection probes, a side-loaded copy of the
pre-repair module) run against the current `cad/parts/corner_mount.py` --
none of the implementer's own numbers were taken on faith.

## What changed (verified against the diff, not just the commit message)

`git diff 1d77324 a9c1a51 -- cad/parts/corner_mount.py` confirms the
implementer's claimed changes: `WALL_W` 50→56, gussets repositioned via a
new `MOTOR_CORNER_CLEARANCE=2.0` constraint (`_gusset_inner_edge` now takes
`max()` of the old NEMA-bolt-pattern clearance and
`NEMA17_FACE/2 + MOTOR_CORNER_CLEARANCE`), `BASE_L` 148→138, `BASE_W`
58→65, `FACE_TO_SPOOL` 3.0→0.0, and `GUSSET_RUN`/`GUSSET_HEIGHT` restored
from the shrunk 3.0/16.0 (temporary mitigation in the very first draft) to
a full 10.0/18.0.

## 1. Re-run of my own interference scripts (independent reproduction)

**7a. Virtual spool cylinder vs. bracket** (same method as the original
report: cylinder ⌀`SPOOL_FLANGE_DIA`=36.0 mm, length
`SPOOL_LEN + 2*SPOOL_FLANGE_THK`=32.0 mm, on the shaft axis per the part's
own constants):

- Measured intersection volume: **0.000000 mm³** -- PASS (unchanged from
  the original pass; this check never found a defect).

**7b. NEMA17 motor-body envelope (42.3×42.3×38 mm, flush against the
wall's -Y face) vs. bracket** -- re-run of the exact script that found the
original 70.42 mm³ defect, against the new geometry:

| body | intersection volume vs. motor envelope |
|---|---|
| whole part | **0.000000 mm³** |
| plate alone | 0.000000 mm³ |
| wall alone | 0.000000 mm³ |
| gussets alone | **0.000000 mm³** (was 70.423008 mm³) |
| ears alone | 0.000000 mm³ |

**PASS -- the defect is repaired.** Motor envelope bbox measured as
X∈[-61.15,-18.85], Y∈[-60.00,-22.00], Z∈[7.35,49.65] (Y-range shifted
versus the original report because `WALL_BACK_Y` moved from -25 to -22
with the smaller `FACE_TO_SPOOL`; the box is still seated flush against
the wall's measured back face in both cases).

**Root-cause confirmation**: to be sure this isn't a coincidence of the
new envelope's position, I re-ran the *identical* motor-envelope
intersection script (unchanged) against a side-loaded copy of the
pre-repair module (`git show 1d77324:cad/parts/corner_mount.py`, imported
from an isolated `cad` package copy so the tracked repo file was never
touched): **70.423008 mm³** -- reproduces the original defect exactly.
This confirms the fix, not the check, changed.

## 2. Re-measurement of the full geometry

All measured directly on the rebuilt solid (`corner_mount.make()`), not
read off source constants:

| quantity | measured | claimed | tol | verdict |
|---|---|---|---|---|
| solid validity / count | isValid=True, 1 solid | -- | -- | PASS |
| bbox | 138.0000 × 65.0000 × 50.0000 mm | 138×65×50 | -- | PASS |
| volume | 69891.5014 mm³ | -- | -- | -- |
| mass (PETG 1.27 g/cm³) | **88.7622 g** | 88.76 g | budget ≤90 g | PASS (1.24 g / 1.4% margin -- tight but real) |
| gusset centers (measured X-span of built gusset material) | X-range [-67.150,-63.150] (center -65.15) and [-16.850,-12.850] (center -14.85), width 4.000 mm each | -65.15 / -14.85 | -- | PASS |
| wall thickness (bisected, independent probe point near the boss) | 6.0000 mm | WALL_THK=6.0 | -- | PASS |
| wall front/back Y (bisected) | front -16.0000, back -22.0000 | WALL_FRONT_Y=-16.0, WALL_BACK_Y=-22.0 | -- | PASS |
| back margin behind wall (`BASE_W/2 + WALL_BACK_Y`) | 10.500 mm | -- | ≥ GUSSET_RUN=10.0 | PASS, **0.5 mm margin only** -- flagged below |
| fleet separation (X, boss vs. axle) | 95.0 mm | 95 mm | ≥60 required | PASS |
| fleet coplanarity | drum mid Y = 0.0000 mm exactly (by construction and by the existing probing test) | 0 | ±2.0 | PASS |
| fleet height match | axis Z agreement, unchanged from original pass | -- | ±3.0 | PASS |
| max fleet angle | atan(13/95) = **7.7921°** | 7.79° | -- | PASS |
| spool-plate clearance | `SPOOL_AXIS_Z(22.5) - SPOOL_FLANGE_DIA/2(18.0)` = **4.500 mm** | -- | ≥4.0 | PASS |
| countersink spacing (BASE_L now 138, re-checked in case the shrink broke it) | gaps 50.0 / 50.0 mm at x = -55, -5, 45 (unchanged `MOUNT_HOLE_X`) | ≥45 mm | -- | PASS |
| countersink hole clearance vs. new footprints | wall X-range now [-68,-12] (was [-65,-15]); ear X-range now [51.5,58.5] (moved with `EAR_CX`=55, was 60); hole x=45 to ear inner edge = 6.50 mm clear; hole x=-55 inside wall's X-range but wall lives at Y∈[-32,-22], not Y=0, so no interference | -- | -- | PASS |
| screwdriver access (+Z clear from plate top to bbox top) | all 3 holes clear at every probed Z | -- | -- | PASS |
| STEP round-trip | 1 solid; bbox diff 0.000000 mm; volume diff 0.000000% | tol 0.1mm / 1% | -- | PASS |

**All claimed numbers reproduced exactly to the reported precision.** No
discrepancies found between the implementer's claims and independently
measured values.

One new observation, not a defect but worth flagging: the back margin
behind the wall (10.5 mm) now has only **0.5 mm** of slack over the
`GUSSET_RUN` requirement of 10.0 mm (the code's own `assert GUSSET_RUN <=
_back_margin` would trip at `GUSSET_RUN > 10.5`). This is by design (traded
plate depth for the wider wall/gussets within the declared 55-65 mm Y
envelope, landing at its very top), but it leaves no room for a future
`GUSSET_RUN` increase without either shrinking `FACE_TO_SPOOL` further
(already at 0) or exceeding the declared Y envelope.

## 3. Audit of the upgraded/new tests

Reviewed `git diff 1d77324 a9c1a51 -- tests/test_winch_geometry.py`
directly (not just re-running the tests) to confirm the changes are real
probes, not relabeled arithmetic:

- **`test_corner_mount_countersink_spacing_meets_declared_minimum`** --
  previously sorted `MOUNT_HOLE_X` directly (flagged in the original
  report). Now bisects each hole's true void→solid X-center on the built
  solid via a new shared helper `_measure_center_offset_1d` and computes
  spacing from the *measured* centers. Genuinely upgraded.
- **`test_corner_mount_pulley_axle_holes_present_and_coaxial`** --
  previously `assert len(set(EAR_SY)) == 2` (flagged). Now bisects each
  ear's hole center along both X and Z independently and requires the two
  measured (x,z) pairs to agree within 0.05 mm. Genuinely upgraded --
  would now catch a future edit that gave the two ears different `EAR_CX`
  or hole-height formulas, which the old version could not.
- **`test_corner_mount_fleet_separation_minimum`** -- previously
  `abs(EAR_CX - WALL_CX)` (flagged). Now bisects the boss void and one
  ear's axle void on the built solid and computes distance from measured
  centers. Genuinely upgraded.
- **`test_corner_mount_max_fleet_angle_reasonable`** -- **not changed**;
  still pure arithmetic on `P.SPOOL_LEN` and the (now itself
  solid-derived, per the previous item, but not re-derived *within this
  test*) `separation` value computed from `EAR_CX`/`WALL_CX` constants.
  This is a minor residual gap: low risk in practice because the
  separation test right above it now does probe the solid, but this
  specific test would not independently catch a regression on its own.
  Not a blocker, flagged for a future pass.
- **`test_corner_mount_gussets_clear_motor_body_envelope`** (new) --
  reproduces my original Section 7b method exactly: builds the 42.3×42.3×
  38 mm box flush against the wall's -Y face, boolean-intersects with the
  whole built part, asserts `< 1e-6 mm³`. **Confirmed this test would fail
  on the pre-repair geometry**: I ran its exact logic against a
  side-loaded copy of commit `1d77324`'s `corner_mount.py` (isolated
  import, tracked file untouched) and got **70.423008 mm³**, which fails
  the `< 1e-6` assertion. This is a real, working regression test for
  Finding #1.
- **`test_corner_mount_clears_virtual_spool_envelope`** (new) -- same
  boolean-intersection method as my original Section 7a probe. Passes on
  both old and new geometry (0 mm³ both times) since this was never
  defective -- correctly a no-op regression guard, not a repair
  verification.
- **`test_corner_mount_wall_thickness_through_boss_measured`** (new) --
  bisects solid↔void transitions on both sides of the wall near the boss
  hole; independently reproduced (6.0000 mm) above. Fills the wall-
  thickness gap flagged in the original report.
- **`test_corner_mount_pulley_gap_measured`** (new) -- bisects the void
  span between the ears at a Z clear of the axle hole; fills the
  `PULLEY_GAP` coverage gap flagged in the original report.
- **`test_corner_mount_ear_wall_around_axle_hole_measured`** (new) --
  bisects the ear's true thickness and the hole radius, computes wall/side,
  asserts ≥1.0 mm. This directly targets the defect class found in
  `corner_guide` (0.15 mm wall) during the earlier verification pass --
  good, targeted regression coverage.
- **`test_corner_mount_spool_plate_clearance_measured`** (new) -- bisects
  the boss axis height on the solid and derives clearance from
  `SPOOL_FLANGE_DIA`, rather than trusting `CORNER_MOUNT_AXIS_Z` directly.
  Fills the spool-plate-clearance coverage gap flagged in the original
  report.

Net: of the 6 gaps and weak/nominal-only tests flagged in the original
report's Section 10, **5 are now properly probing tests** and 1
(`test_corner_mount_max_fleet_angle_reasonable`) remains nominal-only but
low-risk given its neighbor now probes the solid. The screwdriver-access
and printability/overhang checks from the original Section 8 still have no
permanent test coverage (still assignment-only manual checks, re-verified
by hand in Section 2 above) -- minor residual gap, not blocking.

Test counts: `test_corner_mount_*` = **25** (matches claim), full repo
suite = **130 passed** (matches claim).

## 4. Lead-requested assessment: `FACE_TO_SPOOL = 0` and the rub-gap risk

The lead's concern is correct and worth stating precisely.

**How the model works today**: `WALL_FRONT_Y = -(FACE_TO_SPOOL +
SPOOL_FLANGE_THK + SPOOL_LEN/2)` and `SPOOL_NEAR_Y = WALL_FRONT_Y +
FACE_TO_SPOOL`. With `FACE_TO_SPOOL = 0`, `SPOOL_NEAR_Y` lands exactly on
`WALL_FRONT_Y` -- i.e. the model places the spool's near flange face
**flush against the wall's front face, zero gap**. `SPOOL_DRUM_MID_Y = 0`
by construction for *any* `FACE_TO_SPOOL` value (the term cancels
algebraically), so shrinking `FACE_TO_SPOOL` to 0 doesn't change the
nominal coplanarity claim -- but it does mean the part now models an
assembly with no physical standoff at all between two things that must
rotate relative to one another (the spool spins; the wall does not).

**What a real assembly gap does to alignment**: if a real build introduces
an axial rub-gap `g` (spool shifted `+g` in Y, away from the wall, to
clear rubbing), then `SPOOL_NEAR_Y_real = WALL_FRONT_Y + g`, so
`SPOOL_DRUM_MID_Y_real = 0 + g = g`. **The drum mid-plane shifts 1:1 with
the gap** -- every mm of rub clearance is a full mm of coplanarity error
against the pulley groove mid-plane (which stays fixed at Y=0, set by the
ears).

**Quantified**:
- Coplanarity tolerance is `CORNER_MOUNT_FLEET_COPLANAR_TOL = ±2.0 mm`
  (interfaces.py). Since the mapping is 1:1, **the admissible assembly gap
  before exceeding tolerance is exactly g ≤ 2.0 mm.** There is no other
  slack in the budget to draw on -- `SPOOL_DRUM_MID_Y` is otherwise exactly
  0.0000 mm (verified above), so the entire ±2 mm tolerance band is
  available for the gap, but all of it, and none of it is buffer for
  anything else (fabrication tolerance on `SPOOL_FLANGE_THK`/`SPOOL_LEN`,
  print dimensional error on `WALL_FRONT_Y`, etc.).
- Fleet-angle bias contributed by a 2 mm gap, at the current 95 mm
  separation: `atan(2/95) = 1.2060°`. Added (worst case, same sense) to
  the existing `atan(13/95) = 7.7921°` winding-width angle gives a
  combined worst-case fleet angle of **≈9.00°**, still comfortably under
  the repo's 15° working-limit test threshold, but consuming real margin
  that a coplanarity-perfect assembly wouldn't spend.

**Assessment**: this is **acceptable as an assembly-procedure note, not a
geometry defect** -- but only if it is actually written down and enforced,
because nothing in the CAD or the test suite currently constrains the real
build's rub gap. Concretely:
1. `FACE_TO_SPOOL = 0` should not be read as "zero clearance is the
   design," it should be read as "this model does not budget any
   clearance -- the assembler must add ≤2 mm and no more."
2. Recommend adding an explicit note to `interfaces.py` or the spool's own
   part docs (whichever eventually models the coupling) stating the ≤2 mm
   rub-gap ceiling, and/or a physical shim/spacer feature sized into that
   budget rather than leaving it to an assembler's judgment at build time,
   since 2 mm is not a generous margin to hit by eye.
3. If any other error source shares this ±2 mm coplanarity budget (e.g.
   coupling squareness, spool print tolerance on `SPOOL_FLANGE_THK`), the
   admissible rub gap is less than 2 mm in practice -- worth a stack-up
   check before finalizing an assembly procedure, not something this
   geometry-only pass can resolve.

This is a documentation/process finding, not a geometry FAIL -- no part
file change is being recommended here.

## Summary of this re-verification

| Item | Verdict |
|---|---|
| Finding #1 (gusset/motor-envelope interference) | **RESOLVED** -- 0.000000 mm³, confirmed by independent reproduction and by re-running the identical check against the pre-repair geometry (reproduces the original 70.42 mm³) |
| Virtual spool interference | PASS (unchanged, 0 mm³) |
| All re-measured geometry (bbox, mass, gusset positions, wall thickness, fleet metrics, spool-plate clearance, countersink spacing/access) | PASS, all claimed numbers reproduced exactly |
| STEP round-trip | PASS |
| Test upgrades | 5/6 flagged gaps now have genuine solid-probing tests; 1 residual low-risk nominal-only test (`test_corner_mount_max_fleet_angle_reasonable`) |
| New regression tests catch the old defect | Confirmed -- `test_corner_mount_gussets_clear_motor_body_envelope` fails (70.42 mm³) against the pre-repair module |
| Test counts | 25 corner_mount tests, 130 repo-wide -- both match the implementer's claim |
| FACE_TO_SPOOL=0 / rub-gap | Not a geometry defect; admissible real-world gap ≤2.0 mm (1:1 with coplanarity tolerance), adds ≈1.21° fleet-angle bias at the 2 mm limit (worst case ≈9.00° combined, still under the 15° threshold) -- recommend an explicit assembly-procedure note, not a geometry change |

**Overall verdict: PASS.** The repair is real and independently confirmed;
no outstanding geometry defects found in this pass. One process
recommendation (rub-gap note) and one minor residual test-coverage
suggestion, neither blocking.

Reproduce: `python -m pytest tests/test_winch_geometry.py -k corner_mount -v`
(25 passed) and `python -m pytest tests/ -q` (130 passed).
