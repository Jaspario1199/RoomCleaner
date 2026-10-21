# Winch station Rev D, as soldered: KiCad 7 project

One A3 schematic, a netlist, a PDF/PNG, and a no-routing PCB (ratsnest only) of the
station perfboard (5 x 7 cm, 24 columns A-X x 18 rows 01-18, 2.54 mm). Everything is
generated from `../perfboard_layout.py`, the as-soldered, net-checked design. If the
Rev D schematic (`../draw_schematic.py`, `../README.md`) and the perfboard file disagree,
the perfboard file wins (list below). Current limit: DECISIONS.md **D30** (Vref about
0.85 V, about 1.06 A), not the 1.35 A / 1.08 V of the Rev D README.

## Open it

KiCad 7.0.x: open `RoomCleaner_Station_RevD.kicad_pro`.
The schematic is `RoomCleaner_Station_RevD.kicad_sch` (A3, one sheet), the PCB
`RoomCleaner_Station_RevD.kicad_pcb`. `sym-lib-table` / `fp-lib-table` name the stock
libraries through `${KICAD7_SYMBOL_DIR}` / `${KICAD7_FOOTPRINT_DIR}` and the project
libraries `RoomCleaner.kicad_sym` / `RoomCleaner.pretty` through `${KIPRJMOD}`.
The PCB shows the connections as a ratsnest (no tracks: the copper on the real board is
bare wire and solder runs, see `../PERFBOARD_LAYOUT.md`).

| File | What |
|---|---|
| `build_kicad.py` | generator for everything below (also runs the exports, the PCB, DRC, the net check) |
| `perfboard_data.py` | the bridge to `perfboard_layout.py`: loads its tables, holds the one hole-to-pin map |
| `check_netlist.py` | compares the exported netlist (and the PCB) with the perfboard nets; prints PASS/FAIL |
| `run_erc_xvfb.py` | runs KiCad's real ERC headlessly (see ERC below) |
| `RoomCleaner_Station_RevD.kicad_pro/.kicad_sch/.kicad_pcb` | project, schematic, PCB |
| `RoomCleaner.kicad_sym`, `RoomCleaner.pretty/` | custom XIAO ESP32-C3 and DROK buck symbols + footprints |
| `sym-lib-table`, `fp-lib-table` | project library tables |
| `RoomCleaner_Station_RevD_netlist.xml` | `kicad-cli sch export netlist --format kicadxml` |
| `RoomCleaner_Station_RevD.pdf`, `..._preview.png` | `kicad-cli sch export pdf`, `pdftoppm -r 110 -png` |
| `netlist_check.txt` | output of `check_netlist.py --pcb` (PASS) |
| `RoomCleaner_Station_RevD_erc.rpt` | KiCad 7 ERC report (0 errors, 0 warnings) |
| `RoomCleaner_Station_RevD_drc.rpt`, `..._pcb_preview.png` | PCB DRC report; trimmed render of the placed board |

## Regenerate

```
cd docs/electrical/station_revD_20261021/kicad
/usr/bin/python3 build_kicad.py            # project, netlist, PDF, PNG, PCB, DRC, netlist_check.txt
/usr/bin/python3 build_kicad.py --erc      # same + real ERC through eeschema under Xvfb (about 1 min)
/usr/bin/python3 build_kicad.py --no-pcb   # schematic side only (also --no-export, --no-drc)
python3 check_netlist.py                   # netlist only, stdlib only; add --pcb with /usr/bin/python3
```

Use `/usr/bin/python3` (the one with `pcbnew`). `perfboard_layout.py` is **not imported**:
importing it runs its matplotlib code and rewrites `perfboard_layout.png/.pdf`. Instead
`perfboard_data.py` executes only its table/check section (above the `# --- drawing`
marker) and never writes anything outside this folder. Schematic, libraries and project
files are deterministic (fixed UUID namespace); the netlist XML carries a date and pcbnew
assigns fresh item UUIDs to the PCB on every run.

