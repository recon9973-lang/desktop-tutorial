"""The flat shape behind both spreadsheet exports.

CSV and XLSX are two encodings of *this* list. They do not each walk the snapshot, so
there is no second traversal that could round differently, skip a section, or print a
blank where the other printed ``측정 불가``.

Two rules carried over from ``veo.keywords.export``, for the same reasons:

**A missing measurement is a blank numeric cell, never a zero.** Nobody hovers a
spreadsheet cell to read its footnote, so every value column is followed by the columns
that explain it — ``display`` always spells the value out in Korean (``측정 불가`` /
``해당 없음`` / the number), ``value_status_ko`` names the state, ``reason_ko`` gives the
reason, and ``source`` names where it came from.

**A cell that could be read as a formula is neutralised.** URLs, titles and remediation
text in a report are influenced by the site being measured, and a CSV opened in Excel
executes what it finds.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Final

from veo.reports.snapshot import MeasuredValue, Provenance, ReportSnapshot, ValueStatus

__all__ = ["COLUMNS", "SHEET_NAME", "neutralise", "report_rows"]

SHEET_NAME: Final = "veo-report"

#: Characters Excel and LibreOffice treat as the start of a formula.
_FORMULA_STARTERS: Final = ("=", "+", "-", "@", "\t", "\r")

COLUMNS: Final[tuple[str, ...]] = (
    "report_title",
    "report_version",
    "report_content_hash",
    "report_methodology",
    "generated_at",
    "section",
    "domain",
    "metric_key",
    "label_ko",
    "display",
    "value",
    "unit",
    "value_status",
    "value_status_ko",
    "reason_ko",
    "source",
    "provenance",
    "spec_id",
    "spec_version",
    "spec_checksum",
    "collector_version",
    "measured_at",
    "coverage",
    "confidence",
    "evidence_ids",
    "note_ko",
)


def neutralise(value: str) -> str:
    """Prefix a formula-shaped cell so a spreadsheet renders it as text."""
    if value.startswith(_FORMULA_STARTERS):
        return f"'{value}"
    return value


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _numeric_cell(value: MeasuredValue) -> str:
    """The number, or an empty cell.

    Never ``0`` and never ``-``: a reader who sorts this column must see blanks for the
    unmeasured rows, and read the neighbouring ``display`` column to find out why.
    """
    if value.status is not ValueStatus.MEASURED or value.value is None:
        return ""
    return value.display()


def _provenance_cells(entry: Provenance | None) -> dict[str, str]:
    if entry is None:
        return {
            "provenance": "",
            "spec_id": "",
            "spec_version": "",
            "spec_checksum": "",
            "collector_version": "",
            "measured_at": "",
            "coverage": "",
            "confidence": "",
        }
    return {
        "provenance": entry.label_ko,
        "spec_id": _text(entry.spec_id),
        "spec_version": _text(entry.spec_version),
        "spec_checksum": _text(entry.spec_checksum),
        "collector_version": _text(entry.collector_version),
        "measured_at": _text(entry.measured_at),
        "coverage": entry.coverage.display() if entry.coverage else "",
        "confidence": entry.confidence.display() if entry.confidence else "",
    }


def _rows(
    snapshot: ReportSnapshot, *, version_number: int | None, content_hash: str
) -> Iterator[dict[str, object]]:
    methodology = snapshot.methodology_summary_ko()
    common: dict[str, object] = {
        "report_title": snapshot.report_title_ko,
        "report_version": "" if version_number is None else version_number,
        "report_content_hash": content_hash,
        "report_methodology": methodology,
        "generated_at": snapshot.generated_at,
    }

    for row in snapshot.metrics:
        entry = snapshot.provenance.get(row.provenance_ref)
        yield {
            **common,
            "section": row.section,
            "domain": _text(row.domain),
            "metric_key": row.metric_key,
            "label_ko": row.label_ko,
            "display": row.value.display(),
            "value": _numeric_cell(row.value),
            "unit": row.value.unit,
            "value_status": row.value.status.value,
            "value_status_ko": row.value.status_ko,
            "reason_ko": _text(row.value.reason_ko),
            "source": row.value.source,
            **_provenance_cells(entry),
            "evidence_ids": " ".join(row.evidence_ids),
            "note_ko": row.note_ko,
        }

    for change in snapshot.changes:
        entry = snapshot.provenance.get(change.domain) if change.domain else None
        yield {
            **common,
            "section": "변화",
            "domain": _text(change.domain),
            "metric_key": f"change.{change.metric_key}",
            "label_ko": f"{change.label_ko} 변화량",
            "display": change.delta.display(),
            "value": _numeric_cell(change.delta),
            "unit": change.delta.unit,
            "value_status": change.delta.status.value,
            "value_status_ko": change.delta.status_ko,
            "reason_ko": _text(change.delta.reason_ko),
            "source": change.delta.source,
            **_provenance_cells(entry),
            "evidence_ids": "",
            "note_ko": (
                f"이전 {change.previous.display()} → 현재 {change.current.display()} "
                f"({change.direction})"
            ),
        }


def report_rows(
    snapshot: ReportSnapshot,
    *,
    version_number: int | None = None,
    content_hash: str | None = None,
) -> list[dict[str, str]]:
    """One row per fact in the snapshot, every cell already a string.

    ``content_hash`` is passed in by the service so that a gated export — which drops raw
    excerpts and therefore no longer hashes to the same bytes — still names the hash the
    version was *published* with. The numbers are identical either way; only the raw
    material differs.
    """
    from veo.reports.snapshot import compute_content_hash

    resolved = content_hash or compute_content_hash(snapshot)
    return [
        {column: neutralise(_text(row[column])) for column in COLUMNS}
        for row in _rows(snapshot, version_number=version_number, content_hash=resolved)
    ]
