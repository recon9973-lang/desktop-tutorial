"""One reading of the target page, shared by every collector.

Each collector is handed the same :class:`~veo.collect.contract.CollectionContext` and
would otherwise parse the same HTML seven times. This module does it once per collector
run and keeps the parsed page, the entity graph and the page kind together, so that the
checks argue about the same document rather than seven slightly different readings of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from veo.collect.contract import CollectionContext, EvidenceRecord
from veo.common.security.fetcher import FetchedDocument
from veo.geo.entity_graph import EntityGraph, build_entity_graph
from veo.geo.pagekind import PageKind, classify
from veo.geo.parsing import PageDocument, parse_html
from veo.geo.reporting import html_evidence


@dataclass(frozen=True, slots=True)
class TargetView:
    context: CollectionContext
    url: str
    path: str
    document: FetchedDocument | None
    page: PageDocument
    graph: EntityGraph
    kind: PageKind
    evidence: tuple[EvidenceRecord, ...]

    @property
    def was_fetched(self) -> bool:
        return self.document is not None

    @property
    def status(self) -> int:
        """The response status, or 0 when nothing was fetched at all."""
        return self.document.status if self.document is not None else 0

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(record.evidence_id for record in self.evidence)

    def header(self, name: str) -> str:
        if self.document is None:
            return ""
        return self.document.headers.get(name.lower(), "")


def build_view(context: CollectionContext) -> TargetView:
    document = context.primary_document or context.document_for(context.target_url)
    markup = document.text() if document is not None else ""
    page = parse_html(markup)
    evidence = (
        (html_evidence(context.target_url, document.body, excerpt=page.title),)
        if document is not None
        else ()
    )
    return TargetView(
        context=context,
        url=context.target_url,
        path=urlparse(context.target_url).path or "/",
        document=document,
        page=page,
        graph=build_entity_graph(page),
        kind=classify(page, context.target_url),
        evidence=evidence,
    )


def parsed_documents(context: CollectionContext) -> dict[str, PageDocument]:
    """Every fetched document, parsed. Used by the site-scope checks."""
    return {url: parse_html(doc.text()) for url, doc in context.documents.items()}


__all__ = ["TargetView", "build_view", "parsed_documents"]
