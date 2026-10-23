# Winch 3:1 spur drive train: build notes (implementer, 10/23; revision B: 18T/54T, D41)

**Revision B (D41, `cad/WINCH_GEAR3_SPEC.md` revision note).** The spur pair went from 20T/60T to **18T/54T at module 1**. Centre distance 36.00 + 0.20 =
36.20, spool axis z -33.56 (4 mm higher). Everything else is unchanged: every axial position, drum, flange, hubs, bore, shaft, bearings, spacer, magnet cap,
encoder bodies, pinion hub, bore and set screw. Part and file names follow the tooth counts: `spool_gear54`, `winch_gear3_pinion18`; the 20T/60T exports were
removed with `git rm` (`winch_gear3_spool_gear60.step/.stl`, `winch_gear3_pinion20.step`). **Old (revision A, 20T/60T) values are quoted as "rev A" for comparison.**

Spec: `cad/WINCH_GEAR3_SPEC.md` revision B. Parameters: `cad/params.py` block `WG3_*` (`WG3_Z_PINION = 18`, `WG3_Z_GEAR = 54`, `WG3_WINDOW_D = 10.0`,
`WG3_WINDOW_R = 17.5`; CD, spool axis and root radius still derive; new `WG3_MIN_CLEAR_HUB = 1.0`). Code: `cad/parts/winch_gear3.py` (the gear body, its part file stem and
the drive-body name are derived from the tooth count: `SPOOL = f"spool_gear{WG3_Z_GEAR}"`, `PINION_FILE = f"pinion{WG3_Z_PINION}"`). Tests: `tests/test_winch_gear3.py`
(29 tests, all pass, 145 s).

    cd /home/user/RoomCleaner && xvfb-run -a -s "-screen 0 1600x1200x24" /usr/bin/python3 -m cad.parts.winch_gear3    # exports, report, renders (about 2 min)
    cd /home/user/RoomCleaner && /usr/bin/python3 -m pytest -q -p no:cacheprovider tests/test_winch_gear3.py

## 1. Frames (read this before opening the STEPs)

- **Design frame** = `station_1021` without the extraction residual: motor axis x 0, z +2.64; +y along the motor shaft toward the spool; +x out of the wall;
  +z up; tab y 0 to 5; fin y -3.175 to 0. Every number below is in it.
