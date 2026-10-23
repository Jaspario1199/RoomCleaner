# Winch station with the 3:1 spur reduction (D40)

Revision B (D41): 18T/54T; the revision A (20T/60T) results are in git history.

Source: `calculations/winch_gear3.py` (run `PYTHONPATH=. /usr/bin/python3 -m calculations.winch_gear3`), output
`calculations/winch_gear3.json`. Geometry: `cad/WINCH_GEAR3_SPEC.md`, `cad/params.py` WG3_*. Motor model, spool radii, running
fraction (0.7), skip margin (1.5) and the tension-per-weight factor (1.101) are the repo's (`calculations/simulation_loads.py`,
D37, Lift budget tab; the factor and the 1.50 kg are exported by `lift_chain_weakest_link.py`, WL). Pass rule from D39: every
link at least 1.5 times the most the motor can pull before it slips. Revised 10/23 after the independent check
(`verification/winch_gear3_calc_check.md`, F1 to F12).

## Inputs

| Input | Value | Tag |
|---|---|---|
| Ratio | 54 / 18 = 3.00, module 1.0, 20°, centres 36.20 mm | REPO WG3 |
| Stage efficiency | 0.90 each direction (sensitivity 0.70 to 1.00 below) | ASSUMED (the pull test measures the net) |
| Motor holding torque | 0.36 N·m at 1.5 A, scaled with current; upper bound x 40/36; low case x 0.707 (A4988 full-step vector, the drive is wired full-step) | REPO |
| Spool radius | 7.5 mm core, 10 mm full | REPO |
| Running fraction | 0.7, set for the direct-drive winch at 64 rpm | REPO, unverified at 191 rpm |
| Line speed | 50 mm/s | REPO `config/robot.sim.json` max_cable_speed_m_s |
| Warm factor, printed PETG next to the motor | 0.85 | ASSUMED (WL) |
| PETG tooth allowable (Lewis basis) | 22.5 MPa (half the UTS) x 0.85 = 19.1 MPa | REPO (review R5, D39) |
| PETG in-plane UTS (failure basis; teeth print flat, bend along the layers) | 45 MPa x 0.85 = 38.25 MPa | REPO; warm ASSUMED |
| Root fillet concentration Kf | 1.8 (range 1.5 to 2.0) | ASSUMED |
| Tooth thinning | 0.10 mm, stress x (t / (t - 0.10))² = 1.141 with t = π·m/2 | REPO WG3; approximation |
| Lewis form factor | 0.309 (18T), 0.4142 (54T) | SRC Shigley's table; 54T interpolated between 50T 0.409 and 60T 0.422 (SRC, interpolated) |
| Contact materials | steel E 200 GPa, ν 0.30; PETG E 1800 MPa, ν 0.38 | SRC; REPO (`simulation_loads`) |
| PETG compressive strength | 50 MPa x 0.85 = 42.5 MPa | ASSUMED typical |
| Steel pinion bending allowable | 150 MPa (carbon steel; sintered or brass is lower) | ASSUMED |
| Set-screw friction, steel hub (tip = bore) | 0.10, 0.15, 0.20; seat 3 to 4 in-lb, cup bite 1.15 (WL model) | ASSUMED |
| 687 bearing static rating C0 | 600 N | ASSUMED, check the datasheet |
| Spool shaft yield | 350 MPa (plain Ø7 dowel; hardened are higher) | ASSUMED |
| Motor radial limit | about 28 N at 20 mm from the face | SRC 17HS4401 listing (WL); check Jasper's motor |
| Motor front bearing, motor shaft | C0 380 N, 3 mm behind the face, 30 mm span; yield 350 MPa | ASSUMED (WL) |
| Encoder | 4096 counts per turn; a skip is 4 full steps; rotor lag up to 1 full step; AS5600 nonlinearity 0.5° to 1.0° as mounted | REPO; ASSUMED |
| Knot, claw eye, dovetails, #6 wall screws in SPF, 3 dead wraps | as in WL | REPO (WL, unchanged) |

## Results

| | Direct drive today, 1.5 A | **Geared, 1.0 A (recommended)** | Geared, 1.5 A |
|---|---|---|---|
| A4988 Vref (R100) | 1.20 V | **0.80 V** | 1.20 V |
| Lift capacity (design, worst cable), full-step vector to nominal | 1.10 to 1.56 kg (-27 % to +4 %) | **1.98 to 2.80 kg (+32 % to +87 %)** | 2.97 to 4.20 kg (+98 % to +180 %) |
| Most the motor pulls before it slips | 34 to 59 N | **68 to 132 N** | 102 to 198 N |
| Every part must hold (1.5 x) | 89 N | **198 N** | 297 N |
| Motor heat | 4.05 W | **1.80 W** | 4.05 W |

