# Claw Rev B: KiCad 7 schematic

One A3 schematic of the claw's point-to-point wiring, drawn from the net table of
[`../CLAW_REVB_SPEC.md`](../CLAW_REVB_SPEC.md) (authority: DECISIONS.md D31 and the pin map in
`firmware/claw_s3/claw_s3.ino`). Status as in the spec: **design, not yet built or bench-tested.**
There is no PCB: the claw is hand-wired.

## Open it

KiCad 7.0.x: open `RoomCleaner_Claw_RevB.kicad_pro`. The libraries are in `sym-lib-table` /
`fp-lib-table` (stock libraries through `${KICAD7_SYMBOL_DIR}` / `${KICAD7_FOOTPRINT_DIR}`, project
libraries `RoomCleanerClaw.kicad_sym` / `RoomCleanerClaw.pretty` through `${KIPRJMOD}`).

| File | What |
|---|---|
| `claw_spec.py` | the spec's parts table, net table and unconnected line, encoded once (comment points at the spec); also the spec-words-to-pin-number map |
| `build_kicad.py` | generator: libraries, schematic, project, netlist, PDF, PNG, net check |
| `check_netlist.py` | compares the exported netlist with `claw_spec.py` net by net; prints PASS/FAIL |
| `run_erc_xvfb.py` | KiCad's real ERC, headless (copy of the station runner for this project) |
| `RoomCleaner_Claw_RevB.kicad_pro/.kicad_sch` | project, schematic |
| `RoomCleanerClaw.kicad_sym`, `RoomCleanerClaw.pretty/` | XIAO ESP32-S3, UBEC and MP1584 modules (IN+, IN-, OUT+, OUT-), USB-C 2S charger (B+, B-), 3-pin servo lead; footprints for the XIAO and the wire modules |
| `RoomCleaner_Claw_RevB_netlist.xml`, `.pdf`, `_preview.png` | `kicad-cli sch export netlist --format kicadxml`, `export pdf`, `pdftoppm -r 110` |
| `netlist_check.txt`, `RoomCleaner_Claw_RevB_erc.rpt` | check output (PASS), ERC report (0 / 0) |

## Regenerate

```
cd docs/electrical/claw_revB_20261021/kicad
/usr/bin/python3 build_kicad.py            # everything + netlist check
/usr/bin/python3 build_kicad.py --erc      # also the real ERC (about 1 min)
python3 check_netlist.py                   # netlist only, stdlib only
```

The s-expression, symbol and footprint helpers are imported from the station generator
(`../../station_revD_20261021/kicad/build_kicad.py`); that folder is read, never written
(bytecode writing is disabled for the import). Stock symbols are embedded unchanged
(`Device:Battery`, `Fuse`, `R`, `C`, `C_Polarized`, `D_Schottky`, `Switch:SW_SPST`, `power:GND`,
`power:PWR_FLAG`). Where the coordinator's list asked for battery / fuse / switch symbols I used the
stock ones; the module, charger, servo-lead and XIAO symbols are project symbols.

## Results

* **Net check: PASS.** 9 nets / 37 connected pins identical to the spec's net table (BAT_POS,
  BAT_FUSED, VBAT_SW, GND, +6V_SERVO, +5V_BUCK, +5V_XIAO, VBAT_SENSE, SERVO_PWM); the 10 XIAO pins
  the spec leaves open (D1, D3-D10, 3V3) carry no-connect flags; every library pin of every part is
  accounted for; 15 parts with the symbols and values of the parts table. Two corrupted netlists
  (a pin dropped from VBAT_SENSE, C4's ground lead moved onto VBAT_SENSE) print FAIL.
* **ERC (KiCad 7.0.11): 0 errors, 0 warnings.** `kicad-cli` 7.0.11 has no `sch erc` (added in KiCad 8),
  so `run_erc_xvfb.py` runs the real eeschema ERC (Inspect > Electrical Rules Checker) under Xvfb on a
  temporary copy of the project; it needs `Xvfb`, `eeschema`, `libX11`, `libXtst`, and its click
  coordinates were tested on 7.0.11 only. The only ignored test is KiCad's default-off "SPICE model
  issue". A copy with the two PWR_FLAGs and one wire removed reports 4 errors. PWR_FLAGs: GND at the
  battery negative, +5V_XIAO at the XIAO 5V pad.
* Net names are local labels (the exported netlist shows them with a leading `/`, which the check
  strips), except GND, a stock power symbol. Rails are labels, not power symbols, so the names match
  the spec exactly (`+6V_SERVO`, `+5V_XIAO`, ...).

## What is a note, not wiring

Per the coordinator and the spec: the **Sense camera board** (factory B2B connector; no header pin
used), the XIAO **BAT pads** (unused), the **USB-C input** of U4 (external 5 V adapter) and the module
enable pins ("if any") are text/graphics on the sheet, not pins. The sheet also carries: D31
reference, the charging rule (charge only with SW1 OFF, attended, non-flammable surface, 8.4 V CC/CV
at <= 1 A, protection PCB must give per-cell protection, 2-wire pack cannot be balance-charged),
"emergency stop is the switched power strip at the stations; SW1 is a service disconnect", the
"Checks" and "Before the first power-up" sections of the spec in short form, and the per-part notes
(BT1 / F1 / SW1 / U1 / U2 / D1 / J2 lead colours).

## Spec observations (the spec was followed; no net changed)

1. The spec has **no J1** (the pack connector it mentions in "Before the first power-up" is not a
   listed part); BT1 is drawn wired straight to F1 and GND. Refs are kept as in the spec (J2 = servo).
2. C2, C3, C4 appear in two nets without a pin; their leads are drawn pin 1 on the signal/rail net,
   pin 2 on GND (`LEAD_PIN` in `claw_spec.py`). R1 top/bottom = pin 1/2, F1 in/out and SW1 in/out =
   pin 1/2, J2 pins 1/2/3 = GND / V+ / signal (drawn with GND at the bottom).
3. The divider top (R1) hangs on VBAT_SW, so with SW1 OFF (charging, or programming over USB) D2 reads
   0 V and the firmware will report low battery. Consistent with "charge with SW1 OFF" but not stated.
4. The XIAO 5V pad sits one 1N5819 drop (roughly 0.3-0.5 V, not measured) below the 5.00 V trimmed at
   U2; the spec trims U2 before connecting but gives no value at the pad.
5. Only F1 (5 A, provisional) and the pack's PCB protect against a short; there is no reverse-polarity
   protection, so the polarity check in step 3 is the only guard. U1 and U2 are drawn as generic
   4-pin modules: check the pin labels printed on the real modules against IN+/IN-/OUT+/OUT-.
6. The spec arithmetic was re-checked: 8.4 V x 100/300 = 2.80 V, 6.8 V -> 2.27 V, 28 uA; 18.5 W /
   0.88 = 21.0 W -> 2.84 A at 7.4 V, 3.09 A at 6.8 V.

## Known limits

* Footprints exist only for the XIAO (outline approximate, same 2 x 7 header layout as the C3 one)
  and the generic wire modules; BT1, F1 and SW1 have none (lead-wired). Passive footprints are generic
  through-hole choices (C1 radial 10 mm, disc ceramics, 0207 resistors), not the purchased parts.
* The connectivity is only as good as the spec; ERC and the net check do not prove the wiring on the
  bench. U4 must still be verified as an 8.4 V CC/CV <= 1 A module before the first charge.
