# Winch 3:1 spur drive train: build notes (implementer, 10/23)

Spec: `cad/WINCH_GEAR3_SPEC.md` as revised after the first stop report (commits 94be76d, aed5cfa) plus the coordinator's decisions: cap 6.25 thick and
shaft 55 long, windows Ø11, AS5600 on the encoder1021 convention with an `as5600_chip` body, tie-off as a chord hole, the gear's near face on the
bed, the near hub split off as `spacer_near_w3`, 0.3 x 45 deg chamfer on the bed-face teeth. Parameters: `cad/params.py` block `WG3_*` (appended; no
other block touched). Code: `cad/parts/winch_gear3.py`. Tests: `tests/test_winch_gear3.py` (25 tests, all pass, about 2.3 min).

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
- Spec section 5 still says "far flange face down" for the spool: stale. I followed section 3 and the coordinator: the gear's near face is on the bed.

## 2. What was built

| File | Content |
|---|---|
| `exports/step/winch_gear3_spool_gear60.step`, `exports/stl/..._spool_gear60.stl` | printable spool, print frame, one solid |
| `exports/step/winch_gear3_spacer_near.step`, `.stl` | printable near spacer |
| `exports/step/winch_gear3_magnet_cap.step`, `.stl` | printable magnet cap |
| `exports/step/winch_gear3_drive_asm1021.step` | 17 named bodies: `motor_front_cap, motor_stator, motor_winding, motor_rear_cap, motor_shaft, motor_connector, fin, pinion, spool_gear60, shaft, bearing_near, bearing_far, spacer_near, magnet_cap, magnet, as5600_chip, as5600_board` |
| `exports/step/winch_gear3_drive_with_slipin_asm1021.step` | the same plus `slipin_mount`, `wall_mount` |
| `renders/winch_gear3/winch_gear3_{front,side,top,iso,mesh,section_axis,section_cap,section_tieoff}.png` | front (from +x), side (end view from +y), top (from +z), iso, mesh close-up (section y 15.825), section through the spool axis, zoom on the encoder end, section at the drum mid-plane (tie-off). All eight looked at. |

## 3. Measured values (from the built solids; checked by the tests)

**Gear stage**

| Item | Measured |
|---|---|
| Centre distance (bore axes of pinion and spool) | 40.2000 (nominal 40.00 + 0.20) |
| Spool axis, design frame | x 0.0000, z -37.5600 |
| Tooth counts counted on the solids (tip faces) | 60 and 20: ratio 3.000 |
| 60T gear tip / root diameter | Ø62.000 / Ø57.500 (tip faces R31.0, root faces R28.75; axis-aligned bbox +-30.973 because no tooth sits on an axis) |
| 20T pinion tip / root | Ø22.000 / Ø17.500; hub Ø14, y 5.825 to 10.825; teeth y 10.825 to 20.825 |
| Mesh, 5 poses over one pinion pitch (0, 4.5, 9, 13.5, 18 deg, gear -1/3) | overlap 0, minimum flank distance 0.117 mm at every pose |
| Backlash (calculated) | 0.246 mm transverse at the pitch circle (0.1 gear thinning + 2 x 0.2 x tan 20 deg), 0.231 mm normal; 1.4 deg at the pinion, 0.47 deg at the spool = 0.06 mm of cable at the drum |
| Gear tip to pinion hub | 2.33 mm (>= 1.5) |
| Spool to fin / motor front cap / stator / winding / rear cap / shaft / connector | 10.83 / 12.00 / 22.0 / 22.0 / 44.0 / 6.82 / 46.7 mm (all >= 1.5) |
| Pinion hub to the tab face | 0.825 mm |
| Phasing | gear tooth SPACE on the line of centres (axial-frame phase -93 deg = 267), pinion TOOTH on it (90 deg); pinion rotates +, gear -1/3 |

**spool_gear60** (print frame; design y = z + 10.825): y 10.825 to 44.0 = z 0 to 33.175; one valid solid; V = 27 345.9 mm3, **34.7 g PETG**.

