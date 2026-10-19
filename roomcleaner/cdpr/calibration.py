"""Geometric self-calibration: anchors, length references and the marker pose.

Problem
-------
Unknowns (the *physical* parameters ``theta``):

* ``a_i^M``  cable exit points in the **marker** frame (12)
* ``L0_i``   external length at motor position 0 of the current boot epoch (4)
* ``s_i``    optional payout-scale corrections (4, off by default)

plus the marker's pose in the room ``psi = (x, y, yaw)`` (the marker lies flat
on the floor, so z = roll = pitch = 0) and one nuisance position ``p_k`` per
vision sample.

Observations:

* vision: claw pose ``T_M_B`` per sample, with a covariance from the detector;
* motors: microstep positions ``P_k`` (encoder-checked by the stations);
* taut onsets from slack take-up: ``L_i(P_onset) ~ |a_i - q|`` at low weight.

Model: ``L_i(P; L0_i, s_i) = |a_i - (p + R b_i)|``  (straight cables).

Why the marker frame: the data constrain the anchors only *relative to the
marker*. The room frame enters only through the user's anchor entries and the
marker heading guess, which are priors. Splitting it this way makes the gauge
explicit: measurement information is checked on ``theta`` alone, and the room
alignment ``psi`` is reported with its own (prior-dominated) uncertainty.

Estimator: MAP least squares (Gauss-Newton/LM via scipy) with Huber IRLS
weights on measurement rows only (priors are never down-weighted), multiple
initial headings to expose alternate optima, and a covariance from the final
Jacobian.

Acceptance is never "the optimiser converged":

1. identifiability: every direction of ``theta`` must be constrained by the
   *data* at least ``data_sv_min`` times as well as by the priors, or it is
   reported as prior-dominated by name (e.g. "range of anchor C vs L0_C");
2. adequacy: whitened residual RMS <= ``norm_rms_max`` (else the model is
   wrong: camera extrinsics, slack, sag, a mis-wound spool...);
3. uniqueness: no alternate optimum within ``ambiguity_dchi2``;
4. prediction: posterior 1-sigma of every cable length over the accepted
   volume <= ``length_sigma_max_m``;
5. witnesses: held-out poses are predicted within ``witness_rms_max_m``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from .frames import planar_T, rot_z
from .spool import CableMap, SpoolRangeError

IDS = ("A", "B", "C", "D")


# ---------------------------------------------------------------- samples
@dataclass
class PoseSample:
    """Claw pose from vision (marker frame) with the four motor positions."""
    P: np.ndarray                 # (4,) microsteps, all in the current boot epochs
    p: np.ndarray                 # (3,) body origin in the marker frame
    R: np.ndarray                 # (3,3) body orientation in the marker frame
    cov: np.ndarray               # (3,3) covariance of p (m^2)
    kind: str = "fit"             # "fit" | "witness"
    t: float | None = None

    def __post_init__(self):
        self.P = np.asarray(self.P, float).reshape(4)
        self.p = np.asarray(self.p, float).reshape(3)
        self.R = np.asarray(self.R, float).reshape(3, 3)
        self.cov = np.asarray(self.cov, float).reshape(3, 3)


@dataclass
class OnsetSample:
    """Station ``i`` became taut at motor position ``P`` with the claw at ``p``."""
    i: int
    P: float
    p: np.ndarray
    R: np.ndarray
    cov: np.ndarray
    bearing: float | None = None      # horizontal slide direction (rad, marker frame) after onset
    bearing_from: np.ndarray | None = None   # claw position the slide started from
    bearing_sigma: float = 0.15


@dataclass
class BeadObs:
    """Bead capture: cable i's external length was ``trigger`` at position P."""
    i: int
    P: float
    trigger: float
    sigma: float


# ------------------------------------------------------------- the model
@dataclass
class Layout:
    """Index bookkeeping for the parameter vector."""
    n_samples: int
    fit_scale: bool

    @property
    def n_theta(self):
        return 12 + 4 + (4 if self.fit_scale else 0)

    def a(self, i):
        return slice(3 * i, 3 * i + 3)

    def L0(self, i):
        return 12 + i

    def s(self, i):
        return 16 + i if self.fit_scale else None

    @property
    def psi(self):
        return slice(self.n_theta, self.n_theta + 3)

    def p(self, k):
        o = self.n_theta + 3 + 3 * k
        return slice(o, o + 3)

    @property
    def n(self):
        return self.n_theta + 3 + 3 * self.n_samples

    def names(self):
        out = []
        for i, sid in enumerate(IDS):
            out += [f"anchor {sid}.{ax}" for ax in "xyz"]
        out += [f"L0 {sid}" for sid in IDS]
        if self.fit_scale:
            out += [f"scale {sid}" for sid in IDS]
        return out


