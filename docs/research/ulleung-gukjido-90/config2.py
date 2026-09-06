# -*- coding: utf-8 -*-
import json, math
from PIL import Image, ImageDraw, ImageFont
W_ = "/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
g = json.load(open(f"{W_}/geo_03.json")); a,b,s = g["a"],g["b"],g["s"]
def merY(lat): return math.degrees(math.log(math.tan(math.pi/4+math.radians(lat)/2)))
SC = 2
def p(lo,la): return ((a+s*lo)*SC, (b-s*merY(la))*SC)
PPMs = 4.41*SC

im = Image.open(f"{W_}/base/03_dodong_sat_50m.webp").convert("RGB")
im = im.resize((im.size[0]*SC, im.size[1]*SC), Image.LANCZOS)
W,H = im.size
ov = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(ov,"RGBA")
F = lambda n,w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf", n)
f26,f30,f34,f40 = F(26,"SemiBold"),F(30),F(34),F(40,"ExtraBold")

def txt(xy,t,font,fill=(255,255,255),hw=4,anchor="mm"):
    x,y=xy
    for dx in range(-hw,hw+1):
        for dy in range(-hw,hw+1):
            if dx*dx+dy*dy<=hw*hw: d.text((x+dx,y+dy),t,font=font,fill=(0,0,0,235),anchor=anchor)
    d.text((x,y),t,font=font,fill=fill+(255,),anchor=anchor)
def dash(p1,p2,col,w,on=24,off=16):
    x1,y1=p1; x2,y2=p2; L=math.hypot(x2-x1,y2-y1)
    ux,uy=(x2-x1)/L,(y2-y1)/L; t=0.0
    while t<L:
        e=min(t+on,L); d.line([x1+ux*t,y1+uy*t,x1+ux*e,y1+uy*e],fill=col,width=w); t+=on+off
def arrow(p1,p2,col,w,head=30):
    d.line([p1,p2],fill=col,width=w)
    ang=math.atan2(p2[1]-p1[1],p2[0]-p1[0])
    for sg in (1,-1):
        aa=ang+sg*math.radians(158)
        d.line([p2,(p2[0]+head*math.cos(aa),p2[1]+head*math.sin(aa))],fill=col,width=w)
def proj(o,brg,m): return (o[0]+math.sin(math.radians(brg))*m*PPMs, o[1]-math.cos(math.radians(brg))*m*PPMs)
def box(xy,lines,font,anchor="lt",bg=(12,14,20,225)):
    x,y=xy; ws=[d.textbbox((0,0),L,font=font)[2] for L in lines]; lh=font.size+12
    bw,bh=max(ws)+28,lh*len(lines)+20
    if anchor[0]=="r": x-=bw
    if anchor[1]=="b": y-=bh
    d.rounded_rectangle([x,y,x+bw,y+bh],12,fill=bg,outline=(255,255,255,130),width=3)
    for i,L in enumerate(lines): d.text((x+14,y+10+i*lh),L,font=font,fill=(255,255,255,255))

A0 = p(130.908918, 37.482490)
B0 = p(130.907939, 37.482038)
LAND, SEA = 329.8, 149.8          # A0->B0 방위 239.8°의 좌우 법선

# 1) 부두 노면 존치구역 (바다측 밴드) : 주차·하역·보행 전용
poly = [A0, B0, proj(B0,LAND,32), proj(A0,LAND,32)]
d.polygon(poly, fill=(0,220,120,58), outline=(0,255,150,190))
d.line([poly[0],poly[1]], fill=(0,255,150,150), width=4)
C = ((A0[0]+B0[0])/2, (A0[1]+B0[1])/2)
SEAC = proj(C, LAND, 20)
txt((SEAC[0]-210, SEAC[1]+18), "부두 노면 존치", f34, (150,255,205))
txt((SEAC[0]-210, SEAC[1]+60), "지상 구조물 0 · 주차/하역/보행", f26, (190,255,225))

