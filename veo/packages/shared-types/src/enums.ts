/**
 * Generated from `apps/api/src/veo/contracts/enums.py` — do not edit by hand.
 *
 * Regenerate with:
 *   python apps/api/scripts/export_shared_types.py
 *
 * VEO — SEO · GEO · Naver Keyword Intelligence Platform
 * Developed by VENOM. Research & Methodology by VEO-LAB.
 */

/** Lifecycle of an asynchronous analysis job. */
export type JobStatus =
  | "QUEUED"
  | "RUNNING"
  | "PARTIAL_SUCCESS"
  | "SUCCEEDED"
  | "FAILED_RETRYABLE"
  | "FAILED_FINAL"
  | "CANCEL_REQUESTED"
  | "CANCELLED"
  | "EXPIRED";

export const JOB_STATUS_VALUES: readonly JobStatus[] = [
  "QUEUED",
  "RUNNING",
  "PARTIAL_SUCCESS",
  "SUCCEEDED",
  "FAILED_RETRYABLE",
  "FAILED_FINAL",
  "CANCEL_REQUESTED",
  "CANCELLED",
  "EXPIRED",
] as const;

/** Kind of work a job performs. */
export type JobType =
  | "SEO_SCAN"
  | "GEO_READINESS_SCAN"
  | "GEO_OBSERVATION_RUN"
  | "KEYWORD_LOOKUP"
  | "SITE_CRAWL"
  | "COMPETITOR_COMPARISON"
  | "REPORT_EXPORT"
  | "REVERIFICATION";

export const JOB_TYPE_VALUES: readonly JobType[] = [
  "SEO_SCAN",
  "GEO_READINESS_SCAN",
  "GEO_OBSERVATION_RUN",
  "KEYWORD_LOOKUP",
  "SITE_CRAWL",
  "COMPETITOR_COMPARISON",
  "REPORT_EXPORT",
  "REVERIFICATION",
] as const;

/** How much of a site a scan covers. */
export type ScanScope =
  | "SINGLE_URL"
  | "SITE";

export const SCAN_SCOPE_VALUES: readonly ScanScope[] = [
  "SINGLE_URL",
  "SITE",
] as const;

/** Why a job stopped early. A closed set, never free text. */
export type CancellationReason =
  | "USER_REQUESTED"
  | "SUPERSEDED_BY_NEWER_RUN"
  | "QUOTA_EXCEEDED"
  | "BUDGET_EXCEEDED"
  | "TARGET_UNREACHABLE"
  | "SHUTDOWN"
  | "EXPIRED";

export const CANCELLATION_REASON_VALUES: readonly CancellationReason[] = [
  "USER_REQUESTED",
  "SUPERSEDED_BY_NEWER_RUN",
  "QUOTA_EXCEEDED",
  "BUDGET_EXCEEDED",
  "TARGET_UNREACHABLE",
  "SHUTDOWN",
  "EXPIRED",
] as const;

/** Which product surface requested the work. */
export type Surface =
  | "PUBLIC"
  | "CONSOLE";

export const SURFACE_VALUES: readonly Surface[] = [
  "PUBLIC",
  "CONSOLE",
] as const;

/** Console roles. Access is denied by default. */
export type Role =
  | "SUPER_ADMIN"
  | "LAB_ADMIN"
  | "ANALYST"
  | "DEVELOPER"
  | "SALES_VIEWER"
  | "CLIENT_VIEWER";

export const ROLE_VALUES: readonly Role[] = [
  "SUPER_ADMIN",
  "LAB_ADMIN",
  "ANALYST",
  "DEVELOPER",
  "SALES_VIEWER",
  "CLIENT_VIEWER",
] as const;

/** Origin of a value. NAVER_SEARCH_AD carries absolute search counts; NAVER_DATALAB carries a relative interest index and is never a count. */
export type DataSource =
  | "NAVER_SEARCH_AD"
  | "NAVER_DATALAB"
  | "NAVER_SEARCH_API"
  | "GOOGLE_SEARCH_CONSOLE"
  | "GOOGLE_PAGESPEED"
  | "GOOGLE_CRUX"
  | "BING_WEBMASTER"
  | "AI_ENGINE_OBSERVATION"
  | "VEO_CRAWLER"
  | "VEO_INTERNAL"
  | "CALCULATED";

