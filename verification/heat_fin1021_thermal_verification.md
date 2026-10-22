# Independent geometry verification: heat fin 1021, thermal station, detailed NEMA 17, Ø4 magnet caps

Verifier: geometry-verifier (Sonnet), 2026-10-22. Scope: the files built by the implementer under `cad/HEAT_FIN_1021_SPEC.md` (A fin, B thermal station, C short-peg cap, D tests) and the lead's late changes (detailed NEMA 17; fin split `fin_in` / `fin_out` at z 31.16; Ø4.0 magnet caps).
Nothing under `cad/`, `exports/`, `docs/` or any part file was modified, and no exporter was run. Files added by the verifier: `verification/heat_fin1021_thermal_verify.py` (the measuring harness), `verification/heat_fin1021_thermal_results.json` (all 319 rows), `tests/test_heat_fin1021_thermal_verification.py` (pytest wrapper).

## Verdict

**PASS on every item (1 to 5). 0 failures, 319 checks (303 PASS, 10 NOTE observations that are not requirements, 6 negative controls that must fire and do).** Details of the observations are in section 7. No part needs to go back to the implementer; two interface findings (shell slot, screw engagement modelling) are the lead's to decide.

| Item | Result | Checks |
|---|---|---|
| 1 Fin (outline, holes, thickness, flat bbox, assembly coincidence, volume, STL, DXF) | PASS | 41 (1 NOTE) |
| 2 Thermal STEPs (13 / 13 / 18 named solids, overlaps, motor shift, screws, inserts, split, engagement, contact list) | PASS | 141 (2 NOTE) |
| 3 Detailed NEMA 17 | PASS | 29 |
| 4 Ø4 caps (pocket, peg ends, shaft clearance, spool-only contact, STL) | PASS | 39 |
| 5 Every STEP (valid BREP, reimport, solid count) | PASS | 63 (7 NOTE, cosmetic) |
| Negative controls (the detectors do fire on broken input) | PASS | 6 |

## Method (how the numbers were obtained)

- All values are measured from the files on disk with OpenCascade (CadQuery 2.8 / OCP): cylinder axes and radii from the B-rep faces, volumes and contact areas from booleans, distances from `BRepExtrema`, STL / DXF parsed directly (binary STL by `struct`, DXF by `ezdxf`).
  The builders' own measurement helpers (`measure_slipin`, `contact_area`, ...) were not used for any pass or fail decision. The builder functions were called only for the "file is current" currency checks (3.13, 4.9), which write nothing.
- Only two constants are taken from `cad/params.py`: the extraction residual and the 2.64 axis shift (both also verifiable from the reference files). Expected values come from the spec, from Jasper's reference STEPs (`cad/reference/station_1021/*.step`, and the original `solidworks/v4_assembly_2026-10-21/Assem_laundry_v3_step_1021.STEP` for the fin face and for the cap contact test), and from first-principles formulas.
- Frames: station_1021 = reference frame; assembly = station + O, O = (1269.08, 738.76, 927.56) (from `extract.py`). The reference files carry the common extraction residual (0.004243, 0.001645, 0.003854); "design" values below have it removed. Tab face = design y 0.
- Overlap was checked two ways (boolean common volume, and V_a + V_b - V(fuse)) over every bbox-near pair, so a failure of one boolean cannot hide an overlap. Negative controls (9.1 to 9.5) confirm that a 0.1 mm penetration, a 0.15 mm shank offset, the standard cap on the 23.517 shaft, and a real face contact are all detected.
- Reproduce: `PYTHONPATH=. /usr/bin/python3 verification/heat_fin1021_thermal_verify.py` (about 2 minutes, prints every row, writes the JSON) or `PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_heat_fin1021_thermal_verification.py` (6 grouped tests).
- Also run: the builder's `test_heat_fin1021.py`, `test_thermal_station1021.py`, `test_nema17_thermal.py`, `test_encoder1021_m4.py`, `test_encoder1021_peg1p9.py` together with the wrapper: **130 passed** in 258 s (they read the exports and write only to `tmp_path`).

## 1. Fin (`heat_fin1021_1p8.step`, `_1p8_asm1021.step`, `_0p019_asm1021.step`, `heat_fin1021_1p8.stl`, `heat_fin1021_1p8_profile.dxf`)

| # | Check | Expected | Measured | Tol | Result |
|---|---|---|---|---|---|
| 1.0 | Heat_horn y = 0 face (reference): bottom / left / right / slanted edges | 42.0 / 195.6 / 228.6 / 53.4 | 42.000 / 195.600 / 228.600 / 53.413 (= hypot(42, 33)) | 0.02 | PASS |
| 1.0 | Heat_horn outline x, z range (design frame) | -20.0 .. 22.0, -18.36 .. 210.24 | exactly | 0.005 | PASS |
| 1.1 | each fin file | 1 valid solid | 1 solid, valid, 1 shell | - | PASS |
| 1.2 | thickness 1/8 in (asm and flat) / 0.019 in (asm) | 3.175 / 0.483 | 3.175000 / 0.483000 | 0.001 | PASS |
| 1.3 | flat bbox | 42 x 228.6 x 3.175 | 42.0000 x 228.6000 x 3.1750 | 0.001 | PASS |
| 1.3 | flat origin = bottom-left of the 42 mm edge | (0, 0, 0) | (-0.0, -0.0, -0.0) | 0.001 | PASS |
| 1.3 | flat orientation (long 228.6 side on the X = 42 side; material at (41, 220) and (1, 190), none at (1, 220)) | T / F / T | T / F / T | - | PASS |
| 1.4 | flat holes: Ø22.5 at (20, 21); 4 x Ø3.4 at (4.5 / 35.5, 5.5 / 36.5); all through 0 .. 3.175 | as stated | Ø22.500 (20.000, 21.000); Ø3.400 at (4.500, 5.500), (4.500, 36.500), (35.500, 5.500), (35.500, 36.500); through | 0.01 | PASS |
| 1.4 | every reference Heat_horn hole has a matching hole in the fin (Ø, centre) | 5 / 5 | 5 / 5 | 0.01 | PASS |
| 1.4 | asm copies (1/8 in and 0.019 in): Ø22.5 on x 0, z 2.64; Ø3.4 at x +-15.5, z 2.64 +- 15.5 | as stated | Ø22.500 (-0.000, 2.640); Ø3.400 at (+-15.500, -12.860 / 18.140) | 0.01 | PASS |
| 1.5 | asm y = 0 face plane vs the original assembly's Heat_horn y = 0 face (both thicknesses) | y 738.76165 | 738.76165 (identical to 1e-9) | 1e-4 | PASS |
| 1.5 | common area of the two y = 0 faces; area of the symmetric difference | 8474.275; 0 | 8474.275; 0.000 | 0.05 | PASS |
| 1.6 | volume = reference face area x t: flat 1/8 in, asm 1/8 in, asm 0.019 in | 26905.824 / 26905.824 / 4093.075 | 26905.824 / 26905.824 / 4093.075 | 0.01 | PASS |
| 1.7 | STL bbox vs flat STEP | 0 | 6e-6 | 0.002 | PASS |
| 1.7 | STL mesh volume / area vs STEP (relative) | 0 | 2.1e-5 / 1.7e-5 | 3e-3 | PASS |
| 1.7 | STL closed manifold; normals agree with winding; 250 sampled vertices on the STEP surface | 0 open edges; True; 0 | 0; True; 1.0e-5 mm | 0.002 | PASS |
| 1.8 | DXF units mm ($INSUNITS 4); 1 closed outline + 5 circles | yes | yes (plus 10 centre-mark lines) | - | PASS |
| 1.8 | DXF outline vertices | (0,0) (42,0) (42,228.6) (0,195.6) | exactly | 0.005 | PASS |
| 1.8 | DXF circles (Ø, X, Y) = flat STEP holes | 5 | 5 identical | 0.005 | PASS |
| 1.8 | DXF net area (outline - holes) | 8474.275 | 8474.275 | 0.05 | PASS |

## 2. Thermal STEPs (`thermal_station1021_fin1p8`, `_fin0p019`, `_detailed_fin1p8`)

| # | Check | Expected | Measured | Result |
|---|---|---|---|---|
| 2.1 | solid names and count, no duplicates, every component one valid solid | fin1p8 / fin0p019: `motor_block, fin_in, fin_out, slipin_mount, screw_1..4, insert_deck, insert_enc_1..4` (13). detailed: `front_cap, stator, winding, rear_cap, shaft, connector` instead of `motor_block` (18) | identical lists, 13 / 13 / 18 solids, all valid | PASS |
| 2.2 | max pairwise overlap (limit 0.01 mm3), 78 / 78 / 153 pairs, boolean common | 0 | 0.000000 (all three) | PASS |
| 2.2b | same, by fuse-volume bookkeeping | 0 | 2e-4 at most | PASS |
| 2.3 | `slipin_mount` unchanged vs reference (symmetric difference) | 0 | 1.5e-5 mm3 | PASS |
| 2.4 | fin_in + fin_out volume = whole fin; union = whole fin | 26905.824 / 4093.075 | equal to 1e-9; symmetric difference 0 | PASS |
| 2.4 | split plane z (station frame) | 31.16 +- 0.05 | 31.1600 (shell roof at the slot measured on `Shell_Casing.step`: walls y -2.688 / +2.312, top z 31.1558 file = 31.152 design) | PASS |
| 2.4 | split contact area = 42 x t | 133.35 / 20.286 | 133.350 / 20.286 | PASS |
| 2.4 | fin_in holds all 5 holes; fin_out none | 5 / 0 | 5 / 0 | PASS |
| 2.5 | motor shift along y vs Motor_Reference block (2.0 - t) | -1.175 (1/8 in), +1.517 (0.019 in) | -1.175000, +1.517000; x, z extents unchanged | PASS |
| 2.5 | motor front face = fin motor-side face (design y -t) | -3.175 / -0.483 | -3.175 / -0.483 (detailed: front cap face, same) | PASS |
| 2.5 | motor_block = shifted reference block minus 4 holes | 113.097 / 0.000 mm3 | 113.097 / 0.000 | PASS |
| 2.5 | motor holes | 4 x Ø3.0 x 4.0 on the 31 mm square | Ø3.000, (+-15.500, +-15.500), depth 4.000, open at the front face | PASS |
| 2.6 | screw positions and order | 1(-x,-z) 2(+x,-z) 3(-x,+z) 4(+x,+z) at +-15.5 | as stated, head and shank coaxial to 1e-6 | PASS |
| 2.6 | screw head: Ø5.5, y 5.0 .. 8.0, underside = tab spool-side face | 5.0 / 8.0 | 5.000 / 8.000; tab face from the Ø3.5 tab holes 5.0016 (= head underside to 1e-4) | PASS |
| 2.6 | shank tip y (design) | block: -t - 4.0 (-7.175 / -4.483); detailed -7.0 | -7.175 / -4.483 / -7.000 | PASS |
| 2.8 | shank in the motor holes: overlap; contact area | 0; 44.768 (Ø3 x 4 + end face) | 0.000; 44.768 (detailed 36.050 = Ø3 x 3.825) | PASS |
| 2.8 | shank to fin hole (Ø3.4) / tab hole (Ø3.5) radial gap | 0.200 / 0.250 | 0.2000 / 0.2500 (all 4 screws, 3 stations); screw-to-fin distance 0.2000, no contact | PASS |
| 2.8 | screw overlap with fin_in, fin_out, slipin | 0 | 0.000 | PASS |
| 2.9 | insert_deck OD / ID / length; coaxial with the Ø4.1 slip-in pocket; top flush with the deck face; bottom 1.3 above pocket floor | 4.1 / 2.5 / 5.7; 0; flush; 1.3 | 4.100 / 2.500 / 5.700; 0.0000; flush (z top 885.185, air above, material beside); 1.3000 | PASS |
| 2.9 | insert_deck contact with slip-in | pi x 4.1 x 5.7 = 73.419 | 73.419; overlap 0 | PASS |
| 2.9 | insert_enc_1..4 | OD 3.45, ID 2.1, length 4.0, in the 4 Ø3.45 divot holes, flush with the divot floor | exactly; (y, z) = (40.25, -4.75), (40.25, +4.75), (49.75, -4.75), (49.75, +4.75) from the axis; open end at the divot floor confirmed by probe; overlap 0 | PASS |
| 2.7 | engagement behind the fin, M3 x 12 on the 1/8 in fin | 12 - 5 - 3.175 = 3.825 | detailed variant: shank tip y -7.000, engagement 3.825, under-head length 12.000; contact with the front cap 36.05 mm2; tapped holes 4.5 deep (0.675 air under the tip) | PASS |
| 2.12 | touching pairs and contact areas vs the builder's contact CSV | same pairs, areas within 0.01 | 17 / 17 / 27 pairs identical; worst area difference 0.0004 mm2; near-gap list (fin_in to screws, 0.2) true | PASS |
| 2.13 | body table volumes and masses | table = measured | volumes to 5e-4 mm3, masses to 4.5e-3 g | PASS |

