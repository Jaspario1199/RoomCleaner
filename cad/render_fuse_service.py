"""CAD-derived fuse service prototype inspection views."""
from cad.winch_fuse_service import make,OUT
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def draw(ax,shape,color):
    vertices,faces=shape.val().tessellate(.4,.15)
    vv=np.array([v.toTuple() for v in vertices])[:,[0,2,1]]
    tri=vv[np.array(faces)];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-8)
    shade=.65+.3*np.abs(norm@np.array([.3,-.5,.8]))
    ax.add_collection3d(Poly3DCollection(tri,facecolors=np.array(to_rgb(color))[None,:]*shade[:,None],edgecolors='none'))

def main():
    wall,adapter,p,printed,refs,hw=make();OUT.mkdir(parents=True,exist_ok=True)
    fig=plt.figure(figsize=(15,8),facecolor='white')
    for i,title in enumerate(('Revised enclosure on slide-in dock','Fuse support and finite wire clearances'),1):
        ax=fig.add_subplot(1,2,i,projection='3d')
        if i==1:
            pieces=[(wall,'#366580'),(adapter,'#dca14b'),(p['base'],'#556579'),(p['cover'],'#cbd2da')]
            pieces.extend((p[n],'#dca14b')for n in ('guide_carrier','homing_collar','homing_stopper','outlet_backplate'))
            ax.set(xlim=(-85,85),ylim=(-35,135),zlim=(-105,105));ax.set_box_aspect((170,170,210))
        else:
            pieces=[(printed['electronics_carrier'],'#abb8c6'),(printed['fuse_service_support'],'#2b8b97')]
            pieces.extend((s,'#e8a02b' if 'wire' in n or 'lead' in n else '#596b75')for n,s in refs.items())
            pieces.extend((s,'#718b68')for n,s in printed.items()if n not in ('electronics_carrier','fuse_service_support','microfit_input_panel'))
            ax.set(xlim=(-57,5),ylim=(0,127),zlim=(-55,20));ax.set_box_aspect((62,127,75))
        for shape,color in pieces:draw(ax,shape,color)
        ax.view_init(elev=24,azim=57);ax.set_axis_off();ax.set_title(title,fontsize=13)
    fig.suptitle('Housing fit prototype — unpowered\nTeal: removable fuse support | amber: provisional wire clearance envelopes',fontsize=15)
    fig.tight_layout(rect=(0,0,1,.9));fig.savefig(OUT/'preview.png',dpi=160)
if __name__=='__main__':main()
