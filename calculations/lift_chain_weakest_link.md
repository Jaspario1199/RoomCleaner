# Weakest link of the lifting chain, one winch station at 1.5 A

Asked by Jasper (10/22): "validate the weakest links in the chain for each module for lifting: first how much the studs can
hold, then the mount itself, then the cable and the joint holding the motor, then the torque. The goal is to make the motor
torque the smallest force that gives first, so the motor slips before anything is damaged, and the encoder picks it up and
reports an overload."

Script: `calculations/lift_chain_weakest_link.py` (numbers in `lift_chain_weakest_link.json`). It reuses the station load model
of `calculations/simulation_loads.py` (directions, tab hand model, wall-screw group). CALCULATED, not measured.
Independent check: `verification/lift_chain_weakest_link_check.md` (arithmetic agreed; findings F1 to F9 applied on 10/22:
tab faces paired with their own root detail and a direction scan, warm PETG, insert fit and pull-out, the 10/21 spool bore,
the fin in the shaft lever, the set-screw verdict relabelled "may give first", the computed dovetail value).

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

Design condition: PETG parts rated warm (× 0.85, the 1/8 in fin keeps the motor at 45 to 49 °C; the PETG next to the motor runs
at about the motor temperature). Torque links are shown as straight cable on the empty core and rated by torque.

| Link | Gives at, low | high | Ratio to the motor | Verdict |
|---|---|---|---|---|
| Spool set screw in the **printed** thread (as drawn) | 22 N | 64 N | 0.42 to 1.21 (0.17 to 0.48 of 0.40 N·m) | **May give first** |
| Motor torque (the fuse) | 34 N | 59 N | | Fuse |
| Spool set screw in **metal** (short insert or captive nut) | 53 N | 118 N | 1.00 to 2.2 (0.40 to 0.88 N·m) | Marginal: test |
| Motor tab, 5 mm, **sharp back corner** (as drawn) | 70 N | 82 N (room) | 1.17 | **Marginal** |
| Motor tab, 5 mm with a 2 mm back fillet | 87 N | 103 N (room) | 1.47 | Marginal |
| Motor tab, **6 mm with fillets on both roots** | 125 N | 147 N (room) | 2.11 | Pass |
| Motor shaft, bending yield at the D-flat | 149 N | 255 N | 2.5 | Pass |
| Line knot, 120 lb braid | 267 N | 480 N | 4.5 | Pass |
| Wall screws, 3 × #6 in one stud column | 531 N | 2954 N | 8.9 | Pass |
| Claw cable eye, knot behind a washer | 1.0 kN | 1.8 kN | 17 | Pass |
| Motor screws, 4 × M3 × 12 into the motor | 3.1 kN | 7.6 kN | 53 | Pass |
| Wall plate: screw head pulls through the PETG | 5.5 kN | 9.9 kN | 93 | Pass |
| Slide-in dovetails and lips | 13 kN | | 225 | Pass |
| *For comparison: the 6 wall screws in drywall only, no stud* | *46 N* | *95 N* | *0.77* | *Gives first* |

Prototype stations (0.019 in fin, 56 to 59 °C, PETG × 0.70): tab as drawn 57 N (0.96), 5 mm with a back fillet 72 N, 6 mm with
fillets 103 N (1.74).

### What the numbers say

1. **As drawn, the motor may not be the weakest link.** The set screw that holds the spool on the shaft is threaded into printed
   PETG. A warm printed thread strips at about 280 to 510 N, so the screw can only be seated to about 140 to 410 N, and its
   friction then carries 0.17 to 0.48 N·m. The motor can apply up to 0.40 N·m. The range straddles the motor, so it **may** slip
   first; the independent check puts the chance at 35 to 80 % depending on the assumed inputs.
   - The encoder is on the **spool**, so a spool slipping on the shaft is still caught as a tracking fault. But each slip
     wears the bore, while a motor skip does no damage.
   - The D-flat is no backup: on the 10/21 spool (bore 5.30, 4.80 across the flat) the shaft turns 13.8° before the flats meet,
     and they meet 0.98 mm from the axis, a steel edge on PETG carrying about 370 N at 0.36 N·m (v3 spool, bore 5.45: 25° and
     720 N). PETG crushes under that line contact.
   - Moving the screw into metal (a short insert or a captive nut) gives 0.40 to 0.88 N·m. A standard 5.7 mm M3 insert does not
     fit: the hub wall at the screw is 5.35 mm. The insert's own pull-out in warm PETG (400 to 750 N assumed) then limits the
     seat force, so this is marginal on paper and the bench test decides it.
2. **The motor tab's sharp back-side corner gives at 70 N warm, 1.17 times the motor**, with the cable pulled straight down
   and fleeted toward the spool (82 N at room temperature). A 2 mm back fillet moves the limit to the existing R2.5 spool-side
   fillet (87 N warm, 1.47 times), with the cable pulled high and along the wall. A **6 mm tab with fillets on both roots**
   gives 125 N warm (2.11 times).
3. **Studs are far from the limit; drywall is not.** One #6 wood screw with 1 in of thread in a spruce-pine-fir stud has an NDS
   design withdrawal value of 309 N (69 lb) and an average test ultimate of about 1.7 kN. The worst top screw sees 38 N at the
   motor's upper slip force (59 N). The same six screws in bare drywall would let go at about 46 N, below the motor.
