"""Ray/triangle checks of optical access to the open grasp area; not a lens calibration."""
import json,numpy as np
from cad.clamp_camera_v2 import parts,pose,OUT
import cadquery as cq

def hits_segment(tri,start,end):
 direction=end-start; e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
 h=np.cross(np.broadcast_to(direction,e2.shape),e2);a=np.sum(e1*h,axis=1)
 keep=np.abs(a)>1e-10
 if not np.any(keep):return False
 e1=e1[keep];e2=e2[keep];h=h[keep];a=a[keep];tri=tri[keep]
 f=1/a;s=start-tri[:,0];u=f*np.sum(s*h,axis=1);q=np.cross(s,e1)
 v=f*np.sum(direction*q,axis=1);t=f*np.sum(e2*q,axis=1)
 return bool(np.any((u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>1e-6)&(t<1-1e-6)))

def main():
 origin=np.array(pose(cq.Workplane('XY').sphere(.01).translate((.6386,6.945,.1))).val().Center().toTuple())
 p=parts();meshes={}
 for n,s in p.items():
  if 'reference' in n or 'cable_ring' in n:continue
  vertices,faces=s.val().tessellate(.3,.2)
  meshes[n]=np.array([v.toTuple() for v in vertices])[np.array(faces)]
 rows=[]
 for x in (-15,0,15):
  for y in (-12,0,12):
   target=np.array([x,y,-96.5]);blocked=[n for n,t in meshes.items() if hits_segment(t,origin,target)]
   assert not blocked,(x,y,blocked)
   rows.append(dict(target_mm=target.tolist(),blocked_by=blocked))
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'sightline_report.json').write_text(json.dumps(dict(lens_origin_mm=origin.tolist(),rays=rows,limits='Nine open-jaw rays only; actual lens FOV, cloth occlusion, closed-jaw visibility and high scan coverage remain unverified.'),indent=2))
 print('Nine open-grasp optical sight lines passed')
if __name__=='__main__':main()
