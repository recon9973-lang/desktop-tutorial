"""CSV export — the flat rows, encoded for a spreadsheet application."""

from __future__ import annotations

import csv
import io
from typing import Final

from veo.reports.render.rows import COLUMNS, report_rows
from veo.reports.snapshot import ReportSnapshot

__all__ = ["CSV_CONTENT_TYPE", "export_csv"]

CSV_CONTENT_TYPE: Final = "text/csv; charset=utf-8"


def export_csv(
    snapshot: ReportSnapshot,
    *,
    version_number: int | None = None,
    content_hash: str | None = None,
) -> bytes:
    """UTF-8 with a BOM, because Excel on Windows reads Korean as mojibake without it."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(COLUMNS), lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(
        report_rows(snapshot, version_number=version_number, content_hash=content_hash)
    )
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
