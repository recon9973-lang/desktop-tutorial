"""홈페이지를 못 읽는 것은 **등록을 막을 일이 아니다.**

이 층이 지키는 것 둘 —

1. 사이트가 안 열려도 예외를 내지 않는다. 후보가 비고 사유가 붙는다. 등록 화면이
   500 을 받으면 사람은 등록 자체를 포기한다.
2. **왜 못 읽었는지 말한다.** 빈 목록만 돌려주면 "이 사이트에는 정보가 없다" 로
   읽히고, 그것은 사실이 아니다.

그리고 하나 더 — 한국 병의원 홈페이지에는 euc-kr 이 남아 있다. 인코딩을 잘못 읽으면
상호도 주소도 통째로 깨진 채 후보로 올라간다.
"""

from __future__ import annotations

import httpx
import pytest
from fakes import ZONE, FakeResolver

from veo.brands.discovery import IdentityField
from veo.brands.site_lookup import SiteIdentityReader
from veo.common.security.url_guard import UrlGuard

PAGE = (
    "<html><body>"
    "<p>더바른한의원 대표전화 053-355-0000</p>"
    "<p>대구광역시 북구 옥산로 95</p>"
    "</body></html>"
)


def reader(handler) -> SiteIdentityReader:  # type: ignore[no-untyped-def]
    return SiteIdentityReader(
        guard=UrlGuard(resolver=FakeResolver(ZONE)),
        transport=httpx.MockTransport(handler),
    )


def serving(body: bytes, *, status: int = 200, content_type: str = "text/html"):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body, headers={"content-type": content_type})

    return handler


class TestItReads:
    def test_받아서_후보를_돌려준다(self) -> None:
        draft = reader(serving(PAGE.encode())).read("https://example.com")

        values = [one.value for one in draft.candidates]
        assert "053-355-0000" in values
        assert "대구광역시 북구 옥산로 95" in values

    def test_euc_kr_페이지도_깨지지_않는다(self) -> None:
        """한국 병의원 홈페이지에 남아 있는 인코딩이다. 잘못 읽으면 전부 깨진다."""
        markup = (
            '<html><head><meta charset="euc-kr"></head>'
            "<body><p>대구광역시 북구 옥산로 95</p></body></html>"
        )
        draft = reader(serving(markup.encode("euc-kr"))).read("https://example.com")

        assert "대구광역시 북구 옥산로 95" in [one.value for one in draft.candidates]

    def test_등록한_주소가_아니라_최종_주소의_도메인을_쓴다(self) -> None:
        """리다이렉트가 있으면 실제로 도착한 곳이 그 업체의 도메인이다."""
        draft = reader(serving(PAGE.encode())).read("https://example.com/about")

        assert [one.value for one in draft.of(IdentityField.OWN_DOMAIN)] == ["example.com"]


class TestItRefusesQuietly:
    """실패해도 예외가 아니다 — 등록 화면이 살아 있어야 사람이 직접 채운다."""

    def test_사이트가_오류를_내면_사유를_붙여_돌려준다(self) -> None:
        draft = reader(serving(b"nope", status=503)).read("https://example.com")

        assert draft.found_nothing
        assert any("503" in note for note in draft.notes_ko)

    def test_HTML_이_아니면_말해_준다(self) -> None:
        draft = reader(serving(b"%PDF-1.4", content_type="application/pdf")).read(
            "https://example.com"
        )

        assert draft.found_nothing
        assert any("홈페이지가 아니" in note for note in draft.notes_ko)

    def test_접속이_안_되면_말해_준다(self) -> None:
        def explode(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        draft = reader(explode).read("https://example.com")

        assert draft.found_nothing
        assert any("읽지 못했습니다" in note for note in draft.notes_ko)

    @pytest.mark.parametrize(
        "url",
        ["http://127.0.0.1/admin", "http://localhost:8000", "file:///etc/passwd"],
    )
    def test_내부_주소로는_나가지_않는다(self, url: str) -> None:
        """등록 창구가 내부망을 들여다보는 통로가 되면 안 된다."""
        draft = reader(serving(PAGE.encode())).read(url)

        assert draft.found_nothing
        assert draft.notes_ko

    def test_사유_없이_빈_목록을_돌려주지_않는다(self) -> None:
        """빈 목록만 오면 화면은 '사이트에 정보가 없다'로 그린다 — 사실이 아니다."""
        draft = reader(serving(b"", status=500)).read("https://example.com")

        assert draft.found_nothing
        assert draft.notes_ko != ()
