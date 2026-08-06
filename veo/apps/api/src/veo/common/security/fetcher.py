"""The only way VEO fetches a URL from the outside world.

`UrlGuard` decides *whether* an address may be contacted and *which* address that is.
This module is what makes that decision binding.

The gap it closes: a guard resolves ``example.com`` to a public IP and approves it, the
HTTP client is then handed the hostname and resolves it again — and an attacker with a
short-TTL record answers ``169.254.169.254`` the second time. Validating a hostname and
then connecting by hostname is not a control at all. So the connection is addressed to
the IP the guard returned, with the hostname carried in the ``Host`` header and in SNI so
virtual hosting and certificate verification still work.

Redirects are followed by hand, one hop at a time, each re-validated from scratch. The
client is never allowed to follow one itself, because following a redirect means
resolving a new hostname without asking anyone.

VEO crawls anonymously: no cookies are stored, no credentials are ever sent, and the
user agent says who is calling.
"""

from __future__ import annotations

import hashlib
import ssl
import time
import zlib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from veo.common.encoding import DEFAULT_ENCODING, decode_html
from veo.common.security.limits import (
    DecompressionLimitError,
    FetchLimits,
    ResponseBudget,
)
from veo.common.security.url_guard import (
    UrlDecision,
    UrlGuard,
    UrlRejectedError,
    UrlRejectionReason,
)

# HTTP header values must be latin-1 encodable, so this stays plain ASCII — the "·"
# used in VEO's product name elsewhere would raise on encode.
#
# The URL has to resolve to a real page. A site owner who finds an unfamiliar bot in
# their logs looks it up, and a dead link makes VEO an anonymous crawler worth blocking.
# See docs/operations/bot-identification.md.
#: 우리가 남의 서버에 밝히는 신원. 작업의뢰서 §5.2 가 정한 형태 그대로다.
#:
#: 괄호 앞의 토큰(`VEOBot`)이 robots.txt 매칭에 쓰이는 이름이다 —
#: `veo.seo.parsing.robots.CRAWLER_AGENT_NAME` 과 **반드시 같아야 한다.** 2026-08-06
#: 이전에는 UA 가 `VEO-Bot/1.0`, 매칭이 `veo-bot`, 의뢰서 요구가 `VEOBot/1.0` 으로
#: 셋이 달라, 거래처가 `User-agent: VEOBot` 으로 막아도 걸리지 않았다.
DEFAULT_USER_AGENT = "VEOBot/1.0 (+https://veo.seokorea.org/bot)"

#: 사이트 운영자가 로그를 보고 연락할 곳. 의뢰서 §5.2 가 요구하는 헤더다.
#: 대행사 서비스라 **클라이언트 웹 담당자가 로그를 보고 문의할 상황이 반드시 생긴다.**
CRAWLER_FROM = "bot@seokorea.org"

#: Response headers that must never be written into evidence as-is.
REDACTED_RESPONSE_HEADERS = frozenset(
    {"set-cookie", "set-cookie2", "authorization", "proxy-authorization", "www-authenticate"}
)

REDACTED = "[REDACTED]"


class FetchError(Exception):
    """Base class for a fetch that could not be completed."""


class RedirectLimitExceededError(FetchError):
    """Too many hops, or a loop. Either way VEO stops rather than chasing it."""


class TransportFailedError(FetchError):
    """The network refused, timed out or reset. Not a finding about the site's SEO."""


@dataclass(frozen=True, slots=True)
class FetchHop:
    """One leg of a redirect chain, recorded for evidence."""

    url: str
    status: int
    resolved_ip: str
    location: str | None
    elapsed_ms: int


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    """Everything a collector and an auditor need from one fetch.

    Deliberately carries the raw bytes *and* the hash: a check reads the bytes, and the
    evidence record proves later that the bytes have not changed since.
    """

    requested_url: str
    final_url: str
    status: int
    headers: Mapping[str, str]
    body: bytes
    content_hash: str
    content_type: str | None
    charset: str | None
    hops: tuple[FetchHop, ...]
    resolved_ips: tuple[str, ...]
    fetched_at: datetime
    elapsed_ms: int
    truncated: bool = False
    user_agent: str = DEFAULT_USER_AGENT
    request_headers: Mapping[str, str] = field(default_factory=dict)
    tls_expires_at: datetime | None = None
    """상대 인증서의 만료 시각. 평문 HTTP 이거나 읽지 못했으면 ``None``.

    갱신이 실패한 인증서는 만료되는 순간 사이트가 통째로 열리지 않는다. 핸드셰이크는
    어차피 일어나므로 그때 한 번 읽어 두면 추가 요청 없이 알 수 있다."""

    @property
    def was_redirected(self) -> bool:
        return len(self.hops) > 1

    def text(self, fallback: str = "utf-8") -> str:
        """Decode the body, never raising — a mis-declared charset is a finding, not a crash.

        ``self.charset`` 은 **서버 헤더가 말한 것**이고, 헤더가 없어도 문서가
        ``<meta charset>`` 으로 스스로 밝힌 인코딩이 있다. 그것을 안 보면 euc-kr
        페이지의 제목·본문이 통째로 깨진 채 채점된다(2026-08-06 실측).
        무엇으로 읽을지는 :mod:`veo.common.encoding` 한 곳이 정한다.
        """
        return self.decoded(fallback)[0]

    def decoded(self, fallback: str = DEFAULT_ENCODING) -> tuple[str, str]:
        """``(본문, 실제로 쓴 인코딩)``. 무엇으로 읽었는지가 필요한 곳에서 쓴다."""
        return decode_html(self.body, header_charset=self.charset, fallback=fallback)


