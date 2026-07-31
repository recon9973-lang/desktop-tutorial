"""claim assessments can be read back

`claim_assessments` 는 지금까지 **쓰는 코드가 0건**이었다. 그래서 이 테이블이 실제로
쓸 수 있는 모양인지 아무도 확인하지 않았고, 확인해 보니 아니었다.

빠져 있던 것 셋:

1. **근거를 다시 열 수 없다.** `claim_text` 만 있고 원문 포인터·해시·구간이 없다.
   그 문장이 정말 그 답변의 그 자리였는지 확인할 방법이 없으므로, 저장된 지적은
   근거가 아니라 주장이 된다(0-A).
2. **판정을 되읽을 수 없다.** `automated_basis`(규칙인가 모델인가)와 `rule_id` 가 없어
   행에서 판정 객체를 복원할 수 없다. `claim_domain` 도 없어 심각도를 다시 계산할 수
   없다 — 규제 영역은 유형과 무관하게 치명이기 때문이다.
3. **검수 단계가 셋으로 접힌다.** `review_state` 는 네 값뿐이라
   `UNDER_REVIEW`·`NEEDS_MORE_EVIDENCE` 가 `PENDING_REVIEW` 로 뭉개진다. 재기동하면
   "누가 잡고 있었는지", "근거 보강 대기인지 손도 안 댄 건인지" 가 사라지고, 워커가 두
   대면 같은 건을 두 사람이 각각 판정한다.

`risk/INTEGRATION_REQUEST.md` 의 요청 #1·#2·#3 이 이 셋이다.

Revision ID: 8c41d7b02e19
Revises: 2580c21edf72
Create Date: 2026-07-31 14:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c41d7b02e19"
down_revision: str | None = "2580c21edf72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 요청 #1 — 어휘 8종. `RECOMMENDATION` 하나로는 "잘못 추천되었다" 와 "당연히 들어가야
    # 할 목록에서 빠졌다" 가 구별되지 않고, 둘은 대응이 정반대다.
    op.alter_column(
        "claim_assessments",
        "assessment_type",
        existing_type=sa.String(length=48),
        existing_nullable=False,
        comment=(
            "CLAIM_ACCURACY | CITATION_ENTAILMENT | CITATION_COMPLETENESS | "
            "ENTITY_DISAMBIGUATION | RECOMMENDATION_INCLUSION | RECOMMENDATION_EXCLUSION | "
            "SENTIMENT_WITH_GROUNDS | STALENESS"
        ),
    )

    op.add_column(
        "claim_assessments",
        sa.Column(
            "claim_domain",
            sa.String(length=32),
            nullable=False,
            server_default="GENERAL",
            comment=(
                "MEDICAL | LEGAL | PRICING | CONTRACTUAL | IDENTITY | CONTACT | "
                "REPUTATION | GENERAL — 심각도가 여기서 나온다. 규제 4종은 유형과 무관하게 "
                "치명이므로, 이 값을 안 남기면 저장된 행에서 심각도를 다시 계산할 수 없다."
            ),
        ),
    )
    op.add_column(
        "claim_assessments",
        sa.Column(
            "automated_basis",
            sa.String(length=32),
            nullable=False,
            server_default="NOT_MEASURED",
            comment=(
                "DETERMINISTIC_RULE | LANGUAGE_MODEL | NOT_MEASURED — 누가 판정했나. "
                "이것 없이는 행을 다시 판정 객체로 읽을 수 없다."
            ),
        ),
    )
    op.add_column(
        "claim_assessments",
        sa.Column(
            "rule_id",
            sa.String(length=32),
            nullable=True,
            comment="규칙 판정일 때 어떤 규칙이었나. 규칙 판정에는 필수, 모델 판정에는 금지.",
        ),
    )

    # 근거 — 이 지적을 나중에 다시 열어볼 수 있게 하는 값들.
    op.add_column(
        "claim_assessments", sa.Column("evidence_answer_ref", sa.Text(), nullable=True)
    )
    op.add_column(
        "claim_assessments",
        sa.Column("evidence_answer_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "claim_assessments", sa.Column("evidence_span_start", sa.Integer(), nullable=True)
    )
    op.add_column(
        "claim_assessments", sa.Column("evidence_span_end", sa.Integer(), nullable=True)
    )

    # 요청 #2 — 다섯 단계를 있는 그대로.
    op.add_column(
        "claim_assessments",
        sa.Column(
            "review_stage",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING_REVIEW",
            comment=(
                "PENDING_REVIEW | UNDER_REVIEW | NEEDS_MORE_EVIDENCE | CONFIRMED | "
                "REJECTED — 검수 기계의 다섯 단계. `review_state` 는 이 가운데 셋을 "
                "PENDING_REVIEW 로 접으므로, 그 칸만으로는 '누가 잡고 있었는지'·'근거 보강 "
                "대기인지 손도 안 댄 건인지' 를 재기동 후 복원할 수 없다."
            ),
        ),
    )

    # 요청 #3 — 점유. `reviewed_by`(판단한 사람)로 대신할 수 없다. 여기 필요한 것은
    # "아직 판단하지 않았지만 보고 있는 사람" 이고, 둘을 합치면 착수만 한 건이 검수
    # 완료로 읽힌다.
    op.add_column(
        "claim_assessments", sa.Column("claimed_by", sa.UUID(), nullable=True)
    )
    op.add_column(
        "claim_assessments",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_claim_assessments_claimed_by_users"),
        "claim_assessments",
        "users",
        ["claimed_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "claim_assessments",
        sa.Column(
            "review_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )

    # 기존 행을 채우기 위한 기본값이고, 그 뒤로는 애플리케이션이 값을 정한다. DB 에
    # 남겨 두면 모델과 어긋나 `alembic check` 가 매번 새 변경을 찾아낸다.
    for column in ("claim_domain", "automated_basis", "review_stage", "review_history"):
        op.alter_column("claim_assessments", column, server_default=None)


def downgrade() -> None:
    op.drop_column("claim_assessments", "review_history")
    op.drop_constraint(
        op.f("fk_claim_assessments_claimed_by_users"),
        "claim_assessments",
        type_="foreignkey",
    )
    op.drop_column("claim_assessments", "claimed_at")
    op.drop_column("claim_assessments", "claimed_by")
    op.drop_column("claim_assessments", "review_stage")
    op.drop_column("claim_assessments", "evidence_span_end")
    op.drop_column("claim_assessments", "evidence_span_start")
    op.drop_column("claim_assessments", "evidence_answer_hash")
    op.drop_column("claim_assessments", "evidence_answer_ref")
    op.drop_column("claim_assessments", "rule_id")
    op.drop_column("claim_assessments", "automated_basis")
    op.drop_column("claim_assessments", "claim_domain")
    op.alter_column(
        "claim_assessments",
        "assessment_type",
        existing_type=sa.String(length=48),
        existing_nullable=False,
        comment=(
            "CLAIM_ACCURACY | CITATION_ENTAILMENT | CITATION_COMPLETENESS | "
            "ENTITY_DISAMBIGUATION | RECOMMENDATION | SENTIMENT | STALENESS"
        ),
    )
