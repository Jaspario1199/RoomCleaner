# Gripper 1021 housing lid: implementer build notes

Implementer: cad-implementer (Sonnet), 2026-10-22. Status: built, 17/17 acceptance tests pass, exports and renders current.
NOT yet independently verified. Not committed.

- Part: `cad/parts/gripper1021_housing_lid.py` (`make_lid()`, `measure_opening()`, `arm_estimate()`, `keepout_solids()`, `export_all()`, `render_all()`).
- Params: `LID1021_*` block in `cad/params.py` (new names only). Tests: `tests/test_gripper1021_housing_lid.py` (17 items).
- Regenerate: `/usr/bin/python3 -m cad.parts.gripper1021_housing_lid` (about 15 s); check: `/usr/bin/python3 -m pytest tests/test_gripper1021_housing_lid.py` (about 25 s).
- Frame: the housing's bay frame (origin on the tube axis in the box bottom plane, +y up) = world minus `CAMBAY1021_BAY_ORIGIN_WORLD`. The STEP is in the
  world frame like the housing; the STL is in print orientation.

## 1. Opening and seat, measured from `exports/step/gripper1021_housing_cambay_34.step`

| feature | spec text | measured | used |
|---|---|---|---|
| seat plane (top of the seat ring) | y 1141.2 = box 50.0 | 50.000012 | 50.0 |
| rim top | y 1146.19 = box 55.0 | 55.000018 | 55.0 |
| opening | recess half 42.5 (`CAMBAY1021_TRI_LID_RECESS_HALF`) | 85.000 x 85.000 (half 42.5, centred on the tube axis to 3e-5 mm) | 42.5 |
| opening corners | not listed | **R12.5**, centres at +-30 (the pocket below has R10, centres +-30, so the ring is 2.5 mm wide all round) | R12.5 |
| seat | "lid seat" | a **2.5 mm wide ring** (area 776.7 mm2) between the 80 x 80 pocket (half 40) and the recess; below it the pocket is open down to y = 5 | ring 40 .. 42.5 |
| inside the recess | | nothing: no feature between y 50 and 55 within the recess outline (tested) | |

The STEP's own placement residual is (-3e-6, +1.2e-5, -2.9e-5) mm; the loader removes it so that the lid's seat face lies exactly on the seat plane (the plain
frame leaves contact slivers below 0.002 mm3, tested). The spec numbers agree with the STEP; the R12.5 corners and the fact that the lid is supported only on a
2.5 mm ring over an open pocket are the new information.

## 2. The lid

One printed part, no screws. All values in `LID1021_*`.

- **Plate** 1.8 mm thick on the seat ring (bottom face on y = 50.0, top face y = 51.8, 3.2 mm below the rim), outline = the recess offset 0.25 mm inward (84.5 x 84.5,
  R12.25 concentric with the R12.5), top edge chamfered 0.3 x 45 deg. Volume 12391 mm3, **15.7 g** PETG, bbox 85.3 x 1.8 x 85.3 (bump tips).
  The plate covers 645 mm2 of the 777 mm2 seat ring (the rest is slots and the notch).
- **Four crush bumps**, one per side in a pinwheel (the +z bump at x = +2, copies rotated by 90 deg). Tip **0.6 wide** (base 1.6 sunk into the arm), standing **0.40 mm**
  beyond the plate edge = 0.25 clearance + **0.15 interference** with the recess wall. 45 deg lead-in on the underside (the lid goes in underside first), so the bump grows
  from the edge to its full tip over 0.40 mm of height (tested at five heights).
- **Each bump sits on the free end of an in-plane cantilever arm**: arm 2.0 mm wide x 1.8 high, freed by a 1.0 mm L-shaped slot (along its inboard side and across its end),
  root 8 mm from the bump. Reason: a rigid plate with rigid bumps cannot be pressed into a rigid recess. Two opposite bumps with 0.15 mm each shorten an 84.5 mm strip by 0.3 mm,
  which needs 1134 N of axial force (E A x 0.3 / L), while the strip buckles at 119 N (Euler, pi^2 E I / L^2): the plate would simply bow. The arms turn the 0.15 mm into a controlled force.
- **Pry notch** on the +z side: 14 x 4.5 mm at x = -20, inner corners R2. Its outer 2.25 mm lies over the seat ring, its inner 2.25 mm past the ring's inner edge (z < 40) over the
  open pocket, so a screwdriver blade (tested: 8 x 1 mm pushed straight down through the notch, zero contact with lid and housing) or a fingernail goes under the plate edge.
  It is clear of the +z arm (x -3 .. 10) and of the corner (starts at |x| = 30).
- Light by design: 15.7 g, no skirt, no standoffs, no screws.

## 3. Measured results (booleans, probes and distances on the solids)

