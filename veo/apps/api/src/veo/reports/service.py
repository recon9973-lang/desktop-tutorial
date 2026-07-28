"""Creating, reading and exporting report versions.

The service owns two decisions the renderers must not make:

* **Which snapshot.** A read never re-runs a diagnosis. It loads the stored payload,
  verifies its content hash, and hands the frozen object on. HTML, CSV and XLSX are then
  three encodings of that one object.
* **Whether raw evidence travels with it.** A caller without ``EVIDENCE_READ`` gets the
  report with the excerpts removed — not a ``403`` for the whole document. The scores,
  the coverage, the confidence and the methodology are all still there; only the raw
  material is withheld, and the reference to it stays so the reader knows it exists.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal

from sqlalchemy.exc import IntegrityError

from veo.authz import Permission, Principal
from veo.reports.render.csv import CSV_CONTENT_TYPE, export_csv
from veo.reports.render.html import HTML_CONTENT_TYPE, render_html
from veo.reports.render.xlsx import XLSX_CONTENT_TYPE, export_xlsx
from veo.reports.repository import SqlReportRepository, StoredVersion
from veo.reports.snapshot import (
    DiagnosisInput,
    ReportSnapshot,
    freeze,
    from_payload,
    redact_evidence,
    to_payload,
)
from veo.reports.views import ReportViews, build_views

__all__ = [
    "EXPORT_FORMATS",
    "ExportFormat",
    "ExportResult",
    "LoadedReport",
    "ReportNotFoundError",
    "ReportService",
    "ReportVersionConflictError",
]

ExportFormat = Literal["html", "csv", "xlsx"]

EXPORT_FORMATS: Final[tuple[str, ...]] = ("html", "csv", "xlsx")


class ReportNotFoundError(LookupError):
    """The report, the version or the project is not there — or not this tenant's."""


class ReportVersionConflictError(RuntimeError):
    """Two writers raced for the same version number."""


@dataclass(frozen=True, slots=True)
class CreatedVersion:
    report_id: uuid.UUID
    project_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    content_hash: str
    title_ko: str
    audience: str
    generated_at: datetime
    scoring_versions: dict[str, dict[str, str]]
    export_formats: tuple[str, ...]
    snapshot: ReportSnapshot


@dataclass(frozen=True, slots=True)
class LoadedReport:
    """One stored version, read back and projected for a specific caller."""

    stored: StoredVersion
    snapshot: ReportSnapshot
    views: ReportViews
    evidence_included: bool

    @property
    def content_hash(self) -> str:
        return self.stored.content_hash


@dataclass(frozen=True, slots=True)
class ExportResult:
    body: bytes
    media_type: str
    filename: str


class ReportService:
    def __init__(self, repository: SqlReportRepository) -> None:
        self._repository = repository

    # -------------------------------------------------------------- writing #

    def create_report(
        self,
        *,
        principal: Principal,
        project_id: uuid.UUID,
        diagnosis: DiagnosisInput,
    ) -> CreatedVersion:
        """Open a new report on a project and freeze version 1."""
        if not self._repository.project_belongs_to_tenant(principal, project_id):
            raise ReportNotFoundError("project")

        report = self._repository.create_report(
            principal,
            project_id=project_id,
            title=diagnosis.title_ko,
            audience=diagnosis.audience,
        )
        return self._freeze_into(principal, report_id=report.id, diagnosis=diagnosis)

    def create_version(
        self, *, principal: Principal, report_id: uuid.UUID, diagnosis: DiagnosisInput
    ) -> CreatedVersion:
        """Freeze another version of an existing report. Nothing existing is touched."""
        if self._repository.get_report(principal, report_id) is None:
            raise ReportNotFoundError("report")
        return self._freeze_into(principal, report_id=report_id, diagnosis=diagnosis)

    def _freeze_into(
        self, principal: Principal, *, report_id: uuid.UUID, diagnosis: DiagnosisInput
    ) -> CreatedVersion:
        report = self._repository.get_report(principal, report_id)
        if report is None:  # pragma: no cover - guarded by both callers
            raise ReportNotFoundError("report")

        previous = self._repository.latest_version(principal, report_id)
        previous_snapshot = (
            from_payload(previous.content) if previous is not None else None
        )

        snapshot = freeze(diagnosis, previous=previous_snapshot)
        payload = to_payload(snapshot)
        version_number = self._repository.next_version_number(principal, report_id)

        try:
            stored = self._repository.add_version(
                principal,
                report=report,
                version_number=version_number,
                content=payload,
                scoring_versions=snapshot.scoring_versions(),
                disclosures_ko=snapshot.disclosures_ko,
                export_formats=EXPORT_FORMATS,
                included_run_ids=snapshot.included_run_ids,
                measurement_window_start=snapshot.measurement_window_start,
                measurement_window_end=snapshot.measurement_window_end,
            )
        except IntegrityError as exc:
            raise ReportVersionConflictError(
                "같은 버전 번호가 이미 발행되었습니다. 다시 시도해 주세요."
            ) from exc

        return CreatedVersion(
            report_id=report_id,
            project_id=report.project_id,
            version_id=stored.version_id,
            version_number=stored.version_number,
            content_hash=stored.content_hash,
            title_ko=stored.title_ko,
            audience=stored.audience,
            generated_at=snapshot.generated_at,
            scoring_versions=snapshot.scoring_versions(),
            export_formats=EXPORT_FORMATS,
            snapshot=snapshot,
        )

    # -------------------------------------------------------------- reading #

    def list_versions(
        self, *, principal: Principal, report_id: uuid.UUID
    ) -> list[StoredVersion]:
        if self._repository.get_report(principal, report_id) is None:
            raise ReportNotFoundError("report")
        return self._repository.list_versions(principal, report_id)

    def read_version(
        self, *, principal: Principal, report_id: uuid.UUID, version_number: int
    ) -> LoadedReport:
        stored = self._repository.get_version(principal, report_id, version_number)
        if stored is None:
            raise ReportNotFoundError("version")

        snapshot = from_payload(stored.content)
        included = principal.has(Permission.EVIDENCE_READ)
        if not included:
            snapshot = redact_evidence(snapshot)

        return LoadedReport(
            stored=stored,
            snapshot=snapshot,
            views=build_views(snapshot),
            evidence_included=included,
        )

    def export(
        self,
        *,
        principal: Principal,
        report_id: uuid.UUID,
        version_number: int,
        export_format: ExportFormat,
    ) -> ExportResult:
        """One snapshot, encoded three ways. The numbers cannot differ between them."""
        loaded = self.read_version(
            principal=principal, report_id=report_id, version_number=version_number
        )
        stem = f"veo-report-{report_id}-v{version_number}"

        if export_format == "html":
            body = render_html(
                loaded.snapshot,
                views=loaded.views,
                version_number=version_number,
                content_hash=loaded.content_hash,
            ).encode("utf-8")
            return ExportResult(body, HTML_CONTENT_TYPE, f"{stem}.html")

        if export_format == "csv":
            return ExportResult(
                export_csv(
                    loaded.snapshot,
                    version_number=version_number,
                    content_hash=loaded.content_hash,
                ),
                CSV_CONTENT_TYPE,
                f"{stem}.csv",
            )

        return ExportResult(
            export_xlsx(
                loaded.snapshot,
                version_number=version_number,
                content_hash=loaded.content_hash,
            ),
            XLSX_CONTENT_TYPE,
            f"{stem}.xlsx",
        )
