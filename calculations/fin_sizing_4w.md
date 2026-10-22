# Fin sizing: what would carry all 4.05 W (1.5 A, D37)?

Asked by Jasper (10/22): "calculate how thick/long the fin would need to be to dissipate all 4.05 W".
Script: `calculations/fin_sizing_4w.py`; full output in the section "Raw output" below. CALCULATED, not measured.

## Case and method

- **Case:** the fin **alone** carries all 4.05 W. The motor's own path to the shell air is ignored, which is conservative and
  close to a sealed shell.
- **Pass:** the motor flange at or below **60 °C**, the limit for loaded PETG, in a 23 °C room. A second pass level keeps a
  5 K margin (55 °C).
- **Geometry:** 6061 aluminium, 44 mm wide (the motor's width), the real hole pattern, paste contact (0.074 K/W).
- **Model:** the quasi-1D fin of `simulation_loads.py`, with natural convection and radiation converged for each geometry.
- **Ranges:** isothermal flange (lower) to uniform flux into the patch (upper).
- **Infinite-fin limit:** q∞ = w √(2 h k t) θ_b, the most heat any length of that sheet can carry.

## Results (painted fin, ε 0.9)

| Thickness | Mass (250 mm) | Motor at 200 mm exposed, all 4.05 W through the fin | Shortest exposed length for ≤ 60 °C | for ≤ 55 °C | Infinite fin at 60 °C |
|---|---|---|---|---|---|
| **0.019 in (built)** | 14 g | 100 to 120 °C | **never** | never | **2.0 W** |
| 0.032 in | 24 g | 82 to 94 °C | never | never | 2.6 W |
| 0.050 in | 38 g | 71 to 78 °C | never | never | 3.2 W |
| 1/16 in | 47 g | 66 to 72 °C | never | never | 3.6 W |
| 0.090 in | 68 g | 60 to 65 °C | 210 mm to never | never | 4.3 W |
| **1/8 in (first drawing)** | 94 g | **56 to 59 °C** | **145 to 185 mm** | 245 mm to never | 5.1 W |
| 3/16 in | 141 g | 53 to 55 °C | 125 to 140 mm | 165 to 195 mm | 6.3 W |
| 1/4 in | 189 g | 51 to 52 °C | 115 to 125 mm | 150 to 165 mm | 7.2 W |

**Bare aluminium (ε 0.1)** needs **1/4 in × 285 to 330 mm** for 60 °C, and nothing up to 600 mm reaches 55 °C.

## What it means

1. **The built 0.019 in sheet cannot carry 4.05 W alone at any length.**
   - Even infinitely long, it carries only about 2.0 W at a 60 °C base.
   - It works today (56 to 59 °C, vented) only because the motor sheds about 2.5 W straight into the vented shell air.
2. **Thickness is the lever, not length.**
   - A thin sheet has a large m = √(2h / (k t)), so its far end does almost nothing.
   - Past about 140 mm the 0.019 in sheet adds under 5 %, while k·t sets the most heat any length can carry.
3. **The 1/8 in plate of the first drawing, painted, at the current 200 mm** carries all 4.05 W at 56 to 59 °C on its own.
   With the vented shell as well, the motor would run at about **45 °C** (44.7 to 45.8; sealed 48.0 to 49.5), against 56 to
   59 °C with the built sheet.
4. **For a 5 K margin with the fin alone:** 3/16 in × 165 to 195 mm, or 1/4 in × 150 to 165 mm.
5. **Paint matters.** Bare aluminium needs a 1/4 in plate about 300 mm long.
6. **Mass is not the constraint.** The fin is on the wall station, not the claw, so its 94 to 141 g does not load the winches.
7. **Length is limited by the ceiling.**
   - The fin top already sits 229 mm above the shaft axis, so a longer fin may not fit under the ceiling.
   - Thickness avoids that problem.
8. **Manufacturing note:** 1/8 in and thicker plate may be beyond a hand shear's rated capacity. Check the shear; otherwise
   cut on a bandsaw and square the edges on the mill. The one-setup hole drilling stays the same.

## Raw output

```
All 4.05 W through one 44 mm wide 6061 fin, room 23.0 C, paste contact 0.074 K/W, shell air +1.5 K

Motor flange temperature for the built length (200 mm exposed), isothermal flange -> uniform flux:
  0.019 in (built)         t  0.48 mm,    14 g: bare Al: 120.1-140.2 C (h  6.2) | black paint:  99.7-119.8 C (h 10.6)
  0.032 in                 t  0.81 mm,    24 g: bare Al:  99.3-111.3 C (h  6.2) | black paint:  81.7- 93.7 C (h 10.6)
  0.040 in                 t  1.02 mm,    30 g: bare Al:  92.5-102.0 C (h  6.2) | black paint:  75.7- 85.3 C (h 10.6)
  0.050 in                 t  1.27 mm,    38 g: bare Al:  86.7- 94.3 C (h  6.2) | black paint:  70.5- 78.1 C (h 10.6)
  1/16 in                  t  1.59 mm,    47 g: bare Al:  81.8- 87.9 C (h  6.2) | black paint:  66.1- 72.2 C (h 10.6)
  0.080 in                 t  2.03 mm,    60 g: bare Al:  77.3- 82.1 C (h  6.2) | black paint:  61.9- 66.7 C (h 10.6)
  0.090 in                 t  2.29 mm,    68 g: bare Al:  75.5- 79.8 C (h  6.2) | black paint:  60.2- 64.5 C (h 10.6)
  1/8 in (first drawing)   t  3.17 mm,    94 g: bare Al:  71.3- 74.4 C (h  6.2) | black paint:  56.2- 59.3 C (h 10.6)
  3/16 in                  t  4.76 mm,   141 g: bare Al:  67.6- 69.6 C (h  6.2) | black paint:  52.6- 54.7 C (h 10.6)
  1/4 in                   t  6.35 mm,   189 g: bare Al:  65.6- 67.2 C (h  6.2) | black paint:  50.7- 52.3 C (h 10.6)

Shortest exposed length (mm) so the motor stays at or below 60 C limit; '-' = not even at 600 mm. Ranges: isothermal flange / uniform flux. Infinite-fin limit = most heat any length can carry.
  0.019 in (built)         bare Al: -/- mm (infinite fin 1.35 W) | black paint: -/- mm (infinite fin 1.99 W)
  0.032 in                 bare Al: -/- mm (infinite fin 1.75 W) | black paint: -/- mm (infinite fin 2.58 W)
  0.040 in                 bare Al: -/- mm (infinite fin 1.96 W) | black paint: -/- mm (infinite fin 2.89 W)
  0.050 in                 bare Al: -/- mm (infinite fin 2.19 W) | black paint: -/- mm (infinite fin 3.23 W)
  1/16 in                  bare Al: -/- mm (infinite fin 2.45 W) | black paint: -/- mm (infinite fin 3.61 W)
  0.080 in                 bare Al: -/- mm (infinite fin 2.77 W) | black paint: -/- mm (infinite fin 4.09 W)
  0.090 in                 bare Al: -/- mm (infinite fin 2.94 W) | black paint: 210/- mm (infinite fin 4.33 W)
  1/8 in (first drawing)   bare Al: -/- mm (infinite fin 3.46 W) | black paint: 145/185 mm (infinite fin 5.11 W)
  3/16 in                  bare Al: 395/- mm (infinite fin 4.24 W) | black paint: 125/140 mm (infinite fin 6.26 W)
  1/4 in                   bare Al: 285/330 mm (infinite fin 4.90 W) | black paint: 115/125 mm (infinite fin 7.22 W)

Shortest exposed length (mm) so the motor stays at or below 55 C (5 K margin); '-' = not even at 600 mm. Ranges: isothermal flange / uniform flux. Infinite-fin limit = most heat any length can carry.
  0.019 in (built)         bare Al: -/- mm (infinite fin 1.15 W) | black paint: -/- mm (infinite fin 1.70 W)
  0.032 in                 bare Al: -/- mm (infinite fin 1.49 W) | black paint: -/- mm (infinite fin 2.21 W)
  0.040 in                 bare Al: -/- mm (infinite fin 1.66 W) | black paint: -/- mm (infinite fin 2.47 W)
  0.050 in                 bare Al: -/- mm (infinite fin 1.86 W) | black paint: -/- mm (infinite fin 2.76 W)
  1/16 in                  bare Al: -/- mm (infinite fin 2.08 W) | black paint: -/- mm (infinite fin 3.09 W)
  0.080 in                 bare Al: -/- mm (infinite fin 2.35 W) | black paint: -/- mm (infinite fin 3.50 W)
  0.090 in                 bare Al: -/- mm (infinite fin 2.49 W) | black paint: -/- mm (infinite fin 3.71 W)
  1/8 in (first drawing)   bare Al: -/- mm (infinite fin 2.94 W) | black paint: 245/- mm (infinite fin 4.37 W)
  3/16 in                  bare Al: -/- mm (infinite fin 3.60 W) | black paint: 165/195 mm (infinite fin 5.35 W)
  1/4 in                   bare Al: -/- mm (infinite fin 4.16 W) | black paint: 150/165 mm (infinite fin 6.18 W)
```
