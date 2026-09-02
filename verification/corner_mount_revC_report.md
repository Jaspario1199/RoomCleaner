# corner_mount REV C — independent verification report

Scope: `cad/parts/corner_mount.py` rev C, the D14 homing-switch relocation
(mid-span boss → drop arm beside the vertical line under the pulley). This
report covers Gate 5 (geometry-verifier role) only, superseding nothing in
the rev B report (`verification/corner_mount_report.md`) except where rev C
explicitly changed geometry.

Verifier: geometry-verifier (Sonnet), read-only against `cad/parts/
corner_mount.py`. Every number below was reproduced independently — built
`corner_mount.make()` directly and probed the actual BRep (OCCT
`BRepClass3d_SolidClassifier` point-in-solid tests, bisection, and boolean
intersection volumes), then cross-checked against a fresh, independently
written test file: `tests/test_corner_mount_revC_verification.py` (26
tests). The implementer's own suite (`tests/test_winch_geometry.py`, 72
tests, includes 38 `corner_mount` tests) was also re-run in full as a
secondary signal — see Section 10.

Authority for expected values: `cad/interfaces.py` (`CORNER_MOUNT_*`,
`CORNER_PULLEY_OD_NOM`), `DECISIONS.md` D14, the assignment's own check 5
model (bead/roller geometry), and the rev B baseline in `verification/
corner_mount_report.md`.

## Summary

