# Study E: SolidWorks thermal of a detailed NEMA 17, the 1/8 in fin and the motor screws (1.5 A)

SolidWorks Simulation walkthrough for Jasper (lead, 2026-10-22). Jasper's direction: use **SolidWorks Simulation**, not ANSYS
(the ANSYS manual, Study D, is kept for reference only).

Study E replaces Study C's plain steel block with a **multi-part NEMA 17**: aluminium end caps, a black steel stator, copper
windings as the heat source, a steel shaft and a plastic connector. It adds the four M3 screws, so you can see heat travel
from the motor into the screws and the PETG tab.

**Geometry:** `exports/step/thermal_station1021_detailed_fin1p8.step`, from `cad/thermal_station1021.py` (variant `detailed`).
It is one STEP assembly; every part is named.

| Part | What it is | Material to assign | k (W/m·K) | Its outside surface |
|---|---|---|---|---|
| `front_cap` | die-cast aluminium end cap, Ø22 pilot boss, 4 × M3 threaded holes | Custom "Al die-cast A380" | 96 | aluminium (check: silver or black?) |
| `stator` | laminated silicon-steel stack, 22 mm | Custom "Silicon steel lamination" | 25 | black-painted steel |
| `winding` | copper coils + insulation, homogenised; **the heat source** | Custom "Winding (Cu + insulation)" | 5 (assumed) | inside, not exposed |
| `rear_cap` | aluminium end cap | Al die-cast A380 | 96 | aluminium |
| `shaft` | Ø5 steel shaft | Alloy Steel (library) | 50 | steel |
| `connector` | plastic connector housing | Custom "PBT" | 0.25 | plastic |
| `screw_1..4` | M3 × 12 socket head, 3.8 mm into the front cap | Alloy Steel | 50 (42 for 12.9; stainless 16) | steel |
| `fin_in`, `fin_out` | the **1/8 in** fin, split where it leaves the shell | 6061-T6 (library 6061 Alloy) | 167 | matte black paint |
| `slipin_mount` | the PETG slip-in | Custom "PETG printed" | 0.20 | PETG |

**A note on the motor's surfaces.** On a NEMA 17 the black sides are **not plastic**: they are the laminated **steel** stator,
painted black.
- The front and rear end caps are **aluminium**: often silver, sometimes painted black.
- The only plastic is the connector housing.
- Check your motor with a magnet: it sticks to the black sides (steel), not to the end caps (aluminium) or the connector.

The finish matters for heat loss, because black surfaces radiate about 9 times more than bare aluminium (emissivity 0.9
against 0.1). Section 3 gives the numbers for both.

---

## 0. The answer sheet (1.5 A, 4.05 W, room 23 °C, vented shell, painted 1/8 in fin)

| Output | Expected | Source |
|---|---|---|
| **Motor outside** (front cap, stator) | **45 to 49 °C** | network model (sheet 48.9 °C; refined with radiation 44.7 to 45.8 °C) |
| Winding | a few K above the stator in this model; a real motor's winding sits 10 to 20 K above its case (insulation, air gaps) | the homogenised winding conducts better than a real coil |
| **Heat carried by the fin** | **2.4 to 2.5 W** (about 60 % of 4.05 W) | network model |
| **PETG max** (tab against the fin) | about 1 to 3 K below the front cap: **≈ 43 to 48 °C** | must stay **under 60 °C** |
| **Screw heads** | close to the front cap temperature, minus a few K | steel bridges heat around the PETG |
| Heat per screw | well under 0.1 W | a head can only lose heat into the PETG and still air |

The model passes when:
- the energy balance closes within 1 % of 4.05 W;
- the front cap lands in the 45 to 49 °C band;
- the fin carries 2.2 to 2.8 W.

---

## 1. Open and prepare

1. In SOLIDWORKS: **File → Open →** `thermal_station1021_detailed_fin1p8.step`. Import as an **assembly**; each named part
   becomes a component.
2. Save it as `Thermal_E.SLDASM` in its own folder. It is a copy, so nothing in your real assembly changes.
3. Run **Tools → Evaluate → Interference Detection**. Expect **no interferences**. The parts only touch:
   - the screws in the front-cap holes;
   - the screw heads on the tab;
   - the motor on the fin;
   - the fin on the tab.

## 2. Study setup

1. Turn on **Tools → Add-Ins → SOLIDWORKS Simulation**.
2. Open **Simulation → Options → Default Options → Units**. Set Temperature to **Celsius** and Length to **mm**.
3. Choose **Simulation tab → New Study → Thermal**, and name it `E1_1p5A_vented_1p8fin`.
4. Right-click the study → **Properties**: Steady state; solver Automatic.
5. **Materials:** right-click each part → Apply/Edit Material. Use the table above; for the custom materials enter the thermal
   conductivity only.
