"""
Dry-run the hardware bridge with NO Arduino connected.

    python -m scripts.hardware_dryrun

Runs the full scan->grab->deliver plan through the hardware executor with a
MockDriver, and prints the exact serial commands the firmware would receive
(H / M a b c d / G deg). This is how you sanity-check the motor + gripper stream
before wiring anything up. Swap MockDriver -> SerialDriver(port=...) to drive the
real robot.
"""

from __future__ import annotations

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot
from roomcleaner.perception.detector import SimulatedDetector
from roomcleaner.control.state_machine import Controller
from roomcleaner.hardware.driver import MockDriver
from roomcleaner.hardware.executor import run_on_hardware


def main():
    cfg = DEFAULT_CONFIG
    robot = CableRobot(cfg)
    detector = SimulatedDetector(cfg, n_items=3, seed=7)
    controller = Controller(robot, detector, hamper_xy=(cfg.room_width - 0.5, 0.5))

    driver = MockDriver(robot)   # <-- SerialDriver(robot, port="/dev/ttyUSB0").open() for real HW
    n = run_on_hardware(robot, controller, driver)

    print(f"plan produced {n} actions -> {len(driver.commands)} serial commands\n")
    print("--- serial stream to the Arduino ---")
    for c in driver.commands:
        kind = {"H": "home", "M": "move winches", "G": "gripper"}.get(c[0], "")
        print(f"  {c:28s}  {kind}")

    moves = [c for c in driver.commands if c.startswith("M ")]
    grips = [c for c in driver.commands if c.startswith("G ")]
    print(f"\n{len(moves)} winch moves, {len(grips)} gripper commands, "
          f"picked up {controller.picked_up} item(s).")


if __name__ == "__main__":
    main()
