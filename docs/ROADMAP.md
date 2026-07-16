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

## Phase 1 — Perception (mostly free; needs a webcam eventually)

Give the robot eyes. All of this can be prototyped on your laptop with a webcam
or even a folder of phone photos — no robot required.

- [ ] Collect/annotate a small dataset of *your* laundry on *your* floor
      (a few hundred phone photos goes a long way).
- [ ] Fine-tune or prompt an object detector (start with a pretrained
      YOLO-class model; "clothing"/"sock"/"towel" classes).
- [ ] Implement a real `Detector` subclass with the same interface as
      `SimulatedDetector` — drop-in, nothing downstream changes.
- [ ] **2D → 3D:** map a pixel detection to a floor coordinate.
      - Easiest: one fixed, calibrated ceiling camera → a homography maps floor
        pixels directly to (x, y) world coordinates.
      - Or: a camera on the moving claw, combined with the known claw position.
- [ ] Confidence thresholding + "is this actually laundry or is it the cat?"
      sanity checks.

**Decision to make:** fixed overhead camera(s) vs. a camera riding on the claw.
Fixed is simpler to calibrate and scan; onboard gives close-up confirmation
before a grab. A hybrid (wide fixed camera to find, onboard camera to confirm)
is likely best.

---

## Phase 2 — Planning & safety in sim (free)

Harden the brain before it can move real motors.

- [ ] Velocity/acceleration limits and cable-length-rate limits per motor.
- [ ] Geofencing: never command a point outside the verified safe workspace.
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
