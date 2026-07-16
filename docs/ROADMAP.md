# RoomCleaner — Build Roadmap

The guiding principle: **de-risk everything cheap in software before spending a
dollar on hardware.** Each phase produces something you can run and check.

---

## Phase 0 — Simulation foundation ✅ (done)

Prove the concept with no hardware.

- [x] Project scaffold, config, tests, CI-ready layout
- [x] Cable-robot kinematics: inverse, forward, statics/workspace
- [x] Smooth motion planning (`safe_transit`: up → across → down)
- [x] Scan→select→grab→deliver state machine
- [x] 3D simulator that renders runs to PNG/GIF
- [x] `python -m scripts.demo_sim` clears a floor of fake laundry end-to-end

**You can play with this now.** Edit `roomcleaner/config.py` to your real room
dimensions and re-run the demo to see the workspace change.

---

## Phase 1 — Perception 🚧 (scaffolded; runs on a webcam today)

Give the robot eyes. All of this can be prototyped on your laptop with a webcam
or even a folder of phone photos — no robot required. See **[VISION.md](VISION.md)**.

- [x] Real `Detector` subclass with the same interface as `SimulatedDetector` —
      drop-in, nothing downstream changes (`perception/vision_detector.py`).
- [x] **Open-vocabulary** detection (YOLO-World): detects laundry from *words*
      (`"sock"`, `"towel"`, …) with **no training** required.
- [x] **2D → 3D localization** (`perception/localization.py`): pixel → floor
      `(x, y)`, both a zero-calibration overhead mapper and a precise 4-point
      homography.
- [x] Webcam capture wrapper + a live demo (`scripts/detect_webcam.py`).
- [ ] Validate accuracy on YOUR camera: place items at known spots, confirm the
      reported `(x, y)` matches a tape measure. Undistort a wide-angle lens if the
      edges drift (OpenCV `calibrateCamera`).
- [ ] Optionally fine-tune on a few hundred phone photos of *your* laundry/floor
      for higher precision than the zero-shot model.
- [ ] Confidence thresholding + "is this laundry or the cat?" sanity checks.

**Decision made:** start with a **fixed overhead camera** (simplest to calibrate
and scan). A camera on the claw for close-up grab confirmation is a good later
addition; a hybrid (wide fixed to *find*, claw cam to *confirm*) is the long-term
best.

---

## Phase 2 — Planning & safety in sim (free)

Harden the brain before it can move real motors.

- [x] **Fan keep-out:** every cable segment is tested against the fan cylinder;
      unreachable points are rejected (`geometry.py`, `is_reachable`).
- [x] **Geofencing (endpoints):** commands outside the safe workspace (walls,
      floor clearance, tension limits, fan) are rejected.
- [x] **Auto rest pose:** the effector parks out of the way, below the fan,
      between jobs (`find_rest_position`).
- [x] **Fan-aware cruise height:** transits stay in the good-tension band and
      below the fan.
- [ ] **Full-path** fan/workspace checking (currently endpoints + cruise height;
      validate every waypoint of a transit, not just its ends).
- [ ] Velocity/acceleration limits and cable-length-rate limits per motor.
- [ ] Failure/recovery states: `GRAB` can fail — add `VERIFY_GRAB` and `RETRY`.
- [ ] Multi-item route optimization (currently nearest-first; fine to start).
- [ ] Soft-start / soft-stop and an emergency-stop path modeled in sim.
- [ ] Log everything; replay logs through the simulator.

---

## Phase 3 — Hardware bring-up 💰

Now we spend money. See [HARDWARE.md](HARDWARE.md) for the parts list.

- [ ] Build **one** winch and prove closed-loop cable-length control on a bench.
- [ ] Repeat ×4; mount in the ceiling corners; measure exact anchor positions.
- [ ] Camera mount + calibration (map camera frame ↔ room frame).
- [ ] A real, tested **e-stop** that cuts motor power in hardware (not software).
- [ ] Home the system: how does it know each cable's starting length?
- [ ] Drive the claw to commanded points; measure real vs. commanded position;
      tune. Expect cable stretch and winch backlash to bite here.

**Start small:** build a tabletop version first (1 m × 1 m, tiny motors, a
foam block for the claw). Everything transfers to the full-size room build.

---

## Phase 4 — The grasp 💰🧪 (the real experiment)

The hardest, least-certain part. Budget time to iterate.

- [ ] Choose the end-effector. Strong recommendation: **start with suction**
      (a small vacuum + solenoid valve) — it grabs flat cloth far more reliably
      than a claw. Keep fingers/claw as a fallback.
      Decision made: a **tentacle gripper** (a ring of tendon-driven curling TPU
      fingers, one servo) — see `cad/` and HARDWARE.md.
- [ ] The vertical "reach down and touch the floor" motion — a pure cable robot
      is weak straight down; consider a short spring-loaded or servo Z-stage on
      the claw for the final few centimeters.
- [ ] Grab confirmation: did we actually pick it up? (onboard camera or a load
      check on cable tension.)
- [ ] Release over the hamper and confirm the drop.
- [ ] Tune the tentacle curl on real laundry — stiff denim (jeans) is the hardest
      case; may want deeper notches or an extra finger.
- [ ] Close the loop with Phase 1–3 and let it run a full room.

---

## Phase 5 — Future directions (someday / maybe)

Ideas the mechanism opens up once the laundry version works. Not committed, just
captured so they're not lost.

### Turn it into a large-format 3D printer
Cable-driven robots are a real approach to room/building-scale additive
manufacturing (e.g. ORNL's cable-suspended large-format printer). The bones carry
over — **our inverse kinematics, winches, motion control, and homing are exactly
what a cable printer needs.** What would have to change:

- **Precision & stiffness:** printing needs ~0.1–0.2 mm; a hanging effector sags,
  stretches, and sways. Fight it with low-stretch (steel) cable, higher tension,
  slower moves.
- **More cables — 8, not 4:** four cables fix a point's *position* but can't hold
  the toolhead *level*. Full 6-DOF rigidity uses 8 cables (upgrade the point-mass
  model to a rigid body).
- **A real toolhead:** extruder + hot end (small scale) or a paste/concrete pump
  (room scale — plastic is impractical past ~1 m³).
- **Cables vs. the growing print:** the descending cables can collide with the
  object as it builds up — a genuine open problem.

Realistic path: after the laundry robot, swap the gripper for a light toolhead and
try a **~1 m³ paste/clay printer** (or even a pen-plotter) to prove precision
before a hot end. Nail the forgiving laundry version first.

### Other ideas
- Fetch-and-carry for other light objects (toys, TV remote).
- Overhead camera doubling as a room monitor / time-lapse.
- Multiple hampers / sorting (lights vs. darks) using the detector's labels.

---

## Guardrails (apply from Phase 3 onward)

- **A hardware power cut is not optional.** Even a light rig has motors that can
  run away or swing the effector. This build uses a **switched power strip on the
  12 V motor supply** as the kill switch (slap it / flip it → motors dead),
  backed by an inline fuse. Software limits and geofencing (walls + fan) come
  *before* the first powered move — but they can't replace the physical cut.
- **Never run it unattended** until it has earned that trust over many
  supervised runs.
- Keep humans, pets, and fragile things out of the workspace during operation.
