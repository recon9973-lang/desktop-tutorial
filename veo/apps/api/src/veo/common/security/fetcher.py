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
import time
import zlib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from veo.common.security.limits import (
    FetchLimits,
    ResponseBudget,
    ResponseTooLargeError,
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
DEFAULT_USER_AGENT = "VEO-Bot/1.0 (+https://veo.seokorea.org/bot; SEO/GEO diagnostics by VENOM)"

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

    @property
    def was_redirected(self) -> bool:
        return len(self.hops) > 1

    def text(self, fallback: str = "utf-8") -> str:
        """Decode the body, never raising — a mis-declared charset is a finding, not a crash."""
        return self.body.decode(self.charset or fallback, errors="replace")


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
                            request_headers={"user-agent": self._user_agent},
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
            timeout=httpx.Timeout(self._limits.max_total_seconds),
            follow_redirects=False,  # never: following one means resolving one
            cookies=None,
            headers={
                "user-agent": self._user_agent,
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
        """Stream the body under budget, refusing anything oversized or bomb-shaped."""
        budget = ResponseBudget(self._limits)
        budget.check_content_type(response.headers.get("content-type"))
        budget.check_declared_length(response.headers.get("content-length"))

        encoding = (response.headers.get("content-encoding") or "").lower()
        decoder = _decoder_for(encoding)

        chunks: list[bytes] = []
        try:
            for chunk in response.iter_raw():
                budget.check_deadline()
                budget.add_wire_bytes(len(chunk))
                if decoder is None:
                    budget.add_decompressed_bytes(len(chunk))
                    chunks.append(chunk)
                    continue
                expanded = decoder.decompress(chunk, self._limits.max_decompressed_bytes)
                budget.add_decompressed_bytes(len(expanded))
                chunks.append(expanded)
                if decoder.unconsumed_tail:
                    # More output was available than the ceiling allows: that is the bomb.
                    raise ResponseTooLargeError("decompressed body over budget")
        except httpx.StreamConsumed:
            # The body was already materialised before we could stream it. Real network
            # transports never do this; test doubles built from a bytes literal always
            # do. The budget still applies — it just charges the whole body at once
            # instead of refusing it partway through.
            return self._charge_materialised_body(response, budget), False

        return b"".join(chunks), False

    def _charge_materialised_body(
        self, response: httpx.Response, budget: ResponseBudget
    ) -> bytes:
        """Apply the budget to a body that is already in memory."""
        body = response.content  # httpx has decoded any content-encoding by this point
        budget.add_wire_bytes(len(body))
        budget.add_decompressed_bytes(len(body))
        return body


def _decoder_for(encoding: str) -> zlib._Decompress | None:
    if encoding == "gzip":
        return zlib.decompressobj(16 + zlib.MAX_WBITS)
    if encoding == "deflate":
        return zlib.decompressobj()
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