export const DATA_SOURCE_VALUES: readonly DataSource[] = [
  "NAVER_SEARCH_AD",
  "NAVER_DATALAB",
  "NAVER_SEARCH_API",
  "GOOGLE_SEARCH_CONSOLE",
  "GOOGLE_PAGESPEED",
  "GOOGLE_CRUX",
  "BING_WEBMASTER",
  "AI_ENGINE_OBSERVATION",
  "VEO_CRAWLER",
  "VEO_INTERNAL",
  "CALCULATED",
] as const;

/** Availability of an external provider. A disabled provider yields UNKNOWN results, never invented ones. */
export type ProviderState =
  | "ENABLED"
  | "DISABLED_NO_CREDENTIAL"
  | "DISABLED_INVALID_CREDENTIAL"
  | "DISABLED_BY_CONFIG"
  | "NOT_AVAILABLE"
  | "DEGRADED"
  | "CIRCUIT_OPEN";

export const PROVIDER_STATE_VALUES: readonly ProviderState[] = [
  "ENABLED",
  "DISABLED_NO_CREDENTIAL",
  "DISABLED_INVALID_CREDENTIAL",
  "DISABLED_BY_CONFIG",
  "NOT_AVAILABLE",
  "DEGRADED",
  "CIRCUIT_OPEN",
] as const;

/** Why a number is what it is. Zero and 'no data' are different facts. */
export type ValueQuality =
  | "EXACT"
  | "ROUNDED"
  | "RANGE"
  | "SUPPRESSED_BY_PROVIDER"
  | "BELOW_PROVIDER_THRESHOLD"
  | "MISSING";

export const VALUE_QUALITY_VALUES: readonly ValueQuality[] = [
  "EXACT",
  "ROUNDED",
  "RANGE",
  "SUPPRESSED_BY_PROVIDER",
  "BELOW_PROVIDER_THRESHOLD",
  "MISSING",
] as const;

/** Severity of a finding. */
export type IssueSeverity =
  | "BLOCKER"
  | "CRITICAL"
  | "MAJOR"
  | "MINOR"
  | "INFO";

export const ISSUE_SEVERITY_VALUES: readonly IssueSeverity[] = [
  "BLOCKER",
  "CRITICAL",
  "MAJOR",
  "MINOR",
  "INFO",
] as const;

/** Issue lifecycle through to verified resolution. */
export type IssueState =
  | "OPEN"
  | "ACKNOWLEDGED"
  | "IN_PROGRESS"
  | "FIX_CLAIMED"
  | "VERIFYING"
  | "VERIFICATION_FAILED"
  | "VERIFIED_RESOLVED"
  | "RECURRED"
  | "WONT_FIX";

export const ISSUE_STATE_VALUES: readonly IssueState[] = [
  "OPEN",
  "ACKNOWLEDGED",
  "IN_PROGRESS",
  "FIX_CLAIMED",
  "VERIFYING",
  "VERIFICATION_FAILED",
  "VERIFIED_RESOLVED",
  "RECURRED",
  "WONT_FIX",
] as const;

/** Human review status, tracked separately from automated judgement. */
export type ReviewState =
  | "NOT_REVIEWED"
  | "PENDING_REVIEW"
  | "HUMAN_CONFIRMED"
  | "HUMAN_REJECTED";

export const REVIEW_STATE_VALUES: readonly ReviewState[] = [
  "NOT_REVIEWED",
  "PENDING_REVIEW",
  "HUMAN_CONFIRMED",
  "HUMAN_REJECTED",
] as const;

/** Machine-readable error codes. */
export type ErrorCode =
  | "VALIDATION_FAILED"
  | "UNAUTHENTICATED"
  | "PERMISSION_DENIED"
  | "NOT_FOUND"
  | "CONFLICT"
  | "RATE_LIMITED"
  | "QUOTA_EXCEEDED"
  | "TARGET_URL_REJECTED"
  | "PROVIDER_UNAVAILABLE"
  | "PROVIDER_RATE_LIMITED"
  | "JOB_CANCELLED"
  | "JOB_EXPIRED"
  | "SCORING_SPEC_INVALID"
  | "INTERNAL_ERROR";

export const ERROR_CODE_VALUES: readonly ErrorCode[] = [
  "VALIDATION_FAILED",
  "UNAUTHENTICATED",
  "PERMISSION_DENIED",
  "NOT_FOUND",
  "CONFLICT",
  "RATE_LIMITED",
  "QUOTA_EXCEEDED",
  "TARGET_URL_REJECTED",
  "PROVIDER_UNAVAILABLE",
  "PROVIDER_RATE_LIMITED",
  "JOB_CANCELLED",
  "JOB_EXPIRED",
  "SCORING_SPEC_INVALID",
  "INTERNAL_ERROR",
] as const;

