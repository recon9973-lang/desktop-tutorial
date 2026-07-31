"""관측을 요청 밖에서 돌리기 위한 작업 본문.

라우터가 아니라 여기에 두는 이유가 둘이다.

1. **라우터는 HTTP 를 다루는 곳이다.** 배경에서 도는 일은 요청도 응답도 없다.
2. 라우터 모듈은 `veo.api` 를 거쳐 자기 자신으로 돌아오는 순환 고리 위에 있어서,
   테스트가 직접 열면 깨진다. 작업 본문은 그 고리 밖에 있어야 한다.

여기서 던지는 :class:`JobFailure` 의 메시지는 **그대로 화면에 간다.** 공급자 예외를
그대로 옮기면 자격증명 조각과 내부 호스트명이 함께 나가므로, 우리가 뜻을 아는 예외만
문장으로 바꾸고 나머지는 일반 문구로 덮는다(`veo.jobs.execution` 참조).
"""

from __future__ import annotations

import uuid
from typing import Final

from sqlalchemy.orm import Session

from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.jobs import service as jobs
from veo.jobs.execution import JobFailure, JobOutcome, JobWork
from veo.observations.execution import (
    BrandIdentityMissingError,
    EngineChoice,
    execute_observation,
)
from veo.observations.providers.registry import ProviderRegistry, UnknownEngineError
from veo.observations.providers.storage import RecordedAnswerStore
from veo.observations.runner import RepetitionFloorError
from veo.observations.service import get_prompt_set

#: 화면이 "지금 어디쯤인가" 를 말할 수 있도록 미리 알려주는 단계들.
OBSERVATION_STAGES: Final = ("질문 준비", "AI 엔진 호출", "인용·언급 판별", "저장")


def observation_work(
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    roles: frozenset[Role],
    session_id: str,
    prompt_set_id: uuid.UUID,
    choices: list[EngineChoice],
    repetitions: int,
    allow_below_floor: bool,
    registry: ProviderRegistry | None = None,
    store: RecordedAnswerStore | None = None,
) -> JobWork:
    """배경에서 돌 실제 관측 작업을 만든다.

    요청의 :class:`Principal` 객체를 그대로 넘기지 않고 **값으로 풀어서 다시 만든다.**
    요청 객체를 스레드 밖으로 들고 나가면 그 수명이 요청보다 길어지고, 그때 무엇이
    아직 살아 있는지 추적하기 어려워진다. 권한은 값이므로 값으로 옮긴다.
    """

    def work(session: Session, job_id: uuid.UUID) -> JobOutcome:
        principal = Principal(
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            session_id=session_id,
        )
        prompt_set_row = get_prompt_set(session, principal, prompt_set_id)
        if prompt_set_row is None:
            raise JobFailure(
                "PROMPT_SET_NOT_FOUND",
                "질문 집합을 찾을 수 없습니다. 실행을 시작한 뒤 지워졌을 수 있습니다.",
            )

        jobs.advance(session, job_id, progress=0.1, stage=OBSERVATION_STAGES[1])

        def report(done: int, total: int) -> None:
            """실행기가 반복 간격을 기다리는 동안 "아직 살아 있다" 를 남긴다.

            같은 질문의 반복은 일부러 간격을 두고 던지므로(`RepetitionSpread`) 실행은
            분 단위로 길어진다. 그동안 아무 흔적도 안 남기면 `is_stale()` 이 20분 뒤
            이 작업을 **알 수 없음**으로 표시한다 — 멀쩡히 도는 일이 고장으로 보인다.
            """
            if total <= 0:
                return
            # 0.1 에서 시작해 0.9 까지. 마지막 0.1 은 저장 몫으로 남긴다.
            jobs.advance(
                session,
                job_id,
                progress=0.1 + 0.8 * (done / total),
                stage=f"{OBSERVATION_STAGES[1]} ({done}/{total}, 반복 간격 대기 중)",
            )

        try:
            row = execute_observation(
                session,
                principal,
                prompt_set_row=prompt_set_row,
                engines=choices,
                repetitions=repetitions,
                allow_below_floor=allow_below_floor,
                registry=registry,
                store=store,
                on_progress=report,
            )
        except BrandIdentityMissingError as exc:
            raise JobFailure("BRAND_IDENTITY_MISSING", str(exc)) from exc
        except RepetitionFloorError as exc:
            raise JobFailure("REPETITION_FLOOR", str(exc)) from exc
        except UnknownEngineError as exc:
            raise JobFailure("UNKNOWN_ENGINE", str(exc)) from exc

        jobs.advance(session, job_id, progress=0.95, stage=OBSERVATION_STAGES[3])
        # 부분 실행을 성공으로 접지 않는다. 절반만 돈 관측 위에서 계산한 노출률은
        # 분모가 틀린 값이고, 그 사실이 작업 기록에서 사라지면 아무도 모른다.
        return JobOutcome(result_run_id=row.id, is_partial=not row.is_complete)

    return work


__all__ = ["OBSERVATION_STAGES", "observation_work"]
