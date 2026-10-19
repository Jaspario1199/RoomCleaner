import cv2
import numpy as np

from roomcleaner.cdpr import frames as F
from roomcleaner.cdpr.vision.camera import CameraModel
from tools.calibrate_camera import board, calibrate_images
from tools.print_marker import make_marker_sheet


def test_marker_sheet_has_exact_physical_edge():
    sheet = make_marker_sheet(152.4, 0, dpi=300)
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    corners, ids, _ = cv2.aruco.ArucoDetector(d).detectMarkers(sheet)
    assert ids is not None and ids.ravel()[0] == 0
    c = corners[0].reshape(4, 2)
    edge_px = np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)])
    assert abs(edge_px / 300 * 25.4 - 152.4) < 0.5


def test_charuco_calibration_recovers_synthetic_intrinsics():
    true = CameraModel(np.array([[610.0, 0, 405.0], [0, 605.0, 295.0], [0, 0, 1]]),
                       np.zeros(5), (800, 600), "truth")  # a homography warp cannot render lens distortion
    b = board(0.03)
    img_board = b.generateImage((800, 600), marginSize=0)
    W, H = 8 * 0.03, 6 * 0.03
    rng = np.random.default_rng(0)
    shots = []
    for k in range(18):
        R = F.rpy_to_matrix(*rng.uniform(-0.45, 0.45, 2), rng.uniform(-0.4, 0.4))
        t = [rng.uniform(-0.05, 0.05), rng.uniform(-0.04, 0.04), rng.uniform(0.32, 0.5)]
        corners_b = np.array([[0, 0, 0], [W, 0, 0], [W, H, 0], [0, H, 0]]) - [W / 2, H / 2, 0]
        pts_c = corners_b @ R.T + t
        dst = true.project(pts_c).astype(np.float32)
        src = np.array([[0, 0], [800, 0], [800, 600], [0, 600]], np.float32)
        # generateImage pixel (u, v) <-> board (x, y) = (u, v) * square / px_per_square, same handedness
        Hm = cv2.getPerspectiveTransform(src, dst)
        shots.append(cv2.warpPerspective(img_board, Hm, (800, 600), borderValue=255))
    res = calibrate_images(shots, 0.03, max_rms=2.5)
    K = np.array(res["K"])
    assert abs(K[0, 0] - 610) < 25 and abs(K[1, 1] - 605) < 25
    assert res["views"] >= 12
