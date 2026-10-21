"""
Presentation fundamentals: every number a slide will show, recomputed from the
repository's authoritative inputs.

One function per topic (topic_01 .. topic_12).  Each function records
  * the equation,
  * every input with its source path (or ASSUMED),
  * the derived results (with units),
  * comparisons against numbers already claimed in the repository (AGREE / DISAGREE / STALE),
and the script prints a table plus per-topic detail and writes
calculations/presentation_fundamentals.json.

Nothing here is copied from a report: constants are read from the source files
(AST-parsed, no import of the CAD package) or from the JSON the studies wrote,
and every result is recomputed.  Rules of the file:
  * supplied   = a fact recorded in the repository (spec, measurement, decision);
  * ASSUMED    = a value nobody has measured (repository assumption or one made here);
  * derived    = computed in this file.

    /usr/bin/python3 calculations/presentation_fundamentals.py            # all topics
    /usr/bin/python3 calculations/presentation_fundamentals.py --fast     # skip the slow LP in topic 1
    /usr/bin/python3 calculations/presentation_fundamentals.py --only 3 7

Writes calculations/presentation_fundamentals.json (deterministic: fixed seeds, no timestamps).
"""
from __future__ import annotations

import argparse
import ast
import itertools
import json
import math
import operator
import os
import sys
import textwrap

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_OUT = os.path.join(HERE, "presentation_fundamentals.json")

LB_KG = 0.45359237          # exact definition of the pound-mass
IN_MM = 25.4                # exact


# =============================================================================
# source readers
# =============================================================================
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
_UN = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _ev(node, env):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.BinOp):
        return _BIN[type(node.op)](_ev(node.left, env), _ev(node.right, env))
    if isinstance(node, ast.UnaryOp):
        return _UN[type(node.op)](_ev(node.operand, env))
    if isinstance(node, ast.Tuple):
        return tuple(_ev(e, env) for e in node.elts)
    if isinstance(node, ast.List):
        return [_ev(e, env) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_ev(k, env): _ev(v, env) for k, v in zip(node.keys, node.values)}
    raise ValueError("unsupported expression")


class PyConsts:
    """Top-level numeric constants of a source file, evaluated without importing it."""

    def __init__(self, relpath: str):
        self.path = relpath
        self.env: dict = {}
        with open(os.path.join(REPO, relpath), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            tgt = node.targets[0]
            try:
                if isinstance(tgt, ast.Name):
                    self.env[tgt.id] = _ev(node.value, self.env)
                elif isinstance(tgt, ast.Tuple):
                    vals = _ev(node.value, self.env)
                    for n, v in zip(tgt.elts, vals):
                        self.env[n.id] = v
            except (ValueError, KeyError, TypeError, ZeroDivisionError):
                continue

    def get(self, name):
        return self.env[name]

    def src(self, name):
        return f"{self.path}:{name}"


_JSON_CACHE: dict = {}


def load_json(relpath: str):
    if relpath not in _JSON_CACHE:
        with open(os.path.join(REPO, relpath), encoding="utf-8") as fh:
            _JSON_CACHE[relpath] = json.load(fh)
    return _JSON_CACHE[relpath]


def _num(v):
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, (list, tuple)):
        return [_num(x) for x in v]
    if isinstance(v, dict):
        return {k: _num(x) for k, x in v.items()}
    if isinstance(v, float):
        if math.isinf(v):
            return "inf"
        return float(f"{v:.12g}")          # strip binary noise (17.849999999999998 -> 17.85)
    return v


# =============================================================================
# topic record
# =============================================================================
class Topic:
    def __init__(self, num, title, equation, evidence, decision, limits):
        self.num = num
        self.p = f"t{num:02d}_"
        self.d = dict(id=num, topic=title, equation=equation, evidence=evidence, decision=decision, limits=limits,
                      inputs=[], results=[], tables={}, comparisons=[], headline=[])
        self.flat: dict = {}

    # -- inputs --------------------------------------------------------------
    def _inp(self, key, label, value, unit, source, basis):
        self.d["inputs"].append(dict(key=self.p + key, name=label, value=_num(value), unit=unit, basis=basis,
                                     source=source))
        self.flat[self.p + key] = _num(value)
        return value

    def fact(self, key, label, value, unit, source):
        return self._inp(key, label, value, unit, source, "supplied")

    def assume(self, key, label, value, unit, source="ASSUMED"):
        if "ASSUMED" not in source:
            source = "ASSUMED; " + source
        return self._inp(key, label, value, unit, source, "assumed")

    def fact_py(self, key, label, C, name, unit, scale=1.0):
        return self.fact(key, label, C.get(name) * scale, unit, C.src(name))

    def assume_py(self, key, label, C, name, unit, scale=1.0):
        return self.assume(key, label, C.get(name) * scale, unit, C.src(name))

    # -- results -------------------------------------------------------------
    def res(self, key, label, value, unit, note="", headline=False):
        self.d["results"].append(dict(key=self.p + key, name=label, value=_num(value), unit=unit, note=note))
        self.flat[self.p + key] = _num(value)
        if headline:
            self.d["headline"].append(self.p + key)
        return value

    def table(self, name, columns, rows):
        self.d["tables"][name] = dict(columns=columns, rows=_num(rows))

    def compare(self, claim, repo_val, mine, unit, source, status, note=""):
        self.d["comparisons"].append(dict(claim=claim, repo=_num(repo_val), mine=_num(mine), unit=unit,
                                          source=source, status=status, note=note))


def within(a, b, tol):
    return "AGREE" if abs(a - b) <= tol else "DISAGREE"


def range_status(lo, hi, claim_lo, claim_hi, tol):
    """AGREE when my [lo, hi] lies within the claimed range widened by tol."""
    return "AGREE" if (lo >= claim_lo - tol and hi <= claim_hi + tol) else "DISAGREE"


# =============================================================================
# shared physics helpers
# =============================================================================
def motor_numbers(vref, rs, hold_rated, i_rated, run_frac, sf, r_core, r_full):
    """A4988: Vref = 8 I Rs.  Torque scales with phase current (below saturation); line force F = tau / r."""
    cur = vref / (8.0 * rs)
    hold = hold_rated * cur / i_rated
    run = hold * run_frac
    return dict(I=cur, hold=hold, run=run, F_core=run / r_core, F_full=run / r_full,
                F_use_core=run / r_core / sf, F_use_full=run / r_full / sf, F_snag=hold / r_core)


def wind(core_r, line_d, packing, width, total):
    """Layer winding exactly as calculations/gen2_screening.py: turns/layer = packing * width / d,
    each layer at mean radius r + d/2, radius grows by d per layer."""
    tpl = packing * width / line_d
    r, wound, layers = core_r, 0.0, 0
    while wound < total:
        wound += tpl * 2 * math.pi * (r + line_d / 2)
        r += line_d
        layers += 1
    return layers, r


def wind_hex(core_r, line_d, packing, width, total):
    """Same, but with hexagonal layer pitch 0.866 d (sensitivity only)."""
    tpl = packing * width / line_d
    r, wound, layers = core_r, 0.0, 0
    while wound < total:
        wound += tpl * 2 * math.pi * (r + 0.433 * line_d)
        r += 0.866 * line_d
        layers += 1
    return layers, r


def fin_eta(k, h, t, length):
    """Straight fin, both faces exposed, adiabatic tip: m = sqrt(2h/(k t)), eta = tanh(mL)/mL."""
    m = math.sqrt(2.0 * h / (k * t))
    ml = m * length
    return m, ml, math.tanh(ml) / ml


def network(p_m, p_e, r_ma, r_sa, r_f, t_amb):
    """Two-node network of calculations/gen2_motor_thermal.py plus an optional parallel fin path motor -> room."""
    inv = 0.0 if (r_f is None or math.isinf(r_f)) else 1.0 / r_f
    q_s = (p_m - r_sa * p_e * inv) / (1.0 + (r_sa + r_ma) * inv)
    th_s = r_sa * (q_s + p_e)
    th_m = th_s + r_ma * q_s
    q_f = th_m * inv
    return dict(T_m=t_amb + th_m, T_s=t_amb + th_s, Q_shell=q_s, Q_fin=q_f, share=q_f / p_m)


def lewis_sf(ft, face_mm, module_mm, y, allow):
    sigma = ft / (face_mm * 1e-3 * module_mm * 1e-3 * y)
    return sigma, allow / sigma


# =============================================================================
# 1. cable statics
# =============================================================================
def _lp_worst_ratio(pl, anchors, az, depth_min, nx=23, ny=19, nz=5):
    """max over the workspace of (max cable tension / supported static weight), best split by linear program,
    dynamic factor (1 + a/g) included.  Same formulation as calculations/gen2_payload_limit.py, coarser in z
    (the worst point is always at the highest allowed z)."""
    from scipy.optimize import linprog
    L, Wd = pl.get("ROOM_L"), pl.get("ROOM_W")
    wm, low, tmin = pl.get("WALL_MARGIN"), pl.get("CLAW_LOW"), pl.get("T_MIN")
    xs = np.linspace(wm, L - wm, nx)
    ys = np.linspace(wm, Wd - wm, ny)
    zs = np.linspace(low, az - depth_min, nz)
    w_dyn = 1.0 + pl.get("ACCEL") / 9.81
    worst, where = 0.0, None
    for x, y, z in itertools.product(xs, ys, zs):
        u = np.column_stack([anchors[:, 0] - x, anchors[:, 1] - y, np.full(4, az - z)])
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        r = linprog([0, 0, 0, 0, 1], A_ub=np.hstack([np.eye(4), -np.ones((4, 1))]), b_ub=np.zeros(4),
                    A_eq=np.hstack([u.T, np.zeros((3, 1))]), b_eq=[0, 0, w_dyn],
                    bounds=[(tmin * 1e-3, None)] * 4 + [(0, None)], method="highs")
        if r.status == 0 and r.x[4] > worst:
            worst, where = float(r.x[4]), (float(x), float(y), float(z))
    return worst, where


_LP_CACHE: dict = {}


def lp_k(depth):
    """Cached worst max-tension / weight for a ceiling limit `depth` below the anchors (all four cables, best split)."""
    key = round(depth, 4)
    if key not in _LP_CACHE:
        pl = PyConsts("calculations/gen2_payload_limit.py")
        anchors = np.array([(0, 0), (pl.get("ROOM_L"), 0), (pl.get("ROOM_L"), pl.get("ROOM_W")), (0, pl.get("ROOM_W"))], float)
        az = pl.get("ROOM_H") - pl.get("ANCHOR_DROP")
        _LP_CACHE[key] = _lp_worst_ratio(pl, anchors, az, depth)
    return _LP_CACHE[key]


def task_depth():
    """Depth below the anchors of the highest claw position the planner allows (motion.task_max_height_m)."""
    pl = PyConsts("calculations/gen2_payload_limit.py")
    cfg = load_json("config/robot.sim.json")
    return pl.get("ROOM_H") - pl.get("ANCHOR_DROP") - cfg["motion"]["task_max_height_m"]


def topic_01(opts):
    t = Topic(1, "Cable statics: tension vs elevation angle",
              "T = W / (4 sin phi);  sin phi = d / sqrt(d^2 + Dh^2);  W_dyn = W (1 + a/g)",
              "CALCULATED",
              "A ceiling margin (0.4 m below the anchors) and a software ceiling: near the anchors the cables are almost "
              "horizontal, tension blows up as 1/sin(phi), and the motor cannot supply it.",
              "Point claw, massless straight cables, equal vertical share (the system is statically indeterminate, the "
              "best split is found by LP); ignores the 84 mm attachment spread, sag, pulley friction and swing.")
    pl = PyConsts("calculations/gen2_payload_limit.py")
    sc = PyConsts("calculations/gen2_screening.py")
    g = t.fact_py("g", "gravity", sc, "G", "m/s^2")
    room_l = t.fact_py("room_l", "room length (11 ft)", pl, "ROOM_L", "m")
    room_w = t.fact_py("room_w", "room width (9 ft)", pl, "ROOM_W", "m")
    room_h = t.fact_py("room_h", "room height (9 ft)", pl, "ROOM_H", "m")
    drop = t.assume_py("anchor_drop", "anchor drop below ceiling", pl, "ANCHOR_DROP", "m")
    accel = t.fact_py("accel", "design vertical acceleration", pl, "ACCEL", "m/s^2")
    m_claw = t.assume("m_claw", "claw mass (budget, unweighed)", 0.45, "kg", "REQUIREMENTS.md R7; calculations/gen2_screening.py:CLAW_MASS")
    m_test = t.fact("m_test", "test load, 1 lb", LB_KG, "kg", "calculations/gen2_screening.py:TEST_WEIGHT (Outline v1, first target)")

    dh = math.hypot(room_l / 2, room_w / 2)
    w_static = (m_test + m_claw) * g
    w_dyn = w_static * (1 + accel / g)
    t.res("dh", "horizontal distance, room centre to each anchor", dh, "m")
    t.res("w", "supported weight W (1 lb + 0.45 kg)", w_static, "N")
    t.res("w_dyn", "W x (1 + a/g)", w_dyn, "N")

    rows = []
    claims = {0.15: 32.1, 0.30: 16.1, 0.60: 8.3, 1.20: 4.6}
    for d, claim in claims.items():
        s = d / math.hypot(d, dh)
        phi = math.degrees(math.asin(s))
        tt = w_static / (4 * s)
        t.res(f"phi_{d:.2f}", f"elevation angle at {d} m", phi, "deg")
        t.res(f"T_{d:.2f}", f"tension per cable at {d} m below anchors (static)", tt, "N", headline=True)
        t.res(f"Tdyn_{d:.2f}", f"tension per cable at {d} m, +2 m/s^2", tt * (1 + accel / g), "N")
        rows.append([d, phi, tt, tt * (1 + accel / g), claim])
        t.compare(f"equal-share tension at {d} m", claim, tt, "N", "verification/design_review_gen2.md R6",
                  within(tt, claim, 0.06))
    t.table("equal_share", ["depth_m", "phi_deg", "T_static_N", "T_dynamic_N", "repo_R6_N"], rows)

    # motor side (topic 2 convention, 1.0625 A)
    hold_rated, i_rated = pl.get("HOLD_RATED"), pl.get("I_RATED")
    run_frac, sf = pl.get("RUN_FRAC"), pl.get("SKIP_SF")
    r_full = pl.get("R_FULL")
    mn = motor_numbers(0.85, 0.100, hold_rated, i_rated, run_frac, sf, pl.get("R_EMPTY"), r_full)
    t.fact("vref", "A4988 Vref at the carrier maximum (measured)", 0.85, "V", "DECISIONS.md D30")
    t.res("f_full", "line force available, full spool (running)", mn["F_full"], "N")
    t.res("f_use", "line force used for design (full spool / 1.5)", mn["F_use_full"], "N")
    for lbl, f in (("no_margin", mn["F_full"]), ("sf15", mn["F_use_full"])):
        s_req = w_dyn / (4 * f)
        d_min = dh * math.tan(math.asin(s_req))
        t.res(f"dmin_{lbl}", f"shallowest centred depth the motor can hold ({lbl})", d_min, "m",
              headline=(lbl == "sf15"))

    t.fact("ceil_margin", "ceiling margin used by the planner", 0.4, "m", "config/robot.sim.json motion.ceiling_margin_m; DECISIONS.md D26")
    d_task = task_depth()
    t.fact("task_h", "highest task height allowed", 1.6, "m", "config/robot.sim.json motion.task_max_height_m")
    t.res("d_task", "depth below the anchors of the highest task pose", d_task, "m")
    # static centred pose: where does R6's 'cannot be lifted above ~0.3 m' come from?
    d_static = dh * math.tan(math.asin(w_static / (4 * mn["F_full"])))
    t.res("dmin_static_nomargin", "shallowest centred depth, static weight, no margin, full spool", d_static, "m")
    t.compare("R6: 'above ~0.3 m below the anchors the claw cannot be lifted'", 0.3,
              f"{d_static:.2f} (static) .. {t.flat['t01_dmin_no_margin']:.2f} (+2 m/s^2)", "m",
              "verification/design_review_gen2.md R6", "AGREE",
              "Centred pose, full spool, no margin; with the 1.5 margin the shallowest centred depth is 0.50 m.")
    if not opts.fast:
        rows = []
        g_lb = 2.2046226
        for depth, repo_lb in ((0.4, 1.04), (0.6, 1.51), (1.0, 2.30), (d_task, None)):
            k, where = lp_k(depth)
            f1 = motor_numbers(0.80, 0.100, hold_rated, i_rated, run_frac, sf, pl.get("R_EMPTY"), r_full)["F_use_full"]
            w1 = f1 / k / g * g_lb
            w2 = mn["F_use_full"] / k / g * g_lb
            rows.append([depth, k, where[0], where[1], where[2], w1, w2])
            tag = "task" if repo_lb is None else str(depth)
            t.res(f"lp_k_{tag}", f"worst max-tension / weight, ceiling limit {depth:.3f} m", k, "-")
            t.res(f"lp_lb_{tag}", f"max total weight at 1.0625 A, SF 1.5, ceiling {depth:.3f} m", w2, "lb", headline=(depth in (0.4, d_task)))
            t.res(f"lp_kg_{tag}", f"same, in kg", w2 / g_lb, "kg")
            if repo_lb is not None:
                t.compare(f"best-split total weight at 1.0 A, ceiling {depth} m", repo_lb, w1, "lb",
                          "verification/design_review_gen2.md R10", within(w1, repo_lb, 0.03))
        t.table("lp", ["ceiling_limit_m", "worst_T_over_W", "x_m", "y_m", "z_m", "lb_at_1.0A", "lb_at_1.0625A"], rows)
        k_task = lp_k(d_task)[0]
        need = m_claw + 0.9
        t.res("need_kg", "claw (0.45) + 0.9 kg jeans", need, "kg")
        t.res("need_ratio", "required / available at the task ceiling (Ø15 core, SF 1.5)", need / (mn["F_use_full"] / k_task / g), "x", headline=True)
        # D29 claim: 'claw mass budget rises to ~750 g with a 1 lb payload at the 0.4 m ceiling margin' (1.35 A)
        k04 = lp_k(0.4)[0]
        d29 = motor_numbers(1.08, 0.100, hold_rated, i_rated, run_frac, sf, pl.get("R_EMPTY"), r_full)
        d29c = motor_numbers(1.08, 0.100, hold_rated, i_rated, run_frac, sf, pl.get("R_EMPTY"), pl.get("R_EMPTY"))
        claw_design = d29["F_use_full"] / k04 / g - m_test
        claw_nosf = d29["F_full"] / k04 / g - m_test
        claw_core = d29c["F_full"] / k04 / g - m_test
        t.res("d29_claw_design", "claw mass for 1 lb payload at 1.35 A, ceiling 0.4 m: full spool, SF 1.5", claw_design * 1e3, "g")
        t.res("d29_claw_nosf", "same, no safety factor", claw_nosf * 1e3, "g")
        t.res("d29_claw_core", "same, core radius, no safety factor", claw_core * 1e3, "g")
        claw_hold = d29c["hold"] / pl.get("R_EMPTY") / sf / k04 / g - m_test
        t.res("d29_claw_hold", "same, using the HOLD torque at the empty-spool radius / 1.5 as the line force", claw_hold * 1e3, "g",
              "this is how ~750 g (D29) and ~650 g at 1.25 A (DESIGN_STATE) can be reached")
        t.compare("D29: 'claw mass budget rises to ~750 g with a 1 lb payload at the 0.4 m ceiling margin' (1.35 A)", 750, f"{claw_design*1e3:.0f} / {claw_nosf*1e3:.0f} / {claw_core*1e3:.0f}", "g",
                  "DECISIONS.md D29 (superseded by D30)", "DISAGREE",
                  "Not reproducible with the repository's own capacity method (full spool, running torque): 1.5 margin gives about 180 g, no margin 500 g, "
                  f"core radius and no margin 820 g.  The ~750 g appears only if the HOLD torque at the empty-spool radius (43 N) is used as the line force "
                  f"with the 1.5 margin ({claw_hold*1e3:.0f} g).  D30 withdrew 1.35 A; do not quote the 750 g.")
    t.compare("claw at the room centre needs the ceiling margin", 0.4, t.flat["t01_dmin_sf15"], "m",
              "config/robot.sim.json motion.ceiling_margin_m",
              "CONTEXT", "Centred pose with 1 lb + 0.45 kg needs about 0.5 m at SF 1.5 (0.33 m with no margin); poses "
              "near a wall are worse (LP), so 0.4 m is a floor, not a comfortable margin.")
    return t


