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

## In flight (this session)
1. cad-implementer A: NEW parts — standoff, tendon_drum, electronics_cover.
2. calculation-checker: independent review of C1–C6 (parallel, disjoint files).
3. cad-implementer B: MODIFY hub (through slots), finger (shoulder), frame
   (ear taps, cover inserts); software EFFECTOR_REACH + firmware /setup.
4. geometry-verifier: all six parts vs interfaces; report in verification/.
5. integration-agent: assembly rebuild + STEP round-trip + renders.

## Last verified state
29/29 pytest green before this pass; all parts export STEP/STL (pre-contract).
