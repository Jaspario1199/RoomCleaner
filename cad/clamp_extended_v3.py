"""Primary extended claw: upper electronics, lower servo/clamp, printed removable uprights."""
import json
from pathlib import Path
from functools import lru_cache
import cadquery as cq
from cad import clamp_v1 as old,clamp_camera_v2 as prev,extended_camera_pod as pod
OUT=Path('cad/exports/clamp_extended_v3')
EXTENSION=150.; POST_X=43.; PAD_Z=old.PAD_BOTTOM-EXTENSION

def move(p):return p.translate((0,0,-EXTENSION))

@lru_cache(maxsize=1)
def upper_deck():
 p=prev.deck().union(old.box(105,62,4))
 for x in (-48,46):
  for y in (-12,12):p=old.hole_z(p,x,y,3.4,-1,6)
 for x in (-49,49):
  for y in (-24,24):p=old.hole_z(p,x,y,3.4,-1,6)
 p=p.cut(old.box(8,8,6,(43,34,-1))) # protected servo harness exit
 return p

@lru_cache(maxsize=1)
def lower_carrier():
 p=old.box(140,90,4).edges('|Z').fillet(5)
 p=p.cut(old.box(43,22,6,(-10.5,0,-1)))
 p=p.cut(old.box(40,14,6,(0,45,-1))) # optical notch between forward rail mounts
 for x in (-34.5,13.5):
  for y in (-5,5):p=p.cut(cq.Workplane('XY').center(x,y).slot2D(5,3.4).extrude(6).translate((0,0,-1)))
 for x in (-53,53):
  for y in (-35,35):p=old.hole_z(p,x,y,3.4,-1,6)
 for x in (-43,43):
  for y in (-36,36):p=old.hole_z(p,x,y,3.4,-1,6)
 for x in (22,31):p=p.cut(old.box(2.5,8,6,(x,0,-1))) # lower servo harness ties
 return move(p)

@lru_cache(maxsize=2)
def upright(side):
 x=side*POST_X
 p=old.box(14,18,EXTENSION-10,(x,0,-EXTENSION+4))
 p=p.cut(old.box(8,12,EXTENSION-10.2,(x,0,-EXTENSION+4.1)))
 p=p.union(old.box(24,82,6,(x,0,-6)))
 p=p.union(old.box(24,82,6,(x,0,-EXTENSION+4)))
 for y in (-24,24):p=old.hole_z(p,side*49,y,3.4,-7,8)
 for y in (-36,36):p=old.hole_z(p,x,y,3.4,-EXTENSION+3,8)
 if side==-1:p=p.cut(old.box(20,24,7,(-30,0,-EXTENSION+4))) # servo ear/head relief
 if side==1:
  p=p.cut(old.box(8,12,8,(x,0,-7)))
  p=p.cut(old.box(8,44,4,(x,16,-4))) # enclosed upper elbow to deck exitY34
  p=p.cut(old.box(8,8,8,(x,8,-EXTENSION+14))) # lower lead exit
 return p

@lru_cache(maxsize=1)
def camera():return pod.pose(cq.importers.importStep(str(pod.OEM)))

def parts(angle=0,with_cover=True):
 p=old.components(angle,with_cover)
 for n in ('esp32_tray','esp32_reference','board_foam_reference'):p.pop(n)
 p['deck']=upper_deck()
 for n in ('rail_left','rail_right','jaw_left','jaw_right','pad_left','pad_right','pinion','horn_reference','servo_reference'):p[n]=move(p[n])
 p.update(lower_carrier=lower_carrier(),upright_left=upright(-1),upright_right=upright(1),camera_cradle=pod.cradle(),camera_keeper_left=pod.keeper(-1),camera_keeper_right=pod.keeper(1),camera_oem_reference=camera())
 p['camera_usb_access_reference']=pod.pose(pod.local_box(12,18,6,v=22.585,z=8.8))
 p['camera_harness_access_reference']=pod.pose(pod.local_box(10,8,6,v=-15.1,z=6))
 for x in (-18,18):p[f'camera_deck_head_{x}_reference']=cq.Workplane('XY').center(x,70).circle(3).extrude(2).translate((0,0,8))
 for side in (-1,1):p[f'camera_keeper_head_{side}_reference']=pod.pose(cq.Workplane('XY').center(side*14,0).circle(3).extrude(2).translate((0,0,10.1)))
 for label,x,ys,z in [('upper',49,(-24,24),4),('lower',43,(-36,36),-EXTENSION+10)]:
  for side in (-1,1):
   for y in ys:
    p[f'extension_{label}_head_{side}_{y}_reference']=cq.Workplane('XY').center(side*x,y).circle(3).extrude(2).translate((0,0,z))
    nz=-10.5 if label=='upper' else -EXTENSION-4.5
    p[f'extension_{label}_nut_{side}_{y}_reference']=cq.Workplane('XY').center(side*x,y).polygon(6,6.4).circle(1.7).extrude(4).translate((0,0,nz))
 return p

def main():
 OUT.mkdir(parents=True,exist_ok=True);p=parts();report={}
 for n,s in p.items():
  assert s.val().isValid(),n
  printable='reference' not in n and 'cable_ring' not in n
  if printable:assert len(s.solids().vals())==1,(n,len(s.solids().vals()))
  cq.exporters.export(s,str(OUT/(n+'.step')))
  if printable:
   r=cq.importers.importStep(str(OUT/(n+'.step')));assert abs(r.val().Volume()-s.val().Volume())<.001,n
   if n.startswith('camera_keeper'):s=s.translate(tuple(-q for q in pod.ORIGIN)).rotate((0,0,0),(1,0,0),pod.TILT)
   if n.startswith('upright'):s=s.rotate((0,0,0),(0,1,0),90) # print long uprights on side; support5mm under midsection
   b=s.val().BoundingBox();s=s.translate((0,0,-b.zmin));cq.exporters.export(s,str(OUT/(n+'.stl')))
  b=p[n].val().BoundingBox();report[n]={'solids':len(p[n].solids().vals()),'bounds':[[getattr(b,c+'min'),getattr(b,c+'max')] for c in 'xyz']}
 for a,label in ((0,'open'),(120,'closed')):
  assembly=cq.Assembly(name='Extended_claw_'+label)
  for n,s in parts(a).items():assembly.add(s,name=n)
  assembly.save(str(OUT/('extended_claw_'+label+'.step')))
 (OUT/'geometry.json').write_text(json.dumps(report,indent=2))
 (OUT/'geometry_profile.json').write_text(json.dumps({'extension_mm':EXTENSION,'pad_bottom_z_mm':PAD_Z,'anchor_plane_to_pad_m':(old.CABLE_PLANE-PAD_Z)/1000,'camera_tilt_deg':pod.TILT,'requires_reach_and_collision_model_update':True},indent=2))
 print('Extended primary assembly exported; grip reach',(old.CABLE_PLANE-PAD_Z)/1000,'m')
if __name__=='__main__':main()
