"""
Gen-2 (SolidWorks redesign, Oct 2026) screening calculations.

Purpose: first-principles checks for the design review in
verification/design_review_gen2.md and the SpaceX presentation. Every input
that is an ASSUMPTION (not measured from the user's CAD or parts) is marked
ASSUMED and listed in the report's "inputs to confirm" table. Re-run after
replacing assumptions with measured values:

    python -m calculations.gen2_screening
"""
from __future__ import annotations
import math

G = 9.81
FT = 0.3048
LBF = 4.448

# ---------------- room + anchors (from the user's Outline v1) -------------
ROOM_L, ROOM_W, ROOM_H = 11 * FT, 9 * FT, 9 * FT   # 11 x 9 x 9 ft
ANCHOR_DROP = 0.15          # m, ASSUMED: pulley exit below ceiling plane

# ---------------- line + spool --------------------------------------------
LINE_D = 0.5e-3             # m, ASSUMED effective diameter of 50 lb Dyneema
LINE_STORED = 20 * FT       # m, "target about 20 ft of line" (Outline v1)
CORE_R = 7.5e-3             # m, MEASURED: Spoolv3.STEP hub Ø15 (core the line winds on)
DRUM_W_MEASURED = 16e-3     # m, MEASURED: Spoolv3.STEP flanges at z=0-3 and 19-22 mm
FLANGE_R = 18e-3            # m, MEASURED: Spoolv3.STEP flange Ø36
PACKING = 0.85              # ASSUMED winding efficiency (gaps, cross-overs)

# ---------------- motor (SIMAX 42-38, from the shopping list) ------------
HOLD_TORQUE = 0.36          # N·m rated holding (36 N·cm)
RUN_FRAC = 0.5              # ASSUMED usable fraction at speed + 1 A derate
MOTOR_TORQUE = HOLD_TORQUE * RUN_FRAC

# ---------------- payload --------------------------------------------------
TEST_WEIGHT = 1.0 * LBF     # N, first integration target (Outline v1)
CLAW_MASS = 0.45            # kg, ASSUMED: gen-1 budget reused for gen-2 clamp

# ---------------- gripper gear train (tooth counts from the V5 file names) -
Z_PINION, Z_COMPOUND_BIG, Z_COMPOUND_SMALL, Z_FOLLOWER = 18, 54, 24, 24
SERVO_STALL = 9.4 * G / 100  # N·m, MG996R @4.8 V (9.4 kg·cm)
SERVO_STALL_6V = 11.0 * G / 100
ETA_MESH = 0.95              # ASSUMED per printed spur mesh
MODULE = 1.0e-3              # m, ASSUMED (not readable from SLDPRT names)
FACE_W = 6e-3                # m, ASSUMED face width
LEWIS_Y = {18: 0.309, 24: 0.337, 54: 0.416}   # 20° full-depth Lewis form factors
PETG_ALLOW = 0.5 * 45e6      # Pa, ASSUMED 50 % of PETG tensile (FDM layers, fatigue)
MU_CLOTH = 0.3               # ASSUMED cloth-on-printed-jaw friction
JAW_ARM = 0.06               # m, ASSUMED pivot-to-grip-point distance


def hr(t):
    print("\n" + t + "\n" + "-" * len(t))


def anchors():
    z = ROOM_H - ANCHOR_DROP
    return [(0, 0, z), (ROOM_L, 0, z), (ROOM_L, ROOM_W, z), (0, ROOM_W, z)]


def cable_lengths(p):
    return [math.dist(a, p) for a in anchors()]


def tensions_symmetric(p, weight):
    """Equal-share vertical support (lower bound on the max tension).
    Real 4-cable support is statically indeterminate; see review."""
    s = [(a[2] - p[2]) / math.dist(a, p) for a in anchors()]
    return weight / sum(s)


