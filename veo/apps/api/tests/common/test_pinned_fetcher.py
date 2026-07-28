"""The fetcher that actually honours the SSRF decision.

`UrlGuard` decides which address is safe. That decision is worthless if the HTTP client
then resolves the hostname again and connects wherever DNS points the second time — the
classic rebinding window. These tests hold the line: the connection goes to the address
that was validated, on every hop, or it does not happen.
"""

from __future__ import annotations

import gzip
import hashlib

import httpx
import pytest

from veo.common.security.fetcher import (
    FetchedDocument,
    FetchError,
    RedirectLimitExceededError,
    SafeFetcher,
)
from veo.common.security.limits import (
    ContentTypeNotAllowedError,
    DecompressionLimitError,
    FetchLimits,
    ResponseTooLargeError,
)
from veo.common.security.url_guard import UrlGuard, UrlGuardPolicy, UrlRejectedError

PUBLIC_IP = "93.184.216.34"
# 203.0.113.0/24 is RFC 5737 documentation space and the guard blocks it, so the
# second host needs a genuinely routable address.
OTHER_PUBLIC_IP = "8.8.8.8"
PRIVATE_IP = "10.0.0.5"


class RecordingTransport(httpx.BaseTransport):
    """Captures exactly what the fetcher asked the network for."""

    def __init__(self, responses: list[httpx.Response] | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self._responses = responses or []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return httpx.Response(200, content=b"<html>ok</html>",
                              headers={"content-type": "text/html"})

    @property
    def connected_hosts(self) -> list[str]:
        """The host each request was actually addressed to — an IP when pinned."""
        return [r.url.host for r in self.requests]

    @property
    def host_headers(self) -> list[str]:
        return [r.headers.get("host", "") for r in self.requests]

    @property
    def sni_names(self) -> list[str | None]:
        return [r.extensions.get("sni_hostname") for r in self.requests]


def guard_with(mapping: dict[str, list[str]]) -> UrlGuard:
    def resolver(host: str) -> list[str]:
        try:
            return mapping[host]
        except KeyError:
            raise LookupError(host) from None

    return UrlGuard(resolver=resolver)


def fetcher_for(
    mapping: dict[str, list[str]],
    transport: httpx.BaseTransport,
    *,
    limits: FetchLimits | None = None,
    policy: UrlGuardPolicy | None = None,
) -> SafeFetcher:
    guard = (
        UrlGuard(resolver=lambda h: mapping[h], policy=policy)
        if policy is not None
        else guard_with(mapping)
    )
    return SafeFetcher(
        guard=guard,
        limits=limits or FetchLimits(),
        transport=transport,
    )


def html(body: str = "<html><body>hi</body></html>") -> httpx.Response:
    return httpx.Response(200, content=body.encode(), headers={"content-type": "text/html"})


# --------------------------------------------------------------------------- #
# The pin itself
# --------------------------------------------------------------------------- #


def test_connects_to_the_validated_address_not_the_hostname() -> None:
    transport = RecordingTransport([html()])
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    fetcher.fetch("https://example.com/page")

    assert transport.connected_hosts == [PUBLIC_IP], (
        "the request must be addressed to the validated IP, not re-resolved by the client"
    )


def test_host_header_and_sni_still_carry_the_real_hostname() -> None:
    """Pinning must not break virtual hosting or certificate verification."""
    transport = RecordingTransport([html()])
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    fetcher.fetch("https://example.com/page")

    assert transport.host_headers == ["example.com"]
    assert transport.sni_names == ["example.com"]


def test_dns_rebinding_between_validation_and_connect_cannot_take_effect() -> None:
    """The hostname resolves public, then private. The pin must win.

    This is the whole reason the fetcher exists. A resolver that flips on the second
    lookup models an attacker with a short-TTL record.
    """
    lookups: list[str] = []
    answers = iter([[PUBLIC_IP], [PRIVATE_IP], [PRIVATE_IP]])

    def flipping_resolver(host: str) -> list[str]:
        lookups.append(host)
        return next(answers)

    transport = RecordingTransport([html()])
    fetcher = SafeFetcher(
        guard=UrlGuard(resolver=flipping_resolver),
        limits=FetchLimits(),
        transport=transport,
    )

    fetcher.fetch("https://example.com/")

    assert transport.connected_hosts == [PUBLIC_IP]
    assert len(lookups) == 1, "the host must be resolved once, by the guard, and never again"


def test_a_url_the_guard_rejects_is_never_dialled() -> None:
    transport = RecordingTransport()
    fetcher = fetcher_for({"internal.example": [PRIVATE_IP]}, transport)

    with pytest.raises(UrlRejectedError):
        fetcher.fetch("https://internal.example/")

    assert transport.requests == [], "a rejected URL must produce no network traffic at all"


def test_credentials_in_the_url_are_refused() -> None:
    transport = RecordingTransport()
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    with pytest.raises(UrlRejectedError):
        fetcher.fetch("https://user:pass@example.com/")
    assert transport.requests == []


# --------------------------------------------------------------------------- #
# Redirects — re-validated, never auto-followed
# --------------------------------------------------------------------------- #


def redirect_to(location: str, status: int = 302) -> httpx.Response:
    return httpx.Response(status, headers={"location": location})


def test_each_redirect_hop_is_revalidated_and_repinned() -> None:
    transport = RecordingTransport([redirect_to("https://second.example/next"), html()])
    fetcher = fetcher_for(
        {"first.example": [PUBLIC_IP], "second.example": [OTHER_PUBLIC_IP]}, transport
    )

    document = fetcher.fetch("https://first.example/")

    assert transport.connected_hosts == [PUBLIC_IP, OTHER_PUBLIC_IP]
    assert transport.host_headers == ["first.example", "second.example"]
    assert document.final_url == "https://second.example/next"
    assert len(document.hops) == 2


def test_a_redirect_into_private_space_is_refused() -> None:
    """The oldest SSRF trick: pass the guard, then bounce to 169.254.169.254."""
    transport = RecordingTransport([redirect_to("http://169.254.169.254/latest/meta-data/")])
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    with pytest.raises(UrlRejectedError):
        fetcher.fetch("https://example.com/")

    assert len(transport.requests) == 1, "the redirect target must not be dialled"


def test_a_redirect_to_a_rebinding_host_is_refused() -> None:
    transport = RecordingTransport([redirect_to("https://evil.example/")])
    fetcher = fetcher_for(
        {"example.com": [PUBLIC_IP], "evil.example": [PRIVATE_IP]}, transport
    )

    with pytest.raises(UrlRejectedError):
        fetcher.fetch("https://example.com/")
    assert len(transport.requests) == 1


def test_a_redirect_to_a_foreign_scheme_is_refused() -> None:
    transport = RecordingTransport([redirect_to("ftp://example.com/x")])
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    with pytest.raises(UrlRejectedError):
        fetcher.fetch("https://example.com/")


def test_too_many_redirects_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [redirect_to(f"https://example.com/{i}") for i in range(12)]
    transport = RecordingTransport(responses)
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    with pytest.raises(RedirectLimitExceededError):
        fetcher.fetch("https://example.com/start")

    assert len(transport.requests) <= UrlGuardPolicy().max_redirects + 1


def test_a_redirect_loop_terminates() -> None:
    transport = RecordingTransport(
        [redirect_to("https://example.com/b"), redirect_to("https://example.com/a")] * 6
    )
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    with pytest.raises(RedirectLimitExceededError):
        fetcher.fetch("https://example.com/a")


def test_no_cookie_survives_a_redirect_to_another_host() -> None:
    transport = RecordingTransport(
        [
            httpx.Response(
                302,
                headers={"location": "https://second.example/", "set-cookie": "s=secret"},
            ),
            html(),
        ]
    )
    fetcher = fetcher_for(
        {"first.example": [PUBLIC_IP], "second.example": [OTHER_PUBLIC_IP]}, transport
    )

    fetcher.fetch("https://first.example/")

    assert "cookie" not in transport.requests[1].headers, (
        "VEO crawls anonymously; a cookie must never be carried anywhere"
    )


# --------------------------------------------------------------------------- #
# Limits
# --------------------------------------------------------------------------- #


def test_an_oversized_body_is_refused() -> None:
    limits = FetchLimits(max_response_bytes=1024)
    transport = RecordingTransport(
        [httpx.Response(200, content=b"x" * 5000, headers={"content-type": "text/html"})]
    )
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport, limits=limits)

    with pytest.raises(ResponseTooLargeError):
        fetcher.fetch("https://example.com/")