Interface cross-checks (not requirements, run for the lead): 1/8 in fin vs `Shell_Casing.step` overlap **68.943 mm3** (the builder's F1, reproduced independently; the motor-side slot wall at y -2.688 must open to y <= -3.675); 0.019 in fin: 0.000. Motor bodies clear the shell by 1.915 mm (1/8 in, detailed) and 4.044 mm (0.019 in); slip-in, inserts, screws and motor bodies do not overlap the shell.

## 3. Detailed NEMA 17 (`nema17_thermal.step`, `nema17_thermal_fin1p8_asm1021.step`, `nema17_thermal_fin0p019_asm1021.step`)

| # | Check | Expected | Measured | Result |
|---|---|---|---|---|
| 3.1 | parts | front_cap, stator, winding, rear_cap, shaft, connector | identical, 6 x (1 solid, 1 shell, valid) | PASS |
| 3.2 | body square (front cap, stator, rear cap) | 42.3 | 42.300 each | PASS |
| 3.2 | length: rear back face y -38, front face y 0, boss end +2; 3 mm x 45 deg chamfers on the 4 long edges | as stated | -38.000 / 0 (one planar face at y 0) / +2.000; chamfer faces 4 x 93.338 mm2 (= 3 sqrt2 x 22), corners probed | PASS |
| 3.3 | tapped holes | 4 x Ø3.0 x 4.5 on the 31 mm square | Ø3.000, (+-15.500, +-15.500), y -4.5 .. 0 | PASS |
| 3.4 | pilot boss | Ø22, y 0 .. 2 | Ø22.000, y 0.000 .. 2.000, on the axis | PASS |
| 3.5 | shaft | Ø5, y -37 .. 24 | Ø5.000, -37.000 .. 24.000 | PASS |
| 3.6 | bores | front cap Ø5.0 through; rear cap blind Ø5.0 seat y -37 .. -30 | exactly | PASS |
| 3.7 | connector | 16 x 6 x 6, x 21.15 .. 27.15, y -38 .. -32 | exactly | PASS |
| 3.8 | stator bore Ø34; winding Ø23 .. Ø34 x 22 | as stated | exactly (y -30 .. -8) | PASS |
| 3.9 | max pairwise overlap (15 pairs, includes both shaft-to-cap pairs) | 0 (limit 0.01) | 0.000000. The shaft touches the caps only on their shared surfaces: front cap 157.08 mm2, rear cap 129.59 mm2 | PASS |
| 3.9 | touching pairs (mm2) | list | stator-winding 2349.91, front/rear cap-stator 863.37, front/rear cap-winding 492.44, front cap-shaft 157.08, rear cap-shaft 129.59, rear cap-connector 96.00; shaft to winding 9.000 apart | PASS |
| 3.10 | total mass with the table densities | 288.15 g | 288.16 g (0.28 kg reference motor, +2.9 %) | PASS |
| 3.11 | placement, 1/8 in stack: front face y = -t, axis x 0 / z 2.64, shaft end | -3.175; 20.825 | -3.175; 20.825 (0.019 in file: -0.483; 23.517); six bodies equal to the `detailed_fin1p8` station bodies to 1e-5 | PASS |
| 3.12 | boss in the fin Ø22.5 / tab Ø22.4 pilot holes: overlap with fin and slip-in | 0 | 0.000 / 0.000 for both fin thicknesses (0.019 in: boss ends 1.517 mm into the tab pilot hole, 0.2 mm radial gap) | PASS |

## 4. Ø4 caps (`encoder1021_magnet_cap_v2_m4[_peg1p9][_asm1021].step`, STL)

| # | Check | Expected | Measured | Result |
|---|---|---|---|---|
| 4.1 | each cap | 1 valid solid | 1 solid, 1 shell, valid; volume 531.941 / 502.312 mm3 (notes 531.94 / 502.31) | PASS |
| 4.4 | magnet pocket | Ø4.3 on the shaft axis, y 26.75 .. 29.3 | Ø4.300 at (0.000, 0.000), floor 26.750, rim 29.300; probes at 0 / 30 / 90 / 270 deg: air at r 2.1, wall at r 2.2 | PASS |
| 4.4 | Ø4.0 x 2.5 magnet (y 26.8 .. 29.3) vs cap | crush ribs only | 0.403 mm3 | PASS |
| 4.3 | peg end y: standard / peg1p9 | 22.6 / 24.1 +- 0.01 | 22.600 / 24.100 (asm copies 22.600 / 24.100 from the tab face) | PASS |
| 4.6 | peg1p9 to a Ø5 shaft ending at y 23.517 (ideal cylinder) | >= 0.5 | **0.5830**, overlap 0; also 0.583 to the `nema17_thermal_fin0p019_asm1021` shaft (end 23.517) | PASS |
| 4.6 | standard cap to the 1/8 in shaft (end 20.825) | 1.775 | 1.775 | PASS |
| 4.6 | standard cap on the 23.517 shaft (why the short peg exists) | collision | 16.81 mm3 | PASS |
| 4.5 | `_asm1021` = station file + (O + residual + (0, 0, 2.64)) | exact | bbox deviation 0.00000, volume equal | PASS |
| 4.7 | `_asm1021` copies in Jasper's assembly STEP | touch only the spool (ribs): 0.477 / 0.234 mm3 | only Spool1011: 0.4766 / 0.2343 mm3; nearest other solid (the shaft, original 22.0 end) 0.600 / 2.100 mm | PASS |
| 4.8 | STL: bbox 14 x 14 x 6.7 / 5.2, magnet face on the bed (z 0), peg up, pocket rim on z 0; volume vs STEP; closed | as stated | 14.0 x 14.0 x 6.7 / 5.2, z min 0; 3.7e-4 relative; 0 open edges; same print pose as the v2 STL | PASS |
| 4.9 | files current with the builder (volume difference) | 0 | 1e-7 mm3 | PASS |

The Ø6 files (`encoder1021_magnet_cap_v2.step`, pocket r 3.150) remain beside the `_m4` files and are unchanged since commit e99d6de. Use only the `_m4` files for the Ø4.0 magnet.

## 5. All STEP files (13 files)

Each of `heat_fin1021_1p8`, `_1p8_asm1021`, `_0p019_asm1021`, `thermal_station1021_fin1p8`, `_fin0p019`, `_detailed_fin1p8`, `nema17_thermal`, `nema17_thermal_fin1p8_asm1021`, `nema17_thermal_fin0p019_asm1021`, `encoder1021_magnet_cap_v2_m4`, `_m4_asm1021`, `_m4_peg1p9`, `_m4_peg1p9_asm1021`:

| Check | Expected | Measured | Result |
|---|---|---|---|
| unit | millimetre | `SI_UNIT(.MILLI.,.METRE.)` in all 13 | PASS |
| valid BREP, solid count, one shell per solid | 1 / 1 / 1 / 13 / 13 / 18 / 6 / 6 / 6 / 1 / 1 / 1 / 1 solids | identical, all valid, no stray or disconnected bodies | PASS |
| re-export, reimport: volume and bbox | dV/V <= 1e-6, dbbox <= 1e-4 | worst dV/V 1.5e-15, dbbox 0.0 | PASS |
| total volume vs the build notes | as recorded | equal (thermal fin1p8 313249.668 vs 313249.667) | PASS |
| every component named | none missing | all 13 / 13 / 18 / 6 names present | PASS |

## 6. Tests added

`tests/test_heat_fin1021_thermal_verification.py` (6 grouped tests, 258 s together with the builder suites): wraps `verification/heat_fin1021_thermal_verify.py`; fails with expected and measured values if any row regresses. Run alone it takes about 2 minutes.

## 7. Observations (status NOTE: not failures, for the lead)

1. **Shell slot (interface, already known as F1).** The 1/8 in fin overlaps the shell's motor-side slot wall by 68.943 mm3 (independent reproduction). The slot must open to y <= -3.675 on the motor side. The 0.019 in fin: 0. The shell is Jasper's.
2. **Screw engagement is over-modelled in the block variants (spec-conformant, but physically optimistic).** `fin1p8` and `fin0p019` put a 4.0 mm shank in the 4.0 mm motor holes as the spec says. The real screws give M3 x 12 on 1/8 in = 3.825 (+0.175 modelled); M3 x 8 on 0.019 in = 2.517 (+1.483, 59 % more thread contact than real); M3 x 10 on 0.019 in = 4.517, which is longer than the 4.0 mm hole in the model. Only the `detailed_fin1p8` station is exact (3.825). The arithmetic for all three claims (3.825, 2.517, 4.517) is confirmed.
3. **Detailed shaft has no D-flat.** It is a plain Ø5 cylinder (volume 1197.7 mm3 over 61 mm). Jasper's reference shaft has a flat 2.0 mm from the axis (446.7 mm3 vs 471.2 for a round shaft over 24 mm). The plain shaft overlaps Jasper's spool bore by 8.353 mm3, but the reference shaft already overlaps that spool by 9.063 mm3 in Jasper's own assembly, so this is not new. The spool is not in the thermal STEPs, so there is no effect on the simulation geometry unless the spool is added.
4. **DXF header extents unset.** `$EXTMIN` / `$EXTMAX` are +-1e20 (the entities, units and layers are correct), so some viewers need a "zoom extents".
5. **STEP product names of the single-solid files** (fin, caps) are the generic "Open CASCADE STEP translator 7.9 n" (7 files). The thermal and NEMA 17 files carry proper names.
6. **Disclosed test loosening, not re-audited.** The build notes say the existing encoder tests' volume bounds and one overhang-area bound were loosened after the Ø4.0 change. They were outside this assignment.
7. Not in scope and not checked: the shop drawing PNG / PDF, the renders, SOLIDWORKS import of the named multi-body STEPs (only the OpenCascade read-back was done), and thermal results.

## Appendix: every check (generated from `verification/heat_fin1021_thermal_results.json`)

Values longer than 230 characters are truncated here; the JSON has them in full.

| id | check | expected | measured | tol | status |
|---|---|---|---|---|---|
| 1.0a | Heat_horn y=0 outline vertices (x,z), design frame | [[-20.0, -18.36], [-20.0, 177.24], [22.0, -18.36], [22.0, 210.24]] | [[-20.0, -18.36], [-20.0, 177.24], [22.0, -18.36], [22.0, 210.24]] | 0.005 | PASS |
| 1.0b | reference outline edge: bottom (mm) | 42.0 | 42.0 | 0.02 | PASS |
| 1.0b | reference outline edge: left (mm) | 195.6 | 195.6 | 0.02 | PASS |
| 1.0b | reference outline edge: right (mm) | 228.6 | 228.6 | 0.02 | PASS |
| 1.0b | reference outline edge: top (slanted) (mm) | 53.4 | 53.413 | 0.02 | PASS |
| 1.1 | flat 1p8: single valid solid | 1 solid, valid | 1 solid(s), valid=True | 0 | PASS |
| 1.1 | asm 1p8: single valid solid | 1 solid, valid | 1 solid(s), valid=True | 0 | PASS |
| 1.1 | asm 0p019: single valid solid | 1 solid, valid | 1 solid(s), valid=True | 0 | PASS |
| 1.2a | asm 1p8 thickness (y extent, mm) | 3.175 | 3.175000000000068 | 0.001 | PASS |
| 1.2b | asm 0p019 thickness (y extent, mm) | 0.483 | 0.48300000000006094 | 0.001 | PASS |
| 1.2c | flat 1p8 thickness (z extent, mm) | 3.175 | 3.1750000000003906 | 0.001 | PASS |
| 1.3a | flat bbox X extent | 42.0 | 42.00000000000674 | 0.001 | PASS |
| 1.3b | flat bbox Y extent | 228.6 | 228.60000000001898 | 0.001 | PASS |
| 1.3c | flat bbox Z extent | 3.175 | 3.1750000000003906 | 0.001 | PASS |
| 1.3d | flat bbox min corner (origin at bottom-left of the 42 mm edge) | [0, 0, 0] | [-0.0, -0.0, -0.0] | 0.001 | PASS |
| 1.3e | flat orientation: material at (41,220), none at (1,220); material at (1,190) | True/False/True | True/False/True | 0 | PASS |
| 1.4 | flat fin holes: Ø22.5 at (20.0, 21.0) and 4 x Ø3.4 at (20+-15.5, 21+-15.5), all through 0..3.175 (tol 0.01) | [[22.5, 20.0, 21.0], [3.4, 4.5, 5.5], [3.4, 4.5, 36.5], [3.4, 35.5, 5.5], [3.4, 35.5, 36.5]] | [[3.4, 4.5, 5.5, -0.0, 3.175], [3.4, 4.5, 36.5, -0.0, 3.175], [3.4, 35.5, 5.5, -0.0, 3.175], [3.4, 35.5, 36.5, -0.0, 3.175], [22.5, 20.0, 21.0, -0.0, 3.175]] | 0.01 | PASS |
| 1.4b | every Heat_horn reference hole has a matching hole (same Ø, centre within 0.01) in the flat fin | 5/5 | 5/5 | 0 | PASS |
| 1.4c | asm 1p8: hole centres in the station frame (Ø22.5 on x 0 / z 2.64; Ø3.4 on 31 mm square) | 5 holes | [[3.4, -15.5, -12.86], [3.4, -15.5, 18.14], [3.4, 15.5, -12.86], [3.4, 15.5, 18.14], [22.5, -0.0, 2.64]] | 0.01 | PASS |
| 1.4c | asm 0p019: hole centres in the station frame (Ø22.5 on x 0 / z 2.64; Ø3.4 on 31 mm square) | 5 holes | [[3.4, -15.5, -12.86], [3.4, -15.5, 18.14], [3.4, 15.5, -12.86], [3.4, 15.5, 18.14], [22.5, -0.0, 2.64]] | 0.01 | PASS |
| 1.5a | asm 1p8 y=0 face plane y vs original assembly Heat_horn y=0 face (mm) | 738.7616451304033 | 738.7616451304 | 0.0001 | PASS |
| 1.5b | asm 1p8 y=0 face area (mm2) vs original face | 8474.275368704546 | 8474.27536867929 | 0.01 | PASS |
| 1.5c | common area of the two faces (mm2) = full original face | 8474.275368704546 | 8474.27536867929 | 0.05 | PASS |
| 1.5d | asm 0p019 y=0 face plane y vs original assembly Heat_horn y=0 face (mm) | 738.7616451304033 | 738.7616451304 | 0.0001 | PASS |
| 1.5e | asm 0p019 common face area with original y=0 face (mm2) | 8474.275368704546 | 8474.27536867929 | 0.05 | PASS |
| 1.5f | asm 1p8: fin y=0 face minus original face, and original minus fin (mm2) | 0.0 | 0.0 | 0.05 | PASS |
| 1.6 | flat 1p8: volume = reference face area x t (mm3) | 26905.824295633804 | 26905.82429563178 | 0.01 | PASS |
| 1.6 | asm 1p8: volume = reference face area x t (mm3) | 26905.824295633804 | 26905.824295618633 | 0.01 | PASS |
| 1.6 | asm 0p019: volume = reference face area x t (mm3) | 4093.0750030838194 | 4093.0750030811255 | 0.01 | PASS |
| 1.7a | STL bbox == flat STEP bbox (max abs diff, mm) | 0.0 | 6.195626667704346e-06 | 0.002 | PASS |
| 1.7b | STL (mesh) volume vs STEP volume (relative; tessellated holes, tol 0.3 %) | 0.0 | 2.1276170739521626e-05 | 0.003 | PASS |
| 1.7c | STL closed manifold (edges not shared by exactly 2 triangles) | 0 | 0 | 0 | PASS |
| 1.7d | STL surface area vs STEP surface area (relative, tol 0.3 %) | 0.0 | 1.7034011733638898e-05 | 0.003 | PASS |
| 1.7e | STL vertices lie on the STEP surface (max distance of 250 sampled vertices, mm) | 0.0 | 1.0092983970565814e-05 | 0.002 | PASS |
| 1.7f | STL facet normals agree with the winding | True | True | 0 | PASS |
| 1.8a | DXF units ($INSUNITS 4 = mm) | 4 | 4 | 0 | PASS |
| 1.8b | DXF entities: 1 closed outline polyline + 5 circles | 1 poly + 5 circles | 1 poly + 5 circles {'LWPOLYLINE': 1, 'CIRCLE': 5, 'LINE': 10} | 0 | PASS |
| 1.8c | DXF outline vertices == flat-frame outline | [[0.0, 0.0], [0.0, 195.6], [42.0, 0.0], [42.0, 228.6]] | [[-0.0, -0.0], [-0.0, 195.6], [42.0, -0.0], [42.0, 228.6]] | 0.005 | PASS |
| 1.8d | DXF circles (Ø, X, Y) == flat STEP holes (tol 0.005) | [[3.4, 4.5, 5.5], [3.4, 4.5, 36.5], [3.4, 35.5, 5.5], [3.4, 35.5, 36.5], [22.5, 20.0, 21.0]] | [[3.4, 4.5, 5.5], [3.4, 4.5, 36.5], [3.4, 35.5, 5.5], [3.4, 35.5, 36.5], [22.5, 20.0, 21.0]] | 0.005 | PASS |
| 1.8f | DXF header drawing extents ($EXTMIN / $EXTMAX) set (observation: unset = +-1e20, viewers must 'zoom extents') | set | $EXTMIN=(1e+20, 1e+20, 1e+20) | 0 | NOTE |
| 1.8e | DXF net area (outline - holes) vs STEP face area (mm2) | 8474.27536870356 | 8474.275368704542 | 0.05 | PASS |
| 2.1a | [fin1p8] component names == spec list (13 bodies) | ['fin_in', 'fin_out', 'insert_deck', 'insert_enc_1', 'insert_enc_2', 'insert_enc_3', 'insert_enc_4', 'motor_block', 'screw_1', 'screw_2', 'screw_3', 'screw_4', 'slipin_mount'] | ['fin_in', 'fin_out', 'insert_deck', 'insert_enc_1', 'insert_enc_2', 'insert_enc_3', 'insert_enc_4', 'motor_block', 'screw_1', 'screw_2', 'screw_3', 'screw_4', 'slipin_mount'] | 0 | PASS |
| 2.1b | [fin1p8] component count / duplicate names | 13 / none | 13 / none | 0 | PASS |
| 2.1c | [fin1p8] every component = one valid solid; whole file solid count = component count | 13 solids, all valid | 13 solids; valid=True; solids per component=[1] | 0 | PASS |
| 2.2b | [fin1p8] second method: max /V_a + V_b - V(fuse)/ over the bbox-near pairs (mm3, limit 0.01) | 0.0 | 0.00019628694280982018 | 0.01 | PASS |
| 2.2 | [fin1p8] max pairwise overlap volume over 78 pairs (22 bbox-near) (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.3a | [fin1p8] slipin_mount == reference Slipin_mount_piecev3 (+O): volume and symmetric difference (mm3) | 0.0 | 1.4599179849028587e-05 | 0.01 | PASS |
| 2.4a | [fin1p8] fin_in + fin_out volume == whole fin (mm3) | 26905.824295618633 | 26905.824295620423 | 0.01 | PASS |
| 2.4b | [fin1p8] fin_in U fin_out == exported whole fin: symmetric difference (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.4c | [fin1p8] split plane z, from fin_in top (station frame, spec 31.16 +- 0.05) | 31.16 | 31.160000000000082 | 0.05 | PASS |
| 2.4d | [fin1p8] fin_out bottom == fin_in top (mm) | 0.0 | 0.0 | 0.0001 | PASS |
| 2.4e | [fin1p8] split contact area fin_in/fin_out = 42 x t (mm2) | 133.35 | 133.34999999999854 | 0.01 | PASS |
| 2.4f | [fin1p8] fin_in holds all 5 holes, fin_out none | 5 / 0 | 5 / 0 | 0 | PASS |
| 2.5a | [fin1p8] motor_block shift along y vs Motor_Reference block (mm; expected 2.0 - t) | -1.1749999999999998 | -1.1749999999998408 | 0.002 | PASS |
| 2.5b | [fin1p8] motor_block shifts only in y (x, z extents and y length unchanged) | 0.0 | 7.958078640513122e-13 | 0.002 | PASS |
| 2.5c | [fin1p8] motor_block == shifted reference block minus 4 holes: reference-minus-built volume (mm3; 4 x pi x 1.5^2 x 4 = 113.097) and built-minus-reference (0) | 113.097 / 0.000 | 113.097 / 0.000 | 0.01 | PASS |
| 2.5d | [fin1p8] motor_block: 4 x Ø3.0 x 4.0 deep holes in the front face on the 31 mm square about the axis | 4 holes Ø3.0 depth 4.0 | [[3.0, -15.5, -15.5, 4.0], [3.0, -15.5, 15.5, 4.0], [3.0, 15.5, -15.5, 4.0], [3.0, 15.5, 15.5, 4.0]] | 0.01 | PASS |
| 2.5e | [fin1p8] motor front face y == fin motor-side face (-t from the tab face) (mm) | 735.5866450000001 | 735.5866451304 | 0.002 | PASS |
| 2.6a | [fin1p8] tab spool-side face y == 5.0 (design), from the 4 tab holes (Ø3.5) (mm) | 743.761645 | 743.7616451304 | 0.002 | PASS |
| 2.6b | [fin1p8] screws 1..4 at (+-15.5, 2.64+-15.5) in the order 1(-x,-z) 2(+x,-z) 3(-x,+z) 4(+x,+z); head Ø5.5 + shank Ø3.0 | all 4 | [[1, 5.0, 8.0, -7.175], [2, 5.0, 8.0, -7.175], [3, 5.0, 8.0, -7.175], [4, 5.0, 8.0, -7.175]] | 0.01 | PASS |
| 2.6c | [fin1p8] screw heads on the tab spool-side face: head y 5.0 .. 8.0 and head underside == tab face (mm) | 5.0..8.0 | [[1, 5.0, 8.0], [2, 5.0, 8.0], [3, 5.0, 8.0], [4, 5.0, 8.0]] | 0.002 | PASS |
| 2.6d | [fin1p8] shank tip y (design): block variant: shank 4.0 mm into the Ø3.0 x 4.0 holes | -7.175 | [-7.175, -7.175, -7.175, -7.175] | 0.002 | PASS |
| 2.6e | [fin1p8] shank and head coaxial (mm) | 0.0 | 0.0 | 1e-06 | PASS |
| 2.7a | [fin1p8] thread/shank engagement behind the fin motor face = tip depth below -t (mm) | 4.0 | [4.0, 4.0, 4.0, 4.0] | 0.002 | PASS |
| 2.8a | [fin1p8] shank-to-fin-hole radial gap (Ø3.4 vs Ø3.0 -> 0.200) (mm) | 0.2 | [0.2, 0.2, 0.2, 0.2] | 0.002 | PASS |
| 2.8b | [fin1p8] shank-to-tab-hole radial gap (Ø3.5 vs Ø3.0 -> 0.250) (mm) | 0.25 | [0.25, 0.25, 0.25, 0.25] | 0.002 | PASS |
| 2.8c | [fin1p8] screw overlap with fin_in / fin_out / slipin_mount (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.8d | [fin1p8] screw to fin_in minimum distance (mm; 0.2 radial gap, no contact) | 0.2 | [0.2, 0.2, 0.2, 0.2] | 0.002 | PASS |
| 2.8e | [fin1p8] screw / motor-hole overlap volume (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.8f | [fin1p8] screw-to-motor contact area (mm2): cylinder Ø3 x 4 + end face (shared) | 44.76769531365455 | [44.768, 44.768, 44.768, 44.768] | 0.05 | PASS |
| 2.9a | [fin1p8] insert_deck: OD 4.1 / ID 2.5 / length 5.7 (mm) | [4.1, 2.5, 5.7] | [4.1, 2.5, 5.7] | 0.005 | PASS |
| 2.9b | [fin1p8] insert_deck coaxial with the slip-in pocket Ø4.1 (axis offset, mm) | 0.0 | 0.0 | 0.001 | PASS |
| 2.9c | [fin1p8] insert_deck top flush with the deck face (pocket opening) (mm); deck face is at the pocket top: air above, material beside | 885.18498070175 | 885.18498070175 | 0.001 | PASS |
| 2.9d | [fin1p8] insert_deck inside the pocket depth (sleeve bottom above pocket floor by 7.0 - 5.7 = 1.3 mm) | 1.3 | 1.3000000000000682 | 0.001 | PASS |
| 2.9e | [fin1p8] insert_deck / slipin contact = outer cylinder pi x 4.1 x 5.7 (mm2); distance 0 | 73.41902031439346 | 73.41902031439895 | 0.05 | PASS |
| 2.9f | [fin1p8] insert_deck overlap with slipin_mount (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.9g | [fin1p8] insert_enc_1..4: OD 3.45 / ID 2.1 / length 4.0, coaxial with the 4 divot holes (same x range, flush with the divot floor), no overlap | 4 sleeves in 4 holes | [[1, 3.45, 2.1, 4.0, 40.25, -4.75], [2, 3.45, 2.1, 4.0, 40.25, 4.75], [3, 3.45, 2.1, 4.0, 49.75, -4.75], [4, 3.45, 2.1, 4.0, 49.75, 4.75]] | 0.001 | PASS |
| 2.9h | [fin1p8] divot hole open at the divot floor (air at +0.2, material beside the hole at -0.2) | True | True | 0 | PASS |
| 2.10 | [fin1p8] touching pairs (distance < 1e-6) are listed | list | [['fin_in', 'fin_out'], ['fin_in', 'motor_block'], ['fin_in', 'slipin_mount'], ['insert_deck', 'slipin_mount'], ['insert_enc_1', 'slipin_mount'], ['insert_enc_2', 'slipin_mount'], ['insert_enc_3', 'slipin_mount'], ['insert_enc_... | 0 | PASS |
| 2.1a | [fin0p019] component names == spec list (13 bodies) | ['fin_in', 'fin_out', 'insert_deck', 'insert_enc_1', 'insert_enc_2', 'insert_enc_3', 'insert_enc_4', 'motor_block', 'screw_1', 'screw_2', 'screw_3', 'screw_4', 'slipin_mount'] | ['fin_in', 'fin_out', 'insert_deck', 'insert_enc_1', 'insert_enc_2', 'insert_enc_3', 'insert_enc_4', 'motor_block', 'screw_1', 'screw_2', 'screw_3', 'screw_4', 'slipin_mount'] | 0 | PASS |
| 2.1b | [fin0p019] component count / duplicate names | 13 / none | 13 / none | 0 | PASS |
| 2.1c | [fin0p019] every component = one valid solid; whole file solid count = component count | 13 solids, all valid | 13 solids; valid=True; solids per component=[1] | 0 | PASS |
| 2.2b | [fin0p019] second method: max /V_a + V_b - V(fuse)/ over the bbox-near pairs (mm3, limit 0.01) | 0.0 | 0.00019957931363023818 | 0.01 | PASS |
| 2.2 | [fin0p019] max pairwise overlap volume over 78 pairs (22 bbox-near) (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.3a | [fin0p019] slipin_mount == reference Slipin_mount_piecev3 (+O): volume and symmetric difference (mm3) | 0.0 | 1.4599179849028587e-05 | 0.01 | PASS |
| 2.4a | [fin0p019] fin_in + fin_out volume == whole fin (mm3) | 4093.0750030811255 | 4093.075003081396 | 0.01 | PASS |
| 2.4b | [fin0p019] fin_in U fin_out == exported whole fin: symmetric difference (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.4c | [fin0p019] split plane z, from fin_in top (station frame, spec 31.16 +- 0.05) | 31.16 | 31.160000000000082 | 0.05 | PASS |
| 2.4d | [fin0p019] fin_out bottom == fin_in top (mm) | 0.0 | 0.0 | 0.0001 | PASS |
| 2.4e | [fin0p019] split contact area fin_in/fin_out = 42 x t (mm2) | 20.285999999999998 | 20.28599999999824 | 0.01 | PASS |
| 2.4f | [fin0p019] fin_in holds all 5 holes, fin_out none | 5 / 0 | 5 / 0 | 0 | PASS |
| 2.5a | [fin0p019] motor_block shift along y vs Motor_Reference block (mm; expected 2.0 - t) | 1.517 | 1.5170000000001664 | 0.002 | PASS |
| 2.5b | [fin0p019] motor_block shifts only in y (x, z extents and y length unchanged) | 0.0 | 7.958078640513122e-13 | 0.002 | PASS |
| 2.5c | [fin0p019] motor_block == shifted reference block minus 4 holes: reference-minus-built volume (mm3; 4 x pi x 1.5^2 x 4 = 113.097) and built-minus-reference (0) | 113.097 / 0.000 | 113.097 / 0.000 | 0.01 | PASS |
| 2.5d | [fin0p019] motor_block: 4 x Ø3.0 x 4.0 deep holes in the front face on the 31 mm square about the axis | 4 holes Ø3.0 depth 4.0 | [[3.0, -15.5, -15.5, 4.0], [3.0, -15.5, 15.5, 4.0], [3.0, 15.5, -15.5, 4.0], [3.0, 15.5, 15.5, 4.0]] | 0.01 | PASS |
| 2.5e | [fin0p019] motor front face y == fin motor-side face (-t from the tab face) (mm) | 738.2786450000001 | 738.2786451304 | 0.002 | PASS |
| 2.6a | [fin0p019] tab spool-side face y == 5.0 (design), from the 4 tab holes (Ø3.5) (mm) | 743.761645 | 743.7616451304 | 0.002 | PASS |
| 2.6b | [fin0p019] screws 1..4 at (+-15.5, 2.64+-15.5) in the order 1(-x,-z) 2(+x,-z) 3(-x,+z) 4(+x,+z); head Ø5.5 + shank Ø3.0 | all 4 | [[1, 5.0, 8.0, -4.483], [2, 5.0, 8.0, -4.483], [3, 5.0, 8.0, -4.483], [4, 5.0, 8.0, -4.483]] | 0.01 | PASS |
| 2.6c | [fin0p019] screw heads on the tab spool-side face: head y 5.0 .. 8.0 and head underside == tab face (mm) | 5.0..8.0 | [[1, 5.0, 8.0], [2, 5.0, 8.0], [3, 5.0, 8.0], [4, 5.0, 8.0]] | 0.002 | PASS |
| 2.6d | [fin0p019] shank tip y (design): block variant: shank 4.0 mm into the Ø3.0 x 4.0 holes | -4.483 | [-4.483, -4.483, -4.483, -4.483] | 0.002 | PASS |
| 2.6e | [fin0p019] shank and head coaxial (mm) | 0.0 | 0.0 | 1e-06 | PASS |
| 2.7a | [fin0p019] thread/shank engagement behind the fin motor face = tip depth below -t (mm) | 4.0 | [4.0, 4.0, 4.0, 4.0] | 0.002 | PASS |
| 2.8a | [fin0p019] shank-to-fin-hole radial gap (Ø3.4 vs Ø3.0 -> 0.200) (mm) | 0.2 | [0.2, 0.2, 0.2, 0.2] | 0.002 | PASS |
| 2.8b | [fin0p019] shank-to-tab-hole radial gap (Ø3.5 vs Ø3.0 -> 0.250) (mm) | 0.25 | [0.25, 0.25, 0.25, 0.25] | 0.002 | PASS |
| 2.8c | [fin0p019] screw overlap with fin_in / fin_out / slipin_mount (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.8d | [fin0p019] screw to fin_in minimum distance (mm; 0.2 radial gap, no contact) | 0.2 | [0.2, 0.2, 0.2, 0.2] | 0.002 | PASS |
| 2.8e | [fin0p019] screw / motor-hole overlap volume (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.8f | [fin0p019] screw-to-motor contact area (mm2): cylinder Ø3 x 4 + end face (shared) | 44.76769531365455 | [44.768, 44.768, 44.768, 44.768] | 0.05 | PASS |
| 2.9a | [fin0p019] insert_deck: OD 4.1 / ID 2.5 / length 5.7 (mm) | [4.1, 2.5, 5.7] | [4.1, 2.5, 5.7] | 0.005 | PASS |
| 2.9b | [fin0p019] insert_deck coaxial with the slip-in pocket Ø4.1 (axis offset, mm) | 0.0 | 0.0 | 0.001 | PASS |
| 2.9c | [fin0p019] insert_deck top flush with the deck face (pocket opening) (mm); deck face is at the pocket top: air above, material beside | 885.18498070175 | 885.18498070175 | 0.001 | PASS |
| 2.9d | [fin0p019] insert_deck inside the pocket depth (sleeve bottom above pocket floor by 7.0 - 5.7 = 1.3 mm) | 1.3 | 1.3000000000000682 | 0.001 | PASS |
| 2.9e | [fin0p019] insert_deck / slipin contact = outer cylinder pi x 4.1 x 5.7 (mm2); distance 0 | 73.41902031439346 | 73.41902031439895 | 0.05 | PASS |
| 2.9f | [fin0p019] insert_deck overlap with slipin_mount (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.9g | [fin0p019] insert_enc_1..4: OD 3.45 / ID 2.1 / length 4.0, coaxial with the 4 divot holes (same x range, flush with the divot floor), no overlap | 4 sleeves in 4 holes | [[1, 3.45, 2.1, 4.0, 40.25, -4.75], [2, 3.45, 2.1, 4.0, 40.25, 4.75], [3, 3.45, 2.1, 4.0, 49.75, -4.75], [4, 3.45, 2.1, 4.0, 49.75, 4.75]] | 0.001 | PASS |
| 2.9h | [fin0p019] divot hole open at the divot floor (air at +0.2, material beside the hole at -0.2) | True | True | 0 | PASS |
| 2.10 | [fin0p019] touching pairs (distance < 1e-6) are listed | list | [['fin_in', 'fin_out'], ['fin_in', 'motor_block'], ['fin_in', 'slipin_mount'], ['insert_deck', 'slipin_mount'], ['insert_enc_1', 'slipin_mount'], ['insert_enc_2', 'slipin_mount'], ['insert_enc_3', 'slipin_mount'], ['insert_enc_... | 0 | PASS |
| 2.1a | [detailed_fin1p8] component names == spec list (18 bodies) | ['connector', 'fin_in', 'fin_out', 'front_cap', 'insert_deck', 'insert_enc_1', 'insert_enc_2', 'insert_enc_3', 'insert_enc_4', 'rear_cap', 'screw_1', 'screw_2', 'screw_3', 'screw_4', 'shaft', 'slipin_mount', 'stator', 'winding'] | ['connector', 'fin_in', 'fin_out', 'front_cap', 'insert_deck', 'insert_enc_1', 'insert_enc_2', 'insert_enc_3', 'insert_enc_4', 'rear_cap', 'screw_1', 'screw_2', 'screw_3', 'screw_4', 'shaft', 'slipin_mount', 'stator', 'winding'] | 0 | PASS |
| 2.1b | [detailed_fin1p8] component count / duplicate names | 18 / none | 18 / none | 0 | PASS |
| 2.1c | [detailed_fin1p8] every component = one valid solid; whole file solid count = component count | 18 solids, all valid | 18 solids; valid=True; solids per component=[1] | 0 | PASS |
| 2.2b | [detailed_fin1p8] second method: max /V_a + V_b - V(fuse)/ over the bbox-near pairs (mm3, limit 0.01) | 0.0 | 0.00019628694280982018 | 0.01 | PASS |
| 2.2 | [detailed_fin1p8] max pairwise overlap volume over 153 pairs (38 bbox-near) (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.3a | [detailed_fin1p8] slipin_mount == reference Slipin_mount_piecev3 (+O): volume and symmetric difference (mm3) | 0.0 | 1.4599179849028587e-05 | 0.01 | PASS |
| 2.4a | [detailed_fin1p8] fin_in + fin_out volume == whole fin (mm3) | 26905.824295618633 | 26905.824295620423 | 0.01 | PASS |
| 2.4b | [detailed_fin1p8] fin_in U fin_out == exported whole fin: symmetric difference (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.4c | [detailed_fin1p8] split plane z, from fin_in top (station frame, spec 31.16 +- 0.05) | 31.16 | 31.160000000000082 | 0.05 | PASS |
| 2.4d | [detailed_fin1p8] fin_out bottom == fin_in top (mm) | 0.0 | 0.0 | 0.0001 | PASS |
| 2.4e | [detailed_fin1p8] split contact area fin_in/fin_out = 42 x t (mm2) | 133.35 | 133.34999999999854 | 0.01 | PASS |
| 2.4f | [detailed_fin1p8] fin_in holds all 5 holes, fin_out none | 5 / 0 | 5 / 0 | 0 | PASS |
| 2.5a | [detailed_fin1p8] motor front face moves by 2.0 - t relative to Motor_Reference (mm) | -1.1749999999999998 | -1.1749999999998408 | 0.002 | PASS |
| 2.5e | [detailed_fin1p8] motor front face y == fin motor-side face (-t from the tab face) (mm) | 735.5866450000001 | 735.5866451304 | 0.002 | PASS |
| 2.6a | [detailed_fin1p8] tab spool-side face y == 5.0 (design), from the 4 tab holes (Ø3.5) (mm) | 743.761645 | 743.7616451304 | 0.002 | PASS |
| 2.6b | [detailed_fin1p8] screws 1..4 at (+-15.5, 2.64+-15.5) in the order 1(-x,-z) 2(+x,-z) 3(-x,+z) 4(+x,+z); head Ø5.5 + shank Ø3.0 | all 4 | [[1, 5.0, 8.0, -7.0], [2, 5.0, 8.0, -7.0], [3, 5.0, 8.0, -7.0], [4, 5.0, 8.0, -7.0]] | 0.01 | PASS |
| 2.6c | [detailed_fin1p8] screw heads on the tab spool-side face: head y 5.0 .. 8.0 and head underside == tab face (mm) | 5.0..8.0 | [[1, 5.0, 8.0], [2, 5.0, 8.0], [3, 5.0, 8.0], [4, 5.0, 8.0]] | 0.002 | PASS |
| 2.6d | [detailed_fin1p8] shank tip y (design): detailed: M3 x 12, shank tip y = -7.0 | -7.0 | [-7.0, -7.0, -7.0, -7.0] | 0.002 | PASS |
| 2.6e | [detailed_fin1p8] shank and head coaxial (mm) | 0.0 | 0.0 | 1e-06 | PASS |
| 2.7a | [detailed_fin1p8] thread/shank engagement behind the fin motor face = tip depth below -t (mm) | 3.825 | [3.825, 3.825, 3.825, 3.825] | 0.002 | PASS |
| 2.7b | [detailed_fin1p8] screw length under the head = M3 x 12 (mm) -> 5 (tab) + 3.175 (fin) + 3.825 (engagement) | 12.0 | [11.99999986960006, 11.99999986960006, 11.99999986960006, 11.99999986960006] | 0.002 | PASS |
| 2.8a | [detailed_fin1p8] shank-to-fin-hole radial gap (Ø3.4 vs Ø3.0 -> 0.200) (mm) | 0.2 | [0.2, 0.2, 0.2, 0.2] | 0.002 | PASS |
| 2.8b | [detailed_fin1p8] shank-to-tab-hole radial gap (Ø3.5 vs Ø3.0 -> 0.250) (mm) | 0.25 | [0.25, 0.25, 0.25, 0.25] | 0.002 | PASS |
| 2.8c | [detailed_fin1p8] screw overlap with fin_in / fin_out / slipin_mount (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.8d | [detailed_fin1p8] screw to fin_in minimum distance (mm; 0.2 radial gap, no contact) | 0.2 | [0.2, 0.2, 0.2, 0.2] | 0.002 | PASS |
| 2.8e | [detailed_fin1p8] screw / motor-hole overlap volume (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 2.8f | [detailed_fin1p8] screw-to-motor contact area (mm2): cylinder Ø3 x 3.825, 0.675 air under the tip | 36.04977569994288 | [36.05, 36.05, 36.05, 36.05] | 0.05 | PASS |
| 2.8g | [detailed_fin1p8] front_cap tapped holes: 4 x Ø3.0, depth 4.5 (so the M3 x 12 tip stops 0.675 short of the bottom) | 4 x depth 4.5 | [[3.0, 4.5], [3.0, 4.5], [3.0, 4.5], [3.0, 4.5]] | 0.002 | PASS |
| 2.9a | [detailed_fin1p8] insert_deck: OD 4.1 / ID 2.5 / length 5.7 (mm) | [4.1, 2.5, 5.7] | [4.1, 2.5, 5.7] | 0.005 | PASS |
| 2.9b | [detailed_fin1p8] insert_deck coaxial with the slip-in pocket Ø4.1 (axis offset, mm) | 0.0 | 0.0 | 0.001 | PASS |
| 2.9c | [detailed_fin1p8] insert_deck top flush with the deck face (pocket opening) (mm); deck face is at the pocket top: air above, material beside | 885.18498070175 | 885.18498070175 | 0.001 | PASS |
| 2.9d | [detailed_fin1p8] insert_deck inside the pocket depth (sleeve bottom above pocket floor by 7.0 - 5.7 = 1.3 mm) | 1.3 | 1.3000000000000682 | 0.001 | PASS |
| 2.9e | [detailed_fin1p8] insert_deck / slipin contact = outer cylinder pi x 4.1 x 5.7 (mm2); distance 0 | 73.41902031439346 | 73.41902031439895 | 0.05 | PASS |
| 2.9f | [detailed_fin1p8] insert_deck overlap with slipin_mount (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.9g | [detailed_fin1p8] insert_enc_1..4: OD 3.45 / ID 2.1 / length 4.0, coaxial with the 4 divot holes (same x range, flush with the divot floor), no overlap | 4 sleeves in 4 holes | [[1, 3.45, 2.1, 4.0, 40.25, -4.75], [2, 3.45, 2.1, 4.0, 40.25, 4.75], [3, 3.45, 2.1, 4.0, 49.75, -4.75], [4, 3.45, 2.1, 4.0, 49.75, 4.75]] | 0.001 | PASS |
| 2.9h | [detailed_fin1p8] divot hole open at the divot floor (air at +0.2, material beside the hole at -0.2) | True | True | 0 | PASS |
| 2.10 | [detailed_fin1p8] touching pairs (distance < 1e-6) are listed | list | [['connector', 'rear_cap'], ['fin_in', 'fin_out'], ['fin_in', 'front_cap'], ['fin_in', 'slipin_mount'], ['front_cap', 'screw_1'], ['front_cap', 'screw_2'], ['front_cap', 'screw_3'], ['front_cap', 'screw_4'], ['front_cap', 'shaf... | 0 | PASS |
| 2.11a | shell fin-slot walls measured on Shell_Casing.step: y (file frame) and roof-plate top z | y -2.690 / +2.310; top z 31.16 +- 0.05 (design) | y -2.688 / 2.312; top z 31.152 (file 31.1558) | 0.05 | PASS |
| 2.11b | split plane (fin_in top, file frame) vs shell roof top at the slot (mm) | 0.0 | 0.004201937139082901 | 0.05 | PASS |
| 2.11c | 1/8 in fin vs shell (finding F1: motor-side slot wall overlaps the fin) (mm3; builder 68.94) | 68.94 | 68.94262985595074 | 1.0 | PASS |
| 2.11d | 0.019 in fin vs shell (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.11e | [fin1p8] motor bodies (excl. shaft) minimum distance to the shell (mm; clears the shell; builder: 1.9 for the 1/8 in stack) | >= 1.0 (1.915 for 1/8 in) | 1.915 | 0.0 | PASS |
| 2.11f | [fin1p8] overlap of slipin_mount / inserts / screws / motor bodies with the shell (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.11e | [fin0p019] motor bodies (excl. shaft) minimum distance to the shell (mm; clears the shell; builder: 1.9 for the 1/8 in stack) | >= 1.0 (1.915 for 1/8 in) | 4.0444 | 0.0 | PASS |
| 2.11f | [fin0p019] overlap of slipin_mount / inserts / screws / motor bodies with the shell (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.11e | [detailed_fin1p8] motor bodies (excl. shaft) minimum distance to the shell (mm; clears the shell; builder: 1.9 for the 1/8 in stack) | >= 1.0 (1.915 for 1/8 in) | 1.915 | 0.0 | PASS |
| 2.11f | [detailed_fin1p8] overlap of slipin_mount / inserts / screws / motor bodies with the shell (mm3) | 0.0 | 0.0 | 0.01 | PASS |
| 2.11g | [detailed_fin1p8] shaft end y (design; expected 20.825) (mm); shaft vs Jasper's spool (not in the export): OBSERVATION, plain round Ø5 shaft (no D-flat) overlaps the spool bore profile; Jasper's own reference shaft (with its D-... | 20.825 | end 20.8250; detailed shaft/spool overlap 8.353 mm3; reference Motor_Reference shaft/spool overlap 9.063 mm3; reference shaft volume 446.7 vs round 471.2 mm3 | 0.01 | NOTE |
| 2.11h | [detailed_fin1p8] shaft engagement in the spool bore (y 7 .. shaft end) (mm; spec 13.8) | 13.8 | 13.825 | 0.05 | PASS |
| 2.12 | [fin1p8] touching pairs and contact areas: my 17 touching pairs vs the builder's 17-row contact CSV (set equality; worst area difference mm2) | same pairs, areas within 0.01 | same set=True; extra mine=[]; missing=[]; worst /dA/=0.0004 ('insert_enc_1', 'slipin_mount') | 0.01 | PASS |
| 2.12b | [fin1p8] builder's near-gap list (not touching) is true: measured distances (mm) vs the CSV | {"('fin_in', 'screw_1')": 0.2, "('fin_in', 'screw_4')": 0.2, "('fin_in', 'screw_3')": 0.2, "('fin_in', 'screw_2')": 0.2} | {"('fin_in', 'screw_1')": 0.2, "('fin_in', 'screw_4')": 0.2, "('fin_in', 'screw_3')": 0.2, "('fin_in', 'screw_2')": 0.2} | 0.002 | PASS |
| 2.12 | [fin0p019] touching pairs and contact areas: my 17 touching pairs vs the builder's 17-row contact CSV (set equality; worst area difference mm2) | same pairs, areas within 0.01 | same set=True; extra mine=[]; missing=[]; worst /dA/=0.0004 ('insert_enc_1', 'slipin_mount') | 0.01 | PASS |
| 2.12b | [fin0p019] builder's near-gap list (not touching) is true: measured distances (mm) vs the CSV | {"('fin_in', 'screw_1')": 0.2, "('fin_in', 'screw_2')": 0.2, "('fin_in', 'screw_3')": 0.2, "('fin_in', 'screw_4')": 0.2} | {"('fin_in', 'screw_1')": 0.2, "('fin_in', 'screw_2')": 0.2, "('fin_in', 'screw_3')": 0.2, "('fin_in', 'screw_4')": 0.2} | 0.002 | PASS |
| 2.12 | [detailed_fin1p8] touching pairs and contact areas: my 27 touching pairs vs the builder's 27-row contact CSV (set equality; worst area difference mm2) | same pairs, areas within 0.01 | same set=True; extra mine=[]; missing=[]; worst /dA/=0.0004 ('insert_enc_1', 'slipin_mount') | 0.01 | PASS |
| 2.12b | [detailed_fin1p8] builder's near-gap list (not touching) is true: measured distances (mm) vs the CSV | {"('fin_in', 'screw_2')": 0.2, "('fin_in', 'screw_4')": 0.2, "('fin_in', 'screw_3')": 0.2, "('fin_in', 'screw_1')": 0.2} | {"('fin_in', 'screw_2')": 0.2, "('fin_in', 'screw_4')": 0.2, "('fin_in', 'screw_3')": 0.2, "('fin_in', 'screw_1')": 0.2} | 0.002 | PASS |
| 2.13b | [fin1p8] body table mass = volume x density (max /dm/ g) | 0.0 | 0.004477085999951669 | 0.01 | PASS |
| 2.13 | [fin1p8] body table volumes vs measured (max /dV/ mm3, over 13 rows; every body listed=True) | 0.0 | 0.00046920080785639584 | 0.01 | PASS |
| 2.13b | [fin0p019] body table mass = volume x density (max /dm/ g) | 0.0 | 0.004477085999951669 | 0.01 | PASS |
| 2.13 | [fin0p019] body table volumes vs measured (max /dV/ mm3, over 13 rows; every body listed=True) | 0.0 | 0.00046920080785639584 | 0.01 | PASS |
| 2.13b | [detailed_fin1p8] body table mass = volume x density (max /dm/ g) | 0.0 | 0.0004960999999923388 | 0.01 | PASS |
| 2.13 | [detailed_fin1p8] body table volumes vs measured (max /dV/ mm3, over 18 rows; every body listed=True) | 0.0 | 0.00046920080785639584 | 0.01 | PASS |
| 2.14b | OBSERVATION: block variants model 4.0 mm of shank in the motor holes (spec) vs the real screw engagement: 1/8 in + M3x12 = 3.825 (+0.175 modelled); 0.019 in + M3x8 = 2.517 (+1.483, +59 %); 0.019 in + M3x10 = 4.517 (longer than ... | info | modelled 4.0 in both block variants; detailed variant 3.825 exact | 0 | NOTE |
| 2.14 | engagement arithmetic M3x12 + 1/8 in = L - 5 (tab) - t (mm) | 3.825 | 3.825 | 0.001 | PASS |
| 2.14 | engagement arithmetic M3x8 + 0.019 in = L - 5 (tab) - t (mm) | 2.517 | 2.517 | 0.001 | PASS |
| 2.14 | engagement arithmetic M3x10 + 0.019 in = L - 5 (tab) - t (mm) | 4.517 | 4.517 | 0.001 | PASS |
| 3.1a | nema17_thermal.step components | ['connector', 'front_cap', 'rear_cap', 'shaft', 'stator', 'winding'] | ['connector', 'front_cap', 'rear_cap', 'shaft', 'stator', 'winding'] | 0 | PASS |
| 3.1b | each part: one valid solid, one shell | 6 x (1 solid, 1 shell, valid) | [['front_cap', 1, 1, True], ['stator', 1, 1, True], ['winding', 1, 1, True], ['rear_cap', 1, 1, True], ['shaft', 1, 1, True], ['connector', 1, 1, True]] | 0 | PASS |
| 3.2a | front_cap: body 42.3 mm square (x and z extent) (mm) | [42.3, 42.3] | [42.3, 42.3] | 0.01 | PASS |
| 3.2a | stator: body 42.3 mm square (x and z extent) (mm) | [42.3, 42.3] | [42.3, 42.3] | 0.01 | PASS |
| 3.2a | rear_cap: body 42.3 mm square (x and z extent) (mm) | [42.3, 42.3] | [42.3, 42.3] | 0.01 | PASS |
| 3.2b | body length: rear cap back face y -38; front cap boss end y +2 (front face y 0) (mm) | [-38.0, 2.0] | [-38.0, 2.0] | 0.005 | PASS |
| 3.2c | front face is at y = 0 (one planar face, boss and 4 holes cut out of it) | 1 face at y 0 | 1 | 0 | PASS |
| 3.2d | stator long edges chamfered 3 mm (corner point (20.5,20.5) outside, (19,19) inside, all 4 corners) | True | True | 0 | PASS |
| 3.2e | stator chamfer faces: 4 x 3 sqrt2 x 22 (mm2) | 93.33809511662429 | [93.338, 93.338, 93.338, 93.338] | 0.05 | PASS |
| 3.3a | front_cap: 4 tapped holes Ø3.0 x 4.5 deep on the 31 mm square (x, z, r, depth) | [[-15.5, -15.5, 1.5, 4.5], [-15.5, 15.5, 1.5, 4.5], [15.5, -15.5, 1.5, 4.5], [15.5, 15.5, 1.5, 4.5]] | [[-15.5, -15.5, 1.5, 4.5], [-15.5, 15.5, 1.5, 4.5], [15.5, -15.5, 1.5, 4.5], [15.5, 15.5, 1.5, 4.5]] | 0.005 | PASS |
| 3.3b | tap holes open at the front face (hole top y = 0, bottom y = -4.5) | [0.0, -4.5] | [[0.0, -4.5]] | 0.005 | PASS |
| 3.4 | front_cap pilot boss Ø22 on the axis, y 0 .. +2 | Ø22, y 0..2 | [[22.0, 0.0, 0.0, 0.0, 2.0]] | 0.005 | PASS |
| 3.5 | shaft Ø5.0, y -37 .. +24 (24 proud of the front face) | Ø5, -37..24 | [[5.0, -37.0, 24.0]] | 0.005 | PASS |
| 3.6 | bores that carry the shaft: front cap Ø5.0 through (y -8..2), rear cap Ø5.0 blind seat y -37..-30 | [[5.0, -8.0, 2.0], [5.0, -37.0, -30.0]] | [[5.0, -8.0, 2.0], [5.0, -37.0, -30.0]] | 0.01 | PASS |
| 3.7 | connector 16 (z) x 6 (y) x 6 (x), x 21.15..27.15, y -38..-32, flush with the back face | [[21.15, 27.15], [-38, -32], [-8, 8]] | [[21.15, 27.15], [-38.0, -32.0], [-8.0, 8.0]] | 0.005 | PASS |
| 3.8 | stator bore Ø34, winding annulus Ø23..Ø34 x 22 inside it | bore Ø34; winding Ø23/Ø34, y -30..-8 | [1, [[23.0, -30.0, -8.0], [34.0, -30.0, -8.0]]] | 0.005 | PASS |
| 3.9a | max pairwise overlap, 15 pairs, incl. the shaft-to-cap contact pairs (mm3, limit 0.01) | 0.0 | 0.0 | 0.01 | PASS |
| 3.9b | shaft-to-cap contact is surface contact: front_cap-shaft pi x 5 x 10 = 157.08, rear_cap-shaft pi x 5 x 7 + pi x 2.5^2 = 129.59 (mm2) | [157.08, 129.59] | [157.08, 129.59] | 0.05 | PASS |
| 3.9c | contact list (touching pairs, mm2) | list | [['connector', 'rear_cap', 96.0], ['front_cap', 'shaft', 157.08], ['front_cap', 'stator', 863.37], ['front_cap', 'winding', 492.44], ['rear_cap', 'shaft', 129.59], ['rear_cap', 'stator', 863.37], ['rear_cap', 'winding', 492.44]... | 0 | PASS |
| 3.9d | shaft to winding distance (air around the shaft inside the stator; 17 - ... = 11.5 - 2.5 = 9.0 mm) | 9.0 | 9.0 | 0.01 | PASS |
| 3.10 | total mass with the table densities (g) vs 0.28 kg reference motor (builder: 288.15, +2.9 %) | 288.15 | 288.16 | 0.1 | PASS |
| 3.11a | [fin1p8] nema17 asm1021 file = motor-frame model translated by (X0, Y0 - t, Z0) = front face on the fin motor face, axis on x 0 / z 2.64 (max bbox deviation mm) | 0.0 | 0.0 | 0.01 | PASS |
| 3.11b | [fin1p8] front face y (design) == -t; shaft end y (design) == 24 - t (mm) | [-3.175, 20.825] | [-3.175, 20.825] | 0.003 | PASS |
| 3.11a | [fin0p019] nema17 asm1021 file = motor-frame model translated by (X0, Y0 - t, Z0) = front face on the fin motor face, axis on x 0 / z 2.64 (max bbox deviation mm) | 0.0 | 0.0 | 0.01 | PASS |
| 3.11b | [fin0p019] front face y (design) == -t; shaft end y (design) == 24 - t (mm) | [-0.483, 23.517] | [-0.483, 23.517] | 0.003 | PASS |
| 3.11c | nema17_thermal_fin1p8_asm1021 == the six motor bodies of thermal_station1021_detailed_fin1p8 (max bbox deviation, mm) | 0.0 | 0.0 | 0.002 | PASS |
| 3.12 | [fin1p8] nema17 front cap boss in the fin pilot (Ø22.5) / tab pilot (Ø22.4): overlap with fin and slip-in (mm3); boss end y (design) | 0 / 0 | fin 0.00000 / slipin 0.00000; boss end y -1.175 (fin tab-side face at y 0, tab pilot r 11.2 vs boss r 11) | 0.01 | PASS |
| 3.12 | [fin0p019] nema17 front cap boss in the fin pilot (Ø22.5) / tab pilot (Ø22.4): overlap with fin and slip-in (mm3); boss end y (design) | 0 / 0 | fin 0.00000 / slipin 0.00000; boss end y 1.517 (fin tab-side face at y 0, tab pilot r 11.2 vs boss r 11) | 0.01 | PASS |
| 3.13 | nema17_thermal.step volumes == fresh build_bodies() (max /dV/ mm3; the builder's own code, only a currency check) | 0.0 | 7.785274647176266e-10 | 0.01 | PASS |
| 4.1 | [std] station-frame cap: one valid solid | 1 solid, valid | 1 solid, valid=True, shells=1 | 0 | PASS |
| 4.2 | [std] cap volume (mm3; build notes) | 531.94 | 531.941 | 0.05 | PASS |
| 4.3a | [std] peg end y (mm; station frame) | 22.6 | 22.6 | 0.01 | PASS |
| 4.3b | [std] head: Ø14 x ... magnet face at y 29.3 (bbox x, z = +-7; y max 29.3) | [14.0, 14.0, 29.3] | [14.0, 14.0, 29.3] | 0.005 | PASS |
| 4.4a | [std] magnet pocket Ø4.3 on the shaft axis, y 26.75 .. 29.3 (Ø, axis x/z, floor y, rim y) | [4.3, 0.0, 0.0, 26.75, 29.3] | [[4.3, 0.0, 0.0, 26.75, 29.3]] | 0.005 | PASS |
| 4.4b | [std] pocket probe at y 28: air at r 2.1 and wall at r 2.2 at 0/30/90/270 deg (the Ø4.0 magnet + 0.15 per side) | True | True | 0 | PASS |
| 4.4c | [std] Ø4.0 x 2.5 magnet (y 26.8..29.3, flush with the face) vs the cap: only crush-rib overlap (mm3; builder 0.403, limit < 1) | 0.403 | 0.403 | 0.15 | PASS |
| 4.5a | [std] asm1021 copy = station copy translated by (O + RES + (0, 0, 2.64)) (max bbox deviation mm); volume equal | 0.0 | 0.0 | 0.001 | PASS |
| 4.1 | [short] station-frame cap: one valid solid | 1 solid, valid | 1 solid, valid=True, shells=1 | 0 | PASS |
| 4.2 | [short] cap volume (mm3; build notes) | 502.31 | 502.312 | 0.05 | PASS |
| 4.3a | [short] peg end y (mm; station frame) | 24.1 | 24.1 | 0.01 | PASS |
| 4.3b | [short] head: Ø14 x ... magnet face at y 29.3 (bbox x, z = +-7; y max 29.3) | [14.0, 14.0, 29.3] | [14.0, 14.0, 29.3] | 0.005 | PASS |
| 4.4a | [short] magnet pocket Ø4.3 on the shaft axis, y 26.75 .. 29.3 (Ø, axis x/z, floor y, rim y) | [4.3, 0.0, 0.0, 26.75, 29.3] | [[4.3, 0.0, 0.0, 26.75, 29.3]] | 0.005 | PASS |
| 4.4b | [short] pocket probe at y 28: air at r 2.1 and wall at r 2.2 at 0/30/90/270 deg (the Ø4.0 magnet + 0.15 per side) | True | True | 0 | PASS |
| 4.4c | [short] Ø4.0 x 2.5 magnet (y 26.8..29.3, flush with the face) vs the cap: only crush-rib overlap (mm3; builder 0.403, limit < 1) | 0.403 | 0.403 | 0.15 | PASS |
| 4.5a | [short] asm1021 copy = station copy translated by (O + RES + (0, 0, 2.64)) (max bbox deviation mm); volume equal | 0.0 | 0.0 | 0.001 | PASS |
| 4.5b | [std] asm1021 peg end y (design, from the tab face y 0 of the assembly) (mm) | 22.6 | 22.6 | 0.01 | PASS |
| 4.5b | [short] asm1021 peg end y (design, from the tab face y 0 of the assembly) (mm) | 24.1 | 24.1 | 0.01 | PASS |
| 4.6a | 0.019 in motor shaft end y (design) from nema17_thermal_fin0p019_asm1021 (mm; 22.0 + 1.517 = 23.517) | 23.517 | 23.517 | 0.003 | PASS |
| 4.6b | 1/8 in motor shaft end y (design) from nema17_thermal_fin1p8_asm1021 (mm; 20.825) | 20.825 | 20.825 | 0.003 | PASS |
| 4.6c | [peg1p9] clearance to an ideal Ø5 shaft ending at y 23.517 (mm; required >= 0.5; builder 0.583) | >= 0.5 | 0.5830 (overlap 0.00000) | 0.0 | PASS |
| 4.6d | [standard] vs the same 23.517 shaft: INTERFERENCE expected (why the short peg exists): overlap (mm3; builder ~18) | > 0 (collides) | 16.812 mm3, distance 0.0000 | 0.0 | PASS |
| 4.6e | [peg1p9 asm1021] clearance to the nema17 0.019 in asm shaft (mm; required >= 0.5) | >= 0.5 | 0.583 | 0.0 | PASS |
| 4.6f | [standard asm1021] clearance to the nema17 1/8 in asm shaft (mm; builder 1.775) | 1.775 | 1.775 | 0.005 | PASS |
| 4.6g | [standard asm1021] vs the 0.019 in motor shaft: overlap (mm3, expected collision ~18, builder note) | > 0 | 16.812 | 0.0 | PASS |
| 4.7 | [std asm1021] touches only Spool1011 in Jasper's assembly STEP (distance < 1e-6), contact volume (mm3; builder 0.477) | {'Spool1011': 0.477} | {'Spool1011': 0.4766} | 0.005 | PASS |
| 4.7b | [std asm1021] nearest other solids in the original assembly (shaft ends at y 22.0 there) | info | [[0.6, 'solid 5'], [14.15, 'Slipin_mount_piecev3'], [22.604, 'Shell_Casing']] | 0 | PASS |
| 4.7 | [short asm1021] touches only Spool1011 in Jasper's assembly STEP (distance < 1e-6), contact volume (mm3; builder 0.234) | {'Spool1011': 0.234} | {'Spool1011': 0.2343} | 0.005 | PASS |
| 4.7b | [short asm1021] nearest other solids in the original assembly (shaft ends at y 22.0 there) | info | [[2.1, 'solid 5'], [14.15, 'Slipin_mount_piecev3'], [22.604, 'Shell_Casing']] | 0 | PASS |
| 4.8a | [std] STL bbox 14 x 14 x 6.7 with the magnet face on the bed (z min 0) | [14.0, 14.0, 6.7, 0.0] | [14.0, 13.996, 6.7, -0.0] | 0.01 | PASS |
| 4.8b | [std] STL volume vs STEP (relative; tessellated, tol 1 %) | 0.0 | 0.00036707844003818076 | 0.01 | PASS |
| 4.8c | [std] STL closed manifold (bad edges) | 0 | 0 | 0 | PASS |
| 4.8d | [std] STL orientation: peg end at top (z max, radius <= 2.6), pocket rim (r 2.15) on the bed (z 0) | True | True | 0 | PASS |
| 4.8a | [short] STL bbox 14 x 14 x 5.2 with the magnet face on the bed (z min 0) | [14.0, 14.0, 5.2, 0.0] | [14.0, 13.996, 5.2, -0.0] | 0.01 | PASS |
| 4.8b | [short] STL volume vs STEP (relative; tessellated, tol 1 %) | 0.0 | 0.0003728507629211575 | 0.01 | PASS |
| 4.8c | [short] STL closed manifold (bad edges) | 0 | 0 | 0 | PASS |
| 4.8d | [short] STL orientation: peg end at top (z max, radius <= 2.6), pocket rim (r 2.15) on the bed (z 0) | True | True | 0 | PASS |
| 4.9 | [std] cap file == fresh builder output (volume difference mm3; currency check) | 0.0 | 9.548989510221872e-08 | 0.01 | PASS |
| 4.9 | [short] cap file == fresh builder output (volume difference mm3; currency check) | 0.0 | 7.73636088524654e-08 | 0.01 | PASS |
| 5.0b | heat_fin1021_1p8: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | heat_fin1021_1p8: valid BREP, 1 solid(s), one shell each (no stray bodies) | 1 solids, valid | 1 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | heat_fin1021_1p8: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 1 | 0 | PASS |
| 5.3 | heat_fin1021_1p8: total volume vs build-notes value (mm3) | 26905.824 | 26905.824 | 0.053811648 | PASS |
| 5.5 | heat_fin1021_1p8: single-solid file: STEP product name (cosmetic observation) | info | ['Open CASCADE STEP translator 7.9 3'] | 0 | NOTE |
| 5.0b | heat_fin1021_1p8_asm1021: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | heat_fin1021_1p8_asm1021: valid BREP, 1 solid(s), one shell each (no stray bodies) | 1 solids, valid | 1 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | heat_fin1021_1p8_asm1021: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 1 | 0 | PASS |
| 5.3 | heat_fin1021_1p8_asm1021: total volume vs build-notes value (mm3) | 26905.824 | 26905.824 | 0.053811648 | PASS |
| 5.5 | heat_fin1021_1p8_asm1021: single-solid file: STEP product name (cosmetic observation) | info | ['Open CASCADE STEP translator 7.9 1'] | 0 | NOTE |
| 5.0b | heat_fin1021_0p019_asm1021: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | heat_fin1021_0p019_asm1021: valid BREP, 1 solid(s), one shell each (no stray bodies) | 1 solids, valid | 1 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | heat_fin1021_0p019_asm1021: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 1 | 0 | PASS |
| 5.3 | heat_fin1021_0p019_asm1021: total volume vs build-notes value (mm3) | 4093.075 | 4093.075 | 0.01 | PASS |
| 5.5 | heat_fin1021_0p019_asm1021: single-solid file: STEP product name (cosmetic observation) | info | ['Open CASCADE STEP translator 7.9 2'] | 0 | NOTE |
| 5.0b | thermal_station1021_fin1p8: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | thermal_station1021_fin1p8: valid BREP, 13 solid(s), one shell each (no stray bodies) | 13 solids, valid | 13 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | thermal_station1021_fin1p8: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 13 | 0 | PASS |
| 5.3 | thermal_station1021_fin1p8: total volume vs build-notes value (mm3) | 313249.667 | 313249.668 | 0.626499334 | PASS |
| 5.4 | thermal_station1021_fin1p8: every component named (none empty/None), volumes sum to file total | all named | 13 names, none None=True, sum V 313249.667 | 0 | PASS |
| 5.0b | thermal_station1021_fin0p019: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | thermal_station1021_fin0p019: valid BREP, 13 solid(s), one shell each (no stray bodies) | 13 solids, valid | 13 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | thermal_station1021_fin0p019: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 13 | 0 | PASS |
| 5.4 | thermal_station1021_fin0p019: every component named (none empty/None), volumes sum to file total | all named | 13 names, none None=True, sum V 290360.803 | 0 | PASS |
| 5.0b | thermal_station1021_detailed_fin1p8: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | thermal_station1021_detailed_fin1p8: valid BREP, 18 solid(s), one shell each (no stray bodies) | 18 solids, valid | 18 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | thermal_station1021_detailed_fin1p8: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 18 | 0 | PASS |
| 5.4 | thermal_station1021_detailed_fin1p8: every component named (none empty/None), volumes sum to file total | all named | 18 names, none None=True, sum V 305606.322 | 0 | PASS |
| 5.0b | nema17_thermal: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | nema17_thermal: valid BREP, 6 solid(s), one shell each (no stray bodies) | 6 solids, valid | 6 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | nema17_thermal: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 6 | 0 | PASS |
| 5.3 | nema17_thermal: total volume vs build-notes value (mm3) | 60241.53 | 60241.525 | 0.12048305999999999 | PASS |
| 5.4 | nema17_thermal: every component named (none empty/None), volumes sum to file total | all named | 6 names, none None=True, sum V 60241.525 | 0 | PASS |
| 5.0b | nema17_thermal_fin1p8_asm1021: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | nema17_thermal_fin1p8_asm1021: valid BREP, 6 solid(s), one shell each (no stray bodies) | 6 solids, valid | 6 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | nema17_thermal_fin1p8_asm1021: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 6 | 0 | PASS |
| 5.3 | nema17_thermal_fin1p8_asm1021: total volume vs build-notes value (mm3) | 60241.53 | 60241.525 | 0.12048305999999999 | PASS |
| 5.4 | nema17_thermal_fin1p8_asm1021: every component named (none empty/None), volumes sum to file total | all named | 6 names, none None=True, sum V 60241.525 | 0 | PASS |
| 5.0b | nema17_thermal_fin0p019_asm1021: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | nema17_thermal_fin0p019_asm1021: valid BREP, 6 solid(s), one shell each (no stray bodies) | 6 solids, valid | 6 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | nema17_thermal_fin0p019_asm1021: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 6 | 0 | PASS |
| 5.3 | nema17_thermal_fin0p019_asm1021: total volume vs build-notes value (mm3) | 60241.53 | 60241.525 | 0.12048305999999999 | PASS |
| 5.4 | nema17_thermal_fin0p019_asm1021: every component named (none empty/None), volumes sum to file total | all named | 6 names, none None=True, sum V 60241.525 | 0 | PASS |
| 5.0b | encoder1021_magnet_cap_v2_m4: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | encoder1021_magnet_cap_v2_m4: valid BREP, 1 solid(s), one shell each (no stray bodies) | 1 solids, valid | 1 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | encoder1021_magnet_cap_v2_m4: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 1.50e-15, dbbox 0.00e+00, solids 1 | 0 | PASS |
| 5.3 | encoder1021_magnet_cap_v2_m4: total volume vs build-notes value (mm3) | 531.941 | 531.941 | 0.01 | PASS |
| 5.5 | encoder1021_magnet_cap_v2_m4: single-solid file: STEP product name (cosmetic observation) | info | ['Open CASCADE STEP translator 7.9 1'] | 0 | NOTE |
| 5.0b | encoder1021_magnet_cap_v2_m4_asm1021: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | encoder1021_magnet_cap_v2_m4_asm1021: valid BREP, 1 solid(s), one shell each (no stray bodies) | 1 solids, valid | 1 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | encoder1021_magnet_cap_v2_m4_asm1021: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 0.00e+00, dbbox 0.00e+00, solids 1 | 0 | PASS |
| 5.3 | encoder1021_magnet_cap_v2_m4_asm1021: total volume vs build-notes value (mm3) | 531.941 | 531.941 | 0.01 | PASS |
| 5.5 | encoder1021_magnet_cap_v2_m4_asm1021: single-solid file: STEP product name (cosmetic observation) | info | ['Open CASCADE STEP translator 7.9 1'] | 0 | NOTE |
| 5.0b | encoder1021_magnet_cap_v2_m4_peg1p9: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | encoder1021_magnet_cap_v2_m4_peg1p9: valid BREP, 1 solid(s), one shell each (no stray bodies) | 1 solids, valid | 1 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | encoder1021_magnet_cap_v2_m4_peg1p9: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 1.24e-15, dbbox 0.00e+00, solids 1 | 0 | PASS |
| 5.3 | encoder1021_magnet_cap_v2_m4_peg1p9: total volume vs build-notes value (mm3) | 502.312 | 502.312 | 0.01 | PASS |
| 5.5 | encoder1021_magnet_cap_v2_m4_peg1p9: single-solid file: STEP product name (cosmetic observation) | info | ['Open CASCADE STEP translator 7.9 2'] | 0 | NOTE |
| 5.0b | encoder1021_magnet_cap_v2_m4_peg1p9_asm1021: STEP length unit is millimetre | True | True | 0 | PASS |
| 5.1 | encoder1021_magnet_cap_v2_m4_peg1p9_asm1021: valid BREP, 1 solid(s), one shell each (no stray bodies) | 1 solids, valid | 1 solids, valid=True, 1 shell each=True | 0 | PASS |
| 5.2 | encoder1021_magnet_cap_v2_m4_peg1p9_asm1021: re-export + reimport: volume (relative) and bbox (mm), solid count | dV/V <= 1e-6, dbbox <= 1e-4 | dV/V 1.13e-16, dbbox 0.00e+00, solids 1 | 0 | PASS |
| 5.3 | encoder1021_magnet_cap_v2_m4_peg1p9_asm1021: total volume vs build-notes value (mm3) | 502.312 | 502.312 | 0.01 | PASS |
| 5.5 | encoder1021_magnet_cap_v2_m4_peg1p9_asm1021: single-solid file: STEP product name (cosmetic observation) | info | ['Open CASCADE STEP translator 7.9 2'] | 0 | NOTE |
| 9.1 | control: screw_1 moved -0.1 mm in y must show overlap with the slip-in (head annulus 14.137 x 0.1 = 1.41 mm3) | 1.414 | 1.414 | 0.05 | PASS |
| 9.1b | control: same displaced screw also overlaps the motor hole bottom (pi x 1.5^2 x 0.1 = 0.71 mm3) | 0.707 | 0.707 | 0.05 | PASS |
| 9.2 | control: screw_1 shifted 0.15 mm in x: shank-to-fin distance must drop to ~0.05 | 0.05 | 0.05 | 0.01 | PASS |
| 9.3 | control: standard cap (end 22.6) vs the 23.517 shaft must collide (>5 mm3) | > 5 | 16.81 | 0 | PASS |
| 9.4 | control: contact_area() of two bodies 300 mm apart is 0 | 0.0 | 0.0 | 1e-06 | PASS |
| 9.5 | control: contact_area() of the real motor_block / fin_in pair = 1300.55 (the detector sees a true contact) | 1300.548 | 1300.548 | 0.01 | PASS |
