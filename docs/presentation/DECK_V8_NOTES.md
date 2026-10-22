# Deck v8: the panel-chair critique applied (Oct 22)

**Source:** v7 plus the critique in `docs/presentation/deck_v7/CRITIQUE_EXEC.md` (a role-played SpaceX executive). The lead
checked each factual claim against `DECISION_STORIES.md`, `FUNDAMENTALS.md`, `verification/deck_factcheck.md` and the code.

**Build:** `docs/presentation/deck_v8/build_deck_v8.js`.

**Outputs:**
- `RoomCleaner_Buntinx_Oct27_v8.pptx` and `.pdf`
- `contact_sheet.png`
- charts in `deck_v8/fig` (the Sheet re-exported after the claw-mass updates)

v1 to v7 are kept unchanged.

**Slide count:** 21 main slides (v7 had 30), then an appendix of 9 slides behind a divider.

**Phases:** the phase is now plain text in the footer ("Phase 2 of 5: Generation 1") instead of five divider slides. The Gantt
chart on slide 5 sets up the five phases.

## Numbers changed in the Sheet (Oct 22)

| Tab | Change | Effect |
|---|---|---|
| Cable tension | Claw mass 0.45 kg (budget) → 0.60 kg (weighed, with battery) | 1 lb test at 0.4 m: 14.3 N static, 17.2 N with 2 m/s², against the 16.8 N limit |
| Lift budget | Weighed claw 600 g, battery included (Jasper) | Jeans case 1.50 kg against 1.56 kg capacity: 0.06 kg (4 %) margin; jeans bar no longer red |

## Critique items: applied

**Status and story**
- **Status upfront:** new slide 4, "Where It Stands Today": built, measured, open risks, this week's tests.
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

**Slide 5 now reads:**
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

- Number of stations built
- Generation 1 test weight
- Cost: the budget and the total
- The calibration pass limit (suggested ≤ 20 mm, to confirm)
- Test results
- One EcoFil result number
- How 1.5 A was reached, and the Vref reading
