"""Generate ``packages/shared-types/src/enums.ts`` from the Python contract enums.

The two languages must never disagree about what ``NOT_APPLICABLE`` means. Rather than
maintaining the list twice, TypeScript is generated from Python and a contract test fails
the build when the committed file is stale.

Usage:
    python scripts/export_shared_types.py [--check]
"""

from __future__ import annotations

import argparse
import enum
import sys
from pathlib import Path

from veo.authz.permissions import Permission
from veo.contracts import enums as contract_enums
from veo.scoring.models import CheckStatus, ScoringDomain, Severity, SpecStatus

OUTPUT = (
    Path(__file__).resolve().parents[3] / "packages" / "shared-types" / "src" / "enums.ts"
)

EXPORTED: list[tuple[str, type[enum.StrEnum], str]] = [
    ("JobStatus", contract_enums.JobStatus, "Lifecycle of an asynchronous analysis job."),
    ("JobType", contract_enums.JobType, "Kind of work a job performs."),
    ("ScanScope", contract_enums.ScanScope, "How much of a site a scan covers."),
    (
        "CancellationReason",
        contract_enums.CancellationReason,
        "Why a job stopped early. A closed set, never free text.",
    ),
    ("Surface", contract_enums.Surface, "Which product surface requested the work."),
    ("Role", contract_enums.Role, "Console roles. Access is denied by default."),
    (
        "DataSource",
        contract_enums.DataSource,
        "Origin of a value. NAVER_SEARCH_AD carries absolute search counts; "
        "NAVER_DATALAB carries a relative interest index and is never a count.",
    ),
    (
        "ProviderState",
        contract_enums.ProviderState,
        "Availability of an external provider. A disabled provider yields UNKNOWN "
        "results, never invented ones.",
    ),
    (
        "ValueQuality",
        contract_enums.ValueQuality,
        "Why a number is what it is. Zero and 'no data' are different facts.",
    ),
    ("IssueSeverity", contract_enums.IssueSeverity, "Severity of a finding."),
    ("IssueState", contract_enums.IssueState, "Issue lifecycle through to verified resolution."),
    (
        "ReviewState",
        contract_enums.ReviewState,
        "Human review status, tracked separately from automated judgement.",
    ),
    ("ErrorCode", contract_enums.ErrorCode, "Machine-readable error codes."),
    (
        "UrlImportance",
        contract_enums.UrlImportance,
        "Importance class of a URL, used to build coverage denominators.",
    ),
    (
        "CheckStatus",
        CheckStatus,
        "Outcome of one check. NOT_APPLICABLE leaves the denominator entirely; "
        "UNKNOWN lowers coverage and confidence but never the score.",
    ),
    ("Severity", Severity, "Severity coefficients are defined in the scoring specification."),
    ("ScoringDomain", ScoringDomain, "Domains that the deterministic evaluator scores."),
    (
        "Permission",
        Permission,
        "A single capability, named resource:action. The role -> permission matrix lives "
        "only on the server; the front end reads the resolved list from /auth/me and "
        "never reimplements the mapping.",
    ),
    ("SpecStatus", SpecStatus, "Publication state of a scoring specification."),
]

HEADER = """\
/**
 * Generated from `apps/api/src/veo/contracts/enums.py` — do not edit by hand.
 *
 * Regenerate with:
 *   python apps/api/scripts/export_shared_types.py
 *
 * VEO — SEO · GEO · Naver Keyword Intelligence Platform
 * Developed by VENOM. Research & Methodology by VEO-LAB.
 */
"""


def render() -> str:
    blocks: list[str] = [HEADER]

    for name, enum_cls, doc in EXPORTED:
        members = [member.value for member in enum_cls]
        union = "\n  | ".join(f'"{value}"' for value in members)
        const_name = _screaming(name)

        blocks.append(
            f"/** {doc} */\nexport type {name} =\n  | {union};\n\n"
            f"export const {const_name}: readonly {name}[] = [\n"
            + "".join(f'  "{value}",\n' for value in members)
            + "] as const;\n"
        )

    blocks.append(
        "/** Job statuses after which no further transition occurs. */\n"
        "export const TERMINAL_JOB_STATUSES: readonly JobStatus[] = [\n"
        + "".join(
            f'  "{value}",\n'
            for value in sorted(s.value for s in contract_enums.TERMINAL_JOB_STATUSES)
        )
        + "] as const;\n"
    )
    blocks.append(
        "/** Error codes where retrying the same request may succeed. */\n"
        "export const RETRYABLE_ERROR_CODES: readonly ErrorCode[] = [\n"
        + "".join(
            f'  "{value}",\n'
            for value in sorted(c.value for c in contract_enums.RETRYABLE_ERROR_CODES)
        )
        + "] as const;\n"
    )

    return "\n".join(blocks)


def _screaming(name: str) -> str:
    out: list[str] = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            out.append("_")
        out.append(char.upper())
    return "".join(out) + "_VALUES"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render()

    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT} is out of date. Run: python scripts/export_shared_types.py",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT} is up to date")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
