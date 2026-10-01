"""Parallel-jaw RoomCleaner prototype. All lengths mm, plate bottom Z=0.
Servo output axis is (0,0), pointing down. Jaw travel = r*servo_angle.
Canonical geometry, BOM interfaces and pose exports for the assembly prototype.
"""
from pathlib import Path
import math,json
from functools import lru_cache
import cadquery as cq

OUT=Path('cad/exports/clamp_v1')
MODULE=1.5; N=24; PRESSURE=math.radians(20); R=MODULE*N/2
PITCH=math.pi*MODULE; BACKLASH=.20
OPEN_ANGLE=20; CLOSED_ANGLE=140
TRAVEL=R*math.radians(CLOSED_ANGLE-OPEN_ANGLE)
JAW_X=45.7; TRACK_Y=R+1.25*MODULE+5
GEAR_BOTTOM=-15.; GEAR_T=7.; PAD_BOTTOM=-96.5
CABLE_X=69.; CABLE_Y=64.; CABLE_PLANE=21.5
REACH=(CABLE_PLANE-PAD_BOTTOM)/1000
BOARD_CLEAR=(68.,36.,20.)  # roomy strap mounting; actual ELEGOO board unmeasured
BATTERY_CLEAR=(78.,39.,18.) # OVONIC listing:71+/-5 x35+/-2 x12+/-2, plus clearances


def box(x,y,z,center=(0,0,0)):
    return cq.Workplane('XY').box(x,y,z,centered=(True,True,False)).translate(center)


def hole_z(shape,x,y,d,z0,length):
    return shape.cut(cq.Workplane('XY').center(x,y).circle(d/2).extrude(length).translate((0,0,z0)))


def hole_y(shape,x,z,d,y0,length):
    cut=cq.Workplane('XZ').center(x,z).circle(d/2).extrude(length).translate((0,y0+length,0))
    return shape.cut(cut)


def involute(a): return math.tan(a)-a


@lru_cache(maxsize=1)
def pinion():
    base=R*math.cos(PRESSURE); root=R-1.25*MODULE; tip=R+MODULE
    half=math.pi/(2*N)-BACKLASH/(2*R); invp=involute(PRESSURE)
    pts=[]
    for i in range(N):
        center=2*math.pi*i/N
        flank0=half+invp
        for rad,angle in [(root,-flank0)]+[(rad,-(half+invp-involute(math.acos(base/rad)))) for rad in [base+(tip-base)*k/8 for k in range(9)]]+[(rad,half+invp-involute(math.acos(base/rad))) for rad in [tip-(tip-base)*k/8 for k in range(9)]]+[(root,flank0)]:
            pts.append((rad*math.cos(center+angle),rad*math.sin(center+angle)))
        # Root arc in the space before the next tooth.
        end=2*math.pi*(i+1)/N-flank0
        for k in range(1,4):
            a=center+flank0+(end-(center+flank0))*k/4
            pts.append((root*math.cos(a),root*math.sin(a)))
    gear=cq.Workplane('XY').polyline(pts).close().extrude(GEAR_T).translate((0,0,GEAR_BOTTOM))
    gear=hole_z(gear,0,0,6.5,GEAR_BOTTOM-1,GEAR_T+2)
    # Drill supplied >=20 mm round plastic servo horn using this three-hole template.
    for a in (0,120,240):
        gear=hole_z(gear,7*math.cos(math.radians(a)),7*math.sin(math.radians(a)),2.3,GEAR_BOTTOM-1,GEAR_T+2)
    return gear


