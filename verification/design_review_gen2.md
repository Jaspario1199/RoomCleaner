# Design review — Generation 2 (SolidWorks redesign)

**Date:** 2026-10-19 · **Gate:** 7 (lead design audit) · **Reviewer:** lead engineer (AI-assisted review)
**Scope:** removable wall station (v3), short spool (v3), per-station
electronics, V5 geared clamp gripper, 1 lb first target.
**Evidence used:** Drive file names, dates and sizes; Outline v1 text; bench
results reported in the outline; gen-1 parts/specs in this repo; screening
calculations in `calculations/gen2_screening.py` (re-run to reproduce every
number below). Spool and reference STEP geometry is measured where it has been
copied into `solidworks/`; the gripper and wall-station geometry is **not yet
measurable** (SLDPRT only / not synced), so those findings are stated as
checks with pass criteria rather than pass/fail.

## Verdict

The architecture is sound and the scope (1 lb on four stations first) is the
right size. Two findings are **blockers for powered testing** (R2 boot/comms
safety, R8 driver capacitor), one is a **likely failure in the first gripper
print** (R5 gear teeth), and one is the **main technical risk of the whole
redesign** (R1 synchronizing four Wi-Fi nodes). None require changing the
concept.

| # | Area | Finding | Severity | Status |
|---|---|---|---|---|
| R1 | Electronics | Four independent nodes must change four cable lengths in sync; timing skew on a stiff line becomes tension spikes or slack | High | Open — design choice needed |
| R2 | Safety | Boot-time glitches can step a motor; comms-loss must HOLD, never disable; kill switch drops the load | High (blocker) | Open |
| R3 | Wall station | Slide-in housing needs positive retention and a load direction that seats it | Med-High | Needs geometry |
| R4 | Spool | Measured v3: 20 ft fits (5 layers, 8 mm flange margin). Radius grows 7.5 → 10 mm, a 33 % change in length per rev. Bore opened to Ø5.45 (loose) | Medium | Open |
| R5 | Gripper | Module-1, 6 mm-face PETG pinion fails at servo stall (SF 0.35–0.41) | High (likely failure) | Needs module/face |
| R6 | Workspace | Within ~0.3 m of the anchors, cable tension exceeds what the motor can pull | Medium | Open (software limit) |
| R7 | Sensing | Camera moved onto a swinging claw: view and localization trade-off | Medium | Decision to state |
| R8 | Electronics | Standalone A4988 needs a 47–100 µF bulk capacitor at VMOT on every station | High (blocker) | Open |
| R9 | Electronics | Driver logic supply: the 1.14 V fault shows the 3.3 V feed is a single point of failure | Low-Med | Partly fixed |

Positives worth presenting: the 24T/24T stage is a clean way to get two
counter-rotating jaws from one servo; grip force margin is ~2.8× for 1 lb; the
removable station decouples calibration from service; per-station wiring
removes four long motor harnesses; 20 ft of line covers the 15.3 ft worst-case
cable with 1.4 m to spare.

---

## R1 — Synchronized motion across four Wi-Fi nodes (High)

A cable robot with four position-controlled cables is **over-constrained**: any
difference between commanded and actual length on one cable shows up directly
as tension change in all four. Gen 1 avoided this by generating all four step
trains on one microcontroller (AccelStepper `MultiStepper`), so the cables
always moved together.

With four nodes, each receives its own command over Wi-Fi. Typical Wi-Fi
latency jitter is tens of milliseconds. At 50 mm/s of cable speed, 50 ms of skew
is 2.5 mm of length mismatch. Dyneema is stiff (estimated ~3 N/mm over a 3 m
run for a 0.5 mm line), so 2.5 mm is on the order of 8 N of unplanned tension,
or a slack cable if the error goes the other way. That is the same size as the
static load in R6.

**Recommended direction (pick one and say why on the slide):**
- *Time-stamped trajectory streaming:* the host sends each node its full
  segment list ahead of time with a start time; nodes sync clocks (ESP-NOW
  broadcast beacon) and start segments on the shared clock. Skew becomes clock
  error (sub-ms) instead of network jitter.
- *Coordinator node:* one node is master and broadcasts a "step tick" by
  ESP-NOW; other nodes only advance on ticks.
- *Hybrid:* keep central step generation (gen-1 wiring) for the integration
  test and move to distributed nodes once sync is proven. This is the
  lowest-risk path to the 1 lb demo.

**Pass criteria for the first four-node test:** commanded 300 mm vertical move
at 50 mm/s with the 1 lb load; no cable goes slack (visual + switch), measured
length error at end ≤ 2 mm per cable, no step loss.

