"""HTML reading with the standard library only.

``lxml`` and ``beautifulsoup4`` are not installed in this environment and adding a
dependency is not this worker's call, so the parser underneath is
:mod:`html.parser`. That is enough: every GEO check needs headings, visible text split
from page furniture, meta tags, links, tables, dates and the raw JSON-LD blocks — none
of it needs a full DOM or CSS selectors.

Two ideas carry most of the weight:

*Regions.* Text inside ``nav``/``header``/``footer``/``aside`` is furniture. Everything
else is content. The split is what makes "is this page mostly navigation" answerable at
all, and it is deliberately crude — it is reported as a heuristic, never as a fact.

*Own text versus subtree text.* Each block element records the text written directly
inside it as well as everything underneath. A paragraph containing a link keeps the link
text (``a`` is inline), while a wrapper ``div`` has no text of its own and so never
masquerades as a passage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from html.parser import HTMLParser

#: Elements that open a new text frame.
BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "body", "caption", "dd", "div", "dl",
        "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4",
        "h5", "h6", "header", "label", "li", "main", "nav", "ol", "p", "pre", "section",
        "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
    }
)

#: Elements whose own text can be quoted as a standalone passage.
PASSAGE_TAGS = frozenset({"p", "li", "dd", "blockquote", "figcaption", "td", "div", "section"})

FURNITURE_TAGS = frozenset({"nav", "header", "footer", "aside"})

VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
)

SKIPPED_CONTENT_TAGS = frozenset({"script", "style", "template", "noscript"})

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

JSON_LD_TYPE = "application/ld+json"

_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Collapse whitespace so two renderings of the same sentence compare equal."""
    return _WHITESPACE.sub(" ", text).strip()


class Region(StrEnum):
    CONTENT = "CONTENT"
    FURNITURE = "FURNITURE"


@dataclass(frozen=True, slots=True)
class TextBlock:
    tag: str
    own_text: str
    subtree_text: str
    region: Region
    in_table: bool
    in_list: bool

    @property
    def is_passage(self) -> bool:
        return self.tag in PASSAGE_TAGS and bool(self.own_text)


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    text: str
    region: Region


@dataclass(frozen=True, slots=True)
class Link:
    href: str
    text: str
    rel: str
    region: Region


@dataclass(frozen=True, slots=True)
class TimeStamp:
    datetime_attribute: str
    text: str


@dataclass(frozen=True, slots=True)
class PageDocument:
    """Everything the GEO checks read out of one HTML document."""

    title: str = ""
    meta_names: dict[str, str] = field(default_factory=dict)
    meta_properties: dict[str, str] = field(default_factory=dict)
    blocks: tuple[TextBlock, ...] = ()
    headings: tuple[Heading, ...] = ()
    links: tuple[Link, ...] = ()
    timestamps: tuple[TimeStamp, ...] = ()
    json_ld_blocks: tuple[str, ...] = ()
    table_count: int = 0
    list_count: int = 0
    element_ids: tuple[str, ...] = ()
    script_source_count: int = 0
    has_password_field: bool = False
    body_text: str = ""

    # ------------------------------------------------------------------ #
    # Text views
    # ------------------------------------------------------------------ #

    @property
    def content_text(self) -> str:
        return normalise(" ".join(b.own_text for b in self.blocks if b.region is Region.CONTENT))

    @property
    def furniture_text(self) -> str:
        return normalise(" ".join(b.own_text for b in self.blocks if b.region is Region.FURNITURE))

    @property
    def visible_text(self) -> str:
        return normalise(" ".join(b.own_text for b in self.blocks))

    def passages(self, *, region: Region | None = Region.CONTENT) -> tuple[TextBlock, ...]:
        return tuple(
            b for b in self.blocks if b.is_passage and (region is None or b.region is region)
        )

    def content_headings(self) -> tuple[Heading, ...]:
        return tuple(h for h in self.headings if h.region is Region.CONTENT)

    def meta(self, name: str) -> str:
        return self.meta_names.get(name.lower(), "")

    def property_value(self, name: str) -> str:
        return self.meta_properties.get(name.lower(), "")

    def external_links(self, host: str) -> tuple[Link, ...]:
        return tuple(
            link
            for link in self.links
            if link.href.startswith(("http://", "https://")) and host not in link.href
        )

    def has_contact_path(self) -> bool:
        for link in self.links:
            lowered = link.href.lower()
            if lowered.startswith(("tel:", "mailto:")):
                return True
            if "contact" in lowered or "문의" in link.text or "고객센터" in link.text:
                return True
        return False


