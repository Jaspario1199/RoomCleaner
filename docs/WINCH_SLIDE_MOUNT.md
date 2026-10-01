# Removable winch dock: first bench revision

The complete winch slides down into a separate wall dock. Two channels capture its rear adapter against outward pull. A bottom ledge supports downward load. One accessible M3 screw into a captive metal nut blocks upward disengagement. Install this screw every time; friction is not retention. Disconnect power and unload the cables before removing a station. A slack independent safety tether is required for initial suspended tests.

## Dimensions and interface

All dimensions are millimetres. Wall plate: 150 wide ×190 high ×6 thick. Two channels: 120 long, 7 thick outer walls, 6 thick retaining lips with 5.8 nominal overlap on each adapter edge. Adapter tongue:135.6×119.6×6. Channel side clearance:0.2 each side; thickness clearance:0.6 each side. Bottom-stop gap:0.2. Printed dimensions must be verified with a fit coupon or one dock/adapter pair before making four.

The case sits 24mm forward of the wall. Its original112×150 envelope and all internal components are preserved. Use the supplied **base_slide_version** instead of the original base; it adds four M3 holes at X±25/Y±60. The adapter attaches before closing the case. There are no mounting loads through the cover.

Allow at least125mm upward lift for rail disengagement and sufficient space for the station to move outward afterwards. Validation samples0–190mm of vertical lift every5mm. Keep wall wiring outside this path.

## Hardware per station

- Four M3×20 low-profile socket screws, head diameter≤6mm and height≤3mm, plus four M3 nuts in rear hex pockets. No washers in recessed seats. Screw tips remain inside the docking gap nominally; verify actual fasteners.
- One M3×20 lock screw, one washer and one M3 nut in the wall dock's side-loading nut pocket. Lock screw is at X0/Y84, above the case outline, accessible with the cover fitted. Thread it into the nut before wall installation to confirm fit.
- Three wall screws on X0 at Y−78/0/+78. CAD has5.4mm shank clearance and11mm diameter×3mm head recesses. Actual screw SKU, length, head fit and embedment depend on measured wall construction. Fasten into a structural stud or equivalent qualified backing; this CAD does not qualify drywall anchors.
- One independent slack safety tether for suspended bench tests; attachment and hardware must be qualified separately.

## Printing and assembly

PETG is the starting material; use at least6 perimeters and generous solid regions at channels, stops and bolt seats. Exported STLs lie on their flat rear faces. Rail lips and captive nut pockets create bridges/overhangs: inspect slicer supports and remove all channel obstructions. Avoid PLA for a long-term continuously loaded dock. Material choice is not a load rating.

Print one dock and adapter first. Check sliding without forcing, captured nut retention and full engagement. Secure adapter to the replacement base; assemble the original station; screw dock to structural backing with the station removed. Lower the station fully onto its stop, insert the lock screw and connect the slack tether before connecting cables.

## Verification and remaining qualification

Automated checks cover valid single-solid print parts, STEP volume round trips, adapter clearance against station components and sampled vertical removal clearance. They do not establish strength, creep life, impact resistance or wall fastening capacity. No physical load rating is assigned.

Before overhead use, measure maximum cable tensions and their resultant force/torque at the station, including motor stall and snag scenarios. Define a proof load from that envelope and test at floor level with a restrained dummy load. Check rail spreading, lip/root cracks, base bolt pull-through, lock screw loosening and permanent deformation. Repeat sustained-load and removal-cycle tests. Do not use a hand-pull test as a certified load rating. If the printed rails deform or creep, increase sections or use metal rails/backing rather than treating a passed fit test as a strength test.

This pack replaces only the mounting interface; original winch components and encoder/homing bench qualification requirements still apply. No hardware has been ordered by this update.
