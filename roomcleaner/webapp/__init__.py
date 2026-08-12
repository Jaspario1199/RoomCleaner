"""RoomCleaner live web app (browser dashboard).

A small Flask server that runs the camera + open-vocabulary detector in
background threads and serves:
  * an annotated MJPEG video stream (detection boxes drawn on the live feed),
  * a JSON state endpoint (detections, floor coords, fps),
  * a dashboard page that ties them together.

Entry point: ``python -m scripts.live_app --camera 1`` -> http://localhost:8000
"""
from .server import DetectorApp, create_app

__all__ = ["DetectorApp", "create_app"]