# =============================================================================
# 2. motor torque -> line tension, current cap, spool core
# =============================================================================
def topic_02(opts):
    t = Topic(2, "Motor torque to line tension, current cap, spool core",
              "I = Vref / (8 Rs);  tau_hold = tau_rated I / I_rated;  tau_run = 0.7 tau_hold;  F = tau / r",
              "CALCULATED (inputs: MEASURED Vref and spool; PLANNED pull test for the 0.7 running fraction)",
              "Winch current is capped by the driver board (about 1.06 A), so lift capacity has to come from a smaller "
              "spool core, a lighter claw, or a larger ceiling margin; a Ø10 mm core is the largest that still lifts a "
              "0.45 kg claw plus 0.9 kg jeans with a 1.5 margin at the highest task pose.",
              "Torque is taken linear in current with a flat 0.7 running fraction (no speed dependence); the 85 % "
              "packing rule ignores cross-overs; line bend life is a rule of thumb, not a test.")
    pl = PyConsts("calculations/gen2_payload_limit.py")
    sc = PyConsts("calculations/gen2_screening.py")
    cfg = load_json("config/robot.sim.json")
    sp = cfg["stations"][0]["spool"]
    dr = cfg["stations"][0]["drive"]
    mot = cfg["motion"]
    vref = t.fact("vref", "A4988 Vref at the carrier maximum", 0.85, "V", "DECISIONS.md D30 (measured on the red R100 carrier)")
    vref_old = t.fact("vref_old", "earlier measurement of the same cap", 0.79, "V", "DESIGN_STATE.md (10/21 measured entry)")
    rs = t.fact("rs", "sense resistor, marking R100", 0.100, "ohm", "DECISIONS.md D29 (R100 -> 1.08 V for 1.35 A)")
    hold_rated = t.fact_py("hold", "rated holding torque, SIMAX 42-38", pl, "HOLD_RATED", "N m")
    i_rated = t.fact_py("i_rated", "rated phase current", pl, "I_RATED", "A")
    run_frac = t.assume_py("run_frac", "running / holding torque", pl, "RUN_FRAC", "-")
    run_frac_old = t.assume_py("run_frac_old", "running fraction in the R4/R6 tables", sc, "RUN_FRAC", "-")
    sf = t.assume_py("sf", "skip margin on line force", pl, "SKIP_SF", "-")
    r_core = t.fact("r_core", "spool core radius (Spoolv3, measured)", sp["core_radius_m"], "m", "config/robot.sim.json stations[0].spool; verification/design_review_gen2.md R4")
    line_d = t.assume("line_d", "line effective diameter", sp["line_diameter_m"], "m", "config/robot.sim.json stations[0].spool; calculations/gen2_screening.py:LINE_D")
    packing = t.assume("packing", "winding packing", sp["packing"], "-", "config/robot.sim.json stations[0].spool; calculations/gen2_screening.py:PACKING")
    width = t.fact("width", "drum width (Spoolv3, measured)", sp["drum_width_m"], "m", "config/robot.sim.json stations[0].spool; design_review_gen2.md R4")
    flange_r = t.fact("flange_r", "flange radius (measured)", sp["flange_radius_m"], "m", "config/robot.sim.json stations[0].spool")
    total = t.fact("line_total", "stored line, 20 ft", sp["line_total_m"], "m", "config/robot.sim.json stations[0].spool")
    usteps = dr["full_steps_per_rev"] * dr["microsteps"]
    t.fact("usteps", "microsteps per rev (200 x 16)", usteps, "1/rev", "config/robot.sim.json stations[0].drive")
    f_cap = t.assume("f_cap", "step-rate cap in the simulation profile (hardware example: null, 1 microstep)", dr["max_step_rate_hz"], "Hz", "config/robot.sim.json stations[0].drive.max_step_rate_hz; config/robot.example.json has null")
    v_max = t.fact("v_max", "max cable speed", mot["max_cable_speed_m_s"], "m/s", "config/robot.sim.json motion.max_cable_speed_m_s")
    enc = t.fact("enc", "encoder counts per spool rev", cfg["stations"][0]["encoder"]["counts_per_rev"], "1/rev", "config/robot.sim.json stations[0].encoder")
    bore_d = t.fact("bore_d", "bore diameter as printed design (v3)", 5.45, "mm", "verification/design_review_gen2.md R4")
    flat = t.fact("flat", "D-flat depth", 0.50, "mm", "verification/design_review_gen2.md R4; cad/params.py:MOTOR_SHAFT_FLAT")
    shaft_d = t.fact("shaft_d", "NEMA 17 shaft", 5.0, "mm", "cad/params.py:MOTOR_SHAFT_DIA")
    tie_d = t.fact("tie_d", "tie-off hole diameter", 1.4, "mm", "verification/design_review_gen2.md R4 (offset 6 mm from the axis)")
    tie_wall = t.fact("tie_wall", "outer wall left by the drawn tie-off hole", 7.5 - 6.0 - 0.7, "mm", "derived from R4: core R7.5, hole at 6 mm, R0.7")
    m3 = t.fact("m3", "M3 thread-forming engagement wanted (1 x D)", 3.0, "mm", "ASSUMED rule of thumb for a thread-forming screw in plastic")
    bend_min = t.assume("bend_min", "line bend ratio, core diameter / line diameter, preferred minimum", 20.0, "-", "ASSUMED rule of thumb for braided HMPE (8-10 absolute minimum)")

    # --- headline: current and tension --------------------------------------
    layers15, r_full = wind(r_core, line_d, packing, width, total)
    mn = motor_numbers(vref, rs, hold_rated, i_rated, run_frac, sf, r_core, r_full)
    mn_old = motor_numbers(vref_old, rs, hold_rated, i_rated, run_frac, sf, r_core, r_full)
    t.res("current", "driver current at Vref 0.85 V", mn["I"], "A", headline=True)
    t.res("current_old", "driver current at Vref 0.79 V", mn_old["I"], "A")
    t.res("hold", "holding torque at that current", mn["hold"], "N m")
    t.res("run", "running torque (x 0.7)", mn["run"], "N m")
    t.res("r_full", "full-spool radius, Ø15 core (recomputed winding)", r_full * 1e3, "mm")
    t.res("layers", "layers on the Ø15 core", layers15, "-")
    t.res("f_core", "line force, core radius 7.5 mm (running)", mn["F_core"], "N", headline=True)
    t.res("f_full", "line force, full spool (running)", mn["F_full"], "N", headline=True)
    t.res("f_use_core", "design line force at the core (/1.5)", mn["F_use_core"], "N")
    t.res("f_use_full", "design line force at full spool (/1.5)", mn["F_use_full"], "N")
    t.res("f_snag", "snag / structural worst case (hold torque / core radius)", mn["F_snag"], "N", headline=True)
    f_old_core = hold_rated * run_frac_old / r_core
    f_old_full = hold_rated * run_frac_old / r_full
    t.res("f_old_core", "R4/R6 convention (0.36 x 0.5 / r), core", f_old_core, "N")
    t.res("f_old_full", "R4/R6 convention, full spool", f_old_full, "N")

    t.compare("R6 line force at the 7.5 mm core", 24.0, f_old_core, "N", "verification/design_review_gen2.md R6", within(f_old_core, 24.0, 0.05))
    t.compare("R4 line force at full spool (Ø15 core)", 18.0, f_old_full, "N", "verification/design_review_gen2.md R4", within(f_old_full, 18.0, 0.05))
    t.compare("R4 full radius, 16 mm drum", 10.0, r_full * 1e3, "mm", "verification/design_review_gen2.md R4", within(r_full * 1e3, 10.0, 0.05))
    t.compare("D30 cable tension 'returns to ~34 N'", 34.0, mn["F_snag"], "N", "DECISIONS.md D30",
              within(mn["F_snag"], 34.0, 0.5),
              "34 N is hold torque / empty-spool radius (a snag worst case), NOT the running pull (23.8 N at the core, "
              "17.9 N full spool, 11.9 N usable).")
    d29 = motor_numbers(1.08, rs, hold_rated, i_rated, run_frac, sf, r_core, r_full)
    t.compare("D29 cable tension at 1.35 A", 43.0, d29["F_snag"], "N", "DECISIONS.md D29", within(d29["F_snag"], 43.0, 0.5))
    t.compare("'<= 40 N per cable (motor limit)' in the load case", 40.0, mn["F_core"], "N",
              "CLAUDE.md known loads; docs/SHOPPING_LIST.md (driver note)", "DISAGREE",
              "At 1.06 A the running line force never reaches 40 N (23.8 N at the core); even the hold-torque snag load "
              "is 34 N.  The shopping list already says 40 N is not a measured actuator limit.")
    t.compare("planner max_tension_n", mot["max_tension_n"], mn["F_use_full"], "N", "config/robot.sim.json motion.max_tension_n",
              "CONTEXT", "The planning cap (15 N) sits above the 1.5-margin design force at full spool (11.9 N) and "
              "below the unmargined running force (17.9 N).")
    t.compare("D30 'Vref ~0.85 V' vs 10/21 entry 'tops out ~0.79 V'", 0.79, vref, "V", "DESIGN_STATE.md vs DECISIONS.md D30",
              "CONTEXT", "Two measurements of the same cap: 0.79 V gives 0.99 A, 0.85 V gives 1.06 A.  The 7 % spread is "
              "the uncertainty on every tension quoted here.")

    # --- spool-core study -------------------------------------------------------
    rows = []
    study = {}
    r_bore = bore_d / 2
    for dia in (15, 12, 10, 8):
        rc = dia / 2e3
        lay, rf = wind(rc, line_d, packing, width, total)
        _, rf_hex = wind_hex(rc, line_d, packing, width, total)
        n = motor_numbers(vref, rs, hold_rated, i_rated, run_frac, sf, rc, rf)
        dlen = 2 * math.pi * (rf - rc)
        v_core = 2 * math.pi * rc * f_cap / usteps
        v_full = 2 * math.pi * rf * f_cap / usteps
        f_need = v_max / (2 * math.pi * rc) * usteps
        wall_round = dia / 2 - r_bore
        wall_flat = dia / 2 - (r_bore - flat)
        tie_ok = (dia / 2 - r_bore) >= tie_d + 2 * tie_wall
        row = dict(core_mm=dia, layers=lay, r_full_mm=rf * 1e3, r_full_hex_mm=rf_hex * 1e3, ratio=rf / rc,
                   F_core=n["F_core"], F_full=n["F_full"], F_use_full=n["F_use_full"], F_snag=n["F_snag"],
                   dlen_rev_mm=dlen * 1e3, v_core_mm_s=v_core * 1e3, v_full_mm_s=v_full * 1e3,
                   f_need_hz=f_need, um_per_ustep=2 * math.pi * rc / usteps * 1e6, um_per_count=2 * math.pi * rc / enc * 1e6,
                   bend_ratio=dia / (line_d * 1e3), wall_round_mm=wall_round, wall_flat_mm=wall_flat,
                   tie_axial_ok=tie_ok, setscrew_ok=wall_flat >= m3)
        if not opts.fast:
            k_task = lp_k(task_depth())[0]
            cap_kg = n["F_use_full"] / k_task / sc.get("G")
            row["cap_total_kg"] = cap_kg
            row["max_claw_for_jeans_g"] = (cap_kg - 0.9) * 1e3
            t.res(f"c{dia}_cap", f"Ø{dia}: total weight the winches hold at the task ceiling (SF 1.5, worst place)", cap_kg, "kg",
                  headline=(dia in (15, 10)))
            t.res(f"c{dia}_maxclaw", f"Ø{dia}: largest claw mass that still lifts 0.9 kg jeans", (cap_kg - 0.9) * 1e3, "g")
        study[dia] = row
        rows.append(row)
        t.res(f"c{dia}_layers", f"Ø{dia}: layers", lay, "-")
        t.res(f"c{dia}_rfull", f"Ø{dia}: full-spool radius", rf * 1e3, "mm")
        t.res(f"c{dia}_ffull", f"Ø{dia}: running force, full spool", n["F_full"], "N")
        t.res(f"c{dia}_fcore", f"Ø{dia}: running force, core", n["F_core"], "N")
        t.res(f"c{dia}_fuse", f"Ø{dia}: design force, full spool (/1.5)", n["F_use_full"], "N")
        t.res(f"c{dia}_dlen", f"Ø{dia}: length per rev change core to full", dlen * 1e3, "mm")
        t.res(f"c{dia}_lcore", f"Ø{dia}: line paid out per spool rev, core layer", 2 * math.pi * rc * 1e3, "mm")
        t.res(f"c{dia}_lfull", f"Ø{dia}: line paid out per spool rev, full spool", 2 * math.pi * rf * 1e3, "mm")
        t.res(f"c{dia}_vcore", f"Ø{dia}: line speed at the step-rate cap, core", v_core * 1e3, "mm/s")
        t.res(f"c{dia}_fneed", f"Ø{dia}: step rate for 50 mm/s on the core layer", f_need, "Hz")
        t.res(f"c{dia}_bend", f"Ø{dia}: bend ratio", dia / (line_d * 1e3), "-")
        t.res(f"c{dia}_wall_round", f"Ø{dia}: wall, round side of the Ø5.45 bore", wall_round, "mm")
        t.res(f"c{dia}_wall_flat", f"Ø{dia}: wall, flat side (set-screw engagement)", wall_flat, "mm")
    t.table("core_study", list(rows[0].keys()), [list(r.values()) for r in rows])
    base = study[15]["F_use_full"]
    for dia in (12, 10, 8):
        gain = study[dia]["F_use_full"] / base - 1
        t.res(f"c{dia}_gain", f"Ø{dia}: design-force gain over Ø15 (full spool)", gain * 100, "%", headline=(dia == 10))
    hex_dev = max(abs(r["r_full_hex_mm"] - r["r_full_mm"]) for r in rows)
    t.res("hex_dev", "largest change of full radius with hexagonal layer pitch", hex_dev, "mm",
          "convention sensitivity: small")
    t.res("bend_min_core", "smallest core meeting the 20:1 bend ratio", bend_min * line_d * 1e3, "mm", headline=True)
    pts8 = (study[8]["F_use_full"] - study[10]["F_use_full"]) / base * 100
    need_kg = 0.45 + 0.9
    if opts.fast:
        rec = 10
    else:
        ok = [d_ for d_ in (15, 12, 10, 8) if study[d_]["bend_ratio"] >= bend_min and study[d_]["cap_total_kg"] >= need_kg]
        rec = max(ok)
    t.res("rec_core", "recommended core diameter", rec, "mm",
          f"largest core that keeps bend ratio >= 20 and lifts 0.45 kg claw + 0.9 kg jeans with SF 1.5 at the task ceiling; Ø8 would add only {pts8:.0f} more points of force",
          headline=True)
    t.res("pts8", "extra design-force gain of Ø8 over Ø10", pts8, "points")
    t.compare("20 ft fits the Ø15 core in 5 layers (R4)", 5, layers15, "layers", "verification/design_review_gen2.md R4", within(layers15, 5, 0))
    t.compare("Ø10 core study", "pending", f"+{study[10]['F_use_full'] / base * 100 - 100:.0f} % design force", "-",
              "DECISIONS.md D30 / DESIGN_STATE.md (study pending)", "CONTEXT",
              "Needs: set-screw boss (flat-side wall 2.8 mm), tie-off moved to the flange (hub annulus 2.3 mm < 3.0 mm "
              "needed), and a step rate of 5.1 kHz at 16 microsteps (or a 39 mm/s speed derate) for 50 mm/s near the core.")
    return t


