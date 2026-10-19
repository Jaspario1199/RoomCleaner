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

D11. **Finger assembly placement corrected (integration find)** — the finger's
local frame is ventral-anchored (y=0 at the notched face), so placing at the
raw pocket radius pushed each finger H_BASE/2 = 6.5 mm outboard (445 mm³
interference). Assembly translates to pocket_r − H_BASE/2; part files untouched.

D12. **EFFECTOR_REACH corrected 130 → 118 mm (integration-measured)** — the
original C5 sum double-counted the hub: the finger's 12 mm base fills the hub
thickness. Contract, config, calc, and R8 all updated; grab pose now
GRAB_Z = 0.138 m.

D13. **Rigid printed corner mounts replace hanging eye-hook anchors (user
request, lead-approved)** — the QXSKSLH closed-eye hooks made each corner a
pivot: the winch/pulley assembly could swing, moving the effective anchor
point that the kinematics and calibration treat as fixed (the calibration
sensitivity study shows ~1:1 anchor→position error transfer). New part
`corner_mount` unifies the NEMA 17 bracket and pulley ears on one 6 mm base
plate, screwed with 3× #10 × 3" wood screws in a line into a ceiling joist or
high wall stud (screws in shear on wall mount, install easier). Load path:
motor bolts to bracket, bracket to wood — nothing hangs from the motor or the
drywall. BOM: eye hooks (−$14) out; wood screws (~$8) in. motor_mount and
corner_guide remain in the repo for bench/legacy use but the corner install
uses corner_mount.

D14. **Homing switch moves from the spool–pulley span to the vertical drop
below the pulley (user find, lead-approved, 8/28)** — with the switch
mid-span, home = "bead between spool and pulley", so the stopper bead had to
ride over the pulley groove on every descent and every homing run (groove is
sized for 0.5 mm line; a bead climbs the flanges or jams). Relocating the
KW12-3 to a short drop arm beside the vertical line under the pulley keeps
the bead permanently on the vertical span — it never crosses the pulley.
Wiring (C + NC, fail-safe), firmware (`H`, HOME_BACKOFF), and the ~4 mm bead
set-back are unchanged; only the actuation direction becomes vertical.
corner_mount rev C implements it; the mid-span boss is removed. New interface
value CORNER_PULLEY_OD_NOM (20 mm, purchased U-groove bearing pulley, 18–22
mm accepted) fixes the drop line's X offset from the ear centre.

---

## Generation 2 (SolidWorks redesign, October 2026)

Recorded 2026-10-19 from Jasper's Drive files (folders v1 Oct 7, V2 Oct 11,
v3 Oct 18, Claw_V1 Oct 12, V5 Oct 18–19) and "RoomCleaner — SpaceX Technical
Presentation — Outline v1". These are Jasper's decisions; rationale is as
stated in the outline. Generation-1 decisions D1–D14 remain on record; where a
D15+ decision changes direction it says so, it does not erase the earlier one.

D15. **Removable wall station replaces the one-piece corner mount.** A fixed
wall frame accepts a slide-in motor housing with a shell cover. Reason:
serviceability; a station can be pulled and swapped without disturbing the
installed frame and its calibrated anchor position. Supersedes the
installation role of `corner_mount` (D13); `cad/parts/corner_mount.py` and its
rev A–D.1 history stay as the gen-1 record. Open item: positive retention so
the housing cannot slide out under cable load or vibration (review R3).

D16. **Shortened spool.** Spool length reduced to match the motor shaft's
usable engagement; target ~20 ft of stored line. Supersedes the gen-1 spool
length (26 mm drum). Open item: wound-radius change vs force and
length-per-revolution (review R4).

D17. **Distributed winch electronics.** Each station carries a Seeed XIAO
ESP32, an A4988 and a step-down regulator, fed by one 12 V pair; stations are
coordinated over Wi-Fi. Supersedes the central Uno + CNC Shield architecture
for the installed robot (the shield remains the bench reference). Open items:
synchronized motion, boot-time and comms-loss behavior, kill switch coverage
(review R1, R2).

D18. **Two-jaw geared clamp gripper.** MG996R → 18T pinion → 54T/24T compound
→ 24T follower: 3:1 reduction, second jaw counter-rotates through the 1:1
stage. Electronics/camera housing above a rigid extension ("Griper Cylinder").
Supersedes the five-finger tendon claw (gen-1 `tentacle_*`, `tendon_drum`
parts kept on record). Open item: printed gear tooth strength at servo stall
(review R5).

D19. **First integration target is a 1 lb test weight on four stations**, not
the 0.9 kg laundry payload; no payload, accuracy or reliability rating is
claimed until measured.

Note (10/19): Codex's decision record from `codex/design-history-2026-10-14`
is archived verbatim at docs/history/codex_DECISIONS_20261019.md, and its
dated decision logs at docs/history/decisions_20261014.md,
decisions_20261018.md and startup_decision_20261016.md (SC01–SC10). Those
startup-calibration decisions are adopted by the control system V1
(docs/CONTROL_SYSTEM_V1.md).

D20. **Control system V1 architecture** (docs/CONTROL_SYSTEM_V1.md): the host
plans and coordinates; stations execute Hermite segments in their own clocks
with path-time feed-hold, leases and peer-broadcast holds; the Python station
core is the specification and the C++ firmware must match it trace-for-trace.

D21. **Stop never disables.** Every fault and pause holds torque; only a
`disarm` confirmed with `claw_supported` (and vision or recorded state showing
support) removes it. The power strip is the only category-0 stop. No
safety-rated function is claimed (ISO 13849 / IEC 61508 not claimed).

D22. **Calibration estimates anchors in the marker frame**; the room frame
enters only through the operator's anchor entries and marker heading as
priors, and through floor slide bearings. Acceptance requires
identifiability, residual adequacy, uniqueness, held-out witnesses and a
predicted-sigma volume; partial acceptance is LOCAL_ONLY within the validated
hull.

D23. **Slack is modelled, not assumed away.** A common-point claw with stiff
cables hangs on three cables whenever lengths are inconsistent; the estimator
selects a per-sample slack hypothesis and excitation grows in stages.

D24. **Bead searches are gated on absolute-length sigma** (k*sigma <= window,
2*k*sigma <= overtravel); captures are fused by refitting the whole model,
never by overwriting L0 alone. In simulation vision alone gives sigma ~20 mm,
so beads are BLOCKED until open decision D-B is taken.

D25. **No automatic resume** after any reboot (host, station, claw): host
start goes to DISARMED if the claw is known supported, else
RECOVERY_REQUIRED.
