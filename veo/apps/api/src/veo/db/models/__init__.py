"""VEO data model.

Owned by the integration maintainer. Feature workers propose migrations; they do not
write to this package directly.
"""

from veo.db.base import Base
from veo.db.models.analysis import (
    APIUsageEvent,
    CheckResult,
    Evidence,
    FixRecommendation,
    Issue,
    Job,
    Scan,
    ScanRun,
    ScoreResult,
    ScoringVersion,
    VerificationRun,
)
from veo.db.models.identity import (
    AuditLog,
    Competitor,
    Customer,
    Organization,
    Project,
    RoleAssignment,
    Site,
    URLRecord,
    User,
)
from veo.db.models.keywords import (
    KeywordList,
    KeywordMetric,
    KeywordOpportunity,
    KeywordQuery,
    KeywordTrend,
    RelatedKeyword,
)
from veo.db.models.observation import (
    AIAnswer,
    AIEngine,
    BrandIdentity,
    Citation,
    ClaimAssessment,
    EntityMention,
    ObservationRun,
    Prompt,
    PromptSet,
    Report,
    ReportVersion,
)
from veo.db.models.public_leads import PublicLead
from veo.db.models.public_results import PublicSharedResult
from veo.db.models.security import (
    LoginAttempt,
    ProviderCredential,
    UserSession,
)

__all__ = [
    "AIAnswer",
    "AIEngine",
    "APIUsageEvent",
    "AuditLog",
    "Base",
    "BrandIdentity",
    "CheckResult",
    "Citation",
    "ClaimAssessment",
    "Competitor",
    "Customer",
    "EntityMention",
    "Evidence",
    "FixRecommendation",
    "Issue",
    "Job",
    "KeywordList",
    "KeywordMetric",
    "KeywordOpportunity",
    "KeywordQuery",
    "KeywordTrend",
    "LoginAttempt",
    "ObservationRun",
    "Organization",
    "Project",
    "Prompt",
    "PromptSet",
    "ProviderCredential",
    "PublicLead",
    "PublicSharedResult",
    "RelatedKeyword",
    "Report",
    "ReportVersion",
    "RoleAssignment",
    "Scan",
    "ScanRun",
    "ScoreResult",
    "ScoringVersion",
    "Site",
    "URLRecord",
    "User",
    "UserSession",
    "VerificationRun",
]
