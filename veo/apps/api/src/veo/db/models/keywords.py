"""Naver keyword intelligence.

The three Naver data families never share a column:

* ``NAVER_SEARCH_AD``  — official absolute monthly search counts, clicks, CTR, competition.
* ``NAVER_DATALAB``    — a *relative* interest index. Not a search count, ever.
* ``CALCULATED``       — VEO's own arithmetic, always labelled with its formula version.

Zero, missing, provider-suppressed and below-threshold are distinct facts and are stored
as distinct facts. A suppressed value is never written as 0.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
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


class KeywordQuery(Base, OrganizationScopedMixin, ImmutableMixin):
    """One lookup request, kept so a figure can always be traced to when it was asked."""

    __tablename__ = "keyword_queries"
    __table_args__ = (Index("ix_keyword_queries_org_created", "organization_id", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    surface: Mapped[str] = mapped_column(String(16), nullable=False, default="CONSOLE")
    original_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="ko-KR")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_state: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    error_code: Mapped[str | None] = mapped_column(String(48), nullable=True)


class KeywordMetric(Base, OrganizationScopedMixin, ImmutableMixin):
    """Official Naver Search Ad figures for one keyword at one point in time.

    Each numeric column has a paired ``*_quality`` column recording whether the value is
    exact, rounded, a range, suppressed by the provider, below its reporting threshold, or
    simply missing. Reading a count without reading its quality is a bug.
    """

    __tablename__ = "keyword_metrics"
    __table_args__ = (
        UniqueConstraint("keyword_query_id", "normalized_keyword"),
        Index("ix_keyword_metrics_keyword_collected", "normalized_keyword", "collected_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    keyword_query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_keyword: Mapped[str] = mapped_column(String(255), nullable=False)

    source: Mapped[str] = mapped_column(String(32), nullable=False, default="NAVER_SEARCH_AD")
    api_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    was_cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    monthly_pc_searches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_pc_searches_quality: Mapped[str] = mapped_column(
        String(32), nullable=False, default="MISSING"
    )
    monthly_mobile_searches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_mobile_searches_quality: Mapped[str] = mapped_column(
        String(32), nullable=False, default="MISSING"
    )
    monthly_total_searches: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="CALCULATED from the two device figures, not provided."
    )

    avg_pc_clicks: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_mobile_clicks: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_pc_ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_mobile_ctr: Mapped[float | None] = mapped_column(Float, nullable=True)

    competition_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ad_depth: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Ad slots observed. Advertising competition only."
    )

    provider_raw: Mapped[JsonObject] = json_column()
    partial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RelatedKeyword(Base, OrganizationScopedMixin, ImmutableMixin):
    __tablename__ = "related_keywords"
    __table_args__ = (
        Index("ix_related_keywords_query_rank", "keyword_query_id", "source_rank"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    keyword_query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seed_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    related_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="NAVER_SEARCH_AD")
    source_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_total_searches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_quality: Mapped[str] = mapped_column(String(32), nullable=False, default="MISSING")


class KeywordTrend(Base, OrganizationScopedMixin, ImmutableMixin):
    """DataLab relative interest. Stored apart from counts so it can never be mistaken for one."""

    __tablename__ = "keyword_trends"
    __table_args__ = (
        UniqueConstraint("keyword_query_id", "normalized_keyword", "period_start", "device"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    keyword_query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="NAVER_DATALAB")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    time_unit: Mapped[str] = mapped_column(String(16), nullable=False, default="month")
    device: Mapped[str] = mapped_column(String(16), nullable=False, default="ALL")
    relative_index: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Relative interest, 0-100 within the requested window. NOT a search count.",
    )
    index_basis_note_ko: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KeywordList(Base, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "keyword_lists"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[JsonArray] = json_column()


class KeywordOpportunity(Base, OrganizationScopedMixin, ImmutableMixin):
    """VEO's own opportunity score.

    Explicitly a VEO calculation, never a provider figure. Every component is stored
    separately so a customer can see exactly what drove the number, and the formula
    version travels with it.
    """

    __tablename__ = "keyword_opportunities"
    __table_args__ = (
        UniqueConstraint("keyword_query_id", "normalized_keyword", "formula_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    keyword_query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="CALCULATED")

    demand: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend: Mapped[float | None] = mapped_column(Float, nullable=True)
    intent_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition_inverse: Mapped[float | None] = mapped_column(Float, nullable=True)
    content_gap: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculation_trace: Mapped[JsonObject] = json_column()
    missing_components: Mapped[JsonArray] = json_column()
