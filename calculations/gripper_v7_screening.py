"""
Gripper v7 -- screening calculations (gear tooth strength, jaw grip force, tube-socket tension).

Method = review R5 (verification/design_review_gen2.md, calculations/gen2_screening.py):
  * MG996R stall 9.4 kg cm (4.8 V) and 11.0 kg cm (6.0 V)
  * 0.95 efficiency per printed spur mesh; torque split equally between the two jaws
    (jaw torque = tau * ratio * eta^2 / 2)
  * Lewis bending, PETG allowable 22.5 MPa (50 % of tensile, layer adhesion + fatigue)
  * 1 lb test weight at mu = 0.3 needs 7.4 N normal force per jaw
Inputs that are ASSUMED rather than measured are marked ASSUMED.  Every geometric number comes from
cad/params.py (GRIPV7_*) or the v6 inspection report.

    python -m calculations.gripper_v7_screening
"""

from __future__ import annotations

import math

import numpy as np

from cad import params as P
from cad.parts import gripper_v7_kin as K

G = 9.81
SERVO_STALL = {"4.8 V": K.SERVO_STALL_4V8, "6.0 V": K.SERVO_STALL_6V0}     # N m
ETA_MESH = K.ETA_MESH
PETG_ALLOW = 0.5 * 45e6               # Pa, ASSUMED 50 % of PETG tensile (as R5)
NEED_PER_JAW = 1.0 * 4.448 / (2 * 0.3)  # N, 1 lb at mu 0.3 (R5)
# Lewis form factors, 20 deg full depth (R5 values for 18/24/54; 36 interpolated 34: 0.371, 38: 0.384)
LEWIS_Y = {18: 0.309, 24: 0.337, 36: 0.3775, 54: 0.416}

# Effective face width of the pinion / 36T mesh: the 36T-layer top carries a GRIPV7_AXIAL_RELIEF annular relief (axial gap to the
# follower), so the pinion (16 mm) meshes over min(16, 16 - 0.3) = 15.7 mm.  The 24T pair is not relieved (20 mm).
FACE_MAIN_EFF = P.GRIPV7_FACE_MAIN - P.GRIPV7_AXIAL_RELIEF
# Lead decision (repair round 1): sync 24T one-jaw SF at the 6 V stall is 1.997 (< 2.0 by 0.15 %).  ACCEPTED as is: it sits at the
# precision of the assumed stall torque (11 kg cm) and of the Lewis form factor; the gear width is NOT changed.
ACCEPTED = {("6.0 V", "sync 24T, one jaw takes all"): "lead decision: SF 1.997 vs 2.0 accepted (within stall-torque precision)"}

# v6 reference numbers (verification/gripper_v6_inspection.md)
V6 = dict(module=1.5, z_pinion=18, z_big=54, z_sync=24, face_main=16.0, face_sync=20.0, ratio=3.0)


def lewis(ft: float, face_mm: float, module_mm: float, z: int) -> tuple[float, float]:
    """(stress Pa, safety factor) by the Lewis equation sigma = Ft / (b m Y)."""
    sigma = ft / (face_mm * 1e-3 * module_mm * 1e-3 * LEWIS_Y[z])
    return sigma, PETG_ALLOW / sigma


def tooth_table(ratio: float, z_big: int, module: float, face_main: float, face_sync: float,
                tag: str) -> list[dict]:
    rows = []
    d_p = P.GRIPV7_Z_PINION * module * 1e-3
    for vname, tau in SERVO_STALL.items():
        ft_pinion = 2 * tau / d_p
        tau_c = tau * ratio * ETA_MESH
        r24 = module * P.GRIPV7_Z_SYNC / 2 * 1e-3
        ft_sync_bal = (tau_c / 2) / r24
        ft_sync_one = tau_c / r24
        for name, ft, face, z in (
                ("pinion 18T", ft_pinion, face_main, 18),
                ("big gear %dT" % z_big, ft_pinion, face_main, z_big),
                ("sync 24T, jaws balanced", ft_sync_bal, face_sync, 24),
                ("sync 24T, one jaw takes all", ft_sync_one, face_sync, 24)):
            s, sf = lewis(ft, face, module, z)
            rows.append(dict(train=tag, servo=vname, gear=name, Ft_N=ft, stress_MPa=s / 1e6, SF=sf,
                             face_mm=face, accepted=ACCEPTED.get((vname, name), "") if tag == "v7" else ""))
    return rows


