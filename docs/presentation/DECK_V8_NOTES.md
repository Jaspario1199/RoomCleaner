# Deck v8: the panel-chair critique applied (Oct 22)

**Source:** v7 plus the critique in `docs/presentation/deck_v7/CRITIQUE_EXEC.md` (a role-played SpaceX executive). The lead
checked each factual claim against `DECISION_STORIES.md`, `FUNDAMENTALS.md`, `verification/deck_factcheck.md` and the code.

**Build:** `docs/presentation/deck_v8/build_deck_v8.js`.

**Outputs:**
- `RoomCleaner_Buntinx_Oct27_v8.pptx` and `.pdf`
- `contact_sheet.png`
- charts in `deck_v8/fig` (the Sheet re-exported after the claw-mass updates)

v1 to v7 are kept unchanged.

**Slide count:** 20 main slides (v7 had 30), then an appendix of 9 slides behind a divider. "Where It Stands Today" was added from the critique and then removed at Jasper's request (Oct 22); its status line is in the Project Goal speaker notes.

**Phases:** the phase is now plain text in the footer ("Phase 2 of 5: Generation 1") instead of five divider slides. The Gantt
chart on slide 4 sets up the five phases.

## Numbers changed in the Sheet (Oct 22)

| Tab | Change | Effect |
|---|---|---|
| Cable tension | Claw mass 0.45 kg (budget) → 0.60 kg (weighed, with battery) | 1 lb test at 0.4 m: 14.3 N static, 17.2 N with 2 m/s², against the 16.8 N limit |
| Lift budget | Weighed claw 600 g, battery included (Jasper) | Jeans case 1.50 kg against 1.56 kg capacity: 0.06 kg (4 %) margin; jeans bar no longer red |

## Critique items: applied

**Status and story**
- **Status upfront:** a "Where It Stands Today" slide was tried and removed at Jasper's request; the status is in the Project Goal speaker notes, and the open risks appear in their phases and in the results table.
- **Five phase dividers and the Questions slide cut:** "Takeaways and Next Steps" stays up during questions.
- **Slides merged:**
  - Gen 1 build with Gen 1 findings;
  - printing and machining with electronics bring-up;
  - thermal verification into motor cooling;
  - thorough and scrappy into decisions.

**Corrected against the project record**
- **Finger claw:** "designed in CAD (419 g of a 450 g budget), never built". The clamp that could not close on thin cloth (Sep 30) and the v6 clamp at 4.6 times its budget (Oct 20) now sit on the claw slide, with their dates.
- **Cable tension:** recomputed with the weighed claw. 0.4 m is the margin for the empty claw; jeans need the claw at least 0.6 m below the anchors. The planner checks every cable against the measured pull limit.
- **Gear story:** module 1.5 with a 16 mm face. The first screening, with module 1 and a 6 mm face, gave a safety factor of 0.35.
- **Accuracy:** cable lengths after the fit are about 12–16 mm (simulated). The 0.7 mm figure is labeled as per-frame camera pose, best case (appendix).

**Added**
- **Grip force:** jeans need 17.7 N per jaw; the jaws give 13.3–25 N. Shown on the claw slide (equation box) and in the results table.
- **Lift uncertainty:** the 4 % margin is inside the uncertainty (1.1 kg capacity at 0.5 × holding torque). The pull test decides.
- **Safe state:**
  - PAUSE holds position; power loss, emergency stop or a reset drops the claw.
  - New appendix slide "Safe State and Failure Modes".
  - A brake or non-backdrivable stage added to next steps.
  - Control-logic Faults row corrected.
- **Room geometry:** a to-scale room elevation on Project Goal. It shows the 2.74 m (9 ft) ceiling, the anchors 0.15 m below it, and the 0.2 m wall and 0.4 m ceiling margins.
- **Station load path:** cable to stud, and the 34 N snag sizing from the static-study manual.

**Wording and tables**
- **Success criterion:** "no human touch; I approve each move on the phone", replacing "no human input".
- **Authorship:** see the section below.
- **Results table:** an Evidence column added (Calculated, Weighed, Built, Not measured).
- **Decisions:**
  - Poor decisions are now: mass not tracked through four claw versions; the scrap prototype fin; the build week ending on presentation day.
  - Bead homing moves to the good side, since it was caught on paper.
  - "Several stations built before one was proven" is held in the notes until Jasper confirms it.
- **Half-time answer:** made specific: pull-test and set the mass budget in week 1; kill the central board, bead homing and fingers on paper; prove one station first.
- **Speaker notes:** a short talk track plus "If asked" material.
- **Interaction points:** "pause and ask" on the Generation 1, Weight Budget and First System Test slides.
- **Units:** SI first, imperial in parentheses. Chart source lines shortened. Title subtitle no longer claims it picks laundry today.
- **About Me:** three larger photo groups instead of seventeen thumbnails; the hiking bullet dropped.

## Authorship (to confirm)

**Slide 4 now reads:**
- "Mine: requirements, design decisions, the SolidWorks station and claw, printing, machining, wiring and bring-up"
- "With Claude Code, under my direction: the control software, calculation scripts and CAD checks"

This extends Jasper's software wording (Oct 22) to the calculation scripts and CAD checks, because the repository record shows
those also came through the Claude Code workflow (`verification/deck_factcheck.md` F05 and F06). **Jasper to confirm the wording.**

## Critique items: not applied, and why

