# Fresh mount revision — bench assembly release

Supersedes `MOUNT_PRINT_RELEASE_20261002.md` and its ZIP. Use one station for restrained bench fit and qualification. Manufacturer dimensions improved the model; unknown actual hardware and print properties are still measurements, not facts established by CAD.

**Known design blocker:** the current40° outlet cone does not cover unrestricted movement in the default4×3×2.6m room. This release is suitable for restricted bench fit/homing tests only. Do not print four final stations or treat the room-scanning configuration as compatible. See the angular-workspace appendix in the structural review.

## Changes and reasons

| Finding | Correction | Why this approach |
|---|---|---|
| Shaft blocked the line anchoring hole | Offset chordal Ø1.4 line bore,6mm from axis | Threads with shaft installed while preserving the original spool dimensions |
| M3 grub pilot almost consumed thin flange | Flat-facing one-sided pilot at axial7mm in thick drum; M3×6 recessed2mm | More surrounding material and no screw protruding into cable winding |
| Lowest encoder screw blocked by rotating cup | Separate PCB pedestal with two vertical M3 bolts | Assemble PCB off station, insert whole mount, lift for service |
| Trapped outlet plate and obscured metal flare | Split external groove capture around OEM-derived ring profile | Ring drops into lower jaw; removable upper jaw; metal flare remains exposed |
| Spring stop did not fit selected spring ID | External collar hard stops; no thin printed sleeve inside spring | Leaves spring free on shoulder shaft and stops before coil bind |
| Shoulder screw/spring reference dimensions were generic | Ondrives SHS3-12 and Century Z-2CS envelopes | Published dimensions, tolerances and spring rate replace unspecified hardware |
| Printed guide spacing could bind | One primary round guide and one relieved secondary guide | Reduces overconstraint while retaining collar guidance |
| Cover mesh had zero-thickness edges at roof access holes | Roof openings match continuous6.4mm access bores | Watertight export with head/driver access retained |
| Wall hole/head recess too small | Ø6 passage andØ13×3 head recess | Fits candidate screw major thread/head nominally; does not establish wall capacity |
| Claimed motor torque margin unsupported | Removed margin claim; explicit torque/radius limits | Holding torque is not available running torque |
| Lock-tab gross section ignored clearance notch | Net-section screening and preinstalled rear washer procedure | Calculation and assembly sequence now match actual cuts |

## Current assembly and fasteners

Preserve the preceding release's base/adapter four M3×20 bolts, M3×20 dock lock with two0.5mm washers, motor four M3×10, cartridge M3×25/M3×30 with front/rear0.5mm washers and ordinary2.4mm nuts, switch upper two M3×12, cover four M3×10, node two M3×12 and rear0.5mm washers/nuts, and cup three M3×5 button screws without spacers. Their audited head envelopes remain constraints. Do not substitute nyloc nuts in the shallow seats.

New encoder pedestal: two M3×16 at X48/Y10 and50; head OD≤6,height≤2, no front washer; rear0.5mm washers and ordinary2.4mm nuts. Adapter has Ø8×6.5 rear pockets. Preassemble the three M2×5 PCB screws before installing the pedestal. Unplug its lead and remove the two foot bolts before lifting it. Encoder alignment correction parameters in `winch_bench.py` change the riser relative to its foot; measure first, regenerate and rerun audits after changes. Nominal1.5mm magnet/chip face gap remains a starting value.

Spool M3×6 grub faces the shaft flat and is recessed2mm below the winding surface. Index motor/spool together so the socket faces into the room for tightening, or tighten before motor installation. Thread line through the chord hole with shaft fitted; verify knot retention and smooth edges physically. Winding width26, core20, flange36×3 and total32mm are unchanged.

Homing hardware: two Ondrives SHS3-12, two1mm washers (OD≤7,ID≥4.3), two Century Z-2CS. Installed spring length7→5mm; nominal pair force3.45→6.05N and full-stroke coil-bind margin1.19mm. These are spring calculations, not measured switch return performance. Check both guides slide without binding and switch trips at least0.5mm before the2mm hard stop.

Fit the real Ronstan RF8090-05, never a printed ring, for cable tests. The manufacturer's IGES is open surfaces; a documented revolved profile proxy supports nominal clearance checks. Actual groove fit, retention, wear and angle-of-approach must be checked on the bought ring. Upper jaw: two M3×10 button screws, head OD≤5.7,height≤1.7, at X8.5/31.5,Y−66. Assemble ring and upper jaw before the KW12 cradle and collar. For service remove cover, KW12 cradle, shoulder guides/springs/collar, then jaw screws; lift jaw and ring. A long OD≤4mm driver is required. Nominal40° cable clearance is a collar-opening check, not a verified off-axis bead return or friction limit. The circular outlet accommodates360° azimuth within that polar cone; it does not permit an unrestricted sideways bend. Compare every room pose against the outlet axis before room operation. A near-ceiling approach may exceed this cone; reorient the station or redesign the aperture/guide after measuring those directions. No whole-room compatibility is claimed. The upper groove jaw is the part still named `outlet_backplate` for file continuity; it is not the old trapped plate.

Before sliding onto the wall dock, retain the rear lock washer against the boss with a tiny temporary removable tack outside its bearing surface. Lower the case fully and install top washer/lock bolt. Unload cables before removal. Allow125mm upward travel and forward withdrawal space. Do not leave the lock out during operation.

## Print scope and unresolved gates

Print only the new package's `PRINT_ONE_STATION` folder; old export folders can contain obsolete sleeves/plates. Start with fit coupon, dock/adapter and one homing/encoder set. Updated coupon has2.8/3.4/4.3/6.55/8.8mm holes for pilots, clearance, guides, magnet and groove capture. Use actual final material and inspect slicer support/bridging. Rail lips and roots, pilots and nut seats need intact layers; clearance success does not establish strength. Printed sleeves and plastic ring dummy are excluded from functional hardware.

The exact motor shaft/bearing capacity and running torque curve, switch lever/force/travel, actual fasteners/magnet/PCB fit, wire boots and bend radii, station/loaded-claw mass, cable direction extremes, printer tolerances, material creep, wall substrate and effective screw embedment remain physical gates. Camera/claw geometry is reviewed separately and does not establish autonomous vision/control readiness.

Read `MOUNT_INTERFACE_CONTROL_20261002.md` for datums, sourced dimensions and inspection. Read `FRESH_STRUCTURAL_REVIEW_20261002.md` for vector loads, net sections, material limits and restrained proof/creep/cycle qualification. A planner tension or a provisional240N calculation is not a mount rating. Release for overhead service only after the actual revision is tested with its declared working load and directions.

## Claw correction included separately

The extended claw had an omitted-hardware collision: lower rail heads/nuts occupied upright flange material. Revised left/right uprights have four open-edge Ø8 pockets at X±53/Y±35, leaving nominal4.35mm to adjacent upright clear holes. Use the separate `CLAW_CORRECTION` files for these two parts. Rail stack is M3×30, head≤6×2, two OD≤7×0.5 washers and ordinary2.4mm nuts. This correction and its hardware/tool audit do not qualify the whole claw mechanically: exact servo horn, actuator bolts, electrical connectors, load/mass and extension strength remain physical gates. See the updated extended claw build guide.
