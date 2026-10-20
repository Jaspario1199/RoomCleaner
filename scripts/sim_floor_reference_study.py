"""Floor-reference study: how large / accurate must the printed floor reference
be for the self-calibration to pin ABSOLUTE cable lengths well enough for the
homing beads (docs/CONTROL_SYSTEM_V1.md 6.4, decision D-B)?

Runs the full simulated startup (Supervisor.start) for a set of floor-reference
cases and seeds and reports, per case: predicted absolute length sigma (the
quantity the bead gate uses), the actual |L0 error|, the trust level, bead
status, witness RMS and wall time.

    /usr/bin/python3 scripts/sim_floor_reference_study.py --suite all --seeds 3 --out results.json
    /usr/bin/python3 scripts/sim_floor_reference_study.py --suite quick --seeds 1

SIMULATION ONLY. The multi-tag board is the STUDY HOOK ``sim.world.FloorBoard``
(plus ``StartupSequencer.study_board``); neither is active by default.
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):   # one thread per worker process
    os.environ.setdefault(_v, "1")
import argparse
import json
import math
import multiprocessing as mp
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "cdpr"))
os.chdir(ROOT)

LETTER_W = 0.2159   # US Letter short side (m)


def case_table():
    """name -> spec dict(board=(nx, ny, pitch, tag_edge, span_mode, layout_err) | None, span=None | m,
    tilt=None | rad (sim IMU noise AND the estimator's tilt sigma), pix=None | px, box=None | (bx, by, bz) half
    extents of calibration.expanded_box_m, EA=None | N cable stiffness)."""
    C = {}

    def add(name, group, **kw):
        d = dict(group=group, board=None, span=None, tilt=None, pix=None, box=None, EA=None)
        d.update(kw)
        C[name] = d

    e = 0.16                                      # tag edge: fits a Letter sheet (215.9 mm) with a 28 mm white border
    add("1 baseline single 6in tag", "1")
    add("2a board_span 0.30 (existing opt)", "2", span=0.30)
    add("2b board_span 0.60 (existing opt)", "2", span=0.60)
    grids = {
        "3a dense 3x3 p0.22 (0.60 m, 9 sheets)": (3, 3, 0.22),
        "3b dense 5x5 p0.21 (1.0 m, 25 sheets)": (5, 5, 0.21),
        "3c sparse 3x3 p0.42 (1.0 m, 9 sheets)": (3, 3, 0.42),
        "3d sparse 5x5 p0.34 (1.5 m, 25 sheets)": (5, 5, 0.34),
        "3e very sparse 3x3 p0.67 (1.5 m, 9 sheets)": (3, 3, 0.67),
        "3f dense 7x7 p0.22 (1.5 m, 49 sheets)": (7, 7, 0.22),
    }
    for name, (nx, ny, p) in grids.items():
        add(name, "3", board=(nx, ny, p, e, "extent", 0.0))
    add("3g dense 5x5 p0.21, rms span", "3", board=(5, 5, 0.21, e, "rms", 0.0))
    add("3h dense 7x7 p0.22, rms span", "3", board=(7, 7, 0.22, e, "rms", 0.0))
    # wider excitation box (config knob calibration.expanded_box_m, overridden in memory only) and stiffer cable
    f = (7, 7, 0.22, e, "extent", 0.0)
    add("6a 3f, box 1.0/0.5", "6", board=f, box=(1.0, 1.0, 0.5))
    add("6b 3f, box 1.2/0.5", "6", board=f, box=(1.2, 1.2, 0.5))
    add("6c 3f, box 1.2/0.5, cable EA x10", "6", board=f, box=(1.2, 1.2, 0.5), EA=2.0e5)
    add("6d 3f, box 0.8/0.5, cable EA x10", "6", board=f, EA=2.0e5)
    add("6e baseline tag, box 0.8/0.5, cable EA x10", "6", EA=2.0e5)
    add("6f 3f, box 1.2/0.8, cable EA x10", "6", board=f, box=(1.2, 1.2, 0.8), EA=2.0e5)
    return C


def sens_cases(best, box=None, EA=None):
    """sensitivity variants of a board case: IMU tilt noise, pixel noise, tag layout error."""
    C = {}

    def add(name, group, **kw):
        d = dict(group=group, board=best, span=None, tilt=None, pix=None, box=box, EA=EA)
        d.update(kw)
        C[name] = d

    for tag, tilt in (("tilt 3 mrad", 0.003), ("tilt 1 mrad", 0.001), ("tilt 0.3 mrad", 0.0003)):
        add(f"4 {tag}", "4", tilt=tilt)
    for pix in (0.15, 0.6):
        add(f"4 pixel_sigma {pix}", "4", pix=pix)
    add("4 tilt 1 mrad + pixel 0.15", "4", tilt=0.001, pix=0.15)
    add("5 layout err 0 mm (ref)", "5")
    for err in (0.001, 0.002):
        b = list(best)
        b[5] = err
        add(f"5 layout err {err * 1e3:.0f} mm", "5", board=tuple(b))
    return C


def vision_components(r, smp, board, spec_pix, n_frames):
    """Re-derive one fit sample's vision covariance as pixel / tilt / rotation parts (same model as
    VisionSource._fused, averaged over ``n_frames``). Returns dict of 3x3 covariances (position, m^2)."""
    from roomcleaner.cdpr.frames import make_T
    T_B_C = np.asarray(r.cfg.claw.T_body_cam, float)
    T_M_C = make_T(smp.R, smp.p) @ T_B_C
    Rmc, c = T_M_C[:3, :3], T_M_C[:3, 3]
    t = -Rmc.T @ c                                    # marker origin in the camera frame
    z, h = float(t[2]), float(np.linalg.norm(t))
    fx = r.camera.fx
    pix = spec_pix if spec_pix else 0.3
    if board is not None:
        T_M_B = make_T(smp.R, smp.p)
        edge = board.edge_eff(r.camera, T_B_C, T_M_B, min_side_px=r.cfg.camera.min_marker_pixels)
    else:
        edge = r.vision.edge
    return Rmc, z, h, fx, pix, edge, float(np.linalg.norm(smp.p[:2]))


def whatif(r, board, spec_pix, tilt_sigma, n_frames):
    """Refit the SAME fit samples with the vision covariance rescaled by component (no new motion, no new
    noise) and return the predicted absolute sigma (max over stations, mm). Isolates what limits the
    absolute length: pixel/depth noise, IMU tilt, or the geometry/prior/encoder floor."""
    import copy
    ctx = r.ctx
    fit = [s for s in ctx.samples if s.kind == "fit"]
    rot_sigma = r.vision.rot_sigma
    parts = []
    for s in fit:
        Rmc, z, h, fx, pix, edge, horiz = vision_components(r, s, board, spec_pix, n_frames)
        lat = pix * z / fx
        dep = 2 * pix * z * z / (fx * edge)
        Cp = Rmc @ np.diag([lat ** 2, lat ** 2, dep ** 2]) @ Rmc.T / n_frames
        Ct = np.diag([(tilt_sigma * h) ** 2] * 2 + [0.0]) / n_frames
        Cr = (np.eye(3) * (rot_sigma * horiz) ** 2 + np.eye(3) * 1e-8) / n_frames
        parts.append((Cp, Ct, Cr))
    recon = np.median([np.linalg.norm(Cp + Ct + Cr - s.cov) / np.linalg.norm(s.cov) for (Cp, Ct, Cr), s in zip(parts, fit)])
    out = {"recon_rel_err": float(recon)}
    # (pixel, tilt, rotation) sigma scales, encoder/spool length-noise scale, anchor-prior scale
    variants = {"as_run": (1, 1, 1, 1, 1), "pixel x0.5": (0.5, 1, 1, 1, 1), "tilt x1/3": (1, 1 / 3, 1, 1, 1),
                "pixel x0.5 & tilt x1/3": (0.5, 1 / 3, 1, 1, 1),
                "all vision noise ->0": (1e-3, 1e-3, 1e-3, 1, 1),
                "length noise x0.5": (1, 1, 1, 0.5, 1), "length noise x0.1": (1, 1, 1, 0.1, 1),
                "vision ->0 & length x0.1": (1e-3, 1e-3, 1e-3, 0.1, 1),
                "anchor prior 2 cm": (1, 1, 1, 1, "abs0.02"),
                "anchor prior 1 cm": (1, 1, 1, 1, "abs0.01"),
                "anchor prior 0.5 cm": (1, 1, 1, 1, "abs0.005"),
                "vision ->0 & length x0.1 & anchor 1 cm": (1e-3, 1e-3, 1e-3, 0.1, "abs0.01")}
    cal = ctx.cal
    cc0, pr0 = cal.cc, cal.priors
    for name, (a, b, c, ls, asc) in variants.items():
        smp = []
        for (Cp, Ct, Cr), s in zip(parts, fit):
            q = copy.copy(s)
            q.cov = a * a * Cp + b * b * Ct + c * c * Cr
            smp.append(q)
        cc1, pr1 = copy.copy(cc0), copy.copy(pr0)
        object.__setattr__(cc1, "length_sigma_m", cc0.length_sigma_m * ls)
        a_new = (np.full(4, float(asc[3:])) if isinstance(asc, str) else np.asarray(pr0.anchor_sigma) * asc)
        object.__setattr__(pr1, "anchor_sigma", a_new)
        cal.cc, cal.priors = cc1, pr1
        try:
            res = cal.fit(smp, ctx.onsets, L0_init=ctx.result.L0, psi_inits=[ctx.result.psi])
            out[name] = float(np.max(cal.absolute_sigma(res)) * 1e3)
        except Exception as ex:
            out[name] = f"fail {type(ex).__name__}"
        finally:
            cal.cc, cal.priors = cc0, pr0
    return out


def run_one(args):
    name, spec, seed = args
    from roomcleaner.cdpr.calibration import IDS
    from roomcleaner.cdpr.sim.harness import SimRobot
    from roomcleaner.cdpr.sim.world import FloorBoard
    from roomcleaner.cdpr.startup import StartupSequencer
    from roomcleaner.cdpr.supervisor import Supervisor
    from simkit import fast_cfg
    cfg = fast_cfg(**({"calibration.expanded_box_m": list(spec["box"])} if spec.get("box") else {}))
    ck = {}
    if spec["span"]:
        ck["board_span_m"] = spec["span"]
    if spec["pix"]:
        ck["pixel_sigma"] = spec["pix"]
    board = None
    if spec["board"]:
        nx, ny, p, e, mode, err = spec["board"]
        board = FloorBoard(nx, ny, p, e, layout_err_m=err, span_mode=mode, seed=seed)
        ck["board"] = board
    out = dict(case=name, seed=seed)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        wk = {"EA_n": spec["EA"]} if spec.get("EA") else None
        r = SimRobot(cfg, seed=seed, data_dir=td, camera_kw=ck, world_kw=wk)
        if spec["tilt"] is not None:
            r.claw.tilt_noise = spec["tilt"]
            r.vision.tilt_sigma = spec["tilt"]
        sup = Supervisor(r.ctx, state_path=td / "state.json", ledger_path=td / "ledger.json")
        StartupSequencer.study_board = board
        try:
            rep = sup.start()
        except Exception as ex:                      # a startup abort is a result, not a crash of the study
            out.update(error=f"{type(ex).__name__}: {ex}"[:300], state=sup.state)
            out["time_s"] = time.time() - t0
            return out
        finally:
            StartupSequencer.study_board = None
        m = rep.measurements
        out["state"] = sup.state
        out["reasons"] = [x[:160] for x in rep.reasons][:4]
        out["log_tail"] = [x[:200] for x in r.log_lines if "reject" in x.lower() or "abort" in x.lower()][-2:]
        out["trust"] = r.ctx.ledger.level
        out["accepted"] = "absolute_sigma_m" in m
        if out["accepted"]:
            sig = np.asarray(m["absolute_sigma_m"])
            err_L0 = np.array([r.ctx.model.maps[s].L0 - r.world.true_L0(s) for s in IDS])
            out["sigma_abs_mm"] = (sig * 1e3).tolist()
            out["L0_err_mm"] = (err_L0 * 1e3).tolist()
        else:
            # the startup rejected its own calibration: refit all fit samples to still see sigma / error
            fit_all = [x for x in r.ctx.samples if x.kind == "fit"]
            if len(fit_all) >= 20:
                try:
                    res = r.ctx.cal.fit(fit_all, r.ctx.onsets, L0_init=r.ctx.result.L0, psi_inits=[r.ctx.result.psi])
                    out["refit_sigma_abs_mm"] = (r.ctx.cal.absolute_sigma(res) * 1e3).tolist()
                    out["refit_L0_err_mm"] = [(res.L0[i] - r.world.true_L0(sid)) * 1e3 for i, sid in enumerate(IDS)]
                except Exception as ex:
                    out["refit_error"] = f"{type(ex).__name__}: {ex}"[:120]
        if "calibration" in m:
            out["witness_chi2_dof"] = m["calibration"].get("witness_chi2_dof")
            out["witness_rms_mm"] = m["calibration"]["witness_rms_m"] * 1e3
            out["validated_points"] = m.get("validated_points")
        if r.ctx.model is not None and r.ctx.result is not None:
            home = r.ctx.model.pose_from_positions(r.ctx.co.positions())[0]
            Lh = r.ctx.model.geometry.lengths(home)
            trig = np.array([st.bead.trigger_length_m for st in cfg.stations])
            out["home_length_m"] = Lh.tolist()
            out["payout_term_mm"] = (cfg.calibration.payout_scale_sigma * np.abs(Lh - trig) * 1e3).tolist()
        if "beads" in m:
            out["beads"] = {s: dict(status=b["status"], reason=b["reason"][:120], sigma_mm=(b["sigma_m"] or 0) * 1e3)
                            for s, b in m["beads"].items()}
        # excitation diagnostics: spread of the fit poses and of the cable directions seen from each true anchor
        fit = [s for s in r.ctx.samples if s.kind == "fit"]
        if fit:
            P = np.array([s.p for s in fit])                         # marker frame
            out["n_fit"] = len(fit)
            out["fit_extent_xy_m"] = float(np.mean(P[:, :2].max(0) - P[:, :2].min(0)))
            out["fit_extent_z_m"] = float(P[:, 2].max() - P[:, 2].min())
            T = r.world.T_R_M                                        # marker->room (truth)
            Pr = (T[:3, :3] @ P.T).T + T[:3, 3]
            spread = []
            for a in r.world.anchors:
                u = a - (Pr + np.asarray(r.world.cfg.attachment_points()[0]))
                u /= np.linalg.norm(u, axis=1)[:, None]
                spread.append(float(np.sqrt(np.mean(np.sum((u - u.mean(0)) ** 2, axis=1)))))
            out["dir_spread_rad"] = spread
            out["vis_sigma_med_mm"] = float(np.median([math.sqrt(np.trace(s.cov) / 3) for s in fit]) * 1e3)
        try:
            out["whatif_sigma_max_mm"] = whatif(r, board, spec["pix"], r.vision.tilt_sigma,
                                                cfg.calibration.noise_capture_frames)
        except Exception as ex:
            out["whatif_sigma_max_mm"] = {"error": f"{type(ex).__name__}: {ex}"[:200]}
    out["time_s"] = time.time() - t0
    return out


def _sig_err(r):
    """(sigma_max_mm, |L0 err|_max_mm, from_refit) for a run, or None."""
    if "sigma_abs_mm" in r:
        return max(r["sigma_abs_mm"]), float(np.max(np.abs(r["L0_err_mm"]))), False
    if "refit_sigma_abs_mm" in r:
        return max(r["refit_sigma_abs_mm"]), float(np.max(np.abs(r["refit_L0_err_mm"]))), True
    return None


def summarize(results):
    by = {}
    for r in results:
        by.setdefault(r["case"], []).append(r)
    rows = []
    for name, rs in by.items():
        acc = [r for r in rs if r.get("accepted")]
        se = [(r, _sig_err(r)) for r in rs]
        se = [(r, v) for r, v in se if v]
        row = dict(case=name, runs=len(rs), accepted=len(acc), time_s=float(np.mean([r["time_s"] for r in rs])))
        if se:
            sg = np.array([v[0] for _, v in se])
            er = np.array([v[1] for _, v in se])
            row.update(sigma_med=float(np.median(sg)), sigma_max=float(sg.max()), sigma_min=float(sg.min()),
                       err_med=float(np.median(er)), err_max=float(er.max()),
                       err_over_sigma_max=float(np.max(er / sg)),
                       fit_xy=float(np.mean([r.get("fit_extent_xy_m", np.nan) for r, _ in se])),
                       dir_spread=float(np.mean([np.mean(r.get("dir_spread_rad", [np.nan])) for r, _ in se])))
        if acc:
            row.update(witness_mm=float(np.max([r.get("witness_rms_mm", np.nan) for r in acc])),
                       trust=",".join(sorted({r["trust"] for r in acc})),
                       beads=",".join(sorted({b["status"] for r in acc for b in r.get("beads", {}).values()})),
                       gate_sigma_med=float(np.median([max(b["sigma_mm"] for b in r["beads"].values())
                                                       for r in acc if r.get("beads")] or [np.nan])),
                       payout_term_med=float(np.median([max(r["payout_term_mm"]) for r in acc
                                                        if "payout_term_mm" in r] or [np.nan])))
        row["rejections"] = [(r["seed"], (r.get("error") or "; ".join(r.get("reasons", [])))[:90])
                             for r in rs if not r.get("accepted")]
        row["whatif"] = _median_whatif(rs)
        rows.append(row)
    return rows


def _median_whatif(rs):
    keys = {}
    for r in rs:
        w = r.get("whatif_sigma_max_mm") or {}
        for k, v in w.items():
            if isinstance(v, float) and k != "recon_rel_err":
                keys.setdefault(k, []).append(v)
    return {k: float(np.median(v)) for k, v in keys.items()}


def print_table(rows):
    print(f"{'case':44s} {'acc':>4s} {'sig_med':>8s} {'sig_max':>8s} {'err_med':>8s} {'err_max':>8s} {'e/s_max':>7s} "
          f"{'wit':>5s} {'trust':>10s} {'beads':>9s} {'gate':>6s} {'pay':>5s} {'fitxy':>5s} {'dirsp':>6s} {'t/run':>6s}")
    for r in rows:
        if "sigma_med" not in r:
            print(f"{r['case']:44s} {r['accepted']}/{r['runs']}  no sigma  {r['rejections']}")
            continue
        print(f"{r['case']:44s} {r['accepted']}/{r['runs']:<2d} {r['sigma_med']:8.2f} {r['sigma_max']:8.2f} "
              f"{r['err_med']:8.1f} {r['err_max']:8.1f} {r['err_over_sigma_max']:7.1f} "
              f"{r.get('witness_mm', float('nan')):5.2f} {r.get('trust', '-'):>10s} {r.get('beads', '-'):>9s} "
              f"{r.get('gate_sigma_med', float('nan')):6.1f} {r.get('payout_term_med', float('nan')):5.1f} "
              f"{r['fit_xy']:5.2f} {r['dir_spread']:6.3f} {r['time_s']:6.0f}")
        for sd, why in r["rejections"]:
            print(f"{'':50s} seed {sd} rejected: {why}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="quick",
                    help="quick | main (groups 1-3) | wide (group 6) | sens (groups 4/5 on --best) | all")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--procs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None, help="substring filter on case names")
    ap.add_argument("--best", default="3a dense 3x3 p0.22 (0.60 m, 9 sheets)", help="board case for groups 4/5")
    ap.add_argument("--best-box", default=None, help="bx,bz half extents for groups 4/5 (default: config)")
    ap.add_argument("--best-ea", type=float, default=None)
    a = ap.parse_args()
    table = case_table()
    cases = {}
    if a.suite == "quick":
        cases = {k: v for k, v in table.items() if k.startswith(("1", "3a"))}
    if a.suite in ("main", "all"):
        cases.update({k: v for k, v in table.items() if v["group"] in ("1", "2", "3")})
    if a.suite in ("wide", "all"):
        cases.update({k: v for k, v in table.items() if v["group"] == "6"})
    if a.suite in ("sens", "all"):
        box = None
        if a.best_box:
            bxy, bz = (float(x) for x in a.best_box.split(","))
            box = (bxy, bxy, bz)
        cases.update(sens_cases(table[a.best]["board"], box, a.best_ea))
    if a.only:
        cases = {k: v for k, v in cases.items() if a.only in k}
    jobs = [(k, v, s) for k, v in cases.items() for s in range(a.seed0, a.seed0 + a.seeds)]
    print(f"{len(jobs)} runs on {a.procs} processes", flush=True)
    results = []
    with mp.get_context("fork").Pool(a.procs) as pool:
        for res in pool.imap_unordered(run_one, jobs):
            results.append(res)
            v = _sig_err(res)
            print(f"  done {res['case']} seed {res['seed']}: {'accepted' if res.get('accepted') else 'REJECTED'} "
                  f"sigma={v[0] if v else float('nan'):.1f} err={v[1] if v else float('nan'):.1f} ({res['time_s']:.0f}s)",
                  flush=True)
    results.sort(key=lambda r: (r["case"], r["seed"]))
    rows = summarize(results)
    print_table(rows)
    if a.out:
        Path(a.out).write_text(json.dumps(dict(results=results, summary=rows), indent=1))


if __name__ == "__main__":
    main()
