# Floor board: detector, survey and printable PDF (D26)

Status: implemented and tested on synthetic data only. No real camera frames, no real printout measured yet.

## What was built

| Item | File |
|---|---|
| Printable multi-page Letter PDF (layout page + 9 tag sheets) and its self-check | `tools/print_floor_board.py` |
| Layout, joint-PnP detector, survey | `roomcleaner/cdpr/vision/board.py` |
| Tests (31) | `tests/cdpr/test_floor_board.py` |
| Review copy of the printout | `prints/floor_board_letter.pdf` and `prints/floor_board_letter-01..10.png` (100 dpi) |
| Small refactor | `vision/marker.py`: the accept / disambiguate / reject tail of `pose_from_corners` is now `MarkerDetector.select_pose` (behaviour unchanged, `test_vision.py` still passes) so the board detector reuses the exact ambiguity rules |

### Printable PDF
- 10 pages: layout instructions + sheets for ids 0..8. Options `--ids`, `--edge-mm`, `--family`, `--no-instructions`, `--png-dpi`.
- Tag: AprilTag 36h11, black square 150.0 mm = 8 cells of 18.75 mm, white quiet zone 18.75 mm (1 cell), vector drawn (each black cell run is an exact rectangle), everything inside the 6.35 mm printer margins.
- Each sheet: large id, scale-check bar (100 mm), instruction to measure the black square and enter it as `marker.edge_m`. Sheet 0 also states it defines the frame (+X right as printed, +Y up the page, same as `marker.py`).
- Built-in check (`verify_pdf`, run by the CLI): every page is 612 x 792 pt (Letter); the drawn cells reproduce the dictionary bit pattern of the id exactly; black square 150.0000 x 150.0000 mm (tolerance 0.005 mm); tag centred; quiet zone inside the margins. Independent raster check in the tests (pdftoppm at 300 dpi, real aruco detector): ids 0..8 found, edge 150 mm +/- 0.25 mm; nothing printed outside the 1/4 in margin on any page.
- The printed size is still whatever the printer does: the user must measure the black square and enter that as `edge_m`. Tags are the only length scale in the system.

### Detector (`BoardDetector`)
- Detects all 36h11 tags, keeps the surveyed ones, solves ONE PnP over all their corners (IPPE for the planar set, then LM refinement of both candidates), then the unchanged `MarkerDetector.select_pose` rules (reprojection limit, ambiguity ratio, priors). Returns a `BoardObservation`, a subclass of `MarkerObservation` (so `perception.py` consumes it unchanged) with `used_ids`, `dropped`, `unsurveyed_ids`, per-tag rms, duplicate and unexpected ids.
- `edge_eff` = sqrt(x-extent * y-extent) of the used tags' outer corners in M (same definition as the sim's `FloorBoard` "extent" mode); `None` with one tag, as before.
- One usable tag (including "only tag 0 known"): delegates to `MarkerDetector.pose_from_corners`, so result, reason strings, ambiguity handling are identical (tested bit-for-bit on 10 random renders, `atol=1e-9`). A single non-origin tag is re-expressed in M.
- Tags too small, touching the border, duplicated, excluded by the caller, or inconsistent with the rest (per-tag reprojection > `outlier_px`, 2 px; only with >= 3 tags) are dropped with a reason.

