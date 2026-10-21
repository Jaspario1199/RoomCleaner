# Deck v3: what changed from v2 (2026-10-21)

Jasper asked for four changes (10/21):
- equations on the process slides, boxed in a corner, not the centre of the slide;
- a heat-fin slide with the effective-length graph, the chosen length and the fin's look;
- charts built in Google Sheets, with only one or two outside citations and fewer generated graphics;
- manufacturing as its own part of the story (3D printing and the manual mill).

v1 (`docs/presentation/deck/`) and v2 (`docs/presentation/deck_v2/`) are kept unchanged.

## Files

| File | What it is |
|---|---|
| `deck_v3/RoomCleaner_Buntinx_Oct27_v3.pptx` / `.pdf` | the deck: 44 slides, including 4 backups |
| `deck_v3/build_deck_v3.js` | builds the deck (pptxgenjs); validated with the pptx skill's `validate.py` |
| `deck_v3/sheet_export.pdf` | PDF export of the Google Sheet the charts come from |
| `deck_v3/sheet_charts.py` | crops the eight Sheet charts out of that PDF into `deck_v3/fig/sheet_*.png` |
| `deck_v3/make_figures.py` | position-vector figure without its formula line (the formulas are in the slide's box) |

Rebuild: export the Sheet to `deck_v3/sheet_export.pdf`, then run `sheet_charts.py`, `make_figures.py` and the node build.
The commands are in the build script header.

## Google Sheet

"RoomCleaner engineering calculations", owner Jasper:
https://docs.google.com/spreadsheets/d/1UGFnkL1v305WnDYj5aj5zBtgxnxmGP7_TVRN0afZTGs/edit

- **Tabs:** Read me, Cable tension, Winch pull, Heat fin, Motor temperature, Wiring, Bead homing, Floor board, Lift budget, Gears.
- **Formulas:** every result is a formula on its inputs. Inputs are in blue text, links to other tabs in green.
- **Bead homing exception:** the reachable-share column is pasted from `calculations/bead_reach.py`, which grids the working volume; the cell note says so.
- **Changes on 10/21:**
  - the Heat fin tab gained columns F:H: share of a long fin's heat, tanh(mL), for both thicknesses, plus the 95 % line;
  - the Motor temperature chart gained the 60 °C limit line (column E19:E21);
  - all charts were restyled for slides: 520 × 360 px, 14 pt axes, 16 pt titles.

## Slide changes

- **Equation boxes (bottom left):** position vectors (distance formula), statics, winch, wiring, timing skew, slide-in mount,
  cooling, heat fin, bead homing, calibration (least squares), floor board, four-bar/grip, lift budget, printed fits,
  Lewis (backup).
- **Charts from the Sheet:** tension, winch pull, wiring, motor temperature, heat fin, bead reach, floor board, lift budget. Each has a caption naming its tab.
- **Generated graphics removed:**
  - the wiring diagram is replaced by the Sheet chart;
  - the bead-reach plot is replaced by the Sheet chart;
  - the calibration loop is now native slide shapes.
  - Only the position-vector figure is still a generated picture.
- **New slides:**
  - *Heat fin: how much length is useful.* Chart plus the decisions: 0.019 in sheet reaches 95 % of a long fin's heat by 136 mm; the 1/8 in plate by 349 mm; built 200 mm; vertical, motor width, matte black.
  - *Manufacturing* section:
    - *Designing parts to be printed:* PETG, orientation, undersize holes and lead-ins, heat-set inserts, part consolidation.
    - *Print, measure, adjust: the spool:* v1 → v3 bore story.
    - *Machining the heat fin:* shear, one mill setup, ±0.1 mm hole positions, paint, test fit; photos 06, 03, 02, 15.
  - *First test* (in Status): a photo placeholder and what the run checks. It does not say how many stations the first test uses.
  - *Backup: calculations and sources:* the Sheet link and the two references.
- **Citations (two):**
  - Incropera et al., *Fundamentals of Heat and Mass Transfer*, ch. 3 (fin equations);
  - Allegro A4988 datasheet (current limit).

## v3.1 (same day, Jasper's follow-up)

- **Camera story (D33):** two new slides in The claw section. *First setup: an overhead camera* covers the gen-1 ceiling camera, YOLO-World, and the pixel-to-floor map, with equations and a render of the gen-1 ceiling case. *Moving the camera to the claw* replaces the old *Camera on the claw* slide: why the overhead camera went, what replaced it, and the cost.
- **New photos:**
  - 19, the soldered station perfboard, on *Station board* next to the KiCad schematic;
  - 20, the slicer for the K1, on *Designing parts to be printed*.
  - The other three photos Jasper sent were already in the deck (05, 04, 11).
- **Other edits:** "the overhead camera" added to the parts-deleted lesson; the outline's claw line updated. The deck is now 45 slides.

## Open for Jasper

- **Fin length:** 200 mm was sized for the 1/8 in plate. For the 0.019 in sheet, about 140 mm does the same job (past 136 mm adds under 5 %). Keep 200 mm, so the same cover slot takes the plate later, or trim. The slide says "built 200 mm" either way.
- **Camera reasons:** the three reasons on *Moving the camera to the claw* come from the design review; say them in your own words or replace them with your own.
- **First test slide:** replace the placeholder with the photo and the measured numbers after the run.
- **Hold-test length:** the deck says 90 min (status slide); the prep checklist says 60 min. Pick one.
