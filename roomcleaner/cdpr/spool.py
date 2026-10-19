"""Spool payout model: motor position <-> external cable length.

Conventions
-----------
* ``P``  station motor position in microsteps; **positive = payout** (cable
  gets longer). The firmware maps this to the DIR pin through ``step_sign``.
* ``W``  line stored on the spool (m).  ``L`` external span from the cable
  outlet to the claw attachment (m).  ``line_total = W + L + routing`` where
  the constant routing length is folded into ``line_total``.
* ``phi`` wound angle (rad) measured from an empty core; payout decreases it.

The radius the line leaves at depends on how much is wound, so the
microsteps-per-metre ratio is **not constant** (Spoolv3: 7.5 -> 10 mm over
20 ft, a 33 % change). Using the total-length identity, the stored length
follows from the geometric span, so the model needs only one calibration
constant per station: ``L0``, the external length at ``P = 0`` of the
current station boot epoch.

A measured payout table (bench metrology, docs T03) can replace the layered
model; it is used as ``L(P) = L0 + table(P)``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .config import SpoolConfig


class SpoolRangeError(ValueError):
    pass


@dataclass
class LayeredSpool:
    core_radius_m: float
    drum_width_m: float
    flange_radius_m: float
    line_diameter_m: float
    packing: float = 0.85
    scale: float = 1.0

    def __post_init__(self):
        d = self.line_diameter_m
        if not (d and d > 0):
            raise ValueError("line_diameter_m must be measured and > 0")
        self.turns_per_layer = self.packing * self.drum_width_m / d
        if self.turns_per_layer < 1:
            raise ValueError("drum narrower than one turn of line")
        # layers that fit under the flange rim
        self.n_layers = int(math.floor((self.flange_radius_m - self.core_radius_m) / d))
        self._r = np.array([self.core_radius_m + d * (k + 0.5) for k in range(self.n_layers)])
        self._layer_angle = 2 * math.pi * self.turns_per_layer
        self._layer_len = self._r * self._layer_angle
        self._cum_len = np.concatenate([[0.0], np.cumsum(self._layer_len)])
        self._cum_ang = np.arange(self.n_layers + 1) * self._layer_angle

    @property
    def capacity_m(self) -> float:
        return float(self._cum_len[-1]) * self.scale

    def wound_from_angle(self, phi: float) -> float:
        if phi < -1e-9 or phi > self._cum_ang[-1] + 1e-9:
            raise SpoolRangeError(f"wound angle {phi:.3f} rad outside spool capacity")
        k = min(int(phi // self._layer_angle), self.n_layers - 1)
        return float(self._cum_len[k] + (phi - self._cum_ang[k]) * self._r[k]) * self.scale

    def angle_from_wound(self, W: float) -> float:
        Wn = W / self.scale
        if Wn < -1e-9 or Wn > self._cum_len[-1] + 1e-9:
            raise SpoolRangeError(f"wound length {W:.3f} m outside 0..{self.capacity_m:.3f} m")
        k = min(int(np.searchsorted(self._cum_len, Wn, side="right") - 1), self.n_layers - 1)
        k = max(k, 0)
        return float(self._cum_ang[k] + (Wn - self._cum_len[k]) / self._r[k])

    def radius_at_wound(self, W: float) -> float:
        Wn = min(max(W / self.scale, 0.0), self._cum_len[-1])
        k = min(int(np.searchsorted(self._cum_len, Wn, side="right") - 1), self.n_layers - 1)
        return float(self._r[max(k, 0)]) * self.scale


class CableMap:
    """Maps one station's motor position P (microsteps) to external length L."""

    def __init__(self, spool_cfg: SpoolConfig, usteps_per_rev: int, L0: float | None = None):
        self.cfg = spool_cfg
        self.spr = usteps_per_rev
        self.L0 = L0
        self.table = None
        if spool_cfg.payout_table:
            t = np.asarray(spool_cfg.payout_table, float)
            if t.ndim != 2 or t.shape[1] != 2 or np.any(np.diff(t[:, 0]) <= 0) or np.any(np.diff(t[:, 1]) <= 0):
                raise ValueError("payout_table must be increasing [[usteps, payout_m], ...]")
            self.table = t
            self.spool = None
        else:
            self.spool = LayeredSpool(spool_cfg.core_radius_m, spool_cfg.drum_width_m,
                                      spool_cfg.flange_radius_m, spool_cfg.line_diameter_m,
                                      spool_cfg.packing, spool_cfg.payout_scale)
            if spool_cfg.line_total_m is None:
                raise ValueError("line_total_m must be measured for the layered model")

    # -- reference ---------------------------------------------------------
    def with_reference(self, L0: float) -> "CableMap":
        m = CableMap.__new__(CableMap)
        m.__dict__.update(self.__dict__)
        m.L0 = float(L0)
        return m

    def _need_ref(self):
        if self.L0 is None:
            raise RuntimeError("cable map has no length reference (L0) for this boot epoch")

    def _phi0(self) -> float:
        return self.spool.angle_from_wound(self.cfg.line_total_m - self.L0)

    # -- conversions -------------------------------------------------------
    def length(self, P: float) -> float:
        self._need_ref()
        if self.table is not None:
            return self.L0 + float(np.interp(P, self.table[:, 0], self.table[:, 1],
                                             left=np.nan, right=np.nan)) - float(
                np.interp(0.0, self.table[:, 0], self.table[:, 1]))
        phi = self._phi0() - 2 * math.pi * P / self.spr
        return self.cfg.line_total_m - self.spool.wound_from_angle(phi)

    def position(self, L: float) -> float:
        """Microstep position (float) at which the external length equals L."""
        self._need_ref()
        if self.table is not None:
            base = float(np.interp(0.0, self.table[:, 0], self.table[:, 1]))
            return float(np.interp(L - self.L0 + base, self.table[:, 1], self.table[:, 0],
                                   left=np.nan, right=np.nan))
        phi = self.spool.angle_from_wound(self.cfg.line_total_m - L)
        return (self._phi0() - phi) * self.spr / (2 * math.pi)

    def payout_per_ustep(self, L: float) -> float:
        """dL/dP at external length L (m per microstep)."""
        if self.table is not None:
            P = self.position(L)
            i = int(np.clip(np.searchsorted(self.table[:, 0], P), 1, len(self.table) - 1))
            dP = self.table[i, 0] - self.table[i - 1, 0]
            return float((self.table[i, 1] - self.table[i - 1, 1]) / dP)
        r = self.spool.radius_at_wound(self.cfg.line_total_m - L)
        return 2 * math.pi * r / self.spr

    def radius(self, L: float) -> float:
        return self.payout_per_ustep(L) * self.spr / (2 * math.pi)

    def payout(self, P_from: float, P_to: float) -> float:
        """Length change (+ = longer) between two positions; needs no L0 for the
        table model, and is evaluated around the current reference otherwise."""
        return self.length(P_to) - self.length(P_from)


def counts_per_ustep(counts_per_rev: int, usteps_per_rev: int) -> float:
    """Encoder counts per motor microstep for a spool-mounted (1:1) encoder."""
    return counts_per_rev / usteps_per_rev
