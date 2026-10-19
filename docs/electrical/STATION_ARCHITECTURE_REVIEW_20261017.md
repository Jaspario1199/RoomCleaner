# Motor-station architecture: effectiveness review

October 17, 2026 (America/Chicago). Companion to [Rev C schematic](station_revC_20261016/RoomCleaner_Station_RevC.pdf).

## Decision

Retain the current XIAO ESP32-C3 + A4988 + local buck architecture for the supervised, unloaded bench prototype, after locating the existing electrical fault. Keep the Rev C pin map and resistor values; do not introduce another round of speculative rewiring. Four 10k resistors are a sensible complete implementation, but they are not four independent safety devices or four prerequisites to seeing a motor move.

The architecture is economical with the parts already bought. It is not yet the best configuration for an unattended, suspended four-station machine: power-fault protection, motor/load qualification, and loss-of-power behavior are still incomplete. An electrical topology review cannot establish that a particular perfboard is correctly built.

No fault diagnosis, purchase, hardware test or new firmware deployment is claimed by this review. Rev C remains the current drawing; this document qualifies its benefits and limits rather than silently changing connections.

## 1. Why each resistor is there

The labels below are the external R1-R4 on Rev C, not similarly named components already on the A4988 carrier.

| Part | Actual benefit | Priority / decision | What it cannot do |
|---|---|---|---|
| R1: ENABLE to 3.3V, 10k | Biases outputs disabled when the ESP32 pin is high impedance and logic power is present | Highest priority; retain | Cannot oppose a GPIO actively driving LOW, guarantee behavior during every fault, or hold a suspended load when disabled |
| R2: STEP to GND, 10k | Gives the step input a defined inactive state before firmware takes over | Useful; retain | Cannot block valid-looking pulses from faulty software or eliminate every noise transient |
| R3: DIR to GND, 10k | Defines the initial direction | Low-cost secondary improvement; retain if fitting the complete circuit | Does not itself prevent movement; direction matters only when stepping |
| R4: HOME to 3.3V, 10k | Defines the switch signal externally and lowers its impedance compared with the internal pull-up alone | Useful for the assembled station; optional for the earlier short-wire INPUT_PULLUP-only test | Not contact debounce, short-to-ground detection, or proof of switch contact suitability |

One important reason to keep R2: disabling A4988 motor outputs does not disable its internal step sequencer. An unintended STEP can alter its electrical state even while ENABLE is HIGH. Holding RESET LOW would reset that state, but our current design keeps RESET HIGH. This is a reasoned improvement, not evidence that stray steps caused the overheating. [A]

With an assumed 3.3V rail, a 10k resistor draws at most 0.33mA when its two ends are at opposite logic levels and dissipates 1.09mW. A 1/4W part has ample power margin. These resistors do not load a healthy controller like a motor winding would. R1-R3 are attached to the signal junctions, not inserted in series between boards.

For the driver input, a worst-case 20uA input leakage across 10k changes voltage by 0.20V. Against A4988 thresholds of 0.7VDD HIGH and 0.3VDD LOW, at 3.3V the simple leakage-only estimates are 3.10V versus a 2.31V HIGH requirement and 0.20V versus a 0.99V LOW limit. This supports 10k as a reasonable choice. It is not a full noise-margin analysis of unknown carrier pull resistors, ground shifts or board contamination. [A]

Espressif lists approximately 45k typical internal pulls. If the HOME internal pull-up is enabled alongside external 10k, their equivalent is about 8.18k. Closed-switch current is then approximately 0.403mA, compared with 0.073mA for the typical internal pull-up alone. The stronger pull is real, but is not an RC filter. [B]

Do not remove resistors already correctly installed. If starting with the older circuit, R1 is the first bias component to prioritize, followed by R2; R3/R4 are inexpensive refinements. Missing R2-R4 does not explain the measured 0V at VMOT, and adding them will not repair a shorted supply or failed XIAO.

## 2. Controller-to-driver compatibility

The C3 pin assignment remains suitable: D1/GPIO3 STEP, D2/GPIO4 DIR, D3/GPIO5 ENABLE, D10/GPIO10 HOME. These do not use C3 boot-strap GPIO2/8/9 or USB data GPIO18/19. GPIO4/5 share pad-JTAG functions, so do not enable external pad-JTAG on those pins while using this wiring. Keep D4/GPIO6 and D5/GPIO7 reserved for a local encoder bus. [B,C]

Continue using XIAO 3V3 for driver VDD. At VDD=5V the driver's specified HIGH threshold would be 3.5V, which a 3.3V GPIO cannot guarantee. No level shifter is needed with the present common 3.3V logic supply. Healthy A4988 logic consumes only a few milliamps; motor power comes from VMOT, not the XIAO. The controller's thermal failure is not an expected consequence of correctly powering this logic load. [A]

RESET/SLEEP to 3.3V and MS1-MS3 to ground remain valid bench choices. Full-step mode is for initial testing; final smooth motion may benefit from microstepping plus acceleration planning, requiring corresponding software scaling. It does not require replacing the power architecture. Retain the carrier's onboard small decoupling capacitors; the drawing represents modules, not an unpopulated IC design.

