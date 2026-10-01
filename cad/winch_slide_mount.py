"""Removable wall dock, mm. +Y up; wall at Z=-24. Bench prototype."""
from pathlib import Path
import json
import cadquery as cq
from cad.winch_bench import build,box,cyl
OUT=Path(__file__).parent/'exports'/'winch_slide_mount'

def make():
    wall=box(150,190,6,z=-24)
    # Three screws on a single stud centreline, outside the docking tongue.
    for y in (-78,0,78):
        wall=wall.cut(cyl(2.7,8,0,y,-25)).cut(cyl(5.5,3,0,y,-21))
    # Captive channels: 6mm back, 7mm side, 6mm front lip.
    for sign in (-1,1):
        wall=wall.union(box(7,120,15,x=sign*71.5,z=-18))
        wall=wall.union(box(12,120,6,x=sign*69,z=-9))
    # Bottom stop supports downwards force; tongue slides in from above.
    wall=wall.union(box(140,8,15,y=-64,z=-18))
    # Accessible M3 lock with a captured metal nut, separate from load rails.
    wall=wall.union(box(18,18,14,y=84,z=-18))
    wall=wall.cut(cyl(1.7,20,0,84,-20))
    nut=cq.Workplane('XY').polygon(6,6.6).extrude(3.4).translate((0,84,-17))
    wall=wall.cut(nut).cut(box(7,12,3.4,y=90,z=-17))
    tongue=box(135.6,119.6,6,z=-15.6)
    # Central spine brings assembled case forward of the rail lips.
    tongue=tongue.union(box(104,119.6,9.6,z=-9.6))
    tongue=tongue.union(box(18,31,6,y=74.3,z=-9.6))
    tongue=tongue.cut(box(20,181,12.6,y=15,z=-15.6))
    tongue=tongue.cut(cyl(1.7,18,0,84,-16.6))
    station=build()
    base=station['base']
    for x in (-25,25):
        for y in (-60,60):
            base=base.cut(cyl(1.7,8,x,y,-1)).cut(cyl(3.2,3.1,x,y,3))
            tongue=tongue.cut(cyl(1.7,18,x,y,-17))
            pocket=cq.Workplane('XY').polygon(6,6.6).extrude(3.4).translate((x,y,-15.6))
            tongue=tongue.cut(pocket)
    station['base']=base
    return wall,tongue,station

def volume(p):return sum(s.Volume() for s in p.solids().vals())

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    wall,tongue,station=make()
    report={'checks':[], 'load_rating':'UNQUALIFIED: physical proof test required'}
    for name,p in [('wall_dock',wall),('case_adapter',tongue),('base_slide_version',station['base'])]:
        assert p.val().isValid() and len(p.solids().vals())==1,name
        cq.exporters.export(p,str(OUT/(name+'.step')))
        # Flat backs down on the bed.
        b=p.val().BoundingBox(); printable=p.translate((0,0,-b.zmin))
        cq.exporters.export(printable,str(OUT/(name+'.stl')))
        restored=cq.importers.importStep(str(OUT/(name+'.step')))
        assert abs(volume(restored)-volume(p))<.001
        report['checks'].append(name+' valid, connected, STEP round trip')
    for dy in range(0,191,5):
        assert volume(wall.intersect(tongue.translate((0,dy,0))))<.001,dy
        for name,p in station.items():
            assert volume(wall.intersect(p.translate((0,dy,0))))<.001,(dy,name)
        report['checks'].append(f'slide {dy}mm clear')
    for name,p in station.items():
        assert volume(tongue.intersect(p))<.001,name
    report['checks'].append('adapter clear of all station components')
    assembly=cq.Assembly(name='RoomCleaner_slide_dock')
    assembly.add(wall,name='wall_dock',color=cq.Color(.2,.35,.5))
    assembly.add(tongue,name='case_adapter',color=cq.Color(.9,.55,.2))
    for name,p in station.items():assembly.add(p,name=name)
    assembly.save(str(OUT/'docked_station.step'))
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    print(f"PASS: {len(report['checks'])} checks; exports at {OUT}")
if __name__=='__main__':main()
