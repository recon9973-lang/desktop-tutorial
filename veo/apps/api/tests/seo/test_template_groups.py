"""템플릿 그룹 표본 — 자동 생성 문서는 표본으로, 고정 페이지는 전부.

실측 근거(2026-08-02, chamsarang1075.com): 게시판 칼럼 103장의 title 이 전부 같았고
무작위 3장의 뼈대가 완전히 동일했다. 결함이 템플릿 단위이므로 표본이면 잡힌다.

이 파일이 지키는 성질:

1. 고정 페이지(최상위 문서)는 **절대** 그룹이 되지 않는다 — 표본으로 대신할 수 없다.
2. 그룹 상한을 넘어 건너뛴 주소가 있으면 크롤은 "전체를 봤다" 를 선언할 수 없다.
3. 건너뛴 사실이 결과 고지로 나간다 — 숨기면 점수가 사이트 전체처럼 읽힌다.
4. 사람이 직접 지정한 주소(SEED)는 상한과 무관하게 가져온다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from veo.seo.discovery import DiscoveredUrl, DiscoverySource
from veo.seo.template_groups import group_key


class TestGroupKeyIsConservative:
    """오판이 일반화되면 표본의 결함이 무고한 페이지에 씌워진다. 보수적으로 묶는다."""

    def test_a_board_document_query_forms_a_group(self) -> None:
        """실측 그대로의 모양 — 같은 경로, 값만 다른 문서 식별자."""
        a = group_key("https://x.kr/칼럼/?pageid=10&mod=document&uid=188")
        b = group_key("https://x.kr/칼럼/?pageid=6&mod=document&uid=233")

        assert a is not None
        assert a == b, "값이 다른 것이 그룹의 정의다 — 키 집합이 같으면 같은 그룹"

    def test_a_prefixed_article_path_forms_a_group(self) -> None:
        a = group_key("https://x.kr/news/마산-참사랑한의원-이벤트/")
        b = group_key("https://x.kr/news/7월-진료-일정/")

        assert a == b == "/news/*"

    def test_a_top_level_fixed_page_is_never_grouped(self) -> None:
        """고정 페이지는 사람이 한 장씩 만든다. 표본으로 대신할 수 없다."""
        assert group_key("https://x.kr/불면증/") is None
        assert group_key("https://x.kr/") is None
        assert group_key("https://x.kr/오시는-길/") is None

    def test_listing_prefixes_are_never_grouped(self) -> None:
        """목록은 문서를 담는 그릇이다. 수가 적어 표본화할 이유도 없다."""
        assert group_key("https://x.kr/category/침구과/") is None
        assert group_key("https://x.kr/tag/한약/") is None

    def test_an_ordinary_query_does_not_form_a_group(self) -> None:
        """검색·정렬 파라미터는 문서 식별자가 아니다."""
        assert group_key("https://x.kr/진료안내/?sort=asc&lang=ko") is None


class TestSamplingInsideTheCrawler:
    def _crawl(self, pages: dict[str, bytes], **kwargs):  # type: ignore[no-untyped-def]
        import httpx
        from tests.seo.test_console_crawl import _guard

        from veo.core.settings import Settings
        from veo.seo.crawl import ConsoleCrawler

        def handler(request: httpx.Request) -> httpx.Response:
            key = request.url.path + (f"?{request.url.query.decode()}" if request.url.query else "")
            body = pages.get(key)
            if body is None:
                return httpx.Response(404, content=b"none", headers={"content-type": "text/html"})
            media = "text/plain" if request.url.path == "/robots.txt" else "text/html"
            return httpx.Response(200, content=body, headers={"content-type": media})

        settings = Settings(
            console_crawl_group_sample=kwargs.pop("group_sample", 2),
            console_crawl_max_urls=kwargs.pop("max_urls", 8),
        )
        return ConsoleCrawler(
            guard=_guard(), transport=httpx.MockTransport(handler), settings=settings
        ).crawl("https://clinic.example.kr/")

    def _board_site(self, posts: int) -> dict[str, bytes]:
        from urllib.parse import quote

        links = "".join(
            f'<a href="/board/?mod=document&uid={i}">글{i}</a>' for i in range(posts)
        )
        home = f"<html><body><a href='/진료안내/'>안내</a>{links}</body></html>"
        pages = {"/": home.encode()}
        pages[quote("/진료안내/")] = b"<html><body>fixed</body></html>"
        for i in range(posts):
            pages[f"/board/?mod=document&uid={i}"] = b"<html><body>post</body></html>"
        return pages

    def test_the_group_cap_limits_fetches_and_counts_the_rest(self) -> None:
        outcome = self._crawl(self._board_site(posts=9), group_sample=2)

        board = [d for d in outcome.documents if "uid=" in d.final_url]
        assert len(board) == 2, "표본 상한 2 를 넘겨 가져왔다"
        assert sum(outcome.sampled_out.values()) == 7, "건너뛴 수를 세지 않았다"

    def test_fixed_pages_are_still_fetched_in_full(self) -> None:
        outcome = self._crawl(self._board_site(posts=9), group_sample=2)

        from urllib.parse import quote

        fetched = {d.final_url for d in outcome.documents}
        assert f"https://clinic.example.kr{quote('/진료안내/')}" in fetched

    def test_a_sampled_crawl_never_claims_exhaustion(self) -> None:
        """**이 파일에서 가장 중요한 시험.** 표본은 수집 전략이지 "다 봤다" 가 아니다.

        이것이 무너지면 부재형 검사가 표본 위에서 "없음" 을 단정한다 — 방금 고친
        0-A 위반이 다른 문으로 돌아온다.
        """
        outcome = self._crawl(self._board_site(posts=9), group_sample=2)

        assert outcome.sampled_out
        assert outcome.discovery_exhausted is False

    def test_a_small_group_is_untouched_and_exhaustion_still_possible(self) -> None:
        """상한 아래 그룹은 표본이 아니라 전부다 — 전체 선언이 가능해야 한다."""
        outcome = self._crawl(self._board_site(posts=2), group_sample=5, max_urls=50)

        assert not outcome.sampled_out
        assert outcome.discovery_exhausted is True

    def test_a_site_within_the_page_cap_is_never_sampled(self) -> None:
        """**전량을 볼 수 있으면 전부 본다.**

        볼 수 있는데 표본을 쓰면 결함 비율이 희석되어 점수가 오른다 — 실측
        (2026-08-02, chamsarang)에서 게시판 canonical 결함률 60% 가 표본 후 23% 로
        왜곡되며 점수가 71.8 → 77.6 이 됐다. 덜 재서 점수가 오르는 것은 이 제품이
        금지하는 방향이고, 표본은 전량의 대체가 아니라 잘림의 대체다.
        """
        outcome = self._crawl(self._board_site(posts=9), group_sample=2, max_urls=50)

        board = [d for d in outcome.documents if "uid=" in d.final_url]
        assert len(board) == 9, "상한 안에 드는데 표본으로 줄였다"
        assert not outcome.sampled_out

    def test_a_seed_url_ignores_the_cap(self) -> None:
        """직원이 특정 글을 지정했다면 그것은 시킨 일이다."""
        from veo.seo.crawl import _apply_group_sampling

        frontier = tuple(
            DiscoveredUrl(
                url=f"https://x.kr/board/?mod=document&uid={i}",
                source=DiscoverySource.SEED if i == 5 else DiscoverySource.LINK,
            )
            for i in range(6)
        )
        kept, skipped = _apply_group_sampling(frontier, {}, 1)

        kept_urls = {r.url for r in kept}
        assert "https://x.kr/board/?mod=document&uid=5" in kept_urls
        assert sum(skipped.values()) == 4  # LINK 5개 중 1개만 표본


class TestTheSampleIsDisclosed:
    def test_the_scan_notes_say_what_was_sampled(self) -> None:
        from veo.collect.from_crawl import _sampling_notes
        from veo.seo.crawl import CrawlOutcome

        outcome = CrawlOutcome(
            documents=(),
            sampled_out={"/칼럼/?mod,pageid,uid": 91},
            group_fetched={"/칼럼/?mod,pageid,uid": 12},
        )
        notes = _sampling_notes(outcome)

        assert len(notes) == 1
        assert "103장 중 12장을 표본" in notes[0]
        assert "개별 문서만의 문제는 이번 측정 범위 밖" in notes[0]
        assert "mod,pageid,uid" not in notes[0], "내부 그룹 키가 사람에게 새면 안 된다"

    def test_no_sampling_means_no_note(self) -> None:
        from veo.collect.from_crawl import _sampling_notes
        from veo.seo.crawl import CrawlOutcome

        assert _sampling_notes(CrawlOutcome(documents=())) == ()
