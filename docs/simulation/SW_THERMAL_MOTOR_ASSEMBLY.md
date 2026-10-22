# Study C: steady-state thermal of the winch motor in the station assembly at 1.5 A

SolidWorks Simulation walkthrough for Jasper (lead, 2026-10-22). It builds on Study B
([`SW_THERMAL_HEAT_FIN.md`](SW_THERMAL_HEAT_FIN.md): the fin alone at 1.06 A). Study C runs on **your own 10/21 assembly**
(`Assem_laundry_v3`) with the motor, heat fin and slip-in mount together, at the **D37 current of 1.5 A**.
Its target numbers come from `calculations/thermal_assembly_1p5a.py`: the same network and fin model as Study B, run at 1.5 A.
That network has no heat path through the PETG and uses the as-built fin. Section 0 therefore also gives the numbers for **your CAD
model** (CAD fin, PETG bonded and loaded), from an independent 3-D conduction check
([`verification/thermal_assembly_1p5a_check.md`](../../verification/thermal_assembly_1p5a_check.md)).

**What it answers.**
1. How hot does the motor run at 1.5 A?
2. How hot is the **PETG of the slip-in mount** where it touches the fin and the motor? This is the loaded printed part that
   the 60 °C limit is for. The hand calculation cannot give this number; this study can.
3. How much of the heat leaves through the fin, and how much through the PETG deck?

**Time:** about 1.5 hours the first time: preparation 20 min, setup 30 min, mesh and run 10 min, results 20 min, variants 15 min.

**Licence.** A thermal study needs SOLIDWORKS Simulation **Professional** or **Premium**. Check that *Thermal* appears
under New Study before you start.

---

## 0. The answer sheet (what SolidWorks should land on)

Conditions:
- 1.5 A, so the motor makes 4.05 W (I² R, with 1.8 Ω per phase **assumed**);
- room air 23 °C;
- vented shell, with the inside air at 27 °C;
- 6061 fin (0.483 mm as built; k_eq 40.3 in your 2 mm CAD fin), thermal paste between the motor and the fin;
- **load set A of section 3.3**: h 10.1 on the motor's 6,612 mm² of free faces, `H_petg` on, the PETG bonded to the motor and the fin.

There are two layers of numbers. All are CALCULATED.
- **Network** (the script): the as-built fin, 44 × 200 mm. The network has **no PETG heat path**. Each range runs from "heat spread
  evenly over the fin patch" to "flange at one temperature".
- **3-D check** (your CAD model, set A): the CAD fin, 42 × 228.6 mm, with the PETG bonded and loaded. Its PETG heat is good to about ±20 %.

The steel motor block is **not simply** at the isothermal (lower) end. With the PETG insulated and R_ma kept at 12 K/W, the 3-D check
gives 57.7 °C and 1.50 W of fin heat: mid-range of the CAD-fin network values (56.6 to 59.4 °C, 1.36 to 1.58 W). Do not count on the lower end.

**Network values** (as-built fin, no PETG path):

| Output | Painted fin | Bare fin |
|---|---|---|
| **Motor block, mean** | **55.9 to 58.8 °C** | 59.5 to 61.6 °C |
| **Heat carried by the fin** | **1.41 to 1.63 W** (35 to 40 % of 4.05 W) | 1.20 to 1.36 W |
| Fin, 50 mm above the shell exit (rise over room air) | 12.1 to 13.7 K | 17.8 to 19.7 K |
| Fin tip (rise over room air) | 2.5 to 2.8 K | 6.7 to 7.2 K |

**Your CAD model.** The CAD fin is 42 × 228.6 mm with 179 mm above the shell exit; the as-built fin is 44 × 200 mm. Use these targets for the
study you run:

