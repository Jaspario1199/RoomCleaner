# Study C: steady-state thermal of the winch motor in the station assembly at 1.5 A

SolidWorks Simulation walkthrough for Jasper (lead, 2026-10-22). It builds on Study B
([`SW_THERMAL_HEAT_FIN.md`](SW_THERMAL_HEAT_FIN.md): the fin alone at 1.06 A). Study C runs on **your own 10/21 assembly**
(`Assem_laundry_v3`) with the motor, heat fin and slip-in mount together, at the **D37 current of 1.5 A**.
Its target numbers come from `calculations/thermal_assembly_1p5a.py`: the same network and fin model as Study B, run at 1.5 A.

**What it answers.**
1. How hot does the motor run at 1.5 A?
2. How hot is the **PETG of the slip-in mount** where it touches the fin and the motor? This is the loaded printed part that
   the 60 °C limit is for. The hand calculation cannot give this number; this study can.
3. How much of the heat leaves through the fin?

**Time:** about 1.5 hours the first time: preparation 20 min, setup 30 min, mesh and run 10 min, results 20 min, variants 15 min.

**Licence.** A thermal study needs SOLIDWORKS Simulation **Professional** or **Premium**. Check that *Thermal* appears
under New Study before you start.

---

## 0. The answer sheet (what SolidWorks should land on)

Conditions:
- 1.5 A, so the motor makes 4.05 W (I² R, with 1.8 Ω per phase **assumed**);
- room air 23 °C;
- vented shell, with the inside air at 27 °C;
- 6061 fin as built (0.483 mm), thermal paste between the motor and the fin.

All values are CALCULATED. Each range runs from "heat spread evenly over the fin patch" to "flange at one temperature".
The steel motor block in the FEA is close to the second case, so expect the **lower motor temperature and the higher fin heat**.

| Output | Painted fin | Bare fin |
|---|---|---|
| **Motor block, mean** | **55.9 to 58.8 °C** | 59.5 to 61.6 °C |
| **Heat carried by the fin** | **1.41 to 1.63 W** (35 to 40 % of 4.05 W) | 1.20 to 1.36 W |
| Fin, 50 mm above the shell exit (rise over room air) | 12.1 to 13.7 K | 17.8 to 19.7 K |
| Fin tip (rise over room air) | 2.5 to 2.8 K | 6.7 to 7.2 K |
| **PETG slip-in face against the fin** | expect 1 to 3 K below the motor block: **about 53 to 58 °C** (new output) | about 57 to 61 °C |

Other cases:

| Case | Motor temperature |
|---|---|
| Sealed shell, painted fin (inside air 36 °C) | 63.5 to 67.8 °C |
| No fin, vented | 77.1 °C |
| No fin, sealed | 99.1 °C |
| 1.35 A (3.28 W), painted, vented | 49.9 to 52.2 °C |
| 1.06 A (2.02 W), painted, vented | 40.1 to 41.5 °C |

**Pass for the model:**
- the energy balance closes: the heat leaving through all convection faces equals 4.05 W within 1 %;
- the motor block lands within about ±3 K of the painted range;
- the fin heat lands within about ±20 % of its range.

**Pass for the design:** the PETG face is **under 60 °C** with margin. If it is above about 55 °C, the hold test decides
(section 8). The fallback is 1.35 A, and the fin must be painted.

---

## 1. Inputs, with where each one comes from

