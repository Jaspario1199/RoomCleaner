# One complete removable winch: revised bench-print release, 2 October 2026

**Print one bench-fit station, not four installed stations yet.** This release corrects confirmed CAD and assembly defects in the first slide dock. It defines the nominal housing, motor/spool, encoder, stationary KW12 mounting, moving homing collar and wall dock. It is not a certified overhead load rating. Actual component fit, spring/guide selection, electrical switch trip and physical mounting proof remain gates.

Use this document instead of the historical BENCH_PRINT_AUDIT and first slide-dock pack. The historical ORDER_STATUS_V2 worksheet still describes older cap hardware; use the fastener table here for this release. The ZIP includes current STEP files, individually named bed-oriented STLs, the complete assembly and validation results. Hardware-reference geometry is excluded from the print folder.

## Corrected load path

External cable → stationary Ronstan outlet/cartridge and motor bracket → structural base → four through-bolts → case adapter → captive side rails/bottom stop → thick wall plate → structural stud screws. Cover and electronics holders carry no cable load. The M3 locking bolt prevents upward release; the rails carry normal outward pull. Unload cables and disconnect power before removal.

The dock now has a160×190×12mm wall plate, two120mm-long channels,7mm side walls,8mm retaining lips and exterior triangular root gussets. The adapter tongue is135.6×119.6×7.8mm; each edge overlaps its lip4.8mm. Nominal clearances are0.2mm per side and0.6mm on both front/back faces. The bottom-stop gap is0.2mm. These are CAD gaps, not measured printer tolerances.

Four case bolts are atX±25/Y±48, safely inside closed nut seats. Their nominal M3 nuts are ordinary2.4mm-thick hex nuts; **nyloc nuts do not fit these pockets**. Old direct-wall holes in the base are filled. Two adapter clearances accommodate node-tray nuts/tips. Case base Z0 is30mm forward of the wall; outlet axis Z43 is73mm forward of it.

The rebuilt anti-lift tab is36mm wide, with a3mm connecting web and a further3mm pad around the lock hole above the case. A0.5mm metal washer between the dock boss and tab supports locking-bolt preload; another0.5mm washer sits under its head. Fit both washers. Do not tighten an unsupported tab across a gap. The locking bolt is atX0/Y84, accessible with the case closed. Wall screws are onX0 atY−78/0/+68; moving the upper screw clears the lock boss. Allow at least125mm of upward travel above the assembled station, then room to withdraw it.

## Current dimensions

| Interface | Nominal CAD |
|---|---|
| Base / cover |112×150×6mm base; cover frontZ74.4 |
| Motor |42.3mm face;38mm body alongX;31mm mounting pattern;22mm locating boss;5mm D shaft,0.5mm flat;24mm shaft projection |
| Spool |20mm core;26mm winding width;36mm flanges,3mm each;32mm total;5.2mm nominal D bore |
| Shaft engagement |17.5mm, cantilevered spool; no outboard bearing |
| Magnet |D42DIA,6.35×3.175mm; cup hole6.55mm; adhesive only on magnet |
| Cap retention |Three M3×5 button screws;0.5mm-deep head recess; no spacers;2.325mm nominal pilot engagement;0.675mm nominal screw-tip margin inside flange |
| Encoder |Grove101020692;41×24×1.6mm conservative board envelope; three M2 screws; chip faceX41.175, magnet faceX39.675,1.5mm nominal gap |
| Encoder head clearance |M2 headheight≤2mm/OD≤4mm; revised cap buttonheadheight≤1.7mm leaves0.3mm nominal axial clearance to the lowest PCB screw |
| Homing |KW12 body20×10.5×6.5mm; collar bore18.6mm; stopper24mm×8;2mm collar stroke; schematic0.7mm initial gap/1.3mm roller displacement |
| Outlet |RonstanRF8090-05,15mm OD/5mm ID/7.5mm axial reference;15.3mm printed seat; actual flange/groove profile must fit |
| Return mechanism |Two shoulder guidesØ4×12mm with M3×6mm threads; two springsOD≤7.4/ID≥6.4mm, installed7→5mm, solidheight<5mm; actual SKUs/rates unqualified |

The user's supplied motor dimensions are preserved. The5.2mm bore is a nominal clearance fit and needs printer/shaft checks; do not describe it as a guaranteed press fit. D-flat and grub screw provide retention. Measure line diameter and stopper knot fit before line installation.

## Fasteners per station

Head dimensions below are maximum envelopes, not supplier tolerance guarantees. Measure purchased parts. Use ordinary2.4mm M3 nuts where modeled. A compatible removable threadlocker/locking method must be checked with the actual plastic and fasteners; do not substitute thicker nuts without changing CAD.

