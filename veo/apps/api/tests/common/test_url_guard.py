"""Adversarial corpus for :mod:`veo.common.security.url_guard`.

VEO fetches URLs that anonymous callers hand it. Every case below is a real SSRF
technique; the table is meant to grow whenever a new one is published. The single
invariant that matters more than any individual reason code: **nothing in this file
that should be blocked is ever allowed.**
"""

from __future__ import annotations

import ipaddress

import pytest
from fakes import PUBLIC_V4, FakeResolver

from veo.common.security.url_guard import (
    IpBlockCategory,
    UrlDecision,
    UrlGuard,
    UrlGuardPolicy,
    UrlRejectedError,
    UrlRejectionReason,
    classify_ip,
)
from veo.contracts.enums import ErrorCode

R = UrlRejectionReason


# ---------------------------------------------------------------------------
# 1. scheme allowlist
# ---------------------------------------------------------------------------

SCHEME_CASES = [
    ("file", "file:///etc/passwd"),
    ("file with host", "file://localhost/etc/passwd"),
    ("ftp", "ftp://example.com/x"),
    ("gopher", "gopher://example.com:70/_x"),
    ("gopher smuggling", "gopher://127.0.0.1:6379/_SET%20a%20b"),
    ("data", "data:text/html;base64,PHNjcmlwdD4="),
    ("javascript", "javascript:alert(1)"),
    ("javascript mixed case", "JaVaScRiPt:alert(1)"),
    ("blob", "blob:http://example.com/uuid"),
    ("dict", "dict://127.0.0.1:11211/stat"),
    ("ldap", "ldap://127.0.0.1:389/x"),
    ("jar", "jar:http://example.com/a.jar!/b"),
    ("ws", "ws://example.com/socket"),
    ("wss", "wss://example.com/socket"),
    ("netdoc", "netdoc:///etc/passwd"),
    ("no scheme", "example.com/path"),
    ("scheme only", "http:"),
]


@pytest.mark.parametrize(
    "raw", [pytest.param(raw, id=label) for label, raw in SCHEME_CASES]
)
def test_scheme_allowlist(guard: UrlGuard, raw: str) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is False
    assert decision.reason in {R.SCHEME_NOT_ALLOWED, R.MISSING_HOST}


@pytest.mark.parametrize(
    "raw", ["http://example.com/", "HTTP://example.com/", "HtTp://example.com/"]
)
def test_mixed_case_http_is_allowed(guard: UrlGuard, raw: str) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is True
    assert decision.url == "http://example.com/"


def test_https_is_allowed(guard: UrlGuard) -> None:
    assert guard.validate("HTTPS://Example.com/a").allowed is True


# ---------------------------------------------------------------------------
# 2. credential-bearing URLs
# ---------------------------------------------------------------------------

CREDENTIAL_CASES = [
    ("user and password", "http://user:pass@example.com/"),
    ("user only", "http://user@example.com/"),
    ("empty userinfo", "http://@example.com/"),
    ("at confusion", "http://example.com@127.0.0.1/"),
    ("double at confusion", "http://user:pass@example.com@127.0.0.1/"),
    ("at confusion with port", "http://example.com:80@127.0.0.1:80/"),
    ("colon confusion", "http://example.com:@127.0.0.1/"),
    ("credentials on https", "https://admin:hunter2@example.com/"),
    ("backslash before at", "http://example.com\\@127.0.0.1/"),
]


@pytest.mark.parametrize(
    "raw", [pytest.param(raw, id=label) for label, raw in CREDENTIAL_CASES]
)
def test_credentials_are_rejected(guard: UrlGuard, raw: str) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is False
    assert decision.reason is R.CREDENTIALS_IN_URL


def test_credential_rejection_does_not_echo_the_secret(guard: UrlGuard) -> None:
    decision = guard.validate("https://admin:hunter2@example.com/")
    assert "hunter2" not in decision.message_ko
    assert "hunter2" not in (decision.url or "")
    assert "hunter2" not in repr(decision)


# ---------------------------------------------------------------------------
# 3. port allowlist
# ---------------------------------------------------------------------------

