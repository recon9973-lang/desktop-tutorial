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
