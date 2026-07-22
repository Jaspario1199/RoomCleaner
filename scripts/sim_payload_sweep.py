"""
Simulation 3 -- Maximum payload, anywhere in the room.

Answers the hard spec: "what's the heaviest thing this can lift, and where?"

Key physics shortcut: cable tension scales EXACTLY linearly with the load
(the balance equation  A·t = M·g·ẑ  is linear in the mass M). So we compute the
tension for a 1 kg reference load once at every point, call it tau(P), and then
the load on the busiest cable at total mass M is simply  M · tau(P).

A point stays liftable while  M · tau(P) <= motor_limit, so:
    max total mass at a point  =  motor_limit / tau(P)
    - the EASIEST point (room center) sets the absolute max payload
    - the HARDEST reachable point (a corner) sets the max for FULL floor coverage

    python -m scripts.sim_payload_sweep
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from roomcleaner.config import RobotConfig, EFFECTOR_ASSEMBLY
from roomcleaner.kinematics import CableRobot

OUT = "output"


def tau_field(robot, z=0.3, res=45):
    """Peak cable tension per 1 kg of load, at each reachable floor point."""
    cfg = robot.cfg
    xs = np.linspace(0, cfg.room_width, res)
    ys = np.linspace(0, cfg.room_depth, res)
    best = 0.0
    center_tau = None
    for y in ys:
        for x in xs:
            p = np.array([x, y, z])
            if not robot.is_reachable(p):
                continue
            t, ok = robot.solve_tensions(p)
            if ok:
                best = max(best, t.max())
    # tau at the room center (the easiest, symmetric point).
    tc, _ = robot.solve_tensions(np.array([cfg.room_width / 2, cfg.room_depth / 2, z]))
    return tc.max(), best   # (center tau, worst-point tau) per 1 kg


def main():
    os.makedirs(OUT, exist_ok=True)
    # Reference robot at exactly 1 kg total, so tensions == tau (per kg).
    robot = CableRobot(RobotConfig(mass=1.0))
    limit = robot.cfg.max_tension

    tau_center, tau_worst = tau_field(robot)
    # Max TOTAL mass = limit / tau; subtract the effector assembly to get payload.
    max_total_center = limit / tau_center
    max_total_full = limit / tau_worst
    max_payload_center = max_total_center - EFFECTOR_ASSEMBLY
    max_payload_full = max_total_full - EFFECTOR_ASSEMBLY

    payloads = np.linspace(0, max_total_center - EFFECTOR_ASSEMBLY + 1, 200)
    total = payloads + EFFECTOR_ASSEMBLY

    plt.figure(figsize=(8, 5))
    plt.plot(payloads, total * tau_center, label="at room center (easiest)")
    plt.plot(payloads, total * tau_worst, label="at a corner (hardest reachable)")
    plt.axhline(limit, color="k", ls="--", label=f"motor limit {limit:.0f} N")
    plt.axvline(max_payload_full, color="tab:orange", ls=":",
                label=f"full-coverage max {max_payload_full:.1f} kg ({max_payload_full*2.2:.1f} lb)")
    plt.axvline(max_payload_center, color="tab:blue", ls=":",
                label=f"center-only max {max_payload_center:.1f} kg ({max_payload_center*2.2:.1f} lb)")
    plt.xlabel("payload (kg)"); plt.ylabel("busiest-cable tension (N)")
    plt.title("Max payload: where the busiest cable hits the motor limit")
    plt.legend(fontsize=8); plt.grid(alpha=0.3)
    p = os.path.join(OUT, "payload_sweep.png")
    plt.savefig(p, dpi=110, bbox_inches="tight"); plt.close()

    print(f"wrote {p}")
    print(f"effector assembly: {EFFECTOR_ASSEMBLY} kg | motor limit {limit:.0f} N")
    print(f"MAX PAYLOAD (full floor coverage): {max_payload_full:.2f} kg "
          f"({max_payload_full*2.2:.1f} lb)")
    print(f"MAX PAYLOAD (center of room only):  {max_payload_center:.2f} kg "
          f"({max_payload_center*2.2:.1f} lb)")
    print("For reference: jeans ~0.9 kg, wet towel ~0.7 kg.")


if __name__ == "__main__":
    main()
