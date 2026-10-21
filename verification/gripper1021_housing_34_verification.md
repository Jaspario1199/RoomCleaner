# Independent verification: Gripper 1021 electrical housing with three-cable holes ("_34")

Verifier: geometry-verifier (Sonnet), 2026-10-21. Nothing in the repository was repaired or edited; the only files written are this report and
`tests/test_gripper1021_housing_34_verification.py`.

- Part under test: `exports/step/gripper1021_housing_cambay_34.step` and `exports/stl/gripper1021_housing_cambay_34.stl`.
- Baseline: `exports/step/gripper1021_housing_cambay.step`, `..._cover.step`, Jasper's raw housing `cad/reference/gripper_1021/parts/05_..._NAUO5.step` (read only).
- Spec: `cad/GRIPPER_1021_SPEC.md` section 5 as amended by 5.1 (volume within 10 % of the designed cutter; 4.98 mm to the pocket's own R10 fillet accepted; cable lines: minimum > 0 and bay + cover clear by >= 5 mm).
- Implementer's notes (`verification/gripper1021_housing_34_build_notes.md`) were used only as hints. The implementer's tests, build script and cable-line analyzer were NOT imported or run (except that `tests/test_gripper1021.py`, the pre-existing baseline suite, was run for item 10).

## 1. Verdict: PASS

All 11 items pass; 70 of 70 verification tests pass (full run 10 min). No repair is required. Seven advisories (section 5) are things the lead should know, none of them a failure
against the criteria as amended by 5.1. The two cable-line minimums asked for:

| Cable-line minimum (42 966 lines) | Value | Where |
|---|---|---|
| Housing + bay + cover, overall | **0.2345 mm** (> 0, no line intersects) | hole A (mirror: hole B, 0.2346 mm); claw (0.2000, 0.2938) m, reference height 0.52 m, yaw -15 deg (B: claw (3.1528, 0.2938), yaw +15 deg); line elevation 82.98 deg, length 2.054 m; nearest point = top outer edge of the A wall (box (-45, 55, 27.56), room (0.149, 0.279, 0.567) m). Hole C: 0.4842 mm at claw (1.5841, 2.5432), yaw +15 deg, elevation 85.83 deg, rim edge at box (0.815, 55, -45). |
| Bay + cover only | **12.728 mm** (>= 5 mm) | hole C line; claw (1.5841, 2.5432) m, reference height 0.52 m, yaw -15 deg, elevation 86.25 deg; nearest point = top corner of the bay cover at box (0, 29.3, -45.85). A and B lines: 77.55 mm. |

## 2. Method (all measurements are on the exported files, not on the implementer's intermediate data)

- Frames: world -> box frame by subtracting (951.8475, 1091.1905, 1103.9899). Body frame: origin on the tube axis at box y = 7.82, +x = box x, +y = -box z, +z = box y.
- B-rep face parameters (exact cylinder / cone / plane parameters read from the STEP surfaces), face-by-face signature comparison against the baseline (type, area, centre of mass),
  point-in-solid probes (OCC `BRepClass3d_SolidClassifier`) with bisection, OCC edge-solid common, local volume differences, Monte Carlo volume,
  an own raster of the glyphs, an own ray-cast depth image of the STL, and an own segment-to-triangle distance code (self-checked against brute force, cross-checked against OCC `BRepExtrema`).
- Exact bounding boxes use `BRepBndLib.AddOptimal` (cq's `BoundingBox()` grows once a face has been meshed; it was not used for comparisons).
- Mutation self-check of the tests (scratch script, not committed): feeding the baseline as "the part" fails 02a/03a; a stray extra Ø2 hole fails 02a; an added 3 mm bump fails 02a, 02c and 02d;
  assuming a chamfer of 0.4 or 0.65 instead of 0.5 fails all nine chamfer probes. Weak spot: 02e (uniform random probes) did not catch the stray hole (too small a volume for 2500 probes); it is a secondary check, 02a/02c/02d are the primary ones.
- Repository untouched: md5 snapshot of `exports/`, `cad/step`, `cad/stl`, `renders/` before and after all runs shows no change by this work (the only differences in `verification/` are another agent's three-station files).

## 3. Expected vs measured

Tolerances are stated per row. `C / A / B` = holes T_C / T_A / T_B.

### Item 1. Solid

| Check | Expected | Measured | Tol | Result |
|---|---|---|---|---|
| Solids in file / shells | 1 / 1 | 1 `MANIFOLD_SOLID_BREP`, 1 solid, 1 shell | exact | PASS |
| Valid BREP | valid | `isValid` and `BRepCheck_Analyzer` both true | - | PASS |
| Volume | > 0 | 154 246.269 mm3 (baseline 154 311.087) | > 0 | PASS |
| Bounding box = baseline (box frame) | x -50..50, y 0..55.00002, z -101.3..49.99997 | identical, max difference 0.0 mm | 1e-4 mm | PASS |

### Item 2. Difference to the baseline: only three holes and three labels, nothing added

| Check | Expected | Measured | Tol | Result |
|---|---|---|---|---|
| Baseline faces changed | only the 6 hole-bearing wall faces (3 outer, 3 inner) | 6 of 187 changed, exactly those; 181 faces identical (type, area, centre) | area 1e-3 mm2, centre 1e-3 mm | PASS |
| Outer boundary of the 6 wall faces | unchanged | edge lengths and centres identical; they only gain inner loops (hole mouths, labels) | exact | PASS |
| New faces (91) and new inner loops: distance to nearest hole axis segment / label box | <= 3 mm | max 1.654 mm (faces), 1.644 mm (loops) | 3 mm | PASS |
| Nothing added: material side of 411 interior probes on the new faces | inside baseline material, void side empty in part | 0 violations | - | PASS |
| Removed volume, sum of local differences (holes 17.760 + 20.323 + 20.326, labels 1.688 + 1.913 + 2.474) | = global change | 64.484 mm3 local; global GProp difference 64.818 mm3; STL volume change -64.43 mm3 (agrees with the local sum within 0.06) | 0.5 mm3 (GProp error on a 154 000 mm3 solid is 2e-6 relative) | PASS |
| Random probes (2500 whole part, 2700 in the zones) | no added material, no change outside the zones | 0 added, 0 outside zones, 52 removed in zones | - | PASS |

### Item 3. Hole mouths (box frame, measured from the exact cylinder surfaces of the STEP)

| Hole | Outer mouth expected | Outer mouth measured | Inner mouth expected | Inner mouth measured | Result |
|---|---|---|---|---|---|
| T_C | (0, 42, -45) | (0, 42.0000, -45.0000), error 0 | (0, 42, -40) | (0, 42.0000, -40.0000), error 0 | PASS |
| T_A | (-45, 42, 25.98) | (-45, 42.0000, 25.9808), error 0.0008 | (-40, 42, 23.09) | (-40, 42.0000, 23.0940), error 0.004 | PASS |
| T_B | (45, 42, 25.98) | (45, 42.0000, 25.9808), error 0.0008 | (40, 42, 23.09) | (40, 42.0000, 23.0940), error 0.004 | PASS |

(Tolerance 0.01 mm; the spec table is rounded to 0.01.)

| Check | Expected | Measured C / A / B | Tol | Result |
|---|---|---|---|---|
| Bore diameter (cylinder face) | 2.000 | 2.0000 / 2.0000 / 2.0000 | 2e-4 | PASS |
| Axis horizontal | vertical component 0 | 0 / 0 / 0 | 1e-6 | PASS |
| Axis height | 42.000 | 42.0000 / 42.0000 / 42.0000 | 0.005 | PASS |
| Axis radial (misses the tube axis by) | 0 | 0 / 3e-10 / 4e-10 mm | 0.01 mm | PASS |
| Axis direction vs spec table | 0 deg | 0 / 0.028 / 0.028 deg (the table's 25.98 / 23.09 rounding) | 0.1 deg | PASS |
| Wall length along the axis | 5.000 / 5.7735 / 5.7735 | 5.0000 / 5.7735 / 5.7735 | 0.01 | PASS |
| Teardrop tip points +y: both flank planes' normals point down | yes | yes, all three | - | PASS |
| Tip apex above axis | 1.4142 (45 deg tangent tip) | 1.41421 / 1.41421 / 1.41421; flank 45.0000 deg from vertical | 0.005 / 0.1 deg | PASS |
| Probed half widths at the axis (left, right) / bottom / apex | 1.000 / 1.000 / 1.4142 | 1.0000, 1.0000 / 1.0000 / 1.4143 (all three) | 0.01 | PASS |
| Flank half width at 0.9 / 1.1 / 1.25 above axis | 0.5142 / 0.3142 / 0.1642 | 0.5143 / 0.3143 / 0.1642 (all three) | 0.012 | PASS |
| Probed cross-section area (0.05 mm grid) | 3.356 mm2 | 3.350 / 3.353 / 3.350 | 2 % | PASS |
| Chamfer at the outer mouth, C: cone | 45 deg, radius 1.5 at the wall plane, 1.0 at 0.5 mm depth | 45.000 deg, 1.5000, 1.0000 | 0.01 deg, 0.005 | PASS |
| Chamfer, all holes: probes at bottom, left, right of the mouth edge against an equal-distance 0.5 x 0.5 chamfer (+-0.03 mm; +-0.06 mm at the oblique bottom) | no failures | 0 failures in 9 probe sets (an assumed 0.4 or 0.65 chamfer fails all 9) | - | PASS |
| Clear through the wall: 6 lines (axis, +-0.9 lateral, -0.9, +0.9, +1.3 vertical) as OCC edges from 4 mm inside the pocket to 4 mm outside | 0 mm inside the part, wall material in the baseline | 0.000 mm inside the part on all 18 lines; the same lines have 5.000 mm (C) / 5.7735 mm (A, B) of material in the baseline; 53-56 axis point probes, 0 solid | 1e-6 mm | PASS |

### Item 4. Removed volume per hole vs the designed cutter (spec 5.1: within 10 %)

The designed cutter is modelled independently as the Ø2 teardrop prism through the 5 mm wall plus a 0.5 mm 45 deg mitred chamfer ring at the outer mouth (wall-normal model, integrated numerically).

| Hole | Removed (measured) | Designed cutter | Difference | Plain Ø2 bore (for information) | Monte Carlo cross-check | Result |
|---|---|---|---|---|---|---|
| T_C | 17.760 mm3 | 17.760 mm3 | 0.00 % | 15.708 (+13.06 %) | 17.61 +- 0.69 | PASS |
| T_A | 20.323 mm3 | 20.410 mm3 | -0.43 % | 18.138 (+12.04 %) | 20.72 +- 0.79 | PASS |
| T_B | 20.326 mm3 | 20.410 mm3 | -0.41 % | 18.138 (+12.06 %) | 20.72 +- 0.79 | PASS |

Teardrop bore alone 16.781 / 19.377 / 19.377 mm3; chamfer extra measured 0.979 / 0.946 / 0.949 mm3 (model 0.979 / 1.033 / 1.033). Hole faces stay inside the 5 mm wall slab (checked on every face).

### Item 5. Keep-outs (minimum distance from the hole's boundary faces, OCC `BRepExtrema`, to each feature category; hole faces include bore, flanks and chamfer)

| Feature | T_C | T_A | T_B | Required | Result |
|---|---|---|---|---|---|
| Corner cable holes (4 x Ø2) | 48.61 | 33.79 | 33.79 | >= 5 | PASS |
| Wire window (cut faces) | 20.50 | >= 40 (bbox bound) | >= 40 | >= 5 | PASS |
| Bay body | 17.48 | >= 40 (bbox bound) | >= 40 | >= 5 | PASS |
| Bay cover (separate part) | 11.23 | >= 40 (bbox bound) | >= 40 | >= 5 | PASS |
| Lid-seat ledge (y = 50) | 6.388 | 6.430 | 6.430 | >= 5 | PASS |
| Lid-recess wall (y 50..55, 2.5 mm inboard of the outer wall) | 6.388 | 6.430 | 6.430 | >= 5 | PASS |
| 8 x Ø3.3 floor holes | 42.68 | 36.56 | 36.56 | >= 5 | PASS |
| Tube hole Ø30 | 43.83 | 47.54 | 47.54 | >= 5 | PASS |
| Box corner R10 (outer, convex) | 33.5 | 7.366 | 7.366 | >= 5 | PASS |
| Rim top (y = 55) | 10.88 | 10.92 | 10.92 | >= 5 | PASS |
| Other housing faces (R75 blend for C; lid-recess R10 corner for A, B) | 8.574 | 7.583 | 7.583 | >= 5 | PASS |
| Pocket R10 fillet (the hole's own wall; exempt per 5.1, floor 4.95 mm) | 28.94 | **4.981** | **4.981** | accepted 4.98 | PASS (as amended) |

### Item 6. Labels

| Check | Expected | Measured C / A / B | Tol | Result |
|---|---|---|---|---|
| Glyph height | 4.0 mm | 4.000 / 4.010 (apex overshoot) / 4.000 | 0.05 | PASS |
| Depth | 0.4 mm | 0.4000 / 0.4000 / 0.4000 | 0.01 | PASS |
| Centre above the mouth | 5.0 mm | 5.000 / 4.995 / 5.000 | 0.1 | PASS |
| Lateral centre offset from the mouth axis | 0 | 0.000 / 0.000 / 0.000 | 0.2 | PASS |
| Glyph y range (box) vs chamfer top 44.12 and ledge 50 | clear by >= 0.5 mm | 45.00-49.00 / 44.99-49.00 / 45.00-49.00 | 0.5 | PASS |
| Glyph width | information | 3.30 / 3.50 / 3.00 mm | - | - |
| Area x depth vs removed volume | agree | 1.710 vs 1.688 / 1.940 vs 1.913 / 2.504 vs 2.474 mm3 | 3 % | PASS |
| Upright, unmirrored (C opens to the reader's right; B stem on the left; A apex up, bottom heavy, symmetric), computed from the exact floor faces | yes | yes, all three | - | PASS |
| Same reading from the STL in print orientation (own ray-cast depth image, camera right = forward x up), IoU with the STEP glyph | yes, IoU > 0.85 | yes; IoU 0.987 / 0.991 / 0.994; pit depth 0.400 | - | PASS |
| Thinnest stroke (largest opening disk leaving only corner pieces); median stroke | >= 0.4 mm | 0.42 / 0.43 / 0.42 mm; median 0.48 / 0.49 / 0.52 mm | 0.40 | PASS |

Glyphs as read from outside (up = up, right = reader's right), rasterised from the exact floor faces of the STEP and down-sampled for this report
(`ascii_glyph()` in the test file):

```
C  (3.30 x 4.00 mm, opens to the right)
...............##############.............
..........#######################.........
........###########################.......
......########...............########.....
....########...................#######....
...#######......................#######...
..#######........................#######..
.#######..........................######..
.######...................................
#######...................................
######....................................
######....................................
######....................................
######....................................
######....................................
#######...................................
.######...........................#######.
.#######..........................#######.
..#######........................#######..
...#######......................#######...
....########...................#######....
......#########..............########.....
.......#############################......
..........#######################.........
...............##############.............
```

```
A  (3.50 x 4.01 mm, apex up)
..................#########.................
.................##########.................
................############................
...............##############...............
...............######..######...............
..............######...#######..............
.............#######....#######.............
.............######......######.............
............######.......#######............
...........#######........#######...........
..........#######..........#######..........
..........######...........#######..........
.........######.............#######.........
........#######..............#######........
........######...............#######........
.......##############################.......
......################################......
.....########..................#######......
.....#######....................#######.....
....#######......................#######....
...#######.......................########...
...######.........................#######...
..#######..........................#######..
.#######...........................########.
#######.............................#######
#######..............................#######
```

```
B  (3.00 x 4.00 mm, stem on the left)
###############################............
###################################........
#####################################......
########..................############.....
#######.......................#########....
#######.........................########...
#######..........................#######...
#######..........................#######...
#######..........................#######...
#######.........................########...
#######........................########....
#######......................#########.....
####################################.......
#################################..........
#####################################......
#######################################....
#######.........................#########..
#######...........................########.
#######............................#######.
#######............................########
#######............................########
#######............................########
#######............................#######.
#######...........................########.
#######........................##########..
########################################...
######################################.....
###################################........
###############################............
```

## 4. Cable lines, three-station mode (items 7)

- Lines: from each hole's measured outer mouth centre to its station anchor prior (A (0.05, 0.05, 2.5932), B (3.3028, 0.05, 2.5932), C (1.6764, 2.6932, 2.5932) m). Room 3.3528 x 2.7432 m.
- Claw: body origin height (tube axis at box y 7.82) 0.52 .. 2.20 m in 11 steps (mouths 0.554 .. 2.234 m; this contains the spec's 0.56 m up to 0.4 m below the anchors = 2.1932 m), yaw -15 .. +15 deg in 7 steps,
  186 floor positions: 0.15 m grid inside the A-B-C triangle clipped to the 0.2 m wall margin, plus the six vertices of the clipped polygon and its centroid.
  14 322 lines per hole, 42 966 in all. Yaw 0: body +x = room +x, body +y = room +y = -box z (bay toward station C); verified: the bay is at box z < 0 (z min -101.3).
- Distance: exact segment-to-triangle minimum on a 0.01 mm tessellation of the housing + bay + cover, over the first 250 mm of each line (beyond that every point of the 170 mm radius part is > 80 mm away).
  Excluded as "own mouth": the faces within 2.5 mm of the line's own mouth (wall face, bore, chamfer), the debossed label of the same wall (its edges lie in the wall plane) and the pocket-side face of the same wall.
  Everything else counts, including the interior lid-recess faces 2.5 mm behind the wall (that is why the low-elevation minima below are about 2.4 mm: they are the lid recess, not an obstacle a cable can reach).
- Cross-check: the own distance code agrees with brute force (kernel self-check) and with OCC `BRepExtrema` on the six extreme lines and on 24 random lines (max difference 0.00011 mm).

| | T_C | T_A | T_B | Criterion | Result |
|---|---|---|---|---|---|
| All lines leave outward (minimum of line . wall normal) | +0.0372 | +0.0179 | +0.0179 | > 0 | PASS |
| Lines intersecting the claw solid | 0 | 0 | 0 | 0 | PASS |
| Minimum distance to housing + bay + cover (mm) | 0.4842 | 0.2345 | 0.2346 | > 0 | PASS |
| Minimum distance to bay + cover only (mm) | 12.728 | 77.55 | 77.55 | >= 5 | PASS |
| Lines closer than 0.5 mm / 1 mm | 2 / 67 | 18 / 106 | 14 / 72 | information | - |

Minimum by elevation band (mm), housing + bay + cover: 0-30 deg: C 7.76, A 2.42, B 2.47; 30-45: 6.74, 2.30, 2.47; 45-60: 4.66, 1.32, 1.32; 60-70: 2.69, 0.91, 0.91; 70-80: 1.41, 0.35, 0.35; 80-90: 0.48, 0.23, 0.23.
Every near miss is the top outer edge of the line's own wall (rim at y = 55, 13 mm above the mouth) for lines steeper than about 70 deg. At the worst pose the line passes 0.2345 mm from that edge,
which is about 1.0 deg of tilt toward the wall (0.2345 / 13 mm). The lowest reference height of the sweep (0.52 m) is slightly below the spec's 0.56 m, so the minimum is conservative.

## 5. Advisories (none is a failure against 5.1)

1. Near-vertical lines graze the rim edge (0.23 mm for A and B, 0.48 mm for C); about 1 deg of claw tilt toward the wall at the worst pose would touch it. This is the accepted flag 3 of 5.1; the file-the-edge practice stays the remedy.
2. A and B are oblique (30 deg to their walls). Their chamfer is an equal-distance 0.5 x 0.5 chamfer on the mouth edge: 0.5 mm wide on the wall face and 0.5 mm along the bore. It is 45 deg to the wall face only at the bottom of the mouth;
   at the lateral extremes the flank is 30 deg to the axis on the acute side and 60 deg on the obtuse side (measured). It does not deviate from "0.5 chamfer on the edge", but it is not a coaxial 45 deg countersink. C is an exact 45 deg cone.
3. Seven new sliver faces (areas 0 .. 3.2e-4 mm2) and a few sub-micron edges sit at the chamfer / flank transitions at the mouths (baseline has 3 such faces). The solid is valid, but SOLIDWORKS import may report small faces or need healing.
4. STL: watertight and consistently oriented once 118 micro-triangles that collapse at 0.1 micron (largest 1.6e-4 mm2; baseline STL has 12) are discarded; slicers discard them. STL volume is +0.200 % over the STEP; the baseline STL has the same +0.1996 % offset (tessellation tolerance 0.05 mm), and the volume change from the new features agrees (-64.43 vs -64.82 mm3).
5. Label pits are debossed 0.4 mm into a vertical wall, so their tops are horizontal ceilings (5.15 mm2 in all, unsupported depth 0.4 mm, one extrusion width). Unavoidable for deboss text. No other face in the hole bodies overhangs more than 45.0 deg (the sliver faces of advisory 3 are excluded).
6. The thinnest label stroke is 0.42 mm, close to a 0.4 mm nozzle line width; the median is about 0.5 mm. Expect legible but soft text at 0.4 mm layer width.
7. `cad/interfaces.py` has no 1021 / three-hole entries, so there was no interface contract to compare; `cad/params.py` `CAMBAY1021_TRI_*` values agree with the measured geometry and the anchors in the task (test 12a). The corner-hole configs still need re-deriving for the 1021 box (the spec's own flag 4).

## 6. Items 8 to 11

### Item 8. STEP round trip and STL

| Check | Expected | Measured | Tol | Result |
|---|---|---|---|---|
| STEP re-import (export from cq, re-import): solids, valid, faces | 1, valid, 278 | 1, valid, 278 | exact | PASS |
| Volume agreement | equal | 154 246.2688 -> 154 246.2702 mm3, relative 8.9e-9; second pass 2.6e-15 | 1e-6 | PASS |
| Bounding box agreement | equal | max difference 0.0 mm (second pass 0.0) | 1e-4 | PASS |
| Shipped STEP vs `make_34()` source | equal | volume relative 7.4e-9, bbox 2e-13 mm | 1e-4 | PASS |
| STL print orientation: bbox = STEP box rotated (x, -z, y) | x -50..50, y -50..101.3, z 0..55 | x -50.0..50.0, y -50.0..101.3, z 0.0..55.0 | 0.02 | PASS |
| Box bottom flat on the bed | all triangles on z = 0 face down | 10 148 mm2 on z = 0, all facing down (bay floor shares the plane) | 99.9 % | PASS |
| STL watertight, consistently oriented | 0 open edges | 0 (after discarding 118 collapsed micro-triangles, advisory 4) | 0 | PASS |
| STL volume vs STEP | match | 154 554.7 vs 154 246.3 mm3 (+0.200 %, same offset as the baseline STL +0.1996 %); change vs baseline -64.43 vs -64.82 mm3 | 0.25 % and 1 mm3 | PASS |
| STL vertices on the STEP surface (200 sampled) | 0 | max 7e-6 mm | 0.01 | PASS |
| STL has the through holes (4 lines per hole through the wall) | 0 crossings (baseline STL: 2) | 0 / 0 / 0 (baseline 2 on every line) | exact | PASS |

### Item 9. Printability (print orientation, box bottom down)

| Check | Expected | Measured | Result |
|---|---|---|---|
| New overhang steeper than 47 deg in the hole bodies | none beyond the teardrop tip (45 deg) | 1e-5 mm2 (noise); worst hole face 45.000 deg | PASS |
| Overhang area outside the hole / label zones | unchanged | 10 239.9055 mm2 in both | PASS |
| Label pits | information | 5.15 mm2 of 0.4 mm deep ceilings (advisory 5) | PASS |
| Label strokes >= 0.4 mm | yes | 0.42 / 0.43 / 0.42 mm | PASS |

### Item 10. Baseline untouched

| Check | Expected | Measured | Result |
|---|---|---|---|
| `make()` housing regenerates the baseline export | volume and bbox equal | volume 154 311.0867 vs 154 311.0866 (rel 4.9e-10), bbox 2.3e-13 mm | PASS |
| `make()` cover regenerates the cover export | equal | rel 3.4e-12, bbox 1.2e-10 mm | PASS |
| The four baseline export files vs git HEAD | identical blobs | identical | PASS |
| `tests/test_gripper1021.py` | passes | 40 passed (2:04) | PASS |

### Item 11. Body-frame points (origin on the tube axis at box y 7.82; +x = box x, +y = -box z, +z up)

| Point | Expected (m) | Measured (m) | Error | Tol | Result |
|---|---|---|---|---|---|
| T_C outer mouth | (0, +0.0450, +0.0342) | (0.00000, +0.04500, +0.03418) | 2e-5 | 6e-5 (the notes round to 0.1 mm) | PASS |
| T_A outer mouth | (-0.0450, -0.0260, +0.0342) | (-0.04500, -0.02598, +0.03418) | 2e-5 | 6e-5 | PASS |
| T_B outer mouth | (+0.0450, -0.0260, +0.0342) | (+0.04500, -0.02598, +0.03418) | 2e-5 | 6e-5 | PASS |
| Tube axis passes through box (0, *, 0) | 0 | 2.9e-5 mm | 0.01 mm | PASS |
| Corner-hole inner-mouth height (frame origin) | 7.82 | 7.8231 on all four (inner mouths (+-0.03707, +-0.03707, 0.0000) m) | 0.02 | PASS |
| Handedness: bay on box -z = body +y | yes | bbox z min -101.3 (bay), C hole on the bay side | - | PASS |

## 7. Reproduce

The `python3` on the default PATH has no CadQuery; use `/usr/bin/python3` (CadQuery 2.8.0, OCP 7.9.3.1, pytest 9.1.1, numpy, scipy, Pillow).

```
cd /home/user/RoomCleaner
/usr/bin/python3 -m pytest -p no:cacheprovider -q tests/test_gripper1021_housing_34_verification.py            # 70 tests, about 10 min (cable sweep about 4 min)
HOUSING34_RUN_BASELINE_SUITE=1 HOUSING34_VERIFY_JSON=/tmp/h34.json /usr/bin/python3 -m pytest -p no:cacheprovider -q \
    tests/test_gripper1021_housing_34_verification.py    # also runs tests/test_gripper1021.py (+2 min) and dumps all measurements to JSON
```

The test file writes nothing into the repository (STEP round-trip files go to a pytest tmp dir). Test groups: 01 solid; 02a-e difference; 03a-f holes; 04 volume; 05 keep-outs; 06a-c labels; 07a-d cable lines;
08a-e STEP / STL; 09, 09b printability; 10a-c baseline; 11a-b body frame; 12a-b parameters and renders; 99 JSON dump.

## 8. Not covered

- Fit of an actual Dyneema line, knot or washer in the Ø2 hole (physical test).
- Claw tilt (the sweep is yaw only, as specified); behaviour of the line over the chamfer lip (lines start at the mouth centre, as specified).
- Print quality of 0.43 mm label strokes and the 45 deg tips (needs a test print).
- The four corner-hole outer mouths in the body frame (the implementer's table lists them; only the inner mouths, which replace the configs' v6 values, were verified).
