"""RoomCleaner universal wall winch v2. Units mm. Bench prototype, not load certified.
Local XY is wall plane, +Y up, +Z into room. Run: python winch_housing.py.
"""
from pathlib import Path
import cadquery as cq
import json
from cad.parts.winch_spool_v2 import make as spool_v2,magnet_cap
OUT=Path(__file__).parent/'exports'/'winch_bench'
W,H,DEPTH=112.,150.,68.
PLATE=6.; WALL=3.; LINE_D=.60
SHAFT_Z=33.; MOTOR_Y=30.; SPOOL_START=4.5; SPOOL_LEN=32.
EYE_X=20.; EYE_Z=43.; EYE_Y=-68.
COLLAR_HOLE=18.6; BEAD_D=24.; STROKE=2.

def box(w,h,d,x=0,y=0,z=0):
    return cq.Workplane('XY').box(w,h,d,centered=(True,True,False)).translate((x,y,z))
def cyl(r,l,x=0,y=0,z=0):
    return cq.Workplane('XY').circle(r).extrude(l).translate((x,y,z))
def along_y(s,x,y,z):
    return s.rotate((0,0,0),(1,0,0),90).translate((x,y,z))
def along_x(s,x,y,z):
    return s.rotate((0,0,0),(0,1,0),90).translate((x,y,z))
def rounded(w,h,d,r=6):
    return box(w,h,d).edges('|Z').fillet(r)
