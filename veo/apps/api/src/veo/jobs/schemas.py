"""작업 하나를 화면이 오해할 수 없는 모양으로 편다."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class JobPayload(BaseModel):
    """진행 중이거나 끝난 작업 하나.

    `status` 만 보고 화면을 그리지 마십시오. **소식이 끊긴 작업도 `RUNNING` 입니다.**
    `is_stale` 이 참이면 그 작업이 아직 도는지 저희도 알지 못합니다 — 그때 "실행 중"
    이라고 표시하면 사용자는 오지 않을 결과를 기다립니다.
    """

    model_config = _FROZEN

    id: uuid.UUID
    type: str
    status: str = Field(
        description=(
            "`QUEUED` 대기 · `RUNNING` 실행 중 · `SUCCEEDED` 완료 · "
            "`PARTIAL_SUCCESS` 일부만 실행 · `FAILED_FINAL` 실패 · `CANCELLED` 취소."
        )
    )
    is_stale: bool = Field(
        description=(
            "소식이 끊긴 미완료 작업인가. 참이면 **끝났는지 아닌지 알 수 없다**는 "
            "뜻이며, 실행 중과 같게 그리면 안 됩니다."
        )
    )
    progress: float = Field(ge=0.0, le=1.0)
    current_stage: str | None
    stages: list[str] = Field(description="이 작업이 거치는 단계들입니다.")

    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    attempts: int
    error_code: str | None
    safe_error_message: str | None = Field(
        description=(
            "사용자에게 보여도 되는 문장만 들어갑니다. 공급자 오류 원문은 여기 오지 "
            "않습니다 — 자격증명과 내부 주소가 섞여 있기 때문입니다."
        )
    )

    result_run_id: uuid.UUID | None = Field(
        description="끝났다면 결과 행의 id 입니다. 이것으로 결과를 조회합니다."
    )
    partial_result_available: bool

    note_ko: str = Field(
        description="이 상태를 사람에게 설명하는 문장입니다. 비어 있으면 덧붙일 말이 없습니다."
    )


class JobListPayload(BaseModel):
    model_config = _FROZEN

    items: list[JobPayload]
    total: int


__all__ = ["JobListPayload", "JobPayload"]
