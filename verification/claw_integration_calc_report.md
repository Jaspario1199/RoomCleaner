# Independent Calculation Check — calculations/claw_integration.md (C1–C6)

Reviewer: calculation-checker (Sonnet). Read-only review; no geometry/parameter
files modified. Authoritative sources checked: cad/params.py, cad/interfaces.py,
cad/parts/tentacle_finger.py, cad/materials.py, REQUIREMENTS.md.

## C1. Tendon travel
- Inputs used: FINGER_RIBS = 6 (cad/params.py, confirmed), NOTCH_GAP = 4.5 mm
  (cad/parts/tentacle_finger.py L33; loop confirms exactly 6 notches cut).
- My result: 6 × 4.5 = **27 mm**.
- **Agree.**
- Flag: NOTCH_GAP is defined only in cad/parts/tentacle_finger.py, not in
  cad/params.py or cad/interfaces.py. Per CLAUDE.md ("important master values
  must have one authoritative definition") this is a single-source-of-truth
  violation — C1/C2/DRUM_CORE_R depend on it but it lives in a part file, not
  the parameter/interface contract. Recommend promoting NOTCH_GAP to
  params.py or interfaces.py and importing it into tentacle_finger.py.

## C2. Drum radius vs servo throw
- Inputs used: travel 27 mm (C1), throw 120° = GRIP 140° − RELEASE 20°,
  DRUM_CORE_R = 13.5 mm, DRUM_FLANGE_R = 16.5 mm (both cad/interfaces.py,
  confirmed).
- My result: θ = 120·π/180 = 2.09440 rad. r_min = 27/2.09440 = **12.894 mm**
  (doc: 12.9 ✓). s(13.5) = 13.5×2.09440 = **28.274 mm** (doc: 28.3, rounding
  only). Margin = (28.274−27)/27 = **4.72 %** (doc: 4.7 % ✓). Flange lip =
  16.5−13.5 = 3 mm ✓.
- **Agree** on the arithmetic and on the interfaces.py values.
- Unresolved: GRIP_ANGLE (140°), RELEASE_ANGLE (20°), and SERVO_THROW_DEG do
  not appear in cad/params.py or cad/interfaces.py (the two files this repo
  treats as authoritative for such contracts). I could not trace these to a
  master definition within the files I'm permitted to read. Either they live
  in an un-reviewed part/firmware file (another SSOT gap) or they are
  undocumented — recommend confirming source before relying on 120°.

## C3. Servo torque margin
- Inputs used: 5 N/tendon × 5 fingers = 25 N (matches R18's "≤25 N at the
  drum"), DRUM_CORE_R = 13.5 mm = 0.0135 m (cad/interfaces.py).
- My result: T = 25 × 0.0135 = 0.3375 N·m = 0.3375 × 10.1972 = **3.44 kg·cm**
  (doc: 3.4 ✓). Margin vs 9 kg·cm = 9/3.44 = **2.6×** (doc: 2.6× ✓).
- **Agree** with the stated numbers.
- Red flag (cross-document, not a math error): REQUIREMENTS.md R18 states
  "required torque ≤ 3.2 kg·cm." That figure only reproduces if you use
  r_min = 12.9 mm (25 N × 0.0129 m = 3.29 kg·cm), not the as-built
  DRUM_CORE_R = 13.5 mm actually in interfaces.py. R18 appears to predate the
  C2 decision to round the drum radius up to 13.5 mm and was never updated.
  The servo still clears with large margin (2.6×), so this doesn't threaten
  R18's intent, but R18's literal number is stale and should be corrected to
  ≥3.4 kg·cm or the drum radius revisited.

## C4. Mass rollup
- Inputs used: itemized printed masses (plate 60, hub 40, fingers 5×8=40,
  standoffs 4×4=16, drum 10, cover 55) and purchased masses (servo 55, LiPo
  90, ESP32 10, buck 5, wiring 25 — these match materials.py
  PURCHASED_MASS_G exactly).
- My result, printed subtotal: 60+40+40+16+10+55 = **221 g**, not the
  document's stated "~240 g."
- Purchased subtotal: 55+90+10+5+25 = **185 g** ✓ (matches doc and
  materials.py).
- Total using the document's own itemized numbers: 221+185 = **406 g**, not
  the stated "425 g."
- **Disagree** on the printed subtotal and total — arithmetic error of
  ~19 g (~8%) in the printed rollup. Direction is favorable (actual margin
  against 450 g is larger than claimed — ~44 g / 9.8% rather than the stated
  5.6%), so the ✓ pass conclusion is not threatened, but the reported number
  and margin percentage are wrong and should be corrected before Gate 5
  sign-off. All of this is explicitly flagged in the doc itself as
  provisional pending measured volumes, which is good practice, but the
  interim number should still be arithmetically correct.

## C5. Geometric clearances
Checked against HUB_MOUNT_R=27, STANDOFF_OD=10, STANDOFF_ANGLES_DEG=(36,108,
252,324), DRUM_FLANGE_R=16.5, DRUM_CORE_H=8, DRUM_FLANGE_T=2.2,
EFFECTOR_THK=5.0, EFFECTOR_REACH_M=0.130, FINGER_LEN=70, STANDOFF_LEN=40
(all cad/interfaces.py / cad/params.py, confirmed).
- Pocket half-width: atan(8.2/25.8)=17.7°, or 8.2/25.8 rad(small-angle)=18.2°
  — both round to **≈18°** ✓.
- Gap centers at 36/108/180/252/324°: arithmetic (0,72,144,216,288 pockets,
  midpoints) confirmed exactly ✓. Matches STANDOFF_ANGLES_DEG (4 of the 5
  gaps are used; 180° is intentionally unused — plausible, not verifiable
  from files read).
- Standoff angular half-width: asin(5/27)=10.68°, small-angle 5/27 rad=10.6°
  → **≈10.6°** ✓.
- 36−18−10.6 = **7.4°** ✓ arithmetic. Converting to linear material width:
  I get 27×7.4°(rad) = 3.49 mm at r=27, but 25.8×7.4°(rad) = 3.33 mm at
  r=25.8 (pocket radius) — the doc's "3.3 mm" only reproduces using r=25.8,
  not the r=27 standoff radius used two lines earlier. Not a hard error (the
  material in question is at the pocket edge, r≈25.8, so 25.8 is arguably
  the more correct radius) but the doc doesn't state which radius it used —
  flag as an approved-assumption gap, not a disagreement.
- Flange-to-standoff radial clearance: 22−16.5 = **5.5 mm** ✓.
- EFFECTOR_REACH: 8+40+12+70 = **130 mm** ✓, and I can independently
  reconstruct "8" as boss-top-to-plate-underside = 3 mm (cable plane per
  interfaces.py header, Z=+3) + EFFECTOR_THK 5 mm = 8 mm — consistent with
  the stated Z convention. **Agree**, matches EFFECTOR_REACH_M=0.130 exactly.
- **Agree overall.** Unresolved: "frame bore R15" (used in the drum/bore
  overlap check) does not appear in any file I was permitted to read —
  cannot verify against an authoritative source.

## C6. Structure sanity
- Shear check: assumes boss Ø12 mm (not found in any file I read — cannot
  verify) with 3.2 mm hole (CABLE_HOLE_D, confirmed), 5 mm thick
  (EFFECTOR_THK, confirmed). Net area π/4×(12²−3.2²) = **105.0 mm²** (doc:
  ">100 mm²" ✓). Stress = 40/105 = **0.381 MPa** vs yield 45 MPa (PETG,
  materials.py, confirmed) → margin = 45/0.381 = **118×**, comfortably "≫10"
  as stated, and far above R17's required ≥3× ✓.
- Standoff buckling: not numerically shown in the source doc. I computed it
  independently: solid Ø10 mm PETG column (I=πd⁴/64=490.9 mm⁴), E=2.1 GPa
  (materials.py), L=40 mm, K=1 → Pcr=π²EI/L² ≈ **6.4 kN** per column vs
  actual load 25/4=6.25 N per column → margin ≈ 1000×. **Agree** with the
  doc's qualitative "≫ kN range" conclusion, well above R17.
- **Agree**, with the Ø12 boss dimension flagged as unverifiable from the
  files in scope.

## Supplied facts
FINGER_RIBS=6, DRUM_CORE_R=13.5, DRUM_FLANGE_R=16.5, DRUM_CORE_H=8,
DRUM_FLANGE_T=2.2, HUB_MOUNT_R=27, STANDOFF_OD=10, STANDOFF_LEN=40,
STANDOFF_ANGLES_DEG, EFFECTOR_THK=5.0, EFFECTOR_REACH_M=0.130,
CABLE_HOLE_D=3.2, FINGER_LEN=70 (cad/interfaces.py, cad/params.py); PETG
density 1.27 g/cm³, yield 45 MPa, E=2.1 GPa (cad/materials.py); purchased
masses 55/90/10/5/25 g (cad/materials.py); R17 (40 N/cable, ≥3× margin), R18
(≤25 N total, "≤3.2 kg·cm" stated) (REQUIREMENTS.md); NOTCH_GAP=4.5
(cad/parts/tentacle_finger.py only).

## Approved assumptions (as stated in source doc, not independently checkable)
5 N max tension per tendon at full curl; MG996R ≥9 kg·cm @6 V; full notch
closure ≈ required tendon travel; horn height ~6 mm in the sub-plate stack.

## Derived results (my independent recomputation)
C1: 27 mm ✓. C2: r_min=12.89 mm, s(13.5)=28.27 mm, margin 4.72% ✓. C3: 3.44
kg·cm, margin 2.6× ✓. C4: printed 221 g (not 240), total 406 g (not 425) —
still ≤450 g but doc's numbers are arithmetically wrong. C5: all geometry ✓,
EFFECTOR_REACH=130 mm confirmed exactly. C6: shear margin 118×, buckling
margin ~1000× (buckling independently derived, not shown in source doc).

## Unresolved uncertainty
1. NOTCH_GAP (SSOT violation — lives only in tentacle_finger.py).
2. GRIP_ANGLE/RELEASE_ANGLE/SERVO_THROW_DEG — not found in params.py or
   interfaces.py; source untraceable within files reviewed.
3. R18's "≤3.2 kg·cm" is stale versus the as-built 3.4 kg·cm from
   DRUM_CORE_R=13.5 mm — needs a REQUIREMENTS.md correction or drum-radius
   revisit (owner decision, not mine to make).
4. C4 printed-mass subtotal arithmetic error (221 g vs stated 240 g) —
   recommend correcting the doc; conclusion (≤450 g) unaffected but margin
   percentage is wrong.
5. "Frame bore R15" (C5) and boss "Ø12" (C6) are not defined in any file I
   was permitted to read — cannot verify against an authoritative source.
