"""잘못된 판정 세 가지.

없는 기능을 더하기 전에 **틀린 답부터** 고친다. 판정이 틀리면 그 아래 모든 것 — 점수,
개선 순서, 고객에게 낸 보고서 — 이 함께 틀린다. 셋 다 실제 사이트에서 재현된다.

1. 구글이 문서화한 `max-image-preview:none` 을 색인 차단으로 읽어 25점 상한을 건다.
2. robots.txt 를 `veo-bot` 으로만 물어본다. `User-agent: Yeti` 로 네이버를 통째로
   막아 둔 사이트가 "허용" 으로 통과한다 — 병원 고객의 주력 유입원인데도.
3. `maximum-scale=10` 을 `maximum-scale=1` 로 읽어 확대를 막는 설정이라고 지적한다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id, status_of

from veo.scoring import CheckStatus
from veo.seo.collectors import CrawlIndexabilityCollector, PerformanceUxCollector

CRAWL = CrawlIndexabilityCollector()
PERF = PerformanceUxCollector()


def _with_meta_robots(fixture: str, value: str):
    """모든 페이지에 같은 robots 메타를 세운 맥락."""
    context = build_context(fixture)
    documents = {
        url: dataclasses.replace(
            document, body=_inject(document.body, f'<meta name="robots" content="{value}">')
        )
        for url, document in context.documents.items()
    }
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )


def _inject(body: bytes, tag: str) -> bytes:
    text = body.decode("utf-8", errors="replace")
    return text.replace("<head>", f"<head>{tag}", 1).encode("utf-8")


class TestMetaRobotsIsParsedNotSearched:
    """`content` 는 쉼표로 나뉜 지시자 목록이지 검색 대상 문자열이 아니다."""

    def test_max_image_preview_none_is_not_a_noindex(self) -> None:
        """구글이 문서화한 값이다. 이것을 차단으로 읽으면 멀쩡한 사이트가 25점이 된다."""
        result = CRAWL.collect(_with_meta_robots("healthy", "max-image-preview:none"))

        assert status_of(result, "seo.robots.meta_indexable") is CheckStatus.PASS

    def test_max_snippet_combination_is_not_a_noindex(self) -> None:
        result = CRAWL.collect(
            _with_meta_robots("healthy", "max-snippet:-1, max-image-preview:none")
        )

        assert status_of(result, "seo.robots.meta_indexable") is CheckStatus.PASS

    def test_a_real_noindex_still_fails(self) -> None:
        result = CRAWL.collect(_with_meta_robots("healthy", "noindex, follow"))

        assert status_of(result, "seo.robots.meta_indexable") is CheckStatus.FAIL

    def test_bare_none_still_fails(self) -> None:
        """`none` 은 `noindex, nofollow` 의 줄임말이다. 지시자 하나로 서 있으면 차단이다."""
        result = CRAWL.collect(_with_meta_robots("healthy", "none"))

        assert status_of(result, "seo.robots.meta_indexable") is CheckStatus.FAIL


class TestRobotsIsAskedForTheEnginesWeReportOn:
    """`veo-bot` 이 들어갈 수 있다는 사실은 고객에게 아무 의미가 없다."""

    def test_a_naver_only_block_is_reported(self) -> None:
        """`User-agent: Yeti` 차단은 병원 고객에게 가장 아픈 설정이다."""
        context = build_context("healthy")
        blocked = dataclasses.replace(
            context, robots_txt="User-agent: Yeti\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
        )

        result = CRAWL.collect(blocked)

        assert status_of(result, "seo.robots.txt_allows_url") is CheckStatus.FAIL

    def test_a_google_only_block_is_reported(self) -> None:
        context = build_context("healthy")
        blocked = dataclasses.replace(
            context,
            robots_txt="User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nAllow: /\n",
        )

        result = CRAWL.collect(blocked)

        assert status_of(result, "seo.robots.txt_allows_url") is CheckStatus.FAIL

    def test_the_engine_that_is_blocked_is_named(self) -> None:
        """'차단됨' 만으로는 어디를 고쳐야 할지 알 수 없다."""
        context = build_context("healthy")
        blocked = dataclasses.replace(
            context, robots_txt="User-agent: Yeti\nDisallow: /\n"
        )

        outcome = by_id(CRAWL.collect(blocked))["seo.robots.txt_allows_url"]

        assert outcome.note is not None
        assert "Yeti" in outcome.note or "네이버" in outcome.note

    def test_an_open_robots_still_passes(self) -> None:
        context = build_context("healthy")
        allowed = dataclasses.replace(context, robots_txt="User-agent: *\nAllow: /\n")

        assert status_of(CRAWL.collect(allowed), "seo.robots.txt_allows_url") is CheckStatus.PASS


class TestViewportIsParsedNotSearched:
    def test_maximum_scale_10_allows_zooming(self) -> None:
        """`maximum-scale=1` 을 부분 문자열로 찾으면 10, 100 이 함께 걸린다."""
        context = _with_viewport("healthy", "width=device-width,initial-scale=1,maximum-scale=10")

        assert status_of(PERF.collect(context), "seo.ux.mobile_viewport") is CheckStatus.PASS

    def test_maximum_scale_1_still_fails(self) -> None:
        context = _with_viewport("healthy", "width=device-width,maximum-scale=1")

        assert status_of(PERF.collect(context), "seo.ux.mobile_viewport") is CheckStatus.FAIL

    def test_user_scalable_no_still_fails(self) -> None:
        context = _with_viewport("healthy", "width=device-width,user-scalable=no")

        assert status_of(PERF.collect(context), "seo.ux.mobile_viewport") is CheckStatus.FAIL

    def test_a_plain_responsive_viewport_passes(self) -> None:
        context = _with_viewport("healthy", "width=device-width, initial-scale=1")

        assert status_of(PERF.collect(context), "seo.ux.mobile_viewport") is CheckStatus.PASS


def _with_viewport(fixture: str, value: str):
    context = build_context(fixture)
    documents = {
        url: dataclasses.replace(
            document, body=_inject(document.body, f'<meta name="viewport" content="{value}">')
        )
        for url, document in context.documents.items()
    }
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )
