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
