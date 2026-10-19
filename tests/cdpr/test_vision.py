import numpy as np
import pytest

from roomcleaner.cdpr import frames as F
from roomcleaner.cdpr.config import load_config
from roomcleaner.cdpr.vision.camera import CameraModel
from roomcleaner.cdpr.vision.marker import MarkerDetector, claw_pose_in_marker, render_marker_view

CAM = CameraModel.load("config/camera.sim.json")
EDGE = 0.1524


def camera_above_marker(height, dx=0.0, dy=0.0, roll=0.0, pitch=0.0, yaw=0.0):
    """T_C_M for a camera looking down at a floor marker from `height`."""
    # camera pose in marker frame: optical axis pointing -Z_marker
    R_M_C = F.rpy_to_matrix(roll, pitch, yaw) @ F.rot_x(np.pi)
    T_M_C = F.make_T(R_M_C, [dx, dy, height])
    return F.inv_T(T_M_C)


@pytest.mark.parametrize("seed", range(12))
def test_detects_and_recovers_pose(seed):
    rng = np.random.default_rng(seed)
    h = rng.uniform(0.25, 1.4)
    T = camera_above_marker(h, *rng.uniform(-0.15, 0.15, 2) * h, *rng.uniform(-0.15, 0.15, 2), rng.uniform(-3, 3))
    img = render_marker_view(CAM, "apriltag_36h11", 0, EDGE, T, rng=rng, noise=2.0)
    det = MarkerDetector("apriltag_36h11", 0, EDGE, CAM)
    obs = det.detect(img)
    if not obs.ok:
        # small, near-frontal markers are genuinely ambiguous: a clean refusal is correct
        assert "ambiguous" in obs.reason and obs.side_px < 100, (obs.reason, obs.side_px)
        return
    pos_err = np.linalg.norm(obs.T_C_M[:3, 3] - T[:3, 3])
    rot_err = np.linalg.norm(F.matrix_to_rotvec(obs.T_C_M[:3, :3].T @ T[:3, :3]))
    assert pos_err < 0.004 + 0.01 * h, (h, pos_err)
    assert rot_err < np.radians(3), np.degrees(rot_err)


def test_rejects_small_and_border_markers():
    det = MarkerDetector("apriltag_36h11", 0, EDGE, CAM)
    far = render_marker_view(CAM, "apriltag_36h11", 0, EDGE, camera_above_marker(4.0))
    o = det.detect(far)
    assert not o.ok and ("small" in o.reason or "not found" in o.reason)
    edge = render_marker_view(CAM, "apriltag_36h11", 0, EDGE, camera_above_marker(0.4, dx=0.24))
    o = det.detect(edge)
    assert not o.ok


def test_wrong_id_is_not_found():
    det = MarkerDetector("apriltag_36h11", 7, EDGE, CAM)
    img = render_marker_view(CAM, "apriltag_36h11", 0, EDGE, camera_above_marker(0.5))
    assert det.detect(img).reason == "marker not found"


def test_claw_pose_chain():
    cfg = load_config("config/robot.sim.json")
    T_B_C = cfg.claw.T_body_cam
    # claw hanging upright 0.6 m above the marker centre, yawed 0.4 rad
    T_M_B = F.make_T(F.rot_z(0.4), [0.1, -0.05, 0.6])
    T_M_C = T_M_B @ T_B_C
    T_C_M = F.inv_T(T_M_C)
    assert np.allclose(claw_pose_in_marker(T_C_M, T_B_C), T_M_B)
    img = render_marker_view(CAM, "apriltag_36h11", 0, EDGE, T_C_M)
    obs = MarkerDetector("apriltag_36h11", 0, EDGE, CAM).detect(img)
    assert obs.ok
    est = claw_pose_in_marker(obs.T_C_M, T_B_C)
    assert np.linalg.norm(est[:3, 3] - T_M_B[:3, 3]) < 0.01
    assert F.tilt_angle(est[:3, :3]) < np.radians(2)


def test_gravity_prior_resolves_far_frontal_ambiguity():
    """With a measured tilt (IMU) the up-vector prior is tight enough to pick
    the right mirror solution where the loose upright prior refused."""
    rng = np.random.default_rng(9)
    h = rng.uniform(0.25, 1.4)
    roll, pitch = rng.uniform(-0.15, 0.15, 2)
    T = camera_above_marker(h, *rng.uniform(-0.15, 0.15, 2) * h, roll, pitch, rng.uniform(-3, 3))
    img = render_marker_view(CAM, "apriltag_36h11", 0, EDGE, T, rng=rng, noise=2.0)
    det = MarkerDetector("apriltag_36h11", 0, EDGE, CAM)
    up_true = T[:3, 2]                         # marker normal (= world up) in camera frame
    obs = det.detect(img, up_in_cam=up_true, up_sigma_rad=np.radians(1.0))
    assert obs.ok, obs.reason
    # it must pick the mirror candidate closer to the truth (a 64 px tag is
    # itself only good to a few degrees)
    errs = [np.linalg.norm(F.matrix_to_rotvec(Tc[:3, :3].T @ T[:3, :3])) for _, Tc in obs.candidates]
    chosen = np.linalg.norm(F.matrix_to_rotvec(obs.T_C_M[:3, :3].T @ T[:3, :3]))
    assert np.isclose(chosen, min(errs))


def test_ambiguity_statistics_over_heights():
    """Report-style check: near the start height almost every frame resolves."""
    det = MarkerDetector("apriltag_36h11", 0, EDGE, CAM)
    rng = np.random.default_rng(42)
    ok = 0
    for k in range(20):
        T = camera_above_marker(rng.uniform(0.25, 0.6), *rng.uniform(-0.05, 0.05, 2), *rng.uniform(-0.1, 0.1, 2), 0)
        ok += det.detect(render_marker_view(CAM, "apriltag_36h11", 0, EDGE, T, rng=rng)).ok
    assert ok >= 18
