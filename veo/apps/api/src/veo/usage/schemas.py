"""``/usage`` 응답 모양.

화면이 숫자를 다시 해석하지 않도록 **문장까지 여기서 실어 보낸다.** `summary_ko` 와
`caveat_ko` 는 `QuotaUsage` 가 만든 것을 그대로 옮기며, 화면이 `calls_today` 로 문장을
새로 지으면 안 된다 — 그 순간 한도를 설명하는 말이 두 벌이 되고, 한쪽만 고쳐진다.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["AlertTestPayload", "PageSpeedQuotaPayload"]


class PageSpeedQuotaPayload(BaseModel):
    """오늘 PageSpeed 를 몇 번 불렀고 얼마나 남았는가.

    **`calls_by_this_organization` 은 남은 양을 말해 주지 않는다.** 한도는 API 키 하나에
    걸리고 키는 하나이므로, 다른 조직이 태운 것도 같은 한도를 쓴다. 두 숫자를 같은 크기로
    나란히 그리면 화면이 "우리는 200회밖에 안 썼는데요" 라고 말하는 동안 키는 이미 막혀
    있게 된다. 그래서 `remaining`·`is_exhausted` 는 전체에서만 나온다.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str
    #: 오늘(UTC) 전체에서 나간 호출 수. **실패한 호출도 한도를 썼으므로 포함한다.**
    calls_today: int
    #: 이 조직이 쓴 몫. "누가 많이 썼나" 용이며 남은 양의 근거가 아니다.
    calls_by_this_organization: int
    daily_quota: int
    remaining: int
    used_ratio: float
    #: 한도를 넘기 **전에** 참이 된다. 넘고 나서 알면 그날은 이미 늦었다.
    is_warning: bool
    is_exhausted: bool
    #: 남은 호출로 더 돌릴 수 있는 진단 횟수(상한 기준). 사람이 판단에 쓰는 숫자는
    #: "5,000회 남음" 이 아니라 "1,000번 더 진단 가능" 쪽이다.
    scans_remaining: int
    #: 진단 한 번이 태우는 최대 호출 수. 위 나눗셈의 근거를 숨기지 않는다.
    calls_per_scan: int
    #: 세는 창(UTC 하루). 구글은 태평양 시간에 초기화하므로 경계가 어긋난다.
    window_start: datetime
    window_end: datetime
    #: 화면에 그대로 쓰는 한 줄. 남은 양을 먼저 말한다.
    summary_ko: str
    #: 이 숫자를 읽을 때 함께 알아야 하는 것. 화면에서 빼면 안 된다.
    caveat_ko: str
    #: 한도가 끝났을 때 무엇을 하라고 할지. 끝나지 않았으면 비어 있다.
    remedies_ko: list[str] = Field(default_factory=list)


class AlertTestPayload(BaseModel):
    """경보 통로가 실제로 닿는가 — **비밀값은 여기 없다.**

    주소 자체를 돌려주지 않는다. 사람이 알아야 하는 것은 "닿았다/안 닿았다/설정 안 됨"
    셋뿐이고, 주소를 화면에 실으면 그 화면을 열 수 있는 사람 모두가 그것을 갖는다.
    """

    model_config = ConfigDict(frozen=True)

    outcome: str = Field(
        description="SENT(닿았다) · DISABLED(주소가 설정되지 않았다) · FAILED(보냈으나 실패)"
    )
    message_ko: str = Field(description="사람이 읽고 다음에 무엇을 할지 아는 한 문장.")
