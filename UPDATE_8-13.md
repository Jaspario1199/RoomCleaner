# 8/13 update — read me first (note for the local agent)

From: the cloud lead session (Fable, session of 8/13). Audience: the local
agent picking up work on Jasper's machine.

## ⚠️ Hold your pushes — a merge is landing

The **console unification** (two web consoles → one app) is being built and
verified in the cloud session RIGHT NOW. It rewrites `roomcleaner/app/`,
deletes `roomcleaner/webapp/`, turns `scripts/live_app.py` into a forwarder,
and touches `docs/APP.md`, `README.md`, `quickstart.py`, `tests/test_app.py`.

**Do not edit or push anything touching those paths until you see a commit
whose message starts with "Unify the consoles" (or similar) on
`claude/magical-cerf-gqr7j7`.** Last time two agents pushed this branch
concurrently it cost a manual conflict untangle. After that commit appears:
`git pull` and you're clear everywhere.

## Safe to do right now (no repo conflicts)

1. **Baseline camera check** (today's code): `python -m scripts.live_app
   --camera 1` → live feed at :8000. Confirms camera + drivers before the
   merge changes anything.
2. **Bench support**: walk Jasper through `docs/BENCH_ASSEMBLY.md` (10 gated
   phases; interactive checklist exists on claude.ai artifacts). All pushed,
   stable, yours to use. Multimeter required from Phase 3.
3. **Physical measurements** (recorded as pending in DESIGN_STATE.md): servo
   round disc horn (dia/thickness/hole spacing → HORN_POCKET_DIA), KW12-3
   ruler check (~20 mm body, 9.5 mm hole pitch), room tape-measure (dims +
   fan position + ceiling footage). If Jasper produces numbers, you may
   record them in DESIGN_STATE.md under "Pending physical measurements"
   (append, don't restructure) — but leave `cad/` regeneration to the CAD
   workflow unless the numbers are in hand AND you follow CLAUDE.md's gates.

## First tasks once the merge commit lands

1. `git pull`, then the **smoke test**: `python -m roomcleaner.app --live
   --camera 1` → http://localhost:8000. Success = real feed in the unified
   page + detections in the detected-items panel + plan panel populates.
2. Report the result in `BRINGUP_LOG.md` (append a dated entry).
3. If the smoke test fails: capture the traceback/symptom in BRINGUP_LOG.md,
   fix ONLY if the cause is local-environment (camera index, cv2 backend);
   architecture issues go back to the cloud session via Jasper.

## State snapshot (as of this note)

- CAD: 13 verified parts incl. corner_mount rev B (homing-switch boss) and
  base_station_case (tray+lid). Print queue + gates: see DESIGN_STATE.md.
- Firmware: winch .ino has the NC polarity fix + `S` switch-state command;
  effector .ino needs Jasper's WiFi credentials before flashing.
- Electronics: ALL parts delivered except LiPo, balance charger, slide
  switch, TPU, wood screws, room wiring (see docs/SHOPPING_LIST.md).
- Tests: 185/185 at last push (more arriving with the merge).
- docs/HANDOFF_LOCAL_BRINGUP.md is STALE (its milestone completed) — it gets
  replaced after the merge lands.
