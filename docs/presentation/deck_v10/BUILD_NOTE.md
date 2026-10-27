# Deck v10 build note (2026-10-27)

**Brief:** `docs/presentation/DECK_V10_BRIEF.md` (Jasper, 10/27): the simple format of the reference deck, Jasper's flow, bullets
only, nothing invented. Emphasis per `DESIGN_INTENT_20261027.md`; calibration text from `CALIBRATION_SIMPLE.md`.

**Built:** `build_deck_v10.js` (new; pptxgenjs, 16:9, 10 x 5.625 in, Arial). A structured deck: theme (black / grey / one dark
blue), two layouts (`CONTENT` with the title placeholder and the footer bar, `PLAIN` for the title and thank-you slides),
sections per topic. Charts are native pptxgenjs charts drawn from the calculation-sheet data used by v8/v9 (`deck_v8/fig` charts),
restyled. Outputs in this folder: `RoomCleaner_Buntinx_v10.pptx`, `.pdf`, `contact_sheet.png`.

## Rebuild

```bash
SK=<pptx skill directory>
NODE_PATH=<node_modules with pptxgenjs> APPLY_THEME=$SK/scripts/apply_theme.js node docs/presentation/deck_v10/build_deck_v10.js
/usr/bin/python3 $SK/scripts/office/validate.py docs/presentation/deck_v10/RoomCleaner_Buntinx_v10.pptx
/usr/bin/python3 $SK/scripts/office/soffice.py --headless --convert-to pdf RoomCleaner_Buntinx_v10.pptx   # in deck_v10/
/usr/bin/python3 $SK/scripts/thumbnail.py RoomCleaner_Buntinx_v10.pptx v10thumbs --cols 5 && python3 -c "from PIL import Image; Image.open('v10thumbs.jpg').save('contact_sheet.png')"
```

`validate.py` passes. Every slide was rendered through LibreOffice (`pdftoppm -r 70`) and inspected.

## Slides and sources

Speaker notes on each slide name the file and line for every number. Summary:

| # | Slide | Visual | Sources |
|---|---|---|---|
| 1 | Title | photo 42 | brief (byline); photos/README row 42 |
| 2 | About me | about_me collage columns | photos/README about_me row |
| 3 | Project scope | three cards + photo 42 | DECK_V9_NOTES slide 3 (v9.1 origins); D19, D21; COST_BREAKDOWN headline table |
| 4 | Generation 1: one central unit | photos 14, 05, 13 | DESIGN_INTENT "Iteration 1"; DECK_V9_NOTES v9.2 slide 7, slide 8; D13, D33 |
| 5 | Problems with Generation 1 | bead-homing chart (native) | DECK_V9_NOTES slides 9, 10; calculations/bead_reach.json; PANEL_FEEDBACK_ANSWERS (floor area); D33 |
| 6 | What a winch on a wall needs | photos 09, 23, 39 | DESIGN_INTENT "Why it changed"; DECK_V9_NOTES slide 20 (encoder jobs, switch wiring), v9.2 slide 10 (wire) |
| 7 | The solution: a modular box | photo 46, station_shell_transparent | DESIGN_INTENT "Iteration 2"; FUNDAMENTALS section 10 (0.82 / 0.51 V); COST_BREAKDOWN 16 AWG row |
| 8 | Modular, for the everyday user | photos 45, 24, 31 | DESIGN_INTENT "Iteration 2"; DECK_V9_NOTES slide 12 |
| 9 | Trade-offs | five native charts + "The factors" card | FUNDAMENTALS 1; sheet_motor_temperature / fin_sizing_4w.md; lift_chain_weakest_link.md and .json; PANEL_FEEDBACK_ANSWERS slide 16 and "larger motors"; DECK_V9_NOTES slides 6, 16, 17 |
| 10 | Mount assembly: slide-in on a dovetail | photos 45, 24; snap_dovetail; station_shell_transparent | DECK_V9_NOTES slides 12, 13; lift_chain_weakest_link.md; PANEL_FEEDBACK_ANSWERS fits row "Slide-in mount" |
| 11 | Mount assembly: fin, vents and the wall | photos 32, 33, 44 | DECK_V9_NOTES slides 16, 22, 24; fin_sizing_4w.md |
| 12 | The claw, and why it is modular | photos 25, 40; gripper1021_head, claw_v6 | DECK_V9_NOTES slides 11, 17, v9.2 slide 18; DESIGN_INTENT "The gripper" |
| 13 | Electrical and testing: on the bench | photos 43, 29, 37 | DECK_V9_NOTES slides 20, 21; PANEL_FEEDBACK_ANSWERS slide 17 item (1.14 V) |
| 14 | Electrical and testing: on the wall | photos 32, 44, 31 | DECK_V9_NOTES slides 22, 25, 26 |
| 15 | How the claw calibrates itself | six step cards + photo 42 | CALIBRATION_SIMPLE.md (six step names kept) |
| 16 | Next iteration | three cards, planned card, "[Jasper: new CAD]" box | DECK_V9_NOTES slide 24 and the 10/27 correction; D40-D42; PANEL_FEEDBACK_ANSWERS "larger motors" |
| 17 | Thank you | | |

## Left off because the record does not hold it

- Slide 2: Ironman time, marathon time, EcoFil numbers, the Gladiator Dash total (only in older speaker notes, not the record files named in the brief).
- Slide 4: the Gen-1 test weight and lift height (not recorded).
- Slide 13: the live-view screenshot (`docs/app_screenshots/02_camera.png` is the simulator's view, so it is not shown as the claw camera); what the bad 3.3 V connection physically was.
- Slide 14: "on the wall" is one station; the three stations are not on the network yet (v9 slide 22 notes), so no network result is claimed.
- Slide 16: the draft and the lighter mount are intentions, not drawings; the box is for Jasper's new CAD.

## Record caveats carried into the notes

- Station bench "PASS on both boards" and the LED-out short come from Jasper's 10/25-10/26 bench (DECK_V9_NOTES); DESIGN_STATE has no entry, so Jasper confirms before the talk.
- The 0.51 V / 0.82 V drops are calculated at an illustrative 2 A, not measured. The 16 AWG roll price is an estimate (COST_BREAKDOWN "est.").
- The weakest-link chart caps "Screws in a stud" at 600 N (record: 531 to 2954 N).
