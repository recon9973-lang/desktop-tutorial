"""Synthetic responses for the Google and Naver Search Advisor adapters.

**Every byte in this module is invented.** VEO holds no PageSpeed key, no Search Console
service account and no IndexNow key, so nothing here was captured from a live call. The
hosts are all under ``example.kr``/``example.com`` (RFC 2606), the RSA key is generated at
import time and thrown away with the process, and every identifier says ``synthetic``.
``test_fixtures_are_synthetic.py`` enforces those properties rather than trusting this
docstring.

The response *shapes* follow Google's published documentation. Which fields were taken on
faith is listed in ``providers/google/INTEGRATION_REQUEST.md`` §A — that list is what an
integrator diffs against the first real response.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

HEALTHY_URLS = (
    "https://healthy.example.kr/",
    "https://healthy.example.kr/services/",
    "https://healthy.example.kr/services/laser/",
    "https://healthy.example.kr/contact/",
)

SITE_URL = "https://healthy.example.kr/"


# --------------------------------------------------------------------------- #
# PageSpeed Insights — /pagespeedonline/v5/runPagespeed
# --------------------------------------------------------------------------- #


def lighthouse_audits(
    *,
    lcp_score: float = 0.98,
    cls_score: float = 1.0,
    tbt_score: float = 0.95,
    fcp_score: float = 0.99,
) -> dict[str, Any]:
    return {
        "largest-contentful-paint": {
            "id": "largest-contentful-paint",
            "title": "Largest Contentful Paint",
            "score": lcp_score,
            "scoreDisplayMode": "numeric",
            "displayValue": "1.6 s",
            "numericValue": 1600.0,
            "numericUnit": "millisecond",
        },
        "cumulative-layout-shift": {
            "id": "cumulative-layout-shift",
            "title": "Cumulative Layout Shift",
            "score": cls_score,
            "scoreDisplayMode": "numeric",
            "displayValue": "0.01",
            "numericValue": 0.01,
            "numericUnit": "unitless",
        },
        "total-blocking-time": {
            "id": "total-blocking-time",
            "title": "Total Blocking Time",
            "score": tbt_score,
            "scoreDisplayMode": "numeric",
            "displayValue": "60 ms",
            "numericValue": 60.0,
            "numericUnit": "millisecond",
        },
        "first-contentful-paint": {
            "id": "first-contentful-paint",
            "title": "First Contentful Paint",
            "score": fcp_score,
            "scoreDisplayMode": "numeric",
            "displayValue": "0.9 s",
            "numericValue": 900.0,
            "numericUnit": "millisecond",
        },
    }


def loading_experience(
    *, url: str = SITE_URL, inp_category: str = "FAST", inp_percentile: int = 120
) -> dict[str, Any]:
    """The CrUX block PageSpeed embeds. Note the snake_case keys — that is Google's."""
    return {
        "id": url,
        "metrics": {
            "INTERACTION_TO_NEXT_PAINT": {
                "percentile": inp_percentile,
                "category": inp_category,
                "distributions": [
                    {"min": 0, "max": 200, "proportion": 0.91},
                    {"min": 200, "max": 500, "proportion": 0.07},
                    {"min": 500, "proportion": 0.02},
                ],
            },
            "LARGEST_CONTENTFUL_PAINT_MS": {
                "percentile": 1800,
                "category": "FAST",
                "distributions": [
                    {"min": 0, "max": 2500, "proportion": 0.88},
                    {"min": 2500, "max": 4000, "proportion": 0.09},
                    {"min": 4000, "proportion": 0.03},
                ],
            },
        },
        "overall_category": "FAST",
        "initial_url": url,
    }


def runpagespeed_response(
    *,
    url: str = SITE_URL,
    strategy: str = "mobile",
    with_field_data: bool = True,
    inp_category: str = "FAST",
    **audit_scores: float,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "captchaResult": "CAPTCHA_NOT_NEEDED",
        "kind": "pagespeedonline#result",
        "id": url,
        "analysisUTCTimestamp": "2026-07-28T03:00:00.000Z",
        "lighthouseResult": {
            "requestedUrl": url,
            "finalUrl": url,
            "lighthouseVersion": "11.7.1",
            "fetchTime": "2026-07-28T03:00:00.000Z",
            "configSettings": {"formFactor": strategy, "locale": "ko"},
            "audits": lighthouse_audits(**audit_scores),
            "categories": {"performance": {"id": "performance", "score": 0.97}},
        },
    }
    if with_field_data:
        payload["loadingExperience"] = loading_experience(url=url, inp_category=inp_category)
        payload["originLoadingExperience"] = loading_experience(url=url)
    return payload


# --------------------------------------------------------------------------- #
# CrUX API — /v1/records:queryRecord
# --------------------------------------------------------------------------- #


