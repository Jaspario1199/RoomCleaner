# RoomCleaner — 3D-Printed Parts (CAD)

Every printable part, as **parametric CadQuery scripts** that export genuine
**STEP** files (open in Fusion 360 / SolidWorks / FreeCAD / Onshape) and **STL**
files (ready to slice). The generated files are committed, so you can print
without installing anything.

```
cad/
  params.py         # ← edit YOUR dimensions here (shaft dia, line dia, servo…)
  parts/*.py        # one parametric script per part
  export_all.py     # regenerate everything + an assembled gripper preview
  lib.py            # STEP/STL export + PNG preview helper
  step/  stl/  previews/   # generated output (committed)
```

## Parts list

| Part | What it is | Print | Material |
|------|-----------|-------|----------|
| `winch_spool` | Drum the Dyneema winds onto; mounts on the motor shaft | ×4 | PLA/PETG |
| `motor_mount` | Cradles the gear motor in a ceiling corner | ×4 | PETG |
| `corner_guide` | U-bracket holding the corner pulley | ×4 | PETG |
| `effector_frame` | Body that hangs on the 4 cables; holds servo + camera | ×1 | PETG |
| `tentacle_hub` | Disc carrying the ring of fingers; routes tendons | ×1 | PETG |
| `tentacle_finger` | Tendon-driven curling "tentacle" finger | ×5 | **TPU 95A** |
| `camera_mount` | Pi Camera bracket for the effector | ×1 | PLA/PETG |

## Regenerate after changing dimensions

Edit `cad/params.py` (especially `MOTOR_SHAFT_DIA`, `DYNEEMA_DIA`) then:

```bash
pip install -r requirements-cad.txt
python -m cad.export_all
```

## Print settings

- **Structural parts** (spool, motor mount, corner guide, frame, hub): **PETG**,
  0.2 mm layers, **4 walls**, **40–50% infill**. These carry real load.
- **Tentacle fingers**: **TPU 95A**, 0.2 mm, 3 walls, 15–20% infill. Lay each
  finger on its **flat dorsal (back) face** so the V-notches open upward — no
  supports. Slow down to ~20–30 mm/s for clean TPU.
- Most parts print support-free in the orientation described in each script's
  docstring.
- Tune `CLEARANCE` in `params.py` if press-fits are too tight/loose on your printer.

## Assembling the tentacle gripper

1. Bolt the **servo (MG996R)** into the `effector_frame` pocket, horn facing down.
2. Bolt the **tentacle_hub** under the frame (4× M3).
3. Insert each **tentacle_finger** base into a hub pocket; retain with one M3.
4. Thread one Dyneema/line **tendon** through each finger's channel, tie off at
   the tip, route the other end through the hub guide hole to the servo horn.
5. Tie all tendons to the horn so one servo sweep curls all fingers inward.
6. Tie the **four winch cables** to the four corner eyes of the frame.
7. Clip the **Pi Camera** (`camera_mount`) to the frame edge, facing down.

Mount fingers with their **notched (ventral) side facing inward** so they curl
toward the center and wrap the laundry.

## ⚠️ Safety: do NOT print these

The **load-bearing ceiling anchors** (the eye screws / lag bolts into your
joists) must be **metal**, driven into solid wood — never a printed part. The
whole robot hangs from them. `motor_mount` and `corner_guide` bolt *to* those
metal anchors; the anchors themselves stay steel. Same for the emergency-stop
hardware.
