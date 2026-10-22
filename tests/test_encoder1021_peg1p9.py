"""
Acceptance checks for the SHORT-PEG v2 magnet cap for the 0.019 in prototype fin (deliverable C of cad/HEAT_FIN_1021_SPEC.md; magnet Ø4.0):

    encoder1021_magnet_cap_v2_m4_peg1p9   ENC1021_CAP_PEG_LEN = FIN1021_PROTO_CAP_PEG_LEN = 1.9, everything else v2

The thin fin puts the motor shaft end at y = 22.0 + (2.0 - 0.483) = 23.517; the standard peg (end y 22.6) would hit it by 0.917 mm, the short peg ends at
y = 26.0 - 1.9 = 24.1, 0.583 mm clear.  With the 1/8 in fin the shaft ends at 20.825 and the standard cap clears it by 1.775 mm.
Run with /usr/bin/python3 -m pytest tests/test_encoder1021_peg1p9.py
"""

from __future__ import annotations

import math
import os
import sys

import pytest

cq = pytest.importorskip("cadquery")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import encoder1021 as E                           # noqa: E402
from tests.test_encoder1021 import Probe, _bb                    # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(E.REF_DIR), reason="station_1021 reference parts not available")

SHAFT_END_THIN = P.ENC1021_SHAFT_END_Y + (P.FIN1021_REF_T - P.FIN1021_T_PROTOTYPE_MM)     # 23.517 with the 0.019 in fin
SHAFT_END_THICK = P.ENC1021_SHAFT_END_Y + (P.FIN1021_REF_T - P.FIN1021_T_PRODUCTION_MM)   # 20.825 with the 1/8 in fin


@pytest.fixture(scope="module")
def peg_cap():
    return E.build_v2_variant("m4_peg1p9").val()


@pytest.fixture(scope="module")
def std_cap():
    return E.build_v2_variant("m4").val()


def _shaft_round(end_y: float) -> cq.Shape:
    """A plain Ø5 shaft ending at y = end_y (the D-flat only removes material)."""
    return cq.Solid.makeCylinder(P.MOTOR_SHAFT_DIA / 2, end_y + 40.0, cq.Vector(0, -40.0, 0), cq.Vector(0, 1, 0))


def test_parameters():
    assert P.FIN1021_PROTO_CAP_PEG_LEN == 1.9 and P.ENC1021_CAP_PEG_LEN == 3.4          # the v2 cap default is unchanged
    assert SHAFT_END_THIN == pytest.approx(23.517, abs=1e-9)
    assert E.V2_VARIANTS["m4_peg1p9"][1] == {"ENC1021_CAP_PEG_LEN": 1.9}
    with E.params_override(ENC1021_CAP_PEG_LEN=1.9):
        assert E.Cfg(v2=True).peg_end_y == pytest.approx(24.1)
    assert P.ENC1021_CAP_PEG_LEN == 3.4


def test_peg_end_is_y_24p1(peg_cap):
    assert peg_cap.isValid() and len(peg_cap.Solids()) == 1
    assert _bb(peg_cap)[2] == pytest.approx(24.1, abs=0.01)                               # lowest y of the solid
    y_end = 20.0 + Probe(peg_cap).boundary((0, 20.0, 0), (0, 1, 0), 8.0)                  # first surface met going up the axis
    assert y_end == pytest.approx(24.1, abs=0.01)
    assert 20.0 + Probe(peg_cap).boundary((5.0, 20.0, 0.0), (0, 1, 0), 9.0) == pytest.approx(26.0, abs=0.01)   # head underside unchanged


def test_clear_of_a_shaft_ending_at_23p517(peg_cap):
    d = peg_cap.distance(_shaft_round(SHAFT_END_THIN))
    assert d >= P.FIN1021_PROTO_PEG_MIN_CLEAR and d == pytest.approx(24.1 - SHAFT_END_THIN, abs=1e-6)       # 0.583 mm
    assert peg_cap.intersect(_shaft_round(SHAFT_END_THIN)).Volume() < 1e-9


def test_clear_of_the_reference_shaft_moved_with_the_thin_fin(peg_cap):
    """The Motor_Reference's own shaft (Ø5 with its D-flat), moved by 2.0 - t = +1.517 mm."""
    shaft = min(E.reference_parts(True)["Motor_Reference"].Solids(), key=lambda s: s.Volume())
    moved = shaft.translate(cq.Vector(0, P.FIN1021_REF_T - P.FIN1021_T_PROTOTYPE_MM, 0))
    assert moved.BoundingBox().ymax == pytest.approx(SHAFT_END_THIN, abs=1e-6)
    assert peg_cap.distance(moved) >= P.FIN1021_PROTO_PEG_MIN_CLEAR


