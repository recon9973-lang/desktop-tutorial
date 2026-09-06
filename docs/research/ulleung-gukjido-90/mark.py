# -*- coding: utf-8 -*-
import json, math, sys
sys.path.insert(0,"/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad")
from overlay import Geo, render
B="/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad/"
Z=json.load(open(B+"build/zones.json",encoding='utf-8'))
ALIGN=json.load(open(B+"build/align_south.json"))
def km(p,q):
    dy=(q[1]-p[1])*111.195; dx=(q[0]-p[0])*111.195*math.cos(math.radians((p[1]+q[1])/2))
    return math.hypot(dx,dy)
acc=0; SOUTH=[ALIGN[0]]
for i in range(1,len(ALIGN)):
    acc+=km(ALIGN[i-1],ALIGN[i]); SOUTH.append(ALIGN[i])
    if acc>=2.70: break
SPUR=[[130.90881,37.48141],[130.90789,37.48303],[130.90602,37.48426],[130.90473,37.48451],
      [130.90368,37.48500],[130.90275,37.48610],[130.90160,37.48690]]
NORTH=[[130.90881,37.48141],[130.90789,37.48303],[130.90602,37.48426],[130.90368,37.48500],
       [130.90275,37.48610],[130.90160,37.48690],[130.90229,37.48772],[130.90462,37.49056],
       [130.90680,37.49330],[130.90775,37.49308],[130.90971,37.49287],[130.90971,37.49482],
       [130.90978,37.49615],[130.90971,37.49683],[130.91263,37.49766]]
LINES={"SPUR":SPUR,"SOUTH":SOUTH,"NORTH":NORTH}
DODONG=[130.90881,37.48141]
def zones(ids=None):
    out=[]
    for z in Z:
        if ids and z["id"] not in ids: continue
        d={"id":z["id"],"g":z["g"],"r":z["r"]}
        if z.get("band"): d["line"]=LINES[z["band"]]
        else: d["c"]=z["c"]
        out.append(d)
    return out
