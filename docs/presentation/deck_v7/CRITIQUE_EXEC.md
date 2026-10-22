# RoomCleaner deck v7: critique from the panel chair

**Reviewer:** senior engineering executive on the interview panel (role-play).
**Deck reviewed:** `RoomCleaner_Buntinx_Oct27_v7`, 38 slides (1 to 30 main, 31 to 38 appendix), rendered PNGs and the on-slide text and speaker notes in `review_v7/`.
**Cross-checked against the project's own record:** `docs/presentation/FUNDAMENTALS.md`, `docs/presentation/DECISION_STORIES.md`, `DECISIONS.md` (D37), `REQUIREMENTS.md` (R7), `verification/deck_factcheck.md` (Oct 21), `verification/gripper_v6_inspection.md`, `docs/simulation/SW_THERMAL_HEAT_FIN.md`. Where I recomputed a number, the arithmetic is shown.
**Red brackets:** not criticized for being empty. Section 4.5 lists the ones that would hurt if still empty on October 27.

---

## 1. Verdict

He thinks like an engineer: he prices trade-offs, tags numbers as "calculated", and titled his own biggest problem "Weight Budget: Open Issue" instead of burying it, which most candidates never do. But the load-bearing numbers do not survive a calculator. The cable-tension slide still uses the 0.45 kg budget claw, not the 0.60 kg claw he weighed. The lift capacity is quoted to 3 % on an unmeasured torque assumption worth ±30 %. And "Finger claw could not pinch fabric and was 4.6 times over its mass budget" is contradicted by his own records: the finger claw was never built, and the 4.6 times belongs to a later clamp. Nothing has picked up a garment yet, and "Solo project: requirements, calculations, all CAD" claims more than his repository shows. As delivered I am a lean no, because I cannot tell which numbers to trust. With the numbers reconciled, a measured pull test, and a plain statement of what the AI tooling did, this becomes a strong new-graduate presentation.

---

## 2. Story and flow

### 2.1 Does the arc hold?

The skeleton is right. Five chronological phases, a Gantt chart that sets them up (slide 4), and a goal on each divider make the talk easy to follow. The beats the panel asked for are in the wrong places, though:

| Beat the panel asked for | Where it is now | Problem |
|---|---|---|
| What the problem was | Slide 3 | No picture of the system in the room, no ceiling height, and "Success ... with no human input" contradicts slides 6 and 34 |
| What was decided, and why | Slides 6, 13, 14, 15, 18 | The alternatives live only in the speaker notes. Each slide shows the winner, never the losers or the numbers that beat them |
| What failed (brief: "upfront") | Slide 11 (a paper result plus a misattributed claim), slide 20 (about minute 30), slide 26 ("Not met") | The first honest status arrives at minute 30. A SpaceX reviewer wants the bottom line in minute 3 |
| What was learned | Slide 29, sharing space with next steps | Squeezed into three sub-bullets at the very end, where time runs out |
| What comes next | Slide 29 | Fine, but the most important next step (the pull test) should already be done |

The deck is mostly analysis about hardware that is about to be built. Of the 23 content slides, 7 carry calculated charts (slides 8, 11, 13, 14, 18, 19 and 20), and 2 more are tables of calculated values (slides 7 and 26). The measured facts in the main deck are the claw mass (0.60 kg), the 1.14 V logic rail, one bore printed too tight (Ø5.2 on a 5 mm shaft), fin holes at ±0.1 mm, and a driver Vref of 0.85 V (notes only). That is the entire measured record. Say so on a status slide in minute 3, so the panel does not discover it on slide 26.

### 2.2 Where I got lost, bored or confused

**Lost**
- **Slide 7.** October's final settings ("1.5 A, vented shell and heat fin", "Module 1.5 gears") appear inside the July "Concept" phase. I am handed the conclusions before the problems that produced them.
- **Slide 11.** "Finger claw could not pinch fabric". Slide 10 shows that claw only as CAD. Was it ever built or tested? Per `DECISION_STORIES.md`, no: "the five-finger claw was never built (no print recorded)".
- **Slide 14.** 6.6 mm, then 2.5 mm, then 0.7 mm. Averaging four independent tags gives √4 = 2 times better, not 9 times. Nothing on the slide or in the notes explains the extra factor (it is geometry: spread-out corners, best-case placement).
- **Slide 15.** The caption says "v6 clamp". What were v1 to v5, and what killed each one? The best failure-and-iteration story in the project is compressed into a caption.

**Bored**
- **Slide 13.** The 820 versus 164 comparison appears three times: in a bullet, in the bars, and in the equation box.
- **Slide 25.** A placeholder plus a table that repeats slide 19's numbers.
- **Slide 28.** The mill photo again (it is already on slide 22), and "gears checked before printing" for the third time (slides 15 and 27).
- **Five dividers** (slides 5, 9, 12, 16 and 21) with no information on them.

**Confused**
- **Slide 3 against slides 6 and 34.** The slides say "Success: one garment to the hamper with no human input", and also "Every move waits for approval on the phone".
- **Slide 8 against slide 20.** The weight basis on slide 8 is 0.45 kg + 0.454 kg (notes). Slide 20 is 0.60 kg + 0.10 kg + payload. Which claw is the robot carrying?
- **Slides 20, 26 and 27.** One problem carries two overages: "0.04 kg" over capacity, and "0.15 kg" over a 0.45 kg budget that is never derived.
- **Slide 16.** The goal reads "Size the winch, the cooling and the weight in SolidWorks". The sizing on slides 18 to 20 is hand calculation and a spreadsheet, and the weight is a scale reading.

### 2.3 Order

The present order is chronological and mostly sound. Four changes:

1. **Put the status first.** Add a "Where It Stands Today" slide right after the Project Goal: what is built, what is measured, what is failing, and what gets tested this week.
2. **Move slide 7 (trade-offs) out of the Concept phase.** Either make it the closing summary (after slide 20), or strip it to the concept-phase levers without the October values.
3. **Merge slide 25 into slide 19.** The thermal plan belongs next to the thermal result.
4. **Merge slide 28 into slide 27,** and end on slide 29. Leave slide 29 up during questions instead of a "Questions" slide.

Proposed running order (22 main slides, down from 30):

| New # | Slide | Source |
|---|---|---|
| 1 | Title | 1 |
| 2 | About Me | 2 (fewer photos) |
| 3 | Project Goal, with a room sketch | 3 |
| 4 | Where It Stands Today (new) | new; failures upfront |
| 5 | Timeline, Scope and Who Did What | 4, with failure milestones on the Gantt chart |
| 6 | Why a Cable Robot | 6, with the concept comparison |
| 7 | One Chain Sets Every Limit | 7, reworked as a diagram |
| 8 | Cable Tension Sets the Ceiling Margin | 8, recomputed |
| 9 | Generation 1: What the Bench and the Math Showed | 10 + 11, corrected |
| 10 | One Controller per Winch | 13, reworked |
| 11 | Camera Calibration Replaces Homing | 14, honest accuracy |
| 12 | Claw: Four Versions to a Parallel Grip | 15, with the iteration strip and grip force |
| 13 | Final Wall Station and Its Load Path | 17 |
| 14 | Winch Pull at 1.5 A | 18, with the measured pull if possible |
| 15 | Motor Cooling and How It Will Be Verified | 19 + 25 |
| 16 | Weight Budget: Open Issue (your call) | 20, with an uncertainty band |
| 17 | Build: Printing, Machining, Bring-Up | 22 + 23 |
| 18 | First System Test | 24 |
| 19 | Results Against Targets | 26, with an evidence column |
| 20 | Good and Poor Decisions; Thorough and Scrappy | 27 + 28 |
| 21 | Takeaways, Half the Time, Next Steps | 29 |
| (22) | Spare slot, if one is needed, for the claw iteration strip on its own | |

### 2.4 Are the phase dividers worth their time?

No. Each costs a transition and about 15 seconds, and together they make up 17 % of the main deck with zero information. Slide 4's Gantt chart already gives the structure. The Phase 5 divider announces a phase that has not happened at the time of writing. Cut all five, and carry the phase in the footer, which is plain text, not a chip or tracker: "Jasper Buntinx | RoomCleaner | Phase 2 of 5: Generation 1 (August)".