def test_standard_peg_hits_the_thin_fin_shaft_but_clears_the_1p8_one(std_cap):
    """Why the variant exists: the standard cap (peg end 22.6) collides with the shaft of the 0.019 in station, and clears the 1/8 in station's."""
    assert std_cap.intersect(_shaft_round(SHAFT_END_THIN)).Volume() > 10.0                # about 0.917 mm of Ø5 shaft inside the peg: 18 mm3
    assert std_cap.distance(_shaft_round(SHAFT_END_THICK)) == pytest.approx(22.6 - SHAFT_END_THICK, abs=1e-6)
    assert 22.6 - SHAFT_END_THICK >= 1.5                                                  # 1.775 mm


def test_only_the_peg_changed(peg_cap, std_cap):
    """Same head, pocket, ribs and notch: the two caps agree on everything at y >= 26.0 (the head), the short peg just ends 1.5 mm later."""
    box = cq.Workplane("XY").box(40, 40, 40, centered=False).translate((-20, 26.0, -20)).val()
    a, b = peg_cap.intersect(box), std_cap.intersect(box)
    assert a.Volume() == pytest.approx(b.Volume(), rel=1e-9)
    assert a.cut(b).Volume() < 1e-6 and b.cut(a).Volume() < 1e-6
    pp = E.to_print_pose(peg_cap, "cap").BoundingBox()                                   # same print orientation as the v2 cap: magnet face on the bed, peg up
    assert (pp.xlen, pp.ylen, pp.zlen) == pytest.approx((14.0, 14.0, 5.2), abs=1e-3)


def test_short_peg_still_has_its_three_crush_ribs(peg_cap):
    """Rib tip r = 2.55 + 0.20 (0.10 crush into the Ø5.30 bore) over the full length behind the 0.5 mm lead-in; flat at x = +2.05 unchanged."""
    pc = Probe(peg_cap)
    for y in (24.7, 25.2, 25.8):
        for a in (60, 180, 300):
            r = pc.boundary((0, y, 0), (math.cos(math.radians(a)), 0, math.sin(math.radians(a))), 4.0, 0.005)
            assert r == pytest.approx(2.55 + P.ENC1021_V2_CAP_RIB_H, abs=0.006), (y, a)
        assert pc.boundary((0, y, 0), (1, 0, 0), 4.0, 0.005) == pytest.approx(P.ENC1021_CAP_PEG_FLAT_X, abs=0.006)


def test_contact_with_the_spool_is_the_ribs_only(peg_cap, std_cap):
    """Crush volume against the corrected reference spool: the ribs only, about half of the standard cap's (1.5 mm less rib engagement) -> note for the print."""
    spool = E.reference_parts(True)["Spool1011"]
    a, b = peg_cap.intersect(spool), std_cap.intersect(spool)
    assert len(a.Solids()) == 3 and len(b.Solids()) == 3
    assert a.Volume() == pytest.approx(0.234, abs=0.01) and b.Volume() == pytest.approx(0.477, abs=0.01)
    assert peg_cap.cut(spool).Volume() == pytest.approx(peg_cap.Volume() - a.Volume(), abs=1e-6)


def test_exports_exist_and_equal_the_build(peg_cap):
    step = os.path.join(E.STEP_DIR, "encoder1021_magnet_cap_v2_m4_peg1p9.step")
    stl = os.path.join(E.STL_DIR, "encoder1021_magnet_cap_v2_m4_peg1p9.stl")
    assert os.path.isfile(step) and os.path.isfile(stl) and os.path.getsize(stl) > 1000
    back = cq.importers.importStep(step).val()
    assert back.isValid() and len(back.Solids()) == 1
    assert back.Volume() == pytest.approx(peg_cap.Volume(), rel=1e-5)
    assert _bb(back)[2] == pytest.approx(24.1, abs=5e-3)
    # the nominal v2 / Ø6 record files are not overwritten by this variant
    assert not os.path.samefile(step, os.path.join(E.STEP_DIR, "encoder1021_magnet_cap_v2.step"))
