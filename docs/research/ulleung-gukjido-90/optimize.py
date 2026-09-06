# -*- coding: utf-8 -*-
"""갱구·접속로 최적화: 좌표정합 위성 래스터 + 해안선 + 기존도로 기반 최소비용 탐색"""
import json, math
import numpy as np
from PIL import Image
B="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad/"
def merY(lat): return math.degrees(math.log(math.tan(math.pi/4+math.radians(lat)/2)))
def invY(my): return math.degrees(2*math.atan(math.exp(math.radians(my)))-math.pi/2)
def mLon(lat): return 111320*math.cos(math.radians(lat))
def km(p,q):
    dy=(q[1]-p[1])*111.195; dx=(q[0]-p[0])*111.195*math.cos(math.radians((p[1]+q[1])/2))
    return math.hypot(dx,dy)

# ---------- 위성 래스터 (좌표정합됨) ----------
class Ras:
    def __init__(s,img,geo):
        s.a=np.array(Image.open(B+"base/"+img).convert("RGB")).astype(np.int16)
        g=json.load(open(B+geo)); s.A,s.Bc,s.S=g["a"],g["b"],g["s"]
        s.H,s.W,_=s.a.shape
        s.mpp=111320/s.S*math.cos(math.radians(37.48))
        s.cls=s._classify()
    def px(s,lon,lat): return (s.A+s.S*lon, s.Bc-s.S*merY(lat))
    def inb(s,lon,lat):
        x,y=s.px(lon,lat); return 8<=x<s.W-8 and 8<=y<s.H-8
    def _classify(s):
        R,G,Bl=s.a[:,:,0].astype(int),s.a[:,:,1].astype(int),s.a[:,:,2].astype(int)
        v=np.maximum(np.maximum(R,G),Bl); mn=np.minimum(np.minimum(R,G),Bl)
        water=(Bl>=R+8)&(Bl>=G-2)&(v<150)
        veg=(~water)&(G>R+6)&(G>Bl+6)
        built=(~water)&(~veg)&(v>95)
        c=np.full(s.a.shape[:2],2,np.uint8)   # 2=기타(나지·도로·그늘)
        c[veg]=1; c[built]=3; c[water]=0
        return c
    def cost(s,lon,lat,rad_m=12):
        """반경 rad_m 내 지표 편입 비용 (0=물 불가)"""
        x,y=s.px(lon,lat); r=max(2,int(rad_m/s.mpp))
        x0,x1=int(x-r),int(x+r+1); y0,y1=int(y-r),int(y+r+1)
        if x0<0 or y0<0 or x1>=s.W or y1>=s.H: return None
        w=s.cls[y0:y1,x0:x1]
        if (w==0).mean()>0.30: return None            # 수면 30% 초과 → 갱구 불가
        return float((w==3).mean()*10 + (w==2).mean()*3 + (w==1).mean()*1)

R03=Ras("03_dodong_sat_50m.webp","geo_03.json")
R04=Ras("04_jeodong_area_sat.webp","geo_04.json")
R05=Ras("05_sadong_area_sat.webp","geo_05.json")
def surface_cost(lon,lat,rad=12):
    for r in (R03,R04,R05):
        if r.inb(lon,lat):
            c=r.cost(lon,lat,rad)
            if c is not None: return c
    return None

# ---------- 해안선 ----------
rings=json.load(open(B+"build/coast.min.json")); COAST=max(rings,key=len)
CO=np.array(COAST)
def inside(pt,ring=COAST):
    x,y=pt; c=False; n=len(ring)
    for i in range(n):
        x1,y1=ring[i]; x2,y2=ring[(i+1)%n]
        if ((y1>y)!=(y2>y)) and (x<(x2-x1)*(y-y1)/(y2-y1)+x1): c=not c
    return c
def dcoast_m(p):
    dy=(CO[:,1]-p[1])*111195.0; dx=(CO[:,0]-p[0])*mLon(p[1])
    return float(np.min(np.hypot(dx,dy)))

# ---------- 기존 도로(국지도 90호선 본선 + 도동항 지선) ----------
MAIN90=[[130.89357,37.47500],[130.89815,37.48425],[130.89952,37.48587],[130.90160,37.48690],
        [130.90229,37.48772],[130.90462,37.49056],[130.90775,37.49308],[130.90971,37.49287],
        [130.90971,37.49482],[130.90978,37.49615],[130.90971,37.49683],[130.91263,37.49766]]
SPUR=[[130.90881,37.48141],[130.90789,37.48303],[130.90602,37.48426],[130.90473,37.48451],
      [130.90368,37.48500],[130.90275,37.48610],[130.90160,37.48690]]
def dens(line,step=15.0):
    out=[]
    for i in range(1,len(line)):
        a,b=line[i-1],line[i]; d=km(a,b)*1000; n=max(1,int(d/step))
        for j in range(n): out.append([a[0]+(b[0]-a[0])*j/n, a[1]+(b[1]-a[1])*j/n])
    out.append(line[-1]); return np.array(out)
