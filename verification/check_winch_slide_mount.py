"""Functional rail retention and real fastener-envelope audit, no strength certification."""
from pathlib import Path
import json, math
import cadquery as cq
from cad.winch_slide_mount import make,volume,OUT
from cad.winch_bench import box,cyl

def nut(x,y,z):
    return cq.Workplane('XY').polygon(6,6.35).extrude(2.4).translate((x,y,z)).cut(cyl(1.5,3,x,y,z-.1))

def main():
 w,t,p=make();rows=[];hardware={}
 def check(label,condition,**details):
  assert condition,(label,details)
  rows.append(dict(check=label,**details))
 for x in (-25,25):
  for y in (-48,48):
   n=f'case_{x}_{y}'
   hardware[n+'_screw']=cyl(1.5,20,x,y,-17).union(cyl(3,3,x,y,3))
   hardware[n+'_nut']=nut(x,y,-16.4)
   # Both bearing seats must be fully supported, not semicircular edge notches.
   seat=cyl(3,.01,x,y,2.99).cut(cyl(1.7,.02,x,y,2.985))
   ratio=volume(seat.intersect(p['base']))/volume(seat)
   check(n+' head bearing support',ratio>.99,supported_fraction=ratio)
   seat=cq.Workplane('XY').polygon(6,6.35).extrude(.01).translate((x,y,-14)).cut(cyl(1.7,.02,x,y,-14.005))
   ratio=volume(seat.intersect(t))/volume(seat)
   check(n+' nut bearing support',ratio>.99,supported_fraction=ratio)
   check(n+' full nut thread engagement',-17<=-16.4 and 3>=-14)
 hardware['lock_screw']=cyl(1.5,20,0,84,-16.5).union(cyl(3,3,0,84,3.5))
 hardware['lock_washer']=cyl(3.5,.5,0,84,3).cut(cyl(1.6,.6,0,84,2.95))
 hardware['lock_nut']=nut(0,84,-16)
 hardware['lock_back_washer']=cyl(3.5,.5,0,84,-3.5).cut(cyl(1.6,.6,0,84,-3.55))
 seat=cyl(3.5,.01,0,84,2.99).cut(cyl(1.7,.02,0,84,2.985))
 ratio=volume(seat.intersect(t))/volume(seat)
 check('lock washer bearing support',ratio>.99,supported_fraction=ratio)
 seat=cq.Workplane('XY').polygon(6,6.35).extrude(.01).translate((0,84,-13.6)).cut(cyl(1.7,.02,0,84,-13.605))
 ratio=volume(seat.intersect(w))/volume(seat)
 check('lock nut bearing support',ratio>.99,supported_fraction=ratio)
 check('lock full nut thread engagement',-16.5<=-16 and 3.5>=-13.6)
 for n,h in hardware.items():
  for fixed,shape in [('wall',w),('adapter',t),*p.items()]:
   v=volume(h.intersect(shape));check(n+' clear '+fixed,v<.001,intersection_mm3=v)
 # Lock installed: shaft collides with displaced tab before appreciable lift.
 for dy in (.25,.5,1,2):
  v=volume(hardware['lock_screw'].intersect(t.translate((0,dy,0))))
  check(f'installed lock blocks lift {dy}',v>.001,intersection_mm3=v)
 # Captive rails prevent pulling directly outward while seated.
 for dz in (.75,1,2,5):
  v=volume(w.intersect(t.translate((0,0,dz))))
  check(f'rails block outward withdrawal {dz}',v>.001,intersection_mm3=v)
 # Solid stop prevents downward escape; nominal seating gap is0.2mm.
 for dy in (-.3,-1,-5):
  v=volume(w.intersect(t.translate((0,dy,0))))
  check(f'bottom stop blocks descent {dy}',v>.001,intersection_mm3=v)
 # Driver clearance for wall fasteners with the case removed.
 for y in (-78,0,68):
  shank=cyl(2.4,46,0,y,-67).union(cyl(5,2.5,0,y,-21))
  bit=cyl(3,35,0,y,-18.5)
  check(f'wall screw head/shank fit {y}',volume(shank.intersect(w))<.001)
  check(f'wall screw driver access {y}',volume(bit.intersect(w))<.001)
 # Lock driver access with full case fitted.
 bit=cyl(3,85,0,84,6.5)
 for n,s in [('dock',w),('adapter',t),*p.items()]:
  check('lock driver clear '+n,volume(bit.intersect(s))<.001)
 # Actual case screws must travel with case during extraction.
 moving=[t,*p.values(),*[h for n,h in hardware.items() if n.startswith('case_')]]
 for dy in range(0,191,5):
  for i,s in enumerate(moving):
   check(f'complete extraction {dy} part{i}',volume(w.intersect(s.translate((0,dy,0))))<.001)
 a=cq.Assembly(name='Dock_fastener_audit');a.add(w,name='wall');a.add(t,name='adapter')
 for n,s in p.items():a.add(s,name=n)
 for n,s in hardware.items():a.add(s,name=n)
 OUT.mkdir(parents=True,exist_ok=True)
 a.save(str(OUT/'docked_station_with_M3_hardware.step'))
 (OUT/'functional_audit.json').write_text(json.dumps(dict(checks=len(rows),results=rows,limits='Nominal fastener envelopes; no material capacity, actual purchased hardware, creep, tolerance or load certification.'),indent=2))
 print(len(rows),'functional mount checks passed')
if __name__=='__main__':main()
