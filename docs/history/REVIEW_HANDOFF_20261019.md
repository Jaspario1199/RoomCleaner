# RoomCleaner — review handoff and current decision ledger

Recorded 2026-10-19, America/Chicago. Documentation update for Jasper's review with another agent. No CAD, firmware, wiring, load rating or purchase status is released by this record.

## Start here

1. Read this handoff and the [presentation text + complete speaker notes](spacex_outline_snapshot_20261019.md).
2. Read [October 18 decisions](decisions_20261018.md), then [the later cost review](claw_cost_review_20261018.md). The battery baseline in the older decision record is historical and is not a frozen current bill of materials.
3. Use the [history index](README.md) to locate subsystem records. Resolve actual file availability before relying on a link.
4. Inspect the user's selected SolidWorks parts and the actual running sketch before proposing changes. Multiple proposed CAD versions are not interchangeable.
5. Return findings as: evidence → issue → engineering consequence → proposed fix → required verification. Distinguish a missing fact from an actual demonstrated defect.

The documentation branch is `codex/design-history-2026-10-14` in `Jaspario1199/RoomCleaner`. It has not been merged into the default branch by this task. Some historical CAD/export files are still outside the remote archive. This is not a complete binary CAD backup or a full chat transcript.

## Current state and authority

| Subsystem | Latest supported statement | What remains unverified |
|---|---|---|
| One motor station | Jasper reports successful motor motion and homing-switch input after correcting a poor 3.3 V connection; he is transferring successful bench wiring to a soldered assembly | Current as-built netlist, exact running firmware, current limit, pull-force/speed/thermal tests and post-solder regression |
| Four stations | Local ESP32-C3/A4988 stations selected; 12 V distribution branches locally | Four-axis timing, communication-loss handling, load envelope and physical coordinated tests |
| Wall mount/spool | User is CADing and printing removable wall frame, slide-in holder, housing and spool | Final adopted revisions, retention, dimensions, fits, supported load tests and fatigue/creep |
| Claw mechanism | Simple servo clamp with compliant pads; upper electronics/camera and lower servo on extension | Selected gear version, actual dimensions/mass, closure, horn retention and cloth grip |
| Feedback | AS5600 encoders and magnets discussed; encoder modules appear in later cart | Exact board/magnet identities, delivery, installation, wiring and firmware integration |
| Camera/calibration | Moving camera and floor-marker startup are design directions | Calibrated camera model, camera-to-claw transform, identifiable anchor/offset solution and bounded startup tests |
| Battery/charger | Purchasing evolved beyond earlier DROK/OVONIC/TB6B proposal | Final received battery, chemistry, protection, discharge limit, charger and as-built power path |
| Complete laundry task | Planned | Dated video verifying pickup, transport and release/delivery |

Evidence hierarchy: current physical measurements and actual as-built files > selected revision plus user confirmation > archived design proposals. A recent document timestamp alone does not make its circuit or CAD the selected build.

## Decision rationale and costs

