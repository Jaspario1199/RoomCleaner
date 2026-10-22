# Study D: ANSYS steady-state thermal of the motor, fin, motor screws and heat-set inserts (1.5 A)

ANSYS Mechanical walkthrough for Jasper (lead, 2026-10-22). It is the ANSYS version of Study C
([`SW_THERMAL_MOTOR_ASSEMBLY.md`](SW_THERMAL_MOTOR_ASSEMBLY.md)), with two additions Jasper asked for:
- the **four M3 motor screws**;
- the **brass heat-set inserts**, to see how much heat reaches them.

It runs on the simulation-ready geometry from `cad/thermal_station1021.py` (spec: `cad/HEAT_FIN_1021_SPEC.md`):

| File | Fin |
|---|---|
| `exports/step/thermal_station1021_fin1p8.step` | the **1/8 in production fin** (D38) |
| `exports/step/thermal_station1021_fin0p019.step` | the **0.019 in prototype fin** |

Both are in your assembly's own coordinates, and every body is named. The answer sheet comes from
`calculations/thermal_assembly_1p5a.py`.

**Time:** about 2 hours the first time, then about 15 minutes per variant.

**Licence:** the Ansys Student version is enough if the mesh stays under its node and element limit (128 k at the time of
writing). Section 5 keeps it there. A TAMU academic licence has no such limit.

**Not yet confirmed:**
- **Which inserts.** The 10/21 CAD has no inserts at the motor: the motor screws thread straight into the motor. The
  insert-size pockets in your slip-in are:
  - one Ø4.1 × 7 pocket (M3) in the deck under the spool;
  - the four Ø3.45 encoder divot holes (M2.5).

  The geometry models those as `insert_deck` and `insert_enc_1..4`. If you meant other inserts, tell me where and I will add
  them.
- **Screw material.** Black-oxide alloy steel (class 12.9, k about 42 W/m·K) is assumed. Stainless A2 is 16 W/m·K.

---

## 0. The answer sheet

Conditions: 4.05 W in the motor (1.5 A, 1.8 Ω assumed), room 23 °C, vented shell, painted fin, paste between the motor and the
fin. All values are CALCULATED. Each range runs from "heat spread evenly over the fin patch" to "flange at one temperature"; the
motor block of the FEA is close to the second case.

| Output | 1/8 in fin (production) | 0.019 in fin (prototype) |
|---|---|---|
| **Motor block** | **44.7 to 45.8 °C** | **55.9 to 58.8 °C** |
| **Heat carried by the fin** | **2.41 to 2.50 W** (about 60 % of 4.05) | 1.41 to 1.63 W (35 to 40 %) |
| Shell air (input) | 26 °C | 27 °C |
| Fin, 50 mm above the shell exit (rise over room) | 15.6 to 16.1 K | 12.1 to 13.7 K |
| Fin tip (rise) | 10.8 to 11.1 K | 2.5 to 2.8 K |
| **Each motor screw, shank** (head to motor) | about 28 K/W in steel (72 in stainless) | about 19 K/W (49) |
| **Screw heads** | expect within a few K of the motor (see below) | same |
| **PETG under the screw heads and at the tab** | expect close to the motor temperature | same |
| **Inserts (deck, encoder)** | expect only a few K above the shell air (see below) | same |

**Why the screw heads stay nearly as hot as the motor:**
- The steel shank conducts well: about 19 to 28 K/W, against about 4,000 to 6,000 K/W for the same path through PETG.
- But a head can only lose heat into the PETG and the still air inside the shell, and both of those paths are poor.
- So each screw carries little heat (well under 0.1 W) and its head sits near the motor temperature. The screws are **hot
  spots** on the spool side of the tab, not heat paths. That is worth seeing in the plot: the PETG under each head is heated
  from both sides.

