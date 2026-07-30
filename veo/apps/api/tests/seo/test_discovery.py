"""주소를 어떻게 찾는가.

발견은 네트워크 없이 시험할 수 있어야 한다 — 사이트맵 본문과 HTML 문자열만 주면 어떤
주소가 나오는지 결정되기 때문이다. 그래서 이 파일에는 모의 전송조차 없다.
"""

from __future__ import annotations

from veo.seo.discovery import (
    DiscoverySource,
    allowed_by_robots,
    build_frontier,
    links_on_page,
    looks_like_a_page,
    sitemap_candidates,
    sitemap_index_targets,
    urls_in_sitemaps,
)
from veo.seo.parsing.robots import parse_robots

ENTRY = "https://example.com/"


def _urlset(*locations: str) -> str:
    body = "".join(f"<url><loc>{location}</loc></url>" for location in locations)
    return f"<?xml version='1.0'?><urlset>{body}</urlset>"


def _index(*locations: str) -> str:
    body = "".join(f"<sitemap><loc>{location}</loc></sitemap>" for location in locations)
    return f"<?xml version='1.0'?><sitemapindex>{body}</sitemapindex>"


class TestSitemapCandidates:
    def test_uses_the_declaration_when_robots_has_one(self) -> None:
        robots = parse_robots("Sitemap: https://example.com/sitemap-news.xml\n")

        assert sitemap_candidates(ENTRY, robots) == ("https://example.com/sitemap-news.xml",)

    def test_does_not_also_guess_the_conventional_path(self) -> None:
        """선언이 있는데 관례 경로까지 두드리면 없는 파일을 요청하는 셈이다."""
        robots = parse_robots("Sitemap: https://example.com/custom.xml\n")

        assert "https://example.com/sitemap.xml" not in sitemap_candidates(ENTRY, robots)

    def test_falls_back_to_the_conventional_path(self) -> None:
        assert sitemap_candidates(ENTRY, parse_robots("User-agent: *\n")) == (
            "https://example.com/sitemap.xml",
        )

    def test_no_robots_at_all_still_tries_the_conventional_path(self) -> None:
        assert sitemap_candidates(ENTRY, None) == ("https://example.com/sitemap.xml",)

    def test_a_declaration_pointing_elsewhere_is_dropped(self) -> None:
        """robots.txt 는 진단 대상이 쓴 파일이다. 그대로 따라가면 임의 주소로 요청을 보낸다."""
        robots = parse_robots("Sitemap: https://attacker.example.net/sitemap.xml\n")

        assert sitemap_candidates(ENTRY, robots) == ("https://example.com/sitemap.xml",)


class TestSitemapIndex:
    def test_follows_an_index(self) -> None:
        body = _index("https://example.com/a.xml", "https://example.com/b.xml")

        targets = sitemap_index_targets(ENTRY, body, limit=10)

        assert targets == ("https://example.com/a.xml", "https://example.com/b.xml")

    def test_a_plain_urlset_is_not_an_index(self) -> None:
        assert sitemap_index_targets(ENTRY, _urlset("https://example.com/a"), limit=10) == ()

    def test_offsite_entries_are_dropped(self) -> None:
        body = _index("https://elsewhere.example.net/a.xml")

        assert sitemap_index_targets(ENTRY, body, limit=10) == ()

    def test_the_limit_is_honoured(self) -> None:
        body = _index(*[f"https://example.com/{n}.xml" for n in range(50)])

        assert len(sitemap_index_targets(ENTRY, body, limit=3)) == 3


