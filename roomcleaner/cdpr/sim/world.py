"""Physical truth for simulation: cables, claw, floor, beads, marker, camera.

Quasi-static model (the claw is slow and light):

* Each cable has a free (unstretched) length ``ell_i`` set by its spool's
  physical motor position through the TRUE spool geometry. It carries tension
  ``k_i * max(0, d_i - ell_i)`` with ``k_i = EA / ell_i`` (no compression,
  no sag), ``d_i`` the straight distance from exit point to attachment.
* Suspended: the claw is a RIGID BODY (6 DOF) hung from the four attachment
  points b_i (inner mouths of the corner holes of the electrical box): it sits at
  the minimum of gravity (at the CoM) + cable strain energy, found by a damped
  (Levenberg-Marquardt) Newton with an Armijo line search and an exact analytic
  Hessian, warm-started from the previous state. Non-convergence is REPORTED
  (``World.eq_failures``, event ``no_equilibrium``, ``strict`` raises) and the
  previous state is kept: a non-equilibrium state is never returned. Roll/pitch
  follow from the statics; yaw is whatever the (weak) line geometry leaves it, so
  length errors make it drift realistically (see tests/cdpr/test_rigid_body.py).
  With a single common attachment point at the CoM the orientation is irrelevant
  and the claw is the original 3-DOF point (R fixed).
* On the floor: static friction ``mu * N`` holds it until the horizontal
  cable pull exceeds it, then it slides to the limit. A net upward pull larger
  than its weight lifts it.
* Bead switch i is actuated when ``ell_i <= trigger_i`` (bead fixed on the
  cable near the claw; the switch is at the exit).

The model deliberately differs from the controller's knowledge: anchors,
marker pose, line totals, payout scale and bead positions are the truth here
and only priors in the configuration.
"""
from __future__ import annotations

import math

import numpy as np

from ..frames import inv_T, make_T, planar_T, rot_z, rotvec_to_matrix
from ..spool import LayeredSpool
from ..vision.marker import MarkerObservation

G = 9.81


