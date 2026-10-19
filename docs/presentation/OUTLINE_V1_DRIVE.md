# Outline v1 (Google Slides, 2026-10-19) — archived record

Source: "RoomCleaner — SpaceX Technical Presentation — Outline v1" in Jasper's
Drive (https://docs.google.com/presentation/d/1-9cpMw0nqccEls9PRC2QUmUAKyAcmY5KLo52BrZoQjA).
Superseded by `SPACEX_OUTLINE.md` (v2); kept because it records the gen-2
design statements that DECISIONS D15–D19 were taken from.

| # | Section | Headline | Key content |
|---|---|---|---|
| 1 | About me | Jasper Buntinx | background, why I build (placeholders) |
| 2 | Scope | The problem and success criteria | find/grip/deliver laundry; first target four winches + central 1 lb test weight (not a payload rating); room 11 × 9 ft, 9 ft high |
| 3 | Ownership | My scope and timeline | requirements → sizing → CAD → fabrication → station bring-up → integration (placeholders) |
| 4 | Design | Architecture and its evolution | earlier: one central Arduino + drivers, long motor harnesses; now: local XIAO ESP32, A4988 and step-down regulator at each winch; trade-off: fewer long wires vs synchronized motion and comms faults |
| 5 | First principles | Cable force and motor sizing | Σ Tᵢuᵢ + mg = ma, Tᵢ ≥ 0; τ = T·r; F ≈ η·G·τ(ω)/r |
| 6 | Mechanism | Spool and cable path | spool shortened to fit shaft engagement, ~20 ft of line; radius changes with winding; simple outlet vs level-wind |
| 7 | Structure | Removable wall station | fixed wall frame + removable housing; interlocking slide; failure cases: rail-root cracking, layer separation, creep, fastener pull-out, upward motion |
| 8 | Manufacturing | Fit, fabrication, assembly | rail clearance, motor pilot/bolt pattern, shaft engagement, lid access; record material/orientation/layer/walls |
| 9 | End effector | Gripper packaging and transmission | upper electronics/camera housing, rigid extension, lower servo clamp; proposed 3:1 reduction |
| 10 | Controls | Motion, homing, fault response | one station: motor jog + homing switch worked |
| 11 | Challenge | Motor that would not move | pulses logged; EN 3.3→0→3.3 V; logic rail ≈ 1.14 V; poor 3.3 V connection; moved after repair |
| 12 | Test plan | One station to four | four stages with acceptance criteria to fill |
| 13 | Results | Results and limits | one station reported; no room-scale claims |
| 14 | Reflection | Lessons | half-time: freeze one station, test early, duplicate |
| 15 | Conclusion | Next gate | repeatable four-station 1 lb demo |
| 16–18 | Backups | electrical, gearing, calibration | |
| 19–20 | Prep | evidence list; SpaceX prompt fit | draft Oct 22, panel Oct 27 11:00 CT, bring local PPT/PDF |
