# Design State

## Repository adaptation map (per CLAUDE.md structure)
- parameters.py → `cad/params.py` (re-exports contracts from `cad/interfaces.py`)
- interfaces.py → `cad/interfaces.py` · materials.py → `cad/materials.py`
- parts/ → `cad/parts/` · exports/ → `cad/step/`, `cad/stl/` · renders/ → `cad/previews/`
- tests/ → `tests/` (pytest) · calculations/ → `calculations/` · verification/ → `verification/`

## Current gate
Gate 4 (bounded implementation) — Gates 1–3 recorded this session:
REQUIREMENTS.md, DECISIONS.md (D1–D10), calculations/claw_integration.md (C1–C6).

## Architecture (claw integration pass, two-pass reviewed)
Inverted MG996R on plate → flanged tendon drum (bottom tie-offs, reachable
through hub bore) → 40 mm standoffs on unified Ø54 bolt circle at
[36°,108°,252°,324°] → hub with THROUGH finger slots → shouldered TPU fingers.
Electronics strapped on plate top under a screwed cover (switch/USB cutouts,
corner cable notches).

## Known risks / open items
- Latent bug FIXED in contracts, pending in geometry: frame used r=27 @45°+90k,
  hub used r≈23.6 — both must be regenerated to the shared contract.
- MP1584 3 A vs servo stall marginal (D10) — electronics BOM watch item.
- C1 travel assumption (full notch closure) to be trimmed at bench test.
- Jeans-size wrap volume may want FINGER_LEN 70→90 (parameter change only).

## Gate 4 complete (this session)
1. ✅ calculation-checker: C1–C6 reviewed — caught servo-throw/firmware
   inconsistency (100° vs 120° — would have undersized the drum), stale R18,
   mass-rollup arithmetic (406 g). Contracts corrected; report in verification/.
2. ✅ cad-implementer A: standoff (10×10×40), tendon_drum (33×33×12.4),
   electronics_cover (98.8×98.8×44.4) — contract-sourced, lead-reviewed.
3. ✅ cad-implementer B: hub through-slots + unified bolt circle, finger
   shoulder (bbox 20×17×70) + NOTCH_GAP import, frame ear-taps/cover inserts,
   EFFECTOR_REACH=0.13 + GRAB_Z derived, GRIP_ANGLE 120→140, firmware /setup.
   Known: tests/test_hardware.py "G 120" assertion stale → verifier owns fix.

4. ✅ geometry-verifier: ALL PASS — 6 parts exact bboxes, bolt-circle identity,
   through-slots, drum capacity 28.27 mm, cover/frame alignment, STEP round-trips
   0.0000 diff; mass rollup 419.2 g ≤ 450 (A3). 42 new geometry tests.
5. ⚠→✅ LEAD-CAUGHT SPEC ERROR before integration: finger shoulder was specced
   at the mounting end (z 0–2), which would have blocked slot insertion
   entirely. Contract corrected (FINGER_SHOULDER_Z0 = HUB_THK, both now in
   interfaces.py; hub imports HUB_THK), finger fixed, stale test updated.
   71/71 pytest green.

6. ✅ integration-agent: real stack-up assembled; pairwise interference all
   0.000 mm³ (after catching a 6.5 mm finger placement offset, D11); slot
   engagement 100 % ×5; drum↔standoff 5.5 mm; assembly STEP round-trip exact.
   Reach measured 118 mm → contract corrected (D12). 71/71 pytest.

## Gate 7 audit notes (lead, this session)
- (low) DRUM_TOP_Z = −6 is assembly-local; verify real MG996R spline+horn
  stack-out below the plate at bench; adjust drum z or GRIP tuning if needed.
- (med) Tendon bend at hub guide-hole exits: chamfers specified, friction not
  modeled — bench item with Dyneema.
- (low) Cover↔servo wire routing clearance unmodeled (42 mm inner height OK).
- Physical validation plan: print frame + standoffs + hub + drum + ONE finger
  first; verify slot fit, shoulder seating, tendon travel ≈27 mm, THEN print
  the remaining fingers and the cover.

