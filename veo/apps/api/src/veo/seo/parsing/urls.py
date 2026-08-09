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


def to_ascii_host(host: str) -> str:
    """한글 도메인을 punycode 로 맞춘다 — 같은 도메인을 두 이름으로 세지 않기 위해.

    ``더바른한의원.kr`` 과 ``xn--9m1bm0ji9bd0qotax68d.kr`` 은 **같은 도메인**이다.
    앞의 것은 사람이 읽는 표기이고 뒤의 것은 그것을 ASCII 로 인코딩한 것이다. 그런데
    문자열로 비교하면 서로 다르다.

    실측 2026-08-09 — 그래서 거래처 한 곳의 SEO 점수가 **40(취약)** 에 묶여 있었다.
    그 사이트는 punycode 주소로 서비스되면서 ``<link rel="canonical">`` 에는 한글
    주소를 적어 두었고, 우리는 그것을 "canonical 이 외부 도메인을 가리킨다(치명)" 로
    읽었다. 명세의 ``mass_cross_domain_canonical`` 상한이 걸려 다른 항목을 아무리
    고쳐도 40 을 못 넘는 상태였다. **사이트에는 아무 문제가 없었다.**

    인코딩할 수 없는 호스트는 **있는 그대로 돌려준다.** 여기서 예외를 내면 진단이
    통째로 멈춘다 — 이상한 호스트는 사이트에 대한 사실이지 우리 쪽 고장이 아니다.
    """
    if not host:
        return host
    try:
        return host.encode("idna").decode("ascii").lower()
    except (UnicodeError, UnicodeDecodeError):
        return host.lower()


def registrable_domain(host: str) -> str:
    """The part of a host that decides ownership, for a cross-domain comparison.

    Deliberately simple: the last two labels, plus a third for the two-level public
    suffixes Korean sites actually use (``co.kr``, ``or.kr``, ``go.kr``, ``ne.kr``).
    A full public-suffix list is a dependency VEO has not taken, and being slightly
    conservative here only ever merges two hosts that share an owner anyway.

    호스트는 먼저 punycode 로 맞춘다(:func:`to_ascii_host`). 이 함수를 지나는 비교가
    셋이고 — canonical 의 외부 도메인 판정, AI 답변 인용의 자사 도메인 대조, `same_site`
    — 셋 다 한글 도메인을 다른 도메인으로 세면 조용히 틀린다. 인용 쪽은 특히 나쁘다:
    자사 도메인 인용은 확신도를 그것만으로 확정선 위로 올리는 신호라, 못 맞추면
    **실제로 인용된 노출이 검수 대기로 사라진다.**
    """
    labels = [label for label in to_ascii_host(host).split(".") if label]
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
    "to_ascii_host",
]