class _Reader(HTMLParser):
    """Walks the document once, filling a :class:`PageDocument`."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._open: list[str] = []
        self._frame_tags: list[str] = []
        self._frame_regions: list[Region] = []
        self._frame_flags: list[tuple[bool, bool]] = []
        self._own: list[list[str]] = []
        self._all: list[list[str]] = []

        self.blocks: list[TextBlock] = []
        self.headings: list[Heading] = []
        self.links: list[Link] = []
        self.timestamps: list[TimeStamp] = []
        self.json_ld: list[str] = []
        self.meta_names: dict[str, str] = {}
        self.meta_properties: dict[str, str] = {}
        self.element_ids: list[str] = []
        self.title = ""
        self.table_count = 0
        self.list_count = 0
        self.script_source_count = 0
        self.has_password_field = False
        self.body_text: list[str] = []

        self._in_title = False
        self._in_json_ld = False
        self._json_ld_buffer: list[str] = []
        self._skip_depth = 0
        self._anchor: dict[str, str] | None = None
        self._anchor_text: list[str] = []
        self._time: str | None = None
        self._time_text: list[str] = []

    # -- element boundaries ------------------------------------------- #

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {k.lower(): (v or "") for k, v in attrs}
        if tag in VOID_TAGS:
            self._handle_void(tag, attributes)
            return

        if tag in SKIPPED_CONTENT_TAGS:
            if tag == "script":
                if (attributes.get("type") or "").strip().lower() == JSON_LD_TYPE:
                    self._in_json_ld = True
                    self._json_ld_buffer = []
                    return
                if attributes.get("src"):
                    self.script_source_count += 1
            self._skip_depth += 1
            return

        if self._skip_depth:
            return

        if identifier := attributes.get("id"):
            self.element_ids.append(identifier)

        if tag == "title":
            self._in_title = True
        elif tag == "a":
            self._anchor = {"href": attributes.get("href", ""), "rel": attributes.get("rel", "")}
            self._anchor_text = []
        elif tag == "time":
            self._time = attributes.get("datetime", "")
            self._time_text = []
        elif tag == "table":
            self.table_count += 1
        elif tag in {"ul", "ol", "dl"}:
            self.list_count += 1

        self._open.append(tag)
        if tag in BLOCK_TAGS:
            self._push_frame(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_CONTENT_TAGS:
            if tag == "script" and self._in_json_ld:
                self.json_ld.append("".join(self._json_ld_buffer))
                self._in_json_ld = False
                return
            self._skip_depth = max(0, self._skip_depth - 1)
            return

        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = False
            return
        if tag == "a" and self._anchor is not None:
            self.links.append(
                Link(
                    href=self._anchor["href"],
                    text=normalise("".join(self._anchor_text)),
                    rel=self._anchor["rel"].lower(),
                    region=self._current_region(),
                )
            )
            self._anchor = None
            return
        if tag == "time" and self._time is not None:
            self.timestamps.append(
                TimeStamp(
                    datetime_attribute=self._time, text=normalise("".join(self._time_text))
                )
            )
            self._time = None
            return

        if tag not in self._open:
            return
        while self._open:
            open_tag = self._open.pop()
            if open_tag in BLOCK_TAGS:
                self._pop_frame()
            if open_tag == tag:
                break

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_ld_buffer.append(data)
            return
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
            return
        if self._anchor is not None:
            self._anchor_text.append(data)
        if self._time is not None:
            self._time_text.append(data)
        self.body_text.append(data)
        if self._own:
            self._own[-1].append(data)

    # -- frames -------------------------------------------------------- #

    def _push_frame(self, tag: str) -> None:
        self._frame_tags.append(tag)
        self._frame_regions.append(
            Region.FURNITURE
            if tag in FURNITURE_TAGS or any(t in FURNITURE_TAGS for t in self._open)
            else Region.CONTENT
        )
        self._frame_flags.append(
            ("table" in self._open, any(t in {"ul", "ol", "dl"} for t in self._open))
        )
        self._own.append([])
        self._all.append([])

    def _pop_frame(self) -> None:
        if not self._frame_tags:
            return
        tag = self._frame_tags.pop()
        region = self._frame_regions.pop()
        in_table, in_list = self._frame_flags.pop()
        own = normalise("".join(self._own.pop()))
        subtree_parts = self._all.pop()
        subtree = normalise(" ".join([own, *subtree_parts]))

        block = TextBlock(
            tag=tag,
            own_text=own,
            subtree_text=subtree,
            region=region,
            in_table=in_table,
            in_list=in_list,
        )
        self.blocks.append(block)
        if tag in HEADING_TAGS:
            self.headings.append(
                Heading(level=int(tag[1]), text=subtree or own, region=region)
            )
        if self._all:
            self._all[-1].append(subtree)

    def _current_region(self) -> Region:
        if any(t in FURNITURE_TAGS for t in self._open):
            return Region.FURNITURE
        return self._frame_regions[-1] if self._frame_regions else Region.CONTENT

    def _handle_void(self, tag: str, attributes: dict[str, str]) -> None:
        if self._skip_depth:
            return
        if tag == "meta":
            content = attributes.get("content", "")
            if name := attributes.get("name"):
                self.meta_names[name.lower()] = content
            if prop := attributes.get("property"):
                self.meta_properties[prop.lower()] = content
            if equiv := attributes.get("http-equiv"):
                self.meta_names[equiv.lower()] = content
        elif tag == "input" and attributes.get("type", "").lower() == "password":
            self.has_password_field = True
        elif tag == "link" and (rel := attributes.get("rel", "").lower()):
            self.meta_names.setdefault(f"link:{rel}", attributes.get("href", ""))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS and tag not in SKIPPED_CONTENT_TAGS:
            self.handle_endtag(tag)

    def finish(self) -> PageDocument:
        while self._frame_tags:
            self._pop_frame()
        return PageDocument(
            title=normalise(self.title),
            meta_names=dict(self.meta_names),
            meta_properties=dict(self.meta_properties),
            blocks=tuple(self.blocks),
            headings=tuple(self.headings),
            links=tuple(self.links),
            timestamps=tuple(self.timestamps),
            json_ld_blocks=tuple(self.json_ld),
            table_count=self.table_count,
            list_count=self.list_count,
            element_ids=tuple(self.element_ids),
            script_source_count=self.script_source_count,
            has_password_field=self.has_password_field,
            body_text=normalise("".join(self.body_text)),
        )


def parse_html(markup: str) -> PageDocument:
    """Read one HTML document. Malformed markup degrades; it never raises."""
    reader = _Reader()
    try:
        reader.feed(markup)
        reader.close()
    except AssertionError:  # pragma: no cover - html.parser guards against a few shapes
        pass
    return reader.finish()


__all__ = [
    "BLOCK_TAGS",
    "FURNITURE_TAGS",
    "JSON_LD_TYPE",
    "PASSAGE_TAGS",
    "Heading",
    "Link",
    "PageDocument",
    "Region",
    "TextBlock",
    "TimeStamp",
    "normalise",
    "parse_html",
]