| # | Area | Verdict |
|---|---|---|
| 1 | Regression — rev-B features unchanged; mid-span boss removed | PASS |
| 2 | Solid validity, mass, bbox | PASS |
| 3 | Drop arm shape (no overhang), slot types/sizes | PASS |
| 4 | Clearances (pulley, line corridor, csk, NEMA17 body) | PASS |
| 5 | **Bead/roller interception (KEY CHECK)** | **FAIL — severe, both axes** |
| 6 | Trigger height formula + slot bracket | PASS |
| 7 | Printability of horizontally-bored slots | PASS (assignment's "flat span" premise is not what's built — see detail) |
| 8 | STEP round trip, STL, preview | PASS |
| 9 | Ear mirror-symmetry (implementer's test substitution) | PASS |

**Overall: FAIL.** The part is a valid, well-formed, printable single solid
that correctly implements every rev-B regression item and the D14
geometric relocation *as literal geometry* — but the KW12-3 switch, mounted
and oriented exactly as the assignment's own model specifies, cannot
physically detect the stopper bead on the vertical drop line. This is not a
tolerance/adjustment-range problem (the ±5 mm slot travel does not touch
either failure axis); it is a wrong-by-construction mechanism placement.
Not repaired, per instructions.

Reproduce: `python3 -m pytest tests/test_corner_mount_revC_verification.py -v -s`
and `python3 -m pytest tests/test_winch_geometry.py -k corner_mount -v`.

---

## 1. Regression — rev-B features unchanged, mid-span boss gone

Dense probe grid (`x∈[-30,45] step 2, y∈{4,8,12,16,20,24,28,30}, z∈{plate+0.5,
+3,+7,+12}`, excluding nothing — the true rev-B mid-span-boss footprint) found
**zero solid material**: the boss is gone. (An earlier, wider probe pass
that also scanned `x∈[46,55]` did find solid material there — that is the
pulley ear, legitimate pre-existing geometry, not a boss remnant; re-run
excluding the ear/arm block at X≥51.5 to reproduce the clean result.)

Rev-B feature spot checks, all measured directly on the built solid:

| feature | measured | expected | verdict |
|---|---|---|---|
| plate footprint | 138.000 × 65.000 mm | 138 × 65 | PASS |
| plate thickness | `PLATE_T = 6.0` (= `CORNER_MOUNT_PLATE_T`) | 6.0 | PASS |
| 3 countersinks | void top+bottom at x = −55, −5, 45 (y=0) | per rev-B report | PASS |
| wall | `WALL_CX=-40, WALL_THK=6.0, WALL_W=56.0` | unchanged | PASS |
| gussets | 2×, `RUN=10, HEIGHT=18, THK=4` | unchanged | PASS |
| NEMA17 pattern/boss | 0 mm³ vs 42.3×42.3×38 motor-body box (fresh boolean, see §4) | 0 | PASS |
| pulley ears | `EAR_H=28.5, EAR_CX=55.0, EAR_SY=(10,-10)` | unchanged | PASS |
| `SPOOL_DRUM_MID_Y` | 0.0 | 0 (fleet coplanarity) | PASS |

All PASS.

## 2. Solid validity, mass, bbox

- `solids()` count = **1**, `isValid()` = **True**
- `Volume()` = **76155.14 mm³** (76.155 cm³)
- Mass @ PETG 1.27 g/cm³ = **96.717 g**, budget **105.0 g** → **8.283 g
  margin**. Delta vs rev B (92.15 g measured) = **+4.567 g** (rev C's own
  budget was raised +11.5 g for exactly this, so the actual increase is
  comfortably under the raised ceiling).
- KW12 mount's own added mass (both legs) = **8.433 g**, ceiling 10 g — PASS.
- `BoundingBox()`: **138.000 × 65.000 × 60.500 mm**, X:[−69,69] Y:[−32.5,32.5]
  Z:[0,60.5]. Z is now driven by the KW arm (`PLATE_T(6)+KW_ARM_H(54.5) =
  60.5`), taller than the wall (50 mm in rev B) — expected, since D14 raised
  the part's mass/height budget for exactly this arm.

All PASS.

## 3. Drop arm: shape, slot types, sizes

**No-overhang vertical prism.** Both legs sampled solid/void at
`z_local ∈ {2,15,35,52.5}` and confirmed solid at every height (never
floating). The leg's own −X face was bisected at each height: it sits
flush at `KW_ARM_X0 = 57.0` for `z_local ≥ 35` (above the pulley ear); at
lower Z it merges with the ear (wider footprint below, narrower above —
material only ever *adds* going down, never overhangs going up). No taper,
no cantilever. PASS.

**Zip-tie slot — through cut.** Probed void at three X depths (near face,
mid-depth, near back) at both legs' `KW_ZIP_Y` — void at all three. PASS
(matches "always a through-cut" spec).

**M2 pilot — blind, ≥5 mm deep.** Bisected the solid→void transition behind
each pilot slot:

| leg | measured blind depth | spec (`KW12_PILOT_DEPTH`) |
|---|---|---|
| 0 (front) | 5.000 mm | ≥5.0 |
| 1 (back) | 5.000 mm | ≥5.0 |

PASS, exact match, 3.0 mm of solid wall remains behind it (`KW_BOSS_DEPTH −
KW12_PILOT_DEPTH = 8.0 − 5.0`).

**Z-elongation, 10 mm range.** Measured Z void-span of the pilot slot (both
legs): **11.700 mm** = `KW_TRIGGER_ADJ_RANGE(10) + KW12_SELFTAP_PILOT_DIA(1.7)`,
matching the slot2D "length" construction exactly. Zip slot: **14.02 mm** ≈
`10 + KW_ZIPTIE_SLOT_W(4)`. Both PASS (±0.5 mm sampling step tolerance).

All PASS.

## 4. Clearances (fresh boolean intersections, independently built geometry)

| clearance check | volume | verdict |
|---|---|---|
| Pulley envelope Ø22×10 wide, axle at (`EAR_CX`,0,`PLATE_T+AXIS_Z`), axis‖Y | 0.000000 mm³ | PASS |
| Line corridor Ø6, horizontal span (`WALL_CX`→`EAR_CX` @ Y=0) | 0.000000 mm³ | PASS |
| Line corridor Ø6, vertical drop (X=`DROP_X`, Y=0, plate-top→axis) | 0.000000 mm³ | PASS |
| X=45 mm countersink cone — void confirmed top & bottom | void confirmed | PASS |
| NEMA17 motor-body box 42.3×42.3×38, flush on wall −Y face | 0.000000 mm³ | PASS |

All PASS. (Note: the horizontal-span line-corridor check was not previously
covered by name in the implementer's own suite — the rev-B and rev-C repo
tests only probe the vertical drop corridor — so this is new independent
coverage, and it passes.)

## 5. THE KEY CHECK — bead/roller interception: **FAIL**

Modeled exactly per the assignment's own spec: roller center
`X = KW_ARM_X1 + KW12_LEVER_HEIGHT_ABOVE_MOUNT = 65.0 + 5.0 = 70.0 mm`,
roller Ø4.5 mm (range **[67.75, 72.25] mm**). Bead centered on the drop
line at `X_line = EAR_CX + OD/2`, `EAR_CX = 55.0`.

### 5a. X-overlap table (all required OD × bead combinations)

| OD (mm) | X_line (mm) | bead Ø (mm) | bead X-range | roller X-range | **overlap (mm)** |
|---|---|---|---|---|---|
| 18 | 64.0 | 5 | [61.50, 66.50] | [67.75, 72.25] | **−1.250** (gap) |
| 18 | 64.0 | 8 | [60.00, 68.00] | [67.75, 72.25] | 0.250 |
| **20** | **65.0** | **5** | **[62.50, 67.50]** | **[67.75, 72.25]** | **−0.250 (gap) — FAIL, need ≥1.5** |
| 20 | 65.0 | 8 | [61.00, 69.00] | [67.75, 72.25] | 1.250 |
| 22 | 66.0 | 5 | [63.50, 68.50] | [67.75, 72.25] | 0.750 |
| 22 | 66.0 | 8 | [62.00, 70.00] | [67.75, 72.25] | 2.250 |

**PASS bar (OD=20, Ø5 bead) requires overlap ≥ 1.5 mm; measured overlap is
−0.25 mm — a 0.25 mm *gap*, not an overlap.** The roller sits entirely
beyond the bead even for the exact nominal (design-target) pulley OD; a
standard 5 mm bead never touches it.

**Bead diameter that would be needed:** solving
`(X_line + bead_r) − roller_x_min ≥ 1.5` at OD=20 gives
`bead_r ≥ 4.25 mm → bead Ø ≥ 8.5 mm`. An 8.5 mm bead on a line running
through a groove/pulley system sized for 0.5 mm Dyneema is impractical —
notably, this is the same class of problem D14 was written to eliminate
(oversized beads jamming in narrow guides), now reappearing on the
replacement mechanism at an even larger required size than before.

Even the most favorable case in the accepted OD range (OD=22, Ø8 bead) only
reaches 2.25 mm overlap — real but marginal, and requires assuming both the
purchased pulley's OD sits at the top of its accepted tolerance *and* an
oversized bead, neither of which is the part's own nominal design point.

### 5b. Roller Y-reach: **FAIL**

Per the assignment's model: pivot Y = switch body's lever-side (leading)
edge = `KW_BODY_Y_FRONT = KW_BOSS_Y0 + KW_BOSS_LIP = 6.0 + 1.5 = 7.5 mm`.
Lever is 18 mm, fixed hardware, pointing −Y:

```
roller_Y = KW_BODY_Y_FRONT − KW12_LEVER_LEN = 7.5 − 18.0 = −10.5 mm
```

Required: within **±2 mm of Y=0** (the drop line's own Y position).
**Measured: −10.5 mm — off by 10.5 mm, over 5× the tolerance.** The 18 mm
lever massively *overshoots* the 7.5 mm gap between the pivot and the line;
the roller ends up 10.5 mm past the line, in open space beyond the pulley's
own −Y ear, nowhere near the bead's travel path in Y at all. This failure
is independent of the X-overlap failure above — even a correctly-sized
bead would not be struck, because the roller isn't over the line's Y
position in the first place.

### Why the implementer's own test suite didn't catch this

`test_corner_mount_kw12_lever_reaches_drop_line` (in
`tests/test_winch_geometry.py`) only asserts
`KW_BODY_Y_FRONT (7.5) < KW12_LEVER_LEN (18)` — i.e. "the lever is long
enough to physically reach across." That is necessary but not sufficient:
a lever *longer* than the required reach overshoots past the target rather
than landing on it, exactly what happened here. No test in either suite
checks the roller's actual resting *position* (X or Y) against the line's
position — only that a component's own local dimension is "big enough."
This is the geometric error the drop-arm reorientation introduced: rev B's
±8 mm Z corridor made this kind of pivot-offset approximation forgiving
(see the module docstring's own `KW12_LEVER_HEIGHT_ABOVE_MOUNT` discussion);
rev C's tighter, single-axis-critical geometry (both the switch's mount-face
offset *and* its lever throw now act directly along axes the line-contact
depends on) is not forgiving in the same way, and nothing in either test
suite computes the roller's actual resulting coordinates.

Reproducible: `tests/test_corner_mount_revC_verification.py::
test_kw12_roller_x_overlaps_bead_on_drop_line_for_nominal_pulley` and
`::test_kw12_roller_y_reach_hits_the_drop_line` (both new, both FAIL as
designed to demonstrate this).

## 6. Trigger height

```
KW_TRIGGER_Z = PLATE_T + EAR_H + 15.0 = 6.0 + 28.5 + 15.0 = 49.5 mm  (matches formula exactly)
```

Adjustment band ±5 mm → world Z ∈ [44.5, 54.5] must sit inside both slots'
Z void ranges. Measured: pilot slot void Z ∈ [43.65, 55.35] (brackets
[44.5,54.5] with 0.85 mm margin each end — the cap radius); zip slot void Z
∈ [42.49, 56.51] (brackets it with 2.0 mm margin each end — its cap
radius). Both PASS.

## 7. Printability of the horizontally-bored slots

The assignment's premise ("a Z-elongated slot bored along X has a FLAT top
span = slot width") does **not** match what CadQuery's `slot2D` actually
builds here. Measured directly on the standalone leg BRep (not inferred
from source): the pilot slot's Y-width is **constant at 1.705 mm** through
the entire straight-adjustment band, then narrows **smoothly** through the
top end-cap —

| Z above cap base | measured width (Y) |
|---|---|
| 0.00 mm (cap base, = full width) | 1.705 mm |
| 0.35 mm | 1.545 mm |
| 0.425 mm (half the cap radius) | 1.475 mm |
| 0.68 mm (80% of cap radius) | ~1.0 mm |
| 0.85 mm (cap apex = full cap radius) | 0.005 mm (≈0) |

— an exact semicircular arc (`width(h) = 2·√(r²−h²)`, r = 0.85 mm), i.e.
the same self-arching profile as any round horizontal hole, closing to a
point rather than snapping shut across a flat 1.7 mm (or 4 mm, for the zip
slot's 2 mm cap radius) span. **There is no flat unsupported bridge here at
all** — the maximum single-layer "new" span the printer must close at any
point near the top is a fraction of a millimeter, well inside FDM's normal
self-supporting limit for any hole this size. **PASS** — but note this
corrects rather than confirms the assignment's stated premise; the
"exact flat span" the assignment asked me to report is not present in the
built geometry, and the docstring's own printability claim ("self-arching…
same precedent as the NEMA17 boss/bolt holes") is the one that matches the
measured geometry.

Reproducible: `tests/test_corner_mount_revC_verification.py::
test_pilot_slot_roof_is_self_arching_not_flat`.

## 8. STEP round trip, STL, preview

- `cad/step/corner_mount.step` exists (229,272 bytes), reimports as **1**
  solid.
- Volume: built 76155.1415 mm³ vs on-disk-STEP-reimport 76155.1415 mm³ —
  **0.00000% diff** (well under 0.1%).
- Bbox: 138.0000×65.0000×60.5000 both ways — **0.00000 mm diff** (well
  under 0.05 mm).
- A fresh independent export+reimport round trip (bypassing the on-disk
  file entirely) reproduces the same 0.00000%/0.00000 mm result.
- `cad/stl/corner_mount.stl` exists (225,184 bytes).
- `cad/previews/corner_mount.png` exists (48,352 bytes), timestamped after
  the source file — current, no regeneration needed.

All PASS.

## 9. Ear mirror-symmetry (implementer's test substitution)

The implementer changed `test_corner_mount_ear_wall_around_axle_hole_measured`
to probe the −Y ear (`EAR_SY[1]`) instead of the +Y ear, because the +Y ear
now sits directly beside the KW12 drop arm and the arm's material merges
with it (confirmed independently: scanning the +Y ear's own X-footprint at
`z_local=2` finds only **one** edge within an 12 mm window — solid
continues uninterrupted into the arm — vs. the −Y ear, which shows the
expected two edges at exactly `EAR_CX ± EAR_PLATE_T/2`).

Built `_pulley_ears()` **standalone** (no arm/wall/plate) and confirmed the
two ears are true mirror images of each other about Y=0:
- Explicit edge probes: both ears' body X-edges = [51.52, 58.50] (width
  6.98 ≈ `EAR_PLATE_T`=7), identical at both `sy = ±10`.
- Hole-height probes: identical at both ears.
- Random mirror-symmetry probe, 3000 points across the ear's own local
  volume, reflecting Y→−Y: **0 mismatches**.

The substitution is valid and loses no coverage — both ears are built by
the same code path from the same constants and are geometrically identical
before the arm is added; only the −Y ear remains cleanly isolated for a
standalone wall-thickness probe after the union. **PASS.**

## 10. Secondary signal — full existing test suite

```
python3 -m pytest tests/test_winch_geometry.py -v
```
**72 passed, 0 failed** (38 of them `corner_mount`-scoped). This confirms
the implementer's own suite is internally consistent and does not
regress rev B — but per Section 5, it does not check the one property that
actually matters for the mechanism's function (the roller's resulting
world coordinates vs. the line's), which is why an independently-written
check was required to surface the defect.

---

## Reproduce everything

```bash
# New independent verification suite (this report's source data)
python3 -m pytest tests/test_corner_mount_revC_verification.py -v -s

# Implementer's own suite, unmodified, as secondary signal
python3 -m pytest tests/test_winch_geometry.py -k corner_mount -v
python3 -m pytest tests/test_winch_geometry.py -v   # full 72
```

New test file (read-only against `corner_mount.py`, all assertions
independently derived, not copied from the implementer's tests):
`tests/test_corner_mount_revC_verification.py`.

## Recommendation (not actioned — geometry-verifier does not repair)

The X and Y failures in Section 5 are both large relative to their
tolerances (0.25 mm gap against a 1.5 mm bar on X — i.e. the *nominal*
mount is already offset by more than the whole allowed margin from PASS;
10.5 mm off against a 2 mm bar on Y) and are structural to the current
mount-face position and lever-pointing convention, not something the
existing ±5 mm Z-adjustment slots can absorb (that adjustment moves the
trigger point along the line, not the roller across it). This needs a
geometry change — most directly, either moving the arm's mount face closer
to the pulley/line in X while re-deriving `KW_BOSS_Y0`'s pulley-envelope
clearance at the new position, or re-deriving `KW_BOSS_Y0`/leading-edge
placement so `KW_BODY_Y_FRONT ≈ KW12_LEVER_LEN` (so the roller lands near
Y=0) — and should go back to the implementer as a bounded rev D task per
the two focused-repair-attempt rule in `CLAUDE.md`, or be escalated to the
lead if a second attempt does not resolve both axes simultaneously without
reopening the pulley/csk/motor-body clearances re-verified clean in
Section 4.
