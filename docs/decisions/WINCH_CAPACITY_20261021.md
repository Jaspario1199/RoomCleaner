# Winch lift capacity at 1.06 A — decision memo (2026-10-21)

**Status: needs Jasper's decision.** Supersedes the capacity statements made
with D29/D30 ("~43 N", "~34 N per cable", "claw budget ~650–750 g"). Those
used the stepper's *holding* (snag) force; the planning number is the
*running* pull. Source: `calculations/presentation_fundamentals.py` topic 2 and
the capacity LP from `calculations/gen2_payload_limit.py` (same model as
review R10), recomputed by the lead.

## The numbers (all CALCULATED; inputs: Vref 0.85 V MEASURED)

- Current cap: I = Vref / (8 Rs) = 0.85 / 0.8 = **1.06 A** (measured board limit).
- Holding torque scales to 0.255 N·m. Running torque, using the repo convention of 0.7 × holding, is 0.179 N·m.
- Line pull = τ / r:

| Spool radius | Running pull | Design force (÷ 1.5 margin) |
|---|---|---|
| Core 7.5 mm (empty spool) | 23.8 N | 15.9 N |
| 10 mm (full spool) | 17.9 N | **11.9 N** |

- The worst place in the room is not near the ceiling. It is near the **walls/corners**, where two cables run almost flat. There, max cable tension ≈ 1.06–1.10 × total weight, including 2 m/s² acceleration.

**Heaviest claw + payload the four winches can carry anywhere in the working area:**

| Configuration | Wall margin 0.2 m | 0.4 m | 0.6 m | 0.8 m |
|---|---|---|---|---|
| Ø15 core, direct drive (today) | 1.10–1.14 kg | 1.18–1.29 | 1.26–1.48 | 1.34–1.75 |
| Ø10 core, direct | 1.38–1.43 | 1.47–1.62 | 1.57–1.85 | 1.68–2.19 |
| Ø15 core + **3:1 gear reduction** (η 0.9) | 2.98–3.09 | 3.18–3.49 | 3.39–3.99 | 3.62–4.72 |

The range in each cell spans task-height limits from 1.0 m to 1.6 m.

**Need:** the claw (printed estimate 1.05–1.25 kg, unweighed) plus 0.9 kg of jeans is about **2.0–2.2 kg**. The 1 lb test weight gives about 1.5–1.7 kg.

## What this means
- **Today's direct drive can't lift the current claw plus jeans.** That holds anywhere near the walls, and even with a lighter claw the margin is thin.
- **A smaller spool core helps about 25 %.** That's not enough on its own.
- **Lowering the ceiling hardly helps.** The binding case is near the walls.
- **A larger wall margin helps,** but it shrinks the pick-up area.
- **A 3:1 reduction at each winch is the only single change that clears it with margin.**

## Options (Jasper decides)
1. **3:1 printed gear reduction at each winch (recommended).**
   - Gain: about 2.7× pull; any claw up to about 1.5 kg plus jeans.
   - Speed: line speed drops 3× for the same motor speed, but full-step mode has headroom. 50 mm/s needs about 190 rpm at the motor.
   - Cost: station redesign (a second shaft, two printed gears, two 687 bearings, which you already use) and a bigger housing.
   - Same tooth-strength method as the claw gears.
2. **Ø10 core plus a much lighter claw (under about 0.5 kg) plus a 0.6 m wall margin.** No new parts, but it needs the claw weight cut in half, and the pick-up area shrinks.
3. **Reduce the payload goal** to shirts/towels (about 0.3–0.5 kg) for the panel demo, and keep option 1 as the next revision.
4. **Measure before deciding.** Run a luggage-scale pull test on one station at 1.06 A: slowly reel in against a scale until the motor skips, at an empty and a full spool. This replaces the 0.7 running-torque assumption with a real number (it could be higher). It's about 15 minutes of work and it is the first thing to do.

## Recommendation
Do the pull test first (option 4). If running pull at a full spool is under about 25 N, which is likely, adopt option 1 for gen 3 and use option 3 for the Oct 27 demo. Record the choice as D31.

**Update (review of the simulation manuals):** in full-step mode the A4988
drives both coils at about 0.71 × I_trip. If the motor's holding torque is
specified for both phases at rated current, then torque scales with 0.71 ×
1.06 A rather than 1.06 A. That would cut every pull number above by up to
about 30 % (running pull at the core about 17 N), which makes the pull test
and the reduction more important, not less.
