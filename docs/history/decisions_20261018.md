# RoomCleaner decisions and evidence update — 2026-10-18

> **Historical selection notice, added October 19:** Later cost reviews and the user's subsequent Amazon cart reopened the battery/regulator/charger choices. The DROK/OVONIC/TB6B configuration below is not a frozen current BOM. See [current handoff and procurement correction](REVIEW_HANDOFF_20261019.md) before using these component dimensions or wiring assumptions. This record is preserved to explain the earlier reasoning.

Recorded 2026-10-18, America/Chicago. Retrospective record of the current conversation and inspected local design artifacts; individual hardware event dates are not established unless explicitly stated. This is a documentation revision, not a new CAD, firmware, or hardware release.

## Current configuration and scope

- Four wall winches: NEMA17, A4988, local XIAO ESP32-C3, local step-down regulator, homing switch; one 12 V supply pair per station splits locally to driver and buck. ALITOVE supply reported as 12 V / 6 A / 72 W. Four-station current demand and synchronization are not yet qualified.
- Claw: XIAO ESP32-S3 Sense camera on the upper housing/outrigger, battery above, wired extension to a lower servo-driven clamp. PETG structure and TPU contact pads; metal extension remains a later possibility.
- Initial system milestone: four cables supporting a central one-pound test weight. A working moving claw is the intended build, but electrical commissioning and measured load tests still precede that milestone. Five pounds is an aspiration for reserve, not an established payload or safety factor.
- Current power selection: retain **2S battery + DROK 200359 set to 5.0 V**. Do not confuse it with the small DROK modules used at motor stations.
- Manual balance charging is the current prototype implementation. Automatic hook/contact charging remains an end-state requirement, not a completed feature.

## Decision/change register

| ID | Problem or prior approach | Current choice and rationale | Cost/tradeoff and evidence status |
|---|---|---|---|
| D18-01 | Long motor extensions and central Arduino wiring | Local ESP32/A4988 control at each station; distribute DC power and split locally | Reuses drivers and reduces long coil/control runs; requires coordinated motion, local pulse timing, communication-loss behavior and aggregate supply qualification. Architecture selected; one station reported operating. |
| D18-02 | No-motion commands despite software completion | Verify actual rails and connections before attributing failure to code | User ultimately reported a bad 3.3 V connection and successful motor motion after correction. This is a user report, not a captured waveform/load test. |
| D18-03 | Ambiguous XIAO D-labels versus GPIO numbers | C3 bench mapping: STEP D1/GPIO3, DIR D2/GPIO4, ENABLE D3/GPIO5, HOME D10/GPIO10 | These are C3 mappings; do not transfer them to the claw's S3. Runtime firmware identity still needs a saved sketch/commit. |
| D18-04 | Floating or incorrectly wired active-low ENABLE | R1 pulls ENABLE to 3.3 V; driver ENABLE and C3 D3 meet at the resistor's other end | User measured 3.3 V idle, 0 V during command, then 3.3 V. Default disable removes motor torque; not a safe suspended-load holding function. User elected R1 and R4 in the station circuit; full Rev C is not confirmed as-built. |
| D18-05 | Ground routing confusion and an earlier damaged controller | Separate driver/motor power returns from controller return while maintaining the required signal reference | Common ground is not itself a fault. User reported USB-only heating/non-enumeration of a XIAO; exact failure cause remains unproven. Do not claim backfeed or a particular solder bridge caused it. |
| D18-06 | Tentacle complexity and camera occlusion | Simple padded clamp below an extension; upper moving camera looks toward grip region | Preserves a direct view of pickup; adds mass, moment and collision envelope. Vision under bulky laundry still needs testing. |
| D18-07 | Direct servo drive lacks desired force margin | V2 lower gripper uses 18T:54T spur reduction with 36T:36T opposite-jaw synchronization | Ideal 3:1 torque multiplication trades speed and travel; torque is shared by both jaws. Herringbone was considered; V2 uses spur geometry for simpler prototyping and support. No lifetime or optimality claim. |
| D18-08 | Assumed 8 mm servo interface versus reported approximately 5.9 mm spline | V2 records a separate coupling with provisional 5.9 mm smooth recess | Not a modeled 25T spline. Fit, spline engagement, screw thread and torque retention must be measured. Do not represent the printed coupling as qualified. |
| D18-09 | Repeated regulator substitutions made the purchase baseline unclear | Keep the user-accepted 2S + DROK 200359 architecture | Earlier Hobbywing, ZTW and 3S alternatives are not the current shopping baseline. Larger display regulator consumes housing volume/mass. Selection does not prove thermal/current suitability. |
| D18-10 | Battery depletion can reset camera/control and stop grip | Proposed pack-level low-voltage disconnect plus individual-cell checking/alarm and software monitoring | Hardware cutoff does not depend on Wi-Fi/software, but pack voltage cannot identify cell imbalance. Alarm is not a per-cell disconnect. Shutdown can release the grasp: return/park must occur earlier. Thresholds and recovery behavior are not released. |
| D18-11 | Need a complete charger rather than a voltage converter | Tenergy TB6B kit with AC supply and XT60 harness; disconnected-pack 2S balance charging | Adds no charger mass to the moving claw. Does not automatically dock or implement unattended contact charging. |
| D18-12 | Beads positioned for simultaneous center homing restrict reach | Preserve bounded floor-start lift, marker-relative calibration and sequential bead verification | Follow the existing startup research. Encoder mismatch is backup motion evidence, not cable-tension measurement or permission for automatic unwinding. Not hardware-demonstrated. |
| D18-13 | Presentation risks conflating simulation with hardware | Keep decisions, calculations, user-reported tests, purchases and verified receipts distinct | Preserve failures and superseded approaches. Do not use old simulated 9 lb / 4 kg / 40 N assumptions as measured motor or system ratings. |

