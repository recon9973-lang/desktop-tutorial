"""판정이 "어느 페이지였는지" 를 실어 나르는가 — 페이지별 점수의 첫 번째 전제.

무게(affected/evaluated_weight)는 사이트 점수를 정하고, URL 목록은 페이지별 재집계를
가능하게 한다. 목록 없이 무게만 흐르면 "103장" 은 남고 "어느 103장" 은 사라진다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from tests.seo.support import build_context

import veo.api.app  # noqa: F401
from veo.seo.service import run_seo_scan


class TestUrlScopeOutcomesCarryTheirPages:
    def test_a_failing_check_names_the_pages_that_failed(self) -> None:
        result = run_seo_scan(build_context("duplicate_metadata"))
        outcome = next(
            o for o in result.score.outcomes
            if o.check_id == "seo.onpage.title_present_and_unique"
        )

        assert outcome.affected_urls, "실패했는데 어느 페이지인지 없다"
        assert outcome.evaluated_urls
        assert set(outcome.affected_urls) <= set(outcome.evaluated_urls)

    def test_a_passing_check_still_names_what_it_judged(self) -> None:
        """통과도 판정이다 — "이 페이지들에서 확인했다" 가 없으면 페이지 점수에서
        통과와 미측정을 가를 수 없다."""
        result = run_seo_scan(build_context("healthy"))
        outcome = next(
            o for o in result.score.outcomes if o.check_id == "seo.http.status_ok"
        )

        assert outcome.affected_urls == ()
        assert len(outcome.evaluated_urls) == len(build_context("healthy").documents)

    def test_the_url_lists_agree_with_the_weights(self) -> None:
        """목록과 무게가 다른 페이지 집합에서 나오면 페이지 재집계가 사이트 점수와
        조용히 어긋난다. 둘은 같은 관측에서 나와야 한다."""
        result = run_seo_scan(build_context("duplicate_metadata"))

        for outcome in result.score.outcomes:
            if not outcome.evaluated_urls:
                continue
            if outcome.affected_weight == 0.0:
                assert outcome.affected_urls == (), outcome.check_id
            if outcome.affected_urls:
                assert outcome.affected_weight > 0.0, outcome.check_id
