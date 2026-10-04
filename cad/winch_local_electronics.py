"""Experimental self-contained 12V winch electronics; existing bench CAD unchanged.

Manufacturer dimensions/provenance and electrical gates are documented in
docs/LOCAL_STATION_HARDWARE_20261004.md. Not a hardware-qualified print release.
Run python -m cad.winch_local_electronics to export and audit nominal geometry.
"""
from pathlib import Path
import json
import cadquery as cq
from cad.winch_slide_mount import make as dock_make,volume
from cad.winch_bench import box,cyl,along_x
from verification.check_winch_slide_mount import nut

OUT=Path(__file__).parent/'exports'/'winch_local_electronics'
TRAY_BOLTS=((-47.,-44.),(-10.,-44.),(-49.,1.),(-8.,-20.))
BOARD_SPECS={
 'drv8825':dict(x=-36.,y=-9.,w=15.2,h=20.3,t=1.57,total=4.06),
 'd24v10f5':dict(x=-23.,y=-33.,w=12.7,h=17.8,t=1.0,total=3.5),
}

def panel_cutout():
    """Molex43020-0200 SDA-43020: C4.2,D7.90, central7.11+key1.59."""
    s=box(4.2,7.11,6)
    s=s.union(box(7.90,4.06,6))
    return s.union(box(1.98,1.59,6,y=7.11/2+1.59/2))

