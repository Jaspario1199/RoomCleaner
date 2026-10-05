# Housing fit review — 4 October 2026 scope

Independent review executed 5 October 2026 against the existing source and exports; no source geometry or exports changed. This review separates an **unpowered, restrained housing fit prototype** from the unresolved populated local-electronics package. Housing-first work can proceed without a room survey. Jeans are the working pickup use case; the 5 lb reserve goal is not a certified factor of safety, working-load rating or demonstrated payload.

## Decision

**PASS for nominal housing fit only:** deliver the matched `base_local_station`, `cover_local_station` and `adapter_local_station` together. They can be assembled without the local electronics carrier, capacitor, fuse holder or power harness. Their added tray holes/adapter reliefs and cover panel relief do not require a populated carrier to check housing closure, mounting and removal. Leave the prototype disconnected from all power and USB, supported on the bench, with no suspended payload.

**FAIL / HOLD for a final populated local station:** the fuse-holder upper lead bend and complete restrained harness are absent. The 4.27 mm roof clearance is for the bare fuse body only. Neither nominal component clearance nor a successful housing fit closes this gate. Do not designate the carrier or assembled local station as a final print/powered assembly release.

## Inputs and independent checks

Read `CLAUDE.md`, `REQUIREMENTS.md`, `DESIGN_STATE.md`, `DECISIONS.md`, `cad/winch_local_electronics.py`, `cad/winch_slide_mount.py`, `docs/LOCAL_STATION_HARDWARE_20261004.md`, `docs/FRESH_MOUNT_RELEASE_20261002.md`, `docs/MOUNT_INTERFACE_CONTROL_20261002.md`, `docs/WINCH_SLIDE_MOUNT.md`, `docs/BENCH_PRINT_AUDIT.md` and `verification/check_homing_hardware.py`. The fresh mount document supersedes the historical dock/homing recipe.

| Check | Expected / criterion | Measured evidence | Result |
|---|---|---|---|
| Existing local audit integrity | Reported count equals rows; no unexplained overlap >=0.001 mm³ | 5,531 rows; six nonzero intersections, all documented keeper-shank engagement with carrier: four M3 at 5.466371 mm³ and two M2 at 6.974336 mm³ | PASS, existing audit evidence |
| Rebuild in memory from current source | Valid single solid for all 10 local exported parts | `make()` completed; all ten valid, one solid each | PASS, independently rerun |
| Source versus existing STEP exports | Volume and all six bounding-box coordinates agree within 0.001 mm³ / 0.001 mm | All ten reimported STEP parts agree; largest reported volume difference approximately 1e-8 mm³; bbox differences below displayed 1e-8 mm | PASS, independently rerun |
| Housing static interfaces | Pairwise intersection <0.001 mm³ | Base/cover/adapter against each other and dock: 0 mm³ | PASS, independently rerun |
| Housing/dock insertion samples | No dock intersection at +Y displacement 0, 5, 25, 60, 120, 125, 190 mm | Each base/cover/adapter sample <0.001 mm³ | PASS for sampled nominal motion only |
| Cover removal past stationary mechanism | No interference at +Z displacement 0, 1, 5, 15, 30, 60, 80 mm | Against every other part/reference returned by original station `p`: <0.001 mm³ | PASS for sampled nominal motion only |
| Housing/panel binary STL topology | Every exact-coordinate edge used twice, balanced opposite directions; flat export Zmin=0 | All four meshes: zero nonmanifold edges, zero unbalanced directed edges, Zmin=0 | PASS; triangle-edge check, not slicer/print validation |
| Fuse upper lead / complete harness | Actual insulated, restrained bend and service envelope | Not modeled or physically measured; roof minus bare-body top =70.9−66.63=4.27 mm | FAIL / HOLD |
| Actual prints / purchased components | Measured fit, retention, support cleanup and service access | No physical evidence supplied | OPEN |

The full 5,531-check script was not rerun: unchanged exports were independently compared with current in-memory source. The existing script checks local printed parts against fixed station parts, reference envelopes and hardware, sampled tray/cover lifts, and tray bolt drivers. It does not exhaustively check every printed-part pair, detailed PCB components, wires, continuous swept motion, or actual fingers/tools. No rendered visual/slicer inspection or structural test was performed in this review.

| Local part | Current bbox X×Y×Z (mm) | Volume (mm³) |
|---|---:|---:|
| `base_local_station` | 112×150×68 | 132632.6226 |
| `cover_local_station` | 112×150×68 | 130683.8307 |
| `adapter_local_station` | 135.6×149.6×20.4 | 213216.8283 |
| `microfit_input_panel` | 1.5×32×24 | 1052.7141 |
| `electronics_carrier` | 44×56.3×18 | 9363.8170 |
| `drv8825_keeper_-1`, `drv8825_keeper_1` | 17.2×6.2×2 each | 136.8816 each |
| `d24v10f5_keeper_-1`, `d24v10f5_keeper_1` | 14.7×6.2×2 each | 118.8816 each |
| `capacitor_perimeter_keeper` | 12×22×2 | 431.0692 |

Housing/panel STL triangle counts respectively: 18,808 / 7,616 / 6,292 / 1,096. STL exports only translate the source to Zmin=0; they do not establish the final support strategy.

## Include / exclude instructions

