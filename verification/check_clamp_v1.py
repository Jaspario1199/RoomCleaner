"""Check sampled rigid clearances; excludes intended pad/jaw interfaces."""
import json
from pathlib import Path
from cad.clamp_v1 import components
pairs=[('pinion','jaw_left'),('pinion','jaw_right'),('jaw_left','rail_left'),('jaw_left','rail_right'),('jaw_left','deck'),('jaw_left','jaw_right'),('pinion','rail_left'),('pinion','rail_right')]
rows=[]
for a in range(0,121,5):
 p=components(a,False)
 for l,r in pairs:
  v=p[l].val().intersect(p[r].val()).Volume()
  rows.append(dict(angle=a,a=l,b=r,intersection_mm3=v))
  assert v<.01,(a,l,r,v)
print(f'{len(rows)} sampled clearance checks passed')
Path('cad/exports/clamp_v1/clearance_report.json').write_text(json.dumps(rows,indent=2))