- The builder adds `ENC1021_REF_RESIDUAL` (+0.004243, +0.001645, +0.003854) to every body it places, so the bodies coincide with Jasper's STEP files and
  with `heat_fin1021_1p8_asm1021.step` (the motor front face is on the fin's motor face to 1e-6 mm).
- **Assembly STEPs** (`*_asm1021.step`) are station_1021 + O (O = 1269.08, 738.76, 927.56, the repo convention for every `_asm1021` export): they drop into
  `Assem_laundry_v3_step_1021` at the origin. The slip-in and wall mount in `..._with_slipin_asm1021.step` are Jasper's STEPs translated by +O, unchanged.
- **Part STEPs and STLs are in the print frame**: axis +z, bed face z = 0 (parts are built in an axial frame, axis = local z = station y, local x = station x,
  local y = -station z; the print frame is that frame shifted so the bed face is z = 0).

## 2. What was built (all regenerated for revision B by `python -m cad.parts.winch_gear3`, exit 0)

| File | Content |
|---|---|
| `exports/step/winch_gear3_spool_gear54.step`, `exports/stl/..._spool_gear54.stl` | printable spool, print frame, one solid, body name `spool_gear54` |
| `exports/step/winch_gear3_spacer_near.step`, `.stl` | printable near spacer (body `spacer_near_w3`; geometry unchanged) |
| `exports/step/winch_gear3_magnet_cap.step`, `.stl` | printable magnet cap (body `magnet_cap_w3`; geometry unchanged) |
| `exports/step/winch_gear3_drive_asm1021.step` | 17 named bodies: `motor_front_cap, motor_stator, motor_winding, motor_rear_cap, motor_shaft, motor_connector, fin, pinion, spool_gear54, shaft, bearing_near, bearing_far, spacer_near, magnet_cap, magnet, as5600_chip, as5600_board` |
| `exports/step/winch_gear3_drive_with_slipin_asm1021.step` | the same plus `slipin_mount`, `wall_mount` |
| `exports/step/winch_gear3_pinion18.step` | the purchased pinion alone (body `pinion`, axial frame, axis z, hub y 5.825 .. 10.825, teeth to 20.825) |
| `exports/step/winch_gear3_gears_asm1021.step` | `pinion` + `spool_gear54` in mesh, assembly coordinates |
| `renders/winch_gear3/winch_gear3_{front,side,top,iso,mesh,section_axis,section_cap,section_tieoff}.png` | front (from +x), side (end view from +y), top (from +z), iso, mesh close-up (section y 15.827), section through the spool axis, zoom on the encoder end, section at the drum mid-plane (tie-off). Front, side, iso, mesh and section_axis looked at after the rebuild. |

STEP reimport (checked with `nema17_thermal.read_named_step`): every file above reimports with exactly these body names; volumes and bounding boxes agree
within 0.1 % (tests `test_step_round_trip_*`, `test_gear_step_files_*`).

## 3. Measured values (from the built solids; checked by the tests)

**Gear stage**

| Item | Rev B (18T/54T) measured | Rev A (20T/60T) |
|---|---|---|
| Centre distance (bore axes of pinion and spool) | **36.2000** (nominal 36.00 + 0.20) | 40.2000 |
| Spool axis, design frame | x 0.0000, z -33.5600 | z -37.5600 |
| Tooth counts counted on the solids (tip faces) | 54 and 18: ratio 3.000 | 60 and 20 |
| Gear tip / root diameter | **Ø56.000 / Ø51.500** (tip faces R28.0, root faces R25.75; axis-aligned bbox x +-28.000 because a tooth sits on the x axis, y +-27.970 because a space sits on the y axis) | Ø62.000 / Ø57.500 |
| Pinion tip / root | **Ø20.000 / Ø15.500**; hub Ø14, y 5.825 to 10.825; teeth y 10.825 to 20.825 | Ø22.000 / Ø17.500 |
| Mesh, 21 poses over one pinion pitch (0 to 20 deg in 1 deg steps, gear -1/3) | overlap 0.0000 mm3 at every pose; **minimum flank distance 0.1168 mm** at every pose | 0, 0.117 |
| Backlash at the pitch circle (calculated) | **0.246 mm transverse** (0.1 gear thinning + 2 x 0.2 x tan 20 deg), 0.231 mm normal; 1.56 deg at the pinion, 0.52 deg at the spool = 0.068 mm of cable at the drum | 0.246 / 0.231; 1.4 deg, 0.47 deg, 0.06 mm |
| Gear tip to pinion hub (solid distance) | **1.364 mm** (>= 1.0, spec section 5; radial 36.20 - 28.0 - 7.0 = 1.2 at the tooth on the line of centres, but a space faces the hub so the nearest tip is a half pitch off) | 2.33 (>= 1.5) |
| Gear to fin / motor front cap / stator / winding / rear cap / shaft / connector | 10.83 / 12.00 / 22.0 / 22.0 / 44.0 / 5.83 / 46.6 mm (all >= 1.5) | 10.83 / 12.00 / 22.0 / 22.0 / 44.0 / 6.82 / 46.7 |
| Pinion hub to the tab face | 0.825 mm | 0.825 |
| Phasing | gear tooth SPACE on the line of centres (axial-frame phase -93.333 deg = 266.667 = line of centres -90 deg minus half a pitch), pinion TOOTH on it (90 deg); pinion rotates +, gear -1/3. A test checks it on the solids (`test_gear_space_faces_the_pinion_tooth_at_the_mesh_point`) | -93 deg / 90 deg |

**spool_gear54** (print frame; design y = z + 10.825): y 10.825 to 44.0 = z 0 to 33.175; one valid solid; V = 22 987.9 mm3, **29.2 g PETG** (rev A 27 345.9 mm3, 34.7 g).

| Feature | Rev B measured |
|---|---|
| Gear | z 0 to 10 (y 10.825 to 20.825), 54 tip faces from z 0.3 to 10 |
| Bed-face chamfer | tooth outline on the bed face reaches R27.7 (tip R28 minus 0.3) |
| Windows | 6 x Ø10 on R17.500, through the 10 mm gear; outer edge R22.5: **rim 3.25 mm below the root R25.75 (>= 3), web 5.0 mm to the drum core (>= 2)**; inner edge R12.5 is 2.5 mm outside the 10 mm full-spool line radius; spaced 60 deg, a spoke (not a window) on the line of centres. Rev A: 6 x Ø11 on R20, rim 3.25, web 7.0 |
| Drum | R7.5, y 20.825 to 36.825 (unchanged) |
| Outer flange | R18, y 36.825 to 39.825; its inner face (y 36.825) overhangs the Ø15 drum by 10.5 mm (unchanged) |
| Far hub | R6, y 39.825 to 43.7; Ø9 land (R4.5) y 43.7 to 44.0 (unchanged) |
| Bore | Ø7.00 through, on the axis (unchanged) |
| Tie-off | Ø1.4 chord hole, axis 5.25 mm off the spool axis toward +x, along z, at y 28.825; ligaments 1.05 mm to the bore, 1.55 mm to the core surface (unchanged, probed in the solid by the test) |

**pinion** (purchased steel, 18T): V = 2 928.1 mm3, 23.0 g steel (rev A 27.6 g). Ø5 bore, M3 set-screw hole at the hub mid-plane y 8.325 toward +z (D-flat), unchanged.

**spacer_near_w3**: y 5.0 to 10.825 (5.825 long), Ø10 body, Ø7.10 bore, Ø9 lands 0.3 proud on both ends (flat end faces: prints on either), V = 217.9 mm3, 0.28 g (unchanged).

**magnet_cap_w3**: Ø12, y 49.3 to 55.55 (6.25); Ø7 bore y 49.3 to 52.3; web y 52.3 to 53.05 (0.75); Ø6.3 x 2.5 pocket y 53.05 to 55.55 with 3 crush ribs
(protrusion 0.27 = 0.15 + 0.12 crush, tip at R2.88, tip 0.45 / base 0.9 wide, 45 deg lead-in at the mouth; ENC1021_V2 rule, first rib at 90 deg of the axial frame).
V = 514.6 mm3, 0.65 g (unchanged). Shaft end (52.0) is 0.3 mm short of the bore floor; cap face is 0.3 mm above the far bearing (49.0).

**Encoder stack** (unchanged, but 4 mm higher with the spool axis): magnet Ø6 x 2.5 y 53.05 to 55.55; chip 6 x 4 x 1.45, chip face y 57.05 (air gap 1.5 to the magnet face), PCB 23 x 23 x 1.6 at y 58.5 to 60.1, all centred on the spool axis, PCB z -45.06 to -22.06 (rev A -49.06 to -26.06).

**Other bodies**: shaft Ø7 x 55, y -3.0 to 52.0; 687 envelopes (Ø7 x Ø14 x 5, plain rings) y 0 to 5 and 44 to 49. Motor = `nema17_thermal` bodies, front face on the fin; its
shaft has the 0.5 mm D-flat on +z (66 mm2) from the boss end to the shaft end; shaft end y 20.825.

**Masses** (typical densities, not certified; bearings are solid-ring envelopes, a real 687 weighs about 2 g, not 4.5):

| Body | Rev B | Rev A |
|---|---|---|
| spool_gear54 / spool_gear60 (PETG) | 29.2 g | 34.7 g |
| pinion (steel) | 23.0 g | 27.6 g |
| shaft | 16.6 g | 16.6 g |
| 2 bearings | 2 x 4.5 g | 2 x 4.5 g |
| magnet / spacer / cap | 0.53 / 0.28 / 0.65 g | 0.5 / 0.28 / 0.65 g |
| **drive train without motor and fin** | **79.3 g** | 89.5 g |

The old Spool1011 is replaced (7 992 mm3, about 10 g).

## 4. Overlap audit of the drive bodies (all pairs, in the assembly)

Only one pair overlaps: `magnet_cap` - `magnet`, **0.4125 mm3 by design** (the three crush ribs bite 0.12 mm into the Ø6 magnet; the test bounds it by the rib geometry).
SolidWorks interference detection will flag it; it is the interference fit. Every other pair is <= 0.01 mm3 (contacts: shaft in the bores, lands on the races,
magnet on the pocket floor, chip on the PCB, motor front face on the fin, pinion bore on the shaft's round part). The D-flat side of the pinion bore is closed by the set screw
(M3, modelled as a plain Ø3.0 hole at the hub mid-plane y 8.325, radial toward +z). Meshing teeth at the reference pose: zero overlap (0.0000 mm3, `test_mesh_has_no_overlap_through_a_tooth_pitch` and the 21-pose sweep above).

## 5. Interferences with Jasper's current slide-in, wall mount and shell (redesign inputs, not failures)

Design-frame coordinates (residual removed), volumes of the boolean intersection (pieces under 0.01 mm3 dropped). **Rev B (18T/54T, spool axis z -33.56) next to rev A (20T/60T, z -37.56, from the first build).**

| Jasper part | Drive body | Rev B mm3 | Rev A mm3 | Where (rev B) | What it is |
|---|---|---|---|---|---|
| `Slipin_mount_piecev3` | `spool_gear54` | **2451.6** | **3953.3** | three regions: | |
| | back plate (x < -21.15) | 1233.3 | 2003.4 | x -28.00 to -21.15, y 10.82 to 20.83, z -51.82 to -15.30 | gear teeth through the back plate (plate x -34.6 to -21.2); includes 4.0 mm3 of tooth tips at x -21.67 to -21.15, z -16.77 to -15.30 |
| | deck block (x > -21.15, z < -42.40) | 1133.2 | 1860.6 | x -21.15 to 13.85, y 10.82 to 20.83, z -52.38 to -42.40 | deck block of the lower lug (deck top z -42.4, bottom z -52.4); all of it under the gear face (y 10.825 to 20.825). Rev A also had 58.8 under the drum and 41.5 in the far cheek: the drum now stays above the deck (drum bottom z -41.06) |
| | above the deck top (z > -42.40) | 85.1 | 89.3 | x -21.15 to 13.85, y 10.82 to 25.56, z -42.40 to -31.48 | 72.3 is the Ø15 drum through the 2 mm far cheek wall (y 23.56 to 25.56, x -7.50 to 2.08, z -41.06 to -31.48); 12.8 is gear teeth just above the deck top (y 10.82 to 20.83, z -42.40 to -40.38). Rev A: 83.5 + 5.8 |
| `Slipin_mount_piecev3` | `shaft` | **0** | 54.8 (2 x 27.4) | none; closest approach 0.127 mm | the shaft (z -37.06 to -30.06) no longer cuts the two 2 mm lug cheeks (y 5.6 to 7.6 and 23.6 to 25.6). Rev A: x -3.50 to 1.85, z -41.06 to -35.71. A 0.13 mm margin is not a design clearance: Jasper's cheeks are being redesigned anyway |
| `Slipin_mount_piecev3` | `spacer_near` | **13.0** | 35.3 | x -5.00 to -0.13, y 5.56 to 7.56, z -38.56 to -33.69 | spacer against the near cheek only (rev A: also the deck, y 5.56 to 10.52) |
| `Wall_Mount_v3` | `spool_gear54` | **27.3** | 697.3 | two pieces: | |
| | | 25.8 | 686.1 | x -14.29 to -8.48, y 10.82 to 20.83, z -59.40 to -55.91 | bottom of the gear (z down to -61.53) in the wall mount's lower part (top face z -55.91) |
| | | 1.5 | 11.2 (12 slivers) | x -16.87 to -15.92, y 10.86 to 20.83, z -56.22 to -55.91 | one sliver of tooth tips at the same lower part. Rev A's tip slivers on the wall-mount face at x about -29.8 are gone (tips now reach x -28.0 only) |
| `Shell_Casing` (information) | `spool_gear54` | **730.4** | 1164.6 | two pieces: | |
| | | 369.0 | 548.6 | x -14.54 to 14.54, y 36.83 to 39.83, z -50.01 to -44.17 | the Ø36 flange against shell material up to z -44.17 (rev A: flange and drum, x -16.74 to 16.74, y 25.81 to 39.83) |
| | | 361.4 | 616.0 | x 14.09 to 25.17, y 10.82 to 20.83, z -49.17 to -44.17 | gear teeth in the shell wall (rev A: x 14.09 to 30.03) |
| `Shell_Casing` (information) | `as5600_board` | 32.9 | 180.1 | x -11.50 to 11.50, y 58.50 to 60.10, z -45.06 to -44.17 | the 23 x 23 board against shell material up to z -44.17 |
| `Shell_Casing` (information) | `bearing_near`, `bearing_far` | **0** | 6.1 each | none | bearing bottoms are now at z -40.56, above the shell top (-44.17) |
| `Spool1011` (the part being replaced) | `pinion` | 2012.9 | 2012.9 | x -7.50 to 7.50, y 7.00 to 20.83, z -4.86 to 10.14 | unchanged: it sits on the motor shaft |
| `Spool1011` | `motor_shaft` | 8.4 | 8.4 | x 2.15 to 2.50, y 7.00 to 20.83, z 1.36 to 3.92 | unchanged |

No overlap with the slip-in or the wall mount: `pinion`, all `motor_*`, **`shaft`** (new in rev B), `bearing_near`, `bearing_far`, `magnet_cap`, `magnet`, `as5600_chip`, `as5600_board`.
The pinion hub (y 5.825 to 10.825) clears the tab (y 0 to 5) by 0.825 and every other slip-in feature. The test `test_interference_with_current_slipin_and_wall_mount`
now asserts that exactly these three pairs interfere: (`spool_gear54`, slip-in), (`spacer_near`, slip-in), (`spool_gear54`, wall mount).

What the mount has to do (for Jasper, not designed here), revision B numbers:
- Cut the back plate (x < -21.15) and the deck block (z < -42.4) away over the gear: Ø56 gear, x +-28.0, z -61.53 to -5.59, y 10.825 to 20.825; drum Ø15 to y 36.825;
  Ø36 flange y 36.825 to 39.825 (reaches z -51.56); the whole spool occupies y 10.825 to 44.0.
- Replace the lug cheeks: near 687 seat Ø14 x 5 at y 0 to 5 in the tab, extended down from z -18.5 (the tab's lower edge) to at least z -40.56 (seat centre z -33.56);
  far 687 seat y 44 to 49 in a new far cheek; the shaft runs y -3.0 to 52.0 (3 mm behind the tab, free below the motor and fin).
- The AS5600 board is 23 x 23 at y 58.5 to 60.1 (z -45.06 to -22.06): it needs its casing/bridge beyond the far cheek; the magnet face is at y 55.55, chip face 57.05.
- Wall mount: the gear's lowest teeth reach z -61.5 (x -14.3 to -8.5 is where the wall mount's lower part, top z -55.91, is hit); the face at x -29.8 is no longer reached.
- Pinion set screw: M3 radial toward +z (onto the D-flat), at y 8.325, in the 5 mm hub between the tab (y 5) and the teeth (y 10.825): it needs access from +z above the hub.
- Shell (information): shell material up to z -44.17 (a floor or wall top face) is in the way of the Ø36 flange, the gear teeth at x > 14 and the board.

## 6. Print notes

- `spool_gear54`: near gear face (y 10.825, z 0 in the STEP/STL) on the bed, axis up, the far hub builds on top of the Ø36 flange. **The flange's inner face (y 36.825, z 26.0)
  overhangs the Ø15 drum by 10.5 mm and is printed on supports**; the cable touches that face, so sand it smooth. The Ø1.4 chord hole is horizontal (small bridge; clear with a 1.4 mm drill).
  The Ø7.00 bore prints about 6.9: press fit on the Ø7 shaft (the spool turns the shaft, which carries only the magnet). The six Ø10 windows are vertical, no supports.
  The 0.3 x 45 deg chamfer on the bed-face teeth is in the model.
- `spacer_near_w3`: either end face on the bed (both are Ø9 lands), no supports. Ø7.10 bore: slip fit.
- `magnet_cap_w3`: bearing-side face (y 49.3, the Ø7 bore opening) on the bed, pocket up (magnet face up), no supports: the 0.75 web bridges the Ø7 bore.

## 7. Assumptions I introduced (the spec is silent) and open points

1. **Pinion tooth thinning 0** (`WG3_PINION_TOOTH_THIN`): a purchased steel pinion has the full tooth; the 0.10 is only on the printed gear.
2. **Tie-off direction**: the hole's axis is offset toward +x (as Spool1011's hole at x +6) and runs along z; the spec gives only "5.25 mm off the axis". Say if it should be on the -x side.
3. **Motor shaft D-flat on +z**, copied from Motor_Reference; `nema17_thermal` itself has no flat, so the flat is cut in the assembly copy only (the thermal parts and exports are untouched).
4. **Set-screw hole**: Ø3.0 plain hole (as NEMA17T_TAP_D), hub mid-plane, +z. The set screw itself is not a body.
5. **Land height** 0.3 mm on the spacer too (the spec gives "Ø9 lands" without a height; the spool lands were 0.3 proud).
6. **Window phase** 0 deg (spoke on the line of centres), **rib phase** 90 deg: free choices.
7. **Bearings are plain rings** (envelope), the chip is a 6 x 4 x 1.45 block (`ENC1021_CHIP_BODY`), the board has no holes or pads.
8. The magnet pocket is exactly 2.5 deep (no glue-film extra as in encoder1021), per the spec; the magnet sits on the floor.
9. The cap bore (Ø7.00) has no lead-in chamfer and prints about 6.9: press fit by hand or a light tap.
10. Densities are typical, not certified (PETG 1.27 from `THERMAL_DENSITY_G_CM3`, steel 7.85, NdFeB 7.5).
11. **Revision B, hub clearance parameter**: spec section 5 relaxes the gear-tip to pinion-hub criterion to >= 1.0 mm and keeps 1.5 mm for the motor body and the fin, so `WG3_MIN_CLEAR` (1.5, motor and fin) gained a sibling `WG3_MIN_CLEAR_HUB = 1.0` in the `WG3_*` block, from the spec; no other parameter was added.
12. **Revision B, interference test**: the old test required the shaft and the near spacer to hit the slip-in. With the spool axis 4 mm higher the shaft no longer does (section 5), so the test now asserts the exact set of interfering pairs instead.

**Left for others (not edited, outside this assignment):** `tests/test_winch_gear3_verify.py` still expects 20T/60T, the body name `spool_gear60`, `winch_gear3_spool_gear60.stl` and the rev A interference volumes, so it fails until the verifier updates it;
`calculations/winch_gear3.py` has `Y_LEWIS = {20: 0.320, 60: 0.422}` and will raise `KeyError` for 18 and 54 until the calculation is rerun with the Lewis factors for 18T and 54T; `DESIGN_STATE.md` line 643 still names `winch_gear3_pinion20.step`.

No inconsistency in the revised spec blocked the build.
