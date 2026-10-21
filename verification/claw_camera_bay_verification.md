# Claw camera bay: independent geometry verification

# ROUND 3 (newest): IMU removal, 23.0 x 18.6 cradle, lens window at the USB-C end, D28 tube cut (commit 769d4e4)

Verifier: geometry-verifier (did not build the part).  Measured the SHIPPED exports (`exports/step/*.step`, `exports/stl/*.stl`) with my own
ray casting, solid booleans and occupancy grids (tests/test_claw_camera_bay_verify.py); previous export and preview taken from `git show 1c2e968:`.
Nothing was repaired, committed or pushed.  Frames as before (bay frame = v6 world - (951.8475, 1091.1905, 1103.9899); r = -z).
Reproduce: `/usr/bin/python3 -m pytest tests/test_claw_camera_bay*.py tests/test_gripper_v7*.py -q -rxX` (about 15 min; the verifier file alone 5 min).

**Verdict: PASS WITH CONDITIONS.**  Of the ten claims, 1, 4, 5, 7, 8, 9 and 10 reproduce fully; 2 (ribs), 3 (window tolerance) and 6 (walls) carry the two findings:
R3-F1 (MEDIUM, FAIL): the shipped body/housing export is stale against `cad/parts/claw_camera_bay.py` (locating ribs; details below);
R3-F2 (LOW, shortfall): the lens window does not reach the +-4 mm tolerance everywhere.  Everything else reproduces within tolerance.

## R3.1 Claim by claim (expected vs measured)

