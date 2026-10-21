# Independent re-check: keep-alive pumping and bound fixes (H1, M1, L1, L2, L4)

Reviewer: independent calculation-checker (did not write this code). Under review: `verification/keepalive_fix_results.md` and
`git diff eb07a5d -- roomcleaner/cdpr/startup.py roomcleaner/cdpr/config.py tests/` (the content of commit `12d9e11`; the diff stat of the working tree I
read at the start, 43 / 75 / 7 / 102 / 289 lines, is the same as that of the commit now at HEAD `0959c67`). Everything below is **simulation**
(`/usr/bin/python3` 3.13, `OMP_NUM_THREADS=1`, 4 shared vCPU, partly loaded by my own parallel runs where stated): the real host CPU, the real
`faults.lease_s` (null = unmeasured in `config/robot.example.json`; 0.3 s in `config/robot.sim.json`) and the real corner noise are unmeasured.
No code, config or other test was changed; nothing committed. New file besides this report: `tests/cdpr/test_keepalive_fix_review.py` (4 tests, 11 s).

## Verdict: PASS WITH CONDITIONS

The change does what its write-up says for the sites it names: every `Calibrator.fit` and the survey flush go through `_pumped`, results and
exceptions pass through unchanged, no thread leaks, no shared object is mutated while the command thread pumps, the bound changes (M1, L1, L2, L4) are
correct and no shipped default moved. **But H1's purpose (a startup that does not latch Fault.LEASE from host stalls) is not achieved on this CPU**:

1. **N1 (High for hardware, same class as H1).** Other multi-second calls still run unpumped on the command thread while the stations are armed:
   the excitation-candidate filter (`_stage > _feasible`, 0.7-2.3 s) and every planned move (`plan_line > _check_path`, 0.2-1.2 s). In a full startup
   with the simulated clock coupled to wall time, the fixed tree still ends `FAULT` with **State FAULT / Fault.LEASE (4) on all four stations** at the
   first calibration stage; with those two sites pumped too (emulated in a scratch script, not in the repo) the same startup ends READY.
2. **N2 (Medium).** The pump gap across a large `cal.fit` is **0.10-0.30 s, not ~21 ms** (1.0-3x the 0.3 s lease): the worker re-takes the GIL after
   every numpy call and starves the sleeping command thread. `sys.setswitchinterval(5e-4)` brings it to 0.04-0.05 s (tested).
3. **N3 (Low).** The M1 cross-check hard-codes `frame_interval_s` = 0.1 s although the config carries it: 0.5 px, limit 0.025, `frame_interval_s` 0.05 is
   accepted and the gate then never opens.

Neither N1 nor N2 is a drop hazard (torque is kept; the startup aborts suspended, as the original H1). They are the same "first suspended run on hardware"
condition as H1: either pump the remaining sites and fix the GIL hand-off, or size `faults.lease_s` from the measured worst stall (section 6).

## Supplied facts, approved assumptions, derived results, uncertainty

* **Supplied:** the review's findings and the implementer's claims; `config/robot.sim.json` (`lease_s` 0.3 s, camera `fx` 520 px, `frame_interval_s` 0.1 s,
  `corner_sigma_px` 0.3, `grip_still_rate_rad_s` 0.02); `Coordinator.pump` (ping every `min(lease/4, 20 ms)`); `Service.idle_tick` skipped while a command runs.