def make():
    wall,adapter,p=dock_make(); printed={};refs={};hw={};rows=[]
    tray=box(44,56,3,x=-29,y=-20,z=6)
    base=p['base'];cover=p['cover']
    for x,y in TRAY_BOLTS:
        tray=tray.cut(cyl(1.7,5,x,y,5))
        base=base.cut(cyl(1.7,8,x,y,-1))
        adapter=adapter.cut(cyl(4,7.5,x,y,-7.5))
        hw[f'tray_head_{x}_{y}']=cyl(3,2,x,y,9)
        hw[f'tray_shank_{x}_{y}']=cyl(1.5,16,x,y,-7)
        hw[f'tray_washer_{x}_{y}']=cyl(3.5,.5,x,y,-.5).cut(cyl(1.6,.6,x,y,-.55))
        hw[f'tray_nut_{x}_{y}']=nut(x,y,-2.9)
    for name,b in BOARD_SPECS.items():
        x,y,w,h=b['x'],b['y'],b['w'],b['h']
        # Only bare board end edges are seated, not underside chips/ground pad.
        # Lead exit via both long edges remains open. Direct-soldered harness;
        # do not install unmodeled vertical female-header stacks.
        for sign in (-1,1):
            yy=y+sign*(h/2-.25)
            tray=tray.union(box(w,.5,3,x=x,y=yy,z=9))
        refs[name+'_board_reference']=box(w,h,b['t'],x=x,y=y,z=12)
        refs[name+'_top_reference']=box(w-2,h-2,b['total']-b['t'],x=x,y=y,z=12+b['t'])
        refs[name+'_underside_reference']=box(w-2,h-2,1.8,x=x,y=y,z=10.2)
        # Each independent screw keeper presses only the outermost0.3mm end
        # margin; actual populated revision and bare-edge clearance need checking.
        for sign in (-1,1):
            bolt_y=y+sign*(h/2+3.4)
            tray=tray.union(cyl(3,7,x,bolt_y,9)).cut(cyl(1.4,12,x,bolt_y,6.5))
            keeper=box(w+2,3.6,2,x=x,y=y+sign*(h/2+1.5),z=12+b['t']+.3)
            keeper=keeper.union(box(6,5,2,x=x,y=bolt_y,z=12+b['t']+.3))
            keeper=keeper.cut(cyl(1.7,4,x,bolt_y,12+b['t']))
            # Boss top is cut to keeper underside so the screw seats on boss.
            tray=tray.cut(box(7,7,8,x=x,y=bolt_y,z=12+b['t']+.3))
            printed[f'{name}_keeper_{sign}']=keeper
            seat=12+b['t']+.3+2
            hw[f'{name}_keeper_head_{sign}']=cyl(3,2,x,bolt_y,seat)
            hw[f'{name}_keeper_shank_{sign}']=cyl(1.5,8,x,bolt_y,seat-8)
    # Panasonic EEUFR1H101,100uF50V,Ø8×11.5; no clamp across vent.
    # 0.5mm sleeve and a removable perimeter keeper retain body, leaving vent open.
    cap_x,cap_y=-44.,-32.
    holder=cyl(6,8,cap_x,cap_y,9).cut(cyl(4.5,9,cap_x,cap_y,9))
    tray=tray.union(holder)
    refs['vmot_capacitor_reference']=cyl(4,11.5,cap_x,cap_y,12)
    cap_keeper=box(12,22,2,x=-43,y=-33,z=24).cut(cyl(3,3,cap_x,cap_y,23.5))
    for i,(xx,yy) in enumerate(((-44.,-25.5),(-42.,-40.))):
        tray=tray.union(cyl(2,15,xx,yy,9)).cut(cyl(.85,10,xx,yy,15.5))
        cap_keeper=cap_keeper.cut(cyl(1.1,4,xx,yy,23))
        hw[f'cap_keeper_head_{i}']=cyl(2,2,xx,yy,26)
        hw[f'cap_keeper_shank_{i}']=cyl(1,10,xx,yy,16)
    for xx,yy in TRAY_BOLTS: cap_keeper=cap_keeper.cut(cyl(3,4,xx,yy,23))
    printed['capacitor_perimeter_keeper']=cap_keeper
    # Lead drain and two independent tie slots in the foot.
    for xx in (cap_x-1.75,cap_x+1.75):tray=tray.cut(cyl(.8,7,xx,cap_y,5))
    for yy in (cap_y-6.8,cap_y+6.8):tray=tray.cut(box(5,1.4,5,x=cap_x,y=yy,z=5))
    # Littelfuse01550100Z: conservative cylinderØ15.24×55.63, vertical.
    # Ring and two ties restrain lower body; remove ties/lift out to service fuse.
    fx,fy=-17.,-5.
    tray=tray.union(cyl(9.8,10,fx,fy,9).cut(cyl(7.82,11,fx,fy,9)))
    refs['fuseholder_reference']=cyl(7.62,55.63,fx,fy,11)
    # Bottom wire port; insulation/grommet and top lead bend are physical gates.
    tray=tray.cut(cyl(2.2,7,fx,fy,5))
    for yy in (fy-11,fy+11):tray=tray.cut(box(5,1.4,5,x=fx,y=yy,z=5))
    printed['electronics_carrier']=tray
    # Replaceable1.5mm panel, on existing left cover wall. Larger relief behind
    # thin panel permits manufacturer snap ears to latch over only1.5mm.
    panel=along_x(box(24,32,1.5),-57.5,-18,43)
    # along_x reverses localX into-Z; panel remains Z31..55,Y−34..−2.
    panel=panel.cut(along_x(panel_cutout(),-59,-18,43))
    cover=cover.cut(box(6,20,18,x=-55,y=-18,z=34))
    for yy in (-31.,-5.):
        passage=along_x(cyl(1.7,14),-60,yy,43)
        panel=panel.cut(passage);cover=cover.cut(passage)
        hw[f'panel_head_{yy}']=along_x(cyl(3,2),-59.5,yy,43)
        hw[f'panel_shank_{yy}']=along_x(cyl(1.5,10),-57.5,yy,43)
        hw[f'panel_nut_{yy}']=along_x(nut(0,0,0),-53,yy,43)
    printed['microfit_input_panel']=panel
    refs['microfit_panel_plug_reference']=box(16.89,6.85,3.86,x=-49.055,y=-18,z=43-1.93)
    # Actual mate extends24.77mm combined per OEM drawing; conservative external
    # servicing keepout. Removable feed cable remains separate from moving cover.
    refs['microfit_external_mate_space_reference']=box(25,12,12,x=-70,y=-18,z=37)
    p['base']=base;p['cover']=cover
    return wall,adapter,p,printed,refs,hw

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    wall,adapter,p,printed,refs,hw=make();rows=[]
    fixed={'wall_dock':wall,'case_adapter':adapter,**p}
    for n,s in printed.items():
        assert s.val().isValid() and len(s.solids().vals())==1,n
        for other,q in fixed.items():
            v=volume(s.intersect(q));assert v<.001,(n,other,v)
            rows.append(dict(check=n+' vs '+other,volume_mm3=v))
    for n,s in refs.items():
        for other,q in {**fixed,**printed}.items():
            v=volume(s.intersect(q));assert v<.001,(n,other,v)
            rows.append(dict(check=n+' vs '+other,volume_mm3=v))
    for n,s in hw.items():
        for other,q in {**fixed,**printed,**refs}.items():
            v=volume(s.intersect(q))
            allowed=(n.endswith(('shank_-1','shank_1')) or n.startswith('cap_keeper_shank')) and other=='electronics_carrier'
            assert v<.001 or allowed,(n,other,v)
            rows.append(dict(check=n+' vs '+other,volume_mm3=v,intentional_thread=allowed))
    # Cover service and tray service are distinct: unplug panel harness/mate,
    # remove cover, then remove tray through-bolts before lifting carrier.
    for dz in (1,5,15,30,60,80):
        moving=p['cover'].translate((0,0,dz))
        for n,s in {**printed,**refs}.items():
            # External mating cable must be unplugged before cover removal.
            if n.startswith('microfit_'):continue
            v=volume(moving.intersect(s));assert v<.001,(dz,n,v)
            rows.append(dict(check='cover lift '+str(dz)+' '+n,volume_mm3=v))
    for dz in (0,1,5,10,20,40,80):
        for n,s in {**printed,**refs}.items():
            if n.startswith('microfit_'):continue
            for other,q in p.items():
                if other=='cover':continue
                v=volume(s.translate((0,0,dz)).intersect(q));assert v<.001,(dz,n,other,v)
                rows.append(dict(check='tray lift '+str(dz)+' '+n+' '+other,volume_mm3=v))
    # Accessible four tray bolt drivers after the cover comes off.
    for x,y in TRAY_BOLTS:
        tool=cyl(2.5,80,x,y,11)
        for n,s in {**p,**printed,**refs}.items():
            if n=='cover' or n.startswith('microfit_'):continue
            v=volume(tool.intersect(s));assert v<.001,('tray driver',x,y,n,v)
            rows.append(dict(check=f'tray driver{x}/{y} '+n,volume_mm3=v))
    export={'base_local_station':p['base'],'cover_local_station':p['cover'],'adapter_local_station':adapter,**printed}
    assembly=cq.Assembly(name='Experimental_local_winch_station')
    for n,s in {**fixed,**printed,**refs,**hw}.items():assembly.add(s,name=n)
    assembly.save(str(OUT/'local_station_assembly.step'))
    for n,s in export.items():
        cq.exporters.export(s,str(OUT/(n+'.step')))
        b=s.val().BoundingBox();cq.exporters.export(s.translate((0,0,-b.zmin)),str(OUT/(n+'.stl')))
    (OUT/'geometry_audit.json').write_text(json.dumps(dict(checks=len(rows),results=rows,
      limits='Experimental nominal component envelopes. Real populated board edges, connectors/ears, leads, wire bend, thermal performance, electrical isolation and fuse selection unqualified.'),indent=2))
    print(len(rows),'local station geometry checks passed')

if __name__=='__main__':main()
