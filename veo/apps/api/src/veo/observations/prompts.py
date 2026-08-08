"""The questions VEO asks AI engines, and the rules that stop them being chosen to flatter.

Every number in an AI visibility report is downstream of this file. Nobody has to
falsify a figure to produce a dishonest report — they only have to choose the questions.
Ask where the client is strong, skip where they are weak, and the arithmetic stays
perfect while the conclusion becomes false. That failure leaves no trace in the data.

Four rules make the set answerable for itself:

* **Balance is checked, not asserted.** A set has to span intents rather than pile into
  "best/recommended", and it must include the trust questions — 부작용, 후기, 안전 —
  that a brand has every incentive to avoid.
* **A set is frozen and checksummed.** Two brands compared in one report are measured
  with byte-identically the same questions, and the checksum proves it.
* **Every exclusion carries a written reason** and produces a *different* set with a
  different checksum. Narrowing is legitimate; narrowing silently is not.
* **Business importance is an analyst's estimate and is named as one.** It never shares a
  field with measured search volume, which lives in the keyword engine with its own
  source and quality flags.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# 아래 넷의 근거: docs/adr/0015-prompt-sets-are-audited-artefacts.md (ADR 0015, 2026-07-28)
#
# ADR 이 대는 이유는 조작 방지다:
#
#   > 경쟁 비교를 조작하는 데 숫자를 위조할 필요가 없다. **질문만 고르면 된다.**
#   > 고객이 잘 나오는 "서초 임플란트 잘하는 곳"은 묻고, 잘 안 나오는 "임플란트
#   > 부작용"은 뺀다. 이후 모든 계산은 산술적으로 완벽하고 결론은 거짓이다.
#   > 그리고 이 실패는 데이터에 아무 흔적을 남기지 않는다.
#
# **이 숫자들은 통계나 외부 연구에서 나온 값이 아니다.** 우리가 그날 정한 바닥값이고,
# ADR 도 왜 5이고 왜 50%인지는 적지 않았다. 바꾸려면 ADR 을 고쳐야 하고, 고칠 때는
# 그 숫자여야 하는 이유를 대야 한다.
#
# 여기 근거를 적어 두는 것 자체가 관문이다 — 2026-08-08 에 나는 이 규칙이 참인 것은
# 확인하고서 **왜 그런지는 지어내서** 설명했다("3개로는 균형을 맞출 수 없다" — 실제로는
# 맞출 수 있고 개수만 걸린다). ADR 을 찾아보지 않았기 때문이다.
# `tests/test_thresholds_cite_a_decision.py` 가 이 인용이 사라지지 않게 지킨다.
# 사례: docs/CORRECTIONS.md 7·8번.
# ─────────────────────────────────────────────────────────────────────────────

#: 최소 질문 수. 이보다 적으면 그 몇 개가 곧 결론이 된다. [ADR 0015]
MIN_PROMPTS_PER_SET = 5

#: No single intent may exceed this share of the set. [ADR 0015]
MAX_SINGLE_INTENT_SHARE = 0.5

#: Brand-name questions almost guarantee a mention; they measure recall, not visibility.
#: [ADR 0015]
MAX_BRAND_SUBJECT_SHARE = 0.5


class Intent(StrEnum):
    """What the asker wants. Drawn from the VEO-LAB prompt taxonomy."""

    DEFINITION = "DEFINITION"
    HOW_TO = "HOW_TO"
    BEST_OR_RECOMMENDED = "BEST_OR_RECOMMENDED"
    COMPARISON = "COMPARISON"
    PRICE = "PRICE"
    LOCAL = "LOCAL"
    #: 부작용, 후기, 안전 — the questions a brand most wants left out.
    TRUST = "TRUST"
    #: 아무도 분류하지 않았다. **비교용 집합에서는 거부된다** — `describe_balance` 를 볼 것.
    #:
    #: 이 값이 있는 이유는 수동 측정 때문이다. 관리자가 "지금 이 검색어로 우리가 나오나"
    #: 를 물을 때 의도를 함께 고르게 하는 것은 군더더기이고, 그렇다고 서버가 대신 골라
    #: 넣으면 **분석가가 판단한 것처럼 저장된다.** 모르는 것은 모른다고 적는다.
    UNCLASSIFIED = "UNCLASSIFIED"


class Funnel(StrEnum):
    #: 위 `Intent.UNCLASSIFIED` 와 같은 이유. 비교용 집합에서는 거부된다.
    UNCLASSIFIED = "UNCLASSIFIED"
    PROBLEM_AWARE = "PROBLEM_AWARE"
    RESEARCH = "RESEARCH"
    COMPARISON = "COMPARISON"
    RECOMMENDATION = "RECOMMENDATION"
    PURCHASE_OR_VISIT = "PURCHASE_OR_VISIT"
    AFTERCARE = "AFTERCARE"


class Subject(StrEnum):
    #: 위 `Intent.UNCLASSIFIED` 와 같은 이유. 비교용 집합에서는 거부된다.
    #:
    #: 특히 여기서 함부로 `NON_BRAND` 를 넣으면 안 된다. 관리자가 넣은 검색어가 브랜드명일
    #: 수도 있고, 그러면 브랜드 질문 비중 상한이 실제보다 낮게 계산된다.
    UNCLASSIFIED = "UNCLASSIFIED"
    BRAND = "BRAND"
    NON_BRAND = "NON_BRAND"
    COMPETITOR = "COMPETITOR"
    CATEGORY = "CATEGORY"


#: Intents a set may not omit. Leaving these out is the cheapest way to flatter a brand.
#:
#: 근거 [ADR 0015]: "신뢰·안전(부작용·후기)과 비교 의도는 필수다. 브랜드가 가장 빼고
#: 싶어 하는 질문이고, 빼면 노출률이 실제보다 높게 나온다."
REQUIRED_INTENTS = frozenset({Intent.TRUST, Intent.COMPARISON})

_INTENT_LABELS_KO = {
    Intent.DEFINITION: "정의",
    Intent.HOW_TO: "방법",
    Intent.BEST_OR_RECOMMENDED: "추천",
    Intent.COMPARISON: "비교",
    Intent.PRICE: "가격",
    Intent.LOCAL: "지역",
    Intent.TRUST: "신뢰·안전",
    Intent.UNCLASSIFIED: "분류 안 함",
}


class PromptSetImbalanceError(ValueError):
    """The set cannot support an honest comparison."""


@dataclass(frozen=True, slots=True)
class Prompt:
    """One question, classified so the set's balance can be measured."""

    text: str
    intent: Intent
    funnel: Funnel
    subject: Subject
    #: An analyst's judgement of how much this question matters to the business, 0 to 1.
    #: Deliberately *not* a demand figure: a guess and a Naver measurement must never
    #: share a field, or the guess eventually gets read as data.
    business_importance: float = 0.5
    locale: str = "ko-KR"
    persona: str | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("prompt text cannot be empty")
        if not 0.0 <= self.business_importance <= 1.0:
            raise ValueError("business_importance must be between 0 and 1")

    @property
    def prompt_id(self) -> str:
        """Stable across runs, so repeated measurement of the same question lines up."""
        payload = json.dumps(
            {
                "text": self.text.strip(),
                "intent": str(self.intent),
                "funnel": str(self.funnel),
                "subject": str(self.subject),
                "locale": self.locale,
                "persona": self.persona,
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "text": self.text,
            "intent": str(self.intent),
            "funnel": str(self.funnel),
            "subject": str(self.subject),
            "business_importance": self.business_importance,
            "locale": self.locale,
            "persona": self.persona,
        }


@dataclass(frozen=True, slots=True)
class Exclusion:
    """A prompt removed from a set, and why."""

    prompt_id: str
    text: str
    reason_ko: str

    def as_dict(self) -> dict[str, Any]:
        return {"prompt_id": self.prompt_id, "text": self.text, "reason_ko": self.reason_ko}


@dataclass(frozen=True, slots=True)
class PromptSet:
    """A frozen, checksummed set of questions shared by every brand in a comparison."""

    name: str
    prompts: tuple[Prompt, ...]
    exclusions: tuple[Exclusion, ...] = field(default=())
    checksum: str = ""

    @classmethod
    def build(
        cls,
        *,
        name: str,
        prompts: Sequence[Prompt],
        exclusions: Sequence[Exclusion] = (),
    ) -> PromptSet:
        problems = cls.describe_balance(prompts)
        if problems:
            raise PromptSetImbalanceError(
                "프롬프트 집합이 공정한 비교에 쓰기 어렵습니다 — " + " / ".join(problems)
            )

        ordered = tuple(sorted(prompts, key=lambda p: p.prompt_id))
        return cls(
            name=name,
            prompts=ordered,
            exclusions=tuple(exclusions),
            checksum=cls._checksum(name, ordered, tuple(exclusions)),
        )

    @classmethod
    def ad_hoc(cls, *, name: str, prompts: Sequence[Prompt]) -> PromptSet:
        """관리자가 그 자리에서 고른 검색어 몇 개. **균형을 검사하지 않는다.**

        `build` 의 관문을 무르는 것이 아니다. 그 관문은 **비교와 추이**를 지키는 것이고,
        이 집합은 둘 중 어디에도 못 들어간다 — 이 집합으로 만든 실행은
        `kind=MANUAL` 이 되고, `runs.aggregate_rate` 가 정기 측정과 섞이는 것을 거부한다.

        검사할 것이 없어서 안 하는 것도 아니다. 질문 한 개짜리 집합에 "한 의도가 50%를
        넘을 수 없다" 를 적용하면 언제나 실패한다. 규칙이 지키려는 것(고른 질문으로
        결론을 만들지 못하게)은 여기서 **다른 방법으로** 지켜진다: 이 값은 애초에
        결론이 되는 자리에 못 간다.

        빈 집합은 여전히 거부한다. 질문이 없으면 잴 것이 없다.
        """
        if not prompts:
            raise PromptSetImbalanceError("질문이 하나도 없습니다. 잴 것이 없습니다")

        ordered = tuple(sorted(prompts, key=lambda prompt: prompt.prompt_id))
        return cls(name=name, prompts=ordered, checksum=cls._checksum(name, ordered, ()))

    @classmethod
    def rebuild(cls, *, name: str, prompts: Sequence[Prompt]) -> PromptSet:
        """이미 발행된 집합을 저장소에서 되살린다. 균형은 다시 검사하지 않는다.

        `build` 는 새 집합을 만들 때의 문지기다. 저장된 집합에까지 그것을 적용하면,
        규칙이 나중에 엄격해졌을 때 **과거에 적법하게 발행된 집합이 소급해서 거부되고**
        그 집합으로 잰 결과를 다시 열 수 없게 된다. 발행본은 그때의 규칙으로 설명한다.
        """
        ordered = tuple(sorted(prompts, key=lambda prompt: prompt.prompt_id))
        return cls(name=name, prompts=ordered, checksum=cls._checksum(name, ordered, ()))

    # ----------------------------------------------------------------- #
    # Balance
    # ----------------------------------------------------------------- #

    @staticmethod
    def describe_balance(prompts: Sequence[Prompt]) -> list[str]:
        """Every reason this set would not support an honest comparison, in Korean."""
        problems: list[str] = []
        total = len(prompts)

        if total < MIN_PROMPTS_PER_SET:
            problems.append(f"질문이 {total}개뿐입니다. 최소 {MIN_PROMPTS_PER_SET}개가 필요합니다")
            return problems

        # 분류가 안 된 질문이 하나라도 있으면 이 집합은 균형을 말할 수 없다. 비중을
        # 세는 계산이 전부 분류 위에 서 있기 때문이다 — 모르는 것을 한쪽으로 접어 세면
        # 그 순간 비중이 사실이 아니게 된다.
        unclassified = sum(
            1
            for p in prompts
            if p.intent is Intent.UNCLASSIFIED
            or p.funnel is Funnel.UNCLASSIFIED
            or p.subject is Subject.UNCLASSIFIED
        )
        if unclassified:
            problems.append(
                f"분류하지 않은 질문이 {unclassified}개 있습니다. 의도·단계·대상을 매기지 "
                "않으면 균형을 잴 수 없습니다"
            )

        present = {p.intent for p in prompts}
        missing = sorted(REQUIRED_INTENTS - present, key=lambda i: i.value)
        if missing:
            names = ", ".join(_INTENT_LABELS_KO[intent] for intent in missing)
            problems.append(
                f"{names} 의도의 질문이 없습니다. 브랜드에 불리한 질문을 빼면 "
                "노출률이 실제보다 높게 나옵니다"
            )

        for intent in Intent:
            share = sum(1 for p in prompts if p.intent is intent) / total
            if share > MAX_SINGLE_INTENT_SHARE:
                problems.append(
                    f"{_INTENT_LABELS_KO[intent]} 의도가 전체의 {share:.0%}를 차지합니다 "
                    f"(상한 {MAX_SINGLE_INTENT_SHARE:.0%})"
                )

        brand_share = sum(1 for p in prompts if p.subject is Subject.BRAND) / total
        if brand_share > MAX_BRAND_SUBJECT_SHARE:
            problems.append(
                f"브랜드명이 들어간 질문이 전체의 {brand_share:.0%}입니다. 브랜드를 직접 "
                "물으면 언급은 거의 보장되므로 가시성이 아니라 재인지를 재게 됩니다"
            )

        return problems

    # ----------------------------------------------------------------- #
    # Narrowing
    # ----------------------------------------------------------------- #

    def excluding(self, prompt_id: str, *, reason_ko: str) -> PromptSet:
        """Remove a prompt, recording why. The result is a different set."""
        if not reason_ko.strip():
            raise ValueError("제외 사유를 반드시 남겨야 합니다")

        target = next((p for p in self.prompts if p.prompt_id == prompt_id), None)
        if target is None:
            raise KeyError(prompt_id)

        remaining = [p for p in self.prompts if p.prompt_id != prompt_id]
        return PromptSet.build(
            name=self.name,
            prompts=remaining,
            exclusions=(
                *self.exclusions,
                Exclusion(prompt_id=prompt_id, text=target.text, reason_ko=reason_ko.strip()),
            ),
        )

    # ----------------------------------------------------------------- #
    # Comparison
    # ----------------------------------------------------------------- #

    def is_same_set_as(self, other: PromptSet) -> bool:
        """Whether two brands were asked byte-identically the same questions."""
        return self.checksum == other.checksum

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "checksum": self.checksum,
            "prompt_count": len(self.prompts),
            "prompts": [p.as_dict() for p in self.prompts],
            "exclusions": [e.as_dict() for e in self.exclusions],
        }

    @staticmethod
    def _checksum(name: str, prompts: tuple[Prompt, ...], exclusions: tuple[Exclusion, ...]) -> str:
        payload = json.dumps(
            {
                "name": name,
                "prompts": sorted(p.prompt_id for p in prompts),
                "exclusions": sorted(e.prompt_id for e in exclusions),
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