**Why the inserts stay cool:** they are 25 to 50 mm of PETG away from the motor, and PETG (k 0.2) is about 800 times worse than
aluminium.
- **If any insert comes out more than about 10 K above the shell air, check the contacts first** (section 4): a spurious
  bonded contact across a clearance gap is the usual cause.
- Motor and fin readings within the ranges above, and the inserts cool, means the model is behaving.

---

## 1. Materials (Engineering Data)

Double-click **Engineering Data**, then add new materials. Steady state needs only **Isotropic Thermal Conductivity**.

| Material | k (W/m·K) | Bodies | Note |
|---|---|---|---|
| `Motor block (steel)` | 50 | `motor_block` | a lumped stator and can; it behaves nearly isothermal, like the real flange |
| `Al 6061-T6` | 167 | `fin_in`, `fin_out` | 5052-H32 would be 138 |
| `PETG printed` | 0.20 | `slipin_mount` | sensitivity run at 0.12 (infill) |
| `Steel 12.9 screw` | 42 | `screw_1..4` | stainless A2: 16 |
| `Brass insert` | 110 | `insert_*` | CuZn39Pb3 is about 110 to 120 |

For the optional transient (section 8) add density and specific heat:

| Material | Density (kg/m³) | Specific heat (J/kg·K) | Why |
|---|---|---|---|
| Motor block | 4100 | 460 | the block then weighs about 280 g, like a real NEMA 17 |
| Al 6061-T6 | 2700 | 896 | |
| PETG printed | 1270 | 1200 | |
| Steel 12.9 screw | 7850 | 460 | |
| Brass insert | 8500 | 380 | |

---

## 2. Geometry

1. In Workbench, drag **Steady-State Thermal** from the Toolbox onto the Project Schematic.
2. Right-click **Geometry → Import Geometry → Browse** and choose `thermal_station1021_fin1p8.step`.
3. Open it in **SpaceClaim** (or Discovery) once to look. You should see these bodies:
   - `motor_block`;
   - `fin_in` and `fin_out`: the fin split where it leaves the shell, so the two get different convection;
   - `slipin_mount`;
   - `screw_1..4`;
   - `insert_deck` and `insert_enc_1..4`.

   Do **not** use Share Topology. Contacts handle every joint, including the fin split.
4. Check the units: mm.

---

## 3. Mechanical: assign the materials

Open **Model**. Under Geometry, select each body and set Material → Assignment from the table in section 1.

---

## 4. Contacts (the step that decides the answer)

1. Click **Connections**.
2. In the Details pane set **Tolerance Type: Value, 0.05 mm before** auto-detection. The screw shanks pass through the Ø3.4 fin
   hole and the Ø3.5 tab hole with a 0.2 to 0.25 mm radial gap. A larger tolerance would bond them to the PETG and the fin,
   which is wrong.
3. Right-click Connections → **Create Automatic Connections**.
4. Check that you have these contact regions:

| Pair | Type | Thermal conductance (Advanced → Thermal Conductance) |
|---|---|---|
| `motor_block` – `fin_in` (motor front face) | Bonded | **Manual, 10,000 W/m²K** (paste; 3,000 if dry). In mm units type `10000 [W m^-2 C^-1]` |
| `fin_in` – `fin_out` (the split plane) | Bonded | Program Controlled (perfect: it is one piece of metal) |
| `fin_in` – `slipin_mount` (tab face) | Bonded | Manual, 3,000 W/m²K (dry metal on a print) |
| `motor_block` – `slipin_mount` (where the motor touches the back plate) | Bonded | Manual, 3,000 |
| `screw_n` shank – `motor_block` (the threaded holes) | Bonded | Program Controlled (thread contact is good) |
| `screw_n` head – `slipin_mount` (head on the tab face) | Bonded | Manual, 3,000 |
| `insert_*` – `slipin_mount` | Bonded | Program Controlled (melted-in knurl) |

**There must be no contact between a screw shank and the fin or the tab.** If one appeared, delete it and lower the tolerance.

