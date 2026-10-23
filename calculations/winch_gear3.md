# Winch station with the 3:1 spur reduction (D40)

Source: `calculations/winch_gear3.py` (run `PYTHONPATH=. /usr/bin/python3 -m calculations.winch_gear3`), output
`calculations/winch_gear3.json`. Geometry: `cad/WINCH_GEAR3_SPEC.md`, `cad/params.py` WG3_*. Motor model, spool radii, running
fraction (0.7), skip margin (1.5) and the tension-per-weight factor (1.101) are the repo's (`calculations/simulation_loads.py`,
D37, Lift budget tab). Pass rule from D39: every link at least 1.5 times the most the motor can pull before it slips.

## Inputs

| Input | Value | Tag |
|---|---|---|
| Ratio | 60 / 20 = 3.00, module 1.0, 20° | REPO WG3 |
| Stage efficiency | 0.90 each direction | ASSUMED (the pull test measures the net) |
| Motor holding torque | 0.36 N·m at 1.5 A, scaled with current; upper bound x 40/36 | REPO |
| Spool radius | 7.5 mm core, 10 mm full | REPO |
| PETG tooth allowable | 22.5 MPa x 0.85 warm = 19.1 MPa | REPO (review R5, D39) |
| Lewis form factor | 0.320 (20T), 0.422 (60T) | SRC standard table |
| 687 bearing static rating C0 | 600 N | ASSUMED, check the datasheet |
| Shaft yield | 350 MPa (plain Ø7 dowel; hardened are higher) | ASSUMED |
| Motor radial limit | about 28 N at 20 mm from the face | SRC typical 17HS datasheet; check Jasper's motor |

## Results

| | Direct drive today, 1.5 A | **Geared, 1.0 A (recommended)** | Geared, 1.5 A |
|---|---|---|---|
| A4988 Vref (R100) | 1.20 V | **0.80 V** | 1.20 V |
| Lift capacity (design, worst cable) | 1.56 kg (+4 %) | **2.80 kg (+87 %)** | 4.20 kg (+180 %) |
| Most the motor pulls before it slips | 59 N | **68 to 132 N** | 102 to 198 N |
| Every part must hold (1.5 x) | 89 N | **198 N** | 297 N |
| Motor heat | 4.05 W | **1.80 W** | 4.05 W |

Margins on 1.50 kg (claw 0.60 + jeans 0.90).

| Link, at 1.0 A | Load at the slip torque | Ratio | Verdict |
|---|---|---|---|
| Printed 60T teeth (Lewis, warm) | F_t 26.7 N, 6.3 MPa vs 19.1 | 3.03 | PASS |
| Pinion set screw, steel on steel D-flat | 0.67 to 0.89 N·m vs 0.27 | 2.50 | PASS |
| Spool shaft Ø7, bending (cable + mesh) | 1461 N·mm, 43 MPa | 8.06 | PASS |
| 687 bearings, static | 64 N near, 83 N far | 7.26 | PASS |
| Line knot | | 2.02 | PASS |
| Wall screws, one stud column | | 4.03 | PASS |

At 1.5 A the teeth fall to SF 2.02 and the set screw to 1.66; both still pass, but 1.0 A gives almost twice the needed capacity
at less than half the heat, so 1.0 A is the recommendation.

## Design inputs for Jasper (he designs the mount, cheeks and shell)

- **The cable no longer loads the motor tab through the motor.** It loads the two bearing seats. At 1.0 A the near seat (in the
  extended motor tab) must hold **96 N** and the far cheek **124 N** (1.5 x 64 and 83 N), radial, through a 14 mm bore.
- **Every part of the station must now hold 198 N** of cable tension, not 89 N. The as-drawn 5 mm tab with a sharp corner gave
  at 70 N warm (`lift_chain_weakest_link.md`); it no longer carries the cable, but whatever he extends down to the spool axis
  must meet the 96 N seat load with fillets on its roots.
- **Motor shaft:** in normal running the pinion puts 6.4 N on the motor shaft 19 mm from the face; at the slip torque 28.4 N,
  about the catalogue life limit. That limit is a bearing-life rating, so short peaks at a slip do no harm. At 1.5 A the slip
  peak is 42.6 N: another reason to run 1.0 A.

## Encoder and software

| Item | Value | Why |
|---|---|---|
| One skip (4 full steps) at the spool | 2.4° = **27 counts** | was 82 counts direct |
| Gear backlash at the spool | 5.3 counts | 0.246 mm at the pitch circle (build notes) |
| `tracking_tol_counts` | **20** (sim config has 60) | above backlash plus noise, below one skip |
| `full_steps_per_rev` (motor steps per spool turn) | **600** | 200 x 3; the software uses it per spool revolution, so only the config changes |
| 50 mm/s at the core | 637 full steps/s, motor 191 rpm; `max_step_rate_hz` about 800 | |
| Cable per full step at the core | 0.079 mm | was 0.236 mm |
| `drive.step_sign` | **flip** (or swap one motor coil pair) | the spur pair turns the spool opposite to the motor |
| `encoder.sign` | **measure again** on the bench | the magnet moves to the far end of the spool shaft |

Change the configs only when the gearbox is installed; until then the direct-drive values stay.

## Limits

- Efficiency 0.90 is assumed; the pull test on the built station replaces it.
- The shaft check takes the full cable force straight down and the mesh force at the gear mid-face; the real cable angle lowers it.
- Lewis bending only: printed tooth wear and creep under a long hold are not covered; continuous testing (next phase) logs them.
- The bearing seat loads assume a rigid shaft on two simple supports.
