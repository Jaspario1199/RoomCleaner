# Control system V1 - independent review (read-only)

Scope: `docs/CONTROL_SYSTEM_V1.md` against `roomcleaner/cdpr/*.py`, `tests/cdpr/test_system.py`.
Not reviewed: C++ firmware (`firmware/winch_station`, another agent is editing it), claw firmware beyond the IMU
formula. `station_core.py` was read in its working-tree state (uncommitted edits by another agent).

Evidence tags: **[V]** verified by running something (scripts in the session scratchpad, simulator, sim time
advanced explicitly); **[T]** traced by reading code, not executed; **[S]** suspicion, plausible but not demonstrated.
Baseline: `pytest tests/cdpr/{test_calibration,test_trust,test_station_core,test_service,test_core_models}.py` = 36 passed.
A full simulated startup (`sup.start()`) completes in 43 s wall and reaches READY/LOCAL_ONLY.

## 1. Findings (ranked)

### Critical

| ID | Sev | Where | Finding | Failure scenario | Fix |
|---|---|---|---|---|---|
| C1 [V] | Critical | `service.py:41-97,193`; `supervisor.py:120-140`; `coordinator.py:82-97` | The service has no background loop. `Coordinator.pump()` (the only sender of SYNC and the 20 ms keep-alive ping) and `Supervisor.poll()` (the only turn of station faults/reboots into trust events) run only inside a command. `SimRuntime` time advances only inside `wait()`, so the simulator can never show this. | Claw READY and hanging, operator reads the page for longer than `lease_s` (0.3 s sim). All four stations latch FAULT(LEASE) (sim: `rt.wait(1e6)` then state 4/fault 4 on A-D). The page still says READY. A station reboot or TRACKING fault while READY never reaches the ledger and never changes the state. Also: after `start` from PARKED on the floor, the first SELF_CHECK sees FAULT stations. | One supervisor thread that owns the coordinator: pump at <= lease/4 always, `poll()` every ~100 ms, HTTP threads only enqueue commands. Add a test that advances sim time while the host is idle. |
| C2 [V] | Critical | `supervisor.py:47-56,140,202-211,277-301,303-359`; `trust.py:105-135` (dead code); `startup.py:84-101` | With a hanging claw and stations latched FAULT(LEASE) there is no software path to lower it. `acknowledge` is only allowed in FAULT, but `poll()` sends a hanging claw to RECOVERY_REQUIRED (`:140,:211`). `recover()` returns True and sets READY with all four stations FAULT (sim E1; it never checks `readiness()`). After a host restart, `recover` refuses ("no calibrated model") because `ctx.model/result/T_R_M` are not persisted (sim E5). `lower()` then fails at the first `execute` with "not ready: fault LEASE" (E1 and E5). `restore_after_host_restart` and `on_power_loss` are never called (grep). | The documented scenario (spec 12.10: Wi-Fi drop, host reset, host crash while suspended) leaves the claw hanging with torque on and no command that can lower it. The only exit is the power strip, i.e. a category-0 drop of the claw over the room. | Let `lower` and `recover` clear LEASE/UNDERRUN faults (explicit operator command; re-check boot id, config hash, clock sync). Persist the calibration result and model and restore them with `restore_after_host_restart` at start. `recover` must require `readiness()` empty before READY. Add a system test: link down > lease while suspended, then lower to the floor. |
| C3 [V] | Critical | `supervisor.py:74-80,90-97,365-375`; `startup.py:394,199`; `trust.py:67`; `service.py:184` | `claw_supported` is persisted only inside `_set()`. Startup flips it to False at the end of INITIAL_LIFT (`startup.py:394`) and nothing saves. Sim E2: during CALIBRATION the claw is at ~0.5 m and in-memory `claw_supported=False`, but `state.json` says `true`. `disarm()` skips the vision check when the flag is True (`:368`). Sim E4: fresh Supervisor on a hanging claw starts DISARMED, `disarm("claw_supported")` sends OFF to all four stations (core state 0). The ledger default is True (`trust.py:67`), so a missing or relocated data dir (`--data data/cdpr` is CWD-relative) also fails open. | Host process crash or PC reboot during CALIBRATION / REFERENCE_VERIFICATION (tens of minutes with the claw up). On restart the UI says DISARMED; one `disarm` (typed confirm only) removes torque and the claw falls. | Fail closed: unknown = not supported. Atomically write and fsync `claw_supported=false` before the first lift command. Require vision confirmation in `disarm` always, except in PARKED set by `lower` in the same run. Refuse `disarm` from DISARMED unless vision confirms. |