| Output | Painted fin | Bare fin |
|---|---|---|
| Motor block, mean: network with the CAD fin | 56.6 to 59.4 °C (**+0.8 K** on the as-built fin) | 59.9 to 62.0 °C |
| **Motor block, mean: 3-D, load set A** | **55 to 56.5 °C** | about 58 °C |
| **Heat carried by the fin** | **1.36 to 1.58 W** (network); 1.4 W (3-D) | 1.14 W (3-D); as-built network 1.20 to 1.36 W |
| Fin, 50 mm above the shell exit (rise) | 11.9 to 13.5 K (network); 12.5 to 13.5 K (3-D) | as-built network 17.8 to 19.7 K (CAD fin not run) |
| **Fin tip (rise)** | **3.4 to 4.5 K** (network 3.4 to 3.8; 3-D 4.4) | **8 to 10 K** (network 8.2 to 8.9; 3-D 9.9) |
| **PETG slip-in maximum** | **about equal to the motor mean** (within 0.2 K): 55 to 59 °C (CAD fin 56 to 60) | 59 to 62 °C (network); 3-D set A about 58 °C |
| PETG face against the fin | 0.5 to 1.2 K below the motor mean | the same |
| Motor face against the fin | about 0.4 K below the block mean | the same |
| Heat split: motor faces / fin / PETG | **about 1.9 / 1.4 / 0.75 W** (fin 1.29 outside + 0.10 inside the shell) | 2.08 / 1.14 / 0.83 W |

Other cases:

| Case | Motor temperature (network) | 3-D check (set A, CAD fin) |
|---|---|---|
| Sealed shell, painted fin (inside air 36 °C) | 63.5 to 67.8 °C | 63.5 °C; PETG also 63.5 °C |
| No fin, vented | 77.1 °C | about 69 °C with the motor on the plate; PETG takes 1.20 W |
| No fin, sealed | 99.1 °C | not run |
| 1.35 A (3.28 W), painted, vented | 49.9 to 52.2 °C | not run |
| 1.06 A (2.02 W), painted, vented | 40.1 to 41.5 °C | not run |

**Pass for the model:**
- the energy balance closes: the heat leaving through all convection faces equals 4.05 W within 1 %;
- the split is about 1.9 W through the motor faces, 1.4 W through the fin and 0.75 W through the PETG (PETG 0.6 to 0.9 W);
- the motor block lands within about ±3 K of the value for the load set you used: **55 to 56.5 °C for set A** (sets B to D are in section 3.3);
- the fin heat lands within about ±20 % of 1.36 to 1.58 W;
- the PETG maximum lands within about 1 K of the motor mean, and the PETG face against the fin is 0.5 to 1.2 K lower.

**Pass for the design:** the PETG maximum is **under 60 °C**. The margin is **0.4 to 4.7 K with the painted fin, and none with a bare fin**
(59 to 62 °C). If it is above about 55 °C, the hold test decides (section 8). The fallback is 1.35 A, and the fin must be painted.
About 20 cm³ of the PETG sits above 50 °C, so check the hot-tab creep too, not only the 60 °C face (section 6).

---

## 1. Inputs, with where each one comes from

| Input | Value | Source / status |
|---|---|---|
| Motor heat | **4.05 W** = 1.5² × 1.8 | D37 (1.5 A); 1.8 Ω per phase **ASSUMED**. Measure one phase with a meter: the heat scales with R |
| Room air | 23 °C | Study B; use your measured air temperature on the day and compare rises |
| Shell inside air | **27 °C vented, 36 °C sealed** | network at 1.5 A: room + R_sa × (motor heat into the air + 1.5 W of electronics) |
| Motor faces to the shell air | **h = 10.1 W/m²K vented, 8.7 sealed**, on the block's **6,612 mm²** of free faces | the script spreads the repo's R_ma (12 or 14 K/W) over 8,219 mm² (four sides + back). In your CAD the −x side (1,607 mm²) is bonded to the PETG deck, so that area no longer applies; see 3.3 |
| Fin outside the shell (convection + radiation) | **h = 9.2 W/m²K painted, 4.8 bare**, to 23 °C | converged for the heat the fin carries at 1.5 A (`thermal_assembly_1p5a.py`) |
| Fin inside the shell | h = 4 W/m²K, to the shell air (27 °C) | Study B, ASSUMED |
| PETG slip-in, free faces | h = 5 W/m²K, to 27 °C | ASSUMED (warm side). **Required:** the bonded deck carries about 0.75 W to the air, and leaving this load out raises the motor by about 7 K (to 62 °C). Loading only the faces within 30 mm of the motor is enough (it changes the motor by only +0.2 K) |
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
- **Shell_Casing**: the fin passes through its slot and does not touch it. The gap is **0.69 mm on the motor side and 2.31 mm on
  the spool side** (slot walls at y −2.69 and +2.31, fin at y −2 to 0). Its effect is the shell-air temperature, which you enter
  as a number.
