"""Orient/center winch STL files for bench slicing; no hardware surrogates in load list."""
from pathlib import Path
import cadquery as cq
from cad.winch_bench import build,bench_parts,OUT

def main():
 out=OUT/'print_oriented';out.mkdir(parents=True,exist_ok=True)
 p=build();p.update(bench_parts())
 names=['fit_coupon','cartridge_bench_fixture','guide_carrier','homing_collar','switch_mount','homing_stopper','base','cover','encoder_magnet_cup','encoder_node_holder','eyelet_fit_dummy','stop_sleeve_0','stop_sleeve_1']
 for n in names:
  part=p[n]
  if n in ('guide_carrier','homing_collar','switch_mount','homing_stopper','eyelet_fit_dummy','stop_sleeve_0','stop_sleeve_1'):
   part=part.rotate((0,0,0),(1,0,0),90)
  elif n=='encoder_magnet_cup':part=part.rotate((0,0,0),(0,1,0),-90)
  elif n=='cover':part=part.rotate((0,0,0),(1,0,0),180)
  b=part.val().BoundingBox();part=part.translate((-(b.xmin+b.xmax)/2,-(b.ymin+b.ymax)/2,-b.zmin))
  cq.exporters.export(part,str(out/(n+'.stl')))
 print(len(names),'oriented STLs ready; sliced supports still require review')
if __name__=='__main__':main()
