# Proposal: lighter, smaller parts sized to their loads (10/22, lead)

Jasper (10/22): "suggest a redesign for lower weight and volume parts to get the job done"; building parts stronger than any
load needed was a mistake. **Status: proposal for the next phase, not approved.** The volumes are measured from Jasper's STEP
files; the targets are estimates to be checked part by part.

## Why there is room

The weakest-link ranking (`calculations/lift_chain_weakest_link.md`) gives the cable tension at which each part gives, against
the most the motor can pull (59 N). The motor is meant to give first, so a part needs about 1.5 times that, not 100 times:

| Part | Gives at | Times the motor | Reading |
|---|---|---|---|
| Slide-in dovetails and lips | 13 kN | 225 | far more material than the load needs |
| Wall plate under the screw heads | 5.5 kN | 93 | same |
| Motor screws into the motor | 3.1 kN | 53 | hardware, no change |
| Claw cable eye | 1.0 kN | 17 | same |
| Wall screws in one stud column | 531 N | 8.9 | keep the screws; the plate around them can shrink |
| Motor tab, 5 mm, sharp corner | 70 N | 1.2 | **the one part that needs more**: 6 mm with fillets (2.1 times) |

## Station (per station; not lifted, so this saves plastic, print time and wall load)

| Part | Solid volume now | Proposal | Target (estimate) |
|---|---|---|---|
| Wall mount | 597 cm³ (758 g solid PETG) | Keep the six counterbored screw bosses, the three dovetail grooves, the lips and the shelf; replace the solid 34 mm deep block with a 5 mm back plate, a 3 mm perimeter wall and ribs between the bosses | about 200 cm³ |
| Slide-in | 218 cm³ (276 g) | Deck from 8.5 mm to 5 mm with ribs under the motor; motor tab 5 to 6 mm with fillets on both roots | about 130 cm³ |
| Shell | 352 cm³ (448 g) | Not on the load path: 2 mm walls, vents and the fin slot kept | about 150 cm³ |
| **Total** | **1.17 L** | | **about 0.48 L (−60 %)** |

Four stations: about 2.8 L less PETG and several hours less printing per station (to be read from the slicer).

## Claw (lifted: every 0.1 kg is about 7 points of jeans margin)

Weighed 0.60 kg with the battery against a 0.45 kg budget. Of that: aluminium tube 198 g (CAD), servo 55 g, battery 99 g, so
the printed parts weigh about 250 g as built (677 cm³ of solid CAD volume).

| Item | Now | Proposal | Saving (estimate) |
|---|---|---|---|
| Aluminium tube, 266 mm | 198 g | Carbon-fibre tube of the same outside diameter, or a thinner aluminium wall | 100 to 140 g |
| Gear housing (two parts), electrical housing, cylinder | about 250 g printed | Thinner walls and lightening windows where the servo-stall loads allow (teeth checked at stall, SF 2.05) | 30 to 80 g |
| **Claw** | **0.60 kg** | | **0.45 kg budget: jeans margin from 0.06 kg (4 %) to about 0.21 kg (16 %)** |

## How each change is checked

1. Re-run `calculations/lift_chain_weakest_link.py` with the new section sizes: no part below 1.5 times the motor.
2. Run the SolidWorks static study on the new station at the 48 N slip force.
3. Weigh the printed part and record it in the Lift budget tab.
4. Continuous testing (next phase): long unattended runs that log tracking faults, motor and PETG temperatures, and creep at the
   motor tab and the wall screws.
