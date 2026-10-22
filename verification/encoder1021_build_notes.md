# Encoder 1021: magnet cap and encoder casing, implementer build notes

Implementer: cad-implementer (Sonnet), 2026-10-22. Status: built, 54/54 acceptance tests pass, exports and renders current.
NOT yet independently verified (the `geometry-verifier` report is still to come). Not committed.

- Spec: `cad/ENCODER_1021_SPEC.md`. Master values: `cad/params.py`, block `ENC1021_*` (appended, nothing existing changed).
- Parts: `cad/parts/encoder1021.py` (`make_magnet_cap()`, `make_casing()`, `export_all()`, reference/assembly helpers).
- Tests: `tests/test_encoder1021.py` (54 items). Regenerate everything with `/usr/bin/python3 -m cad.parts.encoder1021` (about 30 s),
  check with `/usr/bin/python3 -m pytest tests/test_encoder1021.py` (about 45 s).
- Frame: v3 station frame (origin on the shaft axis in the slip-in motor-plate face, +y toward the spool, +z up, +x into the room).
  STEP files are in this frame; STL files are in print orientation (below).

## 1. Interfaces re-measured from `cad/reference/station_1021/*.step` (shifted by (0, 0, -2.64))

All the spec's section 2 values agree with the STEPs to better than 0.1 mm (largest: 0.046 mm). Nothing was changed silently.

The extraction carries a common placement residual of (+0.004243, +0.001645, +0.003854) mm in (x, y, z): the spool centre is at
x = 0.004243, z = 0.003854, the spool outer face at y = 26.001645, and the divot floor / holes / shaft end sit at the same offsets.
With it removed every interface lands on an exact design number (max deviation of all measured items from `ENC1021_*`: < 1e-5 mm).
`reference_parts(corrected=True)` removes it; `corrected=False` is the plain "subtract 2.64" frame. Both are tested.

| feature | spec | measured (plain frame) | used |
|---|---|---|---|
| spool outer face / flange | y 26.0 | 26.0016 | 26.0 |
| shaft end | y 22.0 | 22.0016 (Ø5 with a D-flat at z = +2.0) | 22.0 |
| bore | Ø5.30, D-flat x = +2.15, through y 7-26 | Ø5.30, flat 2.1542 (axis x = 0.0042) | Ø5.30, 2.15 |
| back-plate face / divot floor | x -21.1 / -22.1 | -21.1458 / -22.1458 | -21.15 / -22.15 (differs 0.046 from spec rounding) |
| divot rim, centre | 24.0, y 45.0, z 0 | 24.00, y 45.0016, z 0.0039 | 24.0, (45.0, 0) |
| divot holes | Ø3.46, 9.5 square, 4.0 deep | Ø3.45, y 40.2516 / 49.7516, z 4.7539 / -4.7461, bottom x -26.1458 | Ø3.45, 9.5 pitch |

**Spec point that is wrong or at least ambiguous: the divot is not a straight-walled pocket with R1.0 corners.** It is a dish: floor
22 x 22, a **quarter-round R1.0 wall** from the floor up to the 24 x 24 rim, 1.0 deep, so the wall is vertical only at the rim. Three of
its four corners are R1.0 spherical patches (R1.0 plan corners at the rim, sharp at the floor); the fourth, at (+y, +z), is a sharp mitre. A straight-sided 23.6 foot bottomed on the floor interferes with the wall by 8.6 mm3
(a wedge along all four sides; test `test_a_plain_square_foot_would_not_seat_in_the_divot`) and only seats about 0.6 mm deep. The
foot's bottom edge is therefore rounded R1.0 (`ENC1021_FOOT_KEY_R`), which keeps 0.2 mm lateral play over the full 1.0 mm key depth.

## 2. Derived levels (from `ENC1021_*`; one edit regenerates both parts)

| level | y (mm) | derivation |
|---|---|---|
| peg end | 22.6 | spool face 26.0 - peg length 3.4 (0.6 above the shaft end) |
| pocket floor | 26.75 | magnet face - (MAGNET_T + 0.05) |
| magnet face = head top | 29.3 | 26.0 + head 3.3 (head grows if MAGNET_T + 0.05 + 0.75 > 3.3) |
| chip face | 30.8 | magnet face + AIR_GAP 1.5 |
| frame / tab front | 31.0 | chip face + 0.2 (the chip sticks out 0.2 mm) |
| PCB front / back | 32.25 / 33.85 | chip face + CHIP_H 1.45 / + PCB_THICK 1.6 |
| hook catch face | 33.95 | PCB back + 0.1 |

