"""Tests for the fan keep-out geometry -- the safety-critical bits."""

import numpy as np

from roomcleaner.geometry import (
    segment_intersects_cylinder,
    point_in_cylinder,
    cables_clear_of_fan,
)
from roomcleaner.config import FanZone, DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot


CENTER = (2.0, 1.5)
R = 0.5
ZLO, ZHI = 2.0, 2.6


def test_segment_straight_through_center_hits():
    # Horizontal segment at z=2.3 passing right over the fan center.
    a = np.array([0.0, 1.5, 2.3])
    b = np.array([4.0, 1.5, 2.3])
    assert segment_intersects_cylinder(a, b, CENTER, R, ZLO, ZHI)


def test_segment_below_cylinder_misses():
    # Same horizontal line but well BELOW the cylinder's height band.
    a = np.array([0.0, 1.5, 1.0])
    b = np.array([4.0, 1.5, 1.0])
    assert not segment_intersects_cylinder(a, b, CENTER, R, ZLO, ZHI)


def test_segment_beside_cylinder_misses():
    # Passes over at correct height but offset in y beyond the radius.
    a = np.array([0.0, 0.5, 2.3])   # y=0.5 is 1.0 m from center y=1.5 > R
    b = np.array([4.0, 0.5, 2.3])
    assert not segment_intersects_cylinder(a, b, CENTER, R, ZLO, ZHI)


def test_diagonal_cable_across_fan_column_hits():
    # A cable from the corner directly ABOVE the fan center down to the far
    # side passes through the fan column near the ceiling -> must be caught.
    a = np.array([2.0, 1.5, 2.6])   # straight above fan center, at ceiling
    b = np.array([3.5, 1.5, 0.1])
    assert segment_intersects_cylinder(a, b, CENTER, R, ZLO, ZHI)


def test_diagonal_cable_clearing_fan_misses():
    # A corner cable whose path stays outside the fan radius at fan height.
    a = np.array([0.0, 0.0, 2.6])
    b = np.array([3.0, 2.2, 0.1])
    assert not segment_intersects_cylinder(a, b, CENTER, R, ZLO, ZHI)


def test_vertical_segment_inside_column():
    a = np.array([2.0, 1.5, 0.0])
    b = np.array([2.0, 1.5, 2.6])
    assert segment_intersects_cylinder(a, b, CENTER, R, ZLO, ZHI)


def test_point_in_cylinder():
    assert point_in_cylinder(np.array([2.0, 1.5, 2.3]), CENTER, R, ZLO, ZHI)
    assert not point_in_cylinder(np.array([2.0, 1.5, 1.0]), CENTER, R, ZLO, ZHI)
    assert not point_in_cylinder(np.array([3.5, 1.5, 2.3]), CENTER, R, ZLO, ZHI)


def test_cables_clear_of_fan_disabled_always_true():
    fan = FanZone(cx=2, cy=1.5, radius=0.5, z_low=2.0, z_high=2.6, enabled=False)
    anchors = DEFAULT_CONFIG.anchors
    assert cables_clear_of_fan(anchors, np.array([2.0, 1.5, 2.3]), fan)


def test_effector_inside_fan_is_rejected():
    robot = CableRobot(DEFAULT_CONFIG)
    if robot.cfg.fan.enabled:
        # A point right at the fan center & height must be unreachable.
        p = np.array([robot.cfg.fan.cx, robot.cfg.fan.cy, robot.cfg.fan.z_low + 0.05])
        assert not robot.is_reachable(p)


def test_rest_position_is_reachable_and_clears_fan():
    robot = CableRobot(DEFAULT_CONFIG)
    rest = robot.find_rest_position(prefer_xy=(robot.cfg.room_width - 0.5, 0.5))
    assert robot.is_reachable(rest)
    assert cables_clear_of_fan(robot.anchors, rest, robot.cfg.fan)
