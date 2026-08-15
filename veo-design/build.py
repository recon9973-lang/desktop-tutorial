#!/usr/bin/env python3
"""샘플 화면들을 한 파일짜리 HTML 로 묶는다.

왜 필요한가 — samples/ 의 화면들은 CSS 를 상대경로로 부른다. 파일 하나만 떼어
보내면 스타일이 안 붙는다. 여기서 CSS 를 안에 박아 어디서 열어도 같게 만든다.

원본은 samples/ 하나뿐이다. 이 스크립트는 **읽기만 한다** — 손으로 옮겨 적은
사본을 만들지 않는다. 사본을 만들면 둘이 갈라지고, 갈라진 쪽을 사장님이 본다.

    python3 veo-design/build.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
OUT = ROOT / "샘플-B안-480px.html"

SCREENS = [
    ("b-clinical/empty.html", "화면 1 — 빈 화면",
     "지금은 본문 83자. 여기는 채점 기준을 진단 전에 먼저 공개한다."),
    ("b-clinical/result.html", "화면 2 — 결과",
     "점수보다 할 일이 먼저. 근거·고칠 코드는 접어 두고 펼치면 나온다."),
]

CSS_FILES = ["tokens.css", "base.css", "b-clinical/clinical.css"]

BODY_RE = re.compile(r"<body[^>]*>(.*)</body>", re.S)


def body_of(path: Path) -> str:
    match = BODY_RE.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"{path} 에 <body> 가 없다")
    return match.group(1).strip()


def main() -> None:
    css = "\n\n".join(
        f"/* ===== {name} ===== */\n{(SAMPLES / name).read_text(encoding='utf-8')}"
        for name in CSS_FILES
    )

    frames = []
    for rel, title, note in SCREENS:
        frames.append(
            f'<figure class="frame">\n'
            f'  <figcaption><b>{title}</b><span>{note}</span></figcaption>\n'
            f'  <div class="viewport" data-gauge="geo">\n{body_of(SAMPLES / rel)}\n  </div>\n'
            f"</figure>"
        )

    OUT.write_text(
        PAGE.replace("{{CSS}}", css).replace("{{FRAMES}}", "\n\n".join(frames)),
        encoding="utf-8",
    )
    print(f"썼다: {OUT}  ({OUT.stat().st_size // 1024} KB)")


PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VEO 화면 샘플 — B안 진단서 · 480px</title>
<style>
{{CSS}}

/* ── 이 배포본에만 있는 겉틀. 화면 자체의 CSS 는 위에서 끝났다. ── */
html { background: var(--veo-color-bg-subtle); }
body {
  margin: 0;
  padding: var(--veo-space-6) var(--veo-space-5) var(--veo-space-12);
  background: var(--veo-color-bg-subtle);
}
.pageHead { max-width: var(--veo-layout-prose); }
.pageHead h1 { font-size: var(--veo-font-size-700); }
.pageHead p { margin-top: var(--veo-space-2); font-size: var(--veo-font-size-300); color: var(--veo-color-text-muted); }
.gates { display: flex; flex-wrap: wrap; gap: var(--veo-space-2); margin-top: var(--veo-space-4); }
.gates span {
  padding: var(--veo-space-1) var(--veo-space-3);
  border-radius: var(--veo-radius-pill);
  background: var(--veo-status-pass-bg);
  border: 1px solid var(--veo-status-pass-border);
  color: var(--veo-status-pass-fg);
  font-size: var(--veo-font-size-100);
  font-weight: var(--veo-weight-semibold);
}
.deck { display: flex; flex-wrap: wrap; gap: var(--veo-space-8); margin-top: var(--veo-space-8); }
.frame { flex: none; width: 480px; max-width: 100%; margin: 0; }
.frame figcaption { margin-bottom: var(--veo-space-3); }
.frame figcaption b { display: block; font-size: var(--veo-font-size-500); letter-spacing: var(--veo-tracking-tight); }
.frame figcaption span { display: block; margin-top: var(--veo-space-1); font-size: var(--veo-font-size-200); color: var(--veo-color-text-muted); }
/* 480px 폭을 실제로 강제한다 — 화면 안의 반응형 규칙이 이 폭 기준으로 걸리게. */
.viewport {
  width: 480px;
  max-width: 100%;
  border: 1px solid var(--veo-color-border);
  border-radius: var(--veo-radius-lg);
  background: var(--veo-color-bg);
  box-shadow: var(--veo-shadow-2);
  overflow: hidden;
}
.viewport .sampleFlag { position: static; }
</style>
</head>
<body>

<header class="pageHead">
  <h1>B안 — 진단서</h1>
  <p>
    방향 3안 중 첫째. 파는 것은 <b>신뢰</b>. 폭 480px 기준으로 그렸다.
    숫자는 지어낸 값이고, 채점 영역·가중치·등급은 실제 명세
    <b>veo.geo.readiness 1.3.0</b> 에서 그대로 가져왔다.
  </p>
  <div class="gates">
    <span>토큰 우회 0줄</span>
    <span>hex·rgba·px 글자크기 0개</span>
    <span>veo/ 코드 수정 0줄</span>
  </div>
</header>

<div class="deck">
{{FRAMES}}
</div>

</body>
</html>
"""


if __name__ == "__main__":
    main()
