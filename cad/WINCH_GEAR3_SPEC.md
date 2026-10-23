# Winch station, 3:1 spur reduction: drive-train reference (spec, lead, 10/23; revision B: 18T/54T)

**Revision B (Jasper, 10/23: "can we make the radius of both gears just a little smaller", D41).** The pair is 18T/54T at module 1
(was 20T/60T): both gears about 10 % smaller, ratio still 3.00, same tooth size and pinion family. Centre distance 36.20, spool axis
z −33.56. Every axial position, the drum, flange, hubs, shaft, bearings, cap and encoder are unchanged. Part and file names follow
the tooth counts (`spool_gear54`, `pinion18`); the 20T/60T exports are removed. Numbers below are revision B.

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
| Pinion (purchased, steel) | 18 teeth (tip Ø20), Ø5 bore, set screw on the D-flat; teeth 10 mm face; hub Ø14 × 5 mm on the tab side | steel set screw on the steel flat replaces the printed set-screw joint that may slip before the motor (weakest-link study) |
| Gear (printed PETG, part of the spool) | 54 teeth (tip Ø56), face 10 mm, tooth thinning 0.10 mm (generator default) | ratio 3.00 |
| Centre distance | nominal m (18 + 54) / 2 = 36.00; **built 36.20** (+0.20 backlash allowance, steel against printed) | claw gears use +0.30 for printed against printed |
| Spool axis | x = 0, z = 2.64 − 36.20 = **−33.56** (directly below the motor) | shortest bracket from the deck; the cable still leaves downward; the cable hole stays under the drum |
| Pinion position | teeth y 10.825 to 20.825 (flush with the shaft end); hub y 5.825 to 10.825 | 0.825 mm clear of the tab face |
| Gear position | teeth y 10.825 to 20.825, aligned with the pinion | |

