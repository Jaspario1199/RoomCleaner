"""CAD-derived upright wall views; no generated concept geometry."""
from cad.winch_slide_mount import make,OUT
from cad.winch_bench import cyl
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def main():
 wall,adapter,p=make();OUT.mkdir(parents=True,exist_ok=True)
 fig=plt.figure(figsize=(13,8),facecolor='white')
 for i,title in enumerate(('Complete station on wall dock','Captive rails and removable adapter'),1):
  ax=fig.add_subplot(1,2,i,projection='3d')
  pieces=[(wall,'#366580')]
  if i==1:
   pieces.extend([(adapter,'#dca14b'),(p['base'],'#4b5867'),(p['cover'],'#cbd2da')])
   for n in ('guide_carrier','homing_collar','homing_stopper','metal_eyelet_reference','outlet_backplate'):
    pieces.append((p[n],'#e4a442' if n in ('homing_collar','homing_stopper') else '#6d8190'))
   pieces.append((cyl(3,3,0,84,3.5),'#333c45'))
  else:pieces.append((adapter.translate((0,135,25)),'#dca14b'))
  for shape,color in pieces:
   vertices,faces=shape.val().tessellate(.5,.15)
   vv=np.array([v.toTuple() for v in vertices])[:,[0,2,1]] # XY wall -> upright XZ view
   tri=vv[np.array(faces)];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
   normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8)
   shade=.65+.35*np.abs(normal@np.array([.3,-.5,.8]))
   ax.add_collection3d(Poly3DCollection(tri,facecolors=np.array(to_rgb(color))[None,:]*shade[:,None],edgecolors='none'))
  ax.set(xlim=(-85,85),ylim=(-35,95),zlim=(-105,235 if i==2 else 105))
  ax.set_box_aspect((170,130,340 if i==2 else 210));ax.view_init(elev=18,azim=65);ax.set_axis_off();ax.set_title(title,pad=15)
 fig.suptitle('Revised removable winch mount • blue wall dock / gold case adapter',fontsize=16)
 fig.tight_layout(rect=(0,0,1,.94));fig.savefig(OUT/'preview.png',dpi=170)
if __name__=='__main__':main()
