# -*- coding: utf-8 -*-
import math, json
from PIL import Image, ImageDraw, ImageFont
FD="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad/fonts/"
def F(sz,w="SemiBold"): return ImageFont.truetype(FD+"Pretendard-%s.ttf"%w, sz)
def merY(lat): return math.degrees(math.log(math.tan(math.pi/4+math.radians(lat)/2)))
def mLon(lat): return 111320*math.cos(math.radians(lat))

PAL={"dark":{"hi":(255,90,70),"mid":(255,176,58),"lo":(255,224,138),"none":(200,214,205),
             "fix":(60,224,208),"ref":(178,184,206),"ink":(255,255,255),"pan":(12,18,16)},
     "light":{"hi":(190,40,25),"mid":(196,110,25),"lo":(170,140,50),"none":(90,110,100),
              "fix":(0,120,120),"ref":(110,118,150),"ink":(20,26,24),"pan":(255,255,255)}}

class Geo:
    def __init__(s_,a,b,s): s_.a,s_.b,s_.s=a,b,s
    def px(s_,lon,lat): return (s_.a+s_.s*lon, s_.b-s_.s*merY(lat))
    def mpp(s_,lat): return 111320*math.cos(math.radians(lat))/(s_.s*math.cos(math.radians(lat)))

def circle_ll(c,rm,n=96):
    dLat=rm/110574.0; dLon=rm/mLon(c[1])
    return [(c[0]+math.cos(2*math.pi*i/n)*dLon, c[1]+math.sin(2*math.pi*i/n)*dLat) for i in range(n+1)]
def band_ll(line,rm):
    L=[];R=[]
    for i in range(len(line)):
        a=line[max(0,i-1)]; b=line[min(len(line)-1,i+1)]
        mx=(b[0]-a[0])*mLon(line[i][1]); my=(b[1]-a[1])*110574.0
        ln=math.hypot(mx,my) or 1.0; nx,ny=-my/ln,mx/ln
        L.append((line[i][0]+nx*rm/mLon(line[i][1]), line[i][1]+ny*rm/110574.0))
        R.append((line[i][0]-nx*rm/mLon(line[i][1]), line[i][1]-ny*rm/110574.0))
    return L+R[::-1]
def dash(dr,pts,fill,width,on=26,off=16):
    for i in range(1,len(pts)):
        x1,y1=pts[i-1]; x2,y2=pts[i]; d=math.hypot(x2-x1,y2-y1)
        if d<1e-6: continue
        ux,uy=(x2-x1)/d,(y2-y1)/d; t=0; draw=True
        while t<d:
            seg=min(on if draw else off, d-t)
            if draw: dr.line([(x1+ux*t,y1+uy*t),(x1+ux*(t+seg),y1+uy*(t+seg))],fill=fill,width=width)
            t+=seg; draw=not draw

