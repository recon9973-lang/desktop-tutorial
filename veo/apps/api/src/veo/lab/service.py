"""The VEO-LAB scoring-version workflow, with no HTTP in it.

This is where the four rules meet the database.

1. **A published version is immutable.** Content-bearing operations —
   :func:`update_draft` and :func:`run_golden` — go through
   :func:`veo.lab.versions.assert_row_writable`, which refuses ``PUBLISHED`` and
   ``RETIRED`` outright. Status changes go through the transition table instead, which is
   what lets ``PUBLISHED -> RETIRED`` happen without opening the row up to edits.
2. **Re-scoring preserves both numbers.** :func:`rescore` selects originals and hands them
   to :mod:`veo.lab.rescore`, which only ever inserts.
3. **A checksum mismatch is a hard error.** Every path that turns a stored row back into a
   :class:`~veo.scoring.ScoringSpec` verifies the checksum first and refuses on mismatch.
   Nothing here recomputes a stored checksum to make it agree.
4. **Publishing requires the golden fixtures.** :func:`publish` will not proceed without a
   recorded, passing run bound to the exact checksum being published.

One authoring convention follows from rule 1 and is enforced in :func:`publish`: the
specification document must already say ``status: PUBLISHED`` when it is published. VEO
never rewrites the stored document — rewriting it would change its checksum, which is the
thing the whole workflow exists to hold still — so the document has to be authored for the
status it will end its life in.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veo.authz import Permission, Principal, assert_tenant_scoped, tenant_select
from veo.db.models.analysis import ScoreResult as ScoreResultRow
from veo.db.models.analysis import ScoringVersion
from veo.lab import golden as golden_module
from veo.lab import rescore as rescore_module
from veo.lab import validation, versions
from veo.lab.errors import (
    DuplicateVersionError,
    IllegalTransitionError,
    SpecificationRejectedError,
    VersionNotFoundError,
)
from veo.organizations import audit
from veo.scoring import ScoringSpec, SpecNotFoundError, SpecStatus, latest_published

TARGET_TYPE = "scoring_version"

#: A rescore touches every stored result of a specification family, so it is bounded.
DEFAULT_RESCORE_LIMIT = 200
MAX_RESCORE_LIMIT = 1000


@dataclass(frozen=True)
class VersionDetail:
    """Everything a reviewer needs on one screen."""

    version: ScoringVersion
    spec: ScoringSpec
    diff: validation.SpecDiff
    validation: validation.ValidationReport
    golden: dict[str, Any] | None
    baseline_source_ko: str

    @property
    def allowed_transitions(self) -> tuple[SpecStatus, ...]:
        return versions.next_statuses(versions.parse_status(self.version.status))


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #


def get_version(
    session: Session, principal: Principal, version_id: uuid.UUID
) -> ScoringVersion | None:
    """One version row, or ``None``.

    ``scoring_versions`` is not tenant-owned — a methodology belongs to VEO-LAB, not to a
    customer — so this is guarded by permission rather than by an organization filter.
    """
    principal.require(Permission.SCORING_SPEC_READ)
    return session.get(ScoringVersion, version_id)


def list_versions(
    session: Session,
    principal: Principal,
    *,
    spec_id: str | None = None,
    status: SpecStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ScoringVersion], int]:
    """One page of versions, newest first."""
    principal.require(Permission.SCORING_SPEC_READ)

    statement = select(ScoringVersion)
    if spec_id is not None:
        statement = statement.where(ScoringVersion.spec_id == spec_id)
    if status is not None:
        statement = statement.where(ScoringVersion.status == status.value)

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    page_statement = (
        statement.order_by(
            ScoringVersion.spec_id,
            ScoringVersion.created_at.desc(),
            ScoringVersion.semantic_version.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(page_statement)), total


def read_detail(
    session: Session, principal: Principal, version_id: uuid.UUID
) -> VersionDetail:
    """A version, verified, validated and diffed against what is published today."""
    principal.require(Permission.SCORING_SPEC_READ)
    row = _require_row(session, version_id)
    spec = _verified_spec(row)

    baseline, source_ko = baseline_spec(session, row.spec_id, exclude_id=row.id)
    report = validation.validate_candidate(row.specification, baseline=baseline)
    diff = report.diff or validation.diff_specs(baseline, spec)

    return VersionDetail(
        version=row,
        spec=spec,
        diff=diff,
        validation=report,
        golden=dict(row.golden_fixture_results) if row.golden_fixture_results else None,
        baseline_source_ko=source_ko,
    )


def baseline_spec(
    session: Session, spec_id: str, *, exclude_id: uuid.UUID | None = None
) -> tuple[ScoringSpec | None, str]:
    """The specification a candidate should be compared against.

    The published row in the database wins. Falling back to the on-disk published
    specification matters for the first database-managed version of an existing family:
    without it the very first candidate would report "no baseline" and a reviewer would
    approve a weight change with nothing to compare it to.
    """
    statement = (
        select(ScoringVersion)
        .where(ScoringVersion.spec_id == spec_id)
        .where(ScoringVersion.status == SpecStatus.PUBLISHED.value)
    )
    if exclude_id is not None:
        statement = statement.where(ScoringVersion.id != exclude_id)
    statement = statement.order_by(ScoringVersion.created_at.desc()).limit(1)

    row = session.scalars(statement).first()
    if row is not None:
        return _verified_spec(row), f"현재 발행본 {row.semantic_version} (데이터베이스)"

    try:
        on_disk = latest_published(spec_id)
    except SpecNotFoundError:
        return None, "비교할 이전 발행본이 없습니다."
    return on_disk, f"현재 발행본 {on_disk.version} (packages/scoring-specs)"


def score_history(
    session: Session, principal: Principal, scan_run_id: uuid.UUID
) -> list[ScoreResultRow]:
    """Every score ever computed for one run — original and recomputed alike.

    Guarded by ``SCAN_READ`` rather than ``SCORING_SPEC_READ``: these rows are the
    customer's measurements, not VEO-LAB's methodology, and they belong behind the
    permission that governs scan results everywhere else.
    """
    principal.require(Permission.SCAN_READ)
    statement = tenant_select(ScoreResultRow, principal).where(
        ScoreResultRow.scan_run_id == scan_run_id
    )
    assert_tenant_scoped(statement, principal.organization_id)
    return list(session.scalars(statement.order_by(ScoreResultRow.created_at)))


# --------------------------------------------------------------------------- #
# Authoring
# --------------------------------------------------------------------------- #


def create_draft(
    session: Session,
    principal: Principal,
    *,
    specification: Mapping[str, Any],
    changelog: str | None = None,
    compatible_collector_versions: Sequence[str] | None = None,
    request_id: str | None = None,
) -> ScoringVersion:
    """Register a candidate as a DRAFT, checksummed once and for good."""
    principal.require(Permission.SCORING_SPEC_AUTHOR)

    document = dict(specification)
    declared_id = document.get("spec_id")
    baseline, _ = (
        baseline_spec(session, str(declared_id)) if isinstance(declared_id, str) else (None, "")
    )
    spec = _accept(document, baseline)

    _reject_existing_version(session, spec.spec_id, spec.version)

    collectors = (
        list(compatible_collector_versions)
        if compatible_collector_versions is not None
        else list(spec.compatible_collector_versions)
    )
    row = ScoringVersion(
        spec_id=spec.spec_id,
        domain=str(spec.domain),
        semantic_version=spec.version,
        status=SpecStatus.DRAFT.value,
        effective_at=None,
        specification=document,
        checksum=spec.checksum,
        changelog=changelog,
        compatible_collector_versions=collectors,
        golden_fixture_results={},
    )
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError as exc:
        raise DuplicateVersionError(
            f"{spec.spec_id}의 {spec.version} 버전은 이미 등록되어 있습니다."
        ) from exc

    _audit(session, principal, row, "create", request_id, {"checksum": spec.checksum})
    session.flush()
    return row


def update_draft(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    specification: Mapping[str, Any] | None = None,
    changelog: str | None = None,
    request_id: str | None = None,
) -> ScoringVersion:
    """Replace a draft's body or its note. Refused outright once published."""
    principal.require(Permission.SCORING_SPEC_AUTHOR)
    row = _require_row(session, version_id)
    status = versions.parse_status(row.status)
    versions.assert_row_writable(status)

    changed: list[str] = []

    if specification is not None:
        versions.assert_specification_editable(status)
        document = dict(specification)
        baseline, _ = baseline_spec(session, row.spec_id, exclude_id=row.id)
        spec = _accept(document, baseline)

        if spec.spec_id != row.spec_id or spec.version != row.semantic_version:
            raise SpecificationRejectedError(
                f"이 행은 {row.spec_id}@{row.semantic_version} 버전입니다. "
                f"{spec.spec_id}@{spec.version}은(는) 다른 버전이므로 새 초안으로 등록하세요."
            )

        row.specification = document
        row.checksum = spec.checksum
        row.domain = str(spec.domain)
        row.compatible_collector_versions = list(spec.compatible_collector_versions)
        # The recorded run described different bytes. Keeping it would let "validate,
        # then edit, then publish" pass the gate.
        row.golden_fixture_results = {}
        changed.append("specification")

    if changelog is not None:
        row.changelog = changelog
        changed.append("changelog")

    session.flush()
    _audit(session, principal, row, "update", request_id, {"changed_fields": changed})
    session.flush()
    return row


