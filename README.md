# RoomCleaner 🧺🤖

An autonomous robot that scans your room, spots dirty laundry on the floor,
picks it up, and drops it in the hamper — using four winch motors in the
ceiling corners and a downward-facing gripper on cables.

> **Status:** Phase 0 (simulation) — the kinematics, motion planning, and the
> full scan→grab→deliver control loop run today with **zero hardware**.

![A cleaning run in simulation](docs/images/run.gif)

---

## The idea in one picture

The machine is a **Cable-Driven Parallel Robot (CDPR)** — the same mechanism
that flies the "SkyCam" over a football stadium. Four motorized winches sit in
the ceiling corners; each pays out or reels in a cable. Where the cables meet is
the end-effector (the "claw"). Control the four cable lengths and you control the
claw's position anywhere in the room.

![The robot in its room](docs/images/scene_before.png)

**Why a cable robot instead of arms or a rolling vacuum?**
- It reaches the *whole floor* from above — no bumping into furniture.
- The heavy motors stay bolted to the ceiling; only a light claw moves.
- The math (below) is clean and the parts are cheap.

The trade-off is the reachable area shrinks near the walls (cables can't pull the
claw sideways into a corner). Here's the safe workspace at a low height — green is
reachable, pink is not:

![Reachable workspace](docs/images/workspace.png)

That pink border is a real design constraint: **laundry pushed right against a
wall is a hard case** we'll have to handle (e.g. a longer-reach end-effector, or
just accepting a small dead-zone).

---

## Quick start

```bash
pip install -r requirements.txt
python -m scripts.demo_sim      # writes images + a GIF into ./output/
python -m pytest                # run the kinematics tests
```

The demo scatters fake laundry, then runs the real control loop to clear the
floor and animates the result.

---

## How it works (the four subsystems)

### 1. Kinematics — `roomcleaner/kinematics.py`
The core math, and it's simpler than it looks:

- **Inverse kinematics** ("put the claw *here* → how long is each cable?") is just
  the straight-line distance from each ceiling anchor to the target point.
- **Forward kinematics** ("cables are *these* lengths → where's the claw?") is a
  least-squares fit, because real cable measurements are never perfectly
  consistent.
- **Statics** ("can four *pull-only* cables actually hold the claw here without
  exceeding the motor's force limit?") defines the usable workspace. Cables can
  pull but never push, so this is the constraint that carves out those pink edges.

### 2. Perception — `roomcleaner/perception/`
Finds laundry and locates it in 3D. Phase 0 ships a `SimulatedDetector` that
invents laundry so the rest of the system has something to chase. Phase 1 swaps
in a real object-detection model (YOLO-class) behind the **exact same
interface**, so nothing downstream changes.

### 3. Motion planning — `roomcleaner/control/trajectory.py`
Turns "go to point X" into a smooth, ease-in/ease-out path. The `safe_transit`
helper always travels *up → across → down* so the claw never drags across the
floor or clips furniture.

### 4. Orchestration — `roomcleaner/control/state_machine.py`
The brain: an explicit state machine
(`SCAN → SELECT → APPROACH → GRAB → DELIVER → DONE`) that clears the floor one
item at a time, nearest first. Keeping it an explicit state machine (not tangled
`if`s) makes safety easy to reason about and new states easy to add.

---

## Repository layout

```
roomcleaner/
  config.py               # room size, motor limits, safety margins — EDIT THIS for your room
  kinematics.py           # inverse/forward kinematics + workspace/statics
  simulator.py            # 3D visualiser (renders to PNG/GIF, no display needed)
  perception/
    detector.py           # Detector interface + SimulatedDetector (Phase 1 goes here)
  control/
    trajectory.py         # smooth path generation
    state_machine.py      # the scan→grab→deliver brain
  hardware/               # (Phase 3) motor drivers, camera, e-stop live here
scripts/
  demo_sim.py             # end-to-end simulation demo
tests/
  test_kinematics.py      # the math we must trust
docs/
  ROADMAP.md              # phase-by-phase build plan
  HARDWARE.md             # parts list & wiring for when you go physical
  ARCHITECTURE.md         # how the pieces fit + the design decisions
```

---

## Where this is going

See **[docs/ROADMAP.md](docs/ROADMAP.md)** for the full plan. The short version:

| Phase | What | Cost |
|------|------|------|
| **0** ✅ | Kinematics + simulator + control loop | Free (software) |
| **1** | Real laundry detection & 3D localization | Free–cheap (a webcam) |
| **2** | Motion planning polish, safety logic, sim tuning | Free |
| **3** | Hardware bring-up: motors, drivers, camera, e-stop | 💰 the build |
| **4** | The grasp — actually picking cloth off the floor | 💰 the experiment |

The two genuinely hard, risky parts are called out honestly in the docs:
**grasping deformable cloth** (Phase 4) and **safety** (a motor that can move a
payload across your ceiling can hurt someone). We de-risk everything cheap in
software first.

---

## A note on the gripper

A rigid claw grabbing flat, crumpled cloth off a hard floor is the classic
failure point of projects like this. Before committing to a claw, seriously
consider a **suction / vacuum end-effector** — it grabs flat fabric far more
reliably. The code treats the end-effector as swappable, so this decision stays
open. See [docs/HARDWARE.md](docs/HARDWARE.md).