# 2) 348 m 접속부 = 도동항 집산로 (부두 육지측 가장자리, 평면)
R1, R2 = A0, B0
for w,c in ((32,(0,0,0,200)),(20,(255,255,255,255)),(11,(255,120,0,255))):
    d.line([R1,R2], fill=c, width=w)
txt((C[0]-40, C[1]-118), "도동항 집산로 (평면 2차로)", f40, (255,190,110))
txt((C[0]-40, C[1]-72), "확정 접속부 348 m 의 핵심 100 m", f30, (255,215,160))

# 3) 접속점 3개소
for base, brg, m, lab, off in (
    (C,  200, 34, "부두 · 여객 하선 진입",   (-70, 66)),
    (A0, 169, 62, "여객선터미널 방면",       (210, 30)),
    (B0, 318, 58, "도동길 (생활교통만 잔류)", (-40,-46)),
):
    tip = proj(base, brg, m)
    arrow(base, tip, (0,255,150,255), 9, 24)
    txt((tip[0]+off[0], tip[1]+off[1]), lab, f26, (150,255,205))

# 4) 갱구 + 방향
for O,lab,col,brg,nm in ((A0,"A",(255,92,92),13.1,"저동 방면 2.74 km"),
                         (B0,"B",(86,180,255),235.8,"사동 방면 2.70 km")):
    T = proj(O, brg, 165 if lab=="B" else 74)
    d.line([O,T], fill=(0,0,0,190), width=26); arrow(O,T,col+(255,),14,44)
    d.ellipse([O[0]-26,O[1]-26,O[0]+26,O[1]+26], fill=col+(255,), outline=(0,0,0,255), width=5)
    txt((O[0],O[1]-1), lab, f34, (0,0,0), 0)
    M = proj(O, brg, 118 if lab=="B" else 56)
    txt((M[0]+(230 if lab=="A" else 170), M[1]+(-30 if lab=="A" else 0)), nm, f30, col)

# 5) 암반 주차장 병설 후보 (A갱구 배후 절개지)
PK = proj(A0, 355, 12); r = 30*PPMs
d.ellipse([PK[0]-r,PK[1]-r,PK[0]+r,PK[1]+r], fill=(255,214,0,60), outline=(255,214,0,240), width=6)
txt((PK[0]+r+270, PK[1]+30), "가설야드 → 준공 후 주차장 전용", f34, (255,225,90))
txt((PK[0]+r+270, PK[1]+74), "죽도관광 배후 나지 2,344 ㎡ · 해일 침수 밖", f26, (255,238,150))

# 6) 보행교
BC = proj(A0,169,44)
dash(proj(BC,258,26), proj(BC,78,26), (255,214,0,235), 12)
txt((BC[0]+230, BC[1]+46), "보행교(추정)", f26, (255,225,90))

box((36,132), [
 "구성 정정 — 도동항은 통과점이 아니라 결절점",
 "폐기: 부두 상부 고가 통과형 (도동항 분산 목적 미달)",
 "채택: 부두 평면 집산로 + 암반 주차장 병설",
 "① 여객 하선 차량이 부두에서 곧장 집산로 진입",
 "② 100 m 안에서 북(저동)·남(사동) 방향 분기",
 "③ 도동길 통과교통 제거 → 생활교통·보행 전용화",
 "④ 노면 주차 수요를 갱구 배후 암반 주차장으로 흡수",
], f30)
box((W-36,H-36), [
 "네이버 위성(30 m) 아핀 정합 RMS 3.4 m · 로드뷰 4매(2025-11)",
 "노선 미공표 — 전 항목 추정",
], F(26,"SemiBold"), anchor="rb", bg=(12,14,20,205))

out = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB").resize((W//2,H//2), Image.LANCZOS)
out.save(f"{W_}/out/52_node.jpg", quality=92); print("ok")
