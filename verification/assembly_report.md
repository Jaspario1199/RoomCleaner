# Claw assembly — integration verification report

Integrator: integration-agent (Sonnet). Assembled from `cad/parts/*.py`
(all PASS per `verification/claw_parts_report.md`, dated 2026-07-27) and
`cad/interfaces.py`. Read-only against part files; edited only
`cad/export_all.py` (registered the 3 new parts + rebuilt `build_assembly()`
to the real standoff stack-up) and this report. Date: 2026-07-27.

Reproducible via `cad.export_all.placed_components()`, which returns every
claw component individually positioned (no boolean union) in the
`effector_frame`'s own build frame: plate `z ∈ [0, 5]`, corner bosses to
`z = 8`, plate TOP at `z = 5`, frame UNDERSIDE (standoff attachment) at
`z = 0`.

## Positions used (as built in `cad/export_all.py`)

| Component | Built span (local z) | Transform | Assembled span / position |
|---|---|---|---|
| standoff ×4 | z ∈ [0, 40] | translate z = −40; XY at `(HUB_MOUNT_R·cosθ, HUB_MOUNT_R·sinθ)`, θ ∈ {36, 108, 252, 324}° | z ∈ [−40, 0], r = 27 |
| hub | z ∈ [0, 12] | translate z = −(STANDOFF_LEN + HUB_THK) = −52 | z ∈ [−52, −40], top face at −40 |
| finger ×5 | z ∈ [0, 70] | rotate 180° about X; rotate (deg+90)° about Z; translate `((pocket_r − H_BASE/2)·cosθ, (pocket_r − H_BASE/2)·sinθ, −40)`, θ = 360·i/5 | mounting face flush at z = −40; base solid fills [−52, −40]; shoulder at [−54, −52]; tip at z = −110 |
| tendon_drum | z ∈ [0, 12.4] | translate z = −18.4 (drum top at DRUM_TOP_Z = −6) | z ∈ [−18.4, −6], centered on axis |
| electronics_cover | z ∈ [0, 44.4] | translate z = +5 (EFFECTOR_THK) | rim at z = 5 (plate top), roof at z = 49.4 |

**Correction found and applied (finger radial placement):** the finger part's
local frame is centered on its own axis in X (`W_BASE`, ±8 mm) but is
**not** centered in Y — `H_BASE` runs from the ventral face at local `y=0`
to the dorsal face at `y=H_BASE` (13 mm), not `±H_BASE/2`. Placing the
finger's translation origin directly at `pocket_r` (as the pre-standoff
legacy `build_assembly` did) therefore pushes the finger's actual
cross-section center `H_BASE/2 = 6.5 mm` too far outboard, overlapping the
hub by ≈445 mm³ (confirmed by direct probe — see check 3a below). Fixed by
translating to radius `pocket_r − H_BASE/2 = 27.8 mm` instead of `pocket_r`.
This is an assembly-placement correction, not a part redesign — no part
file was touched. Recommend Fable review whether the pre-standoff legacy
`build_assembly` (now replaced) had the same latent bug.

## Check 3a — pairwise boolean interference (expect ~0 mm³, tol < 1 mm³)

Method: each component built individually via `placed_components()` (no
union), then `Workplane.intersect()` pairwise; volume of the intersection
compound measured directly (not via a probe).

| Pair | Max overlap (mm³) | Result |
|---|---|---|
| frame vs standoffs | 0.000000 | PASS |
| frame vs hub | 0.000000 | PASS |
| frame vs fingers | 0.000000 | PASS |
| frame vs drum | 0.000000 | PASS |
| standoffs vs hub | 0.000000 | PASS |
| standoffs vs fingers | 0.000000 | PASS |
| standoffs vs drum | 0.000000 | PASS |
| **hub vs fingers (critical)** | **0.000000** (all 5, worst pair reported) | **PASS** |
| hub vs drum | 0.000000 | PASS |
| fingers vs drum | 0.000000 | PASS |
| cover vs frame | 0.000000 | PASS |

Before the radial-placement fix, hub-vs-fingers measured 445.1 mm³ overlap
(finger_0 worst case) — a real interference, not a false positive; the fix
above resolved it to exactly 0.000000 mm³ across all 5 fingers, confirming
the 0.2 mm/side slot clearance (`POCKET_H/W` vs `H_BASE/W_BASE`) and the
corrected `FINGER_SHOULDER_Z0` shoulder placement are both geometrically
sound. **Check 3a: PASS.**

## Check 3b — slot engagement (expect > 90% of base_solid volume)

Method: intersect each assembled finger with a slab spanning the hub's
full z-range [−52, −40]; compare to the finger's local base-solid volume
(`intersect(local_finger, slab z∈[0, BASE_SOLID=12])` = 2210.33 mm³,
computed independent of the assembly transform).

| Finger | Engaged volume (mm³) | % of expected | Result |
|---|---|---|---|
| finger_0 | 2210.33 | 100.00% | PASS |
| finger_1 | 2210.33 | 100.00% | PASS |
| finger_2 | 2210.33 | 100.00% | PASS |
| finger_3 | 2210.33 | 100.00% | PASS |
| finger_4 | 2210.33 | 100.00% | PASS |

