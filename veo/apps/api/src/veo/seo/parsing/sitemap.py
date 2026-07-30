"""Reading a sitemap without handing an attacker an XML parser.

A sitemap is fetched from the site under diagnosis, so it is untrusted input. The
obvious tool — ``xml.etree.ElementTree`` — resolves entity declarations, and a sitemap
containing nested entities is the classic way to turn a few kilobytes into gigabytes of
memory inside the process reading it.

Extracting ``<loc>`` needs none of that. ``html.parser`` walks the tags without ever
resolving a declaration, so an entity bomb arrives as the literal text ``&b;`` and is
discarded with everything else that is not a URL. It also tolerates the truncated and
mis-nested sitemaps that real sites serve, which a strict XML parser would refuse
outright — and "the sitemap is unreadable" is a finding VEO should report, not an
exception it should raise.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Literal

SitemapKind = Literal["urlset", "sitemapindex", "unknown"]

#: A sitemap may declare 50,000 URLs. Reading every one of them into memory to count
#: them is unnecessary, so the list stops here and ``truncated`` says so.
MAX_LOCATIONS = 5000


@dataclass(frozen=True, slots=True)
class SitemapEntry:
    location: str
    lastmod: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedSitemap:
    kind: SitemapKind
    entries: tuple[SitemapEntry, ...] = ()
    truncated: bool = False

    @property
    def locations(self) -> tuple[str, ...]:
        return tuple(entry.location for entry in self.entries)


#: 확장 네임스페이스가 자기 자원의 주소를 담는 데 쓰는 접두어.
#:
#: `<image:loc>` 은 그 페이지에 **실려 있는 이미지**의 주소이고 `<loc>` 은 **페이지**의
#: 주소다. 둘은 전혀 다른 것인데, 접두어를 떼어 버리면 같아진다. 실제로 그렇게 읽고
#: 있었다 — Jetpack 이미지 사이트맵 하나에서 페이지 26개와 이미지 26개를 합쳐 52개를
#: 전부 페이지 주소로 셌다. 이미지는 HTML 이 아니므로 sitemap URL 검사가 "비정상"
#: 으로 판정하고, **이미지 사이트맵을 제대로 갖춘 사이트가 그 때문에 감점됐다.**
#: 이미지가 페이지보다 많은 사이트맵은 흔하므로, "sitemap 과반 비정상" 상한(55점)이
#: 걸릴 수도 있었다.
EXTENSION_PREFIXES = frozenset({"image", "video", "news", "xhtml", "mobile", "pagemap"})

#: 확장 자원을 감싸는 원소. 이 안의 `<loc>` 은 페이지 주소가 아니다.
EXTENSION_CONTAINERS = frozenset({"image", "video", "news", "pagemap"})

#: 페이지·사이트맵 항목을 감싸는 원소. 이 바로 안의 `<loc>` 만 주소로 인정한다.
LOCATION_PARENTS = frozenset({"url", "sitemap"})


class _SitemapParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.kind: SitemapKind = "unknown"
        self.entries: list[SitemapEntry] = []
        self.truncated = False

        self._in_loc = False
        self._in_lastmod = False
        self._loc_parts: list[str] = []
        self._lastmod_parts: list[str] = []
        self._pending_lastmod: str | None = None
        self._containers: list[str] = []
        """열려 있는 구조 원소만 쌓는다 — 그 밖의 태그는 무시한다.

        전부 쌓으면 닫는 태그가 빠진 사이트맵에서 스택이 어긋나고, 그때 멀쩡한 주소를
        버리게 된다. 실제 사이트가 내보내는 사이트맵은 잘려 있거나 겹쳐 있는 일이
        흔하고, 그것을 읽어 내는 것이 이 모듈이 존재하는 이유다.
        """

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = _local_name(tag)
        if name in EXTENSION_CONTAINERS or name in LOCATION_PARENTS:
            self._containers.append(name)
        if name == "urlset":
            self.kind = "urlset"
        elif name == "sitemapindex":
            self.kind = "sitemapindex"
        elif name == "loc":
            if not self._names_a_page(tag):
                return
            self._in_loc = True
            self._loc_parts = []
        elif name == "lastmod":
            self._in_lastmod = True
            self._lastmod_parts = []
        if name in LOCATION_PARENTS:
            self._pending_lastmod = None

    def _names_a_page(self, tag: str) -> bool:
        """이 `loc` 이 페이지(또는 사이트맵) 주소를 담고 있는가.

        두 겹으로 본다. 접두어가 확장 네임스페이스면 거절하고, 접두어가 없어도 확장
        자원 안에 들어 있으면 거절한다. 한 겹만 두면 접두어를 다르게 쓴 사이트나
        접두어를 생략한 사이트 가운데 한쪽을 놓친다.
        """
        if _prefix(tag) in EXTENSION_PREFIXES:
            return False
        return not (self._containers and self._containers[-1] in EXTENSION_CONTAINERS)

    def handle_endtag(self, tag: str) -> None:
        name = _local_name(tag)
        if self._containers and name == self._containers[-1]:
            self._containers.pop()
        if name == "loc" and self._in_loc:
            self._in_loc = False
            location = "".join(self._loc_parts).strip()
            if location and len(self.entries) < MAX_LOCATIONS:
                self.entries.append(SitemapEntry(location=location, lastmod=self._pending_lastmod))
            elif location:
                self.truncated = True
        elif name == "lastmod" and self._in_lastmod:
            self._in_lastmod = False
            self._pending_lastmod = "".join(self._lastmod_parts).strip() or None
            if self.entries and self.entries[-1].lastmod is None:
                last = self.entries[-1]
                self.entries[-1] = SitemapEntry(
                    location=last.location, lastmod=self._pending_lastmod
                )

    def handle_data(self, data: str) -> None:
        if self._in_loc:
            self._loc_parts.append(data)
        elif self._in_lastmod:
            self._lastmod_parts.append(data)


def _local_name(tag: str) -> str:
    """``sitemap:loc`` and ``loc`` are the same element."""
    return tag.split(":")[-1].lower()


def _prefix(tag: str) -> str:
    """``image:loc`` 의 ``image``. 접두어가 없으면 빈 문자열."""
    prefix, _, local = tag.lower().partition(":")
    return prefix if local else ""


def parse_sitemap(text: str) -> ParsedSitemap:
    """Parse a sitemap or sitemap index. Unreadable input returns ``kind='unknown'``."""
    parser = _SitemapParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception:  # noqa: S110 - unreadable input is a finding, not a crash
        pass
    if parser.kind == "unknown":
        return ParsedSitemap(kind="unknown")
    return ParsedSitemap(
        kind=parser.kind, entries=tuple(parser.entries), truncated=parser.truncated
    )


__all__ = [
    "EXTENSION_CONTAINERS",
    "EXTENSION_PREFIXES",
    "LOCATION_PARENTS",
    "MAX_LOCATIONS",
    "ParsedSitemap",
    "SitemapEntry",
    "SitemapKind",
    "parse_sitemap",
]
