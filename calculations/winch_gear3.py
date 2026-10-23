"""Winch station with the 3:1 spur reduction (D40): what it lifts, what it can pull before the motor slips, and whether each
part of the new drive train outlasts the motor.

Drive train: `cad/WINCH_GEAR3_SPEC.md`, parameters `cad/params.py` WG3_* (built by `cad/parts/winch_gear3.py`). Motor, spool
radii, running fraction, skip margin and the tension-per-weight factor are the repo's (simulation_loads, D37, Lift budget).
Rule from D39: every link >= 1.5 x the most the motor can pull before it slips.

Tags: [REPO] recorded in the repo, [ASSUMED] to be replaced by a measurement, [SRC] published value. Units N, mm, MPa, N.m.

    PYTHONPATH=. /usr/bin/python3 -m calculations.winch_gear3
Writes calculations/winch_gear3.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from cad import params as P
from calculations import simulation_loads as S
from calculations import lift_chain_weakest_link as WL

OUT_JSON = Path(__file__).with_suffix(".json")
G = 9.81
N_RATIO = P.WG3_RATIO                 # 3.0 [REPO WG3]
ETA = 0.90                            # printed spur stage efficiency, each direction [ASSUMED; the pull test measures the net]
K_TENSION = 1.101                     # worst tension per unit weight, +2 m/s2 included [REPO Lift budget]
NEEDED_KG = 1.50                      # claw 0.60 + jeans 0.90 [REPO Lift budget]
R_SENSE = S.R_SENSE                   # 0.100 ohm, red R100 A4988 [REPO D29/D30]
CURRENTS = (1.0, 1.5)                 # A: recommended (D40) and today's setting (D37)
Y_LEWIS = {20: 0.320, 60: 0.422}      # Lewis form factors, 20 deg full depth [SRC standard table]
PETG_ALLOW = 22.5 * WL.WARM["design"] # MPa: half of 45 MPa (review R5), warm x0.85
C0_687 = 600.0                        # N, static rating of a 687 (7 x 14 x 5) bearing [ASSUMED, check the datasheet]
SHAFT_SY = 350.0                      # MPa, Ø7 dowel (hardened dowels are much higher) [ASSUMED]
MOTOR_RADIAL_N = 28.0                 # N at 20 mm from the face, usual 17HS catalogue limit [SRC typical datasheet; check Jasper's motor]
SKIP_FULL_STEPS = 4                   # a stepper loses steps in whole electrical cycles
CPR = 4096                            # AS5600 [REPO]
LINE_SPEED = 0.050                    # m/s target [REPO REQUIREMENTS]


def at_current(i_amp: float) -> dict:
    hold = S.hold_torque(i_amp)                                      # motor holding torque, N.m (36 N.cm at 1.5 A basis)
    hold_hi = hold * WL.MOTOR_SENS                                   # 40 N.cm motor
    run_full = S.RUN_FRAC * hold * N_RATIO * ETA / S.R_FULL           # running pull at a full spool, N
    design = run_full / S.SKIP_SF
    cap = design / (K_TENSION * G)
    fuse_low = hold * WL.VECTOR_LOW * N_RATIO / S.R_EMPTY             # straight cable, no friction help
    fuse_up = hold_hi * N_RATIO / ETA / S.R_EMPTY * WL.FLEET_K       # back-driven through the stage, fleeted cable
    return dict(i=i_amp, vref=8 * i_amp * R_SENSE, hold=hold, hold_hi=hold_hi, run_full=run_full, run_core=run_full * S.R_FULL / S.R_EMPTY,
                design=design, capacity_kg=cap, margin=(cap - NEEDED_KG) / NEEDED_KG, fuse_low=fuse_low, fuse_up=fuse_up,
                need=WL.PASS_RATIO * fuse_up, heat=S.motor_heat(i_amp))


def gear_teeth(hold_hi: float) -> dict:
    """Lewis bending at the most torque the motor puts through the pinion (it slips above that)."""
    r_p = P.WG3_MODULE * P.WG3_Z_PINION / 2.0                        # 10 mm
    f_t = hold_hi / (r_p * 1e-3)
    f_r = f_t * math.tan(math.radians(P.WG3_PRESSURE_ANGLE_DEG))
    sig_gear = f_t / (P.WG3_FACE * P.WG3_MODULE * Y_LEWIS[P.WG3_Z_GEAR])
    torque_break = hold_hi * PETG_ALLOW / sig_gear                    # pinion torque at which the printed teeth reach the warm allowable
    return dict(f_t=f_t, f_r=f_r, sigma_gear=sig_gear, allow=PETG_ALLOW, sf=PETG_ALLOW / sig_gear, ratio=torque_break / hold_hi)


def pinion_setscrew(hold_hi: float) -> dict:
    """The purchased pinion's M3 set screw in a steel hub on the steel D-flat: seated to the steel rating, same friction model."""
    ss = WL.setscrew_joint()
    lo, hi = [WL.CUP_BITE * f * ss["lever_mm"] * 1e-3 for f in ss["f_seat_steel"]]
    return dict(torque_lo=lo, torque_hi=hi, ratio=lo / hold_hi)