def run_golden(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> golden_module.GoldenRun:
    """Replay the golden fixtures and record the outcome on the row."""
    principal.require(Permission.SCORING_SPEC_AUTHOR)
    row = _require_row(session, version_id)
    versions.assert_row_writable(versions.parse_status(row.status))

    spec = _verified_spec(row)
    run = golden_module.run_golden_fixtures(spec)
    row.golden_fixture_results = run.to_record()
    session.flush()

    _audit(
        session,
        principal,
        row,
        "golden_run",
        request_id,
        {"all_passed": run.all_passed, "total": run.total, "failed": run.failed_count},
    )
    session.flush()
    return run


# --------------------------------------------------------------------------- #
# Transitions
# --------------------------------------------------------------------------- #


def submit_for_review(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> ScoringVersion:
    principal.require(Permission.SCORING_SPEC_AUTHOR)
    row = _require_row(session, version_id)
    return _move(session, principal, row, SpecStatus.REVIEW, "submit", request_id)


def send_back(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> ScoringVersion:
    """Return a candidate to DRAFT so its body can be edited again."""
    principal.require(Permission.SCORING_SPEC_AUTHOR)
    row = _require_row(session, version_id)
    return _move(session, principal, row, SpecStatus.DRAFT, "send_back", request_id)


def approve(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> ScoringVersion:
    """Approve a specific checksum. Verified first, so nobody approves a tampered row."""
    principal.require(Permission.SCORING_SPEC_PUBLISH)
    row = _require_row(session, version_id)
    versions.assert_transition(versions.parse_status(row.status), SpecStatus.APPROVED)
    _verified_spec(row)

    row.status = SpecStatus.APPROVED.value
    row.approved_by = None if principal.is_service_account else principal.user_id
    row.approved_at = datetime.now(UTC)
    session.flush()

    _audit(session, principal, row, "approve", request_id, {"checksum": row.checksum})
    session.flush()
    return row


def publish(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> ScoringVersion:
    """Make a version the live methodology, or refuse and say why."""
    principal.require(Permission.SCORING_SPEC_PUBLISH)
    row = _require_row(session, version_id)
    versions.assert_transition(versions.parse_status(row.status), SpecStatus.PUBLISHED)

    spec = _verified_spec(row)
    if spec.status is not SpecStatus.PUBLISHED:
        raise SpecificationRejectedError(
            f"명세 문서의 status가 {spec.status.value}입니다. 발행할 문서는 "
            "status: PUBLISHED로 작성되어 있어야 합니다. VEO는 저장된 문서를 고쳐 쓰지 "
            "않습니다 — 고쳐 쓰면 체크섬이 달라지고, 승인한 내용과 발행한 내용이 "
            "달라집니다."
        )

    golden_module.assert_golden_ready(row.golden_fixture_results, spec_checksum=row.checksum)

    superseded = _retire_current_published(session, principal, row, request_id)

    row.status = SpecStatus.PUBLISHED.value
    row.effective_at = _effective_at(spec)
    session.flush()

    _audit(
        session,
        principal,
        row,
        "publish",
        request_id,
        {
            "checksum": row.checksum,
            "superseded_version": superseded.semantic_version if superseded else None,
        },
    )
    session.flush()
    return row


def retire(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> ScoringVersion:
    principal.require(Permission.SCORING_SPEC_PUBLISH)
    row = _require_row(session, version_id)
    return _move(session, principal, row, SpecStatus.RETIRED, "retire", request_id)


# --------------------------------------------------------------------------- #
# Re-scoring
# --------------------------------------------------------------------------- #


def rescore(
    session: Session,
    principal: Principal,
    version_id: uuid.UUID,
    *,
    scan_run_ids: Sequence[uuid.UUID] | None = None,
    limit: int = DEFAULT_RESCORE_LIMIT,
    request_id: str | None = None,
) -> rescore_module.RescoreSummary:
    """Recompute this organization's stored scores under a published version."""
    principal.require(Permission.SCORING_SPEC_PUBLISH)
    row = _require_row(session, version_id)

    status = versions.parse_status(row.status)
    if status is not SpecStatus.PUBLISHED:
        raise IllegalTransitionError(
            f"{status.value}({versions.label_ko(status)}) 상태의 명세로는 재계산할 수 "
            "없습니다. 발행된 버전으로만 과거 결과를 다시 계산할 수 있습니다."
        )

    spec = _verified_spec(row)
    originals = _rescorable(
        session,
        principal,
        spec_id=row.spec_id,
        semantic_version=row.semantic_version,
        scan_run_ids=scan_run_ids,
        limit=max(1, min(limit, MAX_RESCORE_LIMIT)),
    )
    summary = rescore_module.rescore_results(session, spec, originals)
    session.flush()

    _audit(
        session,
        principal,
        row,
        "rescore",
        request_id,
        {
            "total": summary.total,
            "risen": summary.risen,
            "fallen": summary.fallen,
            "unchanged": summary.unchanged,
            "skipped": summary.skipped,
        },
    )
    session.flush()
    return summary


def _rescorable(
    session: Session,
    principal: Principal,
    *,
    spec_id: str,
    semantic_version: str,
    scan_run_ids: Sequence[uuid.UUID] | None,
    limit: int,
) -> list[ScoreResultRow]:
    statement = (
        tenant_select(ScoreResultRow, principal)
        .where(ScoreResultRow.spec_id == spec_id)
        .where(ScoreResultRow.spec_version != semantic_version)
        # Only originals. Re-scoring a recomputed row would stack derivations and make
        # "the score this run actually got" ambiguous.
        .where(ScoreResultRow.recomputed_from_score_result_id.is_(None))
    )
    if scan_run_ids:
        statement = statement.where(ScoreResultRow.scan_run_id.in_(list(scan_run_ids)))
    statement = statement.order_by(ScoreResultRow.created_at, ScoreResultRow.id).limit(limit)
    assert_tenant_scoped(statement, principal.organization_id)
    return list(session.scalars(statement))


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _require_row(session: Session, version_id: uuid.UUID) -> ScoringVersion:
    row = session.get(ScoringVersion, version_id)
    if row is None:
        raise VersionNotFoundError("점수 명세 버전을 찾을 수 없습니다.")
    return row


def _verified_spec(row: ScoringVersion) -> ScoringSpec:
    """Turn a stored row back into a specification — checksum first, always."""
    versions.verify_checksum(
        specification=row.specification,
        checksum=row.checksum,
        spec_id=row.spec_id,
        semantic_version=row.semantic_version,
    )
    return validation.build_candidate(row.specification)


def _accept(
    document: Mapping[str, Any], baseline: ScoringSpec | None
) -> ScoringSpec:
    """Validate a candidate and return it, or raise with every reason at once."""
    report = validation.validate_candidate(document, baseline=baseline)
    if not report.ok or report.spec is None:
        raise SpecificationRejectedError(
            "점수 명세를 받아들일 수 없습니다: " + " / ".join(report.errors_ko),
            reasons_ko=report.errors_ko,
        )
    return report.spec


def _reject_existing_version(session: Session, spec_id: str, version: str) -> None:
    statement = (
        select(ScoringVersion)
        .where(ScoringVersion.spec_id == spec_id)
        .where(ScoringVersion.semantic_version == version)
        .limit(1)
    )
    if session.scalars(statement).first() is not None:
        raise DuplicateVersionError(
            f"{spec_id}의 {version} 버전은 이미 등록되어 있습니다. "
            "발행된 버전은 바꿀 수 없으므로 새 버전 번호를 사용하세요."
        )


def _move(
    session: Session,
    principal: Principal,
    row: ScoringVersion,
    target: SpecStatus,
    action: str,
    request_id: str | None,
) -> ScoringVersion:
    versions.assert_transition(versions.parse_status(row.status), target)
    row.status = target.value
    session.flush()
    _audit(session, principal, row, action, request_id, {"status": target.value})
    session.flush()
    return row


def _retire_current_published(
    session: Session,
    principal: Principal,
    incoming: ScoringVersion,
    request_id: str | None,
) -> ScoringVersion | None:
    """Retire whatever this version replaces, so "currently published" stays singular."""
    statement = (
        select(ScoringVersion)
        .where(ScoringVersion.spec_id == incoming.spec_id)
        .where(ScoringVersion.status == SpecStatus.PUBLISHED.value)
        .where(ScoringVersion.id != incoming.id)
    )
    superseded: ScoringVersion | None = None
    for row in session.scalars(statement):
        versions.assert_transition(versions.parse_status(row.status), SpecStatus.RETIRED)
        row.status = SpecStatus.RETIRED.value
        superseded = row
        _audit(
            session,
            principal,
            row,
            "retire",
            request_id,
            {"superseded_by": incoming.semantic_version},
        )
    session.flush()
    return superseded


def _effective_at(spec: ScoringSpec) -> datetime:
    """When the specification says it takes effect, or now if it will not parse."""
    try:
        parsed = datetime.fromisoformat(spec.effective_at)
    except ValueError:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _audit(
    session: Session,
    principal: Principal,
    row: ScoringVersion,
    verb: str,
    request_id: str | None,
    detail: dict[str, Any],
) -> None:
    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.{verb}",
        target_type=TARGET_TYPE,
        target_id=row.id,
        request_id=request_id,
        detail={
            "spec_id": row.spec_id,
            "semantic_version": row.semantic_version,
            **detail,
        },
    )
