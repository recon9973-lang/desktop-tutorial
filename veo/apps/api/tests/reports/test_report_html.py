"""The HTML report: self-contained, accessible, printable, and disclosed.

A delivered report is opened months later, often offline, often printed. Anything it
fetches from the network is a number that can silently disappear or, worse, change.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from report_support import (
    EVIDENCE_SENTINEL,
    NOT_APPLICABLE_REASON,
    SPEC_CHECKSUM,
    SPEC_VERSION,
    UNKNOWN_REASON,
    make_diagnosis,
)

from veo.reports.render.html import HTML_CONTENT_TYPE, render_html
from veo.reports.snapshot import NOT_APPLICABLE_KO, UNMEASURED_KO, freeze, redact_evidence

#: Attributes a browser will dereference. Any of these carrying a scheme is a fetch.
FETCHING_ATTRIBUTES = frozenset(
    {
        "src",
        "srcset",
        "href",
        "data",
        "poster",
        "action",
        "formaction",
        "background",
        "cite",
        "manifest",
        "xlink:href",
        "ping",
        "codebase",
    }
)

EXTERNAL_TAGS = frozenset({"iframe", "object", "embed", "frame", "applet", "base"})


class _Auditor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.external_references: list[tuple[str, str, str]] = []
        self.forbidden_tags: list[str] = []
        self.headings: list[int] = []
        self.tables_without_caption = 0
        self._open_table_has_caption: list[bool] = []
        self.langs: list[str] = []
        self.images_without_alt = 0
        self.th_without_scope = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = {name: (value or "") for name, value in attrs}

        if tag in EXTERNAL_TAGS:
            self.forbidden_tags.append(tag)
        if tag == "html" and "lang" in mapping:
            self.langs.append(mapping["lang"])
        if tag == "img" and "alt" not in mapping:
            self.images_without_alt += 1
        if tag == "th" and "scope" not in mapping:
            self.th_without_scope += 1
        if tag == "table":
            self._open_table_has_caption.append(False)
        if tag == "caption" and self._open_table_has_caption:
            self._open_table_has_caption[-1] = True
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))

        for name, value in mapping.items():
            if name not in FETCHING_ATTRIBUTES:
                continue
            if re.match(r"\s*[a-zA-Z][a-zA-Z0-9+.-]*:", value) and not value.startswith("#"):
                self.external_references.append((tag, name, value))
            if value.startswith("//"):
                self.external_references.append((tag, name, value))

    def handle_endtag(self, tag: str) -> None:
        if (
            tag == "table"
            and self._open_table_has_caption
            and not self._open_table_has_caption.pop()
        ):
            self.tables_without_caption += 1


def _audit(markup: str) -> _Auditor:
    auditor = _Auditor()
    auditor.feed(markup)
    auditor.close()
    return auditor


def _markup() -> str:
    return render_html(freeze(make_diagnosis()))


def test_the_html_references_no_external_url_at_all() -> None:
    auditor = _audit(_markup())
    assert auditor.external_references == []
    assert auditor.forbidden_tags == []


def test_the_html_pulls_in_no_stylesheet_font_or_script_from_anywhere() -> None:
    markup = _markup()
    assert "<script" not in markup.lower()
    assert "@import" not in markup
    assert not re.search(r"url\(\s*[\"']?(?:https?:)?//", markup)
    assert "<style" in markup.lower(), "styling must be inline, not absent"


def test_affected_urls_appear_as_text_and_not_as_links() -> None:
    markup = _markup()
    assert "https://example.test/robots.txt" in markup
    assert 'href="https://example.test' not in markup


def test_the_html_is_accessible_enough_to_be_read_and_printed() -> None:
    markup = _markup()
    auditor = _audit(markup)

    assert auditor.langs == ["ko"]
    assert auditor.headings and auditor.headings[0] == 1
    assert max(auditor.headings) - min(auditor.headings) <= 3
    assert auditor.tables_without_caption == 0
    assert auditor.th_without_scope == 0
    assert auditor.images_without_alt == 0
    assert "@media print" in markup


def test_the_html_carries_the_full_disclosure_block() -> None:
    markup = _markup()
    assert SPEC_VERSION in markup
    assert SPEC_CHECKSUM in markup
    assert "측정 범위" in markup
    assert "측정 시점" in markup
    assert "신뢰도" in markup
    assert "순위 예측" in markup


def test_the_html_shows_all_three_audiences_from_one_snapshot() -> None:
    markup = _markup()
    assert "경영진" in markup
    assert "마케팅" in markup
    assert "개발자" in markup


def test_unmeasured_and_not_applicable_render_as_themselves_with_a_reason() -> None:
    markup = _markup()
    assert UNMEASURED_KO in markup
    assert NOT_APPLICABLE_KO in markup
    assert UNKNOWN_REASON in markup
    assert NOT_APPLICABLE_REASON in markup


def test_a_gated_reader_gets_the_html_without_any_raw_excerpt() -> None:
    markup = render_html(redact_evidence(freeze(make_diagnosis())))
    assert EVIDENCE_SENTINEL not in markup
    assert SPEC_VERSION in markup
    assert "72.5" in markup


def test_the_content_type_is_declared_once_in_the_module() -> None:
    assert HTML_CONTENT_TYPE.startswith("text/html")
