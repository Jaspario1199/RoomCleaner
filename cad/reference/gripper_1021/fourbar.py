import numpy as np, math
O2=np.array([969.997,721.413]); O4=np.array([963.847,685.391]); r2=53.0; r4=50.0
def solve(t2,c,prev=None):
    A=O2+r2*np.array([math.cos(t2),math.sin(t2)])
    d=np.linalg.norm(A-O4)
    if d>r4+c or d<abs(r4-c): return None
    # circle-circle: B on circle(O4,r4) and circle(A,c)
    a=(r4**2-c**2+d**2)/(2*d); h=math.sqrt(max(r4**2-a**2,0))
    u=(A-O4)/d; P=O4+a*u; n=np.array([-u[1],u[0]])
    sols=[P+h*n,P-h*n]
    # choose branch: rocker angle closest to crank angle (parallel branch)
    best=min(sols,key=lambda B: abs(((math.atan2(*(B-O4)[::-1])-t2+math.pi)%(2*math.pi))-math.pi))
    return A,best
for c in [34.0,34.67,35.5,36.54,37.5]:
    rows=[]
    for deg in range(-10,-111,-10):
        r=solve(math.radians(deg),c)
        if r is None: rows.append(f"{deg}:--"); continue
        A,B=r; phi=math.degrees(math.atan2(*(B-A)[::-1])); t4=math.degrees(math.atan2(*(B-O4)[::-1]))
        # transmission angle between coupler and rocker
        v1=(B-A)/np.linalg.norm(B-A); v2=(B-O4)/r4; mu=math.degrees(math.acos(abs(np.dot(v1,v2))))
        rows.append(f"{deg}:phi{phi:6.1f} t4{t4:6.1f} mu{mu:4.0f} Bx{B[0]-951.85:5.1f} By{B[1]:6.1f}")
    print(f"c={c}"); [print("   ",r) for r in rows]
