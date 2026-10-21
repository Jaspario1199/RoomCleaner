"""How much of the room a bead-homed robot can reach (deck v2, slide "The problem: beads limit the motion").

A stopper bead cannot pass its outlet, so cable i can never be shorter than its length at the homing pose. If all
four beads are set with the claw at the room centre at height z_h, the claw can only reach points p with
||a_i - p|| >= ||a_i - p_home|| for every cable. This script grids the working volume (0.2 m wall margin,
z 0.3 .. 2.19 m, i.e. 0.4 m below the anchors) and reports the reachable fraction.

    /usr/bin/python3 calculations/bead_reach.py          # prints a table and writes calculations/bead_reach.json
Room 11 x 9 x 9 ft (3.3528 x 2.7432 x 2.7432 m); anchors 0.05 m in from the corners at 2.5932 m (config/robot.sim.json).
"""
import json
from pathlib import Path

import numpy as np

X, Y = 3.3528, 2.7432
A = np.array([[0.05, 0.05, 2.5932], [3.3028, 0.05, 2.5932], [3.3028, 2.6932, 2.5932], [0.05, 2.6932, 2.5932]])
MARGIN, Z_LO, Z_HI = 0.2, 0.3, 2.19
HEIGHTS = [0.3, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.19]


def reachable_fraction(z_home, n=(60, 50, 50)):
    xs = np.linspace(MARGIN, X - MARGIN, n[0]); ys = np.linspace(MARGIN, Y - MARGIN, n[1]); zs = np.linspace(Z_LO, Z_HI, n[2])
    P = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), -1).reshape(-1, 3)
    home = np.array([X / 2, Y / 2, z_home])
    L_home = np.linalg.norm(A - home, axis=1)
    ok = (np.linalg.norm(P[:, None, :] - A[None], axis=2) >= L_home - 1e-9).all(1)
    return float(ok.mean()), float(L_home[0])


if __name__ == "__main__":
    rows = []
    for z in HEIGHTS:
        f, L = reachable_fraction(z)
        rows.append({"homing_height_m": z, "cable_length_at_home_m": round(L, 3), "reachable_percent": round(100 * f, 1)})
        print(f"home at centre, {z:4.2f} m up: L_home {L:.3f} m, reachable {100 * f:5.1f} %")
    Path(__file__).with_suffix(".json").write_text(json.dumps(rows, indent=1))
