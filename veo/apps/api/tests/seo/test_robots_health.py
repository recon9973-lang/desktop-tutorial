"""robots.txt 가 깨져 있으면 알려 준다.

검수에서 나온 것: robots.txt 에 문법이 어긋난 줄이 있어도 점수가 정상과 같았다.
파싱 불가한 줄을 건너뛰는 것은 구글도 하는 일이라 판정 자체는 맞지만, 그래서 고객은
**자기 robots.txt 가 망가져 있다는 사실을 영영 모른다.**

건너뛴 줄이 `Disallow: /admin` 을 의도한 것이었다면 의도한 차단이 걸리지 않은 것이고,
`Sitemap:` 을 의도한 것이었다면 사이트맵이 전달되지 않은 것이다. 어느 쪽이든 운영자가
믿고 있는 상태와 실제가 다르다.

감점은 경미로 둔다 — 크롤링을 막는 것이 아니라 의도가 전달되지 않는 문제이고, 실제로
무엇이 막혔는지는 다른 항목이 따로 판정한다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id, issues_for

from veo.scoring import CheckStatus
from veo.seo.collectors import CrawlIndexabilityCollector

COLLECTOR = CrawlIndexabilityCollector()
CHECK = "seo.robots.txt_parses_cleanly"


def run(robots: str | None):
    context = build_context("healthy")
    return COLLECTOR.collect(dataclasses.replace(context, robots_txt=robots))


class TestACleanFile:
    def test_a_well_formed_robots_passes(self) -> None:
        assert by_id(run("User-agent: *\nAllow: /\nSitemap: https://a.kr/s.xml"))[
            CHECK
        ].status is CheckStatus.PASS

    def test_comments_and_blank_lines_are_not_faults(self) -> None:
        text = "# 주석입니다\n\nUser-agent: *\n\n  \nDisallow: /admin  # 뒤 주석\n"
        assert by_id(run(text))[CHECK].status is CheckStatus.PASS

    def test_an_empty_file_is_clean(self) -> None:
        """빈 robots.txt 는 '아무것도 막지 않는다' 는 뜻이지 고장이 아니다."""
        assert by_id(run(""))[CHECK].status is CheckStatus.PASS


class TestABrokenFile:
    def test_a_line_without_a_colon_is_reported(self) -> None:
        text = "User-agent: *\nDisallow /admin\nAllow: /\n"

        assert by_id(run(text))[CHECK].status is CheckStatus.WARNING

    def test_the_line_number_is_named(self) -> None:
        """"어딘가 깨졌습니다" 로는 고칠 수 없다. 몇 번째 줄인지 말해야 한다."""
        text = "User-agent: *\nDisallow /admin\nAllow: /\n"

        outcome = by_id(run(text))[CHECK]
        assert "2" in (outcome.note or "")

    def test_the_broken_line_content_is_shown(self) -> None:
        outcome = by_id(run("User-agent: *\nDisallow /admin\n"))[CHECK]

        assert "Disallow /admin" in str(outcome.observed_value)

    def test_a_file_that_is_not_robots_at_all_is_reported(self) -> None:
        assert by_id(run("!!! 이건 robots.txt 가 아닙니다 @@@"))[CHECK].status is (
            CheckStatus.WARNING
        )

    def test_the_issue_says_what_the_skipped_line_would_have_done(self) -> None:
        drafts = issues_for(run("User-agent: *\nDisallow /admin\n"), CHECK)

        assert drafts
        assert drafts[0].remediation_ko
        assert drafts[0].business_impact_ko


class TestNoFileAtAll:
    def test_a_missing_robots_is_not_a_broken_robots(self) -> None:
        """robots.txt 가 없는 것은 전부 허용한다는 뜻이다. 없는 결함을 지어내지 않는다."""
        assert by_id(run(None))[CHECK].status is CheckStatus.NOT_APPLICABLE


class TestTheThreeThingsThatLookLikeNoRobotsFile:
    """**없음 · 서버 오류 · 응답 없음은 서로 다른 사실이다.**

    2026-08-06 실측: 같은 사이트에서 robots.txt 만 바꿨더니 404 · 500 · 타임아웃이
    **완전히 같은 결과**를 냈다 — `txt_allows_url` UNKNOWN, 점수 29.081753.
    수집기가 셋을 `None` 하나로 접었기 때문이다.

    그런데 `crawl.py` 의 주석은 "없다는 사실과 못 읽었다는 사실을 구분한다" 고 적혀
    있었다. 지킬 수 없는 약속이었다.

    왜 중요한가. **robots.txt 가 없는 것은 사실상 정상이다** — 표준이 그렇게 정한다
    (규칙 파일이 없으면 모든 크롤러에게 허용). 못 읽은 것은 우리 관측의 실패다.
    접어 두면 멀쩡한 사이트가 "robots.txt를 수집하지 못했습니다" 라는 **사실이 아닌
    문장**을 받는다.
    """

    def _crawl(self, robots_response: object) -> object:  # type: ignore[no-untyped-def]
        import httpx

        from veo.common.security.url_guard import UrlGuard
        from veo.seo.crawl import ConsoleCrawler

        html = {"content-type": "text/html"}
        page = (
            "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            "<title>참사랑의원</title><meta name='description' content='진료 안내입니다.'>"
            "</head><body><h1>참사랑의원</h1><p>본문입니다.</p></body></html>"
        ).encode()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                if isinstance(robots_response, Exception):
                    raise robots_response
                return robots_response  # type: ignore[return-value]
            return httpx.Response(200, content=page, headers=html)

        crawler = ConsoleCrawler(
            guard=UrlGuard(resolver=lambda host: ["93.184.216.34"]),
            transport=httpx.MockTransport(handler),
        )
        return crawler.crawl("https://example.com/", max_urls=1)

    def test_a_present_file_is_present(self) -> None:
        import httpx

        outcome = self._crawl(
            httpx.Response(
                200, content=b"User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"}
            )
        )

        assert outcome.robots_state == "PRESENT"  # type: ignore[attr-defined]

    def test_a_missing_file_is_absent_not_unreadable(self) -> None:
        """404 는 "규칙이 없다" 이지 "못 읽었다" 가 아니다."""
        import httpx

        outcome = self._crawl(
            httpx.Response(404, content=b"Not Found", headers={"content-type": "text/html"})
        )

        assert outcome.robots_state == "ABSENT"  # type: ignore[attr-defined]

    def test_a_server_error_is_unreadable(self) -> None:
        """5xx 는 파일이 있는지조차 알 수 없다."""
        import httpx

        outcome = self._crawl(
            httpx.Response(500, content=b"error", headers={"content-type": "text/html"})
        )

        assert outcome.robots_state == "UNREADABLE"  # type: ignore[attr-defined]

    def test_no_answer_at_all_is_unreadable(self) -> None:
        import httpx

        outcome = self._crawl(httpx.ReadTimeout("응답 없음"))

        assert outcome.robots_state == "UNREADABLE"  # type: ignore[attr-defined]


class TestASiteWithNoRobotsFileIsNotToldWeFailed:
    """규칙 파일이 없는 정상 사이트에게 **"수집하지 못했습니다"** 라고 말하지 않는다.

    이것이 고객이 실제로 보는 결과다. robots.txt 를 두지 않는 사이트는 흔하고,
    그 사이트는 아무것도 잘못하지 않았다.
    """

    def _scan(self, robots_response: object):  # type: ignore[no-untyped-def]
        import httpx

        from veo.collect.from_crawl import context_from_crawl
        from veo.common.security.url_guard import UrlGuard
        from veo.scoring import latest_published
        from veo.seo.crawl import ConsoleCrawler
        from veo.seo.service import run_seo_scan

        spec = latest_published("veo.seo.readiness")
        html = {"content-type": "text/html"}
        page = (
            "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            "<title>참사랑의원</title><meta name='description' content='진료 안내입니다.'>"
            "</head><body><h1>참사랑의원</h1><p>본문입니다.</p></body></html>"
        ).encode()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                if isinstance(robots_response, Exception):
                    raise robots_response
                return robots_response  # type: ignore[return-value]
            return httpx.Response(200, content=page, headers=html)

        crawler = ConsoleCrawler(
            guard=UrlGuard(resolver=lambda host: ["93.184.216.34"]),
            transport=httpx.MockTransport(handler),
        )
        outcome = crawler.crawl("https://example.com/", max_urls=1)
        context = context_from_crawl(
            target_url="https://example.com/", spec=spec, outcome=outcome, locale="ko-KR"
        )
        result = run_seo_scan(context)
        return next(
            item
            for item in result.score.outcomes
            if item.check_id == "seo.robots.txt_allows_url"
        )

    def test_a_missing_file_passes(self) -> None:
        import httpx

        from veo.scoring import CheckStatus

        found = self._scan(
            httpx.Response(404, content=b"Not Found", headers={"content-type": "text/html"})
        )

        assert found.status is CheckStatus.PASS

    def test_a_server_error_stays_unknown(self) -> None:
        """못 잰 것을 잰 것처럼 만들지 않는다 — 반대 방향으로 틀리면 안 된다(0-A)."""
        import httpx

        from veo.scoring import CheckStatus

        found = self._scan(
            httpx.Response(500, content=b"error", headers={"content-type": "text/html"})
        )

        assert found.status is CheckStatus.UNKNOWN
