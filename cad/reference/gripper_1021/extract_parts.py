import sys
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRepTools import BRepTools
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
import cadquery as cq
path=sys.argv[1]
doc=TDocStd_Document(TCollection_ExtendedString("doc"))
r=STEPCAFControl_Reader(); r.SetNameMode(True)
assert r.ReadFile(path)==1
r.Transfer(doc)
st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
def name(l):
    a=TDataStd_Name()
    if l.FindAttribute(TDataStd_Name.GetID_s(),a): return a.Get().ToExtString()
    return "?"
out=[]
def walk(label, loc, depth):
    comps=TDF_LabelSequence()
    ref=TDF_Label()
    if st.IsReference_s(label):
        st.GetReferredShape_s(label, ref)
        lloc=st.GetLocation_s(label)
        walk2(ref, loc.Multiplied(lloc), depth, name(label))
def walk2(label, loc, depth, iname):
    if st.IsAssembly_s(label):
        comps=TDF_LabelSequence(); st.GetComponents_s(label, comps)
        print("  "*depth+f"[asm] {name(label)} ({iname})")
        for i in range(1, comps.Length()+1):
            walk(comps.Value(i), loc, depth+1)
    else:
        shp=st.GetShape_s(label).Moved(loc)
        b=Bnd_Box(); BRepBndLib.AddOptimal_s(shp,b,False,False)
        x0,y0,z0,x1,y1,z1=b.Get()
        g=GProp_GProps(); BRepGProp.VolumeProperties_s(shp,g)
        c=g.CentreOfMass()
        n=name(label)
        print("  "*depth+f"{n} | inst {iname} | bbox x[{x0:.2f},{x1:.2f}] y[{y0:.2f},{y1:.2f}] z[{z0:.2f},{z1:.2f}] | vol {g.Mass():.0f} mm3 | com ({c.X():.2f},{c.Y():.2f},{c.Z():.2f})")
        out.append((n,iname,shp))
roots=TDF_LabelSequence(); st.GetFreeShapes(roots)
for i in range(1,roots.Length()+1):
    walk2(roots.Value(i), TopLoc_Location(), 0, "root")
import pickle
# export each instance to its own STEP for later use
import re
for k,(n,iname,shp) in enumerate(out):
    fn=re.sub(r'[^A-Za-z0-9_]+','_',f"{k:02d}_{n}_{iname}")[:80]+".step"
    cq.exporters.export(cq.Shape.cast(shp), fn)