Tip: right-click each contact region → **Go To → Bodies For Selected** to see what it joins.

---

## 5. Mesh (fits the student limit)

| Control | Scope | Setting |
|---|---|---|
| Defaults | all | Element Order: **Program Controlled** (quadratic); Physics Preference Mechanical, Element Size 5 mm |
| Body Sizing | `screw_*`, `insert_*` | 0.6 mm |
| Body Sizing | `motor_block` | 3 mm |
| Body Sizing | `fin_in`, `fin_out` | 1.5 mm |
| Method: **Sweep** | `fin_in`, `fin_out` | Src/Trg Selection **Automatic Thin**, Sweep Num Divs **2** for the 1/8 in fin, **1** for the 0.019 in fin |
| Body Sizing | `slipin_mount` | 5 mm; add a Face Sizing of 1.5 mm on the tab faces around the screw holes and the pilot |

Generate the mesh and read **Statistics → Nodes**. If it is over the student limit:
1. raise the slip-in size to 7 mm;
2. then set Element Order **Linear** on the slip-in only (Method on the body → Element Order Linear).

The slip-in is where the elements go, and the temperature gradients inside PETG far from the motor do not matter.

---

## 6. Thermal loads

**Make Named Selections first,** so the faces are easy to pick again in the variants. Right-click a selection of faces →
Create Named Selection:

| Named Selection | Faces |
|---|---|
| `NS_motor_free` | the motor block's faces that do not touch the fin or the slip-in (the sides and the back) |
| `NS_fin_out` | all faces of `fin_out` except the split plane |
| `NS_fin_in` | the faces of `fin_in` that touch nothing (outside the motor and tab patches), front and back |
| `NS_petg_free` | the slip-in faces near the motor tab, or all of its exposed faces if that is quicker |
| `NS_heads` | the exposed faces of the four screw heads |

**Loads** (Steady-State Thermal → Insert):

| Load | Scope | Value |
|---|---|---|
| **Internal Heat Generation** | `motor_block` (body) | **4.05 W ÷ the block volume.** Read the volume in the body's Details (Properties). About 67,880 mm³ gives **5.966e-5 W/mm³** (= 59,660 W/m³) |
| Convection | `NS_motor_free` | film **10.1 W/m²K**, ambient **27 °C** (26 °C for the 1/8 in fin) |
| Convection | `NS_fin_out` | film **9.8 W/m²K** (1/8 in) or **9.2** (0.019 in), ambient **23 °C**. Radiation is included; do not add a radiation load too |
| Convection | `NS_fin_in` | film 4 W/m²K, ambient 27 °C |
| Convection | `NS_petg_free` | film 5 W/m²K, ambient 27 °C |
| Convection | `NS_heads` | film 4 W/m²K, ambient 27 °C |

Leave everything else adiabatic: the slip-in's faces against the wall mount, and the insert bores.

You can type any value with its units, e.g. `10.1 [W m^-2 C^-1]`. Mechanical converts it to the model's unit system.

---

## 7. Solve and results

1. Click **Solve**. Steady linear thermal takes under a minute.
2. **Energy balance first.** Insert → Probe → **Reaction** for each convection boundary. The five must add up to 4.05 W.
   Expected:
   - 1/8 in fin: motor faces about 1.6 W, fin about 2.4 to 2.5 W, the PETG and screw heads a few hundredths;
   - 0.019 in fin: motor faces about 2.4 to 2.6 W, fin about 1.4 to 1.6 W.
3. Insert these results:
   - **Temperature** (whole model). Set the legend from 23 to 50 °C (1/8 in) or 23 to 60 °C (0.019 in).
   - **Temperature scoped to each insert body**: record the maximum.
   - **Temperature scoped to `screw_1..4`**: the head maximum and the minimum.
   - **Temperature on `slipin_mount`**: the maximum. That is the PETG number for the 60 °C limit, and where it occurs.
   - **Total Heat Flux** on `slipin_mount` and the screws, as a vector display. It shows the heat entering the PETG at the tab
     and the screws carrying heat around the PETG.
   - **Reaction probe on a contact region**: on the motor–fin contact (heat into the fin) and on each screw shank–motor
     contact (heat into each screw).
