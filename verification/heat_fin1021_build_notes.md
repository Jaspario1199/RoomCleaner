# Heat fin 1021, thermal station geometry, NEMA 17 thermal model: implementer build notes

Implementer: cad-implementer (Sonnet), 2026-10-22. Status: built, acceptance tests pass (counts in section 7), exports and renders current.
NOT yet independently verified (the `geometry-verifier` report is still to come); the STEP files were read back with OpenCascade only, not opened in SOLIDWORKS.
No thermal analysis was run. Nothing committed by this task.

- Spec: `cad/HEAT_FIN_1021_SPEC.md` (A heat fin, B thermal station, C short-peg cap, D tests) plus two later scope additions from the lead: the fin split at the shell exit,
  and E (a multi-body NEMA 17 + a `detailed` station variant, target SOLIDWORKS Simulation). Magnet Ø4.0 change: see `verification/encoder1021_build_notes.md` (last section).
- Master values: `cad/params.py`, appended blocks `FIN1021_*`, `THERMAL_*`, `NEMA17T_*` (nothing existing changed except `ENC1021_MAGNET_D`, by the lead's instruction).
- Parts: `cad/parts/heat_fin1021.py`, `cad/thermal_station1021.py`, `cad/parts/nema17_thermal.py`; encoder short-peg variant in `cad/parts/encoder1021.py` (`V2_VARIANTS`).
- Regenerate: `/usr/bin/python3 -m cad.parts.heat_fin1021` (10 s), `-m cad.parts.nema17_thermal` (12 s), `-m cad.thermal_station1021` (35 s), `-m cad.parts.encoder1021 m4`.
- Frames: **station_1021** = the reference STEP frame (motor axis x = 0, z = 2.64; +y toward the spool; tab face y = 0; carries the 0.004 mm extraction residual);
  **assembly** = station_1021 + O, O = (1269.08, 738.76, 927.56); **flat part frame** = plate in XY, thickness +Z, origin at the bottom-left corner of the 42 mm edge seen from the
  motor side (X = x + 20, Y = z + 18.36, Z = -y: Z = 0 is the PETG-tab face, Z = t the motor contact face), residual removed.

## 1. A: the fin (`cad/parts/heat_fin1021.py`)

Built by extruding the Heat_horn's y = 0 face (outer wire + 5 inner wires) toward -y by t: production **3.175 mm (1/8 in)**, prototype record **0.483 mm (0.019 in)**.

| item | expected (spec / lead) | measured on the Heat_horn face and the built fin |
|---|---|---|
| bottom edge | 42.0 | 42.000 |
| left / right (long) side edges | 195.6 / 228.6 | 195.600 / 228.600 |
| slanted top edge | 53.4 | 53.413 (= hypot(42, 33)); the spec's 53.4 is this rounded |
| x range / z range (design, residual removed) | -20.0 .. 22.0 / -18.36 .. 210.24 | -20.000 .. 22.000 / -18.360 .. 210.240 (raw file: -19.9958 .. 22.0042 / -18.3561 .. 210.2439) |
| face area | | 8474.275 mm2 (fin face = Heat_horn face: area equal, symmetric difference 0) |
| centre hole | Ø22.5 at the axis (0, 2.64) | Ø22.500 at (0.000, 2.640) |
| 4 holes | Ø3.4 on a 31 mm square | Ø3.400 at (+-15.500, 2.640 +- 15.500); through the whole thickness |
| 1/8 in fin | volume = area x t | 26905.82 mm3 (area x 3.175 to 1e-9), 72.65 g at 2.70 g/cm3, bbox station x 42.0, y -3.1734 .. 0.0016, z 228.6 |
| 0.019 in fin | | 4093.08 mm3, 11.05 g, y -0.4814 .. 0.0016 |
| flat frame bbox (both) | [0, 42] x [0, 228.6] x [0, t] | X [0.0000, 42.0000], Y [0.0000, 228.6000], Z [0.0000, 3.1750] (errors < 2e-6) |
| asm1021 copy vs the original assembly's Heat_horn (volume 16948.55) | coincide on the y = 0 face | face area equal to 1e-9, common area = full face, centres < 1e-6 apart, in assembly coordinates |
| STEP reimport (asm1021 x 2, flat) | equal volume | rel. difference < 1e-6, bbox < 1e-4 |
| STL (flat, 127 684 bytes) | | bbox [0,42] x [0,228.6] x [0,3.175] to 1e-3; mesh volume within 0.2 % of the solid (tessellated holes) |
| DXF | outline + holes | closed 4-vertex polyline + 5 circles + centre marks, mm; outline area - holes = 8474.275 +- 0.05; hole centres = the hole table |

Files: `exports/step/heat_fin1021_1p8_asm1021.step`, `heat_fin1021_0p019_asm1021.step`, `heat_fin1021_1p8.step`, `exports/stl/heat_fin1021_1p8.stl`, `exports/dxf/heat_fin1021_1p8_profile.dxf`,
`renders/heat_fin1021/heat_fin1021_1p8_drawing.png|pdf` (A3 portrait, true 1:1; mm and [inch] dimensions; hole table from datum A = bottom edge and datum B = the 228.6 mm long side,
with the distance from the left edge as an extra column; 6061-T6 (or 5052-H32) 1/8 in; matte black paint except the motor contact square; mass 72.6 g; the 0.019 in prototype noted) and the 7 standard
views + a hole-end detail (`heat_fin1021_1p8_*.png`). Hole table (from B / from the left edge / from A): pilot 22.00 / 20.00 / 21.00; holes 37.50 / 4.50 and 6.50 / 35.50 at 5.50 and 36.50.

Observations (not changed): the motor's 42.3 square face overhangs the fin outline by 1.146 mm on the left (x -21.146 vs -20.0) and 0.150 mm at the bottom, so the paste contact
patch is 1300.5 mm2 of the 1789.3 mm2 motor face (73 %). The hole nearest the left edge has 2.8 mm of material to the edge, 3.8 mm at the bottom.

## 2. B: the thermal station (`cad/thermal_station1021.py`)

Every position is measured on the reference STEPs, not typed (raw station_1021 frame, residual included; `T.measure_slipin()`):

| item | spec | measured |
|---|---|---|
| tab holes | 4 x Ø3.5 at (+-15.5, 2.64 +- 15.5), tab y 0 .. 5 | Ø3.500 at x = 0.0042 +- 15.5, z = 2.6439 +- 15.5; tab y 0.0016 .. 5.0016; pilot Ø22.4 |
| deck insert pocket | Ø4.1 x 7 deep, Ø3.4 x 3 below | Ø4.100, centre (7.854, 15.562), z -49.375 .. -42.375 (7.000 deep, open at the deck top face z -42.375), Ø3.4 below to the deck bottom |
| divot holes | 4 x Ø3.45 x 4 deep along x | Ø3.450, (y, z) = (40.2516 / 49.7516, -2.1061 / 7.3939), x -26.1458 .. -22.1458 (4.000 deep, open at the divot floor) |
| shell fin slot | open y -2.6 .. +2.2 | **-2.690 .. +2.310** (5.000 wide), walls z 27.84 .. 31.16 (differs 0.09 / 0.11 from the spec text) |

Bodies (STEP component names): variants `fin1p8`, `fin0p019`: `motor_block`, `fin_in`, `fin_out`, `slipin_mount`, `screw_1..4`, `insert_deck`, `insert_enc_1..4`;
variant `detailed_fin1p8`: the NEMA 17 bodies of section 4 instead of `motor_block`. Screw order: 1 = (-x, -z), 2 = (+x, -z), 3 = (-x, +z), 4 = (+x, +z); `insert_enc_n` sorted by (y, z).
Modelled as the spec says: `motor_block` = the Motor_Reference block (no shaft) moved by 2.0 - t with 4 x Ø3.0 x 4.0 holes; screw = head Ø5.5 x 3.0 on the tab's spool-side face (y 5 .. 8) +
shank Ø3.0 from y 5 to y = -t - 4.0 filling the motor holes (shared cylinder + end face, no overlap); `insert_deck` brass sleeve OD 4.1 x 5.7 ID 2.5 flush with the deck face (1.3 mm above the
pocket floor); `insert_enc_n` OD 3.45 x 4.0 ID 2.1 flush with the divot floor on the hole bottom. `THERMAL_INSERTS = ("deck", "enc")` selects the candidates (tested: `()`, `("deck",)`,
`("enc",)`, both). Which inserts Jasper means is still not confirmed.

**Fin split (lead's addition).** `fin_in` (below) and `fin_out` (above) the plane z = `THERMAL_FIN_SPLIT_Z` = 34.6 (station_1021 frame). Re-measured from `Shell_Casing.step`: max z of shell material inside the
Heat_horn's x / y footprint widened by 6 mm = **34.593** (parameter 34.6, tolerance 0.05, asserted at build). **Height above the fin's bottom edge: 52.96 mm** (34.6 - (-18.356); 52.95 for the measured top).
The halves touch on the plane over 42 x t = 133.35 mm2 (1/8 in) / 20.29 mm2 (0.019 in); volumes sum to the unsplit fin within 1e-9 mm3 (limit 0.01). Caution: the measured top depends on which footprint is
used. With the 3.175 mm fin's own footprint widened by 6 mm (y -9.175 .. +6) the max z is 36.45, because a taller shell feature lies at y < -6; the Heat_horn (2.0 mm) footprint, which the 34.6 refers to, gives 34.593.

**Overlaps: none.** All three variants: the largest pair overlap is 0.000000 mm3 (limit 0.01); no pair overlaps at all.

Body table, `fin1p8` (volumes measured; masses = volume x the density in `THERMAL_DENSITY_G_CM3` / `NEMA17T_MATERIALS`, vendor-typical, not certified). Same file: `renders/thermal_station1021/thermal_station1021_<variant>_bodies.csv`.

| body | material to assign | k W/m.K | density g/cm3 | volume mm3 | mass g |
|---|---|---|---|---|---|
| motor_block | structural steel (motor proxy, effective density so the block = 0.28 kg) | 50 | 4.118 | 67879.92 | 279.53 |
| fin_in / fin_out | aluminium 6061-T6 (5052-H32 k ~138) | 167 | 2.70 | 5683.99 / 21221.83 | 15.35 / 57.30 |
| slipin_mount | PETG | 0.20 | 1.27 | 217693.15 | 276.47 |
| screw_1..4 (each) | steel (12.9 alloy; A2 would be k ~16) | 50 | 7.85 | 157.34 | 1.235 |
| insert_deck | brass | 115 | 8.5 | 47.28 | 0.402 |
| insert_enc_1..4 (each) | brass | 115 | 8.5 | 23.54 | 0.200 |

`fin0p019`: same, with fin_in / fin_out 864.68 / 3228.39 mm3 (2.34 / 8.72 g) and screws 138.31 mm3 (1.086 g). `detailed_fin1p8`: section 4 for the motor bodies, screws 156.10 mm3 (1.225 g).

**Contact list for the simulation** (face-to-face contact areas, mm2; computed as the area of the coincident faces, checked against the analytic values; distance 0 within 1e-9). `fin1p8` (`fin0p019` is identical
except fin_in - fin_out = 20.29):

| pair | area | what it is |
|---|---|---|
| motor_block - slipin_mount | 1607.40 | the motor's whole -x face (38 x 42.3) on the slip-in's back plate (x = -21.146) |
| motor_block - fin_in | 1300.55 | paste interface (motor front face minus the fin's holes and the part that overhangs the outline) |
| fin_in - slipin_mount | 1298.55 | fin y = 0 face on the PETG tab |
| fin_in - fin_out | 133.35 | split plane (convection zones inside / outside the shell) |
| motor_block - screw_n (each) | 44.77 = 37.70 cyl (Ø3.0 x 4.0) + 7.07 end face | thread / hole contact (full 4.0 mm engagement modelled) |
| slipin_mount - screw_n (each) | 14.14 | head underside annulus on the tab face (Ø5.5 over the Ø3.5 hole) |
| slipin_mount - insert_deck | 73.42 | Ø4.1 x 5.7 cylinder |
| slipin_mount - insert_enc_n (each) | 49.24 = 43.35 cyl + 5.89 end annulus | Ø3.45 x 4.0 + hole bottom |

Not touching (listed as near gaps): fin_in - screw_n, 0.200 mm radial gap (Ø3.4 fin hole vs the Ø3.0 shank); the tab hole gap is 0.25 mm radial (Ø3.5). `fin_out` touches only `fin_in`. The motor (block or detailed) clears
the shell by 1.9 mm and does not touch it; the slip-in touches the shell (the shell is not in the export) without overlapping it.

Section renders: `renders/thermal_station1021/thermal_station1021_<variant>_section_screws.png` (plane through the upper screw row, motor / fin / tab / two screws) and `..._section_deck_insert.png`.
STEP files: `exports/step/thermal_station1021_fin1p8.step`, `thermal_station1021_fin0p019.step`, `thermal_station1021_detailed_fin1p8.step`; each reads back (OpenCascade XCAF) with every
component named as listed, one solid each, volumes equal to the build (rel 1e-6), bboxes = station + O.

## 3. Findings (shell slot, screw length, others)

1. **Shell fin slot.** The 1/8 in fin (y -3.175 .. 0) overlaps the slot's motor-side wall (y -2.690) by **68.94 mm3** over y -3.175 .. -2.690 (the spec's "about 69"). The 0.019 in fin (y -0.483 .. 0) clears it
   (0 mm3). The shell's slot must open to **y <= -3.675** on the motor side (fin face -3.175 - `THERMAL_SLOT_CLEAR` 0.5; "about -3.7"): move that wall by 0.985 mm; the spool-side wall (+2.310) is fine.
   The measured slot is 5.000 wide (walls -2.690 / +2.310), not -2.6 / +2.2 as in the spec text. The shell was not edited; Jasper owns it.
2. **Screw length.** Engagement = screw length - 5.0 tab - t (modelled motor hole: 4.0, spec; "about 4.5" real: depth gauge to be checked). 1/8 in with M3 x 12: **3.825 mm** (in 3.0 .. 4.5). 0.019 in with M3 x 8:
   2.517 mm (below the 3.0 target); with M3 x 10: **4.517 mm, which is longer than the 4.0 mm hole of this model** (and at the 4.5 limit of the real hole): it would bottom out if the real hole is 4.0 deep.
   The simulation screws for `fin0p019` fill the hole to 4.0 mm as the spec says, which overstates the thread contact of an M3 x 8 (2.5 mm) by 59 %.
3. **Motor / spool shift.** Motor shift 2.0 - t: -1.175 (1/8 in, shaft end 20.825, 13.8 mm in the spool bore) and +1.517 (0.019 in, shaft end 23.517). Both measured on the built bodies.
4. **Motor face overhang** and **contact patch** (section 1).
5. **Spec deviations / assumptions:** shank in the real tapped hole is plain Ø3.0 (no thread); the M3 x 12 detailed screw is 12.0 under the head (engagement 3.825, the spec's "3.8"); material numbers are
   typical values; the motor-block steel proxy k = 50 and density 4.118 are my assumptions (block weighs the 0.28 kg of `simulation_loads.py`).

## 4. E: NEMA 17 for thermal simulation (`cad/parts/nema17_thermal.py`, `NEMA17T_*`)

Motor frame: front face y = 0, axis +y, body y -38 .. 0, boss and shaft toward +y. 42.3 square, 38 long, 3 mm x 45 deg chamfers on the four long edges (chamfer faces measured 3 x sqrt(2) x length each).
No rotor: the cavity inside the winding is air. Files: `exports/step/nema17_thermal.step` (motor frame), `nema17_thermal_fin1p8_asm1021.step` (front face at y = -3.175, assembly coordinates, 1/8 in fin),
`nema17_thermal_fin0p019_asm1021.step` (front face at y = -0.483); body table `renders/thermal_station1021/nema17_thermal_bodies.csv`; renders `nema17_thermal_front_iso|rear_iso|section_z0.png`.

| body | y range | geometry (measured) | suggested material | k W/m.K | density | volume mm3 | mass g | exposed surface |
|---|---|---|---|---|---|---|---|---|
| front_cap | -8 .. 0, boss to +2 | Ø22 x 2 boss, 4 x Ø3.0 x 4.5 at +-15.5, Ø5.0 bore through | aluminium die-cast (A380) | 96 | 2.74 | 14607.00 | 40.02 | aluminium end cap |
| stator | -30 .. -8 | bore Ø34 | silicon-steel laminations (k in-plane; axial 1 - 2) | 25 | 7.65 | 18994.13 | 145.31 | black painted steel |
| winding | -30 .. -8 | annulus Ø23 .. Ø34 x 22 inside the stator bore (heat source) | copper + insulation, homogenised (effective k 0.5 .. 2) | 1.0 | 5.0 | 10833.78 | 54.17 | internal |
| rear_cap | -38 .. -30 | blind Ø5.0 shaft seat, 7 deep | aluminium die-cast (A380) | 96 | 2.74 | 14032.88 | 38.45 | aluminium end cap |
| shaft | -37 .. 24 | Ø5.0, 61 long (24 proud of the front face), no D-flat | carbon steel | 50 | 7.85 | 1197.73 | 9.40 | bare steel shaft |
| connector | -38 .. -32, x 21.15 .. 27.15, z +-8 | PBT housing 16 x 6 x 6, flush with the back face, on the rear cap's +x face | PBT | 0.25 | 1.40 | 576.00 | 0.81 | plastic connector |

Total 288.15 g against the 0.28 kg of the reference motor (+2.9 %). No pair of bodies overlaps (largest 0.000000 mm3). Deviations from the brief (both as the lead allowed):
(a) the Ø5.2 caps' bores are built Ø5.0 so the shaft surface is coincident with the bores (contact: front cap 157.08 mm2 = Ø5 x 10 mm incl. the boss, rear cap 129.59 = Ø5 x 7 + the end face);
(b) "shaft from 1 mm inside the rear cap's back face" is built as a blind seat whose bottom is the shaft's back end face (a through bore would leave a 1 mm Ø5 hole behind the shaft end).
Motor-internal contacts: stator - winding 2349.91 (Ø34 x 22), winding - front cap / rear cap 492.45 each, front cap - stator and stator - rear cap 863.37 each, rear cap - connector 96.00.
Air around the shaft inside the stator: shaft - winding distance 9.0 mm. The material numbers of the stator (axial conductivity) and winding (effective k) are the least certain and decide the heat path: assumptions to confirm.

**`detailed_fin1p8` station.** Replaces `motor_block` by the six bodies (placed with the axis on the centre of the 4 measured tab holes and the front face on the fin's motor face, so the shared faces
coincide to 1e-9); fin split, slip-in, inserts as in B; screws M3 x 12: head on the tab face, shank Ø3.0 through the tab and fin, **3.825 mm into the front cap's Ø3.0 x 4.5 holes** (contact 36.05 mm2 each, a
0.675 mm air gap under the screw tip). Overlaps: none. Contact list (mm2): stator - winding 2349.91; fin_in - slipin 1298.55; front_cap - fin_in 1288.83; front_cap - stator 863.37; stator - rear_cap 863.37;
stator - slipin 798.60; front_cap - winding 492.45; winding - rear_cap 492.45; front_cap - slipin 290.40; rear_cap - slipin 290.40 (the chamfers cut the side contact to 36.3 x length: 1379.4 total vs 1607.4 for the
block); front_cap - shaft 157.08; fin_in - fin_out 133.35; rear_cap - shaft 129.59; rear_cap - connector 96.00; inserts and screw heads as in B. The motor clears the shell by 1.9 mm (connector and rear cap).

## 5. C: the short-peg cap

`ENC1021_CAP_PEG_LEN` = 1.9 through `params_override` (`FIN1021_PROTO_CAP_PEG_LEN`), everything else v2, **built for the measured Ø4.0 magnet** (lead's priority message): `exports/step|stl/encoder1021_magnet_cap_v2_m4_peg1p9.*`
(and `_asm1021.step`); no Ø6 `peg1p9` file was ever exported, so none is superseded. Peg end **y 24.1** (probed 24.10); clearance to a Ø5 shaft ending at 23.517: **0.583 mm** (>= 0.5); to the Motor_Reference
shaft moved by +1.517: >= 0.5. The standard cap (peg end 22.6) penetrates that shaft by 0.917 mm (about 18 mm3 of shaft) and clears the 1/8 in fin's shaft (end 20.825) by 1.775 mm.
Retention note: the crush ribs engage 1.5 mm less (spool contact volume 0.234 vs 0.477 mm3), so expect about half the press-fit hold: a drop of CA on the peg is an option.

## 6. Open items / risks

- Independent geometry verification of all of the above is still to be done (this report is the implementer's own).
- Jasper to confirm which inserts exist (deck, divot, or neither); the deck and divot pockets were found in the slip-in, nothing confirms they are used.
- Real motor tapped-hole depth (4.0 vs 4.5) decides whether M3 x 10 is allowed with the 0.019 in fin.
- Shell slot to open to y <= -3.675 for the 1/8 in fin (Jasper's SOLIDWORKS shell).
- SOLIDWORKS import of the named multi-body STEPs not tested (only the OpenCascade read-back); the paste interface needs a thermal contact resistance in the study; bonded contact elsewhere.
- Material properties are typical values; stator axial k and winding effective k are the largest uncertainties.

## 7. Tests (all run with `/usr/bin/python3 -m pytest`)

SEE_RESULTS_BELOW
