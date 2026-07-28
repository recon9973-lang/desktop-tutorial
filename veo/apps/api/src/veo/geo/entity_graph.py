"""JSON-LD read as a graph of entities, not as a checklist of script tags.

The question a GEO diagnosis has to answer is not "is there structured data" — plenty of
sites emit a valid ``Organization`` block that connects to nothing and states a name the
page never shows. It is whether the declared entities *hang together*: do they carry
stable ``@id`` values, do those values link the nodes to one another, is there an
official-profile trail through ``sameAs``, and do name, url, logo, telephone and address
agree with what a reader sees.

Parsing is deliberately forgiving. Broken JSON is recorded and reported, never raised:
a syntax error is a finding about the site, not a crash in the diagnostic.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from veo.geo.parsing import PageDocument, normalise

#: Types that stand for "the business behind this site".
ORGANIZATION_MARKERS = (
    "organization",
    "business",
    "corporation",
    "company",
    "clinic",
    "dentist",
    "hospital",
    "physician",
    "medical",
    "store",
    "shop",
    "restaurant",
    "agency",
    "school",
    "ngo",
    "practice",
    "brand",
)

#: Properties whose value is another entity rather than a literal.
REFERENCE_PROPERTIES = (
    "about",
    "author",
    "brand",
    "creator",
    "editor",
    "isPartOf",
    "itemReviewed",
    "mainEntity",
    "mainEntityOfPage",
    "manufacturer",
    "parentOrganization",
    "provider",
    "publisher",
    "reviewedBy",
    "seller",
    "subOrganization",
)

#: Values a reader can check against the page with their own eyes.
CHECKABLE_PROPERTIES = (
    "name",
    "legalName",
    "headline",
    "telephone",
    "price",
    "ratingValue",
    "reviewCount",
    "streetAddress",
    "addressLocality",
)

_ADDRESS_PARTS = (
    "streetAddress",
    "addressLocality",
    "addressRegion",
    "postalCode",
)


@dataclass(frozen=True, slots=True)
class SchemaClaim:
    """One declared value a human could verify by reading the page."""

    property_name: str
    value: str
    node_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityNode:
    node_id: str
    types: tuple[str, ...]
    name: str
    url: str
    logo: str
    telephone: str
    address_text: str
    same_as: tuple[str, ...]
    references: tuple[str, ...]
    raw: Mapping[str, Any]

    @property
    def is_organization(self) -> bool:
        lowered = " ".join(self.types).lower()
        return any(marker in lowered for marker in ORGANIZATION_MARKERS)

    def claims(self) -> tuple[SchemaClaim, ...]:
        found: list[SchemaClaim] = []
        for prop in CHECKABLE_PROPERTIES:
            value = _literal(self.raw.get(prop))
            if not value and prop in _ADDRESS_PARTS:
                value = _literal(_as_mapping(self.raw.get("address")).get(prop))
            if not value:
                value = _nested_offer_value(self.raw, prop)
            if not value:
                value = _literal(_as_mapping(self.raw.get("aggregateRating")).get(prop))
            if value:
                found.append(SchemaClaim(prop, value, self.types))
        return tuple(found)


@dataclass(frozen=True, slots=True)
class GraphCoherence:
    """How well the declared entities connect to one another."""

    node_count: int
    nodes_with_ids: int
    referenced_ids: tuple[str, ...]
    orphan_ids: tuple[str, ...]
    unresolved_references: tuple[str, ...]

    @property
    def every_node_is_identified(self) -> bool:
        return self.node_count > 0 and self.nodes_with_ids == self.node_count


@dataclass(frozen=True, slots=True)
class EntityGraph:
    nodes: tuple[EntityNode, ...] = ()
    parse_errors: tuple[str, ...] = ()
    block_count: int = 0

    @property
    def has_structured_data(self) -> bool:
        return self.block_count > 0

    def declared_types(self) -> tuple[str, ...]:
        seen: list[str] = []
        for node in self.nodes:
            for node_type in node.types:
                if node_type not in seen:
                    seen.append(node_type)
        return tuple(seen)

    def primary_organization(self) -> EntityNode | None:
        for node in self.nodes:
            if node.is_organization:
                return node
        return None

    def claims(self) -> tuple[SchemaClaim, ...]:
        return tuple(claim for node in self.nodes for claim in node.claims())

    def coherence(self) -> GraphCoherence:
        identified = {node.node_id for node in self.nodes if node.node_id}
        referenced: set[str] = set()
        for node in self.nodes:
            referenced.update(node.references)

        orphans = [
            node.node_id
            for node in self.nodes
            if node.node_id
            and node.node_id not in referenced
            and not [ref for ref in node.references if ref in identified]
        ]
        unresolved = sorted(ref for ref in referenced if ref not in identified)

        return GraphCoherence(
            node_count=len(self.nodes),
            nodes_with_ids=len(identified),
            referenced_ids=tuple(sorted(referenced)),
            orphan_ids=tuple(sorted(orphans)),
            unresolved_references=tuple(unresolved),
        )


def build_entity_graph(page: PageDocument) -> EntityGraph:
    """Read every JSON-LD block on the page into one graph."""
    nodes: list[EntityNode] = []
    errors: list[str] = []

    for index, block in enumerate(page.json_ld_blocks):
        text = block.strip()
        if not text:
            errors.append(f"block {index}: 빈 JSON-LD 블록입니다.")
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"block {index}: {exc.msg} (line {exc.lineno})")
            continue
        for item in _top_level_objects(payload):
            nodes.append(_build_node(item))

    return EntityGraph(
        nodes=tuple(nodes), parse_errors=tuple(errors), block_count=len(page.json_ld_blocks)
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _top_level_objects(payload: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from _top_level_objects(item)
        return
    if not isinstance(payload, dict):
        return
    graph = payload.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            yield from _top_level_objects(item)
        return
    yield payload


def _build_node(item: Mapping[str, Any]) -> EntityNode:
    address = _as_mapping(item.get("address"))
    address_text = normalise(
        " ".join(_literal(address.get(part)) for part in _ADDRESS_PARTS)
    ) or _literal(item.get("address"))

    return EntityNode(
        node_id=_literal(item.get("@id")),
        types=_types(item.get("@type")),
        name=_literal(item.get("name")) or _literal(item.get("legalName")),
        url=_literal(item.get("url")),
        logo=_literal(item.get("logo")) or _literal(_as_mapping(item.get("logo")).get("url")),
        telephone=_literal(item.get("telephone")),
        address_text=address_text,
        same_as=_string_list(item.get("sameAs")),
        references=_references(item),
        raw=dict(item),
    )


def _references(item: Mapping[str, Any]) -> tuple[str, ...]:
    found: list[str] = []
    for prop in REFERENCE_PROPERTIES:
        value = item.get(prop)
        for candidate in value if isinstance(value, list) else [value]:
            if isinstance(candidate, dict) and (target := _literal(candidate.get("@id"))):
                found.append(target)
            elif isinstance(candidate, str) and candidate.startswith(("http", "#")):
                found.append(candidate)
    return tuple(found)


def _types(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(v for v in value if isinstance(v, str))
    return ()


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(v for v in value if isinstance(v, str))
    return ()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _literal(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def _nested_offer_value(item: Mapping[str, Any], prop: str) -> str:
    offers = item.get("offers")
    for candidate in offers if isinstance(offers, list) else [offers]:
        if isinstance(candidate, dict) and (value := _literal(candidate.get(prop))):
            return value
    return ""


__all__ = [
    "CHECKABLE_PROPERTIES",
    "ORGANIZATION_MARKERS",
    "EntityGraph",
    "EntityNode",
    "GraphCoherence",
    "SchemaClaim",
    "build_entity_graph",
]
