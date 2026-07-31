"""절대 평가 — 못 잰 것은 0점이고, 분모에서 빼지 않는다.

지금까지는 상대 평가였다. 측정하지 못한 항목은 예산에서 빠지고, 통째로 측정 불가인
영역은 가중치에서 빠졌다. 그래서 8개 영역 중 3개(20점어치)를 하나도 재지 못한 사이트가
"남은 80점어치 안에서 91.8점" 을 받았고, 화면에는 그냥 **91.8점 양호**로 떴다.

성능·사용자 경험이 가장 나빴다. 5개 항목 중 4개를 못 쟀는데 남은 하나로 **100점**이었다.
PageSpeed 연동이 없어서였다. 화면에는 "성능 100점" 이라고만 적혔다.

절대 평가에서는 100점이 고정된 만점이다. 재지 못한 항목은 점수를 얻지 못하고, 그 배점은
분모에 그대로 남는다. 못 잰 이유가 우리 쪽이든 대상 쪽이든 **얻지 못한 점수는 얻지 못한
것**이다.

해당 없음(N/A)은 다르다. 그것은 "이 대상에는 적용되지 않는 항목" 이라는 뜻이지 "없다" 가
아니다. 브로슈어 사이트에 페이지네이션 검사를 0점으로 매기면 없는 결함을 만들어 내는
것이므로, N/A 는 그대로 분모에서 빠진다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")


@pytest.fixture
def spec():  # type: ignore[no-untyped-def]
    import veo.api.app  # noqa: F401
    from veo.scoring.spec import latest_published

    return latest_published("veo.seo.readiness")


def _SCORING_CATEGORIES() -> set[str]:
    """점수를 이루는 영역들. 연동이 있어야 잴 수 있는 영역은 분모 밖이다."""
    import veo.api.app  # noqa: F401
    from veo.scoring.spec import latest_published

    spec = latest_published("veo.seo.readiness")
    # 관문은 더해지지 않고 곱해지므로 가중 평균의 분모에 들어가지 않는다.
    return {c.id for c in spec.scoring_categories}


def _scan(fixture: str):  # type: ignore[no-untyped-def]
    from tests.seo.support import build_context

    import veo.api.app  # noqa: F401
    from veo.seo.service import run_seo_scan

    return run_seo_scan(build_context(fixture)).score


class TestUnknownEarnsNothing:
    def test_an_unknown_check_keeps_its_severity_in_the_category_budget(self) -> None:
        """0점 처리하고 분모에 남긴다 — 그 '남긴다' 가 실제로 일어나는 자리.

        예산에서 빼면 남은 항목들의 몫이 그만큼 부풀고, 못 잰 것이 점수에 아무 영향을
        주지 않게 된다. 그것이 상대 평가다.
        """
        score = _scan("healthy")

        rows = [r for r in score.trace["checks"] if r["status"] == "UNKNOWN"]
        assert rows, "이 픽스처는 우리 힘으로 재지 못한 항목을 포함해야 한다"
        for row in rows:
            assert row["counted_in_budget"] is True
            assert row["penalty"] == pytest.approx(row["severity_coefficient"])

    def test_the_denominator_is_always_the_declared_total(self) -> None:
        """분모가 줄면 남은 항목의 몫이 부풀려진다. 그것이 상대 평가다."""
        score = _scan("healthy")

        applicable_weight = sum(
            c.weight
            for c in score.categories
            if c.status != "NOT_APPLICABLE" and c.category_id in _SCORING_CATEGORIES()
        )
        assert score.effective_weight_total == pytest.approx(applicable_weight)

    def test_a_half_measured_category_cannot_score_full_marks(self) -> None:
        """4개 중 1개만 보고 100점을 주면 '성능 100점' 같은 거짓말이 만들어진다."""
        score = _scan("healthy")

        for category in score.categories:
            if category.unknown_check_ids and category.scored_check_ids:
                assert category.score is not None
                assert category.score < 100.0


class TestNotApplicableStillLeavesTheDenominator:
    def test_a_check_that_does_not_apply_is_not_a_zero(self) -> None:
        """브로슈어 사이트에 없는 페이지네이션을 결함으로 만들지 않는다."""
        score = _scan("brochure_na")

        scoring = _SCORING_CATEGORIES()
        excluded = sum(
            c.weight
            for c in score.categories
            if c.status == "NOT_APPLICABLE" and c.category_id in scoring
        )
        assert score.effective_weight_total == pytest.approx(100.0 - excluded)

    def test_a_site_with_nothing_to_fault_can_still_reach_one_hundred(self) -> None:
        """적용되는 항목을 모두 통과했다면 100점이어야 한다 — 절대 평가라도."""
        from tests.seo.support import build_context, healthy_provider_payloads

        import veo.api.app  # noqa: F401
        from veo.contracts.enums import ProviderState
        from veo.seo.service import run_seo_scan

        context = build_context(
            "healthy",
            provider_states=dict.fromkeys(
                (
                    "GOOGLE_PAGESPEED",
                    "GOOGLE_SEARCH_CONSOLE",
                    "NAVER_SEARCH_ADVISOR",
                    "INDEXNOW",
                    "BACKLINK_INDEX",
                    "BRAND_MENTIONS",
                    "GOOGLE_CRUX",
                ),
                ProviderState.ENABLED,
            ),
            provider_payloads=healthy_provider_payloads(
                tuple(build_context("healthy").documents)
            ),
        )

        assert run_seo_scan(context).score.overall_score == pytest.approx(100.0)


class TestTheNumbersAreExplained:
    def test_the_trace_says_an_unknown_check_was_counted(self) -> None:
        """반년 뒤 '왜 이 점수였나' 에 답하려면 계산 과정에 남아 있어야 한다."""
        score = _scan("healthy")

        rows = [r for r in score.trace.get("checks", []) if r.get("status") == "UNKNOWN"]
        assert rows, "이 픽스처는 측정 불가 항목을 포함해야 한다"
        assert all(row.get("counted_in_budget") for row in rows)
