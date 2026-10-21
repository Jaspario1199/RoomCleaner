"""Independent review of three-station mode (verification/three_station_mode_review.md).

Two kinds of test live here, exactly as in the earlier review files:

* PINS (finding ids F-xx in the test name): they PASS while the reviewed defect is present and say in their assertion message what
  the corrected behaviour must be, so that a fix is a deliberate act (flip the assertion in the same change as the fix).
* CHECKS: properties the reviewer verified independently (own ``np.linalg.solve``, own random poses, own hand calculation). They
  pass and must keep passing.

Nothing here changes production code. The slow tests (full simulated startups) use the FAST profile of the implementer's own helper
(``fast3``: 4 microsteps, 0.15 m/s), the same plant and logic as ``config/robot.sim3.json`` with a quicker clock.
"""
import ast
import http.client
import json
import math
import re
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from werkzeug.serving import make_server

from roomcleaner.cdpr.config import ConfigError, STATION_IDS, load_config, triangle_geometry
from roomcleaner.cdpr.kinematics import Geometry, geometry_from_config, tension_distribution, workspace_from_config
from roomcleaner.cdpr.service import BUSY_BACKOFF_S, Service, create_app, station_addresses
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.sim.world import FloorBoard
from roomcleaner.cdpr.supervisor import CommandRefused, Supervisor
from roomcleaner.cdpr.trajectory import PlanError, plan_line_from

from .simkit import bring_up, fast_cfg
from .test_three_station import EX3, SIM, SIM3, fast3, raw_of

ROOT = Path(__file__).resolve().parents[2]
CDPR = ROOT / "roomcleaner" / "cdpr"
GUIDE = (ROOT / "docs" / "THREE_STATION_MODE.md")
G = 9.81


# ======================================================================================================== host loop (F3 change)
def _real_time_robot(tmp_path):
    """A simulated robot whose runtime really sleeps 1 ms per ``wait(1000)`` like ``RealRuntime`` (the hardware path), with a spy on
    the keep-alive pings the coordinator sends to every station. Returns (robot, service, ping_times)."""
    r = SimRobot(fast_cfg(), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path)
    svc.poll_claw()
    co = r.ctx.co
    orig_wait = co.rt.wait

    def real_wait(dt_us):
        orig_wait(dt_us)
        time.sleep(dt_us / 1e6)
    co.rt.wait = real_wait
    pings = []
    orig_send = co._send

    def spy(dest, msg):
        if dest == "*" and msg.get("t") == "ping":
            pings.append(time.monotonic())
        return orig_send(dest, msg)
    co._send = spy
    return r, svc, pings


def _max_gap(times, t0, t1):
    ts = [t0] + [t for t in times if t0 <= t <= t1] + [t1]
    return max(b - a for a, b in zip(ts, ts[1:]))


def test_f3_fix_the_station_keep_alive_is_never_starved_idle_or_across_a_long_command(tmp_path):
    """CHECK of the lead's change to ``start_background``: with the hardware setting (``real_sleep_s=0.0``) the pings to the stations keep
    their ~20 ms period (lease 0.3 s) (1) while the claw idles READY-like with the lock free, (2) while a long command holds the lock and
    pumps the stations itself (the host loop only sleeps ``BUSY_BACKOFF_S`` and retries; it must not pump a second time or go silent),
    and (3) across the hand-over when the command ends (the loop is asleep for at most the back-off when the lock is released)."""
    r, svc, pings = _real_time_robot(tmp_path)
    co = r.ctx.co
    lease = r.ctx.cfg.faults.lease_s
    limit = 0.6 * lease                                          # well inside the lease: no station can see its lease expire (30 to 95 ms measured under load)
    assert BUSY_BACKOFF_S <= 0.02 <= lease / 4 + 1e-9            # the back-off is no longer than one ping period
    calls = [0]
    orig_tick = svc.idle_tick

    def counted(dt_s=0.02):
        calls[0] += 1
        return orig_tick(dt_s)
    svc.idle_tick = counted
    svc.start_background(real_sleep_s=0.0)
    try:
        time.sleep(0.3)
        # (1) idle, lock free
        t0 = time.monotonic()
        time.sleep(0.8)
        t1 = time.monotonic()
        idle_gap = _max_gap(pings, t0, t1)
        # (2) a long command: it owns the lock and pumps; the host loop must stay out of the way and not spin
        assert svc.lock.acquire(timeout=2.0)       # NOT blocking=False: that is finding H1 (the idle loop wins every non-blocking attempt)
        c0 = calls[0]
        t2 = time.monotonic()
        while time.monotonic() - t2 < 1.2:
            co.wait(5000)                                       # what _pumped / ctx.wait do
        t3 = time.monotonic()
        busy_calls = calls[0] - c0
        busy_gap = _max_gap(pings, t2, t3)
        svc.lock.release()
        # (3) hand-over: the loop resumes pumping within the back-off
        t4 = time.monotonic()
        time.sleep(0.8)
        t5 = time.monotonic()
        handover_gap = _max_gap(pings, t3 - 0.02, t5)
    finally:
        svc.stop_background()
    print(f"[F3] longest ping silence: idle {idle_gap * 1e3:.0f} ms, long command {busy_gap * 1e3:.0f} ms, hand-over {handover_gap * 1e3:.0f} ms "
          f"(lease {lease * 1e3:.0f} ms); idle_tick calls while the lock was held (1.2 s): {busy_calls}; pings {len(pings)}")
    assert idle_gap < limit, f"idle READY: longest silence to the stations {idle_gap * 1e3:.0f} ms (limit {limit * 1e3:.0f} ms)"
    assert busy_gap < limit, f"long command: longest silence {busy_gap * 1e3:.0f} ms (limit {limit * 1e3:.0f} ms)"
    assert handover_gap < limit, f"hand-over after the command: longest silence {handover_gap * 1e3:.0f} ms"
    assert busy_calls < 1.2 / BUSY_BACKOFF_S * 1.5, f"{busy_calls} idle_tick calls in 1.2 s with the lock held: the loop is spinning again"
    assert len(pings) > 100


