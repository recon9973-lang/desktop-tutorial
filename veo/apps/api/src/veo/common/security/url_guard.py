"""The decision of whether VEO may fetch a URL.

VEO takes URLs from anonymous callers and fetches them from inside our network. That
makes this module the blast door between the public internet and everything reachable
from a VEO worker: the cloud metadata endpoint, the database, Redis, the internal
admin surfaces. It is deliberately paranoid and it defaults to deny.

What it checks, in order, stopping at the first failure:

1. Scheme is ``http`` or ``https``. Nothing else — no ``file:``, ``gopher:``, ``data:``.
2. No userinfo. ``http://trusted.example@127.0.0.1/`` is the oldest trick in the book.
3. Port is on the allowlist (80/443 by default).
4. Host is not on the never-fetch name list (``localhost``, ``*.internal``, …).
5. Host is not a legacy/obfuscated IP spelling (``2130706433``, ``0177.0.0.1``, …).
6. If the host is an IP literal, that address is in public space.
7. Otherwise the host is resolved and **every** returned address — A *and* AAAA — is in
   public space. One bad answer rejects the whole URL.

DNS rebinding
-------------
Steps 6 and 7 are worthless on their own. An attacker who controls a name can answer
the guard's lookup with a public address and the *connection's* lookup with
``169.254.169.254`` a moment later: TOCTOU over DNS. That is why an allowed decision
carries :attr:`UrlDecision.resolved_ip`.

    **The caller must connect to** ``decision.resolved_ip`` **and must not let the HTTP
    client resolve the hostname again.**

Concretely, with httpx that means a transport whose socket connects to the pinned
address while ``Host`` and TLS SNI/verification still use ``decision.host``. Validating
here and then handing the raw URL to ``httpx.get()`` re-opens the exact hole this module
exists to close. This module cannot enforce that — only the HTTP client layer can.

Redirects
---------
Every hop is a fresh, untrusted URL, so :meth:`UrlGuard.validate_redirect` re-runs the
whole pipeline for each one and the hop budget is enforced by us, not by the HTTP
client's own ``follow_redirects``. A chain that starts public and ends on
``10.0.0.5`` is rejected at the hop that turns bad.

Information disclosure
----------------------
Rejection reasons are specific enough to debug but never name an address: a rejected
decision carries **no** resolved IPs at all, by construction rather than by filtering.
The Korean messages are safe to render to an anonymous caller.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Protocol

from veo.common.urls import HostForm, UrlNormalizationError, normalize_url, resolve_reference
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError

__all__ = [
    "DEFAULT_DENIED_HOST_NAMES",
    "DEFAULT_DENIED_HOST_SUFFIXES",
    "DEFAULT_POLICY",
    "HostResolutionError",
    "HostResolver",
    "IpBlockCategory",
    "UrlDecision",
    "UrlGuard",
    "UrlGuardPolicy",
    "UrlRejectedError",
    "UrlRejectionReason",
    "classify_ip",
    "system_resolver",
]


class UrlRejectionReason(StrEnum):
    """Why a URL was refused. Machine-readable, safe to log, safe to return."""

    MALFORMED_URL = "MALFORMED_URL"
    SCHEME_NOT_ALLOWED = "SCHEME_NOT_ALLOWED"
    CREDENTIALS_IN_URL = "CREDENTIALS_IN_URL"
    MISSING_HOST = "MISSING_HOST"
    PORT_NOT_ALLOWED = "PORT_NOT_ALLOWED"
    HOST_NOT_ALLOWED = "HOST_NOT_ALLOWED"
    OBFUSCATED_IP_LITERAL = "OBFUSCATED_IP_LITERAL"
    BLOCKED_IP_RANGE = "BLOCKED_IP_RANGE"
    DNS_RESOLUTION_FAILED = "DNS_RESOLUTION_FAILED"
    DNS_NO_ADDRESSES = "DNS_NO_ADDRESSES"
    TOO_MANY_REDIRECTS = "TOO_MANY_REDIRECTS"


class IpBlockCategory(StrEnum):
    """Which non-public range an address belongs to.

    Internal only — it is useful in a server-side log and dangerous in a response, so it
    never reaches :class:`UrlDecision`.
    """

    LOOPBACK = "LOOPBACK"
    PRIVATE = "PRIVATE"
    LINK_LOCAL = "LINK_LOCAL"
    CLOUD_METADATA = "CLOUD_METADATA"
    CGNAT = "CGNAT"
    MULTICAST = "MULTICAST"
    BROADCAST = "BROADCAST"
    UNSPECIFIED = "UNSPECIFIED"
    RESERVED = "RESERVED"
    UNIQUE_LOCAL = "UNIQUE_LOCAL"
    IPV4_MAPPED = "IPV4_MAPPED"
    NAT64 = "NAT64"


_MESSAGES: dict[UrlRejectionReason, str] = {
    UrlRejectionReason.MALFORMED_URL: "주소 형식이 올바르지 않습니다. 주소를 다시 확인해 주세요.",
    UrlRejectionReason.SCHEME_NOT_ALLOWED: "http 또는 https 주소만 분석할 수 있습니다.",
    UrlRejectionReason.CREDENTIALS_IN_URL: (
        "아이디·비밀번호가 포함된 주소는 분석할 수 없습니다. 계정 정보를 빼고 다시 입력해 주세요."
    ),
    UrlRejectionReason.MISSING_HOST: "주소에 도메인이 없습니다.",
    UrlRejectionReason.PORT_NOT_ALLOWED: "허용되지 않은 포트가 지정된 주소입니다.",
    UrlRejectionReason.HOST_NOT_ALLOWED: "분석할 수 없는 도메인입니다.",
    UrlRejectionReason.OBFUSCATED_IP_LITERAL: "비정상적으로 표기된 IP 주소는 분석할 수 없습니다.",
    UrlRejectionReason.BLOCKED_IP_RANGE: (
        "공개 인터넷에서 접근할 수 없는 주소입니다."
    ),
    UrlRejectionReason.DNS_RESOLUTION_FAILED: "도메인 주소를 확인할 수 없습니다.",
    UrlRejectionReason.DNS_NO_ADDRESSES: "도메인에 연결할 수 있는 주소가 없습니다.",
    UrlRejectionReason.TOO_MANY_REDIRECTS: "리디렉션이 너무 많아 분석을 중단했습니다.",
}

_SCHEME_PREFIX_RE = re.compile(r"([A-Za-z][A-Za-z0-9+.\-]*):")

_NORMALIZATION_REASONS: dict[str, UrlRejectionReason] = {
    "MALFORMED_URL": UrlRejectionReason.MALFORMED_URL,
    "ILLEGAL_CHARACTER": UrlRejectionReason.MALFORMED_URL,
    "ILLEGAL_HOST": UrlRejectionReason.MALFORMED_URL,
    "ILLEGAL_ESCAPE": UrlRejectionReason.MALFORMED_URL,
    "INVALID_PORT": UrlRejectionReason.MALFORMED_URL,
    "CREDENTIALS_IN_URL": UrlRejectionReason.CREDENTIALS_IN_URL,
}


# Order matters: the most specific range must come first, because the first match wins.
_BLOCKED_V4: tuple[tuple[IPv4Network, IpBlockCategory], ...] = tuple(
    (IPv4Network(cidr), category)
    for cidr, category in (
        ("169.254.169.254/32", IpBlockCategory.CLOUD_METADATA),
        ("127.0.0.0/8", IpBlockCategory.LOOPBACK),
        ("10.0.0.0/8", IpBlockCategory.PRIVATE),
        ("172.16.0.0/12", IpBlockCategory.PRIVATE),
        ("192.168.0.0/16", IpBlockCategory.PRIVATE),
        ("169.254.0.0/16", IpBlockCategory.LINK_LOCAL),
        ("100.64.0.0/10", IpBlockCategory.CGNAT),
        ("255.255.255.255/32", IpBlockCategory.BROADCAST),
        ("224.0.0.0/4", IpBlockCategory.MULTICAST),
        ("0.0.0.0/8", IpBlockCategory.UNSPECIFIED),
        ("192.0.0.0/24", IpBlockCategory.RESERVED),
        ("192.0.2.0/24", IpBlockCategory.RESERVED),
        ("192.88.99.0/24", IpBlockCategory.RESERVED),
        ("198.18.0.0/15", IpBlockCategory.RESERVED),
        ("198.51.100.0/24", IpBlockCategory.RESERVED),
        ("203.0.113.0/24", IpBlockCategory.RESERVED),
        ("240.0.0.0/4", IpBlockCategory.RESERVED),
    )
)

_BLOCKED_V6: tuple[tuple[IPv6Network, IpBlockCategory], ...] = tuple(
    (IPv6Network(cidr), category)
    for cidr, category in (
        ("::/128", IpBlockCategory.UNSPECIFIED),
        ("::1/128", IpBlockCategory.LOOPBACK),
        ("::ffff:0:0/96", IpBlockCategory.IPV4_MAPPED),
        ("64:ff9b::/96", IpBlockCategory.NAT64),
        ("64:ff9b:1::/48", IpBlockCategory.NAT64),
        ("::/96", IpBlockCategory.IPV4_MAPPED),
        ("100::/64", IpBlockCategory.RESERVED),
        ("2001::/23", IpBlockCategory.RESERVED),
        ("2001:db8::/32", IpBlockCategory.RESERVED),
        ("2002::/16", IpBlockCategory.RESERVED),
        ("fc00::/7", IpBlockCategory.UNIQUE_LOCAL),
        ("fe80::/10", IpBlockCategory.LINK_LOCAL),
        ("ff00::/8", IpBlockCategory.MULTICAST),
    )
)


def classify_ip(address: IPv4Address | IPv6Address) -> IpBlockCategory | None:
    """Return the blocked range ``address`` falls in, or ``None`` if it is public.

    IPv4-mapped (``::ffff:0:0/96``) and NAT64 (``64:ff9b::/96``) addresses are rejected
    whatever they wrap, including a public IPv4. Both are ways of writing an IPv4
    destination that a v6-aware stack will happily dial, and neither has any business
    appearing in a URL a customer typed. Unwrapping and re-checking the embedded address
    would still leave the mapped form as a second spelling for every future range we
    add, so we cut the whole class off.

    Anything not caught by the explicit tables but reported non-global by
    :mod:`ipaddress` is rejected too — that is the default-deny backstop for ranges IANA
    allocates after this file was written.
    """
    if isinstance(address, IPv6Address):
        for network6, category in _BLOCKED_V6:
            if address in network6:
                return category
    else:
        for network4, category in _BLOCKED_V4:
            if address in network4:
                return category
    if not address.is_global:
        return IpBlockCategory.RESERVED
    return None


class HostResolutionError(Exception):
    """A hostname could not be resolved. Always fatal — the guard never guesses."""


class HostResolver(Protocol):
    """Injected so tests never touch the network and production can pin a DNS client."""

    def __call__(self, host: str) -> Sequence[str]:
        """Return every address for ``host`` (A and AAAA) or raise."""


def system_resolver(host: str) -> list[str]:
    """Resolve via the operating system, returning both families in answer order."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise HostResolutionError(str(exc)) from exc
    seen: dict[str, None] = {}
    for info in infos:
        seen.setdefault(str(info[4][0]), None)
    return list(seen)


