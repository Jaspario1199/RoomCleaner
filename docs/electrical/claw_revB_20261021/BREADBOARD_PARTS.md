# Claw Rev B breadboard: parts and links (2026-10-25)

One row per label on [breadboard_layout_claw.png](breadboard_layout_claw.png). Values come from
[CLAW_REVB_SPEC.md](CLAW_REVB_SPEC.md).

**About the links:**
- **"listing"** is a specific product page already used elsewhere in this repo ([SHOPPING_LIST.md](../../SHOPPING_LIST.md),
  the 10/18-10/19 claw power notes). Amazon blocks automated checks, so confirm the variant and price at checkout.
- **"search"** is an Amazon search for a generic part. Any seller works if the value and package match.
- **"own"** means a part you probably already have, from the ELEGOO starter kit or the station builds.

| Label | Part | Value / what to check | Link |
|---|---|---|---|
| U3 | Seeed XIAO ESP32-S3 **Sense** (with the camera board) | Solder the header pins before it goes in the breadboard | [Seeed wiki (has the buy link)](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) · [search](https://www.amazon.com/s?k=Seeed+Studio+XIAO+ESP32S3+Sense) |
| U2 | MP1584EN buck module | Trim to **5.00 V** before connecting | [listing (EBOOT 6-pack, own)](https://www.amazon.com/MP1584EN-DC-DC-Converter-Adjustable-Module/dp/B01MQGMOKI) |
| U1 | ZTW 6 A UBEC (screenless) | Jumper set to **6.0 V**. Not the G2 variant (7 V minimum input) | [listing](https://www.amazon.com/dp/B071CHGWRM) |
| J2 | MG996R servo, standard 180° (not 360°) | Brown GND, red V+, orange signal | [listing (4-pack, own)](https://www.amazon.com/4-Pack-MG996R-Torque-Digital-Helicopter/dp/B07MFK266B) |
| J2 header | 2.54 mm male break-away header, 3 pins | Goes in f22-f24 | [search](https://www.amazon.com/s?k=2.54mm+male+breakaway+header+pins) |
| BT1 | Tenergy 7.4 V 2200 mAh 2S1P Li-ion with protection PCB | Confirm the label and connector | [Tenergy page](https://power.tenergy.com/tenergy-li-ion-7-4v-2200mah-rechargeable-battery-w-pcb-2s1p-16-25wh-4a-rate/) |
| F1 | Inline blade-fuse holder + blade fuses | Fit a **5 A** fuse | [listing (SIM&NAT, own)](https://www.amazon.com/SIM-NAT-Automotive-Standard-Replacement/dp/B07FQCBSJ5) |
| SW1 | SPST rocker or toggle switch | Rated ≥ 5 A DC | [search](https://www.amazon.com/s?k=SPST+rocker+switch+10A+12V+DC) |
| U4 | USB-C 2S lithium charging (boost) module, "2S1A" | **8.4 V** output, ≤ 1 A. Not the 12.6 V or 16.8 V version | [search](https://www.amazon.com/s?k=Type-C+2S+8.4V+1A+lithium+battery+charging+boost+module) |
| D1 | 1N5819 Schottky diode, DO-41 (through-hole) | Stripe = cathode. Not the SMD "1N5819WS" | [search](https://www.amazon.com/s?k=1N5819+schottky+diode+DO-41) |
| C1 | Electrolytic capacitor | **1000 µF, ≥ 16 V**. Long leg +, stripe − | [search](https://www.amazon.com/s?k=1000uF+16V+electrolytic+capacitor) |
| C2, C3, C4 | Ceramic capacitor | **100 nF**, marked "104", ≥ 16 V | [search](https://www.amazon.com/s?k=100nF+104+ceramic+capacitor+50V) (the ELEGOO kit has some) |
| R1 | Metal-film resistor | **200 kΩ 1 %** (red-black-black-orange-brown) | [search](https://www.amazon.com/s?k=200k+ohm+1%25+metal+film+resistor) |
| R2 | Metal-film resistor | **100 kΩ 1 %** (brown-black-black-orange-brown) | own (ELEGOO kit) · [search](https://www.amazon.com/s?k=100k+ohm+1%25+metal+film+resistor) |
| WAGO 1, 2, 3 | Lever nuts: two 5-way (221-415), one 3-way (221-413) | WAGO 1 (VBAT) takes 4 wires, WAGO 2 (GND) takes 5, WAGO 3 (fuse / charger / switch joint) takes 3. See [offboard_wiring_claw.png](offboard_wiring_claw.png) | [search 5-way](https://www.amazon.com/s?k=WAGO+221-415+lever+nut) · [search 3-way](https://www.amazon.com/s?k=WAGO+221-413+lever+nut) |
| Board | Full-size 830-point breadboard + jumper wires | | own (ELEGOO starter kit) |
| Pack-side wire | 18-20 AWG silicone wire, red + black | For the battery, fuse, switch and WAGO leads | [search](https://www.amazon.com/s?k=18+AWG+silicone+wire+red+black) |

**No 200 kΩ resistor?** Two 100 kΩ in series in the same spot work as R1. Put them h14 → h16 → h18, with the
middle joint alone in row 16 (f-j). That gives the same 1:3 divider the firmware expects (BATT_RATIO 3.0).

Before buying, read the U4 note in [CLAW_REVB_SPEC.md](CLAW_REVB_SPEC.md) "Charging rule": it must be an 8.4 V CC/CV module
at ≤ 1 A, and the pack's PCB must give per-cell protection.