### High

| ID | Sev | Where | Finding | Failure scenario | Fix |
|---|---|---|---|---|---|
| H1 [V] | High | `coordinator.py:303-305,358-361`; `station_core.py:329,343,418` | The coordinated hold is two back-to-back datagrams with no ack and no resend while a station still reports RUN. Stations that start a hold from a received `hold_tau` do not re-broadcast it (`broadcast=False`, `:418`). The keep-alive ping keeps the unreached station's lease alive, so lease cannot catch it. Sim E3: both host hold datagrams to C dropped, A/B/D stopped at tau 1.147 s, C kept running until its own UNDERRUN at tau 1.89 s = **85.6 mm of extra cable** on one winch. | Wi-Fi burst loss (spec evidence only covers 2-5 % random loss) at pause, fault or capture: one cable keeps pulling/paying while three hold, which over-tensions or slackens the claw. The pull is limited only by the 0.8 s `lookahead_s` and the motor. | Resend `hold` every ~20 ms until all four telemetry streams show HOLD/IDLE/FAULT. Stations should re-broadcast on receiving a hold. Host: station still RUN > 100 ms after hold = escalate (send `stop`, mark station suspect). |
| H2 [T] | High | `supervisor.py:47-56`; spec 1.5 | PAUSE is allowed only in STARTUP/TASK/READY. `lower` and `recover` run with the supervisor state unchanged (RECOVERY_REQUIRED, FAULT, PAUSED), so they cannot be paused. `lower` is the riskiest motion: model moves with `check_tension=False` (`:329`), then up to 400 vision-terminated equal-payout packets (`:339-352`) with no drift or tilt check. | Operator sees the claw swing toward furniture while lowering from RECOVERY_REQUIRED; the page rejects PAUSE; only the power strip is left. | Accept pause whenever `Service.busy` is set, in any state. Add drift/tilt bounds to the lowering packets. |
| H3 [T] | High | `service.py:155,161,181-193` | HTTP API bound to 0.0.0.0, no auth, `request.get_json(force=True)` (no CORS preflight). The checklist is a client-asserted boolean (`body.get("checklist") is True`). | Any LAN host, or a web page open in the phone browser (CSRF with `text/plain` body), can POST `{"cmd":"start","checklist":true}` and start a suspended lift, rewrite anchors via `/api/room`, or `acknowledge`/`lower`. | Bind to localhost or a VPN, per-session token, require `application/json` plus an Origin check, server-issued one-time nonce for `start` and `disarm`. |
| H4 [T] | High | `coordinator.py:191-343`; `startup.py:272,357`; `perception.py:72-73,82-85`; `claw_link.py:229-262` | `execute()` has no try/finally. Monitors run vision (blocking HTTP, `timeout=1.0 s`) inside the control loop, and `VisionSource._fused` raises `ClawError` if `/status` is offline while the frame succeeded. | (a) Exception in a monitor: no hold is sent and `pump()` stops, so stations run their buffered path (<= 0.8 s) or hit lease (0.3 s) + hold ramp (0.25 s), uncoordinated in time. (b) A frame fetch longer than `lease_s` blocks the ping (needs <= lease/4) and LEASE-faults all four mid-motion, which then trips C1/C2. | `try/finally: _abort(...)` in `execute`. Run vision on its own thread, monitors read the latest result with a timeout. Catch `ClawError` in `_fused`. |

### Medium

