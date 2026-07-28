"""robots.txt parsing, and the distinction the whole access category rests on.

A crawler that reads a page to answer a question now, and a crawler that harvests text
to train a model later, are different things. VEO only ever penalises the first being
turned away.
"""

from __future__ import annotations

import pytest

from veo.geo.robots import (
    SEARCH_PURPOSE_CRAWLERS,
    TRAINING_PURPOSE_CRAWLERS,
    parse_robots,
)

ONLY_TRAINING_BLOCKED = """
User-agent: *
Allow: /

User-agent: GPTBot
Disallow: /

User-agent: Google-Extended
Disallow: /
"""

SEARCH_BLOCKED = """
User-agent: *
Allow: /

User-agent: Googlebot
Disallow: /

User-agent: OAI-SearchBot
Disallow: /
"""

BLANKET_BLOCK = """
User-agent: *
Disallow: /
"""


def test_the_two_crawler_families_do_not_overlap() -> None:
    assert not SEARCH_PURPOSE_CRAWLERS & TRAINING_PURPOSE_CRAWLERS


def test_known_search_crawlers_are_recognised() -> None:
    assert "googlebot" in SEARCH_PURPOSE_CRAWLERS
    assert "oai-searchbot" in SEARCH_PURPOSE_CRAWLERS
    assert "perplexitybot" in SEARCH_PURPOSE_CRAWLERS
    assert "yeti" in SEARCH_PURPOSE_CRAWLERS


def test_known_training_crawlers_are_recognised() -> None:
    assert "gptbot" in TRAINING_PURPOSE_CRAWLERS
    assert "google-extended" in TRAINING_PURPOSE_CRAWLERS
    assert "ccbot" in TRAINING_PURPOSE_CRAWLERS


def test_blocking_training_crawlers_leaves_search_crawlers_allowed() -> None:
    policy = parse_robots(ONLY_TRAINING_BLOCKED)
    assert policy.blocked_search_agents("/") == ()
    assert set(policy.blocked_training_agents("/")) == {"gptbot", "google-extended"}


def test_blocking_search_crawlers_is_reported() -> None:
    policy = parse_robots(SEARCH_BLOCKED)
    assert set(policy.blocked_search_agents("/")) == {"googlebot", "oai-searchbot"}


def test_a_blanket_disallow_blocks_every_search_crawler() -> None:
    policy = parse_robots(BLANKET_BLOCK)
    assert set(policy.blocked_search_agents("/")) == set(SEARCH_PURPOSE_CRAWLERS)


def test_a_specific_group_overrides_the_wildcard() -> None:
    policy = parse_robots("User-agent: *\nDisallow: /\n\nUser-agent: Googlebot\nAllow: /\n")
    assert "googlebot" not in policy.blocked_search_agents("/")


def test_longest_matching_rule_wins() -> None:
    policy = parse_robots("User-agent: *\nDisallow: /private\nAllow: /private/public\n")
    assert policy.is_disallowed("googlebot", "/private/secret")
    assert not policy.is_disallowed("googlebot", "/private/public/page")


def test_a_training_policy_is_declared_when_any_training_agent_is_named() -> None:
    assert parse_robots(ONLY_TRAINING_BLOCKED).declares_training_policy()
    assert not parse_robots("User-agent: *\nAllow: /\n").declares_training_policy()


def test_allowing_a_training_crawler_explicitly_also_counts_as_a_declaration() -> None:
    policy = parse_robots("User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nAllow: /\n")
    assert policy.declares_training_policy()
    assert policy.blocked_training_agents("/") == ()


def test_an_empty_robots_file_allows_everything() -> None:
    policy = parse_robots("")
    assert policy.blocked_search_agents("/") == ()
    assert not policy.declares_training_policy()


@pytest.mark.parametrize("line", ["Sitemap: https://example.com/sitemap.xml", "# comment"])
def test_non_rule_lines_are_ignored(line: str) -> None:
    policy = parse_robots(f"User-agent: *\nAllow: /\n{line}\n")
    assert policy.blocked_search_agents("/") == ()
