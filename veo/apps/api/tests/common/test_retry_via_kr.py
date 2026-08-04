"""관문 페이지를 만나면 한국에서 다시 받는다 — 그리고 **그때만** 다시 받는다.

2026-08-05 실측. 운영 서버(싱가포르)가 거래처 4곳 중 2곳에서 759·760바이트짜리
자바스크립트 쿠키 검사만 받았다. 같은 주소를 한국 데이터센터에서 받으면 정상이었다.

여기서 지키는 것 넷:

1. 관문 페이지면 **다시 받는다.**
2. 멀쩡한 응답은 **다시 받지 않는다** — 한 걸음이 늘면 그만큼 느려진다.
3. 경유가 실패하면 **원래 응답을 쓴다** — 관측점 고장이 사이트 판정을 바꾸면 안 된다.
4. 설정이 없으면 **아무 일도 하지 않는다.**
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

pytest.importorskip("httpx")

from veo.common.security.egress_kr import KoreanEgressUnavailable
from veo.common.security.fetcher import FetchedDocument
from veo.common.security.retry_via_kr import RetryViaKorea

#: 그날 실제로 받은 응답(759바이트)의 형태.
CHALLENGE = (
    b'<html><body><script src="/cupid.js"></script><script>'
    b'document.cookie="CUPID=x; path=/";location.href="https://venomad.com/?ckattempt=1";'
    b"</script></body></html>"
)
REAL_PAGE = (
    b"<html><head><title>\xeb\xb2\xa0\xeb\x86\x88\xec\x95\xa0\xeb\x93\x9c</title>"
    b"</head><body>x</body></html>"
)


def document(body: bytes, url: str = "https://venomad.com") -> FetchedDocument:
    return FetchedDocument(
        requested_url=url,
        final_url=url,
        status=200,
        headers={"content-type": "text/html"},
        body=body,
        content_hash=hashlib.sha256(body).hexdigest(),
        content_type="text/html",
        charset="utf-8",
        hops=(),
        resolved_ips=(),
        fetched_at=datetime.now(UTC),
        elapsed_ms=10,
        truncated=False,
        user_agent="VEO-Bot/1.0",
        request_headers={"user-agent": "VEO-Bot/1.0"},
        tls_expires_at=None,
    )


class _Direct:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls = 0

    def fetch(self, url: str, *, method: str = "GET") -> FetchedDocument:
        self.calls += 1
        return document(self.body, url)


class _Egress:
    def __init__(self, body: bytes | None = None, *, fails: bool = False) -> None:
        self.body = body
        self.fails = fails
        self.calls = 0

    def fetch(self, url: str) -> FetchedDocument:
        self.calls += 1
        if self.fails:
            raise KoreanEgressUnavailable("관측점이 답하지 않았습니다")
        assert self.body is not None
        return document(self.body, url)


class TestWhenWeGoThroughKorea:
    def test_a_challenge_page_is_fetched_again(self) -> None:
        direct, egress = _Direct(CHALLENGE), _Egress(REAL_PAGE)

        result = RetryViaKorea(direct, egress=egress).fetch("https://venomad.com")  # type: ignore[arg-type]

        assert egress.calls == 1
        assert result.body == REAL_PAGE

    def test_a_normal_page_is_not_fetched_again(self) -> None:
        """멀쩡한 응답까지 돌아가면 모든 진단이 느려진다. 실측에서 4곳 중 2곳은
        싱가포르에서도 정상이었다."""
        direct, egress = _Direct(REAL_PAGE), _Egress(REAL_PAGE)

        RetryViaKorea(direct, egress=egress).fetch("https://chamsarang1075.com")  # type: ignore[arg-type]

        assert egress.calls == 0

    def test_nothing_happens_when_it_is_not_configured(self) -> None:
        direct = _Direct(CHALLENGE)

        result = RetryViaKorea(direct, egress=None).fetch("https://venomad.com")  # type: ignore[arg-type]

        assert result.body == CHALLENGE
        assert direct.calls == 1


class TestWhenTheDetourFails:
    def test_the_original_response_is_kept(self) -> None:
        """관측점 고장은 **대상 사이트의 사실이 아니다.** 원래 응답을 그대로 돌려주면
        `readable` 관문이 "수집 실패" 로 보고한다 — 있는 그대로다(0-K)."""
        direct, egress = _Direct(CHALLENGE), _Egress(fails=True)

        result = RetryViaKorea(direct, egress=egress).fetch("https://venomad.com")  # type: ignore[arg-type]

        assert result.body == CHALLENGE

    def test_a_challenge_from_korea_too_is_reported_as_measured(self) -> None:
        """한국에서도 관문이 나오면 그것도 관측이다 — 위치 문제가 아니라는 사실."""
        direct, egress = _Direct(CHALLENGE), _Egress(CHALLENGE)

        result = RetryViaKorea(direct, egress=egress).fetch("https://venomad.com")  # type: ignore[arg-type]

        assert egress.calls == 1
        assert result.body == CHALLENGE
