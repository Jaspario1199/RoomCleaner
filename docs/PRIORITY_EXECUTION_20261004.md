# Priority execution and remaining inputs — 4 October 2026 (America/Chicago)

This pass follows the existing 57-group skeleton. Each group has one primary priority below; work-package dependencies still govern implementation. Completed source/code tasks are checked off individually. No physical parameter group was closed and no whole-product print release was issued.

## Priorities and actual disposition

| Priority | Skeleton | Work / groups | Completed contribution | What still controls closure |
|---|---|---|---|---|
| P1 | W01 | Define acceptance targets and freeze build profile: P01, C06, C08 | Pin/microstep profile documented; exact synchronized transport and performance targets remain open. | User Q1/Q2; then timing/transport design. |
| P2 | W02 | Survey actual mount throats, wall and cable directions: M01, M02, M20, C01, C02, M16, M24 | Coordinate contracts fixed; motor dimensions already supplied are retained. Four-point passive attitude must be modeled. | User Q3/Q4/Q9; no invented room dimensions or COM. |
| P3 | W03 | Outlet/collar/switch coherent redesign: M03, M04, M05, M06, M07, M08, M09, M10, M18, C03 | Exact metal ring/spring/guide candidates researched. Detached homing selected; measured trigger lengths remain null. | User Q5/Q6; use survey to set angle and load envelope, then fix seats, switch cradle and cover together. |
| P4 | W04 | Spool/shaft/magnet fit and payout: M11, M12, M13, M14, M15, C04, C05 | Motor nominal interfaces and diametric magnet reference retained; no shaft-angle-to-payout shortcut. | User Q7/Q10; restrained fit, retention and bidirectional payout tests. |
| P5 | W05 | Power/retention/harness/thermal: M29, M30, M31, M32, M33, E01, E02, E03 | DRV8825 and external-power requirements rechecked. Fuse body-only clearance is insufficient for its wires. | User Q2/Q8/Q10; route real harness and coordinate fuse with actual supply/current. |
| P6 | W06 | Dock/load path/process and service: M17, M19, M21, M22, M35, M36 | Old bench exports preserved. No load rating inherited from ring strength, line label or holding torque. | User Q3/Q11; directional load cases, print coupons and restrained joint/creep tests. |
| P7 | W07 | Motion/fault configuration and synchronized execution: C07, C09, C10, C11 | Local arrival/home/tick limits exposed and validated; encoder watchdog configuration hardened. Four-axis local synchronization remains unimplemented. | Real board compile/timing; selected transport implementation; globally supported fault/recovery. |
| P8 | W08 | Claw mechanism/servo/attitude: M23, M25, M26, M27, M28, C12 | 150 mm extension, gear/rack/pad geometry and IMU gate cited; design angles are not verified servo stops. | User Q8/Q9; horn fit, stops, cloth pullout, loaded deflection and attitude tests. |
| P9 | W09–W10 | Calibrated moving camera and success evidence: M34, V01, V02, V03, V04 | Standalone explicit-pose ray/plane geometry implemented and synthetically tested. Existing delivery counting remains gated. | User Q12; actual intrinsics/pose/time/occlusion plus moving-background negative tests and integration. |
| P10 | W11 | Reconciled parts/print release: O01 | Historical order flags separated from received/tested; current candidate quantities collected below. | User Q10; release one exact hardware/software/export revision after qualification. |

## Executed in this pass

- [x] Inventoried every skeleton group into the ten priorities above; no group omitted or counted twice.
- [x] Made five local bench settings explicit in `MotionCore::Config`: arrival tolerance, arrival dwell, settle timeout, switch debounce and active tick interval. Defaults remain unchanged.
- [x] Reject invalid timing/arrival settings before local arming; exercised actual C++ core with boundary and fault tests.
- [x] Fixed host encoder configuration accepting NaN/infinite/zero/negative watchdog ages, which could defeat stale-data rejection. Reject boolean signs and invalid 32-bit epoch/sequence fields.
- [x] Added an explicit calibrated camera ray/plane projection utility, requiring actual intrinsics and per-image camera pose. No fixed-ceiling fallback or invented calibration.
- [x] Added seven cited reference values to the canonical ledger (now 22 referenced fields); retained all actual measurements as unknown.
- [x] Made the readable register show filled references and their qualifications.
- [x] Strengthened quick-value checking to compare numeric source values, not merely find an anchor string. Updated anchors after the Config refactor.
- [x] Rechecked exact selected supplier interfaces and separated component specifications from actual fit/load tests.
- [x] Consolidated candidate part quantities and unresolved inventory states below. No purchase was placed.