If he insists on keeping them, each divider must earn its slot with one question and one verdict. For example, slide 9: "Question: can one printed winch lift a load? Answer: yes, [weight] at [speed]; but homing and wiring would not scale."

### 2.5 Is the time budget realistic?

The notes for slides 1 to 30 total 2,372 words, which is about 17 minutes at reading speed. Real delivery, with pointing at figures and transitions, runs 1.8 to 2.2 times that: **30 to 38 minutes uninterrupted.** An interactive review with this panel adds 15 to 25 minutes of interruptions. **Thirty slides do not fit in 60 minutes with questions.** The slides that get rushed or skipped would be 26 to 29, exactly the ones the brief asks for.

| Block | Now (slides) | Proposed (slides) | Proposed minutes |
|---|---|---|---|
| About me | 1 | 1 | 1.5 |
| Problem, status, timeline | 2 | 3 | 4 |
| Concept | 4 (with divider) | 3 | 5 |
| Generation 1 | 3 | 1 | 2.5 |
| Redesign | 4 | 3 | 6 |
| Final design | 5 | 4 | 7 |
| Build and test | 5 | 2 | 4 |
| Results, decisions, lessons | 5 | 3 | 5 |
| **Talk total** | **30** | **21 to 22** | **about 35** |
| Interruptions plus final questions | | | **about 25** |

**The notes are number dumps.** Slide 15's notes read out four link lengths ("ground 36.5, crank 53, rocker 50, coupler 34.7 mm") and four tooth counts. Slide 22's notes read out five hole sizes. Nobody retains more than two spoken numbers per slide. Rule for every note: **one claim, at most two numbers, one "so what"**, kept under 60 words. Everything else moves to a "Q&A ammunition" list under the note, marked "only if asked".

### 2.6 "An interactive design review, not a lecture"

Nothing in the deck invites the panel in, and the brief explicitly asked for that. Plant three decision points where he stops and asks:

- **Slide 11 (bead homing):** "Before I show you what I did: how would you home a four-cable robot without a reference pose?"
- **Slide 20 (weight):** "Jeans are 45 g over. Cut 45 g from the claw, add a 2:1 gear stage, or ship with a 1 lb limit? Which would you pick?"
- **Slide 24 (first test):** "Here are my pass limits, set before the run. Which one would you tighten?"

That is how the review becomes a conversation, and it shows confidence.

---

## 3. Slide by slide (main deck, 1 to 30)

Format for each slide: **Verdict**, then fluff, figure, statements and numbers, missing justification, and the question I would ask (with whether the slide or notes answer it).

### Slide 1: "RoomCleaner": KEEP, small rework
- **Fluff:** none.
- **Figure:** two real photos (a Generation 1 corner plate with motor and spool, and the disassembled claw). Real hardware on the title slide is good. Neither photo shows the robot working or the final design, so caption them: "Generation 1 station (August)" and "Claw parts (October)".
- **Statements:** the subtitle "A cable-driven robot that picks laundry up off the floor" is present tense for something that has not yet picked up a garment (slide 26: "Speed: Not yet run"). Change it to "A four-cable ceiling robot designed to pick laundry off the floor".
- **Question:** none.

### Slide 2: "About Me": KEEP, rework the figure
- **Fluff:** "Hiking, canyons and cliff jumping". It adds nothing for this panel, and cliff jumping is an odd signal to a safety-minded room. "Mechanical Engineering, Texas A&M University, class of 2027" repeats the title slide's affiliation. Only the class year is new.
- **Figure:** a 17-thumbnail collage. At projection size the Strava screenshot, the EcoFil CAD and the schematic are unreadable, and the brief says "only [graphics] you can defend in depth". Use three large images: EcoFil (shredder, dryer and extruder, labeled), the 70.3 finish, and a Gladiator Dash obstacle he built or repaired.
- **Statements:** "Built EcoFil, a filament recycler" is a name, not a result. Add one number: filament diameter tolerance, throughput, or what broke and how he fixed it.
- **Missing:** why this panel should care. One sentence: "I build things end to end, and I finish long things."
- **Question:** "What failed on EcoFil, and what did you change?" Answered? No. The notes say "what you learned building it" but give no content.

### Slide 3: "Project Goal": REWORK
- **Fluff:** "3D-printed PETG ... on a hobby budget". That is a constraint, not a goal, and "hobby budget" is not a number.
- **Figure:** the station CAD (green shell with the fin) and the claw CAD. Neither shows the system. The single most useful picture in the whole talk is missing: **a to-scale room sketch** showing the 11 × 9 ft floor, the 9 ft ceiling, four anchors about 0.15 m below the ceiling, the hamper, the claw on four cables, and the 0.2 m wall and 0.4 m ceiling keep-outs. Keep the two CAD images as small insets.
- **Statements:**
  - "Success: one garment to the hamper with no human input" contradicts slide 6 ("a phone app ... approves it") and slide 34 ("Every move waits for approval on the phone"). Fix: "Success: one garment from floor to hamper with no human touch; I approve each move on the phone."
  - "Design load: jeans, 0.9 kg, at 2 m/s²; first test with 1 lb" mixes units in one bullet. Use "0.9 kg jeans; first test 0.45 kg (1 lb)".
- **Missing justification:**
  - The ceiling height (9 ft, which is in `FUNDAMENTALS.md` but on no slide).
  - Where 0.9 kg comes from (weighed jeans, or a guess?).
  - Why 2 m/s² when the top speed is 50 mm/s. At 2 m/s² the claw reaches 50 mm/s in 25 ms, so 2 m/s² is really a 1.2 times dynamic allowance for stops and snags. Say that.
  - The cycle-time target. A 4.3 m diagonal at 50 mm/s takes 86 s, plus about 40 s down and 40 s up.
- **Question:** "Why does a floor-picking robot need 2 m/s² if it never goes faster than 50 mm/s?" Answered? No.

### Slide 4: "Timeline and Scope": KEEP, rework
- **Fluff:** the Dates column repeats the Gantt bars. Acceptable.
- **Figure:** the Gantt chart is clean and readable, and it is the right roadmap. It wastes the chance to show failures upfront. Add milestone markers on the bars: "bead homing rejected", "clamp V1 cannot pinch (Oct 12)", "v6 clamp 4.6 times its mass budget in CAD (Oct 20)", "drivers to 1.5 A (Oct 22)", "claw weighed 0.60 kg". Now the timeline tells the story, failures included.
- **Statements:** "Solo project: requirements, calculations, all CAD (computer-aided design), printing, machining, wiring and [software parts you wrote]" is the most dangerous line in the deck. See section 4.4. The record shows most of the parametric CAD, the calculation scripts, the verification, and the software came through an AI-agent workflow (`verification/deck_factcheck.md` F05 and F06: "143 of 180 commits authored 'Claude'").
- **Missing:** hours spent, total cost, shop access (whose mill?), and any mentor or reviewer.
- **Question:** "Which of these numbers did you derive yourself, and which did a tool derive that you then checked?" Answered? No. The bracket invites the question.

### Slide 5: divider "Phase 1: Concept": CUT
- **Fluff:** the entire slide. "Choose the architecture and set the limits" is the title of the next two slides anyway.

### Slide 6: "Why a Cable Robot": REWORK
- **Fluff:** none, but the slide answers "what", not "why".
- **Figure:** a textbook cable-robot schematic (anchors a1 to a4, lengths L1 to L4, claw at p). It is readable and supports "The four cable lengths set the claw position". It does not support the title. The alternatives (a floor robot and a gantry) exist only in the notes. Add a three-column comparison next to the figure (floor robot, gantry, cable robot) with four rows (reach, floor footprint, moving mass, cost), and one-line kill reasons for the losers. That is the biggest architecture decision in the project, and it gets zero on-screen evidence.
- **Statements:** "the whole floor is reachable" is not true for the loaded claw near the walls (see slide 26). Use "the whole floor is reachable from above".
- **Missing justification:** the cost of the choice. Cables only pull, and four cables on three translational degrees of freedom are statically indeterminate, so tension sharing depends on cable-length errors (see slide 13). This is the deep cable-robot question, and the deck never raises it.
- **Question:** "Four position-controlled steppers on three degrees of freedom: who decides how the load splits between the cables?" Answered? No.

