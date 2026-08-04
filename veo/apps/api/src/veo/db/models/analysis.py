"""Jobs, scans, evidence, scoring versions and score results.

Every score row here stores the specification version, checksum, applicable denominator,
calculation trace and confidence alongside the number. A score without that context is
not a VEO score.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from veo.db.base import (
    Base,
    ImmutableMixin,
    JsonArray,
    JsonObject,
    OrganizationScopedMixin,
    TimestampMixin,
    json_column,
    uuid_pk,
)


class Job(Base, OrganizationScopedMixin, TimestampMixin):
    """A unit of asynchronous work. Long analyses never run inside a request."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "type",
            "idempotency_key",
            name="uq_jobs_org_type_idempotency_key",
        ),
        Index("ix_jobs_status_created_at", "status", "created_at"),
        CheckConstraint("progress >= 0 AND progress <= 1", name="progress_unit_interval"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    surface: Mapped[str] = mapped_column(String(16), nullable=False, default="CONSOLE")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", index=True)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stages: Mapped[JsonArray] = json_column()

    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parameters: Mapped[JsonObject] = json_column()

    scoring_spec_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scoring_spec_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    safe_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_error_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)

    result_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    partial_result_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    estimated_cost_krw: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_krw: Mapped[float | None] = mapped_column(Float, nullable=True)


class Scan(Base, OrganizationScopedMixin, TimestampMixin):
    """A configured, repeatable analysis. Its executions are ScanRuns."""

    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="SEO | GEO_READINESS | GEO_OBSERVATION | KEYWORD"
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="SINGLE_URL")
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuration: Mapped[JsonObject] = json_column()
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ScanRun(Base, OrganizationScopedMixin, ImmutableMixin):
    """One immutable execution of a scan. Results are appended, never overwritten."""

    __tablename__ = "scan_runs"
    __table_args__ = (Index("ix_scan_runs_scan_created", "scan_id", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    surface: Mapped[str] = mapped_column(String(16), nullable=False, default="CONSOLE")
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    collector_version: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_profile: Mapped[str] = mapped_column(String(16), nullable=False, default="MOBILE")

    urls_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    urls_collected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    provider_states: Mapped[JsonObject] = json_column()
    partial_reasons: Mapped[JsonArray] = json_column()

    #: 이 진단을 실행한 사람. 예약 실행처럼 사람이 없는 경우가 있어 nullable 이다.
    #:
    #: 사용자가 지워져도 **기록은 남는다**(``ON DELETE SET NULL``). 퇴사자 계정을 정리하다
    #: 지난 진단 이력이 함께 사라지면, 고객에게 낸 보고서의 출처를 설명할 수 없게 된다.
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="진단을 실행한 사용자. 예약 실행이면 NULL.",
    )

    #: 이 실행이 그때 실제로 돌려준 보고서 전문.
    #:
    #: 정규화된 ``check_results``·``issues`` 와 겹치지만, 겹치는 것이 목적이다. 저쪽은
    #: 추이와 이슈 수명을 **질의**하기 위한 것이고, 이쪽은 "그때 화면에 무엇이 떴는지"
    #: 를 **그대로** 다시 보여주기 위한 것이다. 조치 문구는 수집기가 발견한 값을 넣어
    #: 그때그때 만들어 내므로(예: 문제가 된 URL 이 문장 안에 있다) 명세로부터 되살릴 수
    #: 없다. 스냅샷이 없으면 다시 열었을 때 문장이 달라지거나 사라진다.
    report_snapshot: Mapped[JsonObject | None] = mapped_column(
        JSONB, nullable=True, comment="그때 반환한 ScanPayload 전문."
    )

    #: 이 점수가 **어떤 조건에서** 나왔는지.
    #:
    #: 명세·수집기 판·본 페이지 수·언어·기기·렌더링 방식·응답한 공급자·측정 시각. 이것이
    #: 없으면 점수는 단위 없는 숫자이고, 두 실행을 나란히 놓을 수 있는지 판단할 근거가
    #: 없다 — 조건이 달라서 생긴 차이가 사이트가 나아졌다는 뜻으로 읽힌다.
    #:
    #: 이 칸이 생기기 전에 저장된 실행은 ``NULL`` 이다. 그럴듯한 값으로 채우지 않는다.
    #: 어떻게 쟀는지 모르는 실행은 실제로 비교할 수 없다.
    measurement_conditions: Mapped[JsonObject | None] = mapped_column(
        JSONB, nullable=True, comment="MeasurementConditions.as_dict(). 옛 실행은 NULL."
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )


class Evidence(Base, OrganizationScopedMixin, ImmutableMixin):
    """Raw material behind every finding. Secrets and cookies are excluded on write."""

    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_run_kind", "scan_run_id", "kind"),
        Index("ix_evidence_run_evidence_id", "scan_run_id", "evidence_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scan_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    #: 판정과 이슈가 근거를 부를 때 쓰는 이름 (``kind:content_hash 앞 16자``).
    #:
    #: 이 칸이 없었다. ``check_results.evidence_ids`` 와 ``issues.evidence_ids`` 는
    #: 이 이름을 저장하는데 근거 행에는 그 이름이 없어서, **저장된 모든 근거 참조가
    #: 어디도 가리키지 않았다**. 근거는 56줄 있는데 그중 부를 수 있는 것이 0줄이었다.
    #: 감사할 수 없는 지적은 소문이다.
    evidence_id: Mapped[str] = mapped_column(
        String(96),
        nullable=False,
        server_default="",
        comment="판정·이슈가 근거를 부를 때 쓰는 이름. kind:content_hash[:16].",
    )
    kind: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        comment="http_response | raw_html | rendered_dom | robots_txt | sitemap_document | "
        "lighthouse_run | crux_record | provider_response | screenshot | external_source",
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Object storage key for large payloads."
    )
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(48), nullable=False, default="VEO_CRAWLER")
    detail: Mapped[JsonObject] = json_column()