| ID | Sev | Where | Finding | Failure scenario | Fix |
|---|---|---|---|---|---|
| M1 [T] | Medium | `supervisor.py:277-301,383-387`; `startup.py:195-201`; `tasks.py` abort path `supervisor.py:383-386` | The ledger learns of faults and reboots only through `poll()`. It is not called after a startup abort, a task abort, `acknowledge`, or in the service (C1). `recover()` takes `bad` from the ledger only. | Task aborts with "station C fault TRACKING" (steps lost, claw hanging) -> FAULT -> `acknowledge` clears the station (`clear` re-origins tracking) -> RECOVERY_REQUIRED -> `recover` sees no invalid station and accepts a `visual_check` within 4 sigma (cm-level) -> READY with a suspect L0. A rebooted station is not reconfigured (`boot_changed` stays) so `lower` refuses. | Call `poll()` (or the ledger update) from every abort path and from `acknowledge`. Derive `bad` from live telemetry (boot id, latched fault), not only the ledger. |
| M2 [T] | Medium | `kinematics.py:135-152`; `config.py:103`; spec 6.4 | Normal moves keep cable i >= `trigger + 0.02 m` using **model** lengths. Spec 6.4 reports absolute errors of -38..+21 mm (sigma 20-25 mm) and the run ends LOCAL_ONLY, so the 20 mm margin is below the model error. | A LOCAL_ONLY move near a corner drives the bead onto the switch inside a `ref=0` segment -> SWITCH fault (stop, torque kept), station invalidated -> RECOVERY (see C2). | Margin >= k * absolute sigma while level != VERIFIED, or exclude bead-reach regions from the LOCAL_ONLY hull. |
| M3 [T] | Medium | `station_core.py:415-458`; `homing.py:417-422` | The overtravel guarantee (docstring, spec 6.4) holds only for \|e\| <= k*sigma, where sigma excludes spool-model/payout-scale error (`fit_payout_scale=False`, `config.py:216`) and an erroneous `trigger_length_m` entry. The only bound on the search is the host's model-based `L_floor`; the station has no travel clamp. | Payout-scale error of 1 % over ~3 m is 30 mm, outside the sigma used. A failed or mis-wired switch then lets the bead be pulled past `max_overtravel_m` with no independent stop. | Firmware-enforced absolute `pos_floor` per `ref=1` segment (host-supplied, station refuses pulses below it); include a payout-scale term in the bead sigma. |
| M4 [T] | Medium | `coordinator.py:70,287-289`; `supervisor.py:171-175,155-163` | `pause_requested` is a sticky flag consumed only in `execute`'s main loop (after T0). Pause in READY with no motion, or between startup steps, leaves it set; `resume` does not clear it. `start()` ends with unconditional `_set("READY")`, overwriting a PAUSED set by the HTTP thread. | After pause/resume the next motion starts and is held ~20 ms into the path (a visible jolt). A pause pressed between motions is shown as PAUSED while the worker continues to the next step; if that step is the last, the pause is lost and the state returns to READY. | Clear the flag in `resume`; check it before sending the first segment; the worker must honour PAUSED before starting any motion. |
| M5 [T] | Medium | `startup.py:394`; `supervisor.py:339-359` | `claw_supported=False` is set only after the target clearance is reached, but packets lift the claw earlier; a non-`StartupAbort` exception during the lift leaves True. `lower()` sets True after the 400-iteration loop even when the break condition (floor reached) never held. | The claw rests on a laundry pile 10 cm up (z - zf > 3 cm): loop runs 400 packets (2 m of cable), then slackens and marks PARKED; `disarm` then skips the vision check (`:368`) and drops it. | Set the flag False before the first lift packet. After `lower`, require the vision floor test; otherwise stay in RECOVERY_REQUIRED. |
| M6 [S] | Medium | `calibration.py:692-706`; `supervisor.py:256-275` | `visual_reference` derives L0 of a recovered station assuming that cable is taut at the current vision pose (`L = \|a - q\|`). With the claw hanging on three cables the recovered cable may be slack by several mm. | Model length of that cable is short by the slack. Later commanded poses make it taut early; with stiff Dyneema and no tension sensing the error appears as tension (D-A). | Treat the recovered L0 as an upper bound; pretension that cable slowly under vision watch, or keep it LOCAL_ONLY with a smaller hull. |
| M7 [S] | Medium | `station_core.py:427,434`; coordinator | Path time is `tau += rate * period_us` (nominal period) and never re-anchored to `now - motion_t0`. The host does not compare reported `tau` across stations. | A loop that averages 1.1 ms instead of 1.0 ms makes that winch lag 10 %; the cables drift apart geometrically with no fault. Sim cannot show it (exact ticks). | Integrate measured elapsed time (or re-anchor to `now` minus accumulated hold time); host monitors per-station `tau` skew and holds if > few ms. |
| M8 [T] | Medium | `kinematics.py:75-93`; `trajectory.py:237-241`; CLAUDE.md load case | Statics use zero acceleration; the stated load case (+2 m/s^2 with 0.9 kg) is not in the planner, and `max_tension_n` is used as the limit without a margin. | Near the workspace edge min-max tension is close to 40 N statically; adding the dynamic term pushes a cable beyond the motor limit, causing a stall, TRACKING fault and RECOVERY. | Pass `accel=(0,0,cart_a)` in `_check_path`; apply a derating factor. |
| M9 [S] | Medium | `claw_link.py:234-250,257-261`; `perception.py:72-98` | Fusion uses the latest IMU roll/pitch from a status cached up to 100 ms (`status_ttl_s`) and low-passed in firmware, not time-aligned to the frame's `capture_us`. Sigma 3 mrad is assumed. | Fused pose errors during any motion exceed the stated sigma; absolute-length sigma (bead gate) is optimistic. | Timestamp IMU samples; use the sample at frame capture time; inflate sigma with angular rate. |
| M10 [T] | Medium | `station_core.py:154-164`; `transport.py:53` | A station accepts a bare `{"t":"disarm","confirm":"claw_supported"}` in IDLE from any "host" source; host side falls back to the message's own `sid` (`transport.py:53`) when the address is unknown. No nonce, no session. | Any LAN device (or a stale tool, replayed packet) drops a hanging claw in READY/PAUSED. | Station accepts `disarm` only after a host-issued challenge echoed from telemetry; filter by host IP in firmware; do not trust `sid` from the payload. |
| M11 [T] | Medium | `trust.py:96-99,142-147`; `supervisor.py:197` | `on_fault(LEASE/UNDERRUN)` sets `recovery_required`, but spec 5 says "unchanged". `_update_level` demotes only from VERIFIED, so LOCAL_ONLY stays when all stations are invalid. `resume` returns READY after a paused startup with `ledger.level == "NONE"` if any `ctx.result` exists. | READY displayed with unvalidated calibration; tasks then refuse (hull is None) but the page claims READY, and spec 6.1 says READY means VERIFIED or LOCAL_ONLY. | Align code and spec; READY only after `calibrate()` finished. |
| M12 [T] | Medium | `supervisor.py:90-100`; `service.py:57-61` | State files are written non-atomically from two threads (HTTP `pause`, worker); a truncated `state.json` makes `Supervisor.__init__` raise (service will not start). | Crash during write -> no UI after restart; operator improvises. | Write temp + `os.replace`; lock `_set`. |

