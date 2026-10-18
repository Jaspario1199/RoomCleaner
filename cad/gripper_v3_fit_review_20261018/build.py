import cadquery as q, math,json
from pathlib import Path
from gears import gear
P=Path(__file__).parent
A=(-18.15,5); B=(18.15,5); C=(A[0]+54.3/math.sqrt(2),A[1]-54.3/math.sqrt(2))
def box(w,d,h,x=0,y=0,z=0):return q.Workplane('XY').box(w,d,h,centered=(True,True,False)).translate((x,y,z))
def cy(r,h,x=0,y=0,z=0):return q.Workplane('XY').circle(r).extrude(h).translate((x,y,z))
def loc(s,xy,z=0):return s.translate((*xy,z))
def rounded(w,d,h,z):return box(w,d,h,-8,0,z).edges('|Z').fillet(5)
posts=[(-59,-48),(43,-48),(-59,48),(43,48)]
def holes(s,z,h):
 for x,y in posts:s=s.cut(cy(1.7,h,x,y,z))
 return s
# 112x112 shell: servo bay -46..0, gear cassette 0..50.
lower=rounded(112,112,46,-46).cut(rounded(106,106,43,-43))
# four solid screw towers; removable bottom plate would need separate design, use open-top bay.
for x,y in posts:
 lower=lower.union(cy(4.5,43,x,y,-43)).cut(cy(1.7,14,x,y,-14)).cut(cy(2.3,6,x,y,-6))
# cable exit with rounded edges; at rear wall, mechanical strain relief holes nearby.
lower=lower.cut(box(10,8,5,C[0],-54,-25))
for x in [C[0]-8,C[0]+8]:lower=lower.cut(cy(1.7,5,x,-48,-46))
base=holes(rounded(112,112,4,0),-1,6)
# servo long body along Y; shaft 10 mm from body end.
base=base.cut(box(21,41.5,7,C[0],C[1]+10,-1))
# tab landing pads on underside, holes are adjustable Y slots.
for yy in [C[1]-13.5,C[1]+33.5]:
 pad=box(26,10,7,C[0],yy,-7)
 for xx in [C[0]-5,C[0]+5]:
  cut=q.Workplane('XY').center(xx,yy).slot2D(6,3.4,90).extrude(13).translate((0,0,-8))
  cb=q.Workplane('XY').center(xx,yy).slot2D(9,6.4,90).extrude(8).translate((0,0,-3.5))
  pad=pad.cut(cut).cut(cb);base=base.cut(cut).cut(cb)
 base=base.union(pad)
base=base.cut(cy(14.3,5,*C,0))
for xy in [A,B]:
 base=base.union(cy(7,7,*xy,-3)).cut(cy(4.05,6.5,*xy,-2.5))
# Gear-bay walls and four M3 through screw towers.
wall=rounded(112,112,42,4).cut(rounded(106,106,44,3))
for x,y in posts:wall=wall.union(cy(4.5,42,x,y,4))
wall=holes(wall,3,44)
lid=holes(rounded(112,112,4,46),45,6)
for xy in [A,B]:lid=lid.cut(cy(12.2,6,*xy,45))
lid=lid.cut(cy(6.15,6,*C,45))
# Rounded service/lightening windows leave bearing and screw lands intact.
for x,y,w,d in [(-35,-28,34,24),(8,37,46,18)]:
 window=box(w,d,6,x,y,45).edges('|Z').fillet(3);lid=lid.cut(window)
 base=base.cut(box(w,d,6,x,y,-1).edges('|Z').fillet(3))
for y in range(-30,37,6):lower=lower.cut(box(38,2,5,-30,y,-47).edges('|Z').fillet(.8))
for y in [-55,55]:
 for z in [10,16,22,28,34]:
  for x in [-30,-8,14]:wall=wall.cut(box(16,6,2,x,y,z).edges('|Y').fillet(.8))
# Gear tooth thinning .10 per gear gives .20 nominal tangential backlash plus center allowance.
g54=gear(54,width=16)
for k in range(8):
 t=k*math.pi/4;g54=g54.cut(cy(6,18,27*math.cos(t),27*math.sin(t),-1))
