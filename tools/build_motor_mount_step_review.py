"""SolidWorks review pack: assembly, individual parts, nominal hardware envelopes."""
from pathlib import Path
import shutil,json,hashlib,zipfile
import cadquery as cq
from cad.winch_fuse_service import make
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cad/exports/RoomCleaner_Motor_Mount_STEP_Review_20261005'
def main():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(parents=True)
 source=ROOT/'cad/exports/RoomCleaner_Fuse_Service_Fit_20261004/STEP'
 for group in source.iterdir():
  for p in group.glob('*.step'):
   folder='03_BENCH_FIXTURES' if p.stem in ('fit_coupon','cartridge_bench_fixture') else '01_PRINTED_PARTS'
   (OUT/folder).mkdir(exist_ok=True);shutil.copy2(p,OUT/folder/p.name)
 shutil.copy2(ROOT/'cad/exports/winch_fuse_service/fuse_service_assembly.step',OUT/'00_COMPLETE_MOTOR_MOUNT.step')
 wall,adapter,p,printed,refs,hw=make()
 nominal={n:s for n,s in p.items()if n.endswith('_reference') and n!='spool_reference'}
 nominal.update(refs)
 for group,parts in [('02_PURCHASED_PART_ENVELOPES',nominal),('04_FASTENER_ENVELOPES',hw)]:
  folder=OUT/group;folder.mkdir()
  for name,shape in parts.items():cq.exporters.export(shape,str(folder/(name+'.step')))
 notes='''# Motor mount STEP review package

Start with `00_COMPLETE_MOTOR_MOUNT.step`: the current fuse-service motor station in its assembled positions, including the wall dock, adapter, case, spool, encoder, homing mechanism and electronics references.

This package covers ONE MOTOR MOUNT, not the suspended claw.

- 01_PRINTED_PARTS: all21 individual printable station components, including revised cover, carrier and fuse support.
- 02_PURCHASED_PART_ENVELOPES: nominal purchased-component references and explicit space reservations. These are simplified envelopes, not supplier production models. The spool is the printable `winch_spool_v2.step`, not a second purchased reference.
- 03_BENCH_FIXTURES: two optional test/fit pieces, not installed in the complete assembly.
- 04_FASTENER_ENVELOPES: locally modeled fasteners; this is not a guaranteed complete assembly fastener BOM.

All dimensions are millimeters. Individual STEP parts retain assembly coordinates: +Y is up along the wall, +Z points away from the wall, and the motor/spool shaft is along X. Preserve these coordinates when reconstructing the assembly. STL print orientations from the earlier print kit differ from these STEP coordinates.

STEP transfers geometry and available assembly hierarchy; it does not supply native SolidWorks features, functional mates, an engineering drawing or a solved motion model. Review imported organization and assign native mates as needed. Source geometry is CadQuery.

Suggested inspection order: dock/adapter capture and lock; spool/shaft and encoder alignment; cable path through guide and collar; switch travel; cover clearance; board retention; fuse support removal and wire access.

Current scope is UNPOWERED FIT PROTOTYPE. Cable bend suitability, actual purchased dimensions, complete downstream harness, retention, temperature and lifting capacity remain unverified. Wire sweeps are provisional clearance envelopes. The complete STEP includes space reservations that can be hidden for visual inspection. No cable operating pose or continuous swept motion is implied.

Read the included independent review for service details. Both fuse leads must be disconnected/released and displaced before support screw access; remove support and holder together, then unthread the lower lead off-case.
'''
 (OUT/'READ_FIRST.md').write_text(notes)
 shutil.copy2(ROOT/'verification/FUSE_SERVICE_REVIEW_20261004.md',OUT/'FUSE_SERVICE_REVIEW.md')
 shutil.copy2(ROOT/'docs/FUSE_SERVICE_PROTOTYPE_20261004.md',OUT/'FUSE_SERVICE_BUILD_NOTES.md')
 files=sorted(OUT.rglob('*.step'));checks=[]
 for file in files:
  s=cq.importers.importStep(str(file));solids=s.solids().vals()
  if not solids or not all(q.isValid()for q in solids):raise ValueError(file)
  checks.append(dict(file=str(file.relative_to(OUT)),solid_count=len(solids)))
 (OUT/'manifest.json').write_text(json.dumps(dict(scope='One motor mount; nominal unpowered fit only',checks=checks,sha256={str(f.relative_to(OUT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in OUT.rglob('*')if f.is_file()}),indent=2))
 with zipfile.ZipFile(OUT.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED)as z:
  for f in sorted(OUT.rglob('*')):
   if f.is_file():z.write(f,f.relative_to(OUT))
 print(len(files),'STEP files reimported with valid solids;',OUT.with_suffix('.zip'))
if __name__=='__main__':main()
