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

## In flight
6. 🔄 integration-agent: real stack-up assembly (standoffs/hub/fingers/drum/
   cover), pairwise interference ~0, slot-engagement probe (independent check
   of the shoulder fix), clearance table, assembly STEP round-trip, render.

## Last verified state
71/71 pytest after shoulder correction; all six parts exported and verified.
