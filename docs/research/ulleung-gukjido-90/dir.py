# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
W_="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
F=lambda n,w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf",n)
f24,f26,f30,f34,f44=F(24,"SemiBold"),F(26,"SemiBold"),F(30),F(34),F(44,"ExtraBold")
W,H=1820,1120
im=Image.new("RGB",(W,H),(17,19,24)); d=ImageDraw.Draw(im,"RGBA")
ROCK=(84,94,72); BARE=(150,128,96); YARD=(96,100,110); STEEL=(180,188,200); FDN=(122,126,136)
def hatch(x0,y0,x1,y1,col,step=16,w=3):
    k=-(y1-y0)
    while k<(x1-x0):
        d.line([max(x0,x0+k),y0+max(0,-k),min(x1,x0+k+(y1-y0)),y0+min(y1-y0,(x1-x0)-k)],fill=col,width=w); k+=step
d.text((W//2,34),"정정 — 죽도관광 앞 도동길 5.0 m 단면 (실제 배치)",font=f44,fill=(255,255,255),anchor="ma")
d.text((W//2,94),"북동측 = 나지·절개지(A갱구 편입 부지)   /   남서측 = 부두 야적장 + 보행교 교대",font=f30,fill=(180,190,210),anchor="ma")

SC=76; base=700; cx=W//2; half=5.0*SC/2
# 북동(좌): 절개지 + 나지 = 갱구 부지
d.polygon([(60,base),(cx-half,base),(cx-half,base-210),(60,base-430)],fill=ROCK)
d.rectangle([cx-half-6.0*SC,base-190,cx-half,base],fill=BARE)
d.text((cx-half-4.6*SC,base-232),"나지 (지번 40 · 46-6)",font=f26,fill=(240,220,180),anchor="ma")
d.text((160,base-330),"절개지 · A갱구",font=f30,fill=(200,220,190))
# 남서(우): 부두 야적장 + 다리
d.rectangle([cx+half,base-14,W-60,base],fill=YARD)
d.text((W-70,base+56),"부두 야적장 (항만시설)",font=f26,fill=(180,190,205),anchor="ra")
fx0,fx1=cx+half+1.1*SC, cx+half+3.2*SC
d.rectangle([fx0,base-84,fx1,base],fill=FDN,outline=(215,220,230,210),width=3)
d.text((fx1+26,base-46),"보행교 교대·아치 기부",font=f26,fill=(225,230,240),anchor="lm")
d.polygon([(fx0+24,base-84),(fx0+50,base-380),(fx0+118,base-420),(fx0+92,base-84)],fill=STEEL)
dy=base-3.2*SC-20
d.rectangle([cx-half-40,dy-20,W-70,dy],fill=STEEL,outline=(232,238,248,220),width=3)
d.text((W-90,dy-54),"보행교 데크 · 형하 3.2 m",font=f26,fill=(230,236,246),anchor="ra")
# 노면 + 확폭(북동측)
d.rectangle([cx-half,base-14,cx+half,base],fill=(72,76,86))
t=3.0*SC; x0,x1=cx-half-t,cx-half
d.rectangle([x0,base-190,x1,base],fill=(40,200,140,120)); hatch(x0,base-190,x1,base,(90,240,175,240))
d.rectangle([x0,base-190,x1,base],outline=(60,225,155,255),width=6)
d.text(((x0+x1)/2,base-330),"확폭 3.0 m",font=f30,fill=(120,245,185),anchor="ma")
d.text(((x0+x1)/2,base-292),"갱구 편입 부지 안에서 흡수",font=f26,fill=(120,245,185),anchor="ma")
# X on bridge side
RX=cx+half+2.15*SC; RY=base-250
for ax,ay in ((1,1),(1,-1)):
    d.line([(RX-40*ax,RY-40*ay),(RX+40*ax,RY+40*ay)],fill=(255,60,60,255),width=16)
d.ellipse([RX-58,RY-58,RX+58,RY+58],outline=(255,60,60,255),width=10)
d.text((RX+92,RY),"남서측 확폭 금지 — 다리 기초",font=f30,fill=(255,130,130),anchor="lm")
# 치수
y=base+140
d.line([cx-half,y,cx+half,y],fill=(150,210,255,255),width=6)
for x in (cx-half,cx+half): d.line([x,y-18,x,y+18],fill=(150,210,255,255),width=6)
d.text((cx,y+26),"현재 5.0 m",font=f30,fill=(150,210,255),anchor="ma")
d.line([x0,y+86,cx+half,y+86],fill=(60,225,155,255),width=6)
for x in (x0,cx+half): d.line([x,y+68,x,y+104],fill=(60,225,155,255),width=6)
d.text(((x0+cx+half)/2,y+112),"확폭 후 8.0 m",font=f30,fill=(60,225,155),anchor="ma")
d.rounded_rectangle([40,1010,W-40,1104],14,fill=(24,30,26),outline=(120,240,180,160),width=3)
d.text((64,1024),"결론: 북동측(갱구측)으로 넓힌다. 그쪽은 나지이고 이미 A갱구로 매수되는 부지라 추가 편입이 사실상 없다.",font=f30,fill=(150,245,200))
d.text((64,1064),"죽도관광·영일모텔·해산촌·농어민장터는 도로에서 물러나 있어 3 m로 저촉되지 않고, 보행교도 건드리지 않는다.",font=f26,fill=(205,245,225))
im.save(f"{W_}/out/97_section_final.jpg",quality=93); print("ok")
