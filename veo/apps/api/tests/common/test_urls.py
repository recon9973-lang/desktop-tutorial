"""Normalisation contract for :mod:`veo.common.urls`.

The canonical form is what VEO caches and de-duplicates on, so two URLs that mean the
same thing must produce the same string, and two URLs that mean different things must
not. The security-critical half of that contract lives in ``test_url_guard.py``:
normalisation must never widen what the guard allows.
"""

from __future__ import annotations

import ipaddress

import pytest

from veo.common.urls import (
    HostForm,
    UrlNormalizationError,
    canonical_url,
    normalize_url,
    parse_legacy_ipv4,
    resolve_reference,
)

CANONICAL_CASES = [
    # (label, raw, expected canonical)
    ("adds root path", "http://example.com", "http://example.com/"),
    ("lowercases scheme", "HTTP://example.com/", "http://example.com/"),
    ("lowercases mixed scheme", "HtTpS://example.com/", "https://example.com/"),
    ("lowercases host", "http://ExAmPlE.CoM/a", "http://example.com/a"),
    ("strips default http port", "http://example.com:80/a", "http://example.com/a"),
    ("strips default https port", "https://example.com:443/a", "https://example.com/a"),
    ("keeps non-default port", "http://example.com:8080/a", "http://example.com:8080/a"),
    ("strips fragment", "http://example.com/a#top", "http://example.com/a"),
    ("strips empty fragment", "http://example.com/a#", "http://example.com/a"),
    ("strips trailing root dot", "http://example.com./a", "http://example.com/a"),
    ("strips surrounding space", "  http://example.com/a  ", "http://example.com/a"),
    ("strips trailing newline", "http://example.com/a\n", "http://example.com/a"),
    ("resolves dot segments", "http://example.com/a/./b/../c", "http://example.com/a/c"),
    ("resolves leading parent", "http://example.com/../../a", "http://example.com/a"),
    ("keeps trailing slash", "http://example.com/a/", "http://example.com/a/"),
    ("drops empty query", "http://example.com/a?", "http://example.com/a"),
    ("preserves query order", "http://example.com/?b=2&a=1", "http://example.com/?b=2&a=1"),
    ("preserves duplicate keys", "http://example.com/?a=1&a=2", "http://example.com/?a=1&a=2"),
    ("uppercases pct escapes", "http://example.com/%2fa%3Fb", "http://example.com/%2Fa%3Fb"),
    ("never decodes escapes", "http://example.com/%2e%2e/a", "http://example.com/%2E%2E/a"),
    (
        "punycodes idn host",
        "http://例え.テスト/",
        "http://xn--r8jz45g.xn--zckzah/",
    ),
    (
        "punycodes homograph host",
        "http://ex\u0430mple.com/",
        "http://xn--exmple-4nf.com/",
    ),
    (
        "folds fullwidth host to ascii",
        "http://\uff45\uff58\uff41\uff4d\uff50\uff4c\uff45.com/",
        "http://example.com/",
    ),
    (
        "percent-encodes non-ascii path",
        "http://example.com/パス",
        "http://example.com/%E3%83%91%E3%82%B9",
    ),
    ("compresses ipv6 literal", "http://[2001:DB8:0:0::1]/", "http://[2001:db8::1]/"),
    ("keeps ipv6 port", "http://[2001:db8::1]:8080/", "http://[2001:db8::1]:8080/"),
    ("keeps ipv4 literal", "http://93.184.216.34/x", "http://93.184.216.34/x"),
    ("leaves legacy ip form intact", "http://2130706433/", "http://2130706433/"),
]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [pytest.param(raw, expected, id=label) for label, raw, expected in CANONICAL_CASES],
)
def test_canonical_form(raw: str, expected: str) -> None:
    assert canonical_url(raw) == expected


MALFORMED_CASES = [
    ("empty", "", "MALFORMED_URL"),
    ("blank", "   ", "MALFORMED_URL"),
    ("interior space", "http://exa mple.com/", "ILLEGAL_CHARACTER"),
    ("interior tab", "http://exa\tmple.com/", "ILLEGAL_CHARACTER"),
    ("interior newline", "http://exa\nmple.com/", "ILLEGAL_CHARACTER"),
    ("interior cr", "http://exa\rmple.com/", "ILLEGAL_CHARACTER"),
    ("nul byte", "http://exa\x00mple.com/", "ILLEGAL_CHARACTER"),
    ("del byte", "http://example.com/\x7f", "ILLEGAL_CHARACTER"),
    ("c1 control", "http://exam\x9fple.com/", "ILLEGAL_CHARACTER"),
    ("space before host", "http:// 127.0.0.1/", "ILLEGAL_CHARACTER"),
    ("userinfo password", "http://user:pass@example.com/", "CREDENTIALS_IN_URL"),
    ("userinfo only", "http://user@example.com/", "CREDENTIALS_IN_URL"),
    ("empty userinfo", "http://@example.com/", "CREDENTIALS_IN_URL"),
    ("at confusion", "http://expected.com@127.0.0.1/", "CREDENTIALS_IN_URL"),
    ("double at confusion", "http://a:b@evil.com@127.0.0.1/", "CREDENTIALS_IN_URL"),
    ("port out of range", "http://example.com:99999/", "INVALID_PORT"),
    ("non numeric port", "http://example.com:http/", "INVALID_PORT"),
    ("percent in host", "http://%31%32%37.0.0.1/", "ILLEGAL_HOST"),
    ("ipv6 zone id", "http://[fe80::1%25eth0]/", "ILLEGAL_HOST"),
    ("bad bracket host", "http://[not-an-ip]/", "MALFORMED_URL"),
    ("empty label", "http://example..com/", "ILLEGAL_HOST"),
    ("dangling pct escape", "http://example.com/%zz", "ILLEGAL_ESCAPE"),
    ("truncated pct escape", "http://example.com/%2", "ILLEGAL_ESCAPE"),
    ("oversized label", "http://" + "a" * 64 + ".com/", "ILLEGAL_HOST"),
]


