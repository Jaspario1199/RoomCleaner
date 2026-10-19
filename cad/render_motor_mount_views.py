"""Assembled and grouped exploded views from the reviewed fuse-service CAD."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import proj3d
from cad.winch_fuse_service import make
from cad.render_fuse_service import draw
OUT=Path(__file__).parent/'exports/motor_mount_views'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    wall,adapter,p,printed,refs,hw=make()
    groups={'dock':[(wall,'#365f7b')], 'adapter':[(adapter,'#d9a14c')], 'base':[(p['base'],'#64788b')], 'cover':[(p['cover'],'#c1ced8')], 'drive':[], 'encoder':[], 'homing':[], 'electronics':[]}
    for n,s in p.items():
        if n in ('base','cover') or 'space_reference' in n:continue
        if n in ('motor_reference','shaft_reference','spool_reference'):
            g='drive';c='#303f4b' if n=='motor_reference' else '#329aac' if n=='spool_reference' else '#a0a9af'
        elif n.startswith('encoder'):
            g='encoder';c='#487a66' if 'reference' in n else '#9380b1'
        else:
            g='homing';c='#de9f34' if 'collar' in n or 'stopper' in n else '#788fa0'
        groups[g].append((s,c))
    for n,s in printed.items():groups['cover' if n=='microfit_input_panel' else 'electronics'].append((s,'#268793' if n=='fuse_service_support' else '#8ba79b'))
    for n,s in refs.items():
        if 'space_reference' in n:continue
        groups['cover' if 'microfit' in n else 'electronics'].append((s,'#dca333' if 'lead' in n else '#354d43'))
    for s in hw.values():groups['electronics'].append((s,'#9ca5ab'))
    offsets={'dock':(-370,0,0),'adapter':(-180,0,20),'base':(10,0,45),'drive':(160,150,90),'encoder':(290,150,90),'homing':(230,-100,110),'electronics':(20,-160,105),'cover':(470,0,60)}
    labels={'dock':'1  Wall dock','adapter':'2  Slide-in adapter','base':'3  Structural case base','drive':'4  Motor + spool','encoder':'5  Encoder + magnet mounts','homing':'6  Bead / collar / home switch','electronics':'7  Electronics tray + fuse support','cover':'8  Removable cover'}
    for exploded in (False,True):
        fig=plt.figure(figsize=(12,10) if exploded else (10,10),facecolor='#f6f8fa')
        ax=fig.add_subplot(111,projection='3d',computed_zorder=True);ax.set_facecolor('#f6f8fa')
        for g,items in groups.items():
            delta=offsets[g] if exploded else (0,0,0)
            for s,c in items:draw(ax,s.translate(delta),c)
        if exploded:
            ax.set(xlim=(-460,550),ylim=(-50,270),zlim=(-270,265));ax.set_box_aspect((1010,320,535),zoom=1.15);ax.view_init(elev=20,azim=78)
        else:
            ax.set(xlim=(-95,95),ylim=(-40,140),zlim=(-110,110));ax.set_box_aspect((190,180,220));ax.view_init(elev=22,azim=58)
        ax.set_proj_type('ortho');ax.set_axis_off()
        title='Motor mount | exploded subassemblies' if exploded else 'Motor mount | assembled'
        fig.suptitle(title,fontsize=21,fontweight='bold',x=.06,ha='left',y=.965,color='#233647')
        fig.text(.06,.915,'Current fuse-service housing revision • CAD geometry, dimensions in mm',fontsize=12,color='#596b7a')
        fig.text(.06,.035,'Unpowered fit prototype. Purchased components shown as nominal CAD envelopes.',fontsize=11,color='#596b7a')
        if exploded:
            legend='1  Wall dock     2  Adapter     3  Case base     4  Motor + spool\n5  Encoder     6  Homing assembly     7  Electronics + fuse support     8  Cover'
            fig.text(.06,.08,legend,fontsize=10,color='#233647',linespacing=1.8)
            for g,items in groups.items():
                # Label numbered groups above their own bounds in the same view.
                pts=[]
                for s,c in items:
                    b=s.translate(offsets[g]).val().BoundingBox();pts.extend([(b.xmin,b.zmin,b.ymin),(b.xmax,b.zmax,b.ymax)])
                a=np.array(pts);v=(a.min(0)+a.max(0))/2;v[2]=a[:,2].max()+14
                ax.text(*v,labels[g].split()[0],fontsize=15,fontweight='bold',color='#233647',ha='center',bbox=dict(boxstyle='circle,pad=.25',fc='white',ec='#bac6d0'))
        fig.subplots_adjust(left=0,right=1,bottom=.13 if exploded else .065,top=.9)
        fig.savefig(OUT/('exploded.png' if exploded else 'assembled.png'),dpi=190,facecolor=fig.get_facecolor());plt.close(fig)
if __name__=='__main__':main()
