# Deck v5: notes and content contract (2026-10-22)

`deck_v5/build_deck_v5.js` builds `deck_v5/RoomCleaner_Buntinx_Oct27_v5.pptx` / `.pdf`: 20 main slides + 13 backups,
validated. `deck_v5/contact_sheet.png` shows all 33. Decks v1 to v4 are unchanged.

## Why v5

Jasper's brief (10/22): about me first; scope, timeline and who did what; my own responsibility and decisions with the
reasons; at least one graphic per slide, only ones I can defend in depth; good and poor decisions; lessons and "what would
you do in half the time"; acronyms written out; failures upfront; thorough and scrappy examples; an interactive design
review, not a lecture. Also: v4 was "all over the place, not organized, way too wordy".

What changed from v4 (52 slides):
- **One story line:** Intro → Design → Build → Test → Lessons, shown by a tracker at the top of every slide instead of
  eight section-divider slides.
- **Short titles** (2 to 4 words), not full-sentence headlines.
- **3 to 5 terse bullets**, most in the pattern Problem / Decision / Result / Next. The detail moved to the speaker notes,
  so Jasper expands on each bullet himself.
- **A status chip** on each technical slide says what kind of evidence it is: Built, Measured, Calculated, Simulated,
  Planned, Open problem.
- **New slides:** About Me, Scope and Timeline (native timeline, "me" vs "bought or outside"), Good and Poor Decisions,
  Thorough vs Scrappy, Lessons Learned (actual 15 weeks vs a 7-week plan, same scale).
- Control logic is one slide ("How It Works"); the gen-1 vs final table, one run, the phone app and obstacles are backups.

## Slide list

| # | Title | Graphic | Status chip |
|---|---|---|---|
| 1 | RoomCleaner | photos 11 (station), 21 (claw body) | |
| 2 | About Me | photo placeholder | |
| 3 | The Goal | final station and claw renders; gate strip | |
| 4 | Scope and Timeline | native timeline; me vs bought | |
| 5 | How It Works | five-layer diagram | Simulated end to end |
| 6 | Cable Tension | Sheet chart, equations | Calculated |
| 7 | Winch Pull | Sheet chart, equations | Calculated |
| 8 | One Controller per Winch | wiring chart, equations | Built |
| 9 | Cooling the Motor | motor temperature chart, equations | Fin built · temperature calculated |
| 10 | Homing | bead homing chart, equation | Calculated · simulated |
| 11 | The Claw | four claw images incl. photo 22 | Body built · hands in CAD |
| 12 | Weight: the Open Problem | lift budget chart | Open problem |
| 13 | Printed Fits | spool v1 to v3 | Built |
| 14 | Machining the Fin | photos 06, 03, 02, 15 | Built |
| 15 | Electronics Bring-Up | photos 19, 12 | Measured |
| 16 | First Test | placeholder + pass-limit table | Planned · this week |
| 17 | Good and Poor Decisions | eight thumbnails | |
| 18 | Thorough vs Scrappy | mill photo; ESP32 breadboard drawing | |
| 19 | Lessons Learned | actual vs half-time bars | |
| 20 | Questions | | |
| B | Where It Stands, Fin Length, Floor Board Accuracy, Startup Calibration, Logic: Gen 1 vs Final, One Run, Phone App, Obstacles, Claw Electrical, Gear Strength, Safety, Acronyms, Calculations and Sources | | |

## Update, Oct 22: drivers at 1.5 A (D37)

The calculation Sheet's Vref input went from 0.85 V to 1.2 V (1.5 A). The lift capacity now follows the winch force (it was
a typed 1.1 kg), and the lift chart gained a "claw + battery + 1 lb test" bar. Everything else follows the Sheet's formulas.
The charts were re-exported to `deck_v5/fig/` (`sheet_export.pdf`, then `deck_v3/sheet_charts.py <pdf> <out_dir>`); the
1.06 A charts are unchanged in `deck_v3/fig/`.

Slides changed:
- Cable Tension: 0.4 m now holds while accelerating (14.7 N against 16.8 N).
- Winch Pull: 1.5 A, 34 / 25 N, design force 16.8 N.
- Cooling the Motor: twice the heat; vented + fin 58 °C; hold test decides 1.5 or 1.35 A.
- Weight: capacity 1.56 kg; the 1 lb test fits; jeans 0.2 kg over.
- Good and Poor Decisions, Where It Stands: the same numbers.

New placeholder: how 1.5 A was reached (Vref reading), on "Where It Stands" and in the Winch Pull notes.

## Placeholders for Jasper (red, in brackets, on the slides)

1. Slide 2: graduation month and year; hobbies and interests; one line on why a laundry robot; a photo of you building.
2. Slide 4: which control-software parts you wrote (or delete the line); any shop access or mentors (or delete).
3. Slide 12: the weighed claw mass.
4. Slide 16: a photo or video of the three-station test, and the four result cells (record failures too).
5. Backup "Where It Stands": how many stations are built.

In the speaker notes only: the start date (git shows Jul 16) and what happened in September; time per fin and any scrap; the
1.14 V readings and date; confirm "several stations before one was proven" as a poor decision.

## Facts used (all from the repository record)

Requirements and gates: SPACEX_OUTLINE.md slides 2 and 3. Numbers: as in deck v4 (calculation sheet tabs, DECK_V4_NOTES.md).
Timeline: SPACEX_OUTLINE.md slide 3 plus git dates (Aug 6 to Sep 2, Oct 19 to 22). Good and poor decisions:
DECISION_STORIES.md and the v4 lessons slide. The tube is called 10.5 in (D36: 10.48 in), as Jasper asked.

## Build

```
NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck_v5/build_deck_v5.js
```
`[[text]]` in any slide string renders as a red bracketed placeholder.