BLOCKED_PORTS = [22, 23, 25, 110, 135, 389, 445, 1433, 3306, 5432, 6379, 8080, 9200, 11211, 27017]


@pytest.mark.parametrize("port", BLOCKED_PORTS)
def test_port_allowlist(guard: UrlGuard, port: int) -> None:
    decision = guard.validate(f"http://example.com:{port}/")
    assert decision.allowed is False
    assert decision.reason is R.PORT_NOT_ALLOWED


@pytest.mark.parametrize("url", ["http://example.com:80/", "https://example.com:443/"])
def test_default_ports_are_allowed(guard: UrlGuard, url: str) -> None:
    assert guard.validate(url).allowed is True


def test_https_on_port_80_is_allowed(guard: UrlGuard) -> None:
    assert guard.validate("https://example.com:80/").allowed is True


def test_port_allowlist_is_configurable(permissive_port_guard: UrlGuard) -> None:
    assert permissive_port_guard.validate("http://example.com:8080/").allowed is True
    assert permissive_port_guard.validate("http://example.com:6379/").allowed is False


def test_port_check_happens_before_dns(resolver: FakeResolver) -> None:
    """A blocked port must not even cost us a lookup — and must not confirm the host."""
    guard = UrlGuard(resolver=resolver)
    assert guard.validate("http://example.com:6379/").reason is R.PORT_NOT_ALLOWED
    assert resolver.calls == []


# ---------------------------------------------------------------------------
# 4 + 5. blocked IP ranges, reached directly as literals
# ---------------------------------------------------------------------------

BLOCKED_LITERALS = [
    ("ipv4 loopback", "http://127.0.0.1/", IpBlockCategory.LOOPBACK),
    ("ipv4 loopback high", "http://127.255.255.254/", IpBlockCategory.LOOPBACK),
    ("rfc1918 10", "http://10.0.0.1/", IpBlockCategory.PRIVATE),
    ("rfc1918 172", "http://172.16.0.1/", IpBlockCategory.PRIVATE),
    ("rfc1918 172 top", "http://172.31.255.255/", IpBlockCategory.PRIVATE),
    ("rfc1918 192", "http://192.168.1.1/", IpBlockCategory.PRIVATE),
    ("link local", "http://169.254.1.1/", IpBlockCategory.LINK_LOCAL),
    ("cloud metadata", "http://169.254.169.254/latest/meta-data/", IpBlockCategory.CLOUD_METADATA),
    ("alibaba metadata", "http://100.100.100.200/latest/", IpBlockCategory.CGNAT),
    ("cgnat", "http://100.64.0.1/", IpBlockCategory.CGNAT),
    ("cgnat top", "http://100.127.255.255/", IpBlockCategory.CGNAT),
    ("multicast", "http://224.0.0.1/", IpBlockCategory.MULTICAST),
    ("reserved 240", "http://240.0.0.1/", IpBlockCategory.RESERVED),
    ("benchmark 198.18", "http://198.18.0.1/", IpBlockCategory.RESERVED),
    ("shared 192.0.0", "http://192.0.0.1/", IpBlockCategory.RESERVED),
    ("unspecified", "http://0.0.0.0/", IpBlockCategory.UNSPECIFIED),
    ("this network", "http://0.1.2.3/", IpBlockCategory.UNSPECIFIED),
    ("broadcast", "http://255.255.255.255/", IpBlockCategory.BROADCAST),
    ("ipv6 loopback", "http://[::1]/", IpBlockCategory.LOOPBACK),
    ("ipv6 unspecified", "http://[::]/", IpBlockCategory.UNSPECIFIED),
    ("ipv6 ula fc00", "http://[fc00::1]/", IpBlockCategory.UNIQUE_LOCAL),
    ("ipv6 ula fd00", "http://[fd12:3456:789a::1]/", IpBlockCategory.UNIQUE_LOCAL),
    ("ipv6 link local", "http://[fe80::1]/", IpBlockCategory.LINK_LOCAL),
    ("ipv6 multicast", "http://[ff02::1]/", IpBlockCategory.MULTICAST),
    ("ipv6 mapped loopback", "http://[::ffff:127.0.0.1]/", IpBlockCategory.IPV4_MAPPED),
    ("ipv6 mapped public", "http://[::ffff:93.184.216.34]/", IpBlockCategory.IPV4_MAPPED),
    ("ipv6 mapped hex", "http://[::ffff:7f00:1]/", IpBlockCategory.IPV4_MAPPED),
    ("nat64 loopback", "http://[64:ff9b::7f00:1]/", IpBlockCategory.NAT64),
    ("nat64 public", "http://[64:ff9b::5db8:d822]/", IpBlockCategory.NAT64),
    ("ipv6 documentation", "http://[2001:db8::1]/", IpBlockCategory.RESERVED),
    ("teredo", "http://[2001::1]/", IpBlockCategory.RESERVED),
    ("ipv6 discard", "http://[100::1]/", IpBlockCategory.RESERVED),
]


