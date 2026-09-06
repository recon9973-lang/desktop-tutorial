# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
W_="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
F=lambda n,w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf",n)
f22,f26,f30,f38,f46=F(22,"SemiBold"),F(26,"SemiBold"),F(30),F(38),F(46,"ExtraBold")
W,H=1760,1180
im=Image.new("RGB",(W,H),(17,19,24)); d=ImageDraw.Draw(im,"RGBA")
BG_PANEL=(28,31,38); ROAD=(72,76,86); BLD=(96,104,122); TAKE=(214,54,54)

def hatch(x0,y0,x1,y1,col,step=16,w=3):
    for k in range(int(-(y1-y0)), int(x1-x0), step):
        d.line([max(x0,x0+k), y0+max(0,-k), min(x1,x0+k+(y1-y0)), y0+min(y1-y0,(x1-x0)-k)], fill=col, width=w)

def panel(ox,oy,title,sub,road_m,need_m,note,ncol):
    PW,PH=800,880
    d.rounded_rectangle([ox,oy,ox+PW,oy+PH],18,fill=BG_PANEL,outline=(255,255,255,55),width=3)
    d.text((ox+28,oy+24),title,font=f38,fill=(255,255,255))
    d.text((ox+28,oy+74),sub,font=f26,fill=ncol)
    SC=48                      # px per metre
    cx=ox+PW//2; base=oy+560
    half=road_m*SC/2
    # 건물 (양쪽) — 도로경계에 바짝
    for sgn in (-1,1):
        bx0=cx+sgn*half; bx1=cx+sgn*(half+150/SC*SC/1)
        x0,x1=sorted([bx0, bx0+sgn*160])
        d.rectangle([x0,base-260,x1,base],fill=BLD)
        d.rectangle([x0,base-260,x1,base],outline=(190,200,220,190),width=3)
        for r in range(3):
            for c in range(2):
                wx=x0+22+c*70; wy=base-235+r*78
                d.rectangle([wx,wy,wx+46,wy+50],fill=(40,46,58))
    # 노면
    d.rectangle([cx-half,base-14,cx+half,base],fill=ROAD)
    d.line([cx-half,base-7,cx+half,base-7],fill=(230,220,120,220),width=4)
    # 확폭 편입분
    if need_m>0:
        t=need_m*SC/2
        for sgn in (-1,1):
            x0,x1=sorted([cx+sgn*half, cx+sgn*(half+t)])
            d.rectangle([x0,base-260,x1,base],fill=(214,54,54,120))
            hatch(x0,base-260,x1,base,(255,110,110,235))
            d.rectangle([x0,base-260,x1,base],outline=(255,80,80,255),width=4)
        d.line([cx-half-t,base+40,cx+half+t,base+40],fill=(255,80,80,255),width=6)
        for x in (cx-half-t,cx+half+t):
            d.line([x,base+22,x,base+58],fill=(255,80,80,255),width=6)
        d.text((cx,base+64),f"확폭 후 {road_m+need_m:.1f} m",font=f30,fill=(255,120,120),anchor="ma")
    # 현재 폭 치수선
    d.line([cx-half,base+120,cx+half,base+120],fill=(150,210,255,255),width=5)
    for x in (cx-half,cx+half):
        d.line([x,base+104,x,base+136],fill=(150,210,255,255),width=5)
    d.text((cx,base+144),f"현재 {road_m:.1f} m",font=f30,fill=(150,210,255),anchor="ma")
    # 건물 라벨
    d.text((cx-half-80,base-300),"상가·모텔",font=f26,fill=(190,200,220),anchor="ma")
    d.text((cx+half+80,base-300),"상가·모텔",font=f26,fill=(190,200,220),anchor="ma")
    y=oy+PH-150
    for L in note:
        d.text((ox+28,y),L,font=f26,fill=(220,225,235)); y+=38

panel(40,190,"현재  폭 5~6 m","대형 덤프 교행 불가 · 편도 교대통행만 가능",5.5,0,
 ["· 편입 0 ㎡","· 건물 저촉 없음","· 죽도관광·영일모텔은 야드 밖 → 아예 안 걸림"],(150,210,255))
panel(920,190,"확폭  폭 8 m 필요","15~25 t 덤프 2대 교행 (3.5 m×2 + 측방여유)",5.5,2.5,
 ["· 편입 2.5 m × 296 m = 740 ㎡","· 건물 전면 2.5 m 저촉 → 부분 철거 불가",
  "· 잔여건물 이전(재축) 보상 · 영업보상 동반"],(255,140,140))

d.text((W//2,44),"도로 폭이 편입을 만드는 방식 — 넓히려면 그만큼 옆 땅을 산다",font=f46,fill=(255,255,255),anchor="ma")
d.text((W//2,110),"③ 우회로 296 m (A갱구 → 부두 북측 가장자리 → 여객선터미널) 단면 개념도",font=f30,fill=(170,180,200),anchor="ma")
d.rounded_rectangle([40,1092,W-40,1160],12,fill=(30,26,26),outline=(255,90,90,150),width=3)
d.text((62,1108),"핵심: 폭이 바꾸는 건 「면적」이 아니라 「어느 필지가 대상이 되느냐」다. 확폭이 없으면 연변 필지는 도로에 접할 뿐 편입되지 않는다.",font=f26,fill=(255,200,200))
im.save(f"{W_}/out/80_width.jpg",quality=93); print("ok")
