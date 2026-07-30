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

#: Fewer than this and the set cannot span the intents, so a rate over it means little.
MIN_PROMPTS_PER_SET = 5

#: No single intent may exceed this share of the set.
MAX_SINGLE_INTENT_SHARE = 0.5

#: Brand-name questions almost guarantee a mention; they measure recall, not visibility.
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


class Funnel(StrEnum):
    PROBLEM_AWARE = "PROBLEM_AWARE"
    RESEARCH = "RESEARCH"
    COMPARISON = "COMPARISON"
    RECOMMENDATION = "RECOMMENDATION"
    PURCHASE_OR_VISIT = "PURCHASE_OR_VISIT"
    AFTERCARE = "AFTERCARE"


class Subject(StrEnum):
    BRAND = "BRAND"
    NON_BRAND = "NON_BRAND"
    COMPETITOR = "COMPETITOR"
    CATEGORY = "CATEGORY"


#: Intents a set may not omit. Leaving these out is the cheapest way to flatter a brand.
REQUIRED_INTENTS = frozenset({Intent.TRUST, Intent.COMPARISON})

_INTENT_LABELS_KO = {
    Intent.DEFINITION: "정의",
    Intent.HOW_TO: "방법",
    Intent.BEST_OR_RECOMMENDED: "추천",
    Intent.COMPARISON: "비교",
    Intent.PRICE: "가격",
    Intent.LOCAL: "지역",
    Intent.TRUST: "신뢰·안전",
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
