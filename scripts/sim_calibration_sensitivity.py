"""
Simulation 4 -- How precisely must you measure your ceiling?

The robot computes cable lengths from the anchor positions you type into
config.py. If your real ceiling corners differ from those numbers (measurement
error), the claw won't land where you asked. This sim answers: "if I measure my
anchors to +/- X cm, how far off will the claw be?"

Method:
  * The robot PLANS using the nominal anchors: L = cable_lengths(target).
  * Reality has anchors nudged by a random error of magnitude e.
  * Where does the claw actually end up? Forward kinematics with the REAL
    anchors: actual = position_from_lengths(L, real_anchors).
  * Position error = ‖actual - target‖. Average over many targets & random
    perturbations to get a robust curve of claw error vs. anchor error.

    python -m scripts.sim_calibration_sensitivity
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot

OUT = "output"


def sample_targets(cfg, n=40):
    rng = np.random.default_rng(0)
    pts = []
    while len(pts) < n:
        p = np.array([
            rng.uniform(0.5, cfg.room_width - 0.5),
            rng.uniform(0.5, cfg.room_depth - 0.5),
            rng.uniform(0.3, cfg.room_height - 0.8),
        ])
        pts.append(p)
    return pts


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = DEFAULT_CONFIG
    nominal = CableRobot(cfg)
    targets = sample_targets(cfg)

    # Anchor measurement errors to test (meters): 0.5 cm .. 5 cm.
    errors_cm = np.array([0.5, 1, 2, 3, 5])
    rng = np.random.default_rng(1)
    mean_err, max_err = [], []

    for e in errors_cm / 100.0:
        claw_errs = []
        for _ in range(12):                       # random realizations of the error
            real_anchors = cfg.anchors + rng.normal(0, e, size=cfg.anchors.shape)
            real = CableRobot(RobotConfigLike(cfg, real_anchors))
            for tgt in targets:
                L = nominal.cable_lengths(tgt)     # planned from NOMINAL anchors
                actual = real.position_from_lengths(L, guess=tgt)  # lands per REAL anchors
                claw_errs.append(np.linalg.norm(actual - tgt))
        mean_err.append(np.mean(claw_errs) * 100)  # cm
        max_err.append(np.max(claw_errs) * 100)

    plt.figure(figsize=(8, 5))
    plt.plot(errors_cm, mean_err, "o-", label="average claw error")
    plt.plot(errors_cm, max_err, "s--", label="worst-case claw error")
    plt.xlabel("anchor measurement error (cm, per corner)")
    plt.ylabel("resulting claw position error (cm)")
    plt.title("How ceiling-measurement precision maps to claw accuracy")
    plt.legend(); plt.grid(alpha=0.3)
    p = os.path.join(OUT, "calibration_sensitivity.png")
    plt.savefig(p, dpi=110, bbox_inches="tight"); plt.close()

    print(f"wrote {p}")
    for ecm, m, mx in zip(errors_cm, mean_err, max_err):
        print(f"  anchors +/-{ecm:>3.1f} cm -> claw off by ~{m:.1f} cm avg, {mx:.1f} cm worst")
    print("\nRule of thumb: claw error is roughly your anchor error. For ~2 cm "
          "grab accuracy, measure each ceiling corner to within ~2 cm.")


class RobotConfigLike:
    """Lightweight config wrapper that swaps in different anchor positions."""
    def __init__(self, base, anchors):
        self.__dict__.update(base.__dict__)
        self.anchors = anchors


if __name__ == "__main__":
    main()
