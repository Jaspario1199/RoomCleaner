# Independent payload reserve review — 4 October 2026

Reviewed `calculations/payload_reserve_screening.py`, its committed JSON output, CR6/CR13 in `REQUIREMENTS.md`, and `docs/FRESH_STRUCTURAL_REVIEW_20261002.md`. This is a numerical and assumption review, not physical qualification or a capacity rating.

## Result

**PASS — illustrative equations, units, case coverage and reported ratios.** Independently recomputed all 32 tensions and all 96 spool torques from the committed JSON without executing the generator or changing its output. Relative tolerance was 1e-12; maximum absolute tension residual was 0 N. The 32 unique cases exactly cover 2 payloads × 2 cable counts × 4 angles × 2 accelerations.

**OPEN — actual capacity, achieved factor of safety and four-axis margin.** These are not established by this calculation or by a supported two-motor planar carriage test.

## Equations and units

Under symmetric equal sharing, vertical equilibrium is `n T cos(theta) = (m_payload + m_effector)(g + a_up)`, so `T = (m_payload + m_effector)(g + a_up) / (n cos(theta))`. Mass is in kg; g=9.81 m/s² and upward acceleration is 0 or 2 m/s²; theta is measured from vertical and converted from degrees to radians. T is per cable in N. Required spool torque is `T r`, with the tabulated radii 10/15/20 mm divided by 1000 to obtain metres and torque in N·m.

The calculation assumes all n cables are taut at the same angle, carry the same tension, and their horizontal forces cancel. The applied total mass accelerates together vertically. It omits off-centre centre-of-mass moments, attitude dynamics, unequal angles/tensions, pretension, friction, cable/spool/drivetrain inertia, drag, snag and faults. The `axes` field must be interpreted as the number of equally load-bearing cables for this calculation; motor count alone does not establish it. These are ideal illustrative demands, not guaranteed worst-case interface demands.

The 5 lb reserve converts to 2.26796185 kg. The jeans reference 0.9 kg and effector reference 0.45 kg remain provisional assumptions; weigh the actual representative jeans and complete extended effector. Five pounds is the requested reserve investigation, not the normal working garment load.

## Ratio checks

| Comparison | Independent result | Meaning |
|---|---:|---|
| Reserve payload / jeans reference, excluding effector | 2.519957611 | Payload mass ratio only |
| Static reserve total / static working total | 2.013305074 | (2.26796185+0.45)/(0.9+0.45) |
| Static reserve total / working total accelerating upward at 2 m/s² | 1.672355866 | 2.013305074 × 9.81/11.81 |

Static working force is 13.2435 N; static reserve force is 26.6632057485 N; working force at +2 m/s² is 15.9435 N. The ratios apply to cable tension and spool torque only when cable count, angle, effective spool radius and load-sharing assumptions are the same in the compared cases. With acceleration equal on both sides, the total-load ratio remains 2.013305074. None of these ratios divides a verified failure/allowable capacity by working demand, so none is an achieved factor of safety.

Useful cross-checks: changing two equally loaded cables to four halves each ideal tension; a 60° angle doubles tension relative to vertical; +2 m/s² multiplies static tension by 11.81/9.81. Tabulated tension spans 3.310875 to 62.0107562714 N, with the maximum at reserve payload, two cables, 75°, +2 m/s². At that maximum, 20 mm spool torque is 1.24021512543 N·m. The historical 40 N cable constant therefore does not bound all screened cases and cannot serve as a measured limit.

## Why a two-motor supported planar test does not establish four-axis margin

A support or carriage rail can carry weight and moments that four suspension cables must carry in the installed system. Test cable count does not by itself describe the gravity load path. The support reactions must be measured or accounted for before a planar result can be compared with this suspended equal-share calculation.

A planar test can investigate the tested housing, payout/encoder behavior and bounded motion under its recorded load and angles. It does not establish four-station spatial tension allocation, positive tension across the workspace, attitude control, unequal cable demand, extended-effector COM/inertia, coordinated fault response, actual wall/backing interfaces, or room-wide outlet angles. Four-cable equal sharing is a conditional mathematical result, not an extrapolation rule from a two-motor test.

The structural review also requires local guide reaction `G=T(u_to_spool+u_external)`, which can approach 2T, and whole-station external cable force approximately `T u_external` plus station weight. Guide and spool internal forces must not be added as separate external wall loads. These reactions, moments and weakest interfaces require separate checks; a payload mass ratio does not qualify them. The listed unverified holding torque is not actual running torque at the test current, speed, temperature and spool radius.

## Needed follow-up

No numerical fix is needed in the screening script or JSON. Keep the illustrative scope and no-capacity wording.

One documentation inconsistency needs correction outside this review's edit scope: the opening update in `docs/DESIGN_RESOLUTION_PLAN_20261004.md` calls 5 lb the target payload and says the earlier 0.9 kg target is superseded. Align that wording with CR6: jeans are the working payload to weigh; 0.9 kg is provisional; 5 lb is reserve to investigate.

Before any load or margin claim, establish measured masses/COM, actual cable geometry and force distribution, acceleration/fault demands, effective spool-radius envelope, running/holding torque and the weakest load-path interface. Perform the physical qualification specified by the structural review on the exact assembly/material/process/hardware revision. No physical load tests, capacity qualification or CAD edits were performed in this review.