### Slide 7: "Design Trade-offs": REWORK into a diagram, and move it
- **Fluff:** the "Larger room" row. The room is fixed (his own room), so it is not a lever. "Larger safety margins: No skipped steps or wall contact" is two unrelated margins in one row.
- **Figure:** a table, not a graphic. The brief asks for at least one graphic per slide. The real message is the single bullet under the table: "A heavier claw needs more pull, more pull needs more current, and heat rises with the square of the current". **Draw that chain**: claw and load mass, then cable tension (1.1 times the weight at task height, up to 2.4 times near the ceiling), then motor current (pull proportional to I), then heat (proportional to I²), then the PETG 60 °C limit. Write the lever and the chosen setting under each arrow. It becomes the spine of the whole talk.
- **Statements:**
  - "Smaller spool radius | ... | Slower line speed" names the wrong cost. At 50 mm/s on a 10 mm radius the spool turns under 1 rev/s, so line speed never binds. The binding constraints are the braided line's bend ratio (core diameter ÷ line diameter: Ø15 / 0.5 mm = 30, against a recommended 20 minimum), the M3 set screw and the Ø1.4 tie-off hole (`FUNDAMENTALS.md` §2; fact-check F03).
  - "15 mm core" is a diameter, while slide 18's chart axis is radius. Say "Ø15 mm core".
  - "Cable tension 12 N to 32 N" uses the stale 0.904 kg mass (see slide 8).
- **Missing justification:** where "Force ÷ 1.5" comes from.
- **Question:** "Which of these six levers actually bound the design?" Answered? No. The answer is current, with heat behind it, and the slide should say so.

### Slide 8: "Cable Tension Limit": REWORK, numbers wrong
- **Fluff:** "Source: RoomCleaner engineering calculations, 'Cable tension' (calculated)". The candidate is citing his own spreadsheet. Shorten to "Calculated (calculation sheet: Cable tension)".
- **Figure:** a clean, readable line chart with the winch design force as a dashed line. It supports "rises sharply near the ceiling". It is plotted for the wrong mass.
- **Statements and numbers:**
  - The notes give W = (0.45 + 0.454) kg × 9.81 = 8.87 N: the 0.45 kg budget claw, no battery, 1 lb payload. The claw was weighed at 0.60 kg, and the battery adds 0.10 kg (slide 20).
  - With the weighed claw, centred, at 0.4 m: 1 lb test (1.15 kg total) gives 15.6 N static and **18.8 N with 2 m/s²**. Jeans (1.60 kg) give 21.6 N static and **26.0 N with 2 m/s²**. Both are above the 16.8 N limit. The bullet "Covers 2 m/s² acceleration within the 16.8 N winch limit" is false for any real configuration.
  - The centred claw is the best case. The project's own linear program puts the worst point at the 0.4 m ceiling at 2.42 times the weight (fact-check F02). At 1.5 A that allows 16.8 / (2.42 × 9.81) = **0.71 kg in total**, which is the claw plus battery (0.70 kg) and nothing else.
- **Missing justification:**
  - The limit that actually protects the loaded claw. The lift budget on slide 20 assumes the claw stays at or below 1.6 m above the floor (0.99 m below the anchors; `DECISIONS.md` D37). If that is the rule, say it on this slide: the loaded claw stays 0.99 m below the anchors, and the 0.4 m margin is the empty-claw end stop.
  - Why a floor-picking robot goes near the ceiling at all.
- **Question:** "Is this with the claw you weighed?" Answered? No. The answer is no, and that ends the slide.

### Slide 9: divider "Phase 2: Generation 1": CUT
- **Fluff:** the entire slide. "Prove the idea on the bench" is only worth saying if the next slide proves it with a number, and that number is a bracket.

### Slide 10: "Generation 1 Build": MERGE with slide 11
- **Fluff:** "One central board drove all four motors" repeats what slide 11 and slide 13 say.
- **Figure:** four images (a bench lift photo, a corner plate, the CNC shield, and the finger-claw CAD). The photos are real and good. The finger-claw CAD on a slide titled "Build" implies it was built. Per the record, it was not.
- **Statements:**
  - "Five flexible TPU (thermoplastic polyurethane) fingers on the claw" reads as built. Change it to "Finger claw: designed (CAD), not built".
  - "A station lifted a test weight on the bench [weight]" is the only physical result of the phase, and it is a bracket.
- **Missing justification:** was a bead ever tripped on real line? `DECISION_STORIES.md` T16 says it is "NOT RECORDED".
- **Question:** "What did it lift, how high, how fast, and what broke?" Answered? Bracket.

### Slide 11: "What Generation 1 Taught Me": REWORK, contains a factual error
- **Fluff:** none.
- **Figure:** the bead-homing chart supports bullet 1 only. The y-axis reads "Reachable working volume (%)", while the title and bullet say "share of the room". Pick one. The mechanism is never drawn, so a reviewer who has never heard "bead homing" sees a curve with no explanation. Add a 3-line sketch: anchor, cable, bead at the outlet switch, and the claw at home, with "cable can never be shorter than this" labeled.
- **Statements:**
  - "Finger claw could not pinch fabric and was 4.6 times over its mass budget" is **wrong on both counts** per the project record:
    - The five-finger claw was never built (`DECISION_STORIES.md`: "never built (no print recorded)"), and its CAD mass roll-up was 419 g against a 450 g budget, so it was under budget.
    - "Could not pinch thin fabric" was the rack-and-pinion **clamp V1** of September 30 (audit Oct 12, T21).
    - "4.6 times" was the **v6 clamp** on October 20 (CAD upper bound at 100 % solid, about 2,061 g; `verification/gripper_v6_inspection.md`).

    Neither happened in Generation 1 (August 6 to September 2).
  - The notes say bead homing "was caught on paper, before it was built", so the title "What Generation 1 Taught Me" overstates it. Use "What Generation 1 Showed, on the Bench and on Paper".
- **Missing justification:** why every bead must trip at one common home pose. The obvious alternative is to put each bead at that cable's shortest operating length and home one cable at a time. If the answer is "homing would then drag the claw into the high-tension zone near an anchor", say so. That is a good answer, and the slide-8 chart already proves it.
- **Question:** "Why not home each cable separately at its own minimum length?" Answered? No.

### Slide 12: divider "Phase 3: Redesign": CUT
- **Fluff:** the entire slide. The notes ("Three decisions, one for each finding") are a good bridging sentence. Say it on slide 11 instead.

### Slide 13: "One Controller per Winch": REWORK the figure
- **Fluff:** the bar chart and the equation box say the same thing as bullet 2. That is triple redundancy.
- **Figure:** decorative. A bar chart of 10 × 82 against 2 × 82 adds nothing a ratio does not. Swap it for a **room plan with the four real cable routes** (6, 21, 23 and 32 ft) drawn twice: central box with 10-conductor bundles, against one 12 V pair plus Wi-Fi.
- **Statements:**
  - "Five times less wire" counts conductor-feet, and copper is cheap. The real benefits are no 32 ft step, direction and encoder signal runs, fewer connectors, and stations testable alone. Say those.
  - "Cost: synchronization moves into software" understates it. The notes say a 50 ms skew at 50 mm/s is 2.5 mm of cable mismatch, which already exceeds the 2 mm pass limit on slides 24 and 26. The record converts it to force: **2.5 mm × 3 N/mm line stiffness = 7.5 N of extra tension** (`FUNDAMENTALS.md` §9), which is 45 % of the 16.8 N design force. That number belongs on the slide.
- **Missing justification:** the communication link (Wi-Fi?), its latency, the clock-sync method, and the skew budget (40 ms gives 2 mm).
- **Question:** "What happens to cable tension when one station is 50 ms late?" Answered? Partly. The notes give the length, not the force.