## 3. USB and external power

The reviewed Seeed drawing connects the exposed 5V pin to the board VBUS net. The manufacturer recommends a diode in the external feed. Our 1N5819 orientation follows that recommendation. [C,D]

Engineering inference: an external-feed diode blocks a higher USB voltage from feeding the buck backward. It does not positively disconnect an external source from USB VBUS in every voltage/tolerance/fault condition. The fact that 5.00V minus a diode drop is normally below USB voltage is not a complete source-selection guarantee.

JP1 is therefore effective as a simple manual separation:

| Operating mode | USB | JP1 | 12V |
|---|---|---|---|
| Upload / controller test | Connected | Open | Off |
| Serial motor bench test | Connected | Open | On after checks |
| Standalone station | Unplugged | Closed | On |

Change connections only while unpowered. JP1 can be an existing removable connector in the positive feed. Grounds remain common. This solves source contention by procedure, not automatic interlocking. For a later product, a designed power multiplexer/reverse-blocking arrangement would remove this human dependency; simply adding another diode somewhere outside the USB path is not equivalent. No board modification or USB cable surgery is recommended for this bench build.

The normal external path contains voltage drops; retain 5.00V at buck OUT+ and verify 3.3V at the controller under its actual operating load. Do not increase buck voltage just to make the post-diode pin read exactly 5V. We have not proved USB backfeed was the failure mechanism.

## 4. The power system is the larger unfinished issue

One 12V pair per station, splitting locally to motor VMOT and the buck input, remains appropriate. Common ground supplies the signal reference. Give motor current a short, substantial return to the station inlet; avoid routing it through the controller's narrow wiring. A schematic ground symbol says two nodes are electrically common, not that long thin wires have zero impedance.

The matching DROK family is specified for 4.5-20V input and explicitly lacks output-overvoltage and reverse-input protection. Exact module revision remains unconfirmed. Thus a motor-supply transient could exceed the buck's stated range before reaching the A4988's 35V limit. Do not upgrade this assembly to a 24V supply while retaining that buck. [E]

The local 100uF/50V capacitor is useful and exceeds Pololu's 47uF minimum bulk-capacitor guidance, but placement and the overall circuit matter. It supplements onboard ceramic decoupling. A4988 carrier guidance warns about motor-power spikes and powered motor disconnection. [F]

Calculation, not a measured transient: a 100uF capacitor stores only an additional 12.8mJ when rising from 12V to 20V, using delta-E = 0.5 C (V2 squared - V1 squared). This is not an acceptable operating target; it illustrates why a 50V capacitor rating is not a voltage clamp for a 20V-rated buck. Actual excess energy, source absorption, inductance and regeneration remain unknown. TI explains why capacitance and transient suppression depend on those system conditions. [G]

For future room operation, prefer a qualified fixed-output regulator with more input transient margin and specified downstream fault protection, or a designed overvoltage-disconnect stage. Generic short-circuit or overtemperature protection does not imply protection against the output rising toward 12V. TI's eFuse families show that current limiting, reverse blocking and overvoltage cutoff are separate functions; no particular bare eFuse IC or generic module is being released as a drop-in purchase here. [H]

Do not add a random '12V TVS' and assume the issue is solved: its clamp voltage at the expected surge current must protect the weakest load, with tolerances and wiring inductance accounted for. For an unloaded short-wire test, verify the existing buck before replacing it. Before long-cable/load use, measure the station rail during start, stop and controlled lowering, using a properly referenced oscilloscope, and select protection from that evidence. No fault-injection experiment with a fresh XIAO is needed.

## 5. Fusing and supply capacity

Keep distribution in parallel. Place individual positive-branch protection near the source, before the long cables. Select against the smallest downstream wire/connector and actual fault current, accounting for startup pulses and the fuse curve. A 7.5A fuse does not guarantee rapid clearing from a supply whose current may limit below that level; the adapter's actual overload behavior has not been verified. A fuse is not an overvoltage protector. [I]

The 12V/6A label gives a nominal 72W envelope, not proof that four motors plus electronics fit it. Nor is four times the motor phase-current rating the correct DC input-current estimate for chopper drivers. Measure one station at the chosen current/speed/load, then validate aggregate steady and transient demand with margin. [F]

## 6. Homing input quality

Keep COM to ground and NC to HOME. An open wire reads like a pressed switch, but a short to ground masks a press; the input is not fully fail-safe. In firmware, latch a stop on the first credible opening and require a deliberate re-arm, with a stable released state before resuming. Do not add a long debounce delay before stopping toward the bead. Any filter delay belongs in the stopping-distance budget. Pair the short signal wire with its ground and separate it from motor wiring.

