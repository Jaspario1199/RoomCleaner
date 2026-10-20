# Claw camera bay: independent geometry verification

Verifier: geometry-verifier (did not build the part).  Commit under review: 7f63e95.
Method: measured the SHIPPED exports (`exports/step/*.step`, `exports/stl/*.stl`), the original v6 STEP
(read through the XCAF loader, hash-checked against git HEAD) and the CadQuery module (regeneration check only).
Ray casting, ray-parity probing, wall-thickness probing and occupancy grids were re-implemented in the test file; nothing is
taken from `tests/test_claw_camera_bay.py` or `cad/mesh_tools.py`.  Nothing was repaired, committed or pushed.

Reproduce: `/usr/bin/python3 -m pytest tests/test_claw_camera_bay_verify.py -q -rxX`  (about 3 min)
Result of the final run: **30 passed, 9 xfailed (strict)**.  Each xfail is a documented finding F2..F9 that is expected to
fail until the design changes (strict mode will flag it when fixed).  The author's own suite was also re-run: 18 passed.

Frames: bay frame = v6 world minus (951.8475, 1091.1905, 1103.9899); r = -z = outward distance on the -Z side.

## 1. PASS / FAIL table

| # | Check | Expected | Measured | Tol | Status |
|---|---|---|---|---|---|
| 1.1 | v6 STEP unchanged | blob = git HEAD | sha256 c57a2c9f...e71 identical to `git show HEAD:` | exact | PASS |
| 1.2 | Combined box+bay valid, 1 solid | valid, 1 solid, 1 shell | valid, 1 solid, vol 403,721.1 mm3, 210 faces | exact | PASS |
| 1.3 | Bay body / cover valid, 1 solid | 1 solid each | 14,457.8 / 3,323.3 mm3, valid, 1 solid | exact | PASS |
| 1.4 | STEP re-import (own export, then import) | vol, bbox agree | dV 1e-12 rel, bbox diff 0.0000 mm, 1 solid | 1e-6 | PASS |
| 1.5 | Shipped exports not stale | regenerated = shipped | symmetric difference 0.0 mm3 (all three) | 1 mm3 | PASS |
| 1.6 | Preview assembly STEP | 14-1+2 = 15 solids, volumes sum | 15 solids, rel 2e-8 | 1e-6 | PASS |
| 1.7 | STL closed, volume = STEP | closed 2-manifold, dV < 0.3 % | closed (3-decimal weld); dV +0.11 %, -0.02 %, -0.01 %; box+bay and body zmin = 0 | 0.3 % | PASS |
| 1.8 | Interference bay vs other v6 parts | 0 | Griper Cylinder 0.004 mm3 (coincident-face noise; original box 0.0) | 0.01 mm3 | PASS |
| 2.1 | Removed from box = window + pilot only | 2 solids at the window and IMU pilot | 1,060.8 mm3 in two solids: window tunnel+flares 1,050.9 (|x|<=8.06, r 45..61.6, y 8.9..20.5), pilot nick 9.9 (r 62.05..63.5). Nothing on the +Z half | +-15 mm3 | PASS |
| 2.2 | Added to box = bay only | subset of shipped bay body, y<=24.4 | added 12,018.7 mm3, one solid, \|x\|<=34.9, r 50..101.2, y 0..24.4; added minus body = 0.0; nothing above the cover seat | 0.5 mm3 | PASS |
| 2.3 | Corner cable holes unchanged | D1.5, 18.24 long, wall untouched | bore area 85.916 mm2 per hole orig = comb (all 4); material in a R10 x 40 shell around each bore differs by < 1 mm3 (boolean noise); nearest added material 16.9 mm from a bore (rib), window 35.2 mm | keep-out 5 | PASS |
| 2.4 | Lid seat and rim unchanged | identical | volume above y=60, 73.7, 80: diff 0.000; rim face (y=81.2) 1949.825 mm2 and seat ledge (y=73.7) 1792.699 mm2 identical | 0.05 | PASS |
| 3.1 | Bay on narrow side | gear housing Z < X; bay on Z | housing 140.0 (X) x 80.0 (Z) x 175 (Y), centred on tube axis; bay at z = -(50..101.2) | 0.1 | PASS |
| 3.2 | Optical-axis offset | 90.0 mm from tube axis | lens window void x -7.5..+7.5, r 82.5..97.5: centre r = 90.00, x = 0; tube axis matches BAY_ORIGIN to 1e-3 | 0.02 | PASS |
| 3.3 | Lens height above floor, jaws down | 511.7 | 511.66 (lens glass y = 1093.09, lowest jaw tip y = 581.43) | 0.5 | PASS |
| 3.4 | FOV blockage claim 12.4 % | 12.4 % | 12.6 % (80x60 rays), 12.7 % (160x120); rotated sensor 15.0 % (claim 14.5); round cone 10.9 % (claim 11.0). Blockers: gear housing halves 11 %, tube 1.5 %, jaws/follower <0.1 %. Bay and cover block 0 rays | +-1.5 pt | PASS |
| 3.5 | Grasp point visible (not an authored claim) | floor between jaw tips seen | NOT visible: floor from z = -20 to +130 mm (rel. tube) is blocked by the gear housing; first visible floor point is z = -30 | n/a | FAIL (F5, design limit, disclosed by author) |
| 4.1 | Cable exits | found independently | (+-54.09, 14.05, +-54.09) bay frame, bore 18.24 long | 0.05 | PASS |
| 4.2 | Corner lines vs bay, stated range (az 0..90 in the quadrant, el 10..90) | 0 hits, >= 5 mm | 1,292 rays, 0 hits; minimum clearance 20.4 mm (author 19.17) | 5 mm | PASS |
| 4.3 | Lines aimed across the bay face | n/a | from the two -Z corners, az 312..325 deg (toward the bay), el <= 12.5 deg hit the bay (24 of 5184 swept rays); el >= 30: 7.0 mm clear, el >= 60: 16 mm | info | WARN (F6) |
| 5.1 | Wire window size | >= 8 x 6 | 10.00 x 7.00 (x +-5.00, y 12.00..19.00) constant over the 14 mm tunnel (r 45..59) | 0.05 | PASS |
| 5.2 | Wire window below lid seat | well below 73.7 | top incl. flare 20.5; 53 mm under the seat; rim untouched | 50 mm | PASS |
| 5.3 | Edge breaks | both mouths broken | 1.5 x 45 deg flare at the pocket mouth (half-width 6.45 at r 45.05); outer mouth flared to the bay cavity; roof corners chamfered 2.5 mm (5 mm flat bridge) | 0.06 | PASS |
| 5.4 | Window to corner holes | > 5 | 35.2 mm | 5 mm | PASS |
| 5.5 | Continuous wire path XIAO to box interior | free route | straight sight line at (x=0, y=15.5) from r=44 to r=99; with XIAO block, IMU board and cover as obstacles the widest sphere that travels from the XIAO neck edge / headroom to the pocket is 3.5 / 3.0 mm | >= 3.0 | PASS (small bundle only) |
| 6.1 | XIAO cradle clearance | 21.6 x 18.4 void (21.0 x 17.8 + 0.3/side) | exact 21.60 x 18.40; 21x17.8x15 block clears for shifts +-0.25, collides at +0.35 | 0.02 | PASS |
| 6.2 | Lens window size and alignment | >= 14 x 14, centred over lens | 15.00 x 15.00, centred on board centre; Ø8 x 4.5 barrel clears for lens offsets up to 3.4 mm; hood rays clipped 0; support ledge 1.7 mm radial, 3.3 mm along X | n/a | PASS (lens position assumed, F7) |
| 6.3 | USB-C window reachable, 12 x 7 plug | 0 interference | 12 x 7 plug: 6.1 mm3 interference; 12 x 6.5: 4.5; 12 x 6: 3.1; 11 x 6.5: 2.0; 10 x 6: 0.13; only <= 8.5 x 7 or ~10 x 6 passes | 0 | FAIL (F2) |
| 6.4 | IMU posts vs GY-521 holes | hole pitch fits the board | posts at x=-8.0, r = 63.1 / 78.3 (pitch 15.2) on a 15.6 mm wide board: hole centres 0.2 mm from the board edge | edge >= D/2+0.5 | FAIL (F4) |
| 6.5 | IMU posts intact | both reach seat height 8.4 | post 1 cut by the window outer-flare cutter: top height 6.2..7.9 on the outboard half, 36 % of ring contact (12.9 of 36.1 mm2); post 2 28.0 mm2 | 80 % | FAIL (F4b) |
| 6.6 | Repo-selected IMU fits | Adafruit 3886 26 x 17.8 x 4.6 | docs name Adafruit 3886; does not fit the neck in either orientation (339 / 251 mm3 interference) | 0 | FAIL (F4c) |
| 6.7 | Cover screws / inserts | M3 heat-set boss | boss OD 9.0, insert hole D4.0 x 6.0 deep, 3.0 mm to cavity, 2.5 mm outer wall; cover holes D3.4 coaxial; cover vs bay interference 0; cover-to-box gap 0.33 mm | n/a | PASS (insert depth margin only 0.3 mm, F8) |
| 6.8 | Min wall >= 2.0 (inward-normal probe, 1,593 facets) | >= 2.0 | cover min 2.00 (PASS). Bay: USB-window lintel 1.10 mm; pilot-2 to fence face 1.45; IMU post-1 sliver <0.3 | 0.05 | FAIL (F3, F4) |
| 6.9 | Overhangs > 45 deg, bridges (box+bay, +Y up) | none unsupported | only flat roofs: USB window flat 8.5 mm, wire window flat 5.0 mm, vent/tie slots 2 mm; sloped down-faces < 80 mm2 total (window flares, 34 deg over 0.5 mm) | 10 mm bridge | PASS |
| 6.10 | Cover print orientation | flat either face down | cover has pegs 2.7, lip 1.0 below and rails 1.5 above; neither face sits flat; STL is at z 21.7..28.3 (not on bed) | n/a | FAIL (F9, minor) |
| 7.1 | Cantilever stiffness, 1 g + 2 m/s2 | << 12.5 MPa | section r=64: A 284 mm2, Ix 12,274 mm4, Iy 97,742 mm4. Outboard mass 28.6 g (14.4 bay + 3.7 cover + 5 XIAO + 2.5 IMU + 3 wiring, last three assumed) at arm ~21 mm: 0.008 MPa | 12.5 | PASS |
| 7.2 | 10 N tip load, vertical / lateral | < 12.5 MPa | tip arm 37.2 mm, M = 372 N.mm: vertical 0.49 MPa (x3 stress concentration = 1.5), lateral 0.11 MPa (0.34); tip droop 0.007 mm (0.016 deg) | 12.5 | PASS |
| 7.3 | Added mass | small | net 18.2 g solid (13.9 bay net of window + 4.2 cover); gross 19.5 g; author "about 18 g" confirmed | 30 g | PASS |

