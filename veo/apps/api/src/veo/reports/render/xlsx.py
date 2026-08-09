"""XLSX export — the same flat rows, written as a minimal OOXML package.

``openpyxl`` and ``xlsxwriter`` are both absent and a new dependency needs a request, so
this follows the approach already proven in ``veo.keywords.export``: one sheet, inline
strings, no styling, built with ``zipfile`` and ``xml.sax.saxutils`` from the standard
library. A minimal file is one that can be read back and checked rather than trusted.

Every cell is an inline string on purpose. A report contains version numbers like
``1.4.0``, checksums, and Korean text that a spreadsheet would happily re-type as a date
or a float on open — and a number that changes shape when the file is opened is exactly
the failure this module exists to prevent.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable, Sequence
from typing import Final
from xml.sax.saxutils import escape, quoteattr

from veo.common.spreadsheet import cell_reference
from veo.reports.render.rows import COLUMNS, SHEET_NAME, report_rows
from veo.reports.snapshot import ReportSnapshot

__all__ = ["XLSX_CONTENT_TYPE", "export_xlsx"]

XLSX_CONTENT_TYPE: Final = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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
<sheets><sheet name="{SHEET_NAME}" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""





def _row_xml(values: Sequence[str], row_index: int) -> str:
    cells = "".join(
        f'<c r={quoteattr(cell_reference(index, row_index))} t="inlineStr">'
        f'<is><t xml:space="preserve">{escape(value)}</t></is></c>'
        for index, value in enumerate(values)
    )
    return f'<row r="{row_index}">{cells}</row>'


def _sheet_xml(header: Sequence[str], rows: Iterable[dict[str, str]]) -> str:
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{_SPREADSHEET_NS}">',
        "<sheetData>",
        _row_xml(list(header), 1),
    ]
    for offset, row in enumerate(rows, start=2):
        parts.append(_row_xml([row[column] for column in header], offset))
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def export_xlsx(
    snapshot: ReportSnapshot,
    *,
    version_number: int | None = None,
    content_hash: str | None = None,
) -> bytes:
    """A minimal, valid OOXML workbook built with the standard library only."""
    rows = report_rows(snapshot, version_number=version_number, content_hash=content_hash)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("xl/workbook.xml", _WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(COLUMNS, rows))
    return buffer.getvalue()