class FetchCapture(Base, OrganizationScopedMixin, ImmutableMixin):
    """진단이 **실제로 받은 응답**. 판정이 아니라 원자료다.

    이것이 없어서 하루를 썼다. venomad.com 이 15~27점으로 나왔는데, "무엇을 받았길래
    그 점수인가" 에 답할 방법이 없었다. 남아 있던 것은 sha256 해시 64자와 수집기가
    고른 2,000자 발췌뿐이었다 — 사람이 열어 볼 수 있는 것이 아니었다. 그래서 코드를
    읽고 판정에서 거꾸로 추측하는 데 감사관 넷과 하루가 들었고, 그러고도 확정하지
    못했다.

    아무 AI에게 주소를 주면 페이지를 열어 보고 답한다. 우리는 측정기라면서 측정한
    것을 안 갖고 있었다.

    `evidence.storage_key`("큰 자료는 객체 저장소에") 가 처음부터 선언돼 있었지만
    채우는 코드가 없었다. 객체 저장소를 붙이는 것은 별건이므로, 여기서는 **DB 에 상한을
    두고 그대로 담는다.** 상한을 넘으면 앞부분만 담고 `truncated` 로 그 사실을 남긴다 —
    잘린 것을 전부인 척하지 않는다.

    보관 기간: 사이트마다 가장 최근 진단 한 번분. 문제를 볼 수 있으면서 용량은 최소다.
    """

    __tablename__ = "fetch_captures"
    __table_args__ = (Index("ix_fetch_captures_run_url", "scan_run_id", "url"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scan_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    #: 요청한 주소와 최종 도달한 주소. 리다이렉트로 다른 곳에 떨어졌으면 여기서 보인다.
    final_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    #: 응답 헤더. 자격증명·쿠키는 수집 단계에서 이미 걸러진 것만 온다.
    headers: Mapped[JsonObject] = json_column()
    #: 우리가 **보낸** 헤더. 봇 차단을 만났을 때 무엇을 보내서 그랬는지 알아야 한다.
    request_headers: Mapped[JsonObject] = json_column()
    body: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    #: 원본의 실제 크기. `len(body)` 와 다르면 잘린 것이다.
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: 이 응답을 문서로 읽었는가. 못 읽었으면 그 사유(0-K).
    read_failure_ko: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScoringVersion(Base, ImmutableMixin):
    """A VEO-LAB specification as published.

    Published rows are never edited. A change is a new version, and re-scoring old data
    keeps both the original and the recomputed number.
    """

    __tablename__ = "scoring_versions"
    __table_args__ = (UniqueConstraint("spec_id", "semantic_version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    spec_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    semantic_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    specification: Mapped[JsonObject] = json_column()
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    compatible_collector_versions: Mapped[JsonArray] = json_column()
    golden_fixture_results: Mapped[JsonObject] = json_column()


class CheckResult(Base, OrganizationScopedMixin, ImmutableMixin):
    """One check outcome, with the evidence that produced it."""

    __tablename__ = "check_results"
    __table_args__ = (
        Index("ix_check_results_run_check", "scan_run_id", "check_id"),
        CheckConstraint(
            "affected_weight <= evaluated_weight", name="affected_within_evaluated"
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_unit_interval"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scan_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("url_records.id", ondelete="SET NULL"), nullable=True
    )
    check_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="PASS | WARNING | FAIL | NOT_APPLICABLE | UNKNOWN"
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    affected_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evaluated_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    not_applicable_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    unknown_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_value: Mapped[JsonObject] = json_column()
    evidence_ids: Mapped[JsonArray] = json_column()
    #: 이 검사에 걸린 / 판정한 페이지 URL 목록 — 페이지별 점수 재집계의 기반.
    #:
    #: "canonical 문제 103장" 만 저장하면 **어느** 103장인지가 사라져, 페이지별 점수를
    #: 내려면 재크롤이 필요해진다. 수집기가 이미 아는 목록을 여기 남긴다.
    #: NULL 은 이 칸이 생기기 전의 실행이다 — 채워 넣지 않는다(모른다 ≠ 없었다).
    affected_urls: Mapped[JsonArray | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="이 검사에 걸린 페이지 URL 목록. 옛 실행은 NULL(기록되지 않음).",
    )
    evaluated_urls: Mapped[JsonArray | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="이 검사가 판정한 페이지 URL 목록. 옛 실행은 NULL(기록되지 않음).",
    )


class ScoreResult(Base, OrganizationScopedMixin, ImmutableMixin):
    """A computed score with everything needed to defend it.

    ``score_before_caps`` is kept beside ``score`` so a customer can see both the raw
    arithmetic and the ceiling that a catastrophic fault imposed on it.
    """

    __tablename__ = "score_results"
    __table_args__ = (
        UniqueConstraint("scan_run_id", "spec_id", "spec_version"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="score_range"),
        CheckConstraint("coverage >= 0 AND coverage <= 1", name="coverage_unit_interval"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_unit_interval"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    scan_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scan_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spec_id: Mapped[str] = mapped_column(String(120), nullable=False)
    spec_version: Mapped[str] = mapped_column(String(32), nullable=False)
    spec_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SCORED")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_before_caps: Mapped[float | None] = mapped_column(Float, nullable=True)
    band_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    coverage: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    effective_weight_total: Mapped[float] = mapped_column(Float, nullable=False)

    category_scores: Mapped[JsonArray] = json_column()
    applied_caps: Mapped[JsonArray] = json_column()
    gates: Mapped[JsonArray] = json_column()
    calculation_trace: Mapped[JsonObject] = json_column()

    recomputed_from_score_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("score_results.id", ondelete="SET NULL"),
        nullable=True,
        comment="Set when an older run was re-scored under a newer spec. Both rows survive.",
    )


class Issue(Base, OrganizationScopedMixin, TimestampMixin):
    """A finding routed to a person, tracked to verified resolution."""

    __tablename__ = "issues"
    __table_args__ = (Index("ix_issues_project_state", "project_id", "state"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_seen_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_runs.id", ondelete="SET NULL"), nullable=True
    )
    last_seen_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_runs.id", ondelete="SET NULL"), nullable=True
    )
    check_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    title_ko: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact_ko: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_url_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sample_urls: Mapped[JsonArray] = json_column()
    evidence_ids: Mapped[JsonArray] = json_column()
    remediation_owner: Mapped[str] = mapped_column(String(32), nullable=False, default="DEVELOPER")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    regression_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FixRecommendation(Base, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "fix_recommendations"

    id: Mapped[uuid.UUID] = uuid_pk()
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_ko: Mapped[str] = mapped_column(Text, nullable=False)
    developer_steps_ko: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_effort: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reverification_rule: Mapped[JsonObject] = json_column()
    generated_by: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="RULE",
        comment="RULE | LLM_ASSISTED | HUMAN — an LLM may explain a fix, never decide a score.",
    )
    llm_prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_state: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_REVIEWED")


class VerificationRun(Base, OrganizationScopedMixin, ImmutableMixin):
    """A targeted re-check after a fix. Kept separate from the original measurement."""

    __tablename__ = "verification_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_runs.id", ondelete="SET NULL"), nullable=True
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="RESOLVED | STILL_FAILING | INCONCLUSIVE"
    )
    detail: Mapped[JsonObject] = json_column()


class APIUsageEvent(Base, ImmutableMixin):
    """Per-call usage and cost. Payloads are never stored here — only shapes and counts."""

    __tablename__ = "api_usage_events"
    __table_args__ = (
        Index(
            "ix_api_usage_org_provider_created",
            "organization_id",
            "provider",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    was_cache_hit: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="캐시 응답이었는가. NULL 은 판단 근거가 없었다는 뜻 — False(새로 잼)와 다르다.",
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_krw: Mapped[float | None] = mapped_column(Float, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
