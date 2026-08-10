"""``/usage`` — 외부 API 를 얼마나 썼고 한도까지 얼마나 남았는가.

이 라우터가 없어서 **세는 법은 있는데 볼 곳이 없었다.** `veo.usage.pagespeed_quota` 는
완성돼 있었고 시험도 있었지만 부르는 코드가 하나도 없었다. 부를 수 없는 기능은 없는
기능이다(0-E).

한도를 화면에 붙이는 이유는 순서 때문이다. 넘고 나서는 "성능이 전부 측정 불가" 로만
드러나고, 그것도 화면에서는 **사이트의 문제처럼 보이는 형태**로 나타난다. 그때는 이미
그날 하루가 지나갔다.

## 전체를 돌려주는 것은 의도한 것이다

`calls_today` 는 조직 경계를 넘어 전부 센다. 조직 격리 원칙의 예외처럼 보이지만 예외가
아니라 **질문 자체가 전역이기 때문이다** — 한도는 API 키 하나에 걸리고 키는 하나다.
조직별로 잘라 세면 "우리 조직은 200회밖에 안 썼는데요" 라고 말하는 동안 키는 이미
막혀 있다. 새어 나가는 것은 고객 자료가 아니라 우리 키의 소진량이고, 이 화면은
``usage:read`` 를 가진 내부 역할만 본다(SALES_VIEWER·CLIENT_VIEWER 에는 없다).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.envelope import ApiResponse
from veo.db.session import get_db
from veo.notify import AlertOutcome, send_alert
from veo.organizations.http import guard
from veo.usage.quota import CALLS_PER_SCAN, pagespeed_quota
from veo.usage.schemas import AlertTestPayload, PageSpeedQuotaPayload

router = APIRouter(prefix="/usage", tags=["usage"])

UsageReader = Annotated[Principal, Depends(guard(Permission.USAGE_READ))]


@router.get(
    "/pagespeed-quota",
    response_model=ApiResponse[PageSpeedQuotaPayload],
    summary="오늘 PageSpeed 를 몇 번 불렀고 얼마나 남았는가",
    description=(
        "PageSpeed 는 하루 25,000회까지 무료라 **청구서가 아니라 하루가 위험합니다.** "
        "넘기면 그날의 모든 고객 진단에서 성능이 측정 불가가 되고, 화면에는 사이트의 "
        "문제처럼 보이는 형태로 나타납니다.\n\n"
        "`calls_by_this_organization` 은 참고용입니다. **남은 양은 전체로만 답할 수 "
        "있습니다** — 한도는 API 키 하나에 걸리고 키는 하나라, 다른 조직이 태운 것도 "
        "같은 한도를 씁니다.\n\n"
        "실패한 호출도 셉니다. 요청은 나갔고 한도를 썼기 때문입니다. 초기화 시각은 "
        "구글이 태평양 시간 자정으로 정하는데 이 집계는 UTC 하루 기준이라 최대 몇 "
        "시간 어긋날 수 있고, 그 사실을 `caveat_ko` 에 적어 보냅니다."
    ),
)
def pagespeed_quota_today(
    principal: UsageReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[PageSpeedQuotaPayload]:
    usage = pagespeed_quota(db, organization_id=principal.organization_id)
    return ok(
        PageSpeedQuotaPayload(
            provider=usage.provider,
            calls_today=usage.calls_today,
            calls_by_this_organization=usage.calls_by_this_organization,
            daily_quota=usage.daily_quota,
            remaining=usage.remaining,
            used_ratio=usage.used_ratio,
            is_warning=usage.is_warning,
            is_exhausted=usage.is_exhausted,
            scans_remaining=usage.scans_remaining,
            calls_per_scan=CALLS_PER_SCAN,
            window_start=usage.window_start,
            window_end=usage.window_end,
            # 문장은 여기서 짓지 않는다. 화면과 응답이 각자 지으면 한도를 설명하는
            # 말이 두 벌이 되고, 한쪽만 고쳐진다.
            summary_ko=usage.summary_ko(),
            caveat_ko=usage.caveat_ko(),
            remedies_ko=usage.remedies_ko(),
        ),
        request_id,
    )


#: 시험 발송의 결과를 사람 말로. 주소는 어디에도 싣지 않는다.
_ALERT_MESSAGES_KO: dict[AlertOutcome, str] = {
    AlertOutcome.SENT: (
        "보냈습니다. 받는 채널을 확인해 주십시오. 도착하지 않았다면 주소는 맞지만 "
        "받는 쪽(채널 삭제·권한)에 문제가 있는 것입니다."
    ),
    AlertOutcome.DISABLED: (
        "알림 주소가 설정되어 있지 않습니다. 지금은 모든 경보가 조용히 버려집니다 — "
        "Railway 환경변수 VEO_ALERT_WEBHOOK_URL 에 https 주소를 넣어 주십시오."
    ),
    AlertOutcome.FAILED: (
        "보내지 못했습니다. 주소가 https 인지, 받는 쪽이 살아 있는지 확인해 주십시오. "
        "서버 로그에 사유가 남습니다."
    ),
}


@router.post(
    "/alert-test",
    response_model=ApiResponse[AlertTestPayload],
    summary="경보가 실제로 닿는지 한 번 보내 본다",
    description=(
        "알림 통로가 살아 있는지 확인하는 **유일한 방법**입니다. 경보는 사고가 났을 때만 "
        "울리므로, 주소를 넣고도 맞는지 알 방법이 없었습니다.\n\n"
        "실제 경보와 같은 통로로 보냅니다 — 시험용 우회로를 따로 두면 그 우회로만 "
        "동작하는 상태를 못 잡습니다. 본문에 **시험 발송**이라고 적혀 나갑니다.\n\n"
        "응답에 주소는 들어 있지 않습니다."
    ),
)
def send_test_alert(principal: UsageReader, request_id: RequestId) -> ApiResponse[AlertTestPayload]:
    outcome = send_alert(
        title_ko="VEO 경보 시험 발송",
        body_ko=(
            "이 메시지가 보이면 알림 통로가 살아 있습니다. 실제 경보(사용량 한도·진단 "
            "하락·관측 미완료)도 같은 곳으로 옵니다."
        ),
        source="usage.alert_test",
    )
    return ok(
        AlertTestPayload(outcome=str(outcome.value), message_ko=_ALERT_MESSAGES_KO[outcome]),
        request_id,
    )