Use the repo's involute generator `cad/gripper_v3_fit_review_20261018/gears.py` `gear(n, module, width, phase, reduction,
root_radius)`. Phase the gear so a gear tooth space faces the pinion tooth at the mesh point (no overlap at the reference pose).

## 3. Spool on its own shaft (one printed PETG part, `spool_gear54`)

Along y, on the spool axis (x 0, z −33.56):

| Section | y range | Size |
|---|---|---|
| Gear | 10.825 to 20.825 | 54T, m 1.0 (tip Ø56, root R 25.75); six lightening windows **Ø10 on R 17.5** (outer edge R 22.5: rim 3.25 mm below the root; inner edge R 12.5, 2.5 mm outside the 10 mm full-spool line radius so the line cannot drop into a window); 0.3 mm × 45° chamfer on the tooth edges of the bed face (y 10.825) against elephant foot |
| Drum | 20.825 to 36.825 | Ø15 core (7.5 mm radius, as Spoolv3, so the calibration's core radius stays); the gear's side face is the inner flange |
| Outer flange | 36.825 to 39.825 | Ø36 × 3 (as Spoolv3) |
| Far hub | 39.825 to 44.0 | Ø12; end face Ø9 land 0.3 mm proud |
| Bore | through | Ø7.00 (prints about 6.9: press fit on the Ø7 shaft; the shaft carries no torque, only the encoder magnet) |

The part runs y 10.825 to 44.0. **Print frame: the gear's near face (y 10.825) on the bed**; the far hub builds on top of the flange.
The outer flange's inner face (y 36.825) overhangs the Ø15 drum by 10.5 mm and is printed on supports (record it in the build
notes; the line touches that face, so it is sanded smooth). The near hub is a separate part (`spacer_near_w3`, below).
| Tie-off | Ø1.4 chord hole through the drum core, perpendicular to the axis, 5.25 mm off the axis, at the drum mid-plane y 28.825; both ends open on the winding surface (as Spool1011) | ligaments: 1.05 mm to the Ø7 bore, 1.55 mm to the core surface at the chord's closest point |

## 4. Purchased and reference bodies (assembly only)

| Body | Placement |
|---|---|
| Shaft, Ø7 × 55 steel dowel | y −3.0 to 52.0 on the spool axis (the 3 mm behind the tab is below the motor and the fin) |
| Near spacer (printed, `spacer_near_w3`) | y 5.0 to 10.825 on the shaft: Ø10 OD, Ø7.10 bore (slip), both end faces Ø9 lands (it touches only the 687 inner race and the gear face); prints on either end face |
| 687 bearing (7 × 14 × 5), near | y 0 to 5 (seat in the motor tab, which Jasper extends down to the spool axis) |
| 687 bearing, far | y 44 to 49 (seat in a far cheek Jasper adds) |
| Magnet cap (printed, `magnet_cap_w3`) | on the shaft end: Ø12, **y 49.3 to 55.55 (6.25 thick)**; Ø7 bore y 49.3 to 52.3 (3.0 deep; the shaft end at 52.0 leaves 0.3 mm); web y 52.3 to 53.05 (0.75, `ENC1021_CAP_FLOOR_MIN`); Ø6.3 × 2.5 magnet pocket y 53.05 to 55.55 with 3 crush ribs (the ENC1021_V2 rule: 0.15 per side + 0.12 crush); prints magnet-face up |
| Magnet | Ø6 × 2.5 diametric, y 53.05 to 55.55 (face flush with the cap) |
| AS5600 board envelope | follow the `encoder1021` convention: chip face 1.5 mm from the magnet face, **chip face y 57.05**, chip `ENC1021_CHIP_H` tall, PCB 23 × 23 × 1.6 behind it (y 58.5 to 60.1), centred on the axis |
| Pinion (purchased) | section 2 |
| Motor | `cad/parts/nema17_thermal.py` bodies at front face y −3.175 (or the block motor of `thermal_station1021`) |
| 1/8 in fin | `exports/step/heat_fin1021_1p8_asm1021.step` (as is) |

Lead revision 10/23 after the implementer's stop report: cap thickness and shaft length, window size, board position, tie-off
path, print frame and the separate near spacer (section 3 and 4 tables).

## 5. Deliverables

- `cad/params.py`: new block `WG3_*` (every number above, one definition each; nothing duplicated from other blocks: import
  NEMA17T_*, FIN1021_*, GRIPV7 bearing sizes where they already exist).
- `cad/parts/winch_gear3.py`: builds the printable `spool_gear54` and `magnet_cap_w3`, the reference bodies, and the assembly.
- Exports:
  - `exports/step/winch_gear3_spool_gear54.step` / `exports/stl/winch_gear3_spool_gear54.stl` (print frame: drum axis +z, the gear's near face on the bed, section 3);
  - `exports/step/winch_gear3_magnet_cap.step` / `.stl`, and `exports/step/winch_gear3_spacer_near.step` / `.stl`;
  - `exports/step/winch_gear3_drive_asm1021.step`: every body named (`motor_*`, `fin`, `pinion`, `spool_gear54`, `shaft`,
    `bearing_near`, `bearing_far`, `spacer_near`, `magnet_cap`, `magnet`, `as5600_chip`, `as5600_board`), in the station_1021 frame;
  - `exports/step/winch_gear3_drive_with_slipin_asm1021.step`: the same plus Jasper's current slide-in and wall mount, for him to
    see what has to change.
- Renders `renders/winch_gear3/`: front, side, top, iso of the drive; the mesh close-up; and a section through the spool axis.
- `tests/test_winch_gear3.py`: valid solids, counts, the key dimensions above, centre distance 36.20, ratio 3, no overlap between
  any two drive bodies (≤ 0.01 mm³), gear tip to pinion hub ≥ 1.0 mm (revision B: the Ø14 hub ends at the gear's face plane, so the gap is radial, 36.20 − 28.0 − 7.0 = 1.2 mm; the 0.2 mm end play cannot close it), gear to motor body and to the fin ≥ 1.5 mm, STEP
  round trip (volume and bounding box within 0.1 %).
- `verification/winch_gear3_build_notes.md`: what was built, measured values, and the **interferences with Jasper's current
  slide-in** (expected: the spool and gear cut through the lower lug and deck region; list each with its volume and location).
  These are redesign inputs for Jasper, not failures.

## 6. Do not

- Do not modify Jasper's reference STEP files, the encoder1021 parts, the heat fin parts, or any existing export.
- Do not design the mount, the far cheek or the shell (Jasper does); only report where they must change.
- Do not change software or configs.

## 7. For Jasper's mount (lead, 10/23, after the verification and the calculation check)

*Revision B (18T/54T): seat loads from the rerun `calculations/winch_gear3.md`, interferences from the revision B build notes.*

The drive train passed independent verification (`verification/winch_gear3_verification.md`, 26 tests, 0 failures). Inputs
for the slide-in, far cheek and shell he redesigns (numbers from `calculations/winch_gear3.md`, at 1.0 A):

- **Bearing seats:** Ø14 seats for the two 687s, the near one in the extended motor tab (y 0 to 5), the far one in a cheek
  (y 44 to 49). They must hold **133 N (near) and 161 N (far) radial and 87 N axial** (1.5 x the motor's upper slip force
  case). Fillets on the roots of the tab and the cheek.
- **Axial location:** the stack between the bearing faces is exactly 39.000 mm (spacer 5.825 + spool 33.175), with no float.
  Put a shoulder on the **outboard** face of each bearing (near: the motor side at y 0; far: the encoder side at y 49) and set
  the two shoulders **49.2 mm apart** (0.2 mm end play), or shim to it. The fleeted line pushes the spool either way (58 N), so
  each direction has one shoulder.
- **687 land:** the spacer and the spool's far hub touch the bearing with a Ø9 land, meant for the inner race only. Check the
  687 datasheet's inner-ring shoulder; if it is under Ø9, reprint the lands at Ø8.4 so they clear the shields.
- **Cable exit:** keep the line leaving the drum on the room side (+x), hanging down, through the cable hole under the drum.
  The `drive.step_sign` flip in D40 assumes this exit.
- **Pinion (purchase):** steel M1 18T, Ø5 bore, two set screws (one on the D-flat) or one set screw plus retaining compound on
  the bore; not sintered or brass. Torque-slip test it on the bench.
- **Spool:** keep 3 dead wraps on the drum (the Ø1.4 tie-off is not rated for the full line pull).
- **Interferences with the current parts** (redesign inputs, `verification/winch_gear3_build_notes.md`, confirmed by the
  verifier): slide-in against the spool 2452 mm³ (back plate 1233, deck block 1133, far cheek and deck top 85), against the
  spacer 13 mm³, no longer against the shaft; wall mount against the spool 27 mm³; shell against the spool 730 mm³ and the
  AS5600 board 33 mm³ (revision A: 3953, 55, 35, 697, 1165 mm³).

The export bullet in section 5 ("print frame: drum axis +z, the gear's near face on the bed") was aligned with section 3 by the
implementer in 609aff7; the lead confirms it.