The 0.05 mm of pocket depth beyond the magnet thickness is the CA glue film: with the magnet glued it sits flush at 29.3; bottomed in
the pocket (no glue) the face is at 29.25, still inside 29.3 +- 0.05. Both cases are tested.

## 3. Measured results

| item | value |
|---|---|
| cap | 1 valid solid, bbox x [-7.000, 7.000] y [22.600, 29.300] z [-7.000, 7.000] (14.0 x 6.7 x 14.0), volume 490.2 mm3, 0.62 g PETG |
| casing | 1 valid solid, bbox x [-22.150, 13.700] y [31.000, 56.800] z [-13.700, 13.700] (35.85 x 25.8 x 27.4), volume 3454.8 mm3, 4.39 g PETG |
| peg vs bore (y = 24.3, probed every 5 deg) | round part r 2.55 vs 2.65 (0.10 clear); flat 2.05 vs 2.15 (0.10 clear); 3 ribs at 60/180/300 deg, tip r 2.70 (0.05 crush) |
| peg length / end | head underside y 26.0, peg end y 22.6, length 3.4; 0.600 mm to the shaft end (distance measured) |
| magnet pocket | Ø6.2 (r 3.1 at all angles), floor y 26.75, depth 2.55, on the axis; reference magnet 0.05 from the cap |
| chip-face plane | tab back face 32.25 (all four tabs) - 1.45 = 30.8 (spec 30.8 +- 0.1) |
| board pocket | 23.4 x 23.4, centre offset from the axis 4e-8 mm (limit 0.05) |
| tabs | four, 3.0 x 3.0 plan, y 31.0 .. 32.25 |
| foot | 23.6 x 23.6, plan corner cylinders R1.2, x -22.15 .. -18.15 (1.0 keyed, 3.0 proud of the plate), contact patch on the floor 427.7 mm2 |
| foot side clearance to the divot | 0.200 +- 0.006 on all four sides at 7 depths between the floor and the rim; on the corner diagonals 0.366 mm at every depth (0.42 .. 0.78 at the divot's sharp (+y, +z) corner) |
| foot holes | 4 x Ø3.4 (teardrop top), axes within 2e-7 mm of the STEP's divot holes (limit 0.05) |
| screw access | Ø6.0 head + 0.5 tool clearance cylinders from the foot face outward: no contact with casing or station parts; 0.55 mm to the bridge |
| hooks | catch face 0.10 mm behind the PCB; lip overlap 0.40 mm over the PCB edge; 45 deg ramp; only over 8 mm of each +-z wall |

## 4. Interference and clearance (booleans and distances; corrected frame)

| pair | interference volume | min distance |
|---|---|---|
| casing vs Slipin_mount_piecev3 | 0.0000 mm3 | 0 (intended foot-on-floor face contact only; everything above the floor is >= 0.029 mm clear; the filler under the foot is 0.25 clear of the plate) |
| casing vs Spool1011 | 0 | 5.000 |
| casing vs Shell_Casing | 0 | 17.410 (limit 1.0) |
| casing vs Motor_Reference / Heat_horn / Wall_Mount_v3 | 0 | 12.87 / 31.00 / 7.64 |
| cap vs Spool1011 | **0.163 mm3 = the three crush ribs only** (cap without ribs: 0) | 0 (head on the spool face) |
| cap vs Motor_Reference | 0 | 0.600 (peg end to the shaft end) |
| cap vs Shell / Slipin / Heat_horn / Wall_Mount | 0 | >= 14.1 |
| cap swept 360 deg (10 deg steps) vs casing | 0 | 5.108 (exact body of revolution: 4.998), limit 1.0 |
| cap vs board (chip face) | 0 | 1.500 (the air gap; the chip is the only thing within 1.5 mm) |
| board vs casing | 0 | 0 (rests on the tabs); lips 0.1 behind the back face; 0.2 side play (tested to 0.19 / 0.25) |
| casing, y < 26 inside r 19 (line path) | 0 | casing starts at y = 31.0 |

Plain frame (subtract 2.64 only, no residual correction): casing vs slip-in 1.83 mm3 and cap vs spool 0.372 mm3, which is the
0.004 / 0.0016 mm extraction offset acting on the two intended contact faces (428 mm2 and 126 mm2). All other pairs are 0 in both frames.
So a verifier that uses the plain frame will see 1.83 mm3 at the foot and 0.37 mm3 at the cap, not zero. That is a contact, not a design error.

## 5. Print orientation (PETG, no supports)

- **Casing:** frame front face (y = 31.0) on the bed, +y up (print bbox 35.85 x 27.4 x 25.8). The ring, the four tabs and the bridge
  block all start on the bed; the foot plate stands up from the bridge block. 0.2 mm layers, at least 3 perimeters (the flex walls are
  1.2 mm = 3 lines). The thinned +-z walls bend in the layer plane when the board snaps in, which is why this orientation was chosen
  (a vertical tongue would bend across the layers).
- **Cap:** magnet face (y = 29.3) on the bed, peg up (print bbox 14 x 14 x 6.7). The ribs and the D-flat are vertical; the 0.3 mm head
  chamfer is the elephant-foot relief. Use 0.12 to 0.16 mm layers for the peg.
- **Overhang analysis** (`overhang_faces`, downward faces steeper than 45 deg + 0.5 deg tolerance, bed contact excluded):
  - cap: one face only, the magnet pocket floor seen as a ceiling, Ø6.2 = 30.2 mm2, a 6.2 mm bridge. No supports. If it sags,
    the floor rises into the pocket by the sag; scrape it flat before gluing the magnet.
  - casing, over the pocket: only the two hook catch ledges (0.6 mm wide x 8 mm = 9.6 mm2). Nothing else lies over the pocket plan.
  - casing, elsewhere: the foot's key-edge ledge on the -y side, 22.7 mm2, 0.93 mm wide, 33.2 .. 33.6 mm up (the bridge block fills
    in the rest of the foot underside). The foot screw holes are teardrops with 45 deg flanks, so they are not flagged.

