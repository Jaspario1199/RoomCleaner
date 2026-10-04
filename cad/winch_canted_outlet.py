"""Fixed-canted55deg-cone cartridge experiment. Separate from print release.
Global +Y up,+Z room. Outward axis(1,-1,1)/sqrt3; mirrorX for othercorner.
No passive alignment or strength qualification is implied.
"""
from pathlib import Path
import math,json
from itertools import combinations
import cadquery as cq
from cad.winch_bench import build,box,cyl,along_y
OUT=Path(__file__).parent/'exports'/'canted_outlet'
THROAT=(20.,-68.25,43.)
ANGLE=math.degrees(math.acos(1/math.sqrt(3)))
def place(p,hand=1):
 q=p.rotate((0,0,0),(-1,0,1),ANGLE).translate(THROAT)
 return q if hand==1 else q.mirror('YZ')
def cone(a,b,h,y=0):return cq.Workplane('XY').newObject([cq.Solid.makeCone(a,b,h,cq.Vector(0,y,0),cq.Vector(0,1,0))])
def local_parts():
 old=build();origin=(-20,68.25,-43)
 ring=old['metal_eyelet_reference'].translate(origin)
 slope=math.tan(math.radians(65))
 shell=cone(11,11+12*slope,12).cut(cone(2.85,2.85+12*slope,12))
 # Expose ring shoulders/mouth; neckcapture remains1.5thick atY±.75.
 shell=shell.cut(along_y(cyl(7.7,4),0,4,0))
 capture=along_y(cyl(11,1.5).cut(cyl(4.4,2)),0,.75,0)
 shell=shell.union(capture)
 for x in (-24,24):
  # Guides remainSHS3-12, thread4 intoY4.25..8.25.
  boss=box(10,4,14,x=x,y=6.25,z=-7)
  shell=shell.union(boss).cut(along_y(cyl(1.4,4),x,8.25,0))
  stop=box(8,9,1.5,x=x,y=3.75,z=-5)
  shell=shell.union(stop)
 for x in (-28,28):shell=shell.union(cyl(5,14,x,10,-8))
 shell=shell.cut(cone(2.85,2.85+12*slope,12))
 lower=shell.intersect(box(90,40,45,y=8,z=-45))
 upper=shell.intersect(box(90,40,45,y=8,z=0))
 for x in (-28,28):
  lower=lower.cut(cyl(1.4,7,x,10,-7))
  upper=upper.cut(cyl(1.7,7,x,10,0)).cut(cyl(3.1,40,x,10,6))
 collar=along_y(cyl(17,4).cut(cyl(13,5)),0,-2.75,0)
 for x in (-24,24):
  collar=collar.union(box(16,4,10,x=x,y=-4.75,z=-5))
  collar=collar.cut(along_y(cyl(2.15,6),x,-1.75,0))
 collar=collar.cut(box(5.3,6,4.3,x=24,y=-4.75,z=-2.15))
 # MoveKW bodyoutward26mm so it does not occupyincoming55degcone.
 # Its fastenedadjustablemount remainspending ratherthan pretendingoldplatefits.
 collar=collar.union(box(12,4,10,x=34,y=-4.75,z=0))
 collar=collar.union(box(4,4,14,x=38,y=-4.75,z=0)).union(box(6,3.55,5,x=36,y=-.975,z=8.5))
 bead=along_y(cyl(14,8).edges('%Circle').fillet(1).cut(cyl(.6,9)).cut(cyl(3.5,3,0,0,5)),0,-16.75,0)
 p={'lower_carrier':lower,'upper_capture':upper,'homing_collar':collar,'metal_ring_reference':ring,'stopper':bead}
 for n in ('switch_body_reference','switch_lever_reference','switch_roller_reference'):
  p[n]=old[n].translate(origin).translate((26,0,0))
 for i,x in enumerate((-24,24)):
  p[f'guide_{i}_reference']=along_y(cyl(2,12),x,4.25,0).union(along_y(cyl(1.5,4),x,8.25,0)).union(along_y(cyl(3,3),x,-7.75,0))
  p[f'washer_{i}_reference']=along_y(cyl(3.5,1).cut(cyl(2.15,1.2)),x,-6.75,0)
  p[f'spring_{i}_reference']=along_y(cyl(3.175,7).cut(cyl(2.665,8)),x,4.25,0)
 for i,x in enumerate((-28,28)):
  p[f'capture_bolt_{i}_reference']=cyl(1.5,12,x,10,-6).union(cyl(2.85,1.7,x,10,6))
 return p

def volume(a,b):
 aa=a.val().BoundingBox();bb=b.val().BoundingBox()
 if any(getattr(aa,t+'max')<=getattr(bb,t+'min') for t in 'xyz')or any(getattr(bb,t+'max')<=getattr(aa,t+'min')for t in 'xyz'):return 0.
 return sum(s.Volume()for s in a.intersect(b).solids().vals())