def crux_query_record_response(*, url: str = SITE_URL, p75_inp: int = 120) -> dict[str, Any]:
    """The standalone CrUX record. It carries percentiles and histograms — no category."""
    return {
        "record": {
            "key": {"url": url},
            "metrics": {
                "interaction_to_next_paint": {
                    "histogram": [
                        {"start": 0, "end": 200, "density": 0.91},
                        {"start": 200, "end": 500, "density": 0.07},
                        {"start": 500, "density": 0.02},
                    ],
                    "percentiles": {"p75": p75_inp},
                },
                "largest_contentful_paint": {
                    "histogram": [
                        {"start": 0, "end": 2500, "density": 0.88},
                        {"start": 2500, "end": 4000, "density": 0.09},
                        {"start": 4000, "density": 0.03},
                    ],
                    "percentiles": {"p75": 1800},
                },
            },
            "collectionPeriod": {
                "firstDate": {"year": 2026, "month": 6, "day": 29},
                "lastDate": {"year": 2026, "month": 7, "day": 26},
            },
        }
    }


def crux_not_found_response() -> dict[str, Any]:
    """What CrUX answers for a URL with too few real-user samples."""
    return {
        "error": {
            "code": 404,
            "message": "chrome ux report data not found",
            "status": "NOT_FOUND",
        }
    }


# --------------------------------------------------------------------------- #
# Search Console
# --------------------------------------------------------------------------- #


def gsc_site_response(*, permission_level: str = "siteOwner") -> dict[str, Any]:
    return {"siteUrl": SITE_URL, "permissionLevel": permission_level}


def gsc_sitemaps_response(*, errors: str = "0", is_pending: bool = False) -> dict[str, Any]:
    return {
        "sitemap": [
            {
                "path": "https://healthy.example.kr/sitemap.xml",
                "lastSubmitted": "2026-07-20T00:00:00.000Z",
                "isPending": is_pending,
                "isSitemapsIndex": False,
                "type": "sitemap",
                "lastDownloaded": "2026-07-27T00:00:00.000Z",
                # int64 fields arrive as JSON strings. That is a documented protobuf
                # convention and the reason these are quoted here.
                "warnings": "0",
                "errors": errors,
                "contents": [{"type": "web", "submitted": "120", "indexed": "118"}],
            }
        ]
    }


#: Clicks, impressions and ctr for one day. ``ctr`` is exactly ``clicks / impressions``,
#: which is the arithmetic that pins the unit as a ratio rather than a percentage.
GSC_PERFORMANCE_ROWS = (
    ("2026-07-24", 41, 1200, 8.4),
    ("2026-07-25", 37, 1150, 8.9),
    ("2026-07-26", 52, 1310, 7.6),
)


def gsc_search_analytics_response() -> dict[str, Any]:
    return {
        "rows": [
            {
                "keys": [day],
                "clicks": clicks,
                "impressions": impressions,
                "ctr": clicks / impressions,
                "position": position,
            }
            for day, clicks, impressions, position in GSC_PERFORMANCE_ROWS
        ],
        "responseAggregationType": "byPage",
    }


def gsc_url_inspection_response(*, verdict: str = "PASS") -> dict[str, Any]:
    return {
        "inspectionResult": {
            "inspectionResultLink": "https://search.google.com/search-console/inspect?synthetic",
            "indexStatusResult": {
                "verdict": verdict,
                "coverageState": (
                    "Submitted and indexed"
                    if verdict == "PASS"
                    else "Crawled - currently not indexed"
                ),
                "robotsTxtState": "ALLOWED",
                "indexingState": "INDEXING_ALLOWED",
                "lastCrawlTime": "2026-07-26T11:00:00Z",
                "pageFetchState": "SUCCESSFUL",
                "googleCanonical": SITE_URL,
                "userCanonical": SITE_URL,
            },
        }
    }


def oauth_token_response(*, expires_in: int = 3599) -> dict[str, Any]:
    return {
        "access_token": "synthetic-access-token",
        "expires_in": expires_in,
        "token_type": "Bearer",
    }


# --------------------------------------------------------------------------- #
# Credentials — generated here, never read from a file or an environment
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=1)
def synthetic_private_key_pem() -> str:
    """A 2048-bit RSA key created in this process and never written to disk."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")


def service_account_json() -> str:
    return json.dumps(
        {
            "type": "service_account",
            "project_id": "synthetic-veo-project",
            "private_key_id": "synthetic-key-id",
            "private_key": synthetic_private_key_pem(),
            "client_email": "synthetic-veo@synthetic-veo-project.iam.gserviceaccount.example.com",
            "client_id": "000000000000000000000",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )


def authorized_user_json() -> str:
    return json.dumps(
        {
            "type": "authorized_user",
            "client_id": "synthetic-client-id.apps.googleusercontent.example.com",
            "client_secret": "synthetic-client-secret",
            "refresh_token": "synthetic-refresh-token",
        }
    )
