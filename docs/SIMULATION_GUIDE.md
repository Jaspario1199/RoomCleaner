# SolidWorks Simulation guide — generation 2 assemblies

> **Focused manuals for the two presentation studies** (click-by-click, real part names, pass/fail tables):
> [Study A, static stress of the wall mount and housing](simulation/SW_STATIC_STATION_MOUNT.md) ·
> [Study B, steady-state thermal of the aluminium heat fin](simulation/SW_THERMAL_HEAT_FIN.md).
> Loads and targets come from [`calculations/simulation_loads.py`](../calculations/simulation_loads.py). This guide stays the reference for the one-time setup and the other studies.

Linear static studies for each gen-2 assembly, with every load traced to
`calculations/gen2_screening.py` or `verification/design_review_gen2.md`.
Results feed presentation slides 7, 8, 10 and backup B2.

## What these studies can and cannot tell you

- They assume an **isotropic, linear-elastic** material. FDM parts are weaker
  across layers and creep under constant load. That is handled by a derated
  allowable and a higher required safety factor, not by the solver.
- They are **static**. Jerk and swing are covered by a 2× dynamic factor on
  the load.
- Stress peaks at sharp corners and point fixtures are partly numerical.
  Judge them with a mesh-convergence check (step 8) and by whether the peak
  sits on a real feature (a rail root) or an artifact (the edge of a fixture).
- For the robot, **stiffness matters as much as strength**: the station's
  deflection at the cable exit moves the anchor point, and anchor error turns
  ~1:1 into claw position error.

## One-time setup

1. **Turn on Simulation:** Tools → Add-Ins → check *SOLIDWORKS Simulation*
   (both columns). A *Simulation* tab appears on the CommandManager.
2. **Units:** Tools → Options → Document Properties → Units → **MMGS**
   (mm, g, s). Then Simulation → Options → Default Options → Units → SI,
   length mm, stress N/mm² (MPa).
3. **Create the printed-PETG material once:** in any part, right-click the
   material → Edit Material → in the left tree, right-click *Custom Materials*
   → New Category "3D printed" → New Material "PETG FDM (derated)":

   | Property | Value | Note |
   |---|---|---|
   | Elastic modulus | 1800 MPa | printed, lower than bulk ~2100 |
   | Poisson's ratio | 0.38 | |
   | Mass density | 1270 kg/m³ | matches the repo's mass calcs |
   | Tensile strength | 45 MPa | bulk |
   | **Yield strength** | **25 MPa** | derated for layer adhesion; this is what the FoS plot uses |

   Make "PLA FDM (derated)" the same way if any part is PLA: E 2300 MPa,
   ν 0.35, 1240 kg/m³, yield 25 MPa. The creep warning still applies.
4. **Acceptance criteria (use for every study):**
   - Factor of safety ≥ **3** on the derated yield at the design load (FDM
     variability + creep), ≥ **1.5** at the 2× dynamic case.
   - Station deflection at the cable exit ≤ **0.5 mm** at the working load.

## Workflow that every study repeats

1. Open the assembly. **Exclude purchased parts** from analysis (motor,
   switch, servo, ESP32, battery): right-click in the Simulation tree under
   *Parts* → Exclude from Analysis. Replace each with the load it applies
   (remote mass or force on its mounting faces).
2. Simulation → **New Study → Static**. Name it after the load case
   (e.g. `Station_40N_down`).
3. **Apply material:** right-click *Parts* → Apply Material to All → PETG FDM
   (derated). Override any non-printed parts (steel axle: *Alloy Steel*).
4. **Connections:** the default global contact is *Bonded* (parts glued).
   Change it only where parts can separate or slide: right-click
   *Connections* → Contact Set → type **No Penetration** → select the two
   touching faces. Use it for the slide-in rails and gear teeth.
5. **Fixtures:** where the assembly is held (details per study).
6. **External loads:** forces, bearing loads, gravity, remote masses.
7. **Mesh:** right-click *Mesh* → Create Mesh → **Curvature-based**,
   start at the default size. Add **Mesh Control** (right-click Mesh) on the
   faces you care about (rail roots, gear tooth roots, fillets) at about 1/3
   of the global size.
