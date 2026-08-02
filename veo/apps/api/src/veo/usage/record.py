"""외부 API 를 몇 번 불렀는지 남긴다.

`api_usage_events` 테이블은 처음부터 있었지만 **쓰는 코드가 하나도 없었다.** 진단이
외부 API 를 부르지 않던 동안에는 빈 것이 정상이었다. 2026-08-01 에 PageSpeed 배선이
들어가면서 실제로 호출이 나가기 시작했고, 그 순간부터 빈 테이블은 결함이 됐다.

## 여기서 세는 것은 돈이 아니라 횟수다

PageSpeed 는 하루 25,000회까지 무료다. 돈은 들지 않는다. 그래서 `cost_krw` 는 0 이고,
그것은 **모른다는 뜻이 아니라 정말 0원이라는 뜻**이다. 값을 모르는 제공자를 나중에
붙일 때는 `None` 으로 둔다 — 0 과 None 을 섞으면 "공짜라서 0" 과 "몰라서 0" 이
같은 자리에 앉고, 그 표를 보고 아무도 판단할 수 없게 된다.

**진짜 위험은 한도다.** 25,000회를 넘기면 그날의 모든 고객 진단에서 성능이 측정
불가가 된다. 돈이 아니라 그날 하루가 사라진다. 그래서 이 기록의 목적은 청구서가
아니라 "한도까지 얼마나 남았는가" 다.

진단 한 번에 최대 5회가 나간다(표본 상한). 25,000 ÷ 5 = **하루 5,000회 진단**이
이론상 한계이고, 실패한 호출도 한도를 쓰므로 실제로는 그보다 적다.

## 기록이 진단을 막지 않는다

사용량을 남기다 실패했다고 고객의 진단 결과를 버리면 안 된다. 진단은 이미 끝났고,
그 결과는 옳다. 그래서 여기서 나는 예외는 삼키되 **삼켰다는 사실은 로그로 남긴다** —
조용히 사라지면 기록이 비어 있는 이유를 아무도 모른다.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from veo.db.models.analysis import APIUsageEvent

__all__ = ["record_pagespeed_calls"]

_log = logging.getLogger(__name__)

#: PageSpeed 는 하루 25,000회까지 무료다. **모른다가 아니라 정말 0원**이다.
_FREE_WITHIN_QUOTA_KRW = 0.0

#: 이 호출이 무엇이었는지. 구글 엔드포인트 이름을 그대로 쓴다 — 나중에 로그와
#: 대조할 사람이 우리가 지어낸 이름을 구글 문서에서 찾을 수는 없다.
_OPERATION = "runPagespeed"


def record_pagespeed_calls(
    db: Session,
    calls: Iterable[Any],
    *,
    organization_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    request_id: str | None = None,
) -> int:
    """호출 기록을 남기고 남긴 건수를 돌려준다.

    실패해도 예외를 올리지 않는다 — 진단 결과가 사용량 기록 때문에 사라지면 안 된다.
    대신 삼킨 사실을 로그로 남긴다.
    """
    rows: list[APIUsageEvent] = []
    for call in calls:
        cache_hit = call.was_cache_hit
        rows.append(
            APIUsageEvent(
                organization_id=organization_id,
                project_id=project_id,
                provider="GOOGLE_PAGESPEED",
                operation=_OPERATION,
                # 상태 코드는 우리가 못 본다. 어댑터가 이미 분류해 오류 코드로 바꿔
                # 주기 때문이다. 숫자를 지어내지 않고 비워 둔다.
                status_code=None,
                # **알려진 한계.** 이 컬럼은 NOT NULL 이라 "모른다" 를 담을 수 없다.
                # 근거가 있을 때만 True 이고, 근거가 없으면 False 가 들어가는데 그
                # False 는 "새로 쟀다" 가 아니라 "판단할 수 없었다" 는 뜻이다. 둘을
                # 구분하려면 컬럼을 nullable 로 바꾸는 마이그레이션이 필요하고,
                # 지금 세는 것이 캐시 비율이 아니라 **호출 횟수**라 미뤄 둔다.
                # 캐시 비율을 지표로 쓰기 시작하면 그때 반드시 먼저 고쳐야 한다.
                was_cache_hit=bool(cache_hit),
                latency_ms=call.latency_ms,
                cost_krw=_FREE_WITHIN_QUOTA_KRW,
                request_id=request_id,
            )
        )

    if not rows:
        return 0

    try:
        db.add_all(rows)
        db.flush()
    except Exception:
        _log.exception(
            "사용량 기록에 실패했습니다. 진단 결과는 그대로 유지합니다 — "
            "이 로그가 없으면 기록이 비어 있는 이유를 알 수 없습니다."
        )
        db.rollback()
        return 0

    # 경보는 기록 지점에서만 판단한다 — 한도는 호출이 있을 때만 넘을 수 있으므로,
    # 여기 하나면 콘솔·공개 어느 경로든 덮인다. 실패해도 기록은 유지된다.
    from veo.usage.alerts import maybe_alert_pagespeed_quota

    maybe_alert_pagespeed_quota(db, recorded=len(rows))

    return len(rows)
