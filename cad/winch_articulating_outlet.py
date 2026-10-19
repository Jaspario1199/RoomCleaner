"""Experimental two-axis outlet geometry, not a released wall station.
Yaw Z and pitch X intersect the ring throat. No passive alignment is claimed.
8mm cut steel pins and printed bushings require physical qualification.
"""
from pathlib import Path
import json
import cadquery as cq
from cad.winch_bench import build,box,cyl,along_x
OUT=Path(__file__).parent/'exports'/'articulating_outlet'

def frame(outer,inner):
 return box(outer,8,outer,z=-outer/2).cut(box(inner,10,inner,z=-inner/2))
def pose(s,yaw,pitch=0):
 return s.rotate((0,0,0),(1,0,0),pitch).rotate((0,0,0),(0,0,1),yaw)
def parts():
 p=build(); names=['guide_carrier','outlet_backplate','homing_collar','switch_mount','metal_eyelet_reference','switch_body_reference','switch_lever_reference','switch_roller_reference']
 cartridge={n:p[n].translate((-20,68.25,-43)) for n in names}
 pitch=frame(140,120);yaw=frame(180,160);fixed=frame(220,200)
 # Pivot sockets are geometry only; cut steel pins must be retained with
 # separately qualified M3 split clamp collars. No glue-fit axle retention.
 for sign in (-1,1):
  pitch=pitch.cut(along_x(cyl(4.2,12),sign*62 if sign>0 else -74,0,0))
  yaw=yaw.cut(along_x(cyl(8.1,12),sign*80 if sign>0 else -92,0,0))
  yaw=yaw.cut(cyl(4.2,12,0,0,sign*82 if sign>0 else -94))
  fixed=fixed.cut(cyl(8.1,12,0,0,sign*100 if sign>0 else -112))
 bushings={};pins={}
 for sign in (-1,1):
  bushings[f'pitch_bushing_{sign}']=along_x(cyl(8,8).cut(cyl(4.2,9)),80 if sign>0 else -88,0,0)
  pins[f'pitch_pin_{sign}_reference']=along_x(cyl(4,28),62 if sign>0 else -90,0,0)
  bushings[f'yaw_bushing_{sign}']=cyl(8,8,0,0,100 if sign>0 else -108).cut(cyl(4.2,9,0,0,99.5 if sign>0 else -108.5))
  pins[f'yaw_pin_{sign}_reference']=cyl(4,28,0,0,82 if sign>0 else -110)
 return cartridge,pitch,yaw,fixed,bushings,pins

def volume(a,b):
 aa=a.val().BoundingBox();bb=b.val().BoundingBox()
 if any(getattr(aa,t+'max')<=getattr(bb,t+'min') or getattr(bb,t+'max')<=getattr(aa,t+'min')for t in 'xyz'):return 0
 return sum(s.Volume()for s in a.intersect(b).solids().vals())
def main():
 OUT.mkdir(parents=True,exist_ok=True);cart,pitch,yaw,fixed,bush,pins=parts();results=[]
 for y in (-60,-30,0,30,60):
  for t in (-60,-30,0,30,60):
   a=pose(pitch,y,t);b=pose(yaw,y)
   for name,s in [('pitch_vs_yaw',b),('pitch_vs_fixed',fixed)]:
    v=volume(a,s);assert v<.001,(y,t,name,v);results.append(dict(yaw=y,pitch=t,pair=name,volume=v))
   for n,s in cart.items():
    moving=pose(s,y,t)
    for nn,f in [('pitch',a),('yaw',b),('fixed',fixed)]:
     v=volume(moving,f);assert v<.001,(y,t,n,nn,v);results.append(dict(yaw=y,pitch=t,pair=n+'/'+nn,volume=v))
   v=volume(b,fixed);assert v<.001,(y,'yaw/fixed',v)
 # Adversarial functional check: stationary spool-side line, not a line
 # silently rotated with the cartridge. Failures are recorded as failures.
 line=cyl(.3,80).rotate((0,0,0),(1,0,0),-90)
 cable=[]
 for y,t in [(0,0),(30,0),(0,30),(45,0),(0,45),(60,60)]:
  v=volume(line,pose(cart['guide_carrier'],y,t))
  cable.append(dict(yaw=y,pitch=t,cable_carrier_intersection_mm3=v,route_clear=v<.001))
 (OUT/'incoming_cable_failure.json').write_text(json.dumps(cable,indent=2))
 assembly=cq.Assembly(name='Experimental_outlet_clearance_skeleton')
 for n,s in {**cart,'pitch_frame':pitch,'yaw_frame':yaw,'fixed_frame':fixed,**bush,**pins}.items():assembly.add(s,name=n)
 assembly.save(str(OUT/'experimental_clearance_skeleton.step'))
 (OUT/'audit.json').write_text(json.dumps(dict(checks=len(results),results=results,limits='Sampled frame/cartridge clearance only. No cartridge-to-frame attachment, pin retention, load rating, internal cable path or passive alignment qualification. Not printable release.'),indent=2))
 print(len(results),'experimental geometric clearances passed; integration and retention remain unresolved')
if __name__=='__main__':main()