### Low

| ID | Where | Finding |
|---|---|---|
| L1 [T] | `calibration.py:532` | `pinv(H)` returns zero variance along unconstrained directions; rank deficiency would show as small sigma. Check conditioning or use `inv`. |
| L2 [T] | `calibration.py:482-483,543,548` | Up to one reading per sample is declared slack and removed from residual RMS and outlier tests; the slack count is reported but never limited by acceptance. Systematic anchor error that looks like slack is hidden from criterion 2 (witnesses still guard it). |
| L3 [T] | `startup.py:280,302` | `mon["onset"]` is computed but unused; the onset sample pairs the **end-of-pull** P with the end pose (self-consistent, but docs/spec say "onset"). |
| L4 [T] | `startup.py:312,375` | Results of backoff and lift `_execute`/`_packet` calls are ignored; a failed packet is only caught indirectly by the lift-lag budget. |
| L5 [T] | `tasks.py:67-69` | `Delaunay` on coplanar validated points raises `QhullError` -> generic exception in `run_task`. |
| L6 [T] | `spool.py:275-276` | Table model returns NaN beyond the table instead of raising; NaN reaches plans (stations nack "range"). |
| L7 [T] | `service.py:92-97`; spec 2, 8 | The service exposes no `task` command; tasks are unreachable from the phone page. |
| L8 [T] | `station_core.py:276-278` | Speed limit checked at 5 sample points of each Hermite segment only. |

