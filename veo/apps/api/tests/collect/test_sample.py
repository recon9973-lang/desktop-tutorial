"""``해당 없음`` 과 ``측정 불가`` 를 가르는 규칙, 경우의 수 전부.

이 하나가 틀리면 **덜 재는 편이 유리해진다.** 실제로 두 번 그랬다 — SEO 수집기에서
한 번(1장 52.23점 → 25장 50.11점), 그리고 GEO 수집기에서 한 번 더. 두 번째는 규칙이
`seo/collectors/base.py` 안에만 있어서 GEO 쪽에서 보이지 않았기 때문이다.

이제 규칙은 `veo.collect.sample` 한 곳에 있고, 이 파일이 그것을 고정한다. 표를 통째로
적어 두는 이유는, 한 칸만 뒤집혀도 점수가 조용히 부풀기 때문이다.
"""

from __future__ import annotations

import pytest

from veo.collect.sample import (
    SampleScope,
    absent_in_sample_outcome,
    single_page_outcome,
)
from veo.scoring import CheckStatus


def scope(*, exhaustive: bool, pages: int, declared: int) -> SampleScope:
    return SampleScope(
        crawl_is_exhaustive=exhaustive, page_count=pages, declared_url_count=declared
    )


class TestWhenWeMaySayWeSawTheWholeSite:
    @pytest.mark.parametrize(
        ("exhaustive", "pages", "declared", "whole"),
        [
            # 예산·상한에 걸려 멈췄으면 무엇을 봤든 전부가 아니다.
            (False, 25, 30, False),
            (False, 1, 1, False),
            # 다 돌았고 여러 장을 가져왔다 — 링크 추적이 실제로 동작했다는 증거다.
            (True, 2, 0, True),
            (True, 25, 30, True),
            # 다 돌았는데 한 장뿐이다. 사이트가 스스로 "한 장이다" 라고 선언해야 인정한다.
            (True, 1, 1, True),
            (True, 1, 0, False),
            (True, 1, 30, False),
        ],
    )
    def test_the_truth_table(
        self, exhaustive: bool, pages: int, declared: int, whole: bool
    ) -> None:
        assert scope(exhaustive=exhaustive, pages=pages, declared=declared).is_whole_site is whole

    def test_a_site_that_hides_its_menu_in_javascript_does_not_get_the_benefit(self) -> None:
        """원본 HTML 에 링크가 없으면 크롤은 "더 볼 것이 없다" 고 판단한다.

        그것을 사이트 전체로 인정하면 **링크를 숨긴 사이트가 유리해진다.** sitemap 이
        없으면 한 장이라는 주장을 확인할 방법이 없으므로 인정하지 않는다.
        """
        assert not scope(exhaustive=True, pages=1, declared=0).is_whole_site


class TestPagesWeCouldNotCompare:
    def test_one_page_out_of_a_partial_crawl_is_unmeasured(self) -> None:
        outcome = single_page_outcome(
            scope(exhaustive=False, pages=1, declared=0), "x", subject_ko="중복 여부"
        )

        assert outcome.status is CheckStatus.UNKNOWN

    def test_one_page_that_really_is_the_whole_site_leaves_the_denominator(self) -> None:
        outcome = single_page_outcome(
            scope(exhaustive=True, pages=1, declared=1), "x", subject_ko="중복 여부"
        )

        assert outcome.status is CheckStatus.NOT_APPLICABLE

    def test_the_reason_says_what_would_settle_it(self) -> None:
        """"측정 불가" 만 띄우면 고장으로 읽힌다."""
        outcome = single_page_outcome(
            scope(exhaustive=True, pages=1, declared=0), "x", subject_ko="중복 여부"
        )

        assert "sitemap" in (outcome.note or "")


class TestThingsAbsentFromTheSample:
    def test_absent_from_a_partial_crawl_is_unmeasured(self) -> None:
        """"수집한 페이지 중에 없다" 와 "이 사이트에 없다" 는 다른 문장이다."""
        outcome = absent_in_sample_outcome(
            scope(exhaustive=False, pages=5, declared=40),
            "x",
            absent_ko="이 사이트에는 없습니다.",
            subject_ko="대상",
        )

        assert outcome.status is CheckStatus.UNKNOWN

    def test_absent_from_the_whole_site_leaves_the_denominator(self) -> None:
        outcome = absent_in_sample_outcome(
            scope(exhaustive=True, pages=5, declared=5),
            "x",
            absent_ko="이 사이트에는 없습니다.",
            subject_ko="대상",
        )

        assert outcome.status is CheckStatus.NOT_APPLICABLE
        assert outcome.note == "이 사이트에는 없습니다."


class TestTheIncentiveThisProtects:
    @pytest.mark.parametrize("pages", [1, 3, 25])
    def test_measuring_less_never_earns_a_pass_out_of_the_denominator(self, pages: int) -> None:
        """예산에 걸려 멈춘 수집은 몇 장을 봤든 배점을 빼 주지 않는다.

        빼 주면 "적게 재면 점수가 오른다" 가 성립하고, 그 순간 이 도구는 자기가 진단하는
        대상에게 잘못된 유인을 만든다.
        """
        outcome = absent_in_sample_outcome(
            scope(exhaustive=False, pages=pages, declared=100),
            "x",
            absent_ko="없습니다.",
            subject_ko="대상",
        )

        assert outcome.status is CheckStatus.UNKNOWN
