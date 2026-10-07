> User update,4October2026: housing prototype is now first priority; room survey deferred until installation. Possible supported two-motor planar test, then four-station installed pickup. Jeans are the working payload;5lb (2.26796185kg) is reserve capacity to investigate, not an achieved safety factor; no demonstrated capacity. Combined station power/data is preferred; protocol/connector remain open. Q1 demonstration/mass and Q2 cabling preference below have been answered; supply/driver identity remains open. Earlier0.9kg target and survey-first order below are superseded by this update.

# RoomCleaner: research, design skeleton and methodical gap closure

**Working revision: 4 October 2026.** This document defines the current system before further detailed CAD. It covers currently identified interfaces and gaps; new observations can add parameters rather than being forced into an unsuitable existing assumption. It is a research and resolution plan, not a complete-station print release. Existing reviewed bench exports remain unchanged. No purchase or physical measurement is inferred from a selected component or a passed simulation.

The working ledger contains **57 parameter groups and 282 named fields**, including known nominal dimensions and unresolved calibration/qualification fields. These are not 282 independent mysteries: repeated mechanical/control views are linked by group IDs. The ledger is `design_resolution/unknown_parameters.json`; its readable index is [parameter_register.md](design_resolution/parameter_register.md). Detailed alternatives, provenance, tests and affected geometry are in [the mechanical audit](UNKNOWN_MECHANICAL_AUDIT_20261004.md) and [the controls audit](UNKNOWN_CONTROL_AUDIT_20261004.md).

## 1. What is already decided

| Requirement / selected direction | Current interpretation |
|---|---|
| Four removable wall winches | Stud-mounted support dock, slide-in case and positive anti-lift retention. One common station design is preferred; actual corner orientation may require an indexed/reversible outlet interface. |
| Encoders on all four winches | Spool magnet + AS5600, continuous turn tracking and command comparison. This detects rotation error; it does not establish rope payout, tension or successful pickup. |
| Bead-triggered homing | Structural metal guide carries cable force; a separate sliding annular collar actuates a secured stationary KW12 switch. Springs return the collar. Actual trigger lengths remain unset. |
| Gripper | Two-jaw servo clamp first, yellow TPU95A contact pads. Flexible fingers are deferred. |
| Extended assembly | Printed150mm extension, servo/clamp below; battery, camera/controller and IMU above; removable lid and retained electronics. Nominal cable-plane-to-pad reach268mm requires measurement. |
| Cable attachments | Four spaced attachment points retained for this skeleton. No deliberate orientation maneuvers. Near-level operation is an acceptance requirement requiring validation, not an achieved guarantee. |
| Camera | Upper offset XIAO ESP32-S3 Sense camera, local computer processes images. Start with settled calibrated viewpoints; keep ceiling/bench camera only as an independent development reference. |
| Success evidence | Close clamp → partial transfer → camera confirms payload moved relative to scene → continue. Retry or retain uncertain status if evidence fails. Delivered count increments only after camera-confirmed deposit and retreat. |
| Fasteners/manufacture | M3 preferred; small encoder/horn/keeper interfaces can require documented M2 exceptions. PETG structure and TPU pads; K1/K1Max actual profiles and fit coupons govern final tolerances. |
| Power product goal | Self-contained station with one retained low-voltage external plug. Exact control transport remains open; a power-only plug and a combined power/data plug are separate candidate architectures. No mains inside printed case. |

Payload0.9kg is the existing dry-laundry design target, not a verified capacity. The old0.45kg effector mass and40N cable limit are assumptions, not measurements of this longer assembly. No unrestricted room workspace, structural rating, battery runtime or delivery success rate is closed.

## 2. Rules for filling a blank

Fifteen already-known motor, spring, clamp and encoder facts are recorded as separate reference values with provenance. They do not fill an actual measurement or authorize motion.

