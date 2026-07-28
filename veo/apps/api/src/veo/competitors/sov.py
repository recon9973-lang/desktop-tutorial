"""Share of Voice — observed AI visibility, and only that.

This module deals in one kind of fact: what the answer engines actually did. It knows
nothing about how well a site is built, and it must stay that way. Structural quality and
observed visibility are separate measurements, they move for different reasons, and a
product that blends them into one figure can no longer tell a customer which of the two
to fix.

Three rules, each of which exists because the alternative is a number that lies.

**A zero denominator is 데이터 없음, never 0%.** If no brand in the set was cited by any
engine, the honest statement is "there is no data", not "we hold 0% of citations". The
first invites another measurement; the second invites a panicked budget meeting about a
number that was never measured. A participant who scored zero *inside a set that was
cited* really is 0.0% — that is a measurement, and it is reported as one.

**The set is part of the number.** Share of voice is relative by construction: add a
competitor and everyone else's share falls, with no change whatsoever in the underlying
observation. So every value here travels with the set it was computed over and a note
saying so, and dropping a competitor visibly changes the answer.

**An impossible observation is refused, not averaged.** More citations than answers, or
more winners than decided prompts, means the counting upstream is wrong. Computing a
share from it would launder a bug into a percentage.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

#: What a share is called when there is nothing to divide by. Never rendered as a number.
NO_DATA_KO = "데이터 없음"

SET_NOTE_KO = (
    "이 점유율은 아래 비교 집합 안에서의 상대값입니다. 같은 관측 결과라도 집합에 브랜드를 "
    "넣거나 빼면 모든 값이 달라집니다. 집합을 밝히지 않은 점유율 수치는 의미가 없습니다."
)

SCOPE_KO = (
    "관측된 AI 가시성입니다. 실제 엔진 응답에서 인용·언급된 횟수를 센 값이며, SEO·GEO "
    "준비도 점수와 더하거나 대체할 수 없습니다. 두 값은 별개의 측정입니다."
)

_NO_CITATION_KO = (
    "비교 집합 안의 어떤 브랜드도 인용되지 않았습니다. 점유율 0%가 아니라 나눌 분모가 "
    "없는 상태입니다."
)
_NO_MENTION_KO = (
    "비교 집합 안의 어떤 브랜드도 언급되지 않았습니다. 점유율 0%가 아니라 나눌 분모가 "
    "없는 상태입니다."
)
_NO_DECIDED_PROMPT_KO = (
    "승자를 판정할 수 있는 프롬프트가 없습니다. 승률 0%가 아니라 계산할 분모가 없는 "
    "상태입니다."
)


@dataclass(frozen=True, slots=True)
class ParticipantVisibility:
    """One brand's observed counts. Counts of *answers*, not of occurrences.

    An answer that names a brand four times is one visible answer, not four: repeating a
    name does not make a brand more visible to the person reading it.
    """

    key: str
    label_ko: str
    is_own_brand: bool
    cited_answer_count: int
    mentioned_answer_count: int
    won_prompt_count: int

    def __post_init__(self) -> None:
        for name in ("cited_answer_count", "mentioned_answer_count", "won_prompt_count"):
            if getattr(self, name) < 0:
                raise ValueError(f"{self.key}: {name}에 음수가 들어올 수 없습니다.")
        if not self.key.strip():
            raise ValueError("참여자 키가 비어 있습니다.")


@dataclass(frozen=True, slots=True)
class ObservedVisibility:
    """One measurement window: a prompt set, a set of engines, and what was seen."""

    prompt_set_label: str
    engine_labels: tuple[str, ...]
    observed_answer_count: int
    decided_prompt_count: int
    """Prompts where a winner could actually be determined. The winning-rate denominator."""
    participants: tuple[ParticipantVisibility, ...]

    def __post_init__(self) -> None:
        if not self.participants:
            raise ValueError(
                "비교 집합이 비어 있습니다. 참여자가 없으면 점유율을 정의할 수 없습니다."
            )
        if self.observed_answer_count < 0 or self.decided_prompt_count < 0:
            raise ValueError("관측 수치에 음수가 들어올 수 없습니다.")

        keys = [participant.key for participant in self.participants]
        if len(set(keys)) != len(keys):
            raise ValueError("비교 집합에 같은 키가 두 번 들어 있습니다.")

        for participant in self.participants:
            if participant.cited_answer_count > self.observed_answer_count:
                raise ValueError(
                    f"{participant.key}: 인용된 응답 수가 전체 응답 수보다 많습니다."
                )
            if participant.mentioned_answer_count > self.observed_answer_count:
                raise ValueError(
                    f"{participant.key}: 언급된 응답 수가 전체 응답 수보다 많습니다."
                )

        won = sum(participant.won_prompt_count for participant in self.participants)
        if won > self.decided_prompt_count:
            raise ValueError(
                "승리한 프롬프트 수의 합이 판정된 프롬프트 수보다 많습니다. "
                "한 프롬프트의 승자는 한 곳뿐입니다."
            )


@dataclass(frozen=True, slots=True)
class SovValue:
    """A share, or an explicit statement that there is nothing to divide by."""

    numerator: int
    denominator: int
    share: float | None
    display_ko: str
    unavailable_reason_ko: str | None

    @classmethod
    def of(cls, numerator: int, denominator: int, *, empty_reason_ko: str) -> SovValue:
        if denominator <= 0:
            return cls(
                numerator=numerator,
                denominator=denominator,
                share=None,
                display_ko=NO_DATA_KO,
                unavailable_reason_ko=empty_reason_ko,
            )
        share = numerator / denominator
        return cls(
            numerator=numerator,
            denominator=denominator,
            share=share,
            display_ko=f"{share * 100:.1f}%",
            unavailable_reason_ko=None,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "share": self.share,
            "display_ko": self.display_ko,
            "unavailable_reason_ko": self.unavailable_reason_ko,
        }


@dataclass(frozen=True, slots=True)
class ParticipantShare:
    """One brand's three observed visibility figures."""

    key: str
    label_ko: str
    is_own_brand: bool
    citation_sov: SovValue
    mention_sov: SovValue
    winning_prompt_rate: SovValue

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label_ko": self.label_ko,
            "is_own_brand": self.is_own_brand,
            "citation_sov": self.citation_sov.as_dict(),
            "mention_sov": self.mention_sov.as_dict(),
            "winning_prompt_rate": self.winning_prompt_rate.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class SovSetMember:
    key: str
    label_ko: str

    def as_dict(self) -> dict[str, str]:
        return {"key": self.key, "label_ko": self.label_ko}


