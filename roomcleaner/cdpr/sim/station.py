"""A simulated winch station: StationCore + motor + encoder + switch + clock."""
from __future__ import annotations

import random

from ..station_core import StationCore


class SimStation:
    def __init__(self, sid, *, usteps_per_rev, counts_per_rev=4096, enc_sign=1,
                 clock_offset_us=0.0, drift_ppm=0.0, seed=0, period_us=1000):
        self.sid = sid
        self.rng = random.Random(seed)
        self.offset = clock_offset_us
        self.drift = drift_ppm * 1e-6
        self.period_us = period_us
        self.spr = usteps_per_rev
        self.cpr = counts_per_rev
        self.enc_sign = enc_sign
        self.motor = 0.0              # physical spool position in microsteps (+ payout)
        self.stalled = False          # injected: motor ignores steps (jam / lost steps)
        self.enc_broken = False       # injected: encoder unreadable
        self.enc_noise_counts = 0.6
        self.powered = True
        self.switch_fn = lambda: False   # set by the world: is the bead at the switch?
        self.boot_n = 0
        self._new_core()

    def _new_core(self):
        self.boot_n += 1
        self.core = StationCore(boot_id=self.rng.getrandbits(32), period_us=self.period_us)
        # a reboot loses the multi-turn epoch: firmware counts restart at 0
        self.enc_base = self.motor
        self.pos_base = self.motor

    def local(self, t_true_us: float) -> int:
        return int(t_true_us * (1 + self.drift) + self.offset)

    def reboot(self):
        self._new_core()

    def tick(self, t_true_us: float, inbox: list) -> list:
        if not self.powered:
            return []
        now = self.local(t_true_us)
        for src, msg in inbox:
            self.core.handle(msg, now, from_host=(src == "host"))
        rel = self.motor - self.enc_base
        counts = rel * self.cpr / self.spr * self.enc_sign + self.rng.gauss(0, self.enc_noise_counts)
        steps = self.core.update(now, int(round(counts)), not self.enc_broken, bool(self.switch_fn()))
        if not self.stalled and self.core.armed:
            self.motor += steps
        return self.core.drain()

    @property
    def motor_rel(self) -> float:
        """Physical position in the current firmware epoch's microsteps."""
        return self.motor - self.pos_base
