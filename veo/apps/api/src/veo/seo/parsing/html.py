"""Reading an HTML document with nothing but the standard library.

``lxml`` and ``beautifulsoup4`` are not installed in this environment and VEO does not
add a dependency in order to read a ``<title>``. ``html.parser`` is lenient in exactly
the way a crawler needs: an unclosed tag, a stray ``<`` or a mis-declared charset is a
finding about the page, not a reason to stop parsing.

Two distinctions this module keeps deliberately sharp.

*Missing and empty are different.* ``<img alt="">`` marks a decorative image and is
correct; ``<img>`` with no ``alt`` at all is an omission. So ``alt`` is ``None`` in one
case and ``""`` in the other, and no code path may collapse them.

*Body text is not page text.* The navigation and the footer repeat on every page, so
counting them would make every page look substantial and every pair of pages look
duplicated. :attr:`ParsedPage.body_text` is the main content only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

#: Elements whose text is markup or styling, never content.
_INVISIBLE = frozenset({"script", "style", "template", "noscript", "svg", "head"})

#: Repeated furniture. Excluded from the body text so that boilerplate cannot pass for
#: substance and cannot make two different pages look like copies of each other.
_BOILERPLATE = frozenset({"nav", "header", "footer", "aside"})

_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

#: ``rel`` values that ask the browser to start work early on a named resource.
_RESOURCE_HINTS = frozenset(
    {"preload", "preconnect", "dns-prefetch", "prefetch", "modulepreload"}
)

#: HTML void elements — they never receive an end tag, so the stack must not wait for one.
_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

_SUBRESOURCE_ATTRS = {
    "img": "src",
    "script": "src",
    "iframe": "src",
    "audio": "src",
    "video": "src",
    "source": "src",
    "embed": "src",
    "object": "data",
}


@dataclass(frozen=True, slots=True)
class Anchor:
    href: str
    text: str
    rel: str | None = None
    aria_label: str | None = None
    title: str | None = None
    in_boilerplate: bool = False

    @property
    def accessible_text(self) -> str:
        """What a reader or a crawler would take the link to be about."""
        for candidate in (self.text, self.aria_label, self.title):
            if candidate and candidate.strip():
                return candidate.strip()
        return ""


@dataclass(frozen=True, slots=True)
class Image:
    src: str
    alt: str | None
    """``None`` when the attribute is absent; ``""`` when it is present and empty."""

    loading: str | None = None
    """``loading="lazy"`` and friends, lower-cased. ``None`` when absent."""

    order: int = 0
    """Document order among images. Used as the only honest stand-in for "above the
    fold" — we do not lay the page out, so we cannot know what is actually visible."""


@dataclass
class ParsedPage:
    """Everything the collectors read out of one HTML document."""

    title: str | None = None
    title_count: int = 0
    """How many ``<title>`` elements the document declared. Two is a real and common
    fault — a theme and a plugin each adding one — and the search engine then has no
    way to know which was meant."""

    doctype: str | None = None
    """The raw doctype declaration, lower-cased, or ``None`` when the document had none."""

    icon_hrefs: tuple[str, ...] = ()
    """``rel`` values containing ``icon``: favicon, apple-touch-icon, mask-icon."""

    resource_hints: tuple[tuple[str, str], ...] = ()
    """``(rel, href)`` for preload / preconnect / dns-prefetch / prefetch / modulepreload."""

    lazy_iframes: int = 0
    """``<iframe loading="lazy">`` count. Iframes carry content, not decoration."""

    lang: str | None = None
    meta_description: str | None = None
    meta_robots: str | None = None
    viewport: str | None = None
    canonical: str | None = None
    canonical_count: int = 0
    rel_next: str | None = None
    rel_prev: str | None = None
    hreflang: tuple[tuple[str, str], ...] = ()
    open_graph: dict[str, str] = field(default_factory=dict)
    headings: tuple[tuple[int, str], ...] = ()
    links: tuple[Anchor, ...] = ()
    images: tuple[Image, ...] = ()
    json_ld_blocks: tuple[str, ...] = ()
    subresources: tuple[str, ...] = ()
    has_breadcrumb: bool = False
    body_text: str = ""
    full_text: str = ""
    has_main: bool = False


