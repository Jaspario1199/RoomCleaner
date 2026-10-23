# Winch station, 3:1 spur reduction: drive-train reference (spec, lead, 10/23)

Jasper (10/23): "lets go with spur gears" (3:1, after "I want to use a bevel gear system on the motor mounts to increase torque
3:1"; the lead advised a parallel-axis stage instead of bevels). Recorded as D40. Jasper designs the mount, cheeks and shell in
SolidWorks himself; this spec is the **drive train he designs around**: the motor where it is now, a purchased steel pinion on
its shaft, and the spool on its own shaft with a printed 60-tooth gear, all placed in the `station_1021` frame so the STEP drops
into his assembly.

## 1. Frame and fixed geometry (do not change)

- Frame `station_1021` (`cad/reference/station_1021/*.step`, `cad/params.py` FIN1021 block): motor axis at x = 0, z = +2.64;
  +y along the motor shaft toward the spool side; +x out of the wall; +z up. The PETG motor tab of the slide-in is y 0 to 5;
  the 1/8 in fin is y −3.175 to 0.
- Motor: NEMA 17 (`cad/parts/nema17_thermal.py`, NEMA17T_*): front face at y = −3.175 (behind the 1/8 in fin, D38), shaft Ø5
  with a 0.5 mm D-flat, end at y = −3.175 + 24.0 = **20.825**.
- Existing parts kept for context only (not modified): `Slipin_mount_piecev3.step`, `Wall_Mount_v3.step`, `Heat_horn.step`
  (replace by the 1/8 in fin `exports/step/heat_fin1021_1p8_asm1021.step`), `Motor_Reference.step`.

## 2. Gear stage (approved: spur, 3:1)

| Item | Value | Why |
|---|---|---|
| Module, pressure angle | 1.0, 20° | the common module for off-the-shelf steel pinions on 5 mm shafts |
| Pinion (purchased, steel) | 20 teeth, Ø5 bore, set screw on the D-flat; teeth 10 mm face; hub Ø14 × 5 mm on the tab side | steel set screw on the steel flat replaces the printed set-screw joint that may slip before the motor (weakest-link study) |
| Gear (printed PETG, part of the spool) | 60 teeth, face 10 mm, tooth thinning 0.10 mm (generator default) | ratio 3.00 |
| Centre distance | nominal m (20 + 60) / 2 = 40.00; **built 40.20** (+0.20 backlash allowance, steel against printed) | claw gears use +0.30 for printed against printed |
| Spool axis | x = 0, z = 2.64 − 40.20 = **−37.56** (directly below the motor) | shortest bracket from the deck; the cable still leaves downward; the cable hole stays under the drum |
| Pinion position | teeth y 10.825 to 20.825 (flush with the shaft end); hub y 5.825 to 10.825 | 0.825 mm clear of the tab face |
| Gear position | teeth y 10.825 to 20.825, aligned with the pinion | |

Use the repo's involute generator `cad/gripper_v3_fit_review_20261018/gears.py` `gear(n, module, width, phase, reduction,
root_radius)`. Phase the gear so a gear tooth space faces the pinion tooth at the mesh point (no overlap at the reference pose).

## 3. Spool on its own shaft (one printed PETG part, `spool_gear60`)

Along y, on the spool axis (x 0, z −37.56):

| Section | y range | Size |
|---|---|---|
| Near hub (rotates) | 5.0 to 10.825 | Ø12; end face at y 5.0 is a Ø9 land 0.3 mm proud (touches only the 687 inner race) |
| Gear | 10.825 to 20.825 | 60T, m 1.0 (tip Ø62); six lightening windows Ø12 on R 20 (keep ≥ 3 mm rim below the root and ≥ 2 mm web to the hub) |
| Drum | 20.825 to 36.825 | Ø15 core (7.5 mm radius, as Spoolv3, so the calibration's core radius stays); the gear's side face is the inner flange |
| Outer flange | 36.825 to 39.825 | Ø36 × 3 (as Spoolv3) |
| Far hub | 39.825 to 44.0 | Ø12; end face Ø9 land 0.3 mm proud |
| Bore | through | Ø7.00 (prints about 6.9: press fit on the Ø7 shaft; the shaft carries no torque, only the encoder magnet) |
| Tie-off | axial Ø1.4 through the drum at r = 5.5 mm | 1.3 mm ligaments to the bore and the core |

## 4. Purchased and reference bodies (assembly only)

| Body | Placement |
|---|---|
| Shaft, Ø7 × 50 steel dowel | y 0 to 50 on the spool axis |
| 687 bearing (7 × 14 × 5), near | y 0 to 5 (seat in the motor tab, which Jasper extends down to the spool axis) |
| 687 bearing, far | y 44 to 49 (seat in a far cheek Jasper adds) |
| Magnet cap (printed, `magnet_cap_w3`) | on the shaft end: Ø12 × 3.0, y 49.3 to 52.3; Ø7 bore 2.0 deep from the bearing side; Ø6.3 × 2.5 magnet pocket on the outer face with 3 crush ribs (the ENC1021_V2 rule: 0.15 per side + 0.12 crush) |
| Magnet | Ø6 × 2.5 diametric, in the cap |
| AS5600 board envelope | 23 × 23 × 1.6 board, centred on the axis, chip side facing the magnet, 1.5 mm air gap: board y 53.8 to 55.4 |
| Pinion (purchased) | section 2 |
| Motor | `cad/parts/nema17_thermal.py` bodies at front face y −3.175 (or the block motor of `thermal_station1021`) |
| 1/8 in fin | `exports/step/heat_fin1021_1p8_asm1021.step` (as is) |

## 5. Deliverables

- `cad/params.py`: new block `WG3_*` (every number above, one definition each; nothing duplicated from other blocks: import
  NEMA17T_*, FIN1021_*, GRIPV7 bearing sizes where they already exist).
- `cad/parts/winch_gear3.py`: builds the printable `spool_gear60` and `magnet_cap_w3`, the reference bodies, and the assembly.
- Exports:
  - `exports/step/winch_gear3_spool_gear60.step` / `exports/stl/winch_gear3_spool_gear60.stl` (print frame: drum axis +z, far
    flange face down; record which face goes on the bed);
  - `exports/step/winch_gear3_magnet_cap.step` / `.stl`;
  - `exports/step/winch_gear3_drive_asm1021.step`: every body named (`motor_*`, `fin`, `pinion`, `spool_gear60`, `shaft`,
    `bearing_near`, `bearing_far`, `magnet_cap`, `magnet`, `as5600_board`), in the station_1021 frame;
  - `exports/step/winch_gear3_drive_with_slipin_asm1021.step`: the same plus Jasper's current slide-in and wall mount, for him to
    see what has to change.
- Renders `renders/winch_gear3/`: front, side, top, iso of the drive; the mesh close-up; and a section through the spool axis.
- `tests/test_winch_gear3.py`: valid solids, counts, the key dimensions above, centre distance 40.20, ratio 3, no overlap between
  any two drive bodies (≤ 0.01 mm³), gear tip to pinion hub ≥ 1.5 mm, gear to motor body and to the fin ≥ 1.5 mm, STEP
  round trip (volume and bounding box within 0.1 %).
- `verification/winch_gear3_build_notes.md`: what was built, measured values, and the **interferences with Jasper's current
  slide-in** (expected: the spool and gear cut through the lower lug and deck region; list each with its volume and location).
  These are redesign inputs for Jasper, not failures.

## 6. Do not

- Do not modify Jasper's reference STEP files, the encoder1021 parts, the heat fin parts, or any existing export.
- Do not design the mount, the far cheek or the shell (Jasper does); only report where they must change.
- Do not change software or configs.
