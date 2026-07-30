"""작업을 요청 밖에서 돌린다.

## 이것은 Celery 가 아니다

배포 환경에 브로커(Redis)가 없다. 그래서 여기서는 **API 프로세스 안의 배경 스레드**로
돌린다. 없는 것을 있는 척하지 않기 위해 그 사실을 이름과 문서 양쪽에 적어 둔다.

이 방식이 실제로 고치는 것: 관측 한 번이 수 분 걸려도 **요청은 즉시 돌아온다.**
게이트웨이가 끊는 일이 없어지고, 사용자는 진행률을 물어볼 수 있다.

이 방식이 고치지 못하는 것: **프로세스가 재시작하면 돌던 작업은 죽는다.** 재시도도
없고, 여러 대로 나눠 돌리지도 못한다. 그 대가는 :mod:`veo.jobs.service` 의
`STALE_AFTER` 로 드러낸다 — 소식이 끊긴 작업은 "실행 중" 이 아니라 "알 수 없음" 이다.

브로커가 생기면 :func:`run_detached` 만 Celery 호출로 바꾸면 된다. 작업 계약과 조회
경로는 그대로다.

## 오류를 옮길 때

작업 안에서 난 예외를 그대로 `safe_error_message` 에 넣으면 안 된다. 공급자 오류에는
URL·키 조각·내부 호스트명이 섞여 들어온다. 여기서는 **닫힌 목록의 문장**만 내보내고,
원문은 로그로만 남긴다.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, final

from sqlalchemy.orm import Session

from veo.db.session import session_scope
from veo.jobs import service

logger = logging.getLogger(__name__)


@final
@dataclass(frozen=True, slots=True)
class JobOutcome:
    """작업이 끝나면서 남기는 것.

    `is_partial` 을 본문이 직접 말하게 한 이유가 있다. 예산에 걸려 절반만 실행된 관측은
    실패가 아니지만 성공도 아니다. 둘 중 하나로 접으면 그 사실이 사라진다.
    """

    result_run_id: uuid.UUID | None = None
    is_partial: bool = False


#: 작업 본문. 세션과 작업 id 를 받고 결과를 돌려준다.
JobWork = Callable[[Session, uuid.UUID], JobOutcome]

#: 사용자에게 보여줄 수 있는 문장. 예외 원문은 절대 여기 오지 않는다.
UNEXPECTED_KO: Final = (
    "작업 중 예기치 못한 오류가 발생했습니다. 기술팀이 로그로 원인을 확인할 수 "
    "있습니다. 같은 조건으로 다시 실행해 보시고, 반복되면 알려주십시오."
)


class JobFailure(Exception):
    """작업 본문이 스스로 실패를 선언할 때 쓴다.

    이 예외의 메시지는 **사용자에게 그대로 보인다.** 그래서 본문에서 던질 때
    보여줘도 되는 문장인지 확인하고 던져야 한다. 그 판단을 못 하겠으면 그냥 다른
    예외를 던져라 — 그때는 위 `UNEXPECTED_KO` 로 덮인다.
    """

    def __init__(self, error_code: str, message_ko: str, *, retryable: bool = False) -> None:
        super().__init__(message_ko)
        self.error_code = error_code
        self.message_ko = message_ko
        self.retryable = retryable


def execute(job_id: uuid.UUID, work: JobWork) -> None:
    """작업 하나를 처음부터 끝까지 돌리고 결과를 기록한다.

    **자기 세션을 연다.** 요청의 세션을 배경 스레드로 넘기면 안 된다 — SQLAlchemy 세션은
    스레드 사이에서 안전하지 않고, 요청이 끝나면 그 세션은 닫힌다.

    상태 기록과 작업 본문은 **세션을 나눈다.** 본문이 실패해 롤백될 때 "실패했다" 는
    기록까지 함께 사라지면, 그 작업은 영원히 `RUNNING` 으로 남는다.
    """
    with session_scope() as session:
        service.begin(session, job_id)

    try:
        with session_scope() as session:
            outcome = work(session, job_id)
    except JobFailure as failure:
        logger.warning("job %s failed: %s", job_id, failure.error_code)
        with session_scope() as session:
            service.fail(
                session,
                job_id,
                error_code=failure.error_code,
                safe_message_ko=failure.message_ko,
                retryable=failure.retryable,
            )
        return
    except Exception:
        # 원문은 로그로만. 화면과 DB 에는 닫힌 목록의 문장만 간다.
        logger.exception("job %s raised", job_id)
        with session_scope() as session:
            service.fail(
                session,
                job_id,
                error_code="UNEXPECTED_ERROR",
                safe_message_ko=UNEXPECTED_KO,
                internal_error_ref=str(job_id),
            )
        return

    with session_scope() as session:
        service.succeed(
            session,
            job_id,
            result_run_id=outcome.result_run_id,
            partial=outcome.is_partial,
        )


def run_detached(job_id: uuid.UUID, work: JobWork) -> threading.Thread:
    """작업을 배경 스레드에서 시작하고 즉시 돌아온다.

    데몬 스레드다. 프로세스를 종료할 때 이 스레드가 붙잡지 않는다 — 붙잡게 두면 배포가
    멈춘다. 대신 그렇게 죽은 작업은 `STALE_AFTER` 로 드러난다.
    """
    thread = threading.Thread(
        target=execute,
        args=(job_id, work),
        name=f"veo-job-{job_id}",
        daemon=True,
    )
    thread.start()
    return thread


__all__ = [
    "UNEXPECTED_KO",
    "JobFailure",
    "JobOutcome",
    "JobWork",
    "execute",
    "run_detached",
]
