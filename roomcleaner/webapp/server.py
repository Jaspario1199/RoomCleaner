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
        source: str = "camera",
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.conf = conf
        self.classes = list(classes or DEFAULT_LAUNDRY_CLASSES)
        self.backend = backend
        self.model_name = model_name
        self.source = source  # "camera" or "demo" (simulated laundry, no camera)

        self.cfg = DEFAULT_CONFIG
        self._frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._dets: list[dict] = []
        self._dets_lock = threading.Lock()
        self._render_lock = threading.Lock()  # matplotlib (pyplot) is not thread-safe
        self._rest = None  # cached parking pose (depends only on config)
        self._gif_cache = {}  # cached run animation, keyed by detection signature
        self.stats = {
            "resolution": None,
            "cam_fps": 0.0,
            "infer_fps": 0.0,
            "model_ready": False,
            "frames": 0,
            "reopens": 0,
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
        # NOTE: deliberately DON'T force CAP_PROP_FPS / CAP_PROP_AUTO_EXPOSURE
        # here — on this camera's DirectShow driver those underexposed the feed
        # to black. Leaving the driver's own auto-exposure alone keeps the image
        # visible; the self-heal reopen (see _capture_loop) handles a stuck stream.
        if not cap.isOpened():
            raise RuntimeError(
                f"Could not open camera index {self.camera_index}. "
                f"Close any app using it and check the index."
            )
        return cap

    def start(self):
        self._running = True
        if self.source == "demo":
            self._start_demo()
            return
        self._cap = self._open_camera()
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.width
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.height
        self.stats["resolution"] = f"{w}x{h}"
        self._mapper = OverheadLinearMapper(self.cfg.room_width, self.cfg.room_depth, w, h)
        self._detector = YoloWorldDetector(
            self._mapper, classes=self.classes, model_name=self.model_name, confidence=self.conf
        )
        threading.Thread(target=self._capture_loop, name="capture", daemon=True).start()
        threading.Thread(target=self._infer_loop, name="infer", daemon=True).start()

    def _start_demo(self):
        """No-camera mode: seed simulated laundry so the whole console (detections,
        plan, 3-D view) works offline for a demo or a hardware-free walkthrough."""
        from roomcleaner.perception.detector import SimulatedDetector

        sim = SimulatedDetector(self.cfg, n_items=4)
        with self._dets_lock:
            self._dets = [
                {
                    "label": d.label,
                    "confidence": float(d.confidence),
                    "floor": [float(d.position[0]), float(d.position[1])],
                    "bbox": None,
                    "area": float(d.area),
                }
                for d in sim.detect()
            ]
        self.stats["resolution"] = "demo (no camera)"
        self.stats["model_ready"] = True

    def stop(self):
        self._running = False
        time.sleep(0.2)
        if self._cap is not None:
            self._cap.release()

    # -- worker loops --------------------------------------------------------
    def _reopen_camera(self):
        """Release and reopen the camera — clears a stalled/stuck UVC stream."""
        try:
            if self._cap is not None:
                self._cap.release()
        except Exception:
            pass
        time.sleep(0.3)
        for attempt in range(15):
            if not self._running:
                return
            try:
                self._cap = self._open_camera()
                for _ in range(5):  # warm up
                    self._cap.read()
                print("[capture] camera reopened", flush=True)
                return
            except Exception as exc:
                print(f"[capture] reopen attempt {attempt + 1} failed: {exc}", flush=True)
                time.sleep(1.0)

    def _capture_loop(self):
        for _ in range(5):  # warm up the sensor
            self._cap.read()
        t0, n = time.time(), 0
        fail_since = None      # when consecutive read failures began
        frozen_since = None    # when frames stopped changing (stuck/black stream)
        last_frame = None
        last_reopen = 0.0
        while self._running:
            ok, frame = self._cap.read()
            now = time.time()
            if not ok or frame is None:
                fail_since = fail_since or now
                frozen_since = None
            else:
                fail_since = None
                # A live sensor never returns two byte-identical frames (noise);
                # an identical repeat means the stream froze (incl. stuck-black).
                if last_frame is not None and np.array_equal(frame, last_frame):
                    frozen_since = frozen_since or now
                else:
                    frozen_since = None
                last_frame = frame
                with self._frame_lock:
                    self._frame = frame
                n += 1
                if n >= 30:
                    dt = now - t0
                    self.stats["cam_fps"] = round(n / dt, 1) if dt > 0 else 0.0
                    t0, n = now, 0

            # Self-heal: reopen if reads fail (>2s) or the frame is frozen (>3s).
            stalled = ((fail_since and now - fail_since > 2.0)
                       or (frozen_since and now - frozen_since > 3.0))
            if stalled and now - last_reopen > 4.0:
                print("[capture] stream stalled — reopening camera", flush=True)
                self._reopen_camera()
                self.stats["reopens"] += 1
                self.stats["cam_fps"] = 0.0
                last_reopen = time.time()
                fail_since = frozen_since = None
                last_frame = None
                t0, n = time.time(), 0
            elif not ok:
                time.sleep(0.03)

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
            "reopens": self.stats["reopens"],
            "source": self.source,
            "conf": self.conf,
            "classes": self.classes,
            "room": {"width": self.cfg.room_width, "depth": self.cfg.room_depth},
            "detections": dets,
        }

    # -- planning + 3D view -------------------------------------------------
    def _detections_as_objects(self):
        from roomcleaner.perception.detector import Detection

        with self._dets_lock:
            raw = list(self._dets)
        return [
            Detection(
                position=np.array([d["floor"][0], d["floor"][1], 0.0]),
                label=d["label"], confidence=d["confidence"], area=d["area"],
                bbox=tuple(d["bbox"]) if d["bbox"] else None,
            )
            for d in raw
        ]

    def rest_pose(self, robot, hamper_xy):
        if self._rest is None:
            self._rest = robot.find_rest_position(prefer_xy=hamper_xy)
        return self._rest

    def plan(self) -> dict:
        """Plan the pickup order + per-target winch (cable-length) commands for
        the current detections, using the SAME Controller that drives the robot."""
        from roomcleaner.kinematics import CableRobot
        from roomcleaner.control.state_machine import Controller
        from roomcleaner.perception.live import LiveDetector

        items = self._detections_as_objects()
        robot = CableRobot(self.cfg)
        holder = LiveDetector(None)
        holder._items = list(items)
        hamper_xy = (self.cfg.room_width - 0.5, 0.5)
        ctrl = Controller(robot, holder, hamper_xy=hamper_xy)

        anchors = ["A", "B", "C", "D"]
        steps = []
        for _ in range(50):
            actions = ctrl._plan_cycle()
            if actions is None:
                break
            grab_pt = next((p for k, p in actions if k == "grip"), None)
            lengths = robot.cable_lengths(grab_pt)
            tensions, feasible = robot.solve_tensions(grab_pt)
            steps.append({
                "order": len(steps) + 1,
                "label": ctrl.target.label,
                "confidence": round(float(ctrl.target.confidence), 2),
                "floor": [round(float(ctrl.target.position[0]), 2),
                          round(float(ctrl.target.position[1]), 2)],
                "grab_z": round(float(grab_pt[2]), 3),
                "cables": {a: round(float(L), 3) for a, L in zip(anchors, lengths)},
                "max_tension_N": round(float(np.max(tensions)), 1),
                "feasible": bool(feasible),
            })
        return {
            "planned": len(steps),
            "total_detected": len(items),
            "unreachable": max(0, len(items) - len(steps)),
            "trips": len(steps) + (1 if steps else 0),
            "hamper": [round(hamper_xy[0], 2), round(hamper_xy[1], 2)],
            "rest": [round(float(x), 2) for x in ctrl.rest],
            "cruise_z": round(float(ctrl.cruise_z), 2),
            "steps": steps,
        }

    def render_room_png(self) -> bytes:
        import io
        import matplotlib
        matplotlib.use("Agg", force=True)  # headless render in a worker thread
        import matplotlib.pyplot as plt
        from roomcleaner.kinematics import CableRobot
        from roomcleaner.perception.live import LiveDetector
        from roomcleaner import simulator

        items = self._detections_as_objects()
        robot = CableRobot(self.cfg)
        holder = LiveDetector(None)
        holder._items = items
        hamper_xy = (self.cfg.room_width - 0.5, 0.5)
        rest = self.rest_pose(robot, hamper_xy)
        with self._render_lock:  # pyplot global state -> one render at a time
            fig = plt.figure(figsize=(7, 5))
            ax = fig.add_subplot(111, projection="3d")
            simulator.render_frame(
                robot, effector=rest, detector=holder, hamper_xy=hamper_xy,
                rest_xyz=rest, ax=ax, title="Room — detections + plan",
            )
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
        return buf.getvalue()

    def render_run_gif(self):
        """Render an animated GIF of the claw flying the whole planned route.

        Reuses the simulator's animate_run (same code that makes run.gif). Cached
        by a signature of the current detections so repeat requests are instant.
        Returns None when there is nothing reachable to animate.
        """
        import hashlib
        import os
        import tempfile
        import matplotlib
        matplotlib.use("Agg", force=True)
        from roomcleaner.kinematics import CableRobot
        from roomcleaner.control.state_machine import Controller
        from roomcleaner.perception.live import LiveDetector
        from roomcleaner import simulator

        items = self._detections_as_objects()
        if not items:
            return None
        sig = hashlib.md5(
            repr([(round(float(d.position[0]), 3), round(float(d.position[1]), 3), d.label)
                  for d in items]).encode()
        ).hexdigest()
        if self._gif_cache.get("sig") == sig and self._gif_cache.get("bytes"):
            return self._gif_cache["bytes"]

        robot = CableRobot(self.cfg)
        holder = LiveDetector(None)
        holder._items = list(items)
        hamper_xy = (self.cfg.room_width - 0.5, 0.5)
        rest = self.rest_pose(robot, hamper_xy)
        ctrl = Controller(robot, holder, hamper_xy=hamper_xy)
        paths = ctrl.run()  # empties holder as it "picks up" each item
        if not paths:
            return None
        holder._items = list(items)  # restore so laundry shows during the flight

        with self._render_lock:  # pyplot + PillowWriter -> one render at a time
            fd, tmp = tempfile.mkstemp(suffix=".gif")
            os.close(fd)
            try:
                simulator.animate_run(
                    robot, paths, holder, hamper_xy, out_path=tmp,
                    rest_xyz=rest, max_frames=45, fps=12,
                )
                with open(tmp, "rb") as fh:
                    data = fh.read()
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        self._gif_cache = {"sig": sig, "bytes": data}
        return data


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

    @app.route("/api/plan")
    def api_plan():
        return jsonify(state.plan())

    @app.route("/api/room.png")
    def api_room_png():
        return Response(state.render_room_png(), mimetype="image/png")

    @app.route("/api/room.gif")
    def api_room_gif():
        data = state.render_run_gif()
        if data is None:
            return Response(status=204)
        return Response(data, mimetype="image/gif")

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
  .console{padding:0 16px 24px}
  .planwrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,460px);gap:16px;padding:12px 14px}
  @media(max-width:900px){.planwrap{grid-template-columns:1fr}}
  #plansummary{font-size:13px;color:var(--text);margin-bottom:10px;line-height:1.6}
  #plansummary b{color:var(--accent)}
  .step{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:9px 11px;margin-bottom:7px}
  .step .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
  .step .ord{color:var(--muted);font:11px ui-monospace,monospace}
  .step .lab{font-weight:600;text-transform:capitalize}
  .step .rz{color:var(--muted);font:11px ui-monospace,monospace}
  .step .cables{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px}
  .cbl{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:4px 6px;text-align:center}
  .cbl .k{color:var(--muted);font:10px ui-monospace,monospace}
  .cbl .v{font:12px ui-monospace,monospace;color:var(--text)}
  .step .foot{margin-top:7px;font:11px ui-monospace,monospace;color:var(--muted);
    display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
  .ok{color:var(--accent)} .bad{color:#f85149}
  .planview img{width:100%;border:1px solid var(--border);border-radius:8px;background:#fff}
  .viewcap{color:var(--muted);font-size:11px;margin-top:6px;text-align:center}
  .viewbox{position:relative}
  .rendering{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    background:rgba(13,17,23,.72);color:var(--text);font-size:13px;border-radius:8px}
  .viewbtns{display:flex;gap:8px;margin-top:8px}
  .vb{flex:1;background:var(--panel2);color:var(--text);border:1px solid var(--border);
    border-radius:7px;padding:7px 10px;font-size:12.5px;cursor:pointer}
  .vb:hover{border-color:var(--accent)}
  .vb.active{border-color:var(--accent);color:var(--accent)}
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
  </section>
</main>

<section class="console">
  <div class="card">
    <h2>Robot &amp; plan — live pickup plan + winch commands</h2>
    <div class="planwrap">
      <div class="planinfo">
        <div id="plansummary" class="empty">planning…</div>
        <div id="plansteps"></div>
      </div>
      <div class="planview">
        <div class="viewbox">
          <img id="roomimg" src="/api/room.png" alt="3D room view">
          <div id="rendering" class="rendering" hidden>rendering animation… (~10s)</div>
        </div>
        <div class="viewbtns">
          <button id="btnLive" class="vb active">● Live view</button>
          <button id="btnAnim" class="vb">▶ Animate plan</button>
        </div>
        <div class="viewcap">3-D room · winches ■ · claw ● · laundry ★ · hamper ✚ · fan keep-out (red)</div>
      </div>
    </div>
  </div>
</section>

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

async function planPoll(){
  try{
    const p = await (await fetch('/api/plan')).json();
    const sum = el('plansummary');
    if(!p.total_detected){
      sum.className = 'empty'; sum.textContent = 'no items detected — nothing to plan yet';
      el('plansteps').innerHTML = '';
      return;
    }
    sum.className = '';
    sum.innerHTML = `Plan: <b>${p.planned}</b> pickup(s) in <b>${p.trips}</b> trip(s)`
      + (p.unreachable ? ` · <span class="bad">${p.unreachable} unreachable</span>` : '')
      + ` · hamper (${p.hamper[0]}, ${p.hamper[1]}) m · cruise z ${p.cruise_z} m`
      + ` · rest [${p.rest.join(', ')}]`;
    el('plansteps').innerHTML = p.steps.map(s => {
      const cbl = ['A','B','C','D'].map(k =>
        `<div class="cbl"><div class="k">${k}</div><div class="v">${s.cables[k].toFixed(2)}</div></div>`).join('');
      return `<div class="step">
        <div class="top">
          <span><span class="ord">#${s.order}</span> <span class="lab">${s.label}</span>
            <span class="rz">@(${s.floor[0]}, ${s.floor[1]}) m</span></span>
          <span class="${s.feasible?'ok':'bad'}">${s.feasible?'reachable':'NOT reachable'}</span>
        </div>
        <div class="cables">${cbl}</div>
        <div class="foot"><span>cable lengths A–D (m) · grab z ${s.grab_z} m</span>
          <span>max tension ${s.max_tension_N} N</span></div>
      </div>`;
    }).join('');
  }catch(e){}
}
setInterval(planPoll, 2000);
planPoll();

let roomMode = 'live';
const roomImg = el('roomimg');
function setRoomMode(m){
  roomMode = m;
  el('btnLive').classList.toggle('active', m === 'live');
  el('btnAnim').classList.toggle('active', m === 'anim');
}
el('btnLive').addEventListener('click', () => {
  setRoomMode('live');
  el('rendering').hidden = true;
  roomImg.src = '/api/room.png?t=' + Date.now();
});
el('btnAnim').addEventListener('click', async () => {
  const r = el('rendering');
  try{
    const p = await (await fetch('/api/plan')).json();
    if(!p.planned){
      r.textContent = 'no reachable items to animate'; r.hidden = false;
      setTimeout(() => { r.hidden = true; r.textContent = 'rendering animation… (~10s)'; }, 1800);
      return;
    }
  }catch(e){}
  setRoomMode('anim');
  r.textContent = 'rendering animation… (~10s)'; r.hidden = false;
  const img = new Image();
  img.onload = () => { roomImg.src = img.src; r.hidden = true; };
  img.onerror = () => { r.hidden = true; setRoomMode('live'); };
  img.src = '/api/room.gif?t=' + Date.now();
});
setInterval(() => {
  if(roomMode === 'live'){ roomImg.src = '/api/room.png?t=' + Date.now(); }
}, 4000);
</script>
</body>
</html>
"""
