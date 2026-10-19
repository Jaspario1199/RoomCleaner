# Decision register — retrospective baseline

Recorded 2026-10-14. Links in the [index](README.md) locate supporting design documents. Dates not established by those documents are intentionally omitted. This supplements the original `DECISIONS.md` without rewriting its history.

| ID | Problem | Direction and reason | Status / tradeoff |
|---|---|---|---|
| H01 | Complex first gripper | Simple two-jaw clamp with TPU pads before flexible fingers | User-selected prototype direction; thin-cloth pickup and pad closure need validation |
| H02 | Camera view obstructed near jaws | Camera on upper horizontal outrigger; servo/clamp below on extension | User-selected; improves sight lines but adds mass, moment and collision envelope |
| H03 | Extension material and fabrication | Print PETG prototype, retain removable interfaces for later metal tube | User-selected; section dimensions and strength not validated |
| H04 | Difficult wall assembly/service | Fixed wall frame with removable motor casing and positive retention | User-selected; rail strength, anti-lift lock and wall fastening all require evidence |
| H05 | Long distributed wiring | ESP32 per motor station with local driver and power conversion | Active direction; actual purchased board/driver models still need identification |
| H06 | Apparent pickup can fail | Short transfer plus camera confirmation; verify delivery before counting | User requirement; implementation and camera behavior need full-system tests |
| H07 | Encoders do not measure cable slip | Use shaft feedback for motor tracking; retain vision verification | Design limitation; not a substitute for payload tracking |
| H08 | Power-off stepper holding | Park/support mechanism at rest; defer active locking mechanism | User deferred lock; supported commissioning remains necessary |
| H09 | Recharging without handling pack | Structural wall hook with keyed recessed compliant electrical contacts | User requirement; charger and contact implementation not frozen |
| H10 | Exposed balance connections at dock | Evaluate onboard 2S charger/power path with internal cell taps | Assistant recommendation; mass/thermal cost vs simpler external contacts; exact module not selected |
| H11 | Reliable presentation history | Keep dated snapshots, subsystem versions, decisions and evidence separate | User requirement 2026-10-12; established in this archive |
| H12 | Shipment vs inventory certainty | Record motor-station components as reported shipped; FSR as reported purchased | Exact received stock requires photos/counts; battery purchase remains unconfirmed |

Future changes append a new entry with superseded ID, rationale and evidence. Do not silently turn recommendations into approved requirements.
