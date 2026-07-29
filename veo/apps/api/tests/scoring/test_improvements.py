"""무엇을 먼저 고쳐야 점수가 가장 많이 오르는가.

화면에 "이걸 고치면 +12점" 이라고 쓰려면 그 숫자가 실제 채점 산식에서 나와야 한다.
화면이 따로 어림하면 고친 뒤 실제 점수와 어긋나고, 그러면 우리가 준 우선순위 자체를
고객이 믿지 않게 된다. 기획서 §12.3 이 "한 원시 결과에서 보기만 다르게 만들며 별도
계산을 중복하지 않는다" 고 못박는 이유가 이것이다.

산식은 이렇다::

    penalty        = 심각도계수 x 상태배수 x 수집비율 x 신뢰도
    카테고리 점수  = 100 x max(0, 1 - Σpenalty / budget)
    전체 점수      = Σ(카테고리 점수 x 가중치) / Σ가중치

따라서 어떤 항목을 통과로 바꾸면 그 항목의 penalty 가 사라지고, 그만큼 카테고리 점수가
오르고, 카테고리 가중치 비율만큼 전체 점수가 오른다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")


@pytest.fixture
def result():  # type: ignore[no-untyped-def]
    from tests.seo.support import build_context

    import veo.api.app  # noqa: F401
    from veo.seo.service import run_seo_scan

    return run_seo_scan(build_context("broken_jsonld"))


class TestRanking:
    def test_every_entry_names_a_failing_or_warning_check(self, result) -> None:
        """통과한 항목은 고칠 것이 없고, 측정 불가는 **우리가** 못 잰 것이다."""
        from veo.scoring.improvements import rank_improvements

        statuses = {o.check_id: str(o.status) for o in result.score.outcomes}
        entries = rank_improvements(result.score)

        assert entries
        assert all(statuses[e.check_id] in {"FAIL", "WARNING"} for e in entries)

    def test_entries_are_ordered_by_how_much_they_gain(self, result) -> None:
        from veo.scoring.improvements import rank_improvements

        gains = [e.gain_points for e in rank_improvements(result.score)]

        assert gains == sorted(gains, reverse=True)

    def test_every_gain_is_positive(self, result) -> None:
        """0점짜리 항목을 '개선 할 일' 로 올리면 목록만 길어지고 우선순위가 흐려진다."""
        from veo.scoring.improvements import rank_improvements

        assert all(e.gain_points > 0 for e in rank_improvements(result.score))


class TestArithmetic:
    def test_the_sum_of_gains_never_exceeds_the_points_actually_lost(self, result) -> None:
        """전부 고쳐도 100점을 넘길 수는 없다."""
        from veo.scoring.improvements import rank_improvements

        score = result.score.overall_score
        assert score is not None
        total_gain = sum(e.gain_points for e in rank_improvements(result.score))

        assert total_gain <= 100.0 - score + 0.01

    def test_a_capped_score_reports_the_cap_rather_than_a_gain_it_cannot_deliver(self) -> None:
        """상한이 걸려 있으면 항목 하나를 고쳐도 점수가 오르지 않는다.

        상한은 "이것을 풀기 전에는 몇 점 이상 줄 수 없다" 는 규칙이다. 그 상태에서
        "+12점" 이라고 쓰면 고쳐도 점수가 그대로여서 거짓말이 된다.
        """
        from tests.seo.support import build_context

        import veo.api.app  # noqa: F401
        from veo.scoring.improvements import rank_improvements
        from veo.seo.service import run_seo_scan

        capped = run_seo_scan(build_context("sitewide_noindex"))
        assert capped.score.applied_caps, "이 픽스처는 상한이 걸려야 한다"

        entries = rank_improvements(capped.score)

        assert all(e.blocked_by_cap for e in entries)
        assert all(e.gain_points == 0.0 for e in entries)
