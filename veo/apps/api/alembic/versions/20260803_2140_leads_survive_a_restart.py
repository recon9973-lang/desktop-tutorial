"""상담 요청(리드)이 재시작을 견딘다.

지금까지 리드의 수명은 프로세스의 수명이었다 — InMemoryLeadStore 는 재배포 한 번이면
방문자가 남긴 연락처를 전부 잃었다. "저장했습니다" 라고 답해 놓고 잃는 것은 영업
기회의 문제이기 전에 정직의 문제다. 이 테이블이 그 거짓을 지운다.

organization_id 가 없다: 리드는 아직 어떤 고객도 아니다. 칼럼은 StoredLead 의 다섯
필드 그대로 — 여섯 번째 칸을 만들지 않는 것이 리드 모듈의 존재 이유다.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e7a2d94c1f58"
down_revision: str | None = "c9e4a51f7b23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_leads",
        sa.Column("lead_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("site_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_public_leads_received_at", "public_leads", ["received_at"])


def downgrade() -> None:
    # 되돌리면 남긴 연락처가 전부 사라진다 — 되돌리기 전에 반드시 내보내야 한다.
    op.drop_index("ix_public_leads_received_at", table_name="public_leads")
    op.drop_table("public_leads")