def test_f3_fix_a_persistent_error_in_the_tick_does_not_spin_the_loop_or_kill_it(tmp_path):
    """CHECK: an exception from ``idle_tick`` every time (a transport error, say) is reported in ``last_error`` and the loop backs off
    (before the fix this branch also spun); it keeps trying, so a transient error cannot silence the keep-alive for good."""
    r, svc, pings = _real_time_robot(tmp_path)
    calls = [0]

    def boom(dt_s=0.02):
        calls[0] += 1
        raise RuntimeError("transport down")
    svc.idle_tick = boom
    svc.start_background(real_sleep_s=0.0)
    try:
        time.sleep(0.5)
    finally:
        svc.stop_background()
    assert svc.last_error and "transport down" in svc.last_error
    assert 20 < calls[0] < 200, calls[0]                          # ~100 at 5 ms: alive, not spinning


def test_h1_fixed_an_operator_command_gets_the_robot_lock_on_the_hardware_loop(tmp_path):
    """PIN F-H1 (High for tonight, pre-existing, NOT fixed by the F3 change). ``main()`` runs the hardware host loop with
    ``real_sleep_s=0.0``: ``idle_tick`` holds ``Service.lock`` for 20 ms (20 real 1 ms sleeps) and re-takes it microseconds after
    releasing it. ``_run`` (start, lower, disarm, ...) takes the same lock with ``acquire(blocking=False)`` from the HTTP thread, so it
    almost never wins and the phone shows "busy with 'None'". Here: the real threaded HTTP server, a runtime that really sleeps,
    the hardware loop setting; ``disarm`` (legal in DISARMED) is posted 100 times. Measured at review: 0 of 589 raw acquisitions in
    6 s; 23 of 590 with ``real_sleep_s=0.001``; 165 of 589 with 0.01.
    Fixed when ONE post is accepted (200): then flip to ``assert accepted >= 1`` (a command must never need luck)."""
    r, svc, pings = _real_time_robot(tmp_path)
    srv = make_server("127.0.0.1", 0, create_app(svc), threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    svc.start_background(real_sleep_s=0.0)                       # exactly what main() does for hardware
    accepted, busy_none, other = 0, 0, []
    try:
        time.sleep(0.3)
        for _ in range(100):
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
            conn.request("POST", "/api/command", body=json.dumps({"cmd": "disarm", "confirm": "claw_supported"}),
                         headers={"X-Token": svc.token, "Content-Type": "application/json"})
            resp = conn.getresponse()
            body = resp.read().decode()
            conn.close()
            if resp.status == 200:
                accepted += 1
            elif "busy with 'None'" in body:
                busy_none += 1
            else:
                other.append(body[:80])            # e.g. "busy with 'disarm'" after an accepted one: not a starvation sample
            time.sleep(0.015)
    finally:
        svc.stop_background()
        srv.shutdown()
        srv.server_close()
        t0 = time.time()
        while svc.busy and time.time() - t0 < 20:
            time.sleep(0.05)
    # H1 FIXED (lead, 2026-10-21): Service._run waits up to LOCK_WAIT_S for the idle loop to hand the lock over.
    assert accepted >= 1 and busy_none == 0, (
        f"H1 regressed: accepted={accepted}, 'busy with None'={busy_none}, other={other[:2]}: the idle loop starves operator commands")


def test_h1_the_suggested_fix_is_sufficient_on_the_hardware_loop(tmp_path, monkeypatch):
    """CHECK that the one-line fix suggested for H1 works end to end: ``Service._run`` re-compiled with
    ``if self.busy or not self.lock.acquire(timeout=0.3):`` instead of ``if not self.lock.acquire(blocking=False):`` (the code under test is
    patched in memory only; nothing on disk changes). Same set-up as the pin: real threaded HTTP server, runtime with real sleeps,
    ``real_sleep_s=0.0``. The first ``disarm`` post is accepted and the host loop keeps its keep-alive. Skipped once ``_run`` no longer has the
    non-blocking acquire."""
    import inspect
    import textwrap
    from roomcleaner.cdpr import service as service_mod
    src = textwrap.dedent(inspect.getsource(Service._run))
    old = "if not self.lock.acquire(blocking=False):"
    if old not in src:
        pytest.skip("H1 already fixed: Service._run no longer takes the lock with acquire(blocking=False)")
    ns = {}
    exec(compile(src.replace(old, "if self.busy or not self.lock.acquire(timeout=0.3):"), "<h1 fix>", "exec"), vars(service_mod), ns)
    monkeypatch.setattr(Service, "_run", ns["_run"])
    r, svc, pings = _real_time_robot(tmp_path)
    srv = make_server("127.0.0.1", 0, create_app(svc), threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    svc.start_background(real_sleep_s=0.0)
    statuses, t_first = [], None
    try:
        time.sleep(0.3)
        for _ in range(5):
            t0 = time.perf_counter()
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
            conn.request("POST", "/api/command", body=json.dumps({"cmd": "disarm", "confirm": "claw_supported"}),
                         headers={"X-Token": svc.token, "Content-Type": "application/json"})
            resp = conn.getresponse()
            body = resp.read().decode()
            conn.close()
            statuses.append((resp.status, body[:60]))
            if resp.status == 200:
                t_first = time.perf_counter() - t0
                break
            time.sleep(0.05)
    finally:
        svc.stop_background()
        srv.shutdown()
        srv.server_close()
        t0 = time.time()
        while svc.busy and time.time() - t0 < 20:
            time.sleep(0.05)
    assert statuses and statuses[-1][0] == 200, statuses
    assert t_first < 0.3, t_first


# ============================================================================================================ configuration
@pytest.mark.parametrize("key", ["stations_actve", "stations_activ", "active", "stations_enabled", "enabled_stations", "three_station",
                                 "stations.actve"])
def test_m2_pin_a_misspelt_active_key_that_the_guard_does_not_recognise_silently_runs_all_four(key):
    """PIN F-M2: ``_parse_active`` only recognises a stray top-level key that contains both 'active' and 'station' (so
    ``active_stations`` is caught). Any other spelling, ``stations_actve`` for one, is ignored without a word and the config loads
    as FOUR active stations. On hardware that is then stopped only because D has no address (SystemExit at start-up); if D's
    address is filled in, a fourth unit would be configured and armed. Fixed when ``load_config`` refuses every top-level key it does
    not know (underscore keys such as ``_comment`` excepted): flip to ``pytest.raises(ConfigError)``."""
    raw = raw_of(SIM3)
    del raw["stations_active"]
    raw[key] = ["A", "B", "C"]
    cfg = load_config(raw)
    assert cfg.ids == list(STATION_IDS), f"DEFECT M2 fixed? {key!r} now gives {cfg.ids}: flip this test"


def test_config_checks_sliver_boundary_and_inactive_station_exemptions():
    """CHECK of the validation the guide promises: the shortest altitude of the three anchors' floor triangle must be >= 0.25 m (0.26
    accepted, 0.24 refused); two ids, one id, duplicates, an unknown id and the key ``active_stations`` are refused with a message that
    names the problem; four stations are exempt from every triangle rule (a degenerate 4-station layout is not this mode's business)."""
    base = raw_of(SIM3)

    def with_c_y(y):
        r = json.loads(json.dumps(base))
        r["stations"][0]["anchor_room_m"] = [0.0, 0.0, 2.5]
        r["stations"][1]["anchor_room_m"] = [3.0, 0.0, 2.5]
        r["stations"][2]["anchor_room_m"] = [1.5, y, 2.5]
        return r
    assert load_config(with_c_y(0.26)).ids == ["A", "B", "C"]
    with pytest.raises(ConfigError, match="shortest altitude 0.24 m < 0.25 m"):
        load_config(with_c_y(0.24))
    for ids, msg in ((["A", "B"], "2 station"), (["A"], "1 station"), (["A", "B", "B"], "duplicate"), (["A", "B", "Z"], "unknown station id")):
        r = json.loads(json.dumps(base))
        r["stations_active"] = ids
        with pytest.raises(ConfigError, match=msg):
            load_config(r)
    r = json.loads(json.dumps(base))
    del r["stations_active"]
    r["active_stations"] = ["A", "B", "C"]
    with pytest.raises(ConfigError, match="unknown config key"):
        load_config(r)
    four = json.loads(json.dumps(base))
    del four["stations_active"]
    for i in range(3):
        four["stations"][i]["anchor_room_m"] = [0.0, 0.0, 2.5]           # collinear / coincident, but four stations are active
    assert load_config(four).n_active == 4


def test_a_station_left_without_an_anchor_entry_silently_becomes_a_room_corner():
    """CHECK (documents behaviour, Low): ``anchor_priors`` fills a missing entry with the room's upper corner of that station id, so a
    three-station config whose C entry is deleted gets C in the far corner (3.35, 2.74), not the middle of the far wall, and a
    start point 12 cm off the guide's (1.68, 0.93). The shipped example sets all three; a deleted entry is not reported."""
    raw = raw_of(EX3)
    raw["stations"][2]["anchor_room_m"] = None
    c = load_config(raw)
    assert np.allclose(c.anchor_priors()[2], [3.3528, 2.7432, 2.7432])
    assert np.linalg.norm(c.start_point_xy() - np.array([1.6764, 0.9311])) > 0.5


# ======================================================================================================== statics and margins
def _point_geo(cfg):
    return Geometry(cfg.anchor_priors(), np.zeros((3, 3)))


def test_three_cable_tensions_match_an_independent_solve_and_a_hand_calculation_at_the_centroid():
    """CHECK: T from ``tension_distribution`` == ``np.linalg.solve(u.T, w)`` (own call, any pose, 0 / +2 / -2 m/s2) and, at the
    centroid with lambda_i = 1/3, the hand formula T_i = (W/3) L_i / (H - z) (anchors at one height H)."""
    cfg = load_config(SIM3)
    A = cfg.anchor_priors()
    geo = _point_geo(cfg)
    rng = np.random.default_rng(3)
    for _ in range(40):
        xy = rng.dirichlet([2, 2, 2]) @ A[:, :2]
        p = np.array([xy[0], xy[1], rng.uniform(0.6, 2.1)])
        for az in (0.0, 2.0, -2.0):
            m = float(rng.uniform(0.3, 1.5))
            u = (A - p) / np.linalg.norm(A - p, axis=1, keepdims=True)
            own = np.linalg.solve(u.T, m * np.array([0.0, 0.0, G + az]))
            got = tension_distribution(geo, p, m, t_min=-1e9, t_max=1e9, accel=(0, 0, az)).tensions
            assert np.allclose(got, own, rtol=1e-9, atol=1e-9)
    c = A[:, :2].mean(0)
    m, z = 0.45, 0.517
    p = np.array([c[0], c[1], z])
    L = np.linalg.norm(A - p, axis=1)
    hand = (m * G / 3.0) * L / (A[0, 2] - z)
    got = tension_distribution(geo, p, m, t_min=0.5, t_max=15.0)
    assert got.feasible and np.allclose(got.tensions, hand, atol=1e-9)
    assert got.tensions == pytest.approx([1.9708, 1.9708, 1.9300], abs=2e-4)           # the guide's "about 2 N per cable"


def test_m6_the_lift_tilt_margin_is_about_9_mm_of_centre_of_mass_error():
    """CHECK of M6: hanging from three of the box's four corners tilts the claw by (CoM offset from the centroid of the three holes) /
    (CoM depth 0.196 m): 5.5 degrees at the start point on the CAD CoM, against the 8 degree lift abort. ``claw.com_body_m`` is a CAD estimate
    without electronics. A 10 mm shift toward the empty D corner (body -x, +y) reaches 8 degrees, 8 mm does not; the best direction removes tilt."""
    raw = raw_of(SIM3)
    raw["claw"]["mass_kg"] = 0.45
    base = np.array(raw["claw"]["com_body_m"], float)

    def tilt(shift_mm, az_deg):
        r = json.loads(json.dumps(raw))
        d = np.array([math.cos(math.radians(az_deg)), math.sin(math.radians(az_deg)), 0.0]) * shift_mm / 1000.0
        r["claw"]["com_body_m"] = list(base + d)
        cfg = load_config(r)
        geo = geometry_from_config(cfg, cfg.anchor_priors(), 0.0)
        c = cfg.start_point_xy()
        sol = geo._att.solve(np.array([c[0], c[1], 0.592]))
        assert sol.ok
        return math.degrees(math.hypot(sol.roll, sol.pitch))
    assert tilt(0, 0) == pytest.approx(5.5, abs=0.05)
    assert tilt(8, 135) < 8.0 < tilt(10.5, 135) and tilt(15, 135) > 9.0
    assert tilt(10, 315) < 3.0                                            # the other way it helps
    assert math.radians(8.0) == pytest.approx(load_config(EX3).startup.max_tilt_rad)


@pytest.mark.parametrize("mass", [0.375, 0.45, 0.6])
def test_the_edge_margin_keeps_every_tension_at_or_above_the_floor_at_any_height_for_the_point_and_the_real_claw(mass):
    """CHECK (item 4): ``lambda_i >= T_floor / (m g)`` guarantees ``T_i >= T_floor`` for the point claw at any height (anchors at one
    height) and, with the real spaced attachments / CoM / predicted tilt, the tension stays >= T_floor at the boundary of the margin
    triangle at 0 and +2 m/s2 and (a stricter case than the code plans for) -2 m/s2. 3000 random poses, half of them ON the boundary."""
    raw = raw_of(SIM3)
    raw["claw"]["mass_kg"] = mass
    cfg = load_config(raw)
    A = cfg.anchor_priors()
    lam = cfg.tension_floor_fraction()
    assert lam == pytest.approx(0.5 / (mass * G))
    pt, real = _point_geo(cfg), geometry_from_config(cfg, A, 0.0)
    rng = np.random.default_rng(5)
    worst_pt, worst_real = {0: 9.0, 2: 9.0, -2: 9.0}, {0: 9.0, 2: 9.0, -2: 9.0}
    for _ in range(3000):
        if rng.random() < 0.5:
            j = int(rng.integers(3))
            l = np.empty(3)
            l[j] = lam
            k = [x for x in range(3) if x != j]
            l[k[0]] = lam + (1 - 3 * lam) * rng.random()
            l[k[1]] = 1 - l[j] - l[k[0]]
        else:
            l = rng.dirichlet([1, 1, 1]) * (1 - 3 * lam) + lam
        xy = l @ A[:, :2]
        p = np.array([xy[0], xy[1], rng.uniform(0.59, 2.19)])
        for az in (0, 2, -2):
            T = np.linalg.solve(pt.unit_vectors(p).T, mass * np.array([0.0, 0.0, G + az]))
            worst_pt[az] = min(worst_pt[az], float(T.min()))
            r = tension_distribution(real, p, mass, t_min=0.5, t_max=99.0, accel=(0, 0, az))
            worst_real[az] = min(worst_real[az], float(r.tensions.min()))
    assert worst_pt[0] >= 0.5 - 1e-9 and worst_pt[2] >= lam * mass * (G + 2) - 1e-9 and worst_pt[-2] >= lam * mass * (G - 2) - 1e-9, worst_pt
    assert worst_pt[2] >= 0.5                              # an upward 2 m/s2 only adds
    assert worst_real[0] >= 0.5 and worst_real[2] >= 0.5 and worst_real[-2] >= 0.5, worst_real
    # the bound is conservative by sin(elevation): the point claw at the boundary is never tight against 0.5 N
    assert worst_pt[0] > 0.5


def test_the_margins_are_031_from_the_two_diagonal_sides_and_030_from_the_ab_wall_side_for_a_045_kg_claw():
    """CHECK (item 4): the guide's two margins (0.31 / 0.30 m for 0.45 kg; 0.235 / 0.225 m for 0.6 kg) are right in size. The side each
    belongs to is not what the guide says (see ``test_l1_pin_...``): the edge OPPOSITE station C is the A-B wall side (altitude 2.643 m
    -> 0.299 m), the edges opposite A and B are the diagonals (altitude 2.771 m -> 0.314 m)."""
    for mass, diag, wall in ((0.45, 0.314, 0.299), (0.6, 0.235, 0.225)):
        raw = raw_of(SIM3)
        raw["claw"]["mass_kg"] = mass
        cfg = load_config(raw)
        g = triangle_geometry(cfg.anchor_priors()[:, :2])
        lam = cfg.tension_floor_fraction()
        assert g["altitudes_m"] == pytest.approx([2.771, 2.771, 2.643], abs=1e-3)
        margins = lam * g["altitudes_m"]
        assert margins[0] == pytest.approx(diag, abs=1e-3) and margins[1] == pytest.approx(diag, abs=1e-3)
        assert margins[2] == pytest.approx(wall, abs=1e-3)
        # the claw is closest to the A-B wall, where the margin is the SMALLER one
        assert margins[2] < margins[0]
        ws = workspace_from_config(cfg, cfg.anchor_priors(), lowest_point_z=float(cfg.claw.lowest_point_body_m[2]))
        near_ab = np.array([1.6764, 0.05 + wall + 0.01, 1.0])
        assert ws.triangle_violation(near_ab) is None                                  # just inside the wall-side margin
        assert ws.triangle_violation(np.array([1.6764, 0.05 + wall - 0.01, 1.0])) is not None


def test_l1_pin_the_guide_and_the_results_attribute_the_two_margins_to_the_wrong_sides():
    """PIN F-L1 (Low, documentation): ``docs/THREE_STATION_MODE.md`` section 5 says "0.31 m from the A-B wall side and 0.30 m from each
    diagonal side (0.235 m / 0.225 m ...)". The code (and ``workspace_summary``) give the A-B wall side the SMALLER margin: 0.30 m
    (0.225 m for 0.6 kg) and each diagonal 0.31 m (0.235 m). Fixed when the guide says 0.30 m for the wall side."""
    text = GUIDE.read_text()
    assert "0.31 m from the A-B wall side and 0.30 m from each diagonal side" in text, \
        "DEFECT L1 fixed? the guide no longer says that: flip this test to assert the corrected sentence"
    assert "(0.235 m / 0.225 m for the simulator's 0.6 kg claw)" in text


def test_l2_pin_the_guide_says_the_room_centre_is_2_ft_closer_to_c_but_it_is_44_cm():
    """PIN F-L2 (Low, documentation): section 4 says the room centre is "2 ft closer to C" than the start point. It is 0.440 m =
    1 ft 5 in (room centre y 1.372 m, centroid y 0.931 m); the safety section says 0.44 m. Fixed when the guide says about 1 ft 5 in."""
    cfg = load_config(EX3)
    d = cfg.room_m[1] / 2 - cfg.start_point_xy()[1]
    assert d == pytest.approx(0.4405, abs=1e-3) and d / 0.3048 == pytest.approx(1.445, abs=0.01)
    assert "the room centre is\n  2 ft closer to C" in GUIDE.read_text() or "2 ft closer to C" in GUIDE.read_text(), \
        "DEFECT L2 fixed? the guide no longer says '2 ft closer to C': flip this test"


def test_the_guides_start_point_and_heading_prior_agree_with_the_code():
    """CHECK (item 6): start point (1.68, 0.93) = centroid = 5 ft 6 in along the wall and 3 ft 0.6 in out from it; the marker heading
    prior -2.645 rad is the direction from the start point to station A (the sim3 profile has -2.6451)."""
    cfg = load_config(EX3)
    sx, sy = cfg.start_point_xy()
    assert (round(sx, 2), round(sy, 2)) == (1.68, 0.93)
    assert sx / 0.3048 == pytest.approx(5.5, abs=0.01) and sy / 0.3048 == pytest.approx(3.054, abs=0.01)         # 3 ft 0.65 in
    a = cfg.anchor_priors()[0]
    heading = math.atan2(a[1] - sy, a[0] - sx)
    assert heading == pytest.approx(-2.645, abs=1e-3)
    assert load_config(SIM3).marker.heading_prior_rad == pytest.approx(heading, abs=1e-3)
    assert load_config(EX3).marker.heading_prior_rad is None                          # the guide tells the operator to enter it
    text = GUIDE.read_text()
    assert "-2.645" in text and "(1.68, 0.93)" in text


def test_every_refusal_text_in_the_guides_table_exists_in_the_code_and_every_config_key_it_names_exists():
    """CHECK (item 6): the refusal messages of section 8 are produced by the code; the config keys of section 3 exist in the loaded
    config (so a typo in the guide would be caught)."""
    src = "\n".join(p.read_text() for p in CDPR.glob("*.py"))
    for needle in ("needs 3 or 4 distinct ids", "are collinear or coincide", "span a degenerate triangle", "unknown config key",
                   "the claw rests where three cables cannot lift it", "slide directions disagree with the anchor entries",
                   "check station order/wiring", "it must be at least", "the edge opposite station", '"outside"'):
        assert needle in src, needle
    cfg = load_config(EX3)
    for dotted in ("claw.mass_kg", "marker.edge_m", "marker.heading_prior_rad", "camera.intrinsics_file", "camera.max_frame_age_s",
                   "motion.max_tension_n", "startup.max_slack_m", "authorization.suspended_motion_authorized",
                   "claw.address", "faults.lease_s", "startup.max_tilt_rad", "marker.position_prior_room_m"):
        obj = cfg
        for part in dotted.split("."):
            assert hasattr(obj, part), dotted
            obj = getattr(obj, part)
    assert cfg.startup.max_tilt_rad == pytest.approx(math.radians(8.0))                # "(8 degrees)"
    assert cfg.motion.min_tension_n == 0.5 and cfg.motion.task_max_height_m == 1.6
    assert cfg.startup.slack_probe is False                                           # "LOCAL_ONLY is the normal result"
    text = GUIDE.read_text()
    for k in ("stations_active", "drive.max_step_rate_hz", "encoder.sign", "spool.line_diameter_m", "spool.line_total_m", "claw.mass_kg"):
        assert k in text


# ================================================================================================ no hidden four-cable fallback
def test_no_loop_or_array_over_stations_is_hard_wired_to_four_in_the_host_code():
    """CHECK (item 1): scan of ``roomcleaner/cdpr`` (AST, not grep). The only ``range(4)`` left are the four CORNERS of a marker tag; the
    only ``(4, 3)`` shape literals are the config's attachment-point array of the FILE (all four station records are in the file; the
    active ones are picked from it by id, ``attachment_points``) and the render's quad; no ``[:4]`` slice, ``zeros/ones(4)`` or
    ``reshape(4`` remains; the station-id tuples ``IDS`` / ``STATION_IDS`` / ``"ABCD"`` are used only to apply the active set on top
    (config), as a label default (homing), for old saved files without ``ids`` (calibration, startup) and as the default
    ledger of ``TrustLedger()`` (every production construction goes through ``TrustLedger.for_ids``). A new hit is a conscious act."""
    hits = []
    for path in sorted(CDPR.glob("*.py")) + sorted((CDPR / "sim").glob("*.py")):
        src = path.read_text()
        lines = src.splitlines()
        for node in ast.walk(ast.parse(src)):
            seg = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" \
                    and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value == 4:
                seg = "range(4)"
            elif isinstance(node, ast.Slice) and isinstance(node.upper, ast.Constant) and node.upper.value == 4 and node.lower is None:
                seg = "[:4]"
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("zeros", "ones", "full", "reshape") \
                    and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 4:
                seg = f"{node.func.attr}(4"
            elif isinstance(node, ast.Tuple) and len(node.elts) == 2 and all(isinstance(e, ast.Constant) for e in node.elts) \
                    and tuple(e.value for e in node.elts) == (4, 3):
                seg = "(4, 3)"
            if seg:
                hits.append((path.name, node.lineno, seg, lines[node.lineno - 1].strip()))
    assert {(f, sg) for f, _, sg, _ in hits} == {("calibration.py", "range(4)"), ("service.py", "range(4)"), ("world.py", "range(4)"),
                                                  ("config.py", "(4, 3)"), ("render.py", "full(4")}, hits
    assert all("uv[(k + 1) % 4]" in text for _, _, sg, text in hits if sg == "range(4)"), hits
    ids_use = {}
    for path in sorted(CDPR.glob("*.py")):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"\bSTATION_IDS\b|\bIDS\b|\"ABCD\"", line) and not line.strip().startswith(("#", '"""')):
                ids_use.setdefault(path.name, []).append(i)
    assert set(ids_use) == {"calibration.py", "config.py", "homing.py", "startup.py", "trust.py"}, ids_use
    # every production construction of a ledger is over the active ids
    prod = {p.name: p.read_text() for p in list(CDPR.glob("*.py")) + list((CDPR / "sim").glob("*.py"))}
    assert not [n for n, t in prod.items() if re.search(r"\bTrustLedger\(\)", t) and n != "trust.py"]


def test_station_d_is_never_addressed_in_the_simulator_or_over_udp(tmp_path):
    """CHECK (item 1): bring-up of the sim3 robot (configure + arm + 1 s of pumping) sends nothing to D and D has no node, link,
    ledger entry or firmware parameter set; the UDP transport built from ``station_addresses`` for the hardware example has exactly three
    destinations, a '*' broadcast reaches those three sockets only, and D is unknown to ``send``."""
    r = SimRobot(fast3(), seed=3, data_dir=tmp_path)
    sent = []
    orig = r.net.send

    def spy(src, dest, msg, now):
        sent.append((src, dest, msg.get("t")))
        return orig(src, dest, msg, now)
    r.net.send = spy
    bring_up(r.co)
    r.co.wait(1_000_000)
    assert sent and not any(s == "D" or d == "D" for s, d, _ in sent)
    assert {d for _, d, _ in sent if d not in ("host", "*")} <= {"A", "B", "C"}
    assert "D" not in r.co.links and "D" not in r.ctx.ledger.stations and "D" not in r.net.inbox
    with pytest.raises(KeyError):
        r.cfg.station_firmware_params("D")
    # UDP: the hardware example with addresses filled in
    raw = raw_of(EX3)
    for sid, port in zip("ABC", (9001, 9002, 9003)):
        raw["stations"]["ABC".index(sid)]["address"] = f"127.0.0.1:{port}"
    raw["claw"]["address"] = "127.0.0.1:9100"
    cfg = load_config(raw)
    addrs = station_addresses(cfg)
    assert sorted(addrs) == ["A", "B", "C"]
    raw["stations"][3]["address"] = "127.0.0.1:9004"                                    # an address on D changes nothing
    assert sorted(station_addresses(load_config(raw))) == ["A", "B", "C"]
    from roomcleaner.cdpr.transport import UdpHostTransport
    sock_log = []
    tx = UdpHostTransport(addrs, bind=("127.0.0.1", 0))
    real_sock = tx.sock

    class Spy:
        def sendto(self, data, addr):
            sock_log.append(addr)

        def __getattr__(self, k):
            return getattr(real_sock, k)
    tx.sock = Spy()
    tx.send("*", {"t": "ping"})
    assert sorted(sock_log) == sorted(addrs.values()) and ("127.0.0.1", 9004) not in sock_log
    with pytest.raises(KeyError):
        tx.send("D", {"t": "ping"})
    real_sock.close()


# ==================================================================================================== simulated three-station startups
_RUNS: dict = {}


def _startup(seed, **cfg_over):
    key = (seed, tuple(sorted(cfg_over.items())))
    if key not in _RUNS:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix=f"three_review_{seed}_"))
        r = SimRobot(fast3(**cfg_over), seed=seed, data_dir=tmp, camera_kw={"board": FloorBoard.nominal(0.15)})
        sup = Supervisor(r.ctx, state_path=tmp / "state.json", ledger_path=tmp / "ledger.json")
        rep = sup.start()
        _RUNS[key] = (r, sup, rep, tmp)
    return _RUNS[key]