| # | Check | Expected | Measured | Tol | Status |
|---|---|---|---|---|---|
| 1 | IMU removed | no IMU pocket/pad/peg/vent, no CAMBAY_IMU_*, bay ends r 101.3 | no `CAMBAY_IMU` in params.py or the part; housing/body/cover bbox r max 101.30; 0 mm3 of any part beyond r 101.4; no R1.05 post/pilot cylinders; cover has only the 4 cradle-corner pegs. The 3 XIAO airflow slots in the -X cradle wall (r 84.5/90/95.5, y 10.9..18.9) remain by design (not IMU vents) | 0.01 | PASS |
| 2a | Pocket | 23.0 x 18.6 | x -11.5..+11.5 = 23.00; r 80.7..99.3 = 18.60 | 0.02 | PASS |
| 2b | Cavity height | >= 16 (claimed 17.0) | seat y 9.9 (block top), cover underside 26.9 -> 17.00 above the seat.  Only the four 2.4 mm cover pegs drop to 11 above the seat at the corners | 0.01 | PASS |
| 2c | Four 0.4 mm ribs | 4 ribs, 0.4 proud, 17.8 between | 4 ribs (2 per long wall), pocket 17.8 between them (r 81.1..98.9), 0.40 proud.  BUT positions/widths differ from the module (see R3-F1) | 0.01 | PASS (count, height) / FAIL vs module |
| 2d | Board fit | 21 x 17.8, ~15 mm stack fits | 21 x 17.8 (+1.5 USB overhang) x 7 mm above the seat (nominal stack, camera 8 mm in the window): 0 mm3 with housing and cover.  A full 15 mm above the seat fits the housing (0 mm3) but touches the cover pegs (56 mm3; not the real arrangement).  Width 18.0 squeezes the ribs (3.4 mm3, by design).  Play: +-0.25 mm in X, 0 radially (snug).  23.2 long board collides (11.4 mm3) | 1e-3 | PASS |
| 3a | Lens window | 14.25 x 16.4 at the USB-C end | x -3.25..+11.0 = 14.25 (centre +3.875, USB-C end), r 81.8..98.2 = 16.40 centred on r 90.00; 1.0 mm chamfer at the bottom mouth; 2.5 mm wall to the +X outside above the chamfer | 0.02 | PASS |
| 3b | Window vs lens shifts (lens centre x 4.75, r 90) | D8 barrel and 8.5 module clear for -3.9/+2.25 in X, +-3.9 in R | D8 barrel limits: X -4.00 / +2.25, R +-4.20.  8.5 module: X -3.75 / +2.00, R +-3.95.  Claim holds for the barrel (and R for both); the 8.5 module is 0.15 (X-) and 0.25 (X+) short of the claimed values | 0.03 | PASS (barrel) / FAIL (module X) |
| 3c | +-4 mm everywhere | +-4 in X and R | Shortfall vs 4.0: barrel +X 1.75; module X- 0.25, X+ 2.00, R 0.05.  The +X cap does NOT matter: the board has 0.25 mm slack in the pocket and the module cannot overhang the board end (lens centre >= 4.25 from the end, nominal 5.0), so the lens cannot move more than about +1.0 mm toward +X; the window gives +2.0 | n/a | FAIL (R3-F2, harmless in X+) |
| 4a | USB-C notch | 15 wide, sill 0.4 above the seat, closed by the cover | width 15.00 (r 82.5..97.5, centred r 90.00) constant from the sill to the wall top, through the whole +X wall (x 11.5..13.5); sill y 10.3 = 0.4 above the seat; wall top 26.9 = cover underside, cover plate 26.9..29.3 roofs the notch | 0.02 | PASS |
| 4b | Plug 12 x 6.5 reaches the receptacle in place | 0 interference | Overmould front at the receptacle face x = 11.25, 12 x 6.5 plug: 0 mm3 with housing and cover for plug centre y 13.55..22.65 (receptacle nominal 15.3 -> margin -1.75 / +7.35 mm, i.e. the plug centre must be >= 3.65 above the seat), lateral +-1.5 mm.  12 x 7: 13.80..22.40; 13 x 8: 14.30..21.90, lateral +-1.0.  8.94 x 3.26 receptacle clear.  Open assumption: receptacle centre height (stack top - 1.6) is still unmeasured | 1e-4 | PASS |
| 5 | Unchanged vs 1c2e968 | corner holes, lid seat, rim, wire window | differences vs the previous export lie only inside the bay zone (|x|<=36, r 50..131, y<40): 0.00 mm3 outside; nothing above y 27 and nothing on the +Z half; wire window removed volume 1050.94 mm3 both, symmetric difference 0.0; bore areas of all 4 corner holes identical (85.916 mm2); lid seat (1792.699 mm2), rim (1949.825 mm2) and volume above y 60/73.7/80 identical; nearest added material to a bore 16.76 mm | 0.01 | PASS |
| 6 | Walls | >= 1.2 (claimed min 1.6 at ribs) | 1,552 bay facets + 1,408 cover facets (inward-normal probe, no exclusions): every wall except the ribs >= 1.999 mm (cover 1.999).  Ribs in the SHIPPED export: 1.2 mm wide at x = -8.0 and a free-standing fin only 0.5 mm thick (0.4 proud + 0.1) at x = -1.0, 8 mm tall, in the |x| < 4 wire gap with no wall behind it.  Module would give 1.6 mm ribs backed by the fences | 0.02 | FAIL (R3-F1) |
| 7 | STEP round trip | single valid solid, bbox and volume agree | housing 404,199.15 mm3, body 14,984.04, cover 3,597.63: valid, 1 solid, 1 shell; re-import volume diff < 1e-6 relative, bbox diff < 1e-4 mm; STL closed 2-manifold, volume within 0.3 %, z min 0 | 1e-6 | PASS |
| 8 | Mass | 19.1 g (was 28.7) | PETG 1.27 g/cc: bay net of the window cut 14.56 g + cover 4.57 g = 19.12 g (gross of the window 20.46 g) | 0.2 g | PASS |
| 9a | D28 tube | GRIPV7_TUBE_LEN 254.8; lower end 786.39, top 1041.19 | param 254.8 (V6 304.8, cut 50.0); preview tube 786.390 .. 1041.190 = 254.800, axis x 951.8475 z 1103.990; volume down by annulus x 50 (12,035 mm3) | 0.01 | PASS |
| 9b | Only four parts moved | tube shortened, cylinder, box+bay, cover down exactly 50.0 | 55 of 59 preview solids bit-identical (bbox < 1e-4 mm, volume); the cylinder moved -50.0000 rigidly; box+bay and cover equal the CURRENT exports shifted -50.000 in y (symmetric difference 0.0 mm3) | 1e-4 | PASS |
| 9c | No interference moved vs head/tube | none new | Touching pairs identical to the previous preview: tube/cylinder 0.037 mm3, cylinder/box 0.004 mm3 (coincident faces); cover and bay touch nothing; box bottom plane = tube top = y 1041.19 | 0.05 | PASS |
| 9d | Lens position and height | (956.60, 1043.09, 1013.99); 462.06 above the lowest tip (581.03) | lens (956.5975, 1043.0905, 1013.9899); lowest closed-jaw point of the v7 head y 581.034; height 462.056 mm.  (v6 frame, bay unmoved: y 1093.09, 511.66 above the v6 tip 581.43; v6-frame FOV blockage test still within 12.4 +-1.5 %) | 0.01 | PASS |
| 10 | Cable-line clearance (az 0..90, el 10..90, stated range) | earlier 19.25 | min 20.67 mm (1,292 rays per corner, 0 hits); corner hole mouth to the bay solid 21.43 mm (21.37 before) - the closest features are the gussets and columns near the root, so the shorter bay changes nothing.  Realistic lines (yaw about the installed orientation): 0 hits at |yaw| <= 30 deg in all four installed orientations (round 2: 2 hits at +-30); +-45: 5 hits (installed 0/180) / 7 (90/270) (round 2: 7); +-60: 3 / 8 | 5 mm | PASS (F6 narrowed to |yaw| >= 45) |

