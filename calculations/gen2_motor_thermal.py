"""
ROUGH motor-case temperature model for a winch station, vs driver current
and enclosure. Two-node lumped network:

  motor case (C_m) --R_ma--> shell interior: air + PETG housing (C_s) --R_sa--> room

- Motor coil heat P_m = I^2 * R_phase (A4988 keeps I_a^2 + I_b^2 = I_peak^2,
  so holding power is I_peak^2 * R_phase, all the time the claw is held).
- The PETG housing is a poor conductor (k ~ 0.2 W/m·K), so it is lumped with
  the interior air: it does NOT sink heat away, it rises toward the motor's
  temperature where they touch.
- Driver + step-down regulator + XIAO add P_e of heat into the same interior.

Every value is an ASSUMPTION to replace with a thermometer test.

    python -m calculations.gen2_motor_thermal -> docs/presentation/figures/motor_thermal.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R_PHASE = 1.8        # ohm per phase (measure: meter across one coil pair)
T_AMB = 30.0         # C near the ceiling
C_M = 130.0          # J/K, 0.28 kg motor
C_S = 600.0          # J/K, ~0.4 kg PETG shell/housing + air
P_E = 1.5            # W, A4988 + buck + XIAO inside the shell

# (label, R_ma motor->interior K/W, R_sa interior->room K/W, P_e W)
SCENARIOS = [
    ("open air, no shell", 12.0, 0.0, 0.0),
    ("vented shell (low inlet, high outlet)", 12.0, 1.0, P_E),
    ("sealed shell, stagnant air", 14.0, 3.5, P_E),
]
CURRENTS = [(1.0, "#6da7ec"), (1.25, "#2a78d6"), (1.5, "#184f95")]   # one-hue ramp
SCEN_COLORS = ["#86b6ef", "#2a78d6", "#104281"]
SAFE, PETG = 60.0, 80.0
INK, MUTED, GRID = "#2b2b29", "#6b6a63", "#e4e3dd"


def steady(i, r_ma, r_sa, p_e):
    p_m = i * i * R_PHASE
    t_s = T_AMB + (p_m + p_e) * r_sa
    return t_s + p_m * r_ma, t_s


def transient(i, r_ma, r_sa, p_e, minutes=180, dt=5.0):
    p_m = i * i * R_PHASE
    tm = ts = T_AMB
    out = [(0, tm, ts)]
    for k in range(1, int(minutes * 60 / dt) + 1):
        q_ms = (tm - ts) / r_ma
        q_sa = (ts - T_AMB) / r_sa if r_sa > 0 else None
        tm += dt * (p_m - q_ms) / C_M
        if r_sa > 0:
            ts += dt * (q_ms + p_e - q_sa) / C_S
        if k % 12 == 0:
            out.append((k * dt / 60, tm, ts))
    return out


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.axhline(SAFE, color=MUTED, lw=1.2, ls="--")
    ax.axhline(PETG, color=INK, lw=1.2, ls=":")
    ax.set_ylim(25, 125)


def main():
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 5.0), dpi=150)
    style(a); style(b)
    xs = [0.8 + k * 0.01 for k in range(81)]
    for (lbl, rma, rsa, pe), c in zip(SCENARIOS, SCEN_COLORS):
        a.plot(xs, [steady(x, rma, rsa, pe)[0] for x in xs], color=c, lw=2, label=lbl)
    for i, _ in CURRENTS:
        a.axvline(i, color=GRID, lw=1)
    a.text(1.595, SAFE - 1.5, "60 °C target for loaded printed parts", color=MUTED,
           fontsize=8.5, ha="right", va="top")
    a.text(0.81, PETG + 1.5, "~80 °C PETG softening", color=INK, fontsize=8.5)
    a.set_xlim(0.8, 1.6)
    a.set_xlabel("driver current per phase (A)", color=INK, fontsize=10)
    a.set_ylabel("motor case temperature, steady state (°C)", color=INK, fontsize=10)
    a.set_title("Steady state vs current, by enclosure", color=INK, fontsize=11, loc="left")
    leg = a.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, 1.0))
    for t in leg.get_texts():
        t.set_color(INK)

    lbl, rma, rsa, pe = SCENARIOS[2]
    for i, c in CURRENTS:
        tr = transient(i, rma, rsa, pe)
        b.plot([p[0] for p in tr], [p[1] for p in tr], color=c, lw=2,
               label=f"{i:.2f} A (Vref {0.8*i:.2f} V)")
        b.text(182, tr[-1][1], f" {tr[-1][1]:.0f} °C", color=INK, fontsize=8.5, va="center")
    b.set_xlim(0, 200)
    b.set_xlabel("minutes holding the claw (motors never switch off)", color=INK, fontsize=10)
    b.set_ylabel("motor case temperature (°C)", color=INK, fontsize=10)
    b.set_title("Warm-up in a sealed shell with stagnant air", color=INK, fontsize=11, loc="left")
    leg = b.legend(frameon=False, fontsize=9, loc="lower right")
    for t in leg.get_texts():
        t.set_color(INK)

    fig.suptitle("Winch motor heating — ROUGH MODEL, verify with a thermometer. "
                 "PETG touching the motor runs close to the motor's temperature.",
                 color=INK, fontsize=11.5, x=0.01, ha="left")
    fig.text(0.01, 0.005, f"Assumed: {R_PHASE} Ω/phase, room {T_AMB:.0f} °C, motor {C_M:.0f} J/K, "
             f"shell {C_S:.0f} J/K, electronics {P_E} W inside the shell. "
             "calculations/gen2_motor_thermal.py", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    out = "docs/presentation/figures/motor_thermal.png"
    fig.savefig(out, facecolor="white")
    for i, _ in CURRENTS:
        row = [f"{steady(i, r1, r2, pe)[0]:.0f}" for _, r1, r2, pe in SCENARIOS]
        t60 = next((p[0] for p in transient(i, *SCENARIOS[2][1:]) if p[1] >= SAFE), None)
        print(f"{i:.2f} A: open/vented/sealed = {'/'.join(row)} C; sealed crosses 60 C at "
              f"{'never' if t60 is None else f'{t60:.0f} min'}")
    print(out)


if __name__ == "__main__":
    main()
