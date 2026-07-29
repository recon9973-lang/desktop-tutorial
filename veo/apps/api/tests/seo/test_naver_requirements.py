"""네이버 노출 요건은 구조화 데이터가 없어도 물어야 한다.

오픈그래프는 네이버 검색 결과와 카카오톡 공유에서 **제목·설명·썸네일**이 되는 값이다.
JSON-LD 와는 별개의 것인데, 지금은 "이 페이지가 JSON-LD 를 선언했는가" 뒤에 가려 있다.

그래서 구조화 데이터가 하나도 없는 사이트는 구조화 데이터 다섯 검사가 통째로 '해당 없음'
이 되고, **네이버에 필요한 태그가 없다는 사실 자체를 안내받지 못한다.** 국내 병원 사이트의
대부분이 정확히 그 상태다 — 이 도구가 가장 도움이 되어야 할 고객이 아무 말도 못 듣는다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id

from veo.scoring import CheckStatus
from veo.seo.collectors import OnpageSemanticsCollector, StructuredDataCollector

COLLECTOR = OnpageSemanticsCollector()
STRUCTURED = StructuredDataCollector()

_NAVER = "seo.sd.naver_supported_type"
_JSONLD_CHECKS = (
    "seo.sd.jsonld_parses",
    "seo.sd.required_properties_present",
    "seo.sd.matches_visible_content",
    "seo.sd.google_supported_type",
)


def _without_json_ld(fixture: str, *, open_graph: dict[str, str] | None = None):
    """JSON-LD 를 걷어낸 맥락.

    `healthy` 픽스처는 오픈그래프가 완비돼 있으므로, 없는 상태를 보려면 그것도 걷어낸다.
    `open_graph` 를 주면 그 값들만 다시 심는다 — 국내 병원 사이트의 실제 상태(구조화
    데이터도 오픈그래프도 없음)를 재현하기 위한 것이다.
    """
    context = build_context(fixture)
    documents = {}
    for url, document in context.documents.items():
        text = document.body.decode("utf-8", errors="replace")
        text = _strip_json_ld(text)
        text = _strip_open_graph(text)
        if open_graph:
            tags = "".join(
                f'<meta property="{key}" content="{value}">'
                for key, value in open_graph.items()
            )
            text = text.replace("<head>", f"<head>{tags}", 1)
        documents[url] = dataclasses.replace(document, body=text.encode("utf-8"))
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )


def _strip_open_graph(text: str) -> str:
    """`<meta property="og:...">` 를 모두 걷어낸다."""
    out = []
    rest = text
    while True:
        start = rest.find('<meta property="og:')
        if start < 0:
            out.append(rest)
            return "".join(out)
        end = rest.find(">", start)
        out.append(rest[:start])
        rest = rest[end + 1 :] if end >= 0 else ""


def _strip_json_ld(text: str) -> str:
    out = []
    rest = text
    while True:
        start = rest.lower().find('<script type="application/ld+json"')
        if start < 0:
            out.append(rest)
            return "".join(out)
        end = rest.lower().find("</script>", start)
        out.append(rest[:start])
        rest = rest[end + len("</script>") :] if end >= 0 else ""


class TestNaverIsAskedRegardlessOfStructuredData:
    def test_a_site_without_json_ld_is_still_told_about_open_graph(self) -> None:
        """구조화 데이터가 없다는 것과 네이버 태그가 없다는 것은 다른 사실이다."""
        result = COLLECTOR.collect(_without_json_ld("healthy"))

        assert by_id(result)[_NAVER].status is CheckStatus.FAIL

    def test_the_json_ld_checks_are_still_not_applicable(self) -> None:
        """구조화 데이터가 없으면 구조화 데이터 검사는 그대로 '해당 없음' 이다."""
        outcomes = by_id(STRUCTURED.collect(_without_json_ld("healthy")))

        for check_id in _JSONLD_CHECKS:
            if check_id in outcomes:
                assert outcomes[check_id].status is CheckStatus.NOT_APPLICABLE

    def test_complete_open_graph_passes_without_any_json_ld(self) -> None:
        result = COLLECTOR.collect(
            _without_json_ld(
                "healthy",
                open_graph={
                    "og:title": "온담의원 피부과",
                    "og:description": "레이저 치료와 회복 안내",
                    "og:url": "https://ondam.example/",
                    "og:image": "https://ondam.example/thumb.jpg",
                },
            )
        )

        assert by_id(result)[_NAVER].status is CheckStatus.PASS

    def test_the_missing_tags_are_named(self) -> None:
        """'네이버 요건 미충족' 만으로는 무엇을 넣어야 할지 알 수 없다."""
        result = COLLECTOR.collect(
            _without_json_ld("healthy", open_graph={"og:title": "온담의원"})
        )

        note = by_id(result)[_NAVER].note or ""
        assert "og:image" in note or "썸네일" in note


class TestNonKoreanMarket:
    def test_a_non_korean_locale_is_not_asked(self) -> None:
        context = dataclasses.replace(_without_json_ld("healthy"), locale="en-US")

        assert by_id(COLLECTOR.collect(context))[_NAVER].status is CheckStatus.NOT_APPLICABLE
