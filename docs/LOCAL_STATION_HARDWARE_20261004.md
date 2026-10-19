# Experimental self-contained winch electronics, 4 October 2026

This module puts one motor driver, logic regulator, input capacitor and protective fuse holder inside the existing winch cover. The existing XIAO ESP32-C3, AS5600 pedestal and homing switch stay local. It is a separate experimental CAD variant; it does not overwrite `winch_bench.build()` or certify the complete station for suspension. The design has not been physically assembled, powered or thermally qualified. No parts are recorded as purchased by this update.

Generate with `python -m cad.winch_local_electronics`. Exports are in `cad/exports/winch_local_electronics`: replacement base/cover/adapter, electronics carrier, independent board keepers, capacitor keeper, replaceable input panel and complete assembly. Do not mix the replacement base/cover/adapter with old source versions. The conventional external Uno/CNC shield profile remains available; the local driver is an alternative, not a second driver connected to the same motor.

## Selected components and provenance

| Per station | Selected item | Mechanical/electrical basis |
|---|---|---|
| 1 | [Pololu2133 DRV8825 carrier](https://www.pololu.com/product/2133) | OEM15.2×20.3mm board,1.57mm PCB and4.06mm component-side profile. Use direct soldered wires; tall sockets/headers are not modeled.3.3V STEP/DIR interface. About1.5A/phase without added cooling is a manufacturer open-air figure, not this enclosure's demonstrated rating. |
| 1 | [Pololu2831 D24V10F5](https://www.pololu.com/product/2831) |12.7×17.8mm board; conservative3.5mm populated envelope. Supplies5V logic only. Typical1A maximum is input-voltage/temperature dependent. No reverse-polarity protection. |
| 1 | [PanasonicEEUFR1H101](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/EEUFR1H101) |100uF50V,Ø8×11.5mm body. Across VMOT/GND near driver, observing polarity. Driver manufacturer requires at least47uF nearby because long supply leads can cause destructive transients. |
| 1 | [Molex43020-0200](https://www.molex.com/en-us/products/part-detail/430200200) | Two-circuit keyed panel plug with mounting ears. Mechanically mounted in a separate1.5mm panel. |
| 1 | [Molex43025-0200](https://www.molex.com/en-us/products/part-detail/430250200) | Mating locking receptacle on detachable supply cable; source-side contacts are recessed female contacts. |
| 2 each | [43031-0001 male terminals](https://www.molex.com/en-us/products/part-detail/430310001) and [43030-0001 female terminals](https://www.molex.com/en-us/products/part-detail/430300001) |20–24AWG crimp variant, insulation OD≤1.85mm. Use correctly sized crimp tool or manufacturer-compatible precrimp leads; a soldered imitation crimp is not qualified. |
| 1 | [Littelfuse01550100Z](https://www.littelfuse.com/assetdocs/littelfuse-fuse-holder-155-100-datasheetpdf?assetguid=feb34c70-4b5c-48a2-88f9-895c15c5efcc) | Current manufacturer drawing55.63mm length/15.24mm diameter;≤32V holder. Vertical mount with ring and two restraints. Supplied14AWG lead loop; reduce to connector20AWG with insulated, restrained joints, not an undersized crimp. Fuse not included. |
| 1 | DC-rated3AG cartridge fuse |6.35×31.75mm mechanical size. Exact fuse series/current/interrupt rating is **not finalized**. Select after measured input current, wire ampacity and available supply fault current; motor phase current is not supply input current. Do not infer DC suitability from a250VAC marking. |

Primary dimension drawings: [DRV8825](https://www.pololu.com/file/0J1075/drv8825-stepper-motor-driver-carrier-high-current-dimension-diagram.pdf), [D24V10Fx](https://www.pololu.com/file/0J1662/d24v10fx-step-down-voltage-regulator-dimensions.pdf), [Micro-FitSDA-43020](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43020/430200200_sd.pdf). Sources checked4October2026. Pololu listed driver$15.95 and regulator$12.95, before shipping/tax; availability can change. Neither has been ordered here.

The correct **two-circuit** Micro-Fit drawing row is A3.86/C4.20/D7.90mm. The panel cutout has a4.20×7.11mm central rectangle,7.90×4.06mm lateral-ear region and1.98×1.59mm top key. Manufacturer panel thickness range is1.40–2.54mm; the CAD panel is1.5mm. The cover has a larger relief behind it so the3mm cover does not obstruct the snap ears. Manufacturer corner radius maximum0.18mm is difficult to print accurately; inspect/file corners or fabricate the small panel from1.5mm sheet. Nominal housing references omit exact flexible ear shape. Physically demonstrate ear capture, mating latch and pull retention before use.

## Retention, clearances and service

Carrier sits below the motor, in X−51..−7/Y−48..8/Z6..9mm. Four new through-bolts attach to the base, with ordinary rear nuts and corresponding rear-adapter clearances. Driver/regulator sit at Z12mm on narrow bare-end supports; four removable M3 keepers press only board end margins through insulating compliant edge pads. The underside ground pad and components are not pressed against plastic. Actual populated-board revisions must have these bare margins; if they do not, redesign the keepers instead of clamping components or solder joints.

The capacitor has a bottom lead port, an insulating0.5mm radial sleeve and removable perimeter keeper with centralØ6mm vent opening. A compliant rim pad fills the nominal0.5mm vertical gap; do not preload the vent or cover it with a tie. The fuse holder sits in a locating ring with two restraints; free lead loops and opening force are not carried by electrical contacts. Unplug power, discharge the capacitor, release restraints and lift the holder out to change its fuse. Never twist a powered holder inside the case.

| Printed/assembly hardware | Quantity |
|---|---|
| Carrier mounting |4×M3×16,4 ordinary2.4mm nuts,4 rear0.5mm washers; headOD≤6/height≤2mm |
| Driver/regulator end keepers |4×M3×8 into printed pilots; headOD≤6/height≤2mm |
| Capacitor perimeter keeper |2×M2×10; headOD≤4/height≤2mm |
| Input panel |2×M3×10,2 ordinary2.4mm nuts; headOD≤6/height≤2mm |
| Insulation/restraint |4 board-edge pad strips, capacitor sleeve/rim pad,2 fuse-body ties, lead strain-relief ties, heat-shrink over all exposed power joints |

Fit carrier through-bolts/rear nuts before attaching adapter. Populate the carrier on the bench, then install it with cover removed. Route motor pair leads above the tray and around the stationary bracket; route encoder leads separately from motor power and restrain both. Existing top wiring notch remains available. Motor coil connector may remain a secured internal keyed harness; its exact connector/boot envelope is not yet selected.

To service the cover, unplug the external mating cable and disconnect the restrained internal input pigtail before lifting it. The panel is attached to the cover; its actual harness bend/service loop is not modeled. Then remove carrier mounting bolts to lift the populated tray. Independent PCB keepers allow replacement without disturbing the shaft/encoder alignment. CAD checks cover stationary clearances, sampled cover/tray lift and accessible tray drivers; they do not prove wire routing or finger access.

The capacitor keeper retains two M2 screws because its narrow Ø4mm upper support sits between the populated driver and capacitor. An M3 printed pilot would leave only0.6mm radial wall there; M2 leaves1.15mm. All carrier, board-keeper and input-panel attachments use M3. Do not force M3 into this small boss.

The vertical fuse body ends atZ66.63mm; cover inner roof is nominallyZ70.9mm, leaving only4.27mm. That is **bare-body clearance**, not a validated bend for its14AWG lead. No bent-lead envelope or complete harness route has passed CAD checks. The fuse holder/carrier packaging is therefore experimental and **not released for final printing or powered assembly**; change the holder pose/part or supply an actual lead route before release. Other module parts may be used for restrained unpowered fit coupons.

## Electrical assembly contract

Supply is12V DC from the existing isolated external supply. Assign connector cavity1=+12V and cavity2=GND only after checking OEM cavity identification; label both mating sides, verify continuity and polarity before connection. Station positive lead passes through the local fuse before splitting to VMOT and regulator VIN; negatives join at a restrained common-ground node. Keep capacitor wires short near VMOT, with no exposed solder bridge or terminal against printed walls. The local fuse protects the branch after the connector; the supply-side cable also needs protection at its source. No AC mains enters this station.

D24V10F5 VOUT supplies XIAO5V through an external Schottky diode, never its3.3V pin. [Seeed explicitly requires a diode on an external5V feed](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/): anode toward regulator, cathode toward XIAO5V. Its actual current rating, forward drop, insulation and restraint must be qualified; this is not an assumed onboard isolation feature. Regulator ground, driver ground, XIAO ground and encoder ground are common; this is **not galvanically isolated logic**. Disconnect external power before USB programming, or use a qualified power-isolation harness. Do not connect USB5V and regulator5V together assuming automatic backfeed protection. The regulator has no reverse-polarity protection; keyed mechanics do not replace polarity verification.

Control profile: STEP GPIO3,DIR4,active-low ENABLE5,homing10,I2C SDA6/SCL7; nFAULT GPIO20 as INPUT_PULLUP. Read nFAULT low as a driver fault and stop. The firmware profile is detached single-station bench-only; synchronized four-axis motion is not implemented by this module. Hardware pull-up10k on ENABLE holds driver disabled during startup/reset. Hold RESET/SLEEP high from3.3V through the intended wiring; never leave SLEEP low and expect motion. Set DRV8825 MODE0=low,MODE1=low,MODE2=high for1/16 steps. This differs from A4988 mode straps. Keep open logic states deterministic. Firmware motion/watchdog compatibility is separately validated by its owner.

For this genuine Pololu driver, manufacturer relationship is I_limit=2×VREF. Initially set conservatively below motor rating, measure actual coil current and temperature, and increase only if bench behavior permits. Verify resistor/board revision before applying that formula to clones. No claim of1.5A continuous operation inside the printed case is made. Test prolonged holding, motion, stalled/snags and supply transients with the final cover fitted. Log driver/regulator temperature, thermal faults, logic brownouts and encoder integrity. A fuse is not a motor brake; removing power can release cable tension. Use unloaded or restrained bench tests.

## Remaining gates

Exact DC fuse/current coordination; physical snap-panel and mating latch; purchased board bare-edge areas; actual solder/lead boots and bends; input transient behavior; USB power isolation; motor current limit and enclosure thermal performance; emergency-stop wiring and load-holding behavior; print tolerances and assembly retention. These are open qualification items, not completed measurements. This experimental local-controller module is not an approval to operate unattended or install overhead.
