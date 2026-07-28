"""A prompt set is where a competitive comparison gets rigged.

Nobody has to falsify a number. You just choose the questions. Ask "서초 임플란트 잘하는
곳" where the client ranks well, skip "임플란트 부작용" where they do not, and the report
shows a brand dominating AI answers. Every figure downstream is arithmetically correct
and the conclusion is false.

So the prompt set is a versioned, frozen artefact with an audit trail: the same questions
go to every brand in a comparison, exclusions carry a recorded reason, and the balance of
the set across intent and funnel is measurable rather than asserted.
"""

from __future__ import annotations

import pytest

from veo.observations.prompts import (
    Funnel,
    Intent,
    Prompt,
    PromptSet,
    PromptSetImbalanceError,
    Subject,
)


def prompt(
    text: str = "임플란트 비용",
    *,
    intent: Intent = Intent.PRICE,
    funnel: Funnel = Funnel.RESEARCH,
    subject: Subject = Subject.NON_BRAND,
    importance: float = 0.5,
    locale: str = "ko-KR",
) -> Prompt:
    return Prompt(
        text=text,
        intent=intent,
        funnel=funnel,
        subject=subject,
        business_importance=importance,
        locale=locale,
    )


def balanced_prompts() -> list[Prompt]:
    """One prompt per intent, spread across funnel stages and subjects."""
    intents = list(Intent)
    funnels = list(Funnel)
    subjects = list(Subject)
    return [
        prompt(
            f"질문 {index}",
            intent=intent,
            funnel=funnels[index % len(funnels)],
            subject=subjects[index % len(subjects)],
        )
        for index, intent in enumerate(intents)
    ]


# --------------------------------------------------------------------------- #
# A prompt carries its own classification
# --------------------------------------------------------------------------- #


def test_a_prompt_records_intent_funnel_and_subject() -> None:
    item = prompt("임플란트 부작용", intent=Intent.TRUST, funnel=Funnel.RESEARCH)
    assert item.intent is Intent.TRUST
    assert item.funnel is Funnel.RESEARCH
    assert item.prompt_id, "a prompt needs a stable id so repeat runs are comparable"


def test_the_same_text_and_classification_always_gets_the_same_id() -> None:
    assert prompt("임플란트 비용").prompt_id == prompt("임플란트 비용").prompt_id


def test_changing_the_text_changes_the_id() -> None:
    assert prompt("임플란트 비용").prompt_id != prompt("임플란트 가격").prompt_id


def test_business_importance_is_bounded() -> None:
    with pytest.raises(ValueError):
        prompt(importance=1.5)


def test_estimated_demand_is_never_confused_with_measured_volume() -> None:
    """An analyst's guess and a Naver figure must not share a field."""
    item = prompt()
    assert hasattr(item, "business_importance")
    assert not hasattr(item, "monthly_searches"), (
        "search volume belongs to the keyword engine, with its own source and quality flags"
    )


# --------------------------------------------------------------------------- #
# Balance — the anti-cherry-picking property
# --------------------------------------------------------------------------- #


def test_a_balanced_set_is_accepted() -> None:
    PromptSet.build(name="치과 기본", prompts=balanced_prompts())


def test_a_set_of_only_flattering_intents_is_refused() -> None:
    """All 'best/recommended' questions is the classic rigged set."""
    flattering = [prompt(f"질문 {i}", intent=Intent.BEST_OR_RECOMMENDED) for i in range(6)]
    with pytest.raises(PromptSetImbalanceError, match="의도"):
        PromptSet.build(name="편향", prompts=flattering)


def test_a_set_that_omits_trust_questions_is_refused() -> None:
    """Skipping 부작용/후기 questions is how a brand avoids its weak ground."""
    without_trust = [p for p in balanced_prompts() if p.intent is not Intent.TRUST]
    with pytest.raises(PromptSetImbalanceError, match="신뢰"):
        PromptSet.build(name="신뢰 회피", prompts=without_trust)


