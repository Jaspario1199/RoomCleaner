# Housing fit prototype results

All results are for a supported, unpowered nominal fit prototype; no material/structural/thermal/room-capacity qualification.

Independent housing review: matched local base/cover/adapter geometry and sampled service paths pass. Root reran121 homing hardware/service checks,4605 encoder pedestal checks,2024 functional dock checks and spool thread/grub/access checks successfully. The existing5531 local-electronics audit remains scope-limited, excluding wire bends and actual populated PCB edges.

New kit:16 main printed parts and6 optional empty-tray parts. Every part is one valid BREP solid, STEP reimported valid, and a positive-volume watertight STL seated on Z=0. All50 manifest file hashes and ZIP integrity checked. Maximum22-part STEP volume delta0.000072432903mm³. Archive size1,824,609 bytes. No purchased metal ring or electronics dummy is presented as functional printable hardware.

A first strict STEP comparison of the spool failed when using default mass integration: apparent volume difference0.00844596mm³. Investigation recomputed both source and imported mass with explicit integration tolerance1e-7: difference1.68e-9mm³. The exporter/geometry was unchanged and acceptance threshold was not widened. Builder now uses explicit matching mass integration accuracy for all round-trip comparisons; rerun passed. The initial partial output was preserved separately and is not included in the delivered archive.

Payload screening: independent reviewer recomputed32 equal-sharing cases and96 torques.0.9kg garment/0.45kg effector remain historical illustrative assumptions;5lb is a reserve investigation. Static total-demand ratio2.013, reserve-static versus working upward-2m/s² ratio1.672, neither an achieved component safety factor. The review's stale five-pound wording finding was corrected in current REQUIREMENTS and both skeleton/priority opening updates.

Populated fuse/carrier remains HOLD:4.27mm bare-body roof gap excludes the lead bend. Optional empty carrier prints only support physical layout observations. Combined power/data connector, real switch trip, actual hardware fits, full-room angles, measured masses/COM, printed load path and actual motor torque/current/cooling remain open. User can now print coupons and the matched empty housing without a room survey.
