"""URL parsing, normalisation and canonicalisation.

Two jobs, deliberately kept apart from policy:

1. Produce a **stable canonical form** so that two URLs meaning the same thing collapse
   to one cache key, one de-duplication key, one row in a crawl frontier.
2. Produce a **fully classified** view of the authority — punycode host, effective port,
   and whether the host is a name, a real IP literal, or one of the legacy ``inet_aton``
   spellings attackers use to smuggle ``127.0.0.1`` past a naive filter.

Nothing here decides whether a URL may be fetched; :mod:`veo.common.security.url_guard`
does that. The division matters because of one hard rule:

    **Normalisation must never be able to turn a blocked URL into an allowed one.**

Three design choices enforce that rule:

* Percent-escapes are *never* decoded. Case is normalised (``%2f`` → ``%2F``) and
  nothing else, so ``%2e%2e`` can never become ``..`` and ``%31%32%37`` can never
  become ``127``.
* A percent sign in the host is a hard error rather than something to decode.
* A URL carrying userinfo has **no canonical form at all** — see
  :func:`normalize_url`. Stripping ``user:pass@`` would launder
  ``http://trusted.example@127.0.0.1/`` into ``http://127.0.0.1/``, and stripping the
  host after the ``@`` would launder it into ``http://trusted.example/``. Both are
  wrong, so the function refuses instead.

IDNA conversion is done *before* the host is inspected as an address, because the
Unicode-to-ASCII fold is itself an attack surface: a host written in fullwidth digits
(U+FF11 U+FF12 U+FF17 . U+FF10 . U+FF10 . U+FF11) folds straight to ``127.0.0.1``, and
U+3002/U+FF0E/U+FF61 are all label separators.
Classifying first and folding second would miss both.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import urljoin, urlsplit

__all__ = [
    "DEFAULT_PORTS",
    "HostForm",
    "NormalizedUrl",
    "UrlNormalizationError",
    "canonical_url",
    "normalize_url",
    "parse_legacy_ipv4",
    "resolve_reference",
]

DEFAULT_PORTS: dict[str, int] = {
    "http": 80,
    "https": 443,
    "ws": 80,
    "wss": 443,
    "ftp": 21,
}

MAX_URL_LENGTH = 4096
MAX_HOST_LENGTH = 253
MAX_LABEL_LENGTH = 63

_PCT_RE = re.compile(r"%[0-9A-Fa-f]{2}")
_LABEL_RE = re.compile(r"\A[a-z0-9_\-]+\Z")
_LEGACY_PART_RE = re.compile(r"\A(?:0[xX][0-9a-fA-F]+|[0-9]+)\Z")


class UrlNormalizationError(ValueError):
    """A URL cannot be reduced to a canonical form.

    ``code`` is machine-readable and maps onto a
    :class:`~veo.common.security.url_guard.UrlRejectionReason`. ``detail`` is for logs
    only — it may quote the offending input and must not be shown to a caller.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class HostForm(StrEnum):
    """What the authority component actually is, after IDNA folding.

    ``OBFUSCATED_IP`` covers every legacy ``inet_aton`` spelling: bare decimal
    (``2130706433``), octal (``0177.0.0.1``), hex (``0x7f.0x0.0x0.0x1``), zero-padded
    (``127.000.000.001``) and short forms (``127.1``). These are always treated as
    hostile — a real client has no reason to write an address that way, while an SSRF
    payload has every reason to.
    """

    EMPTY = "EMPTY"
    DNS_NAME = "DNS_NAME"
    IP_LITERAL = "IP_LITERAL"
    OBFUSCATED_IP = "OBFUSCATED_IP"


@dataclass(frozen=True, slots=True)
class NormalizedUrl:
    """A URL reduced to its canonical parts. Immutable on purpose."""

    raw: str
    scheme: str
    host: str
    host_form: HostForm
    ip: IPv4Address | IPv6Address | None
    port: int | None
    explicit_port: int | None
    path: str
    query: str
    canonical: str

    @property
    def host_for_url(self) -> str:
        """The host as it appears inside a URL — IPv6 literals wear their brackets."""
        if isinstance(self.ip, IPv6Address):
            return f"[{self.host}]"
        return self.host

    @property
    def default_port(self) -> int | None:
        return DEFAULT_PORTS.get(self.scheme)