## 6. Hand calculations (both consume the real solid, see `stiffness_estimate()` and `hook_estimate()`)

**Stiffness, 1 N push on the far (+x) wall of the frame, PETG E = 2100 MPa (`cad/materials.py`):** foot clamped by its four screws,
frame and PCB rigid, bridge neck as a cantilever of L = 31.85 mm (root at the foot face x = -18.15, load at x = +13.7, chip at x = 0,
so a = 18.15 mm). Weakest section of the solid at mid-span, counting only the part against the foot (y >= 33.2 up to the bridge top 36.2):
w = 27.4 - 2 x 1.6 (tie slots) = 24.2 mm, h = 3.0 mm, I = w h^3 / 12 = 54.45 mm4 (from the solid: 54.45). Chip motion
d = F a^2 (3 L - a) / (6 E I) = 0.037 mm in y (the weak direction), 0.0004 mm in z, 0.0001 mm in x. **Worst 0.037 mm < 0.1 mm.**
Not covered: foot-screw joint compliance and slip-in flexibility (assumed rigid), and the PCB's own flex.

**Snap hooks:** each +-z wall is a beam clamped between the corner blocks, span 23.4, height 4.05, t = 1.2, deflected 0.5 mm
(0.4 overlap + 0.1 margin) at mid-span: F = 192 E I d / L^3 = 9.2 N per wall, bending stress 27.6 MPa along x (inside the layer plane),
strain 1.3 %. That is about 60 % of PETG's 45 MPa XY yield: fine for a few insertions, not for repeated ones. If it is too stiff or cracks,
lower `ENC1021_FLEX_WALL_T` to 1.0 or `ENC1021_HOOK_OVERLAP` to 0.3.

## 7. Design choices beyond the spec text (check these)

1. **Board orientation:** the pad edges (DIR/SCL/SDA/GPO and VCC/OUT/GND) go to +-x, the hook edges to +-z, because the bridge sits on
   the -x wall. The two +-x walls stop flush with the PCB back face, so wires soldered on the back leave backward. The board may be
   turned 180 deg. Assumed: no components on the PCB back within 0.4 mm of the +-z edges over the middle 8 mm.
2. **Frame walls:** 2.0 mm on the +-x pad edges; the +-z hook walls are thinned to 1.2 mm between the corner blocks so that they flex
   (spec: "2 mm walls"). The outer bounding box is still 27.4 x 27.4 (corner blocks).
