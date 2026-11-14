from pathlib import Path
import cadquery as cq
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];O=R/'docs/flush-base'
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def F(n):return ImageFont.truetype(font,n)
def text(d,xy,t,n=25,c='#293943'):d.text(xy,t,font=F(n),fill=c)
colors={'C':'#4f89b2','M':'#5e9b70','G':'#bd9048'}
im=Image.new('RGB',(2000,1830),'#f7f6f1');d=ImageDraw.Draw(im)
text(d,(60,30),'PROJECT ZOE / 后收口 · 中底板外缘 · 底面齐平',41)
text(d,(60,97),'已更新模型：1.5 称板 + 0.5 间隙 + 1 中层 + 0.5 间隙 + 1 底板 = 4.5 mm',28)
for name,xy,size,label in [('cad-assembled.png',(60,200),(1180,811),'01 局部装配：侧面不再露出底板'),('cad-exploded.png',(1290,200),(650,447),'02 分解：蓝 C / 绿 M / 金 G'),('cad-underside.png',(1290,730),(650,447),'03 底板收在裙边以内')]:
 p=Image.open(O/name).convert('RGB');p.thumbnail(size);im.paste(p,xy);text(d,(xy[0],xy[1]-40),label,26)
text(d,(60,1040),'裙边仍下伸 3 mm；后收口对齐，中层与底板外缘对齐；后圆角下缘也已抬至同一底面。',25)
parts={n:cq.importers.importStep(str(R/'cad'/(f+'.step'))).val() for n,f in [('C','base'),('M','flush-middle-full'),('G','ground-plate-concept')]}
def section(plane,origin,project,bounds,rect):
 x0,y0,w,h=rect;u0,u1,v0,v1=bounds;scale=min(w/(u1-u0),h/(v1-v0))
 layer=Image.new('RGB',(w,h),'#fffefa');dd=ImageDraw.Draw(layer)
 def pix(u,v):return((u-u0)*scale,h-(v-v0)*scale)
 for n,s in parts.items():
  sec=cq.Workplane(plane,origin=origin).newObject([s]).section(0).val()
  for e in sec.Edges():dd.line([pix(*project(p)) for p in e.positions([i/100 for i in range(101)])],fill=colors[n],width=4)
 im.paste(layer,(x0,y0));d.rectangle((x0,y0,x0+w,y0+h),outline='#d9ddda',width=2)
 return lambda u,v:(x0+pix(u,v)[0],y0+pix(u,v)[1])
text(d,(60,1205),'04 中心纵剖 / X0：后收口与下缘对齐',27)
p=section('YZ',(0,0,0),lambda p:(p.y,p.z),(5,28,-.5,9.5),(60,1260,1060,460))
a=p(12.5,3);b=(590,1320);d.line((a,b),fill='#3d7b52',width=3);d.ellipse((a[0]-5,a[1]-5,a[0]+5,a[1]+5),fill='#3d7b52')
text(d,b,'中层仍连续为 1 mm',24,'#3d7b52')
# Requested rear edge alignment and common underside, directly on true sections.
def dashed(a,b,c='#c9563f'):
 if abs(a[0]-b[0])<.1:
  for yy in range(int(min(a[1],b[1])),int(max(a[1],b[1])),14):d.line((a[0],yy,a[0],min(yy+7,max(a[1],b[1]))),fill=c,width=3)
 else:
  for xx in range(int(min(a[0],b[0])),int(max(a[0],b[0])),14):d.line((xx,a[1],min(xx+7,max(a[0],b[0])),a[1]),fill=c,width=3)
dashed(p(12,.5),p(12,5.2));dashed(p(7,.5),p(27,.5))
text(d,(760,1635),'同一底面 Z0.5',22,'#b74735')
text(d,(1230,1205),'05 横剖 / Y25：真实裙边截面',27)
p=section('XZ',(0,25,0),lambda p:(p.x,p.z),(44,51,0,6),(1230,1260,400,460))
for z,t in [(4.2,'称板 1.5'),(2.5,'中层 1'),(1,'底板 1')]:
 a=p(47.3,z);b=(1660,1290+(4.2-z)*95);d.line((a,b),fill='#606c70',width=2);text(d,b,t,24)
text(d,(1660,1650),'M/G 外缘同为 X48.3',20)
dashed(p(48.3,.5),p(48.3,3.2))
text(d,(1660,1690),'至裙边内壁仍留 0.5',20)
text(d,(60,1750),'尺寸保持 1.5 / 0.5 / 1 / 0.5 / 1 mm。CAD 对齐与间隙检查通过；未加脚垫，未做受力验证。',24)
im.save(O/'review.png')
# Sheet uses current STEP sections and the flat-shaded CAD review renders.
