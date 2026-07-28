"""One parse of the crawl, shared by all eight collectors.

Parsing the same four pages eight times would be wasteful, but the real reason this
exists is consistency: if each collector normalised URLs its own way, a link would look
broken to one collector and fine to another, and the two findings would contradict each
other in the same report.

Nothing here judges anything. It answers "what is on the page" and "what points at
what"; the collectors decide what that means, and only the evaluator turns it into a
number.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from veo.collect.contract import CollectionContext, EvidenceRecord
from veo.common.security.fetcher import FetchedDocument
from veo.seo.parsing import (
    ParsedPage,
    ParsedSitemap,
    RobotsFile,
    normalise_url,
    parse_html,
    parse_robots,
    parse_sitemap,
    resolve,
    same_site,
)

#: URL importance classes that make a page worth a customer's attention. Tag and filter
#: pages, and pages deliberately kept out of the index, are excluded from the site-wide
#: "is this reachable / is this substantial" questions.
KEY_IMPORTANCE = frozenset({"CONVERSION_OR_HOME", "CATEGORY_OR_HUB", "CONTENT_OR_PRODUCT"})

FALLBACK_IMPORTANCE = "CONTENT_OR_PRODUCT"


@dataclass(frozen=True, slots=True)
class PageObservation:
    """One crawled URL, parsed once."""

    url: str
    document: FetchedDocument
    raw: ParsedPage
    rendered: ParsedPage | None
    importance: str
    importance_value: float
    """How much this URL counts towards a site-wide coverage ratio, from the
    specification's ``url_importance`` table. Never a score."""

    @property
    def status(self) -> int:
        return self.document.status

    @property
    def is_ok(self) -> bool:
        return 200 <= self.document.status < 300

    @property
    def is_key(self) -> bool:
        return self.importance in KEY_IMPORTANCE

    @property
    def effective(self) -> ParsedPage:
        """What a browser ended up showing — the rendered DOM when one exists.

        Used only where the browser's view is the right question. Anything about what a
        crawler can see without executing JavaScript must read :attr:`raw` explicitly.
        """
        return self.rendered or self.raw

    def header(self, name: str) -> str | None:
        return self.document.headers.get(name.lower())


@dataclass(frozen=True, slots=True)
class SiteObservation:
    """The whole crawl, parsed and cross-referenced."""

    context: CollectionContext
    pages: tuple[PageObservation, ...]
    entry_url: str
    robots: RobotsFile | None
    sitemaps: Mapping[str, ParsedSitemap]
    outbound: Mapping[str, tuple[str, ...]]
    """Internal, crawled targets each page links to, deduplicated and self excluded."""
    inbound: Mapping[str, tuple[str, ...]]
    broken_targets: Mapping[str, tuple[str, ...]]
    """Crawled 4xx/5xx URLs, mapped to the pages that link to them."""
    click_depth: Mapping[str, int]
    by_url: Mapping[str, PageObservation] = field(default_factory=dict)

    def page(self, url: str) -> PageObservation | None:
        return self.by_url.get(normalise_url(url))

    @property
    def has_pages(self) -> bool:
        return bool(self.pages)

    @property
    def key_pages(self) -> tuple[PageObservation, ...]:
        return tuple(page for page in self.pages if page.is_key)

    @property
    def sitemap_locations(self) -> tuple[str, ...]:
        seen: list[str] = []
        for sitemap in self.sitemaps.values():
            for location in sitemap.locations:
                normalised = normalise_url(location)
                if normalised not in seen:
                    seen.append(normalised)
        return tuple(seen)

    def is_korean_market(self) -> bool:
        return self.context.locale.lower().startswith("ko")


def build_observation(context: CollectionContext) -> SiteObservation:
    """Parse everything in ``context`` exactly once."""
    entry_url = normalise_url(context.target_url)

    importance_table = {
        str(name): float(value) for name, value in context.spec.url_importance.items()
    }
    rendered_source = {normalise_url(url): html for url, html in context.rendered_dom.items()}

    pages: list[PageObservation] = []
    for raw_url, document in context.documents.items():
        url = normalise_url(document.final_url or raw_url)
        importance = str(context.url_importance.get(raw_url, FALLBACK_IMPORTANCE))
        if importance not in importance_table:
            importance = FALLBACK_IMPORTANCE
        rendered_html = rendered_source.get(url)
        pages.append(
            PageObservation(
                url=url,
                document=document,
                raw=parse_html(document.body, charset=document.charset),
                rendered=parse_html(rendered_html) if rendered_html is not None else None,
                importance=importance,
                importance_value=importance_table.get(importance, 1.0),
            )
        )

    pages.sort(key=lambda page: page.url)
    by_url = {page.url: page for page in pages}

    outbound, inbound, broken = _link_graph(pages, by_url)
    depth = _click_depth(entry_url, outbound, by_url)

    robots = parse_robots(context.robots_txt) if context.robots_txt is not None else None
    sitemaps = {url: parse_sitemap(text) for url, text in context.sitemap_documents.items()}

    return SiteObservation(
        context=context,
        pages=tuple(pages),
        entry_url=entry_url,
        robots=robots,
        sitemaps=sitemaps,
        outbound=outbound,
        inbound=inbound,
        broken_targets=broken,
        click_depth=depth,
        by_url=by_url,
    )


def _link_graph(
    pages: tuple[PageObservation, ...] | list[PageObservation],
    by_url: Mapping[str, PageObservation],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    outbound: dict[str, list[str]] = {page.url: [] for page in pages}
    inbound: dict[str, list[str]] = {page.url: [] for page in pages}
    broken: dict[str, list[str]] = {}

    for page in pages:
        for anchor in page.raw.links:
            target = resolve(page.url, anchor.href)
            if target is None or not same_site(page.url, target):
                continue
            destination = by_url.get(target)
            if destination is None:
                continue
            if not destination.is_ok:
                broken.setdefault(target, [])
                if page.url not in broken[target]:
                    broken[target].append(page.url)
                continue
            if target == page.url:
                continue
            if target not in outbound[page.url]:
                outbound[page.url].append(target)
            if page.url not in inbound[target]:
                inbound[target].append(page.url)

    return (
        {url: tuple(targets) for url, targets in outbound.items()},
        {url: tuple(sources) for url, sources in inbound.items()},
        {url: tuple(sources) for url, sources in broken.items()},
    )


def _click_depth(
    entry_url: str,
    outbound: Mapping[str, tuple[str, ...]],
    by_url: Mapping[str, PageObservation],
) -> dict[str, int]:
    """Breadth-first distance from the entry URL. Unreachable pages are absent."""
    if entry_url not in by_url:
        return {}
    depth = {entry_url: 0}
    queue = [entry_url]
    while queue:
        current = queue.pop(0)
        for target in outbound.get(current, ()):
            if target in depth:
                continue
            depth[target] = depth[current] + 1
            queue.append(target)
    return depth


def evidence_for_document(document: FetchedDocument, kind: str, excerpt: str) -> EvidenceRecord:
    """An evidence record tied to one fetched document."""
    return EvidenceRecord.of(
        kind,
        url=document.final_url,
        payload=document.body or document.final_url.encode("utf-8"),
        excerpt=excerpt,
        collected_at=document.fetched_at,
        detail={"status": document.status, "content_hash": document.content_hash},
    )


__all__ = [
    "FALLBACK_IMPORTANCE",
    "KEY_IMPORTANCE",
    "PageObservation",
    "SiteObservation",
    "build_observation",
    "evidence_for_document",
]
