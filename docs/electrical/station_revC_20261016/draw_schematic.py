"""Generate audited module-level electrical schematic; no hardware interface."""
from pathlib import Path
import html
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Readable', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('ReadableBold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

OUT = Path(__file__).resolve().parent
W, H = 1190, 842  # A3 landscape, approximately
C = canvas.Canvas(str(OUT / 'RoomCleaner_Station_RevC.pdf'), pagesize=(W, H))
C.setTitle('RoomCleaner motor station - Rev C electrical schematic and audit')
INK = '#172b3a'; RED = '#aa2525'; BLUE = '#155ca2'; GREEN = '#096a50'; GRAY = '#566573'
svg = []

def line(x1,y1,x2,y2,color=INK,width=1.5,dash=False):
    C.setStrokeColor(HexColor(color)); C.setLineWidth(width)
    C.setDash([5,4] if dash else [])
    C.line(x1,H-y1,x2,H-y2); C.setDash([])
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')

def wire(points,color=INK):
    for a,b in zip(points,points[1:]): line(*a,*b,color)

def text(x,y,s,size=12,bold=False,color=INK,anchor='start'):
    C.setFillColor(HexColor(color)); C.setFont('ReadableBold' if bold else 'Readable',size)
    {'start':C.drawString,'middle':C.drawCentredString,'end':C.drawRightString}[anchor](x,H-y,s)
    svg.append(f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" font-weight="'+('bold' if bold else 'normal')+f'" fill="{color}" text-anchor="{anchor}">{html.escape(s)}</text>')

def rect(x,y,w,h,fill=None,stroke=INK):
    C.setLineWidth(1.3); C.setStrokeColor(HexColor(stroke)); C.setFillColor(HexColor(fill or '#ffffff'))
    C.rect(x,H-y-h,w,h,fill=bool(fill),stroke=1)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill or "none"}" stroke="{stroke}" stroke-width="1.3"/>')

def circle(x,y,r=3,fill=INK):
    C.setFillColor(HexColor(fill or '#ffffff')); C.setStrokeColor(HexColor(INK)); C.setLineWidth(1.2)
    C.circle(x,H-y,r,stroke=1,fill=1)
    svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill or "white"}" stroke="{INK}"/>')

def ground(x,y):
    line(x,y,x,y+10)
    for k,half in enumerate([12,8,3]): line(x-half,y+10+5*k,x+half,y+10+5*k)

def tp(x,y,name):
    line(x,y,x,y-15); circle(x,y-18,3,None); text(x+7,y-18,name,11,True)

def net(x,y,name,color=BLUE):
    text(x,y-6,name,11,True,color)

def res(x,y,vertical=True,label='10k',ref=''):
    if vertical:
        line(x,y,x,y+10); rect(x-5,y+10,10,30); line(x,y+40,x,y+50)
        text(x+10,y+22,ref,10,True); text(x+10,y+36,label,10)
    else:
        line(x,y,x+10,y); rect(x+10,y-5,30,10); line(x+40,y,x+50,y)
        text(x+25,y-12,ref+' '+label,10,anchor='middle')

def pin(x,y,x2,label,inside_x,align='start'):
    line(x,y,x2,y); text(inside_x,y+4,label,12,anchor=align)

def header(n,title,subtitle):
    global svg
    svg=[]
    text(35,36,'ROOMCLEANER / MOTOR STATION',13,True,BLUE)
    text(35,70,title,25,True)
    text(35,94,subtitle,12,color=GRAY)
    line(35,108,1155,108,BLUE)
    text(1155,36,f'REV C | 2026-10-16 | SHEET {n}/4',11,True,anchor='end')
    text(35,813,'DESIGN REVIEW - NOT AS-BUILT CERTIFICATION. Do not reuse the suspect XIAO until isolated and assessed.',10,True,RED)
    text(1155,813,'Symbols are functional; use module pin labels, not drawing position.',10,anchor='end')

def finish(n):
    (OUT / f'sheet_{n}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>'+''.join(svg)+'</svg>')
    C.showPage()

def table(x,y,width,headers,rows,colwidths,rowh=30,size=11):
    rect(x,y,width,rowh,fill='#e9f0f5',stroke='#bdccd6')
    offsets=[x]
    for z in colwidths: offsets.append(offsets[-1]+z)
    for i,h in enumerate(headers): text(offsets[i]+8,y+20,h,11,True)
    for j,row in enumerate(rows):
        yy=y+rowh*(j+1)
        if j%2==0: rect(x,yy,width,rowh,fill='#f5f8fa',stroke='#f5f8fa')
        for i,s in enumerate(row): text(offsets[i]+8,yy+20,s,size)
    return y+rowh*(len(rows)+1)

