# Base station case -- independent verification report

Scope: `cad/parts/base_station_case.py` (NEW two-piece part -- `make_tray()` /
`make_lid()` / `make() -> (tray, lid)`). Enclosure for an Arduino Uno R3 +
stacked CNC Shield V3 + 4x A4988, wall/shelf-mountable, printed PETG.

Verifier: geometry-verifier (Sonnet). Read-only against `cad/`; this report
and a new scratch verification script are the only outputs. All measurements
below were produced by independently building `bsc.make()` and probing the
actual BRep solids (OCCT `BRepClass3d_SolidClassifier` point-in-solid tests,
binary-search radius probes, exact `Face`/`Edge` boundary queries, mesh
triangle-normal overhang scanning, and boolean intersection/union probes) --
not by reading source and trusting comments or the module's docstring.
`tests/test_base_station_case.py` was read and audited (§11) but not
executed as the source of truth for any PASS/FAIL below; every row here was
re-derived independently.

**Out of scope / not touched**: `cad/parts/corner_mount.py` and
`tests/test_winch_geometry.py` are being edited concurrently by another
agent and were not read or verified in this pass.

## Summary

| # | Check | Verdict |
|---|---|---|
| 1 | Build validity, bbox, mass | **PASS** |
| 2 | Uno hole pattern (internal) | PASS (bores match built geometry) -- external sanity-check surfaced a **1.27 mm discrepancy** in the source data itself (see detail) |
| 3 | Boss height + board envelope fit | Boss height **PASS**; board envelope clearance-to-walls **PASS**; board-does-not-intersect-tray **FAIL** (corner posts collide with the board) |
| 4 | Stack clearance >= 45 mm, assembled | **PASS** (49.0 mm worst case over a 3x3 grid) |
| 5 | Lid/tray interface alignment + flush seating | **PASS** |
| 6 | Ports (openings, zip-ties, height math) | Openings/zip-ties/height-layering **PASS**; USB port **dimensions FAIL** (width/height swapped) |
| 7 | Vent slots | Presence **PASS**; area adequacy for ~2 W **marginal (INFO)** |
| 8 | External mounting (countersink direction, screwdriver access) | Screwdriver access **PASS**; countersink **FAIL -- no countersink is actually cut** |
| 9 | Printability / overhangs | Lid **PASS**; tray **PASS** once the (buggy, oversized) USB port ceiling is attributed to the row-6 finding, not a new defect |
| 10 | STEP round-trip | **PASS** |
| 11 | Test-file audit | 3 severe coverage gaps identified (see §11) |

**Overall: 3 reproducible geometry defects found**, none of which the part's
own test suite (172/172 passing at time of writing) catches:

1. **External mount holes have no countersink at all** (§8) -- a CadQuery
   workplane-recentering pitfall silently relocates the `cskHole()` cut
   ~18 mm away from the floor, into empty cavity air.
2. **USB port width and height are swapped** (§6) -- a coordinate-rotation
   bug in the `_x_axis_box()` helper.
3. **The 4 freestanding lid-screw corner posts sit inside the Uno board's own
   footprint** (§3) -- `CORNER_POST_INSET` was chosen clear of the wall ports
   and external mount holes, but not clear of the Uno board rectangle, so the
   posts (which run the full tray wall height) collide with the PCB.

Reproduce: `python3 -m pytest tests/test_base_station_case.py -v` (existing
suite, all green) and the independent probe script referenced inline below
(not checked into the repo; paths noted per finding).

---

## 1. Build validity, bounding box, mass

| Item | Expected | Measured | Tol | Status |
|---|---|---|---|---|
| tray: valid single solid | 1 valid solid | valid=True, 1 solid | -- | PASS |
| lid: valid single solid | 1 valid solid | valid=True, 1 solid | -- | PASS |
| tray bbox | 104.82 x 94.81 x 52.01 mm | 104.80 x 94.80 x 52.00 mm | 0.3 mm | PASS |
| lid bbox | 104.81 x 94.81 x 8.41 mm | 104.80 x 94.80 x 8.40 mm | 0.3 mm | PASS |
| tray mass @ PETG 1.27 g/cm^3 | 96.02 g | 96.02 g | 0.5 g | PASS |
| lid mass | 35.36 g | 35.36 g | 0.5 g | PASS |
| combined mass vs 150 g budget | <= 150.00 g (claimed 131.37 g) | 131.37 g | -- | PASS |

## 2. Uno R3 mounting-hole pattern

**Built-geometry self-consistency (PASS).** Probed the actual tray at all 4
`UNO_HOLE_XY` positions: insert bore (Ø`M3_THREAD_HOLE`=4.0 mm) is void at
mid-boss height, boss material is present just outside the bore. Bore
diameter measured by binary-search radius probe at all 4 holes: **4.00 mm**
vs. expected 4.00 mm (tol 0.05 mm) -- PASS at every hole.

