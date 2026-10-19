# RoomCleaner V3 - compact gripper gear module

Status: CAD fit-review prototype, 18 October 2026. NOT a print-release or payload-rated assembly.

## Scope and reference
The supplied Gripper_gear_housing.STEP measures 100 X 90 X 50 mm and contains one solid. It is used as an approximate HALF-housing envelope, as requested, not an exact mating part. The new case is 112 X 112 X 96 mm (lower servo bay 46 mm, upper stack 50 mm). Output flanges project to Z56.5, so the actual non-exploded assembly envelope is 112 X 112 X 102.5 mm. Dimensions in millimeters. This revision contains the servo, reduction and jaw synchronization gearbox, housing, output flanges, shafts and representative fastening hardware. It does NOT contain the final jaw shapes, TPU pads, extension tube, battery, camera or ESP32. No original uploaded geometry was modified. Installing this gearbox into the original shell would require shell changes.

## Why this layout
A module 1.5, 18:54 single-stage reduction retains relatively coarse PETG teeth. Placing the motor diagonally packs the 84 mm gear and 30 mm pinion into the square envelope. Replacing the old 36:36 synchronization stage with 24:24 gears reduces jaw-axis spacing from 54.3 to 36.3 mm. Increasing synchronization face width to 20 mm mitigates its higher tooth force. It is not a proven global optimum. Alternatives considered: module 1.0 would reduce diameter but raise root stress at equal width; a two-stage reduction adds shafts/backlash; herringbone complicates printing and axial alignment without demonstrated need here.

## Primary geometry and rationale
| Feature | CAD value | Reason/status |
|---|---|---|
| Tooth profile | 20 degree involute, spur | Simple flat printing, no intentional axial tooth thrust |
| Module | 1.5 | Coarser roots than module 1.0 in the same tooth-count scheme |
| Reduction | 18:54, 3:1 | Torque multiplication; 105 degrees servo gives 35 degrees jaw travel |
| Reduction face width | 16 | Lowers estimated pinion bending stress versus 12 mm |
| Synchronization | 24:24, 1:1 opposite rotation | Compact 36.3 mm pivot spacing |
| Synchronization width | 20 | Allows for asymmetric jaw contact; stress not verified allowable |
| Gear OD, 18/54/24 | 30 / 84 / 39 | m*(z+2) |
| Pitch diameter, 18/54/24 | 27 / 81 / 36 | m*z |
| Root diameter, 18/54/24 | 23.25 / 77.25 / 32.25 | m*(z-2.5), full depth |
| Addendum / dedendum | 1.5 / 1.875 | Standard full-depth proportions |
| Root blend radius | 0.40 | Smooth analytic tangent blend, NOT a generated hob trochoid |
| Tooth thinning | 0.10 per gear at pitch circle | 0.20 nominal pair backlash before center offset |
| Actual reduction center spacing | 54.30 | Nominal 54.00 + 0.30 trial print allowance |
| Actual sync center spacing | 36.30 | Nominal 36.00 + 0.30 trial print allowance |
| Gear lightening | Eight diameter-12 holes on radius 27 | Removes web material while retaining about 5.6 mm to root circle |
| Closed clocking | 54T:0, left24T:0, right24T:7.5, pinion:10 degrees | Tooth/gap phasing at the diagonal and horizontal meshes |

The combined tooth thinning and center-distance increase produces approximately 0.42 mm tangential backlash per mesh using the first-order expression 0.20 + 2*0.30*tan(20 degrees). This is a loose prototype allowance, not precision gearing. It can create roughly degree-scale output lost motion across both stages. Fit coupons and a short mesh test should determine whether to reduce the allowance. Do not remove it solely for appearance.

## Coordinate and stack definition
XY is the gear plane; Z follows the shafts. This is a CAD coordinate convention, not a finalized installation orientation. The housing footprint runs X=-64..48 and Y=-56..56.

