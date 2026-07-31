"""2026-08-01 구글 Lighthouse 대조로 더한 두 검사.

둘 다 구글이 배점을 주는데 우리에게는 없던 항목이다(`charset`, `crawlable-anchors`).
그런데 판정 기준은 구글을 그대로 옮기지 않았다. 국내 병원 홈페이지에서 실제로
일어나는 일이 다르기 때문이다.

**전화번호 링크를 결함으로 세면 모든 고객이 실패한다.** `tel:` 은 병원 홈페이지의
거의 모든 페이지에 있고, 크롤러가 따라갈 수 없지만 따라갈 이유도 없다. 이 파일의
절반은 "무엇을 결함으로 세지 않는가" 를 못 박는 시험이다 — 지나친 검사는 없는
검사보다 나쁘다. 없는 검사는 놓칠 뿐이지만, 지나친 검사는 멀쩡한 것을 고치라고
시키고 진짜 결함을 그 소음에 묻는다.

**인코딩은 한글에서 성격이 다르다.** 라틴 문자 페이지는 추측이 틀려도 대개 읽히지만,
EUC-KR 문서를 UTF-8 로 읽으면 본문 전체가 대체 문자가 되고 그대로 색인된다.
그래서 구글이 위생 등급으로 두는 항목을 우리도 위생에 두되 doctype 보다 비싸게 뒀다.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id

from veo.scoring import CheckStatus
from veo.seo.collectors import CrawlIndexabilityCollector, OnpageSemanticsCollector
from veo.seo.parsing.html import parse_html

#: 두 검사는 사는 곳이 다르다. charset 은 문서가 자기를 어떻게 설명하는가이고,
#: 크롤 가능한 링크는 크롤러가 사이트를 돌 수 있는가다.
ONPAGE = OnpageSemanticsCollector()
CRAWL = CrawlIndexabilityCollector()
CHARSET = "seo.html.charset_declared"
ANCHORS = "seo.crawl.crawlable_anchors"


def rewrite(*, strip_charset: bool = False, body: str = "", headers: dict | None = None):
    """healthy 픽스처를 손봐 다시 만든다."""
    context = build_context("healthy")
    documents = {}
    for url, document in context.documents.items():
        text = document.body.decode("utf-8", errors="replace")
        if strip_charset:
            text = text.replace('<meta charset="utf-8">', "", 1)
        if body:
            text = text.replace("</body>", f"{body}</body>", 1)
        merged = {
            key: value
            for key, value in document.headers.items()
            if not (strip_charset and key.lower() == "content-type")
        }
        merged.update({key.lower(): value for key, value in (headers or {}).items()})
        replaced = dataclasses.replace(
            document,
            body=text.encode("utf-8"),
            headers=merged,
            charset=None if strip_charset and not headers else document.charset,
        )
        documents[url] = replaced
    return dataclasses.replace(
        context, documents=documents, primary_document=next(iter(documents.values()))
    )


def outcome_of(context, check_id: str):  # type: ignore[no-untyped-def]
    collector = CRAWL if check_id == ANCHORS else ONPAGE
    return by_id(collector.collect(context))[check_id]


def issues_of(context, check_id: str):  # type: ignore[no-untyped-def]
    collector = CRAWL if check_id == ANCHORS else ONPAGE
    return [i for i in collector.collect(context).issues if i.check_id == check_id]


# --------------------------------------------------------------------------- #
# 인코딩 선언 — 파서
# --------------------------------------------------------------------------- #


class TestCharsetParsing:
    def test_the_html5_form_is_read(self) -> None:
        page = parse_html('<html><head><meta charset="UTF-8"></head></html>')
        assert page.declared_charset == "utf-8"

    def test_the_older_http_equiv_form_is_read(self) -> None:
        """국내 병원 홈페이지는 오래된 제작 도구로 만든 경우가 많다.

        `<meta charset>` 만 보면 멀쩡히 선언한 사이트를 결함으로 적게 된다.
        """
        page = parse_html(
            '<html><head><meta http-equiv="Content-Type" '
            'content="text/html; charset=euc-kr"></head></html>'
        )
        assert page.declared_charset == "euc-kr"

    def test_case_and_spacing_do_not_matter(self) -> None:
        page = parse_html(
            "<html><head><META HTTP-EQUIV='content-type' "
            "content='text/html;  CHARSET= EUC-KR '></head></html>"
        )
        assert page.declared_charset == "euc-kr"

    def test_an_empty_declaration_is_not_a_declaration(self) -> None:
        assert parse_html('<html><head><meta charset=""></head></html>').declared_charset is None

    def test_a_document_without_any_declaration_reports_none(self) -> None:
        assert parse_html("<html><head><title>t</title></head></html>").declared_charset is None

    def test_the_first_declaration_wins(self) -> None:
        """브라우저도 첫 번째를 쓴다. 뒤에 오는 것은 이미 늦었다."""
        page = parse_html(
            '<html><head><meta charset="utf-8">'
            '<meta http-equiv="Content-Type" content="text/html; charset=euc-kr">'
            "</head></html>"
        )
        assert page.declared_charset == "utf-8"


# --------------------------------------------------------------------------- #
# 인코딩 선언 — 판정
# --------------------------------------------------------------------------- #


class TestCharsetCheck:
    def test_a_declared_page_passes(self) -> None:
        assert outcome_of(build_context("healthy"), CHARSET).status is CheckStatus.PASS

    def test_a_page_with_no_declaration_anywhere_fails(self) -> None:
        assert outcome_of(rewrite(strip_charset=True), CHARSET).status is CheckStatus.FAIL

    def test_a_response_header_alone_is_enough_to_pass(self) -> None:
        """헤더가 있으면 브라우저는 추측하지 않는다. 그것으로 목적은 달성된다.

        문서 안에 없다는 사실은 통과 문구에 남긴다 — CDN 이 헤더를 떨어뜨리는 순간
        같은 파일이 다시 추측 대상이 되기 때문이다. 그러나 그것은 **지금 깨진 것이
        아니므로** 감점하지 않는다. 일어날 수 있는 일과 일어난 일을 섞지 않는다.
        """
        context = rewrite(
            strip_charset=True, headers={"content-type": "text/html; charset=utf-8"}
        )
        result = outcome_of(context, CHARSET)
        assert result.status is CheckStatus.PASS
        assert "헤더에만" in (result.note or "")

    def test_the_failure_carries_a_line_the_customer_can_paste(self) -> None:
        found = issues_of(rewrite(strip_charset=True), CHARSET)
        assert found, "실패했는데 조치 항목이 없다"
        assert "<meta charset" in (found[0].fix_example or "")

    def test_the_failure_says_what_actually_goes_wrong(self) -> None:
        """'인코딩을 선언하세요' 만으로는 왜 해야 하는지 알 수 없다."""
        found = issues_of(rewrite(strip_charset=True), CHARSET)[0]
        assert "한글" in found.business_impact_ko
        assert "색인" in found.business_impact_ko


# --------------------------------------------------------------------------- #
# 크롤 가능한 링크 — 결함으로 세지 않는 것들
#
# 이 묶음이 이 파일에서 가장 중요하다. 여기가 틀리면 아무 잘못 없는 병원이
# 실패 판정을 받는다.
# --------------------------------------------------------------------------- #


class TestAnchorsWeDoNotFlag:
    def test_a_phone_link_is_not_a_defect(self) -> None:
        """병원 홈페이지의 거의 모든 페이지에 전화번호 링크가 있다.

        크롤러가 따라갈 수 없지만 따라갈 이유도 없다. 이것을 세면 모든 고객이
        실패한다 — 아무 잘못도 하지 않았는데.
        """
        context = rewrite(body='<a href="tel:0212345678">전화 문의</a>')
        assert outcome_of(context, ANCHORS).status is CheckStatus.PASS

    def test_a_mail_link_is_not_a_defect(self) -> None:
        context = rewrite(body='<a href="mailto:hello@example.kr">이메일 문의</a>')
        assert outcome_of(context, ANCHORS).status is CheckStatus.PASS

    def test_an_in_page_anchor_is_not_a_defect(self) -> None:
        """탭·아코디언·본문 앵커의 정상적인 형태다.

        같은 페이지를 가리키므로 다른 페이지의 발견 가능성을 잃지 않는다.
        """
        context = rewrite(body='<a href="#reservation">예약 안내로 이동</a><a href="#">닫기</a>')
        assert outcome_of(context, ANCHORS).status is CheckStatus.PASS

    def test_a_healthy_site_passes(self) -> None:
        assert outcome_of(build_context("healthy"), ANCHORS).status is CheckStatus.PASS


# --------------------------------------------------------------------------- #
# 크롤 가능한 링크 — 실제로 잡아야 하는 것
# --------------------------------------------------------------------------- #


class TestAnchorsWeDoFlag:
    def test_a_javascript_only_menu_fails(self) -> None:
        """제작 도구가 만든 자바스크립트 메뉴. 국내 병원 홈페이지에 흔하다.

        메뉴가 따라가지지 않으면 그 메뉴로만 연결된 페이지 — 진료과목, 의료진,
        오시는 길 — 이 통째로 발견되지 않는다.
        """
        menu = (
            "<nav>"
            "<a onclick=\"go('/doctors')\">의료진 소개</a>"
            "<a href=\"javascript:void(0)\" onclick=\"go('/services')\">진료과목</a>"
            "</nav>"
        )
        assert outcome_of(rewrite(body=menu), ANCHORS).status is CheckStatus.FAIL

    def test_a_javascript_link_in_the_body_is_only_a_warning(self) -> None:
        """본문의 자바스크립트 버튼 하나와 메뉴 전체가 자바스크립트인 것은 다르다.

        앞은 그 링크 하나를 잃고, 뒤는 사이트의 하위 페이지 전부를 잃는다.
        같은 무게로 보고하면 어느 쪽이 급한지 화면에서 알 수 없다.
        """
        assert (
            outcome_of(rewrite(body='<a onclick="openModal()">상담 신청</a>'), ANCHORS).status
            is CheckStatus.WARNING
        )

    def test_the_navigation_failure_outranks_a_body_warning(self) -> None:
        """둘 다 있으면 실패로 보고한다. 더 아픈 쪽이 판정이 되어야 한다."""
        both = '<a onclick="openModal()">상담</a><nav><a onclick="go(\'/x\')">진료과목</a></nav>'
        assert outcome_of(rewrite(body=both), ANCHORS).status is CheckStatus.FAIL

    def test_the_failure_names_the_links_it_found(self) -> None:
        """'링크에 문제가 있습니다' 로는 어느 것을 고칠지 알 수 없다."""
        menu = "<nav><a onclick=\"go('/doctors')\">의료진 소개</a></nav>"
        found = issues_of(rewrite(body=menu), ANCHORS)
        assert found, "실패했는데 조치 항목이 없다"
        assert "의료진 소개" in found[0].summary_ko

    def test_the_fix_keeps_the_javascript_behaviour(self) -> None:
        """href 를 넣으라는 조치가 기존 동작을 깨뜨리면 아무도 고치지 않는다.

        고칠 사람이 겁내지 않을 예시를 줘야 한다 — 사람은 스크립트로, 크롤러는
        href 로 가는 형태.
        """
        menu = "<nav><a onclick=\"go('/doctors')\">의료진 소개</a></nav>"
        example = issues_of(rewrite(body=menu), ANCHORS)[0].fix_example or ""
        assert "href=" in example
        assert "onclick" in example
