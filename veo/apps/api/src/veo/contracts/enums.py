"""Shared vocabulary for the whole VEO platform.

Owned by the integration maintainer. Feature workers read these; they do not edit them.
Every value here is mirrored in ``packages/shared-types`` and asserted by a contract test.
"""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle of a long-running analysis job.

    Long work never runs inside a synchronous request. ``PARTIAL_SUCCESS`` exists because
    a scan that collected 80% of its pages is more useful — and more honest — than one
    reported as a flat failure.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


TERMINAL_JOB_STATUSES = frozenset(
    {
        JobStatus.PARTIAL_SUCCESS,
        JobStatus.SUCCEEDED,
        JobStatus.FAILED_FINAL,
        JobStatus.CANCELLED,
        JobStatus.EXPIRED,
    }
)


class JobType(StrEnum):
    SEO_SCAN = "SEO_SCAN"
    GEO_READINESS_SCAN = "GEO_READINESS_SCAN"
    GEO_OBSERVATION_RUN = "GEO_OBSERVATION_RUN"
    KEYWORD_LOOKUP = "KEYWORD_LOOKUP"
    SITE_CRAWL = "SITE_CRAWL"
    COMPETITOR_COMPARISON = "COMPETITOR_COMPARISON"
    REPORT_EXPORT = "REPORT_EXPORT"
    REVERIFICATION = "REVERIFICATION"


class CancellationReason(StrEnum):
    """Why a job stopped early.

    Deliberately a closed set. Forwarding a provider's error text as a cancellation
    reason is a well-trodden way to leak credentials and internal hostnames to customers.
    """

    USER_REQUESTED = "USER_REQUESTED"
    SUPERSEDED_BY_NEWER_RUN = "SUPERSEDED_BY_NEWER_RUN"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    TARGET_UNREACHABLE = "TARGET_UNREACHABLE"
    SHUTDOWN = "SHUTDOWN"
    EXPIRED = "EXPIRED"


class ScanScope(StrEnum):
    SINGLE_URL = "SINGLE_URL"
    SITE = "SITE"


class Surface(StrEnum):
    """Which product surface requested the work. Limits and retention differ."""

    PUBLIC = "PUBLIC"
    CONSOLE = "CONSOLE"


class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    LAB_ADMIN = "LAB_ADMIN"
    ANALYST = "ANALYST"
    DEVELOPER = "DEVELOPER"
    SALES_VIEWER = "SALES_VIEWER"
    CLIENT_VIEWER = "CLIENT_VIEWER"


class DataSource(StrEnum):
    """Where a number came from. Never blend these in a single figure.

    ``NAVER_SEARCH_AD`` carries absolute monthly search counts from the official API.
    ``NAVER_DATALAB`` carries a *relative* interest index — it is not a count of searches
    and must never be rendered as one.
    """

    NAVER_SEARCH_AD = "NAVER_SEARCH_AD"
    NAVER_DATALAB = "NAVER_DATALAB"
    NAVER_SEARCH_API = "NAVER_SEARCH_API"
    GOOGLE_SEARCH_CONSOLE = "GOOGLE_SEARCH_CONSOLE"
    GOOGLE_PAGESPEED = "GOOGLE_PAGESPEED"
    GOOGLE_CRUX = "GOOGLE_CRUX"
    BING_WEBMASTER = "BING_WEBMASTER"
    AI_ENGINE_OBSERVATION = "AI_ENGINE_OBSERVATION"
    VEO_CRAWLER = "VEO_CRAWLER"
    VEO_INTERNAL = "VEO_INTERNAL"
    CALCULATED = "CALCULATED"


