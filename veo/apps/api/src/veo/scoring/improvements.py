"""무엇을 먼저 고쳐야 점수가 가장 많이 오르는가.

화면이 이 계산을 스스로 하면 안 된다. 산식은 발행된 명세와 채점기의 소관이고, 화면이
따로 어림하는 순간 "고치면 +12점" 과 실제로 고친 뒤의 점수가 어긋난다. 기획서 §12.3 —
한 원시 결과에서 보기만 다르게 만들며 별도 계산을 중복하지 않는다.

**어림하지 않고 실제로 고쳐 본다.** 항목 하나를 PASS 로 바꾼 판정 목록을 만들어
:func:`veo.scoring.evaluator.evaluate` 를 다시 돌리고, 나온 점수의 차이를 그대로 쓴다.
그것이 "고치면 오르는 폭" 의 정의 그 자체다.

예전에는 산식을 이 파일에서 다시 세웠다. 두 벌이 되면 언젠가 한쪽만 바뀌고(0-D),
실제로 그랬다 — 2026-08-05 시연으로 확인한 두 가지:

* **분모가 달랐다.** 여기서는 채점 가능한 영역 가중치의 합(실측 130.0)을 썼고 채점기는
  `effective_weight_total`(100.0)을 썼다. 그래서 표기된 이득이 실제보다 항상 23% 낮았다
  (0.769 = 100/130). 표본과 항목을 가리지 않고 같은 비율이었다.
* **상한을 "고쳐도 안 오른다" 로 뭉갰다.** 상한이 걸려 있으면 모든 항목의 이득을 0 으로
  적었는데, 상한을 **유발한 바로 그 항목**을 고치면 상한이 풀려 크게 오른다:

      render_gap            js_render_parity          표기 0.0 → 실제 +32.91
      cross_domain_canonical canonical.not_cross_domain 표기 0.0 → 실제 +28.89

  고객은 이 숫자를 보고 무엇부터 고칠지 정한다. **가장 효과 큰 항목이 "고쳐도 소용없다"**
  로 표시되고 있었다.

상한·도달률·재정규화가 얽힌 산식을 여기서 다시 구현하면 같은 일이 반복된다. 재채점은
실측 **0.30ms**, 조치 대상 14건을 전부 다시 재도 4ms 다 — 진단 한 번이 38초인 것에 비하면
없는 비용이고, 근사할 이유가 없다.

`blocked_by_cap` 은 이제 **관측된 사실**이다: 다시 채점해도 점수가 오르지 않았고, 상한이
실제로 점수를 깎고 있다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

from veo.scoring.errors import SpecNotFoundError
from veo.scoring.evaluator import evaluate
from veo.scoring.models import CheckStatus, ScoreResult
from veo.scoring.spec import load_spec

#: 고칠 수 있는 판정. 통과는 고칠 것이 없고, 해당없음은 적용되지 않으며, 측정 불가는
#: **우리가** 못 잰 것이라 고객의 조치 목록에 올릴 일이 아니다.
_ACTIONABLE: Final = frozenset({"FAIL", "WARNING"})

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Improvement:
    """고치면 얼마나 오르는가."""

    check_id: str
    category_id: str
    #: 이 항목을 통과로 바꿨을 때 전체 점수가 오르는 폭. 0~100 척도.
    gain_points: float
    #: 상한에 걸려 있어 지금은 고쳐도 점수가 오르지 않는 상태.
    blocked_by_cap: bool


def rank_improvements(result: ScoreResult) -> tuple[Improvement, ...]:
    """이득이 큰 것부터. 이득이 0 인 항목은 상한에 걸린 경우에만 남긴다.

    명세는 **결과가 기록해 둔 그 판**을 다시 불러 쓴다(`spec_id`·`spec_version`).
    지금 발행된 최신 명세를 쓰면, 반년 전 실행을 다시 열었을 때 그때 없던 규칙으로
    "고치면 오르는 폭" 을 계산하게 된다 — 그 숫자는 그 실행의 것이 아니다(ADR 0012).
    """
    base = result.overall_score
    if base is None:
        return ()

    try:
        spec = load_spec(result.spec_id, result.spec_version)
    except SpecNotFoundError:
        # 명세를 못 찾으면 이득을 지어내지 않는다. 목록이 비는 편이, 없는 규칙으로 낸
        # 숫자를 고객이 보고 무엇부터 고칠지 정하는 것보다 낫다.
        _log.warning(
            "개선 이득을 계산할 명세를 찾지 못했습니다: %s@%s",
            result.spec_id, result.spec_version, exc_info=True,
        )
        return ()

    category_of = {
        check_id: category.category_id
        for category in result.categories
        for check_id in category.applicable_check_ids
    }
    # 상한이 지금 실제로 점수를 깎고 있는가. 상한이 걸려 있어도 상한 전후 점수가 같다면
    # 깎고 있지 않다는 뜻이므로 "상한 때문" 이라고 말하지 않는다.
    before = result.overall_score_before_caps
    capping = bool(result.applied_caps) and before is not None and base < before

    outcomes = list(result.outcomes)
    entries: list[Improvement] = []
    for index, outcome in enumerate(outcomes):
        if str(outcome.status) not in _ACTIONABLE:
            continue
        category_id = category_of.get(outcome.check_id, "")
        if not category_id:
            # 어느 영역에도 채점되지 않은 항목은 고쳐도 점수가 움직이지 않는다.
            continue

        # **이 항목만 통과로 바꿔 다시 채점한다.** 상한·도달률·재정규화가 전부 그대로
        # 반영된 값이 나온다 — 여기서 다시 세울 필요가 없다.
        patched = list(outcomes)
        patched[index] = outcome.model_copy(update={"status": CheckStatus.PASS})
        after = evaluate(spec, patched).overall_score
        gain = 0.0 if after is None else max(0.0, after - base)

        entries.append(
            Improvement(
                check_id=outcome.check_id,
                category_id=category_id,
                gain_points=gain,
                # 다시 채점해도 안 올랐고, 상한이 실제로 깎고 있다 — 그때만 참이다.
                blocked_by_cap=capping and gain <= 0.0,
            )
        )

    entries.sort(key=lambda entry: (-entry.gain_points, entry.check_id))
    return tuple(entry for entry in entries if entry.gain_points > 0 or entry.blocked_by_cap)
