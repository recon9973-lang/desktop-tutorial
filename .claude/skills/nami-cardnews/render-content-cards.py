#!/usr/bin/env python3
# 배나미 카드뉴스 2~5장(인물 없는 콘텐츠 카드) 렌더러 — 샌드박스에서 headless chrome로 직접 렌더.
# 인트로/포인트=크림 배경(본문 세로 중앙), 팁=에메랄드, CTA=에메랄드 GR[OU]ND.
# 사용: POSTS 딕셔너리(글별 콘텐츠) 수정 후 실행 → persona-nami/ig/postN-2..-5.png 생성.
import subprocess, os

CHROME = os.environ.get("CHROME_BIN", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
LIME, EM, INK, CREAM = "#C7F24E", "#12574F", "#14201d", "#F4F1E8"

def spark(w, col): return f'<svg width="{w}" height="{w}" viewBox="0 0 100 100"><path d="M50 2 C56 38 62 44 98 50 C62 56 56 62 50 98 C44 62 38 56 2 50 C38 44 44 38 50 2Z" fill="{col}"/></svg>'
def star(w, col): return f'<svg width="{w}" height="{w}" viewBox="0 0 100 100"><path d="M50 4 L61 39 L98 39 L68 61 L79 96 L50 74 L21 96 L32 61 L2 39 L39 39 Z" fill="{col}"/></svg>'
def squig(w, col): return f'<svg width="{w}" height="{int(w*0.5)}" viewBox="0 0 120 60"><path d="M6 40 Q 24 6 42 34 T 78 34 T 114 30" stroke="{col}" fill="none" stroke-width="9" stroke-linecap="round"/></svg>'

HEAD = '<meta charset="utf-8"><style>*{margin:0;padding:0;box-sizing:border-box;font-family:"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif;}html,body{width:1080px;height:1080px;overflow:hidden;}'
def W(css, body): return f'<!doctype html><html><head>{HEAD}{css}</style></head><body>{body}</body></html>'
def badge(): return f'<span style="background:{EM};color:#fff;font-size:26px;font-weight:800;padding:11px 22px;border-radius:40px;">GROUND 🌿</span>'

def intro(topic, ta, hl, tb, sub):
    css = f'.wrap{{position:relative;width:1080px;height:1080px;background:{CREAM};padding:88px 84px;display:flex;flex-direction:column;}}.top{{display:flex;align-items:center;gap:16px;}}.topic{{font-size:26px;font-weight:800;color:{EM};opacity:.8;}}.main{{flex:1;display:flex;flex-direction:column;justify-content:center;}}.title{{font-size:84px;font-weight:900;color:{INK};line-height:1.5;letter-spacing:-2.5px;}}.hl{{background:{LIME};padding:2px 16px;border-radius:8px;box-decoration-break:clone;-webkit-box-decoration-break:clone;}}.sub{{margin-top:52px;font-size:41px;font-weight:700;color:#3c4a44;line-height:1.6;}}.d1{{position:absolute;top:78px;right:90px;transform:rotate(-8deg);}}.d2{{position:absolute;bottom:110px;left:84px;}}'
    return W(css, f'<div class="wrap"><div class="d1">{spark(60,EM)}</div><div class="d2">{squig(116,LIME)}</div><div class="top">{badge()}<span class="topic">{topic}</span></div><div class="main"><div class="title">{ta}<span class="hl">{hl}</span>{tb}</div><div class="sub">{sub}</div></div></div>')

def points(topic, ta, hl, tb, items):
    rows = "".join(f'<div class="row"><div class="num">{i+1}</div><div class="txt">{p}</div></div>' for i, p in enumerate(items))
    css = f'.wrap{{position:relative;width:1080px;height:1080px;background:{CREAM};padding:88px 84px;display:flex;flex-direction:column;}}.top{{display:flex;align-items:center;gap:16px;}}.topic{{font-size:26px;font-weight:800;color:{EM};opacity:.8;}}.main{{flex:1;display:flex;flex-direction:column;justify-content:center;}}.title{{font-size:74px;font-weight:900;color:{INK};line-height:1.4;letter-spacing:-2px;}}.hl{{background:{LIME};padding:2px 14px;border-radius:8px;}}.list{{margin-top:58px;display:flex;flex-direction:column;gap:42px;}}.row{{display:flex;align-items:center;gap:28px;}}.num{{flex:0 0 auto;width:68px;height:68px;border-radius:20px;background:{LIME};color:{INK};font-size:34px;font-weight:900;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 0 {EM};}}.txt{{font-size:45px;font-weight:800;color:#233029;line-height:1.4;}}.d1{{position:absolute;top:74px;right:84px;transform:rotate(-10deg);}}.d3{{position:absolute;bottom:80px;right:84px;}}'
    return W(css, f'<div class="wrap"><div class="d1">{star(50,EM)}</div><div class="d3">{squig(104,LIME)}</div><div class="top">{badge()}<span class="topic">{topic}</span></div><div class="main"><div class="title">{ta}<span class="hl">{hl}</span>{tb}</div><div class="list">{rows}</div></div></div>')

def tip(label, body_html):
    css = f'.wrap{{position:relative;width:1080px;height:1080px;background:radial-gradient(130% 120% at 26% 16%,#17685e 0%,{EM} 60%,#0b3a34 100%);padding:110px 88px;display:flex;flex-direction:column;justify-content:center;}}.label{{align-self:flex-start;background:{LIME};color:{INK};font-size:30px;font-weight:900;padding:12px 26px;border-radius:40px;}}.body{{margin-top:52px;font-size:64px;font-weight:900;color:#fff;line-height:1.6;letter-spacing:-1.5px;}}.body .hl{{background:{LIME};color:{INK};padding:2px 14px;border-radius:8px;}}.d1{{position:absolute;top:120px;right:110px;transform:rotate(8deg);}}.d2{{position:absolute;bottom:120px;right:120px;}}'
    return W(css, f'<div class="wrap"><div class="d1">{spark(58,LIME)}</div><div class="d2">{squig(110,LIME)}</div><div class="label">{label}</div><div class="body">{body_html}</div></div>')

def cta():
    css = f'.wrap{{position:relative;width:1080px;height:1080px;background:radial-gradient(130% 120% at 28% 18%,#15645a 0%,{EM} 55%,#0b3a34 100%);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:80px;}}.leaf{{font-size:88px;}}.brand{{margin-top:6px;font-size:112px;font-weight:900;color:#fff;letter-spacing:-4px;}}.brand .hl{{background:{LIME};color:{INK};padding:0 16px;border-radius:10px;}}.sub{{margin-top:34px;font-size:44px;font-weight:700;color:#dbeee7;line-height:1.7;}}.handle{{margin-top:56px;font-size:50px;font-weight:900;color:{INK};background:{LIME};padding:18px 44px;border-radius:50px;}}.cta{{margin-top:32px;font-size:33px;font-weight:700;color:#bfe9df;}}.d1{{position:absolute;top:120px;left:120px;transform:rotate(-12deg);}}.d2{{position:absolute;bottom:150px;right:130px;}}'
    return W(css, f'<div class="wrap"><div class="d1">{spark(64,LIME)}</div><div class="d2">{spark(44,LIME)}</div><div class="leaf">🌿</div><div class="brand">GR<span class="hl">OU</span>ND</div><div class="sub">검색이 사라지는 시대의 마케팅<br>SEO·GEO·AEO, 쉽게 풀어드려요</div><div class="handle">@ground_geo</div><div class="cta">팔로우하고 다음 편도 받아보세요 👆</div></div>')

# 글별 콘텐츠 — 새 시리즈 만들 때 이 딕셔너리만 교체.
POSTS = {
    2: {"topic": "AEO · 답변 엔진 최적화", "intro": ("AI는 순위가 아니라 ", "답", "을 골라요", "그래서 요즘 'AEO(답변 엔진 최적화)'가 중요해졌어요."), "points": ("AEO 핵심 ", "3", "가지", ["질문–답 형식으로 쓰기", "출처·근거 확실하게", "FAQ 구조화(스키마)"]), "tip": ("오늘의 한 줄", '내 글을 <span class="hl">AI가 인용하기 쉽게</span> 정리하면 절반은 성공이에요.')},
    # ... 나머지 글은 같은 형식으로 추가 (topic, intro, points, tip)
}

def render(html, out):
    open(out + ".html", "w").write(html)
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--hide-scrollbars", f"--screenshot={out}.png", "--window-size=1080,1080", os.path.abspath(out + ".html")], check=True, capture_output=True)
    os.remove(out + ".html")

if __name__ == "__main__":
    cta_html = cta()
    for n, d in POSTS.items():
        render(intro(d["topic"], *d["intro"]), f"persona-nami/ig/post{n}-2")
        pa, ph, pb, items = d["points"]
        render(points(d["topic"], pa, ph, pb, items), f"persona-nami/ig/post{n}-3")
        render(tip(*d["tip"]), f"persona-nami/ig/post{n}-4")
        render(cta_html, f"persona-nami/ig/post{n}-5")
        print("cards for post", n)
