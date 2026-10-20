"""
Read-only loader for the user's gripper v6 assembly STEP
(solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP).

Applies the assembly transforms (OCP/XCAF) and returns [(name, cq.Shape)].
The STEP file is NEVER modified.  Same method as
verification/gripper_v6_scripts/gripper_v6_measure.py.
"""

from __future__ import annotations

import os

import cadquery as cq
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.XCAFApp import XCAFApp_Application
from OCP.TopLoc import TopLoc_Location

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V6_STEP = os.path.join(REPO, "solidworks", "gripper_v6_2026-10-20", "LaundryGripperAssem1.STEP")
BOX_NAME = "Gripper_Electric_Housing_Base (2)"
CYLINDER_NAME = "Griper Cylinder"
TUBE_NAME = "aluminum tubing"


def load_v6(path: str = V6_STEP):
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("x"))
    app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.ReadFile(path)
    reader.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def name(label):
        n = TDataStd_Name()
        return n.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"

    out = []

    def walk(label, loc):
        if st.IsAssembly_s(label):
            comps = TDF_LabelSequence()
            st.GetComponents_s(label, comps)
            for i in range(1, comps.Length() + 1):
                c = comps.Value(i)
                ref = TDF_Label()
                st.GetReferredShape_s(c, ref)
                walk(ref, loc.Multiplied(st.GetLocation_s(c)))
        else:
            out.append((name(label), cq.Shape.cast(st.GetShape_s(label).Moved(loc))))

    seq = TDF_LabelSequence()
    st.GetFreeShapes(seq)
    for i in range(1, seq.Length() + 1):
        walk(seq.Value(i), TopLoc_Location())
    return out


def find(parts, name: str):
    for n, s in parts:
        if n == name:
            return s
    raise KeyError(name)


def tube_axis_world(parts):
    """Tube axis point (x, z) and Y extent from the cylindrical faces of the tube."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    tube = find(parts, TUBE_NAME)
    for f in tube.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder:
            loc = a.Cylinder().Axis().Location()
            bb = tube.BoundingBox()
            return loc.X(), loc.Z(), bb.ymin, bb.ymax
    raise RuntimeError("tube cylinder not found")