100% engagement is expected here (not just >90%): the through-slot depth
(`HUB_THK = 12`) exactly equals the finger's un-notched `BASE_SOLID = 12`,
so the entire base-solid section is a rigid-body copy of the same material
mapped into the slab by the assembly transform. **Check 3b: PASS.**

## Check 3c — clearances (reported numbers)

| Clearance | Expected | Measured | Result |
|---|---|---|---|
| Drum flange (R16.5) to nearest standoff inner face (R = HUB_MOUNT_R − STANDOFF_OD/2 = 22.0) | ≈5.5 mm | **5.500 mm** | PASS |
| Drum bottom (z) to hub top (z) — tendon working gap | −18.4 / −40 (given) | drum bottom **−18.400**, hub top **−40.000**, gap = 21.600 mm | matches spec exactly |
| Fingertip z, cross-checked against EFFECTOR_REACH_M (cable plane z = +8) | ≈−124 (task estimate); 8 − 130 = −122 (from EFFECTOR_REACH_M) | **−110.000** (measured, min over 5 fingers) | **flag — see note** |

**Reach discrepancy note:** measured reach (cable plane z=8 to fingertip
z=−110) is **118 mm**, vs. the `EFFECTOR_REACH_M = 0.130 m` (130 mm)
parameter in `cad/interfaces.py` (D9) — a 12 mm / ~9% shortfall. This
follows directly and unavoidably from the literal placement instructions
(mounting end flush with hub TOP at z=−40, finger length 70 mm fixed by
`FINGER_LEN`): total drop = STANDOFF_LEN(40) + FINGER_LEN(70) − cable-plane
offset(8) = 102 mm... reconciling exactly requires either the finger to
mount flush with the hub BOTTOM (which D5's through-slot/shoulder design
explicitly forbids — the shoulder bears on the underside, not the topside)
or `EFFECTOR_REACH_M` to be re-derived from the corrected 40 mm standoff
stack-up. This is a **parameter/geometry reconciliation item for the Fable
lead**, not an interference defect — no boolean overlap exists, and no part
geometry was altered. Flagging in lieu of independently deciding which
value governs, per integration-agent's no-redesign restriction.

## Check 3d — assembly STEP export/reimport (tol ≤0.1 mm bbox, ≤1% volume)

Full assembly (mechanism + cover) exported to `cad/step/claw_assembly.step`
and reimported via `cq.importers.importStep`.

| Metric | Original | Reimported | Diff | Result |
|---|---|---|---|---|
| Volume (mm³) | 186547.65 | 186547.65 | 0.0000% | PASS |
| Bbox (mm) | 98.800 × 98.800 × 159.400 | 98.800 × 98.800 × 159.400 | 0.0000 / 0.0000 / 0.0000 | PASS |

**Check 3d: PASS.**

## Check 3e — renders / exports

- `cad/previews/assembly.png` — mechanism (frame + 4 standoffs + hub + 5
  fingers + drum) rendered **without** the cover, via the existing
  `render_stl` helper. Visually confirms the corrected stack-up: plate on
  top, standoffs and hub below, fingers hanging tip-down with ventral
  V-notches visible, no visible interference. **Generated, PASS.**
- `cad/step/claw_assembly.step` — full assembly **with** the electronics
  cover included, exported for the SOLIDWORKS handoff. **Generated, PASS.**

Note: the mechanism union resolves to **2 disjoint solid bodies** in the
compound — (1) frame + standoffs + hub + 5 fingers (all touching/screwed
together, 138994.8 mm³) and (2) the tendon drum, floating free in the
standoff cavity (6913.9 mm³). This is expected, not a defect: per D4/D3 the
drum has no printed-part contact with anything else in the claw — it is
retained only by the servo horn screw (through the plate, not modeled here)
and free to rotate to wind the tendons. Two solids in one STEP compound is
the correct topology for this joint.

## Mass-rollup / prior verification cross-reference

Not re-derived here (out of integration-agent's scope); see
`verification/claw_parts_report.md` check 4 (419.20 g vs 450 g budget,
PASS) — unaffected by assembly placement.

## pytest

```
python -m pytest tests/ -q
71 passed in 12.11s
```

No test file was touched; count matches the pre-integration baseline in
`verification/claw_parts_report.md`.

## Summary

| Check | Result |
|---|---|
| 3a — pairwise interference (incl. hub-vs-fingers, cover-vs-frame) | **PASS** (all 0.000000 mm³, after radial-placement fix) |
| 3b — slot engagement | **PASS** (100% of expected, all 5 fingers) |
| 3c — clearances | drum-standoff 5.500 mm (PASS vs ≈5.5 mm); drum-hub gap 21.600 mm (matches spec); fingertip reach 118 mm vs 130 mm nominal — **flagged for Fable**, not a geometry failure |
| 3d — STEP round trip | **PASS** (0.0000% volume, 0.0000 mm bbox) |
| 3e — renders/exports | **PASS** (assembly.png without cover; claw_assembly.step with cover) |

One real defect was found and fixed during integration: the finger radial
placement (translation origin vs. cross-section centroid mismatch),
previously causing ≈445 mm³ of hub/finger interference. All other placements
matched the literal stack-up instructions with zero interference. The
`EFFECTOR_REACH_M` vs. measured-fingertip discrepancy (118 mm vs. 130 mm) is
a parameter-reconciliation item, not a geometric defect, and is escalated
to the Fable lead rather than resolved unilaterally.
