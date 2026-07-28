"""Targeted re-measurement: the only thing that may resolve an issue.

Two separate guarantees live here, and both matter.

**Scope.** A verification re-scans the affected URLs and the one check that produced the
finding. Re-crawling a whole site to answer "is this one canonical tag fixed?" costs the
customer hours and burns a crawl budget that has other work to do, so
:class:`VerificationRequest` cannot express anything wider: one ``check_id``, the issue's
own URLs, nothing else.

**Authority.** The verdict is *derived* from persisted check outcomes. There is no
argument, header or body field anywhere in this module that a caller can set to mean
"call it resolved" — :func:`derive_outcome` reads what was measured and nothing else.
That is what keeps the module's central rule from being a comment: a human may report a
fix, but only a measurement can close the issue.

Three deliberate conservatisms in the verdict:

* A ``WARNING`` is not a pass. The check did not pass, so the problem is not gone.
* ``NOT_APPLICABLE`` is inconclusive, not resolved. Deleting the page is not fixing it,
  and a rule that rewarded disappearance would be gamed within a week.
* Passing *some* of the affected URLs is inconclusive. A partial re-scan that resolved
  the issue would let a five-page problem be closed by fixing one page.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from veo.db.models.analysis import Issue
from veo.issues.identity import normalize_affected_urls
from veo.issues.lifecycle import VerificationOutcome
from veo.scoring import CheckStatus

#: Marks the scan parameters as a re-verification rather than a normal analysis, so a
#: worker cannot mistake one for the other and widen the crawl.
TARGETED_SCOPE = "TARGETED_REVERIFICATION"

DEFAULT_NOTE_KO = (
    "이 이슈에 표시된 URL만, 이 검사 하나만 다시 수집·판정합니다. "
    "사이트 전체를 다시 진단하지 않습니다."
)


class VerificationScopeError(Exception):
    """A verification request cannot be built for this issue.

    ``message_ko`` is safe to show a caller verbatim.
    """

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    """What to re-measure. Narrow by construction."""

    issue_id: uuid.UUID
    project_id: uuid.UUID
    check_id: str
    target_urls: tuple[str, ...]
    note_ko: str

    def as_scan_parameters(self) -> dict[str, Any]:
        """The payload a re-verification job takes.

        ``check_ids`` is a one-element list rather than a bare string so the worker's
        existing parameter shape is reused, and the list can never grow: it is built from
        a single field.
        """
        return {
            "scope": TARGETED_SCOPE,
            "check_ids": [self.check_id],
            "urls": list(self.target_urls),
            "issue_id": str(self.issue_id),
            "project_id": str(self.project_id),
            "note_ko": self.note_ko,
        }


@dataclass(frozen=True, slots=True)
class MeasuredCheck:
    """One persisted check outcome from the re-scan, with the URL it was measured on."""

    check_id: str
    status: CheckStatus
    url: str | None
    check_result_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class VerificationVerdict:
    """What the re-measurement concluded, and why, in terms a customer can read."""

    outcome: VerificationOutcome
    reason_ko: str
    detail: dict[str, Any] = field(default_factory=dict)


def build_verification_request(issue: Issue) -> VerificationRequest:
    """Build the narrowest request that can settle this issue.

    Refuses an issue with no recorded URL: there would be nothing to fetch, and a
    "verification" that fetched a default page instead would be measuring the wrong
    thing while looking like evidence.
    """
    target_urls = normalize_affected_urls(issue.sample_urls or [])
    if not target_urls:
        raise VerificationScopeError(
            "재검사할 대상 URL이 기록되어 있지 않아 표적 재검사를 만들 수 없습니다. "
            "사이트 전체를 다시 진단하는 것은 이 이슈의 검증이 아니므로 수행하지 않습니다."
        )

    return VerificationRequest(
        issue_id=issue.id,
        project_id=issue.project_id,
        check_id=issue.check_id,
        target_urls=target_urls,
        note_ko=DEFAULT_NOTE_KO,
    )


def derive_outcome(
    measurements: Sequence[MeasuredCheck], *, affected_urls: Sequence[str]
) -> VerificationVerdict:
    """Read what the re-scan measured and say what it means. Nothing else may decide."""
    expected = set(normalize_affected_urls(affected_urls))
    measured_urls = {
        normalized
        for item in measurements
        if item.url
        for normalized in normalize_affected_urls([item.url])
    }
    detail: dict[str, Any] = {
        "measured_count": len(measurements),
        "measured_urls": sorted(measured_urls),
        "expected_urls": sorted(expected),
        "unmeasured_urls": sorted(expected - measured_urls),
        "check_result_ids": [
            str(item.check_result_id) for item in measurements if item.check_result_id
        ],
        "statuses": sorted({str(item.status) for item in measurements}),
    }

    if not measurements:
        return VerificationVerdict(
            VerificationOutcome.INCONCLUSIVE,
            "재검사 실행에 이 검사 항목의 결과가 없습니다. 측정되지 않았으므로 해결로 "
            "인정하지 않습니다.",
            detail,
        )

    statuses = {item.status for item in measurements}

    if statuses & {CheckStatus.FAIL, CheckStatus.WARNING}:
        return VerificationVerdict(
            VerificationOutcome.STILL_FAILING,
            "재측정에서도 해당 검사가 통과하지 못했습니다. 수정 내용이 반영되지 않았거나 "
            "문제의 원인이 다른 곳에 있습니다.",
            detail,
        )

    if CheckStatus.UNKNOWN in statuses:
        return VerificationVerdict(
            VerificationOutcome.INCONCLUSIVE,
            "재측정에서 해당 검사를 수행하지 못했습니다(측정 불가). 측정 불가는 실패도 "
            "해결도 아닙니다.",
            detail,
        )

    if statuses == {CheckStatus.NOT_APPLICABLE}:
        return VerificationVerdict(
            VerificationOutcome.INCONCLUSIVE,
            "재측정에서 해당 검사가 '해당 없음'으로 나왔습니다. 페이지가 사라졌거나 조건이 "
            "달라진 것이며, 문제가 고쳐졌다는 근거는 아닙니다.",
            detail,
        )

    unmeasured = expected - measured_urls
    if unmeasured:
        return VerificationVerdict(
            VerificationOutcome.INCONCLUSIVE,
            f"영향 URL {len(expected)}개 가운데 {len(unmeasured)}개를 재측정하지 못했습니다. "
            "일부만 통과한 상태로는 해결로 인정하지 않습니다.",
            detail,
        )

    return VerificationVerdict(
        VerificationOutcome.RESOLVED,
        "표적 재측정에서 영향 URL 전체가 해당 검사를 통과했습니다.",
        detail,
    )


__all__ = [
    "DEFAULT_NOTE_KO",
    "TARGETED_SCOPE",
    "MeasuredCheck",
    "VerificationRequest",
    "VerificationScopeError",
    "VerificationVerdict",
    "build_verification_request",
    "derive_outcome",
]
