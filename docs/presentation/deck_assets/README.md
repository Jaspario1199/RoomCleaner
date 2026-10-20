# Deck assets

Everything the interview deck is built from. Style rules: `../STYLE_GUIDE.md`.

| File | What |
|---|---|
| `style_sampler.pptx` / `.pdf` | One slide per archetype (A–I) plus a style reference sheet. Sample text only. |
| `build_style_sampler.js` | Generator: theme, four layouts (Dark Title, Dark Section, Content, Dark Closing) and helpers `tag()`, `rail()`, `callout()`, `photo()`, `render()`. The real deck reuses these. |
| `renders/*.png` | Transparent orthographic renders from `tools/render_deck_assets.py` |

Rebuild:

```bash
xvfb-run -a python3 tools/render_deck_assets.py            # all renders (or name some)
NODE_PATH=<node_modules with pptxgenjs> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
  node docs/presentation/deck_assets/build_style_sampler.js
```

## Asset → story map

| Story (DECISION_STORIES.md shortlist) | Photos (`../photos`) | Renders | Data on hand |
|---|---|---|---|
| Title / hero | 13 gen-1 station lifting weight | `claw_v6_camera_bay` | — |
| 1 Heat fin | 01, 02, 03, 06 | `heat_fin` | fin efficiency 54/68/81 %; shop drawings in `solidworks/heat_plate/`; `figures/motor_thermal.png` |
| 2 Motor that wouldn't move | 07, 08, 12, 14 | — | meter readings — **need from Jasper** |
| 3 Spool shorter, then too tight | 05 | `spool_v1`, `spool_v2`, `spool_v3` | bore numbers — **need from Jasper** |
| 4 Homing switch | 09 | — | 5 mm / 10.5 mm misses, 3.75 mm overlap |
| 5 Gear teeth / stall | — | `claw_v6`, `gripper_v7` (WIP, re-render once verified) | SF 0.35–0.41 → 2.1; v6 mass 2.06 kg vs 450 g |
| 6 Tension sets the workspace | 13 | — | 32 N per cable, 24 N limit, 0.4 m ceiling margin |
| 8 Central → distributed electronics | 10, 14 | — | 2.5 mm / 8 N per 50 ms skew |
| 9 Fixed vs serviceable anchor | 04, 05, 11, 13 | `gen1_corner_mount`, `wall_mount_v3`, `slipin_v3`, `shell_v3`, `station_v3_assembly` | — |
| 10 Margins instead of precision | — | — | σ ≈ 10–12 mm board, 5/5 slack-probe runs |
| Vision / camera bay | — | `claw_v6_camera_bay` | 512 mm lens height, 12.4 % blocked, 1.98 m / 1.6 m cap |
| Gen-1 claw (what came before) | — | `gen1_tentacle_claw`, `gen1_winch_spool` | — |