- **Spool1011**;
- **Wall_Mount_v3**: heat into it has to cross the PETG first, which is negligible; leaving it out is slightly conservative;
- the encoder parts and any screws.

Check that the three remaining parts touch:
- Run **Tools → Evaluate → Interference Detection** on them. You want **no interference**.
- Then check the touching faces:
  - the motor's front face against the fin's back face (0.000 mm in the STEP; 1,300.5 mm² of contact);
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

Your CAD fin is 42 mm wide and 228.6 mm tall, with 179 mm above the shell exit; the built one is 44 × 200. That is worth about
1 K/W (19.7 against 18.7 K/W). The motor therefore runs **about 0.8 K warmer**, and the fin tip rises 1 K or more (3.4 to 3.8 K
painted against 2.5 to 2.8 K). Use the CAD-fin targets of section 0, not the as-built ones.

The 2 mm CAD fin has one more side effect. A **Heat Flux plot** (`C_heatflux.png`) shows k_eq × gradient, which is about 4 times lower
than the real 0.483 mm fin's flux density. The integrated heat is right; read the plot for where the heat goes, not for its size.

### 2.4 Split the fin faces where it leaves the shell (5 minutes)

The fin needs two convection zones: inside the shell (h 4, at 27 °C) and outside (h 9.2, at 23 °C). In your CAD the fin
leaves the shell roof plate **49.5 mm above the fin's bottom edge**. That is z = 31.16 mm in the station frame: the roof plate at
the slot is z 27.84 to 31.16 mm (3.3 mm thick). The motor axis is 21 mm above the bottom edge (the station-frame origin is
2.64 mm below the true shaft axis, which is at z 2.64).

1. Open **Heat_horn** (right-click → Open Part).
2. Sketch on its large front face. Draw a horizontal line across the full width, **49.5 mm above the bottom edge**.
   - Or use Convert Entities on the top edge of the shell's roof plate at the slot (z 31.16); it gives the same line.
3. Use **Insert → Curve → Split Line**, type **Projection**. Select both large faces (front and back), and untick
   *Single direction* or do the back face separately.
4. Optional: a second line **50 mm above the first** (99.5 mm above the bottom edge). That is where the thermocouple TC2
   goes in the hold test, and the probe in section 6.
5. Save and return to the assembly.

The split lines do not change the part, so they are harmless in the real assembly too.

**The funnel around the slot.** The shell roof rises around the slot in a funnel: z 33 at 6 mm from the fin, z 36 to 37 at 9 mm,
and z 70.8 beyond 10 mm. The hottest 40 mm of the exposed fin therefore sits in a V-notch, where the unconfined h 9.2 may be too
high. This is UNRESOLVED; the hold test decides. The exit height itself changes the results by under 0.4 K and under 0.05 W.

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
   - In some releases, *Total* asks for K/W instead: use **0.077 K/W** for paste (1.0e-4 ÷ the 1,300.5 mm² contact). The script's 0.074 K/W
     uses a 1,359 mm² model patch; the difference is under 0.01 K.
   - Leave the fin to PETG and motor to PETG contacts as Bonded.

### 3.3 Thermal loads

Right-click **Thermal Loads**:

