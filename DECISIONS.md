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

D26. **D-B resolved: the ceiling and wall margins, not bead precision,
protect against absolute-length error** (user decision, 2026-10-20). The robot
starts near the room centre on the printed floor reference, gross slack is
caught on the floor by the bounded one-cable-at-a-time take-up, and the claw
is kept `ceiling_margin_m` (0.4 m) below the anchors and `workspace_margin_m`
inside the walls. Rule: the calibration may grant full-workspace operation
only if the predicted absolute claw-position / cable-length sigma over the
whole workspace satisfies k*sigma <= the relevant margin (k = bead_k_sigma),
checked at every startup, and only when that sigma is honest: per-pose slack
probing on and the witness chi-squared consistent. Otherwise the robot stays
LOCAL_ONLY. Beads become end-of-travel switches (NC, station stops if hit);
a bead search is optional, never required. Supersedes the "beads required for
VERIFIED" reading of D24 (D24's gating of any bead search still applies).
Also adopted: per-pose slack probing by motion onset during suspended
calibration (user's method: reel each cable in turn; no claw motion = slack),
and a printed multi-sheet floor reference (~1 m, spaced Letter sheets, scale
check) replacing the single 6" tag once the slack probe makes its sigma honest.

D27. **No IMU on the claw** (Jasper, 2026-10-20). The Adafruit 3886 / MPU-6050
is dropped from the design. Claw tilt comes from vision when the floor
reference is in view; the camera-to-body mounting offset is measured at every
startup while the claw rests upright on its jaws over the printout (Jasper's
proposal). Away from the reference the claw waits for the pendulum to settle
and uses the cable model's static-equilibrium tilt; the host approves grips
(the firmware's own IMU tilt gate is removed). Camera bay: IMU pocket removed.
Supersedes the IMU parts of D20/D22 (gravity fusion becomes optional, unused).

D28. **Cut the claw tube by 50 mm, to 254.8 mm** (Jasper, 2026-10-20). The
extra length isn't needed; start at 50 and cut more later if wanted. Evidence
(verification/claw_tube_length_view_study.md, v7 head): the grasp spot is
fully visible from a hover of 140 mm (172 mm uncut); about 9–13 % of the view
is blocked; the box (cable tie-offs) is 474 mm above the jaw tips when
gripping; 33 g saved. Recommended cut was 100 mm; the remaining cut up to the
~206 mm limit stays available. Everything above the tube (box, camera bay,
cover, cylinder) moves down 50 mm relative to the head. The claw body frame
and the approach hover follow from this.

D29. **Winch drivers at 1.35 A on the existing A4988s, vented shells**
(Jasper, 2026-10-21). The BOM is fixed (no driver swap); shells are already
vented. Estimate (gen2_motor_thermal model, 0.019 in fin, ~23 °C near the
ceiling): motor case ~52 °C vented, A4988 junction ~82–127 °C vented (165 °C
shutdown). Cable tension ~43 N (from 32 N at 1.0 A), so the claw mass budget
rises to ~750 g with a 1 lb payload at the 0.4 m ceiling margin. Vref = 8 × I
× Rsense: R100 → 1.08 V, R050 → 0.54 V. Confirmation: 60 min hold test; if the
driver heatsink exceeds ~70 °C, drop to 1.25 A. Station schematic Rev D.

D30. **Winch current set to the carrier's maximum, Vref ≈ 0.85 V (≈1.06 A),
superseding D29's 1.35 A** (Jasper, 2026-10-21). Measured: the red R100 A4988
clones top out at ~0.79–0.85 V Vref on 3.3 V logic, so 1.35 A is not
reachable without board rework (rejected); VDD stays 3.3 V. Cable tension
returns to ~34 N (32 N at 1.0 A, scaled). Shells stay vented; thermal margin
is now large. Lift capacity must come from claw mass, ceiling margin, or a
smaller spool drum (Ø10 core study pending).

**Erratum to D29/D30 (2026-10-21, lead).** The "~43 N" (1.35 A) and "~34 N"
(1.06 A) per-cable figures and the "~650–750 g claw budget" were based on
holding torque at the empty-spool radius (the snag/slip load), not the running
pull. At 1.06 A the running pull is ~23.8 N at the core and ~17.9 N at a full
spool (11.9 N design force with the 1.5 margin), so the worst-case lift
anywhere in the working area is ~1.1 kg total (claw + payload). D30 (Vref at
the board maximum) stands; the capacity consequence is open — see
`docs/decisions/WINCH_CAPACITY_20261021.md` (pull test first; 3:1 winch
reduction recommended).

D31. **Claw power: Tenergy 7.4 V 2S pack, ZTW UBEC at 6.0 V for the servo, MP1584
at 5.00 V for the XIAO, USB-C 2S charger on the claw** (Jasper, 2026-10-21).
Battery: Tenergy 7.4 V 2200 mAh 2S1P Li-ion with protection PCB (the 10/19 cart
item; 31003 assumed: 3 A continuous, 1 A max charge). The servo rail matches
`firmware/claw_s3` ("servo power from the 6.0 V buck"); the XIAO 5V pin is fed
from a separate MP1584 through a 1N5819, never from the 6 V rail. Battery sense
200k/100k on D2/GPIO3 (firmware BATT_RATIO 3.0, cutoff 6.8 V); servo PWM on
D0/GPIO1. Charging: the USB-C 2S module sits on the pack side of the main switch
and is used with the switch OFF (Jasper chose "whichever is best, we were going
with the on-claw charger"; lead kept it, with the condition that the module is
verified as an 8.4 V CC/CV type at ≤ 1 A before first charge). Supersedes the
Rev A two-5 V-regulator / FSR / buffer drawing and the 10/18 18650 proposal
(both kept as history). Schematic: docs/electrical/claw_revB_20261021/.
D31 consequence — charging rule (lead, 2026-10-21): the standing rule "balance-
charge the LiPo with the pack off the robot" is replaced for the Tenergy pack
by: charge only with SW1 OFF, attended, on a non-flammable surface, with an
8.4 V CC/CV charger at ≤ 1 A; the pack's protection PCB must provide per-cell
overcharge/over-discharge protection (confirm on the label/datasheet before the
first charge, because a 2-wire pack cannot be balance-charged). Deck B7, the
phone-app start checklist and the claw spec follow this wording.

D32. **Gripper 1021 is the build baseline; hands are four-bar couplers** (Jasper,
2026-10-21: "this is my final gripper assembly"; lead design of the hands).
Jasper's `1021LaundryAssem` (v6r gears, his gear housing, arms, housing,
cylinder, 12 in tube) supersedes v7 for building; v6/v7 are kept as history.
Each hand joins the gear crank pin (r 53) to the arm tip (r 50): a
near-parallelogram four-bar (ground 36.54, coupler 34.67), so the hands
stay within ~1° of parallel. Working crank range −5° to −62° (faces meet);
servo travel ≈ 114°; the arm hits the crank at −70°. 53 mm opening, and the
tips drop ~38 mm while closing (close from ~35–40 mm above the floor). The
follower must be meshed 6° from its file pose. The housing gets the verified
v6 camera bay (r 90, same lens position). Cable-to-bay clearance is ≥ 12 mm
within ±15° claw yaw; contact is possible at ≥ 30° yaw near the ceiling, so
start square to the room. Spec: cad/GRIPPER_1021_SPEC.md; checks:
verification/gripper1021_build_notes.md, gripper1021_hands_lead_check.md.

D33. **The overhead camera is retired; the claw camera is the robot's camera**
(Jasper, 2026-10-21: "the first setup also used an overhead camera, and moving
away from that design change"). Gen 1 used one fixed ceiling camera looking
straight down (USB board in `camera_case_overhead`, YOLO-World detection,
pixel-to-floor map: linear for a straight-down camera, 4-point homography for a
tilted one). Gen 2 uses only the XIAO ESP32-S3 Sense in the claw's camera bay
(D32), which guides the grasp and reads the floor board for calibration.
Reasons as presented (from the gen-2 review R7, wording to be confirmed by
Jasper): the ceiling camera is one more device to mount, wire and calibrate in
every room; the claw and cables hide the grasp spot from above; its floor map
assumes a flat floor. Cost accepted: the claw camera sees less of the room at
once, so the robot scans by moving. R7's "keep both cameras" recommendation is
not adopted. Gen-1 camera parts and code stay in the repo as history.

D34. **Electrical housing carries both cable patterns ("_34")** (Jasper, 10/21: "add a hole configuration on it meant
for 3 motors, so based on function you can choose"; lead layout).
- **Four-station mode:** the four corner holes, unchanged.
- **Three-station mode:** three new Ø2 teardrop holes, 42 mm up the wall, 120° apart:
  - C on the camera-bay side, above the bay (bay top y 26.9, cover 29.3);
  - A and B on the side walls, on the side away from the bay.
  - Each outer mouth has a 0.5 mm chamfer and a debossed letter. At yaw 0 each hole points at its station.
- **Spec:** cad/GRIPPER_1021_SPEC.md §5 and the lead decisions in §5.1.
- **Verification:**
  - built and checked by the implementer, then independently verified PASS (11/11 items, 70 tests);
  - no cable line intersects the claw: minimum 0.23 mm, a graze along the rim for very steep lines, accepted;
  - the bay and cover clear by 12.7 mm.
  - Reports: verification/gripper1021_housing_34_build_notes.md, gripper1021_housing_34_verification.md.
- **Exports:** exports/step|stl/gripper1021_housing_cambay_34. The previous 4-hole export is kept. The cover is unchanged.
- **Software (open):** three-station configs must list the new outer-mouth points:
  - C (0, +0.0450, +0.0342), A (−0.0450, −0.0260, +0.0342), B (+0.0450, −0.0260, +0.0342) m, body frame;
  - the start yaw stays "camera bay toward station C".

D35. **Room map: the user draws the obstacles first, the robot models the room later** (Jasper, 10/21: "in the app
can you have it to where you can drag and drop squares, rectangles and circles and then input height and diameter or
LxW? ... I say we start with this and then the robot builds its own model of the room").
- **Now:** a Map tab in the phone app. The user drags squares, rectangles and circles onto a top view of the room and
  gives each its size and height (a bottom height for things that hang, like a fan). The planner keeps every cable line
  and the claw body out of each shape, plus a 0.10 m margin. Exact segment tests replace the 24-point sampling, which a
  thin pole could slip between. A "Where can it pick?" overlay shows the floor the claw can reach.
- **Later:** the claw camera builds a 2.5D height map from scans at known poses, and its detections appear as proposed
  shapes the user accepts. A phone room scan can be imported the same way.
- **Why this order:** a drawn map works tonight's way (one room, a few big objects) and shows the user exactly what the
  robot avoids. The camera looks down, so it cannot see tall furniture tops or a fan above the claw: those stay user-drawn
  even after phase 2. A static map never detects people or pets, so "nobody under the robot" stays.
- **Spec:** `docs/ROOM_MAP_SPEC.md`. Not built yet. It goes to an implementer after the phone-app verification finishes,
  because it edits the same files.

D36. **Claw tube as built: 10.48 in (266.2 mm)** (Jasper, 10/22: "the new pipe length is 10.48 in"). D32's 1021
assembly has the full 12 in tube (304.8 mm); the built one is 38.6 mm shorter, so the head (gear housing, arms,
hands) sits 38.6 mm closer to the electronics box. (D28's 254.8 mm cut was for the v7 head and is history.)
- **Config:** `claw.lowest_point_body_m` z = −0.4854 m in `robot.three34.example.json` and `robot.sim3_34.json`
  (closed fingertips: −0.5240 in the 12 in CAD + 0.0386). The old −0.5173 would have been 32 mm off, past
  SELF_CHECK's ±3 cm floor-height check.
- **Rest the claw on CLOSED jaws at startup:** open, the four-bar lifts the tips about 42 mm.
- **Field check:** standing on closed jaws, the electronics box's bottom face is 477.6 mm (18.8 in) above the floor.
- **Still the v6 CAD value:** `com_body_m` (measure it).
- **Unchanged:** the camera, which sits in the box.
- **Not yet re-derived:** the corner-hole profiles (`robot.three.example.json`, four-station configs).
- Parameter: `cad/params.py` `GRIP1021_TUBE_LEN`.

D37. **Winch drivers at 1.5 A, superseding D30's 1.06 A** (Jasper, 10/22: "I actually got 1.5 amps to work on the
motors, so I think our strength is increased"). 1.5 A is the motor's rated current. How it was reached (the Vref reading,
whether VDD or the sense resistor changed) is **not yet recorded**; the calculation Sheet uses Vref 1.2 V on the R100
carrier, which gives 1.5 A. D29's 1.35 A and D30's 1.06 A entries stay as history.
- **Strength (calculated; calculation Sheet, `calculations/gen2_payload_limit.py`):**
  - running pull 33.6 N on an empty spool and 25.2 N on a full one (was 23.8 / 17.9);
  - design force 16.8 N (was 11.9), +41 %;
  - worst-point lift capacity 1.56 kg (was 1.10), with the same linear program: 0.2 m wall margin, claw up to 1.6 m,
    +2 m/s² included, worst tension per unit weight 1.101;
  - claw + battery + 1 lb test = 1.32 kg now fits; claw + battery + jeans = 1.76 kg is still 0.21 kg over (was 0.66);
  - the 0.4 m ceiling margin now holds the +2 m/s² case too (14.7 N against 16.8 N).
- **Heat (calculated; same two-node model):**
  - motor heat P = I²R = 4.05 W (was 2.0 W);
  - vented shell with the 0.019 in fin: 57.6 °C against the 60 °C PETG limit;
  - vented without the fin: 77.2 °C;
  - sealed with the fin: 66.3 °C, so **the shells must stay vented and the fin fitted**;
  - at 1.35 A the vented shell with the fin is 51.2 °C, with a 15.1 N design force.
- **Conditions:**
  1. Run a 90-minute hold test at 1.5 A with the shell closed as installed. Read the motor case and the A4988 chip or its
     heatsink (the A4988 holds full current even standing still; if it overheats it shuts its outputs off and the winch
     loses torque). If the motor case is above about 55 °C, or the driver heatsink is above about 70 °C (D29's rule),
     drop to 1.35 A.
  2. If VDD was raised to 5 V to reach Vref 1.2 V, the 3.3 V STEP, DIR and EN signals are below the A4988's logic-high
     threshold of 0.7 × VDD = 3.5 V. Re-check the boot-off bench test (a reset must not move the motor, and EN high
     must disable the driver) before the motor goes back on a loaded line.
  3. Software: `motion.max_tension_n` stays unset on the hardware configs until the pull test measures the real pull.
     The simulation configs keep 15.0 N.
- The deck v5 charts are re-exported at 1.5 A to `docs/presentation/deck_v5/fig/`; the 1.06 A charts stay in
  `docs/presentation/deck_v3/fig/` (decks v3 and v4).

D38. **Heat fin: 1/8 in (3.175 mm) aluminium is the design; the 0.019 in sheet is the prototype only** (Jasper, 10/22: "make
the CAD for a 1/8 in fin and then note that only prototype is using .019 in. For now as I already had extra material").
- **Why:** at 1.5 A (D37) the motor makes 4.05 W.
  - The 0.019 in sheet cannot carry that alone at any length: about 2 W at most for a 60 °C base.
  - A painted 1/8 in plate with the same outline carries all of it at 56 to 59 °C on its own, and about 45 °C with the vented
    shell (`calculations/fin_sizing_4w.md`).
- **Prototype stations** keep the 0.019 in fins that were cut from material already on hand.
- **CAD:** `cad/parts/heat_fin1021.py`. Jasper's 10/21 Heat_horn outline is extruded to 3.175 mm toward the motor (spec
  `cad/HEAT_FIN_1021_SPEC.md`).
- **Interface consequences** (from the 10/21 reference parts):
  - **The shell's fin slot must open about 1.2 mm on the motor side.** It is open from y −2.6 to +2.2; the 1/8 in fin
    occupies y −3.175 to 0.
  - The motor sits 1.175 mm further back than in the CAD (shaft engagement in the spool 13.8 mm; check the set screw lands on
    the flat). Motor screws: **M3 × 12** (3.8 mm of thread).
  - **Prototype stations (0.019 in)** put the motor 1.5 mm further forward than the CAD. The shaft end (y 23.52) then reaches
    the v2 magnet cap's peg (from y 22.6), so prototype stations need the **short-peg cap** (peg 1.9 mm,
    `encoder1021_magnet_cap_v2_peg1p9`).
- **Simulation:** the ANSYS study with the motor screws and the heat-set inserts is
  `docs/simulation/ANSYS_THERMAL_MOTOR_SCREWS.md` (Study D). The insert locations are still to be confirmed by Jasper.

D39. **The motor's holding torque is the lifting chain's fuse** (Jasper, 10/22: "the goal is to make the torque of the motor
the smallest force that gives first, so slipping of motors happens before damage to the system, which the encoder can then pick
up and report an overload").
- **Rule (lead, proposed numbers):** every other part from the claw to the stud must give at no less than 1.5 times the most
  the motor can pull before it skips: 59.4 N at the cable (0.36 N·m at 1.5 A × 40/36 motor sensitivity, empty 7.5 mm core,
  fully fleeted cable). Torque links (the spool on the shaft) are rated against the motor's 0.40 N·m. Printed PETG near the
  motor is rated warm (× 0.85 with the 1/8 in fin).
- **Detection:** the AS5600 is on the spool, so a motor skip and a spool slipping on the shaft both raise the station's
  TRACKING fault. One skip is 82 counts; the hardware tolerance must be set below that (60 proposed).
- **Result as drawn** (`calculations/lift_chain_weakest_link.md`, independently checked): the set screw in its printed thread
  may slip first, and the 5 mm tab's sharp back corner is 1.17 times the motor. Everything else passes.
- **Proposed changes, not yet approved:** spool set screw into metal plus a bench pull test; a 6 mm tab with fillets on both
  roots; wall screws into the stud only; 3 dead wraps; hardware tracking tolerance 60 counts; the host reports a payout-side
  tracking fault as an overload.

D40. **Winch: 3:1 spur reduction** (Jasper, 10/23: "lets go with spur gears", after proposing 3:1 bevel gears; the lead advised
a parallel-axis stage: bevels need their cone apexes held to about 0.1 mm, push both shafts axially, and print poorly).
- **Drive train** (`cad/WINCH_GEAR3_SPEC.md`): purchased steel M1 20T pinion (Ø5 bore, set screw on the D-flat) on the
  NEMA 17; printed PETG 60T gear made in one piece with the spool (Ø15 × 16 mm drum, Ø36 flange, as Spoolv3); the spool on its
  own Ø7 × 55 steel shaft in two 687 bearings, 40.20 mm directly below the motor axis (40.00 + 0.20 backlash allowance). The
  encoder magnet moves to a cap on the spool shaft's far end. Jasper redesigns the slide-in (tab extended down to the near
  bearing, a far cheek, the cable hole and switch lug under the drum) and the shell in SolidWorks.
- **Why:** lift capacity 1.10 to 1.56 kg (full-step vector to rated torque; -27 % to +4 % on 1.50 kg) rises to 1.98 to 2.80 kg at 1.0 A
  (+32 % to +87 %; `calculations/winch_gear3.md`, revised after `verification/winch_gear3_calc_check.md`); motor heat falls
  from 4.05 W to 1.8 W; the printed set-screw joint that may slip before the motor goes away; the cable load leaves the motor
  shaft (its bearing now sees only the gear mesh).
- **Motor configuration (lead's recommendation; Jasper to confirm the current):** 1.0 A, Vref 0.80 V on the R100 carriers
  (within the 3.3 V logic range, no VDD change); `drive.full_steps_per_rev` 600 (200 motor steps × 3); hardware
  `faults.tracking_tol_counts` 60 (revised from 20 after the check: counts are at the spool, so 60 is the same 0.69 mm of line
  as direct drive; a continuous slip trips it within 3 skips, 0.94 mm, 19 ms; 60 is about 2 x the error budget); `drive.max_step_rate_hz` about 800 (50 mm/s
  needs about 640 at the empty core); `drive.step_sign` flips (the spur pair turns the spool opposite to the motor; holds while the cable
  still leaves the drum on the room side; or swap one coil pair; the first bench move confirms it) and `encoder.sign` is measured again on the bench (the magnet moves to the spool shaft's far end). Configs change
  only when the gearbox is installed.
- **Consequence for D39:** the most the motor can pull before it slips rises from 59 N to about 130 N at the cable (1.0 A,
  40 N·cm motor, fleeted cable, back-driven through the stage), so the new station is sized for about 200 N (1.5 ×). Bearing seats (Jasper): 130 N near, 160 N far radial, 87 N axial.
  Pinion: steel (not sintered or brass), two set screws or retaining compound (one set screw at low friction is marginal; a
  pinion slip is still caught by the spool encoder). Three dead wraps stay on the drum.

D41. **Winch gears 18T/54T** (Jasper, 10/23: "can we make the radius of both gears just a little smaller"). Supersedes the tooth
counts in D40; everything else in D40 stands.
- **Pair:** steel M1 18T pinion (tip Ø20, was 20T Ø22) and printed 54T gear (tip Ø56, was 60T Ø62): about 10 % smaller, ratio
  still 3.00, same module and pinion family, the smallest step that keeps both (19T/57T is 5 % but an odd pinion is harder to buy;
  module 0.8 would be 20 % smaller but drops the tooth contact below 1.5 x). Centre distance 36.00 + 0.20 = **36.20**; spool axis
  z −33.56 (4 mm higher). 18 teeth is above the 17-tooth undercut limit at 20°.
- **Margins (lead estimate, scaled from `calculations/winch_gear3.md`, to be rerun):** printed teeth 2.65 → about 2.3, tooth contact
  2.21 → about 1.8, both still above 1.5; the set screw and the motor-side numbers do not change (same motor torque).
- **Geometry rules:** windows Ø10 on R 17.5 (rim 3.25 under the root as before; inner edge 2.5 mm outside the full-spool line).
  Gear tip to pinion hub is 1.2 mm radial (criterion relaxed from 1.5 to 1.0: the hub ends at the gear's face plane).
- Files renamed by tooth count (`winch_gear3_spool_gear54`, `winch_gear3_pinion18`); the 20T/60T exports are removed.

D42. **Winch pinion printed in PETG** (Jasper, 10/23: "I'm printing it", after the lead's note that the pinion was specified as
bought steel). Supersedes the purchased steel pinion of D40/D41; the 54T gear and everything else stand.
- **Pinion (`pinion18`, printed):** 18T m1, face 10 (y 10.825 to 20.825), tooth thinning 0.10 like the gear; the hub Ø14 now
  runs back through the slide-in tab's Ø22.4 motor hole and the fin's 7/8 in hole to y −0.675 (0.5 mm clear of the motor's pilot
  boss), 11.5 mm long. Bore: Jasper's proven printed D-bore on this shaft (Ø5.30 round, flat 2.15 from the axis, the 10/21 spool
  values `ENC1021_BORE_*`). Set screw: M3 cup point onto the D-flat through a short M3 heat-set insert (4 mm long, pocket Ø4.0 x
  4.5 deep, radial from +z) at y 7.9, the middle of the exposed hub, so a key reaches it from above. Prints teeth-end down, hub up.
- **Centre distance:** printed against printed uses the claw gears' +0.30 allowance: 36.00 + 0.30 = **36.30**, spool axis
  z −33.66 (0.1 mm lower than revision B).
- **Why it is acceptable (lead estimate, to be rerun):** printed 18T teeth about 1.7 x the motor's slip force (the pinion is now the
  weakest tooth, above 1.5); the set screw in a metal insert holds 0.40 to 0.88 N·m against the motor's 0.27 (1.5 to 3.3 x, the
  weakest-link study's metal-insert model); a pinion slip is still caught by the spool encoder (TRACKING fault), and the D-flat
  takes over after the bore clearance closes. Tooth contact improves (PETG on PETG is softer). Backlash grows to about 0.42 mm at
  the pitch circle (about 10 encoder counts, inside the 60-count tolerance).
- **Interface for Jasper:** keep the tab's motor hole at Ø22.4 (at least Ø16) so the pinion hub passes through it.


D43. **Winch encoder magnet on the spool shaft is the measured Ø4.0 magnet** (Jasper, 10/26: "the magnet is much smaller than
originally thought"). Supersedes the Ø6 × 2.5 magnet written into `cad/WINCH_GEAR3_SPEC.md` for `magnet_cap_w3`. That spec
assumed Ø6 although Jasper had measured Ø4.0 on 10/22 (`ENC1021_MAGNET_D`).
- **Geometry:** `WG3_MAGNET_D = ENC1021_MAGNET_D` (4.0), one definition. The pocket becomes Ø4.3 × 2.5 with the same three
  crush ribs (0.15 per side + 0.12 crush). Unchanged: the cap's Ø12 outside, the Ø7 bore and web, every axial position,
  and the chip face 1.5 mm from the magnet face.
- **Open:** the magnet's thickness is still assumed to be 2.5 mm. If it is thinner, its face sits below the cap face and the
  air gap grows. The AS5600 still reads up to about 3 mm; check the `magnet DETECTED` / AGC line in the bench test.

D44. **The robot scans its own workspace into a stored, updating height map** (Jasper, 10/26: "using the vision to actually
create a real-time model that's stored and edited to update, so that the robot knows the sandbox it's playing in"; "yes
write the spec and start with the map tab"). This is the "later" half of D35, specified in `docs/ROOM_SCAN_SPEC.md`.
- **How it builds the map:** plane-sweep stereo from the claw camera at **known** poses (the cable model plus the floor
  board, no SLAM). The result is a 2.5D height map, a photo mosaic, proposed shapes in the Map tab, and partial re-scans
  with change detection. A 3D mesh export (COLMAP) is optional.
- **Safety rule:** a scan only adds keep-out. Taller or new objects apply at once; anything that would free space waits for
  the user to accept it. Unknown cells count as obstacles.
- **Order:** the Map tab (D35 "now", `docs/ROOM_MAP_SPEC.md` §1 to 5) is built first, then phases S1 to S5. Each phase is
  independently verified.
