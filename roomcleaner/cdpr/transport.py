"""Message transport: real UDP and an in-memory simulated network.

Both expose the same host-side interface:

    send(dest, msg)      dest = station id, or "*" for every station
    recv() -> [(src, msg), ...]

The simulated network routes station-originated broadcasts ("*") to the
host and all *other* stations, exactly like a UDP broadcast on the LAN, and
models latency, jitter, loss and link outages so fault handling can be tested.
"""
from __future__ import annotations

import heapq
import random
import socket
from dataclasses import dataclass, field

from . import protocol


class UdpHostTransport:
    """Host UDP endpoint. ``stations`` maps id -> (ip, port)."""

    def __init__(self, stations: dict[str, tuple[str, int]], bind=("0.0.0.0", 8770)):
        self.stations = dict(stations)
        self.by_addr = {v: k for k, v in self.stations.items()}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(bind)
        self.sock.setblocking(False)

    def send(self, dest: str, msg: dict) -> None:
        data = protocol.encode(msg)
        targets = self.stations.values() if dest == "*" else [self.stations[dest]]
        for addr in targets:
            try:
                self.sock.sendto(data, addr)
            except OSError:
                pass  # surfaced by missing acks/telemetry, never by blocking

    def recv(self) -> list[tuple[str, dict]]:
        out = []
        while True:
            try:
                data, addr = self.sock.recvfrom(protocol.MAX_DATAGRAM + 64)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            msg = protocol.decode(data)
            if msg is None:
                continue
            sid = self.by_addr.get(addr) or msg.get("sid")
            if sid in self.stations:
                out.append((sid, msg))
        return out

    def close(self):
        self.sock.close()


@dataclass(order=True)
class _Pending:
    t: float
    n: int
    dest: str = field(compare=False)
    src: str = field(compare=False)
    data: bytes = field(compare=False)


class SimNetwork:
    """Deterministic (seeded) network between 'host' and stations."""

    def __init__(self, nodes, *, latency_us=2000, jitter_us=1500, loss=0.0, seed=0):
        self.nodes = list(nodes)
        self.latency_us = latency_us
        self.jitter_us = jitter_us
        self.loss = loss
        self.rng = random.Random(seed)
        self.q: list[_Pending] = []
        self.n = 0
        self.inbox: dict[str, list] = {k: [] for k in ["host"] + self.nodes}
        self.down: set[str] = set()          # nodes whose link is cut (both directions)
        self.stats = {"sent": 0, "dropped": 0}

    def send(self, src: str, dest: str, msg: dict, now: float) -> None:
        data = protocol.encode(msg)
        if dest == "*":
            dests = [n for n in self.nodes if n != src] + (["host"] if src != "host" else [])
        else:
            dests = [dest]
        for d in dests:
            self.stats["sent"] += 1
            if src in self.down or d in self.down or self.rng.random() < self.loss:
                self.stats["dropped"] += 1
                continue
            lat = self.latency_us + self.rng.uniform(0, self.jitter_us)
            self.n += 1
            heapq.heappush(self.q, _Pending(now + lat, self.n, d, src, data))

    def deliver(self, now: float) -> None:
        while self.q and self.q[0].t <= now:
            p = heapq.heappop(self.q)
            msg = protocol.decode(p.data)
            if msg is not None:
                self.inbox[p.dest].append((p.src, msg))

    def take(self, node: str) -> list:
        out, self.inbox[node] = self.inbox[node], []
        return out


class SimHostTransport:
    """Host view of a SimNetwork (same interface as UdpHostTransport)."""

    def __init__(self, net: SimNetwork, now_fn):
        self.net, self.now_fn = net, now_fn

    def send(self, dest, msg):
        self.net.send("host", dest, msg, self.now_fn())

    def recv(self):
        return self.net.take("host")
