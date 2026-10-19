"""Removable wall dock, mm. +Y up; wall at Z=-30. Bench prototype."""
from pathlib import Path
import json
import cadquery as cq
from cad.winch_bench import build,box,cyl,ENCODER_FOOT_BOLTS
OUT=Path(__file__).parent/'exports'/'winch_slide_mount'

def make():
    wall=box(160,190,12,z=-30)
    # Three screws on a single stud centreline, outside the docking tongue.
    for y in (-78,0,68):
        wall=wall.cut(cyl(3,14,0,y,-31)).cut(cyl(6.5,3,0,y,-21))
    # Captive channels: 6mm back, 7mm side, 6mm front lip.
    for sign in (-1,1):
        wall=wall.union(box(7,120,15,x=sign*71.5,z=-18))
        wall=wall.union(box(12,120,8,x=sign*69,z=-9))
        gusset=cq.Workplane('XZ').polyline([(sign*75,-18),(sign*80,-18),(sign*75,-3)]).close().extrude(120).translate((0,60,0))
        wall=wall.union(gusset)
    # Bottom stop supports downwards force; tongue slides in from above.
    wall=wall.union(box(140,8,15,y=-64,z=-18))
    # Accessible M3 lock with a captured metal nut, separate from load rails.
    wall=wall.union(box(18,18,14.5,y=84,z=-18))
    wall=wall.cut(cyl(1.7,32,0,84,-31))
    nut=cq.Workplane('XY').polygon(6,6.6).extrude(3.4).translate((0,84,-17))
    wall=wall.cut(nut).cut(box(7,12,3.4,y=90,z=-17))
    tongue=box(135.6,119.6,7.8,z=-17.4)
    # Central spine brings assembled case forward of the rail lips.
    tongue=tongue.union(box(104,119.6,9.6,z=-9.6))
    tongue=tongue.cut(box(20,181,14.4,y=15,z=-17.4))
    # Rebuild the anti-lift bridge AFTER cutting the through-clearance channel.
    tongue=tongue.union(box(36,31,3,y=74.3,z=-3))
    tongue=tongue.union(box(36,14.4,3,y=82.6,z=0))
    tongue=tongue.cut(cyl(1.7,23,0,84,-18))
    station=build()
    base=station['base']
    # The dock replaces the original direct-wall holes; restore the base section.
    for y in (-43,0,60):base=base.union(cyl(5.5,6,0,y,0))
    for x in (-25,25):
        for y in (-48,48):
            base=base.cut(cyl(1.7,8,x,y,-1)).cut(cyl(3.2,3.1,x,y,3))
            tongue=tongue.cut(cyl(1.7,20,x,y,-18.4))
            pocket=cq.Workplane('XY').polygon(6,6.6).extrude(3.4).translate((x,y,-17.4))
            tongue=tongue.cut(pocket)
    # Existing node tray through-bolt nuts/tips must clear the rear adapter.
    for x in (-37,-7):tongue=tongue.cut(cyl(4,4.5,x,61,-4.5))
    # Removable encoder pedestal: M3x16 tips, rear washers and ordinary nuts.
    # Ø8.2 relief breaks exact tangency at the X52 spine edge; Ø8 caused
    # zero-width tessellation edges. Nuts still bear on structural base, not this relief.
    for x,y in ENCODER_FOOT_BOLTS: tongue=tongue.cut(cyl(4.1,6.5,x,y,-6.5))
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