3. **Hooks** are lips on those thin walls (lateral flex) instead of cantilever tongues; reason in section 5.
4. **Bridge** is a full-width block from the frame front face to y = 36.2 (the highest it can go while keeping the screw heads open), so it
   doubles as the printing filler under the foot. Two zip-tie slots (3.0 x 1.6 at z = +-6.2) give strain relief for the five wires.
5. **Wires:** no separate notch; the pad edges are open (the +-x walls end flush with the PCB back), so the wires lead straight up from
   the pads and over the -x wall and the bridge, where the tie slots hold them.
6. **Foot bottom edge R1.0** (section 1). Its closest approach to the divot's own R1.0 floor edge is about 0.03 mm (normal gap; the
   lateral play stays 0.2). If the first print binds in the divot, set `ENC1021_FOOT_SIZE` to 23.4.
7. `ENC1021_PINS_ON = False`: the optional corner pins are built and tested when switched on (pitch placeholder 19.0, unmeasured).

## 8. Risks and things to measure before printing all five

- **AS5600 displacement tolerance.** The datasheet's recommended magnet-to-chip displacement is about 0.25 mm (verify). The stack here
  is foot play 0.2 + board play 0.2 + chip-to-board position + peg clearance 0.10 on the spool side, so the worst case is above it.
  Expect only extra INL, but check the MD/ML/MH status bits over a full turn, and if needed reduce `ENC1021_PCB_CLEAR` after measuring the board.
- **Crush ribs are finer than a 0.4 mm line** (0.15 high, 0.8 wide at the base, 0.3 at the tip) and may print weakly. If the cap spins
  in the bore, make `ENC1021_CAP_RIB_H` 0.2 and `ENC1021_CAP_RIB_W_TIP` 0.5.
- **The spool bore flat is at x = +2.15, the motor shaft flat at z = +2.0** (90 deg apart in the extraction). Harmless for the cap, which
  keys only to the bore; but check how the spool is driven, since any lash between spool and shaft shows up as position error.