## 2. Spec vs code contradictions

- Spec 1.5 "PAUSE holds position at any time": `ALLOWED["pause"]` excludes PAUSED, FAULT, RECOVERY_REQUIRED (H2).
- Spec 5/12.10 host restart "restored or RECOVERY": `restore_after_host_restart`, `on_power_loss` are never called; model is not persisted (C2). The power-loss row (NONE, floor restart) is not implemented.
- Spec 5 coordinated stop "unchanged" vs `trust.py:99` sets `recovery_required` for LEASE/UNDERRUN (M11).
- Spec 7 "acknowledge: FAULT -> RECOVERY_REQUIRED (hanging)" vs `poll()` entering RECOVERY_REQUIRED directly, so acknowledge is unreachable for a hanging claw (C2).
- Spec 7 "disarm needs claw_supported and vision/state confirming support": the state flag is not durable (C3).
- Spec 4 "Lease: stations hold" is true; spec does not say the hold latches FAULT and needs `clear`, which the supervisor cannot issue in RECOVERY_REQUIRED (C2).
- Spec 6.1 READY = VERIFIED or LOCAL_ONLY vs `resume()` READY at level NONE (M11).
- Spec 2/8 task runner in the service: not exposed (L7).

## 3. Math, checked

- **Bead gate**: derived independently. Model length error e = L_model - L_true. Approach stops at model `trigger + window`; bead not reached iff e < window -> `k*sig <= window`. Search ends at model `trigger - overtravel + k*sig`; true overtravel = overtravel - k*sig + e <= overtravel iff e <= k*sig. Search complete iff `trigger - overtravel + k*sig <= trigger + e` for e >= -k*sig -> `2*k*sig <= overtravel`. Code (`homing.py:417-422`) matches the docstring and spec; `sig` there is `capture_sigma` (adds bead, quantisation, latency) so the gate is slightly stricter than the spec text. Caveat: M3.
- **Absolute vs in-volume**: bead gate correctly uses `absolute_sigma` = sqrt(cov[L0,L0]) (`calibration.py:617-622`); motion/hull uses in-volume `length_sigma` with g = [u, -1] (consistent with the residual sign). `sigma_fn` is a constant (sigma before bead refit), conservative.
- **Jacobians [V]**: central-difference check of `Calibrator._rows` (length, vision, onset, slide-bearing, bead, anchor/heading/position priors, payout scale on and off, Huber weights = 1): max relative error 5e-8, zero rows over 1e-3. Includes the dRz term and bearing derivative.
- **Slack logic**: sign correct (slack = model length > span, `calibration.py:446`); one slack per sample, penalty slack_k^2, witness check uses the same sign convention. Residual masking caveat: L2.
- **Gravity fusion [V]**: with exact inputs the fused pose reproduces truth to 1e-16 (position and R). Firmware roll = atan2(ay,az), pitch = atan2(-ax, sqrt(ay^2+az^2)) is consistent with R = Rz(yaw)Ry(pitch)Rx(roll) used in `perception._fused` and `claw_link` (`up_body`). Not verified: IMU mounting vs body axes (no extrinsic in config). Timing: M9.
- **Frames**: `T_A_B` maps B->A used consistently: `to_room`, `to_marker`, `claw_pose_in_marker`, `marker_visible`, `lower()` camera offset (`supervisor.py:322-325`), `anchors_room = anchors_M @ Rz^T + t`.
- **Spool**: P positive = payout, `length`/`position` are exact inverses; layered model matches test.

## 4. Verified OK (traced or run)

