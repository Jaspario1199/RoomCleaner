"""Independent review of D27: what rotation (tilt) noise does a vision-only pose have, single tag vs the floor board?

Pure-numpy / OpenCV study, no simulator.  Two independent methods:
  * CRB: Cramer-Rao bound of the 6-DOF pose from the corner reprojection Jacobian (iid pixel noise).
  * MC : Monte Carlo through cv2.solvePnP (IPPE), noisy corners.
Quantities: sigma of the tag-normal tilt (roll/pitch of the camera relative to the floor, rad), and the 1-sigma of the
camera position in the marker frame (lever term: tilt sigma * range).

    OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_attitude_noise.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FX, FY, CX, CY, W, H = 520.0, 520.0, 400.0, 300.0, 800, 600           # config/camera.sim.json (OV2640-class guess)
K = np.array([[FX, 0, CX], [0, FY, CY], [0, 0, 1.0]])


def rotvec(v):
    return cv2.Rodrigues(np.asarray(v, float).reshape(3, 1))[0]


def tag_corners(cx, cy, edge, yaw=0.0):
    h = edge / 2
    loc = np.array([[-h, h], [h, h], [h, -h], [-h, -h]])
    c, s = math.cos(yaw), math.sin(yaw)
    R = np.array([[c, -s], [s, c]])
    xy = loc @ R.T + [cx, cy]
    return np.c_[xy, np.zeros(4)]


def board_tags(pitch, edge, n=3):
    c = (np.arange(n) - (n - 1) / 2) * pitch
    return [(x, y) for y in c for x in c]


def camera_pose(cam_xyz, tilt_xy=(0.0, 0.0)):
    """T_C_M (R, t) for a camera at cam_xyz in the marker frame looking straight down, plus a small tilt."""
    R_M_C = rotvec([tilt_xy[0], tilt_xy[1], 0.0]) @ np.diag([1.0, -1.0, -1.0])
    R_C_M = R_M_C.T
    t = -R_C_M @ np.asarray(cam_xyz, float)
    return R_C_M, t


def visible(tags, edge, R, t, margin=4, min_side=40.0):
    keep = []
    for (x, y) in tags:
        pc = tag_corners(x, y, edge) @ R.T + t
        if np.any(pc[:, 2] < 0.05):
            continue
        uv = pc[:, :2] / pc[:, 2:3] * FX + [CX, CY]
        if not (np.all(uv[:, 0] > margin) and np.all(uv[:, 0] < W - margin) and np.all(uv[:, 1] > margin) and np.all(uv[:, 1] < H - margin)):
            continue
        side = np.mean([np.linalg.norm(uv[k] - uv[(k + 1) % 4]) for k in range(4)])
        if side >= min_side:
            keep.append((x, y))
    return keep


def project(P, R, t):
    pc = P @ R.T + t
    return pc[:, :2] / pc[:, 2:3] * FX + [CX, CY]


def crb(P, R, t, px):
    """Pose covariance (rotation vector about camera axes, translation) from iid pixel noise px; numerical Jacobian."""
    def f(x):
        Rn = rotvec(x[:3]) @ R
        return project(P, Rn, t + x[3:]).ravel()
    x0 = np.zeros(6)
    J = np.zeros((2 * len(P), 6))
    for k in range(6):
        d = np.zeros(6)
        d[k] = 1e-6
        J[:, k] = (f(x0 + d) - f(x0 - d)) / 2e-6
    C = np.linalg.inv(J.T @ J) * px ** 2
    return C


def pose_stats_from_cov(C, R, t):
    """tilt sigma (roll,pitch about the MARKER axes x,y) and camera-position sigma in M from the 6x6 covariance."""
    # perturbation: R' = dR(cam) R ;  camera orientation error in M = R^T dr ; marker-frame tilt about x,y
    Rm = R.T
    A = np.zeros((6, 6))                # map (dr_cam, dt_cam) -> (dtheta_M (3), dcam_pos_M (3))
    A[:3, :3] = Rm                      # rotation error expressed in the marker frame (small angle)
    # camera position c = -R^T t ;  dc = -dR^T t - R^T dt ;  dR = [dr]x R  ->  dR^T = -R^T [dr]x
    def skew(v):
        return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    # dc = R^T [dr]x t - R^T dt = -R^T [t]x dr - R^T dt
    A[3:, :3] = -Rm @ skew(t)
    A[3:, 3:] = -Rm
    S = A @ C @ A.T
    return S


def mc(P, R, t, px, n=3000, seed=1, refine=False):
    """Monte Carlo through cv2.  refine=False: IPPE only, the candidate with the lowest reprojection error (this is what
    the repo's SINGLE-tag MarkerDetector.pose_from_corners does when it is not ambiguous).  refine=True: each IPPE
    candidate polished with solvePnPRefineLM, lowest reprojection error kept (what vision/board.py does)."""
    rng = np.random.default_rng(seed)
    uv0 = project(P, R, t)
    out_tilt, out_pos, flips = [], [], 0
    flag = cv2.SOLVEPNP_IPPE if len(P) > 4 else cv2.SOLVEPNP_IPPE_SQUARE
    c_true = -R.T @ t
    P64 = P.astype(np.float64)
    for _ in range(n):
        uv = (uv0 + rng.normal(0, px, uv0.shape)).astype(np.float64)
        try:
            k, rvs, tvs, errs = cv2.solvePnPGeneric(P64, uv, K, None, flags=flag)
        except cv2.error:
            continue
        cands = []
        for rv_, tv_ in zip(rvs, tvs):
            if refine:
                rv_, tv_ = cv2.solvePnPRefineLM(P64, uv, K, None, rv_.copy(), tv_.copy())
            pr = cv2.projectPoints(P64, rv_, tv_, K, None)[0].reshape(-1, 2)
            cands.append((float(np.sqrt(np.mean(np.sum((pr - uv) ** 2, axis=1)))), rv_, tv_))
        cands.sort(key=lambda c: c[0])
        _, rv_, tv_ = cands[0]
        Rc = cv2.Rodrigues(rv_)[0]
        e_M = R.T @ cv2.Rodrigues(Rc @ R.T)[0].ravel()
        if np.linalg.norm(e_M[:2]) > 0.05 + 3 * 0.0:
            flips += 1
        out_tilt.append(e_M[:2])
        out_pos.append(-Rc.T @ tv_.ravel() - c_true)
    return np.array(out_tilt), np.array(out_pos), flips / max(len(out_tilt), 1)


def row(label, tags, edge, cam_xyz, px, tilt_xy=(0.0, 0.0), do_mc=True, n=2000):
    R, t = camera_pose(cam_xyz, tilt_xy)
    vis = visible(tags, edge, R, t)
    if not vis:
        return dict(label=label, cam=list(cam_xyz), n_tags=0)
    P = np.vstack([tag_corners(x, y, edge) for (x, y) in vis])
    C = crb(P, R, t, px)
    S = pose_stats_from_cov(C, R, t)
    rng_cam = float(np.linalg.norm(t))
    d = dict(label=label, cam=[round(c, 3) for c in cam_xyz], n_tags=len(vis), px=px, range_m=round(rng_cam, 3),
             crb_tilt_mrad=round(1e3 * math.sqrt((S[0, 0] + S[1, 1]) / 2), 2),
             crb_yaw_mrad=round(1e3 * math.sqrt(S[2, 2]), 2),
             crb_pos_xy_mm=round(1e3 * math.sqrt((S[3, 3] + S[4, 4]) / 2), 2),
             crb_pos_z_mm=round(1e3 * math.sqrt(S[5, 5]), 2),
             lever_pred_mm=round(1e3 * math.sqrt((S[0, 0] + S[1, 1]) / 2) * rng_cam, 2))
    if do_mc:
        for tag, ref in (("ippe", False), ("lm", True)):
            T, Pp, fl = mc(P, R, t, px, n=n, refine=ref)
            d.update({f"{tag}_tilt_mrad": round(1e3 * float(np.sqrt(np.mean(T ** 2))), 2),
                      f"{tag}_tilt_med_mrad": round(1e3 * float(np.median(np.abs(T))) / 0.6745, 2),
                      f"{tag}_pos_xy_mm": round(1e3 * float(np.sqrt(np.mean(Pp[:, :2] ** 2))), 2),
                      f"{tag}_flip_frac": round(fl, 3)})
    return d


def main():
    edge_s = 0.1524                    # config marker.edge_m (single 6-inch tag)
    edge_b = 0.150                     # floor board tags (D26)
    single = [(0.0, 0.0)]
    board = board_tags(0.42, edge_b)   # 3x3, pitch 0.42 -> span 1.0 m (the study's case 3c; Letter sheets fit)
    rows = []
    for px in (0.3,):
        for h in (0.46, 0.6, 0.8, 1.0, 1.3):
            for off in ((0.0, 0.0), (0.2, 0.1)):
                rows.append(row("single 152mm", single, edge_s, (off[0], off[1], h), px, tilt_xy=(0.03, -0.02), n=1000))
                rows.append(row("board 3x3 p0.42", board, edge_b, (off[0], off[1], h), px, tilt_xy=(0.03, -0.02), n=1000))
    print(f"{'case':16s} {'px':>3s} {'cam xyz (m)':>18s} {'tags':>4s} | {'CRB tilt':>8s} {'pos xy':>6s} | {'IPPE-only rms/med':>17s} {'pos':>6s} {'flip':>5s} | {'IPPE+LM rms/med':>16s} {'pos':>6s} {'flip':>5s}   (tilt mrad, pos mm)")
    for r in rows:
        if r["n_tags"] == 0:
            print(f"{r['label']:16s} {'':>3s} {str(r['cam']):>18s}    0  (nothing usable in view)")
            continue
        print(f"{r['label']:16s} {r['px']:3.1f} {str(r['cam']):>18s} {r['n_tags']:4d} | {r['crb_tilt_mrad']:8.2f} {r['crb_pos_xy_mm']:6.2f} | "
              f"{r['ippe_tilt_mrad']:8.1f}/{r['ippe_tilt_med_mrad']:<8.1f} {r['ippe_pos_xy_mm']:6.1f} {r['ippe_flip_frac']:5.2f} | "
              f"{r['lm_tilt_mrad']:7.1f}/{r['lm_tilt_med_mrad']:<8.1f} {r['lm_pos_xy_mm']:6.1f} {r['lm_flip_frac']:5.2f}")
    # averaging: N independent frames
    R, t = camera_pose((0, 0, 0.6), (0.03, -0.02))
    P = tag_corners(0, 0, edge_s)
    T, Pp, _ = mc(P, R, t, 0.3, n=4000, seed=5, refine=True)
    print("\nAveraging check (IPPE+LM), single tag, 0.6 m, 0.3 px: per-frame tilt sigma %.2f mrad, pos xy sigma %.2f mm" % (
        1e3 * np.sqrt(np.mean(T ** 2)), 1e3 * np.sqrt(np.mean(Pp[:, :2] ** 2))))
    for N in (1, 4, 10, 30):
        m = len(T) // N
        TT = T[:m * N].reshape(m, N, 2).mean(1)
        PP = Pp[:m * N].reshape(m, N, 3).mean(1)
        print(f"  mean of N={N:2d} frames: tilt {1e3 * np.sqrt(np.mean(TT ** 2)):.2f} mrad, pos xy {1e3 * np.sqrt(np.mean(PP[:, :2] ** 2)):.2f} mm "
              f"(1/sqrt(N) prediction {1e3 * np.sqrt(np.mean(T ** 2)) / math.sqrt(N):.2f} mrad)")


if __name__ == "__main__":
    main()


def differential_probe_noise(cam=(0.0, 0.0, 0.52), edge=EDGE_S if False else 0.1524, px=0.3, n=10, trials=300, seed=2):
    """Noise (mm, 1 sigma per axis) of a DIFFERENTIAL claw-displacement measurement between two n-frame still poses of an
    unmoved claw: (a) as the repo does it (camera position in M = -R_k^T t_k, each pose with its own noisy R_k, so the
    tilt lever does not cancel) and (b) with ONE fixed reference rotation, i.e. -R_ref^T (t_k - t_ref) (the lever is
    common-mode and cancels; only the precise lateral / depth noise of the marker origin remains)."""
    rng = np.random.default_rng(seed)
    R, t = camera_pose(cam, (0.03, -0.02))
    P = tag_corners(0, 0, edge)
    uv0 = project(P, R, t)
    a_err, b_err = [], []

    def still():
        Rs, ts = [], []
        for _ in range(n):
            uv = uv0 + rng.normal(0, px, uv0.shape)
            k, rvs, tvs, errs = cv2.solvePnPGeneric(P, uv, K, None, flags=cv2.SOLVEPNP_IPPE_SQUARE)
            c = []
            for rv, tv in zip(rvs, tvs):
                rv, tv = cv2.solvePnPRefineLM(P, uv, K, None, rv.copy(), tv.copy())
                pr = cv2.projectPoints(P, rv, tv, K, None)[0].reshape(-1, 2)
                c.append((float(np.sum((pr - uv) ** 2)), rv, tv))
            c.sort(key=lambda x: x[0])
            Rs.append(cv2.Rodrigues(c[0][1])[0])
            ts.append(c[0][2].ravel())
        Rm = cv2.Rodrigues(np.mean([cv2.Rodrigues(r_)[0].ravel() for r_ in Rs], axis=0))[0]
        return Rm, np.mean(ts, axis=0), np.mean([-r_.T @ t_ for r_, t_ in zip(Rs, ts)], axis=0)
    for _ in range(trials):
        R1, t1, c1 = still()
        R2, t2, c2 = still()
        a_err.append(c2 - c1)
        b_err.append(-R1.T @ (t2 - t1))
    a, b = np.array(a_err), np.array(b_err)
    return dict(repo_xy_mm=1e3 * float(np.sqrt(np.mean(a[:, :2] ** 2))), repo_z_mm=1e3 * float(np.sqrt(np.mean(a[:, 2] ** 2))),
                fixedR_xy_mm=1e3 * float(np.sqrt(np.mean(b[:, :2] ** 2))), fixedR_z_mm=1e3 * float(np.sqrt(np.mean(b[:, 2] ** 2))))


if __name__ == "__main__" and "--probe" in sys.argv:
    for n_ in (10, 40):
        print("differential probe noise, single tag 0.52 m, n =", n_, differential_probe_noise(n=n_, trials=250))
