# Prep checklist — Oct 22 draft, Oct 27 panel

Order matters: each item turns a PLANNED card in the deck into a MEASURED one.

| # | Do | Time | Fills deck slide | How |
|---|---|---|---|---|
| 1 | Winch pull test (one station, 1.06 A) | 15 min | 5, 16 | `docs/tests/WINCH_PULL_TEST.md` |
| 2 | Hold test: motor case + fin + PETG tab, 60 min, vented shell | 60 min (mostly waiting) | 6, 7, B5 | thermocouple/IR every 10 min; thermal manual §8 |
| 3 | SolidWorks static study of the station mount | ~1 h | 10, 16 | `docs/simulation/SW_STATIC_STATION_MOUNT.md` (read its "Before you run" box first) |
| 4 | SolidWorks thermal study of the fin | ~1 h | 7, B5 | `docs/simulation/SW_THERMAL_HEAT_FIN.md` |
| 5 | Photos: built perfboard (both sides), fin installed in a station, claw parts on a scale | 15 min | 7, 11, 14 | plain background, shoot straight down, ruler in frame |
| 6 | Weigh: printed claw parts, battery | 5 min | 4, 5, 11 | kitchen scale |
| 7 | Answer the open questions | 20 min | several | `DECISION_STORIES.md` §3: start date, printer and filament, 1.14 V fault readings and dates, spool bore calipers, line diameter |
| 8 | Rehearse once out loud with a timer; aim for 28–30 min | 35 min | all | speaker notes in the PPTX |

Decisions waiting on you (not needed for the draft):
- **Winch capacity** after the pull test: 3:1 reduction vs lighter claw (`docs/decisions/WINCH_CAPACITY_20261021.md`).
- **Grip-tilt rule:** raise to ~12° and aim with predicted tilt, or keep 5° and pick near the centre.
- **Compound web:** 7 holes (SF ~1.7) or 6 holes (SF ~3.75).

Rebuild the deck after updating numbers:
`NODE_PATH=<pptxgenjs dir> APPLY_THEME=<skill>/scripts/apply_theme.js node docs/presentation/deck/build_deck.js`