## Claw power selection and procurement status

User accepted continuing the DROK/2S plan. The exact additional items below were recommended afterward; there is **no subsequent purchase or receipt confirmation** for this list. Listed module ratings are supplier specifications, not measured robot performance. Prices/delivery were not reliably available; no total is claimed.

| Part | Quantity | Current disposition | Specification / consequence |
|---|---:|---|---|
| DROK 200359 | 1 | Selected architecture; purchase unconfirmed | Set 5.0 V; supplier states 3.5 A continuous naturally cooled, 4.5 A with enhanced cooling; input 6.5–36 V. Shared output powers servo and XIAO through separate branches. |
| OVONIC 2S 2200 mAh 50C, XT60 | 1 | Recommended exact battery; purchase unconfirmed | 7.4 V nominal, 8.4 V full; nominal 87 × 33 × 18 mm, 118 g. Supplier tolerances ±5/±2/±2 mm and ±20 g; 3-pin JST-XH balance lead. No built-in protection assumed. |
| Tenergy TB6B kit | 1 | Recommended; purchase unconfirmed | Select AC supply and XT60 harness variant. Proposed initial setting: LiPo BALANCE, 2S, 1.0 A; confirm battery instructions. |
| ICStation XY-CD60 | 1 | Recommended cutoff; purchase unconfirmed | 6–60 V; discharge mode; approximately 79 × 43 × 27 mm. Pack-level switching, not a charger or complete cell-level BMS. |
| Individual-cell LiPo alarm | 1 | Generic recommendation; exact SKU unresolved | Must support 2S JST-XH. Alarm only, no automatic per-cell isolation. |
| Fuse and holder | 1 | Holder reported owned; claw fuse allocation unverified | 5 A was suggested provisionally; verify wire/connector ratings, fault behavior and fuse curve. Existing 7.5 A station main fuse is not automatically the claw fuse. |
| Master disconnect | 1 | Stock/model unconfirmed | At least 5 A at 12 V DC was recommended; verify actual DC rating. Disconnect after use/storage because protection electronics can still consume current. |
| Servo bulk capacitor | 1 | Availability unconfirmed | Proposed 1000 µF / 16 V across lower servo supply, correctly polarized; does not prove surge immunity. |
| Battery ADC network | 1 set | Proposed, not installed/implemented | 100 kΩ / 47 kΩ 1% divider and 100 nF filter. At 8.4 V, nominal ADC input is 2.686 V; validate attenuation, calibration and input behavior. |
| Harness | as needed | XT60 pairs reported owned; remaining quantities unverified | 18 AWG copper for short power distribution; suitable signal wiring, insulation, strain relief, service connectors and battery restraint. |

