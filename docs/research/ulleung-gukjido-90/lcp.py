# -*- coding: utf-8 -*-
"""10 m 격자 최소비용 경로: 갱구 → 기존 국지도 90호선/도동 지선 접속로"""
import sys, math, json, heapq
sys.path.insert(0,"/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad")
import numpy as np
from optimize import (B, R03, R04, R05, Ras, COAST, inside, dcoast_m, ROAD, km, mLon, merY, invY, DODONG)

LON0,LON1,LAT0,LAT1,CELL = 130.8890,130.9170,37.4715,37.5010,10.0
NX=int((LON1-LON0)*mLon(37.485)/CELL); NY=int((LAT1-LAT0)*111195.0/CELL)
lons=LON0+(np.arange(NX)+0.5)*CELL/mLon(37.485)
lats=LAT0+(np.arange(NY)+0.5)*CELL/111195.0
LO,LA=np.meshgrid(lons,lats)

def sample(r):
    x=(r.A+r.S*LO); y=(r.Bc-r.S*np.vectorize(merY)(LA))
    xi=np.round(x).astype(int); yi=np.round(y).astype(int)
    ok=(xi>=0)&(xi<r.W)&(yi>=0)&(yi<r.H)
    out=np.full(LO.shape,-1,np.int8)
    out[ok]=r.cls[yi[ok],xi[ok]]
    return out
CLS=np.full(LO.shape,-1,np.int8)
R06=Ras("06_overview_sat_300m.webp","geo_06.json")
for r in (R06,R05,R04,R03):                       # 뒤일수록 우선(고해상)
    s=sample(r); m=s>=0; CLS[m]=s[m]

# 육지 마스크(해안선 폴리곤) — 래스터 결측 보완
def poly_mask():
    from matplotlib.path import Path
    p=Path(np.array(COAST))
    pts=np.stack([LO.ravel(),LA.ravel()],1)
    return p.contains_points(pts).reshape(LO.shape)
try:
    LAND=poly_mask()
except Exception:
    LAND=np.ones(LO.shape,bool)

COST=np.select([CLS==3, CLS==2, CLS==1, CLS==0],
               [10.0,     3.0,   1.0,   np.inf], default=2.0)
COST[~LAND]=np.inf
COST[CLS==0]=np.inf

# 기존 도로 셀
ROADCELL=np.zeros(LO.shape,bool)
for lon,lat in ROAD:
    j=int((lon-LON0)*mLon(37.485)/CELL); i=int((lat-LAT0)*111195.0/CELL)
    if 0<=i<NY and 0<=j<NX: ROADCELL[i,j]=True

def dijkstra_from_roads():
    INF=float('inf')
    D=np.full(LO.shape,INF); L=np.full(LO.shape,INF); PREV=np.full(LO.shape,-1,np.int32)
    h=[]
    for i,j in zip(*np.nonzero(ROADCELL)):
        if np.isfinite(COST[i,j]):
            D[i,j]=0.0; L[i,j]=0.0; heapq.heappush(h,(0.0,int(i),int(j)))
    nb=[(-1,0,1),(1,0,1),(0,-1,1),(0,1,1),(-1,-1,1.4142),(-1,1,1.4142),(1,-1,1.4142),(1,1,1.4142)]
    while h:
        d,i,j=heapq.heappop(h)
        if d>D[i,j]+1e-9: continue
        for di,dj,w in nb:
            a,b_=i+di,j+dj
            if not(0<=a<NY and 0<=b_<NX): continue
            c=COST[a,b_]
            if not np.isfinite(c): continue
            nd=d+w*CELL*(0.5*(COST[i,j]+c))/10.0     # 비용 가중 거리
            if nd<D[a,b_]-1e-9:
                D[a,b_]=nd; L[a,b_]=L[i,j]+w*CELL; PREV[a,b_]=i*NX+j
                heapq.heappush(h,(nd,a,b_))
    return D,L,PREV
def ij(p,snap=True):
    j=int((p[0]-LON0)*mLon(37.485)/CELL); i=int((p[1]-LAT0)*111195.0/CELL)
    if snap and (not(0<=i<NY and 0<=j<NX) or not np.isfinite(COST[i,j])):
        best=None
        for di in range(-6,7):
            for dj in range(-6,7):
                a,b_=i+di,j+dj
                if 0<=a<NY and 0<=b_<NX and np.isfinite(COST[a,b_]):
                    d=di*di+dj*dj
                    if best is None or d<best[0]: best=(d,a,b_)
        if best: i,j=best[1],best[2]
    return i,j
def ll(i,j): return (LON0+(j+0.5)*CELL/mLon(37.485), LAT0+(i+0.5)*CELL/111195.0)
def path_from(PREV,p):
    i,j=ij(p); out=[]
    while i>=0 and PREV[i,j]!=-1:
        out.append(ll(i,j)); k=PREV[i,j]; i,j=k//NX,k%NX
    out.append(ll(i,j)); return out[::-1]
