# Down the line: details for Q&A and later work, not on slides

Bench and build details taken off the v10 slides in v10.3 to keep the deck short. One line each, with its source.

## Generation 1 bench (August)

- The shield terminal read 18 V on the meter from a supply labelled 12 V. Source: `DECK_V9_NOTES.md` slide 9 row; v9 slide 9 notes.
- The homing switch was wired fail-safe (LOW at rest) but the firmware took LOW as pressed, so homing would have zeroed without moving; logic inverted. Source: `DECK_V9_NOTES.md` slide 9 row.
- The homing switch had to move below the pulley onto a drop arm; the first arm design failed a CAD check before printing. Source: `DECK_V9_NOTES.md` slide 9 row; `DECISION_STORIES.md` T16.

## Station bench (10/25 to 10/26)

- Driver off at boot: the enable line is pulled high so a reset cannot move a motor. Source: `DECK_V9_NOTES.md` slide 20 row; `docs/electrical/station_revC_20261016/README.md`.
- The encoder answers at its I²C address (0x36) with the magnet detected. Source: `DECK_V9_NOTES.md` slide 20 row and "what is new since v8".
- One spool turn lands within 60 encoder counts of a revolution: PASS on both boards (60 counts = 0.69 mm of line). Source: `DECK_V9_NOTES.md` slide 20 row; `calculations/lift_chain_weakest_link.json` detection.tol_line_mm.
- A short announced itself by the board LED going out; traced to the switch pull-up. Source: `DECK_V9_NOTES.md` slide 20 row.
- A motor that logged steps but did not turn: the driver logic rail read about 1.14 V instead of 3.3 V (bad 3.3 V connection); the driver VDD now comes from the regulated rail, soldered, and is measured before enable. Source: `PANEL_FEEDBACK_ANSWERS_20261026.md` (v8 slide 17 item); `DECISION_STORIES.md` T30.

## Claw bench (10/26)

- Battery read through the 200k/100k divider at 7.2 V, matching the meter. Source: `DECK_V9_NOTES.md` slide 21 row.
- The servo got no pulses while the camera ran: both shared one hardware timer; the servo now drives from its own timer. Source: `DECK_V9_NOTES.md` slide 21 row; v9 slide 21 notes.
- Still open: servo end points not measured; camera not calibrated. Source: v9 slide 21 notes.

## Wiring

- The Gen 1 motor leads (driver to motor) ran back to the central box; their gauge is not recorded, so v10.3 shows no Gen 1 voltage-drop figure. Open: motor lead gauge from the insulation print. Source: Jasper, 10/27.