@dataclass(frozen=True, slots=True)
class ShareOfVoiceReport:
    """Observed visibility for one set, one prompt set and one group of engines."""

    prompt_set_label: str
    engine_labels: tuple[str, ...]
    observed_answer_count: int
    decided_prompt_count: int
    comparison_set: tuple[SovSetMember, ...]
    comparison_set_note_ko: str
    scope_ko: str
    participants: tuple[ParticipantShare, ...]
    summary_ko: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_set_label": self.prompt_set_label,
            "engine_labels": list(self.engine_labels),
            "observed_answer_count": self.observed_answer_count,
            "decided_prompt_count": self.decided_prompt_count,
            "comparison_set": [member.as_dict() for member in self.comparison_set],
            "comparison_set_note_ko": self.comparison_set_note_ko,
            "scope_ko": self.scope_ko,
            "participants": [participant.as_dict() for participant in self.participants],
            "summary_ko": self.summary_ko,
        }


def share_of_voice(observation: ObservedVisibility) -> ShareOfVoiceReport:
    """Citation SOV, mention SOV and winning-prompt rate for one observation window.

    The two SOV denominators are the *set totals* — how the visibility that existed was
    divided up. The winning-prompt denominator is the number of prompts where a winner
    could be determined, which makes it a rate rather than a share: it does not move when
    the set shrinks, and the parts do not have to add up to one.
    """
    citation_total = sum(p.cited_answer_count for p in observation.participants)
    mention_total = sum(p.mentioned_answer_count for p in observation.participants)

    participants = tuple(
        ParticipantShare(
            key=participant.key,
            label_ko=participant.label_ko,
            is_own_brand=participant.is_own_brand,
            citation_sov=SovValue.of(
                participant.cited_answer_count,
                citation_total,
                empty_reason_ko=_NO_CITATION_KO,
            ),
            mention_sov=SovValue.of(
                participant.mentioned_answer_count,
                mention_total,
                empty_reason_ko=_NO_MENTION_KO,
            ),
            winning_prompt_rate=SovValue.of(
                participant.won_prompt_count,
                observation.decided_prompt_count,
                empty_reason_ko=_NO_DECIDED_PROMPT_KO,
            ),
        )
        for participant in observation.participants
    )

    return ShareOfVoiceReport(
        prompt_set_label=observation.prompt_set_label,
        engine_labels=observation.engine_labels,
        observed_answer_count=observation.observed_answer_count,
        decided_prompt_count=observation.decided_prompt_count,
        comparison_set=tuple(
            SovSetMember(key=p.key, label_ko=p.label_ko) for p in observation.participants
        ),
        comparison_set_note_ko=_set_note_ko(observation.participants),
        scope_ko=SCOPE_KO,
        participants=participants,
        summary_ko=_summary_ko(observation, participants),
    )


def _set_note_ko(participants: Sequence[ParticipantVisibility]) -> str:
    names = ", ".join(participant.label_ko for participant in participants)
    return f"{SET_NOTE_KO} 현재 집합 {len(participants)}곳: {names}."


def _summary_ko(
    observation: ObservedVisibility, participants: Sequence[ParticipantShare]
) -> str:
    engines = ", ".join(observation.engine_labels) or "지정된 엔진 없음"
    sentences = [
        f"프롬프트 세트 '{observation.prompt_set_label}'에서 {engines} 응답 "
        f"{observation.observed_answer_count}건을 관측했습니다.",
    ]

    own = next((p for p in participants if p.is_own_brand), None)
    if own is None:
        sentences.append("비교 집합에 자사 브랜드가 없어 자사 점유율은 계산하지 않았습니다.")
    elif own.citation_sov.share is None:
        sentences.append(
            f"자사 인용 점유율은 {NO_DATA_KO}입니다. {own.citation_sov.unavailable_reason_ko}"
        )
    else:
        sentences.append(
            f"자사 인용 점유율 {own.citation_sov.display_ko}, "
            f"언급 점유율 {own.mention_sov.display_ko}, "
            f"프롬프트 승률 {own.winning_prompt_rate.display_ko}입니다."
        )

    sentences.append(SET_NOTE_KO)
    return " ".join(sentences)


__all__ = [
    "NO_DATA_KO",
    "SCOPE_KO",
    "SET_NOTE_KO",
    "ObservedVisibility",
    "ParticipantShare",
    "ParticipantVisibility",
    "ShareOfVoiceReport",
    "SovSetMember",
    "SovValue",
    "share_of_voice",
]
