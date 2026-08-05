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


class TestTheNumberIsTheRealGain:
    """표기한 이득이 **실제로 고쳤을 때 오르는 폭**과 같은가.

    2026-08-05 시연으로 두 가지가 드러났다. 둘 다 산식을 이 파일 밖에서 한 벌 더 세운
    탓이다(0-D).

    * **분모가 채점기와 달랐다.** 여기서는 채점 가능한 영역 가중치 합(실측 130.0)을
      썼고 채점기는 `effective_weight_total`(100.0)을 썼다 — 표기가 실제보다 항상
      23% 낮았다(0.769 = 100/130). 표본·항목을 가리지 않고 같은 비율이었다.
    * **상한이 걸리면 전부 0 으로 적었다.** 그런데 상한을 **유발한 그 항목**을 고치면
      상한이 풀려 크게 오른다: `render_gap` 의 `js_render_parity` 는 표기 0.0, 실제
      **+32.91** 이었다. 가장 효과 큰 항목이 "고쳐도 소용없다" 로 표시되고 있었다.

    이제 어림하지 않고 다시 채점한다. 아래 시험은 그 성질을 **모든 표본에서** 지킨다 —
    표본 하나로는 비율 오차가 눈에 띄지 않았다.
    """

    FIXTURES = (
        "brochure_na", "broken_jsonld", "conflicting_hreflang", "cross_domain_canonical",
        "duplicate_metadata", "healthy", "orphan_page", "redirect_loop",
        "render_gap", "sitewide_noindex",
    )

    @pytest.mark.parametrize("fixture", FIXTURES)
    def test_the_reported_gain_is_what_actually_happens(self, fixture: str) -> None:
        from tests.seo.support import build_context

        import veo.api.app  # noqa: F401
        from veo.scoring.evaluator import evaluate
        from veo.scoring.improvements import rank_improvements
        from veo.scoring.models import CheckStatus
        from veo.scoring.spec import load_spec
        from veo.seo.service import run_seo_scan

        result = run_seo_scan(build_context(fixture)).score
        spec = load_spec(result.spec_id, result.spec_version)
        base = result.overall_score
        outcomes = list(result.outcomes)
        index_of = {outcome.check_id: i for i, outcome in enumerate(outcomes)}

        entries = rank_improvements(result)
        # **빈 목록으로 통과하지 않는다.** 이 시험을 처음 썼을 때, 옛 방식(상한이면 전부
        # 0)으로 되돌려도 통과했다 — 이득이 0 이면 목록에서 걸러져 반복문이 아예 돌지
        # 않았기 때문이다. 아무것도 검사하지 않고 초록불이 되는 시험은 결함을 지킨다(0-I).
        actionable = [o for o in outcomes if str(o.status) in {"FAIL", "WARNING"}]
        if actionable:
            assert entries, (
                f"{fixture}: 조치 대상이 {len(actionable)}건인데 개선 후보가 하나도 없다"
            )

        for entry in entries:
            position = index_of[entry.check_id]
            patched = list(outcomes)
            patched[position] = outcomes[position].model_copy(
                update={"status": CheckStatus.PASS}
            )
            actual = round(max(0.0, evaluate(spec, patched).overall_score - base), 2)

            assert entry.gain_points == pytest.approx(actual, abs=0.01), (
                f"{fixture}/{entry.check_id}: 표기 {entry.gain_points} vs 실제 {actual}"
            )
            if entry.blocked_by_cap:
                assert actual <= 0.01, (
                    f"{fixture}/{entry.check_id}: '상한 때문에 0점' 이라 했는데 "
                    f"실제로는 {actual}점 오른다"
                )
