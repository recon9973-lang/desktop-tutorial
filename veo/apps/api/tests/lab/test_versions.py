"""The DRAFT -> REVIEW -> APPROVED -> PUBLISHED -> RETIRED state machine.

Every legal transition is exercised, and every transition that is *not* in the table is
exercised too — a state machine that only ever sees its happy path is a lookup table with
extra steps.
"""

from __future__ import annotations

import itertools

import pytest

from veo.lab import versions
from veo.lab.errors import ChecksumMismatchError, IllegalTransitionError, ImmutableVersionError
from veo.scoring import SpecStatus, compute_checksum

LEGAL_PAIRS = [
    (SpecStatus.DRAFT, SpecStatus.REVIEW),
    (SpecStatus.REVIEW, SpecStatus.APPROVED),
    (SpecStatus.REVIEW, SpecStatus.DRAFT),
    (SpecStatus.APPROVED, SpecStatus.PUBLISHED),
    (SpecStatus.APPROVED, SpecStatus.DRAFT),
    (SpecStatus.PUBLISHED, SpecStatus.RETIRED),
]

ALL_PAIRS = list(itertools.product(SpecStatus, repeat=2))
ILLEGAL_PAIRS = [pair for pair in ALL_PAIRS if pair not in LEGAL_PAIRS]


def _has_hangul(text: str) -> bool:
    return any("가" <= character <= "힣" for character in text)


@pytest.mark.parametrize(("current", "target"), LEGAL_PAIRS)
def test_legal_transition_is_allowed(current: SpecStatus, target: SpecStatus) -> None:
    versions.assert_transition(current, target)
    assert versions.is_legal_transition(current, target)
    assert target in versions.next_statuses(current)


@pytest.mark.parametrize(("current", "target"), ILLEGAL_PAIRS)
def test_illegal_transition_is_rejected_in_korean(
    current: SpecStatus, target: SpecStatus
) -> None:
    assert not versions.is_legal_transition(current, target)
    with pytest.raises(IllegalTransitionError) as caught:
        versions.assert_transition(current, target)
    message = caught.value.message_ko
    assert _has_hangul(message), message
    assert current.value in message and target.value in message


def test_the_transition_table_names_every_status() -> None:
    assert set(versions.LEGAL_TRANSITIONS) == set(SpecStatus)
    assert versions.next_statuses(SpecStatus.RETIRED) == ()


def test_retired_is_the_only_terminal_status() -> None:
    terminal = [s for s in SpecStatus if not versions.next_statuses(s)]
    assert terminal == [SpecStatus.RETIRED]


@pytest.mark.parametrize("status", [SpecStatus.DRAFT])
def test_specification_is_editable_only_in_draft(status: SpecStatus) -> None:
    versions.assert_specification_editable(status)


@pytest.mark.parametrize(
    "status",
    [SpecStatus.REVIEW, SpecStatus.APPROVED, SpecStatus.PUBLISHED, SpecStatus.RETIRED],
)
def test_specification_edit_is_refused_outside_draft(status: SpecStatus) -> None:
    with pytest.raises(ImmutableVersionError) as caught:
        versions.assert_specification_editable(status)
    assert _has_hangul(caught.value.message_ko)
    assert status.value in caught.value.message_ko


@pytest.mark.parametrize(
    "status", [SpecStatus.DRAFT, SpecStatus.REVIEW, SpecStatus.APPROVED]
)
def test_pre_publication_rows_accept_workflow_writes(status: SpecStatus) -> None:
    versions.assert_row_writable(status)


@pytest.mark.parametrize("status", [SpecStatus.PUBLISHED, SpecStatus.RETIRED])
def test_published_and_retired_rows_refuse_every_write(status: SpecStatus) -> None:
    with pytest.raises(ImmutableVersionError) as caught:
        versions.assert_row_writable(status)
    assert status.value in caught.value.message_ko
    assert _has_hangul(caught.value.message_ko)


def test_immutable_statuses_are_exactly_published_and_retired() -> None:
    assert set(versions.IMMUTABLE_STATUSES) == {SpecStatus.PUBLISHED, SpecStatus.RETIRED}


def test_parse_status_rejects_an_unknown_value_in_korean() -> None:
    assert versions.parse_status("DRAFT") is SpecStatus.DRAFT
    with pytest.raises(ValueError) as caught:
        versions.parse_status("ARCHIVED")
    assert _has_hangul(str(caught.value))


def test_status_labels_are_korean_and_complete() -> None:
    assert set(versions.STATUS_LABELS_KO) == set(SpecStatus)
    for label in versions.STATUS_LABELS_KO.values():
        assert _has_hangul(label)


# --------------------------------------------------------------------------- #
# Checksum integrity
# --------------------------------------------------------------------------- #


def test_matching_checksum_passes() -> None:
    document = {"spec_id": "veo.lab_test.readiness", "version": "1.0.0"}
    versions.verify_checksum(
        specification=document,
        checksum=compute_checksum(document),
        spec_id="veo.lab_test.readiness",
        semantic_version="1.0.0",
    )


def test_a_tampered_specification_is_refused_not_repaired() -> None:
    document = {"spec_id": "veo.lab_test.readiness", "version": "1.0.0"}
    recorded = compute_checksum(document)
    tampered = {**document, "version": "1.0.1"}

    with pytest.raises(ChecksumMismatchError) as caught:
        versions.verify_checksum(
            specification=tampered,
            checksum=recorded,
            spec_id="veo.lab_test.readiness",
            semantic_version="1.0.0",
        )

    message = caught.value.message_ko
    assert _has_hangul(message)
    assert "veo.lab_test.readiness" in message
    # The recorded checksum stays recorded; nothing here rewrites it.
    assert compute_checksum(document) == recorded