**Independent source cross-check (network reachable via `raw.githubusercontent.com`;
`docs.arduino.cc`, `forum.arduino.cc`, `blog.adafruit.com`, `instructables.com`,
`sparkfun.com`, `componentsearchengine.com` are all `EGRESS_BLOCKED` from this
sandbox).** Fetched and grepped directly (not LLM-summarized) the raw KiCad
footprint at
`raw.githubusercontent.com/Alarm-Siren/arduino-kicad-library/master/footprints/arduino-library.pretty/Arduino_Uno_R3_Shield.kicad_mod`,
which reproduces the complete real Uno pin map (D0-D13, A0-A5, GND, AREF,
3V3, 5V, ICSP, all at correct 2.54 mm-pitch positions) -- a credible,
board-accurate source. Its 4 `np_thru_hole` mounting pads (Ø3.2 mm, matching
the module's own claimed diameter):

```
(13.97, -2.54)  (15.24, -50.8)  (66.04, -7.62)  (66.04, -35.56)
```

vs. the part's `UNO_HOLE_XY_BOARD`:

```
(15.24, 2.54)  (15.24, 50.80)  (66.04, 7.62)  (66.04, 35.56)
```

3 of 4 points match exactly. The hole nearest the USB/power-jack corner
differs by **1.27 mm in X** (15.24 vs 13.97 -- exactly 0.05 in, half the
0.1 in grid). A second independent source
(`raw.githubusercontent.com/KiCad/kicad-templates/master/Projects/Arduino_Uno_R3/Arduino_Uno.kicad_pcb`,
hand-authored mechanical mounting-hole footprints P5-P8) shows the same
irregular (non-rectangular) hole pattern rather than the idealized rectangle
the part assumes, though its absolute hole spacings differ from both other
sources by a similar order (~1 mm), suggesting it is a rougher project file.

**Verdict: PASS for internal build correctness** (the tray faithfully
reproduces its own documented coordinates); **the coordinates themselves
carry a flagged, unresolved 1.27 mm discrepancy at one hole** that the
module's docstring claim of "four independent...libraries, cross-checked"
did not catch -- worth a bench check against a physical Uno before trusting
the boss position at that one corner.

## 3. Boss height + Uno board envelope fit

| Item | Expected | Measured | Status |
|---|---|---|---|
| Boss height | 6.0 mm | 6.0 mm | PASS |
| Board-to-interior-wall clearance (all 4 sides) | > 0 mm | +X 15.70, -X 15.70, +Y 18.30, -Y 18.30 mm | PASS |
| Board envelope (68.6x53.4x1.6 @ boss-top Z) does not intersect tray material | intersection volume = 0 | **245.19 mm^3** | **FAIL** |

Built a 68.6 x 53.4 x 1.6 mm box (the documented Uno board envelope) seated
at `z = FLOOR_T + BOSS_H` (on top of the standoff bosses, matching the
module's own `UNO_TOP_Z` reference) and boolean-intersected it with the
built tray. **Non-zero intersection volume: 245.19 mm^3.**

Root cause: `CORNER_POST_XY = (±30, ±25)` (inset 20 mm from the interior
wall faces, chosen per the code comment to clear "wall port cutouts AND...
external mounting holes below"). The Uno board footprint spans x in
[-34.3, 34.3], y in [-26.7, 26.7] (`UNO_ORIGIN_X/Y ± UNO_L/W`). **All 4
corner posts (center within the board rectangle, ±4 mm post radius) sit
inside the board's footprint**, and each post is a **freestanding column
running the full `TRAY_WALL_H` = 49.6 mm** from the cavity floor to the rim
-- i.e. directly through the space the Uno PCB needs to occupy. The Uno
board cannot be seated on its bosses without either cutting notches in the
PCB or the posts physically blocking board placement.

Reproduce: `cq.Workplane` board box at
`(UNO_ORIGIN_X+UNO_L/2, UNO_ORIGIN_Y+UNO_W/2, FLOOR_T+BOSS_H)`,
`.intersect(tray)`, `.val().Volume()`.

## 4. Stack clearance >= 45 mm, assembled

Independent probe (not the part's own `test_interior_clearance_above_pcb_meets_minimum`,
which only samples the single center point (0,0)): assembled `tray.union(lid
translated to FLOOR_T+TRAY_WALL_H)`, then swept an empty-column probe from
`z0 = FLOOR_T + UNO_TOP_Z` upward at a 3x3 grid spanning the board footprint
(10%/50%/90% of `UNO_L` x `UNO_W`).

| Item | Expected | Measured | Status |
|---|---|---|---|
| Worst-case clearance over 3x3 grid | >= 45.0 mm | **49.00 mm** | PASS |
| Center-column clearance (0,0), 0.5 mm step | >= 45.0 mm (claimed 48.0) | 48.50 mm | PASS |

No blocked points found before 45 mm anywhere in the sampled grid (all 9
points clear to the full 49 mm design headroom). This check is genuinely
independent of the part's own test and confirms the claim.

## 5. Lid/tray interface -- alignment + flush seating

| Item | Expected | Measured | Status |
|---|---|---|---|
| 4x corner post: tray bore void, boss material present, lid clearance hole void | all True | all True (4/4 posts) | PASS |
| Tray/lid boolean intersection at assembly offset | 0 mm^3 | 0.0 mm^3 | PASS |
| Tray rim top Z == lid bottom Z (coincident mating plane) | gap = 0 mm | gap = 0.000000 mm (52.000 == 52.000) | PASS |

No interference between the lid and the tray rim/posts at the assembled
height; the mating plane is exactly coincident (no gap, no overlap).

## 6. Ports

All openings probed as real 5-point through-wall voids (not single-point
presence checks):

| Port | Expected | Status |
|---|---|---|
| USB (-X wall) | void through wall thickness | PASS (opening exists) |
| DC (-X wall) | void through wall thickness | PASS |
| Motor x4, endstop x1 (+X wall) | void through wall thickness | PASS (5/5) |
| Zip-tie holes, all 14 (2 per port x 7 ports) | void at computed flanking position | PASS (14/14) |
| USB port centers within Uno layer (`uno_top`..`shield_top` = 7.60-17.70) | PASS | PASS |
| Motor/terminal/endstop ports center within shield layer (17.70-39.70) | PASS | PASS |
| Documented stack math `SHIELD_TOP_Z = UNO_TOP_Z + 8.5 + 1.6` | 17.70 mm | 17.70 mm, PASS |

**USB port dimensions -- FAIL.** Queried the exact BREP face bounding the
port's top ceiling (4 straight edges, `PLANE` geomType): the built opening
spans **Y = 14.0 mm** (span [-21, -7]) x **Z = 20.0 mm** (span [2.6, 22.6]),
the reverse of the documented `USB_SLOT_W` (Y) = 20 mm x `USB_SLOT_H` (Z) =
14 mm.

Root cause: `_x_axis_box(width_y, height_z, length_x, x0, y, z)` builds
`.rect(width_y, height_z).extrude(length_x)` then
`.rotate((0,0,0),(0,1,0),90)` (90° about the Y axis). That rotation swaps
the local X and Z axes, so `width_y` (meant, per the function's own
docstring, to become the port's Y-width) and the pre-rotation extrusion
length end up on the wrong final axes. Verified this is the *only* call site
of `_x_axis_box` in the file -- the DC/motor/endstop ports use
`_x_axis_cylinder` (round, immune to an axis swap by symmetry), and the tray
vent slots use the separately-implemented `_y_axis_box`, independently
checked and confirmed **not** to have this swap (its Y/Z/X mapping works out
correctly under a 90° X-axis rotation; row-7 vent presence checks all pass
at the documented small dimensions).

Consequences:
- The built port (14 x 20 mm) is still large enough for a THT USB-B
  connector (~12 x 11.5 mm) in both axes, so it is likely still functional,
  but it does not match the documented shape or the module's stated
  reasoning.
- The flanking zip-tie holes are positioned using the *nominal*
  `USB_SLOT_W`=20 (not the actual 14 mm built width), landing 3 mm farther
  from the real port edge on each side than intended -- harmless but
  internally inconsistent.
- The port's actual Z-bottom is 2.6 mm, only **0.2 mm above `FLOOR_T`
  (2.4 mm)** -- a sub-perimeter-width sliver of wall material between the
  port and the interior floor that is unlikely to print as a distinct
  feature.

Reproduce: `tray.val().Faces()`, filter `geomType()=="PLANE"` with center
near `(-51.2, USB_PORT_Y, 22.6)`, inspect `.Edges()` bounding box.

## 7. Ventilation slots

| Item | Expected | Measured | Status |
|---|---|---|---|
| Tray side-wall vents (±Y), 24 slot centers | all void | 24/24 void | PASS |
| Lid roof vents, 24 slot centers | all void | 24/24 void | PASS |
| Nominal total open area | -- | ~1056 mm^2 across 48 slots (2.2x10 mm each) | INFO |

No hard numeric adequacy spec was given. For reference, sealed low-voltage
enclosures relying on passive-only natural convection through small slots
are commonly kept well above ~1000-2000 mm^2 effective free area per watt as
a rule of thumb (not a code requirement), and narrow 2.2 mm slots throttle
real airflow well below their raw geometric area (discharge-coefficient
losses). ~1056 mm^2 for an estimated ~2 W (4x A4988 without/with modest
heatsinking) is on the thin side of that heuristic. Not a hard FAIL, but
flagged for a bench thermal-soak test before relying on passive cooling
alone, especially near the top of expected driver current.

## 8. External mounting holes -- countersink direction + screwdriver access

**Screwdriver access -- PASS.** Probed a 30 mm empty vertical column above
each of the 4 mount holes (tray only, Uno bosses in place, per the module's
own stated "screwdriver access before the lid goes on"): all 4 clear.

**Countersink -- FAIL, no countersink is present in the built solid.**
Binary-search bore-radius probes at all 4 mount holes, at 3 Z levels
spanning the 2.4 mm floor thickness (near-exterior, mid, near-interior):

```
hole0 (37.4, 32.4):   r = 2.25, 2.25, 2.25 mm
hole1 (37.4,-32.4):   r = 2.25, 2.25, 2.25 mm
hole2 (-37.4, 32.4):  r = 2.25, 2.25, 2.25 mm
hole3 (-37.4,-32.4):  r = 2.25, 2.25, 2.25 mm
```

Expected: radius should widen from the shank (`MOUNT_HOLE_SHANK_DIA`/2 =
2.25 mm) to the countersink (`MOUNT_HOLE_CSK_DIA`/2 = 3.75 mm) somewhere
within the 2.4 mm floor thickness. **Measured: constant 2.25 mm at all 4
holes, all 3 Z levels -- no widening anywhere in the solid material.**

**Root cause** (`cadquery/cq.py Workplane.workplane()`, lines ~561-618): the
code does
```python
tray = tray.workplane(offset=FLOOR_T).pushPoints(MOUNT_HOLE_XY).cskHole(...)
```
directly on the cut tray Compound, with no prior `.faces()` selection. CQ's
default `centerOption="ProjectedOrigin"` then computes the new workplane's Z
from **the current solid's mass-centroid Z** (`Shape.Center()`), not from
Z=0 as the code's own comment claims ("Cut via a workplane offset from the
part's own base XY plane (Z=0)..."). Verified directly by reproducing the
exact tray construction up to that point and reading `.plane.origin`:

```
tray_precut.workplane(offset=FLOOR_T).plane.origin.z == 20.59 mm
(== tray-solid mass-centroid Z 18.19 + FLOOR_T 2.4)
```

not the intended 2.4 mm. `cskHole()`'s countersink cone (base radius
`cskDiameter/2`, tapering to a point over height `h = r/tan(cskAngle/2)` =
3.75 mm along `-Z` from the workplane) is therefore cut starting at global
Z≈20.6 mm, entirely inside the hollow interior cavity air (well above the
2.4 mm floor, and clear of any boss/post at those XY), where it removes
nothing. Only the separately-unioned, full-depth **shank** cylinder (radius
2.25 mm, independent of workplane Z since its "depth" spans the whole part)
actually reaches down through the real floor material, producing a plain
Ø4.5 mm clearance hole with **no countersink chamfer at either face**.

Consequence: a flat-head/countersunk screw will not sit flush at either the
interior or exterior floor face. The task's specific question ("countersink
opens DOWNWARD... check cone direction carefully") cannot be answered
because no countersink geometry exists in the built part at all -- this
supersedes any direction question.

Note: since the cone is cut in empty air, it removes zero material, so the
row-1 claimed tray mass (96.02 g) is consistent with the as-built
(uncountersunk) part; a corrected countersink would remove a small
additional volume (a few hundred mm^3 total across 4 holes), within the
stated 0.5 g mass tolerance but explaining why the mass claim doesn't
already reveal the defect.

Reproduce: `tray.workplane(offset=bsc.FLOOR_T).plane.origin` on the tray
Compound immediately before the `cskHole()` call; or binary-search bore
radius vs Z at any `MOUNT_HOLE_XY` position.

## 9. Printability (overhang scan)

Print orientations per the module docstring: **tray** as-modeled (floor
down, opening up, no flip); **lid** flipped 180° from its CAD/assembly
orientation (roof face down on the bed, recessed cavity up).

Tessellated both solids (`solid.tessellate(0.15, 0.3)`), computed per-
triangle normals, flagged triangles whose downward-facing normal exceeds
45° from vertical (`n_z < -cos(45°)`), excluded the bed-contact plane
itself (not an overhang by definition) and triangles within a generous
radius of every documented port/vent/countersink/insert-bore/corner-post
feature center (horizontal port/vent bridges are explicitly acceptable per
the assignment).

| Part | Unexplained downward area | Status |
|---|---|---|
| Lid (roof-down) | 0.00 mm^2 (0 triangles) | PASS |
| Tray | 33.60 mm^2 (2 triangles), centroid ≈(-51.6,-14,22.6) | initially flagged; **fully attributable to the §6 USB-port axis-swap bug**, not a separate defect |

The tray's flagged area is exactly the (buggy, oversized-in-Z) USB port's
own ceiling -- a horizontal bridge spanning the port's actual 14 mm Y-width,
well inside the assignment's own carve-out for port/vent bridges. No
genuine unexplained overhang exists in either part. Vertical edge fillets
(`CORNER_R`, `|Z` edges) contribute no downward-facing area by construction
(constant-radius fillet around a vertical axis has a horizontal-only
normal). The 90°-included-angle countersink cones (where geometrically
intended, see §8) are a standard self-supporting FDM feature and were
excluded from consideration.

## 10. STEP round-trip

| Part | Metric | Original | Reimported | Diff | Status |
|---|---|---|---|---|---|
| tray | bbox | 104.80x94.80x52.00 | +0.03mm max axis diff | 0.03 mm | PASS (tol 0.1mm, matches repo `BBOX_TOL` convention) |
| tray | volume | 75603.21 mm^3 | 75603.21 mm^3 | 0.0000 mm^3 (0.00000%) | PASS |
| lid | bbox | 104.80x94.80x8.40 | +0.03mm max axis diff | 0.03 mm | PASS |
| lid | volume | 27840.39 mm^3 | 27840.39 mm^3 | 0.0000 mm^3 (0.00000%) | PASS |

Both pieces export to STEP, reimport as a single valid solid each, and agree
on volume to 5 decimal places; bbox differences are within normal
STEP-tessellation precision (well under the repo's own 0.3 mm `BBOX_TOL`
convention used elsewhere).

## 11. Audit of `tests/test_base_station_case.py`

242 lines, 17 test functions (some parametrized), all currently passing.
Overall the suite is well-built where it goes -- it uses exact BRep point
classification rather than mesh sampling, matching this project's
convention. Its main structural weakness, and the reason it missed 2 of the
3 defects above, is a systematic pattern:

**Pattern: presence-only assertions, not dimension assertions.** Nearly
every geometric test asks "is there a void/solid at this one constant-
derived coordinate?" and almost none ask "is the feature the *documented
size/shape*?" Specifically:

- `test_usb_and_dc_ports_open` / `test_output_wall_ports_open` probe a
  **single point** per port (`inside_tray(x_in, bsc.USB_PORT_Y,
  bsc.USB_PORT_CTR_Z)`), which is satisfied by a port of *any* size as long
  as it's open at the exact center -- this is precisely how the §6 USB
  width/height swap slipped through: the center point is void either way.
- `test_external_mount_holes_open` probes a **single point at the floor
  mid-thickness**, checking only that a hole of *some* diameter exists --
  it never measures the countersink cone at all, which is exactly how the
  §8 missing-countersink defect slipped through.
- No test measures the Uno boss bore diameter, the corner-post bore
  diameter, or any hole diameter anywhere in the file (`M3_THREAD_HOLE`
  is asserted only by "is the bore void", never by a radius measurement) --
  a hole cut 2x too large or too small at the right center point would
  pass every existing test.

**Coverage gaps vs. this assignment's checklist (items with zero test
coverage in the file):**

1. **Board envelope fit / wall clearance** (§3): no test builds or probes
   the Uno board envelope against the tray at all. This is the single
   biggest gap -- it's how the corner-post/board collision (§3, 245 mm^3
   interference) went completely undetected.
2. **Zip-tie holes**: never probed anywhere in the file, despite 14 of them
   existing in the design.
3. **Countersink geometry / direction**: `MOUNT_HOLE_CSK_DIA` and
   `MOUNT_HOLE_CSK_ANGLE` are never referenced by any test.
4. **Screwdriver access column**: not tested.
5. **Printability / overhangs**: not tested (reasonable to leave to a
   geometry-verifier pass, but worth naming explicitly since this part has
   two different print orientations for its two pieces).
6. **STEP export + reimport**: not tested anywhere in this file (other repo
   parts do have STEP round-trip tests elsewhere; this one doesn't).
7. **Vent area adequacy**: appropriately left as a qualitative judgment
   (correctly not asserted as a hard number).

**Constants-only assertions (no BRep probe at all):**

- `test_uno_hole_spacing_matches_researched_pattern`'s final two lines
  (`assert bsc.UNO_L == pytest.approx(68.6)`, `assert bsc.UNO_W ==
  pytest.approx(53.4)`) compare the module's own constant to a literal,
  never touching the built solid.
- The same test's main body compares `UNO_HOLE_XY` against
  `UNO_HOLE_XY_BOARD + UNO_ORIGIN` -- both are the module's own constants;
  this checks the module is internally self-consistent, not that either
  value is *correct* (see §2's external-source discrepancy, which no test
  in this file could ever catch by construction).
- Every `expected` bbox/Z value in the bbox and clearance tests
  (`bsc.OUTER_L`, `bsc.FLOOR_T + bsc.TRAY_WALL_H`, etc.) is pulled from the
  same module rather than a hardcoded reference number. This is a
  defensible pattern for catching *regressions*, but it structurally cannot
  catch a bug where the *construction code* itself misinterprets a correct
  constant (exactly what happened in both the §6 and §8 defects: the
  input constants are fine, the CadQuery operations misapply them).

No recommendation to repair the test file is made here per this
assignment's scope (audit only, no repair); the gaps above are handed back
as findings for the implementing agent.

---

## Reproduction notes

All probes were run against `bsc.make()` freshly built in-process (no
caching), using:
- `OCP.BRepClass3d.BRepClass3d_SolidClassifier` for point-in-solid tests
  (tol 1e-6 to 1e-7, care taken to offset probe points off exact face
  boundaries to avoid `TopAbs_ON` misclassification -- an early version of
  this script hit exactly that pitfall at `z=0.0` and was corrected).
- Binary-search radius probes (40-60 bisection iterations, ~1e-9 mm
  convergence) for hole/boss/countersink diameter measurement.
- `cq.Workplane.intersect()` / `.union()` for boolean interference and
  flush-seating checks.
- `solid.tessellate(0.15, 0.3)` + per-triangle cross-product normals for
  the overhang scan.
- `cq.exporters.export()` / `cq.importers.importStep()` for the STEP
  round-trip.

Full pytest suite (run from repo root, `python3 -m pytest -q`): **172
passed**, 0 failed, at time of writing. (Count includes tests from
`tests/test_winch_geometry.py` / `corner_mount`-related files that another
agent is concurrently editing in this pass -- not this report's scope,
included only because the assignment asked for the full-suite count.)

---

# Re-verification (post-repair)

Focused delta re-verification of the implementer's repair pass, against the
7 claimed fixes. Same rules as the original pass: read-only against `cad/`;
every measurement below was produced with a **freshly-written, independent**
probe/bisection/boolean script (not by running or trusting
`tests/test_base_station_case.py`, though its own methodology was spot-
audited separately per item 7). `cad/parts/corner_mount.py` and
`tests/test_winch_geometry.py` remain untouched and out of scope.

## Summary

| # | Original defect | Claimed fix | Independently re-verified | Verdict |
|---|---|---|---|---|
| 1 | No countersink cut (workplane recentered on solid mass-centroid) | `faces("<Z").workplane()` | Countersink cone confirmed opening on the **outside** (bottom) face at all 4 holes; shank-only at inside face | **RESOLVED** |
| 2 | USB port width/height swapped | `_x_axis_box` fixed (rect(height_z, width_y)) | Measured via independent BREP face query: Y=20.0mm, Z=14.0mm, bottom z=5.6mm -- matches exactly | **RESOLVED** |
| 3 | Corner posts collide with Uno board (245.19 mm^3) | Posts relocated outboard, (±41.3,±33.7) | Board-envelope boolean intersection: **0.0 mm^3**; moved mount holes still open/accessible; countersink discs not fillet-clipped; lid holes align | **RESOLVED** |
| 4 | Uno hole 1 at wrong X (15.24 vs 13.97) | Corrected to (13.97, 2.54) | Measured actual built boss center via own edge-bisection: (13.970, 2.540); all 6 pairwise distances match an independently-typed canonical reference to <0.0001mm | **RESOLVED** |
| 5 | (new, found during hardening) Zip-tie/port merge at old 14mm pitch | Re-pitched 14→17mm, ZIP_TIE_OFFSET 4→2 | Port diameters all correct (5/5); all 14 zip-tie holes present; **but the endstop port's zip-tie holes overlap BOTH neighboring motor ports' zip-tie holes** -- probed midpoint between the two hole centers is void (merged, 0mm wall) at both the port1/port2 and port2/port3 boundaries | **NOT FULLY RESOLVED at this pass -- see "Attempt-2 confirmation" section below: RESOLVED by moving zip-ties to Z-flanking, measured 1.75mm wall everywhere** |
| 6 | Interior width 90→94, mass recompute | 135.16 g combined | Re-measured: 98.38g (tray) + 36.78g (lid) = **135.16g**, exact match; stack clearance 49.0mm (≥45 required); lid seats flush (0 interference, 0 gap); STEP round-trip both pieces exact (0.0000mm bbox diff, 0.00000% volume diff) | **RESOLVED** |
| 7 | (audit) rewritten tests genuinely measure? | claimed yes | Confirmed: `_measure_rect_port()` and `_bisect_wall()` are genuine BREP face/bisection measurements (not single-point presence); `test_uno_board_envelope_does_not_intersect_tray` is a genuine boolean check; `CANONICAL_UNO_HOLES_BOARD_MM` is a literal typed directly in the test file, independent of `bsc` constants | **CONFIRMED** |

**Net: 5 of the 6 geometry defects are resolved. One new defect surfaced by
the implementer's own hardening pass (item 5, the re-pitched output-port
zip-tie holes) is only partially fixed** -- it fixed the port-to-port and
port-to-own-zip-tie overlaps that motivated the re-pitch, but introduced (or
left unaddressed) a zip-tie-hole-to-adjacent-port's-zip-tie-hole overlap
specifically at the two motor/endstop boundaries.

## Item 1: Countersink direction (RESOLVED)

Bisection-probed bore radius at all 4 `MOUNT_HOLE_XY` positions, at Z just
inside the outside face (0.05mm) and just inside the inside face
(`FLOOR_T`-0.05mm):

```
hole0 (46.4, 43.4):   r_outside=3.700mm  r_inside=2.250mm
hole1 (46.4,-43.4):   r_outside=3.700mm  r_inside=2.250mm
hole2 (-46.4, 43.4):  r_outside=3.700mm  r_inside=2.250mm
hole3 (-46.4,-43.4):  r_outside=3.700mm  r_inside=2.250mm
```

`r_outside` (3.70mm) is approaching the full countersink radius (3.75mm,
right at the cone's near-surface taper) and clearly beyond the shank radius
(2.25mm); `r_inside` is exactly the shank radius. The cone now opens on the
**outside (exterior, wall-facing) floor face**, matching both the task
brief's requirement ("opens DOWNWARD... so the case sits flush on screws")
and the `faces("<Z")` fix. Confirmed at all 4 holes -- **RESOLVED**.

## Item 2: USB port dimensions (RESOLVED)

Independent BREP face query (own re-implementation of the same
ceiling/floor-face-finding method used in the original report's §6 finding,
not the test file's `_measure_rect_port`):

```
faces found=2, Y-span=20.0mm, Z-span=14.0mm, z_lo=5.600mm, z_hi=19.600mm
```

Matches the documented `USB_SLOT_W`=20, `USB_SLOT_H`=14, and bottom
`USB_PORT_CTR_Z - USB_SLOT_H/2` = 5.6mm exactly. The `_x_axis_box` axis-swap
bug is fixed. Flanking zip-tie holes recomputed for the corrected width
(`USB_PORT_Y ± (USB_SLOT_W/2 + ZIP_TIE_OFFSET)` = -26.0, -2.0) both probed
void -- **RESOLVED**.

## Item 3: Corner posts + moved mount holes (RESOLVED)

Rebuilt the Uno board envelope box independently and boolean-intersected it
with the built tray: **0.0000 mm^3** (was 245.19 mm^3). `CORNER_POST_XY` is
now `(±41.3, ±33.7)`, matching the claim, and is derived from
`UNO_L/2 + BOARD_POST_CLEARANCE + CORNER_POST_OD/2` (outboard of the board
footprint) rather than an inset from the interior walls.

Additional checks per the coordinator's request:
- All 4 moved `MOUNT_HOLE_XY` (inset 6mm from the outer edge) are open, and
  a 30mm screwdriver-access column above each (with Uno bosses/corner posts
  in place) is clear -- **PASS**.
- Countersink discs (full csk radius 3.75mm, sampled at 12 angles around
  each hole) are void at every angle at the outside face -- not clipped by
  the `CORNER_R`=6mm corner fillet at the new, tighter 6mm inset -- **PASS**.
- Lid through-holes (`CORNER_POST_XY`) align with the moved posts, void at
  all 4 -- **PASS**.

## Item 4: Uno hole 1 correction (RESOLVED)

Measured the actual built boss centers on the tray via independent edge-
bisection (own implementation, not the test file's `edge()` helper), using
an independently-typed canonical reference (not read from any `bsc`
constant):

```
measured hole0 board-relative: (13.970, 2.540)  -- canonical: (13.97, 2.54)
```

All 6 pairwise inter-hole distances match the canonical reference to better
than 0.0001mm:

```
(0,1): canonical=48.277  measured=48.277
(0,2): canonical=52.317  measured=52.317
(0,3): canonical=61.657  measured=61.657
(1,2): canonical=66.672  measured=66.672
(1,3): canonical=53.037  measured=53.037
(2,3): canonical=27.940  measured=27.940
```

**RESOLVED.**

## Item 5: Output-port re-pitch (NOT FULLY RESOLVED)

Port diameters are all correct (measured via bisection, capped short of
each port's own zip-tie hole):

```
port0(motor)@y=-34: r=5.000  port1(motor)@y=-17: r=5.000
port2(endstop)@y=0: r=7.000  port3(motor)@y=17: r=5.000  port4(motor)@y=34: r=5.000
```

All 14 zip-tie holes are individually present (void at their nominal
centers). However, a fine Y-profile scan across the +X wall at
`TERMINAL_PORT_CTR_Z` found two void runs (~3.75mm wide, at y≈[-11.25,-7.5]
and y≈[7.75,11.5]) that are wider than a single 2.5mm-diameter zip-tie
hole should be. Direct analysis and probing confirmed why:

- Port1 (motor, y=-17) right zip-tie hole center =
  `-17 + (MOTOR_PORT_D/2 + ZIP_TIE_OFFSET)` = **-10.0mm**
- Port2 (endstop, y=0) left zip-tie hole center =
  `0 - (ENDSTOP_PORT_D/2 + ZIP_TIE_OFFSET)` = **-9.0mm**
- Center-to-center distance = **1.0mm**, but each hole has radius
  `ZIP_TIE_HOLE_D/2` = 1.25mm, so they need >= 2.5mm separation to stay
  apart. **They overlap by 1.5mm.**
- Probed the exact midpoint (y=-9.5, z=`TERMINAL_PORT_CTR_Z`): **void, not
  solid** -- the two holes have merged into one continuous opening with
  zero wall between them. The mirror-image boundary (port2's right zip-tie
  at y=9.0 vs port3's left zip-tie at y=10.0) shows the identical 1.0mm
  center-to-center gap and was also confirmed void at its midpoint.
- By contrast, the motor-motor boundaries (port0/port1, port3/port4) were
  checked the same way and are fine: zip-tie centers 3.0mm apart, midpoint
  confirmed **solid** (0.5mm wall remains -- thin, but present).

**Root cause**: the module's own fail-fast assertion (lines 261-268,
computing `_gap` from `OUTPUT_PORT_Y ± radii ± ZIP_TIE_OFFSET`) only checks
that a zip-tie hole's *center* clears the *neighboring port's body edge* --
it never adds back each zip-tie hole's own `ZIP_TIE_HOLE_D/2` radius on
both sides, and so never catches two *adjacent ports'* zip-tie holes
overlapping each other. This specifically bites the two motor/endstop
boundaries because the endstop port is 4mm wider in diameter than a motor
port, pushing its zip-tie ring further out than a uniform pitch sized only
for "port radius + port radius + margin" accounts for.

**Verdict: NOT FULLY RESOLVED.** The originally-reported defect (a port's
zip-tie hole reaching into the *next port's own opening*) is fixed. A
narrower but real variant of the same class of bug (adjacent *zip-tie holes*
merging with each other) remains at both motor/endstop boundaries.

## Item 6: Bbox/mass/clearance/seating/STEP (RESOLVED)

| Metric | Claimed | Measured | Status |
|---|---|---|---|
| Tray bbox | -- | 104.80 x 98.80 x 52.00 mm | -- |
| Lid bbox | -- | 104.80 x 98.80 x 8.40 mm | -- |
| Tray mass | -- | 98.38 g | -- |
| Lid mass | -- | 36.78 g | -- |
| Combined mass | 135.16 g | **135.16 g** | PASS |
| Stack clearance (3x3 grid, assembled) | >= 45.0 mm | 49.00 mm worst-case | PASS |
| Lid flush seating | 0 interference, 0 gap | 0.0000 mm^3, 0.000000 mm gap | PASS |
| Tray STEP round-trip | bbox/vol agreement | 0.0000mm bbox diff, 0.00000% vol diff | PASS |
| Lid STEP round-trip | bbox/vol agreement | 0.0000mm bbox diff, 0.00000% vol diff | PASS |

The interior width growth (90→94mm) and all downstream geometry (mass,
clearance, seating) re-verify cleanly with fresh independent probes/booleans
-- **RESOLVED**.

## Item 7: Spot-audit of rewritten/new tests (CONFIRMED)

- `_measure_rect_port()` (test file lines 78-96): iterates `solid.Faces()`,
  filters `geomType()=="PLANE"` near the wall, selects the flat
  Y-spanning/Z-flat ceiling faces, returns the real face `BoundingBox()`
  span. **Genuine BREP face measurement**, not a presence check --
  independently reproduced with the same result in item 2 above.
- `_bisect_wall()` (lines 54-75): genuine 50-iteration binary search from a
  void seed to the void→solid transition, with pre-asserted void/solid
  bounds. **Genuine measurement** -- independently reproduced with matching
  results in items 1 and 5.
- `test_uno_board_envelope_does_not_intersect_tray` (lines 319-328): builds
  its own board box and calls `.intersect()`, sums solid volumes. **Genuine
  boolean check** -- matches this report's item 3 result exactly (0.0 mm^3).
- `test_uno_hole_pairwise_distances_match_canonical_pattern` /
  `CANONICAL_UNO_HOLES_BOARD_MM` (lines 184-257): the canonical reference
  is a **literal tuple typed directly in the test file**, not read from
  `bsc.UNO_HOLE_XY_BOARD` or any other `bsc` constant. The comparison side
  is measured by bisecting the actual built solid (seeded from, but not
  trusting, the canonical coordinates). This test would fail if the module
  ever reverted to the old 15.24mm value while the test file weren't also
  reverted -- it is a genuine regression guard, not a tautology.

All 4 sub-claims **CONFIRMED** by direct source reading and independent
reproduction.

## Full pytest suite (post-repair)

`python3 -m pytest -q` from repo root: **179 passed**, 0 failed.
`python3 -m pytest tests/test_base_station_case.py -q`: **31 passed**, 0
failed (up from 17 test functions/parametrizations in the original file,
reflecting the new/hardened tests for items 1-4 above). The overall
repo-wide count continues to grow between runs because another agent is
concurrently adding tests to `tests/test_winch_geometry.py` /
`corner_mount`-related files in parallel with this pass -- not this
report's scope.

## Outstanding action (as of the post-repair pass above)

~~Item 5 needs a further, targeted fix~~ -- **superseded, see "Attempt-2
confirmation" below: item 5 is now resolved.**

---

# Attempt-2 confirmation (item 5 resolved)

Final confirmation pass on the implementer's attempt-2 repair, which moved
the +X wall's zip-tie holes from Y-flanking (beside each port, competing
with neighboring ports' own zip ties for the same Y-band -- the root cause
of the item-5 defect above) to **Z-flanking** (above/below each port,
sharing that port's own Y-center exactly, using the ~50 mm of spare interior
wall height instead), and raised `ZIP_TIE_OFFSET` on both walls from 2.0 to
3.0 mm. `OUTPUT_PORT_PITCH` itself is unchanged (17.0 mm). Narrow scope,
independent probes only (fresh bisection/scan code, not
`tests/test_base_station_case.py`); `corner_mount.py` /
`tests/test_winch_geometry.py` untouched.

## 1. +X wall (output ports): void/solid scan

**Port-to-port** (Y-profile scan at `TERMINAL_PORT_CTR_Z`, 0.1 mm step,
confirmed with fine bisection at each transition): exactly **5** distinct
void runs (the zip ties no longer appear in this Y/Z plane at all, since
they're now Z-flanking). Solid gap measured between every adjacent pair:

```
port0/port1 (motor/motor):    7.000 mm
port1/port2 (motor/endstop):  5.000 mm
port2/port3 (endstop/motor):  5.000 mm
port3/port4 (motor/motor):    7.000 mm
```

All comfortably above the 1.5 mm minimum -- **PASS**.

**Port-to-own-zip-tie** (Z-direction bisection at each port's exact Y-center,
both above and below):

```
port0 (motor, y=-34):    gap_above=1.750mm  gap_below=1.750mm
port1 (motor, y=-17):    gap_above=1.750mm  gap_below=1.750mm
port2 (endstop, y=0):    gap_above=1.750mm  gap_below=1.750mm
port3 (motor, y=17):     gap_above=1.750mm  gap_below=1.750mm
port4 (motor, y=34):     gap_above=1.750mm  gap_below=1.750mm
```

**Measured minimum: 1.750 mm, matching the claimed 1.75-1.80 mm exactly**,
identical for every port regardless of diameter (motor or endstop) --
expected, since a port's own zip-tie gap is `ZIP_TIE_OFFSET -
ZIP_TIE_HOLE_D/2` = 3.0 - 1.25 = 1.75 mm, independent of the port's own
radius once the hole is Z-flanking (no longer competing with a neighbor).
**PASS.**

## 2. -X wall (USB/DC): void/solid scan

Same port-to-own-zip-tie measurement, Y-direction bisection (unchanged
flanking style on this wall, only `ZIP_TIE_OFFSET` changed):

```
USB port, both sides:  1.7500 mm, 1.7500 mm
DC port, both sides:   1.7500 mm, 1.7500 mm
```

**Confirmed raised from the previous 0.75 mm to 1.75 mm**, matching the
claim exactly (min measured 1.750 mm >= 1.5 mm minimum). USB's and DC's own
zip-tie holes sit 7.00 mm apart in Y and additionally occupy different Z
bands (`USB_PORT_CTR_Z`=12.6 mm vs `TERMINAL_PORT_CTR_Z`=27.7 mm), so they
cannot interact regardless. **PASS.**

## 3. Diameters, bbox/mass, STEP round-trip

| Check | Expected | Measured | Status |
|---|---|---|---|
| 5x output port diameters | motor r=5.0, endstop r=7.0 | port0-4: 5.000, 5.000, 7.000, 5.000, 5.000 mm | PASS |
| USB port dims | Y=20.0, Z=14.0 mm | Y=20.0, Z=14.0 mm | PASS |
| DC port diameter | r=5.0 mm | 5.000 mm | PASS |
| All 14 zip-tie holes open | all void | 14/14 void | PASS |
| Tray bbox | unchanged, 104.8x98.8x52.0 | 104.80x98.80x52.00 mm | PASS |
| Lid bbox | unchanged, 104.8x98.8x8.4 | 104.80x98.80x8.40 mm | PASS |
| Combined mass | 135.15 g | 98.36g (tray) + 36.78g (lid) = **135.15 g** | PASS |
| Tray STEP round-trip | valid, bbox/vol agreement | valid, 1 solid, 0.0000mm bbox diff, 0.00000% vol diff | PASS |
| Lid STEP round-trip | valid, bbox/vol agreement | valid, 1 solid, 0.0000mm bbox diff, 0.00000% vol diff | PASS |

Exact match to the claimed combined mass (135.15 g) and unchanged bbox.
**All PASS.**

## Item 5: RESOLVED

The Z-flanking relocation eliminates the adjacent-port zip-tie collision by
construction: each port's zip-tie holes now share that port's own Y-center
exactly, so their Y-footprint is always a strict subset of their own port's
footprint and can never reach a neighboring port's zip ties in Y regardless
of pitch. Measured wall minimums (1.750 mm on both walls, all ports) confirm
this independently, with no merged voids anywhere on either wall.

## Full pytest suite (attempt-2)

`python3 -m pytest -q` from repo root: **185 passed**, 0 failed.
`python3 -m pytest tests/test_base_station_case.py -q`: **37 passed**, 0
failed. (Counts continue to grow run-over-run because another agent is
concurrently adding tests to `tests/test_winch_geometry.py` /
`corner_mount`-related files in parallel -- not this report's scope.)

## FINAL VERDICT: base_station_case.py -- PASS

All defects found across both verification passes are now resolved:
countersink direction (§8 / item 1), USB port width/height (§6 / item 2),
corner-post/board collision (§3 / item 3), Uno hole-pattern correction
(§2 / item 4), and the output-port zip-tie merge (item 5, this section).
Stack clearance, lid flush seating, bounding boxes, combined mass (135.15 g,
well under the 150 g budget), and STEP round-trip fidelity for both pieces
all independently re-verify clean. No open defects remain from this
verifier's review. Recommend proceeding to the next gate (assembly
integration / Fable design audit) for `base_station_case.py`.