* **Assumptions used (not approved by anyone, stated):** i.i.d. Gaussian corner noise (the design's own model); host CPU = this sandbox; a hardware
  `ctx.wait` is `time.sleep(1 ms)` + `Coordinator.pump()` in a loop (`RealRuntime`); a coupled-clock simulation (simulated time advances by every host
  stall between two pumps, with no ping sent) is a fair stand-in for a real runtime.
* **Derived:** all numbers in sections 1-5 are my own runs (scripts in `.../scratchpad/fixrev/`, section 7).
* **Uncertain:** every absolute time (real CPU), the real lease, the real corner noise, whether the sim's non-determinism (N4) changes outcomes.

## Findings: claim, evidence, verdict

| id | Implementer's claim | My evidence (expected -> measured) | Verdict |
|---|---|---|---|
| H1-a routing | flush and all 6 `cal.fit` sites are `_pumped`; nothing else long | `grep`: no direct `cal.fit(` / `sv.flush(` left in `startup.py` (6 x `self._pumped(ctx.cal.fit,` at 773, 1077, 1168, 1189, 1194, 1373; `self._pumped(sv.flush)` at 863; no other module calls them). **But** `ctx.cal.validate` (0.04-0.08 s), `design_excitation` (0.06-0.2 s), `_stage > _feasible` (0.7-2.3 s), `plan_line > _check_path` (0.2-1.2 s) run on the command thread armed and unpumped (section 2) | **AGREE for the named sites, DISAGREE that nothing else is long (N1)** |
| H1-b gap, flush | worst gap well under the lease | real 60-frame flush through `_survey_topup` (9 sheets, 0.17 mm): direct 2.21-2.28 s (7.4-7.6x lease); pumped max gap **36-49 ms** (CPU-bound sim wait) and **45-85 ms** (sleeping wait), median 0.1-1.4 ms, p99 21-22 ms; 3.5-8.3x margin; stations fault-free; wall +15-30 % | **AGREE** (margin 3.5-8x, not 14x) |
| H1-c gap, fit | worst gap ~21 ms on hardware | real fits (captured from a startup) through `_pumped` with a sleeping wait: 0.7 s / 1-sample **37-60 ms**; 1.5 s / 19-sample **86-105 ms**; 1.7 s / 31-sample **115-159 ms**; 11-16 s / 31-sample **154-301 ms**; synthetic 25-sample (1.8 s) **106-145 ms**, 60-sample (4.2 s) **203-291 ms**. Ratio to lease **1.0-8x** | **DISAGREE (N2)**: the 21 ms is the sleep between steps, not the gap |
| H1-d thread safety | worker touches only its own objects | flush: `FloorBoardSurveyor._pending/.survey/.layout`, layout file, `log`; fit: `ctx.cal` (`hold_yaw_M`, `_last_slack`), reads `ctx.samples/onsets` (copied at the top of `fit`). Command thread during the wait: `Coordinator.pump` (transport, links, ping timers), `rt.wait` (sim stations/world). No overlap; `fit` uses no global RNG or module cache (`grep np.random` empty; `kinematics.Model._cache` is per model and not used by `fit`). `claw-frames` vs layout (L7) is unchanged by the fix | **AGREE** |
| H1-e exceptions | `fn`'s exception re-raised unchanged | `KeyError` raised two frames deep in `fn`: same type and instance, traceback shows `deep`, `inner`, `thread.py:run`, `_base.py:__get_result`; no leaked thread (`micro.py C`) | **AGREE** |
| H1-f abort path | the worker finishes in the background, result dropped, holds no robot resources | `ctx.wait` raising at its 3rd call during a real 60-frame flush: exception reaches the caller in **47-49 ms**; worker still alive, finishes **2.3-2.4 s later**, 3 trials of 3: layout file **rewritten after the abort** (3 -> 9 sheets), `ctx.floor_board` stale (1 tag vs 9 surveyed) until the next survey step (`micro.py D`). Reachability is low: `UdpHostTransport` swallows `OSError` on send/recv; only a bug in `pump`/`ingest` raises. Not harmful by itself (the sheets passed the survey's own criteria); a restart within ~2.5 s would share `ctx.board_survey`/`ctx.cal` with the zombie, unlocked (`BoardSurvey` and `Calibrator` have no locks; not reproduced); the pool thread is non-daemon, so interpreter exit waits for it (up to the fit's remaining time) | **AGREE** (Info, N5) |
| H1-g leaks | none | pytest plugin checking `threading.enumerate()` after every teardown of the four requested files: `startup-pumped` threads alive after a test: `[]`; threads at session end: `['MainThread']`. Full simulated startups (3 runs): `leaked_pump_threads: []` | **AGREE** |
| M1 formula | noise-only rate = sqrt(pi) sigma / (fx dt) | sigma 0.3: **1.0223e-2** rad/s (formula) vs MC 20,000 pairs **1.020 / 1.022 / 1.023 / 1.022e-2** for 1 / 2 / 4 / 9 tags; reviewer's MC 1.0e-2. sigma 0.5: 1.7044e-2 vs MC 1.708 / 1.701 / 1.704 / 1.706e-2. Linear in sigma | **AGREE** |
| M1 margin 1.4x | sensible; 0.5 px with 0.02 is correctly refused | 1.4 x floor = 0.0143 (0.3 px), **0.0239** (0.5 px), 0.0954 (2 px, <= 0.1: feasible). Per-pair pass at 1.4x: 93 / 98 / 99.8 % (1 / 2 / 4 tags). The real `wait_until_still` on a still claw (400 runs each, 15 s timeout, 5 pairs in a row): **1.4x floor: opens 100 %, median 0.5 s, max 2.0 s**; **0.5 px with 0.02 (1.17x): opens 100 %, median 0.9 s, p90 2.2 s, max 6.4 s (1 tag)**; limit = 1.0x floor: 98.5-99.5 %, median 2.4 s; 0.9x: 75 / 48 / 20 % (1 / 2 / 4 tags); 1.0 px with 0.02 (0.59x): **0 %**. 1.4x also covers a 1.4x under-set corner sigma (limit = 1.0x of the true floor still opens, 2.4 s) | **AGREE with the margin and the bound; the refusal of 0.5 px + 0.02 is stricter than needed** (the gate would open in ~1 s), a margin choice, not an impossibility |
| M1 message | actionable | names the key and value, the noise rate and its formula, the minimum limit (`at least 0.048` at 1 px, `0.024` at 0.5 px) and the other remedy (lower sigma / measure it). Wording "would see five quiet frame pairs in a row only rarely and could not approve" is true below ~0.9x, false for 0.9-1.4x | **AGREE** (wording condition) |
| M1 reason numbers | 75 % / 24 % at 1.2e-2, 95 % / 79 % at 1.5e-2, 3 tags 99.8 % / 99 % | MC (shared frames as in the gate): 1.2e-2: **75.6 %** per pair / 29.6 % five-in-a-row (24 % is 0.756^5, independence); 1.5e-2: **95.4 % / 80.3 %**; 3 tags 99.8 % / 99.0 % | **AGREE** (24 % -> 30 %, immaterial) |
| L1 | `rocking_tilt_k` lower bound 3 -> 4, reason with 98 / 12.7 / 0.15 % | bound 4.0; analytic 1 - (1 - exp(-k^2/2))^430 = 99.2 / 13.4 / 0.16 % at k = 3 / 4 / 5 (the review's simulation 98 / 12.7 / 0.15 %); the reason text carries the numbers and the review reference | **AGREE** |
| L2 | dwell-vs-timeout check removed: not needed | `wait_until_still` code: `timeout = max(timeout, dwell + 2 dt)` for `payload_kg > 0`; unloaded needs no dwell; the no-signal dwell is not bounded by the timeout. Shipped: loaded dwell 7.82 s vs timeout 15 s. Residual (Info): with `timeout <= dwell` the allowance for one noise exceedance or residual swing is 2 dt: a **still** claw at 0.3 px (1 tag) is approved **91.5 %** (200 seeds) at periods 5 / margin 3 / timeout 10 (dwell 18.8 s) and 95.5 % at periods 8 / timeout 10 (12.5 s), 100 % with 4 tags and with the shipped values | **AGREE** (removal is justified; "no combination unapprovable" is true in the sense >= 91 %, not 100 %) |
| L4 | `corner_sigma_px` lower bound 0.05 -> 0.15 | bound 0.15 (the cv2 corner bias of `floor_board_detector.md`), reason updated; `load_config` refuses 0.14, accepts 0.15 (test). Not asked and not done: a cross-check of `sigma x pose_cov_inflate` (0.15 x 1.0 is a covariance 6.8x smaller than the validated 0.3 x 1.3) | **AGREE** |
| config untouched | no `config/*.json` default changed; `slack_probe`, `lease_s` untouched | `git diff eb07a5d -- config/` is empty (no file in `config/` differs at all); both profiles load (`corner_sigma_px` 0.3, still 0.02 = 1.96x the floor) | **AGREE** |
| tests | 11 + 16 + 4 pass, 2 by design failing before the lead's edit | `tests/cdpr/test_keepalive_pumping.py` 11, `test_board_followups.py` 44, `test_board_followups_review.py` 16, `test_service.py` 4: **75 passed in 141.6 s** (with the thread-leak plugin). The lead's two edits (`EDGE_COMPANIONS["camera.corner_sigma_px"]`, the removed L2 `raises`) are what the results file proposes and are correct | **AGREE** |
| N1 (new) | -- | section 2 | **FINDING (High, hardware)** |
| N2 (new) | -- | section 3 | **FINDING (Medium)** |
| N3 (new) | -- | section 4 | **FINDING (Low)** |
| N4 (new) | -- | section 5 | **FINDING (Low)** |

## 1. The pump gap across a flush and across fits (H1-b/c)

Method: `Coordinator.pump` timestamps (`co.pump` wrapped; the gap is the wall time between consecutive calls); the flush through the real
`StartupSequencer._survey_topup` on an armed simulated robot with 60 offered frames (`micro.py A B`); fits captured from a real simulated startup
(probe off, seed 0), deep-copied and re-run through `StartupSequencer._pumped` with a stub `ctx.wait` that does what `Coordinator.wait` does on a
`RealRuntime` (`time.sleep(1 ms)`, then a pump timestamp, until 20 ms are up) on an otherwise idle machine (`fit_gap*.py`, `syn_fit.py`).

| call (this machine) | direct (unpumped) | pumped wall | max gap between pumps | lease / gap |
|---|---|---|---|---|
| 60-frame flush, CPU-bound sim wait | 2.21-2.28 s (7.4-7.6x lease) | 2.62-2.88 s | 36-49 ms | 6.1-8.3x |
| 60-frame flush, sleeping wait | -- | 2.68-2.93 s | 45-85 ms | 3.5-6.7x |
| `fit`, 1 sample (0.7 s) | 0.7 s | 0.85-1.03 s | 37-60 ms | 5-8x |
| `fit`, 19 samples (1.5 s) | 1.5 s | 1.8-2.2 s | 86-105 ms | 2.8-3.5x |
| `fit`, 31 samples (1.7 s) | 1.6-1.8 s | 2.1-2.7 s | 115-159 ms | 1.9-2.6x |
| `fit`, 31 samples (11-16 s, two simulated runs) | 11.1-13.2 s | 10.6-16.2 s | 154-301 ms | 1.0-1.9x |
| synthetic `fit`, 25 samples (`test_calibration` helpers) | 1.77 s | 2.0-2.1 s | 106-145 ms | 2.1-2.8x |
| synthetic `fit`, 60 samples | 4.15 s | 5.1-5.8 s | 203-291 ms | 1.0-1.5x |
| same fits at `sys.setswitchinterval(5e-4)` | -- | 1.6-4.5 s (shorter) | **34-52 ms** | 5.8-8.8x |

Inside the full startups (CPU-bound sim wait, per-call inner gaps, probe on, seed 0, fixed tree): flush calls of 2.2-3.8 s: 25-46 ms; fits of 0.8-2.9 s:
34-48 ms. With the CPU-bound wait the command thread is always runnable and the GIL is handed over at the 5 ms switch interval, so the simulator
(which the implementer's test uses: 31-72 ms) under-states the hardware gap; the sleeping wait is the representative case, and it is the one the
review's 25-28 ms measurement (a pure sleep loop against a numpy-only worker) did not cover for the fit's pure-Python-plus-numpy mix.
Stack samples of the worker at a >80 ms silence: `calibration._solve > _assign_slack > least_squares > call_minpack`, `np.linalg.norm`,
`np.searchsorted`: short GIL-releasing calls in a tight loop, the classic hand-off starvation. The ratio of the gap to the 5 ms switch interval
and the 5-8x improvement at 0.5 ms support the diagnosis.

## 2. N1: other long calls on the command thread while armed (High, hardware availability)

Full simulated startups on the fixed tree, probe off and on, seed 0, simulated clock NOT coupled (so they complete), each pump gap > 0.3 s sampled by a
watchdog thread (`gap_run2.py`):

| source | probe off (seed 0) | probe on (seed 0) |
|---|---|---|
| gaps > 0.3 s after `arm()` | 21 (max 2.32 s) | 17 (max 2.07 s) |
| `_stage > _feasible` (candidate filter, per stage) | 12 gaps, max 2.32 s | 8 gaps, max 2.07 s |
| `plan_line > _check_path` (path check of each planned move) | 9 gaps, max 1.17 s | 9 gaps, max 0.85 s |
| SELF_CHECK board survey (before `arm()`: stations unarmed) | 1 gap, 0.64 s (harmless) | 1 gap, 0.57 s |
| gaps that contain a fit or a flush | 0 | 0 |
| old tree `eb07a5d`, probe on, for comparison | -- | 20 gaps after arm, max 4.93 s; 5 of them contain a fit or a flush (4.93, 3.42, 2.25, 2.21, 2.11 s): the ones the fix removed |

Consequence with the simulated clock coupled to wall time (`COUPLE=1`: a stall between two pumps advances the stations by the stall with no ping):

| tree | outcome | stations at the end | first stall over the lease |
|---|---|---|---|
| `eb07a5d` (before the fix) | FAULT, "motion start window not acknowledged" | A-D State FAULT, **Fault.LEASE (4)** | 2.66 s at the first top-up (flush 1.08 s + fit 0.81 s) |
| HEAD (this fix) | FAULT, same reason | A-D State FAULT, **Fault.LEASE (4)** | 0.91 s in `_stage > _feasible`, first calibration stage |
| HEAD + `_feasible` and `_check_path` pumped (scratch emulation only) | **READY** (probe off, seed 0) | all IDLE, no fault | none; max gap after arm 0.25 s, 10 gaps > 0.15 s |

So the fix removes the two largest stalls but not the failure. Residual 0.15-0.25 s gaps (`design_excitation` 0.2 s, `cov_fn` / `visible_corners` 0.25 s, `plan_line`'s spool
tables 0.19 s, and the simulator's own plant solve `world._hang_checked` 0.22 s, which has no hardware counterpart) remain even then: with a 0.3 s lease the margin
on the command-thread ones is 1.2-2x on this CPU; the real host may be slower. (The split `_feasible` / `_check_path` in the table above is from a 7-frame stack sample and
approximate near the boundary; the totals are exact.) Test: `test_n1_*` (deterministic counts: 75 LPs and 0 pumps in the stage filter;
188 LPs per 1.3 m `plan_line`, which has no way to pump). Same caveat as H1: it matters only if the real `lease_s` is of the order of 0.3 s and the host as slow as this sandbox.

## 3. N2: GIL hand-off starves the pump during large fits (Medium)

See the table in section 1. Test: `test_n2_*` (synthetic 60-sample fit, sleeping wait: gap > 0.10 s and > 2x the gap at a 0.5 ms switch interval; 229 ms vs 49 ms in the run
above). The comment on `PUMP_STEP_S` ("the worst gap between two pumps is ~21 ms") and the results file's "on hardware ~21 ms" are not supported.

## 4. N3: the noise-floor cross-check assumes frame_interval_s = 0.1 s (Low)

`config.still_rate_noise_floor_rad_s` uses the constants `STILL_RATE_REF_FX_PX` (520) and `STILL_RATE_REF_DT_S` (0.1) although `startup.frame_interval_s`
is in the config (unbounded, used by `wait_until_still`). `load_config` accepts `corner_sigma_px` 0.5, limit 0.025, `frame_interval_s` 0.05: the true noise rate is
0.0341 rad/s (limit = 0.73x), and the real gate opens in **0 / 200** (4 tags) and 21 / 200 (1 tag) runs; at 0.1 s it opens every time. (`fx` is only in the intrinsics file, so
520 is a disclosed approximation; `dt` is not.) Test: `test_n3_*`. Fix: pass `cfg.startup.frame_interval_s` into the floor.

## 5. Other observations

* **N4 (Low): the simulator is no longer bit-reproducible.** The number of `ctx.wait(0.02)` steps during a pumped call depends on wall time. Same seed and code, probe off, two
  runs: simulated end 328.80 s vs 329.07 s, CALIBRATION entered at 118.15 vs 118.07 s; the old tree twice: 319.104 s, identical history. In three fixed-tree runs of probe on, seed 0, two
  were READY and one ended FAULT "calibration rejected: 1 outlier readings" (the old tree: READY, deterministic). Not shown to be caused by the pumping (an outlier rate under
  re-drawn noise is plausible), but seeded studies and tests of whole startups can now flip with CPU load. Do not compare simulated clock values bit-for-bit.
* **N5 (Info): abort path** (table, H1-f). A comment "(a flush may still write the layout file after the abort)" is in the results file; the demonstration is above.
* **N6 (Info): documentation lags.** `docs/CONTROL_SYSTEM_V1.md` lines 262-269 still state `corner_sigma_px` 0.05-2, `grip_still_rate_rad_s` 0.005-0.1, `rocking_tilt_k` 3-10 and "(and >= periods x
  margin x 1.5 s, or a loaded release could never be approved)"; the implementer said docs were out of scope.
* The L4 residual (sigma x inflate not cross-checked) and the L2 residual (2 dt allowance when `timeout <= dwell`) are Info, in the table.

## 6. Recommended bounded tasks (not done; for the lead)

1. **N1:** pump the candidate filter (a `ctx.wait(0.001)` every ~15 ms inside the `_stage` list comprehension, or `_pumped` per stage), `plan_line_from` at its call sites in `_stage`/`ctx` move helpers,
   and `design_excitation`; acceptance: a `COUPLE=1` full startup (seeds 0-2, probe off) ends with no Fault.LEASE and a largest post-arm gap < 0.1 s.
2. **N2:** `sys.setswitchinterval(5e-4)` inside `_pumped` (restore in `finally`), or a process worker; acceptance: max pump gap < 0.08 s across the synthetic 60-sample fit with a sleeping wait.
3. **N3:** use `cfg.startup.frame_interval_s` in the floor (and say so in the message); soften the message for the 0.9-1.4x band.
4. Whatever is done, set the hardware `faults.lease_s` from the measured worst post-arm gap on the real host (>= 4x), not from the sim value.
5. Update the stale lines of `docs/CONTROL_SYSTEM_V1.md` (N6) and the comment on `PUMP_STEP_S`.
When N1/N2 are fixed convert the matching tests of `tests/cdpr/test_keepalive_fix_review.py` (rename with `_fixed`, `# converted after fix: N1`).

## 7. What I did not check / limits

* Real hardware: lease, CPU, corner noise, claw-frames thread behaviour (no `ThreadedFrameSource` in the sim). The coupled-clock simulation only approximates a real runtime: simulated time advances by every host stall
  between two pumps, but the plant's own CPU time inside `rt.wait` is counted as a stall too (no hardware counterpart; the two decisive gaps are command-thread code, the plant ones are <= 0.22 s).
* The full 25-minute suite was not re-run (no reason found); the 4 requested files (75 tests) and my 4 new tests pass. Fit timings vary 1-16 s between simulated runs of the same seed (N4).
* Whether the one FAULT in three probe-on runs (N4) is caused by the pumping.

## 8. Reproduce

```
cd /home/user/RoomCleaner
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q tests/cdpr/test_keepalive_pumping.py tests/cdpr/test_board_followups.py tests/cdpr/test_board_followups_review.py tests/cdpr/test_service.py   # 75 passed, ~142 s
OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest -q -s tests/cdpr/test_keepalive_fix_review.py        # 4 passed, ~11 s; prints the measured stalls and gaps
git diff eb07a5d -- config/                                                                         # empty
S=/tmp/claude-0/-home-user-RoomCleaner/c51aa926-76d6-52eb-b707-af7c5e22fd24/scratchpad/fixrev        # scratch (session scratchpad, not in the repo)
cd $S; OMP_NUM_THREADS=1 /usr/bin/python3 micro.py A B C D        # flush gaps (CPU-bound and sleeping wait), direct baseline, exception, abort path
OMP_NUM_THREADS=1 /usr/bin/python3 fit_capture.py && OMP_NUM_THREADS=1 /usr/bin/python3 fit_gap3.py   # a real fit (writes $S/big_fit.pkl) through _pumped, 5 ms vs 0.5 ms switch interval
OMP_NUM_THREADS=1 /usr/bin/python3 fit_gap.py                                                       # the three slowest fits of a real startup, 3 repetitions each, sleeping wait
OMP_NUM_THREADS=1 /usr/bin/python3 syn_fit.py                                                       # synthetic 25 / 60-sample fits
OMP_NUM_THREADS=1 /usr/bin/python3 gap_run2.py 0 noprobe                                            # uncoupled: every pump gap > 0.15 s with the command thread's stack
COUPLE=1 OMP_NUM_THREADS=1 /usr/bin/python3 gap_run2.py 0 noprobe                                   # coupled clock: FAULT, Fault.LEASE on A-D (fixed tree)
COUPLE=1 ROOT=$S/tree_eb07a5d OMP_NUM_THREADS=1 /usr/bin/python3 gap_run2.py 0 noprobe              # same on `git archive eb07a5d` (extract it to $S/tree_eb07a5d first)
COUPLE=1 PUMP_EXTRA=1 OMP_NUM_THREADS=1 /usr/bin/python3 gap_run2.py 0 noprobe                      # emulated N1 remedy: READY
OMP_NUM_THREADS=1 /usr/bin/python3 m1_mc.py; /usr/bin/python3 m1_claims.py; /usr/bin/python3 dt_check.py; /usr/bin/python3 l2_check.py   # M1 / N3 / L2 numbers
OMP_NUM_THREADS=1 /usr/bin/python3 det_check.py tag                                                 # determinism fingerprint (ROOT=... for the old tree)
```
