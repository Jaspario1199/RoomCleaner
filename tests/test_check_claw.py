"""tools/check_claw.py against a fake claw node speaking the claw_s3 HTTP endpoints."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np
import pytest

from tools import check_claw


class FakeClaw(BaseHTTPRequestHandler):
    state = {"grip_closed": False, "servo_us": 900, "frame_id": 0}
    jpeg = cv2.imencode(".jpg", np.full((60, 80), 128, np.uint8))[1].tobytes()

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", headers=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in headers:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        s = FakeClaw.state
        if self.path == "/status":
            d = {"online": True, "t_us": 1_000_000, "battery_v": 7.6, "battery_low": False, "camera_ok": True,
                 "camera_mode": "SVGA-800x600-q10", **s}
            self._send(200, json.dumps(d).encode())
        elif self.path == "/frame":
            s["frame_id"] += 1
            self._send(200, FakeClaw.jpeg, "image/jpeg", [("X-Capture-Us", "1000000"), ("X-Frame-Id", str(s["frame_id"])),
                                                         ("X-Camera-Mode", "SVGA-800x600-q10")])
        else:
            self._send(404, b"{}")

    def do_POST(self):
        if self.path.startswith("/grip?close="):
            close = self.path.endswith("=1")
            FakeClaw.state.update(grip_closed=close, servo_us=2000 if close else 900)
            self._send(200, json.dumps({"ok": True, "grip_closed": close}).encode())
        else:
            self._send(400, b'{"ok":false}')


@pytest.fixture
def claw():
    srv = HTTPServer(("127.0.0.1", 0), FakeClaw)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_status_frames_and_grip_pass_against_the_endpoints(claw, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert check_claw.main([claw, "status"]) == 0
    assert check_claw.main([claw, "frames", "--n", "2"]) == 0
    assert len(list((tmp_path / "data" / "claw_check").glob("*.jpg"))) == 2
    monkeypatch.setattr("builtins.input", lambda q: "y")
    assert check_claw.main([claw, "grip", "close"]) == 0 and FakeClaw.state["grip_closed"] is True
    assert check_claw.main([claw, "grip", "open"]) == 0 and FakeClaw.state["grip_closed"] is False
    recs = [json.loads(x) for x in (tmp_path / "data" / "commissioning" / "claw.jsonl").read_text().splitlines()]
    assert [r["pass"] for r in recs] == [True, True, True, True]


def test_close_is_refused_without_confirmation(claw, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    FakeClaw.state.update(grip_closed=False, servo_us=900)
    monkeypatch.setattr("builtins.input", lambda q: "n")
    assert check_claw.main([claw, "grip", "close"]) == 1
    assert FakeClaw.state["grip_closed"] is False


def test_offline_claw_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert check_claw.main(["127.0.0.1:9", "status"]) == 1