Where a perfboard fact had to be turned into a schematic fact, the map lives in one place,
`perfboard_data.py`: `HOLE_PIN` (hole -> connector/part pin, with the perfboard label as a
cross-check), `XIAO_PIN`, `A4988_PIN` + `A4988_GND_BY_HOLE`, and `NET_NAME`
(perfboard `12V`/`3V3`/`5V` -> the power symbols `+12V`/`+3V3`/`+5V`; `PGND` is folded into
`GND` by the perfboard file's own `NETMAP`). Every hole in `PINS` must be mapped exactly once,
and the generator checks that the XIAO / A4988 pin names match the perfboard labels. The PCB
step then places each footprint with pad 1 on its hole and checks that **every pad of every
footprint lands on the hole the map says** (worst error 0.04 mm, C1), which independently
confirms the pad numbering of the stock A4988 footprint.

## Results

* **ERC (KiCad 7.0.11): 0 errors, 0 warnings.** Note: `kicad-cli` 7.0.11 has **no**
  `sch erc` (or `pcb drc`) subcommand; both arrived in KiCad 8. The ERC was therefore run with
  the real eeschema ERC engine by driving the GUI under Xvfb (`run_erc_xvfb.py`: Inspect >
  Electrical Rules Checker > Run ERC > Save, on a temporary copy of the project and a temporary
  config dir). KiCad's only ignored test is its default-off "SPICE model issue". To show the run
  is not vacuous, the same script on a copy with the three PWR_FLAGs and one wire removed
  reports 4 errors (pin not connected, 3x power pin not driven). PWR_FLAGs: +12V and GND at J1,
  +5V at JP1's XIAO side. The stock-symbol copies embedded in the schematic match the library
  (no "symbol doesn't match library" warning).
* **Netlist: PASS** (`netlist_check.txt`): 16 nets / 55 connected pins identical, per net, to the
  perfboard; 6 pins unconnected on both sides (U1 EN, XIAO D0 D6 D7 D8 D9); 14 components.
  Mutation tests (a pin dropped from SDA, a pin moved from STEP to EN) print FAIL.
* **PCB / DRC:** 70 x 50 mm outline, hole A01 at (101.6, 76.2) mm with equal margins to the
  board edge (5.79 / 3.41 mm), all 14 footprints on their holes, 22 nets (16 + 6 `unconnected-`),
  no routing. DRC runs through `pcbnew.WriteDRCReport` (same engine as the GUI): **0 errors
  other than the 39 "unconnected items" (the ratsnest)**, 5 warnings: 3 courtyard overlaps on
  adjacent holes (JP1/D1, JP1/U3, R4/J3; the bodies do not collide, the stock 0.5 mm connector
  courtyard margins do) which the project sets to *warning* (`courtyards_overlap` in
  `.kicad_pro`), and 2 silkscreen overlaps between neighbouring outlines around JP1 / U3 (x 142-146 mm). Designators are on the
  fab layer to keep the silk readable. Footprints carry the schematic symbol UUID path so
  "Update PCB from Schematic" should match them (not exercised in the GUI).

## What is off-board

Drawn as dashed blocks next to their connectors, not as parts: **AS5600 encoder** on J5
(C17-F17: 3V3, GND, SDA, SCL), **KW12-3 NC switch** on J3 (H17 NC -> HOME, I17 COM -> GND),
the **NEMA 17 motor** on J2 (X05-X08), the **12 V supply branch** on J1 (+ its supply-end fuses
F0-F4, which are notes only) and the XIAO's USB cable. The DROK module is modeled as a 5-pin
header part (pads only; its body is not modeled).

## Disagreements Rev D schematic vs perfboard (perfboard followed)

1. Current limit: Rev D README / sheet 3 / sheet 5 say 1.35 A, Vref 1.08 V (D29). The sheet
   follows D30: **Vref 0.85 V, about 1.06 A**; 1.08 V is noted as not reachable on this carrier.
2. Encoder: sheet 3 draws AS5600 DIR -> GND and OUT open at the encoder. The perfboard J5 has
   4 pins only (3V3, GND, SDA, SCL), so those two connections are on the encoder board, not
   the perfboard.
3. Test points TP0-TP4 (sheets 1, 2, 4) are not parts on the perfboard; omitted.
4. Grounds: Rev D shows one GND. The perfboard has two A4988 GND pads (pad 7 next to VMOT =
   motor return `PGND`, pad 1 = logic) joined by wire S03-O11; after `NETMAP` that is one net,
   drawn as one `GND`.
5. Net names: Rev D sheet 4 (`+12_STATION`, `+5_BUCK`, `DIODE OUTPUT`, `XIAO_5V`, `ENABLE`,
   `HOME_NC`) are `+12V`, `5VB`, `5VD`, `+5V`, `EN`, `HOME` here.
6. Packages as built: R2/R3 stand upright (2.54 mm holes), R1/R4 lie (7.62 mm); J1 uses a
   5.08 mm terminal pitch (X01 / X03), not a 2.54 mm header.

## Known limits

* Footprints: stock footprints except the XIAO (outline approximate) and the DROK header.
  R = DIN0204 (3.6 mm) so the 2.54 mm-pitch courtyards of R1-R3 do not collide; any 1/8-1/4 W
  10k fits electrically. C1 = `CP_Radial_D6.3mm_P2.50mm` (2.50 vs 2.54 mm hole pitch, 0.04 mm
  off); the real 100 uF/50 V can may be larger. J1 uses the 5.08 mm terminal footprint instead
  of a pin header because X01-X03 are 5.08 mm apart. No 3D models for the custom footprints.
* Resistors and JP1 are symmetric; their pin 1/2 assignment is arbitrary (pin 1 = upper lead in
  the drawing, JP1 pin 1 = diode side).
* The schematic is a connectivity drawing of the soldered board. ERC and the net check prove it
  matches `perfboard_layout.py`; they do not prove `perfboard_layout.py` matches the hardware
  (meter-check the board, see the power-up note on the sheet). The DROK revision is unverified.
* The PCB is a placement / ratsnest aid for the perfboard, not a fabrication board (no tracks,
  no mounting holes, no copper). 3 courtyard overlaps are downgraded to warnings on purpose.
* `run_erc_xvfb.py` is coordinate-based (tested on KiCad 7.0.11, Xvfb 1600x1000, fresh config)
  and needs `Xvfb`, `eeschema`, `libX11`, `libXtst`. With KiCad 8+ use `kicad-cli sch erc`.
