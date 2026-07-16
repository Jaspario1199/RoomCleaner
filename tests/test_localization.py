"""Tests for pixel -> floor mapping (the 2D->3D perception step)."""

import numpy as np

from roomcleaner.perception.localization import (
    OverheadLinearMapper,
    HomographyMapper,
)


def test_overhead_linear_corners_and_center():
    m = OverheadLinearMapper(room_width=4.0, room_depth=3.0, image_w=1000, image_h=600)
    assert np.allclose(m.pixel_to_floor(0, 0), [0.0, 0.0])
    assert np.allclose(m.pixel_to_floor(1000, 600), [4.0, 3.0])
    assert np.allclose(m.pixel_to_floor(500, 300), [2.0, 1.5])


def test_overhead_linear_flip():
    m = OverheadLinearMapper(4.0, 3.0, 1000, 600, flip_x=True, flip_y=True)
    assert np.allclose(m.pixel_to_floor(0, 0), [4.0, 3.0])
    assert np.allclose(m.pixel_to_floor(1000, 600), [0.0, 0.0])


def test_to_detection_point_is_on_floor():
    m = OverheadLinearMapper(4.0, 3.0, 1000, 600)
    p = m.to_detection_point(500, 300)
    assert p.shape == (3,)
    assert p[2] == 0.0


def test_homography_recovers_known_rectangle():
    # Pixel corners of a frame mapped to floor corners of a 4x3 room.
    pixels = np.array([[0, 0], [1000, 0], [1000, 600], [0, 600]], dtype=float)
    floor = np.array([[0, 0], [4, 0], [4, 3], [0, 3]], dtype=float)
    m = HomographyMapper.from_correspondences(pixels, floor)
    # Corners must map back exactly.
    for px, fl in zip(pixels, floor):
        assert np.allclose(m.pixel_to_floor(*px), fl, atol=1e-6)
    # And the center maps to the room center.
    assert np.allclose(m.pixel_to_floor(500, 300), [2.0, 1.5], atol=1e-6)


def test_homography_handles_perspective():
    # A trapezoid (perspective) view of a square floor patch.
    pixels = np.array([[100, 500], [900, 500], [700, 100], [300, 100]], dtype=float)
    floor = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], dtype=float)
    m = HomographyMapper.from_correspondences(pixels, floor)
    for px, fl in zip(pixels, floor):
        assert np.allclose(m.pixel_to_floor(*px), fl, atol=1e-6)


def test_homography_needs_four_points():
    try:
        HomographyMapper.from_correspondences(
            np.array([[0, 0], [1, 0], [1, 1]]), np.array([[0, 0], [1, 0], [1, 1]])
        )
        assert False, "should have raised"
    except ValueError:
        pass