| Load | Select | Value |
|---|---|---|
| **Heat Power** `Q_motor` | the **motor block body** | **4.05 W** |
| **Convection** `H_motor_air` | the motor's free faces: **6,612 mm²** (see below) | **h 10.1 W/m²K**, bulk ambient **27 °C** |
| **Convection** `H_fin_out` | the fin faces **above** the split line, front and back (two faces each if you made the TC2 line) | **h 9.2 W/m²K** (painted), bulk ambient **23 °C** |
| **Convection** `H_fin_in` | the fin faces **below** the split line that do **not** touch the motor or the PETG, front and back | **h 4 W/m²K**, bulk ambient **27 °C** |
| **Convection** `H_petg` | the slip-in's free faces: the motor-plate region, plus its outer faces if quick to select. **Do not leave this load out** | **h 5 W/m²K**, bulk ambient **27 °C** |
| Edges of the fin, the slip-in's faces against the wall mount | leave unloaded (insulated) | |

**Heat Power:**
- Put it on the motor block only. The shaft is 0.6 % of the volume, so selecting the whole component is fine too.
- If the Heat Power dialog gives a choice between total and per entity, choose total, so that 4.05 W is the sum.

**Motor free faces:**
- Use the four sides and the back face of the block, **less the −x side** (1,607 mm²), which is bonded to the PETG deck: **6,612 mm²**.
- If any other side face touches the slip-in pocket, leave that face out too; the bonded contact carries its heat instead.
- The script's h 10.1 is R_ma = 12 K/W spread over 8,219 mm² (four sides + back). It no longer applies to that area. On 6,612 mm² the
  air path is G = 0.067 W/K (**14.9 K/W**, not 12). That is intended: the bonded PETG deck carries the rest.

**One load set.** The motor temperature depends on how you choose the faces, so use **set A** and do not mix sets (3-D check, painted
fin, vented, CAD fin, 4.05 W):

| Set | Motor free faces | PETG | Motor mean | PETG heat |
|---|---|---|---|---|
| **A: use this one** | h 10.1 on 6,612 mm² (air path 14.9 K/W) | `H_petg` on, bonded | **55 to 56.5 °C** (55.3; 56.4 at PETG k 0.12) | **0.7 to 0.8 W** (0.64 W at k 0.12) |
| B | h 12.57 on 6,612 mm² (R_ma kept at 12 K/W) | `H_petg` on, bonded | 52.3 °C | 0.68 W |
| C | h 12.57 on 6,612 mm² (R_ma kept) | `H_petg` left out | 57.7 °C (the network: 56.6 to 59.4 °C) | 0 |
| D | h 10.1 on 6,612 mm² | `H_petg` left out | **62.1 °C** | 0 |

**The R_ma double count.** In `gen2_motor_thermal.py` R_ma is the path from the motor case to the shell interior: air **and the PETG
housing** together. So the PETG path is already inside the 12 K/W.
- Once the PETG deck is modelled and loaded, its path must not also sit in the motor-air path. Set B keeps 12 K/W on the air faces and
  lets the PETG conduct as well, so it counts the PETG path twice: 3 K cooler than set A.
- Set A puts 10.1 on the real free area and lets the bonded PETG carry its own heat. Set C is the network exactly, with the PETG as
  an insulator.
- Set D is the mistake to avoid. It has no PETG heat path and 20 % less air path, so it runs about 7 K hot. If you get about 62 °C,
  check that `H_petg` is applied.

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
   - With set A, expect about **1.9 W from the motor faces, 1.4 W from the fin** (1.29 W outside the shell and 0.10 W inside) **and about
     0.75 W from the PETG** (0.7 to 0.8 W; 0.64 W at PETG k 0.12).
   - The PETG heat is real. The motor's −x face and the fin patch are both bonded to the PETG deck, which is 13.5 mm thick and acts
     as a fin of its own. The network's 2.4 to 2.6 W of "non-fin" heat is the motor faces and the PETG together.
