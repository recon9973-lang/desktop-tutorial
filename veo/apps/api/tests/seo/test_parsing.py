"""Parsing helpers: HTML, robots.txt and sitemaps, all on the standard library.

``lxml`` and ``beautifulsoup4`` are not installed and VEO does not add a dependency to
read a fixture, so these are built on ``html.parser``. The tests below pin the behaviour
that the collectors rely on, including the malformed input a real crawl produces.
"""

from __future__ import annotations

import pytest
from tests.seo.support import FIXTURE_ROOT

from veo.seo.parsing import (
    RobotsFile,
    parse_html,
    parse_robots,
    parse_sitemap,
    shingle_similarity,
    visible_text,
)

HEALTHY_HOME = (FIXTURE_ROOT / "healthy" / "pages" / "index.html").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #


def test_head_metadata_is_read_from_a_real_page() -> None:
    page = parse_html(HEALTHY_HOME)
    assert page.title == "온담의원 — 서울 마포 피부과 진료 안내"
    assert page.meta_description is not None
    assert page.lang == "ko"
    assert page.canonical == "https://healthy.example.kr/"
    assert page.viewport == "width=device-width, initial-scale=1"
    assert page.meta_robots is None


def test_headings_keep_their_level_and_order() -> None:
    page = parse_html(HEALTHY_HOME)
    assert [level for level, _ in page.headings] == [1, 2, 3, 2]
    assert page.headings[0][1] == "온담의원 피부과 진료"


def test_links_carry_their_anchor_text() -> None:
    page = parse_html(HEALTHY_HOME)
    hrefs = {link.href for link in page.links}
    assert "/services/" in hrefs
    laser = next(link for link in page.links if link.href == "/services/laser/")
    assert laser.text.strip() != ""


def test_images_record_a_missing_alt_apart_from_an_empty_one() -> None:
    page = parse_html(
        '<html><body><img src="/a.jpg" alt="설명"><img src="/b.jpg" alt="">'
        '<img src="/c.jpg"></body></html>'
    )
    assert [image.alt for image in page.images] == ["설명", "", None]


def test_json_ld_blocks_are_returned_raw_so_a_syntax_error_survives() -> None:
    page = parse_html(HEALTHY_HOME)
    assert len(page.json_ld_blocks) == 1
    assert "MedicalClinic" in page.json_ld_blocks[0]


def test_open_graph_properties_are_read() -> None:
    page = parse_html(HEALTHY_HOME)
    assert page.open_graph["og:site_name"] == "온담의원"
    assert page.open_graph["og:url"] == "https://healthy.example.kr/"


def test_hreflang_alternates_are_collected() -> None:
    page = parse_html(
        (FIXTURE_ROOT / "conflicting_hreflang" / "pages" / "ko.html").read_text(encoding="utf-8")
    )
    assert dict(page.hreflang) == {
        "ko": "https://hreflang.example.kr/ko/",
        "en": "https://hreflang.example.kr/en/",
    }


def test_script_and_style_text_never_reaches_the_visible_text() -> None:
    page = parse_html(
        "<html><body><main><p>본문입니다</p><script>var a = '숨은 글자';</script>"
        "<style>.a{content:'숨은 글자'}</style></main></body></html>"
    )
    assert "본문입니다" in visible_text(page)
    assert "숨은 글자" not in visible_text(page)


def test_boilerplate_outside_main_is_excluded_from_the_body_text() -> None:
    page = parse_html(
        "<html><body><nav><a href='/'>메뉴</a></nav><main><p>본문 내용</p></main>"
        "<footer><p>바닥글</p></footer></body></html>"
    )
    assert "본문 내용" in page.body_text
    assert "메뉴" not in page.body_text
    assert "바닥글" not in page.body_text


def test_an_unclosed_tag_does_not_stop_the_parse() -> None:
    page = parse_html("<html><body><main><p>첫 문단<p>둘째 문단</main></body></html>")
    assert "첫 문단" in page.body_text
    assert "둘째 문단" in page.body_text


def test_subresources_are_listed_for_the_mixed_content_check() -> None:
    page = parse_html(
        '<html><head><link rel="stylesheet" href="http://cdn.example.com/a.css"></head>'
        '<body><img src="http://img.example.com/b.jpg" alt="x">'
        '<script src="https://cdn.example.com/c.js"></script></body></html>'
    )
    assert "http://cdn.example.com/a.css" in page.subresources
    assert "http://img.example.com/b.jpg" in page.subresources
    assert "https://cdn.example.com/c.js" in page.subresources


def test_a_breadcrumb_navigation_is_detected() -> None:
    assert parse_html(HEALTHY_HOME).has_breadcrumb
    assert not parse_html("<html><body><main><p>없음</p></main></body></html>").has_breadcrumb


def test_pagination_relations_are_read() -> None:
    page = parse_html(
        (FIXTURE_ROOT / "duplicate_metadata" / "pages" / "list.html").read_text(encoding="utf-8")
    )
    assert page.rel_next == "https://dup.example.kr/list/page/2/"
    assert page.rel_prev is None


# --------------------------------------------------------------------------- #
# robots.txt
# --------------------------------------------------------------------------- #


def _robots(text: str) -> RobotsFile:
    return parse_robots(text)