| ID | Choice / problem | Why / tradeoff | Reviewer action |
|---|---|---|---|
| H19-01 | Local ESP32-C3 with reused A4988 at each wall unit | Reduces long motor/control harnesses and packages a removable unit; introduces distributed synchronization and fault handling | Verify local pulse timing and coordinated buffered motion rather than assuming Wi-Fi timing is deterministic |
| H19-02 | One 12 V pair per station, split to driver and buck locally | Powers motor and logic from one source; power returns must be appropriately sized and share a signal reference | Check source/branch fuses, conductor material/gauge, long-run voltage drop, connector polarity and return routes from as-built schematic |
| H19-03 | Default-disabled active-low ENABLE, pull-up R1 | Keeps output disabled when controller pin floats; disabling also removes holding torque | Verify resistor value/rail and startup state. Decide supported parking and fault response before suspending load |
| H19-04 | Unloaded motor bench success before integration | Isolates power, logic and coil pairing; makes fault diagnosis tractable | Save known-good sketch and record actual motion, not only logged pulse counts |
| H19-05 | Slide-in wall housing and fixed support frame | Enables bench servicing of the complete station | Identify load-bearing surfaces, positive retention, assembly/tool access, wall substrate and fastener engagement |
| H19-06 | Shorter spool for roughly 20 ft of line | Addresses limited motor shaft engagement and unnecessary capacity | Measure line diameter, core/flange/width, full winding radius, axial retention and spool-to-shaft torque transfer |
| H19-07 | Outlet ring / potential winding guide | Guides cable through varied directions; even winding stabilizes effective radius | Confirm the actually selected ring and finish. Fixed redirection does not halve tension; a level-wind adds friction and parts |
| H19-08 | Simple clamp before flexible fingers | Limits initial mechanism complexity and provides a testable baseline | Test flat and bulky cloth; label flexible fingers as deferred |
| H19-09 | Upper camera and electronics with lower servo on extension | Improves visibility of grip/payload and reduces near-ground housing obstruction | Measure mass, bending/swing envelope, wiring strain relief and view with cloth occlusion |
| H19-10 | Proposed 3:1 servo reduction | More output torque at the cost of angular travel and speed | Use actual servo voltage/torque, transmission efficiency, jaw lever arms and torque sharing; verify required opening |
| H19-11 | Spur versus herringbone geometry remains version-specific | Spur gears simplify prototype manufacture/support; herringbone may improve overlap but adds print and assembly issues | Confirm selected model. Tooth geometry is not “optimal” without load/material/life criteria and measured printed performance |
| H19-12 | Beads near claw, sequential homing after pose estimate | Center-position bead references limit reach; coupled cables cannot generally all retract to arbitrary references together | Audit geometry, allowed startup region, slack handling and homing motion; do not assume arbitrary slack is recoverable |
| H19-13 | Camera marker plus optional tilt/encoders | Supplies complementary observations | Marker-relative pose is not automatically room pose. Tilt is orientation, encoder is rotation; neither measures cable tension |
| H19-14 | Verify pickup by a partial transport move; verify delivery visually | Issued grip/release commands do not establish successful laundry handling | Inspect implementation and end-to-end evidence; do not mark delivered solely from state-machine progression |
| H19-15 | Keep physical results separate from calculations | Prevents simulated load/accuracy estimates becoming hardware claims | Reproduce assumptions and compare to measured tests at a named revision |
| H19-16 | Presentation structured around personal technical decisions | Matches recruiter's design-review prompt and the manufacturing role's equipment ownership requirements | Select strongest evidence, identify Jasper's work and outside contributions, and remove unsupported topics |

## Electrical debugging record

Reported sequence: command output showed pulses while the shaft did not move; switch worked; ENABLE was eventually measured at approximately 3.3 V idle, 0 V during run, then 3.3 V. SLEEP was reported around 1 V and the 3.3 V rail around 1.14 V. Jasper identified a bad connection and then reported motor motion after correction.

Reasoning: separate command generation from actual motion; check supply/reference/wake state before further code changes. This is a retrospective user report, not saved oscilloscope evidence. Earlier XIAO heating and failure to enumerate on USB has no proven root cause. Do not assert that a common-ground connection, buck negative bridge or USB backfeed caused that failure without evidence.

Recorded C3 bench mapping: STEP D1/GPIO3, DIR D2/GPIO4, ENABLE D3/GPIO5, HOME D10/GPIO10. Verify against the saved successful sketch and actual board before soldering; the claw S3 has a different pin map. The user kept R1 and R4; full protection circuits in other drawings are not automatically as-built. All resistor values and switch wiring require the actual final schematic.

## Procurement correction — later cart, not verified receipt

The visible conversation includes a later Amazon cart with the following candidates. This is later purchasing evidence than the older DROK/OVONIC/TB6B proposal, but a pasted cart does not establish an order or delivery.

| Cart item | Quantity shown | Status / unresolved detail |
|---|---:|---|
| ZTW UBEC, 10 A peak / 6 A continuous, selectable 5/5.5/6 V | 1 | Candidate; confirm exact received model, input range and output setting |
| Tenergy 7.4 V Li-ion 2200 mAh module with PCB | 1 | Candidate; exact part ID, dimensions, protection thresholds, continuous/peak discharge and connector need confirmation |
| USB-C 2S boost charging module, variant “2S1A” | Pack of 2 | Candidate; verify actual 8.4 V charging behavior, battery compatibility, balancing/protection and power-path behavior |
| 1000 µF / 16 V electrolytic capacitor | Pack of 15 | Candidate servo decoupling; verify identity/polarity/location |
| 100 nF ceramic capacitors, “104” | Pack of 100 | Candidate filtering/decoupling |
| 16 AWG red/black pure copper cable, 100 ft | 1 | Candidate long distribution cable; verify conductor identity and run/branch sizing |
| FR4 perfboards | Pack of 34 | Candidate assembly medium; holes do not imply shared conductive rails |
| Dupont jumper wires | Pack of 120 | Candidate signal/prototyping connections, not automatically motor/servo power wiring |
| Breadboard jumper kit | 840 pieces | Candidate prototyping wiring |
| AS5600 encoder boards | Pack of 5 | Candidate feedback upgrade; magnet inclusion not established |

