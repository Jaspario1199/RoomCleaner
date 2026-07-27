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
- R8. Vertical reach (cable plane → fingertips) ≈ 130 mm; recorded as EFFECTOR_REACH and consumed by the motion planner.
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