Purchasing references: [DROK](https://www.amazon.com/dp/B07FL6PBZF), [OVONIC Amazon search](https://www.amazon.com/s?k=OVONIC+2S+2200mAh+50C+XT60), [Tenergy kit](https://www.amazon.com/dp/B07VQBP4ZQ), [ICStation](https://www.amazon.com/dp/B07YTVK1JK). Search links are not a verified SKU or stock confirmation.

## Interfaces changed from the earlier claw Rev A

The earlier Rev A drawing is historical; **do not combine its netlist with this shopping sketch without a revised schematic**.

1. Rev A proposed separate servo and logic regulators. The latest selection uses one DROK 200359 output with separate load branches. Lower part count trades away some supply isolation; simultaneous camera streaming and servo surge tests are mandatory.
2. Rev A's general common-ground description must not be applied across this regulator's input/output negative terminals. The 200359 manual explicitly prohibits an external IN− to OUT− short because it bypasses the constant-current function. Servo and XIAO grounds join on the output side. Avoid bypasses through instruments, USB ground or other circuitry.
3. Rev A used 100 kΩ / 33 kΩ battery sensing; latest suggestion is 100 kΩ / 47 kΩ. Firmware scaling must match the assembled divider. Sense the switched supply so an unplugged/off controller is not driven by a permanently connected battery divider. Confirm the output-ground reference and current-shunt offset in the detailed schematic.
4. The short shopping answer omitted Rev A's USB/external-power isolation, diode, PWM buffer, FSR interface and local logic decoupling. Omission is **not approval to remove these functions**. Audit against actual S3 Sense hardware and servo logic thresholds before issuing a complete wiring drawing or final no-more-purchases claim.
5. Proposed protection is pack cutoff plus cell alarm, not automatic cell-level protection. The full protection requirement remains open. Firmware must start disarmed, inhibit new pickups on low battery, return/park before hard cutoff and never auto-resume after brownout. Hardware threshold/hysteresis and relay retry behavior need controlled verification.
6. Battery and regulator dimensions, harness bend space, cutoff enclosure and combined mass must be added to the user's upper-housing CAD. No housing regeneration or clearance check occurred in this documentation task.
7. Gripper V2 torque calculations used a **6 V reference servo condition**. Current supply selection is **5 V**. Those numerical force estimates cannot be carried over as verified 5 V performance; measure the actual servo or recalculate from appropriate data.

## Evidence and limitations

| Evidence | What it supports | What it does not establish |
|---|---|---|
| User upload log identifying ESP32-C3, flash hash verified, successful serial operation | Correct C3 programming path demonstrated | Correct motor wiring, coordination or exact latest firmware version |
| User-reported switch operation and ENABLE voltage sequence | Some control input/output behavior works | All fault cases, switch reliability or stop distance |
| User: bad 3.3 V connection corrected, motor works; subsequent loud/slow motion | One motor station achieved reported bench motion | Current calibration, load rating, temperature, four-station operation or encoder feedback |
| Local gripper_v2 README, calculated_values.json and geometry_checks.json inspected | Nominal 18:54 / 36:36 design; recorded valid-solid and sampled intersection screens | Physical fit, cyclic wear, torque coupling, native SolidWorks mates, completed upper enclosure or lifting capacity |
| Gear calculations and sampled CAD screens | Basis for choosing a prototype to test | An optimal tooth design, material allowable, fatigue life or validated force rating |
| Supplier documents below | Nominal component ratings and dimensions | Received variant, current stock, purchase, assembly or measured behavior |

The local V2 geometry report records 11 unique printed valid solids; 141 planar mesh samples over 0–35° with no overlap; exact CAD intersection checks at 5° intervals with no reported collision above 0.001 mm³. These were read from existing output, not rerun here. Local V2 specifies 105° servo travel for 35° jaw rotation, 4.3 mm closed pad gap, approximate 81 mm open midpoint gap, and a still-missing upper extension adapter. These limitations are material for cloth grip and integration. The full V2 source/export bundle is not uploaded by this documentation commit.

## Next milestones and required evidence

1. Capture the as-built station schematic, exact running sketch, motor/driver current settings and short bench video. Record measured rails under load, temperature and switch stop behavior.
2. Complete the claw schematic reconciliation above, then qualify 5 V regulation at low battery during camera streaming, servo start, grip and release. Record current, voltage dips, thermal behavior and reset events.
3. Verify charger settings, cell balance, cutoff threshold/recovery and low-battery software behavior. Confirm safe mechanical outcome of lost gripper power. No automatic dock charging in this milestone.
4. Measure complete claw mass, spline interface, printed gear fit and closure; test actual cloth grip and repeated release. Record failures, wear and witness-mark slip.
5. Commission restrained multi-station timing and one-pound load before a room pickup demonstration. Record vision-confirmed pickup and delivery separately from issued commands.

## Sources and provenance

- User conversation through 2026-10-18; motor event times are retrospective, not fabricated timestamps.
- [Prior decision register](decisions_20261014.md), [startup decision](startup_decision_20261016.md), [station architecture review](../electrical/STATION_ARCHITECTURE_REVIEW_20261017.md), [historical claw Rev A](../CLAW_ELECTRICAL_REVA_20261012.md). Older links may be available only in the local archive; see index upload scope.
- DROK 200359 manual: https://m.media-amazon.com/images/I/A18f8cFrTjL.pdf (use parameter table, not conflicting 12 A heading).
- OVONIC manufacturer battery dimensions: https://us.ovonicshop.com/products/ovonic-50c-7-4v-2200mah-2s1p-xt60-and-trx-lipo-battery
- Tenergy kit specifications: https://power.tenergy.com/tenergy-tb6b-multifunctional-balance-charger-for-nimh-nicd-li-po-li-fe-battery-packs-power-supply/
- XY-CD60 manual: https://images-na.ssl-images-amazon.com/images/I/91nFjzJjeJL.pdf

Supplier sources were checked in the preceding purchasing discussion on 2026-10-18. This update changes documentation only. It does not mark purchases as ordered, regenerate CAD, change firmware, or assert completed electrical qualification.
