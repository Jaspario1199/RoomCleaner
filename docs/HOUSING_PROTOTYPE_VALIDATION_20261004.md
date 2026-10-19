# Housing prototype: print and fit validation

**Scope: one supported, unpowered fit prototype.** This bundle lets you prototype a matched station casing, sliding dock, spool/encoder and bead-switch mechanisms before surveying the room. It is not a load rating, powered electronics release or full-room outlet. The existing circular outlet has a restricted nominal40° polar cone,360° azimuth; do not confuse those two angles.

## What is validated now

Independent packaging review passes the matched `base_local_station`, `cover_local_station`, `adapter_local_station`, supported bench dock and optional input-panel coupon at nominal dimensions. Ten existing STEP envelopes agree with current source; sampled cover/dock service paths are clear. Separate checks pass121 homing hardware/service cases,4605 encoder pedestal cases,2024 functional dock/fastener cases, and spool threading/grub/access checks. Local electronics' existing5531 nominal checks exclude full wire routes. Source dimensions are not physical fit measurements.

New archive `RoomCleaner_Housing_Fit_20261004.zip` contains current-source STL/STEP exports with a manifest and mesh/STEP checks. `PRINT_MAIN` is the housing/mechanism fit set. `OPTIONAL_EMPTY_TRAY_FIT` contains empty carrier/keepers only for an unpowered layout experiment. No reference motor/PCB/magnet/ring dummy is offered as a functional printed component.

## Print sequence

1. Print `fit_coupon`, `encoder_magnet_cup`, and `microfit_input_panel` first. Check actual magnet, screws/shoulders and purchased connector against them. The two-contact input panel is an experimental power interface; combined power/data is still to be finalized and may require replacing this small panel/cover interface.
2. Print the matched base/cover/adapter and wall dock. Use `base_local_station`, `cover_local_station` and `adapter_local_station` together; do not mix an old base/adapter with the new carrier-hole revision. Check the dock on a supported bench, including the installed positive lock. Fit the empty cover before putting expensive parts inside.
3. Print the spool, encoder mount/node holder and outlet/collar/switch parts. Assemble with the bought metal ring, real shoulder guides/springs/switch/motor and actual screws. Keep motor power disconnected; turn the spool by hand, inspect line clearance and collar reset. Exact switch trip and spring return must be measured.
4. Optionally print the empty carrier/keepers to compare PCB retention and wire routing. The current fuse-holder arrangement is **on hold for populated/powered use**:55.63mm body ends atZ66.63, roofZ70.9 gives4.27mm above body, without its14AWG wire bend. Do not force a wire against the lid or call a body-only fit complete. This experiment provides measurements for a revised carrier/fuse layout.

The supplied STLs are bed-oriented, including lid exterior down. Orientations do not guarantee support-free printing: inspect roof holes, internal ledges, nut pockets and dock rail lips in OrcaSlicer. Use intended PETG, the correct K1/K1Max profile and the filament's own settings. A0.2mm layer/5 walls/40% gyroid starting profile is for this fit experiment only; it provides no strength/creep rating. Do not scale the whole part to repair a tight hole; record the actual difference and revise the interface.

## Fit record and pass/fail

| Check | Method | Pass / fail rule |
|---|---|---|
| Coupon and screws | Compare real shaft/magnet/shoulders/screw heads/nut stack to coupon and drawings | Fits without splitting, crushing or forced board/connector insertion; record tight/loose values for revised tolerances |
| Dock and lock | Slide supported assembled empty housing in/out; install correct washer/nut/lock | Seats fully, positive lock engages; no cracking or forced prying. Geometric retention is not a proof-load pass |
| Lid/tool access | Fit lid and remove it with exact screw heads/driver; unplug connector first | No interference; all fasteners reachable and lid clears hardware |
| Spool/encoder | Rotate by hand throughout full revolution; check cup/PCB/shaft and line path | No rubbing; actual sensor gap/centering recorded. Magnetic health checks come later with controlled logic power |
| Collar/switch | Operate bead/collar by hand and monitor switch continuity | Free travel/reset with both guides fitted; switch trips ≥0.5mm before2mm hard stop. Record any binding/variant difference |
| Electronics | Empty carrier coupon, then loose actual component envelopes with power disconnected | Bare board edges supported; no keeper on solder/components/vent. Stop if real leads/boots collide or fuse bend is undefined |

Use one station first. Duplicate after real fit measurements are incorporated. Do not suspend the claw from this kit until the declared directional working/proof load and actual printed/wall joints are qualified. For a two-motor planar experiment, use an independent supported carriage/guide to constrain out-of-plane rotation; two unconstrained lines do not reproduce the four-cable robot.

## Jeans load and reserve screening

Jeans are the working payload. Weigh the chosen garment before setting that working mass;0.9kg is the old illustrative reference, not a measured requirement. Five pounds (2.26796185kg) is the requested reserve capacity to investigate, not an achieved safety factor or everyday garment requirement. Actual assembled claw mass must also be included.

With the old assumed0.45kg claw, the5lb-to0.9kg garment ratio is2.52, but the ratio of total static weights is only2.013. Comparing the static reserve case with a working case accelerated upward at2m/s² reduces that ratio to1.672, before unequal tensions, friction, torque/current limits, structural concentrations or creep. These are comparisons of illustrative demand, not measured capacity margins.

`calculations/payload_reserve_screening.py` enumerates32 symmetric equal-share demand cases (two/four axes,0/45/60/75° from vertical, static/upward acceleration) and required spool torque at10/15/20mm winding radii. Formula: `T=(m_payload+m_claw)(g+a_z)/(n cos(theta))`; torque is `T*r`. It deliberately supplies no available torque/strength rating. Two-axis equal sharing doubles per-axis tension compared with four at identical mass/angle; real moment equilibrium can invalidate equal sharing.

Actual FoS is verified component capacity divided by the applicable maximum operating demand, evaluated separately for dock, screws, guide capture, hub, line termination, shaft/bearings, clamp and extension. Motor available running torque is an operating margin with speed/current/temperature dependence, not a static material ultimate strength. Set proof-test conditions only after these directional demands, actual material/process and intended duty are established. Manufacturer PETG comparison data depends on print process and cannot be used as a K1 part rating.

Source: [Prusament PETG TDS](https://prusament.com/wp-content/uploads/2022/10/PETG_Prusament_TDS_2021_10_EN.pdf); supplier explicitly qualifies dependence on process. See independent `PAYLOAD_RESERVE_REVIEW_20261004.md` and `HOUSING_FIT_REVIEW_20261004.md` in GUIDES. The missing dimensions and load tests are commissioning inputs; they do not block the supported empty housing fit prototype.