class SafeFetcher:
    """Fetches a URL through the guard, pinned to the validated address."""

    def __init__(
        self,
        *,
        guard: UrlGuard,
        limits: FetchLimits | None = None,
        transport: httpx.BaseTransport | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._guard = guard
        self._limits = limits or FetchLimits()
        self._transport = transport
        self._user_agent = user_agent

    def fetch(self, url: str, *, method: str = "GET") -> FetchedDocument:
        """Fetch ``url``, re-validating every redirect. Raises rather than guessing."""
        started = time.monotonic()
        fetched_at = datetime.now(UTC)

        hops: list[FetchHop] = []
        resolved: list[str] = []
        current = url
        max_hops = self._guard.policy.max_redirects + 1

        with self._client() as client:
            for hop_index in range(max_hops):
                decision = self._guard.validate(current, hop=hop_index)
                if not decision.allowed or decision.resolved_ip is None:
                    raise UrlRejectedError(decision)

                hop_started = time.monotonic()
                # Streamed, not buffered: the size and bomb limits have to bite while
                # the body is arriving. Reading first and checking afterwards would mean
                # a 5 GB response is already in memory by the time it is refused.
                with self._stream(client, method, decision) as response:
                    elapsed_ms = int((time.monotonic() - hop_started) * 1000)
                    resolved.append(decision.resolved_ip)

                    location = response.headers.get("location")
                    hops.append(
                        FetchHop(
                            url=decision.url or current,
                            status=response.status_code,
                            resolved_ip=decision.resolved_ip,
                            location=location,
                            elapsed_ms=elapsed_ms,
                        )
                    )

                    if not _is_redirect(response) or not location:
                        # 스트림이 아직 열려 있는 동안에만 상대 인증서를 볼 수 있다.
                        expires_at = _peer_certificate_expiry(response)
                        body, truncated = self._read_body(response)
                        return FetchedDocument(
                            requested_url=url,
                            final_url=decision.url or current,
                            status=response.status_code,
                            headers=_safe_headers(response.headers),
                            body=body,
                            content_hash=hashlib.sha256(body).hexdigest(),
                            content_type=_media_type(response.headers.get("content-type")),
                            charset=_charset(response.headers.get("content-type")),
                            hops=tuple(hops),
                            resolved_ips=tuple(resolved),
                            fetched_at=fetched_at,
                            elapsed_ms=int((time.monotonic() - started) * 1000),
                            truncated=truncated,
                            user_agent=self._user_agent,
                            request_headers={
                                "user-agent": self._user_agent,
                                "from": CRAWLER_FROM,
                            },
                            tls_expires_at=expires_at,
                        )

                # A redirect is a brand new decision, resolved from scratch. Its body is
                # never read. Relative locations join against the hop actually reached.
                current = str(httpx.URL(decision.url or current).join(location))

        raise RedirectLimitExceededError(
            f"stopped after {max_hops} hops; the chain is too long or it loops"
        )

    # ----------------------------------------------------------------- #
    # Internals
    # ----------------------------------------------------------------- #

    def _client(self) -> httpx.Client:
        return httpx.Client(
            transport=self._transport,
            # 연결 10초 / 전체 30초 — 의뢰서 §5.2. 죽은 호스트에 30초를 매달려 있지
            # 않는다. 예전에는 전체 값 하나만 있었다.
            timeout=httpx.Timeout(
                self._limits.max_total_seconds, connect=self._limits.connect_seconds
            ),
            follow_redirects=False,  # never: following one means resolving one
            cookies=None,
            headers={
                "user-agent": self._user_agent,
                # 사이트 운영자가 로그를 보고 연락할 곳(의뢰서 §5.2). 대행사 서비스라
                # 클라이언트 웹 담당자가 로그를 보고 문의할 상황이 반드시 생긴다.
                "from": CRAWLER_FROM,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.1",
                "accept-encoding": "gzip, deflate",
            },
        )

    @contextmanager
    def _stream(
        self, client: httpx.Client, method: str, decision: UrlDecision
    ) -> Iterator[httpx.Response]:
        """Dial the validated address, presenting the real hostname.

        The URL handed to the client has the IP in the host position, so no name is
        resolved here. ``Host`` keeps virtual hosting working and ``sni_hostname`` keeps
        TLS verification checking the certificate against the name the user asked for —
        pinning the address must not weaken the certificate check.

        This is a context manager rather than a function returning one, and that is the
        whole point of the shape. ``httpx.Client.stream`` is itself a context manager: it
        sends nothing when called and everything when *entered*. Wrapping only the call
        therefore caught none of the errors it named — a refused connection, a DNS failure
        at connect time or a TLS handshake error was raised a frame later, in the caller's
        ``with``, and escaped as a raw ``httpx`` exception. Every unreachable site became
        an unhandled error instead of :class:`TransportFailedError`, which for a
        customer-facing scan is a 500 where a plain "the site did not answer" belongs.

        Entering inside the ``try`` closes that gap, and yielding inside it means a
        transport error while the *body* arrives is contained on the same terms.
        """
        if decision.url is None or decision.host is None or decision.resolved_ip is None:
            raise TransportFailedError("an allowed decision must carry a url, host and address")

        pinned = httpx.URL(decision.url).copy_with(host=decision.resolved_ip)

        try:
            with client.stream(
                method,
                pinned,
                headers={"host": decision.host},
                extensions={"sni_hostname": decision.host},
            ) as response:
                yield response
        except httpx.TimeoutException as exc:
            raise TransportFailedError(f"timed out fetching hop {decision.hop}") from exc
        except httpx.HTTPError as exc:
            raise TransportFailedError(
                f"transport failure on hop {decision.hop}: {type(exc).__name__}"
            ) from exc

    def _read_body(self, response: httpx.Response) -> tuple[bytes, bool]:
        """Stream the body under budget. **Oversized is cut, not refused.**

        크기 상한을 넘는 것과 압축 폭탄은 다르게 다룬다.

        *크기* — 앞부분만 담고 ``truncated`` 로 그 사실을 남긴다. 상한을 넘었다고
        진단을 통째로 버리면 **그 사이트는 영원히 진단할 수 없다.** 2026-08-06
        시뮬레이션에서 2MB 를 넘는 응답이 `CrawlRefusal` 로 진단 전체를 실패시켰다 —
        점수도, 부분 결과도 없었다. `FetchCapture` 모델은 처음부터 "상한을 넘으면
        앞부분만 담고 truncated 로 남긴다" 고 적어 두었는데 코드가 그러지 않았다.
        인라인 데이터가 많은 국내 병원 홈페이지는 2MB 를 넘을 수 있다.

        앞부분 2MB 로도 제목·설명·canonical·구조화 데이터는 거의 다 읽힌다. 그것들은
        ``<head>`` 에 있다. 잘린 사실은 결과에 실려 나가므로 "다 보고 내린 판정" 인
        척하지 않는다.

        *압축 폭탄* — 그대로 거절한다. 작은 응답이 수십 MB 로 부풀도록 만든 것은
        사이트의 사실이 아니라 우리를 넘어뜨리려는 입력이고, 그 앞부분도 믿을 것이
        못 된다.

        ``check_declared_length`` 를 더는 부르지 않는다. "5MB 라고 선언했다" 는 이유로
        읽기도 전에 거절하면, 우리가 기꺼이 읽을 수 있는 앞 2MB 까지 버리게 된다.
        실제 상한은 아래 흐름이 바이트를 세면서 건다.
        """
        budget = ResponseBudget(self._limits)
        budget.check_content_type(response.headers.get("content-type"))

        encoding = (response.headers.get("content-encoding") or "").lower()
        decoder = _decoder_for(encoding)

        chunks: list[bytes] = []
        truncated = False
        try:
            for chunk in response.iter_raw():
                budget.check_deadline()
                room = budget.remaining_bytes
                if room <= 0:
                    truncated = True
                    break
                if len(chunk) > room:
                    chunk = chunk[:room]
                    truncated = True
                budget.add_wire_bytes(len(chunk))
                if decoder is None:
                    budget.add_decompressed_bytes(len(chunk))
                    chunks.append(chunk)
                else:
                    expanded = decoder.decompress(chunk, self._limits.max_decompressed_bytes)
                    budget.add_decompressed_bytes(len(expanded))
                    chunks.append(expanded)
                    if decoder.unconsumed_tail:
                        # 작은 입력이 상한을 넘겨 부푼다 — 폭탄이다. 이건 거절한다.
                        raise DecompressionLimitError("decompressed body over budget")
                if truncated:
                    break
        except httpx.StreamConsumed:
            # The body was already materialised before we could stream it. Real network
            # transports never do this; test doubles built from a bytes literal always
            # do. The budget still applies — it just charges the whole body at once
            # instead of refusing it partway through.
            return self._charge_materialised_body(response, budget)

        return b"".join(chunks), truncated

    def _charge_materialised_body(
        self, response: httpx.Response, budget: ResponseBudget
    ) -> tuple[bytes, bool]:
        """Apply the budget to a body that is already in memory."""
        body = response.content  # httpx has decoded any content-encoding by this point
        room = budget.limits.max_response_bytes
        truncated = len(body) > room
        if truncated:
            body = body[:room]
        budget.add_wire_bytes(len(body))
        budget.add_decompressed_bytes(len(body))
        return body, truncated


def _decoder_for(encoding: str) -> zlib._Decompress | None:
    if encoding == "gzip":
        return zlib.decompressobj(16 + zlib.MAX_WBITS)
    if encoding == "deflate":
        return zlib.decompressobj()
    return None


def parse_certificate_expiry(certificate: Mapping[str, object] | None) -> datetime | None:
    """``getpeercert()`` 의 ``notAfter`` 를 시각으로 옮긴다.

    형식은 ``'Jun  1 12:00:00 2027 GMT'`` 처럼 자리 맞춤 공백이 들어간 C 계열 표기라,
    직접 파싱하지 않고 표준 라이브러리의 변환기를 쓴다. 읽지 못하면 **None** 이다 —
    못 읽은 것을 여유 있는 것으로 접으면 만료 직전인 사이트를 정상으로 보고하게 된다.
    """
    if not certificate:
        return None
    raw = certificate.get("notAfter")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromtimestamp(ssl.cert_time_to_seconds(raw), UTC)
    except (ValueError, OSError, OverflowError):
        return None


def _peer_certificate_expiry(response: httpx.Response) -> datetime | None:
    """열려 있는 응답에서 상대 인증서의 만료 시각을 읽는다.

    평문 HTTP, 그리고 테스트에서 쓰는 모의 전송에는 TLS 계층이 없다. 그때는 조용히
    ``None`` 이고, 그것은 "측정하지 못했다" 로 보고된다.
    """
    stream = response.extensions.get("network_stream")
    if stream is None:
        return None
    try:
        ssl_object = stream.get_extra_info("ssl_object")
        if ssl_object is None:
            return None
        return parse_certificate_expiry(ssl_object.getpeercert())
    except (AttributeError, ValueError, OSError):
        # 인증서를 읽지 못하는 것은 진단의 실패이지 수집의 실패가 아니다. 여기서
        # 예외를 올리면 인증서 하나 때문에 페이지 수집 전체가 무산된다.
        return None


def _is_redirect(response: httpx.Response) -> bool:
    return response.status_code in {301, 302, 303, 307, 308}


def _media_type(header: str | None) -> str | None:
    if not header:
        return None
    return header.split(";", 1)[0].strip().lower() or None


def _charset(header: str | None) -> str | None:
    if not header or "charset=" not in header.lower():
        return None
    for part in header.split(";"):
        name, _, value = part.partition("=")
        if name.strip().lower() == "charset":
            return value.strip().strip('"').lower() or None
    return None


def _safe_headers(headers: httpx.Headers) -> dict[str, str]:
    """Response headers with the credential-bearing ones blanked.

    Evidence is read by developers and exported into reports. A ``Set-Cookie`` copied
    verbatim into a report is a session handed to whoever reads it.
    """
    return {
        key.lower(): (REDACTED if key.lower() in REDACTED_RESPONSE_HEADERS else value)
        for key, value in headers.items()
    }


__all__ = [
    "DEFAULT_USER_AGENT",
    "FetchError",
    "FetchHop",
    "FetchedDocument",
    "RedirectLimitExceededError",
    "SafeFetcher",
    "TransportFailedError",
    "UrlRejectedError",
    "UrlRejectionReason",
]