## Tier 2 closure (winch-side verification + docs)
- geometry-verifier swept the 5 pre-discipline parts: motor_mount,
  camera_mount, camera_mount_overhead PASS. Two REAL defects found:
  winch_spool D-flat was a geometric no-op (cut box ended at the bore
  surface); corner_guide ear walls 0.15 mm (unprintable).
- cad-implementer repaired both (flat via bore-cutter ∩ half-space, wall
  2.100 mm exact; EAR_PLATE_T=7.0, walls 1.65 mm) and correctly ESCALATED a
  defective verifier test (hardcoded nominal arithmetic, never probed the
  solid). Lead authorized and rewrote the test to probe built geometry.
- Fastener-length contracts trued (hub-side standoff M3x16; finger retainer
  M3x12); cad/README assembly procedure + insert map rewritten to the real
  D2-D8 stack-up, incl. single-finger validation print.

## corner_mount cycle (D13, user-initiated: rigid anchors replace eye hooks)
Full Gate 4→5 loop on the new part, 3 defects caught by process:
1. Lead spec was self-contradictory on fleet alignment; implementer correctly
   flagged instead of silently resolving, but chose a layout where the line
   pays off perpendicular to the pulley groove. Lead ruling: spool axis ∥
   pulley axle, drum mid-plane coplanar with groove plane. Repaired.
