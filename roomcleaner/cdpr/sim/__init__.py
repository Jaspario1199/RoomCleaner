"""Simulation of the whole machine for testing the control logic end to end.

Nothing here is used on hardware. The simulated stations run the *same*
``StationCore`` the firmware mirrors, behind a simulated network with
latency, jitter, loss and outages, with independent drifting clocks.
"""