A newly identified qualification gap: the KW12-3 listing's AC 5A rating does not establish reliable switching at approximately 0.4mA and 3.3V. Manufacturer switch guidance distinguishes power contacts from contacts intended for small signals. The user has demonstrated operation, so this is not a reason to discard the switch immediately; test repeatability at actual current and obtain its minimum-load/contact data before claiming long-term reliability. A stronger pull-up alone is not proof of adequate contact wetting. [J]

## 7. Firmware and failure behavior

The provided bench sketch's 5us HIGH pulse and ~20ms interval exceed A4988 STEP minimum timing, and its delayed first step gives direction setup time. No obvious pulse-timing error explains the observed no-motion result. Completion only means commands were issued. [A]

USB operation with JP1 open can still energize the controller and driver logic while VMOT is absent. That is a valid staged test, but the program cannot know VMOT is missing without additional sensing. The measured 0V at VMOT was therefore important evidence, not a software diagnosis.

The sketch is deliberately unsuitable for suspending a claw: it disables outputs after each jog or stop. R1's default-off action also removes torque during controller reset. Do not call this mechanically safe merely because it is electrically predictable. Current firmware is a bench tool; a suspended system needs a defined supported parking/recovery behavior, coordination across stations and no automatic continuation after reset. The previously deferred brake discussion is not silently reinstated as a bench purchase requirement.

## 8. Best configuration by stage

| Option | Fit to this project | Decision |
|---|---|---|
| Existing A4988/C3/local buck with checked wiring, capacitor, R1-R4 and JP1 | Least rework; clear bench diagnostics; uses purchased parts | Recommended present baseline after fault isolation |
| Separate 3.3V regulator only for driver logic | Extra regulator for a small load; does not address shared-ground or gross miswiring faults | Not justified now |
| Optoisolators on short local STEP/DIR wires | More power/interface complexity; does not inherently stop a bad power rail | Not justified now |
| Different stepper driver | Could improve noise/current/diagnostics, but motor requirements and existing carrier condition are still unknown | Do not replace solely because VMOT read 0V |
| Protected fixed regulator + designed power-path/connector PCB | Better repeatability and fault containment; requires component/layout qualification | Preferred later station revision |

## 9. Prioritized closure plan

1. **Find the existing fault with the suspect controller isolated.** Inspect the board copper map, polarity and soldering; establish continuity of both returns and trace the absent VMOT feed. Isolate the driver as well if it is loading the logic rail. A USB-only cable is not electrical isolation while other wires remain attached.
2. **Verify power stages independently.** Supply, fuse chain and unloaded buck first; then appropriate test load/current-limited source if available. Record output under load, not only pot position. Keep a replacement controller out of the unknown circuit.
3. **Confirm motor and driver settings.** Need motor label/current, Rsense markings and calculated Vref. Check coil pairs and carrier orientation. No universal Vref released.
4. **Commission one unloaded station.** Power and logic readings, waveform checks if needed, jog in both directions, switch opening, reset with outputs disabled, thermal observation. Inspect rather than deliberately creating shorts.
5. **Qualify long-wire and room operation separately.** Wire/fuse selection, four-station power, voltage transients, camera/encoder calibration and controlled supported-load tests.

Open questions needed to complete the hardware release: clear photographs of both perfboard sides and carrier orientation; motor model/rating; Rsense values; exact buck model; wire gauge/material and fuse types; whether the suspect XIAO ever heated fully detached from all external wiring. These are specific missing facts, not reasons to keep redesigning the signal circuit.

## Sources and evidence boundary

Primary documents checked October 17, 2026; calculations above are engineering deductions, not empirical performance claims. ESP32-C3 datasheet pages 16-18 and 55 were also read locally. A4988 carrier guidance applies as a reference, not a guarantee of an unbranded carrier's component values. This review did not run a SPICE simulation or perform physical measurements.

- [A] Allegro A4988 datasheet, electrical characteristics and interface operation: https://www.pololu.com/file/0J450/A4988.pdf
- [B] Espressif ESP32-C3 datasheet v2.4: https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf
- [C] Seeed XIAO ESP32C3 guide: https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/
- [D] Seeed board schematic: https://files.seeedstudio.com/wiki/XIAO_WiFi/Resources/Seeeduino-XIAO-ESP32C3-SCH.pdf
- [E] DROK matching buck family: https://www.droking.com/10pcs-dc-buck-converter-5v-voltage-regulator
- [F] Pololu A4988 carrier documentation: https://www.pololu.com/product/1182
- [G] TI, motor-drive electrical overstress, bulk capacitance and TVS selection: https://www.ti.com/document-viewer/lit/html/SSZTBS1/GUID-4E20E0C2-9D92-42A8-B86E-D05394FAD546
- [H] TI TPS25947 family, function reference only: https://www.ti.com/product/TPS25947
- [I] Littelfuse Fuseology Selection Guide: https://www.littelfuse.com/assetdocs/fuseology-selection-guide?assetguid=fa4aa360-f6c4-4eec-88a6-3d7ec3fe57d5
- [J] Omron/Aratas switch microload guidance: https://components.omron.com/us-en/faq/switches/FAQE20012
