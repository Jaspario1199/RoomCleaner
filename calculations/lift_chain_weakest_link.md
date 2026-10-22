# Weakest link of the lifting chain, one winch station at 1.5 A

Asked by Jasper (10/22): "validate the weakest links in the chain for each module for lifting: first how much the studs can
hold, then the mount itself, then the cable and the joint holding the motor, then the torque. The goal is to make the motor
torque the smallest force that gives first, so the motor slips before anything is damaged, and the encoder picks it up and
reports an overload."

Script: `calculations/lift_chain_weakest_link.py` (numbers in `lift_chain_weakest_link.json`). It reuses the station load model
of `calculations/simulation_loads.py` (directions, tab hand model, wall-screw group). CALCULATED, not measured.
Independent check: `verification/lift_chain_weakest_link_check.md`.

## The chain and the rule

Line force path, claw to house:

claw tie-off → Dyneema line → spool tie-off → spool hub → **set screw on the D-flat** → motor shaft and bearings →
**motor torque (the intended fuse)** → 4 × M3 × 12 into the motor → **5 mm PETG motor tab** → slide-in dovetails → wall mount
plate → **wall screws** → wood stud

For each link: the **cable tension at which it gives** (breaks, strips, yields or slips), as a lower and an upper estimate.
The motor is the fuse: above its holding torque the rotor skips, the spool turns away from the command, and the station's
tracking fault stops it. So every other link must give at a higher cable tension than the **most** the motor can pull before
it skips:

- Fuse, upper: τ_h × (40/36) / r_empty / cos(fleet) = 0.36 N·m × 1.111 / 0.0075 m / cos 26.1° = **59.4 N**
- Rule: link (lower estimate) / 59.4 N **≥ 1.5** passes; 1.0 to 1.5 is marginal; below 1.0 the link gives before the motor.
  Torque links (the spool joint) compare N·m with the motor's 0.40 N·m. The 1.5 covers the overshoot while the rotor skips and
  the scatter of printed parts.

## Results

### Demand and the fuse

| Case | Cable tension |
|---|---|
| Jeans, worst cable (1.50 kg × 1.101 × g, +2 m/s² included) | 16.2 N |
| Design force (full spool, 1.5 skip margin) | 16.8 N |
| Motor skips **while moving**: full / empty spool (0.7 × holding) | 25.2 / 33.6 N |
| Motor slips **while holding**: full / empty spool | 36.0 / 48.0 N |
| Holding, low bound (torque vector 1/√2 of the datasheet) | 33.9 N |
| Holding, fully fleeted cable (26.1°) | 53.4 N |
| **Holding, upper (40 N·cm motor and fleeted cable)** | **59.4 N** |

The fuse sits 1.6 × above the jeans demand while moving at a full spool and 3.0 × above it while holding.

### Ranking (cable tension at which each link gives)

| Link | Gives at, low | high | Ratio to the motor | Verdict |
|---|---|---|---|---|
| Spool on shaft: set screw in the **printed** thread (as drawn) | 29 N | 82 N | 0.48 (0.19 of 0.40 N·m) | **Gives first** |
| Motor torque (the fuse) | 34 N | 59 N | | Fuse |
| Motor tab root, **sharp** back corner (as drawn), along-wall pull D4f | 62 N | 172 N | 1.05 | **Marginal** |
| Spool on shaft: set screw in a **brass heat-set insert** | 99 N | 132 N | 1.66 (0.67 of 0.40 N·m) | Pass |
| Motor tab root with a **2 mm fillet** | 103 N | 172 N | 1.74 | Pass |
| Motor shaft, bending yield at the D-flat | 171 N | 294 N | 2.9 | Pass |
| Line knot, 120 lb braid | 267 N | 480 N | 4.5 | Pass |
| Wall screws, 3 × #6 in one stud column | 531 N | 2954 N | 8.9 | Pass |
| Slide-in dovetails and lips | > 1 kN | | > 16 | Pass |
| Motor screws, 4 × M3 × 12 into the motor | 4.3 kN | 8.9 kN | 73 | Pass |
| Wall plate: screw head pulls through the PETG | 5.5 kN | 9.9 kN | 93 | Pass |
| *For comparison: the 6 wall screws in drywall only, no stud* | *46 N* | *95 N* | *0.8* | *Gives first* |

### What the numbers say

1. **As drawn, the motor is not the weakest link.** The set screw that holds the spool on the shaft is threaded into printed
   PETG. A printed thread strips at about 330 to 590 N, so the screw can only be seated to about 160 to 470 N, and its friction
   then carries 0.19 to 0.55 N·m. The motor can apply up to 0.40 N·m. At the low end the spool slips on the shaft at 29 N of
   cable, below the motor's own slip.
   - The encoder is on the **spool**, so a spool slipping on the shaft is still caught as a tracking fault. But each slip
     wears the bore, so the joint gets weaker every time, while a motor skip does no damage.
   - The D-flat is no backup today: the bore is 4.95 mm across its flat against the shaft's 4.50, so the shaft turns 25°
     before the flats meet, and they meet 0.5 mm from the axis (720 N of line contact on PETG at 0.36 N·m).
