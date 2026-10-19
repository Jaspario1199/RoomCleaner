"""Host-side record of one winch station.

Tracks the station's boot epoch, telemetry freshness, sequence order, clock
model, acknowledgements and events. A change of boot id means the station
rebooted: its multi-turn position epoch is gone and every length reference
tied to it is invalid (see trust.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .clock import ClockModel
from .protocol import Fault, State


@dataclass
class StationLink:
    sid: str
    clock: ClockModel = field(default_factory=ClockModel)
    boot: int | None = None
    boot_changed: bool = False
    last_seq: int = -1
    tel: dict | None = None
    tel_host_t: float = -1e18
    expected_hash: int | None = None
    acks: list = field(default_factory=list)
    events: list = field(default_factory=list)
    _seen_events: set = field(default_factory=set)
    sync_pending: dict = field(default_factory=dict)

    def ingest(self, msg: dict, host_now: float) -> None:
        boot = msg.get("boot")
        if boot is not None:
            if self.boot is None:
                self.boot = boot
            elif boot != self.boot:
                self.boot = boot
                self.boot_changed = True
                self.last_seq = -1
                self.tel = None
                self.clock = ClockModel()
                self._seen_events.clear()
        seq = msg.get("seq", -1)
        t = msg.get("t")
        if t == "tel":
            # only state snapshots need ordering; acks/events are idempotent
            if seq <= self.last_seq:
                return
            self.last_seq = seq
            self.tel = msg
            self.tel_host_t = host_now
        elif t == "sync_r":
            h0 = msg.get("h")
            if h0 in self.sync_pending:
                self.sync_pending.pop(h0)
                self.clock.add(h0, msg["rx"], msg["tx"], host_now)
        elif t == "ack":
            self.acks.append(msg)
        elif t == "evt":
            key = (msg.get("boot"), msg.get("e"))
            if key not in self._seen_events:
                self._seen_events.add(key)
                self.events.append(msg)
        elif t == "hold":
            self.events.append(dict(msg, k="peer_hold"))

    # ------------------------------------------------------------ queries
    def fresh(self, host_now: float, max_age_us: float) -> bool:
        return self.tel is not None and host_now - self.tel_host_t <= max_age_us

    def health(self, host_now: float, max_age_us: float, clock_budget_us: float) -> list[str]:
        out = []
        if self.boot_changed:
            out.append("rebooted")
        if not self.fresh(host_now, max_age_us):
            out.append("telemetry stale")
            return out
        tel = self.tel
        if tel["flt"] != Fault.NONE:
            out.append(f"fault {Fault.NAMES.get(tel['flt'], tel['flt'])}")
        if not tel.get("encv"):
            out.append("encoder invalid")
        if self.expected_hash is not None and tel.get("hash") != self.expected_hash:
            out.append("config hash mismatch")
        if self.clock.uncertainty(host_now) > clock_budget_us:
            out.append(f"clock uncertainty {self.clock.uncertainty(host_now):.0f} us")
        return out

    @property
    def state(self) -> int | None:
        return None if self.tel is None else self.tel["st"]

    @property
    def pos(self) -> int | None:
        return None if self.tel is None else self.tel["pos"]

    def take_acks(self, re: str, **match):
        hit, keep = [], []
        for a in self.acks:
            if a.get("re") == re and all(a.get(k) == v for k, v in match.items()):
                hit.append(a)
            else:
                keep.append(a)
        self.acks = keep
        return hit

    def take_events(self, kind: str | None = None):
        hit = [e for e in self.events if kind is None or e.get("k") == kind]
        self.events = [e for e in self.events if not (kind is None or e.get("k") == kind)]
        return hit


def state_name(st):
    return State.NAMES.get(st, str(st))