The conversation also includes a 100 kΩ/33 kΩ battery measurement proposal; the October 18 decision file later records 100 kΩ/47 kΩ for another circuit. These are alternative revisions, not interchangeable values. Resolve actual battery maximum voltage, reference, attenuation and divider loading, then align firmware with the installed network.

The Tenergy Li-ion module cannot inherit OVONIC LiPo dimensions or discharge claims. A protection PCB is not a complete charger; a USB charging board may lack balancing, discharge protection or load sharing. Reconcile the final power schematic from exact component identities before declaring the BOM complete. Do not buy duplicate regulators solely because different historical records mention them.

## CAD and artifact map for the reviewer

User-provided filenames in the conversation include `Spoolv3.STEP`, `Shell_Casing.STEP`, `Slipin_mount_piecev3.STEP`, `Wall_Mount_v3.STEP` and `Gripper_gear_housing.STEP`. These identify desired source inputs; their presence on this branch is not established by this update. Obtain those exact revisions from Jasper or the project file archive and compare them with printed parts.

Earlier archived proposals include V2 18:54 reduction with 36:36 synchronization and a later V3 proposal with different synchronization/packaging. Neither is automatically the user's selected SolidWorks design. Nominal valid-solid checks and sampled collision tests do not prove continuous motion clearance, assembly access or load capacity. Preserve the user’s chosen version and record modifications explicitly.

The Google Slides deck is stored in Drive; GitHub now holds its full textual snapshot and reasoning. This task does not upload the binary PowerPoint, render images, native SolidWorks files or all historical STEP files. The older index's incomplete-backup limitation remains valid.

## SpaceX presentation structure and why

The live deck has 15 main slides for approximately 30 minutes, followed by three backups and two preparation pages. Its first slide is about Jasper; the main story proceeds through requirements, individual ownership, architecture, first-principles sizing, spool, mount, fabrication, gripper, controls, diagnostic failure, verification, results, lessons and next release.

Why this emphasis: the official Mechanical Engineer, Insource Manufacturing (Starlink) posting focuses on custom equipment, structures/mechanisms, end effectors, assembly/manufacturing, failure analysis and commissioning. This is role alignment inferred from the public job description, not an internal grading rubric. Source: https://job-boards.greenhouse.io/spacex/jobs/8552671002 .

The user-supplied recruiter prompt explicitly asks for personal contribution, good and poor decisions, first principles, practical impact, visuals and metrics, lessons, and an approach to completing the work in half the time. The deck provides prompts for all of these, including thorough versus scrappy examples in notes.

Do not claim historical “9 lb”, “4 kg anywhere”, “40 N motor limit”, “±1 cm”, “63% room volume”, “29 tests” or “$230 total” as present hardware results without fresh source/test verification. One working unloaded station is a meaningful result; it is not full-system validation. Keep proposal, calculation, CAD check, user-reported hardware result and documented physical test distinct.

The outline has intentionally unfilled photos, plots, dimensions and ownership details. Add only material Jasper can explain under detailed questioning. Export a final local PowerPoint/PDF for onsite use; preparation uses Google Slides. The requested submission lead time implies October 22 for the October 27 interview; confirm time-of-day directly if needed. No recruiter email or submission was sent by this task.

## Review priorities and specific questions

1. Which exact CAD parts are being printed and which gear train is adopted? Provide revision/date and assembly screenshot.
2. What exact station sketch is running, and does the soldered version pass the same jog/switch checks? Save schematic, pin table, board photos and firmware.
3. What are the actual motor part number/current rating, A4988 sense-resistor value/current limit, spool radii and speed? Establish measured pull force and temperature before payload claims.
4. What positively retains the housing in its wall frame, and how is the wall load transferred into the substrate? Record engagement, print orientation, fastener details and supported proof-test results.
5. Which battery, regulator and charger were actually purchased/received? Provide labels or exact order links, not cart names alone.
6. Which encoders/magnets are physically installed, and what software reads them? Provide direction, wrap/reset and tracking-error evidence.
7. What startup/calibration and fault handling is implemented versus proposed? Inspect code, then define bounded physical tests.
8. Which three engineering decisions can Jasper support with his own before/after evidence? Prioritize these for the interview.

## Change and provenance discipline

- Each next decision should include problem, alternatives, selected option, rationale, assumptions, revision, test and remaining gap.
- Add dated evidence; preserve previous records and mark superseded claims rather than deleting history.
- The current full deck snapshot is a point-in-time record. Changes to Google Slides are not automatically committed to GitHub.
- This handoff uses the visible conversation, the current native deck readback and remote documentation inspected on October 19. It does not invent missing prior assistant responses or reconstruct unavailable measurements.
