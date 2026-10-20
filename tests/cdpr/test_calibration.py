"""Estimator, identifiability, slack handling, floor alignment and bead gating
on synthetic data (fast)."""
import math

import numpy as np
import pytest

from roomcleaner.cdpr.calibration import (BeadObs, Calibrator, CableLengthModel, OnsetSample, PoseSample,
                                          align_from_bearings, box_candidates)
from roomcleaner.cdpr.config import load_config
from roomcleaner.cdpr.frames import rot_z
from roomcleaner.cdpr.homing import BeadOutcome, capture_sigma, check_capture
from roomcleaner.cdpr.spool import CableMap

SIM = "config/robot.sim.json"


def point_claw_config():
    """These synthetic-data tests generate lengths for a POINT claw (L = |a - p|), so they run with the common-point
    profile; the four-point claw (spaced attachments, rotated claw) is covered in tests/cdpr/test_rigid_body.py."""
    import json
    raw = json.load(open(SIM))
    raw["claw"]["attachment"] = "common"
    raw["claw"]["attachment_points_body_m"] = [[0, 0, 0]]
    return load_config(raw)


@pytest.fixture(scope="module")
def setup():
    cfg = point_claw_config()
    maps = {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations}
    rng = np.random.default_rng(1)
    aR = cfg.anchor_priors() + rng.normal(0, 0.05, (4, 3))
    psi = np.array([1.5, 1.45, cfg.marker.heading_prior_rad + 0.15])
    aM = (aR - [psi[0], psi[1], 0]) @ rot_z(psi[2])
    L0 = np.array([2.3, 2.5, 2.4, 2.2])
    return cfg, maps, aM, psi, L0


def make_samples(maps, aM, L0, pts, rng, kind="fit", slack=None):
    lm = CableLengthModel(maps)
    out = []
    for k, q in enumerate(pts):
        L = np.linalg.norm(aM - q, axis=1)
        if slack is not None and slack[k] is not None:
            L[slack[k][0]] += slack[k][1]          # commanded longer than the span: slack cable
        P = np.array([lm.position(i, L[i], L0[i]) for i in range(4)])
        cov = np.diag([0.002, 0.002, 0.004]) ** 2
        out.append(PoseSample(np.round(P), q + rng.multivariate_normal(np.zeros(3), cov), np.eye(3), cov, kind))
    return out


def test_small_box_is_reported_prior_dominated_and_large_box_is_accepted(setup):
    cfg, maps, aM, psi, L0 = setup
    cal = Calibrator(cfg, maps)
    rng = np.random.default_rng(2)
    small = box_candidates([0, 0, 0.45], (0.15, 0.15, 0.1))
    res = cal.fit(make_samples(maps, aM, L0, small[rng.choice(len(small), 25, replace=False)], rng))
    assert not res.identifiability.ok
    assert any("L0" in d or "anchor" in d for _, d in res.identifiability.weak)
    big = box_candidates([0, 0, 1.2], (0.8, 0.8, 0.5))
    fit = make_samples(maps, aM, L0, big[rng.choice(len(big), 25, replace=False)], rng)
    wit = make_samples(maps, aM, L0, big[rng.choice(len(big), 5, replace=False)], rng, "witness")
    res = cal.fit(fit)
    rep = cal.validate(res, wit, box_candidates([0, 0, 1.0], (0.8, 0.8, 0.5), (3, 3, 3)))
    assert rep["accepted"], rep["reasons"]
    assert abs(math.remainder(res.psi[2] - psi[2], 2 * math.pi)) < 0.05
    assert np.max(np.abs(res.psi[:2] - psi[:2])) < 0.1
    # the posterior is honest: actual length errors inside the volume are within ~3 sigma
    for q in box_candidates([0, 0, 1.0], (0.6, 0.6, 0.3), (3, 3, 2)):
        err = np.linalg.norm(res.anchors_M - q, axis=1) - res.L0 - (np.linalg.norm(aM - q, axis=1) - L0)
        assert np.all(np.abs(err) < 3 * cal.length_sigma(res, q) + 1e-3)