- Station (`station_core.py`): every fault path keeps torque (`_set_fault` never sets OFF); `disarm` refused in RUN/HOLD and without the literal confirm; a reboot yields OFF with an empty queue (nothing persisted); `clear` never requeues; late/duplicate/out-of-order segments are rejected or idempotently acked (t0 lead check, continuity, `position` check at first segment); capture suppresses shortening after debounce; unexpected switch is a fault outside `ref` 1/2; ENCODER/TRACKING/TIMING/LEASE/UNDERRUN reactions as documented.
- Coordinator: readiness gate (fresh telemetry, boot id, hash, clock, IDLE), start-position match, first-window ack before T0 with abort, lease-aligned hold when a station goes silent.
- Nothing auto-resumes: no code path restarts a startup/task after reboot, host restart, or `clear`; `resume` re-checks readiness and vision; HTTP `start` needs the checklist flag (but see H3).
- Searches and retractions are bounded: SLACK_TAKEUP by `max_slack_m`, INITIAL_LIFT by `max_lift_m` and the lift-lag budget, bead search by `L_floor`, ref=2 backoff by `backoff_m`. Exception: the 400-packet lowering loop (M5).
- Bead procedure aborts rather than extends: no capture -> retreat + BLOCKED; capture on another station -> FAULT; no release -> FAULT.

## 5. Test gaps that matter

1. Sim time only advances inside `wait()`: host stalls, idle gaps, blocking HTTP are untestable (C1, H4). Add a runtime where wall-clock advances while the host is idle.
2. No lost-hold test; `test_lossy_network...` accepts "completes or stops safely" and uses random 2-5 % loss (H1). Add targeted drop of `hold` to one station.
3. No test of lower/recover after LEASE or host restart; `test_host_restart_while_suspended_never_resumes` (`test_system.py` ~75-83) only checks the state name (C2).
4. No test of persisted `claw_supported` during startup, nor of `disarm` on a hanging claw with a fresh Supervisor (C3).
5. System test ends with all beads BLOCKED; the VERIFIED -> refit -> `set_level("VERIFIED")` path (`startup.py:540-565`) is exercised only by unit tests with a fake sigma of 0.5 mm. No test that mis-entered `trigger_length_m` or a failed switch is bounded by `max_overtravel_m` (M3).
6. No pause-during-lower/recover, pause-flag staleness, or service threading test (`test_service.py` covers page, room, illegal commands only).
7. No test where a monitor raises or blocks (H4); no Jacobian finite-difference test in the repo (I ran one, results above).

## 6. Recommended order

1. C1 (host loop owner + keepalive + poll), then C2 (lower/recover from LEASE and restart, persist model).
2. C3 (fail-closed `claw_supported`, atomic persistence), H3 (bind/auth), H2 (pause everywhere).
3. H1 (hold resend), H4 (execute try/finally, vision off the control thread).
4. M3 (station-side travel clamp) before any suspended run with beads; M10 (disarm challenge).
5. Close the test gaps in section 5 before hardware qualification of the suspended 1 lb test.

Hardware status unchanged from the spec: nothing here has run on the physical rig; every [V] above is simulator evidence.

---

## 7. Lead disposition (2026-10-19)