| Feature | Measured |
|---|---|
| Gear | z 0 to 10 (y 10.825 to 20.825), 60 tip faces from z 0.3 to 10 |
| Bed-face chamfer | tooth outline on the bed face reaches R30.7 (tip R31 minus 0.3); 16.5 mm3 removed |
| Windows | 6 x Ø11 on R20.000, through the 10 mm gear; outer edge R25.5: **rim 3.25 mm below the root (>= 3), web 7.0 mm to the drum core (>= 2)**; spaced 60 deg, a spoke (not a window) on the line of centres |
| Drum | R7.5, y 20.825 to 36.825 |
| Outer flange | R18, y 36.825 to 39.825; its inner face (y 36.825) overhangs the Ø15 drum by 10.5 mm |
| Far hub | R6, y 39.825 to 43.7; Ø9 land (R4.5) y 43.7 to 44.0 |
| Bore | Ø7.00 through, on the axis |
| Tie-off | Ø1.4 chord hole, axis 5.25 mm off the spool axis toward +x (as Spool1011), along z, at y 28.825; spans the chord +-5.36 and is open on the winding surface at both ends; ligaments **1.05 mm to the bore, 1.55 mm to the core surface** (probed in the solid) |

**spacer_near_w3**: y 5.0 to 10.825 (5.825 long), Ø10 body, Ø7.10 bore, Ø9 lands 0.3 proud on both ends (flat end faces: prints on either), V = 217.9 mm3, 0.28 g.

**magnet_cap_w3**: Ø12, y 49.3 to 55.55 (6.25); Ø7 bore y 49.3 to 52.3; web y 52.3 to 53.05 (0.75); Ø6.3 x 2.5 pocket y 53.05 to 55.55 with 3 crush ribs
(protrusion 0.27 = 0.15 + 0.12 crush, tip at R2.88, tip 0.45 / base 0.9 wide, 45 deg lead-in at the mouth; ENC1021_V2 rule, first rib at 90 deg of the axial frame).
V = 514.6 mm3, 0.65 g. Shaft end (52.0) is 0.3 mm short of the bore floor; cap face is 0.3 mm above the far bearing (49.0).

**Encoder stack**: magnet Ø6 x 2.5 y 53.05 to 55.55; chip 6 x 4 x 1.45, chip face y 57.05 (air gap 1.5 to the magnet face), PCB 23 x 23 x 1.6 at y 58.5 to 60.1, all centred on the spool axis.

**Other bodies**: shaft Ø7 x 55, y -3.0 to 52.0; 687 envelopes (Ø7 x Ø14 x 5, plain rings) y 0 to 5 and 44 to 49. Motor = `nema17_thermal` bodies, front face on the fin; its
shaft got the 0.5 mm D-flat on +z (Motor_Reference has the flat at axis + 2.0 toward +z), 66 mm2, from the boss end (y 2.0 in the motor frame) to the shaft end;
shaft end y 20.825.

**Masses** (typical densities, not certified; bearings are solid-ring envelopes, a real 687 weighs about 2 g, not 4.5): spool 34.7 g, pinion (steel) 27.6 g,
shaft 16.6 g, bearings 2 x 4.5 g, magnet (NdFeB 7.5) 0.5 g, spacer 0.28 g, cap 0.65 g; drive train without motor and fin 89.5 g. The old Spool1011 is replaced
(7 992 mm3, about 10 g).

## 4. Overlap audit of the drive bodies (all pairs, in the assembly)

