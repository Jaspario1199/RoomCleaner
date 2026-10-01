"""Expanded assembly checks. Nominal solid envelopes, no physical guarantees."""
import json
from pathlib import Path
from itertools import combinations
from cad.clamp_v1 import components, OUT, cover
rows=[]
def check(p,a,b,pose):
 ba=p[a].val().BoundingBox();bb=p[b].val().BoundingBox()
 separated=any(getattr(ba,axis+'max')<=getattr(bb,axis+'min')+1e-8 or getattr(bb,axis+'max')<=getattr(ba,axis+'min')+1e-8 for axis in ('x','y','z'))
 v=0.0 if separated else p[a].val().intersect(p[b].val()).Volume()
 rows.append(dict(pose=pose,a=a,b=b,intersection_mm3=v))
 assert v<.01,(pose,a,b,v)
p=components()
for a,b in combinations(p,2):check(p,a,b,'open-static')
# Both moving jaws/pads and pinion against every stationary modeled component.
moving={'jaw_left','jaw_right','pad_left','pad_right','pinion'}
for angle in range(5,121,5):
 p=components(angle)
 for a,b in combinations(p,2):
  if not({a,b}&moving):continue
  check(p,a,b,angle)
# Cover lift with fixed components; cables/harness must be released from openings.
p=components()
for dz in (1,5,15,30,60):
 p['cover']=cover().translate((0,0,dz))
 for b in p:
  if b!='cover':check(p,'cover',b,f'lid-lift-{dz}')
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'assembly_clearance_report.json').write_text(json.dumps({'sampled_checks':len(rows),'results':rows,'limits':'Envelope checks only; wires, exact fasteners, real servo/horn and flexible cable movement require physical fit validation.'},indent=2))
print(f'{len(rows)} complete-assembly sampled checks passed')
