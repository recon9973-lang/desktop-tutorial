"""Scrubbing secrets out of anything on its way to a log or an error message."""

from __future__ import annotations

import pytest

from veo.credentials.redaction import REDACTED, redact, redact_exception, redact_mapping

SECRET = "test-secret-not-a-real-key"


def test_none_and_empty_are_safe() -> None:
    assert redact(None) == ""
    assert redact("") == ""


def test_a_known_value_is_removed_even_when_it_looks_ordinary() -> None:
    message = f"provider rejected {SECRET} at 09:00"
    scrubbed = redact(message, known_values=[SECRET])
    assert SECRET not in scrubbed
    assert REDACTED in scrubbed
    assert "provider rejected" in scrubbed


def test_a_known_value_is_removed_wherever_it_appears() -> None:
    message = f"{SECRET}/{SECRET}?x={SECRET}"
    assert SECRET not in redact(message, known_values=[SECRET])


def test_overlapping_known_values_are_fully_removed() -> None:
    scrubbed = redact(f"{SECRET}-extra", known_values=[SECRET, f"{SECRET}-extra"])
    assert SECRET not in scrubbed


def test_blank_known_values_do_not_shred_the_message() -> None:
    assert redact("hello", known_values=["", "  ", None]) == "hello"  # type: ignore[list-item]


@pytest.mark.parametrize(
    "message",
    [
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJlX3Rlc3Q",
        "x-api-key: abcdefghijklmnopqrstuvwx",
        "api_key=abcdefghijklmnopqrstuvwx&next=1",
        "client_secret: abcdefghijklmnopqrstuvwx",
        "password = abcdefghijklmnop",
        "https://user:abcdefghijklmnop@example.com/path",
        "https://example.com/v1?token=abcdefghijklmnopqrstuvwx",
        "AKIAIOSFODNN7EXAMPLE",
        "sk-abcdefghijklmnopqrstuvwxyz012345",
        "0123456789abcdef0123456789abcdef0123456789abcdef",
    ],
)
def test_secret_shaped_patterns_are_scrubbed(message: str) -> None:
    scrubbed = redact(message)
    assert REDACTED in scrubbed
    # The high-entropy part must be gone, not merely shortened.
    for token in ("abcdefghijklmnopqrstuvwx", "AKIAIOSFODNN7EXAMPLE", "abcdefghijklmnop"):
        assert token not in scrubbed


def test_ordinary_text_survives() -> None:
    message = "네이버 검색광고 자격증명이 설정되지 않았습니다."
    assert redact(message) == message


def test_output_is_length_bounded() -> None:
    scrubbed = redact("a" * 100_000)
    assert len(scrubbed) <= 4_200


def test_redaction_is_idempotent() -> None:
    once = redact(f"token={SECRET}", known_values=[SECRET])
    assert redact(once, known_values=[SECRET]) == once


def test_exceptions_are_scrubbed_and_never_reveal_their_payload() -> None:
    exc = RuntimeError(f"401 for key {SECRET}")
    scrubbed = redact_exception(exc, known_values=[SECRET])
    assert SECRET not in scrubbed
    assert "RuntimeError" in scrubbed


def test_exception_chain_is_scrubbed() -> None:
    try:
        try:
            raise ValueError(SECRET)
        except ValueError as inner:
            raise RuntimeError("wrapped") from inner
    except RuntimeError as outer:
        scrubbed = redact_exception(outer, known_values=[SECRET])
    assert SECRET not in scrubbed


def test_mappings_are_scrubbed_by_key_and_by_value() -> None:
    scrubbed = redact_mapping(
        {"provider": "OPENAI", "api_key": SECRET, "note": f"used {SECRET}"},
        known_values=[SECRET],
    )
    assert scrubbed["provider"] == "OPENAI"
    assert SECRET not in str(scrubbed)
    assert scrubbed["api_key"] == REDACTED


# --------------------------------------------------------------------------- #
# Quoted values — the shape a traceback actually produces
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "line",
    [
        "password='hunter2xyzq'",
        'password="hunter2xyzq"',
        "{'api_key': 'naver-customer-1234567'}",
        '{"api_key": "naver-customer-1234567"}',
        "client_secret='abcd1234efgh5678'",
        "Settings(token='abcd1234efgh5678', provider='NAVER')",
    ],
    ids=["single", "double", "repr-dict", "json-dict", "assignment", "repr-object"],
)
def test_a_quoted_secret_is_scrubbed_whichever_quote_was_used(line: str) -> None:
    """Single quotes are not a stylistic variant here — they are what ``repr()`` writes.

    A traceback, an ``!r`` format field and a dumped settings object all render strings
    with single quotes, so a pattern that only recognised double quotes scrubbed the JSON
    payload and left the traceback untouched. The traceback is the likeliest place a
    credential ever meets a log.
    """
    scrubbed = redact(line)
    assert REDACTED in scrubbed
    assert "hunter2xyzq" not in scrubbed
    assert "naver-customer-1234567" not in scrubbed
    assert "abcd1234efgh5678" not in scrubbed


def test_the_quotes_themselves_survive_so_the_line_stays_readable() -> None:
    assert redact("password='hunter2xyzq'") == f"password='{REDACTED}'"


def test_an_ordinary_quoted_string_is_left_alone() -> None:
    """Redaction must not eat text that merely sits next to a quote."""
    line = "clinic_name='서울온담의원' status='ACTIVE'"
    assert redact(line) == line