4. A section plane through one screw (y–z plane at x = 15.5 in the station frame) gives the most useful picture:
   motor → screw → head → PETG.

**Results table** (paste into `verification/simulation_results_ansys_motor_screws.md`):

```
Study D (ANSYS), fin ____ (1/8 in / 0.019 in), run by ____, date ____, release ____, nodes ____
Heat ____ W (4.05), shell air ____ C, h_fin_out ____, contact motor-fin ____ W/m2K
Energy balance: motor ____ W, fin ____ W, PETG ____ W, heads ____ W, sum ____ W
Motor block ____ C (44.7-45.8 | 55.9-58.8)   Heat into the fin ____ W (2.41-2.50 | 1.41-1.63)
PETG max ____ C at ____   Screw heads ____ C   Heat per screw ____ W
Inserts: deck ____ C, enc_1..4 ____ / ____ / ____ / ____ C   (shell air ____ C)
With screws suppressed: motor ____ C, PETG max ____ C   (the screw effect)
Plots: D_temp_full.png, D_section_screw.png, D_flux_petg.png
```

---

## 8. Variants (duplicate the analysis: right-click the system → Duplicate)

| Variant | Change | What it shows |
|---|---|---|
| **Fin 0.019 in (prototype)** | Replace the geometry with `thermal_station1021_fin0p019.step`; fin film 9.2; motor-face ambient 27 °C | the motor about 11 to 13 K hotter; the screws and the PETG hotter with it |
| **Without screws** | Right-click `screw_1..4` → Suppress | the screws' own effect on the PETG and the insert temperatures |
| **Stainless screws** | screw k 16 | less heat to the heads |
| **Sealed shell** | ambients 36 °C (0.019) or 32.5 °C (1/8 in); motor film 8.7 | the worst case for the inserts and the PETG |
| **Transient** (optional) | Transient Thermal system, 5400 s, 60 s steps, initial temperature 23 °C, with the densities and specific heats from section 1 | compare minute by minute with the hold test |

---

## 9. What this cannot tell you

- **The shell air temperature** is an input from the network. ANSYS Fluent, or Icepak with conjugate natural convection, could
  compute it; that is a bigger job.
- **The A4988 driver and the station board** are not modelled. Their 1.5 W is lumped into the shell air. Log the driver during
  the hold test.
- **Preload loss.** Steady thermal shows temperature only. Whether a screw or insert loosens as the PETG softens under it is a
  creep question, made worse at the PETG under the screw heads. Keep the PETG well below 60 °C, and check the screws for
  tightness after the hold test.
- **Coil resistance.** 1.8 Ω is assumed; measure one phase. The heat scales with it.

---

## 10. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Insert or PETG far hotter than expected | a contact bonded across a clearance gap (the tolerance is too big), or the PETG got steel by default |
| Energy balance short | a convection Named Selection is missing faces, or Internal Heat Generation is on the wrong body |
| Motor hundreds of °C | heat generation entered as W/m³ while the model is in mm (use the `[W m^-3]` units syntax) |
| Mesh over the student limit | coarser slip-in, Linear elements on the slip-in, a Sweep on the fin |
| Fin uniformly hot | `NS_fin_out` convection missing, or the fin_in–fin_out contact missing |

*Links:* [Study C (SolidWorks)](SW_THERMAL_MOTOR_ASSEMBLY.md) · [spec](../../cad/HEAT_FIN_1021_SPEC.md) ·
[answer sheet](../../calculations/thermal_assembly_1p5a.py) · [fin sizing](../../calculations/fin_sizing_4w.md)
