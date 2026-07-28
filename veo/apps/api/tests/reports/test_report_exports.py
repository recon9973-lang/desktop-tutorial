"""HTML, CSV and XLSX are three views of one snapshot — never three renderings.

The failure this guards against is quiet: a spreadsheet that says 72.5 and a PDF that
says 73 because one of them rounded, or a CSV that shows a blank where the HTML showed
``측정 불가``. Both make the report unciteable.
"""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree

from report_support import (
    EVIDENCE_SENTINEL,
    GEO_OVERALL,
    SEO_CONTENT_SCORE,
    SEO_CRAWL_SCORE,
    SEO_OVERALL,
    SPEC_CHECKSUM,
    SPEC_VERSION,
    UNKNOWN_REASON,
    make_diagnosis,
)

from veo.reports.render.csv import CSV_CONTENT_TYPE, export_csv
from veo.reports.render.html import render_html
from veo.reports.render.rows import COLUMNS, report_rows
from veo.reports.render.xlsx import XLSX_CONTENT_TYPE, export_xlsx
from veo.reports.snapshot import NOT_APPLICABLE_KO, UNMEASURED_KO, freeze, redact_evidence
from veo.reports.views import build_views

_SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _snapshot():  # type: ignore[no-untyped-def]
    return freeze(make_diagnosis())