/** Importance class of a URL, used to build coverage denominators. */
export type UrlImportance =
  | "CONVERSION_OR_HOME"
  | "CATEGORY_OR_HUB"
  | "CONTENT_OR_PRODUCT"
  | "TAG_OR_FILTER"
  | "INTENTIONAL_NOINDEX";

export const URL_IMPORTANCE_VALUES: readonly UrlImportance[] = [
  "CONVERSION_OR_HOME",
  "CATEGORY_OR_HUB",
  "CONTENT_OR_PRODUCT",
  "TAG_OR_FILTER",
  "INTENTIONAL_NOINDEX",
] as const;

/** Outcome of one check. NOT_APPLICABLE leaves the denominator entirely; UNKNOWN lowers coverage and confidence but never the score. */
export type CheckStatus =
  | "PASS"
  | "WARNING"
  | "FAIL"
  | "NOT_APPLICABLE"
  | "UNKNOWN";

export const CHECK_STATUS_VALUES: readonly CheckStatus[] = [
  "PASS",
  "WARNING",
  "FAIL",
  "NOT_APPLICABLE",
  "UNKNOWN",
] as const;

/** Severity coefficients are defined in the scoring specification. */
export type Severity =
  | "BLOCKER"
  | "CRITICAL"
  | "MAJOR"
  | "MINOR"
  | "INFO";

export const SEVERITY_VALUES: readonly Severity[] = [
  "BLOCKER",
  "CRITICAL",
  "MAJOR",
  "MINOR",
  "INFO",
] as const;

/** Domains that the deterministic evaluator scores. */
export type ScoringDomain =
  | "SEO_READINESS"
  | "GEO_READINESS";

export const SCORING_DOMAIN_VALUES: readonly ScoringDomain[] = [
  "SEO_READINESS",
  "GEO_READINESS",
] as const;

/** A single capability, named resource:action. The role -> permission matrix lives only on the server; the front end reads the resolved list from /auth/me and never reimplements the mapping. */
export type Permission =
  | "org:read"
  | "org:manage"
  | "user:read"
  | "user:manage"
  | "role:assign"
  | "customer:read"
  | "customer:write"
  | "project:read"
  | "project:write"
  | "site:read"
  | "site:write"
  | "competitor:read"
  | "competitor:write"
  | "scan:read"
  | "scan:run"
  | "evidence:read"
  | "keyword:read"
  | "keyword:run"
  | "observation:read"
  | "observation:run"
  | "observation:raw_read"
  | "issue:read"
  | "issue:write"
  | "report:read"
  | "report:write"
  | "report:export"
  | "scoring_spec:read"
  | "scoring_spec:author"
  | "scoring_spec:publish"
  | "credential:read_state"
  | "credential:manage"
  | "usage:read"
  | "audit:read";

export const PERMISSION_VALUES: readonly Permission[] = [
  "org:read",
  "org:manage",
  "user:read",
  "user:manage",
  "role:assign",
  "customer:read",
  "customer:write",
  "project:read",
  "project:write",
  "site:read",
  "site:write",
  "competitor:read",
  "competitor:write",
  "scan:read",
  "scan:run",
  "evidence:read",
  "keyword:read",
  "keyword:run",
  "observation:read",
  "observation:run",
  "observation:raw_read",
  "issue:read",
  "issue:write",
  "report:read",
  "report:write",
  "report:export",
  "scoring_spec:read",
  "scoring_spec:author",
  "scoring_spec:publish",
  "credential:read_state",
  "credential:manage",
  "usage:read",
  "audit:read",
] as const;

/** Publication state of a scoring specification. */
export type SpecStatus =
  | "DRAFT"
  | "REVIEW"
  | "APPROVED"
  | "PUBLISHED"
  | "RETIRED";

export const SPEC_STATUS_VALUES: readonly SpecStatus[] = [
  "DRAFT",
  "REVIEW",
  "APPROVED",
  "PUBLISHED",
  "RETIRED",
] as const;

/** Job statuses after which no further transition occurs. */
export const TERMINAL_JOB_STATUSES: readonly JobStatus[] = [
  "CANCELLED",
  "EXPIRED",
  "FAILED_FINAL",
  "PARTIAL_SUCCESS",
  "SUCCEEDED",
] as const;

/** Error codes where retrying the same request may succeed. */
export const RETRYABLE_ERROR_CODES: readonly ErrorCode[] = [
  "INTERNAL_ERROR",
  "PROVIDER_RATE_LIMITED",
  "PROVIDER_UNAVAILABLE",
  "RATE_LIMITED",
] as const;
