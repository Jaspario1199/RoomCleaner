from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from cad.clamp_v1 import components,OUT

def main():
 fig=plt.figure(figsize=(14,7))
 for i,(angle,title) in enumerate([(0,'Open — 77.4 mm gap'),(120,'Closed — 2.0 mm gap')],1):
  ax=fig.add_subplot(1,2,i,projection='3d')
  for name,p in components(angle,False).items():
   vertices,faces=p.val().tessellate(.7,.2)
   vs=[v.toTuple() for v in vertices]
   color=('#d5a240' if 'pad' in name else '#447b9b' if 'reference' in name else '#abb9c5')
   if 'battery' in name:color='#de854b'
   if 'esp32' in name:color='#3e976d'
   if 'ring' in name:color='#444444'
   ax.add_collection3d(Poly3DCollection([[vs[j] for j in f] for f in faces],facecolors=color,edgecolors='none',alpha=1))
  ax.set(xlim=(-90,90),ylim=(-80,80),zlim=(-105,60),title=title)
  ax.set_box_aspect((180,160,165));ax.view_init(elev=23,azim=-58);ax.set_axis_off()
 fig.suptitle('RoomCleaner clamp V1 • cover removed to show electronics',fontsize=16)
 fig.tight_layout(rect=(0,0,1,.90));fig.savefig(OUT/'clamp_preview.png',dpi=160)
if __name__=='__main__':main()
