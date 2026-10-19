"""Host <-> winch-station protocol, version 1.

Transport: UDP datagrams, one JSON object per datagram (< 512 bytes), so any
packet can be read in a capture. Every message carries ``"v": 1`` and a type
``"t"``. Stations stamp ``sid`` (A-D), ``boot`` (random 32-bit per power-up)
and a strictly increasing ``seq``.

Time
----
Each station runs its own microsecond clock (``micros()`` extended to 64 bit).
The host estimates every station's offset from SYNC round trips and converts
times itself, so **all times sent to a station are in that station's clock**.
Motion segments additionally carry *path time* ``tau`` (us since the motion's
start). Holds are expressed in path time, which is identical on all stations,
so a coordinated stop decelerates every cable along the same geometric path.

Messages host -> station
------------------------
cfg     {"t":"cfg", "p":{firmware params}}              -> ack (with "hash")
sync    {"t":"sync","h":host_us}                         -> sync_r
arm     {"t":"arm"}                                      -> ack  (driver enabled, holding)
disarm  {"t":"disarm","confirm":"claw_supported"}        -> ack  (removes holding torque!)
seg     {"t":"seg","m":motion,"i":index,"t0":local_us,"d":us,
         "p0":usteps,"p1":usteps,"v0":usteps_s,"v1":usteps_s,
         "last":bool,"ref":0|1|2}                        -> ack/nack
            ref 0 normal: switch actuation is a fault
            ref 1 reference capture: switch actuation is recorded and holds
            ref 2 reference release: switch may be active; release is recorded
hold    {"t":"hold","m":motion,"tau":path_us}            (also station-to-station)
cancel  {"t":"cancel","m":motion}   drop queued (not yet started) segments
clear   {"t":"clear"}                                    -> ack (only when stopped)
ping    {"t":"ping"}               lease keep-alive (any valid message renews)

Messages station -> host
------------------------
ack     {"t":"ack","re":type,"ok":bool,"why":str,"m":..,"i":..,"hash":..}
sync_r  {"t":"sync_r","h":host_us,"rx":local_us,"tx":local_us}
tel     telemetry, ~50 Hz (fields in TELEMETRY_FIELDS)
evt     {"t":"evt","k":kind,...}  kinds: boot, fault, hold, done, capture, release
hold    station-originated hold, broadcast to peers and host
"""
from __future__ import annotations

import json
import zlib

VERSION = 1
MAX_DATAGRAM = 512


class State:
    OFF = 0       # driver disabled (no holding torque)
    IDLE = 1      # enabled, holding position
    RUN = 2       # executing a motion
    HOLD = 3      # decelerating along the path (coordinated stop)
    FAULT = 4     # latched fault, stopped, still enabled (holding)
    NAMES = {0: "OFF", 1: "IDLE", 2: "RUN", 3: "HOLD", 4: "FAULT"}


class Fault:
    NONE = 0
    TRACKING = 1    # encoder disagrees with commanded steps beyond tolerance/dwell
    ENCODER = 2     # stale, unreadable or bad-magnet encoder
    SWITCH = 3      # bead switch open when not expected (actuated or broken wire)
    LEASE = 4       # no valid host message within the lease
    UNDERRUN = 5    # motion buffer would run out before the stop distance
    TIMING = 6      # control loop overran its period
    CONFIG = 7      # no/invalid configuration
    NAMES = {0: "NONE", 1: "TRACKING", 2: "ENCODER", 3: "SWITCH", 4: "LEASE",
             5: "UNDERRUN", 6: "TIMING", 7: "CONFIG"}
    # How the station reacts: 'stop' = no further pulses this instant
    # (motion cannot be trusted / would worsen a jam); 'hold' = coordinated
    # path deceleration first (motion is fine, coordination is at risk).
    REACTION = {1: "stop", 2: "stop", 3: "stop", 4: "hold", 5: "hold", 6: "stop", 7: "stop"}


TELEMETRY_FIELDS = ("sid", "boot", "seq", "now", "st", "flt", "pos", "enc", "encv", "sw",
                    "swr", "m", "i", "tau", "buf", "terr", "cap")

REQUIRED_PARAMS = ("sid", "usteps_per_rev", "step_sign", "max_rate_hz", "counts_per_rev",
                   "enc_sign", "enc_max_age_us", "track_tol", "track_dwell_us", "lease_us",
                   "sw_nc", "debounce_us", "hold_us")


def params_hash(params: dict) -> int:
    """CRC32 of the canonical parameter string; identical in firmware."""
    canon = ";".join(f"{k}={_canon(params[k])}" for k in REQUIRED_PARAMS)
    return zlib.crc32(canon.encode("ascii")) & 0xFFFFFFFF


def _canon(v) -> str:
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return str(int(round(v))) if float(v).is_integer() else f"{v:.6f}"
    return str(v)


def encode(msg: dict) -> bytes:
    m = dict(msg)
    m.setdefault("v", VERSION)
    data = json.dumps(m, separators=(",", ":")).encode("ascii")
    if len(data) > MAX_DATAGRAM:
        raise ValueError(f"message too large ({len(data)} bytes): {m.get('t')}")
    return data


def decode(data: bytes) -> dict | None:
    """Parse a datagram; returns None for anything malformed or wrong version."""
    try:
        m = json.loads(data.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(m, dict) or m.get("v") != VERSION or not isinstance(m.get("t"), str):
        return None
    return m
