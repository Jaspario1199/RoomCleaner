"""Host-side estimate of one station's clock.

Each SYNC round trip gives host send time h0, station receive/send times
rx/tx and host receive time h1. Assuming symmetric delay:

    offset = ((rx - h0) + (tx - h1)) / 2        (station - host)
    rtt    = (h1 - h0) - (tx - rx)

Delay asymmetry is bounded by rtt/2, so samples with the smallest rtt are the
most trustworthy. We keep a sliding window, take the lowest-rtt quartile, and
fit offset = a + b * host_time (b = relative drift). The reported uncertainty
is half the best rtt plus the fit residual and the drift extrapolation since
the newest sample; motion is refused when it exceeds the configured budget.
"""
from __future__ import annotations

from collections import deque

import numpy as np


class ClockModel:
    def __init__(self, window: int = 40):
        self.samples: deque = deque(maxlen=window)
        self.a = 0.0
        self.b = 0.0
        self.t_ref = 0.0
        self.unc_base = float("inf")
        self.last_h = None

    def add(self, h0: int, rx: int, tx: int, h1: int) -> None:
        rtt = (h1 - h0) - (tx - rx)
        if rtt < 0 or h1 < h0:
            return
        off = ((rx - h0) + (tx - h1)) / 2.0
        self.samples.append((float(h1), off, float(rtt)))
        self.last_h = h1
        self._fit()

    def _fit(self):
        s = np.array(self.samples)
        k = max(3, len(s) // 4)
        best = s[np.argsort(s[:, 2])[:k]]
        t, off, rtt = best[:, 0], best[:, 1], best[:, 2]
        self.t_ref = float(t.mean())
        if len(best) >= 3 and np.ptp(t) > 1e5:
            b, a = np.polyfit(t - self.t_ref, off, 1)
        else:
            b, a = 0.0, float(np.median(off))
        self.a, self.b = float(a), float(b)
        resid = off - (self.a + self.b * (t - self.t_ref))
        self.unc_base = float(rtt.min() / 2 + 2 * (np.std(resid) if len(resid) > 1 else rtt.min() / 2))

    @property
    def ready(self) -> bool:
        return len(self.samples) >= 3

    def offset(self, host_us: float) -> float:
        return self.a + self.b * (host_us - self.t_ref)

    def to_local(self, host_us: float) -> int:
        return int(round(host_us + self.offset(host_us)))

    def to_host(self, local_us: float) -> float:
        # invert local = h + a + b (h - t_ref)
        return (local_us - self.a + self.b * self.t_ref) / (1 + self.b)

    def uncertainty(self, host_us: float) -> float:
        if not self.ready:
            return float("inf")
        age = abs(host_us - (self.last_h or host_us))
        return self.unc_base + 50e-6 * age   # 50 ppm residual-drift allowance since the last sample
