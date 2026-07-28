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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = _local_name(tag)
        if name == "urlset":
            self.kind = "urlset"
        elif name == "sitemapindex":
            self.kind = "sitemapindex"
        elif name == "loc":
            self._in_loc = True
            self._loc_parts = []
        elif name == "lastmod":
            self._in_lastmod = True
            self._lastmod_parts = []
        elif name in {"url", "sitemap"}:
            self._pending_lastmod = None

    def handle_endtag(self, tag: str) -> None:
        name = _local_name(tag)
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


__all__ = ["MAX_LOCATIONS", "ParsedSitemap", "SitemapEntry", "SitemapKind", "parse_sitemap"]