def test_a_decompression_bomb_is_refused() -> None:
    payload = gzip.compress(b"0" * 5_000_000)
    limits = FetchLimits(max_response_bytes=10_000_000, max_decompressed_bytes=100_000)
    transport = RecordingTransport(
        [
            httpx.Response(
                200,
                content=payload,
                headers={"content-type": "text/html", "content-encoding": "gzip"},
            )
        ]
    )
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport, limits=limits)

    with pytest.raises((DecompressionLimitError, ResponseTooLargeError)):
        fetcher.fetch("https://example.com/")


def test_an_unexpected_content_type_is_refused() -> None:
    transport = RecordingTransport(
        [
            httpx.Response(
                200,
                content=b"MZ\x90\x00",
                headers={"content-type": "application/x-msdownload"},
            )
        ]
    )
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    with pytest.raises(ContentTypeNotAllowedError):
        fetcher.fetch("https://example.com/")


# --------------------------------------------------------------------------- #
# What the collectors receive
# --------------------------------------------------------------------------- #


def test_the_document_carries_everything_evidence_needs() -> None:
    body = "<html><body>안녕</body></html>"
    transport = RecordingTransport([html(body)])
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    document = fetcher.fetch("https://example.com/page?a=1")

    assert isinstance(document, FetchedDocument)
    assert document.requested_url.startswith("https://example.com/page")
    assert document.status == 200
    assert document.body == body.encode()
    assert document.content_hash == hashlib.sha256(body.encode()).hexdigest()
    assert document.content_type == "text/html"
    assert document.resolved_ips == (PUBLIC_IP,)
    assert document.fetched_at is not None
    assert document.elapsed_ms >= 0


