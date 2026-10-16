# Startup calibration research package

Read the [full startup specification](../../docs/STARTUP_CALIBRATION_V1_20261016.md) first.

- `observability_study.py`: offline, deterministic synthetic sensitivity experiment; no hardware/network interfaces.
- `synthetic_results.json`: generated results from NumPy 2.3.5 / SciPy 1.17.0.
- `parameters.example.json`: measurement inventory, not a runnable station configuration.

Run with `python research/startup_calibration_20261016/observability_study.py` from the repository root. Requires NumPy and SciPy. It rewrites only `synthetic_results.json` next to itself.

The fitting experiment uses independently noisy observed positions and relative cable changes to estimate each of four ideal outlets and its initial cable length. Small local sample regions allow substantial anchor/length-offset ambiguity even with small residuals. Rough bounds prevent unlimited estimates but do not substitute for measured priors. The study intentionally does not apply a prior penalty, so it illustrates why blindly replacing a rough geometry estimate with a local fit can make the geometry worse.

Witness residuals concern cable-change prediction within a central 1.2 × 1.2 × 0.6 m box, not full-room position accuracy. No feasibility, field-of-view, load capability or startup success is inferred. See the JSON for assumptions and omitted effects.
