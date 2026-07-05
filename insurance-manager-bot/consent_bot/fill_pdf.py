"""프로젝트 ① — 고정 양식(가입설계동의서)에 좌표 기반 자동 기재.

입력: 저장한 원본 동의서 PDF(2장) + 고객/사용인 정보
출력: 동의함 표시 + 서명일 + 성명 + 서명 + 전화번호 + 사용인 서명이 기재된 PDF

주의(§4.3): 서명은 '동의를 이미 받은' 전제 하에 기재한다. 봇은 서식 작성만 담당하며,
동의 확보의 책임은 사용인/프로그램 사용자에게 있다. 동의 증빙은 별도 audit trail로 보관.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import os
import sys

import fitz  # PyMuPDF

_HERE = Path(__file__).parent
_TEMPLATE_PATH = _HERE / "template.json"
_FONT_ALIAS = "kr"


def _resolve_font() -> str:
    """한글 폰트 경로를 이식성 있게 탐색(Windows exe/리눅스/맥 공통).

    우선순위: 환경변수 → 번들(assets, PyInstaller _MEIPASS) → OS 시스템 폰트.
    """
    candidates = []
    if os.environ.get("IMB_FONT"):
        candidates.append(os.environ["IMB_FONT"])
    # 번들 폰트(패키징 시 포함)
    bundled = Path(getattr(sys, "_MEIPASS", _HERE.parent)) / "assets" / "NanumGothic.ttf"
    candidates.append(str(bundled))
    candidates.append(str(_HERE.parent / "assets" / "NanumGothic.ttf"))
    # OS 시스템 폰트
    candidates += [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",   # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",       # Linux fallback(CJK)
        r"C:\Windows\Fonts\malgun.ttf",                        # Windows 맑은 고딕
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",          # macOS
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError(
        "한글 폰트를 찾지 못했습니다. assets/NanumGothic.ttf를 두거나 IMB_FONT 환경변수를 설정하세요."
    )


_FONT = _resolve_font()
_HAND_ALIAS = "hw"


def _resolve_hand_font() -> str:
    """한글 손글씨 폰트 경로 탐색(펜 글씨체). 없으면 기본 고딕으로 대체."""
    candidates = []
    if os.environ.get("IMB_HAND_FONT"):
        candidates.append(os.environ["IMB_HAND_FONT"])
    bundled = Path(getattr(sys, "_MEIPASS", _HERE.parent)) / "assets" / "NanumPen.ttf"
    candidates.append(str(bundled))
    candidates.append(str(_HERE.parent / "assets" / "NanumPen.ttf"))
    candidates += [
        "/usr/share/fonts/truetype/nanum/NanumPen.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunpenR.ttf",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return _FONT  # 손글씨 폰트 없으면 고딕으로 대체(동작 보장)


_HAND_FONT = _resolve_hand_font()


@dataclass
class ConsentData:
    customer_name: str
    phone: str
    agent_name: str               # 사용인(FC) 성명 — 서명 기재용
    sign_date: date | None = None  # 서명일(기본: 오늘)
    circle_all: bool = True        # 모든 '동의함' 표시 여부
    # circle_all=False일 때 표시할 라벨만 지정
    circle_labels: list[str] | None = None


def load_template(path: str | Path = _TEMPLATE_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


import random

# 동의함 단어 rect → 왼쪽 체크박스(정사각형) 좌표 추정.
# 양식 실측: 동의함 글자 시작 x0 기준으로 박스 우변이 약 4pt 왼쪽, 한 변 ~19.8pt.
_BOX_SIDE = 19.8
_BOX_GAP = 4.0


def _checkbox_from_anchor(word_rect):
    x0, _, _, _ = word_rect
    y_center = (word_rect[1] + word_rect[3]) / 2
    bx1 = x0 - _BOX_GAP
    bx0 = bx1 - _BOX_SIDE
    by0 = y_center - _BOX_SIDE / 2
    by1 = y_center + _BOX_SIDE / 2
    return (bx0, by0, bx1, by1)


def _hand_check(page: fitz.Page, box, seed: int) -> None:
    """체크박스 안에 '펜으로 직접 그은 듯한' V 체크를 그린다.

    seed마다 꼭짓점 위치·기울기·획 두께가 조금씩 달라 손으로 한 것처럼 보인다.
    팩스(흑백)를 고려해 진한 잉크색 사용.
    """
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0

    def jit(v, amt=1.1):
        return v + rng.uniform(-amt, amt)

    # V 체크의 세 꼭짓점(박스 내부 비율 + 지터). p3는 약간 박스 위로 올라가 자연스럽게.
    p1 = (jit(x0 + w * rng.uniform(0.10, 0.24)), jit(y0 + h * rng.uniform(0.38, 0.52)))
    p2 = (jit(x0 + w * rng.uniform(0.33, 0.45)), jit(y1 - h * rng.uniform(0.10, 0.22)))
    p3 = (jit(x1 - w * rng.uniform(0.00, 0.14)), jit(y0 + h * rng.uniform(-0.12, 0.06)))

    def lerp(a, b, t):
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    # 직선이 아니라 미세하게 흔들리는 획(중간 보간점에 지터)
    pts = [p1]
    m = lerp(p1, p2, 0.55)
    pts.append((jit(m[0], 0.7), jit(m[1], 0.7)))
    pts.append(p2)
    for t in (0.4, 0.75):
        m = lerp(p2, p3, t)
        pts.append((jit(m[0], 0.7), jit(m[1], 0.7)))
    pts.append(p3)

    width = rng.uniform(1.1, 1.9)
    ink = (0.10, 0.11, 0.16)  # 진한 남색 계열의 볼펜 느낌(흑백 팩스에서도 진함)
    page.draw_polyline(pts, color=ink, width=width, lineCap=1, lineJoin=1)


_INK = (0.10, 0.11, 0.16)


def _hand_text(page: fitz.Page, x: float, y: float, text: str, size: float,
               seed: int, font: "fitz.Font") -> None:
    """손글씨 폰트로 글자마다 크기·기울기·상하 위치를 미세하게 달리해 기재한다.

    사람이 펜으로 쓴 것처럼 글자별 흔들림을 준다.
    """
    rng = random.Random(seed)
    cx = x
    baseline_drift = 0.0
    for ch in text:
        if ch == " ":
            cx += size * 0.4
            continue
        fs = size * rng.uniform(0.90, 1.10)
        baseline_drift += rng.uniform(-0.5, 0.5)          # 줄이 미세하게 물결치듯
        dy = baseline_drift + rng.uniform(-0.8, 0.8)
        ang = rng.uniform(-7, 7)                           # 글자별 기울기
        pivot = fitz.Point(cx, y + dy)
        page.insert_text((cx, y + dy), ch, fontname=_HAND_ALIAS, fontsize=fs,
                         color=_INK, morph=(pivot, fitz.Matrix(ang)))
        adv = font.text_length(ch, fontsize=fs) * rng.uniform(0.98, 1.12)
        cx += max(adv, fs * 0.35)


def fill_consent_pdf(
    src_pdf: str | Path,
    dst_pdf: str | Path,
    data: ConsentData,
    template: dict | None = None,
) -> Path:
    tpl = template or load_template()
    doc = fitz.open(src_pdf)
    if doc.page_count < tpl["pages"]:
        raise ValueError(
            f"양식 페이지 수 불일치: 기대 {tpl['pages']}, 실제 {doc.page_count}. "
            "다른 양식이거나 저장 오류일 수 있습니다."
        )

    for page in doc:
        page.insert_font(fontname=_FONT_ALIAS, fontfile=_FONT)
        page.insert_font(fontname=_HAND_ALIAS, fontfile=_HAND_FONT)
    hand_font = fitz.Font(fontfile=_HAND_FONT)

    # 1) 동의함 표시 — 박스 안에 손으로 그은 듯한 V 체크(매번 조금씩 다르게)
    labels = set(data.circle_labels or [])
    for i, item in enumerate(tpl["consent_circles"]):
        if data.circle_all or item["label"] in labels:
            box = _checkbox_from_anchor(item["rect"])
            _hand_check(doc[item["page"]], box, seed=1000 + item["page"] * 50 + i)

    # 2) 텍스트 기재 — 이름·연락처·서명·날짜를 손글씨로(글자마다 다르게)
    d = data.sign_date or date.today()
    # 전화번호는 항상 하이픈 형식으로 정리(엔진 직접 호출 시에도 일관되게)
    from common.validation import normalize_phone
    phone = normalize_phone(data.phone) or data.phone
    values = {
        "sign_year": f"{d.year % 100:02d}",
        "sign_month": f"{d.month:02d}",
        "sign_day": f"{d.day:02d}",
        "cust_name": data.customer_name,
        "cust_sign": data.customer_name,   # 서명란에 고객명 기재
        "cust_phone": phone,
        "agent_sign": data.agent_name,
    }
    for si, (key, spec) in enumerate(tpl["text_fields"].items()):
        text = values.get(key, "")
        if not text:
            continue
        page = doc[spec["page"]]
        _hand_text(page, spec["x"], spec["y"], text, spec["size"],
                   seed=hash(key) & 0xFFFF, font=hand_font)

    dst = Path(dst_pdf)
    doc.save(dst, garbage=4, deflate=True)
    doc.close()
    return dst


def verify_layout(src_pdf: str | Path, template: dict | None = None) -> list[str]:
    """양식 정합성 검증: 페이지 수 + '동의함' 앵커가 기대 좌표 근처에 있는지 확인.

    양식 개정으로 좌표가 어긋나면 기재 전에 잡아낸다.
    """
    tpl = template or load_template()
    doc = fitz.open(src_pdf)
    problems: list[str] = []
    if doc.page_count != tpl["pages"]:
        problems.append(f"페이지 수 {doc.page_count} != 기대 {tpl['pages']}")
    for item in tpl["consent_circles"]:
        page = doc[item["page"]]
        cx = (item["rect"][0] + item["rect"][2]) / 2
        cy = (item["rect"][1] + item["rect"][3]) / 2
        hit = page.get_text("words", clip=fitz.Rect(cx - 20, cy - 8, cx + 20, cy + 8))
        if not any("동의함" in w[4] for w in hit):
            problems.append(f"'동의함' 앵커 확인 실패: {item['label']} (p{item['page']})")
    doc.close()
    return problems