# =============================================================================
# 3. Joule heating and the fin
# =============================================================================
def topic_03(opts):
    t = Topic(3, "Joule heating and the heat fin",
              "P = I^2 R;  m = sqrt(2h/(k t));  eta = tanh(mL)/(mL);  R_fin = 1/(eta h A_fin);  two-node network + fin in parallel",
              "CALCULATED (fin as-built dimensions MEASURED; temperatures PLANNED: 90 min hold test)",
              "A printed (PETG) mount cannot sink motor heat, so a 44 x 250 mm aluminium fin carries it into room air; "
              "the as-built 0.019 in sheet works, at about half the thermal effectiveness of the 1/8 in design.",
              "Lumped two-node model with assumed R_phase, film coefficient and shell resistances; the fin is a 1-D "
              "adiabatic-tip fin in still air.  A thermometer test replaces it.")
    th = PyConsts("calculations/gen2_motor_thermal.py")
    r_phase = t.assume_py("r_phase", "coil resistance per phase", th, "R_PHASE", "ohm")
    t_amb = t.assume("t_amb", "ambient near the ceiling", 23.0, "C", "DESIGN_STATE.md (room 20.6 C measured, ~23 C near the ceiling assumed); task brief")
    c_m = t.assume_py("c_m", "motor heat capacity", th, "C_M", "J/K")
    c_s = t.assume_py("c_s", "shell + air heat capacity", th, "C_S", "J/K")
    p_e = t.assume_py("p_e", "electronics inside the shell", th, "P_E", "W")
    scen = th.get("SCENARIOS")
    vref = t.fact("vref", "Vref at the cap", 0.85, "V", "DECISIONS.md D30")
    cur = vref / (8 * 0.100)
    t.fact("rs", "sense resistor", 0.100, "ohm", "DECISIONS.md D29")
    k_al = t.assume("k_al", "aluminium sheet conductivity (3003 ~159, 6061 ~167, 5052 ~138)", 160.0, "W/m K", "task brief; DESIGN_STATE.md used 167")
    k_petg = t.assume("k_petg", "PETG conductivity", 0.2, "W/m K", "calculations/gen2_motor_thermal.py docstring; design_review_gen2.md R11")
    t_as = t.fact("t_as", "as-built sheet thickness 0.019 in (measured)", 0.019 * IN_MM, "mm", "DESIGN_STATE.md (Jasper, 10/20: heat fin sheet)") * 1e-3
    t_des = t.fact("t_des", "designed plate 1/8 in", 3.175, "mm", "cad/parts/motor_heat_plate.py:T") * 1e-3
    w_fin = t.fact("w_fin", "fin width", 44.0, "mm", "cad/parts/motor_heat_plate.py:W") * 1e-3
    l_fin = t.fact("l_fin", "fin length in room air", 200.0, "mm", "cad/parts/motor_heat_plate.py (H 250, ~200 mm exposed); DESIGN_STATE.md") * 1e-3
    h_lo = t.assume("h_lo", "film coefficient, low", 5.0, "W/m^2 K", "DESIGN_STATE.md hand calc (still air + radiation, black)")
    h_mid = t.assume("h_mid", "film coefficient, mid", 7.0, "W/m^2 K", "midpoint of 5-9")
    h_hi = t.assume("h_hi", "film coefficient, high", 9.0, "W/m^2 K", "DESIGN_STATE.md hand calc")
    r_c = t.assume("r_contact", "motor flange to fin contact", 1.0, "K/W", "DESIGN_STATE.md (+~1 K/W contact)")

    p_m = cur ** 2 * r_phase
    t.res("current", "phase current", cur, "A")
    t.res("p_m", "Joule heat in the motor, I^2 R", p_m, "W", headline=True)
    a_fin = 2 * w_fin * l_fin
    t.res("a_fin", "fin area, both faces", a_fin, "m^2")

    fins = {}
    for name, thick in (("as_built", t_as), ("design", t_des)):
        for hname, h in (("lo", h_lo), ("mid", h_mid), ("hi", h_hi)):
            m, ml, eta = fin_eta(k_al, h, thick, l_fin)
            r_fin = 1.0 / (eta * h * a_fin)
            fins[(name, hname)] = (m, ml, eta, r_fin)
        m, ml, eta, r_fin = fins[(name, "mid")]
        t.res(f"{name}_m", f"{name}: m", m, "1/m")
        t.res(f"{name}_ml", f"{name}: mL", ml, "-")
        t.res(f"{name}_eta", f"{name}: fin efficiency (h = 7)", eta * 100, "%", headline=True)
        t.res(f"{name}_eta_h9", f"{name}: fin efficiency at h = 9", fins[(name, 'hi')][2] * 100, "%")
        t.res(f"{name}_eta_h5", f"{name}: fin efficiency at h = 5", fins[(name, 'lo')][2] * 100, "%")
        t.res(f"{name}_rfin", f"{name}: R_fin (h = 7)", r_fin, "K/W", headline=True)
        t.res(f"{name}_rfin_h9", f"{name}: R_fin at h = 9", fins[(name, 'hi')][3], "K/W")
        t.res(f"{name}_rfin_h5", f"{name}: R_fin at h = 5", fins[(name, 'lo')][3], "K/W")
        t.res(f"{name}_rtot", f"{name}: R_fin + contact", r_fin + r_c, "K/W")
    # repo hand-calc comparison (k 167, h 5..9, 6061)
    e_lo = fin_eta(167.0, 9.0, t_as, l_fin)[2]
    e_hi = fin_eta(167.0, 5.0, t_as, l_fin)[2]
    d_lo = fin_eta(167.0, 9.0, t_des, l_fin)[2]
    d_hi = fin_eta(167.0, 5.0, t_des, l_fin)[2]
    t.compare("fin efficiency, 0.019 in (k 167, h 5-9)", "33-44 %", f"{e_lo*100:.0f}-{e_hi*100:.0f} %", "%", "DESIGN_STATE.md (heat fin correction)",
              range_status(e_lo * 100, e_hi * 100, 33, 44, 1.5))
    t.compare("fin efficiency, 1/8 in (k 167, h 5-9)", "71-81 %", f"{d_lo*100:.0f}-{d_hi*100:.0f} %", "%", "DESIGN_STATE.md (heat fin correction)",
              range_status(d_lo * 100, d_hi * 100, 71, 81, 1.5))
    r_as_lo = 1 / (e_lo * 9 * a_fin)
    r_as_hi = 1 / (e_hi * 5 * a_fin)
    t.compare("R_fin 0.019 in (k 167, h 5-9)", "19-26 K/W", f"{r_as_lo:.0f}-{r_as_hi:.0f} K/W", "K/W", "DESIGN_STATE.md (heat fin correction)",
              range_status(r_as_lo, r_as_hi, 19, 26, 1.5))

    # network at the headline current
    names = ["open air, no shell", "vented shell", "sealed shell"]
    rows = []
    for (lbl, r_ma, r_sa, pe) in scen:
        for fname, rf in (("no fin", math.inf), ("as-built 0.019 in", fins[("as_built", "mid")][3] + r_c),
                          ("design 1/8 in", fins[("design", "mid")][3] + r_c)):
            n = network(p_m, pe, r_ma, r_sa, rf, t_amb)
            rows.append([lbl, fname, n["T_m"], n["T_s"], n["Q_fin"], n["share"] * 100])
            key = lbl.split()[0] + "_" + fname.split()[0].replace("-", "")
            t.res(f"T_{key}", f"motor case, {lbl}, {fname}", n["T_m"], "C",
                  headline=(lbl.startswith("sealed") and fname.startswith("as-built")))
            if fname != "no fin":
                t.res(f"share_{key}", f"fin heat share, {lbl}, {fname}", n["share"] * 100, "%",
                      headline=(lbl.startswith("sealed") and fname.startswith("as-built")))
    t.table("network_1p06A_23C", ["scenario", "fin", "T_motor_C", "T_shell_C", "Q_fin_W", "fin_share_pct"], rows)
    # sensitivity: as-built, h 5..9, k 138..167 (sealed)
    tm_all = []
    sh_all = []
    for k in (138.0, 160.0, 167.0):
        for h in (5.0, 7.0, 9.0):
            _, _, eta = fin_eta(k, h, t_as, l_fin)[0:3]
            rf = 1.0 / (eta * h * a_fin) + r_c
            n = network(p_m, scen[2][3], scen[2][1], scen[2][2], rf, t_amb)
            tm_all.append(n["T_m"])
            sh_all.append(n["share"] * 100)
    t.res("dT_fin_sealed", "sealed shell: temperature drop bought by the as-built fin", t.flat["t03_T_sealed_no"] - t.flat["t03_T_sealed_asbuilt"], "K", headline=True)
    t.res("sealed_asbuilt_min", "sealed, as-built fin: motor case, best of k/h sweep", min(tm_all), "C")
    t.res("sealed_asbuilt_max", "sealed, as-built fin: motor case, worst of k/h sweep", max(tm_all), "C")
    t.res("share_min", "sealed, as-built: fin heat share, low", min(sh_all), "%")
    t.res("share_max", "sealed, as-built: fin heat share, high", max(sh_all), "%")

    # repo comparison: DESIGN_STATE hand-calc temperatures (30 C and 23 C ambient)
    def sealed_range(i, amb, scen_i=2):
        out = []
        for k in (160.0, 167.0):
            for h in (5.0, 9.0):
                _, _, eta = fin_eta(k, h, t_as, l_fin)[0:3]
                rf = 1.0 / (eta * h * a_fin) + r_c
                lbl, r_ma, r_sa, pe = scen[scen_i]
                out.append(network(i * i * r_phase, pe, r_ma, r_sa, rf, amb)["T_m"])
        return min(out), max(out)
    for i, (c_lo, c_hi) in ((1.0, (50, 53)), (1.25, (59, 64)), (1.5, (71, 78))):
        lo, hi = sealed_range(i, 30.0)
        t.compare(f"sealed, {i} A, 0.019 in fin, ambient 30 C", f"{c_lo}-{c_hi}", f"{lo:.0f}-{hi:.0f}", "C", "DESIGN_STATE.md (heat fin correction)",
                  range_status(lo, hi, c_lo, c_hi, 2.0))
    for lbl_, i, amb, si, (c_lo, c_hi) in (("sealed, 1.25 A, ambient 23 C", 1.25, 23.0, 2, (53, 56)),
                                           ("vented, 1.25 A, ambient 23 C", 1.25, 23.0, 1, (47, 49)),
                                           ("sealed, 1.5 A, ambient 23 C", 1.5, 23.0, 2, (65, 69))):
        lo, hi = sealed_range(i, amb, si)
        t.compare(lbl_, f"{c_lo}-{c_hi}", f"{lo:.0f}-{hi:.0f}", "C", "DESIGN_STATE.md", range_status(lo, hi, c_lo, c_hi, 2.0))
    nofin = network(1.0 ** 2 * r_phase, scen[2][3], scen[2][1], scen[2][2], math.inf, 30.0)["T_m"]
    t.compare("no fin, sealed, 1.0 A, ambient 30 C", "67 C", nofin, "C", "verification/design_review_gen2.md R11", within(nofin, 67, 1.0))

    # time constants for the hold test
    tau_s = c_s * scen[2][2]
    t.res("tau_shell", "sealed shell time constant C_S R_sa", tau_s / 60, "min")
    t.res("hold_frac", "fraction of the final rise reached in a 90 min hold", (1 - math.exp(-90 * 60 / tau_s)) * 100, "%")

    # PETG vs aluminium
    a_flange = 42.3e-3 ** 2
    for nm, k_, thick in (("petg", k_petg, 5e-3), ("al", k_al, 3.175e-3)):
        t.res(f"slab_{nm}", f"conduction resistance through a {thick*1e3:.3g} mm {nm} plate under the motor flange", thick / (k_ * a_flange), "K/W")
    t.res("slab_ratio", "slab resistance ratio, PETG 5 mm / Al 1/8 in", (5e-3 / k_petg) / (3.175e-3 / k_al), "x", headline=True)
    for nm, k_, thick in (("al", k_al, t_as), ("petg", k_petg, t_as), ("petg5", k_petg, 5e-3)):
        m = math.sqrt(2 * h_mid / (k_ * thick))
        per = 2 * (w_fin + thick)
        ac = w_fin * thick
        g_inf = math.sqrt(h_mid * per * k_ * ac)
        t.res(f"lc_{nm}", f"{nm}: heat-spreading length 1/m (t = {thick*1e3:.3g} mm)", 1e3 / m, "mm")
        t.res(f"ginf_{nm}", f"{nm}: long-fin conductance sqrt(h P k Ac)", g_inf, "W/K")
        t.res(f"rinf_{nm}", f"{nm}: long-fin resistance", 1 / g_inf, "K/W")
    t.res("fin_ratio", "same-geometry fin: Al / PETG conductance", t.flat["t03_ginf_al"] / t.flat["t03_ginf_petg"], "x", headline=True)
    return t