| item | result |
|---|---|
| lid | 1 valid solid; bbox x, z +-42.650, y 50.000 .. 51.800 |
| interference with the housing | **exactly 4 pieces, 0.157 mm3 each (0.627 mm3), one per bump tip**, 0.150 mm deep (tip 42.650 vs wall 42.500, probed at three heights on all four sides); the bare plate (no bumps) has zero interference, rests on the seat ring (distance 0, 0.02 mm lower collides), nothing else touches |
| insertion | lowered from 6 mm above to seated (8 heights): no contact above the rim, then only the four bump tips |
| tip width | 0.60 on all four bumps (limit >= 0.45) |
| cable holes | corner bores and lines: 39.4 mm; T_A / T_B / T_C bores 7.0 mm; lines leaving the T holes at 15 / 30 / 45 / 60 deg: 8.0 / 7.7 / 6.8 / **5.54 mm** (limit 5.0); steep lines at 75 deg 3.99 mm and straight up along the wall plane **2.25 mm** (the lid stays inside the 45 mm wall plane, so no line can reach it) |
| camera-bay cover | 21.0 mm, zero overlap; no overlap with the housing below the seat plane |
| 4 arms | the L-slot is open and the arm solid at its root and free end on every side (probed) |
| STEP round trip | volume equal (1e-6), bbox in the world frame centred on the bay origin; against the housing STEP as exported: the four bump tips plus contact slivers below 0.02 mm3 |
| STL | watertight, volume within 1 %, print pose bbox 85.3 x 85.3 x 1.8, bed plane exact |

## 4. Hand calculation of one bump arm (`arm_estimate()`, PETG E = 2100 MPa from `cad/materials.py`)

In-plane cantilever, free length L = 8 mm, I = h t^3 / 12 = 1.8 x 2.0^3 / 12 = 1.2 mm4: F = 3 E I d / L^3.

| case | deflection d | force per bump | strain |
|---|---|---|---|
| lid centred | 0.15 | 2.2 N | 0.70 % |
| printed interference 0.05 short / 0.05 more | 0.10 / 0.20 | 1.5 / 3.0 N | |
| lid pushed against one wall (whole 0.40 protrusion) | 0.40 | 5.9 N | 1.9 % |

Retention (vertical friction of the four bumps, mu 0.4, centred): 3.5 N against the lid's weight of 0.154 N, 23 times, still removable by hand. Bending is along the layers
(print is flat), so the strain is in the strong direction. Friction between the arm underside and the seat ring is ignored.

## 5. Print orientation

**Top face down** on the bed (print bbox 85.3 x 85.3 x 1.8; the bed face is the top face, 6804 mm2 after the chamfer, slots and notch). Every wall is vertical; the bump lead-ins
and the underside of the plate face up, and the top chamfer sits on the bed (elephant-foot relief). Overhang analysis (downward faces steeper than 45 deg + 0.5 deg): **none**.
Minimum features: bump tip 0.6, slot 1.0, arm 2.0, plate 1.8. A flat 85 x 85 x 1.8 PETG plate can warp: use a brim or a heated bed and a cool part before pulling it off.

## 6. Risks and assumptions

- **The notch needs free space below it.** The blade goes 2.25 mm past the seat ring into the pocket; the electronics inside must leave that gap on the +z side (not known from the STEP).
- The lid is supported only on the 2.5 mm seat ring; pressing in the middle bends it (about 0.65 mm under 10 N at the centre, plate theory, not simulated). It is a dust and shield lid, not a structural one.
- The top face is 3.2 mm below the rim. A flush lid would need a 5 mm plate; the brief said light, so it was not done.
- The interference and force numbers assume the printed recess is the CAD recess; the arms make the grip insensitive to +-0.1 mm of size error (1.5 to 3.0 N for +-0.05 mm) but a recess printed
  more than 0.15 mm oversize leaves the lid loose (the bump tips lose contact); `LID1021_INTERF` 0.20 gives 3 N.
- Not covered: friction coefficient, creep of the arms over time (PETG under 2 N at 0.7 % strain is low), the electronics' own height under the lid, the wire path if a cable has to leave through the lid.

## 7. Files

`cad/params.py` (appended `LID1021_*`), `cad/parts/gripper1021_housing_lid.py`, `tests/test_gripper1021_housing_lid.py`, this file, `exports/step/gripper1021_housing_lid.step`,
`exports/stl/gripper1021_housing_lid.stl`, `renders/gripper1021_lid/`: the 7 standard views (`gripper1021_housing_lid_top|bottom|front|rear|left|right|iso.png`, bay frame;
top = the +y top face seen from above, bottom = the underside with the arms and slots, front / rear = edge-on from -z (camera-bay side) / +z (notch side), left / right from -x / +x) and
four views on the housing (`..._on_housing_iso`, `_section_y`, `_section_arm`, `_section_x0`).