| Input | Value | Source / status |
|---|---|---|
| Motor heat | **4.05 W** = 1.5² × 1.8 | D37 (1.5 A); 1.8 Ω per phase **ASSUMED**. Measure one phase with a meter: the heat scales with R |
| Room air | 23 °C | Study B; use your measured air temperature on the day and compare rises |
| Shell inside air | **27 °C vented, 36 °C sealed** | network at 1.5 A: room + R_sa × (motor heat into the air + 1.5 W of electronics) |
| Motor faces to the shell air | **h = 10.1 W/m²K vented, 8.7 sealed** | the repo's R_ma (12 or 14 K/W) spread over the motor's 8,219 mm² of free faces |
| Fin outside the shell (convection + radiation) | **h = 9.2 W/m²K painted, 4.8 bare**, to 23 °C | converged for the heat the fin carries at 1.5 A (`thermal_assembly_1p5a.py`) |
| Fin inside the shell | h = 4 W/m²K, to the shell air (27 °C) | Study B, ASSUMED |
| PETG slip-in, free faces | h = 5 W/m²K, to 27 °C | ASSUMED (warm side); the result barely depends on it because PETG conducts poorly |
| Motor block material | Alloy Steel (k about 50 W/m·K) | Study B, B-2 |
| Fin conductivity | **40.3 W/m·K** (see 2.3) | 6061 k 167 × 0.483 mm built ÷ 2.0 mm in your CAD |
| PETG conductivity | **0.20 W/m·K** solid; 0.12 for infill sensitivity | typical datasheet range 0.19 to 0.24, ASSUMED |
| Contact, motor to fin | thermal resistance 1.0 × 10⁻⁴ K·m²/W (paste); 3.3 × 10⁻⁴ dry | Study B, section 1.2 |
| Contact, fin and motor to PETG | Bonded (no resistance) | conservative: it puts the most heat into the PETG |

---

## 2. Prepare the assembly (20 minutes)

### 2.1 Work on a copy

1. Open `Assem_laundry_v3` (the 10/21 assembly).
2. Use **File → Save As → Save as copy and open**, name `Assem_thermal_C`. That way nothing in the real assembly changes.

### 2.2 Choose the bodies

Study C-1 needs only three parts:
- **Motor_Reference**: the block and its shaft;
- **Heat_horn**: the fin;
- **Slipin_mount_piecev3**: the PETG mount the motor and fin bolt to.

Leave the other parts in the assembly. In the Simulation tree, right-click each one and choose **Exclude from Analysis**:
- **Shell_Casing**: the fin passes through its slot with a 0.69 mm gap and does not touch it. Its effect is the shell-air
  temperature, which you enter as a number.
- **Spool1011**;
- **Wall_Mount_v3**: heat into it has to cross the PETG first, which is negligible; leaving it out is slightly conservative;
- the encoder parts and any screws.

Check that the three remaining parts touch:
- Run **Tools → Evaluate → Interference Detection** on them. You want **no interference**.
- Then check the touching faces:
  - the motor's front face against the fin's back face (0.000 mm in the STEP);
  - the fin's front face against the slip-in plate (about 1,300 mm² of contact);
  - the motor against the slip-in.
- **Bonded contact only conducts across faces that touch.** A gap means no heat path.

### 2.3 The fin: CAD thickness versus as built

Your Heat_horn is drawn **2.0 mm** thick; the built fin is 0.019 in (**0.483 mm**). Steady conduction along a thin fin depends
only on k × t. So instead of editing the geometry, give the 2 mm CAD fin an **equivalent conductivity**:
- k = 167 × 0.483 / 2.0 = **40.3 W/m·K**.

It then conducts like the real 6061 sheet. The resistance through its thickness is still negligible: 0.04 K/W.
- If you ever change the drawn thickness, use k = 167 × 0.483 / t_CAD.
- For the 1/8 in comparison, use k = 167 × 3.175 / 2.0 = 265 W/m·K. That is not a real aluminium value; it is just the
  equivalent for the thicker sheet.

Your CAD fin is 42 mm wide with 176 mm above the shell; the built one is 44 × 200. That is worth only about 1 K/W
(19.7 against 18.7 K/W), so the motor runs about 0.5 K warmer. Ignore it.

### 2.4 Split the fin faces where it leaves the shell (5 minutes)

The fin needs two convection zones: inside the shell (h 4, at 27 °C) and outside (h 9.2, at 23 °C). In your CAD the fin
leaves the shell top **53 mm above the fin's bottom edge**. That is z = 34.6 mm in the station frame; the motor axis is
21 mm above the bottom edge.

1. Open **Heat_horn** (right-click → Open Part).
2. Sketch on its large front face. Draw a horizontal line across the full width, **53.0 mm above the bottom edge**.
   - Or use Convert Entities on the shell slot's top edge in the assembly, if you prefer to follow the CAD exactly.
3. Use **Insert → Curve → Split Line**, type **Projection**. Select both large faces (front and back), and untick
   *Single direction* or do the back face separately.