## R3.2 Findings

**R3-F1 (MEDIUM): the shipped body/housing export is stale against the module.**  `cad/parts/claw_camera_bay.py` builds the locating ribs at
x = -8.0 and +7.0, 1.6 mm wide (both clear of the |x| < 4 wire gap).  The export has them at x = -8.0 and -1.0, 1.2 mm wide: regen-minus-export 12.8 mm3 and
export-minus-regen 8.64 mm3, nothing else differs (cover export identical).  The x = -1.0 pair is a 0.5 mm free-standing fin (0.4 proud + 0.1 buried, 8 mm tall) that
narrows the wire gap and is below the 1.2 mm minimum wall; the author's suite passes because it tests the module, not the export.
Repair is a re-export only (no design change).  Evidence: `test_exports_not_stale`, `test_min_wall_1p2_everywhere_including_ribs` (both xfail strict), `test_rib_defect_is_confined_to_the_stale_ribs`.

**R3-F2 (LOW): lens window tolerance.**  The window follows the stated +-4 mm for the D8 barrel in X- and R only.  Shortfalls are in R3.1 3c.  The X+ cap (0.5 mm short of
the pocket end wall) is physically harmless as computed; the real exposure is the -X/R direction for the 8.5 mm module (0.25 / 0.05 mm) and the unmeasured lens position itself.

**Observations (no action needed):** the Seeed ruler photo (xiao_esp32s3_top_seeed_ruler.png) shows the USB-C receptacle overhanging the board edge by about 1.7 mm and the board
without the USB about 20 mm (scale read at 150 px/cm, +-0.5 mm); so the "21 mm" most likely includes the receptacle and the 21 + 1.5 envelope in the 23.0 pocket is conservative.
Camera protrusion 8 mm, receptacle height and lens position remain ASSUMED (VERIFY with calipers before printing).  Wire bundle: widest sphere from the neck to the box pocket 6.99 mm (was 3.5).

## R3.3 Test-file changes (tests/test_claw_camera_bay_verify.py, tests/test_gripper_v7_verify.py)

