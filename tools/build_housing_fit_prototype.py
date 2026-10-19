"""Fresh matched unpowered fit kit; explicitly excludes powered/load qualification."""
from pathlib import Path
import json,hashlib,shutil,zipfile
import cadquery as cq
import trimesh
from cad.winch_local_electronics import make as station
from cad.winch_bench import bench_parts
from cad.parts.winch_spool_v2 import make as spool
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cad/exports/RoomCleaner_Housing_Fit_20261004'

def main():
    if OUT.exists(): raise FileExistsError('Preserve prior kit; choose a new output revision before rebuilding')
    wall,adapter,p,printed,refs,hw=station()
    parts={'wall_dock':wall,'adapter_local_station':adapter,'base_local_station':p['base'],'cover_local_station':p['cover']}
    parts.update({n:s for n,s in p.items()if n not in ('base','cover')and not n.endswith('_reference')})
    parts['winch_spool_v2']=spool()
    parts['microfit_input_panel']=printed['microfit_input_panel']
    coupons=bench_parts();parts['fit_coupon']=coupons['fit_coupon'];parts['cartridge_bench_fixture']=coupons['cartridge_bench_fixture']
    optional={n:s for n,s in printed.items()if n!='microfit_input_panel'}
    rows=[]
    for group,mapping in [('PRINT_MAIN',parts),('OPTIONAL_EMPTY_TRAY_FIT',optional)]:
        for name,shape in mapping.items():
            if not shape.val().isValid()or len(shape.solids().vals())!=1: raise ValueError(name+' invalid solid')
            path=OUT/'STEP'/group/(name+'.step');path.parent.mkdir(parents=True,exist_ok=True);cq.exporters.export(shape,str(path))
            rt=cq.importers.importStep(str(path));volume=sum(s.Volume(1e-7)for s in shape.solids().vals());rv=sum(s.Volume(1e-7)for s in rt.solids().vals())
            if not rt.val().isValid()or len(rt.solids().vals())!=1 or abs(volume-rv)>max(.001,volume*1e-8):raise ValueError(name+' STEP roundtrip')
            orient=shape
            if name in ('guide_carrier','switch_mount'): orient=orient.rotate((0,0,0),(1,0,0),-90)
            elif name in ('outlet_backplate','homing_collar','homing_stopper'):orient=orient.rotate((0,0,0),(1,0,0),90)
            elif name=='encoder_magnet_cup':orient=orient.rotate((0,0,0),(0,1,0),90)
            elif name=='cover_local_station':orient=orient.rotate((0,0,0),(1,0,0),180)
            b=orient.val().BoundingBox();orient=orient.translate((-(b.xmin+b.xmax)/2,-(b.ymin+b.ymax)/2,-b.zmin))
            path=OUT/group/(name+'.stl');path.parent.mkdir(parents=True,exist_ok=True);cq.exporters.export(orient,str(path))
            mesh=trimesh.load_mesh(path,process=True)
            if not mesh.is_watertight or mesh.volume<=0:raise ValueError(name+' invalid mesh')
            dz=-float(mesh.bounds[0,2]);mesh.apply_translation((0,0,dz));mesh.export(path)
            if abs(mesh.bounds[0,2])>.001:raise ValueError(name+' off bed')
            rows.append(dict(part=name,group=group,brep_valid=True,solid_count=1,STEP_volume_delta_mm3=abs(volume-rv),mesh_watertight=True,mesh_volume_mm3=float(mesh.volume),mesh_bounds_mm=mesh.bounds.tolist()))
    guide=ROOT/'docs/HOUSING_PROTOTYPE_VALIDATION_20261004.md'
    shutil.copy2(guide,OUT/'READ_FIRST.md')
    for source in ['verification/HOUSING_FIT_REVIEW_20261004.md','verification/PAYLOAD_RESERVE_REVIEW_20261004.md','docs/FRESH_MOUNT_RELEASE_20261002.md','docs/LOCAL_STATION_HARDWARE_20261004.md']:
        target=OUT/'GUIDES'/Path(source).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,target)
    (OUT/'mesh_and_STEP_checks.json').write_text(json.dumps(rows,indent=2)+'\n')
    sourcefiles=['tools/build_housing_fit_prototype.py','cad/winch_local_electronics.py','cad/winch_bench.py','cad/winch_slide_mount.py','cad/parts/winch_spool_v2.py']
    manifest={'scope':'UNPOWERED FIT ONLY, restricted40deg bench outlet; no load rating or full-room connector release','parts':rows,'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()for n in sourcefiles},'file_sha256':{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(OUT.rglob('*'))if p.is_file()}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=OUT.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
        for path in sorted(OUT.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(OUT))
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('Archive integrity')
    print(len(parts),'main parts;',len(optional),'optional empty-tray fit parts;',len(rows),'valid roundtripped solids / watertight meshes;',archive.stat().st_size,'archive bytes')
if __name__=='__main__':main()