4. Optional: a second line **50 mm above the first** (103 mm above the bottom edge). That is where the thermocouple TC2
   goes in the hold test, and the probe in section 6.
5. Save and return to the assembly.

The split lines do not change the part, so they are harmless in the real assembly too.

---

## 3. Study setup (30 minutes)

1. Turn on **Tools → Add-Ins → SOLIDWORKS Simulation**.
2. Open **Simulation → Options → Default Options → Units**. Set Temperature to **Celsius** and Length to **mm**.
3. Choose **Simulation tab → New Study → Thermal**, and name it `C1_1p5A_vented_paint`.
4. Right-click the study → **Properties**:
   - Solution type: **Steady state**;
   - Solver: Automatic (or FFEPlus).

### 3.1 Materials

In the Simulation tree, use the Parts folder. Right-click each part → **Apply/Edit Material**. Steady state needs only the
thermal conductivity; the density and specific heat matter only for the transient in section 7.

| Part | Material | k (W/m·K) | Density, specific heat (transient only) |
|---|---|---|---|
| Motor_Reference (block and shaft) | Custom "Motor block": copy **Alloy Steel**, keep k 50 | 50 | density **4100 kg/m³** (so the block weighs about 280 g, like a real NEMA 17), cp 460 J/kg·K |
| Heat_horn | Custom "Fin 6061 as built (equivalent)" | **40.3** | density **652 kg/m³** (keeps the real fin's mass), cp 896 |
| Slipin_mount_piecev3 | Custom "PETG printed" | **0.20** | 1270 kg/m³, cp 1200 |

### 3.2 Connections

1. Right-click **Connections → Component Contact** (or open Global Contact). Set it to **Bonded**. Every touching face pair
   now conducts perfectly.
2. Right-click **Connections → Contact Set**:
   - Type: **Thermal Resistance**, *Distributed*.
   - Set 1: the motor's **front face** and the fin's **back face**.
   - Value: **1.0e-4 K·m²/W** for thermal paste, or 3.3e-4 for a dry contact.
   - In some releases, *Total* asks for K/W instead: use 0.074 K/W for paste.
   - Leave the fin to PETG and motor to PETG contacts as Bonded.

### 3.3 Thermal loads

Right-click **Thermal Loads**:

| Load | Select | Value |
|---|---|---|
| **Heat Power** `Q_motor` | the **motor block body** | **4.05 W** |
| **Convection** `H_motor_air` | the motor's free faces (see below) | **h 10.1 W/m²K**, bulk ambient **27 °C** |
| **Convection** `H_fin_out` | the fin faces **above** the split line, front and back (two faces each if you made the TC2 line) | **h 9.2 W/m²K** (painted), bulk ambient **23 °C** |
| **Convection** `H_fin_in` | the fin faces **below** the split line that do **not** touch the motor or the PETG, front and back | **h 4 W/m²K**, bulk ambient **27 °C** |
| **Convection** `H_petg` | the slip-in's free faces: the motor-plate region, plus its outer faces if quick to select | **h 5 W/m²K**, bulk ambient **27 °C** |
| Edges of the fin, the slip-in's faces against the wall mount | leave unloaded (insulated) | |

**Heat Power:**
- Put it on the motor block only. The shaft is 0.6 % of the volume, so selecting the whole component is fine too.
- If the Heat Power dialog gives a choice between total and per entity, choose total, so that 4.05 W is the sum.

**Motor free faces:**
- Use the four sides and the back face of the block: the faces that do not touch the fin or the slip-in.
- If a side face touches the slip-in pocket, leave that face out; the bonded contact carries its heat instead.

**Radiation:** it is already folded into the fin's 9.2 W/m²K. Do **not** add a Radiation load as well, or you count it twice.

---

## 4. Mesh and run (10 minutes)

1. Right-click **Mesh → Create Mesh**: **Blended curvature-based**, maximum element size **5 mm**, minimum **1 mm**.
2. Right-click **Mesh → Apply Mesh Control** on the Heat_horn: element size **1 mm**. That puts two elements through the
   2 mm fin.
3. Mesh. Expect about 150 to 300 k elements; the slip-in is the big part. If meshing fails on the slip-in, raise its size to
   6 mm or use a mesh control of 3 mm on it.
4. Click **Run This Study**. Steady thermal is linear, so it takes about a minute.

---

## 5. Check the run first

1. **Energy balance.** Right-click **Results → List Heat Power**. In some releases it sits under List Result Force →
   Heat Power, or is called Net Heat Power. Select all the faces that carry a convection load.
   - The total should be **4.05 W** within 1 %.
   - Expect roughly 2.4 to 2.6 W from the motor faces, 1.4 to 1.6 W from the fin, and a few hundredths of a watt from the PETG.
2. **Temperature plot.** Open **Results → Thermal1**. Right-click → Edit Definition → Celsius, and set the legend to
   **23 to 65 °C**. The motor should be the hottest body. The fin cools steadily from the motor patch to the tip.
   The PETG should be hot only right around the motor plate.

If the balance does not close, check in this order:
- the heat power value and where it is applied;
- whether any convection face set is missing, such as the back face of the fin;
- whether a face has two convection loads, so it is counted twice.

---

## 6. Outputs to record

Right-click Thermal1 → **Probe** → *On selected entities*. It shows the minimum, maximum and average for a face.

| Output | Probe | FEA | Target (painted, vented) |
|---|---|---|---|
| **Motor block mean** | average over the block's faces, or one probe mid-block | | **55.9 to 58.8 °C** |
| Motor face against the fin | the motor front face, average | | about the motor mean, minus less than 1 K |
| **PETG maximum** | the slip-in faces touching the fin and the motor: **maximum** | | **about 53 to 58 °C; must be under 60** |
| PETG, 10 mm away from the motor plate | any slip-in face 10 mm from the contact | | well below the maximum: PETG insulates |
| Fin at the shell exit | the split line, centre | | |
| **Fin, 50 mm above the shell exit (TC2 line)** | the second split line, centre | | rise **12.1 to 13.7 K** (35 to 37 °C) |
| Fin tip | the top edge | | rise 2.5 to 2.8 K (about 26 °C) |
| **Heat through the fin** | List Heat Power on the fin's convection faces (`H_fin_out` + `H_fin_in`) | | **1.41 to 1.63 W** |

Save plots for the deck:
- `C_temp_assembly.png`: Thermal1, legend 23 to 65 °C, isometric, with the motor, fin and slip-in visible;
- `C_temp_section.png`: a section through the motor axis, showing the heat path into the fin and the PETG;
- `C_heatflux.png`: a Heat Flux plot (Resultant), showing where the heat leaves.

---

## 7. Variants (15 minutes; duplicate the study and change one thing each time)

| Study | Change | Expected motor temperature |
|---|---|---|
| `C2_sealed` | `H_motor_air` h **8.7**, bulk **36 °C**; `H_fin_in` and `H_petg` bulk **36 °C** | 63.5 to 67.8 °C (PETG likely **above 60**: this is why the shells stay vented) |
| `C3_bare_fin` | `H_fin_out` h **4.8** | 59.5 to 61.6 °C (paint matters at 1.5 A) |
| `C4_1p35A` | Heat Power **3.28 W** (1.35² × 1.8) | 49.9 to 52.2 °C |
| `C5_no_fin` | Exclude Heat_horn from analysis; move the motor-to-plate contact to the slip-in; motor faces only | about 77 °C |
| `C6_PETG_infill` | PETG k **0.12** | almost no change in the motor; the PETG gets slightly hotter right at the contact |
| `C7_transient` (optional) | Properties → **Transient**: total time **5400 s**, step **60 s**; initial temperature 23 °C on all bodies (Thermal Loads → Temperature → Initial temperature) | about 94 % of the steady rise at 60 minutes. Compare with the hold-test log, minute by minute |

---

## 8. What makes it true: the hold test

The FEA is SIMULATED, with inputs that are partly assumed: coil resistance, h, and the shell air. The 90-minute hold test
turns it into MEASURED.

**Setup:**
- one station at 1.5 A, shell closed as installed (vented), fin on with paste, motor holding;
- the A4988 does not reduce current when the motor stands still;
- thermocouples or an IR thermometer, logged every minute.

| Point | Prediction (steady; × 0.94 at 60 min) |
|---|---|
| TC1 motor case, next to the fin | 55.9 to 58.8 °C painted (rise 33 to 36 K over 23 °C) |
| TC2 fin, 50 mm above the shell exit | rise 12.1 to 13.7 K painted, 17.8 to 19.7 K bare |
| PETG next to the motor plate (IR) | under 60 °C |
| **A4988 chip or heatsink** | not modelled. If its heatsink is above about 70 °C, drop to 1.35 A (D29 rule). If it overheats, the driver shuts off and the winch loses torque |

**If the test disagrees,** change the inputs, not the physics:
- **TC1 high but TC2 on target:** more motor heat (measure R; heat scales with it) or a higher R_ma. Fit the motor h.
- **TC2 off:** fit the fin's h.

Record the fitted values in `DESIGN_STATE.md`. The measured curve then replaces the model on the slide.

---

## 9. What this study cannot tell you

- **The shell air temperature.** It is an input (27 °C vented) from the network, not computed.
  - SOLIDWORKS **Flow Simulation** (a separate add-in) can compute it with conjugate natural convection. If you have it, the
    short version is:
    - internal and external analysis, gravity along −z, ambient 23 °C;
    - solids conduction on, radiation on;
    - a 4.05 W volume heat source in the motor, plus 1.5 W in the electronics region;
    - the real shell with its vents.
  - It is optional, and much slower to set up.
- **The coil hot spot.** The winding sits about 3 to 6 K/W above the case. The PETG sees the case, so the 60 °C limit is
  checked on the case.
- **The driver,** the buck and the ESP32. Their 1.5 W is lumped into the shell air.
- **Draughts and the ceiling hot layer.** Still air is assumed; a fan lowers everything, and a hot ceiling layer raises the
  top of the fin.
- **Contact quality.** A bowed fin with no paste adds 0 to 1 K (Study B, section 1.2).

---

## 10. Troubleshooting

| Symptom | Cause and cure |
|---|---|
| Motor at hundreds of °C | Heat power on a tiny face instead of the body, or no convection on the motor; check the balance in section 5 |
| Fin uniformly at the motor temperature | No convection on the fin, or the convection was put on one face only |
| PETG at the motor temperature everywhere | PETG k entered as 0.2 in the wrong units (W/mm·K), or the PETG was given steel by default |
| "Bodies are not in contact" or no heat in the fin | Gap between the motor and the fin in the copy; check Interference Detection and Clearance; mate the faces coincident |
| Mesh fails | Raise the global size, add a 1 mm control on the fin only, or simplify the slip-in fillets in the copy |
| Results in K | Edit the plot definition to Celsius; compare rises, not absolute values |

---

## 11. Results template (paste into `verification/simulation_results_motor_assembly.md`)

```
Study C, motor in the station assembly. Run by ____  Date ____  SolidWorks release ____  Evidence: SIMULATED
Current 1.5 A, heat power ____ W (4.05 with R 1.8 ohm; measured R ____)  Room ____ C  Shell air ____ C  Vented / sealed
Fin: k_eq ____ (40.3), h_out ____ (9.2 painted / 4.8 bare), h_in 4   Motor h ____ (10.1)   PETG k ____ (0.20)   Contact ____ (1e-4 paste)
Mesh ____ elements   Energy balance ____ W of ____ W (within 1 %?)
Motor block mean ____ C (55.9-58.8)   PETG max ____ C (about 53-58, < 60)   Fin heat ____ W (1.41-1.63)
Fin 50 mm above exit ____ K rise (12.1-13.7)   Tip ____ K (2.5-2.8)
Variants: sealed ____ C (63.5-67.8), bare ____ C (59.5-61.6), 1.35 A ____ C (49.9-52.2), no fin ____ C (about 77)
Hold test: TC1 ____ C, TC2 ____ K, PETG ____ C, A4988 heatsink ____ C at ____ min
Plots saved: C_temp_assembly.png, C_temp_section.png, C_heatflux.png
Findings: ____
```

*Links:* [Study B, fin alone](SW_THERMAL_HEAT_FIN.md) · [answer-sheet script](../../calculations/thermal_assembly_1p5a.py) ·
[network and fin model](../../calculations/simulation_loads.py) · D37 in [DECISIONS.md](../../DECISIONS.md).