2. **The motor tab's sharp back-side corner gives just above the motor** (62 N against 59 N) when the cable pulls along the
   wall. A 2 mm fillet raises it to 103 N (1.74 ×).
3. **Studs are far from the limit; drywall is not.** One #6 wood screw with 1 in of thread in a spruce-pine-fir stud has an NDS
   design withdrawal value of 309 N (69 lb) and an average test ultimate of about 1.7 kN. The worst top screw sees 34 N at
   the motor's upper slip force. The same six screws in bare drywall would let go at about 46 N, below the motor.
4. **Line, shaft and motor screws** are 2.9 × to 73 × the motor.
5. **Detection.** A stepper loses steps in whole electrical cycles (4 full steps = 7.2° = 82 counts, 0.94 mm of cable on the
   empty core). The tracking fault trips at 60 counts (5.3°, 0.69 mm of cable) held for 0.15 s, so a single skip is caught.

### Design changes (proposed, Jasper to approve)

| # | Change | Effect |
|---|---|---|
| 1 | M3 brass heat-set insert in the spool hub for the set screw; seat the cup-point screw to 3 to 4 in·lb (0.34 to 0.45 N·m) with medium thread locker | Joint 0.67 to 0.89 N·m: 1.66 × the motor |
| 2 | Print the spool bore to 5.15 mm with the flat at 4.62 mm (0.12 mm clearance) | The D-flat engages after 5° at 1.3 mm from the axis: a real backup |
| 3 | 2 mm fillet on the motor tab's back-side root; 6 mm tab if the static study's SF 3 at the slip force is to hold (see below) | Tab 1.74 × the motor (5 mm + fillet) |
| 4 | Wall screws into the stud only; one column of three if both columns cannot land in a 38 mm stud | 8.9 × the motor |
| 5 | Keep at least 3 dead wraps on the spool (planner line limit) | The spool tie-off sees 15 to 39 % of the cable tension; the fuse also works at full payout |
| 6 | Report a tracking fault toward payout as an **overload** with the slip in mm | Software (host message only) |

**Static study at 1.5 A.** The SolidWorks manual (`docs/simulation/SW_STATIC_STATION_MOUNT.md`) was written at the 1.06 A slip
force of 34 N and scales linearly (its section 7.1). At 1.5 A the slip force is 48 N (53.4 N on a fleeted cable). The hand model
then gives the 5 mm tab with a 2 mm fillet a factor of safety of 2.15 on the 25 MPa derated yield in the along-wall case, below
the manual's 3, and a cable-exit deflection of 0.53 mm against its 0.5 mm limit. A 6 mm tab with the fillet gives 3.04 and
0.31 mm. With the 1/8 in fin, M3 × 12 screws then leave 2.8 mm of thread in the motor (strip strength still about 1.9 kN per
screw). The weakest-link order passes with the 5 mm tab and fillet; the 6 mm tab is for the long-term creep criterion.

**If a 2:1 gear stage is added** (the fallback if the pull test comes in low), the fuse doubles to about 119 N at the cable and
this ranking has to be redone: the 5 mm tab with a fillet (103 N) would then give before the motor.

## Inputs and sources

- Motor: 0.36 N·m at the rated 1.5 A (D37; `docs/SHOPPING_LIST.md`); 40 N·cm sensitivity (17HS4401 nameplate, unverified);
  running = 0.7 × holding (assumed, the pull test measures it). Spool radius 7.5 mm empty, 10 mm full (Spoolv3, review R4).
- Line: 9KM DWLIFE X8, 120 lb (`docs/SHOPPING_LIST.md`). Knot efficiency 50 % (clinch-type knots in braid) to 90 % (Palomar)
  [published fishing tests, see Sources].
- Spool joint: bore, flat and set-screw geometry from review R4. Friction 0.20 (steel tip) and 0.25 (steel on PETG), cup bite
  +15 %, K = 0.20, seat torque 3 to 4 in·lb for a #4-40 / M3 cup point in steel; PETG thread shear 14.5 to 26 MPa; seated at
  50 to 80 % of the strip force. All assumed; the bench test below replaces them.
- Shaft and bearing: Ø5 with a 0.5 mm flat (Z = 10.3 mm³, minimum over all bending directions), yield 350 to 600 MPa, front
  bearing 3 mm behind the flange, bearings 30 mm apart, 625-size static rating 380 N (assumed). The 28 N radial rating at
  20 mm (17HS4401 listing) is a life rating: the running pull at the empty core is 1.2 × that, so bearing life is worth
  watching, not strength.
