# Room layout — Rev B, 2026-10-14

User reports room/mount layout as 9 ft high × 11 ft × 9 ft. Adopt an 11 ft × 9 ft horizontal room envelope and 9 ft height: X=3.3528 m, Y=2.7432 m, H=2.7432 m. These are user-reported dimensions, not a surveyed anchor calibration.

Actual cable outlet coordinates, mount inset from corners, height of outlets relative to the ceiling, spool zero lengths and effector attachment offsets remain open. No runtime anchors, payload limits or homing calibrations were changed by this record.

## Preliminary length check

Assuming ideal outlets at the four upper corners and a point target at floor level:
- Corner to floor center: sqrt(5.5² + 4.5² + 9²) = 11.4673 ft (3.49525 m approximately).
- Corner to opposite floor corner: sqrt(11² + 9² + 9²) = 16.8226 ft (5.12753 m approximately).
- Previous 20 ft line-per-spool target leaves about 3.1774 ft beyond that geometric maximum for retained wraps, internal routing, terminations and other allowances. It is not yet a released cut length or validated spool capacity.

These distances are geometric checks only. Opposite floor corners need not be reachable under positive cable tensions or outlet-angle limits. Finite claw reach and attachment offsets change actual line lengths. No holding torque, load rating or whole-room access is established by these calculations.

## Power wiring consequence

The former approximately 14 ft per-station power-run estimate remains provisional. Power cables follow their chosen wall/ceiling routes from the distribution point, not the straight-line suspension geometry. Determine supply/distribution location, vertical rise, wall routing and service loops before cutting wire or confirming the 100 ft purchase quantity. The proposed 18 AWG cable is for individual branches, subject to measured current and fuse coordination, not an automatic replacement for the shared feed.


## Supply location and floor routing — user update 2026-10-14

Supply/distribution is near one corner on a 3 ft high stand. User wants remote feeds down to the floor and back up the walls. Assuming outlets at 9 ft, four upper corners, independent home-run pairs, and floor runs along the room perimeter:

| Station | Route before slack | Paired cable length |
|---|---|---:|
| Nearest | Straight up from stand: 9−3 | 6 ft |
| Across 11 ft side | 3 down + 11 along floor + 9 up | 23 ft |
| Across 9 ft side | 3 down + 9 along floor + 9 up | 21 ft |
| Diagonally opposite | 3 down + 11 + 9 along floor + 9 up | 32 ft |
| Total | Four independent pairs | 82 ft |

Add about 2–3 ft per run for routing/service slack: 90–94 ft total, before extra internal harness lengths or stand offsets. A 100 ft paired roll is plausible but close enough to measure actual routes before cutting. A floor diagonal would shorten the far run, but is not assumed because it crosses usable floor space. If the nearest run must also descend to the floor, it becomes 12 ft and total rises to 88 ft before slack.

Voltage-drop screening uses illustrative 2 A branch input current, not measured phase current or a selected fuse. At 32 ft one-way, there are 64 ft of conductor in the loop. Representative copper DCR values 6.4 ohm/1000 ft (18 AWG) and 4.2 ohm/1000 ft (16 AWG) give approximately 0.82 V and 0.54 V drop respectively, excluding fuse/contact/shared-feed resistance and temperature effects. At 1 A, these drops halve. Values are representative cable data, not qualification of the proposed Amazon spool.

The longer route changes the preference to 16 AWG stranded copper for added voltage margin, pending actual current and product resistance. 18 AWG is not automatically unusable; the prior 14 ft recommendation must be rechecked against the actual longest run. No purchase, fuse value or load rating is finalized here.

Reference DCR sources: https://www.belden.com/products/cable/audio-cable/speaker-cable/6301uh and https://catalog.belden.com/techdata/EN/5202F2_techdata.pdf .
