# Deck QA notes (draft, after the fact-check pass)

Build: `NODE_PATH=<pptxgenjs, react-icons, react, react-dom, sharp> APPLY_THEME=<pptx skill>/scripts/apply_theme.js SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck/build_deck.js`
Files: `build_deck.js` (slides), `deck_kit.js` (visual system), `deck_notes.js` (speaker notes), `assets/c050_open_jaws_panel.png` (crop of the camera-view figure, made by the build), outputs `RoomCleaner_SpaceX_draft.pptx` (24 slides) and `.pdf`.
Checks run: all 24 slides rendered to PNG (LibreOffice, `pdftoppm`) and inspected, every changed slide re-inspected after each fix; `validate.py` passes; every figure typed into slide text is asserted against `calculations/presentation_fundamentals.json` (including the two-phase range 12.6 / 16.8 / 8.4 / 24 N, derived as the one-phase value divided by √2); forbidden-content scan of slide text and notes (AI, assistant, tool names other than SolidWorks, SpaceX, Starlink) finds nothing. Not tested in PowerPoint itself (Liberation, Carlito and Caladea stand in for Arial, Calibri, Cambria).

Pattern on slides 4 to 15: eyebrow, claim title (at most 12 words), evidence pill(s), hero left, vertical WANTED / REALIZED / DECIDED / RESULT / BUT rail right (active step in Signal, one line each, at most 12 words), fundamentals box, PLANNED card under the hero where a result is not in. Rail lines are the only body text (34 to 45 words per slide); detail is in the notes.

Speaker notes now hold only: what to say, the numbers, likely questions with answers, and (slides 2, 6, 7, 9, 11, 13) one line "If you did this yourself, you can say it in the first person: ...". Nothing in the notes refers to files, decision IDs, working prompts or this checklist.

## Slides

1. Title: photo 13, "designed to pick laundry off the floor".
2. Solo project: timeline, bought vs made (neutral wording), tag legend.
3. Done means: renders, five requirement cards (0.9 kg provisional, 450 g, studs designed, one switch, nobody under). Notes carry hard question 3 (power strip).
4. Cable statics: native scatter, design-force band 8.4 to 11.9 N, title "walls bind at task height, ceiling above".
5. Drive: 0.79 to 0.85 V range hero, native chart of largest claw per core (all bars steel, upper bounds), pull 12.6 to 17.9 N, fix open. PLANNED card (pull test). Notes carry hard question 1.
6. Heat: native chart, sealed first as the motivation, vented as the planned case. PLANNED card (vented hold test). Notes carry hard question 2.
7. Fin: photos 06, 01, 16, native efficiency chart, neutral "drawn / built" wording. PLANNED card (hold test).
8. Spool: three renders, CAD-derived overhang, line diameter assumed. No placeholder.
9. Homing switch: photo 09 labelled as a bench switch, pill CALCULATED · CAD, rev C X and Y misses. PLANNED card (trip test).
10. Removable station: renders, targets at 34 N (24 N if two-phase), hand estimate 8 to 14 MPa. PLANNED card (SolidWorks study, station-mount pull test); no results.
11. Gripper: native chart needed vs available, gear renders, v6r vs v7 gear sets distinguished. No placeholder.
12. Camera and tube: render (v6, superseded) with camera-bay callout, 140 mm hover view, 3 mm wall assumed.
13. Electronics: photos labelled gen 1 / gen 2, assumptions marked. PLANNED card (four-station test).
14. Bring-up: photo 07, 3.3 V vs 1.14 V (not logged). PLANNED card (as-built meter checklist).
15. Calibration: floor-board schematic, 4 tags vs 2 tags in view, per-frame error vs cable sigma separated. No placeholder.
16. Evidence table with an "Observed, not instrument-measured" group; first-test strip.
17. Deletions and lessons: five deletions (yaw guard removed).
B1 jaw kinematics; B2 control architecture; B3 Rev D board (pill PLANNED only; PLANNED card); B4 floor-board study (two-tag and four-tag lines); B5 thermal network (PLANNED card: fin FEA); B6 v7 gearbox; B7 safety (stud anchors marked as open items).

## Before sending

