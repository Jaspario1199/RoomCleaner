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

---

# Rev B: homing-switch mount

Verifier: geometry-verifier (Sonnet), independent of the implementer.
Read-only against `cad/parts/corner_mount.py` (uncommitted working-tree
revision, not yet committed as of this pass); no part file modified. Scope:
the KW12-3 cable-homing limit-switch mount added this revision (module
docstring section "HOMING SWITCH", constants `KW12_*`/`KW_*`, functions
`_kw12_leg`/`_kw12_switch_boss`), plus a regression re-check of everything
verified in the prior two sections above. All numbers below are from a
fresh, independent probe script built against this file's own real
geometry (BRep point-in-solid classification via
`BRepClass3d_SolidClassifier`, bisection to solid/void transitions,
boolean-intersection volumes) — none of the implementer's numbers were
taken on faith. Probe script:
`/tmp/claude-0/-home-user-RoomCleaner/c51aa926-76d6-52eb-b707-af7c5e22fd24/scratchpad/probe_corner_mount.py`
(full listing reproducible from this report's method descriptions if that
path is unavailable).

## Summary

| Area | Verdict |
|---|---|
| Baseline regression (plate 138x65x6, csk x3, motor-envelope 0mm³, spool-envelope 0mm³, coplanarity 0mm, separation 95mm, STEP round-trip) | **PASS, unchanged** |
| 1. Boss legs: leading edge, X-center, boss height, lever-Z target | **PASS** |
| 2. Line-corridor boolean (own construction) | **PASS**, 0.000000 mm³ |
| 3. Switch-body envelope vs. part / spool / driver columns | **PASS**, 0.000000 mm³ all three |
| 4. Slots: pilot pitch/width, zip-tie through-cuts, ±5mm travel, M2 head clearance | **PASS** |
| 5. Mass | **PASS**, 92.1465 g measured (claimed 92.15 g), delta +3.3843 g (claimed +3.384 g) |
| 6. New-test audit (7 tests, boss-deletion check) | **4/7 correctly fail without the boss; 2/7 structurally cannot detect its absence; 1/7 not applicable by design — see detail** |
| 7. Printability (>45° overhang scan) | **PASS**, no new overhangs |
| 8. STEP round-trip | **PASS** |
| Homing physics (Z alignment / X alignment / Y-reach) | **Z and X are geometrically supported; the lever's Y-reach into the bead's path is an UNVERIFIED assumption — see assessment below (not a geometry FAIL, a documented gap)** |

**Overall: PASS** on all measurable geometry claims (baseline unchanged, all
7 new-feature checks reproduce 0 mm³/exact-dimension claims). Two findings
requiring lead attention, neither a geometry defect: (a) a real but narrow
test-coverage gap in 2 of the 7 new tests (Section 6), and (b) the homing
lever's actual roller position in Y is never modeled or checked anywhere in
the code or test suite (Homing Physics Assessment, below) — the part's own
Z-height engineering is sound, but whether the purchased switch's lever
physically reaches the bead's line is not something this geometry can
confirm on its own.

## 0. Baseline regression (must be unchanged)

Re-ran my own independent scripts (not the repo's), reproducing the
Rev-A re-verification's exact methods against the current file:

| check | measured | expected | verdict |
|---|---|---|---|
| solids / validity | 1 / isValid=True | -- | PASS |
| bbox | 138.0000 × 65.0000 × 50.0000 mm | 138×65×6(+wall/ear/boss stack) | PASS |
| 3 countersinks (x=-55,-5,45) void top+bottom | all void | -- | PASS |
| motor-body envelope (42.3×42.3×38) vs. part | 0.000000 mm³ | 0 | PASS |
| virtual-spool envelope vs. part | 0.000000 mm³ | 0 | PASS |
| fleet coplanarity (pulley mid-Y vs. spool drum mid-Y) | diff 0.0000 mm | ±2.0 | PASS |
| fleet separation (X, boss vs. axle, both bisected on solid) | 95.000 mm | ≥60.0 | PASS |
| STEP round-trip | 1 solid, bbox diff 0.000000 mm, volume diff 0.000000% | tol 0.1mm/1% | PASS |

No regression. The baseline geometry is byte-for-byte unchanged from the
Rev-A re-verification's measured values (138×65×50 bbox, 95 mm separation,
0 mm³ both interference checks, 0 mm coplanarity).