DEFAULT_DENIED_HOST_NAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "ip6-localhost",
        "ip6-loopback",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)

# RFC 6761/6762 special-use names plus the suffixes cloud and home networks squat on.
DEFAULT_DENIED_HOST_SUFFIXES: tuple[str, ...] = (
    ".localhost",
    ".local",
    ".localdomain",
    ".internal",
    ".intranet",
    ".home.arpa",
    ".in-addr.arpa",
    ".ip6.arpa",
    ".onion",
    ".invalid",
)


@dataclass(frozen=True, slots=True)
class UrlGuardPolicy:
    """Everything about the guard that a deployment is allowed to tune."""

    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    allowed_ports: frozenset[int] = frozenset({80, 443})
    max_redirects: int = 5
    denied_host_names: frozenset[str] = DEFAULT_DENIED_HOST_NAMES
    denied_host_suffixes: tuple[str, ...] = DEFAULT_DENIED_HOST_SUFFIXES
    allowed_host_suffixes: tuple[str, ...] | None = None
    """When set, only hosts ending in one of these suffixes may be fetched."""


DEFAULT_POLICY = UrlGuardPolicy()


@dataclass(frozen=True, slots=True)
class UrlDecision:
    """The result of a guard check. Frozen — a decision is a fact, not a scratchpad."""

    allowed: bool
    reason: UrlRejectionReason | None = None
    message_ko: str = ""
    url: str | None = None
    """Canonical form of what was checked, when it could be parsed at all."""
    host: str | None = None
    port: int | None = None
    resolved_ip: str | None = None
    """The address the caller **must** connect to. ``None`` on every rejection.

    Re-resolving the hostname at connection time re-opens the DNS-rebinding hole this
    decision exists to close. See the module docstring.
    """
    resolved_ips: tuple[str, ...] = ()
    """Every address that passed validation. Empty on every rejection, so a rejected
    decision can be serialised without leaking internal network topology."""
    hop: int = 0
    """0 for the original URL, 1 for the first redirect, and so on."""

    @property
    def error_code(self) -> ErrorCode | None:
        return ErrorCode.TARGET_URL_REJECTED if not self.allowed else None

    @staticmethod
    def message_for(reason: UrlRejectionReason) -> str:
        """The safe Korean message for ``reason``. Never contains an address or a secret."""
        return _MESSAGES[reason]

    @classmethod
    def reject(
        cls,
        reason: UrlRejectionReason,
        *,
        url: str | None = None,
        host: str | None = None,
        port: int | None = None,
        hop: int = 0,
    ) -> UrlDecision:
        return cls(
            allowed=False,
            reason=reason,
            message_ko=cls.message_for(reason),
            url=url,
            host=host,
            port=port,
            hop=hop,
        )

    @classmethod
    def allow(
        cls,
        *,
        url: str,
        host: str,
        port: int,
        resolved_ips: tuple[str, ...],
        hop: int = 0,
    ) -> UrlDecision:
        return cls(
            allowed=True,
            url=url,
            host=host,
            port=port,
            resolved_ip=resolved_ips[0],
            resolved_ips=resolved_ips,
            hop=hop,
        )

    def raise_if_rejected(self) -> None:
        if not self.allowed:
            raise UrlRejectedError(self)

    def as_api_error(self) -> ApiError:
        """Render the rejection as the platform-standard error envelope."""
        if self.allowed:
            raise ValueError("decision is allowed; there is no error to render")
        return ApiError.of(ErrorCode.TARGET_URL_REJECTED, self.message_ko)