def main():
    W = TEST_WEIGHT + CLAW_MASS * G
    hr("1. Cable length range (sets how much line the spool must hold)")
    floor_pts = [(x, y, 0.05) for x in (0.3, ROOM_L / 2, ROOM_L - 0.3)
                 for y in (0.3, ROOM_W / 2, ROOM_W - 0.3)]
    ls = [l for p in floor_pts for l in cable_lengths(p)]
    lmax = max(ls)
    lmin = min(cable_lengths((ROOM_L / 2, ROOM_W / 2, ROOM_H - 0.6)))
    print(f"room {ROOM_L:.2f} x {ROOM_W:.2f} x {ROOM_H:.2f} m")
    print(f"longest cable (claw at far floor corner): {lmax:.2f} m = {lmax/FT:.1f} ft")
    print(f"shortest useful (claw 0.6 m below ceiling, centre): {lmin:.2f} m")
    print(f"line stored on spool target: {LINE_STORED:.2f} m -> margin "
          f"{LINE_STORED - lmax:+.2f} m over the longest cable")

    hr("2. Spool winding: layers, radius growth, force and calibration impact")
    for width_mm in (10, 16, 20):
        w = width_mm * 1e-3
        turns_per_layer = PACKING * w / LINE_D
        r, wound, layers = CORE_R, 0.0, 0
        while wound < LINE_STORED:
            wound += turns_per_layer * 2 * math.pi * (r + LINE_D / 2)
            r += LINE_D
            layers += 1
        f_core = MOTOR_TORQUE / CORE_R
        f_full = MOTOR_TORQUE / r
        dl = 2 * math.pi * (r - CORE_R)
        tag = "  <- Spoolv3 as drawn" if width_mm == 16 else ""
        print(f"width {width_mm:>2} mm: {layers:>2} layers, full radius "
              f"{r*1e3:5.1f} mm, line force {f_core:5.1f} N (core) -> {f_full:5.1f} N "
              f"(full), length/rev changes by {dl*1e3:5.1f} mm, flange "
              f"clearance {(FLANGE_R-r)*1e3:4.1f} mm{tag}")

    hr("3. Static cable tension, 4 cables, equal vertical share")
    print(f"supported weight: {TEST_WEIGHT:.2f} N test + {CLAW_MASS*G:.2f} N claw = {W:.2f} N")
    for depth in (0.15, 0.3, 0.6, 1.2, 2.4):
        p = (ROOM_L / 2, ROOM_W / 2, ROOM_H - ANCHOR_DROP - depth)
        t = tensions_symmetric(p, W)
        print(f"claw {depth:4.2f} m below anchors (centre): T = {t:6.1f} N per cable")
    corner = (0.4, 0.4, 0.3)
    print(f"near-corner floor pick (0.4,0.4,0.3) equal-share T = "
          f"{tensions_symmetric(corner, W):.1f} N (actual max is higher; "
          f"far cables carry little)")
    print(f"motor line force available (running, core): {MOTOR_TORQUE/CORE_R:.1f} N")

    hr("4. Gripper gear train (18T -> 54T | 24T -> 24T)")
    ratio = Z_COMPOUND_BIG / Z_PINION
    print(f"ratio {ratio:.1f}:1 ; 24T/24T stage = 1:1 direction reversal for the second jaw")
    print(f"servo 180 deg travel -> jaw shaft {180/ratio:.0f} deg")
    for label, tq in (("4.8 V stall", SERVO_STALL), ("6.0 V stall", SERVO_STALL_6V)):
        d = Z_PINION * MODULE
        ft = 2 * tq / d
        sigma = ft / (FACE_W * MODULE * LEWIS_Y[18])
        out = tq * ratio * ETA_MESH
        print(f"{label}: pinion tangential force {ft:6.1f} N, Lewis root stress "
              f"{sigma/1e6:5.1f} MPa vs allow {PETG_ALLOW/1e6:.1f} MPa "
              f"(SF {PETG_ALLOW/sigma:.2f}); compound-shaft torque {out:.2f} N·m")
    for m_mm, b_mm in ((1.0, 6), (1.5, 8), (2.0, 10)):
        d = Z_PINION * m_mm * 1e-3
        ft = 2 * SERVO_STALL_6V / d
        sigma = ft / (b_mm * 1e-3 * m_mm * 1e-3 * LEWIS_Y[18])
        print(f"  module {m_mm} mm, face {b_mm} mm: stress {sigma/1e6:5.1f} MPa "
              f"(SF {PETG_ALLOW/sigma:.2f} at 6 V stall)")
    need = (TEST_WEIGHT / (2 * MU_CLOTH))
    jaw_t = SERVO_STALL * ratio * ETA_MESH ** 2 / 2
    print(f"grip normal force needed per jaw for 1 lb at mu={MU_CLOTH}: {need:.1f} N")
    print(f"available per jaw at {JAW_ARM*1e3:.0f} mm arm (4.8 V stall, torque split): "
          f"{jaw_t / JAW_ARM:.1f} N")


if __name__ == "__main__":
    main()
