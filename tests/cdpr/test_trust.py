from roomcleaner.cdpr.protocol import Fault
from roomcleaner.cdpr.trust import TrustLedger


def verified_ledger():
    t = TrustLedger()
    for k, s in enumerate("ABCD"):
        t.set_reference(s, 100 + k, 2.0 + k * 0.1, 0.001, "bead", bead=True)
    t.marker_valid = True
    t.set_level("VERIFIED")
    return t


def test_coordinated_stops_keep_references():
    t = verified_ledger()
    t.on_fault("B", Fault.LEASE)
    assert t.all_valid() and t.level == "VERIFIED" and not t.recovery_required   # spec 5: unchanged


def test_tracking_fault_and_reboot_invalidate_only_that_station():
    t = verified_ledger()
    t.on_fault("C", Fault.TRACKING)
    assert not t.stations["C"].valid and t.stations["A"].valid
    assert t.level == "LOCAL_ONLY" and t.unverified() == ["C"]
    t2 = verified_ledger()
    t2.on_boot_change("A", 999)
    assert not t2.stations["A"].valid and t2.stations["A"].boot == 999


def test_host_restart_restores_matching_epochs(tmp_path):
    t = verified_ledger()
    p = tmp_path / "trust.json"
    t.save(p)
    t2 = TrustLedger.load(p)
    t2.restore_after_host_restart({"A": 100, "B": 101, "C": 555, "D": 103}, {"D": Fault.ENCODER})
    assert t2.stations["A"].valid and t2.stations["B"].valid
    assert not t2.stations["C"].valid and not t2.stations["D"].valid


def test_visual_reference_does_not_count_as_bead_verified():
    t = verified_ledger()
    t.invalidate("D", "test")
    t.set_reference("D", 104, 2.3, 0.004, "visual")
    assert t.stations["D"].valid and not t.stations["D"].bead_verified


def test_unknown_support_fails_closed_and_save_is_atomic(tmp_path):
    t = TrustLedger()
    assert t.claw_supported is False                   # unknown = may be hanging
    t.save(tmp_path / "l.json")
    assert not (tmp_path / "l.json.tmp").exists()
    assert TrustLedger.load(tmp_path / "l.json").claw_supported is False


def test_level_drops_to_none_when_every_reference_is_lost():
    t = verified_ledger()
    t.set_level("LOCAL_ONLY")
    for s in "ABCD":
        t.invalidate(s, "test")
    assert t.level == "NONE"