- Motor screws: 3.8 mm of thread in the aluminium cap (D38), 120 MPa shear; head Ø5.5 punching through the 5 mm tab.
- Tab and dovetails: the hand model and Kt band of the static manual (Kt 2.5 sharp, 1.5 with a 2 mm fillet), 25 MPa derated
  yield and 22.5 MPa across layers.
- Wall screws: NDS reference withdrawal W = 2850 G² D L (lb, in; normal load duration, dry), G = 0.42 (spruce-pine-fir; 0.50
  Douglas fir-larch, 0.55 southern pine), #6 D = 0.138 in, L = 1 in of thread in the stud (#6 × 2½ in through 10.5 mm of PETG
  and ½ in drywall; measure the real screw). Ultimate in the Wood Handbook form P = 15 700 G² D L (secondary source, about
  5.5 × the design value). Lateral: the screw bent across the ½ in drywall gap, 271 N per screw. Drywall alone: 5 to 10 lb
  bare, 10 to 25 lb plastic anchors (published ratings).
- Screw loads: rigid plate, wall bearing ignored for the six-screw group (the static manual's model); one column of three
  tipping about the nearer plate edge.

Withdrawal per inch of thread (design / ultimate):

| Screw | Spruce-pine-fir (G 0.42) | Douglas fir-larch (0.50) | Southern pine (0.55) |
|---|---|---|---|
| #6 | 309 / 1700 N | 437 / 2409 N | 529 / 2915 N |
| #8 | 367 / 2020 N | 520 / 2863 N | 629 / 3465 N |
| #10 | 425 / 2341 N | 602 / 3317 N | 729 / 4014 N |

## Limitations

- Hand estimates. The tab and the dovetails come from the static manual's cantilever model; the SolidWorks study is still to
  run, at 48 N now (and 53.4 N fleeted).
- The set-screw range rests on assumed friction and seat force. It is the link most likely to be wrong in either direction,
  and the cheapest to measure.
- The fuse holds only while the motor is powered. With the power off, on an emergency stop or a reset, the cable pays out
  freely (the safe-state table); no link is loaded beyond the claw's weight.
- At full payout with no dead wraps the fuse is bypassed: the spool tie-off takes the whole tension.

## Test that settles it (fold into the pull test)

Paint one line across the shaft end, the spool face and the magnet cap. Pull the cable with the luggage scale at 1.5 A,
holding, on the empty core, until it slips.
- If the paint line stays in one piece, the **motor** skipped: that is the fuse working; record the force.
- If the line breaks between the shaft and the spool, the **spool slipped on the shaft**: fit the brass insert (change 1)
  before anything else.
- Either way the station should report the tracking fault; check that it does.

## Sources

- AWC National Design Specification (NDS) wood-screw withdrawal W = 2850 G² D, as quoted in
  [Huber AdvanTech technical tip](https://www.huberwood.com/uploads/documents/technical/Comparable-Fastener-Withdrawal-of-AdvanTech-Subflooring-and-Sheathing-Technical-Tip-Subflooring-AdvanTech_2021-01-25-151604.pdf)
  and [Engineering ToolBox, wood screws](https://www.engineeringtoolbox.com/wood-screws-allowable-withdrawal-load-d_1815.html).
- Test-based allowables divide the average ultimate by 5 (ICC-ES AC233):
  [Simpson Strong-Tie engineering blog](https://seblog.strongtie.com/?p=2873).
- Wood Handbook form P = 15 700 G² D L (secondary):
  [Fine Woodworking forum](https://finewoodworking.com/forum/correct-use-of-screws-and-wood-on-joi).
- Drywall anchors: [Dottie WD6](https://www.mc-mc.com/Product/dottie-wd6),
  [EngineerFix](https://engineerfix.com/how-much-weight-can-drywall-hold-without-a-stud/),
  [Austin Gallery hardware guide](https://www.austingallery.org/blog/how-much-weight-can-drywall-hold).
- Set screws: [Albany County Fasteners torque chart](https://www.albanycountyfasteners.com/media/33/7c/b2/1764616278/set-screw-size-torque-chart.pdf),
  [Machine Design, setscrews](https://www.machinedesign.com/fastening-joining/article/21834719/setscrews).
- Knots in braid: [Field & Stream knot test](https://www.fieldandstream.com/stories/fishing/knot-strength-isnt-all-about-line-strength),
  [Hunt Fish Sport knot strength (unverified)](https://huntfishsport.com/tools/knot-strength-calculator).
- NEMA 17 radial rating, 28 N at 20 mm: [17HS4401-1704A listing](https://elecena.pl/product/23173009/rss).
