# Design intent, in Jasper's words (10/27, paraphrased from a voice note; authoritative for the deck's story)

Use this for the order and emphasis of the deck. Numbers still come from the record (REQUIREMENTS, DECISIONS, calcs).

## What the story is about

The story is the **architecture of the system around the claw**, not the gripper. The gripper is a modular attachment on
purpose; it gets one slide.

## Iteration 1: one central unit

- One central unit drove all four motors, placed in the four corners of the room, with wires run to each corner.
- An overhead camera on the ceiling scanned the room.
- It worked, but every motor and every sensor had to be wired back to that one place.

## Why it changed: what a motor on a wall needs

- A motor bolted to a wall cannot just run. Things go wrong: a camera malfunctions, a spool winds too tight, tension rips
  something out of the wall, a motor stalls. So each winch needs a **switch (button)** and an **encoder**.
- The encoder is there to **measure the discrepancies** while testing. If the camera later turns out to be good enough on
  its own, the encoder can go; but the data comes first.
- Once every corner has a motor, a switch and an encoder, driving all of them from one box over a long run of
  **small-diameter wire** does not make sense: many conductors per corner, and voltage lost along the way.

## Iteration 2: modular boxes with their own brain

- Each box has its own ESP32 and everything it needs inside. The only thing that enters is **power**, on a thicker wire.
- Power can come from anywhere, so a box can sit in **any position and orientation**, not within a set distance of one
  central unit. The geometry of the room no longer limits where the winches go.
- Plug and play: once a box works, it works indefinitely. It **slides on and off the wall** and plugs and unplugs. When
  guests come, or the robot is not wanted in the room, each box slips off and goes in a drawer; back on, one plug, it
  joins the Wi-Fi by itself and works.
- Not a tangle of wires from a central area: a **product**. If these were ever sold, they would be individual packaged
  boxes with one plug and a Wi-Fi setup.
- The mounts are separate from the boxes, so they can be customised later: today a slide-in mount screwed into a stud,
  later a clamp onto a pole, the way gym equipment attaches.

## The gripper: a modular test bed

- The gripper attaches in a modular way **by design**, so different grippers can be tried to find what works best on
  shirts.
- A hard-material pinch was expected to work better; testing showed it does not, because of alignment problems.
- Other materials, TPU among them, are being tried. Still testing; this part is not a big deal to the system.
- The deck should not open with "I planned TPU tendon fingers and then switched". One slide on the modular gripper and
  the experiments is enough.
