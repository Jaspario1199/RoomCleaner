# SpaceX presentation — editable-deck text and reasoning snapshot

Captured 2026-10-19, America/Chicago. This is an outline, not a completed submission or a hardware validation report.

- [Live Google Slides deck](https://docs.google.com/presentation/d/1-9cpMw0nqccEls9PRC2QUmUAKyAcmY5KLo52BrZoQjA)
- Native revision: `3vMM6mvSqrhsUA`
- 20 slides: 15 main slides (30 minutes planned), 3 technical backups, 2 preparation pages to remove before submission.
- This snapshot preserves every slide's visible text and speaker notes. Text and tables remain editable in the live deck; later edits there do not automatically update GitHub.
- Private inbox URLs are intentionally omitted. The requirements below reflect the user-supplied interview prompt; no full email, contact details or attendee list is published.
- Local and Google Slides renders were reviewed on creation. Placeholder content is intentional and must be replaced before submission. This does not verify any physical performance.

## Slide 1 — Jasper Buntinx

### Visible content

ABOUT ME

Jasper Buntinx

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

01

RoomCleaner · cable-driven laundry robot

Background

[Insert degree, school, graduation date and one relevant hands-on experience.]

Why I build

[Insert a short personal motivation and one interest outside engineering.]

INSERT PERSONAL PHOTO

A real workshop or build photo.

Keep this introduction to one minute.

### Speaker notes / rationale / questions

MAIN TALK — 1 minutes

Start with who you are, not the whole résumé. Connect one hands-on interest to why you chose this project. Do not invent degree details or an employment history. The recruiter explicitly requests one quick about-me slide.

SOURCE / STATUS
Recruiter presentation requirements supplied by Jasper, October 2026. [private correspondence; link omitted from repository]

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 2 — The problem and success criteria

### Visible content

SCOPE

The problem and success criteria

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

02

Goal

Find, grip and deliver laundry with a suspended camera-equipped claw.

First integration target

Four winches supporting a central 1 lb test weight; not a demonstrated payload rating.

Constraints

Low suspended mass, affordable parts, removable wall stations and repeatable assembly.

INSERT ROOM + ROBOT OVERVIEW

Label four anchors, cable paths, claw and hamper.

Room reference: 11 × 9 ft; height 9 ft.

Add target speed, repeatability and budget.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Define what “success” means before discussing implementation. Distinguish the one-pound test target from garment mass, total suspended mass and any future five-pound aspiration. Add quantitative acceptance criteria only after you choose and can defend them. Explain why a suspended robot was attractive and what alternatives you considered.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 3 — My scope and project timeline

### Visible content

OWNERSHIP

My scope and project timeline

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

03

My direct work

[Insert the CAD, fabrication, wiring, code, analysis and tests you personally performed.]

Other contributions

[Name any collaborators, purchased modules, outside designs and tools; state their roles.]

Sequence

Requirements → sizing → CAD → fabrication → station bring-up → integration tests.

INSERT DATED BUILD TIMELINE

Use 4–6 milestones with dated photos or versions.

Mark completed, in progress and planned work.

Confirm project start date and team size.

### Speaker notes / rationale / questions

MAIN TALK — 1 minutes

This is a personal project; do not imply a team or production responsibility if there was none. Identify which CAD/code came from you versus tools or outside sources, and what you personally checked. Include decision ownership and any feedback from classmates, mentors or suppliers only if it happened. Recruiter asks for timeline, team size and responsibility split.

SOURCE / STATUS
Recruiter presentation requirements supplied by Jasper, October 2026. [private correspondence; link omitted from repository]
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 4 — System architecture and its evolution

### Visible content

DESIGN

System architecture and its evolution

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

04

Earlier configuration

One central Arduino and motor drivers, with long motor harnesses.

Current station direction

Local XIAO ESP32 controller, A4988 driver and step-down regulator at each winch.

Tradeoff

Fewer long motor wires; new responsibility for synchronized motion and communication faults.

INSERT BEFORE / AFTER ARCHITECTURE

Separate electrical power from commands.

Show one 12 V pair per station.

Label bench-tested paths vs planned Wi-Fi coordination.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Spell out microcontroller and wireless communication rather than using unexplained acronyms. Explain why the wiring drove the architecture change; do not claim Wi-Fi synchronization or four-axis performance has been demonstrated. Bring the exact firmware/version and as-built connection diagram to backup. Camera and gripper are a separate moving assembly.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 5 — Cable force and motor sizing

### Visible content

FIRST PRINCIPLES

Cable force and motor sizing

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

05

Σ Tᵢuᵢ + mg = ma     with Tᵢ ≥ 0

τspool = T · reffective

Favailable ≈ η · G · τmotor(ω) / reffective

Load model

Include claw, battery and garment mass—not only payload.

Capacity limits

Use running torque at speed and the largest wound spool radius.

INSERT FREE-BODY DIAGRAM + TEST

Define cable directions and anchor coordinates.

Add measured pull force versus speed.

Compare model to a controlled bench result.

### Speaker notes / rationale / questions

MAIN TALK — 3 minutes

Explain every variable: Ti cable tension, ui unit vector from claw toward anchor, m total suspended mass, g gravity vector, a acceleration, r effective radius, G reduction ratio, eta efficiency, omega motor speed. Four cable tensions with three translational equilibrium equations are generally underdetermined: state the tension allocation method and positive-tension constraints. These formulas assume an idealized taut-cable translational model, not a validated room payload. Holding torque is not running torque; include dynamic/friction margins and test. Do not reuse historical 40 N or 4 kg claims without reproducing assumptions and measurements.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 6 — Spool and cable-path decisions

### Visible content

MECHANISM

Spool and cable-path decisions

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

06

Compact spool

Shorten the spool to fit the available shaft engagement; target about 20 ft of line.

Winding behavior

Changing winding radius changes force and length per motor revolution.

Guide tradeoff

Compare a simple outlet with a level-wind mechanism: wear, friction, mass and complexity.

INSERT SPOOL SECTION / CABLE PATH

Dimension core radius, width, flange and shaft fit.

Show line anchoring and retention.

Add winding photos at low and high fill.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Use your current printed geometry, not an obsolete proposed CAD version. Explain the entire load path and why the spool cannot rely only on a shallow friction fit. A fixed guide redirects line but does not halve motor tension. Define whether a level-wind is in the as-built design or a future option. Add exact line diameter from measurement and capacity calculation; 120 lb line rating is not system capacity.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 7 — Removable wall station and load path

### Visible content

STRUCTURE

Removable wall station and load path

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

07

Serviceability decision

A fixed wall frame accepts a removable assembled motor housing.

Mechanical interface

Interlocking slide geometry carries load; positive retention must prevent unintended removal.

Failure cases

Rail-root cracking, layer separation, creep, fastener pullout and unintended upward motion.

INSERT EXPLODED VIEW + SECTION

Trace load: cable → spool/support → housing → frame → wall.

Show screws, engagement, fillets and retention.

Add print orientation and real installation substrate.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Explain which surfaces carry load versus locate the assembly. Do not claim gravity alone is a lock. Identify whether the positive retention feature is installed or still pending. Include wall fastener embedment, substrate, edge distances and worst-case cable direction before stating an allowable load. Printed strength depends on process and orientation; a nominal material value is insufficient. Role relevance: structures, lifting/rigging, failure modes and serviceable equipment.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.
Official SpaceX role: https://job-boards.greenhouse.io/spacex/jobs/8552671002 (accessed October 19, 2026).

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 8 — Fit, fabrication and assembly

### Visible content

MANUFACTURING

Fit, fabrication and assembly

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

08

Critical interfaces

Sliding rail clearance, motor pilot/bolt pattern, shaft engagement and lid access.

Process control

Record material, orientation, layer height, walls and dimensional inspection.

Assembly check

Prove tool access, cable routing, strain relief and replacement without dismantling the wall frame.

INSERT FIT COUPONS + DIMENSIONED DETAIL

Compare measured clearance and insertion force.

Show the selected fit and why it won.

Add assembly time and one inspection datum.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

This is a good mechanical manufacturing deep dive. Bring one dimensioned drawing you truly understand. Explain datum choice, tolerance stack and what happens at both limits. A 0.15 mm CAD clearance is not automatically a measured printed clearance. Use PETG coupons for final PETG acceptance; PLA trials are not a substitute. Record actual results rather than claiming proposed coupon offsets were tested. Role relevance: manufacturability, inspection, CAD and geometric dimensioning and tolerancing.

SOURCE / STATUS
Official SpaceX role: https://job-boards.greenhouse.io/spacex/jobs/8552671002 (accessed October 19, 2026).
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 9 — Gripper packaging and transmission

### Visible content

END EFFECTOR

Gripper packaging and transmission

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

09

Selected direction

Upper electronics/camera housing, rigid extension and lower servo-driven clamp.

Visibility versus mass

Camera offset and extension improve the view but add mass, bending and swing.

Gear decision

A proposed 3:1 reduction increases output torque while reducing speed and angular travel.

INSERT CURRENT GRIPPER SECTION

Show the MG996R servo, gear pair and jaw pivots.

Dimension jaw opening, lever arm and travel.

Add assembled mass and camera view with cloth.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Use the latest geometry you actually intend to print; the archived large V3 gearbox may not be the selected design. Clearly label proposed versus built. Do not claim full stall torque is continuous torque. Explain the servo-horn attachment and supports; a printed press fit alone is not verified torque retention. If both jaws share one drive, do not allocate the total output torque independently to each jaw. Suggested numerical force reasoning is in backup slide 17.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 10 — Motion, homing and fault response

### Visible content

CONTROLS

Motion, homing and fault response

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

10

Bench evidence

Motor jog and homing-switch input have worked on one station.

Integration sequence

Coordinated motion, bounded calibration and observed pickup/delivery remain test gates.

Fault response

A missed command, lost connection or reset must not trigger uncontrolled motion or load release.

INSERT OPERATING STATE DIAGRAM

Start → checks → calibrated → move → grip → verify → deliver.

Add fault branches and supported recovery.

Mark which transitions run in current firmware.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

The state flow is a proposed explanation, not evidence of an implemented state machine. Be ready to explain how local timing is generated, how commands are synchronized, and what happens on a Wi-Fi dropout. Shaft encoders can detect rotation mismatch but do not directly measure cable tension or all cable slip. Simultaneous bead homing is not generally compatible with four coupled cable lengths. No automatic power-cut drop test with a suspended load; support the mechanism during fault tests.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 11 — Debugging a motor that would not move

### Visible content

CHALLENGE

Debugging a motor that would not move

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

11

Observation | Interpretation / next check

Command log showed pulses | Command generation did not verify physical motion.

ENABLE changed 3.3 → 0 → 3.3 V | Enable control appeared to respond; check driver logic supply.

Reported logic rail ≈ 1.14 V | Found a poor 3.3 V connection.

Motor moved after connection repair | Capture the repeat test and before/after measurements.

INSERT: annotated meter photos + short bench video

Evidence status: reported bench observations; original measurement log still needed.

### Speaker notes / rationale / questions

MAIN TALK — 3 minutes

This is the clearest current physical problem-solving story. Observations are Jasper’s reported bench readings, not a captured laboratory data set. Insert original photos/logs and repeat the before/after measurements if possible. Successful command output was not proof of shaft movement. ENABLE reportedly changed 3.3 V → 0 V → 3.3 V, which redirected attention to supply/wake signals. A poor 3.3 V connection was then found and motor motion was reported after correction. Earlier XIAO overheating/failure has an unproven cause; do not call this the proven cause of that damage. Explain your exact measurement reference and decision sequence.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 12 — Verification from one station to four

### Visible content

TEST PLAN

Verification from one station to four

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

12

Stage | Evidence / acceptance criteria to fill

1 · One station | Jog/stop repeatability; pull force vs speed; temperature; switch response.

2 · Mechanical assembly | Measured fits; retained slide; supported proof test; inspection after cycles.

3 · Four-station 1 lb target | Position error; timing; tension behavior; supported fault response.

4 · Laundry task | Observed pickup + delivery; attempts, retries, garment classes and failures.

INSERT: test-fixture photo and pass/fail limits set before testing

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Keep this as a planned test matrix until the relevant tests are actually run. Predeclare measurable acceptance limits with rationale, capture setup/photos/raw data, and distinguish repeated cycles from independent units. For suspended tests, use a supported fixture or very low-height catch arrangement and keep people clear. The initial 1 lb test is not authorization for a room-scale payload rating. Role relevance: qualification, failure modes, stress testing and commissioning.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.
Official SpaceX role: https://job-boards.greenhouse.io/spacex/jobs/8552671002 (accessed October 19, 2026).

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 13 — Results and remaining limits

### Visible content

RESULTS

Results and remaining limits

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

13

Evidence class | What can be said now | What to add

Reported hardware result | One station: motor + switch work | Dated video, as-built circuit, repeat log

Design / analysis | Geometry and architecture iterations | Selected CAD revision; checked inputs

Not yet demonstrated | Room-scale pickup and delivery | Integrated trials with success criteria

INSERT RESULTS PLOT: measurement versus prediction, with error bars or repeat range

No demonstrated room payload, accuracy or reliability rating is claimed in this outline.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Replace reported status with actual dated evidence as it becomes available. Do not fill empty metrics with model outputs. Report sample size, operating conditions, failures and uncertainty. The website’s historical payload, workspace and accuracy headlines are not current demonstrated results. Good eventual metrics: maximum repeatable pull at chosen speed, temperature after a defined duty cycle, rail displacement under load, assembly time, independent position error, grip success by garment class and pickup/delivery success per attempt.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 14 — Lessons and what I would change

### Visible content

REFLECTION

Lessons and what I would change

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

14

Decision that helped

[Insert one measured example: removable station, local electronics or fit coupons.]

Decision that cost time

[Insert a specific assumption or rework event, its impact and the evidence that changed your mind.]

Half-time approach

Freeze one station’s interfaces, test its limits early, then duplicate the verified build.

INSERT BEFORE / AFTER REVISION

Show one real change and its measured effect.

Include time, cost or reliability impact.

Label any estimate as an estimate.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

The recruiter explicitly asks what you would do differently and how you would finish in half the time. Be candid without blaming tools or collaborators. Candidate lessons to verify in your own words: pulse count is not motion evidence; pin naming needs a controlled wiring table; interface changes compound late; calculation is a hypothesis until measured. Explain a scrappy solution that actually worked and one area where thoroughness mattered. The half-time approach is a proposal, not a measured 50% improvement.

SOURCE / STATUS
Recruiter presentation requirements supplied by Jasper, October 2026. [private correspondence; link omitted from repository]
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 15 — Current outcome and next release

### Visible content

CONCLUSION

Current outcome and next release

ROOMCLEANER · WORKING OUTLINE  |  19 OCT 2026

15

Established so far

Single-station motor motion and switch response reported; mechanical designs and integration work continue.

Next release gate

A repeatable four-station 1 lb demonstration with documented limits and supported fault tests.

Engineering takeaway

[Insert your one-sentence lesson about designing, building and verifying electromechanical equipment.]

INSERT LATEST HARDWARE PHOTO

Add a short offline demo when available.

Show the next gate and its acceptance criteria.

End here; technical backups follow.

### Speaker notes / rationale / questions

MAIN TALK — 2 minutes

Close on what you personally accomplished and what the evidence supports. RoomCleaner is an ongoing prototype, not commissioned production equipment. Make the connection to the role through the demonstrated method: requirements, mechanism design, assembly, debugging and verification. Avoid a generic SpaceX mission slide. Leave discussion time; the main slide timing totals 30 minutes before interruptions.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.
Official SpaceX role: https://job-boards.greenhouse.io/spacex/jobs/8552671002 (accessed October 19, 2026).

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 16 — Backup · electrical pathway

### Visible content

TECHNICAL BACKUP

Backup · electrical pathway

ROOMCLEANER · BACKUP  |  19 OCT 2026

16

Power branches

12 V input splits to the motor driver and the step-down converter; controller logic uses its regulated rails.

Interfaces

[Insert exact STEP, DIR, ENABLE, switch and ground connections from the working build.]

Review questions

Where do motor currents return? What prevents boot-time motion? Which tests detect wiring errors?

INSERT AS-BUILT CIRCUIT

Show connector labels, fuses and capacitor polarity.

Identify board revisions and test points.

Include the measured current-limit setting.

### Speaker notes / rationale / questions

BACKUP / PREPARATION

Use the schematic that matches the successful bench setup, not a speculative revision. Confirm XIAO ESP32-C3 pin aliases against actual code and board; the recorded plan uses D1/GPIO3 for STEP and D3/GPIO5 for ENABLE, but recheck every net. Do not turn this outline into soldering instructions. Record all regulator voltages, current limit, capacitor ratings, wire sizes and connector/fuse ratings. Keep motor current out of signal wiring. Abbreviations: DIR direction; STEP step pulse; ENABLE driver enable.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 17 — Backup · gearing and grip-force model

### Visible content

TECHNICAL BACKUP

Backup · gearing and grip-force model

ROOMCLEANER · BACKUP  |  19 OCT 2026

17

G = zoutput / zinput = 3   (proposed)

τoutput ≈ ηGτservo      θoutput = θservo / G

Ft = 2τpinion / dpinion      σbend ≈ KFt / (b m Y)

INSERT: tooth section, input torque, face width, module and material test basis.

Force at each jaw depends on torque sharing and the effective lever arm through travel.

Screening model only—not a validated life or grip-force rating.

### Speaker notes / rationale / questions

BACKUP / PREPARATION

Screening equations only. For a spur gear, Ft is tangential tooth force, b face width, m module and Y a dimensionless geometry-based Lewis form factor in the selected convention. Y is not derived from transmitted load or material hardness; do not use the dimensionally inconsistent formula pasted in the earlier discussion. K represents explicitly chosen load/service factors, not an arbitrary safety certification. Herringbone gears require the relevant normal/transverse geometry and additional analysis; the simple spur screen does not certify them. For equal jaws with an equal split of available torque, normal force per jaw is approximately total output torque/(2*effective lever arm); mechanism geometry changes the lever arm through travel. Friction-only retention requires 2*mu*N >= payload weight with a chosen margin, but cloth engagement is not a constant-friction rigid contact. Use measured force/cycles to validate. Do not claim a numerical factor of safety without a justified printed-material allowable.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 18 — Backup · calibration and sensing

### Visible content

TECHNICAL BACKUP

Backup · calibration and sensing

ROOMCLEANER · BACKUP  |  19 OCT 2026

18

Observability

A known-size floor marker gives camera-relative pose, not automatically room anchor coordinates.

Bounded startup

Define starting region and slack limits; test controlled take-up before autonomous lift.

Independent checks

Compare estimated pose against measured ground truth; use beads and encoders only for what they sense.

INSERT CALIBRATION EXPERIMENT

Label marker, camera transform and anchors.

Show measured residuals and an independent check.

List failure cases: slack, occlusion, slip and reset.

### Speaker notes / rationale / questions

BACKUP / PREPARATION

This is future work unless implemented and physically demonstrated. A rigid camera-to-claw transform and calibrated camera are needed to interpret marker pose. Unknown anchor locations, cable offsets and winding-radius errors need identifiable measurements; one image alone does not solve them all. Tilt sensing provides orientation, not absolute translation. An encoder stall is not a safe tension limit or a brake. Do not frame arbitrary-slack recovery as established. Explain assumptions and a bounded experiment instead.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 19 — Evidence to collect before the draft

### Visible content

PREPARATION · REMOVE BEFORE SUBMISSION

Evidence to collect before the draft

ROOMCLEANER · PREPARATION  |  19 OCT 2026

19

Priority | Insert / confirm | Used on

1 · Ownership + scope | Exact responsibilities, dates, selected CAD and test status | 1–4, 13

1 · Physical evidence | Motor video; voltage log; current wiring photo | 11, 13, 16

1 · Mechanical evidence | Load-path section; measured fits; one defensible sizing calculation | 5–9

2 · Quantified results | Safe test data, failures, assembly time and actual cost | 12–15

2 · Submission rehearsal | Resolve placeholders; rehearse questions; export offline files | Entire deck

### Speaker notes / rationale / questions

BACKUP / PREPARATION

Working checklist, not an interview slide. Priority is honest evidence for the existing station and mechanical design, not rushing unsupported suspended tests before the interview. Keep original files and versions. If no integrated demo exists by the deadline, present the verified subsystem scope and the explicit validation plan. Replace every bracketed placeholder or move unfinished material out of the submitted main deck.

SOURCE / STATUS
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.
Recruiter presentation requirements supplied by Jasper, October 2026. [private correspondence; link omitted from repository]

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

## Slide 20 — SpaceX prompt and role fit

### Visible content

PREPARATION · REMOVE BEFORE SUBMISSION

SpaceX prompt and role fit

ROOMCLEANER · PREPARATION  |  19 OCT 2026

20

What SpaceX explicitly asks / values | RoomCleaner evidence to emphasize

Recruiter: first principles + personal decisions | Cable statics, spool sizing, interface tradeoffs

Role: equipment from concept through commissioning | Removable station, assembly access, bring-up gates

Role: failure analysis + mechanical fundamentals | Load path, printed-part limits, fault diagnosis

Recruiter: results, failures and lessons | Measured bench evidence; candid remaining limits

30 min / ~15 slides · Draft: Oct 22 · Panel: Oct 27, 11:00 Central

Google Slides is for preparation. Bring local PowerPoint/PDF; cloud sites are blocked onsite.

### Speaker notes / rationale / questions

BACKUP / PREPARATION

SOURCE HIERARCHY: recruiter email is the direct presentation requirement; coordinator email supplies schedule/logistics; official job posting supplies role responsibilities. The suggested RoomCleaner emphasis is an inference, not an internal SpaceX scoring rubric. REQUIREMENTS: most technically challenging project; one about-me slide; scope/timeline/team; individual contributions; first principles and practical impact; graphics on each slide; good/poor decisions; lessons and half-time approach. About 30 minutes/~15 slides with interactive questions. Presentation on October 27, 2026, 11:00–12:00 Central; schedule subject to change. Submit three business days before, interpreted as Thursday October 22; confirm time-of-day with recruiter if needed. Cloud sites unsupported onsite: send actual file and bring local PPT/PDF. Keep confidential former-employer content out; only use permitted project material. TOPIC DECISION: RoomCleaner has strong personal ownership but incomplete system validation. If another project has stronger completed engineering results, compare topic summaries or use recruiter’s offered feedback before committing. Do not submit an unfinished project as if end-to-end success were established.

SOURCE / STATUS
Recruiter presentation requirements supplied by Jasper, October 2026. [private correspondence; link omitted from repository]
Interview logistics supplied to Jasper, October 2026. [private correspondence; link omitted from repository]
Official SpaceX role: https://job-boards.greenhouse.io/spacex/jobs/8552671002 (accessed October 19, 2026).
RoomCleaner project evidence/roadmap, October 18, 2026: https://github.com/Jaspario1199/RoomCleaner/blob/codex/design-history-2026-10-14/docs/history/presentation_roadmap_20261018.md . Read on October 19, 2026; file SHA a0b752ddb6509b1ec3cb5927adfa8dd563816c95. Cross-check against Jasper’s current as-built hardware.

Bracketed inserts and visual placeholders are intentional working-outline prompts. Replace them with your own evidence before submission. Sources inform structure; they do not establish unmeasured hardware results.