@pytest.mark.parametrize(
    ("raw", "category"),
    [pytest.param(raw, cat, id=label) for label, raw, cat in BLOCKED_LITERALS],
)
def test_blocked_ip_literals(guard: UrlGuard, raw: str, category: IpBlockCategory) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE


@pytest.mark.parametrize(
    ("raw", "category"),
    [pytest.param(raw, cat, id=label) for label, raw, cat in BLOCKED_LITERALS],
)
def test_ip_block_categories(raw: str, category: IpBlockCategory) -> None:
    """The category is internal-only, but it must be right so operators can triage."""
    host = raw.split("//", 1)[1].split("/", 1)[0].strip("[]")
    assert classify_ip(ipaddress.ip_address(host)) is category


@pytest.mark.parametrize("address", ["93.184.216.34", "8.8.8.8", "2606:2800:220:1::1"])
def test_public_addresses_are_not_blocked(address: str) -> None:
    assert classify_ip(ipaddress.ip_address(address)) is None


def test_public_ipv4_literal_is_allowed(guard: UrlGuard, resolver: FakeResolver) -> None:
    decision = guard.validate(f"http://{PUBLIC_V4}/x")
    assert decision.allowed is True
    assert decision.resolved_ip == PUBLIC_V4
    assert resolver.calls == [], "an IP literal must not trigger a lookup"


def test_public_ipv6_literal_is_allowed(guard: UrlGuard) -> None:
    decision = guard.validate("http://[2606:2800:220:1::1]/")
    assert decision.allowed is True
    assert decision.resolved_ip == "2606:2800:220:1::1"


# ---------------------------------------------------------------------------
# 6. obfuscated address literals
# ---------------------------------------------------------------------------

OBFUSCATED_CASES = [
    ("decimal loopback", "http://2130706433/"),
    ("decimal metadata", "http://2852039166/"),
    ("octal loopback", "http://0177.0.0.1/"),
    ("octal flat", "http://017700000001/"),
    ("hex dotted", "http://0x7f.0x0.0x0.0x1/"),
    ("hex flat", "http://0x7f000001/"),
    ("hex uppercase", "http://0X7F000001/"),
    ("zero padded", "http://127.000.000.001/"),
    ("short form two part", "http://127.1/"),
    ("short form three part", "http://127.0.1/"),
    ("mixed radix", "http://0177.0.0.0x1/"),
    ("decimal private", "http://3232235777/"),
    ("obfuscated public host", "http://1572395042/"),
]


@pytest.mark.parametrize(
    "raw", [pytest.param(raw, id=label) for label, raw in OBFUSCATED_CASES]
)
def test_obfuscated_literals_are_rejected(
    guard: UrlGuard, raw: str, resolver: FakeResolver
) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is False
    assert decision.reason is R.OBFUSCATED_IP_LITERAL
    assert resolver.calls == [], "a legacy IP form must never be handed to DNS"


# ---------------------------------------------------------------------------
# whitespace, control characters, malformed input
# ---------------------------------------------------------------------------

