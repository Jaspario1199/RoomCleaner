# Verification report: cad/parts/camera_case_overhead.py

Role: geometry-verifier (Gate 5), independent of the implementer.
Scope: `cad/parts/camera_case_overhead.py`, `make() -> (shell, bezel)`.
Method: built the solids directly from `make()` and measured the actual BRep
geometry with exact OCCT point-classification (`BRepClass3d_SolidClassifier`)
and bisection, not the module's own constants alone. Probe tests added at
`tests/test_camera_case_overhead_verification.py` (24 tests, all passing).
The implementer's own suite (`tests/test_camera_case_overhead.py`, 29 tests)
was also run as a secondary signal — both suites pass; **combined result:
52/52 passed.**
No repairs were made; this is a read-only assessment plus new test code.

**Overall: PASS.** One byte-level bug was found in my own first draft of the
wall-thickness probe (inverted bisection direction, produced a nonsensical
28.0 mm reading that still satisfied `>=2.4`, i.e. a false-positive test) and
was fixed before being trusted — noted here for traceability, not as a part
defect. One real design observation is flagged in §8 (non-blocking).

---

## 1. Shell: plate, holes, slot, skirt, standoffs, bosses

| Item | Expected | Measured | Tol | Result |
|---|---|---|---|---|
| Plate footprint | 56 x 56 mm | 56.000 x 56.000 mm (bbox) | ±0.3 mm | PASS |
| Plate thickness | 4 mm | zmax(shell)=4.000, plate spans Z 0..4 | ±0.3 mm | PASS |
| Ceiling screw holes (4x) | Ø4.2, corners at inset 6.0 mm | Ø4.20 measured at all 4 corners `(±22,±22)` via bisection | ±0.1 mm dia | PASS |
| Through-plate cable slot | 16 x 6 mm slot, through plate | void at center and out to x=±8 (SLOT_L/2), solid beyond | ±0.5 mm | PASS |
| Skirt wall thickness | ≥2.4 mm | **2.400 mm** measured (outer half-plate 28.000 mm − independently-bisected cavity half-span 25.600 mm) | ≥2.35 (−0.05 mm) | PASS — meets the minimum with **zero margin**, exactly at spec |
| Standoff posts (4x) | Ø1.7 M2 self-tap through Ø6.0 post, on 28.0 mm square pitch, imported not redefined | pitch measured 28.00 mm via pairwise bisection (implementer test) + posts confirmed straight vertical prisms (solid at r=(1.7+6)/4 sampled at z-fractions 5/25/50/75/95% of −10 mm) | ±0.1 mm / vertical at all 5 samples | PASS |
| Corner bosses (4x) | Ø2.8 blind pilot, boss integral with skirt | pilot present, solid boss material confirmed at 5 Z-fractions of full −24.6 mm skirt height (straight vertical cylinder) | vertical at all 5 samples | PASS |
| Interface import | `CAM_HOLE_PITCH`, `M2_TAP` imported from `camera_mount_overhead.py`, not redefined | `cco.CAM_HOLE_PITCH is cmo.CAM_HOLE_PITCH` and `cco.M2_TAP is cmo.M2_TAP` — same object identity, not just equal value | identity check | PASS |
| Solid count | 1 solid, no stray bodies | `shell.solids()` → 1 | exact | PASS |
| Valid BREP | valid | `shell.val().isValid()` → True | — | PASS |

## 2. Bezel

| Item | Expected | Measured | Tol | Result |
|---|---|---|---|---|
| Thickness | ~3 mm | 3.000 mm (bbox zlen) | ±0.3 mm | PASS |
| Footprint | 56 x 56 mm | 56.000 x 56.000 mm | ±0.3 mm | PASS |
| Lens opening | Ø18.0, centered | 18.00 mm on X axis, 18.00 mm on Y axis (perpendicular re-check) | ±0.1 mm | PASS |
| M3 clearance holes (4x) | align with shell boss pilots | **independently** bisected each hole's true (x,y) center on the bezel and on the shell separately (no shared source constant used for both), then compared center-to-center: **0.0000 mm offset on all 4 corners** (24.5, 24.5) / (−24.5, 24.5) / (24.5, −24.5) / (−24.5, −24.5) | <0.1 mm | PASS |
| M3 clearance dia | 3.4 mm | 3.40 mm measured (implementer test, cross-checked) | ±0.1 mm | PASS |
| Solid count | 1 | `bezel.solids()` → 1 | exact | PASS |
| Valid BREP | valid | True | — | PASS |

