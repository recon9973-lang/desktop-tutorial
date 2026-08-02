"""공개 진단의 사용량 기록 배선 — 격리 불변식의 반대편 절반.

공개 패키지는 DB 를 임포트하지 못한다(tests/public/test_isolation.py). 그래서 무료
진단이 쓴 PageSpeed 호출을 장부에 적는 구현은 조립 지점(veo.api.app)이 의존성
덮어쓰기로 주입한다. 이 파일이 지키는 것은 그 주입이 **실제로 걸려 있다**는 사실이다
— 격리 시험은 공개 쪽에 DB 가 없음을 지키고, 이 시험은 그래도 기록은 된다는 것을
지킨다. 둘 중 하나만 있으면 반쪽이다: 격리만 지키면 무료 트래픽이 소모한 한도가
보이지 않게 되고, 기록만 지키면 익명 표면이 고객 데이터에 닿는 문을 다시 연다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from veo.api.app import build_public_usage_recorder, create_app
from veo.public.router import get_usage_recorder
from veo.seo.measure_performance import CallRecord


def test_the_app_injects_a_db_backed_usage_recorder() -> None:
    app = create_app()
    assert app.dependency_overrides.get(get_usage_recorder) is build_public_usage_recorder


def test_the_recorder_swallows_storage_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """기록 실패가 이미 완성된 진단 응답을 죽여서는 안 된다."""

    def broken_scope():  # type: ignore[no-untyped-def]
        raise RuntimeError("데이터베이스가 없다")

    import veo.db.session as db_session

    monkeypatch.setattr(db_session, "session_scope", broken_scope)

    record = build_public_usage_recorder(request_id=str(uuid.uuid4()))
    call = CallRecord(
        url="https://clinic.example/",
        latency_ms=24_000,
        succeeded=True,
        failure_code=None,
        analysed_at=None,
        requested_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )

    record([call])  # 예외가 밖으로 나오면 이 시험이 그 예외로 죽는다.
