"""Review of D27: does the printed multi-sheet floor board bring back the floor-stage checks and the slack probe?

The simulator's board hook (SimCamera(board=...), StartupSequencer.study_board) already exists, but SimCamera draws the
SAME iid rotation noise (``rot_sigma``) whatever tags are in view, so the board gives no attitude benefit by
construction; the implementer's stress test therefore measured "single-tag-like attitude noise with a board's depth
noise". This script adds, without touching repository code (monkeypatching the harness names inside this process only):

  mode "fixed"   plant rotation noise = sigma on all three axes (the repo's behaviour; replicates the stress test)
  mode "fixed_t" tilt (x, y) = sigma, yaw = sigma / 10  (real yaw about the optical axis is ~10x better than tilt)
  mode "crb"     rotation noise covariance from the Cramer-Rao bound of the joint PnP over the tags that are in view
                 (corner noise ``pix`` px), i.e. what the real board detector (vision/board.py, joint LM PnP) would give;
                 the estimator's VisionSource.rot_sigma is set to the same tilt sigma every frame (honest estimator)

    OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_board_sim.py --mode crb --seeds 3 --pix 0.3
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import argparse
import json
import math
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sim_floor_reference_study as S                      # noqa: E402  (chdirs to ROOT, sets sys.path)

from roomcleaner.cdpr.frames import inv_T, rotvec_to_matrix   # noqa: E402
from roomcleaner.cdpr.perception import VisionSource           # noqa: E402
from roomcleaner.cdpr.sim import harness                       # noqa: E402
from roomcleaner.cdpr.sim.world import SimCamera               # noqa: E402
from roomcleaner.cdpr.vision.marker import MarkerObservation   # noqa: E402

_DW0 = harness.default_world         # the unpatched function (patching must not nest across jobs in a worker)
from roomcleaner.cdpr.sim import world as _world               # noqa: E402
_FB0 = _world.FloorBoard
CFG = dict(mode="fixed", sigma=0.002, pix=0.3, floor_mrad=1.0, shift=None)
LOG = []                    # (tilt_sigma, n_tags) per board frame (per process)


def rot_cov_camera(P_M, T_C_M, cam, px):
    """3x3 covariance of the pose rotation error about the CAMERA axes (rad^2) from iid corner noise ``px`` (CRB)."""
    R, t = T_C_M[:3, :3], T_C_M[:3, 3]

    def skew_rot(x):
        th = np.linalg.norm(x[:3])
        if th < 1e-14:
            return np.eye(3)
        return rotvec_to_matrix(x[:3])

    def f(x):
        pc = P_M @ (skew_rot(x) @ R).T + (t + x[3:])
        return (pc[:, :2] / pc[:, 2:3] * cam.fx + np.array([cam.K[0, 2], cam.K[1, 2]])).ravel()
    J = np.zeros((2 * len(P_M), 6))
    for k in range(6):
        d = np.zeros(6)
        d[k] = 1e-6
        J[:, k] = (f(d) - f(-d)) / 2e-6
    C = np.linalg.inv(J.T @ J) * px ** 2
    return C[:3, :3]


class ReviewCam(SimCamera):
    def __init__(self, *a, **k):
        k["rot_sigma"] = CFG["sigma"] if CFG["mode"] in ("fixed", "fixed_t") else 0.0
        super().__init__(*a, **k)
        self.last_tilt_sigma = None
        self.n_tags_last = 0

    def _observe_board(self, t_us):
        mode = CFG["mode"]
        if mode == "fixed":
            return super()._observe_board(t_us)
        T_M_B = self.w.T_M_B()
        ks = self.board.visible_tags(self.cam, self.T_B_C, T_M_B, min_side_px=self.min_side)
        if not ks or self.covered:
            return super()._observe_board(t_us)
        T_C_M = inv_T(T_M_B @ self.T_B_C)
        if mode == "fixed_t":
            C = np.diag([CFG["sigma"] ** 2, CFG["sigma"] ** 2, (CFG["sigma"] / 10) ** 2])
        else:
            P = self.board.corners[ks].reshape(-1, 3)
            C = rot_cov_camera(P, T_C_M, self.cam, CFG["pix"])
        # the base class applies Rn(rot_sigma) ... so draw the rotation here and use a zero base rotation noise
        self.rot_sigma = 0.0
        obs = super()._observe_board(t_us)
        if obs.ok:
            dr = self.rng.multivariate_normal(np.zeros(3), C)
            T = obs.T_C_M.copy()
            T[:3, :3] = rotvec_to_matrix(dr) @ T[:3, :3]
            obs.T_C_M = T
            # tilt sigma in the marker frame (roll/pitch of the claw) for the estimator
            Cm = T_C_M[:3, :3].T @ C @ T_C_M[:3, :3]
            self.last_tilt_sigma = math.sqrt((Cm[0, 0] + Cm[1, 1]) / 2)
            self.n_tags_last = len(ks)
            LOG.append((self.last_tilt_sigma, len(ks)))
        return obs


class ReviewVision(VisionSource):
    def observe(self):
        if CFG["mode"] == "crb":
            s = getattr(self.src, "last_tilt_sigma", None)
            if s is not None:
                self.rot_sigma = max(s, CFG["floor_mrad"] * 1e-3)
        return super().observe()


class ShiftedBoard(_FB0):
    """Same grid, translated in the marker frame so that the origin (where the claw rests) is NOT over a tag centre."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        d = np.array([CFG["shift"][0], CFG["shift"][1], 0.0])
        self.centres = self.centres + d
        self.corners = self.corners + d


