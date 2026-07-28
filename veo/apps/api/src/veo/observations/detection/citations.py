"""Whose URL an answer cited — decided by normalisation, never by string comparison.

A mention and a citation are different facts with different value, and this module owns
the second one. Two ways to get it wrong, both expensive:

* **Claiming a third party's URL.** An article *about* the customer, cited as a source, is
  the publisher's citation, not the customer's. Merging the two inflates the citation rate
  with somebody else's earned coverage.
* **Losing our own URL behind a wrapper.** Engines rarely hand over a bare link. It arrives
  as ``google.com/url?q=…``, or with ``utm_*`` bolted on, or on a subdomain. String equality
  against a declared domain misses every one of those, and the loss is silent.

So every URL goes through :mod:`veo.common.urls` — the same canonicalisation the crawler is
held to, including its refusal to decode percent-escapes in a host. What this module cannot
resolve without a network call (a link shortener) it marks ``UNRESOLVED`` and hands to a
human, rather than assuming it points somewhere convenient.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import parse_qsl, urlsplit

from veo.common.urls import UrlNormalizationError, normalize_url
from veo.observations.detection.disambiguation import BrandProfile

__all__ = [
    "CitationMatch",
    "CitationOwnership",
    "OwnDomainRule",
    "match_citations",
    "own_citations",
    "registrable_domain",
]

#: Second-level suffixes that are registries rather than registrable names. Used only to
#: report a readable domain — ownership never depends on this list.
_PUBLIC_SECOND_LEVELS: frozenset[str] = frozenset(
    {
        "co.kr", "ne.kr", "or.kr", "go.kr", "re.kr", "pe.kr", "sc.kr", "hs.kr", "ms.kr",
        "es.kr", "ac.kr", "co.uk", "org.uk", "ac.uk", "co.jp", "or.jp", "ne.jp",
        "com.cn", "com.au", "com.br", "com.tw", "com.hk", "com.sg",
    }
)

#: Hosts where many businesses live side by side. Declaring one of these *without* a path
#: would hand the customer every blog, cafe and channel on it — the single largest
#: over-claim available, and it looks like a normal configuration until the citation rate
#: is suddenly enormous. A path prefix is required instead.
_SHARED_PLATFORM_HOSTS: frozenset[str] = frozenset(
    {
        "naver.com", "blog.naver.com", "m.blog.naver.com", "cafe.naver.com",
        "post.naver.com", "in.naver.com", "smartstore.naver.com",
        "daum.net", "cafe.daum.net", "brunch.co.kr", "tistory.com", "kakao.com",
        "medium.com", "blogspot.com", "wordpress.com", "blogger.com", "notion.site",
        "wixsite.com", "modoo.at", "imweb.me", "cafe24.com", "github.io", "linktr.ee",
        "facebook.com", "www.facebook.com", "instagram.com", "www.instagram.com",
        "youtube.com", "www.youtube.com", "m.youtube.com", "threads.net",
        "x.com", "twitter.com",
    }
)

#: Query parameters that carry the real destination on a redirect or tracker.
_REDIRECT_PARAMS: tuple[str, ...] = (
    "url", "u", "q", "target", "to", "dest", "destination", "redirect", "redirect_url",
    "redirect_uri", "link", "out", "goto", "next",
)

#: Hosts whose links cannot be resolved without fetching them. We do not fetch.
_OPAQUE_REDIRECT_HOSTS: frozenset[str] = frozenset(
    {
        "bit.ly", "t.co", "goo.gl", "tinyurl.com", "buly.kr", "han.gl", "vo.la",
        "me2.do", "abr.ge", "url.kr", "lnkd.in", "naver.me", "kko.to", "kko.kr",
    }
)

_MAX_UNWRAP_HOPS = 3

_UNRESOLVED_SHORTENER_KO = (
    "단축 URL 이라 실제 목적지를 알 수 없습니다. 네트워크를 타지 않고 추측하지 않습니다 — "
    "사람이 확인해야 합니다."
)
_MALFORMED_KO = "URL 을 정규화할 수 없습니다({code}). 소유 여부를 판단하지 않습니다."
_OWN_KO = "선언된 자사 도메인 {domain} 과(와) 일치합니다."
_THIRD_PARTY_KO = (
    "자사 도메인이 아닙니다. 우리를 다룬 남의 문서일 수는 있지만, 그것은 그 매체의 "
    "인용입니다."
)


class CitationOwnership(StrEnum):
    """Whose source this citation is."""

    OWN = "OWN"
    THIRD_PARTY = "THIRD_PARTY"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class OwnDomainRule:
    """One declared property.

    A path prefix exists because a customer's presence is often a page on someone else's
    host — ``blog.naver.com/venomdental``. Claiming the whole of ``blog.naver.com`` would
    hand the customer every Naver blog in the country.
    """

    host: str
    path_prefix: str = "/"

    @classmethod
    def parse(cls, declared: str) -> OwnDomainRule:
        """Read one declared property, refusing declarations that claim too much.

        A refusal is loud on purpose. Silently dropping an unusable rule would leave the
        customer's real citations uncounted with nothing on screen to explain why, and
        silently honouring ``blog.naver.com`` would credit them with the whole platform.
        """
        cleaned = declared.strip().lower()
        for scheme in ("https://", "http://"):
            if cleaned.startswith(scheme):
                cleaned = cleaned[len(scheme) :]
        host, _, path = cleaned.partition("/")
        host = host.strip("/").rstrip(".")
        prefix = f"/{path.strip('/')}" if path.strip("/") else "/"

        if not host or len(host.split(".")) < 2 or host in _PUBLIC_SECOND_LEVELS:
            raise ValueError(
                f"자사 도메인 '{declared}' 이(가) 도메인이 아닙니다. "
                "이 값으로는 남의 사이트까지 우리 인용으로 셉니다."
            )
        if host in _SHARED_PLATFORM_HOSTS and prefix == "/":
            raise ValueError(
                f"'{host}' 은(는) 여러 업체가 함께 쓰는 플랫폼입니다. "
                f"'{host}/계정경로' 처럼 경로까지 선언해야 우리 것만 셉니다."
            )
        return cls(host=host, path_prefix=prefix)

    def covers(self, host: str, path: str) -> bool:
        if not self.host:
            return False
        if host != self.host and not host.endswith(f".{self.host}"):
            return False
        if self.path_prefix == "/":
            return True
        return path == self.path_prefix or path.startswith(f"{self.path_prefix}/")


@dataclass(frozen=True, slots=True)
class CitationMatch:
    """One cited URL, and the verdict on whose it is."""

    position: int
    raw_url: str
    canonical_url: str
    host: str
    domain: str
    ownership: CitationOwnership
    matched_domain: str
    unwrapped_from: str
    """The wrapper the destination was extracted from, or ``""`` if there was none."""
    reason_ko: str

    @property
    def is_own(self) -> bool:
        return self.ownership is CitationOwnership.OWN

    def as_citation_values(self) -> dict[str, object]:
        """The shape ``citations`` rows want."""
        return {
            "url": self.canonical_url or self.raw_url,
            "domain": self.domain or self.host,
            "position": self.position,
            "is_own_domain": self.is_own,
        }


def registrable_domain(host: str) -> str:
    """``blog.venomdental.co.kr`` -> ``venomdental.co.kr``. Reporting only."""
    labels = host.strip(".").lower().split(".")
    if len(labels) < 2:
        return host
    if len(labels) >= 3 and ".".join(labels[-2:]) in _PUBLIC_SECOND_LEVELS:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def match_citations(urls: Sequence[str], profile: BrandProfile) -> tuple[CitationMatch, ...]:
    """Classify each cited URL against ``profile``'s declared properties.

    Order is preserved: the position an engine gave a source is itself a signal, and the
    competitor path relies on getting exactly the same treatment as the customer's.
    """
    rules = tuple(OwnDomainRule.parse(item) for item in profile.own_domains)
    return tuple(
        _classify(position, raw, rules) for position, raw in enumerate(urls)
    )


def own_citations(matches: Sequence[CitationMatch]) -> tuple[CitationMatch, ...]:
    return tuple(item for item in matches if item.is_own)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _classify(
    position: int, raw: str, rules: Sequence[OwnDomainRule]
) -> CitationMatch:
    destination, wrapper = _unwrap(raw)
    try:
        parsed = normalize_url(destination)
    except UrlNormalizationError as error:
        return CitationMatch(
            position=position,
            raw_url=raw,
            canonical_url="",
            host="",
            domain="",
            ownership=CitationOwnership.UNRESOLVED,
            matched_domain="",
            unwrapped_from=wrapper,
            reason_ko=_MALFORMED_KO.format(code=error.code),
        )

    host = parsed.host
    domain = registrable_domain(host)
    if host in _OPAQUE_REDIRECT_HOSTS:
        return CitationMatch(
            position=position,
            raw_url=raw,
            canonical_url=parsed.canonical,
            host=host,
            domain=domain,
            ownership=CitationOwnership.UNRESOLVED,
            matched_domain="",
            unwrapped_from=wrapper,
            reason_ko=_UNRESOLVED_SHORTENER_KO,
        )

    for rule in rules:
        if rule.covers(host, parsed.path):
            return CitationMatch(
                position=position,
                raw_url=raw,
                canonical_url=parsed.canonical,
                host=host,
                domain=domain,
                ownership=CitationOwnership.OWN,
                matched_domain=rule.host,
                unwrapped_from=wrapper,
                reason_ko=_OWN_KO.format(domain=rule.host),
            )

    return CitationMatch(
        position=position,
        raw_url=raw,
        canonical_url=parsed.canonical,
        host=host,
        domain=domain,
        ownership=CitationOwnership.THIRD_PARTY,
        matched_domain="",
        unwrapped_from=wrapper,
        reason_ko=_THIRD_PARTY_KO,
    )


def _unwrap(raw: str) -> tuple[str, str]:
    """Follow redirect parameters down to the real destination, without any network call.

    Returns ``(destination, wrapper)`` where ``wrapper`` is the original URL when something
    was actually unwrapped, and ``""`` when the input was already the destination.
    """
    current = raw.strip()
    original = current
    unwrapped = False
    for _ in range(_MAX_UNWRAP_HOPS):
        inner = _redirect_target(current)
        if inner is None:
            break
        current = inner
        unwrapped = True
    return current, original if unwrapped else ""


def _redirect_target(url: str) -> str | None:
    try:
        split = urlsplit(url)
    except ValueError:
        return None
    if not split.query:
        return None
    for key, value in parse_qsl(split.query, keep_blank_values=False):
        if key.lower() not in _REDIRECT_PARAMS:
            continue
        candidate = value.strip()
        if not candidate.lower().startswith(("http://", "https://")):
            continue
        if candidate == url:
            return None
        return candidate
    return None