@pytest.mark.parametrize(
    ("raw", "code"),
    [pytest.param(raw, code, id=label) for label, raw, code in MALFORMED_CASES],
)
def test_rejected_by_normalisation(raw: str, code: str) -> None:
    with pytest.raises(UrlNormalizationError) as excinfo:
        normalize_url(raw)
    assert excinfo.value.code == code


def test_credentialed_url_has_no_canonical_form() -> None:
    """Stripping userinfo would turn a rejected URL into an innocuous-looking one.

    ``http://user:pass@evil.com@127.0.0.1/`` must never canonicalise to
    ``http://127.0.0.1/`` *or* to ``http://evil.com/``: both would launder the input.
    The only safe answer is that such a URL has no canonical form at all.
    """
    with pytest.raises(UrlNormalizationError):
        normalize_url("http://user:pass@evil.com@127.0.0.1/")


def test_hostless_scheme_is_parsed_not_rejected() -> None:
    """The guard needs the scheme to report SCHEME_NOT_ALLOWED, so parsing must survive."""
    parsed = normalize_url("javascript:alert(1)")
    assert parsed.scheme == "javascript"
    assert parsed.host == ""


def test_missing_host_survives_parsing() -> None:
    parsed = normalize_url("http:///etc/passwd")
    assert parsed.scheme == "http"
    assert parsed.host == ""


HOST_FORM_CASES = [
    ("dns name", "http://example.com/", HostForm.DNS_NAME, None),
    ("ipv4 literal", "http://93.184.216.34/", HostForm.IP_LITERAL, "93.184.216.34"),
    ("ipv6 literal", "http://[2001:db8::1]/", HostForm.IP_LITERAL, "2001:db8::1"),
    ("decimal", "http://2130706433/", HostForm.OBFUSCATED_IP, "127.0.0.1"),
    ("octal", "http://0177.0.0.1/", HostForm.OBFUSCATED_IP, "127.0.0.1"),
    ("hex dotted", "http://0x7f.0x0.0x0.0x1/", HostForm.OBFUSCATED_IP, "127.0.0.1"),
    ("hex flat", "http://0x7f000001/", HostForm.OBFUSCATED_IP, "127.0.0.1"),
    ("octal flat", "http://017700000001/", HostForm.OBFUSCATED_IP, "127.0.0.1"),
    ("zero padded", "http://127.000.000.001/", HostForm.OBFUSCATED_IP, "127.0.0.1"),
    ("short form", "http://127.1/", HostForm.OBFUSCATED_IP, "127.0.0.1"),
    ("two part", "http://192.11010305/", HostForm.OBFUSCATED_IP, "192.168.1.1"),
    ("public decimal", "http://1572395042/", HostForm.OBFUSCATED_IP, "93.184.216.34"),
]


@pytest.mark.parametrize(
    ("raw", "form", "ip"),
    [pytest.param(raw, form, ip, id=label) for label, raw, form, ip in HOST_FORM_CASES],
)
def test_host_form_classification(raw: str, form: HostForm, ip: str | None) -> None:
    parsed = normalize_url(raw)
    assert parsed.host_form is form
    assert parsed.ip == (ipaddress.ip_address(ip) if ip else None)


LEGACY_NON_MATCHES = [
    "example.com",
    "123.example.com",
    "1.2.3.4.5",
    "256.1.1.1",
    "0x1.0x2.0x3.0x4.0x5",
    "099.1.1.1",  # 9 is not an octal digit
    "4294967296",  # one past the 32-bit space
    "",
]


@pytest.mark.parametrize("host", LEGACY_NON_MATCHES)
def test_parse_legacy_ipv4_rejects_non_addresses(host: str) -> None:
    assert parse_legacy_ipv4(host) is None


def test_canonical_is_idempotent() -> None:
    for _, raw, expected in CANONICAL_CASES:
        assert canonical_url(canonical_url(raw)) == expected


REFERENCE_CASES = [
    ("absolute", "http://example.com/a/b", "https://other.example/x", "https://other.example/x"),
    ("root relative", "http://example.com/a/b", "/x", "http://example.com/x"),
    ("path relative", "http://example.com/a/b", "c", "http://example.com/a/c"),
    ("parent relative", "http://example.com/a/b/c", "../x", "http://example.com/a/x"),
    ("protocol relative", "https://example.com/a", "//other.example/x", "https://other.example/x"),
    ("query only", "http://example.com/a?x=1", "?y=2", "http://example.com/a?y=2"),
]


@pytest.mark.parametrize(
    ("base", "location", "expected"),
    [pytest.param(b, loc, exp, id=label) for label, b, loc, exp in REFERENCE_CASES],
)
def test_resolve_reference(base: str, location: str, expected: str) -> None:
    assert resolve_reference(base, location) == expected


def test_normalized_url_is_frozen() -> None:
    parsed = normalize_url("http://example.com/")
    with pytest.raises((AttributeError, TypeError)):
        parsed.host = "evil.example"  # type: ignore[misc]