def patch():
    _world.FloorBoard = ShiftedBoard if CFG.get("shift") else _FB0
    harness.SimCamera = ReviewCam
    harness.VisionSource = ReviewVision


def run_job(job):
    name, spec, seed, extra_world = job
    patch()
    harness.default_world = _DW0
    if extra_world:
        # claw_offset given in the MARKER frame (so that the camera sits over a chosen spot of the board): rotate it into the
        # room frame with the marker yaw that default_world will draw (same rng stream: anchors, marker xy, yaw)
        dw0 = _DW0

        def dw(cfg, stations, *a, **k):
            rng = np.random.default_rng(k.get("seed", 0) + 1000)
            rng.normal(0, 0.04, (4, 3))
            rng.normal(0, 0.15, 2)
            yaw = cfg.marker.heading_prior_rad + rng.normal(0, 0.15)
            c, s_ = math.cos(yaw), math.sin(yaw)
            off = np.asarray(extra_world["claw_offset"], float)
            return dw0(cfg, stations, *a, **k, claw_offset=(c * off[0] - s_ * off[1], s_ * off[0] + c * off[1]))
        harness.default_world = dw
    t0 = time.time()
    out = S.run_one((name, spec, seed))
    out["time_s"] = time.time() - t0
    out["tilt_sigma_mrad_med"] = float(np.median([x[0] for x in LOG]) * 1e3) if LOG else None
    out["tags_med"] = float(np.median([x[1] for x in LOG])) if LOG else None
    LOG.clear()
    return out


def registration(seed, imu):
    """Model-frame vs truth claw position after a normal single-tag startup (fixture-isolation check, item 5)."""
    import tempfile
    sys.path.insert(0, str(ROOT / "tests" / "cdpr"))
    from simkit import fast_cfg
    from roomcleaner.cdpr.sim.harness import SimRobot
    from roomcleaner.cdpr.supervisor import Supervisor
    ov = {"claw.imu": True, "calibration.attitude_sigma_rad": 0.004} if imu else {}
    cfg = fast_cfg(**ov)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = SimRobot(cfg, seed=seed, data_dir=td)
        sup = Supervisor(r.ctx, state_path=td / "state.json", ledger_path=td / "ledger.json")
        sup.start()
        here = r.ctx.model.pose_from_positions(r.ctx.co.positions())[0]
        err = here[:2] - r.world.p[:2]
        vv = r.ctx.validated_volume
        hull = {}
        if vv is not None and len(vv) >= 4:
            from scipy.spatial import ConvexHull, Delaunay
            xy = np.asarray(vv)[:, :2]
            hull = dict(n_pts=len(vv), area_m2=round(float(ConvexHull(xy).volume), 3),
                        z_range=[round(float(np.min(np.asarray(vv)[:, 2])), 2), round(float(np.max(np.asarray(vv)[:, 2])), 2)],
                        room_centre_inside=bool(Delaunay(xy).find_simplex(np.asarray(cfg.room_m[:2]) / 2) >= 0))
        return dict(seed=seed, imu=imu, validated_xy=hull, state=sup.state, trust=r.ctx.ledger.level, model_minus_truth_xy_mm=(err * 1e3).round(1).tolist(),
                    norm_mm=round(float(np.linalg.norm(err)) * 1e3, 1), z_err_mm=round(float(here[2] - r.world.p[2]) * 1e3, 1))


