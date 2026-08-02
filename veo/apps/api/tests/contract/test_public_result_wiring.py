"""공유 결과 저장소 배선 — 격리 불변식의 반대편 절반 (usage recorder 와 같은 계열).

격리 시험은 공개 패키지에 DB 가 없음을 지키고, 이 시험은 그래도 공유 링크가
재시작을 견딘다는 것을 지킨다. 둘 중 하나만 있으면 반쪽이다: 격리만 지키면 재배포가
발급된 링크를 전부 죽이고, 저장만 지키면 익명 표면이 고객 데이터에 닿는 문이 열린다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.api.app import build_public_result_store, create_app
from veo.api.public_result_store import DbPublicResultStore
from veo.public.router import get_result_store
from veo.public.schemas import PublicScoreBlock, PublicSeoScanPayload
from veo.public.service import StoredPublicResult


def payload(token: str) -> PublicSeoScanPayload:
    return PublicSeoScanPayload(
        target_url="https://clinic.example/",
        scanned_url_count=1,
        summary_ko="요약",
        score=PublicScoreBlock(
            spec_id="veo.seo.readiness",
            spec_version="1.0.0",
            spec_checksum="abc",
            status="SCORED",
            score=42.0,
            band_id="warn",
            band_label_ko="주의",
            coverage=0.8,
            confidence=0.9,
        ),
        result_token=token,
        result_expires_at=datetime(2026, 8, 10, tzinfo=UTC),
    )


def stored(token: str) -> StoredPublicResult:
    return StoredPublicResult(
        fingerprint="fp-1",
        payload=payload(token),
        expires_at=datetime(2026, 8, 10, tzinfo=UTC),
    )


def test_the_app_injects_a_db_backed_result_store() -> None:
    app = create_app()
    assert app.dependency_overrides.get(get_result_store) is build_public_result_store


def test_put_swallows_storage_failure() -> None:
    """저장 실패가 이미 완성된 진단 응답을 죽여서는 안 된다 — 로그로만 남는다."""

    def broken_scope():  # type: ignore[no-untyped-def]
        raise RuntimeError("데이터베이스가 없다")

    store = DbPublicResultStore(scope=broken_scope)
    store.put(stored("any"))  # 예외가 밖으로 나오면 이 시험이 그 예외로 죽는다.


def test_get_does_not_swallow_storage_failure() -> None:
    """읽기 실패가 '만료되었습니다' 로 위장하면 링크를 받은 사람에게 거짓말이 된다."""

    def broken_scope():  # type: ignore[no-untyped-def]
        raise RuntimeError("데이터베이스가 없다")

    store = DbPublicResultStore(scope=broken_scope)
    with pytest.raises(RuntimeError):
        store.get("fp-1", now=datetime(2026, 8, 3, tzinfo=UTC))


def test_put_strips_the_raw_token_from_the_stored_payload() -> None:
    """행의 키가 지문인 이유와 같은 이유 — DB 에서 공유 주소를 복원할 수 없어야 한다."""
    captured: list[object] = []

    class Recorder:
        def merge(self, row: object) -> None:
            captured.append(row)

        def __enter__(self) -> Recorder:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    store = DbPublicResultStore(scope=Recorder)  # type: ignore[arg-type]
    store.put(stored("raw-token-must-not-be-stored"))

    assert len(captured) == 1
    row_payload = captured[0].payload  # type: ignore[attr-defined]
    assert row_payload["result_token"] == ""
    assert "raw-token-must-not-be-stored" not in str(row_payload)
