import cadquery as cq, math, sys, numpy as np
import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cad', 'reference', 'gripper_1021', 'parts')); sys.path.insert(0, '..')
from fourbar import solve
L=lambda f: cq.importers.importStep(f).val()
C=L("10_gripper_v6r_compound_36T_24T_norelief_NAUO10.step"); F=L("11_gripper_v6r_follower_NAUO11.step")
H1=L("03_Gripper_gear_housing_NAUO3.step"); H2=L("07_Gripper_gear_housing_Part2_NAUO7.step")
AR=L("08_Claw_arm_extension3_NAUO8.step"); AL=L("09_Claw_arm_extension3_NAUO9.step"); P=L("04_Simple_18T_Pinionvlast_NAUO4.step")
HR=L("/home/user/RoomCleaner/exports/step/gripper1021_hand_right.step"); HL=L("/home/user/RoomCleaner/exports/step/gripper1021_hand_left.step")
CX=951.8475
O2=(969.997,721.413); O4=(963.847,685.391); O2L=(933.697,721.413); O4L=(939.847,685.391)
def rot(s,c,deg): return s.rotate(cq.Vector(c[0],c[1],0),cq.Vector(c[0],c[1],1),deg)
def ang(p,o): return math.degrees(math.atan2(p[1]-o[1],p[0]-o[0]))
t20=ang((1002.522,679.566),O2); t40=ang((994.531,645.912),O4); t40L=ang((909.17,645.91),O4L)
# left arm tip hole from its STEP: find the D3.5 hole nearest the tip
def hole_near(s,pt):
    best=None
    for f in s.Faces():
        if f.geomType()!="CYLINDER": continue
        c=f._geomAdaptor().Cylinder(); p=c.Axis().Location()
        if abs(2*c.Radius()-3.5)>0.05: continue
        d=math.hypot(p.X()-pt[0],p.Y()-pt[1])
        if best is None or d<best[0]: best=(d,(p.X(),p.Y()))
    return best[1]
tipL=hole_near(AL,(913.4,642.9)); t40L=ang(tipL,O4L); print("left arm tip hole",tipL)
c=34.67
Af,Bf=solve(math.radians(-52.1),c)   # file pose (what the hand STEPs are placed at)
phif=ang(Bf,Af)
def place_right(th):
    A,B=solve(math.radians(th),c); d=ang(B,A)-phif
    s=HR.rotate(cq.Vector(Af[0],Af[1],0),cq.Vector(Af[0],Af[1],1),d).translate(cq.Vector(A[0]-Af[0],A[1]-Af[1],0))
    return s,A,B
def mirror_pt(p): return (2*CX-p[0],p[1])
def place_left(th):
    A,B=solve(math.radians(th),c); Am,Bm=mirror_pt(A),mirror_pt(B); Afm=mirror_pt(Af)
    d=-(ang(B,A)-phif)
    s=HL.rotate(cq.Vector(Afm[0],Afm[1],0),cq.Vector(Afm[0],Afm[1],1),d).translate(cq.Vector(Am[0]-Afm[0],Am[1]-Afm[1],0))
    return s
FL0=rot(F,O2L,-6.0)
def iv(a,b):
    v=a.intersect(b).Volume(); return v
print("theta | worst overlaps (mm3) for hands vs parts")
for th in [-5,-10,-20,-30,-40,-50,-52.1,-60,-62]:
    A,B=solve(math.radians(th),c); t4=ang(B,O4)
    Cr=rot(C,O2,th-t20); Ar=rot(AR,O4,t4-t40); Fr=rot(FL0,O2L,-(th-t20)); Al=rot(AL,O4L,(-180-t4)-t40L)
    hr,_,_=place_right(th); hl=place_left(th)
    res={}
    for hn,h in (("R",hr),("L",hl)):
        for pn,p in (("comp",Cr),("foll",Fr),("armR",Ar),("armL",Al),("H1",H1),("H2",H2),("pin",P)):
            v=iv(h,p)
            if v>0.01: res[f"{hn}-{pn}"]=round(v,3)
    v=iv(hr,hl)
    if v>0.01: res["R-L"]=round(v,3)
    # check pins: hand hole centres vs crank pin / arm tip after motion
    print(f"{th:6.1f} | {res if res else 'clear'}")
