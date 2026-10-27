# Deck v10 build note (2026-10-27)

**Brief:** `docs/presentation/DECK_V10_BRIEF.md` (Jasper, 10/27): the simple format of the reference deck, Jasper's flow, bullets
only, nothing invented. Emphasis per `DESIGN_INTENT_20261027.md`; calibration text from `CALIBRATION_SIMPLE.md`.

**Built:** `build_deck_v10.js` (new; pptxgenjs, 16:9, 10 x 5.625 in, Arial). A structured deck: theme (black / grey / one dark
blue), two layouts (`CONTENT` with the title placeholder and the footer bar, `PLAIN` for the title and thank-you slides),
sections per topic. Outputs in this folder: `RoomCleaner_Buntinx_v10.pptx`, `.pdf`, `contact_sheet.png`.

## v10.3 (10/27)

- **Homing slide (7)**: bead homing vs floor-board homing. The bead condition reachable(p) <=> ||a_i - p|| >= L_i,home for every i is
  typeset by `make_equations.py` (fig/eq_d.png); the reachable share is the grid count of that condition (`calculations/bead_reach.json`:
  0.0 % at 0.3 m to 32.0 % at 2.19 m). The floor-board figure moved here from the calibration slide; the calibration cards are full width.
- **Calculated values carry their equation.** Every value tagged (calculated) is shown with its equation and substituted numbers on the
  same slide, recomputed in Python from the repo inputs. Model results that need a multi-node model are captioned with the governing
  equation and their numbers are off the cards (fin temperatures: two-node thermal network, P = I²R input). Values that did not
  reproduce in one line were deleted (about 130 N gear-stage slip fuse; "about 200x" mount margin; four-bar "within 1°").
- **Wire drop (v10.3, corrected)**: Gen 1 ran the motors' own 24 AWG driver-to-motor leads back to the central box (Jasper, 10/27). The
  slide compares them with the 16 AWG power pair by the FUNDAMENTALS section 10 method, V = I·ρ·2L/A (ρ 1.724e-8 Ω·m, 32 ft one way,
  2 A): 24 AWG 1.64 Ω, 3.29 V (27 %), 6.6 W; 16 AWG 0.257 Ω, 0.51 V (4.3 %), 1.0 W. The earlier 18 AWG comparison is gone.
- **Bench minutiae** (18 V supply, inverted switch logic, switch below the pulley, 1.14 V logic rail, servo timer, 7.2 V divider,
  driver off at boot, encoder address/magnet, 60 counts) moved to `DOWN_THE_LINE.md`; the two electrical slides are one.
- **Manufacturing slide (14)** for the manufacturing role: processes, fits, make vs buy, cost per station. Two record conflicts handled
  on the slide: the dovetail 0.175 mm is a CAD dimension (measured on the STEP files), and the hole-sweep fit coupon is planned
  (FUNDAMENTALS section 12), so the slide does not say fits came from coupons.
- 19 slides. validate.py PASS; no ppt/charts or ppt/embeddings entries; aspect check 48 pictures, 0 mismatches.

## v10.1 (10/27)

- **Charts are images.** PowerPoint reported the v10 file as needing repair; the only structural difference from v9 was the six
  native pptxgenjs charts (`ppt/charts` + embedded xlsx). The build now writes `chart_data.json` (the one source of numbers,
  with each chart's box size in inches) and runs `make_charts.py` (matplotlib, Agg, 300 dpi, Arial/Liberation Sans, navy / grey /
  black) into `fig/*.png`, placed with `addImage` at the same boxes. The rebuilt package has no `ppt/charts/` or
  `ppt/embeddings/` entries (checked with `unzip -l`; the build also strips the empty directory entries pptxgenjs leaves).
- **Photos are centre-cropped, not stretched.** The build records every photo box in `crop_jobs.json`; `crop_photos.py` (PIL)
  crops each source to the exact box aspect into `img/<name>_<w>x<h>.jpg` (<= 300 px/in, git-ignored), and the picture is placed
  with plain w/h and no `sizing`. Renders and CAD images are fitted (letterboxed) with `fitImage`; photo 13 (gen-1 lift) is fitted
  too, since a crop would cut the station. Check: every picture's displayed w/h equals its file's pixel ratio within 1 %
  (41 pictures, 0 mismatches).
