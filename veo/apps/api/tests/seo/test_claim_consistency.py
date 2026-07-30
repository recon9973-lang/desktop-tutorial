"""구조화 데이터가 주장하는 값이 화면에 실제로 있는가.

검사 이름은 "구조화 데이터가 화면에 보이는 내용과 일치하는가" 인데, 지금까지 비교한 것은
`name` 과 `headline` 두 개뿐이었다. 정작 꾸며지는 값 — 평점, 후기 수, 전화번호, 주소 —
은 아무도 보지 않았다.

병원 고객에게 이건 두 겹으로 위험하다. 화면 어디에도 없는 `aggregateRating: 4.9,
reviewCount: 312` 은 구글의 구조화 데이터 정책 위반이자 수동 조치 대상이고, 동시에
의료법 제56조가 금지하는 환자 후기·평가 광고에 해당한다.

전화번호와 주소를 함께 보는 이유는 다르다. 그 둘은 이미 페이지의 JSON-LD 와 푸터에
모두 있는데 서로 맞는지 확인한 적이 없었다. 네이버 스마트플레이스·카카오맵과의 NAP
일관성은 지역 검색의 핵심인데, 자기 페이지 안에서부터 어긋나 있으면 그 앞이 없다.
"""

from __future__ import annotations

import dataclasses
import json

from tests.seo.support import build_context, by_id

from veo.scoring import CheckStatus
from veo.seo.collectors import StructuredDataCollector

COLLECTOR = StructuredDataCollector()
_CHECK = "seo.sd.matches_visible_content"


def _with_json_ld(node: dict[str, object], *, visible: str = ""):
    """JSON-LD 를 갈아 끼우고, 필요하면 본문에 보이는 텍스트를 심는다."""
    context = build_context("healthy")
    block = f'<script type="application/ld+json">{json.dumps(node, ensure_ascii=False)}</script>'
    documents = {}
    for url, document in context.documents.items():
        text = document.body.decode("utf-8", errors="replace")
        text = _strip_json_ld(text)
        text = text.replace("<head>", f"<head>{block}", 1)
        if visible:
            text = text.replace("</body>", f"<p>{visible}</p></body>", 1)
        documents[url] = dataclasses.replace(document, body=text.encode("utf-8"))
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )


def _strip_json_ld(text: str) -> str:
    out, rest = [], text
    while True:
        start = rest.lower().find('<script type="application/ld+json"')
        if start < 0:
            out.append(rest)
            return "".join(out)
        end = rest.lower().find("</script>", start)
        out.append(rest[:start])
        rest = rest[end + len("</script>") :] if end >= 0 else ""


_CLINIC = {
    "@context": "https://schema.org",
    "@type": "MedicalClinic",
    "name": "온담의원",
    "address": "서울특별시 강남구 테헤란로 1",
    "telephone": "02-555-1234",
}


class TestFabricatedRatings:
    def test_a_rating_nobody_can_see_is_a_mismatch(self) -> None:
        """구글 제재 대상이자 의료법 제56조 위반이다. 지금까지 통과했다."""
        node = {**_CLINIC, "aggregateRating": {"ratingValue": "4.9", "reviewCount": "312"}}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.FAIL

    def test_a_rating_shown_on_the_page_is_fine(self) -> None:
        node = {**_CLINIC, "aggregateRating": {"ratingValue": "4.9", "reviewCount": "312"}}

        result = COLLECTOR.collect(
            _with_json_ld(
                node,
                visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234 평점 4.9 후기 312건",
            )
        )

        assert by_id(result)[_CHECK].status is CheckStatus.PASS

    def test_the_fabricated_value_is_named(self) -> None:
        node = {**_CLINIC, "aggregateRating": {"ratingValue": "4.9", "reviewCount": "312"}}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        note = by_id(result)[_CHECK].note or ""
        assert "4.9" in note or "평점" in note


