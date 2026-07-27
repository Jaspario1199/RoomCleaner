# Calculations — Claw integration pass

Method note: hand calculations, SI units unless stated. Authoritative inputs come
from `cad/params.py` (geometry) and `REQUIREMENTS.md` (loads). Each result names
the parameter or test that consumes it.

## C1. Tendon travel required (drives DRUM_CORE_R)
- Inputs: FINGER_RIBS = 6 notches/finger, NOTCH_GAP = 4.5 mm ventral opening.
- Assumption (approved): full curl closes each notch's ventral gap fully; the
  dorsal skin is inextensible, so tendon shortening ≈ Σ gap closures.
- Travel = 6 × 4.5 mm = **27 mm** (was estimated 25; use 27 as the requirement).
- Consumer: C2 drum sizing; assembly test "drum winds ≥ 27 mm within throw".

## C2. Drum radius vs servo throw (drives DRUM_CORE_R, SERVO_THROW_DEG)
- Servo usable throw: SERVO_THROW_DEG = 120° = 2.094 rad (SERVO_GRIP_DEG 140° − SERVO_RELEASE_DEG 20°, cad/interfaces.py; firmware hw_config must match — it previously said GRIP=120°, a 100° throw that would UNDERSIZE the drum; corrected via interface contract).
- Arc length at core radius r: s = r·θ → need r ≥ 27 / 2.094 = **12.9 mm**.
- Chosen DRUM_CORE_R = 13.5 mm → s = 28.3 mm ≥ 27 mm ✓ (margin 4.7%).
- Flange radius 16.5 mm (3 mm lip) retains slack tendons.
- Consumer: cad/params.py DRUM_CORE_R/DRUM_FLANGE_R; clearance check C5.

## C3. Servo torque margin (R18)
- Assumption: 5 N max tension per tendon at full curl (grip on stiff denim) → 25 N total.
- Torque = 25 N × 0.0135 m = 0.3375 N·m = **3.44 kg·cm** vs MG996R ≥ 9 kg·cm @6 V.
- Margin ≈ 2.6× ✓. Consumer: none (validates D2/D4 sizing); revisit if fingertip
  force measurements exceed 5 N.

## C4. Mass rollup vs 450 g budget (R7)
Printed (PETG 1.27 g/cm³, TPU 1.21): plate ~60, hub ~40 (through-slots reduce),
fingers 5×8, standoffs 4×4, drum ~10, cover ~55 → **~221 g** (checker-corrected).
Purchased: servo 55, LiPo 90, ESP32 10, buck 5, wiring/screws/switch ~25 → **185 g**.
Total ≈ **406 g ≤ 450 g** ✓ (9.8% margin — verify from measured volumes at Gate 5).
Consumer: verification mass check; roomcleaner/config EFFECTOR_ASSEMBLY stays 0.45.

## C5. Geometric clearances (drive interface angles)
- Finger pockets: 5 at 72° pitch, tangential half-width ≈ 8.2 mm at r≈25.8 →
  angular half-width ≈ 18°. Largest inter-pocket gap centers: 36°, 108°, 180°, 252°, 324°.
- Standoff Ø10 at r=27 → angular half-width ≈ 10.6°. Placed at gap centers:
  clearance to pocket edge = 36−18−10.6 ≈ **7.4°** ≈ 3.3 mm of material ✓.
- Drum flange R16.5 vs standoff inner face at 27−5 = 22 mm → **5.5 mm** radial ✓.
- Drum flange R16.5 vs frame bore R15: drum sits below the plate; no overlap plane. ✓
- Servo body below-plate depth 0 (inverted). Sub-plate volume: standoff 40 mm ≥
  drum height (core 8 + 2 flanges ≈ 12.4) + horn ~6 + tendon rise ✓.
- EFFECTOR_REACH: boss top→plate 8 + standoffs 40 + hub 12 + finger 70 ≈ **130 mm**
  → EFFECTOR_REACH_M = 0.13. Consumer: roomcleaner/config.py, planner grab pose.

## C6. Structure sanity (R17)
- Worst single-cable load 40 N enters a corner boss: shear area ≈ boss Ø12×5 mm
  PETG ann. ≈ >100 mm² → stress ≪ 1 MPa vs ~45 MPa yield → margin ≫ 10 ✓.
- Standoffs: worst compression = grip reaction ~25 N over 4 columns Ø10 → trivial;
  Euler buckling of 40 mm PETG column Ø10 ≫ kN range ✓. No further analysis needed.

- Note (calc-check): "frame bore R15" and boss "Ø12" are part-local constants in effector_frame.py, not contracts; acceptable (not mating values), recorded here for traceability.

## Limitations
- C1 assumes full notch closure = required travel; real TPU curl may need less
  (fingers meet the item earlier). Excess throw is absorbed by drum slip-free
  stall at current limit — acceptable; physical test will trim GRIP_ANGLE.
- C3's 5 N/tendon is an engineering estimate, not measured; flagged for bench test.
