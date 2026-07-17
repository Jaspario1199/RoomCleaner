"""
Tests for the host-side hardware bridge, using MockDriver so no Arduino/pyserial
is needed. Verifies the length->steps math and that a full plan streams to the
driver as sensible commands.
"""

import numpy as np

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot
from roomcleaner.perception.detector import SimulatedDetector
from roomcleaner.control.state_machine import Controller
from roomcleaner.hardware.driver import MockDriver
from roomcleaner.hardware.executor import run_on_hardware, subsample_path
from roomcleaner.hardware.hw_config import STEPS_PER_M


def test_steps_at_home_are_zero():
    robot = CableRobot(DEFAULT_CONFIG)
    home = robot.find_rest_position()
    drv = MockDriver(robot, home_lengths=robot.cable_lengths(home))
    steps = drv.steps_for_point(home)
    assert steps == [0, 0, 0, 0]


def test_steps_scale_with_cable_length():
    robot = CableRobot(DEFAULT_CONFIG)
    home = np.array([2.0, 1.5, 1.0])
    drv = MockDriver(robot, home_lengths=robot.cable_lengths(home))
    # Move 0.5 m lower -> cables lengthen; steps should be positive and match
    # the length delta * STEPS_PER_M.
    target = np.array([2.0, 1.5, 0.5])
    steps = np.array(drv.steps_for_point(target))
    dl = robot.cable_lengths(target) - robot.cable_lengths(home)
    assert np.allclose(steps, np.round(dl * STEPS_PER_M), atol=1)
    assert np.all(steps > 0)          # lower effector => longer cables


def test_subsample_keeps_endpoints_and_thins():
    path = np.linspace([0, 0, 1], [1, 0, 1], 200)   # 1 m straight line
    keep = subsample_path(path, step_m=0.15)
    assert np.allclose(keep[0], path[0])
    assert np.allclose(keep[-1], path[-1])
    assert 5 <= len(keep) <= 12       # ~1m / 0.15m ~ 7 points


def test_full_plan_streams_expected_commands():
    cfg = DEFAULT_CONFIG
    robot = CableRobot(cfg)
    det = SimulatedDetector(cfg, n_items=2, seed=1)
    ctrl = Controller(robot, det, hamper_xy=(cfg.room_width - 0.5, 0.5))
    drv = MockDriver(robot)
    n = run_on_hardware(robot, ctrl, drv)

    assert n > 0
    assert drv.commands, "driver received no commands"
    # Homing happened first, then moves, and both grip and release were issued.
    assert any(c.startswith("M ") for c in drv.commands)
    assert any(c == "G 120" for c in drv.commands)   # grip
    assert any(c == "G 20" for c in drv.commands)     # release
    # Every M command carries exactly 4 step targets.
    for c in drv.commands:
        if c.startswith("M "):
            assert len(c.split()) == 5