ROAD=np.vstack([dens(MAIN90),dens(SPUR)])
def droad_m(p):
    dy=(ROAD[:,1]-p[1])*111195.0; dx=(ROAD[:,0]-p[0])*mLon(p[1])
    return float(np.min(np.hypot(dx,dy)))

# ---------- 선형 평가 ----------
def line_ok(p,q,step=20.0,min_cover=45.0):
    """터널 중심선이 전 구간 육지이고 해안에서 min_cover 이상 떨어져 있는가"""
    d=km(p,q)*1000; n=max(2,int(d/step)); worst=1e9
    for i in range(n+1):
        t=i/n; r=(p[0]+(q[0]-p[0])*t, p[1]+(q[1]-p[1])*t)
        if not inside(r): return False,0.0
        worst=min(worst,dcoast_m(r))
    return worst>=min_cover, worst

def approach(portal,step=15.0):
    """갱구 → 기존도로 최근접점 직선 접속로: 길이와 평균 지표비용"""
    dy=(ROAD[:,1]-portal[1])*111195.0; dx=(ROAD[:,0]-portal[0])*mLon(portal[1])
    i=int(np.argmin(np.hypot(dx,dy))); tgt=ROAD[i]
    L=km(portal,tgt)*1000; n=max(1,int(L/step)); cs=[]
    for j in range(n+1):
        t=j/n; r=(portal[0]+(tgt[0]-portal[0])*t, portal[1]+(tgt[1]-portal[1])*t)
        c=surface_cost(r[0],r[1],10)
        if c is None: return None
        cs.append(c)
    return L, float(np.mean(cs)), list(map(float,tgt))

def score(portal, pair, w_app=0.012, w_appcost=0.55):
    if not inside(portal): return None
    if dcoast_m(portal)<30: return None
    sc=surface_cost(portal[0],portal[1],25)
    if sc is None: return None
    ap=approach(portal)
    if ap is None or ap[0]>260: return None
    ok,cover=line_ok(portal,pair)
    if not ok: return None
    J=sc + w_app*ap[0] + w_appcost*ap[1]
    return dict(J=J, surf=sc, app_len=ap[0], app_cost=ap[1], road=ap[2],
                cover=cover, tunnel=km(portal,pair)*1000)

def search(center, pair, span=220, step=10):
    dLat=step/111195.0; dLon=step/mLon(center[1]); n=int(span/step)
    best=None; grid=[]
    for i in range(-n,n+1):
        for j in range(-n,n+1):
            p=(center[0]+j*dLon, center[1]+i*dLat)
            s=score(p,pair)
            if s is None: continue
            s["p"]=[round(p[0],6),round(p[1],6)]; grid.append(s)
            if best is None or s["J"]<best["J"]: best=s
    return best, grid

DODONG=(130.90881,37.48141)
def diag(portal,pair,min_cover=30.0,max_app=300.0,hub_max=None):
    r={}
    r["land"]=inside(portal); r["dcoast"]=dcoast_m(portal)
    sc=surface_cost(portal[0],portal[1],25); r["surf"]=sc
    ap=approach(portal); r["app"]=ap
    ok,cov=line_ok(portal,pair,min_cover=min_cover); r["cover"]=cov; r["line_ok"]=ok
    r["dhub"]=km(portal,DODONG)*1000
    bad=[]
    if not r["land"]: bad.append("육지밖")
    if r["dcoast"]<30: bad.append("해안<30m")
    if sc is None: bad.append("수면비율초과")
    if ap is None: bad.append("접속로 수면통과")
    elif ap[0]>max_app: bad.append("접속로 %.0fm>%.0f"%(ap[0],max_app))
    if not ok: bad.append("토피여유 %.0fm<%.0f"%(cov,min_cover))
    if hub_max and r["dhub"]>hub_max: bad.append("도동항 %.0fm>%.0f"%(r["dhub"],hub_max))
    r["bad"]=bad; return r

def score2(portal,pair,min_cover=30.0,max_app=300.0,hub_max=None,tgt_len=None):
    d=diag(portal,pair,min_cover,max_app,hub_max)
    if d["bad"]: return None
    L=km(portal,pair)*1000
    J=d["surf"] + 0.012*d["app"][0] + 0.55*d["app"][1]
    if tgt_len: J += 0.004*abs(L-tgt_len)
    return dict(J=J,surf=d["surf"],app_len=d["app"][0],app_cost=d["app"][1],
                road=d["app"][2],cover=d["cover"],tunnel=L,dhub=d["dhub"])
def search2(center,pair,span=260,step=10,**kw):
    dLat=step/111195.0; dLon=step/mLon(center[1]); n=int(span/step)
    best=None; cnt=0
    for i in range(-n,n+1):
        for j in range(-n,n+1):
            p=(center[0]+j*dLon, center[1]+i*dLat)
            s=score2(p,pair,**kw)
            if s is None: continue
            cnt+=1; s["p"]=[round(p[0],6),round(p[1],6)]
            if best is None or s["J"]<best["J"]: best=s
    return best,cnt
