# Deck v7: one story by phase, figure plus statements (Oct 22)

**Jasper's direction (Oct 22):**
- "I'm not gonna read off my slides": show data and short statements, a figure and then bullet points.
- No unusual box structures or designs. Make the title simpler.
- "Have a clearer story to tell with justifications and phases where I talk about stuff along the way."
- No slides on topics the story does not need. A side topic is mentioned inside the slide it fits.

**Build:** `docs/presentation/deck_v7/build_deck_v7.js` (the build command is in its header).

**Outputs:**
- `RoomCleaner_Buntinx_Oct27_v7.pptx`
- `.pdf`
- `contact_sheet.png`

The numbers are the same as v5 and v6 (1.5 A). v1 to v6 are kept unchanged.

## Format

- **Title:** plain, 26 pt bold, top left. No rule, tracker or chip.
- **Footer:** "Jasper Buntinx | RoomCleaner" and the page number.
- **Content slides:** the figure on the left (a chart from the calculation sheet, photos or CAD), and 3 or 4 statements with values on the right.
- **Equation boxes:** kept, but cut to 2 or 3 lines, under the statements. The inputs are in the speaker notes.
- **Tables:** only where the data is a table: trade-offs, results against targets, decisions, test pass limits, acronyms.
- **Phase dividers:** five plain slides (phase number, name, dates, goal). They match the five rows of the Gantt chart.
- **Removed:** the system block diagram, the calibration flow boxes, the operating-sequence column boxes, the column headings with rules, and the image panels.

## Story (38 slides; 30 in the main deck)

| # | Slide | Figure | Why it is here |
|---|---|---|---|
| 1 | Title | station and claw photos | |
| 2 | About Me | photo placeholder | panel brief |
| 3 | Project Goal | Jasper's SolidWorks station screenshot and claw CAD | the problem and the targets; safety rules in the notes |
| 4 | Timeline and Scope | Gantt chart of the 5 phases | the roadmap the talk follows; what is mine and what is bought |
| 5 | Phase 1: Concept | divider | Jul 16 – Aug 5 |
| 6 | Why a Cable Robot | cable geometry figure | architecture choice; system overview and phone app folded in |
| 7 | Design Trade-offs | table | the levers revisited in every later phase |
| 8 | Cable Tension Limit | Sheet chart and equation | sets the 0.4 m ceiling margin; obstacles mentioned in the notes |
| 9 | Phase 2: Generation 1 | divider | Aug 6 – Sep 2 |
| 10 | Generation 1 Build | gen-1 photos and claw CAD | what was built and what worked |
| 11 | What Generation 1 Taught Me | bead-homing chart | the three findings that drove the redesign |
| 12 | Phase 3: Redesign | divider | Sep 3 – Oct 6 |
| 13 | One Controller per Winch | wiring chart and equation | finding 2 |
| 14 | Camera Calibration Replaces Homing | floor-board chart | finding 1; calibration and accuracy merged |
| 15 | Geared Four-Bar Claw | claw CAD and photos, gear equation | finding 3; gear strength and claw electrical folded in |
| 16 | Phase 4: Final Design | divider | Oct 7 – Oct 21 |
| 17 | Final Wall Station | Jasper's SolidWorks screenshot, shell transparent | the final design itself: slide-in mount, vented shell, fin slot |
| 18 | Winch Pull at 1.5 A | Sheet chart and equation | the current decision |
| 19 | Motor Cooling | Sheet chart and equation | the cost of 1.5 A; fin sizing folded in |
| 20 | Weight Budget: Open Issue | Sheet chart and equation | the failure, shown upfront; the gear-reduction option |
| 21 | Phase 5: Build and Test | divider | Oct 22 – Oct 27 |
| 22 | Printing and Machining | spool CAD and fin photos | printed fits and fin machining merged |
| 23 | Electronics Bring-Up | board and bench photos | the 1.14 V failure |
| 24 | First System Test | placeholder and pass-limit table | |
| 25 | Thermal Verification | placeholder and method table | |
| 26 | Results Against Targets | table | closes the loop on slide 3 |
| 27 | Good and Poor Decisions | two tables | panel brief |
| 28 | Thorough vs. Scrappy | mill photo and ESP32 board | panel brief |
| 29 | Lessons Learned | actual vs half-time schedule | panel brief |
| 30 | Questions | | |

**Appendix (31 to 38):**
- Heat Fin Length
- Fin Sizing for 4 W
- Operating Sequence (now covers the phone app, obstacles and safety)
- Control Logic: Generation 1 vs. Final
- Claw Electrical
- Acronyms
- Calculations and Sources

**Dropped as standalone slides; each is now part of another slide or its notes:**
- Agenda (replaced by the Gantt chart and the phase dividers)
- How It Works
- Project Status
- Floor Board Accuracy
- Startup Calibration
- One Run
- Phone App
- Obstacles
- Gear Strength
- Safety

## Still to fill in

The red brackets on the slides mark these:
- graduation year, hobbies and a photo;
- the software parts Jasper wrote;
- the generation 1 test weight;
- the weighed claw mass and the total cost;
- the test results;
- the "several stations" decision, to confirm.

The speaker notes also ask for:
- the Vref reading;
- the electronics readings;
- the fin machining time;
- the Gantt start date.
