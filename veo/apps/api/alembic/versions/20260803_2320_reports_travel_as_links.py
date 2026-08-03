"""리포트가 링크로 여행한다 — 거래처 전달 링크의 복사본 저장소 (P2-10a).

지금까지 발행한 리포트를 업체에 주는 길은 파일 내보내기뿐이었다. 이 테이블은 공유
시점의 HTML 내보내기를 통째로 굳혀 담고, 익명 링크는 이 복사본만 연다 — 발행 불변
원칙과 익명 표면의 격리 원칙(공유 진단 결과와 같은 계열)이 함께 지켜진다.

행의 키는 토큰의 지문이라 DB 가 통째로 읽혀도 공유 주소를 복원할 수 없다.
organization_id 가 없다: 복사본은 링크를 받은 사람의 것이 될 문서이지 조회 창구가
아니다.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "f4b8c31e9a72"
down_revision: str | None = "e7a2d94c1f58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_shared_reports",
        sa.Column("fingerprint", sa.String(length=128), primary_key=True),
        sa.Column("html", sa.Text, nullable=False),
        sa.Column("title_ko", sa.String(length=300), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_public_shared_reports_expires_at", "public_shared_reports", ["expires_at"]
    )


def downgrade() -> None:
    # 되돌리면 업체에 이미 보낸 링크가 전부 죽는다 — 보낸 사람은 모른 채로.
    op.drop_index("ix_public_shared_reports_expires_at", table_name="public_shared_reports")
    op.drop_table("public_shared_reports")