@lru_cache(maxsize=1)
def rack_jaw():
    # Upper (+Y) rack at open pose; positive X travel closes left jaw.
    root=R+1.25*MODULE
    shape=box(116,10,GEAR_T,(-10,root+5,GEAR_BOTTOM))
    tooth_half_pitch=(PITCH/2-BACKLASH)/2
    for k in range(-14,10):
        x=(k+.5)*PITCH
        tip_half=tooth_half_pitch-MODULE*math.tan(PRESSURE)
        root_half=tooth_half_pitch+1.25*MODULE*math.tan(PRESSURE)
        tooth=cq.Workplane('XY').polyline([(x-root_half,root+.05),(x-tip_half,R-MODULE),(x+tip_half,R-MODULE),(x+root_half,root+.05)]).close().extrude(GEAR_T).translate((0,0,GEAR_BOTTOM))
        shape=shape.union(tooth)
    neck=box(8,4,9,(-JAW_X,TRACK_Y,-23))
    crossbar=box(8,50,5,(-JAW_X,0,-25))
    jaw=box(4,44,70,(-JAW_X,0,-95))
    # Lightweight window leaves continuous side rails and a pad mounting face.
    jaw=jaw.cut(box(8,24,32,(-JAW_X,0,-57)))
    shape=shape.union(neck).union(crossbar).union(jaw)
    # TPU pad uses 4 M3 screws through the jaw; nuts remain on the outer face.
    for y in (-14,14):
        for z in (-88,-68):
            cut=cq.Workplane('YZ').center(y,z).circle(1.7).extrude(12,both=True).translate((-JAW_X,0,0))
            shape=shape.cut(cut)
    return shape


@lru_cache(maxsize=1)
def pad():
    # Inward face is a rounded 5 mm compliant block; leading lip reaches ground.
    shape=box(5,40,36,(-JAW_X+4.5,0,PAD_BOTTOM))
    shape=shape.edges('|X').fillet(.7)
    for y in (-14,14):
        for z in (-88,-68):
            cut=cq.Workplane('YZ').center(y,z).circle(1.7).extrude(12,both=True).translate((-JAW_X+4.5,0,0))
            shape=shape.cut(cut)
            recess=cq.Workplane('YZ').center(y,z).circle(3.2).extrude(3).translate((-JAW_X+4.4,0,0))
            shape=shape.cut(recess)
    return shape


@lru_cache(maxsize=1)
def rail():
    shape=box(120,16,10.3,(0,TRACK_Y,-18))
    shape=shape.cut(box(122,10.6,12,(0,TRACK_Y,-15.3)))
    shape=shape.cut(box(122,6.4,14,(0,TRACK_Y,-20))) # neck clearance slot
    shape=shape.cut(cq.Workplane('XY').circle(20.5).extrude(20).translate((0,0,-20)))
    for x in (-53,53):
        shape=shape.union(box(12,27,3.1,(x,TRACK_Y,-7.8)))
        tab=box(12,13,18,(x,35,-18))
        shape=shape.union(tab)
        shape=hole_z(shape,x,35,3.4,-19,21)
    shape=shape.cut(box(122,10.6,7.6,(0,TRACK_Y,-15.3)))
    shape=shape.cut(box(122,6.4,14,(0,TRACK_Y,-20)))
    shape=shape.cut(box(122,12,4.7,(0,16,-20))) # remove disconnected inner floor
    shape=shape.cut(box(122,8,7.6,(0,16,-15.3))) # teeth need an open inner side
    return shape


@lru_cache(maxsize=1)
def deck():
    shape=box(160,150,4).edges('|Z').fillet(10)
    # Open underside around drive, retaining peripheral load paths and mounting bands.
    shape=shape.cut(box(105,62,6,(0,0,-1)))
    bridge=box(73,30,4,(-10.5,0,0))
    bridge=bridge.cut(box(43,22,6,(-10.5,0,-1)))
    shape=shape.union(bridge)
    for x in (-45,45):
        shape=shape.union(box(10,104,4,(x,0,0)))
    for x in (-53,53):
        for y in (-35,35): shape=hole_z(shape,x,y,3.4,-1,6)
    # Servo ear slots let body move to align the actual shaft with pinion axis.
    for x in (-34.5,13.5):
        for y in (-5,5):
            slot=cq.Workplane('XY').center(x,y).slot2D(5,3.4).extrude(6).translate((0,0,-1))
            shape=shape.cut(slot)
    for cy in (38,-36):
        for x in (-20,20): shape=shape.cut(box(3,12,6,(x,cy,-1)))
    for rx in (-48,46):
        for y in (-12,12): shape=hole_z(shape,rx,y,3.4,-1,6)
    # Corner metal-ring clevises, M3 pin axis along Y.
    for x in (-CABLE_X,CABLE_X):
        for y in (-CABLE_Y,CABLE_Y):
            for dy in (-6,6):
                ear=box(14,3,15,(x,y+dy,4))
                shape=shape.union(ear)
            shape=hole_y(shape,x,13,3.4,y-9,18)
    for x,y in ((69,0),(-69,0),(0,65),(0,-65)):
        shape=hole_z(shape,x,y,4.0,-1,6) # insert pilots; verify actual insert OD
    return shape