Constants changed only after my own measurement above: export volumes (404,199 / 14,984 / 3,598), added bbox r <= 101.3 and y <= 26.9, lens window x -3.25..11.0 and 16.4, lens x +4.75
and heights (v6 511.66; v7 preview 462.06 added), cradle 23.0 x 18.6, seat 9.9, notch/sill/plug tests (15 wide, y 10.3, centre 15.3), boss x 16.55 / hole bottom 19.9, cover top 29.3, section Ix 15,369,
mass 19.1 g, minimum-wall test split (non-rib walls >= 1.95 pass; the rib defect is a strict xfail), IMU tests replaced by `test_imu_removed`, F6 yaw test moved from +-30 (now passes, all 4 orientations) to +-45 (strict xfail).
New: lens shift limits, plug passage ranges, unchanged-regions vs previous export, four D28 preview tests.  No assertion was weakened to hide a failing measurement.
`test_gripper_v7_verify.py`: `_tube()` now searches 254.8 mm (the v6-STEP call passes 304.8).

Final runs: `tests/test_claw_camera_bay.py` 19 passed; `tests/test_claw_camera_bay_verify.py` **61 passed, 6 xfailed** (strict: F5 grasp point hidden, R3-F1 x2, R3-F2, F6 at +-45 x2);
`tests/test_gripper_v7.py` 34 passed and `tests/test_gripper_v7_verify.py` 72 passed (106 total).

---


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

---

# ROUND 2: re-verification of repair round 1 (commit 5b7764d)

Same rules as round 1: shipped exports measured, own ray casting and probing, nothing repaired or committed.
Reproduce: `/usr/bin/python3 -m pytest tests/test_claw_camera_bay_verify.py -q -rxX` (about 3.5 min).  Author's suite re-run: 18 passed.
Final run: see the status line at the end of this section.  Round-1 findings F2, F3, F4, F4b, F4c, F7(envelope), F8, F9 are re-checked below;
F5 (grasp point hidden) and F6 (lines at shallow elevation) remain.

## R2.1 Results table