class TestUrlsInSitemaps:
    def test_reads_the_declared_pages(self) -> None:
        sitemaps = {
            "https://example.com/sitemap.xml": _urlset(
                "https://example.com/a", "https://example.com/b"
            )
        }

        found = urls_in_sitemaps(ENTRY, sitemaps)

        assert {record.url for record in found} == {
            "https://example.com/a",
            "https://example.com/b",
        }
        assert all(record.source is DiscoverySource.SITEMAP for record in found)

    def test_an_index_declares_no_pages(self) -> None:
        """index 항목은 사이트맵 주소이지 페이지가 아니다. 페이지로 세면 없는 페이지를 만든다."""
        sitemaps = {"https://example.com/sitemap.xml": _index("https://example.com/a.xml")}

        assert urls_in_sitemaps(ENTRY, sitemaps) == ()

    def test_unreadable_sitemaps_yield_nothing_rather_than_raising(self) -> None:
        sitemaps = {"https://example.com/sitemap.xml": "<<< 깨진 문서"}

        assert urls_in_sitemaps(ENTRY, sitemaps) == ()

    def test_records_which_sitemap_named_it(self) -> None:
        sitemaps = {"https://example.com/s.xml": _urlset("https://example.com/a")}

        assert urls_in_sitemaps(ENTRY, sitemaps)[0].found_on == "https://example.com/s.xml"


class TestLinksOnPage:
    def test_finds_internal_links_in_document_order(self) -> None:
        html = (
            "<html><body>"
            "<a href='/first'>1</a><a href='/second'>2</a>"
            "<a href='https://elsewhere.example.net/x'>바깥</a>"
            "</body></html>"
        )

        found = links_on_page(ENTRY, html)

        assert [record.url for record in found] == [
            "https://example.com/first",
            "https://example.com/second",
        ]

    def test_the_page_does_not_discover_itself(self) -> None:
        found = links_on_page(ENTRY, "<a href='/'>홈</a>")

        assert found == ()

    def test_non_page_schemes_are_not_links(self) -> None:
        html = "<a href='mailto:a@example.com'>메일</a><a href='tel:021234'>전화</a>"

        assert links_on_page(ENTRY, html) == ()


class TestRobotsIsObeyed:
    def test_a_disallowed_path_is_refused(self) -> None:
        robots = parse_robots("User-agent: *\nDisallow: /private\n")

        assert not allowed_by_robots(robots, "https://example.com/private/x")

    def test_no_robots_means_allowed(self) -> None:
        assert allowed_by_robots(None, "https://example.com/anything")


class TestFrontier:
    def test_people_first_then_sitemap_then_links(self) -> None:
        """상한에 걸려 잘리는 것은 언제나 뒤쪽이어야 한다."""
        discovered = [
            *urls_in_sitemaps(ENTRY, {"https://example.com/s.xml": _urlset("https://example.com/sm")}),
            *links_on_page(ENTRY, "<a href='/link'>l</a>"),
        ]

        frontier, _ = build_frontier(
            ENTRY, seeds=["https://example.com/seed"], discovered=discovered, limit=10
        )

        assert [record.source for record in frontier] == [
            DiscoverySource.SEED,
            DiscoverySource.SITEMAP,
            DiscoverySource.LINK,
        ]

    def test_the_entry_url_is_never_in_the_frontier(self) -> None:
        frontier, _ = build_frontier(
            ENTRY, discovered=links_on_page("https://example.com/a", "<a href='/'>홈</a>"), limit=10
        )

        assert frontier == ()

    def test_already_seen_urls_are_skipped(self) -> None:
        discovered = links_on_page(ENTRY, "<a href='/a'>a</a><a href='/b'>b</a>")

        frontier, _ = build_frontier(
            ENTRY, discovered=discovered, limit=10, seen={"https://example.com/a"}
        )

        assert [record.url for record in frontier] == ["https://example.com/b"]

    def test_robots_blocked_urls_are_reported_not_silently_dropped(self) -> None:
        robots = parse_robots("User-agent: *\nDisallow: /private\n")
        discovered = links_on_page(ENTRY, "<a href='/private/x'>비공개</a><a href='/ok'>공개</a>")

        frontier, blocked = build_frontier(ENTRY, discovered=discovered, robots=robots, limit=10)

        assert [record.url for record in frontier] == ["https://example.com/ok"]
        assert blocked == ("https://example.com/private/x",)

    def test_a_seed_is_not_filtered_by_robots(self) -> None:
        """사람이 직접 지정한 주소는 우리가 넓힌 범위가 아니라 시킨 일이다."""
        robots = parse_robots("User-agent: *\nDisallow: /\n")

        frontier, blocked = build_frontier(
            ENTRY, seeds=["https://example.com/private"], robots=robots, limit=10
        )

        assert [record.url for record in frontier] == ["https://example.com/private"]
        assert blocked == ()

    def test_the_limit_cuts_the_tail(self) -> None:
        discovered = links_on_page(
            ENTRY, "".join(f"<a href='/{n}'>{n}</a>" for n in range(20))
        )

        frontier, _ = build_frontier(ENTRY, discovered=discovered, limit=5)

        assert len(frontier) == 5

    def test_a_spent_limit_asks_for_nothing(self) -> None:
        discovered = links_on_page(ENTRY, "<a href='/a'>a</a>")

        assert build_frontier(ENTRY, discovered=discovered, limit=0) == ((), ())

    def test_duplicates_across_sources_are_fetched_once(self) -> None:
        discovered = [
            *urls_in_sitemaps(ENTRY, {"https://example.com/s.xml": _urlset("https://example.com/a")}),
            *links_on_page(ENTRY, "<a href='/a'>같은 곳</a>"),
        ]

        frontier, _ = build_frontier(ENTRY, discovered=discovered, limit=10)

        assert [record.url for record in frontier] == ["https://example.com/a"]


