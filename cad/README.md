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
| `corner_mount` | **Rigid corner anchor plate**: NEMA 17 bracket + pulley ears on one base, screwed to a joist/stud with 3× #10×3" wood screws (D13) | ×4 | PETG |
| `motor_mount` | (superseded by `corner_mount` for the corner install; kept for bench use) | — | PETG |
| `corner_guide` | (superseded by `corner_mount` for the corner install; kept for bench use) | — | PETG |
| `effector_frame` | Hangs on the 4 cables; holds servo, camera, + strap slots for the ESP32 & LiPo (wireless claw) | ×1 | PETG |
| `tentacle_hub` | Disc carrying the ring of fingers; routes tendons | ×1 | PETG |
| `tentacle_finger` | Tendon-driven curling "tentacle" finger | ×5 | **TPU 95A** |
| `camera_mount` | Pi Camera bracket for the effector (close-up cam, Phase 4) | ×1 | PLA/PETG |
| `camera_mount_overhead` | Ceiling bracket for the innomaker 32×32 overhead cam | ×1 | PLA/PETG |
| `standoff` | 40 mm column joining frame to hub (insert both ends) | ×4 | PETG |
| `tendon_drum` | Flanged spool on the servo horn; winds all 5 tendons | ×1 | PETG |
| `electronics_cover` | Screw-down lid over servo + ESP32 + LiPo (switch/USB cutouts) | ×1 | PETG/PLA |

## Regenerate after changing dimensions

Edit `cad/params.py` (especially `MOTOR_SHAFT_DIA`, `DYNEEMA_DIA`) then:

```bash
pip install -r requirements-cad.txt
python -m cad.export_all
```

## Print settings

- **Structural parts** (spool, motor mount, corner guide, frame, hub, standoffs, drum, cover): **PETG**,
  0.2 mm layers, **4 walls**, **40–50% infill**. These carry real load.
- **Tentacle fingers**: **TPU 95A**, 0.2 mm, 3 walls, 15–20% infill. Lay each
  finger on its **flat dorsal (back) face** so the V-notches open upward — no
  supports. Slow down to ~20–30 mm/s for clean TPU.
- Most parts print support-free in the orientation described in each script's
  docstring.
- Tune `CLEARANCE` in `params.py` if press-fits are too tight/loose on your printer.

## Corner-mount assembly note (fleet alignment)

When sliding each `winch_spool` onto its motor shaft, set the gap between the
spool's near flange and the bracket wall to **at most 2 mm** before tightening
the grub screw (a folded piece of paper card ≈1 mm makes a good feeler). The
CAD models the flange flush with the wall; every millimeter of real gap shifts
the drum off the pulley's groove plane by the same amount, and 2 mm is the
budgeted ceiling (verified: ≤2 mm keeps worst-case fleet angle ≈9°, within
tolerance). Don't run the flange rubbing the wall — aim for ~1 mm.

## Assembling the claw (D2–D8 stack-up — matches `claw_assembly.step`)

**Inserts first.** Press M3 heat-set inserts into: both ends of each `standoff`
(8 total) and the 4 cover-tab holes in the frame's top face. (No inserts in TPU.)

1. **Zero the servo.** Power the ESP32 and hit `GET /setup` — the servo parks at
   RELEASE (20°). Screw the round horn into the `tendon_drum`'s top pocket
   (4× Ø2.4 self-taps), then press horn+drum onto the spline in this position
   and lock with the M3 horn screw through the drum's central Ø6.5 hole.
2. **Mount the servo INVERTED**: body above the plate, spline down through the
   frame pocket; ears screw to the plate top (M3 self-tap, 2.8 mm holes).
   The drum now hangs under the plate, tie-off flange facing down.
3. **Standoffs to frame**: M3×8 down through the frame's clearance holes into
   each standoff's TOP insert (bolt circle Ø54, angles 36/108/252/324°).
4. **Fingers into hub** (before the hub goes up): insert each finger from
   BELOW through its slot, **notched (ventral) side facing the hub center**,
   until the shoulder seats on the hub underside; retain with an axial
   **M3×12 + washer** from the hub top into the finger's base tap.
5. **Hub to standoffs**: **M3×16 + washer** up through the hub (head on the
   hub underside) into each standoff's BOTTOM insert.
6. **Tendons** (Dyneema, same 50 lb line): tie off at each fingertip's cross
   hole, run down the finger channel, in through the hub guide hole, up the
   central bore, and tie to the drum's bottom-flange holes — reaching up
   through the hub bore. With the servo still at RELEASE and fingers straight,
   pull each tendon just-taut before knotting; re-tension individually later
   through the same bore access.
7. **Electronics**: set the buck to **6.0 V before connecting the servo**;
   strap the ESP32 (+y band) and LiPo (−y band) with zip ties; wire
   LiPo → switch → buck → servo + ESP32 VIN, common ground.
8. **Cover**: seat over everything, screws into the 4 frame tab inserts;
   switch and USB accessible through the cutouts; the corner notches leave
   the cable bosses exposed.
9. **Cables**: Palomar knot through each corner boss (Ø3.2). The Pi Camera
   (`camera_mount`, Phase 4) clips to the frame edge later.

**First-print validation set (do this before printing everything):** frame,
4× standoff, hub, drum, ONE finger — verify slot fit, shoulder seating, and
~27 mm of tendon travel over the 120° throw, then print the rest.

## Heat-set inserts (brass threaded inserts)

`params.py` has `USE_HEATSET_INSERTS` (default **True**). It controls only the
holes where a screw threads **into printed plastic**:

- **Insert holes:** BOTH ends of each `standoff` (8 inserts — these carry the
  whole gripper) and the 4 cover-tab holes in the frame top. Melt each in with
  a soldering iron + insert tip.
- **Left as clearance / screw-through:** the frame's and hub's Ø-holes on the
  bolt circle (screws pass through into the standoff inserts — the hub's 4 mm
  holes are deliberately loose; the washer seats the head), the servo ear taps,
  and everything that threads into motor/servo metal.
- **TPU parts stay self-tap / use a screw + nut:** heat-set inserts do **not** hold
  in flexible TPU, so the `tentacle_finger` base is not insert-drilled.

Set `USE_HEATSET_INSERTS = False` and re-run `python -m cad.export_all` if you'd
rather self-tap screws straight into the plastic (holes shrink to ~2.8 mm).

## ⚠️ Safety: do NOT print these

The **load-bearing ceiling anchors** (the eye screws / lag bolts into your
joists) must be **metal**, driven into solid wood — never a printed part. The
whole robot hangs from them. `motor_mount` and `corner_guide` bolt *to* those
metal anchors; the anchors themselves stay steel. Same for the emergency-stop
hardware.
