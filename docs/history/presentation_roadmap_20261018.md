# RoomCleaner — presentation evidence and roadmap

Prepared 2026-10-18 for Jasper's SpaceX project presentation. This is an outline and evidence checklist, not a claim that the full robot has operated. Pair with the [current decision record](decisions_20261018.md) and [version index](README.md).

## Suggested narrative

1. **Problem and requirements.** Pick laundry with four wall winches and a suspended camera-equipped gripper. Explain room coverage, low suspended mass, serviceability and use of purchased hardware. Separate the initial central one-pound test weight from the longer-term jeans/five-pound reserve discussion.
2. **Architecture evolution.** Show central Arduino/driver wiring followed by local ESP32/A4988 stations. Explain why long motor harnesses motivated the change, and the new synchronization, power and fault-handling responsibilities.
3. **Mechanical iteration.** Show the removable wall frame, retained slide-in casing, spool and bead homing mechanism. Then show simple padded clamp, camera outrigger and lower servo extension. Explain assembly access, line routing, camera visibility and payload mass tradeoffs.
4. **Force and motion reasoning.** Present torque-to-cable-force dependence on spool radius and speed; show 3:1 geared jaw tradeoffs. Explain that torque multiplication reduces travel/speed, jaw force depends on lever arms, and nominal motor holding torque is not a running load rating.
5. **Bring-up and debugging.** Walk through actual measurements: logic rails, active-low ENABLE and switch state. Describe motor motion after correcting the reported 3.3 V connection. Distinguish this resolved connection issue from the earlier controller damage whose root cause is unproven.
6. **Next validation and roadmap.** Show tests required for camera/servo battery power, load retention, coordinated winches, floor-marker calibration and verified pickup/delivery. Explain what is built, what is predicted and what remains to measure.

## Claims that can be used, with appropriate qualifiers

| Topic | Accurate wording now | Evidence to add before making a stronger claim |
|---|---|---|
| One motor station | "I brought up one ESP32/A4988 station and reported successful bench motor motion after correcting a logic-supply connection." | Dated video, wiring photo, running firmware, load/speed/current/thermal readings |
| Electrical diagnosis | "I separated power, logic and command checks instead of treating transmitted pulses as measured motion." | Measurement log and exact fault/fix photographs |
| Geared gripper | "The CAD prototype uses 3:1 reduction with synchronized opposing jaws; nominal geometry checks were recorded." | Printed fit, coupling retention, actual 5 V grip-force measurements and cycle testing |
| Simulation | "Simulation and analysis informed the design and exposed assumptions to test." | Versioned inputs and reproduced results; physical comparison before claiming accuracy |
| Local station architecture | "Local controllers reduce long motor wiring; synchronized multi-axis execution remains a commissioning milestone." | Four-axis timing, dropout, reset and load evidence |
| Camera pickup verification | "The planned success criterion is observed payload movement, then observed delivery." | End-to-end video and retry/error records |
| Encoders | "Provisioned as a feedback upgrade to compare commanded and measured shaft motion." | Installed sensor/magnet photos, angle logs, tracking-error and reset/wrap tests |
| Startup calibration | "Designed a bounded floor-start and marker-relative calibration procedure with sequential bead verification." | Actual lift, camera calibration, estimator residuals and independent position checks |
| Battery system | "Selected a 2S/DROK power architecture and identified the remaining protection/interface tests." | As-built schematic, received-part identities, surge/current/thermal/cutoff tests |

Do not present historical website claims such as 9 lb payload, 4 kg anywhere, 40 N motor limit, ±1 cm grab accuracy or a test-count headline as current hardware results. Do not call an estimated force a demonstrated factor of safety. Reproduce software tests at a named commit before quoting their current count.

## Milestones

| Stage | Current evidence status | Exit criteria |
|---|---|---|
| M1 — One motor station | Motor/switch/serial operation reported by user; measured test package incomplete | Saved as-built circuit and sketch; repeatable jog/stop, rail/current/thermal records |
| M2 — Claw electrical and mechanical integration | CAD prototype and component selection; final interfaces still open | Fit/mass records, 5 V camera+servo test, verified power protection, grip/release cycles |
| M3 — Four-station one-pound demonstration | Planned | Coordinated local timing, supported fault recovery, measured cable/load behavior |
| M4 — Floor-start calibration | Research/specification and synthetic work | Controlled physical startup and accepted visual/bead calibration evidence |
| M5 — Laundry pickup and delivery | Planned integrated demonstration | Video verifies pickup, transport and delivery; retries and failures logged |
| M6 — Automatic charging dock | Concept; manual charger is current prototype plan | Mechanical seating/contact qualification, correct charging/balancing/termination and recovery |

## Evidence capture for each new revision

Use [stage_template.md](stage_template.md). Record:

- Date, subsystem/version and previous revision being changed.
- Problem, alternatives, selected decision, reason and measured or assumed inputs.
- CAD/code commit, dimensions, drawings and BOM changes; exact ordered/received status.
- Test setup and pass/fail criteria, raw measurements, photos/video, failures and fixes.
- Remaining risks and next action, with the exact evidence needed to close it.

Preserve old versions and link the superseding record. Do not silently overwrite the reason a choice was made. GitHub commits provide immutable references; add milestone tags only to clearly scoped snapshots, never imply a documentation tag is hardware qualification. Verify the GitHub read-back before reporting an upload complete. Record missing artifacts explicitly rather than presenting the design-history branch as a complete CAD backup.
