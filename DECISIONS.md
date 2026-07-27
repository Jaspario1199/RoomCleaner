# Design Decisions

D1. **Tentacle gripper over pin/scoop** — five tendon-driven curling TPU fingers;
gathers crumpled cloth without needing a pinch feature. Pin gripper remains the
documented fallback for flat items. (Research phase, docs/RESEARCH.md.)

D2. **Inverted servo** — MG996R body ABOVE the plate, spline down through the
pocket. Keeps the sub-plate volume clean for the tendon mechanism and puts the
servo mass with the electronics. Rejected: body-below (collides with hub,
fouls tendon paths).

D3. **40 mm standoff stack-up** — hub hangs on 4 printed standoffs; the gap houses
the tendon drum and gives wrench/tendon access. Resolves the servo↔hub collision.

D4. **Flanged tendon drum, tie-offs on the bottom face** — one drum winds all 5
tendons (equal pull); flanges stop slack tendons jumping off; bottom-face tie-off
holes are reachable through the hub's central bore after full assembly (R5).

D5. **Through-slot finger mounts with shoulders** — pocket floors deleted (they
blocked the finger); a 2 mm base shoulder bears on the hub underside for floor
loads; axial M3+washer from above carries gravity. TPU threads only ever see the
finger's own weight.

D6. **Standoff bolt circle moved to shared parameter + new angles** — frame and
hub previously used DIFFERENT hole circles (27.0 vs 23.6 mm — latent bug found
during interface unification). Now one authoritative HUB_MOUNT_R = 27.0 at
angles [36°, 108°, 252°, 324°] chosen to clear the five finger pockets (72°
pitch) with ≥5° of material margin.

D7. **Electronics exposed-strap v1 + printed cover** — ESP32/LiPo zip-tied to the
plate bands; cover screws to 4 edge-midpoint insert holes, with switch + USB
cutouts and 45° corner notches clearing the cable cones. Dock charging deferred
(roadmap Phase 4).

D8. **Servo zeroing via firmware** — /setup endpoint parks the servo at
RELEASE_ANGLE so the drum/horn is pressed on at a known zero (R6).

D9. **EFFECTOR_REACH = 0.13 m** enters the motion config; grab pose is derived
(fingertips at floor when the plate is at ~0.15 m — coincides with SAFE_MIN_Z, so
existing workspace analysis holds unchanged).

D10. **Buck converter risk accepted** — MP1584 (3 A) vs MG996R stall (~2.5–3 A)
is marginal; brief brownouts possible under stall. Escalation path: 5 A UBEC.
Not a geometry decision; recorded for the electronics BOM.
