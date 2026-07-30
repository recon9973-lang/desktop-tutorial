"""주소 하나로 GEO 준비도를 재는 경로.

이 경로가 없어서 GEO 준비도는 **화면에서 실행할 수 없었다.** 검사기 일곱 개가 완성돼
있었는데도 호출자가 수집물을 직접 만들어 넘겨야만 돌았고, 콘솔에는 그럴 방법이 없었다.

여기서 고정하는 것은 **SEO 와 같은 수집 경로를 쓴다**는 사실이다. 두 진단이 서로 다른
규칙으로 사이트를 돌면 두 결과를 나란히 놓을 수 없고, 한쪽에서 고친 수집 결함이 다른
쪽에는 남는다. 실제로 사이트맵 미연결과 중요도 오분류는 그 자리의 결함이었다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.collect.from_crawl import context_from_crawl
from veo.common.security.fetcher import FetchedDocument
from veo.contracts.enums import UrlImportance
from veo.geo.service import GEO_SPEC_ID
from veo.scoring import latest_published
from veo.seo.crawl import CrawlOutcome

HTML = (
    "<html lang='ko'><head><title>클리닉</title></head>"
    "<body><h1>소개</h1></body></html>"
).encode()


def _document(url: str) -> FetchedDocument:
    return FetchedDocument(
        requested_url=url,
        final_url=url,
        status=200,
        headers={"content-type": "text/html; charset=utf-8"},
        body=HTML,
        content_hash="0" * 64,
        content_type="text/html",
        charset="utf-8",
        hops=(),
        resolved_ips=(),
        fetched_at=datetime.now(UTC),
        elapsed_ms=12,
    )


@pytest.fixture
def outcome() -> CrawlOutcome:
    return CrawlOutcome(
        documents=(
            _document("https://clinic.example/"),
            _document("https://clinic.example/tag/laser?page=2"),
        ),
        robots_txt="User-agent: *\nSitemap: https://clinic.example/sitemap.xml\n",
        sitemaps={"https://clinic.example/sitemap.xml": "<urlset></urlset>"},
        discovered={},
        failures=(),
        robots_blocked=(),
        discovery_exhausted=True,
    )


class TestTheSharedContext:
    def test_the_sitemap_reaches_the_geo_context(self, outcome: CrawlOutcome) -> None:
        """사이트맵을 안 넘기면 관련 검사가 **언제나** 측정 불가가 된다.

        SEO 에서 정확히 그 결함이 있었다. 같은 함수를 쓰므로 GEO 는 그것을 물려받지
        않는다 — 이 검사가 그 사실을 붙잡아 둔다.
        """
        context = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published(GEO_SPEC_ID),
            outcome=outcome,
            locale="ko-KR",
        )

        assert context.sitemap_documents != {}

    def test_url_importance_is_classified_not_flattened(self, outcome: CrawlOutcome) -> None:
        """모든 페이지를 대표 페이지로 넣으면 태그 한 장이 홈페이지와 같은 무게가 된다."""
        context = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published(GEO_SPEC_ID),
            outcome=outcome,
            locale="ko-KR",
        )

        assert context.url_importance["https://clinic.example/"] == (
            UrlImportance.CONVERSION_OR_HOME
        )
        assert context.url_importance["https://clinic.example/tag/laser?page=2"] == (
            UrlImportance.TAG_OR_FILTER
        )

    def test_it_does_not_pretend_the_rendered_dom_matches(self, outcome: CrawlOutcome) -> None:
        """렌더링 후 DOM 을 안 가져왔으면 원본과 같다고 **가정하지 않는다.**"""
        context = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published(GEO_SPEC_ID),
            outcome=outcome,
            locale="ko-KR",
        )

        assert context.rendered_dom == {}

    def test_an_exhausted_crawl_is_reported_as_exhaustive(self, outcome: CrawlOutcome) -> None:
        """"더 찾을 게 없어서 멈췄다" 와 "예산이 떨어져 멈췄다" 는 다른 사실이다."""
        context = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published(GEO_SPEC_ID),
            outcome=outcome,
            locale="ko-KR",
        )

        assert context.crawl_is_exhaustive is True


class TestTheTwoDiagnosticsSeeTheSameSite:
    def test_seo_and_geo_build_the_same_view_of_one_crawl(self, outcome: CrawlOutcome) -> None:
        """같은 수집물이면 두 진단이 본 사이트도 같아야 한다.

        수집물이 갈리면 "SEO 는 25장, GEO 는 1장" 같은 일이 조용히 생기고, 두 점수를
        같은 보고서에 실을 수 없게 된다.
        """
        seo = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published("veo.seo.readiness"),
            outcome=outcome,
            locale="ko-KR",
        )
        geo = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published(GEO_SPEC_ID),
            outcome=outcome,
            locale="ko-KR",
        )

        assert seo.documents.keys() == geo.documents.keys()
        assert seo.sitemap_documents == geo.sitemap_documents
        assert seo.url_importance == geo.url_importance
        assert seo.crawl_is_exhaustive == geo.crawl_is_exhaustive

    def test_they_are_still_scored_by_different_specifications(
        self, outcome: CrawlOutcome
    ) -> None:
        """재는 재료가 같다는 것과 뜻이 같다는 것은 다른 이야기다 (ADR 0003)."""
        seo = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published("veo.seo.readiness"),
            outcome=outcome,
            locale="ko-KR",
        )
        geo = context_from_crawl(
            target_url="https://clinic.example/",
            spec=latest_published(GEO_SPEC_ID),
            outcome=outcome,
            locale="ko-KR",
        )

        assert seo.spec.spec_id != geo.spec.spec_id


class TestWhatTheScreenIsToldAboutAreasOutsideTheScore:
    """참고 항목과 못 잰 항목을 화면이 구분할 수 있어야 한다.

    둘 다 점수가 없어서 응답만 보면 똑같아 보인다. 같게 그리면 참고 항목이 감점처럼
    읽히거나, 반대로 우리가 못 잰 것이 "원래 안 재는 항목" 처럼 읽힌다. 뒤쪽이 더 나쁘다.
    """

    def test_the_reply_says_which_areas_are_outside_the_score(
        self, outcome: CrawlOutcome
    ) -> None:
        from veo.geo.payload import payload_from
        from veo.geo.service import run_geo_readiness

        spec = latest_published(GEO_SPEC_ID)
        context = context_from_crawl(
            target_url="https://clinic.example/",
            spec=spec,
            outcome=outcome,
            locale="ko-KR",
        )
        payload = payload_from("https://clinic.example/", run_geo_readiness(context, spec=spec))

        outside = [c for c in payload.readiness.categories if not c.contributes_to_score]
        inside = [c for c in payload.readiness.categories if c.contributes_to_score]

        assert outside, "점수 밖 영역이 응답에서 사라지면 화면에 띄울 수 없다"
        assert inside, "점수 안 영역이 하나도 없으면 무언가 크게 잘못된 것이다"

    def test_every_area_outside_the_score_says_why(self, outcome: CrawlOutcome) -> None:
        """"점수에 안 들어감" 만 띄우면 왜인지 묻게 된다. 사유를 함께 준다."""
        from veo.geo.payload import payload_from
        from veo.geo.service import run_geo_readiness

        spec = latest_published(GEO_SPEC_ID)
        context = context_from_crawl(
            target_url="https://clinic.example/",
            spec=spec,
            outcome=outcome,
            locale="ko-KR",
        )
        payload = payload_from("https://clinic.example/", run_geo_readiness(context, spec=spec))

        for category in payload.readiness.categories:
            if category.contributes_to_score:
                assert category.outside_score_reason_ko is None
            else:
                assert category.outside_score_reason_ko, category.category_id
                assert "참고 항목" in category.outside_score_reason_ko

    def test_areas_inside_the_score_are_not_labelled_reference(
        self, outcome: CrawlOutcome
    ) -> None:
        """참고 표시가 점수 영역으로 번지면 감점을 참고로 둔갑시킬 수 있다."""
        from veo.geo.payload import payload_from
        from veo.geo.service import run_geo_readiness

        spec = latest_published(GEO_SPEC_ID)
        context = context_from_crawl(
            target_url="https://clinic.example/",
            spec=spec,
            outcome=outcome,
            locale="ko-KR",
        )
        payload = payload_from("https://clinic.example/", run_geo_readiness(context, spec=spec))

        scored_weight = sum(
            c.weight for c in payload.readiness.categories if c.contributes_to_score
        )
        assert scored_weight == pytest.approx(100.0)
