"""A TRACKING fault is reported in words: an overload when the spool turned toward payout beyond the command, a possible
jam the other way, with the amount (degrees of spool, mm of line). Message text only: these tests check the wording
and the numbers, and that the trust-ledger transition and the supervisor reaction are the ones they always were.

The encoder is on the SPOOL; ``terr`` = measured - expected spool angle in encoder counts, + = payout
(``station_core._check_tracking``). Design intent: the motor's holding torque is the weakest link
(calculations/lift_chain_weakest_link.py), so a line pulled harder than the motor holds turns the spool toward payout
beyond the command (terr > 0) and the station stops."""
import math
import re

import pytest

from roomcleaner.cdpr.protocol import Fault
from roomcleaner.cdpr.spool import CableMap
from roomcleaner.cdpr.startup import RobotContext
from roomcleaner.cdpr.supervisor import Supervisor
from roomcleaner.cdpr.trajectory import RobotModel, plan_cable_move
from roomcleaner.cdpr.trust import TrustLedger, tracking_fault_detail

from .cdpr.simkit import bring_up, build

CPR = 4096          # encoder counts per spool revolution (config/robot.sim.json)
R_CORE = 0.0075     # core radius (m)

OVERLOAD_TAIL = ("toward payout beyond the command; the line pulled harder than the motor holds "
                 "(motor skipped or spool slipped on the shaft)")
JAM_TAIL = "less than commanded toward payout (jam, or spool slipping on the shaft)"
# 82 counts at 4096 counts/rev and r = 7.5 mm: 7.2 deg of spool, 0.94 mm of line
OVERLOAD_82 = f"overload: spool turned 7 deg (0.9 mm of line) {OVERLOAD_TAIL}"
JAM_82 = f"spool turned 7 deg (0.9 mm of line) {JAM_TAIL}"
AMOUNT = re.compile(r"spool turned (\d+) deg \((\d+\.\d) mm of line\)")


# how a motion that a station's TRACKING fault stopped says so: the station's own hold reaches the host first ("hold
# originated by station X"), its fault event or telemetry (the latched fault) can win the race
STOP_A, STOP_B, STOP_C = (rf"(?:station {s}:? fault |hold originated by station {s} \(fault )" for s in "ABC")


def amount_of(text):
    m = AMOUNT.search(text)
    assert m, text
    return int(m.group(1)), float(m.group(2))


def assert_amount_is_consistent(text, radius_m=R_CORE):
    """The mm shown is the line length of the degrees shown (each rounded for display)."""
    deg, mm = amount_of(text)
    assert deg >= 5                                                   # tracking_tol_counts = 60 counts = 5.3 deg
    assert mm == pytest.approx(2e3 * math.pi * radius_m * deg / 360.0, abs=0.15)


# ------------------------------------------------------------------ the wording
def test_terr_toward_payout_is_an_overload_with_the_amount():
    text = tracking_fault_detail({"terr": 82.0}, CPR, R_CORE)
    assert text == OVERLOAD_82
    assert tracking_fault_detail({"terr": 82}, CPR, R_CORE) == OVERLOAD_82          # an int counts the same


def test_terr_away_from_payout_is_a_possible_jam_with_the_amount():
    assert tracking_fault_detail({"terr": -82.0}, CPR, R_CORE) == JAM_82


def test_degrees_and_mm_come_from_counts_per_rev_and_the_radius():
    # half a turn of a 7.5 mm core: 180 deg and pi * 7.5 mm = 23.6 mm of line
    half = tracking_fault_detail({"terr": CPR / 2}, CPR, R_CORE)
    assert half == f"overload: spool turned 180 deg (23.6 mm of line) {OVERLOAD_TAIL}"
    assert tracking_fault_detail({"terr": -CPR / 2}, CPR, R_CORE) == f"spool turned 180 deg (23.6 mm of line) {JAM_TAIL}"
    # another encoder: 82 of 1024 counts = 28.8 deg, 3.8 mm
    other = tracking_fault_detail({"terr": 82.0}, 1024, R_CORE)
    assert other == f"overload: spool turned 29 deg (3.8 mm of line) {OVERLOAD_TAIL}"
    # a fuller spool: the same 82 counts are more line (82/4096 * 2 pi * 10.5 mm = 1.32 mm), the same angle
    fuller = tracking_fault_detail({"terr": 82.0}, CPR, 0.0105)
    assert fuller == f"overload: spool turned 7 deg (1.3 mm of line) {OVERLOAD_TAIL}"