@pytest.mark.parametrize("seed", [3, 5, 7])
def test_m1_pin_three_station_startups_with_other_seeds_abort_in_pretension_with_a_false_drag_trip(seed):
    """PIN F-M1 (Medium for tonight, fail-safe): three-station startups stop at PRETENSION with "claw dragged while tensioning" for 3 of
    the 8 seeds 0-7 (3, 5, 7; READY on 0, 1, 2, 4, 6). Cause, measured in the simulator: the pretension target ("just taut" from the take-up
    fit) overshoots the true cable lengths by 0.3-0.6 mm (tension = EA/L x stretch = 7 N/mm), the three cables then carry the whole weight
    at once, the claw lifts off its jaws and TILTS about 6 degrees (three of the box's four corners; the predicted 5.5 degrees) and the
    drag watch, which assumes "a claw resting on the floor cannot change its tilt" (``perception.floor_displacement``) and reads the tag
    through the camera 0.5 m above the floor, reports 15-18 mm of "drag" while the claw moved only 5 mm. The claw is safe on the floor
    (RECOVERY_REQUIRED, stations holding), but the startup does not complete. With four cables the same seeds complete PRETENSION with
    the claw on the floor (tilt 0.0 degrees). Fixed when these seeds reach READY (or the lift-off tilt is allowed for): flip to
    ``rep.outcome == 'READY'``."""
    r, sup, rep, tmp = _startup(seed)
    assert rep.outcome != "READY" and sup.state == "RECOVERY_REQUIRED", \
        f"DEFECT M1 fixed? seed {seed} now ends {rep.outcome}/{sup.state} ({rep.reasons}): flip this test"
    assert any("pretension: claw dragged while tensioning" in x for x in rep.reasons), rep.reasons
    assert all(r.co.links[s].tel["flt"] == 0 and r.ctx.ledger.stations[s].valid for s in "ABC")      # nothing faulted, all holding
    assert r.world.eq_failures == 0


