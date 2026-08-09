"""관측 경보 — **돈은 나갔는데 다 재지 못한 실행**을 사람에게 알린다.

## 왜 이것이 필요한가

관측은 이 제품에서 **유일하게 호출마다 돈이 나가는 축**이다. 질문 1개 1회가 854원,
거래처 한 곳이 월 2.8~4만원이다(`docs/observation-engine.md` §8-C).

실패는 이미 남는다 — `observation_runs.stopped_reason` · `executions_skipped` ·
`skipped_detail`. 화면도 보여 준다. 그런데 **아무도 그 화면을 보고 있지 않다.**
주 1회 자동으로 도는 측정이라(§9 확정 설계) 사람이 그 시각에 앉아 있을 이유가 없다.

그래서 조용히 이런 일이 일어날 수 있다 —

```
매주 월요일 관측이 돈다
  → 엔진 하나의 열쇠가 만료된다
  → 그 엔진 몫이 전부 건너뛰어진다
  → 나머지 엔진 값으로 비율이 나온다
  → 화면은 정상으로 보이고, 청구서만 계속 나온다
```

`metrics.py` 가 분모를 지키므로 **숫자가 거짓이 되지는 않는다.** 하지만 "왜 이 주에
표본이 줄었나" 를 사람이 알아야 고칠 수 있고, 알기 전까지는 계속 돈만 나간다.

## 왜 새 통로를 만들지 않는가

`veo.notify.send_alert` 하나를 재사용한다. 그 모듈이 머리말에 못박아 둔 약속이다 —
*"새 알림이 필요하면 여기의 ``send_alert`` 를 부르지, 발송 코드를 새로 쓰지 않는다"*
(0-D). 웹훅 주소가 없으면 그쪽이 조용히 ``DISABLED`` 를 낸다. 여기서 그것을 오류로
다루지 않는다 — 알림을 못 보내는 것이 측정을 실패로 만들지는 않는다.

## 언제 부르지 않는가

**완전히 성공한 실행은 알리지 않는다.** 잘 된 것까지 알리면 채널이 시끄러워지고,
시끄러운 채널은 꺼진다 — 꺼진 알림은 없는 기능이다(`seo/regression.py` 와 같은 이유).

**수동 측정도 알리지 않는다.** 사람이 그 자리에서 버튼을 누르고 결과를 보고 있다.
알림은 아무도 안 보고 있을 때를 위한 것이다.
"""

from __future__ import annotations

import logging
from typing import Protocol, final

from veo.notify import AlertOutcome, send_alert

__all__ = ["ObservationRunFacts", "alert_if_incomplete"]

_log = logging.getLogger(__name__)

#: 정기 측정. 수동 측정은 사람이 보고 있으므로 알리지 않는다.
SCHEDULED = "SCHEDULED"


class _Sender(Protocol):
    def __call__(self, *, title_ko: str, body_ko: str, source: str) -> AlertOutcome: ...


@final
class ObservationRunFacts:
    """알림에 필요한 사실만. 저장 행을 통째로 받지 않는다 — 그러면 이 판단이 DB 모양에
    묶이고, 시험이 세션을 들고 와야 한다.
    """

    __slots__ = (
        "cost_usd",
        "executions_planned",
        "executions_skipped",
        "executions_valid",
        "kind",
        "project_name",
        "prompt_set_name",
        "stopped_reason",
        "unpriced_calls",
    )

    def __init__(
        self,
        *,
        kind: str,
        project_name: str,
        prompt_set_name: str,
        executions_planned: int,
        executions_valid: int,
        executions_skipped: int,
        stopped_reason: str | None,
        cost_usd: float,
        unpriced_calls: int,
    ) -> None:
        self.kind = kind
        self.project_name = project_name
        self.prompt_set_name = prompt_set_name
        self.executions_planned = executions_planned
        self.executions_valid = executions_valid
        self.executions_skipped = executions_skipped
        self.stopped_reason = stopped_reason
        self.cost_usd = cost_usd
        self.unpriced_calls = unpriced_calls

    @property
    def is_worth_telling(self) -> bool:
        """알릴 값이 있는가.

        셋을 다 만족해야 한다 —

        1. **정기 측정이다.** 수동은 사람이 보고 있다.
        2. **덜 쟀다.** 건너뛴 것이 있거나 중단됐거나, 유효 실행이 계획보다 적다.
        3. **돈이 나갔거나 나갔는지 모른다.** 아무 호출도 안 하고 끝났으면 잃은 것이
           없다 — 그건 실패라기보다 시작을 못 한 것이고, 작업 실패로 이미 보인다.
        """
        if self.kind != SCHEDULED:
            return False

        incomplete = (
            self.executions_skipped > 0
            or self.stopped_reason is not None
            or self.executions_valid < self.executions_planned
        )
        spent = self.cost_usd > 0 or self.unpriced_calls > 0
        return incomplete and spent


def alert_if_incomplete(
    facts: ObservationRunFacts, *, sender: _Sender = send_alert
) -> AlertOutcome:
    """덜 잰 정기 관측을 알린다. 알릴 것이 없으면 ``DISABLED``.

    예외를 밖으로 내보내지 않는다. **알림을 못 보낸 것이 측정을 실패로 만들면 안 된다** —
    잰 값은 이미 저장돼 있다.
    """
    if not facts.is_worth_telling:
        return AlertOutcome.DISABLED

    title = f"관측이 덜 끝났습니다 — {facts.project_name}"

    lines = [
        f"질문 집합: {facts.prompt_set_name}",
        f"계획 {facts.executions_planned}회 중 유효 {facts.executions_valid}회"
        f" · 건너뜀 {facts.executions_skipped}회",
    ]
    if facts.stopped_reason is not None:
        lines.append(f"중단 사유: {facts.stopped_reason}")

    # **금액은 잰 그대로 쓴다.** 반올림하지 않는다(사장님 지시 2026-08-09). 그리고
    # 값을 못 낸 호출이 있으면 그 사실을 함께 적는다 — 0원이라는 뜻이 아니라 모른다는
    # 뜻이고, 둘을 섞으면 청구서와 어긋난다.
    lines.append(f"이번 실행 비용: ${facts.cost_usd}")
    if facts.unpriced_calls > 0:
        lines.append(
            f"이 중 {facts.unpriced_calls}회는 금액을 알 수 없습니다"
            " (0원이라는 뜻이 아니라 모른다는 뜻입니다)."
        )

    lines.append("표본이 줄면 비율의 오차 폭이 넓어집니다. 엔진 열쇠와 한도를 확인해 주십시오.")

    try:
        outcome = sender(
            title_ko=title, body_ko="\n".join(lines), source="observations.incomplete_run"
        )
    except Exception:  # pragma: no cover - 발송 쪽이 이미 예외를 삼키지만 이중으로 막는다
        _log.warning("could not send observation alert", exc_info=True)
        return AlertOutcome.FAILED

    _log.info(
        "observation.incomplete project=%s valid=%s/%s skipped=%s alert=%s",
        facts.project_name,
        facts.executions_valid,
        facts.executions_planned,
        facts.executions_skipped,
        outcome,
    )
    return outcome
