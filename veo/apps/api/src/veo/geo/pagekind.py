"""What kind of page is this, so that "not applicable" can mean something.

Applicability is where most readiness tools go wrong: a product page has no byline, a
company's About page has no publication date, and a business that trades only online has
no address to be inconsistent about. Scoring those as failures tells the owner to do
something pointless.

The classification below is a heuristic and is used only to decide *whether* a check
applies — never to decide how it turns out. It reads the URL and the visible page before
it looks at any structured data, so that "the schema says Product" cannot make the schema
check about the page type pass by construction.
"""

from __future__ import annotations

import re
from enum import StrEnum
from urllib.parse import urlparse

from veo.geo.parsing import PageDocument

_PRODUCT_PATH = re.compile(r"/(products?|item|goods|shop|store)/", re.IGNORECASE)
_ARTICLE_PATH = re.compile(r"/(blog|news|posts?|articles?|guide|magazine|20\d\d)/", re.IGNORECASE)
_CORPORATE_PATH = re.compile(r"/(about|company|corporate|who-we-are|introduction)", re.IGNORECASE)
_CONTACT_PATH = re.compile(r"/(contact|location|directions|오시는길)", re.IGNORECASE)

_ADDRESS_PATTERN = re.compile(
    r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|제주)"
    r"[^,\n]{0,30}?(로|길|대로)\s?\d+"
)

_TELEPHONE_PATTERN = re.compile(r"0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}")

_BYLINE_MARKERS = ("글 ", "글:", "작성자", "기자", "감수", "by ", "취재")

_CORPORATE_HEADINGS = ("회사 소개", "회사소개", "about us", "기업 소개")


class PageKind(StrEnum):
    PRODUCT = "PRODUCT"
    ARTICLE = "ARTICLE"
    LOCAL_BUSINESS = "LOCAL_BUSINESS"
    CORPORATE = "CORPORATE"
    CONTACT = "CONTACT"
    GENERIC = "GENERIC"


#: Page kinds where a named author or reviewer is a reasonable expectation.
KINDS_EXPECTING_AN_AUTHOR = frozenset(
    {PageKind.ARTICLE, PageKind.LOCAL_BUSINESS, PageKind.GENERIC}
)

#: Page kinds where publication and revision dates are a reasonable expectation.
KINDS_EXPECTING_DATES = frozenset({PageKind.ARTICLE, PageKind.LOCAL_BUSINESS, PageKind.GENERIC})

_ALLOWED_TYPES: dict[PageKind, frozenset[str]] = {
    PageKind.PRODUCT: frozenset(
        {
            "product", "productgroup", "offer", "aggregateoffer", "itempage", "webpage",
            "website", "organization", "brand", "breadcrumblist", "review", "faqpage",
        }
    ),
    PageKind.ARTICLE: frozenset(
        {
            "article", "newsarticle", "blogposting", "techarticle", "report", "webpage",
            "website", "person", "organization", "newsmediaorganization", "breadcrumblist",
            "faqpage", "imageobject",
        }
    ),
    PageKind.LOCAL_BUSINESS: frozenset(
        {
            "localbusiness", "dentist", "medicalclinic", "medicalbusiness", "hospital",
            "physician", "store", "restaurant", "healthandbeautybusiness", "organization",
            "webpage", "website", "faqpage", "offer", "breadcrumblist", "article",
            "person", "service", "medicalwebpage", "place", "professionalservice",
        }
    ),
    PageKind.CORPORATE: frozenset(
        {
            "organization", "corporation", "aboutpage", "contactpage", "webpage", "website",
            "breadcrumblist", "person",
        }
    ),
    PageKind.CONTACT: frozenset(
        {"contactpage", "organization", "localbusiness", "webpage", "website", "place"}
    ),
    PageKind.GENERIC: frozenset(
        {
            "webpage", "website", "organization", "service", "faqpage", "breadcrumblist",
            "collectionpage", "itemlist", "person",
        }
    ),
}


def classify(page: PageDocument, url: str) -> PageKind:
    """Best guess at the page's purpose, from the URL and what a reader would see."""
    path = urlparse(url).path or "/"
    text = page.visible_text

    if _PRODUCT_PATH.search(path):
        return PageKind.PRODUCT
    if _CORPORATE_PATH.search(path) or _has_corporate_heading(page):
        return PageKind.CORPORATE
    if _CONTACT_PATH.search(path):
        return PageKind.CONTACT
    if has_physical_presence(page):
        return PageKind.LOCAL_BUSINESS
    if _ARTICLE_PATH.search(path) or _looks_like_an_article(page, text):
        return PageKind.ARTICLE
    return PageKind.GENERIC


def has_physical_presence(page: PageDocument) -> bool:
    """An address a customer could walk to, stated on the page itself."""
    return bool(_ADDRESS_PATTERN.search(page.visible_text))


def visible_addresses(page: PageDocument) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _ADDRESS_PATTERN.finditer(page.visible_text))


def visible_telephones(page: PageDocument) -> tuple[str, ...]:
    numbers = [match.group(0) for match in _TELEPHONE_PATTERN.finditer(page.visible_text)]
    for link in page.links:
        if link.href.lower().startswith("tel:"):
            numbers.append(link.href[4:])
    return tuple(dict.fromkeys(numbers))


def type_is_appropriate(kind: PageKind, declared_types: tuple[str, ...]) -> tuple[str, ...]:
    """Declared types that do not belong on a page of this kind."""
    allowed = _ALLOWED_TYPES[kind]
    return tuple(t for t in declared_types if t.lower() not in allowed)


def expected_types(kind: PageKind, declared_types: tuple[str, ...]) -> tuple[str, ...]:
    allowed = _ALLOWED_TYPES[kind]
    return tuple(t for t in declared_types if t.lower() in allowed)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _has_corporate_heading(page: PageDocument) -> bool:
    headings = " ".join(h.text.lower() for h in page.content_headings() if h.level == 1)
    return any(marker in headings for marker in _CORPORATE_HEADINGS)


def _looks_like_an_article(page: PageDocument, text: str) -> bool:
    has_byline = any(marker in text for marker in _BYLINE_MARKERS)
    has_dates = bool(page.timestamps) or bool(page.property_value("article:published_time"))
    return has_byline and has_dates


__all__ = [
    "KINDS_EXPECTING_AN_AUTHOR",
    "KINDS_EXPECTING_DATES",
    "PageKind",
    "classify",
    "expected_types",
    "has_physical_presence",
    "type_is_appropriate",
    "visible_addresses",
    "visible_telephones",
]