| # | Check | Expected | Measured | Status |
|---|---|---|---|---|
| 1 | Exports valid, one solid each; v6 STEP unchanged | valid, 1 solid | box+bay 408,848.1 mm3, body 19,603.6, cover 6,515.4 mm3, all valid, 1 solid; v6 blob = git HEAD; regeneration vs shipped 0.0 mm3; STEP round-trip exact; STL closed | PASS |
| 2 | F2 USB-C open notch, 13 x 8 overmold + cover | no interference | notch x 12.48..14.48 through the +X wall, width 13.50 (r 83.25..96.75) constant to the wall top, sill y = 14.26, no roof. 13 x 8 and 12 x 7 plugs (x >= 12.6, outside the wall): 0 interference with box+bay, cover and all other v6 parts. Plug top 22.76, cover lip underside 23.36 (0.6 mm) | PASS |
| 2b | Plug position tolerance | not specified | lateral play is only +-0.25 mm (r offset +-0.2 passes, +0.4 hits the notch wall 12 mm3); vertical -0.5 / +0.6 mm. USB-C height (1.6 below envelope top) is still an assumption | WARN (R2-W1) |
| 3 | XIAO cradle 24.963 x 18.4 for the 24.363 x 17.78 x 13.96 envelope | 0.3 mm per side | exact void 24.962 x 18.400; envelope clears for shifts +-0.25 (0 interference with box and cover), hits at +0.35 (8.3 / 13.6 mm3); headroom 4.0 mm to the cover seat | PASS |
| 3b | Lens window 17 x 16 and tolerance | >= 14 x 14, +-3.2 | 17.00 x 16.00 centred on r = 90; D8 x 4.5 barrel clears for offsets up to 4.4 mm (X) and 3.9 mm (r), hits at 4.6 / 4.1; hood rays clipped 0; FOV blockage unchanged 12.6 / 12.7 % (bay and cover block 0 rays); lens height 511.66 mm | PASS |
| 3c | Board seat under the envelope | support ledge | radial bearing of the 17.78 board on the block is only 0.89 mm per long edge (window edge at r 82.0 / 98.0, board edge 81.11 / 98.89); 3.7 mm along X | WARN (R2-W2) |
| 4 | Adafruit 3886 IMU pocket outboard of the XIAO | board fits, rigid | pocket 18.40 x 26.60 (r 101.2..127.8) for the 17.8 x 26 board (0.3 per side); 4 pads 3 x 3 x 1.0 at y 3.4 (36.0 mm2 measured), side blocks to y = 8.0, PCB-only envelope and 4.6 mm envelope clear of the body (0 interference), no screw posts/pilots left; 4 cover pegs 3 x 3 end 0.2 mm above the PCB (36 mm2 at y 5.2); two zip-tie loops at r = 107.5 / 121.5, pit 4.4 wide, floor slot 1.8 x 3.8 | PASS |
| 4b | IMU rigidity | no rattle | board play +-0.3 mm in plan (about +-0.7 deg about the board normal, irrelevant for tilt), vertical play 0.2 mm (0.4-0.6 deg tilt) unless the zip ties are tightened; the cover pegs act through a cover held by two screws near the root, so the far end only floats 0.2 mm above the PCB. Corner pegs sit on 4.6 mm component envelope corners (100.8 mm3 interference of the cover pegs with the full 4.6 envelope); hole/component-free corners are an UNVERIFIED assumption | WARN (R2-W3) |
| 4c | IMU wire route to box | free | widest sphere IMU pocket -> box pocket 3.0 mm (limited by the 3.5 mm gap over the partition, top 20.86); XIAO -> box 3.8 / 4.0 mm | PASS |
| 5 | Min wall >= 2.0, own sampling (inward-normal rays, 1,787 bay facets without any near-box-wall exclusion, 1,496 cover facets) | >= 2.0 | bay 1.989, cover 1.999 (tessellation noise). Axis-run scan in x, y, r: no solid run < 1.95 mm except the 0.35 mm convex corner tip where each gusset rib start pokes out of the wall (x 14.48..14.83, r about 76.9, 18 mm tall, cosmetic) | PASS |
| 6 | Insert bosses D4.1 x 7, OD 9.1 | as stated | hole 4.10 dia, bottom at y = 17.36 (7.00 deep from the 24.36 seat, 1.3 mm over a 5.7 insert); boss OD 9.10, outer wall 2.50, 3.00 mm to the cavity; cover holes 3.40 coaxial (x = 17.53) | PASS |
| 7 | Cover flat face / STL on bed | flat outer face down | STL zmin 0.0000; bed contact 2178.6 mm2 = the whole flat outer face (2178.7); 0 overhang facets in the print orientation (lip, pegs, corral up); cover to original box gap 0.33 mm; no interference with box+bay | PASS |
| 8 | Cantilever, tip now at r = 129.8 | << 12.5 MPa | section r = 64: Ix 12,713 mm4, Iy 102,832; outboard mass 39.1 g (20.9 bay + 7.7 cover + 10.5 assumed electronics); weight + 2 m/s2: 0.016 MPa; plus 10 N at the tip (arm 65.8): vertical 0.84 MPa (x3 = 2.5), lateral 0.18 (0.53); droop 0.036 mm, 0.046 deg | PASS |
| 9 | Mass | small | net added 28.7 g solid (20.5 bay + 8.3 cover), up from 18.2 g (+10.5 g); 38.7 g with electronics | PASS (watch) |
| 10 | Everything else unchanged | as round 1 | removed material now only the wire window, 1,050.9 mm3 (pilot nick gone); corner holes, lid seat and rim unchanged (volumes, areas, bore areas identical); cable-line stated range (az 0..90, el >= 10): 0 hits, min clearance 20.6 mm; window 10 x 7, 53 mm under the seat | PASS |
| 11 | Realistic cable lines at 0, +-15 deg yaw | 0 hits | own implementation, 4 installation orientations (0/90/180/270): 1,344 feasible lines each, 0 hits, min clearance 21.2 (0), 19.4 (+15), 20.1 (-15) | PASS |
| 12 | Realistic cable lines at |yaw| >= 30 deg | 0 hits | 2 hits at +-30 (min clearance 0.1-0.2 mm), 7 at +-45 (installed facing 0/180), 3 and 11 for installed 90/270; all with the claw reference at z >= 1.98 m (top 0.4..0.8 m of the workspace) and line elevation <= 11 deg | FAIL at yaw >= 30 (F6, conditional) |