- **New slide 4** "How cable length becomes position, and torque becomes pull": three cards with boxed equations
  (kinematics.py docstring; FUNDAMENTALS.md sections 1 and 2; D37). Slides after it shift by one.
- **Slide 16 (calibration)** rewritten in the sequencer's terms: the six `StartupSequencer.run` states from
  `roomcleaner/cdpr/startup.py` (SELF_CHECK, SLACK_TAKEUP, INITIAL_LIFT, VISUAL_INITIALIZATION, CALIBRATION,
  REFERENCE_VERIFICATION), bullets from the module docstring; notes cite the line ranges. `CALIBRATION_SIMPLE.md` stays on file
  as the plain-words version; it is no longer the slide text.
- Wording: no "the record says" on slides or in notes; evidence tags in parentheses only where they change the meaning.

## Rebuild

```bash
SK=<pptx skill directory>
NODE_PATH=<node_modules with pptxgenjs> APPLY_THEME=$SK/scripts/apply_theme.js node docs/presentation/deck_v10/build_deck_v10.js
#   the build itself runs make_charts.py (chart_data.json -> fig/*.png) and crop_photos.py (crop_jobs.json -> img/*.jpg)
/usr/bin/python3 $SK/scripts/office/validate.py docs/presentation/deck_v10/RoomCleaner_Buntinx_v10.pptx
/usr/bin/python3 $SK/scripts/office/soffice.py --headless --convert-to pdf RoomCleaner_Buntinx_v10.pptx   # in deck_v10/
/usr/bin/python3 $SK/scripts/thumbnail.py RoomCleaner_Buntinx_v10.pptx v10thumbs --cols 5 && python3 -c "from PIL import Image; Image.open('v10thumbs.jpg').save('contact_sheet.png')"
```

`validate.py` passes. Every slide was rendered through LibreOffice (`pdftoppm -r 70`) and inspected. Chart images need
`matplotlib`; photo crops need `Pillow` (both under `/usr/bin/python3`).

## Slides and sources (v10.3)

Speaker notes on each slide name the file for every number and carry the substituted equation for every calculated value.

