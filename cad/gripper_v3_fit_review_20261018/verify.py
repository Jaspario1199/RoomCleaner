from pathlib import Path
import cadquery as q,json
P=Path(__file__).parent
rows=[];volume=0
for f in sorted(P.glob('[0-9][0-9]_*.step')):
 s=q.importers.importStep(str(f)).val();b=s.BoundingBox();qty=2 if f.name[:2] in ['08','09','12'] else 1;volume+=s.Volume()*qty
 rows.append({'part':f.name,'valid':s.isValid(),'solids':len(s.Solids()),'bbox_mm':[b.xlen,b.ylen,b.zlen],'volume_cm3':s.Volume()/1000,'quantity':qty})
asm=q.importers.importStep(str(P/'Gearbox_V3_Closed.step')).val();b=asm.BoundingBox()
checks=json.loads((P/'checks.json').read_text())
result={'parts':rows,'all_valid_single_solid':all(r['valid'] and r['solids']==1 for r in rows),'assembly_reimport_valid':asm.isValid(),'assembly_solid_count':len(asm.Solids()),'assembly_bbox_mm':[b.xlen,b.ylen,b.zlen],'collision_sample_count':len(checks),'maximum_sampled_overlap_mm3':max(r['overlap_mm3'] for r in checks),'printed_volume_including_quantities_cm3':volume/1000,'fully_dense_PETG_mass_g_at_1p27_NOT_slicer_prediction':volume/1000*1.27,'limits':'Sampled gear/housing collisions only. Not all-pairs hardware or continuous motion validation. No independent or physical verification.'}
(P/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='parts'},indent=2))
p=json.loads((P/'parameters.json').read_text());p['printed_solid_volume_cm3']=volume/1000;p['assembly_envelope_mm']=[b.xlen,b.ylen,b.zlen];(P/'parameters.json').write_text(json.dumps(p,indent=2))
# Fit coupon is separate from the functional part count and assembly mass.
c=q.Workplane('XY').box(110,32,5,centered=(True,True,False))
for x,d in [(-42,8.1),(-22,8.3),(0,12.3),(32,24.4)]:c=c.cut(q.Workplane('XY').circle(d/2).extrude(7).translate((x,0,-1)))
q.exporters.export(c,str(P/'FIT_ONLY_bore_coupon.step'));q.exporters.export(c,str(P/'FIT_ONLY_bore_coupon.stl'))
assert result['all_valid_single_solid'] and result['assembly_reimport_valid'] and result['maximum_sampled_overlap_mm3']<.001
