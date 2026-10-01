"""Claw electronics packaging prototype; millimetres; frame underside at Z=0.
Board/pack envelopes are provisional: replace with purchased dimensions before
printing. Run python -m cad.claw_electronics. Existing cover/mechanism retained.
"""
from pathlib import Path
import json
import cadquery as cq
from .export_all import placed_components

BOARD_MM = (55.0, 26.0, 13.0)  # unconfirmed board/connector envelope
BATTERY_MM = (55.0, 25.0, 18.0)  # unconfirmed 2S pack envelope
BAY_Y = 31.0
BAY_BOTTOM_Z = 8.5
FLOOR_MM = 2.0
WALL_MM = 1.8
CLEARANCE_MM = 0.6


def bay(width, depth):
    outer_w=width+CLEARANCE_MM+2*WALL_MM
    outer_d=depth+CLEARANCE_MM+2*WALL_MM
    solid=cq.Workplane('XY').box(outer_w,outer_d,5,centered=(True,True,False)).edges('|Z').chamfer(4)
    void=cq.Workplane('XY').box(width+CLEARANCE_MM,depth+CLEARANCE_MM,4,centered=(True,True,False)).translate((0,0,FLOOR_MM))
    solid=solid.cut(void)
    for x in (-14,14):
        solid=solid.cut(cq.Workplane('XY').center(x,0).slot2D(6.5,2.6,90).extrude(6))
    for x in (-20,20):
        for y in (-8,8):
            foot=cq.Workplane('XY').center(x,y).circle(2).extrude(BAY_BOTTOM_Z-5).translate((0,0,5-BAY_BOTTOM_Z))
            solid=solid.union(foot)
    return solid


def components():
    parts=placed_components()
    parts['esp32_bay']=bay(*BOARD_MM[:2]).translate((0,BAY_Y,BAY_BOTTOM_Z))
    parts['battery_bay']=bay(*BATTERY_MM[:2]).translate((0,-BAY_Y,BAY_BOTTOM_Z))
    parts['esp32_envelope']=cq.Workplane('XY').box(*BOARD_MM,centered=(True,True,False)).translate((0,BAY_Y,BAY_BOTTOM_Z+FLOOR_MM))
    parts['battery_envelope']=cq.Workplane('XY').box(*BATTERY_MM,centered=(True,True,False)).translate((0,-BAY_Y,BAY_BOTTOM_Z+FLOOR_MM))
    parts['servo_body_envelope']=cq.Workplane('XY').box(41,20.2,38,centered=(True,True,False)).translate((0,0,5))
    return parts


def main():
    out=Path('cad/exports/claw_electronics');out.mkdir(parents=True,exist_ok=True)
    parts=components(); report={'status':'PACKAGING PROTOTYPE: hardware dimensions unconfirmed','checks':[]}
    names=['esp32_bay','battery_bay','esp32_envelope','battery_envelope','servo_body_envelope']
    for name in names:
        shape=parts[name]
        assert shape.val().isValid() and len(shape.solids().vals())==1
        path=out/f'{name}.step';cq.exporters.export(shape,str(path))
        reread=cq.importers.importStep(str(path))
        assert abs(reread.val().Volume()-shape.val().Volume())<1e-5
        if name.endswith('bay'): cq.exporters.export(shape,str(out/f'{name}.stl'))
        for other_name,other in parts.items():
            if other_name==name: continue
            volume=shape.intersect(other).val().Volume()
            report['checks'].append({'part':name,'other':other_name,'interference_mm3':volume})
            assert volume<1e-5,(name,other_name,volume)
    assembly=cq.Assembly()
    for name,shape in parts.items(): assembly.add(shape,name=name)
    assembly.save(str(out/'claw_electronics_assembly.step'))
    (out/'verification.json').write_text(json.dumps(report,indent=2))
    print('Prototype: valid solids, STEP round-trip and pairwise checks passed.')


if __name__=='__main__': main()