def build():
    base=rounded(W,H,PLATE)
    # Three stud screws on one vertical centerline; accessible with cover removed.
    for y in (-43,0,60):
        base=base.cut(cyl(2.7,PLATE+1,0,y,-.5)).cut(cyl(5.5,3,0,y,3))
    # Motor face at x=-2. Six-mm bracket leaves shaft projection outside it.
    bracket=box(6,52,54,x=1,y=MOTOR_Y,z=PLATE)
    boss=along_x(cyl(11.2,8),-3,MOTOR_Y,SHAFT_Z)
    bracket=bracket.cut(boss)
    for dy in (-15.5,15.5):
        for dz in (-15.5,15.5):
            bracket=bracket.cut(along_x(cyl(1.7,8),-3,MOTOR_Y+dy,SHAFT_Z+dz))
    base=base.union(bracket)
    # Structural tower for stationary switch mounting plate.
    tower=box(20,10,58,x=43,y=-47,z=PLATE)
    for x in (36,48):
        for z in (46,62):
            tower=tower.cut(along_y(cyl(1.4,12),x,-42,z))
    base=base.union(tower)
    for z in (46,62):
        base=base.cut(box(3,8,3,x=42,y=-51,z=z-1.5))
    # Cover fasteners, away from motor and spool.
    for x in (-51.5,51.5):
        for y in (-66,66):
            post=cyl(3,9,x,y,PLATE).cut(cyl(1.4,10,x,y,PLATE))
            base=base.union(post)
    # Outlet cartridge mounts directly to base (cover carries no guide load).
    for x in (0,40):
        tower=box(9,12,40,x=x,y=-52,z=PLATE)
        tower=tower.cut(along_y(cyl(1.7,15),x,-44,32))
        base=base.union(tower)
    for x in (2,38):
        base=base.cut(along_y(cyl(4.3,6),x,-53,EYE_Z))
    cover=rounded(W,H,DEPTH).translate((0,0,PLATE+.4))
    cavity=rounded(W-2*WALL,H-2*WALL,DEPTH-WALL+.5,4).translate((0,0,PLATE))
    cover=cover.cut(cavity)
    for x in (-51.5,51.5):
        for y in (-66,66):
            # Screw heads sit on low shelves, accessed through the roof.
            cover=cover.cut(cyl(4.5,5,x,y,PLATE+DEPTH-4))
            cover=cover.cut(cyl(3.2,9.3,x,y,PLATE))
            foot=cyl(3,3,x,y,15.3).cut(cyl(1.7,4,x,y,15))
            cover=cover.union(foot)
    for x in (-35,-25,-15):
        cover=cover.cut(box(4,28,8,x=x,y=30,z=PLATE+DEPTH-5))
    # Bottom outlet and symmetric rear wiring notches.
    cover=cover.cut(box(52.4,15,76,x=EYE_X,y=-73,z=PLATE))
    for x in (-42,42):
        cover=cover.cut(box(9,12,9,x=x,y=73,z=PLATE))
    # Cartridge plate sits on base towers; fixed eyelet is structural.
    carrier=box(52,6,26,x=EYE_X,y=-61,z=30)
    carrier=carrier.cut(along_y(cyl(4.15,9),EYE_X,-56,EYE_Z))
    for x in (0,40):
        carrier=carrier.cut(along_y(cyl(1.7,9),x,-56,32))
    for x in (2,38):
        carrier=carrier.cut(along_y(cyl(1.4,9),x,-56,EYE_Z))
    carrier=carrier.cut(box(21,7.5,12,x=40,y=-58.25,z=48.25))
    # Button front face -75, back face -71. Moves +Y by 2 mm.
    collar=along_y(cyl(14,4).cut(cyl(COLLAR_HOLE/2,5)),EYE_X,-71,EYE_Z)
    for x in (2,38):
        collar=collar.union(box(16,4,10,x=x,y=-73,z=EYE_Z-5))
        collar=collar.cut(along_y(cyl(2.15,6),x,-70,EYE_Z))
    # Integral fork/stem brings flat pad to the stationary switch roller.
    collar=collar.union(box(4,4,14,x=32,y=-73,z=43))
    collar=collar.union(box(6,3.55,5,x=30,y=-69.225,z=51.5))
    carrier=carrier.cut(box(28,10,13,x=39,y=-59,z=48.25))
    carrier=carrier.cut(box(25,10,2,x=40.5,y=-59,z=46.75))
    # Stationary KW12 cradle: plate, bottom shelf, and zip-tie slots.
    switch_mount=box(28,3,22,x=39,y=-53.5,z=44)
    for x in (36,48):
        for z in (46,62):
            cut=along_y(cq.Workplane('XY').center(x,z).slot2D(7.4,3.4,0).extrude(6),0,-50,0)
            switch_mount=switch_mount.cut(cut)
    switch_mount=switch_mount.union(box(23,7,1.5,x=40,y=-58.25,z=47.25))
    for z in (46,62):
        switch_mount=switch_mount.cut(box(2.5,5,3,x=42,y=-53.5,z=z-1.5))
    switch_mount=switch_mount.cut(box(9.6,5,2.4,x=40,y=-53.5,z=43.9)) # guide tower corner relief
    # Selected Ronstan RF8090-05:15OD,5ID,7.5axial. Conservative
    # smooth cylindrical reference; manufacturer groove/flaring not reproduced.
    eyelet=along_y(cyl(7.5,7.5).cut(cyl(2.5,8)).edges('%Circle').fillet(.6),EYE_X,-64.5,EYE_Z)
    holder=along_y(cyl(11,8),EYE_X,-61,EYE_Z).union(along_y(cyl(9,4),EYE_X,-69,EYE_Z))
    carrier=carrier.union(holder)
    carrier=carrier.cut(along_y(cyl(7.65,14),EYE_X,-58,EYE_Z))
    carrier=carrier.cut(along_y(cyl(5,17),EYE_X,-57,EYE_Z))
    carrier=carrier.cut(box(28.4,2.2,18.4,x=EYE_X,y=-63.5,z=33.8))
    backplate=box(28,2,18,x=EYE_X,y=-63.5,z=34).cut(along_y(cyl(2.75,4),EYE_X,-62,EYE_Z))
    backplate=backplate.cut(box(8,4,4,x=31,y=-63.5,z=52)) # stationary lever sweep clearance
    for x in (9,31):
        backplate=backplate.cut(along_y(cyl(1.7,4),x,-62,EYE_Z))
        carrier=carrier.cut(along_y(cyl(1.4,8),x,-56,EYE_Z))
    carrier=carrier.cut(switch_mount) # preserve stationary cradle clearance
    # Two guide springs return the sliding collar, not the load-bearing eyelet.
    extra={'outlet_backplate':backplate}
    for i,x in enumerate((2,38)):
        rod=along_y(cyl(2,12),x,-64,EYE_Z).union(along_y(cyl(1.5,6),x,-58,EYE_Z))
        head=along_y(cyl(3.5,2),x,-76,EYE_Z)
        sleeve=along_y(cyl(2.9,5).cut(cyl(2.1,6)),x,-64,EYE_Z)
        washer=along_y(cyl(3.5,1).cut(cyl(2.15,1.2)),x,-75,EYE_Z)
        extra[f'guide_bolt_{i}_reference']=rod.union(head)
        extra[f'stop_sleeve_{i}']=sleeve
        extra[f'washer_{i}_reference']=washer
        # Spring solid envelope for packaging; winding represented in preview.
        extra[f'spring_{i}_reference']=along_y(cyl(3.7,7).cut(cyl(3.2,8)),x,-64,EYE_Z)
    # Body orientation:20 along X, 6.5 deep Y,10.5 high Z.
    switch_body=box(20,6.5,10.5,x=42,y=-58.25,z=48.75)
    lever=box(18,.5,3,x=39,y=-63.9,z=52.5)
    roller=cyl(2.25,3,x=29.5,y=-64.5,z=52.5)
    extra['switch_body_reference']=switch_body
    extra['switch_lever_reference']=lever
    extra['switch_roller_reference']=roller
    # Hardware envelopes only; do not print.
    motor=box(38,42.3,42.3,x=-21,y=MOTOR_Y,z=SHAFT_Z-21.15)
    shaft=along_x(cyl(2.5,24).intersect(box(4.5,5,24,x=-.25)),-2,MOTOR_Y,SHAFT_Z) # original spool assumes0.5mm D-flat
    spool=along_x(spool_v2(),SPOOL_START,MOTOR_Y,SHAFT_Z)
    # Flat-faced stopper avoids a sphere entering the collar and hitting eyelet.
    bead_local=cyl(BEAD_D/2,8).edges('%Circle').fillet(1).cut(cyl(.6,9)).cut(cyl(3.5,3,0,0,5))
    bead=along_y(bead_local,EYE_X,-85,EYE_Z)
    parts=dict(base=base,cover=cover,guide_carrier=carrier,homing_collar=collar,switch_mount=switch_mount,metal_eyelet_reference=eyelet,motor_reference=motor,shaft_reference=shaft,spool_reference=spool,homing_stopper=bead)
    parts.update(extra)
    # Grove SKU101020692: Eagle outline40x20, AS5600 on underside10mm
    # off board center. Orient board long dimension vertically, chip at z33.
    encoder=box(4,28,60,x=47.175,y=MOTOR_Y,z=PLATE)
    encoder=encoder.cut(box(6,24,14,x=47.175,y=MOTOR_Y,z=47))
    for y in (20,40):
        for z in (25,62):encoder=encoder.cut(along_x(cyl(1.5,6),44.175,y,z))
    # Exact Eagle mounting holes: two at Y±10,Z53, one at Y0,Z23.
    for yy,zz in ((20,53),(40,53),(30,23)):
        ear=along_x(cyl(3,3.4),44.775,yy,zz)
        encoder=encoder.union(ear).cut(along_x(cyl(.85,6),43.5,yy,zz))
    base=base.union(encoder)
    # PCB bottom faces spool; top connector clearance sits above sensor.
    parts['encoder_board_reference']=box(1.6,24,41,x=43.975,y=MOTOR_Y,z=22.5)
    for yy,zz in ((20,53),(40,53),(30,23)):
        parts['encoder_board_reference']=parts['encoder_board_reference'].cut(along_x(cyl(1.1,3),42.5,yy,zz))
    parts['encoder_chip_reference']=box(2,5,5,x=42.175,y=MOTOR_Y,z=30.5)
    parts['encoder_lead_space_reference']=box(8,14,10,x=48.775,y=MOTOR_Y,z=48)
    # Removable XIAO tray. Foam + nonconductive ties, USB faces -X.
    tray=box(26,22,4,x=-22,y=61,z=6).cut(box(24,20,3,x=-22,y=61,z=8))
    for x in (-37,-7):
        tray=tray.union(box(6,6,2,x=x,y=61,z=6)).cut(cyl(1.7,4,x,61,5))
        base=base.cut(cyl(1.7,8,x,61,-1))
    for x in (-29,-15):tray=tray.cut(box(2,16,5,x=x,y=61,z=5))
    tray=tray.cut(box(4,10,4,x=-34,y=61,z=8))
    parts['encoder_node_holder']=tray
    parts['encoder_node_reference']=box(21,17.8,6,x=-22,y=61,z=10)
    parts['encoder_usb_space_reference']=box(15,10,8,x=-40,y=61,z=10)
    cover=cover.cut(box(8,14,18,x=-55,y=61,z=6))
    parts['cover']=cover
    parts['base']=base
    # Cup pilots over the outer flange and is retained by three M2 screws.
    cap=magnet_cap()
    parts['encoder_magnet_cup']=along_x(cap,SPOOL_START+29,MOTOR_Y,SHAFT_Z)
    # Printable spool exported separately; reference uses identical V2 geometry.
    parts['encoder_magnet_reference']=along_x(cyl(3.175,3.175),SPOOL_START+32,MOTOR_Y,SHAFT_Z)
    # K&J D42DIA6.35x3.175: chip face41.175, magnet face39.675, gap1.5.
    return parts

