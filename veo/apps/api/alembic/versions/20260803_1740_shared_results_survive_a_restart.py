"""공유된 무료 진단 결과가 재시작을 견딘다.

지금까지 공유 링크의 수명은 프로세스의 수명이었다 — InMemoryPublicResultStore 는
재배포 한 번이면 발급된 모든 링크를 죽였고, 화면은 그 한계를 문구로 적어야 했다.
이 테이블이 그 문구를 지운다.

행의 키는 토큰의 지문(해시)이고 payload 안의 result_token 도 저장 전에 지워진다 —
DB 가 통째로 읽혀도 공유 주소를 복원할 수 없다. organization_id 가 없다: 익명
방문자의 결과는 어떤 고객에게도 속하지 않는다(tests/public/test_isolation.py).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c9e4a51f7b23"
down_revision: str | None = "b3d1c6a4e902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_shared_results",
        sa.Column("fingerprint", sa.String(length=128), primary_key=True),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_public_shared_results_expires_at", "public_shared_results", ["expires_at"]
    )


def downgrade() -> None:
    # 되돌리면 발급된 공유 링크가 전부 죽는다 — 인메모리 시절로 돌아간다는 뜻이고,
    # 그때는 화면의 만료 문구도 함께 되돌려야 정직하다.
    op.drop_index("ix_public_shared_results_expires_at", table_name="public_shared_results")
    op.drop_table("public_shared_results")