class TestContactDetailsAgreeWithThePage:
    def test_a_phone_number_only_in_the_markup_is_a_mismatch(self) -> None:
        """전화번호가 어긋나면 네이버·카카오맵과의 NAP 일관성은 그 앞에서 이미 깨진다."""
        node = {**_CLINIC, "telephone": "02-999-8888"}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.FAIL

    def test_an_address_only_in_the_markup_is_a_mismatch(self) -> None:
        node = {**_CLINIC, "address": "부산광역시 해운대구 센텀로 99"}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.FAIL

    def test_matching_contact_details_pass(self) -> None:
        result = COLLECTOR.collect(
            _with_json_ld(_CLINIC, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.PASS

    def test_a_phone_written_differently_on_the_page_still_matches(self) -> None:
        """`02-555-1234` 와 `02) 555-1234` 는 같은 번호다. 표기 차이로 실패시키지 않는다."""
        result = COLLECTOR.collect(
            _with_json_ld(_CLINIC, visible="온담의원 서울특별시 강남구 테헤란로 1 02) 555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.PASS


class TestKoreanPhoneNotation:
    """국제 표기와 국내 표기는 같은 번호다.

    schema.org 는 국제 표기를 권장하므로, 이 둘을 다른 값으로 보면 제대로 만든
    사이트일수록 어긋난다고 보고하게 된다.
    """

    def test_international_markup_matches_a_national_number_on_the_page(self) -> None:
        node = {**_CLINIC, "telephone": "+82-2-555-1234"}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.PASS

    def test_a_genuinely_different_number_still_fails(self) -> None:
        node = {**_CLINIC, "telephone": "+82-2-999-8888"}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.FAIL


class TestNameAndHeadlineMayMirrorTheTitle:
    """실제 사이트에서 잡힌 오탐.

    `WebPage.name` 과 `Article.headline` 은 문서의 제목을 옮겨 적는 자리다 — 원래
    그러라고 있는 필드이고, 워드프레스 SEO 플러그인이 자동으로 채운다. 그런데 화면
    본문에서만 찾으면 `<title>` 이 본문 텍스트에 포함되지 않으므로 **제대로 만든
    사이트가 통째로 실패한다.**

    실제로 마산의 한 한의원 사이트를 진단했을 때 7개 페이지가 이 이유로 실패했다.
    지어낸 값이 하나도 없는데 "구조화 데이터가 화면 내용과 어긋난다" 고 보고했다.

    꾸며지는 값을 잡겠다는 이 검사의 목적은 그대로다. 평점·후기 수·전화번호·주소는
    사용자가 화면에서 확인할 수 있어야 하고, 그 부분은 계속 엄격하게 본다.
    """

    def test_a_headline_that_equals_the_title_is_not_a_mismatch(self) -> None:
        node = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "오시는 길 - 온담의원",
            "name": "오시는 길 - 온담의원",
        }
        context = _with_json_ld(node, visible="오시는 길 온담의원 진료 안내")
        documents = {}
        for url, document in context.documents.items():
            text = document.body.decode("utf-8", errors="replace")
            text = text.replace("<title>", "<title>오시는 길 - 온담의원</title><!--", 1)
            documents[url] = dataclasses.replace(document, body=text.encode("utf-8"))
        context = dataclasses.replace(
            context, documents=documents, primary_document=next(iter(documents.values()))
        )

        assert by_id(COLLECTOR.collect(context))[_CHECK].status is CheckStatus.PASS

    def test_a_name_matching_a_heading_is_not_a_mismatch(self) -> None:
        node = {**_CLINIC, "name": "온담의원 레이저 클리닉"}
        context = _with_json_ld(
            node, visible="서울특별시 강남구 테헤란로 1 02-555-1234"
        )
        documents = {}
        for url, document in context.documents.items():
            text = document.body.decode("utf-8", errors="replace")
            text = text.replace("</body>", "<h2>온담의원 레이저 클리닉</h2></body>", 1)
            documents[url] = dataclasses.replace(document, body=text.encode("utf-8"))
        context = dataclasses.replace(
            context, documents=documents, primary_document=next(iter(documents.values()))
        )

        assert by_id(COLLECTOR.collect(context))[_CHECK].status is CheckStatus.PASS

    def test_a_fabricated_rating_is_still_caught(self) -> None:
        """느슨해진 것은 제목·제목 계층뿐이다. 꾸며진 평점은 그대로 잡힌다."""
        node = {**_CLINIC, "aggregateRating": {"ratingValue": "4.9", "reviewCount": "312"}}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.FAIL

    def test_a_phone_number_only_in_the_title_is_still_a_mismatch(self) -> None:
        """전화번호는 제목이 아니라 화면에서 확인되어야 한다."""
        node = {**_CLINIC, "telephone": "02-999-8888"}

        result = COLLECTOR.collect(
            _with_json_ld(node, visible="온담의원 서울특별시 강남구 테헤란로 1 02-555-1234")
        )

        assert by_id(result)[_CHECK].status is CheckStatus.FAIL