g24=gear(24,width=20);g24b=gear(24,width=20,phase=7.5)
def output_hub(s):
 s=s.union(cy(12,11,z=40))
 s=s.cut(cy(4.15,45,z=3)) # blind at48, shaft end47.5
 for x in [-8.5,8.5]:
  s=s.cut(cy(1.7,9,x,0,43))
  # open radial nut insertion at z44, nut across flats5.8, axial2.6
  nut=q.Workplane('XY').polygon(6,5.8/math.cos(math.pi/6)).extrude(2.6).translate((x,0,44))
  s=s.cut(nut).cut(box(8,5.8,2.6,x+(-4 if x<0 else 4),0,44))
 return s
left=output_hub(g54.translate((0,0,5)).union(g24.translate((0,0,21))))
# sync gears21..41; journal40..51 overlaps1 mm.
right=output_hub(g24b.translate((0,0,21)))
pinion=gear(18,width=16,phase=10).translate((0,0,5)).union(cy(14,5,z=0)).union(cy(6,29,z=21))
pinion=pinion.cut(cy(12.65,2.8,z=-.1)).cut(cy(3.25,52,z=-1))
for angle in [0,90,180,270]:
 t=math.radians(angle);cut=q.Workplane('XY').center(8.5*math.cos(t),8.5*math.sin(t)).slot2D(6,3.3,angle).extrude(23).translate((0,0,-1));pinion=pinion.cut(cut)
flange=cy(17,5,z=51.5).cut(cy(3.25,7,z=51))
for x in [-8.5,8.5]:flange=flange.cut(cy(1.7,7,x,0,51)).cut(cy(3,3,x,0,54))
for y in [-12,12]:flange=flange.cut(cy(1.7,7,0,y,51))
# 0.5 axial gap under output flange: M3 screws clamp flange against separate .5 washer atop hub.
washer=cy(12,.5,z=51).cut(cy(3.25,1,z=51))
for x in [-8.5,8.5]:washer=washer.cut(cy(1.7,1,x,0,51))
spacerL=cy(7,1,z=4).cut(cy(4.15,1,z=4))
spacerR=cy(7,17,z=4).cut(cy(4.15,17,z=4))
# central bore servo reference; do not treat as supplier-exact.
servo=box(19.7,40,36,C[0],C[1]+10,-43).union(cy(9,7,*C,-7)).union(cy(2.95,3,*C,0))
for yy in [C[1]-13.5,C[1]+33.5]:
 t=box(19.7,7,2.5,C[0],yy,-9.5)
 for xx in [C[0]-5,C[0]+5]:t=t.cut(cy(1.7,4,xx,yy,-10))
 servo=servo.union(t)
horn=cy(12.5,2.5,*C,0).cut(cy(3,3,*C,0))
shaft=cy(4,50,z=-2.5)
top_spacer=cy(15,4.5,z=41).cut(cy(12.2,5,z=41))
pinion_spacer=cy(9,24.5,z=21).cut(cy(6.15,25,z=21))
parts={'12_top_thrust_spacer_PRINT2':top_spacer,'13_pinion_thrust_spacer':pinion_spacer,'01_servo_bay':lower,'02_motor_and_shaft_deck':base,'03_gear_bay':wall,'04_service_lid':lid,'05_pinion_18T':pinion,'06_compound_54T_24T':left,'07_follower_24T':right,'08_output_flange_PRINT2':flange,'09_output_shim_PRINT2':washer,'10_left_thrust_spacer':spacerL,'11_right_thrust_spacer':spacerR}
for n,s in parts.items():
 print('export',n,flush=True);assert s.val().isValid() and len(s.solids().vals())==1,(n,len(s.solids().vals()))
 q.exporters.export(s,str(P/(n+'.step')));q.exporters.export(s.translate((0,0,-s.val().BoundingBox().zmin)),str(P/(n+'.stl')),tolerance=.05,angularTolerance=.1)
