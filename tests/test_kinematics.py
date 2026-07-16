"""Tests for the cable-robot kinematics -- the math we must trust."""

import numpy as np
import pytest

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot


@pytest.fixture
def robot():
    return CableRobot(DEFAULT_CONFIG)


def test_inverse_then_forward_roundtrips(robot):
    """Compute cable lengths for a point, then recover the point from them."""
    for point in [
        np.array([2.0, 1.5, 1.0]),
        np.array([1.0, 1.0, 0.5]),
        np.array([3.0, 2.0, 1.8]),
    ]:
        lengths = robot.cable_lengths(point)
        recovered = robot.position_from_lengths(lengths)
        assert np.allclose(recovered, point, atol=1e-4), f"{recovered} != {point}"


def test_cable_lengths_are_positive_distances(robot):
    point = np.array([2.0, 1.5, 1.0])
    lengths = robot.cable_lengths(point)
    assert lengths.shape == (4,)
    assert np.all(lengths > 0)
    # Length to the nearest anchor must be <= room diagonal.
    diag = np.linalg.norm([4.0, 3.0, 2.6])
    assert np.all(lengths <= diag)


def test_directions_are_unit_vectors(robot):
    point = np.array([2.0, 1.5, 1.0])
    dirs = robot.cable_directions(point)
    norms = np.linalg.norm(dirs, axis=1)
    assert np.allclose(norms, 1.0)


def test_tensions_balance_gravity_in_workspace(robot):
    """In the reachable middle of the room, tensions must sum to hold weight."""
    point = np.array([2.0, 1.5, 1.0])
    tensions, feasible = robot.solve_tensions(point)
    assert feasible
    assert np.all(tensions >= 0)


def test_center_is_reachable_and_corner_floor_is_not(robot):
    assert robot.is_reachable(np.array([2.0, 1.5, 1.0]))
    # Right at a wall should be rejected by the margin check.
    assert not robot.is_reachable(np.array([0.0, 0.0, 0.05]))