def _reg(j):
    patch()
    return registration(*j)


def main():
    if "--registration" in sys.argv:
        jobs = [(s_, imu) for s_ in range(3) for imu in (False, True)]
        with mp.get_context("fork").Pool(2) as pool:
            for res in pool.imap_unordered(_reg, jobs):
                print(json.dumps(res), flush=True)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="crb", choices=["fixed", "fixed_t", "crb"])
    ap.add_argument("--sigma", type=float, nargs="*", default=[0.002], help="plant sigma(s), rad (fixed modes)")
    ap.add_argument("--pix", type=float, default=0.3)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--case", default="3c sparse 3x3 p0.42 (1.0 m, 9 sheets)")
    ap.add_argument("--cfg", action="append", default=[], metavar="KEY=JSON")
    ap.add_argument("--claw-offset", type=float, nargs=2, default=None, help="shift the start xy (m) from the marker")
    ap.add_argument("--pitch", type=float, default=None, help="override the board pitch (m); tag edge 0.15 (D26)")
    ap.add_argument("--board-shift", type=float, nargs=2, default=None, help="translate the tag grid in the marker frame (m)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    CFG.update(mode=a.mode, pix=a.pix, shift=a.board_shift)
    table = S.case_table()
    base = dict(table[a.case])
    if a.pitch:
        base["board"] = (3, 3, a.pitch, 0.15, "extent", 0.0)
    extra = {"startup.slack_probe": True}
    for kv in a.cfg:
        k_, v_ = kv.split("=", 1)
        extra[k_] = json.loads(v_)
    jobs = []
    sigmas = a.sigma if a.mode != "crb" else [0.0]
    for sg in sigmas:
        for s in range(a.seed0, a.seed0 + a.seeds):
            spec = dict(base, cfg=extra, no_whatif=True, pix=a.pix if a.pix != 0.3 else None)
            nm = f"{a.mode} sigma={sg * 1e3:.0f}mrad pix={a.pix}" + (f" {' '.join(a.cfg)}" if a.cfg else "") + \
                 (f" off={a.claw_offset}" if a.claw_offset else "") + (f" pitch={a.pitch}" if a.pitch else "") + (f" shift={a.board_shift}" if a.board_shift else "")
            jobs.append((nm, spec, s, {"claw_offset": tuple(a.claw_offset)} if a.claw_offset else None, sg))
    print(len(jobs), "runs", flush=True)
    results = []

    def _run(j):
        CFG["sigma"] = j[4]
        return run_job(j[:4])
    with mp.get_context("fork").Pool(a.procs, initializer=lambda: None) as pool:
        # sigma is per job: set it inside the worker through a tiny wrapper
        for res in pool.imap_unordered(_run_wrapper, jobs):
            results.append(res)
            print_one(res)
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1, default=str))


def _run_wrapper(j):
    CFG["sigma"] = j[4]
    return run_job(j[:4])


def print_one(r):
    sig = None
    if "sigma_abs_mm" in r:
        sig = (max(r["sigma_abs_mm"]), float(np.max(np.abs(r["L0_err_mm"]))))
    elif "refit_sigma_abs_mm" in r:
        sig = (max(r["refit_sigma_abs_mm"]), float(np.max(np.abs(r["refit_L0_err_mm"]))))
    pr = r.get("probe")
    cov = None
    if pr:
        cov = pr["readings_probed"] / max(pr["readings_probed"] + pr["readings_skipped"], 1)
    print(json.dumps(dict(case=r["case"], seed=r["seed"], completed=bool(r.get("state") == "READY" or r.get("accepted")),
                          accepted=bool(r.get("accepted")), state=r.get("state"), trust=r.get("trust"),
                          sigma_max_mm=None if sig is None else round(sig[0], 1), L0err_max_mm=None if sig is None else round(sig[1], 1),
                          probed=None if cov is None else round(cov, 2), witness_rms_mm=r.get("witness_rms_mm"),
                          tilt_sigma_mrad_med=r.get("tilt_sigma_mrad_med"), tags_med=r.get("tags_med"),
                          why=(r.get("error") or "; ".join(r.get("reasons", [])))[:140], t=round(r["time_s"]))), flush=True)


if __name__ == "__main__":
    main()
