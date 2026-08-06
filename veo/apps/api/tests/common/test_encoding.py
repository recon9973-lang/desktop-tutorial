"""받은 바이트를 무엇으로 읽는가.

2026-08-06 실측: ``<meta charset="euc-kr">`` 페이지의 제목이
``'ѱ �����Դϴ'`` 로 읽힌 채 **43.3점과 지적 8건**이 나갔다. 사이트가 아니라 우리
디코딩 실패를 잰 것이다. 이 파일은 그 자리를 지킨다.
"""

from __future__ import annotations

from veo.common.encoding import decode_html, sniff_declared_charset
from veo.seo.parsing.html import parse_html

KOREAN_TITLE = "참사랑의원 내과 진료"
KOREAN_BODY = "예약과 진료시간을 안내합니다."


def _euckr_page(*, declaration: str) -> bytes:
    return (
        f"<!doctype html><html lang='ko'><head>{declaration}"
        f"<title>{KOREAN_TITLE}</title>"
        f"<meta name='description' content='{KOREAN_BODY}'>"
        f"</head><body><h1>{KOREAN_TITLE}</h1><p>{KOREAN_BODY}</p></body></html>"
    ).encode("euc-kr")


class TestTheDocumentGetsToDeclareItsOwnEncoding:
    def test_meta_charset_is_honoured_when_the_header_is_silent(self) -> None:
        """서버가 헤더로 안 알려 줘도 문서가 밝힌 것을 쓴다."""
        page = parse_html(_euckr_page(declaration="<meta charset='euc-kr'>"))

        assert page.title == KOREAN_TITLE
        assert page.meta_description == KOREAN_BODY
        assert KOREAN_BODY in page.body_text

    def test_the_old_http_equiv_form_is_honoured_too(self) -> None:
        """국내 병원 홈페이지는 옛 제작 도구가 만든 이 형태가 드물지 않다."""
        declaration = "<meta http-equiv='Content-Type' content='text/html; charset=euc-kr'>"

        page = parse_html(_euckr_page(declaration=declaration))

        assert page.title == KOREAN_TITLE

    def test_the_server_header_wins_over_the_document(self) -> None:
        """헤더는 응답과 함께 온 사실이다. 표준이 정한 우선순위를 따른다."""
        raw = _euckr_page(declaration="<meta charset='utf-8'>")

        _, used = decode_html(raw, header_charset="euc-kr")

        assert used == "euc-kr"

    def test_a_bom_beats_everything(self) -> None:
        raw = "﻿<html><head><meta charset='euc-kr'></head></html>".encode()

        _, used = decode_html(raw, header_charset="iso-8859-1")

        assert used == "utf-8-sig"


class TestTheSamePageScoresTheSameInEitherEncoding:
    """이 제품이 재는 것은 **사이트**여야 한다. 같은 내용을 어떤 인코딩으로 주든
    우리가 읽어 낸 것이 같아야, 점수 차이가 사이트의 차이가 된다.

    고치기 전 실측: 같은 문서가 utf-8 이면 29.1점, euc-kr 이면 43.3점이었다.
    14점 차이는 사이트의 사실이 아니라 우리 디코딩 실패였다.
    """

    def test_utf8_and_euckr_are_read_identically(self) -> None:
        source = (
            f"<!doctype html><html lang='ko'><head><meta charset='{{charset}}'>"
            f"<title>{KOREAN_TITLE}</title>"
            f"<meta name='description' content='{KOREAN_BODY}'>"
            f"</head><body><h1>{KOREAN_TITLE}</h1><p>{KOREAN_BODY}</p></body></html>"
        )

        as_utf8 = parse_html(source.format(charset="utf-8").encode("utf-8"))
        as_euckr = parse_html(source.format(charset="euc-kr").encode("euc-kr"))

        assert as_utf8.title == as_euckr.title
        assert as_utf8.meta_description == as_euckr.meta_description
        assert as_utf8.body_text == as_euckr.body_text
        assert as_utf8.headings == as_euckr.headings


class TestAWrongDeclarationIsAFindingNotACrash:
    def test_an_encoding_that_does_not_exist_falls_back_instead_of_raising(self) -> None:
        """사이트는 charset='unicode' 같은 없는 이름도 쓴다. 터지면 그 자리를
        사이트의 결함으로 적게 된다."""
        raw = "<html><head><meta charset='unicode'><title>가나다</title></head></html>".encode()

        text, used = decode_html(raw)

        assert used == "utf-8"
        assert "가나다" in text

    def test_a_header_that_does_not_exist_still_lets_the_document_speak(self) -> None:
        raw = _euckr_page(declaration="<meta charset='euc-kr'>")

        _, used = decode_html(raw, header_charset="charset-that-does-not-exist")

        assert used == "euc-kr"

    def test_nothing_declared_anywhere_is_utf8(self) -> None:
        raw = "<html><head><title>제목</title></head></html>".encode()

        text, used = decode_html(raw)

        assert used == "utf-8"
        assert "제목" in text


class TestSniffing:
    def test_a_declaration_past_the_window_is_not_searched_forever(self) -> None:
        """본문 전체를 훑을 이유가 없다. 명세는 앞쪽에 두라고 한다."""
        padded = b"<!--" + b"x" * 8000 + b"--><meta charset='euc-kr'>"

        assert sniff_declared_charset(padded) is None

    def test_a_document_with_no_declaration_sniffs_to_none(self) -> None:
        assert sniff_declared_charset(b"<html><body>plain</body></html>") is None
