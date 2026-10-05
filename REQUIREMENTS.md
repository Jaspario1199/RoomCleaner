# Current system requirements and resolution scope — 2026-10-04

The active architecture and unresolved parameters are controlled by `docs/DESIGN_RESOLUTION_PLAN_20261004.md` and `docs/design_resolution/unknown_parameters.json`. The five-finger requirements retained below are historical and superseded for the first build.

- CR1: Four slide-in, positively retained wall stations, mounted into qualified structural backing; one common main housing preferred.
- CR2: Spool encoders on all four motors; measured payout and travel limits, not shaft angle alone, govern room motion.
- CR3: Stationary metal cable guide and bead-triggered sliding collar operate a retained KW12 switch; supported/detached calibration precedes suspended operation.
- CR4: Two-jaw servo clamp with TPU95A pads, printed150mm extension first; battery, XIAO-S3 Sense camera and IMU above, servo below, removable lid and retained electronics/harness.
- CR5: Four spaced upper cable attachments. No deliberate attitude maneuvers. Near-level settled pickup is required; achievable workspace and allowable attitude must be measured/modelled. An IMU is not assumed to guarantee level.
- CR6: Jeans are the working laundry payload; weigh the actual representative garment. Prior0.9kg is a provisional screening reference only. User requested5lb (2.26796185kg) as capacity reserve to investigate, not the normal required garment load or an achieved factor of safety. Evaluate claw dead weight, dynamics, unequal cable forces and weakest interfaces separately; all capacity claims require verification.
- CR7: Slow final approach and payload probe; camera confirms pickup relative to scene before transit. Delivered count requires confirmed deposition after release/retreat. Ambiguous evidence cannot mark success.
- CR8: Claw-mounted primary camera uses calibrated image-specific pose, freshness and visibility. A fixed-camera homography cannot be silently reused.
- CR9: Intended product station has one retained low-voltage plug; combined power/data is the preferred development direction after user clarification. Exact transport, connector and pins remain to be engineered. Suspension braid carries mechanical load only; encoder/driver/controller power and data are routed electrically at each wall station. No AC mains inside printed housings.
- CR10: M3 preferred, documented M2 exceptions allowed; PETG structural/TPU pads with actual K1/K1Max profile, fit/strength/thermal/creep qualification.
- CR11: Global coordinated motion and fault/boot recovery must be verified before room operation. A software pulse stop, loss of power and mechanical load holding are separate behaviors.
- CR12: Complete-station print/order release requires one coherent assembly revision, resolved critical mates and source/physical verification. Current canted outlet and local power packaging remain experimental.

- CR13: Immediate milestone is a complete housing prototype with bounded bench interfaces, before room survey. A possible supported two-motor planar test precedes installed four-station pickup. Room-specific geometry is deferred; this does not qualify the outlet for arbitrary room angles or provide a structural load rating.

## Historical five-finger requirements

# RoomCleaner — Requirements (mechanical scope: the claw / end-effector)

Judged success: the claw, hanging from four Dyneema cables, descends onto laundry,
closes five tendon-driven fingers with one servo, holds the item through transit,
and releases it — repeatably, with every part printable or on the approved BOM.

## Functional
- R1. Grip and hold items 0.05–0.9 kg (sock → jeans) during transit at ≤2 m/s² vertical acceleration.
- R2. Release reliably on command (servo return; gravity + finger springback eject the item).
- R3. All five fingers actuate from ONE MG996R-class servo (tendon drum).
- R4. Wireless effector: ESP32 + 2S LiPo + 6 V buck + power switch ride on the claw; only the 4 cables touch it.
- R5. Tendon pre-tension must be individually adjustable after full assembly.
- R6. Servo horn must be attachable at a known zero (RELEASE) angle via a documented procedure/firmware endpoint.

## Physical / envelope
- R7. Total claw mass ≤ 0.45 kg (the value the workspace/tension analysis assumed).
- R8. Vertical reach (cable plane → fingertips) ≈ 118 mm (integration-measured); recorded as EFFECTOR_REACH and consumed by the motion planner.
- R9. Fits within a 100 mm square footprint at the plate (cable clearance at the corners).

## Interfaces (authoritative details in cad/interfaces.py)
- R10. Servo: MG996R inverted (body above plate, spline down), ear-screwed to the plate.
- R11. Cables: 4× tie-offs at plate corner bosses (Ø3.2 holes), knot spec Palomar.
- R12. Frame↔hub: 4 printed standoffs on a shared bolt circle; heat-set M3 inserts + M3×8.
- R13. Fingers: base into hub through-slots from below, shoulder bears on hub underside (floor loads), axial M3+washer from above (gravity loads).
- R14. Electronics: strap-mounted on plate top; cover with switch + USB cutouts; cover must not intrude on cable corner cones.

## Manufacturing
- R15. FDM printable without supports in the documented orientations; PETG structural, TPU 95A fingers.
- R16. Threads in plastic use heat-set M3 inserts wherever fastened more than once.

## Loads
- R17. Worst case at the plate: 40 N per cable (motor limit). Claw structure margin ≥3 on that.
- R18. Servo torque budget: total tendon load ≤ 25 N at the drum; required torque ≤ 3.5 kg·cm (3.44 at DRUM_CORE_R=13.5) vs ~10 kg·cm available.

## Acceptance
- A1. Every part passes independent geometry verification (dims, interfaces, STEP round-trip).
- A2. Assembly integrates with zero static interference and documented clearances.
- A3. Mass rollup ≤ 450 g from measured part volumes × material density + purchased masses.
- A4. pytest suite stays green; EFFECTOR_REACH consumed by planner without breaking sims.