@lru_cache(maxsize=8)
def tray(w,d,x,y):
    shape=box(w+4,d+4,6,(x,y,4))
    shape=shape.cut(box(w,d,8,(x,y,6)))
    for sx in (-20,20):
        shape=shape.cut(box(3,12,8,(x+sx,y,3)))
    # Feet/rim attach through deck to straps; no compression on cell pouch.
    return shape


@lru_cache(maxsize=1)
def cover():
    shape=box(142,130,50,(0,0,4)).edges('|Z').chamfer(24)
    void=box(138,126,48,(0,0,4)).edges('|Z').chamfer(24)
    shape=shape.cut(void)
    for x,y in ((69,0),(-69,0),(0,65),(0,-65)):
        tab=box(8,8,3,(x,y,4))
        shape=shape.union(tab)
        shape=hole_z(shape,x,y,3.4,3,5)
    # USB / battery connector access; not an assumed connector location.
    shape=shape.cut(box(32,10,18,(0,65,14)))
    shape=shape.cut(box(32,10,18,(0,-65,14)))
    # Vent slots on side walls, away from cable clevises.
    for y in (-18,-9,0,9,18):
        shape=shape.cut(box(150,3,8,(0,y,35)))
    return shape


@lru_cache(maxsize=1)
def regulator_mount():
    shape=box(29,29,3,(46,0,4))
    for x,y in ((46-6.731,-8.001),(46+6.731,8.001)):
        shape=shape.union(cq.Workplane('XY').center(x,y).circle(2.5).extrude(5).translate((0,0,7)))
        shape=hole_z(shape,x,y,1.7,6,7)
    for y in (-12,12):shape=hole_z(shape,46,y,3.4,3,6)
    # Adafruit3886 MPU6050,26x17.8, foam retained with nonconductive ties.
    for y in (-10,10):shape=shape.union(box(2,2,23,(59,y,7)))
    shelf=box(28,24,2,(46,0,28))
    for x in (35,57):shelf=shelf.cut(box(2,16,4,(x,0,27)))
    return shape.union(shelf)


@lru_cache(maxsize=1)
def logic_mount():
    shape=box(30,28,3,(-48,0,4))
    for y in (-12,12):shape=hole_z(shape,-48,y,3.4,3,6)
    # Foam and two cable ties retain an unmeasured MP1584 module.
    for x in (-58,-45):shape=shape.cut(box(2,16,5,(x,0,3)))
    shape=shape.cut(box(8.6,14.6,4,(-34.5,0,3))) # actual servo ear clearance
    return shape.union(fuse_mount())


@lru_cache(maxsize=1)
def fuse_mount():
    # Shelf above logic buck, with outer support clear of its module envelope.
    shape=box(35,24,2,(-49,0,22))
    shape=shape.union(box(3,24,18,(-63,0,4)))
    shape=shape.union(box(35,2,4,(-49,-11,24)))
    shape=shape.union(box(35,2,4,(-49,11,24)))
    for x in (-59,-37):shape=shape.cut(box(2,18,4,(x,0,21)))
    return shape