### Slide 14: "Camera Calibration Replaces Homing": REWORK, over-claims accuracy
- **Fluff:** the source line (same as slide 8).
- **Figure:** a readable bar chart (6.6, 2.5, 0.7 mm). It is the right chart for the wrong claim: these are **per-frame camera pose errors, best case** (a Cramér-Rao bound with an assumed 0.3 px corner noise and a guessed 520 px focal length; `FUNDAMENTALS.md` §8 says "the four-tag figure is the best placement; the project's simulator reports 1.0 to 3.0 mrad for 3 to 5 tags in realistic positions"). Better figure: a photo of the paper floor board as the claw camera sees it, plus this chart labeled "best case, calculated".
- **Statements:**
  - "Position error: 6.6 mm with one tag in view, 0.7 mm with four" omits the number that matters: **cable-length error after the fit, predicted at about 12 to 16 mm with the board** (fact-check F04). Slide 26 then uses 0.7 mm against a "2 mm per cable" target, a different quantity entirely.
  - "Whole room reachable" holds only "when the fit's error bars allow it" (notes). Say that on the slide.
- **Missing justification:** why 12 to 16 mm is fine. With 3σ at about 50 mm, it sits well inside the 0.2 m wall and 0.4 m ceiling margins. That is a strong argument, and it is missing.
- **Question:** "After the fit, how well do you know each anchor and each cable length, not the camera pose?" Answered? No.

### Slide 15: "Geared Four-Bar Claw": REWORK
- **Fluff:** "Camera moved into the claw to see each grasp" is fine but belongs in the notes. The slide has more important things to say.
- **Figure:** four images. "v6 clamp" is unexplained jargon. The CAD views do not show the four-bar moving. Replace one image with an open and closed overlay of the jaws (53 mm open, about 38 mm tip drop), and add a **grip force against jaw opening** chart: 13.3 to 25 N per jaw available, against 17.7 N needed for jeans at a friction coefficient of 0.3 (`FUNDAMENTALS.md` §5). The gear-train photo is good; keep it.
- **Statements:**
  - "Parallel jaws pinch thin fabric" is unproven. Has this claw ever picked up a T-shirt, even hand-held?
  - "Stall check moved the gears from module 1 to 1.5" hides half the fix. In Lewis bending at a fixed face width and tooth count, stress scales with 1/m², so module alone gives 2.25 times: 0.35 to 0.79. The face width also went from 6 mm to 16 mm (`FUNDAMENTALS.md` §4), which gives the other 2.67 times (0.35 × 6 = 2.1). Also, `DECISION_STORIES.md` T34 says the V3 fit review already used module 1.5 with a 16 mm face the day before the stall screening: "do not tell it as 'the screening made me change the module'".
  - "SF = 22.5 MPa / 11.0 MPa": SF is not written out on the slide, F_t, b, m and Y are undefined, and 22.5 MPa (half of an assumed 45 MPa PETG tensile strength) is unexplained.
- **Missing justification:**
  - **Grip force.** This is the product's primary function, and the deck never shows it. The record says jeans are 0.75 times short at the weakest jaw position. That is a second "jeans fail" the deck omits.
  - Servo thermal limit while holding at stall during transit (MG996R stall current about 2.5 A, for how many seconds?).
  - Claw yaw. With every cable meeting at the top plate, what orients the jaws relative to the garment?
- **Question:** "How much grip force do jeans need, and how much do you have?" Answered? No.

### Slide 16: divider "Phase 4: Final Design": CUT
- **Fluff:** the entire slide. "Size the winch, the cooling and the weight in SolidWorks" is also inaccurate: the sizing on slides 18 to 20 is hand calculation and the weight is a scale reading.

### Slide 17: "Final Wall Station": REWORK the figure
- **Fluff:** "Three station and three spool versions in SolidWorks". The version count means nothing unless each version's fix is stated. Cut it, or say "v1 to v3 fixed [fit], [assembly], [fin slot]".
- **Figure:** a transparent green shell over grey internals. At projection size I cannot tell the motor from the spool from the encoder, and I cannot see where the cable exits. Use a section view or an exploded view with five callouts (mount, motor and PETG tab, spool, encoder magnet, fin slot) plus the **cable exit and pulley**.
- **Statements:** fine as far as they go.
- **Missing justification:** the **structural load path**: cable, spool, motor shaft, the 5 mm PETG tab, shell, slide-in mount, then the stud. Also the snag load (a stepper at hold torque over the empty-spool radius gives about 48 N at 1.5 A per `DECISION_STORIES.md` T36), and the stress in that PETG tab at 57 °C. That is the real reason for the 60 °C limit on slide 19, and the deck never connects the two. A static SolidWorks study of the mount exists (`docs/simulation/SW_STATIC_STATION_MOUNT.md`); use it.
- **Question:** "Walk me from the cable to the stud. What is the snag load, and where does it fail first?" Answered? No. The notes cover assembly order, not load.

### Slide 18: "Winch Pull at 1.5 A": KEEP, add uncertainty and, ideally, a measurement
- **Fluff:** "NEMA 17 (National Electrical Manufacturers Association) stepper on a printed spool". The written-out acronym is good, but the bullet carries no information. Replace it with the assumption that drives everything: "Running torque assumed 0.7 of the 0.36 N·m holding torque (to be measured)".
- **Figure:** a readable 1/r curve. Shade the operating band (7.5 mm empty core to 10 mm full spool) and mark the 16.8 N chosen point. Right now the reader has to work out where the spool actually runs.
- **Statements:**
  - "Driver current raised from 1.06 A to the rated 1.5 A: 41 % more pull". How? The notes say "[Fill in: how, and the Vref you read]", and `DECISIONS.md` D37 says "How it was reached ... is not yet recorded". The single biggest capacity gain in the project rests on an unrecorded measurement. The earlier Vref readings already disagree by 7 % (0.79 V against 0.85 V).
  - Two unstated torque risks: the 0.7 running-torque factor (an earlier table used 0.5), and the A4988 microstepping current vector. With I_a² + I_b² = I_trip², the torque can be 1/√2 of the rating (fact-check F01).
- **Missing justification:** A4988 driver temperature at 1.5 A. `DECISIONS.md` D37 notes it "holds full current even standing still; if it overheats it shuts its outputs off and the winch loses torque". That means the claw falls.
- **Question:** "Did you measure the pull? With a luggage scale it is a 10-minute test." Answered? No. It is listed as the next step. **Do it before October 27.**

### Slide 19: "Motor Cooling": KEEP, fix the figure and the inputs
- **Fluff:** none.
- **Figure:** a grouped bar chart. It supports the vent-and-fin decision. Defects:
  - The red 60 °C line strikes through the "48.9" label.
  - The bars give single values (57.6, 48.9), while the bullet gives ranges ("45–49 °C", "56–59 °C") with no stated source for the range.
  - The four sealed-shell bars are a side story. The two vented-with-fin bars carry the claim.
- **Statements:**
  - "Motor at ... 56–59 °C with the 0.019 in prototype" leaves 1 to 4 K of margin to the 60 °C limit, on a hand calculation that assumes a 1.8 Ω coil (a placeholder, "measure with a meter" per `SW_THERMAL_HEAT_FIN.md`), 7 W/m²·K still air, and a **23 °C room**.
  - The station sits about 0.15 m below a 9 ft ceiling, where room air in a Texas house runs warmer than 23 °C. Five extra kelvin puts the prototype over the limit.
- **Missing justification:** the uncertainty band, and the source for "PETG creeps above 60 °C" (glass transition about 80 °C; what stress is in the tab?).
- **Question:** "What is the air temperature at your stations, and have you measured the coil resistance? It takes 30 seconds." Answered? No.

### Slide 20: "Weight Budget: Open Issue": KEEP, best slide in the deck, but fix the precision
- **Fluff:** none. The title is exactly right, and "Be upfront" in the notes is exactly right.
- **Figure:** a horizontal bar chart. The message is right. The 1.56 against 1.60 gap is visually 2.5 %, so the chart looks like a near-pass. Add an **error bar on capacity**: 0.79 to 1.56 kg. That is 1.11 kg if running torque is 0.5 of holding rather than 0.7, 1.10 kg with the 1/√2 microstepping factor, and 0.79 kg with both. Then the chart shows the truth: the pull test decides whether even the 1 lb test (1.15 kg) fits.
- **Statements:**
  - "jeans are 0.04 kg over". The gap is 1.60 − 1.555 = **0.045 kg**. "Next: ... a 40 g cut" then does not close it. Say "a 50 g cut".
  - "Lift capacity, worst point" is the worst point only for the claw at or below 1.6 m (the domain of the lift linear program, `DECISIONS.md` D37). Near the 0.4 m ceiling the worst point allows 0.71 kg in total (see slide 8). Label it "worst point at task height (claw ≤ 1.6 m)".
