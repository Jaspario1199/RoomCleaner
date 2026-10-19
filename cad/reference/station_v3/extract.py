"""Extract each part of solidworks/v3_assembly_2026-10-19/Assem_laundry_v3.STEP
into the STATION frame used by cad/parts/station_cover_v4.py:

    origin = motor shaft axis at the motor flange face (y = 0)
    +y     = along the shaft toward the spool (assembly -> local: subtract O)
    +z     = up (vertical, as installed)
    +x     = out of the wall into the room

Run:  /usr/bin/python3 -m cad.reference.station_v3.extract
"""
from pathlib import Path

import cadquery as cq
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "solidworks" / "v3_assembly_2026-10-19" / "Assem_laundry_v3.STEP"
OUT = Path(__file__).parent
# motor shaft axis (cylinder r=2.5 mm) and flange face (motor plane y=0) in assembly coordinates
O = (1269.08, 738.76, 927.56)


def main():
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    r.ReadFile(str(SRC))
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = TDF_LabelSequence()
    st.GetFreeShapes(roots)
    comps = TDF_LabelSequence()
    st.GetComponents_s(roots.Value(1), comps)
    for i in range(comps.Length()):
        c = comps.Value(i + 1)
        ref = TDF_Label()
        st.GetReferredShape_s(c, ref)
        a = TDataStd_Name()
        name = a.Get().ToExtString() if ref.FindAttribute(TDataStd_Name.GetID_s(), a) else f"part{i}"
        shape = cq.Shape.cast(st.GetShape_s(c)).translate(cq.Vector(*O) * -1)
        cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{name}.step"))
        bb = shape.BoundingBox()
        print(f"{name}: x[{bb.xmin:.1f},{bb.xmax:.1f}] y[{bb.ymin:.1f},{bb.ymax:.1f}] z[{bb.zmin:.1f},{bb.zmax:.1f}]")


if __name__ == "__main__":
    main()