| Part / source | Disposition today |
|---|---|
| `cad/exports/winch_local_electronics/{base_local_station,cover_local_station,adapter_local_station}.{step,stl}` | INCLUDE as one matched unpowered housing set. Do not mix with older base/cover/adapter versions. |
| `wall_dock` from current `cad.winch_slide_mount.make()` / `cad/exports/winch_slide_mount/wall_dock.*` | INCLUDE for supported bench slide/lock fit, using the fresh mount hardware/retention contract. This review does not requalify dock strength or wall fixing. |
| `microfit_input_panel.*` in local electronics exports | OPTIONAL separate blank/unpowered connector-fit coupon; nominal two-circuit cutout only. Its power-only connector is experimental and does not freeze the preferred combined power/data interface. |
| Current `guide_carrier`, `outlet_backplate`, `homing_collar`, `switch_mount`, `homing_stopper`, `encoder_mount`, `encoder_node_holder`, `encoder_magnet_cup`, and the current spool geometry used by `cad.winch_bench.build()` | OPTIONAL original restricted-bench mechanism interfaces to check enclosure fit, with real retained components where fitted. This review checks cover clearance against their current source geometry; it does not issue a new complete mechanism release. Use the fresh mount assembly sequence, not obsolete sleeves/plates. |
| `electronics_carrier.*` | EXCLUDE from the main housing prototype print set; HOLD final print/populated assembly. The source permits separate restrained experimental fit coupons, but an unchanged full carrier is not needed to establish the housing milestone. |
| Four board keeper files and `capacitor_perimeter_keeper.*` | EXCLUDE from the main housing set. OPTIONAL isolated unpowered fit coupons only, after checking real board bare margins and capacitor sleeve/pad fit. |
| `local_station_assembly.step` | REFERENCE ONLY; contains component/reference/hardware envelopes and is not a print part or assembly qualification. |
| All `*_reference` bodies, plastic ring/eyelet dummy, obsolete printed sleeves, canted outlet variants | EXCLUDE from functional hardware. A plastic ring/eyelet dummy is at most a manual alignment surrogate, never a cable/load guide. No canted variant is integrated by this local-housing source. |

## Required retention and print/support warnings

Preserve these source constraints when handing over the fit prototype:

- “Do not mix the replacement base/cover/adapter with old source versions.”
- “Actual populated-board revisions must have these bare margins; if they do not, redesign the keepers instead of clamping components or solder joints.” Supports contact bare board end edges; insulating compliant edge pads are required. Direct soldered wires are modeled; tall header/socket stacks are not.
- “A compliant rim pad fills the nominal0.5mm vertical gap; do not preload the vent or cover it with a tie.” Preserve the capacitor's insulating 0.5 mm radial sleeve and Ø6 mm vent opening. “Do not force M3 into this small boss.” The capacitor keeper uses two M2×10 screws; other carrier/board/panel attachments use M3.
- The fuse body requires its locating ring and **two restraints**; free lead loops and opening force cannot be carried by contacts. The source expressly says “not released for final printing or powered assembly” until holder pose/part or actual lead routing is resolved.
- Retain switch/motor/encoder leads with insulation and strain relief, clear of spool and moving collar; do not transfer strain to switch terminals. XIAO tray requires foam and nonconductive ties. Fit carrier rear nuts before adapter if separately trialled; ordinary 2.4 mm nuts and the specified head/washer envelopes apply, not substituted nyloc nuts.
- “Base wall-facing flat surface on bed; support underside of encoder tie holes and horizontal bosses as needed. Cover front face on bed, support low internal screw shelves and inspect support removal.” The local STL Z translation alone does not implement the cover-front print orientation. Inspect the modified panel opening and relief in the slicer too.
- “Rail lips and roots, pilots and nut seats need intact layers; clearance success does not establish strength.” Critical holes may need controlled drilling/reaming; measure coupons in the actual final material/profile, without global scaling.
- “Before sliding onto the wall dock, retain the rear lock washer against the boss with a tiny temporary removable tack outside its bearing surface. Lower the case fully and install top washer/lock bolt. Unload cables before removal. Allow125mm upward travel and forward withdrawal space. Do not leave the lock out during operation.” For today's fit work the station remains supported and unpowered.
- “Fit the real Ronstan RF8090-05, never a printed ring, for cable tests.” Keep the ring/upper jaw, shoulder screws, springs, collar and KW12 cradle in the fresh assembly/service order. Actual trip must precede the 2 mm hard stop by at least 0.5 mm; source spring calculations and the 40° nominal cable cone do not demonstrate physical homing performance or room coverage.
- The enclosure provides no outboard spool bearing. Preserve D-flat/set-screw retention; do not force a hot press fit or rely on friction alone. Encoder cup/magnet centering and sensor alignment require measurements; nominal clearance is not a locating tolerance.

## Physical housing-fit acceptance still to record

With all power/USB disconnected and the station supported: inspect support removal and intact rail/nut/fastener seats; verify real fasteners seat without fouling the interior; slide/lock/unlock without binding or damage; close and remove the cover with the installed mechanism; record printed clearances and access. If trying the panel coupon, demonstrate snap-ear capture, mating latch and pull retention with the actual connector; inspect/file corners or use 1.5 mm sheet as the source allows. Do not install a powered connector/harness to close a housing-fit check.

Fuse/current coordination, harness bends/boots, purchased board retention, insulation/backfeed isolation, enclosed thermal performance, control fault behavior, structural strength/creep, actual wall fastening, room-angle compatibility and payload capability remain open. No new assumptions, purchases, structural strength claim, whole-room compatibility, powered readiness or 5 lb qualification are established here.