class World:
    def __init__(self, cfg, stations: dict, *, anchors, T_R_M, claw_xy, claw_yaw=0.0, slack_m=(0.08,) * 4,
                 mass_kg=None, EA_n=20000.0, mu=0.4, bead_trigger_m=None, payout_scale=(1.0,) * 4,
                 line_total_m=None, seed=0, update_s=0.005, suspended_at=None, bead_noise_m=0.0003):
        self.cfg = cfg
        self.stations = stations
        self.ids = list(cfg.ids)
        self.anchors = np.asarray(anchors, float)
        self.T_R_M = np.asarray(T_R_M, float)
        self.attach = cfg.attachment_points()
        self.mass = cfg.claw.mass_kg if mass_kg is None else mass_kg
        self.EA = EA_n
        self.mu = mu
        self.rng = np.random.default_rng(seed)
        self.update_s = update_s
        self._acc = 0.0
        self.z_floor = -float(cfg.claw.lowest_point_body_m[2])     # body origin height when resting
        self.low_body = np.asarray(cfg.claw.lowest_point_body_m, float)
        self.com_claw = np.zeros(3) if cfg.claw.com_body_m is None else np.asarray(cfg.claw.com_body_m, float)
        # orientation matters only if the attachment is spaced or the CoM is off the (common) attachment point
        self.rigid = bool(np.max(np.abs(self.attach - self.attach[0])) > 1e-9
                          or np.max(np.abs(self.com_claw - self.attach[0])) > 1e-9)
        self.strict = False                 # True: non-convergence raises instead of being reported
        self.eq_failures = 0
        self.eq_worst_residual = 0.0
        self.eq_iters = 0
        self.p = np.array([claw_xy[0], claw_xy[1], self.z_floor])
        self.R = rot_z(claw_yaw)
        self.on_floor = True
        stretch = np.zeros(4)
        if suspended_at is not None:
            from ..kinematics import Geometry, tension_distribution
            self.p = np.asarray(suspended_at, float)
            self.on_floor = False
            T = tension_distribution(Geometry(self.anchors, self.attach, com=self.com_claw), self.p, self.mass,
                                     t_min=1.0, t_max=1e3, R=self.R).tensions
            stretch = -self.dist() * T / (self.EA + T)          # ell = d * EA / (EA + T)
            slack_m = stretch
        self.bead = np.array([s.bead.trigger_length_m for s in cfg.stations]) if bead_trigger_m is None \
            else np.asarray(bead_trigger_m, float)
        self.spools, self.phi0, self.line_total = [], [], []
        for k, s in enumerate(cfg.stations):
            sc = s.spool
            sp = LayeredSpool(sc.core_radius_m, sc.drum_width_m, sc.flange_radius_m, sc.line_diameter_m,
                              sc.packing, payout_scale[k])
            lt = sc.line_total_m if line_total_m is None else line_total_m[k]
            d = self.dist()[k]
            ell = d + slack_m[k]
            self.spools.append(sp)
            self.line_total.append(lt)
            self.phi0.append(sp.angle_from_wound(lt - ell))         # angle at physical motor = 0
        self.bead_noise = bead_noise_m
        self._bead_jit = self.rng.normal(0, bead_noise_m, 4)
        self._sw = [False] * 4
        for k, sid in enumerate(self.ids):
            stations[sid].switch_fn = (lambda kk=k: self._switch(kk))
        self.tension = np.zeros(4)
        self.events = []
        self.items: list = []           # {"id","xy","height","mass","state","last_drop"}
        self.held = None
        self.hamper = None              # (xy, radius) for the delivery check
        self.base_mass = self.mass

    def add_item(self, iid, xy, *, height=0.05, mass=0.5):
        self.items.append({"id": iid, "xy": np.asarray(xy, float), "height": height, "mass": mass,
                           "state": "floor", "last_drop": None})

    def grip(self, close: bool, reach_xy=0.06, reach_z=0.03):
        low = self.lowest_z()                    # lowest claw point above the floor
        if close and self.held is None:
            for it in self.items:
                if it["state"] == "floor" and np.linalg.norm(it["xy"] - self.p[:2]) <= reach_xy \
                        and low <= it["height"] + reach_z:
                    it["state"] = "held"
                    self.held = it
                    self.mass = self.base_mass + it["mass"]
                    break
        elif not close and self.held is not None:
            it = self.held
            it["xy"] = self.p[:2].copy()
            it["last_drop"] = it["xy"].copy()
            in_hamper = self.hamper is not None and np.linalg.norm(it["xy"] - self.hamper[0]) <= self.hamper[1]
            it["state"] = "hamper" if in_hamper else "floor"
            self.held = None
            self.mass = self.base_mass

    def _switch(self, k):
        on = bool(self.ell()[k] <= self.bead[k] + self._bead_jit[k])
        if self._sw[k] and not on:                 # new trigger point for the next actuation
            self._bead_jit[k] = self.rng.normal(0, self.bead_noise)
        self._sw[k] = on
        return on

    # ---------------------------------------------------------------- truth
    def attach_world(self, p=None):
        p = self.p if p is None else p
        return p + self.attach @ self.R.T

    def dist(self, p=None):
        return np.linalg.norm(self.anchors - self.attach_world(p), axis=1)

    def ell(self):
        out = np.zeros(4)
        for k, sid in enumerate(self.ids):
            st = self.stations[sid]
            phi = self.phi0[k] - 2 * math.pi * st.motor / st.spr
            out[k] = self.line_total[k] - self.spools[k].wound_from_angle(phi)
        return out

    def true_L0(self, sid) -> float:
        """External free length at the station's current epoch position 0."""
        k = self.ids.index(sid)
        st = self.stations[sid]
        phi = self.phi0[k] - 2 * math.pi * st.pos_base / st.spr
        return self.line_total[k] - self.spools[k].wound_from_angle(phi)

    def T_R_B(self):
        return make_T(self.R, self.p)

    def T_M_B(self):
        return inv_T(self.T_R_M) @ self.T_R_B()

    # ---------------------------------------------------------------- physics
    def lowest_z(self, p=None, R=None) -> float:
        """Height of the lowest claw point (the CAD jaw point) above the floor."""
        p = self.p if p is None else p
        R = self.R if R is None else R
        return float((p + R @ self.low_body)[2])

    def _com(self):
        """Centre of mass in the body frame: the claw plus a held item at the jaws."""
        extra = self.mass - self.base_mass
        if extra <= 1e-12:
            return self.com_claw
        return (self.base_mass * self.com_claw + extra * self.low_body) / self.mass

    def _forces(self, p, ell, R=None):
        R = self.R if R is None else R
        q = p + self.attach @ R.T
        d_vec = self.anchors - q
        d = np.linalg.norm(d_vec, axis=1)
        n = d_vec / d[:, None]
        k = self.EA / ell
        stretch = np.maximum(0.0, d - ell)
        T = k * stretch
        return T, n, d, k

    @staticmethod
    def _skew(r):
        z = np.zeros(r.shape[:-1])
        return np.stack([np.stack([z, -r[..., 2], r[..., 1]], -1),
                         np.stack([r[..., 2], z, -r[..., 0]], -1),
                         np.stack([-r[..., 1], r[..., 0], z], -1)], -2)

    def _energy(self, p, R, ell, m, c):
        q = p + self.attach @ R.T
        d = np.linalg.norm(self.anchors - q, axis=1)
        st = np.maximum(d - ell, 0.0)
        return m * G * (p[2] + (R @ c)[2]) + 0.5 * float(np.sum(self.EA / ell * st * st))

    def _grad_hess(self, p, R, ell, m, c, rot):
        """Gradient and Hessian of the potential energy wrt the twist (dp, w): p <- p + dp, R <- exp([w]x) R."""
        r = self.attach @ R.T                                           # (4,3) attachment offsets, world frame
        d_vec = self.anchors - (p + r)
        d = np.linalg.norm(d_vec, axis=1)
        n = d_vec / d[:, None]
        k = self.EA / ell
        T = k * np.maximum(d - ell, 0.0)
        taut = T > 0
        g = -T[:, None] * n                                             # dU/dq_i
        gc = np.array([0.0, 0.0, m * G])                                # dU/dq_c (gravity at the CoM)
        rc = R @ c
        n_tw = 6 if rot else 3
        grad = np.zeros(n_tw)
        grad[:3] = g.sum(0) + gc
        H = np.zeros((n_tw, n_tw))
        Hq = np.zeros((4, 3, 3))
        w_ = np.where(taut, k * ell / d, 0.0)
        Hq[:] = (np.where(taut, k * (1 - ell / d), 0.0))[:, None, None] * np.eye(3) \
            + w_[:, None, None] * n[:, :, None] * n[:, None, :]
        H[:3, :3] = Hq.sum(0)
        if rot:
            grad[3:] = np.cross(r, g).sum(0) + np.cross(rc, gc)
            S = self._skew(r)                                           # [r]x
            H[:3, 3:] = -np.einsum("iab,ibc->ac", Hq, S)
            H[3:, :3] = H[:3, 3:].T
            Hww = np.einsum("iba,ibc,icd->ad", S, Hq, S)                # [r]x^T Hq [r]x
            for gi, ri in list(zip(g, r)) + [(gc, rc)]:                 # second-order rotation terms
                Hww += 0.5 * (np.outer(gi, ri) + np.outer(ri, gi)) - float(gi @ ri) * np.eye(3)
            H[3:, 3:] = Hww
        return grad, H

    def _equilibrium(self, p0, R0, ell, *, max_iter=120, tol_f=1e-6, tol_m=1e-7):
        """Minimum of the potential energy near (p0, R0): returns (p, R, ok, residual)."""
        m, c = self.mass, self._com()
        rot = self.rigid
        p, R = np.array(p0, float), np.array(R0, float)
        U = self._energy(p, R, ell, m, c)
        lam = 1e-9
        scale = m * G
        for it in range(max_iter):
            grad, H = self._grad_hess(p, R, ell, m, c, rot)
            if np.max(np.abs(grad[:3])) < tol_f and (not rot or np.max(np.abs(grad[3:])) < tol_m):
                self.eq_iters = it
                return p, R, True, float(np.max(np.abs(grad)))
            hdiag = float(np.max(np.diag(H))) if np.max(np.diag(H)) > 0 else 1.0
            for _ in range(40):                                         # raise damping until the step descends
                try:
                    step = -np.linalg.solve(H + lam * hdiag * np.eye(len(grad)), grad)
                except np.linalg.LinAlgError:
                    lam = max(lam * 10, 1e-6)
                    continue
                dp = step[:3]
                nd = np.linalg.norm(dp)
                if nd > 0.05:
                    step = step * (0.05 / nd)
                if rot:
                    nw = np.linalg.norm(step[3:])
                    if nw > 0.1:
                        step = step * (0.1 / nw)
                slope = float(grad @ step)
                if slope >= 0:                                          # not a descent direction: damp harder
                    lam = max(lam * 10, 1e-6)
                    continue
                a = 1.0
                ok = False
                for _ in range(30):                                     # Armijo backtracking
                    pn = p + a * step[:3]
                    Rn = rotvec_to_matrix(a * step[3:]) @ R if rot else R
                    Un = self._energy(pn, Rn, ell, m, c)
                    if Un <= U + 1e-4 * a * slope + 1e-14 * abs(U):      # last term: float round-off floor
                        ok = True
                        break
                    a *= 0.5
                if ok:
                    p, R, U = pn, Rn, Un
                    lam = max(lam * 0.3, 1e-12)
                    break
                lam = max(lam * 10, 1e-6)
            else:
                break                                                   # no descent found: report
        grad, _ = self._grad_hess(p, R, ell, m, c, rot)
        resid = float(np.max(np.abs(grad)))
        # at the round-off floor of the energy no further descent is measurable: accept a residual of <= 1e-4 N / N m
        return p, R, bool(resid < 1e-4), resid

    def _hang(self, p0, ell, R0=None):
        """Equilibrium position (compat wrapper): the claw hangs as a rigid body from the current orientation."""
        p, R, ok, resid = self._equilibrium(p0, self.R if R0 is None else R0, ell)
        self._last_hang = (R, ok, resid)
        return p

    def _hang_checked(self, p0, R0, ell):
        """(p, R, ok): equilibrium or, if the minimiser fails, the state is NOT updated (reported instead)."""
        p, R, ok, resid = self._equilibrium(p0, R0, ell)
        self.eq_worst_residual = max(self.eq_worst_residual, resid) if ok else self.eq_worst_residual
        if not ok:
            self.eq_failures += 1
            self.events.append(("no_equilibrium", np.array(p0, float), resid))
            if self.strict:
                raise RuntimeError(f"World: no static equilibrium found (residual {resid:.3g}); state kept")
            return np.array(p0, float), np.array(R0, float), False
        return p, R, True

    def settle(self):
        ell = self.ell()
        if not self.on_floor:
            p, R, ok = self._hang_checked(self.p, self.R, ell)
            if ok:
                if self.lowest_z(p, R) <= 1e-12:
                    self.on_floor = True
                    yaw = math.atan2(R[1, 0], R[0, 0])
                    self.R = rot_z(yaw)                  # rests flat on the floor (tilt released)
                    self.p = np.array([p[0], p[1], self.z_floor])
                    self.events.append(("landed", self.p.copy()))
                else:
                    self.p, self.R = p, R
        if self.on_floor:
            T, n, d, k = self._forces(self.p, ell)
            F = (T[:, None] * n).sum(0)
            if F[2] > self.mass * G:
                p, R, ok = self._hang_checked(self.p + [0, 0, 1e-4], self.R, ell)
                if ok and self.lowest_z(p, R) > 1e-12:
                    self.on_floor = False
                    self.p, self.R = p, R
                    self.events.append(("lifted", self.p.copy()))
                elif ok:
                    self.p = np.array([p[0], p[1], self.z_floor])
            else:
                self._slide(ell)
        self.tension = self._forces(self.p, ell)[0]

    def _slide(self, ell):
        for _ in range(20):
            T, n, d, k = self._forces(self.p, ell)
            F = (T[:, None] * n).sum(0)
            Fh = F[:2]
            N = self.mass * G - F[2]
            excess = np.linalg.norm(Fh) - self.mu * max(N, 0.0)
            if excess <= 1e-6:
                return
            # move along the pull until friction balances (stiffness-scaled step)
            kh = sum(k[i] for i in range(4) if T[i] > 0)
            step = min(excess / max(kh, 1.0), 0.01)
            self.p[:2] += Fh / np.linalg.norm(Fh) * step

    def step(self, t_us, dt_s):
        self._acc += dt_s
        if self._acc + 1e-12 >= self.update_s:
            self._acc = 0.0
            self.settle()


