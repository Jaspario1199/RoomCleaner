"""Independent nominal fit checks; no load or flexible-harness qualification."""
import json,tempfile
from pathlib import Path
import cadquery as cq
from cad.winch_fuse_service import make
from cad.winch_bench import cyl

def main():
 w,a,p,pr,r,h=make(); rows=[]
 def record(name,ok,value=None): rows.append({'check':name,'pass':bool(ok),'measured':value})
 def clear(name,x,y):
  v=sum(s.Volume(1e-7) for s in x.intersect(y).solids().vals());record(name,v<.001,v)
 changed={'cover':p['cover'],'electronics_carrier':pr['electronics_carrier'],'fuse_service_support':pr['fuse_service_support']}
 with tempfile.TemporaryDirectory() as tmp:
  for n,s in changed.items():
   record(n+' valid single solid',s.val().isValid() and len(s.solids().vals())==1,len(s.solids().vals()))
   path=str(Path(tmp)/(n+'.step'));cq.exporters.export(s,path);t=cq.importers.importStep(path)
   dv=abs(s.val().Volume(1e-7)-t.val().Volume(1e-7));record(n+' STEP volume',dv<.001,dv)
   b=s.val().BoundingBox();c=t.val().BoundingBox();err=max(abs(getattr(b,k)-getattr(c,k)) for k in ('xmin','xmax','ymin','ymax','zmin','zmax'));record(n+' STEP bounds',err<1e-5,err)
 allparts={'wall':w,'adapter':a,**p,**pr,**r,**h}
 for n in ('fuse_service_support','fuseholder_reference','lower_lead_provisional','upper_lead_provisional'):
  for k,q in allparts.items():
   if k!=n:clear(n+' static '+k,allparts[n],q)
 for x,y in ((-25.,-15.),(-13.,-18.)):
  # Nut cavity ends Z8.5, locally thickened carrier ends Z11.5.
  probe=cyl(.1,2.98,x+2.1,y,8.51);v=probe.val().Volume(1e-7);inside=pr['electronics_carrier'].intersect(probe).val().Volume(1e-7)
  record('3mm nut roof '+str(x),abs(v-inside)<1e-5,inside/v)
  tool=cyl(2.5,110,x,y,18)
  for k,q in {**p,**pr,**r}.items():
   if k not in ('cover','lower_lead_provisional','upper_lead_provisional'):clear('driver with holder installed and both leads deflected '+str(x)+' '+k,tool,q)
 focus={k:allparts[k] for k in ('fuse_service_support','fuseholder_reference','lower_lead_provisional','upper_lead_provisional')}
 for dz in (.1,.5,1,2,3,5,7,10,25,50,90,125):
  for n,s in focus.items():
   clear('cover lift '+str(dz)+' '+n,p['cover'].translate((0,0,dz)),s)
   for k,q in {**p,**pr,**r}.items():
    if k not in focus and k!='cover':clear('support assembly lift '+str(dz)+' '+n+' '+k,s.translate((0,0,dz)),q)
 gap=121-r['upper_lead_provisional'].val().BoundingBox().zmax;record('roof envelope clearance >=3mm',gap>=3,gap)
 result={'status':'PASS' if all(t['pass'] for t in rows) else 'FAIL','checks':len(rows),'failed':[t for t in rows if not t['pass']],'roof_clearance_mm':gap}
 print(json.dumps(result,indent=2));return result
if __name__=='__main__':
 result=main();raise SystemExit(result['status']!='PASS')
