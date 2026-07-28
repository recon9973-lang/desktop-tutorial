"""Replaying a public scan with no network at all.

The public surface is the only part of VEO that fetches a URL a stranger typed, so its
tests have to exercise the real :class:`SafeFetcher` — guard, pinned address, redirect
handling — rather than a stub that skips it. A ``httpx.MockTransport`` supplies the
bytes and a fake resolver supplies the address, and nothing leaves the process.

The resolver is the interesting knob: point it at ``127.0.0.1`` and the guard refuses
the URL exactly as it would in production, which is how the private-address tests work
without ever dialling anything.

:class:`RequestLog` is the other one. The amplification guarantee is a claim about
**how many requests VEO sends to a third party**, and the only way to assert that is to
count them at the transport, on the far side of every redirect and every robots.txt
fetch. A test that counted refusals instead would have passed against the version of
this package that could be made to deliver eighty requests to one victim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from veo.common.security.fetcher import SafeFetcher
from veo.common.security.url_guard import UrlGuard

#: A fixed instant, so a score computed in the service and the same score computed
#: directly from the engine cannot drift apart because a clock ticked between them.
FIXED_NOW = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

#: A globally routable address. The TEST-NET ranges (``203.0.113.0/24`` and friends) are
#: reserved, and the guard refuses them — correctly.
PUBLIC_IP = "93.184.216.34"

ROBOTS_TXT = "User-agent: *\nAllow: /\nSitemap: https://clinic.example/sitemap.xml\n"

CLINIC_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>서울온담의원 — 내과·건강검진</title>
<meta name="description" content="서울 강남구 내과 의원. 건강검진과 만성질환 관리를 진료합니다.">
<link rel="canonical" href="https://clinic.example/">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"MedicalClinic","name":"서울온담의원",
"url":"https://clinic.example/","telephone":"02-000-0000"}
</script>
</head>
<body>
<h1>서울온담의원</h1>
<p>내과 진료와 건강검진을 제공합니다. 평일 09:00-18:00 진료합니다.</p>
<h2>진료 안내</h2>
<p>예약은 전화로 받습니다.</p>
<a href="https://clinic.example/about">의원 소개</a>
<img src="/logo.png" alt="서울온담의원 로고">
</body>
</html>
"""


class ServiceClock:
    """A clock a test can move, so a TTL can be crossed without waiting a week."""

    def __init__(self, start: datetime = FIXED_NOW) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


class RequestLog:
    """Every request that reached the transport, counted by the host it was sent to."""

    def __init__(self) -> None:
        self.hosts: list[str] = []

    def record(self, host: str) -> None:
        self.hosts.append(host)

    def count(self, host: str) -> int:
        return sum(1 for item in self.hosts if item == host)

    @property
    def total(self) -> int:
        return len(self.hosts)


@dataclass(frozen=True, slots=True)
class Page:
    """One canned response, keyed by scheme, host and path."""

    body: bytes
    status: int = 200
    headers: Mapping[str, str] = field(
        default_factory=lambda: {"content-type": "text/html; charset=utf-8"}
    )

    def to_response(self) -> httpx.Response:
        return httpx.Response(self.status, headers=dict(self.headers), content=self.body)


def html_page(markup: str, *, status: int = 200) -> Page:
    return Page(body=markup.encode("utf-8"), status=status)


def text_page(text: str, *, status: int = 200) -> Page:
    return Page(
        body=text.encode("utf-8"),
        status=status,
        headers={"content-type": "text/plain; charset=utf-8"},
    )


def redirect_page(location: str) -> Page:
    return Page(body=b"", status=302, headers={"location": location})


def clinic_site() -> dict[str, Page]:
    """The one-page site every scan test uses."""
    return {
        "https://clinic.example/": html_page(CLINIC_HTML),
        "https://clinic.example/robots.txt": text_page(ROBOTS_TXT),
    }


def site_transport(
    pages: Mapping[str, Page] | None = None,
    *,
    log: RequestLog | None = None,
    serve_unknown_hosts: bool = False,
    redirect_suffix: tuple[str, str] | None = None,
) -> httpx.MockTransport:
    """A transport that answers from ``pages`` and records who it was asked to contact.

    ``serve_unknown_hosts`` makes every host answer with the same stock page, which is
    how a test scans many distinct hosts without listing them all. ``redirect_suffix``
    is ``(host_suffix, location)``: any host ending in the suffix answers ``302`` to the
    location — somebody who owns a domain owns its redirects, and that is the whole
    point of the laundering test.
    """
    known = dict(pages or {})

    def handler(request: httpx.Request) -> httpx.Response:
        # The fetcher dials the pinned IP and carries the real name in ``Host``, so the
        # lookup key has to be rebuilt from the header rather than from the URL host.
        host = request.headers.get("host") or request.url.host or ""
        if log is not None:
            log.record(host)

        if redirect_suffix is not None and host.endswith(redirect_suffix[0]):
            return redirect_page(redirect_suffix[1]).to_response()

        key = f"{request.url.scheme}://{host}{request.url.path}"
        page = known.get(key)
        if page is not None:
            return page.to_response()
        if serve_unknown_hosts:
            if request.url.path == "/robots.txt":
                return text_page(ROBOTS_TXT).to_response()
            return html_page(CLINIC_HTML).to_response()
        return Page(
            body=b"<!doctype html><html><body>not found</body></html>", status=404
        ).to_response()

    return httpx.MockTransport(handler)


def public_guard(resolves_to: str = PUBLIC_IP) -> UrlGuard:
    """A real guard with a fixed DNS answer, so no lookup ever leaves the process."""
    return UrlGuard(resolver=lambda host: [resolves_to])


def make_fetcher(
    pages: Mapping[str, Page],
    *,
    resolves_to: str = PUBLIC_IP,
) -> SafeFetcher:
    """A plain :class:`SafeFetcher` with no rate-limit accounting.

    Used only where a test needs a document from *outside* the service — notably the
    engine-equivalence test, which rebuilds the collection context by hand. Everything
    that goes through the service gets the budget-charging guard instead, which the
    service builds itself precisely so it cannot be left out.
    """
    return SafeFetcher(guard=public_guard(resolves_to), transport=site_transport(pages))


def payload_strings(value: object) -> list[str]:
    """Every string anywhere in a serialised payload, keys included.

    The leak assertions need to look at the whole tree, not at the fields somebody
    remembered to check.
    """
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            found.append(str(key))
            found.extend(payload_strings(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.extend(payload_strings(item))
    return found


__all__ = [
    "CLINIC_HTML",
    "FIXED_NOW",
    "PUBLIC_IP",
    "ROBOTS_TXT",
    "Page",
    "RequestLog",
    "ServiceClock",
    "clinic_site",
    "html_page",
    "make_fetcher",
    "payload_strings",
    "public_guard",
    "redirect_page",
    "site_transport",
    "text_page",
]