- Divot hole hardware is still to be confirmed with Jasper (M2.5 heat-set insert fits Ø3.45; the casing's Ø3.4 passes M2.5 and M3).
- Chip centring on the board, PCB thickness, chip height, magnet size, hole pitch: all nominal until measured (spec section 6).
  A chip offset moves the frame and pocket (they follow `ENC1021_CHIP_OFFSET`); the foot and bridge stay put.
- The chip sticks out 0.2 mm in front of the frame: do not set the casing face down on the bench with the board in it.

## 9. Files

`cad/params.py` (appended block), `cad/parts/encoder1021.py`, `tests/test_encoder1021.py`, this file,
`exports/step/encoder1021_{casing,magnet_cap}.step`, `exports/stl/encoder1021_{casing,magnet_cap}.stl`,
`renders/encoder1021/`: for each part the 7 standard views (`*_front|rear|left|right|top|bottom|iso.png`, station frame, camera
at -y / +y / -x / +x / +z / -z), section views (`encoder1021_magnet_cap_section_z0`, `encoder1021_casing_section_z0|x0|hole_row`),
and the assembly preview with the slip-in mount, spool, motor and shell (`encoder1021_assembly_iso`, `_iso_front`, `_section_z0`).

## 10. Fit-test variants (added 2026-10-22, after the independent verification; nominal exports unchanged)

Built through the parameters (`encoder1021.build_variant(key)`, `params_override`), the master `ENC1021_*` values in `cad/params.py` are not
edited, and `git status` shows the nominal `encoder1021_{casing,magnet_cap}.step/.stl` unmodified. Regenerate with
`/usr/bin/python3 -m cad.parts.encoder1021 variants` (the plain run rewrites the nominal exports, do not use it for this).
Tests: `tests/test_encoder1021_variants.py` (22 items; each variant is one valid solid with the changed dimension measured on the solid,
zero interference with the station parts except the cap ribs, STEP round trip, STL watertight; together with the 54 nominal tests: 76 pass).

| file stem (`exports/step` and `exports/stl`) | overrides | measured on the solid |
|---|---|---|
| `encoder1021_magnet_cap` (nominal, existing) | rib 0.15 high, 0.30 tip | tip r 2.70, 0.05 crush, ribs overlap the bore by 0.163 mm3 |
| `encoder1021_magnet_cap_rib020` | `ENC1021_CAP_RIB_H` 0.20, `ENC1021_CAP_RIB_W_TIP` 0.45 | tip r 2.750, crush 0.10, 0.477 mm3, 490.8 mm3 |
| `encoder1021_magnet_cap_rib025` | `ENC1021_CAP_RIB_H` 0.25, `ENC1021_CAP_RIB_W_TIP` 0.45 | tip r 2.800, crush 0.15, 0.735 mm3, 491.3 mm3 |
| `encoder1021_casing_foot234` | `ENC1021_FOOT_SIZE` 23.4 | foot 23.4 x 23.4 (y max 56.7), side play 0.300 at 7 depths, normal gap foot round to divot wall 0.044 mm (nominal foot 0.0198), floor patch 21.4 flat, 3425.5 mm3 |

- Rib caps: only the rib height and tip width change (verifier condition 2 asked for a tip of at least 0.45 on the taller ribs); the peg round
  part (r 2.55), flat (2.05), pocket, head, magnet face 29.3 and peg end 22.6 are identical to nominal, the bounding box is the same
  14 x 6.7 x 14, and the 0.6 mm to the shaft end is unchanged. Without ribs the peg has zero interference in every variant.
- Foot 23.4: the cost is lateral play (0.3 mm per side instead of 0.2, so the foot term of the chip-offset stack-up grows). Use it only if the
  23.6 foot binds. Pocket, tabs, chip plane (30.8), hooks, holes (axes unchanged, coaxial with the divot holes), screw access, the bridge
  and the print orientation are the same as nominal; zero interference with all six station parts; foot-on-floor is the only contact.

## 11. v2: self-centring version (added 2026-10-22, answer to verification finding F1)

v1, the three fit-test variants and their exports are unchanged (tests prove a zero boolean difference). v2 is selected by `v2=True`
(`make_casing(v2=True)`, `make_magnet_cap(v2=True)`, `Cfg(v2=True)`) and reads `ENC1021_V2_<X>` where it exists, else `ENC1021_<X>`; the
new names are in the `ENC1021_V2_*` block of `cad/params.py`. Regenerate with `/usr/bin/python3 -m cad.parts.encoder1021 v2`.
Files: `exports/step|stl/encoder1021_casing_v2.*`, `encoder1021_magnet_cap_v2.*`; renders `renders/encoder1021/v2_*` (7 views of each part, 3 assembly
views, sections z0 / x0 / hole row, plus `v2_..._section_board_ribs`, `_section_foot_bumps`, `_section_magnet_ribs`); tests `tests/test_encoder1021_v2.py`
(41 items; with v1 and the variants 117 pass).

**Principle.** Every fit that set the chip position by CLEARANCE gets a large clearance (never binds, whatever the FDM size error) plus small crush
ribs / bumps that touch on all sides symmetrically. The centre then moves only with the ASYMMETRY of opposite ribs (`ENC1021_V2_RIB_TOL`, assumed
0.05 mm), not with over- or undersize, which is common to opposite sides and cancels.

### Geometry (all measured on the solids, tests in section "casing v2" / "cap v2")

| fit | v1 | v2 |
|---|---|---|
| board in pocket | pocket 23.4 (0.2 per side), no ribs | pocket **23.5** (0.25 per side) + **8 ribs**, 2 per wall at +-6.5 from the wall centre (clear of the pad rows |z| < 4 on the +-x edges, the hook lips |x| < 4 on the +-z edges and the corner tabs at 8.75): rib height above the wall **0.35 = 0.25 clearance + 0.10 crush**, tip **0.45**, base 0.9, from the bed face (y 31.0) to the wall top with a 45 deg lead-in; tips at 11.40 = board edge 11.50 - 0.10. Crush volume 0.504 mm3 in 8 pieces |
| magnet in pocket | Ø6.2 (0.10 per side) | pocket **Ø6.3** (0.15 per side) + **3 ribs** at 60 / 180 / 300 deg, height 0.27 = 0.15 + **0.12 crush**, tip 0.45, base 0.9, full pocket depth (y 26.75 to 29.3), 45 deg lead-in; tip radius 2.88; crush volume 0.413 mm3 in 3 pieces |
| peg in bore | 3 ribs 0.15 high, tip 0.30 (crush 0.05) | the rib020 variant: 0.20 high, tip **0.45**, tip radius 2.75, **crush 0.10**; 0.477 mm3 of interference (v1 0.163); equal to the variant peg to 1e-6 mm3 |
| foot in divot | 23.6, 0.2 per side, free to turn +-1.10 deg | **23.4** (0.3 per side, normal gap to the wall round 0.044, no bind risk) + **8 crush bumps**, two per side at +-9.0, 0.6 wide, tip = the MEASURED dish wall + **0.10 lateral** at every depth from 0.3 mm above the plate-face plane down to 0.7 mm below it. 8 pieces of 0.042 mm3 = 0.336 mm3 of interference with the slip-in |

The bump envelope is the foot's own rounded-slab construction sized to the divot (rim 24.0 + 2 x 0.10, bottom round R1.0 = the measured quarter-round),
so the crush is 0.10 along the whole bump instead of a point contact; below 0.7 mm depth, where the wall flattens and lateral interference stops
being a normal one, nothing touches. The floor contact stays the x datum. Entry is a wedge: while the foot is still raised the bump tips are
inside the wall line, the crush rises to 0.10 only as the foot settles. Hooks, tabs, chip plane (30.8), tie slots, holes, bridge and print orientation
are unchanged; the frame is 0.05 larger per side (27.5), the hook lip protrusion 0.65 (tip flat 0.35, still >= 0.2).

### Stack-up (verification item 5 method, `encoder1021.stackup()`)

Each term is a bound; worst case = linear sum, RSS = quadrature of the bounds; x = floor normal, z = across the divot; arm of the foot rotation = divot centre
to chip face = 14.2 mm. Only these parts (not the spool-on-shaft eccentricity, the printed slip-in / motor seat, PCB outline, chip placement on the board).

| source | v1 x / z | v2 x / z |
|---|---|---|
| foot | 0 / 0.273 (rotation 1.10 deg; reproduced here by bisection: 1.10 deg to the numerical-contact level) | 0 / 0.050 translation + 0 / 0.079 rotation (eps / lever 9.0 x 14.2) |
| board in pocket | 0.20 / 0.20 | 0.05 / 0.05 |
| peg in bore | 0.10 / 0.10 | 0.05 / 0.05 |
| magnet in pocket | 0.10 / 0.10 | 0.05 / 0.05 |
| worst case (sum) | 0.40 / 0.673, radial **0.783** | 0.150 / 0.279, radial **0.317** (target <= 0.4: met) |
| RSS | 0.245 / 0.367, radial **0.441** | 0.087 / 0.127, radial **0.154** (target <= 0.25: met) |

**It rests on eps = 0.05 mm**, the assumed asymmetry between opposite crush features. Every v2 term is proportional to eps, so the targets hold up to
eps = **0.063 mm** (worst case) and **0.081 mm** (RSS); at eps = 0.10 the worst case is 0.633 and the RSS 0.308, both over. eps is a bound on how much two
opposite ribs differ (line-width and corner effects of one print); a common over- or undersize does not enter. It must be measured on the first print
(for example caliper the board between its ribs and the foot between its bumps). Each crush is at least 2 x eps, so contact survives a systematic size
error of eps per side (tested).

### Foot: bumps, not locator pins

Two close-fit pins in diagonal divot holes were evaluated (`stackup(2, foot="pins")`): worst 0.341 / RSS 0.169 against 0.317 / 0.154 for the bumps, so both
meet the targets at the same eps, and the bumps win on four counts: (1) a bigger lever (9.0 from the side centre against 6.7 for pins 13.4 apart); (2) the
bumps use the 24 mm rim, a large feature printed to about +-0.1, while the pins would use blind Ø3.45 x 4 mm holes, which FDM undersizes and scatters more,
so eps for pins is likely larger (at eps = 0.07 the pins already exceed 0.4); (3) all four screws and all four holes stay available, and Jasper's open question
about the hardware in the divot holes (insert or screw) stays open; (4) no pin to break off. The cost of the bumps: a firm press-in (8 bumps, each about
0.6 x 0.7 mm of crush face; the four screws draw the foot down the wedge; file a bump or lower `ENC1021_V2_FOOT_BUMP_CRUSH` to 0.07 if it will not seat).

### Checks (same as v1, all pass)

- One valid solid each: cap v2 489.5 mm3 (0.62 g), bbox 14 x 6.7 x 14 as v1; casing v2 3427.0 mm3 (4.35 g), bbox x [-22.15, 13.75], y [31.0, 57.1] (the +y bumps
  stand 0.4 beyond the 23.4 foot), z +-13.75.
- Interference with the six station parts: casing: only the 8 bump pieces with the slip-in (0.336 mm3), 0 with all others; cap: only the peg ribs with the
  spool (0.477 mm3), 0 with all others; board vs casing: 8 rib pieces (0.504 mm3); magnet vs cap: 3 rib pieces (0.413 mm3); without ribs they are 0.
- Clearances: casing to shell 17.11 (limit 1.0), spool 5.0, motor 12.9, wall mount 7.6; cap swept 360 deg 5.15 mm from the casing, chip 1.500, shaft end 0.600;
  nothing of the casing at y < 26; screw-access cylinders clear (0.55 to the bridge); foot holes coaxial with the divot holes.
- Geometric play before contact is lost (the centring itself is the elastic balance of equal ribs): board +-0.09 keeps all 8 ribs, 0.11 loses two walls' ribs;
  foot +-0.09 keeps all 8 bumps, 0.11 loses two, rotation 0.5 deg keeps all 8, 0.8 deg loses some (v1: free to move +-0.2 and turn +-1.10 deg before touching).
- STEP round trip (volume 1e-6, bbox 5e-3), STL watertight and equal volume, exports current, renders present.

### Print (same orientations as v1)

Casing: frame front face (y = 31.0) on the bed, +y up; the board ribs start on the bed face and ramp at the top, so no new overhang over the pocket: over the pocket
only the two hook ledges (0.65 x 8 mm = 10.4 mm2). Elsewhere the foot key-edge ledge (about 1 mm, as v1) and the undersides of the foot bumps (0.4 mm ledges,
0.6 wide, about 2 mm2 together). Cap: magnet face on the bed, peg up; one 6.3 mm bridge over the pocket floor (30.7 mm2), the ribs stand on it, their 45 deg lead-in is
at the bed side and not flagged. Ribs 0.45 wide at the tip are one nozzle line plus a little: print the casing and cap at 0.12 to 0.16 mm layers, and expect the 0.35 high
board ribs to need a trial.

### Not covered / to measure on the first print

eps itself; the real board outline (a 23.2 board would crush the board ribs 0.2 more: still inside the 0.35 rib height, but the insertion force rises); the insertion
force of 8 board ribs, 3 magnet ribs and 8 foot bumps (all crush ribs in PETG yield locally; no force was calculated); ribs avoid the pad rows and hook lips, but the
photo of the board was not available: check that no part sits within 0.45 of the edge at +-6.5 on any side, and move `ENC1021_V2_BOARD_RIB_POS` if one does;
the spool-on-shaft eccentricity and the printed slip-in / motor seat position, which the verifier also left out.

## Assembly-frame STEP copies (lead, 2026-10-22)

Jasper asked for STEP files of the cap and casing to put into the final assembly. The v2 STEP files were already exported
from the CadQuery source (true B-rep solids, not converted from the STL), and they match the builder exactly (volume and
bounding box). `tools/export_encoder1021_asm.py` also writes copies placed in the coordinates of
`Assem_laundry_v3_step_1021.STEP`:

| file | frame | use |
|---|---|---|
| `exports/step/encoder1021_casing_v2.step`, `encoder1021_magnet_cap_v2.step` | station frame (origin on the motor shaft at the motor flange face) | mate in SOLIDWORKS: foot face to divot floor, holes to divot holes; cap axis to shaft axis, head face to spool face |
| `exports/step/encoder1021_casing_v2_asm1021.step`, `encoder1021_magnet_cap_v2_asm1021.step` | the 10/21 assembly's own coordinates | insert with the part origin on the assembly origin (or fix at the origin): they land in place |

Offset station frame → assembly: (1269.084243, 738.761645, 930.203854) mm = O + (0, 0, 2.64) + the extraction residual.
Check, run in assembly coordinates against the original assembly STEP: the casing touches only the slip-in mount (0.336 mm³:
the eight foot bumps) and the cap touches only the spool (0.477 mm³: the three crush ribs); the peg ends 0.6 mm short of the
motor shaft. These equal the corrected-frame values in `encoder1021_v2_verification.md`. Volumes unchanged by the round trip: PASS.
SOLIDWORKS will report these intended press-fit overlaps in an interference check.