Every parameter records units, provenance, current nominal/default, actual resolved or measured value, uncertainty, hardware/process revision and evidence. An unknown stays `null`, never zero. Structured measured vectors/matrices have declared shape/frame records for the principal geometry. Duplicate anchor/mass/extrinsic views have canonical aliases; they cannot be independently calibrated to conflicting facts. A supplier drawing can close a nominal purchased-part interface; it cannot close its printed fit, electrical performance or structural capacity.

P01 controls explicit acceptance/error-budget targets. Package milestones do not automatically close entire parameter groups; full closure requires a structured independent review, resolved applicable fields and declared dependency evidence. The checker rejects null closure records, empty measurement metadata and negative uncertainty even under optimized Python. It checks evidence references, not the truth of a physical test.

The resolution sequence for one group is:

1. State the quantity and what consumes it.
2. Gather the current evidence and identify the limiting requirement.
3. Compare plausible solutions and select one for development.
4. Calculate its interfaces and failure margins.
5. Implement only its bounded part/code change.
6. Verify independently, including relevant negative cases.
7. Record actual evidence; close only the claims the evidence supports.
8. Update every dependent drawing, configuration, test and order entry.

The ledger keeps **solution status separate from closure status**. A design may be selected or implemented while its physical tests remain open. If the chosen solution fails, retain that failure and revise the solution; do not enlarge tolerances simply to obtain a pass.

## 3. System skeleton and interface contracts

| Module | Inputs / outputs | Parameters to close | Design boundary |
|---|---|---|---|
| Wall dock / structural adapter | Stud reactions; station retention and service motion | M17–M22,M35,M36 | Metal screw seats bypass finish/plastic preload where required; case cannot lift out without releasing positive lock. |
| Motor / spool / encoder module | Steps/current → shaft angle → measured spool angle → calibrated cable payout | M11–M15,C04–C07 | Motor face and axis datums govern hub/cup/PCB alignment. Encoder calibration and rope calibration remain separate. |
| Outlet / homing module | Incoming winding corridor; outgoing working directions; bead force → switch | M01–M10,M18,C03 | Stationary structural guide and load bracket; moving collar only actuates switch. Working and homing angle envelopes are different contracts. |
| Station electronics / harness | Protected DC power; local motion/diagnostics; external interface | M29–M33,E01,E02,C08,C09 | Components and wires both have retained, serviceable envelopes. Local fault behavior must fit the global stop policy. |
| Upper effector assembly | Four cable forces; battery/camera/IMU support; lower frame attachment | M16,M23,M24,M28–M34,C01,C02,C12,E03 | Actual attachment points, COM and full-body volume enter statics/collision calculations. |
| Lower clamp | Servo angle/current → gear/rack stroke → garment retention | M25–M28 | Real horn stack, stops, gear/rail clearances and TPU friction must be demonstrated with representative cloth. |
| Motion supervisor | Pose/route requests → feasible cable lengths/tensions → synchronized segments | C01–C12 | Refuses undefined calibration, impossible attitude/tension, stale epochs or unhealthy axes. Four local MOVE commands are not coordinated execution. |
| Vision / mission supervisor | Timestamped images and camera pose → target/evidence → action state | V01–V04 | Rejects uncertain camera pose/depth and ambiguous pickup/release; camera-only scene motion cannot prove a carried payload. |
| Release and inventory | One configuration revision → exact prints, fasteners, purchases and tests | O01,M35,M36 | Selection, reported order, verified receipt and qualification are separate states. |

### Coordinate and datum skeleton

World frame W: floor corner origin, metres, +Z upward. Physical anchors `a_i` are the **metal outlet throats**, not ideal room corners. Body frame B: upper cable-plane reference; four attachment vectors `b_i` and COM `c_B`. Camera frame C: calibrated optical axis/frame. Station frame S: mm, existing CAD +Y upward/+Z roomward. Define a measured transform `T_WS` for each mount and `T_BC` for the assembled camera; retain consistent A/B/C/D cable ordering.

