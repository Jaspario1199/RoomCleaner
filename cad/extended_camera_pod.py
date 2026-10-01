"""Camera-equipped derivative. OEM frame: localU=-Z-6.1114,V=X-1.805,W=13.71-Y.
W=0 is lens front; +W goes behind camera. All mm. Requires downloaded OEM STEP.
"""
from pathlib import Path
from functools import lru_cache
import json
import cadquery as cq
from cad import clamp_v1 as old
OUT=Path('cad/exports/clamp_extended_v3')
OEM=Path('cad/exports/clamp_camera_v2/camera_oem_normalized.step')
TILT=28.; ORIGIN=(0.,136.,22.)

def pose(part):
 return part.rotate((0,0,0),(1,0,0),-TILT).translate(ORIGIN)

def local_box(w,d,h,u=0,v=0,z=0):return old.box(w,d,h,(u,v,z))

@lru_cache(maxsize=1)
def cradle():
 # Open optical face; closed rear carries electrically insulating support pad.
 body=local_box(22.4,29,17.2,v=1.4,z=-.8).cut(local_box(18.4,25,16,v=1.4,z=-1.6))
 # USB and antenna/wiring exits. Slot dimensions describe access, not exact plugs.
 body=body.cut(local_box(12,10,8,v=16,z=8))
 body=body.cut(local_box(10,10,8,v=-14,z=6))
 for u in (-11,11):body=body.cut(local_box(6,14,7,u=u,z=5))
 # Keeper seats replace side wall locally; bosses take M3 threaded pilots.
 for u in (-14,14):
  body=body.union(local_box(8,12,7,u=u,z=14.1))
  body=body.cut(local_box(12,22.4,4.15,u=u,z=10))
  body=old.hole_z(body,u,0,2.8,14,7.3)
 # Rear ventilation, clear of corner foam and clamp screws.
 for u in (-4,0,4):body=body.cut(local_box(2,12,8,u=u,z=14))
 body=pose(body)
 # Two side rails leave the downward optical path open. Front crossbar bolts to deck.
 mount=old.box(44,6,4,(0,70,4))
 for x in (-18,18):
  mount=mount.union(old.box(8,80,8,(x,113,4)))
  mount=mount.union(old.box(8,12,28,(x,147,12)))
  mount=old.hole_z(mount,x,70,3.4,3,7)
 for x in (-10,10):mount=mount.cut(old.box(2.5,2,6,(x,71.5,3))) # harness tie anchors
 mount=mount.cut(pose(local_box(36.4,24,14.15,z=0))) # keep support behind keeper seats and screw heads
 mount=mount.cut(old.box(10,8,50,(0,66,0))) # front lid tab and its vertical extraction path
 return body.union(mount)

@lru_cache(maxsize=2)
def keeper(side):
 u=14*side
 p=local_box(8,22,2,u=u,z=12.1)
 # Inner0.7mm lip overlaps bare motherboard edge, not lens or camera daughterboard.
 p=p.union(local_box(2,18,.4,u=side*9.2,z=12.1))
 p=old.hole_z(p,u,0,3.4,11.5,4)
 return pose(p)

