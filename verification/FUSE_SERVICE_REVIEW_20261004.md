# Independent fuse service fit review — 4 October 2026

**PASS for nominal unpowered fit prototype only.** Independently run
`python -m verification.check_fuse_service_independent`: **2,732 checks passed**.
Reviewed CAD SHA-256: `79bbdb024aee344371ce938e126c479bd145fb73554977e234423209fd363d4d`.
This reviewer did not implement the part geometry.

## Checks and measured result

- Replacement cover, revised electronics carrier, and fuse support: valid,
  exactly one solid each; independent temporary STEP export/reimport volume
  difference below 0.001 mm³ and bounding-coordinate difference below 0.00001 mm.
- Support, holder reference and both finite lead envelopes: no static overlap
  above 0.001 mm³ with modeled station parts and hardware.
- Both carrier nut roofs: 3 mm nominal after local boss revision; material
  probes spanning 2.98 mm inside each roof are fully contained. This is a
  geometry check, not an M3 pullout or printed-material strength result.
- M3 attachment access: modeled Ø5 mm axial tool clears rigid parts with holder
  installed **only after both flexible leads are released and deflected**.
  Real flexible repositioning and hand access are not simulated.
- Cover and combined support/holder/lead assembly removal checked at +Z
  0.1, 0.5, 1, 2, 3, 5, 7, 10, 25, 50, 90 and 125 mm against the relevant
  stationary parts. These are sampled positions, not a continuous sweep proof.
- Upper lead-envelope clearance to inner roof: **3.1699999 mm** nominal.

## Findings resolved during review

1. Original carrier pockets left a 0.5 mm nut roof. Implementer added local
   bosses to give 3 mm, raised the support foot, and changed screws to M3×10.
2. Original static regulator-keeper overlap was 0.700563 mm³. First static
   relief still collided during extraction: 0.035028 mm³ at +Z0.5 mm and
   0.490394 mm³ at +Z2 mm. Implementer extended the clearance channel down
   through the foot; independent extraction checks now pass.
3. Original closed strain-relief passages obstructed straight lead lifting.
   Implementer opened their +Z sides and corrected service instructions.
4. Both nominal lead routes intersect the X−13 attachment-driver envelope by
   about 3.372035 mm³. They must both be released and held clear before screws
   are reached. The check explicitly excludes the displaced flexible leads;
   it does not silently claim the installed routes clear the tool.

## Correct service scope and remaining gates

Disconnect the downstream lead ends, release strain-relief ties, move both
leads clear of the tool, undo support screws, and withdraw support plus holder.
The lower lead is threaded through the annular seat **off the case** before
separating the holder. The holder and pre-bent lower lead do not simply lift
straight through that seat. Physical service access remains a fit-test gate.

The 4.4 mm swept diameter is a clearance allocation, not measured insulation
OD; 15 mm centerline radius is provisional. The finite paths stop at Y−34 mm.
Downstream connections, complete harness routing and service loops remain open.
Body retention requires selected ties and compliant pads; their retention force,
creep and thermal behavior are unverified. The long support needs printed fit
and stiffness checks. Fastener engagement is nominal; verify purchased screws,
nuts and printed tolerances before tightening. No suspension capacity, motor
thermal limit, fuse rating, wire bend qualification or five-pound lift rating
is established by these checks. This review does not release powered or overhead
operation, nor requalify every unchanged part of the inherited housing.