## 1. Boss legs

| quantity | measured (on built solid) | declared/target | verdict |
|---|---|---|---|
| boss leading edge Y | **4.0000 mm** (bisected at a probe X outside both slots' X-ranges but inside the leg's own X-footprint, avoiding the false reading a naive centerline probe gives — see method note below) | KW_BOSS_Y0=4.0; must be ≥3.0 exclusion | PASS, 1.0 mm margin over the 3.0 mm hard minimum, matches declared |
| boss X-center | **10.000 mm** (bisected leg outer X-edges: [1.000, 19.000]) | ~10.0 | PASS |
| boss top Z (local, above plate top) | **13.5000 mm** | KW_BOSS_H=13.5 | PASS |
| estimated lever pivot Z, WORLD frame (boss top + KW12_LEVER_HEIGHT_ABOVE_MOUNT, PLATE_T=6 included) | **24.5000 mm** | assignment target "≈24.5 local" (this figure is a world-Z value including PLATE_T — see note) / window [20.5, 36.5] | PASS, inside window with margin (4.0 mm below the corridor's own Z-center of 28.5, 8.0 mm above the low bound, 12.0 mm below the high bound) |

**Method note on the leading-edge probe**: a naive probe straight up from
the boss's nominal centerline X (`KW_TRIGGER_X=10`) and bisecting toward -Y
does **not** find the true boss edge — it finds the near edge of the
zip-tie through-slot instead (measured 8.0 mm, not 4.0), because the
zip-tie slot's own X-range ([3,17] for the front leg) covers the
centerline. I re-probed at `x = KW_BOSS_X0 + 0.5 = 1.5` (inside the leg's
X-footprint but outside both the zip-tie slot's X-range [3,17] and the
pilot slot's X-range [4.15,15.85]) and got the correct **4.0000 mm**,
exactly matching `KW_BOSS_Y0`. Flagging this because it is exactly the
kind of probe-methodology trap the assignment is watching for, and it is
worth noting for anyone re-running spot checks on this boss.

**Note on the "Z=13.5+plate" / "Z≈24.5 local" figures in the assignment**:
these are consistent once the reference frame is made explicit. This
part's own internal `KW_BOSS_H`/`KW_LEVER_TARGET_Z` constants are in the
**local** frame (relative to the plate's own top face, `Z=0` at
`PLATE_T`); the assignment's stated `20.5`–`36.5` window and `≈24.5` figure
are in the **world** frame (`Z=0` at the plate's bottom / joist face,
i.e. local + `PLATE_T`). `PLATE_T(6) + KW_LEVER_TARGET_Z(18.5) = 24.5`
world, and `PLATE_T(6) + CORNER_MOUNT_AXIS_Z(22.5) ± 8 = [20.5, 36.5]`
world — both match exactly. No discrepancy, just two valid reference
frames; noting it here since a same-frame comparison error (which I made
once while writing the probe script and then corrected) is an easy trap.

## 2. Line-corridor boolean (own construction, independent of the repo test)

The repo's own new test (`test_corner_mount_kw12_line_corridor_clearance`)
builds its corridor spanning only `WALL_CX` to `EAR_CX` in X. I built the
corridor two additional, independent ways:

1. **Full-part-X-span corridor** (X spans the ENTIRE built bbox, not just
   spool-to-pulley — a stricter check than the repo test, since it also
   catches anything the boss might do outside the nominal spool-pulley
   span): Y ∈ [-3, 3], Z ∈ [axis-8, axis+8]. Intersection with the built
   part: **0.000000 mm³**.
2. **YZ-workplane construction** (built by extruding a rectangle along X
   from a YZ workplane, a structurally different CadQuery construction path
   than the repo test's XY-workplane rectangle, to rule out a construction-
   specific false negative): same result, **0.000000 mm³**.

**PASS**, reproduced two independent ways, both stricter than or
structurally different from the repo's own test.

## 3. Switch-body envelope

Built the 20.0×6.4×10.0 mm switch-body box at its declared mounted
position (resting on the boss top, centered on `KW_TRIGGER_X`, spanning
`KW_BODY_Y_FRONT`→`KW_BODY_Y_BACK`) — measured box: X[6.80,13.20]
Y[5.50,25.50] Z[19.50,29.50], dims 6.40×20.00×10.00, matching the declared
20.0×6.4×10.0 (L×W×H) exactly.

| intersection | volume | verdict |
|---|---|---|
| switch-body envelope vs. built part | 0.000000 mm³ | PASS |
| switch-body envelope vs. virtual SPOOL envelope (same cylinder as baseline Section 7a) | 0.000000 mm³ | PASS, no collision |
| switch-body envelope vs. wood-screw driver-access column at x=-55 | 0.000000 mm³ | PASS |
| switch-body envelope vs. driver-access column at x=-5 | 0.000000 mm³ | PASS |
| switch-body envelope vs. driver-access column at x=45 | 0.000000 mm³ | PASS |

All PASS — the switch seats flush on the boss with no interference against
the bracket, the spool, or any wood-screw's vertical driver-access column.

## 4. Slots

| feature | measured | expected | verdict |
|---|---|---|---|
| pilot pitch (KW_SCREW_Y[1] - KW_SCREW_Y[0]) | 9.5000 mm | 9.5 (KW12_HOLE_SPACING) | PASS |
| pilot slot width (bisected, both slots) | 1.7000 mm both | 1.7 (1.7mm self-tap class) | PASS |
| pilot slot: blind (solid below KW12_PILOT_DEPTH), both slots | solid, confirmed | blind hole | PASS |
| pilot slot X-travel: void at nominal ±5mm ends, solid just beyond | void at ±5, solid at ±5.85 (pilot radius) beyond | ±5.0 mm (KW_TRIGGER_ADJ_RANGE/2) | PASS, both slots |
| zip-tie slot width (bisected inward half, ×2) | 2.0000 mm half-width (4.0 mm total) both slots | 4.0 mm (KW_ZIPTIE_SLOT_W, ≥3.5 required) | PASS |
| zip-tie slot: through-cut (void near boss base AND boss top) | void both ends, both slots | through-cut, not blind | PASS |
| zip-tie slot: open-notch outward side (void beyond the slot, flush to boss edge, no forward wall) | void, both slots | open notch per docstring | PASS, matches the "no forward wall" design claim |
| zip-tie slot X-travel | void at nominal ±5mm ends, both slots | ±5.0 mm | PASS |
| M2 screw head clearance from above (4mm-dia column swept above the switch body top, up through the rest of the bracket to bbox top) | clear at all sampled Z/angle combinations, both screws | no obstruction | PASS |
| M2 screw shank clearance straight down through the pilot slot | clear, both screws | clear path to the pilot | PASS |

All PASS. Note the zip-tie width measurement used a directional (inward-only)
bisection rather than a symmetric one, because the slot is an intentional
open notch flush to the boss's own leading/trailing edge on the outward
side (confirmed void there too, consistent with the docstring's "needs no
forward wall" design note) — a naive symmetric bisection from center would
fail outright on the open side (no solid to find), which is itself a useful
confirmation that the open-notch claim is real, not just asserted.

## 5. Mass

- Total part mass (measured): **92.1465 g** (volume 72556.3114 mm³ × PETG
  1.27 g/cm³). Claimed: 92.15 g. **Match** (rounds identically).
- Mass delta vs. the Rev-A baseline (88.7622 g, from the prior
  re-verification section above): **+3.3843 g**. Claimed: +3.384 g.
  **Match.**
- Budget: 92.1465 g ≤ `MASS_BUDGET_G` = 93.5 g — **PASS**, 1.35 g / 1.4%
  margin (tight, consistent with the module docstring's own stated intent
  to "keep roughly the same ~1.3 g margin style").
- KW12 boss's own volume, measured directly via `_kw12_switch_boss()`
  (isolated from the rest of the part): 2665.5 mm³ → 3.3843 g, matching the
  whole-part delta above exactly (confirms the delta is attributable
  entirely to the new boss, not a side effect on other geometry).

## 6. New-test audit (7 new tests)

`test_corner_mount_kw12_*` = 7 test cases (32 total `test_corner_mount_*`
now, 25 pre-existing + 7 new — matches the assignment's count), all
currently passing:
`test_corner_mount_kw12_boss_present_at_declared_position`,
`test_corner_mount_kw12_line_corridor_clearance`,
`test_corner_mount_kw12_ziptie_slots_are_through_cuts[0]` and `[1]`
(parametrized, 2 cases),
`test_corner_mount_kw12_switch_footprint_envelope_clear`,
`test_corner_mount_kw12_mass_delta_within_budget`,
`test_corner_mount_kw12_lever_target_within_corridor_z_band`.

All 7 probe the built solid via `BRepClass3d_SolidClassifier`/boolean
intersection, not bare Python constants — none of them are the "nominal
arithmetic only" failure mode flagged against the pre-existing suite in
Section 10 above.

**Boss-deletion check** (per the assignment's specific request): built an
isolated copy of the whole `cad` package
(`/tmp/claude-0/.../scratchpad/isolated_bossless/cad/`, side-loaded from a
fresh Python process so the tracked repo file was never touched), with the
`kw12_boss.translate(...)` union commented out of `make()` (boss geometry
still built by `_kw12_switch_boss()`, just never unioned into the part),
then re-ran each of the 7 tests' own logic against that boss-less rebuild:

| test | result against boss-less rebuild |
|---|---|
| `kw12_boss_present_at_declared_position` | **CORRECTLY FAILS** — probe point that should be solid boss material reads void |
| `kw12_ziptie_slots_are_through_cuts[0]` | **CORRECTLY FAILS** — the "material expected just inward of the slot" assertion finds void instead (no leg at all) |
| `kw12_ziptie_slots_are_through_cuts[1]` | **CORRECTLY FAILS** — same, back leg |
| `kw12_lever_target_within_corridor_z_band` | **CORRECTLY FAILS** — the bisection's own precondition (`assert probe(lo) is solid`) trips immediately: there is no boss top to find |
| `kw12_line_corridor_clearance` | Still passes — **expected, not a gap**: this test's job is to confirm the boss stays OUTSIDE the corridor; a missing boss is trivially also outside it, so this test was never meant to detect the boss's presence, only its encroachment |
| `kw12_switch_footprint_envelope_clear` | Still passes — **real gap**: this test only confirms 0 mm³ intersection between the switch envelope and the part; with less material (no boss at all), the intersection is still 0 mm³, so this test **cannot distinguish a present boss from a missing one** |
| `kw12_mass_delta_within_budget` | Still passes — **real gap**: this test calls `corner_mount._kw12_switch_boss()` directly, bypassing `make()` entirely, so it measures the boss's own standalone volume regardless of whether `make()` actually unions it into the returned part. It correctly probes a built solid (not a bare constant, so it doesn't fall in the Section-10-style "nominal arithmetic" failure class), but it is blind to an *integration* bug where the boss is computed correctly yet never attached to the part |

**Net**: 4 of 7 new tests would correctly catch a deleted/unattached boss;
1 of 7 was never meant to (by its own stated purpose); 2 of 7
(`kw12_switch_footprint_envelope_clear`, `kw12_mass_delta_within_budget`)
pass identically whether the boss is unioned into `make()` or not — a real,
if narrow, coverage gap. Recommend a lead/implementer follow-up: a single
cheap additional assertion (e.g., `assert cm.val().Volume() >
plate_wall_ears_only_volume` or a direct positive-volume boolean-
intersection check between the boss's own nominal footprint and the
built part) would close both gaps at once, since neither current test
would need to change, only supplement.

## 7. Printability (>45° overhang scan)

Scanned all planar faces of the **full built part** (not just the boss in
isolation, to catch anything a union with the plate might expose or hide)
for downward-facing normals: **exactly 1** such face found — the plate's
own bottom face at Z=0 (`normal=(0,0,-1)`, spanning the full X/Y footprint,
the print-bed contact plane itself, not an overhang). No new overhangs
introduced by the boss legs; their own internal "bottom" faces (visible
when `_kw12_switch_boss()` is scanned standalone: 2 downward faces, one per
leg, both flat 90°-from-horizontal) fuse away entirely into the plate's top
surface in the unified boolean solid and are not exposed print surfaces.
Confirms the "simple vertical prism, no overhangs" claim.

**PASS.**

## 8. STEP round-trip

Reimport solids = 1; bbox diff **0.000000 mm** (tol 0.1); volume diff
**0.000000 %** (tol 1%). **PASS**, unchanged from baseline methodology.

## Test run

```
python -m pytest tests/test_winch_geometry.py -k corner_mount -v
...
32 passed in 14.07s
```

```
python -m pytest tests/ -q
...
172 passed in 32.65s
```

(172 includes the concurrently-worked `tests/test_base_station_case.py`,
which this pass did not touch, read, or evaluate — out of scope per
instructions.)

## Homing-physics assessment (report only, not fixed)

**The question**: a bead on the line at Y=0, height ≈
`CORNER_MOUNT_AXIS_Z`, traveling in -X toward the spool during reel-in —
does the claimed lever geometry (pivot on the switch at the boss position,
roller reaching toward Y=0) put the roller IN the bead's path, with the
switch mounted at its nominal slot-center position?

**Geometric chain, as actually modeled in the code**:

1. **Bead path** — fixed at Y=0.000 (both spool axis and pulley axle land
   exactly there, confirmed above), Z = `CORNER_MOUNT_AXIS_Z` world
   (28.5 mm), traveling along X. This is solid — directly confirmed by the
   fleet-alignment measurements (Sections 0 and the original two sections
   above).
2. **Boss/switch mounting-face Z** — computed and confirmed: boss top at
   world Z=19.5, switch body sits on top of it (Z 19.5→29.5).
   `KW_LEVER_TARGET_Z` (a **Z-only** estimate: boss top + half the body
   height) lands at world Z=24.5, inside the corridor's own ±8 mm Z-band
   [20.5, 36.5] around the bead's Z=28.5, with margin on both sides. **This
   part is genuinely computed and verified geometrically**, and the
   docstring is explicit that it is a documented estimate (no datasheet
   gives the true internal pivot height), not a load-bearing precision
   claim.
3. **Switch/boss X-position** — `KW_TRIGGER_X`=10.0 (±5 mm adjustable),
   near the spool(-40)↔pulley(55) mid-span (7.5), independently confirmed
   on the built solid. This is also genuinely computed and reasonable: the
   roller should be encountered by the bead somewhere along its X travel,
   and mid-span is as good a nominal choice as any (the ±5 mm adjustability
   exists specifically to let this be tuned at assembly, per the
   docstring).
4. **The gap — lever Y-reach is never modeled, computed, or checked
   anywhere in this file or its tests.** `KW12_LEVER_LEN` = 18 mm (pivot-
   to-roller-center) is documented in the module docstring and stored as a
   constant, but it is **never used** in any coordinate calculation, any
   boolean check, or any test assertion in the entire diff. Nothing in the
   code computes "where is the roller, in Y, given this lever length and
   whatever this switch's pivot-within-body location actually is" and
   checks that against the corridor's Y ∈ [-3, +3] mm band the way the Z
   target is checked against the Z band.

   Working the numbers through by hand with the ASSUMPTION the docstring's
   language most directly suggests (pivot at the switch body's -Y,
   corridor-facing edge, at `KW_BODY_Y_FRONT` = 5.5 mm, lever pointing
   straight in -Y): roller Y ≈ 5.5 - 18 = **-12.5 mm** — 12.5 mm on the
   *far side* of the bead's line (Y=0), well outside even the generous
   ±3 mm corridor exclusion, and on the *opposite* side of Y=0 from the
   switch body itself. That would put the roller's straight-line rest
   position past the line entirely, not resting near it. If instead the
   pivot sits further into the body (say, mid-body around
   `KW_BODY_Y_FRONT + 9` ≈ 14.5, i.e., near the switch's own screw-hole
   centerline), a straight 18 mm reach in -Y lands the roller at
   14.5-18 = **-3.5 mm** — just outside the ±3 mm corridor, on the wrong
   side, by a small margin that would be sensitive to the exact (unstated)
   pivot location. Only a pivot noticeably closer to the body's far
   (+Y, non-corridor) end would put an 18 mm straight radial reach inside
   or near the [-3,+3] band on the correct (or any consistent) side.

   None of these three hand-worked cases is verifiable from the part file,
   because **the pivot's own (X,Y) location within the 20×6.4 mm body
   footprint is not specified anywhere** — only its estimated Z-offset
   above the mounting face is. Real KW12-3-style microswitches commonly
   have the lever **bent or curved** back toward the body rather than
   extending as a straight 18 mm radial arm (precisely so the roller sits
   close to, or just past, the body's own footprint rather than far out in
   space) — which would resolve the overshoot the straight-arm hand
   calculation above shows, but the module docstring never states this
   assumption, and no geometry or test in the diff encodes a bent-lever
   roller position either. As modeled, the switch is treated as a rigid
   mounting-footprint-plus-height problem; the lever is pure narrative
   text in the docstring, not geometry.
5. **Switch orientation assumed**: long axis along Y, lever "pointing -Y
   toward Y=0" — i.e., the switch is assumed pre-oriented so its lever
   generally faces the corridor. This is a reasonable choice of *which way
   to point the switch*, but it is a separate question from *whether an
   18 mm lever from this switch's actual (unstated) pivot location reaches
   the bead's Y=0 line* — the orientation choice does not by itself
   guarantee the reach does.

**Assessment**: the part's **mounting-face** geometry (X position, Z
height, adjustability range) is sound and independently confirmed on the
built solid. The **lever-reach** claim — that the roller actually ends up
at or near Y≈0 where the bead can strike it — is **not verifiable from
this geometry or its tests**, because the lever itself is not modeled as
geometry and its pivot's location within the switch body is never stated
or computed. This is not a proven defect (a bent/formed lever, which is
common on this switch family, could easily resolve it), but it is a real,
unclosed gap between the docstring's qualitative claim ("roller reaching
toward Y=0") and what the code actually establishes (a mounting Z/X
position only). Recommend one of: (a) a datasheet drawing or physical
sample confirming the pivot's (X,Y) location and lever bend/rest angle, so
the roller's true rest position can be computed and checked the same way
the Z target already is; or (b) an assembly-time adjustability note (the
existing ±5 mm X-slot travel already helps X, but there is currently no Y
adjustability at all if the roller turns out to land short of or past the
line) documented alongside the existing bead-placement procedure in the
docstring. This is a documentation/verification gap, not a geometry
change — no part file modification is recommended here.

## Findings requiring a decision

1. **Test-coverage gap (Section 6)** — 2 of 7 new tests
   (`kw12_switch_footprint_envelope_clear`, `kw12_mass_delta_within_budget`)
   pass identically whether the boss is actually unioned into `make()`'s
   output or not. Low severity (the boss demonstrably IS unioned in
   correctly today, per Sections 1-5 above), but the coverage gap itself is
   real. Recommend a bounded follow-up test.
2. **Homing-lever Y-reach is unmodeled (assessment, above)** — not a
   geometry defect in what's built, but a real gap between the docstring's
   narrative claim and what the code/tests can actually confirm. Recommend
   routing to the lead for a decision on whether a datasheet/physical
   confirmation of the KW12-3 pivot location is needed before this design
   is treated as functionally verified, not just geometrically clean.

Reproduce this section:
`python -m pytest tests/test_winch_geometry.py -k corner_mount -v` (32
passed) and `python -m pytest tests/ -q` (172 passed).
