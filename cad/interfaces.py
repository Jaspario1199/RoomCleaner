"""
Interface contracts for the RoomCleaner claw (authoritative).

Every mating relationship lives HERE, once. Part scripts import these values;
no part may re-declare a number that appears in this file. Units: mm, degrees.

Coordinate convention (claw assembly):
    Z=0 at the frame plate TOP surface, +Z up toward the ceiling.
    The cable tie-off plane is at boss top, Z = +3.
    The hub hangs below: hub TOP face at Z = -(PLATE_THK + STANDOFF_LEN).
"""

# ---- frame <-> hub standoff joint (D3, D6) --------------------------------
HUB_MOUNT_R = 27.0            # shared bolt circle radius, frame AND hub
STANDOFF_ANGLES_DEG = (36.0, 108.0, 252.0, 324.0)   # clear of 5 finger pockets @72°
STANDOFF_LEN = 40.0           # frame underside -> hub top face
STANDOFF_OD = 10.0
STANDOFF_SCREW = "M3x8 into heat-set insert each end"

# ---- servo <-> frame (D2) --------------------------------------------------
SERVO_MODEL = "MG996R"
SERVO_MOUNT = "inverted: body above plate, spline down through pocket"
SERVO_POCKET_L = 41.0         # through-cutout in the plate
SERVO_POCKET_W = 20.2
SERVO_EAR_SPAN = 48.3         # ear screw hole c-c (2 holes per ear pair axis)
SERVO_EAR_TAP = 2.8           # self-tap M3 into 5 mm PETG plate
SERVO_BODY_ABOVE = 38.0       # body height above plate when inverted (cover must clear)

# ---- servo horn <-> tendon drum (D4) ---------------------------------------
HORN_TYPE = "MG996R round horn"
HORN_POCKET_DIA = 21.6        # horn nests into drum top pocket
HORN_POCKET_T = 2.4
HORN_SCREW_CIRCLE = 14.0      # 4x Ø2.4 through-holes for horn self-tap screws
HORN_SCREW_HOLE = 2.4

# ---- servo throw contract (C2; firmware MUST match) ------------------------
SERVO_RELEASE_DEG = 20        # tentacles open; horn attached at this angle (/setup)
SERVO_GRIP_DEG = 140          # tentacles curled
SERVO_THROW_DEG = SERVO_GRIP_DEG - SERVO_RELEASE_DEG   # 120 deg
# roomcleaner/hardware/hw_config.py GRIP_ANGLE/RELEASE_ANGLE and the ESP32
# firmware must equal these values — drum sizing (below) depends on the throw.

# ---- tendon drum (C1/C2) ----------------------------------------------------
DRUM_CORE_R = 13.5            # winds >=27 mm over SERVO_THROW_DEG (C2)
DRUM_CORE_H = 8.0
DRUM_FLANGE_R = 16.5
DRUM_FLANGE_T = 2.2
DRUM_TIEOFF_HOLES = 5         # Ø2.0 through BOTTOM flange at r=DRUM_CORE_R, 72° pitch
DRUM_TIEOFF_HOLE_D = 2.0      # reachable through the hub bore after assembly (R5)

# ---- finger <-> hub (D5) ----------------------------------------------------
HUB_THK = 12.0                # hub disc thickness == finger slot engagement length
FINGER_POCKET = "through-slot"          # no floor; finger inserted from BELOW
FINGER_ENGAGE_LEN = HUB_THK              # finger local z [0, HUB_THK] fills the slot
FINGER_SHOULDER_Z0 = HUB_THK             # shoulder starts JUST BELOW the slot --
                                         # local z [HUB_THK, HUB_THK+FINGER_SHOULDER_T]
                                         # (z=0 is the mounting end face, flush with hub top)
FINGER_SHOULDER_T = 2.0                  # lip thickness; bears on hub UNDERSIDE
FINGER_SHOULDER_GROW = 2.0               # lip overhang per side beyond base section
FINGER_RETAIN = "axial M3x16 + washer from hub top into finger base tap"

# ---- cover <-> frame (D7) ---------------------------------------------------
COVER_SCREW_POS = 40.0        # 4 tabs at edge midpoints (±x,0),(0,±y) on plate top
COVER_SCREW = "M3 into heat-set insert in plate top"
COVER_INNER_H = 42.0          # clears SERVO_BODY_ABOVE + wire
COVER_CORNER_NOTCH = 26.0     # 45° corner cuts clearing the cable cones
COVER_WALL = 2.4

# ---- cables <-> frame (R11) -------------------------------------------------
CABLE_HOLE_D = 3.2            # corner boss tie-off holes; knot spec: Palomar

# ---- claw <-> motion software (D9) -----------------------------------------
EFFECTOR_REACH_M = 0.118      # cable plane -> fingertips (integration-measured:
                              # boss top 8 + standoffs 40 + finger 70; the hub 12 is
                              # INSIDE the finger base, not additive — C5 corrected)