## 2. Ranked findings (for the lead; nothing was repaired)

**F2 (HIGH, FAIL): USB-C window blocks a 12 x 7 plug.**  Window 12.5 x 7.0, 45 deg roof chamfers 2 mm, so width at the
roof is 8.5 mm.  Interference with a 12 x 7 rectangular overmold is 6.1 mm3; even 12 x 6 collides (3.1).  Window height equals
plug height (no vertical play).  Evidence: `test_usb_window_passes_12x7_plug` (xfail), `test_usb_window_geometry`.
Options: open-top U-notch through the wall top closed by the cover (removes F2 and F3 together), or taller window with
the chamfers above the plug height.

**F4 / F4b / F4c (HIGH for the IMU mount): three independent IMU defects.**
 (a) Hole pitch 15.2 across a 15.6 mm board width leaves 0.2 mm edge distance for a D3 hole: impossible.  A 15.2 pitch is only
 feasible along the 21 mm axis (2.9 mm edge distance); the posts may be rotated 90 deg relative to the real board.  I could not
 find GY-521 hole coordinates in the repo; assumption: typical GY-521 about 20.5-21 x 15.5-16, holes on the long axis.  Calipers needed.
 (b) Post 1 (r = 63.1) is truncated by the wire-window outer flare cutter (loft to 22 x 19 at r = 66, y from 6.0): the post top is
 6.2..7.9 on the outboard half, only 36 % of the ring reaches 8.4, a 0.75 mm sliver remains at r 66.0..66.65, and pilot hole 1
 opens sideways above y about 6.2 (about 3.8 of 6 mm thread engagement).  The board will rock on post 2 plus a partial post 1.
 (c) `docs/` and the BOM select the Adafruit 3886 (26 x 17.8 x 4.6), not a GY-521; it does not fit the 21.6 x 15.6 neck.
 Also pilot 2 leaves only 1.45 mm to the fence face (r 79.35..80.8).

