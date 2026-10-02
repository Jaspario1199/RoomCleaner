# Critical review: removable complete winch, 2 October 2026

Three independent agent reviews covered structural load paths, assembly/hardware interfaces, and homing/printability. This report supersedes the first dock's43-check release claim as a complete-assembly assurance. That check did not include actual fastener support and therefore missed real blockers.

## Defects found and fixed

| Defect | Correction |
|---|---|
| Clearance cut removed entire anti-lift tab | Rebuilt tab after the cut; supported bolt preload with a rear metal washer; test requires lock to block upward movement |
| Adapter bolts lay0.2mm outside its end edges | Moved centers fromY±60 toY±48; checked full nut/head bearing seats |
| Lock screw could bottom in un-drilled dock material | Full through-bore and checked actual20mm shank/nut/head stack |
| Thin6mm wall plate spanned rails to single stud centerline |12mm plate preserving rail plane; exterior root gussets;8mm lips |
| Upper wall-screw access blocked by lock boss | Upper screw moved fromY78 toY68; driver envelope checked |
| Node-tray nuts/tips hit adapter | Rear clearances in adapter, inspected actual fastener stacks |
| Node screw heads hit USB envelope/tray wall | Button heads≤1.7mm without front washers; local tray head reliefs |
| Shared switch tower filled right cartridge bolt passage | Passage cut after all tower unions; longerM3×30 used atX40 |
| Cover screw heads intruded into wall | Continuous head/driver clearance cuts above low shelves |
| Switch cradle screw heads hit switch body/shelf | Upper positions moved toZ63 with taller support/plate; lower slots unused |
| PCB screw head could strike rotating cup screw stack | M3×5 button heads≤1.7mm, no spacers; cap recess reduced to0.5mm, improving tip margin; M2 head≤2mm |
| Outlet backplate socket heads struck holder | Matching carrier head reliefs;Ø5.5mm×3mm head envelope checked |
| Carrier/switch/cup oriented on poor faces | Broad rear faces down for carrier/switch; cup disk down with open skirt up |
| Coupon and instructions had obsolete eyelet/stopper values |15.3mm seat coupon; new authoritative mount release guide |

## Structural calculations: demands, not capacities

Historical15N peak tension used0.45kg old effector plus0.9kg jeans. It is not validated for the extended claw. The software40N statics bound is not a measured tension limit. Internal spool-to-guide forces cancel when considering the whole station; the guide itself can see approximately2T. The station also carries its own weight and motor reaction/operating effects.

Use240N as a conservative provisional bench-proof envelope derived from3×2×40N, pending actual stall/snags, current setting and load measurements. This does not establish safe working load or dictate a safe wall proof procedure for an unknown substrate.

| Screening calculation at240N | Demand |
|---|---:|
| Base-to-adapter offset43mm |10.32N·m moment |
| Adapter top bolt, moment/(2×96mm) plus240/4 |113.75N each |
| Wall offset73mm |17.52N·m moment |
| Wall screw rows−78/0/68, centroid−3.333mm; Σdy²10674.667mm² |122.55N maximum moment contribution |
| Wall screw maximum moment contribution plus240/3 |202.55N combined envelope |
|12mm plate strip, half-load120N,65mm span,120mm effective width |2.71MPa nominal bending |
| Same plate strip,20mm localized width |16.25MPa nominal bending |
| Old6mm plate, same120mm strip |10.83MPa nominal bending |
| Rail lip,120N per side,4.8mm overhang,8mm thickness,120mm width |0.45MPa nominal bending |
| Rail lip with20mm localized width |2.70MPa nominal bending |
| Bottom stop,240N at15mm lever,140mm width,8mm root |2.41MPa nominal bending |
| Anti-lift web36×3mm,240N in plane |2.22MPa nominal tension |
| Lock hole bearing,3mm bolt×6mm pad |13.33MPa nominal bearing |
| Lock tab two end ligaments,4.1mm×6mm each |4.88MPa nominal shear |

Strip bending uses6FL/(bt²). Fastener figures independently combine component maxima and deliberately overbound a single240N force vector. The plate/rail real contact distribution, stress concentrations, plastic anisotropy, temperature, creep, purchased screw capacity and stud pullout are unknown. No allowable stress, factor-of-safety rating or fatigue certification is asserted. A cosmetic fillet or a collision test cannot substitute for those inputs.

## Automated verification

- `python -m cad.winch_bench`: connected/valid printable solids, STEP round-trip volumes and baseline mechanism checks.
- `python -m cad.export_bench_prints`: oriented STL generation; reference hardware excluded from released print folder.
- `python -m cad.winch_slide_mount`: connected solids, STEP round trips, sampled full upward extraction.
- `python -m verification.check_winch_slide_mount`: bearing support, actual M3 case/lock stacks, upward/downward/outward retention, wall/lock driver access and complete extraction with case bolts.
- `python -m verification.check_winch_fasteners`: explicit motor/cartridge/node/cover/switch/encoder/outlet/cap fasteners, intentional thread interfaces, cup head sweep and collar stroke clearance.
- `python -m verification.check_winch_bench`: component pairs, homing approach/stroke, rotor envelope and cover removal.

Final results:43 mount-generator checks +1,969 functional mount checks +2,005 winch-fastener checks +2,735 mechanism/cover checks = **6,752 passed nominal CAD checks**. Printable solids are valid and connected, STEP volumes round-trip, and the release ZIP integrity test passed. Results are included in the release ZIP. Sampling is not a continuous-motion mathematical proof. Fastener envelope tests do not model real threads, tolerances, pilot tapping torque or actual received component revisions. Most importantly, homing lever pivot/operating force and real wire flex are not known from the switch body dimensions.

## Remaining gates before installing overhead

1. Actual spring/shoulder-guide/stop hardware and real switch trip/release before hard stop, including repeated oblique bead returns.
2. Ronstan ring capture/groove seating; cartridge/backplate pull and repeat load without cracking or loosening.
3. Actual shaft fit, motor bearing/runout and spool/grub/cup retention; rotation field valid through360degrees; no PCB/cup rub.
4. Printed rail fit, head/nut stock dimensions and intact bearing seats; installed lock stops lift and does not distort tab.
5. Exact structural wall screw SKU, head shape, length and embedment in measured substrate; actual station mass and load envelope.
6. Restrained low-height proof load, sustained-load/creep inspection and repeated mount/removal cycles. Add independent slack tether for initial suspension.

Release decision: **one complete bench-fit station can be printed after reviewing its sliced supports. Four installed or unattended stations are not qualified.**