| Item | Reason |
|---|---|
| Replace the trade-off table with a chain diagram | Jasper asked for plain tables and no box diagrams. The table stays, without the October "chosen setting" column, so the concept phase no longer shows later conclusions. The chain is one sentence under it. |
| Delete the "Larger room" row | Jasper asked for this trade-off (more room means more wire resistance) |
| Room plan of cable routes on the controller slide | No route drawing exists. Before and after board photos are used instead; the route lengths are in the notes. |
| Exploded or section view of the station | No such render yet. The screenshot stays, and the load path is in a bullet. |
| Grip-force chart; error bar on the lift chart; 48.9 label on the 60 °C line | Kept as numbers in the bullets and equation box. The Sheet charts are unchanged. |
| Run the pull test before Oct 27 | Jasper's action: it settles the lift margin and the planner's tension limit |

## Still to fill in

The slides no longer carry red placeholders: the version sent on Oct 22 uses neutral wording ("a test weight", "Planned",
"Not yet totaled"). Jasper fills these in on his own copy before Tuesday:

- Generation 1 test weight (slide 8)
- First-test results (slide 17; "Planned" today) and the calibration pass limit (≤ 20 mm proposed)
- Cost: the budget and the total (slide 18)
- One EcoFil result number (About Me notes)
- How 1.5 A was reached, and the Vref reading (Winch Pull notes)
- Number of stations built (Project Goal notes)

Send the PDF to the recruiters: the PPTX speaker notes are a coaching track ("Pause and ask", "If asked") meant for Jasper only.

**About Me (Oct 22, Jasper):** photos only, the three collage columns filling the slide; the degree, EcoFil, Gladiator Dash role and Ironman are in the speaker notes.

## Appendix kept on file; its data moved into the talk (Oct 22, Jasper)

The main deck has no appendix: 20 slides, ending on "Takeaways and Next Steps". The appendix builds as its own file with
`PART=appendix` (same script): `RoomCleaner_Buntinx_Oct27_v8_appendix.pptx` / `.pdf` (divider plus 9 slides).

**Data moved onto related slides** (Jasper: "having excessive data/graphs on a slide is perfectly fine"):

| Appendix slide | Now on |
|---|---|
| Control Logic: Generation 1 vs. Final (table) | One Controller per Winch, under the before/after photos |
| Floor Board Accuracy (chart) | Camera Calibration Replaces Bead Homing, under the bead-homing chart |
| Claw Electrical | Claw slide, as a power bullet (schematic stays on file) |
| Heat Fin Length (chart) and Fin Sizing for 4 W (table) | Motor Cooling: two charts, the table and the P = I²R box |
| Operating Sequence (phone app screens) and Safe State and Failure Modes (table) | First System Test |
| Calculations and Sources | Results Against Targets: link to the calculation sheet; the chart captions name the sources |
| Acronyms | On file only (each acronym is written out on first use) |

## Calculation sheet simplified (Oct 22, Jasper)

The Google Sheet keeps every formula, input and chart in place; only text changed:
- The "Read me" tab (colour key, tab index, change log) was deleted.
- Each tab now opens with a short title and the governing equation on one line.
- Labels carry their symbols ("Claw mass m_c", "Holding torque τ_h"); the "Source" column became a short "Note".
- Results have a "Formula" column; chart-data headers are short, so the chart legends read "Static (N)", "0.019 in sheet", "PETG limit".
- Lift budget row 19 now shows the CAD estimate with battery (0.86 kg) as a formula.

Charts re-exported to `deck_v8/fig`; `deck_v3/sheet_charts.py` also accepts the new "Motor temperature" tab title.

**Beads (Jasper asked):** the camera calibration does the homing; the beads stay on the cables as end-of-travel switches.
The startup self-check needs every switch closed; until a bead is verified, the planner keeps each cable a margin longer than
its bead trip length; a bead search is optional, as a cross-check (D24, D26; `roomcleaner/cdpr/startup.py`). The calibration
slide now says so.

## Weakest link and manufacturing slides (Oct 22, Jasper)

**Which Part Gives First** (Phase 4, after Winch Pull): the Sheet's "Weakest link" chart, five statements and the fuse
equation. Numbers come from `calculations/lift_chain_weakest_link.json`, so a corrected calculation flows into the slide on the
next build. Final Wall Station now gives the full load path and points to it; Results Against Targets gains a "Weakest link"
row; next steps gain the two fixes.

**Manufacturing: Fits and Datums** (Phase 5, after Build): a four-panel detail figure cut from Jasper's STEP files (gear
bearing pocket and its T-slotted entry lip, the slide-in dovetail with its gaps, the fin's mill datums) and a fits table.
To confirm before Tuesday: which spool bore is printed (Ø5.30 in the 10/21 CAD, Ø5.45 in v3), which holes get heat-set
inserts, and the insert part number.

Main deck: 22 slides.

**Update (Oct 22, Jasper):** the "Which Part Gives First" chart slide is taken out; the design idea (the motor is the weakest
link and the encoder reports the overload) is a note on Final Wall Station, with the slip-force box, and the detail is in that
slide's speaker notes for Jasper to elaborate. The Sheet tab "Weakest link" stays as the record.
The manufacturing slide shows shaded snapshots of Jasper's parts (`deck_v8/make_mfg_snapshots.py`, some cut open, no added
dimensions) instead of the drawn detail figure (`make_mfg_figure.py`, kept on file). Takeaways gain "size every part to a load
number"; next steps gain the lighter redesign (`docs/decisions/WEIGHT_REDESIGN_PROPOSAL_20261022.md`) and continuous testing;
Poor decisions gain "parts built far stronger than any load needed". Main deck: 21 slides.

**Links removed (Oct 22, Jasper):** the audience cannot open the calculation Sheet, so the links on Results Against Targets and on the
appendix's Calculations and Sources slide are gone. Chart captions still name the Sheet tab as the source.
