"""CSV and XLSX export of a recorded lookup.

Two rules shape every cell:

**An unmeasured value is an empty cell, never ``0``.** A spreadsheet is where a figure
stops carrying its context — nobody hovers a cell to read a quality flag — so each value
column is followed by its own ``*_quality`` column, and the numeric cell is left blank
whenever there is no number. A reader who sorts by volume then sees blanks, not a block of
zeroes indistinguishable from genuinely unsearched keywords.

**A cell that could be read as a formula is neutralised.** ``=``, ``+``, ``-``, ``@`` and
the two control characters Excel treats as formula starters are prefixed with an
apostrophe. A keyword is attacker-influenced text — a customer can type anything into the
lookup box — and a CSV opened in Excel executes what it finds.

The XLSX writer is written against the OOXML package format using only the standard
library. ``openpyxl`` is not installed and adding a dependency needs a request
(``INTEGRATION_REQUEST.md`` #4); the workbook produced here is deliberately minimal —
one sheet, inline strings, no styling — because a minimal file is one that can be read
back and checked rather than trusted.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Final
from xml.sax.saxutils import escape, quoteattr

from veo.common.spreadsheet import cell_reference
from veo.keywords.service import KeywordLookupResult

__all__ = [
    "COLUMNS",
    "CSV_CONTENT_TYPE",
    "XLSX_CONTENT_TYPE",
    "export_csv",
    "export_xlsx",
    "rows_for_export",
]

CSV_CONTENT_TYPE: Final = "text/csv; charset=utf-8"
XLSX_CONTENT_TYPE: Final = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

#: Characters Excel and LibreOffice treat as the start of a formula.
_FORMULA_STARTERS: Final = ("=", "+", "-", "@", "\t", "\r")

COLUMNS: Final[tuple[str, ...]] = (
    "normalized_keyword",
    "original_keyword",
    "source",
    "collected_at",
    "api_version",
    "raw_response_hash",
    "monthly_pc_searches",
    "monthly_pc_searches_quality",
    "monthly_mobile_searches",
    "monthly_mobile_searches_quality",
    "monthly_total_searches",
    "monthly_total_searches_quality",
    "monthly_total_searches_source",
    "avg_pc_clicks",
    "avg_pc_clicks_quality",
    "avg_mobile_clicks",
    "avg_mobile_clicks_quality",
    "avg_pc_ctr",
    "avg_pc_ctr_quality",
    "avg_mobile_ctr",
    "avg_mobile_ctr_quality",
    "competition_label",
    "competition_index",
    "ad_depth",
    "trend_source",
    "trend_unit",
    "trend_latest_relative_index",
    "opportunity_formula_version",
    "opportunity_score",
    "opportunity_confidence",
    "opportunity_source",
)


def _text(value: object) -> str:
    """Render a cell. ``None`` is an empty cell — never a zero and never "None"."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)


def _neutralise(value: str) -> str:
    """Prefix a formula-shaped cell so a spreadsheet renders it as text."""
    if value.startswith(_FORMULA_STARTERS):
        return f"'{value}"
    return value