Mechanical station datums: A motor shaft axis; B motor front face; C structural base back plane; D outlet throat; E actual wall/dock contact. Fastener axes, guide axes, chip center and service direction refer to these datums. A changed outlet location changes its wall moment and must trigger a structural recalculation.

Finite attachment lengths are `L_i = ||a_i - (p + R b_i)||`. For statics, use cable force and moment simultaneously: `sum(T_i u_i) + F_external = 0` and `sum((R b_i) × T_i u_i) + M_external = 0`. The point-effector model remains a development baseline; it is not the current complete-body model.

## 4. First research findings and solutions to develop

### 4.1 Architecture profiles: resolve mixing before geometry

**Resolved at the documentation level:** keep three named profiles: central Uno pulse executor; detached local XIAO-C3/DRV8825 station; extended XIAO-S3 Sense claw. Their pin maps, drivers and tests do not merge automatically. The selected claw uses servoGPIO1 and IMU SDA5/SCL6; historical ESP32 servo13/IMU21,22 applies only to the old board profile. The current local station is single-axis bench only.

Further research compares these control options:

| Option | Benefits | Cost / unresolved interfaces | Recommendation |
|---|---|---|---|
| Central coordinated pulse executor, drivers local | Shared timing already exists; preserves much existing software | Reliable distributed STEP/DIR/home/fault transport and a larger external connector/harness need design | Keep as reference implementation and synchronization benchmark. |
| Local buffered segments over wired CAN/TWAI | Local encoder/fault loops, explicit segment IDs and scheduled starts; can combine power/data in one plug | Adds transceivers, connector contacts, termination/cable topology, controller pin/boot analysis and coordinated software | Research as a product candidate; not selected or implemented yet. ESP32-C3 needs an external transceiver. |
| Local buffered segments over WiFi, power-only plug | Matches one power cable per station; no added data cable | Clock uncertainty, radio outages, global fault propagation and partial-start prevention need measured guarantees | Candidate only after a jitter/clock/fault experiment; sequential WiFi MOVE requests are rejected as a design. |

A wired option can still have one plug, but it would be power **and data**, so the current two-contact Micro-Fit input would change. Current XIAO-C3 spare GPIOs include boot-strapping/UART functions: no CAN/interlock assignment is frozen without startup analysis. Firmware package compatibility and real timing matter more than nominal link bitrate.

### 4.2 Level equilibrium: a real architecture gap

The current four-point layout does not guarantee a level claw everywhere. This can be shown without assuming encoder error. For equal-height4×3m rectangular anchors, level/yaw-zero body attachments at X±69/Y±64mm, and purely vertical gravity, force balance imposes these necessary COM shifts for roll/pitch moment balance:

`c_x = 0.069 (p_x - 2)/(2 - 0.069)` and `c_y = 0.064 (p_y - 1.5)/(1.5 - 0.064)` metres.

At room center the required shifts are zero. At `(1,1)m`, they are approximately **−35.7mm and−22.3mm**. A fixed centered COM cannot meet that level static pose simply by improving encoder accuracy. Actual wall heights, yaw, COM and passive tilt change the result; this is a diagnostic for the ideal geometry, not a numerical prediction of actual tilt. Matching these shifts is necessary under the stated assumptions; full yaw moment balance, positive cable tensions and stability also require verification.

| Attitude solution | Benefits | Tradeoff / remaining work |
|---|---|---|
| Retain four points and validate near-level subset | Closest to the current assembly and first prototype | Full-body equilibrium and measured tilt/settling define where pickup is permitted; cannot promise room-wide level. |
| Passive leveling joint between suspension platform and lower clamp | Gravity can keep the lower clamp upright while upper platform tilts | New joint, load path, stops, COM design, cable/servo wire routing and camera-to-grip transform; upper camera still needs measured pose. |
| Common cable apex with low hanging COM | Reduces suspension-induced pitch/roll moments at the common point | Changes selected attachment architecture; weaker yaw constraint, swing and apex/termination load tests; does not guarantee exact level dynamically. |
| Additional actuation/cables | Can address pose constraints intentionally | Scope/cost/complexity increase, incompatible with assuming current four motors solve6DOF. |

