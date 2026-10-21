import cadquery as cq, math, numpy as np
from fourbar import solve
L=lambda f: cq.importers.importStep(f).val()
C=L("10_gripper_v6r_compound_36T_24T_norelief_NAUO10.step"); F=L("11_gripper_v6r_follower_NAUO11.step")
H1=L("03_Gripper_gear_housing_NAUO3.step"); H2=L("07_Gripper_gear_housing_Part2_NAUO7.step")
AR=L("08_Claw_arm_extension3_NAUO8.step"); AL=L("09_Claw_arm_extension3_NAUO9.step")
P=L("04_Simple_18T_Pinionvlast_NAUO4.step")
O2=cq.Vector(969.997,721.413,0); O4=cq.Vector(963.847,685.391,0)
O2L=cq.Vector(933.697,721.413,0); O4L=cq.Vector(939.847,685.391,0)
def rot(s,c,deg): return s.rotate(cq.Vector(c.x,c.y,0),cq.Vector(c.x,c.y,1),deg)
t20=math.degrees(math.atan2(679.566-721.413,1002.522-969.997)); t40=math.degrees(math.atan2(645.91-685.391,994.19-963.847))
t40L=math.degrees(math.atan2(642.95-685.391,913.41-939.847))
FL0=rot(F,O2L,-6.0)   # valid mesh, mirror of compound
c=34.67
def iv(a,b):
    try: return a.intersect(b).Volume()
    except Exception as e: return -1
for th in [-5,-10,-15,-20,-25,-30,-35,-40,-50,-60,-65,-70,-75]:
    A,B=solve(math.radians(th),c); t4=math.degrees(math.atan2(B[1]-685.391,B[0]-963.847))
    Cr=rot(C,O2,th-t20); Ar=rot(AR,O4,t4-t40)
    # left side mirror: follower crank angle = -180-th ; follower rotates opposite to compound by same amount
    Fr=rot(FL0,O2L,-(th-t20)); t4L=-180-t4; Al=rot(AL,O4L,t4L-t40L)
    res={"C-H1":iv(Cr,H1),"C-H2":iv(Cr,H2),"F-H1":iv(Fr,H1),"F-H2":iv(Fr,H2),"AR-H":iv(Ar,H1)+iv(Ar,H2),"AL-H":iv(Al,H1)+iv(Al,H2),
         "AR-C":iv(Ar,Cr),"AL-F":iv(Al,Fr),"AR-AL":iv(Ar,Al),"C-F":iv(Cr,Fr),"AR-F":iv(Ar,Fr),"AL-C":iv(Al,Cr)}
    print(th, " ".join(f"{k}:{v:.1f}" for k,v in res.items() if abs(v)>0.05) or "clear")