def normalize_url(raw: str) -> NormalizedUrl:
    """Parse and canonicalise ``raw``.

    Raises :class:`UrlNormalizationError` when the input cannot be reduced safely. The
    error ``code`` is one of ``MALFORMED_URL``, ``ILLEGAL_CHARACTER``, ``ILLEGAL_HOST``,
    ``ILLEGAL_ESCAPE``, ``INVALID_PORT`` or ``CREDENTIALS_IN_URL``.

    Leading and trailing whitespace is stripped (URLs are pasted by humans); whitespace
    or control characters *inside* the URL are a hard error, because ``urlsplit`` itself
    silently deletes tab/CR/LF and that deletion is exactly how a request-splitting or
    filter-evasion payload gets through.
    """
    cleaned = raw.strip()
    if not cleaned:
        raise UrlNormalizationError("MALFORMED_URL", "empty url")
    if len(cleaned) > MAX_URL_LENGTH:
        raise UrlNormalizationError("MALFORMED_URL", "url too long")
    _reject_illegal_characters(cleaned)

    try:
        split = urlsplit(cleaned)
    except ValueError as exc:
        raise UrlNormalizationError("MALFORMED_URL", str(exc)) from exc

    if "@" in split.netloc:
        # Never report which part of the userinfo was present; it may be a password.
        raise UrlNormalizationError("CREDENTIALS_IN_URL", "userinfo component present")

    try:
        explicit_port = split.port
    except ValueError as exc:
        raise UrlNormalizationError("INVALID_PORT", str(exc)) from exc

    scheme = split.scheme.lower()
    host, host_form, ip = _normalize_host(split.hostname or "")
    default_port = DEFAULT_PORTS.get(scheme)
    port = explicit_port if explicit_port is not None else default_port

    path = _encode_component(split.path)
    query = _encode_component(split.query)

    if host:
        path = _remove_dot_segments(path) if path else "/"
        if not path:
            path = "/"
        authority = f"[{host}]" if isinstance(ip, IPv6Address) else host
        if port is not None and port != default_port:
            authority = f"{authority}:{port}"
        canonical = f"{scheme}://{authority}{path}"
        if query:
            canonical = f"{canonical}?{query}"
    else:
        # No authority: there is nothing meaningful to canonicalise, and inventing a
        # shape here risks changing what the string means. Keep the cleaned input.
        canonical = cleaned

    return NormalizedUrl(
        raw=raw,
        scheme=scheme,
        host=host,
        host_form=host_form,
        ip=ip,
        port=port,
        explicit_port=explicit_port,
        path=path,
        query=query,
        canonical=canonical,
    )


def canonical_url(raw: str) -> str:
    """Return the canonical string form of ``raw``. Stable, idempotent, cache-safe."""
    return normalize_url(raw).canonical


def resolve_reference(base: str, reference: str) -> str:
    """Resolve a ``Location`` header (absolute or relative) against ``base``.

    Both sides go through normalisation, so a redirect target inherits every rule the
    original URL was held to — including the ban on control characters, which is how
    ``Location: http://evil\\r\\nX: y`` gets stopped.
    """
    base_url = normalize_url(base)
    target = reference.strip()
    if not target:
        raise UrlNormalizationError("MALFORMED_URL", "empty reference")
    _reject_illegal_characters(target)
    try:
        joined = urljoin(base_url.canonical, target)
    except ValueError as exc:
        # urljoin parses the reference itself and raises on, say, ``http://[bad]/``.
        # Left uncaught this escapes the guard as a bare ValueError instead of a
        # rejection, and an exception on the redirect path is a fetch that keeps going.
        raise UrlNormalizationError("MALFORMED_URL", str(exc)) from exc
    return canonical_url(joined)