**Current development recommendation:** retain four points, model passive attitude and permit pickup only when measured near-level conditions are satisfied. Do not claim this meets whole-room level operation until the resulting workspace is known. If that workspace is too small, choose a mechanical leveling solution before printing a final claw. An IMU is an observation/gate, not a source of leveling torque.

### 4.3 Outlet direction and size: derive it instead of guessing

The ideal downward/inward corner orthant requires54.7356° around its diagonal bisector. The55° experiment has only0.2644° margin. A **60° outgoing design study** gives5.2644° ideal angular margin; this is a development target, not a surveyed installation tolerance or a passed geometry result.

A wider angle needs a larger mouth. At the current collar's6.75mm rear setback, the conservative throat-edge cable envelope gives `D >= 2(2.55 + s tan(alpha) + 0.3/cos(alpha))` mm, before printer/assembly tolerances. For the same hypothetical edge-started0.6mm oblique cable tube used in this screening, at55° this is25.43mm; at60° it is29.68mm. The exact physically admissible throat centerline and rounded-metal contact path must still be established; this benchmark is not a universal minimum-bore formula. The current26mm bore therefore cannot simply be relabeled60°. Its28mm stopper and clamp/guide/fork geometry must change too.

The rear incoming corridor is separate: actual sampled directions reach63.626°. A65° rear opening is48.59mm diameter10mm behind the throat; a70° study opening is60.65mm. These are geometric cone opening diameters, not a proof that a finite oblique cable tube clears the entire ring/enclosure. Extra tolerance can increase enclosure size markedly. Winding tangency, ring contact and incoming/outgoing swept lines remain unverified physically.

| Outlet concept | Assessment |
|---|---|
| Wider fixed canted ring/collar plus separate load bracket/front service enclosure | Recommended first detailed study. Few moving parts; requires full clamp seats, secured switch cradle and coherent base/cover. It may need two indexed outlet orientations to preserve common major housings. |
| Articulating cartridge | The earlier pivot-at-throat concept is rejected because its rear carrier obstructs the fixed-spool cable. Reopening articulation requires a substantially different pivot/rope/load path. |
| Broad-angle fairlead with separate homing detector | Potentially separates room clearance from bead-button geometry; extra sensor/actuator interface and bead handling need definition. Contingency if a broad-angle collar cannot home reliably. |

The ring carries guide reaction `G = T_in u_in + T_out u_out`; unequal tensions are possible during sliding friction. The earlier equal-T formula is a special case. Whole-station external wall force does not add spool and guide internal reactions twice. Actual friction and terminated line wear need representative tests, especially during repeated running.

### 4.4 Homing: define where and how it is valid

**Selected procedure for initial commissioning:** detached individual switch homing; measured payout; attach the claw in a supported measured setup pose; independently verify all cable lengths before suspension. Existing trigger-length and setup-pose placeholders stay unset. This is already represented in `hw_config.py`; it must remain explicit in the new local architecture.

For a collar with2mm stroke, ideal bead travel is `2/cos(beta)` mm. The selected spring pair alone reaches6.045N at full stroke; ideal line force before switch/guide/ring friction is `6.045/cos(beta)` N. At55° this becomes3.49mm travel and10.54N. Side loading can cause guide binding, so these are lower-bound projections, not an acceptance test.

Develop a **separate restricted homing cone** and rounded removable stopper. Compare spherical/rounded shapes with the current flat-cylinder bead; a nominal diameter greater than the bore does not demonstrate oblique contact, retained bead position, effective switch travel or reset. Measure actual KW12 lever force, trip/release and overtravel before selecting spring changes. Use an adjustable secured cradle and independent hard stops; do not use coil bind as a stop.

