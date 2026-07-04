"""카톡/문자 자유 텍스트에서 고객정보 항목을 추출한다 (프로젝트 ①·② 공유).

추출 결과는 반드시 사용자 확인 게이트를 거친 뒤 사용한다.
항목별 신뢰도(confidence)를 함께 반환해 UI에서 강조 표시한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .validation import normalize_phone, normalize_birthdate, validate_rrn

__all__ = ["ParsedCustomer", "parse_customer_text"]

# 이름: 한글 2~4자 (성+이름). '고객', '이름' 라벨 뒤 우선.
_NAME_LABELED = re.compile(r"(?:성명|이름|고객명|가입자)\s*[:：]?\s*([가-힣]{2,4})")
_NAME_BARE = re.compile(r"(?<![가-힣])([가-힣]{2,4})(?![가-힣])")
_RRN = re.compile(r"\b(\d{6})[-\s]?([1-4]\d{6})\b")
_PHONE = re.compile(r"01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}")
_BIRTH = re.compile(r"(?:생년월일|생일)?\s*[:：]?\s*((?:19|20)?\d{2}[.\-/년\s]\s*\d{1,2}[.\-/월\s]\s*\d{1,2}일?)")
# 주소: '주소' 라벨 뒤 한 줄, 또는 시/도 + 구/군 패턴
_ADDR_LABELED = re.compile(r"주소\s*[:：]?\s*(.+)")
_ADDR_HINT = re.compile(r"([가-힣]+(?:특별시|광역시|특별자치시|도|시)\s?.+?(?:로|길|동|읍|면)\s?\S*.*)")


@dataclass
class ParsedCustomer:
    name: str | None = None
    phone: str | None = None
    birthdate: str | None = None          # YYYY-MM-DD
    address: str | None = None
    rrn: str | None = None                # 원문(민감) — 즉시 폐기 전제
    confidence: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def parse_customer_text(text: str) -> ParsedCustomer:
    text = (text or "").strip()
    out = ParsedCustomer()

    # 이름
    m = _NAME_LABELED.search(text)
    if m:
        out.name, out.confidence["name"] = m.group(1), 0.9
    else:
        # 라벨 없으면 첫 줄에서 조심스럽게 후보 추출
        first_line = text.splitlines()[0] if text else ""
        m2 = _NAME_BARE.search(first_line)
        if m2:
            out.name, out.confidence["name"] = m2.group(1), 0.5
            out.warnings.append("이름은 라벨 없이 추정됨 — 확인 필요")

    # 전화번호
    m = _PHONE.search(text)
    if m:
        norm = normalize_phone(m.group(0))
        out.phone = norm
        out.confidence["phone"] = 0.95 if norm else 0.4

    # 주민번호 (민감) + 생년월일 유도
    m = _RRN.search(text)
    if m:
        rrn = m.group(1) + m.group(2)
        out.rrn = rrn
        ok = validate_rrn(rrn)
        out.confidence["rrn"] = 0.95 if ok else 0.3
        if not ok:
            out.warnings.append("주민번호 검증(체크섬) 실패 — 오인식 가능")

    # 생년월일 (주민번호 있으면 그쪽 우선은 호출자에서 처리)
    m = _BIRTH.search(text)
    if m:
        bd = normalize_birthdate(m.group(1))
        if bd:
            out.birthdate, out.confidence["birthdate"] = bd.isoformat(), 0.85

    # 주소
    m = _ADDR_LABELED.search(text)
    if m:
        out.address, out.confidence["address"] = m.group(1).strip(), 0.85
    else:
        m = _ADDR_HINT.search(text)
        if m:
            out.address, out.confidence["address"] = m.group(1).strip(), 0.6
            out.warnings.append("주소는 라벨 없이 추정됨 — 확인 필요")

    return out
