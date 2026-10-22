# 1/8 in heat fin for the 10/21 station, and the thermal simulation geometry (spec, lead, 2026-10-22)

**Request (Jasper, 10/22):** "make the CAD for a 1/8 in fin and then note that only prototype is using .019 in. For now as I
already had extra material. My goal with the ansys sim is to also simulate the screws and see the heat distribution change to
the heatset inserts."

**Why 1/8 in:** `calculations/fin_sizing_4w.md`. At 1.5 A (D37) the motor makes 4.05 W.
- The 0.019 in sheet cannot carry that alone at any length (about 2 W at most).
- A painted 1/8 in plate at the same size carries all of it at 56 to 59 °C, and about 45 °C with the vented shell.

**Reference geometry:** `cad/reference/station_1021/*.step`, extracted from Jasper's `Assem_laundry_v3_step_1021.STEP` into the
station_1021 frame:
- frame: motor axis at x = 0, z = +2.64; +y along the shaft toward the spool; +x out of the wall; +z up;
- assembly coordinates = station_1021 + O, with O = (1269.08, 738.76, 927.56) from `cad/reference/station_1021/extract.py`.

## 1. Measured from the reference (lead, 10/22; re-check in code)

**Heat_horn** (Jasper's CAD fin):
- 2.0 mm thick, y −2.0 to 0.0;
- outline: 42.0 mm bottom edge, 228.6 mm and 195.6 mm side edges, a 53.4 mm slanted top edge (a tapered horn);
- x −20.0 to 22.0, z −18.36 to 210.24;
- centre hole Ø22.5 on the motor axis (x 0, z 2.64);
- 4 × Ø3.4 on a 31 mm square about the axis.

**Motor_Reference:** a 42.3 mm block at y −40 to −2; the Ø5 shaft runs to y 22.0.

**Slipin_mount_piecev3:**
- motor tab y 0 to 5 (PETG, 5 mm);
- 4 × Ø3.5 clearance holes for the motor screws at (±15.5, z 2.64 ± 15.5) through the tab; pilot Ø22.4.
- **Insert-size pockets found:**
  - Ø4.1 × 7 deep (with Ø3.4 × 3 below it) at about (7.85, 15.55), z −49.4 to −42.4, in the deck under the spool;
  - 4 × Ø3.45 × 4 deep along x (x −26.1 to −22.1) at y 40.25 / 49.75, z 2.64 ± 4.75: the encoder divot holes.
- Which inserts Jasper means is **not confirmed**. Model these as candidates, each one optional by a parameter.

**Shell_Casing:** the fin slot at the shell top (z about 30) is open from **y −2.6 to +2.2**.

## 2. Consequences of a thicker fin (the stack: motor | fin | PETG tab, with the tab face fixed at y = 0)

**Motor position.** The motor moves to y = −t (its front face). Relative to the CAD (2.0 mm) it shifts by 2.0 − t:

| Fin | Motor shift | Shaft end | Engagement in the spool bore (y 7 to 26) |
|---|---|---|---|
| 1/8 in | −1.175 mm | y 20.83 | 13.8 mm |
| 0.019 in prototype | +1.517 mm | **y 23.52** | 15 mm or more |

**Shell slot.** The 1/8 in fin, at y −3.175 to 0, overlaps the slot wall at y −2.6 by about 0.6 mm (69 mm³). The shell's fin slot
must open to about y −3.7 on the motor side. Jasper owns the shell in SOLIDWORKS: report the change; do not edit the shell.

**Encoder magnet cap (v2).** Its peg occupies y 22.6 to 26.0 (ENC1021_CAP_PEG_LEN 3.4, sized for the CAD's shaft end at 22.0).
- With the **0.019 in prototype fin** the shaft end is at 23.52, so the peg hits the shaft by 0.92 mm.
- Prototype stations need a **short-peg cap**: peg 1.9 mm, ending at y 24.1, 0.58 mm clear of the shaft.
- The 1/8 in fin leaves 1.77 mm, so the standard cap fits.

**Motor screws:** M3, from the spool side through the 5 mm tab and the fin into the motor's tapped holes (about 4.5 mm deep).
Keep 3.0 to 4.5 mm of thread engagement:

| Fin | Screw | Engagement |
|---|---|---|
| 1/8 in | **M3 × 12** | 3.8 mm |
| 0.019 in | M3 × 8 | 2.5 mm |
| 0.019 in | M3 × 10 | 4.5 mm (at the limit; check the motor's hole depth) |

## 3. Deliverables

**A. `cad/parts/heat_fin1021.py`** (new file; do not edit `cad/parts/motor_heat_plate.py`, which is the 10/18 design and is kept).
- Fin = the Heat_horn's y = 0 face extruded toward −y by t:
  - production **t = 3.175 mm (1/8 in)**;
  - prototype record **t = 0.483 mm (0.019 in)**.
- Parameters in `cad/params.py` under a `FIN1021_*` block: thickness options, alloy note, the reference source, the measured
  outline numbers.
- Exports:
  - `exports/step/heat_fin1021_1p8_asm1021.step` and `heat_fin1021_0p019_asm1021.step`, in assembly coordinates, so they drop
    into Jasper's assembly at the origin;
  - `exports/step/heat_fin1021_1p8.step` and `exports/stl/heat_fin1021_1p8.stl` in a **flat part frame**: plate in XY, thickness
    +Z, origin at the bottom-left corner of the 42 mm edge;
  - `exports/dxf/heat_fin1021_1p8_profile.dxf`, the 2D outline with holes, for cutting and drilling;
  - a dimensioned shop drawing `renders/heat_fin1021/heat_fin1021_1p8_drawing.png` and `.pdf`, with:
    - the outline dimensions in mm and inches;
    - a hole table measured from the bottom and long-side edges (the mill setup datums);
    - thickness, material "6061-T6 (or 5052-H32) 1/8 in", finish "matte black paint except the motor contact square";
    - mass.
- Standard renders in `renders/heat_fin1021/`.

**B. `cad/thermal_station1021.py`**: simulation-ready geometry for ANSYS (and SOLIDWORKS). One STEP per fin variant, in assembly
coordinates, every solid named:

| Body | Construction |
|---|---|
| `motor_block` | Motor_Reference block only (drop the shaft), shifted by 2.0 − t, with **4 × Ø3.0 holes, 4.0 mm deep** into its front face at the screw positions |
| `fin` | from A, thickness t |
| `slipin_mount` | the reference part, unchanged |
| `screw_1` to `screw_4` | M3 socket head, simplified: head Ø5.5 × 3.0 seated on the tab's spool-side face (y 5 to 8); shank Ø3.0 from y 5 to y −t − 4.0, filling the motor holes exactly (shared cylindrical face, no overlap). The shank passes through the Ø3.4 fin hole and the Ø3.5 tab hole with a radial gap (no contact) |
| `insert_deck` | brass sleeve OD 4.1 × 5.7 long, ID 2.5, flush with the deck face it is pressed from (re-measure the pocket) |
| `insert_enc_1` to `insert_enc_4` | brass sleeves OD 3.45 × 4.0, ID 2.1, in the divot holes (M2.5) |

- Parameters select which inserts exist: `THERMAL_INSERTS = ("deck", "enc")` by default.
- No pair of bodies may overlap by more than 0.01 mm³.
- Report the touching pairs and their contact areas (the contact list for the simulation).
- Exports:
  - `exports/step/thermal_station1021_fin1p8.step` and `thermal_station1021_fin0p019.step`;
  - a body table: name, material to assign, volume, mass;
  - a section render through a screw.

**C. Encoder short-peg cap for the prototype fin.** In `cad/parts/encoder1021.py` add a v2 variant with ENC1021_CAP_PEG_LEN = 1.9
(everything else v2). Export `exports/step|stl/encoder1021_magnet_cap_v2_peg1p9.*` in the same print orientation as the v2 cap.
Leave the nominal and existing variant exports untouched.

**D. Tests:**
- `tests/test_heat_fin1021.py`: outline and holes equal to the reference; thicknesses; flat-frame bounding box; the
  assembly-coordinate copy coincides with the Heat_horn on the y = 0 face; volume equals area × t.
- `tests/test_thermal_station1021.py`: body names; the overlap limits; the screw heads on the tab face; the shanks in the motor
  holes; the insert sleeves in their pockets; motor shift per variant.
- A test for the peg1p9 variant: peg end y 24.1 ± 0.01; clearance to a Ø5 shaft ending at y 23.517 is at least 0.5 mm.

## 4. Out of scope

- Do not edit the shell, the slip-in, or Jasper's SOLIDWORKS parts.
- Do not change the v2 cap defaults or any existing export.
- Do not run any thermal analysis.
