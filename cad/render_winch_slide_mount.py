from cad.winch_slide_mount import make,OUT
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def main():
 w,t,p=make();fig=plt.figure(figsize=(12,7))
 for i,title in enumerate(('Docked station','Adapter lifted for removal'),1):
  ax=fig.add_subplot(1,2,i,projection='3d')
  pieces=[(w,'#386b8d'),(t.translate((0,140 if i==2 else 0,0)),'#eda645')]
  if i==1:pieces.append((p['cover'],'#cbd3dc'))
  for s,c in pieces:
   v,f=s.val().tessellate(.8,.2);vv=np.array([q.toTuple() for q in v]);ax.add_collection3d(Poly3DCollection(vv[np.array(f)],facecolor=c,edgecolor='#555555',linewidth=.08))
  ax.set(xlim=(-80,80),ylim=(-100,230 if i==2 else 100),zlim=(-30,80));ax.set_box_aspect((160,330 if i==2 else 200,110));ax.view_init(elev=26,azim=-65);ax.set_title(title);ax.set_axis_off()
 fig.tight_layout();fig.savefig(OUT/'preview.png',dpi=160)
if __name__=='__main__':main()
