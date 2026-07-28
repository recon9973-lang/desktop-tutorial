"""Whose URL was cited — decided by normalisation, never by string comparison.

A citation is a different fact from a mention and is worth more, so the one thing this
module must never do is hand a third party's URL to the customer. It must also not lose
the customer's own URL behind a redirect wrapper, which is how most engines present a
source.
"""

from __future__ import annotations

import pytest

from veo.observations.detection import BrandProfile
from veo.observations.detection.citations import (
    CitationOwnership,
    match_citations,
    registrable_domain,
)

BRAND = BrandProfile(
    entity_key="venom-dental",
    display_name="베놈치과",
    own_domains=("venomdental.co.kr",),
)


def ownerships(*urls: str, profile: BrandProfile = BRAND) -> list[CitationOwnership]:
    return [item.ownership for item in match_citations(urls, profile)]


def test_our_own_url_is_ours() -> None:
    assert ownerships("https://venomdental.co.kr/implant") == [CitationOwnership.OWN]


def test_a_subdomain_of_our_domain_is_ours() -> None:
    assert ownerships("https://blog.venomdental.co.kr/cost") == [CitationOwnership.OWN]


def test_a_lookalike_domain_is_not_ours() -> None:
    assert ownerships("https://notvenomdental.co.kr/implant") == [CitationOwnership.THIRD_PARTY]


def test_a_redirect_wrapper_is_unwrapped_before_the_decision() -> None:
    wrapped = "https://www.google.com/url?q=https%3A%2F%2Fvenomdental.co.kr%2Fimplant&sa=U"
    match = match_citations((wrapped,), BRAND)[0]
    assert match.ownership is CitationOwnership.OWN
    assert match.unwrapped_from == wrapped
    assert "venomdental.co.kr" in match.canonical_url


def test_tracking_parameters_do_not_change_ownership() -> None:
    tracked = "https://venomdental.co.kr/implant?utm_source=chatgpt.com&utm_medium=referral"
    assert ownerships(tracked) == [CitationOwnership.OWN]


def test_an_article_about_us_on_someone_elses_site_is_not_our_citation() -> None:
    assert ownerships("https://news.example.co.kr/health/2026/venom-review") == [
        CitationOwnership.THIRD_PARTY
    ]


def test_an_unresolvable_shortener_is_admitted_not_guessed() -> None:
    match = match_citations(("https://bit.ly/3xYzAbc",), BRAND)[0]
    assert match.ownership is CitationOwnership.UNRESOLVED
    assert match.reason_ko


def test_a_path_scoped_rule_claims_only_our_own_blog() -> None:
    profile = BrandProfile(
        entity_key="venom-dental",
        display_name="베놈치과",
        own_domains=("blog.naver.com/venomdental",),
    )
    assert ownerships("https://blog.naver.com/venomdental/223", profile=profile) == [
        CitationOwnership.OWN
    ]
    assert ownerships("https://blog.naver.com/someoneelse/9", profile=profile) == [
        CitationOwnership.THIRD_PARTY
    ]


def test_declaring_a_shared_platform_without_a_path_is_refused() -> None:
    # blog.naver.com holds millions of blogs. Honouring it as "ours" would credit the
    # customer with every citation the platform ever receives.
    profile = BrandProfile(
        entity_key="venom-dental", display_name="베놈치과", own_domains=("blog.naver.com",)
    )
    with pytest.raises(ValueError, match="플랫폼"):
        match_citations(("https://blog.naver.com/anyone",), profile)


def test_declaring_a_public_suffix_is_refused() -> None:
    profile = BrandProfile(
        entity_key="venom-dental", display_name="베놈치과", own_domains=("co.kr",)
    )
    with pytest.raises(ValueError):
        match_citations(("https://anything.co.kr/",), profile)


def test_a_malformed_url_is_recorded_not_raised() -> None:
    match = match_citations(("http://exa mple.com/x",), BRAND)[0]
    assert match.ownership is CitationOwnership.UNRESOLVED
    assert match.reason_ko


def test_position_follows_the_order_the_engine_gave() -> None:
    matches = match_citations(
        ("https://a.example.com/1", "https://venomdental.co.kr/2"), BRAND
    )
    assert [item.position for item in matches] == [0, 1]
    assert matches[1].ownership is CitationOwnership.OWN


def test_registrable_domain_handles_the_korean_second_level_suffixes() -> None:
    assert registrable_domain("blog.venomdental.co.kr") == "venomdental.co.kr"
    assert registrable_domain("news.example.com") == "example.com"


def test_matching_is_deterministic() -> None:
    urls = ("https://blog.venomdental.co.kr/a", "https://bit.ly/x", "https://n.example.com/b")
    first = match_citations(urls, BRAND)
    for _ in range(5):
        assert match_citations(urls, BRAND) == first