## R2 — Boot, comms loss and the kill switch (High, blocker)

1. **Boot glitches.** ESP32 strapping pins and some GPIOs toggle during boot,
   and the A4988 `EN` input defaults to *enabled* (internal pull-down). A step
   pin that toggles during reset can move a loaded winch. Fix: external
   pull-up on `EN` (driver disabled until firmware drives it low after setup),
   pull-down on `STEP`, and use XIAO pins that are not strapping pins.
2. **Comms loss must hold, not disable.** A NEMA 17 with no brake and no
   current backdrives; disabling a driver on a lost connection drops the claw.
   Rule: on lost link, stop stepping and keep `EN` low (holding torque).
3. **The kill switch drops the load.** Cutting 12 V at the power strip makes
   every winch go limp at once. That is acceptable only with the existing rule
   that nobody is under the workspace, and it should be said explicitly in
   the presentation (it is a deliberate trade: a guaranteed stop over a
   controlled stop). One strip must feed all four stations.

**Pass criteria:** reset each node 10× under load with the 1 lb weight → zero
motion; pull Wi-Fi mid-move → load holds position; strip off → all four
stations unpowered within one motion.

## R3 — Wall station retention and load path (Med-High, needs geometry)

Load path to check on the v3 section: line → pulley/outlet → slide-in housing →
rails → wall frame → screws → stud. The line leaves the station toward the
room and downward, so the reaction on the housing points **down and away from
the wall**. Checks when the STEP files are synced:

- Slide direction: housing should insert **downward** (or toward the wall) so
  the line load seats it. If it slides out in a direction the line pulls,
  retention carries the full load.
- Positive retention independent of friction: screw, pin or snap rated for the
  full line load (32 N worst case, R6) with SF ≥ 3.
- Rail root: fillet ≥ 1 mm; rails printed so the load does not peel layers
  (load along the layer plane, not across it).
- Frame screws: with the line pulling away from the wall, screws see pull-out,
  not shear. Into a stud only; drywall anchors are not acceptable.
- Creep: PETG or better for the frame and housing; PLA under constant load
  near a warm ceiling creeps.

## R4 — Spool winding, bore fit and shaft loading (Medium)

**Measured from `solidworks/v3_2026-10-18/Spoolv3.STEP`** (and v2
`Spool1011_Step.STEP`, identical outside the bore): Ø36 flanges, 3 mm thick;
core (hub) Ø15; drum width 16 mm; overall 22 mm; bore Ø5.45 with a single
D-flat 0.50 mm deep (4.95 mm across the flat); Ø2.8 radial set-screw hole on
the flat's axis at 7 mm from the base, so the screw bears on the shaft flat;
Ø1.4 tie-off hole through the hub, offset 6 mm from the axis so it misses the
bore. v2 had a Ø5.2 bore (4.70 across the flat).

Winding 20 ft of 0.5 mm line (`gen2_screening.py`, 85 % packing):

| Drum width | Layers | Full radius | Line force core → full | Length/rev change | Flange margin |
|---|---|---|---|---|---|
| 10 mm | 7 | 11.0 mm | 24.0 → 16.4 N | 22.0 mm | 7.0 mm |
| **16 mm (v3 as drawn)** | **5** | **10.0 mm** | **24.0 → 18.0 N** | **15.7 mm** | **8.0 mm** |
| 20 mm | 4 | 9.5 mm | 24.0 → 18.9 N | 12.6 mm | 8.5 mm |

- **Capacity: pass.** 20 ft fills to ~10 mm radius, 8 mm inside the
  flanges. The flanges could be ~4 mm smaller in radius if mass or print time
  matters.
- **Calibration: action.** Radius changes 7.5 → 10 mm, so length per
  revolution changes by 15.7 mm (33 %). The controller must use radius as a
  function of wound length, or the claw drifts.
- **Bore fit: question.** v3 opened the bore from Ø5.2 to Ø5.45: 0.45 mm
  diametral clearance on a 5 mm shaft. That is loose for a printed hole unless
  your printer prints holes ~0.3 mm undersize. If you measured a v2 print as
  too tight and opened it, that is a good fit-coupon story for slide 7. Say
  what the printed bore measured. Either way, the set screw on the flat is
  what transmits torque. Use a thread-forming M3 or a heat-set insert, not a
  printed thread.
