"""VEO shared contracts.

Owned exclusively by the integration maintainer. Feature workers import from here and
propose changes rather than editing. Every symbol is mirrored in
``packages/shared-types`` and verified by ``tests/contract``.
"""

from veo.contracts.enums import (
    RETRYABLE_ERROR_CODES,
    TERMINAL_JOB_STATUSES,
    CancellationReason,
    DataSource,
    ErrorCode,
    IssueSeverity,
    IssueState,
    JobStatus,
    JobType,
    ProviderState,
    ReviewState,
    Role,
    ScanScope,
    Surface,
    UrlImportance,
    ValueQuality,
)
from veo.contracts.envelope import (
    ApiError,
    ApiResponse,
    FieldError,
    PagedResponse,
    PageInfo,
    ResponseMeta,
    SourceAttribution,
)
from veo.contracts.jobs import JobDescriptor, JobStage, JobSubmission

__all__ = [
    "RETRYABLE_ERROR_CODES",
    "TERMINAL_JOB_STATUSES",
    "ApiError",
    "ApiResponse",
    "CancellationReason",
    "DataSource",
    "ErrorCode",
    "FieldError",
    "IssueSeverity",
    "IssueState",
    "JobDescriptor",
    "JobStage",
    "JobStatus",
    "JobSubmission",
    "JobType",
    "PageInfo",
    "PagedResponse",
    "ProviderState",
    "ResponseMeta",
    "ReviewState",
    "Role",
    "ScanScope",
    "SourceAttribution",
    "Surface",
    "UrlImportance",
    "ValueQuality",
]
