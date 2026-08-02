"""한도 경보 — 넘고 나서 알면 그날은 이미 늦었다 (#45 의 남은 절반).

화면(`/console/usage`)은 사람이 봐야 알고, 한도는 사람이 안 볼 때 넘는다. 그래서
경보는 **기록하는 순간** 나간다 — 한도는 호출이 있을 때만 넘을 수 있으므로,
스케줄러 없이 기록 지점 하나면 모든 경로(콘솔·공개 진단)가 덮인다.

## 왜 "경계 통과" 인가

매 기록마다 "80% 넘음" 을 알리면 80% 이후의 모든 진단이 알림을 쏜다 — 받는 사람이
채널을 끄고, 그날부터 알림은 없는 기능이 된다. 하루 호출 수는 단조 증가하므로
어떤 경계든 **딱 한 번** 통과한다. 통과한 그 기록만 알린다. 별도의 "보냈음" 저장이
필요 없고, 프로세스가 여럿이어도 경계를 가르는 기록은 하나다(정확히 그 사이에 두
기록이 동시에 끼는 극단에서 중복 1회가 가능하지만, 경보가 한 번 더 오는 쪽이 한 번도
안 오는 쪽보다 낫다).

문턱 값은 화면과 같은 곳(quota.WARN_RATIO)에서 읽는다 — 화면은 80% 에 노랗게
되는데 알림은 다른 비율에서 울리면, 둘 중 하나는 거짓말이 된다(같은 값 두 곳 금지).
"""

from __future__ import annotations

import logging
import math

from sqlalchemy.orm import Session

from veo.notify import send_alert
from veo.usage.quota import PAGESPEED_DAILY_QUOTA, WARN_RATIO, pagespeed_quota

__all__ = ["crossed_thresholds", "maybe_alert_pagespeed_quota"]

_log = logging.getLogger(__name__)


def crossed_thresholds(
    *, before: int, after: int, quota: int = PAGESPEED_DAILY_QUOTA
) -> list[str]:
    """이 기록이 통과한 경계들. 순수 함수 — 시험이 통신 없이 셈만 본다."""
    if quota <= 0 or after <= before:
        return []
    crossed: list[str] = []
    warn_at = math.ceil(quota * WARN_RATIO)
    if before < warn_at <= after:
        crossed.append("WARNING")
    if before < quota <= after:
        crossed.append("EXCEEDED")
    return crossed


def maybe_alert_pagespeed_quota(db: Session, *, recorded: int) -> None:
    """방금 ``recorded`` 건을 기록한 결과 경계를 넘었으면 알린다.

    실패해도 예외를 올리지 않는다 — 경보 때문에 기록·진단이 죽으면 안 된다.
    """
    if recorded <= 0:
        return
    try:
        usage = pagespeed_quota(db)
        after = usage.calls_today
        before = after - recorded
        for threshold in crossed_thresholds(
            before=before, after=after, quota=usage.daily_quota
        ):
            if threshold == "EXCEEDED":
                title = "PageSpeed 하루 한도를 넘었습니다"
                body = (
                    f"오늘(UTC) {after:,}회 — 한도 {usage.daily_quota:,}회를 넘었습니다. "
                    "지금부터 그날의 모든 진단에서 성능 항목이 측정 불가로 나옵니다. "
                    "한도는 태평양 시간 자정에 초기화됩니다."
                )
            else:
                title = "PageSpeed 하루 한도 80% 도달"
                body = (
                    f"오늘(UTC) {after:,}회 / 한도 {usage.daily_quota:,}회 — "
                    f"남은 호출 {usage.remaining:,}회, 남은 진단 여력 약 "
                    f"{usage.remaining // 5:,}회분입니다. /console/usage 에서 어느 "
                    "조직이 썼는지 확인할 수 있습니다."
                )
            send_alert(title_ko=title, body_ko=body, source="usage.pagespeed_quota")
    except Exception:
        _log.exception("한도 경보 판단에 실패했습니다. 기록은 그대로 유지합니다.")