def bench_parts():
    p=build()
    fixture=p['base'].intersect(box(75,45,68,x=21.5,y=-55,z=0))
    for x,y in ((-8,-68),(-8,-38),(28,-38)):
        fixture=fixture.cut(cyl(2.25,8,x,y,-1))
    coupon=box(40,24,6)
    for x,r in ((-12,1.4),(-4,1.7),(4,2.15),(14,4.15)):
        coupon=coupon.cut(cyl(r,8,x,0,-1))
    return {'cartridge_bench_fixture':fixture,'fit_coupon':coupon,'eyelet_fit_dummy':p['metal_eyelet_reference']}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name,part in bench_parts().items():
        assert len(part.solids().vals())==1 and part.val().isValid(),name
        cq.exporters.export(part,str(OUT/(name+'.stl')))
        cq.exporters.export(part,str(OUT/(name+'.step')))
    parts=build(); assembly=cq.Assembly(name='RoomCleaner_Winch_bench')
    colors={'base':(.18,.23,.3),'cover':(.8,.83,.87),'homing_collar':(.95,.55,.12),'metal_eyelet_reference':(.65,.7,.75),'motor_reference':(.2,.2,.2),'spool_reference':(.2,.55,.65)}
    report={}
    for name,p in parts.items():
        assert p.val().isValid(),name
        if not name.endswith('_reference'): assert len(p.solids().vals())==1,name
        assembly.add(p,name=name,color=cq.Color(*colors.get(name,(.45,.5,.55))))
        cq.exporters.export(p,str(OUT/(name+'.step')))
        restored=cq.importers.importStep(str(OUT/(name+'.step')))
        assert abs(sum(q.Volume() for q in restored.solids().vals())-sum(q.Volume() for q in p.solids().vals()))<.001,name
        if not name.endswith('_reference'): cq.exporters.export(p,str(OUT/(name+'.stl')))
        b=p.val().BoundingBox(); report[name]={'valid':True,'solids':len(p.solids().vals()),'bbox_mm':[b.xlen,b.ylen,b.zlen]}
    assembly.save(str(OUT/'winch_assembly.step'))
    checks={}
    for a,b in [('base','motor_reference'),('base','spool_reference'),('cover','motor_reference'),('cover','spool_reference'),('cover','base'),('switch_mount','switch_body_reference'),('base','switch_body_reference'),('switch_mount','cover'),('guide_carrier','switch_body_reference'),('cover','switch_mount'),('guide_carrier','metal_eyelet_reference'),('base','guide_carrier'),('base','guide_bolt_0_reference'),('base','guide_bolt_1_reference')]:
        volume=parts[a].intersect(parts[b]).val().Volume() if parts[a].intersect(parts[b]).solids().size() else 0
        checks[a+' vs '+b]=volume
        assert volume<.01,(a,b,volume)
    # Sample entire stroke against fixed structure and guide hardware.
    stroke_results=[]
    for travel in (0,.5,1,1.5,2):
        moving=parts['homing_collar'].translate((0,travel,0))
        collision={}
        for name in ('base','cover','guide_carrier','metal_eyelet_reference','switch_mount','switch_body_reference','stop_sleeve_0','stop_sleeve_1','outlet_backplate'):
            common=moving.intersect(parts[name]); v=sum(q.Volume() for q in common.solids().vals())
            collision[name]=round(v,6); assert v<.01,(travel,name,v)
        stroke_results.append({'travel_mm':travel,'fixed_intersection_mm3':collision})
    # Re-export a fully depressed named assembly; roller displacement schematic.
    pressed=cq.Assembly(name='RoomCleaner_Winch_bench_pressed')
    for name,p in parts.items():
        if name=='homing_collar': p=p.translate((0,2,0))
        elif name=='homing_stopper': p=p.translate((0,12,0))
        elif name in ('switch_roller_reference','switch_lever_reference'): p=p.translate((0,1.3,0))
        elif name.startswith('spring_'):
            x=2 if '_0_' in name else 38
            p=along_y(cyl(3.7,5).cut(cyl(3.2,6)),x,-64,EYE_Z)
        pressed.add(p,name=name)
    pressed.save(str(OUT/'winch_pressed_assembly.step'))
    import math
    radial_envelope=5+.3+2*math.tan(math.radians(55))
    assert radial_envelope<COLLAR_HOLE/2
    report['cable_angle_check']={'cone_half_angle_deg':55,'radial_envelope_mm':radial_envelope,'bore_radius_mm':COLLAR_HOLE/2,'clearance_mm':COLLAR_HOLE/2-radial_envelope,'assumption':'ray from5mm retainer opening radius;front plane2mm beyond lip'}
    dynamic=[]
    for travel in (0,.5,1,1.5,2):
        roller=parts['switch_roller_reference'].translate((0,max(0,travel-.7),0))
        common=roller.intersect(parts['switch_body_reference'])
        volume=sum(q.Volume() for q in common.solids().vals()); assert volume<.01
        dynamic.append({'travel_mm':travel,'roller_body_intersection_mm3':volume})
    stopper=parts['homing_stopper'].translate((0,12,0))
    for name in ('homing_collar','metal_eyelet_reference','guide_carrier','outlet_backplate'):
        fixed=parts[name].translate((0,2,0)) if name=='homing_collar' else parts[name]
        common=stopper.intersect(fixed); volume=sum(q.Volume() for q in common.solids().vals())
        assert volume<.01,(name,volume)
    report['stopper_pressed_clearance']='No solid intersections at flat-face contact'
    report['roller_clearance_checks']=dynamic
    report['stroke_checks']=stroke_results
    # Roller front=-67.45, pad rest=-67.45: adjust lever reference for .7 gap.
    report['actuation']={'initial_gap_mm':.7,'nominal_roller_displacement_at_full_stroke_mm':1.3,'stroke_mm':2,'actual_switch_travel_requires_measurement':True}
    report['interference_mm3']=checks
    (OUT/'geometry_checks.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(checks,indent=2))
if __name__=='__main__': main()