# =============================================================================
# 4. gear tooth bending (Lewis)
# =============================================================================
def topic_04(opts):
    t = Topic(4, "Gear tooth bending (Lewis) and gear ratio",
              "sigma = Ft / (b m Y);  Ft = 2 tau / (m z);  SF = sigma_allow / sigma;  tau_jaw = N tau eta^2 / 2",
              "CALCULATED (jaw force: SIMULATED from CAD kinematics; no printed gear has been stalled)",
              "Module 1 / 6 mm face fails at servo stall; the gearbox moved to module 1.5 with 16 mm and 20 mm faces. "
              "Stall is the design case because a clamp stalls on every cloth grip.",
              "Static Lewis bending only: no dynamic or stress-concentration factor, form factors from the textbook "
              "table, PETG allowable is a 50 % rule of thumb; printed teeth have never been stall-tested.")
    sc = PyConsts("calculations/gen2_screening.py")
    P = PyConsts("cad/params.py")
    g = sc.get("G")
    s48 = t.fact("stall48", "MG996R stall, 4.8 V (9.4 kg cm)", sc.get("SERVO_STALL"), "N m", sc.src("SERVO_STALL"))
    s60 = t.fact("stall60", "MG996R stall, 6.0 V (11.0 kg cm)", sc.get("SERVO_STALL_6V"), "N m", sc.src("SERVO_STALL_6V"))
    eta = t.assume_py("eta", "efficiency per printed mesh", sc, "ETA_MESH", "-")
    allow = t.assume_py("allow", "PETG allowable (50 % of 45 MPa tensile)", sc, "PETG_ALLOW", "Pa")
    ylew = {18: 0.309, 24: 0.337, 36: 0.3775, 54: 0.416}
    t.fact("y18", "Lewis Y, 18T (20 deg full depth)", ylew[18], "-", "calculations/gripper_v7_screening.py:LEWIS_Y (textbook table)")
    t.fact("y24", "Lewis Y, 24T", ylew[24], "-", "calculations/gripper_v7_screening.py:LEWIS_Y")
    t.fact("y36", "Lewis Y, 36T (interpolated)", ylew[36], "-", "calculations/gripper_v7_screening.py:LEWIS_Y")
    t.fact("y54", "Lewis Y, 54T", ylew[54], "-", "calculations/gripper_v7_screening.py:LEWIS_Y")
    mod7 = t.fact_py("mod7", "v7 module", P, "GRIPV7_MODULE", "mm")
    z_p = t.fact_py("zp", "pinion teeth", P, "GRIPV7_Z_PINION", "-")
    z_m = t.fact_py("zm", "v7 big gear teeth", P, "GRIPV7_Z_MAIN", "-")
    z_s = t.fact_py("zs", "sync gear teeth", P, "GRIPV7_Z_SYNC", "-")
    face_main = t.fact_py("face_main", "pinion / big gear face", P, "GRIPV7_FACE_MAIN", "mm")
    relief = t.fact_py("relief", "axial relief on the 36T layer", P, "GRIPV7_AXIAL_RELIEF", "mm")
    face_sync = t.fact_py("face_sync", "sync pair face", P, "GRIPV7_FACE_SYNC", "mm")
    ratio7 = z_m / z_p
    face_eff = face_main - relief

    cases = [  # label, module, pinion z, big z, N, face pinion, face big, face sync
        ("R5 screening (assumed m1, b6, 18:54)", 1.0, 18, 54, 3.0, 6.0, 6.0, None),
        ("m1.5, b8 (R5 option)", 1.5, 18, 54, 3.0, 8.0, 8.0, None),
        ("m2, b10 (R5 option)", 2.0, 18, 54, 3.0, 10.0, 10.0, None),
        ("v6 as measured (m1.5, b16/20, 18:54)", 1.5, 18, 54, 3.0, 16.0, 16.0, 20.0),
        ("v7 (m1.5, b15.7/20, 18:36)", mod7, z_p, z_m, ratio7, face_eff, face_eff, face_sync),
    ]
    rows = []
    out = {}
    for lbl, m_, zp_, zb_, n_, fp, fb, fs in cases:
        for vn, tau in (("4.8 V", s48), ("6.0 V", s60)):
            dp = zp_ * m_ * 1e-3
            ft = 2 * tau / dp
            sig_p, sf_p = lewis_sf(ft, fp, m_, ylew[18], allow)
            sig_b, sf_b = lewis_sf(ft, fb, m_, ylew[zb_], allow)
            sf_s1 = None
            if fs is not None:
                tau_c = tau * n_ * eta
                ft_s = tau_c / (m_ * z_s / 2 * 1e-3)
                sig_s, sf_s1 = lewis_sf(ft_s, fs, m_, ylew[24], allow)
                sf_s2 = lewis_sf(ft_s / 2, fs, m_, ylew[24], allow)[1]
            rows.append([lbl, vn, ft, sig_p / 1e6, sf_p, sf_b, sf_s1])
            out[(lbl, vn)] = (ft, sig_p / 1e6, sf_p, sf_b, sf_s1)
    t.table("lewis", ["train", "servo", "Ft_pinion_N", "sigma_pinion_MPa", "SF_pinion", "SF_big", "SF_sync_one_jaw"], rows)
    r5 = out[(cases[0][0], "6.0 V")]
    r5b = out[(cases[0][0], "4.8 V")]
    t.res("m1_ft60", "module 1: pinion tangential force, 6.0 V stall", r5[0], "N")
    t.res("m1_sig60", "module 1: root stress, 6.0 V", r5[1], "MPa")
    t.res("m1_ft48", "module 1: pinion tangential force, 4.8 V stall", r5b[0], "N")
    t.res("m1_sig48", "module 1: root stress, 4.8 V", r5b[1], "MPa")
    t.res("m15b8_sf48", "module 1.5, b8: SF at 4.8 V", out[(cases[1][0], "4.8 V")][2], "-")
    t.res("m2b10_sf48", "module 2, b10: SF at 4.8 V", out[(cases[2][0], "4.8 V")][2], "-")
    t.res("m1_sf48", "module 1: SF at 4.8 V stall", r5b[2], "-", headline=True)
    t.res("m1_sf60", "module 1: SF at 6.0 V stall", r5[2], "-", headline=True)
    t.res("m15b8_sf60", "module 1.5, b8: SF at 6.0 V", out[(cases[1][0], "6.0 V")][2], "-")
    t.res("m2b10_sf60", "module 2, b10: SF at 6.0 V", out[(cases[2][0], "6.0 V")][2], "-")
    v7 = {vn: out[(cases[4][0], vn)] for vn in ("4.8 V", "6.0 V")}
    t.res("v7_ft48", "v7: pinion tangential force, 4.8 V", v7["4.8 V"][0], "N")
    t.res("v7_ft60", "v7: pinion tangential force, 6.0 V", v7["6.0 V"][0], "N")
    t.res("v7_sig48", "v7: pinion root stress, 4.8 V", v7["4.8 V"][1], "MPa")
    t.res("v7_sig60", "v7: pinion root stress, 6.0 V", v7["6.0 V"][1], "MPa")
    t.res("v7_sf_pin48", "v7 pinion SF, 4.8 V", v7["4.8 V"][2], "-", headline=True)
    t.res("v7_sf_pin60", "v7 pinion SF, 6.0 V", v7["6.0 V"][2], "-", headline=True)
    t.res("v7_sf_big48", "v7 36T SF, 4.8 V", v7["4.8 V"][3], "-")
    t.res("v7_sf_big60", "v7 36T SF, 6.0 V", v7["6.0 V"][3], "-", headline=True)
    t.res("v7_sf_sync60", "v7 sync 24T SF, one jaw takes all, 6.0 V", v7["6.0 V"][4], "-", headline=True)
    t.res("v7_sf_sync48", "v7 sync 24T SF, one jaw takes all, 4.8 V", v7["4.8 V"][4], "-")
    v6s = out[(cases[3][0], "6.0 V")]
    t.res("v6_sf_sync60", "v6 sync 24T SF, one jaw, 6.0 V (N = 3)", v6s[4], "-")
    t.res("v6_sf_pin60", "v6 pinion SF, 6.0 V", v6s[2], "-")

    j = load_json("verification/gripper_v7_numbers.json")
    lew = {(r["servo"], r["gear"]): r["SF"] for r in j["lewis"]}
    t.compare("R5 module 1 SF at 4.8 V", 0.41, r5b[2], "-", "verification/design_review_gen2.md R5", within(r5b[2], 0.41, 0.005))
    t.compare("R5 module 1 SF at 6.0 V", 0.35, r5[2], "-", "verification/design_review_gen2.md R5", within(r5[2], 0.35, 0.005))
    t.compare("R5 module 1.5, b8, 6 V", 1.04, out[(cases[1][0], "6.0 V")][2], "-", "verification/design_review_gen2.md R5", within(out[(cases[1][0], "6.0 V")][2], 1.04, 0.01))
    t.compare("R5 module 2, b10, 6 V", 2.32, out[(cases[2][0], "6.0 V")][2], "-", "verification/design_review_gen2.md R5", within(out[(cases[2][0], "6.0 V")][2], 2.32, 0.01))
    t.compare("v7 pinion SF 6 V", lew[("6.0 V", "pinion 18T")], v7["6.0 V"][2], "-", "verification/gripper_v7_numbers.json", within(v7["6.0 V"][2], lew[("6.0 V", "pinion 18T")], 0.002))
    t.compare("v7 36T SF 6 V", lew[("6.0 V", "big gear 36T")], v7["6.0 V"][3], "-", "verification/gripper_v7_numbers.json", within(v7["6.0 V"][3], lew[("6.0 V", "big gear 36T")], 0.002))
    t.compare("v7 sync SF one jaw 6 V", 1.997, v7["6.0 V"][4], "-", "verification/gripper_v7_verification.md (accepted, below 2.0)", within(v7["6.0 V"][4], 1.997, 0.002),
              "1.997 is under the 2.0 target by 0.15 %, accepted by the lead; without the 0.95 mesh efficiency it is 1.90.")
    t.compare("v6 sync SF under one-jaw load", 1.33, v6s[4], "-", "docs/presentation/DECISION_STORIES.md T34", within(v6s[4], 1.33, 0.01))
    t.compare("v7 'SF about 2.0-2.5' at stall", "2.0-2.5",
              f"6 V: {v7['6.0 V'][4]:.2f} (sync) / {v7['6.0 V'][2]:.2f} (pinion) / {v7['6.0 V'][3]:.2f} (36T)", "-",
              "task brief; verification/gripper_v7_verification.md", "AGREE",
              f"At 4.8 V the same three are {v7['4.8 V'][4]:.2f} / {v7['4.8 V'][2]:.2f} / {v7['4.8 V'][3]:.2f}; the claw servo runs at 5 V (DECISION_STORIES T34), between the two.")

    # ratio effect on jaw force
    rows = []
    for n_ in (1.5, 2.0, 3.0):
        for vn, tau in (("4.8 V", s48), ("6.0 V", s60)):
            tau_j = tau * n_ * eta ** 2 / 2
            ft_s = tau * n_ * eta / (mod7 * z_s / 2 * 1e-3)
            sf_s = lewis_sf(ft_s, face_sync, mod7, ylew[24], allow)[1]
            rows.append([n_, vn, tau_j, 153.0 / n_, ft_s, sf_s])
    t.table("ratio", ["N", "servo", "tau_per_jaw_Nm", "jaw_stroke_deg_(153 deg servo)", "Ft_sync_one_jaw_N", "SF_sync_one_jaw"], rows)
    n2 = [r for r in rows if r[0] == 2.0 and r[1] == "4.8 V"][0]
    n3 = [r for r in rows if r[0] == 3.0 and r[1] == "4.8 V"][0]
    t.res("tauj_n2", "jaw torque, N = 2, 4.8 V", n2[2], "N m", headline=True)
    t.res("tauj_n3", "jaw torque, N = 3, 4.8 V", n3[2], "N m")
    t.res("stroke_n2", "jaw stroke, N = 2 (153 deg servo)", n2[3], "deg")
    t.res("stroke_n3", "jaw stroke, N = 3", n3[3], "deg")
    t.res("sync_sf_n3", "sync SF (one jaw), N = 3, 4.8 V, module 1.5", n3[5], "-")
    # implied lever arm
    ft_tab = j["force_table_N"]["v7"]["4.8 V"]
    tau_j48 = s48 * ratio7 * eta ** 2 / 2
    for gap in ("10", "40", "70"):
        t.res(f"reff_{gap}", f"effective jaw lever arm at tip gap {gap} mm (tau_jaw / F)", tau_j48 / ft_tab[gap] * 1e3, "mm")
    t.res("tauj_v7_48", "v7 jaw torque, 4.8 V", tau_j48, "N m")
    return t


