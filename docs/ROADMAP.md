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
- [ ] The vertical "reach down and touch the floor" motion — a pure cable robot
      is weak straight down; consider a short spring-loaded or servo Z-stage on
      the claw for the final few centimeters.
- [ ] Grab confirmation: did we actually pick it up? (Suction pressure sensor,
      onboard camera, or a load check.)
- [ ] Release over the hamper and confirm the drop.
- [ ] Close the loop with Phase 1–3 and let it run a full room.

---

## Guardrails (apply from Phase 3 onward)

- **Safety is not optional.** Motors that can move a payload across your ceiling
  can injure a person or pet and damage the room. Hardware e-stop, force limits,
  and geofencing come *before* the first powered move.
- **Never run it unattended** until it has earned that trust over many
  supervised runs.
- Keep humans, pets, and fragile things out of the workspace during operation.