def test_m1_pin_the_claw_has_lifted_off_with_a_tilt_when_the_drag_watch_trips():
    """PIN F-M1 (evidence): at the moment the watch trips (seed 3) the real claw is OFF the floor, tilted 5-7 degrees and has moved
    under 8 mm: the 17 mm the watch reports is mostly the tilt lever of the camera, not a slide."""
    r, sup, rep, tmp = _startup(3)
    w = r.world
    tilt = math.degrees(math.acos(float(np.clip(w.R[2, 2], -1, 1))))
    assert not w.on_floor and 4.0 < tilt < 8.0, (w.on_floor, tilt)
    assert float(np.sum(w.tension)) > 0.9 * w.mass * G                     # the cables carry (about) the whole weight
    reported = max(float(re.search(r"\(([0-9.]+)\)", x).group(1)) for x in rep.reasons if "dragged" in x)
    assert reported > 0.014                                                 # what the watch reported (m)


def test_a_ready_robot_moves_300_mm_refuses_the_missing_corner_before_motion_and_lowers_to_the_floor_from_a_displaced_pose():
    """CHECK (item 5 and the guide's step 9), seed 6 (not one of the implementer's seeds; seed 7 aborts, see the M1 pins):
    READY / LOCAL_ONLY with a stated reason, no station faults, D nowhere; a 300 mm move inside the area completes (the real claw moves
    0.30 +- 0.02 m, no fault, still READY); moves toward the missing D corner are refused by the planner and by the task layer's
    ``TrustedVolume`` BEFORE any motion (no motion id consumed, positions untouched); after a move to (1.68, 1.5, 1.3 m) the supervisor's
    ``lower`` (the guide's step 9, not exercised by the implementer's tests) parks the claw on the floor (PARKED, vision-confirmed, no
    equilibrium failure, no station fault) and ``disarm`` returns DISARMED."""
    r, sup, rep, tmp = _startup(6)
    assert rep.outcome == "READY" and sup.state == "READY", (rep.outcome, rep.reasons)
    assert r.ctx.ledger.level in ("VERIFIED", "LOCAL_ONLY")
    if r.ctx.ledger.level == "LOCAL_ONLY":
        assert r.ctx.ledger.trust_reasons and "slack probe was off" in r.ctx.ledger.trust_reasons[0]
    assert all(r.co.links[s].tel["flt"] == 0 for s in "ABC") and "D" not in r.co.links and r.world.eq_failures == 0
    ctx, co = r.ctx, r.co
    here = ctx.model.pose_from_positions(co.positions())[0]
    truth0 = r.world.p.copy()
    target = None
    for a in np.arange(0, 2 * np.pi, np.pi / 4):
        q = here + 0.3 * np.array([np.cos(a), np.sin(a), 0.0])
        if not ctx.ws.violations(ctx.model.geometry, q):
            target = q
            break
    assert target is not None
    res = co.execute(plan_line_from(ctx.model, co.positions(), target, ctx.lim, ws=ctx.ws, label="review 300 mm"))
    assert res.ok, res.reason
    assert np.linalg.norm(r.world.p - truth0) == pytest.approx(0.3, abs=0.02)
    assert all(co.links[s].tel["flt"] == 0 for s in "ABC") and sup.state == "READY"
    # toward the missing corner: refused before any motion, by the planner and by the task layer's volume
    pos0, mid0 = co.positions().copy(), co.motion_id
    here = ctx.model.pose_from_positions(co.positions())[0]
    for tgt_xy in ((0.4, 2.1), (0.05, 2.69), (0.8, 1.9), (1.0, 2.0)):
        with pytest.raises(PlanError, match="workspace: floor point .* the edge opposite station"):
            plan_line_from(ctx.model, co.positions(), np.array([tgt_xy[0], tgt_xy[1], here[2]]), ctx.lim, ws=ctx.ws, label="toward D")
    from roomcleaner.cdpr.tasks import TrustedVolume
    vol = TrustedVolume(ctx)
    for z in (0.7, 1.0, 1.5):
        assert not vol.allows(np.array([0.3, 2.3, z])) and not vol.allows(np.array([3.0, 0.3, z]))     # toward D / at B's corner
    assert np.array_equal(co.positions(), pos0) and co.motion_id == mid0
    # a displaced pose, then the guide's step 9
    tgt = np.array([1.676, 1.5, 1.3])
    assert not ctx.ws.violations(ctx.model.geometry, tgt)
    assert co.execute(plan_line_from(ctx.model, co.positions(), tgt, ctx.lim, ws=ctx.ws, label="displace")).ok
    sup.lower()
    assert sup.state == "PARKED" and r.world.on_floor and r.world.eq_failures == 0
    assert all(co.links[s].tel["flt"] == 0 for s in "ABC")
    sup.disarm("claw_supported")
    assert sup.state == "DISARMED"


