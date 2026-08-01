"""부재 주장 — 표본으로 존재는 증명되지만 부재는 증명되지 않는다.

2026-08-01 실측(docs/research/DOMAIN_VALIDATION_2026-08.md §6)에서 도메인 8개 전부가
크롤 100장 상한에 잘린 채 "깨진 내부 링크 없음" 을 PASS 로 단정했다. 이 파일은 그
결함의 수정을 성질로 고정한다:

    위반 발견          → FAIL.    존재는 표본으로도 증명된다.
    미발견 + 전체 크롤  → PASS.    부재가 실제로 증명됐다.
    미발견 + 잘린 크롤  → UNKNOWN. 본 것에 없었다는 사실은 표본에 대한 사실이다.

UNKNOWN 은 분모에 남아 0점이므로(ADR 0016) **덜 재서 점수가 오르지 않는다** —
1장 52.23 > 25장 50.11 이 나오던 바로 그 구멍이 닫혔는지를 마지막 시험이 본다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from tests.seo.support import build_context

import veo.api.app  # noqa: F401
from veo.scoring import CheckStatus
from veo.seo.service import run_seo_scan

#: 부재를 주장하는 검사 넷. 설계(SEO_SCORING_V3_PAGES.md §2)가 정한 목록이다.
ABSENCE_CHECKS = (
    "seo.onpage.no_duplicate_metadata",
    "seo.content.no_duplicate_bodies",
    "seo.crawl.no_orphan_key_pages",
    "seo.crawl.no_broken_internal_links",
)


def statuses(fixture: str, *, exhaustive: bool) -> dict[str, object]:
    result = run_seo_scan(build_context(fixture, crawl_is_exhaustive=exhaustive))
    return {o.check_id: o for o in result.score.outcomes}


class TestACleanTruncatedCrawlMayNotAssertAbsence:
    """**이 파일의 핵심 묶음.** healthy 픽스처는 네 검사 모두 위반이 없다."""

    @pytest.mark.parametrize("check_id", ABSENCE_CHECKS)
    def test_a_whole_site_crawl_still_passes(self, check_id: str) -> None:
        """전체를 봤고 없었다 — 부재가 증명됐으니 PASS 는 정당하다."""
        outcome = statuses("healthy", exhaustive=True)[check_id]

        assert outcome.status in (CheckStatus.PASS, CheckStatus.NOT_APPLICABLE), (
            check_id,
            outcome.note,
        )

    @pytest.mark.parametrize("check_id", ABSENCE_CHECKS)
    def test_a_truncated_crawl_answers_unknown_not_pass(self, check_id: str) -> None:
        """잘린 크롤에서 "없다" 는 표본에 대한 사실일 뿐이다."""
        outcome = statuses("healthy", exhaustive=False)[check_id]

        assert outcome.status is CheckStatus.UNKNOWN, (check_id, outcome.status)

    @pytest.mark.parametrize("check_id", ABSENCE_CHECKS)
    def test_the_unknown_says_what_would_settle_it(self, check_id: str) -> None:
        """"측정 불가" 만 띄우면 고장으로 읽힌다(0-J). 다음 행동이 문구에 있어야 한다."""
        note = statuses("healthy", exhaustive=False)[check_id].note or ""

        assert "확인하지 못했습니다" in note
        assert "전체를 재면 판정됩니다" in note


class TestAFoundViolationStaysAFailure:
    """존재는 표본으로도 증명된다 — 잘린 크롤이 결함을 지워 주면 안 된다."""

    def test_duplicates_found_in_a_truncated_crawl_still_fail(self) -> None:
        outcome = statuses("duplicate_metadata", exhaustive=False)[
            "seo.onpage.no_duplicate_metadata"
        ]

        assert outcome.status is CheckStatus.FAIL

    def test_orphans_found_in_a_truncated_crawl_still_fail(self) -> None:
        outcome = statuses("orphan_page", exhaustive=False)["seo.crawl.no_orphan_key_pages"]

        assert outcome.status is CheckStatus.FAIL


class TestSeeingFewerPagesNeverRaisesTheScore:
    def test_the_truncated_crawl_scores_at_most_the_whole_crawl(self) -> None:
        """덜 재서 점수가 오르면 진단 도구가 만들면 안 되는 유인이 생긴다.

        UNKNOWN 이 분모에 남아 0점이 되므로(ADR 0016) 잘린 크롤의 점수는 같은
        판정에서 반드시 낮거나 같아야 한다.
        """
        whole = run_seo_scan(build_context("healthy", crawl_is_exhaustive=True))
        truncated = run_seo_scan(build_context("healthy", crawl_is_exhaustive=False))

        assert whole.score.overall_score is not None
        assert truncated.score.overall_score is not None
        assert truncated.score.overall_score <= whole.score.overall_score