## Supplier research resolved at nominal-interface level

| Candidate | Exact nominal interface retained | What it settles / does not settle |
|---|---|---|
| Ronstan RF8090-05 | 5 mm ring throat, 15 mm outside, 7 mm width | Existing smooth omnidirectional guide candidate. Its retained load bracket, thin-braid friction/wear and allowed cone still require tests. |
| K&J D42DIA | Diametric N42 disk, 6.35 × 3.175 mm | Rotating magnet identity settled; actual AS5600 field/gap/centering remains unqualified. |
| Century Z-2CS | OD 6.35 mm, wire 0.508 mm, free 9.652 mm, rate 3.7 lbf/in ≈0.648 N/mm | Spring candidate identity/rate. Rounded legacy 0.65 N/mm and 9.65 mm are consistent; actual collar return/binding is unknown. Springs return the collar after the bead leaves. |
| Ondrives SHS3-12 | M3 thread with nominal Ø4 ×12 mm precision shoulder | M3-compatible guide choice. Ordinary fully threaded M3 screws are not equivalent sliding guide surfaces. |
| Pololu 2133 DRV8825 | 1/16 = MODE0/1 low, MODE2 high; genuine-board current relationship I_limit=2 VREF | Configuration/formula reference. Current setting requires actual motor rating and enclosed thermal test. |
| XIAO ESP32-C3 | External 5 V feed requires diode isolation per Seeed guidance | Power contract clarified. Disconnect external station power before USB programming; diode drop/retention remain design/test items. |

