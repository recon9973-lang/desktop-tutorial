"""확신도는 모를 수 있다 — check_results.confidence 를 NULL 허용으로.

**무엇이 잘못돼 있었나.** `confidence` 가 `NOT NULL` 이라 "매기지 않았다" 를 담을 자리가
없었고, 저장하는 쪽이 `outcome.confidence or 0.0` 으로 접었다. 그래서 확신도를 매기지
않는 검사가 전부 **0.0** 으로 들어갔다. 운영 실측(2026-08-05): 1,767건이 0.0, 248건이 1.0.

페이지 점수 산식은 손실에 확신도를 곱한다:

    손실 = 배점 x 상태계수 x 폭 x 확신도

확신도가 0.0 이면 손실이 0 이 되고, **모든 페이지가 100점**으로 나간다. 화면에서
`실패 5건`인 페이지가 `100.0` 으로 표시됐다. 사이트 점수는 처음부터 `None → 1.0` 으로
옳게 읽고 있었는데(`scoring/page.py`), 저장이 그 `None` 을 없애 읽는 쪽이 손쓸 수 없었다.

**이미 쌓인 0.0 을 NULL 로 돌린다.** 그 값은 우리가 잰 것이 아니라 이 결함이 만든
흔적이다. 0.0 은 "확신이 전혀 없다" 라는 뜻인데 그렇게 판정한 검사는 없다 —
명세가 쓰는 값은 0.4·0.65·1.0 이다. 남겨 두면 지난 진단을 다시 열 때마다 100점이
계속 나온다.

되돌리기는 NULL 을 0.0 으로 되돌린다. 정보가 없으므로 원래 값을 복원할 수는 없다 —
그래서 downgrade 는 **결함이 있던 상태로 돌아가는 것**이고, 그 사실을 여기 적어 둔다.

Revision ID: d4a8b1c60e27
Revises: c2f9d47b6a13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4a8b1c60e27"
down_revision = "c2f9d47b6a13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "check_results",
        "confidence",
        existing_type=sa.Float(),
        nullable=True,
        comment="확신도. 매기지 않은 검사는 NULL — 0.0 이 아니다.",
    )
    # 결함이 만든 0.0 을 "모른다" 로 되돌린다. CHECK 제약(0..1)은 NULL 을 막지 않는다.
    op.execute(sa.text("UPDATE check_results SET confidence = NULL WHERE confidence = 0.0"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE check_results SET confidence = 0.0 WHERE confidence IS NULL"))
    op.alter_column(
        "check_results",
        "confidence",
        existing_type=sa.Float(),
        nullable=False,
        comment=None,
    )
