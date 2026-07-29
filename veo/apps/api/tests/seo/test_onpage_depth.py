"""존재 여부를 넘어선 판정.

구현계획 §63-1 — "단순 항목 존재 여부를 넘어 유효성·정합성·범위·신뢰도를 평가한다."
두 항목이 그 선 아래에 있었다.

`title` 은 CRITICAL 인데 비어 있는지와 다른 페이지와 같은지만 봤다. 15자짜리 브랜드
조각도, 130자짜리 키워드 나열도 통과했다. 바로 아래 `meta description` 은 MINOR 인데
길이를 두 방향으로 본다 — 심각도와 판정 깊이가 거꾸로였다.

`html lang` 은 선언 여부만 봤다. 국내 사이트에서 가장 흔한 오기인 `lang="kr"` 은 언어
코드가 아니다(올바른 값은 `ko`). 통과하던 값이다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id

from veo.scoring import CheckStatus
from veo.seo.collectors import OnpageSemanticsCollector

COLLECTOR = OnpageSemanticsCollector()


def _with(fixture: str, *, title: str | None = None, lang: str | None = None):
    """길이·값만 보려는 테스트다. title 은 페이지마다 다르게 만들어 **중복 판정과 섞이지
    않게** 한다 — 같은 title 을 모든 페이지에 넣으면 길이가 멀쩡해도 중복으로 걸린다."""
    context = build_context(fixture)
    documents = {}
    for index, (url, document) in enumerate(context.documents.items()):
        text = document.body.decode("utf-8", errors="replace")
        if title is not None:
            start = text.find("<title>")
            end = text.find("</title>")
            if start >= 0 and end > start:
                unique = title if index == 0 else f"{title} {index}"
                text = text[: start + len("<title>")] + unique + text[end:]
        if lang is not None:
            start = text.find("<html")
            end = text.find(">", start)
            if start >= 0 and end > start:
                text = text[:start] + f'<html lang="{lang}"' + text[end:]
        documents[url] = dataclasses.replace(document, body=text.encode("utf-8"))
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )


class TestTitleLength:
    def test_a_title_too_short_to_carry_a_topic_is_flagged(self) -> None:
        """`온담` 만 있는 title 은 무엇을 하는 곳인지 말하지 않는다."""
        result = COLLECTOR.collect(_with("healthy", title="온담"))

        assert by_id(result)["seo.onpage.title_present_and_unique"].status is not CheckStatus.PASS

    def test_a_title_that_search_results_will_cut_is_flagged(self) -> None:
        result = COLLECTOR.collect(_with("healthy", title="강남 " * 40))

        assert by_id(result)["seo.onpage.title_present_and_unique"].status is not CheckStatus.PASS

    def test_the_measured_length_is_reported(self) -> None:
        """'너무 깁니다' 만으로는 얼마나 줄여야 할지 알 수 없다."""
        result = COLLECTOR.collect(_with("healthy", title="강남 " * 40))

        note = by_id(result)["seo.onpage.title_present_and_unique"].note or ""
        assert "자" in note

    def test_a_reasonable_korean_title_passes(self) -> None:
        result = COLLECTOR.collect(
            _with("healthy", title="레이저 치료 안내 — 회복 기간과 주의 사항 | 온담의원")
        )

        assert by_id(result)["seo.onpage.title_present_and_unique"].status is CheckStatus.PASS


class TestLanguageCode:
    def test_kr_is_not_a_language_code(self) -> None:
        """국내 사이트에서 가장 흔한 오기다. 올바른 값은 `ko` 다."""
        result = COLLECTOR.collect(_with("healthy", lang="kr"))

        assert by_id(result)["seo.onpage.html_lang_declared"].status is not CheckStatus.PASS

    def test_an_underscore_is_not_valid_bcp47(self) -> None:
        result = COLLECTOR.collect(_with("healthy", lang="ko_KR"))

        assert by_id(result)["seo.onpage.html_lang_declared"].status is not CheckStatus.PASS

    def test_ko_passes(self) -> None:
        assert (
            by_id(COLLECTOR.collect(_with("healthy", lang="ko")))[
                "seo.onpage.html_lang_declared"
            ].status
            is CheckStatus.PASS
        )

    def test_ko_kr_with_a_hyphen_passes(self) -> None:
        assert (
            by_id(COLLECTOR.collect(_with("healthy", lang="ko-KR")))[
                "seo.onpage.html_lang_declared"
            ].status
            is CheckStatus.PASS
        )

    def test_the_wrong_value_is_named(self) -> None:
        result = COLLECTOR.collect(_with("healthy", lang="kr"))

        note = by_id(result)["seo.onpage.html_lang_declared"].note or ""
        assert "kr" in note
