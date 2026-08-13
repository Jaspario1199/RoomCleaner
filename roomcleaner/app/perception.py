"""
Camera capture + inference pipeline for the unified console's live mode.

Ported (largely intact) from the retired perception console
(`roomcleaner/webapp/server.py`), which was validated on the real innomaker
camera. The design and the reasons behind it are preserved:

  * a CAPTURE thread pulls frames from the camera as fast as it can, so the
    video stays smooth;
  * an INFERENCE thread runs the (slow, ~1-2 fps on CPU) YOLO-World detector on
    the latest frame and caches the boxes;
  * the MJPEG consumer (`LiveSession.frame_jpeg`) draws the latest boxes onto
    the latest frame at display rate, so the feed never stutters while waiting
    on the model;
  * SELF-HEALING capture: reads that fail for >2 s or a frame that stops
    changing for >3 s (a stuck/black UVC stream -- observed on the real camera)
    trigger a camera release + reopen with warm-up reads.

Heavy dependencies (cv2, ultralytics via YoloWorldDetector) import lazily so
`--demo` mode -- simulated laundry pushed through the real detection-dict
format, no camera -- needs neither OpenCV nor torch.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import numpy as np

BOX_COLOR = (80, 220, 80)      # BGR green
HUD_COLOR = (0, 220, 0)


class PerceptionPipeline:
    """Owns the camera + detector threads and the shared latest-frame /
    latest-detections state that the session reads.

    `source` is "camera" (real capture + YOLO-World inference) or "demo"
    (seed simulated laundry once; no camera, no model).
    """

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
        room_width: float = 4.0,
        room_depth: float = 3.0,
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.conf = conf                    # written live by the sensitivity slider
        self.classes = list(classes) if classes else None   # None -> detector default
        self.backend = backend
        self.model_name = model_name
        self.source = source
        self.room_width = room_width
        self.room_depth = room_depth

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
            "reopens": 0,
        }
        self._running = False
        self._cap = None
        self._detector = None
        self._mapper = None

    # -- lifecycle -----------------------------------------------------------
    def _open_camera(self):
        import cv2

        be = cv2.CAP_DSHOW if (self.backend == "dshow" and hasattr(cv2, "CAP_DSHOW")) else 0
        cap = cv2.VideoCapture(self.camera_index, be)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        # NOTE: deliberately DON'T force CAP_PROP_FPS / CAP_PROP_AUTO_EXPOSURE
        # here — on the validated camera's DirectShow driver those underexposed
        # the feed to black. Leaving the driver's own auto-exposure alone keeps
        # the image visible; the self-heal reopen (see _capture_loop) handles a
        # stuck stream.
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
        import cv2  # noqa: F401 -- fail fast with a clear message if missing

        from ..perception.localization import OverheadLinearMapper
        from ..perception.vision_detector import YoloWorldDetector

        self._cap = self._open_camera()
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.width
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.height
        self.stats["resolution"] = f"{w}x{h}"
        self._mapper = OverheadLinearMapper(self.room_width, self.room_depth, w, h)
        kwargs = {"model_name": self.model_name, "confidence": self.conf}
        if self.classes:
            kwargs["classes"] = self.classes
        self._detector = YoloWorldDetector(self._mapper, **kwargs)
        if self.classes is None:
            self.classes = list(self._detector.classes)
        threading.Thread(target=self._capture_loop, name="capture", daemon=True).start()
        threading.Thread(target=self._infer_loop, name="infer", daemon=True).start()

    def _start_demo(self):
        """No-camera mode: seed simulated laundry so the whole console
        (detections, plan, 3-D view) works offline for a demo or a
        hardware-free walkthrough. Needs neither OpenCV nor torch."""
        from ..perception.detector import SimulatedDetector
        from ..perception.vision_detector import DEFAULT_LAUNDRY_CLASSES

        room = SimpleNamespace(room_width=self.room_width, room_depth=self.room_depth)
        sim = SimulatedDetector(room, n_items=4)
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
        if self.classes is None:
            self.classes = list(DEFAULT_LAUNDRY_CLASSES)
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

    # -- reads ---------------------------------------------------------------
    def detections(self) -> list[dict]:
        with self._dets_lock:
            return list(self._dets)

    def stats_snapshot(self) -> dict:
        return {
            "source": self.source,
            "camera": self.camera_index if self.source == "camera" else None,
            "resolution": self.stats["resolution"],
            "cam_fps": self.stats["cam_fps"],
            "infer_fps": self.stats["infer_fps"],
            "model_ready": self.stats["model_ready"],
            "reopens": self.stats["reopens"],
            "classes": list(self.classes or []),
        }

    def annotated_jpeg(self) -> bytes | None:
        """The latest camera frame with the latest boxes burned in (camera
        source only; demo mode has no frame -- the session renders its own)."""
        import cv2

        with self._frame_lock:
            frame = None if self._frame is None else self._frame.copy()
        if frame is None:
            frame = np.zeros((self.height, self.width, 3), np.uint8)
            cv2.putText(frame, "waiting for camera...", (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, HUD_COLOR, 2)
        dets = self.detections()
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
