"""Cross-cutting utilities shared by the API and the worker.

Nothing in here knows about SEO, GEO or Naver. If a module in ``veo.common`` needs to
import from a feature package, it belongs in that feature package instead.

The security-critical entry point is :mod:`veo.common.security.url_guard`: VEO fetches
URLs supplied by anonymous callers, and that module is the only thing standing between
those URLs and our internal network.
"""

from veo.common.urls import (
    HostForm,
    NormalizedUrl,
    UrlNormalizationError,
    canonical_url,
    normalize_url,
    resolve_reference,
)

__all__ = [
    "HostForm",
    "NormalizedUrl",
    "UrlNormalizationError",
    "canonical_url",
    "normalize_url",
    "resolve_reference",
]
