"""관문 영역 — 앞이 막히면 뒤는 무의미하다.

가산 방식만 쓰던 판에서 실측한 값이 이 기능을 만들게 했다. **색인이 전면 차단된
사이트가 74점을 받았다.** 검색에 존재하지 않는 사이트가 "양호" 등급을 받은 것이다.
차단 검사들의 배점만큼만 잃기 때문이었다.

noindex 페이지의 완벽한 구조화 데이터는 아무 일도 하지 않는다. 그래서 차단은
배점이 아니라 곱셈이다.

이 파일은 두 가지를 함께 지킨다.

1. **관문이 선언된 명세에서는 곱한다.**
2. **선언하지 않은 명세는 하나도 바뀌지 않는다.** 발행본은 불변이고(ADR 0012),
   1.7.0 이하로 매긴 과거 점수는 앞으로도 그때의 규칙으로 설명되어야 한다.
"""

from __future__ import annotations

import copy

import pytest

from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    build_spec,
    evaluate,
    latest_published,
)


def outcome(check_id: str, status: CheckStatus, *, coverage_ratio: float = 1.0):
    """범위 비율은 affected/evaluated 로 표현된다."""
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence=1.0,
        affected_weight=coverage_ratio,
        evaluated_weight=1.0,
        evidence_ids=[f"ev::{check_id}"],
    )

def gated(tiny_spec_dict):  # type: ignore[no-untyped-def]
    """`tiny_spec_dict` 의 첫 영역을 관문으로 돌린 사본.

    시험용 명세를 손으로 다시 짜지 않는다. 스키마는 필수 항목이 많고, 손으로 짠 사본은
    스키마가 바뀔 때마다 조용히 낡는다. 여기서 확인하려는 것은 **관문 선언 하나가
    무엇을 바꾸는가**이므로, 이미 검증된 명세에 그 한 줄만 더한다.
    """
    spec = copy.deepcopy(tiny_spec_dict)
    spec["spec_id"] = "veo.test.gate"
    spec["categories"][0]["is_gate"] = True
    return build_spec(spec)


def ungated(tiny_spec_dict):  # type: ignore[no-untyped-def]
    return build_spec(copy.deepcopy(tiny_spec_dict))


#: 관문 영역(cat_a)의 검사들과 품질 영역(cat_b)의 검사들.
GATE_CHECKS = ("test.a.blocker", "test.a.major", "test.a.info")
QUALITY_CHECKS = ("test.b.critical", "test.b.minor")
ALL_CHECKS = (*GATE_CHECKS, *QUALITY_CHECKS)


def outcomes_for(overrides: dict[str, object]):  # type: ignore[no-untyped-def]
    """선언하지 않은 검사는 통과로 둔다."""
    built = []
    for check_id in ALL_CHECKS:
        value = overrides.get(check_id, CheckStatus.PASS)
        status, ratio = value if isinstance(value, tuple) else (value, 1.0)
        built.append(outcome(check_id, status, coverage_ratio=ratio))
    return built


def score(spec, **overrides: object) -> float | None:  # type: ignore[no-untyped-def]
    return evaluate(spec, outcomes_for(dict(overrides))).overall_score


