"""Decision D26: the ceiling and wall margins, not bead precision, grant full-workspace trust.

Unit part: the boundary-relative sigma (``Calibrator.boundary_sigma``) against analytic cases and a Monte-Carlo
of the nonlinear physics; the trust ledger's basis; configuration. Simulation part: ONE full startup with the
floor board and the per-pose slack probe (several minutes of wall time, shared by the tests below), then the
decision is re-evaluated on that finished robot with the probe flag, the margins and the witness chi-squared
changed one at a time, with the bead search on, and through the operator API. An end-to-end startup without the
probe checks the LOCAL_ONLY outcome."""
import json

import numpy as np
import pytest
from scipy.optimize import least_squares

from roomcleaner.cdpr.calibration import (IDS, CalibrationResult, Calibrator, Identifiability, Layout)
from roomcleaner.cdpr.config import ConfigError, load_config
from roomcleaner.cdpr.frames import inv_T, planar_T, rot_z
from roomcleaner.cdpr.homing import BeadOutcome, BeadVerifier
from roomcleaner.cdpr.protocol import Fault
from roomcleaner.cdpr.service import Service, create_app
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.sim.world import FloorBoard
from roomcleaner.cdpr.spool import CableMap
from roomcleaner.cdpr.startup import StartupAbort, StartupSequencer
from roomcleaner.cdpr.supervisor import Supervisor
from roomcleaner.cdpr.tasks import ItemPerception, TaskRunner, TrustedVolume
from roomcleaner.cdpr.trust import TrustLedger

from .simkit import assert_no_eq_failures, fast_cfg
from .test_service import Client

SIM = "config/robot.sim.json"
EXAMPLE = "config/robot.example.json"


# ============================================================ boundary-relative sigma (no simulation)
def make_cal(cfg=None):
    cfg = cfg or load_config(SIM)
    return cfg, Calibrator(cfg, {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations})


def fake_result(cfg, cov, psi=(1.4, 1.1, 0.0)):
    T = planar_T(*psi)
    A = (inv_T(T) @ np.c_[cfg.anchor_priors(), np.ones(4)].T).T[:, :3]
    return CalibrationResult(anchors_M=A, L0=np.full(4, 3.0), scale=np.ones(4), psi=np.array(psi, float),
                             cov_theta=cov, chi2=0.0, norm_rms=1.0, n_rows=0, residuals_m=np.zeros((0, 4)),
                             outliers=[], identifiability=Identifiability(np.ones(1), [], True))


def zero_cov():
    return np.zeros((19, 19))             # 12 anchors + 4 L0 + (x, y, yaw)


Q_M = np.array([0.4, -0.3, 1.2])          # a commanded claw pose, marker frame


def test_boundary_sigma_analytic_components():
    cfg, cal = make_cal()
    lay = Layout(0, False)
    sig = 0.02
    # only the marker x registration uncertain: the x wall sees it 1:1, y wall and ceiling do not
    C = zero_cov()
    C[lay.psi.start, lay.psi.start] = sig ** 2
    b = cal.boundary_sigma(fake_result(cfg, C), Q_M)
    assert b["wall_x"] == pytest.approx(sig) and b["wall_y"] < 1e-9 and b["ceiling"] < 1e-9
    # only the marker yaw uncertain: error = yaw sigma x lever arm, perpendicular to the marker->claw vector
    C = zero_cov()
    C[lay.psi.start + 2, lay.psi.start + 2] = 0.01 ** 2
    b = cal.boundary_sigma(fake_result(cfg, C, psi=(1.4, 1.1, 0.0)), Q_M)
    assert b["wall_x"] == pytest.approx(0.01 * abs(Q_M[1])) and b["wall_y"] == pytest.approx(0.01 * abs(Q_M[0]))
    assert b["ceiling"] < 1e-9                   # the ceiling is relative to the anchors: no registration involved
    # only one absolute cable length uncertain: that IS the claw-to-anchor distance error of a taut cable; the
    # bound is never below it (hanging on three cables can only add to it)
    C = zero_cov()
    C[lay.L0(2), lay.L0(2)] = 0.03 ** 2
    b = cal.boundary_sigma(fake_result(cfg, C), Q_M)
    assert 0.03 - 1e-12 <= b["ceiling_dist"] < 0.03 * 5 and b["ceiling"] >= 0.03 - 1e-12
    # the payout-scale term enters as an independent per-cable length error
    b0 = cal.boundary_sigma(fake_result(cfg, zero_cov()), Q_M)
    assert b0["wall"] < 1e-9 and b0["ceiling"] < 1e-9
    b1 = cal.boundary_sigma(fake_result(cfg, zero_cov()), Q_M, extra_len_sigma=np.full(4, 0.004))
    assert 0.004 - 1e-12 <= b1["ceiling_dist"] < 0.004 * 5 and b1["wall"] > 0


