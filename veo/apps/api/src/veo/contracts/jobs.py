"""The job contract shared by the API, the worker and both front-end surfaces."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from veo.contracts.enums import (
    CancellationReason,
    ErrorCode,
    JobStatus,
    JobType,
    Surface,
)

_STRICT = ConfigDict(extra="forbid")


class JobStage(BaseModel):
    model_config = _STRICT

    key: str
    label_ko: str
    status: JobStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    items_done: int = 0
    items_total: int | None = None


class JobDescriptor(BaseModel):
    """Everything a caller may know about a job.

    ``idempotency_key`` plus ``input_hash`` make at-least-once delivery safe: a repeated
    submission returns the original job instead of starting a second one.
    """

    model_config = _STRICT

    job_id: str
    type: JobType
    surface: Surface
    status: JobStatus
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    current_stage: str | None = None
    stages: list[JobStage] = Field(default_factory=list)

    organization_id: str | None = None
    project_id: str | None = None
    requested_by: str | None = None

    idempotency_key: str | None = None
    input_hash: str
    scoring_spec_id: str | None = None
    scoring_spec_version: str | None = None

    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime | None = None

    attempts: int = 0
    max_attempts: int = 3
    next_retry_at: datetime | None = None

    error_code: ErrorCode | None = None
    safe_error_message: str | None = None
    internal_error_ref: str | None = None

    result_run_id: str | None = None
    partial_result_available: bool = False

    # Real counts behind PARTIAL_SUCCESS. A run that gathered 80 of 100 pages must be
    # able to say so — "partial" without numbers is not usable information.
    units_planned: int | None = None
    units_attempted: int | None = None
    units_collected: int | None = None

    # Why a job was cancelled. An enum, never free text: provider messages forwarded
    # verbatim are how credentials and internal hostnames end up in front of customers.
    cancellation_reason: CancellationReason | None = None

    estimated_cost_krw: float | None = None
    actual_cost_krw: float | None = None

    def is_terminal(self) -> bool:
        from veo.contracts.enums import TERMINAL_JOB_STATUSES

        return self.status in TERMINAL_JOB_STATUSES


class JobSubmission(BaseModel):
    """Common request shape for starting work."""

    model_config = _STRICT

    type: JobType
    idempotency_key: str | None = Field(
        default=None,
        max_length=200,
        description="Client-supplied key. Repeating it returns the existing job.",
    )
    parameters: dict[str, Any] = Field(default_factory=dict)
