"""Persistence for reports and their versions.

``ReportVersion`` is declared with ``ImmutableMixin`` — it carries no ``updated_at``,
because a row that can be edited is a row whose history nobody can trust. That is a
statement of intent in the model; this module makes it a fact at runtime.

The guard below refuses any ``UPDATE`` against ``report_versions``. A correction is a new
version, never an edit: the number a client was given six months ago has to still be
there, unchanged, when they quote it back.

**A database-level trigger would be stronger** and is requested in
``INTEGRATION_REQUEST.md`` (#2) — migrations are outside this worker's scope. Until it
lands, an ``UPDATE`` issued outside the ORM would not be caught here.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import event, func, select
from sqlalchemy.orm import Mapper, Session

from veo.authz import Permission, Principal, assert_tenant_scoped, tenant_select
from veo.db.models.identity import Project
from veo.db.models.observation import Report, ReportVersion

__all__ = [
    "ReportVersionImmutableError",
    "SqlReportRepository",
    "StoredVersion",
    "report_read_permissions",
]


class ReportVersionImmutableError(RuntimeError):
    """Someone tried to change a published report version."""

    def __init__(self, version_id: uuid.UUID | None = None) -> None:
        super().__init__(
            "발행된 리포트 버전은 수정할 수 없습니다. 재측정 결과는 새 버전으로 발행하십시오."
            + (f" (version_id={version_id})" if version_id else "")
        )


@event.listens_for(ReportVersion, "before_update", propagate=True)
def _refuse_report_version_update(
    mapper: Mapper[ReportVersion], connection: Any, target: ReportVersion
) -> None:
    """Fail the flush rather than let a delivered number change under a client."""
    raise ReportVersionImmutableError(getattr(target, "id", None))


def report_read_permissions() -> tuple[Permission, ...]:
    return (Permission.REPORT_READ,)


@dataclass(frozen=True, slots=True)
class StoredVersion:
    """The row as the service needs it, without leaking the ORM object upwards."""

    version_id: uuid.UUID
    report_id: uuid.UUID
    project_id: uuid.UUID
    version_number: int
    title_ko: str
    audience: str
    generated_at: datetime
    content: dict[str, Any]
    scoring_versions: dict[str, Any]
    disclosures_ko: list[Any]
    export_formats: list[Any]
    included_run_ids: list[Any]
    measurement_window_start: datetime | None
    measurement_window_end: datetime | None

    @property
    def content_hash(self) -> str:
        value = self.content.get("content_hash")
        return str(value) if value else ""


class SqlReportRepository:
    """Every read is tenant-scoped by construction, then checked before execution."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ---------------------------------------------------------------- reads #

    def project_belongs_to_tenant(self, principal: Principal, project_id: uuid.UUID) -> bool:
        statement = tenant_select(Project, principal).where(Project.id == project_id)
        assert_tenant_scoped(statement, principal.organization_id)
        return self._session.scalars(statement).first() is not None

    def get_report(self, principal: Principal, report_id: uuid.UUID) -> Report | None:
        statement = tenant_select(Report, principal).where(Report.id == report_id)
        assert_tenant_scoped(statement, principal.organization_id)
        return self._session.scalars(statement).first()

    def list_reports(
        self, principal: Principal, project_id: uuid.UUID | None = None
    ) -> list[tuple[Report, StoredVersion | None]]:
        """이 조직의 리포트들과 각자의 최신 버전. 최근에 만든 것이 먼저.

        버전이 하나도 없는 리포트도 목록에 남긴다. 감추면 "만들다 만 것" 이 흔적 없이
        사라지고, 왜 안 보이는지 아무도 모른다.
        """
        statement = tenant_select(Report, principal).order_by(Report.created_at.desc())
        if project_id is not None:
            statement = statement.where(Report.project_id == project_id)
        assert_tenant_scoped(statement, principal.organization_id)
        reports = list(self._session.scalars(statement).all())
        return [(report, self.latest_version(principal, report.id)) for report in reports]

    def list_versions(
        self, principal: Principal, report_id: uuid.UUID
    ) -> list[StoredVersion]:
        report = self.get_report(principal, report_id)
        if report is None:
            return []
        statement = (
            tenant_select(ReportVersion, principal)
            .where(ReportVersion.report_id == report_id)
            .order_by(ReportVersion.version_number.desc())
        )
        assert_tenant_scoped(statement, principal.organization_id)
        rows = self._session.scalars(statement).all()
        return [self._stored(report, row) for row in rows]

    def get_version(
        self, principal: Principal, report_id: uuid.UUID, version_number: int
    ) -> StoredVersion | None:
        report = self.get_report(principal, report_id)
        if report is None:
            return None
        statement = (
            tenant_select(ReportVersion, principal)
            .where(ReportVersion.report_id == report_id)
            .where(ReportVersion.version_number == version_number)
        )
        assert_tenant_scoped(statement, principal.organization_id)
        row = self._session.scalars(statement).first()
        return None if row is None else self._stored(report, row)

    def latest_version(
        self, principal: Principal, report_id: uuid.UUID
    ) -> StoredVersion | None:
        versions = self.list_versions(principal, report_id)
        return versions[0] if versions else None

    def next_version_number(self, principal: Principal, report_id: uuid.UUID) -> int:
        statement = (
            select(func.max(ReportVersion.version_number))
            .where(ReportVersion.report_id == report_id)
            .where(ReportVersion.organization_id == principal.organization_id)
        )
        assert_tenant_scoped(statement, principal.organization_id)
        highest = self._session.scalar(statement)
        return 1 if highest is None else int(highest) + 1

    # --------------------------------------------------------------- writes #

    def create_report(
        self, principal: Principal, *, project_id: uuid.UUID, title: str, audience: str
    ) -> Report:
        report = Report(
            organization_id=principal.organization_id,
            project_id=project_id,
            title=title,
            audience=audience,
        )
        self._session.add(report)
        self._session.flush()
        return report

    def add_version(
        self,
        principal: Principal,
        *,
        report: Report,
        version_number: int,
        content: dict[str, Any],
        scoring_versions: dict[str, Any],
        disclosures_ko: Sequence[str],
        export_formats: Sequence[str],
        included_run_ids: Sequence[str],
        measurement_window_start: datetime | None,
        measurement_window_end: datetime | None,
    ) -> StoredVersion:
        row = ReportVersion(
            organization_id=principal.organization_id,
            report_id=report.id,
            version_number=version_number,
            generated_by=principal.user_id,
            measurement_window_start=measurement_window_start,
            measurement_window_end=measurement_window_end,
            included_run_ids=list(included_run_ids),
            scoring_versions=dict(scoring_versions),
            content=content,
            disclosures_ko=list(disclosures_ko),
            export_formats=list(export_formats),
        )
        self._session.add(row)
        self._session.flush()
        return self._stored(report, row)

    # -------------------------------------------------------------- mapping #

    @staticmethod
    def _stored(report: Report, row: ReportVersion) -> StoredVersion:
        return StoredVersion(
            version_id=row.id,
            report_id=row.report_id,
            project_id=report.project_id,
            version_number=row.version_number,
            title_ko=report.title,
            audience=report.audience,
            generated_at=row.created_at,
            content=dict(row.content),
            scoring_versions=dict(row.scoring_versions),
            disclosures_ko=list(row.disclosures_ko),
            export_formats=list(row.export_formats),
            included_run_ids=list(row.included_run_ids),
            measurement_window_start=row.measurement_window_start,
            measurement_window_end=row.measurement_window_end,
        )