static={'left_top_spacer':loc(top_spacer,A),'right_top_spacer':loc(top_spacer,B),'pinion_top_spacer':loc(pinion_spacer,C),'servo_bay':lower,'deck':base,'gear_bay':wall,'lid':lid,'servo_REFERENCE':servo,'horn_REFERENCE_UNMEASURED':horn,'left_pin_REFERENCE':loc(shaft,A),'right_pin_REFERENCE':loc(shaft,B),'left_spacer':loc(spacerL,A),'right_spacer':loc(spacerR,B)}
# Reference hardware, simplified cylinders/hex nuts, not detailed threads.
for i,(x,y) in enumerate(posts):
 static['case_M3x60_'+str(i)+'_REFERENCE']=cy(1.5,60,x,y,-10).union(cy(2.75,3,x,y,50))
 static['insert_M3_'+str(i)+'_REFERENCE']=cy(2.3,5.7,x,y,-5.7).cut(cy(1.5,6,x,y,-5.7))
for i,yy in enumerate([C[1]-13.5,C[1]+33.5]):
 for j,xx in enumerate([C[0]-5,C[0]+5]):
  static['servo_screw_'+str(i)+str(j)+'_REFERENCE']=cy(1.5,10,xx,yy,-13.5).union(cy(2.75,3,xx,yy,-3.5))
  static['servo_nut_'+str(i)+str(j)+'_REFERENCE']=q.Workplane('XY').polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).translate((xx,yy,-11.9)).cut(cy(1.5,3,xx,yy,-12))
def moving(a):
 def rot(s,xy,t):return loc(s.rotate((0,0,0),(0,0,1),t),xy)
 return {'pinion':rot(pinion,C,-3*a),'left_gear':rot(left,A,a),'right_gear':rot(right,B,-a),'left_flange':rot(flange,A,a),'right_flange':rot(flange,B,-a),'left_shim':rot(washer,A,a),'right_shim':rot(washer,B,-a)}
def asm(a,explode=False):
 ass=q.Assembly(name='RoomCleaner_Gearbox_V3_PROTOTYPE')
 for n,s in {**static,**moving(a)}.items():
  z=0
  if explode:
   z=90 if n=='lid' else (60 if 'flange' in n or 'shim' in n else (30 if n in ['pinion','left_gear','right_gear'] else (-55 if n=='servo_bay' else 0)))
  color=(.12,.24,.29) if n in ['servo_bay','gear_bay','deck','lid'] else ((.95,.58,.15) if n=='pinion' else ((.65,.69,.72) if 'REFERENCE' in n else (.17,.65,.68)))
  ass.add(s.translate((0,0,z)),name=n,color=q.Color(*color))
 return ass
for angle,n in [(0,'Closed'),(35,'Open')]:asm(angle).save(str(P/('Gearbox_V3_'+n+'.step')))
asm(0,True).save(str(P/'Gearbox_V3_Exploded.step'))
# exact BREP overlap screening; exclude intended fits and shared bearing surfaces.
checks=[]
for a in [0,5,10,15,20,25,30,35]:
 mv=moving(a)
 for x,y in [('pinion','left_gear'),('left_gear','right_gear')]:
  v=mv[x].intersect(mv[y]).val().Volume();checks.append({'angle':a,'pair':[x,y],'overlap_mm3':v})
 for n in ['pinion','left_gear','right_gear']:
  for sn in ['deck','gear_bay','lid','servo_bay']:
   v=mv[n].intersect(static[sn]).val().Volume();checks.append({'angle':a,'pair':[n,sn],'overlap_mm3':v})
print('worst',sorted(checks,key=lambda x:x['overlap_mm3'],reverse=True)[:8],flush=True)
(P/'checks.json').write_text(json.dumps(checks,indent=2))
(P/'parameters.json').write_text(json.dumps({'axes':{'A':A,'B':B,'C':C},'housing_mm':[112,112,96],'parts_valid':True,'module':1.5,'pressure_angle_deg':20,'gear_teeth':[18,54,24,24],'reduction_face_mm':16,'sync_face_mm':20,'output_travel_deg':35,'servo_travel_deg':105,'printed_solid_volume_cm3':sum(s.val().Volume()*(2 if n[:2] in ['08','09','12'] else 1) for n,s in parts.items())/1000},indent=2))