header(1,'Power circuit - one station','Real wire connections, component symbols, and named nets. Filled dot = connected junction. Same net label = same electrical node.')

# Incoming branch cable, capacitor and motor supply.
text(40,144,'J1  TWO-WIRE INPUT',13,True)
text(40,162,'Branch fuse is at supply end (see below).',10)
circle(55,205,4,None); text(40,193,'1: +12V',11,True,RED)
circle(55,490,4,None); text(40,478,'2: RETURN',11,True)
wire([(59,205),(1000,205)],RED); net(290,205,'+12_STATION',RED)
tp(145,205,'TP1'); circle(580,205)
wire([(580,205),(580,264)])
line(565,264,595,264); line(565,273,595,273)
text(557,257,'+',14,True,RED); text(600,265,'C1  100 uF / 50V',12,True)
text(600,285,'Striped negative lead below',10)
line(580,273,580,300); ground(580,300)
wire([(59,490),(1148,490)])
text(420,511,'GND: common 0V, not a separate earth connection',11,True)
ground(145,490); tp(170,490,'TP0'); circle(145,490)

rect(1000,170,130,140,fill='#f5f8fa')
text(1065,190,'U3A A4988',13,True,anchor='middle')
text(1012,209,'VMOT',12,True,RED)
# Redraw termination so no wire extends through the block.
# The block masks the previously drawn power wire; line to its boundary remains.
line(920,205,1000,205,RED)
wire([(1148,490),(1148,290),(1130,290)])
text(1118,294,'GND (VMOT)',11,anchor='end')
text(1065,242,'Motor supply',11,anchor='middle')
text(1065,261,'C1 stays nearby',10,True,anchor='middle')
text(825,330,'Route VMOT / C1 / return as a short loop.',11,True)
text(825,348,'Motor current returns straight to J1-2.',11)

rect(245,340,250,110,fill='#f5f8fa')
text(370,363,'U1  DROK BUCK',14,True,anchor='middle')
pin(205,385,245,'IN+',257); wire([(205,385),(205,205)]); circle(205,205)
pin(205,425,245,'IN-',257); line(205,425,205,490); circle(205,490)
pin(495,385,535,'OUT+',482,'end'); text(520,407,'+5_BUCK',10,True,GREEN)
pin(495,425,535,'OUT-',482,'end'); line(535,425,535,490); circle(535,490)
text(370,399,'Adjust to 5.00V',12,True,anchor='middle')
text(370,420,'Non-isolated: IN- = OUT-',10,anchor='middle')
line(330,450,330,465); line(326,461,334,469); line(326,469,334,461)
text(250,480,'EN left unconnected externally',10)
tp(550,385,'TP2')
line(535,385,600,385,GREEN)
# Diode: triangle-like standard diode outline with cathode bar; label physical stripe.
line(600,385,616,385,GREEN)
wire([(616,375),(616,395),(633,385),(616,375)])
line(635,373,635,397); line(635,373,640,373); line(630,397,635,397)
line(635,385,705,385,GREEN)
text(622,342,'D1  1N5819',12,True,anchor='middle')
text(602,365,'A',10); text(643,365,'K / stripe',10)
text(622,416,'Stripe faces XIAO',11,True,anchor='middle')
circle(705,385,3,None); circle(745,385,3,None)
line(708,382,738,366)
text(725,337,'JP1',12,True,anchor='middle')
text(725,354,'REMOVABLE LINK',9,True,anchor='middle')
line(748,385,870,385,GREEN); tp(815,385,'TP3')
rect(870,360,245,90,fill='#f5f8fa')
text(993,381,'U2A  XIAO ESP32-C3',13,True,anchor='middle')
text(882,401,'5V / VBUS',11,True)
# pin entry at y385 is labeled slightly lower for title clearance.
text(882,435,'GND',11)
line(850,431,870,431); line(850,431,850,490); circle(850,490)
text(1000,435,'3V3 OUT',11,True)
wire([(1115,431),(1140,431),(1140,470)])
net(1000,478,'+3V3 (sheet 2)',BLUE)
text(40,548,'USB / EXTERNAL POWER RULE',13,True,RED)
text(40,570,'USB plugged in: JP1 OPEN. Standalone from 12V: USB unplugged, JP1 CLOSED. Change JP1 only with all power off.',12,True)
text(40,589,'The diode blocks backfeed into the buck; it is not a complete two-source power selector or 12V overvoltage protector.',11)