def test_boundary_sigma_matches_a_monte_carlo_of_the_nonlinear_physics():
    """Sample the model error eps = true - estimated from a full covariance, put the claw where the four true
    cable lengths (model lengths + the L0 error) really put it, and compare the empirical spread of the
    clearance errors with the linearised prediction."""
    cfg, cal = make_cal()
    rng = np.random.default_rng(3)
    psi = (1.4, 1.1, 0.35)
    B = rng.normal(size=(19, 19)) * 0.004
    C = B @ B.T + np.diag(np.r_[np.full(12, 0.008), np.full(4, 0.015), 0.01, 0.01, 0.004]) ** 2
    res = fake_result(cfg, C, psi=psi)
    pred = cal.boundary_sigma(res, Q_M)
    att = cal.attach
    A_e = res.anchors_M
    L_m = np.linalg.norm(A_e - (Q_M + att), axis=1)
    Lc = np.linalg.cholesky(C)
    N = 1200
    wall, zc, dist = [], [], []
    for _ in range(N):
        eps = Lc @ rng.normal(size=19)
        A_t = A_e + eps[:12].reshape(4, 3)
        L_t = L_m + eps[12:16]                                    # true length at the same motor positions
        # a consistent set of true lengths cannot be made from 4 independent errors: hang on the 3 tautest
        # cables (the fourth one slack), as the real claw does
        best = None
        for om in range(4):
            keep = [i for i in range(4) if i != om]
            x = least_squares(lambda q: np.linalg.norm(A_t[keep] - (q + att[keep]), axis=1) - L_t[keep], Q_M,
                              method="lm").x
            if np.linalg.norm(A_t[om] - (x + att[om])) <= L_t[om] + 1e-9:
                if best is None or np.linalg.norm(x - Q_M) < np.linalg.norm(best - Q_M):
                    best = x
        if best is None:
            continue
        psi_t = np.array(psi) + eps[16:19]
        q_room_true = rot_z(psi_t[2]) @ best + [psi_t[0], psi_t[1], 0.0]
        q_room_cmd = rot_z(psi[2]) @ Q_M + [psi[0], psi[1], 0.0]
        wall.append((q_room_true - q_room_cmd)[:2])
        r = (A_t - (best + att)) - (A_e - (Q_M + att))            # claw-to-anchor vector error, per anchor
        zc.append(r[:, 2])
        dist.append(np.linalg.norm(A_t - (best + att), axis=1) - L_m)
    wall, zc, dist = np.array(wall), np.array(zc), np.array(dist)
    assert len(wall) > 0.5 * N
    # the prediction is the worst of the four-cable and the four three-cable solutions, so it must bound the
    # empirical spread of the physical (hang-on-three) error, and must not be absurdly larger
    assert pred["wall_x"] > 0.9 * wall[:, 0].std() and pred["wall_y"] > 0.9 * wall[:, 1].std()
    assert pred["wall"] < 3.0 * max(wall[:, 0].std(), wall[:, 1].std())
    assert 0.9 * zc.std(axis=0).max() < pred["ceiling_z"] < 4.0 * zc.std(axis=0).max()
    assert pred["ceiling_dist"] > 0.9 * dist.std(axis=0).max()


