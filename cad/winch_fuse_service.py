"""Provisional fuse service variant; all dimensions mm, +Z into room.
Run python -m cad.winch_fuse_service. Original sources/exports are unchanged.
"""
from pathlib import Path
import json, math
import cadquery as cq
from cad.winch_local_electronics import make as original_make
from cad.winch_bench import box,cyl
from cad.winch_slide_mount import volume
OUT=Path(__file__).parent/'exports'/'winch_fuse_service'
FX,FY,FZ=-17.,-5.,40.
BODY_D,BODY_L=15.24,55.63
WIRE_ENVELOPE_OD=4.4 # PROVISIONAL clearance envelope, not physical insulation OD
BEND_R=15. # PROVISIONAL centerline bend radius, not material qualification
EXIT=5.

def lead(upper):
    z=FZ+BODY_L if upper else FZ
    sign=1 if upper else -1
    a=(FX,FY,z); b=(FX,FY,z+sign*EXIT)
    mid=(FX,FY-BEND_R+BEND_R/math.sqrt(2),b[2]+sign*BEND_R/math.sqrt(2))
    c=(FX,FY-BEND_R,b[2]+sign*BEND_R)
    d=(FX,-34.,c[2])
    edges=[cq.Edge.makeLine(cq.Vector(*a),cq.Vector(*b)),cq.Edge.makeThreePointArc(cq.Vector(*b),cq.Vector(*mid),cq.Vector(*c)),cq.Edge.makeLine(cq.Vector(*c),cq.Vector(*d))]
    path=cq.Wire.assembleEdges(edges)
    return cq.Workplane('XY',origin=a).circle(WIRE_ENVELOPE_OD/2).sweep(path),c[2]

