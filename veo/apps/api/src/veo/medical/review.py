"""원고 검수 — 규칙을 텍스트에 대고, 사람이 읽어야 할 자리를 표시한다.

순수 함수다: 텍스트가 들어오면 발견 목록이 나온다. DB 도 통신도 없다 — 시험이
문장과 기대만으로 성질을 고정할 수 있어야 규칙을 고칠 때마다 무엇이 달라졌는지
보인다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, final

from veo.medical.rules import MEDICAL_REVIEW_RULES, ReviewRule

__all__ = ["DISCLAIMER_KO", "MedicalFinding", "review_copy"]

#: 모든 응답에 그대로 실린다 — 이 도구가 무엇이 아닌지가 무엇인지만큼 중요하다.
DISCLAIMER_KO: Final = (
    "이 결과는 의료법 제56조의 금지 유형에 해당할 수 있는 표현을 기계적으로 표시한 "
    "검토 신호이며, 법률 판단이 아닙니다. 표시가 없다고 적법한 것도, 표시가 있다고 "
    "위법한 것도 아닙니다. 게재 전 의료광고 심의 대상 여부와 문안의 적법성은 "
    "심의기구·전문가 확인을 거치십시오."
)

_ABSENCE_PREFIX: Final = "__ABSENCE__:"

#: 부재형 규칙이 "고지가 있다"고 인정하는 신호 — 이 단어들이 하나라도 있으면
#: 부작용 고지를 시도한 원고로 본다(문구의 충분성은 사람의 몫).
_SIDE_EFFECT_SIGNALS: Final = re.compile(r"(부작용|주의\s*사항|개인차|합병증|유의\s*사항)")

#: 발견 주변을 얼마나 보여줄 것인가 — 구절만 똑 떼면 왜 걸렸는지 안 보인다.
_CONTEXT_CHARS: Final = 40


@final
@dataclass(frozen=True, slots=True)
class MedicalFinding:
    """검토가 필요한 자리 하나."""

    rule_id: str
    category_ko: str
    guidance_ko: str
    reference_ko: str
    #: 걸린 구절 그대로. 부재형 규칙이면 무엇이 안 보이는지를 설명하는 문장.
    excerpt: str
    #: 원고 안에서의 위치(문자 오프셋). 부재형이면 None — 없는 것에는 자리가 없다.
    offset: int | None


def _excerpt_around(text: str, start: int, end: int) -> str:
    left = max(0, start - _CONTEXT_CHARS)
    right = min(len(text), end + _CONTEXT_CHARS)
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return f"{prefix}{text[left:right]}{suffix}"


def _apply_presence_rule(rule: ReviewRule, text: str) -> list[MedicalFinding]:
    findings: list[MedicalFinding] = []
    for match in rule.pattern.finditer(text):
        findings.append(
            MedicalFinding(
                rule_id=rule.rule_id,
                category_ko=rule.category_ko,
                guidance_ko=rule.guidance_ko,
                reference_ko=rule.reference_ko,
                excerpt=_excerpt_around(text, match.start(), match.end()),
                offset=match.start(),
            )
        )
    return findings


def _apply_absence_rule(rule: ReviewRule, text: str) -> list[MedicalFinding]:
    """대상 시술 언급은 있는데 고지 신호가 없을 때만 운다."""
    trigger = re.compile(rule.pattern.pattern.removeprefix(_ABSENCE_PREFIX))
    if trigger.search(text) is None:
        return []
    if _SIDE_EFFECT_SIGNALS.search(text) is not None:
        return []
    return [
        MedicalFinding(
            rule_id=rule.rule_id,
            category_ko=rule.category_ko,
            guidance_ko=rule.guidance_ko,
            reference_ko=rule.reference_ko,
            excerpt=(
                "시술·수술을 다루는 원고인데 부작용·주의사항·개인차 언급이 보이지 않습니다."
            ),
            offset=None,
        )
    ]


def review_copy(text: str) -> list[MedicalFinding]:
    """원고 하나를 전 규칙에 대고, 발견을 원고 내 위치 순으로 돌려준다."""
    findings: list[MedicalFinding] = []
    for rule in MEDICAL_REVIEW_RULES:
        if rule.pattern.pattern.startswith(_ABSENCE_PREFIX):
            findings.extend(_apply_absence_rule(rule, text))
        else:
            findings.extend(_apply_presence_rule(rule, text))
    # 부재형(offset=None)은 맨 뒤 — 원고를 따라 읽는 순서를 깨지 않는다.
    return sorted(findings, key=lambda f: (f.offset is None, f.offset or 0))
