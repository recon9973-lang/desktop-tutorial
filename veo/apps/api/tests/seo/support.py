"""Turning a fixture directory into a :class:`CollectionContext`, with no network.

Every SEO test starts here. The fixtures under ``tests/fixtures/seo`` are real HTML
files plus a small manifest describing what the crawler saw — status codes, headers,
redirect chains, URL importance — because those are facts that cannot live inside the
HTML itself.

Nothing in this module decides anything about SEO. It only replays a crawl.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from veo.collect.contract import CollectionContext, CollectionResult
from veo.common.security.fetcher import FetchedDocument, FetchHop
from veo.contracts.enums import ProviderState
from veo.scoring import CheckOutcome, CheckStatus, ScoringSpec, latest_published

FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "seo"

SPEC: ScoringSpec = latest_published("veo.seo.readiness")

#: Every provider key the SEO collectors read, switched off. The default state of the
#: product: no credentials, so every provider-backed check must answer UNKNOWN.
ALL_PROVIDERS_DISABLED: Mapping[str, ProviderState] = {
    "GOOGLE_PAGESPEED": ProviderState.DISABLED_NO_CREDENTIAL,
    "GOOGLE_CRUX": ProviderState.DISABLED_NO_CREDENTIAL,
    "GOOGLE_SEARCH_CONSOLE": ProviderState.DISABLED_NO_CREDENTIAL,
    "NAVER_SEARCH_ADVISOR": ProviderState.DISABLED_NO_CREDENTIAL,
    "INDEXNOW": ProviderState.DISABLED_NO_CREDENTIAL,
    "BACKLINK_INDEX": ProviderState.DISABLED_NO_CREDENTIAL,
    "BRAND_MENTIONS": ProviderState.DISABLED_NO_CREDENTIAL,
}


@dataclass(frozen=True, slots=True)
class Fixture:
    """A loaded fixture site, kept around so a test can tweak one field and reload."""

    name: str
    manifest: dict[str, Any]
    root: Path

    def page_urls(self) -> tuple[str, ...]:
        return tuple(str(page["url"]) for page in self.manifest["pages"])


def load_manifest(name: str) -> Fixture:
    root = FIXTURE_ROOT / name
    manifest = json.loads((root / "site.json").read_text(encoding="utf-8"))
    return Fixture(name=name, manifest=manifest, root=root)


def _document(root: Path, page: Mapping[str, Any]) -> FetchedDocument:
    url = str(page["url"])
    file_name = page.get("file")
    body = (root / str(file_name)).read_bytes() if file_name else b""
    status = int(page.get("status", 200))
    headers = {str(k).lower(): str(v) for k, v in dict(page.get("headers", {})).items()}

    raw_hops = page.get("hops")
    if raw_hops:
        hops = tuple(
            FetchHop(
                url=str(hop["url"]),
                status=int(hop["status"]),
                resolved_ip="203.0.113.10",
                location=hop.get("location"),
                elapsed_ms=12,
            )
            for hop in raw_hops
        )
        requested = hops[0].url
    else:
        hops = (
            FetchHop(
                url=url, status=status, resolved_ip="203.0.113.10", location=None, elapsed_ms=12
            ),
        )
        requested = url

    return FetchedDocument(
        requested_url=requested,
        final_url=url,
        status=status,
        headers=headers,
        body=body,
        content_hash=hashlib.sha256(body).hexdigest(),
        content_type="text/html",
        charset="utf-8",
        hops=hops,
        resolved_ips=("203.0.113.10",),
        fetched_at=datetime(2026, 7, 28, 3, 0, tzinfo=UTC),
        elapsed_ms=140,
        tls_expires_at=_expiry(page),
    )


def _expiry(page: Mapping[str, Any]) -> datetime | None:
    """픽스처의 인증서 만료일.

    고정 날짜를 적으면 그 날이 지나는 순간 테스트가 깨진다. 매니페스트에는 **수집 시각
    기준 남은 일수**를 적고 여기서 시각으로 옮긴다 — 픽스처가 시간이 지나도 같은 뜻을
    유지하게 하려는 것이다. 적지 않은 페이지는 만료일을 못 받은 상태이고, 그것은
    통과가 아니라 측정 불가로 보고된다.
    """
    days = page.get("tls_expires_in_days")
    if days is None:
        return None
    return datetime(2026, 7, 28, 3, 0, tzinfo=UTC) + timedelta(days=float(days))


def build_context(
    name: str,
    *,
    provider_states: Mapping[str, ProviderState] | None = None,
    provider_payloads: Mapping[str, object] | None = None,
    with_rendered: bool = True,
    spec: ScoringSpec | None = None,
) -> CollectionContext:
    """Replay the crawl recorded in ``tests/fixtures/seo/<name>``."""
    fixture = load_manifest(name)
    root, manifest = fixture.root, fixture.manifest

    documents: dict[str, FetchedDocument] = {}
    rendered: dict[str, str] = {}
    importance: dict[str, str] = {}

    for page in manifest["pages"]:
        url = str(page["url"])
        documents[url] = _document(root, page)
        importance[url] = str(page.get("importance", "CONTENT_OR_PRODUCT"))
        rendered_file = page.get("rendered")
        if with_rendered and rendered_file:
            rendered[url] = (root / str(rendered_file)).read_text(encoding="utf-8")

    robots_name = manifest.get("robots")
    robots_txt = (root / str(robots_name)).read_text(encoding="utf-8") if robots_name else None

    sitemaps = {
        str(sitemap_url): (root / str(file_name)).read_text(encoding="utf-8")
        for sitemap_url, file_name in dict(manifest.get("sitemaps", {})).items()
    }

    primary_url = str(manifest.get("primary_url", manifest["target_url"]))

    return CollectionContext(
        target_url=str(manifest["target_url"]),
        spec=spec or SPEC,
        documents=documents,
        primary_document=documents.get(primary_url),
        robots_txt=robots_txt,
        sitemap_documents=sitemaps,
        rendered_dom=rendered,
        provider_states=dict(provider_states or ALL_PROVIDERS_DISABLED),
        provider_payloads=dict(provider_payloads or {}),
        url_importance=importance,
        locale=str(manifest.get("locale", "ko-KR")),
        collected_at=datetime(2026, 7, 28, 3, 5, tzinfo=UTC),
    )


def by_id(result: CollectionResult) -> dict[str, CheckOutcome]:
    return {outcome.check_id: outcome for outcome in result.outcomes}


def status_of(result: CollectionResult, check_id: str) -> CheckStatus:
    return by_id(result)[check_id].status


def issues_for(result: CollectionResult, check_id: str) -> tuple[Any, ...]:
    return tuple(issue for issue in result.issues if issue.check_id == check_id)


def scan_bundle(**overrides: Any) -> dict[str, Any]:
    """The ``POST /seo/scan`` request body for the healthy fixture.

    The router takes a pre-collected bundle rather than a URL, so a test that exercises
    the API boundary has to hand it the same pages ``build_context`` would replay.
    """
    root = FIXTURE_ROOT / "healthy"
    body: dict[str, Any] = {
        "target_url": "https://healthy.example.kr/",
        "locale": "ko-KR",
        "robots_txt": (root / "robots.txt").read_text(encoding="utf-8"),
        "sitemaps": {
            "https://healthy.example.kr/sitemap.xml": (root / "sitemap.xml").read_text(
                encoding="utf-8"
            )
        },
        "pages": [
            {
                "url": "https://healthy.example.kr/",
                "status": 200,
                "importance": "CONVERSION_OR_HOME",
                "html": (root / "pages" / "index.html").read_text(encoding="utf-8"),
                "rendered_dom": (root / "rendered" / "index.html").read_text(encoding="utf-8"),
            },
            {
                "url": "https://healthy.example.kr/services/",
                "status": 200,
                "importance": "CATEGORY_OR_HUB",
                "html": (root / "pages" / "services.html").read_text(encoding="utf-8"),
            },
            {
                "url": "https://healthy.example.kr/services/laser/",
                "status": 200,
                "importance": "CONTENT_OR_PRODUCT",
                "html": (root / "pages" / "services-laser.html").read_text(encoding="utf-8"),
            },
            {
                "url": "https://healthy.example.kr/contact/",
                "status": 200,
                "importance": "CONVERSION_OR_HOME",
                "html": (root / "pages" / "contact.html").read_text(encoding="utf-8"),
            },
        ],
    }
    body.update(overrides)
    return body


# --------------------------------------------------------------------------- #
# Provider payloads used by the "credential present" half of the tests
# --------------------------------------------------------------------------- #


def healthy_provider_payloads(urls: tuple[str, ...]) -> dict[str, object]:
    """Payloads shaped as the collectors expect, all reporting a healthy site."""
    return {
        "GOOGLE_PAGESPEED": {
            url: {
                "lighthouse": {
                    "largest-contentful-paint": {"score": 0.98, "display_value": "1.6초"},
                    "cumulative-layout-shift": {"score": 1.0, "display_value": "0.01"},
                    "total-blocking-time": {"score": 0.95, "display_value": "60밀리초"},
                }
            }
            for url in urls
        },
        "GOOGLE_CRUX": {
            url: {
                "metrics": {
                    "INTERACTION_TO_NEXT_PAINT": {"category": "FAST", "percentile": 120}
                }
            }
            for url in urls
        },
        "GOOGLE_SEARCH_CONSOLE": {
            "site": {"verified": True, "permission_level": "siteOwner"},
            "sitemaps": [
                {
                    "path": "https://healthy.example.kr/sitemap.xml",
                    "is_pending": False,
                    "errors": 0,
                    "warnings": 0,
                    "last_downloaded": "2026-07-27T00:00:00+00:00",
                }
            ],
            "performance": {
                "rows": 412,
                "impressions": 15200,
                "date_range_end": "2026-07-26T00:00:00+00:00",
            },
            "index_coverage": {"indexed": 120, "previous_indexed": 118, "excluded": 3},
        },
        "NAVER_SEARCH_ADVISOR": {
            "site_registered": True,
            "ownership_verified": True,
            "sitemap_submitted": True,
        },
        "INDEXNOW": {"configured": True, "key_location": "https://healthy.example.kr/veo.txt"},
        "BACKLINK_INDEX": {
            "referring_domains": 63,
            "spam_flagged_domains": 0,
            "sampled_domains": 63,
        },
        "BRAND_MENTIONS": {
            "canonical_name": "온담의원",
            "observed_names": ["온담의원", "온담의원"],
            "sources_checked": 4,
        },
    }


ALL_PROVIDERS_ENABLED: Mapping[str, ProviderState] = dict.fromkeys(
    ALL_PROVIDERS_DISABLED, ProviderState.ENABLED
)