Margins on 1.50 kg (claw 0.60 + jeans 0.90). The low end uses the A4988 full-step current vector (both coils at 0.707 of the
trip current, MS1-3 low); the high end is the rated torque. The 0.7 running fraction was set for the direct-drive winch at
50 mm/s = 64 rpm and is carried to 191 rpm unverified (pull-out torque falls with speed, the repo has no curve); the pull test at
50 mm/s replaces it.

| Link | Load at the slip torque, 1.0 A | Ratio, 1.0 A | Ratio, 1.5 A |
|---|---|---|---|
| Printed 54T teeth (UTS, Kf, thinning) | F_t 32.9 N, 16.3 MPa vs 38.25 | 2.34 PASS | 1.56 PASS |
| Tooth contact, steel on PETG (Hertz) | p 31.7 MPa vs 42.5 | 1.79 PASS | 1.20 MARGINAL |
| Pinion set screw, steel on steel D-flat | 0.29 to 0.78 N·m vs 0.27 | 1.10 to 2.92 MARGINAL | 0.73 to 1.95 MAY GIVE FIRST |
| Spool body, drum core torque | 0.89 N·m, 1.4 MPa vs 12.3 | 8.75 PASS | 5.84 PASS |
| Spool shaft Ø7, bending | 1549 N·mm, 46.0 MPa | 7.61 PASS | 5.07 PASS |
| 687 bearings, static | 88.4 N near, 107.0 N far | 5.61 PASS | 3.74 PASS |
| Motor shaft, bending at the D-flat | 31.5 N at 22 mm, 67.4 MPa | 5.19 PASS | 3.46 PASS |
| Motor front bearing, static | 55 N vs C0 380 | 6.95 PASS | 4.64 PASS |
| Line knot | 266.9 N vs 131.9 | 2.02 PASS | 1.35 MARGINAL |
| Wall screws, one stud column | 391 N of line puts the top screw at design withdrawal (D3, cable y 36.8) | 2.96 PASS | 1.97 PASS |
| Wall plate, screw head pulls through | 3166 N per screw at 3968 N of line (D3, cable y 36.8) | 30.08 PASS | 20.05 PASS |
| Claw cable eye | 1015 N | 7.69 PASS | 5.13 PASS |
| Slide-in dovetails | 13351 N (WL value scaled by tension) | 101.20 PASS | 67.47 PASS |

Ratio = load at which the link gives / the motor's upper slip force (131.9 N at 1.0 A, 197.9 N at 1.5 A); torque links by
torque. At 1.0 A nothing gives first; the pinion set screw is marginal at the low-friction end. At 1.5 A the set screw may give
first, and the knot and the tooth contact are marginal, so 1.0 A is the recommendation: capacity 1.98 to 2.80 kg clears the needed
1.50 kg by 32 % to 87 % at less than half the heat.

**Printed teeth and contact** (spool-side tangential force = slip torque x 3 / η / 27 mm; pinion-side 29.6 N at 1.0 A, 44.4 N at 1.5 A):

| | 1.0 A | 1.5 A |
|---|---|---|
| Spool-side tangential force F_t | 32.9 N | 49.4 N |
| Lewis stress, printed 54T | 7.95 MPa | 11.92 MPa |
| (a) Lewis SF on the half-UTS allowable (19.1 MPa warm) | 2.41 | 1.60 |
| Root stress, Kf 1.8 and thinning x 1.141 | 16.3 MPa | 24.5 MPa |
| (b) D39 ratio, against the warm in-plane UTS 38.25 MPa (used in the links table) | 2.34 | 1.56 |
| Hertz p_max at the pitch point (F_n 35.0 N / 52.6 N, ρ 2.31 mm, E* 2084 MPa) vs 42.5 MPa | 31.7 MPa | 38.9 MPa |
| Hertz force ratio (allowable / p)² | 1.79 | 1.20 |
| Steel pinion, Lewis stress (share of 150 MPa) | 10.7 MPa (7.1 %) | 16.0 MPa (10.7 %) |

(a) is the old basis and reads as a margin to a half-UTS design stress, not to failure; (b) is the failure basis the links table
uses. The steel pinion is not critical (under 11 % of a steel allowable at both currents); the purchase spec must say **steel**,
not sintered or brass.

