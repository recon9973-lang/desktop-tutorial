"""외부 API 사용량 — 남기는 쪽과 세는 쪽.

**돈이 아니라 한도가 위험하다.** PageSpeed 는 하루 25,000회까지 무료라 청구서는 오지
않지만, 넘기면 그날의 모든 고객 진단에서 성능이 측정 불가가 된다.
"""

from veo.usage.quota import PAGESPEED_DAILY_QUOTA, QuotaUsage, pagespeed_quota
from veo.usage.record import record_pagespeed_calls

__all__ = [
    "PAGESPEED_DAILY_QUOTA",
    "QuotaUsage",
    "pagespeed_quota",
    "record_pagespeed_calls",
]