### Survey (`BoardSurvey`)
1. Per frame: camera pose from the surveyed tags (detector above). Unsurveyed tags are placed by intersecting their four corner rays with the floor plane (known size, flat floor) and a 2-D rigid fit: (x, y, yaw, scale) per frame. No tag-by-tag PnP, so no ambiguity flips.
2. A tag becomes a candidate after `min_obs` (8) such views with spread below a loose gate. A planar bundle adjustment then runs (tag 0 fixed; tag poses; per-frame camera pose; known tag size; robust loss; optional IMU gravity residual per frame). A candidate is accepted if: enough views in the adjustment, spread of per-frame placements against the adjusted cameras <= 3 mm and 0.86 deg, reprojection rms <= 1.5 px, printed size within 1.2 % of `edge_m`, and BA sigma <= 2 mm / 0.34 deg. All surveyed tags are refined at each acceptance and in `finalize()`; sigma comes from the BA covariance. Candidates that fail a consistency check are removed and the adjustment re-run so they cannot disturb the others.
3. Chaining: frames that only show tags near the edge become usable as soon as a neighbour is surveyed (frames are stored and re-posed when the surveyed set changes).
4. Limits scale with `pixel_sigma / 0.4`: set `pixel_sigma` to the real corner noise or good tags will be rejected as "inconsistent".
5. Rejections carry a reason in `status()`: `duplicate id`, `printed size differs ... (measured X mm vs edge_m)`, `sheet moved ~N mm between observations (step at frame k)`, `inconsistent observations`, `reprojection ...`. A surveyed tag that later disagrees (3 consecutive frames, or BA diagnostics) becomes `suspect`, keeps its old pose, and is excluded from joint solves. A moved origin sheet makes tag 0 `suspect`. `reset_tag(id)` forgets a tag after the user re-places it. Sheet 0 printed at a different scale than the rest produces a warning (`survey.warnings`).

## Measured accuracy (synthetic; sim camera 800x600, fx = 520 px)

Joint PnP at 1.5 m (12 rendered frames, 2 gray-level noise, tilt up to 3 deg, all 9 tags surveyed with their true poses):
- 9 tags: camera position error median 0.22 mm (max 0.45 mm); orientation median 0.017 deg (max 0.037 deg); reprojection rms 0.2-0.3 px.
- tag 0 alone at the same height/frames: refused as ambiguous in 8 of 12 frames; the 4 accepted frames were off by 6.0 mm / 1.6 deg (median). Depth noise model: `edge_eff` ~ 1.1 m vs 0.15 m.

Survey, random sheet placements (+-0.1 m about a 0.45 m grid, any yaw), corner noise 0.3 px (projected corners), camera 1.2-1.7 m, +-0.3 m, +-3.4 deg tilt:

| frames | gravity (3 mrad) | position error | yaw error |
|---|---|---|---|
| 40 (12 seeds, 96 tags) | no | mean 0.36 mm, p95 0.78, max 1.13 mm | max 0.12 deg |
| 60 (12 seeds, 96 tags) | no | mean 0.26 mm, p95 0.47, max 0.67 mm | max 0.12 deg |
| 60 (test seed) | no / yes | max 0.47 / 0.23 mm | max 0.11 / 0.06 deg |

Reported per-tag sigma 0.3-0.6 mm / 0.08 deg; observed errors are consistent with it. Survey runtime 1-1.5 s for 40 frames (numpy, no GPU); all tags accepted after roughly 9-12 frames at 1.2-1.7 m.

Full image path (rendered images through the real cv2 detector, 40 frames): with the default detector, max position error 2.85 mm, mean 2.3 mm, yaw 0.06 deg. See limitation 1: this is a pure scale bias.

Noise sensitivity (3 surveys each, 60 frames): corner noise 0.6 px -> max 0.7 mm / 0.16 deg; 1.0 px with `pixel_sigma=1.0` -> max 1.2 mm / 0.27 deg. With `pixel_sigma` left at 0.4 and 1.0 px noise the yaw-spread gate rejects good tags (falsely "inconsistent"), which is why the limits scale with `pixel_sigma`.

Fault detection (12 random boards each): sheet printed at 97 % -> rejected with measured size within 0.1-0.9 % of true (1 % is accepted, 2 % rejected); sheet kicked 30 mm during the survey -> rejected as "moved ~26 mm" with the others unaffected; kicked 20 mm after being surveyed -> `suspect` within 3 frames; kicked 12 mm -> suspect; kicked 6 mm -> not detected (below tolerance by design). Duplicate id -> rejected. All 12/12 seeds. Moved origin sheet (3 cm) -> tag 0 `suspect`.