- **Shaft loading:** the line runs at the drum's mid-plane, 11 mm from the
  spool base. NEMA 17 front bearings are typically rated ~25–30 N radial at
  20 mm from the flange. The near-ceiling tension in R6 (32 N) reaches that,
  so keep the spool base as close to the motor face as the housing allows.

## R5 — Gripper gear teeth (High, likely failure)

Train from the V5 part names: 18T pinion → 54T (3:1) on a compound shaft with
a 24T gear → 24T follower (1:1, second jaw counter-rotates). Servo 180° gives
60° at the jaws.

Lewis bending at the 18T pinion (assumed module 1, face 6 mm, PETG allowable
22.5 MPa = 50 % of tensile for layers and fatigue):

| Case | Tangential force | Root stress | SF |
|---|---|---|---|
| MG996R stall 4.8 V | 102 N | 55 MPa | 0.41 |
| MG996R stall 6.0 V | 120 N | 65 MPa | 0.35 |
| Module 1.5, face 8 mm, 6 V | — | 22 MPa | 1.04 |
| Module 2.0, face 10 mm, 6 V | — | 10 MPa | 2.32 |

A clamp gripper drives into stall every time it closes on cloth, so stall is
the design case, not an edge case. Options: module ≥ 2 with ≥ 10 mm face; or a
metal pinion on the servo with printed 54T; or limit closing torque in firmware
(stop at a grip angle instead of stalling). Also: do not rely on a printed
spline — bolt the pinion to the servo's metal horn. Allow 0.1–0.2 mm extra
center distance for print tolerance and backlash.

Grip force is not the problem: 1 lb at μ = 0.3 needs 7.4 N per jaw; the
train delivers ~20.8 N per jaw at a 60 mm arm (4.8 V stall). That margin is
what allows torque limiting.

## R6 — Tension near the anchors (Medium)

Equal-share static tension, 1 lb + 0.45 kg claw, claw under room center:

| Depth below anchors | Tension per cable |
|---|---|
| 0.15 m | 32.1 N |
| 0.30 m | 16.1 N |
| 0.60 m | 8.3 N |
| 1.20 m | 4.6 N |

The motor delivers ~24 N of line force at the measured 7.5 mm core, falling to
~18 N at a full spool (36 N·cm × 50 % running margin / radius). Above ~0.3 m below the anchors the claw cannot be lifted, and
the bearing load in R4 peaks. Add a software ceiling (≥ 0.4 m below the
anchors) and never home by winching the claw up to the pulleys. Re-run the
gen-1 tension-feasibility solver (`roomcleaner/`) with the gen-2 anchor
positions; corner picks load the near cables far more than equal-share shows.

## R7 — Camera on the claw (Medium, decision to state)

Outline v1 places the camera in the claw's upper housing. That gives a close
view for the final grasp but the camera swings with the claw and no longer
sees the whole room. Gen 1 used a fixed overhead camera with a verified
pixel-to-floor mapping. Recommendation: keep the ceiling camera for "where is
the laundry" and use the claw camera for "am I centered and did I grab it".
State the choice and its reason in the presentation; the panel will ask.

## R8 — Driver bulk capacitor (High, blocker)

The CNC shield supplied a bulk capacitor across the motor supply. A standalone
A4988 at each station needs its own **47–100 µF electrolytic, ≥ 25 V, across
VMOT/GND, as close to the driver as possible**. Without it, voltage spikes from
the motor coils on a long 12 V run destroy the driver; this is the most common
A4988 failure. Watch polarity.

## R9 — Driver logic supply (Low-Med)

The bench fault (logic rail ~1.14 V instead of 3.3 V from a poor connection) is
a good presentation story and also a design flag: the A4988 VDD feed should be
a crimped/soldered connection, not a jumper, and should come from the same
regulated rail as the XIAO so the logic levels agree. Add a test step: measure
VDD at the driver before enabling.

## Inputs to confirm (replace assumptions, re-run the script)

| Input | Assumed | Where it comes from |
|---|---|---|
| Spool core radius, drum width | **measured** 7.5 mm, 16 mm | Spoolv3.STEP |
| Line effective diameter | 0.5 mm | calipers on wound line |
| Anchor positions / drop below ceiling | room corners, 0.15 m | tape measure after install |
| Motor running torque | 50 % of 36 N·cm | pull test vs speed (outline slide 5 calls for it) |
| Claw mass | 0.45 kg | scale, V5 assembled |
| Gear module and face width | 1 mm, 6 mm | V5 pinion SLDPRT / STEP |
| Jaw arm length | 60 mm | V5 assembly |
| Slide direction, retention feature | unknown | Slipin_mount_piece v3 STEP |
