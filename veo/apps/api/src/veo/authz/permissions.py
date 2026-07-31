"""The VEO permission vocabulary and the role matrix that grants it.

Deny by default. A role holds exactly what this file grants and nothing else, and the
matrix is asserted by ``tests/authz/test_permissions.py`` so widening a role has to be a
deliberate change someone reviews.

Two deliberate absences:

* There is no permission to read a provider secret back. Credentials go in and are used;
  they never come out. The most anyone can see is whether a provider is configured.
* Only VEO-LAB roles can publish a scoring specification. If an analyst could move a score
  band, the methodology version on a report would stop meaning anything.
"""

from __future__ import annotations

from enum import StrEnum

from veo.contracts.enums import Role


class Permission(StrEnum):
    """A single capability, named ``resource:action``."""

    ORG_READ = "org:read"
    ORG_MANAGE = "org:manage"

    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    ROLE_ASSIGN = "role:assign"

    CUSTOMER_READ = "customer:read"
    CUSTOMER_WRITE = "customer:write"

    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"

    SITE_READ = "site:read"
    SITE_WRITE = "site:write"

    COMPETITOR_READ = "competitor:read"
    COMPETITOR_WRITE = "competitor:write"

    SCAN_READ = "scan:read"
    SCAN_RUN = "scan:run"

    # Raw crawl material, HTTP exchanges, rendered DOM, screenshots.
    EVIDENCE_READ = "evidence:read"

    KEYWORD_READ = "keyword:read"
    KEYWORD_RUN = "keyword:run"

    OBSERVATION_READ = "observation:read"
    OBSERVATION_RUN = "observation:run"
    # Raw AI answers are sensitive and gated separately from the aggregate metrics.
    OBSERVATION_RAW_READ = "observation:raw_read"
    # Deciding a risk finding decides what a customer is told about their own
    # reputation. It is the same class of act as REPORT_WRITE and is kept away from
    # DEVELOPER for the same reason: reading observations plus fixing sites should not
    # add up to the ability to confirm a claim about a clinic.
    OBSERVATION_REVIEW = "observation:review"

    ISSUE_READ = "issue:read"
    ISSUE_WRITE = "issue:write"

    REPORT_READ = "report:read"
    # Publishing a client-facing report is a distinct act from running a scan. Without
    # this, "read a report" plus "run a scan" was enough to publish one — which handed
    # DEVELOPER, a role deliberately kept away from customer-facing output, the ability
    # to create it.
    REPORT_WRITE = "report:write"
    REPORT_EXPORT = "report:export"

    SCORING_SPEC_READ = "scoring_spec:read"
    SCORING_SPEC_AUTHOR = "scoring_spec:author"
    SCORING_SPEC_PUBLISH = "scoring_spec:publish"

    # State only — configured or not. Never the secret itself.
    CREDENTIAL_READ_STATE = "credential:read_state"
    CREDENTIAL_MANAGE = "credential:manage"

    USAGE_READ = "usage:read"
    AUDIT_READ = "audit:read"


_ALL: frozenset[Permission] = frozenset(Permission)

_READ_ONLY_PROJECT_VIEW: frozenset[Permission] = frozenset(
    {
        Permission.PROJECT_READ,
        Permission.SITE_READ,
        Permission.SCAN_READ,
        Permission.KEYWORD_READ,
        Permission.OBSERVATION_READ,
        Permission.COMPETITOR_READ,
        Permission.ISSUE_READ,
        Permission.REPORT_READ,
        Permission.SCORING_SPEC_READ,
    }
)

#: Role to permission. The single source of truth for what anyone may do.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.SUPER_ADMIN: _ALL,
    # VEO-LAB owns measurement methodology: authors and publishes specifications,
    # reads results widely enough to validate them, changes no customer data.
    Role.LAB_ADMIN: frozenset(
        {
            Permission.ORG_READ,
            Permission.USER_READ,
            Permission.CUSTOMER_READ,
            Permission.PROJECT_READ,
            Permission.SITE_READ,
            Permission.COMPETITOR_READ,
            Permission.SCAN_READ,
            Permission.EVIDENCE_READ,
            Permission.KEYWORD_READ,
            Permission.OBSERVATION_READ,
            Permission.OBSERVATION_RAW_READ,
            Permission.ISSUE_READ,
            Permission.REPORT_READ,
            Permission.SCORING_SPEC_READ,
            Permission.SCORING_SPEC_AUTHOR,
            Permission.SCORING_SPEC_PUBLISH,
            Permission.USAGE_READ,
            Permission.AUDIT_READ,
        }
    ),
    # Runs the work: projects, diagnostics, review, reports.
    Role.ANALYST: frozenset(
        {
            Permission.ORG_READ,
            Permission.CUSTOMER_READ,
            Permission.CUSTOMER_WRITE,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.SITE_READ,
            Permission.SITE_WRITE,
            Permission.COMPETITOR_READ,
            Permission.COMPETITOR_WRITE,
            Permission.SCAN_READ,
            Permission.SCAN_RUN,
            Permission.EVIDENCE_READ,
            Permission.KEYWORD_READ,
            Permission.KEYWORD_RUN,
            Permission.OBSERVATION_READ,
            Permission.OBSERVATION_RUN,
            Permission.OBSERVATION_RAW_READ,
            Permission.OBSERVATION_REVIEW,
            Permission.ISSUE_READ,
            Permission.ISSUE_WRITE,
            Permission.REPORT_READ,
            Permission.REPORT_WRITE,
            Permission.REPORT_EXPORT,
            Permission.SCORING_SPEC_READ,
            Permission.CREDENTIAL_READ_STATE,
            Permission.USAGE_READ,
        }
    ),
    # Fixes what the diagnostics found, and re-verifies it. Needs raw evidence.
    Role.DEVELOPER: frozenset(
        {
            Permission.ORG_READ,
            Permission.PROJECT_READ,
            Permission.SITE_READ,
            Permission.SCAN_READ,
            Permission.SCAN_RUN,
            Permission.EVIDENCE_READ,
            Permission.KEYWORD_READ,
            Permission.OBSERVATION_READ,
            Permission.ISSUE_READ,
            Permission.ISSUE_WRITE,
            Permission.REPORT_READ,
            Permission.SCORING_SPEC_READ,
            Permission.CREDENTIAL_READ_STATE,
            Permission.USAGE_READ,
        }
    ),
    # Customer-facing summaries only. No raw evidence, no credentials, no writes.
    Role.SALES_VIEWER: frozenset(
        {
            Permission.ORG_READ,
            Permission.CUSTOMER_READ,
            Permission.PROJECT_READ,
            Permission.SITE_READ,
            Permission.COMPETITOR_READ,
            Permission.SCAN_READ,
            Permission.KEYWORD_READ,
            Permission.OBSERVATION_READ,
            Permission.ISSUE_READ,
            Permission.REPORT_READ,
            Permission.SCORING_SPEC_READ,
        }
    ),
    # Future customer portal. Read-only, and narrower than sales: no customer list,
    # no internal issue tracker context beyond their own project's findings.
    Role.CLIENT_VIEWER: _READ_ONLY_PROJECT_VIEW,
}


def permissions_for(roles: frozenset[Role] | set[Role]) -> frozenset[Permission]:
    """Union the permissions of every held role. No roles means no permissions."""
    if not roles:
        return frozenset()
    granted: frozenset[Permission] = frozenset()
    for role in roles:
        granted |= ROLE_PERMISSIONS.get(role, frozenset())
    return granted
