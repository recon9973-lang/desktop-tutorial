"""The scoring-version state machine, and the integrity rules that guard it.

    DRAFT -> REVIEW -> APPROVED -> PUBLISHED -> RETIRED

with two ways back: ``REVIEW -> DRAFT`` and ``APPROVED -> DRAFT``, so a reviewer can
return a candidate for rework. Everything else is refused.

Three rules are enforced here rather than left to reviewer discipline.

**A published version is immutable.** ``PUBLISHED`` and ``RETIRED`` rows accept no write
at all — not the specification, not the changelog, not a fresh golden run. The single
exception is the ``PUBLISHED -> RETIRED`` transition itself, which changes the workflow
status and nothing else. Changing a specification means creating a new version.

**The specification body is editable only in DRAFT.** Approval is approval of a specific
checksum. If the bytes could move after approval — even while the row still says
``APPROVED`` — the approval would attest to nothing. Send the candidate back to ``DRAFT``
first; that is a legal transition and it is visible.

**A checksum mismatch is a hard error.** :func:`verify_checksum` recomputes the hash of
the stored document and refuses the row when it disagrees with the recorded value. It
never rewrites the recorded value: the mismatch *is* the finding.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from veo.lab.errors import ChecksumMismatchError, IllegalTransitionError, ImmutableVersionError
from veo.scoring import SpecStatus, compute_checksum

#: The whole state machine. Every status appears as a key, including terminal ones, so
#: that a new status added to :class:`SpecStatus` fails a test rather than defaulting to
#: "no transitions allowed" and silently stranding rows.
LEGAL_TRANSITIONS: Mapping[SpecStatus, frozenset[SpecStatus]] = {
    SpecStatus.DRAFT: frozenset({SpecStatus.REVIEW}),
    SpecStatus.REVIEW: frozenset({SpecStatus.APPROVED, SpecStatus.DRAFT}),
    SpecStatus.APPROVED: frozenset({SpecStatus.PUBLISHED, SpecStatus.DRAFT}),
    SpecStatus.PUBLISHED: frozenset({SpecStatus.RETIRED}),
    SpecStatus.RETIRED: frozenset(),
}

#: Rows that accept no write of any kind.
IMMUTABLE_STATUSES: frozenset[SpecStatus] = frozenset(
    {SpecStatus.PUBLISHED, SpecStatus.RETIRED}
)

#: Statuses in which the specification document itself may still be replaced.
SPECIFICATION_EDITABLE_STATUSES: frozenset[SpecStatus] = frozenset({SpecStatus.DRAFT})

STATUS_LABELS_KO: Mapping[SpecStatus, str] = {
    SpecStatus.DRAFT: "초안",
    SpecStatus.REVIEW: "검토 중",
    SpecStatus.APPROVED: "승인됨",
    SpecStatus.PUBLISHED: "발행됨",
    SpecStatus.RETIRED: "폐기됨",
}


def parse_status(value: str) -> SpecStatus:
    """Turn a stored or requested status string into a :class:`SpecStatus`."""
    try:
        return SpecStatus(value)
    except ValueError as exc:
        known = ", ".join(status.value for status in SpecStatus)
        raise ValueError(
            f"'{value}'은(는) 알 수 없는 명세 상태입니다. 사용할 수 있는 상태: {known}"
        ) from exc


def label_ko(status: SpecStatus) -> str:
    return STATUS_LABELS_KO[status]


def next_statuses(current: SpecStatus) -> tuple[SpecStatus, ...]:
    """Legal destinations from ``current``, in the order the workflow runs them."""
    allowed = LEGAL_TRANSITIONS[current]
    order = (
        SpecStatus.REVIEW,
        SpecStatus.APPROVED,
        SpecStatus.PUBLISHED,
        SpecStatus.RETIRED,
        SpecStatus.DRAFT,
    )
    return tuple(status for status in order if status in allowed)


def is_legal_transition(current: SpecStatus, target: SpecStatus) -> bool:
    return target in LEGAL_TRANSITIONS[current]


def assert_transition(current: SpecStatus, target: SpecStatus) -> None:
    """Raise unless ``current -> target`` is in the table."""
    if is_legal_transition(current, target):
        return

    allowed = next_statuses(current)
    if allowed:
        options = ", ".join(f"{s.value}({label_ko(s)})" for s in allowed)
        tail = f"현재 상태에서 갈 수 있는 상태는 {options}뿐입니다."
    else:
        tail = f"{label_ko(current)} 상태는 더 이상 상태를 바꿀 수 없습니다."

    raise IllegalTransitionError(
        f"{current.value}({label_ko(current)}) 상태의 명세를 "
        f"{target.value}({label_ko(target)}) 상태로 바꿀 수 없습니다. {tail}"
    )


def assert_row_writable(current: SpecStatus) -> None:
    """Raise unless the row may be written to at all."""
    if current not in IMMUTABLE_STATUSES:
        return
    raise ImmutableVersionError(
        f"{current.value}({label_ko(current)}) 상태의 점수 명세는 변경할 수 없습니다. "
        "이미 발행된 점수가 이 버전과 체크섬을 근거로 삼고 있으므로, 방법론을 바꾸려면 "
        "새 버전을 만들어야 합니다."
    )


def assert_specification_editable(current: SpecStatus) -> None:
    """Raise unless the specification document itself may still be replaced."""
    if current in SPECIFICATION_EDITABLE_STATUSES:
        return
    if current in IMMUTABLE_STATUSES:
        assert_row_writable(current)
    raise ImmutableVersionError(
        f"{current.value}({label_ko(current)}) 상태에서는 명세 본문을 수정할 수 없습니다. "
        "승인은 특정 체크섬에 대한 승인이므로, 본문을 고치려면 먼저 DRAFT(초안)로 "
        "되돌려야 합니다."
    )


def verify_checksum(
    *,
    specification: Mapping[str, Any],
    checksum: str,
    spec_id: str,
    semantic_version: str,
) -> None:
    """Raise when the stored document does not hash to its recorded checksum.

    Deliberately does not return the recomputed value and deliberately does not offer to
    fix anything. A caller that could "resolve" this by taking the new hash would turn a
    detected tamper into a silent acceptance.
    """
    recomputed = compute_checksum(dict(specification))
    if recomputed == checksum:
        return
    raise ChecksumMismatchError(
        f"{spec_id}@{semantic_version}의 저장된 명세가 기록된 체크섬과 일치하지 않습니다. "
        f"기록된 값은 {checksum[:12]}…, 실제 계산값은 {recomputed[:12]}…입니다. "
        "이 버전은 사용할 수 없습니다. 체크섬을 다시 계산해 맞추지 말고, 원인을 확인한 뒤 "
        "새 버전을 만드세요."
    )
