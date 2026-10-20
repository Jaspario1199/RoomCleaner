#!/usr/bin/python3
"""Read-only measurement of solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP.
Run:  /usr/bin/python3 verification/gripper_v6_scripts/gripper_v6_measure.py
Prints: per-solid bbox/volume/mass, gear axes + tooth counts + thickness, centre distances,
        mesh-phase overlap sweeps, static interference matrix (>0.5 mm^3).
Writes nothing. ~2-3 minutes.
"""
import math, os, sys
import cadquery as cq
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.XCAFApp import XCAFApp_Application
from OCP.TopLoc import TopLoc_Location

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = os.path.join(HERE, '..', '..', 'solidworks', 'gripper_v6_2026-10-20', 'LaundryGripperAssem1.STEP')

def load(path=STEP):
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString('x'))
    app.NewDocument(TCollection_ExtendedString('MDTV-XCAF'), doc)
    r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(path); r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    def name(l):
        n = TDataStd_Name()
        return n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else '?'
    out = []
    def walk(l, loc):
        if st.IsAssembly_s(l):
            comps = TDF_LabelSequence(); st.GetComponents_s(l, comps)
            for i in range(1, comps.Length() + 1):
                c = comps.Value(i); ref = TDF_Label(); st.GetReferredShape_s(c, ref)
                walk(ref, loc.Multiplied(st.GetLocation_s(c)))
        else:
            out.append((name(l), cq.Shape.cast(st.GetShape_s(l).Moved(loc))))
    seq = TDF_LabelSequence(); st.GetFreeShapes(seq)
    for i in range(1, seq.Length() + 1): walk(seq.Value(i), TopLoc_Location())
    return out

parts = load()
names = [p[0] for p in parts]; S = [p[1] for p in parts]
print('instances', len(S))
for i, (n, s) in enumerate(parts):
    bb = s.BoundingBox(); dens = 2.70 if 'aluminum' in n else 1.27
    print('%2d %-44s valid=%s solids=%d V=%9.1f mm3  m=%6.1f g  size %.2f x %.2f x %.2f  x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]' %
          (i, n, s.isValid(), len(s.Solids()), s.Volume(), s.Volume() / 1000 * dens, bb.xlen, bb.ylen, bb.zlen,
           bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
idx = {n: i for i, n in enumerate(names)}
P = S[idx['Simple_18T_Pinionvlast']]; C = S[idx['06_compound_54T_24T']]; F = S[idx['24T_Follower']]
Ap, Ac, Af = (961.8475, 761.3905), (969.8475, 707.9864), (933.8475, 707.9864)   # from cylinder faces (see report)
print('CD pinion-compound %.4f (nominal 54)   compound-follower %.4f (nominal 36)' % (math.dist(Ap, Ac), math.dist(Ac, Af)))

def tooth_count(s, A, z0, z1, rp):
    rg = cq.Workplane('XY').workplane(offset=z0).center(*A).circle(rp + .02).circle(rp - .02).extrude(z1 - z0).val()
    return len(s.intersect(rg).Solids()), s.intersect(rg).Volume() / rg.Volume() * 2 * math.pi * rp
for nm, s, A, z0, z1, z in (('pinion 18T', P, Ap, 1081.5, 1095.5, 18), ('54T', C, Ac, 1081.5, 1095.5, 54),
                            ('24T compound (upper half, clear of arm)', C, Ac, 1107.5, 1115.5, 24),
                            ('24T follower', F, Af, 1107.5, 1115.5, 24)):
    n, w = tooth_count(s, A, z0, z1, 1.5 * z / 2)
    print('%-40s teeth %d  tooth+space per pitch circle; tooth thickness at pitch = %.3f mm (ideal %.3f)' % (nm, n, w / z, math.pi * 1.5 / 2))

def rot(s, A, deg): return s.rotate(cq.Vector(A[0], A[1], 0), cq.Vector(A[0], A[1], 1), deg)
vol = lambda a, b: a.intersect(b).Volume()
print('as-built overlap pinion/compound %.2f mm3, compound/follower %.2f mm3' % (vol(P, C), vol(C, F)))
print('pinion phase sweep (deg: mm3):', [(d, round(vol(rot(P, Ap, d), C), 2)) for d in (-1.6, -1.3, -1.0, -0.85, -0.5, -0.4, 0, 0.5)])
print('follower phase sweep (deg: mm3):', [(d, round(vol(C, rot(F, Af, d)), 2)) for d in (0.5, 0.9, 1.0, 1.35, 1.6, 1.7, 2.0)])
print('--- static interference (> 0.5 mm3) ---')
for i in range(len(S)):
    for j in range(i + 1, len(S)):
        a, b = S[i].BoundingBox(), S[j].BoundingBox()
        if a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin or b.ymax < a.ymin or a.zmax < b.zmin or b.zmax < a.zmin: continue
        v = S[i].intersect(S[j]).Volume()
        if v > 0.5: print('  %s <-> %s : %.2f mm3' % (names[i], names[j], v))
print('done')