# ============================================================ trust ledger: basis and reasons
def ledger_with(level_kwargs):
    t = TrustLedger()
    for k, s in enumerate("ABCD"):
        t.set_reference(s, 100 + k, 2.0 + k * 0.1, 0.02, "visual")
    t.marker_valid = True
    t.set_level("VERIFIED", **level_kwargs)
    return t


def test_ledger_records_the_basis_and_numbers_and_survives_a_save(tmp_path):
    mc = {"k": 3.0, "sigma_ceiling_m": 0.03, "ceiling_margin_m": 0.4, "worst_pose_ceiling_room_m": [1.0, 2.0, 2.1]}
    t = ledger_with({"basis": "margin", "margin_check": mc})
    assert t.level == "VERIFIED" and t.verified_basis == "margin" and t.margin_check == mc and t.trust_reasons == []
    t.save(tmp_path / "l.json")
    t2 = TrustLedger.load(tmp_path / "l.json")
    assert t2.verified_basis == "margin" and t2.margin_check == mc
    # a ledger written before D26 (no basis fields) still loads
    d = json.loads((tmp_path / "l.json").read_text())
    for k in ("verified_basis", "margin_check", "trust_reasons"):
        d.pop(k)
    (tmp_path / "old.json").write_text(json.dumps(d))
    old = TrustLedger.load(tmp_path / "old.json")
    assert old.verified_basis is None and old.trust_reasons == []


def test_basis_is_dropped_with_the_level_and_the_reason_is_plain():
    t = ledger_with({"basis": "margin"})
    t.on_fault("B", Fault.SWITCH)                  # a bead switch opening in normal motion (station core: Fault.SWITCH)
    assert t.level == "LOCAL_ONLY" and t.verified_basis is None and t.recovery_required
    assert any("station B" in r and "bead switch" in r for r in t.trust_reasons), t.trust_reasons
    t = ledger_with({"basis": "beads"})
    t.on_marker_lost()
    assert t.level == "LOCAL_ONLY" and t.verified_basis is None and "marker" in t.trust_reasons[0]
    t = ledger_with({"basis": "margin"})
    t.on_power_loss()
    assert t.level == "NONE" and t.verified_basis is None


def test_bead_search_is_off_by_default_and_validated():
    for path in (SIM, EXAMPLE):
        assert load_config(path).startup.bead_search is False
    raw = json.load(open(SIM))
    raw["startup"]["bead_search"] = 1
    with pytest.raises(ConfigError):
        load_config(raw)
    raw = json.load(open(SIM))
    raw["motion"]["ceiling_margin_m"] = -0.1
    with pytest.raises(ConfigError):
        load_config(raw)


# ============================================================ simulation: floor board + slack probe
D27_VISION_ONLY = pytest.mark.xfail(
    strict=True,
    reason="D27 (no IMU): with vision-only attitude (10 mrad) the per-pose slack probe cannot resolve the cable onsets, "
           "the board+probe fixture's calibration is rejected (witness RMS 9.3 mm > 6 mm) and VERIFIED-by-margin is not "
           "reached. Genuine consequence of the noisier attitude, not relaxed: verification/imu_removal_results.md. "
           "strict: this flips (fails) when the probe/attitude problem is solved, so the mark must then be removed.")


@pytest.fixture(scope="module")
def board_probe(tmp_path_factory):
    td = tmp_path_factory.mktemp("margin")
    # With the four-point claw (CAD camera 7 cm higher over the floor, jaw tips 17 cm lower, spaced attachments) the
    # predicted length sigma over the work volume of this run is 6.0 mm instead of < 5 mm
    # (verification/multi_attachment_results.md). The margin rule under test is about k*sigma against the margins, not about
    # that calibration criterion, so the criterion is relaxed to 7.5 mm for this fixture only (default 5 mm unchanged).
    cfg = fast_cfg(**{"startup.slack_probe": True, "calibration.length_sigma_max_m": 0.0075})
    # seed 1: the calibration criteria accept this run; seeds 0 and 2 miss the 5 mm predicted-length-sigma
    # criterion (5.4 / 5.6 mm at the time of writing) and stay LOCAL_ONLY by design
    board = FloorBoard(3, 3, 0.42, 0.16, layout_err_m=0.0, span_mode="extent", seed=1)
    r = SimRobot(cfg, seed=1, data_dir=td, camera_kw={"board": board})
    svc = Service(r.ctx, data_dir=td)
    c = Client(create_app(svc), svc.token)
    StartupSequencer.study_board = board
    try:
        rep = svc.sup.start()
    finally:
        StartupSequencer.study_board = None
    assert_no_eq_failures(r, "margin fixture: board + probe startup")
    return r, svc, c, rep