def force_table(gaps=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90)) -> dict:
    """Tip normal force per jaw (N) vs tip gap for v6 and v7, 4.8 V and 6.0 V stall."""
    out = {}
    for tag, fb, ratio in (("v6", K.v6_reference(), 3.0), ("v7", K.default(), P.GRIPV7_RATIO)):
        if tag == "v6":
            th_closed, th_open = -65.2, -14.2          # measured free range (arm-link contact at -35 deg rotation)
        else:
            th_closed, th_open = fb.theta_c, fb.theta_open
        ths = np.linspace(th_closed, th_open, 201)
        gp = np.array([fb.tip_gap(fb.pose(t)) for t in ths])
        res = {}
        for vname, tau in SERVO_STALL.items():
            f = np.array([fb.tip_force(t, tau, ratio) if 0.3 < i < 199.7 else np.nan
                          for i, t in enumerate(ths)])
            res[vname] = (gp, f)
        out[tag] = dict(theta=ths, gap=gp, force=res, closed=(th_closed, th_open),
                        gap_closed=float(gp[0]), gap_open=float(gp[-1]))
    return out


def interp_force(tab: dict, tag: str, vname: str, gap: float) -> float:
    gp, f = tab[tag]["force"][vname]
    ok = ~np.isnan(f)
    idx = np.argsort(gp[ok])
    return float(np.interp(gap, gp[ok][idx], f[ok][idx]))


def socket_tension_check(f_design: float = 100.0) -> dict:
    """M3 cross-bolt through the tube + printed saddle, tube in tension (design load ASSUMED 100 N:
    >= 4x (0.45 kg claw + 0.9 kg payload) x (9.81 + 2 m/s^2))."""
    d = 3.0e-3                       # M3 shank
    bolt_tau = 0.6 * 450e6           # A2-70 class bolt, shear strength ~0.6 x yield (ASSUMED)
    a_bolt = math.pi * d ** 2 / 4
    cap_bolt = 2 * a_bolt * bolt_tau                    # double shear (both tube walls)
    wall = (P.GRIPV7_TUBE_OD - P.GRIPV7_TUBE_ID) / 2 * 1e-3
    al_bearing = 1.5 * 240e6                            # 6061-T6 yield 240 MPa x 1.5 (ASSUMED alloy)
    cap_tube_bearing = 2 * d * wall * al_bearing
    e = (P.GRIPV7_XBOLT_Y_FROM_END - P.GRIPV7_XBOLT_HOLE_D / 2) * 1e-3
    cap_tube_tearout = 2 * 2 * e * wall * 0.6 * 240e6   # 2 walls x 2 shear planes
    # printed side: bearing on the Ø3.4 hole through upper plate (6) + saddle top (3.1) and the lower rib (10) + plate (6)
    t_print = (6.0 + 3.1 + 10.0 + 6.0) * 1e-3
    cap_petg_bearing = P.GRIPV7_XBOLT_HOLE_D * 1e-3 * t_print * PETG_ALLOW
    ahead = (P.GRIPV7_SADDLE_RIB_T * 2 + 2 - P.GRIPV7_XBOLT_HOLE_D / 2 - 0.0) * 1e-3   # rib 10 mm: 8.3 mm ahead
    cap_petg_shearout = 2 * ahead * t_print * 0.5 * PETG_ALLOW
    caps = dict(bolt_double_shear=cap_bolt, tube_bearing=cap_tube_bearing, tube_tearout=cap_tube_tearout,
                petg_bearing=cap_petg_bearing, petg_shearout=cap_petg_shearout)
    gov = min(caps, key=caps.get)
    return dict(design_load_N=f_design, capacities_N=caps, governing=gov, SF=caps[gov] / f_design)


