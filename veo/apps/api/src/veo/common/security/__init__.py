"""Security primitives shared by every VEO surface that touches the outside world."""

from veo.common.security.limits import (
    ContentTypeNotAllowedError,
    DecompressionLimitError,
    FetchLimitError,
    FetchLimits,
    FetchTimeoutError,
    ResponseBudget,
    ResponseTooLargeError,
    enforce_async_stream,
    enforce_stream,
)
from veo.common.security.url_guard import (
    DEFAULT_POLICY,
    HostResolutionError,
    HostResolver,
    IpBlockCategory,
    UrlDecision,
    UrlGuard,
    UrlGuardPolicy,
    UrlRejectedError,
    UrlRejectionReason,
    classify_ip,
    system_resolver,
)

__all__ = [
    "DEFAULT_POLICY",
    "ContentTypeNotAllowedError",
    "DecompressionLimitError",
    "FetchLimitError",
    "FetchLimits",
    "FetchTimeoutError",
    "HostResolutionError",
    "HostResolver",
    "IpBlockCategory",
    "ResponseBudget",
    "ResponseTooLargeError",
    "UrlDecision",
    "UrlGuard",
    "UrlGuardPolicy",
    "UrlRejectedError",
    "UrlRejectionReason",
    "classify_ip",
    "enforce_async_stream",
    "enforce_stream",
    "system_resolver",
]