def evaluate(r, rep, **over):
    """Re-run only the margin decision on the finished startup, with config / report values changed."""
    cfg = r.cfg
    saved = {}
    try:
        for path, v in over.items():
            if path == "chi2":
                continue
            obj, key = cfg, path
            *parts, key = path.split(".")
            for p_ in parts:
                obj = getattr(obj, p_)
            saved[path] = (obj, key, getattr(obj, key))
            setattr(obj, key, v)
        seq = StartupSequencer(r.ctx)
        seq.cal_report = dict(rep.measurements["calibration"])
        if "chi2" in over:
            seq.cal_report["witness_chi2_dof"] = over["chi2"]
        return seq.assess_margin_trust()
    finally:
        for obj, key, v in saved.values():
            setattr(obj, key, v)


@D27_VISION_ONLY
def test_verified_by_margin_with_board_and_probe(board_probe):
    r, svc, c, rep = board_probe
    assert svc.sup.state == "READY", rep.reasons
    lg = r.ctx.ledger
    m = rep.measurements["margin_trust"]
    assert lg.level == "VERIFIED" and lg.verified_basis == "margin", (lg.level, m["reasons"])
    # (a) calibration accepted, (b) probe on for every suspended sample with a consistent witness chi-squared
    assert m["calibration_accepted"] and m["slack_probe"] and m["probed_samples"].split("/")[0] == \
        m["probed_samples"].split("/")[1]
    assert m["witness_chi2_dof"] <= m["witness_chi2_max"]
    # (c) k*sigma within each margin, with the numbers and the worst pose recorded in the ledger
    assert m["k"] == r.cfg.calibration.bead_k_sigma
    assert m["k_sigma_ceiling_m"] <= r.cfg.motion.ceiling_margin_m and m["k_sigma_wall_m"] <= r.cfg.motion.workspace_margin_m
    assert len(m["worst_pose_ceiling_room_m"]) == 3 and len(m["worst_pose_wall_room_m"]) == 3
    assert lg.margin_check == m and lg.trust_reasons == []
    # the beads were not searched (default off) and are not what granted the level
    assert rep.measurements["beads"] == {} and not any(st.bead_verified for st in lg.stations.values())
    assert not r.cfg.startup.bead_search


@D27_VISION_ONLY
def test_margin_decision_is_reevaluated_and_fails_closed(board_probe):
    r, svc, c, rep = board_probe
    ok = evaluate(r, rep)
    assert ok["ok"] and not ok["reasons"]
    # probe off -> the sigma is not honest
    off = evaluate(r, rep, **{"startup.slack_probe": False})
    assert not off["ok"] and any("slack probe was off" in x for x in off["reasons"])
    # k*sigma beyond a margin: shrink each margin in turn
    ce = evaluate(r, rep, **{"motion.ceiling_margin_m": 0.5 * ok["k_sigma_ceiling_m"]})
    assert not ce["ok"] and any("ceiling margin" in x for x in ce["reasons"])
    assert not any("wall" in x for x in ce["reasons"])
    wa = evaluate(r, rep, **{"motion.workspace_margin_m": 0.5 * ok["k_sigma_wall_m"]})
    assert not wa["ok"] and any("wall) margin" in x for x in wa["reasons"])
    assert not any("ceiling margin" in x for x in wa["reasons"])
    # exactly at the limit still passes (k*sigma <= margin), a hair under fails
    edge = evaluate(r, rep, **{"motion.ceiling_margin_m": ok["k_sigma_ceiling_m"] + 1e-9})
    assert edge["ok"]
    assert not evaluate(r, rep, **{"motion.ceiling_margin_m": ok["k_sigma_ceiling_m"] - 1e-6})["ok"]
    # a larger k tightens it
    big_k = evaluate(r, rep, **{"calibration.bead_k_sigma": 40.0})
    assert not big_k["ok"] and big_k["k"] == 40.0
    # witness chi-squared inconsistent
    bad = evaluate(r, rep, chi2=r.cfg.calibration.norm_rms_max ** 2 + 0.5)
    assert not bad["ok"] and any("witness chi-squared" in x for x in bad["reasons"])
    # the calibration itself not accepted
    seq = StartupSequencer(r.ctx)
    seq.cal_report = dict(rep.measurements["calibration"], accepted=False, reasons=["witness position RMS 9 mm"])
    na = seq.assess_margin_trust()
    assert not na["ok"] and any("calibration not accepted" in x for x in na["reasons"])
    # the real decision is untouched by these what-ifs
    assert r.ctx.ledger.level == "VERIFIED" and r.cfg.motion.ceiling_margin_m == 0.4


