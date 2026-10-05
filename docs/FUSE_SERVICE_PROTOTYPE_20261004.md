# Fuse service packaging prototype — 4 October 2026

`python -m cad.winch_fuse_service` regenerates the separate variant under
`cad/exports/winch_fuse_service`. Original local-station source and exports are
preserved. The `make()` contract matches `winch_local_electronics.make()`.
This is a nominal packaging prototype, not electrical or mechanical qualification.
Local +Z is depth into the room, not gravity-up.

## Defined geometry

The existing Littelfuse01550100Z body remains Ø15.24×55.63mm at X−17/Y−5.
Its base moves from Z11 to Z40; its far end is Z95.63. The old carrier's
fuse ring is removed in this variant. A separate removable support has an
annular body seat at Z37..40, concave saddles at Z45..51 and76..82, and a
right-side spine. Two accessible3×1.8mm tunnels accept body-restraint ties;
fit compliant insulating pads to the0.2mm radial saddle clearance. The ties
and their tension are physical installation/retention items, not qualified
load-bearing hardware. No tie may squeeze a joint or the fuse-opening seam.

Both outgoing leads are real circular-profile sweeps along a straight segment,
a tangent circular arc, and a second straight segment. They are not bounding
boxes with a radius annotation. Parameters are explicitly provisional:

| Parameter | Value |
|---|---:|
| Wire clearance-envelope diameter |4.4mm|
| Centerline bend radius |15mm|
| Straight exit at each body end |5mm|
| Lower outgoing centerline depth |Z20mm|
| Upper outgoing centerline depth |Z115.63mm|
| Bend endpoint |Y−20mm|
| Finite lead endpoint |Y−34mm|
| Strain-relief fixture center |Y−27mm|
| Cover bulge outer bounds |X−34..2/Y−42..11/Z70..124mm|
| Bulge inner roof |Z121mm|
| Upper lead envelope extreme |Z117.83mm|
| Nominal roof-to-wire envelope clearance |3.17mm|

The lower and upper fixtures each have a Ø5mm lead cradle opened toward+Z and two
1.5×4mm tie slots; they sit after the bend. Use ties through these slots for
strain relief. The lead envelopes end at Y−34: downstream harnesses, joints,
connector pigtails and their service loops are not fully routed by this model.

The4.4mm value is an allocated **clearance envelope**, not a claim about the
supplied wire's actual insulation diameter. The [manufacturer drawing](https://www.littelfuse.com/assetdocs/littelfuse-fuse-holder-155-100-datasheetpdf?assetguid=feb34c70-4b5c-48a2-88f9-895c15c5efcc)
shows0.14in/3.556mm insulated-wire holes;01550100Z has an8in14AWG lead loop,
two springs and no fuse. Actual insulation diameter and permissible bend
radius require purchased-part measurement/manufacturer confirmation. R15 is a
packaging allocation, not a certified supplier minimum. The code rejects
envelope diameters below4.4mm, radii below10mm, and exits below5mm.

## Attachment and service order

The new support attaches only to the removable electronics carrier, using two
M3×10 screws, head diameter≤6mm and height≤2mm, with ordinary2.4mm nuts in
bottom-loaded hex pockets. Local2.5mm carrier bosses provide3mm solid roof
above the2.5mm-deep nut pockets; the support foot is Z11.5..16, with
screw heads atZ16 and10mm shanks reachingZ6. Centers are(−25,−15) and(−13,−18). Insert these
nuts before installing the carrier. This variant does not change the inherited
wall, adapter, structural base or docking interfaces. Existing capacitor M2
hardware remains unchanged; new attachment hardware is M3.

1. Isolate external power and discharge the capacitor. Unplug the external
   input mate and disconnect the cover-mounted internal pigtail.
2. Undo the existing cover fasteners and lift the replacement cover in +Z.
3. Disconnect the two downstream lead ends and release the lead-restraint
   ties. Lift both leads from their open cradles and hold them clear of the
   support screw driver paths. This flexible repositioning is a physical
   service check, not part of the nominal finite-route sweep audit.
4. Remove the two support M3 screws; lift the support, holder and lead routes
   together in +Z. **Do not pull the lower bent lead through the annular seat
   while installed.** The audited +Z removal moves these parts together.
5. On the bench, release the body ties and carefully feed the disconnected
   lower lead through the seat while lifting the holder from its saddle.
   Open the holder only outside the case. Actual wire stiffness, terminal
   removal and threading through the6mm seat hole require physical fit testing.
   Carrier removal uses its original four bolts; replacing captive nuts
   requires removing the carrier.
6. Refit, restore all insulating pads and restraints, check polarity and
   continuity before any restrained bench powering.

## Reproducible evidence and limits

The generated `geometry_audit.json` records the current pass/fail result for the
current build: actual boolean intersection volumes of support/body/both lead
sweeps against inherited components, cover lifts at0/1/5/15/30/60/100/120mm,
support/body/leads against fixed station parts during sampled +Z lifts,
attachment driver cylinders, valid BREP and printable-part STEP round trips.
Failed rows are recorded as failures; no nonzero-intersection exemptions are
used in these checks. Finite wire sweeps meet the holder at their endpoints,
with no volumetric body overlap.

Sampled removal poses are evidence, not a continuous-motion proof. The audit
focuses on the changed support/body/leads; it does not requalify every inherited
hardware pair or model hands, tie installation, flexible harness dynamics,
thread preload, insulation creep or thermal behavior. The upper support arm is
long; stiffness, printing orientation and retention pull testing remain open.
The tie products and compliant pads still require selection and physical fit.

No fuse current, DC interrupt rating, continuous motor current, enclosure
thermal performance, wire bend qualification, or suspension rating is assigned.
The user's5lb reserve is a jeans-handling target, not a released load rating.
Room survey and overhead installation remain deferred.

## Print preparation

The separate print bundle orients the support90° about Y with its spine side
toward the bed. Inspect support and tie-slot bridging in the slicer. A cover
flipped180° about X rests on its bulge roof; the surrounding main roof is
approximately50mm above that bed plane and requires explicit slicer support
planning and preview. No universal support settings or support-free print
claim is made. These remain unpowered fit-prototype parts.
