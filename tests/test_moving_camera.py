"""Synthetic calibrated geometry checks; no physical-camera calibration claim."""

import numpy as np
import pytest

from roomcleaner.perception.moving_camera import pixel_to_world_plane


K = np.array([[700., 12., 320.], [0., 810., 240.], [0., 0., 1.]])


def pose(rotation=None, translation=(1., 2., 3.)):
    result = np.eye(4)
    result[:3, :3] = np.diag([1., -1., -1.]) if rotation is None else rotation
    result[:3, 3] = translation
    return result


def project(point, camera_pose):
    # Independent forward camera projection of a known world point.
    camera_point = camera_pose[:3, :3].T @ (point - camera_pose[:3, 3])
    assert camera_point[2] > 0
    homogeneous = K @ camera_point
    return homogeneous[:2] / homogeneous[2]


def test_downward_floor_principal_point_and_noncentral_skew():
    camera_pose = pose()
    np.testing.assert_allclose(pixel_to_world_plane(320, 240, K, camera_pose, [0, 0, 1], 0), [1, 2, 0])
    point = np.array([1.4, 1.6, 0.])
    pixel = project(point, camera_pose)
    np.testing.assert_allclose(pixel_to_world_plane(*pixel, K, camera_pose, [0, 0, 1], 0), point, atol=1e-12)


@pytest.mark.parametrize("yaw,tilt,translation", [
    (0.3, 0.4, (2., -1., 4.)), (-1.2, -0.6, (-3., 5., 4.)),
    (2.8, 0.9, (0.3, 0.7, 6.)),
])
@pytest.mark.parametrize("normal,offset", [([0., 0., 1.], 0.), ([0.1, -0.2, 1.], -0.5)])
def test_rotated_translated_camera_recovers_known_plane_points(yaw, tilt, translation, normal, offset):
    rz = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
    ry = np.array([[np.cos(tilt), 0, np.sin(tilt)], [0, 1, 0], [-np.sin(tilt), 0, np.cos(tilt)]])
    camera_pose = pose(rz @ ry @ np.diag([1., -1., -1.]), translation)
    for x, y in [(0., 0.), (0.4, -0.3), (-0.5, 0.2)]:
        point = np.array([translation[0] + x, translation[1] + y, 0.])
        point[2] = -(normal[0] * point[0] + normal[1] * point[1] + offset) / normal[2]
        pixel = project(point, camera_pose)
        np.testing.assert_allclose(pixel_to_world_plane(*pixel, K, camera_pose, normal, offset), point, atol=1e-11)


def test_same_world_point_under_two_camera_poses():
    point = np.array([1.2, 1.7, 0.])
    for camera_pose in [pose(), pose(translation=(-0.5, 0.3, 2.))]:
        np.testing.assert_allclose(pixel_to_world_plane(*project(point, camera_pose), K, camera_pose, [0, 0, 1], 0), point, atol=1e-12)


@pytest.mark.parametrize("scale", [1e-200, -3., 1e200])
def test_plane_scaling_preserves_result(scale):
    np.testing.assert_allclose(pixel_to_world_plane(320, 240, K, pose(), np.array([0, 0, 1.]) * scale, -0.7 * scale), [1, 2, 0.7], atol=1e-12)


@pytest.mark.parametrize("bad_k", [None, np.eye(2), np.zeros((3, 3)),
    [[-1, 0, 0], [0, 1, 0], [0, 0, 1]],
    [[1, 0, 0], [0, 0, 0], [0, 0, 1]],
    [[1, 0, 0], [0, 1, 0], [0, 0, 2]],
    [[1, 0, 0], [1, 1, 0], [0, 0, 1]], np.full((3, 3), np.nan), np.full((3, 3), np.inf)])
def test_invalid_intrinsics_rejected(bad_k):
    with pytest.raises(ValueError):
        pixel_to_world_plane(320, 240, bad_k, pose(), [0, 0, 1], 0)


@pytest.mark.parametrize("bad_pose", [None, np.eye(3), np.zeros((4, 4)),
    np.diag([1., 1., -1., 1.]), np.diag([2., 1., 1., 1.]), np.full((4, 4), np.nan)])
def test_invalid_pose_rejected(bad_pose):
    with pytest.raises(ValueError):
        pixel_to_world_plane(320, 240, K, bad_pose, [0, 0, 1], 0)


def test_shear_and_projective_transform_rejected():
    for row, col in [(0, 1), (3, 0)]:
        bad_pose = pose()
        bad_pose[row, col] = 0.1
        with pytest.raises(ValueError):
            pixel_to_world_plane(320, 240, K, bad_pose, [0, 0, 1], 0)


@pytest.mark.parametrize("normal,offset", [(None, 0), ([0, 0], 0), ([0, 0, 0], 0),
    ([0, 0, np.nan], 0), ([0, 0, 1], np.inf), ([0, 0, 1], None), ([0, 0, 1], [0])])
def test_invalid_plane_rejected(normal, offset):
    with pytest.raises(ValueError):
        pixel_to_world_plane(320, 240, K, pose(), normal, offset)


@pytest.mark.parametrize("u,v", [(np.nan, 240), (320, np.inf), (None, 0), ([1], 2)])
def test_invalid_pixel_rejected(u, v):
    with pytest.raises(ValueError):
        pixel_to_world_plane(u, v, K, pose(), [0, 0, 1], 0)


@pytest.mark.parametrize("normal,offset,camera_pose", [
    ([1, 0, 0], 0, pose()),  # Parallel.
    ([1, 0, 1e-14], 0, pose()),  # Near parallel.
    ([0, 0, 1], 0, pose(rotation=np.eye(3))),  # Behind camera.
    ([0, 0, 1], -3, pose()),  # At optical centre.
])
def test_nonforward_intersections_rejected(normal, offset, camera_pose):
    with pytest.raises(ValueError):
        pixel_to_world_plane(320, 240, K, camera_pose, normal, offset)


@pytest.mark.parametrize("u,v", [(-0.01, 0), (0, -0.01), (640, 0), (0, 480)])
def test_outside_image_rejected(u, v):
    with pytest.raises(ValueError, match="outside"):
        pixel_to_world_plane(u, v, K, pose(), [0, 0, 1], 0, image_size=(640, 480))


@pytest.mark.parametrize("u,v", [(0, 0), (639.99, 479.99)])
def test_valid_image_edges(u, v):
    result = pixel_to_world_plane(u, v, K, pose(), [0, 0, 1], 0, image_size=(640, 480))
    assert np.isfinite(result).all()
    assert abs(result[2]) < 1e-12


@pytest.mark.parametrize("size", [(0, 480), (640, -1), (640., 480), (True, 480), (640,), None, (640, 480, 1)])
def test_invalid_dimensions_or_explicit_no_dimensions(size):
    if size is None:
        assert np.isfinite(pixel_to_world_plane(-100, 600, K, pose(), [0, 0, 1], 0, image_size=None)).all()
    else:
        with pytest.raises(ValueError):
            pixel_to_world_plane(320, 240, K, pose(), [0, 0, 1], 0, image_size=size)


def test_pose_is_required_and_inputs_are_not_mutated():
    with pytest.raises(TypeError):
        pixel_to_world_plane(320, 240, K, plane_normal=[0, 0, 1], plane_offset=0)
    camera_pose = pose()
    normal = np.array([0., 0., 2.])
    copies = [x.copy() for x in (K, camera_pose, normal)]
    pixel_to_world_plane(320, 240, K, camera_pose, normal, 0)
    for actual, expected in zip((K, camera_pose, normal), copies):
        np.testing.assert_array_equal(actual, expected)
