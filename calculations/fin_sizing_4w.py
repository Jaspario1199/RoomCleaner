"""How thick and how long would the heat fin have to be to carry ALL of the motor's heat at 1.5 A (4.05 W, D37)?

Bound case: the fin alone dissipates 4.05 W (the motor's own path to the shell air is ignored, which is conservative and is
close to a sealed shell). Criterion: the motor flange (fin patch plus the paste contact) at or below the 60 C limit for
loaded PETG, in a 23 C room; a second criterion keeps a 5 K margin (55 C).

Model: the quasi-1D fin of calculations/simulation_loads.py (real width profile with the 7/8 in hole and the bolt holes,
the strip inside the shell, the heat entering over the contact patch), with the combined natural-convection + radiation h
converged for each geometry. Width stays 44 mm (the motor's width). Exposed length = height above the shell exit.
Ranges: isothermal flange (lower) to uniform flux into the patch (upper).

    PYTHONPATH=. /usr/bin/python3 -m calculations.fin_sizing_4w
"""
import math

from calculations import simulation_loads as S

Q = S.motor_heat(1.5)                         # 4.05 W
LIMITS = {"60 C limit": 60.0, "55 C (5 K margin)": 55.0}
K_6061 = S.ALLOYS["6061-T6"]
R_C = 1.0 / (10000.0 * S.contact_area_mm2() * 1e-6)   # thermal paste, K/W
DT_INSIDE = S.R_SA["vented"] * S.P_ELEC       # shell air over room with only the electronics heating it (fin carries the motor)
GAUGES = {                                     # common aluminium sheet and plate thicknesses
    "0.019 in (built)": 0.019, "0.032 in": 0.032, "0.040 in": 0.040, "0.050 in": 0.050, "1/16 in": 0.0625,
    "0.080 in": 0.080, "0.090 in": 0.090, "1/8 in (first drawing)": 0.125, "3/16 in": 0.1875, "1/4 in": 0.25,
}


def motor_temp(t_mm: float, L_mm: float, eps: float, isothermal: bool) -> tuple[float, float]:
    """Motor flange temperature (C) with all Q through a fin of thickness t and exposed length L; returns (T, h)."""
    h, _ = S.converge_h(K_6061, t_mm, eps, Q, L_mm)
    saved = S.FIN["h"]
    S.FIN["h"] = S.FIN["z_exit"] + L_mm
    try:
        fd = S.fin_quasi_1d(K_6061, t_mm, h, q_total=Q, dT_inside=DT_INSIDE, dz=0.5, isothermal=isothermal)
    finally:
        S.FIN["h"] = saved
    return S.T_AMB + fd["patch_avg"] + R_C * Q, h


def infinite_fin_limit(t_mm: float, eps: float, T_limit: float) -> float:
    """Most heat an infinitely long 44 mm fin can carry with its base at T_limit: q = w sqrt(2 h k t) theta_b."""
    theta = T_limit - S.T_AMB
    h = S.h_churchill_chu(theta / 3, 0.4)[2] + S.h_rad(eps, S.T_AMB + theta / 3, S.T_AMB)   # mean rise ~ theta/3
    return S.FIN["w"] * 1e-3 * math.sqrt(2 * h * K_6061 * t_mm * 1e-3) * theta


def min_length(t_mm: float, eps: float, T_limit: float, isothermal: bool, L_max: float = 600.0) -> float | None:
    for L in range(60, int(L_max) + 1, 5):
        if motor_temp(t_mm, float(L), eps, isothermal)[0] <= T_limit:
            return float(L)
    return None


def main():
    print(f"All {Q:.2f} W through one 44 mm wide 6061 fin, room {S.T_AMB} C, paste contact {R_C:.3f} K/W, shell air +{DT_INSIDE:.1f} K")
    print("\nMotor flange temperature for the built length (200 mm exposed), isothermal flange -> uniform flux:")
    for name, inch in GAUGES.items():
        t = inch * 25.4
        cells = []
        for fin, eps in S.EPS.items():
            lo, h = motor_temp(t, 200.0, eps, True)
            hi, _ = motor_temp(t, 200.0, eps, False)
            cells.append(f"{fin}: {lo:5.1f}-{hi:5.1f} C (h {h:4.1f})")
        mass = 2700 * 0.044 * 0.25 * t * 1e-3 * 1e3
        print(f"  {name:<24} t {t:5.2f} mm, {mass:5.0f} g: " + " | ".join(cells))
    for lim_name, T_lim in LIMITS.items():
        print(f"\nShortest exposed length (mm) so the motor stays at or below {lim_name}; '-' = not even at 600 mm."
              f" Ranges: isothermal flange / uniform flux. Infinite-fin limit = most heat any length can carry.")
        for name, inch in GAUGES.items():
            t = inch * 25.4
            cells = []
            for fin, eps in S.EPS.items():
                a = min_length(t, eps, T_lim, True)
                b = min_length(t, eps, T_lim, False)
                q_inf = infinite_fin_limit(t, eps, T_lim)
                fmt = lambda v: "-" if v is None else f"{v:.0f}"
                cells.append(f"{fin}: {fmt(a)}/{fmt(b)} mm (infinite fin {q_inf:4.2f} W)")
            print(f"  {name:<24} " + " | ".join(cells))


if __name__ == "__main__":
    main()
