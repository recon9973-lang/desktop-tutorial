"""사용량 기록 — 한도까지 얼마나 남았는가.

`api_usage_events` 테이블은 처음부터 있었지만 **쓰는 코드가 하나도 없었다.** 진단이
외부 API 를 부르지 않던 동안에는 빈 것이 정상이었고, 2026-08-01 에 PageSpeed 배선이
들어가면서 결함이 됐다.

여기서 세는 것은 돈이 아니라 **횟수**다. PageSpeed 는 하루 25,000회까지 무료이고 돈은
들지 않지만, 넘기면 그날의 모든 고객 진단에서 성능이 측정 불가가 된다. 진단 한 번에
최대 5회가 나가므로 이론상 하루 5,000회 진단이 한계다.

이 파일은 **우리가 만드는 행**을 본다. SQLAlchemy 가 그 행을 잘 저장하는지는 여기서
확인하지 않는다 — 그것은 DB 가 필요한 시험이고 `requires_postgres` 로 따로 있다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from veo.seo.measure_performance import CallRecord
from veo.usage import record_pagespeed_calls

ORG = uuid.uuid4()
REQUESTED_AT = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


class FakeSession:
    """`add_all` 로 들어온 것을 붙잡아 둔다. 실패를 흉내 낼 수도 있다."""

    def __init__(self, *, explode: bool = False) -> None:
        self.rows: list[object] = []
        self.flushed = False
        self.rolled_back = False
        self._explode = explode

    def add_all(self, rows) -> None:  # type: ignore[no-untyped-def]
        if self._explode:
            raise RuntimeError("연결이 끊겼습니다")
        self.rows.extend(rows)

    def flush(self) -> None:
        self.flushed = True

    def rollback(self) -> None:
        self.rolled_back = True


def call(url: str, *, ok: bool = True, analysed_at: str | None = None) -> CallRecord:
    return CallRecord(
        url=url,
        latency_ms=24_000,
        succeeded=ok,
        failure_code=None if ok else "PROVIDER_UNAVAILABLE",
        analysed_at=analysed_at,
        requested_at=REQUESTED_AT,
    )


class TestOneRowPerCall:
    def test_every_call_becomes_a_row(self) -> None:
        db = FakeSession()
        written = record_pagespeed_calls(
            db, [call("https://a/"), call("https://b/")], organization_id=ORG
        )

        assert written == 2
        assert len(db.rows) == 2

    def test_a_failed_call_is_recorded_too(self) -> None:
        """실패해도 요청은 나갔고 한도를 썼다.

        빼면 남은 한도를 실제보다 많게 세고, 어느 날 갑자기 모든 고객의 성능이
        측정 불가가 된다.
        """
        db = FakeSession()
        assert record_pagespeed_calls(db, [call("https://a/", ok=False)]) == 1

    def test_nothing_to_record_touches_nothing(self) -> None:
        db = FakeSession()
        assert record_pagespeed_calls(db, []) == 0
        assert db.flushed is False


class TestTheRowSaysWhatWeActuallyKnow:
    def test_the_organization_is_carried_so_usage_can_be_split(self) -> None:
        """조직마다 얼마나 썼는지 나뉘지 않으면 한 고객이 한도를 태워도 알 수 없다."""
        db = FakeSession()
        record_pagespeed_calls(db, [call("https://a/")], organization_id=ORG)

        assert db.rows[0].organization_id == ORG  # type: ignore[attr-defined]

    def test_the_provider_and_operation_use_googles_own_names(self) -> None:
        """우리가 지어낸 이름은 나중에 구글 문서에서 찾을 수 없다."""
        db = FakeSession()
        record_pagespeed_calls(db, [call("https://a/")])

        assert db.rows[0].provider == "GOOGLE_PAGESPEED"  # type: ignore[attr-defined]
        assert db.rows[0].operation == "runPagespeed"  # type: ignore[attr-defined]

    def test_a_free_call_costs_zero_not_unknown(self) -> None:
        """0 과 None 을 섞으면 "공짜라서 0" 과 "몰라서 0" 이 같은 자리에 앉는다.

        PageSpeed 는 한도 안에서 정말 0원이다. 값을 모르는 제공자를 나중에 붙일 때는
        None 으로 둔다.
        """
        db = FakeSession()
        record_pagespeed_calls(db, [call("https://a/")])

        assert db.rows[0].cost_krw == 0.0  # type: ignore[attr-defined]

    def test_the_status_code_is_left_empty_rather_than_invented(self) -> None:
        """어댑터가 이미 분류해 오류 코드로 바꿔 주므로 우리는 상태 코드를 못 본다."""
        db = FakeSession()
        record_pagespeed_calls(db, [call("https://a/")])

        assert db.rows[0].status_code is None  # type: ignore[attr-defined]

    def test_a_cache_hit_is_recorded_when_google_told_us(self) -> None:
        """분석 시각이 우리 요청보다 앞서면 새로 돌린 것이 아니다 — 관측이지 추론이 아니다."""
        db = FakeSession()
        record_pagespeed_calls(
            db, [call("https://a/", analysed_at="2026-08-01T11:00:00Z")]
        )

        assert db.rows[0].was_cache_hit is True  # type: ignore[attr-defined]


class TestRecordingNeverBreaksTheScan:
    def test_a_write_failure_does_not_raise(self) -> None:
        """진단은 이미 끝났고 그 결과는 옳다. 기록 때문에 버리면 안 된다."""
        db = FakeSession(explode=True)

        assert record_pagespeed_calls(db, [call("https://a/")]) == 0
        assert db.rolled_back is True

    def test_a_write_failure_is_logged_rather_than_swallowed(self, caplog) -> None:  # type: ignore[no-untyped-def]
        """조용히 사라지면 기록이 비어 있는 이유를 아무도 모른다."""
        db = FakeSession(explode=True)
        with caplog.at_level("ERROR"):
            record_pagespeed_calls(db, [call("https://a/")])

        assert any("사용량 기록에 실패" in record.message for record in caplog.records)
