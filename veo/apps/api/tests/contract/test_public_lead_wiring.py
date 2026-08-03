"""리드 저장소 배선 (E2) — 방문자의 연락처가 재시작을 견딘다.

격리 시험은 공개 패키지에 DB 가 없음을 지키고, 이 시험은 그래도 리드가 재시작을
견딘다는 것을 지킨다. 실패 방향이 공유 결과와 **반대**라는 것도 여기서 고정한다:
저장하지 못했으면서 "저장했습니다" 라고 답하는 것이 최악의 거짓이므로, 리드의
쓰기 실패는 삼키지 않고 던진다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from veo.api.app import build_lead_store, create_app
from veo.api.public_lead_store import DbLeadStore
from veo.public.leads import StoredLead
from veo.public.router import get_lead_store


def lead() -> StoredLead:
    return StoredLead(
        lead_id=uuid.uuid4(),
        received_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
        name="김원장",
        phone="010-0000-0000",
    )


def test_the_app_injects_a_db_backed_lead_store() -> None:
    app = create_app()
    assert app.dependency_overrides.get(get_lead_store) is build_lead_store


def test_add_does_not_swallow_storage_failure() -> None:
    """저장 실패가 '저장했습니다' 로 위장하면, 연락을 기다리는 사람이 속는다."""

    def broken_scope():  # type: ignore[no-untyped-def]
        raise RuntimeError("데이터베이스가 없다")

    store = DbLeadStore(scope=broken_scope)
    with pytest.raises(RuntimeError):
        store.add(lead())


def test_add_writes_the_five_fields_and_no_sixth() -> None:
    captured: list[object] = []

    class Recorder:
        def add(self, row: object) -> None:
            captured.append(row)

        def __enter__(self) -> Recorder:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    store = DbLeadStore(scope=Recorder)  # type: ignore[arg-type]
    one = lead()
    store.add(one)

    assert len(captured) == 1
    row = captured[0]
    assert row.name == "김원장"  # type: ignore[attr-defined]
    assert row.phone == "010-0000-0000"  # type: ignore[attr-defined]
    assert row.email is None  # type: ignore[attr-defined]
    assert row.site_url is None  # type: ignore[attr-defined]
    assert row.lead_id == one.lead_id  # type: ignore[attr-defined]
