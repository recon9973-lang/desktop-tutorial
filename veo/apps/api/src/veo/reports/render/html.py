"""A self-contained HTML report.

Constraints, and why each one is not negotiable:

**Nothing is fetched.** No stylesheet, no font, no image, no script, no iframe — and no
``<a href>`` to a measured URL either. A delivered report is opened months later, often
offline and often printed; anything the page fetches is a part of the document that can
quietly disappear or, worse, change after delivery. Measured URLs are printed as text.

**It prints.** The stylesheet is inline and carries a ``@media print`` block, because the
most common way this document reaches a decision-maker is on paper.

**It is readable by a screen reader.** ``lang="ko"``, one ``h1``, ordered headings, every
table with a ``<caption>`` and every header cell with a ``scope``.

**Every number is disclosed.** The methodology version and checksum, the measurement
scope and time, the coverage and confidence, and the standing notice that a readiness
score is not a rank prediction, all appear on the page — not in a tooltip, not in a
footnote nobody exports.

Nothing here computes. Every figure printed is ``MeasuredValue.display()`` from the
snapshot, which is the same string the CSV and the XLSX carry.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from html import escape
from typing import Final

from veo.reports.snapshot import (
    MeasuredValue,
    MetricRow,
    ReportSnapshot,
    ValueStatus,
)
from veo.reports.views import ReportViews, build_views

__all__ = ["HTML_CONTENT_TYPE", "render_html"]

HTML_CONTENT_TYPE: Final = "text/html; charset=utf-8"

_STYLE: Final = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0 auto; padding: 2rem 1.5rem; max-width: 60rem;
  font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  font-size: 15px; line-height: 1.7; color: #16181d; background: #ffffff;
}
h1 { font-size: 1.75rem; margin: 0 0 .25rem; }
h2 { font-size: 1.3rem; margin: 2.5rem 0 .75rem; padding-bottom: .35rem;
     border-bottom: 2px solid #16181d; }
h3 { font-size: 1.05rem; margin: 1.5rem 0 .5rem; }
h4 { font-size: .95rem; margin: 1rem 0 .35rem; }
p, li { margin: .35rem 0; }
a { color: #14407a; }
.skip { position: absolute; left: -9999px; }
.skip:focus { position: static; }
.subtitle { color: #4b5162; margin: 0 0 1rem; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0 1.25rem;
        font-size: .9rem; }
caption { text-align: left; font-weight: 700; padding: .35rem 0; }
th, td { border: 1px solid #c8ccd6; padding: .4rem .55rem; vertical-align: top;
         text-align: left; }
thead th { background: #eef1f6; }
td.number { text-align: right; white-space: nowrap; }
.state-unmeasured { color: #7a3d00; font-weight: 700; }
.state-not-applicable { color: #4b5162; font-weight: 700; }
.reason { color: #4b5162; }
dl.disclosure { margin: 0; }
dl.disclosure dt { font-weight: 700; margin-top: .6rem; }
dl.disclosure dd { margin: 0 0 .2rem; }
.notice { border: 2px solid #7a3d00; padding: .75rem 1rem; margin: 1rem 0;
          background: #fff8ef; }
pre { background: #f4f5f8; border: 1px solid #c8ccd6; padding: .6rem .75rem;
      overflow-x: auto; white-space: pre-wrap; word-break: break-all; font-size: .85rem; }
.urls { list-style: none; padding-left: 0; word-break: break-all; }
footer { margin-top: 2.5rem; border-top: 1px solid #c8ccd6; padding-top: .75rem;
         color: #4b5162; font-size: .85rem; }
@media print {
  body { max-width: none; padding: 0; font-size: 11pt; }
  h2 { break-before: page; }
  h2:first-of-type { break-before: auto; }
  table, pre, .notice { break-inside: avoid; }
  .skip, nav.toc { display: none; }
}
"""

_STATE_CLASS: Final[dict[ValueStatus, str]] = {
    ValueStatus.MEASURED: "",
    ValueStatus.UNMEASURED: "state-unmeasured",
    ValueStatus.NOT_APPLICABLE: "state-not-applicable",
}


def _e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _value_cell(value: MeasuredValue) -> str:
    """A value cell that can never be mistaken for zero."""
    if value.status is ValueStatus.MEASURED:
        return f'<td class="number">{_e(value.display_with_unit())}</td>'
    return (
        f'<td class="number {_STATE_CLASS[value.status]}">{_e(value.display())}</td>'
    )


def _reason_cell(value: MeasuredValue) -> str:
    return f'<td class="reason">{_e(value.reason_ko or "")}</td>'