Automatic homing of an assembled freely suspended robot is not part of the current procedure. If later required, it needs a compatible common pose, calibrated per-cable bead positions, positive tension and coordinated approach—not four independently retracted cables.

### 4.5 Encoder alignment: separate fit from measurement accuracy

The old radial floats0.20mm cup +0.15mm magnet +0.10mm board can add to0.45mm before printer/runout error. The AS5600 data sheet gives a0.25mm displacement condition for a6mm reference magnet and typical gap0.5–3mm dependent on magnet/field. This is not a blanket tolerance for every magnet.

**Recommended fix:** center and retain the magnet/cup with a measured fixture, then align the removable adjustable PCB pedestal. Measure assembled eccentricity, face gap and energized360° AGC/magnitude/status under representative shaft load. Add a precision locating insert if printed locating faces cannot achieve the requirement. Tightening every printed hole is not a substitute for a measured alignment stack. The existing encoder algorithm can be bench tested while this mechanical alignment remains open.

### 4.6 Fuse and wiring: body fit is insufficient

The current vertical fuse holder ends atZ66.63mm below aZ70.9mm roof: only4.27mm bare-body clearance. Its14AWG bend has no qualified route. The next design compares: (A) horizontal holder with measured lead sweeps, (B) separate service pocket on the enclosure, and (C) compact exact DC-compatible holder. Prefer a service pocket if it preserves short protected leads and avoids electrical/mechanical intrusion; reject options lacking connector/lead/strain-relief envelopes.

Select fuse **series, DC voltage, interrupt rating and current curve** after measured input current, inrush and source/wire/connector coordination. Driver phase current is not station input current. Source-side protection also covers the external cable. External5V/USB isolation, reverse-polarity behavior and transient limits are explicit interfaces, not solved by a keyed plug.

### 4.7 Moving-camera evidence: define the observation frame

The current fixed-camera verifier cannot be reused unchanged after moving the camera. Develop calibrated settled viewpoints first: real intrinsics/distortion, assembled camera transform, observed image-specific pose from surveyed references, and a known floor/hamper plane. `solvePnP` is a suitable researched pose-estimation building block; it does not itself solve occlusion, depth ambiguity or robot-camera timestamp association.

Pickup verification must compare cloth and background/world motion, not simply detect changed pixels after the camera moved. Release confirmation requires the cloth remaining in the receiving area after retreat. Test empty grabs, cloth occlusion, camera-only motion, wrong cloth identity and failed releases as negative cases. Stream and inference performance are independent of success-evidence accuracy.

## 5. Methodical work order

| Package | Work | Closure depends on |
|---|---|---|
| W01 | Profiles, scope, datums, homing/attitude policy and inventory format | Existing decisions and source audit |
| W02 | Real room/component survey, mass/COM and preliminary finite-body loads | W01; supplied physical measurements |
| W03 | Outlet, stopper, guides, stationary switch and bracket/enclosure | W02; selected angle/force envelope |
| W04 | Shaft/hub/spool/payout/magnet/encoder and absolute length limits | W02; physical motor/line tests |
| W05 | Station/effector power, retained harness, service/fuse/thermal design | W01,W02; exact component/lead data |
| W06 | Dock/joints/material process/structural and creep verification | W03–W05; measured load/temperature envelope |
| W07 | Real-board motion timing, synchronization and global faults | W04,W05 |
| W08 | Extended clamp/horn/pads/joints and passive attitude tests | W02,W05 |
| W09 | Full-body/cloth/cable workspace, calibrated pose and collision limits | W06–W08 |
| W10 | Camera localization, frame age and pickup/delivery evidence | W08,W09 |
| W11 | Versioned order/print bundle and supported end-to-end commissioning | W06,W07,W09,W10 |

