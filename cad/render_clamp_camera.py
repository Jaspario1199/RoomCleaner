"""Actual CAD service/enclosed views; purchased parts shown as envelopes."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from cad.clamp_camera_v2 import parts as components,OUT

def main():
 fig=plt.figure(figsize=(15,8))
 for i,(lift,title) in enumerate([(0,'Complete enclosure'),(75,'Lid removed for service')],1):
  ax=fig.add_subplot(1,2,i,projection='3d')
  all_tri=[];all_colors=[]
  for name,part in components().items():
   if 'access_reference' in name:continue
   if name=='cover':part=part.translate((0,0,lift))
   vertices,faces=part.val().tessellate(.8,.2)
   vs=np.array([v.toTuple() for v in vertices]);tri=vs[np.array(faces)]
   color='#acbbc8'
   if 'pad' in name:color='#dfad45'
   if 'servo' in name:color='#404854'
   if 'battery_reference'==name:color='#dc814e'
   if 'camera_oem' in name:color='#3b996c'
   if 'camera_cradle' in name:color='#a670ab'
   if 'camera_keeper' in name:color='#ca9c66'
   if 'ring' in name or 'pin_reference' in name:color='#596570'
   if name=='cover':color='#7097b1'
   from matplotlib.colors import to_rgb
   normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8)
   light=np.array([.2,-.4,.8]);light/=np.linalg.norm(light)
   shade=.6+.4*np.abs(normal@light)
   colors=np.array(to_rgb(color))[None,:]*shade[:,None]
   all_tri.extend(tri);all_colors.extend(colors)
  ax.add_collection3d(Poly3DCollection(all_tri,facecolors=all_colors,edgecolors='none'))
  ax.set(xlim=(-95,95),ylim=(-85,145),zlim=(-105,145),title=title)
  ax.set_box_aspect((190,230,250));ax.view_init(elev=22,azim=58);ax.set_axis_off()
 fig.suptitle('RoomCleaner • camera pod secured with M3 • electronics above clamp',fontsize=15)
 fig.tight_layout(rect=(0,0,1,.94));fig.savefig(OUT/'camera_assembly_preview.png',dpi=160)
if __name__=='__main__':main()

if __name__=='__main__':main()