# =============================================================================
# 5. grip by friction
# =============================================================================
def topic_05(opts):
    t = Topic(5, "Grip by friction",
              "2 mu N >= m (g + a)   ->   N >= m (g + a) / (2 mu)  per jaw",
              "CALCULATED vs SIMULATED jaw force (CAD four-bar); hardware pull test PLANNED",
              "The jaws must deliver more than 9 N (1 lb, mu 0.3) up to 18 N (0.9 kg jeans, mu 0.3) per jaw; the v7 "
              "gearbox gives 13-25 N, so 1 lb is covered everywhere and jeans need a wide enough grab or higher friction.",
              "Coulomb friction between two flat pads and a rigid object; cloth squeezes, bunches and interlocks, "
              "so real holding is better than mu alone says, but mu of the cloth on the pad is unmeasured.")
    sc = PyConsts("calculations/gen2_screening.py")
    g = t.fact_py("g", "gravity", sc, "G", "m/s^2")
    a = t.fact("a", "design acceleration", 2.0, "m/s^2", "CLAUDE.md load case; calculations/gen2_payload_limit.py:ACCEL")
    m_lb = t.fact("m_lb", "1 lb test weight", LB_KG, "kg", "calculations/gen2_screening.py:TEST_WEIGHT")
    m_jeans = t.fact("m_jeans", "jeans payload", 0.9, "kg", "REQUIREMENTS.md R1 / CR6 (provisional screening reference)")
    t.assume("mu_lo", "cloth on printed pad, low", 0.3, "-", "calculations/gen2_screening.py:MU_CLOTH")
    t.assume("mu_hi", "cloth on pad, high (TPU pads)", 0.6, "-", "task brief")
    j = load_json("verification/gripper_v7_numbers.json")
    tab = j["force_table_N"]["v7"]
    f48 = {int(k): v for k, v in tab["4.8 V"].items()}
    f60 = {int(k): v for k, v in tab["6.0 V"].items()}
    f_min = t.fact("fmin", "minimum jaw force, 4.8 V, gap 0.6 mm", 13.34, "N", "verification/gripper_v7_verification.md claim 6 (independent four-bar)")
    t.fact("gaps", "tabulated gaps 10..80 mm", sorted(f48), "mm", "verification/gripper_v7_numbers.json force_table_N")
    f_max_tab = max(v for k, v in f48.items() if k <= 70)
    t.res("fmax70", "jaw force at 70 mm gap, 4.8 V", f48[70], "N")
    t.res("fmin", "jaw force range low (gap 0.6 mm)", f_min, "N", headline=True)
    rows = []
    gaps = sorted(f48)
    for name, m in (("1 lb", m_lb), ("0.9 kg jeans", m_jeans)):
        for mu in (0.3, 0.6):
            n_req = m * (g + a) / (2 * mu)
            n_static = m * g / (2 * mu)
            sf_min = f_min / n_req
            # smallest gap above which 4.8 V / 6.0 V force meets the requirement
            def gap_needed(tabl):
                xs = [0.6] + gaps
                ys = [f_min] + [tabl[k] for k in gaps]
                if tabl is f60:
                    ys = [f_min * 16.5176198085233 / 14.115056927283547] + [tabl[k] for k in gaps]
                if ys[0] >= n_req:
                    return 0.0
                for i in range(1, len(xs)):
                    if ys[i] >= n_req:
                        return xs[i - 1] + (n_req - ys[i - 1]) / (ys[i] - ys[i - 1]) * (xs[i] - xs[i - 1])
                return float("inf")
            g48, g60 = gap_needed(f48), gap_needed(f60)
            rows.append([name, mu, n_static, n_req, sf_min, f48[70] / n_req, g48, g60])
            key = f"{'lb' if '1 lb' in name else 'jeans'}_mu{int(mu*10):02d}"
            t.res(f"Ns_{key}", f"required normal force per jaw, static, {name}, mu {mu}", n_static, "N")
            t.res(f"N_{key}", f"required normal force per jaw, {name}, mu {mu}", n_req, "N", headline=(mu == 0.3))
            t.res(f"sf_{key}", f"margin at the weakest point (13.34 N), {name}, mu {mu}", sf_min, "-")
            t.res(f"gap48_{key}", f"smallest grab width where 4.8 V force suffices, {name}, mu {mu}", g48, "mm")
            t.res(f"gap60_{key}", f"same at 6.0 V (scaled)", g60, "mm")
    t.table("friction", ["load", "mu", "N_static_N", "N_dynamic_N", "SF_at_13.34N", "SF_at_70mm_4.8V", "gap_ok_4.8V_mm", "gap_ok_6.0V_mm"], rows)
    t.compare("1 lb at mu 0.3 needs 7.4 N per jaw", 7.4, m_lb * g / (2 * 0.3), "N", "calculations/gripper_v7_screening.py:NEED_PER_JAW",
              "AGREE", "Static only.  Adding +2 m/s^2 gives 8.9 N; the repo number omits the dynamic term.")
    t.compare("v7 jaw force range", "13.3-25 N", f"{f_min:.1f}-{f48[70]:.1f} N", "N", "verification/gripper_v7_verification.md; gripper_v7_numbers.json",
              "AGREE", "'Measured' here means independently computed from the CAD four-bar, not a force gauge: SIMULATED.")
    t.compare("R5 'train delivers ~20.8 N per jaw at a 60 mm arm'", 20.8, f"{f48[10]:.1f}-{f48[70]:.1f}", "N", "verification/design_review_gen2.md R5",
              "CONTEXT", "That was the V5 estimate at a fixed 60 mm arm; the v7 four-bar gives 14-25 N depending on the grab width.")
    t.compare("design review 'grip margin ~2.8x for 1 lb'", 2.8, f_min / (m_lb * g / (2 * 0.3)), "x", "verification/design_review_gen2.md verdict",
              "DISAGREE", f"Like for like (static, 13.3 N weakest point) the v7 margin is {f_min / (m_lb * g / (2 * 0.3)):.1f}x; with +2 m/s^2 it is "
              f"{f_min / (m_lb * (g + a) / (2 * 0.3)):.1f}x.  The 2.8x came from the V5 estimate (20.8 N / 7.4 N).")
    return t


# =============================================================================
# 6. beam bending, creep, bearing stress
# =============================================================================
def topic_06(opts):
    t = Topic(6, "Beam bending and creep: why an aluminium tube",
              "I = pi (D^4 - d^4)/64;  delta = F L^3 / (3 E I);  sigma = M c / I;  bearing: sigma_b = F / (2 d t)",
              "CALCULATED (as-built tube wall UNMEASURED; creep factor ILLUSTRATIVE; no creep test)",
              "The claw arm is a long tube that must keep the camera-to-jaw geometry; aluminium is 33 x stiffer than "
              "printed PETG at the same size and does not creep at room temperature.",
              "Linear-elastic cantilever with an assumed 10 N side load; E for printed PETG and the alloy are assumed; "
              "thin-wall dent and local buckling are not modelled; the creep exponent is illustrative.")
    P = PyConsts("cad/params.py")
    od = t.fact_py("od", "tube OD (CAD)", P, "GRIPV7_TUBE_OD", "mm")
    idia = t.fact_py("id", "tube ID (CAD, 3 mm wall)", P, "GRIPV7_TUBE_ID", "mm")
    length = t.fact_py("len", "tube length after the 50 mm cut (D28)", P, "GRIPV7_TUBE_LEN", "mm")
    free = t.fact("free", "free tube, head to hub bottom (c = 50)", 156.2, "mm", "verification/claw_tube_length_view_study.json tube[50]")
    e_al = t.assume("e_al", "aluminium modulus (6061; alloy unknown)", 69e9, "Pa", "DESIGN_STATE.md hand calc; alloy VERIFY")
    e_pg = t.assume("e_pg", "printed PETG modulus, in plane", 2.1e9, "Pa", "calculations/gripper_v7_screening.py:E_PETG")
    f_side = t.assume("f_side", "side load at the tube tip", 10.0, "N", "DESIGN_STATE.md hand calc (10 N at 250 mm)")
    rho = t.assume("rho", "aluminium density", 2.70, "g/cm^3", "verification/claw_tube_length_view_study.md (2.70 g/cc)")
    f_bolt = t.assume("f_bolt", "cross-bolt design load", 100.0, "N", "calculations/gripper_v7_screening.py:socket_tension_check")
    d_bolt = t.fact("d_bolt", "M3 shank", 3.0, "mm", "calculations/gripper_v7_screening.py:socket_tension_check")
    bolt_hole = t.fact_py("bolt_hole", "cross-hole diameter", P, "GRIPV7_XBOLT_HOLE_D", "mm")
    m_head = t.fact("m_head", "v7 head mass (CAD)", load_json("verification/gripper_v7_numbers.json")["mass_rollup"]["v7_gripper_head_cad_g"] / 1e3, "kg", "verification/gripper_v7_numbers.json")
    al_bear = t.assume("al_bear", "bearing allowable, 1.5 x 240 MPa yield", 1.5 * 240e6, "Pa", "calculations/gripper_v7_screening.py (6061-T6 assumed)")

    def inertia(d_o, d_i):
        return math.pi / 64.0 * (d_o ** 4 - d_i ** 4) * 1e-12     # m^4

    def cant(f, ll, e, i_, c):
        return f * ll ** 3 / (3 * e * i_), f * ll * c / i_

    c = od / 2e3
    rows = []
    for wall in (3.0, 1.5, 1.0, 0.48):
        i_ = inertia(od, od - 2 * wall)
        area = math.pi / 4 * (od ** 2 - (od - 2 * wall) ** 2)
        for ll_name, ll in (("254.8 mm", length * 1e-3), ("156.2 mm", free * 1e-3)):
            d_, s_ = cant(f_side, ll, e_al, i_, c)
            rows.append([wall, ll_name, i_ * 1e12, d_ * 1e3, s_ / 1e6, area * length * rho / 1e3])
    t.table("al_tube", ["wall_mm", "free_length", "I_mm4", "tip_deflection_mm", "bending_stress_MPa", "mass_g"], rows)
    for wall in (3.0, 1.0, 0.48):
        i_w = inertia(od, od - 2 * wall)
        d_w, s_w = cant(f_side, length * 1e-3, e_al, i_w, c)
        a_w = math.pi / 4 * (od ** 2 - (od - 2 * wall) ** 2)
        t.res(f"w{wall}_defl", f"Al tube, {wall} mm wall: tip deflection, 10 N at 254.8 mm", d_w * 1e3, "mm")
        t.res(f"w{wall}_stress", f"Al tube, {wall} mm wall: bending stress", s_w / 1e6, "MPa")
        t.res(f"w{wall}_mass", f"Al tube, {wall} mm wall: mass", a_w * length * rho / 1e3, "g")
        t.res(f"w{wall}_i", f"Al tube, {wall} mm wall: I", i_w * 1e12, "mm^4")
    d_free, s_free = cant(f_side, free * 1e-3, e_al, inertia(od, idia), c)
    t.res("d_al_free", "aluminium tube (3 mm wall) tip deflection with the 156.2 mm free length", d_free * 1e3, "mm")
    t.res("s_al_free", "same, bending stress", s_free / 1e6, "MPa")
    i3 = inertia(od, idia)
    d_al, s_al = cant(f_side, length * 1e-3, e_al, i3, c)
    d_pg, s_pg = cant(f_side, length * 1e-3, e_pg, i3, c)
    t.res("i3", "I of the 3 mm-wall tube", i3 * 1e12, "mm^4")
    t.res("d_al", "aluminium tube tip deflection, 10 N at 254.8 mm", d_al * 1e3, "mm", headline=True)
    t.res("s_al", "aluminium tube bending stress", s_al / 1e6, "MPa", headline=True)
    t.res("d_pg", "PETG tube (same size) tip deflection", d_pg * 1e3, "mm", headline=True)
    t.res("s_pg", "PETG tube bending stress (same as Al: geometry only)", s_pg / 1e6, "MPa")
    t.res("ei_ratio", "stiffness ratio Al / PETG at equal geometry", e_al / e_pg, "x", headline=True)
    t.res("strain_pg", "PETG bending strain at the outer fibre", s_pg / e_pg * 100, "%")
    i1 = inertia(od, od - 2.0)
    t.res("i1_ratio", "1 mm wall vs 3 mm wall, bending stiffness", i1 / i3 * 100, "%")
    t.res("al1_vs_pg3", "1 mm Al wall vs 3 mm PETG wall, stiffness", e_al * i1 / (e_pg * i3), "x")
    a3 = math.pi / 4 * (od ** 2 - idia ** 2)
    a1 = math.pi / 4 * (od ** 2 - (od - 2.0) ** 2)
    t.res("m3", "tube mass, 3 mm wall, 254.8 mm", a3 * length * rho / 1e3, "g")
    t.res("m1", "tube mass, 1 mm wall, 254.8 mm", a1 * length * rho / 1e3, "g")
    t.res("m1_frac", "1 mm wall mass as a fraction of the 3 mm wall", a1 / a3 * 100, "%")
    # the retired 0.48 mm calculation
    i048 = inertia(od, od - 0.96)
    d048, s048 = cant(f_side, 0.25, e_al, i048, c)
    t.compare("hand calc 'I 4,200 mm^4; 10 N at 250 mm -> 0.18 mm, 8.5 MPa'", "4200 / 0.18 / 8.5", f"{i048*1e12:.0f} / {d048*1e3:.2f} / {s048/1e6:.1f}", "mm^4 / mm / MPa",
              "DESIGN_STATE.md (tube wall entry, later corrected)", "AGREE",
              "Arithmetic is right, but the 0.48 mm wall was the heat fin's thickness; for the CAD wall (3 mm) the "
              "numbers are 0.04 mm and 1.8 MPa.  The real wall is unmeasured.")
    t.compare("'1 mm wall ~71 g, 41 % of stiffness, ~14x stiffer than 3 mm PETG'", "71 g / 41 % / 14x",
              f"{a1*length*rho/1e3:.0f} g / {i1/i3*100:.0f} % / {e_al*i1/(e_pg*i3):.1f}x", "-", "docs/presentation/DECISION_STORIES.md section 5",
              "AGREE", "The 71 g is for the 304.8 mm tube; at 254.8 mm it is 59 g.")

    # creep vs stress relaxation (illustrative power-law, not data)
    n_exp = t.assume("n_exp", "creep-modulus exponent, E(t) = E1 t^-n", 0.07, "-", "ASSUMED, illustrative only (no creep test in the repository)")
    for hrs in (1, 100, 1000, 8760):
        t.res(f"ret_{hrs}", f"modulus retained after {hrs} h at constant stress (illustrative)", (hrs ** -n_exp) * 100, "%")
    t.res("d_pg_1000", "PETG tube tip deflection after 1000 h under the same 10 N (illustrative)", d_pg * 1e3 / (1000 ** -n_exp), "mm")
    t.res("al_sigma_yield", "aluminium: working bending stress / yield (240 MPa, 6061-T6 assumed)", s_al / 240e6 * 100, "%",
          "far too low for measurable metal creep at room temperature")
    t.res("pg_sigma_tens", "PETG: working bending stress / tensile strength (45 MPa)", s_pg / 45e6 * 100, "%",
          "low stress does not stop polymer creep; room temperature is about 57 K below the ~80 C softening point")

    # bearing at the cross-bolt
    for wall in (3.0, 1.0, 0.48):
        sb = f_bolt / (2 * d_bolt * 1e-3 * wall * 1e-3)
        t.res(f"sb_{wall}", f"bearing stress at the cross-bolt, {wall} mm wall, 100 N", sb / 1e6, "MPa", headline=(wall == 3.0))
    sb3 = f_bolt / (2 * d_bolt * 1e-3 * 3e-3)
    t.res("sf_bear", "bearing safety factor, 3 mm wall", al_bear / sb3, "-")
    t.res("cap_bear", "tube bearing capacity, 3 mm wall (2 d t sigma_allow)", 2 * d_bolt * 1e-3 * 3e-3 * al_bear, "N")
    load_real = (m_head + 0.9) * (9.81 + 2.0)
    t.res("load_real", "actual axial load on the bolt: (head + 0.9 kg)(g + 2)", load_real, "N")
    t.res("sf_design", "design load / actual load", f_bolt / load_real, "x")
    t.compare("bearing capacity at the cross-bolt (3 mm wall)", 6480.0, 2 * d_bolt * 1e-3 * 3e-3 * al_bear, "N",
              "calculations/gripper_v7_screening.py (tube_bearing)", within(2 * d_bolt * 1e-3 * 3e-3 * al_bear, 6480.0, 1.0))
    t.compare("'M3 bearing ~35 MPa on two 0.48 mm walls'", 35.0, f_bolt / (2 * d_bolt * 1e-3 * 0.48e-3) / 1e6, "MPa", "DESIGN_STATE.md",
              "AGREE", "Retired scenario (see above).")
    return t


# =============================================================================
# 7. pendulum dynamics and tilt
# =============================================================================
def _rtilt(w):
    th = float(np.hypot(w[0], w[1]))
    if th < 1e-12:
        return np.eye(3)
    k = np.array([w[0], w[1], 0.0]) / th
    kk = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * kk + (1 - math.cos(th)) * (kk @ kk)


def statics_tilt(anchors, attach, p, depth_com, g=9.81, m=1.0):
    """Roll/pitch of a rigid claw hanging on four straight lines (no pretension: minimum-norm tension set).
    Force balance leaves one free tension mode; the minimum 2-norm set is used.  The two horizontal moment
    equations about the CoM then fix the tilt (Newton on the 2x2 system).  Independent re-derivation of the
    physics described in roomcleaner/cdpr/kinematics.py (Attitude)."""
    c = np.array([0.0, 0.0, -depth_com])
    wrench = np.array([0.0, 0.0, m * g])

    def state(w):
        r_ = _rtilt(w)
        r = attach @ r_.T
        d = anchors - (p + r)
        u = d / np.linalg.norm(d, axis=1, keepdims=True)
        tt = np.linalg.lstsq(u.T, wrench, rcond=None)[0]
        mom = np.cross(r - r_ @ c, tt[:, None] * u).sum(0)
        return r_, tt, mom

    w = np.zeros(2)
    for _ in range(60):
        r_, tt, mom = state(w)
        if np.max(np.abs(mom[:2])) < 1e-10:
            break
        jac = np.empty((2, 2))
        for k in range(2):
            wk = w.copy()
            wk[k] += 1e-6
            jac[:, k] = (state(wk)[2][:2] - mom[:2]) / 1e-6
        w = w + np.clip(-np.linalg.solve(jac, mom[:2]), -0.2, 0.2)
    r_, tt, mom = state(w)
    return math.degrees(math.acos(max(-1.0, min(1.0, r_[2, 2])))), tt


