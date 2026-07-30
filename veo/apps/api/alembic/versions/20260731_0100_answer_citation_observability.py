"""answer citation observability

인용률의 분모를 정직하게 만들려면 **인용을 볼 수 있었는지**를 답변마다 알아야 한다.
`citations` 가 비어 있는 것은 두 가지 뜻이고, 둘은 정반대다.

    STRUCTURED     + 인용 0건  →  엔진이 출처를 밝혔고 우리는 거기 없었다
    그 밖의 값      + 인용 0건  →  이 응답으로는 출처를 알 수 없다

앞의 것만 인용률 분모에 들어간다. 뒤의 것을 넣으면 인용률이 낮게 나오고, 그 낮은 값은
**사이트 탓처럼 읽힌다.** 실제로는 그 모델이 출처를 알려주지 않은 것이다 — 같은 부류의
결함을 어댑터 층에서 한 번 고쳤고(`CITATION_CAPABLE_MODEL_PREFIXES`), 이것은 그것이
저장 층까지 살아남게 하는 조치다.

`RecordedAnswer` 는 이 값을 갖고 있었는데 `ObservationRun` 을 거치며 흘렸다. 지금은
실행 기록과 이 컬럼까지 함께 온다.

Revision ID: d5b2e1c9a374
Revises: c4a1f0d7b2e8
Create Date: 2026-07-31 01:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5b2e1c9a374"
down_revision: str | None = "c4a1f0d7b2e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COMMENT = (
    "이 응답에서 인용을 볼 수 있었는가. STRUCTURED 인 답변만 인용률의 분모에 "
    "들어간다. 볼 수 없었던 답변을 분모에 넣으면 인용률이 낮게 나오고, 그 낮은 "
    "값은 사이트 탓처럼 읽힌다 — 실제로는 그 모델이 출처를 알려주지 않은 것이다."
)


def upgrade() -> None:
    op.add_column(
        "ai_answers",
        sa.Column("citation_support", sa.String(length=32), nullable=True, comment=_COMMENT),
    )


def downgrade() -> None:
    op.drop_column("ai_answers", "citation_support")