class TestAGateMultiplies:
    def test_a_clean_site_is_unaffected_by_the_gate(self, tiny_spec_dict) -> None:  # type: ignore[no-untyped-def]
        assert score(gated(tiny_spec_dict)) == 100.0

    def test_a_fully_blocked_site_scores_zero_however_good_the_rest_is(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """이 시험이 이 기능의 존재 이유다.

        가산 방식에서는 같은 상황이 74점이었다. 관문 하나가 전면 실패했는데도 나머지
        영역의 점수가 살아남았기 때문이다.
        """
        blocked = {"test.a.blocker": CheckStatus.FAIL}
        assert score(gated(tiny_spec_dict), **blocked) == 0.0

        # 같은 결과를 관문 없이 매기면 점수가 남는다. 이 대비가 기능의 크기다.
        # 이 명세에서는 25.0 이고, 실제 SEO 명세에서는 74점이었다. 숫자를 못 박지
        # 않는 이유는 그것이 명세의 가중치에 달린 값이라서다 — 여기서 지킬 성질은
        # "관문 없이는 차단된 사이트에도 점수가 남는다" 이지 특정 값이 아니다.
        assert (score(ungated(tiny_spec_dict), **blocked) or 0.0) > 0.0

    def test_every_gate_must_be_passed_not_just_most_of_them(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """관문은 곱해진다. 하나가 절반, 다른 하나가 20% 면 (1-0.5)(1-0.2) = 0.4 다."""
        result = score(
            gated(tiny_spec_dict),
            **{
                "test.a.blocker": (CheckStatus.FAIL, 0.5),
                "test.a.major": (CheckStatus.FAIL, 0.2),
            },
        )
        assert result == pytest.approx(40.0, abs=0.01)

    def test_half_the_pages_blocked_costs_about_half_the_score(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        result = score(gated(tiny_spec_dict), **{"test.a.blocker": (CheckStatus.FAIL, 0.5)})
        assert result == pytest.approx(50.0, abs=0.01)

    def test_a_warning_on_a_gate_costs_less_than_a_failure(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        spec = gated(tiny_spec_dict)
        warned = score(spec, **{"test.a.blocker": CheckStatus.WARNING})
        failed = score(spec, **{"test.a.blocker": CheckStatus.FAIL})
        assert warned is not None and failed is not None
        assert 100.0 > warned > failed


class TestAnUnmeasuredGateDoesNotInventABlockage:
    """못 잰 차단은 없는 차단이다(0-A).

    구글 Lighthouse 는 이것을 반대로 한다 — 2026-08-01 실측에서 robots.txt fetch
    타임아웃이 0점 실패로 기록됐고, 화면에서 '크롤러를 막고 있음' 과 구분되지 않았다.
    같은 사이트가 잴 때마다 SEO 1.00 과 0.92 를 오갔다. 우리가 같은 짓을 하면 아무
    문제 없는 병원 홈페이지가 **우리 쪽 네트워크 사정으로** 0점을 받는다.
    """

    def test_an_unknown_gate_leaves_the_score_alone(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        assert score(gated(tiny_spec_dict), **{"test.a.blocker": CheckStatus.UNKNOWN}) == 100.0

    def test_the_unverified_gate_is_named_in_the_trace(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """조용히 넘어가면 '확인했고 문제없음' 과 구분되지 않는다."""
        result = evaluate(
            gated(tiny_spec_dict), outcomes_for({"test.a.blocker": CheckStatus.UNKNOWN})
        )
        assert result.trace["overall"]["gate_unverified"] == ["test.a.blocker"]
        assert result.trace["overall"]["reach"] == 1.0

    def test_a_not_applicable_gate_is_skipped(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        assert (
            score(gated(tiny_spec_dict), **{"test.a.blocker": CheckStatus.NOT_APPLICABLE})
            == 100.0
        )


class TestTheQualitySideIsUnchanged:
    """관문 선언은 관문 영역만 바꾼다. 나머지 영역의 계산은 그대로다."""

    def test_a_quality_failure_costs_the_same_with_or_without_a_gate(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        failing = {"test.b.critical": CheckStatus.FAIL}
        with_gate = score(gated(tiny_spec_dict), **failing)
        without = score(ungated(tiny_spec_dict), **failing)
        assert with_gate is not None and without is not None
        # 관문 없는 판은 두 영역을 가중 평균하고, 관문 판은 품질 영역만 남긴다.
        # 값이 같을 필요는 없지만 **둘 다 100점 미만**이어야 한다 — 품질 실패가
        # 관문 선언 때문에 사라지면 안 된다.
        assert with_gate < 100.0
        assert without < 100.0


class TestASpecWithoutGatesIsUnaffected:
    """관문을 선언하지 않은 명세는 계산이 한 글자도 달라지지 않는다(ADR 0012).

    이 시험은 처음에 "발행된 SEO 명세는 관문을 선언하지 않는다" 였다. 그날은 사실
    이었지만 **성질이 아니라 그 시점의 상태**를 못 박은 것이었고, 명세 1.8.0 이
    정당하게 관문을 선언하자 깨졌다. 잡아야 할 것을 잡은 게 아니라 정상적인 발행을
    막고 있었다. 상태를 못 박는 시험은 반드시 이렇게 된다.

    지켜야 할 성질은 "관문 **없는** 명세는 그대로 동작한다" 이고, 그것은 관문 없는
    명세로만 확인할 수 있다.
    """

    def test_reach_is_one_when_no_category_is_a_gate(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        spec = ungated(tiny_spec_dict)
        assert not any(category.is_gate for category in spec.categories)

        built = [outcome(check_id, CheckStatus.FAIL) for check_id in spec.check_ids]
        trace = evaluate(spec, built).trace["overall"]
        assert trace["reach"] == 1.0
        assert trace["gate_unverified"] == []


class TestThePublishedSpecUsesTheGate:
    """1.8.0 부터 발행된 SEO 명세가 관문을 쓴다.

    누가 실수로 지우면 색인이 전면 차단된 사이트가 다시 74점을 받게 된다.
    """

    def test_the_indexing_stage_is_declared_as_a_gate(self) -> None:
        published = latest_published("veo.seo.readiness")
        gates = [category for category in published.categories if category.is_gate]
        assert len(gates) == 1, "관문은 색인 차단 단계 하나여야 한다"
        assert gates[0].id == "s1_blocked"

    def test_the_gate_holds_the_checks_that_actually_block_indexing(self) -> None:
        published = latest_published("veo.seo.readiness")
        gate = next(c for c in published.categories if c.is_gate)
        ids = {check.id for check in gate.checks}
        assert "seo.robots.txt_allows_url" in ids
        assert "seo.robots.meta_indexable" in ids
        assert "seo.http.status_ok" in ids