These were "Need from Jasper" and "check before saying" lines in the notes; they are deliberately not in the file.

File and notes
- The file name still carries "SpaceX" (assigned path). Rename (for example `RoomCleaner_Buntinx_Oct27.pptx`) or share the PDF only. The notes travel with the PPTX; the PDF has none.
- The first-person lines in the notes (slides 2, 6, 7, 9, 11, 13) are conditional: use each only if it is true.
- The planned-card heading is now "PLANNED — not yet run" (kit default in `deck_kit.js`, `plannedCard`). The original brief used "PLANNED — result after the Oct 22 test"; switch back only once the tests are actually scheduled.

Per slide
- 1: confirm title wording. Photo 13 shows the gen-1 station lifting the test weight; no weight or result is recorded, so the slide claims none.
- 2: confirm the true start date (Jul 16 in git, Aug 6 in the old outline); printer and filament; how many stations actually exist (title says "four-winch" as a design); prepare a truthful answer to "what did you write yourself?" (software and the control architecture are the most likely probe).
- 3: weigh a representative pair of jeans; decide which claw mass you will defend (450 g requirement vs the unweighed 1.05 to 1.25 kg estimate).
- 4: a weighed claw (every capacity number uses the 0.45 kg budget). "Max 0.5 kg / 1.1 kg" are one-phase upper bounds (about 0.35 / 0.78 kg if two-phase).
- 5: pull-test readings (the sheet runs full-step, the winches run 1/16 microstep); decide 3:1 vs Ø10 core vs lighter payload for the demo; confirm which Vref reading is right (0.79 V on Oct 21, 0.85 V) and VDD = 3.3 V at the driver; measure the line diameter (0.5 mm assumed; 0.6 and 1.0 mm appear in the record); the 12.6 N low end uses the 0.85 V basis (0.79 V takes a further 7 % off).
- 6: what first made you suspect heat; which of the seven options you actually considered and why each lost (keep the stated reason only if true); a thermometer reading; coil resistance with a meter; fin alloy (magnet or file test; k = 160 assumed) and finish (model assumes a black fin, the part is bare; bare reads about 41 to 43 °C vented, 46 to 50 °C sealed). Hold-test length: 60 minutes on the vented shell per the plan and the thermal manual; the fundamentals sheet assumed 90 minutes. The storyline's "70 to 100 °C" for the PETG joint is not in the fundamentals (sealed, no fin: 64 °C) and is not used.
- 7: who produced the 1/8 in shop drawing (the slide says "drawing"; say "I drew" only if true); photo of the fin installed in a station; hole-position tolerance (calipers), time per fin, scrap; why 0.019 in and why 250 mm; the drawing says a Ø22.5 pilot, the storyline and photo README say 7/8 in (22.225 mm), the slide says 7/8 in; photo 03 (mill set-up with the printed drawing) is unused.
- 8: v2 and v3 printed-bore caliper readings (the slide says "no caliper reading yet"; change if one exists); why Ø20 to Ø15 and 26 to 16 mm; whether a level-wind was considered; the 14.5 mm is derived from CAD dimensions, not measured.
- 9: what you noticed that showed the bead would ride over the groove (your find); whether rev D was printed; real bead diameter; rev C was found by the geometry verification, say it that way. Photo 09 is a bench microswitch, not the arm.
- 10: SolidWorks results (peak stress, SF, exit deflection); the slide-in retention (a positive lock is open); what the gen-1 plate tests (photos 05, 13) showed. The study manual `docs/simulation/SW_STATIC_STATION_MOUNT.md` expects the motor-tab root to read 8 to 14 MPa against 8.33 MPa and calls it a design-finding study. With a 3:1 reduction the station study is redone at about 2.7 times the load.
- 11: when and why module 1.5; whether you specified the 36T / 2:1 / R53 change (the rebuilt v6r set was produced and checked in the repo); weighed claw mass and new budget; why a 12 in aluminium tube; the 157 g to 96 g comparison is v6 vs v6r, the safety factors are the v7 gear train (B6): say which is current.
- 12: tube wall and alloy (3 mm CAD wall assumed; a 1 mm wall saves about 12 g, not 33 g); re-extract the centre of mass; the hero render is the superseded v6 head.
- 13: harness length numbers; whether a central-stepping fallback remains for the 1 lb demo; the review (not you) priced the sync cost unless you did; 16 AWG is preferred, not purchased; photo 14 is the assembled gen-1 shield, so "July" is only the decision date.
- 14: exact readings and dates (VDD, SLEEP, ENABLE) and VDD after the repair; what the bad connection physically was; what you tried first; whether the XIAO that heated and lost USB is quarantined; the 1.14 V was reported, not logged or photographed; photo of the built perfboard (Rev D is a layout only).
- 15: what led to the margins decision and the slack probe; any hardware test planned; re-extract the centre of mass (the 13° uses the stale 0.196 m depth, the current estimate gives 20.7°); the 0.7 mm needs four tags in view (two tags: 2.5 mm); calibration counts (6/6, 3 of 6, 91 to 97 %) come from an implementer report marked "independent verification pending".
- 16: anything measured since Oct 20; confirm the pass limits; the 18 V supply reading (12 V label, 20 V buck input limit) is unresolved.
- 17: what the yaw guard was (removed from the slide); the −560 g open-frame figure is head 1,044 g to 481 g in CAD; "the 5 lb reserve: a 1 lb gate first" replaced the contactor e-stop line in an edit made outside this pass, confirm you want it.
- B3: schematic image if wanted; photo of the built board. B5: fin FEA results after the study. B6: the gripper_v7 render is marked work in progress in the asset README. B7: confirm the stud anchoring and charging statements match what you do, and which charger.