def test_m4_pin_the_calibration_box_sends_most_poses_far_outside_the_40_degree_outlet_cone():
    """PIN F-M4 (Medium, known open item): there is no outlet-angle limit in the planner. For a 0.45 kg claw, over the feasible poses of the
    startup's calibration box (start point +-0.8 m, z 0.59 to 1.6 m) the cable leaves the outlet up to 68 degrees from vertical and more than
    80 % of the poses are above 40 degrees at each of A, B and C (the start point itself: A 41.7, B 41.7, C 40.3 for the point claw of the guide; 40.8 / 40.9 / 39.6 with the real attachment points and tilt). Fixed when the planner or the
    calibration box respects an outlet limit: flip to a bound on the maximum angle."""
    raw = raw_of(SIM3)
    raw["claw"]["mass_kg"] = 0.45
    cfg = load_config(raw)
    A = cfg.anchor_priors()
    geo = geometry_from_config(cfg, A, 0.0)
    ws = workspace_from_config(cfg, A, lowest_point_z=float(cfg.claw.lowest_point_body_m[2]))
    c = cfg.start_point_xy()
    p0 = np.array([c[0], c[1], 0.517])
    ang_pt = np.degrees(np.arccos(Geometry(A, np.zeros((3, 3))).unit_vectors(p0)[:, 2]))
    assert ang_pt == pytest.approx([41.7, 41.7, 40.3], abs=0.1)                 # the guide's numbers are for the point claw
    ang0 = np.degrees(np.arccos(geo.unit_vectors(p0)[:, 2]))                    # real attachment points and predicted tilt
    assert ang0 == pytest.approx([40.8, 40.9, 39.6], abs=0.3) and np.max(np.abs(ang0 - ang_pt)) < 1.3
    mx, over, tot = np.zeros(3), np.zeros(3), 0
    for dx in np.arange(-0.8, 0.801, 0.1):
        for dy in np.arange(-0.8, 0.801, 0.1):
            for z in np.arange(0.592, 1.6, 0.1):
                p = np.array([c[0] + dx, c[1] + dy, z])
                if ws.violations(geo, p) or not tension_distribution(geo, p, 0.45, t_min=0.5, t_max=11.25).feasible:
                    continue
                ang = np.degrees(np.arccos(np.clip(geo.unit_vectors(p)[:, 2], -1, 1)))
                mx, over, tot = np.maximum(mx, ang), over + (ang > 40), tot + 1
    assert tot > 1500 and np.all(mx > 60) and np.all(mx < 72), (tot, mx)
    assert np.all(over / tot > 0.80), over / tot


