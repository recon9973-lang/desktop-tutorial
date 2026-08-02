"""한도 경보 — 딱 한 번, 경계를 가르는 그 기록에서만 (#45).

셈(crossed_thresholds)은 순수 함수로 시험한다. 80% 문턱은 화면(is_warning)과 같은
상수(WARN_RATIO)에서 오므로, 화면과 알림이 다른 비율에서 울릴 수 없다.
"""

from __future__ import annotations

import math

import pytest

from veo.usage.alerts import crossed_thresholds, maybe_alert_pagespeed_quota
from veo.usage.quota import PAGESPEED_DAILY_QUOTA, WARN_RATIO

WARN_AT = math.ceil(PAGESPEED_DAILY_QUOTA * WARN_RATIO)


class TestCrossingArithmetic:
    def test_the_record_that_crosses_80_percent_fires_once(self) -> None:
        assert crossed_thresholds(before=WARN_AT - 1, after=WARN_AT) == ["WARNING"]

    def test_records_before_and_after_the_boundary_stay_silent(self) -> None:
        """80% 이후의 모든 기록이 울리면 받는 사람이 채널을 끈다 — 그날부터 알림은
        없는 기능이 된다."""
        assert crossed_thresholds(before=WARN_AT - 2, after=WARN_AT - 1) == []
        assert crossed_thresholds(before=WARN_AT, after=WARN_AT + 1) == []

    def test_the_record_that_exhausts_the_quota_fires_exceeded(self) -> None:
        assert crossed_thresholds(
            before=PAGESPEED_DAILY_QUOTA - 1, after=PAGESPEED_DAILY_QUOTA
        ) == ["EXCEEDED"]

    def test_one_big_record_can_cross_both_boundaries(self) -> None:
        assert crossed_thresholds(before=WARN_AT - 1, after=PAGESPEED_DAILY_QUOTA) == [
            "WARNING",
            "EXCEEDED",
        ]

    def test_nothing_recorded_means_nothing_crossed(self) -> None:
        assert crossed_thresholds(before=5, after=5) == []
        assert crossed_thresholds(before=5, after=4) == []

    def test_a_zero_quota_never_divides_or_fires(self) -> None:
        assert crossed_thresholds(before=0, after=10, quota=0) == []


class TestTheDbWrapper:
    def test_a_crossing_sends_and_a_plateau_does_not(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import veo.usage.alerts as alerts

        sent: list[str] = []

        class FakeUsage:
            calls_today = WARN_AT
            daily_quota = PAGESPEED_DAILY_QUOTA
            remaining = PAGESPEED_DAILY_QUOTA - WARN_AT

        monkeypatch.setattr(alerts, "pagespeed_quota", lambda db: FakeUsage())
        monkeypatch.setattr(
            alerts,
            "send_alert",
            lambda **kwargs: sent.append(kwargs["title_ko"]),
        )

        # calls_today=WARN_AT 이고 방금 1건 기록 → before=WARN_AT-1 → 경계 통과.
        maybe_alert_pagespeed_quota(object(), recorded=1)  # type: ignore[arg-type]
        assert len(sent) == 1 and "80%" in sent[0]

        # 같은 상태에서 0건 기록 → 아무 일도 없다.
        maybe_alert_pagespeed_quota(object(), recorded=0)  # type: ignore[arg-type]
        assert len(sent) == 1

    def test_a_broken_quota_query_never_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """경보 때문에 기록·진단이 죽으면 안 된다 — 삼키고 로그에 남긴다."""
        import veo.usage.alerts as alerts

        def explode(db):  # type: ignore[no-untyped-def]
            raise RuntimeError("데이터베이스가 없다")

        monkeypatch.setattr(alerts, "pagespeed_quota", explode)
        maybe_alert_pagespeed_quota(object(), recorded=3)  # type: ignore[arg-type]