Primary sources rechecked this pass: [Ronstan](https://www.ronstan.com/us/ropeglide-ring15mm-x-5mm-x-7mmblack-1.html), [K&J](https://www.kjmagnetics.com/d42dia-neodymium-diametric-disc-magnet), [Century](https://www.centuryspring.com/shop/z-2cs), [Ondrives](https://ondrives.com/shoulder-screws/shs3-12), [Pololu](https://www.pololu.com/product/2133), [Seeed](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/). Selection is not purchase, receipt or application qualification.

## Current candidate quantities and inventory uncertainty

| Part | One-station trial | Complete four-station system | Inventory state |
|---|---:|---:|---|
| AS5600 Grove 101020692 | 1 | 4 | No current order/receipt confirmation |
| XIAO ESP32-C3 | 1 | 4 | No current order/receipt confirmation |
| D42DIA magnet | 1 | 4 | No current order/receipt confirmation |
| RF8090-05 ring | 1 | 4 | Selected; no current order/receipt confirmation |
| SHS3-12 shoulder guide | 2 | 8 | Selected candidate; no current order/receipt confirmation |
| Z-2CS spring | 2 | 8 | Selected candidate; no current order/receipt confirmation |
| KW12-3 switch | 1 | 4 | Historical reported order; actual stock/variant unconfirmed |
| NEMA17 motor | 1 | 4 | Historical reported order; supplied dimensions retained |
| Local DRV8825/regulator/capacitor/input connector | 1 set | 4 sets | Experimental local profile only; do not also purchase for central profile by default |
| XIAO-S3 Sense camera/controller | — | 1 claw | Selected; no current order/receipt confirmation |
| MPU6050 Adafruit 3886 | — | 1 claw | Selected; no current order/receipt confirmation |
| Positional MG996R-class servo | — | 1 claw | Historical reported order; matching horn/received variant unconfirmed |
| Battery and servo regulator | — | 1 set | Exact actual pack/module still unresolved |
| M3 fasteners | Per interface | See fresh parts delta | User reports M3 stock; lengths/head/washer profiles unconfirmed |
| M2 encoder screws | 3 | 12 | M2×5 required by selected PCB bosses; stock unconfirmed |

Sources: `docs/ORDER_STATUS_V2.csv`, `docs/BOM_ENCODER_TILT.csv`, `docs/FRESH_PARTS_DELTA_20261002.md`, and the experimental local hardware document. Historical webcam/old ESP32 board/USB power purchases may be reusable development equipment, but are not silently treated as the selected S3 claw parts.

## Exact questions for Jasper

Answer in the numbered format below. If a component has not arrived, say “not arrived”; that determines the next task without fabricating a measurement. No repeated request for the motor face/body/pitch/boss dimensions already supplied.

| ID | Exact requested input | Why needed / next action |
|---|---|---|
| Q1 | What is the first demonstration: restrained single-station bench, low-height four-station pickup, or installed-room pickup? What maximum dry garment mass [g] and desired pickup placement error [mm] should that demonstration accept? | Freeze P01 targets and stop treating historical 0.9 kg as qualified performance. |
| Q2 | Give the label/model and output voltage/current of the supply and identify the drivers actually in hand (A4988 or DRV8825, board vendor). For the final station, is one combined power+data cable acceptable, or must its only cable be power? | Select one electrical/control profile and avoid buying incompatible duplicate drivers/connectors. Recommended development study: wired synchronized control if a combined cable is acceptable. |
| Q3 | Give room width/depth/height [mm] and each proposed metal outlet throat XYZ from one floor corner; identify the intended wall face for A/B/C/D. Give finish thickness over each stud [mm] and whether backing is wood stud, metal stud or other. | Bound outlet directions, wall moment and actual embedment. If mounts are not placed, provide proposed stud center locations first. |
| Q4 | List furniture/fan/other obstacles as bounding boxes: Xmin/Xmax/Ymin/Ymax/Zmin/Zmax [mm] in the same room frame. Give hamper receiving opening bounds and its rim height [mm]. | Define intended workspace before widening outlet or validating paths. |
| Q5 | For the received KW12: body mounting-hole center spacing and hole diameter [mm], roller diameter [mm], roller-center XYZ relative to the body, and terminal protrusion [mm]. Can you provide a side/front photo with a ruler if these are easier? | Build an adjustable, retained switch cradle with true lever/terminal envelope. Trip force/stroke are a later fixture test, not guessed from the 5 A rating. |
| Q6 | Is the selected 120 lb braid received? Give outside width/thickness at five separated points [mm], measured without crushing it; include measurement method. Are any ring/springs/guides already ordered or received (exact SKU)? | Verify clearance/friction inputs. Cheap caliper resolution may be inadequate for braid: report observed range/method, not unjustified precision. |
| Q7 | On the existing motor, give shaft flat depth [mm] and usable threaded mounting depth [mm], or exact manufacturer drawing/model. Which spool STL/STEP was actually printed, and did it slip or bind on the shaft? | Match the magnet-cup generation to the physical spool; avoid regenerating the wrong revision. Shaft diameter/projection already have supplied nominal values. |
| Q8 | For the servo/horn: exact servo model, horn type/tooth count if specified, horn OD/thickness [mm], hole pattern [mm], and mounting-flange-to-horn underside height [mm]. For battery: label/cell count/capacity plus actual L×W×H and connector/lead protrusion [mm]. | Lock lower mechanism axial stack and upper battery retention without clamping a connector or guessing spline geometry. |
| Q9 | Have upper housing/extension/clamp parts been printed? If yes, give their exact export revision and complete effector mass [g], plus balance-point X/Y and suspended COM depth below cable plane [mm] if measurable. If no, say no and use component masses as a preliminary budget only. | Finite-body equilibrium and extension loads; near-level operation remains gated. |
| Q10 | For each current item above, reply ordered quantity / received quantity / exact SKU or label. For M3 stock, explicitly list whether M3×5 button, M3×6 grub, M3×10 button, M3×16 and M3×30 are available, including head OD/height and washer/nut thickness [mm]. | Produce a truthful remaining-order list and final fastener stack. |
| Q11 | Confirm printer (K1 or K1 Max), nozzle diameter, exact PETG/TPU filament brands and any measured hole/shaft fit coupon result [mm]. Are metal compression sleeves/wood screws already owned? Give their actual dimensions. | Set real print fit allowances and wall seat stack before structural release. |
| Q12 | Is the XIAO-S3 Sense received, and which camera sensor/revision is fitted? Can the assembled camera see all of both jaws and a held garment at the intended offset? Provide a test frame once assembled; until then the optical calibration is deliberately blank. | Qualify FOV/occlusion, then collect calibrated fiducial images and pose timing. |

## Work that remains ours after your answers

The user inputs above unlock design; they do not transfer engineering work to you. We still owe a finite-body workspace/attitude model; coherent outlet/cradle/bracket/cover redesign; fuse/harness packaging; real board compilation and synchronized transport; measured-process structural test plans; moving-camera pose/timestamp integration and background-registration evidence; and a consistent final print/order release. No numerical load or performance limit is claimed from the research-only pass.