@pytest.mark.parametrize("tel", [None, {}, {"terr": None}, {"terr": float("nan")}, {"terr": float("inf")},
                                 {"terr": 0}, {"terr": 0.0}, {"terr": "82"}, {"terr": True}])
def test_unknown_terr_gives_no_reading(tel):
    assert tracking_fault_detail(tel, CPR, R_CORE) is None


# ------------------------------------------------------------------ trust ledger
def verified_ledger():
    t = TrustLedger()
    for k, s in enumerate("ABCD"):
        t.set_reference(s, 100 + k, 2.0 + k * 0.1, 0.001, "bead", bead=True)
    t.marker_valid = True
    t.set_level("VERIFIED")
    return t


def test_ledger_note_carries_the_reading_and_the_transition_is_unchanged():
    t = verified_ledger()
    t.on_fault("C", Fault.TRACKING, OVERLOAD_82)
    assert t.stations["C"].note == f"TRACKING fault: {OVERLOAD_82}"
    assert f"C: reference invalid (TRACKING fault: {OVERLOAD_82})" in t.history
    # exactly what test_trust.py asserts for the plain call
    assert not t.stations["C"].valid and t.stations["A"].valid
    assert t.level == "LOCAL_ONLY" and t.unverified() == ["C"] and t.recovery_required


def test_ledger_note_keeps_the_old_wording_without_a_reading():
    t = verified_ledger()
    t.on_fault("C", Fault.TRACKING)
    assert t.stations["C"].note == "TRACKING fault: steps may be lost"
    t = verified_ledger()
    t.on_fault("C", Fault.TRACKING, None)
    assert t.stations["C"].note == "TRACKING fault: steps may be lost"
    # a reading belongs to TRACKING only
    t = verified_ledger()
    t.on_fault("C", Fault.ENCODER, OVERLOAD_82)
    assert t.stations["C"].note == "ENCODER fault: steps may be lost"


# ------------------------------------------------------------------ coordinator
def cable_plan(co, delta):
    return plan_cable_move(co.positions(), delta, max_rate=2500, max_acc=6000, segment_s=0.1)


def test_coordinator_fault_name_follows_the_latest_telemetry():
    cfg, net, st, rt, co = build(1)
    bring_up(co)
    tel = dict(co.links["B"].tel)
    co.links["B"].tel = dict(tel, terr=82.0)
    assert co._fault_name("B", Fault.TRACKING) == f"TRACKING: {OVERLOAD_82}"        # core radius (no model here)
    co.links["B"].tel = dict(tel, terr=-82.0)
    assert co._fault_name("B", Fault.TRACKING) == f"TRACKING: {JAM_82}"
    # unknown terr (no telemetry, or none in it): the plain name
    tel.pop("terr", None)
    co.links["B"].tel = tel
    assert co._fault_name("B", Fault.TRACKING) == "TRACKING"
    co.links["B"].tel = None
    assert co._fault_name("B", Fault.TRACKING) == "TRACKING"
    # other faults are untouched
    co.links["B"].tel = dict(tel, terr=82.0)
    assert co._fault_name("B", Fault.LEASE) == "LEASE"
    assert co._fault_name("B", Fault.ENCODER) == "ENCODER"
    assert co._fault_name("B", 99) is None


def test_coordinator_running_check_reports_a_latched_tracking_fault_with_the_reading():
    cfg, net, st, rt, co = build(1)
    bring_up(co)
    tel = dict(co.links["B"].tel, flt=Fault.TRACKING)
    co.links["B"].tel = dict(tel, terr=82.0)
    reason, lost = co._check_running(rt.now_us())
    assert reason == f"station B: fault TRACKING: {OVERLOAD_82}" and lost is None
    co.links["B"].tel = dict(tel, terr=-82.0)
    assert co._check_running(rt.now_us())[0] == f"station B: fault TRACKING: {JAM_82}"
    tel.pop("terr", None)
    co.links["B"].tel = tel
    assert co._check_running(rt.now_us())[0] == "station B: fault TRACKING"          # the current wording
    co.links["B"].tel = dict(tel, flt=Fault.ENCODER, terr=82.0)
    assert co._check_running(rt.now_us())[0] == "station B: fault ENCODER"


