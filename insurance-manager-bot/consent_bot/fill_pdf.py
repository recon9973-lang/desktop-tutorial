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


def _circle(page: fitz.Page, rect, pad_x: float = 6.0, pad_y: float = 3.5) -> None:
    """동의함 단어를 타원으로 감싼다(선택 표시). 팩스 흑백에서 선명한 방식."""
    x0, y0, x1, y1 = rect
    oval = fitz.Rect(x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y)
    page.draw_oval(oval, color=(0, 0, 0), width=1.3)


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

    # 1) 동의함 표시
    labels = set(data.circle_labels or [])
    for item in tpl["consent_circles"]:
        if data.circle_all or item["label"] in labels:
            _circle(doc[item["page"]], item["rect"])

    # 2) 텍스트 기재
    d = data.sign_date or date.today()
    values = {
        "sign_year": f"{d.year % 100:02d}",
        "sign_month": f"{d.month:02d}",
        "sign_day": f"{d.day:02d}",
        "cust_name": data.customer_name,
        "cust_sign": data.customer_name,   # 서명란에 고객명 기재
        "cust_phone": data.phone,
        "agent_sign": data.agent_name,
    }
    for key, spec in tpl["text_fields"].items():
        text = values.get(key, "")
        if not text:
            continue
        page = doc[spec["page"]]
        page.insert_text(
            (spec["x"], spec["y"]),
            text,
            fontname=_FONT_ALIAS,
            fontsize=spec["size"],
            color=(0, 0, 0),
        )

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
