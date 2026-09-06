# -*- coding: utf-8 -*-
import json, math
from PIL import Image, ImageDraw, ImageFont
W_="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
g=json.load(open(f"{W_}/geo_03.json")); a,b,s=g["a"],g["b"],g["s"]
def merY(lat): return math.degrees(math.log(math.tan(math.pi/4+math.radians(lat)/2)))
SC=2
def P(lo,la): return ((a+s*lo)*SC,(b-s*merY(la))*SC)
PPMs=(s/88352.0)*SC
im=Image.open(f"{W_}/base/03_dodong_sat_50m.webp").convert("RGB")
im=im.resize((im.size[0]*SC,im.size[1]*SC),Image.LANCZOS)
# A갱구 주변으로 크롭 (원본 px 기준 x520-1500, y120-900)
CX,CY,CW,CH=520*SC,110*SC,980*SC,790*SC
A0=P(130.908918,37.482490); B0=P(130.907939,37.482038)
ov=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(ov,"RGBA")
F=lambda n,w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf",n)
f28,f34,f40,f50=F(28,"SemiBold"),F(34),F(40),F(50,"ExtraBold")
def txt(xy,t,fo,fill=(255,255,255),hw=5,anchor="mm"):
    x,y=xy
    for dx in range(-hw,hw+1):
        for dy in range(-hw,hw+1):
            if dx*dx+dy*dy<=hw*hw: d.text((x+dx,y+dy),t,font=fo,fill=(0,0,0,245),anchor=anchor)
    d.text((x,y),t,font=fo,fill=fill+(255,),anchor=anchor)
def pr(o,brg,m): return (o[0]+math.sin(math.radians(brg))*m*PPMs, o[1]-math.cos(math.radians(brg))*m*PPMs)
def arw(p1,p2,col,w,head=40):
    d.line([p1,p2],fill=col,width=w); ang=math.atan2(p2[1]-p1[1],p2[0]-p1[0])
    for sg in(1,-1):
        aa=ang+sg*math.radians(157)
        d.line([p2,(p2[0]+head*math.cos(aa),p2[1]+head*math.sin(aa))],fill=col,width=w)
def dash(p1,p2,col,w,on=30,off=20):
    x1,y1=p1;x2,y2=p2;L=math.hypot(x2-x1,y2-y1);ux,uy=(x2-x1)/L,(y2-y1)/L;t=0
    while t<L:
        e=min(t+on,L); d.line([x1+ux*t,y1+uy*t,x1+ux*e,y1+uy*e],fill=col,width=w); t+=on+off

# 터널에서 나오는 진행방향 193.1° (저동→도동)
IN=pr(A0,13.1,95)
d.line([IN,A0],fill=(0,0,0,200),width=30); arw(IN,A0,(255,80,80,255),16,44)
txt(pr(A0,13.1,112),"A터널 진출 193.1°",f34,(255,170,170))

# ① 본선 : 서남서 239.8° → B터널·도동길
T1=pr(A0,239.8,100)
d.line([A0,T1],fill=(0,0,0,200),width=34); arw(A0,T1,(40,235,120,255),18,50)
txt(pr(A0,239.8,58),"① 본선",f50,(120,255,175))
txt(pr(A0,246,104),"→ B터널(사동) · 도동길",f34,(150,255,195))
txt(pr(A0,255,60),"절선각 46.7° · R≈120~150 m",f28,(150,255,195))

# ② 다리 하부 : 169° 차단
BC=pr(A0,169,44); T2=pr(A0,169,52)
d.line([A0,T2],fill=(0,0,0,200),width=30); d.line([A0,T2],fill=(255,60,60,255),width=15)
R=34
for dx,dy in ((1,1),(1,-1)):
    d.line([(T2[0]-R*dx,T2[1]-R*dy),(T2[0]+R*dx,T2[1]+R*dy)],fill=(255,40,40,255),width=17)
d.ellipse([T2[0]-R-14,T2[1]-R-14,T2[0]+R+14,T2[1]+R+14],outline=(255,40,40,255),width=11)
dash(pr(BC,258,30),pr(BC,78,30),(255,214,0,255),15)
txt(pr(A0,182,78),"② 다리 하부 — 차단",f40,(255,120,120))
txt(pr(A0,183,96),"형하 3.2 m · 버스 3.5~3.8 m · 공사장비 불가",f28,(255,180,180))
txt(pr(BC,78,64),"보행교(강아치)",f28,(255,225,90))

# ③ 우회 : 부두 북측 가장자리 → 부두 동측 → 여객선터미널
W1=pr(A0,120,42); W2=pr(A0,143,86); W3=pr(A0,152,132)
for p1,p2 in ((A0,W1),(W1,W2),(W2,W3)):
    d.line([p1,p2],fill=(0,0,0,190),width=26)
    dash(p1,p2,(255,150,20,255),14)
arw(W2,W3,(255,150,20,255),14,40)
txt(pr(A0,127,116),"③ 우회 → 여객선터미널",f40,(255,190,90))
txt(pr(A0,128,134),"부두 북측 가장자리 경유 · 실측 296 m",f28,(255,215,150))
txt(pr(A0,129,152),"현재 폭 5~6 m → 확폭 시 A측 편입 확대",f28,(255,215,150))

# 갱구
d.ellipse([A0[0]-32,A0[1]-32,A0[0]+32,A0[1]+32],fill=(255,70,70,255),outline=(0,0,0,255),width=7)
txt((A0[0],A0[1]-2),"A",f50,(0,0,0),0)
d.ellipse([B0[0]-26,B0[1]-26,B0[0]+26,B0[1]+26],fill=(90,180,255,255),outline=(0,0,0,255),width=6)
txt((B0[0],B0[1]-2),"B",f40,(0,0,0),0)

x,y=CX+30,CY+30
lines=["A갱구 통행 분배 — 다리는 ②에만 걸린다",
 "① 본선  239.8°  B터널(사동)·도동길   다리 무관 (등 뒤)",
 "② 남남동 169°  다리 하부            형하 3.2 m — 노선에서 배제",
 "③ 우회  북동 가장자리 296 m         여객선터미널·방파제",
 "선형만 보면 ②가 순방향(절선각 24.1°)이지만 통과 불가.",
 "그래서 본선은 46.7° 꺾어 ①로 뺀다."]
ws=[d.textbbox((0,0),L,font=f34)[2] for L in lines]; lh=f34.size+14
d.rounded_rectangle([x,y,x+max(ws)+34,y+lh*len(lines)+24],14,fill=(10,12,18,232),outline=(255,255,255,145),width=3)
for i,L in enumerate(lines): d.text((x+17,y+12+i*lh),L,font=f34,fill=(255,255,255,255))

out=Image.alpha_composite(im.convert("RGBA"),ov).convert("RGB").crop((CX,CY,CX+CW,CY+CH))
out=out.resize((CW//2,CH//2),Image.LANCZOS)
out.save(f"{W_}/out/71_flow.jpg",quality=93); print("ok",out.size)