def run_with_stall(station, delta):
    cfg, net, st, rt, co = build(4)
    bring_up(co)
    plan = cable_plan(co, delta)
    rt.hooks.append(lambda t, t0=rt.t + 1.0e6: setattr(st[station], "stalled", True) if t > t0 else None)
    return co, co.execute(plan)


def test_a_stalled_lift_is_reported_as_an_overload():
    # B takes line in (-4000) but the motor stops following: the spool is pulled toward payout beyond the command
    co, res = run_with_stall("B", (6000, -4000, 3000, -2000))
    assert not res.ok and co.links["B"].tel["flt"] == Fault.TRACKING
    assert re.search(STOP_B + r"TRACKING: overload: spool turned ", res.reason), res.reason
    assert OVERLOAD_TAIL in res.reason and "jam" not in res.reason
    assert_amount_is_consistent(res.reason)
    assert any("B fault event TRACKING: overload: spool turned " in line for line in co.log), co.log[-5:]


def test_a_stalled_payout_is_reported_as_a_possible_jam():
    # A pays out (+6000) but the motor stops following: the spool turned less than commanded toward payout
    co, res = run_with_stall("A", (6000, -4000, 3000, -2000))
    assert not res.ok and co.links["A"].tel["flt"] == Fault.TRACKING
    assert re.search(STOP_A + r"TRACKING: spool turned ", res.reason), res.reason
    assert JAM_TAIL in res.reason and "overload" not in res.reason
    assert_amount_is_consistent(res.reason)


def test_a_spool_slipping_toward_payout_during_a_move_is_reported_as_an_overload_of_that_amount():
    cfg, net, st, rt, co = build(5)
    bring_up(co)
    plan = cable_plan(co, (6000, -4000, 3000, -2000))
    slip_usteps = 100 * cfg.station("C").drive.usteps_per_rev / CPR              # 100 counts = 8.8 deg of the spool
    done = []

    def slip(t, t0=rt.t + 1.0e6):
        if t > t0 and not done:
            done.append(t)
            st["C"].motor += slip_usteps                                          # the spool turns toward payout, uncommanded
    rt.hooks.append(slip)
    res = co.execute(plan)
    assert not res.ok and co.links["C"].tel["flt"] == Fault.TRACKING and done
    assert re.search(STOP_C + r"TRACKING: overload: spool turned 9 deg ", res.reason), res.reason
    assert_amount_is_consistent(res.reason)


# ------------------------------------------------------------------ supervisor
@pytest.fixture
def sup_rig():
    cfg, net, st, rt, co = build(3)
    bring_up(co)
    ledger = TrustLedger.for_ids(cfg.ids)
    for k, s in enumerate(cfg.ids):
        ledger.set_reference(s, co.links[s].boot, 2.0 + 0.1 * k, 0.001, "bead", bead=True)
    ledger.marker_valid = True
    ledger.set_level("VERIFIED")
    ctx = RobotContext(cfg, co, None, None, None, ledger, log=lambda *a: None)
    sup = Supervisor(ctx)
    sup._set("READY", "test")
    co.pump = lambda: None                      # the tests below put a station's telemetry in by hand
    return cfg, st, rt, co, ctx, sup


def latch(co, sid, **tel):
    co.links[sid].tel = dict(co.links[sid].tel, flt=Fault.TRACKING, **tel)


def assert_unchanged_reaction(sup, ctx, sid):
    """What a TRACKING fault has always done: that station's reference is lost, the others are kept, recovery."""
    assert not ctx.ledger.stations[sid].valid and ctx.ledger.recovery_required
    assert all(ctx.ledger.stations[s].valid for s in ctx.ids if s != sid)
    assert ctx.ledger.level == "LOCAL_ONLY"
    assert sup.state == "RECOVERY_REQUIRED"                                       # claw_supported is False (fail closed)


