"""STEP copies of the v2 encoder casing and magnet cap placed in the coordinates of Jasper's 10/21 assembly
(solidworks/v4_assembly_2026-10-21/Assem_laundry_v3_step_1021.STEP), so they drop into place in SOLIDWORKS when the part
origin is put on the assembly origin.

The v2 exports (exports/step/encoder1021_*_v2.step) are in the station frame (cad/ENCODER_1021_SPEC.md section 1).
Station frame -> assembly: + (0, 0, ENC1021_REF_SHIFT_Z) + the extraction residual (ENC1021_REF_RESIDUAL), then + O from
cad/reference/station_1021/extract.py.  The check below repeats the verified contacts in assembly coordinates:
casing vs slip-in = the foot bumps only, cap vs spool = the crush ribs only (verification/encoder1021_v2_verification.md).

Any cap / casing file can be exported: give its stem(s) (STEP file name without .step) on the command line.  With no argument the files made for the
measured Ø4.0 magnet are exported (lead 2026-10-22; the Ø6 v2 asm1021 files are kept as the superseded record and are not rewritten):
    encoder1021_magnet_cap_v2_m4          standard peg 3.4  (stations with the 1/8 in fin)
    encoder1021_magnet_cap_v2_m4_peg1p9   short peg 1.9     (stations with the 0.019 in prototype fin)
The contact check is the same: a cap touches the spool only (its crush ribs) and nothing else (the peg stays clear of the motor shaft); the expected
contact volume of a stem without a recorded value is computed on the station-frame file against the corrected reference spool, so the check
also proves the placement offset.

Run:  PYTHONPATH=. /usr/bin/python3 tools/export_encoder1021_asm.py [stem ...]
"""
from pathlib import Path

import cadquery as cq

from cad import params as P
from cad.reference.station_1021.extract import O, SRC

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "exports" / "step"
EXPECTED = {"encoder1021_casing_v2": ("Slipin_mount_piecev3", 0.336), "encoder1021_magnet_cap_v2": ("Spool1011", 0.477)}   # recorded contact volume, mm3 (Ø6 v2 files)
CAP_STEMS = ("encoder1021_magnet_cap_v2_m4", "encoder1021_magnet_cap_v2_m4_peg1p9")   # default: caps for the Ø4.0 magnet
CAP_TOUCH = "Spool1011"


def offset() -> cq.Vector:
    dx, dy, dz = P.ENC1021_REF_RESIDUAL
    return cq.Vector(O[0] + dx, O[1] + dy, O[2] + P.ENC1021_REF_SHIFT_Z + dz)


def main(stems=None):
    off = offset()
    asm = cq.importers.importStep(str(SRC)).val().Solids()
    refs = {p.stem: cq.importers.importStep(str(p)).val().translate(cq.Vector(*O))
            for p in (ROOT / "cad" / "reference" / "station_1021").glob("*.step")}
    names = {}
    for i, s in enumerate(asm):
        for n, r in refs.items():
            if abs(r.Volume() - s.Volume()) < 0.01 and (r.Center() - s.Center()).Length < 0.01:
                names[i] = n
    print("offset station frame -> assembly:", tuple(round(v, 6) for v in off.toTuple()))
    for stem in (stems or CAP_STEMS):
        touch, vol = EXPECTED.get(stem, (CAP_TOUCH, None))
        src = cq.importers.importStep(str(STEP_DIR / f"{stem}.step")).val()
        if vol is None:                                              # station-frame contact volume of the file against the corrected reference part
            from cad.parts import encoder1021 as E
            vol = src.intersect(E.reference_parts(True)[touch]).Volume()
        out = STEP_DIR / f"{stem}_asm1021.step"
        cq.exporters.export(cq.Workplane().add(src.translate(off)), str(out))
        back = cq.importers.importStep(str(out)).val()
        assert abs(back.Volume() - src.Volume()) < 1e-3, "STEP round trip changed the volume"
        contacts = {names.get(i, f"solid {i}"): back.intersect(s).Volume() for i, s in enumerate(asm) if back.distance(s) < 1e-6}
        ok = set(contacts) == {touch} and abs(contacts[touch] - vol) < 0.005
        print(f"{out.name}: volume {back.Volume():.3f} mm3, contacts {({k: round(v, 3) for k, v in contacts.items()})} "
              f"-> {'PASS' if ok else 'FAIL'} (expected {touch} {vol:.3f})")
        assert ok


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
