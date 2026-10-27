# Deck v9 build note (2026-10-26)

**Built:** `build_deck_v9.js` (from `deck_v8/build_deck_v8.js`: same theme, helpers, equation boxes, footer; evidence pills
added per the style guide; "Act N of 5: <name>" in the footer). Outputs in this folder:

- `RoomCleaner_Buntinx_v9.pptx` / `.pdf`: 26 main slides (slides 1-4 opening, Acts 1-5, results, close; slide 13 "The drive slips before the wall does" added 10/27)
- `RoomCleaner_Buntinx_v9_appendix.pptx` / `.pdf` (`PART=appendix`): divider + 12 slides: safe state (with a three-station
  row), heat fin length, fin sizing, floor board, operating sequence, control logic, manufacturing fits and datums (the v8
  main slide, kept on file), station Rev D schematic, station breadboard layout, claw Rev B schematic, acronyms, sources
- `contact_sheet.png`, `contact_sheet_appendix.png`
- `fig/winch_gear3_iso_crop.png`, `fig/winch_gear3_mesh_crop.png`: the `renders/winch_gear3` renders with their title and
  frame-note strips cropped off (they carried file names)

Validation: the pptx skill's `validate.py` passes on both files. Every slide was rendered through LibreOffice and inspected.
Speaker notes: a 40-60 s talk track per slide plus "If asked".

## Where each new photo went

| Photo | Slide |
|---|---|
| 38 claw assembled, lit | 1 (title) until 10/27; now photo 42 (claw hanging from three cables) |
| 29 station bench, ELEGOO | 20 (2 x 2 grid with 43, 37, 31) |
| 37 red shell, fused 12 V lead | 20 |
| 31 XIAO breadboard, shell open | 20 |
| 40 claw housing open, lit | 18 (with photo 25) and 21 (large left) |
| 39 slide-in held up with harness | not used since 10/27 (the gear-stage slide was removed) |
| 35 blue shell, failed layer kept | 19 (large right) |
| 26 slicer (v8) | 19 |
| 32 station on the TV wall | 22 (large left) |
| 33 mounted station from below | 22 until 10/27; replaced by 44 (line leaving straight down) |
| 36 shell front, vents and fin tab | 22 |
| 34 shell rear | not used (the outline said "34/36"; 36 chosen; three photos fit the slide) |
| 30 bench, spool side | not used (not in the outline) |

Slide 23's three-station plan is drawn with shapes from `docs/THREE_STATION_MODE.md` section 2 (room 3.35 x 2.74 m; A (0.05,
0.05), B (3.30, 0.05), C (1.68, 2.69), D empty, start point (1.68, 0.93), sides 3.25 / 3.10 / 3.10 m).

## Placeholders for Jasper (render red)

