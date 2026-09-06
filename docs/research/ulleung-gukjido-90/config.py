# -*- coding: utf-8 -*-
import json, math
from PIL import Image, ImageDraw, ImageFont
W_ = "/tmp/claude-0/-home-user-desktop-tutorial/a49bfc76-9aab-5342-b75f-19862b631a3f/scratchpad"
g = json.load(open(f"{W_}/geo_03.json"))
a, b, s = g["a"], g["b"], g["s"]
def merY(lat): return math.degrees(math.log(math.tan(math.pi/4 + math.radians(lat)/2)))
def P(lo, la): return (a + s*lo, b - s*merY(la))
PPM = 4.41

im = Image.open(f"{W_}/base/03_dodong_sat_50m.webp").convert("RGB")
W, H = im.size
SC = 2
im = im.resize((W*SC, H*SC), Image.LANCZOS)
W, H = im.size
ov = Image.new("RGBA", (W, H), (0,0,0,0))
d = ImageDraw.Draw(ov, "RGBA")
def p(lo, la):
    x, y = P(lo, la); return (x*SC, y*SC)
PPMs = PPM*SC

F = lambda n, w="Bold": ImageFont.truetype(f"{W_}/fonts/Pretendard-{w}.ttf", n)
f28, f34, f40, f48, f56 = F(28), F(34), F(40), F(48,"ExtraBold"), F(56,"Black")

def txt(xy, t, font, fill=(255,255,255), halo=(0,0,0), hw=4, anchor="mm"):
    x, y = xy
    for dx in range(-hw, hw+1):
        for dy in range(-hw, hw+1):
            if dx*dx+dy*dy <= hw*hw:
                d.text((x+dx, y+dy), t, font=font, fill=halo+(235,), anchor=anchor)
    d.text((x, y), t, font=font, fill=fill+(255,), anchor=anchor)

def box(xy, lines, font, bg=(12,14,20,225), fg=(255,255,255), pad=14, anchor="lt", ec=None):
    x, y = xy
    ws = [d.textbbox((0,0), L, font=font)[2] for L in lines]
    lh = font.size + 12
    bw, bh = max(ws)+pad*2, lh*len(lines)+pad*2-8
    if anchor[0] == "r": x -= bw
    if anchor[1] == "b": y -= bh
    d.rounded_rectangle([x, y, x+bw, y+bh], 12, fill=bg, outline=(ec or (255,255,255,110)), width=3)
    for i, L in enumerate(lines):
        d.text((x+pad, y+pad+i*lh), L, font=font, fill=fg+(255,))
    return (x, y, x+bw, y+bh)