class TestNonPageUrls:
    """확실히 페이지가 아닌 주소에는 요청을 보내지 않는다.

    실측에서 이미지 사이트맵 하나가 25장 예산 가운데 9장을 이미지 내려받기로 태웠다.
    아홉 번 모두 "분석할 수 없는 형식" 으로 버려졌고, 그 아홉 번은 대상 서버가 실제로
    치른 비용이다.
    """

    def test_images_are_not_pages(self) -> None:
        assert not looks_like_a_page("https://example.com/wp-content/uploads/a.png")
        assert not looks_like_a_page("https://example.com/logo.SVG")

    def test_documents_and_media_are_not_pages(self) -> None:
        assert not looks_like_a_page("https://example.com/brochure.pdf")
        assert not looks_like_a_page("https://example.com/clip.mp4")

    def test_an_extensionless_path_is_a_page(self) -> None:
        assert looks_like_a_page("https://example.com/about")
        assert looks_like_a_page("https://example.com/")

    def test_ambiguous_server_extensions_stay_pages(self) -> None:
        """페이지를 놓치는 쪽이 이미지를 한 장 더 받는 쪽보다 나쁘다."""
        assert looks_like_a_page("https://example.com/index.php")
        assert looks_like_a_page("https://example.com/page.aspx")
        assert looks_like_a_page("https://example.com/a.html")

    def test_a_dot_in_a_directory_name_is_not_an_extension(self) -> None:
        assert looks_like_a_page("https://example.com/v1.2/about")

    def test_the_frontier_drops_them_without_calling_them_failures(self) -> None:
        discovered = links_on_page(ENTRY, "<a href='/a.png'>그림</a><a href='/about'>소개</a>")

        frontier, blocked = build_frontier(ENTRY, discovered=discovered, limit=10)

        assert [record.url for record in frontier] == ["https://example.com/about"]
        assert blocked == ()

    def test_a_seed_is_fetched_even_if_it_looks_like_a_file(self) -> None:
        """사람이 그 주소를 진단하라고 했으면 진단한다."""
        frontier, _ = build_frontier(ENTRY, seeds=["https://example.com/report.pdf"], limit=10)

        assert [record.url for record in frontier] == ["https://example.com/report.pdf"]