def cable_segment(a,b):
 d=cq.Vector(*b).sub(cq.Vector(*a));return cq.Workplane('XY').newObject([cq.Solid.makeCylinder(.3,d.Length,cq.Vector(*a),d.normalized())])
def main():
 OUT.mkdir(parents=True,exist_ok=True);p=local_parts();world={n:place(s)for n,s in p.items()};rows=[]
 for n,s in p.items():
  rows.append(dict(check='solid',part=n,valid=s.val().isValid(),solids=len(s.solids().vals())))
 # Exhaustive installed pairs; only modeled pilot-thread and purchased lever joint
 # overlaps are intentional. Keep every failed result visible.
 allowed=set()
 for part in ('lower_carrier','upper_capture'):
  for i in range(2):allowed.add(frozenset((part,f'guide_{i}_reference')))
 for i in range(2):allowed.add(frozenset(('lower_carrier',f'capture_bolt_{i}_reference')))
 allowed.add(frozenset(('switch_lever_reference','switch_roller_reference')))
 for a,b in combinations(p,2):
  v=volume(p[a],p[b]);intentional=frozenset((a,b)) in allowed
  rows.append(dict(check='installed_pair',a=a,b=b,overlap_mm3=v,intentional=intentional,passed=v<.001 or intentional))
 for x in (-28,28):
  ann=cyl(2.85,.1,x,10,5.9).cut(cyl(1.7,.2,x,10,5.85))
  required=ann.val().Volume();actual=volume(ann,p['upper_capture'])
  rows.append(dict(check='full_clamp_head_bearing',x=x,required_mm3=required,actual_mm3=actual,passed=actual>=required-.001))
 old=build()
 for n in ('lower_carrier','upper_capture','homing_collar','switch_body_reference'):
  for fixed in ('base','cover'):
   v=volume(world[n],old[fixed]);rows.append(dict(check='existing_case_fit',part=n,case=fixed,overlap_mm3=v,passed=v<.001))
 # All windingpositions/radii/azimuths;exclude last3.8mm atmetalring because
 # cablebendsinsideactualroundedmetalguide,notastraightthroughringline.
 for x in (4.5,12.5,20.5,28.5,36.5):
  for radius in (10,12.5,15):
   for az in range(0,360,30):
    a=(x,30+radius*math.cos(math.radians(az)),33+radius*math.sin(math.radians(az)))
    d=cq.Vector(*a).sub(cq.Vector(*THROAT));b=cq.Vector(*THROAT).add(d.normalized().multiply(3.8)).toTuple();line=cable_segment(a,b)
    hits={n:volume(line,s)for n,s in world.items()if n not in ('metal_ring_reference','stopper','homing_collar')}
    rows.append(dict(check='incoming_spool_corridor',x=x,radius=radius,azimuth=az,hits={n:v for n,v in hits.items()if v>.001},passed=all(v<.001 for v in hits.values())))
 # Outgoing55degcone fromworstthroat-edgepoint, notjustaxialline.
 for angle in (0,15,30,45,55):
  for az in range(0,360,30):
   c=math.cos(math.radians(az));s=math.sin(math.radians(az));r=2.55
   a=(r*c,0,r*s);b=((r+30*math.tan(math.radians(angle)))*c,-30,(r+30*math.tan(math.radians(angle)))*s)
   line=cable_segment(a,b)
   hits={n:volume(line,v)for n,v in p.items()if n not in ('metal_ring_reference','stopper')}
   rows.append(dict(check='outgoing55cone',angle=angle,azimuth=az,hits={n:v for n,v in hits.items()if v>.001},passed=all(v<.001 for v in hits.values())))
 for t in (0,.5,1,1.5,2):
  c=p['homing_collar'].translate((0,t,0))
  hits={n:volume(c,p[n])for n in ('lower_carrier','upper_capture','metal_ring_reference','switch_body_reference')}
  rows.append(dict(check='collar_stroke',travel=t,hits=hits,passed=all(v<.001 for v in hits.values())))
 for t in range(13):
  b=p['stopper'].translate((0,t,0));hits={n:volume(b,p[n])for n in ('lower_carrier','upper_capture','metal_ring_reference')}
  rows.append(dict(check='axial_bead_approach',travel=t,hits=hits,passed=all(v<.001 for v in hits.values())))
 assembly=cq.Assembly(name='Canted_outlet_experimental_geometry')
 for n,s in world.items():assembly.add(s,name=n)
 assembly.save(str(OUT/'canted_outlet_experiment.step'))
 failed=[r for r in rows if r.get('passed')is False or r.get('valid')is False or(r.get('check')=='solid'and r.get('solids')!=1)]
 (OUT/'audit.json').write_text(json.dumps(dict(checks=len(rows),failures=len(failed),results=rows,limits='No basebracket orsecuredKWmount; fullspoolcorridoris sampledgeometricpotentiallinepath,not tangency/winding certification;failedpaths are not waived.'),indent=2))
 print(len(rows),'checks;',len(failed),'failures; NOT printrelease')
if __name__=='__main__':main()