Mechanics
- Chart limit lines and the 1,050 to 1,250 g band are drawn shapes positioned from each chart's fixed plot layout; they will not follow if a chart is resized by hand.
- Pills, footer and rail dot numbers are 9 pt per the style guide; all other text is 11 pt or larger.
- `build_style_sampler.js` `photo()` stretches photos whose aspect differs from the box; `deck_kit.js` `photo()` keeps the aspect (the sampler was not changed).
- Commit 7135d7c (a parallel session) swept an early partial copy of the deck files into history; the working-tree files are newer and uncommitted. Nothing was committed or pushed by this build.

## Change log by fact-check finding

Applied as suggested or in close form:
- F01 (High): torque-basis range shown. Slide 4 design-force band 8.4 to 11.9 N, rail "Max 0.5 kg ... 1.1 kg", notes with the two-phase capacities; slide 5 full-spool pull 12.6 to 17.9 N (core 16.8 to 23.8 N) in rail and fundamentals, chart axis "upper bound", notes; slide 10 target at 34 N (24 N if two-phase); slide 16 first test and notes.
- F02 (High): slide 4 title "Cable angle sets the limits: walls bind at task height, ceiling above." (lead's wording, 12 words); rail 4 "Max 0.5 kg at 0.4 m, 1.1 kg at task height."; matching notes and Q&A.
- F03 (High): slide 5 title "The driver, not the motor, capped my pull; the fix is open."; rail 3 "Run at the cap; open: core +25 %, or 3:1 gearing."; all bars steel (Ø10 un-highlighted).
- F04 (High): slide 15 hero sub, label, fundamentals (1.32 mrad, two tags 4.85 mrad = 2.5 mm); B4 title "up to 10×", two-tag and four-tag lines, notes.
- F05 (High): slide 7 title "Drawn at 1/8-inch, built at 0.019-inch, then rechecked the physics." (neutral, 10 words), rail 1 "Drawing: ...", caption "shop drawing"; first-person line in notes.
- F06 (High): slide 2 title, bought and made lists, tag legend; notes rewritten without "wrote the control logic"; first-person line.
- F07 (High): slide 11 title, rail 3, notes SAY; first-person line.
- F08, F09 (Medium): slide 4 equation "(claw centred, equal share)", D_h defined, off-centre note, legend "(budget)", rail 5 "0.45 kg is a budget".
- F10 (Medium): slide 5 hero range 0.79 to 0.85 V and 0.99 to 1.06 A; slide 16 "Vref pot maximum 0.79–0.85 V"; first test adds VDD.
- F11 (Medium): slide 6 title "A sealed station would heat the motor mount, my most loaded joint." (12 words); rail 4 sealed and vented pairs; planned card on the vented shell (41 °C predicted); chart orders sealed first.
- F12 (Medium): slide 6 notes neutral ("a design review listed seven options"); first-person line.
- F13 (Medium, partial): slide 7 rail 2 "As built: 0.019 in (0.48 mm) sheet, not the 1/8 in drawn."; alloy and finish caveats in notes and above. "Aluminium" stays on the slides.
- F14, F15 (Medium): slide 8 rails 2 and 5, fundamentals "diameter assumed 0.5 mm (not measured)"; line-diameter caveat in slide 5 notes and slide 16.
- F16 (Medium): slide 9 title "Bead must not cross the pulley; verification caught rev C." (neutral, 10 words), rail 4 "missed in X and Y", fundamentals with 5.0 and 10.5 mm, notes SAY; first-person line.
- F17 (Medium): slide 9 callout "Bench switch, not rev D", card text, pill "CALCULATED · CAD".
- F18 (Medium): slide 10 rails 3 and 4, fundamentals, notes (one check at 34 N and 68 N, hand estimate, 3:1 raises the load).
- F19 (Medium): slide 3 card "Stations designed to screw into wall studs"; B7 card "Stud anchors" with open items; slide 10 notes answer (three dovetail ribs and J-lips, positive lock open).
- F20 (Medium): slide 12 rail 4 "saves ~33 g", fundamentals "assumes a 3 mm wall", notes.
- F21 (Medium): slide 13 title "One controller per winch removes long harnesses; a review priced sync." (11 words), fundamentals marked assumed and illustrative, notes; first-person line.
- F22 (Medium): slide 14 tile "read on my meter (not logged)", rail 4 "Motor moved after repair; Rev D layout net-checked, not built."
- F23 (Medium): slide 16 "Observed, not instrument-measured" group for the fin fit and the 18 V reading.
- F24 (Medium): slide 16 "Winch pull test (luggage scale)" and "Station-mount pull test"; first test "under about 25 N points to a 3:1 reduction (decision open)".
- F25 (Medium): slide 17 yaw guard removed, "−560 g, CAD".
- F26 (Medium): planned-card heading "PLANNED — not yet run" everywhere (see Before sending).
- F27 (Medium): hold test stated as 60 minutes on the vented shell (slides 6, 16, B5 notes; B5 "94 % vented, about 82 % sealed").
- F28 (Medium): slide 3 "0.9 kg" card "Provisional jeans payload plus 2 m/s²; first gate 1 lb".
- F29 (Medium): slide 2 notes "PETG for the structural parts".
- F30, F31, F33, F34, F35, F36, F37, F38, F39 (Low): applied (slide 1 subtitle; slide 8 rail 1; slide 12 fundamentals "ray-cast 172" and caption "v6 head (superseded)"; slide 13 labels "GEN 1 / GEN 2" and 16 AWG "preferred, not purchased"; slide 11 rail 4 "with conditions" and "36T web 1.7"; slide 6 fundamentals and B5 "1260× = 800× from k × 1.6× from thickness"; B6 "333 g"; B3 pill PLANNED only; slide 16 "Grip force required per jaw").
- F40 (Low, partial): notes stripped to what to say, numbers and questions; "generated by" wording removed (B3 says "net-checked by a script").
- Hard questions: Q1 in slide 5 notes, Q2 in slide 6 notes, Q3 in slide 3 and B7 notes (decision IDs removed from the answers).

Not applied, or applied differently:
- F32 (Low, optional): not applied; the slides keep the fundamentals-sheet figures (23.8 and 17.9 N, r = 7.5 and 10 mm); the line-centre figures (23.0 and 18.3 N) are in the slide 5 notes.
- F40, file name: not renamed, because the original brief fixed the path; see Before sending.
- F13: "aluminium" kept on the slides until the alloy test is done.
- F05, F07, F11, F16, F21: the suggested titles were over 12 words, so shortened versions with the same meaning are used.
- Edits made to this file by others during the work (slide 10 rail and fundamentals, slide 16 SolidWorks line, slide 17 last deletion) were kept as the current state; F18 and F25 were applied on top of them.