def _table(
    caption: str, headers: Sequence[str], rows: Iterable[str], *, table_id: str | None = None
) -> str:
    attribute = f' id="{_e(table_id)}"' if table_id else ""
    head = "".join(f'<th scope="col">{_e(header)}</th>' for header in headers)
    body = "".join(rows)
    return (
        f"<table{attribute}><caption>{_e(caption)}</caption>"
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def _metric_rows(snapshot: ReportSnapshot, rows: Sequence[MetricRow]) -> list[str]:
    out: list[str] = []
    for row in rows:
        provenance = snapshot.provenance.get(row.provenance_ref)
        methodology = provenance.methodology_line_ko() if provenance else ""
        out.append(
            f'<tr><th scope="row">{_e(row.label_ko)}</th>'
            f"{_value_cell(row.value)}"
            f"<td>{_e(row.value.status_ko)}</td>"
            f"{_reason_cell(row.value)}"
            f"<td>{_e(row.value.source)}</td>"
            f"<td>{_e(methodology)}</td></tr>"
        )
    return out


_METRIC_HEADERS: Final = ("지표", "값", "상태", "사유", "출처", "측정 방법론")


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #


def _executive_section(snapshot: ReportSnapshot, views: ReportViews) -> str:
    view = views.executive
    parts = [
        '<section id="executive" aria-labelledby="executive-heading">',
        '<h2 id="executive-heading">경영진 요약</h2>',
        f"<p>{_e(view.status_ko)}</p>",
        "<h3>핵심 수치</h3>",
        _table("핵심 수치", _METRIC_HEADERS, _metric_rows(snapshot, view.headline)),
    ]

    parts.append("<h3>경쟁사 대비 격차</h3>")
    if view.competitive_gap:
        parts.append(
            _table(
                "경쟁사 대비 격차",
                _METRIC_HEADERS,
                _metric_rows(snapshot, view.competitive_gap),
            )
        )
    else:
        parts.append("<p>이 리포트에는 비교한 경쟁사가 없습니다.</p>")

    parts.append("<h3>우선 조치</h3>")
    if view.top_actions:
        rows = [
            f'<tr><th scope="row">{action.rank}</th>'
            f"<td>{_e(action.title_ko)}</td>"
            f"<td>{_e(action.why_ko)}</td>"
            f"<td>{_e(action.owner_ko)}</td>"
            f"<td>{_e(action.severity)}</td></tr>"
            for action in view.top_actions
        ]
        parts.append(
            _table("우선 조치 목록", ("순위", "조치", "왜 중요한가", "담당", "심각도"), rows)
        )
    else:
        parts.append("<p>조치가 필요한 항목이 없습니다.</p>")

    parts.append("<h3>지난 발행 대비 변화</h3>")
    parts.append(
        "<ul>" + "".join(f"<li>{_e(line)}</li>" for line in view.changes_ko) + "</ul>"
    )
    parts.append("</section>")
    return "".join(parts)


def _marketing_section(snapshot: ReportSnapshot, views: ReportViews) -> str:
    view = views.marketing
    parts = [
        '<section id="marketing" aria-labelledby="marketing-heading">',
        '<h2 id="marketing-heading">마케팅 상세</h2>',
        f"<p>{_e(view.summary_ko)}</p>",
    ]

    for table in view.category_tables:
        rows = []
        for row in table.rows:
            change = (
                _e(row.change.display_with_unit()) if row.change is not None else "—"
            )
            rows.append(
                f'<tr><th scope="row">{_e(row.name_ko)}</th>'
                f"<td>{_e(row.weight)}</td>"
                f"{_value_cell(row.value)}"
                f"<td>{_e(row.value.status_ko)}</td>"
                f'<td class="number">{_e(row.coverage.display_with_unit())}</td>'
                f'<td class="number">{_e(row.confidence.display_with_unit())}</td>'
                f"<td>{change}</td>"
                f"{_reason_cell(row.value)}</tr>"
            )
        parts.append(f"<h3>{_e(table.name_ko)} 카테고리별</h3>")
        parts.append(
            f"<p>종합 {_e(table.overall.display_with_unit())}</p>"
            if table.overall.status is ValueStatus.MEASURED
            else f"<p>종합 {_e(table.overall.display_with_reason())}</p>"
        )
        parts.append(
            _table(
                f"{table.name_ko} 카테고리별 점수",
                ("카테고리", "가중치", "점수", "상태", "측정 범위", "신뢰도", "변화", "사유"),
                rows,
            )
        )

    parts.append("<h3>키워드 수요와 기회</h3>")
    if view.keyword_rows:
        rows = [
            f'<tr><th scope="row">{_e(row.keyword)}</th>'
            f"{_value_cell(row.monthly_searches)}"
            f"<td>{_e(row.monthly_searches.status_ko)}</td>"
            f"{_value_cell(row.opportunity)}"
            f"<td>{_e(row.opportunity.status_ko)}</td>"
            f'<td class="reason">'
            f"{_e(row.monthly_searches.reason_ko or row.opportunity.reason_ko or row.note_ko)}"
            f"</td></tr>"
            for row in view.keyword_rows
        ]
        parts.append(
            _table(
                "키워드 수요와 기회 점수",
                ("키워드", "월간 검색량", "상태", "기회 점수", "상태", "비고"),
                rows,
            )
        )
    else:
        parts.append("<p>이 리포트에는 키워드 수요 자료가 없습니다.</p>")

    parts.append("<h3>경쟁사 비교</h3>")
    if view.competitor_rows:
        rows = [
            f'<tr><th scope="row">{_e(row.label_ko)}</th>'
            f"<td>{_e(row.domain)}</td>"
            f"{_value_cell(row.ours)}"
            f"{_value_cell(row.theirs)}"
            f"{_value_cell(row.gap)}"
            f"<td>{_e('비교 가능' if row.is_comparable else '비교 불가')}</td>"
            f'<td class="reason">{_e(row.conditions_note_ko)}</td></tr>'
            for row in view.competitor_rows
        ]
        parts.append(
            _table(
                "경쟁사 비교와 측정 조건",
                ("경쟁사", "영역", "우리", "경쟁사", "격차", "비교 가능 여부", "측정 조건"),
                rows,
            )
        )
    else:
        parts.append("<p>이 리포트에는 비교한 경쟁사가 없습니다.</p>")

    parts.append("</section>")
    return "".join(parts)


def _developer_section(snapshot: ReportSnapshot, views: ReportViews) -> str:
    view = views.developer
    parts = [
        '<section id="developer" aria-labelledby="developer-heading">',
        '<h2 id="developer-heading">개발자 작업 목록</h2>',
        f"<p>{_e(view.summary_ko)}</p>",
    ]

    if not view.work_items:
        parts.append("<p>조치가 필요한 항목이 없습니다.</p>")
    for item in view.work_items:
        parts.append(f"<h3>{_e(item.title_ko)}</h3>")
        parts.append(
            f"<p>{_e(item.summary_ko)} (검사 {_e(item.check_id)}, 심각도 "
            f"{_e(item.severity)}, 담당 {_e(item.owner_ko)})</p>"
        )
        parts.append("<h4>영향 URL</h4>")
        parts.append(
            '<ul class="urls">'
            + "".join(f"<li>{_e(url)}</li>" for url in item.affected_urls)
            + "</ul>"
        )
        parts.append("<h4>근거 참조</h4>")
        parts.append(
            "<p>"
            + (_e(", ".join(item.evidence_ids)) or "참조된 근거가 없습니다.")
            + "</p>"
        )
        parts.append("<h4>수정 방법</h4>")
        parts.append(f"<p>{_e(item.remediation_ko)}</p>")
        if item.fix_example:
            parts.append(f"<pre>{_e(item.fix_example)}</pre>")
        parts.append("<h4>재검증</h4>")
        parts.append(f"<p>{_e(item.reverification_ko)}</p>")

    parts.append("<h3>측정하지 못한 검사</h3>")
    if view.unmeasured_checks:
        rows = [
            f'<tr><th scope="row">{_e(check.check_id)}</th>'
            f"<td>{_e(check.title_ko)}</td>"
            f"<td>{_e(check.domain)}</td>"
            f'<td class="state-unmeasured">{_e(check.status_ko)}</td>'
            f'<td class="reason">{_e(check.reason_ko or "")}</td></tr>'
            for check in view.unmeasured_checks
        ]
        parts.append(
            _table("측정하지 못한 검사와 사유", ("검사", "항목", "영역", "상태", "사유"), rows)
        )
    else:
        parts.append("<p>모든 검사를 측정했습니다.</p>")

    parts.append("<h3>근거 목록</h3>")
    if view.evidence:
        rows = [
            f'<tr><th scope="row">{_e(record.evidence_id)}</th>'
            f"<td>{_e(record.kind)}</td>"
            f"<td>{_e(record.url or '')}</td>"
            f"<td>{_e(record.content_hash)}</td>"
            f"<td>{_e(record.collected_at.isoformat())}</td>"
            "<td>"
            + (
                "권한이 없어 원문 발췌를 표시하지 않았습니다."
                if record.excerpt_redacted
                else f"<pre>{_e(record.excerpt or '')}</pre>"
            )
            + "</td></tr>"
            for record in view.evidence
        ]
        parts.append(
            _table(
                "근거 참조와 원문 해시",
                ("근거 ID", "종류", "URL", "내용 해시", "수집 시각", "발췌"),
                rows,
            )
        )
    else:
        parts.append("<p>이 리포트에는 저장된 근거가 없습니다.</p>")

    parts.append("<h3>재검증 절차</h3>")
    parts.append(
        "<ol>" + "".join(f"<li>{_e(line)}</li>" for line in view.reverification_ko) + "</ol>"
    )
    parts.append("</section>")
    return "".join(parts)


def _disclosure_section(views: ReportViews) -> str:
    block = views.executive.disclosure
    items = (
        ("측정 범위", block.scope_ko),
        ("측정 시점", block.measured_at_ko),
        ("측정 방법론 (버전·체크섬)", block.methodology_ko),
        ("측정 범위 값", block.coverage_ko),
        ("신뢰도", block.confidence_ko),
    )
    definitions = "".join(
        f"<dt>{_e(term)}</dt><dd>{_e(value)}</dd>" for term, value in items
    )
    lines = "".join(f"<li>{_e(line)}</li>" for line in block.lines_ko)
    return (
        '<section id="disclosure" aria-labelledby="disclosure-heading">'
        '<h2 id="disclosure-heading">측정 공시</h2>'
        f'<div class="notice"><p>{_e(block.rank_prediction_notice_ko)}</p></div>'
        f'<dl class="disclosure">{definitions}</dl>'
        f"<h3>고지 사항</h3><ul>{lines}</ul>"
        "</section>"
    )


def _appendix_section(snapshot: ReportSnapshot) -> str:
    parts = [
        '<section id="metrics" aria-labelledby="metrics-heading">',
        '<h2 id="metrics-heading">부록 — 전체 지표</h2>',
        "<p>이 리포트가 담고 있는 모든 수치입니다. CSV·XLSX 내보내기는 같은 값을 같은 "
        "표기로 담습니다.</p>",
        _table(
            "전체 지표 목록",
            ("지표", "값", "상태", "사유", "출처", "측정 방법론"),
            _metric_rows(snapshot, snapshot.metrics),
        ),
    ]
    if snapshot.changes:
        rows = [
            f'<tr><th scope="row">{_e(change.label_ko)}</th>'
            f"{_value_cell(change.previous)}"
            f"{_value_cell(change.current)}"
            f"{_value_cell(change.delta)}"
            f"<td>{_e(change.direction)}</td>"
            f"{_reason_cell(change.delta)}</tr>"
            for change in snapshot.changes
        ]
        parts.append("<h3>이전 버전 대비 변화</h3>")
        parts.append(
            _table("이전 버전 대비 변화", ("지표", "이전", "현재", "변화량", "방향", "사유"), rows)
        )
    parts.append("</section>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Document
# --------------------------------------------------------------------------- #


def render_html(
    snapshot: ReportSnapshot,
    *,
    views: ReportViews | None = None,
    version_number: int | None = None,
    content_hash: str | None = None,
) -> str:
    """One printable, offline-readable document holding all three readings."""
    from veo.reports.snapshot import compute_content_hash

    resolved = views or build_views(snapshot)
    digest = content_hash or compute_content_hash(snapshot)
    version_line = (
        f"버전 {version_number}" if version_number is not None else "버전 미지정"
    )

    window = ""
    if snapshot.measurement_window_start and snapshot.measurement_window_end:
        window = (
            f" · 측정 기간 {snapshot.measurement_window_start.isoformat()}"
            f" ~ {snapshot.measurement_window_end.isoformat()}"
        )

    body = "".join(
        [
            '<a class="skip" href="#executive">본문으로 건너뛰기</a>',
            "<header>",
            f"<h1>{_e(snapshot.report_title_ko)}</h1>",
            f'<p class="subtitle">{_e(version_line)} · 발행 '
            f"{_e(snapshot.generated_at.isoformat())}{_e(window)}</p>",
            f'<p class="subtitle">내용 해시 {_e(digest)}</p>',
            f'<p class="subtitle">{_e(resolved.executive.disclosure.methodology_ko)}</p>',
            "</header>",
            '<nav class="toc" aria-label="문서 목차"><ul>'
            '<li><a href="#executive">경영진 요약</a></li>'
            '<li><a href="#marketing">마케팅 상세</a></li>'
            '<li><a href="#developer">개발자 작업 목록</a></li>'
            '<li><a href="#disclosure">측정 공시</a></li>'
            '<li><a href="#metrics">부록 — 전체 지표</a></li>'
            "</ul></nav>",
            _executive_section(snapshot, resolved),
            _marketing_section(snapshot, resolved),
            _developer_section(snapshot, resolved),
            _disclosure_section(resolved),
            _appendix_section(snapshot),
            "<footer><p>"
            + _e(resolved.executive.disclosure.rank_prediction_notice_ko)
            + "</p><p>VEO · VENOM. 측정 방법론 연구 VEO-LAB.</p></footer>",
        ]
    )

    return (
        "<!DOCTYPE html>"
        '<html lang="ko">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex, nofollow">'
        f"<title>{_e(snapshot.report_title_ko)}</title>"
        f"<style>{_STYLE}</style>"
        "</head>"
        f"<body>{body}</body>"
        "</html>"
    )
