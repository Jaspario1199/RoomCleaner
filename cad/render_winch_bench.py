import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgb
from cad.winch_bench import build,bench_parts,OUT

def main():
 fig=plt.figure(figsize=(14,8));p=build()
 for i,title in enumerate(('Print first: manual homing cartridge','Complete winch: cover removed'),1):
  ax=fig.add_subplot(1,2,i,projection='3d');parts=dict(p)
  parts.pop('cover');parts.pop('homing_stopper')
  if i==1:
   parts={k:v for k,v in parts.items() if not any(t in k for t in ('motor','shaft','spool','encoder','base'))}
   parts['bench_fixture']=bench_parts()['cartridge_bench_fixture']
  alltri=[];colors=[]
  for n,s in parts.items():
   v,f=s.val().tessellate(.7,.2);vs=np.array([x.toTuple() for x in v]);tri=vs[np.array(f)]
   c='#adbdcc'
   if 'collar' in n:c='#eba941'
   if 'spool' in n:c='#3e919e'
   if 'motor' in n:c='#343d49'
   if 'switch' in n:c='#477f59'
   if 'encoder' in n:c='#8461a0'
   normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8)
   shade=.6+.4*np.abs(normal@np.array([.2,-.4,.8])/np.linalg.norm([.2,-.4,.8]))
   alltri.extend(tri);colors.extend(np.array(to_rgb(c))[None,:]*shade[:,None])
  ax.add_collection3d(Poly3DCollection(alltri,facecolors=colors,edgecolors='none'))
  if i==1:ax.set(xlim=(-20,60),ylim=(-95,-28),zlim=(0,72));ax.set_box_aspect((80,67,72))
  else:ax.set(xlim=(-60,60),ylim=(-90,80),zlim=(0,82));ax.set_box_aspect((120,170,82))
  ax.view_init(elev=32,azim=-70);ax.set_title(title,pad=16);ax.set_axis_off()
 fig.suptitle('RoomCleaner • revised bench winch • orange annular homing button',fontsize=15)
 fig.tight_layout(rect=(0,0,1,.93));fig.savefig(OUT/'bench_preview.png',dpi=160)
if __name__=='__main__':main()