def test_supervisor_reports_terr_toward_payout_as_an_overload(sup_rig):
    cfg, st, rt, co, ctx, sup = sup_rig
    latch(co, "B", terr=82.0)
    sup.poll()
    assert ctx.ledger.stations["B"].note == f"TRACKING fault: {OVERLOAD_82}"        # no model yet: the core radius
    assert sup.reasons[-1] == f"station reference lost: B: TRACKING fault: {OVERLOAD_82}"
    assert sup.status()["stations"]["B"]["note"] == f"TRACKING fault: {OVERLOAD_82}"
    assert sup.status()["stations"]["B"]["fault"] == "TRACKING"                     # the structured field is as it was
    assert_unchanged_reaction(sup, ctx, "B")


def test_supervisor_reports_terr_away_from_payout_as_a_possible_jam(sup_rig):
    cfg, st, rt, co, ctx, sup = sup_rig
    latch(co, "D", terr=-82.0)
    sup.poll()
    assert sup.reasons[-1] == f"station reference lost: D: TRACKING fault: {JAM_82}"
    assert_unchanged_reaction(sup, ctx, "D")


def test_supervisor_keeps_the_current_wording_without_terr(sup_rig):
    cfg, st, rt, co, ctx, sup = sup_rig
    tel = {k: v for k, v in co.links["A"].tel.items() if k != "terr"}
    co.links["A"].tel = dict(tel, flt=Fault.TRACKING)
    sup.poll()
    assert ctx.ledger.stations["A"].note == "TRACKING fault: steps may be lost"
    assert sup.reasons[-1] == "station reference lost: A: TRACKING fault: steps may be lost"
    assert_unchanged_reaction(sup, ctx, "A")


def test_supervisor_uses_the_radius_the_line_leaves_the_spool_at(sup_rig):
    cfg, st, rt, co, ctx, sup = sup_rig
    # 5.6 m of line on the spool (L0 = 0.5 m of 6.096 m): the fourth layer, radius 9.25 mm instead of the 7.5 mm core
    maps = {s: CableMap(cfg.station(s).spool, cfg.station(s).drive.usteps_per_rev).with_reference(0.5)
            for s in cfg.ids}
    ctx.model = RobotModel(None, maps, tuple(cfg.ids))
    latch(co, "C", terr=82.0)
    sup.poll()
    r_eff = maps["C"].radius(maps["C"].length(co.links["C"].pos))
    assert r_eff == pytest.approx(0.00925) and r_eff > 1.2 * R_CORE
    mm = 82 / CPR * 2e3 * math.pi * r_eff
    assert mm != pytest.approx(0.94, abs=0.1)                                     # not the core radius
    expected = f"overload: spool turned 7 deg ({mm:.1f} mm of line) {OVERLOAD_TAIL}"
    assert ctx.ledger.stations["C"].note == f"TRACKING fault: {expected}"
    assert_unchanged_reaction(sup, ctx, "C")


def test_supervisor_falls_back_to_the_core_radius_when_the_position_is_off_the_spool(sup_rig):
    cfg, st, rt, co, ctx, sup = sup_rig
    maps = {s: CableMap(cfg.station(s).spool, cfg.station(s).drive.usteps_per_rev).with_reference(0.5)
            for s in cfg.ids}
    ctx.model = RobotModel(None, maps, tuple(cfg.ids))
    latch(co, "C", terr=82.0, pos=10 ** 9)                                         # far beyond the line on the spool
    sup.poll()
    assert ctx.ledger.stations["C"].note == f"TRACKING fault: {OVERLOAD_82}"
    assert_unchanged_reaction(sup, ctx, "C")


def test_supervisor_reports_a_real_station_fault_from_a_slipping_spool(sup_rig):
    cfg, st, rt, co, ctx, sup = sup_rig
    del co.pump                                  # real telemetry this time (drops the instance override)
    st["B"].motor += 64 * 1.0                    # 64 usteps = 81.9 counts: the spool turns toward payout, uncommanded
    co.wait(600000)                              # tolerance exceeded for the dwell: the station latches TRACKING by itself
    assert co.links["B"].tel["flt"] == Fault.TRACKING
    sup.poll()
    note = ctx.ledger.stations["B"].note
    assert note.startswith("TRACKING fault: overload: spool turned 7 deg (0.9 mm of line) "), note
    assert note.endswith(OVERLOAD_TAIL)
    assert_unchanged_reaction(sup, ctx, "B")