## R2.2 Repair claim by claim

- F2 fixed.  The open notch removes both the chamfered roof and the 1.1 mm lintel; a 13 x 8 plug passes.  Residual: lateral play +-0.25 mm.
- F3 fixed.  No wall below 1.989 mm in either part (own scans).  The earlier USB lintel, pilot-2 and post-1 slivers are gone.
- F4/F4b/F4c fixed by removing the posts and pilots and designing for the repo-selected Adafruit 3886.  New residual: R2-W3 (corner-peg assumption).
- F7 envelope fixed (24.963 cradle).  Lens and USB-C positions inside the envelope remain assumptions; both tolerate small errors (lens +-3.9 mm, USB lateral +-0.25 mm).
- F8 fixed (7.0 deep hole, 1.3 reserve).  F9 fixed (flat face on the bed, no overhangs).
- F5 unchanged: the gear housing still hides the floor under the jaws (first visible floor 30 mm from the tube axis).

## R2.3 Cable-line analysis (item 8): review of scripts/analyze_cable_lines_claw_camera_bay.py

- Units: stations in metres, line length L converted to mm before it is compared with the ray parameter (mm), positions and offsets in metres with 54.09/1000.  The mm/m bug disclosed earlier is fixed; my independent run reproduces the author's numbers (yaw 0: clearance 21.2 vs 20.8; 15 deg: 19.4 vs 19.1; 30 deg: 2 hits vs 2; 45 deg: 7 vs 7).
- Mapping: the corner-to-station map is made at psi = 0 by the nearest corner diagonal (B, C, D, A for (+X,+Z), (+X,-Z), (-X,-Z), (-X,+Z)) and held fixed.  I rebuilt it with my own handedness derivation (v6 is right-handed with Y up, so bay +Z maps to room -y) and also for installed orientations of 90, 180 and 270 deg: the same 0.0 hits at 0 and +-15 deg and the same hit counts at +-30 / +-45 deg (3 and 11 hits at 90/270 because the room is not square).
- Feasibility filter (lines through the box excluded) is right; the claw reference sampling (8 x 7 x 6 grid, z from the jaw-tip limit to ceiling - 0.4 m) is coarse but adequate.

**Are hits at |yaw| >= 30 deg physically reachable?  Yes, they cannot be ruled out.**  Reason (my linear model of a rigid claw hung from four inextensible lines, attach points 54.09 mm from the axis):
the four lines leave nearly radially from the corners (the corner diagonals are at 45 deg while the lines to the stations are at about 39 deg from the room centre), so the yaw lever arm of each line is only a few mm.  Consequences:
 - yaw sensitivity to line-length inconsistency is 3.6 to 6.0 deg per mm (median 4.7); a 2 mm 1-sigma error per line (spool payout, anchor position) gives about 9 deg 1-sigma yaw, and about 6 mm of inconsistency reaches 30 deg.  `anchor_sigma_m` is 0.05 in the simulation profile (unsurveyed).
 - the restoring torque from line tension is tiny: about 0.1 to 0.7 N.mm per degree (450 g claw, equal vertical share); roughly 3 to 20 N.mm of disturbance torque moves the claw 30 deg.
 So "four corner holes 108 mm apart" holds the claw near the installed yaw only if the lengths are calibrated to a few mm; it does not provide a stiff yaw constraint.  This is a linear estimate (cable elasticity, tilt coupling and slack were not modelled), so treat the numbers as order of magnitude.
 Where it matters: hits occur only with the claw in the top 0.4 to 0.8 m of the workspace.  In my 6-level grid there are no hits at |yaw| <= 45 deg for a claw reference at z <= 1.62 m.  Mitigation options for the lead: raise `ceiling_margin_m` to about 0.8 m while yaw is unmeasured, or measure/limit yaw, or shorten/shape the bay.

## R2.4 Audit of changes to tests/test_claw_camera_bay_verify.py (git diff be58fc5..HEAD)