def test_a_set_of_only_brand_questions_is_refused() -> None:
    """Asking only '베놈치과 어때' guarantees a mention and measures nothing."""
    brand_only = [
        prompt(f"질문 {i}", intent=intent, subject=Subject.BRAND) for i, intent in enumerate(Intent)
    ]
    with pytest.raises(PromptSetImbalanceError, match="브랜드"):
        PromptSet.build(name="브랜드만", prompts=brand_only)


def test_a_tiny_set_is_refused() -> None:
    with pytest.raises(PromptSetImbalanceError):
        PromptSet.build(name="너무 작음", prompts=[prompt("하나")])


def test_the_balance_report_names_what_is_missing() -> None:
    without_trust = [p for p in balanced_prompts() if p.intent is not Intent.TRUST]
    report = PromptSet.describe_balance(without_trust)
    assert any("신뢰" in line for line in report)


# --------------------------------------------------------------------------- #
# Freezing — the same questions reach every brand
# --------------------------------------------------------------------------- #


def test_a_published_set_is_frozen_and_checksummed() -> None:
    prompt_set = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    assert len(prompt_set.checksum) == 64

    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        prompt_set.name = "다른 이름"  # type: ignore[misc]


def test_reordering_the_prompts_does_not_change_the_checksum() -> None:
    prompts = balanced_prompts()
    first = PromptSet.build(name="치과 기본", prompts=prompts)
    second = PromptSet.build(name="치과 기본", prompts=list(reversed(prompts)))
    assert first.checksum == second.checksum


def test_changing_one_prompt_changes_the_checksum() -> None:
    prompts = balanced_prompts()
    original = PromptSet.build(name="치과 기본", prompts=prompts)
    edited = PromptSet.build(
        name="치과 기본",
        prompts=[*prompts[:-1], prompt("완전히 다른 질문", intent=prompts[-1].intent)],
    )
    assert original.checksum != edited.checksum


# --------------------------------------------------------------------------- #
# Exclusions carry a reason
# --------------------------------------------------------------------------- #


def test_excluding_a_prompt_requires_a_recorded_reason() -> None:
    prompt_set = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    target = prompt_set.prompts[0]

    with pytest.raises(ValueError, match="사유"):
        prompt_set.excluding(target.prompt_id, reason_ko="")


def test_an_exclusion_is_recorded_and_visible() -> None:
    prompt_set = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    target = prompt_set.prompts[0]

    narrowed = prompt_set.excluding(target.prompt_id, reason_ko="이 지역에서 제공하지 않는 시술")

    assert target.prompt_id not in {p.prompt_id for p in narrowed.prompts}
    assert len(narrowed.exclusions) == 1
    assert narrowed.exclusions[0].reason_ko
    assert narrowed.checksum != prompt_set.checksum, (
        "a narrowed set is a different set and must not pass for the original"
    )


def test_exclusions_survive_into_the_serialised_form() -> None:
    import json

    prompt_set = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    narrowed = prompt_set.excluding(prompt_set.prompts[0].prompt_id, reason_ko="비해당 시술")
    payload = json.loads(json.dumps(narrowed.as_dict(), ensure_ascii=False))

    assert payload["exclusions"], "a report must be able to show what was left out and why"
    assert payload["checksum"]


def test_excluding_below_the_minimum_is_refused() -> None:
    """Narrowing is legitimate; narrowing until only friendly questions remain is not."""
    prompt_set = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    with pytest.raises(PromptSetImbalanceError):
        for item in prompt_set.prompts[:-1]:
            prompt_set = prompt_set.excluding(item.prompt_id, reason_ko="범위 밖")


# --------------------------------------------------------------------------- #
# Fair comparison
# --------------------------------------------------------------------------- #


def test_two_brands_must_be_measured_with_the_same_set() -> None:
    ours = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    theirs = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    assert ours.is_same_set_as(theirs)


def test_a_narrowed_set_is_not_the_same_set() -> None:
    ours = PromptSet.build(name="치과 기본", prompts=balanced_prompts())
    theirs = ours.excluding(ours.prompts[0].prompt_id, reason_ko="사유 있음")
    assert not ours.is_same_set_as(theirs)