class CableLengthModel:
    """L_i(P; L0_i, s_i) built on each station's spool map."""

    def __init__(self, maps: dict):
        self.maps = [maps[s] for s in IDS]

    def length(self, i, P, L0, s=1.0):
        m = self.maps[i].with_reference(L0)
        P = np.atleast_1d(np.asarray(P, float))
        Ln = np.array([m.length(x) for x in P])
        return L0 + s * (Ln - L0)

    def dL_dL0(self, i, P, L0, s=1.0, h=1e-4):
        return (self.length(i, P, L0 + h, s) - self.length(i, P, L0 - h, s)) / (2 * h)

    def position(self, i, L, L0, s=1.0):
        """Microstep position giving external length L (inverse of length())."""
        m = self.maps[i].with_reference(L0)
        target = L0 + (L - L0) / s
        return m.position(target)

    def solve_L0(self, i, P, L, L0_guess):
        """L0 such that length(P; L0) == L (secant on a near-identity map)."""
        x = float(L0_guess)
        for _ in range(30):
            f = float(self.length(i, P, x)[0]) - L
            if abs(f) < 1e-9:
                break
            d = float(self.dL_dL0(i, P, x)[0])
            x -= f / d
        return x


@dataclass
class Priors:
    anchors_room: np.ndarray          # (4,3)
    anchor_sigma: np.ndarray          # (4,)
    heading: float
    heading_sigma: float
    position: np.ndarray              # (2,)
    position_sigma: float
    scale_sigma: float = 0.02

    @classmethod
    def from_config(cls, cfg):
        a = cfg.anchor_priors()
        sig = np.array([s.anchor_sigma_m for s in cfg.stations], float)
        pos = cfg.marker.position_prior_room_m
        if pos is None:
            pos = cfg.room_m[:2] / 2
        if cfg.marker.heading_prior_rad is None:
            raise ValueError("marker.heading_prior_rad must be set (which way the marker +X points)")
        return cls(a, sig, float(cfg.marker.heading_prior_rad), float(cfg.marker.heading_sigma_rad),
                   np.asarray(pos, float), float(cfg.marker.position_sigma_m))


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ------------------------------------------------------------- results
@dataclass
class Identifiability:
    singular_values: np.ndarray       # data information, prior-normalised (sqrt of eigenvalues)
    weak: list                        # [(sv, description)] below threshold
    ok: bool


@dataclass
class CalibrationResult:
    anchors_M: np.ndarray
    L0: np.ndarray
    scale: np.ndarray
    psi: np.ndarray                   # (x, y, yaw) of the marker in the room
    cov_theta: np.ndarray             # posterior covariance of theta (+psi appended: last 3)
    chi2: float
    norm_rms: float
    n_rows: int
    residuals_m: np.ndarray           # (K,4) length residuals of fit samples (m)
    outliers: list
    identifiability: Identifiability
    alternates: list = field(default_factory=list)
    ambiguous: bool = False
    fit_scale: bool = False
    slack: np.ndarray | None = None   # (K,4) readings classified as slack cables
    notes: list = field(default_factory=list)

    @property
    def T_R_M(self) -> np.ndarray:
        return planar_T(*self.psi)

    @property
    def anchors_room(self) -> np.ndarray:
        return self.anchors_M @ rot_z(self.psi[2]).T + [self.psi[0], self.psi[1], 0.0]

    def sigma(self) -> dict:
        lay = Layout(0, self.fit_scale)
        sd = np.sqrt(np.diag(self.cov_theta))
        names = lay.names() + ["marker x", "marker y", "marker yaw"]
        return dict(zip(names, sd))

    def to_jsonable(self) -> dict:
        return {"anchors_marker_m": self.anchors_M.tolist(), "anchors_room_m": self.anchors_room.tolist(),
                "L0_m": dict(zip(IDS, self.L0.tolist())), "payout_scale": dict(zip(IDS, self.scale.tolist())),
                "marker_in_room": {"x_m": self.psi[0], "y_m": self.psi[1], "yaw_rad": self.psi[2]},
                "sigma": {k: float(v) for k, v in self.sigma().items()}, "chi2": self.chi2,
                "norm_rms": self.norm_rms, "outliers": self.outliers,
                "identifiability": {"ok": self.identifiability.ok,
                                    "weak": [[float(a), b] for a, b in self.identifiability.weak]},
                "ambiguous": self.ambiguous, "notes": self.notes,
                "slack_readings": int(self.slack.sum()) if self.slack is not None else 0}