class UrlRejectedError(Exception):
    """Raised by :meth:`UrlDecision.raise_if_rejected`."""

    def __init__(self, decision: UrlDecision) -> None:
        self.decision = decision
        super().__init__(f"{decision.reason}: {decision.url or '<unparseable>'}")


class UrlGuard:
    """Decides whether VEO may fetch a URL, and re-decides on every redirect hop."""

    def __init__(
        self,
        *,
        resolver: HostResolver | None = None,
        policy: UrlGuardPolicy = DEFAULT_POLICY,
    ) -> None:
        self._resolver: HostResolver = resolver if resolver is not None else system_resolver
        self._policy = policy

    @property
    def policy(self) -> UrlGuardPolicy:
        return self._policy

    def validate(self, raw_url: str, *, hop: int = 0) -> UrlDecision:
        """Run the full pipeline against ``raw_url``."""
        peeked = _peek_scheme(raw_url)
        if peeked is not None and peeked not in self._policy.allowed_schemes:
            # Refused before parsing: an exotic scheme should not get a parser at all.
            return UrlDecision.reject(UrlRejectionReason.SCHEME_NOT_ALLOWED, hop=hop)

        try:
            parsed = normalize_url(raw_url)
        except UrlNormalizationError as exc:
            reason = _NORMALIZATION_REASONS.get(exc.code, UrlRejectionReason.MALFORMED_URL)
            return UrlDecision.reject(reason, hop=hop)

        url = parsed.canonical
        if parsed.scheme not in self._policy.allowed_schemes:
            return UrlDecision.reject(UrlRejectionReason.SCHEME_NOT_ALLOWED, url=url, hop=hop)
        if not parsed.host:
            return UrlDecision.reject(UrlRejectionReason.MISSING_HOST, url=url, hop=hop)

        host = parsed.host
        port = parsed.port
        if port is None or port not in self._policy.allowed_ports:
            return UrlDecision.reject(
                UrlRejectionReason.PORT_NOT_ALLOWED, url=url, host=host, port=port, hop=hop
            )
        if self._is_denied_name(host):
            return UrlDecision.reject(
                UrlRejectionReason.HOST_NOT_ALLOWED, url=url, host=host, port=port, hop=hop
            )
        if parsed.host_form is HostForm.OBFUSCATED_IP:
            return UrlDecision.reject(
                UrlRejectionReason.OBFUSCATED_IP_LITERAL, url=url, host=host, port=port, hop=hop
            )

        if parsed.host_form is HostForm.IP_LITERAL:
            if parsed.ip is None or classify_ip(parsed.ip) is not None:
                return UrlDecision.reject(
                    UrlRejectionReason.BLOCKED_IP_RANGE, url=url, host=host, port=port, hop=hop
                )
            return UrlDecision.allow(
                url=url, host=host, port=port, resolved_ips=(parsed.ip.compressed,), hop=hop
            )

        return self._validate_by_resolution(url=url, host=host, port=port, hop=hop)

    def validate_redirect(self, *, from_url: str, location: str, hop: int) -> UrlDecision:
        """Validate the ``Location`` of a redirect. ``hop`` counts from 1.

        The target is re-validated from scratch: a redirect is an untrusted URL chosen
        by a server we have already decided not to trust.
        """
        if hop > self._policy.max_redirects:
            return UrlDecision.reject(UrlRejectionReason.TOO_MANY_REDIRECTS, hop=hop)
        try:
            target = resolve_reference(from_url, location)
        except UrlNormalizationError as exc:
            reason = _NORMALIZATION_REASONS.get(exc.code, UrlRejectionReason.MALFORMED_URL)
            return UrlDecision.reject(reason, hop=hop)
        return self.validate(target, hop=hop)

    def validate_chain(self, start_url: str, locations: Sequence[str]) -> UrlDecision:
        """Walk a whole redirect chain, returning the first rejection or the last allow."""
        decision = self.validate(start_url)
        if not decision.allowed:
            return decision
        for hop, location in enumerate(locations, start=1):
            current = decision.url
            if current is None:  # pragma: no cover - an allowed decision always has a url
                return UrlDecision.reject(UrlRejectionReason.MALFORMED_URL, hop=hop)
            decision = self.validate_redirect(from_url=current, location=location, hop=hop)
            if not decision.allowed:
                return decision
        return decision

    # -- internals ----------------------------------------------------------

    def _is_denied_name(self, host: str) -> bool:
        if host in self._policy.denied_host_names:
            return True
        if host.endswith(self._policy.denied_host_suffixes):
            return True
        allowed = self._policy.allowed_host_suffixes
        return allowed is not None and not host.endswith(allowed)

    def _validate_by_resolution(self, *, url: str, host: str, port: int, hop: int) -> UrlDecision:
        def refuse(reason: UrlRejectionReason) -> UrlDecision:
            return UrlDecision.reject(reason, url=url, host=host, port=port, hop=hop)

        try:
            answers = list(self._resolver(host))
        except Exception:
            # Deliberately broad: a resolver that raises anything at all — timeout,
            # NXDOMAIN, a bug — means we do not know where this name points, and
            # "do not know" is a rejection.
            return refuse(UrlRejectionReason.DNS_RESOLUTION_FAILED)

        if not answers:
            return refuse(UrlRejectionReason.DNS_NO_ADDRESSES)

        validated: list[str] = []
        for answer in answers:
            try:
                address = ipaddress.ip_address(answer)
            except ValueError:
                return refuse(UrlRejectionReason.DNS_RESOLUTION_FAILED)
            if classify_ip(address) is not None:
                # Every answer must pass. Checking only the first is the classic bug:
                # the attacker controls record order and the client may use any of them.
                return refuse(UrlRejectionReason.BLOCKED_IP_RANGE)
            validated.append(address.compressed)

        return UrlDecision.allow(
            url=url, host=host, port=port, resolved_ips=tuple(validated), hop=hop
        )


def _peek_scheme(raw_url: str) -> str | None:
    """Read the scheme without committing to a full parse."""
    match = _SCHEME_PREFIX_RE.match(raw_url.strip())
    return match.group(1).lower() if match else None
