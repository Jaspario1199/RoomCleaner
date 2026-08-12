"""The RoomCleaner live web app.

Design (why two threads):
  * a CAPTURE thread pulls frames from the camera as fast as it can, so the
    video stays smooth;
  * an INFERENCE thread runs the (slow, ~1-2 fps on CPU) YOLO-World detector on
    the latest frame and caches the boxes;
  * the MJPEG generator draws the latest boxes onto the latest frame at display
    rate. So the feed never stutters while waiting on the model.

Everything the detector produces here is exactly what the real robot's control
loop consumes (floor (x, y) Detections), so this dashboard is a window onto the
actual perception the robot acts on -- not a separate demo.
"""
from __future__ import annotations

import threading
import time

import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template_string, request

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.perception.localization import OverheadLinearMapper
from roomcleaner.perception.vision_detector import (
    DEFAULT_LAUNDRY_CLASSES,
    YoloWorldDetector,
)

BOX_COLOR = (80, 220, 80)      # BGR green
HUD_COLOR = (0, 220, 0)


class DetectorApp:
    """Owns the camera + detector and the shared latest-frame / latest-detections
    state that the Flask routes read."""

    def __init__(
        self,
        camera_index: int = 1,
        width: int = 1280,
        height: int = 720,
        conf: float = 0.25,
        classes: list[str] | None = None,
        backend: str = "dshow",
        model_name: str = "yolov8s-world.pt",
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.conf = conf
        self.classes = list(classes or DEFAULT_LAUNDRY_CLASSES)
        self.backend = backend
        self.model_name = model_name

        self.cfg = DEFAULT_CONFIG
        self._frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._dets: list[dict] = []
        self._dets_lock = threading.Lock()
        self.stats = {
            "resolution": None,
            "cam_fps": 0.0,
            "infer_fps": 0.0,
            "model_ready": False,
            "frames": 0,
        }
        self._running = False
        self._cap = None
        self._detector: YoloWorldDetector | None = None
        self._mapper = None

    # -- lifecycle -----------------------------------------------------------
    def _open_camera(self):
        be = cv2.CAP_DSHOW if (self.backend == "dshow" and hasattr(cv2, "CAP_DSHOW")) else 0
        cap = cv2.VideoCapture(self.camera_index, be)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not cap.isOpened():
            raise RuntimeError(
                f"Could not open camera index {self.camera_index}. "
                f"Close any app using it and check the index."
            )
        return cap

    def start(self):
        self._cap = self._open_camera()
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.width
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.height
        self.stats["resolution"] = f"{w}x{h}"
        self._mapper = OverheadLinearMapper(self.cfg.room_width, self.cfg.room_depth, w, h)
        self._detector = YoloWorldDetector(
            self._mapper, classes=self.classes, model_name=self.model_name, confidence=self.conf
        )
        self._running = True
        threading.Thread(target=self._capture_loop, name="capture", daemon=True).start()
        threading.Thread(target=self._infer_loop, name="infer", daemon=True).start()

    def stop(self):
        self._running = False
        time.sleep(0.2)
        if self._cap is not None:
            self._cap.release()

    # -- worker loops --------------------------------------------------------
    def _capture_loop(self):
        for _ in range(5):  # warm up the sensor
            self._cap.read()
        t0, n = time.time(), 0
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.03)
                continue
            with self._frame_lock:
                self._frame = frame
            n += 1
            if n >= 30:
                dt = time.time() - t0
                self.stats["cam_fps"] = round(n / dt, 1) if dt > 0 else 0.0
                t0, n = time.time(), 0

    def _infer_loop(self):
        t0, n = time.time(), 0
        while self._running:
            with self._frame_lock:
                frame = None if self._frame is None else self._frame.copy()
            if frame is None:
                time.sleep(0.05)
                continue
            self._detector.confidence = self.conf  # live sensitivity changes
            try:
                dets = self._detector.detect(frame)
                self.stats["model_ready"] = True
            except Exception as exc:  # keep the app alive if a frame trips the model
                print(f"[infer] {exc}", flush=True)
                dets = []
            out = [
                {
                    "label": str(d.label),
                    "confidence": float(d.confidence),
                    "floor": [float(d.position[0]), float(d.position[1])],
                    "bbox": [float(v) for v in d.bbox] if d.bbox else None,
                    "area": float(d.area),
                }
                for d in dets
            ]
            out.sort(key=lambda d: d["confidence"], reverse=True)
            with self._dets_lock:
                self._dets = out
            n += 1
            self.stats["frames"] += 1
            dt = time.time() - t0
            if dt >= 1.0:
                self.stats["infer_fps"] = round(n / dt, 1)
                t0, n = time.time(), 0
            time.sleep(0.01)

    # -- frame rendering -----------------------------------------------------
    def _annotated_jpeg(self) -> bytes | None:
        with self._frame_lock:
            frame = None if self._frame is None else self._frame.copy()
        if frame is None:
            frame = np.zeros((self.height, self.width, 3), np.uint8)
            cv2.putText(frame, "waiting for camera...", (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, HUD_COLOR, 2)
        with self._dets_lock:
            dets = list(self._dets)
        for d in dets:
            if not d["bbox"]:
                continue
            x1, y1, x2, y2 = (int(v) for v in d["bbox"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)
            fx, fy = d["floor"]
            cv2.putText(
                frame, f'{d["label"]} {d["confidence"]:.2f}  @({fx:.1f},{fy:.1f})m',
                (x1, max(y1 - 8, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, BOX_COLOR, 2,
            )
        hud = (f'cam {self.stats["cam_fps"]}fps | infer {self.stats["infer_fps"]}fps | '
               f'{len(dets)} item(s)')
        if not self.stats["model_ready"]:
            hud = "loading detector (first run downloads weights)... | " + hud
        cv2.putText(frame, hud, (10, frame.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, HUD_COLOR, 2)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes() if ok else None

    def mjpeg_generator(self, fps: float = 20.0):
        period = 1.0 / fps
        while True:
            jpg = self._annotated_jpeg()
            if jpg is not None:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            time.sleep(period)

    def snapshot(self) -> dict:
        with self._dets_lock:
            dets = list(self._dets)
        return {
            "camera": self.camera_index,
            "resolution": self.stats["resolution"],
            "cam_fps": self.stats["cam_fps"],
            "infer_fps": self.stats["infer_fps"],
            "model_ready": self.stats["model_ready"],
            "conf": self.conf,
            "classes": self.classes,
            "room": {"width": self.cfg.room_width, "depth": self.cfg.room_depth},
            "detections": dets,
        }


def create_app(state: DetectorApp) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template_string(INDEX_HTML)

    @app.route("/video_feed")
    def video_feed():
        return Response(state.mjpeg_generator(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/snapshot.jpg")
    def snapshot_jpg():
        jpg = state._annotated_jpeg()
        if jpg is None:
            return Response(status=503)
        return Response(jpg, mimetype="image/jpeg")

    @app.route("/api/state")
    def api_state():
        return jsonify(state.snapshot())

    @app.route("/api/config", methods=["POST"])
    def api_config():
        data = request.get_json(force=True, silent=True) or {}
        if "conf" in data:
            try:
                state.conf = max(0.05, min(0.9, float(data["conf"])))
            except (TypeError, ValueError):
                pass
        return jsonify({"conf": state.conf})

    return app


# --------------------------------------------------------------------------
# Dashboard page. Self-contained (inline CSS/JS) so it needs no build step.
# The reserved "Robot & plan" panel is where the 3D room view, pickup plan,
# and controls will land as the app grows into the full RoomCleaner console.
# --------------------------------------------------------------------------
INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RoomCleaner — Live</title>
<style>
  :root{
    --bg:#0d1117; --panel:#161b22; --panel2:#1c232c; --border:#2a323d;
    --text:#e6edf3; --muted:#8b98a5; --accent:#3fb950; --accent-dim:#2ea043;
    --warn:#d29922;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  header{display:flex;align-items:center;gap:14px;padding:14px 20px;
    border-bottom:1px solid var(--border);background:var(--panel)}
  header .dot{width:10px;height:10px;border-radius:50%;background:var(--warn);
    box-shadow:0 0 8px var(--warn)}
  header .dot.live{background:var(--accent);box-shadow:0 0 8px var(--accent)}
  header h1{font-size:16px;margin:0;font-weight:650;letter-spacing:.2px}
  header .sub{color:var(--muted);font-size:12px}
  header .spacer{flex:1}
  header .stat{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}
  header .stat b{color:var(--text);font-weight:600}
  main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px;padding:16px;
    align-items:start}
  @media(max-width:900px){main{grid-template-columns:1fr}}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:12px;overflow:hidden}
  .card h2{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
    margin:0;padding:12px 14px;border-bottom:1px solid var(--border)}
  .feed{position:relative;background:#000;display:flex;justify-content:center}
  .feed img{max-width:100%;display:block}
  .controls{padding:12px 14px;display:flex;align-items:center;gap:12px;
    border-top:1px solid var(--border);font-size:13px;color:var(--muted);flex-wrap:wrap}
  .controls input[type=range]{flex:1;min-width:120px;accent-color:var(--accent)}
  .controls b{color:var(--text)}
  .side{display:flex;flex-direction:column;gap:16px}
  #detlist{padding:8px;display:flex;flex-direction:column;gap:6px;min-height:60px}
  .det{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:8px 10px}
  .det .row{display:flex;justify-content:space-between;align-items:baseline}
  .det .lab{font-weight:600;text-transform:capitalize}
  .det .co{font:12px ui-monospace,monospace;color:var(--accent)}
  .det .meta{color:var(--muted);font:11px ui-monospace,monospace;margin-top:3px}
  .bar{height:4px;border-radius:2px;background:#30363d;margin-top:6px;overflow:hidden}
  .bar>span{display:block;height:100%;background:var(--accent)}
  .empty{color:var(--muted);font-size:13px;padding:14px;text-align:center}
  .chips{display:flex;flex-wrap:wrap;gap:6px;padding:12px 14px}
  .chip{font-size:11px;color:var(--muted);background:var(--panel2);border:1px solid var(--border);
    border-radius:999px;padding:3px 9px}
  .soon{padding:16px 14px;color:var(--muted);font-size:12.5px;line-height:1.5}
  .soon ul{margin:8px 0 0;padding-left:18px} .soon li{margin:2px 0}
</style>
</head>
<body>
<header>
  <span class="dot" id="livedot"></span>
  <div>
    <h1>RoomCleaner <span class="sub">— live perception</span></h1>
  </div>
  <div class="spacer"></div>
  <div class="stat">cam <b id="s_res">–</b> · <b id="s_camfps">0</b> fps &nbsp;|&nbsp;
    detect <b id="s_inferfps">0</b> fps &nbsp;|&nbsp; <b id="s_count">0</b> items</div>
</header>

<main>
  <section class="card">
    <h2>Camera feed — detections drawn live</h2>
    <div class="feed"><img id="feed" src="/video_feed" alt="live feed"></div>
    <div class="controls">
      <label>sensitivity (confidence ≥ <b id="confval">0.25</b>)</label>
      <input type="range" id="conf" min="0.05" max="0.90" step="0.05" value="0.25">
    </div>
  </section>

  <section class="side">
    <div class="card">
      <h2>Detected items</h2>
      <div id="detlist"><div class="empty">watching the floor…</div></div>
    </div>
    <div class="card">
      <h2>Looking for</h2>
      <div class="chips" id="chips"></div>
    </div>
    <div class="card">
      <h2>Robot &amp; plan</h2>
      <div class="soon">
        Reserved for the rest of the console:
        <ul>
          <li>3-D room view with the pickup plan</li>
          <li>cable-length / winch commands per target</li>
          <li>robot status: position, payload, hamper count</li>
          <li>run / pause controls</li>
        </ul>
      </div>
    </div>
  </section>
</main>

<script>
const el = id => document.getElementById(id);
const confInput = el('conf');
confInput.addEventListener('input', () => {
  el('confval').textContent = (+confInput.value).toFixed(2);
});
confInput.addEventListener('change', () => {
  fetch('/api/config', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({conf: +confInput.value})});
});

let confDirty = false;
confInput.addEventListener('input', () => confDirty = true);

async function poll(){
  try{
    const s = await (await fetch('/api/state')).json();
    el('s_res').textContent = s.resolution || '–';
    el('s_camfps').textContent = s.cam_fps;
    el('s_inferfps').textContent = s.infer_fps;
    el('s_count').textContent = s.detections.length;
    el('livedot').classList.toggle('live', s.model_ready);
    if(!confDirty){ confInput.value = s.conf; el('confval').textContent = (+s.conf).toFixed(2); }

    const chips = el('chips');
    if(chips.childElementCount !== s.classes.length){
      chips.innerHTML = s.classes.map(c => `<span class="chip">${c}</span>`).join('');
    }

    const list = el('detlist');
    if(!s.detections.length){
      list.innerHTML = `<div class="empty">${s.model_ready ? 'no laundry in view' : 'loading detector…'}</div>`;
    } else {
      list.innerHTML = s.detections.map(d => {
        const pct = Math.round(d.confidence*100);
        const [x,y] = d.floor;
        return `<div class="det">
          <div class="row"><span class="lab">${d.label}</span><span class="co">${d.confidence.toFixed(2)}</span></div>
          <div class="meta">floor (${x.toFixed(2)}, ${y.toFixed(2)}) m</div>
          <div class="bar"><span style="width:${pct}%"></span></div>
        </div>`;
      }).join('');
    }
  }catch(e){ el('livedot').classList.remove('live'); }
}
setInterval(poll, 500);
poll();
</script>
</body>
</html>
"""
