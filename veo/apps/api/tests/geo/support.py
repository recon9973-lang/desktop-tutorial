"""Turn a fixture directory under ``tests/fixtures/geo`` into a ``CollectionContext``.

No test in this package touches the network. Everything a GEO collector may read —
documents, robots.txt, sitemaps, the rendered DOM, provider payloads — arrives from disk
through this loader, which is exactly the shape the real crawl pipeline will hand over.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import FetchedDocument
from veo.contracts.enums import ProviderState
from veo.scoring import ScoringSpec, latest_published

FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "geo"

#: Placeholder a fixture may use where a content hash would otherwise have to be
#: hard-coded. Replaced with the real digest of the primary document's bytes, which is
#: how "the date moved but the bytes did not" stays true when the fixture is edited.
CURRENT_HASH_TOKEN = "$CURRENT"

SPEC_ID = "veo.geo.readiness"


def geo_spec() -> ScoringSpec:
    return latest_published(SPEC_ID)


@dataclass(frozen=True, slots=True)
class GeoCase:
    name: str
    purpose_ko: str
    context: CollectionContext


def case_names() -> list[str]:
    return sorted(p.name for p in FIXTURE_ROOT.iterdir() if (p / "case.json").is_file())


def iter_cases() -> Iterator[GeoCase]:
    for name in case_names():
        yield load_case(name)


def load_case(name: str, *, spec: ScoringSpec | None = None) -> GeoCase:
    directory = FIXTURE_ROOT / name
    manifest: dict[str, Any] = json.loads((directory / "case.json").read_text(encoding="utf-8"))
    collected_at = datetime.fromisoformat(manifest["collected_at"])

    documents: dict[str, FetchedDocument] = {}
    primary: FetchedDocument | None = None
    for entry in manifest["documents"]:
        document = _build_document(directory, entry, collected_at)
        documents[document.final_url] = document
        if entry.get("primary"):
            primary = document

    payloads = _load_payloads(directory, manifest, primary)

    context = CollectionContext(
        target_url=manifest["target_url"],
        spec=spec or geo_spec(),
        documents=documents,
        primary_document=primary,
        robots_txt=_read_optional(directory, manifest.get("robots_txt_file")),
        sitemap_documents={
            url: _read_required(directory, path)
            for url, path in manifest.get("sitemap_documents", {}).items()
        },
        rendered_dom={
            url: _read_required(directory, path)
            for url, path in manifest.get("rendered_dom", {}).items()
        },
        provider_states={
            name: ProviderState(value)
            for name, value in manifest.get("provider_states", {}).items()
        },
        provider_payloads=payloads,
        url_importance=manifest.get("url_importance", {}),
        collected_at=collected_at,
    )
    return GeoCase(name=manifest["name"], purpose_ko=manifest["purpose_ko"], context=context)


def replace_robots(case: GeoCase, robots_txt: str | None) -> GeoCase:
    """The same case with a different robots.txt and nothing else changed."""
    from dataclasses import replace

    return GeoCase(
        name=f"{case.name}+robots",
        purpose_ko=case.purpose_ko,
        context=replace(case.context, robots_txt=robots_txt),
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _build_document(
    directory: Path, entry: Mapping[str, Any], collected_at: datetime
) -> FetchedDocument:
    body = (directory / entry["file"]).resolve().read_bytes()
    headers = {k.lower(): v for k, v in entry.get("headers", {}).items()}
    content_type = headers.get("content-type", "text/html; charset=utf-8")
    url = entry["url"]
    return FetchedDocument(
        requested_url=url,
        final_url=url,
        status=int(entry.get("status", 200)),
        headers=headers,
        body=body,
        content_hash=hashlib.sha256(body).hexdigest(),
        content_type=content_type.split(";", 1)[0].strip().lower(),
        charset="utf-8",
        hops=(),
        resolved_ips=("203.0.113.10",),
        fetched_at=collected_at,
        elapsed_ms=120,
    )


def _load_payloads(
    directory: Path, manifest: Mapping[str, Any], primary: FetchedDocument | None
) -> dict[str, object]:
    path = manifest.get("provider_payloads_file")
    if not path:
        return {}
    raw = (directory / path).resolve().read_text(encoding="utf-8")
    if primary is not None:
        raw = raw.replace(CURRENT_HASH_TOKEN, primary.content_hash)
    payloads: dict[str, object] = json.loads(raw)
    return payloads


def _read_optional(directory: Path, path: str | None) -> str | None:
    if not path:
        return None
    return _read_required(directory, path)


def _read_required(directory: Path, path: str) -> str:
    return (directory / path).resolve().read_text(encoding="utf-8")
