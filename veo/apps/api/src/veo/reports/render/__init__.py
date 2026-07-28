"""Encoders for a frozen report snapshot.

HTML, CSV and XLSX are three encodings of one object, not three renderings of a
diagnosis. The spreadsheet formats share :mod:`veo.reports.render.rows`, and the HTML
prints ``MeasuredValue.display()`` — the same string those rows carry — so a figure on a
printed page and a figure in a spreadsheet cell cannot disagree.
"""

from veo.reports.render.csv import CSV_CONTENT_TYPE, export_csv
from veo.reports.render.html import HTML_CONTENT_TYPE, render_html
from veo.reports.render.rows import COLUMNS, report_rows
from veo.reports.render.xlsx import XLSX_CONTENT_TYPE, export_xlsx

__all__ = [
    "COLUMNS",
    "CSV_CONTENT_TYPE",
    "HTML_CONTENT_TYPE",
    "XLSX_CONTENT_TYPE",
    "export_csv",
    "export_xlsx",
    "render_html",
    "report_rows",
]