class ProviderState(StrEnum):
    """Availability of an external provider.

    ``DISABLED_NO_CREDENTIAL`` is a first-class state. When a provider is unavailable VEO
    reports UNKNOWN and says why — it never invents a plausible-looking value.
    """

    ENABLED = "ENABLED"
    DISABLED_NO_CREDENTIAL = "DISABLED_NO_CREDENTIAL"
    # A credential is present but is a placeholder, not a usable secret — for example
    # the literal "[SENSITIVE]" that `vercel env pull` writes for redacted variables.
    # Distinct from NO_CREDENTIAL because the remedy is different: one slot is empty,
    # the other is filled with something that will only ever produce 401s and 403s.
    DISABLED_INVALID_CREDENTIAL = "DISABLED_INVALID_CREDENTIAL"
    DISABLED_BY_CONFIG = "DISABLED_BY_CONFIG"
    # The provider does not offer this capability at all — no credential would help.
    # Distinct from NO_CREDENTIAL because the remedies are opposite: one is "get a key",
    # the other is "there is no key to get; do it by hand". Naver Search Advisor has no
    # public API for most of what VEO would like to read, and reporting that as
    # "연동이 구성되어 있지 않아" would send an operator hunting for a key that
    # does not exist.
    NOT_AVAILABLE = "NOT_AVAILABLE"
    DEGRADED = "DEGRADED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"


class ValueQuality(StrEnum):
    """Why a numeric field is what it is. Zero and 'no data' are different facts."""

    EXACT = "EXACT"
    ROUNDED = "ROUNDED"
    RANGE = "RANGE"
    SUPPRESSED_BY_PROVIDER = "SUPPRESSED_BY_PROVIDER"
    BELOW_PROVIDER_THRESHOLD = "BELOW_PROVIDER_THRESHOLD"
    MISSING = "MISSING"


class IssueSeverity(StrEnum):
    BLOCKER = "BLOCKER"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class IssueState(StrEnum):
    """An issue is closed by a re-measurement, not by someone saying it is fixed.

    Three of these states exist purely to keep that true:

    * ``FIX_CLAIMED`` is as far as a person can move an issue on their own. It means
      "I changed something", which is not the same as "it is fixed".
    * ``VERIFYING`` means a re-scan has been requested. Without it there is no way to
      tell an asserted fix from a measured one, and that gap is exactly where a passing
      verdict could be injected by hand.
    * ``VERIFICATION_FAILED`` means the re-measurement ran and the check still fails.
      Without it a failed verification has to land in ``OPEN`` — erasing the fact that
      anyone measured — or back in ``FIX_CLAIMED``, which makes a failure look like a fix.
    """

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    FIX_CLAIMED = "FIX_CLAIMED"
    VERIFYING = "VERIFYING"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    VERIFIED_RESOLVED = "VERIFIED_RESOLVED"
    RECURRED = "RECURRED"
    WONT_FIX = "WONT_FIX"


class ReviewState(StrEnum):
    """Automated judgement and human review are tracked separately, never merged."""

    NOT_REVIEWED = "NOT_REVIEWED"
    PENDING_REVIEW = "PENDING_REVIEW"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    HUMAN_REJECTED = "HUMAN_REJECTED"


class ErrorCode(StrEnum):
    """Machine-readable error codes. Messages are localised; codes are not."""

    VALIDATION_FAILED = "VALIDATION_FAILED"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    TARGET_URL_REJECTED = "TARGET_URL_REJECTED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    JOB_CANCELLED = "JOB_CANCELLED"
    JOB_EXPIRED = "JOB_EXPIRED"
    SCORING_SPEC_INVALID = "SCORING_SPEC_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"


RETRYABLE_ERROR_CODES = frozenset(
    {
        ErrorCode.RATE_LIMITED,
        ErrorCode.PROVIDER_UNAVAILABLE,
        ErrorCode.PROVIDER_RATE_LIMITED,
        ErrorCode.INTERNAL_ERROR,
    }
)


class UrlImportance(StrEnum):
    """Importance class of a URL, used to build coverage denominators."""

    CONVERSION_OR_HOME = "CONVERSION_OR_HOME"
    CATEGORY_OR_HUB = "CATEGORY_OR_HUB"
    CONTENT_OR_PRODUCT = "CONTENT_OR_PRODUCT"
    TAG_OR_FILTER = "TAG_OR_FILTER"
    INTENTIONAL_NOINDEX = "INTENTIONAL_NOINDEX"
