# -*- coding: utf-8 -*-
import json, math
from PIL import Image, ImageDraw, ImageFont
W_="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
g=json.load(open(f"{W_}/geo_30.json")); a,b,s=g["a"],g["b"],g["s"]
def merY(lat): return math.degrees(math.log(math.tan(math.pi/4+math.radians(lat)/2)))
SC=2
def P(lo,la): return ((a+s*lo)*SC, (b-s*merY(la))*SC)
PPM = s/88352.0            # px per metre (native)
PPMs = PPM*SC

im=Image.open(f"{W_}/base/30_dodong_cad_30m.webp").convert("RGB")
im=im.resize((im.size[0]*SC, im.size[1]*SC), Image.LANCZOS); W,H=im.size
ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov,"RGBA")
F=lambda n,w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf",n)
f26,f30,f36,f44=F(26,"SemiBold"),F(30),F(36),F(44,"ExtraBold")
def txt(xy,t,fo,fill=(255,255,255),hw=4,anchor="mm"):
    x,y=xy
    for dx in range(-hw,hw+1):
        for dy in range(-hw,hw+1):
            if dx*dx+dy*dy<=hw*hw: d.text((x+dx,y+dy),t,font=fo,fill=(0,0,0,240),anchor=anchor)
    d.text((x,y),t,font=fo,fill=fill+(255,),anchor=anchor)

A0=P(130.908918,37.482490); B0=P(130.907939,37.482038)
G1,G2,G3 = 35.0, 60.0, 90.0

# ---- 등급 밴드 (3→2→1 순으로 덮어 그림)
for O in (A0,B0):
    for r,fill,out,wd in ((G3,(255,235,60,34),(255,225,40,215),6),
                          (G2,(255,150,30,60),(255,140,20,235),7),
                          (G1,(235,40,40,96),(255,50,50,255),9)):
        R=r*PPMs; d.ellipse([O[0]-R,O[1]-R,O[0]+R,O[1]+R], fill=fill, outline=out, width=wd)

# ---- 부두 집산로 회랑 (A0-B0, 폭 ±12 m)
ang=math.atan2(B0[1]-A0[1], B0[0]-A0[0]); nx,ny=-math.sin(ang)*12*PPMs, math.cos(ang)*12*PPMs
d.polygon([(A0[0]+nx,A0[1]+ny),(B0[0]+nx,B0[1]+ny),(B0[0]-nx,B0[1]-ny),(A0[0]-nx,A0[1]-ny)],
          fill=(40,150,255,80), outline=(80,190,255,240))

# ---- 필지 라벨 판독 좌표(원본 px) → 등급 자동 판정
LOTS=[(1070,602,"38"),(1075,632,"5잡"),(1055,740,"4잡"),(1140,533,"12"),(1148,575,"13"),
 (1215,620,"5"),(1265,655,"10"),(1315,715,"6임"),(1060,495,"11"),(1215,450,"17"),
 (1170,405,"42"),(1105,335,"9"),(1170,365,"3"),(985,355,"8"),(905,515,"640"),(920,600,"640-1"),
 (900,687,"84"),(838,780,"85잡"),(760,840,"89"),(884,948,"89"),(740,960,"94잡"),
 (700,780,"95"),(650,850,"95"),(762,1043,"110"),(760,1100,"2임"),(773,720,"100"),
 (718,675,"107"),(612,715,"106"),(568,745,"111"),(830,600,"99"),(875,605,"97"),(780,590,"102")]
COL={1:(255,60,60),2:(255,165,30),3:(255,235,70),0:(150,150,150)}
band_lots={1:[],2:[],3:[]}
for x,y,name in LOTS:
    p=(x*SC,y*SC)
    dm=min(math.hypot(p[0]-A0[0],p[1]-A0[1]), math.hypot(p[0]-B0[0],p[1]-B0[1]))/PPMs
    side = "A" if math.hypot(p[0]-A0[0],p[1]-A0[1]) < math.hypot(p[0]-B0[0],p[1]-B0[1]) else "B"
    bnd = 1 if dm<=G1 else 2 if dm<=G2 else 3 if dm<=G3 else 0
    c=COL[bnd]
    d.ellipse([p[0]-15,p[1]-15,p[0]+15,p[1]+15], fill=c+(255,), outline=(0,0,0,255), width=4)
    if bnd: band_lots[bnd].append((side,name,round(dm)))

