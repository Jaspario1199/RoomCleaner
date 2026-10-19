"""
ROUGH motor-case temperature model for the winch steppers vs driver current.

First-order lumped model:  T(t) = T_amb + P*R_th*(1 - exp(-t/tau)),
P = I^2 * R_phase (A4988 microstepping keeps I_a^2 + I_b^2 = I_peak^2 while
holding, so total coil power is I_peak^2 * R_phase).

Every input is an ASSUMPTION to be replaced by a thermometer test:
- R_phase 1.8 ohm (typical 42-38, 1.5 A NEMA 17; measure with the meter)
- R_th 10 K/W (motor bolted to metal / vented) to 16 K/W (bolted to printed
  PETG inside a closed shell). Bracketed by datasheet "rise <= 80 K at rated
  current" and typical 3D-printer stepper temperatures.
- thermal time constant 30 min (0.28 kg motor, C ~ 130 J/K)
- ambient 30 C (near a ceiling)

    python -m calculations.gen2_motor_thermal   -> docs/presentation/figures/motor_thermal.png
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R_PHASE, T_AMB, TAU_MIN = 1.8, 30.0, 30.0
RTH_GOOD, RTH_BAD = 10.0, 16.0
SAFE, PETG = 60.0, 80.0
CURRENTS = [(1.0, "#6da7ec"), (1.25, "#2a78d6"), (1.5, "#184f95")]  # one-hue ramp: magnitude
INK, MUTED, GRID = "#2b2b29", "#6b6a63", "#e4e3dd"


def ss(i, rth):
    return T_AMB + i * i * R_PHASE * rth


def main():
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8), dpi=150)
    for ax in (a, b):
        ax.spines[["top", "right"]].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(MUTED)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.axhline(SAFE, color=MUTED, lw=1.2, ls="--")
        ax.axhline(PETG, color=INK, lw=1.2, ls=":")
        ax.set_ylim(25, 100)

    # Left: steady state vs current, band between mounting conditions
    xs = [0.8 + k * 0.01 for k in range(81)]
    lo = [ss(x, RTH_GOOD) for x in xs]
    hi = [ss(x, RTH_BAD) for x in xs]
    a.fill_between(xs, lo, hi, color="#9ec5f4", alpha=0.6, lw=0)
    a.plot(xs, lo, color="#2a78d6", lw=2)
    a.plot(xs, hi, color="#184f95", lw=2)
    a.text(1.58, ss(1.6, RTH_GOOD) - 4, "vented / metal\nmount (10 K/W)", color=INK,
           fontsize=8.5, ha="right", va="top")
    a.text(1.40, ss(1.45, RTH_BAD) + 1, "inside printed shell\n(16 K/W)", color=INK,
           fontsize=8.5, ha="right", va="bottom")
    for i, _ in CURRENTS:
        a.axvline(i, color=GRID, lw=1)
    a.set_xlim(0.8, 1.6)
    a.set_xlabel("driver current per phase (A)", color=INK, fontsize=10)
    a.set_ylabel("motor case temperature, steady state (°C)", color=INK, fontsize=10)
    a.set_title("Steady-state temperature vs current", color=INK, fontsize=11, loc="left")

    # Right: warm-up holding the claw, enclosed shell (worst case)
    ts = list(range(0, 121))
    for i, c in CURRENTS:
        ys = [T_AMB + i * i * R_PHASE * RTH_BAD * (1 - math.exp(-t / TAU_MIN)) for t in ts]
        b.plot(ts, ys, color=c, lw=2, label=f"{i:.2f} A  (Vref {0.8*i:.2f} V)")
        b.text(121, ys[-1], f" {ys[-1]:.0f} °C", color=INK, fontsize=8.5, va="center")
    b.text(62, SAFE + 1, "60 °C target for printed mounts", color=MUTED, fontsize=8.5)
    b.text(62, PETG + 1, "~80 °C PETG softening", color=INK, fontsize=8.5)
    b.set_xlim(0, 135)
    b.set_xlabel("minutes holding the claw (motor never switches off)", color=INK, fontsize=10)
    b.set_ylabel("motor case temperature (°C)", color=INK, fontsize=10)
    b.set_title("Warm-up inside the printed shell (worst case)", color=INK, fontsize=11, loc="left")
    leg = b.legend(frameon=False, fontsize=9, loc="lower right")
    for t in leg.get_texts():
        t.set_color(INK)

    fig.suptitle("Winch motor heating vs driver current — ROUGH MODEL, verify with a thermometer",
                 color=INK, fontsize=12, x=0.01, ha="left")
    fig.text(0.01, 0.005, f"Assumed: phase resistance {R_PHASE} Ω, ambient {T_AMB:.0f} °C, "
             f"time constant {TAU_MIN:.0f} min, heat ∝ I². calculations/gen2_motor_thermal.py",
             color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    out = "docs/presentation/figures/motor_thermal.png"
    fig.savefig(out, facecolor="white")
    for i, _ in CURRENTS:
        print(f"{i:.2f} A: {i*i*R_PHASE:.2f} W, steady {ss(i, RTH_GOOD):.0f}-{ss(i, RTH_BAD):.0f} °C")
    print(out)


if __name__ == "__main__":
    main()
