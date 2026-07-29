"""콘솔 진단의 수집 단계.

무료 공개 진단은 `public_max_urls_per_scan = 1` 로 **한 페이지만** 본다. 그래서 측정
범위가 60% 언저리에서 멈추고, 사이트 전체를 봐야 판정되는 항목(내부 링크·중복 메타·
클릭 깊이 등)이 전부 UNKNOWN 으로 남는다. 콘솔은 그 제한을 쓰지 않는다.

여기서 고정하는 것은 두 가지다: 콘솔이 **더 많이** 보되, 공개 진단을 지켜 온 안전장치
(SSRF 차단, 호스트 예산, 크기·시간 상한)는 **하나도 우회하지 않는다**는 것.
"""

from __future__ import annotations

import httpx
import pytest

from veo.common.security.url_guard import UrlRejectedError
from veo.seo.crawl import ConsoleCrawler, CrawlRefusal


def _html(title: str) -> bytes:
    return (
        f"<!doctype html><html lang='ko'><head><title>{title}</title>"
        f"<meta name='description' content='설명'></head>"
        f"<body><h1>{title}</h1><a href='/b'>다음</a></body></html>"
    ).encode()


def _transport(pages: dict[str, bytes]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(request.url.path)
        if body is None:
            return httpx.Response(404, content=b"none")
        return httpx.Response(200, content=body, headers={"content-type": "text/html"})

    return httpx.MockTransport(handler)


class TestScope:
    def test_collects_every_requested_page(self) -> None:
        crawler = ConsoleCrawler(
            transport=_transport(
                {"/": _html("홈"), "/a": _html("가"), "/b": _html("나")}
            )
        )

        documents, _ = crawler.collect(
            ["https://example.com/", "https://example.com/a", "https://example.com/b"]
        )

        assert len(documents) == 3

    def test_refuses_more_pages_than_the_console_allows(self) -> None:
        """상한이 없으면 한 번의 실수로 남의 사이트를 수백 번 두드리게 된다."""
        crawler = ConsoleCrawler(transport=_transport({"/": _html("홈")}), max_urls=2)

        with pytest.raises(CrawlRefusal) as caught:
            crawler.collect([f"https://example.com/{n}" for n in range(3)])

        assert caught.value.status_code == 422

    def test_refuses_an_empty_list(self) -> None:
        crawler = ConsoleCrawler(transport=_transport({}))

        with pytest.raises(CrawlRefusal):
            crawler.collect([])


class TestSafety:
    def test_ssrf_guard_still_applies(self) -> None:
        """콘솔은 로그인한 직원이 쓰지만, 그렇다고 내부망을 열어 주지는 않는다."""
        crawler = ConsoleCrawler(transport=_transport({"/": _html("홈")}))

        with pytest.raises((CrawlRefusal, UrlRejectedError)):
            crawler.collect(["http://169.254.169.254/latest/meta-data/"])

    def test_a_dead_site_is_not_a_500(self) -> None:
        """고객 사이트가 죽어 있는 것은 VEO 의 오류가 아니다. 그렇게 말해야 한다."""

        def dead(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("연결 불가")

        crawler = ConsoleCrawler(transport=httpx.MockTransport(dead))

        with pytest.raises(CrawlRefusal) as caught:
            crawler.collect(["https://example.com/"])

        assert caught.value.status_code == 502
