"""점유율을 **실측에서** 만든다 — 사람이 숫자를 넣지 않는다.

## 무엇이 틀려 있었나

`sov.py` 는 완성되어 있었다. 인용 점유율, 언급 점유율, 승리 프롬프트율, 비교군 표기까지
전부 있었다. 그런데 그 입력(`ObservedVisibilityInput`)이 **요청 본문**이었다 — 사람이
"우리 12건, A병원 7건, B병원 3건" 을 손으로 적어 넣는 구조였다.

손으로 넣은 숫자는 잰 값처럼 보이지만 잰 값이 아니다. 그리고 그 숫자가 틀려도 아무도
모른다 — 대조할 원본이 없기 때문이다(0-A). 게다가 틀리는 방향은 한쪽으로 몰린다.
자기 숫자를 적는 사람은 자기에게 유리하게 적는다.

## 여기서 하는 일

관측 실행 하나(`observation_runs`)를 읽어 그대로 센다. 세는 규칙은 셋이다.

**응답 단위로 센다.** 한 답변이 브랜드를 네 번 불러도 1건이다. 되풀이가 노출을 늘리지
않는다(`ParticipantVisibility` 의 계약).

**확정된 것만 센다.** 동명 업체와 갈리지 않아 보류된 언급은 분자에 넣지 않는다. 우리
쪽만 후하게 세면 산술을 안 고치고 점유율이 오른다.

**승자는 반복 전체로 가린다.** 한 프롬프트에서 언급 응답 수가 가장 많은 참여자가
이긴다. 최다가 둘 이상이면 **판정하지 않는다** — 비긴 것을 누구 승리로도 세지 않고,
그 프롬프트는 분모에서도 빠진다(방법론: "비교 가능 프롬프트").

## 못 하는 것은 못 한다고 한다

경쟁사를 하나도 선언하지 않았으면 점유율을 만들지 않는다. 참여자가 우리뿐이면 모든
점유율이 100% 로 나오고, 그 100% 는 측정이 아니라 **비교 대상이 없다는 사실**이다.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.competitors.sov import ObservedVisibility, ParticipantVisibility
from veo.db.models.observation import (
    AIAnswer,
    AIEngine,
    BrandIdentity,
    Citation,
    EntityMention,
)
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import PromptSet as PromptSetRow


class ComparisonSetTooSmallError(ValueError):
    """비교할 상대가 없다.

    참여자가 우리뿐이면 모든 점유율이 100% 다. 그 값은 측정이 아니라 **비교 대상이 없다는
    사실**이고, 보고서에 100% 로 적으면 정반대로 읽힌다.
    """


@dataclass(frozen=True, slots=True)
class _Counts:
    mentioned: set[uuid.UUID]
    cited: set[uuid.UUID]


def observed_visibility_from_run(
    session: Session, principal: Principal, run_id: uuid.UUID
) -> ObservedVisibility:
    """관측 실행 하나를 점유율 입력으로.

    `MeasurementRejected` 대신 :class:`ComparisonSetTooSmallError` 를 던진다 — 이것은
    측정이 거부된 것이 아니라 **비교 집합이 성립하지 않는** 경우이고, 화면에서 안내할
    말이 다르다("경쟁사를 먼저 등록해 주십시오").
    """
    run = session.get(ObservationRunRow, run_id)
    if run is None or run.organization_id != principal.organization_id:
        raise LookupError(f"관측 실행을 찾을 수 없습니다: {run_id}")

    prompt_set = session.get(PromptSetRow, run.prompt_set_id)
    prompt_set_label = (
        f"{prompt_set.name} v{prompt_set.version}" if prompt_set is not None else "질문 집합"
    )

    # 선언된 참여자 — 우리와 경쟁사. **선언에서 온다**, 답변에서 발견한 이름이 아니다.
    # 답변에 나온 모든 상호를 참여자로 삼으면 비교군이 실행마다 달라지고, 그러면
    # 점유율이 무엇에 대한 비율인지 말할 수 없게 된다.
    identities = list(
        session.scalars(
            tenant_select(BrandIdentity, principal)
            .where(BrandIdentity.project_id == run.project_id)
            .where(BrandIdentity.is_active.is_(True))
            .order_by(BrandIdentity.competitor_id.is_(None).desc(), BrandIdentity.entity_key)
        )
    )
    if sum(1 for row in identities if row.competitor_id is not None) == 0:
        raise ComparisonSetTooSmallError(
            "이 프로젝트에 경쟁사가 등록되어 있지 않습니다. 비교 대상이 없으면 점유율은 "
            "언제나 100%로 나오는데, 그 값은 측정이 아니라 비교 대상이 없다는 사실입니다. "
            "경쟁사를 먼저 등록해 주십시오."
        )

    statement = (
        tenant_select(AIAnswer, principal)
        .where(AIAnswer.observation_run_id == run_id)
        .where(AIAnswer.is_valid_execution.is_(True))
    )
    assert_tenant_scoped(statement, principal.organization_id)
    answers = {row.id: row for row in session.scalars(statement)}

    mentions = (
        session.scalars(
            select(EntityMention)
            .where(EntityMention.ai_answer_id.in_(answers))
            .where(EntityMention.organization_id == principal.organization_id)
            # 보류는 아직 언급이 아니다. 여기서 세면 우리 쪽이 부풀고, 부푼 값은
            # 비율의 분자와 분모에 동시에 들어가 어느 쪽이 틀렸는지도 안 보인다.
            .where(EntityMention.needs_human_disambiguation.is_(False))
        ).all()
        if answers
        else []
    )

    counts: dict[str, _Counts] = defaultdict(lambda: _Counts(mentioned=set(), cited=set()))
    by_prompt: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for mention in mentions:
        answer = answers[mention.ai_answer_id]
        counts[mention.entity_key].mentioned.add(answer.id)
        by_prompt[answer.prompt_id][mention.entity_key] += 1

    # 인용은 **우리 도메인**만 확인할 수 있다. `citations.is_own_domain` 은 자사 기준으로
    # 계산된 값이고, 경쟁사 도메인은 그 표에서 구분되지 않는다. 그래서 경쟁사 인용은
    # 0 이 아니라 **아직 못 재는 값**이며, 그 사실은 아래 `scope` 문구가 말한다.
    own_key = next((row.entity_key for row in identities if row.competitor_id is None), None)
    if own_key is not None and answers:
        cited_answer_ids = set(
            session.scalars(
                select(Citation.ai_answer_id)
                .where(Citation.ai_answer_id.in_(answers))
                .where(Citation.organization_id == principal.organization_id)
                .where(Citation.is_own_domain.is_(True))
            )
        )
        counts[own_key].cited.update(
            cited_answer_ids & counts[own_key].mentioned,
        )

    wins = _winners(by_prompt)

    participants = tuple(
        ParticipantVisibility(
            key=row.entity_key,
            label_ko=row.display_name,
            is_own_brand=row.competitor_id is None,
            cited_answer_count=len(counts[row.entity_key].cited),
            mentioned_answer_count=len(counts[row.entity_key].mentioned),
            won_prompt_count=wins.won.get(row.entity_key, 0),
        )
        for row in identities
    )

    engine_labels = tuple(
        str(name)
        for name in session.scalars(
            select(AIEngine.display_name).where(
                AIEngine.provider.in_([str(engine) for engine in run.engines or ()])
            )
        )
    ) or tuple(str(engine) for engine in run.engines or ())

    return ObservedVisibility(
        prompt_set_label=prompt_set_label,
        engine_labels=engine_labels,
        observed_answer_count=len(answers),
        decided_prompt_count=wins.decided,
        participants=participants,
    )


@dataclass(frozen=True, slots=True)
class _Wins:
    won: dict[str, int]
    decided: int


def _winners(by_prompt: dict[uuid.UUID, dict[str, int]]) -> _Wins:
    """프롬프트마다 승자를 가린다 — 비기면 **아무도** 이기지 않는다.

    방법론의 승리 프롬프트율은 "자사가 경쟁사보다 높은 결과를 보인 프롬프트 / **비교
    가능** 프롬프트" 다. 비긴 프롬프트는 비교가 되지 않은 것이므로 분자에서 빼는 데
    그치지 않고 분모에서도 뺀다. 분모에 남겨 두면 비길수록 모두의 승률이 내려간다.
    """
    won: dict[str, int] = defaultdict(int)
    decided = 0
    for tally in by_prompt.values():
        if not tally:
            continue
        best = max(tally.values())
        leaders = [key for key, value in tally.items() if value == best]
        if len(leaders) != 1:
            continue
        won[leaders[0]] += 1
        decided += 1
    return _Wins(won=dict(won), decided=decided)


__all__ = ["ComparisonSetTooSmallError", "observed_visibility_from_run"]
