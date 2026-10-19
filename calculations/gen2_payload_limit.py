"""
Maximum total suspended weight (claw + load) the four NEMA 17 winches can hold
anywhere in the workspace.

For each claw position the four cable tensions are statically indeterminate
(4 cables, 3 force equations). We take the BEST possible split: a linear
program minimises the largest tension subject to equilibrium and a 0.5 N
minimum (no slack). The worst position in the workspace then sets
W_max = F_line / (max tension per unit weight).

    python -m calculations.gen2_payload_limit
"""
from __future__ import annotations
import itertools
import numpy as np
from scipy.optimize import linprog

FT = 0.3048
ROOM_L, ROOM_W, ROOM_H = 11 * FT, 9 * FT, 9 * FT        # Outline v1
ANCHOR_DROP = 0.15         # m below ceiling, ASSUMED
WALL_MARGIN = 0.20         # m, roomcleaner/config.py WALL_MARGIN
CLAW_LOW = 0.15            # m, claw plate height at floor grab (config SAFE_MIN_Z)
T_MIN = 0.5                # N, config MIN_CABLE_TENSION
ACCEL = 2.0                # m/s^2, design dynamic (CLAUDE.md load case)
G = 9.81

# Motor: SIMAX 42-38, 36 N·cm holding at 1.5 A rated.
HOLD_RATED = 0.36          # N·m
I_RATED, I_SET = 1.5, 1.0  # A; Vref set for ~1.0 A on the bench
RUN_FRAC = 0.7             # ASSUMED pull-out / holding at low winch speed
R_EMPTY, R_FULL = 7.5e-3, 10.0e-3   # m, measured Spoolv3 core, full spool (calc)
SKIP_SF = 1.5              # margin so the stepper never silently loses steps

anchors = np.array([(0, 0), (ROOM_L, 0), (ROOM_L, ROOM_W), (0, ROOM_W)], float)
AZ = ROOM_H - ANCHOR_DROP


def worst_ratio(depth_min):
    """max over workspace of (max cable tension / supported weight), with
    vertical acceleration ACCEL included (multiplies weight by 1+a/g)."""
    xs = np.linspace(WALL_MARGIN, ROOM_L - WALL_MARGIN, 23)
    ys = np.linspace(WALL_MARGIN, ROOM_W - WALL_MARGIN, 19)
    zs = np.linspace(CLAW_LOW, AZ - depth_min, 25)
    worst, where = 0.0, None
    W = 1.0 * (1 + ACCEL / G)       # unit weight, dynamic
    for x, y, z in itertools.product(xs, ys, zs):
        u = np.column_stack([anchors[:, 0] - x, anchors[:, 1] - y,
                             np.full(4, AZ - z)])
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        # variables T1..T4, t ; minimise t
        c = [0, 0, 0, 0, 1]
        A_eq = np.hstack([u.T, np.zeros((3, 1))])
        b_eq = [0, 0, W]
        A_ub = np.hstack([np.eye(4), -np.ones((4, 1))])
        b_ub = np.zeros(4)
        bounds = [(T_MIN * 1e-3, None)] * 4 + [(0, None)]  # T_MIN scaled per N of W
        r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
        if r.status == 0 and r.x[4] > worst:
            worst, where = r.x[4], (x, y, z)
    return worst, where


def main():
    hold = HOLD_RATED * I_SET / I_RATED
    run = hold * RUN_FRAC
    print(f"motor torque: rated hold {HOLD_RATED} N·m @ {I_RATED} A -> "
          f"{hold:.3f} N·m @ {I_SET} A -> running ~{run:.3f} N·m")
    for lbl, r in (("empty spool", R_EMPTY), ("full spool", R_FULL)):
        print(f"line force at {lbl} (r={r*1e3:.1f} mm): {run/r:.1f} N, "
              f"usable /{SKIP_SF} = {run/r/SKIP_SF:.1f} N")
    f_use = run / R_FULL / SKIP_SF       # conservative: full spool + margin
    f_raw = run / R_FULL
    print(f"\nDesign line force used: {f_use:.1f} N (full spool, SF {SKIP_SF}); "
          f"no-margin: {f_raw:.1f} N")
    print(f"workspace: {WALL_MARGIN} m wall margin, claw from {CLAW_LOW} m "
          f"to the ceiling limit; {ACCEL} m/s² vertical accel included\n")
    print("ceiling limit below anchors | worst T/W | worst point (x,y,z m) | "
          "max total weight (with margin) | (no margin)")
    for d in (0.2, 0.3, 0.4, 0.6, 0.8, 1.0):
        k, p = worst_ratio(d)
        wm, wr = f_use / k, f_raw / k
        print(f"  {d:4.1f} m | {k:5.2f} | ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}) | "
              f"{wm:5.1f} N = {wm/G:4.2f} kg = {wm/G*2.2046:4.2f} lb | "
              f"{wr/G:4.2f} kg = {wr/G*2.2046:4.2f} lb")


if __name__ == "__main__":
    main()