def dash(p1, p2, col, w, on=26, off=18):
    x1,y1 = p1; x2,y2 = p2
    L = math.hypot(x2-x1, y2-y1); n = max(1, int(L//(on+off)))
    ux, uy = (x2-x1)/L, (y2-y1)/L
    t = 0.0
    while t < L:
        e = min(t+on, L)
        d.line([x1+ux*t, y1+uy*t, x1+ux*e, y1+uy*e], fill=col, width=w)
        t += on+off

def arrow(p1, p2, col, w, head=34):
    d.line([p1, p2], fill=col, width=w)
    ang = math.atan2(p2[1]-p1[1], p2[0]-p1[0])
    for sgn in (1, -1):
        aa = ang + sgn*math.radians(158)
        d.line([p2, (p2[0]+head*math.cos(aa), p2[1]+head*math.sin(aa))], fill=col, width=w)

# ---- anchors ----
A0 = p(130.908918, 37.482490)
B0 = p(130.907939, 37.482038)
PORT = p(130.9088118, 37.4814127)
TERM = p(130.9095053, 37.4816281)

def proj(o, bearing, metres):
    return (o[0] + math.sin(math.radians(bearing))*metres*PPMs,
            o[1] - math.cos(math.radians(bearing))*metres*PPMs)

# ---- 1) 갱구 가설야드 (표준 6,220 m2 -> r 44.5 m / 최소 3,540 m2 -> r 33.6 m)
for O, col in ((A0, (255,92,92)), (B0, (86,180,255))):
    for r, al in ((44.5, 46), (33.6, 74)):
        R = r*PPMs
        d.ellipse([O[0]-R, O[1]-R, O[0]+R, O[1]+R], fill=col+(al,))
    for r, wdt in ((44.5, 4), (33.6, 5)):
        R = r*PPMs
        d.ellipse([O[0]-R, O[1]-R, O[0]+R, O[1]+R], outline=col+(255,), width=wdt)

# ---- 2) 다리(보행교) 추정 위치 밴드: A갱구에서 ESE 30~65 m
BC  = proj(A0, 169, 44)
BR1 = proj(BC, 258, 26); BR2 = proj(BC, 78, 26)
d.line([BR1, BR2], fill=(255,214,0,235), width=16)
for q in (BR1, BR2):
    d.ellipse([q[0]-13, q[1]-13, q[0]+13, q[1]+13], fill=(255,214,0,255), outline=(0,0,0,255), width=3)
RU = 25*PPMs
d.ellipse([BC[0]-RU, BC[1]-RU, BC[0]+RU, BC[1]+RU], outline=(255,214,0,200), width=5)
txt((BC[0]+250, BC[1]+40), "보행교(강아치)", f34, (255,214,0))
txt((BC[0]+250, BC[1]+82), "판독 추정 ±25 m", F(28,"SemiBold"), (255,230,120))

# ---- 3) 본선 접속부 A0-B0 (100.1 m) : 부두 상부 고가
d.line([A0, B0], fill=(0,0,0,190), width=30)
d.line([A0, B0], fill=(255,255,255,255), width=18)
d.line([A0, B0], fill=(255,140,0,255), width=9)

# ---- 4) 터널 축
AJ = proj(A0, 13.1, 210)      # 저동 방면
BJ = proj(B0, 235.8, 210)     # 사동 방면
for (O, T, col) in ((A0, AJ, (255,92,92)), (B0, BJ, (86,180,255))):
    d.line([O, T], fill=(0,0,0,190), width=26)
    arrow(O, T, col+(255,), 14, 46)

# ---- 5) 도동항 램프 (개념) : 접속부 중앙 -> 부두 노면
MID = ((A0[0]+B0[0])/2, (A0[1]+B0[1])/2)
RMP = proj(MID, 145, 52)
dash(MID, RMP, (0,255,150,255), 12)
arrow((RMP[0]-1, RMP[1]-1), RMP, (0,255,150,255), 12, 30)

# ---- 6) 포인트
for O, lab, col in ((A0, "A", (255,92,92)), (B0, "B", (86,180,255))):
    d.ellipse([O[0]-26, O[1]-26, O[0]+26, O[1]+26], fill=col+(255,), outline=(0,0,0,255), width=5)
    txt((O[0], O[1]-1), lab, f34, (0,0,0), (0,0,0), 0)

# ---- 7) 라벨
txt((A0[0]+40, A0[1]-140), "A갱구  저동 방면", f40, (255,150,150))
txt((A0[0]+40, A0[1]-96),  "축 방위 13.1° · 북측 2.74 km", f34, (255,190,190))
txt((B0[0]-30, B0[1]+150), "B갱구  사동 방면", f40, (170,215,255), anchor="mm")
txt((B0[0]-30, B0[1]+194), "축 방위 235.8° · 남측 확정 2.70 km", f34, (200,230,255), anchor="mm")
txt((MID[0]-120, MID[1]-92), "본선 접속부 100.1 m", f40, (255,190,110))
txt((MID[0]-120, MID[1]-46), "부두 상부 고가(권고)", f34, (255,210,150))
txt((RMP[0]+40, RMP[1]+44), "도동항 램프", f34, (140,255,200))

txt((A0[0]+120, A0[1]+248), "야드 지장물: 죽도관광 · 나지 2,344 ㎡", F(28,"SemiBold"), (255,205,205))
txt((B0[0]-30, B0[1]-150), "야드 지장물: 소공원·해경출장소·활어회센타", F(28,"SemiBold"), (200,230,255), anchor="mm")

# 절선각
txt((A0[0]-190, A0[1]+58), "절선각 46.7°", f34, (255,235,120))
txt((B0[0]+150, B0[1]+52), "절선각 4.0°", f34, (255,235,120))

# ---- 8) 범례
box((36, 132), [
  "국지도 90호선 · 도동항 A/B 터널 구성안",
  "A갱구 130.908918, 37.482490  (도동항 126 m)",
  "B갱구 130.907939, 37.482038  (도동항  56 m)",
  "두 갱구 이격 100.1 m · A→B 방위 239.8°",
  "B터널 축 235.8° → 차이 4.0° = 사실상 일직선",
  "원: 갱구 가설야드 최소 3,540 ㎡ / 표준 6,220 ㎡",
], f34, ec=(255,255,255,150))

box((W-36, H-36), [
  "판독 근거: 사용자 제공 네이버 위성(30 m 축척) 아핀 정합 RMS 3.4 m",
  "로드뷰 4매(2025-11, 도동길) · 네이버 실측선 296 m / 147 m",
  "노선 미공표 — 전 항목 추정",
], F(28, "SemiBold"), anchor="rb", bg=(12,14,20,205), ec=(255,255,255,110))

out = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
out = out.resize((W//2, H//2), Image.LANCZOS)
out.save(f"{W_}/out/43_config.jpg", quality=92)
print("saved", out.size)