**F5 (MEDIUM, design limit, already disclosed by the author): the camera does not see the grasp point.**  The gear housing
(Y 654..829, Z 1064..1144) hides the floor from z = -20 to +130 mm about the tube axis, including the whole zone under the jaw tips
(x +-40, z -13..+7).  First visible floor is 30 mm from the tube axis on the camera side.  The ground is seen (87 % of rays reach it),
laundry heaps beside the claw are visible, the grasp target is not.  Not fixable by moving along the side; inherent to a
narrow-side mount under a 175 mm tall housing at this FOV.

**F3 (MEDIUM, FAIL): minimum wall.**  USB lintel 1.10 mm (y 23.3..24.4); pilot-2 to fence 1.45 mm; post-1 sliver.  The cover
meets 2.0 everywhere.  Lens seat ledge 1.7 mm radial is a support ledge, not a wall, but is the board's only support.

**F7 (MEDIUM, unverified inputs): XIAO and lens assumptions.**  `docs/SELF_CAD_DIMENSIONS_AND_WIRING_20261006.md` records the OEM model
as 24.363 x 17.78 x 13.96; the cradle is 21.0 x 17.8 x 15.0 (3.4 mm shorter in X).  If 24.363 is a true X length, 411-417 mm3 of
it lands in the cradle walls.  Lens centred on the board (CAMBAY_LENS_DX/DR = 0) is an assumption; the 15 x 15 window tolerates
+-3.4 mm of error so a real offset is likely survivable.  Measure the real board before printing.

