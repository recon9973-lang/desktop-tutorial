"""거래처 등록은 사람이 정한다 — 재 본 것과 맡은 것을 가른다.

주소만 넣으면 잰다는 규칙 덕분에 영업 중에 아무 주소나 넣어 볼 수 있다. 그런데 그렇게
만들어진 자리가 **거래처 목록에 그대로 섞였다.** 목록이 "우리가 맡은 곳"을 말하지 못하고
"이 도구를 거쳐 간 주소"를 말하게 되어, 아침에 열어도 할 일이 보이지 않는다(사용자 지적).

`is_active` 와는 다른 축이다. 저것은 **지웠는가**, 이것은 **우리 거래처인가** 이다. 한
칸에 접으면 "재 보기만 한 곳"과 "거래처였다가 끊긴 곳"이 같은 값이 되어 구분이 사라진다.

기존 행은 전부 True 로 둔다. 이미 목록에 있던 업체가 이 마이그레이션 하나로 조용히
사라지면, 사장님은 무엇이 없어졌는지도 모른 채 찾게 된다. 어느 것이 손으로 등록한
것이고 어느 것이 자동 생성인지 지금 와서는 알 수 없고, **추측으로 숨기는 것보다 남겨
두고 사람이 지우는 편이 되돌리기 쉽다.**
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a1c7e5b93d80"
down_revision: str | None = "f4b8c31e9a72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "is_registered",
            sa.Boolean(),
            nullable=False,
            # 기존 행을 채우기 위해 필요하다. 앞으로 만들어지는 행의 값은 애플리케이션이
            # 정한다 — 진단이 자동으로 만드는 자리는 명시적으로 False 를 보낸다.
            server_default=sa.true(),
        ),
    )
    # 목록은 늘 이 값으로 걸러 읽는다. 거래처가 늘어날수록 이 색인이 일한다.
    op.create_index(
        "ix_customers_organization_registered",
        "customers",
        ["organization_id", "is_registered"],
    )


def downgrade() -> None:
    op.drop_index("ix_customers_organization_registered", table_name="customers")
    op.drop_column("customers", "is_registered")
