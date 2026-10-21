"""
INDEPENDENT geometry verification of the Gripper 1021 electrical housing with the three-cable holes ("_34").

  Part under test : exports/step/gripper1021_housing_cambay_34.step / exports/stl/gripper1021_housing_cambay_34.stl
  Baseline        : exports/step/gripper1021_housing_cambay.step (+ _cover.step), Jasper's raw housing (read only)
  Spec            : cad/GRIPPER_1021_SPEC.md section 5, as amended by the lead's decisions in section 5.1

Written by the geometry-verifier.  It does NOT import the implementer's tests, build script or cable-line analyzer, and it does not
use cad.params for any expected value: every expected number below is typed in from the task / spec table.  Measurements are made on the
exported STEP / STL files (B-rep face parameters, point-in-solid probes, face-signature comparison, local volume differences, an own
ray / segment-to-triangle distance code on a re-tessellated mesh).  The only repository code it executes is
cad.parts.gripper1021_housing_cambay.make() (item 10: baseline regenerates identically) and make_34() (STEP vs source).
Nothing in the repository is written; STEP round-trip files go to a pytest tmp dir.

Frames.  World -> "box frame": subtract ORIGIN (origin on the tube axis in the box bottom plane, +y up; box x = world x,
box z = world z - 1103.9899).  Body frame of the claw: origin on the tube axis at box y = 7.82, +x = box x, +y = -box z, +z = box y.
"""

from __future__ import annotations

import itertools
import math
import os
import struct
import sys
import time
from functools import lru_cache

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")
from OCP.BRepAdaptor import BRepAdaptor_Surface                      # noqa: E402
from OCP.BRepCheck import BRepCheck_Analyzer                         # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier              # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape              # noqa: E402
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane  # noqa: E402
from OCP.TopAbs import TopAbs_IN, TopAbs_OUT                         # noqa: E402
from OCP.gp import gp_Pnt                                            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

STEP_34 = os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay_34.step")
STL_34 = os.path.join(REPO, "exports", "stl", "gripper1021_housing_cambay_34.stl")
STEP_BASE = os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay.step")
STL_BASE = os.path.join(REPO, "exports", "stl", "gripper1021_housing_cambay.stl")
STEP_COVER = os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay_cover.step")
STEP_RAW = os.path.join(REPO, "cad", "reference", "gripper_1021", "parts", "05_Gripper_Electric_Housing_Base_2__NAUO5.step")

pytestmark = pytest.mark.skipif(
    not all(os.path.exists(p) for p in (STEP_34, STL_34, STEP_BASE, STEP_COVER, STEP_RAW)), reason="exports / reference parts not available")

# ---- expected values, typed from the task / spec (NOT read from cad.params) ----------------------------------------------------
ORIGIN = (951.8475, 1091.1905, 1103.9899)
IDS = ("C", "A", "B")
OUTER = {"C": (0.0, 42.0, -45.0), "A": (-45.0, 42.0, 25.98), "B": (45.0, 42.0, 25.98)}
INNER = {"C": (0.0, 42.0, -40.0), "A": (-40.0, 42.0, 23.09), "B": (40.0, 42.0, 23.09)}
WALL_NORMAL = {"C": (0.0, 0.0, -1.0), "A": (-1.0, 0.0, 0.0), "B": (1.0, 0.0, 0.0)}
WALL_LEN = {"C": 5.0, "A": 5.0 / math.cos(math.radians(30)), "B": 5.0 / math.cos(math.radians(30))}
BORE_R, CHAMFER, TIP_HALF_DEG, LABEL_H, LABEL_DEPTH, LABEL_ABOVE = 1.0, 0.5, 45.0, 4.0, 0.4, 5.0
KEEPOUT = 5.0
HOLE_ZONE = 3.0                      # mm: changed regions must lie within this of a hole or a label
BODY_ORIGIN_BOX_Y = 7.82
BODY_POINTS_M = {"C": (0.0, 0.0450, 0.0342), "A": (-0.0450, -0.0260, 0.0342), "B": (0.0450, -0.0260, 0.0342)}
ANCHORS_M = {"A": (0.05, 0.05, 2.5932), "B": (3.3028, 0.05, 2.5932), "C": (1.6764, 2.6932, 2.5932)}
ROOM_M = (3.3528, 2.7432)
WALL_MARGIN_M = 0.2
PETG = 1.27                          # g/cm3

RESULTS: dict = {}                   # filled by the tests, dumped by the last test for the report


def note(key, value):
    RESULTS[key] = value


def vec(p):
    return np.array(p, dtype=float)


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def axis_out(hid):
    """Unit outward axis (horizontal, radial) from the spec mouths."""
    return unit(vec(OUTER[hid]) - vec(INNER[hid]))


def e1_of(hid):
    """Horizontal unit vector perpendicular to the axis (lateral direction of the hole cross-section)."""
    a = axis_out(hid)
    return unit(np.cross([0.0, 1.0, 0.0], a))


# ---- loading ---------------------------------------------------------------------------------------------------------------------
def to_box(shape):
    return shape.translate(cq.Vector(-ORIGIN[0], -ORIGIN[1], -ORIGIN[2]))


@lru_cache(maxsize=None)
def load_box(path):
    return to_box(cq.importers.importStep(path).val())


@lru_cache(maxsize=None)
def classifier(path):
    sh = load_box(path)
    c = BRepClass3d_SolidClassifier(sh.wrapped)

    def state(p):
        c.Perform(gp_Pnt(float(p[0]), float(p[1]), float(p[2])), 1e-7)
        s = c.State()
        return "I" if s == TopAbs_IN else ("O" if s == TopAbs_OUT else "N")

    return state


def part():
    return load_box(STEP_34)


def base():
    return load_box(STEP_BASE)


def is_empty34(p):
    return classifier(STEP_34)(p) == "O"


def is_solid34(p):
    return classifier(STEP_34)(p) in ("I",)


def is_solid_base(p):
    return classifier(STEP_BASE)(p) in ("I",)


def bisect_boundary(inside_fn, p_empty, p_solid, tol=1e-4):
    """Along the segment p_empty -> p_solid, locate the empty/solid transition; returns the fraction t in [0,1] of the boundary."""
    lo, hi = 0.0, 1.0
    a, b = vec(p_empty), vec(p_solid)
    assert inside_fn(a) and not inside_fn(b), "bisection needs an empty start and a solid end"
    length = np.linalg.norm(b - a)
    while (hi - lo) * length > tol:
        mid = 0.5 * (lo + hi)
        if inside_fn(a + (b - a) * mid):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