@D27_VISION_ONLY
def test_tasks_use_the_full_workspace_only_when_verified(board_probe):
    r, svc, c, rep = board_probe
    ctx, lg = r.ctx, r.ctx.ledger
    # a small validated cluster near the start, well inside the workspace
    saved_vol = ctx.validated_volume
    here = ctx.model.pose_from_positions(ctx.co.positions())[0]
    ctx.validated_volume = here + np.array([[0, 0, 0], [.1, 0, 0], [0, .1, 0], [0, 0, .1], [.1, .1, .1], [-.1, -.1, 0]])
    cands = [q for q in StartupSequencer(ctx)._margin_volume(ctx.result)
             if not ctx.ws.violations(ctx.model.geometry, q)]       # commanded-workspace poses the planner accepts
    far = max(cands, key=lambda q: np.linalg.norm(q - here))
    assert np.linalg.norm(far - here) > 0.6
    saved = (lg.level, lg.verified_basis, list(lg.trust_reasons), lg.margin_check)
    try:
        assert lg.level == "VERIFIED" and TrustedVolume(ctx).allows(far)
        lg.set_level("LOCAL_ONLY", reasons=["test"])
        tv = TrustedVolume(ctx)
        assert tv.allows(here + [0.02, 0.02, 0.02]) and not tv.allows(far)
        with pytest.raises(StartupAbort, match="outside the trusted volume"):
            TaskRunner(ctx, ItemPerception())._move(far, label="far")
    finally:
        ctx.validated_volume = saved_vol
        lg.level, lg.verified_basis, lg.trust_reasons, lg.margin_check = saved


@D27_VISION_ONLY
def test_persisted_ledger_carries_the_basis(board_probe):
    r, svc, c, rep = board_probe
    svc.sup._save()
    saved = TrustLedger.load(svc.data_dir / "ledger.json")
    assert saved.level == "VERIFIED" and saved.verified_basis == "margin" and saved.margin_check["ok"]
    tj = json.loads((svc.data_dir / "trust.json").read_text())
    assert tj["basis"] == "margin" and tj["margin_check"]["k"] == 3.0


