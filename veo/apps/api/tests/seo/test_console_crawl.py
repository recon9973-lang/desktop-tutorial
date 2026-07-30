"""콘솔 진단의 수집 단계.

무료 공개 진단은 `public_max_urls_per_scan = 1` 로 **한 페이지만** 본다. 그래서 측정
범위가 60% 언저리에서 멈추고, 사이트 전체를 봐야 판정되는 항목(내부 링크·중복 메타·
클릭 깊이 등)이 전부 UNKNOWN 으로 남는다. 콘솔은 그 제한을 쓰지 않는다.

여기서 고정하는 것은 두 가지다: 콘솔이 **더 많이** 보되, 공개 진단을 지켜 온 안전장치
(SSRF 차단, 호스트 예산, 크기·시간 상한)는 **하나도 우회하지 않는다**는 것.
"""

from __future__ import annotations

import threading
import time

import httpx
import pytest

from veo.common.security.url_guard import UrlGuard, UrlRejectedError
from veo.core.settings import get_settings
from veo.seo.crawl import ConsoleCrawler, CrawlRefusal


def _html(title: str) -> bytes:
    return (
        f"<!doctype html><html lang='ko'><head><title>{title}</title>"
        f"<meta name='description' content='설명'></head>"
        f"<body><h1>{title}</h1><a href='/b'>다음</a></body></html>"
    ).encode()


def _guard() -> UrlGuard:
    """실제 DNS 를 쓰지 않는 가드.

    기본 가드는 호스트를 진짜로 조회한다. 그대로 두면 이 테스트가 네트워크에 의존하게
    되어, 단독으로는 통과하고 전체 실행에서는 조회 실패로 깨진다 — 실제로 그랬다.
    차단 규칙 자체는 그대로 두고 **주소 조회만** 고정한다.
    """
    return UrlGuard(resolver=lambda host: ["93.184.216.34"])


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
            guard=_guard(),
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
        crawler = ConsoleCrawler(
            guard=_guard(), transport=_transport({"/": _html("홈")}), max_urls=2
        )

        with pytest.raises(CrawlRefusal) as caught:
            crawler.collect([f"https://example.com/{n}" for n in range(3)])

        assert caught.value.status_code == 422

    def test_refuses_an_empty_list(self) -> None:
        crawler = ConsoleCrawler(guard=_guard(), transport=_transport({}))

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

        crawler = ConsoleCrawler(guard=_guard(), transport=httpx.MockTransport(dead))

        with pytest.raises(CrawlRefusal) as caught:
            crawler.collect(["https://example.com/"])

        assert caught.value.status_code == 502


# --------------------------------------------------------------------------- #
# 스스로 찾아 도는 크롤
# --------------------------------------------------------------------------- #


def _page(title: str, *links: str) -> bytes:
    anchors = "".join(f"<a href='{href}'>{href}</a>" for href in links)
    return (
        f"<!doctype html><html lang='ko'><head><title>{title}</title></head>"
        f"<body><h1>{title}</h1>{anchors}</body></html>"
    ).encode()


def _urlset(*locations: str) -> bytes:
    body = "".join(f"<url><loc>{location}</loc></url>" for location in locations)
    return f"<?xml version='1.0'?><urlset>{body}</urlset>".encode()


