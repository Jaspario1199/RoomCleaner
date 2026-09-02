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
