# Claw electronics cost and packaging review — 2026-10-18

Status: researched alternatives and recommendations, not purchased parts or an approved hardware revision. User explicitly reopened the earlier DROK/2S choice to reduce cost, especially unnecessary displays. Keep the previous decision record for provenance. No electrical hardware, CAD, or firmware was changed.

## Findings

| Function | Recommendation | Evidence and tradeoff |
|---|---|---|
| 2S battery | Retain one OVONIC 2200 mAh XT60 pack if proceeding with the existing plan; no spare is necessary for operation | No verified cheaper like-for-like Amazon pack with better supported quality was established. Smaller capacity trades runtime; do not substitute a different cell count. |
| Regulated 5 V for servo and XIAO | Screenless ZTW **6A** UBEC is a compact alternative to DROK 200359, set to 5 V | Manufacturer: 6–25 V input, 6 A continuous/10 A burst, 45 × 23 × 10 mm, 18 g. Amazon listing B071CHGWRM has an inconsistent 5 A bullet; verify received model. Buddy RC reference price $14.99 but sold out; Amazon current price/stock not verified. This is a packaging improvement; price savings versus DROK are not established. Do not substitute the similarly named 8A model without checking its input range. |
| External balance charger | Recommend Gens ace iMars S10 instead of TB6B when lowest initial cost is the priority | Manufacturer $13.99 before shipping/tax, 2–3S LiPo, 0.8 A maximum, standard non-G-Tech packs at 4.2 V/cell, balance connector charging. Requires compatible 5 V / 2 A USB supply (5 V / 1 A explicitly unsupported); reuse a suitable adapter if owned. No selectable storage-charge/discharge function is documented. It trades TB6B storage/discharge/adjustment features for cost and simplicity. |
| Low-voltage disconnect | Display is unnecessary; retain the protection function. No equally well-specified cheaper screenless Amazon replacement qualified in this review | Generic 2S BMS listings commonly give broad 2.3–3.0 V or 2.5–3.0 V cutoff ranges. They are not a verified normal-operation cutoff for the chosen pack. ESP32 voltage sensing alone cannot physically disconnect battery power. Pack cutoff is not cell-level protection. |
| Cell alarm/checker | Optional as a permanently mounted diagnostic; do not remove individual-cell checking/protection capability | The pack ADC measures total voltage, not both cells separately. A charger or meter can perform manual checks; a BMS may provide hardware protection if properly selected. Those alternatives are not all interchangeable. The current bare pack must not be described as having independent per-cell shutdown. |
| Master rocker switch | Can omit if an accessible XT60 is used as the manual disconnect | Stop operation before disconnecting; retain fuse, insulated connections and strain relief. Automatic dock power-path remains separate. |
| Capacitor and ADC passives | Keep servo bulk capacitor and small divider/filter components; use existing suitable stock | These serve electrical functions and occupy little space. Do not buy multiple large assortments for a few parts. |
| Fuse/connectors/wire | Reuse suitable owned parts; do not repurchase holders or XT60s by default | Verify actual ratings and counts. Prior 5 A claw fuse remains provisional, not a universal selection. |

## Alternatives screened out

- Pololu D24V50F5: documented compact regulator, but manufacturer price $32.95 and rationed supply make it a poor cost-reduction choice here.
- Tenergy 31004 protected 2S Li-ion pack: $21.75, 2.6 A continuous, protection cutoff 2.40 ± 0.06 V/cell. Do not confuse with AT31004, a different $44.99 5 A pack. The inexpensive pack is not an unquestioned drop-in for our transient load or a replacement for early low-battery handling.
- Generic B3 chargers and generic peak-rated converters: no verified quality/equivalence established sufficient to prefer over the documented S10/UBEC alternatives.
- Existing MT3608 is a boost converter; it does not replace the required step-down from 2S to 5 V.
- No claim that removing a display makes a module cheaper or more reliable; cost, current capability, low-input operation and support matter.

## Recommendation and remaining boundary

The clearest immediate price reduction is the S10 charger if a compatible USB supply is already owned. The 6A UBEC is substantially more compact than the display regulator, but is only an alternative until price/availability and received identity are confirmed. Do not buy both regulators. Keep 2S battery chemistry/cell count unchanged.

This review does not release a fully screenless autonomous protection system. The cutoff/protection replacement remains unresolved; neither an alarm nor software-only voltage monitoring is equivalent to independent disconnection. Preserve the earlier schematic reconciliation items, including USB/external-power separation, FSR interface, servo signal compatibility, output capacitor placement and load/thermal validation. Earlier mechanical force calculations at 6 V still do not establish 5 V performance.

Charger LED status is appropriate even though a large LCD is unnecessary. The S10 stays off the robot and charges the disconnected battery through its balance lead. It is not the automatic docking charger. Its missing storage mode is a real ownership tradeoff.

