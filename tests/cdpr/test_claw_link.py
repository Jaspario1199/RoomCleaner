"""Host claw client against a fake claw HTTP server (same endpoints/headers as
firmware/claw_s3)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np
import pytest

from roomcleaner.cdpr.claw_link import DetectorFrameSource, HttpClawClient
from roomcleaner.cdpr.frames import make_T, rpy_to_matrix
from roomcleaner.cdpr.vision.camera import CameraModel
from roomcleaner.cdpr.vision.marker import MarkerDetector, render_marker_view

CAM = CameraModel(np.array([[520.0, 0, 400], [0, 520, 300], [0, 0, 1]]), np.zeros(5), (800, 600), "t")
T_C_M = make_T(rpy_to_matrix(np.pi, 0, 0.3), [0.02, -0.01, 0.6])


class FakeClaw(BaseHTTPRequestHandler):
    state = {"grip": False, "tilt": 0.01}

    def log_message(self, *a):
        pass

    def _json(self, code, d):
        b = json.dumps(d).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/status":
            self._json(200, {"online": True, "t_us": 5_000_000, "battery_v": 7.9, "roll": self.state["tilt"],
                             "pitch": 0.0, "tilt_rad": self.state["tilt"], "imu_ok": True,
                             "grip_closed": self.state["grip"], "camera_mode": "SVGA-800x600-q10"})
        elif self.path == "/frame":
            img = render_marker_view(CAM, "apriltag_36h11", 0, 0.1524, T_C_M, noise=0.0)
            ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("X-Capture-Us", "4990000")
            self.send_header("X-Frame-Id", "7")
            self.send_header("X-Camera-Mode", "SVGA-800x600-q10")
            self.send_header("Content-Length", str(len(jpg)))
            self.end_headers()
            self.wfile.write(jpg.tobytes())

    def do_POST(self):
        if self.path.startswith("/grip"):
            close = "close=1" in self.path
            if close and self.state["tilt"] > 0.0873 and "force=1" not in self.path:
                return self._json(409, {"ok": False, "why": "claw not upright"})
            self.state["grip"] = close
            self._json(200, {"ok": True, "grip_closed": close})


@pytest.fixture()
def claw():
    srv = HTTPServer(("127.0.0.1", 0), FakeClaw)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    FakeClaw.state.update(grip=False, tilt=0.01)
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_status_clock_and_grip_gate(claw):
    c = HttpClawClient(claw, now_us=lambda: 1e9)
    s = c.status()
    assert s["online"] and abs(c.to_host_us(5_000_000) - 1e9) < 1
    assert c.grip(True) and FakeClaw.state["grip"]
    FakeClaw.state["tilt"] = 0.2
    c._status = None
    assert not c.grip(True)                     # refused by the claw: tilted


def test_real_frame_source_detects_marker(claw):
    c = HttpClawClient(claw)
    det = MarkerDetector("apriltag_36h11", 0, 0.1524, CAM)
    T_B_C = make_T(rpy_to_matrix(np.pi, 0, 0), [0.04, 0, -0.08])
    src = DetectorFrameSource(c, det, camera_mode="SVGA-800x600-q10", T_B_C=T_B_C)
    o = src.observe(0)
    assert o.ok, o.reason
    assert np.allclose(o.T_C_M[:3, 3], T_C_M[:3, 3], atol=0.005)
    bad = DetectorFrameSource(c, det, camera_mode="UXGA", T_B_C=T_B_C).observe(0)
    assert not bad.ok and "camera mode" in bad.reason
