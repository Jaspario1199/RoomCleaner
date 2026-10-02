"""Purchased-fastener nominal envelopes. Threads intentionally enter named pilots."""
import json
from cad.winch_slide_mount import make,volume,OUT
from cad.winch_bench import cyl,along_y,along_x,MOTOR_Y,SHAFT_Z
from cad.parts.winch_spool_v2 import screw_points
from verification.check_winch_slide_mount import nut
import cadquery as cq

def main():
 wall,adapter,p=make();rows=[];hw={}
 def add(n,s,allowed=()):
  hw[n]=s
  for name,f in [('wall_dock',wall),('case_adapter',adapter),*p.items()]:
   v=volume(s.intersect(f))
   assert v<.001 or name in allowed,(n,name,v)
   rows.append(dict(hardware=n,part=name,intersection_mm3=v,intentional_thread_or_purchased_part=name in allowed))
 # Two supported upper screws; unused lower slots must not receive screws.
 for x in (36,48):
  add(f'switch_head_{x}',along_y(cyl(3,2),x,-55,63))
  add(f'switch_shank_{x}',along_y(cyl(1.5,12),x,-43,63),('base',))
 for x,length,rear in ((0,25,-46),(40,30,-42)):
  add(f'cartridge_head_{x}',along_y(cyl(3,2),x,-64.5,32))
  add(f'cartridge_front_washer_{x}',along_y(cyl(3.5,.5).cut(cyl(1.6,.6)),x,-64,32))
  add(f'cartridge_shank_{x}',along_y(cyl(1.5,length),x,-64.5+length,32))
  add(f'cartridge_rear_washer_{x}',along_y(cyl(3.5,.5).cut(cyl(1.6,.6)),x,rear+.5,32))
  add(f'cartridge_nut_{x}',along_y(nut(0,0,0),x,rear+2.9,32))
 for x in (-37,-7):
  add(f'node_head_{x}',cyl(3,1.7,x,61,8))
  add(f'node_shank_{x}',cyl(1.5,12,x,61,-4))
  add(f'node_rear_washer_{x}',cyl(3.5,.5,x,61,-.5).cut(cyl(1.6,.6,x,61,-.55)))
  add(f'node_nut_{x}',nut(x,61,-2.9))
 for x in (-51.5,51.5):
  for y in (-66,66):
   add(f'cover_head_{x}_{y}',cyl(3,2,x,y,18.3))
   add(f'cover_shank_{x}_{y}',cyl(1.5,10,x,y,8.3),('base',))
   bit=cyl(2.5,65,x,y,20.3)
   assert volume(bit.intersect(p['cover']))<.001
   rows.append(dict(check='cover_driver',x=x,y=y))
 for x in (9,31):
  add(f'outlet_plate_head_{x}',along_y(cyl(2.75,3),x,-64.5,43))
  add(f'outlet_plate_shank_{x}',along_y(cyl(1.5,8),x,-56.5,43),('guide_carrier',))
 for y,z in ((20,53),(40,53),(30,23)):
  add(f'encoder_head_{y}_{z}',along_x(cyl(2,2),41.175,y,z))
  add(f'encoder_shank_{y}_{z}',along_x(cyl(1,5),43.175,y,z),('base',))
 # Cap button heads entire angular sweep, <=1.7mm head height; no spacers.
 sweep=along_x(cyl(16.2,1.7).cut(cyl(9.8,1.8)),39.175,MOTOR_Y,SHAFT_Z)
 for n,s in hw.items():
  if n.startswith('encoder_head'):
   assert volume(s.intersect(sweep))<.001
   rows.append(dict(check='rotor_head_sweep_clear',hardware=n,minimum_nominal_axial_gap_mm=.3))
 for y,z in ((14.5,17.5),(14.5,48.5),(45.5,17.5),(45.5,48.5)):
  add(f'motor_head_{y}_{z}',along_x(cyl(3,2),4,y,z))
  add(f'motor_shank_{y}_{z}',along_x(cyl(1.5,10),-6,y,z),('motor_reference',))
 # Cap 5mm screw tips stop0.675mm inside flange, with2.325mm nominal pilot engagement.
 for u,v in screw_points():
  head=along_x(cyl(3.2,1.7),39.175,MOTOR_Y+v,SHAFT_Z-u)
  add(f'cap_head_{u:.2f}_{v:.2f}',head)
  add(f'cap_shank_{u:.2f}_{v:.2f}',along_x(cyl(1.5,5),34.175,MOTOR_Y+v,SHAFT_Z-u),('spool_reference',))
 for stroke in (0,.5,1,1.5,2):
  for n,s in hw.items():
   assert volume(s.intersect(p['homing_collar'].translate((0,stroke,0))))<.001,(n,stroke)
   rows.append(dict(check='collar_clear_of_fastener',hardware=n,stroke_mm=stroke))
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'winch_fastener_audit.json').write_text(json.dumps(dict(checks=len(rows),results=rows,limits='Exact purchased hardware and component threads, screw lengths/tolerances, real switch lever/pivot and material strength require bench confirmation.'),indent=2))
 assembly=cq.Assembly(name='Winch_all_fasteners')
 assembly.add(wall,name='wall');assembly.add(adapter,name='adapter')
 for n,s in p.items():assembly.add(s,name=n)
 for n,s in hw.items():assembly.add(s,name=n)
 assembly.save(str(OUT/'station_with_winch_fasteners.step'))
 print(len(rows),'winch fastener checks passed')
if __name__=='__main__':main()
