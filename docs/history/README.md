> **Upload scope:** This GitHub branch publishes the design index and current electrical notes. The full local CAD/export snapshot has NOT been uploaded: Git push lacked authentication. Some linked historical artifacts may only exist in the local archive. Local snapshot commits: 4cc14fe and ff2e92b. Do not treat this branch as a complete backup.

# RoomCleaner design history and roadmap

Index established 2026-10-14 following the user's 2026-10-12 request to preserve stages, designs and decision rationale for presentations. This is a retrospective index of available evidence, not a reconstruction of missing commits or physical test results.

## How to read the record

Version IDs below identify subsystem designs; they are not a single sequential whole-robot release. Preserve native names such as clamp V1, camera V2 and extended V3. Historical dates come from named records where available. Undated stages remain undated. A later proposal does not retroactively validate an earlier drawing.

Use these independent labels: **proposed**, **implemented in CAD/code**, **reported software/CAD check**, **physical test documented**, **superseded**, **deferred**. Purchases use **candidate**, **ordered/reported purchased**, **shipped**, **received verified**. Neither a checkmark nor an order is proof of receipt. Hardware performance needs a dated measured test record.

## Stage and design index

| ID | Design / stage | Reason or change | Evidence / limitation |
|---|---|---|---|
| SYS-SIM-01 | Initial cable robot simulator | Establish kinematics, perception interfaces and mission flow | [Original roadmap](../ROADMAP.md); simulation claims are not measured payload ratings |
| CLAW-TENTACLE-01 | Five tendon-driven TPU fingers | Gather soft cloth with a single servo | [Historical decisions](../../DECISIONS.md); deferred in favor of simple clamp |
| CLAW-CLAMP-V1 | Rack-and-pinion parallel clamp | Simplify first functional prototype | [Build](../CLAMP_V1_BUILD.md), [BOM](../BOM_CLAMP_V1.csv); CAD prototype, thin-cloth gap later identified |
| CLAW-CAMERA-V2 | Compact claw-mounted XIAO camera | Move perception with the gripper | [Build](../CLAW_CAMERA_V2_BUILD.md); historical compact version |
| CLAW-EXTENDED-V3 | Upper camera/electronics, lower servo/clamp | Improve view of grasp region and payload | [Build](../EXTENDED_CLAW_V3_BUILD.md); printed fork structure, physical qualification open |
| CLAW-SELF-CAD-A | User SolidWorks redesign, 2026-10-12 | Organize interfaces and identify flaws before further CAD | [Design brief](../CLAW_SELF_CAD_DESIGN_20261012.md); tube proposal and purchased dimensions not all frozen |
| CLAW-ELEC-A | Manual-charge claw circuit, 2026-10-12 | Separate servo and camera power; add FSR feedback | [Circuit](../CLAW_ELECTRICAL_REVA_20261012.md), [PDF](../../output/pdf/Claw_Electrical_RevA.pdf); proposed, not physically tested |
| CLAW-DOCK-B | Automatic hook/contact charging concept | Support parked claw and avoid manual plugging | [Concept](../CLAW_DOCK_CHARGING_REVB_CONCEPT.md); exact charger/protection still open |
| WINCH-OPEN-01 | Original motor/spool/guide | Initial cable drive | [CAD sources](../../cad/parts/); historical baseline |
| WINCH-HOME-01 | Bead-actuated homing casing | Repeatable cable reference | [Bench audit](../BENCH_PRINT_AUDIT.md); trigger lengths require measurement |
| WINCH-SPOOL-V2 | Magnet-ready spool | Support shaft angle feedback | [Decisions](../REVISION_V2_DECISIONS.md), [source](../../cad/parts/winch_spool_v2.py); positive retention and clearance reviews apply |
| WINCH-SLIDE-01 | Removable wall frame and positive lock | Bench assembly and removable servicing | [Build](../WINCH_SLIDE_MOUNT.md); gravity alone is not retention |
| WINCH-BENCH-20261002 | Reviewed restricted bench mount | Correct fastener, homing and mating defects | [Release](../FRESH_MOUNT_RELEASE_20261002.md); 40° outlet is not approved for full-room movement |
| WINCH-OUTLET-CANTED | Canted outlet exploration, 2026-10-04 | Improve directional line clearance | [Review](../CANTED_OUTLET_20261004.md); experimental alternative |
| WINCH-OUTLET-ARTICULATING | Articulating outlet exploration, 2026-10-04 | Increase angular accommodation | [Review](../ARTICULATING_OUTLET_20261004.md); not a replacement release |
| STATION-LOCAL-A | Local driver, regulator and ESP32 | Reduce long motor/control wiring | [Hardware](../LOCAL_STATION_HARDWARE_20261004.md); candidate parts and enclosure qualification open |
| STATION-FUSE-A | Revised fuse service packaging | Allow lead bends and removable servicing | [Build](../FUSE_SERVICE_PROTOTYPE_20261004.md); unpowered fit prototype |
| CONTROL-CENTRAL-01 | Arduino and central stepper drivers | Original synchronized pulse architecture | [Firmware](../FIRMWARE.md); preserve as separate architecture |
| CONTROL-FEEDBACK-01 | Encoder and tilt integration work | Detect rotation errors and gate settled pickup | [Commissioning](../ENCODER_AND_TILT_COMMISSIONING.md); shaft feedback does not prove payload movement |
| CONTROL-LOCAL-A | Experimental one-axis ESP32 controller | Local pulse generation and diagnostics | [Control](../LOCAL_STATION_CONTROL_20261004.md); reported portable tests, hardware adapter unverified; four-axis coordination incomplete |
| VISION-MOVING-A | Moving-camera geometry utility | Map detections using camera pose | [Review](../../verification/MOVING_CAMERA_GEOMETRY_20261004.md); synthetic checks do not establish physical calibration |
| SYSTEM-RESOLUTION-A | Unknowns and closure ledger | Track missing dimensions and evidence methodically | [Skeleton](../DESIGN_RESOLUTION_PLAN_20261004.md), [priorities](../PRIORITY_EXECUTION_20261004.md) |
| STATION-BRINGUP-A | Received-part identification and bench plan, 2026-10-14 | Begin assembling actual ESP32 motor stations | [Guide](../MOTOR_STATION_BRINGUP_20261014.md); user reports components shipped; actual board identities pending |