All 16 hunks were read.  Legitimate geometry-driven changes (new numbers verified by my own measurements above): volume baselines (408,848 / 19,604 / 6,515), removed volume 1,050.9 (pilot nick gone), added bbox r <= 129.81 and |x| <= 34.85, lens window x -8.5..8.5 and r 82..98, cradle 24.963 x 18.4, boss numbers, cover STL on bed, the xfails F2/F3/F4/F4b/F4c/F9 removed once fixed, IMU tests replaced for the pocket design, stiffness Ix 12,713 / arm 65.8 / IMU CoM 114.5, mass 28.7 g.
Findings in the changes (corrected by me in this round, keeping the stricter intent):
 1. Two assertions were reduced to constant arithmetic and tested nothing: `(24.36 - 2.4) >= 5.0` in the IMU test, and `(90 - 8.0) - 80.0 >= 2.0 - 1e-9 and 8.5 < 12.48` for the cradle ledge.  A third, `(xs[7] - xs[0]) / 2 >= 0 and 22.08 - 17.5315 == approx(4.55)`, was vacuous.  I replaced them with measurements (floor height, side-block height, space above the reservation, peg gap, peg area, block bearing, measured boss OD).
 2. `thickness_scan` mask was changed to exclude facets within 1.0 mm of the box wall and x < -45; this could hide defects.  `test_min_wall_known_values` was deleted (acceptable, the flagged defects are fixed).  I added `test_r2_thin_wall_unmasked_scan` (no exclusion): minimum 1.989 / 1.999, so nothing was hidden.
 3. `test_wire_path...` dropped the IMU obstacle (acceptable, the IMU moved) and raised the bound to 3.5 mm (stricter), but no longer covered the IMU wires; added `test_r2_wire_path_from_imu_pocket`.
 4. `test_overhangs...` lost its USB-roof span assertions (fine, no roof now) and gained `area[flat].max() < 40`; unchanged slanted-area bound 80 mm2.
 5. Mass baseline rose from 18.2 to 28.7 g and now sits close to the existing `< 30 g` bound (the bound was not raised).
 6. The cover flat-face test accepts 85 % of an approximate plan area; mine checks that the bed contact equals the whole flat face (1 %) and that nothing overhangs.
No assertion was weakened to hide a failing measurement; the numeric changes track real geometry moves.

## R2.5 New findings (ranked)

1. R2-W1 (LOW-MEDIUM): USB plug lateral tolerance +-0.25 mm (13.5 mm notch for a 13 mm overmold) and vertical -0.5 / +0.6 mm, on an unverified connector height.  Widen the notch (every 0.5 mm of width costs nothing structurally) or measure a real plug.
2. F6 (MEDIUM, upgraded): lines at |yaw| >= 30 deg hit the bay near the ceiling margin, and yaw is only weakly held (above).  The cable-line claim in the design record should say "clear for |yaw| <= 15 deg, or whenever the claw is lower than about 1.6 m".
3. R2-W3 (LOW-MEDIUM): IMU corner pegs and pads assume component-free board corners; vertical play 0.2 mm until the ties are tightened; the cover (two screws near the root, 60 mm cantilever beyond them) floats at the IMU.
4. R2-W2 (LOW): 0.89 mm board bearing on the cradle block; the lens window (16 mm) is nearly as wide as the 17.78 mm board.
5. F10 (INFO, updated): outboard mass 39.1 g solid at r_cg about 94 mm is a CoM shift of about 8 mm for a 450 g claw and a lean near 2 deg if the CoM is about 250 mm below the cable plane (both assumed).  Bay length from the box wall is now about 70 mm (r 56 to 129.8).
6. Cosmetic: gusset-rib start corners protrude 0.35 mm beyond the bay side wall.

Final status of the verification suite: see the next line (updated after the last run).

Final run of the round-2 suite: **45 passed, 3 xfailed (strict: F5 grasp point hidden, F6 lines at yaw 30 deg, both signs)**.  Author suite: 18 passed.