# ------------------------------------------------------------- estimator
class Calibrator:
    def __init__(self, cfg, maps: dict, *, attach=None, priors: Priors | None = None):
        self.cfg = cfg
        self.cc = cfg.calibration
        self.lm = CableLengthModel(maps)
        self.attach = np.asarray(cfg.attachment_points() if attach is None else attach, float)
        self.priors = priors or Priors.from_config(cfg)
        self.beads: list = []             # BeadObs included in every fit once verified

    # -- parameter packing -------------------------------------------------
    def _init_x(self, lay, samples, onsets, psi0, L0_init=None):
        x = np.zeros(lay.n)
        xR, yR, yaw = psi0
        aM = (self.priors.anchors_room - [xR, yR, 0.0]) @ rot_z(yaw)       # R^T applied row-wise
        for i in range(4):
            x[lay.a(i)] = aM[i]
        for i in range(4):
            if L0_init is not None and np.isfinite(L0_init[i]):
                x[lay.L0(i)] = L0_init[i]
                continue
            if samples:
                k = samples[0]
                q = k.p + k.R @ self.attach[i]
                Lk = float(np.linalg.norm(aM[i] - q))
                x[lay.L0(i)] = self.lm.solve_L0(i, k.P[i], Lk, Lk)
            else:
                o = [o for o in onsets if o.i == i][0]
                q = o.p + o.R @ self.attach[i]
                Lk = float(np.linalg.norm(aM[i] - q))
                x[lay.L0(i)] = self.lm.solve_L0(i, o.P, Lk, Lk)
        if lay.fit_scale:
            for i in range(4):
                x[lay.s(i)] = 1.0
        x[lay.psi] = psi0
        for k, smp in enumerate(samples):
            x[lay.p(k)] = smp.p
        return x

    # -- residuals and Jacobian ---------------------------------------------
    def _rows(self, x, lay, samples, onsets, w_len, w_vis, w_on, include_priors=True):
        """Whitened residual vector and dense Jacobian."""
        sl = self.cc.length_sigma_m
        aM = np.array([x[lay.a(i)] for i in range(4)])
        rs, Js = [], []
        K = len(samples)
        # length rows
        for i in range(4):
            L0 = x[lay.L0(i)]
            s = x[lay.s(i)] if lay.fit_scale else 1.0
            P = np.array([smp.P[i] for smp in samples])
            if K:
                Lm = self.lm.length(i, P, L0, s)
                dL0 = self.lm.dL_dL0(i, P, L0, s)
                Ln = (Lm - L0) / s + L0 if lay.fit_scale else None
            for k, smp in enumerate(samples):
                q = x[lay.p(k)] + smp.R @ self.attach[i]
                d = aM[i] - q
                dist = np.linalg.norm(d)
                u = d / dist
                w = w_len[k, i] / sl
                J = np.zeros(lay.n)
                J[lay.a(i)] = -u * w
                J[lay.p(k)] = u * w
                J[lay.L0(i)] = dL0[k] * w
                if lay.fit_scale:
                    J[lay.s(i)] = (Ln[k] - L0) * w
                rs.append((Lm[k] - dist) * w)
                Js.append(J)
        # vision rows
        for k, smp in enumerate(samples):
            W = np.linalg.inv(np.linalg.cholesky(smp.cov)) * w_vis[k]
            r = W @ (x[lay.p(k)] - smp.p)
            J = np.zeros((3, lay.n))
            J[:, lay.p(k)] = W
            rs.extend(r)
            Js.extend(J)
        # taut-onset rows (vision position held fixed, its noise folded into sigma)
        for j, o in enumerate(onsets):
            i = o.i
            L0 = x[lay.L0(i)]
            s = x[lay.s(i)] if lay.fit_scale else 1.0
            q = o.p + o.R @ self.attach[i]
            d = aM[i] - q
            dist = np.linalg.norm(d)
            u = d / dist
            sig = math.sqrt(self.cc.onset_sigma_m ** 2 + u @ o.cov @ u)
            w = w_on[j] / sig
            Lm = float(self.lm.length(i, o.P, L0, s)[0])
            J = np.zeros(lay.n)
            J[lay.a(i)] = -u * w
            J[lay.L0(i)] = float(self.lm.dL_dL0(i, o.P, L0, s)[0]) * w
            if lay.fit_scale:
                J[lay.s(i)] = (Lm - L0) / s * w
            rs.append((Lm - dist) * w)
            Js.append(J)
        # slide bearings: the horizontal direction from the claw to anchor i (marker frame)
        for j, o in enumerate(onsets):
            if o.bearing is None:
                continue
            i = o.i
            c = 0.5 * (np.asarray(o.bearing_from) + o.p)
            dx, dy = aM[i][0] - c[0], aM[i][1] - c[1]
            r2 = dx * dx + dy * dy
            w = w_on[j] / o.bearing_sigma
            J = np.zeros(lay.n)
            J[lay.a(i).start] = -dy / r2 * w
            J[lay.a(i).start + 1] = dx / r2 * w
            rs.append(_wrap(math.atan2(dy, dx) - o.bearing) * w)
            Js.append(J)
        for b in self.beads:
            L0 = x[lay.L0(b.i)]
            sc = x[lay.s(b.i)] if lay.fit_scale else 1.0
            Lm = float(self.lm.length(b.i, b.P, L0, sc)[0])
            J = np.zeros(lay.n)
            J[lay.L0(b.i)] = float(self.lm.dL_dL0(b.i, b.P, L0, sc)[0]) / b.sigma
            if lay.fit_scale:
                J[lay.s(b.i)] = (Lm - L0) / sc / b.sigma
            rs.append((Lm - b.trigger) / b.sigma)
            Js.append(J)
        n_meas = len(rs)
        if include_priors:
            pr = self.priors
            xR, yR, yaw = x[lay.psi]
            Rz = rot_z(yaw)
            dRz = np.array([[-math.sin(yaw), -math.cos(yaw), 0], [math.cos(yaw), -math.sin(yaw), 0], [0, 0, 0]])
            for i in range(4):
                sg = pr.anchor_sigma[i]
                aR = Rz @ aM[i] + [xR, yR, 0.0]
                J = np.zeros((3, lay.n))
                J[:, lay.a(i)] = Rz / sg
                J[:, lay.psi.start] = np.array([1, 0, 0]) / sg
                J[:, lay.psi.start + 1] = np.array([0, 1, 0]) / sg
                J[:, lay.psi.start + 2] = dRz @ aM[i] / sg
                rs.extend((aR - pr.anchors_room[i]) / sg)
                Js.extend(J)
            J = np.zeros(lay.n)
            J[lay.psi.start + 2] = 1 / pr.heading_sigma
            rs.append(_wrap(yaw - pr.heading) / pr.heading_sigma)
            Js.append(J)
            for ax in range(2):
                J = np.zeros(lay.n)
                J[lay.psi.start + ax] = 1 / pr.position_sigma
                rs.append((x[lay.psi][ax] - pr.position[ax]) / pr.position_sigma)
                Js.append(J)
            if lay.fit_scale:
                for i in range(4):
                    J = np.zeros(lay.n)
                    J[lay.s(i)] = 1 / pr.scale_sigma
                    rs.append((x[lay.s(i)] - 1.0) / pr.scale_sigma)
                    Js.append(J)
        return np.array(rs), np.array(Js), n_meas

    def _bounds(self, lay):
        lo = np.full(lay.n, -np.inf)
        hi = np.full(lay.n, np.inf)
        for i in range(4):
            lo[lay.L0(i)] = 0.05
            hi[lay.L0(i)] = self.lm.maps[i].cfg.line_total_m - 0.05
            if lay.fit_scale:
                lo[lay.s(i)], hi[lay.s(i)] = 0.8, 1.2
        return lo, hi

    def _assign_slack(self, x, lay, samples):
        """Per sample, choose 'all taut' or 'cable i slack' by re-solving the
        claw position under each hypothesis with theta held. A cable may be
        declared slack only if its model length then exceeds its span by more
        than slack_k sigma; a fixed penalty prefers 'all taut' when in doubt."""
        sl = self.cc.length_sigma_m
        aM = np.array([x[lay.a(i)] for i in range(4)])
        K = len(samples)
        out = np.zeros((K, 4), bool)
        Lm = np.zeros((K, 4))
        for i in range(4):
            if K:
                Lm[:, i] = self.lm.length(i, [s.P[i] for s in samples], x[lay.L0(i)],
                                          x[lay.s(i)] if lay.fit_scale else 1.0)
        for k, smp in enumerate(samples):
            W = np.linalg.inv(np.linalg.cholesky(smp.cov))
            att = smp.R @ self.attach.T

            def res(q, keep):
                d = np.linalg.norm(aM - (q[None, :] + att.T), axis=1)
                return np.r_[(Lm[k] - d)[keep] / sl, W @ (q - smp.p)]
            best = None
            for drop in (None, 0, 1, 2, 3):
                keep = [i for i in range(4) if i != drop]
                sol = least_squares(res, x[lay.p(k)], args=(keep,), method="lm")
                cost = float(sol.fun @ sol.fun)
                if drop is not None:
                    d = np.linalg.norm(aM[drop] - (sol.x + att[:, drop]))
                    if (Lm[k, drop] - d) / sl < self.cc.slack_k:
                        continue
                    cost += self.cc.slack_k ** 2
                if best is None or cost < best[0]:
                    best = (cost, drop)
            if best[1] is not None:
                out[k, best[1]] = True
        return out

    def _solve(self, x0, lay, samples, onsets):
        K = len(samples)
        w_len = np.ones((K, 4))
        w_vis = np.ones(K)
        w_on = np.ones(len(onsets))
        hk = self.cc.huber_k
        x = x0.copy()
        slack = np.zeros((K, 4), bool)
        for _ in range(8):                         # IRLS: Huber weights on measurement rows
            fun = lambda z: self._rows(z, lay, samples, onsets, w_len, w_vis, w_on)[0]
            jac = lambda z: self._rows(z, lay, samples, onsets, w_len, w_vis, w_on)[1]
            sol = least_squares(fun, x, jac=jac, method="trf", x_scale="jac", max_nfev=200,
                                bounds=self._bounds(lay))
            x = sol.x
            r, _, _ = self._rows(x, lay, samples, onsets, np.ones((K, 4)), np.ones(K), np.ones(len(onsets)),
                                 include_priors=False)
            rl = r[: 4 * K].reshape(4, K).T            # unweighted whitened length residuals
            rv = np.linalg.norm(r[4 * K: 7 * K].reshape(K, 3), axis=1) / math.sqrt(3) if K else np.zeros(0)
            no = len(onsets)
            ro = np.abs(r[7 * K: 7 * K + no])
            rb = iter(np.abs(r[7 * K + no:]))
            ro = np.array([max(ro[j], next(rb)) if o.bearing is not None else ro[j] for j, o in enumerate(onsets)])
            new_len = np.minimum(1.0, hk / np.maximum(np.abs(rl), 1e-12)) ** 0.5
            # A common-point claw hangs on three cables whenever the commanded
            # lengths are not exactly consistent; the fourth is slack, its
            # model length exceeds the distance, and its reading carries no
            # information. At most one per sample: the clearly longest one.
            slack = self._assign_slack(x, lay, samples)
            new_len[slack] = 0.0
            new_vis = np.minimum(1.0, hk / np.maximum(rv, 1e-12)) ** 0.5
            new_on = np.minimum(1.0, hk / np.maximum(ro, 1e-12)) ** 0.5
            if np.allclose(new_len, w_len, atol=1e-3) and np.allclose(new_vis, w_vis, atol=1e-3):
                w_len, w_vis, w_on = new_len, new_vis, new_on
                break
            w_len, w_vis, w_on = new_len, new_vis, new_on
        r, J, n_meas = self._rows(x, lay, samples, onsets, w_len, w_vis, w_on)
        self._last_slack = slack
        return x, r, J, n_meas, (w_len, w_vis, w_on)

    # -- public ------------------------------------------------------------
    def fit(self, samples: list, onsets: list = (), *, L0_init=None, psi_inits=None) -> CalibrationResult:
        fit_s = [s for s in samples if s.kind == "fit"]
        onsets = list(onsets)
        lay = Layout(len(fit_s), self.cc.fit_payout_scale)
        for i in range(4):
            if not any(o.i == i for o in onsets) and not fit_s:
                raise ValueError(f"no observation of cable {IDS[i]}: its L0 is undetermined")
        pr = self.priors
        starts = [np.array([pr.position[0], pr.position[1], _wrap(pr.heading + d)])
                  for d in (0, math.pi / 2, math.pi, -math.pi / 2)]
        if psi_inits is not None:
            starts = [np.asarray(p, float) for p in psi_inits] + starts
        sols = []
        for psi0 in starts:
            x0 = self._init_x(lay, fit_s, onsets, psi0, L0_init)
            lo, hi = self._bounds(lay)
            x0 = np.clip(x0, lo + 1e-6, hi - 1e-6)
            try:
                x, r, J, n_meas, wts = self._solve(x0, lay, fit_s, onsets)
            except (np.linalg.LinAlgError, SpoolRangeError):
                continue
            sols.append((float(r @ r), x, r, J, n_meas, wts, self._last_slack.copy()))
        if not sols:
            raise RuntimeError("calibration failed from every initialisation")
        sols.sort(key=lambda s: s[0])
        chi2, x, r, J, n_meas, (w_len, w_vis, w_on), slack = sols[0]
        x[lay.psi.start + 2] = _wrap(x[lay.psi.start + 2])
        alternates, ambiguous = [], False
        for c2, xa, *_ in sols[1:]:
            dyaw = abs(_wrap(xa[lay.psi][2] - x[lay.psi][2]))
            dA = float(np.max(np.abs(xa[:12] - x[:12])))
            if dyaw > 0.05 or dA > 0.02:
                alternates.append({"chi2": c2, "yaw": float(xa[lay.psi][2]), "max_anchor_diff_m": dA})
                if c2 - chi2 < self.cc.ambiguity_dchi2:
                    ambiguous = True
        # posterior covariance of (theta, psi) by marginalising the sample positions
        H = J.T @ J
        cov_all = np.linalg.pinv(H)
        keep = np.r_[np.arange(lay.n_theta), np.arange(lay.psi.start, lay.psi.stop)]
        cov = cov_all[np.ix_(keep, keep)]
        # whitened residual RMS of measurement rows (unweighted by IRLS)
        K = len(fit_s)
        r0, _, _ = self._rows(x, lay, fit_s, onsets, np.ones((K, 4)), np.ones(K), np.ones(len(onsets)),
                              include_priors=False)
        keep_rows = np.ones(len(r0), bool)
        for k in range(K):
            for i in range(4):
                keep_rows[i * K + k] = not slack[k, i]
        norm_rms = float(np.sqrt(np.mean(r0[keep_rows] ** 2))) if len(r0) else 0.0
        res_m = (r0[: 4 * K].reshape(4, K).T * self.cc.length_sigma_m) if K else np.zeros((0, 4))
        outliers = []
        for k in range(K):
            for i in range(4):
                if not slack[k, i] and abs(r0[i * K + k]) > self.cc.outlier_k:
                    outliers.append({"sample": k, "station": IDS[i], "sigma": float(r0[i * K + k])})
        ident = self.identifiability(x, lay, fit_s, onsets, slack)
        res = CalibrationResult(
            anchors_M=np.array([x[lay.a(i)] for i in range(4)]),
            L0=np.array([x[lay.L0(i)] for i in range(4)]),
            scale=np.array([x[lay.s(i)] for i in range(4)]) if lay.fit_scale else np.ones(4),
            psi=x[lay.psi].copy(), cov_theta=cov, chi2=chi2, norm_rms=norm_rms, n_rows=len(r),
            residuals_m=res_m, outliers=outliers, identifiability=ident, alternates=alternates,
            ambiguous=ambiguous, fit_scale=lay.fit_scale, slack=slack)
        if norm_rms > self.cc.norm_rms_max:
            res.notes.append(f"residual RMS {norm_rms:.2f} sigma exceeds {self.cc.norm_rms_max}: model inadequate")
        if ambiguous:
            res.notes.append("alternate optimum within ambiguity threshold: marker heading/anchor entries inconsistent")
        return res

    # -- identifiability ---------------------------------------------------------
    def identifiability(self, x, lay, samples, onsets, slack=None) -> Identifiability:
        """Data-only information on theta (sample positions marginalised), scaled by
        the prior scales so 1.0 means 'the data constrain this direction as well as
        the prior does'."""
        K = len(samples)
        w = np.ones((K, 4)) if slack is None else (~slack).astype(float)
        _, J, n_meas = self._rows(x, lay, samples, onsets, w, np.ones(K), np.ones(len(onsets)),
                                  include_priors=False)
        Jm = J[:n_meas]
        nt = lay.n_theta
        I = Jm.T @ Jm
        Itt = I[:nt, :nt]
        if K:
            pidx = np.arange(lay.psi.stop, lay.n)
            Itp = I[np.ix_(np.arange(nt), pidx)]
            Ipp = I[np.ix_(pidx, pidx)]
            Itt = Itt - Itp @ np.linalg.solve(Ipp, Itp.T)
        scale = np.r_[np.repeat(self.priors.anchor_sigma, 3), np.full(4, 0.10)]
        if lay.fit_scale:
            scale = np.r_[scale, np.full(4, self.priors.scale_sigma)]
        D = np.diag(scale)
        ev, V = np.linalg.eigh(D @ Itt @ D)
        sv = np.sqrt(np.clip(ev, 0, None))
        names = lay.names()
        weak = []
        for k in np.argsort(sv):
            if sv[k] >= self.cc.data_sv_min:
                break
            v = V[:, k]
            top = np.argsort(-np.abs(v))[:3]
            desc = " + ".join(f"{v[j]:+.2f}*{names[j]}" for j in top if abs(v[j]) > 0.2)
            weak.append((float(sv[k]), desc))
        return Identifiability(sv, weak, not weak)

    # -- prediction -------------------------------------------------------------
    def length_sigma(self, res: CalibrationResult, q_M, R=None) -> np.ndarray:
        """Posterior 1-sigma (m) of the four cable lengths commanded for a claw
        pose q (marker frame): uncertainty in anchors, L0 and scale."""
        R = np.eye(3) if R is None else R
        lay = Layout(0, res.fit_scale)
        nt = lay.n_theta
        C = res.cov_theta[:nt, :nt]
        out = np.zeros(4)
        for i in range(4):
            d = res.anchors_M[i] - (np.asarray(q_M) + R @ self.attach[i])
            u = d / np.linalg.norm(d)
            g = np.zeros(nt)
            g[lay.a(i)] = u
            g[lay.L0(i)] = -1.0
            out[i] = math.sqrt(max(g @ C @ g, 0.0))
        return out

    def absolute_sigma(self, res: CalibrationResult) -> np.ndarray:
        """1-sigma of each cable's ABSOLUTE length at a given motor position
        (what a bead checks). Vision constrains it only through the range of
        the anchors, so it is usually much larger than length_sigma()."""
        lay = Layout(0, res.fit_scale)
        return np.sqrt(np.array([res.cov_theta[lay.L0(i), lay.L0(i)] for i in range(4)]))

    def position_sigma(self, res: CalibrationResult, q_M, R=None) -> float:
        """RMS 1-sigma (m) of the claw position the model would reach for a
        commanded pose: the length errors mapped through the forward kinematics."""
        R = np.eye(3) if R is None else R
        lay = Layout(0, res.fit_scale)
        nt = lay.n_theta
        C = res.cov_theta[:nt, :nt]
        G = np.zeros((4, nt))
        Hq = np.zeros((4, 3))
        for i in range(4):
            d = res.anchors_M[i] - (np.asarray(q_M) + R @ self.attach[i])
            u = d / np.linalg.norm(d)
            G[i, lay.a(i)] = u
            G[i, lay.L0(i)] = -1.0
            Hq[i] = -u
        A = np.linalg.pinv(Hq) @ G
        return float(math.sqrt(np.trace(A @ C @ A.T) / 3))

    def validate(self, res: CalibrationResult, witnesses: list, volume_pts_M=None) -> dict:
        """Witness check (held-out poses) plus the acceptance criteria listed in
        the module docstring. Returns a report with 'accepted' and reasons."""
        reasons = []
        geo_err, len_res, nchi = [], [], []
        for w in witnesses:
            L = np.array([self.lm.length(i, w.P[i], res.L0[i], res.scale[i])[0] for i in range(4)])
            # forward kinematics in the marker frame from the four lengths
            def f(q):
                return np.array([np.linalg.norm(res.anchors_M[i] - (q + w.R @ self.attach[i])) for i in range(4)]) - L
            sol = least_squares(f, w.p, method="lm")
            # a slack witness cable is longer than its span: drop the clearly longest
            rf = -sol.fun / self.cc.length_sigma_m
            j = int(np.argmax(rf))
            if rf[j] > self.cc.slack_k:
                keep = [i for i in range(4) if i != j]
                sol = least_squares(lambda q: f(q)[keep], w.p, method="lm")
            e = sol.x - w.p
            geo_err.append(e @ e - np.trace(w.cov))        # vision noise removed in quadrature
            Cm = w.cov + np.eye(3) * self.position_sigma(res, w.p, w.R) ** 2
            nchi.append(e @ np.linalg.solve(Cm, e) / 3)
            len_res.extend(f(w.p))
        # excess RMS: what the model adds beyond the camera's own expected noise
        wit_rms = float(math.sqrt(max(np.mean(geo_err), 0.0))) if geo_err else float("nan")
        wit_chi = float(np.mean(nchi)) if nchi else float("nan")
        len_rms = float(np.sqrt(np.mean(np.square(len_res)))) if len_res else float("nan")
        if len(witnesses) < self.cc.witness_samples:
            reasons.append(f"only {len(witnesses)} witness poses (need {self.cc.witness_samples})")
        elif wit_rms > self.cc.witness_rms_max_m:
            reasons.append(f"witness position RMS {wit_rms * 1e3:.1f} mm > {self.cc.witness_rms_max_m * 1e3:.1f} mm")
        elif wit_chi > self.cc.norm_rms_max ** 2:
            reasons.append(f"witness errors {wit_chi:.1f}x their predicted variance")
        if not res.identifiability.ok:
            reasons.append("prior-dominated: " + "; ".join(d for _, d in res.identifiability.weak))
        if res.norm_rms > self.cc.norm_rms_max:
            reasons.append(f"residual RMS {res.norm_rms:.2f} sigma > {self.cc.norm_rms_max}")
        if res.ambiguous:
            reasons.append("ambiguous alignment (alternate optimum)")
        if res.outliers:
            reasons.append(f"{len(res.outliers)} outlier readings")
        sig_max = 0.0
        if volume_pts_M is not None and len(volume_pts_M):
            sig_max = max(float(np.max(self.length_sigma(res, q))) for q in volume_pts_M)
            if sig_max > self.cc.length_sigma_max_m:
                reasons.append(f"predicted length sigma {sig_max * 1e3:.1f} mm > "
                               f"{self.cc.length_sigma_max_m * 1e3:.1f} mm in the requested volume")
        return {"accepted": not reasons, "reasons": reasons, "witness_rms_m": wit_rms, "witness_chi2_dof": wit_chi,
                "witness_length_rms_m": len_rms, "max_length_sigma_m": sig_max, "n_witness": len(witnesses)}

    # -- recovery ---------------------------------------------------------------
    def visual_reference(self, res: CalibrationResult, i: int, P_now: float, sample_p, sample_R, cov,
                         ) -> tuple[float, float]:
        """New L0 for ONE station (e.g. after it rebooted) from a vision pose,
        holding the other parameters. Returns (L0, 1-sigma). The station is
        LOCAL_ONLY until bead verification."""
        q = np.asarray(sample_p) + np.asarray(sample_R) @ self.attach[i]
        d = res.anchors_M[i] - q
        Lv = float(np.linalg.norm(d))
        u = d / Lv
        lay = Layout(0, res.fit_scale)
        g = np.zeros(lay.n_theta)
        g[lay.a(i)] = u
        var = g @ res.cov_theta[:lay.n_theta, :lay.n_theta] @ g + u @ np.asarray(cov) @ u
        L0 = self.lm.solve_L0(i, P_now, Lv, res.L0[i])
        return L0, math.sqrt(var)

    def geometric_reference(self, res: CalibrationResult, i: int, P: np.ndarray, R=None,
                            p_guess=None) -> tuple[float, np.ndarray]:
        """New L0 for station i from the other three (trusted) cables: the claw
        position is solved from three lengths, then cable i's span follows.
        Requires all three to be taut, so use only while suspended and still."""
        R = np.eye(3) if R is None else R
        others = [j for j in range(4) if j != i]
        L = {j: float(self.lm.length(j, P[j], res.L0[j], res.scale[j])[0]) for j in others}

        def f(q):
            return np.array([np.linalg.norm(res.anchors_M[j] - (q + R @ self.attach[j])) - L[j] for j in others])
        q0 = np.mean(res.anchors_M, axis=0) - [0, 0, 1.5] if p_guess is None else np.asarray(p_guess, float)
        q = least_squares(f, q0, method="lm").x
        Li = float(np.linalg.norm(res.anchors_M[i] - (q + R @ self.attach[i])))
        return self.lm.solve_L0(i, P[i], Li, res.L0[i]), q