def render(img_path, geo, out, theme="dark", zones=(), lines=(), pts=(), rings=(),
           title="", subtitle="", note="", legend=(), scale_note=""):
    im=Image.open(img_path).convert("RGB"); W,H=im.size
    ov=Image.new("RGBA",(W,H),(0,0,0,0)); dr=ImageDraw.Draw(ov,"RGBA")
    C=PAL[theme]
    def PX(p): return geo.px(p[0],p[1])
    # 1) zone fills
    for z in zones:
        col=C[z["g"]]
        poly=[PX(q) for q in (band_ll(z["line"],z["r"]) if z.get("line") else circle_ll(z["c"],z["r"]))]
        z["_poly"]=poly
        dr.polygon(poly,fill=col+(z.get("a",70),))
    # 2) zone outlines
    for z in zones:
        col=C[z["g"]]
        if z.get("line"): dash(dr,z["_poly"]+[z["_poly"][0]],col+(255,),4,18,12)
        else: dr.line(z["_poly"]+[z["_poly"][0]],fill=col+(255,),width=4)
    # 3) distance rings
    for c,rm in rings:
        pts_=[PX(q) for q in circle_ll(c,rm)]
        dash(dr,pts_,C["ink"]+(120,),2,14,12)
        lx,ly=PX((c[0],c[1]-rm/110574.0))
        dr.text((lx,ly-6),("%dm"%rm) if rm<1000 else ("%.1fkm"%(rm/1000)),font=F(20,"Bold"),
                fill=C["ink"]+(210,),anchor="mm",stroke_width=3,stroke_fill=C["pan"]+(200,))
    # 4) axes on top of fills
    for ln in lines:
        p_=[PX(q) for q in ln["pts"]]; col=C[ln.get("c","hi")]; w=ln.get("w",7)
        if ln.get("dash"):
            dash(dr,p_,C["pan"]+(170,),w+6); dash(dr,p_,col+(255,),w)
        else:
            dr.line(p_,fill=C["pan"]+(170,),width=w+6,joint="curve")
            dr.line(p_,fill=col+(255,),width=w,joint="curve")
    # 5) points
    for p_ in pts:
        x,y=PX((p_["lon"],p_["lat"])); r=p_.get("r",9)
        dr.ellipse([x-r,y-r,x+r,y+r],fill=C[p_.get("c","fix")]+(255,),outline=C["pan"]+(255,),width=3)
        if p_.get("n"):
            dr.text((x+r+7,y),p_["n"],font=F(p_.get("fs",22),"Bold"),fill=C["ink"]+(255,),
                    anchor="lm",stroke_width=4,stroke_fill=C["pan"]+(215,))
    # 6) zone id badges last
    for z in zones:
        col=C[z["g"]]
        cc=z.get("c") or z["line"][len(z["line"])//2]
        cx,cy=PX(cc); t=z["id"]; f=F(30,"Black")
        bb=dr.textbbox((0,0),t,font=f); w=bb[2]-bb[0]; h=bb[3]-bb[1]
        dr.rounded_rectangle([cx-w/2-11,cy-h/2-8,cx+w/2+11,cy+h/2+9],7,fill=col+(240,))
        dr.text((cx,cy),t,font=f,fill=(255,255,255),anchor="mm")
    im=Image.alpha_composite(im.convert("RGBA"),ov)
    dr=ImageDraw.Draw(im,"RGBA")
    # title panel
    if title:
        f1=F(38,"Black"); f2=F(23,"SemiBold")
        tw=max(dr.textbbox((0,0),title,font=f1)[2], dr.textbbox((0,0),subtitle,font=f2)[2])
        dr.rounded_rectangle([26,26,26+tw+40,26+(104 if subtitle else 68)],12,fill=C["pan"]+(224,))
        dr.text((46,44),title,font=f1,fill=C["ink"]+(255,))
        if subtitle: dr.text((46,92),subtitle,font=f2,fill=C["ink"]+(190,))
    # legend
    if legend:
        f=F(22,"SemiBold"); lh=34
        wmax=max(dr.textbbox((0,0),t,font=f)[2] for _,t in legend)
        x0,y0=26,H-(len(legend)*lh+ (56 if note else 30))
        dr.rounded_rectangle([x0,y0-14,x0+wmax+78,H-20],12,fill=C["pan"]+(224,))
        for i,(g,t) in enumerate(legend):
            yy=y0+i*lh
            col=C[g] if g in C else C["ink"]
            dr.rounded_rectangle([x0+16,yy+4,x0+44,yy+22],4,fill=col+(120,),outline=col+(255,),width=3)
            dr.text((x0+56,yy+13),t,font=f,fill=C["ink"]+(255,),anchor="lm")
        if note:
            dr.text((x0+16,H-40),note,font=F(19,"SemiBold"),fill=C["ink"]+(165,))
    if scale_note:
        f=F(20,"SemiBold"); bb=dr.textbbox((0,0),scale_note,font=f)
        dr.rounded_rectangle([W-bb[2]-56,H-64,W-24,H-24],9,fill=C["pan"]+(215,))
        dr.text((W-40,H-44),scale_note,font=f,fill=C["ink"]+(190,),anchor="rm")
    im.convert("RGB").save(out,quality=92)
    return out