| Location | Quantity / fastener | Assembly requirement |
|---|---|---|
| Adapter to base |4×M3×20,4 nuts |HeadOD≤6mm/height≤3mm; no washers in recessed seats; install before motor/node |
| Anti-lift lock |1×M3×20,1 nut,2 washers |Each washerOD≤7mm/ID≥3.2mm/thickness0.5mm; one supports back of tab, one under head |
| Motor bracket |4×M3×10 |HeadOD≤6mm/height≤2mm, no washer in audited stack; nominal4mm motor thread engagement; confirm allowable depth |
| Cartridge atX0/Z32 |1×M3×25,1 nut,2 washers |0.5mm front/rear washers; rear tower faceY−46 |
| Cartridge atX40/Z32 |1×M3×30,1 nut,2 washers |0.5mm front/rear washers; shared tower rear faceY−42; corrected through-hole |
| Stationary switch cradle |2×M3×12 |HeadOD≤6mm/height≤2mm; use upper positionsX36/48,Z63 only. Lower slots unused; heads there hit shelf |
| Outlet capture plate |2×M3×8 socket screws |HeadOD≤5.5mm/height≤3mm; matching carrier head reliefs; direct printed pilots; inspect ring retention |
| Cover |4×M3×10 |HeadOD≤6mm/height≤2mm; recessed shelves and continuous access bores; use a long slender bit |
| Encoder PCB |3×M2×5 |HeadOD≤4mm/height≤2mm; no washer/spacer; actual board mounting holes must match |
| Magnet cup |3×M3×5 button screws |HeadOD≤6.4mm/height≤1.7mm; no spacers; older M3×6+spacer recipe superseded |
| Node tray |2×M3×12 button screws,2 nuts,2 washers |HeadOD≤6mm/height≤1.7mm; no front washer near USB;0.5mm rear washers only |
| Spool grub screw |M3, length qualified on actual spool/shaft |Radial pilot retained; tip must clamp shaft; outer protrusion≤0.5mm and no rubbing across360° |
| KW12 body restraint |2 small nonconductive ties |Through supplied cradle tie slots; do not crush terminals or restrain roller/lever |
| Homing return guides |2 shoulder guides,2 washers,2 springs,2 stops |Exact stocked hardware and spring rate require bench qualification; printed sleeves are geometry prototypes |
| Wall plate |3 structural wood/stud screws |5.4mm shank clearance;11mm×3mm head recess. Actual SKU/length/embedment depend on measured wall and stud; no drywall-anchor rating |

Uno, CNC shield and12V power supply stay outside this winch in the base station. Only the local encoder node, switch and restrained leads are inside. There is no battery bay in a winch.

## Print and assembly order

1. Print the updated fit coupon, dock/adapter pair, magnet cup and node holder. Coupon now includes the actual15.3mm outlet-seat hole plus M3/shoulder holes; it is not a rail-fit substitute. Check the bought ring, fasteners and magnets before scaling up.
2. Print cartridge, switch cradle, collar and stopper. Carrier and switch cradle STLs now place their broad rear faces down. Supports are still required for local reliefs, horizontal holes and collar fork bridges; inspect the sliced layers. Use the real metal ring for cable/load tests. No plastic eyelet substitute.
3. Secure the KW12 body to its shelf using nonconductive ties through the provided slots; the upper M3 bolts secure the cradle only. Check no rocking and free lever motion. Manually demonstrate electrical trip **before** the2mm hard stop, return without binding, spring coil-bind margin, and repeat at intended cable approach angles. Initial trip margin target≥0.5mm before stop is a bench target, not a measured fact. Change geometry if the real lever differs; do not assume the nominal switch body defines its pivot.
4. Print **base_slide_version**, cover and spool. Original base is not the slide-version base. Dry-fit motor shaft, mounting threads and spool runout. Fit the node tray and rear nuts, then adapter, before installing motor/spool and closing the case. Adapter bolts must be fitted before hardware obstructs driver access.
5. Install motor, spool/grub, screwed magnet cup, encoder PCB and local node. The retained magnet is flush nominally; confirm field validity and runout around360°. Test unloaded encoder direction/ratio and homing. Actual wire plugs/boots/radius require physical fit; route above/away from the rotating parts with strain relief.
6. Complete controlled bench loading before suspension. Screw the empty dock into qualified structural backing, lower case fully, insert both lock washers/bolt and add an independent slack tether for suspended tests. Do not operate an unlocked station or remove it under cable load.

K1/K1 Max bed footprint: largest mount print160×190mm. PETG starting point:0.2mm layers,6 perimeters,40–50% infill with solid local regions for bolt seats/rails/stop; this is not a strength rating. Dock, adapter and base flat backs down. Cover front face down. Spool bore vertical. Cup disk on bed/open skirt up. Clean supports from rail undersides, cover shelves and encoder bosses; check for cracks or layer separation. Review actual support toolpaths and bolt-seat bridges before printing.

## What is still unknown

No CAD or agent audit can promise zero mistakes in printed/hardware assembly. Unresolved gates are exact switch lever/travel/force; real spring/guide/stop SKUs; ring groove seating; actual motor shaft/bearing/thread capacity and spool retention; M3/M2 stock dimensions; printed fits/creep; wire/connector clearances; wall substrate/structural screw embedment; measured assembly mass and motor stall/snags.

The old15N peak calculation used the old1.35kg loaded effector. MAX_CABLE_TENSION40N is a planner value, not tension sensing or a demonstrated actuator capability. Local outlet loading can approach2T; the whole station's external cable resultant is approximatelyT plus station weight, since the internal spool-to-guide cable forces cancel. Use conservative loads for proof, not the historical number as a certificate.

The analytic review uses240N as a **provisional conservative bench-proof envelope** (3×2×40N), not a rated working load or prescribed safe test for an unknown wall. At73mm offset it implies17.52N·m. The revised twelve-mm plate reduces idealized strip bending relative to the old six-mm plate, but printed anisotropy, root concentrations and sustained creep are not validated. See the review report for calculations and limits. Qualify at floor level with restrained test loads and the real mounting hardware before overhead installation; do not use people under the apparatus as a test condition.