| Axis or fastener | X | Y |
|---|---:|---:|
| A: driven / first jaw | -18.150 | 5.000 |
| B: second jaw | 18.150 | 5.000 |
| C: servo / pinion | 20.245898 | -33.395898 |
| Case screw 1 | -59 | -48 |
| Case screw 2 | 43 | -48 |
| Case screw 3 | -59 | 48 |
| Case screw 4 | 43 | 48 |

| Component | Z range | Reason |
|---|---|---|
| Servo bay | -46..0 | 43 mm usable reference servo depth, 3 mm floor |
| Deck | 0..4 | Screw/bearing support; underside servo lands to -7 |
| Left lower thrust washer | 4..5 | Separates rotating reduction gear from deck |
| Reduction gears | 5..21 | 16 mm face |
| Synchronization gears | 21..41 | 20 mm face; contiguous compound gear avoids an unsupported overhang |
| Right lower spacer | 4..21 | Raises right gear to synchronization plane |
| Output hub journals | 40..51 | One mm overlap with gear, upper-cover radial support |
| Output upper thrust spacers | 41..45.5 | Leaves 0.5 mm nominal axial space below cover |
| Pinion journal | 21..50 | Upper radial support, diameter 12 |
| Pinion upper thrust sleeve | 21..45.5 | Leaves 0.5 mm axial space below cover |
| Cover | 46..50 | 4 mm support plate |
| Output shim | 51..51.5 | Spaces flange above hub |
| Output flange | 51.5..56.5 | Jaw attachment outside cover |
| Steel pivot pins | -2.5..47.5 | 50 mm cut length; captured between deck seat and blind gear bore |

## Fits, structure and secondary dimensions
All printed fits are nominal CAD starting values, not achieved printer tolerances. Steel pins are stationary; gears rotate on them. The cover supports the diameter-24 rotating output journals, indirectly supporting the upper pivot system. This is a printed plain-bearing prototype, not a rolling-bearing assembly. Its friction and wear need testing. The pinion uses a diameter-12 upper journal and a matching servo horn at its lower end; do not assume the servo output can carry unlimited gear side load.

| Detail | Nominal CAD dimensions | Justification or limitation |
|---|---|---|
| Case outer / inner footprint | 112 / 106 square, radius-5 corners | Nominal 3 mm walls, rounded exterior |
| Floor | 3 | Prototype shell stiffness; no stress validation |
| Deck and cover | 4 | Material around supported shafts and screw lands |
| Screw towers | diameter 9 | Surround M3 case fasteners |
| Case clearance holes | diameter 3.4 | M3 clearance |
| Heat-set insert pockets | diameter 4.6, depth 6 | PROVISIONAL; match actual M3 insert supplier before printing |
| Output pins | diameter 8 X 50 steel, quantity 2 | Captured stationary pivots, no shaft torque transmission |
| Deck pin seats | diameter 8.10, depth 6.5 | Light locating fit; coupon before full print |
| Gear pin bores | diameter 8.30 | 0.30 diametral sliding allowance |
| Output journal / lid bore | diameter 24 / 24.40 | 0.20 radial clearance, coupon required |
| Pinion journal / lid bore | diameter 12 / 12.30 | 0.15 radial clearance |
| Upper thrust spacer OD/ID | 30 / 24.40 | Replaceable rubbing surface, no bearing preload |
| Pinion sleeve OD/ID | 18 / 12.30 | Upper axial stop with journal clearance |
| Lower spacers OD/ID | 14 / 8.30 | Keeps teeth away from deck |
| Output flange | diameter 34, thickness 5 | Interface only; actual jaws not supplied |
| Flange-to-hub bolts | 2 holes diameter 3.4, X=+/-8.5 | M3x10 bolts into radial captive nuts |
| Flange head pockets | diameter 6, depth 2.5 | Recess M3 socket heads; check actual head height |
| Jaw mounting holes | diameter 3.4, Y=+/-12 | 24 mm spacing, M3 through-bolt interface |
| Hub nut pockets | 5.8 across flats X 2.6 high, Z44..46.6 | M3 hex nuts, side insertion before lid |
| Flange center access | diameter 6.5 | Access/relief; not an 8 mm shaft passage |
| Output shim | diameter 24 X 0.5, matching bolt holes | Can be printed or replaced by cut shim |
| Servo body envelope | 19.7 X 40 X 36; body Z-43..-7 | Approximate reference, not manufacturer-verified mounting CAD |
| Servo deck opening | 21 X 41.5 | Body insertion clearance |
| Servo land pads | 26 X 10 X 7 | Four recessed mounting screws, access before installing pinion |
| Servo tab hole centers | X=Cx+/-5; Y=Cy-13.5 and Cy+33.5 | 10 X 47 pattern, provisional |
| Servo screw slots | length 6 X width 3.4, along Y | Adjust hole position; not a substitute for measuring tabs |
| Servo head recess slots | 9 X 6.4; floor Z-3.5 | Keeps screw heads below rotating hub |
| Pinion hub/deck clearance | diameter 28 / 28.6 | Prevents original hub/deck collision |
| Horn pocket | diameter 25.3, depth 2.7 | For <=25 mm round horn; actual horn UNMEASURED |
| Horn reference | diameter 25 X 2.5, center diameter 6 | Envelope only; spline teeth not modeled |
| Horn bolt slots | four 6 X 3.3 radial slots, centers radius 8.5 | Hole-center travel radius 7.15..9.85; check actual pattern |
| Pinion central access | diameter 6.5 through | Access to horn retaining screw; no printed spline press-fit |
| Lightening windows | centers (-35,-28), (8,37); 34X24 and 46X18, R3 | Keep material at journals and screw lands |
| Lower ventilation | eleven 38X2 slots, R0.8, X=-30 | Reduces material and ventilates; not a sealed enclosure |
| Gear-bay ventilation | 16X2 slots, R0.8, front/back; 3 columns, 5 rows | Short bridge spans, no 60 mm unsupported slot bridges |
| Cable exit | 10X5 opening through rear wall | Servo lead passage; add grommet/strain relief |
| Strain relief holes | diameter 3.4 at (Cx+/-8,-48) | Tie-loop points; route away from gears |

