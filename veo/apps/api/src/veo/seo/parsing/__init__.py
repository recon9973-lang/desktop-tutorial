"""Parsing helpers for the SEO collectors, all on the Python standard library.

No parser here decides anything about SEO. They turn bytes into structures; the
collectors read those structures and report observations.
"""

from veo.seo.parsing.html import Anchor, Image, ParsedPage, parse_html, visible_text
from veo.seo.parsing.robots import (
    CRAWLER_AGENT_NAME,
    RobotsDecision,
    RobotsFile,
    RobotsGroup,
    RobotsRule,
    parse_robots,
)
from veo.seo.parsing.sitemap import ParsedSitemap, SitemapEntry, parse_sitemap
from veo.seo.parsing.text import content_length, normalise, shingle_similarity, shingles
from veo.seo.parsing.urls import (
    depth_of,
    host_of,
    is_https,
    normalise_url,
    path_of,
    registrable_domain,
    resolve,
    same_site,
)

__all__ = [
    "CRAWLER_AGENT_NAME",
    "Anchor",
    "Image",
    "ParsedPage",
    "ParsedSitemap",
    "RobotsDecision",
    "RobotsFile",
    "RobotsGroup",
    "RobotsRule",
    "SitemapEntry",
    "content_length",
    "depth_of",
    "host_of",
    "is_https",
    "normalise",
    "normalise_url",
    "parse_html",
    "parse_robots",
    "parse_sitemap",
    "path_of",
    "registrable_domain",
    "resolve",
    "same_site",
    "shingle_similarity",
    "shingles",
    "visible_text",
]
