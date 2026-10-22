"""Host side of the claw node (firmware/claw_s3): HTTP client, clock mapping,
and the real frame source feeding the marker detector.

Timing: frames carry the claw's capture time (esp_timer, us). The claw clock
is mapped to the host clock with the minimum-RTT offset from /status polls,
so frame ages are judged in host time like everything else.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

import cv2
import numpy as np


class ClawError(RuntimeError):
    pass


@dataclass(frozen=True)
class CachedFrame:
    """The newest claw JPEG the frame thread already fetched, kept for the phone app (service /api/frame.jpg and the MJPEG
    stream read ONLY this: they never fetch from the claw). ``capture_us`` is in HOST time like every frame time here;
    ``cached_at`` is ``time.monotonic()`` when it was stored, ``lag_s`` the receive-minus-capture delay at that moment
    (so age = now - cached_at + lag_s)."""
    jpeg: bytes
    capture_us: float
    frame_id: int
    mode: str
    cached_at: float
    lag_s: float

    def age_s(self, now_monotonic: float | None = None) -> float:
        return (time.monotonic() if now_monotonic is None else now_monotonic) - self.cached_at + self.lag_s


class HttpClawClient:
    # Every call is blocking HTTP (``timeout_s``, 1 s) -- longer than faults.lease_s. The task layer (tasks.TaskRunner._grip,
    # garments.ClawGarmentPerception._frame) therefore runs the grip and the colour-frame grab on the pumped worker while this
    # link is in use; a claw object without this attribute (the simulator's) is called directly on the command thread.
    blocking_io = True

    def __init__(self, base_url: str, *, timeout_s=1.0, now_us=None, status_ttl_s=0.1):
        self.base = base_url.rstrip("/")
        self.timeout = timeout_s
        self.now_us = now_us or (lambda: time.monotonic() * 1e6)
        self.offset_us = None          # host = claw + offset
        self.best_rtt = float("inf")
        self.ttl = status_ttl_s
        self._status = None
        self._status_t = -1e18
        self.last_cached: CachedFrame | None = None   # set by frame() (the frame thread); read by the phone app

    def _get(self, path, method="GET"):
        req = urllib.request.Request(self.base + path, method=method)
        return urllib.request.urlopen(req, timeout=self.timeout)

    # -- status / clock ---------------------------------------------------
    def status(self) -> dict:
        now = self.now_us()
        if self._status is not None and now - self._status_t < self.ttl * 1e6:
            return self._status
        t0 = self.now_us()
        try:
            with self._get("/status") as r:
                d = json.loads(r.read())
        except Exception as e:                       # network errors -> offline
            return {"online": False, "error": str(e)}
        t1 = self.now_us()
        rtt = t1 - t0
        if rtt <= self.best_rtt * 1.5 or self.offset_us is None:
            self.best_rtt = min(self.best_rtt, rtt)
            self.offset_us = (t0 + t1) / 2 - d["t_us"]
        self._status, self._status_t = d, t1
        return d

    def to_host_us(self, claw_us: float) -> float:
        if self.offset_us is None:
            self.status()
        return claw_us + (self.offset_us or 0.0)

    # -- actions ---------------------------------------------------------
    def grip(self, close: bool) -> bool:
        """Close / open the claw. The claw node has no IMU and no tilt gate (D27): it obeys; the host decides whether
        the grip is approved (tasks.TaskRunner: settle, then approve). False if the claw answered ok=false."""
        try:
            with self._get(f"/grip?close={int(close)}", "POST") as r:
                return bool(json.loads(r.read()).get("ok"))
        except urllib.error.HTTPError as e:
            if e.code == 400:
                return False                          # claw rejected the request parameters
            raise ClawError(f"grip failed: HTTP {e.code}")

    def frame(self):
        """(BGR image, capture time in HOST us, frame id, camera mode)."""
        with self._get("/frame") as r:
            data = r.read()
            cap = float(r.headers["X-Capture-Us"])
            fid = int(r.headers["X-Frame-Id"])
            mode = r.headers.get("X-Camera-Mode", "")
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ClawError("undecodable JPEG")
        host_cap = self.to_host_us(cap)
        # phone app: keep the bytes just fetched (one reference assignment, no extra request to the claw). ``lag_s`` is for the
        # age display only: with no usable clock mapping yet (negative or absurd) it is 0 and the age is the time in the cache.
        lag = (self.now_us() - host_cap) / 1e6
        self.last_cached = CachedFrame(data, host_cap, fid, mode, time.monotonic(), lag if 0.0 <= lag <= 5.0 else 0.0)
        return img, host_cap, fid, mode


def frame_bgr(client: "HttpClawClient"):
    """Colour frame for the garment detector (the marker path uses grayscale)."""
    with client._get("/frame") as r:
        data = r.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ClawError("undecodable JPEG")
    return img


class DetectorFrameSource:
    """frame_source for perception.VisionSource on real hardware."""

    def __init__(self, client: HttpClawClient, detector, *, camera_mode: str, T_B_C):
        self.client = client
        self.det = detector
        self.mode = camera_mode
        self.R_C_B = np.asarray(T_B_C)[:3, :3].T
        self.prev = None

    def observe(self, now_us):
        from .vision.marker import MarkerObservation
        try:
            img, cap, fid, mode = self.client.frame()
        except Exception as e:
            return MarkerObservation(False, f"no frame: {e}")
        if self.mode and mode != self.mode:
            return MarkerObservation(False, f"camera mode {mode!r} != calibrated {self.mode!r}")
        # no IMU (D27): the disambiguation prior is "claw upright", i.e. world up = body z, seen from the nominal mount
        # (the detector's upright tolerance is far larger than any mount error)
        up_cam = self.R_C_B @ np.array([0.0, 0.0, 1.0])
        obs = self.det.detect(img, prev_T_C_M=self.prev, up_in_cam=up_cam, frame_id=fid, capture_us=cap)
        if obs.ok:
            self.prev = obs.T_C_M
        return obs

    def latest_frame(self):
        """The newest JPEG this source fetched (``CachedFrame``) or None; never fetches."""
        return self.client.last_cached


class ThreadedFrameSource:
    """Runs a (blocking, HTTP) frame source on its own thread so the control
    loop never waits on the network (review H4). ``observe`` returns the
    newest result without blocking; staleness is judged by VisionSource from
    the frame's capture time."""

    def __init__(self, inner, *, period_s=0.05):
        import threading
        from .vision.marker import MarkerObservation
        self.inner = inner
        self.period = period_s
        self.latest = MarkerObservation(False, "no frame yet")
        self.error = None
        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True, name="claw-frames").start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.latest = self.inner.observe(None)
                self.error = None
            except Exception as e:                    # surfaced through the observation reason
                from .vision.marker import MarkerObservation
                self.error = f"{type(e).__name__}: {e}"
                self.latest = MarkerObservation(False, f"frame thread: {self.error}")
            time.sleep(self.period)

    def observe(self, now_us):
        return self.latest

    def latest_frame(self):
        """Newest cached JPEG of the inner source (``CachedFrame``) or None. Reads the cache only: the frame thread is the
        sole client of the claw's /frame."""
        fn = getattr(self.inner, "latest_frame", None)
        return fn() if fn else None

    def stop(self):
        self._stop.set()
