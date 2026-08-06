"""페이지 하나의 점수 — 그 페이지에서 판정된 URL 범위 검사만으로.

설계는 docs/research/SEO_SCORING_V3_PAGES.md(프로토타입 시험 24개로 검증), 숫자는
발행 명세에서만 온다. 사이트 점수(evaluator.py)와의 관계:

* **같은 규칙** — 상태 셈법(N/A·NOT_SAMPLED 분모 제외, UNKNOWN 분모 유지 0점),
  고정 배점, 관문 곱셈, 못 잰 관문은 곱하지 않음(0-A).
* **다른 것 하나** — 페이지 종합은 채점 가능한 단계로 **재정규화**한다. 페이지는
  템플릿에 따라 구조가 다르다: 구조화 데이터가 원래 없는 안내 페이지에서 그 단계가
  통째로 빠졌다고 감점되면, 페이지 순위가 결함이 아니라 템플릿 종류로 갈린다.
  (1.9.0 이 전 영역 N/A 재정규화를 사이트 쪽에서도 공식화했으므로 이제 방향도 같다.)

## SITE 검사를 오류로 거부하는 이유

"본문 중복이 없다" 는 페이지 하나의 성질이 아니다. SITE 검사를 페이지에 붙이면
분모가 다른 두 숫자가 같은 눈금처럼 보인다 — 우리가 타사 진단에서 잡아낸 바로 그
결함이다(methodology §2.9). 조용히 무시하지 않는다: 조용한 무시는 호출자의 실수를
산식이 덮어 주는 것이다.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

from veo.scoring.errors import ScoringSpecError
from veo.scoring.models import (
    CheckOutcome,
    CheckStatus,
    ScoringSpec,
    SpecCategory,
)

__all__ = ["PageLoss", "PageScore", "PageStageScore", "evaluate_page"]

_FROZEN = ConfigDict(frozen=True)

#: 화면이 "표본 밖" 항목에 붙일 문구. 판정이 아니라 정책이라는 사실이 읽혀야 한다.
NOT_SAMPLED_NOTE_KO: Final = (
    "표본 밖 — 명세의 표본 정책이 이 페이지를 재지 않았습니다. 요청 시 측정할 수 "
    "있으며, 점수와 측정 범위 어느 쪽에도 반영되지 않습니다."
)


class PageStageScore(BaseModel):
    """검색 여정 한 단계의, 이 페이지에서의 점수."""

    model_config = _FROZEN

    category_id: str
    name_ko: str
    weight: float
    is_gate: bool
    #: 관문 단계는 누적 도달률(x100), 품질 단계는 그 단계 URL 배점 안에서의 점수.
    #: ``None`` 은 이 페이지에서 그 단계에 판정된 URL 검사가 하나도 없다는 뜻이다.
    score: float | None


class PageLoss(BaseModel):
    """이 페이지가 잃은 점수 한 건 — 고치면 그만큼 돌아온다."""

    model_config = _FROZEN

    check_id: str
    category_id: str
    status: str
    #: 페이지 종합(100점 만점) 기준의 손실 폭. 재정규화 후의 값이다.
    lost: float


class PageScore(BaseModel):
    """페이지 하나의 점수와, 그 숫자가 어떻게 나왔는지 전부.

    항등식: ``quality == 100 - Σ(losses.lost)`` (채점 가능한 단계가 있을 때),
    ``score == reach x quality``. 화면·시험이 이 항등식으로 산식을 검산한다.
    """

    model_config = _FROZEN

    spec_id: str
    spec_version: str
    spec_checksum: str
    status: str  # SCORED | UNKNOWN | NOT_APPLICABLE
    score: float | None
    reach: float
    quality: float | None
    stages: tuple[PageStageScore, ...] = ()
    losses: tuple[PageLoss, ...] = ()
    #: 확인하지 못한 관문 — 곱하지 않았고, 화면은 "차단 여부 미확인" 을 말해야 한다.
    gate_unverified: tuple[str, ...] = ()
    unmeasured: tuple[str, ...] = ()
    not_sampled: tuple[str, ...] = ()
    not_applicable: tuple[str, ...] = ()
    not_sampled_note_ko: str = NOT_SAMPLED_NOTE_KO


def _url_checks(category: SpecCategory) -> list:  # type: ignore[type-arg]
    return [check for check in category.checks if check.scope == "URL"]


def evaluate_page(spec: ScoringSpec, outcomes: list[CheckOutcome]) -> PageScore:
    """페이지 하나의 판정들로 그 페이지의 점수를 낸다.

    ``outcomes`` 는 부분 공급이 허용된다 — 이 페이지에서 판정된 적 없는 검사는
    빠지고, 빠진 검사는 분모에 들어오지 않는다(그 페이지에 그 항목이 없었다는 뜻과
    같은 셈). 단, 공급된 판정은 전부 이 명세의 URL 범위 검사여야 하고, NOT_SAMPLED
    는 명세가 표본 정책을 선언한 검사에만 허용된다.
    """
    if spec.status_policy.unknown != "SCORE_AS_ZERO_KEEP_IN_DENOMINATOR":
        raise ScoringSpecError(
            f"{spec.spec_id}@{spec.version}: 페이지 점수는 절대 평가 명세에서만 계산한다"
        )

    check_by_id = {
        check.id: (category, check)
        for category in spec.categories
        for check in category.checks
    }

    by_id: dict[str, CheckOutcome] = {}
    for item in outcomes:
        found = check_by_id.get(item.check_id)
        if found is None:
            raise ScoringSpecError(
                f"check '{item.check_id}' is not defined in specification "
                f"{spec.spec_id}@{spec.version}"
            )
        if found[1].scope != "URL":
            raise ScoringSpecError(
                f"{item.check_id} 는 SITE 범위 검사다. 페이지 점수에 넣을 수 없다 — "
                "여러 장을 봐야 잴 수 있는 것을 한 장의 점수에 붙이면 분모가 다른 "
                "두 숫자가 같은 눈금처럼 보인다."
            )
        if (
            item.status is CheckStatus.NOT_SAMPLED
            and item.check_id not in spec.sampled_check_ids
        ):
            raise ScoringSpecError(
                f"check '{item.check_id}' may not be NOT_SAMPLED: specification "
                f"{spec.spec_id}@{spec.version} declares no sampling policy for it"
            )
        if item.check_id in by_id:
            raise ScoringSpecError(f"duplicate outcome supplied for check '{item.check_id}'")
        by_id[item.check_id] = item

    policy = spec.status_policy
    multiplier = {
        CheckStatus.FAIL: policy.fail_penalty_multiplier,
        CheckStatus.WARNING: policy.warning_penalty_multiplier,
        CheckStatus.PASS: policy.pass_penalty_multiplier,
    }

    reach = 1.0
    gate_unverified: list[str] = []
    unmeasured: list[str] = []
    not_sampled: list[str] = []
    not_applicable: list[str] = []
    stages: list[PageStageScore] = []
    # (category, 손실비율, [(check_id, 단계 안 손실, status)]) — 재정규화 전.
    scoreable: list[tuple[SpecCategory, float, list[tuple[str, float, str]]]] = []

    for category in spec.categories:
        if not category.contributes_to_score:
            continue
        members = _url_checks(category)

        if category.is_gate:
            stage_reach = 1.0
            for check in members:
                gate_item = by_id.get(check.id)
                if gate_item is None or gate_item.status is CheckStatus.NOT_APPLICABLE:
                    continue
                if gate_item.status is CheckStatus.NOT_SAMPLED:
                    not_sampled.append(check.id)
                    continue
                if gate_item.status is CheckStatus.UNKNOWN:
                    # 관측하지 않은 차단을 있다고 하면 없는 결함을 지어내는 것이다(0-A).
                    gate_unverified.append(check.id)
                    continue
                blocked = multiplier.get(gate_item.status, 1.0) * min(
                    1.0, gate_item.coverage_ratio
                )
                if blocked > 0:
                    stage_reach *= 1.0 - blocked
            reach *= stage_reach
            stages.append(
                PageStageScore(
                    category_id=category.id,
                    name_ko=category.name_ko,
                    weight=category.weight,
                    is_gate=True,
                    # **이 관문 하나**의 도달률이다. 여태까지 곱해 온 값(reach)을 넣으면
                    # 관문이 둘 이상인 명세에서 두 번째 칸이 첫 칸의 손실까지 자기 것으로
                    # 보여 준다. 사이트 쪽도 같은 값을 쓴다(0-D).
                    score=round(stage_reach * 100.0, 6),
                )
            )
            continue

        live: list = []  # type: ignore[type-arg]
        for check in members:
            quality_item = by_id.get(check.id)
            if quality_item is None:
                continue
            if quality_item.status is CheckStatus.NOT_APPLICABLE:
                not_applicable.append(check.id)
            elif quality_item.status is CheckStatus.NOT_SAMPLED:
                not_sampled.append(check.id)
            else:
                live.append(check)

        if not live:
            stages.append(
                PageStageScore(
                    category_id=category.id,
                    name_ko=category.name_ko,
                    weight=category.weight,
                    is_gate=False,
                    score=None,
                )
            )
            continue

        # 단계의 페이지 분모 = 그 단계 URL 검사 배점 합(명세 상수). N/A·표본 밖의
        # 몫은 살아 있는 형제에게 재분배된다 — 사이트 점수와 같은 규칙이다.
        budget = sum(check.points or 0.0 for check in members)
        declared = sum(check.points or 0.0 for check in live)
        if budget <= 0.0 or declared <= 0.0:
            raise ScoringSpecError(
                f"{spec.spec_id}@{spec.version}: {category.id} 의 URL 검사에 배점이 "
                "없다 — 페이지 점수는 고정 배점 명세(1.8.0+)에서만 계산한다"
            )
        scale = budget / declared

        stage_lost = 0.0
        loss_rows: list[tuple[str, float, str]] = []
        for check in live:
            live_item = by_id[check.id]
            points = (check.points or 0.0) * scale
            if live_item.status is CheckStatus.UNKNOWN:
                lost = points
                unmeasured.append(check.id)
            else:
                breadth = min(1.0, live_item.coverage_ratio) ** policy.breadth_exponent
                confidence = (
                    live_item.confidence if live_item.confidence is not None else 1.0
                )
                lost = (
                    points * multiplier.get(live_item.status, 1.0) * breadth * confidence
                )
            if lost > 0:
                loss_rows.append((check.id, lost, str(live_item.status.value)))
            stage_lost += lost

        stages.append(
            PageStageScore(
                category_id=category.id,
                name_ko=category.name_ko,
                weight=category.weight,
                is_gate=False,
                score=round(100.0 * max(0.0, (budget - stage_lost) / budget), 6),
            )
        )
        scoreable.append((category, stage_lost / budget, loss_rows))

    if not scoreable:
        provided = [item.status for item in by_id.values()]
        status = (
            "NOT_APPLICABLE"
            if provided
            and all(
                s in (CheckStatus.NOT_APPLICABLE, CheckStatus.NOT_SAMPLED) for s in provided
            )
            else "UNKNOWN"
        )
        return PageScore(
            spec_id=spec.spec_id,
            spec_version=spec.version,
            spec_checksum=spec.checksum,
            status=status,
            score=None,
            reach=round(reach, 6),
            quality=None,
            stages=tuple(stages),
            gate_unverified=tuple(gate_unverified),
            unmeasured=tuple(unmeasured),
            not_sampled=tuple(not_sampled),
            not_applicable=tuple(not_applicable),
        )

    # 페이지 종합 = 도달률 x (채점 가능한 단계들의 가중 평균). 재정규화 — 판정된
    # 단계가 적은 페이지가 그 이유만으로 감점되지 않는다.
    weight_total = sum(category.weight for category, _, _ in scoreable)
    losses: list[PageLoss] = []
    for category, _fraction_lost, loss_rows in scoreable:
        stage_share = category.weight / weight_total * 100.0
        budget = sum(check.points or 0.0 for check in _url_checks(category))
        for check_id, lost, status_value in loss_rows:
            losses.append(
                PageLoss(
                    check_id=check_id,
                    category_id=category.id,
                    status=status_value,
                    lost=round(stage_share * (lost / budget), 6),
                )
            )

    losses.sort(key=lambda loss: -loss.lost)
    # **품질을 화면에 내보내는 손실들에서 그대로 뺀다.**
    #
    # 예전에는 품질을 단계별 합계에서 빼고(`quality -= stage_share * fraction_lost`),
    # 손실은 항목마다 따로 반올림해 내보냈다. 수학적으로는 같은 값이지만 반올림이 서로
    # 달라 `품질 == 100 - Σ손실` 이 미세하게 어긋났다(실측 73.257706 vs 73.257703).
    #
    # 모든 손실이 0 이던 동안에는 이 어긋남이 드러나지 않았다 — 확신도 결함으로 손실이
    # 전부 0 이었기 때문이다(2026-08-05). 그 결함을 고치자마자 항등식이 깨졌다.
    #
    # 화면은 이 항등식으로 숫자를 검산한다. 그러니 **설명이 곧 숫자여야** 한다: 보여주는
    # 손실을 더한 것이 정확히 깎인 만큼이다. 반대로 두면 "왜 이 점수인가" 를 설명한 표가
    # 그 점수와 맞지 않는다.
    quality = max(0.0, 100.0 - sum(loss.lost for loss in losses))
    return PageScore(
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
        status="SCORED",
        score=round(reach * quality, 6),
        reach=round(reach, 6),
        quality=round(quality, 6),
        stages=tuple(stages),
        losses=tuple(losses),
        gate_unverified=tuple(gate_unverified),
        unmeasured=tuple(unmeasured),
        not_sampled=tuple(not_sampled),
        not_applicable=tuple(not_applicable),
    )
