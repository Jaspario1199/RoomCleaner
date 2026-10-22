"""How thick and how long would the heat fin have to be to carry ALL of the motor's heat at 1.5 A (4.05 W, D37)?

Bound case: the fin alone dissipates 4.05 W (the motor's own path to the shell air is ignored). That is conservative, but it
is NOT a sealed shell: in a sealed shell the built fin carries only 44 to 50 % of the 4.05 W (printed at the end). The
all-through-the-fin case is an adiabatic-motor bound. Criterion: the motor flange (fin patch plus the paste contact) at or
below the 60 C limit for loaded PETG, in a 23 C room; a second criterion keeps a 5 K margin (55 C).

Model: the quasi-1D fin of calculations/simulation_loads.py (real width profile with the 7/8 in hole and the bolt holes,
the strip inside the shell, the heat entering over the contact patch), with the combined natural-convection + radiation h
converged for each geometry. Width stays 44 mm (the motor's width). Exposed length = height above the shell exit.
Ranges: isothermal flange (lower) to uniform flux into the patch (upper).

Limits of the model (independent check, verification/thermal_assembly_1p5a_check.md, 10/22):
- h depends on the exposed length L. converge_h uses L as the Churchill-Chu length, so h falls as L^-0.25 even though the
  added length is far from the hot base (painted: h 10.1 at 250 mm, 9.8 at 300, 8.7 at 600). Above about 250 mm the table is
  indicative only. T(L) is NOT monotonic above about 300 mm: it passes a minimum and rises again (0.090 in painted 59.1 C at
  300 mm, 60.1 at 600; 1/8 in painted 54.0 at 380 mm, 54.5 at 600). Lengths on the falling branch are right and slightly
  conservative. "0.090 in painted, 210 mm" is marginal, and "nothing up to 600 mm reaches 55 C" for bare 1/4 in is borderline
  (55.0 C at 600 mm).
- The infinite-fin limit is approximate: its h uses a mean rise of theta/3 and L = 0.4 m, and it comes out about 10 % low
  (6 to 15 % below the exact first integral with a local h(theta)). It is an indicator, not a strict upper bound.
- Edge and tip area are ignored (conservative, up to 14 % extra area at 1/4 in). The mass column is for the built 250 mm plate
  (200 mm exposed + 50 mm inside the shell); the longer bare fin is heavier (printed at the end).

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
BUILT_EXPOSED_MM = 200.0                       # built fin: 200 mm above the shell exit (+ 50 mm inside the shell = 250 mm plate)


def plate_mass_g(t_mm: float, L_exposed_mm: float) -> float:
    """Mass (g) of a 44 mm wide 6061 plate: exposed length plus the strip inside the shell; holes ignored (slightly conservative)."""
    return 2700 * 0.044 * (L_exposed_mm + S.FIN["z_exit"]) * 1e-3 * t_mm * 1e-3 * 1e3


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
    """Approximate heat (W) an infinitely long 44 mm fin can carry with its base at T_limit: q = w sqrt(2 h k t) theta_b.
    h is evaluated at a mean rise of theta_b/3 and L = 0.4 m, which makes the result about 10 % low."""
    theta = T_limit - S.T_AMB
    h = S.h_churchill_chu(theta / 3, 0.4)[2] + S.h_rad(eps, S.T_AMB + theta / 3, S.T_AMB)   # mean rise ~ theta/3
    return S.FIN["w"] * 1e-3 * math.sqrt(2 * h * K_6061 * t_mm * 1e-3) * theta


def min_length(t_mm: float, eps: float, T_limit: float, isothermal: bool, L_max: float = 600.0) -> float | None:
    for L in range(60, int(L_max) + 1, 5):
        if motor_temp(t_mm, float(L), eps, isothermal)[0] <= T_limit:
            return float(L)
    return None


def span(a: float, b: float, fmt: str = ".1f") -> str:
    lo, hi = sorted((a, b))
    if f"{lo:{fmt}}" == f"{hi:{fmt}}":
        return f"{lo:{fmt}}"
    return f"{lo:{fmt}}-{hi:{fmt}}"


def coupled_report() -> None:
    """The fin WITH the motor's own path to the shell air (simulation_loads.coupled_converged: motor -R_ma-> shell air -R_sa-> room,
    motor -fin-> room, fin h re-converged for the heat the fin actually carries). Painted, 200 mm exposed, 4.05 W."""
    print(f"\nCoupled with the shell (S.coupled_converged: fin AND the motor's own path to the shell air), painted, "
          f"{BUILT_EXPOSED_MM:.0f} mm exposed, {Q:.2f} W; ranges over isothermal flange / uniform flux:")
    for name, t in (("1/8 in (first drawing)", S.T_DESIGN), ("0.019 in (built, 0.483 mm)", S.T_AS_BUILT)):
        for mode in ("vented", "sealed"):
            iso = S.coupled_converged(K_6061, t, S.EPS["black paint"], R_C, mode, P=Q, isothermal=True)
            uni = S.coupled_converged(K_6061, t, S.EPS["black paint"], R_C, mode, P=Q)
            qa, qb = iso["r"]["q_fin"], uni["r"]["q_fin"]
            print(f"  {name:<26} {mode:<6}: motor {span(iso['r']['T_motor'], uni['r']['T_motor'])} C; "
                  f"fin carries {span(qa, qb, '.2f')} W ({span(100 * qa / Q, 100 * qb / Q, '.0f')} % of {Q:.2f} W); "
                  f"shell air {span(iso['r']['T_inside'], uni['r']['T_inside'])} C")


def main():
    print(f"All {Q:.2f} W through one 44 mm wide 6061 fin, room {S.T_AMB} C, paste contact {R_C:.3f} K/W, shell air +{DT_INSIDE:.1f} K")
    print(f"\nMotor flange temperature for the built length ({BUILT_EXPOSED_MM:.0f} mm exposed), isothermal flange -> uniform flux "
          f"(mass: {BUILT_EXPOSED_MM + S.FIN['z_exit']:.0f} mm plate, 200 exposed + 50 inside the shell):")
    for name, inch in GAUGES.items():
        t = inch * 25.4
        cells = []
        for fin, eps in S.EPS.items():
            lo, h = motor_temp(t, BUILT_EXPOSED_MM, eps, True)
            hi, _ = motor_temp(t, BUILT_EXPOSED_MM, eps, False)
            cells.append(f"{fin}: {lo:5.1f}-{hi:5.1f} C (h {h:4.1f})")
        mass = plate_mass_g(t, BUILT_EXPOSED_MM)
        print(f"  {name:<24} t {t:5.2f} mm, {mass:5.0f} g: " + " | ".join(cells))
    found = {}
    for lim_name, T_lim in LIMITS.items():
        print(f"\nShortest exposed length (mm) so the motor stays at or below {lim_name}; '-' = not even at 600 mm."
              f" Ranges: isothermal flange / uniform flux. Infinite fin = approximate limit on the heat any length can carry (about 10 % low)."
              f" Lengths above about 250 mm are indicative only: h falls with L and T(L) turns up above about 300 mm.")
        for name, inch in GAUGES.items():
            t = inch * 25.4
            cells = []
            for fin, eps in S.EPS.items():
                a = min_length(t, eps, T_lim, True)
                b = min_length(t, eps, T_lim, False)
                found[(lim_name, name, fin)] = (a, b)
                q_inf = infinite_fin_limit(t, eps, T_lim)
                fmt = lambda v: "-" if v is None else f"{v:.0f}"
                cells.append(f"{fin}: {fmt(a)}/{fmt(b)} mm (infinite fin about {q_inf:4.2f} W)")
            print(f"  {name:<24} " + " | ".join(cells))
    a, b = found[("60 C limit", "1/4 in", "bare Al")]
    if a is not None and b is not None:
        t = GAUGES["1/4 in"] * 25.4
        print(f"\nMass of the bare 1/4 in fin at {a:.0f} to {b:.0f} mm exposed: plate {a + S.FIN['z_exit']:.0f} to {b + S.FIN['z_exit']:.0f} mm long "
              f"(50 mm of it inside the shell), {plate_mass_g(t, a):.0f} to {plate_mass_g(t, b):.0f} g; "
              f"the mass column above is the built 250 mm plate ({plate_mass_g(t, BUILT_EXPOSED_MM):.0f} g at 1/4 in).")
    coupled_report()


if __name__ == "__main__":
    main()
