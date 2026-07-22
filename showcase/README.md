# RoomCleaner — Interactive Showcase

`index.html` is a **self-contained** portfolio page (no build step, no external
assets — the CAD render and all charts are inlined). Great for recruiters.

## View it
Just open `showcase/index.html` in any browser.

## Host it free on GitHub Pages (permanent portfolio link)
1. Push this repo to GitHub.
2. Repo **Settings → Pages → Source: Deploy from a branch**, pick your branch and
   `/root` (or move this file to `/docs`).
3. Your page goes live at `https://<you>.github.io/<repo>/showcase/`.

## What's on it
- A **live browser simulation** of the control loop (scan → grab → deliver) with
  telemetry — the same kinematics the real robot uses, in JS.
- Native, theme-aware charts: the **cable-tension cost map** and the
  **max-payload** analysis, rendered from the physics.
- The tentacle-gripper CAD render, the tech stack, and the headline specs.
- Light/dark theming, responsive, keyboard-friendly.

It's regenerated from the project's real numbers — if the design changes, update
the stats in the HTML to match.