**Pinion set screw** (WL's friction model with steel-hub friction, tip = bore; ratio to the motor's upper torque, 3 in-lb seat):

| Friction | 0.10 | 0.15 | 0.20 |
|---|---|---|---|
| Ratio at 1.0 A | 1.10 | 1.64 | 2.19 |
| Ratio at 1.5 A | 0.73 | 1.10 | 1.46 |

With the 3 to 4 in-lb seat the joint holds 0.29 to 0.78 N·m: ratio 1.10 to 2.92 at 1.0 A (MARGINAL), 0.73 to 1.95 at 1.5 A
(MAY GIVE FIRST). The earlier 2.50 and 1.66 used the PETG-bore friction (0.25) of WL and are an upper case for a steel hub. A
pinion slip turns the motor without the spool, so the spool encoder reports it exactly like a motor slip (TRACKING fault,
detected); the risk is marring the flat. Mitigation for Jasper: buy a pinion with two set screws (one on the flat) or add
retaining compound on the bore, and torque-slip test the joint on the bench (torque wrench, motor shaft locked).

**Spool shaft and bearings.** The cable (full 131.9 N, radial) is scanned over the drum width (y 20.8 to 36.8 mm) and 0° to 84°
from straight down; straight down is the worst. Mesh at the gear mid-face: 32.9 N tangential + 12.0 N radial. Envelope: 88.4 N on the
near bearing (cable at the gear side), 107.0 N on the far bearing (cable at the flange side), moment 1549 N·mm, 46.0 MPa (7.61 x
yield); the old mid-plane case gave 65.5 / 83.2 N and 1470 N·mm. The fleeted line (26.1°) also pulls axially, T·sin 26.1° = 57.9 N.
Equivalent static bearing load 107.0 N (all thrust on the far bearing), 5.61 x C0. At 1.5 A: 132.6 / 160.5 N, 2323 N·mm, 69.0 MPa
(5.07 x), thrust 86.9 N.

**Other loads.** Spool body: drum core shear 1.41 MPa at the spool-side torque 0.889 N·m (J 4734 mm⁴), 8.75 x the warm shear
allowable 12.3 MPa; the shaft carries no torque (web windows not checked). Spool tie-off (Ø1.4 chord hole, ligaments 1.05 mm to
the bore, 1.55 mm to the core surface): with the 3 dead wraps the capstan share (15 to 39 %) leaves **20 to 51 N** at the tie-off,
without them **131.9 N**; WL has no strength figure for the tie-off, so the **3 dead wraps are required**.

**Efficiency sensitivity at 1.0 A:**

| η | 0.70 | 0.80 | **0.90** | 0.95 | 1.00 |
|---|---|---|---|---|---|
| Capacity, nominal (full-step vector) | 2.18 kg (1.54) | 2.49 kg (1.76) | **2.80 kg (1.98)** | 2.96 kg (2.09) | 3.11 kg (2.20) |
| Fuse upper | 169.6 N | 148.4 N | **131.9 N** | 125.0 N | 118.7 N |
| Knot ratio | 1.57 | 1.80 | **2.02** | 2.14 | 2.25 |

The knot passes 1.5 x only while η is at least 0.67.

## Design inputs for Jasper (he designs the mount, cheeks and shell)

- **The cable no longer loads the motor tab through the motor.** It loads the two bearing seats. At 1.0 A the near seat (in the
  extended motor tab) must hold **133 N** and the far cheek **161 N** radial (1.5 x the envelope reactions 88.4 and 107.0 N),
  through a 14 mm bore, and both must retain the bearing outer race against **87 N axial** (1.5 x 57.9 N). At 1.5 A: 199 N and
  241 N radial, 130 N axial.
- **Every part of the station must now hold 198 N** of cable tension, not 89 N. The motor shaft and the motor screws no longer
  carry the cable (the shaft sees only the mesh force, below, the screws only the mesh and torque reactions), and WL's motor-tab
  link (cable pulled through the motor, 24 mm lever) no longer applies: the tab now carries the near seat load only. The as-drawn
  5 mm tab with a sharp corner gave first at 70 N warm (`lift_chain_weakest_link.md`); whatever he extends down to the spool axis
  must meet the 133 N seat load with fillets on its roots.