- Slide 21: the live-view screenshot box (`docs/app_screenshots/02_camera.png` is the simulator's view, so it was not used).
- Slide 25: cost total (filled 10/26 from the cost breakdown).
- Notes only (not on slides): slide 2 one EcoFil number; slide 4 hours, cost, shop access or mentors; slide 8 the Gen-1 test
  weight and lift height; slide 16 how 1.5 A was reached and the Vref read; slide 19 and appendix fits slide: which spool bore
  is printed and the heat-set insert part number.

## Outline vs record: differences, and claims to confirm

- Slide 4 title: the outline says "fourteen weeks"; the v8 record (Gantt Jul 16 to Oct 27, "about 15 weeks" in the v8 notes
  and the schedule bars) gives fifteen. The slide says **fifteen**.
- Slide 20: "PASS on both boards" and "a short found by the LED going out, traced to the switch pull-up" come from the outline's
  "what is new since v8" list (Jasper's 10/25-10/26 bench). `DESIGN_STATE.md` records the claw bench (10/26) but has no entry
  for the station bench results; the bench script (`firmware/station_bench_test/README.md`) defines the checks and the
  LED-out = 3.3 V short rule. Kept as the outline states; **Jasper to confirm** before the talk.
- Slide 23: the record says 78 % of the workspace is *above* the 5 degree grip limit with the three corner holes
  (`verification/three_station_mode_results.md`), i.e. grips refused there, which is what the slide says; with the three-cable
  housing 78 % is *under* the limit (coincidentally the same figure). The slide names only the corner-hole case.
- (Removed 10/27) The gear-stage slide added the capacity and heat gain of the gear stage (1.98-2.80 kg at 1.0 A, 1.8 W; D40) to the outline's bullets,
  since they are the reason for the stage; the 1.75x teeth figure is at 1.0 A (D42).
- Slide 12 motor slip range is read from `calculations/lift_chain_weakest_link.json` as in v8 (34-59 N).
- Slide 9: the switch bullet says the first drop-arm design "failed a CAD check before it was printed" (T16: rev C found by an
  independent CAD check), rather than the outline's shorter "a switch that had to move below the pulley".
- Slide 25 row "Obstacle map in the app": evidence "Simulated" (the independent verification ran in simulation; verdict FAIL
  for hardware with H-1, H-2 being fixed), status Planned, as the outline asks.

## From the outline, not done

- Nothing dropped. Photo 34 and photo 30 are unused (see the table). The outline's "v8 About Me collage (unchanged)" and the
  v8 figures are reused as specified; the floor-board chart (v8 appendix) stands in for the camera-calibration figure on
  slide 14 because v9 slide 10 already uses the bead-homing chart.

## Panel feedback applied (2026-10-26, evening)

The SpaceX panel's 16 items on deck v8 are answered from the record in `docs/presentation/PANEL_FEEDBACK_ANSWERS_20261026.md`
and added to the matching v9 slides' "If asked" notes. One-line versions on the slides (numbers after the 10/27 insertion): budget and schedule limits (4), what bead
homing is and the floor-area share (10), how to read the margins (12), power loss (14, Faults row), the fin's role (16), narrow
grabs and the cost total (25). Placeholders for Jasper in the notes of slides 16 (fin paint and alloy), 17 (claw infill behind
the 0.86 kg estimate), 19 (source of the 0.3 friction coefficient) and 21 (how the 3.3 V fault was found). Both files
re-validated (PASS); the changed slides re-rendered and inspected; contact sheets regenerated.

## Jasper's stories folded in (2026-10-27)

New slide 13 "The drive slips before the wall does: a designed fuse" (v8 weakest-link chart; CALCULATED; "If asked" notes on why not
a clutch and what happens after a slip). Title photo 42 with the 30-second pitch in the notes (numbers as in the record: slip 34-59 N
from the 0.36 N·m motor on the 7.5 mm core). Slide 14: Gen 1's central box story. Slide 18: the encoder's two jobs. Slide 26: pole-clamp
mount and open-source release. Photos 43 (slide 21), 45 and 46 (slide 12), 44 (slide 23, replacing 33). Rebuilt, validated (PASS on both
files), slides 1, 12, 13, 14, 18, 21, 23, 26 rendered and inspected; contact sheets regenerated.

## Correction 10/27 (Jasper): the 3:1 gear stage is the next iteration, not this build

The gear-stage slide is removed from Act 4 (the mounted stations are direct-drive spools; photo 39 is no longer used). The encoder's
two jobs are stated on the station-bench slide (20). New slide 24 in Act 5, "What hurts now, and the next iteration": three cards
(gear stage, CAD, not fitted; 1° draft on the dovetail, PLANNED; lighter back mount, PLANNED) and a placeholder box for Jasper's photos.
The fuse slide's note, the winch-pull note, the results row and the good-decision row now say "next iteration". Act 5 footer
reads October 22-27. Slides 19-24 of the morning build are 18-23; still 26 main slides. Rebuilt, validated (PASS on both files),
slides 12, 20 and 24 rendered and inspected; contact sheets regenerated. Cost breakdown revised the same day (gear-stage parts out).

## v9.1 (2026-10-27)

Limits strip on slide 24 (cards shortened to make room), the one-turn statement above the results table on slide 25 (table at
10.5 pt, 0.30 in rows), grey origin sub-lines under each requirement on slide 3. Same theme, layouts and card style. Both files
validated (PASS); slides 3, 24 and 25 rendered at 80 dpi and checked; PDFs and contact sheets regenerated.