**F6 (LOW): cable-line boundary.**  Stated range passes (0 hits, 20.4 mm).  A line leaving a -Z corner hole aimed across the bay
face (azimuth about 35 deg past the corner quadrant, elevation <= 12.5 deg) does hit the bay; at >= 30 deg elevation clearance is 7 mm.
Only relevant if the cable-to-anchor pairing can cross the claw at very shallow elevation (claw near ceiling, far anchor).

**F8 (LOW):** insert hole is 6.0 deep for an M3 x 5.7 insert (0.3 mm melt-in reserve; usual practice is >= 0.5-1.0).
**F9 (LOW):** cover STL is at z 21.7..28.3, not on the bed, and the docstring claim "flat on the bed, either face down" is not true
(pegs and lip under, rails above); needs supports or a re-orientation.
**F10 (INFO):** bay plus electronics is about 28.6 g outboard at r about 80 mm: static CoM shift about 5 mm for a 450 g claw (assumed
mass), a lean of order 1 deg if the CoM sits roughly 250 mm below the cable plane (assumed); the optical axis leans with it.
**F11 (INFO):** footprint grows to 127 x 164.7 mm (bed >= 170 in the bay direction); wire bundle bottleneck is 3.0-3.5 mm (3 mm headroom above the XIAO, cover on).

## 3. What was checked and found sound

- Corner-hole bores, lid seat and the continuous top rim are bit-identical to the original; no volume added or removed within 16 mm of a hole.
- Window sits 53 mm under the lid seat, 35 mm from the nearest corner hole, size and edge breaks as designed.
- STEP, STL and preview assembly are current with the module and round-trip cleanly.
- FOV, lens height, mass, cantilever I and cable-clearance claims reproduce within tolerance.  The structure is far stiffer than needed.

Files: `tests/test_claw_camera_bay_verify.py`, `verification/claw_camera_bay_verification.md`.  No other repo files were modified.