def spool_shaft(c: dict) -> dict:
    """Ø7 shaft on two 687 bearings (centres y 2.5 and 46.5), simply supported. Loads at the motor's upper slip force: the cable
    (taken straight down, full magnitude) at the drum mid-plane, and the mesh force at the gear mid-face: radial toward the spool
    axis (also down, the pinion sits above) and tangential (horizontal). The shaft carries no torque (gear and drum are one part)."""
    y_a, y_b = P.WG3_BRG_NEAR_Y0 + P.WG3_BRG_W / 2, P.WG3_BRG_FAR_Y0 + P.WG3_BRG_W / 2
    span = y_b - y_a
    y_c = (P.WG3_Y_TEETH1 + P.WG3_Y_DRUM1) / 2                       # cable at the drum mid-plane
    y_m = (P.WG3_Y_TEETH0 + P.WG3_Y_TEETH1) / 2                      # mesh at the gear mid-face
    r_gear = P.WG3_MODULE * P.WG3_Z_GEAR / 2.0 * 1e-3
    f_t = c["hold_hi"] * N_RATIO / ETA / r_gear                      # back-driven: the gear pushes the pinion at the slip torque
    f_r = f_t * math.tan(math.radians(P.WG3_PRESSURE_ANGLE_DEG))
    loads = {"z": [(c["fuse_up"], y_c), (f_r, y_m)], "x": [(f_t, y_m)]}

    def reactions(plane):
        rb = sum(f * (y - y_a) for f, y in loads[plane]) / span
        return sum(f for f, _ in loads[plane]) - rb, rb

    def moment(plane, y):
        ra, _ = reactions(plane)
        return ra * (y - y_a) - sum(f * (y - yf) for f, yf in loads[plane] if yf < y)

    (az, bz), (ax, bx) = reactions("z"), reactions("x")
    r_near, r_far = math.hypot(az, ax), math.hypot(bz, bx)
    m = max(math.hypot(moment("z", y), moment("x", y)) for y in (y_m, y_c))
    d = P.WG3_SHAFT_D
    sigma = 32 * m / (math.pi * d ** 3)
    return dict(span=span, mesh_t=f_t, mesh_r=f_r, moment=m, sigma=sigma, ratio=SHAFT_SY / sigma, r_near=r_near, r_far=r_far,
                brg_ratio=C0_687 / max(r_near, r_far), seat_near_need=WL.PASS_RATIO * r_near, seat_far_need=WL.PASS_RATIO * r_far)


def motor_shaft_radial(c: dict) -> dict:
    """The pinion's mesh force on the motor shaft, at the pinion mid-face, against the usual 17HS catalogue limit. That limit is a
    bearing-life rating, not a strength: a short peak at the slip torque does no harm; long running near it would wear the front
    bearing. Normal running: the worst cable tension at the full spool, motor driving through the stage."""
    r_p = P.WG3_MODULE * P.WG3_Z_PINION / 2.0 * 1e-3
    k = 1 / math.cos(math.radians(P.WG3_PRESSURE_ANGLE_DEG))         # resultant of tangential and radial
    t_run = NEEDED_KG * K_TENSION * G * S.R_FULL / (N_RATIO * ETA)    # motor torque, N.m
    arm = (P.WG3_Y_TEETH0 + P.WG3_Y_TEETH1) / 2 - P.WG3_Y_MOTOR_FRONT
    return dict(arm_mm=arm, f_slip=c["hold_hi"] / r_p * k, f_run=t_run / r_p * k, catalogue=MOTOR_RADIAL_N, catalogue_arm=20.0)


def encoder() -> dict:
    skip_deg_spool = SKIP_FULL_STEPS * 360.0 / 200 / N_RATIO
    skip_counts = skip_deg_spool / 360 * CPR
    backlash_mm = 0.246                                              # at the pitch circle [REPO verification/winch_gear3_build_notes.md]
    r_gear = P.WG3_MODULE * P.WG3_Z_GEAR / 2.0
    backlash_counts = backlash_mm / r_gear / (2 * math.pi) * CPR
    return dict(skip_deg=skip_deg_spool, skip_counts=skip_counts, backlash_counts=backlash_counts, tol=20)


def speed() -> dict:
    steps_per_rev = 200 * N_RATIO
    rate_core = LINE_SPEED / (2 * math.pi * S.R_EMPTY) * steps_per_rev
    rate_full = LINE_SPEED / (2 * math.pi * S.R_FULL) * steps_per_rev
    rpm = rate_core / 200 * 60
    mm_per_step = 2 * math.pi * S.R_EMPTY * 1e3 / steps_per_rev
    return dict(full_steps_per_rev=steps_per_rev, rate_core=rate_core, rate_full=rate_full, motor_rpm=rpm, mm_per_step_core=mm_per_step)