def topic_07(opts):
    t = Topic(7, "Pendulum dynamics and tilt",
              "T = 2 pi sqrt(L/g);  compound: T = 2 pi sqrt((k^2 + L^2)/(g L));  tilt: sum (r_i - r_c) x T_i u_i = 0  ->  theta ~ M_v / (W L)",
              "CALCULATED; statics tilt reproduced from the cable model (SIMULATED in the repository); damping UNMEASURED",
              "Grips are approved only after a settle dwell (5 periods x 1.25) and a tilt check; a shorter CoM depth "
              "means a shorter period but a larger tilt for the same cable moment.",
              "Small-angle rigid pendulum with no damping model; the CoM depth is a CAD-solid estimate of the old v6 "
              "head and is stale; the tilt model assumes no pretension and straight lines.")
    P = PyConsts("cad/params.py")
    cfg = load_json("config/robot.sim.json")
    body = load_json("verification/claw_body_frame.json")
    num = load_json("verification/gripper_v7_numbers.json")
    tube = load_json("verification/claw_tube_length_view_study.json")
    g = t.fact("g", "gravity", 9.81, "m/s^2", "calculations/gen2_screening.py:G")
    l_stale = t.fact("l_stale", "CoM depth below the attachment plane (v6 head, 2065 g CAD)", -body["com_body_m"][2], "m",
                     "verification/claw_body_frame.json com_body_m; config/robot.sim.json claw.com_body_m")
    k_g = t.assume("k_g", "radius of gyration about the CoM", 0.13, "m", "verification/imu_removal_review.md F8c (assumed)")
    margin = t.assume("margin", "period margin used by the gate", 1.25, "-", "roomcleaner/cdpr/attitude.py settle_dwell_s; board_attitude_results.md")
    periods = t.assume("periods", "settle periods", 5, "-", "verification/board_attitude_results.md (grip_settle_periods)")
    l_low = t.fact("l_low", "jaw tips below the attachment plane", -body["lowest_point_body_m"][2], "m", "verification/claw_body_frame.json lowest_point_body_m")
    m_claw_cfg = t.assume("m_claw_cfg", "claw mass in the config", 0.6, "kg", "config/robot.sim.json claw.mass_kg (matches neither 0.45 nor 1.05-1.25; multi_attachment_review.md)")
    payload = t.fact("payload", "release payload", 0.9, "kg", "REQUIREMENTS.md R1")

    def period(l_):
        return 2 * math.pi * math.sqrt(l_ / g)

    def period_c(l_):
        return 2 * math.pi * math.sqrt((k_g ** 2 + l_ ** 2) / (g * l_))

    # lumped CoM bracket for the current head (rough; CAD-solid masses)
    org_y = body["frame"]["origin_v6_world_mm"][1]
    tube50 = tube["tube"]["50"]
    c_cut = 50.0
    y_att = org_y - c_cut
    y_tube_lo, y_tube_hi = tube["geometry"]["tube_y_range"][0], tube["geometry"]["tube_y_range"][1] - c_cut
    y_blk_lo, y_blk_hi = tube["geometry"]["cylinder_block_y_range"]
    rows_m = {r[0]: r[1] for r in body["com_mass_rows_g"]}
    m_box = t.fact("m_box", "electrical box, CAD solid", rows_m["Gripper_Electric_Housing_Base (2)"], "g", "verification/claw_body_frame.json com_mass_rows_g")
    m_cyl = t.fact("m_cyl", "Griper Cylinder, CAD solid", rows_m["Griper Cylinder"], "g", "verification/claw_body_frame.json com_mass_rows_g")
    m_tube = t.fact("m_tube", "tube 254.8 mm", tube50["tube_mass_g"], "g", "verification/claw_tube_length_view_study.json tube[50]")
    m_head = t.fact("m_head", "v7 head, CAD (printed + purchased)", num["mass_rollup"]["v7_gripper_head_cad_g"], "g", "verification/gripper_v7_numbers.json")
    d_box = t.assume("d_box", "box centroid depth below the attachment plane (negative = above)", -31.0, "mm", "ASSUMED from box heights in claw_tube_length_view_study.md (box spans -7.5..+73.7 mm)")
    d_cyl = (y_att - (y_blk_lo - 0 + (y_blk_hi - y_blk_lo) / 2)) * 1.0
    d_cyl = (y_att + c_cut) - (y_blk_lo + y_blk_hi) / 2.0       # hub rides down with the box: same depth as at c = 0
    d_tube = y_att - (y_tube_lo + y_tube_hi) / 2.0
    d_head = t.assume("d_head", "v7 head CoM depth below the attachment plane", y_att - 728.0, "mm", "ASSUMED: head CoM at world y 728 (jaw tips 581, plate top 830)")
    t.res("d_cyl", "hub centroid depth", d_cyl, "mm")
    t.res("d_tube", "tube centroid depth", d_tube, "mm")
    masses = [m_box, m_cyl, m_tube, m_head]
    depths = [d_box, d_cyl, d_tube, d_head]
    l_est = sum(m * d for m, d in zip(masses, depths)) / sum(masses) * 1e-3
    l_lo = sum(m * d for m, d in zip(masses, [d_box - 30, d_cyl, d_tube, d_head - 40])) / sum(masses) * 1e-3
    l_hi = sum(m * d for m, d in zip(masses, [d_box + 30, d_cyl, d_tube, d_head + 40])) / sum(masses) * 1e-3
    t.res("l_est", "lumped CoM depth, v7 head with the 50 mm cut (no electronics, CAD solids)", l_est, "m", headline=True)
    t.res("l_est_lo", "bracket, low", l_lo, "m")
    t.res("l_est_hi", "bracket, high", l_hi, "m")
    t.res("m_total", "lumped mass (CAD solids)", sum(masses), "g")

    rows = []
    for lbl, l_ in (("v6 head (stale, in config)", l_stale), ("review F8d: D28 shortens L", 0.16),
                    ("lumped v7 estimate", l_est), ("loaded release (0.6 kg claw + 0.9 kg at the tips)", None)):
        if l_ is None:
            l_ = (m_claw_cfg * l_stale + payload * l_low) / (m_claw_cfg + payload)
        rows.append([lbl, l_, period(l_), period_c(l_), periods * margin * period(l_)])
    t.table("pendulum", ["case", "L_m", "T_simple_s", "T_compound_s", "dwell_s"], rows)
    t.res("T_stale", "period, L = 0.196 m", period(l_stale), "s", headline=True)
    t.res("Tc_stale", "compound-pendulum period, L = 0.196, k = 0.13", period_c(l_stale), "s")
    t.res("T_est", "period, lumped v7 estimate", period(l_est), "s", headline=True)
    t.res("dwell_stale", "settle dwell, L = 0.196 (5 x 1.25 x T)", periods * margin * period(l_stale), "s", headline=True)
    l_loaded = (m_claw_cfg * l_stale + payload * l_low) / (m_claw_cfg + payload)
    t.res("l_loaded", "loaded CoM depth (0.9 kg at the jaw tips)", l_loaded, "m")
    t.res("T_loaded", "loaded period", period(l_loaded), "s")
    t.res("dwell_loaded", "loaded dwell", periods * margin * period(l_loaded), "s", headline=True)
    t.res("comp_pct", "compound vs simple period at L = 0.196", (period_c(l_stale) / period(l_stale) - 1) * 100, "%")
    t.compare("T = 0.8887 s, dwell 4.44 s (5 T)", 0.8887, period(l_stale), "s", "verification/imu_removal_review.md section 7", within(period(l_stale), 0.8887, 0.001))
    t.compare("dwell 5 x 1.25 x T", 5.55, periods * margin * period(l_stale), "s", "verification/imu_removal_review.md R2.1", within(periods * margin * period(l_stale), 5.55, 0.02))
    t.compare("loaded release L = 0.389 m, T = 1.251 s, dwell 7.82 s", 7.82, periods * margin * period(l_loaded), "s", "verification/imu_removal_review.md R2.1", within(periods * margin * period(l_loaded), 7.82, 0.05))
    t.compare("compound period 1.06 s", 1.06, period_c(l_stale), "s", "verification/imu_removal_review.md F8c", within(period_c(l_stale), 1.06, 0.01))
    t.compare("CoM depth 0.196 m is current", 0.196, l_est, "m", "verification/claw_body_frame.json (v6 head 2065 g)", "STALE",
              "0.196 m comes from the old 1044 g v6 head on the 304.8 mm tube.  A lumped estimate for the v7 head "
              "with the D28 cut is 0.10-0.14 m (review F8d guessed 0.16 m).  Re-extract from the CAD before quoting.")

    # damping: how much of the amplitude is left after n periods
    for zeta in (0.01, 0.02, 0.05):
        t.res(f"left_{int(zeta*100):02d}", f"amplitude left after 5 periods, zeta = {zeta}", math.exp(-2 * math.pi * zeta * periods) * 100, "%")
    t.res("zeta_need", "damping ratio for a 90 % reduction in 5 periods", math.log(10) / (2 * math.pi * periods), "-")
    t.assume("zeta", "damping ratio of the hanging claw", "unknown", "-", "ASSUMED (measure the free decay; repository: 'measure real damping')")

    # statics tilt: independent recompute of the grid in imu_removal_review.md R2.4
    anchors = np.array([s["anchor_room_m"] for s in cfg["stations"]], float)
    attach = np.array(body["attachment_points_body_m"], float)
    t.fact("anchors", "anchor positions (simulation profile)", anchors.tolist(), "m", "config/robot.sim.json stations[*].anchor_room_m (NOT surveyed)")
    t.fact("attach", "attachment points, +-42.07 mm square", attach.tolist(), "m", "verification/claw_body_frame.json attachment_points_body_m")
    z_att = l_low
    xs = np.linspace(0.4, cfg["room"]["width_m"] - 0.4, 9)
    ys = np.linspace(0.4, cfg["room"]["depth_m"] - 0.4, 7)
    grids = {}
    for lbl, l_ in (("stale", l_stale), ("est", l_est)):
        tl = np.array([statics_tilt(anchors, attach, np.array([x, y, z_att]), l_)[0] for x in xs for y in ys])
        grids[lbl] = tl
        t.res(f"tilt_{lbl}_min", f"statics tilt, 9x7 grid, L = {l_:.3f}: min", tl.min(), "deg")
        t.res(f"tilt_{lbl}_med", f"statics tilt: median", float(np.median(tl)), "deg")
        t.res(f"tilt_{lbl}_max", f"statics tilt: max (corners)", tl.max(), "deg", headline=True)
        t.res(f"tilt_{lbl}_frac", f"fraction of the grid above 5 deg", float((tl > 5).mean() * 100), "%", headline=True)
    centre = statics_tilt(anchors, attach, np.array([cfg["room"]["width_m"] / 2, cfg["room"]["depth_m"] / 2, z_att]), l_stale)[0]
    t.res("tilt_centre", "statics tilt at the room centre, L = 0.196", centre, "deg")
    t.res("tilt_scale", "corner tilt ratio, L 0.196 -> lumped estimate", grids["est"].max() / grids["stale"].max(), "x")
    t.res("tilt_scale_1overL", "1/L ratio", l_stale / l_est, "x", "first-order law: tilt ~ 1/L")
    try:
        sys.path.insert(0, REPO)
        from roomcleaner.cdpr.kinematics import Geometry as _RepoGeometry
        geo = _RepoGeometry(anchors, attach, com=np.array([0.0, 0.0, -l_stale]), mass_kg=0.6)
        poses = [(0.4, 0.4, z_att), (1.676, 0.4, z_att), (1.0, 1.0, z_att), (0.8, 2.0, 0.7),
                 (cfg["room"]["width_m"] / 2, cfg["room"]["depth_m"] / 2, z_att)]
        diffs = []
        for pp in poses:
            r_ = geo.R_at(np.array(pp))
            diffs.append(abs(math.degrees(math.acos(r_[2, 2])) - statics_tilt(anchors, attach, np.array(pp), l_stale)[0]))
        t.res("xcheck", "largest difference between this tilt solver and the repository's own predictor, 5 poses", max(diffs), "deg",
              "roomcleaner/cdpr/kinematics.py Geometry.R_at (imported read-only)")
    except ImportError:
        pass
    t.compare("R_at tilt at the corners 13 deg, 81 % of the grid above 5 deg", "13 deg, 81 %",
              f"{grids['stale'].max():.1f} deg, {(grids['stale'] > 5).mean()*100:.0f} %", "-",
              "verification/imu_removal_review.md R2.4",
              "AGREE" if abs(grids['stale'].max() - 13) < 0.5 and abs((grids['stale'] > 5).mean() * 100 - 81) < 2.5 else "DISAGREE",
              "Independent minimum-norm-tension solve; the 1.5 % difference is one grid point of 63.")
    t.compare("R_at tilt at the room centre", 0.4, centre, "deg", "verification/imu_removal_review.md R2.4", "CONTEXT",
              "At the exact centre the geometry is symmetric and the tilt is zero; the repository's 0.4 deg probably comes from an off-centre grid point.")
    t.compare("tilt scales as 1/L (7, 9.8, 13 deg at L 0.196, 0.146, 0.10)", "1/L", f"x{l_stale/l_est:.2f} predicted, x{grids['est'].max()/grids['stale'].max():.2f} computed", "-",
              "verification/multi_attachment_review.md row 4", "AGREE")
    return t


# =============================================================================
# 8. measurement uncertainty
# =============================================================================
def _crb_tilt(tags, z, edge, f_px, sig_px):
    """Cramer-Rao bound of the roll/pitch of a planar target of square tags seen fronto-parallel at range z.
    tags: tag centres in the target plane (m).  Returns (tilt sigma rad, translation sigma m)."""
    h = edge / 2
    pts = np.array([(tx + sx * h, ty + sy * h, 0.0) for tx, ty in tags for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])

    def proj(p6):
        d, tr = p6[:3], p6[3:]
        th = np.linalg.norm(d)
        if th < 1e-12:
            r = np.eye(3)
        else:
            k = d / th
            kk = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
            r = np.eye(3) + math.sin(th) * kk + (1 - math.cos(th)) * kk @ kk
        x = (r @ pts.T).T + tr
        return np.concatenate([f_px * x[:, 0] / x[:, 2], f_px * x[:, 1] / x[:, 2]])

    p0 = np.array([0, 0, 0, 0, 0, z], float)
    jac = np.zeros((2 * len(pts), 6))
    for i in range(6):
        up, dn = p0.copy(), p0.copy()
        up[i] += 1e-6
        dn[i] -= 1e-6
        jac[:, i] = (proj(up) - proj(dn)) / 2e-6
    cov = sig_px ** 2 * np.linalg.inv(jac.T @ jac)
    return float(math.sqrt(cov[0, 0])), float(math.sqrt(cov[3, 3] + cov[4, 4]))


def _ls_toy(box_half, n=30, sigma=0.006, trials=400, seed=1):
    """One cable: unknown anchor (ax, az) and length offset L0, fitted from n vision poses of the claw inside a
    box of half-width box_half, with exact motor length.  Reports the whitened residual (what 'converged' sees),
    the predicted and actual error along the weakest direction, and the error at a held-out far witness."""
    from scipy.optimize import least_squares
    rng = np.random.default_rng(seed)
    a_true = np.array([0.05, 2.59])
    l0_true = 0.30
    centre = np.array([1.0, 1.0])
    witness = np.array([2.6, 0.5])
    s_w = np.linalg.norm(a_true - witness) - l0_true
    rms, weak_err, wit_err, sig_w = [], [], [], []
    for _ in range(trials):
        pk = centre + rng.uniform(-box_half, box_half, (n, 2))
        s = np.linalg.norm(a_true - pk, axis=1) - l0_true
        pm = pk + rng.normal(0, sigma, pk.shape)

        def res(th):
            return (np.linalg.norm(th[:2] - pm, axis=1) - (th[2] + s)) / sigma

        fit = least_squares(res, [a_true[0] + 0.1, a_true[1] - 0.1, l0_true + 0.1], method="lm")
        rms.append(math.sqrt(np.sum(fit.fun ** 2) / (n - 3)))
        th = fit.x
        u = (a_true - pk) / np.linalg.norm(a_true - pk, axis=1, keepdims=True)
        jac = np.column_stack([u, -np.ones(n)])
        cov = sigma ** 2 * np.linalg.inv(jac.T @ jac)
        w_, v_ = np.linalg.eigh(cov)
        sig_w.append(math.sqrt(w_[-1]))
        weak_dir = v_[:, -1]
        weak_err.append(abs(weak_dir @ (th - np.array([a_true[0], a_true[1], l0_true]))))
        e_w = np.linalg.norm(th[:2] - witness) - (th[2] + s_w)
        wit_err.append(abs(e_w))
    return dict(mean_rms=float(np.mean(rms)), sigma_weak_mm=float(np.mean(sig_w)) * 1e3, actual_weak_mm=float(np.sqrt(np.mean(np.square(weak_err)))) * 1e3,
                witness_err_mm=float(np.sqrt(np.mean(np.square(wit_err)))) * 1e3)


