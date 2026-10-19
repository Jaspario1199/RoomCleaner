# Experimental articulating outlet: reject as a print release

A separate CadQuery clearance skeleton lives in `cad/winch_articulating_outlet.py`. It preserves the current housing release. Its two axes intersect the Ronstan ring throat: yaw about Z and pitch about X. The pitch frame surrounds the existing homing cartridge; a yaw frame surrounds that frame; a fixed frame surrounds both. The nominal outside footprint is220x220mm before mounting and wiring provisions. This is a packaging experiment, not a finished assembly.

## Why the first gimbal idea does not solve the problem

Articulation does not establish passive alignment. A tension force passing through the pivot intersection has little aligning moment. The incoming spool line and outgoing payload line generally have different directions. Even if the outlet faces the payload perfectly, the incoming line must bend at the ring, and the current cartridge's rear hole can block that incoming path. A bead can also contact the annular button eccentrically and jam it. A two-axis swivel introduces four additional moving joints and a flexing switch harness.

At60deg yaw and60deg pitch, the original rearward spool direction differs from the cartridge axis by arccos(cos60*cos60)=75.52deg. A line passing a throat and a second rear guide10mm behind it would need about38.7mm radial opening at that guide, before line diameter and manufacturing clearance. The existing rear opening is around8.3mm diameter. Simply swiveling the current cartridge therefore fails internal cable routing.

## What the CAD experiment actually defines

The140mm pitch frame fits within the180mm yaw frame and220mm fixed frame. Geometric axes intersect at the throat. Nominal8mm cut steel pivot references pass through8.4mm printed running bores or16.2mm bushing sockets. Printed bushing envelopes are16mm OD,8.4mm ID and8mm long. These are manufactured dimensions proposed for an experiment, not verified stock parts. Steel pivot lengths are28mm. M3 split clamps/axial retainers have not been designed or qualified; none are represented as completed mates. Cartridge-to-frame attachments and wall attachment are also absent.

The frame/cartridge angular clearances are tested, and a separate incoming-cable diagnostic explicitly records collisions. With the stationary spool-side line represented by a0.6mm cylinder, the reused rear carrier is clear at0deg but intersects at30deg yaw (1.001mm³),30deg pitch (1.085mm³),45deg yaw (2.380mm³),45deg pitch (2.463mm³), and60/60deg (4.377mm³). These are failed routing checks, not contact exemptions. The STEP is intentionally named `experimental_clearance_skeleton.step`. Do not print it as a working station. A nominal clearance sweep does not prove bearing fit, strength, cable clearance, automatic orientation or homing.

## Alternatives and decision

1. **Larger fixed rounded outlet and larger homing collar:** simplest load path and no flexing switch harness. It needs a ray/cone calculation across the actual room workspace and a larger stopper, followed by off-axis bead tests. A spherical entry or enlarged bellmouth may preserve the stationary electrical switch.
2. **Gimbal with a new cone-cleared rear carrier and a defined incoming guide at the pivot:** feasible to investigate, but needs a new structural cartridge, adequate cone clearance, deliberate alignment mechanism and a qualified flexing harness. The current cartridge cannot be reused unchanged.
3. **Motor-driven gimbal:** explicit commanded orientation can point toward a calculated cable direction, but it adds two actuators/feedback axes and still requires rear cable clearance. It does not fit the present simple prototype objective.
4. **Separate cable homing measurement:** retain a broad-angle stationary metal fairlead and detect bead arrival using an independently supported sensor arrangement. Mechanical contact still needs to tolerate eccentric approach; a simple single-sided button is insufficient without tests.

The first option deserves priority before adding the gimbal's size and moving load joints. This experiment documents why a passive swivel is not ready to replace the stationary station.

Physical qualification, if the gimbal is developed, requires joint friction/retention, printed creep, pin bending and bearing pressure; cartridge attachment and structural wall load path; actual incoming cable swept paths and abrasion; all approach directions with bead trip and return; switch-wire fatigue; angular travel stops; and proof tests at the computed station loads. There is no purchased hardware selection or load rating in this skeleton.
