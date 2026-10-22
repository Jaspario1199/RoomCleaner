# Encoder casing and magnet cap for the 10/21 wall assembly (spec, lead, 2026-10-22)

**Request (Jasper, 10/21):** "make the cylinder caps to hold the magnet and build the encoder casing that is fastened into the
divot with holes on the face of the slip-in mount". Reference: `solidworks/v4_assembly_2026-10-21/Assem_laundry_v3_step_1021.STEP`,
whose parts are extracted to `cad/reference/station_1021/` (`python -m cad.reference.station_1021.extract`).

**Purchased parts (Jasper, 10/21):**
- **Board:** UMLIFE AS5600 module (Amazon, bought Oct 18). 23 × 23 mm PCB, AS5600 SOIC-8 at the board centre,
  four corner mounting holes, through-hole pads along two opposite edges: DIR / SCL / SDA / GPO on one edge, VCC / OUT / GND on
  the other.
- **Magnet:** the diametric magnet that ships with the board, nominally Ø6 × 2.5 mm.

## 1. Frame

All coordinates are in the **v3 station frame**, which is the slip-in mount's own frame (`cad/reference/station_v3/extract.py`):
- origin on the motor shaft axis, in the slip-in's motor-plate face (y = 0);
- +y along the shaft toward the spool;
- +z up;
- +x out of the wall into the room.

The 10/21 extraction (`cad/reference/station_1021/`) is the same frame shifted up by 2.64 mm: there the slip-in sits higher in
the wall mount, and the motor axis is at z = +2.64. **Subtract (0, 0, 2.64)** from every `station_1021` part to put it in this frame.
In this frame the slip-in mount is identical to v3 (same volume, 217 693 mm³).

## 2. Interfaces measured from the CAD

| feature | value (station frame, mm) | source |
|---|---|---|
| spool flanges | Ø36, y 7-10 and **23-26**; core Ø15, y 10-23 | station_1021 Spool1011 |
| spool bore | Ø5.30 with a D-flat at x = +2.15 (0.5 mm deep), through, y 7-26 | Spool1011 faces |
| motor shaft end | y = 22.0 (the motor sits 2 mm back behind the heat fin, y −2-0) | station_1021 Motor_Reference, Heat_horn |
| **empty bore at the spool's outer end** | y 22.0-26.0 (4.0 mm deep) | the two rows above |
| divot (recess) | 24.0 × 24.0, R1.0 concave corners, 1.0 deep (x −22.1 to −21.1), centred at y = 45.0, z = 0 | Slipin_mount_piecev3 |
| divot holes | 4 × Ø3.46, 4.0 deep (x −26.1 to −22.1), at y = 40.25 / 49.75, z = ±4.75 (9.5 mm square) | Slipin faces |
| back-plate face the divot is in | x = −21.1, normal +x | Slipin faces |

The divot holes are Ø3.46 × 4 deep. That suits an M2.5 heat-set insert, or an M3 screw tapping into a printed hole only if
they are drilled smaller. **Ask Jasper what goes in them.** The casing uses Ø3.4 clearance holes, which pass both M2.5 and M3.

## 3. Magnet cap ("cylinder cap"), one per station: print 5 (4 + spare)

- **Peg:** fills the empty end of the bore and keys on the D-flat so the cap turns with the spool, centred on the shaft axis.
  - Nominal Ø5.10 with its flat at x = +2.05.
  - Three axial crush ribs about 0.15 mm high, so it presses into the printed Ø5.3 bore.
  - Length 3.4 mm, which leaves 0.6 mm to the shaft end.
- **Head:** Ø14.0 × 3.3 mm disc against the spool's outer face (y 26.0 to 29.3).
  - The magnet pocket opens toward +y, on the axis: Ø(MAGNET_D + 0.2), depth MAGNET_T + 0.05. With Ø6 × 2.5: Ø6.2 × 2.55.
  - The magnet face sits flush at **y = 29.3**.
  - A 0.8 mm pry notch at the rim for removal.
