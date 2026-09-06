# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
W_="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
F=lambda n,w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf",n)
f22,f26,f30,f36,f46=F(22,"SemiBold"),F(26,"SemiBold"),F(30),F(36),F(46,"ExtraBold")
W,H=1800,1240
im=Image.new("RGB",(W,H),(17,19,24)); d=ImageDraw.Draw(im,"RGBA")
PANEL=(28,31,38); ROCK=(74,86,66); BLD=(96,104,122); QUAY=(86,90,100); SEA=(24,58,78)
def hatch(x0,y0,x1,y1,col,step=15,w=3):
    k=-(y1-y0)
    while k < (x1-x0):
        d.line([max(x0,x0+k), y0+max(0,-k), min(x1,x0+k+(y1-y0)), y0+min(y1-y0,(x1-x0)-k)],fill=col,width=w); k+=step

def panel(ox,oy,title,tcol,side,note):
    PW,PH=840,900
    d.rounded_rectangle([ox,oy,ox+PW,oy+PH],18,fill=PANEL,outline=(255,255,255,55),width=3)
    d.text((ox+26,oy+22),title,font=f36,fill=tcol)
    SC=50; base=oy+540; cx=ox+PW//2; half=5.0*SC/2   # 현재 5.0 m
    # 산측(좌) : 절개사면 + 죽도관광
    d.polygon([(ox+20,base),(cx-half,base),(cx-half,base-150),(ox+20,base-330)],fill=ROCK)
    d.rectangle([ox+60,base-320,ox+230,base-150],fill=BLD,outline=(200,210,225,200),width=3)
    d.text((ox+130,base-392),"죽도관광 · 영일모텔",font=f26,fill=(200,210,225),anchor="ma")
    d.text((ox+40,base-100),"절개사면",font=f26,fill=(190,210,180))
    # 부두측(우) : 평지 포장 + 바다
    d.rectangle([cx+half,base-16,ox+PW-160,base],fill=QUAY)
    d.rectangle([ox+PW-160,base-16,ox+PW-20,base+120],fill=SEA)
    d.text((cx+half+160,base-56),"부두 노면 (항만시설)",font=f26,fill=(170,185,205))
    d.text((ox+PW-90,base+52),"바다",font=f26,fill=(120,170,200),anchor="ma")
    # 노면
    d.rectangle([cx-half,base-16,cx+half,base],fill=(72,76,86))
    d.line([cx,base-8,cx,base-8],fill=(230,220,120,220),width=4)
    # 확폭 3.0 m
    t=3.0*SC
    if side=="rock":
        x0,x1=cx-half-t,cx-half
        d.rectangle([x0,base-330,x1,base],fill=(214,54,54,120)); hatch(x0,base-330,x1,base,(255,110,110,240))
        d.rectangle([x0,base-330,x1,base],outline=(255,70,70,255),width=5)
        d.text((x1+118,base-352),"절취 + 건물 저촉",font=f26,fill=(255,140,140),anchor="ma")
    else:
        x0,x1=cx+half,cx+half+t
        d.rectangle([x0,base-16,x1,base],fill=(60,200,140,150)); hatch(x0,base-70,x1,base,(90,235,170,235))
        d.rectangle([x0,base-70,x1,base],outline=(60,220,150,255),width=5)
        d.text(((x0+x1)/2,base-108),"부두 노면 3 m 잠식",font=f26,fill=(120,240,180),anchor="ma")
    # 치수
    y=base+26
    d.line([cx-half,y,cx+half,y],fill=(150,210,255,255),width=5)
    for x in (cx-half,cx+half): d.line([x,y-16,x,y+16],fill=(150,210,255,255),width=5)
    d.text((cx,y+24),"현재 5.0 m",font=f30,fill=(150,210,255),anchor="ma")
    L,R=(cx-half-t,cx+half) if side=="rock" else (cx-half,cx+half+t)
    c=(255,80,80,255) if side=="rock" else (60,220,150,255)
    d.line([L,y+92,R,y+92],fill=c,width=6)
    for x in (L,R): d.line([x,y+74,x,y+110],fill=c,width=6)
    d.text(((L+R)/2,y+100),"확폭 후 8.0 m",font=f30,fill=c[:3],anchor="ma")
    yy=oy+PH-186
    for t2,c2 in note:
        d.text((ox+26,yy),t2,font=f26,fill=c2); yy+=38

d.text((W//2,40),"죽도관광 앞 5.0 m — 확폭은 확정, 문제는 「어느 쪽으로」",font=f46,fill=(255,255,255),anchor="ma")
d.text((W//2,104),"필요 8.0 m · 부족 3.0 m × 연장 296 m = 888 ㎡",font=f30,fill=(180,190,210),anchor="ma")
panel(40,170,"① 산측(북) 확폭 — 최악",(255,120,120),"rock",
 [("· 편입 888 ㎡ + 죽도관광·영일모텔 건물 전면 저촉",(255,190,190)),
  ("· 잔여건축물 전부 매수 청구 → 건물 통째 이전(재축)",(255,190,190)),
  ("· 영업보상(휴업 4개월/폐업 2년) 동반",(255,190,190)),
  ("· 절개사면 재절취 → 사면 안정·낙석 대책 추가",(255,190,190)),
  ("→ A측 3등급이 1등급으로 점프",(255,120,120))])
panel(920,170,"② 부두측(남) 확폭 — 권고",(120,240,180),"quay",
 [("· 편입 888 ㎡가 항만시설(38·5잡·4잡)에서 나옴",(190,240,215)),
  ("· 국·공유 → 관리전환(무상), 현금보상 거의 0",(190,240,215)),
  ("· 평지 포장이라 시공 용이 · 사면 문제 없음",(190,240,215)),
  ("· 대가: 부두 노면 3 m 잠식 → 주차면 감소",(255,220,150)),
  ("→ 죽도관광·영일모텔은 편입에서 빠짐",(120,240,180))])
d.rounded_rectangle([40,1096,W-40,1200],14,fill=(26,30,28),outline=(120,240,180,150),width=3)
d.text((64,1114),"결론: ②가 정답이다. 산측은 건물·영업·사면이 한꺼번에 걸리고, 부두측은 국공유 관리전환으로 끝난다.",font=f30,fill=(190,245,220))
d.text((64,1156),"단, 부두 노면이 3 m 줄어드는 만큼 A갱구 가설야드의 준공 후 주차장 전용이 더 중요해진다.",font=f26,fill=(255,220,150))
im.save(f"{W_}/out/92_widen_side.jpg",quality=93); print("ok")
