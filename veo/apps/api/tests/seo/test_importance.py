"""URL 중요도 분류.

측정 범위는 중요도로 가중되므로, 여기서 틀리면 점수가 틀린다. 예전에는 수집한 모든
페이지가 `CONVERSION_OR_HOME`(3.0) 이었다 — 태그 페이지 한 장이 홈페이지와 같은 무게였다.

이 파일은 두 가지를 고정한다. 붙이는 것이 맞게 붙는지, 그리고 **붙이지 않기로 한 것을
정말 붙이지 않는지**. 두 번째가 더 중요하다 — 지어낸 분류는 조용히 점수를 흔든다.
"""

from __future__ import annotations

import pytest

from veo.contracts.enums import UrlImportance
from veo.seo.importance import classify_url, classify_urls

ENTRY = "https://clinic.example.kr/"


def _of(path: str) -> UrlImportance:
    return classify_url(f"https://clinic.example.kr{path}", entry_url=ENTRY)


class TestHome:
    def test_the_entry_url_is_the_home_page(self) -> None:
        assert _of("/") is UrlImportance.CONVERSION_OR_HOME

    def test_a_bare_origin_is_the_home_page(self) -> None:
        assert classify_url("https://clinic.example.kr", entry_url=ENTRY) is (
            UrlImportance.CONVERSION_OR_HOME
        )

    def test_the_entry_url_wins_even_when_it_is_deep(self) -> None:
        """사람이 "이걸 진단해 달라" 고 지정한 주소가 그 진단의 대표 페이지다."""
        entry = "https://clinic.example.kr/branch/gangnam/"

        assert classify_url(entry, entry_url=entry) is UrlImportance.CONVERSION_OR_HOME


class TestConversionPages:
    @pytest.mark.parametrize(
        "path",
        ["/contact/", "/reservation/", "/booking/", "/pricing/", "/directions/"],
    )
    def test_english_conversion_paths(self, path: str) -> None:
        assert _of(path) is UrlImportance.CONVERSION_OR_HOME

    @pytest.mark.parametrize(
        "path",
        ["/문의/", "/예약/", "/상담신청/", "/오시는길/", "/진료시간/"],
    )
    def test_korean_conversion_paths(self, path: str) -> None:
        """첫 시장이 국내 병원이다. `contact` 만 보면 `문의` 를 놓친다."""
        assert _of(path) is UrlImportance.CONVERSION_OR_HOME

    def test_a_partial_word_match_is_not_a_conversion_page(self) -> None:
        """부분 일치를 허용하면 `/contactless-treatment/` 가 전환 페이지가 된다."""
        assert _of("/contactless-treatment/") is UrlImportance.CONTENT_OR_PRODUCT

    def test_a_conversion_word_deeper_in_the_path_still_counts(self) -> None:
        assert _of("/clinic/gangnam/contact/") is UrlImportance.CONVERSION_OR_HOME


class TestFilteredListings:
    @pytest.mark.parametrize(
        "path",
        ["/notice/page/2/", "/tag/laser/", "/category/skin/", "/author/kim/", "/search/"],
    )
    def test_listing_paths(self, path: str) -> None:
        assert _of(path) is UrlImportance.TAG_OR_FILTER

    @pytest.mark.parametrize(
        "path", ["/notice/?page=3", "/products/?sort=price", "/?s=레이저"]
    )
    def test_listing_query_strings(self, path: str) -> None:
        assert _of(path) is UrlImportance.TAG_OR_FILTER

    def test_a_filter_beats_a_conversion_word(self) -> None:
        """`/pricing/page/2/` 는 가격 페이지가 아니라 가격 목록의 두 번째 장이다."""
        assert _of("/pricing/page/2/") is UrlImportance.TAG_OR_FILTER

    def test_the_home_page_with_a_search_query_is_a_listing(self) -> None:
        assert _of("/?s=레이저") is UrlImportance.TAG_OR_FILTER


class TestTheNeutralDefault:
    @pytest.mark.parametrize(
        "path", ["/services/laser/", "/about/", "/deep/", "/notice/2026/여름-휴진/"]
    )
    def test_anything_else_is_ordinary_content(self, path: str) -> None:
        assert _of(path) is UrlImportance.CONTENT_OR_PRODUCT


class TestWhatItDeliberatelyDoesNotClaim:
    def test_it_never_guesses_category_or_hub(self) -> None:
        """픽스처가 이유를 보여 준다 — 같은 1단계인데 `/guide/` 는 허브, `/deep/` 은 콘텐츠다.

        사람이 뜻으로 라벨한 것이고 주소 모양에서는 나오지 않는다. 규칙을 지어내면 절반은
        틀리고, 틀린 절반은 조용히 점수를 흔든다.
        """
        paths = ["/guide/", "/deep/", "/services/", "/list/", "/notice/"]

        assert all(_of(path) is not UrlImportance.CATEGORY_OR_HUB for path in paths)

    def test_it_never_guesses_intentional_noindex(self) -> None:
        """배점이 0 이라 분모에서 빠진다. 태그만 보고 "의도된 것" 이라 단정하면 실수로
        걸린 noindex 를 우리가 숨겨 주는 셈이 된다 — 그것이 가장 큰 결함인데."""
        paths = ["/", "/thank-you/", "/print/", "/admin/", "/contact/"]

        assert all(_of(path) is not UrlImportance.INTENTIONAL_NOINDEX for path in paths)


class TestTheTable:
    def test_keys_are_returned_untouched(self) -> None:
        """이 표는 수집한 문서의 **최종 주소**로 조회된다. 키를 바꾸면 조회가 빗나가고,
        그때 모든 페이지가 조용히 기본값으로 떨어진다."""
        urls = ["https://clinic.example.kr/Contact/", "https://clinic.example.kr/a/?page=2"]

        table = classify_urls(urls, entry_url=ENTRY)

        assert set(table) == set(urls)

    def test_values_are_specification_class_names(self) -> None:
        """배점 숫자는 명세에만 있다. 여기서 돌려주는 것은 이름이다."""
        table = classify_urls([ENTRY], entry_url=ENTRY)

        assert table[ENTRY] == UrlImportance.CONVERSION_OR_HOME.value

    def test_a_real_site_gets_more_than_one_class(self) -> None:
        """예전 동작의 회귀 검사 — 전부 같은 값이면 가중치가 없는 것과 같다."""
        urls = [
            ENTRY,
            "https://clinic.example.kr/contact/",
            "https://clinic.example.kr/services/laser/",
            "https://clinic.example.kr/notice/page/2/",
        ]

        table = classify_urls(urls, entry_url=ENTRY)

        assert len(set(table.values())) >= 3