## Bending calculations and limits
Reference input T=1.0 N m =1000 N mm, illustrative load multiplier K=1.5. These are design assumptions, not measured maximum torque or an established safety factor. Lewis stress sigma=K*Ft/(b*m*Y), Ft=T/r. For the pinion Y18=0.29327 and sync Y24=0.33056 (20 degree full-depth reference table).
- Pinion: Ft=1000/13.5=74.07 N; sigma=1.5*74.07/(16*1.5*0.29327)=15.79 MPa.
- Sync, balanced jaws: transmitted torque approximately 1500 N mm; Ft=83.33 N; sigma=12.60 MPa.
- Sync, all ideal output torque transferred to second jaw: 3000 N mm; Ft=166.67 N; sigma=25.21 MPa. This asymmetric case matters.
- Tangential forces ignore losses for the sizing screen. Separating force is approximately Ft*tan(working pressure angle), about 29 N at the pinion and 66 N at the worst-loaded sync mesh.
- At 90% assumed reduction efficiency, 1 N m input gives 2.7 N m total output torque, NOT 2.7 N m at each jaw. At a 40 mm normal lever arm and symmetric ideal split this is 33.75 N per jaw before synchronization losses. Jaw geometry and friction are not defined, so no payload rating follows.
- 105 degrees servo travel produces 35 degrees at each output, opposite directions. Torque rises with reduction while angular speed and available travel fall.
- Lewis is a screening method only. Custom fillets, print orientation, temperature, porosity, wear, contact stress and PETG creep remain unvalidated. No allowable PETG stress or numerical safety factor is claimed. Reference servo stall is not a continuous duty point.

Sources: UNC Charlotte, Bending Stresses in Gears, https://engineering.charlotte.edu/academics/senior-design-program/rd-and-consulting/engineering-toolkit/mechanical/gears/bending-stresses-in-gears/ ; TowerPro MG996R reference, https://towerpro.com.tw/product/mg996R/ . Owned Deegoo servo performance may differ. The earlier pasted load-dependent formula for Lewis Y is not used.