def parse_legacy_ipv4(host: str) -> IPv4Address | None:
    """Interpret ``host`` the way ``inet_aton`` would, or return ``None``.

    ``inet_aton`` accepts one to four parts, each decimal, octal (leading ``0``) or hex
    (leading ``0x``), with the final part absorbing all remaining bytes. Every C-based
    resolver on the planet still honours this, so ``http://0177.0.0.1/`` reaches
    localhost even though :mod:`ipaddress` refuses to parse it. We reproduce the
    parsing solely in order to *reject* it.
    """
    if not host:
        return None
    parts = host.split(".")
    if not 1 <= len(parts) <= 4:
        return None

    values: list[int] = []
    for part in parts:
        if _LEGACY_PART_RE.match(part) is None:
            return None
        try:
            if part[:2].lower() == "0x":
                value = int(part, 16)
            elif part[0] == "0" and len(part) > 1:
                value = int(part, 8)
            else:
                value = int(part, 10)
        except ValueError:
            return None
        values.append(value)

    if any(value > 0xFF for value in values[:-1]):
        return None
    if values[-1] >= 256 ** (5 - len(values)):
        return None

    packed = values[-1]
    for index, value in enumerate(values[:-1]):
        packed |= value << (8 * (3 - index))
    return IPv4Address(packed)


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _reject_illegal_characters(value: str) -> None:
    for char in value:
        code_point = ord(char)
        if char.isspace() or code_point < 0x20 or 0x7F <= code_point <= 0x9F:
            raise UrlNormalizationError(
                "ILLEGAL_CHARACTER", f"disallowed character U+{code_point:04X}"
            )


def _normalize_host(raw_host: str) -> tuple[str, HostForm, IPv4Address | IPv6Address | None]:
    if not raw_host:
        return "", HostForm.EMPTY, None

    if "%" in raw_host:
        # Two attacks in one character: percent-escapes that would decode into an
        # address (``%31%32%37.0.0.1``), and IPv6 zone ids (``fe80::1%25eth0``) which
        # :mod:`ipaddress` happily parses and which only ever name a local interface.
        raise UrlNormalizationError("ILLEGAL_HOST", "percent sign in host")

    if ":" in raw_host:
        # urlsplit has already removed the brackets, so a colon can only be IPv6.
        try:
            address6 = ipaddress.IPv6Address(raw_host)
        except ValueError as exc:
            raise UrlNormalizationError("ILLEGAL_HOST", str(exc)) from exc
        return address6.compressed, HostForm.IP_LITERAL, address6

    host = raw_host.lower().rstrip(".")
    if not host:
        raise UrlNormalizationError("ILLEGAL_HOST", "empty host")

    if not host.isascii():
        try:
            host = host.encode("idna").decode("ascii")
        except (UnicodeError, ValueError) as exc:
            raise UrlNormalizationError("ILLEGAL_HOST", f"IDNA conversion failed: {exc}") from exc
        host = host.rstrip(".")

    _validate_ascii_host(host)

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return literal.compressed, HostForm.IP_LITERAL, literal

    legacy = parse_legacy_ipv4(host)
    if legacy is not None:
        return host, HostForm.OBFUSCATED_IP, legacy

    return host, HostForm.DNS_NAME, None


def _validate_ascii_host(host: str) -> None:
    if len(host) > MAX_HOST_LENGTH:
        raise UrlNormalizationError("ILLEGAL_HOST", "host too long")
    for label in host.split("."):
        if not label:
            raise UrlNormalizationError("ILLEGAL_HOST", "empty label")
        if len(label) > MAX_LABEL_LENGTH:
            raise UrlNormalizationError("ILLEGAL_HOST", "label too long")
        if _LABEL_RE.match(label) is None:
            raise UrlNormalizationError("ILLEGAL_HOST", "illegal character in label")


def _encode_component(value: str) -> str:
    """Percent-encode non-ASCII, upper-case existing escapes, decode nothing."""
    if not value:
        return ""
    out: list[str] = []
    index = 0
    length = len(value)
    while index < length:
        char = value[index]
        if char == "%":
            if _PCT_RE.match(value, index) is None:
                raise UrlNormalizationError("ILLEGAL_ESCAPE", "malformed percent-escape")
            out.append(value[index : index + 3].upper())
            index += 3
            continue
        if char.isascii():
            out.append(char)
        else:
            out.extend(f"%{byte:02X}" for byte in char.encode("utf-8"))
        index += 1
    return "".join(out)


def _remove_dot_segments(path: str) -> str:
    """RFC 3986 §5.2.4, preserving a trailing slash implied by a final ``.`` or ``..``."""
    if not path:
        return ""
    segments = path.split("/")
    last_index = len(segments) - 1
    out: list[str] = []
    for index, segment in enumerate(segments):
        if segment == ".":
            if index == last_index:
                out.append("")
            continue
        if segment == "..":
            if len(out) > 1:
                out.pop()
            if index == last_index:
                out.append("")
            continue
        out.append(segment)
    return "/".join(out)