class _PageParser(HTMLParser):
    """A single pass that fills a :class:`ParsedPage`.

    ``convert_charrefs`` is left on so ``&amp;`` in an anchor or a title arrives decoded,
    which is what every downstream comparison expects.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = ParsedPage()

        self._stack: list[str] = []
        self._invisible_depth = 0
        self._boilerplate_depth = 0
        self._main_depth = 0

        self._title_parts: list[str] = []
        self._saw_title = False
        self._in_title = False

        self._heading_level: int | None = None
        self._heading_parts: list[str] = []
        self._headings: list[tuple[int, str]] = []

        self._anchor: dict[str, str] | None = None
        self._anchor_parts: list[str] = []
        self._links: list[Anchor] = []

        self._images: list[Image] = []
        self._subresources: list[str] = []
        self._icons: list[str] = []
        self._hints: list[tuple[str, str]] = []

        self._json_ld_parts: list[str] = []
        self._in_json_ld = False
        self._json_ld: list[str] = []

        self._hreflang: list[tuple[str, str]] = []
        self._body_parts: list[str] = []
        self._main_parts: list[str] = []
        self._full_parts: list[str] = []
        self._breadcrumb = False

    # -- element boundaries ------------------------------------------------ #

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}
        self._open(tag, attributes)
        if tag in _VOID:
            self._close(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}
        self._open(tag, attributes)
        self._close(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID:
            return
        self._close(tag)

    def handle_decl(self, decl: str) -> None:
        """``<!DOCTYPE html>``. Only the first one counts; a later one is not a doctype."""
        if self.page.doctype is None and decl.strip().lower().startswith("doctype"):
            self.page.doctype = decl.strip().lower()

    def _open(self, tag: str, attributes: dict[str, str]) -> None:
        if tag not in _VOID:
            self._stack.append(tag)

        if tag in _INVISIBLE:
            self._invisible_depth += 1
        if tag in _BOILERPLATE:
            self._boilerplate_depth += 1
        if tag == "main":
            self._main_depth += 1
            self.page.has_main = True

        if tag == "html":
            self._read_html(attributes)
        elif tag == "title":
            self._in_title = True
            self._saw_title = True
            self.page.title_count += 1
        elif tag == "meta":
            self._read_meta(attributes)
        elif tag == "link":
            self._read_link(attributes)
        elif tag == "script":
            self._read_script(attributes)
        elif tag == "a":
            self._read_anchor(attributes)
        elif tag == "img":
            loading = attributes.get("loading", "").strip().lower()
            self._images.append(
                Image(
                    src=attributes.get("src", "").strip(),
                    alt=attributes.get("alt"),
                    loading=loading or None,
                    order=len(self._images),
                )
            )
        elif tag == "iframe" and attributes.get("loading", "").strip().lower() == "lazy":
            self.page.lazy_iframes += 1
        elif tag in _HEADINGS:
            self._heading_level = _HEADINGS[tag]
            self._heading_parts = []

        if _looks_like_breadcrumb(tag, attributes):
            self._breadcrumb = True

        source_attr = _SUBRESOURCE_ATTRS.get(tag)
        if source_attr and attributes.get(source_attr):
            self._subresources.append(attributes[source_attr])

    def _close(self, tag: str) -> None:
        if tag in _INVISIBLE and self._invisible_depth:
            self._invisible_depth -= 1
        if tag in _BOILERPLATE and self._boilerplate_depth:
            self._boilerplate_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1

        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._json_ld.append("".join(self._json_ld_parts))
            self._json_ld_parts = []
            self._in_json_ld = False
        elif tag in _HEADINGS and self._heading_level is not None:
            self._headings.append((self._heading_level, _collapse("".join(self._heading_parts))))
            self._heading_level = None
            self._heading_parts = []
        elif tag == "a" and self._anchor is not None:
            self._links.append(
                Anchor(
                    href=self._anchor["href"],
                    text=_collapse("".join(self._anchor_parts)),
                    rel=self._anchor["rel"] or None,
                    aria_label=self._anchor["aria_label"] or None,
                    title=self._anchor["title"] or None,
                    in_boilerplate=bool(self._anchor["boilerplate"]),
                )
            )
            self._anchor = None
            self._anchor_parts = []

        if tag not in _VOID:
            self._unwind(tag)

    def _unwind(self, tag: str) -> None:
        """Pop to the most recent matching tag, tolerating a page that never closed one."""
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index] == tag:
                del self._stack[index:]
                return

    # -- per-element readers ----------------------------------------------- #

    def _read_html(self, attributes: dict[str, str]) -> None:
        if attributes.get("lang", "").strip():
            self.page.lang = attributes["lang"].strip()

    def _read_meta(self, attributes: dict[str, str]) -> None:
        content = attributes.get("content", "").strip()
        name = attributes.get("name", "").strip().lower()
        prop = attributes.get("property", "").strip().lower()

        if name == "description" and self.page.meta_description is None:
            self.page.meta_description = content
        elif name == "robots":
            self.page.meta_robots = content.lower()
        elif name == "viewport" and self.page.viewport is None:
            self.page.viewport = content
        if prop.startswith("og:") and content:
            self.page.open_graph.setdefault(prop, content)

    def _read_link(self, attributes: dict[str, str]) -> None:
        relations = set(attributes.get("rel", "").strip().lower().split())
        href = attributes.get("href", "").strip()
        if not relations or not href:
            return
        if "canonical" in relations:
            self.page.canonical_count += 1
            if self.page.canonical is None:
                self.page.canonical = href
        if "next" in relations and self.page.rel_next is None:
            self.page.rel_next = href
        if "prev" in relations and self.page.rel_prev is None:
            self.page.rel_prev = href
        if "alternate" in relations and attributes.get("hreflang", "").strip():
            self._hreflang.append((attributes["hreflang"].strip().lower(), href))
        if "stylesheet" in relations:
            self._subresources.append(href)
        # 파비콘의 rel 은 하나가 아니다: icon, shortcut icon, apple-touch-icon, mask-icon.
        if any("icon" in relation for relation in relations):
            self._icons.append(href)
        for relation in relations & _RESOURCE_HINTS:
            self._hints.append((relation, href))

    def _read_script(self, attributes: dict[str, str]) -> None:
        if attributes.get("type", "").strip().lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_parts = []

    def _read_anchor(self, attributes: dict[str, str]) -> None:
        self._anchor = {
            "href": attributes.get("href", "").strip(),
            "rel": attributes.get("rel", "").strip(),
            "aria_label": attributes.get("aria-label", "").strip(),
            "title": attributes.get("title", "").strip(),
            "boilerplate": "1" if self._boilerplate_depth else "",
        }
        self._anchor_parts = []

    # -- character data ---------------------------------------------------- #

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_ld_parts.append(data)
            return
        # 두 번째 title 의 글자는 버린다. 이어 붙이면 없는 제목이 만들어져, 중복 선언을
        # 잡으려던 검사가 길이·중복 검사까지 함께 어지럽힌다.
        if self._in_title and self.page.title_count <= 1:
            self._title_parts.append(data)
        if self._invisible_depth:
            return
        if self._heading_level is not None:
            self._heading_parts.append(data)
        if self._anchor is not None:
            self._anchor_parts.append(data)

        self._full_parts.append(data)
        if self._boilerplate_depth == 0:
            self._body_parts.append(data)
            if self._main_depth:
                self._main_parts.append(data)

    # -- result ------------------------------------------------------------ #

    def finish(self) -> ParsedPage:
        page = self.page
        page.title = _collapse("".join(self._title_parts)) if self._saw_title else None
        page.headings = tuple(self._headings)
        page.links = tuple(self._links)
        page.images = tuple(self._images)
        page.json_ld_blocks = tuple(block for block in self._json_ld if block.strip())
        page.subresources = tuple(self._subresources)
        page.icon_hrefs = tuple(dict.fromkeys(self._icons))
        page.resource_hints = tuple(self._hints)
        page.hreflang = tuple(self._hreflang)
        page.has_breadcrumb = self._breadcrumb
        page.full_text = _collapse(" ".join(self._full_parts))
        parts = self._main_parts if page.has_main else self._body_parts
        page.body_text = _collapse(" ".join(parts))
        return page


def _looks_like_breadcrumb(tag: str, attributes: dict[str, str]) -> bool:
    haystack = " ".join(
        (
            attributes.get("class", ""),
            attributes.get("id", ""),
            attributes.get("aria-label", ""),
            attributes.get("itemtype", ""),
        )
    ).lower()
    if "breadcrumb" in haystack:
        return True
    return tag == "nav" and "탐색 경로" in haystack


def parse_html(source: str | bytes, *, charset: str | None = None) -> ParsedPage:
    """Parse ``source`` into a :class:`ParsedPage`, never raising on malformed markup."""
    if isinstance(source, bytes):
        source = source.decode(charset or "utf-8", errors="replace")

    parser = _PageParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception:  # noqa: S110 - unreadable input is a finding, not a crash
        pass
    return parser.finish()


def visible_text(page: ParsedPage) -> str:
    """All text a reader would see, boilerplate included."""
    return page.full_text


def _collapse(text: str) -> str:
    return " ".join(text.split())


__all__ = ["Anchor", "Image", "ParsedPage", "parse_html", "visible_text"]