- **Missing justification:**
  - Where the 0.45 kg claw budget comes from. `REQUIREMENTS.md` R7 calls it "the value the workspace/tension analysis assumed", not a value derived from capacity. At 1.5 A the lift-derived allowable claw mass is 1.555 − 0.10 − 0.90 = **0.555 kg**. So the claw is 45 g over what physics allows, not 150 g.
  - Why the 198 g aluminium tube (a third of the claw's mass) is not the first place to cut.
- **Question:** "What is the uncertainty on 1.56 kg?" Answered? No. The notes name the 0.7 assumption but give no range.

### Slide 21: divider "Phase 5: Build and Test": CUT
- **Fluff:** the entire slide.

### Slide 22: "Printing and Machining": MERGE with slide 23
- **Fluff:** the spool renders. A CAD render cannot show "bore too tight".
- **Figure:** two CAD spools, the mill setup and the finished fin. The mill photo is a genuine "thorough" example (and is reused on slide 28). Replace the two renders with a photo of the failed v2 spool on the shaft, or of a fit coupon.
- **Statements:**
  - "Printed holes come out at least 0.2 mm undersize" generalizes from one bore. Also, "the spool took three prints" had two causes: v1 was too long for the shaft engagement, and v2 had the tight bore. Only one of them is a hole problem.
  - "Fit coupons are now printed before full parts": `FUNDAMENTALS.md` says "Fit-coupon photo with measured insertion results: None exists in the record; say PLANNED". If a coupon exists now, show it. If not, say "planned".
  - "Fin holes drilled in one mill setup to ±0.1 mm": the M3 clearance holes have 0.4 mm of float. The tight feature is the 7/8 in (22.2 mm) pilot over the 22 mm motor boss. Say that, or the ±0.1 mm reads as gold-plating.
- **Question:** "How did you measure ±0.1 mm?" Answered? No.

### Slide 23: "Electronics Bring-Up": MERGE with slide 22, add the cause
- **Fluff:** the second photo (a cluttered bench overview). It reads as chaos, not evidence.
- **Figure:** the soldered perfboard is an honest scrappy artifact. Keep it.
- **Statements:**
  - "First motor failed to turn: logic rail at 1.14 V, not 3.3 V" gives no cause. The record has one: a bad 3.3 V connection (`DECISION_STORIES.md`). Without the cause, the lesson "Supply rails are now checked with a meter before any code" is shallow.
  - "Driver stays off at boot, so a reset cannot move a motor" is true, and it also means **a reset drops a hanging claw**. With the driver disabled there is no holding torque, and detent torque cannot hold the cable tension. This contradicts "any fault holds position" (slide 3 notes). See section 4.1.
- **Question:** "What happens if the ESP32 browns out with the claw 2 m up?" Answered? No.

### Slide 24: "First System Test": KEEP, fix wording, prepare plan B
- **Fluff:** none.
- **Figure:** a placeholder. If there is no photo or video on October 27, replace the box with the test rig as built, not an empty box.
- **Statements:**
  - "Three stations: the fewest cables that fully hold the claw" is technically wrong. Three cables hold the claw only with gravity closing the force system, and only inside the anchor triangle. Fully constraining three translational degrees of freedom takes four. Use "Three stations: the fewest cables that hold the claw under gravity". Also say that three anchors cover only the triangle under them, about half the floor.
  - "Held-out poses inside the margin" is vague. Give the number, for example "≤ 20 mm cable-length residual".
- **Missing justification:** where the 2 mm per cable limit comes from (the skew budget) and how it is measured (encoder against commanded?). There is no thermal or tension abort limit for the run.
- **Question:** "If this test hasn't run by Monday, what will you show?" Answered? No. Write that version of the slide now.

### Slide 25: "Thermal Verification": CUT (merge into slide 19)
- **Fluff:** the slide. It is a placeholder plus a table whose only filled row repeats slide 19.
- **Figure:** a placeholder.
- **Statements:** "The PETG runs at about the motor temperature" repeats the slide 19 notes.
- **Action:** add one line to slide 19: "Verification: SolidWorks study and a 90-minute hold test at 1.5 A this week; fallback 1.35 A".

### Slide 26: "Results Against Targets": KEEP, rework the statuses
- **Fluff:** "Cost | Hobby budget" is not a target. Give a dollar cap.
- **Figure:** a table. That is acceptable here, since a status table is the right form. Add an **Evidence column** (Measured, Calculated, Simulated, Not run) so the status cannot be misread.
- **Statements:**
  - "Motor temperature ... 45–49 °C with the 1/8 in fin | Met in design": the 1/8 in fin is not made. The hardware that exists (0.019 in) calculates at 56–59 °C, with an assumed coil resistance. Status: "Calculated; prototype within 1–4 K of the limit; hold test pending".
  - "Working area ... All but 0.2 m along the walls | Met in design": not for jeans, whose worst point is the middle of a long wall. Status: "Met for 1 lb (calculated); not for jeans at the long-wall midpoint".
  - "Accuracy | 2 mm per cable | 0.7 mm (calculated)" compares a per-frame camera pose bound with a cable-length target. Fix: "Accuracy (cable mismatch during a move) | ≤ 2 mm | not measured; 40 ms skew budget gives 2 mm | To be tested".
  - "Wiring | ... 0.51 V drop | Met": the 0.51 V is calculated. Tag it.
  - Missing row: **Grip force for jeans**: need 17.7 N per jaw, have 13.3 to 25 N (calculated): short at narrow grabs.
- **Question:** "Which of these rows are measured?" Answered? Only "Claw mass (weighed)".

### Slide 27: "Good and Poor Decisions": KEEP, merge slide 28 in, fix the rows
- **Fluff:** none, but the poor decisions are soft.
- **Figure:** two tables and no graphic. Add one small image per poor decision (the claw on the scale, the bead-homing curve), or accept the table and put the graphic budget elsewhere.
- **Statements:**
  - "Gear strength checked at servo stall | Failure caught in CAD, before printing": the record says the module and face change predates the stall screening (T34). Retell it as "Teeth checked at stall, because a clamp stalls the servo on every grip: safety factor 2.0".
  - "Mass budget set late | Claw 0.15 kg over budget": the budget existed from the start (`REQUIREMENTS.md` R7, and the finger claw was designed to 419 g of 450 g). The real failure is **not re-checking mass when the claw architecture changed**. The v6 clamp reached 4.6 times the budget in CAD before anyone weighed anything, and the budget was never derived from the winch. Fix: "Mass not tracked through four claw versions; budget not derived from the winch pull".
  - "Bead homing as the first plan | Under a third of the room reachable": a plan killed on paper before it was built costs almost nothing. That is a good catch, not a poor decision. Replace it with a real one (for example "Build and test week ends on presentation day" or "Prototype fin from scrap sheet with 1–4 K of thermal margin").
  - "Several stations built before one was proven ... [confirm]": if it is not confirmed, the row must go, which leaves one real poor decision.
- **Question:** "What is the worst call you made, and what did it cost in days?" Answered? No. No row is costed in time.

### Slide 28: "Thorough vs. Scrappy": MERGE into slide 27
- **Fluff:**
  - "Heat fin: one mill setup, ±0.1 mm" repeats slide 22.
  - "Gears: strength checked before printing" is the third appearance.
  - The mill photo repeats slide 22.
- **Figure:** the right-hand image is a breadboard wiring diagram with text too small to read at any projection size. It is labeled "jumpered ESP32 controller board" but is a diagram, not the board. Use a photo of the real jumpered board.
- **Statements:**
  - "Failed controller replaced by a jumpered ESP32 board" is good scrappy content. Add what failed and what the scrappiness cost or risked (nine jumpers in a station at the ceiling: vibration?).
  - "Floor board printed on paper" is good, with the justification from the notes ("accuracy comes from seeing several tags").
- **Action:** add a two-row "Thorough / Scrappy" strip under slide 27's tables, with one photo each.

### Slide 29: "Takeaways and Next Steps": KEEP, rework the half-time answer
- **Fluff:** none, but the slide is overloaded (three takeaways, three next steps, a chart).
- **Figure:** actual against half-time schedule on the same scale. A good idea, and the scale checks out (595 px for 15 weeks against 280 px for 7 weeks). But the half-time bar does not say **what gets cut**, and that is the whole question.
- **Statements:**
  - "In half the time: freeze requirements in week 1, order long-lead parts on day 1": nothing in the story shows a requirement changing or a long-lead part delaying anything, so this takeaway is unsupported by the talk. The talk's own evidence says the time went into a central board and bead homing that died on paper, a finger claw that was never built, and three claw versions before mass was checked.
  - A half-time answer the story supports:
    1. Week 1: pull-test one winch and weigh a mock claw, then set the mass budget from that.
    2. Skip the central board and bead homing, since both were killed by calculations that could have run in week 1.
    3. Start with the clamp, not the fingers.
    4. One station end to end, calibration included, before copying.
    5. Drop the phone chat and voice.
- **Question:** "What would you not build at all in half the time?" Answered? No.

### Slide 30: "Questions": CUT
- **Fluff:** the slide. Leave slide 29 (or a one-line summary slide) up during questions so the panel can point at something. The email address is in the email the panel already has.

---

## 4. Credibility and honesty

### 4.1 Numbers and statements that contradict each other

| # | Claim | Contradicted by | Recomputation or evidence |
|---|---|---|---|
| C1 | Slide 8: "Covers 2 m/s² acceleration within the 16.8 N winch limit" (W = 8.87 N, a 0.45 kg claw, no battery) | Slide 20: claw weighed 0.60 kg, battery 0.10 kg | Centred, 0.4 m: 1 lb test gives 18.8 N, jeans give 26.0 N, both above 16.8 N. Minimum centred depth: 0.45 m (1 lb), 0.64 m (jeans) |
| C2 | Slide 8: "Operating limit set 0.4 m below the anchors" | Slide 20's capacity, which assumes the claw ≤ 1.6 m (0.99 m below the anchors) | Two different ceilings, and neither slide says which applies to a loaded claw. At 0.4 m the worst-case linear program allows 0.71 kg in total, which is the claw plus battery |
| C3 | Slide 3: "Success: one garment to the hamper with no human input" | Slide 6: "a phone app starts, pauses and approves it"; slide 34: "Every move waits for approval on the phone" | Direct contradiction |
| C4 | Slide 3 notes: "any fault holds position"; slide 35: "A stop keeps torque" | Slide 23: "Driver stays off at boot"; slide 34's own app screen: "Emergency stop = the switched power strip. It drops the claw"; D37: A4988 thermal shutdown loses torque | Power loss, a controller reset, a brown-out, or a driver thermal shutdown all drop the claw. 1.6 kg from 2.2 m is about 35 J. "PAUSE holds position" is the true statement |
| C5 | Slide 26: "Accuracy | 2 mm per cable | 0.7 mm (calculated)" | Slide 13 notes: 50 ms skew gives 2.5 mm; fact-check F04: cable-length σ after the fit about 12 to 16 mm | Different quantities. The 0.7 mm is a best-case per-frame pose bound |
| C6 | Slide 20: "jeans are 0.04 kg over"; "Next: ... a 40 g cut" | Slide 20's own equation: 1.60 − 1.555 | The gap is 0.045 kg, so a 40 g cut leaves it 5 g short |
| C7 | Slide 20 and 26: claw 0.15 kg over the 0.45 kg budget | Slide 20: jeans 0.04 kg over capacity | Same problem, two baselines. The lift-derived allowable claw mass at 1.5 A is 0.555 kg, so the claw is 45 g over physics |
| C8 | Slide 11: bead homing "caught on paper, before it was built" (notes) | Slide 10: Generation 1 plates had a "home switch"; slide 27 lists bead homing as a "Poor decision" with a result | A paper catch has no result to regret. It was a good catch |
| C9 | Slide 15: "Stall check moved the gears from module 1 to 1.5" | Lewis scaling; `FUNDAMENTALS.md` §4 (face 6 to 16 mm); T34 (module 1.5 / 16 mm predates the screening) | Module alone: 0.35 × 2.25 = 0.79. Module plus face: 0.35 × 6 = 2.1 |
| C10 | Slide 7: "Smaller spool radius ... Slower line speed" | Slide 26: 50 mm/s | At 50 mm/s the spool turns under 1 rev/s; line speed never binds. Bend ratio and set-screw space bind |
| C11 | Slide 32 (appendix): "Built at 200 mm" | Slide 29: "machine the 1/8 in fin" (next step) | The 1/8 in fin is not built |
| C12 | Slide 36 (appendix): "Peak 2.8–3.1 A against a 3 A pack rating" with "a 5 A fuse" | Itself | The peak exceeds the pack rating, and the fuse sits above it. What protects the pack between 3 and 5 A? |

### 4.2 Calculated or assumed, presented as met or measured

- **Lift capacity, 1.56 kg (slides 7, 18, 20, 26).** It rests on two unmeasured inputs: the running-torque factor (0.7, where an earlier table used 0.5) and the microstepping torque basis (1/√2). The honest range is 0.79 to 1.56 kg. Quoting "0.04 kg short" (2.5 %) on a ±30 % estimate is false precision. Either measure it or show the band.
- **1.5 A (slides 7, 18, 19, 20).** "How it was reached ... is not yet recorded" (D37).
- **Coil resistance 1.8 Ω (slide 19).** A placeholder, not a meter reading.
- **"Met in design" (slide 26)** for the motor temperature (fin not built) and the working area (not for jeans).
- **"Parallel jaws pinch thin fabric" (slide 15)** has no recorded grip test.
- **"Fit coupons are now printed before full parts" (slide 22)** has no coupon in the record.
- **"Whole room reachable" (slides 14 and 27)** holds only when the calibration's error bars allow it (slide 14 notes).
- **"Five times less wire ... Met" (slides 13 and 26).** Fine as arithmetic. Tag the 0.51 V drop as calculated.

### 4.3 Claims contradicted by the project record

1. **Slide 11, finger claw.** The claw was never built, its CAD was 419 g against 450 g, "could not pinch" was clamp V1 (Sep 30), and "4.6 times" was the v6 clamp (Oct 20). This is the most damaging single line in the deck, because a panelist can puncture it with "show me the test".
2. **Slides 15 and 27, gear story.** Told as "the check moved the module". The record says the module and face change came first.
3. **Slide 20 and 27, "Mass budget set late".** R7 existed from the start. The failure was tracking, not timing.
4. **Slide 18, 1.5 A.** No recorded Vref or method.

### 4.4 Authorship ("who did what")

Slide 4 says "Solo project: requirements, calculations, all CAD (computer-aided design), printing, machining, wiring". The repository record says otherwise:

- the parametric CAD (CadQuery), the calculation scripts, the independent verifications and most of the software came through an AI-agent workflow (CLAUDE.md; `verification/deck_factcheck.md` F05 and F06: "143 of 180 commits authored 'Claude'");
- `DECISION_STORIES.md` tags which decisions are Jasper's ([J], [J-sel]) and which are review checks ([chk]).

His own direction (DECK_V7_NOTES, Oct 22) already credits Claude Code for the control logic. That must extend to the calculations and the CAD verification, or the panel will extend it for him. Using tools well is a strength at SpaceX. Being caught overstating authorship is fatal. The bar he must clear: **he can derive every number on every main slide on a whiteboard without notes.** Exact wording is in fix 4.

### 4.5 Brackets that would hurt if still empty on October 27

| Slide | Bracket | Why it hurts |
|---|---|---|
| 4 | "[software parts you wrote]" | Reads as evasion on the "who did what" slide the panel explicitly asked for |
| 10 | "[weight]" | The only physical result of Generation 1; without it "worked on the bench" is unsupported |
| 18 (notes) | "[Fill in: how, and the Vref you read]" | The 41 % capacity gain, the heat doubling and the weight-budget story all rest on it |
| 24 | four "[fill in]" results | If the test has not run, the slide must say "not run; date", not show empty cells |
| 25 | SolidWorks and hold-test cells | Cut the slide rather than show empty rows (see slide 25) |
| 26 | "[total cost]" | "Hobby budget" with no number looks like he did not track it |
| 27 | "[confirm]" | One of only three poor decisions; unconfirmed, it is a guess |
| 23 (notes) | "[Fill in: exact readings, date, what you tried first]" | The 1.14 V story needs its cause (a bad 3.3 V connection) and the reading |

### 4.6 What the deck does right (keep these)

- Evidence tags ("calculated", "weighed") on charts and in the results table.
- "Weight Budget: Open Issue" as a title, with "Not met" in red on slide 26.
- Pass limits set before the run (slide 24).
- Real fabrication evidence: the mill setup, the soldered board, the printed gear train.
- Thinking in trade-offs (slide 7's idea, if not its form).
- The fin-efficiency argument (slides 32 and 33: "Thickness beats length") is the kind of physics-first reasoning this panel likes.

---

## 5. Missing content I expected from an engineer at this level

1. **A status slide in minute 3.** What exists physically, what is measured, what fails, and what gets tested this week.
2. **Grip force.** Requirement against capability across jaw opening, the friction coefficient assumed (0.3) and how it will be measured. Jeans are 0.75 times short at the weakest jaw position per his own record. For a gripper project this is the core function, and it is absent.
3. **Fail-safe behaviour and hazard analysis.** Power loss, reset, brown-out or driver thermal shutdown drops the claw. There is no brake and no non-backdrivable stage. State the worst credible event (1.6 kg from 2.2 m, about 35 J), the mitigation (nobody underneath, falls onto laundry), and the design fix (a brake, a worm stage, or a ratchet pawl).
4. **Cable tension sharing in a redundant system.** Four position-controlled cables on three translational degrees of freedom: the tension split is set by length errors, not by the controller. What happens when one cable goes slack? (`DECISION_STORIES.md` T36 gives 0.76 to 1.75 lb capacity with one slack cable.) The lift linear program's "best split" assumes control he does not have.
5. **Station structural load path.** Cable to spool, motor, PETG tab, shell, mount, then the stud. Include the snag load (stall hold over the empty-spool radius), the stress in the 5 mm PETG tab, and creep at 57 °C. The static SolidWorks study exists. Use it.
6. **The line itself.** Dyneema diameter and breaking strength, safety factor, bend ratio on the Ø15 core, the pulley groove, abrasion at the outlet, stretch over 32 ft runs.
7. **Claw dynamics.** Pendulum period and settle time ("hover until still" for how long?), tilt (the record says static tilt reaches 13° off-centre), and yaw control of the jaws.
8. **Requirements traceability.** Where 0.9 kg, 2 m/s², 2 mm, 50 mm/s and 0.45 kg come from, and which are guesses.
9. **Cycle time per garment.** Currently implied at about 3 minutes, never stated.
10. **Perception performance.** YOLO-World on crumpled laundry: any detection rate at all, even on 20 photos of his floor?
11. **Uncertainty and sensitivity.** The capacity band (0.79 to 1.56 kg) and the temperature sensitivity to h, coil resistance and ambient.
12. **A measured-versus-calculated inventory.** It can be the Evidence column on slide 26.
13. **Cost.** Total spent and the bill of materials per station.
14. **Top three risks**, each with its mitigation and the test that retires it.

---

## 6. Prioritized fix list

Most important first. Each item gives the slides, the exact change, and why.

1. **Slides 11, 10 and 27: correct the finger-claw claim.**
   - Slide 11, replace bullet 3 with: "Finger claw: designed in CAD (419 g of a 450 g budget) but never built; one servo pulling five tendons was harder to build and test than a clamp".
   - Slide 10, change "Five flexible TPU (thermoplastic polyurethane) fingers on the claw" to "Finger claw: CAD only".
   - Move "could not pinch thin fabric" (clamp V1, Sep 30) and "4.6 times its mass budget" (v6 clamp, Oct 20, CAD upper bound at 100 % solid) onto the claw slide (15), with those dates.
   - *Why:* as written it is contradicted by the project record, and one question ("show me the test") destroys credibility for the remaining 40 minutes.

2. **Slide 8 (and 7 and 38): recompute with the weighed claw and state the loaded-claw limit.**
   - New title: "Cable Tension Sets the Ceiling Margin".
   - Chart: add curves for 1.15 kg (1 lb test) and 1.60 kg (jeans), and a vertical line at the operating limit.
   - Bullets:
     - "With the weighed claw and 1 lb, centred: 18.8 N at 0.4 m with 2 m/s², over the 16.8 N limit".
     - "Loaded claw stays at least 0.45 m (1 lb) / 0.64 m (jeans) below the anchors at the centre, more near the walls".
     - "The planner checks every pose: the loaded claw stays at or below 1.6 m above the floor". Confirm that the planner actually enforces this. If it does not, that is a bug to fix before the test.
   - Equation box: "T = m(g + a) / (4 sin φ) = 1.15 × 11.81 / (4 × 0.181) = 18.8 N".
   - Slide 7: change "Cable tension 12 N to 32 N" to match.
   - *Why:* the current conclusion is false for every real configuration, and the error is visible to anyone comparing slide 8 with slide 20.

3. **New slide after slide 3: "Where It Stands Today" (failures upfront).**
   - Figure: one photo of what is built next to one CAD view of what is only drawn.
   - Bullets:
     - "Built: [n] stations, claw (weighed 0.60 kg), station controller".
     - "Measured: claw mass, driver Vref [value], pull [value, if done]".
     - "Open: jeans 45 g over calculated lift; jeans grip short at narrow grabs; prototype fin within 1–4 K of the PETG limit".
     - "This week: pull test, 90-minute hold test, three-station test".
   - *Why:* the brief says failures upfront. Today the first honest status is at minute 30.

4. **Slide 4: rewrite the authorship line.**
   - Bullets:
     - "Mine: the requirements, every design decision, the SolidWorks station and claw, printing, machining, wiring and bring-up".
     - "With Claude Code (an AI coding assistant): the control software, the calculation scripts and independent checks of my CAD; I can derive every number on these slides".
     - "Purchased: stepper motors, drivers, controller boards, servo, camera, battery, encoder boards".
   - *Why:* the repository record contradicts "Solo ... calculations, all CAD", and authorship is the first thing this panel probes.

5. **Slides 18 and 20: replace calculated pull with measured pull, or show the uncertainty band.**
   - Run the luggage-scale pull test (and read Vref and the coil resistance with a meter) before October 27.
   - If it is done, slide 18 bullet 3 becomes "Measured: [x] N at a full spool (calculated 25 N)".
   - If it is not done, add an error bar to slide 20's capacity bar (0.79 to 1.56 kg) and change bullet 1 to "Lift capacity at 1.5 A: 1.1–1.56 kg (calculated; depends on running torque, to be measured)".
   - Change "40 g cut" to "50 g cut", and "0.04 kg" to "0.045 kg".
   - Fill the "how 1.5 A was reached" bracket.
   - *Why:* the deck's central open issue is quoted to 2.5 % on an estimate with about 30 % uncertainty, and the test that settles it takes 10 minutes.

6. **Slides 3, 6 and 34: remove the "no human input" contradiction.**
   - Slide 3 bullet 4: "Success: one garment from floor to hamper with no human touch; I approve each move on the phone".
   - *Why:* it is a direct contradiction on the problem-definition slide.

7. **Slides 3 (notes), 23 and 35: state the fail-safe truth.**
   - Slide 3 notes: replace "any fault holds position" with "PAUSE holds position; power loss, a reset or a driver over-temperature drops the claw, which is why nobody stands under it".
   - Slide 35 row "Faults": "PAUSE keeps torque; the emergency stop cuts power and drops the claw".
   - Add to slide 29 next steps: "Add a brake or a non-backdrivable stage".
   - *Why:* the safety story is internally inconsistent, and a SpaceX reviewer asks "what is the safe state?" first.

8. **Slides 14 and 26: report the accuracy that matters.**
   - Slide 14 bullet 3: "Camera pose per frame (best case, calculated): 6.6 mm with one tag, 0.7 mm with four in view".
   - Slide 14, new bullet: "Cable lengths after the fit (simulated): about 12–16 mm, inside the 0.2 m wall and 0.4 m ceiling margins".
   - Slide 26 Accuracy row: "Cable mismatch during a move | ≤ 2 mm | Not measured; 40 ms skew budget gives 2 mm | To be tested".
   - *Why:* 0.7 mm against a 2 mm per-cable target compares different quantities and over-claims by a factor of 20.

9. **Slide 15: retell the claw as an iteration and add grip force.**
   - New title: "Claw: Four Versions to a Parallel Grip".
   - Figure: a strip of four images (finger CAD, clamp V1, v6 clamp, final four-bar), each with its one-line kill reason. Add a grip-force chart (13.3–25 N available against 17.7 N needed for jeans at friction 0.3).
   - Change bullet 3 to "Teeth checked at servo stall: module 1.5, 16 mm face, safety factor 2.0 (module 1, 6 mm face: 0.35)".
   - Write out "safety factor (SF)".
   - *Why:* it fixes the misleading gear story and the missing core-function number, and turns scattered failures into the best "what failed / what learned" thread in the talk.

10. **Cut slides 5, 9, 12, 16, 21, 25 and 30; merge 28 into 27, and 22 with 23.**
    - Put the phase in the footer: "Jasper Buntinx | RoomCleaner | Phase 2 of 5: Generation 1".
    - Add to slide 19: "Verification: SolidWorks study and 90-minute hold test this week; fallback 1.35 A".
    - *Why:* 30 slides do not fit 60 minutes with an interactive panel, and the cut slides carry no information or repeat other slides.

11. **Slide 13: replace the bar chart and add the cost of the decision.**
    - Figure: a room plan with the four real routes (6, 21, 23, 32 ft), central-box star against power-only.
    - Bullet 3: "Cost: a 50 ms clock skew at 50 mm/s is 2.5 mm of cable mismatch, about 7.5 N of extra tension; time-stamped segments keep skew under 40 ms".
    - *Why:* the chart is triple-redundant decoration, and the real cost (tension) is missing.

12. **Slide 7: replace the table with the chain diagram and move it.**
    - New title: "One Chain Sets Every Limit".
    - Diagram: mass, then tension (×1.1 at task height, ×2.4 near the ceiling), then current (pull ∝ I), then heat (∝ I²), then PETG at 60 °C. Write the lever and chosen setting under each arrow.
    - Delete the "Larger room" row. Change the spool cost to "Line bend ratio and set-screw space".
    - Either remove the October values from the Concept phase or move the slide after slide 20 as the summary.
    - *Why:* it gives the talk a spine, meets the one-graphic rule, and fixes the anachronism and the wrong cost.

13. **Slide 26: add an Evidence column and correct the statuses.**
    - Motor temperature: "Calculated; prototype fin 56–59 °C; hold test pending".
    - Working area: "Met for 1 lb (calculated); jeans short at the long-wall midpoint".
    - Add a row: "Grip for jeans | ≥ 17.7 N per jaw | 13.3–25 N (calculated) | Short at narrow grabs".
    - Cost: put in a dollar cap.
    - *Why:* "Met in design" on unbuilt hardware is over-claiming, and the panel will read this slide hardest.

14. **Slide 27: replace the soft poor decisions.**
    - "Mass budget set late" becomes "Mass not tracked through four claw versions; budget not derived from the winch pull".
    - Replace "Bead homing as the first plan" with a real one that has a cost in days (for example "Build and test week ends on presentation day").
    - Delete "Several stations built ..." unless confirmed.
    - Retell the gear row as "Teeth checked at stall, because a clamp stalls the servo on every grip".
    - *Why:* the current poor decisions are either not poor or not true, and this panel wants ownership.

15. **Slide 29: make the half-time answer specific.**
    - Replace "freeze requirements in week 1, order long-lead parts on day 1" with:
      - "Week 1: pull-test one winch and weigh a mock claw; set the mass budget from that".
      - "Skip the central board and bead homing; both failed on paper".
      - "Start with the clamp; build one full station with calibration before copying; drop the phone chat".
    - Label the half-time bars with what each contains.
    - *Why:* the current takeaway is not supported by anything in the talk.

16. **Slide 19: fix the figure and state the inputs.**
    - Move the "48.9" label off the 60 °C line. Show the 56–59 and 45–49 °C ranges as error bars, or explain them.
    - Add a footnote: "Assumed: coil 1.8 Ω (to measure), still air 7 W/m²·K, 23 °C room".
    - Add a bullet: "Prototype margin 1–4 K; warmer ceiling air would remove it".
    - *Why:* the thinnest margin in the design is presented without its assumptions.

17. **Slide 17: show the load path.**
    - Swap the transparent render for a section or exploded view with callouts, including the cable exit and pulley.
    - Add a bullet: "Load path: cable, spool, motor, 5 mm PETG tab, shell, mount, stud; snag load [x] N, tab stress [y] MPa" (from the existing mount study).
    - Cut "Three station and three spool versions in SolidWorks".
    - *Why:* structural load path is a guaranteed question, and the figure is unreadable.

18. **Slide 3: add the room sketch and the missing requirements.**
    - Add a to-scale sketch: 11 × 9 × 9 ft, anchors, hamper, keep-outs.
    - Add: "9 ft ceiling".
    - Add a note: "2 m/s² is a 1.2 times dynamic allowance for stops and snags, not the motion profile".
    - Units: "0.45 kg (1 lb) first test".
    - Add the cycle-time target.
    - Change "hobby budget" to "$[x] budget".
    - *Why:* the panel cannot judge any later number without the room geometry.

19. **Slides 11, 20 and 24: plant three interaction points.**
    - Slide 11: "How would you home it?" before revealing the curve.
    - Slide 20: "Cut 45 g or add a 2:1 gear stage: your call?"
    - Slide 24: "Which pass limit would you tighten?"
    - Add a line in each note: "Pause. Ask. Wait."
    - *Why:* the brief asks for a design review, not a lecture.

20. **Slides 22 and 23 (merged): fix the generalizations and add the cause.**
    - "Printed holes come out at least 0.2 mm undersize" becomes "One Ø5.2 bore printed too tight on the 5 mm shaft; v3 opened it to Ø5.45".
    - Show a fit coupon, or say "Fit coupons: planned".
    - Add the cause: "1.14 V traced to a bad 3.3 V connection".
    - Replace the CAD spools with a photo of the failed print.
    - Replace "±0.1 mm" justification with "the 7/8 in pilot fits the 22 mm motor boss".
    - *Why:* each statement is currently a generalization from one sample, or a lesson without a cause.

21. **Slide 24: wording, plus a plan B.**
    - "fully hold the claw" becomes "hold the claw under gravity".
    - Add: "covers the anchor triangle, about half the floor".
    - Quantify "inside the margin".
    - Prepare a version for "test not yet run" that shows the rig and the dated plan.
    - *Why:* the current wording is technically wrong, and an empty results table on the day is worse than an honest "not yet".

22. **Slide 2: three large photos, not seventeen thumbnails.**
    - Use EcoFil labeled, the 70.3 finish, and one Gladiator Dash build.
    - Cut "Hiking, canyons and cliff jumping".
    - Add one EcoFil result number.
    - *Why:* the brief's "only graphics you can defend in depth" rule, and 90 seconds of talk.

23. **Speaker notes, every slide: cut to one claim, two numbers and one "so what", under 60 words.**
    - Move the rest under a "Q&A ammunition, only if asked" heading.
    - Start with slide 15 (link lengths, tooth counts), slide 20 (177 words), slide 29 (160 words) and slide 22 (hole sizes).
    - *Why:* spoken number dumps lose the panel, and the deck currently runs 30 to 38 minutes before any interruptions.

24. **Every chart footer: shorten the source line.**
    - "Source: RoomCleaner engineering calculations, 'Cable tension' (calculated)" becomes "Calculated (calc sheet: Cable tension)".
    - *Why:* the self-citation is boilerplate, and the evidence tag is the part that matters.

25. **Units across the deck: SI first, imperial in parentheses.**
    - Keep stock sizes (1/8 in plate, 16 AWG) as sold.
    - Do not mix "0.9 kg" and "1 lb" in one bullet. Room: "3.35 × 2.74 m (11 × 9 ft)". Wire: "25 m (82 ft)".
    - *Why:* mixed units in one argument are how unit errors get made, and this panel will notice.

26. **Slide 1: subtitle.**
    - "A cable-driven robot that picks laundry up off the floor" becomes "A four-cable ceiling robot designed to pick laundry off the floor".
    - *Why:* do not claim on slide 1 what slide 26 says has not been run.