class FloorBoard:
    """STUDY HOOK (floor-reference study, not used by default): a grid of
    AprilTags laid out on the floor around the marker origin (the marker frame
    is the centre of the grid; the centre tag coincides with the single marker).

    * the reference counts as "seen" when ANY tag lies fully in the image and is
      large enough (not only the centre tag);
    * the effective span ``edge_eff`` that sets the depth-noise model is derived
      from the tags currently in view (``span_mode``): "extent" = geometric mean
      of the x/y extents of the visible tags' outer corners (optimistic upper
      bound); "rms" = sqrt(2) x RMS corner radius about the visible-corner
      centroid (conservative for a filled grid). Both reduce to the tag edge for
      a single tag;
    * ``layout_err_m`` > 0 places each tag at a random xy offset (sigma per axis)
      and a yaw offset (sigma = layout_err / tag_edge rad) that the estimator
      does NOT know: it assumes the nominal grid, so the board pose it infers is
      biased by the (pose-dependent) mean of the visible tags' errors.
    """

    def __init__(self, nx, ny, pitch_m, tag_edge_m, *, layout_err_m=0.0, span_mode="extent", seed=0):
        xs = (np.arange(nx) - (nx - 1) / 2) * pitch_m
        ys = (np.arange(ny) - (ny - 1) / 2) * pitch_m
        self.centres = np.array([[x, y, 0.0] for y in ys for x in xs])
        self.edge = float(tag_edge_m)
        self.span_mode = span_mode
        h = self.edge / 2
        self.local = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], float)
        self.corners = self.centres[:, None, :] + self.local[None]          # (n, 4, 3) board frame
        rng = np.random.default_rng(seed + 777)
        n = len(self.centres)
        self.dxy = rng.normal(0, layout_err_m, (n, 2)) if layout_err_m > 0 else np.zeros((n, 2))
        self.dpsi = rng.normal(0, layout_err_m / self.edge, n) if layout_err_m > 0 else np.zeros(n)
        self.layout_err_m = layout_err_m

    @property
    def extent_m(self):
        c = self.corners.reshape(-1, 3)
        return float(c[:, 0].max() - c[:, 0].min()), float(c[:, 1].max() - c[:, 1].min())

    def visible_tags(self, camera, T_B_C, T_M_B, *, min_side_px, margin_px=4):
        """Indices of the tags fully in view and at least ``min_side_px`` large."""
        T_C_M = inv_T(np.asarray(T_M_B, float) @ np.asarray(T_B_C, float))
        pc = self.corners @ T_C_M[:3, :3].T + T_C_M[:3, 3]                  # (n, 4, 3)
        n = len(pc)
        ok = np.all(pc[:, :, 2] > 0.05, axis=1)
        out = []
        if not ok.any():
            return out
        idx = np.flatnonzero(ok)
        uv = camera.project(pc[idx].reshape(-1, 3)).reshape(len(idx), 4, 2)
        for j, k in enumerate(idx):
            if not np.all(camera.in_image(uv[j], margin_px)):
                continue
            side = np.mean([np.linalg.norm(uv[j][m] - uv[j][(m + 1) % 4]) for m in range(4)])
            if side >= min_side_px:
                out.append(int(k))
        return out

    def visible(self, camera, T_B_C, T_M_B, *, min_side_px, margin_px=4) -> bool:
        return bool(self.visible_tags(camera, T_B_C, T_M_B, min_side_px=min_side_px, margin_px=margin_px))

    def edge_eff_for(self, ks) -> float:
        c = self.corners[list(ks)].reshape(-1, 3)
        if self.span_mode == "rms":
            r = np.sqrt(np.mean(np.sum((c[:, :2] - c[:, :2].mean(0)) ** 2, axis=1)))
            return float(math.sqrt(2.0) * r)
        ex = c[:, 0].max() - c[:, 0].min()
        ey = c[:, 1].max() - c[:, 1].min()
        return float(math.sqrt(ex * ey))

    def edge_eff(self, camera, T_B_C, T_M_B, *, min_side_px, margin_px=4):
        """Effective span for the excitation design's predicted covariance."""
        ks = self.visible_tags(camera, T_B_C, T_M_B, min_side_px=min_side_px, margin_px=margin_px)
        return self.edge_eff_for(ks) if ks else self.edge

    def biased_T_C_M(self, T_C_M, ks):
        """Board pose a nominal-grid estimator infers from the visible tags when
        the printed layout deviates from nominal (mean of per-tag results)."""
        if self.layout_err_m <= 0:
            return T_C_M
        ds, psis = [], []
        for k in ks:
            c = self.centres[k]
            T_act = planar_T(c[0] + self.dxy[k, 0], c[1] + self.dxy[k, 1], 0.0) @ rot_z4(self.dpsi[k])
            T_nom_inv = inv_T(planar_T(c[0], c[1], 0.0))
            D = T_act @ T_nom_inv
            ds.append(D[:3, 3])
            psis.append(self.dpsi[k])
        D = np.eye(4)
        D[:3, :3] = rot_z(float(np.mean(psis)))
        D[:3, 3] = np.mean(ds, axis=0)
        return T_C_M @ D


