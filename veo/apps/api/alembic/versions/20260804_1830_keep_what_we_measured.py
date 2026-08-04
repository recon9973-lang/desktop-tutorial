"""잰 것을 남긴다 — 진단이 실제로 받은 응답을 보관한다 (0-K).

venomad.com 진단이 15~27점으로 나왔는데 "무엇을 받았길래 그 점수인가" 에 답할 방법이
없었다. 남아 있던 것은 sha256 해시 64자와 수집기가 고른 2,000자 발췌뿐이었고, 둘 다
사람이 열어 볼 수 있는 것이 아니었다. 코드를 읽고 판정에서 거꾸로 추측하는 데 감사관
넷과 하루가 들었고, 그러고도 확정하지 못했다.

아무 AI에게 주소를 주면 페이지를 열어 보고 답한다. 우리는 측정기라면서 측정한 것을 안
갖고 있었다. `evidence.storage_key`("큰 자료는 객체 저장소에")가 처음부터 선언돼 있었지만
채우는 코드가 없었다 — 설계는 알고 있었고 배선이 없었다.

객체 저장소를 붙이는 것은 별건이므로 DB 에 상한을 두고 담는다. 상한을 넘으면 앞부분만
담고 `truncated` 로 그 사실을 남긴다 — 잘린 것을 전부인 척하지 않는다.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "c2f9d47b6a13"
down_revision: str | None = "a1c7e5b93d80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fetch_captures",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "scan_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scan_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("final_url", sa.Text, nullable=False),
        sa.Column("status", sa.Integer, nullable=False),
        sa.Column("headers", JSONB, nullable=False),
        sa.Column("request_headers", JSONB, nullable=False),
        sa.Column("body", sa.LargeBinary, nullable=False),
        sa.Column("byte_size", sa.Integer, nullable=False),
        sa.Column("truncated", sa.Boolean, nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_failure_ko", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_fetch_captures_run_url", "fetch_captures", ["scan_run_id", "url"])
    # ImmutableMixin 의 관례: 생성 시각에 색인을 둔다.
    op.create_index("ix_fetch_captures_created_at", "fetch_captures", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_fetch_captures_created_at", table_name="fetch_captures")
    op.drop_index("ix_fetch_captures_run_url", table_name="fetch_captures")
    op.drop_table("fetch_captures")