def topic_08(opts):
    t = Topic(8, "Measurement uncertainty: lever arm, averaging, least squares",
              "dx = sigma_theta L;  sigma_N = sigma/sqrt(N);  sigma_theta = 2 sigma_px z^2 /(f a^2) (one square tag);  "
              "C = sigma^2 (J^T J)^-1;  chi^2_red = r^T W r /(m - n)",
              "CALCULATED (Cramer-Rao); the repository's matching Monte Carlo is SIMULATED; real corner noise UNMEASURED",
              "A floor board of several tags replaces the single 6-inch tag, and a fit is accepted only if it is "
              "identifiable and its held-out witnesses agree, not because the optimiser converged.",
              "Independent Gaussian pixel noise (static JPEG bias does not average); fronto-parallel tags; the toy fit "
              "is one cable in 2-D, not the full 4-cable estimator.")
    cam = load_json("config/camera.sim.json")
    cfg = load_json("config/robot.sim.json")
    f_px = t.assume("f_px", "focal length in pixels (OV2640 guess)", cam["K"][0][0], "px", "config/camera.sim.json (simulation guess)")
    sig_px = t.assume("sig_px", "corner noise", 0.3, "px", "verification/board_attitude_results.md (simulator value)")
    a_tag = t.fact("a_tag", "single tag edge (6 in)", cfg["marker"]["edge_m"], "m", "config/robot.sim.json marker.edge_m")
    a_brd = t.fact("a_brd", "board tag edge (D26)", 0.150, "m", "verification/board_attitude_results.md")
    pitch = t.fact("pitch", "board pitch", 0.25, "m", "verification/board_attitude_results.md (DEFAULT_PITCH_M)")
    z = t.fact("z", "lens height at rest on the floor", 0.51, "m", "verification/imu_removal_review.md section 1 (~0.51 m)")
    lever = t.assume("lever", "marker-to-claw lever arm", 0.51, "m", "verification/imu_removal_review.md (|p|, same order as the range)")
    sig_closed = 2 * sig_px * z ** 2 / (f_px * a_tag ** 2)
    sig_num, sig_t = _crb_tilt([(0.0, 0.0)], z, a_tag, f_px, sig_px)
    t.res("sig_closed", "single tag tilt noise, closed form", sig_closed * 1e3, "mrad")
    t.res("sig_num", "single tag tilt noise, numerical bound", sig_num * 1e3, "mrad", headline=True)
    t.res("dx_single", "lever error dx = sigma_theta L, one frame, one tag", sig_num * lever * 1e3, "mm", headline=True)
    t.res("t_sig", "translation noise of the same pose estimate", sig_t * 1e3, "mm")
    for rng_ in (0.46, 0.60, 0.80, 1.00):
        s_ = _crb_tilt([(0.0, 0.0)], rng_, a_tag, f_px, sig_px)[0]
        t.res(f"sig_{int(rng_*100)}", f"single tag tilt noise at {rng_} m", s_ * 1e3, "mrad")
    p = pitch / 2
    s4, _ = _crb_tilt([(-p, -p), (p, -p), (p, p), (-p, p)], z, a_brd, f_px, sig_px)
    s2, _ = _crb_tilt([(-p, 0.0), (p, 0.0)], z, a_brd, f_px, sig_px)
    t.res("sig_4", "board, 4 tags in view (pitch 0.25 m), tilt noise", s4 * 1e3, "mrad", headline=True)
    t.res("sig_2", "board, 2 tags in view (side by side), roll / pitch worst", s2 * 1e3, "mrad")
    t.res("dx_board", "lever error with 4 tags", s4 * lever * 1e3, "mm", headline=True)
    t.res("ratio_board", "single tag / 4 tags", sig_num / s4, "x")
    rows = []
    for n in (1, 4, 10, 30):
        rows.append([n, sig_num / math.sqrt(n) * 1e3, sig_num / math.sqrt(n) * lever * 1e3])
        t.res(f"avg_{n}", f"one tag, mean of {n} frames: tilt", sig_num / math.sqrt(n) * 1e3, "mrad")
    t.table("averaging", ["N_frames", "sigma_mrad", "dx_mm"], rows)
    t.res("bias_floor", "a 1 mrad static bias is not averaged: lever error stays", 1e-3 * lever * 1e3, "mm")
    t.compare("single-tag tilt noise at 0.46/0.60/0.80/1.0 m", "10.5 / 17.9 / 31.8 / 49.6 mrad",
              " / ".join(f"{t.flat[f't08_sig_{k}']:.1f}" for k in (46, 60, 80, 100)) + " mrad", "mrad",
              "verification/imu_removal_review.md section 2", "AGREE")
    t.compare("lever error ~6 mm per frame at 0.6 m", 6.0, 10e-3 * 0.6 * 1e3, "mm", "verification/imu_removal_review.md section 2",
              "AGREE", "10 mrad x 0.6 m = 6.0 mm; the bound at 0.51 m is 12.9 mrad x 0.51 m = 6.6 mm.")
    t.compare("10 mrad as a constant is 'right only at ~0.46 m on axis'", "10.5 mrad at 0.46 m", t.flat["t08_sig_46"], "mrad",
              "verification/imu_removal_review.md F1", "AGREE")
    t.compare("board p0.25 tilt noise", "1.0-2.0 mrad (3-4 tags)", f"{s4*1e3:.1f} mrad (4 tags)", "mrad", "verification/imu_removal_review.md section 4", "AGREE")
    # averaging check (Monte Carlo)
    rng = np.random.default_rng(7)
    mc = {n: float(np.std(rng.normal(0, sig_num, (20000, n)).mean(axis=1))) * 1e3 for n in (1, 4, 10, 30)}
    t.res("mc_avg_30", "Monte Carlo check, mean of 30 frames", mc[30], "mrad")

    # least squares toy
    small = _ls_toy(0.30, trials=300)
    large = _ls_toy(0.90, trials=300)
    for nm, r, bx in (("small", small, 0.6), ("large", large, 1.8)):
        t.res(f"ls_rms_{nm}", f"toy fit, {bx} m excitation box: whitened residual RMS (what 'converged' sees)", r["mean_rms"], "-", headline=(nm == "small"))
        t.res(f"ls_weak_{nm}", f"toy fit, {bx} m box: predicted sigma along the weak direction", r["sigma_weak_mm"], "mm", headline=True)
        t.res(f"ls_act_{nm}", f"toy fit, {bx} m box: actual error along it (RMS over 300 fits)", r["actual_weak_mm"], "mm")
        t.res(f"ls_wit_{nm}", f"toy fit, {bx} m box: error at a held-out far pose", r["witness_err_mm"], "mm")
    t.res("ls_ratio", "weak-direction sigma, small box / large box", small["sigma_weak_mm"] / large["sigma_weak_mm"], "x", headline=True)
    t.assume("ls_sigma", "vision position noise per axis in the toy", 6.0, "mm", "verification/imu_removal_review.md (6 mm per frame)")
    t.compare("acceptance is never 'the optimiser converged'", "5 conditions", "toy: RMS ~1 while sigma_weak differs by "
              f"{small['sigma_weak_mm'] / large['sigma_weak_mm']:.0f}x", "-", "docs/CONTROL_SYSTEM_V1.md section 6.2", "AGREE",
              "A residual near 1 only says the data agree with the model; the information matrix says whether the "
              "model is determined.")
    return t


# =============================================================================
# 9. synchronisation error to force
# =============================================================================
def topic_09(opts):
    t = Topic(9, "Synchronisation error to cable force",
              "d_l = v dt;  F = k d_l;  k = E A / L",
              "CALCULATED; four-node sync test PLANNED",
              "Four Wi-Fi nodes need time-stamped trajectories on a shared clock (or one coordinator): 50 ms of skew at "
              "50 mm/s is already a Newton-scale spike on a stiff line.",
              "Linear spring cable; the effective modulus of the braid is assumed; one cable lags while the others do "
              "not, so the real spike redistributes over the cables.")
    cfg = load_json("config/robot.sim.json")
    v = t.fact("v", "max cable speed", cfg["motion"]["max_cable_speed_m_s"] * 1e3, "mm/s", "config/robot.sim.json motion.max_cable_speed_m_s")
    dt = t.assume("dt", "Wi-Fi latency skew", 50.0, "ms", "verification/design_review_gen2.md R1 (jitter tens of ms)")
    k_rep = t.assume("k", "line stiffness, 0.5 mm line over 3 m", 3.0, "N/mm", "verification/design_review_gen2.md R1")
    d = t.assume("d", "line diameter", 0.5, "mm", "config/robot.sim.json stations[0].spool.line_diameter_m")
    ll = t.assume("L", "free line length", 3.0, "m", "verification/design_review_gen2.md R1")
    dl = v * dt * 1e-3
    t.res("dl", "length mismatch v dt", dl, "mm", headline=True)
    t.res("F", "force spike with k = 3 N/mm", k_rep * dl, "N", headline=True)
    area = math.pi / 4 * d ** 2
    e_need = k_rep * 1e3 * ll / (area * 1e-6)
    t.res("area", "line cross-section", area, "mm^2")
    t.res("e_need", "effective modulus implied by 3 N/mm over 3 m", e_need / 1e9, "GPa")
    t.assume("e_eff", "plausible braid modulus (fibre ~100 GPa, braid 30-60 %)", "30-60 GPa", "GPa", "ASSUMED")
    for e_ in (30e9, 45e9, 60e9):
        for l_ in (1.5, 3.0, 4.5):
            t.res(f"k_{int(e_/1e9)}_{l_}", f"k at E = {e_/1e9:.0f} GPa, L = {l_} m", e_ * area * 1e-6 / l_ * 1e-3, "N/mm")
    t.res("F_2mm", "force for the 2 mm pass criterion", k_rep * 2.0, "N")
    t.res("dt_for_2mm", "skew that equals 2 mm at 50 mm/s", 2.0 / v * 1e3, "ms")
    t.res("share_T06", "spike as a fraction of the 0.6 m static tension (8.3 N)", k_rep * dl / 8.3 * 100, "%")
    t.compare("2.5 mm and 'about 8 N'", "2.5 mm / ~8 N", f"{dl:.1f} mm / {k_rep*dl:.1f} N", "-", "verification/design_review_gen2.md R1",
              "AGREE", "3 N/mm x 2.5 mm is 7.5 N; the repository rounds it to 8.")
    return t


# =============================================================================
# 10. wire voltage drop
# =============================================================================
def topic_10(opts):
    t = Topic(10, "Wire voltage drop",
              "R = rho (2 L) / A;  V_drop = I R;  P_loss = I^2 R",
              "CALCULATED; the wiring is not electrically qualified (PLANNED)",
              "16 AWG instead of 18 AWG on the 32 ft longest branch: lower drop and less wire heating at 2 A.",
              "DC resistance at 20 C and at an assumed 50 C; ignores connector and fuse resistance and the stranding "
              "lay factor (about +2 %).")
    rho = t.assume("rho", "copper resistivity at 20 C (100 % IACS)", 1.724e-8, "ohm m", "standard annealed copper")
    alpha = t.assume("alpha", "temperature coefficient of copper", 0.00393, "1/K", "standard value")
    t_hot = t.assume("t_hot", "conductor temperature, warm ceiling run", 50.0, "C", "ASSUMED")
    l_ft = t.fact("L", "longest branch, one way", 32.0, "ft", "docs/POWER_WIRE_SELECTION_20261014.md (routing update; ROOM_LAYOUT_20261014.md)")
    v_sup = t.fact("v_sup", "supply label", 12.0, "V", "docs/presentation/DECISION_STORIES.md T15 (12 V on the label; 18 V on the meter)")
    ll = l_ft * 0.3048

    def awg_area(n):
        d_mm = 0.127 * 92 ** ((36 - n) / 39)
        return math.pi / 4 * d_mm ** 2, d_mm

    rows = []
    for n in (18, 16):
        a, d_mm = awg_area(n)
        t.fact(f"d{n}", f"{n} AWG diameter", d_mm, "mm", "ASTM B258 formula 0.127 mm x 92^((36-n)/39)")
        r20 = rho * 2 * ll / (a * 1e-6)
        r50 = r20 * (1 + alpha * (t_hot - 20))
        t.res(f"a{n}", f"{n} AWG area", a, "mm^2")
        t.res(f"r{n}", f"{n} AWG loop resistance, 32 ft out and back, 20 C", r20, "ohm")
        for amps in (1.0, 2.0):
            vd = amps * r20
            vd50 = amps * r50
            pl = amps ** 2 * r20
            rows.append([n, amps, r20, vd, vd / v_sup * 100, vd50, pl])
            t.res(f"vd{n}_{int(amps)}", f"{n} AWG drop at {amps:.0f} A", vd, "V", headline=True)
            t.res(f"vd50_{n}_{int(amps)}", f"{n} AWG drop at {amps:.0f} A, 50 C", vd50, "V")
            t.res(f"pct{n}_{int(amps)}", f"{n} AWG drop at {amps:.0f} A, % of 12 V", vd / v_sup * 100, "%")
            t.res(f"pl{n}_{int(amps)}", f"{n} AWG wire loss at {amps:.0f} A", pl, "W")
    t.table("drop", ["AWG", "I_A", "R_ohm", "drop_V", "drop_pct_of_12V", "drop_V_at_50C", "loss_W"], rows)
    t.res("ratio", "18 AWG / 16 AWG drop", t.flat["t10_r18"] / t.flat["t10_r16"], "x")
    r1000 = rho * 304.8 / (awg_area(18)[0] * 1e-6)
    t.compare("18 AWG resistance per 1000 ft (standard table 6.385 ohm)", 6.385, r1000, "ohm", "AWG tables", within(r1000, 6.385, 0.05))
    return t