MALFORMED_CASES = [
    ("empty", ""),
    ("blank", "   "),
    ("tab in host", "http://127.0.0.1\t/"),
    ("newline in host", "http://exam\nple.com/"),
    ("cr in host", "http://exam\rple.com/"),
    ("crlf injection", "http://example.com/\r\nX-Injected: 1"),
    ("nul in host", "http://exam\x00ple.com/"),
    ("space in host", "http://exa mple.com/"),
    ("leading space in host", "http:// 127.0.0.1/"),
    ("del character", "http://example.com/\x7f"),
    ("c1 control", "http://exam\x9fple.com/"),
    ("percent encoded host", "http://%31%32%37.0.0.1/"),
    ("bracket garbage", "http://[not-an-ip]/"),
    ("empty label", "http://example..com/"),
    ("port out of range", "http://example.com:99999/"),
    ("port not a number", "http://example.com:ssh/"),
    ("negative port", "http://example.com:-1/"),
    ("ipv6 zone id", "http://[fe80::1%25eth0]/"),
    ("truncated escape", "http://example.com/%2"),
    ("bad escape", "http://example.com/%zz"),
    ("missing host", "http:///etc/passwd"),
    ("port with no host", "http://:80/"),
    # Browsers fold a backslash to a slash; urlsplit does not. Anything that reads
    # differently in a browser than it does here is rejected rather than guessed at.
    ("backslash in host", "http://127.0.0.1\\.example.com/"),
    ("double backslash", "http:\\\\example.com/"),
    ("angle brackets in host", "http://<script>.example.com/"),
    ("null-ish host", "http://./"),
    ("dot only host", "http://../"),
    ("over-long url", "http://example.com/" + "a" * 5000),
]


@pytest.mark.parametrize(
    "raw", [pytest.param(raw, id=label) for label, raw in MALFORMED_CASES]
)
def test_malformed_urls_are_rejected(guard: UrlGuard, raw: str) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is False
    assert decision.reason in {
        R.MALFORMED_URL,
        R.MISSING_HOST,
        R.OBFUSCATED_IP_LITERAL,
        R.SCHEME_NOT_ALLOWED,
    }


# ---------------------------------------------------------------------------
# hostname denylist (RFC 6761 / cloud metadata names)
# ---------------------------------------------------------------------------

DENIED_NAMES = [
    "http://localhost/",
    "http://LOCALHOST/",
    "http://localhost.:80/",
    "http://api.localhost/",
    "http://printer.local/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://db.internal/",
]


@pytest.mark.parametrize("raw", DENIED_NAMES)
def test_denied_host_names(guard: UrlGuard, raw: str, resolver: FakeResolver) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is False
    assert decision.reason is R.HOST_NOT_ALLOWED
    assert resolver.calls == []


# ---------------------------------------------------------------------------
# 4. DNS resolution and per-address validation
# ---------------------------------------------------------------------------


def test_name_resolving_to_loopback_is_rejected(guard: UrlGuard, resolver: FakeResolver) -> None:
    """The ``localtest.me`` family: a perfectly ordinary public name pointing at 127.0.0.1."""
    decision = guard.validate("http://localtest.me/")
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE
    assert resolver.calls == ["localtest.me"]


DNS_BLOCKED_HOSTS = [
    ("private a record", "http://internal.example.com/"),
    ("metadata a record", "http://metadata.example.com/"),
    ("cgnat a record", "http://cgnat.example.com/"),
    ("ipv6 ula aaaa record", "http://v6-ula.example.com/"),
    ("ipv4 mapped aaaa record", "http://v6-mapped.example.com/"),
    ("nat64 aaaa record", "http://v6-nat64.example.com/"),
]


@pytest.mark.parametrize(
    "raw", [pytest.param(raw, id=label) for label, raw in DNS_BLOCKED_HOSTS]
)
def test_hosts_resolving_into_blocked_space(guard: UrlGuard, raw: str) -> None:
    decision = guard.validate(raw)
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE


@pytest.mark.parametrize("host", ["dual.example.com", "dual-reversed.example.com"])
def test_every_resolved_address_must_pass(guard: UrlGuard, host: str) -> None:
    """One public A record does not excuse a private one in the same answer.

    Checking only the first address is the most common real-world bug in SSRF guards:
    the attacker controls record order, and the connection may use either.
    """
    decision = guard.validate(f"http://{host}/")
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE


