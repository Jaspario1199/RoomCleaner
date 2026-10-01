# Bench release audit — 2026-10-01

Winch revised from standalone v2 and now stored in repository as cad/winch_bench.py.
- 2,373 sampled checks: all component pairs, collar stroke 0–2 mm in 0.25 mm increments, and forward cover extraction at every 1 mm from 1–75 mm.
- Three explicit exemptions: nominal M3 threaded screw cylinders in two printed pilot holes, and lever/roller envelopes representing one purchased switch. No other positive-volume overlaps allowed.
- Full spool/cup cylindrical swept envelopes clear the housing and encoder references.
- All printable parts checked as valid single solids; purchased references checked for validity. STEP reimport volume agreement <0.001 mm³.
- Added fit coupon, compact manual cartridge fixture, plastic eyelet fit surrogate and 12 centered/oriented STL files.

Clamp: 4,037 sampled complete-assembly collision/lid-removal checks passed after adding optional sensor shelf and envelope, including 0.5° tooth-phase samples over one full pinion-tooth period. CAD exports valid with STEP volume agreement <0.0001 mm³.

Offline spaced-attachment diagnostic is illustrative and not connected to the live motion planner. Superseded by encoder/tilt revision: feedback watchdogs and settled pickup tilt gate are now implemented; physical validation remains outstanding. See docs/ENCODER_AND_TILT_COMMISSIONING.md. Bench package does not authorize autonomous suspended operation.

Physical gates remain: exact switch lever/trip geometry; springs and shoulder-screw supplier stack; polished threaded eyelet; actual breakout geometry/magnet alignment; print fit/strength; wires/connectors; servo horn stack; real mass/CG; angle-dependent stopper contact; cable wear; rotational stability; effective drum radius and attachment-aware control integration.
