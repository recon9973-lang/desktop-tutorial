"""수동 측정은 다른 종류의 측정이다 — observation_runs·prompt_sets 에 kind 추가.

**왜 칸을 따로 두는가.** 관리자가 "지금 이 검색어로 우리가 나오나" 를 직접 재는 일은
정당하고 자주 필요하다. 그런데 그 값을 정기 측정과 같은 칸에 담으면, 잘 나오는
검색어를 골라 재는 것만으로 추이가 올라간다. ADR 0015 가 막는 바로 그 실패다:

    "경쟁 비교를 조작하는 데 숫자를 위조할 필요가 없다. 질문만 고르면 된다."

값을 나중에 걸러내는 것으로는 부족하다. 걸러내려면 **무엇이 수동인지 알아야** 하고,
그 사실은 실행이 만들어지는 순간에만 확실하다. 그래서 열로 저장한다.

**기존 행은 전부 SCHEDULED 다.** 이 열이 생기기 전에는 수동 측정이라는 것 자체가
없었다. 추정이 아니라 그때 존재하지 않던 기능이다.

되돌리기는 열을 지운다. 수동 실행이 이미 쌓인 뒤에 되돌리면 그 실행들이 정기 측정과
구별되지 않게 되므로, 되돌리기 전에 `kind = 'MANUAL'` 행이 있는지 확인해야 한다.

Revision ID: f1c3a9d54b82
Revises: d4a8b1c60e27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f1c3a9d54b82"
down_revision = "d4a8b1c60e27"
branch_labels = None
depends_on = None

_RUN_COMMENT = "SCHEDULED | MANUAL. MANUAL 은 추이·비교에서 제외된다."
_SET_COMMENT = (
    "SCHEDULED | MANUAL. MANUAL 은 사람이 그 자리에서 만든 즉석 집합이라 "
    "ADR 0015 의 균형 검사를 거치지 않았다 — 비교와 추이에 쓸 수 없다."
)


def upgrade() -> None:
    op.add_column(
        "observation_runs",
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default="SCHEDULED",
            comment=_RUN_COMMENT,
        ),
    )
    op.add_column(
        "prompt_sets",
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default="SCHEDULED",
            comment=_SET_COMMENT,
        ),
    )
    # 수동 실행만 골라 보는 일이 잦다 — 목록 화면이 종류로 거른다.
    op.create_index(
        "ix_observation_runs_project_kind",
        "observation_runs",
        ["project_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_observation_runs_project_kind", table_name="observation_runs")
    op.drop_column("prompt_sets", "kind")
    op.drop_column("observation_runs", "kind")
