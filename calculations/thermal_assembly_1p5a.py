"""Answer sheet for SolidWorks Study C: the winch motor in the 10/21 station assembly at 1.5 A (D37).

Uses the coupled network and quasi-1D fin of calculations/simulation_loads.py (the model behind Study B,
docs/simulation/SW_THERMAL_HEAT_FIN.md) with the motor heat at 1.5 A instead of 1.0625 A, plus the inputs that only the
assembly study needs (CAD fin equivalent conductivity, convection coefficients, the shell exit height in the CAD).

    PYTHONPATH=. /usr/bin/python3 -m calculations.thermal_assembly_1p5a
"""
from calculations import simulation_loads as S

I_D37 = 1.5                      # A, D37 (Jasper, 10/22)
CAD_FIN_T = 2.0                  # mm, Heat_horn thickness in Assem_laundry_v3_step_1021 (y -2 to 0)
CAD_FIN_EXIT = 53.0              # mm above the fin's bottom edge where it leaves the shell top (z 34.6 in the 1021 frame)
CONTACT = {"thermal paste": 10000.0, "dry, flat": 3000.0, "dry, bowed sheet": 736.0}   # W/m^2K (Study B section 1.2)


def main():
    P = S.motor_heat(I_D37)
    A_c = S.contact_area_mm2()
    k = S.ALLOYS["6061-T6"]
    rc = 1.0 / (CONTACT["thermal paste"] * A_c * 1e-6)
    print(f"Motor heat at {I_D37} A, R_phase {S.R_PHASE} ohm: P = I^2 R = {P:.2f} W")
    print(f"CAD fin is {CAD_FIN_T} mm thick: equivalent conductivity k t_built / t_CAD = {k * S.T_AS_BUILT / CAD_FIN_T:.1f} W/m.K "
          f"(keeps k.t, so the fin conducts like the 0.483 mm 6061 sheet)")
    A_motor = 4 * 42.3 * 38.0 + 42.3 ** 2
    for mode in ("vented", "sealed"):
        print(f"motor free-face h ({mode}) = 1/(R_ma {S.R_MA[mode]} K/W x {A_motor:.0f} mm^2) = {1.0 / (S.R_MA[mode] * A_motor * 1e-6):.2f} W/m^2K")
    print("\nRanges: uniform heat flux into the fin patch -> isothermal flange (the steel block of the FEA is close to isothermal).")
    for fin, eps in S.EPS.items():
        for mode in ("vented", "sealed"):
            a = S.coupled_converged(k, S.T_AS_BUILT, eps, rc, mode, P=P)
            b = S.coupled_converged(k, S.T_AS_BUILT, eps, rc, mode, P=P, isothermal=True)
            print(f"  {fin:<11} {mode}: fin h {a['h']:.1f}; motor {a['r']['T_motor']:.1f} -> {b['r']['T_motor']:.1f} C; fin carries "
                  f"{a['r']['q_fin']:.2f} -> {b['r']['q_fin']:.2f} W; shell air {a['r']['T_inside']:.1f} C; rise 50 mm above the shell exit "
                  f"{a['fd']['at'](100.0):.1f} -> {b['fd']['at'](100.0):.1f} K; tip {a['fd']['tip']:.1f} -> {b['fd']['tip']:.1f} K")
    for mode in ("vented", "sealed"):
        r0 = S.coupled_motor(P, None, mode)
        print(f"  no fin, {mode}: motor {r0['T_motor']:.1f} C, shell air {r0['T_inside']:.1f} C")
    for i in (1.06, 1.35):
        p = S.motor_heat(i)
        a = S.coupled_converged(k, S.T_AS_BUILT, S.EPS["black paint"], rc, "vented", P=p)
        b = S.coupled_converged(k, S.T_AS_BUILT, S.EPS["black paint"], rc, "vented", P=p, isothermal=True)
        print(f"  for comparison, {i} A ({p:.2f} W), painted, vented: motor {a['r']['T_motor']:.1f} -> {b['r']['T_motor']:.1f} C")
    for L, w in ((200.0, 44.0), (210.24 - 34.6, 42.0)):
        f = S.fin_analytic(k, S.T_AS_BUILT, 9.2, L_mm=L, w_mm=w)
        print(f"  fin {w:.0f} mm wide, {L:.0f} mm exposed (painted h 9.2): eta {f['eta']:.3f}, R_fin {f['R']:.1f} K/W")


if __name__ == "__main__":
    main()
