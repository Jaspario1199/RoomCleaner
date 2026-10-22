# RoomCleaner: decision and trouble stories for the SpaceX panel

Prepared 2026-10-20 from the repository record only (DECISIONS.md, DESIGN_STATE.md,
verification/, calculations/, docs/, solidworks/, git history, photo README).
Nothing here is invented. Where the record does not say what Jasper weighed,
saw or measured, the entry says **NOT RECORDED**. Panel date: Tue 2026-10-27;
draft due Thu 2026-10-22.

## How to read this file

Evidence labels (use the same words on slides: measured / calculated / planned):

| Tag | Meaning |
|---|---|
| **MEAS** | physical measurement or physical test on hardware (a number exists in the record) |
| **REP** | reported by Jasper as a bench observation; no log or photo-with-number in the record |
| **CALC** | hand or script calculation (`calculations/`); inputs are assumptions unless stated |
| **CAD** | geometry measured on a CAD solid (boolean volume, bounding box, clearance probe) |
| **SIM** | simulator only; nothing run on the four-station rig |
| **NONE** | nothing yet |

Provenance tags (for Jasper's private prep; do **not** put these on slides):

| Tag | Meaning |
|---|---|
| **[J]** | the record states it as Jasper's own observation, request, decision or measurement ("user find", "raised by Jasper", "per Jasper", "Jasper confirmed") |
| **[J-sel]** | Jasper selected the direction; the record does not say who did the analysis or drawing |
| **[chk]** | found by a verification report or review in the repo; the record does not say what Jasper himself did. Before telling one of these as a personal story, Jasper must be able to say what he personally saw and decided. If he cannot, drop it or tell it only as "my verification process caught...". |
| **[?]** | who decided is not recorded |

Notes on use:
- Every story is written as "what happened and what was decided". Keep tool names and repo file
  paths off the slides. Some history paths contain tool names; they are cited here for traceability only.
- Dates are the date the record shows (commit date, file folder date, or the date in the document).
  "Undated" means the record gives none.
- Entries are chronological within four eras: **Era 0** concept (Jul 16 to Aug 6), **Era 1** first-generation
  build and bench (Aug 7 to Sep 2), **Era 2** a parallel design stream recorded Oct 1 to 6, and **Era 3** the
  SolidWorks second generation, electrical bring-up, heat and control system (Oct 7 to 20).
- Conflicts in the record to reconcile before the deck is final are in section 4.

---

## 1. Chronological list of design changes and troubles

### Era 0: concept and first order (Jul 16 to Aug 6, 2026)

**T01. Winch motor: stepper instead of self-locking worm-gear DC (2026-07-16)** [?]
- **Trigger:** payload re-scoped from "heavy" to "shirts, pants and jeans, ~2 lb max" (jeans 0.9 kg + 0.45 kg claw = 1.35 kg). The loaded point-mass model gave a peak cable tension of **15 N** across the workspace.
- **Options recorded (HARDWARE.md):**
  - Worm-gear DC + encoder, about $32 each: self-locking so it holds with zero current, true closed loop; slow (10 to 30 RPM). Pro = no drop on power loss. Con = more cost and a PID loop per motor.
  - NEMA 17 stepper: cheap, one shield drives all four. Con = holds only while powered, runs hot, silently loses steps on shock or snag, so position goes wrong with no feedback.
- **Deciding constraints:** light payload where a dropped item is harmless; cost; "~2x torque margin" computed; kill path through a switched power strip.
- **Choice:** NEMA 17. The motor itself changed the same day from a $54 4-pack of 59 N·cm to the SIMAX3D 42-38 5-pack at about $33 (36 N·cm, 1.5 A), stated as ~2.4x the torque the build needs, with a spare.
- **Outcome / evidence:** CALC only at the time. Later consequences, all recorded: holding torque is not running torque (review R10 uses 70 % of holding; a 7.5 mm spool core gives ~24 N, not the 40 N once assumed); motors must stay energised to hold the claw (so the heat story T31); no brake, so disabling a driver drops the load (D21).
- **NOT RECORDED:** which alternatives Jasper himself compared; the worm-gear option is documented as "applies if you scale up".
- **Sources:** docs/HARDWARE.md; docs/BOM_ORDER.md; commits 44edc9f, 5d4304a (2026-07-16).

**T02. Controller and driver: central Uno + CNC shield, then A4988 instead of DRV8825 (2026-07-17 to 08-06)** [?]
- **Trigger:** the Jul 17 pick was a $17 kit with Uno + CNC shield + 4x DRV8825 (DRV8825 "run cooler and drive the 1.5 A motors at full torque"), chosen over a $24 A4988 kit. On 2026-08-06 it was sold out at order time.
- **Options recorded:** ELEGOO UNO starter kit (~$45, extra component library "for future projects") + ACEIRMC CNC shield with 4x A4988 (~$10) (chosen); Sevenmore DRV8825 kit (~$24, "like-for-like budget swap"); HiLetgo DRV8825 5-pack as a full-current upgrade.
- **Deciding constraint:** availability, then cost and reuse of the starter kit.
- **Choice:** A4988 on the shield, set to Vref 0.80 V on R100 sense resistors, about 1.0 A (0.40 V on R050 boards).
- **Outcome / evidence:** MEAS (bench, 2026-08-28): all four drivers confirmed R100, Vref 0.75 to 0.85 V. DERIVED, not stated by Jasper: this swap is why the winches run at about 1.0 A of a 1.5 A rating, which later sets the capacity limit (T36) and the heat load (T31).
- **Sources:** docs/SHOPPING_LIST.md; commits bf79b12, e80cabd; DESIGN_STATE.md "Bench bring-up".

**T03. Gripper concept: five tendon-driven TPU fingers (2026-07-16, D1)** [?]
- **Trigger:** flat or crumpled cloth on a hard floor gives a parallel gripper nothing to close on.
- **Options recorded (docs/RESEARCH.md):** parallel jaws alone (poor); Fin Ray soft fingers alone (poor to fair); underactuated tendon fingers (fair, good paired with a rake); spatula-scoop plus soft flap ("best mechanical", primary pick in RESEARCH.md); needle/pin gripper ("best physics straight down", the fallback); jamming/granular (excluded: needs a vacuum pump).
- **Deciding constraints:** crumpled laundry, one servo, printable parts. D1: "gathers crumpled cloth without needing a pinch feature".
- **Choice:** tentacle fingers (D1, HARDWARE.md). **Record conflict:** RESEARCH.md names the spatula-scoop as the primary; D1 and HARDWARE.md choose the tentacle.
- **Outcome:** CAD only. No print of the tentacle claw is recorded. Superseded in October by the two-jaw clamp (T34, D18).
- **Sources:** docs/RESEARCH.md; DECISIONS.md D1; docs/HARDWARE.md.

**T04. Kill path: switched power strip, not an e-stop and contactor (2026-07-16)** [?]
- **Options recorded:** latching mushroom e-stop with contactor ($22, in the first "reliable" BOM) versus the switched power strip already owned.
- **Choice:** the power strip is the stop ("same job", no extra part). Later formalised as D21: the strip is "the only category-0 stop", and no safety-rated function is claimed.
- **Cost recorded in the design review (R2):** cutting 12 V drops the claw; a deliberate trade of a guaranteed stop over a controlled stop, acceptable only if nobody is under the workspace.
- **Evidence:** NONE (not tested with a load).
- **Sources:** docs/BOM_ORDER.md; DECISIONS.md D21; verification/design_review_gen2.md R2.

**T05. Wireless claw, wired winches (2026-07-17)** [?]
- **Decision:** the gripper runs on an ESP32 over Wi-Fi so only the four cables touch the claw. Grip and release are not time-critical; "the synchronized winch motion stays wired".
- **Why it matters later:** this is the opposite of the October decision to distribute the winch electronics (T26). The July reason (synchronised motion needs one controller) is exactly the cost the October review prices at 2.5 mm per 50 ms.
- **Sources:** commit fd837ed (2026-07-17); DECISIONS.md D17.

**T06. Anchors: closed-eye hooks, then rigid printed corner mount (hooks 2026-07-17; D13 2026-08-07)** [J] ("user request, lead-approved")
- **Trigger:** the hanging hooks (QXSKSLH 5 in M10 stainless closed-eye) made each corner a pivot, so the winch and pulley could swing and the effective anchor point moved. The calibration sensitivity study shows about **1:1 anchor-to-position error transfer**.
- **Options recorded:** keep hooks (cheap; "−$14" removed from the BOM); rigid plate screwed to a joist or high stud. A fuller option list is NOT RECORDED.
- **Deciding constraint:** an anchor must be fixed to be calibratable.
- **Choice:** one printed `corner_mount` plate (6 mm base, motor bracket and pulley ears on one part), three #10 x 3" wood screws in a line into a joist or stud, screws in shear on a wall mount. Load path: motor to bracket to wood; "nothing hangs from the motor or the drywall". Cost: hooks out (−$14), wood screws in (~$8).
- **Outcome:** CAD verified (rev A to D.1). CALC: ears 5.5 MPa worst case at 40 N, SF ~5 against PETG layer adhesion; wall below 0.5 MPa. A printed gen-1 plate with motor, spool, pulley ears and switch exists in photo 05, and a gen-1 station lifting a test weight is in photo 13; no weight, duration or result is recorded.
- **Sources:** DECISIONS.md D13; DESIGN_STATE.md "corner_mount cycle"; docs/presentation/photos/README.md (05, 13).

### Era 1: first-generation build and bench (Aug 7 to Sep 2, 2026)

**T07. corner_mount first-pass defects found before printing (2026-08-07)** [chk]
- **Found:** (1) fleet alignment: the line paid off perpendicular to the pulley groove; fixed by ruling the spool axis parallel to the pulley axle with the drum mid-plane coplanar with the groove plane. (2) Gussets intersected the NEMA 17 body envelope by **70.42 mm³**, so the motor could not seat; fixed with a 56 mm wall and gussets driven off the real half-width plus 2 mm. (3) Several tests only checked nominal arithmetic; replaced with probes of the built solid and boolean regression tests.
- **Outcome:** CAD: both interference volumes 0.000 mm³ after repair; mass 88.76 g (≤ 90 g budget); STEP round trip exact; spool rub gap ≤ 2 mm gives a worst-case fleet angle of about 9 deg (limit 15 deg).
- **Sources:** DESIGN_STATE.md "corner_mount cycle"; verification/corner_mount_report.md.

**T08. Purchasing trade-offs recorded (2026-07-16 to 08-11)** [?]
- Power supply: ALITOVE 12 V 6 A ($16, "headroom") chosen over a UL-listed Chanzon 12 V 5 A ($20); 7.5 A blade fuse "matches the 6 A supply".
- Servo: standard 180 deg positional MG996R, "not 360 continuous rotation"; 4-pack for spares; plastic-gear SG90 rejected ("shears the first time it grips").
- Line: 50 lb braid first (2026-07-17), later 120 lb 8-strand 9KM DWLIFE.
- Effector controller: ELEGOO ESP32 3-pack over a hiBCTR 6-pack (2026-08-11, reasons NOT RECORDED). Plain 8.4 V boost boards rejected as chargers; a 2S balance charger is required (2026-08-11).
- **Evidence:** all are selections; none tested. Line diameter was never measured (T22).
- **Sources:** docs/SHOPPING_LIST.md; docs/BOM_ORDER.md; git log 2026-07-16 to 08-11.

**T09. Parts blocked by missing caliper measurements (2026-08-11)** [J]
- **Trigger:** Jasper's calipers were not available. Two prints were blocked: the tendon drum (MG996R horn outer diameter, thickness and screw-hole spacing set the horn pocket) and the winch spool (motor shaft D-flat across-flat).
- **Handling:** D-flat confirmed visually on the 17HS4401 motors; flat depth 0.5 mm assumed (standard); spool cleared for one fit-test print only. Caliper check (~4.5 mm across the flat) deferred.
- **Outcome:** the flat depth is still described as an assumption in later documents. This is the pattern behind the v2 spool bore story (T24).
- **Sources:** DESIGN_STATE.md "Pending physical measurements"; commit 32b8227.

**T10. Limit-switch polarity bug (2026-08-12)** [chk]
- **Found:** firmware treated LOW as pressed (normally-open logic), but the fail-safe wiring (COM + NC) reads LOW at rest and HIGH when pressed or when a wire breaks. Homing would have zeroed instantly without moving.
- **Choice:** keep fail-safe NC wiring, invert the logic, add an `S` serial command that reports all four switch states.
- **Outcome:** firmware fixed (2026-08-12). Bench plan: `SW 1 1 1 1` before wiring and `SW 0 0 0 0` after. A physical test of the four-switch set is a later phase and no result is recorded.
- **Sources:** commit "Fix inverted limit-switch polarity" (2026-08-12); docs/FIRMWARE.md; docs/BENCH_ASSEMBLY.md.

**T11. Bench instructions audited against firmware and hardware (2026-08-13 to 14)** [chk]
- **Found (two blockers, several majors):** the CNC shield V3 A-axis needs two extra jumpers on D12/D13 (14 total, not 12) or the fourth motor never moves; switches wire to the two pins of one end-stop connector; the A4988 Vref target halves to 0.40 V on R050 boards; the MP1584 trimpot is single-turn and reversed input polarity is fatal.
- **Outcome:** MEAS on the bench 2026-08-28: 14 caps seated, drivers R100, Vref 0.75 to 0.85 V, one motor spun one revolution out and back on X, Y, Z and A (so the fourth channel mapping is proven).
- **Sources:** commit "Fix bench-guide errors found by instruction audit"; docs/BENCH_ASSEMBLY.md; DESIGN_STATE.md "Bench bring-up Phases 1 to 5".

**T12. Controller enclosure: five geometry defects found before printing (2026-08-13)** [chk]
- **Found:** mid-air countersinks (a workplane-centroid trap); USB port rotated 90 deg; lid posts inside the Uno footprint; one Uno hole 1.27 mm off against a KiCad footprint; zip-tie holes merging across the motor-to-endstop port boundary (fixed by flanking in Z, which also removed a 0.75 mm sliver).
- **Outcome:** CAD: two verification passes, 37 tests, tray + lid 135.15 g, PASS. No print is recorded. Assumption on record: CNC-shield connector heights are estimates, absorbed by oversized strain-relieved ports.
- **Sources:** verification/base_station_case_report.md; DESIGN_STATE.md.

**T13. Pulleys: printed guide, then bought bearing pulleys (BOM in July; ruling 2026-08-28)** [?]
- **Trigger:** the early BOM dropped bought pulleys ("printed corner_guide handles 15 N tension fine"). A printed corner guide also had ear walls of **0.15 mm** (unprintable, found in verification).
- **Ruling (2026-08-28):** buy complete U-groove ball-bearing pulleys: 3 mm bore, OD 18 to 22 mm, width under 10 mm, ~10-pack, on M3 x 25 axle bolts with nylocks. A printed sheave is fallback only. Rationale in the shopping list: "Bought, not printed: friction here is position error." Warning: "wrong-bore trap: 5 mm is common."
- **Cost:** pulleys become a required line (~$10 for a 10-pack).
- **Evidence:** CALC for the plate stresses (T06); friction not measured.
- **Sources:** docs/SHOPPING_LIST.md; DESIGN_STATE.md "Camera case, corner pulley ruling"; verification/winch_parts_report.md.

**T14. Overhead camera: bracket replaced by an enclosed case (2026-08-28)** [chk]
- **Trigger:** the board needs protection and a lens opening; the open bracket (`camera_mount_overhead`) left the innomaker board exposed.
- **Choice:** two-piece case: 56 x 56 plate, 24.6 mm skirt, board on 10 mm M2 standoffs (28 mm pitch), O18 lens opening in a screw-on bezel, 45.0 g PETG (60 g budget).
- **Outcome:** CAD: independent verification PASS 52/52; the skirt wall measures exactly the 2.4 mm floor. Open before printing: confirm the 28 mm hole pitch and the lens barrel OD (assumed M12). The later claw-camera direction (T33) makes the ceiling camera a bench reference.
- **Sources:** verification/camera_case_overhead_report.md; DESIGN_STATE.md.

**T15. Bench bring-up and power supply: 18 V on the meter (2026-08-28)** [J]
- **Trigger:** with the plug cut off the ALITOVE brick, Jasper metered the leads (found and taped the +12 V lead), fitted a 7.5 A inline fuse, and the shield terminal read **18 V**, not the nominal 12 V. DESIGN_STATE notes "brick label still to be read".
- **Reasoning recorded:** within the 12 to 36 V shield and 35 V A4988 spec; "never feed the Uno barrel jack from it". No VMOT LED on this clone, so the meter reading is the checkpoint. The splice was twist + duct tape, with a note to redo it with solder and heat-shrink or a lever nut.
- **Open and important:** by 2026-10-14 the supply is identified as 12 V / 6 A / 72 W, and the later station design feeds a DROK buck rated 4.5 to 20 V input from that supply. Whether the 18 V was an open-circuit reading is NOT RECORDED.
- **Outcome:** MEAS (18 V reading); resolution NOT RECORDED. Outline v2 uses this as "I trusted a nominal 12 V until the meter read 18 V".
- **Sources:** DESIGN_STATE.md "Bench bring-up"; docs/SHOPPING_LIST.md; docs/history/startup_decision_20261016.md; docs/electrical/STATION_ARCHITECTURE_REVIEW_20261017.md; SPACEX_OUTLINE.md slide 15.

**T16. Homing switch moved below the pulley; first implementation failed (D14; find 2026-08-28; revs C, D, D.1 on 2026-09-02)** [J] for the find ("user find, lead-approved"); the rev C failure was found by an independent CAD check [chk]
- **Trigger (Jasper's find):** with the KW12-3 switch mid-span, "home = bead between spool and pulley", so the stopper bead had to ride over the pulley groove on every descent and every homing run. The groove is sized for 0.5 mm line; a bead climbs the flanges or jams.
- **Options recorded:** (a) switch mid-span (rev B, boss on the plate; rejected because the bead crosses the groove); (b) switch on a short drop arm beside the vertical line under the pulley (chosen, D14); inside (b): rev C = switch on the arm's vertical face, rev D = switch on a horizontal pad atop the arm.
- **Deciding constraint:** the bead must stay on the vertical span and never cross the pulley.
- **What failed (CAD check, rev C):** the roller sat at X = 70.0 mm against a line at X = 65.0 mm (5 mm from the line centre; a 0.25 mm gap to the edge of a 5 mm bead against ≥ 1.5 mm required overlap) and at Y = −10.5 mm (10.5 mm off). "Wrong by construction": the ±5 mm slot travel could not fix either axis.
- **Fix (rev D):** pad horizontal, roller lands on the line: X error 0.000 mm at the nominal 20 mm pulley and ≤ 1.0 mm across 18 to 22 mm pulleys (0.000 after ±2 mm tune); Y overlap 3.750 mm with a 5 mm bead (≥ 2.0 mm required). D.1: zip-tie groove moved clear of the M2 pilots; r = 3 notch in the corridor.
- **Outcome:** CAD-verified (rev D mass 96.29 g of 105 g). Two minor defects logged as strict-xfail: the pilot wall loses 1.5 mm of its 5 mm depth at the outboard tip, and 1.125 mm³ of printed pad intrudes the corridor. NOT RECORDED: any physical print, or a bead actually tripping the roller on real line. Bead diameter (O5) is a "local assumption"; roller overhang (1.5 mm), rest height (12 mm) and hinged end are assumed ("caliper-verify on a KW12-3 in hand").
- **Sources:** DECISIONS.md D14; DESIGN_STATE.md "corner_mount rev D"; verification/corner_mount_revC_report.md, corner_mount_revD_report.md.

### Era 2: a parallel design stream, Oct 1 to 6 (record = documents dated 2026-10-01 to 10-06)

(Authorship of the analysis in this era is not stated in the documents; user statements inside them are quoted as such. Several documents describe candidate parts and do not prove any part was bought or printed.)

**T17. Bench winch housing: defects found by an adversarial fit review (2026-10-01 to 02)** [chk]
- **Found and corrected:** the shaft blocked the line anchoring hole (fixed with a Ø1.4 chordal bore offset 6 mm from the axis, threaded with the shaft installed); the M3 grub pilot nearly consumed the thin flange (moved into the drum, recessed 2 mm); the lowest encoder screw was blocked by the rotating magnet cup (PCB preassembled on a removable pedestal); a trapped outlet plate hid the metal flare (split groove capture); the spring stop did not fit the selected spring ID (external collar stops); tangent roof holes created non-manifold mesh edges; wall hole and head recess too small; an unsupported "torque margin" claim was removed because holding torque is not running torque.
- **Outcome:** CAD checks (thousands of sampled cases; "sampling is not a continuous proof"). A matched unpowered fit-print kit of 16 main parts was delivered (every part one valid solid; STEP volume delta 0.00007 mm³; ZIP hashes checked). Physical fit results: NOT RECORDED.
- **Sources:** verification/fresh_review_results_20261002.md; docs/FRESH_MOUNT_RELEASE_20261002.md; verification/HOUSING_PROTOTYPE_RESULTS_20261004.md.

**T18. The line outlet cone does not cover the room (found 2026-10-02; explored 10-04)** [chk] for the numbers; Jasper's decision [?]
- **Trigger:** the 40 deg outlet cone of the bench release cannot cover unrestricted movement in the default room: the floor-centre cable direction is **43.877 deg** from vertical and a 2.1 m scan direction is **78.690 deg**; a fixed 40 deg cone cannot cover even a three-direction subset by reorienting the station.
- **Options explored (recorded numbers):**
  1. Restricted bench use only (adopted as the release scope).
  2. Two-axis gimbal around the Ronstan ring throat: rejected as a print release. A tension force through the pivot has almost no aligning moment; at 60 deg yaw + 60 deg pitch the incoming line differs from the cartridge axis by 75.52 deg and needs ~38.7 mm radial opening 10 mm behind the throat against ~8.3 mm existing; the reused rear carrier intersects the incoming line at 30 deg yaw (1.001 mm³) up to 4.377 mm³ at 60/60. It adds four moving joints and a flexing switch harness; no wall attachment designed.
  3. Fixed canted outlet, axis (1, −1, 1)/√3: an ideal corner needs **54.7356 deg**, so a 55 deg cone leaves **0.2644 deg** of margin; the incoming spool corridor reached **63.626 deg** and a 55 deg rear aperture failed 24 sampled paths, so the rear opened to 65 deg. Failed checks kept: no load-bearing bracket to the base, 7 collisions with the existing case, clamp screw head only about 92 % supported.
  4. Larger fixed rounded outlet with a larger bead collar (listed "first priority"); motor-driven gimbal (two actuators); separate homing sensor.
- **Deciding constraints:** installation margin, load path, and bead contact at oblique angles (an OD28 bead in an ID26 collar gives only 1 mm radial overlap when centred).
- **Choice:** none adopted in this stream; "restricted validated home ray" for the bench. How the gen-2 station handles line angle is NOT RECORDED (see T25 and Questions).
- **Evidence:** CAD with failures retained. No physical test.
- **Sources:** verification/fresh_review_results_20261002.md; docs/ARTICULATING_OUTLET_20261004.md; docs/CANTED_OUTLET_20261004.md; docs/UNKNOWN_MECHANICAL_AUDIT_20261004.md.

**T19. One-plug removable station, local electronics and fuse packaging (2026-10-02 to 05)** [J] for the goal ("user goal: install stud dock, slide on fully assembled station, connect one external plug; no internal wiring during installation")
- **Options recorded (docs/PLUG_IN_STATION_PROPOSAL):** keep central drivers with a keyed hybrid connector (4 motor + 2 home + 2 DC conductors, with chopped phase current in a long cable) versus fully self-contained stations (local driver, controller, regulator; one DC input with Wi-Fi, or one combined power + data cable). Recommended: self-contained, with local controllers running buffered trajectories so Wi-Fi does not set pulse timing.
- **Constraint:** connecting or disconnecting motor phases with an energised A4988 can damage it; a locking connector does not make a station hot-swappable; DC-only stations lose holding torque on unplug.
- **Fuse packaging:** the 55.63 mm fuse holder body left only **4.27 mm** under the roof, excluding the 14 AWG lead bend, so the populated variant was put on HOLD; the revised carrier uses R15 mm bends, a 4.4 mm wire clearance envelope, **3.17 mm** nominal roof clearance, and M3 x 10 screws into 3 mm nut-seat roofs.
- **Outcome:** CAD and unpowered fit prototype only; physical wire bend, terminal threading and thermal behaviour NOT RECORDED.
- **Sources:** docs/PLUG_IN_STATION_PROPOSAL_20261002.md; docs/FUSE_SERVICE_PROTOTYPE_20261004.md; verification/HOUSING_PROTOTYPE_RESULTS_20261004.md.

**T20. Payload requirement: 0.9 kg, then a 5 lb reserve, then "jeans are the working load" (2026-10-04)** [J] ("user update")
- **Trigger:** Jasper asked to prototype the housing first and defer the room survey; he asked for a "5 lb reserve" to give wiggle room for jeans, "not the normal requirement".
- **Numbers (CALC, independently re-computed):** total static weight ratio 2.013 (5 lb + 0.45 kg claw vs 0.9 kg jeans + 0.45 kg), and 1.672 against the working case at +2 m/s²; tension spans 3.31 to 62.0 N across 32 cases (max: reserve payload, two cables, 75 deg, +2 m/s²); the historical 40 N does not bound them. A supported two-motor planar test cannot establish four-axis margin.
- **Choice:** 5 lb is a reserve to investigate, not an achieved factor of safety. Superseded 2026-10-19 by D19 (1 lb test weight first).
- **Sources:** REQUIREMENTS.md CR6, CR13; docs/PRIORITY_EXECUTION_20261004.md; verification/PAYLOAD_RESERVE_REVIEW_20261004.md.

**T21. Clamp V1 mechanism correction: the jaws could not pinch thin fabric (audit 2026-10-12 of the Sep 30 rack-and-pinion clamp)** [J-sel] (Jasper began his own SolidWorks claw redesign the same day; Claw_V1 folder 2026-10-12)
- **Found (CALC):** pinion pitch radius 18 mm x 120 deg gives 37.699 mm per rack; closed gap = 77.4 − 2 x 37.699 = **2.002 mm**, so the pads never close on thin cloth.
- **Options recorded:** adjustable pad projection with shims (about 1.001 mm per pad only just touches); extend servo travel (3.186 deg more, but gear engagement, rack overlap and servo limits must be checked); a linkage with higher mechanical advantage near closure; geometry that gathers rather than relies on friction.
- **Grip-force screen (CALC):** friction μ = 0.5, reserve 2, efficiency 0.8, r = 18 mm: **1 lb needs 8.90 N per jaw and 0.400 N·m**; 5 lb needs 2.002 N·m. MG996R stall is 0.922 N·m at 4.8 V and 1.079 N·m at 6 V, so 5 lb exceeds even stall. "Do not order a stronger servo before measuring the shortfall."
- **Outcome:** led into the geared clamp (T34). A physical cloth test is NOT RECORDED.
- **Sources:** docs/CLAW_SELF_CAD_DESIGN_20261012.md; docs/QUICK_PARAMETER_RESOLUTIONS_20261005.md.

**T22. Line diameter: three different assumptions in the record (2026-10-06 note)** [chk]
- **Found:** "No measured diameter is recorded." Guide checks use 0.6 mm; `cad/params.py` uses 1.0 mm (giving a 1.4 mm spool anchor hole); the gen-2 screening and the pulley groove use 0.5 mm. The 120 lb rating "is not assembled system capacity".
- **Why it matters:** the 20 ft = 5 layers result (T23) and the bore of every guide depend on it.
- **Outcome:** NONE; the record asks for a measurement. NOT RECORDED whether Jasper has measured it.
- **Sources:** docs/SELF_CAD_DIMENSIONS_AND_WIRING_20261006.md; verification/design_review_gen2.md inputs table.

### Era 3: SolidWorks generation, electrical bring-up, heat and control system (Oct 7 to 20, 2026)

**T23. Spool shortened to the shaft's real engagement, and what that does to the math (v1 2026-10-07; v2 10-11; v3 10-18; D16)** [J]
- **Trigger (recorded):** "the original spool was longer than the motor shaft can engage". Derived from numbers in the 2026-10-06 dimension note (motor face X = −2, shaft projection 24 mm, spool winding from X = 4.5 for 32 mm overall): the spool would extend about 14.5 mm past the end of the shaft. The record does not show Jasper's own measurement of this.
- **Iterations:** `Spool_V1_Short_22mm` (2026-10-07), `Spool_V2` and `Spool1011` (2026-10-11), `Spoolv3` (2026-10-18). **Measured from the v3 STEP:** Ø36 flanges (3 mm thick), **Ø15 core (7.5 mm radius), 16 mm drum, 22 mm overall**, bore Ø5.45 with a 0.5 mm D-flat (4.95 mm across), Ø2.8 radial set-screw hole on the flat's axis 7 mm up, Ø1.4 tie-off 6 mm off axis. The gen-1 spool was Ø20 core x 26 mm winding x 32 mm overall. Reason for core Ø20 to Ø15 and drum 26 to 16: NOT RECORDED.
- **Consequence table (CALC, 20 ft of 0.5 mm line, 85 % packing):** 10 mm drum: 7 layers, 11.0 mm full radius, 22.0 mm length/rev change; **16 mm drum (v3): 5 layers, 10.0 mm, 24 to 18 N line force, 15.7 mm (33 %) length/rev change, 8 mm flange margin**; 20 mm drum: 4 layers, 9.5 mm, 12.6 mm.
- **Capacity check (CALC):** longest cable 4.66 m (15.3 ft; claw 0.3 m inside the walls and 0.05 m above the floor, anchors 0.15 m below the ceiling) against 20 ft = 6.1 m stored: 1.4 m margin. A separate ideal-corner-to-opposite-floor-corner figure is 16.82 ft (5.13 m), which leaves 3.18 ft.
- **Open (review R4):** the controller must use radius as a function of wound length; shaft radial load (line at the drum mid-plane, 11 mm from the base) against a typical 25 to 30 N bearing rating at 20 mm, which the 32 N near-ceiling tension reaches. Level-wind versus simple outlet: NOT RECORDED as decided.
- **Sources:** docs/DESIGN_HISTORY.md; DECISIONS.md D16; solidworks/README.md; docs/SELF_CAD_DIMENSIONS_AND_WIRING_20261006.md; verification/design_review_gen2.md R4; docs/ROOM_LAYOUT_20261014.md; calculations/gen2_screening.py.

**T24. Spool bore printed too tight on the shaft, opened from Ø5.2 to Ø5.45 (v2 to v3; confirmed 2026-10-19)** [J] ("Jasper, confirmed")
- **Trigger:** the v2 print (Ø5.2 bore, 4.70 mm across the flat) was too tight on the 5 mm shaft. Gen-1 notes use Ø5.2 to 5.3, and "fit coupon first" had already been advised on 2026-10-06.
- **Options recorded:** open the bore (chosen); the review also lists measuring the printed bore, a fit-coupon series, and a thread-forming M3 or heat-set insert for the set screw rather than a printed thread.
- **Deciding constraint:** printed holes print undersize; the set screw on the flat, not the bore fit, carries torque.
- **Choice:** Ø5.45, i.e. 0.45 mm diametral clearance, which the review calls "loose for a printed hole unless your printer prints holes ~0.3 mm undersize".
- **Outcome:** the printed bore measurement and whether v3 fits well are NOT RECORDED. The outline asks for a measured printed bore and a coupon; the record has no coupon data.
- **Sources:** DESIGN_STATE.md "Gen-2 updates"; commit "Worst-case payload capacity (review R10), measured spool-bore fix"; verification/design_review_gen2.md R4.

**T25. Removable wall station instead of the one-piece corner mount (v1 2026-10-07, v2 10-11, v3 10-18; D15; register H04 2026-10-14)** [J-sel]
- **Trigger/reason (stated):** serviceability. A station can be pulled and swapped without disturbing the installed frame and its calibrated anchor position.
- **Options:** (a) the gen-1 one-piece plate screwed to a joist (alignment of motor and pulley fixed by the print; not removable); (b) fixed wall frame + slide-in housing + shell cover (chosen). Failure cases the outline lists for (b): rail-root cracking, layer separation, creep, fastener pull-out, upward motion. A removable captive-rail dock with an M3 lock already existed in the 2026-10-01 stream.
- **Cost recorded (review R3):** the slide-in housing needs positive retention independent of friction, rated for the 32 N worst case with SF ≥ 3 (screw, pin or snap); the slide direction should seat under the line load (down or toward the wall); rail root fillet ≥ 1 mm with load along the layers; screws into a stud only (the line pulls away from the wall, so pull-out, not shear); PETG or better.
- **Outcome:** geometry only; the retention feature and its margin are NOT RECORDED. v3 STEP files are in the repo; measuring slide direction and retention is listed as the next step. Why SolidWorks replaced the parametric CAD on 2026-10-07 is NOT RECORDED. How the station handles the line angle (T18) is NOT RECORDED.
- **Sources:** DECISIONS.md D15; docs/DESIGN_HISTORY.md; verification/design_review_gen2.md R3; docs/history/decisions_20261014.md H04.

**T26. Electronics: central controller moved to one controller per winch (D17; Oct 7 to 19)** [J-sel]
- **Trigger (stated):** four long motor harnesses; the one-plug goal (T19).
- **Options recorded:** central Uno + CNC shield (kept as the bench reference); per-station XIAO ESP32 + A4988 + step-down regulator on one 12 V pair; hybrid = central step generation for the 1 lb demo, distributed later.
- **Cost recorded (R1):** a cable robot with four position-controlled cables is over-constrained; with four Wi-Fi nodes, **50 ms skew at 50 mm/s = 2.5 mm of length mismatch**, about **8 N** on a ~3 N/mm line (assumed stiffness), the same size as the static load, or slack the other way.
- **Choice and what followed:** per-station nodes; D20 control system V1: the host plans, stations execute Hermite segments in their own clocks with path-time feed-hold and leases; the Python station core is the specification and the C++ firmware matches it trace-for-trace. D21 stop never disables; D25 no automatic resume.
- **Outcome:** SIM only: lost hold messages, host stalls and reboots caught in simulation. Evidence class for the slide: **designed and simulated, not demonstrated on four stations**. Pass criteria written for the first four-node test: 300 mm vertical move at 50 mm/s with 1 lb, no slack, ≤ 2 mm per cable, no step loss.
- **Sources:** DECISIONS.md D17, D20 to D25; verification/design_review_gen2.md R1, R2; docs/CONTROL_SYSTEM_V1.md.

**T27. Station boot safety and bulk capacitor (review R2, R8; Rev C 2026-10-16)** [chk]
- **Found:** boot glitches can step a motor and the A4988 `EN` input defaults to enabled; a standalone A4988 needs its own **47 to 100 uF** bulk capacitor across VMOT (the CNC shield had supplied one); comms loss must hold, never disable.
- **Choice:** external 10k pull-up on ENABLE (R1), STEP and DIR pull-downs (R2, R3), HOME pull-up (R4); C1 100 uF / 50 V at VMOT; fuses at the source end of each long branch; XIAO pins that are not strapping pins (STEP D1/GPIO3, DIR D2/GPIO4, EN D3/GPIO5, HOME D10/GPIO10).
- **Limits recorded:** the pull-up cannot hold a suspended load (disabling removes torque); the DROK buck family has no output overvoltage or reverse-input protection and is rated 4.5 to 20 V in, so do not move to a 24 V supply (2026-10-17 review).
- **Evidence:** schematic only; as-built not verified.
- **Sources:** docs/electrical/station_revC_20261016/README.md; docs/electrical/STATION_ARCHITECTURE_REVIEW_20261017.md.

**T28. Station power wiring: the 14 ft run became 32 ft; 18 AWG moved toward 16 AWG (2026-10-14)** [J] (layout inputs are "user-reported")
- **Trigger:** Jasper put the supply near one corner on a 3 ft stand with feeds down to the floor and back up the walls: runs of 6, 23, 21 and 32 ft, 82 ft in total (90 to 94 ft with slack), not 14 ft each.
- **Options:** BNTECHGO 18 AWG silicone 100 ft ($37.98) first recommended; cheap CCA cables rejected (WAGO documentation specifies copper); MaxBrite 18 AWG OFC plausible; 16 AWG copper now preferred. Fuse at the source end of each run, not at the station.
- **Numbers (CALC, illustrative 2 A):** 32 ft one way = 64 ft loop: **0.82 V drop on 18 AWG, 0.54 V on 16 AWG**; halves at 1 A.
- **Outcome:** no purchase or fuse value finalised; actual branch current not measured.
- **Sources:** docs/POWER_WIRE_SELECTION_20261014.md; docs/ROOM_LAYOUT_20261014.md.

**T29. Station electrical fault, quarantined controller, Rev C (2026-10-14 to 17)** [J] (user-reported measurements)
- **Trigger (2026-10-16 evening):** VDD, RESET and SLEEP each read 3.3 V, VMOT-to-GND read 0 V, then the XIAO heated on USB and was no longer recognised.
- **Reasoning recorded:** a low VMOT reading cannot distinguish a missing positive, missing return, fuse, supply, short or meter error; the suspect XIAO and the external assembly were both quarantined; no replacement controller was installed into the unchanged assembly. Root cause **unproven**; USB backfeed explicitly not asserted.
- **Choice:** Rev C: JP1 removable link between the buck output and XIAO 5V (open for every USB use, closed only standalone); the 1N5819 blocks reverse flow only; the motor return runs directly to the incoming supply return; R1 to R4 pull resistors; C1 at VMOT. Keep the XIAO + A4988 + local buck architecture (2026-10-17 effectiveness review); do not rewire speculatively.
- **Evidence:** REP (meter readings); Rev C drawing only; the as-built perfboard is not certified. Earlier, on 2026-10-14: buck 5.00 V, about 4.7 V at the XIAO after the diode, 3.3 V regulated; the switch released and pressed states read correctly.
- **Sources:** docs/MOTOR_STATION_BRINGUP_20261014.md; docs/electrical/station_revC_20261016/README.md; docs/history/startup_decision_20261016.md.

**T30. A motor that would not move: the log said stepping, the meter said no (reported 2026-10-16 to 18)** [J]
- **Trigger:** command output showed pulses, the shaft did not move; the switch worked.
- **Reasoning recorded (separate command from motion, then check supply, reference and wake state before changing code):** ENABLE read 3.3 V idle, 0 V during the run command, then 3.3 V; SLEEP read about 1 V; the 3.3 V logic rail read about **1.14 V**. Jasper identified a bad 3.3 V connection; after the correction the motor moved (later described as loud and slow).
- **Alternatives ruled out:** NOT RECORDED (what Jasper tried first is not in the record).
- **Design change it caused (review R9, "partly fixed"):** A4988 VDD from the same regulated rail as the XIAO, soldered or crimped rather than jumpered, and a measure-VDD step before enabling.
- **Evidence:** REP, "not saved oscilloscope evidence". Photos 07, 08 and 12 show the bench wiring (no readings are visible in the README). The date sequence against T29 is not established: the record says not to equate this fault with the earlier XIAO heating.
- **Sources:** docs/history/REVIEW_HANDOFF_20261019.md; docs/history/decisions_20261018.md D18-02; DESIGN_STATE.md "Generation 2"; SPACEX_OUTLINE.md slide 11.

**T31. Heat: a sealed PETG station would cook its own motor mount; aluminium fin (raised by Jasper 2026-10-19)** [J] ("Raised by Jasper"; "Per Jasper: the fin should rise vertically")
- **Trigger (what he noticed):** in stagnant air the motor can only dump heat by conduction into the PETG it is bolted to. PETG is about 0.2 W/m·K (~1/1000 of aluminium), so the loaded motor-bolt interface climbs toward motor temperature, and the joint carrying the cable load creeps, the motor loosens and the anchor drifts.
- **Numbers (CALC, two-node model, all inputs assumed: 1.8 ohm per phase, 30 C ambient, 1.5 W of electronics in the shell):** sealed shell steady state **67 C at 1.0 A, 84 C at 1.25 A, 106 C at 1.5 A**; it passes 60 C after 84 / 37 / 22 minutes. Open air 52 / 64 / 79 C; vented shell 55 / 68 / 84 C. Limits used: 60 C for loaded printed parts, PETG softens near 80 C. Force rises with I, heat with I², so +50 % current (1.0 to 1.5 A) gives +50 % payload for 2.25x the heat.
- **Options recorded (R11):** vent the shell; an aluminium heat-spreader plate through the shell as a fin (named "the biggest single gain", it also spreads the bolt load); a clip-on NEMA 17 heatsink (~$5); electronics outside the motor air space; TMC2209 standstill-current drivers (holding heat down ~75 %, "the next step, not a replacement"); ASA/ABS/PC housing (Tg ~100 to 105 C against PETG ~80 C); NTC thermistor with firmware park at 60 C. The outline adds: a fan costs noise, power and a failure point; lowering current costs payload; copper rejected (aluminium is cheaper and lighter, conduction is enough at ~4 W); liquid-metal paste rejected (gallium attacks aluminium).
- **Choice and iterations (all 2026-10-19 unless noted):**
  1. 100 x 100 x 3 mm plate between the motor flange and the 5 mm PETG tab (77 g; ~36 C at 1.0 A and ~44 C at 1.5 A estimated); interface measured from the v3 STEP (Ø22.4 pilot, 4x Ø3.5 on a 31 mm square, motor axis 21.1 mm above the deck).
  2. **Jasper:** the fin should rise vertically, not sideways (**reason, Jasper 10/21: bio-inspired by antelope horns, from his bio-inspired design class**; a horn is a heat exchanger with a blood-fed core shedding heat through its surface): 44 x 150 x 3 mm, motor width only (50 g; ~39 C at 1.0 A and ~51 C at 1.5 A, open air, black). Cost of the change from the commit numbers: about 3 C worse at 1.0 A and 7 C worse at 1.5 A against the 100 x 100 plate (the outline quotes only "~3 C"); past ~150 mm the tip is near room temperature (fin efficiency), so taller buys little.
  3. Revision to **1/8 in (3.175 mm) x 44 x 250 mm** with a hole table, tolerances and finish notes (about 200 mm in open air above the cover's fin-pocket floor); then a 1:1 A3 shop drawing, then a US Letter printable drawing with a 1:1 hole template and an inch version (2026-10-19 to 20). Reason for 150 to 250 mm and for the final thickness: NOT RECORDED beyond the docstring.
- **Drawing and process facts (docstring and drawing notes):** blank 44.0 x 250 mm sheared (±0.5); all five holes (Ø22.5 pilot, 4x Ø3.4 on a 31.0 mm square) drilled in one setup from the bottom and left edges, positions ±0.1 relative to each other; matte black paint except the motor contact square (thermal paste there); bolts M3 x 10 become M3 x 12; the motor and spool move 3.175 mm along the shaft; the bottom edge sits on the slide-in deck. Photos 01 to 03 and 06 show drilling on the manual mill, the setup with the printed drawing, and the shear with blanks and the Letter drawing. **Jasper's method (10/22):** the edges located only the bottom-left hole; once drilled, he made that hole the mill's zero and positioned every other hole from it, for exactness (the sheared edges are ±0.5).
- **Knock-on to the shell:** cover v4 concept (T32).
- **Outcome / evidence:** CALC only; no temperature has been measured in the record. A 90-minute hold test at 1.0 A with and without the fin, logging motor case and PETG every 10 minutes (pass: both under 60 C), is **planned**; no result is recorded.
- **Sources:** verification/design_review_gen2.md R11; calculations/gen2_motor_thermal.py; cad/parts/motor_heat_plate.py; solidworks/heat_plate/; commits b963896, 94624ee, a78ef8a, 30e7b54, a6fdf46, e0c9ec5; docs/presentation/photos/README.md.

**T32. Station cover v4: what the fin does to the shell (2026-10-19)** [J] ("Jasper is designing the cover himself")
- **Facts recorded (reference concept, not verified, not adopted):** the fin occupies y [−T, 0] and x [−22, 22] from z = −21; **the motor back face moves to y = −38 − T, only 0.33 mm from the old shell's inner −y wall at T = 4.76**, so that wall must be relieved; motor top z = 21.15, slip-in pin top z ≈ 24.9, alcove floor ≥ 25.5; 12 mm air gap per fin face; the fin slot must run out to the mating rim so the cover slides on. Concept numbers: 13 inlet slots (~698 mm²) and 10 outlet slots (~557 mm²), 455.2 g at 100 % solid. Interference of the cover with motor, spool, slip-in, wall mount and fin: 0.0000 mm³; fin to alcove walls 12.00 mm.
- **Outcome:** the concept is kept as a reference; independent verification was stopped; Jasper's own cover is not in the record.
- **Sources:** DESIGN_STATE.md "Station cover v4"; verification/station_cover_v4_implementer_notes.md.

**T33. Camera: ceiling camera or claw camera (2026-10-01 stream; review R7 2026-10-19)** [J-sel] ("user-selected direction: scan, then pick, from the claw")
- **Options recorded:** fixed overhead camera with a verified pixel-to-floor homography (gen 1); claw-mounted XIAO ESP32-S3 Sense with image-specific pose. Review R7: the claw camera gives a close view but swings, loses the whole-room view and needs per-image pose; recommendation: ceiling camera for "where is the laundry", claw camera for "centred, and did I grab it".
- **Choice:** the claw camera is preferred as primary; the final split is NOT RECORDED (the outline asks him to state it). Garment perception on the claw camera was wired to hardware on 2026-10-19; field results are NOT RECORDED.
- **Sources:** docs/REVISION_V2_DECISIONS.md; verification/design_review_gen2.md R7; git log 2026-10-19.

**T34. Gripper: from five fingers to a geared clamp, and the tooth-strength check (D18; V2 and V3 2026-10-18; V5 2026-10-18/19)** [J-sel]
- **Path recorded:** five tendon fingers (T03) to a rack-and-pinion parallel clamp (2026-09-30; T21) to a camera outrigger on an upper housing with servo and clamp below an extension (register H02, "camera view obstructed near jaws") to an 18:54 spur reduction with 36:36 synchronisation (V2) to the compact V3 with 24:24 synchronisation (axis spacing 54.3 to 36.3 mm) to Jasper's V5 (18T pinion, 54T/24T compound, 24T follower; 3:1; the second jaw counter-rotates).
- **Options recorded (V3 review):** module 1.0 (smaller diameter, higher root stress at equal width); two-stage reduction (more shafts and backlash); herringbone (printing and axial alignment cost); 105 deg servo travel for 35 deg jaw travel. Stated reason for the clamp: "simpler to build and test than five TPU fingers and a tendon drum".
- **Deciding calculation (CALC, Lewis bending, PETG allowable 22.5 MPa; stall is the design case because the clamp stalls on every cloth grip):** module 1, 6 mm face at MG996R stall: **55 to 65 MPa, SF 0.41 at 4.8 V and 0.35 at 6.0 V**. Module 1.5, face 8 mm: SF 1.04; module 2, face 10 mm: SF 2.32. Grip need 7.4 N per jaw (μ = 0.3, 1 lb); the train delivers ~20.8 N per jaw at a 60 mm arm. Options in the review: module ≥ 2 with ≥ 10 mm face; a metal pinion; torque limiting in firmware.
- **What the record actually shows:** the V3 fit review (2026-10-18) already uses **module 1.5 with 16 mm (reduction) and 20 mm (sync) faces**, one day before the R5 screening, which assumed module 1 and 6 mm because the V5 geometry was not yet measurable. So do not tell it as "the screening made me change the module" unless Jasper confirms the order. Measured on v6: m1.5, face 16, pinion SF **2.09 to 2.44** at stall (R5's m2, b10 case is 2.32); sync stage under one-jaw load SF **1.33**.
- **Outcome:** CAD and CALC. No printed gear test, stall test or failure is recorded. The claw servo runs at 5 V, not 6 V, so earlier 6 V force numbers do not carry over.
- **Sources:** DECISIONS.md D18; docs/history/gripper_v3_fit_review_20261018.md; docs/history/decisions_20261014.md (H01, H02); docs/history/decisions_20261018.md (D18-06 to 08); verification/design_review_gen2.md R5; verification/gripper_v6_inspection.md.

**T35. Gripper v6 inspection: the claw is about 4.6x its mass budget (2026-10-20)** [chk]
- **Found (CAD, upper bound at 100 % solid PETG 1.27 g/cc, aluminium 2.70):** printed parts about 1,808 g + 12 in aluminium tube (Ø28.54 x 3 wall) 198 g + MG996R 55 g = **~2,061 g against the 450 g budget**. The tube + electronics base (499 g) + cylinder (321 g) are 1,018 g; "not fixable by infill alone". A 60 % slice-fill guess (an assumption, not measured) gives ~1.34 kg.
- **Other High findings:** no torque path from servo to pinion (Ø8.0 bore on a Ø6.0 shaft, no horn, 4 mm engagement; stall tangential force 68 to 80 N); the compound shaft is not a valid two-bearing shaft (the lower pin enters the bearing by 1.05 mm of 5 mm; the lower pin axis is 0.40 mm off the upper).
- **Medium:** centre distances are exactly 54.00 and 36.00 (V3's +0.30 mm print allowance is gone; backlash 0.21 to 0.22 mm against ~0.42 mm); as-exported meshes overlap 2.53 and 17.00 mm³ (clocking only, windows 0.9 and 0.7 deg wide; zero overlap at 13 angles after re-clocking); jaw travel is 51 deg (−34 to +17 deg of the compound), not 60 deg; the follower is cantilevered on one printed Ø7 pin; zero-clearance Ø4.0 servo pegs; the Ø28.54 tube is line-to-line so it will not enter as printed without +0.2 to +0.3 mm.
- **Outcome:** Jasper's response is NOT RECORDED. This conflicts with the capacity calculations (T36) that assume a 0.45 kg claw.
- **Sources:** verification/gripper_v6_inspection.md; REQUIREMENTS.md R7.

**T36. Capacity: how much the four winches can lift anywhere, and why claw mass matters (review R6, R10; 2026-10-19)** [J-sel] (Jasper's one-pound gate, D19)
- **Trigger:** the "1 lb test weight" gate plus a claw of about 1 lb (0.45 kg) needs about 2 lb in total.
- **Numbers (CALC):** equal-share tension for 1 lb + 0.45 kg claw with the claw under the room centre: 0.15 m below the anchors = 32.1 N per cable; 0.30 m = 16.1 N; 0.60 m = 8.3 N; 1.20 m = 4.6 N. The motor gives ~24 N at the 7.5 mm core and ~18 N at a full spool (36 N·cm x 50 % running margin / radius). Worst-case total claw + load at **1.0 A: 1.04 / 1.51 / 1.93 / 2.30 lb for a 0.4 / 0.6 / 0.8 / 1.0 m ceiling limit** (best split, 70 % running torque, 1.5 safety margin, +2 m/s², 0.2 m wall margin); 0.76 to 1.75 lb with one slack cable; +50 % at 1.5 A. Worst spot: high against the middle of a long wall. Structural snag case: 32 N per cable at 1.0 A, 48 N at 1.5 A.
- **Options recorded (cheapest first):** weigh and lighten the claw (every 0.1 kg is ~0.22 lb of payload); a tension-aware ceiling (high only near the centre); raise the drivers to the motor's 1.5 A (limited by heat, T31); fix synchronisation so no cable goes slack.
- **Choice recorded:** D19 (1 lb test weight on four stations first; no rating claimed). A software ceiling at least 0.4 m below the anchors (D26 uses 0.4 m). Which option Jasper chose for current and ceiling is NOT RECORDED.
- **Sources:** verification/design_review_gen2.md R6, R10; calculations/gen2_payload_limit.py; DECISIONS.md D19.

**T37. Charging and claw power: five proposals in one week (2026-10-12 to 18)** [J] ("user explicitly reopened ... to reduce cost"; the finished power bank was rejected by Jasper, who wants a component-built design)
- **Trigger:** automatic wall-hook charging as the end state (2026-10-12), then the mass, cost and volume of the first power chain.
- **Options in order (all proposals; none confirmed as bought):** Rev A (separate servo and logic regulators, 2S, manual charge); 2S + DROK 200359 at 5 V + TB6B charger + XY-CD60 cutoff (2026-10-18; the larger display regulator costs volume and mass); a screenless ZTW 6 A UBEC and a $13.99 charger as cost savings; a USB-C PD power bank (rejected); a single 18650 + boost regulator; a protected 2S pack (Tenergy 31003, 72 x 38 x 19 mm, 99 g) + DFR0564 charger + DFR0753 5 V regulator. The 2026-10-19 cart introduces yet another ZTW + Tenergy 7.4 V 2200 mAh + USB-C 2S charger combination.
- **Constraints recorded:** a protection board is not a charger and a charger is not a balancer; a pack-level cutoff cannot see cell imbalance; a battery cutoff releases the grasp, so park before cutoff; the servo is at 5 V so 6 V torque numbers do not carry over; provisional servo pulse 2.5 A, camera 0.7 A, battery peak ~5.7 A at 3.2 V.
- **Outcome:** unresolved; the final battery and charger actually received are NOT RECORDED. The Oct 18 DROK/OVONIC/TB6B set is explicitly "historical".
- **Sources:** docs/CLAW_ELECTRICAL_REVA_20261012.md; docs/history/decisions_20261018.md; docs/history/claw_cost_review_20261018.md; docs/history/claw_compact_power_proposal_20261018.md; docs/history/REVIEW_HANDOFF_20261019.md.

**T38. Startup calibration: how the robot learns its own geometry (2026-10-16 direction; D22 to D26 through 2026-10-20)** [J] (SC01 to SC10 are "user-selected")
- **Trigger/direction:** the claw starts upright on the floor near the middle of the room, makes a short automatic lift, and the user places a printed marker; no surveyed marker, no docking cradle, no ceiling camera.
- **Options recorded and rejected:** require a docking cradle; remove bead verification; room-wide marker search; ceiling camera. Retained: physical bead verification (SC07).
- **Finding (SIM):** vision alone leaves absolute cable-length sigma at **~20 to 25 mm**, so with 12 mm of bead overtravel every bead is BLOCKED and the robot stays LOCAL_ONLY (D24).
- **Study (SIM):** a printed multi-tag floor board, proposed by Jasper, cut predicted sigma from ~25 to ~10 to 12 mm (extent matters, tag count does not) and then plateaued; with the precise board the fit became overconfident (actual error 7 to 17 sigma) and accepted its own calibration less often (2/5 against 5/5).
- **Decision D26 (Jasper, 2026-10-20):** the ceiling and wall margins, not bead precision, protect against absolute-length error: start near the room centre, catch gross slack on the floor with a bounded one-cable-at-a-time take-up, keep the claw 0.4 m below the anchors and a margin inside the walls; full-workspace operation only if k·sigma ≤ the margin with an honest sigma; beads become end-of-travel switches. **Jasper's method:** probe per-pose slack by reeling each cable in turn; no claw motion means slack. Implemented as an opt-in probe.
- **Outcome (SIM only):** the probe measures slack to ~0.4 mm RMS; with the probe the 1.0 m sparse board is accepted 5/5 (2/5 without); cost ~40 s per pose (+1,480 s on a 275 to 304 s startup). The independent review found no Critical finding and showed that the 17.5 to 24.8 N tension peaks are a simulator limit cycle (true equilibrium at most 6.5 N); two items to fix before hardware (probe tension cap H1, onset robustness M2). A printable 9-sheet Letter board (150 mm AprilTag sheets) exists (`prints/`). Nothing on hardware.
- **Sources:** docs/STARTUP_CALIBRATION_V1_20261016.md; docs/history/startup_decision_20261016.md; DECISIONS.md D22 to D26; verification/floor_reference_study.md, slack_probe_results.md, slack_probe_review.md.

**T39. Control system review: three Critical findings fixed in simulation (2026-10-19)** [chk]
- **Found (reproduced in the simulator):** (C1) the service had no background loop, so a READY hanging claw latches LEASE faults on all four stations while the operator reads the page; (C2) with a hanging claw and stations in LEASE fault there was no software path to lower it, the only exit being the power strip (a category-0 drop over the room); (C3) `claw_supported` was persisted too late, so after a host crash during calibration the UI said DISARMED and one confirm would remove torque on a hanging claw. High: lost hold datagrams (one winch pulled an extra **85.6 mm** of cable); pause refused during lowering; an unauthenticated API; no try/finally in `execute`.
- **Fixes with evidence:** idle host loop; LEASE becomes a coordinated stop that can be acknowledged and lowered; `claw_supported` fails closed and is fsync'd before the first lift; hold resent every 20 ms (spread 0.58 s without resend against < 0.06 s with); a per-boot disarm key; a token on the API. Open before any hardware bead search: a station-enforced travel floor.
- **Outcome:** SIM, unit and conformance tests only (the C++ matches the Python reference trace-for-trace). **Not run on the rig.** Jasper's own role in finding it is NOT RECORDED.
- **Sources:** verification/control_system_v1_review.md (including section 7); DECISIONS.md D21, D25.

**T40. Test plan with pass limits written first, and the evidence plan (2026-10-19 to 20)** [J-sel]
- **Gates:** (1) one station: jog repeatability, pull force vs speed, driver temperature, switch response; (2) station hardware: measured fits, slide retained under 3x line load, inspection after N cycles; (3) four stations, 1 lb: 300 mm at 50 mm/s, no slack, ≤ 2 mm per cable, 10 resets under load = zero motion, Wi-Fi pulled mid-move = load holds, power strip off = all four unpowered; (4) laundry attempts and failure modes by garment type.
- **Also planned:** the 90-minute thermal hold (T31); SolidWorks linear static studies for each gen-2 assembly with a derated PETG and a 2x dynamic factor ("stiffness matters as much as strength; station deflection moves the anchor ~1:1").
- **Outcome:** NONE run. "Limits written before testing" is a claim Jasper can make only if they are written down with dates.
- **Sources:** docs/presentation/SPACEX_OUTLINE.md slide 13; docs/SIMULATION_GUIDE.md; verification/design_review_gen2.md.

**T41. Gen-1 claw integration errors caught before printing (undated; between 2026-07-16 and 08-07 by commit order)** [chk]
- **Found:** the hub and frame used different bolt circles (27.0 vs 23.6 mm, a latent bug; unified to one value at four angles clearing the five finger pockets by ≥ 5 deg); the finger shoulder was specified at the mounting end (z 0 to 2) and would have blocked slot insertion entirely; firmware grip angle said 120 deg (a 100 deg throw) which would have undersized the drum (corrected to a 120 deg throw, 20 to 140 deg); mass roll-up arithmetic was 406 g, not 425 g; finger placement was 6.5 mm outboard (445 mm³ interference); reach corrected **130 to 118 mm** (the original sum double-counted the hub).
- **Numbers kept:** tendon travel 6 notches x 4.5 mm = 27 mm; drum core 13.5 mm gives 28.27 mm (4.7 % margin); servo torque 25 N x 13.5 mm = 3.44 kg·cm against ≥ 9 kg·cm (2.6x); mass 419.2 g against 450 g.
- **Outcome:** CAD verified; the five-finger claw was never built (no print recorded). Superseded by the clamp (T34). Low presentation value; one line at most.
- **Sources:** DECISIONS.md D2 to D12; DESIGN_STATE.md; verification/claw_integration_calc_report.md; calculations/claw_integration.md.

**T42. Software consoles: two built on the same day, merged into one (2026-08-12 to 13)** [?]
- Operations console and perception console were built in parallel; they were merged into one app on 2026-08-13 with the camera-validated capture pipeline. Low manufacturing relevance; one line on a backup slide at most.
- **Sources:** DESIGN_STATE.md "Console convergence"; BRINGUP_LOG.md.

---

## 2. Ranked shortlist for a 30-minute manufacturing-engineering panel

Ranking favours real failures found by measurement, trade-offs with numbers, design for manufacture, and things Jasper caught himself.

| Rank | Story | Story arc (one line) | Evidence | Needs before it is slide-ready |
|---|---|---|---|---|
| 1 | **Heat fin (T31, T32)** | I noticed a sealed PETG shell turns the motor mount into the hottest, most loaded joint; I weighed seven fixes, chose an aluminium fin, narrowed it to fit the station, then sheared and drilled it myself. | CALC; process photos 01, 02, 03, 06; thermal test planned | a thermometer number, why 250 mm, tolerances achieved |
| 2 | **A motor that would not move (T30, T29)** | The log said stepping; the meter said the logic rail was 1.14 V; a poor 3.3 V connection; lesson: verify motion and measure supplies before blaming code. | REP; photos 07, 08, 12 | exact readings and dates, what he tried first, before/after |
| 3 | **Spool: shorter, then too tight (T23, T24)** | The spool was longer than the shaft engagement; shortening it changed layers, line force and length per rev by 33 %; the v2 bore printed too tight so v3 opened it; coupons next time. | CALC + measured STEP; printed bore NOT RECORDED | printed bore numbers, why Ø15 core, line diameter |
| 4 | **Homing switch that would never trip (T16)** | My find: the bead must not cross the pulley; the first implementation failed a geometric check by 5 mm and 10.5 mm; rev D lands the roller on the line with 3.75 mm overlap. | CAD; no print recorded | what he noticed, any print and trip test |
| 5 | **Gear teeth: stall is the design case (T34, T35)** | A module-1 printed pinion would shear at servo stall (SF 0.35 to 0.41); the module-1.5, 16 mm design reads SF 2.1; then a v6 inspection found a 4.6x mass overrun and no torque path. | CALC; CAD | when he chose m1.5 and why; what he did about the v6 findings |
| 6 | **Tension, not payload, sets the workspace (T36)** | A 1 lb test plus a 1 lb claw means 32 N per cable near the ceiling; the ~24 N motor limit sets a 0.4 m ceiling, and the claw mass matters as much as the payload. | CALC | current setting, ceiling chosen, weighed claw mass |
| 7 | **The outlet cone that did not cover the room (T18)** | The 40 deg outlet cone could not reach the 43.9 deg (floor centre) or 78.7 deg (scan) directions; I explored a gimbal and a canted outlet with the numbers and rejected both; here is what I did instead. | CAD with failures kept; decision NOT RECORDED | what the gen-2 station does about line angle |
| 8 | **Central to distributed electronics (T05, T26)** | In July I kept the winches wired so sync was free; in October long harnesses and a one-plug station pushed me to per-winch controllers, priced at 2.5 mm and 8 N per 50 ms of skew, and I designed around it. | CALC; SIM | why he reversed; what the hybrid fallback is |
| 9 | **A fixed anchor versus a serviceable one (T06, T25)** | Hooks wander (1:1 into position error) so I bolted the corner down; then service needed removable stations without losing calibration, so the anchor moved onto a frame and the housing slides in. | CALC; CAD; photos 05, 13 | what gen-1 testing showed; slide retention number |
| 10 | **Margins instead of precision (T38)** | Vision alone gave 20 to 25 mm of length error against 12 mm bead overtravel; I stopped trying to buy precision and moved the safety to ceiling and wall margins, with a per-pose slack probe. | SIM only | what prompted the proposal; hardware plan |

Suggested pairing for the "thorough versus scrappy" prompt: thorough = story 4 (or 2); scrappy = the duct-tape splice and the 18 V reading from the bench (T15), once the 18 V question is answered.

---

## 3. Questions for Jasper (20)

Short answers are enough: a number, a date or "not done". If something was not done, say so; the deck must never present a planned result as measured.

**Heat fin (story 1)**
1. What first made you suspect heat in the shell (a warm motor, soft PETG, a calculation)? Which of the other fixes (vent, TMC2209, ASA, thermistor) did you actually consider, and what ruled them out?
2. Do you have any temperature reading from a real station (IR gun or thermocouple; motor case, PETG tab; current, minutes held)? If not, can you run the 90-minute hold test with and without the fin before Oct 22 or Oct 27?
3. How did the fin dimensions move from 100 x 100 to 44 x 150 to 44 x 250, and why 1/8 in stock? Where did you source it, and how many fins did you make?
4. For the mill and shear photos: what hole-position tolerance did you reach (caliper readings), how long did one fin take, and what went wrong (burrs, walk, scrap)?

**Motor that would not move (story 2)**
5. What are the exact meter readings and dates (VDD, SLEEP, ENABLE), and what did VDD read after the repair? What was the bad connection physically?
6. What did you try before reaching for the meter, and how did you rule out the firmware and the driver?
7. Is the XIAO that heated and lost USB still quarantined, was it replaced, and is the cause known?
8. Under load, what does the ALITOVE supply read at the station buck input? The 2026-08-28 reading of 18 V is close to the DROK's 20 V input limit; was it an open-circuit reading, and what does the brick label say?

**Spool (story 3)**
9. What did you measure on the motor shaft (engagement length, flat depth) that told you the original spool was too long? Why did the core go from Ø20 to Ø15 and the drum from 26 to 16 mm, and did you consider a level-wind?
10. What are the printed bore diameters for v2 and v3 (caliper), the printer and material, and did v3 slip on the shaft or seat well?
11. Have you measured the line diameter? The record has 0.5, 0.6 and 1.0 mm in different places, and the 20 ft = 5 layers result depends on it.

**Homing switch (story 4)**
12. What did you actually see or test that showed the bead would ride over the pulley groove? Did you print rev D (or the plate in photo 05) and see a bead trip the roller on real line? What is the real bead diameter?

**Gears and claw (story 5)**
13. When and why did you choose module 1.5 with 16 and 20 mm faces, and did you run any strength numbers or print a test gear before the Oct 19 review?
14. Have you weighed or sliced the v6 claw? The CAD upper bound is about 2.06 kg against a 450 g budget. What is the new budget, and why the 12 in aluminium tube?

**Capacity (story 6)**
15. What Vref or current are the winches set to now, and which ceiling limit and claw mass did you adopt for the 1 lb gate?

**Outlet and station (stories 7 and 9)**
16. After the 40 deg outlet cone problem, how does the gen-2 station handle line angle (outlet ring, cone, no guide), and why? And why did you move from the parametric CAD to SolidWorks on Oct 7?
17. What did the gen-1 plate tests in photos 05 and 13 show (revision, weight lifted, duration, any slip, creep or breakage)? What retains the slide-in housing, and what load did you check it against?

**Distributed electronics and calibration (stories 8 and 10)**
18. What bothered you most about the central controller in October (harness length numbers, the one-plug goal), and do you still plan a central-stepping fallback for the 1 lb demo?
19. What observation led to the D26 decision and the "reel each cable in turn" slack probe, and is any hardware test of it planned before the panel?

**Timeline and ownership**
20. The first commit is 2026-07-16 (simulator, BOM, tentacle CAD) but the outline says Aug 6. What is the true project start date? Which printer and filament did you use for the fit-critical parts (K1 or K1 Max, brand), and which of the stories above can you tell as "I measured it myself"?

---

## 4. Record conflicts and gaps to fix before the deck is final

1. **Start date and timeline.** Outline v2 slide 3 says gen 1 ran Aug 6 to Sep 2. Git shows the first commits (simulator, BOM, tentacle CAD, shopping list) on 2026-07-16, and shopping-list and wireless-claw decisions on 07-16 and 07-17. The Oct 1 to 6 parallel-stream documents are not on the outline timeline at all.
2. **Rev C numbers.** DESIGN_STATE and the outline say "roller 5 mm off in X, 10.5 mm in Y". The rev C report's own numbers: roller at X = 70.0 against a line at 65.0 (5.0 mm from the line centre, a 0.25 mm gap to the edge of a 5 mm bead against ≥ 1.5 mm required overlap) and Y = −10.5 mm. Use the report numbers on a slide.
3. **Line diameter** is 0.5 mm, 0.6 mm or 1.0 mm depending on the file (T22).
4. **Supply voltage** was 18 V on the meter and 12 V on the label, feeding a 20 V-limit buck (T15).
5. **Claw mass budget of 450 g** (REQUIREMENTS R7, capacity calculations) against a v6 CAD upper bound of about 2.06 kg (T35, T36). The capacity story cannot be told without a weighed number.
6. **Jaw travel** is 60 deg in the outline (slide 10) and in R5, and 51 deg in the v6 measurement.
7. **R5 and the module.** The review assumed module 1 and 6 mm; V3, a day earlier, already used module 1.5 and 16 mm (T34).
8. **Fin penalty.** The outline says the 44 x 150 fin "gives up only ~3 C" against a 100 x 100 plate; the commit numbers are about 3 C at 1.0 A but about 7 C at 1.5 A (T31).
9. **D1 versus RESEARCH.md** on which gripper was the primary pick (T03).
10. **Coupon claim.** Outline slide 8 describes a fit-coupon photo with measured insertion results; the record contains none.
11. **Outline wording to remove.** SPACEX_OUTLINE.md slide 3 ("Who did what") and the "Questions to rehearse" list still refer to an AI assistant and how it was used. The deck must not mention AI tools, so those lines need rewriting in terms of what Jasper did and decided (that file was not edited here).

---

## 5. Answers from Jasper

**Q14 (part), why an aluminium tube (2026-10-20).** "I wanted to use an
aluminum tube to reduce creep because we want a long length ... so that the
camera can see everything, then we don't want to use some type of filament
here." Story notes:
- The arm must be long so the camera on the upper housing sees the jaws and
  the floor around them. A long printed arm under constant load creeps (time-
  dependent strain at constant stress) and would slowly shift the camera
  relative to the jaws, i.e. the camera-to-gripper calibration.
- Creep is the right term for the arm (constant load). Stress relaxation
  (stress decaying at constant strain) is what happens in the printed collars
  and press fits that grip the tube, so the tube joints need a positive lock
  (the v6 collar cross-hole has no matching hole in the tube yet).
- Trade-off to show: v6 tube 28.54 OD x 3 mm wall x 304.8 mm = ~198 g of the
  450 g claw budget. A 1 mm wall at the same OD is ~71 g (36 % of the mass)
  with ~41 % of the bending stiffness, still ~14x stiffer than a PETG tube of
  the 3 mm-wall size (E 69 vs ~2 GPa).