def test_slack_cables_are_identified_instead_of_bending_the_fit(setup):
    cfg, maps, aM, psi, L0 = setup
    cal = Calibrator(cfg, maps)
    rng = np.random.default_rng(3)
    big = box_candidates([0, 0, 1.2], (0.8, 0.8, 0.5))
    pts = big[rng.choice(len(big), 30, replace=False)]
    slack = [(int(rng.integers(4)), float(rng.uniform(0.01, 0.04))) if rng.random() < 0.4 else None
             for _ in pts]
    fit = make_samples(maps, aM, L0, pts, rng, slack=slack)
    wit = make_samples(maps, aM, L0, big[rng.choice(len(big), 5, replace=False)], rng, "witness")
    res = cal.fit(fit)
    truth = np.array([[s is not None and s[0] == i for i in range(4)] for s in slack])
    assert (res.slack & truth).sum() >= 0.8 * truth.sum()
    assert (res.slack & ~truth).sum() <= 1
    assert cal.validate(res, wit)["accepted"]


def test_bearings_register_the_marker_and_expose_swapped_wiring(setup):
    cfg, maps, aM, psi, L0 = setup
    cal = Calibrator(cfg, maps)
    aR = aM @ rot_z(psi[2]).T + [psi[0], psi[1], 0]
    claw = np.zeros((4, 3))
    claw[:, 2] = 0.35
    b = np.array([math.atan2(*(aM[i, [1, 0]] - claw[i, [1, 0]])) for i in range(4)])
    pr = cal.priors
    est, cov, rms = align_from_bearings(pr, claw, b + np.random.default_rng(4).normal(0, 0.05, 4))
    assert rms < 2 and abs(math.remainder(est[2] - psi[2], 2 * math.pi)) < 0.1
    swapped = b[[1, 0, 2, 3]]                      # stations A and B wired to each other's corners
    _, _, rms_bad = align_from_bearings(pr, claw, swapped)
    assert rms_bad > cfg.startup.bearing_rms_max


def test_onsets_alone_determine_L0_given_anchor_priors(setup):
    cfg, maps, aM, psi, L0 = setup
    cal = Calibrator(cfg, maps)
    lm = CableLengthModel(maps)
    q = np.array([0.0, 0.0, 0.35])
    ons = []
    for i in range(4):
        L = np.linalg.norm(aM[i] - q)
        ons.append(OnsetSample(i, lm.position(i, L, L0[i]), q, np.eye(3), np.eye(3) * 1e-6))
    res = cal.fit([], ons, psi_inits=[psi])
    sig = cal.absolute_sigma(res)
    assert np.all(np.abs(res.L0 - L0) < 3 * sig + 0.01)


def test_bead_observation_pins_absolute_length(setup):
    cfg, maps, aM, psi, L0 = setup
    rng = np.random.default_rng(5)
    small = box_candidates([0, 0, 0.6], (0.3, 0.3, 0.15))
    fit = make_samples(maps, aM, L0, small[rng.choice(len(small), 25, replace=False)], rng)
    cal = Calibrator(cfg, maps)
    before = cal.absolute_sigma(cal.fit(fit))
    lm = CableLengthModel(maps)
    cal.beads = [BeadObs(i, lm.position(i, 1.2, L0[i]), 1.2, 0.002) for i in range(4)]
    res = cal.fit(fit)
    after = cal.absolute_sigma(res)
    assert np.all(after < before / 3)
    assert np.all(np.abs(res.L0 - L0) < 0.01)


def test_bead_capture_check_and_sigma():
    class B:
        trigger_length_m, uncertainty_m, approach_speed_m_s = 1.2, 0.002, 0.004
    s = capture_sigma(B, 0.001, 1.8e-5)
    assert 0.0022 < s < 0.0024
    ok = check_capture(lambda i, P: 1.203, 0, 100.0, B, s, 3.0)
    bad = check_capture(lambda i, P: 1.215, 0, 100.0, B, s, 3.0)
    assert ok.consistent and not bad.consistent
    assert isinstance(BeadOutcome("A", "BLOCKED"), BeadOutcome)
