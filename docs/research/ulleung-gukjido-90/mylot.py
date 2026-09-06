# -*- coding: utf-8 -*-
import json, math
from PIL import Image, ImageDraw, ImageFont
W_="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
g=json.load(open(f"{W_}/geo_30.json")); a,b,s=g["a"],g["b"],g["s"]
def merY(lat): return math.degrees(math.log(math.tan(math.pi/4+math.radians(lat)/2)))
PPM=s/88352.0
A0=(a+s*130.908918, b-s*merY(37.482490))
im=Image.open(f"{W_}/base/30_dodong_cad_30m.webp").convert("RGB")
R=int(105*PPM); SC=2
box=(int(A0[0]-R*1.05), int(A0[1]-R*1.15), int(A0[0]+R*0.85), int(A0[1]+R*0.55))
crop=im.crop(box).resize(((box[2]-box[0])*SC,(box[3]-box[1])*SC), Image.LANCZOS)
W,H=crop.size
ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov,"RGBA")
F=lambda n,w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf",n)
f24,f28,f34,f40=F(24,"SemiBold"),F(28,"SemiBold"),F(34),F(40,"ExtraBold")
def txt(xy,t,fo,fill=(255,255,255),hw=5,anchor="mm"):
    x,y=xy
    for dx in range(-hw,hw+1):
        for dy in range(-hw,hw+1):
            if dx*dx+dy*dy<=hw*hw: d.text((x+dx,y+dy),t,font=fo,fill=(0,0,0,245),anchor=anchor)
    d.text((x,y),t,font=fo,fill=fill+(255,),anchor=anchor)
ax,ay=(A0[0]-box[0])*SC,(A0[1]-box[1])*SC
P=PPM*SC
for r,col,al in ((90,(255,235,60),26),(60,(255,150,30),42),(35,(235,40,40),64)):
    RR=r*P; d.ellipse([ax-RR,ay-RR,ax+RR,ay+RR],fill=col+(al,),outline=col+(245,),width=8)
    txt((ax, ay-RR+30), f"{r} m", f28, col)
# 사장님 부지 (원본 image30 px 기준 라벨 판독 위치)
LOT=[(1176,382,"42-3","364 ㎡"),(1176,437,"42-1","208 ㎡")]
for x,y,name,ar in LOT:
    px,py=(x-box[0])*SC,(y-box[1])*SC
    dm=math.hypot(px-ax,py-ay)/P
    bnd = "1등급" if dm<=35 else "2등급" if dm<=60 else "3등급"
    c=(255,60,60) if dm<=35 else (255,170,40)
    RR=42
    d.ellipse([px-RR,py-RR,px+RR,py+RR],fill=(0,220,255,110),outline=(0,225,255,255),width=8)
    d.line([(px,py),(px+150,py-120)],fill=(0,225,255,255),width=6)
    txt((px+160,py-152), f"{name}  {ar}", f40, (120,240,255), anchor="lm")
    txt((px+162,py-112), f"갱구 {dm:.0f} m → {bnd}", f34, c, anchor="lm")
d.ellipse([ax-30,ay-30,ax+30,ay+30],fill=(255,60,60,255),outline=(0,0,0,255),width=7)
txt((ax,ay-2),"A",f34,(0,0,0),0)
txt((ax+70,ay+40),"A갱구",f34,(255,160,160),anchor="lm")
lines=["사장님 부지 — 도동리 41-2 / 42-1 / 42-3  합계 744 ㎡",
 "42-1 (208 ㎡)  갱구 약 33 m → 1등급 · 갱문·개착부 · 전면 매수 (경계선상)",
 "42-3 (364 ㎡)  갱구 약 43 m → 2등급 · 가설야드·절취사면",
 "41-2 (172 ㎡)  지적도상 라벨 미확인 — 42 인접이면 2등급 권역",
 "황색대 = 주거지역 계열로 읽힘(분홍=상업, 연녹=녹지) → 단가의 최대 변수",
 "지번 대응은 판독 추정. 토지이용계획확인원으로 확정할 것"]
ws=[d.textbbox((0,0),L,font=f28)[2] for L in lines]; lh=f28.size+13
d.rounded_rectangle([26,26,26+max(ws)+32,26+lh*len(lines)+22],14,fill=(10,12,18,235),outline=(0,225,255,170),width=3)
for i,L in enumerate(lines): d.text((42,38+i*lh),L,font=f28,fill=(255,255,255,255))
out=Image.alpha_composite(crop.convert("RGBA"),ov).convert("RGB")
out=out.resize((W//2,H//2),Image.LANCZOS)
out.save(f"{W_}/out/A2_mylot.jpg",quality=94); print("ok",out.size)
