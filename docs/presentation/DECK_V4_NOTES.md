# Deck v4: industry-standard restyle (2026-10-21)

Jasper asked whether deck v3's theme was the most appropriate and professional choice, and to research and apply an
industry standard instead of a custom look.

## Standard used

**Assertion-evidence slide design**: Michael Alley's group, Penn State College of Engineering; taught to engineers and
scientists, with studies showing better comprehension and recall than topic-and-bullet slides.
- Every content slide's headline is one full sentence that states the takeaway; it is not a topic label.
- The visual is the evidence: chart, photo, CAD render or diagram.

Sources: https://writing.engr.psu.edu/research.html, https://www.huck.psu.edu/event/rethinking-slide-design-in-scientific-presentation-the-assertion-evidence-approach-1

Styling follows plain engineering-company conventions:
- Arial throughout, black text on white, one dark-blue accent.
- Headline at top left with a thin grey rule under it. No small-caps section labels above the title.
- Square, light-grey equation boxes labelled "Key equations".
- Plain (non-italic) captions; every chart caption is a source line: "Source: calculation sheet (Google Sheets), '<tab>' tab. Calculated, not measured."
- Footer: name, date and page number.

## What changed and what did not

- **Changed:** every content slide's title is now an assertion headline, one line each.
- **Content:** the same as v3.2: bullets, equations, Sheet charts, photos and speaker notes.
  - Two bullets were shortened to fit Arial: the fin-length slide's "Looks" bullet and the winch slide's design-force bullet.
  - Bullets stay, because Jasper asked for bullets on every subject. In assertion-evidence they are supporting text.
- **Files:**
  - `deck_v4/build_deck_v4.js` builds `RoomCleaner_Buntinx_Oct27_v4.pptx` / `.pdf` (46 slides, validated).
  - Figures and Sheet charts are read from `deck_v3/fig`.
  - v1, v2 and v3 stay unchanged.

## v4.1 (2026-10-21, Jasper: "a segment on the logic difference and the final logic, zoomed out"; "how does the robot deal with obstacles?")

New **section 7, Control logic** (51 slides now; validated). Section 6 is now *Electronics* (station board, bring-up);
*Status and next steps* is section 8, and the outline lists all eight sections.

| slide | headline | evidence |
|---|---|---|
| 37 | section divider: Control logic | |
| 38 | The first logic trusted its model; the final logic measures, then checks | native table, gen 1 vs final, seven rows: where the claw is, geometry, who runs the motors, finding laundry, grab check, faults, where it may move |
| 39 | Five layers run the robot, and only the bottom one turns a motor | native layer stack: phone, supervisor, startup and tasks, planner and coordinator, stations; the claw beside the task layer. Equation box: path-point length and tension check, lease rule |
| 40 | One run: start up and calibrate, then pick, check and deliver each item | native four-stage flow with the repeat loop and the stop rule |
| 41 | The phone is the operator's only control, and every move asks first | the phone-app slide from v4 section 6, rewritten so it does not repeat slide 39 |
| 42 | It plans around known obstacles but cannot yet detect new ones | native side view along the A-C diagonal. Example: a 1.9 m shelf 1 m out from corner A; the room-centre claw is clear at 1.5 m and refused at 0.8 m. Checked with the planner's own segment-cylinder test (`kinematics._segment_hits_cylinder`). Equation box: the cable segment and the cylinder hit test |

Facts behind the obstacle slide (code, not hardware):
- `config.obstacles` holds vertical cylinders {x, y, r, z_low, z_high}.
- `Workspace.violations` checks every planned path point: each cable segment (pulley exit to the claw hole) against each
  cylinder, plus the wall, ceiling and bead limits and, for three stations, the triangle. The planner also checks cable tension
  with the payload and dynamics. A failing path raises `PlanError` before any motion.
- No re-routing: moves are straight lines.
- Gap found while writing it: in a task, an item whose approach is refused stops the whole task (FAULT, claw held) instead
  of being skipped (`tasks.py` `_move` raises `StartupAbort`).
- While moving, the robot detects a jammed or stalled cable (station TRACKING fault) and a failed grip (camera). It cannot
  detect a person, a pet or a moved chair: the claw camera looks down and has no depth.
- Gen 1 had the same keep-out idea for the ceiling fan (`roomcleaner/config.py` `FanZone`, exact segment test).

## v4.2 (2026-10-22, Jasper: "make sure the final assembly is getting displayed in the presentation")

- **New slide 3, *The final design: four wall stations hold one claw on four lines*,** right after the goal slide. The finished
  robot comes before the story of how it got there. The deck is now 52 slides.
- **Two new renders,** from `tools/render_deck_assets.py`; the older renders are kept:
  - `station_1021_final.png`: Jasper's Oct 21 wall assembly (wall frame, slide-in mount, shell, motor, spool, heat fin), with
    the encoder casing and magnet cap inside the shell;
  - `gripper1021_asbuilt.png`: the claw as built, with the housing carrying both cable patterns (D34) and its camera-bay cover,
    the 10.48 in tube (D36: the head moved up by the 38.6 mm cut), the 1021 head and the four-bar hands.
- **Unchanged, by choice (Jasper):** the title slide keeps `gripper1021_final.png` (12 in tube). The slide says "10.5 in tube" (10.48 as built).
- **Photo 21 (Jasper, 10/22):** the printed claw body (tube in the top mount, servo in the gear housing). It now appears on the
  "Built and simulated" slide next to the heat fin. That slide's bullets list the claw body as built and the encoder casing as
  designed.