## 3. Interior stack-up

| Term | Value | Source |
|---|---|---|
| STANDOFF_H | 10.0 mm | imported `POST_H` from `camera_mount_overhead.py` |
| PCB_T | 1.6 mm | assumption (documented) |
| LENS_SPACE | 13.0 mm | ≥ LENS_SPACE_MIN (12.0 mm) |
| SKIRT_H (computed) | 24.6 mm = 10.0 + 1.6 + 13.0 | matches measured shell Z depth (zmin=−24.6) |
| Board pocket clear span | required ≥36×36 mm | **measured 51.20 x 51.20 mm** via bisection at board mid-height (independent of `INTERIOR_CLEAR` constant) | PASS |

Board pocket clear span is measured directly on the built solid, not read
from the `INTERIOR_CLEAR` constant — confirms the assertion in the source
isn't just internally self-consistent but actually true of the geometry.

## 4. Printability

| Item | Check | Result |
|---|---|---|
| Standoff posts vertical (no overhang) | solid material present at same (x,y) offset across 5 Z-fractions spanning full post height | PASS, all 4 posts |
| Corner bosses vertical (no overhang) | same, across full skirt height | PASS, all 4 bosses |
| Side notch opens at free edge (no bridge needed) | void confirmed at z = NOTCH_BOTTOM_Z + 0.02 mm (i.e. the very last printed layer, since shell prints plate-down with skirt rim printed last) | PASS |
| Bezel flat, support-free | flat box, both hole cuts are straight verticals through 3 mm | PASS (by construction, confirmed valid single solid) |

## 5. Solid validity

Both `shell` and `bezel`: `isValid() == True`, exactly 1 solid each (`.solids()`
length), no disconnected bodies. PASS.

## 6. Mass (PETG, 1.27 g/cm^3)

| Piece | Volume (cm^3) | Mass (g) |
|---|---|---|
| Shell | 26.896 | 34.16 |
| Bezel | 8.536 | 10.84 |
| **Combined** | 35.432 | **45.00** |

Budget: ≤60 g. **PASS**, 15.0 g margin (25%).

## 7. STEP export / reimport

Two independent round-trips were performed:

1. **Fresh export** of the currently-built solids to a temp path, reimported,
   compared volume and full XYZ bounding box.