# Source distribution inset.
rect(35,612,1120,165,fill='#f5f8fa',stroke='#bdccd6')
text(50,634,'SUPPLY DISTRIBUTION - branch fuses before long cables',12,True)
text(50,660,'ALITOVE 12V / 6A',11,True)
line(180,655,215,655,RED); rect(215,648,45,14); text(237,643,'F0',10,True,anchor='middle')
text(237,682,'7.5A existing*',10,anchor='middle'); line(260,655,330,655,RED)
line(330,655,330,750,RED)
for i,yy in enumerate([655,685,715,745]):
    circle(330,yy); line(330,yy,380,yy,RED); rect(380,yy-6,35,12)
    text(397,yy-9,'F'+str(i+1),9,True,anchor='middle'); line(415,yy,505,yy,RED)
    text(515,yy+4,f'Station {i+1}: positive conductor to J1-1; fuse rating TBD',10)
text(835,658,'Supply negative splits to',11,True)
text(835,677,'each station J1-2.',11)
text(835,705,'* F0 is recorded, not approved',10,True,RED)
text(835,722,'for unknown wire sizes.',10)
text(835,742,'6A total capacity still needs testing.',10)
finish(1)

header(2,'Control circuit, switch, and motor','U2B and U3B are the SAME physical boards as U2A/U3A on sheet 1. No extra ESP32 or driver is implied.')
rect(40,218,245,215,fill='#f5f8fa'); text(162,244,'U2B  XIAO ESP32-C3',14,True,anchor='middle')
rect(650,150,260,455,fill='#f5f8fa'); text(780,178,'U3B  A4988 CARRIER',14,True,anchor='middle')
text(780,198,'Use printed carrier pin names',11,anchor='middle')

# Power logic: one vertical bus ties VDD, RESET and SLEEP.
net(420,140,'+3V3 from XIAO',BLUE)
wire([(440,145),(440,230),(650,230)],BLUE)
text(664,234,'VDD',12,True)
wire([(440,230),(440,460),(650,460)],BLUE)
line(440,490,650,490,BLUE); line(440,460,440,490,BLUE)
for yy in [230,460]: circle(440,yy)
text(664,464,'RESET (LOW = reset)',12)
text(664,494,'SLEEP (LOW = sleep)',12)
tp(520,230,'TP4')

# Signals cross 3V3 bus WITHOUT dots. gap bridge drawn at crossings by white overlay.
for yy,label,name in [(280,'D1 / GPIO3','STEP'),(330,'D2 / GPIO4','DIR'),(380,'D3 / GPIO5','ENABLE')]:
    text(272,yy+4,label,12,True,anchor='end')
    line(285,yy,433,yy)
    # wire hop over power bus, drawn as segmented upper arch
    wire([(433,yy),(436,yy-7),(444,yy-7),(447,yy),(650,yy)])
    text(664,yy+4,name,12,True)
text(300,259,'Crossings without dots do not connect.',10,color=GRAY)

# Named-net branches avoid ambiguous crossings through resistor bodies.
for yy,name in [(280,'STEP'),(330,'DIR'),(380,'ENABLE')]: net(485,yy,name)
text(300,525,'BIAS RESISTORS (same named nets)',10,True)
res(330,550,True,'10k','R1'); net(310,550,'+3V3',BLUE)
text(306,618,'ENABLE',10,True,BLUE)
res(440,550,True,'10k','R2'); net(420,550,'STEP',BLUE); ground(440,600)
res(550,550,True,'10k','R3'); net(530,550,'DIR',BLUE); ground(550,600)
text(300,683,'R1 holds ENABLE HIGH (disabled).',10,True)
text(300,701,'R2/R3 hold STEP/DIR LOW at boot.',10)

# Fullstep & grounds, separate labeled ground ends prevent busy crossings.
for yy,name in [(525,'MS1'),(550,'MS2'),(575,'MS3')]:
    line(610,yy,650,yy); text(664,yy+4,name,12)
line(610,525,610,620); circle(610,550); circle(610,575); ground(610,620)
text(480,650,'All three LOW = full-step',11)
text(780,640,'Both GND pins connect to common GND.',11,True,anchor='middle')
text(780,659,'VMOT and its GND are on sheet 1.',11,anchor='middle')
line(780,605,780,615); ground(780,615)
text(780,593,'GND (beside VDD)',11,anchor='middle')

