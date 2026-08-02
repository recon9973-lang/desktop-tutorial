"""api_usage_events.was_cache_hit 이 "모른다" 를 담을 수 있게 한다.

NOT NULL 이던 시절, 근거가 없을 때 False 가 들어갔다 — 그 False 는 "새로 쟀다" 가
아니라 "판단할 수 없었다" 는 뜻이었고, 둘을 섞으면 캐시 비율을 지표로 쓰는 순간
숫자가 거짓이 된다(usage/record.py 의 오래된 한계 주석). 캐시 비율을 화면에 그리기
전에 반드시 먼저 고쳐야 한다고 적어 두었던 그 마이그레이션이다.

기존 행은 손대지 않는다 — 과거의 False 가 어느 뜻이었는지 이제 와서 알 수 없고,
아는 척 NULL 로 바꾸면 그것대로 지어내는 것이다. 대신 이 시점 이후의 행부터
NULL(모름)이 가능해진다.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "b3d1c6a4e902"
down_revision: str | None = "6f0b1b1941dd"
branch_labels = None
depends_on = None

_COMMENT = "캐시 응답이었는가. NULL 은 판단 근거가 없었다는 뜻 — False(새로 잼)와 다르다."


def upgrade() -> None:
    op.alter_column(
        "api_usage_events",
        "was_cache_hit",
        existing_type=sa.Boolean(),
        nullable=True,
        comment=_COMMENT,
    )


def downgrade() -> None:
    # NULL 을 False 로 되접으면 "모름" 이 "새로 잼" 이 된다 — 되돌릴 때는 그 손실을
    # 감수한다는 뜻이므로, 명시적으로 채우고 조인다.
    op.execute("update api_usage_events set was_cache_hit = false where was_cache_hit is null")
    op.alter_column(
        "api_usage_events",
        "was_cache_hit",
        existing_type=sa.Boolean(),
        nullable=False,
        comment=None,
    )
