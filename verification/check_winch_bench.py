"""Complete nominal winch fit audit; explicit intentional contact exemptions."""
from itertools import combinations
import json
from cad.winch_bench import build,OUT,along_x,cyl,MOTOR_Y,SHAFT_Z,SPOOL_START
p=build();rows=[]
allowed={frozenset(x):why for x,why in [
 (('guide_carrier','guide_bolt_0_reference'),'M3 thread envelope in diameter2.8 printed pilot'),
 (('guide_carrier','guide_bolt_1_reference'),'M3 thread envelope in diameter2.8 printed pilot'),
 (('switch_lever_reference','switch_roller_reference'),'Schematic parts of one purchased switch assembly')]}
def volume(a,b):
 ba=a.val().BoundingBox();bb=b.val().BoundingBox()
 if any(getattr(ba,t+'max')<=getattr(bb,t+'min')+1e-8 or getattr(bb,t+'max')<=getattr(ba,t+'min')+1e-8 for t in 'xyz'):return 0.
 return sum(s.Volume() for s in a.intersect(b).solids().vals())
for a,b in combinations(p,2):
 v=volume(p[a],p[b]);why=allowed.get(frozenset((a,b)))
 rows.append(dict(a=a,b=b,volume_mm3=v,exemption=why))
 assert v<.01 or why,(a,b,v)
for travel in (0,.25,.5,.75,1,1.25,1.5,1.75,2):
 moving=p['homing_collar'].translate((0,travel,0))
 for name in ('base','cover','guide_carrier','switch_mount','switch_body_reference','metal_eyelet_reference','outlet_backplate','stop_sleeve_0','stop_sleeve_1'):
  v=volume(moving,p[name]);assert v<.01,(travel,name,v)
  rows.append(dict(travel_mm=travel,a='homing_collar',b=name,volume_mm3=v))
# Whole rotating spool/cup cylindrical envelopes cover every angular phase.
for name in ('spool_reference','encoder_magnet_cup','encoder_magnet_reference'):
 for fixed in ('base','cover','encoder_board_reference','encoder_chip_reference','guide_carrier'):
  v=volume(p[name],p[fixed]);assert v<.01,(name,fixed,v)
# Bead approaches10mm then presses collar2mm; check fixed ring/holder throughout.
for travel in range(13):
 bead=p['homing_stopper'].translate((0,travel,0))
 for name in ('guide_carrier','metal_eyelet_reference','outlet_backplate'):
  v=volume(bead,p[name]);assert v<.01,('bead-travel',travel,name,v)
  rows.append(dict(bead_travel_mm=travel,a='homing_stopper',b=name,volume_mm3=v))
# Complete rotation sweep of M3 button heads +1mm spacers (max head height2mm).
heads=along_x(cyl(16.2,3).cut(cyl(9.8,3.1)),SPOOL_START+32+3.175-1,MOTOR_Y,SHAFT_Z)
for fixed in ('base','cover','encoder_board_reference','encoder_chip_reference','guide_carrier'):
 v=volume(heads,p[fixed]);assert v<.01,('M3-cap-head-sweep',fixed,v)
 rows.append(dict(a='M3-cap-head-sweep',b=fixed,volume_mm3=v))
# Cover extraction forward into room, motor and cable stationary. Release wiring first.
for lift in range(1,76):
 for name in p:
  if name=='cover':continue
  v=volume(p['cover'].translate((0,0,lift)),p[name]);assert v<.01,('cover-removal',lift,name,v)
  rows.append(dict(cover_lift_mm=lift,a='cover',b=name,volume_mm3=v))
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'bench_audit.json').write_text(json.dumps(dict(checks=len(rows),results=rows,limits='Nominal geometry; switch lever pivot, wire bends and exact purchased fasteners not validated.'),indent=2))
print(len(rows),'winch sampled checks passed')