- **The wall screws are evaluated at the new load point** (the cable leaves the r = 7.5 mm tangent point of a spool axis 36.2 mm
  below the motor axis, anywhere across the drum): 391 N of line puts the top screw at design withdrawal (D3, cable at the drum
  end), ratio 2.96; the old point gave 531 N (D2c), ratio 4.03. WL's one-column model is used unchanged. The lever is Jasper's to
  change with the mount, so re-run after he fixes it. The spool and gear weight (about 0.05 kg) is not added. The remaining WL
  links that still carry the cable are in the links table; WL's dovetail check has no load point (flank bearing from the
  pull-away force, linear in tension), so its value is scaled to the new fuse by tension and the moment of the lower line point is
  not in it.
- **Motor shaft:** in normal running the pinion puts 7.1 N on the motor shaft 19 mm from the face; at the slip torque 31.5 N,
  **1.13 x** the 28 N catalogue limit at 20 mm. That limit is a bearing-life rating, so one short peak at a slip does no harm, but
  repeated retries against a hung claw repeat the peak. At 1.5 A the slip peak is 47.3 N, **1.69 x**: another reason to run 1.0 A.
  Static: 67.4 MPa at the D-flat section with a 22 mm lever to the front bearing (5.19 x yield), front bearing 55 N against
  C0 380 N (6.95 x).
- **Pinion:** steel 18T M1 with two set screws (one on the flat) or retaining compound; **not** sintered or brass.
- **Spool tie-off:** keep the 3 dead wraps.

## Encoder and software

| Item | Value | Why |
|---|---|---|
| One skip (4 full steps) at the spool | 2.4° = **27.3 counts** = 0.31 mm of line | was 82 counts direct |
| One full step at the spool | 6.83 counts | 4096 / (200 x 3) |
| Gear backlash at the spool | 5.9 counts | 0.246 mm at the pitch circle, from `P.WG3_CD_ALLOW` and the tooth thinning |
| `tracking_tol_counts` | **60** (keep; same as `config/robot.sim.json`) | a cable-length tolerance: 60 counts = 0.69 mm of line at the core, geared or direct. An overload slips continuously and trips it within 3 skips (12 full steps, 0.94 mm of line, 18.8 ms at 637 steps/s, then the 0.15 s dwell); one or two isolated skips (0.31 to 0.63 mm) are below it by design |
| `full_steps_per_rev` (motor steps per spool turn) | **600** | 200 x 3; the software uses it per spool revolution, so only the config changes |
| 50 mm/s at the core | 637 full steps/s, motor 191 rpm (direct drive 64 rpm); `max_step_rate_hz` about 800 | |
| Cable per full step at the core | 0.079 mm | was 0.236 mm |
| `drive.step_sign` | **flip**, if the cable still leaves the drum on the room side (+x), hanging down; the first bench move confirms it (a wrong sign gives an immediate TRACKING fault) | the spur pair turns the spool opposite to the motor (or swap one motor coil pair) |
| `encoder.sign` | expected unchanged (sensor still looks from +y); measure again | the magnet moves to the far end of the spool shaft |

Error budget of the tracking counts (persistent, worst case):

| Source | Counts |
|---|---|
| Command quantisation (one full step) | 6.8 |
| Rotor lag before pull-out (up to one full step) | 6.8 |
| Gear backlash after a reversal | 5.9 |
| AS5600 nonlinearity as mounted (0.5° to 1.0°, ASSUMED) | 5.7 to 11.4 |
| Sum | 25.3 to 31.0 |

60 counts is x1.94 to x2.37 over the sum (29.0 counts of headroom over the high end). Log `terr` on the bench at rated pull in both
directions to replace the sensor range.

Change the configs only when the gearbox is installed; until then the direct-drive values stay.

## Limits

- Efficiency 0.90, the 0.7 running fraction (carried from 64 to 191 rpm), Kf 1.8, the thinning factor (an approximation) and the
  Hertz compressive strength are assumed; the pull test on the built station at 50 mm/s replaces them, and a static tooth test
  belongs in it.
- Capacity is a range because the true motor torque is not known (full-step vector against the rated figure); until the pull
  test, plan with the low end.
- The shaft check takes the full cable force radial, anywhere across the drum and in any reachable direction (straight down is
  the worst), and the mesh force at the gear mid-face; the bearing seat loads assume a rigid shaft on two simple supports.
- Teeth: Lewis bending and Hertz contact only, static; printed tooth wear and creep under a long hold are not covered, and
  continuous testing (next phase) logs them. The in-plane strength basis holds only for gears printed flat.
- The wall-screw and head-punch rows use WL's models at the new load point; the dovetail row is scaled by tension (see above).
