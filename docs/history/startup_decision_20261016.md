# Startup calibration decision and evidence — 2026-10-16

## User-selected direction

Upright claw starts near room center on floor with limited slack. A short automatic lift precedes calibration; the user places a roughly six-inch printed fiducial nearby/under the camera. Marker location is not surveyed. Rough room/mount dimensions initialize visual/encoder estimation. Coordinated movements refine geometry. Sequential physical bead checks reaffirm the references. Operation follows accepted calibration and verification.

This supersedes conversational suggestions to require a docking cradle or remove bead verification. It does not remove existing software interlocks or make the former detached HOME command appropriate for attached cables.

Full design: [STARTUP_CALIBRATION_V1_20261016.md](../STARTUP_CALIBRATION_V1_20261016.md).

## Decisions and unresolved choices

| ID | Decision / status | Reason |
|---|---|---|
| SC01 | Adopt marker-relative coordinate system | Marker can be put down without measuring its room position |
| SC02 | Separate bounded pickup from geometric calibration | Slack removal does not produce valid taut-cable geometry samples |
| SC03 | Use coordinated motion even when emphasizing one station | Cable constraints are coupled; other three axes cannot generally remain locked |
| SC04 | Keep encoder following-error stop as a backup | Detects missing motion/backdrive, not tension or line traction |
| SC05 | No automatic unwinding on an unexplained fault in V1 | Fault cause and remaining load support are not established by encoder error |
| SC06 | Camera-first tilt estimation; reserve IMU option | Camera test comes first; independent gravity monitoring is an upgrade |
| SC07 | Preserve physical bead verification | User explicitly requires reaffirmation using the homing devices |
| SC08 | Bead contact is a single cable reference | Do not reset all axes or infer a full pose from one switch |
| SC09 | Preserve LOCAL_ONLY vs full READY | Small-patch fitting and distant bead travel have different evidence requirements |
| SC10 | Tension sensors remain an unresolved qualification-dependent addition | Do not claim needed for every supervised test or replace them with a presumed stall clutch |

## Hardware evidence from the 2026-10-14 session

User identified 12 V / 6 A / 72 W ALITOVE supply. User measured buck 5.00 V, about 4.7 V at XIAO input after diode, and 3.3 V at regulated output; later reported the soldered setup good. Photos identify the red A4988 carrier/heatsink. Motor coil pairs reported identified. Correct ESP32-C3 toolchain uploaded successfully; serial output later confirmed working. Homing-switch released/pressed states confirmed working. Do not infer disconnected-wire test, encoder installation, motor current limit, capacitor arrival, motor motion, or four-axis startup completion from these reports.

## Work completed this revision

- Research/specification with coordinate model, pickup states, camera calibration, fit method, bead checks, fault handling, validation sequence and open measurements.
- Offline synthetic fitting sensitivity study with reproducible script and JSON results.
- Non-executable parameter template with unknown machine limits left null.

No live motor-control firmware was changed. No camera/hardware calibration was performed. The numerical study omits force, visibility and motion dynamics and must not be presented as hardware validation.