def rot_z4(a):
    T = np.eye(4)
    T[:3, :3] = rot_z(a)
    return T


class SimCamera:
    """Marker observations from the true claw pose (no image rendering):
    visibility and size checks as the detector applies them, pose noise from
    the same error model, optional dropouts and stale frames."""

    def __init__(self, world: World, camera, T_B_C, edge_m, *, pixel_sigma=0.3, rot_sigma=0.002,
                 dropout=0.0, min_side_px=40.0, seed=0, bias_m=(0, 0, 0), board_span_m=None, board=None):
        self.w = world
        self.cam = camera
        self.T_B_C = np.asarray(T_B_C, float)
        self.edge = edge_m
        self.pixel_sigma = pixel_sigma
        self.rot_sigma = rot_sigma
        self.dropout = dropout
        self.min_side = min_side_px
        self.rng = np.random.default_rng(seed)
        self.bias = np.asarray(bias_m, float)
        self.frame = 0
        # A marker board (several tags at known offsets) behaves like one large
        # marker for accuracy once the camera is high enough to see all of it.
        self.board_span = board_span_m
        self.covered = False          # injected: marker hidden (laundry on it, person walking)
        self.board = board            # STUDY HOOK: FloorBoard (multi-tag floor reference); None = single marker

    def _observe_board(self, t_us) -> MarkerObservation:
        """STUDY HOOK: observation of a multi-tag floor board (see FloorBoard)."""
        T_C_M = inv_T(self.w.T_M_B() @ self.T_B_C)
        if self.covered:
            return MarkerObservation(False, "marker not found", frame_id=self.frame, capture_us=t_us)
        T_M_B = self.w.T_M_B()
        ks = self.board.visible_tags(self.cam, self.T_B_C, T_M_B, min_side_px=self.min_side)
        if not ks:
            return MarkerObservation(False, "marker not found", frame_id=self.frame, capture_us=t_us)
        if self.rng.random() < self.dropout:
            return MarkerObservation(False, "ambiguous pose", frame_id=self.frame, capture_us=t_us)
        edge = self.board.edge_eff_for(ks)
        T_C_M = self.board.biased_T_C_M(T_C_M, ks)
        z = float(T_C_M[2, 3])
        lat = self.pixel_sigma * z / self.cam.fx
        dep = 2 * self.pixel_sigma * z * z / (self.cam.fx * edge)
        noise_t = self.rng.normal(0, 1, 3) * [lat, lat, dep] + self.bias
        from ..frames import rotvec_to_matrix
        Rn = rotvec_to_matrix(self.rng.normal(0, self.rot_sigma, 3))
        T = T_C_M.copy()
        T[:3, :3] = Rn @ T[:3, :3]
        T[:3, 3] += noise_t
        uv = self.cam.project(self.board.corners[ks[0]] @ T_C_M[:3, :3].T + T_C_M[:3, 3])
        side = float(np.mean([np.linalg.norm(uv[k] - uv[(k + 1) % 4]) for k in range(4)]))
        return MarkerObservation(True, "", T, 0.3, 50.0, side, uv, frame_id=self.frame, capture_us=t_us,
                                 edge_eff=edge)

    def observe(self, t_us) -> MarkerObservation:
        self.frame += 1
        if self.board is not None:
            return self._observe_board(t_us)
        T_C_M = inv_T(self.w.T_M_B() @ self.T_B_C)
        h = self.edge / 2
        pts = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]])
        pc = pts @ T_C_M[:3, :3].T + T_C_M[:3, 3]
        if self.covered:
            return MarkerObservation(False, "marker not found", frame_id=self.frame, capture_us=t_us)
        if np.any(pc[:, 2] <= 0.05):
            return MarkerObservation(False, "marker behind camera", frame_id=self.frame, capture_us=t_us)
        uv = self.cam.project(pc)
        if not np.all(self.cam.in_image(uv, 4)):
            return MarkerObservation(False, "marker not found", frame_id=self.frame, capture_us=t_us)
        side = float(np.mean([np.linalg.norm(uv[k] - uv[(k + 1) % 4]) for k in range(4)]))
        if side < self.min_side:
            return MarkerObservation(False, f"marker too small ({side:.0f} px)", side_px=side,
                                     frame_id=self.frame, capture_us=t_us)
        if self.rng.random() < self.dropout:
            return MarkerObservation(False, "ambiguous pose", frame_id=self.frame, capture_us=t_us)
        z = float(T_C_M[2, 3])
        edge = self.edge
        if self.board_span:
            hb = self.board_span / 2
            bp = np.array([[-hb, hb, 0], [hb, hb, 0], [hb, -hb, 0], [-hb, -hb, 0]]) @ T_C_M[:3, :3].T + T_C_M[:3, 3]
            if np.all(bp[:, 2] > 0.05) and np.all(self.cam.in_image(self.cam.project(bp), 4)):
                edge = self.board_span
        lat = self.pixel_sigma * z / self.cam.fx
        dep = 2 * self.pixel_sigma * z * z / (self.cam.fx * edge)
        noise_t = self.rng.normal(0, 1, 3) * [lat, lat, dep] + self.bias
        from ..frames import rotvec_to_matrix
        Rn = rotvec_to_matrix(self.rng.normal(0, self.rot_sigma, 3))
        T = T_C_M.copy()
        T[:3, :3] = Rn @ T[:3, :3]
        T[:3, 3] += noise_t
        return MarkerObservation(True, "", T, 0.3, 50.0, side, uv, frame_id=self.frame, capture_us=t_us,
                                 edge_eff=edge)