# Motor: terminal pair outputs and independent coil symbols.
for yy,name in [(270,'1A'),(335,'1B'),(430,'2A'),(495,'2B')]:
    text(896,yy+4,name,12,True,anchor='end'); line(910,yy,1040,yy)
    circle(985,yy,3,None)
text(970,235,'J2  MOTOR',12,True)
text(1040,217,'M1  NEMA17',13,True)
def coil(x,y,h):
    for k in range(4):
        ya=y+k*h/4; yb=ya+h/4
        p=C.beginPath(); p.moveTo(x,H-ya); p.curveTo(x+22,H-ya,x+22,H-yb,x,H-yb)
        C.setStrokeColor(HexColor(INK)); C.drawPath(p)
        svg.append(f'<path d="M{x} {ya} C{x+22} {ya} {x+22} {yb} {x} {yb}" fill="none" stroke="{INK}" stroke-width="1.5"/>')
coil(1040,270,65); coil(1040,430,65)
text(1070,308,'Coil A',11,True); text(1070,468,'Coil B',11,True)
text(950,540,'No motor wire goes to',11)
text(950,558,'+12V or GND directly.',11,True)

# Home input with optional external resistor on a named +3V3 net.
text(55,420,'D10 / GPIO10',12,True)
line(125,433,125,600); circle(125,555)
line(125,555,200,555); res(200,505,True,'10k','R4'); net(175,498,'+3V3',BLUE)
circle(125,600,4,None); text(137,605,'J3-1 / NC',11)
line(125,604,125,620); circle(125,620,3,None)
line(125,620,145,650); circle(145,650,3,None)
text(175,636,'S1 KW12-3',12,True)
text(175,655,'NC closed at rest',10)
line(145,654,145,680); ground(145,680); text(175,681,'COM -> GND (J3-2)',10)
text(45,719,'NO unused. INPUT_PULLUP in firmware.',10)
text(45,738,'R4 is an added external pull-up; the earlier test used only the ESP32 internal pull-up. Short/open switch detection is not equivalent:',11)
text(45,758,'open wire reads STOP; a short to GND can falsely read READY. Test both switch states and unplug detection before motion.',11,True)
finish(2)

header(3,'Connection ledger and meter checks','This sheet is the exact connectivity reference. Net names repeat across sheets. Measure at labeled test points rather than crowded pins.')
table(35,130,1120,['NET / FUNCTION','ALL CONNECTED POINTS'],[
('+12_STATION','J1-1; buck IN+; A4988 VMOT; C1 positive; TP1'),
('GND / 0V','J1-2; buck IN-/OUT-; XIAO GND; both A4988 GND pins; C1 negative; TP0'),
('GND (continued)','A4988 MS1/MS2/MS3; R2/R3 lower ends; switch COM (J3-2)'),
('+5_BUCK','Buck OUT+; D1 anode (unstriped); TP2'),
('DIODE OUTPUT','D1 cathode (striped); JP1 buck-side contact'),
('XIAO_5V','JP1 XIAO-side contact; XIAO 5V/VBUS; TP3 (USB VBUS is on this board net)'),
('+3V3','XIAO 3V3 OUT; A4988 VDD/RESET/SLEEP; R1/R4 upper ends; TP4'),
('STEP','XIAO D1 / GPIO3; A4988 STEP; R2 upper end'),
('DIR','XIAO D2 / GPIO4; A4988 DIR; R3 upper end'),
('ENABLE','XIAO D3 / GPIO5; A4988 ENABLE; R1 lower end'),
('HOME_NC','XIAO D10 / GPIO10; switch NC (J3-1); R4 lower end'),
('MOTOR OUTPUTS','1A/1B to one measured coil pair; 2A/2B to the other. No common rail connection.')
],[180,940],rowh=28,size=11)

text(35,526,'POWER MODES - JP1 disconnects only the external positive feed; ground remains common.',13,True)
table(35,540,1120,['MODE','USB','12V','JP1','RESULT'],[
('USB logic / upload','Connected','Off','OPEN','XIAO + driver logic powered; VMOT off'),
('USB motor bench test','Connected','On','OPEN','USB powers logic; 12V powers motor and unloaded buck'),
('Standalone station','Unplugged','On','CLOSED','Buck powers logic; 12V powers motor'),
('Not allowed in this revision','Connected','On','CLOSED','Two sources meet on VBUS; do not use this configuration')
],[215,110,85,100,610],rowh=28,size=11)

