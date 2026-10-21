# Claw electrical — Rev B specification (2026-10-21)

Authority: DECISIONS.md D31 (Jasper, 10/21) and `firmware/claw_s3/claw_s3.ino`
(pin map). Supersedes `docs/CLAW_ELECTRICAL_REVA_20261012.md` for building; Rev A
is kept as history. Status: **design, not yet built or bench-tested.**

## Parts

| Ref | Part | Value / setting | Notes |
|---|---|---|---|
| BT1 | Tenergy 7.4 V 2200 mAh 2S1P Li-ion pack with protection PCB | 8.4 V full, 6.8 V firmware cutoff | 31003 assumed: 3 A continuous, 1 A max charge. Confirm the label and connector. |
| F1 | Blade fuse in holder, battery + lead | 5 A (provisional, from Rev A) | Protects the wiring; the pack PCB is the cell protection |
| SW1 | SPST main switch | ≥ 5 A DC | Load side only; the charger stays on the pack side |
| U1 | ZTW UBEC (6 A continuous / 10 A peak) | jumper set to **6.0 V** | Servo only. Measure the output before connecting the servo |
| U2 | MP1584EN buck module | trim to **5.00 V** before connecting | XIAO only |
| D1 | 1N5819 Schottky | anode at U2 OUT+, band toward the XIAO | Seeed requires a diode on external 5 V input |
| U3 | Seeed XIAO ESP32-S3 Sense (camera board attached) | — | 5V pad from D1; BAT pads unused |
| J2 | MG996R servo lead, 3-pin | GND / V+ / signal | Brown GND, red V+, orange signal; check your lead |
| C1 | Electrolytic | 1000 µF / 16 V | At the servo connector, + to V+ |
| C2 | Ceramic | 100 nF | At the servo connector |
| C3 | Ceramic | 100 nF | At the XIAO 5V pad |
| R1 | Resistor | 200 kΩ 1 % | Battery divider top |
| R2 | Resistor | 100 kΩ 1 % | Battery divider bottom |
| C4 | Ceramic | 100 nF | ADC filter at D2 |
| U4 | USB-C 2S charging module ("2S1A") | B+ / B− to the pack side | USB-C input from a 5 V adapter. Charge with SW1 OFF only |

## Nets (the KiCad schematic must match this exactly)

| Net | Connected pins |
|---|---|
| BAT_POS | BT1 +, F1 in |
| BAT_FUSED | F1 out, SW1 in, U4 B+ |
| VBAT_SW | SW1 out, U1 IN+, U2 IN+, R1 top |
| GND | BT1 −, U1 IN−, U1 OUT−, U2 IN−, U2 OUT−, U3 GND, J2 GND, C1 −, C2, C3, C4, R2 bottom, U4 B− |
| +6V_SERVO | U1 OUT+, J2 V+, C1 +, C2 |
| +5V_BUCK | U2 OUT+, D1 anode |
| +5V_XIAO | D1 cathode, U3 5V, C3 |
| VBAT_SENSE | R1 bottom, R2 top, C4, U3 D2 (GPIO3) |
| SERVO_PWM | U3 D0 (GPIO1), J2 signal |

Unconnected: XIAO D1, D3–D10, 3V3, BAT pads; U2/U1 enable pins (if any) left at
their defaults; U4 USB-C input (external adapter).

## Checks (calculated)

- Battery sense: 8.4 V × 100/300 = 2.80 V at D2; 6.8 V cutoff → 2.27 V. Inside the
  ESP32-S3 ADC range at 11 dB attenuation (~0–3.1 V). Divider drain 28 µA.
- Peak pack current: servo stall ~2.5 A at 6 V (15 W, provisional) + logic ~0.7 A at
  5 V (3.5 W) = 18.5 W; at 88 % efficiency that is 2.8 A at 7.4 V and 3.1 A at 6.8 V,
  at the pack's ~3 A continuous rating. Stalls are short, but the pack PCB may trip on
  a long stall near empty. Measure the servo stall current on the bench.
- Servo signal is 3.3 V PWM into a servo powered at 6 V (no buffer, as the firmware
  assumes). Most MG996R units accept it; bench-check the full open/close travel.
- UBEC near empty: 6.8 V in for 6.0 V out leaves little headroom; the servo rail may sag
  near cutoff, which is acceptable because the firmware stops lifts at 6.8 V.

## Charging rule (D31)

Charge only with SW1 OFF, attended, on a non-flammable surface, with an 8.4 V
CC/CV charger at ≤ 1 A. The pack's protection PCB must provide per-cell
overcharge / over-discharge protection: confirm it on the label or datasheet
before the first charge (a 2-wire pack cannot be balance-charged).

## Before the first power-up

1. Set U1 to 6.0 V and U2 to 5.00 V with a meter, with nothing connected to their outputs.
2. Confirm U4 is an 8.4 V CC/CV module and its charge current is ≤ 1 A (Tenergy limit).
3. Check the pack voltage (7.4–8.4 V) and polarity at the connector.
4. Power up with the servo unplugged; check D2 reads ~VBAT/3 in `/status`.
5. Plug in the servo; run `/setup` to park it open.
