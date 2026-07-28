"""VEO reports: one frozen measurement, three audiences, three file formats.

A report is an **immutable snapshot**. Re-running the analysis produces a new version;
nothing already published is edited. That single rule is what makes a delivered number
citable — a client quoting "72.5 in the June report" and an analyst reopening that report
have to be reading the same document.

Everything else in the package follows from it:

* :mod:`veo.reports.snapshot` freezes a diagnosis, content-hashes it, and refuses to hold
  a number without its provenance or a blank without its reason.
* :mod:`veo.reports.views` arranges that one snapshot for an executive, a marketer and a
  developer. None of them recomputes anything.
* :mod:`veo.reports.render` encodes the same snapshot as self-contained HTML, CSV and
  XLSX. All three read one flat list of values, so they cannot drift apart.
* :mod:`veo.reports.repository` refuses an ``UPDATE`` against a published version.
* :mod:`veo.reports.service` decides which snapshot is read and whether raw evidence
  travels with it.
"""

from veo.reports.service import ReportNotFoundError, ReportService, ReportVersionConflictError
from veo.reports.snapshot import (
    NOT_APPLICABLE_KO,
    UNMEASURED_KO,
    DiagnosisInput,
    DomainDiagnosis,
    MeasuredValue,
    ReportSnapshot,
    ValueStatus,
    freeze,
    from_payload,
    redact_evidence,
    to_payload,
)
from veo.reports.views import ReportViews, build_views

__all__ = [
    "NOT_APPLICABLE_KO",
    "UNMEASURED_KO",
    "DiagnosisInput",
    "DomainDiagnosis",
    "MeasuredValue",
    "ReportNotFoundError",
    "ReportService",
    "ReportSnapshot",
    "ReportVersionConflictError",
    "ReportViews",
    "ValueStatus",
    "build_views",
    "freeze",
    "from_payload",
    "redact_evidence",
    "to_payload",
]