8. **Run, then check convergence:** note the max stress at your critical
   feature; refine the mesh control by half and rerun. If the value changes
   < 10 %, it is converged. If it keeps climbing at a sharp internal corner,
   that is a singularity — add a real fillet in the model.
9. **Results to save** (right-click each plot → Save As image, for slides):
   von Mises stress (MPa), **Factor of Safety** (right-click Results →
   Define Factor of Safety Plot → *Max von Mises* → "Areas below factor of
   safety" = 3), Displacement URES (mm).
10. **Record** the numbers in `verification/simulation_results_gen2.md`
    (expected vs measured, pass/fail), same as the CAD reports.

To run the same model under several directions, right-click the study tab →
**Duplicate**, then edit only the load. (Simulation Premium's Load Case
Manager also works but is not required.)

---

## Study 1 — Wall station (frame + slide-in housing + shell)

**Assembly:** a sub-assembly with `Wall_Mount_v3`, `Slipin_mount_piece v3`,
`Shell_Casing`, `Spoolv3`, `Motor_Reference`. If only the full robot assembly
exists, make this sub-assembly first (Insert → Component → existing parts).

**Why it matters:** this is the load path that holds the robot up, and its
stiffness sets the anchor accuracy.

| Setting | Value | Source |
|---|---|---|
| Excluded | Motor_Reference, any switch | purchased |
| Motor weight | **Remote Mass** 0.28 kg (or weigh yours) on the motor-bolt faces | 42-38 motor |
| Spool | keep, PETG; or exclude and apply its load at the motor face | |
| Contact | **No Penetration** between housing rails and frame rails; Bonded elsewhere | slide-in interface |
| Retention | model the real pin/screw. Use Connectors → **Pin** for a pin, **Bolt** for a screw (housing to frame) | review R3 |
| Fixture | **Fixed Geometry** on the frame's screw-hole faces (cylindrical faces) + **Roller/Slider** on the frame's back face (it can press the wall but not pass through it). Better: Connectors → Bolt → *Foundation bolt* at each wall screw | wall + stud |  ⚠ *Superseded for the station mount by `docs/simulation/SW_STATIC_STATION_MOUNT.md`: a two-sided Roller/Slider gives a false answer when the line pulls the station away from the wall; use the one-sided Virtual Wall described there.*
| Line load | **Bearing Load** on the pulley/outlet axle hole (or **Force** on a split-line patch where the line leaves), magnitude below | review R6 |
| Gravity | Gravity, −Y (or whichever axis is down in your assembly) | |

**Load cases (duplicate the study for each direction):**

| Case | Line force | Direction from the cable exit |
|---|---|---|
| A | 32 N | straight down (claw close to the wall) |
| B | 32 N | 45° down, toward the room diagonal |
| C | 32 N | nearly horizontal toward the opposite corner (claw near the ceiling far away) |
| D | 64 N | worst of A–C × 2 (dynamic: jerk, snag) |

32 N is the equal-share tension 0.15 m below the anchors; the software
ceiling keeps operation below ~16 N, so 32 N is conservative.

**Read:** FoS ≥ 3 for A–C and ≥ 1.5 for D, especially at the rail roots and
around the wall screws. Displacement at the cable exit ≤ 0.5 mm for A–C. The
contact pressure plot on the rails (Results → List Contact/Friction Force)
tells you whether the line load **seats** the housing or pulls on the
retention: if the retention pin carries most of the force, the slide
direction is working against you.

## Study 2 — Spool on the shaft (quick check)

**Why:** confirms the shortened spool and its D-flat/set-screw hub survive the
torque, and gives the shaft-side load for the motor bearing.

| Setting | Value |
|---|---|
| Part | `Spoolv3` alone (Static study on the part) |
| Fixture | **Fixed Geometry** on the D-flat face + set-screw hole face (that is where torque is reacted) |
| Load | **Force** 32 N on a split-line strip on the drum surface, tangent to the drum, at the outermost layer radius (≈ 11.5–13 mm) |
| Case 2 | 64 N (dynamic) |
| Mesh control | flat, set-screw hole, flange-to-drum fillet |

**Read:** FoS will likely be high; the useful outputs are the stress at the
flat (where printed hubs crack) and the hub deflection.

## Study 3 — Gripper gear tooth (compare to the hand calculation)

**Why:** review R5 predicts SF ≈ 0.35–0.41 at servo stall for a module-1,
6 mm-face pinion. An FEA check that agrees with the Lewis equation is strong
evidence on slide 9 and backup B2.

| Setting | Value |
|---|---|
| Part | `Simple_18T_Pinionvlast` alone |
| Fixture | **Fixed Geometry** on the bore/spline faces (where the servo drives it) |
| Load face | Split Line on **one tooth flank, a thin band at the tip** (Lewis' worst case) |
| Load | **Force** normal to the flank. Magnitude = tangential force / cos(20°): F_t = 2·τ / d_pitch. For module 1: d = 18 mm, τ = 1.08 N·m (6 V stall) → F_t = 120 N → **128 N** normal. Recompute with your real module: d = 18 × m |
| Mesh control | the loaded tooth's root fillet, ~0.2 mm |

**Read:** max von Mises at the root fillet vs Lewis (55–65 MPa for module 1).
FEA should land within ~±30 % of Lewis. Then repeat on `06_compound_54T_24T`
for the 24T section (same torque × 3 is carried by the shaft; the 24T sees
F_t = 2·(3·τ·η)/(24·m)). If the pinion fails, the fix options are in the
review (module ≥ 2, face ≥ 10 mm, metal pinion, or torque-limited closing).

Full meshing contact (two gears touching) is possible with No Penetration
contact, but it is slow and sensitive. The single-tooth study is the standard
first check.

## Study 4 — Jaws and gear housing at stall

**Why:** when the clamp closes on cloth the servo stalls, so stall torque
loads the jaws, pivots and housing every grab.

| Setting | Value |
|---|---|
| Assembly | V5 `LaundryGripperAssem1` with jaws, gear housing, compound and follower gears |
| Excluded | servo, ESP32, battery, camera → **Remote Mass** each on its mount faces |
| Contact | Bonded between gears (locks the train, approximates stall) |
| Fixture | **Fixed Geometry** on the gear housing's mounting faces to the extension |
| Load | **Force 24 N** at each jaw's grip pad, normal to the pad, pointing outward (the reaction of the jaws squeezing cloth). This is the 6 V stall torque × 3 × 0.95² split between jaws at a 60 mm arm; scale by 60 / (your arm length in mm) |
| Mesh control | jaw pivot bosses, gear-housing bearing bores |

**Read:** FoS ≥ 3 at pivots and housing bores; jaw-tip deflection (a soft jaw
loses grip force).

## Study 5 — Whole claw hanging from four cables

**Why:** checks the electronics housing, the extension ("Griper Cylinder")
and the cable tie-off points carrying the claw and a 1 lb load.

| Setting | Value |
|---|---|
| Assembly | V5 claw, complete |
| Excluded | servo, ESP32, battery, camera → **Remote Mass** (weigh them; total claw ≈ 0.45 kg assumed) |
| Fixture | **Fixed Hinge** (or Fixed Geometry) on the four cable tie-off holes |
| Loads | **Gravity**; **Force 4.45 N** (1 lb) at the jaw pads; Case 2: both × 2 (17.7 N total) |
| Side case | add **0.5 × g lateral** to gravity (Gravity can take a tilted direction) for swing |
| Mesh control | extension-to-housing joint, tie-off holes |

**Read:** FoS ≥ 3, with the extension's root the usual weak spot in bending.
Also report the vertical deflection at the jaws.

## Results table to fill (save as `verification/simulation_results_gen2.md`)

| Study / case | Max von Mises (MPa) | Location | Min FoS | Max displacement (mm) | Criterion | Pass? |
|---|---|---|---|---|---|---|
| 1A station 32 N down | | | | | FoS ≥ 3, exit ≤ 0.5 mm | |
| 1B station 32 N 45° | | | | | | |
| 1C station 32 N horizontal | | | | | | |
| 1D station 64 N | | | | | FoS ≥ 1.5 | |
| 2 spool 32 / 64 N | | | | | FoS ≥ 3 / 1.5 | |
| 3 pinion tooth 128 N | | | | | compare Lewis | |
| 4 jaws at stall | | | | | FoS ≥ 3 | |
| 5 claw hanging ×1 / ×2 | | | | | FoS ≥ 3 / 1.5 | |