## Sources checked October 18, 2026

- ZTW manufacturer specification: https://www.ztwshop.com/product/accessory/2017/0814/ZTW-6A-UBEC.html
- ZTW Amazon listing: https://www.amazon.com/dp/B071CHGWRM
- Reference retail price (sold out): https://www.buddyrc.com/products/ztw-6a-ubec
- Gens ace manufacturer price/specification: https://www.genstattu.com/gens-ace-imars-s10-smart-charger-dc-10w-0-8a-2-3s/
- Grepow manufacturer operating details: https://www.grepow.com/battery-charger/imars-s10-for-2s-3s-lipo-small-batteries.html
- Amazon S10 search (not verified stock): https://www.amazon.com/s?k=Gens+ace+iMars+S10+GEAS10-UB
- Pololu reference: https://www.pololu.com/product/2851
- Tenergy 31004: https://power.tenergy.com/tenergy-li-ion-7-4v-2600mah-rechargeable-battery-pack-w-pcb-2s1p-19-24wh-2-6a-rate/
- Example seller/manufacturer BMS specifications with uncertain thresholds: https://www.diymore.cc/products/2s-5a-li-ion-battery-overcurrent-protection-board-bms-pcm-lipo-cell-pack-18650-bms-pcm-mos-transistor-short-circuit-low-power

No confirmed Amazon checkout prices or delivery dates were available. No complete-system saving total is asserted. Previous design record: [decisions_20261018.md](decisions_20261018.md).

## Later architecture alternative — integrated USB-C power bank

User asked whether battery use/charging could be fundamentally simpler. Proposed direction: an enclosed USB-C PD power bank with its own cell-management and USB charging electronics. This is a candidate architecture, not an approved purchase or validated substitute.

- Removes user integration of a bare 2S pack, separate balance charger and separate battery-side alarm/cutoff modules when the selected power bank provides the required protection. Retain appropriate output wiring/fusing, servo decoupling and mechanically safe behavior on power loss.
- Candidate power path with headroom: USB-C PD power bank supplying a negotiated 9 V / 3 A contract; small PD sink/trigger; suitable 5 V buck regulator; separate servo and XIAO branches. 27 W input at an assumed 90% buck efficiency gives 24.3 W, or 4.86 A at 5 V, as an upper planning estimate limited by every component and transient behavior. It is not a tested output rating.
- Direct 5 V USB power is even simpler only if measured combined peaks fit the available 5 V contract with margin. A 30 W headline does not imply 30 W at 5 V. Use a compliant USB-C sink/interface; do not route servo power through XIAO USB/PCB, parallel bank outputs, or assume a cable splice negotiates PD.
- Anker A1259 is an existence/reference example, not a final cost-optimized selection: official listing $49.99, 215 g, 104 × 52.3 × 26 mm, single-port 5 V / 3 A or 9 V / 3 A, up to 30 W USB-C input. Its own display is not a requirement; a cheaper screenless equivalent can be assessed. It may be simpler without being lighter or cheaper overall.
- Adafruit HUSB238 fixed/jumper PD sink example: $5.95, 24.5 × 20.2 × 4.9 mm, 2.2 g. Configure and verify requested voltage/current; reset/fallback can yield 5 V before negotiation. Keep actuator disarmed during startup and test negotiation loss.
- Normal use: operate from bank; stop and support gripper, disconnect robot output and charge bank through its intended USB input with a compatible wall charger. No exposed cell charging, raw cell wiring, or DIY balance harness.
- Required selection/qualification: servo surge response, cable voltage drop, low-load automatic shutoff, boot/restart behavior, thermal limits and actual mass. Battery percentage/state must be available or runtime managed conservatively before hard cutoff; regulated 5/9 V output alone does not reveal internal state of charge.
- Automatic hook charging remains separate. Do not assume simultaneous input/output, uninterrupted pass-through, automatic wake, or seamless switching. Verify the exact bank for dock integration; a 9 V output trigger is not an input charger or a bidirectional docking interface.
- Prior runtime estimate (2S pack): 16.28 Wh nominal × assumed 0.8 usable fraction × 0.9 efficiency = 11.72 Wh. At 5 V and average 0.5/1/2 A, estimates 4.69/2.34/1.17 hours. These are scenarios, not measured usage. S10 ideal 2.2 Ah / 0.8 A = 2.75 hours plus taper/balancing, approximately 3–4 hours for near-empty equivalent recharge. They do not transfer unchanged to a power bank.

Sources checked 2026-10-18:
- https://www.anker.com/products/a1259-built-in-cable-power-bank-10000mah
- https://www.adafruit.com/product/5807

No hardware, firmware, approved BOM, or purchase status changed in this discussion.