## Hardware and assembly sequence
Proposed hardware, NOT an order-status claim:
- MG996R servo: 1, existing; matching round horn: 1, actual dimensions must be checked. Supplied cross horns are not necessarily compatible with the round pocket.
- Ground/smooth steel pins diameter 8 X 50: 2; deburr ends. No shaft machining or D-flat required.
- M3x60 socket screws: 4, case stack. M3 inserts nominal OD4.6 X length5.7: 4; verify actual insert geometry. These long screws pass through the lid, gear bay and deck into the lower case.
- M3x10 servo screws: 4 and M3 nuts: 4, subject to measured tab thickness.
- M3x10 flange screws: 4 and M3 nuts: 4. Flange screw heads can project 0.5 mm above the shallow pockets; the jaw mating part must relieve them.
- Horn-to-pinion fasteners and OEM center screw: select only after measuring horn thread, thickness and screw engagement. The central screw must not bottom in the servo shaft. These are intentionally not modeled as finalized hardware.
- Jaw attachment screws: sized after jaw thickness is defined. Printed parts 08,09,12 each require two copies; other functional parts one each.

1. Print fit coupons and servo deck first. Confirm horn pocket, journal clearances, insert pockets and servo tab pattern. Do not force a tight bearing fit.
2. Install heat-set inserts into lower case; ensure no plastic protrudes into mating planes. Keep metal parts and screws away from the electronics during heating.
3. Mount servo under deck using recessed screws and nuts; screw heads must remain below Z0. Route lead through the side opening and tie it at the relief points.
4. Put the two steel pins in deck seats. Add left 1 mm and right 17 mm lower spacers.
5. Center servo electrically with mechanism detached. Attach matching horn with its proper OEM center screw. Set pinion and compound gears to the provided closed clocking, then install horn-to-pinion screws of verified length.
6. Slide compound gear and follower onto pins, engaging both meshes. Insert output-hub captive nuts from the side. Add upper thrust rings and pinion sleeve.
7. Seat deck and gear bay on lower shell. Fit lid over rotating journals. Install four M3x60 case screws without distorting the cover. Check by hand for free motion before power.
8. Add 0.5 mm output shims and flanges, then M3x10 screws. Tighten into nuts, not directly into printed plastic. Add actual jaws using their two-hole interfaces after defining the jaws.
9. With no payload, jog a small angle first. Confirm correct direction, no binding and no heating; then expand toward the 35 degree output envelope. No mechanical end stops are modeled. Do not drive a servo against a jam or use continuous stall as grip control.

## Printing and validation
Use PETG for structural parts. Gear teeth and tooth roots need solid local material, with 6 perimeters as a starting point and 0.20 mm layers; infill elsewhere is a slicer choice, not a verified strength basis. Print gears flat with shafts vertical. The contiguous compound gear avoids the previous unsupported gap between its two gear levels. The underside horn pocket may need local removable support. Flip the motor deck so its flat top face is on the bed; this puts the underside mounting lands upward. Shells, spacers and flanges print on their flat faces. The exported STL positions normalize Z only; they do not automatically flip the deck. Use a fit coupon before the large print.

The JSON report records sampled BREP collision checks for gear meshes and moving gears against deck/case/lid at 0,5,10,15,20,25,30,35 degrees. Zero overlap at samples does not prove zero interference at every intermediate angle, correct contact stress, fatigue life, physical fit, or usable grip force. Review notes and supplemental verification for exact results. STEP contains separate parts but no native SolidWorks mates. Fix the deck; mate pins coaxially; leave rotating gears with revolute freedom; use 3:1 reduction and 1:1 counterrotation gear mates. Do not assign independent unconstrained rotations to the compound pair.

Release blockers: measure actual horn/tab/insert interfaces; inspect print and bearing fit; choose final jaw length/opening; test mesh under asymmetric load; measure mass from actual slicer settings; establish temperature/duty limits and grip force. The geometry is a starting assembly, not certified or independently load-validated. Mass optimization remains open: solid CAD volume is an upper-bound solid-material basis, not the expected sliced weight, and hardware/upper electronics must be added separately.
