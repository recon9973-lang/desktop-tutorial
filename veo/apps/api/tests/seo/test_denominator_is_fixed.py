"""적게 수집한 것이 유리해지지 않는다.

`해당 없음` 은 분모에서 빠지고 `측정 불가` 는 분모에 남아 0점이다(ADR 0016). 그래서
"우리가 한 장만 봤다" 를 해당 없음으로 접으면 **덜 재는 쪽이 점수가 높아진다.** 진단
도구가 만들면 안 되는 유인이고, 이 저장소는 같은 실수를 세 번 했다. 이 파일은 네 번째를
막는다.

실측으로 드러난 값(고치기 전):

    veo.seokorea.org   1장 52.23점 → 25장 50.11점
    www.seokorea.org   1장 71.69점 → 25장 68.07점
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

import pytest

from veo.collect.contract import CollectionContext
from veo.scoring import CheckStatus, latest_published
from veo.seo.collectors.content_architecture import ContentArchitectureCollector
from veo.seo.collectors.onpage_semantics import OnpageSemanticsCollector
from veo.seo.service import run_seo_scan

from .support import build_context

#: 페이지가 둘 이상이어야 판정되는 검사들. 한 장뿐일 때 이 셋의 답이 문제였다.
CROSS_PAGE_CHECKS = (
    "seo.onpage.no_duplicate_metadata",
    "seo.content.no_duplicate_bodies",
    "seo.content.internal_link_density",
)

_ONE_PAGE_SITEMAP = (
    '<?xml version="1.0"?><urlset><url><loc>https://healthy.example.kr/</loc></url></urlset>'
)


def _single_page(context: CollectionContext, **overrides: object) -> CollectionContext:
    """진입 페이지 한 장만 남긴 문맥."""
    primary = context.primary_document or next(iter(context.documents.values()))
    return dataclasses.replace(
        context,
        documents={primary.final_url: primary},
        primary_document=primary,
        url_importance={primary.final_url: context.url_importance.get(primary.final_url, "")},
        **overrides,  # type: ignore[arg-type]
    )


def _status(context: CollectionContext, check_id: str) -> CheckStatus:
    collector = (
        OnpageSemanticsCollector()
        if check_id.startswith("seo.onpage.")
        else ContentArchitectureCollector()
    )
    outcomes = {o.check_id: o for o in collector.collect(context).outcomes}
    return outcomes[check_id].status


class TestOnePageIsNotAnExemption:
    @pytest.mark.parametrize("check_id", CROSS_PAGE_CHECKS)
    def test_collecting_one_page_is_unknown_not_exempt(self, check_id: str) -> None:
        """기본값은 측정 불가다. 우리가 안 본 것을 없는 것으로 접지 않는다."""
        context = _single_page(build_context("healthy"), sitemap_documents={})

        assert _status(context, check_id) is CheckStatus.UNKNOWN

    @pytest.mark.parametrize("check_id", CROSS_PAGE_CHECKS)
    def test_an_exhaustive_crawl_alone_is_not_enough(self, check_id: str) -> None:
        """링크가 없다고 페이지가 없는 것은 아니다 — 메뉴가 자바스크립트뿐일 수 있다."""
        context = _single_page(
            build_context("healthy"), sitemap_documents={}, crawl_is_exhaustive=True
        )

        assert _status(context, check_id) is CheckStatus.UNKNOWN

    @pytest.mark.parametrize("check_id", CROSS_PAGE_CHECKS)
    def test_the_site_declaring_one_page_makes_it_exempt(self, check_id: str) -> None:
        """사이트가 스스로 한 장이라고 선언했고 우리도 다 돌았다면, 없는 결함을 만들지 않는다."""
        context = _single_page(
            build_context("healthy"),
            sitemap_documents={"https://healthy.example.kr/sitemap.xml": _ONE_PAGE_SITEMAP},
            crawl_is_exhaustive=True,
        )

        assert _status(context, check_id) is CheckStatus.NOT_APPLICABLE

    @pytest.mark.parametrize("check_id", CROSS_PAGE_CHECKS)
    def test_the_reason_says_what_to_do_about_it(self, check_id: str) -> None:
        """'측정 불가' 만 띄우면 고장으로 읽힌다."""
        context = _single_page(build_context("healthy"), sitemap_documents={})
        collector = (
            OnpageSemanticsCollector()
            if check_id.startswith("seo.onpage.")
            else ContentArchitectureCollector()
        )
        outcome = {o.check_id: o for o in collector.collect(context).outcomes}[check_id]

        assert outcome.note
        assert "판정" in (outcome.note or "") or "확인" in (outcome.note or "")


class TestScoreDoesNotRewardLookingLess:
    def test_one_page_does_not_score_higher_than_the_whole_site(self) -> None:
        """같은 사이트를 덜 봤다는 이유로 점수가 올라가면 분모가 움직인 것이다."""
        whole = build_context("healthy")
        one_page = _single_page(whole, sitemap_documents={})

        whole_score = run_seo_scan(whole).score.overall_score
        one_page_score = run_seo_scan(one_page).score.overall_score

        assert whole_score is not None
        assert one_page_score is not None
        assert one_page_score <= whole_score, (
            f"한 장만 본 점수 {one_page_score} 가 사이트 전체 점수 {whole_score} 보다 높다 — "
            "덜 재는 편이 유리해졌다"
        )

    def test_the_three_checks_stay_in_the_denominator(self) -> None:
        """분모에서 빠지지 않았는지 직접 확인한다. 점수 비교만으로는 우연히 맞을 수 있다."""
        one_page = _single_page(build_context("healthy"), sitemap_documents={})

        result = run_seo_scan(one_page)
        excluded = {
            check_id
            for category in result.score.categories
            for check_id in category.not_applicable_check_ids
        }

        assert not excluded & set(CROSS_PAGE_CHECKS)

    def test_the_denominator_is_unchanged_by_how_much_we_collected(self) -> None:
        """채점 대상 항목 수는 수집량과 무관해야 한다."""
        whole = build_context("healthy")
        one_page = _single_page(whole, sitemap_documents={})

        def budget(context: CollectionContext) -> float:
            return sum(category.budget for category in run_seo_scan(context).score.categories)

        assert budget(one_page) == pytest.approx(budget(whole))


class TestTheFixWasNotADisguisedReweighting:
    """이것은 수집기의 판정 버그였다. 명세의 숫자로 덮은 것이 아니다(ADR 0012).

    처음에는 `spec.version == "1.6.0"` 한 줄이었다. 그러나 그 줄이 실제로 막는 것은
    **명세를 다시 발행하는 일 전부**였고, 그건 아무도 의도한 규칙이 아니다.
    실제로 2026-08-01 에 검사 두 개를 정당하게 더하면서 이 시험이 깨졌다 —
    잡아야 할 것을 잡은 게 아니라, 정상적인 발행을 막고 있었다.

    독스트링은 처음부터 "배점·심각도·가중치가 그대로" 를 못 박겠다고 적어 두었는데
    코드는 버전 문자열만 봤다. 이제 적힌 대로 검사한다. 누가 이 결함을 점수로
    덮으려 하면 — 예를 들어 교차 페이지 검사들의 심각도를 낮춰 차이를 지우려 하면 —
    버전을 올려도 여기서 걸린다.
    """

    #: 이 결함의 무대였던 검사들. 판정이 아니라 배점으로 차이를 지우는 것을 막는다.
    EXPECTED_SEVERITY: ClassVar[dict[str, str]] = {
        "seo.onpage.no_duplicate_metadata": "MAJOR",
        "seo.content.no_duplicate_bodies": "MAJOR",
        "seo.content.internal_link_density": "MINOR",
    }

    def test_the_cross_page_checks_keep_their_severity(self) -> None:
        spec = latest_published("veo.seo.readiness")
        for check_id, severity in self.EXPECTED_SEVERITY.items():
            assert str(spec.check(check_id).severity).endswith(severity), (
                f"{check_id} 의 심각도가 바뀌었다. 이 결함은 수집기에서 고친 것이고, "
                "배점으로 덮는 것은 같은 고침이 아니다."
            )

    def test_the_category_weights_are_unchanged(self) -> None:
        spec = latest_published("veo.seo.readiness")
        weights = {category.id: category.weight for category in spec.categories}
        assert weights["crawl_indexability"] == 31.25
        assert weights["onpage_semantics"] == 18.75
        assert weights["content_architecture"] == 18.75
