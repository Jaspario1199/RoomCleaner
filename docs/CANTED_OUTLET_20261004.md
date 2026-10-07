# Fixed canted outlet: independent prototype, not a print release

The separate `cad/winch_canted_outlet.py` experiments with a stationary cartridge whose outgoing axis is `(1,-1,1)/sqrt(3)` in the wall CAD frame (+X tangent, +Y up, +Z into room). Mirroring the station across global YZ changes the tangent sign for the opposite corner. This orientation must be confirmed from actual anchor coordinates; it is not passive cable alignment. An ideal orthant needs 54.7356° around its bisector. A nominal 55° cone has only 0.2644° orientation margin at orthant edges, so an arbitrary wall installation is not qualified.

## Architecture and dimensions

The throat remains at global `(20,-68.25,43)` mm; its nominal load lever arm has not silently moved. The purchased RF8090-05 ring is represented by the prior OEM-derived surface-envelope solid proxy (7.5 mm axial width, approximately 15.005 mm maximum diameter, 5.1 mm throat). The OEM IGES was an open surface, so this is not a manufacturer solid or fit certification.

A split annular carrier exposes the metal flare. Its front collar has ID26/OD34 mm and 2 mm axial stroke. The experimental stopper is OD28 by 8 mm, with rounded edges and a provisional knot cavity; this is not a purchased or validated bead. Guides are positioned at local X±24 mm, using the existing SHS3-12 shoulder geometry and Z-2CS springs at installed 7→5 mm. The rear shell is 12 mm deep. Actual sampled spool-to-throat directions reached 63.626°, so the rear opening was increased to a 65° cone: ID48.59 mm at 10 mm behind the throat. A 55° rear cone failed 24 sampled incoming paths.

The KW12 reference is moved 26 mm outward in local X, with a collar bridge and actuator fork. Its adjustable, secured stationary cradle is **not designed**. The purchased switch force/travel and actual roller envelope still require measurement.

## Critical findings and release blocks

- There is **no load-bearing attachment bracket** from this cartridge to the mount base. The cartridge is not structurally connected to the station; proof loads or ratings for the original carrier cannot transfer to it.
- Its expanded body is incompatible with the original cover. Existing base/cover intersections are included as failed checks rather than ignored. A new bracket and enclosure are required before an assembly can be printed for loaded testing.
- Clamp screws are provisional M3x12 button references at local X±28,Y10 with heads seated at Z6. The complete head-bearing annulus is not supported: measured contact is about 92% of the required annulus. This is an explicit failed mate, requiring a larger boss or revised screw location.
- The incoming spool corridor check spans winding X4.5..36.5, radii10..15 mm, and 12 azimuths per radius. It checks potential straight segments, not actual winding tangency or dynamic rubbing. The last 3.8 mm before the throat is excluded because the real metal bellmouth redirects the rope; metal contact and bend durability remain physical gates.
- Outgoing cable tests sample 0/15/30/45/55° and 12 azimuths from a worst throat-edge start, using a 0.6 mm cable reference. Sampling is not a continuous mathematical clearance proof. Actual purchased braid diameter must be checked.
- Stopper return is checked only in the **axial homing pose**. Full oblique bead engagement at 55° is not established. The large bead can pull sideways, jam, miss reliable switch travel, or abrade the rope. A restricted near-home pose and physical return testing are required.
- A stationary canted outlet avoids moving bearing axes and their cable-routing conflicts; it does not eliminate collar side loads, room-coordinate uncertainty, or printed load-path requirements.

## Outputs and verification

Run `python -m cad.winch_canted_outlet` from the repository root. It writes `cad/exports/canted_outlet/canted_outlet_experiment.step` and `audit.json`. The audit contains valid/connected solid checks, every installed part pair with explicit pilot-thread/purchased-lever exceptions, full clamp-head bearing, existing case fit, spool corridor, outgoing cone, collar stroke, and axial stopper approach. Failed rows are retained. The STEP is a geometry review artifact, not a print package.

Next work is to establish the actual station orientation envelope, redesign and qualify the bracket/load path, replace the cover, secure the KW12 cradle with service access, fix clamp head bearing, and physically test bead return, switch reset, braid abrasion, guide binding, and measured proof loads. No overhead operation or final parts ordering is approved by this experiment.