4. **Line, shaft and motor screws** are 2.5 to 53 times the motor. The shaft lever includes the 1/8 in fin (24.2 mm).
5. **Detection.** A stepper loses steps in whole electrical cycles (4 full steps = 7.2° = 82 counts, 0.94 mm of cable on the
   empty core). The simulation profile trips the tracking fault at 60 counts (5.3°, 0.69 mm) held for 0.15 s, so a single skip is
   caught. The margin is only 1.37, and the hardware configs leave the tolerance unset: set it below 82 counts (60 proposed) at
   the bench stage.

### Design changes (proposed, Jasper to approve)

| # | Change | Effect |
|---|---|---|
| 1 | Spool set screw into metal: a short M3 heat-set insert (4 mm, fits the 5.35 mm wall) or a captive M3 nut; cup-point screw seated to 3 to 4 in·lb with medium thread locker | 0.40 to 0.88 N·m against the motor's 0.40: marginal on paper, so the pull test decides. If it slips below 0.6 N·m, a metal 5 mm hub with two set screws |
| 2 | Motor tab 6 mm with 2 mm fillets on both roots (the spool-side root is R2.5 today) | 2.11 × the motor warm; SF 2.8 at the slip force along the wall. 7 mm reaches the static manual's SF 3 (3.8) but needs M3 × 14 |
| 3 | Wall screws into the stud only; one column of three if both columns cannot land in a 38 mm stud | 8.9 × the motor |
| 4 | Keep at least 3 dead wraps on the spool (planner line limit) | Not needed by the numbers (the knot is 4.5 ×); protects the untested knot and the Ø1.4 tie-off hole's 0.8 mm ligament, and keeps the fuse working at full payout |
| 5 | Hardware tracking tolerance 60 counts (below one 82-count skip) | A single skip trips the fault |
| 6 | Report a tracking fault toward payout as an **overload** with the slip in mm | Software (host message only) |

With a 6 mm tab and the 1/8 in fin, M3 × 12 screws leave 2.8 mm of thread in the motor (strip strength still about 1.9 kN per
screw). The tab must still clear the spool (spool base at about y 7).

**Static study at 1.5 A.** The SolidWorks manual (`docs/simulation/SW_STATIC_STATION_MOUNT.md`) was written at the 1.06 A slip
force of 34 N and scales linearly (its section 7.1). At 1.5 A the slip force is 48 N (53.4 N on a fleeted cable). The hand model
gives the 5 mm tab a factor of safety of 1.94 on the 25 MPa derated yield in the along-wall case, 2.79 at 6 mm and 3.81 at 7 mm.

**If a 2:1 gear stage is added** (the fallback if the pull test comes in low), the fuse doubles to about 119 N at the cable and
this ranking has to be redone: the 6 mm tab (125 N) would then be level with the motor.

## Inputs and sources

- Motor: 0.36 N·m at the rated 1.5 A (D37; `docs/SHOPPING_LIST.md`); 40 N·cm sensitivity (17HS4401 nameplate, unverified);
  running = 0.7 × holding (assumed, the pull test measures it). Spool radius 7.5 mm empty, 10 mm full (Spoolv3, review R4).
- Line: 9KM DWLIFE X8, 120 lb (`docs/SHOPPING_LIST.md`). Knot efficiency 50 % (clinch-type knots in braid) to 90 % (Palomar)
  [published fishing tests, see Sources].
- Spool joint: the 10/21 reference spool in `cad/params.py` (bore 5.30, flat 2.15 mm from the axis, hub Ø15); v3 Spoolv3
  (bore 5.45) shown for comparison; set-screw geometry from review R4. Friction 0.20 (steel tip) and 0.25 (steel on PETG), cup bite
  +15 %, K = 0.20, seat torque 3 to 4 in·lb for a #4-40 / M3 cup point in steel; PETG thread shear 14.5 to 26 MPa; seated at
  50 to 80 % of the strip force; short-insert pull-out 400 to 750 N. All assumed; the bench test below replaces them.
- Shaft and bearing: Ø5 with a 0.5 mm flat (Z = 10.3 mm³, minimum over all bending directions), yield 350 to 600 MPa, lever
  24.2 mm (drum 18 mm + the 3.175 mm fin + front bearing 3 mm behind the flange), bearings 30 mm apart, 625-size static rating 380 N (assumed). The 28 N radial rating at
  20 mm (17HS4401 listing) is a life rating: the running pull at the empty core is 1.2 × that, so bearing life is worth
  watching, not strength.
- Motor screws: 3.8 mm of thread in the aluminium cap (D38), 120 MPa shear; head Ø5.5 punching through the 5 mm tab.
- Tab: root section with each face paired with its own root detail (back: sharp, Kt 2.5; spool side: R2.5, Kt 1.5),
  scanned over every reachable cable direction (polar 0 to 84°, azimuth ±90°, fleet clipped); 25 MPa derated yield and
  22.5 MPa across layers, × 0.85 warm (design) or × 0.70 (prototype fin).
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

- Hand estimates. The tab and the dovetails come from a cantilever model of the root; the SolidWorks study is still to run,
  at 48 N now (and 53.4 N fleeted).
- Everything scales with the real driver current, which is not recorded (D37). At 1.7 A the fuse upper is 67 N.
- The warm-PETG factors are assumed; the hold test measures the temperatures.
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
