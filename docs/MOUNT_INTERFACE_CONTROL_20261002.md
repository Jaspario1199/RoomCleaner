# Mount interface control and acceptance — fresh review, 2 October 2026

This is a bench prototype interface specification. CAD nominal dimensions are not achieved manufacturing tolerances. Do not print four stations or install overhead on the basis of a passing interference script. The earlier release ZIP is superseded pending completion of this fresh review.

## Datums and inspection

Use A = motor locating boss/shaft axis, B = motor mounting face, C = structural base back face. Measure spool and magnet runout relative to A, not relative to a printed exterior. Use D = outlet metal bore axis and E = dock wall contact face for outlet and wall-load measurements. Inspect the installed encoder relative to the rotating magnet, including motor-energized testing.

| Mate | Known basis | Acceptance / remaining measurement |
|---|---|---|
| Motor and bracket | User:42.3 face,38 body,31 mounting pitch,22 boss,5 D shaft,24 projection | Caliper-check received motor, flat depth, shaft projection and screw usable depth. No substitute NEMA17 bearing rating. |
| Shaft/spool |5.2 nominal printed bore, original20 core/26 winding/36 flanges | Coupon and actual shaft fit; no rocking; measure rotational runout; demonstrate grub retention under intended torque. |
| Magnet/cup | K&J D42DIA6.35×3.175, manufacturer dimension tolerance±0.1mm | Actual magnet plus calibrated pocket; center while adhesive cures; measure assembled runout. A larger pocket alone does not establish centering. |
| Encoder/magnet | Grove101020692 AS5600 | AS5600 data sheet gives≤0.25mm axis displacement for6mm magnet conditions; the combined shaft/cup/pocket/PCB/print errors must meet the budget. Default1.5mm face gap is a starting value, not a universal field guarantee. Check MD asserted, ML/MH clear, magnitude/AGC throughout360° with motor energized. |
| Outlet | RonstanRF8090-05 OEM model,15.0045 approximate OD,7.5 axial, flared mouths and circumferential groove | Capture groove, expose metal mouth, no plastic contact over intended approach cone. OEM IGES is an open surface model, not a valid closed-solid collision certification. Inspect real groove fit and retention. Current collar clearance is checked at40° from outlet axis, with360° azimuth; prove actual room poses fit this cone. This is not unrestricted angular movement. |
| Collar guide | OndrivesSHS3-12 shoulder3.987 +0.005/−0.025, length12.013 +0.05/−0; head6×3; M3×4 thread | Check sliding friction, guide parallelism and actual shoulder/head seats; qualify oblique bead push with both guide screws installed. |
| Return spring | CenturyZ-2CS OD6.35/ID5.33, free9.65, solid3.81, rate0.65N/mm | Installed7→5mm gives nominal pair3.45→6.05N; full-stroke length1.19mm above published solid. Verify return force against friction and real switch operating force. |
| KW12 switch | User supplied body20×10.5×6.5; published generic KW12 is not a guaranteed matching revision | Body dimensions do not define lever pivot, force or trip/overtravel. Electrically measure trip and release, establish≥0.5mm trip margin before hard stop, verify terminals/ties cannot be contacted by moving parts. |
| Dock rails | Nominal0.2mm side gap,0.6mm face gap | Print rail fit specimen/full dock-adapter pair. No binding, rail damage or rocking; log gap after load and removal cycles. |
| Wall attachment | Actual substrate and purchased fastener unresolved | Match major thread/head/washer, effective timber embedment and edge distances; use manufacturer connection data applicable to actual substrate. Plastic/PETG connection is not a catalog steel-bracket connection. |

## Encoder centering budget

The CAD clearances do not guarantee the AS5600 alignment target. The nominal cup pilot permits0.2mm radial float; a6.55mm pocket and magnet at6.25mm minimum size permit0.15mm radial float; a2.2mm PCB hole around2mm screw permits0.1mm. A simple worst-case sum is0.45mm before printer, shaft and PCB chip-location errors, exceeding the0.25mm data-sheet condition. These clearances are for assembly, not a locating tolerance. Center and retain cup/magnet while measuring runout, then set the removable sensor pedestal to the measured axis. If repeatable centering cannot be obtained, use a measured precision locating insert/shaft-referenced pilot and re-audit; do not merely enlarge the magnet pocket. The alignment parameters do not remove rotating eccentricity.

## What the checks must cover

Installed clearance alone is inadequate. Every revision must cover fastening-tool access, line threading, ring insertion, preassembly order, removal/service path, collar stroke, bead approach, complete rotor sweep, cover removal, encoder lead space and slide insertion with actual fastener envelopes. Intentional screw engagement must be documented; blanket collision exemptions hide defects.

Measured printed fit is required because shrinkage, hole undersize, elephant-foot and layer orientation are printer/process dependent. Print coupons using the final material/settings and record actual hole/bore dimensions. Do not shrink the entire model to fix a single mating feature.

## Primary sources

- [Ronstan RF8090-05 and OEM downloads](https://www.ronstan.com/us/ropeglide-ring15mm-x-5mm-x-7mmblack-1.html)
- [Ondrives SHS3-12 dimensional tolerances](https://ondrives.com/shoulder-screws/shs3-12)
- [Century Spring Z-2CS](https://www.centuryspring.com/shop/z-2cs)
- [K&J D42DIA](https://www.kjmagnetics.com/d42dia-neodymium-diametric-disc-magnet)
- [AS5600 manufacturer data sheet, mirrored by Seeed](https://files.seeedstudio.com/wiki/Grove-12-bit-Magnetic-Rotary-Position-Sensor-AS5600/res/Magnetic%20Rotary%20Position%20Sensor%20AS5600%20Datasheet.pdf)

No purchases or delivery status are inferred from component selection. Existing user stock must be confirmed against these exact variants.

## Source refinement — 2026-10-04

Encoder-foot rear relief diameter is8.2mm in current CAD (formerly8mm): a0.1mm radial increase removes exact tangency at the adapter X52 spine edge. Nuts still bear on the base. Encoder pedestal4605 and functional dock2024 checks pass after this change. Existing reviewed archive is preserved.
