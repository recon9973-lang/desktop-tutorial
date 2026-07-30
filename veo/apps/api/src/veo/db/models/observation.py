"""Observed AI visibility, and reports.

This is the *measurement* side of GEO. It never merges with GEO readiness: readiness says
whether a page could be used by an answer engine, observation says what the engines
actually said. Two engines, two scores, two screens.

A single model response is a sample, not a market share. Every run stores the prompt,
engine, model version, locale, timestamp, raw answer and citations so a rate can be
recomputed and a confidence interval can be honest.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import UUID
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


class AIEngine(Base, TimestampMixin):
    """A registered answer engine. Search mode and account state change results materially."""

    __tablename__ = "ai_engines"
    __table_args__ = (UniqueConstraint("provider", "model", "search_mode"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    search_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DEFAULT", comment="DEFAULT | WEB_SEARCH | NO_SEARCH"
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DISABLED_NO_CREDENTIAL"
    )


class PromptSet(Base, OrganizationScopedMixin, TimestampMixin):
    """A versioned prompt universe. Comparisons are only fair against the same set."""

    __tablename__ = "prompt_sets"
    __table_args__ = (UniqueConstraint("project_id", "name", "version"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="ko-KR")
    generation_rule_ko: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="How prompts were chosen, and what was excluded and why."
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Prompt(Base, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "prompts"
    __table_args__ = (Index("ix_prompts_set_intent", "prompt_set_id", "intent"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    prompt_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(48), nullable=False)
    funnel: Mapped[str] = mapped_column(String(48), nullable=False)
    persona: Mapped[str | None] = mapped_column(String(80), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="ko-KR")
    subject_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NON_BRAND",
        comment="BRANDED | NON_BRAND | COMPETITOR | CATEGORY",
    )
    business_importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    expected_demand: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_demand_is_estimate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="True when the demand figure is an estimate rather than measured search volume.",
    )


class ObservationRun(Base, OrganizationScopedMixin, ImmutableMixin):
    """One batch of repeated prompt executions under fixed conditions."""

    __tablename__ = "observation_runs"
    __table_args__ = (Index("ix_observation_runs_project_created", "project_id", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_sets.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    repetitions_per_prompt: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    engines: Mapped[JsonArray] = json_column()
    competitor_ids: Mapped[JsonArray] = json_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    executions_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executions_valid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    measurement_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_breakdown: Mapped[JsonObject] = json_column()

    # Whether this run measured what it set out to measure.
    #
    # Without these, a run stopped by a budget ceiling is indistinguishable from one that
    # finished — the reader sees a rate over the executions that happened and has no way
    # to know that a third of the prompts were never asked. That is the exact misreading
    # the ceiling exists to prevent, so the truncation has to travel with the result.
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stopped_reason: Mapped[str | None] = mapped_column(
        String(48),
        nullable=True,
        comment=(
            "COMPLETED | BUDGET_EXHAUSTED | COST_UNMEASURABLE | CANCELLED "
            "| PROVIDER_UNAVAILABLE"
        ),
    )
    executions_planned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executions_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompts_below_repetition_floor: Mapped[JsonArray] = json_column()
    skipped_detail: Mapped[JsonObject] = json_column()


class AIAnswer(Base, OrganizationScopedMixin, ImmutableMixin):
    """A single engine response.

    The raw answer is sensitive: it is stored behind access control, referenced by hash,
    and must never appear in logs or observability traces in plaintext.
    """

    __tablename__ = "ai_answers"
    __table_args__ = (
        Index("ix_ai_answers_run_prompt", "observation_run_id", "prompt_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    observation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("observation_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="RESTRICT"), nullable=False
    )
    ai_engine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_engines.id", ondelete="RESTRICT"), nullable=False
    )
    repetition_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    search_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFAULT")
    account_state: Mapped[str | None] = mapped_column(String(48), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="ko-KR")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_valid_execution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    raw_answer_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_answer_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    citation_support: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment=(
            "이 응답에서 인용을 볼 수 있었는가. STRUCTURED 인 답변만 인용률의 분모에 "
            "들어간다. 볼 수 없었던 답변을 분모에 넣으면 인용률이 낮게 나오고, 그 낮은 "
            "값은 사이트 탓처럼 읽힌다 — 실제로는 그 모델이 출처를 알려주지 않은 것이다."
        ),
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment=(
            "제공자에게 실제로 청구되는 통화 그대로. 엔진과 가격표가 모두 USD 이므로 "
            "여기가 실측값이다. 값이 없는 것은 0원이 아니라 '모른다' 이며, 그 이유는 "
            "가격표 미설정·사용량 미보고·가격표 만료 중 하나다."
        ),
    )
    cost_krw: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment=(
            "환율을 아는 시점에만 채운다. 비어 있는 것이 기본이다 — 환율을 지어내면 "
            "고객에게 제시하는 금액이 틀리고, 나중에 환율이 바뀌면 과거 기록까지 "
            "달라진다. 재는 단위(USD)와 저장 단위를 같게 둔 것이 `cost_usd` 이고, "
            "이 칸은 표시용 환산값이다."
        ),
    )


class AnswerDocument(Base, OrganizationScopedMixin, ImmutableMixin):
    """원문 AI 답변 자체. `ai_answers` 가 가리키는 실제 내용.

    ## 왜 `ai_answers` 안이 아니라 옆 테이블인가

    원문은 민감하다. 조회·내보내기·로그에 딸려 나가면 안 되므로 분석용 본 테이블에는
    **가리키는 값(키·해시)만** 둔다(`test_raw_ai_answers_are_referenced_not_inlined`).
    이 테이블은 그 원문을 담되, 원문이 필요할 때만 따로 읽도록 갈라 놓은 자리다.

    ## 왜 파일이 아니라 DB 인가

    처음에는 로컬 파일에만 저장했다. 배포 환경의 컨테이너 파일시스템은 재배포마다
    초기화되므로, **다음 배포에서 모든 근거가 사라진다.** `ai_answers` 에는 키와 해시만
    남으니 "이 판정의 근거를 보여 달라" 에 답할 수 없게 된다 — 0-A 의 마지막 줄이
    무너지는 지점이다.

    오브젝트 스토리지(S3/MinIO)가 붙으면 그쪽으로 옮기는 것이 맞다. 그때까지는 이미
    있는 것 중 재배포를 견디는 유일한 자리가 DB 다.

    수정하지 않는다(`ImmutableMixin`). 원문이 바뀌면 그것은 더 이상 그때 받은 답변이
    아니다. 읽을 때 해시를 다시 계산해 확인한다.
    """

    __tablename__ = "answer_documents"
    __table_args__ = (
        UniqueConstraint("organization_id", "object_key", name="uq_answer_documents_key"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        comment="답변 기록의 정규 JSON 바이트. 해시는 이 바이트에 대해 계산한다.",
    )


class Citation(Base, OrganizationScopedMixin, ImmutableMixin):
    __tablename__ = "citations"
    __table_args__ = (Index("ix_citations_answer_domain", "ai_answer_id", "domain"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    ai_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_own_domain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True
    )


class EntityMention(Base, OrganizationScopedMixin, ImmutableMixin):
    """A brand mention inside one answer.

    One answer counts as at most one mention event per brand — repeating a name does not
    make a brand more visible. The raw occurrence count is kept separately.
    """

    __tablename__ = "entity_mentions"
    __table_args__ = (
        UniqueConstraint("ai_answer_id", "entity_key"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    ai_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_key: Mapped[str] = mapped_column(String(200), nullable=False)
    is_own_brand: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True
    )
    raw_occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    needs_human_disambiguation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Same-name brands go to a manual queue rather than being guessed.",
    )
    review_state: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_REVIEWED")


class ClaimAssessment(Base, OrganizationScopedMixin, TimestampMixin):
    """A risk finding about what an engine said.

    Automated judgement is a candidate, not a verdict: ``review_state`` tracks human
    confirmation separately, and both are shown.
    """

    __tablename__ = "claim_assessments"

    id: Mapped[uuid.UUID] = uuid_pk()
    ai_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    assessment_type: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        comment="CLAIM_ACCURACY | CITATION_ENTAILMENT | CITATION_COMPLETENESS | "
        "ENTITY_DISAMBIGUATION | RECOMMENDATION | SENTIMENT | STALENESS",
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    automated_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    automated_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    llm_prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_state: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_REVIEW")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting_citation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("citations.id", ondelete="SET NULL"), nullable=True
    )


class Report(Base, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    audience: Mapped[str] = mapped_column(
        String(32), nullable=False, default="BUSINESS",
        comment="BUSINESS | MARKETING | DEVELOPER — one measurement, three readings.",
    )


class ReportVersion(Base, OrganizationScopedMixin, ImmutableMixin):
    """An immutable snapshot. Regenerating produces a new version, never an edit."""

    __tablename__ = "report_versions"
    __table_args__ = (UniqueConstraint("report_id", "version_number"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    measurement_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    measurement_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    included_run_ids: Mapped[JsonArray] = json_column()
    scoring_versions: Mapped[JsonObject] = json_column()
    content: Mapped[JsonObject] = json_column()
    disclosures_ko: Mapped[JsonArray] = json_column()
    export_formats: Mapped[JsonArray] = json_column()
    public_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    public_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BrandIdentity(Base, OrganizationScopedMixin, TimestampMixin):
    """The declared facts that tell one business apart from another of the same name.

    A brand name alone is often not an identifier. "서울치과" is dozens of practices;
    "중앙병원" is more. Measured against a name alone, every mention of such a customer
    goes to human review — correct, but it means the product cannot measure them.

    Measured effect on a generic name (see ``tests/observations/detection``):

        name only                          0.40  -> review
        + district                         0.60  -> review
        + district + phone                 0.85  -> confirmed
        + district + phone + distinguisher 1.00  -> confirmed

    So a district alone does not settle it and a phone number usually does. That is worth
    knowing when onboarding a customer: the five minutes spent entering a phone number is
    the difference between a measurable account and a review queue.

    The same table serves the customer and their competitors, because Share of Voice is
    only honest when both sides are described — and therefore detected — identically.
    Giving our own brand richer identifiers than a rival's would inflate our share without
    touching the arithmetic.
    """

    __tablename__ = "brand_identities"
    __table_args__ = (
        UniqueConstraint("project_id", "entity_key", name="uq_brand_identity_entity"),
        Index("ix_brand_identities_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    #: Null for the customer's own brand; set for a declared competitor.
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=True
    )
    entity_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[JsonArray] = json_column()

    #: Administrative districts, neighbourhoods, stations, landmarks — whatever an AI
    #: answer would plausibly say about where this business is.
    address_terms: Mapped[JsonArray] = json_column()
    #: Normalised at write time so 02-1234-5678 and 0212345678 are one number.
    phone_numbers: Mapped[JsonArray] = json_column()
    #: Anything else that separates this business from its namesakes — a signature
    #: treatment, opening hours nobody else keeps, a founder's name.
    distinguishing_terms: Mapped[JsonArray] = json_column()
    own_domains: Mapped[JsonArray] = json_column()

    #: Set when an operator has judged the name generic, overriding the heuristic.
    name_is_ambiguous: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
