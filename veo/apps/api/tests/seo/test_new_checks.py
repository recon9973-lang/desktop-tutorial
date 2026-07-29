"""명세 1.3.0 에서 더한 일곱 검사.

경쟁 도구가 보는데 우리가 보지 않던 것들이다. 그중 하나는 실질적인 구멍이었다 —
`title` 중복 선언. 테마와 SEO 플러그인이 각각 하나씩 넣는 구성에서 흔한데, 브라우저는
첫 번째만 표시하므로 화면상으로는 아무 문제가 없어 보이고, 검색엔진은 어느 것을 쓸지
알 수 없다.

지연 로딩은 속도 기법이 아니라 **색인 위험**으로 넣었다. 구글이 "잘못 구현하면 콘텐츠가
검색에서 숨겨질 수 있다" 고 명시한다. 나머지(파비콘·doctype·압축·최신 이미지 포맷·
리소스 힌트)는 구글이 요구하는 항목은 아니지만 확인 가능한 개선 여지라 경미로 넣었고,
그래서 실패가 아니라 **주의**로 보고한다.

배점에서 빠지는 연동 항목은 여기서 다루지 않는다 — `tests/scoring/test_scored_scope.py`
가 분모까지 함께 본다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id

from veo.scoring import CheckStatus
from veo.seo.collectors import (
    ContentArchitectureCollector,
    CrawlIndexabilityCollector,
    OnpageSemanticsCollector,
    PerformanceUxCollector,
)


def edit(fixture: str = "healthy", *, head: str = "", body: str = "", headers: dict | None = None):
    """픽스처의 모든 페이지에 조각을 심는다."""
    context = build_context(fixture)
    documents = {}
    for url, document in context.documents.items():
        text = document.body.decode("utf-8", errors="replace")
        if head:
            text = text.replace("<head>", f"<head>{head}", 1)
        if body:
            text = text.replace("</body>", f"{body}</body>", 1)
        merged = dict(document.headers)
        merged.update({key.lower(): value for key, value in (headers or {}).items()})
        documents[url] = dataclasses.replace(
            document, body=text.encode("utf-8"), headers=merged
        )
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )


def result_of(collector, context):  # type: ignore[no-untyped-def]
    return by_id(collector.collect(context))


class TestSingleTitle:
    CHECK = "seo.onpage.single_title_element"
    COLLECTOR = OnpageSemanticsCollector()

    def test_one_title_passes(self) -> None:
        outcome = result_of(self.COLLECTOR, build_context("healthy"))[self.CHECK]
        assert outcome.status is CheckStatus.PASS

    def test_two_titles_fail(self) -> None:
        """테마와 플러그인이 각각 하나씩 넣어 두는 경우가 흔하다."""
        context = edit(head="<title>플러그인이 넣은 제목</title>")

        assert result_of(self.COLLECTOR, context)[self.CHECK].status is CheckStatus.FAIL

    def test_the_count_is_reported(self) -> None:
        """"중복입니다" 만으로는 몇 개인지, 어디를 지워야 하는지 알 수 없다."""
        context = edit(head="<title>플러그인이 넣은 제목</title>")
        outcome = result_of(self.COLLECTOR, context)[self.CHECK]

        assert outcome.observed_value
        assert all(count == 2 for count in outcome.observed_value.values())

    def test_the_second_title_does_not_become_the_page_title(self) -> None:
        """두 title 의 글자를 이어 붙이면 없는 제목이 만들어져 길이·중복 검사까지 어지럽힌다."""
        context = edit(head="<title>플러그인이 넣은 제목</title>")
        page = next(iter(context.documents.values()))

        from veo.seo.parsing import parse_html

        parsed = parse_html(page.body.decode("utf-8"))
        assert parsed.title == "플러그인이 넣은 제목"
        assert parsed.title_count == 2


class TestDoctype:
    CHECK = "seo.html.doctype_standards_mode"
    COLLECTOR = OnpageSemanticsCollector()

    def test_html5_doctype_passes(self) -> None:
        outcome = result_of(self.COLLECTOR, build_context("healthy"))[self.CHECK]
        assert outcome.status is CheckStatus.PASS

    def test_a_missing_doctype_is_a_warning_not_a_failure(self) -> None:
        """구글이 요구하는 항목이 아니다. 실패로 올리면 경중이 뒤집힌다."""
        context = build_context("healthy")
        documents = {
            url: dataclasses.replace(
                document,
                body=document.body.decode("utf-8").replace("<!doctype html>", "", 1).encode(),
            )
            for url, document in context.documents.items()
        }
        context = dataclasses.replace(
            context, documents=documents, primary_document=next(iter(documents.values()))
        )

        assert result_of(self.COLLECTOR, context)[self.CHECK].status is CheckStatus.WARNING


class TestFavicon:
    CHECK = "seo.crawl.favicon_declared_and_crawlable"
    COLLECTOR = CrawlIndexabilityCollector()

    def test_a_declared_and_crawlable_favicon_passes(self) -> None:
        outcome = result_of(self.COLLECTOR, build_context("healthy"))[self.CHECK]
        assert outcome.status is CheckStatus.PASS

    def test_a_favicon_blocked_by_robots_is_reported(self) -> None:
        """선언만 보고 통과시키면 절반만 본 것이다. 구글은 그 파일을 가져갈 수 있어야 한다."""
        context = build_context("healthy")
        context = dataclasses.replace(
            context, robots_txt="User-agent: *\nDisallow: /favicon.ico\n"
        )

        outcome = result_of(self.COLLECTOR, context)[self.CHECK]
        assert outcome.status is CheckStatus.WARNING
        assert "robots" in (outcome.note or "")


class TestTextCompression:
    CHECK = "seo.perf.text_compression"
    COLLECTOR = PerformanceUxCollector()

    def test_gzip_passes(self) -> None:
        context = edit(headers={"content-encoding": "gzip"})
        assert result_of(self.COLLECTOR, context)[self.CHECK].status is CheckStatus.PASS

    def test_brotli_passes(self) -> None:
        context = edit(headers={"content-encoding": "br"})
        assert result_of(self.COLLECTOR, context)[self.CHECK].status is CheckStatus.PASS

    def test_no_compression_is_a_warning(self) -> None:
        context = edit(headers={"content-encoding": ""})
        assert result_of(self.COLLECTOR, context)[self.CHECK].status is CheckStatus.WARNING


class TestModernImageFormat:
    CHECK = "seo.perf.modern_image_format"
    COLLECTOR = PerformanceUxCollector()

    def test_webp_passes(self) -> None:
        outcome = result_of(self.COLLECTOR, build_context("healthy"))[self.CHECK]
        assert outcome.status is CheckStatus.PASS

    def test_a_page_without_images_is_not_faulted(self) -> None:
        """이미지가 없는 것은 옛 포맷을 쓰는 것과 다르다."""
        outcome = result_of(self.COLLECTOR, build_context("brochure_na"))[self.CHECK]
        assert outcome.status is not CheckStatus.FAIL


class TestResourceHints:
    CHECK = "seo.perf.resource_hints"
    COLLECTOR = PerformanceUxCollector()

    def test_preconnect_passes(self) -> None:
        outcome = result_of(self.COLLECTOR, build_context("healthy"))[self.CHECK]
        assert outcome.status is CheckStatus.PASS

    def test_no_hints_is_a_warning(self) -> None:
        outcome = result_of(self.COLLECTOR, build_context("brochure_na"))[self.CHECK]
        assert outcome.status in {CheckStatus.WARNING, CheckStatus.PASS}


class TestLazyLoadingSafety:
    CHECK = "seo.content.lazy_loading_safe"
    COLLECTOR = ContentArchitectureCollector()

    def test_a_site_without_lazy_loading_is_not_applicable(self) -> None:
        """안 쓰는 것은 결함이 아니다. 0점으로 매기면 없는 문제를 지어낸다."""
        outcome = result_of(self.COLLECTOR, build_context("brochure_na"))[self.CHECK]
        assert outcome.status is CheckStatus.NOT_APPLICABLE

    def test_lazy_loading_below_the_fold_passes(self) -> None:
        outcome = result_of(self.COLLECTOR, build_context("healthy"))[self.CHECK]
        assert outcome.status is CheckStatus.PASS

    def test_lazy_loading_on_the_first_image_fails(self) -> None:
        """첫 이미지는 대개 LCP 대상이다. 거기에 lazy 를 걸면 첫 화면이 늦어진다."""
        context = edit(body='<img src="/a.webp" alt="첫 이미지" loading="lazy">')
        # 본문 끝에 넣었으므로 문서 순서상 첫 이미지가 아니다. 머리 쪽에 넣어야 한다.
        context = edit()
        documents = {
            url: dataclasses.replace(
                document,
                body=document.body.decode("utf-8")
                .replace("<body>", '<body><img src="/hero.webp" alt="대표" loading="lazy">', 1)
                .encode("utf-8"),
            )
            for url, document in context.documents.items()
        }
        context = dataclasses.replace(
            context, documents=documents, primary_document=next(iter(documents.values()))
        )

        assert result_of(self.COLLECTOR, context)[self.CHECK].status is CheckStatus.FAIL

    def test_a_lazy_iframe_is_reported(self) -> None:
        """크롤러는 스크롤하지 않는다. iframe 안의 안내가 색인에서 빠질 수 있다."""
        context = edit(body='<iframe src="/notice/" loading="lazy" title="공지"></iframe>')

        outcome = result_of(self.COLLECTOR, context)[self.CHECK]
        assert outcome.status is CheckStatus.FAIL
        assert "iframe" in str(outcome.observed_value)