# ------------------------------------------------------- floor alignment
def align_from_bearings(priors: Priors, claw_M, bearings_M, sigma_rad=0.15):
    """Marker pose in the room from the directions the claw slid when each
    cable alone became taut on the floor (horizontal pull points at the anchor).

    ``claw_M``: (4,3) claw positions (marker frame) at each onset;
    ``bearings_M``: (4,) slide directions (rad, marker frame), NaN if unknown.
    Returns (psi, covariance, whitened residual RMS)."""
    claw_M = np.asarray(claw_M, float)
    b = np.asarray(bearings_M, float)
    use = [i for i in range(4) if np.isfinite(b[i])]

    def res(psi):
        x, y, yaw = psi
        r = []
        for i in use:
            c = rot_z(yaw) @ claw_M[i] + [x, y, 0.0]
            d = priors.anchors_room[i] - c
            r.append(_wrap(math.atan2(d[1], d[0]) - yaw - b[i]) / sigma_rad)
        r.append(_wrap(yaw - priors.heading) / priors.heading_sigma)
        r.extend((np.array([x, y]) - priors.position) / priors.position_sigma)
        return np.array(r)
    best = None
    for dy in (0, math.pi / 2, math.pi, -math.pi / 2):
        s = least_squares(res, [priors.position[0], priors.position[1], priors.heading + dy], method="lm")
        if best is None or s.cost < best.cost:
            best = s
    J = best.jac
    cov = np.linalg.pinv(J.T @ J)
    psi = best.x.copy()
    psi[2] = _wrap(psi[2])
    n = len(use)
    rms = float(np.sqrt(np.mean(best.fun[:n] ** 2))) if n else float("nan")
    return psi, cov, rms


# --------------------------------------------------------- excitation design
def sample_information(cal: Calibrator, res_or_state, q_M, cov_p, R=None) -> np.ndarray:
    """Information on theta contributed by one vision sample at q (positions
    marginalised): G^T S^-1 G with S = sigma_L^2 I + H cov_p H^T."""
    R = np.eye(3) if R is None else R
    anchors = res_or_state.anchors_M
    lay = Layout(0, cal.cc.fit_payout_scale)
    nt = lay.n_theta
    G = np.zeros((4, nt))
    H = np.zeros((4, 3))
    for i in range(4):
        d = anchors[i] - (np.asarray(q_M) + R @ cal.attach[i])
        u = d / np.linalg.norm(d)
        G[i, lay.a(i)] = -u
        G[i, lay.L0(i)] = 1.0
        if lay.fit_scale:
            G[i, lay.s(i)] = float(np.linalg.norm(d)) - res_or_state.L0[i]
        H[i] = u
    S = cal.cc.length_sigma_m ** 2 * np.eye(4) + H @ cov_p @ H.T
    return G.T @ np.linalg.solve(S, G)


def prior_information(cal: Calibrator) -> np.ndarray:
    lay = Layout(0, cal.cc.fit_payout_scale)
    d = np.r_[np.repeat(cal.priors.anchor_sigma, 3), np.full(4, 1.0)]   # L0: effectively unconstrained
    if lay.fit_scale:
        d = np.r_[d, np.full(4, cal.priors.scale_sigma)]
    return np.diag(1.0 / d ** 2)