def test_all_a_and_aaaa_records_are_validated(guard: UrlGuard) -> None:
    decision = guard.validate("http://www.example.com/")
    assert decision.allowed is True
    assert len(decision.resolved_ips) == 2


def test_resolution_failure_is_rejected(guard: UrlGuard) -> None:
    decision = guard.validate("http://servfail.example.com/")
    assert decision.allowed is False
    assert decision.reason is R.DNS_RESOLUTION_FAILED


def test_unknown_host_is_rejected(guard: UrlGuard) -> None:
    decision = guard.validate("http://nx.example.com/")
    assert decision.allowed is False
    assert decision.reason is R.DNS_RESOLUTION_FAILED


def test_empty_answer_is_rejected(guard: UrlGuard) -> None:
    decision = guard.validate("http://empty.example.com/")
    assert decision.allowed is False
    assert decision.reason is R.DNS_NO_ADDRESSES


def test_unparseable_answer_is_rejected(guard: UrlGuard) -> None:
    """Default deny: if the resolver hands back something we cannot classify, stop."""
    decision = guard.validate("http://garbage.example.com/")
    assert decision.allowed is False
    assert decision.reason is R.DNS_RESOLUTION_FAILED


# ---------------------------------------------------------------------------
# IDN / homograph handling
# ---------------------------------------------------------------------------


def test_idn_host_is_resolved_as_punycode(guard: UrlGuard, resolver: FakeResolver) -> None:
    decision = guard.validate("http://例え.テスト/")
    assert decision.allowed is True
    assert resolver.calls == ["xn--r8jz45g.xn--zckzah"]
    assert decision.host == "xn--r8jz45g.xn--zckzah"


def test_homograph_host_resolves_as_itself_not_the_lookalike(
    guard: UrlGuard, resolver: FakeResolver
) -> None:
    """Cyrillic 'a' in 'example.com' is a *different* host and must be looked up as such."""
    decision = guard.validate("http://ex\u0430mple.com/")
    assert resolver.calls == ["xn--exmple-4nf.com"]
    assert decision.host == "xn--exmple-4nf.com"


def test_fullwidth_digits_cannot_smuggle_loopback(guard: UrlGuard, resolver: FakeResolver) -> None:
    """U+FF11 etc. fold to ASCII digits during IDNA, so the host really is 127.0.0.1."""
    decision = guard.validate("http://\uff11\uff12\uff17.\uff10.\uff10.\uff11/")
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE
    assert resolver.calls == []


def test_ideographic_full_stop_is_a_label_separator(guard: UrlGuard) -> None:
    decision = guard.validate("http://127\u30020\u30020\u30021/")
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE


# ---------------------------------------------------------------------------
# 7. DNS-rebinding mitigation contract
# ---------------------------------------------------------------------------


def test_allowed_decision_pins_a_single_validated_address(guard: UrlGuard) -> None:
    decision = guard.validate("http://example.com/")
    assert decision.allowed is True
    assert decision.resolved_ip == PUBLIC_V4
    assert decision.resolved_ips == (PUBLIC_V4,)
    assert decision.resolved_ip in decision.resolved_ips


def test_rejected_decision_exposes_no_addresses(guard: UrlGuard) -> None:
    """A public caller must not learn the shape of our internal network."""
    decision = guard.validate("http://internal.example.com/")
    assert decision.resolved_ip is None
    assert decision.resolved_ips == ()
    assert "192.168" not in decision.message_ko
    assert "192.168" not in repr(decision)


def test_message_never_leaks_addresses(guard: UrlGuard) -> None:
    for raw in ("http://10.0.0.1/", "http://metadata.example.com/", "http://localtest.me/"):
        decision = guard.validate(raw)
        assert "169.254" not in decision.message_ko
        assert "127.0.0.1" not in decision.message_ko
        assert "10.0.0.1" not in decision.message_ko


# ---------------------------------------------------------------------------
# 8. redirects
# ---------------------------------------------------------------------------