@lru_cache(maxsize=1)
def servo_envelope():
    shape=box(40.7,19.7,37,(-10.5,0,4))
    for x in (-34.5,13.5):
        shape=shape.union(box(8,14,3,(x,0,4)))
        for y in (-5,5):shape=hole_z(shape,x,y,3.4,3,5)
    # Provisional output projection. Actual horn stack remains a measured interface.
    shape=shape.union(cq.Workplane('XY').circle(3).extrude(10).translate((0,0,-6)))
    return shape


def components(angle=0,with_cover=True):
    travel=R*math.radians(angle)
    left=rack_jaw().translate((travel,0,0));right=rack_jaw().rotate((0,0,0),(0,0,1),180).translate((-travel,0,0))
    parts={'deck':deck(),'rail_left':rail(),'rail_right':rail().rotate((0,0,0),(0,0,1),180),
           'jaw_left':left,'jaw_right':right,'pad_left':pad().translate((travel,0,0)),
           'pad_right':pad().rotate((0,0,0),(0,0,1),180).translate((-travel,0,0)),
           'pinion':pinion().rotate((0,0,0),(0,0,1),-angle),
           'esp32_tray':tray(*BOARD_CLEAR[:2],0,38),'battery_tray':tray(*BATTERY_CLEAR[:2],0,-36),
           'regulator_mount':regulator_mount(),'logic_mount':logic_mount(),
           'fuse_reference':box(33,18,14,(-48,0,24)),
           'logic_reference':box(24,20,8,(-48,0,8)),
           'horn_reference':cq.Workplane('XY').circle(10).circle(3.25).extrude(2).translate((0,0,-8)),
           'servo_reference':servo_envelope(),
           'esp32_reference':box(60,30,17,(0,38,10)),
           'board_foam_reference':box(60,30,4,(0,38,6)),
           'battery_reference':box(76,37,14,(0,-36,8)),
           'battery_foam_reference':box(76,37,2,(0,-36,6)),
           'regulator_reference':box(17.8,20.3,8.8,(46,0,12)),
           'tilt_sensor_reference':box(26,17.8,4.6,(46,0,31))}
    if with_cover:parts['cover']=cover()
    for x in (-CABLE_X,CABLE_X):
        for y in (-CABLE_Y,CABLE_Y):
            # Welded ring OD12/ID8, wire2, bearing against M3 clevis pin.
            ring=cq.Workplane('XZ').center(x,15.5).circle(6).circle(4).extrude(2).translate((0,y+1,0))
            parts[f'cable_ring_{x:g}_{y:g}']=ring
            parts[f'clevis_pin_reference_{x:g}_{y:g}']=cq.Workplane('XZ').center(x,13).circle(1.5).extrude(20).translate((0,y+10,0))
    return parts


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parts=components();report={'prototype':True,'pitch_radius_mm':R,'jaw_travel_mm':TRAVEL,
        'open_gap_mm':2*(JAW_X-7),'closed_gap_mm':2*(JAW_X-7-TRAVEL),'reach_m':REACH,'checks':[]}
    for name,part in parts.items():
        solids=part.solids().vals()
        assert len(solids)==1 and part.val().isValid(),(name,len(solids))
        path=OUT/f'{name}.step';cq.exporters.export(part,str(path))
        imported=cq.importers.importStep(str(path));assert abs(imported.val().Volume()-part.val().Volume())<1e-4
        if not ('reference' in name or 'cable_ring' in name):cq.exporters.export(part,str(OUT/f'{name}.stl'))
    for angle,label in ((0,'open'),(120,'closed')):
        assembly=cq.Assembly()
        for name,shape in components(angle).items():assembly.add(shape,name=name)
        assembly.save(str(OUT/f'clamp_{label}.step'))
    # Analytic jaw gaps and pad positions throughout commanded motion.
    for angle in range(0,121,5):
        gap=2*(JAW_X-7-R*math.radians(angle));assert gap>0
        report['checks'].append({'rotation_deg':angle,'pad_gap_mm':gap,'pad_bottom_z_mm':PAD_BOTTOM})
    (OUT/'geometry_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='checks'}))

if __name__=='__main__':main()