def _site(pages: dict[str, bytes]) -> httpx.MockTransport:
    """경로별 응답. 없는 경로는 404, 지정된 예외는 연결 실패."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(request.url.path)
        if body is None:
            return httpx.Response(404, content=b"none")
        if body is _DEAD:
            raise httpx.ConnectError("연결 불가")
        media = "application/xml" if request.url.path.endswith(".xml") else "text/html"
        if request.url.path == "/robots.txt":
            media = "text/plain"
        return httpx.Response(200, content=body, headers={"content-type": media})

    return httpx.MockTransport(handler)


_DEAD = b"__DEAD__"


class TestDiscovery:
    def test_follows_internal_links_without_being_told(self) -> None:
        """지금까지는 직원이 주소를 하나하나 넣어야 했다. 그래서 아무도 넣지 않았다."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site(
                {
                    "/": _page("홈", "/a", "/b"),
                    "/a": _page("가"),
                    "/b": _page("나"),
                }
            ),
        )

        outcome = crawler.crawl("https://example.com/")

        assert {document.final_url for document in outcome.documents} == {
            "https://example.com/",
            "https://example.com/a",
            "https://example.com/b",
        }

    def test_goes_deeper_than_one_level(self) -> None:
        """한 단계만 보면 클릭 깊이라는 개념 자체가 성립하지 않는다."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site(
                {
                    "/": _page("홈", "/a"),
                    "/a": _page("가", "/b"),
                    "/b": _page("나", "/c"),
                    "/c": _page("다"),
                }
            ),
        )

        outcome = crawler.crawl("https://example.com/")

        assert "https://example.com/c" in {d.final_url for d in outcome.documents}

    def test_stops_at_the_configured_depth(self) -> None:
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site(
                {
                    "/": _page("홈", "/a"),
                    "/a": _page("가", "/b"),
                    "/b": _page("나", "/c"),
                    "/c": _page("다", "/d"),
                    "/d": _page("라"),
                }
            ),
        )

        outcome = crawler.crawl("https://example.com/")

        # 기본 깊이 3 — 홈(0) 다음으로 세 단계까지다.
        assert "https://example.com/d" not in {d.final_url for d in outcome.documents}

    def test_reads_the_sitemap_and_scores_can_finally_see_it(self) -> None:
        """이 자리가 비어 있어서 사이트맵 두 항목이 어떤 사이트를 재도 측정 불가였다."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site(
                {
                    "/": _page("홈"),
                    "/robots.txt": b"Sitemap: https://example.com/sitemap.xml\n",
                    "/sitemap.xml": _urlset("https://example.com/", "https://example.com/z"),
                    "/z": _page("지"),
                }
            ),
        )

        outcome = crawler.crawl("https://example.com/")

        assert outcome.sitemaps
        assert "https://example.com/z" in {d.final_url for d in outcome.documents}

    def test_finds_the_sitemap_at_the_conventional_path(self) -> None:
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site(
                {
                    "/": _page("홈"),
                    "/sitemap.xml": _urlset("https://example.com/z"),
                    "/z": _page("지"),
                }
            ),
        )

        outcome = crawler.crawl("https://example.com/")

        assert "https://example.com/z" in {d.final_url for d in outcome.documents}

    def test_respects_the_page_ceiling(self) -> None:
        pages = {"/": _page("홈", *[f"/{n}" for n in range(30)])}
        pages.update({f"/{n}": _page(str(n)) for n in range(30)})
        crawler = ConsoleCrawler(guard=_guard(), transport=_site(pages))

        outcome = crawler.crawl("https://example.com/", max_urls=5)

        assert len(outcome.documents) == 5

    def test_obeys_the_target_robots_txt_for_its_own_crawling(self) -> None:
        """SEO 엔진은 robots.txt 를 평가한다. 이것은 VEO 가 그것을 지키는 쪽이다."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site(
                {
                    "/": _page("홈", "/private/x", "/ok"),
                    "/robots.txt": b"User-agent: *\nDisallow: /private\n",
                    "/private/x": _page("비공개"),
                    "/ok": _page("공개"),
                }
            ),
        )

        outcome = crawler.crawl("https://example.com/")

        collected = {document.final_url for document in outcome.documents}
        assert "https://example.com/private/x" not in collected
        assert "https://example.com/ok" in collected
        assert outcome.robots_blocked == ("https://example.com/private/x",)


class TestPartialFailure:
    def test_one_dead_page_does_not_kill_the_whole_scan(self) -> None:
        """사이트가 클수록 한 장쯤은 죽어 있다. 그걸로 진단 전체를 버리면 안 된다."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site({"/": _page("홈", "/a", "/dead"), "/a": _page("가"), "/dead": _DEAD}),
        )

        outcome = crawler.crawl("https://example.com/")

        assert {d.final_url for d in outcome.documents} == {
            "https://example.com/",
            "https://example.com/a",
        }
        assert [failure.url for failure in outcome.failures] == ["https://example.com/dead"]

    def test_a_failure_carries_a_sentence_a_person_can_read(self) -> None:
        crawler = ConsoleCrawler(
            guard=_guard(), transport=_site({"/": _page("홈", "/dead"), "/dead": _DEAD})
        )

        outcome = crawler.crawl("https://example.com/")

        assert outcome.failures[0].reason_ko

    def test_the_entry_page_is_still_fatal(self) -> None:
        """대표 페이지를 못 가져오면 채점할 대상 자체가 없다."""
        crawler = ConsoleCrawler(guard=_guard(), transport=_site({"/": _DEAD}))

        with pytest.raises(CrawlRefusal) as caught:
            crawler.crawl("https://example.com/")

        assert caught.value.status_code == 502

    def test_attempted_and_collected_are_both_reported(self) -> None:
        """몇 장을 보려 했고 몇 장을 봤는가. 그 차이가 곧 진단의 신뢰도다."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=_site({"/": _page("홈", "/a", "/dead"), "/a": _page("가"), "/dead": _DEAD}),
        )

        outcome = crawler.crawl("https://example.com/")

        assert outcome.attempted == 3
        assert len(outcome.documents) == 2


class TestParallelFetching:
    """수집은 거의 전부 기다리는 시간이다. 그래서 병렬이 그대로 이득이 된다.

    다만 병렬은 두 가지를 깨뜨릴 수 있고, 둘 다 여기서 막는다 — 대상 호스트 예산이
    우회되는 것과, 결과 순서가 실행마다 달라지는 것.
    """

    def test_pages_are_fetched_concurrently(self) -> None:
        """동시에 열린 요청 수를 직접 센다. 시간을 재는 방식은 느린 기계에서 흔들린다."""
        live = 0
        peak = 0
        guard = threading.Lock()

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal live, peak
            with guard:
                live += 1
                peak = max(peak, live)
            time.sleep(0.05)
            with guard:
                live -= 1
            if request.url.path == "/":
                return httpx.Response(
                    200,
                    content=_page("홈", *[f"/{n}" for n in range(8)]),
                    headers={"content-type": "text/html"},
                )
            return httpx.Response(200, content=_page("쪽"), headers={"content-type": "text/html"})

        crawler = ConsoleCrawler(guard=_guard(), transport=httpx.MockTransport(handler))
        crawler.crawl("https://example.com/", max_urls=9)

        assert peak > 1, "동시에 열린 요청이 하나뿐이다 — 직렬로 돌고 있다"

    def test_concurrency_never_exceeds_the_configured_ceiling(self) -> None:
        """이 숫자는 우리 속도가 아니라 대상 서버가 한순간에 받는 부하다."""
        live = 0
        peak = 0
        guard = threading.Lock()

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal live, peak
            with guard:
                live += 1
                peak = max(peak, live)
            time.sleep(0.05)
            with guard:
                live -= 1
            if request.url.path == "/":
                return httpx.Response(
                    200,
                    content=_page("홈", *[f"/{n}" for n in range(20)]),
                    headers={"content-type": "text/html"},
                )
            return httpx.Response(200, content=_page("쪽"), headers={"content-type": "text/html"})

        settings = get_settings().model_copy(update={"console_crawl_concurrency": 3})
        crawler = ConsoleCrawler(
            guard=_guard(), transport=httpx.MockTransport(handler), settings=settings
        )
        crawler.crawl("https://example.com/", max_urls=21)

        assert peak <= 3

    def test_the_host_budget_still_binds_under_concurrency(self) -> None:
        """예산은 VEO 가 남의 서버를 두드리는 도구가 되지 않게 막는 유일한 통제다.

        락이 없던 제한기는 32스레드·제한 10에서 14개를 통과시켰다. 병렬 수집은 그
        조건을 평범하게 만들어 내므로, 우회되지 않는지 여기서 고정한다.
        """
        sent = 0
        guard = threading.Lock()

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal sent
            with guard:
                sent += 1
            if request.url.path == "/":
                return httpx.Response(
                    200,
                    content=_page("홈", *[f"/{n}" for n in range(40)]),
                    headers={"content-type": "text/html"},
                )
            return httpx.Response(200, content=_page("쪽"), headers={"content-type": "text/html"})

        budget = 12
        settings = get_settings().model_copy(
            update={"console_target_host_limit_per_hour": budget}
        )
        crawler = ConsoleCrawler(
            guard=_guard(), transport=httpx.MockTransport(handler), settings=settings
        )

        outcome = crawler.crawl("https://example.com/", max_urls=41)

        assert sent <= budget, f"예산 {budget} 인데 {sent} 개를 보냈다"
        assert outcome.budget_exhausted

    def test_a_budget_stop_is_not_reported_as_a_page_failure(self) -> None:
        """예산 검사는 요청을 보내기 전에 걸린다. 대상 사이트는 그 사실을 모른다."""
        settings = get_settings().model_copy(
            update={"console_target_host_limit_per_hour": 6}
        )
        pages = {"/": _page("홈", *[f"/{n}" for n in range(20)])}
        pages.update({f"/{n}": _page(str(n)) for n in range(20)})
        crawler = ConsoleCrawler(
            guard=_guard(), transport=_site(pages), settings=settings
        )

        outcome = crawler.crawl("https://example.com/", max_urls=21)

        assert outcome.budget_exhausted
        assert outcome.failures == ()

    def test_the_document_order_is_the_same_every_run(self) -> None:
        """먼저 끝난 순서로 두면 같은 자료로 두 번 진단해도 증거 목록이 달라진다."""
        pages = {"/": _page("홈", *[f"/{n}" for n in range(12)])}
        pages.update({f"/{n}": _page(str(n)) for n in range(12)})

        def order() -> list[str]:
            crawler = ConsoleCrawler(guard=_guard(), transport=_site(pages))
            outcome = crawler.crawl("https://example.com/", max_urls=13)
            return [document.final_url for document in outcome.documents]

        runs = [order() for _ in range(5)]

        assert all(run == runs[0] for run in runs)

    def test_a_dead_page_among_many_is_still_only_its_own_failure(self) -> None:
        pages = {"/": _page("홈", *[f"/{n}" for n in range(6)])}
        pages.update({f"/{n}": _page(str(n)) for n in range(6)})
        pages["/3"] = _DEAD
        crawler = ConsoleCrawler(guard=_guard(), transport=_site(pages))

        outcome = crawler.crawl("https://example.com/", max_urls=7)

        assert [failure.url for failure in outcome.failures] == ["https://example.com/3"]
        assert len(outcome.documents) == 6

    def test_serial_and_parallel_collect_the_same_pages(self) -> None:
        """병렬 결과를 의심할 때 비교할 수 있어야 한다 — 그래서 1 이 직렬 경로다."""
        pages = {"/": _page("홈", *[f"/{n}" for n in range(10)])}
        pages.update({f"/{n}": _page(str(n)) for n in range(10)})

        def collected(concurrency: int) -> list[str]:
            settings = get_settings().model_copy(
                update={"console_crawl_concurrency": concurrency}
            )
            crawler = ConsoleCrawler(
                guard=_guard(), transport=_site(pages), settings=settings
            )
            outcome = crawler.crawl("https://example.com/", max_urls=11)
            return [document.final_url for document in outcome.documents]

        assert collected(1) == collected(4)


class TestRedirectsThatLandOnAPageWeHave:
    """리다이렉트가 이미 가진 페이지로 데려오면, 그것을 새 페이지로 세지 않는다.

    실측: 25번 가져온 것 중 15번이 같은 페이지로 떨어졌다. 그래도 "25장을 봤다" 고
    세고 있었다 — 측정 범위를 부풀리는 형태다.
    """

    @staticmethod
    def _redirects_home(paths: dict[str, bytes], moved: set[str]) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path in moved:
                return httpx.Response(301, headers={"location": "https://example.com/"})
            body = paths.get(path)
            if body is None:
                return httpx.Response(404, content=b"none")
            return httpx.Response(200, content=body, headers={"content-type": "text/html"})

        return httpx.MockTransport(handler)

    def test_the_same_page_is_not_counted_twice(self) -> None:
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=self._redirects_home(
                {"/": _page("홈", "/a", "/b", "/c"), "/c": _page("다")},
                moved={"/a", "/b"},
            ),
        )

        outcome = crawler.crawl("https://example.com/", max_urls=10)

        finals = [document.final_url for document in outcome.documents]
        assert len(finals) == len(set(finals)), f"같은 페이지를 여러 장으로 셌다: {finals}"

    def test_the_collapsed_urls_are_reported(self) -> None:
        """그 사실 자체가 진단 재료다 — 여러 주소가 한 페이지로 모인다는 것."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=self._redirects_home(
                {"/": _page("홈", "/a", "/b")}, moved={"/a", "/b"}
            ),
        )

        outcome = crawler.crawl("https://example.com/", max_urls=10)

        assert set(outcome.collapsed_urls) == {
            "https://example.com/a",
            "https://example.com/b",
        }

    def test_a_collapsed_url_is_not_a_failure(self) -> None:
        """가져오기는 성공했다. 실패로 세면 없는 결함을 만든다."""
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=self._redirects_home({"/": _page("홈", "/a")}, moved={"/a"}),
        )

        outcome = crawler.crawl("https://example.com/", max_urls=10)

        assert outcome.failures == ()

    def test_real_pages_beside_collapsed_ones_are_still_collected(self) -> None:
        crawler = ConsoleCrawler(
            guard=_guard(),
            transport=self._redirects_home(
                {"/": _page("홈", "/a", "/real"), "/real": _page("진짜")},
                moved={"/a"},
            ),
        )

        outcome = crawler.crawl("https://example.com/", max_urls=10)

        assert "https://example.com/real" in {d.final_url for d in outcome.documents}