def test_redirect_to_private_is_rejected(guard: UrlGuard) -> None:
    first = guard.validate("http://hop-a.example.com/")
    assert first.allowed is True
    second = guard.validate_redirect(
        from_url=first.url or "", location="http://internal.example.com/admin", hop=1
    )
    assert second.allowed is False
    assert second.reason is R.BLOCKED_IP_RANGE
    assert second.hop == 1


def test_public_public_private_chain(guard: UrlGuard) -> None:
    decision = guard.validate_chain(
        "http://hop-a.example.com/",
        ["http://hop-b.example.com/next", "http://internal.example.com/admin"],
    )
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE
    assert decision.hop == 2


def test_fully_public_chain_is_allowed(guard: UrlGuard) -> None:
    decision = guard.validate_chain(
        "http://hop-a.example.com/",
        ["http://hop-b.example.com/next", "http://example.com/final"],
    )
    assert decision.allowed is True
    assert decision.url == "http://example.com/final"
    assert decision.hop == 2


def test_relative_redirect_is_resolved_against_the_current_url(guard: UrlGuard) -> None:
    decision = guard.validate_redirect(
        from_url="http://hop-a.example.com/a/b", location="../admin", hop=1
    )
    assert decision.allowed is True
    assert decision.url == "http://hop-a.example.com/admin"


def test_root_relative_redirect(guard: UrlGuard) -> None:
    decision = guard.validate_redirect(
        from_url="http://hop-a.example.com/a/b", location="/x", hop=1
    )
    assert decision.url == "http://hop-a.example.com/x"


def test_redirect_to_blocked_scheme(guard: UrlGuard) -> None:
    decision = guard.validate_redirect(
        from_url="http://hop-a.example.com/", location="file:///etc/passwd", hop=1
    )
    assert decision.allowed is False
    assert decision.reason is R.SCHEME_NOT_ALLOWED


def test_redirect_to_loopback_literal(guard: UrlGuard) -> None:
    decision = guard.validate_redirect(
        from_url="http://hop-a.example.com/", location="http://127.0.0.1:80/", hop=1
    )
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE


def test_redirect_hop_limit(guard: UrlGuard) -> None:
    hosts = ("hop-a.example.com", "hop-b.example.com")
    locations = [f"http://{hosts[n % 2]}/{n}" for n in range(8)]
    decision = guard.validate_chain("http://hop-a.example.com/", locations)
    assert decision.allowed is False
    assert decision.reason is R.TOO_MANY_REDIRECTS


def test_hop_limit_is_configurable(resolver: FakeResolver) -> None:
    guard = UrlGuard(resolver=resolver, policy=UrlGuardPolicy(max_redirects=1))
    ok = guard.validate_chain("http://hop-a.example.com/", ["http://hop-b.example.com/1"])
    assert ok.allowed is True
    too_far = guard.validate_chain(
        "http://hop-a.example.com/",
        ["http://hop-b.example.com/1", "http://example.com/2"],
    )
    assert too_far.allowed is False
    assert too_far.reason is R.TOO_MANY_REDIRECTS


def test_redirect_beyond_limit_is_refused_directly(guard: UrlGuard) -> None:
    decision = guard.validate_redirect(
        from_url="http://hop-a.example.com/", location="http://example.com/x", hop=99
    )
    assert decision.allowed is False
    assert decision.reason is R.TOO_MANY_REDIRECTS


def test_empty_location_is_rejected(guard: UrlGuard) -> None:
    decision = guard.validate_redirect(from_url="http://hop-a.example.com/", location="", hop=1)
    assert decision.allowed is False


MALFORMED_LOCATIONS = [
    ("bad ipv6 literal", "http://[bad]/"),
    ("port out of range", "http://example.com:99999/"),
    ("control character", "http://exa\nmple.com/"),
    ("header injection", "http://example.com/\r\nX-Injected: 1"),
    ("whitespace only", "   "),
    ("bad escape", "http://example.com/%zz"),
]


@pytest.mark.parametrize(
    "location", [pytest.param(loc, id=label) for label, loc in MALFORMED_LOCATIONS]
)
def test_malformed_location_is_a_rejection_not_an_exception(
    guard: UrlGuard, location: str
) -> None:
    """A crash on the redirect path is a fetch that carries on regardless."""
    decision = guard.validate_redirect(
        from_url="http://hop-a.example.com/", location=location, hop=1
    )
    assert decision.allowed is False
    assert decision.reason is R.MALFORMED_URL


