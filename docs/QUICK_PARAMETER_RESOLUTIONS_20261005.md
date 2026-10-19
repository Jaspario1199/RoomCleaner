# Completed quick resolutions — 5 October 2026

This pass settles source-defined values and explicit development procedures. The 57 parent groups remain open until their acceptance evidence exists. These values do not certify printed fit, load capacity, or room operation.

## Checked source values

- [x] **Q01 — Extension length: 150 mm** (M23). Source: `cad/clamp_extended_v3.py`. CAD nominal; stiffness and joint tests remain open.
- [x] **Q02 — Gear module: 1.5 mm** (M26). Source: `cad/clamp_v1.py`. CAD nominal; printed gear fit remains open.
- [x] **Q03 — Gear backlash: 0.2 mm** (M26). Source: `cad/clamp_v1.py`. CAD nominal; actual backlash remains open.
- [x] **Q04 — Clamp design endpoints: [20, 140] deg** (M25). Source: `cad/clamp_v1.py`. CAD commanded angles; horn indexing and safe physical stops remain open.
- [x] **Q05 — Pad envelope: [5, 40, 36] mm** (M27). Source: `cad/clamp_v1.py`. CAD nominal; TPU grip and compression remain open.
- [x] **Q06 — Camera bracket tilt: 28 deg** (M34). Source: `cad/extended_camera_pod.py`. CAD rotation about local X is negative 28 degrees; optical extrinsics/FOV remain uncalibrated.
- [x] **Q07 — Local bench tracking error threshold: 64 encoder counts** (C07). Source: `firmware/local_station/motion_core.h`. Current bench default; not a qualified room accuracy target.
- [x] **Q08 — Local bench tracking dwell: 0.15 s** (C07). Source: `firmware/local_station/motion_core.h`. Current bench default; missed-step testing remains open.
- [x] **Q09 — Local bench arrival tolerance: 4 encoder counts** (C07). Source: `firmware/local_station/motion_core.h`. Current bench default; distinct from running tolerance.
- [x] **Q10 — Local bench arrival continuous dwell: 0.05 s** (C07). Source: `firmware/local_station/motion_core.h`. Current bench default; settlement timeout is separately 0.5 s.
- [x] **Q11 — Local bench heartbeat timeout: 0.5 s** (C09). Source: `firmware/local_station/motion_core.h`. Single-axis bench timeout; global stop latency is still unknown.
- [x] **Q12 — Effector stationary interval: 0.5 s** (C12). Source: `firmware/effector_esp32/effector_esp32.ino`. Existing IMU gate; does not implement active leveling.

## Checked development contracts

- [x] **Q13 — Local bench wiring:** STEP GPIO3, DIR GPIO4, ENABLE GPIO5, HOME GPIO10, driver FAULT GPIO20; encoder SDA GPIO6/SCL GPIO7. USB CDC On Boot required. External 10 kΩ ENABLE pull-up; driver RESET/SLEEP held high; MODE0/1 low and MODE2 high for the selected 1/16 profile. Source: `firmware/local_station/local_station.ino` and `docs/LOCAL_STATION_HARDWARE_20261004.md`. Four-axis communications pins remain unassigned.
- [x] **Q14 — Homing calibration boundary:** bead-triggered lengths remain null; detached axis homing establishes its local reference, followed by measured payout and supported setup-pose verification. Do not independently retract four suspended cables to their beads. Source: `docs/DESIGN_RESOLUTION_PLAN_20261004.md`, C03.
- [x] **Q15 — Fastener policy:** use M3 for printed assemblies where the interface permits. Purchased servo center screws and the documented M2 capacitor keeper remain explicit exceptions; do not enlarge purchased threads to M3. Source: user preference and `docs/LOCAL_STATION_HARDWARE_20261004.md`.
- [x] **Q16 — Inventory policy:** selected, ordered, received, and tested are separate states. No purchase or receipt is inferred from a recommendation or CAD model. The supplied switch and cable specifications are specifications, not receipt evidence. Source: O01 ledger and user conversation.

## Useful derived dimensions

For the 24-tooth, module-1.5 gear, pitch radius is 18 mm. The 120° design stroke gives **37.699 mm travel per rack**, or **75.398 mm relative jaw closure** if both racks follow the ideal symmetric mechanism. This is nominal motion; actual minimum gap, stops, horn fit and cloth force require the assembly test.

At 4096 counts/turn, the running threshold of 64 counts is **5.625°**; the arrival tolerance of 4 counts is **0.3515625°**. Neither is a fixed linear cable error: payout depends on measured drum radius/winding.

## Still requires measurements or a larger design change

- Actual switch lever/trip/force, cable diameter, bead retention and spring return behavior.
- Motor thread/shaft details, magnet centering/gap, printed fits and encoder field checks.
- Battery and board envelopes, servo horn stack, connector lead bends, fuse selection and thermal qualification.
- Room survey, COM/load envelope, dock strength and qualified working tensions.
- Four-axis transport/global faults, camera calibration, pickup/deposit evidence and real inventory reconciliation.

The source verifier checks all twelve numeric entries against their code anchors and recomputes the derived dimensions. It verifies no measured values or parent closure records were introduced. Physical commissioning remains separate.
