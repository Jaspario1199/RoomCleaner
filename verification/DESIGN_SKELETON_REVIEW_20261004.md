# Independent design skeleton review — 4 October 2026

Read-only review of `docs/DESIGN_RESOLUTION_PLAN_20261004.md`, the preliminary screening script/JSON, prior mechanical interface documents, and homing configuration. No CAD changes or physical qualification.

**Result:** the arithmetic and main architectural conclusions are sound within the explicitly ideal assumptions. One geometric wording needs correction before the front-bore screen is used as a clearance requirement.

| Claim | Independent check | Scope / finding |
|---|---|---|
| Level COM identity | Let anchor center minus platform position be Qx=2−px, half anchor spreadA=2 and body half spreadb=.069. With weightswi=Ti/Li, horizontal force balance gives sum(sxi wi)=−Qx sum(wi)/(A−b). Vertical force and pitch balance then give cx=−bQx/(A−b). Y similarly uses1.5/.064. | Signs and units correct. Requires corresponding rectangular anchors/attachments, equal anchor height, level yaw-zero rigid body, purely vertical gravity, no contact/other moment. Necessary roll/pitch balance identity; not a complete positive-tension/yaw feasibility proof. |
| `(1,1)` COM | Independently obtainedcx−.03573278094m,cy−.02228412256m. Numerical force+zero-yaw solve atplatformZ.8m yielded positive normalized tensions .172276,.321814,.385116,.634441 and all three torque residuals below1e−16 with that COM. | Confirms sign; a centered COM cannot meet this particular level pose. Does not predict tilt or establish all-workspace feasibility. |
| Orthant angles | acos(1/√3)=54.735610317°; margins55/60 are.264389683/5.264389683°. | Correct ideal full-orthant bound.60° is a study target, not a surveyed installation budget. |
| Front-bore arithmetic | 2(2.85+6.75tan60)=29.082685902mm;55°=24.979998091mm. ID26 misses60° by1.541342951mm radially. | Arithmetic correct. Calling this a conservative **finite cable** envelope is incomplete: for the same throat-edge-started centerline a Ø.6 cylinder cuts the collar plane with radial half-extent.3/cosα, not.3. At60° this gives29.682685902mm, before tolerance. A ray-only offset model is legitimate screening if labeled accordingly. |
| Rear opening | 2(2.85+10tan65)=48.590138410mm;70°=60.649548389mm. | Correct nominal radial-offset screen; same finite-cylinder projection caveat.65° sampled prototype versus70° study are properly separated. |
| Springs / homing | pairforce2×.65×(9.65−5)=6.045N;55°lineforce10.539135880N,travel3.486893591mm. | Correct ideal axial-force and displacement projection **if** bead travels on a fixed straight line and continuously pushes the translating collar. Contact normal, bead eccentricity, switch/ring friction, guide binding and changing cable angle remain unknown. Not a dependable minimum for a different contact mechanism. |
| Alignment / fuse / stop | Float.20+.15+.10=.45mm;70.9−(11+55.63)=4.27mm;speed×age examples10/5/2mm. | Correct screens. Alignment worst-case addition assumes independently unfavorable direction; fuse excludes lead bends; travel excludes buffered motion/braking. All limitations disclosed. |

## Required wording correction

Replace 'conservative throat-edge cable envelope' with 'radial-offset centerline screening envelope' unless a finite oblique tube sweep or exact constrained throat-to-collar envelope is calculated. Specify whether the cable centerline can begin at throat radius2.55 or must remain within the throat after accounting for its tilted tube section. These are different models: an actually throat-constrained straight tube can have a smaller admissible centerline start, while an edge-started tube sweep is a conservative hypothetical geometry. Do not use29.08 as a final manufacturing requirement.

## Traceability and remaining gates

- Selected detached individual homing is consistent with unset trigger/setup calibration and supported attachment commissioning. It does not authorize independent retracts of a freely hanging claw. Preserve this distinction in every station profile.
- Architecture profiles, selected candidates, nominal dimensions and purchase/measurement states remain separated. Supplier sources support component-level nominal geometry, not printed fit/rating. This review did not independently refresh live supplier pages, prices or availability.
- Canted bracket, enclosure collisions, incomplete clamp seats, secured KW cradle, actual switch mechanics and oblique bead geometry remain explicit blockers. No documentation selection closes them.
- Record uncertainty correlations and intended confidence/worst-case convention in angular, centering and load budgets. A list of individual uncertainties cannot itself demonstrate their combined margin.
- Add per-pose **yaw moment and positive-tension feasibility** to equilibrium closure; the COM identity only supplies roll/pitch necessary conditions. Also include garment-induced off-center gravity/drag and nonlevel body attachment transforms.
- Preserve source revision and qualified homing pose independently from room-motion pose. The loaded collar reaction and rope wear at the actual ring turning angle are still physical gates even if the plastic sweep clears.

No major unregistered mechanical subsystem was found beyond these refinements to existing angular, equilibrium, contact and uncertainty fields. The plan correctly treats measured loads, torque, thermal conditions, retention and creep as unresolved.

## Correction status — 5 October 2026

Rechecked the revised front expression and JSON independently: `2*(2.55+6.75*tan(alpha)+0.3/cos(alpha))` gives **25.426066168mm at55°** and **29.682685902mm at60°**. Corresponding ID26 radial margins are+0.286966916mm and−1.841342951mm. These agree with the regenerated screening output. This closes the arithmetic/projection correction for the explicitly hypothetical edge-started oblique tube benchmark; it is not a universal minimum for a throat-constrained cable, manufacturing allowance, or whole-assembly clearance proof.

The rear expression remains a **geometric conical-opening** screen, not a finite oblique-tube clearance proof. Its65°/70° nominal opening numbers remain arithmetically correct. Full positive-tension wrench feasibility, including yaw, has been added to the main plan as an independent requirement. No physical qualification is closed by these corrections.