# ---- 갱구
for O,lab,col in ((A0,"A",(255,70,70)),(B0,"B",(90,180,255))):
    d.ellipse([O[0]-34,O[1]-34,O[0]+34,O[1]+34], fill=col+(255,), outline=(0,0,0,255), width=7)
    txt((O[0],O[1]-2),lab,f44,(0,0,0),0)
txt((A0[0]+150,A0[1]-250),"A갱구 (저동 방면)",f36,(255,150,150))
txt((B0[0]-190,B0[1]+250),"B갱구 (사동 방면)",f36,(170,215,255))
M=((A0[0]+B0[0])/2,(A0[1]+B0[1])/2)
txt((M[0]+40,M[1]+96),"부두 집산로 회랑 100 m (관리전환)",f30,(150,215,255))

# ---- 반경 눈금
for O in (A0,B0):
    for r,lab in ((G1,"35"),(G2,"60"),(G3,"90")):
        q=(O[0], O[1]-r*PPMs)
        txt(q, lab+" m", f26, (255,255,255))

def box(xy,lines,fo,anchor="lt",bg=(10,12,18,232),wmul=1.0):
    x,y=xy; ws=[d.textbbox((0,0),L,font=fo)[2] for L in lines]; lh=fo.size+13
    bw,bh=int(max(ws)*wmul)+30,lh*len(lines)+22
    if anchor[0]=="r": x-=bw
    if anchor[1]=="b": y-=bh
    d.rounded_rectangle([x,y,x+bw,y+bh],14,fill=bg,outline=(255,255,255,140),width=3)
    for i,L in enumerate(lines): d.text((x+15,y+11+i*lh),L,font=fo,fill=(255,255,255,255))

def lots(bn, side): return " · ".join(n for sd,n,_ in band_lots[bn] if sd==side) or "—"
box((40,150),[
 "국지도 90호선 도동항 — 토지보상 편입 예상 범위",
 "",
 "■ 1등급  갱구 0~35 m   갱문·개착부 — 전면 매수 (회피 불가)",
 f"    A측 : {lots(1,'A')}",
 f"    B측 : {lots(1,'B')}",
 "■ 2등급  35~60 m       가설야드·절취사면 — 매수 또는 일시사용",
 f"    A측 : {lots(2,'A')}",
 f"    B측 : {lots(2,'B')}",
 "■ 3등급  60~90 m       사면·가설도로·소음진동 — 협의 대상",
 f"    A측 : {lots(3,'A')}",
 f"    B측 : {lots(3,'B')}",
 "■ 회랑   부두 집산로 100 m × 24 m — 항만시설, 관리전환(무상)",
 "",
 "90 m 밖 편입 없음 — 108·109·114·116·118·120대·121·122·124·126·128·130대·140대",
 "주의: B측 2등급은 야드 규모에 좌우된다. 최소 야드(33.6 m)로 압축하면",
 "         106·107·111·99·97·102 가 빠지고, 표준 야드(44.5 m)면 들어온다.",
], f30)
box((W-40,H-40),[
 "면적: 1등급 원 3,848 ㎡/개소 · 2등급 링 7,462 ㎡/개소 · 회랑 2,400 ㎡",
 "지적편집도(30 m) 아핀 정합 RMS 2~3 m · 필지 점은 지번 라벨 위치 기준",
 "노선 미공표 — 전 항목 추정. 토지조서 열람 전까지 확정 아님",
], F(26,"SemiBold"), anchor="rb")

out=Image.alpha_composite(im.convert("RGBA"),ov).convert("RGB").resize((W//2,H//2),Image.LANCZOS)
out.save(f"{W_}/out/61_compensation.jpg",quality=93)
for k in (1,2,3): print(k, band_lots[k])
