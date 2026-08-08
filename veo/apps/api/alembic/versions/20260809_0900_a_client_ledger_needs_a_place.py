"""거래처 대장에 소재지 칸.

상호는 식별자가 아니다. `서울치과` 는 수십 곳이고, 대장에 이름만 적혀 있으면 어느
서울치과를 맡고 있는지 사람이 목록에서 가리지 못한다.

**측정용 값이 아니다.** AI 답변과 글자로 대조하는 소재지 표현은
`brand_identities.address_terms` 에 이미 있고 그대로 둔다 — 저것은 "답변이 말할 만한
표현"(행정동·역명·랜드마크)이고 이것은 "우편물이 가는 곳"이다. 한 칸으로 합치면 둘 중
하나가 망가진다.

`nullable=True` 인 이유: 이미 있는 거래처 8곳에 넣을 값을 우리가 모른다. 비워 두는
것이 지어내는 것보다 낫다.

Revision ID: b7e2f04c91a5
Revises: f1c3a9d54b82
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b7e2f04c91a5"
down_revision = "f1c3a9d54b82"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("address", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "address")