def test_redirect_from_a_protocol_relative_location(guard: UrlGuard) -> None:
    """``//host/x`` keeps the scheme but changes the host, so it is re-resolved."""
    decision = guard.validate_redirect(
        from_url="http://hop-a.example.com/a", location="//127.0.0.1/x", hop=1
    )
    assert decision.allowed is False
    assert decision.reason is R.BLOCKED_IP_RANGE


# ---------------------------------------------------------------------------
# 10. normalisation can never widen the guard
# ---------------------------------------------------------------------------

ALL_BLOCKED_URLS = [
    *[raw for _, raw in SCHEME_CASES],
    *[raw for _, raw in CREDENTIAL_CASES],
    *[f"http://example.com:{port}/" for port in BLOCKED_PORTS],
    *[raw for _, raw, _ in BLOCKED_LITERALS],
    *[raw for _, raw in OBFUSCATED_CASES],
    *[raw for _, raw in MALFORMED_CASES],
    *DENIED_NAMES,
    *[raw for _, raw in DNS_BLOCKED_HOSTS],
    "http://localtest.me/",
    "http://dual.example.com/",
    "http://dual-reversed.example.com/",
    "http://empty.example.com/",
    "http://servfail.example.com/",
    "http://garbage.example.com/",
    "http://\uff11\uff12\uff17.\uff10.\uff10.\uff11/",
]


@pytest.mark.parametrize("raw", ALL_BLOCKED_URLS)
def test_nothing_in_the_corpus_is_ever_allowed(guard: UrlGuard, raw: str) -> None:
    assert guard.validate(raw).allowed is False


@pytest.mark.parametrize("raw", ALL_BLOCKED_URLS)
def test_canonical_form_of_a_blocked_url_is_still_blocked(guard: UrlGuard, raw: str) -> None:
    """Feeding the canonical form back in must not launder a rejection into an allow."""
    first = guard.validate(raw)
    assert first.allowed is False
    if first.url is None:
        return
    second = guard.validate(first.url)
    assert second.allowed is False
    assert second.reason is first.reason


# ---------------------------------------------------------------------------
# decision object plumbing
# ---------------------------------------------------------------------------


def test_decision_is_frozen(guard: UrlGuard) -> None:
    decision = guard.validate("http://example.com/")
    with pytest.raises((AttributeError, TypeError)):
        decision.allowed = False  # type: ignore[misc]


def test_raise_if_rejected(guard: UrlGuard) -> None:
    guard.validate("http://example.com/").raise_if_rejected()
    with pytest.raises(UrlRejectedError) as excinfo:
        guard.validate("http://127.0.0.1/").raise_if_rejected()
    assert excinfo.value.decision.reason is R.BLOCKED_IP_RANGE


def test_rejection_maps_to_the_shared_error_code(guard: UrlGuard) -> None:
    decision = guard.validate("http://127.0.0.1/")
    assert decision.error_code is ErrorCode.TARGET_URL_REJECTED
    api_error = decision.as_api_error()
    assert api_error.code is ErrorCode.TARGET_URL_REJECTED
    assert api_error.retryable is False
    assert api_error.message == decision.message_ko


def test_allowed_decision_has_no_error_code(guard: UrlGuard) -> None:
    decision = guard.validate("http://example.com/")
    assert decision.error_code is None
    assert decision.reason is None
    with pytest.raises(ValueError, match="allowed"):
        decision.as_api_error()


@pytest.mark.parametrize("reason", list(UrlRejectionReason))
def test_every_reason_has_a_korean_message(reason: UrlRejectionReason) -> None:
    message = UrlDecision.message_for(reason)
    assert message
    assert any("가" <= ch <= "힣" for ch in message), "message must be Korean"


def test_decision_reports_host_and_port(guard: UrlGuard) -> None:
    decision = guard.validate("http://example.com/a")
    assert decision.host == "example.com"
    assert decision.port == 80
