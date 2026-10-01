"""Encoder-ready generation of the original printed spool, mm.
Preserves its D-bore, radial grub screw, tie hole, drum and flange dimensions.
Three M3x6 screws with1mm head spacers retain a removable magnet cap; no adhesive-only cap retention.
"""
import math
import cadquery as cq
from .winch_spool import make as original
from ..params import SPOOL_LEN,SPOOL_FLANGE_THK,SPOOL_FLANGE_DIA
MAGNET_D=6.35
MAGNET_T=3.175
PILOT_D=2.8
SCREW_RADIUS=13.
TOTAL=SPOOL_LEN+2*SPOOL_FLANGE_THK

def screw_points():
    return [(SCREW_RADIUS*math.cos(math.radians(a)),SCREW_RADIUS*math.sin(math.radians(a))) for a in (0,120,240)]

def make():
    spool=original()
    for x,y in screw_points():
        spool=spool.cut(cq.Workplane('XY').center(x,y).circle(PILOT_D/2).extrude(2.85).translate((0,0,TOTAL-2.85)))
    return spool

def magnet_cap():
    # Cup skirt pilots over flange; disk seats against its outer face.
    cap=cq.Workplane('XY').circle(SPOOL_FLANGE_DIA/2+1.2).circle(SPOOL_FLANGE_DIA/2+.2).extrude(3)
    cap=cap.union(cq.Workplane('XY').circle(SPOOL_FLANGE_DIA/2+1.2).extrude(MAGNET_T).translate((0,0,3)))
    cap=cap.cut(cq.Workplane('XY').circle((MAGNET_D+.2)/2).extrude(MAGNET_T+.1).translate((0,0,3)))
    for x,y in screw_points():
        cap=cap.cut(cq.Workplane('XY').center(x,y).circle(1.7).extrude(MAGNET_T+.1).translate((0,0,3)))
        cap=cap.cut(cq.Workplane('XY').center(x,y).circle(3.2).extrude(1.1).translate((0,0,3+MAGNET_T-1)))
    return cap