def build() -> dict:
    cur = {f"{c:.1f} A": at_current(c) for c in CURRENTS}
    direct = dict(capacity_kg=1.56, fuse_up=WL.FUSE["upper"], heat=S.motor_heat(1.5))
    rec = cur["1.0 A"]
    links = [
        ("Printed 60T gear teeth (torque)", gear_teeth(rec["hold_hi"])["ratio"]),
        ("Pinion set screw, steel on steel (torque)", pinion_setscrew(rec["hold_hi"])["ratio"]),
        ("Spool shaft Ø7, bending", spool_shaft(rec)["ratio"]),
        ("687 bearings, static", spool_shaft(rec)["brg_ratio"]),
        ("Line knot", WL.line_links()["knot_lower"] / rec["fuse_up"]),
        ("Wall screws, one stud column", WL.build()["wall"]["per_case"][WL.build()["wall"]["worst"]]["f_design_one"] / rec["fuse_up"]),
    ]
    return dict(currents=cur, direct_drive=direct, teeth={k: gear_teeth(v["hold_hi"]) for k, v in cur.items()},
                setscrew={k: pinion_setscrew(v["hold_hi"]) for k, v in cur.items()},
                shaft={k: spool_shaft(v) for k, v in cur.items()}, motor_radial={k: motor_shaft_radial(v) for k, v in cur.items()},
                encoder=encoder(), speed=speed(),
                links_at_1A=[dict(link=n, ratio=r, verdict=WL.verdict(r)) for n, r in links], eta=ETA, ratio=N_RATIO)


def report(r: dict) -> None:
    print("WINCH WITH THE 3:1 SPUR REDUCTION (D40)")
    print(f"  ratio {r['ratio']:.1f}, stage efficiency {r['eta']} (assumed, each direction)")
    print(f"  direct drive today at 1.5 A: capacity {r['direct_drive']['capacity_kg']:.2f} kg, fuse upper {r['direct_drive']['fuse_up']:.0f} N, heat {r['direct_drive']['heat']:.2f} W")
    for k, c in r["currents"].items():
        print(f"  {k}: Vref {c['vref']:.2f} V; hold {c['hold']:.3f} N.m; running pull {c['run_full']:.1f} N full / {c['run_core']:.1f} N core; "
              f"design {c['design']:.1f} N; capacity {c['capacity_kg']:.2f} kg ({c['margin']*100:+.0f} % on 1.50 kg); "
              f"fuse {c['fuse_low']:.0f} to {c['fuse_up']:.0f} N; parts must hold {c['need']:.0f} N; heat {c['heat']:.2f} W")
    for k, t in r["teeth"].items():
        print(f"  teeth at {k}: F_t {t['f_t']:.1f} N, F_r {t['f_r']:.1f} N; printed 60T {t['sigma_gear']:.1f} MPa vs {t['allow']:.1f} warm (SF {t['sf']:.2f})")
    for k, s in r["setscrew"].items():
        print(f"  pinion set screw at {k}: {s['torque_lo']:.2f} to {s['torque_hi']:.2f} N.m, {s['ratio']:.2f} x the motor")
    for k, s in r["shaft"].items():
        print(f"  shaft at {k}: span {s['span']:.0f} mm, mesh {s['mesh_t']:.0f} N tangential + {s['mesh_r']:.0f} N radial, M {s['moment']:.0f} N.mm, "
              f"{s['sigma']:.0f} MPa ({s['ratio']:.1f} x yield); bearings {s['r_near']:.0f} / {s['r_far']:.0f} N ({s['brg_ratio']:.1f} x C0); "
              f"Jasper's seats must hold {s['seat_near_need']:.0f} N (tab) and {s['seat_far_need']:.0f} N (far cheek)")
    for k, m in r["motor_radial"].items():
        print(f"  motor shaft at {k}: pinion load {m['f_run']:.1f} N running, {m['f_slip']:.1f} N at the slip torque, {m['arm_mm']:.0f} mm from the face "
              f"(catalogue life limit about {m['catalogue']:.0f} N at {m['catalogue_arm']:.0f} mm)")
    e = r["encoder"]
    print(f"  encoder: one skip = {e['skip_deg']:.1f} deg at the spool = {e['skip_counts']:.0f} counts; backlash {e['backlash_counts']:.1f} counts; "
          f"tracking tolerance {e['tol']} counts")
    v = r["speed"]
    print(f"  speed: full_steps_per_rev {v['full_steps_per_rev']}; 50 mm/s needs {v['rate_core']:.0f} steps/s at the core ({v['rate_full']:.0f} full), "
          f"motor {v['motor_rpm']:.0f} rpm; {v['mm_per_step_core']:.3f} mm of cable per full step at the core")
    print("  links at 1.0 A (ratio to the motor's upper slip force; torque links by torque):")
    for x in r["links_at_1A"]:
        print(f"    {x['link']:<44} {x['ratio']:5.2f}  {x['verdict']}")


def main() -> None:
    r = build()
    report(r)
    OUT_JSON.write_text(json.dumps(r, indent=1, default=float))
    print(f"wrote {OUT_JSON.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