## Camera height / FOV needed (assumption)
Intrinsics are from `config/camera.sim.json` (OV2640-class guess: 800x600, fx = fy = 520 px, HFOV 75 deg, VFOV 60 deg); the real values come from `tools/calibrate_camera.py` and the numbers below must be recomputed with them. Counting tags that are fully inside the image with a 4 px margin and >= 40 px side (`min_marker_pixels`), random boards, camera +-0.3 m off-centre (400 trials per height):

| height | mean usable tags | P(>= 2) | P(>= 6) | P(all 9) |
|---|---|---|---|---|
| 0.6 m | 1.8 | 0.67 | 0 | 0 |
| 0.7 m | 2.8 | 0.96 | 0 | 0 |
| 0.8 m | 3.7 | 1.00 | 0.01 | 0 |
| 1.0 m | 5.5 | 1.00 | 0.54 | 0 |
| 1.2 m | 7.1 | 1.00 | 0.97 | 0.06 |
| 1.5 m | 8.5 | 1.00 | 1.00 | 0.60 |
| 1.8 m | 8.9 | 1.00 | 1.00 | 0.92 |
| 2.0 m | 0.6 | 0.17 | 0 | 0 |

So at least 2 sheets are visible from about 0.7 m; the survey flight wants 1.2-1.8 m. Above roughly 1.9 m the tags drop below 40 px (150 mm * 520 / 40 = 1.95 m frontal); a camera with a narrower lens must fly proportionally higher, a wider one lower.

## Limitations and open issues
1. Detector corner bias sets the absolute scale. cv2's sub-pixel refinement shrinks ~50 px tags by ~0.15 px per corner (measured on renders, nearly independent of height: -0.155 px at 1.5 m, -0.125 px at 1.0 m). Because the tag size is the only ruler, the whole layout comes out ~0.4 % too large (2-3 mm at 0.5 m from tag 0; also a ~6 mm depth bias at 1.5 m for any single-tag pose, existing behaviour). `BoardDetector(corner_inflate_px=...)` removes it (0.155 px -> 0.3 mm); the true value for the real camera/lens/print is unknown and should be calibrated once from a tape measure between tag 0 and an outer tag. The 100 mm bar and measured `edge_m` do not remove it.
2. Flat floor assumed (z = 0, no tilt). Carpet ridges, curled or taped-over-a-bump sheets break it; the survey only catches it through reprojection / spread (rms > 1.5 px or spread > 3 mm).
3. Lighting: glare on glossy paper, shadows or an overexposed tag can lose a tag or add corner noise; use matte paper. Noise above ~0.6 px needs `pixel_sigma` raised and costs accuracy.
4. Sheets must not move after the survey. A kicked sheet is flagged (>= ~10 mm) and excluded, but there is no automatic re-survey; the caller must `reset_tag` and collect new views.
5. Tag-size uniformity: tags 1-8 are checked against `edge_m` (tolerance 1.2 %). If all sheets are mis-scaled by the same factor nothing can detect it: `edge_m` must be measured on the printed sheet 0.
6. Tilt/gravity: without an IMU vector the survey uses the "camera looks straight down" prior only for disambiguation; with gravity (3 mrad) errors roughly halve. Tested with synthetic noise only.
7. Noise limits (3 mm / 0.86 deg spread, 2 mm / 0.34 deg sigma, 1.5 px rms) are tuned on synthetic data at 0.3-0.6 px corner noise and must be re-tuned with real frames.
8. Real camera frames, JPEG artefacts, lens distortion beyond the 5-parameter model (survey supports k1 k2 p1 p2 k3 only) and rolling shutter while the claw swings are untested. The survey assumes the camera is still enough that every frame has one pose.
9. Not wired into startup/perception/config (out of scope of this task, see hand-off notes).