These are staged contribution milestones, not claims that each package fully closes every group it touches. Profile/transport decisions mature inW01; homing calibration, sensor behavior and electrical tests close later with their actual dependencies. Station mechanism and power/thermal evidence iterate jointly. Independent tasks can be researched in parallel; closure requires the complete referenced evidence, including the explicit acceptance-budget groupP01. P01 records position/attitude/payout/vision accuracy, timing-motion allocation, stop distance, visibility, runtime/duty and trial-count targets. Use conservative summed error allocations unless a statistical model is substantiated. For example, motion error from timestamp uncertainty is at least bounded by speed times age; it is separate from camera/calibration error.

Load-model design precedes structural tests; measured structural/timing results then constrain final workspace validation. Do not use a supposed whole-room workspace to justify the same structural assumptions it depends on.

## 6. What can be filled now versus later

**Filled now:** module boundaries, datum convention, separate firmware profiles, detached-homing procedure, success-evidence rules, parameter names/units, research alternatives, dependency order, preliminary angular/force/alignment screens and each closure test.

**Design work next:** choose the outlet angle/installation uncertainty budget from a bounded workspace; design the widened collar, full head seats, secured adjustable switch cradle and load bracket/front enclosure together. In parallel, compare the fuse service pocket/harness route. Detailed CAD begins only when its required envelope and load inputs are explicitly bounded.

**Measured inputs still needed:** room throat coordinates/orientations and wall stack; line diameter/payout; actual KW12 lever trip/force; motor thread/shaft checks; real servo horn stack; battery/connector dimensions; assembled mass/COM; exact fastener and connector stock. The [measurement worksheet](design_resolution/measurement_worksheet.md) captures these without asking for repeated generic 'volume' measurements.

**Tests still needed:** current/torque/thermal limits, line/bead/termination retention, encoder field/runout, printed joints/creep, local firmware compilation and real pulse/fault timing, coordinated stop/recovery, passive attitude/workspace, and moving-camera negative cases. No research source can substitute for these measurements of the actual assembly.

## 7. Research sources and evidence limits

- [Espressif ESP32-C3 TWAI documentation](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-reference/peripherals/twai.html): external transceiver and bus/error handling. Research candidate only; no final controller/connector pinout or protocol implementation selected.
- [AS5600 manufacturer data sheet hosted by Seeed](https://files.seeedstudio.com/wiki/Grove-12-bit-Magnetic-Rotary-Position-Sensor-AS5600/res/Magnetic%20Rotary%20Position%20Sensor%20AS5600%20Datasheet.pdf): gap/field/centering conditions and register interpretation. Actual magnet/PCB and manufacturing stack still require testing.
- [Ronstan RF8090-05](https://www.ronstan.com/us/ropeglide-ring15mm-x-5mm-x-7mmblack-1.html): rope-guide component selection. Supplier ring load data does not rate its printed capture or thin braid abrasion.
- [Pololu DRV8825](https://www.pololu.com/product/2133) and [D24V10F5](https://www.pololu.com/product/2831): driver, regulator and current/transient interfaces. Open-air figures do not establish enclosed capacity.
- [Seeed XIAO ESP32-C3](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/): external power/USB isolation and pins. Actual selected board build/profile must be compiled and tested.
- [OpenCV PnP](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html): calibrated correspondences and camera-pose estimation; not a ready-made moving-camera mission pipeline.
- Exact mechanical spring/guide/fastener sources and process limitations: [MOUNT_INTERFACE_CONTROL_20261002.md](MOUNT_INTERFACE_CONTROL_20261002.md) and [FRESH_STRUCTURAL_REVIEW_20261002.md](FRESH_STRUCTURAL_REVIEW_20261002.md).

Sources checked4October2026. No live pricing or new procurement is required to establish this skeleton. Reproduce numeric screens with `python calculations/design_skeleton_screening.py`; check and render the closure ledger with `python tools/design_resolution.py --render`. The ledger checker validates IDs, unit labels, source paths, staged coverage and closure-record guards; it cannot verify the physical truth of a cited test or arbitrary matrix/frame semantics. Independent engineering review establishes evidence quality. Numeric screening validates only the stated preliminary calculations, not a product rating.