def _csv_rows(body: bytes) -> list[dict[str, str]]:
    import csv

    text = body.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _xlsx_rows(body: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml")
    # S314: the XML parsed here is the workbook this test just produced, not input
    # from anywhere else.
    root = ElementTree.fromstring(sheet)  # noqa: S314
    rows: list[list[str]] = []
    for row in root.iter(f"{_SHEET_NS}row"):
        values: list[str] = []
        for cell in row.iter(f"{_SHEET_NS}c"):
            text = cell.find(f"{_SHEET_NS}is/{_SHEET_NS}t")
            values.append("" if text is None or text.text is None else text.text)
        rows.append(values)
    return rows


# --------------------------------------------------------------------------- #
# One snapshot, three formats, identical numbers
# --------------------------------------------------------------------------- #


def test_the_same_number_appears_identically_in_html_csv_and_xlsx() -> None:
    snapshot = _snapshot()
    markup = render_html(snapshot)
    csv_rows = _csv_rows(export_csv(snapshot))
    xlsx_rows = _xlsx_rows(export_xlsx(snapshot))

    header = xlsx_rows[0]
    display_at = header.index("display")
    key_at = header.index("metric_key")
    xlsx_by_key = {row[key_at]: row[display_at] for row in xlsx_rows[1:]}
    csv_by_key = {row["metric_key"]: row["display"] for row in csv_rows}

    for row in snapshot.metrics:
        rendered = row.value.display()
        assert csv_by_key[row.metric_key] == rendered
        assert xlsx_by_key[row.metric_key] == rendered
        assert rendered in markup, f"{row.metric_key} ({rendered}) missing from the HTML"


def test_the_three_audience_views_and_the_three_formats_agree_on_one_number() -> None:
    snapshot = _snapshot()
    views = build_views(snapshot)
    key = "SEO_READINESS.overall"
    rendered = views.executive.number(key).display()

    assert rendered == str(SEO_OVERALL)
    assert views.marketing.number(key).display() == rendered
    assert views.developer.number(key).display() == rendered

    assert rendered in render_html(snapshot)
    assert any(row["display"] == rendered for row in _csv_rows(export_csv(snapshot)))
    assert any(rendered in row for row in _xlsx_rows(export_xlsx(snapshot)))


def test_the_headline_numbers_are_present_in_every_format() -> None:
    snapshot = _snapshot()
    markup = render_html(snapshot)
    csv_body = export_csv(snapshot).decode("utf-8-sig")
    xlsx_text = "\n".join("\t".join(row) for row in _xlsx_rows(export_xlsx(snapshot)))

    for number in (SEO_OVERALL, GEO_OVERALL, SEO_CRAWL_SCORE, SEO_CONTENT_SCORE):
        rendered = str(number)
        assert rendered in markup
        assert rendered in csv_body
        assert rendered in xlsx_text


# --------------------------------------------------------------------------- #
# Flat exports: every row explains itself
# --------------------------------------------------------------------------- #


def test_every_flat_row_carries_its_source_and_its_status() -> None:
    rows = report_rows(_snapshot())
    assert rows
    for row in rows:
        assert set(row) == set(COLUMNS)
        assert row["source"], row
        assert row["value_status"] in {"MEASURED", "UNMEASURED", "NOT_APPLICABLE"}
        assert row["value_status_ko"] in {"측정됨", UNMEASURED_KO, NOT_APPLICABLE_KO}
        assert row["display"]
        # Every row names the methodology behind the document, even the rows whose own
        # value came from a provider rather than from a scoring specification.
        assert SPEC_VERSION in row["report_methodology"]
        assert SPEC_CHECKSUM in row["report_methodology"]
        if row["domain"] and row["provenance"]:
            assert row["spec_version"]
            assert row["spec_checksum"]


def test_an_unmeasured_cell_is_blank_in_the_number_column_and_named_beside_it() -> None:
    rows = {row["metric_key"]: row for row in report_rows(_snapshot())}
    indexing = rows["SEO_READINESS.category.indexing"]

    assert indexing["value"] == ""
    assert indexing["display"] == UNMEASURED_KO
    assert indexing["value_status_ko"] == UNMEASURED_KO
    assert UNKNOWN_REASON in indexing["reason_ko"]

    i18n = rows["SEO_READINESS.category.i18n"]
    assert i18n["value"] == ""
    assert i18n["display"] == NOT_APPLICABLE_KO
    assert i18n["reason_ko"]


def test_no_export_ever_writes_a_zero_where_a_measurement_is_missing() -> None:
    for row in report_rows(_snapshot()):
        if row["value_status"] == "MEASURED":
            continue
        assert row["value"] == ""
        assert row["display"] != "0"
        assert row["display"] != "0.0"


def test_every_export_names_the_methodology_version_and_checksum() -> None:
    snapshot = _snapshot()

    markup = render_html(snapshot)
    assert SPEC_VERSION in markup and SPEC_CHECKSUM in markup

    for row in _csv_rows(export_csv(snapshot)):
        assert SPEC_VERSION in row["report_methodology"]
        assert SPEC_CHECKSUM in row["report_methodology"]
    scored = [
        row for row in _csv_rows(export_csv(snapshot)) if row["metric_key"].startswith("SEO_")
    ]
    assert scored
    assert all(row["spec_version"] == SPEC_VERSION for row in scored)
    assert all(row["spec_checksum"] == SPEC_CHECKSUM for row in scored)

    xlsx_rows = _xlsx_rows(export_xlsx(snapshot))
    header = xlsx_rows[0]
    methodology_at = header.index("report_methodology")
    for row in xlsx_rows[1:]:
        assert SPEC_VERSION in row[methodology_at]
        assert SPEC_CHECKSUM in row[methodology_at]


def test_every_row_names_the_report_version_and_its_content_hash() -> None:
    snapshot = _snapshot()
    rows = report_rows(snapshot)
    for row in rows:
        assert row["report_title"] == snapshot.report_title_ko
        assert row["report_content_hash"]
        assert row["generated_at"]


def test_a_formula_shaped_cell_is_neutralised() -> None:
    from veo.reports.render.rows import neutralise

    assert neutralise("=1+1") == "'=1+1"
    assert neutralise("+SUM(A1)") == "'+SUM(A1)"
    assert neutralise("-2") == "'-2"
    assert neutralise("@ref") == "'@ref"
    assert neutralise("72.5") == "72.5"


def test_the_csv_is_utf8_with_a_bom_so_excel_reads_korean() -> None:
    body = export_csv(_snapshot())
    assert body.startswith(b"\xef\xbb\xbf")
    assert UNMEASURED_KO in body.decode("utf-8-sig")


def test_the_xlsx_is_a_valid_readable_ooxml_package() -> None:
    body = export_xlsx(_snapshot())
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert {
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
        } <= names
        for name in names:
            ElementTree.fromstring(archive.read(name))  # noqa: S314

    rows = _xlsx_rows(body)
    assert rows[0] == list(COLUMNS)
    assert len(rows) == len(report_rows(_snapshot())) + 1


def test_the_content_types_are_declared_once_per_module() -> None:
    assert CSV_CONTENT_TYPE.startswith("text/csv")
    assert XLSX_CONTENT_TYPE.endswith("spreadsheetml.sheet")


def test_a_gated_export_carries_no_raw_excerpt_but_every_score() -> None:
    snapshot = redact_evidence(_snapshot())
    csv_body = export_csv(snapshot).decode("utf-8-sig")
    xlsx_text = "\n".join("\t".join(row) for row in _xlsx_rows(export_xlsx(snapshot)))

    assert EVIDENCE_SENTINEL not in csv_body
    assert EVIDENCE_SENTINEL not in xlsx_text
    assert str(SEO_OVERALL) in csv_body
    assert str(SEO_OVERALL) in xlsx_text