2. geometry-verifier found gussets intersecting the NEMA 17 motor-body
   envelope (70.42 mm³ — motor couldn't seat). Repaired: wall 56 mm, gussets
   driven off real body half-width + 2 mm; BASE 138×65, mass 88.76 g ≤ 90.
3. Verifier test-audit: several nominal-only assertions upgraded to
   solid probes; boolean interference regression tests added (proven to fail
   on the pre-repair geometry). Residual low-risk gap: fleet-angle test is
   still arithmetic-only.
Re-verification: all measurements reproduced independently, both
interference volumes 0.000 mm³, STEP round-trip exact. FACE_TO_SPOOL=0
assessment: spool rub-gap ≤2 mm is the assembly ceiling (documented in
cad/README.md); at 2 mm, worst-case fleet ≈9° < 15° threshold.
Watch item: back-margin behind wall is 10.5 mm vs GUSSET_RUN=10 (0.5 mm
slack) — re-check if gussets are ever enlarged.

## Pending physical measurements (user's calipers unavailable — blocking two prints)
- MG996R round plastic disc horn: outer diameter, thickness, opposite
  screw-hole spacing → sets HORN_POCKET_DIA (+depth) → tendon_drum print.
- Motor shaft across-flat: D-flat CONFIRMED visually on the 17HS4401s;
  MOTOR_SHAFT_FLAT=0.5 assumed (standard). Caliper check ≈4.5 mm across the
  flat when available; winch_spool cleared for a single fit-test print
  meanwhile.

## Current gate
Gate 6 complete for the claw; corner_mount verified (Gate 5) →
release-candidate items remaining: SOLIDWORKS review (claw_assembly.step),
physical validation plan, winch-corner assembly preview incl. corner_mount.

## Last verified state
130/130 pytest; 12 parts exported and verified; claw_assembly.step
round-trips exactly; corner_mount re-verified at commit a9c1a51.

## Local bring-up findings (software + camera session, 2026-08-12)
Separate from the CAD workflow — no `cad/` files changed. The software + live-
camera milestone was brought up on-machine and a browser console app was built
(see `BRINGUP_LOG.md` and `docs/APP.md`; live camera = innomaker index 1).

Two CAD **casing gaps** surfaced while auditing the BOM against the exported
parts — components in `docs/BOM_ORDER.md` that are mounted but have no printed
enclosure/bracket (candidates for a Gate-4 pass if the user wants them):
1. **Base-station controller enclosure** — Arduino Uno + CNC shield + 4×
   A4988/DRV8825 + fuse/wiring. `electronics_cover` covers ONLY the effector's
   servo/ESP32/LiPo; there is no case for the ground controller.
2. **Limit-switch (KW12-3) mount** — `corner_mount` unifies the NEMA-17 bracket
   + pulley redirect only (no switch pocket); no dedicated switch bracket
   exists. Homing (`docs/FIRMWARE.md` "S switch test") needs these mounted.

Everything else being mounted (4× motors → corner_mount, spools, overhead cam →
camera_mount_overhead, servo, effector electronics, the whole claw) already has
a printed part with a committed STEP.
## Operator dashboard (software interface milestone)
`python -m roomcleaner.app --sim|--live` — Flask + single-page dark UI:
MJPEG live feed (sim renders a top-down synthetic camera; live wires the
real Webcam+YOLO), status cards, per-cable tension bars vs [0.5,40] N,
plan-vs-executed operations log, mission controls + guarded jog pad
(workspace clamp + fan keep-out server-side), room/fan/hamper settings.
Lead-verified headless (Playwright): mission runs real-time, jog moves
pose when idle and is disabled while running, settings drawer OK, no JS
errors. 141/141 tests. Live mode needs bench validation (see docs/APP.md).

## Console convergence (next bounded software task — run on the CAMERA machine)
Two consoles were built the same day on opposite sides (local: live
perception console `scripts/live_app.py` : 8000, validated on the real
innomaker; cloud: operations console `roomcleaner/app` : 8010, validated in
sim). Target: ONE app — the operations console's session/command
architecture absorbs the perception console's proven capture/inference
threading (as LiveSession's feed) and its plan/3-D panels. Must be executed
and validated where the camera is; docs/APP.md documents both until then.

## CAD gap closure (both local-session findings resolved)
1. corner_mount rev B: KW12-3 homing-switch boss (bead-trips-lever), M2
   slots + zip-tie fallback, ±5 mm adjustability; verified, committed.
   Bench items: confirm switch dims (~20 mm body / 9.5 mm hole pitch) on
   the purchased units; set lever reach in the slots with the line strung.
2. base_station_case (tray + lid, 135.15 g): full loop took 2 verification
   passes + 2 repairs, 5 real defects caught pre-print — mid-air
   countersinks (workplane-centroid trap), USB port rotated 90°, lid posts
   inside the Uno footprint, one Uno hole coordinate 1.27 mm off vs a
   KiCad footprint, and zip-tie holes merging across the motor↔endstop
   port boundary (fixed by Z-flanking; also cured a 0.75 mm sliver on the
   input wall). Final verdict PASS; 185/185 tests. Assumption on record:
   CNC-shield connector heights are estimates absorbed by oversized
   strain-relieved ports.
Print queue when the printer returns: 4× corner_mount (rev B), 1× spool
fit-test, claw stack (frame/standoffs/hub), base_station_case tray+lid,
camera_mount_overhead. Still gated: tendon drum (horn measurement), fingers
(TPU).

## Console convergence — DONE (8/13)
One app now: `python -m roomcleaner.app` (--sim | --live --camera N |
--live --demo), port 8000. The operations console's session architecture
absorbed the camera-validated capture/inference pipeline (now
roomcleaner/app/perception.py), detected-items panel + conf slider, plan
panel (per-target A–D cable lengths/tension/reachability), 3-D room view +
animate-plan GIF. roomcleaner/webapp deleted; scripts/live_app.py is a
forwarder. Lead-verified headless in --sim (mission playback) and
--live --demo (real detect→plan pipeline, motion correctly 409-gated,
camera-only banner). 192/192 tests. Outstanding: the physical-camera smoke
test on Jasper's machine (local agent's first task per UPDATE_8-13.md),
plus the pre-existing live-motion bench items (docs/APP.md).

## Camera case — DONE (8/28)
New part camera_case_overhead (shell + bezel) fully encloses the innomaker
board on the ceiling: 56x56 plate + 24.6 mm skirt, board on 10 mm M2
standoffs (28 mm pitch imported from camera_mount_overhead), O18 lens
opening in a screw-on bezel, cable exit through-plate or side notch at USB
level. 45.0 g PETG (60 g budget). Independent verification PASS (52/52;
verification/camera_case_overhead_report.md). It supersedes the open
camera_mount_overhead bracket in the print queue (bracket file retained).
VERIFY before printing: 28 mm board hole pitch; lens-barrel OD (O18 opening
assumes M12). Watch items: skirt wall measures exactly the 2.4 mm floor;
side notch fits a flexible cable, not a rigid strain-relief boot.
Corner pulley ruling (8/28): BUY complete 3 mm-bore U-groove bearing
pulleys (OD 18-22, width <10 mm, ~10-pack) + M3x25 bolts/nylocks/washers;
printed sheave is fallback only. Corner_mount junction stresses checked:
ears 5.5 MPa worst-case (SF ~5 vs PETG layer adhesion), wall <0.5 MPa.

## Bench bring-up — Phases 1–5 DONE (8/28, live session)
Phase 2: 14 caps seated (12 microstep + 2 A-axis D12/D13). Phase 3: ALITOVE
plug cut, meter-identified + lead, 7.5 A inline fuse, shield terminal reads
**18 V** (brick label still to be read; within 12–36 V shield / 35 V A4988
spec — never feed the Uno barrel jack from it). No VMOT LED on this clone;
the meter reading is the checkpoint. Splice is twist + duct tape: REDO with
solder/heat-shrink or a lever nut in Phase 6. Phase 1: firmware flashed,
READY / POS / SW verified. Phase 4: drivers confirmed R100, all four Vref
set 0.75–0.85 V. Phase 5: one SIMAX motor spun 1 rev out/back on X, Y, Z
and A — 4th-axis mapping proven. Next: Phase 6 limit switches (soldering).

## corner_mount rev D — homing switch below the pulley, VERIFIED (8/28)
D14 implemented: mid-span switch boss removed; KW12-3 now sits on a
horizontal pad atop a drop arm beside the vertical line (roller at
DROP_X = EAR_CX + CORNER_PULLEY_OD_NOM/2, Y=1.0, Z=56.5 local); a
descending bead presses the roller toward the pad (-Z = reel-in). Rev C
(switch on the arm's vertical face) FAILED independent verification --
roller 5 mm off in X, 10.5 mm in Y (verification/corner_mount_revC_report.md);
rev D PASSES (verification/corner_mount_revD_report.md), plus D.1 fixes:
zip groove moved to Z 34.5-38.5 clear of the M2 pilots, r=3 corridor
notch at the pad front (0 mm^3 intrusion). Mass 96.29 g / 105 g budget.
100 corner-mount tests green. STL current -> print the 4-off set from this.
Caliper-verify on a KW12-3 in hand: roller overhang past body end
(assumed 1.5 mm), roller rest height above mounting face (12 mm),
hinged end (assumed far end). Trigger height is set by bead placement
(~4 mm below the roller contact). Bead nominal O5 (local assumption,
KW_HOMING_BEAD_DIA_NOM).

## Generation 2 — SolidWorks redesign recorded (10/19)
Between Sep 2 and Oct 19 Jasper redesigned the system in SolidWorks (Drive):
removable wall station (frame + slide-in housing + shell, v1–v3), shortened
spool (v1–v3), per-station XIAO ESP32 + A4988 + buck electronics, and a 3:1
geared two-jaw clamp gripper (Claw_V1, V5). Recorded as DECISIONS D15–D19;
history in docs/DESIGN_HISTORY.md; file manifest in solidworks/README.md.
Generation-1 CadQuery design, tests and reports are kept, not purged.
Bench: one gen-2 station jogged its motor and read its homing switch; a
no-motion fault was traced to a bad 3.3 V logic connection (~1.14 V).
Design review: verification/design_review_gen2.md (calcs:
calculations/gen2_screening.py). Presentation: SpaceX onsite Oct 27, draft
due Oct 22 — docs/presentation/SPACEX_OUTLINE.md.
Next: sync the remaining SolidWorks files + STEP exports into solidworks/,
then measure the gear module/face width and the slide-in retention.

## Gen-2 updates (10/19, later)
- All gen-2 SolidWorks files synced into solidworks/ (BOM .xlsm still
  Drive-only). Spool v3 measured: Ø36 × 22, Ø15 core, 16 mm drum, Ø5.45
  D-bore. The bore was opened from v2's Ø5.2 because v2 printed too tight on
  the shaft (Jasper, confirmed).
- Capacity (review R10): worst-case total suspended weight anywhere at
  1.0 A is 1.0–2.3 lb depending on the ceiling limit, ~25 % less with one
  slack cable. The 1 lb gate (plus ~1 lb claw) needs a tension-aware
  ceiling, a weighed and lightened claw, or 1.5 A drivers.
- Structural design load per cable: 32 N at 1.0 A, 48 N at 1.5 A (stepper
  slip limit, empty spool).

## Codex branch work imported (10/19)
Imported from `codex/design-history-2026-10-14` (which descends from
`codex/verified-laundry-cycle`) every file it **added** (106 files: station Rev C
electrical, local_station bench firmware + C++ tests, encoder_feedback,
moving_camera, startup calibration V1 spec + observability study, room layout,
history/decision records, design-resolution ledger, presentation history) and
its updates to REQUIREMENTS.md, docs/BOM_ORDER.md, docs/SHOPPING_LIST.md.
Its **deletions** of the gen-1 package, CAD, tests and reports were NOT applied
(gen-1 preserved per Jasper). Where both branches edited DECISIONS.md and
DESIGN_STATE.md, this branch's versions are kept and Codex's are archived
verbatim in docs/history/codex_DECISIONS_20261019.md and
docs/history/codex_DESIGN_STATE_20261019.md (README likewise). Three tests in
tests/test_encoder_feedback.py reference central-relay files Codex itself
removed; they are skipped with that reason, not deleted.

## Control system V1 — logic complete in simulation (10/19)
`roomcleaner/cdpr/` now holds the whole gen-2 control stack, specified in
`docs/CONTROL_SYSTEM_V1.md`: station protocol + reference core, synchronized
coordinator (feed-hold in path time, leases, lossy-network tolerant), trust
ledger, marker vision with ambiguity handling + gravity fusion, self-calibration
(MAP fit in the marker frame, slack-cable hypothesis selection, identifiability,
D-optimal staged excitation, witness validation), bounded startup sequencer,
bead verification with a safety-derived gate and joint refit, supervisor
(no auto-resume, visual recovery, controlled lowering, confirmed disarm),
pickup/delivery tasks, phone setup service, claw S3 firmware + host client,
and the station core in C++ (conformance-tested against Python).
- Evidence: `pytest tests/cdpr tests/firmware` (simulation only). Full lifecycle
  passes; unattached cable, swapped wiring, covered marker, unsafe config, low
  battery, station reboot and bead disagreement are all caught.
- Finding: vision alone leaves absolute cable length at sigma ~20 mm, so with
  12 mm bead overtravel every bead is BLOCKED and the robot runs LOCAL_ONLY.
  Open decision D-B (more overtravel clearance / IMU+marker board / taped line
  length / accept switch+stall backstop).
- Open decisions: D-A tension sensing (series spring recommended), D-B,
  D-C power-loss holding (measure back-drive), D-D garment perception on
  hardware, D-E station addressing.
- Nothing has run on the physical four-station rig. Next physical step:
  commissioning steps 1-4 (doc §10) on one XIAO-C3 station.

## Independent review of control V1 — findings fixed (10/19)
`verification/control_system_v1_review.md` (independent reviewer; 3 Critical,
4 High, 12 Medium). Lead disposition at the end of that file. Fixed: idle host
loop (no silent lease faults), software recovery/lowering after lease stops and
host restarts (model persisted), fail-closed `claw_supported` with durable
writes, disarm only after a fresh vision floor check plus a per-boot station
disarm key, hold resend, exception-safe motion, pause in every state, session
token on the operator API, measured-dt path time, dynamic tension margin.
Open before any hardware bead search: station-enforced travel floor (D-F).

## Station cover v4 — concept only, not adopted (10/19)
`cad/parts/station_cover_v4.py` (fin alcove, perfboard/buck bosses, vents,
USB port; built from Jasper's v3 Shell_Casing) is kept as a reference concept.
Jasper is designing the cover himself in SolidWorks; the independent
verification was stopped and this part is NOT verified or released. Useful
numbers for his design (station frame: origin on the motor shaft at the
flange, x out of the wall, z up): fin occupies y[-T,0], x[-22,22], from
z=-21; motor back face moves to y=-38-T (only 0.33 mm to the old shell's
inner -y wall with T=4.76 — relieve that wall); motor top z=21.15, slip-in
pin top z≈24.9 (alcove floor ≥ 25.5); 12 mm air gap per fin face; the fin
slot must run out to the mating rim at x=-21.15 so the cover slides on.

## Floor-reference study for D-B (10/20, simulation only)
User proposal: a printed multi-tag reference of known size on the floor,
scanned at startup. Study: `scripts/sim_floor_reference_study.py`, report
`verification/floor_reference_study.md` (3-5 seeds per case; sim-only hooks
`SimCamera(board=...)` and `StartupSequencer.study_board`, both off by default).
- A 1.0-1.5 m board cuts predicted absolute length sigma from ~25 mm to
  ~10-12 mm (extent matters, tag count does not), then plateaus: the
  excitation box, the 5 cm anchor priors and length noise dominate. No board
  size reaches the 2 mm bead gate (12 mm overtravel).
- Finding (lead-flagged, unresolved): with the precise board the fit becomes
  overconfident — actual |L0 error| 7-17 sigma — and accepts its own
  calibration less often (2/5 vs 5/5). Cause per study: a few mm of
  undetected slack on one cable below the 3 mm slack classifier, amplified
  into L0. Fail-closed today (beads BLOCKED, LOCAL_ONLY), but the predicted
  sigma must NOT be used to size a larger overtravel until this is fixed.
- D-B RESOLVED (D26): margins, not bead precision. Full-workspace operation
  when k*sigma_abs <= ceiling/wall margin with an honest sigma; beads become
  end-of-travel switches. Work in order: (1) per-pose slack probe (in
  progress), (2) margin-based trust rule, (3) printable ~1 m floor board +
  multi-tag detection.

## Gripper v7 gearbox redesign — requirements gathered (10/20, not started)
From Jasper (10/20) and the v6 inspection (verification/gripper_v6_inspection.md):
- Bearings: 7x14x5 bearings (five in v6, not in the STEP) sit inside the gears:
  compound lower x1, compound upper x2, follower upper x2. Any redesign keeps
  bearings in the gears (pockets ~Ø14.05 with lip relief or crush ribs) and
  supports every gear shaft on both sides (straddle), with full bearing
  engagement and coaxial seats (v6: lower pin enters only 1.05 mm, seats
  0.40 mm out of line). Prefer Ø7 steel dowel pins over printed Ø7 pins.
- Gearbox may be partly exposed (open frame) but must stay stable; add thin
  guard bands over each mesh so fabric cannot be drawn in.
- Proposal under discussion (awaiting Jasper): 54T -> 36T (2:1), jaw arm
  75 -> ~53 mm from the gear axis (same opening, ~16 N grip per jaw, pinion SF
  unchanged ~2.1); keep the 24:24 sync stage; rim-and-spoke gear webs; centre
  allowance +0.3 mm; bolted horn-to-pinion drive. Uniform scaling rejected
  (tooth stress ~ 1/s^3: 90 % -> SF 1.5, 80 % -> SF 1.07).
- Electrical box is structural: the four lines attach through radial holes in
  its corner fillets. Camera bay (XIAO S3 Sense + MPU6050) is being added to the
  box on the claw's narrow side, wiring into the box below the light top cap.

## Camera bay — pending revision from Jasper's board reference (10/20)
Seeed reference image (cad/reference/purchased/xiao_esp32s3_sense_seeed_dims.webp):
XIAO ESP32-S3 Sense = 21.0 x 17.8 x 15 mm overall INCLUDING the camera module;
the camera (OV3660 on this unit) sits on top of the stack at the USB-C end,
lens facing away from the boards, roughly centred across the 17.8 width; the
Sense board's FPC connector is at the other end. So the stack mounts
lens-down onto the bay window with the lens at the USB-C end (not centred
along the length), and the USB-C is on the base board at the cover side.
The current bay (5b7764d) assumes a 24.363 envelope and a centred lens:
revise the cradle (21.0 + 0.6), lens-window position and USB notch height.
IMU: Jasper solders wires to the BACK of the IMU board -> relief channel under
the header row + wire exit; board dimensions still to come.
Software (in progress): four line attachment points at the inner mouths of
the corner-fillet holes of the electrical box; passive yaw; yaw guard.
Second Seeed reference (cad/reference/purchased/xiao_esp32s3_top_seeed_ruler.png,
top view with ruler): base board 21.0 x 17.8; USB-C receptacle overhangs the
board edge by ~1-1.5 mm; U.FL antenna connector at the corner opposite the
USB-C. Jasper: "lean on the side of bigger so we aren't having to reprint" ->
cradle 23.0 (incl. USB overhang) x 18.6 with soft locating ribs, stack height
allowance 16+, lens window sized for +-4 mm of lens position, IMU pocket for
the Adafruit 3886 (25.6 x 17.8) with a back-side solder relief.
IMU: not yet purchased per the records (docs/SELF_CAD_DIMENSIONS_AND_WIRING_20261006.md lists the
Adafruit 3886 MPU-6050 as selected, "not recorded ordered").

## Gripper v7 gearbox — verified (10/20)
- Open-frame gearbox, 18T→36T (2:1) + 24T/24T sync, module 1.5, six 687
  (7×14×5) bearings on 2× Ø7×50 steel dowels, re-derived jaw four-bar
  (76.5° stroke, tips meet, 91.6 mm open, ≥13.3 N/jaw at 4.8 V).
- Independent verification rev 2: PASS WITH CONDITIONS (72/72 verifier tests,
  34 implementer tests). Repair round 1 added a 0.3 mm 36T/follower axial
  relief and brought all walls ≥1.2 mm.
- Accepted: sync 24T one-jaw SF 1.997 at 6 V stall; 0.20 mm flank clearance;
  36T SF 2.502 (0.1 % over 2.5).
- Open, measure on hardware: servo ear pitch (47.0 in CAD vs 48.3 in
  interfaces.py), 687 inner-race land vs Ø9.7 ring, M2.5 insert vs Ø3.3 hole,
  horn geometry. Tube needs a Ø3.4 cross-hole 14 mm from its lower end.
- Mass: head 481 g CAD / ~376 g as printed (v6: 1044 g). Whole claw still
  ~1.05–1.25 kg as printed vs 450 g budget — budget decision pending
  (proposed: 1.25 A on the existing A4988s → ~40 N → ~650 g claw).
- Tube-length / camera visibility study running.

## Claw tube wall measured (10/20)
- Jasper: the aluminium tube wall is **0.019 in (0.48 mm)**, not the 3 mm in
  the CAD (OD 28.54 / ID 22.54). With OD ~28.5 (likely 1-1/8 in, VERIFY), the
  ID is ~27.6 mm. The tube at 254.8 mm (D28) is ~29 g, not ~166 g
  (−136 g against the CAD mass roll-ups).
- Stiffness/strength (hand calc, 6061 E 69 GPa): I 4,200 mm^4 (vs 19,900);
  10 N side load at 250 mm → 0.18 mm deflection, 8.5 MPa. M3 cross-bolt
  bearing at the 100 N design load → ~35 MPa on two 0.48 mm walls. Fine,
  but a thin wall dents: don't overtighten the cross-bolt; the printed saddle
  must carry the clamp, not the tube. Alloy unknown (VERIFY).
- To do: update GRIPV7_TUBE_ID (and OD if not 28.54) once OD is confirmed,
  then rerun the mass roll-up and the claw CoM for the body-frame refresh.
