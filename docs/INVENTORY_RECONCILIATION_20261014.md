# Inventory reconciliation — Rev A, 2026-10-14

Evidence: user-supplied Amazon order-history text, `Pasted text(2).txt`, and the user's explicit statement that fuse holders and WAGO connectors are on hand. Personal order numbers, totals and shipping details are intentionally omitted from this public record.

Repeated product-title lines are display duplicates, not additional packs. Quantities below come from listing pack sizes, not a physical stock count. **Amazon marked delivered** does not establish remaining quantity, electrical testing or installation. **Arriving today** is preserved as shown in the supplied text, not promoted to delivered.

## Motor-station parts and tools

| Item | Listed quantity | Evidence/status | Build implication |
|---|---:|---|---|
| Seeed XIAO ESP32-C3 | 3 boards | Amazon delivered October 12, 2026 | Primary compact station controllers |
| ELEGOO ESP-WROOM-32 USB-C development boards | 3 boards | Amazon delivered August 13, 2026 | One could serve as fourth station if unallocated; needs its own pin map and firmware target |
| ACEIRMC CNC Shield V3 with A4988 carriers and heatsinks | 1 shield, 4 drivers, 4 heatsinks | Amazon delivered August 7, 2026 | Use A4988 as actual available driver baseline; inspect carriers before wiring/current adjustment |
| DROK selectable/adjustable buck converters, advertised 4.5–20 V input | 6 | Amazon delivered October 13, 2026 | Candidate station 5 V regulators; exact board selection method and continuous output capability unverified |
| EBOOT MP1584EN adjustable buck converters | 6 | Amazon delivered August 13, 2026 | Alternative regulators; remaining stock/allocations unverified |
| SIM&NAT inline ATC/ATO blade fuse holders, 14 AWG leads | 10 | Amazon delivered August 7; user confirms holders on hand | Replaces hypothetical cartridge-holder purchasing need; actual envelope differs from old CAD |
| Standard blade fuses in the same kit | 50 assorted | Amazon delivered August 7; listing includes 1, 2, 3, 4, 5, 7.5, 10, 15, 20, 30 A | Exact count by rating, DC rating and time-current characteristics unverified; branch rating not yet selected |
| WAGO 221 assortment: 221-2401, -412, -413, -415 | 12 connectors | Pasted text says order received; user explicitly confirms possession | Power distribution; positive and ground use separate connectors; individual assortment counts not physically checked |
| XT60H male/female connector pairs | 10 pairs | Arriving today in supplied text | Candidate detachable power connectors; arrival not confirmed |
| JCCON 100 uF / 50 V electrolytic capacitors, advertised 8×12 mm | 10 | Arriving today in supplied text | Candidate local driver supply capacitors; arrival, polarity and installed behavior need checking |
| HiLetgo KW12-3 roller limit switches | 10 | Amazon delivered August 7 | Homing using COM/NC terminals; verify terminals electrically |
| EEEEE 1N5819 Schottky diodes | 150 | Amazon delivered September 4 | Available stock source for controller supply isolation; remaining quantity unverified |
| Digital multimeter with leads | 1 listed item | Amazon delivered August 13 | Check it is present/functional before power and current-limit setup |
| 80 W adjustable soldering iron kit | 1 listed kit | Amazon delivered August 12 | Assembly tool; remaining consumables unverified |
| ELEGOO UNO R3 Super Starter Kit | 1 | Amazon delivered August 7 | Existing controller/tools/components; resistor and breadboard contents not inferred from title |

The pasted records do not identify the motor part number/current rating, the 12 V supply output rating, available wire sizes/lengths, AS5600 encoders/magnets, or a station pull-up resistor inventory. Missing from this excerpt does not mean never ordered.

## Claw, mechanical and shared stock

| Item | Listed quantity | Evidence/status | Allocation / limitation |
|---|---:|---|---|
| Seeed XIAO ESP32-S3 Sense with camera and microphone | 1 listed board kit | Delivered October 13 grouping | Claw controller/camera; listing now establishes ordered Sense kit, physical revision still unchecked |
| DF9-16 20 g–2 kg force sensors | 2 | Amazon delivered October 13 | Claw force sensing; supersedes purchase-only status |
| Deegoo-FPV MG996R servos | 4 | Amazon delivered August 7 | Claw servo stock; actual model performance and remaining quantity unverified |
| 9KM DWLIFE braided line | 1 listed spool | Amazon delivered August 7 | User previously specified 150 m, 120 lb, 8 strands; excerpt title alone covers multiple variants |
| M3 button-head fastener assortment | 640-piece kit | Amazon delivered August 7 | Actual screw lengths and remaining counts need inspection |
| Heat-set insert kit with tool, M2 through M6 | 580+7-piece listing | Amazon delivered August 7 | Actual insert dimensions need inspection |
| SUNLU grey PETG | 4 kg listed pack | Arriving today in supplied text | Receipt not confirmed |
| JLJLUP protected 3.7 V 2000 mAh LiPo, PH2.0 connector | 1 listed pack | Amazon delivered September 3 grouping | Existing single-cell/shared-project stock, not proof of the proposed 2S claw battery purchase |
| ACEIRMC Type-C USB 2S boost/charging boards | 2 | Amazon delivered August 13 | Exact version, balancing and charging/protection functions unqualified; not approved as autonomous dock charger |
| MT3608 boost modules | 5 | Amazon delivered September 3 grouping | Shared stock; boosts voltage, not a substitute for the station step-down regulator |
| IRLZ44N N-channel MOSFETs | 10 | Amazon delivered September 3 grouping | Shared stock, no automatic station requirement |
| IRF4905 P-channel MOSFETs | 10 | Amazon delivered September 4 | Shared stock, no automatic station requirement |
| Hechen HS-0730B 6 V solenoid | 1 listed item | Amazon delivered September 3 grouping | Shared/other-project stock, not assigned to the motor station |

## Consequences for the next build

1. No additional fuse-holder purchase is established as necessary. Select actual fuse protection from the available kit only after checking ratings, wire sizes, supply and station input current. Motor phase current is not the same as 12 V branch current.
2. Use the actual **A4988**, not the earlier proposed DRV8825, for the first station plan. A4988 requires a separate logic VDD connection (3.3 V is suitable for the chip), has different microstep straps and no equivalent carrier nFAULT connection. Do not wire the old DRV8825 fault input to the A4988 VDD position. Its VREF relationship depends on the actual carrier's current-sense resistors.
3. Prior DRV8825 single-station firmware is not automatically compatible. Create and verify an A4988 hardware profile before motion; do not silently bypass encoder/heartbeat checks to use that firmware for a bare motor test.
4. Three C3s plus one available ELEGOO ESP32 could cover four stations. Different ESP32 variants need separate board definitions/pin assignments and measured timing; the hardware mix alone does not require a replacement purchase. Actual free stock and final enclosure fit remain open.
5. Purchased blade holders, DROK boards and XT60H connectors differ from the previously proposed cartridge fuse, Pololu regulator and Micro-Fit connector. Old electronics trays and panel cutouts are not dimensionally validated for these parts.
6. Next evidence: photographs of both sides of one A4988 and one DROK board, the power-supply and motor labels, fuse markings, plus confirmation that the capacitors have arrived. Begin with one C3 on USB only while this is resolved.

Technical reference checked 2026-10-14: https://www.pololu.com/product/1182 . Pololu documentation establishes A4988 interface behavior, not the exact sense resistance, thermal rating or physical dimensions of the user's ACEIRMC carrier.