text(35,714,'DC VOLTAGE CHECKS: black probe at TP0 (J1 negative), red at the selected test point.',12,True)
text(35,736,'TP1: ~12V with supply on. TP2: 5.00V before diode. TP3: ~USB voltage in USB mode, lower than TP2 through diode standalone.',11)
text(35,756,'TP4: ~3.3V. RESET/SLEEP: ~3.3V. ENABLE: ~3.3V idle, near 0V during jog. HOME: near 0V released, ~3.3V pressed/open.',11)
text(35,778,'A normal meter cannot reliably resolve the short STEP pulse or the 0.4-second ENABLE window. Use scope/logic analyzer if needed.',11)
finish(3)

header(4,'Audit findings and controlled restart','Schematic reviewed against manufacturer references. Actual perfboard, motor rating, fuse sizing, and suspect components remain unverified.')
text(35,142,'WHAT IS VERIFIED / WHAT IS NOT',14,True)
items=[
('Correct topology','12V to VMOT and buck input in parallel; 3.3V to driver VDD/RESET/SLEEP; one common ground.'),
('Reported measurements','VDD, RESET and SLEEP each 3.3V; VMOT-to-adjacent-GND read 0V; later XIAO heated and lost USB recognition.'),
('Diagnosis not established','No proof of short location or failed part. VMOT=0 can be missing feed, missing return, fuse, supply or probe issue.'),
('USB correction','JP1 OPEN for USB. External diode alone does not isolate computer VBUS from all external-power conditions.'),
('Protection limitation','DROK family lists no output overvoltage or input reverse-polarity protection. D1 is not an overvoltage clamp.'),
('New items shown','JP1 disconnect and R2/R3/R4 = 10k resistors are proposed additions; presence in your build is not confirmed.'),
('No fixed Vref yet','I_limit = Vref / (8 x Rsense). Need actual motor phase-current rating and both driver sense-resistor markings.'),
('No approved fuse value','F0=7.5A is existing stock. F1-F4 must protect branch wire/connectors; select with current and fuse-curve data.'),
('Later upgrade only','Reserve XIAO D4/GPIO6 and D5/GPIO7 for encoder I2C. Exact encoder board power/pull-ups are not approved here.')]
table(35,155,1120,['FINDING','DETAIL'],items,[185,935],rowh=30,size=10.5)

text(35,490,'RESTART SEQUENCE - leave the suspect XIAO disconnected throughout passive checks.',14,True,RED)
steps=[
'1. Remove USB and 12V. Confirm capacitor voltage has fallen near 0V before resistance tests; do not short it with a tool.',
'2. Isolate/remove suspect XIAO and driver. Check bare wiring against sheet 3; inspect both sides for bridges and shared copper strips.',
'3. Check intended continuity, including both driver ground socket contacts to J1-2. Check separate power rails for unintended shorts.',
'4. With electronics disconnected, test supply before/after each fuse against supply negative. Test buck alone and verify 5.00V at TP2.',
'5. Use a current-limited lab supply for fault finding if available. A 7.5A fuse is not fast semiconductor protection or overvoltage protection.',
'6. Verify a known-good XIAO separately. JP1 open: add checked logic wiring/driver incrementally, powering off before every change.',
'7. With EN held HIGH, verify TP1/TP4 and set Vref from confirmed motor/Rsense data. Never guess based on screw direction.',
'8. Power off; connect checked coil pairs. Run only the short, unloaded jog and switch test. No suspended load or room operation.'
]
for i,s in enumerate(steps): text(35,514+i*23,s,10.5)
text(35,707,'SOURCE REFERENCES (manufacturer documentation; accessed 2026-10-16 America/Chicago)',11,True)
sources=[
('Seeed C3 pin map and board schematic','https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/'),
('A4988 carrier guidance / Allegro IC datasheet','https://www.pololu.com/product/1182 | https://www.pololu.com/file/0J450/A4988.pdf'),
('DROK matching module family (exact revision unverified)','https://www.droking.com/10pcs-dc-buck-converter-5v-voltage-regulator')]
for i,(name,url) in enumerate(sources):
    text(35,728+i*22,name,9,True); text(365,728+i*22,url,9)
finish(4)
C.save()
print(OUT / 'RoomCleaner_Station_RevC.pdf')