2. **Temperature plot.** Open **Results → Thermal1**. Right-click → Edit Definition → Celsius, and set the legend to
   **23 to 65 °C**. The motor should be the hottest body. The fin cools steadily from the motor patch to the tip.
   The PETG is hottest on the motor plate and cools away from it, but it is still warm 10 to 15 mm out (section 6).

If the balance does not close, check in this order:
- the heat power value and where it is applied;
- whether any convection face set is missing, such as the back face of the fin;
- whether a face has two convection loads, so it is counted twice (the PETG's 0.7 to 0.8 W is expected: it is not a double load).

---

## 6. Outputs to record

Right-click Thermal1 → **Probe** → *On selected entities*. It shows the minimum, maximum and average for a face.

| Output | Probe | FEA | Target (painted, vented) |
|---|---|---|---|
| **Motor block mean** | average over the block's faces, or one probe mid-block | | **55 to 56.5 °C** with set A (network 55.9 to 58.8; CAD fin 56.6 to 59.4) |
| Motor face against the fin | the motor front face, average | | about the motor mean, minus less than 1 K (3-D: 0.4 K) |
| **PETG maximum** | the slip-in faces touching the fin and the motor: **maximum** | | **about equal to the motor mean** (within 0.2 K): 55 to 56.5 °C with set A; **must be under 60** |
| PETG face against the fin | the slip-in faces touching the fin: maximum and average | | 0.5 to 1.2 K below the motor mean |
| PETG, 10 to 15 mm from the motor surface | any slip-in face at that distance | | **still hot**: up to about 52 °C (mean 40 °C); at 15 to 25 mm, about 43.5 °C |
| Fin at the shell exit | the split line, centre | | |
| **Fin, 50 mm above the shell exit (TC2 line)** | the second split line, centre | | rise **11.9 to 13.7 K** (35 to 37 °C) |
| Fin tip | the top edge | | rise **3.4 to 4.5 K** (about 26.5 to 27.5 °C); as-built fin 2.5 to 2.8 K |
| **Heat through the fin** | List Heat Power on the fin's convection faces (`H_fin_out` + `H_fin_in`) | | **1.36 to 1.63 W** (3-D: 1.4 W) |
| Heat through the PETG | List Heat Power on the `H_petg` faces | | **0.7 to 0.8 W** |
| Heat through the motor faces | List Heat Power on the `H_motor_air` faces | | about **1.9 W** |

**The PETG does not insulate near the motor.** The bonded deck is 13.5 mm thick. About 20 cm³ of PETG is above 50 °C (x −35 to 20,
y −64 to 8, z −29 to 33 mm in the station frame). That matters for the hot-tab creep check, not only for the 60 °C face limit.

Save plots for the deck:
- `C_temp_assembly.png`: Thermal1, legend 23 to 65 °C, isometric, with the motor, fin and slip-in visible;
- `C_temp_section.png`: a section through the motor axis, showing the heat path into the fin and the PETG;
- `C_heatflux.png`: a Heat Flux plot (Resultant), showing where the heat leaves.

---

## 7. Variants (15 minutes; duplicate the study and change one thing each time)

| Study | Change | Expected motor temperature (network, no PETG path; 3-D value where one was run) |
|---|---|---|
| `C2_sealed` | `H_motor_air` h **8.7**, bulk **36 °C**; `H_fin_in` and `H_petg` bulk **36 °C** | 63.5 to 67.8 °C; 3-D 63.5 °C, with the PETG also at 63.5 °C (PETG **above 60**: this is why the shells stay vented) |
| `C3_bare_fin` | `H_fin_out` h **4.8** | 59.5 to 61.6 °C; 3-D 57.9 °C, with 0.83 W through the PETG (paint matters at 1.5 A) |
| `C4_1p35A` | Heat Power **3.28 W** (1.35² × 1.8) | 49.9 to 52.2 °C (set A reads lower, as at 1.5 A) |
| `C5_no_fin` | Exclude Heat_horn from analysis; move the motor-to-plate contact to the slip-in; motor faces only | **about 69 °C** with the real PETG path (PETG 1.20 W, PETG maximum 69 °C). The network, with no PETG path, gives 77.1 °C |
| `C6_PETG_infill` | PETG k **0.12** | motor **about +1 K** (56.4 against 55.3 °C); the PETG takes less heat (0.64 W) and gets slightly hotter at the contact |
| `C7_transient` (optional) | Properties → **Transient**: total time **5400 s**, step **60 s**; initial temperature 23 °C on all bodies (Thermal Loads → Temperature → Initial temperature) | **about 90 to 97 % of the steady rise at 60 minutes**: this study fixes the shell air at 27 °C and includes the PETG mass. A fixed-air lumped model gives tau 17 to 19 min and 96 to 97 % with no PETG mass, and 90 to 92 % (tau 24 to 26 min) if about 15 % of the PETG mass takes part. The 94 % is for the hold test with the real shell (it warms up), not for C7 |

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
| TC1 motor case, next to the fin | 55 to 59 °C painted (rise 32 to 36 K over 23 °C): 3-D with the PETG path 55 to 56.5, network 55.9 to 58.8 |
| TC2 fin, 50 mm above the shell exit | rise 12.1 to 13.7 K painted, 17.8 to 19.7 K bare (as-built fin) |
| PETG next to the motor plate (IR) | about equal to the motor case, so 55 to 59 °C painted: under 60 °C, with 0.4 to 4.7 K margin. A bare fin has none |
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
| The PETG takes 0.7 to 0.8 W in the energy balance | Expected with set A: the bonded deck carries heat (section 5). It is not a double load; do not remove loads to make it zero |
| Motor at about 62 °C | `H_petg` was left out (set D, section 3.3). Apply it to the slip-in's free faces |
| Motor at about 52 °C | R_ma was kept at 12 K/W on the air faces and the PETG is loaded too (set B, section 3.3). Use h 10.1 |
| "Bodies are not in contact" or no heat in the fin | Gap between the motor and the fin in the copy; check Interference Detection and Clearance; mate the faces coincident |
| Mesh fails | Raise the global size, add a 1 mm control on the fin only, or simplify the slip-in fillets in the copy |
| Results in K | Edit the plot definition to Celsius; compare rises, not absolute values |

---

## 11. Results template (paste into `verification/simulation_results_motor_assembly.md`)

```
Study C, motor in the station assembly. Run by ____  Date ____  SolidWorks release ____  Evidence: SIMULATED
Current 1.5 A, heat power ____ W (4.05 with R 1.8 ohm; measured R ____)  Room ____ C  Shell air ____ C  Vented / sealed
Fin: k_eq ____ (40.3), h_out ____ (9.2 painted / 4.8 bare), h_in 4   Motor h ____ (10.1 on 6,612 mm2, set A)   PETG k ____ (0.20)   Contact ____ (1e-4 paste)
Mesh ____ elements   Energy balance ____ W of ____ W (within 1 %?)
Split: motor faces ____ W (1.9)   fin ____ W (1.4)   PETG ____ W (0.75)
Motor block mean ____ C (55-56.5, set A)   PETG max ____ C (about the motor mean, < 60)   Fin heat ____ W (1.36-1.63)
Fin 50 mm above exit ____ K rise (11.9-13.7)   Tip ____ K (3.4-4.5)
Variants: sealed ____ C (63.5), bare ____ C (about 58; network 59.5-61.6), 1.35 A ____ C (49.9-52.2 network), no fin ____ C (about 69), PETG k 0.12 ____ C (+1 K)
Hold test: TC1 ____ C, TC2 ____ K, PETG ____ C, A4988 heatsink ____ C at ____ min
Plots saved: C_temp_assembly.png, C_temp_section.png, C_heatflux.png
Findings: ____
```

*Links:* [Study B, fin alone](SW_THERMAL_HEAT_FIN.md) · [answer-sheet script](../../calculations/thermal_assembly_1p5a.py) ·
[network and fin model](../../calculations/simulation_loads.py) · D37 in [DECISIONS.md](../../DECISIONS.md).