6. **Connections:**
   - Global (Component) Contact: **Bonded**.
   - Then add Contact Sets of type **Thermal Resistance (Distributed)**:

| Faces | Value (K·m²/W) | Why |
|---|---|---|
| front_cap front face ↔ fin_in back face | **1.0e-4** | thermal paste |
| fin_in front face ↔ slipin_mount tab face | 3.3e-4 | dry metal on a print |
| each screw head underside ↔ slipin_mount tab face | 3.3e-4 | dry |

   The screw shanks in the front-cap holes stay **Bonded** (good thread contact). So do the parts inside the motor: caps to
   stator, stator to winding, and shaft to caps.

## 3. Thermal loads

**Heat power:** right-click Thermal Loads → **Heat Power** → select the **winding** part → **4.05 W** (1.5² × 1.8 Ω; the 1.8 Ω
is assumed, so measure one phase).

**Convection.** Each surface type gets its own set, so you can see the different finishes:

| Set | Faces | h (W/m²K) | Bulk air (°C) | Note |
|---|---|---|---|---|
| `stator_black` | the four black stator sides | **10** | 26 | black paint: about 4 convection + 6 radiation |
| `caps` | the end caps' free faces (sides and the rear face) | **10** if your caps are black, **5** if they are silver aluminium | 26 | |
| `connector` | the connector's free faces | 10 | 26 | tiny area; included for completeness |
| `fin_out` | all faces of fin_out except the split plane | **9.8** | 23 | painted fin outside the shell, radiation included |
| `fin_in` | fin_in faces that touch nothing | 4 | 26 | inside the shell |
| `heads` | the screw heads' exposed faces | 4 | 26 | |
| `petg` | the slip-in's free faces | 5 | 26 | |

The 26 °C bulk air is the inside of a vented shell with the 1/8 in fin (network model). Room air is 23 °C.

**Optional, more physical:** instead of folding radiation into h, use h = 4 everywhere and add a **Radiation** load per surface
type:
- emissivity **0.9** on the black stator, the painted fin and the connector;
- **0.1** on bare aluminium caps;
- ambient 26 °C inside the shell and 23 °C for fin_out, view factor 1.

This makes the study nonlinear, but the answer should agree within a few per cent.

## 4. Mesh and run

1. **Mesh:** Blended curvature-based, maximum 5 mm, minimum 0.5 mm.
2. **Mesh controls:**
   - screws: 0.5 mm;
   - front cap and fin_in: 1.5 mm;
   - fin_out: 2 mm (the 3.175 mm plate then gets two elements through its thickness).
3. **Run.**

## 5. Results

1. **Energy balance:** Results → List Heat Power (or Result Force → Heat Power), selecting all the convection faces. The total
   must be 4.05 W.
2. **Temperature plot:** use a legend of 23 to 55 °C. Section the plot through one screw (a plane through the motor axis and
   the screw) to see the heat path: winding → stator → front cap → fin and screws → PETG.
3. **Probes:**
   - front cap (average);
   - stator side (average);
   - winding (maximum);
   - each screw head (maximum);
   - slipin_mount (**maximum**, and where it occurs);
   - fin 50 mm above the shell exit.
4. **Heat through the fin:** List Heat Power on the fin_in and fin_out convection sets.
5. **Variants** (duplicate the study):

| Variant | Change | Expected |
|---|---|---|
| 0.019 in prototype fin | swap in `thermal_station1021_fin0p019.step`, which has the simple motor block and the real 0.483 mm fin. Same loads; fin h 9.2; bulk air 27 °C | motor 56 to 59 °C |
| No screws | Exclude screw_1..4 from analysis | the screws' own effect on the PETG |
| Silver caps | caps h 5 | the motor a little hotter |
| Sealed shell | bulk air 32.5 °C; stator and caps h 8.7 | the worst case for the PETG |

## 6. What this does not show

- **The shell air temperature** is an input. Flow Simulation would compute it.
- **Inside the motor** the result is only indicative: a homogenised winding, no rotor, perfect internal contacts. The outside
  temperatures, which are what the fin and the PETG see, are the trustworthy part.
- **The driver chip** (A4988) is not modelled. Log it during the hold test.
- **Creep.** The PETG under the screw heads warms from both sides; check that the screws are still tight after the 90-minute
  hold test.

*Links:* [Study C (simple block)](SW_THERMAL_MOTOR_ASSEMBLY.md) · [spec](../../cad/HEAT_FIN_1021_SPEC.md) ·
[answer sheet](../../calculations/thermal_assembly_1p5a.py) · [fin sizing](../../calculations/fin_sizing_4w.md)
