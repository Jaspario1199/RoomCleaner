"""
Gen-2 accessory: aluminium heat-spreader / fin plate for the NEMA 17 winch
motor (design review R11). Sandwiched between the motor's front flange and
the 5 mm PETG motor tab of Slipin_mount_piece_v3; the upper part passes
through a slot in the shell into room air.

Interface (measured from solidworks/v3_2026-10-18/Slipin_mount_piece_v3.STEP):
motor tab pilot hole Ø22.4, 4× Ø3.5 on a 31.0 mm square, motor axis 21.1 mm
above the deck top (z 34.6 vs deck 13.47).

    /usr/bin/python3 -m cad.parts.motor_heat_plate
"""
import cadquery as cq

T = 3.0            # mm, 5052-H32 or 6061-T6 (1/8" = 3.175 also fine)
W = 100.0          # mm, width (along the housing's 127 mm side)
H = 100.0          # mm, height
AXIS_FROM_BOTTOM = 21.0   # mm, motor axis above the plate's bottom edge (deck clearance 0.1 mm)
PILOT_D = 22.5     # mm, motor boss Ø22.0 + clearance
BOLT_SQ = 31.0     # mm, NEMA 17 bolt square
BOLT_D = 3.4       # mm, M3 clearance
CORNER_R = 3.0


def make():
    cx, cy = W / 2, AXIS_FROM_BOTTOM
    plate = (cq.Workplane("XY").rect(W, H, centered=False).extrude(T)
             .edges("|Z").fillet(CORNER_R))
    h = BOLT_SQ / 2
    plate = (plate.faces(">Z").workplane(origin=(0, 0, T))
             .pushPoints([(cx, cy)]).hole(PILOT_D)
             .faces(">Z").workplane(origin=(0, 0, T))
             .pushPoints([(cx + dx, cy + dy) for dx in (-h, h) for dy in (-h, h)])
             .hole(BOLT_D))
    return plate


if __name__ == "__main__":
    p = make()
    out = "solidworks/heat_plate/motor_heat_plate"
    cq.exporters.export(p, out + ".step")
    cq.exporters.export(p.faces("<Z"), out + ".dxf")   # 2D outline + holes for laser/waterjet
    v = p.val().Volume()
    print(f"volume {v:.0f} mm^3, mass {v*2.7e-3:.0f} g (aluminium)")
    print(out + ".step / .dxf")
