"""무엇을 먼저 고쳐야 점수가 가장 많이 오르는가.

화면이 이 계산을 스스로 하면 안 된다. 산식은 발행된 명세와 채점기의 소관이고, 화면이
따로 어림하는 순간 "고치면 +12점" 과 실제로 고친 뒤의 점수가 어긋난다. 기획서 §12.3 —
한 원시 결과에서 보기만 다르게 만들며 별도 계산을 중복하지 않는다.

산식은 :mod:`veo.scoring.evaluator` 와 같다::

    penalty        = 심각도계수 x 상태배수 x 수집비율 x 신뢰도
    카테고리 점수  = 100 x max(0, 1 - Σpenalty / budget)
    전체 점수      = Σ(카테고리 점수 x 가중치) / Σ가중치

한 항목을 통과로 바꾸면 그 항목의 penalty 가 사라진다. 그만큼 카테고리 점수가 오르고,
그 카테고리의 가중치 비율만큼 전체 점수가 오른다.

**상한이 걸려 있으면 이야기가 다르다.** 상한은 "이것을 풀기 전에는 몇 점 이상 줄 수 없다"
는 규칙이므로, 그 상태에서는 항목 하나를 고쳐도 전체 점수가 움직이지 않는다. 그때
"+12점" 이라고 쓰면 고치고 나서 점수가 그대로여서 거짓말이 된다. 그래서 이득을 0 으로
보고하고 상한 때문임을 함께 말한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from veo.scoring.models import ScoreResult

#: 고칠 수 있는 판정. 통과는 고칠 것이 없고, 해당없음은 적용되지 않으며, 측정 불가는
#: **우리가** 못 잰 것이라 고객의 조치 목록에 올릴 일이 아니다.
_ACTIONABLE: Final = frozenset({"FAIL", "WARNING"})


@dataclass(frozen=True, slots=True)
class Improvement:
    """고치면 얼마나 오르는가."""

    check_id: str
    category_id: str
    #: 이 항목을 통과로 바꿨을 때 전체 점수가 오르는 폭. 0~100 척도.
    gain_points: float
    #: 상한에 걸려 있어 지금은 고쳐도 점수가 오르지 않는 상태.
    blocked_by_cap: bool


def _rows(result: ScoreResult) -> list[dict[str, Any]]:
    """계산 추적에 남은 항목별 행. 채점기가 실제로 쓴 값이다."""
    checks = result.trace.get("checks")
    return [row for row in checks if isinstance(row, dict)] if isinstance(checks, list) else []


def rank_improvements(result: ScoreResult) -> tuple[Improvement, ...]:
    """이득이 큰 것부터. 이득이 0 인 항목은 상한에 걸린 경우에만 남긴다."""
    scoreable = [c for c in result.categories if c.status == "SCORED" and c.score is not None]
    weight_total = sum(c.weight for c in scoreable)
    if weight_total <= 0:
        return ()

    budget_of = {c.category_id: c.budget for c in result.categories}
    weight_of = {c.category_id: c.weight for c in result.categories}
    scoreable_ids = {c.category_id for c in scoreable}

    # 상한이 걸린 점수는 항목을 고쳐도 상한 아래에서만 움직인다. 상한과 상한 전 점수가
    # 같다면 상한이 실제로 깎고 있지는 않다는 뜻이므로 정상 계산한다.
    before = result.overall_score_before_caps
    after = result.overall_score
    capped = bool(result.applied_caps) and before is not None and after is not None and after < before

    entries: list[Improvement] = []
    for row in _rows(result):
        if str(row.get("status")) not in _ACTIONABLE:
            continue
        if not row.get("counted_in_budget"):
            continue

        category_id = str(row.get("category_id", ""))
        if category_id not in scoreable_ids:
            continue

        budget = budget_of.get(category_id, 0.0)
        penalty = float(row.get("penalty") or 0.0)
        if budget <= 0 or penalty <= 0:
            continue

        # 이 항목의 penalty 가 사라졌을 때 카테고리 점수가 오르는 폭, 그리고 그것이
        # 전체에서 차지하는 몫. 카테고리 점수는 0 에서 잘리므로 상승분도 그만큼만 잡는다.
        category_gain = 100.0 * (penalty / budget)
        overall_gain = category_gain * weight_of.get(category_id, 0.0) / weight_total

        entries.append(
            Improvement(
                check_id=str(row.get("check_id", "")),
                category_id=category_id,
                gain_points=0.0 if capped else round(overall_gain, 2),
                blocked_by_cap=capped,
            )
        )

    entries.sort(key=lambda entry: (-entry.gain_points, entry.check_id))
    return tuple(entry for entry in entries if entry.gain_points > 0 or entry.blocked_by_cap)
