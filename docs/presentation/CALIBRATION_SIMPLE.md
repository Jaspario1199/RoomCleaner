# How the robot calibrates itself, in plain words (lead, 10/27; from roomcleaner/cdpr/startup.py)

The claw starts sitting on the floor on a printed mat it can see with its camera. Six steps, in order; any failed check
stops everything and waits for a person.

1. **Am I sitting nicely?** The camera checks the claw is upright and at the right height on the mat. Then every station
   is asked if it is awake, healthy, and its switch is closed. Only then are the motors armed.
2. **Who is pulling me?** One station at a time reels in its cable until the claw just starts to slide or tip. That tells
   the robot how long that cable is and which way it goes. No tug within the slack budget means "cable not attached."
3. **Up we go, a little.** All cables tighten together and lift the claw a few millimetres at a time. After each step the
   camera checks it rose as much as commanded, did not drift sideways, did not tilt.
4. **One good look.** Hanging still, the camera takes a careful look at the mat: now it knows where it really is.
5. **Explore, bigger and bigger.** The claw moves to a few spots nearby, then a wider set, then wider again, looking at
   the mat at each one and refitting the model between rounds. A few surprise spots it did not learn from check whether
   the guesses are right.
6. **Can I trust myself?** From how well the guesses matched, the robot decides: "ready to work," or "only near home."

Two rules: it never retries by itself, and if a station reboots, all six steps run again before it is trusted.