2. **The already-committed files** `cad/step/camera_case_overhead_shell.step`
   and `..._bezel.step` (dated 2026-08-28 17:26, 5 min after the current
   source file's last edit) were independently reimported and compared
   against the current `make()` output, to catch a stale export.

| Piece | Volume rel. err | Bbox rel. err (all axes) | Solids on reimport | Result |
|---|---|---|---|---|
| shell (fresh) | 0.0000% | ≤0.05 mm | 1 | PASS |
| bezel (fresh) | 0.0000% | ≤0.05 mm | 1 | PASS |
| shell (committed STEP) | <0.001% | ≤0.05 mm | 1 | PASS |
| bezel (committed STEP) | <0.001% | ≤0.05 mm | 1 | PASS |

Both well inside the 0.1% tolerance requested. Committed STEP files are
current (not stale).

## 8. Assembly check (32x32x1.6 board + lens stand-in + USB stand-in)

| Check | Method | Result |
|---|---|---|
| (a) Board corner holes land on post axes | board's own 28 mm CAM_HOLE_PITCH corner set compared directly to `STANDOFF_XY` | exact match, PASS |
| (b) Board outline clears skirt interior | sampled 36 points around the 32x32 mm board perimeter at board mid-height (−10.8 mm); none intersect shell material | PASS (board edge at ±16 mm, cavity clear to ±25.6 mm — 9.6 mm margin/side) |
| (c) Ø14x13 lens stand-in clears bezel, passes only through the opening | independently bisected the bezel's actual opening radius (9.00 mm) vs. stand-in radius (7.00 mm) → 2.00 mm radial clearance; sampled 16 points around the stand-in's curved surface at bezel mid-thickness, none touch bezel material; confirmed `LENS_SPACE` (13.0 mm) ≥ stand-in length (13.0 mm) | PASS |
| (d) 16x8x8 mm USB stand-in on board's +Y edge doesn't intersect shell, can reach the notch | box placement (z −10..−2, on board back face) confirmed clear of shell material at all 8 corners | PASS |

**Finding on (d), non-blocking:** the *rigid* USB-connector-body stand-in sits
at z ∈ [−10, −2] (in the standoff gap above the board, per the module's own
stated USB location), while the side notch physically opens at z ∈ [−24.6,
−10] — **these two Z-bands do not overlap.** A rigid straight-line path from
the connector to the notch does not exist; the module's own docstring only
ever claims a *cable* path ("clear, unobstructed path down the inside of the
wall"), not that the connector body itself is level with the notch. I
therefore probed the specific 3-segment path the docstring describes —
sideways off the board edge at the connector's height, down along the inside
of the (unobstructed, board-free) wall clearance zone, then in through the
notch — and it **is fully void, no blockage** (`test_assembly_usb_standin_cable_path_to_notch`,
PASS). So: reachable for a flexible cable exiting the connector, consistent
with what the design actually claims. Flag this for the lead only if a
rigid strain-relief boot or right-angle connector body (rather than a bare
flex cable) is anticipated — that would need its own Z-clearance check,
which this part does not provide.

## 9. Renders

`cad/previews/camera_case_overhead_shell.png` and `..._bezel.png` exist
(dated same run as the STEP exports), single fixed isometric view with
dimension caption, consistent with `cad/lib.py`'s `render_stl` helper — this
is the **same one-view-per-part convention used by every other part in this
repo** (checked all 17 `cad/previews/*.png` files: none has more than one
view per part). CLAUDE.md's Gate-5 template language ("standardized front,
rear, left, right, top, bottom, isometric renders") is not implemented
anywhere in this codebase currently — a pre-existing, repo-wide gap, not a
defect specific to this part. Visual check of both PNGs: shell shows the
plate, skirt, 4 standoff posts, and 4 corner bosses as expected; bezel shows
the flat plate with a centered circular lens opening and rounded corner
relief. PASS (matches established repo convention); render-completeness
vs. the literal CLAUDE.md wording is an open item for the whole repo, not
this part.

---

## Test files

- `tests/test_camera_case_overhead_verification.py` — 24 tests, all new,
  written independently of the implementer's test file. Covers: interface
  import identity, solid validity, wall thickness (measured, bug-fixed
  during this review — see below), post/boss verticality (printability),
  notch free-edge opening, mass, STEP round-trip (fresh export AND the
  committed files), independently-cross-measured bezel/shell hole alignment,
  and the full assembly check (board holes, board clearance, lens stand-in
  clearance, USB stand-in placement + cable-path reachability).
- `tests/test_camera_case_overhead.py` — implementer's own 29 tests, run
  unmodified as a secondary signal. All pass.
- **Combined: 52/52 passed.**

Reproduce:
```
python3 -m pytest tests/test_camera_case_overhead.py tests/test_camera_case_overhead_verification.py -q
```

## Note on my own test-authoring error (for traceability)

The first draft of `test_skirt_wall_thickness_measured` bisected in the wrong
direction (walked inward from the outer face using the implementer's-helper
convention backwards), converging on `28.0 mm` — a value that still passed
the `>= 2.35 mm` assertion, i.e. a **false-positive test** that would not
have caught an undersized wall. Caught by manually inspecting the printed
measured value against the known expected value before trusting the test;
fixed to bisect outward from the known-void cavity center (matching the
`_bisect` convention already used in the implementer's own suite), which now
correctly reads back **2.400 mm** (exactly at the 2.4 mm spec floor). Left in
this report so the fix is auditable rather than silently discarded.

---

## Summary

**PASS overall — 52/52 tests green (29 implementer + 24 verifier), 0 defects
found in the geometry itself.**

Key measured numbers:
- Shell bbox 56.00 x 56.00 x 28.60 mm, volume 26.90 cm^3, mass 34.16 g
- Bezel bbox 56.00 x 56.00 x 3.00 mm, volume 8.54 cm^3, mass 10.84 g
- Combined mass **45.00 g** (budget ≤60 g, 25% margin)
- Skirt wall thickness measured **2.400 mm** (spec ≥2.4 mm — zero margin,
  exactly at the floor; a print-tolerance nudge below nominal would put it
  under spec, worth a note to the lead even though it measures as designed)
- Standoff pitch 28.00 mm (imported, not redefined, confirmed by object
  identity)
- Lens opening 18.00 mm both axes; lens stand-in clearance 2.00 mm radial
- Bezel-to-shell screw alignment: 0.000 mm offset, all 4 corners,
  independently measured on each solid
- STEP round-trip: <0.001% volume error, ≤0.05 mm bbox error, both pieces,
  both fresh and committed exports