def test_m5_l4_pin_the_guide_is_silent_on_the_floor_board_and_on_weighing_the_claw():
    """PIN F-M5 / F-L4 (documentation): the guide never mentions the printed floor board (``marker.board_layout_file``) although every
    simulated three-station startup of the results uses it, says the single-tag LOCAL_ONLY reason is "slack probe was off", and gives
    "the budget is 0.45 kg" for ``claw.mass_kg`` without saying to enter the weighed mass. Fixed when the guide says so: flip."""
    text = GUIDE.read_text().lower()
    assert "board" not in text and "board_layout_file" not in text
    assert "weigh" not in text and "the budget is 0.45 kg" in text


def test_l5_pin_the_start_point_check_is_skipped_when_the_workspace_is_missing(tmp_path):
    """PIN F-L5 (Low): ``tv = None if ctx.ws is None else ...`` (startup.py): with no workspace the INITIAL_LIFT start-point check passes
    silently. Not reachable after the take-up fit (``apply_result`` always sets ``ws``). Fixed when ``None`` refuses: flip."""
    src = (CDPR / "startup.py").read_text()
    assert "tv = None if ctx.ws is None else ctx.ws.triangle_violation(p0)" in src
    from roomcleaner.cdpr.startup import RobotContext
    r = SimRobot(fast3(), seed=0, data_dir=tmp_path)
    assert r.ctx.ws is None                                                  # a fresh context has none until the model is set
    assert isinstance(r.ctx, RobotContext)


