"""The issue fingerprint: one problem, one row, however many scans found it.

Get this wrong and recurrence tracking means nothing — the same missing canonical tag
would appear as a fresh issue every Monday and the history that says "this is the third
time" would never exist.
"""

from __future__ import annotations

import pytest

from veo.collect.contract import IssueDraft
from veo.issues.identity import (
    fingerprint_of_draft,
    issue_fingerprint,
    normalize_affected_urls,
)


def draft(check_id: str, *urls: str) -> IssueDraft:
    return IssueDraft(
        check_id=check_id,
        title_ko="제목",
        summary_ko="요약",
        affected_urls=urls,
        evidence_ids=("http_response:abc",),
        remediation_ko="조치",
        remediation_owner="DEVELOPER",
    )


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #


def test_urls_are_canonicalised_before_they_are_compared() -> None:
    normalized = normalize_affected_urls(
        ["HTTPS://Example.COM:443/a", "https://example.com/a"]
    )
    assert normalized == ("https://example.com/a",)


def test_normalisation_is_order_independent() -> None:
    first = normalize_affected_urls(["https://example.com/b", "https://example.com/a"])
    second = normalize_affected_urls(["https://example.com/a", "https://example.com/b"])
    assert first == second


def test_duplicates_collapse() -> None:
    normalized = normalize_affected_urls(
        ["https://example.com/a", "https://example.com/a", "https://example.com/a/"]
    )
    assert len(normalized) <= 2
    assert len(set(normalized)) == len(normalized)


def test_a_url_that_cannot_be_canonicalised_is_kept_verbatim() -> None:
    """Dropping it would let two different problems share one fingerprint."""
    normalized = normalize_affected_urls(["https://user:pw@example.com/a", "  "])
    assert "https://user:pw@example.com/a" in normalized
    assert "" not in normalized


def test_a_site_wide_issue_has_an_empty_url_set() -> None:
    assert normalize_affected_urls([]) == ()


# --------------------------------------------------------------------------- #
# Fingerprint
# --------------------------------------------------------------------------- #


def test_the_same_problem_in_two_scans_produces_one_fingerprint() -> None:
    monday = fingerprint_of_draft(draft("seo.canonical.declared_and_consistent", "https://e.com/a"))
    friday = fingerprint_of_draft(
        draft("seo.canonical.declared_and_consistent", "https://E.com:443/a")
    )
    assert monday == friday


def test_a_different_check_on_the_same_url_is_a_different_issue() -> None:
    left = issue_fingerprint("seo.http.status_ok", ["https://e.com/a"])
    right = issue_fingerprint("seo.robots.meta_indexable", ["https://e.com/a"])
    assert left != right


def test_a_different_url_set_is_a_different_issue() -> None:
    one = issue_fingerprint("seo.http.status_ok", ["https://e.com/a"])
    two = issue_fingerprint("seo.http.status_ok", ["https://e.com/a", "https://e.com/b"])
    assert one != two


def test_the_fingerprint_does_not_depend_on_url_order() -> None:
    forwards = issue_fingerprint("seo.http.status_ok", ["https://e.com/a", "https://e.com/b"])
    backwards = issue_fingerprint("seo.http.status_ok", ["https://e.com/b", "https://e.com/a"])
    assert forwards == backwards


def test_a_site_wide_check_still_fingerprints() -> None:
    assert issue_fingerprint("seo.robots.txt_reachable", [])


def test_the_fingerprint_is_a_stable_hex_digest() -> None:
    value = issue_fingerprint("seo.http.status_ok", ["https://e.com/a"])
    assert len(value) == 64
    assert all(character in "0123456789abcdef" for character in value)


def test_two_check_ids_cannot_be_confused_by_concatenation() -> None:
    """``ab`` + ``c`` and ``a`` + ``bc`` must not hash alike."""
    left = issue_fingerprint("ab", ["c"])
    right = issue_fingerprint("a", ["bc"])
    assert left != right


def test_an_empty_check_id_is_refused() -> None:
    with pytest.raises(ValueError, match="check_id"):
        issue_fingerprint("", ["https://e.com/a"])
