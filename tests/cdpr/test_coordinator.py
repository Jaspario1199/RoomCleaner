import numpy as np
import pytest

from roomcleaner.cdpr.protocol import Fault, State
from roomcleaner.cdpr.trajectory import plan_cable_move

from .simkit import build, bring_up


def cable_plan(co, delta=(3000, -2000, 1500, -1000)):
    return plan_cable_move(co.positions(), delta, max_rate=2500, max_acc=6000, segment_s=0.1)


def stop_taus(plan, final):
    """Path time at which each station's final position lies on the plan."""
    taus = np.linspace(0, plan.duration, 4001)
    track = np.array([plan.position_at(t) for t in taus])
    out = []
    for j, s in enumerate("ABCD"):
        out.append(taus[int(np.argmin(np.abs(track[:, j] - final[s])))])
    return np.array(out)


def test_bring_up_and_synchronized_motion():
    cfg, net, st, rt, co = build(1)
    bring_up(co)
    assert all(not r for r in co.readiness().values())
    plan = cable_plan(co)
    res = co.execute(plan)
    assert res.ok, res.reason
    assert np.allclose(co.positions(), np.round(plan.end))
    for s in "ABCD":
        assert abs(st[s].motor_rel - plan.end["ABCD".index(s)]) < 0.5


def test_refuses_to_start_when_a_station_is_not_ready():
    cfg, net, st, rt, co = build(2)
    bring_up(co)
    st["C"].enc_broken = True
    co.wait(200000)
    res = co.execute(cable_plan(co))
    assert not res.ok and "C" in res.reason
    assert np.allclose([st[s].motor_rel for s in "ABD"], 0)


def test_operator_pause_stops_all_on_the_same_path_point():
    cfg, net, st, rt, co = build(3)
    bring_up(co)
    plan = cable_plan(co, (6000, -4000, 3000, -2000))
    rt.hooks.append(lambda t, t_pause=rt.t + 1.3e6: co.request_pause("test") if abs(t - t_pause) < 500 else None)
    res = co.execute(plan)
    assert not res.ok and "paused" in res.reason
    taus = stop_taus(plan, res.final_pos)
    assert np.ptp(taus) < 0.01, taus               # all stopped within 10 ms of path time
    assert 0 < taus.mean() < plan.duration


def test_stalled_motor_trips_tracking_and_others_hold():
    cfg, net, st, rt, co = build(4)
    bring_up(co)
    plan = cable_plan(co, (6000, -4000, 3000, -2000))
    rt.hooks.append(lambda t, t0=rt.t + 1.0e6: setattr(st["B"], "stalled", True) if t > t0 else None)
    res = co.execute(plan)
    assert not res.ok
    assert co.links["B"].tel["flt"] == Fault.TRACKING
    others = {s: res.final_pos[s] for s in "ACD"}
    taus = stop_taus(plan, dict(res.final_pos))
    assert np.ptp(taus[[0, 2, 3]]) < 0.02
    assert taus[0] < plan.duration * 0.9            # stopped early, did not finish
    assert all(co.links[s].tel["en"] for s in "ABCD")  # holding torque kept everywhere


def test_station_link_outage_self_holds_and_host_stops_others():
    cfg, net, st, rt, co = build(5)
    bring_up(co)
    plan = cable_plan(co, (6000, -4000, 3000, -2000))
    rt.hooks.append(lambda t, t0=rt.t + 1.0e6: net.down.add("D") if t > t0 else None)
    res = co.execute(plan)
    assert not res.ok and ("D" in res.reason or res.held_by == "D")
    co.wait(800000)
    assert st["D"].core.fault == Fault.LEASE          # D stopped itself
    finals = dict(res.final_pos)
    finals["D"] = st["D"].core.pos
    taus = stop_taus(plan, finals)
    assert np.ptp(taus) < 0.03, taus                # host aligned the others with D's lease stop


def test_reboot_mid_motion_is_detected_and_motion_stopped():
    cfg, net, st, rt, co = build(6)
    bring_up(co)
    plan = cable_plan(co, (6000, -4000, 3000, -2000))
    fired = []
    def hook(t, t0=rt.t + 1.0e6):
        if t > t0 and not fired:
            fired.append(1)
            st["A"].reboot()
    rt.hooks.append(hook)
    res = co.execute(plan)
    assert not res.ok
    assert co.links["A"].boot_changed
    assert "rebooted" in " ".join(co.readiness()["A"])


def test_lossy_network_still_completes_or_stops_safely():
    cfg, net, st, rt, co = build(7, loss=0.02)
    bring_up(co)
    plan = cable_plan(co)
    res = co.execute(plan)
    if res.ok:
        assert np.allclose(co.positions(), np.round(plan.end))
    else:
        taus = stop_taus(plan, res.final_pos)
        assert np.ptp(taus) < 0.06