Only one pair overlaps: `magnet_cap` - `magnet`, **0.4125 mm3 by design** (the three crush ribs bite 0.12 mm into the Ø6 magnet; the test bounds it by the rib geometry).
SolidWorks interference detection will flag it; it is the interference fit. Every other pair is <= 0.01 mm3 (contacts: shaft in the bores, lands on the races,
magnet on the pocket floor, chip on the PCB, motor front face on the fin, pinion bore on the shaft's round part). The D-flat side of the pinion bore is closed by the set screw
(M3, modelled as a plain Ø3.0 hole at the hub mid-plane y 8.325, radial toward +z).

## 5. Interferences with Jasper's current slide-in and wall mount (redesign inputs, not failures)

Design-frame coordinates (residual removed), volumes of the boolean intersection.

| Jasper part | Drive body | Volume mm3 | Where | What it is |
|---|---|---|---|---|
| `Slipin_mount_piecev3` | `spool_gear60` | **3953.3** in total, in three places: | | |
| | | 2003.4 | x -30.97 to -21.15, y 10.82 to 20.83, z -52.38 to -15.40 | gear teeth through the back plate (plate x -34.6 to -21.2) |
| | | 1860.6 | x -21.15 to 13.85, y 10.82 to 25.56, z -52.38 to -42.40 | deck block of the lower lug (deck top z -42.4, bottom z -52.4): 1760.3 under the gear (y 10.825 to 20.825), 58.8 under the drum (y 20.825 to 23.6), 41.5 in the far cheek (y 23.6 to 25.6) |
| | | 89.3 | x -17.39 to 13.85, y 10.82 to 25.56, z -42.40 to -32.85 | far cheek of the lug (2 mm wall y 23.6 to 25.6): 83.5; the other 5.8 is gear and drum at y 10.8 to 23.6 just above the deck top |
| `Slipin_mount_piecev3` | `shaft` | 54.8 (2 x 27.4) | x -3.50 to 1.85, z -41.06 to -35.71; y 5.56 to 7.56 and y 23.56 to 25.56 | the shaft passes through both 2 mm cheek walls of the lug (cheeks at y 5.6 to 7.6 and 23.6 to 25.6) |
| `Slipin_mount_piecev3` | `spacer_near` | 35.3 | x -5.00 to 2.93, y 5.56 to 10.52, z -42.56 to -34.63 | spacer against the near cheek and the deck |
| `Wall_Mount_v3` | `spool_gear60` | **697.3** in total: | | |
| | | 686.1 | x -24.30 to -8.45, y 10.82 to 20.83, z -66.60 to -55.91 | bottom of the gear (z down to -68.5) in the wall mount's lower part |
| | | 11.2 (12 slivers, 0.08 to 1.88 each) | x -30.97 to -29.79; y 10.82 to 12.17 and 19.26 to 20.83; z -45.9 to -29.2 | tooth tips (x to -30.97) in a wall-mount face at x about -29.8 |

No overlap with the slip-in or the wall mount: `pinion`, all `motor_*`, `bearing_near`, `bearing_far`, `magnet_cap`, `magnet`, `as5600_chip`, `as5600_board`.
The pinion hub (y 5.825 to 10.825) clears the tab (y 0 to 5) by 0.825 and every other slip-in feature.

What the mount has to do (for Jasper, not designed here):
- Cut the back plate (x < -21.15) and the deck block (z < -42.4) away over the gear: Ø62 gear, x +-31, z -68.56 to -6.56, y 10.825 to 20.825; drum Ø15 to y 36.825;
  Ø36 flange y 36.825 to 39.825 (reaches z -55.56); the whole spool occupies y 10.825 to 44.0.
- Replace the lug cheeks: near 687 seat Ø14 x 5 at y 0 to 5 in the tab, extended down from z -18.5 (the tab's lower edge) to at least z -44.56 (seat centre z -37.56);
  far 687 seat y 44 to 49 in a new far cheek; the shaft runs y -3.0 to 52.0 (3 mm behind the tab, free below the motor and fin).
- The AS5600 board is 23 x 23 at y 58.5 to 60.1 (z -49.06 to -26.06): it needs its casing/bridge beyond the far cheek; the magnet face is at y 55.55, chip face 57.05.
- Wall mount: the gear's lower teeth reach z -68.5 and x -30.97; the wall mount's lower part (x -24.3 to -8.45, z below -55.9) and a face at x -29.8 are in the way.
- Pinion set screw: M3 radial toward +z (onto the D-flat), at y 8.325, in the 5 mm hub between the tab (y 5) and the teeth (y 10.825): it needs access from +z above the hub.

For information (the shell is Jasper's to redesign; the spec asked only for slip-in and wall mount): `Shell_Casing` overlaps `spool_gear60` by 1164.6 mm3
(616.0 at x 14.09 to 30.03, y 10.82 to 20.83, z -49.17 to -44.17; 548.6 at x -16.74 to 16.74, y 25.81 to 39.83, z -52.15 to -44.17), `as5600_board` by 180.1 mm3
(z -49.06 to -44.17) and each bearing by 6.1 mm3 (z -44.56 to -44.17): shell material up to z -44.17 (a floor or wall top face) is in the way of the spool, board and bearing seats. The old
`Spool1011` overlaps `pinion` by 2012.9 mm3 and `motor_shaft` by 8.4 mm3 (it sits on the motor shaft, y 7 to 26): it is the part being replaced.

## 6. Print notes

- `spool_gear60`: near gear face (y 10.825, z 0 in the STEP/STL) on the bed, axis up, the far hub builds on top of the Ø36 flange. **The flange's inner face (y 36.825, z 26.0)
  overhangs the Ø15 drum by 10.5 mm and is printed on supports**; the cable touches that face, so sand it smooth. The Ø1.4 chord hole is horizontal (small bridge; clear with a 1.4 mm drill).
  The Ø7.00 bore prints about 6.9: press fit on the Ø7 shaft (the spool turns the shaft, which carries only the magnet). The six Ø11 windows are vertical, no supports.
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

No further inconsistency in the revised spec blocked the build.