def test_d1_pin_a_simulator_rehearsal_leaves_state_that_makes_the_real_service_start_in_recovery_required(tmp_path):
    """PIN F-M3 (Medium, operator guide): steps 3 and 4 of the guide run the simulator and then the real service with the SAME default
    ``--data`` directory (``data/cdpr``): the guide never mentions ``--data``. A rehearsal that ends READY (or any aborted
    start) leaves ``claw_supported = false`` in ``state.json``; the next launch then enters RECOVERY_REQUIRED ("host restarted while the claw
    may be suspended"), where ``start`` is refused, and it also loads the simulator's ``model.json`` for the same A/B/C. Here the
    aborted seed-7 start stands in for the rehearsal. Fixed when the guide tells the operator to give each run its own ``--data`` (or the
    service refuses to reuse a data directory written by ``--sim``): flip to ``sup2.state == 'DISARMED'``."""
    r, sup, rep, tmp = _startup(7)
    import shutil
    shutil.copytree(tmp, tmp_path / "data")
    r2 = SimRobot(fast3(), seed=8, data_dir=tmp_path / "data")                 # the "real" run: other plant, same data directory
    sup2 = Supervisor(r2.ctx, state_path=tmp_path / "data" / "state.json", ledger_path=tmp_path / "data" / "ledger.json")
    assert sup2.state == "RECOVERY_REQUIRED", f"DEFECT M3 fixed? the new run starts {sup2.state}: flip this test"
    with pytest.raises(CommandRefused, match="'start' not allowed in RECOVERY_REQUIRED"):
        sup2._require("start")
    assert "--data" not in GUIDE.read_text()


def test_four_station_startup_still_reaches_ready_and_the_default_config_is_unchanged():
    """CHECK (item 2): ``config/robot.sim.json`` (no ``stations_active`` key) -> four active stations, the unchanged checklist and a full
    simulated startup (fast profile, seed 0, the 3 x 3 floor board) reaching READY with all four stations valid and no fault."""
    cfg = fast_cfg()
    assert cfg.ids == list("ABCD") and cfg.inactive_ids == [] and "stations_active" not in raw_of(SIM)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="four_review_"))
    r = SimRobot(cfg, seed=0, data_dir=tmp, camera_kw={"board": FloorBoard.nominal(0.15)})
    sup = Supervisor(r.ctx, state_path=tmp / "state.json", ledger_path=tmp / "ledger.json")
    rep = sup.start()
    assert rep.outcome == "READY" and sup.state == "READY", (rep.outcome, rep.reasons)
    assert all(r.co.links[s].tel["flt"] == 0 and r.ctx.ledger.stations[s].valid for s in "ABCD")
    assert rep.measurements["active_stations"] == list("ABCD") and "inactive_stations" not in rep.measurements
    assert r.world.eq_failures == 0