- **Glue:** a drop of CA on the magnet. The head must not touch anything stationary.

## 4. Encoder casing, one per station: print 5

- **Air gap:** magnet face to chip face **1.5 mm** (AS5600 range about 0.5-3 mm). That puts the chip face at **y = 30.8**, on the axis.
- **Board stack, chip side toward −y:**
  - chip face 30.8;
  - PCB front face 32.25 (assumed chip height 1.45, to be measured);
  - PCB back face 33.85 (assumed PCB thickness 1.6, to be measured).
- **Board pocket:** 23.4 × 23.4 (0.2 clearance per side), centred on the axis, so the board outline locates the chip on the
  axis and no hole positions are needed.
  - **Front stops:** four corner tabs, about 3 × 3, at the PCB corners, the mounting-hole areas, which carry no parts.
    There is no full ledge: the SMD resistors and capacitors sit near the edges.
  - **Retention from the back:** two snap hooks on the two edges without pads, or a small screwed retainer. The two pad edges
    stay open, so wires can be soldered to the back and exit backward.
  - Pins in the board's corner holes are optional, off until the hole spacing is measured (parameter).
- **Frame:** 2 mm walls around the pocket (outer about 27.4 × 27.4), front face of the tabs at y ≥ 31.0.
  - The rotating cap (Ø14, y ≤ 29.3) must keep at least 1.0 mm axial and radial clearance to every casing surface.
  - The chip itself is the only thing within 1.5 mm.
- **Foot:**
  - 23.6 × 23.6 with corner radius ≥ 1.2 (it must clear the divot's concave R1.0), keyed 1.0 mm into the divot, standing
    3 mm proud of the plate face (x −22.1 to −18.1).
  - Four Ø3.4 holes at the divot holes.
  - Screw heads on the foot's +x face, reachable from the room side: keep the region above the holes open.
- **Bridge** from the foot to the frame's −x side. Size it for stiffness, so that a 1 N push on the frame moves the chip less
  than 0.1 mm (hand calculation in the build notes).
- **Wires:** leave a notch or channel for 5 thin wires (VCC, GND, SDA, SCL, DIR) from the board's back toward the station board.

## 5. Constraints and checks

- **Materials:** PETG; FDM-printable without supports, or with minimal supports; orientation chosen and stated. No overhang
  above 45° over the pocket.
- **Clearance, using the `station_1021` parts shifted into this frame:**
  - no interference with Slipin_mount_piecev3 except the intended foot-in-divot contact, Shell_Casing, Spool1011 (rotating:
    sweep it), Motor_Reference or Heat_horn;
  - at least 1.0 mm to the shell's inner faces;
  - the line path stays clear: the line winds on the core between the flanges (y 10-23), and nothing may enter y < 26 within
    r 19 of the axis.
- **Parameters:** everything in `cad/params.py` under an `ENC1021_*` block, including MAGNET_D, MAGNET_T, PCB_SIZE,
  PCB_THICK, CHIP_H, CHIP_OFFSET (default 0, 0) and AIR_GAP. When Jasper measures his parts, a change in one place regenerates
  both parts.
- **Outputs:**
  - `exports/step|stl/encoder1021_casing.*` and `encoder1021_magnet_cap.*`;
  - an assembly preview with the station parts;
  - standard renders to `renders/encoder1021/`;
  - build notes `verification/encoder1021_build_notes.md`.
  Then an independent `geometry-verifier` report.

## 6. To measure (Jasper), before printing all five

1. Board: PCB thickness; chip height above the PCB; chip centre relative to the board edges (expected centred); hole diameter
   and centre spacing.
2. Magnet: diameter and thickness (calipers).
3. The hardware in the divot holes (insert or screw size).
4. Then print **one** cap and **one** casing first and check the fit: cap press-fit in the spool, board in the pocket, foot in
   the divot. Afterwards, check the AS5600 magnet-strength status bits over a full spool turn (MD set, ML/MH clear).
