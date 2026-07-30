"""ai answer cost in the currency it was measured in

`ai_answers.cost_krw` 는 원화 칸인데, 엔진도 가격표도 **달러**로 값을 준다
(`ModelPrice.input_usd_per_million`). 그 상태로 저장하려면 환율이 필요하고, 환율을
지어내면 고객에게 제시하는 금액이 틀린다. 더 나쁜 것은 나중에 환율이 바뀌면 **과거
기록까지 달라진다**는 점이다 — 그때 잰 비용은 그때의 사실이어야 한다.

그래서 재는 단위와 저장 단위를 같게 만든다. `cost_usd` 가 실측값이고, `cost_krw` 는
환율을 아는 시점에만 채우는 표시용 환산값으로 남긴다. 둘 다 비어 있을 수 있으며 그것은
0원이 아니라 "모른다" 이다.

기존 행은 없다 — 관측 실행 경로가 아직 열리지 않아 이 표에 저장된 것이 하나도 없다.
그래서 되돌리기가 안전하다.

Revision ID: c4a1f0d7b2e8
Revises: 87dbf72e5649
Create Date: 2026-07-30 19:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4a1f0d7b2e8"
down_revision: str | None = "87dbf72e5649"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_answers",
        sa.Column(
            "cost_usd",
            sa.Float(),
            nullable=True,
            comment=(
                "제공자에게 실제로 청구되는 통화 그대로. 엔진과 가격표가 모두 USD 이므로 "
                "여기가 실측값이다. 값이 없는 것은 0원이 아니라 '모른다' 이며, 그 이유는 "
                "가격표 미설정·사용량 미보고·가격표 만료 중 하나다."
            ),
        ),
    )
    op.alter_column(
        "ai_answers",
        "cost_krw",
        existing_type=sa.Float(),
        existing_nullable=True,
        comment=(
            "환율을 아는 시점에만 채운다. 비어 있는 것이 기본이다 — 환율을 지어내면 "
            "고객에게 제시하는 금액이 틀리고, 나중에 환율이 바뀌면 과거 기록까지 "
            "달라진다. 재는 단위(USD)와 저장 단위를 같게 둔 것이 `cost_usd` 이고, "
            "이 칸은 표시용 환산값이다."
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "ai_answers",
        "cost_krw",
        existing_type=sa.Float(),
        existing_nullable=True,
        comment=None,
    )
    op.drop_column("ai_answers", "cost_usd")
