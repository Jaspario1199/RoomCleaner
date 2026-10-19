"""Allowlisted bench-only release: run CAD generators/audits first; no stale prints."""
from pathlib import Path
import hashlib,json,shutil,zipfile
import cadquery as cq
import trimesh
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cad/exports'
PACK=OUT/'RoomCleaner_Fresh_Bench_Only_20261002'
WIN=OUT/'winch_bench';DOCK=OUT/'winch_slide_mount'

def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def main():
 if PACK.exists():shutil.rmtree(PACK)
 prints=PACK/'PRINT_ONE_STATION';prints.mkdir(parents=True)
 for n in ('wall_dock','case_adapter','base_slide_version'):
  s=cq.importers.importStep(str(DOCK/(n+'.step')))
  assert s.val().isValid() and len(s.solids().vals())==1,n
  b=s.val().BoundingBox();s=s.translate((-(b.xmin+b.xmax)/2,-(b.ymin+b.ymax)/2,-b.zmin))
  cq.exporters.export(s,str(prints/(n+'.stl')))
 for n in ('cover','guide_carrier','outlet_backplate','homing_collar','switch_mount','homing_stopper','winch_spool_v2','encoder_magnet_cup','encoder_node_holder','encoder_mount'):
  copy(WIN/'print_oriented'/(n+'.stl'),prints/(n+'.stl'))
 for n in ('fit_coupon','cartridge_bench_fixture'):
  copy(WIN/'print_oriented'/(n+'.stl'),PACK/'OPTIONAL_FIT_TESTS'/(n+'.stl'))
 for src in [*(DOCK/(n+'.step')for n in ('wall_dock','case_adapter','base_slide_version','docked_station','docked_station_with_M3_hardware','station_with_winch_fasteners')),
             *(WIN/(n+'.step')for n in ('cover','guide_carrier','outlet_backplate','homing_collar','switch_mount','homing_stopper','winch_spool_v2','encoder_magnet_cup','encoder_mount','encoder_node_holder','winch_assembly','winch_pressed_assembly'))]:
  copy(src,PACK/'STEP'/src.name)
 for src in (WIN/'geometry_checks.json',WIN/'bench_audit.json',WIN/'homing_hardware_audit.json',WIN/'cover_export_audit.json',DOCK/'validation.json',DOCK/'functional_audit.json',DOCK/'encoder_pedestal_audit.json',DOCK/'winch_fastener_audit.json'):
  copy(src,PACK/'CHECKS'/src.name)
 for src in (WIN/'bench_preview.png',DOCK/'preview.png'):copy(src,PACK/'PREVIEW'/src.name)
 for src in (OUT/'claw_rail_correction').iterdir():
  if src.is_file():copy(src,PACK/'CLAW_CORRECTION'/src.name)
 for n in ('FRESH_MOUNT_RELEASE_20261002.md','MOUNT_INTERFACE_CONTROL_20261002.md','FRESH_STRUCTURAL_REVIEW_20261002.md','FRESH_PARTS_DELTA_20261002.md','PLUG_IN_STATION_PROPOSAL_20261002.md','EXTENDED_CLAW_V3_BUILD.md'):
  copy(ROOT/'docs'/n,PACK/'GUIDES'/n)
 for n in ('fresh_review_results_20261002.md','extended_rail_fasteners_report.md'):copy(ROOT/'verification'/n,PACK/'GUIDES'/n)
 for directory in ('cad','verification','tools'):
  for src in (ROOT/directory).rglob('*.py'):
   if 'exports' not in src.parts:copy(src,PACK/'SOURCE'/src.relative_to(ROOT))
 for n in ('requirements.txt','requirements-cad.txt'):copy(ROOT/n,PACK/'SOURCE'/n)
 # Supplier model retained as reference surfaces; never label it a closed solid.
 for n in ('RF8090-05.IGS','RF8090-05.dwg'):
  copy(ROOT/'cad/vendor/ronstan'/n,PACK/'SUPPLIER_REFERENCE'/n)
  copy(ROOT/'cad/vendor/ronstan'/n,PACK/'SOURCE/cad/vendor/ronstan'/n)
 (PACK/'README.md').write_text('''# Restricted bench-only prototype\n\nRead GUIDES/FRESH_MOUNT_RELEASE_20261002.md first. The40° outlet cone does not cover full-room operation. These files establish nominal bench assembly geometry; they do not certify strength, real hardware fit or safe overhead use.\n\nPRINT_ONE_STATION contains13 current parts. OPTIONAL_FIT_TESTS are coupons/fixture. No obsolete sleeves or printed metal-ring dummy are included. CLAW_CORRECTION has two revised uprights and their explicit rail-hardware checks; it is not a complete newly qualified claw release. STEP assemblies show separate hardware scopes.\n\nManufacturer dimensions, remaining measurements, restricted service order and physical proof/creep tests are documented in GUIDES. Run source generators/audits before rebuilding with tools/build_fresh_bench_release.py.\n''')
 mesh_checks=[]
 for src in list(prints.glob('*.stl'))+list((PACK/'OPTIONAL_FIT_TESTS').glob('*.stl'))+list((PACK/'CLAW_CORRECTION').glob('*.stl')):
  m=trimesh.load_mesh(src,process=True)
  assert m.is_watertight and m.volume>0,(src.name,m.is_watertight,m.volume)
  # OCCT bounding boxes can include a small tolerance expansion. Seat the
  # final mesh using its actual vertex bounds; translate only, never repair.
  correction=-float(m.bounds[0,2])
  if abs(correction)>1e-8:
   m.apply_translation((0,0,correction));m.export(src)
  assert abs(m.bounds[0,2])<.001,(src.name,m.bounds)
  mesh_checks.append({'file':str(src.relative_to(PACK)),'watertight':True,'volume_mm3':float(m.volume),'bed_z_mm':float(m.bounds[0,2]),'mesh_bed_translation_mm':correction})
 (PACK/'CHECKS/print_mesh_checks.json').write_text(json.dumps(mesh_checks,indent=2))
 manifest=[{'file':str(p.relative_to(PACK)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(PACK.rglob('*'))if p.is_file()]
 (PACK/'manifest.json').write_text(json.dumps(manifest,indent=2))
 archive=PACK.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for p in sorted(PACK.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(PACK))
 with zipfile.ZipFile(archive)as z:assert z.testzip()is None
 print(archive,len(manifest)+1,'files;',len(mesh_checks),'watertight bed-oriented meshes;',archive.stat().st_size,'bytes')
if __name__=='__main__':main()
