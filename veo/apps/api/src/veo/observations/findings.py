"""관측 결과를 위험 판정으로 옮긴다 — `claim_assessments` 에 쓰는 첫 코드.

## 왜 지금까지 없었나

`veo.observations.risk` 와 `veo.observations.review` 는 완성되어 있었다. 위험 분류
8종, 심각도 표, 검수 상태 기계, 공개 게이트까지 전부 있었고 시험도 붙어 있었다.
**그런데 `src/` 안에서 아무도 부르지 않았다.** `claim_assessments` 에 행을 쓰는 코드가
저장소 전체에 0건이었다.

지침서 0-E — 부를 수 없는 기능은 없는 기능이다. 완성된 모듈이 못 쓰이는 것은 안 만든
것과 결과가 같고, 오히려 나쁘다. 추적표에 "완료" 로 세어지기 때문이다.

## 지금 내는 판정은 한 종류다

`ENTITY_DISAMBIGUATION` — **동명 업체 혼동.** 방법론 8종 가운데 규칙만으로 낼 수 있는
것이 이것이고, 그 입력은 판별기가 이미 만들고 있다(보류된 언급).

나머지 7종은 **안 만든다.** 규칙으로 못 내는 것을 규칙인 척 내면 그 순간 위험 목록
전체가 못 믿을 것이 된다(0-A). 무엇이 왜 없는지는
:func:`assessment_kinds_not_yet_produced` 가 한국어로 말한다 — 화면에 "위험 0건" 만
뜨면 **위험이 없다** 로 읽히기 때문이다.

## 동명 혼동은 "틀렸다" 가 아니라 "모르겠다" 다

자동 판정을 `UNKNOWN` 으로 둔다. AI 가 틀린 말을 했다는 주장이 아니라 **우리가 누구
얘기인지 못 가린 것**이기 때문이다. 게이트가 `UNKNOWN` 을 `EXCLUDED_NOT_MEASURED` 로
빼므로 고객 문서에는 지적이 아니라 "확인하지 못한 건수" 로만 나타난다. 검수 전에
"AI 가 당신 병원을 다른 병원과 혼동했습니다" 라고 적으면, 우리가 확인하지 않은 것을
사실로 적는 것이다.

등급은 `높음` 이라 사람 검수를 거쳐야 게재된다. 병원 고객에게 신원 혼동은 가벼운
일이 아니다.

## 행에서 판정을 되읽을 수 있어야 한다

`claim_text` 만 남기면 그 문장이 **정말 그 답변의 그 자리** 였는지 확인할 수 없다.
그래서 포인터·해시·구간·판정 근거·영역을 함께 남긴다. 이 값들이 없으면 저장된 행은
쓰기 전용이 되고, 쓰기 전용 근거는 근거가 아니라 주장이다(0-A).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.observation import AIAnswer
from veo.db.models.observation import ClaimAssessment as ClaimAssessmentRow
from veo.observations.review.decisions import (
    ReviewedAssessment,
    ReviewHistoryEntry,
    ReviewStage,
    ReviewTrigger,
)
from veo.observations.risk.assessment import (
    AutomatedJudgement,
    AutomatedVerdict,
    ClaimAssessment,
    DecisionBasis,
    EvidenceRef,
)
from veo.observations.risk.taxonomy import ClaimDomain, RiskKind

#: 이름은 걸렸는데 이 고객인지 갈리지 않았다. 규칙이 낸 결론이고, 그 결론은 "모른다" 다.
RULE_NAME_COULD_NOT_BE_ATTRIBUTED = "RISK-R020"

#: 방법론 8종 가운데 아직 낼 수 없는 것과 그 이유. 화면과 보고서가 그대로 읽는다.
_NOT_YET_PRODUCED: tuple[tuple[RiskKind, str], ...] = (
    (
        RiskKind.CITATION_ENTAILMENT,
        "인용이 그 문장을 실제로 뒷받침하는지는 언어모델 판정이 필요합니다. 판정용 "
        "자격증명이 아직 없어 이 유형은 만들지 않습니다.",
    ),
    (
        RiskKind.CITATION_COMPLETENESS,
        "출처가 붙어야 할 주장인지 가리려면 문장 단위 의미 판단이 필요합니다. 규칙으로는 "
        "낼 수 없어 이 유형은 만들지 않습니다.",
    ),
    (
        RiskKind.CLAIM_ACCURACY,
        "고객이 스스로 공개한 사실(가격·주소·진료시간)과 대조해야 판정할 수 있습니다. "
        "그 수집 경로가 아직 없어 이 유형은 만들지 않습니다.",
    ),
    (
        RiskKind.STALENESS,
        "값이 오래됐는지는 고객 사이트의 현재 값과 대조해야 알 수 있습니다. 같은 이유로 "
        "아직 만들지 않습니다.",
    ),
    (
        RiskKind.RECOMMENDATION_INCLUSION,
        "취급하지 않는 시술 추천 목록에 올랐는지는 의미 판단입니다. 규칙으로는 낼 수 "
        "없습니다.",
    ),
    (
        RiskKind.RECOMMENDATION_EXCLUSION,
        "당연히 들어가야 할 목록에서 빠졌는지는 의미 판단입니다. 규칙으로는 낼 수 "
        "없습니다.",
    ),
    (
        RiskKind.SENTIMENT_WITH_GROUNDS,
        "긍정·부정과 그 근거는 의미 판단입니다. 규칙으로는 낼 수 없습니다.",
    ),
)


def assessment_kinds_not_yet_produced() -> tuple[dict[str, str], ...]:
    """아직 만들지 않는 위험 유형과 그 이유.

    "위험 0건" 옆에 이것이 없으면 그 0 은 **위험이 없다** 로 읽힌다. 실제로는 8종 중
    1종만 재고 있다.
    """
    return tuple(
        {"kind": kind.value, "reason_ko": reason} for kind, reason in _NOT_YET_PRODUCED
    )


def assessment_id_for(answer_id: uuid.UUID, kind: RiskKind) -> str:
    """한 답변·한 유형에 판정 하나. 같은 실행을 다시 읽어도 늘어나지 않는다."""
    return f"{answer_id}:{kind.value}"


def assessment_from_held_mention(
    *,
    answer_id: uuid.UUID,
    answer_ref: str,
    answer_hash: str,
    span_start: int,
    quoted_text: str,
    reasons_ko: Sequence[str],
    decided_at: datetime,
) -> ClaimAssessment:
    """보류된 언급 하나를 검수 가능한 판정으로.

    `reasons_ko` 는 판별기가 낸 문장을 **그대로** 옮긴다. 검수자가 읽어야 하는 것은
    기계가 실제로 본 근거이고, 여기서 요약하면 그 순간 다른 이야기가 된다.
    """
    return ClaimAssessment(
        assessment_id=assessment_id_for(answer_id, RiskKind.ENTITY_DISAMBIGUATION),
        ai_answer_id=str(answer_id),
        kind=RiskKind.ENTITY_DISAMBIGUATION,
        # 규제 영역(의료·법률·가격·계약)이 아니다. 여기서 묻는 것은 진료 내용이 아니라
        # **누구 얘기인가** 이므로 IDENTITY 다. 규제로 올리면 전건이 치명이 되고, 치명이
        # 흔해지면 치명이라는 말이 아무 뜻도 없어진다.
        domain=ClaimDomain.IDENTITY,
        evidence=EvidenceRef(
            answer_ref=answer_ref,
            answer_hash=answer_hash,
            span_start=span_start,
            span_end=span_start + len(quoted_text),
            quoted_text=quoted_text,
        ),
        automated=AutomatedJudgement(
            # "AI 가 틀렸다" 가 아니라 "우리가 못 가렸다".
            verdict=AutomatedVerdict.UNKNOWN,
            basis=DecisionBasis.DETERMINISTIC_RULE,
            rule_id=RULE_NAME_COULD_NOT_BE_ATTRIBUTED,
            rationale_ko=(
                "상호가 답변에 나왔지만 같은 이름의 다른 업체와 갈리지 않았습니다. "
                + (" / ".join(reasons_ko) if reasons_ko else "판별 근거가 기록되지 않았습니다.")
            ),
            decided_at=decided_at,
        ),
    )


def new_assessment_row(
    review: ReviewedAssessment, *, organization_id: uuid.UUID, answer_id: uuid.UUID
) -> ClaimAssessmentRow:
    """검수 기록 하나를 `claim_assessments` 행으로.

    `review_state` 는 `ReviewedAssessment` 가 정한다. 자동 판정은 절대 검수 상태를 만들
    수 없다 — `ClaimAssessment` 에는 그 값을 담을 칸 자체가 없다.
    """
    row = review.to_row()
    assessment = review.assessment
    return ClaimAssessmentRow(
        organization_id=organization_id,
        ai_answer_id=answer_id,
        claim_text=row["claim_text"],
        assessment_type=row["assessment_type"],
        claim_domain=assessment.domain.value,
        severity=row["severity"],
        automated_verdict=row["automated_verdict"],
        automated_basis=assessment.automated.basis.value,
        rule_id=assessment.automated.rule_id,
        automated_rationale=row["automated_rationale"],
        llm_model=row["llm_model"],
        llm_prompt_version=row["llm_prompt_version"],
        evidence_answer_ref=assessment.evidence.answer_ref,
        evidence_answer_hash=assessment.evidence.answer_hash,
        evidence_span_start=assessment.evidence.span_start,
        evidence_span_end=assessment.evidence.span_end,
        review_state=row["review_state"],
        review_stage=review.stage.value,
        review_history=[entry.as_dict() for entry in review.history],
    )


class UnreadableAssessmentError(ValueError):
    """저장된 행을 판정 객체로 되읽을 수 없다.

    옛 행이거나 근거 칸이 비어 있는 행이다. 비어 있는 자리를 그럴듯한 값으로 메워
    돌려주면 확인할 수 없는 지적이 확인된 지적처럼 보인다 — 조용히 건너뛰지 않고 여기서
    멈춘다.
    """


def review_from_row(row: ClaimAssessmentRow) -> ReviewedAssessment:
    """`claim_assessments` 행 하나를 다시 검수 기록으로.

    쓰기만 하고 못 읽는 테이블은 근거가 아니다. 이 함수가 성립한다는 것이 곧 "이 지적을
    나중에 다시 열어볼 수 있다" 는 뜻이다(0-A).
    """
    if not row.evidence_answer_ref or not row.evidence_answer_hash:
        raise UnreadableAssessmentError(
            f"{row.id}: 원문 포인터나 해시가 없어 이 판정을 되읽을 수 없습니다. "
            "근거를 다시 열 수 없는 지적은 보고서에 올릴 수 없습니다."
        )
    if row.evidence_span_start is None or row.evidence_span_end is None:
        raise UnreadableAssessmentError(f"{row.id}: 평가 구간이 기록되지 않았습니다.")

    assessment = ClaimAssessment(
        assessment_id=str(row.id),
        ai_answer_id=str(row.ai_answer_id),
        kind=RiskKind.from_storage(row.assessment_type),
        domain=ClaimDomain(row.claim_domain),
        evidence=EvidenceRef(
            answer_ref=row.evidence_answer_ref,
            answer_hash=row.evidence_answer_hash,
            span_start=row.evidence_span_start,
            span_end=row.evidence_span_end,
            quoted_text=row.claim_text,
        ),
        automated=AutomatedJudgement(
            verdict=AutomatedVerdict(row.automated_verdict),
            basis=DecisionBasis(row.automated_basis),
            rationale_ko=row.automated_rationale or "(근거가 기록되지 않았습니다)",
            decided_at=row.created_at,
            rule_id=row.rule_id,
            llm_model=row.llm_model,
            llm_prompt_version=row.llm_prompt_version,
        ),
    )
    return ReviewedAssessment(
        assessment=assessment,
        stage=ReviewStage(row.review_stage),
        history=tuple(_history_entry(item) for item in row.review_history or ()),
    )


def _history_entry(item: object) -> ReviewHistoryEntry:
    record = item if isinstance(item, dict) else {}
    return ReviewHistoryEntry(
        from_stage=ReviewStage(str(record.get("from_stage", ReviewStage.PENDING_REVIEW))),
        to_stage=ReviewStage(str(record.get("to_stage", ReviewStage.PENDING_REVIEW))),
        trigger=ReviewTrigger(str(record.get("trigger", ReviewTrigger.REVIEWER_DECISION))),
        at=datetime.fromisoformat(str(record["at"])),
        reviewer_id=record.get("reviewer_id"),
        note_ko=record.get("note_ko"),
    )


def reviews_for_run(
    session: Session, principal: Principal, run_id: uuid.UUID
) -> tuple[ReviewedAssessment, ...]:
    """이 실행이 남긴 위험 판정 전부, 검수 상태와 함께."""
    statement = (
        tenant_select(ClaimAssessmentRow, principal)
        .join(AIAnswer, AIAnswer.id == ClaimAssessmentRow.ai_answer_id)
        # 붙인 표에도 조직 조건을 따로 건다. 판정 행이 우리 것이라는 사실만으로
        # 답변 행까지 우리 것이 되지는 않는다 — `assert_tenant_scoped` 가 이 줄이
        # 없으면 통과시키지 않는다(ADR 0008).
        .where(AIAnswer.organization_id == principal.organization_id)
        .where(AIAnswer.observation_run_id == run_id)
        .order_by(ClaimAssessmentRow.created_at, ClaimAssessmentRow.id)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    return tuple(review_from_row(row) for row in session.scalars(statement))


__all__ = [
    "RULE_NAME_COULD_NOT_BE_ATTRIBUTED",
    "UnreadableAssessmentError",
    "assessment_from_held_mention",
    "assessment_id_for",
    "assessment_kinds_not_yet_produced",
    "new_assessment_row",
    "review_from_row",
    "reviews_for_run",
]
