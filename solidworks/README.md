# SolidWorks design (generation 2, October 2026)

This folder holds the **SolidWorks redesign** that Jasper built in October 2026
after the CadQuery generation-1 design (`cad/`, Aug–Sep 2026). Generation 1 is
**not deleted or superseded in place**: its parts, tests, verification reports
and decisions (D1–D14) stay in the repo as the design record the redesign grew
out of. See `docs/DESIGN_HISTORY.md` for what changed and why.

Source of truth for these files is Jasper's Google Drive project folder. The
repo copies are for review and for the presentation. Native SolidWorks files
(`.SLDPRT`, `.SLDASM`) open only in SolidWorks; `.STEP` files open anywhere and
are what the design review measures.

## Manifest

Status column: **in repo** = copied byte-exact and size-checked; **Drive** =
listed here but not yet copied (sync step below).

### v1 — 2026-10-07 (first SolidWorks pass)

| File | Bytes | What it is | Status |
|---|---|---|---|
| `Laundry_Robot_Assem1.SLDASM` | 264731 | first full-robot assembly | in repo |
| `Wall Mount.SLDPRT` | 148696 | fixed wall frame, v1 | in repo |
| `Slipin_mount_piece.SLDPRT` | 224459 | removable motor housing that slides into the frame, v1 | in repo |
| `Shell_Casing.SLDPRT` | 199899 | station cover (modified 10-08) | in repo |
| `Spool_V1_Short_22mm.SLDPRT` / `.step` | 101382 / 81781 | shortened spool, 22 mm | in repo |
| `Spool_V2.SLDPRT` / `.step` | 112516 / 93733 | spool iteration 2 | in repo |
| `Bead.SLDPRT` | 138260 | homing stopper bead | in repo |
| `Motor_Reference.SLDASM` / `.step` | 128299 / 27129 | NEMA 17 reference body | step **in repo** (`v1_2026-10-07/`) |
| `KW12_3_Approximate_Reference.step` | 38464 | limit-switch reference body | **in repo** (`v1_2026-10-07/`) |

### v2 — 2026-10-11

| File | Bytes | What it is | Status |
|---|---|---|---|
| `Wall Mount.SLDPRT` / `Wall Mount_Step.STEP` | 191533 / 185647 | wall frame, v2 | in repo |
| `Slipin_mount_piece.SLDPRT` / `_step.STEP` | 243517 / 237957 | slide-in housing, v2 | in repo |
| `Spool1011.SLDPRT` / `Spool1011_Step.STEP` | 115728 / 52617 | spool, 11 Oct | STEP **in repo** (`v2_2026-10-11/`) |
| `RoomCleaner_BOM_1_2_3.xlsm` | 34725 | bill of materials (macro workbook) | Drive |

### v3 — 2026-10-18 (current wall station)

| File | Bytes | What it is | Status |
|---|---|---|---|
| `Wall_Mount_v3.STEP` | 251650 | wall frame, v3 | in repo |
| `Slipin_mount_piece v3.STEP` | 314062 | slide-in housing, v3 | in repo |
| `Shell_Casing.STEP` | 302679 | station cover, v3 export | in repo |
| `Spoolv3.STEP` | 55157 | spool, v3: Ø36 × 22, Ø15 core, 16 mm drum, Ø5.45 D-bore | **in repo** (`v3_2026-10-18/`) |

### Gripper — Claw_V1 (2026-10-12) and V5 (2026-10-18/19)

| File | Bytes | What it is | Status |
|---|---|---|---|
| `Claw_V1/LaundryGripperAssem1.SLDASM` | 231769 | first clamp gripper assembly | in repo |
| `Claw_V1/Gripper_Electric_Housing_Base.SLDPRT` | 362223 | electronics/camera housing, V1 | in repo |
| `V5/LaundryGripperAssem1.SLDASM` | 781748 | current clamp gripper assembly | in repo |
| `V5/Gripper_Electric_Housing_Base.SLDPRT` | 331059 | electronics/camera housing, V5 | in repo |
| `V5/Gripper_gear_housing.SLDPRT` | 123386 | gear housing | in repo |
| `V5/Simple_18T_Pinionvlast.SLDPRT` | 402486 | 18-tooth servo pinion | in repo |
| `V5/06_compound_54T_24T.SLDPRT` | 1467970 | compound gear, 54T driven + 24T drive | in repo |
| `V5/24T_Follower.SLDPRT` | 479845 | 24-tooth follower (second jaw, reversed) | in repo |
| `V5/Griper Cylinder.SLDPRT` | 306886 | rigid extension between housing and clamp | in repo |

All files except the BOM workbook are in the repo, size-checked against
Drive; STEP files parse as valid single solids. The BOM (`.xlsm`) came back
from Drive in a form that cannot be streamed to disk here — copy it by hand.
The folders are `v1_2026-10-07/`, `v2_2026-10-11/`, `v3_2026-10-18/`,
`claw_v1_2026-10-12/`, `gripper_v5_2026-10-19/`.
`Motor_Reference.step` was transcribed rather than streamed; it parses and
matches size, but re-download it if byte-exactness matters.

## Keeping this folder in sync

When the SolidWorks files change, refresh this folder from a machine that has
both the Drive folder and the repo:

1. In Drive, right-click the RoomCleaner project folder → Download (zip).
2. Unzip into `solidworks/` keeping the version folders
   (`v1_2026-10-07/`, `v2_2026-10-11/`, `v3_2026-10-18/`, `claw_v1_2026-10-12/`,
   `gripper_v5_2026-10-19/`).
3. **Also export STEP for every V5 gripper part and the V5 assembly**
   (File → Save As → STEP AP214). The design review cannot measure SLDPRT.
4. `git add solidworks && git commit -m "Sync SolidWorks gen-2 files" && git push`

Files over ~50 MB should go through Git LFS; nothing here is close.

### Accessory — motor heat plate (2026-10-19, review R11)

| File | What it is |
|---|---|
| `heat_plate/motor_heat_plate.step` | 100 × 100 × 3 mm aluminium spreader/fin plate, sandwiched between motor flange and the v3 PETG motor tab |
| `heat_plate/motor_heat_plate.dxf` | 2D outline + 5 holes for laser / waterjet cutting |
| `heat_plate/motor_heat_plate_drawing.png` | dimensioned drawing with hole table |

Generated by `cad/parts/motor_heat_plate.py` (run with `/usr/bin/python3 -m cad.parts.motor_heat_plate`).
