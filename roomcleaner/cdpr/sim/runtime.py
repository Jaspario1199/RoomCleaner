"""Simulated runtime: advances true time in fixed ticks and steps everything."""
from __future__ import annotations


class SimRuntime:
    def __init__(self, net, stations: dict, world=None, tick_us: int = 1000):
        self.net = net
        self.stations = stations
        self.world = world
        self.tick_us = tick_us
        self.t = 0.0
        self.hooks = []               # callables(t) for scripted fault injection

    def now_us(self) -> float:
        return self.t

    def wait(self, dt_us: float) -> None:
        end = self.t + dt_us
        while self.t < end - 1e-9:
            self.t += self.tick_us
            self.net.deliver(self.t)
            for sid, st in self.stations.items():
                out = st.tick(self.t, self.net.take(sid))
                for dest, msg in out:
                    self.net.send(sid, dest, msg, self.t)
            if self.world is not None:
                self.world.step(self.t, self.tick_us / 1e6)
            for h in list(self.hooks):
                h(self.t)
