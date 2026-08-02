"""Structural guarantees of the VEO schema.

These run without a database — they inspect the mapped metadata, which is what the
migration is generated from.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Table

from veo.db.models import Base

METADATA = Base.metadata

# Tables that are genuinely global rather than tenant-owned.
GLOBAL_TABLES = frozenset(
    {
        "organizations",
        "users",
        "scoring_versions",
        "ai_engines",
        # Throttling happens before authentication, so there is no organization yet —
        # the row is keyed by a hashed identifier and nothing else.
        "login_attempts",
        # Nullable organization_id: these survive an organization being removed.
        "audit_logs",
        "api_usage_events",
        # 익명 방문자의 공유 진단 결과 — 어떤 고객에게도 속하지 않는다.
        "public_shared_results",
    }
)

# Append-only tables: a run or a version is evidence, and evidence you can edit is not evidence.
IMMUTABLE_TABLES = frozenset(
    {
        "scan_runs",
        "evidence",
        "check_results",
        "score_results",
        "scoring_versions",
        "verification_runs",
        "keyword_queries",
        "keyword_metrics",
        "related_keywords",
        "keyword_trends",
        "keyword_opportunities",
        "observation_runs",
        "ai_answers",
        "citations",
        "entity_mentions",
        "report_versions",
        "audit_logs",
        "api_usage_events",
    }
)


def tables() -> list[Table]:
    return sorted(METADATA.tables.values(), key=lambda t: t.name)


def test_schema_has_the_expected_scale() -> None:
    assert len(METADATA.tables) >= 30


@pytest.mark.parametrize("table", tables(), ids=lambda t: t.name)
def test_tenant_tables_carry_organization_id(table: Table) -> None:
    if table.name in GLOBAL_TABLES:
        return
    assert "organization_id" in table.c, (
        f"{table.name} has no organization_id — guessing a row id from another "
        "organization must never be enough to read it"
    )
    assert not table.c.organization_id.nullable, f"{table.name}.organization_id must be NOT NULL"


@pytest.mark.parametrize("table", tables(), ids=lambda t: t.name)
def test_organization_id_is_indexed(table: Table) -> None:
    if "organization_id" not in table.c:
        return
    indexed = table.c.organization_id.index or any(
        "organization_id" in index.columns for index in table.indexes
    )
    assert indexed, f"{table.name}.organization_id is not indexed"


@pytest.mark.parametrize("name", sorted(IMMUTABLE_TABLES))
def test_immutable_tables_have_no_updated_at(name: str) -> None:
    table = METADATA.tables[name]
    assert "updated_at" not in table.c, (
        f"{name} is an append-only record; it must not expose updated_at. "
        "Corrections arrive as a new run or version."
    )
    assert "created_at" in table.c


@pytest.mark.parametrize("table", tables(), ids=lambda t: t.name)
def test_every_table_has_a_primary_key(table: Table) -> None:
    assert list(table.primary_key.columns), f"{table.name} has no primary key"


def test_score_result_keeps_everything_needed_to_defend_a_number() -> None:
    columns = METADATA.tables["score_results"].c
    for required in (
        "spec_id",
        "spec_version",
        "spec_checksum",
        "score",
        "score_before_caps",
        "coverage",
        "confidence",
        "effective_weight_total",
        "category_scores",
        "applied_caps",
        "gates",
        "calculation_trace",
    ):
        assert required in columns, f"score_results is missing {required}"

    for required in ("spec_id", "spec_version", "spec_checksum", "coverage", "confidence"):
        assert not columns[required].nullable, (
            f"score_results.{required} must be NOT NULL — a score without it is undefendable"
        )

    # A score itself may be null: NOT_APPLICABLE and UNKNOWN are real outcomes.
    assert columns["score"].nullable


def test_check_result_distinguishes_not_applicable_from_unknown() -> None:
    columns = METADATA.tables["check_results"].c
    assert "not_applicable_reason" in columns
    assert "unknown_reason" in columns
    assert "affected_weight" in columns
    assert "evaluated_weight" in columns


def test_keyword_metrics_pair_every_count_with_a_quality_flag() -> None:
    """Zero, missing and provider-suppressed must not collapse into one number."""
    columns = METADATA.tables["keyword_metrics"].c
    for metric in ("monthly_pc_searches", "monthly_mobile_searches"):
        assert f"{metric}_quality" in columns, f"{metric} has no paired quality column"
        assert columns[metric].nullable, f"{metric} must be nullable so missing is not zero"
    assert "source" in columns
    assert "collected_at" in columns
    assert not columns["collected_at"].nullable


def test_datalab_trend_is_stored_apart_from_search_counts() -> None:
    trend = METADATA.tables["keyword_trends"].c
    metrics = METADATA.tables["keyword_metrics"].c

    assert "relative_index" in trend
    # A relative interest index must never live in a column that reads as a count.
    assert "monthly_total_searches" not in trend
    assert "relative_index" not in metrics


def test_readiness_scores_and_observed_visibility_live_in_different_tables() -> None:
    score_columns = set(METADATA.tables["score_results"].c.keys())
    forbidden = {"mention_rate", "citation_rate", "share_of_voice", "visibility_score"}
    assert not (score_columns & forbidden), (
        "observed AI visibility must not be stored on a readiness score row"
    )
    assert "observation_runs" in METADATA.tables
    assert "ai_answers" in METADATA.tables


def test_raw_ai_answers_are_referenced_not_inlined() -> None:
    """Raw answers are sensitive: stored behind object storage and a hash, not a text blob."""
    columns = METADATA.tables["ai_answers"].c
    assert "raw_answer_storage_key" in columns
    assert "raw_answer_hash" in columns
    assert not columns["raw_answer_hash"].nullable


def test_audit_log_never_stores_a_raw_ip() -> None:
    columns = METADATA.tables["audit_logs"].c
    assert "source_ip_hash" in columns
    assert "source_ip" not in columns


def test_jobs_support_idempotency_retry_and_partial_success() -> None:
    columns = METADATA.tables["jobs"].c
    for required in (
        "idempotency_key",
        "input_hash",
        "attempts",
        "max_attempts",
        "next_retry_at",
        "partial_result_available",
        "safe_error_message",
        "internal_error_ref",
    ):
        assert required in columns, f"jobs is missing {required}"


def test_password_hash_column_is_never_named_password() -> None:
    columns = METADATA.tables["users"].c
    assert "password" not in columns
    assert "password_hash" in columns
