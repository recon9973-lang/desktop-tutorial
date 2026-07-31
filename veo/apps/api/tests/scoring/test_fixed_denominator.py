"""검사를 더해도 분모가 자라지 않는다 — v1 이 무너진 자리.

명세 1.2.0 과 1.6.0 사이에 온페이지 검사가 9개에서 11개로 늘었다. 같은 사이트,
같은 결함(title 전면 실패)인데 점수는 **66.7 에서 72.7 로 올랐다.** 검사를 추가한
사람은 배점을 정확히 매겼고 아무도 거짓말을 하지 않았다. 분모가 조용히 늘어났을
뿐이다.

원인은 `budget += coefficient` 다. 분모가 "채점된 검사들의 심각도 계수 합" 이라
검사를 더할 때마다 커지고, 그만큼 기존 실패가 싸진다.

고친 방법은 영역별 고정 분모(`raw_budget`)와 검사별 배점(`points`)이다. 이제 검사를
추가하려면 형제에서 덜어내야 하고, **무엇을 덜어낼지가 근거를 대야 하는 판단으로
드러난다.** 나눗셈이 조용히 대신 결정하지 않는다.

해당 없음(N/A) 재분배는 그대로 남는다. "이 사이트에 그 항목이 없다"(ADR 0002)와
"명세에 검사가 하나 늘었다" 는 전혀 다른 일이다.
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
from veo.scoring.errors import ScoringSpecError


def outcome(check_id: str, status: CheckStatus, *, coverage_ratio: float = 1.0):  # type: ignore[no-untyped-def]
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence=1.0,
        affected_weight=coverage_ratio,
        evaluated_weight=1.0,
        evidence_ids=[f"ev::{check_id}"],
    )


def uncapped(tiny_spec_dict):  # type: ignore[no-untyped-def]
    """상한을 뺀 사본.

    `tiny_spec_dict` 는 test.a.blocker 가 전면 실패하면 25점으로 클램프하는 상한을
    갖고 있다. 그 상한은 그것대로 옳지만, **배점이 얼마나 아픈가를 재려는 시험을
    통째로 가린다** — 6점짜리와 3점짜리가 둘 다 25점으로 눌리면 비율을 볼 수 없다.
    상한이 없는 사본에서 배점을 재고, 상한 자체는 test_evaluator.py 가 따로 본다.
    """
    spec = copy.deepcopy(tiny_spec_dict)
    spec["caps"] = []
    return spec


def with_points(tiny_spec_dict, points: dict[str, float], budget: float):  # type: ignore[no-untyped-def]
    """cat_a 에 고정 분모와 검사별 배점을 준 사본."""
    spec = uncapped(tiny_spec_dict)
    spec["spec_id"] = "veo.test.points"
    category = spec["categories"][0]
    category["raw_budget"] = budget
    for check in category["checks"]:
        check["points"] = points[check["id"]]
    return spec


BASE_POINTS = {"test.a.blocker": 6.0, "test.a.major": 3.0, "test.a.info": 1.0}


def score(spec_dict, **overrides: object) -> float | None:  # type: ignore[no-untyped-def]
    spec = build_spec(spec_dict)
    built = []
    for check_id in spec.check_ids:
        value = overrides.get(check_id, CheckStatus.PASS)
        status, ratio = value if isinstance(value, tuple) else (value, 1.0)
        built.append(outcome(check_id, status, coverage_ratio=ratio))  # type: ignore[arg-type]
    return evaluate(spec, built).overall_score


# --------------------------------------------------------------------------- #
# 자물쇠 — 배점 합이 고정 분모와 맞지 않으면 명세를 만들 수 없다
# --------------------------------------------------------------------------- #


class TestTheAllocationMustBalance:
    def test_a_balanced_allocation_builds(self, tiny_spec_dict) -> None:  # type: ignore[no-untyped-def]
        assert build_spec(with_points(tiny_spec_dict, BASE_POINTS, 10.0)) is not None

    def test_adding_a_check_without_rebalancing_is_rejected(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """**이 시험이 v1 의 결함을 막는 자물쇠다.**

        검사를 하나 더하면서 형제 배점을 그대로 두면, 그 순간 분모가 늘어난다.
        여기서 막히지 않으면 아무도 눈치채지 못하고 넘어간다 — v1 때 실제로 그랬다.
        """
        spec = with_points(tiny_spec_dict, BASE_POINTS, 10.0)
        added = dict(spec["categories"][0]["checks"][0])
        added["id"] = "test.a.extra"
        added["points"] = 2.0
        spec["categories"][0]["checks"].append(added)

        with pytest.raises(ScoringSpecError, match="배점 합"):
            build_spec(spec)

    def test_points_without_a_declared_budget_are_rejected(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """배점만 적고 고정 분모를 빼면 자물쇠가 없는 것과 같다."""
        spec = copy.deepcopy(tiny_spec_dict)
        spec["categories"][0]["checks"][0]["points"] = 5.0

        with pytest.raises(ScoringSpecError, match="raw_budget"):
            build_spec(spec)

    def test_a_declared_budget_with_a_check_missing_points_is_rejected(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        spec = with_points(tiny_spec_dict, BASE_POINTS, 10.0)
        del spec["categories"][0]["checks"][1]["points"]

        with pytest.raises(ScoringSpecError, match="배점이 없는"):
            build_spec(spec)


# --------------------------------------------------------------------------- #
# 배점이 실제로 쓰인다
# --------------------------------------------------------------------------- #


class TestPointsDecideTheCost:
    def test_a_higher_scoring_check_costs_more(self, tiny_spec_dict) -> None:  # type: ignore[no-untyped-def]
        """심각도 다섯 칸으로는 못 하던 구분이다.

        blocker 와 major 는 심각도 계수로도 1.0 대 0.3 이지만, 배점은 그 비율을
        검사마다 자유롭게 정할 수 있다.
        """
        spec = with_points(tiny_spec_dict, BASE_POINTS, 10.0)
        expensive = score(spec, **{"test.a.blocker": CheckStatus.FAIL})
        cheap = score(spec, **{"test.a.major": CheckStatus.FAIL})
        assert expensive is not None and cheap is not None
        assert expensive < cheap < 100.0

    def test_the_ratio_of_the_two_costs_follows_the_declared_points(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """6점 검사는 3점 검사의 정확히 두 배로 아파야 한다."""
        spec = with_points(tiny_spec_dict, BASE_POINTS, 10.0)
        lost_six = 100.0 - (score(spec, **{"test.a.blocker": CheckStatus.FAIL}) or 0.0)
        lost_three = 100.0 - (score(spec, **{"test.a.major": CheckStatus.FAIL}) or 0.0)
        assert lost_six == pytest.approx(lost_three * 2, abs=0.01)


class TestTheDenominatorDoesNotGrow:
    def test_a_rebalanced_addition_leaves_the_existing_failure_alone(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """v1 의 결함을 정면으로 겨눈 시험.

        검사를 하나 더하면서 형제에서 그만큼 덜어내면, 기존 실패의 값은 그 검사가
        가져간 몫만큼만 움직인다. 분모 자체는 자라지 않는다.
        """
        before = with_points(tiny_spec_dict, BASE_POINTS, 10.0)

        after = with_points(
            tiny_spec_dict,
            {"test.a.blocker": 6.0, "test.a.major": 2.0, "test.a.info": 1.0},
            10.0,
        )
        added = dict(after["categories"][0]["checks"][0])
        added["id"] = "test.a.extra"
        added["points"] = 1.0
        after["categories"][0]["checks"].append(added)

        failing = {"test.a.blocker": CheckStatus.FAIL}
        assert score(before, **failing) == pytest.approx(score(after, **failing), abs=1e-9)


class TestNotApplicableStillRedistributes:
    """해당 없음은 여전히 형제에게 나뉜다(ADR 0002).

    "이 사이트에 그 항목이 없다" 와 "명세에 검사가 하나 늘었다" 는 다른 일이다.
    앞은 사이트의 사실이고 뒤는 방법론의 변경이다.
    """

    def test_a_site_with_an_inapplicable_check_can_still_reach_100(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        spec = with_points(tiny_spec_dict, BASE_POINTS, 10.0)
        assert score(spec, **{"test.a.info": CheckStatus.NOT_APPLICABLE}) == 100.0

    def test_the_remaining_checks_carry_the_full_budget(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """1점짜리가 빠지면 남은 9점이 10점 몫을 나눠 갖는다."""
        spec = with_points(tiny_spec_dict, BASE_POINTS, 10.0)
        full = 100.0 - (score(spec, **{"test.a.blocker": CheckStatus.FAIL}) or 0.0)
        reduced = 100.0 - (
            score(
                spec,
                **{
                    "test.a.blocker": CheckStatus.FAIL,
                    "test.a.info": CheckStatus.NOT_APPLICABLE,
                },
            )
            or 0.0
        )
        assert reduced > full


# --------------------------------------------------------------------------- #
# 범위 지수
# --------------------------------------------------------------------------- #


class TestBreadthExponent:
    """결함은 대개 템플릿 단위로 생긴다.

    100장 중 40장의 title 이 깨졌다면 40개의 개별 실수가 아니라 템플릿 하나의
    문제이고, 나머지 60장도 같은 위험 위에 있다. 40% 실패를 40% 감점으로 세면
    "절반 이상 멀쩡하다" 는 그림이 되는데, 고쳐야 할 것은 페이지가 아니라 템플릿이다.
    """

    def test_the_default_is_linear_and_changes_nothing(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        spec = copy.deepcopy(tiny_spec_dict)
        assert build_spec(spec).status_policy.breadth_exponent == 1.0

    def test_a_sublinear_exponent_makes_a_widespread_defect_cost_more(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        linear = uncapped(tiny_spec_dict)
        curved = uncapped(tiny_spec_dict)
        curved["spec_id"] = "veo.test.curved"
        curved["status_policy"]["breadth_exponent"] = 0.7

        partial = {"test.a.blocker": (CheckStatus.FAIL, 0.4)}
        assert (score(curved, **partial) or 0.0) < (score(linear, **partial) or 0.0)

    def test_a_total_failure_costs_the_same_under_any_exponent(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """1의 어떤 거듭제곱도 1이다. 전면 실패는 지수와 무관해야 한다."""
        linear = uncapped(tiny_spec_dict)
        curved = uncapped(tiny_spec_dict)
        curved["spec_id"] = "veo.test.curved"
        curved["status_policy"]["breadth_exponent"] = 0.7

        total = {"test.a.blocker": CheckStatus.FAIL}
        assert score(curved, **total) == pytest.approx(score(linear, **total), abs=1e-9)

    def test_a_clean_site_is_unaffected_by_the_exponent(
        self, tiny_spec_dict
    ) -> None:  # type: ignore[no-untyped-def]
        """0의 어떤 거듭제곱도 0이다. 만점은 지수와 무관해야 한다."""
        curved = uncapped(tiny_spec_dict)
        curved["spec_id"] = "veo.test.curved"
        curved["status_policy"]["breadth_exponent"] = 0.7
        assert score(curved) == 100.0


class TestPublishedSpecsAreUntouched:
    """발행본은 불변이다(ADR 0012)."""

    def test_no_published_spec_declares_points_or_a_budget(self) -> None:
        spec = latest_published("veo.seo.readiness")
        assert all(category.raw_budget is None for category in spec.categories)
        assert all(
            check.points is None for category in spec.categories for check in category.checks
        )

    def test_the_published_spec_scores_linearly(self) -> None:
        assert latest_published("veo.seo.readiness").status_policy.breadth_exponent == 1.0
