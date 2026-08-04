"""한국 관측점으로 한 번 더 받아 본다.

**왜 있는가 — 실측.** 2026-08-05, 운영 서버(싱가포르, `34.21.188.186`)가 거래처 4곳 중
2곳에서 759·760바이트만 받는다. 그 정체는 차단 페이지가 아니라 **자바스크립트 쿠키
검사**다(`collect.readable.looks_like_interstitial` 참고). 같은 주소를 한국
데이터센터(`3.37.129.161`, AWS 서울)에서 받으면 51,262·64,262바이트가 정상적으로 온다.

    주소                 싱가포르   한국 데이터센터
    venomad.com             759 B      51,262 B
    good-tour.kr            760 B      64,262 B
    chamsarang1075.com  248,927 B     239,990 B   ← 검사 없음
    koreahhospital.com  333,955 B     298,347 B   ← 검사 없음

타사(NXT)가 같은 사이트를 문제없이 재는 이유도 여기 있다 — `next-t.co.kr` 은
`ec2-15-164-85-95.ap-northeast-2.compute.amazonaws.com`, **AWS 서울**이다(AWS 공식
`ip-ranges.json` 으로 확인). 우리 엔진이 못한 것이 아니라 **서버가 다른 나라에 있었다.**

**Googlebot 인 척하지 않는다.** 실측에서 Googlebot User-Agent 로는 검사가 면제됐다. 그
면제는 사이트가 **구글에게** 준 것이고, 우리가 구글인 척하면 사이트 주인을 속이는
것이다. 무엇보다 "잰 것을 그대로 보고한다" 는 이 제품의 근거가 무너진다.

## 안전에서 양보하지 않는 것

경유해도 :class:`~veo.common.security.guard.UrlGuard` 를 **먼저** 통과한다. 부르는 쪽이
이미 검증한 주소만 여기 들어온다.

* **리다이렉트를 대신 따라가지 않는다.** 관측점은 `redirect: manual` 로 받고 3xx 를
  그대로 돌려준다. 다음 홉은 우리 쪽 가드가 다시 검증한다 — 경유가 재검증을 건너뛰는
  구멍이 되면 안 된다.
* 관측점도 **자기 쪽에서 주소를 다시 확인한다.** 우리가 검증한 IP 와 관측점이 접속하는
  IP 는 다를 수 있고(DNS 가 다르게 답할 수 있다), 그 틈이 곧 SSRF 다.
* 열쇠 없이는 부를 수 없다. 없으면 우리 이름으로 남의 서버를 두드리는 공개 창구가 된다.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from datetime import UTC, datetime

import httpx

from veo.common.security.fetcher import (
    DEFAULT_USER_AGENT,
    FetchedDocument,
    TransportFailedError,
)
from veo.core.settings import Settings

__all__ = ["KoreanEgress", "KoreanEgressUnavailable", "korean_egress"]

_log = logging.getLogger(__name__)

#: 관측점이 돌려줄 수 있는 본문의 상한. 우리 쪽 예산과 별개로 한 번 더 막는다.
MAX_BODY_BYTES = 4 * 1024 * 1024


class KoreanEgressUnavailable(TransportFailedError):
    """관측점을 쓰지 못했다. **원래 응답을 그대로 쓰라는 뜻**이지 진단 실패가 아니다."""


class KoreanEgress:
    """한국에서 한 장을 대신 받아 온다."""

    __slots__ = ("_timeout", "_token", "_url", "_user_agent")

    def __init__(
        self, *, url: str, token: str, user_agent: str, timeout_seconds: float = 30.0
    ) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._user_agent = user_agent
        self._timeout = timeout_seconds

    def fetch(self, url: str) -> FetchedDocument:
        """``url`` 을 한국에서 받아 온다. 못 받으면 :class:`KoreanEgressUnavailable`."""
        started = time.monotonic()
        fetched_at = datetime.now(UTC)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    self._url,
                    json={"url": url, "userAgent": self._user_agent},
                    headers={"x-veo-egress-token": self._token},
                )
        except httpx.HTTPError as exc:
            raise KoreanEgressUnavailable(
                f"한국 관측점에 닿지 못했습니다: {type(exc).__name__}"
            ) from exc

        if response.status_code != 200:
            # 관측점 자신의 오류다. 대상 사이트의 사실이 아니므로 **판정에 쓰지 않는다.**
            raise KoreanEgressUnavailable(
                f"한국 관측점이 HTTP {response.status_code} 로 답했습니다"
            )

        try:
            payload = response.json()
            body = base64.b64decode(payload["bodyBase64"])
        except Exception as exc:
            raise KoreanEgressUnavailable("한국 관측점의 응답을 읽지 못했습니다") from exc

        headers = {str(k).lower(): str(v) for k, v in (payload.get("headers") or {}).items()}
        content_type = headers.get("content-type", "")
        return FetchedDocument(
            requested_url=url,
            final_url=str(payload.get("finalUrl") or url),
            status=int(payload["status"]),
            headers=headers,
            body=body,
            content_hash=hashlib.sha256(body).hexdigest(),
            content_type=content_type.split(";")[0].strip() or None,
            charset=_charset_of(content_type),
            # 홉과 해석된 주소는 **우리가 관측한 것이 아니다.** 관측점이 대신 연결했으므로
            # 비워 둔다 — 남의 관측을 우리 관측처럼 적으면 그때부터 기록이 거짓이 된다.
            hops=(),
            resolved_ips=(),
            fetched_at=fetched_at,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            truncated=bool(payload.get("truncated")),
            user_agent=self._user_agent,
            request_headers={"user-agent": self._user_agent},
            tls_expires_at=None,
        )


def korean_egress(settings: Settings) -> KoreanEgress | None:
    """설정이 갖춰졌으면 관측점을, 아니면 ``None``.

    ``None`` 은 "경유하지 않는다" 는 뜻이고 정상 상태다. 주소만 있고 열쇠가 없는
    반쪽 설정도 ``None`` 으로 본다 — 조용히 401 을 받으며 도는 것보다 안 켜진 것이 낫다.
    """
    if not settings.egress_kr_is_configured():
        return None
    return KoreanEgress(
        url=settings.egress_kr_url.strip(),
        token=settings.egress_kr_token.strip(),
        user_agent=DEFAULT_USER_AGENT,
    )


def _charset_of(content_type: str) -> str | None:
    for part in content_type.split(";")[1:]:
        key, _, value = part.strip().partition("=")
        if key.lower() == "charset":
            return value.strip().strip('"') or None
    return None
