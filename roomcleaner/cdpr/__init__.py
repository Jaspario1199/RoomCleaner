"""
RoomCleaner cable-driven parallel robot (CDPR) control system, V1.

Layering (each module depends only on the ones above it):

    frames       rigid transforms (SE3), rotation helpers
    config       system configuration, units, fail-closed authorization
    spool        layered spool payout model (cable length <-> motor steps)
    kinematics   cable geometry, Jacobians, static tension feasibility
    protocol     versioned host <-> station message definitions
    clock        host/station clock-offset estimation
    station_core reference implementation of the winch-station firmware logic
    transport    UDP transport and an in-memory simulated network
    station_link host-side view of one station (freshness, boot epochs, clock)
    trajectory   Cartesian motion planning -> per-station segment streams
    coordinator  synchronized multi-station motion execution and fault reaction
    trust        what calibration/position knowledge survives each fault
    vision       camera model, fiducial marker pose with ambiguity handling
    calibration  geometric estimator, excitation design, bead verification
    startup      floor-start sequence: slack take-up -> lift -> calibrate -> verify
    supervisor   top-level operating states and operator commands
    tasks        pickup / delivery workflow with visual verification
    sim          physics, camera and claw simulators for end-to-end testing

See docs/CONTROL_SYSTEM_V1.md for the design rationale and the startup
calibration specification in docs/STARTUP_CALIBRATION_V1_20261016.md.
All units are SI (metres, seconds, radians, newtons) unless a name says
otherwise (e.g. ``*_us`` microseconds, ``*_usteps`` microsteps, ``*_counts``).
"""