| # | Slide | Visual | Sources |
|---|---|---|---|
| 1 | Title | photo 42 | brief (byline); photos/README row 42 |
| 2 | About me | about_me collage + three cards | Jasper, 10/27; photos/README about_me row |
| 3 | Project scope | three cards + photo 42 | DECK_V9_NOTES slide 3 (v9.1 origins); D19, D21; COST_BREAKDOWN headline table |
| 4 | How cable length becomes position, and torque becomes pull | three cards, typeset equations, position_vectors.png | kinematics.py docstring; FUNDAMENTALS sections 1-2; lift_chain_weakest_link.json; D37 |
| 5 | Generation 1: one central unit | photos 14, 05, 13 | DESIGN_INTENT "Iteration 1"; DECK_V9_NOTES v9.2 slide 7, slide 8; D13, D33 |
| 6 | Problems with Generation 1 | two cards + photo 14 | DESIGN_INTENT; DECK_V9_NOTES slide 10; FUNDAMENTALS section 2 (50 mm/s); D33 |
| 7 | Homing: one floor board instead of four beads | eq_d.png, bead chart, floor_board.png | calculations/bead_reach.py and .json; tools/print_floor_board.py; kinematics.py; startup.py |
| 8 | What a winch on a wall needs to work | photos 09, 23, 39 | DESIGN_INTENT "Why it changed"; DECK_V9_NOTES slide 20; DECK_V2_OUTLINE line 85 (82 ft of routes) |
| 9 | The solution: a modular box that only needs power | photo 46, station_shell_transparent | DESIGN_INTENT "Iteration 2"; FUNDAMENTALS section 10 (16 AWG only); COST_BREAKDOWN 16 AWG row |
| 10 | Modular, for the everyday user | photos 45, 24, 31 | DESIGN_INTENT "Iteration 2"; DECK_V9_NOTES slide 12 |
| 11 | Trade-offs: what each component needs | five chart images + "The factors" card | FUNDAMENTALS 1-3; fin_sizing_4w.py (chart only); lift_chain_weakest_link.md/.json; winch_gear3.json direct_drive |
| 12 | The mount assembly: slide-in on a dovetail | photos 45, 24; snap_dovetail; station_shell_transparent | DECK_V9_NOTES slides 12, 13; lift_chain_weakest_link.md; deck_v8 fits table |
| 13 | The mount assembly: fin, vents and the wall | photos 32, 33, 44 | DECK_V9_NOTES slides 16, 22, 24; FUNDAMENTALS section 3 |
| 14 | Manufacturing: what was made in-house, and how fits were controlled | photos 26, 01; snap_dovetail, snap_gear_lip | deck_v8 fits table; FUNDAMENTALS section 12; DECISION_STORIES T31/T32; COST_BREAKDOWN sections 1-2; DECK_V9_NOTES slides 4, 19 |
| 15 | The claw, and why it is modular | photos 25, 40; gripper1021_head, claw_v6 | DECK_V9_NOTES slides 11, 17, v9.2 slide 18; DESIGN_INTENT "The gripper" |
| 16 | Electrical and testing: bench, then wall | photos 43, 32 | DECK_V9_NOTES slides 20, 21, 22, 25, 26 (details in DOWN_THE_LINE.md) |
| 17 | Startup and self-calibration: six states before the robot is READY | six state cards | roomcleaner/cdpr/startup.py (docstring 1-66; run 669-690; states 693-1619) |
| 18 | Next iteration: what was not working, and what changes | three cards, planned card, photos 49, 50 (CAD) | DECK_V9_NOTES slide 24; D40-D42; winch_gear3.json (ratio, eta, heat) |
| 19 | Thank you | | |

## Left off because the record does not hold it

- Slide 2: Ironman time, marathon time, EcoFil numbers, the Gladiator Dash total (only in older speaker notes, not the record files named in the brief).
- Slide 5: the Gen-1 test weight and lift height (not logged).
- Slide 14: the live-view screenshot (`docs/app_screenshots/02_camera.png` is the simulator's view, so it is not shown as the claw camera); what the bad 3.3 V connection physically was.
- Slide 15: "on the wall" is one station; the three stations are not on the network yet (v9 slide 22 notes), so no network result is claimed.
- Slide 17: the draft and the lighter mount are intentions, not drawings; the box is for Jasper's new CAD.

## Record caveats carried into the notes

- Station bench "PASS on both boards" and the LED-out short come from Jasper's 10/25-10/26 bench (DECK_V9_NOTES); DESIGN_STATE has no entry, so Jasper confirms before the talk.
- The 0.51 V / 0.82 V drops are calculated at an illustrative 2 A, not measured. The 16 AWG roll price is an estimate (COST_BREAKDOWN "est.").
- The weakest-link chart caps "Screws in a stud" at 600 N (record: 531 to 2954 N).

## v10.1 equations
Slide 4 equations are typeset PNGs from `make_equations.py` (matplotlib mathtext, STIX, 400 dpi) in `fig/eq_a|b|c.png`; `eqBox` sizes the white panel to the image. Re-run the script after editing an equation, then rebuild.

## v10.1 floor board and next-iteration views
`make_floor_board_figure.py` draws the nine-sheet AprilTag 36h11 floor reference (FloorBoardLayout.nominal_positions, 150 mm tags, 250 mm pitch) to `fig/floor_board.png`, shown on slide 16. Slide 17 shows photos 49 (front) and 50 (back) of the next-iteration station CAD.

## v10.2 cards are single shapes
Each grey card is ONE rectangle with its heading and bullets inside it (`card()`), no rounded corners, hex fill. The earlier grey-shape-plus-text-box build rendered with text hidden behind the cards in iOS Quick Look. Slide 4 reserves space under each heading (`gapIn`) and places the equation panel on top of the card.
