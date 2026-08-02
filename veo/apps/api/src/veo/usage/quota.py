"""한도까지 얼마나 남았는가.

PageSpeed 는 하루 25,000회까지 무료다. **돈이 아니라 하루가 위험이다** — 넘기면 그날의
모든 고객 진단에서 성능이 측정 불가가 되고, 화면에는 사이트의 문제처럼 보이는 형태로
나타난다. 진단 한 번에 최대 5회가 나가므로 이론상 하루 5,000회 진단이 한계다.

## 세는 범위

**조직이 아니라 전체를 센다.** 한도는 API 키에 걸리고 키는 하나이므로, 한 조직이
태우면 모든 조직이 함께 막힌다. 조직별 숫자는 "누가 많이 썼나" 를 볼 때 쓰고,
"남았나" 는 전체로만 답할 수 있다.

이 구분을 흐리면 화면이 "우리 조직은 200회밖에 안 썼는데요" 라고 말하는 동안 키는
이미 막혀 있게 된다.

## 하루의 경계

구글 한도는 **태평양 시간** 자정에 초기화된다(구글 API 콘솔의 일일 할당량 규칙).
한국 시간으로 세면 초기화 시점이 어긋나 "아직 여유 있다" 고 잘못 말하게 된다.
그래서 여기서는 UTC 로 세고, 그것이 태평양 시간과도 어긋난다는 사실을 함께 돌려준다 —
정확한 경계를 아는 척하지 않는다(0-A).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from veo.db.models.analysis import APIUsageEvent

__all__ = [
    "CALLS_PER_SCAN",
    "PAGESPEED_DAILY_QUOTA",
    "WARN_RATIO",
    "QuotaUsage",
    "pagespeed_quota",
]

#: 구글이 공개한 PageSpeed Insights 무료 한도(하루). 우리가 정한 값이 아니다.
PAGESPEED_DAILY_QUOTA: Final = 25_000

#: 진단 한 번이 태우는 최대 호출 수 = 발행 명세의 ``sampling.perf_lab.max_urls``.
#: **여기서 지어낸 숫자가 아니다.** 재는 쪽(수집기)과 남은 양을 말하는 쪽(이 모듈)이
#: 각자 다른 값을 쓰면 "몇 번 더 진단할 수 있는가" 가 조용히 틀린다 — 화면은 여유가
#: 있다고 말하는데 실제로는 그전에 한도가 끝난다. 명세와 어긋나면 시험이 깨진다.
CALLS_PER_SCAN: Final = 5

#: 이 비율을 넘으면 경고한다. 넘고 나서 알면 그날은 이미 늦었다.
#: 화면(is_warning)과 경보(usage/alerts.py)가 **같은 값**을 읽는다 — 화면은 80% 에
#: 노랗게 되는데 알림은 다른 비율에서 울리면 둘 중 하나는 거짓말이 된다.
WARN_RATIO: Final = 0.8

_PROVIDER: Final = "GOOGLE_PAGESPEED"


@dataclass(frozen=True, slots=True)
class QuotaUsage:
    """오늘 얼마나 썼고 얼마나 남았는가."""

    provider: str
    #: 오늘(UTC) 나간 호출 수. 실패한 호출도 한도를 쓰므로 포함한다.
    calls_today: int
    #: 이 조직이 쓴 몫. 전체와 다를 수 있고, **남은 양을 말해 주지는 않는다.**
    calls_by_this_organization: int
    daily_quota: int
    window_start: datetime
    window_end: datetime

    @property
    def remaining(self) -> int:
        return max(0, self.daily_quota - self.calls_today)

    @property
    def used_ratio(self) -> float:
        return self.calls_today / self.daily_quota if self.daily_quota else 0.0

    @property
    def is_warning(self) -> bool:
        return self.used_ratio >= WARN_RATIO

    @property
    def is_exhausted(self) -> bool:
        return self.remaining == 0

    @property
    def scans_remaining(self) -> int:
        """남은 호출로 몇 번 더 진단할 수 있는가 — **최악의 경우로 센다.**

        진단 한 번이 항상 5회를 태우지는 않는다(페이지가 적으면 덜 쓴다). 그래도 나눗셈은
        상한으로 한다. 평균으로 세면 화면이 실제보다 많은 횟수를 약속하고, 그 약속이
        틀리는 순간은 하필 한도가 끝나는 순간이다.
        """
        return self.remaining // CALLS_PER_SCAN

    def summary_ko(self) -> str:
        """화면에 그대로 쓸 한 줄. 남은 양을 먼저 말한다."""
        if self.is_exhausted:
            return (
                f"오늘 PageSpeed 한도({self.daily_quota:,}회)를 모두 썼습니다. "
                "지금 진단하면 성능 항목이 측정 불가로 나옵니다 — 사이트의 문제가 "
                "아니라 우리 한도입니다. 내일 초기화됩니다."
            )
        if self.is_warning:
            return (
                f"오늘 {self.calls_today:,}회를 썼고 {self.remaining:,}회 남았습니다"
                f"(한도 {self.daily_quota:,}회). 진단 한 번에 최대 {CALLS_PER_SCAN}회가 "
                f"나가므로 약 {self.scans_remaining:,}회 더 진단할 수 있습니다."
            )
        return (
            f"오늘 {self.calls_today:,}회를 썼습니다. 한도 {self.daily_quota:,}회 중 "
            f"{self.remaining:,}회 남았습니다."
        )

    def remedies_ko(self) -> list[str]:
        """지금 무엇을 하면 되는가. **할 일이 없으면 빈 목록이다.**

        여유가 있을 때까지 조언을 띄우면 조언 자체가 배경이 되어, 정작 급할 때 아무도
        읽지 않는다.
        """
        if self.is_exhausted:
            return [
                "오늘 진단은 성능 항목이 빠진 채로 나옵니다. 성능이 필요한 건은 "
                "초기화 뒤로 미룹니다.",
                "고객에게는 '사이트가 느려서'가 아니라 '우리 한도를 다 써서 오늘은 "
                "재지 못했다'고 알립니다 — 그대로 두면 고객이 자기 사이트를 고치려 듭니다.",
                "이 상태가 반복되면 구글 클라우드 콘솔에서 PageSpeed Insights API "
                "한도 증설을 신청합니다.",
            ]
        if self.is_warning:
            return [
                f"남은 {self.scans_remaining:,}회는 성능이 꼭 필요한 진단에 먼저 씁니다.",
                "오늘 안에 대량 진단을 예정했다면 초기화 이후로 미루는 편이 안전합니다.",
            ]
        return []

    def caveat_ko(self) -> str:
        """이 숫자를 읽을 때 함께 알아야 하는 것."""
        return (
            "한도는 API 키 하나에 걸립니다. 아래 '이 조직이 쓴 몫' 은 참고용이며, "
            "**남은 양은 전체로만 답할 수 있습니다** — 다른 조직이 쓴 것도 같은 한도를 "
            "씁니다. 초기화 시각은 구글이 태평양 시간 자정으로 정하는데, 이 집계는 "
            "UTC 하루 기준이라 최대 몇 시간 어긋날 수 있습니다."
        )


def pagespeed_quota(
    db: Session, *, organization_id: uuid.UUID | None = None, now: datetime | None = None
) -> QuotaUsage:
    """오늘 PageSpeed 를 몇 번 불렀는지 센다.

    실패한 호출도 센다. 요청은 나갔고 한도를 썼기 때문이다 — 빼면 남은 양을 실제보다
    많게 세고, 그 숫자를 믿고 진단을 돌리다 한도를 넘긴다.
    """
    moment = now or datetime.now(UTC)
    start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    def count(*conditions) -> int:  # type: ignore[no-untyped-def]
        stmt = select(func.count()).select_from(APIUsageEvent).where(
            APIUsageEvent.provider == _PROVIDER,
            APIUsageEvent.created_at >= start,
            APIUsageEvent.created_at < end,
            *conditions,
        )
        return int(db.execute(stmt).scalar_one() or 0)

    total = count()
    mine = (
        count(APIUsageEvent.organization_id == organization_id)
        if organization_id is not None
        else 0
    )

    return QuotaUsage(
        provider=_PROVIDER,
        calls_today=total,
        calls_by_this_organization=mine,
        daily_quota=PAGESPEED_DAILY_QUOTA,
        window_start=start,
        window_end=end,
    )
