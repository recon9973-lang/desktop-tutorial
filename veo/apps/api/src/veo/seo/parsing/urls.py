"""URL normalisation shared by every collector.

Two URLs that differ only by a trailing slash, a default port or a fragment are the same
page. If the collectors disagreed about that, a link would look broken because the link
graph and the crawl used different spellings of the same address.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

#: Schemes an anchor can carry that are not a page at all.
NON_PAGE_SCHEMES = frozenset({"mailto", "tel", "javascript", "sms", "data", "about", "ftp"})

_DEFAULT_PORTS = {"http": "80", "https": "443"}


def normalise_url(url: str) -> str:
    """Drop the fragment, lower-case scheme and host, and remove a default port."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    port = parts.port
    netloc = host
    if port is not None and _DEFAULT_PORTS.get(scheme) != str(port):
        netloc = f"{host}:{port}"
    path = parts.path or ("/" if netloc else "")
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def resolve(base: str, href: str) -> str | None:
    """Absolute, normalised form of ``href`` as seen from ``base``.

    ``None`` when the href does not address a page — an anchor, a ``mailto:`` or an
    empty attribute. Treating those as links would invent broken links and orphan pages.
    """
    candidate = href.strip()
    if not candidate or candidate.startswith("#"):
        return None
    scheme = urlsplit(candidate).scheme.lower()
    if scheme and scheme in NON_PAGE_SCHEMES:
        return None
    joined = urljoin(base, candidate)
    if urlsplit(joined).scheme.lower() not in {"http", "https"}:
        return None
    return normalise_url(joined)


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def path_of(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path


def registrable_domain(host: str) -> str:
    """The part of a host that decides ownership, for a cross-domain comparison.

    Deliberately simple: the last two labels, plus a third for the two-level public
    suffixes Korean sites actually use (``co.kr``, ``or.kr``, ``go.kr``, ``ne.kr``).
    A full public-suffix list is a dependency VEO has not taken, and being slightly
    conservative here only ever merges two hosts that share an owner anyway.
    """
    labels = [label for label in host.lower().split(".") if label]
    if len(labels) <= 2:
        return ".".join(labels)
    second_level = {"co", "or", "go", "ne", "re", "pe", "ac", "com", "net", "org"}
    if labels[-1] == "kr" and labels[-2] in second_level:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def same_site(left: str, right: str) -> bool:
    return registrable_domain(host_of(left)) == registrable_domain(host_of(right))


def is_https(url: str) -> bool:
    return urlsplit(url).scheme.lower() == "https"


def depth_of(url: str) -> int:
    return len([segment for segment in urlsplit(url).path.split("/") if segment])


__all__ = [
    "NON_PAGE_SCHEMES",
    "depth_of",
    "host_of",
    "is_https",
    "normalise_url",
    "path_of",
    "registrable_domain",
    "resolve",
    "same_site",
]
