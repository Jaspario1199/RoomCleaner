"""Camera-equipped derivative. OEM frame: localU=-Z-6.1114,V=X-1.805,W=13.71-Y.
W=0 is lens front; +W goes behind camera. All mm. Requires downloaded OEM STEP.
"""
from pathlib import Path
from functools import lru_cache
import json
import cadquery as cq
from cad import clamp_v1 as old
OUT=Path('cad/exports/clamp_camera_v2')
OEM=OUT/'camera_oem_normalized.step'
TILT=40.; ORIGIN=(0.,96.,22.)

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
  mount=mount.union(old.box(8,40,4,(x,93,4)))
  mount=mount.union(old.box(8,12,32,(x,107,8)))
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

@lru_cache(maxsize=1)
def deck():
 p=old.deck()
 for x in (-18,18):p=old.hole_z(p,x,70,3.4,-1,6)
 return p

@lru_cache(maxsize=1)
def camera():return pose(cq.importers.importStep(str(OEM)))

def parts(angle=0,with_cover=True):
 p=old.components(angle,with_cover)
 for n in ('esp32_tray','esp32_reference','board_foam_reference'):p.pop(n)
 p['deck']=deck()
 p.update(camera_cradle=cradle(),camera_keeper_left=keeper(-1),camera_keeper_right=keeper(1),camera_oem_reference=camera())
 p['camera_usb_access_reference']=pose(local_box(12,18,6,v=22.585,z=8.8))
 p['camera_harness_access_reference']=pose(local_box(10,8,6,v=-15.1,z=6))
 # Nonmagnetic hardware envelopes; shank/pilot contact checked separately.
 for x in (-18,18):
  p[f'camera_deck_nut_{x:g}_reference']=cq.Workplane('XY').center(x,70).polygon(6,6.4).circle(1.7).extrude(4).translate((0,0,-4.5))
  p[f'camera_deck_washer_{x:g}_reference']=cq.Workplane('XY').center(x,70).circle(3.2).circle(1.7).extrude(.5).translate((0,0,-.5))
  p[f'camera_deck_head_{x:g}_reference']=cq.Workplane('XY').center(x,70).circle(3).extrude(2).translate((0,0,8))
 for side in (-1,1):
  p[f'camera_keeper_head_{side}_reference']=pose(cq.Workplane('XY').center(14*side,0).circle(3).extrude(2).translate((0,0,10.1)))
 return p

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 p=parts();report={}
 for n,s in p.items():
  assert s.val().isValid(),n
  if 'reference' not in n and 'cable_ring' not in n:assert len(s.solids().vals())==1,(n,len(s.solids().vals()))
  cq.exporters.export(s,str(OUT/(n+'.step')))
  if 'reference' not in n and 'cable_ring' not in n:
   restored=cq.importers.importStep(str(OUT/(n+'.step')))
   assert abs(restored.val().Volume()-s.val().Volume())<.001,n
  b=s.val().BoundingBox();report[n]={'solids':len(s.solids().vals()),'bounds':[[getattr(b,c+'min'),getattr(b,c+'max')] for c in 'xyz']}
  if 'reference' not in n and 'cable_ring' not in n:
   # New pod parts export in local camera coordinates for slicing.
   if n.startswith('camera_keeper'):s=s.translate(tuple(-q for q in ORIGIN)).rotate((0,0,0),(1,0,0),TILT)
   b=s.val().BoundingBox();s=s.translate((0,0,-b.zmin))
   cq.exporters.export(s,str(OUT/(n+'.stl')))
 for angle,label in ((0,'open'),(120,'closed')):
  a=cq.Assembly(name='RoomCleaner_camera_'+label)
  for n,s in parts(angle).items():a.add(s,name=n)
  a.save(str(OUT/('camera_clamp_'+label+'.step')))
 (OUT/'geometry.json').write_text(json.dumps(report,indent=2))
 print('Camera-equipped open/closed assemblies and printable parts exported')
if __name__=='__main__':main()