## Current roadmap and exit evidence

| Milestone | Next work | Exit evidence |
|---|---|---|
| M1: one unloaded station | Identify parts, verify rails, set driver current, jog and home | Photos, wiring revision, measured voltages/current/temperature, successful bounded switch tests |
| M2: repeatable local feedback | Align magnets and compare commanded/measured motion where encoders fitted | Rotation logs, diagnostics, direction agreement and fault tests |
| M3: restrained multi-axis bench | Commission network timing and recovery, then four motors with central one-pound test weight | Coordinated timing and stop evidence, mechanical retention/load tests; no assumption of full-room rating |
| M4: working claw | Freeze mechanism, camera, battery and harness; test FSR and cloth grip | Fit measurements, measured mass, video-verified grip and release, power/thermal logs |
| M5: installed room pickup | Survey anchors, establish allowed workspace/load envelope and perception calibration | End-to-end pickup and delivery video, error/retry behavior and cable/load evidence |
| M6: charging dock | Select complete charging electronics and test manually seated dock | Charge termination, cell balance, temperature, contact and fault tests before autonomous docking |

The five-pound goal is a reserve investigation, not a demonstrated load or automatically a safety factor. The one-pound bench milestone is a separate scope. Jeans pickup remains a practical use case requiring measured garment and claw mass.

## Version storage and presentation discipline

- The archive branch preserves all available nonignored project files and the explicitly included claw PDF. Earlier remote branches are retained independently; no automatic merge changes the default branch.
- [Snapshot manifest](snapshot_20261014.json) records paths, sizes and SHA-256 hashes. A hash verifies file identity, not engineering correctness. CAD sources and exports may represent different revisions; only a matching build record establishes reproducibility.
- [Decision register](decisions_20261014.md) gives the problem, choice, rationale and open tradeoffs. Do not present a proposal as a user-approved purchase.
- For every subsequent milestone, add a dated record using [the template](stage_template.md), commit source and deliverables together, and use a unique tag. Never move an existing milestone tag to newer files.
- Attach measurements, photos/video and failed test results to the relevant revision. Keep the previous design and explain why it changed.
- Native user SolidWorks revisions and unavailable chat attachments are not recreated by this snapshot. Add them when available; the archive does not claim to contain every historical intermediate design.
- Existing remote branches at inspection: `claude/magical-cerf-gqr7j7` at `fc0a03a3556c34a8fc3a12632e5da379c96bf192`; `claude/dual-mechanism-cad-design-3gp7zn` at `d071b366c83c960c7e3ca8d2b49aa21b78eec607`; `codex/verified-laundry-cycle` at `95f97cdde81a5629d4cd4659d318dff80d97b423`. These references preserve provenance, not a claim that all branches were reviewed or merged.