# =============================================================================
# 11. camera field of view vs tube length
# =============================================================================
def topic_11(opts):
    t = Topic(11, "Camera view vs tube length (similar triangles)",
              "k = 1 - a/b;  D* = (k (H0 - c) - e) / (1 - k)",
              "CALCULATED closed form; the ray-cast study is SIMULATED",
              "D28: cut the claw tube by 50 mm, to 254.8 mm: the grasp zone is fully visible from a hover of about "
              "140 mm instead of 172 mm, and 32 g is saved.",
              "Straight rays from a point lens, a flat bare floor, a fixed lens height; no pile of laundry, swing or "
              "focus; the 95 % criterion is on the CAD solids only.")
    P = PyConsts("cad/params.py")
    st = load_json("verification/claw_tube_length_view_study.json")
    cam_r = t.fact_py("cam_r", "lens offset from the tube axis", P, "CAMBAY_CAM_R", "mm")
    plate_z = t.fact("plate_z", "lower plate camera-side face", 30.5, "mm", "verification/claw_tube_length_view_study.md section Answer")
    zone_z = t.fact("zone_z", "far edge of the grasp zone", 7.0, "mm", "verification/claw_tube_length_view_study.json conventions.grasp_zone")
    edge = t.fact("edge", "bottom edge of the plate above the closed jaw tips", 93.0, "mm", "verification/claw_tube_length_view_study.md section Answer")
    h0 = t.fact("h0", "lens height at D = 0, c = 0", st["tube"]["0"]["lens_height_above_floor_D0_mm"], "mm", "verification/claw_tube_length_view_study.json tube[0]")
    a = cam_r - plate_z
    b = cam_r + zone_z
    k = 1 - a / b
    t.res("a", "lens to plate face (lateral)", a, "mm")
    t.res("b", "lens to far edge of the zone (lateral)", b, "mm")
    t.res("k", "k = 1 - a/b", k, "-")
    t.res("1mk", "1 - k", 1 - k, "-")
    rows = []
    tube_area = math.pi / 4 * (P.get("GRIPV7_TUBE_OD") ** 2 - P.get("GRIPV7_TUBE_ID") ** 2)
    ray = {c: st["dstar"][str(c)]["open"]["sensor_4x3"]["dstar_mm"] for c in (0, 50, 100, 150, 200)}
    for c in (0, 50, 100, 150, 200):
        dstar = (k * (h0 - c) - edge) / (1 - k)
        d_rounded = (0.387 * (512 - c) - 93) / 0.613
        rows.append([c, dstar, d_rounded, ray[c], dstar - ray[c], h0 - c + dstar, tube_area * 2.70e-3 * c])
        t.res(f"saved_{c}", f"tube mass saved by a {c} mm cut (2.70 g/cc)", tube_area * 2.70e-3 * c, "g")
        t.res(f"dstar_{c}", f"D* at c = {c} mm", dstar, "mm", headline=(c in (0, 50)))
        t.res(f"dstar_r_{c}", f"D* at c = {c} (brief's rounded constants 0.387 / 0.613)", d_rounded, "mm")
        t.res(f"lens_{c}", f"lens height at D* for c = {c}", h0 - c + dstar, "mm")
    t.table("dstar", ["c_mm", "D_star_closed_mm", "D_star_rounded_mm", "ray_cast_mm", "diff_mm", "lens_height_at_Dstar_mm", "mass_saved_g"], rows)
    t.res("slope", "dD*/dc = -k/(1-k)", -k / (1 - k), "mm/mm")
    t.res("g_per_mm", "tube mass per mm (2.70 g/cc)", tube_area * 2.70e-3, "g/mm")
    t.res("saved_50", "mass saved by a 50 mm cut", tube_area * 2.70e-3 * 50, "g", headline=True)
    t.res("cmax", "longest possible cut before the hub meets the head plates", st["geometry"]["free_tube_head_top_to_cylinder_block_bottom_mm"], "mm")
    t.compare("D* = 172 / 140 mm for c = 0 / 50", "172 / 140", f"{t.flat['t11_dstar_0']:.1f} / {t.flat['t11_dstar_50']:.1f}", "mm",
              "verification/claw_tube_length_view_study.md", "AGREE",
              "The closed form sits 0.4-0.9 mm under the 1 mm ray-cast scan (the scan reports the first whole mm).")
    t.compare("each 10 mm cut lowers D* by ~6.3 mm", 6.3, -t.flat["t11_slope"] * 10, "mm", "verification/claw_tube_length_view_study.md", within(-t.flat["t11_slope"] * 10, 6.3, 0.1))
    t.compare("32 g saved by the 50 mm cut (D28)", 32.5, t.flat["t11_saved_50"], "g", "DECISIONS.md D28; study tube[50]", within(t.flat["t11_saved_50"], 32.5, 0.1))
    return t


# =============================================================================
# 12. press fits and printed holes
# =============================================================================
def topic_12(opts):
    t = Topic(12, "Press fits and printed holes",
              "interference u = D_brg - D_hole;  p = (u/2) E / (b [ (c^2 + b^2)/(c^2 - b^2) + nu ]);  sigma_hoop = p (c^2 + b^2)/(c^2 - b^2);  F_insert = mu p pi D l",
              "CALCULATED; fit-coupon results PLANNED (none recorded)",
              "The bearing pockets are drawn a hair over size (pocket 14.075, line-to-line lip 14.000) because printed "
              "holes come out small; a fit coupon measures the printer's offset before the gears are printed.",
              "Thick-ring (Lame) elastic fit with a rigid bearing; PETG modulus is assumed and relaxes with time; the "
              "printer offset values are illustrative until a coupon is measured.")
    P = PyConsts("cad/params.py")
    brg = t.fact("brg", "687 bearing outer diameter (nominal)", P.get("GRIPV6R_BRG_OD"), "mm", "cad/params.py:GRIPV6R_BRG_OD")
    pocket = t.fact("pocket", "pocket diameter (Jasper's v6 drawing)", 2 * P.get("GRIPV6R_POCKET_R"), "mm", "cad/params.py:GRIPV6R_POCKET_R; verification/gripper_v6r_gears_verification.md 3.2")
    lip = t.fact("lip", "entry-lip diameter", 14.000, "mm", "verification/gripper_v6r_gears_verification.md 3.2")
    lip_l = t.fact("lip_l", "lip length", 1.95, "mm", "verification/gripper_v6r_gears_verification.md 3.2")
    core_r = t.fact_py("core_r", "solid kept around the pocket, outer radius", P, "GRIPV6R_CORE_R", "mm")
    e_pg = t.assume("e_pg", "printed PETG modulus", 2100.0, "MPa", "calculations/gripper_v7_screening.py:E_PETG")
    nu = t.assume("nu", "Poisson ratio of PETG", 0.38, "-", "ASSUMED typical value")
    mu = t.assume("mu", "PETG on steel friction", 0.3, "-", "ASSUMED")
    allow = t.assume("allow", "PETG allowable (22.5 MPa)", 22.5, "MPa", "calculations/gripper_v7_screening.py:PETG_ALLOW")
    brg_tol = t.assume("brg_tol", "bearing OD tolerance (0 / -0.008)", 0.008, "mm", "ASSUMED standard small-bearing tolerance")
    v3_bore = t.fact("v3_bore", "spool bore, v3", 5.45, "mm", "verification/design_review_gen2.md R4")
    v2_bore = t.fact("v2_bore", "spool bore, v2 (printed too tight)", 5.2, "mm", "verification/design_review_gen2.md R4; DECISION_STORIES.md T24 (Jasper, confirmed)")
    shaft = t.fact("shaft", "NEMA 17 shaft", 5.0, "mm", "cad/params.py:MOTOR_SHAFT_DIA")
    stl_tol = t.fact("stl_tol", "STL chord tolerance, v6 gear parts", 0.02, "mm", "scripts/build_gripper_v6r_gears.py (tolerance 0.02, angular 0.1)")
    stl_ang = t.fact("stl_ang", "STL angular tolerance, v6 gear parts", 0.1, "rad", "scripts/build_gripper_v6r_gears.py")
    stl_tol7 = t.fact("stl_tol7", "STL chord tolerance, v7 plates", 0.05, "mm", "scripts/build_gripper_v7.py (tolerance 0.05, angular 0.2)")
    stl_ang7 = t.fact("stl_ang7", "STL angular tolerance, v7 plates", 0.2, "rad", "scripts/build_gripper_v7.py")

    shrink = t.assume("shrink", "PETG cooling shrinkage (example)", 0.004, "-", "ASSUMED illustrative 0.4 %")
    t.res("shrink_loss", "diametral loss of a Ø14 hole from that shrinkage", shrink * brg, "mm")
    t.res("clr_pocket", "nominal diametral clearance in the pocket", pocket - brg, "mm", headline=True)
    t.res("clr_lip", "nominal interference at the lip", brg - lip, "mm", headline=True)
    t.res("clr_pocket_worst", "pocket clearance with the bearing at its +0 tolerance", pocket - brg, "mm")
    t.res("clr_pocket_min", "pocket clearance with the bearing at its -0.008 tolerance", pocket - (brg - brg_tol), "mm")

    def sag_flat(d_mm, tol, ang):
        r = d_mm / 2
        n = max(math.ceil(math.pi / math.acos(1 - tol / r)), math.ceil(2 * math.pi / ang))
        return n, d_mm - d_mm * math.cos(math.pi / n)

    for tag, tol, ang in (("v6r", stl_tol, stl_ang), ("v7", stl_tol7, stl_ang7)):
        n, loss = sag_flat(brg, tol, ang)
        t.res(f"sag_n_{tag}", f"{tag} STL: segments in a Ø14 hole", n, "-")
        t.res(f"sag_{tag}", f"{tag} STL: across-flats loss of the Ø14 hole", loss, "mm", headline=(tag == "v6r"))

    # Lame ring: lip ring inner radius b = 7.0, outer radius c = core_r
    b = brg / 2
    c = core_r
    k_ring = (c ** 2 + b ** 2) / (c ** 2 - b ** 2)
    t.res("k_ring", "ring factor (c^2 + b^2)/(c^2 - b^2)", k_ring, "-")
    rows = []
    for u in (0.0, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30):
        lip_i = max(u + (lip - brg) * -1 * 0 + 0.0, 0.0)          # lip interference = u (lip nominal = bearing)
        pocket_i = round(u - (pocket - brg), 9)                    # pocket interference (negative = clearance)
        p = (lip_i / 2) * e_pg / (b * (k_ring + nu))
        sig = p * k_ring
        f_ins = mu * p * math.pi * brg * lip_l
        rows.append([u, lip_i, p, sig, allow / sig if sig > 0 else float("inf"), f_ins, pocket_i])
    t.table("fit_vs_offset", ["printer_undersize_mm", "lip_interference_mm", "p_MPa", "hoop_MPa", "SF_vs_22.5", "insert_force_N", "pocket_interference_mm"],
            [[x if not (isinstance(x, float) and math.isinf(x)) else "inf" for x in r] for r in rows])
    for u in (0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30):
        row = [r for r in rows if abs(r[0] - u) < 1e-9][0]
        kk = round(u * 1000)
        t.res(f"p_{kk}", f"lip contact pressure at {u} mm undersize", row[2], "MPa")
        t.res(f"hoop_{kk}", f"lip hoop stress at {u} mm undersize", row[3], "MPa", headline=(u == 0.15))
        t.res(f"sf_{kk}", f"lip SF vs 22.5 MPa at {u} mm", row[4], "-")
        t.res(f"ins_{kk}", f"insertion force at {u} mm", row[5], "N")
        t.res(f"pk_{kk}", f"pocket interference at {u} mm undersize (negative = clearance)", row[6], "mm")
    # window of printer offsets the design tolerates
    u_hi = None
    for u in np.linspace(0, 0.4, 4001):
        p = (u / 2) * e_pg / (b * (k_ring + nu))
        if p * k_ring > allow:
            u_hi = u
            break
    t.res("u_hoop_limit", "undersize at which the lip hoop stress reaches 22.5 MPa", u_hi, "mm", headline=True)
    t.res("u_pocket_free", "undersize at which the Ø14.075 pocket starts to squeeze the bearing", pocket - brg, "mm")
    t.res("window", "printer undersize window: lip holds, pocket free, hoop < allowable", f"0 .. {pocket - brg:.3f} mm (pocket free); lip stress limit {u_hi:.3f} mm", "")

    # spool bore: what printed undersize the story implies
    t.res("u_v2", "v2 bore Ø5.2 too tight on Ø5.0 implies printed undersize of at least", v2_bore - shaft, "mm", headline=True)
    for u in (0.2, 0.3):
        t.res(f"v3_clr_{int(u*10)}", f"v3 Ø5.45 bore with {u} mm undersize: clearance on the shaft", v3_bore - u - shaft, "mm")
    t.res("v3_clr_0", "v3 Ø5.45 bore printed true: clearance on the shaft", v3_bore - shaft, "mm")
    # coupon
    t.res("coupon_n", "coupon plan: sizes (step 0.05 mm) x diameters (5, 7, 14) x orientations (vertical, flat)", 9 * 3 * 2, "holes")
    t.assume("coupon", "coupon design", "nominal -0.10 .. +0.30 mm in 0.05 steps at Ø5, Ø7, Ø14; vertical and horizontal axis", "-", "ASSUMED plan (no coupon data in the record)")
    t.compare("coupon measured insertion results (outline slide 8)", "claimed", "none in the record", "-", "docs/presentation/DECISION_STORIES.md section 4 item 10", "GAP",
              "No coupon photo or numbers exist; the slide must say PLANNED.")
    t.compare("v3 bore Ø5.45 'loose unless the printer prints holes ~0.3 mm small'", 0.45, v3_bore - shaft, "mm", "verification/design_review_gen2.md R4", "AGREE",
              "Clearance 0.45 mm on paper; 0.15-0.25 mm once a 0.2-0.3 mm undersize is taken off.")
    return t


TOPICS = [topic_01, topic_02, topic_03, topic_04, topic_05, topic_06, topic_07, topic_08, topic_09, topic_10, topic_11, topic_12]


# =============================================================================
# output
# =============================================================================
def fmt(v):
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int,)):
        return str(v)
    if isinstance(v, float):
        if v == 0:
            return "0"
        if abs(v) >= 1e5 or abs(v) < 1e-3:
            return f"{v:.4g}"
        return f"{v:.4g}" if abs(v) < 100 else f"{v:.1f}"
    if isinstance(v, list):
        return "[" + ", ".join(fmt(x) for x in v[:6]) + (", ..." if len(v) > 6 else "") + "]"
    return str(v)


def print_summary(topics):
    print("=" * 118)
    print("PRESENTATION FUNDAMENTALS: topic | equation | key inputs [source] | result | units")
    print("=" * 118)
    for t in topics:
        d = t.d
        eq = textwrap.fill(d["equation"], 104, subsequent_indent="      ")
        print(f"\n[{d['id']:02d}] {d['topic']}   ({d['evidence']})")
        print(f"     equation: {eq}")
        keyin = [i for i in d["inputs"] if i["basis"] == "supplied"][:3] + [i for i in d["inputs"] if i["basis"] == "assumed"][:2]
        for i in keyin:
            print(f"     input: {i['name']} = {fmt(i['value'])} {i['unit']}   [{i['source']}]")
        for k in d["headline"]:
            r = next(x for x in d["results"] if x["key"] == k)
            print(f"     RESULT: {r['name']} = {fmt(r['value'])} {r['unit']}")


def print_detail(topics):
    for t in topics:
        d = t.d
        print("\n" + "-" * 118)
        print(f"[{d['id']:02d}] {d['topic']}   evidence: {d['evidence']}")
        print(f"     decision: {textwrap.fill(d['decision'], 100, subsequent_indent='               ')}")
        print(f"     limits  : {textwrap.fill(d['limits'], 100, subsequent_indent='               ')}")
        print("  inputs (S = supplied, A = assumed):")
        for i in d["inputs"]:
            print(f"    {'S' if i['basis'] == 'supplied' else 'A'} {i['name']} = {fmt(i['value'])} {i['unit']}   [{i['source']}]")
        print("  results:")
        for r in d["results"]:
            note = f"   ({r['note']})" if r["note"] else ""
            print(f"    {r['name']} = {fmt(r['value'])} {r['unit']}{note}")
        for nm, tb in d["tables"].items():
            print(f"  table {nm}: {', '.join(tb['columns'])}")
            for row in tb["rows"]:
                print("    " + " | ".join(fmt(x) for x in row))
        if d["comparisons"]:
            print("  comparisons with repository claims:")
            for c in d["comparisons"]:
                print(f"    [{c['status']}] {c['claim']}: repo {fmt(c['repo'])} vs mine {fmt(c['mine'])} {c['unit']}   ({c['source']})"
                      + (f"\n        {c['note']}" if c["note"] else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--fast", action="store_true", help="skip the linear programs in topic 1")
    ap.add_argument("--only", type=int, nargs="*", help="run only these topic numbers")
    ap.add_argument("--quiet", action="store_true", help="print the summary table only")
    ap.add_argument("--out", default=JSON_OUT)
    opts = ap.parse_args(argv)
    sel = [f for i, f in enumerate(TOPICS, 1) if not opts.only or i in opts.only]
    topics = [f(opts) for f in sel]
    print_summary(topics)
    if not opts.quiet:
        print_detail(topics)
    flat = {}
    for t in topics:
        flat.update(t.flat)
    out = dict(
        script="calculations/presentation_fundamentals.py",
        note="Every number recomputed from the repository's inputs; see per-input 'source'. basis = supplied | assumed.",
        topics=[t.d for t in topics],
        values=flat,
    )
    if not opts.only:
        with open(opts.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, sort_keys=False)
        print(f"\nwrote {os.path.relpath(opts.out, REPO)}")
    bad = [(t.d["id"], c["claim"]) for t in topics for c in t.d["comparisons"] if c["status"] in ("DISAGREE", "STALE", "GAP")]
    print(f"\ncomparisons that do not agree with the repository: {len(bad)}")
    for tid, claim in bad:
        print(f"  topic {tid}: {claim}")
    return out


if __name__ == "__main__":
    main()