def link_and_pivot_check() -> dict:
    """Link axial force from the jaw statics at the 6.0 V stall torque, and the checks it drives:
    link tension/buckling, frame-pivot stub bending (hangs 15 mm from the upper plate to the link mid-plane),
    shoulder-screw bending at the stub, clevis ear bearing.  Design load = 150 N (bounds 6 V stall up to a
    87 mm gap; the last 5 deg toward the open stop is a toggle, firmware must not stall there)."""
    from cad.parts import gripper_v7_jaws as JW
    fb = K.default()
    ratio = P.GRIPV7_RATIO
    rows = []
    for th in np.linspace(fb.theta_c + 0.5, fb.theta_open - 8.0, 40):
        p = fb.pose(th)
        f6 = fb.tip_force(th, K.SERVO_STALL_6V0, ratio)
        rows.append((fb.tip_gap(p), f6, fb.link_force_ratio(p) * f6))
    link_max_80 = max(r[2] for r in rows if r[0] <= 80.0)
    f_design = 150.0
    E_PETG = 2100.0                              # MPa, ASSUMED (printed PETG, XY)
    w, t, L = 2 * JW.LINK_END_R, JW.TONGUE_T, fb.L
    sigma_link = f_design / (t * (w - JW.HOLE_D))
    p_cr = math.pi ** 2 * E_PETG * (w * t ** 3 / 12.0) / L ** 2          # weaker axis (thickness 9)
    r_o = P.GRIPV7_P_STUB_R
    af = P.GRIPV7_NUT_POCKET_AF
    r_i = af / math.cos(math.radians(30)) / 2.0                          # hex pocket circumscribed radius
    i_stub = math.pi * (r_o ** 4 - r_i ** 4) / 4.0
    lever = P.GRIPV7_PLATE_GAP - (JW.TONGUE_Z0 + JW.TONGUE_T / 2.0)
    sigma_stub = f_design * lever * r_o / i_stub
    # shoulder (Ø4 steel, ASSUMED 12.9 alloy: 1000 MPa tensile): bending at the stub face, lever = link mid to the stub face
    lev_s = P.GRIPV7_P_STUB_Z0 - (JW.TONGUE_Z0 + JW.TONGUE_T / 2.0)
    sigma_sh = f_design * lev_s / (math.pi * 4.0 ** 3 / 32.0)
    bearing_ear = f_design / (4.0 * 2 * JW.EAR_T)                          # two 4.5 mm ears carry the shoulder
    return dict(rows=rows, link_force_max_gap_le_80_N=link_max_80, design_N=f_design,
                link_tension_MPa=sigma_link, link_buckling_Pcr_N=p_cr,
                stub_bending_MPa=sigma_stub, stub_SF=PETG_ALLOW / 1e6 / sigma_stub,
                shoulder_bending_MPa=sigma_sh, ear_bearing_MPa=bearing_ear,
                ear_SF=PETG_ALLOW / 1e6 / bearing_ear)


def main() -> dict:
    out = {}
    print("=== gear teeth (Lewis, PETG allowable %.1f MPa) ===" % (PETG_ALLOW / 1e6))
    rows = tooth_table(P.GRIPV7_RATIO, P.GRIPV7_Z_MAIN, P.GRIPV7_MODULE, FACE_MAIN_EFF,
                       P.GRIPV7_FACE_SYNC, "v7")
    rows6 = tooth_table(V6["ratio"], V6["z_big"], V6["module"], V6["face_main"], V6["face_sync"], "v6")
    for r in rows6 + rows:
        print("%s  %s  %-28s face %4.1f mm  Ft %6.1f N  %5.1f MPa  SF %.3f%s" % (
            r["train"], r["servo"], r["gear"], r["face_mm"], r["Ft_N"], r["stress_MPa"], r["SF"],
            ("   ACCEPTED: " + r["accepted"]) if r["accepted"] else ""))
    out["teeth"] = rows
    out["teeth_v6"] = rows6
    tab = force_table()
    out["forces"] = tab
    print("\n=== jaw tip force per jaw (N), R5 efficiency; need %.1f N ===" % NEED_PER_JAW)
    print("gap mm :", "  ".join("%5d" % g for g in (10, 20, 30, 40, 50, 60, 70, 80, 90)))
    for tag in ("v6", "v7"):
        for vname in SERVO_STALL:
            vals = [interp_force(tab, tag, vname, g) for g in (10, 20, 30, 40, 50, 60, 70, 80, 90)]
            print("%s %s:" % (tag, vname), "  ".join("%5.1f" % v for v in vals))
    for tag in ("v6", "v7"):
        print("%s tip gap closed %.1f  open %.1f mm  (crank %.1f .. %.1f deg, %.1f deg travel)" %
              (tag, tab[tag]["gap_closed"], tab[tag]["gap_open"], *tab[tag]["closed"],
               tab[tag]["closed"][1] - tab[tag]["closed"][0]))
    sk = socket_tension_check()
    out["socket"] = sk
    print("\n=== tube socket cross-bolt, tension %.0f N ===" % sk["design_load_N"])
    for k, v in sk["capacities_N"].items():
        print("  %-18s %8.0f N" % (k, v))
    print("  governing %s, SF %.1f" % (sk["governing"], sk["SF"]))
    lk = link_and_pivot_check()
    out["link"] = lk
    print("\n=== link / frame pivot (6.0 V stall) ===")
    print("  link axial force: max %.0f N for gaps <= 80 mm; design load %.0f N" % (lk["link_force_max_gap_le_80_N"], lk["design_N"]))
    print("  link tension %.1f MPa, Euler buckling %.0f N; P stub bending %.1f MPa (SF %.2f); "
          "shoulder bending %.0f MPa (steel); clevis ear bearing %.1f MPa (SF %.1f)" % (
              lk["link_tension_MPa"], lk["link_buckling_Pcr_N"], lk["stub_bending_MPa"], lk["stub_SF"],
              lk["shoulder_bending_MPa"], lk["ear_bearing_MPa"], lk["ear_SF"]))
    return out


if __name__ == "__main__":
    main()