def rows_for_export(result: KeywordLookupResult) -> list[dict[str, str]]:
    """One row per requested keyword, every value beside its quality."""
    rows: list[dict[str, str]] = []
    for snapshot in result.snapshots:
        metric = snapshot.metrics
        trend = snapshot.trend
        opportunity = snapshot.opportunity
        latest = trend.points[-1] if trend and trend.points else None

        row: dict[str, object] = {
            "normalized_keyword": snapshot.normalized_keyword,
            "original_keyword": snapshot.original_keyword,
            "source": None if metric is None else metric.source.value,
            "collected_at": None if metric is None else metric.collected_at,
            "api_version": None if metric is None else metric.api_version,
            "raw_response_hash": None if metric is None else metric.raw_response_hash,
            "monthly_pc_searches": None if metric is None else metric.monthly_pc_searches,
            "monthly_pc_searches_quality": (
                None if metric is None else metric.monthly_pc_searches_quality.value
            ),
            "monthly_mobile_searches": (
                None if metric is None else metric.monthly_mobile_searches
            ),
            "monthly_mobile_searches_quality": (
                None if metric is None else metric.monthly_mobile_searches_quality.value
            ),
            "monthly_total_searches": (
                None if metric is None else metric.monthly_total_searches
            ),
            "monthly_total_searches_quality": (
                None if metric is None else metric.monthly_total_searches_quality.value
            ),
            # Spelled out in its own column so nobody reads the total as a Naver figure.
            "monthly_total_searches_source": None if metric is None else "CALCULATED",
            "avg_pc_clicks": None if metric is None else metric.avg_pc_clicks,
            "avg_pc_clicks_quality": (
                None if metric is None else metric.avg_pc_clicks_quality.value
            ),
            "avg_mobile_clicks": None if metric is None else metric.avg_mobile_clicks,
            "avg_mobile_clicks_quality": (
                None if metric is None else metric.avg_mobile_clicks_quality.value
            ),
            "avg_pc_ctr": None if metric is None else metric.avg_pc_ctr,
            "avg_pc_ctr_quality": None if metric is None else metric.avg_pc_ctr_quality.value,
            "avg_mobile_ctr": None if metric is None else metric.avg_mobile_ctr,
            "avg_mobile_ctr_quality": (
                None if metric is None else metric.avg_mobile_ctr_quality.value
            ),
            "competition_label": None if metric is None else metric.competition_label,
            "competition_index": None if metric is None else metric.competition_index,
            "ad_depth": None if metric is None else metric.ad_depth,
            "trend_source": None if trend is None else trend.source.value,
            "trend_unit": None if trend is None else trend.unit,
            "trend_latest_relative_index": None if latest is None else latest.relative_index,
            "opportunity_formula_version": (
                None if opportunity is None else opportunity.formula_version
            ),
            "opportunity_score": None if opportunity is None else opportunity.score,
            "opportunity_confidence": (
                None if opportunity is None else opportunity.confidence
            ),
            "opportunity_source": None if opportunity is None else opportunity.source.value,
        }
        rows.append({column: _neutralise(_text(row[column])) for column in COLUMNS})
    return rows


def export_csv(result: KeywordLookupResult) -> bytes:
    """UTF-8 with a BOM, because Excel on Windows reads Korean as mojibake without it."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(COLUMNS), lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows_for_export(result))
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


# --------------------------------------------------------------------------- #
# XLSX
# --------------------------------------------------------------------------- #

_OOXML_PACKAGE_NS = "http://schemas.openxmlformats.org/package/2006"
_OOXML_DOC_NS = "http://schemas.openxmlformats.org/officeDocument/2006"
_SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_SHEET_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml"

_CONTENT_TYPES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{_OOXML_PACKAGE_NS}/content-types">
<Default Extension="rels"
 ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="{_SHEET_TYPE}.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{_SHEET_TYPE}.worksheet+xml"/>
</Types>"""

_ROOT_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{_OOXML_PACKAGE_NS}/relationships">
<Relationship Id="rId1" Type="{_OOXML_DOC_NS}/relationships/officeDocument"
 Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{_OOXML_PACKAGE_NS}/relationships">
<Relationship Id="rId1" Type="{_OOXML_DOC_NS}/relationships/worksheet"
 Target="worksheets/sheet1.xml"/>
</Relationships>"""

_WORKBOOK = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{_SPREADSHEET_NS}" xmlns:r="{_OOXML_DOC_NS}/relationships">
<sheets><sheet name="keywords" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""





def _sheet_xml(header: Sequence[str], rows: Iterable[dict[str, str]]) -> str:
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{_SPREADSHEET_NS}">',
        "<sheetData>",
    ]

    def row_xml(values: Sequence[str], row_index: int) -> str:
        cells = "".join(
            # Inline strings throughout: every cell is text, so a keyword that looks like
            # a number or a date cannot be re-typed by the spreadsheet on open.
            f'<c r={quoteattr(cell_reference(index, row_index))} t="inlineStr">'
            f"<is><t xml:space=\"preserve\">{escape(value)}</t></is></c>"
            for index, value in enumerate(values)
        )
        return f'<row r="{row_index}">{cells}</row>'

    lines.append(row_xml(list(header), 1))
    for offset, row in enumerate(rows, start=2):
        lines.append(row_xml([row[column] for column in header], offset))

    lines.append("</sheetData></worksheet>")
    return "".join(lines)


def export_xlsx(result: KeywordLookupResult) -> bytes:
    """A minimal, valid OOXML workbook built with the standard library only."""
    rows = rows_for_export(result)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("xl/workbook.xml", _WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(COLUMNS, rows))
    return buffer.getvalue()
