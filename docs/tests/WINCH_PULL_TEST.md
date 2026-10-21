# Winch pull test (one station, ~15 min)

**Why.** The lift capacity of the whole robot rests on one assumed number:
running torque = 0.7 × holding torque. The test measures how hard one winch
can pull, and with that the 3:1-reduction decision in
`docs/decisions/WINCH_CAPACITY_20261021.md` can be made on data.

## You need
- One assembled station board (Rev D), Vref at the board maximum (≈ 0.85 V), MS1–3 to GND (full step).
- A luggage scale (or kitchen scale with a hook), line tied to it, scale tied to a fixed point.
- `firmware/driver_bench_test` uploaded, Serial Monitor at 115200.
- The station clamped to the bench, or mounted: it will pull hard.

**Safety:**
- Nothing hangs; the line runs horizontally along the bench.
- Keep hands off the line between the spool and the scale.
- Wear safety glasses: braid under load snaps back if a knot lets go.

## A. Holding force (`h`)
1. Leave the line slack, then send `h`: the driver energises.
2. Pull the scale slowly by hand until the spool slips (a click, then it turns).
3. Record the peak reading.
4. Do it 3 times with the line on the bare core (empty spool), and 3 times with about 20 ft wound on (full spool).

## B. Running pull (`F`)
1. Set a speed: `2` = 200 steps/s. Line speed is about 47 mm/s on the core, about 63 mm/s full.
2. Send `F`: the motor tries 10 turns, reels the line in and loads the scale.
3. Record the highest reading **before** the motor starts skipping (it buzzes and the line stops coming in).
4. Repeat at `1` (100/s) and `3` (400/s), on the core and on a full spool.
5. Send `o` after each run to release.

## Record
| Spool | Rate (steps/s) | Holding peak (kg) | Running peak before skip (kg) |
|---|---|---|---|
| core | – | | |
| core | 100 / 200 / 400 | | |
| full | – | | |
| full | 100 / 200 / 400 | | |

N = kg × 9.81.

## Decide
- Running pull at full spool **≥ 25 N** → the direct drive might carry a lighter claw. Re-run the capacity table with the measured number.
- **< 25 N** (expected about 18 N) → go to the 3:1 winch reduction (memo option 1).
- Also note the driver heatsink temperature after the runs.