class SimClaw:
    """Claw node: IMU tilt, battery, servo; camera via SimCamera."""

    def __init__(self, world: World, camera: SimCamera, *, tilt_noise=0.002, seed=0):
        self.w = world
        self.camera = camera
        self.rng = np.random.default_rng(seed)
        self.tilt_noise = tilt_noise
        self.grip_closed = False
        self.holding = None           # simulated item id in the claw
        self.battery_v = 7.8
        self.online = True

    def roll_pitch(self):
        """Body roll/pitch relative to gravity (IMU), radians."""
        from ..frames import matrix_to_rpy
        r, p, _ = matrix_to_rpy(self.w.R)
        return (r + float(self.rng.normal(0, self.tilt_noise)), p + float(self.rng.normal(0, self.tilt_noise)))

    def tilt(self) -> float:
        r, p = self.roll_pitch()
        return float(math.hypot(r, p))

    def grip(self, close: bool):
        self.grip_closed = close
        self.w.grip(close)
        return True

    def status(self) -> dict:
        return {"online": self.online, "battery_v": self.battery_v, "grip_closed": self.grip_closed,
                "tilt_rad": self.tilt()}


def default_world(cfg, stations, *, seed=0, anchor_err_m=0.04, marker_xy=None, marker_yaw_err=0.15,
                  claw_offset=(0.0, 0.0), swap_stations=None, **kw):
    """A plausible truth around the configuration's priors. ``swap_stations``
    (i, j) wires station i's cable to corner j and vice versa (an installation
    error the startup must catch)."""
    rng = np.random.default_rng(seed + 1000)
    anchors = cfg.anchor_priors() + rng.normal(0, anchor_err_m, (4, 3))
    if swap_stations is not None:
        i, j = swap_stations
        anchors[[i, j]] = anchors[[j, i]]
    mxy = cfg.room_m[:2] / 2 + rng.normal(0, 0.15, 2) if marker_xy is None else np.asarray(marker_xy)
    yaw = cfg.marker.heading_prior_rad + rng.normal(0, marker_yaw_err)
    T_R_M = planar_T(mxy[0], mxy[1], yaw)
    # the claw is placed upright with the marker under the camera
    cam_xy = (T_R_M @ np.r_[0, 0, 0, 1])[:2]
    cam_off_body = cfg.claw.T_body_cam[:2, 3] if cfg.claw.T_body_cam is not None else np.zeros(2)
    claw_yaw = float(rng.uniform(-math.pi, math.pi))
    if cfg.claw.attachment == "spaced":
        # the four lines are physically tied to fixed corners of the box and the claw is set down roughly facing the
        # way it hangs (a line cannot pass through the box): +-25 deg, same random stream as the point-claw profile
        claw_yaw *= math.radians(25.0) / math.pi
    xy = cam_xy - rot_z(claw_yaw)[:2, :2] @ cam_off_body + np.asarray(claw_offset)
    slack = kw.pop("slack_m", tuple(rng.uniform(0.03, 0.10, 4)))
    return World(cfg, stations, anchors=anchors, T_R_M=T_R_M, claw_xy=xy, claw_yaw=claw_yaw, slack_m=slack,
                 seed=seed, **kw)