def make():
    assert WIRE_ENVELOPE_OD>=4.4 and BEND_R>=10 and EXIT>=5
    wall,adapter,p,printed,refs,hw=original_make()
    carrier=printed['electronics_carrier']
    # Remove only the obsolete locating ring, leaving the carrier floor intact.
    carrier=carrier.cut(cyl(10,11,FX,FY,9))
    support=box(24,14,4.5,x=-15,y=-13,z=11.5)
    support=support.union(box(4,20,76,x=-4,y=-5,z=12))
    # Two accessible M3 attachment bolts into removable carrier, no base holes.
    for x,y in ((-25.,-15.),(-13.,-18.)):
        support=support.cut(cyl(1.7,9,x,y,8))
        carrier=carrier.union(cyl(3.5,2.5,x,y,9))
        carrier=carrier.cut(cyl(1.4,3,x,y,6))
        hw['fuse_support_head_'+str(x)]=cyl(3,2,x,y,16)
        # Full clearance bore rather than implicit thread-volume exemptions.
        carrier=carrier.cut(cyl(1.7,6,x,y,6))
        pocket=cq.Workplane('XY').polygon(6,6.6).extrude(2.5).translate((x,y,6))
        carrier=carrier.cut(pocket)
        nut=cq.Workplane('XY').polygon(6,6.4).extrude(2.4).translate((x,y,6)).cut(cyl(1.7,3,x,y,6))
        hw['fuse_support_nut_'+str(x)]=nut
        hw['fuse_support_shank_'+str(x)]=cyl(1.5,10,x,y,6)
    # Open-backed concave saddle; independent bands retain body.
    for z in (45.,76.):
        saddle=cyl(10,6,FX,FY,z).cut(cyl(7.82,7,FX,FY,z))
        saddle=saddle.intersect(box(20,24,8,x=-7,y=FY,z=z-1))
        support=support.union(saddle).union(box(4,10,6,x=-6.5,y=FY,z=z))
        # Accessible tie tunnels across the spine, outside cylinder envelope.
        support=support.cut(box(8,3,1.8,x=-4,y=FY,z=z+2))
    refs['fuseholder_reference']=cyl(BODY_D/2,BODY_L,FX,FY,FZ)
    # Bottom seat carries axial contact without obstructing the lower lead.
    seat=cyl(10,3,FX,FY,37).cut(cyl(3,4,FX,FY,36.5))
    support=support.union(seat).union(box(7,12,3,x=-6,y=FY,z=37))
    for upper in (False,True):
        key='upper' if upper else 'lower'
        wire,z=lead(upper);refs[key+'_lead_provisional']=wire
        # Independent strain-relief tie fixture beyond the completed bend.
        # Fixture is a bridge to spine, with a wire channel and two tie slots.
        fixture=box(20,10,6,x=-11,y=-27,z=z-3)
        fixture=fixture.cut(cq.Workplane('XZ',origin=(FX,-21,z)).circle(2.5).extrude(12))
        fixture=fixture.cut(box(5,12,4,x=FX,y=-27,z=z))
        for x in (-21.,-13.):fixture=fixture.cut(box(1.5,4,8,x=x,y=-27,z=z-4))
        # Connect strain-relief foot to spine (top support extends locally).
        support=support.union(box(4,25,6,x=-4,y=-17.5,z=z-3)).union(fixture)
    # Top brace to carry the upper strain relief without using the cover.
    support=support.union(box(4,10,32,x=-4,y=-5,z=85))
    # Foot relief clears the existing regulator boss and carrier bolt head.
    support=support.cut(cyl(3.5,8,-8,-20,9))
    support=support.cut(cyl(3.5,12,-23,-20.7,9))
    support=support.cut(carrier)
    kb=printed['d24v10f5_keeper_1'].val().BoundingBox()
    support=support.cut(box(kb.xlen+.8,kb.ylen+.8,kb.zmax+.4,x=(kb.xmin+kb.xmax)/2,y=(kb.ymin+kb.ymax)/2,z=0))
    printed['electronics_carrier']=carrier
    printed['fuse_service_support']=support
    # Bulge is part of replacement non-load-bearing cover. Clear opening all
    # the way through old roof before adding 3mm walls and new roof.
    cover=p['cover'].cut(box(30,47,12,x=-16,y=-15.5,z=68))
    bulge=box(36,53,54,x=-16,y=-15.5,z=70)
    bulge=bulge.cut(box(30,47,53,x=-16,y=-15.5,z=68))
    p['cover']=cover.union(bulge)
    return wall,adapter,p,printed,refs,hw

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    wall,adapter,p,printed,refs,hw=make()
    allparts={'wall_dock':wall,'case_adapter':adapter,**p,**printed,**refs,**hw}
    rows=[]
    def check(label,s,q):
        v=volume(s.intersect(q));rows.append(dict(check=label,intersection_mm3=v,pass_=v<.001))
    focus=['fuse_service_support','fuseholder_reference','lower_lead_provisional','upper_lead_provisional']
    for n in focus:
        for other,q in allparts.items():
            if other==n:continue
            check(n+' vs '+other,allparts[n],q)
    for dz in (0,1,5,15,30,60,100,120):
        for n in focus:check('cover lift '+str(dz)+' vs '+n,p['cover'].translate((0,0,dz)),allparts[n])
    # Lead ends and body are disconnected from supply before removing support.
    for dz in (.5,1,2,5,15,30,60,100):
        for n in focus:
            for other,q in p.items():
                if other!='cover':check('support lift '+str(dz)+' '+n+' vs '+other,allparts[n].translate((0,0,dz)),q)
    for x,y in ((-25.,-15.),(-13.,-18.)):
        tool=cyl(2.5,110,x,y,18)
        # Remove holder and release lead ties before the attachment screws.
        for other,q in {**p,**printed}.items():
            if other!='cover':check('support screw tool '+str(x)+' '+other,tool,q)
    for n,s in allparts.items():
        rows.append(dict(check=n+' valid',pass_=s.val().isValid()))
        if n in printed or n=='cover':
            rows.append(dict(check=n+' single solid',measured=len(s.solids().vals()),pass_=len(s.solids().vals())==1))
    export={'cover_fuse_service':p['cover'],**printed}
    assembly=cq.Assembly(name='Provisional_fuse_service')
    for n,s in allparts.items():assembly.add(s,name=n)
    assembly.save(str(OUT/'fuse_service_assembly.step'))
    for n,s in export.items():
        cq.exporters.export(s,str(OUT/(n+'.step')))
        cq.exporters.export(s,str(OUT/(n+'.stl')))
        restored=cq.importers.importStep(str(OUT/(n+'.step')))
        error=abs(volume(restored)-volume(s))
        rows.append(dict(check=n+' STEP volume',error_mm3=error,pass_=error<.001))
    report=dict(status='PASS' if all(r['pass_'] for r in rows) else 'FAIL',parameters=dict(wire_clearance_envelope_OD_mm=WIRE_ENVELOPE_OD,bend_centerline_radius_provisional_mm=BEND_R,straight_exit_mm=EXIT,body_base_Z_mm=FZ,body_top_Z_mm=FZ+BODY_L,roof_inner_Z_mm=121),results=rows)
    (OUT/'geometry_audit.json').write_text(json.dumps(report,indent=2))
    print(report['status'],len(rows),'checks')
    for row in rows:
        if not row['pass_']:print(row)
    return report
if __name__=='__main__':main()
