# Deck QA notes (draft)

Build: `NODE_PATH=<pptxgenjs, react-icons, react, react-dom, sharp> APPLY_THEME=<pptx skill>/scripts/apply_theme.js SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck/build_deck.js`
Outputs: `RoomCleaner_SpaceX_draft.pptx` (24 slides) and `RoomCleaner_SpaceX_draft.pdf`. `deck_kit.js` is the shared visual system; `assets/c050_open_jaws_panel.png` is a crop made by the build from `renders/claw_tube_length_view/c050_Dstar140.png`.
Checks run: all 24 slides rendered to PNG (LibreOffice, then `pdftoppm`) and inspected one by one; `validate.py` passes. Every figure typed into slide text is asserted against `calculations/presentation_fundamentals.json` before the file is written.
Not tested: PowerPoint itself (Arial, Calibri and Cambria were rendered with metric-compatible Liberation Sans, Carlito and Caladea).

Pattern on slides 4 to 15: eyebrow, claim title (at most 12 words), evidence pill(s) top right, hero left, vertical WANTED / REALIZED / DECIDED / RESULT / BUT rail right (active step in Signal, one line each, at most 12 words), fundamentals box under the rail, PLANNED card under the hero where a result is not in. The rail lines are the only body text: 33 to 43 words per slide (4 to 12 per line), more than the 30-word target because five rail lines are required; the detail is in the notes.

## Slides

1. Title: photo 13 (gen-1 station lifting the test weight), title, name, Oct 27 2026. Need: confirm title wording.
2. What I built: timeline Jul 16 to Oct 27, bought vs made, evidence-tag legend. Need: true start date (git says Jul 16, old outline said Aug 6), printer and filament.
3. Done means: claw v6 and station v3 renders, five requirement cards (0.9 kg, 450 g, studs, one switch, nobody under). Need: weigh a real pair of jeans; claw mass you will defend.
4. Cable statics: native scatter of tension vs depth (static, +2 m/s², 11.9 N design-force line). Need: weighed claw (every capacity number uses the 0.45 kg budget).
5. Drive: 0.85 V to 1.06 A, native chart of largest claw per spool core with the 450 g budget line and the 1,050 to 1,250 g printed-claw band. PLANNED card: luggage-scale pull test. Need: pull-test readings, decision D31 (3:1 vs Ø10 vs lighter payload).
6. Heat: native chart, motor temperature by enclosure with no fin, as-built fin and 1/8 in fin, 60 °C target. PLANNED card: hold test. Need: reason you suspected heat, other options you weighed, any thermometer reading, measured coil resistance.
7. Building the fin: photos 06, 01, 16 (callout on the 7/8 in hole), native efficiency chart 74 % vs 37 %. PLANNED card: hold test (buzz, bow, thread depth). Need: photo of fin in the station, hole tolerances, time per fin, scrap, why 250 mm and 1/8 in. Photo 03 is not used.
8. Spool: renders of gen-1 spool, v2, v3 and the three dimension changes. No placeholder. Need: v2/v3 caliper readings, line diameter, why Ø20 to Ø15, level-wind answer.
9. Homing switch: photo 09 with roller callout; rev C 5 mm / rev D 3.75 mm overlap. PLANNED card (not yet run): trip test. Need: what you noticed, whether rev D was printed, real bead diameter.
10. Removable station: wall frame and slide-in renders, pass limits (8.33 MPa, SF 3, 0.5 mm at 34 N). PLANNED card: SolidWorks study and pull test, no results shown. Need: study results, retention mechanism and load, what the gen-1 tests showed.
11. Gripper: native chart of grip force needed vs available, before/after gear renders (157 g to 96 g). No placeholder. Need: why module 1.5, any test gear, weighed claw and new budget, why a 12 in tube.
12. Camera and tube: claw render with camera-bay callout and the 140 mm hover view. No placeholder. Need: tube wall and alloy, re-extracted centre of mass.
13. Distributed electronics: photos 14 (July) and 10 (October). PLANNED card (not yet run): four-station test. Need: harness numbers, whether a central fallback remains.
14. Bring-up: photo 07, 3.3 V expected vs 1.14 V read. PLANNED card (not yet run): meter checklist on the as-built board. Need: exact readings and dates, what the bad connection was, what you tried first, photo of the built board.
15. Calibration: drawn floor board (250 mm pitch, 6.6 mm to 0.7 mm). No placeholder; everything simulated. Need: what led to D26, any hardware test, re-extracted centre of mass.
16. Evidence table: measured, calculated, simulated, planned with pass limits; first-test strip. Need: anything measured since Oct 20, hold-test length.
17. Deletions and lessons (dark): six deletions, three lessons, contact line. Need: what the yaw guard was and the source of the -600 g open frame.
B1. Jaw kinematics: native scatter of jaw force vs gap (13.3 to 43.6 N), three stat tiles. No placeholder.
B2. Control architecture: host, four stations, lease, feed-hold, stop never disables. No placeholder (all simulated).
B3. Rev D board: perfboard layout with three callouts. PLANNED card (as-built meter checklist). Need: schematic image if wanted, photo of the built board.
B4. Floor-board attitude study: two native charts (tilt by CoM depth, tilt noise vs range). No placeholder.
B5. Thermal network: node diagram, PETG vs aluminium table. PLANNED card: fin FEA after the SolidWorks study (no result shown).
B6. v7 open-frame gearbox: gripper_v7 render, native safety-factor chart (render is marked work in progress in the asset README). Need: final render if one exists.
B7. Safety: four icon cards (power strip, studs, nobody under, balance charging). Need: confirm the stud and charging statements.

## Flags for Jasper and the lead (details in the speaker notes)

- Hold-test length conflicts: storyline and `SW_THERMAL_HEAT_FIN.md` say 60 minutes (vented shell); `FUNDAMENTALS.md` section 3 says 90. Slides say "hold test" without minutes; the 46 °C figure is the sealed case, the planned test reads the vented case (41 °C predicted).
- Slide 4: "walls bind before the ceiling" holds at task poses (1.1 x weight); at the 0.4 m ceiling limit the same linear program allows only 0.50 kg (2.42 x weight). The slide says "at task heights".
- Slide 6: the storyline's "70 to 100 °C" for the PETG joint is not in `FUNDAMENTALS.md` (sealed, no fin is 64 °C); not on the slide.
- Slide 7: drawing notes say a Ø22.5 pilot hole; the storyline and photo README say 7/8 in (22.225 mm). The slide says 7/8 in.
- Slide 15: "about 13°" uses the stale 0.196 m centre-of-mass depth; the current estimate gives 20.7°. The slide says 13 to 21°.
- Slide 5: three meanings of "tension" (running 23.8 / 17.9 N, design 11.9 N, snag 34 N); the old 43 N and 750 g figures are not used.
- Slide 14: the photo does not show the meter reading; only the 1.14 V and 3.3 V figures are claimed.
- `build_style_sampler.js` `photo()` passes the box size as the image size, which stretches photos whose aspect differs from the box; `deck_kit.js` `photo()` keeps the aspect ratio (cover crop with a focus point). The sampler was not changed.
- Chart limit lines and the 1,050 to 1,250 g band are drawn shapes positioned from each chart's fixed plot layout; they will not follow if a chart is resized by hand.
- Pills, footer and rail dot numbers are 9 pt as set by the style guide; all other text is 11 pt or larger.
- Slide 12 uses a derived crop of the camera-view figure; the figure's own axis text is small.
- A parallel commit (7135d7c) swept an early partial copy of the deck files into git history; the working-tree files here are newer and uncommitted. Nothing was committed or pushed by this build.