def test_a_missing_rule_means_the_url_is_allowed() -> None:
    decision = _robots("User-agent: *\nDisallow: /admin/\n").decide("/about/")
    assert decision.allowed
    assert decision.matched_rule is None


def test_the_matched_rule_is_recorded_as_evidence() -> None:
    decision = _robots("User-agent: *\nDisallow: /admin/\n").decide("/admin/panel")
    assert not decision.allowed
    assert decision.matched_rule == "Disallow: /admin/"
    assert decision.line_number == 2


def test_the_longest_matching_pattern_wins() -> None:
    robots = _robots("User-agent: *\nDisallow: /a/\nAllow: /a/b/\n")
    assert robots.decide("/a/b/c").allowed
    assert not robots.decide("/a/z").allowed


def test_allow_beats_disallow_when_the_patterns_are_the_same_length() -> None:
    robots = _robots("User-agent: *\nDisallow: /page\nAllow: /page\n")
    assert robots.decide("/page").allowed


def test_an_empty_disallow_allows_everything() -> None:
    assert _robots("User-agent: *\nDisallow:\n").decide("/anything").allowed


def test_disallow_slash_blocks_the_whole_site() -> None:
    assert not _robots("User-agent: *\nDisallow: /\n").decide("/").allowed


def test_a_named_group_takes_precedence_over_the_wildcard_group() -> None:
    robots = _robots("User-agent: *\nDisallow: /\n\nUser-agent: Yeti\nAllow: /\n")
    assert robots.decide("/", user_agent="Yeti").allowed
    assert not robots.decide("/", user_agent="Googlebot").allowed


def test_consecutive_user_agent_lines_form_one_group() -> None:
    robots = _robots("User-agent: Yeti\nUser-agent: Googlebot\nDisallow: /private/\n")
    assert not robots.decide("/private/x", user_agent="Googlebot").allowed
    assert not robots.decide("/private/x", user_agent="Yeti").allowed


def test_wildcards_and_end_anchors_are_honoured() -> None:
    robots = _robots("User-agent: *\nDisallow: /*.pdf$\n")
    assert not robots.decide("/docs/manual.pdf").allowed
    assert robots.decide("/docs/manual.pdf?v=1").allowed


def test_comments_and_blank_lines_are_ignored() -> None:
    robots = _robots("# 주석\n\nUser-agent: *   # 모두\nDisallow: /x/\n")
    assert not robots.decide("/x/y").allowed


def test_sitemap_directives_are_collected_regardless_of_group() -> None:
    robots = _robots(
        "Sitemap: https://a.example.kr/sitemap.xml\n"
        "User-agent: *\nDisallow:\nSitemap: https://a.example.kr/news.xml\n"
    )
    assert robots.sitemaps == (
        "https://a.example.kr/sitemap.xml",
        "https://a.example.kr/news.xml",
    )


def test_an_empty_robots_file_allows_everything() -> None:
    assert _robots("").decide("/anything").allowed


def test_a_path_is_matched_case_sensitively_but_the_agent_is_not() -> None:
    robots = _robots("User-agent: YETI\nDisallow: /Private/\n")
    assert not robots.decide("/Private/x", user_agent="yeti").allowed
    assert robots.decide("/private/x", user_agent="yeti").allowed


# --------------------------------------------------------------------------- #
# sitemap
# --------------------------------------------------------------------------- #


def test_a_urlset_yields_its_locations() -> None:
    text = (FIXTURE_ROOT / "healthy" / "sitemap.xml").read_text(encoding="utf-8")
    sitemap = parse_sitemap(text)
    assert sitemap.kind == "urlset"
    assert "https://healthy.example.kr/services/laser/" in sitemap.locations
    assert len(sitemap.locations) == 4


def test_a_sitemap_index_is_recognised() -> None:
    sitemap = parse_sitemap(
        '<?xml version="1.0"?><sitemapindex><sitemap>'
        "<loc>https://a.example.kr/s1.xml</loc></sitemap></sitemapindex>"
    )
    assert sitemap.kind == "sitemapindex"
    assert sitemap.locations == ("https://a.example.kr/s1.xml",)


def test_a_malformed_sitemap_reports_rather_than_raises() -> None:
    sitemap = parse_sitemap("이것은 XML이 아닙니다")
    assert sitemap.kind == "unknown"
    assert sitemap.locations == ()


def test_entity_declarations_are_not_expanded() -> None:
    """A sitemap is untrusted input; an entity bomb must not be resolved."""
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE urlset ['
        '<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;">]>'
        "<urlset><url><loc>https://a.example.kr/&b;</loc></url></urlset>"
    )
    sitemap = parse_sitemap(bomb)
    assert all("aaaaaaaaaa" not in location for location in sitemap.locations)


# --------------------------------------------------------------------------- #
# similarity
# --------------------------------------------------------------------------- #


def test_identical_text_is_fully_similar() -> None:
    assert shingle_similarity("가나다 라마바 사아자", "가나다 라마바 사아자") == pytest.approx(1.0)


def test_unrelated_text_is_barely_similar() -> None:
    assert shingle_similarity("가나다 라마바 사아자", "카타파 하거너 더러머") < 0.1


def test_similarity_is_symmetric() -> None:
    a, b = "하나 둘 셋 넷 다섯", "하나 둘 셋 여섯 일곱"
    assert shingle_similarity(a, b) == pytest.approx(shingle_similarity(b, a))
