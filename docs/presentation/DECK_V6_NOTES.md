# Deck v6: plain corporate format (Oct 22)

**Jasper's direction (Oct 22):** keep the equation boxes and the graphs. Everything else should be simple talking-point bullets,
with values where they are needed. The deck should read as a formal corporate presentation, with no extra formatting.

**Build:** `docs/presentation/deck_v6/build_deck_v6.js` (the build command is in its header).

**Outputs:**
- `RoomCleaner_Buntinx_Oct27_v6.pptx`
- `.pdf`
- `contact_sheet.png`

The content and numbers are the same as v5 (`DECK_V5_NOTES.md`, 1.5 A). v5 is kept unchanged.

## What changed from v5

**Removed:**
- the story tracker;
- the status chips;
- bold "Label:" lead-ins in bullets;
- "·" and arrows inside bullets;
- the gate strip;
- the objective tiles;
- the trade-off cards and their chain;
- the decision thumbnails;
- the shaded rule boxes.

**Bullets:** plain talking points, three to five per slide.
- A number always stays on the same line as its unit.
- Spelling is American (aluminum, center).

**Tables replace graphics:**
- Design Targets: parameter, target, current value, status. "Not met" is shown in red.
- Design Trade-offs: change, benefit, cost, chosen setting.
- Good and Poor Decisions: two tables.

**Gantt chart:** the Scope and Timeline slide now has a Gantt chart of the five phases. Under it are two columns: "My work (solo project)" and "Purchased or external".

**New slides:**
- Agenda (slide 3);
- Appendix divider before the backup slides.

**Renamed slides:**

| Old title | New title |
|---|---|
| What I'm Optimizing | Design Targets |
| Trade-offs | Design Trade-offs |
| Cooling the Motor | Motor Cooling |
| Homing | Homing Method |
| The Claw | Claw Design |
| Weight: the Open Problem | Weight Budget: Open Issue |
| Printed Fits | Printed Part Fits |
| Machining the Fin | Heat Fin Manufacturing |
| First Test | First System Test |
| Thermal Check | Thermal Verification |
| Where It Stands | Project Status |
| One Run | Operating Sequence |

**Equation boxes:**
- Each box has a specific title, for example "Cable tension at the operating limit".
- The inputs are listed on a "Where:" line, separated by semicolons.
- Two equation fixes:
  - The grip line now uses W (the 1 lb load) instead of m g, because m is also the gear module.
  - The winch torque line drops the redundant "× 1.5 / 1.5".

**Chart captions:** each reads "Source: RoomCleaner engineering calculations, "<tab>" (calculated values)".

## Slide list (39)

**Main deck:**
1. Title
2. About Me
3. Agenda
4. Project Goal
5. Scope and Timeline
6. How It Works
7. Design Targets
8. Design Trade-offs
9. Cable Tension
10. Winch Pull
11. One Controller per Winch
12. Motor Cooling
13. Heat Fin Sizing
14. Homing Method
15. Claw Design
16. Weight Budget: Open Issue
17. Printed Part Fits
18. Heat Fin Manufacturing
19. Electronics Bring-Up
20. First System Test
21. Thermal Verification
22. Good and Poor Decisions
23. Thorough vs. Scrappy
24. Lessons Learned
25. Questions

**Appendix:**

26. Appendix divider
27. Project Status
28. Fin Sizing for 4 W
29. Floor Board Accuracy
30. Startup Calibration
31. Control Logic: Generation 1 vs. Final
32. Operating Sequence
33. Phone App
34. Obstacles
35. Claw Electrical
36. Gear Strength
37. Safety
38. Acronyms
39. Calculations and Sources

## Still to fill in

The red bracketed text marks facts only Jasper has. These are unchanged from v5:
- graduation date, hobbies, why this project, and a photo;
- which parts of the control software he wrote, and shop access or mentors;
- the weighed claw mass and the total cost;
- the number of commissioned stations and the Vref reading used to reach 1.5 A;
- the results of the first test, the SolidWorks study and the hold test;
- confirmation of the "several stations" decision and the Gantt dates (git shows a Jul 16 start).