| ID | Disposition | Change | Evidence |
|---|---|---|---|
| C1 | Fixed | `service.py` host loop: idle thread pumps the coordinator (keep-alive/sync) and polls the supervisor every 100 ms; commands own the robot via the service lock; `poll()` after every command | `test_service.py::test_idle_host_loop_keeps_stations_alive` (idle 3 s: no LEASE; stalled host: LEASE on all four) |
| C2 | Fixed | LEASE/UNDERRUN = coordinated stop, references kept, state FAULT -> `acknowledge` clears and re-checks vision -> READY; `recover`/`lower`/`acknowledge` reconfigure rebooted stations and clear latched faults; `recover` requires `readiness()` empty; model persisted (`data/cdpr/model.json`) and restored with `restore_after_host_restart` (lease faults treated as benign) | `test_system.py::test_full_lifecycle...` (stall while hanging -> FAULT -> acknowledge -> READY; host process restart while hanging -> RECOVERY_REQUIRED -> recover -> lower -> PARKED) |
| C3 | Fixed | `claw_supported` defaults False (fail closed), written atomically+fsync False before the first lift command and True only after a vision floor check; `disarm` ALWAYS needs a fresh vision floor check; data dir absolute | `test_system.py::test_crash_mid_calibration_fails_closed`, `test_trust.py::test_unknown_support_fails_closed_and_save_is_atomic` |
| H1 | Fixed | coordinator resends `hold` every 20 ms to any station still RUN (and in the settle wait), escalation logged after 300 ms | `test_coordinator.py::test_lost_hold_datagrams_are_resent_until_every_station_stops` (negative control without resend: 0.58 s path-time spread; with: < 0.06 s) |
| H2 | Fixed | `pause` accepted in every state, stops lowering/recovery moves; lowering packets bounded (count from height), drift and tilt checked, model descent tension-checked | lifecycle test: pause during `lower` stops it, second `lower` completes |
| H3 | Fixed | session token (`X-Token`) on every /api call, JSON content type required (blocks cross-site form posts); token printed at start, page reads it from its URL | `test_service.py::test_api_requires_token_and_json` |
| H4 | Fixed | `execute()` holds all stations on any host exception (resend until stopped); monitor exceptions become a stop reason; hardware frames on their own thread (`ThreadedFrameSource`), attitude sampled with each frame; IMU errors -> no pose | `test_coordinator.py::test_host_exception_still_stops_every_station` |
| M1 | Fixed | `poll()` after every command, task abort and acknowledge; `_restore_stations` derives actions from live telemetry | — |
| M2 | Fixed | normal-motion bead keep-out = trigger + margin + k*sigma_abs until that bead is verified | — |
| M3 | Partly | bead gate sigma now includes a payout-scale term (`calibration.payout_scale_sigma`, default 0.3 % of the distance from the calibrated region). **Open:** a station-enforced absolute travel floor for `ref=1` segments (protocol + both cores) — required before any bead search on hardware | — |
| M4 | Fixed | a pending pause holds the next motion before it starts and is consumed; `resume` clears it; a pause at the end of startup is not overwritten | `test_coordinator.py::test_pause_pressed_between_motions_holds_the_next_one` |
| M5 | Fixed | flag False before the first lift-related command; `lower` enters PARKED only if vision confirms the floor, else RECOVERY_REQUIRED | — |
| M6 | Fixed | recovered cable is tautened slowly under vision (bounded 3 sigma + 10 mm) and re-referenced; no tension within the bound -> refuse, lower | lifecycle test (station B reboot recovery) |
| M7 | Fixed | station path time integrates measured elapsed time (Python + C++, traces identical) | `tests/firmware` conformance |
| M8 | Fixed | planner checks tension with +/- path acceleration plus 2 m/s^2 vertical dynamic allowance at 80 % of the limit; calibration candidates likewise | — |
| M9 | Fixed | attitude fetched right after each frame and attached to it (time-aligned to ~one HTTP round trip) | `test_claw_link.py` |
| M10 | Fixed | `disarm` must echo a per-boot random key reported only in unicast telemetry (Python + C++); wrong/missing key -> nack "key" | `test_station_core.py`, firmware traces |
| M11 | Fixed | LEASE/UNDERRUN no longer set `recovery_required` (spec 5); level drops to NONE when no reference is valid; `resume` gives READY only with a validated model and level != NONE | `test_trust.py` |
| M12 | Fixed | state and ledger written atomically under a lock; unreadable state file = "may be hanging" | — |
| L4 | Fixed | lift and backoff packet results checked | — |
| L5 | Fixed | degenerate validated set -> no trusted volume (tasks refuse) instead of an exception | — |
| L6 | Fixed | payout-table lookups outside the table raise `SpoolRangeError` | — |
| L7 | Fixed | `task` command in the service (simulation perception; hardware refuses until garment perception exists) | `test_service.py` |
| L1, L2, L3, L8 | Accepted, noted | no behaviour change in this pass | — |
