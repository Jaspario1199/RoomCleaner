import cadquery as cq
import math

def gear(n, module=1.5, width=12, phase=0, reduction=.10, root_radius=.40):
    """20-degree involute flanks with analytic tangent circular root blends.
    These blends are not generated hob trochoids. Angles are in radians internally.
    """
    rp=module*n/2; rb=rp*math.cos(math.radians(20)); ra=rp+module; rr=rp-1.25*module
    rho=root_radius
    inv=lambda r: math.sqrt(max(0,(r/rb)**2-1))-math.acos(min(1,rb/r))
    bh=math.pi/(2*n)-reduction/(2*rp)+inv(rp)
    def point(r,a): return (r*math.cos(a),r*math.sin(a))
    def center_at(r):
        a=-bh+inv(r); u=math.sqrt(max(0,(r/rb)**2-1)); q=math.sqrt(1+u*u)
        p=point(r,a); norm=((math.sin(a)+u*math.cos(a))/q,(-math.cos(a)+u*math.sin(a))/q)
        return p,(p[0]+rho*norm[0],p[1]+rho*norm[1])
    # Tangency on radial extension when fillet lies below the base circle.
    radial=math.sqrt((rr+rho)**2-rho*rho)
    if radial<=rb:
        rt=radial; a=-bh; pt=point(rt,a); cent=(pt[0]+rho*math.sin(a),pt[1]-rho*math.cos(a))
    else:
        lo=rb; hi=ra
        for _ in range(70):
            mid=(lo+hi)/2; pp,cc=center_at(mid)
            if math.hypot(*cc)>rr+rho: hi=mid
            else: lo=mid
        rt=(lo+hi)/2;pt,cent=center_at(rt)
    rq=(cent[0]*rr/(rr+rho),cent[1]*rr/(rr+rho))
    # Midpoint of the minor fillet arc.
    u=((rq[0]-cent[0])/rho+(pt[0]-cent[0])/rho,(rq[1]-cent[1])/rho+(pt[1]-cent[1])/rho)
    mag=math.hypot(*u); fm=(cent[0]+rho*u[0]/mag,cent[1]+rho*u[1]/mag)
    def transform(v,c,mirror=False):
        x,y=v; y=-y if mirror else y
        return cq.Vector(x*math.cos(c)-y*math.sin(c),x*math.sin(c)+y*math.cos(c),0)
    edges=[]; start=max(rt,rb); tip=bh-inv(ra)
    for k in range(n):
        c=2*math.pi*k/n+math.radians(phase)
        tr=lambda v:transform(v,c)
        mr=lambda v:transform(v,c,True)
        edges.append(cq.Edge.makeThreePointArc(tr(rq),tr(fm),tr(pt)))
        if rt<rb-1e-7: edges.append(cq.Edge.makeLine(tr(pt),tr(point(rb,-bh))))
        rs=[start+(ra-start)*j/20 for j in range(21)]
        flank=[point(r,-bh+inv(r)) for r in rs]
        edges.append(cq.Edge.makeSpline([tr(p) for p in flank]))
        edges.append(cq.Edge.makeThreePointArc(tr(point(ra,-tip)),tr((ra,0)),tr(point(ra,tip))))
        edges.append(cq.Edge.makeSpline([mr(p) for p in reversed(flank)]))
        if rt<rb-1e-7: edges.append(cq.Edge.makeLine(mr(point(rb,-bh)),mr(pt)))
        edges.append(cq.Edge.makeThreePointArc(mr(pt),mr(fm),mr(rq)))
        a0=c-math.atan2(rq[1],rq[0]);a1=c+2*math.pi/n+math.atan2(rq[1],rq[0])
        edges.append(cq.Edge.makeThreePointArc(cq.Vector(*point(rr,a0),0),cq.Vector(*point(rr,(a0+a1)/2),0),cq.Vector(*point(rr,a1),0)))
    face=cq.Face.makeFromWires(cq.Wire.assembleEdges(edges))
    solid=cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),(0,0,width))
    assert solid.isValid()
    return cq.Workplane(obj=solid)

if __name__=='__main__':
 for n in [18,36,54]:
  s=gear(n);print(n,s.val().isValid(),len(s.val().Faces()),flush=True)