@D27_VISION_ONLY
def test_blocked_bead_does_not_prevent_margin_trust_and_all_verified_beads_give_the_beads_basis(board_probe,
                                                                                                monkeypatch):
    r, svc, c, rep = board_probe
    lg = r.ctx.ledger
    saved = (lg.level, lg.verified_basis, list(lg.trust_reasons), lg.margin_check)
    r.cfg.startup.bead_search = True
    try:
        # D24 gating unchanged: with vision-only absolute sigma the search is BLOCKED without moving the claw
        seq = StartupSequencer(r.ctx)
        seq.cal_report = dict(rep.measurements["calibration"])
        pos0 = r.co.positions().copy()
        seq.verify_references()
        out = seq.rep.measurements["beads"]
        assert out and all(b["status"] == "BLOCKED" for b in out.values()), out
        assert np.all(r.co.positions() == pos0)
        # ... and that no longer prevents VERIFIED when (a)-(c) hold
        assert lg.level == "VERIFIED" and lg.verified_basis == "margin"
        assert seq.rep.measurements["margin_trust"]["bead_notes"]
        assert not any(x.startswith("bead ") for x in seq.rep.reasons)
        # an all-verified search is VERIFIED on the basis "beads", whatever the margins say
        monkeypatch.setattr(BeadVerifier, "run", lambda self, i, **kw: BeadOutcome(IDS[i], "VERIFIED", "stub"))
        r.cfg.motion.ceiling_margin_m = 0.001
        seq = StartupSequencer(r.ctx)
        seq.cal_report = dict(rep.measurements["calibration"])
        seq.verify_references()
        assert lg.level == "VERIFIED" and lg.verified_basis == "beads" and not lg.margin_check["ok"]
        # a blocked bead AND failing margins: LOCAL_ONLY, with the bead reason listed
        monkeypatch.setattr(BeadVerifier, "run", lambda self, i, **kw: BeadOutcome(IDS[i], "BLOCKED", "stub reason"))
        seq = StartupSequencer(r.ctx)
        seq.cal_report = dict(rep.measurements["calibration"])
        seq.verify_references()
        assert lg.level == "LOCAL_ONLY" and lg.verified_basis is None
        assert any("ceiling margin" in x for x in lg.trust_reasons) and any("stub reason" in x for x in lg.trust_reasons)
    finally:
        r.cfg.startup.bead_search = False
        r.cfg.motion.ceiling_margin_m = 0.4
        lg.level, lg.verified_basis, lg.trust_reasons, lg.margin_check = saved


@D27_VISION_ONLY
def test_api_exposes_the_basis_numbers_and_reasons(board_probe):
    r, svc, c, rep = board_probe
    lg = r.ctx.ledger
    s = c.get("/api/status").get_json()
    t = s["trust"]
    assert s["level"] == "VERIFIED" and t["level"] == "VERIFIED" and t["basis"] == "margin" and t["full_workspace"]
    assert t["reasons"] == []
    m = t["margin"]
    for k in ("k", "sigma_ceiling_m", "sigma_wall_m", "k_sigma_ceiling_m", "k_sigma_wall_m", "ceiling_margin_m",
              "workspace_margin_m", "worst_pose_ceiling_room_m", "worst_pose_wall_room_m"):
        assert k in m, k
    assert m["k"] * m["sigma_ceiling_m"] == pytest.approx(m["k_sigma_ceiling_m"])
    # when not verified the API says why, in words
    saved = (lg.level, lg.verified_basis, list(lg.trust_reasons))
    try:
        lg.set_level("LOCAL_ONLY", reasons=["slack probe was off: the predicted sigma is not honest"])
        t = c.get("/api/status").get_json()["trust"]
        assert t["level"] == "LOCAL_ONLY" and t["basis"] is None and not t["full_workspace"]
        assert t["reasons"] == ["slack probe was off: the predicted sigma is not honest"]
    finally:
        lg.level, lg.verified_basis, lg.trust_reasons = saved
    page = c.c.get("/").get_data(as_text=True)
    assert 'id="trust"' in page and "trustText" in page


# ============================================================ end to end: no probe -> LOCAL_ONLY
def test_without_the_probe_the_robot_stays_local_only(tmp_path):
    r = SimRobot(fast_cfg(), seed=0, data_dir=tmp_path)
    sup = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    rep = sup.start()
    assert sup.state == "READY", rep.reasons
    assert_no_eq_failures(r, "no-probe startup")
    lg = r.ctx.ledger
    assert lg.level == "LOCAL_ONLY" and lg.verified_basis is None
    m = rep.measurements["margin_trust"]
    assert not m["ok"] and any("slack probe was off" in x for x in lg.trust_reasons)
    assert any("slack probe was off" in x for x in sup.reasons)       # shown where the operator sees reasons
    assert rep.measurements["beads"] == {}                              # bead search off by default
    # the numbers are still computed and recorded (for the operator), they just do not grant anything here
    assert m["k_sigma_ceiling_m"] > 0 and m["k_sigma_wall_m"] > 0 and m["worst_pose_wall_room_m"]