def design_excitation(cal: Calibrator, state, candidates_M, n: int, *, cov_fn, existing_M=(),
                      start_M=None, n_witness=0) -> tuple[list, list]:
    """Greedy D-optimal choice of ``n`` poses from feasible ``candidates_M``
    (already filtered for workspace, tension and marker visibility), plus
    ``n_witness`` well-spread held-out poses. ``cov_fn(q)`` predicts the vision
    covariance at q. Returned poses are ordered as a short tour from start."""
    cands = [np.asarray(c, float) for c in candidates_M]
    infos = [sample_information(cal, state, c, cov_fn(c)) for c in cands]
    I = prior_information(cal)
    for q in existing_M:
        I = I + sample_information(cal, state, q, cov_fn(q))
    chosen = []
    free = set(range(len(cands)))
    for _ in range(min(n, len(cands))):
        best, best_val = None, -np.inf
        base = np.linalg.slogdet(I)[1]
        for k in free:
            val = np.linalg.slogdet(I + infos[k])[1] - base
            if val > best_val:
                best, best_val = k, val
        chosen.append(best)
        free.discard(best)
        I = I + infos[best]
    wit = []
    for _ in range(min(n_witness, len(free))):
        used = [cands[k] for k in chosen + wit]
        k = max(free, key=lambda j: min(np.linalg.norm(cands[j] - u) for u in used))
        wit.append(k)
        free.discard(k)
    fit_pts = _tour([cands[k] for k in chosen], start_M)
    return fit_pts, [cands[k] for k in wit]