def test_the_same_bytes_always_hash_the_same() -> None:
    """Evidence has to be comparable across runs, so the hash must be stable."""
    documents = []
    for _ in range(2):
        transport = RecordingTransport([html()])
        documents.append(
            fetcher_for({"example.com": [PUBLIC_IP]}, transport).fetch("https://example.com/")
        )
    assert documents[0].content_hash == documents[1].content_hash


def test_sensitive_response_headers_are_redacted_in_the_record() -> None:
    transport = RecordingTransport(
        [
            httpx.Response(
                200,
                content=b"<html></html>",
                headers={
                    "content-type": "text/html",
                    "set-cookie": "session=super-secret-value",
                    "authorization": "Bearer abc",
                },
            )
        ]
    )
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    document = fetcher.fetch("https://example.com/")
    serialized = str(document.headers)

    assert "super-secret-value" not in serialized
    assert "Bearer abc" not in serialized


def test_the_user_agent_identifies_veo() -> None:
    transport = RecordingTransport([html()])
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    fetcher.fetch("https://example.com/")

    agent = transport.requests[0].headers.get("user-agent", "")
    assert "VEO" in agent, "an anonymous crawler that hides its identity is not acceptable"


def test_a_non_2xx_status_is_returned_rather_than_raised() -> None:
    """A 404 is a finding for the SEO engine, not a fetch failure."""
    transport = RecordingTransport(
        [httpx.Response(404, content=b"nope", headers={"content-type": "text/html"})]
    )
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, transport)

    document = fetcher.fetch("https://example.com/missing")
    assert document.status == 404


def test_hops_record_the_address_used_for_each_leg() -> None:
    transport = RecordingTransport([redirect_to("https://second.example/"), html()])
    fetcher = fetcher_for(
        {"first.example": [PUBLIC_IP], "second.example": [OTHER_PUBLIC_IP]}, transport
    )

    document = fetcher.fetch("https://first.example/")

    assert [hop.resolved_ip for hop in document.hops] == [PUBLIC_IP, OTHER_PUBLIC_IP]
    assert [hop.status for hop in document.hops] == [302, 200]


# --------------------------------------------------------------------------- #
# Transport failures stay inside the fetcher's own error type
# --------------------------------------------------------------------------- #


def failing_transport(error: httpx.HTTPError) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("connection refused"),
        httpx.ConnectTimeout("timed out connecting"),
        httpx.ReadError("connection reset"),
    ],
    ids=["refused", "connect-timeout", "reset"],
)
def test_a_site_that_will_not_answer_raises_the_fetchers_own_error(
    error: httpx.HTTPError,
) -> None:
    """An unreachable site is a fetch failure, not an unhandled exception.

    This regressed once and was invisible: ``httpx.Client.stream`` sends nothing when it
    is called and everything when it is *entered*, so a ``try`` around the call caught
    none of the errors it named. Every connect failure escaped as a raw ``httpx``
    exception — meaning a clinic whose site was simply down produced a 500 rather than
    "the address did not respond".
    """
    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, failing_transport(error))

    with pytest.raises(FetchError):
        fetcher.fetch("https://example.com/")


def test_a_transport_failure_while_the_body_arrives_is_contained_too() -> None:
    """The headers can arrive and the connection still die mid-body."""

    def handler(request: httpx.Request) -> httpx.Response:
        def die() -> bytes:
            raise httpx.ReadError("connection reset while streaming")

        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=(chunk for chunk in [b"<html>", die()]),
        )

    fetcher = fetcher_for({"example.com": [PUBLIC_IP]}, httpx.MockTransport(handler))

    with pytest.raises(FetchError):
        fetcher.fetch("https://example.com/")