def _tour(pts, start):
    if not pts:
        return []
    rest = list(pts)
    cur = np.asarray(start, float) if start is not None else rest[0]
    out = []
    while rest:
        k = int(np.argmin([np.linalg.norm(p - cur) for p in rest]))
        cur = rest.pop(k)
        out.append(cur)
    return out


def box_candidates(center, half_extent, n=(5, 5, 3)) -> np.ndarray:
    c = np.asarray(center, float)
    h = np.asarray(half_extent, float)
    axes = [np.linspace(-h[k], h[k], n[k]) if n[k] > 1 else np.zeros(1) for k in range(3)]
    g = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    return c + g


def marker_visible(camera, T_B_C, T_M_B, edge_m, *, min_side_px, margin_px=20) -> bool:
    """Would the whole marker appear in the image, large enough, at this claw pose?"""
    from .frames import inv_T
    T_C_M = inv_T(T_M_B @ T_B_C)
    h = edge_m / 2
    pts = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], float)
    pc = pts @ T_C_M[:3, :3].T + T_C_M[:3, 3]
    if np.any(pc[:, 2] <= 0.05):
        return False
    uv = camera.project(pc)
    if not np.all(camera.in_image(uv, margin_px)):
        return False
    side = np.mean([np.linalg.norm(uv[k] - uv[(k + 1) % 4]) for k in range(4)])
    return bool(side >= min_side_px)


def predicted_vision_cov(camera, T_B_C, T_M_B, edge_m, *, pixel_sigma=0.3, rot_sigma=0.01) -> np.ndarray:
    """Expected claw-position covariance at a pose (same model as the detector)."""
    from .frames import inv_T
    T_C_M = inv_T(T_M_B @ T_B_C)
    z = float(T_C_M[2, 3])
    lat = pixel_sigma * z / camera.fx
    dep = 2 * pixel_sigma * z * z / (camera.fx * edge_m)
    R_M_C = inv_T(T_C_M)[:3, :3]
    C = R_M_C @ np.diag([lat ** 2, lat ** 2, dep ** 2]) @ R_M_C.T
    return C + np.eye(3) * (rot_sigma * float(np.linalg.norm(T_B_C[:3, 3]))) ** 2
